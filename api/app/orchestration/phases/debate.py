from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.generated.schemas import ScoreDebate
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class DebatePhaseResult:
    instance_id: str
    match_id: str
    round_number: int
    speaker_codename: str
    output: ScoreDebate
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


def assign_codenames(instance_ids: Sequence[str], *, codename_seed: str) -> Mapping[str, str]:
    """Create a stable complete-roster map; later absences never cause reassignment."""

    unique = tuple(dict.fromkeys(instance_ids))
    if len(unique) != len(instance_ids) or any(not item.strip() for item in unique):
        raise ValueError("instance_ids must be non-empty and unique")
    shuffled = list(unique)
    random.Random(_seed_int(codename_seed, "codename-map")).shuffle(shuffled)
    return {instance_id: f"玄机{index + 1:02d}" for index, instance_id in enumerate(shuffled)}


def anonymize_and_shuffle_messages(
    messages: Sequence[Mapping[str, Any]],
    *,
    codename_map: Mapping[str, str],
    own_instance_id: str,
    shuffle_seed: str,
    match_id: str,
    round_number: int,
) -> tuple[Mapping[str, Any], ...]:
    """Remove identities, omit the caller's codename, and deterministically shuffle peers."""

    safe: list[Mapping[str, Any]] = []
    for message in messages:
        instance_id = message.get("instance_id")
        if not isinstance(instance_id, str) or instance_id not in codename_map:
            raise ValueError("every debate message requires a frozen participant instance_id")
        public = {
            key: value
            for key, value in message.items()
            if key not in {"instance_id", "provider", "model_id", "provider_request_id"}
        }
        if instance_id != own_instance_id:
            public["speaker_codename"] = codename_map[instance_id]
        else:
            public["speaker_codename"] = "self"
        safe.append(public)
    random.Random(_seed_int(shuffle_seed, match_id, str(round_number), own_instance_id)).shuffle(
        safe
    )
    return tuple(safe)


async def run_debate_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    match_id: str,
    round_number: int,
    speaker_codename: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> DebatePhaseResult:
    if round_number < 1:
        raise ValueError("round_number must be at least 1")
    result = await provider.debate_response(dict(context), request)
    output = ScoreDebate.model_validate(result.output)
    validated = validate_provider_result(output, phase="debate", context=validation_context)
    return DebatePhaseResult(
        instance_id=instance_id,
        match_id=match_id,
        round_number=round_number,
        speaker_codename=speaker_codename,
        output=output,
        provider_request_id=result.provider_request_id,
        event_payload={
            "phase": "debate",
            "match_id": match_id,
            "round_number": round_number,
            "speaker_codename": speaker_codename,
            "result": dict(validated),
        },
    )


def _seed_int(*parts: str) -> int:
    if any(not part for part in parts):
        raise ValueError("shuffle seed parts must not be empty")
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")
