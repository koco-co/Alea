-- FastAPI reads internal roundtable events through the Supabase service client.
-- Keep this backend-only; ordinary users still receive the public projection.
grant select on public.roundtable_events to service_role;
