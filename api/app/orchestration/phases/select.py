from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from app.generated.schemas import SelectionDebate, SelectionNomination, SelectionVote
from app.orchestration.result_validator import ResultValidationContext, validate_provider_result
from app.orchestration.voting import SelectionResult, SelectionVote as WeightedSelectionVote
from app.orchestration.voting import resolve_selection_votes
from app.providers.contract import BaseProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class SelectionPhaseResult:
    instance_id: str
    phase: str
    output: SelectionNomination | SelectionDebate | SelectionVote
    provider_request_id: str | None
    event_payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RestAnnouncementDraft:
    job_id: str
    business_date: date
    title: str
    body: str
    audit_reason: str


async def run_selection_nomination_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> SelectionPhaseResult:
    result = await provider.nominate_matches(dict(context), request)
    output = SelectionNomination.model_validate(result.output)
    validated = validate_provider_result(
        output, phase="select_nomination", context=validation_context
    )
    return _result(instance_id, "select_nomination", output, result.provider_request_id, validated)


async def run_selection_debate_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> SelectionPhaseResult:
    result = await provider.selection_debate(dict(context), request)
    output = SelectionDebate.model_validate(result.output)
    validated = validate_provider_result(
        output, phase="select_debate", context=validation_context
    )
    return _result(instance_id, "select_debate", output, result.provider_request_id, validated)


async def run_selection_vote_phase(
    provider: BaseProvider,
    *,
    instance_id: str,
    context: Mapping[str, Any],
    request: ProviderRequest,
    validation_context: ResultValidationContext,
) -> SelectionPhaseResult:
    result = await provider.vote_matches(dict(context), request)
    output = SelectionVote.model_validate(result.output)
    validated = validate_provider_result(output, phase="select_vote", context=validation_context)
    return _result(instance_id, "select_vote", output, result.provider_request_id, validated)


def resolve_selection_phase(
    votes: Sequence[WeightedSelectionVote], *, maximum_matches: int
) -> SelectionResult:
    """Resolve strict->50% admission and stable truncation through the shared contract."""

    return resolve_selection_votes(votes, maximum_matches=maximum_matches)


def build_rest_announcement_draft(
    *, job_id: str, business_date: date, result: SelectionResult
) -> RestAnnouncementDraft | None:
    """Create today's-rest draft only for a valid zero-admission terminal result."""

    if not result.quorum.met or result.selected_match_ids:
        return None
    if not job_id.strip():
        raise ValueError("job_id must not be empty")
    return RestAnnouncementDraft(
        job_id=job_id,
        business_date=business_date,
        title="今日休战",
        body=(
            "本轮选场终投没有比赛获得超过 50% 的加权赞成票，"
            "平台今日不发布预测方案。"
        ),
        audit_reason="selection_completed_with_zero_eligible_matches",
    )


def build_weighted_selection_votes(
    *,
    instance_id: str,
    vendor_family: str,
    weight: Decimal,
    output: SelectionVote,
    cutoff_by_match: Mapping[str, datetime | str],
) -> tuple[WeightedSelectionVote, ...]:
    votes: list[WeightedSelectionVote] = []
    for vote in output.votes:
        if vote.match_id not in cutoff_by_match:
            raise ValueError(f"missing frozen cutoff for match {vote.match_id}")
        votes.append(
            WeightedSelectionVote(
                instance_id=instance_id,
                vendor_family=vendor_family,
                match_id=vote.match_id,
                yes=vote.decision == "yes",
                direction_confidence=Decimal(vote.direction_confidence),
                cutoff_at=cutoff_by_match[vote.match_id],
                weight=weight,
            )
        )
    return tuple(votes)


def _result(
    instance_id: str,
    phase: str,
    output: SelectionNomination | SelectionDebate | SelectionVote,
    provider_request_id: str | None,
    validated: Mapping[str, Any],
) -> SelectionPhaseResult:
    if not instance_id.strip():
        raise ValueError("instance_id must not be empty")
    return SelectionPhaseResult(
        instance_id=instance_id,
        phase=phase,
        output=output,
        provider_request_id=provider_request_id,
        event_payload={"phase": phase, "instance_id": instance_id, "result": dict(validated)},
    )
