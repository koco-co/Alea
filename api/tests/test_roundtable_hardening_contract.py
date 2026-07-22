from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260721020000_roundtable_execution_hardening.sql"


def test_hardening_migration_enforces_product_quorum() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "exactly three distinct instances" in sql
    assert "at least two provider families" in sql
    assert "v_participant_count <> 3" in sql
    assert "v_provider_count < 2" in sql


def test_hardening_migration_filters_sporttery_offers_before_job_creation() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "alea_is_sporttery_offer_eligible" in sql
    assert "sales_status = 'on_sale'" in sql
    assert "p_at < m.sales_cutoff_at" in sql
    assert "sales_cutoff_at = (" in sql
    assert "sporttery_offer_no_longer_eligible" in sql
    assert "no_eligible_sporttery_matches" in sql
    assert "selection_policy', 'authorized_sporttery_offer_v1'" in sql


def test_lifecycle_initialization_is_idempotent_and_enqueues_provider_work() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "alea_worker_initialize_roundtable" in sql
    assert "on conflict (business_idempotency_key) do nothing" in sql
    assert "roundtable.predict_score" in sql
    assert "get diagnostics v_new_phase_count = row_count" in sql
    assert "get diagnostics v_new_outbox_count = row_count" in sql
    assert "status', 'duplicate'" in sql
