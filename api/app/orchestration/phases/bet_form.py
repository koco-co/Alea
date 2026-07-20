from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.generated.schemas import BetProposal
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class BetFormPhaseResult:
    instance_id: str
    candidate_id: str
    output: BetProposal
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


async def run_bet_form_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    candidate_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> BetFormPhaseResult:
    """Run proposal formation after deterministic ticket validation has been frozen."""

    result = await provider.form_bet(dict(context), request)
    output = BetProposal.model_validate(result.output)
    validated = validate_provider_result(output, phase="bet_form", context=validation_context)
    return BetFormPhaseResult(
        instance_id=instance_id,
        candidate_id=candidate_id,
        output=output,
        provider_request_id=result.provider_request_id,
        event_payload={
            "phase": "bet_proposal",
            "instance_id": instance_id,
            "candidate_id": candidate_id,
            "result": dict(validated),
        },
    )
