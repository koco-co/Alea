from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.generated.schemas import BetDebate
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class BetDebatePhaseResult:
    instance_id: str
    round_number: int
    speaker_codename: str
    output: BetDebate
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


async def run_bet_debate_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    round_number: int,
    speaker_codename: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> BetDebatePhaseResult:
    if round_number < 1:
        raise ValueError("round_number must be at least 1")
    result = await provider.debate_bet(dict(context), request)
    output = BetDebate.model_validate(result.output)
    validated = validate_provider_result(output, phase="bet_debate", context=validation_context)
    return BetDebatePhaseResult(
        instance_id=instance_id,
        round_number=round_number,
        speaker_codename=speaker_codename,
        output=output,
        provider_request_id=result.provider_request_id,
        event_payload={
            "phase": "bet_debate",
            "round_number": round_number,
            "speaker_codename": speaker_codename,
            "result": dict(validated),
        },
    )
