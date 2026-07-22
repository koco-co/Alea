-- Runtime dependency heartbeats used by /readyz. A missing or stale worker
-- heartbeat must keep the API out of the ready state.
create table public.service_heartbeats (
  service_name text primary key check (service_name in ('dispatcher', 'worker', 'scheduler')),
  status text not null check (status in ('starting', 'ready', 'stopping', 'failed')),
  heartbeat_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb
);

grant usage on schema supabase_migrations to alea_api;
grant select on table supabase_migrations.schema_migrations to alea_api;

alter table public.service_heartbeats enable row level security;
revoke all on public.service_heartbeats from public, anon, authenticated, service_role;
grant select on public.service_heartbeats to alea_api;
grant select, insert, update on public.service_heartbeats to alea_worker, alea_dispatcher, alea_scheduler;

create policy service_heartbeats_api_read
  on public.service_heartbeats for select to alea_api using (true);

create policy service_heartbeats_worker_write
  on public.service_heartbeats for all to alea_worker using (true) with check (true);

create policy service_heartbeats_dispatcher_write
  on public.service_heartbeats for all to alea_dispatcher using (true) with check (true);

create policy service_heartbeats_scheduler_write
  on public.service_heartbeats for all to alea_scheduler using (true) with check (true);
