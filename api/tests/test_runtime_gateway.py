from __future__ import annotations

from typing import Any

import pytest

from app.runtime import BusinessGateway, DatasourceFactory, ProviderFactory


class FakeCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.statement = ""
        self.parameters: object = None
        self.description: tuple[()] = ()

    async def __aenter__(self) -> FakeCursor:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, statement: str, parameters: object) -> None:
        self.statement = statement
        self.parameters = parameters

    async def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class FakeDatabase:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.last_cursor = FakeCursor(rows)

    def cursor(self) -> FakeCursor:
        return self.last_cursor


class FakeSupabaseQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.filters: dict[str, object] = {}

    def select(self, value: str) -> FakeSupabaseQuery:
        self.filters["select"] = value
        return self

    def eq(self, key: str, value: object) -> FakeSupabaseQuery:
        self.filters[key] = value
        return self

    def gt(self, key: str, value: object) -> FakeSupabaseQuery:
        self.filters[f"{key}_gt"] = value
        return self

    def order(self, value: str) -> FakeSupabaseQuery:
        self.filters["order"] = value
        return self

    def limit(self, value: int) -> FakeSupabaseQuery:
        self.filters["limit"] = value
        return self

    def execute(self) -> object:
        return type("Response", (), {"data": self.rows})()


class FakeSupabase:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.query = FakeSupabaseQuery(rows)
        self.table_name = ""

    def table(self, value: str) -> FakeSupabaseQuery:
        self.table_name = value
        return self.query


def gateway(database: FakeDatabase) -> BusinessGateway:
    return BusinessGateway(
        database,
        datasource_factory=DatasourceFactory(),
        provider_factory=ProviderFactory(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("visibility", "expected_table", "expected_payload"),
    [
        ("internal", "from roundtable_events", "payload"),
        ("public", "from public_roundtable_events", "public_payload as payload"),
    ],
)
async def test_roundtable_event_reader_uses_persistent_projection(
    visibility: str,
    expected_table: str,
    expected_payload: str,
) -> None:
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "job_id": "00000000-0000-0000-0000-000000000002",
        "event_seq": 4,
        "event_type": "prediction",
        "payload": {"phase": "prediction"},
        "created_at": "2026-07-20T08:00:00+00:00",
    }
    database = FakeDatabase([row])

    result = await gateway(database).read_events(
        row["job_id"],
        after_seq=3,
        limit=201,
        visibility=visibility,
        viewer_id="viewer-1",
    )

    assert result == [row]
    normalized_sql = " ".join(database.last_cursor.statement.split())
    assert expected_table in normalized_sql
    assert expected_payload in normalized_sql
    assert database.last_cursor.parameters == (row["job_id"], 3, 201)


@pytest.mark.asyncio
async def test_business_operation_name_cannot_inject_sql() -> None:
    database = FakeDatabase([])

    with pytest.raises(ValueError, match="invalid_business_operation"):
        await gateway(database).query(
            "events; drop table profiles",
            viewer_id="viewer-1",
            params={},
        )


@pytest.mark.asyncio
async def test_admin_event_reader_uses_privileged_internal_table() -> None:
    rows = [{"job_id": "job-1", "event_seq": 3}]
    supabase = FakeSupabase(rows)
    value = BusinessGateway(
        FakeDatabase([]),
        datasource_factory=DatasourceFactory(),
        provider_factory=ProviderFactory(),
        privileged_supabase=supabase,
    )

    result = await value.read_events(
        "job-1",
        after_seq=2,
        limit=20,
        visibility="internal",
        viewer_id="admin-1",
    )

    assert result == rows
    assert supabase.table_name == "roundtable_events"
    assert supabase.query.filters["job_id"] == "job-1"
    assert supabase.query.filters["event_seq_gt"] == 2
