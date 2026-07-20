from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Iterable, Mapping


class EvidenceState(StrEnum):
    CANDIDATE = "candidate"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    CONFLICT = "conflict"


class EvidenceKind(StrEnum):
    FROZEN_SOURCE = "frozen_source"
    LICENSED_PROVIDER = "licensed_provider"
    ADMIN_IMPORT = "admin_import"
    WEB_SEARCH = "web_search"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    kind: EvidenceKind
    source_record_id: str
    fact_type: str
    subject_id: str
    value: Any
    observed_at: datetime
    captured_url: str | None = None
    title: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (self.evidence_id, self.source_record_id, self.fact_type, self.subject_id)
        ):
            raise ValueError("evidence identifiers must not be empty")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.kind is EvidenceKind.WEB_SEARCH and (not self.captured_url or not self.title):
            raise ValueError("web-search evidence requires a captured URL and title")


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    state: EvidenceState
    evidence_ids: tuple[str, ...]
    value: Any = None
    decided_at: datetime | None = None
    reason: str | None = None


def verify_evidence(
    records: Iterable[EvidenceRecord], *, now: datetime | None = None
) -> EvidenceDecision:
    """Resolve a fact only from frozen/authorized evidence.

    Web Search remains a candidate even when multiple results agree; it can never
    upgrade a claim to verified or feed odds/result settlement.
    """

    items = tuple(records)
    if not items:
        return EvidenceDecision(EvidenceState.UNAVAILABLE, (), decided_at=_utc(now))
    subjects = {(item.fact_type, item.subject_id) for item in items}
    if len(subjects) != 1:
        raise ValueError("all evidence records must address one fact and subject")
    authoritative = tuple(item for item in items if item.kind is not EvidenceKind.WEB_SEARCH)
    if not authoritative:
        return EvidenceDecision(
            EvidenceState.CANDIDATE,
            tuple(item.evidence_id for item in items),
            decided_at=_utc(now),
            reason="web_search_requires_authoritative_verification",
        )
    grouped: dict[str, list[EvidenceRecord]] = {}
    for item in authoritative:
        key = _value_hash(item.value)
        grouped.setdefault(key, []).append(item)
    if len(grouped) > 1:
        return EvidenceDecision(
            EvidenceState.CONFLICT,
            tuple(item.evidence_id for item in authoritative),
            decided_at=_utc(now),
            reason="authorized_sources_disagree",
        )
    accepted = next(iter(grouped.values()))
    return EvidenceDecision(
        EvidenceState.VERIFIED,
        tuple(item.evidence_id for item in accepted),
        value=accepted[0].value,
        decided_at=_utc(now),
    )


def evidence_projection(record: EvidenceRecord) -> Mapping[str, Any]:
    """Expose provenance without leaking adapter internals or credentials."""

    return {
        "evidence_id": record.evidence_id,
        "kind": record.kind.value,
        "source_record_id": record.source_record_id,
        "fact_type": record.fact_type,
        "subject_id": record.subject_id,
        "observed_at": record.observed_at.astimezone(UTC).isoformat(),
        "captured_url": record.captured_url,
        "title": record.title,
        "content_hash": record.content_hash,
    }


def _value_hash(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
