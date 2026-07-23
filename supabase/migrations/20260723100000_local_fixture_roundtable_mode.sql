-- Allow an explicit, non-production roundtable rehearsal for administrator-provided fixtures.
-- Production Sporttery eligibility remains strict and unchanged.

create or replace function public.alea_is_local_fixture_match(
  p_match_id uuid,
  p_at timestamptz default now()
)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1
    from public.matches m
    join public.source_records canonical on canonical.id = m.canonical_source_record_id
    join public.data_sources source on source.id = canonical.data_source_id
    where m.id = p_match_id
      and m.fact_state = 'fixture'
      and m.sales_status in ('scheduled', 'on_sale')
      and m.sales_cutoff_at is not null
      and p_at < m.sales_cutoff_at
      and source.kind = 'fixture'
      and source.enabled
      and source.status = 'ready'
      and source.authorization_status = 'not_required'
      and coalesce(source.configuration->>'non_production', 'false') = 'true'
      and canonical.business_date = m.business_date
      and canonical.sporttery_match_number = m.sporttery_match_number
      and canonical.state in ('mapped', 'accepted')
      and exists (
        select 1
        from public.match_odds_snapshots odds
        join public.source_records odds_record on odds_record.id = odds.source_record_id
        where odds.match_id = m.id
          and odds.observed_at <= p_at
          and odds.observed_at <= m.sales_cutoff_at
          and odds_record.data_source_id = source.id
          and odds_record.state in ('mapped', 'accepted')
      )
  );
$$;

revoke all on function public.alea_is_local_fixture_match(uuid, timestamptz) from public;
grant execute on function public.alea_is_local_fixture_match(uuid, timestamptz) to alea_api, alea_worker;

do $migration$
declare
  v_definition text;
  v_required text;
begin
  select pg_get_functiondef(
    'public.alea_command_start_roundtable(text,text,jsonb)'::regprocedure
  ) into v_definition;

  v_required := '  v_scheduled boolean := false;' || chr(10) ||
    '  v_now timestamptz := now();';
  if position(v_required in v_definition) = 0 then
    raise exception 'local fixture migration could not locate roundtable declaration';
  end if;
  v_definition := replace(
    v_definition,
    v_required,
    '  v_scheduled boolean := false;' || chr(10) ||
    '  v_fixture_mode boolean := false;' || chr(10) ||
    '  v_now timestamptz := now();'
  );

  v_required := '  perform public.alea_assert_admin_actor(p_actor_id);';
  v_definition := replace(
    v_definition,
    v_required,
    v_required || chr(10) || chr(10) ||
    '  begin' || chr(10) ||
    '    v_fixture_mode := coalesce((v_payload->>''fixture_mode'')::boolean, false);' || chr(10) ||
    '  exception when invalid_text_representation then' || chr(10) ||
    '    raise exception ''fixture_mode must be a boolean'' using errcode = ''22023'';' || chr(10) ||
    '  end;'
  );

  v_required := 'and public.alea_is_sporttery_offer_eligible(m.id, v_now)';
  if length(v_definition) - length(replace(v_definition, v_required, '')) = 0 then
    raise exception 'local fixture migration could not locate match eligibility checks';
  end if;
  v_definition := replace(
    v_definition,
    v_required,
    'and (' || chr(10) ||
    '        public.alea_is_sporttery_offer_eligible(m.id, v_now)' || chr(10) ||
    '        or (v_fixture_mode and public.alea_is_local_fixture_match(m.id, v_now))' || chr(10) ||
    '      )'
  );

  v_required := '''scheduled'', false' || chr(10) || '    );';
  if position(v_required in v_definition) = 0 then
    raise exception 'local fixture migration could not locate delegated payload';
  end if;
  v_definition := replace(
    v_definition,
    v_required,
    '''scheduled'', false,' || chr(10) ||
    '      ''fixture_mode'', v_fixture_mode' || chr(10) ||
    '    );'
  );

  v_definition := replace(
    v_definition,
    '''selection_policy'', ''authorized_sporttery_offer_v1'',',
    '''selection_policy'', case when v_fixture_mode then ''local_fixture_v1'' else ''authorized_sporttery_offer_v1'' end,' || chr(10) ||
    '          ''fixture_mode'', v_fixture_mode,'
  );
  v_definition := replace(
    v_definition,
    '''selection_policy'', ''authorized_sporttery_offer_v1''' || chr(10) || '  );',
    '''selection_policy'', case when v_fixture_mode then ''local_fixture_v1'' else ''authorized_sporttery_offer_v1'' end,' || chr(10) ||
    '    ''fixture_mode'', v_fixture_mode' || chr(10) ||
    '  );'
  );
  execute v_definition;
end;
$migration$;

do $migration$
declare
  v_definition text;
  v_required text;
begin
  select pg_get_functiondef(
    'public.alea_worker_initialize_roundtable(uuid,text,jsonb)'::regprocedure
  ) into v_definition;

  v_required := '  v_eligible_match_count integer;';
  if position(v_required in v_definition) = 0 then
    raise exception 'local fixture migration could not locate worker declaration';
  end if;
  v_definition := replace(
    v_definition,
    v_required,
    v_required || chr(10) || '  v_fixture_mode boolean := false;'
  );

  v_required := '  if not found then' || chr(10) ||
    '    raise exception ''roundtable job not found'' using errcode = ''P0002'';' || chr(10) ||
    '  end if;';
  if position(v_required in v_definition) = 0 then
    raise exception 'local fixture migration could not locate worker job guard';
  end if;
  v_definition := replace(
    v_definition,
    v_required,
    v_required || chr(10) || chr(10) ||
    '  v_fixture_mode := coalesce((v_job.config_snapshot->>''fixture_mode'')::boolean, false);'
  );

  v_required := '    and public.alea_is_sporttery_offer_eligible(match_run.match_id, now());';
  if position(v_required in v_definition) = 0 then
    raise exception 'local fixture migration could not locate worker eligibility check';
  end if;
  v_definition := replace(
    v_definition,
    v_required,
    '    and (' || chr(10) ||
    '      public.alea_is_sporttery_offer_eligible(match_run.match_id, now())' || chr(10) ||
    '      or (v_fixture_mode and public.alea_is_local_fixture_match(match_run.match_id, now()))' || chr(10) ||
    '    );'
  );
  execute v_definition;
end;
$migration$;
