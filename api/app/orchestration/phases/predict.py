from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.generated.schemas import ScorePrediction
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class PredictionPhaseResult:
    instance_id: str
    match_id: str
    output: ScorePrediction
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


async def run_predict_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    match_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> PredictionPhaseResult:
    """Run one independent prediction; malformed output never advances the match."""

    if not instance_id.strip() or not match_id.strip():
        raise ValueError("instance_id and match_id must not be empty")
    result = await provider.predict_score(dict(context), request)
    output = ScorePrediction.model_validate(result.output)
    if output.match_id != match_id:
        raise ValueError("provider prediction targets a different match")
    validated = validate_provider_result(output, phase="predict", context=validation_context)
    return PredictionPhaseResult(
        instance_id=instance_id,
        match_id=match_id,
        output=output,
        provider_request_id=result.provider_request_id,
        event_payload={
            "phase": "prediction",
            "match_id": match_id,
            "instance_id": instance_id,
            "result": dict(validated),
        },
    )
