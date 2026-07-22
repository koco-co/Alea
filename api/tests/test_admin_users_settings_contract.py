from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260722020000_admin_users_and_settings.sql"


def test_admin_user_gateway_is_authorized_and_audited() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "create or replace function public.alea_query_list_users" in sql
    assert "create or replace function public.alea_command_disable_user" in sql
    assert "create or replace function public.alea_command_restore_user" in sql
    assert sql.count("administrator_required") >= 5
    assert sql.count("insert into admin_audit_logs") >= 3
    assert "join auth.users u" in sql
    assert "grant select on auth.users" not in sql


def test_settings_are_append_only_and_version_checked() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "create or replace function public.alea_query_read_settings" in sql
    assert "create or replace function public.alea_command_save_settings_version" in sql
    assert "settings_version_conflict" in sql
    assert "insert into system_setting_versions" in sql
    assert "insert into admin_audit_logs" in sql
    assert "revoke all on function public.alea_command_save_settings_version" in sql
