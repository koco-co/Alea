-- Allow an administrator to retry a terminal roundtable whose provider quorum
-- was not met. A successful request keeps the original business idempotency key;
-- a retry derives a stable key from the request id so duplicate HTTP delivery is
-- still idempotent while a new request can create a fresh frozen job.

do $migration$
declare
  v_definition text;
  v_required text;
begin
  select pg_get_functiondef(
    'public.alea_command_start_roundtable_unhardened_20260721(text,text,jsonb)'::regprocedure
  ) into v_definition;

  v_required := $replace$
  if v_existing_job_id is not null then
    return jsonb_build_object(
      'job_id', v_existing_job_id,
      'state', (select state from roundtable_jobs where id = v_existing_job_id),
      'business_idempotency_key', v_key,
      'idempotent', true
    );
  end if;
$replace$;
  if position(v_required in v_definition) = 0 then
    raise exception 'terminal retry migration could not locate idempotency guard';
  end if;

  v_definition := replace(
    v_definition,
    v_required,
    $replace$
  if v_existing_job_id is not null then
    if exists (
      select 1
      from roundtable_jobs existing_job
      where existing_job.id = v_existing_job_id
        and (
          existing_job.state in ('failed', 'no_quorum', 'terminated')
          or (
            existing_job.state = 'completed'
            and exists (
              select 1
              from roundtable_match_runs retry_match
              where retry_match.job_id = existing_job.id
                and retry_match.state = 'no_quorum'
            )
          )
        )
    ) then
      v_key := v_key || ':retry:' || substr(
        encode(digest(convert_to(p_request_id, 'utf8'), 'sha256'), 'hex'),
        1,
        16
      );
      v_existing_job_id := null;
    else
      return jsonb_build_object(
        'job_id', v_existing_job_id,
        'state', (select state from roundtable_jobs where id = v_existing_job_id),
        'business_idempotency_key', v_key,
        'idempotent', true
      );
    end if;
  end if;
$replace$
  );

  execute v_definition;
end;
$migration$;
