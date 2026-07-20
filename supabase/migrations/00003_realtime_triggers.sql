-- Realtime Broadcast for append-only roundtable events.

create function can_read_roundtable_topic(p_topic text)
returns boolean
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  v_job_id uuid;
begin
  if p_topic !~ '^roundtable:[0-9a-fA-F-]{36}$' then
    return false;
  end if;
  v_job_id := split_part(p_topic, ':', 2)::uuid;
  return is_admin()
    or exists (select 1 from public_execution_audits where job_id = v_job_id)
    or exists (select 1 from public_notarized_predictions where job_id = v_job_id);
exception when invalid_text_representation then
  return false;
end;
$$;

create function broadcast_roundtable_event()
returns trigger
language plpgsql
security definer
set search_path = public, realtime, pg_temp
as $$
begin
  perform realtime.broadcast_changes(
    'roundtable:' || new.job_id::text,
    tg_op,
    tg_op,
    tg_table_name,
    tg_table_schema,
    new,
    old
  );
  return null;
end;
$$;

create trigger roundtable_events_broadcast
after insert on roundtable_events
for each row execute function broadcast_roundtable_event();

alter table realtime.messages enable row level security;

create policy roundtable_broadcast_authenticated_read
on realtime.messages
for select
to authenticated
using (can_read_roundtable_topic(realtime.topic()));

-- No INSERT policy is created for anon/authenticated. Client-originated Broadcast is
-- therefore rejected; only the security-definer database trigger may publish events.
revoke insert on realtime.messages from anon, authenticated;
revoke all on function can_read_roundtable_topic(text) from public;
grant execute on function can_read_roundtable_topic(text) to authenticated;
revoke all on function broadcast_roundtable_event() from public;
