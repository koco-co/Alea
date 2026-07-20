from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImportKind(StrEnum):
    MATCH = "match"
    OFFER = "offer"
    RESULT = "result"
    TEAM_INTEL = "team_intel"


class AdminImportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ImportKind
    upstream_record_id: str = Field(min_length=1, max_length=200)
    canonical_match_id: str | None = None
    canonical_team_id: str | None = None
    observed_at: datetime
    valid_from: datetime | None = None
    expires_at: datetime | None = None
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_target(self) -> AdminImportRow:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.kind in {ImportKind.MATCH, ImportKind.OFFER, ImportKind.RESULT}:
            if not self.canonical_match_id:
                raise ValueError("match, offer, and result rows require canonical_match_id")
        elif not self.canonical_team_id:
            raise ValueError("team_intel rows require canonical_team_id")
        return self


class AdminImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_label: str = Field(min_length=1, max_length=100)
    license_reference: str = Field(min_length=1, max_length=500)
    request_scope: str = Field(min_length=1, max_length=500)
    rows: list[AdminImportRow] = Field(min_length=1, max_length=10_000)


class PreparedImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_record_id: str
    content_hash: str
    parser_version: str
    row: AdminImportRow


class AdminImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sync_run_id: str
    accepted: int = Field(ge=0)
    duplicate: int = Field(ge=0)
    conflicts: int = Field(ge=0)


class CanonicalEntityRegistry(Protocol):
    async def contains_match(self, match_id: str) -> bool: ...

    async def contains_team(self, team_id: str) -> bool: ...


class AdminImportGateway(Protocol):
    async def commit_import(
        self,
        *,
        actor_id: str,
        request_id: str,
        source_label: str,
        license_reference: str,
        request_scope: str,
        records: Sequence[PreparedImportRecord],
        imported_at: datetime,
    ) -> Mapping[str, Any] | AdminImportResult:
        """Atomically append sync_run, source_records, domain facts, and audit log."""
        ...


async def prepare_admin_import(
    request: AdminImportRequest,
    *,
    registry: CanonicalEntityRegistry,
    parser_version: str = "admin-import-v1",
) -> tuple[PreparedImportRecord, ...]:
    """Validate canonical IDs explicitly; name-based fuzzy mapping is forbidden."""

    records: list[PreparedImportRecord] = []
    seen: set[str] = set()
    for row in request.rows:
        if row.canonical_match_id and not await registry.contains_match(row.canonical_match_id):
            raise ValueError(f"unknown canonical_match_id: {row.canonical_match_id}")
        if row.canonical_team_id and not await registry.contains_team(row.canonical_team_id):
            raise ValueError(f"unknown canonical_team_id: {row.canonical_team_id}")
        normalized = row.model_dump(mode="json")
        encoded = json.dumps(
            normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        content_hash = hashlib.sha256(encoded).hexdigest()
        source_record_id = str(
            uuid5(
                NAMESPACE_URL,
                f"alea:admin-import:{request.source_label}:{row.upstream_record_id}:{content_hash}",
            )
        )
        if source_record_id in seen:
            continue
        seen.add(source_record_id)
        records.append(
            PreparedImportRecord(
                source_record_id=source_record_id,
                content_hash=content_hash,
                parser_version=parser_version,
                row=row,
            )
        )
    return tuple(records)


async def import_admin_data(
    request: AdminImportRequest,
    *,
    actor_id: str,
    request_id: str,
    registry: CanonicalEntityRegistry,
    gateway: AdminImportGateway,
    now: datetime | None = None,
) -> AdminImportResult:
    if not actor_id.strip() or not request_id.strip():
        raise ValueError("actor_id and request_id must not be empty")
    records = await prepare_admin_import(request, registry=registry)
    result = await gateway.commit_import(
        actor_id=actor_id,
        request_id=request_id,
        source_label=request.source_label,
        license_reference=request.license_reference,
        request_scope=request.request_scope,
        records=records,
        imported_at=_utc(now),
    )
    return (
        result
        if isinstance(result, AdminImportResult)
        else AdminImportResult.model_validate(result)
    )


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
