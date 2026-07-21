-- Connect the admin roundtable flow to the durable job/event/outbox model.
-- This migration intentionally does not bypass provider health checks or RLS.

create or replace function alea_query_roundtable(
  p_actor_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_job_id uuid;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  begin
    v_job_id := (p_params->>'job_id')::uuid;
  exception when invalid_text_representation then
    raise exception 'invalid roundtable job id' using errcode = '22023';
  end;

  if v_job_id is null then
    raise exception 'job_id is required' using errcode = '22023';
  end if;

  return coalesce((
    select jsonb_build_object(
      'job', jsonb_build_object(
        'id', j.id,
        'job_type', j.job_type,
        'state', j.state,
        'state_version', j.state_version,
        'business_idempotency_key', j.business_idempotency_key,
        'config_snapshot', j.config_snapshot,
        'sales_cutoff_at', j.sales_cutoff_at,
        'terminal_reason', j.terminal_reason,
        'created_by', j.created_by,
        'created_at', j.created_at,
        'updated_at', j.updated_at
      ),
      'participants', coalesce((
        select jsonb_agg(
          jsonb_build_object(
            'id', rp.id,
            'ai_instance_id', rp.ai_instance_id,
            'provider_family', rp.provider_family,
            'codename', rp.codename,
            'score', rp.score,
            'raw_weight', rp.raw_weight,
            'normalized_weight', rp.normalized_weight,
            'frozen_config', rp.frozen_config,
            'nickname', i.nickname,
            'model_id', i.model_id,
            'enabled', i.enabled,
            'provider_key', p.key,
            'provider_name', p.display_name,
            'connection_version', c.version,
            'connection_test_status', c.test_status,
            'health_status', h.status,
            'auth_status', h.auth_status
          ) order by rp.codename
        )
        from roundtable_participants rp
        join ai_instances i on i.id = rp.ai_instance_id
        join ai_providers p on p.id = i.provider_id
        join provider_connections c on c.id = i.connection_id
        left join provider_connection_health h
          on h.connection_id = c.id and h.connection_version = c.version
        where rp.job_id = j.id
      ), '[]'::jsonb),
      'match_runs', coalesce((
        select jsonb_agg(
          jsonb_build_object(
            'id', mr.id,
            'match_id', mr.match_id,
            'state', mr.state,
            'state_version', mr.state_version,
            'quorum_instance_count', mr.quorum_instance_count,
            'quorum_provider_count', mr.quorum_provider_count
          ) order by mr.created_at, mr.id
        )
        from roundtable_match_runs mr
        where mr.job_id = j.id
      ), '[]'::jsonb)
    )
    from roundtable_jobs j
    where j.id = v_job_id
      and (j.created_by = v_actor_id or exists (
        select 1 from profiles p where p.id = v_actor_id and p.role = 'admin'
      ))
  ), jsonb_build_object('job', null, 'participants', '[]'::jsonb, 'match_runs', '[]'::jsonb));
end;
$$;

create or replace function alea_query_list_roundtables(
  p_actor_id text,
  p_params jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_limit integer;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_limit := least(greatest(coalesce((p_params->>'limit')::integer, 20), 1), 100);
  return jsonb_build_object(
    'jobs', coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'id', j.id,
          'job_type', j.job_type,
          'state', j.state,
          'state_version', j.state_version,
          'config_snapshot', j.config_snapshot,
          'created_at', j.created_at,
          'updated_at', j.updated_at,
          'participant_count', (select count(*) from roundtable_participants rp where rp.job_id = j.id),
          'match_count', (select count(*) from roundtable_match_runs mr where mr.job_id = j.id)
        ) order by j.created_at desc
      )
      from (
        select * from roundtable_jobs
        where created_by = v_actor_id
        order by created_at desc
        limit v_limit
      ) j
    ), '[]'::jsonb)
  );
end;
$$;

create or replace function alea_command_start_roundtable(
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
  v_actor_id uuid;
  v_job_id uuid;
  v_existing_job_id uuid;
  v_business_date date;
  v_mode text := coalesce(p_payload->>'mode', 'autonomous');
  v_rounds integer := coalesce((p_payload->>'rounds')::integer, 1);
  v_candidate_limit integer := least(greatest(coalesce((p_payload->>'candidate_limit')::integer, 8), 1), 20);
  v_instance_ids uuid[];
  v_match_ids uuid[];
  v_requested_match_count integer := jsonb_array_length(coalesce(p_payload->'match_ids', '[]'::jsonb));
  v_key text;
  v_score_formula_id uuid;
  v_rule_id uuid;
  v_history_id uuid;
  v_match_id uuid;
  v_instance_id uuid;
  v_index integer := 0;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  if p_request_id is null or length(trim(p_request_id)) = 0 then
    raise exception 'request id is required' using errcode = '22023';
  end if;
  if v_mode not in ('autonomous', 'specified') then
    raise exception 'invalid roundtable mode' using errcode = '22023';
  end if;
  if p_payload->>'business_date' is null then
    raise exception 'business_date is required' using errcode = '22023';
  end if;
  begin
    v_business_date := (p_payload->>'business_date')::date;
  exception when invalid_text_representation then
    raise exception 'invalid business_date' using errcode = '22023';
  end;
  if v_rounds not between 1 and 2 then
    raise exception 'rounds must be between 1 and 2' using errcode = '22023';
  end if;
  if jsonb_typeof(coalesce(p_payload->'instance_ids', '[]'::jsonb)) <> 'array' then
    raise exception 'instance_ids must be an array' using errcode = '22023';
  end if;
  v_instance_ids := array(
    select value::uuid from jsonb_array_elements_text(p_payload->'instance_ids')
  );
  if coalesce(array_length(v_instance_ids, 1), 0) not between 1 and 3 then
    raise exception 'one to three instances are required' using errcode = '22023';
  end if;
  if v_mode = 'specified' then
    if v_requested_match_count = 0 then
      raise exception 'specified mode requires match_ids' using errcode = '22023';
    end if;
    v_match_ids := array(
      select value::uuid from jsonb_array_elements_text(p_payload->'match_ids')
    );
    if array_length(v_match_ids, 1) <> v_requested_match_count then
      raise exception 'match_ids contains invalid UUID' using errcode = '22023';
    end if;
    if exists (
      select 1 from matches m
      where m.id = any(v_match_ids) and m.sales_status = 'cancelled'
    ) or (select count(*) from matches m where m.id = any(v_match_ids)) <> v_requested_match_count then
      raise exception 'selected match is unavailable' using errcode = '40901';
    end if;
  else
    v_match_ids := array(
      select m.id
      from matches m
      where m.business_date = v_business_date
        and m.sales_status <> 'cancelled'
      order by m.kickoff_at, m.id
      limit v_candidate_limit
    );
  end if;

  if exists (
    select 1
    from unnest(v_instance_ids) selected(id)
    left join ai_instances i on i.id = selected.id
    left join ai_providers p on p.id = i.provider_id
    left join provider_connections c on c.id = i.connection_id
    left join provider_connection_health h
      on h.connection_id = c.id and h.connection_version = c.version
    where i.id is null
      or not i.enabled
      or not p.enabled
      or c.enabled is not true
      or c.test_status <> 'passed'
      or h.status <> 'passed'
      or (c.execution_mode::text = 'cli' and h.auth_status <> 'authenticated')
  ) then
    raise exception 'selected instance is not qualified' using errcode = '40902';
  end if;

  select id into v_score_formula_id
  from score_formula_versions
  where effective_at <= now()
  order by effective_at desc, version desc limit 1;
  select id into v_rule_id
  from sporttery_rule_versions
  where effective_at <= now()
  order by effective_at desc, version desc limit 1;
  select id into v_history_id
  from system_setting_versions
  where key = 'history_context_limits' and effective_at <= now()
  order by effective_at desc, version desc limit 1;
  if v_score_formula_id is null or v_rule_id is null or v_history_id is null then
    raise exception 'roundtable_versions_unavailable' using errcode = '42404';
  end if;

  v_key := 'roundtable:' || v_business_date::text || ':' ||
    substr(encode(digest(convert_to(p_payload::text, 'utf8'), 'sha256'), 'hex'), 1, 32);
  select id into v_existing_job_id
  from roundtable_jobs
  where job_type = 'prediction' and business_idempotency_key = v_key;
  if v_existing_job_id is not null then
    return jsonb_build_object(
      'job_id', v_existing_job_id,
      'state', (select state from roundtable_jobs where id = v_existing_job_id),
      'business_idempotency_key', v_key,
      'idempotent', true
    );
  end if;

  v_job_id := gen_random_uuid();
  insert into roundtable_jobs (
    id, job_type, state, state_version, business_idempotency_key, config_snapshot,
    score_formula_version_id, sporttery_rule_version_id, history_context_limits_version_id,
    created_by
  ) values (
    v_job_id, 'prediction', 'pending', 0, v_key,
    jsonb_build_object(
      'mode', v_mode,
      'business_date', v_business_date,
      'competition_scope', coalesce(p_payload->>'competition_scope', 'all'),
      'excluded_match_ids', coalesce(p_payload->'excluded_match_ids', '[]'::jsonb),
      'match_ids', to_jsonb(coalesce(v_match_ids, '{}'::uuid[])),
      'instance_ids', to_jsonb(v_instance_ids),
      'rounds', v_rounds,
      'candidate_limit', v_candidate_limit,
      'scheduled', coalesce((p_payload->>'scheduled')::boolean, false),
      'schedule_time', coalesce(p_payload->>'schedule_time', '08:00'),
      'request_id', p_request_id
    ),
    v_score_formula_id, v_rule_id, v_history_id, v_actor_id
  );

  foreach v_match_id in array coalesce(v_match_ids, '{}'::uuid[]) loop
    insert into roundtable_match_runs (job_id, match_id)
    values (v_job_id, v_match_id);
  end loop;

  foreach v_instance_id in array v_instance_ids loop
    v_index := v_index + 1;
    insert into roundtable_participants (
      job_id, ai_instance_id, provider_family, codename, score, raw_weight,
      normalized_weight, frozen_config
    )
    select
      v_job_id, i.id, p.family, '选手 ' || chr(64 + v_index), 0, 1,
      1.0 / array_length(v_instance_ids, 1),
      jsonb_build_object(
        'provider_key', p.key,
        'provider_id', p.id,
        'connection_id', c.id,
        'connection_version', c.version,
        'execution_mode', c.execution_mode,
        'runtime_key', c.runtime_key,
        'executable_path', c.executable_path,
        'model_id', i.model_id,
        'reasoning_level', i.reasoning_level,
        'timeout_seconds', i.timeout_seconds,
        'max_concurrency', i.max_concurrency,
        'prompt_version', i.prompt_version
      )
    from ai_instances i
    join ai_providers p on p.id = i.provider_id
    join provider_connections c on c.id = i.connection_id
    where i.id = v_instance_id;
  end loop;

  insert into roundtable_events (job_id, event_type, payload, is_public)
  values (
    v_job_id,
    'roundtable.started',
    jsonb_build_object(
      'status', 'pending',
      'mode', v_mode,
      'participant_count', array_length(v_instance_ids, 1),
      'match_count', coalesce(array_length(v_match_ids, 1), 0),
      'rounds', v_rounds
    ),
    false
  );

  insert into outbox_events (topic, business_idempotency_key, payload)
  values (
    'roundtable.lifecycle',
    'roundtable-start:' || v_job_id::text,
    jsonb_build_object(
      'job_id', v_job_id,
      'event_type', 'roundtable.worker_acknowledged',
      'payload', jsonb_build_object('status', 'worker_received')
    )
  );

  return jsonb_build_object(
    'job_id', v_job_id,
    'state', 'pending',
    'business_idempotency_key', v_key,
    'idempotent', false,
    'participant_count', array_length(v_instance_ids, 1),
    'match_count', coalesce(array_length(v_match_ids, 1), 0)
  );
end;
$$;

create or replace function alea_worker_append_roundtable_event(
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
  v_event_id uuid;
  v_event_seq bigint;
begin
  if session_user <> 'alea_worker' then
    raise exception 'worker role required' using errcode = '42501';
  end if;
  insert into roundtable_events (job_id, event_type, payload, is_public)
  values (p_job_id, p_event_type, coalesce(p_payload, '{}'::jsonb), false)
  returning id, event_seq into v_event_id, v_event_seq;
  return jsonb_build_object('event_id', v_event_id, 'event_seq', v_event_seq);
end;
$$;

revoke all on function alea_query_roundtable(text, jsonb) from public;
revoke all on function alea_query_list_roundtables(text, jsonb) from public;
revoke all on function alea_command_start_roundtable(text, text, jsonb) from public;
revoke all on function alea_worker_append_roundtable_event(uuid, text, jsonb) from public;
grant execute on function alea_query_roundtable(text, jsonb) to alea_api;
grant execute on function alea_query_list_roundtables(text, jsonb) to alea_api;
grant execute on function alea_command_start_roundtable(text, text, jsonb) to alea_api;
grant execute on function alea_worker_append_roundtable_event(uuid, text, jsonb) to alea_worker;
