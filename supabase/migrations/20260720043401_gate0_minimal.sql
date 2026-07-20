-- Alea Gate 0 minimal schema. Keep this migration immutable after first push.

create extension if not exists pgcrypto with schema extensions;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'alea_api') then
    create role alea_api login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'alea_worker') then
    create role alea_worker login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'alea_dispatcher') then
    create role alea_dispatcher login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'alea_scheduler') then
    create role alea_scheduler login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
end
$$;

create type app_role as enum ('user', 'admin');
create type profile_status as enum ('active', 'pending_consent', 'disabled');
create type roundtable_job_type as enum ('prediction', 'methodology_review');
create type roundtable_job_state as enum (
  'pending', 'select_nominating', 'select_debating', 'select_voting',
  'processing_matches', 'bet_proposing', 'bet_debating', 'bet_voting',
  'notarizing', 'completed', 'independent_reviewing', 'review_debating',
  'review_voting', 'pending_admin_confirmation', 'revise_and_review',
  'no_quorum', 'terminated', 'failed'
);
create type match_run_state as enum (
  'pending', 'predicting', 'debating', 'score_voting', 'eligible',
  'no_quorum', 'terminated', 'failed'
);
create type phase_run_status as enum (
  'pending', 'leased', 'running', 'succeeded', 'failed', 'timed_out', 'skipped'
);
create type fact_claim_status as enum (
  'extracted', 'verifying', 'verified', 'unsupported', 'unavailable'
);
create type outbox_status as enum ('pending', 'leased', 'published', 'failed', 'dead');
create type schedule_run_status as enum ('claimed', 'enqueued', 'running', 'succeeded', 'failed', 'skipped');
create type provider_execution_mode as enum ('api', 'codex_cli');

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role app_role not null default 'user',
  status profile_status not null default 'active',
  display_name text,
  avatar_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table user_consents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  age_confirmed boolean not null,
  terms_version text not null,
  privacy_version text not null,
  risk_version text not null,
  consented_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (user_id, terms_version, privacy_version, risk_version),
  check (age_confirmed)
);
create index user_consents_user_id_idx on user_consents(user_id);

create table ai_providers (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  display_name text not null,
  family text not null,
  allowed_api_domains text[] not null default '{}',
  enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (key = 'codex' or not enabled or cardinality(allowed_api_domains) > 0)
);

create table provider_connections (
  id uuid primary key default gen_random_uuid(),
  provider_id uuid not null references ai_providers(id),
  version integer not null check (version > 0),
  execution_mode provider_execution_mode not null default 'api',
  runtime_key text,
  protocol text not null,
  api_url text check (api_url is null or api_url ~ '^https://'),
  model_id text not null,
  capability_profile jsonb not null default '{}',
  generation_parameters jsonb not null default '{}',
  enabled boolean not null default false,
  test_status text not null default 'untested',
  tested_at timestamptz,
  created_at timestamptz not null default now(),
  unique (provider_id, version),
  unique (id, version),
  unique (id, provider_id),
  check (not enabled or test_status = 'passed'),
  check (
    (execution_mode = 'api' and api_url is not null and runtime_key is null)
    or
    (execution_mode = 'codex_cli' and runtime_key = 'codex' and api_url is null)
  )
);
create index provider_connections_provider_id_idx on provider_connections(provider_id);

create table provider_secrets (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid not null,
  connection_version integer not null,
  ciphertext bytea not null,
  ciphertext_nonce bytea not null check (octet_length(ciphertext_nonce) = 12),
  wrapped_dek bytea not null,
  wrapped_dek_nonce bytea not null check (octet_length(wrapped_dek_nonce) = 12),
  kek_version integer not null check (kek_version > 0),
  secret_tail text not null check (char_length(secret_tail) between 2 and 12),
  disabled_at timestamptz,
  created_at timestamptz not null default now(),
  unique (connection_id, connection_version),
  foreign key (connection_id, connection_version)
    references provider_connections(id, version) on delete cascade
);
create index provider_secrets_connection_id_idx on provider_secrets(connection_id);

create table ai_instances (
  id uuid primary key default gen_random_uuid(),
  provider_id uuid not null references ai_providers(id),
  connection_id uuid not null,
  nickname text not null,
  instance_number smallint not null check (instance_number between 1 and 3),
  reasoning_level text,
  timeout_seconds integer not null default 120 check (timeout_seconds between 1 and 900),
  max_concurrency integer not null default 1 check (max_concurrency between 1 and 16),
  enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider_id, instance_number),
  foreign key (connection_id, provider_id)
    references provider_connections(id, provider_id)
);
create index ai_instances_connection_id_idx on ai_instances(connection_id);

create table prompt_versions (
  id uuid primary key default gen_random_uuid(),
  key text not null,
  version integer not null check (version > 0),
  content jsonb not null,
  content_hash text not null,
  released_by uuid references profiles(id),
  released_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (key, version)
);
create index prompt_versions_released_by_idx on prompt_versions(released_by);

create table score_formula_versions (
  id uuid primary key default gen_random_uuid(),
  version integer not null unique check (version > 0),
  config jsonb not null,
  released_by uuid references profiles(id),
  effective_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index score_formula_versions_released_by_idx on score_formula_versions(released_by);

create table system_setting_versions (
  id uuid primary key default gen_random_uuid(),
  key text not null,
  version integer not null check (version > 0),
  value jsonb not null,
  released_by uuid references profiles(id),
  effective_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (key, version),
  unique (key, id),
  check (
    key <> 'history_context_limits'
    or (
      value ?& array['recent_match_limit', 'lesson_limit']
      and jsonb_typeof(value->'recent_match_limit') = 'number'
      and jsonb_typeof(value->'lesson_limit') = 'number'
      and (value->>'recent_match_limit')::integer between 1 and 50
      and (value->>'lesson_limit')::integer between 1 and 20
    )
  )
);
create index system_setting_versions_released_by_idx on system_setting_versions(released_by);

create table sporttery_rule_versions (
  id uuid primary key default gen_random_uuid(),
  version integer not null unique check (version > 0),
  source_url text not null,
  source_observed_at timestamptz not null,
  source_evidence_hash text not null,
  rules jsonb not null,
  license_status text not null default 'unverified',
  released_by uuid references profiles(id),
  effective_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index sporttery_rule_versions_released_by_idx on sporttery_rule_versions(released_by);

create table roundtable_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type roundtable_job_type not null,
  state roundtable_job_state not null default 'pending',
  state_version integer not null default 0 check (state_version >= 0),
  business_idempotency_key text not null,
  config_snapshot jsonb not null,
  selection_scope_snapshot_id uuid,
  score_formula_version_id uuid not null references score_formula_versions(id),
  sporttery_rule_version_id uuid not null references sporttery_rule_versions(id),
  history_context_limits_version_id uuid not null references system_setting_versions(id),
  sales_cutoff_at timestamptz,
  terminal_reason text,
  created_by uuid references profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (job_type, business_idempotency_key),
  check (
    (job_type = 'prediction' and state in (
      'pending', 'select_nominating', 'select_debating', 'select_voting',
      'processing_matches', 'bet_proposing', 'bet_debating', 'bet_voting',
      'notarizing', 'completed', 'no_quorum', 'terminated', 'failed'
    ))
    or
    (job_type = 'methodology_review' and state in (
      'pending', 'independent_reviewing', 'review_debating', 'review_voting',
      'pending_admin_confirmation', 'completed', 'revise_and_review',
      'no_quorum', 'terminated', 'failed'
    ))
  )
);
create index roundtable_jobs_created_by_idx on roundtable_jobs(created_by);
create index roundtable_jobs_score_formula_version_idx on roundtable_jobs(score_formula_version_id);
create index roundtable_jobs_sporttery_rule_version_idx on roundtable_jobs(sporttery_rule_version_id);
create index roundtable_jobs_history_context_limits_version_idx
  on roundtable_jobs(history_context_limits_version_id);

create table roundtable_match_runs (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references roundtable_jobs(id) on delete cascade,
  match_id uuid not null,
  state match_run_state not null default 'pending',
  state_version integer not null default 0 check (state_version >= 0),
  input_snapshot_id uuid,
  quorum_instance_count integer not null default 0,
  quorum_provider_count integer not null default 0,
  terminal_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (job_id, match_id)
);
create index roundtable_match_runs_job_id_idx on roundtable_match_runs(job_id);

create table roundtable_participants (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references roundtable_jobs(id) on delete cascade,
  ai_instance_id uuid not null references ai_instances(id),
  provider_family text not null,
  codename text not null,
  score numeric(8,4) not null,
  raw_weight numeric(8,4) not null,
  normalized_weight numeric(8,4) not null,
  frozen_config jsonb not null,
  created_at timestamptz not null default now(),
  unique (job_id, ai_instance_id),
  unique (job_id, codename)
);
create index roundtable_participants_ai_instance_id_idx on roundtable_participants(ai_instance_id);

create table roundtable_phase_runs (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references roundtable_jobs(id) on delete cascade,
  match_run_id uuid references roundtable_match_runs(id) on delete cascade,
  ai_instance_id uuid references ai_instances(id),
  phase text not null,
  round_number integer not null default 0 check (round_number >= 0),
  attempt integer not null default 1 check (attempt > 0),
  business_idempotency_key text not null unique,
  status phase_run_status not null default 'pending',
  lease_owner text,
  lease_until timestamptz,
  provider_request_id text,
  started_at timestamptz,
  finished_at timestamptz,
  error_code text,
  error_detail_redacted text,
  created_at timestamptz not null default now()
);
create index roundtable_phase_runs_job_id_idx on roundtable_phase_runs(job_id);
create index roundtable_phase_runs_match_run_id_idx on roundtable_phase_runs(match_run_id);
create index roundtable_phase_runs_ai_instance_id_idx on roundtable_phase_runs(ai_instance_id);

create table roundtable_results (
  id uuid primary key default gen_random_uuid(),
  phase_run_id uuid not null references roundtable_phase_runs(id),
  job_id uuid not null references roundtable_jobs(id) on delete cascade,
  match_run_id uuid references roundtable_match_runs(id) on delete cascade,
  ai_instance_id uuid references ai_instances(id),
  phase text not null,
  output_schema_key text not null,
  output_schema_version integer not null,
  payload jsonb not null,
  payload_hash text not null,
  usage jsonb,
  created_at timestamptz not null default now(),
  unique (phase_run_id)
);
create index roundtable_results_job_id_idx on roundtable_results(job_id);
create index roundtable_results_match_run_id_idx on roundtable_results(match_run_id);
create index roundtable_results_ai_instance_id_idx on roundtable_results(ai_instance_id);

create table fact_claims (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references roundtable_jobs(id) on delete cascade,
  result_id uuid not null references roundtable_results(id) on delete cascade,
  claim_text text not null,
  normalized_claim_hash text not null,
  status fact_claim_status not null default 'extracted',
  evidence_snapshot jsonb,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique (result_id, normalized_claim_hash)
);
create index fact_claims_job_id_idx on fact_claims(job_id);
create index fact_claims_result_id_idx on fact_claims(result_id);

create table roundtable_events (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references roundtable_jobs(id) on delete cascade,
  event_seq bigint not null check (event_seq > 0),
  event_type text not null,
  payload jsonb not null,
  is_public boolean not null default false,
  created_at timestamptz not null default now(),
  unique (job_id, event_seq)
);
create index roundtable_events_job_id_created_at_idx on roundtable_events(job_id, created_at);

create table execution_audits (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null unique references roundtable_jobs(id),
  first_success_result_id uuid references roundtable_results(id),
  reason text not null,
  normalized_payload_hash text not null,
  created_at timestamptz not null default now()
);

create table outbox_events (
  id uuid primary key default gen_random_uuid(),
  topic text not null,
  business_idempotency_key text not null unique,
  payload jsonb not null,
  status outbox_status not null default 'pending',
  available_at timestamptz not null default now(),
  lease_owner text,
  lease_until timestamptz,
  attempt integer not null default 0 check (attempt >= 0),
  broker_message_id text,
  published_at timestamptz,
  error_code text,
  error_detail_redacted text,
  created_at timestamptz not null default now()
);
create index outbox_events_claim_idx on outbox_events(status, available_at, lease_until);

create table notarized_predictions (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references roundtable_jobs(id),
  match_run_id uuid not null references roundtable_match_runs(id),
  payload jsonb not null,
  payload_hash text not null,
  sales_cutoff_at timestamptz not null,
  notarized_at timestamptz not null default now(),
  unique (match_run_id)
);
create index notarized_predictions_job_id_idx on notarized_predictions(job_id);

create table public_execution_audits (
  id uuid primary key default gen_random_uuid(),
  audit_id uuid not null unique references execution_audits(id),
  job_id uuid not null unique references roundtable_jobs(id),
  terminal_state roundtable_job_state not null,
  public_reason text not null,
  created_at timestamptz not null default now()
);
create index public_execution_audits_job_id_idx on public_execution_audits(job_id);

create table public_notarized_predictions (
  id uuid primary key default gen_random_uuid(),
  notarized_prediction_id uuid not null unique references notarized_predictions(id),
  job_id uuid not null references roundtable_jobs(id),
  match_run_id uuid not null references roundtable_match_runs(id),
  summary jsonb not null,
  disclosure_reason text not null check (disclosure_reason in ('published', 'sales_closed')),
  disclosed_at timestamptz not null default now()
);
create index public_notarized_predictions_job_id_idx on public_notarized_predictions(job_id);

create table public_roundtable_events (
  id uuid primary key default gen_random_uuid(),
  source_event_id uuid not null unique references roundtable_events(id),
  job_id uuid not null references roundtable_jobs(id),
  event_seq bigint not null,
  event_type text not null,
  public_payload jsonb not null,
  created_at timestamptz not null,
  unique (job_id, event_seq)
);
create index public_roundtable_events_source_event_id_idx on public_roundtable_events(source_event_id);

create table schedules (
  id uuid primary key default gen_random_uuid(),
  key text not null,
  version integer not null check (version > 0),
  schedule_type text not null,
  cron_expression text not null,
  timezone text not null default 'Asia/Taipei',
  command_payload jsonb not null,
  enabled boolean not null default false,
  effective_at timestamptz not null,
  created_by uuid references profiles(id),
  created_at timestamptz not null default now(),
  unique (key, version)
);
create index schedules_created_by_idx on schedules(created_by);

create table schedule_runs (
  id uuid primary key default gen_random_uuid(),
  schedule_id uuid not null references schedules(id),
  business_date date not null,
  planned_at timestamptz not null,
  triggered_at timestamptz,
  status schedule_run_status not null default 'claimed',
  lease_owner text,
  lease_until timestamptz,
  outbox_event_id uuid references outbox_events(id),
  error_code text,
  created_at timestamptz not null default now(),
  unique (schedule_id, business_date)
);
create index schedule_runs_schedule_id_idx on schedule_runs(schedule_id);
create index schedule_runs_outbox_event_id_idx on schedule_runs(outbox_event_id);

create table admin_role_grants (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  action text not null check (action in ('grant', 'revoke')),
  granted_by uuid references profiles(id),
  reason text not null,
  active boolean not null,
  created_at timestamptz not null default now()
);
create index admin_role_grants_user_id_idx on admin_role_grants(user_id);
create index admin_role_grants_granted_by_idx on admin_role_grants(granted_by);

create table admin_audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references profiles(id),
  action text not null,
  target_type text not null,
  target_id text,
  request_id text,
  detail_redacted jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index admin_audit_logs_actor_id_idx on admin_audit_logs(actor_id);

create function is_admin()
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1 from profiles
    where id = auth.uid() and role = 'admin' and status = 'active'
  );
$$;

create function reject_immutable_mutation()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  raise exception '% is append-only and cannot be updated or deleted', tg_table_name
    using errcode = '55000';
end;
$$;

create function assign_roundtable_event_seq()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  perform 1 from roundtable_jobs where id = new.job_id for update;
  if not found then
    raise exception 'roundtable job % does not exist', new.job_id using errcode = '23503';
  end if;

  select coalesce(max(e.event_seq), 0) + 1 into new.event_seq
  from roundtable_events e
  where e.job_id = new.job_id;
  return new;
end;
$$;

create function protect_profile_privileges()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if (new.role, new.status) is distinct from (old.role, old.status) and not is_admin() then
    raise exception 'profile role and status require an administrator' using errcode = '42501';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

create function validate_roundtable_version_refs()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1
    from system_setting_versions s
    where s.id = new.history_context_limits_version_id
      and s.key = 'history_context_limits'
  ) then
    raise exception 'history_context_limits_version_id must reference history_context_limits'
      using errcode = '23514';
  end if;

  return new;
end;
$$;

create trigger profiles_protect_privileges
before update on profiles
for each row execute function protect_profile_privileges();

create trigger roundtable_jobs_validate_version_refs
before insert or update of history_context_limits_version_id on roundtable_jobs
for each row execute function validate_roundtable_version_refs();

create trigger roundtable_events_assign_seq
before insert on roundtable_events
for each row execute function assign_roundtable_event_seq();

create trigger execution_audits_immutable
before update or delete on execution_audits
for each row execute function reject_immutable_mutation();
create trigger roundtable_results_immutable
before update or delete on roundtable_results
for each row execute function reject_immutable_mutation();
create trigger roundtable_events_immutable
before update or delete on roundtable_events
for each row execute function reject_immutable_mutation();
create trigger notarized_predictions_immutable
before update or delete on notarized_predictions
for each row execute function reject_immutable_mutation();
create trigger public_execution_audits_immutable
before update or delete on public_execution_audits
for each row execute function reject_immutable_mutation();
create trigger public_notarized_predictions_immutable
before update or delete on public_notarized_predictions
for each row execute function reject_immutable_mutation();
create trigger public_roundtable_events_immutable
before update or delete on public_roundtable_events
for each row execute function reject_immutable_mutation();
create trigger prompt_versions_immutable
before update or delete on prompt_versions
for each row execute function reject_immutable_mutation();
create trigger score_formula_versions_immutable
before update or delete on score_formula_versions
for each row execute function reject_immutable_mutation();
create trigger system_setting_versions_immutable
before update or delete on system_setting_versions
for each row execute function reject_immutable_mutation();
create trigger sporttery_rule_versions_immutable
before update or delete on sporttery_rule_versions
for each row execute function reject_immutable_mutation();
create trigger admin_role_grants_immutable
before update or delete on admin_role_grants
for each row execute function reject_immutable_mutation();
create trigger admin_audit_logs_immutable
before update or delete on admin_audit_logs
for each row execute function reject_immutable_mutation();

create function notarize_roundtable(p_job_id uuid)
returns table (notarized_prediction_id uuid, notarized_match_run_id uuid)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_job roundtable_jobs%rowtype;
begin
  if session_user <> 'alea_worker'
     and coalesce(current_setting('role', true), 'none') <> 'alea_worker' then
    raise exception 'notarize_roundtable requires alea_worker' using errcode = '42501';
  end if;

  select j.* into v_job
  from roundtable_jobs j
  where j.id = p_job_id
  for update;

  if not found then
    raise exception 'roundtable job % does not exist', p_job_id using errcode = 'P0002';
  end if;

  if v_job.job_type <> 'prediction' then
    raise exception 'only prediction jobs can be notarized' using errcode = '23514';
  end if;

  if v_job.state = 'completed' then
    return query
      select n.id, n.match_run_id
      from notarized_predictions n
      where n.job_id = p_job_id
      order by n.match_run_id;
    return;
  end if;

  if v_job.state <> 'notarizing' or v_job.sales_cutoff_at is null then
    raise exception 'roundtable is not ready for notarization' using errcode = '23514';
  end if;

  perform 1
  from roundtable_match_runs mr
  where mr.job_id = p_job_id
  order by mr.id
  for update;

  if not exists (
    select 1 from roundtable_match_runs mr
    where mr.job_id = p_job_id and mr.state = 'eligible'
  ) then
    raise exception 'notarization requires at least one eligible match' using errcode = '23514';
  end if;

  if exists (
    select 1
    from roundtable_match_runs mr
    where mr.job_id = p_job_id
      and mr.state = 'eligible'
      and (mr.quorum_instance_count < 3 or mr.quorum_provider_count < 2)
  ) then
    raise exception 'eligible match does not satisfy quorum' using errcode = '23514';
  end if;

  if exists (
    select 1
    from roundtable_match_runs mr
    where mr.job_id = p_job_id
      and mr.state = 'eligible'
      and (
        select count(distinct r.ai_instance_id)
        from roundtable_results r
        where r.job_id = p_job_id
          and r.match_run_id = mr.id
          and r.phase = 'score_vote'
      ) < 3
  ) then
    raise exception 'eligible match is missing score-vote quorum' using errcode = '23514';
  end if;

  if (
    select count(distinct r.ai_instance_id)
    from roundtable_results r
    where r.job_id = p_job_id
      and r.match_run_id is null
      and r.phase = 'bet_vote'
  ) < 3 or (
    select count(distinct p.provider_family)
    from roundtable_results r
    join roundtable_participants p
      on p.job_id = r.job_id and p.ai_instance_id = r.ai_instance_id
    where r.job_id = p_job_id
      and r.match_run_id is null
      and r.phase = 'bet_vote'
  ) < 2 then
    raise exception 'bet vote does not satisfy quorum' using errcode = '23514';
  end if;

  insert into notarized_predictions (
    job_id, match_run_id, payload, payload_hash, sales_cutoff_at
  )
  select
    p_job_id,
    mr.id,
    payloads.payload,
    encode(extensions.digest(convert_to(payloads.payload::text, 'utf8'), 'sha256'), 'hex'),
    v_job.sales_cutoff_at
  from roundtable_match_runs mr
  cross join lateral (
    select jsonb_build_object(
      'job_id', p_job_id,
      'match_run_id', mr.id,
      'match_id', mr.match_id,
      'input_snapshot_id', mr.input_snapshot_id,
      'config_snapshot', v_job.config_snapshot,
      'score_formula_version_id', v_job.score_formula_version_id,
      'sporttery_rule_version_id', v_job.sporttery_rule_version_id,
      'participants', coalesce((
        select jsonb_agg(jsonb_build_object(
          'ai_instance_id', p.ai_instance_id,
          'provider_family', p.provider_family,
          'codename', p.codename,
          'score', p.score,
          'raw_weight', p.raw_weight,
          'normalized_weight', p.normalized_weight,
          'frozen_config', p.frozen_config
        ) order by p.codename)
        from roundtable_participants p
        where p.job_id = p_job_id
      ), '[]'::jsonb),
      'score_votes', coalesce((
        select jsonb_agg(r.payload order by r.created_at, r.id)
        from roundtable_results r
        where r.job_id = p_job_id
          and r.match_run_id = mr.id
          and r.phase = 'score_vote'
      ), '[]'::jsonb),
      'bet_votes', coalesce((
        select jsonb_agg(r.payload order by r.created_at, r.id)
        from roundtable_results r
        where r.job_id = p_job_id
          and r.match_run_id is null
          and r.phase = 'bet_vote'
      ), '[]'::jsonb)
    ) as payload
  ) payloads
  where mr.job_id = p_job_id
    and mr.state = 'eligible'
  on conflict (match_run_id) do nothing;

  update roundtable_jobs
  set state = 'completed',
      state_version = state_version + 1,
      updated_at = now()
  where id = p_job_id and state = 'notarizing';

  insert into roundtable_events (job_id, event_type, payload)
  values (
    p_job_id,
    'roundtable.notarized',
    jsonb_build_object(
      'job_id', p_job_id,
      'notarized_count', (
        select count(*) from notarized_predictions n where n.job_id = p_job_id
      )
    )
  );

  return query
    select n.id, n.match_run_id
    from notarized_predictions n
    where n.job_id = p_job_id
    order by n.match_run_id;
end;
$$;

create function refresh_public_roundtable_projections(p_job_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_job roundtable_jobs%rowtype;
  v_audits integer := 0;
  v_predictions integer := 0;
  v_events integer := 0;
begin
  if session_user <> 'alea_worker'
     and coalesce(current_setting('role', true), 'none') <> 'alea_worker' then
    raise exception 'refresh_public_roundtable_projections requires alea_worker'
      using errcode = '42501';
  end if;

  select j.* into v_job
  from roundtable_jobs j
  where j.id = p_job_id
  for update;

  if not found then
    raise exception 'roundtable job % does not exist', p_job_id using errcode = 'P0002';
  end if;

  if v_job.state in ('completed', 'revise_and_review', 'no_quorum', 'terminated', 'failed') then
    insert into public_execution_audits (
      audit_id, job_id, terminal_state, public_reason
    )
    select
      a.id,
      a.job_id,
      v_job.state,
      case v_job.state
        when 'no_quorum' then '未达法定人数'
        when 'terminated' then '圆桌已终止'
        when 'failed' then '圆桌执行失败'
        when 'revise_and_review' then '提议需修改后再审'
        else '圆桌已完成'
      end
    from execution_audits a
    where a.job_id = p_job_id
      and not exists (
        select 1 from public_execution_audits pa where pa.audit_id = a.id
      );
    get diagnostics v_audits = row_count;
  end if;

  insert into public_notarized_predictions (
    notarized_prediction_id, job_id, match_run_id, summary, disclosure_reason
  )
  select
    n.id,
    n.job_id,
    n.match_run_id,
    jsonb_strip_nulls(jsonb_build_object(
      'match_id', n.payload->'match_id',
      'score_votes', n.payload->'score_votes',
      'bet_votes', n.payload->'bet_votes',
      'score_formula_version_id', n.payload->'score_formula_version_id',
      'sporttery_rule_version_id', n.payload->'sporttery_rule_version_id',
      'notarized_at', to_jsonb(n.notarized_at)
    )),
    'sales_closed'
  from notarized_predictions n
  where n.job_id = p_job_id
    and n.sales_cutoff_at <= now()
    and not exists (
      select 1
      from public_notarized_predictions pp
      where pp.notarized_prediction_id = n.id
    );
  get diagnostics v_predictions = row_count;

  if v_job.state in ('revise_and_review', 'no_quorum', 'terminated', 'failed')
     or exists (
       select 1
       from notarized_predictions n
       where n.job_id = p_job_id and n.sales_cutoff_at <= now()
     ) then
    insert into public_roundtable_events (
      source_event_id, job_id, event_seq, event_type, public_payload, created_at
    )
    select
      e.id,
      e.job_id,
      e.event_seq,
      e.event_type,
      jsonb_strip_nulls(jsonb_build_object(
        'phase', e.payload->'phase',
        'match_id', e.payload->'match_id',
        'codename', e.payload->'codename',
        'status', e.payload->'status',
        'decision', e.payload->'decision',
        'score', e.payload->'score',
        'reason', e.payload->'reason',
        'notarized_count', e.payload->'notarized_count'
      )),
      e.created_at
    from roundtable_events e
    where e.job_id = p_job_id
      and not exists (
        select 1 from public_roundtable_events pe where pe.source_event_id = e.id
      );
    get diagnostics v_events = row_count;
  end if;

  return jsonb_build_object(
    'execution_audits_inserted', v_audits,
    'notarized_predictions_inserted', v_predictions,
    'roundtable_events_inserted', v_events
  );
end;
$$;

create function claim_schedule_run(
  p_schedule_id uuid,
  p_business_date date,
  p_planned_at timestamptz,
  p_lease_owner text,
  p_lease_seconds integer default 60
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_id uuid;
begin
  if session_user <> 'alea_scheduler'
     and coalesce(current_setting('role', true), 'none') <> 'alea_scheduler' then
    raise exception 'claim_schedule_run requires alea_scheduler' using errcode = '42501';
  end if;

  insert into schedule_runs (
    schedule_id, business_date, planned_at, lease_owner, lease_until
  ) values (
    p_schedule_id, p_business_date, p_planned_at, p_lease_owner,
    now() + make_interval(secs => greatest(p_lease_seconds, 1))
  )
  on conflict (schedule_id, business_date) do update
    set lease_owner = excluded.lease_owner,
        lease_until = excluded.lease_until
    where schedule_runs.status in ('claimed', 'failed')
      and (schedule_runs.lease_until is null or schedule_runs.lease_until < now())
  returning id into v_id;

  return v_id;
end;
$$;

create function enqueue_scheduled_command(p_schedule_run_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_outbox_id uuid;
begin
  if session_user <> 'alea_scheduler'
     and coalesce(current_setting('role', true), 'none') <> 'alea_scheduler' then
    raise exception 'enqueue_scheduled_command requires alea_scheduler' using errcode = '42501';
  end if;

  insert into outbox_events (topic, business_idempotency_key, payload)
  select
    'scheduled_command',
    'schedule_run:' || sr.id::text,
    jsonb_build_object(
      'schedule_run_id', sr.id,
      'schedule_id', sr.schedule_id,
      'command', s.command_payload
    )
  from schedule_runs sr
  join schedules s on s.id = sr.schedule_id
  where sr.id = p_schedule_run_id
  on conflict (business_idempotency_key) do nothing
  returning id into v_outbox_id;

  if v_outbox_id is null then
    select id into v_outbox_id
      from outbox_events
      where business_idempotency_key = 'schedule_run:' || p_schedule_run_id::text;
  end if;

  update schedule_runs
    set status = 'enqueued', outbox_event_id = v_outbox_id, triggered_at = now()
    where id = p_schedule_run_id and status = 'claimed';

  return v_outbox_id;
end;
$$;

alter table profiles enable row level security;
alter table user_consents enable row level security;
alter table ai_providers enable row level security;
alter table provider_connections enable row level security;
alter table provider_secrets enable row level security;
alter table ai_instances enable row level security;
alter table prompt_versions enable row level security;
alter table score_formula_versions enable row level security;
alter table system_setting_versions enable row level security;
alter table sporttery_rule_versions enable row level security;
alter table roundtable_jobs enable row level security;
alter table roundtable_match_runs enable row level security;
alter table roundtable_participants enable row level security;
alter table roundtable_phase_runs enable row level security;
alter table roundtable_results enable row level security;
alter table fact_claims enable row level security;
alter table roundtable_events enable row level security;
alter table execution_audits enable row level security;
alter table outbox_events enable row level security;
alter table notarized_predictions enable row level security;
alter table public_execution_audits enable row level security;
alter table public_notarized_predictions enable row level security;
alter table public_roundtable_events enable row level security;
alter table schedules enable row level security;
alter table schedule_runs enable row level security;
alter table admin_role_grants enable row level security;
alter table admin_audit_logs enable row level security;

create policy profiles_self_read on profiles
for select to authenticated using (id = auth.uid() or is_admin());
create policy profiles_self_update on profiles
for update to authenticated using (id = auth.uid())
with check (id = auth.uid());
create policy user_consents_self_read on user_consents
for select to authenticated using (user_id = auth.uid() or is_admin());
create policy user_consents_self_insert on user_consents
for insert to authenticated with check (user_id = auth.uid());

create policy ai_providers_admin_read on ai_providers for select to authenticated using (is_admin());
create policy provider_connections_admin_read on provider_connections for select to authenticated using (is_admin());
create policy ai_instances_admin_read on ai_instances for select to authenticated using (is_admin());
create policy prompt_versions_admin_read on prompt_versions for select to authenticated using (is_admin());
create policy score_formula_versions_admin_read on score_formula_versions for select to authenticated using (is_admin());
create policy system_setting_versions_admin_read on system_setting_versions for select to authenticated using (is_admin());
create policy sporttery_rule_versions_admin_read on sporttery_rule_versions for select to authenticated using (is_admin());
create policy jobs_admin_read on roundtable_jobs for select to authenticated using (is_admin());
create policy match_runs_admin_read on roundtable_match_runs for select to authenticated using (is_admin());
create policy participants_admin_read on roundtable_participants for select to authenticated using (is_admin());
create policy phase_runs_admin_read on roundtable_phase_runs for select to authenticated using (is_admin());
create policy results_admin_read on roundtable_results for select to authenticated using (is_admin());
create policy fact_claims_admin_read on fact_claims for select to authenticated using (is_admin());
create policy events_admin_read on roundtable_events for select to authenticated using (is_admin());
create policy audits_admin_read on execution_audits for select to authenticated using (is_admin());
create policy notarized_admin_read on notarized_predictions for select to authenticated using (is_admin());
create policy schedules_admin_read on schedules for select to authenticated using (is_admin());
create policy schedule_runs_admin_read on schedule_runs for select to authenticated using (is_admin());
create policy admin_role_grants_admin_read on admin_role_grants for select to authenticated using (is_admin());
create policy admin_audit_logs_admin_read on admin_audit_logs for select to authenticated using (is_admin());

create policy public_audits_authenticated_read on public_execution_audits
for select to authenticated using (true);
create policy public_predictions_authenticated_read on public_notarized_predictions
for select to authenticated using (true);
create policy public_events_authenticated_read on public_roundtable_events
for select to authenticated using (true);

create policy api_profiles_read on profiles for select to alea_api using (true);
create policy api_consents_read on user_consents for select to alea_api using (true);
create policy api_public_audits_read on public_execution_audits for select to alea_api using (true);
create policy api_public_predictions_read on public_notarized_predictions for select to alea_api using (true);
create policy api_public_events_read on public_roundtable_events for select to alea_api using (true);

create policy worker_providers_read on ai_providers for select to alea_worker using (true);
create policy worker_connections_read on provider_connections for select to alea_worker using (true);
create policy worker_secrets_read on provider_secrets for select to alea_worker using (true);
create policy worker_instances_read on ai_instances for select to alea_worker using (true);
create policy worker_prompts_read on prompt_versions for select to alea_worker using (true);
create policy worker_scores_read on score_formula_versions for select to alea_worker using (true);
create policy worker_settings_read on system_setting_versions for select to alea_worker using (true);
create policy worker_rules_read on sporttery_rule_versions for select to alea_worker using (true);
create policy worker_jobs_all on roundtable_jobs for all to alea_worker using (true) with check (true);
create policy worker_match_runs_all on roundtable_match_runs for all to alea_worker using (true) with check (true);
create policy worker_participants_all on roundtable_participants for all to alea_worker using (true) with check (true);
create policy worker_phase_runs_all on roundtable_phase_runs for all to alea_worker using (true) with check (true);
create policy worker_results_insert on roundtable_results for insert to alea_worker with check (true);
create policy worker_results_read on roundtable_results for select to alea_worker using (true);
create policy worker_claims_all on fact_claims for all to alea_worker using (true) with check (true);
create policy worker_events_insert on roundtable_events for insert to alea_worker with check (true);
create policy worker_events_read on roundtable_events for select to alea_worker using (true);
create policy worker_audits_insert on execution_audits for insert to alea_worker with check (true);
create policy worker_audits_read on execution_audits for select to alea_worker using (true);
create policy worker_outbox_insert on outbox_events for insert to alea_worker with check (true);
create policy worker_outbox_read on outbox_events for select to alea_worker using (true);

create policy dispatcher_outbox_read on outbox_events for select to alea_dispatcher using (true);
create policy dispatcher_outbox_update on outbox_events for update to alea_dispatcher using (true) with check (true);

create policy scheduler_schedules_read on schedules for select to alea_scheduler using (true);
create policy scheduler_schedule_runs_read on schedule_runs for select to alea_scheduler using (true);
create policy scheduler_settings_read on system_setting_versions for select to alea_scheduler using (true);

revoke all on schema public from public;
grant usage on schema public to anon, authenticated, alea_api, alea_worker, alea_dispatcher, alea_scheduler;

revoke all on all tables in schema public from public, anon, authenticated;
grant select, update on profiles to authenticated;
grant select, insert on user_consents to authenticated;
grant select on ai_providers, provider_connections, ai_instances, prompt_versions,
  score_formula_versions, system_setting_versions, sporttery_rule_versions,
  roundtable_jobs, roundtable_match_runs, roundtable_participants,
  roundtable_phase_runs, roundtable_results, fact_claims, roundtable_events,
  execution_audits, notarized_predictions, schedules, schedule_runs,
  admin_role_grants, admin_audit_logs to authenticated;
grant select on public_execution_audits, public_notarized_predictions,
  public_roundtable_events to authenticated;

grant select on profiles, user_consents, public_execution_audits,
  public_notarized_predictions, public_roundtable_events to alea_api;

grant select on ai_providers, provider_connections, provider_secrets, ai_instances,
  prompt_versions, score_formula_versions, system_setting_versions,
  sporttery_rule_versions to alea_worker;
grant select, insert, update on roundtable_jobs, roundtable_match_runs,
  roundtable_participants, roundtable_phase_runs, fact_claims to alea_worker;
grant select, insert on roundtable_results, roundtable_events,
  execution_audits, outbox_events to alea_worker;
grant execute on function notarize_roundtable(uuid) to alea_worker;
grant execute on function refresh_public_roundtable_projections(uuid) to alea_worker;

grant select on outbox_events to alea_dispatcher;
grant update (status, lease_owner, lease_until, attempt, broker_message_id,
  published_at, error_code, error_detail_redacted) on outbox_events to alea_dispatcher;

grant select on schedules, schedule_runs, system_setting_versions to alea_scheduler;
grant execute on function claim_schedule_run(uuid, date, timestamptz, text, integer) to alea_scheduler;
grant execute on function enqueue_scheduled_command(uuid) to alea_scheduler;

revoke all on function is_admin() from public;
grant execute on function is_admin() to authenticated;
revoke all on function notarize_roundtable(uuid) from public;
revoke all on function refresh_public_roundtable_projections(uuid) from public;
revoke all on function claim_schedule_run(uuid, date, timestamptz, text, integer) from public;
revoke all on function enqueue_scheduled_command(uuid) from public;
