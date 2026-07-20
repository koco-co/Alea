from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class ResultValidationContext:
    frozen_match_ids: frozenset[str] = field(default_factory=frozenset)
    frozen_source_record_ids: frozenset[str] = field(default_factory=frozenset)
    frozen_offer_option_ids: frozenset[str] = field(default_factory=frozenset)
    verified_fact_claim_ids: frozenset[str] = field(default_factory=frozenset)
    ticket_validated_candidate_ids: frozenset[str] = field(default_factory=frozenset)
    ticket_validation_passed: bool = False
    offer_selections: Mapping[str, str] = field(default_factory=dict)
    match_scores: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    public_fact_claim_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class ResultValidationError(ValueError):
    def __init__(self, issues: Sequence[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in self.issues)
        super().__init__(summary)


def score_direction(score: Mapping[str, Any]) -> str:
    home = score.get("home")
    away = score.get("away")
    if not isinstance(home, int) or isinstance(home, bool):
        raise ValueError("score.home must be an integer")
    if not isinstance(away, int) or isinstance(away, bool):
        raise ValueError("score.away must be an integer")
    return "home" if home > away else "away" if home < away else "draw"


def collect_validation_issues(
    payload: Mapping[str, Any] | BaseModel,
    *,
    phase: str,
    context: ResultValidationContext,
) -> tuple[ValidationIssue, ...]:
    data = _as_mapping(payload)
    issues: list[ValidationIssue] = []
    _validate_score_fields(data, issues)
    _validate_alternative_scores(data, issues)
    _validate_match_ownership(data, context, issues)
    _validate_reference_ownership(data, context, issues)
    _validate_fact_claim_links(data, context, issues)
    if phase in {"bet_form", "form_bet", "bet_debate", "debate_bet", "bet_vote", "vote_bet"}:
        _validate_bet(data, phase, context, issues)
    return tuple(issues)


def validate_provider_result(
    payload: Mapping[str, Any] | BaseModel,
    *,
    phase: str,
    context: ResultValidationContext,
) -> dict[str, Any]:
    """Validate all deterministic business rules before persistence.

    The validated mapping is returned for transaction code to hash and persist.
    Any failure is terminal for this phase result; callers must not salvage a
    vote or score from free text.
    """

    data = dict(_as_mapping(payload))
    issues = collect_validation_issues(data, phase=phase, context=context)
    if issues:
        raise ResultValidationError(issues)
    return data


@dataclass(frozen=True, slots=True)
class ResultValidator:
    context: ResultValidationContext

    def validate(self, payload: Mapping[str, Any] | BaseModel, *, phase: str) -> dict[str, Any]:
        return validate_provider_result(payload, phase=phase, context=self.context)


def _validate_score_fields(data: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    score = data.get("full_time_score")
    direction = data.get("direction")
    if score is None or direction is None:
        return
    if not isinstance(score, Mapping):
        issues.append(ValidationIssue("invalid_score", "full_time_score", "must be an object"))
        return
    try:
        derived = score_direction(score)
    except ValueError as exc:
        issues.append(ValidationIssue("invalid_score", "full_time_score", str(exc)))
        return
    if direction != derived:
        issues.append(
            ValidationIssue(
                "direction_mismatch",
                "direction",
                f"declared {direction!r}, but full_time_score derives {derived!r}",
            )
        )


def _validate_alternative_scores(data: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    alternatives = data.get("alternative_scores")
    if alternatives is None:
        return
    if not _is_sequence(alternatives):
        issues.append(
            ValidationIssue("invalid_alternatives", "alternative_scores", "must be an array")
        )
        return
    primary = _score_key(data.get("full_time_score"))
    seen: set[tuple[int, int]] = set()
    for index, alternative in enumerate(alternatives):
        key = _score_key(alternative)
        path = f"alternative_scores[{index}]"
        if key is None:
            issues.append(ValidationIssue("invalid_score", path, "must contain integer home/away"))
        elif key == primary:
            issues.append(
                ValidationIssue("duplicate_primary_score", path, "duplicates full_time_score")
            )
        elif key in seen:
            issues.append(
                ValidationIssue(
                    "duplicate_alternative_score", path, "duplicates another alternative"
                )
            )
        else:
            seen.add(key)


def _validate_match_ownership(
    data: Mapping[str, Any], context: ResultValidationContext, issues: list[ValidationIssue]
) -> None:
    if not context.frozen_match_ids:
        return
    for path, match_id in _values_for_key(data, "match_id"):
        if isinstance(match_id, str) and match_id not in context.frozen_match_ids:
            issues.append(
                ValidationIssue(
                    "match_outside_snapshot", path, "match is not in the frozen candidate pool"
                )
            )


def _validate_reference_ownership(
    data: Mapping[str, Any], context: ResultValidationContext, issues: list[ValidationIssue]
) -> None:
    _validate_id_arrays(
        data,
        "source_record_ids",
        context.frozen_source_record_ids,
        "source_outside_snapshot",
        issues,
    )
    _validate_id_arrays(
        data,
        "verified_fact_claim_ids",
        context.verified_fact_claim_ids,
        "fact_claim_not_verified",
        issues,
    )
    _validate_id_arrays(
        data,
        "offer_option_ids",
        context.frozen_offer_option_ids,
        "offer_outside_snapshot",
        issues,
    )


def _validate_fact_claim_links(
    data: Mapping[str, Any], context: ResultValidationContext, issues: list[ValidationIssue]
) -> None:
    declared = {
        claim.get("claim_id")
        for claims in _objects_for_key(data, "fact_claims")
        for claim in claims
        if isinstance(claim.get("claim_id"), str)
    }
    for arguments in _objects_for_key(data, "arguments"):
        for index, argument in enumerate(arguments):
            ids = argument.get("fact_claim_ids", ())
            if not _is_sequence(ids):
                continue
            for claim_id in ids:
                if claim_id not in declared and claim_id not in context.verified_fact_claim_ids:
                    issues.append(
                        ValidationIssue(
                            "unknown_fact_claim",
                            f"arguments[{index}].fact_claim_ids",
                            f"claim {claim_id!r} is neither declared nor verified",
                        )
                    )
    unverified_public = context.public_fact_claim_ids - context.verified_fact_claim_ids
    for claim_id in sorted(unverified_public):
        issues.append(
            ValidationIssue(
                "unverified_public_fact",
                "public_reason",
                f"fact claim {claim_id!r} is not verified and cannot be published",
            )
        )


def _validate_bet(
    data: Mapping[str, Any],
    phase: str,
    context: ResultValidationContext,
    issues: list[ValidationIssue],
) -> None:
    decision = data.get("decision")
    plan = data.get("plan")
    if decision == "no_bet":
        if plan is not None:
            issues.append(ValidationIssue("invalid_no_bet", "plan", "no_bet requires plan=null"))
        if "no_bet_reason" in data and not _nonempty(data.get("no_bet_reason")):
            issues.append(ValidationIssue("invalid_no_bet", "no_bet_reason", "must be non-empty"))
        return
    if decision != "bet":
        return
    candidate_id = data.get("candidate_id")
    if phase in {"bet_vote", "vote_bet"}:
        if (
            not isinstance(candidate_id, str)
            or candidate_id not in context.ticket_validated_candidate_ids
        ):
            issues.append(
                ValidationIssue(
                    "ticket_not_validated",
                    "candidate_id",
                    "final bet vote must reference a calculate_ticket-validated candidate",
                )
            )
        return
    if not isinstance(plan, Mapping):
        issues.append(ValidationIssue("invalid_bet", "plan", "bet requires a plan"))
        return
    legs = plan.get("legs")
    if not _is_sequence(legs):
        issues.append(ValidationIssue("invalid_bet", "plan.legs", "must be an array"))
        return
    matches: set[str] = set()
    for index, leg in enumerate(cast(Sequence[Any], legs)):
        if not isinstance(leg, Mapping):
            continue
        match_id = leg.get("match_id")
        if isinstance(match_id, str):
            if match_id in matches:
                issues.append(
                    ValidationIssue(
                        "multiple_plays_same_match",
                        f"plan.legs[{index}].match_id",
                        "a plan may use only one play per match",
                    )
                )
            matches.add(match_id)
        if leg.get("play") == "hafu":
            _validate_hafu_leg(leg, index, data, context, issues)
    ticket_ok = context.ticket_validation_passed or (
        isinstance(candidate_id, str) and candidate_id in context.ticket_validated_candidate_ids
    )
    if not ticket_ok:
        issues.append(
            ValidationIssue(
                "ticket_not_validated",
                "plan",
                "calculate_ticket must pass before debate or final candidate admission",
            )
        )


def _validate_hafu_leg(
    leg: Mapping[str, Any],
    index: int,
    data: Mapping[str, Any],
    context: ResultValidationContext,
    issues: list[ValidationIssue],
) -> None:
    match_id = leg.get("match_id")
    match_scores = context.match_scores.get(match_id, {}) if isinstance(match_id, str) else {}
    half = data.get("half_time_score", match_scores.get("half_time_score"))
    full = data.get("full_time_score", match_scores.get("full_time_score"))
    if not isinstance(half, Mapping) or not isinstance(full, Mapping):
        return
    try:
        expected = f"{score_direction(half)}-{score_direction(full)}"
    except ValueError:
        return
    aliases = _hafu_aliases(expected)
    for option_id in _string_items(leg.get("offer_option_ids")):
        selection = context.offer_selections.get(option_id)
        if selection is not None and selection.casefold().replace("_", "-") not in aliases:
            issues.append(
                ValidationIssue(
                    "hafu_score_mismatch",
                    f"plan.legs[{index}].offer_option_ids",
                    f"selection {selection!r} does not match half/full score ({expected})",
                )
            )


def _hafu_aliases(value: str) -> set[str]:
    chinese = {"home": "胜", "draw": "平", "away": "负"}
    first, second = value.split("-")
    return {
        value,
        value.replace("-", "/"),
        f"{chinese[first]}{chinese[second]}".casefold(),
    }


def _validate_id_arrays(
    data: Mapping[str, Any],
    key: str,
    allowed: frozenset[str],
    code: str,
    issues: list[ValidationIssue],
) -> None:
    for path, value in _values_for_key(data, key):
        if not _is_sequence(value):
            issues.append(ValidationIssue("invalid_reference_list", path, "must be an array"))
            continue
        for item in value:
            if isinstance(item, str) and item not in allowed:
                issues.append(
                    ValidationIssue(
                        code, path, f"reference {item!r} does not belong to the frozen snapshot"
                    )
                )


def _values_for_key(value: Any, key: str, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}" if path else str(child_key)
            if child_key == key:
                yield child_path, child
            yield from _values_for_key(child, key, child_path)
    elif _is_sequence(value):
        for index, child in enumerate(value):
            yield from _values_for_key(child, key, f"{path}[{index}]")


def _objects_for_key(data: Mapping[str, Any], key: str) -> Iterable[list[Mapping[str, Any]]]:
    for _, value in _values_for_key(data, key):
        if _is_sequence(value):
            yield [item for item in value if isinstance(item, Mapping)]


def _score_key(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, Mapping):
        return None
    home, away = value.get("home"), value.get("away")
    if not isinstance(home, int) or isinstance(home, bool):
        return None
    if not isinstance(away, int) or isinstance(away, bool):
        return None
    return home, away


def _string_items(value: Any) -> tuple[str, ...]:
    if not _is_sequence(value):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _as_mapping(value: Mapping[str, Any] | BaseModel) -> Mapping[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
