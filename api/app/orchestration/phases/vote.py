from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from app.generated.schemas import ScoreVote
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.orchestration.voting import CandidateVote, VoteResult, resolve_score_votes
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class ScoreVotePhaseResult:
    instance_id: str
    match_id: str
    candidate_id: str
    output: ScoreVote
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


async def run_score_vote_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    match_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> ScoreVotePhaseResult:
    result = await provider.vote_score(dict(context), request)
    output = ScoreVote.model_validate(result.output)
    if output.match_id != match_id:
        raise ValueError("provider score vote targets a different match")
    validated = validate_provider_result(output, phase="score_vote", context=validation_context)
    candidate_id = score_candidate_id(output)
    return ScoreVotePhaseResult(
        instance_id=instance_id,
        match_id=match_id,
        candidate_id=candidate_id,
        output=output,
        provider_request_id=result.provider_request_id,
        event_payload={
            "phase": "score_vote",
            "match_id": match_id,
            "instance_id": instance_id,
            "candidate_id": candidate_id,
            "result": dict(validated),
        },
    )


def score_candidate_id(vote: ScoreVote) -> str:
    return f"{vote.full_time_score.home}:{vote.full_time_score.away}"


def resolve_score_vote_phase(
    votes: Sequence[ScoreVotePhaseResult],
    *,
    vendor_family_by_instance: Mapping[str, str],
    weight_by_instance: Mapping[str, Decimal],
) -> VoteResult:
    weighted = [
        CandidateVote(
            instance_id=vote.instance_id,
            vendor_family=vendor_family_by_instance[vote.instance_id],
            candidate=vote.candidate_id,
            confidence=Decimal(vote.output.direction_confidence),
            weight=weight_by_instance[vote.instance_id],
        )
        for vote in votes
    ]
    return resolve_score_votes(weighted)
