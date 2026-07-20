from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from decimal import Decimal
from statistics import median
from typing import Iterable, Mapping, Sequence

from app.orchestration.voting import canonical_vendor_family, normalize_vendor_weights


ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")


class RankingError(ValueError):
    """Raised when immutable ranking facts or a formula version are invalid."""


@dataclass(frozen=True, slots=True)
class Score:
    home: int
    away: int

    def __post_init__(self) -> None:
        if self.home < 0 or self.away < 0:
            raise RankingError("scores must be non-negative")


@dataclass(frozen=True, slots=True)
class MatchHitFact:
    instance_id: str
    match_id: str
    predicted_full_time: Score
    predicted_half_time: Score
    actual_full_time: Score
    actual_half_time: Score
    direction_confidence: Decimal
    exact_score_hit: bool
    direction_hit: bool
    total_goals_hit: bool
    half_full_hit: bool

    def __post_init__(self) -> None:
        if not self.instance_id.strip() or not self.match_id.strip():
            raise RankingError("instance_id and match_id must not be empty")
        _validate_percent(self.direction_confidence, "direction_confidence")
        expected = _hit_values(
            self.predicted_full_time,
            self.predicted_half_time,
            self.actual_full_time,
            self.actual_half_time,
        )
        actual = (
            self.exact_score_hit,
            self.direction_hit,
            self.total_goals_hit,
            self.half_full_hit,
        )
        if actual != expected:
            raise RankingError("stored hit facts do not match their immutable scores")


@dataclass(frozen=True, slots=True)
class RankingFormula:
    version: str
    prior_sample_count: Decimal
    cold_start_prior: Decimal
    dimension_weights: Mapping[str, Decimal]
    minimum_settled: int = 10
    minimum_coverage: Decimal = Decimal("0.80")
    raw_weight_min: Decimal = Decimal("0.75")
    raw_weight_max: Decimal = Decimal("1.25")
    calibration_min_samples: int = 5
    calibration_bias_threshold: Decimal = Decimal("10")

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise RankingError("formula version must not be empty")
        if self.prior_sample_count < ZERO:
            raise RankingError("prior_sample_count must be non-negative")
        _validate_percent(self.cold_start_prior, "cold_start_prior")
        required = {"exact_score", "direction", "total_goals", "half_full"}
        if set(self.dimension_weights) != required:
            raise RankingError("formula must define exactly four dimension weights")
        if any(value < ZERO for value in self.dimension_weights.values()):
            raise RankingError("dimension weights must be non-negative")
        if sum(self.dimension_weights.values(), ZERO) != Decimal("1"):
            raise RankingError("dimension weights must sum to 1")
        if self.minimum_settled < 0 or self.calibration_min_samples < 1:
            raise RankingError("sample thresholds are invalid")
        if self.minimum_coverage < ZERO or self.minimum_coverage > Decimal("1"):
            raise RankingError("minimum_coverage must be between 0 and 1")
        if self.raw_weight_min <= ZERO or self.raw_weight_max < self.raw_weight_min:
            raise RankingError("raw weight bounds are invalid")
        _validate_percent(self.calibration_bias_threshold, "calibration_bias_threshold")

    @classmethod
    def from_config(cls, version: str | int, config: Mapping[str, object]) -> RankingFormula:
        dimensions = config.get("dimensions")
        if not isinstance(dimensions, Mapping):
            raise RankingError("formula config is missing dimensions")
        try:
            return cls(
                version=str(version),
                prior_sample_count=Decimal(str(config["prior_sample_count"])),
                cold_start_prior=Decimal(str(config["cold_start_prior"])),
                dimension_weights={
                    str(key): Decimal(str(value)) for key, value in dimensions.items()
                },
                minimum_settled=int(config.get("minimum_settled", 10)),
                minimum_coverage=Decimal(str(config.get("minimum_coverage", "0.80"))),
                raw_weight_min=Decimal(str(config.get("raw_weight_min", "0.75"))),
                raw_weight_max=Decimal(str(config.get("raw_weight_max", "1.25"))),
                calibration_min_samples=int(config.get("calibration_min_samples", 5)),
                calibration_bias_threshold=Decimal(
                    str(config.get("calibration_bias_threshold", 10))
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RankingError("formula config is invalid") from exc


@dataclass(frozen=True, slots=True)
class Participation:
    instance_id: str
    vendor_family: str
    eligible_matches: int
    submitted_final_scores: int

    def __post_init__(self) -> None:
        if not self.instance_id.strip() or not self.vendor_family.strip():
            raise RankingError("participant identity must not be empty")
        if self.eligible_matches < 0 or self.submitted_final_scores < 0:
            raise RankingError("participation counts must be non-negative")
        if self.submitted_final_scores > self.eligible_matches:
            raise RankingError("submitted finals cannot exceed eligible matches")


@dataclass(frozen=True, slots=True)
class DimensionScores:
    exact_score: Decimal
    direction: Decimal
    total_goals: Decimal
    half_full: Decimal


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    label: str
    lower: int
    upper: int
    sample_count: int
    mean_confidence: Decimal | None
    actual_hit_rate: Decimal | None
    bias: Decimal | None
    conclusion: str | None


@dataclass(frozen=True, slots=True)
class RankingRow:
    instance_id: str
    vendor_family: str
    formula_version: str
    settled_matches: int
    coverage: Decimal
    dimensions: DimensionScores
    raw_score: Decimal
    prior_mean: Decimal
    smoothed_score: Decimal
    raw_weight: Decimal
    normalized_weight: Decimal
    rank: int | None
    qualification: str | None
    calibration: tuple[CalibrationBucket, ...]
    calibration_warning: str | None


def direction(score: Score) -> str:
    if score.home > score.away:
        return "home"
    if score.home < score.away:
        return "away"
    return "draw"


def evaluate_match(
    *,
    instance_id: str,
    match_id: str,
    predicted_full_time: Score,
    predicted_half_time: Score,
    actual_full_time: Score,
    actual_half_time: Score,
    direction_confidence: Decimal,
) -> MatchHitFact:
    """Create the four immutable hit facts from one notarized final score."""

    if not instance_id.strip() or not match_id.strip():
        raise RankingError("instance_id and match_id must not be empty")
    _validate_percent(direction_confidence, "direction_confidence")
    hit_values = _hit_values(
        predicted_full_time,
        predicted_half_time,
        actual_full_time,
        actual_half_time,
    )
    return MatchHitFact(
        instance_id=instance_id,
        match_id=match_id,
        predicted_full_time=predicted_full_time,
        predicted_half_time=predicted_half_time,
        actual_full_time=actual_full_time,
        actual_half_time=actual_half_time,
        direction_confidence=direction_confidence,
        exact_score_hit=hit_values[0],
        direction_hit=hit_values[1],
        total_goals_hit=hit_values[2],
        half_full_hit=hit_values[3],
    )


def calculate_rankings(
    facts: Sequence[MatchHitFact],
    participants: Sequence[Participation],
    formula: RankingFormula,
) -> tuple[RankingRow, ...]:
    """Compute a version-isolated leaderboard and frozen vendor-normalized weights."""

    by_participant = {item.instance_id: item for item in participants}
    if len(by_participant) != len(participants):
        raise RankingError("participant IDs must be unique")
    unknown = {fact.instance_id for fact in facts}.difference(by_participant)
    if unknown:
        raise RankingError(f"facts reference unknown participants: {', '.join(sorted(unknown))}")
    seen_facts: set[tuple[str, str]] = set()
    grouped: dict[str, list[MatchHitFact]] = defaultdict(list)
    for fact in facts:
        key = (fact.instance_id, fact.match_id)
        if key in seen_facts:
            raise RankingError("only one immutable hit fact is allowed per instance and match")
        seen_facts.add(key)
        grouped[fact.instance_id].append(fact)
    for participant in participants:
        if len(grouped[participant.instance_id]) > participant.submitted_final_scores:
            raise RankingError("settled facts cannot exceed submitted final scores")

    dimensions = {
        participant.instance_id: _dimension_scores(grouped[participant.instance_id])
        for participant in participants
    }
    raw_scores = {
        participant.instance_id: _raw_score(dimensions[participant.instance_id], formula)
        for participant in participants
    }
    observed = [
        raw_scores[participant.instance_id]
        for participant in participants
        if grouped[participant.instance_id]
    ]
    prior_mean = (
        sum(observed, ZERO) / Decimal(len(observed)) if observed else formula.cold_start_prior
    )
    smoothed = {
        participant.instance_id: bayesian_smooth(
            settled_matches=len(grouped[participant.instance_id]),
            raw_score=raw_scores[participant.instance_id],
            prior_mean=prior_mean,
            prior_sample_count=formula.prior_sample_count,
        )
        for participant in participants
    }
    score_median = median(smoothed.values()) if smoothed else ZERO
    raw_weights = {
        instance_id: Decimal("1")
        if score_median == ZERO
        else _clamp(
            score / score_median,
            formula.raw_weight_min,
            formula.raw_weight_max,
        )
        for instance_id, score in smoothed.items()
    }
    families = {
        item.instance_id: canonical_vendor_family(item.vendor_family) for item in participants
    }
    normalized = normalize_vendor_weights(raw_weights, families) if participants else {}

    draft: list[RankingRow] = []
    for participant in participants:
        instance_facts = grouped[participant.instance_id]
        coverage = (
            Decimal(participant.submitted_final_scores) / Decimal(participant.eligible_matches)
            if participant.eligible_matches
            else ZERO
        )
        qualification = None
        if len(instance_facts) < formula.minimum_settled:
            qualification = "insufficient_sample"
        elif coverage < formula.minimum_coverage:
            qualification = "insufficient_coverage"
        buckets = calibration_buckets(instance_facts, formula=formula)
        draft.append(
            RankingRow(
                instance_id=participant.instance_id,
                vendor_family=families[participant.instance_id],
                formula_version=formula.version,
                settled_matches=len(instance_facts),
                coverage=coverage,
                dimensions=dimensions[participant.instance_id],
                raw_score=raw_scores[participant.instance_id],
                prior_mean=prior_mean,
                smoothed_score=smoothed[participant.instance_id],
                raw_weight=raw_weights[participant.instance_id],
                normalized_weight=normalized[participant.instance_id],
                rank=None,
                qualification=qualification,
                calibration=buckets,
                calibration_warning=_calibration_warning(buckets),
            )
        )

    eligible = sorted(
        (row for row in draft if row.qualification is None),
        key=lambda row: (-row.smoothed_score, row.instance_id),
    )
    ranks = {row.instance_id: index + 1 for index, row in enumerate(eligible)}
    rows = [replace(row, rank=ranks.get(row.instance_id)) for row in draft]
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.rank is None,
                row.rank or 0,
                -row.smoothed_score,
                row.instance_id,
            ),
        )
    )


def bayesian_smooth(
    *,
    settled_matches: int,
    raw_score: Decimal,
    prior_mean: Decimal,
    prior_sample_count: Decimal,
) -> Decimal:
    if settled_matches < 0 or prior_sample_count < ZERO:
        raise RankingError("sample counts must be non-negative")
    _validate_percent(raw_score, "raw_score")
    _validate_percent(prior_mean, "prior_mean")
    denominator = Decimal(settled_matches) + prior_sample_count
    if denominator == ZERO:
        return prior_mean
    return (
        Decimal(settled_matches) * raw_score + prior_sample_count * prior_mean
    ) / denominator


def calibration_buckets(
    facts: Iterable[MatchHitFact],
    *,
    formula: RankingFormula,
) -> tuple[CalibrationBucket, ...]:
    """Compare final direction confidence with actual direction hit rate."""

    boundaries = ((0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100))
    values = tuple(facts)
    result: list[CalibrationBucket] = []
    for lower, upper in boundaries:
        bucket = [
            fact
            for fact in values
            if Decimal(lower) <= fact.direction_confidence
            and (
                fact.direction_confidence < Decimal(upper)
                or (upper == 100 and fact.direction_confidence == ONE_HUNDRED)
            )
        ]
        label = f"{lower}-{upper}%"
        if not bucket:
            result.append(CalibrationBucket(label, lower, upper, 0, None, None, None, None))
            continue
        mean_confidence = sum((item.direction_confidence for item in bucket), ZERO) / Decimal(
            len(bucket)
        )
        hit_rate = Decimal(sum(item.direction_hit for item in bucket)) * ONE_HUNDRED / Decimal(
            len(bucket)
        )
        bias = mean_confidence - hit_rate
        conclusion = None
        if len(bucket) >= formula.calibration_min_samples:
            if bias >= formula.calibration_bias_threshold:
                conclusion = "overconfident"
            elif bias <= -formula.calibration_bias_threshold:
                conclusion = "underconfident"
            else:
                conclusion = "calibrated"
        result.append(
            CalibrationBucket(
                label,
                lower,
                upper,
                len(bucket),
                mean_confidence,
                hit_rate,
                bias,
                conclusion,
            )
        )
    return tuple(result)


def _dimension_scores(facts: Sequence[MatchHitFact]) -> DimensionScores:
    if not facts:
        return DimensionScores(ZERO, ZERO, ZERO, ZERO)
    denominator = Decimal(len(facts))

    def percent(count: int) -> Decimal:
        return Decimal(count) * ONE_HUNDRED / denominator

    return DimensionScores(
        exact_score=percent(sum(item.exact_score_hit for item in facts)),
        direction=percent(sum(item.direction_hit for item in facts)),
        total_goals=percent(sum(item.total_goals_hit for item in facts)),
        half_full=percent(sum(item.half_full_hit for item in facts)),
    )


def _hit_values(
    predicted_full_time: Score,
    predicted_half_time: Score,
    actual_full_time: Score,
    actual_half_time: Score,
) -> tuple[bool, bool, bool, bool]:
    full_direction_hit = direction(predicted_full_time) == direction(actual_full_time)
    return (
        predicted_full_time == actual_full_time,
        full_direction_hit,
        (predicted_full_time.home + predicted_full_time.away)
        == (actual_full_time.home + actual_full_time.away),
        direction(predicted_half_time) == direction(actual_half_time) and full_direction_hit,
    )


def _raw_score(scores: DimensionScores, formula: RankingFormula) -> Decimal:
    return sum(
        (
            getattr(scores, dimension) * weight
            for dimension, weight in formula.dimension_weights.items()
        ),
        ZERO,
    )


def _calibration_warning(buckets: Sequence[CalibrationBucket]) -> str | None:
    conclusions = {item.conclusion for item in buckets}
    if "overconfident" in conclusions:
        return "historically_overoptimistic"
    if "underconfident" in conclusions:
        return "historically_overconservative"
    return None


def _clamp(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return min(max(value, lower), upper)


def _validate_percent(value: Decimal, name: str) -> None:
    if value < ZERO or value > ONE_HUNDRED:
        raise RankingError(f"{name} must be between 0 and 100")
