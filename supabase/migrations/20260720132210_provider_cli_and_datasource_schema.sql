-- API providers and local CLI runtimes are both first-class connection types.

alter table ai_providers
  drop constraint if exists ai_providers_check,
  add column retired_at timestamptz;

alter table ai_providers
  add constraint ai_providers_enabled_configuration_check check (
    not enabled
    or family = 'cli'
    or cardinality(allowed_api_domains) > 0
  );

alter table provider_connections
  add column executable_path text,
  add column model_catalog jsonb not null default '[]'::jsonb,
  add column custom_model_ids text[] not null default '{}',
  add column updated_at timestamptz not null default now();

alter table provider_connections
  drop constraint if exists provider_connections_api_url_check;

alter table provider_connections
  add constraint provider_connections_api_url_check check (
    api_url is null
    or api_url ~ '^https://'
    or api_url ~ '^http://(127\.0\.0\.1|localhost|\[::1\]|host\.docker\.internal)(:[0-9]+)?/'
  );

alter table provider_connections
  drop constraint if exists provider_connections_check1;

alter table provider_connections
  add constraint provider_connections_execution_shape_check check (
    (
      execution_mode = 'api'
      and api_url is not null
      and runtime_key is null
      and executable_path is null
    )
    or
    (
      execution_mode in ('cli', 'codex_cli')
      and runtime_key is not null
      and runtime_key in (
        'codex', 'claude', 'gemini', 'copilot', 'cursor', 'opencode',
        'hermes', 'kimi', 'qwen', 'aider', 'amp'
      )
      and executable_path is not null
      and executable_path ~ '^/'
      and api_url is null
    )
  );

alter table ai_instances
  add column model_id text,
  add column prompt_version text;

update ai_instances i
set model_id = c.model_id,
    prompt_version = 'default'
from provider_connections c
where c.id = i.connection_id
  and (i.model_id is null or i.prompt_version is null);

alter table ai_instances
  alter column model_id set not null,
  alter column prompt_version set not null;

create table provider_connection_health (
  connection_id uuid not null,
  connection_version integer not null,
  status text not null default 'untested'
    check (status in ('untested', 'probing', 'passed', 'failed')),
  detected_version text,
  auth_status text not null default 'unknown'
    check (auth_status in ('unknown', 'authenticated', 'unauthenticated', 'not_required', 'error')),
  available_models jsonb not null default '[]'::jsonb,
  checked_at timestamptz,
  error_code text,
  error_message_masked text,
  metadata jsonb not null default '{}'::jsonb,
  primary key (connection_id, connection_version),
  foreign key (connection_id, connection_version)
    references provider_connections(id, version) on delete cascade,
  check (
    (status = 'failed' and error_code is not null)
    or status <> 'failed'
  )
);
create index provider_connection_health_checked_at_idx
  on provider_connection_health(checked_at desc);

create type data_source_kind as enum (
  'sporttery_web', 'licensed_supplier', 'admin_import', 'fixture'
);
create type data_source_status as enum (
  'disabled', 'ready', 'degraded', 'unavailable'
);
create type sync_run_status as enum (
  'pending', 'running', 'paused', 'succeeded', 'failed', 'cancelled'
);
create type source_record_state as enum (
  'observed', 'parsed', 'mapped', 'conflict', 'accepted', 'rejected'
);
create type data_conflict_status as enum ('pending', 'accepted', 'rejected');

create table data_sources (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  display_name text not null,
  kind data_source_kind not null,
  priority smallint not null check (priority between 1 and 100),
  base_url text,
  capabilities text[] not null default '{}',
  enabled boolean not null default false,
  status data_source_status not null default 'disabled',
  authorization_status text not null default 'unverified'
    check (authorization_status in ('unverified', 'authorized', 'expired', 'not_required')),
  authorization_reference text,
  parser_version text not null,
  configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    kind <> 'sporttery_web'
    or not enabled
    or (
      authorization_status = 'authorized'
      and authorization_reference is not null
    )
  ),
  check (
    kind <> 'fixture'
    or authorization_status = 'not_required'
  )
);

create table sync_runs (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references data_sources(id),
  status sync_run_status not null default 'pending',
  scope jsonb not null,
  cursor jsonb,
  parser_version text not null,
  records_seen integer not null default 0 check (records_seen >= 0),
  records_accepted integer not null default 0 check (records_accepted >= 0),
  records_conflicted integer not null default 0 check (records_conflicted >= 0),
  attempt integer not null default 0 check (attempt >= 0),
  last_error_code text,
  last_error_masked text,
  started_at timestamptz,
  heartbeat_at timestamptz,
  completed_at timestamptz,
  created_by uuid references profiles(id),
  created_at timestamptz not null default now(),
  check (
    status not in ('succeeded', 'failed', 'cancelled')
    or completed_at is not null
  )
);
create index sync_runs_source_status_idx
  on sync_runs(data_source_id, status, created_at desc);
create index sync_runs_created_by_idx on sync_runs(created_by);

create table source_records (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references data_sources(id),
  sync_run_id uuid references sync_runs(id) on delete set null,
  source_record_key text not null,
  sporttery_match_number text,
  source_url text,
  business_date date,
  observed_at timestamptz not null,
  collected_at timestamptz not null default now(),
  parser_version text not null,
  raw_content jsonb not null,
  raw_content_hash text not null
    check (raw_content_hash ~ '^[0-9a-f]{64}$'),
  state source_record_state not null default 'observed',
  parsed_payload jsonb,
  created_at timestamptz not null default now(),
  unique (data_source_id, source_record_key, raw_content_hash)
);
create index source_records_source_key_idx
  on source_records(data_source_id, source_record_key, observed_at desc);
create index source_records_sync_run_idx on source_records(sync_run_id);
create index source_records_sporttery_number_idx
  on source_records(business_date, sporttery_match_number);

create table competitions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  country_code text,
  competition_type text not null default 'league',
  sporttery_eligible boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (name, country_code)
);

create table competition_seasons (
  id uuid primary key default gen_random_uuid(),
  competition_id uuid not null references competitions(id),
  name text not null,
  starts_on date,
  ends_on date,
  created_at timestamptz not null default now(),
  unique (competition_id, name)
);
create index competition_seasons_competition_idx
  on competition_seasons(competition_id);

create table teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  country_code text,
  badge_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (name, country_code)
);

create table matches (
  id uuid primary key default gen_random_uuid(),
  competition_id uuid not null references competitions(id),
  season_id uuid references competition_seasons(id),
  home_team_id uuid not null references teams(id),
  away_team_id uuid not null references teams(id),
  kickoff_at timestamptz not null,
  business_date date not null,
  sporttery_match_number text not null,
  sales_status text not null default 'scheduled'
    check (sales_status in ('scheduled', 'on_sale', 'closed', 'cancelled', 'settled')),
  sales_cutoff_at timestamptz,
  fact_state text not null default 'fixture'
    check (fact_state in ('fixture', 'verified', 'conflict', 'unavailable')),
  canonical_source_record_id uuid references source_records(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_date, sporttery_match_number),
  check (home_team_id <> away_team_id)
);
create index matches_kickoff_idx on matches(kickoff_at);
create index matches_competition_idx on matches(competition_id);
create index matches_season_idx on matches(season_id);
create index matches_home_team_idx on matches(home_team_id);
create index matches_away_team_idx on matches(away_team_id);
create index matches_source_record_idx on matches(canonical_source_record_id);

create table match_odds_snapshots (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references matches(id) on delete cascade,
  source_record_id uuid not null references source_records(id),
  play_type text not null,
  values jsonb not null,
  observed_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (match_id, source_record_id, play_type)
);
create index match_odds_match_observed_idx
  on match_odds_snapshots(match_id, observed_at desc);
create index match_odds_source_record_idx
  on match_odds_snapshots(source_record_id);

create table match_results (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references matches(id) on delete cascade,
  source_record_id uuid not null references source_records(id),
  result_version integer not null check (result_version > 0),
  home_score integer not null check (home_score >= 0),
  away_score integer not null check (away_score >= 0),
  status text not null default 'pending'
    check (status in ('pending', 'confirmed', 'rejected')),
  confirmed_by uuid references profiles(id),
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (match_id, result_version),
  check (
    (status = 'confirmed' and confirmed_by is not null and confirmed_at is not null)
    or status <> 'confirmed'
  )
);
create index match_results_source_record_idx on match_results(source_record_id);
create index match_results_confirmed_by_idx on match_results(confirmed_by);

create table entity_mappings (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references data_sources(id),
  entity_type text not null
    check (entity_type in ('competition', 'season', 'team', 'match')),
  source_entity_key text not null,
  canonical_entity_id uuid not null,
  source_record_id uuid references source_records(id),
  mapping_status text not null default 'confirmed'
    check (mapping_status in ('pending', 'confirmed', 'rejected')),
  confirmed_by uuid references profiles(id),
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (data_source_id, entity_type, source_entity_key)
);
create index entity_mappings_canonical_idx
  on entity_mappings(entity_type, canonical_entity_id);
create index entity_mappings_source_record_idx on entity_mappings(source_record_id);
create index entity_mappings_confirmed_by_idx on entity_mappings(confirmed_by);

create table data_conflicts (
  id uuid primary key default gen_random_uuid(),
  match_id uuid references matches(id),
  field_path text not null,
  candidate_source_record_ids uuid[] not null,
  status data_conflict_status not null default 'pending',
  accepted_source_record_id uuid references source_records(id),
  decision_reason text,
  decided_by uuid references profiles(id),
  decided_at timestamptz,
  created_at timestamptz not null default now(),
  check (cardinality(candidate_source_record_ids) >= 2),
  check (
    (
      status = 'pending'
      and accepted_source_record_id is null
      and decided_by is null
      and decided_at is null
    )
    or
    (
      status in ('accepted', 'rejected')
      and decision_reason is not null
      and decided_by is not null
      and decided_at is not null
    )
  )
);
create index data_conflicts_match_status_idx
  on data_conflicts(match_id, status);
create index data_conflicts_accepted_record_idx
  on data_conflicts(accepted_source_record_id);
create index data_conflicts_decided_by_idx on data_conflicts(decided_by);

insert into data_sources (
  key, display_name, kind, priority, capabilities, enabled, status,
  authorization_status, parser_version, configuration
)
values
  (
    'gate0_fixture',
    'Gate 0 人工 Fixture',
    'fixture',
    1,
    array['schedule', 'odds', 'result'],
    true,
    'ready',
    'not_required',
    'fixture-v1',
    '{"non_production": true}'::jsonb
  ),
  (
    'sporttery_web',
    'Sporttery Web Source',
    'sporttery_web',
    10,
    array['schedule', 'detail', 'fixed_odds', 'odds_history', 'result'],
    false,
    'disabled',
    'unverified',
    'sporttery-disabled-v1',
    '{"permission_gate": true}'::jsonb
  )
on conflict (key) do nothing;

alter table provider_connection_health enable row level security;
alter table data_sources enable row level security;
alter table sync_runs enable row level security;
alter table source_records enable row level security;
alter table competitions enable row level security;
alter table competition_seasons enable row level security;
alter table teams enable row level security;
alter table matches enable row level security;
alter table match_odds_snapshots enable row level security;
alter table match_results enable row level security;
alter table entity_mappings enable row level security;
alter table data_conflicts enable row level security;

create policy provider_health_admin_read
on provider_connection_health for select to authenticated
using ((select is_admin()));
create policy data_sources_admin_read
on data_sources for select to authenticated
using ((select is_admin()));
create policy sync_runs_admin_read
on sync_runs for select to authenticated
using ((select is_admin()));
create policy source_records_admin_read
on source_records for select to authenticated
using ((select is_admin()));
create policy entity_mappings_admin_read
on entity_mappings for select to authenticated
using ((select is_admin()));
create policy data_conflicts_admin_read
on data_conflicts for select to authenticated
using ((select is_admin()));
create policy match_results_admin_read
on match_results for select to authenticated
using ((select is_admin()));

create policy competitions_authenticated_read
on competitions for select to authenticated
using (sporttery_eligible);
create policy seasons_authenticated_read
on competition_seasons for select to authenticated
using (
  exists (
    select 1 from competitions c
    where c.id = competition_seasons.competition_id
      and c.sporttery_eligible
  )
);
create policy teams_authenticated_read
on teams for select to authenticated
using (
  exists (
    select 1
    from matches m
    where m.fact_state in ('fixture', 'verified')
      and (m.home_team_id = teams.id or m.away_team_id = teams.id)
  )
);
create policy matches_authenticated_read
on matches for select to authenticated
using (fact_state in ('fixture', 'verified'));
create policy odds_authenticated_read
on match_odds_snapshots for select to authenticated
using (
  exists (
    select 1 from matches m
    where m.id = match_odds_snapshots.match_id
      and m.fact_state in ('fixture', 'verified')
  )
);

create policy api_provider_health_all
on provider_connection_health for all to alea_api
using (true) with check (true);
create policy api_data_sources_read
on data_sources for select to alea_api using (true);
create policy api_sync_runs_all
on sync_runs for all to alea_api using (true) with check (true);
create policy api_source_records_all
on source_records for all to alea_api using (true) with check (true);
create policy api_competitions_all
on competitions for all to alea_api using (true) with check (true);
create policy api_seasons_all
on competition_seasons for all to alea_api using (true) with check (true);
create policy api_teams_all
on teams for all to alea_api using (true) with check (true);
create policy api_matches_all
on matches for all to alea_api using (true) with check (true);
create policy api_odds_all
on match_odds_snapshots for all to alea_api using (true) with check (true);
create policy api_results_all
on match_results for all to alea_api using (true) with check (true);
create policy api_mappings_all
on entity_mappings for all to alea_api using (true) with check (true);
create policy api_conflicts_all
on data_conflicts for all to alea_api using (true) with check (true);

create policy worker_provider_health_read
on provider_connection_health for select to alea_worker using (true);
create policy worker_data_sources_read
on data_sources for select to alea_worker using (true);
create policy worker_sync_runs_all
on sync_runs for all to alea_worker using (true) with check (true);
create policy worker_source_records_all
on source_records for all to alea_worker using (true) with check (true);
create policy worker_competitions_all
on competitions for all to alea_worker using (true) with check (true);
create policy worker_seasons_all
on competition_seasons for all to alea_worker using (true) with check (true);
create policy worker_teams_all
on teams for all to alea_worker using (true) with check (true);
create policy worker_matches_all
on matches for all to alea_worker using (true) with check (true);
create policy worker_odds_all
on match_odds_snapshots for all to alea_worker using (true) with check (true);
create policy worker_results_all
on match_results for all to alea_worker using (true) with check (true);
create policy worker_mappings_all
on entity_mappings for all to alea_worker using (true) with check (true);
create policy worker_conflicts_read
on data_conflicts for select to alea_worker using (true);

grant select on provider_connection_health, data_sources, sync_runs, source_records,
  competitions, competition_seasons, teams, matches, match_odds_snapshots,
  match_results, entity_mappings, data_conflicts to authenticated;

grant select, insert, update, delete on provider_connection_health to alea_api;
grant select on data_sources to alea_api;
grant select, insert, update on sync_runs, source_records, competitions,
  competition_seasons, teams, matches, match_odds_snapshots, match_results,
  entity_mappings, data_conflicts to alea_api;

grant select on provider_connection_health, data_sources to alea_worker;
grant select, insert, update on sync_runs, source_records, competitions,
  competition_seasons, teams, matches, match_odds_snapshots, match_results,
  entity_mappings to alea_worker;
grant select on data_conflicts to alea_worker;

create function alea_assert_admin_actor(p_actor_id text)
returns uuid
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
begin
  begin
    v_actor_id := p_actor_id::uuid;
  exception
    when invalid_text_representation then
      raise exception 'invalid administrator identity' using errcode = '22023';
  end;

  if not exists (
    select 1
    from profiles p
    where p.id = v_actor_id
      and p.role = 'admin'
      and p.status = 'active'
  ) then
    raise exception 'administrator privileges required' using errcode = '42501';
  end if;
  return v_actor_id;
end;
$$;

create function alea_query_list_providers(
  p_actor_id text,
  p_params jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
begin
  perform alea_assert_admin_actor(p_actor_id);
  if p_params <> '{}'::jsonb then
    raise exception 'list_providers does not accept parameters' using errcode = '22023';
  end if;

  return jsonb_build_object(
    'providers',
    coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'id', p.id,
          'key', p.key,
          'display_name', p.display_name,
          'family', p.family,
          'allowed_api_domains', p.allowed_api_domains,
          'enabled', p.enabled,
          'connections', coalesce((
            select jsonb_agg(
              jsonb_build_object(
                'id', c.id,
                'version', c.version,
                'execution_mode', c.execution_mode,
                'runtime_key', c.runtime_key,
                'protocol', c.protocol,
                'api_url', c.api_url,
                'executable_path', c.executable_path,
                'model_id', c.model_id,
                'model_catalog', c.model_catalog,
                'custom_model_ids', c.custom_model_ids,
                'capability_profile', c.capability_profile,
                'generation_parameters', c.generation_parameters,
                'enabled', c.enabled,
                'test_status', c.test_status,
                'tested_at', c.tested_at,
                'secret_tail', s.secret_tail,
                'health', case
                  when h.connection_id is null then null
                  else jsonb_build_object(
                    'status', h.status,
                    'detected_version', h.detected_version,
                    'auth_status', h.auth_status,
                    'available_models', h.available_models,
                    'checked_at', h.checked_at,
                    'error_code', h.error_code,
                    'error_message_masked', h.error_message_masked,
                    'metadata', h.metadata
                  )
                end,
                'instances', coalesce((
                  select jsonb_agg(
                    jsonb_build_object(
                      'id', i.id,
                      'nickname', i.nickname,
                      'instance_number', i.instance_number,
                      'model_id', i.model_id,
                      'reasoning_level', i.reasoning_level,
                      'timeout_seconds', i.timeout_seconds,
                      'max_concurrency', i.max_concurrency,
                      'prompt_version', i.prompt_version,
                      'enabled', i.enabled
                    )
                    order by i.instance_number
                  )
                  from ai_instances i
                  where i.connection_id = c.id
                ), '[]'::jsonb)
              )
              order by c.version desc
            )
            from provider_connections c
            left join provider_secrets s
              on s.connection_id = c.id
             and s.connection_version = c.version
             and s.disabled_at is null
            left join provider_connection_health h
              on h.connection_id = c.id
             and h.connection_version = c.version
            where c.provider_id = p.id
          ), '[]'::jsonb)
        )
        order by p.display_name, p.key
      )
      from ai_providers p
      where p.retired_at is null
    ), '[]'::jsonb)
  );
end;
$$;

create function alea_command_save_provider(
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
  v_provider_id uuid;
  v_connection_id uuid;
  v_mode provider_execution_mode;
  v_domains text[];
  v_health jsonb;
  v_test_status text := 'untested';
  v_tested_at timestamptz;
  v_enabled boolean;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_connection_id := (p_payload->>'connection_id')::uuid;
  v_mode := (p_payload->>'execution_mode')::provider_execution_mode;
  v_domains := coalesce(
    array(select jsonb_array_elements_text(p_payload->'allowed_api_domains')),
    '{}'::text[]
  );
  v_health := p_payload->'health';
  if v_health is not null and v_health->>'status' = 'passed' then
    v_test_status := 'passed';
    v_tested_at := now();
  elsif v_health is not null and v_health->>'status' = 'failed' then
    v_test_status := 'failed';
    v_tested_at := now();
  end if;
  v_enabled := coalesce((p_payload->>'enabled')::boolean, false)
    and v_test_status = 'passed';

  insert into ai_providers (
    id, key, display_name, family, allowed_api_domains, enabled
  )
  values (
    coalesce(nullif(p_payload->>'provider_id', '')::uuid, gen_random_uuid()),
    p_payload->>'provider_key',
    p_payload->>'display_name',
    case when v_mode in ('cli', 'codex_cli') then 'cli' else p_payload->>'protocol' end,
    v_domains,
    v_enabled
  )
  on conflict (key) do update
  set display_name = excluded.display_name,
      family = excluded.family,
      allowed_api_domains = excluded.allowed_api_domains,
      enabled = excluded.enabled,
      retired_at = null,
      updated_at = now()
  returning id into v_provider_id;

  insert into provider_connections (
    id, provider_id, version, execution_mode, runtime_key, protocol,
    api_url, executable_path, model_id, model_catalog, custom_model_ids,
    capability_profile, generation_parameters, enabled, test_status, tested_at
  )
  values (
    v_connection_id,
    v_provider_id,
    (p_payload->>'connection_version')::integer,
    v_mode,
    nullif(p_payload->>'runtime_key', ''),
    p_payload->>'protocol',
    nullif(p_payload->>'api_url', ''),
    nullif(p_payload->>'executable_path', ''),
    p_payload->>'model_id',
    coalesce(v_health->'models', '[]'::jsonb),
    coalesce(
      array(select jsonb_array_elements_text(p_payload->'custom_model_ids')),
      '{}'::text[]
    ),
    coalesce(p_payload->'capability_profile', '{}'::jsonb),
    coalesce(p_payload->'generation_parameters', '{}'::jsonb),
    v_enabled,
    v_test_status,
    v_tested_at
  )
  on conflict (id) do nothing;

  if not found then
    if not exists (
      select 1
      from provider_connections c
      where c.id = v_connection_id
        and c.provider_id = v_provider_id
        and c.version = (p_payload->>'connection_version')::integer
    ) then
      raise exception 'connection id is already used by another version'
        using errcode = '23505';
    end if;
  end if;

  if v_health is not null then
    insert into provider_connection_health (
      connection_id, connection_version, status, detected_version,
      auth_status, available_models, checked_at, error_code,
      error_message_masked, metadata
    )
    values (
      v_connection_id,
      (p_payload->>'connection_version')::integer,
      coalesce(v_health->>'status', 'untested'),
      nullif(v_health->>'version', ''),
      coalesce(v_health->>'auth_status', 'unknown'),
      coalesce(v_health->'models', '[]'::jsonb),
      now(),
      nullif(v_health->>'error_code', ''),
      nullif(v_health->>'error_message_masked', ''),
      coalesce(v_health->'metadata', '{}'::jsonb)
    )
    on conflict (connection_id, connection_version) do update
    set status = excluded.status,
        detected_version = excluded.detected_version,
        auth_status = excluded.auth_status,
        available_models = excluded.available_models,
        checked_at = excluded.checked_at,
        error_code = excluded.error_code,
        error_message_masked = excluded.error_message_masked,
        metadata = excluded.metadata;
  end if;

  if p_payload->'encrypted_secret' is not null then
    insert into provider_secrets (
      connection_id, connection_version, ciphertext, ciphertext_nonce,
      wrapped_dek, wrapped_dek_nonce, kek_version, secret_tail
    )
    values (
      v_connection_id,
      (p_payload->>'connection_version')::integer,
      decode(p_payload#>>'{encrypted_secret,ciphertext}', 'hex'),
      decode(p_payload#>>'{encrypted_secret,ciphertext_nonce}', 'hex'),
      decode(p_payload#>>'{encrypted_secret,wrapped_dek}', 'hex'),
      decode(p_payload#>>'{encrypted_secret,wrapped_dek_nonce}', 'hex'),
      (p_payload#>>'{encrypted_secret,kek_version}')::integer,
      p_payload#>>'{encrypted_secret,secret_tail}'
    )
    on conflict (connection_id, connection_version) do nothing;
  end if;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id,
    'save_provider',
    'provider_connection',
    v_connection_id::text,
    p_request_id,
    jsonb_build_object(
      'provider_key', p_payload->>'provider_key',
      'execution_mode', v_mode,
      'connection_version', (p_payload->>'connection_version')::integer,
      'enabled', v_enabled,
      'test_status', v_test_status,
      'secret_action', case
        when p_payload->'encrypted_secret' is not null then 'replaced'
        when coalesce((p_payload->>'clear_secret')::boolean, false) then 'cleared'
        else 'unchanged'
      end
    )
  );

  return jsonb_build_object(
    'provider_id', v_provider_id,
    'connection_id', v_connection_id,
    'connection_version', (p_payload->>'connection_version')::integer,
    'enabled', v_enabled,
    'test_status', v_test_status
  );
end;
$$;

create function alea_query_provider_secret(
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
  v_secret jsonb;
begin
  perform alea_assert_admin_actor(p_actor_id);
  select jsonb_build_object(
    'ciphertext', encode(s.ciphertext, 'hex'),
    'ciphertext_nonce', encode(s.ciphertext_nonce, 'hex'),
    'wrapped_dek', encode(s.wrapped_dek, 'hex'),
    'wrapped_dek_nonce', encode(s.wrapped_dek_nonce, 'hex'),
    'kek_version', s.kek_version,
    'secret_tail', s.secret_tail
  )
  into v_secret
  from provider_secrets s
  join provider_connections c
    on c.id = s.connection_id and c.version = s.connection_version
  join ai_providers p on p.id = c.provider_id
  where s.connection_id = (p_params->>'connection_id')::uuid
    and s.connection_version = (p_params->>'connection_version')::integer
    and p.key = p_params->>'provider_key'
    and p.retired_at is null
    and s.disabled_at is null
    and c.execution_mode = 'api';
  return v_secret;
end;
$$;

create function alea_command_clear_provider_secret(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_connection_id uuid;
  v_provider_id uuid;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_connection_id := (p_payload->>'connection_id')::uuid;

  select provider_id into v_provider_id
  from provider_connections
  where id = v_connection_id;
  if v_provider_id is null then
    raise exception 'provider connection not found' using errcode = 'P0002';
  end if;

  update provider_secrets
  set disabled_at = now()
  where connection_id = v_connection_id
    and disabled_at is null;
  update provider_connections
  set enabled = false, updated_at = now()
  where id = v_connection_id;
  update ai_instances
  set enabled = false, updated_at = now()
  where connection_id = v_connection_id;
  update ai_providers p
  set enabled = exists (
    select 1 from provider_connections c
    where c.provider_id = p.id and c.enabled
  ),
  updated_at = now()
  where p.id = v_provider_id;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id, 'clear_provider_secret', 'provider_connection',
    v_connection_id::text, p_request_id, '{}'::jsonb
  );
  return jsonb_build_object('connection_id', v_connection_id, 'secret_cleared', true);
end;
$$;

create function alea_command_retire_provider(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_provider_id uuid;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_provider_id := (p_payload->>'provider_id')::uuid;
  update ai_providers
  set enabled = false, retired_at = now(), updated_at = now()
  where id = v_provider_id;
  if not found then
    raise exception 'provider not found' using errcode = 'P0002';
  end if;
  update provider_connections
  set enabled = false, updated_at = now()
  where provider_id = v_provider_id;
  update ai_instances
  set enabled = false, updated_at = now()
  where provider_id = v_provider_id;
  update provider_secrets s
  set disabled_at = now()
  from provider_connections c
  where c.id = s.connection_id
    and c.provider_id = v_provider_id
    and s.disabled_at is null;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id, 'retire_provider', 'ai_provider',
    v_provider_id::text, p_request_id, '{}'::jsonb
  );
  return jsonb_build_object('provider_id', v_provider_id, 'enabled', false);
end;
$$;

create function alea_command_create_provider_instance(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_provider_id uuid;
  v_connection_id uuid;
  v_instance_id uuid;
  v_enabled boolean;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_provider_id := (p_payload->>'provider_id')::uuid;
  v_connection_id := (p_payload->>'connection_id')::uuid;
  v_enabled := coalesce((p_payload->>'enabled')::boolean, false);

  if v_enabled and not exists (
    select 1
    from provider_connections c
    left join provider_connection_health h
      on h.connection_id = c.id and h.connection_version = c.version
    where c.id = v_connection_id
      and c.provider_id = v_provider_id
      and c.enabled
      and c.test_status = 'passed'
      and coalesce(h.auth_status, 'not_required') not in ('unauthenticated', 'error')
  ) then
    raise exception 'instance requires a tested enabled connection' using errcode = '23514';
  end if;

  insert into ai_instances (
    provider_id, connection_id, nickname, instance_number, model_id,
    reasoning_level, timeout_seconds, max_concurrency, prompt_version, enabled
  )
  values (
    v_provider_id,
    v_connection_id,
    p_payload->>'nickname',
    (p_payload->>'instance_number')::smallint,
    p_payload->>'model_id',
    nullif(p_payload->>'reasoning_level', ''),
    (p_payload->>'timeout_seconds')::integer,
    (p_payload->>'max_concurrency')::integer,
    p_payload->>'prompt_version',
    v_enabled
  )
  returning id into v_instance_id;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id,
    'create_provider_instance',
    'ai_instance',
    v_instance_id::text,
    p_request_id,
    jsonb_build_object(
      'provider_id', v_provider_id,
      'connection_id', v_connection_id,
      'instance_number', (p_payload->>'instance_number')::integer,
      'enabled', v_enabled
    )
  );
  return jsonb_build_object('instance_id', v_instance_id);
end;
$$;

create function alea_command_update_provider_instance(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_instance_id uuid;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_instance_id := (p_payload->>'instance_id')::uuid;
  if coalesce((p_payload->>'enabled')::boolean, false) and not exists (
    select 1
    from provider_connections c
    left join provider_connection_health h
      on h.connection_id = c.id and h.connection_version = c.version
    where c.id = (p_payload->>'connection_id')::uuid
      and c.provider_id = (p_payload->>'provider_id')::uuid
      and c.enabled
      and c.test_status = 'passed'
      and coalesce(h.auth_status, 'not_required') not in ('unauthenticated', 'error')
  ) then
    raise exception 'instance requires a tested enabled connection' using errcode = '23514';
  end if;
  update ai_instances
  set nickname = p_payload->>'nickname',
      connection_id = (p_payload->>'connection_id')::uuid,
      instance_number = (p_payload->>'instance_number')::smallint,
      model_id = p_payload->>'model_id',
      reasoning_level = nullif(p_payload->>'reasoning_level', ''),
      timeout_seconds = (p_payload->>'timeout_seconds')::integer,
      max_concurrency = (p_payload->>'max_concurrency')::integer,
      prompt_version = p_payload->>'prompt_version',
      enabled = coalesce((p_payload->>'enabled')::boolean, false),
      updated_at = now()
  where id = v_instance_id
    and provider_id = (p_payload->>'provider_id')::uuid;
  if not found then
    raise exception 'provider instance not found' using errcode = 'P0002';
  end if;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id,
    'update_provider_instance',
    'ai_instance',
    v_instance_id::text,
    p_request_id,
    jsonb_build_object('enabled', coalesce((p_payload->>'enabled')::boolean, false))
  );
  return jsonb_build_object('instance_id', v_instance_id);
end;
$$;

create function alea_command_delete_provider_instance(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_instance_id uuid;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  v_instance_id := (p_payload->>'instance_id')::uuid;
  update ai_instances
  set enabled = false,
      updated_at = now()
  where id = v_instance_id
    and provider_id = (p_payload->>'provider_id')::uuid;
  if not found then
    raise exception 'provider instance not found' using errcode = 'P0002';
  end if;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id,
    'retire_provider_instance',
    'ai_instance',
    v_instance_id::text,
    p_request_id,
    '{}'::jsonb
  );
  return jsonb_build_object('instance_id', v_instance_id, 'enabled', false);
end;
$$;

revoke all on function alea_assert_admin_actor(text) from public;
revoke all on function alea_query_list_providers(text, jsonb) from public;
revoke all on function alea_query_provider_secret(text, jsonb) from public;
revoke all on function alea_command_save_provider(text, text, jsonb) from public;
revoke all on function alea_command_clear_provider_secret(text, text, jsonb) from public;
revoke all on function alea_command_retire_provider(text, text, jsonb) from public;
revoke all on function alea_command_create_provider_instance(text, text, jsonb) from public;
revoke all on function alea_command_update_provider_instance(text, text, jsonb) from public;
revoke all on function alea_command_delete_provider_instance(text, text, jsonb) from public;

grant execute on function alea_query_list_providers(text, jsonb) to alea_api;
grant execute on function alea_query_provider_secret(text, jsonb) to alea_api;
grant execute on function alea_command_save_provider(text, text, jsonb) to alea_api;
grant execute on function alea_command_clear_provider_secret(text, text, jsonb) to alea_api;
grant execute on function alea_command_retire_provider(text, text, jsonb) to alea_api;
grant execute on function alea_command_create_provider_instance(text, text, jsonb) to alea_api;
grant execute on function alea_command_update_provider_instance(text, text, jsonb)
  to alea_api;
grant execute on function alea_command_delete_provider_instance(text, text, jsonb)
  to alea_api;

create function alea_command_import_fixture_data(
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
  v_source_id uuid;
  v_run_id uuid;
  v_record jsonb;
  v_source_record_id uuid;
  v_competition_id uuid;
  v_season_id uuid;
  v_home_team_id uuid;
  v_away_team_id uuid;
  v_match_id uuid;
  v_existing matches%rowtype;
  v_odds jsonb;
  v_seen integer := 0;
  v_accepted integer := 0;
  v_conflicted integer := 0;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  if p_payload->>'fixture_kind' <> 'sporttery_sales_fixture'
     or jsonb_typeof(p_payload->'records') <> 'array'
     or jsonb_array_length(p_payload->'records') = 0 then
    raise exception 'invalid fixture import' using errcode = '22023';
  end if;

  select id into v_source_id
  from data_sources
  where key = 'gate0_fixture'
    and kind = 'fixture'
    and enabled
    and status = 'ready';
  if v_source_id is null then
    raise exception 'gate0 fixture source is unavailable' using errcode = '55000';
  end if;

  insert into sync_runs (
    data_source_id, status, scope, parser_version, attempt,
    started_at, heartbeat_at, created_by
  )
  values (
    v_source_id, 'running',
    jsonb_build_object('kind', 'admin_fixture_import', 'request_id', p_request_id),
    p_payload->>'parser_version', 1, now(), now(), v_actor_id
  )
  returning id into v_run_id;

  begin
    for v_record in select value from jsonb_array_elements(p_payload->'records')
    loop
    v_seen := v_seen + 1;
    insert into source_records (
      data_source_id, sync_run_id, source_record_key, sporttery_match_number,
      source_url, business_date, observed_at, parser_version, raw_content,
      raw_content_hash, state, parsed_payload
    )
    values (
      v_source_id,
      v_run_id,
      v_record->>'source_record_key',
      v_record->>'sporttery_match_number',
      nullif(v_record->>'source_url', ''),
      (v_record->>'business_date')::date,
      (v_record->>'observed_at')::timestamptz,
      v_record->>'parser_version',
      v_record->'raw_content',
      v_record->>'raw_content_hash',
      'parsed',
      v_record - 'raw_content'
    )
    on conflict (data_source_id, source_record_key, raw_content_hash) do update
    set sync_run_id = excluded.sync_run_id,
        collected_at = now()
    returning id into v_source_record_id;

    insert into competitions (
      name, country_code, competition_type, sporttery_eligible
    )
    values (
      v_record#>>'{competition,name}',
      v_record#>>'{competition,country_code}',
      v_record#>>'{competition,competition_type}',
      true
    )
    on conflict (name, country_code) do update
    set competition_type = excluded.competition_type,
        sporttery_eligible = true,
        updated_at = now()
    returning id into v_competition_id;

    insert into entity_mappings (
      data_source_id, entity_type, source_entity_key, canonical_entity_id,
      source_record_id, mapping_status, confirmed_by, confirmed_at
    )
    values (
      v_source_id, 'competition', v_record#>>'{competition,source_key}',
      v_competition_id, v_source_record_id, 'confirmed', v_actor_id, now()
    )
    on conflict (data_source_id, entity_type, source_entity_key) do update
    set canonical_entity_id = excluded.canonical_entity_id,
        source_record_id = excluded.source_record_id,
        mapping_status = 'confirmed',
        confirmed_by = excluded.confirmed_by,
        confirmed_at = excluded.confirmed_at;

    v_season_id := null;
    if jsonb_typeof(v_record->'season') = 'object' then
      insert into competition_seasons (
        competition_id, name, starts_on, ends_on
      )
      values (
        v_competition_id,
        v_record#>>'{season,name}',
        nullif(v_record#>>'{season,starts_on}', '')::date,
        nullif(v_record#>>'{season,ends_on}', '')::date
      )
      on conflict (competition_id, name) do update
      set starts_on = excluded.starts_on,
          ends_on = excluded.ends_on
      returning id into v_season_id;
      insert into entity_mappings (
        data_source_id, entity_type, source_entity_key, canonical_entity_id,
        source_record_id, mapping_status, confirmed_by, confirmed_at
      )
      values (
        v_source_id, 'season', v_record#>>'{season,source_key}',
        v_season_id, v_source_record_id, 'confirmed', v_actor_id, now()
      )
      on conflict (data_source_id, entity_type, source_entity_key) do update
      set canonical_entity_id = excluded.canonical_entity_id,
          source_record_id = excluded.source_record_id,
          mapping_status = 'confirmed',
          confirmed_by = excluded.confirmed_by,
          confirmed_at = excluded.confirmed_at;
    end if;

    insert into teams (name, country_code)
    values (
      v_record#>>'{home_team,name}',
      v_record#>>'{home_team,country_code}'
    )
    on conflict (name, country_code) do update
    set updated_at = now()
    returning id into v_home_team_id;
    insert into teams (name, country_code)
    values (
      v_record#>>'{away_team,name}',
      v_record#>>'{away_team,country_code}'
    )
    on conflict (name, country_code) do update
    set updated_at = now()
    returning id into v_away_team_id;

    insert into entity_mappings (
      data_source_id, entity_type, source_entity_key, canonical_entity_id,
      source_record_id, mapping_status, confirmed_by, confirmed_at
    )
    values
      (
        v_source_id, 'team', v_record#>>'{home_team,source_key}',
        v_home_team_id, v_source_record_id, 'confirmed', v_actor_id, now()
      ),
      (
        v_source_id, 'team', v_record#>>'{away_team,source_key}',
        v_away_team_id, v_source_record_id, 'confirmed', v_actor_id, now()
      )
    on conflict (data_source_id, entity_type, source_entity_key) do update
    set canonical_entity_id = excluded.canonical_entity_id,
        source_record_id = excluded.source_record_id,
        mapping_status = 'confirmed',
        confirmed_by = excluded.confirmed_by,
        confirmed_at = excluded.confirmed_at;

    select * into v_existing
    from matches
    where business_date = (v_record->>'business_date')::date
      and sporttery_match_number = v_record->>'sporttery_match_number';

    if v_existing.id is not null and (
      v_existing.competition_id <> v_competition_id
      or v_existing.home_team_id <> v_home_team_id
      or v_existing.away_team_id <> v_away_team_id
      or v_existing.kickoff_at <> (v_record->>'kickoff_at')::timestamptz
    ) then
      if v_existing.canonical_source_record_id is not null
         and v_existing.canonical_source_record_id <> v_source_record_id
         and not exists (
           select 1 from data_conflicts dc
           where dc.match_id = v_existing.id
             and dc.status = 'pending'
             and v_source_record_id = any(dc.candidate_source_record_ids)
         ) then
        insert into data_conflicts (
          match_id, field_path, candidate_source_record_ids
        )
        values (
          v_existing.id,
          'match_identity',
          array[v_existing.canonical_source_record_id, v_source_record_id]
        );
      end if;
      update matches set fact_state = 'conflict', updated_at = now()
      where id = v_existing.id;
      update source_records set state = 'conflict'
      where id = v_source_record_id;
      v_conflicted := v_conflicted + 1;
      continue;
    end if;

    insert into matches (
      competition_id, season_id, home_team_id, away_team_id, kickoff_at,
      business_date, sporttery_match_number, sales_status, sales_cutoff_at,
      fact_state, canonical_source_record_id
    )
    values (
      v_competition_id,
      v_season_id,
      v_home_team_id,
      v_away_team_id,
      (v_record->>'kickoff_at')::timestamptz,
      (v_record->>'business_date')::date,
      v_record->>'sporttery_match_number',
      v_record->>'sales_status',
      nullif(v_record->>'sales_cutoff_at', '')::timestamptz,
      'fixture',
      v_source_record_id
    )
    on conflict (business_date, sporttery_match_number) do update
    set sales_status = excluded.sales_status,
        sales_cutoff_at = excluded.sales_cutoff_at,
        canonical_source_record_id = excluded.canonical_source_record_id,
        updated_at = now()
    returning id into v_match_id;

    insert into entity_mappings (
      data_source_id, entity_type, source_entity_key, canonical_entity_id,
      source_record_id, mapping_status, confirmed_by, confirmed_at
    )
    values (
      v_source_id, 'match', v_record->>'source_record_key',
      v_match_id, v_source_record_id, 'confirmed', v_actor_id, now()
    )
    on conflict (data_source_id, entity_type, source_entity_key) do update
    set canonical_entity_id = excluded.canonical_entity_id,
        source_record_id = excluded.source_record_id,
        mapping_status = 'confirmed',
        confirmed_by = excluded.confirmed_by,
        confirmed_at = excluded.confirmed_at;

    for v_odds in select value from jsonb_array_elements(coalesce(v_record->'odds', '[]'::jsonb))
    loop
      insert into match_odds_snapshots (
        match_id, source_record_id, play_type, values, observed_at
      )
      values (
        v_match_id, v_source_record_id, v_odds->>'play_type',
        v_odds->'values', (v_odds->>'observed_at')::timestamptz
      )
      on conflict (match_id, source_record_id, play_type) do nothing;
    end loop;

    if jsonb_typeof(v_record->'result') = 'object'
       and not exists (
         select 1 from match_results
         where match_id = v_match_id and source_record_id = v_source_record_id
       ) then
      insert into match_results (
        match_id, source_record_id, result_version, home_score, away_score, status
      )
      values (
        v_match_id,
        v_source_record_id,
        coalesce((select max(result_version) + 1 from match_results where match_id = v_match_id), 1),
        (v_record#>>'{result,home_score}')::integer,
        (v_record#>>'{result,away_score}')::integer,
        'pending'
      );
    end if;

    update source_records set state = 'mapped'
    where id = v_source_record_id;
      v_accepted := v_accepted + 1;
    end loop;
  exception
    when others then
      update sync_runs
      set status = 'failed',
          records_seen = v_seen,
          records_accepted = 0,
          records_conflicted = 0,
          last_error_code = sqlstate,
          last_error_masked = 'fixture_import_failed',
          heartbeat_at = now(),
          completed_at = now()
      where id = v_run_id;
      insert into admin_audit_logs (
        actor_id, action, target_type, target_id, request_id, detail_redacted
      )
      values (
        v_actor_id, 'import_fixture_data_failed', 'sync_run', v_run_id::text,
        p_request_id, jsonb_build_object('error_code', sqlstate)
      );
      return jsonb_build_object(
        'run_id', v_run_id,
        'status', 'failed',
        'error_code', 'fixture_import_failed'
      );
  end;

  update sync_runs
  set status = 'succeeded',
      records_seen = v_seen,
      records_accepted = v_accepted,
      records_conflicted = v_conflicted,
      heartbeat_at = now(),
      completed_at = now()
  where id = v_run_id;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id, 'import_fixture_data', 'sync_run', v_run_id::text,
    p_request_id,
    jsonb_build_object(
      'parser_version', p_payload->>'parser_version',
      'records_seen', v_seen,
      'records_accepted', v_accepted,
      'records_conflicted', v_conflicted
    )
  );
  return jsonb_build_object(
    'run_id', v_run_id,
    'status', 'succeeded',
    'records_seen', v_seen,
    'records_accepted', v_accepted,
    'records_conflicted', v_conflicted
  );
end;
$$;

create function alea_command_trigger_sync(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  if not exists (
    select 1 from data_sources
    where enabled
      and kind <> 'fixture'
      and status in ('ready', 'degraded')
      and (
        kind <> 'sporttery_web'
        or (
          authorization_status = 'authorized'
          and authorization_reference is not null
        )
      )
  ) then
    insert into admin_audit_logs (
      actor_id, action, target_type, target_id, request_id, detail_redacted
    )
    values (
      v_actor_id, 'trigger_sync_unavailable', 'data_source', 'none',
      p_request_id, jsonb_build_object('scope', p_payload)
    );
    return jsonb_build_object(
      'status', 'unavailable',
      'error_code', 'no_authorized_data_source'
    );
  end if;
  return jsonb_build_object('status', 'unavailable', 'error_code', 'sync_worker_not_configured');
end;
$$;

create function alea_query_list_sync_runs(
  p_actor_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
begin
  perform alea_assert_admin_actor(p_actor_id);
  return jsonb_build_object(
    'runs',
    coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'id', r.id,
          'source_key', s.key,
          'source_name', s.display_name,
          'status', r.status,
          'scope', r.scope,
          'cursor', r.cursor,
          'parser_version', r.parser_version,
          'records_seen', r.records_seen,
          'records_accepted', r.records_accepted,
          'records_conflicted', r.records_conflicted,
          'attempt', r.attempt,
          'last_error_code', r.last_error_code,
          'last_error_masked', r.last_error_masked,
          'started_at', r.started_at,
          'completed_at', r.completed_at,
          'created_at', r.created_at
        )
        order by r.created_at desc
      )
      from (
        select *
        from sync_runs
        order by created_at desc
        limit least(greatest(coalesce((p_params->>'limit')::integer, 50), 1), 200)
      ) r
      join data_sources s on s.id = r.data_source_id
    ), '[]'::jsonb),
    'next_cursor', null
  );
end;
$$;

create function alea_command_retry_sync_run(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_run sync_runs%rowtype;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  select * into v_run from sync_runs where id = (p_payload->>'run_id')::uuid;
  if v_run.id is null then
    raise exception 'sync run not found' using errcode = 'P0002';
  end if;
  if v_run.status <> 'failed' then
    raise exception 'only failed sync runs can be retried' using errcode = '23514';
  end if;
  update sync_runs
  set status = 'pending',
      attempt = attempt + 1,
      last_error_code = null,
      last_error_masked = null,
      completed_at = null,
      heartbeat_at = now()
  where id = v_run.id;
  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id, 'retry_sync_run', 'sync_run', v_run.id::text,
    p_request_id, jsonb_build_object('attempt', v_run.attempt + 1)
  );
  return jsonb_build_object('run_id', v_run.id, 'status', 'pending');
end;
$$;

create function alea_query_list_result_conflicts(
  p_actor_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
begin
  perform alea_assert_admin_actor(p_actor_id);
  if p_params <> '{}'::jsonb then
    raise exception 'list_result_conflicts does not accept parameters' using errcode = '22023';
  end if;
  return jsonb_build_object(
    'conflicts',
    coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'id', dc.id,
          'match_id', dc.match_id,
          'field_path', dc.field_path,
          'candidate_source_record_ids', dc.candidate_source_record_ids,
          'status', dc.status,
          'accepted_source_record_id', dc.accepted_source_record_id,
          'decision_reason', dc.decision_reason,
          'decided_at', dc.decided_at,
          'created_at', dc.created_at
        )
        order by dc.created_at desc
      )
      from data_conflicts dc
      where dc.status = 'pending'
    ), '[]'::jsonb)
  );
end;
$$;

create function alea_command_adjudicate_result(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor_id uuid;
  v_conflict data_conflicts%rowtype;
  v_result match_results%rowtype;
begin
  v_actor_id := alea_assert_admin_actor(p_actor_id);
  select * into v_conflict
  from data_conflicts
  where id = (p_payload->>'conflict_id')::uuid
    and status = 'pending'
  for update;
  if v_conflict.id is null then
    raise exception 'pending conflict not found' using errcode = 'P0002';
  end if;
  select * into v_result
  from match_results
  where id = (p_payload->>'result_version_id')::uuid
    and match_id = v_conflict.match_id;
  if v_result.id is null
     or not (v_result.source_record_id = any(v_conflict.candidate_source_record_ids))
     or not (v_result.source_record_id::text in (
       select jsonb_array_elements_text(p_payload->'source_record_ids')
     )) then
    raise exception 'result is not a conflict candidate' using errcode = '23514';
  end if;

  update match_results
  set status = case when id = v_result.id then 'confirmed' else 'rejected' end,
      confirmed_by = case when id = v_result.id then v_actor_id else null end,
      confirmed_at = case when id = v_result.id then now() else null end
  where match_id = v_conflict.match_id
    and source_record_id = any(v_conflict.candidate_source_record_ids);
  update data_conflicts
  set status = 'accepted',
      accepted_source_record_id = v_result.source_record_id,
      decision_reason = p_payload->>'reason',
      decided_by = v_actor_id,
      decided_at = now()
  where id = v_conflict.id;
  update matches
  set fact_state = 'verified', updated_at = now()
  where id = v_conflict.match_id;

  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, request_id, detail_redacted
  )
  values (
    v_actor_id, 'adjudicate_result', 'data_conflict', v_conflict.id::text,
    p_request_id,
    jsonb_build_object(
      'result_version_id', v_result.id,
      'accepted_source_record_id', v_result.source_record_id
    )
  );
  return jsonb_build_object(
    'conflict_id', v_conflict.id,
    'status', 'accepted',
    'result_version_id', v_result.id
  );
end;
$$;

create function alea_query_list_matches(
  p_viewer_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_viewer uuid;
begin
  v_viewer := p_viewer_id::uuid;
  if not exists (select 1 from profiles where id = v_viewer and status = 'active') then
    raise exception 'active profile required' using errcode = '42501';
  end if;
  return jsonb_build_object(
    'matches',
    coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'match_id', m.id,
          'competition', c.name,
          'home_team', ht.name,
          'away_team', at.name,
          'kickoff_at', m.kickoff_at,
          'sales_cutoff_at', m.sales_cutoff_at,
          'state', m.sales_status,
          'data_completeness', case when m.fact_state = 'unavailable' then 0.0 else 1.0 end,
          'missing_fields', case when m.fact_state = 'conflict'
            then jsonb_build_array('conflict') else '[]'::jsonb end,
          'latest_observed_at', sr.observed_at
        )
        order by m.kickoff_at, m.id
      )
      from (
        select *
        from matches
        where (
          nullif(p_params->>'business_date', '') is null
          or business_date = (p_params->>'business_date')::date
        )
        and (
          nullif(p_params->>'state', '') is null
          or sales_status = p_params->>'state'
        )
        order by kickoff_at, id
        limit least(greatest(coalesce((p_params->>'limit')::integer, 50), 1), 200)
      ) m
      join competitions c on c.id = m.competition_id
      join teams ht on ht.id = m.home_team_id
      join teams at on at.id = m.away_team_id
      left join source_records sr on sr.id = m.canonical_source_record_id
    ), '[]'::jsonb),
    'next_cursor', null,
    'freshness_state', case
      when exists (select 1 from matches where fact_state = 'fixture') then 'fixture'
      else 'available'
    end
  );
end;
$$;

create function alea_query_get_match(
  p_viewer_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_viewer uuid;
  v_result jsonb;
begin
  v_viewer := p_viewer_id::uuid;
  if not exists (select 1 from profiles where id = v_viewer and status = 'active') then
    raise exception 'active profile required' using errcode = '42501';
  end if;
  select jsonb_build_object(
    'match_id', m.id,
    'competition', c.name,
    'home_team', ht.name,
    'away_team', at.name,
    'kickoff_at', m.kickoff_at,
    'business_date', m.business_date,
    'sporttery_match_number', m.sporttery_match_number,
    'sales_status', m.sales_status,
    'sales_cutoff_at', m.sales_cutoff_at,
    'fact_state', m.fact_state,
    'source_record_ids', case when m.canonical_source_record_id is null
      then '[]'::jsonb else jsonb_build_array(m.canonical_source_record_id) end,
    'missing_fields', case when m.fact_state = 'conflict'
      then jsonb_build_array('conflict') else '[]'::jsonb end
  )
  into v_result
  from matches m
  join competitions c on c.id = m.competition_id
  join teams ht on ht.id = m.home_team_id
  join teams at on at.id = m.away_team_id
  where m.id = (p_params->>'match_id')::uuid;
  return v_result;
end;
$$;

create function alea_query_get_match_sources(
  p_viewer_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_viewer uuid;
begin
  v_viewer := p_viewer_id::uuid;
  if not exists (select 1 from profiles where id = v_viewer and status = 'active') then
    raise exception 'active profile required' using errcode = '42501';
  end if;
  return coalesce((
    select jsonb_agg(
      jsonb_build_object(
        'source_record_id', sr.id::text,
        'source_label', ds.display_name,
        'observed_at', sr.observed_at,
        'valid_from', null,
        'expires_at', null,
        'confidence', case when ds.kind = 'fixture' then 0.0 else 1.0 end,
        'missing_fields', case when ds.kind = 'fixture'
          then jsonb_build_array('fixture_not_official') else '[]'::jsonb end
      )
      order by sr.observed_at desc
    )
    from matches m
    join source_records sr
      on sr.id = m.canonical_source_record_id
      or sr.id in (
        select unnest(dc.candidate_source_record_ids)
        from data_conflicts dc
        where dc.match_id = m.id
      )
    join data_sources ds on ds.id = sr.data_source_id
    where m.id = (p_params->>'match_id')::uuid
  ), '[]'::jsonb);
end;
$$;

revoke all on function alea_command_import_fixture_data(text, text, jsonb) from public;
revoke all on function alea_command_trigger_sync(text, text, jsonb) from public;
revoke all on function alea_query_list_sync_runs(text, jsonb) from public;
revoke all on function alea_command_retry_sync_run(text, text, jsonb) from public;
revoke all on function alea_query_list_result_conflicts(text, jsonb) from public;
revoke all on function alea_command_adjudicate_result(text, text, jsonb) from public;
revoke all on function alea_query_list_matches(text, jsonb) from public;
revoke all on function alea_query_get_match(text, jsonb) from public;
revoke all on function alea_query_get_match_sources(text, jsonb) from public;

grant execute on function alea_command_import_fixture_data(text, text, jsonb) to alea_api;
grant execute on function alea_command_trigger_sync(text, text, jsonb) to alea_api;
grant execute on function alea_query_list_sync_runs(text, jsonb) to alea_api;
grant execute on function alea_command_retry_sync_run(text, text, jsonb) to alea_api;
grant execute on function alea_query_list_result_conflicts(text, jsonb) to alea_api;
grant execute on function alea_command_adjudicate_result(text, text, jsonb) to alea_api;
grant execute on function alea_query_list_matches(text, jsonb) to alea_api;
grant execute on function alea_query_get_match(text, jsonb) to alea_api;
grant execute on function alea_query_get_match_sources(text, jsonb) to alea_api;

-- One-time administrator bootstrap. The protected profile trigger only accepts
-- this bypass from a migration-level database session while no administrator
-- exists. Runtime roles cannot set the bypass by themselves.
create or replace function protect_profile_privileges()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if (new.role, new.status) is distinct from (old.role, old.status)
     and not is_admin()
     and not (
       old.id = auth.uid()
       and old.role = 'user'
       and new.role = 'user'
       and old.status = 'pending_consent'
       and new.status = 'active'
       and current_setting('app.consent_activation', true) = 'allowed'
     )
     and not (
       session_user in ('postgres', 'supabase_admin')
       and current_setting('app.bootstrap_first_admin', true) = 'allowed'
       and not exists (
         select 1 from profiles where role = 'admin' and status = 'active'
       )
     ) then
    raise exception 'profile role and status require an administrator' using errcode = '42501';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

create function alea_bootstrap_first_admin(
  p_user_id uuid,
  p_reason text,
  p_environment text
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth, pg_temp
as $$
begin
  if session_user not in ('postgres', 'supabase_admin') then
    raise exception 'migration-level database role required' using errcode = '42501';
  end if;
  if exists (select 1 from profiles where role = 'admin' and status = 'active') then
    raise exception 'an active administrator already exists' using errcode = '23505';
  end if;
  if not exists (select 1 from auth.users where id = p_user_id) then
    raise exception 'auth user not found' using errcode = 'P0002';
  end if;

  perform set_config('app.bootstrap_first_admin', 'allowed', true);
  insert into profiles (id, role, status)
  values (p_user_id, 'admin', 'active')
  on conflict (id) do update
  set role = 'admin', status = 'active', updated_at = now();

  insert into admin_role_grants (
    user_id, action, granted_by, reason, active
  )
  values (p_user_id, 'grant', null, p_reason, true);
  insert into admin_audit_logs (
    actor_id, action, target_type, target_id, detail_redacted
  )
  values (
    null, 'bootstrap_admin', 'profile', p_user_id::text,
    jsonb_build_object('environment', p_environment)
  );
  return jsonb_build_object('user_id', p_user_id, 'status', 'active', 'role', 'admin');
end;
$$;

revoke all on function protect_profile_privileges() from public, anon, authenticated,
  service_role, alea_api, alea_worker, alea_dispatcher, alea_scheduler;
revoke all on function alea_bootstrap_first_admin(uuid, text, text) from public, anon,
  authenticated, service_role, alea_api, alea_worker, alea_dispatcher, alea_scheduler;
