-- Fix the worker role guard for the SECURITY DEFINER event append function.
-- current_user is the function owner inside a SECURITY DEFINER function;
-- session_user is the authenticated database role that invoked it.

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

revoke all on function alea_worker_append_roundtable_event(uuid, text, jsonb) from public;
grant execute on function alea_worker_append_roundtable_event(uuid, text, jsonb) to alea_worker;
