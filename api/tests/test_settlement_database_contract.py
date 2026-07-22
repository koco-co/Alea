from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20260722040000_settlement_and_rankings.sql"
)


def test_settlement_migration_persists_immutable_facts_and_ledger() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    for table in (
        "settlement_runs",
        "simulated_accounts",
        "settlement_positions",
        "simulated_account_entries",
        "ranking_facts",
    ):
        assert f"create table public.{table}" in sql
    assert "unique (notarized_prediction_id, result_version_id)" in sql
    assert "unique (notarized_prediction_id, result_version_id, ai_instance_id)" in sql
    assert "create or replace function public.settle_notarized_prediction" in sql
    assert "set search_path = public, pg_temp" in sql
    assert "settlement_runs_immutable" in sql
    assert "ranking_facts_immutable" in sql


def test_settlement_migration_enforces_authorized_result_and_worker_boundary() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "alea_is_authorized_sporttery_source" in sql
    assert "confirmed_authorized_result_required" in sql
    assert "session_user <> 'alea_worker'" in sql
    assert (
        "grant execute on function public.settle_notarized_prediction(uuid, uuid) to alea_worker"
        in sql
    )
    assert (
        "revoke all on function public.settle_notarized_prediction(uuid, uuid) from public, anon, authenticated"
        in sql
    )


def test_settlement_migration_queues_idempotent_downstream_work() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "settlement.run" in sql
    assert "ranking.recompute" in sql
    assert "prediction.review" in sql
    assert "on conflict (business_idempotency_key) do nothing" in sql
    assert "queue_settlement_after_result_trigger" in sql
    assert "queue_settlement_after_notarization_trigger" in sql
    assert "roundtable_match_runs mr on mr.id = new.match_run_id" in sql
