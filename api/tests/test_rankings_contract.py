from __future__ import annotations

from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2] / "supabase" / "migrations" / "20260722030000_rankings_projection.sql"
)


def test_rankings_projection_is_authenticated_and_empty_until_settlement() -> None:
    sql_text = MIGRATION.read_text(encoding="utf-8")

    assert "create or replace function public.alea_query_list_rankings" in sql_text
    assert "create or replace function public.alea_query_ranking_profile" in sql_text
    assert "return '[]'::jsonb" in sql_text
    assert "return null" in sql_text
    assert (
        "revoke all on function public.alea_query_list_rankings(text, jsonb) from public"
        in sql_text
    )
    assert (
        "grant execute on function public.alea_query_list_rankings(text, jsonb) to alea_api"
        in sql_text
    )
