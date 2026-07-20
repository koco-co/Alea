from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Sequence


ROLE_LABEL = re.compile(
    r"(?im)^\s*(system|assistant|developer|tool|user|系统|开发者|助手|工具|用户)\s*[:：]"
)
INJECTION_TEXT = re.compile(
    r"(?i)(ignore\s+(all\s+|the\s+)?(previous|prior)|忽略\s*(以上|前文|之前))"
)


class ContextPhase(StrEnum):
    SELECTION = "selection"
    MATCH = "match"
    BET = "bet"
    POSTMATCH_REVIEW = "postmatch_review"
    METHODOLOGY_REVIEW = "methodology_review"


class SnapshotFrozenError(RuntimeError):
    """Raised when a model-started phase snapshot is refreshed or replaced."""


@dataclass(frozen=True, slots=True)
class FrozenContextSnapshot:
    snapshot_id: str
    phase: ContextPhase
    payload: Mapping[str, Any]
    content_hash: str
    frozen_at: datetime
    suspicious_input: bool = False
    model_call_started_at: datetime | None = None

    @property
    def locked(self) -> bool:
        return self.model_call_started_at is not None


@dataclass(frozen=True, slots=True)
class PromptLayer:
    layer: str
    name: str
    trusted: bool
    content: Any
    version: str | int | None = None
    suspicious_input: bool = False


@dataclass(frozen=True, slots=True)
class PromptEnvelope:
    instance_id: str
    phase: ContextPhase
    input_snapshot_id: str
    trusted_instructions: tuple[PromptLayer, ...]
    untrusted_data: tuple[PromptLayer, ...]
    tools: tuple[Mapping[str, Any], ...]
    output_schema: Mapping[str, Any]
    version_refs: Mapping[str, str | int | None]

    @property
    def layers(self) -> tuple[PromptLayer, ...]:
        return self.trusted_instructions + self.untrusted_data


def freeze_context_snapshot(
    *,
    snapshot_id: str,
    phase: ContextPhase | str,
    payload: Mapping[str, Any],
    now: datetime | None = None,
) -> FrozenContextSnapshot:
    """Deep-copy and freeze one stage's typed data before its first model call."""

    if not snapshot_id.strip():
        raise ValueError("snapshot_id must not be empty")
    sanitized, suspicious = sanitize_untrusted_data(payload)
    if not isinstance(sanitized, dict):
        raise TypeError("snapshot payload must be an object")
    return _new_snapshot(
        snapshot_id,
        ContextPhase(phase),
        sanitized,
        _utc(now),
        suspicious_input=suspicious,
    )


def refresh_context_snapshot(
    snapshot: FrozenContextSnapshot,
    payload: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> FrozenContextSnapshot:
    """Replace pre-call data; replacement is forbidden after the first model starts."""

    if snapshot.locked:
        raise SnapshotFrozenError(
            f"snapshot {snapshot.snapshot_id} is locked by its first model call"
        )
    sanitized, suspicious = sanitize_untrusted_data(payload)
    if not isinstance(sanitized, dict):
        raise TypeError("snapshot payload must be an object")
    return _new_snapshot(
        snapshot.snapshot_id,
        snapshot.phase,
        sanitized,
        _utc(now),
        suspicious_input=suspicious,
    )


def mark_model_call_started(
    snapshot: FrozenContextSnapshot, *, now: datetime | None = None
) -> FrozenContextSnapshot:
    """Lock the stage snapshot idempotently at the first Provider invocation."""

    if snapshot.model_call_started_at is not None:
        return snapshot
    return replace(snapshot, model_call_started_at=_utc(now))


def build_selection_context(snapshot: FrozenContextSnapshot) -> Mapping[str, Any]:
    _require_phase(snapshot, ContextPhase.SELECTION)
    allowed = {
        "matches",
        "match_id",
        "competition",
        "kickoff_at",
        "cutoff_at",
        "data_completeness",
        "odds_summary",
        "missing_fields",
        "source_record_ids",
    }
    return _project(snapshot.payload, allowed)


def freeze_match_context(
    *,
    snapshot_id: str,
    job_id: str,
    match_id: str,
    match_data: Mapping[str, Any],
    now: datetime | None = None,
) -> FrozenContextSnapshot:
    """Freeze the complete pre-match L4 input shared by every participating instance."""

    required = {"teams", "odds", "form", "head_to_head", "standings", "injuries", "lineups"}
    missing = required.difference(match_data)
    if missing:
        raise ValueError(f"match context missing fields: {', '.join(sorted(missing))}")
    return freeze_context_snapshot(
        snapshot_id=snapshot_id,
        phase=ContextPhase.MATCH,
        payload={"job_id": job_id, "match_id": match_id, **dict(match_data)},
        now=now,
    )


def build_bet_context(snapshot: FrozenContextSnapshot) -> Mapping[str, Any]:
    _require_phase(snapshot, ContextPhase.BET)
    allowed = {
        "eligible_match_run_ids",
        "final_score_votes",
        "sellable_options",
        "offer_snapshot_id",
        "risk_limits",
        "risk_rule_version",
        "sporttery_rules_version",
    }
    return _project(snapshot.payload, allowed)


def build_instance_context(
    *,
    instance_id: str,
    snapshot: FrozenContextSnapshot,
    identity_prompt: str,
    core_methodology: str,
    phase_instruction: str,
    output_schema: Mapping[str, Any],
    tools: Sequence[Mapping[str, Any]],
    history_context: Mapping[str, Any] | str,
    lesson_context: Sequence[Mapping[str, Any] | str],
    peer_context: Sequence[Mapping[str, Any]] = (),
    codename_map: Mapping[str, str] | None = None,
    versions: Mapping[str, str | int | None] | None = None,
) -> PromptEnvelope:
    """Assemble L1-L7 while preserving instruction/data role boundaries.

    L1, L2, L6, the output schema, and tool contract remain trusted platform
    material. L3-L5 are recursively normalized and serialized only as data.
    """

    if not instance_id.strip():
        raise ValueError("instance_id must not be empty")
    version_refs = dict(versions or {})
    required_versions = {
        "identity_prompt_version",
        "core_methodology_version",
        "phase_prompt_version",
        "output_schema_version",
        "tool_contract_version",
    }
    missing = required_versions.difference(version_refs)
    if missing:
        raise ValueError(f"versions missing required keys: {', '.join(sorted(missing))}")

    other_codenames = {
        other_id: codename
        for other_id, codename in (codename_map or {}).items()
        if other_id != instance_id
    }
    anonymous_peers = _anonymize_peer_context(peer_context, codename_map or {}, instance_id)
    l3, l3_suspicious = sanitize_untrusted_data(
        {"other_participant_codenames": other_codenames, "peer_messages": anonymous_peers}
    )
    l4, l4_suspicious = sanitize_untrusted_data(_thaw(snapshot.payload))
    l5, l5_suspicious = sanitize_untrusted_data(
        {"history": history_context, "lessons": lesson_context}
    )
    sanitized_tools = tuple(_trusted_mapping(tool, "tool") for tool in tools)
    schema = _trusted_mapping(output_schema, "output_schema")

    trusted = (
        PromptLayer(
            "L1",
            "identity",
            True,
            identity_prompt,
            version_refs["identity_prompt_version"],
        ),
        PromptLayer(
            "L2",
            "core_methodology",
            True,
            core_methodology,
            version_refs["core_methodology_version"],
        ),
        PromptLayer(
            "L6",
            "phase_instruction",
            True,
            phase_instruction,
            version_refs["phase_prompt_version"],
        ),
    )
    untrusted = (
        PromptLayer("L3", "anonymous_peers", False, l3, suspicious_input=l3_suspicious),
        PromptLayer(
            "L4",
            f"{snapshot.phase.value}_context",
            False,
            l4,
            suspicious_input=l4_suspicious or snapshot.suspicious_input,
        ),
        PromptLayer("L5", "history_and_lessons", False, l5, suspicious_input=l5_suspicious),
    )
    return PromptEnvelope(
        instance_id=instance_id,
        phase=snapshot.phase,
        input_snapshot_id=snapshot.snapshot_id,
        trusted_instructions=trusted,
        untrusted_data=untrusted,
        tools=sanitized_tools,
        output_schema=schema,
        version_refs=MappingProxyType(version_refs),
    )


def sanitize_untrusted_data(
    value: Any,
    *,
    max_string_length: int = 20_000,
    max_array_items: int = 500,
    max_depth: int = 12,
) -> tuple[Any, bool]:
    """Normalize untrusted values and remove controls and forged role labels."""

    suspicious = False

    def clean(item: Any, depth: int) -> Any:
        nonlocal suspicious
        if depth > max_depth:
            raise ValueError("untrusted data exceeds maximum nesting depth")
        if item is None or isinstance(item, (bool, int, float)):
            return item
        if isinstance(item, str):
            normalized = unicodedata.normalize("NFKC", item)
            normalized = "".join(
                character
                for character in normalized
                if character in "\n\t" or unicodedata.category(character) != "Cc"
            )
            if ROLE_LABEL.search(normalized) or INJECTION_TEXT.search(normalized):
                suspicious = True
            normalized = ROLE_LABEL.sub("[role-label-removed] ", normalized)
            return normalized[:max_string_length]
        if isinstance(item, Mapping):
            if len(item) > max_array_items:
                raise ValueError("untrusted object exceeds maximum field count")
            return {str(key): clean(child, depth + 1) for key, child in item.items()}
        if isinstance(item, Sequence) and not isinstance(item, (bytes, bytearray)):
            if len(item) > max_array_items:
                raise ValueError("untrusted array exceeds maximum item count")
            return [clean(child, depth + 1) for child in item]
        suspicious = True
        return str(item)[:max_string_length]

    return clean(value, 0), suspicious


def _new_snapshot(
    snapshot_id: str,
    phase: ContextPhase,
    payload: Mapping[str, Any],
    timestamp: datetime,
    *,
    suspicious_input: bool,
) -> FrozenContextSnapshot:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return FrozenContextSnapshot(
        snapshot_id=snapshot_id,
        phase=phase,
        payload=_freeze(payload),
        content_hash=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        frozen_at=timestamp,
        suspicious_input=suspicious_input,
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def _project(payload: Mapping[str, Any], allowed: set[str]) -> Mapping[str, Any]:
    projected = {key: _thaw(value) for key, value in payload.items() if key in allowed}
    return MappingProxyType(projected)


def _require_phase(snapshot: FrozenContextSnapshot, expected: ContextPhase) -> None:
    if snapshot.phase is not expected:
        raise ValueError(f"expected {expected.value} snapshot, got {snapshot.phase.value}")


def _trusted_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be JSON serializable") from exc
    loaded = json.loads(serialized)
    if not isinstance(loaded, dict):
        raise TypeError(f"{name} must be an object")
    return MappingProxyType(loaded)


def _anonymize_peer_context(
    peer_context: Sequence[Mapping[str, Any]],
    codename_map: Mapping[str, str],
    own_instance_id: str,
) -> list[dict[str, Any]]:
    identity_fields = {
        "instance_id",
        "vendor",
        "vendor_family",
        "provider",
        "model",
        "model_id",
        "nickname",
    }
    result: list[dict[str, Any]] = []
    for peer in peer_context:
        peer_instance_id = str(peer.get("instance_id", ""))
        if peer_instance_id == own_instance_id:
            continue
        safe = {key: value for key, value in peer.items() if key not in identity_fields}
        if peer_instance_id:
            if peer_instance_id not in codename_map:
                raise ValueError(f"missing frozen codename for peer {peer_instance_id}")
            safe["speaker"] = codename_map[peer_instance_id]
        result.append(safe)
    return result


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
