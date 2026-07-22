-- Public rankings projection.  Ranking facts are intentionally empty until
-- post-match settlement writes immutable, source-backed facts.  This keeps
-- the UI honest while providing a stable API contract for the live projection.

create or replace function public.alea_query_list_rankings(
  p_viewer_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if nullif(btrim(coalesce(p_viewer_id, '')), '') is null then
    raise exception 'ranking query requires an authenticated viewer'
      using errcode = '42501';
  end if;

  -- Do not manufacture rows from provider configuration.  A row becomes
  -- rankable only after the settlement pipeline persists normalized facts.
  -- The empty projection is therefore the correct state for a fresh install.
  return '[]'::jsonb;
end;
$$;

create or replace function public.alea_query_ranking_profile(
  p_viewer_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if nullif(btrim(coalesce(p_viewer_id, '')), '') is null then
    raise exception 'ranking query requires an authenticated viewer'
      using errcode = '42501';
  end if;
  return null;
end;
$$;

revoke all on function public.alea_query_list_rankings(text, jsonb) from public;
revoke all on function public.alea_query_ranking_profile(text, jsonb) from public;
grant execute on function public.alea_query_list_rankings(text, jsonb) to alea_api;
grant execute on function public.alea_query_ranking_profile(text, jsonb) to alea_api;
