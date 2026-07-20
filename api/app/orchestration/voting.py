from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Iterable, Mapping, Sequence


ZERO = Decimal("0")
ONE = Decimal("1")
MIN_RAW_WEIGHT = Decimal("0.75")
MAX_RAW_WEIGHT = Decimal("1.25")

_VENDOR_ALIASES = {
    "openai": "openai",
    "gpt": "openai",
    "chatgpt": "openai",
    "azureopenai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "google": "google",
    "gemini": "google",
    "deepseek": "deepseek",
    "kimi": "moonshot",
    "moonshot": "moonshot",
    "qwen": "alibaba",
    "tongyi": "alibaba",
    "alibaba": "alibaba",
    "dashscope": "alibaba",
}


@dataclass(frozen=True, slots=True)
class ScoreFormula:
    version: str
    prior_sample_size: Decimal
    cold_start_prior: Decimal

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("score formula version must not be empty")
        if self.prior_sample_size < ZERO:
            raise ValueError("prior_sample_size must be non-negative")
        _validate_percent(self.cold_start_prior, "cold_start_prior")


@dataclass(frozen=True, slots=True)
class ParticipantScore:
    instance_id: str
    vendor_family: str
    settled_matches: int
    raw_score: Decimal

    def __post_init__(self) -> None:
        if not self.instance_id.strip():
            raise ValueError("instance_id must not be empty")
        if self.settled_matches < 0:
            raise ValueError("settled_matches must be non-negative")
        _validate_percent(self.raw_score, "raw_score")


@dataclass(frozen=True, slots=True)
class FrozenVoteWeight:
    instance_id: str
    vendor_family: str
    settled_matches: int
    prior_mean: Decimal
    smoothed_score: Decimal
    raw_weight: Decimal
    weight: Decimal
    score_formula_version: str


@dataclass(frozen=True, slots=True)
class QuorumResult:
    met: bool
    valid_instance_count: int
    vendor_family_count: int
    instance_ids: tuple[str, ...]
    vendor_families: tuple[str, ...]
    reason: str | None


@dataclass(frozen=True, slots=True)
class SelectionVote:
    instance_id: str
    vendor_family: str
    match_id: str
    yes: bool
    direction_confidence: Decimal
    cutoff_at: datetime | str
    weight: Decimal = ONE
    valid: bool = True


@dataclass(frozen=True, slots=True)
class CandidateVote:
    instance_id: str
    vendor_family: str
    candidate: str
    confidence: Decimal
    weight: Decimal = ONE
    valid: bool = True


@dataclass(frozen=True, slots=True)
class SelectionResult:
    selected_match_ids: tuple[str, ...]
    candidates: tuple["WeightedCandidate", ...]
    quorum: QuorumResult


@dataclass(frozen=True, slots=True)
class WeightedCandidate:
    candidate: str
    weighted_votes: Decimal
    total_weight: Decimal
    weighted_share: Decimal
    raw_votes: int
    voter_count: int
    confidence_median: Decimal


@dataclass(frozen=True, slots=True)
class VoteResult:
    winners: tuple[str, ...]
    audit_tied_candidates: tuple[str, ...]
    consensus: Decimal
    raw_votes: int
    voter_count: int
    weak_consensus: bool
    quorum: QuorumResult


def canonical_vendor_family(value: str, aliases: Mapping[str, str] | None = None) -> str:
    """Return the frozen family key without confusing API compatibility with ownership."""

    normalized = re.sub(r"[^a-z0-9]+", "", value.casefold())
    if not normalized:
        raise ValueError("vendor_family must not be empty")
    alias_map = {**_VENDOR_ALIASES, **(aliases or {})}
    return alias_map.get(normalized, normalized)


def bayesian_score(
    *,
    settled_matches: int,
    raw_score: Decimal,
    prior_mean: Decimal,
    prior_sample_size: Decimal,
) -> Decimal:
    """Apply the score-formula-version prior to a participant's raw score."""

    if settled_matches < 0:
        raise ValueError("settled_matches must be non-negative")
    if prior_sample_size < ZERO:
        raise ValueError("prior_sample_size must be non-negative")
    _validate_percent(raw_score, "raw_score")
    _validate_percent(prior_mean, "prior_mean")
    count = Decimal(settled_matches)
    denominator = count + prior_sample_size
    if denominator == ZERO:
        return prior_mean
    return (count * raw_score + prior_sample_size * prior_mean) / denominator


def freeze_vote_weights(
    participants: Sequence[ParticipantScore],
    formula: ScoreFormula,
) -> tuple[FrozenVoteWeight, ...]:
    """Freeze S, w_raw, and vendor-normalized w_i for one roundtable."""

    if not participants:
        raise ValueError("at least one participant is required")
    _ensure_unique(participant.instance_id for participant in participants)
    observed = [
        participant.raw_score for participant in participants if participant.settled_matches >= 1
    ]
    prior_mean = (
        sum(observed, ZERO) / Decimal(len(observed)) if observed else formula.cold_start_prior
    )
    smoothed = {
        participant.instance_id: bayesian_score(
            settled_matches=participant.settled_matches,
            raw_score=participant.raw_score,
            prior_mean=prior_mean,
            prior_sample_size=formula.prior_sample_size,
        )
        for participant in participants
    }
    score_median = median(smoothed.values())
    raw_weights = {
        instance_id: ONE
        if score_median == ZERO
        else _clamp(score / score_median, MIN_RAW_WEIGHT, MAX_RAW_WEIGHT)
        for instance_id, score in smoothed.items()
    }
    families = {
        participant.instance_id: canonical_vendor_family(participant.vendor_family)
        for participant in participants
    }
    normalized = normalize_vendor_weights(raw_weights, families)
    return tuple(
        FrozenVoteWeight(
            instance_id=participant.instance_id,
            vendor_family=families[participant.instance_id],
            settled_matches=participant.settled_matches,
            prior_mean=prior_mean,
            smoothed_score=smoothed[participant.instance_id],
            raw_weight=raw_weights[participant.instance_id],
            weight=normalized[participant.instance_id],
            score_formula_version=formula.version,
        )
        for participant in participants
    )


def normalize_vendor_weights(
    raw_weights: Mapping[str, Decimal],
    vendor_families: Mapping[str, str],
) -> dict[str, Decimal]:
    """Apply W_vendor=mean(w_raw), then split that total proportionally in-family."""

    if set(raw_weights) != set(vendor_families):
        raise ValueError("raw_weights and vendor_families must contain identical instance IDs")
    grouped: dict[str, list[str]] = defaultdict(list)
    for instance_id, raw_weight in raw_weights.items():
        if raw_weight <= ZERO:
            raise ValueError("raw weights must be positive")
        grouped[canonical_vendor_family(vendor_families[instance_id])].append(instance_id)

    result: dict[str, Decimal] = {}
    for instance_ids in grouped.values():
        vendor_sum = sum((raw_weights[item] for item in instance_ids), ZERO)
        vendor_total = vendor_sum / Decimal(len(instance_ids))
        allocated = ZERO
        for index, instance_id in enumerate(instance_ids):
            weight = (
                vendor_total - allocated
                if index == len(instance_ids) - 1
                else vendor_total * raw_weights[instance_id] / vendor_sum
            )
            result[instance_id] = weight
            allocated += weight
    return result


def validate_quorum(
    votes: Iterable[SelectionVote | CandidateVote | FrozenVoteWeight],
    *,
    minimum_instances: int = 3,
    minimum_vendors: int = 2,
) -> QuorumResult:
    valid: dict[str, str] = {}
    for vote in votes:
        if not getattr(vote, "valid", True):
            continue
        instance_id = vote.instance_id
        family = canonical_vendor_family(vote.vendor_family)
        previous = valid.setdefault(instance_id, family)
        if previous != family:
            raise ValueError(f"instance {instance_id} has inconsistent vendor families")
    families = frozenset(valid.values())
    met = len(valid) >= minimum_instances and len(families) >= minimum_vendors
    if len(valid) < minimum_instances:
        reason = f"requires at least {minimum_instances} valid instances"
    elif len(families) < minimum_vendors:
        reason = f"requires at least {minimum_vendors} vendor families"
    else:
        reason = None
    return QuorumResult(
        met=met,
        valid_instance_count=len(valid),
        vendor_family_count=len(families),
        instance_ids=tuple(sorted(valid)),
        vendor_families=tuple(sorted(families)),
        reason=reason,
    )


def resolve_selection_votes(
    votes: Sequence[SelectionVote],
    *,
    maximum_matches: int,
) -> SelectionResult:
    """Select strictly-over-50% matches and apply the PRD's stable truncation order."""

    if maximum_matches < 0:
        raise ValueError("maximum_matches must be non-negative")
    valid_votes = tuple(vote for vote in votes if vote.valid)
    quorum = validate_quorum(valid_votes)
    if not quorum.met:
        return SelectionResult((), (), quorum)

    grouped: dict[str, list[SelectionVote]] = defaultdict(list)
    for vote in valid_votes:
        _validate_vote(vote.instance_id, vote.weight, vote.direction_confidence)
        grouped[vote.match_id].append(vote)

    ranked: list[tuple[WeightedCandidate, str]] = []
    for match_id, match_votes in grouped.items():
        _ensure_unique(vote.instance_id for vote in match_votes)
        if {vote.instance_id for vote in match_votes} != set(quorum.instance_ids):
            raise ValueError(f"match {match_id} does not contain every valid participant's vote")
        cutoff_values = {_cutoff_key(vote.cutoff_at) for vote in match_votes}
        if len(cutoff_values) != 1:
            raise ValueError(f"match {match_id} has inconsistent cutoff times")
        total_weight = sum((vote.weight for vote in match_votes), ZERO)
        yes_votes = [vote for vote in match_votes if vote.yes]
        yes_weight = sum((vote.weight for vote in yes_votes), ZERO)
        share = yes_weight / total_weight
        if share <= Decimal("0.5"):
            continue
        confidence = _median(vote.direction_confidence for vote in yes_votes)
        cutoff = cutoff_values.pop()
        ranked.append(
            (
                WeightedCandidate(
                    candidate=match_id,
                    weighted_votes=yes_weight,
                    total_weight=total_weight,
                    weighted_share=share,
                    raw_votes=len(yes_votes),
                    voter_count=len(match_votes),
                    confidence_median=confidence,
                ),
                cutoff,
            )
        )
    ranked.sort(
        key=lambda item: (
            -item[0].weighted_share,
            -item[0].confidence_median,
            item[1],
            item[0].candidate,
        )
    )
    selected = tuple(item[0] for item in ranked[:maximum_matches])
    return SelectionResult(tuple(item.candidate for item in selected), selected, quorum)


def resolve_score_votes(votes: Sequence[CandidateVote]) -> VoteResult:
    """Resolve score votes by weight, then direction-confidence median."""

    return _resolve_candidate_votes(votes, conservative_no_bet=False)


def resolve_bet_votes(votes: Sequence[CandidateVote]) -> VoteResult:
    """Resolve plan votes, conservatively choosing no_bet in a final mixed tie."""

    return _resolve_candidate_votes(votes, conservative_no_bet=True)


def _resolve_candidate_votes(
    votes: Sequence[CandidateVote], *, conservative_no_bet: bool
) -> VoteResult:
    valid_votes = tuple(vote for vote in votes if vote.valid)
    quorum = validate_quorum(valid_votes)
    if not quorum.met:
        return VoteResult((), (), ZERO, 0, len(valid_votes), False, quorum)
    _ensure_unique(vote.instance_id for vote in valid_votes)
    for vote in valid_votes:
        _validate_vote(vote.instance_id, vote.weight, vote.confidence)
        if not vote.candidate.strip():
            raise ValueError("candidate must not be empty")

    grouped: dict[str, list[CandidateVote]] = defaultdict(list)
    for vote in valid_votes:
        grouped[vote.candidate].append(vote)
    weights = {
        candidate: sum((vote.weight for vote in candidate_votes), ZERO)
        for candidate, candidate_votes in grouped.items()
    }
    maximum_weight = max(weights.values())
    weighted_tie = tuple(sorted(key for key, value in weights.items() if value == maximum_weight))
    confidence = {
        candidate: _median(vote.confidence for vote in grouped[candidate])
        for candidate in weighted_tie
    }
    maximum_confidence = max(confidence.values())
    final_tie = tuple(
        candidate for candidate in weighted_tie if confidence[candidate] == maximum_confidence
    )
    winners = final_tie
    if conservative_no_bet and "no_bet" in final_tie and len(final_tie) > 1:
        winners = ("no_bet",)
    total_weight = sum((vote.weight for vote in valid_votes), ZERO)
    consensus = max(weights[candidate] for candidate in winners) / total_weight
    return VoteResult(
        winners=winners,
        audit_tied_candidates=final_tie,
        consensus=consensus,
        raw_votes=sum(len(grouped[candidate]) for candidate in winners),
        voter_count=len(valid_votes),
        weak_consensus=len(final_tie) > 1,
        quorum=quorum,
    )


def _ensure_unique(values: Iterable[str]) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError("instance IDs must be unique")


def _validate_vote(instance_id: str, weight: Decimal, confidence: Decimal) -> None:
    if not instance_id.strip():
        raise ValueError("instance_id must not be empty")
    if weight <= ZERO:
        raise ValueError("vote weight must be positive")
    _validate_percent(confidence, "confidence")


def _validate_percent(value: Decimal, name: str) -> None:
    if value < ZERO or value > Decimal("100"):
        raise ValueError(f"{name} must be between 0 and 100")


def _median(values: Iterable[Decimal]) -> Decimal:
    items = tuple(values)
    return median(items) if items else ZERO


def _clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return min(maximum, max(minimum, value))


def _cutoff_key(value: datetime | str) -> str:
    return value.isoformat() if isinstance(value, datetime) else value


# Readable aliases for callers that use domain rather than implementation wording.
calculate_bayesian_score = bayesian_score
check_quorum = validate_quorum
select_matches = resolve_selection_votes
resolve_score_vote = resolve_score_votes
resolve_bet_vote = resolve_bet_votes
