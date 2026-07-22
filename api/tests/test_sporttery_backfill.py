from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from app.sources.backfill import (
    BackfillPage,
    BackfillPolicyError,
    BackfillScope,
    BackfillSourcePolicy,
    run_backfill,
)


CAPABILITIES = frozenset(
    {
        "automatic_access",
        "caching",
        "historical_storage",
        "public_display",
        "redistribution",
    }
)

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def authorized_policy() -> BackfillSourcePolicy:
    return BackfillSourcePolicy(
        source_key="licensed-supplier",
        kind="licensed_supplier",
        enabled=True,
        status="ready",
        authorization_status="authorized",
        authorization_reference="contract-2026-001",
        capabilities=CAPABILITIES,
        valid_until=NOW + timedelta(days=30),
    )


class Adapter:
    def __init__(self, policy: BackfillSourcePolicy) -> None:
        self.policy = policy

    async def pages(
        self, scope: BackfillScope, *, cursor: Mapping[str, Any] | None = None
    ) -> AsyncIterator[BackfillPage]:
        del scope, cursor
        yield BackfillPage(
            records=(
                {
                    "source_record_key": "2026-001",
                    "business_date": "2026-07-20",
                    "raw_content": {"match": "001"},
                },
            ),
            next_cursor={"page": 2},
        )


class Sink:
    def __init__(self) -> None:
        self.completed = False
        self.failed = False

    async def start_run(self, **_: Any) -> str:
        return "run-1"

    async def ingest_raw_page(
        self,
        run_id: str,
        *,
        records: Sequence[Mapping[str, Any]],
        request_cursor: Mapping[str, Any] | None,
        next_cursor: Mapping[str, Any] | None,
    ) -> tuple[int, int]:
        assert run_id == "run-1"
        assert request_cursor is None
        assert next_cursor == {"page": 2}
        return len(records), 0

    async def complete_run(self, run_id: str, **_: Any) -> None:
        assert run_id == "run-1"
        self.completed = True

    async def fail_run(self, run_id: str, *, error_code: str) -> None:
        del run_id, error_code
        self.failed = True


@pytest.mark.asyncio
async def test_authorized_backfill_persists_raw_pages() -> None:
    sink = Sink()
    summary = await run_backfill(
        Adapter(authorized_policy()),
        sink,
        BackfillScope(date(2026, 7, 1), date(2026, 7, 31)),
        now=NOW,
    )

    assert summary.records_seen == 1
    assert summary.records_accepted == 1
    assert summary.final_cursor == {"page": 2}
    assert sink.completed is True
    assert sink.failed is False


@pytest.mark.asyncio
async def test_unlicensed_backfill_is_rejected_before_run_creation() -> None:
    policy = BackfillSourcePolicy(
        source_key="unlicensed",
        kind="sporttery_web",
        enabled=True,
        status="ready",
        authorization_status="unverified",
        authorization_reference=None,
        capabilities=CAPABILITIES,
    )

    with pytest.raises(BackfillPolicyError, match="not_authorized"):
        await run_backfill(
            Adapter(policy),
            Sink(),
            BackfillScope(date(2026, 7, 1), date(2026, 7, 31)),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_expired_authorization_is_rejected() -> None:
    policy = BackfillSourcePolicy(
        source_key="expired",
        kind="licensed_supplier",
        enabled=True,
        status="ready",
        authorization_status="authorized",
        authorization_reference="contract-expired",
        capabilities=CAPABILITIES,
        valid_until=NOW - timedelta(seconds=1),
    )

    with pytest.raises(BackfillPolicyError, match="authorization_expired"):
        await run_backfill(
            Adapter(policy),
            Sink(),
            BackfillScope(date(2026, 7, 1), date(2026, 7, 31)),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_naive_authorization_timestamp_fails_closed() -> None:
    policy = BackfillSourcePolicy(
        source_key="naive-timestamp",
        kind="licensed_supplier",
        enabled=True,
        status="ready",
        authorization_status="authorized",
        authorization_reference="contract-naive",
        capabilities=CAPABILITIES,
        valid_until=datetime(2026, 8, 1),
    )

    with pytest.raises(BackfillPolicyError, match="timezone_aware"):
        await run_backfill(
            Adapter(policy),
            Sink(),
            BackfillScope(date(2026, 7, 1), date(2026, 7, 31)),
            now=NOW,
        )
