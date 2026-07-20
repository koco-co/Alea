from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import Connection, sql
from psycopg.errors import InsufficientPrivilege

from pathlib import Path

MIGRATION = Path(__file__).parents[2] / "supabase" / "migrations" / "00001_gate0_minimal.sql"


def test_gate0_migration_declares_all_runtime_roles_and_denies_public_by_default() -> None:
    sql_text = MIGRATION.read_text(encoding="utf-8")
    for role in ("alea_api", "alea_worker", "alea_dispatcher", "alea_scheduler"):
        assert f"create role {role} nologin nosuperuser" in sql_text
    assert "revoke all on all tables in schema public from public, anon, authenticated" in sql_text
    assert "grant execute on function notarize_roundtable(uuid) to alea_worker" in sql_text
    assert "grant update (status, lease_owner, lease_until, attempt, broker_message_id" in sql_text
    assert "grant execute on function claim_schedule_run" in sql_text


@pytest.fixture()
def database() -> Iterator[Connection[tuple[object, ...]]]:
    database_url = os.getenv("GATE0_DATABASE_URL")
    if not database_url:
        pytest.skip("GATE0_DATABASE_URL is required for real G1 verification")
    with psycopg.connect(database_url) as connection:
        with connection.transaction(force_rollback=True):
            yield connection


def set_role(connection: Connection[tuple[object, ...]], role: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))


@pytest.mark.parametrize("role", ["anon", "authenticated", "alea_api", "alea_dispatcher", "alea_scheduler"])
def test_non_worker_cannot_insert_notarized_prediction(
    database: Connection[tuple[object, ...]], role: str
) -> None:
    set_role(database, role)
    with database.cursor() as cursor, pytest.raises(InsufficientPrivilege):
        cursor.execute(
            "insert into notarized_predictions (job_id, match_run_id, payload, payload_hash, sales_cutoff_at) values (%s, %s, '{}', 'x', now())",
            (uuid.uuid4(), uuid.uuid4()),
        )


@pytest.mark.parametrize("role", ["anon", "authenticated", "alea_api", "alea_worker", "alea_scheduler"])
def test_non_dispatcher_cannot_update_outbox_delivery_state(
    database: Connection[tuple[object, ...]], role: str
) -> None:
    set_role(database, role)
    with database.cursor() as cursor, pytest.raises(InsufficientPrivilege):
        cursor.execute("update outbox_events set status = 'published'")


def test_anon_cannot_read_registered_user_projection(database: Connection[tuple[object, ...]]) -> None:
    set_role(database, "anon")
    with database.cursor() as cursor, pytest.raises(InsufficientPrivilege):
        cursor.execute("select * from public_notarized_predictions")


def test_authenticated_can_read_only_public_projection(database: Connection[tuple[object, ...]]) -> None:
    set_role(database, "authenticated")
    with database.cursor() as cursor:
        cursor.execute("select * from public_notarized_predictions")
        cursor.fetchall()
    with database.cursor() as cursor, pytest.raises(InsufficientPrivilege):
        cursor.execute("select * from provider_secrets")
