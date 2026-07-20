from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from app.generated.schemas import BetVote
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.orchestration.voting import CandidateVote, VoteResult, resolve_bet_votes
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class BetVotePhaseResult:
    instance_id: str
    output: BetVote
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


async def run_bet_vote_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> BetVotePhaseResult:
    result = await provider.vote_bet(dict(context), request)
    output = BetVote.model_validate(result.output)
    validated = validate_provider_result(output, phase="bet_vote", context=validation_context)
    return BetVotePhaseResult(
        instance_id=instance_id,
        output=output,
        provider_request_id=result.provider_request_id,
        event_payload={
            "phase": "bet_vote",
            "instance_id": instance_id,
            "candidate_id": output.candidate_id,
            "decision": output.decision,
            "result": dict(validated),
        },
    )


def resolve_bet_vote_phase(
    votes: Sequence[BetVotePhaseResult],
    *,
    vendor_family_by_instance: Mapping[str, str],
    weight_by_instance: Mapping[str, Decimal],
) -> VoteResult:
    weighted = [
        CandidateVote(
            instance_id=vote.instance_id,
            vendor_family=vendor_family_by_instance[vote.instance_id],
            candidate=("no_bet" if vote.output.decision == "no_bet" else vote.output.candidate_id),
            confidence=Decimal(vote.output.plan_confidence),
            weight=weight_by_instance[vote.instance_id],
        )
        for vote in votes
    ]
    return resolve_bet_votes(weighted)
