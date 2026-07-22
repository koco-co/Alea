-- Persist the post-match boundary instead of treating the Python settlement
-- helpers as evidence of a production settlement.  The worker is the only role
-- allowed to commit this transaction; API reads consume the immutable facts.

alter table public.match_results
  add column if not exists half_home_score integer,
  add column if not exists half_away_score integer;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'match_results_half_scores_non_negative'
  ) then
    alter table public.match_results
      add constraint match_results_half_scores_non_negative
      check (
        (half_home_score is null and half_away_score is null)
        or (half_home_score is not null and half_away_score is not null
            and half_home_score >= 0 and half_away_score >= 0)
      );
  end if;
end;
$$;

create table public.settlement_runs (
  id uuid primary key default gen_random_uuid(),
  notarized_prediction_id uuid not null references public.notarized_predictions(id),
  result_version_id uuid not null references public.match_results(id),
  state text not null check (state in ('settled_hit', 'settled_miss', 'settled_refund', 'corrected')),
  idempotency_key text not null unique,
  completed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (notarized_prediction_id, result_version_id)
);
create index settlement_runs_prediction_idx on public.settlement_runs(notarized_prediction_id);

create table public.simulated_accounts (
  id uuid primary key default gen_random_uuid(),
  owner_type text not null check (owner_type in ('ai_instance', 'consensus')),
  owner_id uuid not null,
  display_name text not null,
  initial_balance numeric(14,2) not null check (initial_balance >= 0),
  current_balance numeric(14,2) not null check (current_balance >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_type, owner_id)
);

create table public.settlement_positions (
  id uuid primary key default gen_random_uuid(),
  settlement_run_id uuid not null references public.settlement_runs(id),
  account_id uuid not null references public.simulated_accounts(id),
  owner_type text not null check (owner_type in ('ai_instance', 'consensus')),
  owner_id uuid not null,
  decision text not null check (decision in ('bet', 'no_bet')),
  plan_source_instance_id uuid references public.ai_instances(id),
  is_platform_winner boolean not null default false,
  stake numeric(14,2) not null check (stake >= 0),
  created_at timestamptz not null default now(),
  unique (settlement_run_id, owner_type, owner_id),
  check ((decision = 'no_bet' and stake = 0) or decision = 'bet'),
  check ((owner_type = 'ai_instance' and plan_source_instance_id = owner_id)
      or (owner_type = 'consensus' and plan_source_instance_id is null))
);

create table public.simulated_account_entries (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references public.simulated_accounts(id),
  settlement_run_id uuid not null references public.settlement_runs(id),
  result_version_id uuid not null references public.match_results(id),
  entry_type text not null check (entry_type in ('stake', 'refund', 'payout', 'reversal')),
  amount numeric(14,2) not null check (amount <> 0),
  balance_after numeric(14,2) not null check (balance_after >= 0),
  reverses_entry_id uuid references public.simulated_account_entries(id),
  created_at timestamptz not null default now(),
  unique (account_id, settlement_run_id, entry_type),
  check (entry_type <> 'reversal' or reverses_entry_id is not null)
);

create table public.ranking_facts (
  id uuid primary key default gen_random_uuid(),
  settlement_run_id uuid not null references public.settlement_runs(id),
  notarized_prediction_id uuid not null references public.notarized_predictions(id),
  result_version_id uuid not null references public.match_results(id),
  ai_instance_id uuid not null references public.ai_instances(id),
  match_id uuid not null,
  formula_version_id uuid not null references public.score_formula_versions(id),
  predicted_full_home integer not null check (predicted_full_home >= 0),
  predicted_full_away integer not null check (predicted_full_away >= 0),
  predicted_half_home integer not null check (predicted_half_home >= 0),
  predicted_half_away integer not null check (predicted_half_away >= 0),
  actual_full_home integer not null check (actual_full_home >= 0),
  actual_full_away integer not null check (actual_full_away >= 0),
  actual_half_home integer not null check (actual_half_home >= 0),
  actual_half_away integer not null check (actual_half_away >= 0),
  direction_confidence numeric(5,2) not null check (direction_confidence between 0 and 100),
  exact_score_hit boolean not null,
  direction_hit boolean not null,
  total_goals_hit boolean not null,
  half_full_hit boolean not null,
  created_at timestamptz not null default now(),
  unique (notarized_prediction_id, result_version_id, ai_instance_id)
);
create index ranking_facts_instance_idx on public.ranking_facts(ai_instance_id, created_at desc);
create index ranking_facts_formula_idx on public.ranking_facts(formula_version_id);

create or replace function public.alea_score_direction(p_home integer, p_away integer)
returns text
language sql
immutable
strict
as $$
  select case when p_home > p_away then 'home'
              when p_home < p_away then 'away'
              else 'draw' end;
$$;

create or replace function public.settle_notarized_prediction(
  p_notarized_prediction_id uuid,
  p_result_version_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_prediction public.notarized_predictions%rowtype;
  v_match_run public.roundtable_match_runs%rowtype;
  v_job public.roundtable_jobs%rowtype;
  v_result public.match_results%rowtype;
  v_run public.settlement_runs%rowtype;
  v_run_id uuid;
  v_result_state text := 'settled_refund';
  v_initial_balance numeric(14,2);
  v_account_id uuid;
  v_owner_id uuid;
  v_decision text;
  v_stake numeric(14,2);
  v_vote_count integer;
  v_bet_count integer;
  v_row record;
  v_payload jsonb;
  v_full_home integer;
  v_full_away integer;
  v_half_home integer;
  v_half_away integer;
  v_actual_half_dir text;
  v_actual_full_dir text;
  v_pred_half_dir text;
  v_pred_full_dir text;
  v_entry_ids jsonb;
  v_outbox_ids jsonb;
  v_inserted boolean := false;
begin
  if session_user <> 'alea_worker'
     and coalesce(current_setting('role', true), 'none') <> 'alea_worker' then
    raise exception 'settle_notarized_prediction requires alea_worker' using errcode = '42501';
  end if;

  select * into v_prediction
  from public.notarized_predictions
  where id = p_notarized_prediction_id
  for update;
  if not found then
    raise exception 'notarized prediction not found' using errcode = 'P0002';
  end if;

  select * into v_match_run
  from public.roundtable_match_runs
  where id = v_prediction.match_run_id
  for update;
  select * into v_job from public.roundtable_jobs where id = v_prediction.job_id;

  select mr.* into v_result
  from public.match_results mr
  join public.matches m on m.id = mr.match_id
  join public.source_records sr on sr.id = mr.source_record_id
  where mr.id = p_result_version_id
    and mr.match_id = v_match_run.match_id
    and mr.status = 'confirmed'
    and mr.half_home_score is not null
    and mr.half_away_score is not null
    and m.fact_state = 'verified'
    and m.sales_status in ('closed', 'settled')
    and m.kickoff_at <= now()
    and public.alea_is_authorized_sporttery_source(
      sr.data_source_id, array['caching', 'public_display']::text[]
    );
  if not found then
    raise exception 'confirmed_authorized_result_required' using errcode = '23514';
  end if;

  insert into public.settlement_runs(
    notarized_prediction_id, result_version_id, state, idempotency_key
  ) values (
    p_notarized_prediction_id,
    p_result_version_id,
    v_result_state,
    'settle:' || p_notarized_prediction_id::text || ':' || p_result_version_id::text
  ) on conflict (notarized_prediction_id, result_version_id) do nothing;
  v_inserted := found;
  select * into v_run
  from public.settlement_runs
  where notarized_prediction_id = p_notarized_prediction_id
    and result_version_id = p_result_version_id
  for update;
  v_run_id := v_run.id;

  if not v_inserted then
    select coalesce(jsonb_agg(id order by id), '[]'::jsonb) into v_entry_ids
    from public.simulated_account_entries where settlement_run_id = v_run_id;
    select coalesce(jsonb_agg(id order by id), '[]'::jsonb) into v_outbox_ids
    from public.outbox_events where business_idempotency_key like 'settlement:' || v_run_id::text || ':%';
    return jsonb_build_object(
      'settlement_run_id', v_run_id,
      'notarized_prediction_id', p_notarized_prediction_id,
      'result_version_id', p_result_version_id,
      'state', v_run.state,
      'idempotent_replay', true,
      'account_entry_ids', v_entry_ids,
      'outbox_event_ids', v_outbox_ids
    );
  end if;

  v_initial_balance := coalesce((
    select nullif(value->>'initial_balance', '')::numeric
    from public.system_setting_versions
    where key = 'risk_limits'
    order by version desc limit 1
  ), 10000);

  -- One immutable hit fact per score-vote participant.  The payload is validated
  -- here again because provider output is untrusted even after schema validation.
  for v_row in
    select r.ai_instance_id, r.payload
    from public.roundtable_results r
    where r.job_id = v_prediction.job_id
      and r.match_run_id = v_prediction.match_run_id
      and r.phase = 'score_vote'
    order by r.ai_instance_id
  loop
    begin
      v_payload := v_row.payload;
      v_full_home := (v_payload#>>'{full_time_score,home}')::integer;
      v_full_away := (v_payload#>>'{full_time_score,away}')::integer;
      v_half_home := (v_payload#>>'{half_time_score,home}')::integer;
      v_half_away := (v_payload#>>'{half_time_score,away}')::integer;
    exception when others then
      raise exception 'score_vote_payload_invalid' using errcode = '22023';
    end;
    if least(v_full_home, v_full_away, v_half_home, v_half_away) < 0 then
      raise exception 'score_vote_payload_invalid' using errcode = '22023';
    end if;
    v_pred_half_dir := public.alea_score_direction(v_half_home, v_half_away);
    v_pred_full_dir := public.alea_score_direction(v_full_home, v_full_away);
    v_actual_half_dir := public.alea_score_direction(v_result.half_home_score, v_result.half_away_score);
    v_actual_full_dir := public.alea_score_direction(v_result.home_score, v_result.away_score);
    insert into public.ranking_facts(
      settlement_run_id, notarized_prediction_id, result_version_id, ai_instance_id,
      match_id, formula_version_id, predicted_full_home, predicted_full_away,
      predicted_half_home, predicted_half_away, actual_full_home, actual_full_away,
      actual_half_home, actual_half_away, direction_confidence, exact_score_hit,
      direction_hit, total_goals_hit, half_full_hit
    ) values (
      v_run_id, p_notarized_prediction_id, p_result_version_id, v_row.ai_instance_id,
      v_match_run.match_id, v_job.score_formula_version_id, v_full_home, v_full_away,
      v_half_home, v_half_away, v_result.home_score, v_result.away_score,
      v_result.half_home_score, v_result.half_away_score,
      coalesce((v_payload->>'direction_confidence')::numeric, 0),
      v_full_home = v_result.home_score and v_full_away = v_result.away_score,
      v_pred_full_dir = v_actual_full_dir,
      v_full_home + v_full_away = v_result.home_score + v_result.away_score,
      v_pred_half_dir = v_actual_half_dir and v_pred_full_dir = v_actual_full_dir
    ) on conflict (notarized_prediction_id, result_version_id, ai_instance_id) do nothing;

    insert into public.simulated_accounts(owner_type, owner_id, display_name, initial_balance, current_balance)
    select 'ai_instance', instance.id, instance.nickname, v_initial_balance, v_initial_balance
    from public.ai_instances instance
    where instance.id = v_row.ai_instance_id
    on conflict (owner_type, owner_id) do nothing
    returning id into v_account_id;
    if v_account_id is null then
      select id into v_account_id from public.simulated_accounts
      where owner_type = 'ai_instance' and owner_id = v_row.ai_instance_id;
    end if;
    insert into public.settlement_positions(
      settlement_run_id, account_id, owner_type, owner_id, decision,
      plan_source_instance_id, is_platform_winner, stake
    ) values (
      v_run_id, v_account_id, 'ai_instance', v_row.ai_instance_id, 'no_bet',
      v_row.ai_instance_id, false, 0
    ) on conflict (settlement_run_id, owner_type, owner_id) do nothing;
  end loop;

  select count(*) into v_vote_count
  from public.roundtable_results
  where job_id = v_prediction.job_id and match_run_id is null and phase = 'bet_vote';
  select count(*) into v_bet_count
  from public.roundtable_results
  where job_id = v_prediction.job_id and match_run_id is null and phase = 'bet_vote'
    and payload->>'decision' = 'bet';

  insert into public.simulated_accounts(owner_type, owner_id, display_name, initial_balance, current_balance)
  values ('consensus', v_prediction.job_id, '圆桌共识', v_initial_balance, v_initial_balance)
  on conflict (owner_type, owner_id) do nothing
  returning id into v_account_id;
  if v_account_id is null then
    select id into v_account_id from public.simulated_accounts
    where owner_type = 'consensus' and owner_id = v_prediction.job_id;
  end if;
  v_decision := case when v_vote_count > 0 and v_bet_count * 2 >= v_vote_count then 'bet' else 'no_bet' end;
  v_stake := case when v_decision = 'bet' then round(v_initial_balance * 0.01, 2) else 0 end;
  insert into public.settlement_positions(
    settlement_run_id, account_id, owner_type, owner_id, decision,
    plan_source_instance_id, is_platform_winner, stake
  ) values (
    v_run_id, v_account_id, 'consensus', v_prediction.job_id, v_decision,
    null, v_decision = 'bet', v_stake
  );

  -- No-bet is a valid settled decision and creates no money entry.  A future
  -- ticket payout extension must append entries here, never mutate this run.
  insert into public.outbox_events(topic, business_idempotency_key, payload)
  values
    ('ranking.recompute', 'settlement:' || v_run_id::text || ':ranking',
      jsonb_build_object('settlement_run_id', v_run_id, 'formula_version_id', v_job.score_formula_version_id)),
    ('prediction.review', 'settlement:' || v_run_id::text || ':review',
      jsonb_build_object('settlement_run_id', v_run_id, 'notarized_prediction_id', p_notarized_prediction_id))
  on conflict (business_idempotency_key) do nothing;

  select coalesce(jsonb_agg(id order by id), '[]'::jsonb) into v_entry_ids
  from public.simulated_account_entries where settlement_run_id = v_run_id;
  select coalesce(jsonb_agg(id order by id), '[]'::jsonb) into v_outbox_ids
  from public.outbox_events where business_idempotency_key like 'settlement:' || v_run_id::text || ':%';
  return jsonb_build_object(
    'settlement_run_id', v_run_id,
    'notarized_prediction_id', p_notarized_prediction_id,
    'result_version_id', p_result_version_id,
    'state', v_result_state,
    'idempotent_replay', false,
    'account_entry_ids', v_entry_ids,
    'outbox_event_ids', v_outbox_ids
  );
end;
$$;

create or replace function public.alea_query_list_rankings(
  p_viewer_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_viewer uuid := nullif(btrim(coalesce(p_viewer_id, '')), '')::uuid;
  v_formula uuid;
  v_formula_config jsonb;
  v_dimension text := coalesce(p_payload->>'dimension', 'composite');
  v_rows jsonb;
begin
  if v_viewer is null or not exists (select 1 from profiles where id = v_viewer and status = 'active') then
    raise exception 'ranking query requires an authenticated viewer' using errcode = '42501';
  end if;
  if v_dimension not in ('composite', 'exact_score', 'direction', 'total_goals', 'half_full') then
    raise exception 'invalid ranking dimension' using errcode = '22023';
  end if;
  v_formula := nullif(p_payload->>'formula_version_id', '')::uuid;
  if v_formula is null then
    select id, config into v_formula, v_formula_config
    from score_formula_versions order by version desc limit 1;
  else
    select id, config into v_formula, v_formula_config
    from score_formula_versions where id = v_formula;
  end if;
  if v_formula is null then raise exception 'ranking formula not found' using errcode = 'P0002'; end if;

  with fact_rows as (
    select f.ai_instance_id,
      count(*)::numeric as settled_count,
      avg(case when f.exact_score_hit then 1 else 0 end)::numeric as exact_rate,
      avg(case when f.direction_hit then 1 else 0 end)::numeric as direction_rate,
      avg(case when f.total_goals_hit then 1 else 0 end)::numeric as total_goals_rate,
      avg(case when f.half_full_hit then 1 else 0 end)::numeric as half_full_rate
    from ranking_facts f
    where f.formula_version_id = v_formula
    group by f.ai_instance_id
  ), eligible_rows as (
    select rp.ai_instance_id, count(distinct mr.match_id)::numeric as eligible_count
    from roundtable_participants rp
    join roundtable_match_runs mr on mr.job_id = rp.job_id
      and mr.state in ('eligible')
    group by rp.ai_instance_id
  ), base as (
    select i.id as ai_instance_id, i.nickname as display_name,
      v_formula as formula_version_id,
      coalesce(fr.settled_count, 0)::numeric as settled_count,
      coalesce(er.eligible_count, coalesce(fr.settled_count, 0))::numeric as eligible_count,
      coalesce(fr.exact_rate, 0)::numeric as exact_rate,
      coalesce(fr.direction_rate, 0)::numeric as direction_rate,
      coalesce(fr.total_goals_rate, 0)::numeric as total_goals_rate,
      coalesce(fr.half_full_rate, 0)::numeric as half_full_rate,
      p.family
    from ai_instances i
    join ai_providers p on p.id = i.provider_id
    left join fact_rows fr on fr.ai_instance_id = i.id
    left join eligible_rows er on er.ai_instance_id = i.id
    where i.enabled or fr.ai_instance_id is not null
  ), scored as (
    select b.*, (
      b.exact_rate * coalesce((v_formula_config#>>'{dimensions,exact_score}')::numeric, .40)
      + b.direction_rate * coalesce((v_formula_config#>>'{dimensions,direction}')::numeric, .30)
      + b.total_goals_rate * coalesce((v_formula_config#>>'{dimensions,total_goals}')::numeric, .15)
      + b.half_full_rate * coalesce((v_formula_config#>>'{dimensions,half_full}')::numeric, .15)
    ) * 100 as raw_score,
    case v_dimension
      when 'exact_score' then b.exact_rate
      when 'direction' then b.direction_rate
      when 'total_goals' then b.total_goals_rate
      when 'half_full' then b.half_full_rate
      else (
        b.exact_rate * coalesce((v_formula_config#>>'{dimensions,exact_score}')::numeric, .40)
        + b.direction_rate * coalesce((v_formula_config#>>'{dimensions,direction}')::numeric, .30)
        + b.total_goals_rate * coalesce((v_formula_config#>>'{dimensions,total_goals}')::numeric, .15)
        + b.half_full_rate * coalesce((v_formula_config#>>'{dimensions,half_full}')::numeric, .15)
      )
    end * 100 as selected_score
    from base b
  ), scored_with_prior as (
    select s.*, coalesce(avg(s.raw_score) filter (where s.settled_count > 0) over (),
      (v_formula_config->>'cold_start_prior')::numeric, 50) as prior_mean
    from scored s
  ), ranked as (
    select s.*, (
      s.settled_count * s.selected_score
      + coalesce((v_formula_config->>'prior_sample_count')::numeric, 10) * s.prior_mean
    ) / nullif(s.settled_count + coalesce((v_formula_config->>'prior_sample_count')::numeric, 10), 0) as smoothed_score
    from scored_with_prior s
  ), numbered as (
    select r.*, case when r.settled_count >= coalesce((v_formula_config->>'minimum_settled')::numeric, 10)
      and r.settled_count / nullif(r.eligible_count, 0) >= coalesce((v_formula_config->>'minimum_coverage')::numeric, .8)
      then row_number() over (order by r.smoothed_score desc, r.ai_instance_id)::integer end as rank_value
    from ranked r
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'ai_instance_id', n.ai_instance_id,
    'display_name', n.display_name,
    'formula_version_id', n.formula_version_id,
    'settled_count', n.settled_count::integer,
    'participation_coverage', coalesce(least(1, n.settled_count / nullif(n.eligible_count, 0)), 0),
    'raw_score', n.raw_score,
    'smoothed_score', n.smoothed_score,
    'exact_score_rate', n.exact_rate,
    'direction_rate', n.direction_rate,
    'total_goals_rate', n.total_goals_rate,
    'half_full_rate', n.half_full_rate,
    'eligible_for_rank', n.rank_value is not null,
    'eligibility_reasons', case
      when n.settled_count < coalesce((v_formula_config->>'minimum_settled')::numeric, 10)
        then jsonb_build_array('insufficient_sample')
      when n.settled_count / nullif(n.eligible_count, 0) < coalesce((v_formula_config->>'minimum_coverage')::numeric, .8)
        then jsonb_build_array('insufficient_coverage')
      else '[]'::jsonb end,
    'rank', n.rank_value
  ) order by n.rank_value nulls last, n.smoothed_score desc, n.ai_instance_id), '[]'::jsonb)
  into v_rows from numbered n;
  return v_rows;
end;
$$;

create or replace function public.alea_query_ranking_profile(
  p_viewer_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_viewer uuid := nullif(btrim(coalesce(p_viewer_id, '')), '')::uuid;
  v_instance uuid := nullif(p_payload->>'ai_instance_id', '')::uuid;
  v_rows jsonb;
begin
  if v_viewer is null or not exists (select 1 from profiles where id = v_viewer and status = 'active') then
    raise exception 'ranking query requires an authenticated viewer' using errcode = '42501';
  end if;
  if v_instance is null or not exists (select 1 from ai_instances where id = v_instance) then
    return null;
  end if;
  select coalesce(jsonb_agg(jsonb_build_object(
    'result_version_id', f.result_version_id,
    'match_id', f.match_id,
    'exact_score_hit', f.exact_score_hit,
    'direction_hit', f.direction_hit,
    'total_goals_hit', f.total_goals_hit,
    'half_full_hit', f.half_full_hit,
    'direction_confidence', f.direction_confidence,
    'created_at', f.created_at
  ) order by f.created_at desc), '[]'::jsonb)
  into v_rows from ranking_facts f where f.ai_instance_id = v_instance;
  return jsonb_build_object('ai_instance_id', v_instance, 'facts', v_rows);
end;
$$;

create or replace function public.queue_settlement_for_prediction(
  p_notarized_prediction_id uuid,
  p_result_version_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_outbox_id uuid;
begin
  insert into public.outbox_events(topic, business_idempotency_key, payload)
  values (
    'settlement.run',
    'settlement-request:' || p_notarized_prediction_id::text || ':' || p_result_version_id::text,
    jsonb_build_object(
      'notarized_prediction_id', p_notarized_prediction_id,
      'result_version_id', p_result_version_id
    )
  )
  on conflict (business_idempotency_key) do update
    set payload = excluded.payload
  returning id into v_outbox_id;
  return v_outbox_id;
end;
$$;

create or replace function public.queue_settlement_after_result()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if new.status = 'confirmed' then
    insert into public.outbox_events(topic, business_idempotency_key, payload)
    select
      'settlement.run',
      'settlement-request:' || n.id::text || ':' || new.id::text,
      jsonb_build_object(
        'notarized_prediction_id', n.id,
        'result_version_id', new.id
      )
    from public.notarized_predictions n
    join public.roundtable_match_runs mr on mr.id = n.match_run_id
    where mr.match_id = new.match_id
    on conflict (business_idempotency_key) do nothing;
  end if;
  return new;
end;
$$;

create or replace function public.queue_settlement_after_notarization()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  insert into public.outbox_events(topic, business_idempotency_key, payload)
  select
    'settlement.run',
    'settlement-request:' || new.id::text || ':' || result.id::text,
    jsonb_build_object(
      'notarized_prediction_id', new.id,
      'result_version_id', result.id
    )
  from public.match_results result
  join public.roundtable_match_runs mr on mr.id = new.match_run_id
  where result.match_id = mr.match_id
    and result.status = 'confirmed'
  on conflict (business_idempotency_key) do nothing;
  return new;
end;
$$;

create trigger queue_settlement_after_result_trigger
after insert or update of status on public.match_results
for each row execute function public.queue_settlement_after_result();
create trigger queue_settlement_after_notarization_trigger
after insert on public.notarized_predictions
for each row execute function public.queue_settlement_after_notarization();

alter table public.settlement_runs enable row level security;
alter table public.simulated_accounts enable row level security;
alter table public.settlement_positions enable row level security;
alter table public.simulated_account_entries enable row level security;
alter table public.ranking_facts enable row level security;

create policy worker_settlement_runs_all on public.settlement_runs
  for all to alea_worker using (true) with check (true);
create policy worker_simulated_accounts_all on public.simulated_accounts
  for all to alea_worker using (true) with check (true);
create policy worker_settlement_positions_all on public.settlement_positions
  for all to alea_worker using (true) with check (true);
create policy worker_account_entries_all on public.simulated_account_entries
  for all to alea_worker using (true) with check (true);
create policy worker_ranking_facts_all on public.ranking_facts
  for all to alea_worker using (true) with check (true);
create policy worker_settlement_prediction_read on public.notarized_predictions
  for select to alea_worker using (true);
create policy worker_settlement_match_run_read on public.roundtable_match_runs
  for select to alea_worker using (true);
create policy worker_settlement_job_read on public.roundtable_jobs
  for select to alea_worker using (true);
create policy worker_settlement_result_read on public.match_results
  for select to alea_worker using (true);
create policy worker_settlement_match_read on public.matches
  for select to alea_worker using (true);
create policy worker_settlement_source_read on public.source_records
  for select to alea_worker using (true);
create policy worker_settlement_data_source_read on public.data_sources
  for select to alea_worker using (true);
create policy worker_settlement_participant_read on public.roundtable_participants
  for select to alea_worker using (true);
create policy worker_settlement_result_rows_read on public.roundtable_results
  for select to alea_worker using (true);
create policy worker_settlement_ai_read on public.ai_instances
  for select to alea_worker using (true);
create policy worker_settlement_provider_read on public.ai_providers
  for select to alea_worker using (true);
create policy worker_settlement_formula_read on public.score_formula_versions
  for select to alea_worker using (true);
create policy worker_settlement_settings_read on public.system_setting_versions
  for select to alea_worker using (true);
create policy api_ranking_facts_read on public.ranking_facts
  for select to alea_api using (true);

revoke all on public.settlement_runs, public.simulated_accounts,
  public.settlement_positions, public.simulated_account_entries,
  public.ranking_facts from public, anon, authenticated;
grant select on public.ranking_facts to alea_api;
grant select, insert, update on public.settlement_runs, public.simulated_accounts,
  public.settlement_positions, public.simulated_account_entries,
  public.ranking_facts to alea_worker;
grant select on public.notarized_predictions, public.roundtable_match_runs,
  public.roundtable_jobs, public.match_results, public.matches,
  public.source_records, public.data_sources, public.roundtable_participants,
  public.roundtable_results, public.ai_instances, public.ai_providers,
  public.score_formula_versions, public.system_setting_versions to alea_worker;
grant execute on function public.settle_notarized_prediction(uuid, uuid) to alea_worker;
grant execute on function public.queue_settlement_for_prediction(uuid, uuid) to alea_worker;
grant execute on function public.alea_query_list_rankings(text, jsonb) to alea_api;
grant execute on function public.alea_query_ranking_profile(text, jsonb) to alea_api;
revoke all on function public.settle_notarized_prediction(uuid, uuid) from public, anon, authenticated;
revoke all on function public.queue_settlement_for_prediction(uuid, uuid) from public, anon, authenticated;
revoke all on function public.alea_query_list_rankings(text, jsonb) from public, anon, authenticated;
revoke all on function public.alea_query_ranking_profile(text, jsonb) from public, anon, authenticated;

create trigger settlement_runs_immutable
before update or delete on public.settlement_runs
for each row execute function reject_immutable_mutation();
create trigger settlement_positions_immutable
before update or delete on public.settlement_positions
for each row execute function reject_immutable_mutation();
create trigger simulated_account_entries_immutable
before update or delete on public.simulated_account_entries
for each row execute function reject_immutable_mutation();
create trigger ranking_facts_immutable
before update or delete on public.ranking_facts
for each row execute function reject_immutable_mutation();
