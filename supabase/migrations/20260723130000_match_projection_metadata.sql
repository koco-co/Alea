-- Expose the persisted Sporttery match number and source provenance in the
-- authenticated match projection. Consumers can distinguish a local fixture
-- from an authorized sales Offer without inventing match identities.
create or replace function public.alea_query_list_matches(
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
  if not exists (select 1 from public.profiles where id = v_viewer and status = 'active') then
    raise exception 'active profile required' using errcode = '42501';
  end if;

  return jsonb_build_object(
    'matches',
    coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'match_id', m.id,
          'sporttery_match_number', m.sporttery_match_number,
          'competition', c.name,
          'home_team', ht.name,
          'away_team', at.name,
          'kickoff_at', m.kickoff_at,
          'sales_cutoff_at', m.sales_cutoff_at,
          'state', m.sales_status,
          'sales_status', m.sales_status,
          'fact_state', m.fact_state,
          'source_type', ds.kind,
          'source_authorization_status', ds.authorization_status,
          'data_completeness', case when m.fact_state = 'unavailable' then 0.0 else 1.0 end,
          'missing_fields', case when m.fact_state = 'conflict'
            then jsonb_build_array('conflict') else '[]'::jsonb end,
          'latest_observed_at', sr.observed_at
        )
        order by m.kickoff_at, m.id
      )
      from (
        select *
        from public.matches
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
      join public.competitions c on c.id = m.competition_id
      join public.teams ht on ht.id = m.home_team_id
      join public.teams at on at.id = m.away_team_id
      left join public.source_records sr on sr.id = m.canonical_source_record_id
      left join public.data_sources ds on ds.id = sr.data_source_id
    ), '[]'::jsonb),
    'next_cursor', null,
    'freshness_state', case
      when exists (select 1 from public.matches where fact_state = 'fixture') then 'fixture'
      else 'available'
    end
  );
end;
$$;

revoke all on function public.alea_query_list_matches(text, jsonb) from public;
grant execute on function public.alea_query_list_matches(text, jsonb) to alea_api;
