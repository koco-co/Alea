-- Alea roundtable execution and Sporttery scope hardening.
--
-- This migration is additive.  It keeps the implementation that originally
-- created jobs behind a private compatibility function, then exposes a strict
-- wrapper that resolves only authorized, currently wagerable Sporttery offers.

create or replace function public.alea_is_authorized_sporttery_source(
  p_data_source_id uuid,
  p_required_capabilities text[] default array[]::text[]
)
returns boolean
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_valid_until timestamptz;
  v_valid_until_text text;
begin
  select nullif(btrim(ds.configuration->>'authorization_valid_until'), '')
    into v_valid_until_text
  from public.data_sources ds
  where ds.id = p_data_source_id;

  if v_valid_until_text is not null then
    begin
      v_valid_until := v_valid_until_text::timestamptz;
    exception when invalid_text_representation or datetime_field_overflow then
      -- Malformed authorization metadata must fail closed, not abort selection.
      return false;
    end;
  end if;

  return exists (
    select 1
    from public.data_sources ds
    where ds.id = p_data_source_id
      and ds.enabled
      and ds.status = 'ready'
      and ds.kind in ('sporttery_web', 'licensed_supplier', 'admin_import')
      and ds.authorization_status = 'authorized'
      and nullif(btrim(ds.authorization_reference), '') is not null
      and (
        ds.kind <> 'admin_import'
        or lower(coalesce(ds.configuration->>'origin', '')) = 'sporttery'
      )
      and coalesce(ds.capabilities, array[]::text[])
          @> coalesce(p_required_capabilities, array[]::text[])
      and (v_valid_until is null or v_valid_until > now())
  );
end;
$$;

revoke all on function public.alea_is_authorized_sporttery_source(uuid, text[]) from public;
grant execute on function public.alea_is_authorized_sporttery_source(uuid, text[]) to alea_api, alea_worker;

create or replace function public.alea_is_sporttery_offer_eligible(
  p_match_id uuid,
  p_at timestamptz default now()
)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1
    from public.matches m
    join public.competitions c on c.id = m.competition_id
    join public.source_records canonical on canonical.id = m.canonical_source_record_id
    where m.id = p_match_id
      and c.sporttery_eligible
      and m.fact_state = 'verified'
      and m.sales_status = 'on_sale'
      and nullif(btrim(m.sporttery_match_number), '') is not null
      and m.sales_cutoff_at is not null
      and p_at < m.sales_cutoff_at
      and canonical.business_date = m.business_date
      and canonical.sporttery_match_number = m.sporttery_match_number
      and canonical.state in ('mapped', 'accepted')
      and public.alea_is_authorized_sporttery_source(
        canonical.data_source_id,
        array['caching', 'public_display']::text[]
      )
      and exists (
        select 1
        from public.match_odds_snapshots odds
        join public.source_records odds_record on odds_record.id = odds.source_record_id
        where odds.match_id = m.id
          and odds.observed_at <= p_at
          and odds.observed_at <= m.sales_cutoff_at
          and odds_record.business_date = m.business_date
          and odds_record.sporttery_match_number = m.sporttery_match_number
          and odds_record.state in ('mapped', 'accepted')
          and public.alea_is_authorized_sporttery_source(
            odds_record.data_source_id,
            array['caching', 'public_display']::text[]
          )
      )
  );
$$;

revoke all on function public.alea_is_sporttery_offer_eligible(uuid, timestamptz) from public;
grant execute on function public.alea_is_sporttery_offer_eligible(uuid, timestamptz) to alea_api, alea_worker;

-- Preserve the original implementation once.  Supabase applies each migration
-- once, while this guard keeps local reset/replay workflows deterministic.
do $migration$
begin
  if to_regprocedure(
    'public.alea_command_start_roundtable_unhardened_20260721(text,text,jsonb)'
  ) is null then
    if to_regprocedure('public.alea_command_start_roundtable(text,text,jsonb)') is null then
      raise exception 'base alea_command_start_roundtable function is missing';
    end if;
    alter function public.alea_command_start_roundtable(text, text, jsonb)
      rename to alea_command_start_roundtable_unhardened_20260721;
  end if;
end;
$migration$;

revoke all on function public.alea_command_start_roundtable_unhardened_20260721(text, text, jsonb) from public;
revoke all on function public.alea_command_start_roundtable_unhardened_20260721(text, text, jsonb) from alea_api;

create or replace function public.alea_command_start_roundtable(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions, pg_temp
as $$
declare
  v_payload jsonb := coalesce(p_payload, '{}'::jsonb);
  v_requested_mode text := coalesce(v_payload->>'mode', 'autonomous');
  v_business_date date;
  v_competition_scope text := nullif(btrim(coalesce(v_payload->>'competition_scope', 'all')), '');
  v_candidate_limit integer;
  v_instance_ids uuid[];
  v_selected_match_ids uuid[];
  v_excluded_match_ids uuid[];
  v_requested_match_ids uuid[];
  v_requested_match_count integer;
  v_result jsonb;
  v_job_id uuid;
  v_scheduled boolean := false;
  v_now timestamptz := now();
begin
  perform public.alea_assert_admin_actor(p_actor_id);

  begin
    v_scheduled := coalesce((v_payload->>'scheduled')::boolean, false);
  exception when invalid_text_representation then
    raise exception 'scheduled must be a boolean' using errcode = '22023';
  end;

  -- The existing scheduler does not consume this request shape.  Failing closed
  -- is safer than creating a job that appears scheduled but starts immediately.
  if v_scheduled then
    raise exception 'scheduled_roundtable_not_supported'
      using errcode = '0A000';
  end if;

  if v_requested_mode not in ('autonomous', 'specified') then
    raise exception 'invalid roundtable mode' using errcode = '22023';
  end if;

  begin
    v_business_date := (v_payload->>'business_date')::date;
  exception
    when invalid_text_representation or datetime_field_overflow then
      raise exception 'invalid business_date' using errcode = '22023';
  end;
  if v_business_date is null then
    raise exception 'business_date is required' using errcode = '22023';
  end if;

  begin
    v_candidate_limit := least(
      greatest(coalesce((v_payload->>'candidate_limit')::integer, 8), 1),
      20
    );
  exception when invalid_text_representation or numeric_value_out_of_range then
    raise exception 'invalid candidate_limit' using errcode = '22023';
  end;

  if jsonb_typeof(coalesce(v_payload->'instance_ids', '[]'::jsonb)) <> 'array' then
    raise exception 'instance_ids must be an array' using errcode = '22023';
  end if;
  begin
    v_instance_ids := array(
      select value::uuid
      from jsonb_array_elements_text(coalesce(v_payload->'instance_ids', '[]'::jsonb))
    );
  exception when invalid_text_representation then
    raise exception 'instance_ids contains invalid UUID' using errcode = '22023';
  end;

  if coalesce(array_length(v_instance_ids, 1), 0) <> 3
     or (select count(distinct id) from unnest(coalesce(v_instance_ids, '{}'::uuid[])) as selected(id)) <> 3 then
    raise exception 'roundtable requires exactly three distinct instances'
      using errcode = '22023';
  end if;

  if (
    select count(distinct provider.family)
    from unnest(v_instance_ids) as selected(id)
    join public.ai_instances instance on instance.id = selected.id
    join public.ai_providers provider on provider.id = instance.provider_id
  ) < 2 then
    raise exception 'roundtable requires at least two provider families'
      using errcode = '40902';
  end if;

  if jsonb_typeof(coalesce(v_payload->'excluded_match_ids', '[]'::jsonb)) <> 'array' then
    raise exception 'excluded_match_ids must be an array' using errcode = '22023';
  end if;
  begin
    v_excluded_match_ids := array(
      select distinct value::uuid
      from jsonb_array_elements_text(coalesce(v_payload->'excluded_match_ids', '[]'::jsonb))
    );
  exception when invalid_text_representation then
    raise exception 'excluded_match_ids contains invalid UUID' using errcode = '22023';
  end;

  if v_requested_mode = 'specified' then
    if jsonb_typeof(coalesce(v_payload->'match_ids', '[]'::jsonb)) <> 'array' then
      raise exception 'match_ids must be an array' using errcode = '22023';
    end if;
    v_requested_match_count := jsonb_array_length(coalesce(v_payload->'match_ids', '[]'::jsonb));
    if v_requested_match_count < 1 then
      raise exception 'specified mode requires match_ids' using errcode = '22023';
    end if;
    begin
      v_requested_match_ids := array(
        select value::uuid
        from jsonb_array_elements_text(v_payload->'match_ids')
      );
    exception when invalid_text_representation then
      raise exception 'match_ids contains invalid UUID' using errcode = '22023';
    end;

    if (select count(distinct id) from unnest(v_requested_match_ids) as selected(id)) <> v_requested_match_count then
      raise exception 'match_ids must be distinct' using errcode = '22023';
    end if;
    if coalesce(v_requested_match_ids && coalesce(v_excluded_match_ids, '{}'::uuid[]), false) then
      raise exception 'selected match is excluded' using errcode = '22023';
    end if;

    select array_agg(m.id order by m.kickoff_at, m.id)
      into v_selected_match_ids
    from public.matches m
    join public.competitions c on c.id = m.competition_id
    where m.id = any(v_requested_match_ids)
      and m.business_date = v_business_date
      and public.alea_is_sporttery_offer_eligible(m.id, v_now)
      and (
        lower(coalesce(v_competition_scope, 'all')) = 'all'
        or lower(c.name) = lower(v_competition_scope)
        or c.id::text = v_competition_scope
      );

    if coalesce(array_length(v_selected_match_ids, 1), 0) <> v_requested_match_count then
      raise exception 'selected match is not an eligible Sporttery offer'
        using errcode = '40901';
    end if;
  else
    select array_agg(chosen.id order by chosen.kickoff_at, chosen.id)
      into v_selected_match_ids
    from (
      select m.id, m.kickoff_at
      from public.matches m
      join public.competitions c on c.id = m.competition_id
      where m.business_date = v_business_date
        and not (m.id = any(coalesce(v_excluded_match_ids, '{}'::uuid[])))
        and public.alea_is_sporttery_offer_eligible(m.id, v_now)
        and (
          lower(coalesce(v_competition_scope, 'all')) = 'all'
          or lower(c.name) = lower(v_competition_scope)
          or c.id::text = v_competition_scope
        )
      order by m.kickoff_at, m.id
      limit v_candidate_limit
    ) as chosen;

    if coalesce(array_length(v_selected_match_ids, 1), 0) = 0 then
      raise exception 'no_eligible_sporttery_matches' using errcode = '40901';
    end if;
  end if;

  -- Resolve selection before delegating so the compatibility implementation no
  -- longer has an opportunity to select non-Sporttery or non-wagerable matches.
  v_payload := v_payload
    || jsonb_build_object(
      'mode', 'specified',
      'match_ids', to_jsonb(v_selected_match_ids),
      'instance_ids', to_jsonb(v_instance_ids),
      'candidate_limit', v_candidate_limit,
      'scheduled', false
    );

  v_result := public.alea_command_start_roundtable_unhardened_20260721(
    p_actor_id,
    p_request_id,
    v_payload
  );

  v_job_id := nullif(v_result->>'job_id', '')::uuid;
  if v_job_id is not null then
    update public.roundtable_jobs
    set config_snapshot = config_snapshot || jsonb_build_object(
          'requested_mode', v_requested_mode,
          'resolved_match_ids', to_jsonb(v_selected_match_ids),
          'selection_policy', 'authorized_sporttery_offer_v1',
          'selection_resolved_at', v_now
        ),
        sales_cutoff_at = (
          select min(m.sales_cutoff_at)
          from public.matches m
          where m.id = any(v_selected_match_ids)
        ),
        updated_at = now()
    where id = v_job_id;
  end if;

  return v_result || jsonb_build_object(
    'requested_mode', v_requested_mode,
    'resolved_match_ids', to_jsonb(v_selected_match_ids),
    'selection_policy', 'authorized_sporttery_offer_v1'
  );
end;
$$;

revoke all on function public.alea_command_start_roundtable(text, text, jsonb) from public;
grant execute on function public.alea_command_start_roundtable(text, text, jsonb) to alea_api;

-- Turn a durable lifecycle message into first-phase work.  This function is
-- idempotent: unique business keys protect both phase runs and outbox rows.
create or replace function public.alea_worker_initialize_roundtable(
  p_job_id uuid,
  p_event_type text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_job public.roundtable_jobs%rowtype;
  v_participant_count integer;
  v_provider_count integer;
  v_match_count integer;
  v_eligible_match_count integer;
  v_phase_count integer := 0;
  v_new_phase_count integer := 0;
  v_new_outbox_count integer := 0;
  v_event_id uuid;
  v_event_seq bigint;
begin
  if session_user <> 'alea_worker' then
    raise exception 'worker role required' using errcode = '42501';
  end if;

  select * into v_job
  from public.roundtable_jobs
  where id = p_job_id
  for update;

  if not found then
    raise exception 'roundtable job not found' using errcode = 'P0002';
  end if;

  if v_job.state in ('completed', 'no_quorum', 'terminated', 'failed') then
    return jsonb_build_object(
      'status', 'terminal',
      'job_id', p_job_id,
      'state', v_job.state,
      'phase_count', 0
    );
  end if;

  select count(*), count(distinct provider_family)
    into v_participant_count, v_provider_count
  from public.roundtable_participants
  where job_id = p_job_id;

  select count(*) into v_match_count
  from public.roundtable_match_runs
  where job_id = p_job_id;

  select count(*) into v_eligible_match_count
  from public.roundtable_match_runs match_run
  where match_run.job_id = p_job_id
    and public.alea_is_sporttery_offer_eligible(match_run.match_id, now());

  if v_participant_count <> 3 or v_provider_count < 2 or v_match_count < 1 then
    update public.roundtable_jobs
    set state = 'no_quorum',
        state_version = state_version + 1,
        terminal_reason = case
          when v_match_count < 1 then 'no_eligible_sporttery_matches'
          else 'roundtable_quorum_not_met'
        end,
        updated_at = now()
    where id = p_job_id
      and state not in ('completed', 'terminated', 'failed', 'no_quorum');

    update public.roundtable_match_runs
    set state = 'no_quorum',
        state_version = state_version + 1,
        quorum_instance_count = v_participant_count,
        quorum_provider_count = v_provider_count,
        terminal_reason = 'roundtable_quorum_not_met',
        updated_at = now()
    where job_id = p_job_id
      and state = 'pending';

    insert into public.roundtable_events (job_id, event_type, payload, is_public)
    values (
      p_job_id,
      'roundtable.no_quorum',
      jsonb_build_object(
        'participant_count', v_participant_count,
        'provider_count', v_provider_count,
        'match_count', v_match_count
      ),
      false
    )
    returning id, event_seq into v_event_id, v_event_seq;

    return jsonb_build_object(
      'status', 'no_quorum',
      'event_id', v_event_id,
      'event_seq', v_event_seq,
      'phase_count', 0
    );
  end if;

  if v_eligible_match_count <> v_match_count
     or v_job.sales_cutoff_at is null
     or now() >= v_job.sales_cutoff_at then
    update public.roundtable_jobs
    set state = 'terminated',
        state_version = state_version + 1,
        terminal_reason = 'sporttery_offer_no_longer_eligible',
        updated_at = now()
    where id = p_job_id
      and state not in ('completed', 'terminated', 'failed', 'no_quorum');

    update public.roundtable_match_runs
    set state = 'terminated',
        state_version = state_version + 1,
        terminal_reason = 'sporttery_offer_no_longer_eligible',
        updated_at = now()
    where job_id = p_job_id
      and state in ('pending', 'predicting');

    insert into public.roundtable_events (job_id, event_type, payload, is_public)
    values (
      p_job_id,
      'roundtable.terminated',
      jsonb_build_object(
        'reason', 'sporttery_offer_no_longer_eligible',
        'eligible_match_count', v_eligible_match_count,
        'match_count', v_match_count,
        'sales_cutoff_at', v_job.sales_cutoff_at
      ),
      false
    )
    returning id, event_seq into v_event_id, v_event_seq;

    return jsonb_build_object(
      'status', 'terminated',
      'job_id', p_job_id,
      'reason', 'sporttery_offer_no_longer_eligible',
      'event_id', v_event_id,
      'event_seq', v_event_seq,
      'phase_count', 0
    );
  end if;

  -- Redelivery is handled by the upserts below. Existing phase rows are reused,
  -- and any missing Outbox rows are repaired before returning duplicate.
  update public.roundtable_jobs
  set state = 'processing_matches',
      state_version = state_version + 1,
      updated_at = now()
  where id = p_job_id
    and state = 'pending';

  update public.roundtable_match_runs
  set state = 'predicting',
      state_version = state_version + 1,
      quorum_instance_count = v_participant_count,
      quorum_provider_count = v_provider_count,
      updated_at = now()
  where job_id = p_job_id
    and state = 'pending';

  insert into public.roundtable_phase_runs (
    job_id,
    match_run_id,
    ai_instance_id,
    phase,
    round_number,
    attempt,
    business_idempotency_key,
    status
  )
  select
    p_job_id,
    match_run.id,
    participant.ai_instance_id,
    'predict_score',
    0,
    1,
    p_job_id::text || ':' || match_run.match_id::text || ':predict_score:0:' || participant.ai_instance_id::text,
    'pending'
  from public.roundtable_match_runs match_run
  cross join public.roundtable_participants participant
  where match_run.job_id = p_job_id
    and participant.job_id = p_job_id
  on conflict (business_idempotency_key) do nothing;
  get diagnostics v_new_phase_count = row_count;

  insert into public.outbox_events (topic, business_idempotency_key, payload)
  select
    'roundtable.predict_score',
    'phase:' || phase_run.business_idempotency_key,
    jsonb_build_object(
      'job_id', p_job_id,
      'match_id', match_run.match_id,
      'phase', 'predict_score',
      'round_number', 0,
      'instance_id', phase_run.ai_instance_id,
      'payload', jsonb_build_object(
        'phase_run_id', phase_run.id,
        'match_run_id', phase_run.match_run_id,
        'job_config', v_job.config_snapshot,
        'participant_config', participant.frozen_config
      )
    )
  from public.roundtable_phase_runs phase_run
  join public.roundtable_match_runs match_run on match_run.id = phase_run.match_run_id
  join public.roundtable_participants participant
    on participant.job_id = p_job_id
   and participant.ai_instance_id = phase_run.ai_instance_id
  where phase_run.job_id = p_job_id
    and phase_run.phase = 'predict_score'
    and phase_run.round_number = 0
    and phase_run.status in ('pending', 'leased', 'running')
  on conflict (business_idempotency_key) do nothing;
  get diagnostics v_new_outbox_count = row_count;

  select count(*) into v_phase_count
  from public.roundtable_phase_runs
  where job_id = p_job_id
    and phase = 'predict_score'
    and round_number = 0;

  if v_new_phase_count = 0 and v_new_outbox_count = 0 then
    return jsonb_build_object(
      'status', 'duplicate',
      'job_id', p_job_id,
      'phase_count', v_phase_count
    );
  end if;

  insert into public.roundtable_events (job_id, event_type, payload, is_public)
  values (
    p_job_id,
    coalesce(nullif(btrim(p_event_type), ''), 'roundtable.worker_acknowledged'),
    coalesce(p_payload, '{}'::jsonb) || jsonb_build_object(
      'status', 'phases_enqueued',
      'phase', 'predict_score',
      'phase_count', v_phase_count,
      'new_phase_count', v_new_phase_count,
      'new_outbox_count', v_new_outbox_count,
      'participant_count', v_participant_count,
      'provider_count', v_provider_count,
      'match_count', v_match_count
    ),
    false
  )
  returning id, event_seq into v_event_id, v_event_seq;

  return jsonb_build_object(
    'status', 'succeeded',
    'job_id', p_job_id,
    'event_id', v_event_id,
    'event_seq', v_event_seq,
    'phase_count', v_phase_count
  );
end;
$$;

revoke all on function public.alea_worker_initialize_roundtable(uuid, text, jsonb) from public;
grant execute on function public.alea_worker_initialize_roundtable(uuid, text, jsonb) to alea_worker;

-- Operational evidence for historical sync coverage.  This is intentionally a
-- coverage view, not a claim that a backfill has already happened.
create or replace view public.alea_sporttery_sync_coverage as
select
  ds.id as data_source_id,
  ds.key as data_source_key,
  ds.kind,
  ds.status,
  ds.authorization_status,
  ds.authorization_reference,
  min(sr.business_date) filter (where sr.state in ('mapped', 'accepted')) as earliest_business_date,
  max(sr.business_date) filter (where sr.state in ('mapped', 'accepted')) as latest_business_date,
  count(distinct sr.id) filter (where sr.state in ('mapped', 'accepted')) as accepted_source_records,
  count(distinct m.id) as canonical_matches,
  count(distinct odds.id) as odds_snapshots,
  count(distinct result.id) as result_versions
from public.data_sources ds
left join public.source_records sr on sr.data_source_id = ds.id
left join public.matches m on m.canonical_source_record_id = sr.id
left join public.match_odds_snapshots odds on odds.source_record_id = sr.id
left join public.match_results result on result.source_record_id = sr.id
where ds.kind in ('sporttery_web', 'licensed_supplier', 'admin_import')
group by
  ds.id,
  ds.key,
  ds.kind,
  ds.status,
  ds.authorization_status,
  ds.authorization_reference;

revoke all on public.alea_sporttery_sync_coverage from public;
grant select on public.alea_sporttery_sync_coverage to alea_api;

create index if not exists matches_eligible_offer_idx
  on public.matches (business_date, kickoff_at, competition_id)
  where sales_status = 'on_sale'
    and fact_state = 'verified'
    and sales_cutoff_at is not null;

create index if not exists source_records_match_lookup_idx
  on public.source_records (data_source_id, business_date, sporttery_match_number, observed_at desc)
  where state in ('mapped', 'accepted');
