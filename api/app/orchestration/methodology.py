from __future__ import annotations

import hashlib
import math
import random
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Iterable, Mapping, Sequence

from app.orchestration.roundtable import RoundtableJobState
from app.orchestration.voting import CandidateVote, QuorumResult, validate_quorum


METRIC_NAMES = (
    "exact_score",
    "had_direction",
    "total_goals",
    "half_full",
    "invalid_output_rate",
    "execution_failure_rate",
)


class ProposalStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    BACKTESTING = "backtesting"
    READY_FOR_REVIEW = "ready_for_review"
    PENDING_ADMIN_CONFIRMATION = "pending_admin_confirmation"
    REJECTED = "rejected"
    REVISE_AND_REVIEW = "revise_and_review"
    PUBLISHED = "published"


class ReviewDecision(StrEnum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    REVISE_AND_REVIEW = "revise_and_review"


@dataclass(frozen=True, slots=True)
class MethodologyTriggerSettings:
    distinct_match_threshold: int = 3
    lesson_count_threshold: int = 5
    consecutive_error_threshold: int = 5
    lookback_days: int | None = None
    version: int = 1

    def __post_init__(self) -> None:
        if min(
            self.distinct_match_threshold,
            self.lesson_count_threshold,
            self.consecutive_error_threshold,
            self.version,
        ) < 1:
            raise ValueError("methodology trigger values must be positive")
        if self.lookback_days is not None and self.lookback_days < 1:
            raise ValueError("lookback_days must be positive or null")


@dataclass(frozen=True, slots=True)
class LessonEvidence:
    lesson_id: str
    review_id: str
    match_id: str
    ai_instance_id: str
    category: str
    rule: str
    status: str = "active"
    review_status: str = "published"
    consecutive_count: int = 1
    published_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MethodologyProposal:
    proposal_id: str
    category: str
    normalized_pattern_hash: str
    evidence_lesson_ids: tuple[str, ...]
    evidence_match_ids: tuple[str, ...]
    involved_ai_ids: tuple[str, ...]
    trigger_settings_version: int
    status: ProposalStatus = ProposalStatus.PENDING_REVIEW


@dataclass(frozen=True, slots=True)
class BacktestExecutionConfig:
    attempts_per_instance: int
    sample_size: int
    evaluator_version: str
    generation_parameter_versions: Mapping[str, int]
    output_schema_version: int
    tool_contract_version: int
    random_seeds: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if self.attempts_per_instance < 2:
            raise ValueError("attempts_per_instance must be at least 2")
        if self.sample_size < 20:
            raise ValueError("sample_size must be at least 20")
        if len(self.random_seeds) != self.attempts_per_instance:
            raise ValueError("random_seeds must match attempts_per_instance")


@dataclass(frozen=True, slots=True)
class BacktestSample:
    sample_id: str
    input_snapshot_id: str
    result_version_id: str
    history_context_version_ids: Mapping[str, str]
    lesson_set_version_ids: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class BacktestAttempt:
    sample_id: str
    instance_id: str
    attempt_index: int
    variant: str
    metrics: Mapping[str, Decimal]
    valid_output: bool
    execution_succeeded: bool


@dataclass(frozen=True, slots=True)
class MetricComparison:
    old_mean: Decimal
    new_mean: Decimal
    paired_delta: Decimal
    confidence_interval_95: tuple[Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class BacktestResult:
    total_matches: int
    attempts_per_instance: int
    metrics: Mapping[str, MetricComparison]
    leakage_checked: bool


@dataclass(frozen=True, slots=True)
class MethodologyReviewResolution:
    decision: ReviewDecision
    next_state: RoundtableJobState
    proposal_status: ProposalStatus
    weighted_share: Decimal
    quorum: QuorumResult


@dataclass(frozen=True, slots=True)
class MethodologyVersion:
    version: int
    content: str
    reason: str
    approved_by: str
    source_version: int
    backtest_id: str | None
    review_job_id: str | None
    rollback_of_version: int | None = None


class AdminInterventionKind(StrEnum):
    ADD_VIEWPOINT = "add_viewpoint"
    REQUEST_EXPLANATION = "request_explanation"
    ADOPT_REVISION_DIRECTION = "adopt_revision_direction"
    DIRECT_RULING = "direct_ruling"
    BYPASS_AND_PUBLISH = "bypass_and_publish"


@dataclass(frozen=True, slots=True)
class AdminIntervention:
    kind: AdminInterventionKind
    actor_id: str
    reason: str
    content: str
    source_record_ids: tuple[str, ...] = ()
    facts_verified: bool = False

    @property
    def requires_new_revision_and_backtest(self) -> bool:
        return self.kind is AdminInterventionKind.ADOPT_REVISION_DIRECTION


def normalize_pattern(rule: str) -> str:
    normalized = unicodedata.normalize("NFKC", rule).casefold()
    normalized = re.sub(r"\d+(?:\.\d+)?", "#", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalized_pattern_hash(rule: str) -> str:
    normalized = normalize_pattern(rule)
    if not normalized:
        raise ValueError("lesson rule must not be empty")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def aggregate_methodology_proposals(
    lessons: Iterable[LessonEvidence],
    settings: MethodologyTriggerSettings,
    *,
    existing_evidence_fingerprints: Iterable[str] = (),
    now: datetime | None = None,
) -> tuple[MethodologyProposal, ...]:
    """Aggregate only published active lessons and deduplicate identical evidence sets."""

    timestamp = now or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = (
        timestamp.astimezone(UTC) - timedelta(days=settings.lookback_days)
        if settings.lookback_days is not None
        else None
    )
    groups: dict[tuple[str, str], list[LessonEvidence]] = {}
    for lesson in lessons:
        if lesson.status != "active" or lesson.review_status != "published":
            continue
        if cutoff is not None:
            if lesson.published_at is None:
                continue
            if lesson.published_at.tzinfo is None:
                raise ValueError("lesson published_at must be timezone-aware")
            if lesson.published_at.astimezone(UTC) < cutoff:
                continue
        key = (lesson.category, normalized_pattern_hash(lesson.rule))
        groups.setdefault(key, []).append(lesson)
    existing = set(existing_evidence_fingerprints)
    proposals: list[MethodologyProposal] = []
    for (category, pattern_hash), evidence in sorted(groups.items()):
        match_ids = tuple(sorted({item.match_id for item in evidence}))
        ai_ids = tuple(sorted({item.ai_instance_id for item in evidence}))
        streak = max((item.consecutive_count for item in evidence), default=0)
        triggered = (
            len(match_ids) >= settings.distinct_match_threshold
            or len(evidence) >= settings.lesson_count_threshold
            or streak >= settings.consecutive_error_threshold
        )
        lesson_ids = tuple(sorted({item.lesson_id for item in evidence}))
        fingerprint = hashlib.sha256("\x1f".join(lesson_ids).encode("utf-8")).hexdigest()
        if not triggered or fingerprint in existing:
            continue
        existing.add(fingerprint)
        proposals.append(
            MethodologyProposal(
                proposal_id=f"methodology:{pattern_hash[:16]}:{fingerprint[:12]}",
                category=category,
                normalized_pattern_hash=pattern_hash,
                evidence_lesson_ids=lesson_ids,
                evidence_match_ids=match_ids,
                involved_ai_ids=ai_ids,
                trigger_settings_version=settings.version,
            )
        )
    return tuple(proposals)


def validate_backtest_samples(
    samples: Sequence[BacktestSample], config: BacktestExecutionConfig
) -> None:
    if len(samples) < 20 or len(samples) < config.sample_size:
        raise ValueError(
            "insufficient backtest samples: "
            f"{len(samples)} available, {config.sample_size} required"
        )
    if len({sample.sample_id for sample in samples}) != len(samples):
        raise ValueError("backtest sample IDs must be unique")
    for sample in samples:
        if not sample.input_snapshot_id or not sample.result_version_id:
            raise ValueError(
                "backtest samples require frozen input and independent result refs"
            )


def evaluate_paired_backtest(
    attempts: Sequence[BacktestAttempt],
    *,
    attempts_per_instance: int,
    bootstrap_iterations: int = 2000,
    bootstrap_seed: int = 0,
) -> BacktestResult:
    """Evaluate OLD/NEW pairs by match and report deterministic bootstrap intervals."""

    if attempts_per_instance < 2:
        raise ValueError("attempts_per_instance must be at least 2")
    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")
    grouped: dict[tuple[str, str, int], dict[str, BacktestAttempt]] = {}
    for attempt in attempts:
        if attempt.variant not in {"OLD", "NEW"}:
            raise ValueError("backtest variant must be OLD or NEW")
        grouped.setdefault(
            (attempt.sample_id, attempt.instance_id, attempt.attempt_index), {}
        )[attempt.variant] = attempt
    pairs = [pair for pair in grouped.values() if set(pair) == {"OLD", "NEW"}]
    if not pairs:
        raise ValueError("no complete OLD/NEW pairs")
    sample_ids = {attempt.sample_id for attempt in attempts}
    if len(sample_ids) < 20:
        raise ValueError("methodology backtests require at least 20 distinct matches")
    attempts_by_instance: dict[tuple[str, str], set[int]] = {}
    for sample_id, instance_id, attempt_index in grouped:
        attempts_by_instance.setdefault((sample_id, instance_id), set()).add(attempt_index)
    if any(len(indexes) < attempts_per_instance for indexes in attempts_by_instance.values()):
        raise ValueError("every sample and instance requires the configured repeated attempts")
    metrics: dict[str, MetricComparison] = {}
    for metric in METRIC_NAMES:
        old_values: list[Decimal] = []
        new_values: list[Decimal] = []
        for pair in pairs:
            old, new = pair["OLD"], pair["NEW"]
            old_values.append(_attempt_metric(old, metric))
            new_values.append(_attempt_metric(new, metric))
        deltas = [new - old for old, new in zip(old_values, new_values, strict=True)]
        metrics[metric] = MetricComparison(
            old_mean=_mean(old_values),
            new_mean=_mean(new_values),
            paired_delta=_mean(deltas),
            confidence_interval_95=_bootstrap_interval(
                deltas, bootstrap_iterations, bootstrap_seed + len(metrics)
            ),
        )
    return BacktestResult(
        total_matches=len(sample_ids),
        attempts_per_instance=attempts_per_instance,
        metrics=metrics,
        leakage_checked=True,
    )


def resolve_methodology_review(votes: Sequence[CandidateVote]) -> MethodologyReviewResolution:
    valid_votes = tuple(vote for vote in votes if vote.valid)
    quorum = validate_quorum(valid_votes)
    if not quorum.met:
        return MethodologyReviewResolution(
            ReviewDecision.REVISE_AND_REVIEW,
            RoundtableJobState.NO_QUORUM,
            ProposalStatus.REVISE_AND_REVIEW,
            Decimal("0"),
            quorum,
        )
    allowed = {decision.value for decision in ReviewDecision}
    if any(vote.candidate not in allowed for vote in valid_votes):
        raise ValueError("methodology votes must use support, oppose, or revise_and_review")
    if any(vote.weight <= 0 for vote in valid_votes):
        raise ValueError("methodology vote weights must be positive")
    total = sum((vote.weight for vote in valid_votes), Decimal("0"))
    shares = {
        decision: sum(
            (vote.weight for vote in valid_votes if vote.candidate == decision.value),
            Decimal("0"),
        )
        / total
        for decision in ReviewDecision
    }
    if shares[ReviewDecision.SUPPORT] >= Decimal("0.60"):
        decision = ReviewDecision.SUPPORT
        state = RoundtableJobState.PENDING_ADMIN_CONFIRMATION
        status = ProposalStatus.PENDING_ADMIN_CONFIRMATION
    elif shares[ReviewDecision.OPPOSE] >= Decimal("0.60"):
        decision = ReviewDecision.OPPOSE
        state = RoundtableJobState.COMPLETED
        status = ProposalStatus.REJECTED
    else:
        decision = ReviewDecision.REVISE_AND_REVIEW
        state = RoundtableJobState.REVISE_AND_REVIEW
        status = ProposalStatus.REVISE_AND_REVIEW
    return MethodologyReviewResolution(decision, state, status, shares[decision], quorum)


def require_admin_intervention_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise ValueError("administrator intervention requires a non-empty audit reason")
    return normalized


def validate_admin_intervention(intervention: AdminIntervention) -> AdminIntervention:
    if not intervention.actor_id.strip() or not intervention.content.strip():
        raise ValueError("administrator intervention requires actor and content")
    require_admin_intervention_reason(intervention.reason)
    if intervention.source_record_ids and not intervention.facts_verified:
        raise ValueError("administrator factual material must be verified before AI injection")
    return intervention


def append_methodology_version(
    *,
    current_version: MethodologyVersion,
    content: str,
    reason: str,
    approved_by: str,
    backtest_id: str | None,
    review_job_id: str | None,
    rollback_of_version: int | None = None,
) -> MethodologyVersion:
    """Build an append-only version; persistence must lock and compare current_version."""

    normalized_content = content.strip()
    if not normalized_content or not approved_by.strip():
        raise ValueError("methodology publication requires content and administrator")
    if not reason.strip():
        raise ValueError("methodology publication requires an audit reason")
    if backtest_id is None and review_job_id is not None:
        raise ValueError("AI-reviewed publication requires a completed backtest")
    return MethodologyVersion(
        version=current_version.version + 1,
        content=normalized_content,
        reason=reason.strip(),
        approved_by=approved_by.strip(),
        source_version=current_version.version,
        backtest_id=backtest_id,
        review_job_id=review_job_id,
        rollback_of_version=rollback_of_version,
    )


def _attempt_metric(attempt: BacktestAttempt, metric: str) -> Decimal:
    if metric == "invalid_output_rate":
        return Decimal("0") if attempt.valid_output else Decimal("1")
    if metric == "execution_failure_rate":
        return Decimal("0") if attempt.execution_succeeded else Decimal("1")
    return attempt.metrics.get(metric, Decimal("0"))


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))


def _bootstrap_interval(
    values: Sequence[Decimal], iterations: int, seed: int
) -> tuple[Decimal, Decimal]:
    if len(values) == 1:
        return values[0], values[0]
    generator = random.Random(seed)
    means = sorted(
        _mean([values[generator.randrange(len(values))] for _ in values])
        for _ in range(iterations)
    )
    lower = means[max(0, math.floor(iterations * 0.025) - 1)]
    upper = means[min(iterations - 1, math.ceil(iterations * 0.975) - 1)]
    return lower, upper
