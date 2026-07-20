from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class RoundtableJobState(StrEnum):
    PENDING = "pending"

    # Prediction roundtable states.
    SELECT_NOMINATING = "select_nominating"
    SELECT_DEBATING = "select_debating"
    SELECT_VOTING = "select_voting"
    PROCESSING_MATCHES = "processing_matches"
    BET_PROPOSING = "bet_proposing"
    BET_DEBATING = "bet_debating"
    BET_VOTING = "bet_voting"
    NOTARIZING = "notarizing"

    # Methodology-review-only states.
    INDEPENDENT_REVIEWING = "independent_reviewing"
    REVIEW_DEBATING = "review_debating"
    REVIEW_VOTING = "review_voting"
    PENDING_ADMIN_CONFIRMATION = "pending_admin_confirmation"
    REVISE_AND_REVIEW = "revise_and_review"

    COMPLETED = "completed"
    NO_QUORUM = "no_quorum"
    TERMINATED = "terminated"
    FAILED = "failed"


class MatchRunState(StrEnum):
    PENDING = "pending"
    PREDICTING = "predicting"
    DEBATING = "debating"
    SCORE_VOTING = "score_voting"
    ELIGIBLE = "eligible"
    NO_QUORUM = "no_quorum"
    TERMINATED = "terminated"
    FAILED = "failed"


class RoundtableJobType(StrEnum):
    PREDICTION = "prediction"
    METHODOLOGY_REVIEW = "methodology_review"


class RoundtableMode(StrEnum):
    AUTONOMOUS = "autonomous"
    SPECIFIED = "specified"


JOB_TERMINAL_STATES = frozenset(
    {
        RoundtableJobState.COMPLETED,
        RoundtableJobState.NO_QUORUM,
        RoundtableJobState.TERMINATED,
        RoundtableJobState.FAILED,
        RoundtableJobState.REVISE_AND_REVIEW,
    }
)
MATCH_TERMINAL_STATES = frozenset(
    {
        MatchRunState.ELIGIBLE,
        MatchRunState.NO_QUORUM,
        MatchRunState.TERMINATED,
        MatchRunState.FAILED,
    }
)


PREDICTION_TRANSITIONS: Mapping[RoundtableJobState, frozenset[RoundtableJobState]] = {
    RoundtableJobState.PENDING: frozenset(
        {
            RoundtableJobState.SELECT_NOMINATING,
            RoundtableJobState.PROCESSING_MATCHES,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.SELECT_NOMINATING: frozenset(
        {
            RoundtableJobState.SELECT_DEBATING,
            RoundtableJobState.SELECT_VOTING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.SELECT_DEBATING: frozenset(
        {
            RoundtableJobState.SELECT_VOTING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.SELECT_VOTING: frozenset(
        {
            RoundtableJobState.PROCESSING_MATCHES,
            RoundtableJobState.COMPLETED,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.PROCESSING_MATCHES: frozenset(
        {
            RoundtableJobState.BET_PROPOSING,
            RoundtableJobState.COMPLETED,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.BET_PROPOSING: frozenset(
        {
            RoundtableJobState.BET_DEBATING,
            RoundtableJobState.BET_VOTING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.BET_DEBATING: frozenset(
        {
            RoundtableJobState.BET_VOTING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.BET_VOTING: frozenset(
        {
            RoundtableJobState.NOTARIZING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.NOTARIZING: frozenset(
        {RoundtableJobState.COMPLETED, RoundtableJobState.FAILED}
    ),
}

METHODOLOGY_TRANSITIONS: Mapping[RoundtableJobState, frozenset[RoundtableJobState]] = {
    RoundtableJobState.PENDING: frozenset(
        {
            RoundtableJobState.INDEPENDENT_REVIEWING,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.INDEPENDENT_REVIEWING: frozenset(
        {
            RoundtableJobState.REVIEW_DEBATING,
            RoundtableJobState.REVIEW_VOTING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.REVIEW_DEBATING: frozenset(
        {
            RoundtableJobState.REVIEW_DEBATING,
            RoundtableJobState.REVIEW_VOTING,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.REVIEW_VOTING: frozenset(
        {
            RoundtableJobState.PENDING_ADMIN_CONFIRMATION,
            RoundtableJobState.REVISE_AND_REVIEW,
            RoundtableJobState.COMPLETED,
            RoundtableJobState.NO_QUORUM,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
    RoundtableJobState.PENDING_ADMIN_CONFIRMATION: frozenset(
        {
            RoundtableJobState.COMPLETED,
            RoundtableJobState.REVISE_AND_REVIEW,
            RoundtableJobState.TERMINATED,
            RoundtableJobState.FAILED,
        }
    ),
}

MATCH_TRANSITIONS: Mapping[MatchRunState, frozenset[MatchRunState]] = {
    MatchRunState.PENDING: frozenset({MatchRunState.PREDICTING, MatchRunState.TERMINATED}),
    MatchRunState.PREDICTING: frozenset(
        {
            MatchRunState.DEBATING,
            MatchRunState.SCORE_VOTING,
            MatchRunState.NO_QUORUM,
            MatchRunState.TERMINATED,
            MatchRunState.FAILED,
        }
    ),
    MatchRunState.DEBATING: frozenset(
        {
            MatchRunState.DEBATING,
            MatchRunState.SCORE_VOTING,
            MatchRunState.NO_QUORUM,
            MatchRunState.TERMINATED,
            MatchRunState.FAILED,
        }
    ),
    MatchRunState.SCORE_VOTING: frozenset(
        {
            MatchRunState.ELIGIBLE,
            MatchRunState.NO_QUORUM,
            MatchRunState.TERMINATED,
            MatchRunState.FAILED,
        }
    ),
}

ROUNDTABLE_FREEZE_KEYS = frozenset(
    {
        "participants",
        "vendor_family",
        "S",
        "w_raw",
        "w_i",
        "provider_connection_versions",
        "model_ids",
        "generation_parameter_versions",
        "identity_prompt_version",
        "core_methodology_version",
        "phase_prompt_versions",
        "output_schema_versions",
        "tool_contract_versions",
        "sporttery_rules_version",
        "score_formula_version",
        "history_context_limits_version",
        "history_context_version_ids",
        "lesson_set_version_ids",
        "codename_seed",
        "shuffle_seed",
        "codename_map_version_id",
        "selection_scope_snapshot_id",
    }
)


class RoundtableStateError(ValueError):
    """Raised when a transition violates the domain state machine."""


class StateVersionConflict(RoundtableStateError):
    """Raised when the optimistic-lock version is stale."""


@dataclass(frozen=True, slots=True)
class MatchRun:
    match_id: str
    state: MatchRunState = MatchRunState.PENDING
    state_version: int = 0
    updated_at: datetime | None = None
    terminal_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RoundtableJob:
    job_id: str
    job_type: RoundtableJobType
    mode: RoundtableMode
    state: RoundtableJobState
    state_version: int
    frozen_refs: Mapping[str, Any]
    match_runs: tuple[MatchRun, ...]
    created_at: datetime
    updated_at: datetime
    terminal_reason: str | None = None


def create_roundtable(
    *,
    job_id: str,
    frozen_refs: Mapping[str, Any],
    job_type: RoundtableJobType | str = RoundtableJobType.PREDICTION,
    mode: RoundtableMode | str = RoundtableMode.AUTONOMOUS,
    match_ids: tuple[str, ...] = (),
    now: datetime | None = None,
) -> RoundtableJob:
    """Create a pending job after validating the atomic roundtable-start freeze.

    Persistence code must call this inside the same database transaction that writes
    participants, history/lesson versions, seeds, and the selection-scope snapshot.
    """

    if not job_id.strip():
        raise ValueError("job_id must not be empty")
    resolved_type = RoundtableJobType(job_type)
    resolved_mode = RoundtableMode(mode)
    missing = ROUNDTABLE_FREEZE_KEYS.difference(frozen_refs)
    if missing:
        raise ValueError(f"frozen_refs missing required keys: {', '.join(sorted(missing))}")
    if resolved_type is RoundtableJobType.METHODOLOGY_REVIEW:
        if "methodology_review_context_snapshot_id" not in frozen_refs:
            raise ValueError(
                "methodology_review jobs require methodology_review_context_snapshot_id"
            )
        if match_ids:
            raise ValueError("methodology_review jobs cannot contain match runs")
    if resolved_type is RoundtableJobType.PREDICTION:
        if resolved_mode is RoundtableMode.SPECIFIED and not match_ids:
            raise ValueError("specified mode requires at least one match_id")
        if len(match_ids) != len(set(match_ids)):
            raise ValueError("match_ids must be unique")

    timestamp = _utc(now)
    runs = tuple(MatchRun(match_id=match_id, updated_at=timestamp) for match_id in match_ids)
    return RoundtableJob(
        job_id=job_id,
        job_type=resolved_type,
        mode=resolved_mode,
        state=RoundtableJobState.PENDING,
        state_version=0,
        frozen_refs=_freeze(frozen_refs),
        match_runs=runs,
        created_at=timestamp,
        updated_at=timestamp,
    )


def advance_roundtable(
    job: RoundtableJob,
    target_state: RoundtableJobState | MatchRunState | str,
    *,
    expected_state_version: int,
    match_id: str | None = None,
    reason: str | None = None,
    now: datetime | None = None,
) -> RoundtableJob:
    """Advance a parent job or one child run with optimistic locking.

    The returned value is a new immutable checkpoint; callers persist it together
    with the audit event and transactional-outbox row in one transaction.
    """

    if match_id is not None:
        return _advance_match(
            job,
            match_id,
            MatchRunState(target_state),
            expected_state_version=expected_state_version,
            reason=reason,
            now=now,
        )

    if job.state_version != expected_state_version:
        raise StateVersionConflict(
            f"job {job.job_id} expected state_version {expected_state_version}, "
            f"found {job.state_version}"
        )
    target = RoundtableJobState(target_state)
    transitions = (
        PREDICTION_TRANSITIONS
        if job.job_type is RoundtableJobType.PREDICTION
        else METHODOLOGY_TRANSITIONS
    )
    allowed = transitions.get(job.state, frozenset())
    if target not in allowed:
        raise RoundtableStateError(f"illegal job transition: {job.state} -> {target}")
    _validate_parent_guard(job, target)
    terminal_reason = _terminal_reason(target, reason)
    return replace(
        job,
        state=target,
        state_version=job.state_version + 1,
        updated_at=_utc(now),
        terminal_reason=terminal_reason,
    )


def _advance_match(
    job: RoundtableJob,
    match_id: str,
    target: MatchRunState,
    *,
    expected_state_version: int,
    reason: str | None,
    now: datetime | None,
) -> RoundtableJob:
    if job.job_type is not RoundtableJobType.PREDICTION:
        raise RoundtableStateError("methodology_review jobs do not have match runs")
    try:
        index, current = next(
            (index, run) for index, run in enumerate(job.match_runs) if run.match_id == match_id
        )
    except StopIteration as exc:
        raise KeyError(f"unknown match_id: {match_id}") from exc
    if current.state_version != expected_state_version:
        raise StateVersionConflict(
            f"match {match_id} expected state_version {expected_state_version}, "
            f"found {current.state_version}"
        )
    if target not in MATCH_TRANSITIONS.get(current.state, frozenset()):
        raise RoundtableStateError(f"illegal match transition: {current.state} -> {target}")

    updated = replace(
        current,
        state=target,
        state_version=current.state_version + 1,
        updated_at=_utc(now),
        terminal_reason=_terminal_reason(target, reason),
    )
    runs = list(job.match_runs)
    runs[index] = updated
    return replace(job, match_runs=tuple(runs), updated_at=updated.updated_at or job.updated_at)


def _validate_parent_guard(job: RoundtableJob, target: RoundtableJobState) -> None:
    if job.state is not RoundtableJobState.PROCESSING_MATCHES:
        return
    if not job.match_runs:
        raise RoundtableStateError("processing_matches requires child match runs")
    if not all(run.state in MATCH_TERMINAL_STATES for run in job.match_runs):
        raise RoundtableStateError("parent must wait for every match run to reach a terminal state")
    eligible_count = sum(run.state is MatchRunState.ELIGIBLE for run in job.match_runs)
    if target is RoundtableJobState.BET_PROPOSING and eligible_count == 0:
        raise RoundtableStateError("bet_proposing requires at least one eligible match")
    if target is RoundtableJobState.NO_QUORUM and any(
        run.state is not MatchRunState.NO_QUORUM for run in job.match_runs
    ):
        raise RoundtableStateError("parent no_quorum requires all match runs to be no_quorum")
    if target is RoundtableJobState.COMPLETED and eligible_count:
        raise RoundtableStateError("eligible matches must continue to bet_proposing")


def _terminal_reason(state: StrEnum, reason: str | None) -> str | None:
    is_terminal = state in JOB_TERMINAL_STATES or state in MATCH_TERMINAL_STATES
    if state in {
        RoundtableJobState.TERMINATED,
        RoundtableJobState.FAILED,
        MatchRunState.TERMINATED,
        MatchRunState.FAILED,
    }:
        if not reason or not reason.strip():
            raise RoundtableStateError(f"{state} requires a non-empty reason")
        return reason.strip()
    return reason.strip() if is_terminal and reason and reason.strip() else None


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(child) for child in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze(child) for child in value)
    return value
