from pathlib import Path


MIGRATIONS = Path(__file__).parents[2] / "supabase" / "migrations"


def test_roundtable_start_and_worker_projection_contract_is_forward_migrated() -> None:
    source = (MIGRATIONS / "20260721004857_roundtable_start_and_projection.sql").read_text()
    fix = (MIGRATIONS / "20260721013700_fix_worker_event_role_guard.sql").read_text()

    assert "alea_command_start_roundtable" in source
    assert "roundtable_participants" in source
    assert "roundtable_match_runs" in source
    assert "roundtable_events" in source
    assert "outbox_events" in source
    assert "execution_mode" in source
    assert "connection_version" in source
    assert "worker role required" in fix
    assert "session_user <> 'alea_worker'" in fix
