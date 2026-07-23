-- Serialize per-roundtable event sequence allocation without taking a row lock
-- that can deadlock with concurrent phase-run/job updates.
create or replace function public.assign_roundtable_event_seq()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  perform pg_advisory_xact_lock(hashtextextended(new.job_id::text, 0));
  if not exists (select 1 from public.roundtable_jobs where id = new.job_id) then
    raise exception 'roundtable job % does not exist', new.job_id using errcode = '23503';
  end if;

  select coalesce(max(e.event_seq), 0) + 1
    into new.event_seq
    from public.roundtable_events e
   where e.job_id = new.job_id;
  return new;
end;
$$;
