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


def test_local_fixture_roundtable_mode_is_explicit_and_non_production() -> None:
    migration = ROOT / "supabase/migrations/20260723100000_local_fixture_roundtable_mode.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "alea_is_local_fixture_match" in sql
    assert "source.kind = 'fixture'" in sql
    assert "non_production" in sql
    assert "fixture_mode" in sql
    assert "local_fixture_v1" in sql


def test_internal_event_read_is_granted_only_to_backend_service_role() -> None:
    migration = ROOT / "supabase/migrations/20260723110000_service_role_event_read_grant.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "grant select on public.roundtable_events to service_role" in sql
    assert "authenticated" not in sql
    assert "anon" not in sql


def test_roundtable_event_sequence_allocation_is_advisory_locked() -> None:
    migration = ROOT / "supabase/migrations/20260723120000_serialize_roundtable_event_sequences.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "pg_advisory_xact_lock" in sql
    assert "hashtextextended(new.job_id::text, 0)" in sql
    assert "for update" not in sql.casefold()


def test_match_projection_exposes_offer_identity_and_provenance() -> None:
    migration = ROOT / "supabase/migrations/20260723130000_match_projection_metadata.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "sporttery_match_number" in sql
    assert "source_authorization_status" in sql
    assert "left join public.data_sources" in sql


def test_terminal_roundtable_retry_keeps_successful_jobs_idempotent() -> None:
    migration = ROOT / "supabase/migrations/20260723141220_allow_terminal_roundtable_retry.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "alea_command_start_roundtable_unhardened_20260721" in sql
    assert "existing_job.state in ('failed', 'no_quorum', 'terminated')" in sql
    assert "retry_match.state = 'no_quorum'" in sql
    assert "p_request_id" in sql
    assert "idempotent', true" in sql
