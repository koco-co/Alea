from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class FactClaimState(StrEnum):
    EXTRACTED = "extracted"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"


TERMINAL_FACT_STATES = frozenset(
    {FactClaimState.VERIFIED, FactClaimState.UNSUPPORTED, FactClaimState.UNAVAILABLE}
)
FACT_TRANSITIONS = {
    FactClaimState.EXTRACTED: frozenset({FactClaimState.VERIFYING}),
    FactClaimState.VERIFYING: TERMINAL_FACT_STATES,
}


class FactVerificationError(ValueError):
    """Raised when a fact claim violates the verification state machine."""


@dataclass(frozen=True, slots=True)
class FactClaim:
    claim_id: str
    text: str
    normalized_claim_hash: str
    source_record_ids: tuple[str, ...]
    state: FactClaimState = FactClaimState.EXTRACTED
    evidence_snapshot: Mapping[str, Any] | None = None
    verified_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class VerificationDecision:
    state: FactClaimState
    evidence_snapshot: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.state not in TERMINAL_FACT_STATES:
            raise FactVerificationError("verification decision must be terminal")
        if self.state == FactClaimState.VERIFIED and self.evidence_snapshot is None:
            raise FactVerificationError("verified claims require an evidence snapshot")


def extract_fact_claim(
    *, claim_id: str, text: str, source_record_ids: Iterable[str] = ()
) -> FactClaim:
    normalized = _normalize_claim(text)
    if not claim_id.strip():
        raise FactVerificationError("claim_id must not be empty")
    if not normalized:
        raise FactVerificationError("claim text must not be empty")
    sources = tuple(dict.fromkeys(item.strip() for item in source_record_ids if item.strip()))
    return FactClaim(
        claim_id=claim_id,
        text=text.strip(),
        normalized_claim_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        source_record_ids=sources,
    )


def transition_fact_claim(
    claim: FactClaim,
    target: FactClaimState | str,
    *,
    evidence_snapshot: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> FactClaim:
    target_state = FactClaimState(target)
    if target_state == claim.state:
        return claim
    if target_state not in FACT_TRANSITIONS.get(claim.state, frozenset()):
        raise FactVerificationError(
            f"illegal fact claim transition: {claim.state.value} -> {target_state.value}"
        )
    if target_state == FactClaimState.VERIFIED and evidence_snapshot is None:
        raise FactVerificationError("verified claims require an evidence snapshot")
    frozen_evidence = (
        MappingProxyType(_deep_copy(evidence_snapshot)) if evidence_snapshot is not None else None
    )
    return replace(
        claim,
        state=target_state,
        evidence_snapshot=frozen_evidence,
        verified_at=_utc(now) if target_state in TERMINAL_FACT_STATES else None,
    )


def begin_verification(claim: FactClaim) -> FactClaim:
    return transition_fact_claim(claim, FactClaimState.VERIFYING)


def finish_verification(
    claim: FactClaim, decision: VerificationDecision, *, now: datetime | None = None
) -> FactClaim:
    if claim.state != FactClaimState.VERIFYING:
        raise FactVerificationError("claim must be verifying before it can finish")
    return transition_fact_claim(
        claim,
        decision.state,
        evidence_snapshot=decision.evidence_snapshot,
        now=now,
    )


def build_safe_peer_context(
    messages: Sequence[Mapping[str, Any]],
    claims: Iterable[FactClaim],
) -> tuple[Mapping[str, Any], ...]:
    """Return peer messages with only verified claims propagated.

    Non-verified claim IDs remain visible only in ``fact_claim_audit`` so the
    worker can persist their state without allowing the assertions into a later
    model's evidence context.
    """

    claims_by_id = {claim.claim_id: claim for claim in claims}
    safe: list[Mapping[str, Any]] = []
    for message in messages:
        referenced = _string_ids(message.get("fact_claim_ids", ()))
        verified = [
            _public_claim(claims_by_id[claim_id])
            for claim_id in referenced
            if claim_id in claims_by_id and claims_by_id[claim_id].state == FactClaimState.VERIFIED
        ]
        audit = [
            {"claim_id": claim_id, "status": claims_by_id[claim_id].state.value}
            for claim_id in referenced
            if claim_id in claims_by_id and claims_by_id[claim_id].state != FactClaimState.VERIFIED
        ]
        public_message = {
            key: _deep_copy(value)
            for key, value in message.items()
            if key not in {"fact_claims", "fact_claim_ids", "raw_provider_payload"}
        }
        public_message["verified_fact_claims"] = verified
        public_message["fact_claim_audit"] = audit
        safe.append(MappingProxyType(public_message))
    return tuple(safe)


def verified_claim_ids(claims: Iterable[FactClaim]) -> frozenset[str]:
    return frozenset(claim.claim_id for claim in claims if claim.state == FactClaimState.VERIFIED)


def _public_claim(claim: FactClaim) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "text": claim.text,
        "source_record_ids": list(claim.source_record_ids),
        "evidence_snapshot": _deep_copy(claim.evidence_snapshot),
    }


def _normalize_claim(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(
        character for character in normalized if unicodedata.category(character) != "Cc"
    )
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _string_ids(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _deep_copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _deep_copy(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_deep_copy(child) for child in value]
    return value


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise FactVerificationError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
