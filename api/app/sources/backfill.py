"""Authorization-gated historical Sporttery backfill orchestration.

This module intentionally contains no web scraper.  A production caller must
provide a licensed source adapter and a durable sink.  Raw pages are handed to
the sink before normalization so provenance, hashes and corrections remain
auditable.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

_REQUIRED_CAPABILITIES = frozenset(
    {
        "automatic_access",
        "caching",
        "historical_storage",
        "public_display",
        "redistribution",
    }
)
_ALLOWED_SOURCE_KINDS = frozenset({"sporttery_web", "licensed_supplier"})


class BackfillPolicyError(RuntimeError):
    """The requested source or scope is not permitted for production use."""


class BackfillPayloadError(ValueError):
    """A licensed source returned a malformed or out-of-scope page."""


@dataclass(frozen=True, slots=True)
class BackfillSourcePolicy:
    source_key: str
    kind: str
    enabled: bool
    status: str
    authorization_status: str
    authorization_reference: str | None
    capabilities: frozenset[str] = field(default_factory=frozenset)
    valid_until: datetime | None = None

    def assert_permitted(self, *, now: datetime | None = None) -> None:
        checked_at = _as_utc(now or datetime.now(UTC), field_name="now")
        missing = sorted(_REQUIRED_CAPABILITIES - self.capabilities)
        if self.kind not in _ALLOWED_SOURCE_KINDS:
            raise BackfillPolicyError("unsupported_historical_source_kind")
        if not self.enabled or self.status != "ready":
            raise BackfillPolicyError("historical_source_not_ready")
        if (
            self.authorization_status != "authorized"
            or not (self.authorization_reference or "").strip()
        ):
            raise BackfillPolicyError("historical_source_not_authorized")
        if self.valid_until is not None:
            valid_until = _as_utc(self.valid_until, field_name="valid_until")
            if valid_until <= checked_at:
                raise BackfillPolicyError("historical_source_authorization_expired")
        if missing:
            raise BackfillPolicyError("historical_source_capability_missing:" + ",".join(missing))


@dataclass(frozen=True, slots=True)
class BackfillScope:
    start_date: date
    end_date: date
    competition_keys: tuple[str, ...] = ()
    page_size: int = 200

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if not 1 <= self.page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if len(self.competition_keys) != len(set(self.competition_keys)):
            raise ValueError("competition_keys must be distinct")


@dataclass(frozen=True, slots=True)
class BackfillPage:
    records: tuple[Mapping[str, Any], ...]
    next_cursor: Mapping[str, Any] | None


class LicensedBackfillAdapter(Protocol):
    policy: BackfillSourcePolicy

    def pages(
        self, scope: BackfillScope, *, cursor: Mapping[str, Any] | None = None
    ) -> AsyncIterator[BackfillPage]: ...


class BackfillSink(Protocol):
    async def start_run(self, *, policy: BackfillSourcePolicy, scope: BackfillScope) -> str: ...

    async def ingest_raw_page(
        self,
        run_id: str,
        *,
        records: Sequence[Mapping[str, Any]],
        request_cursor: Mapping[str, Any] | None,
        next_cursor: Mapping[str, Any] | None,
    ) -> tuple[int, int]:
        """Return ``(accepted, conflicted)`` after immutable raw persistence."""
        ...

    async def complete_run(
        self,
        run_id: str,
        *,
        records_seen: int,
        records_accepted: int,
        records_conflicted: int,
        final_cursor: Mapping[str, Any] | None,
    ) -> None: ...

    async def fail_run(self, run_id: str, *, error_code: str) -> None: ...


@dataclass(frozen=True, slots=True)
class BackfillSummary:
    run_id: str
    records_seen: int
    records_accepted: int
    records_conflicted: int
    final_cursor: Mapping[str, Any] | None


async def run_backfill(
    adapter: LicensedBackfillAdapter,
    sink: BackfillSink,
    scope: BackfillScope,
    *,
    initial_cursor: Mapping[str, Any] | None = None,
    max_pages: int = 100_000,
    now: datetime | None = None,
) -> BackfillSummary:
    """Run a resumable licensed backfill and persist every raw page first."""

    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    adapter.policy.assert_permitted(now=now)

    run_id = await sink.start_run(policy=adapter.policy, scope=scope)
    seen = accepted = conflicted = page_count = 0
    cursor: Mapping[str, Any] | None = initial_cursor
    cursor_fingerprints: set[str] = set()
    if initial_cursor is not None:
        cursor_fingerprints.add(_cursor_fingerprint(initial_cursor))

    try:
        async for page in adapter.pages(scope, cursor=initial_cursor):
            page_count += 1
            if page_count > max_pages:
                raise BackfillPayloadError("backfill_page_limit_exceeded")
            if not page.records:
                raise BackfillPayloadError("empty_backfill_page")

            _validate_records(page.records, scope)
            page_accepted, page_conflicted = await sink.ingest_raw_page(
                run_id,
                records=page.records,
                request_cursor=cursor,
                next_cursor=page.next_cursor,
            )
            if page_accepted < 0 or page_conflicted < 0:
                raise BackfillPayloadError("invalid_sink_counts")
            if page_accepted + page_conflicted > len(page.records):
                raise BackfillPayloadError("sink_counts_exceed_page_size")

            seen += len(page.records)
            accepted += page_accepted
            conflicted += page_conflicted
            cursor = page.next_cursor
            if cursor is not None:
                fingerprint = _cursor_fingerprint(cursor)
                if fingerprint in cursor_fingerprints:
                    raise BackfillPayloadError("backfill_cursor_cycle")
                cursor_fingerprints.add(fingerprint)

        await sink.complete_run(
            run_id,
            records_seen=seen,
            records_accepted=accepted,
            records_conflicted=conflicted,
            final_cursor=cursor,
        )
    except Exception as exc:
        try:
            await sink.fail_run(run_id, error_code=type(exc).__name__)
        except Exception as failure_recording_error:
            exc.add_note(
                "backfill sink failed to persist failure state: "
                f"{type(failure_recording_error).__name__}"
            )
        raise

    return BackfillSummary(
        run_id=run_id,
        records_seen=seen,
        records_accepted=accepted,
        records_conflicted=conflicted,
        final_cursor=cursor,
    )


def _validate_records(records: Sequence[Mapping[str, Any]], scope: BackfillScope) -> None:
    for index, record in enumerate(records):
        key = str(record.get("source_record_key", "")).strip()
        business_date_raw = record.get("business_date")
        raw_content = record.get("raw_content")
        if not key:
            raise BackfillPayloadError(f"record_{index}_missing_source_record_key")
        if not isinstance(raw_content, Mapping):
            raise BackfillPayloadError(f"record_{index}_missing_raw_content")
        try:
            business_date = date.fromisoformat(str(business_date_raw))
        except ValueError as exc:
            raise BackfillPayloadError(f"record_{index}_invalid_business_date") from exc
        if not scope.start_date <= business_date <= scope.end_date:
            raise BackfillPayloadError(f"record_{index}_outside_backfill_scope")
        if scope.competition_keys:
            competition_key = str(record.get("competition_key", "")).strip()
            if competition_key not in scope.competition_keys:
                raise BackfillPayloadError(f"record_{index}_outside_competition_scope")


def _cursor_fingerprint(cursor: Mapping[str, Any]) -> str:
    return json.dumps(dict(cursor), sort_keys=True, separators=(",", ":"), default=str)


def _as_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise BackfillPolicyError(f"{field_name}_must_be_timezone_aware")
    return value.astimezone(UTC)
