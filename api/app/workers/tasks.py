from __future__ import annotations

import asyncio
import inspect
import json
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, cast

from celery import Task

from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.tasks.run_roundtable_lifecycle",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_roundtable_lifecycle(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the durable job and enqueue its first provider phase idempotently.

    The database function owns quorum checks, Sporttery-scope checks, state
    transitions and phase/outbox creation. Redelivery is safe.
    """

    job_id = str(payload.get("job_id", "")).strip()
    event_type = str(payload.get("event_type", "")).strip()
    event_payload = payload.get("payload", {})
    if not job_id or not event_type or not isinstance(event_payload, Mapping):
        raise ValueError("invalid roundtable lifecycle payload")
    database_url = os.getenv("DATABASE_URL_ALEA_WORKER")
    if not database_url:
        raise RuntimeError("DATABASE_URL_ALEA_WORKER is required")
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select alea_worker_initialize_roundtable(%s::uuid, %s, %s::jsonb) as value",
                (job_id, event_type, json.dumps(dict(event_payload), ensure_ascii=False)),
            )
            row = cursor.fetchone()
    initialization = row["value"] if row else None
    status_value = (
        str(initialization.get("status", "succeeded"))
        if isinstance(initialization, Mapping)
        else "succeeded"
    )
    return {
        "status": status_value,
        "job_id": job_id,
        "initialization": initialization,
    }


class RoundtablePhase(StrEnum):
    NOMINATE_MATCHES = "nominate_matches"
    SELECTION_DEBATE = "selection_debate"
    VOTE_MATCHES = "vote_matches"
    PREDICT_SCORE = "predict_score"
    DEBATE_RESPONSE = "debate_response"
    VOTE_SCORE = "vote_score"
    FORM_BET = "form_bet"
    DEBATE_BET = "debate_bet"
    VOTE_BET = "vote_bet"
    REVIEW_PREDICTION = "review_prediction"
    REVIEW_METHODOLOGY = "review_methodology"


@dataclass(frozen=True, slots=True)
class PhaseCommand:
    job_id: str
    match_id: str | None
    phase: RoundtablePhase
    round_number: int
    instance_id: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.instance_id.strip():
            raise ValueError("job_id and instance_id must not be empty")
        if self.round_number < 0:
            raise ValueError("round_number must be non-negative")

    @property
    def business_idempotency_key(self) -> str:
        return build_phase_idempotency_key(
            job_id=self.job_id,
            match_id=self.match_id,
            phase=self.phase,
            round_number=self.round_number,
            instance_id=self.instance_id,
        )

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any], *, forced_phase: RoundtablePhase | None = None
    ) -> PhaseCommand:
        phase = forced_phase or RoundtablePhase(str(payload["phase"]))
        match_id = payload.get("match_id")
        body = payload.get("payload", {})
        if not isinstance(body, Mapping):
            raise ValueError("payload.payload must be an object")
        return cls(
            job_id=str(payload["job_id"]),
            match_id=str(match_id) if match_id is not None else None,
            phase=phase,
            round_number=int(payload.get("round_number", 0)),
            instance_id=str(payload["instance_id"]),
            payload=dict(body),
        )


@dataclass(frozen=True, slots=True)
class PhaseOutcome:
    result_id: str
    payload_hash: str
    provider_request_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    usage: Mapping[str, Any] | None = None


class PhaseExecutionStore(Protocol):
    async def claim(self, command: PhaseCommand, *, celery_task_id: str | None) -> bool: ...

    async def commit_success(self, command: PhaseCommand, outcome: PhaseOutcome) -> None:
        """Atomically insert result and immutable audit root if this is the first success."""
        ...

    async def append_failure(
        self, command: PhaseCommand, *, code: str, detail_redacted: str
    ) -> None: ...


class PhaseHandler(Protocol):
    async def __call__(self, command: PhaseCommand) -> PhaseOutcome: ...


@dataclass(slots=True)
class PhaseExecutor:
    store: PhaseExecutionStore
    handler: PhaseHandler

    async def execute(self, command: PhaseCommand, *, celery_task_id: str | None) -> dict[str, Any]:
        if not await self.store.claim(command, celery_task_id=celery_task_id):
            return {
                "status": "duplicate",
                "business_idempotency_key": command.business_idempotency_key,
            }
        try:
            outcome = await self.handler(command)
            await self.store.commit_success(command, outcome)
        except Exception as exc:
            await self.store.append_failure(
                command,
                code=type(exc).__name__,
                detail_redacted="phase execution failed",
            )
            raise
        return {
            "status": "succeeded",
            "business_idempotency_key": command.business_idempotency_key,
            "result_id": outcome.result_id,
            "payload_hash": outcome.payload_hash,
        }


_executor: PhaseExecutor | None = None


def configure_phase_executor(executor: PhaseExecutor) -> None:
    global _executor
    _executor = executor


def build_phase_idempotency_key(
    *,
    job_id: str,
    match_id: str | None,
    phase: RoundtablePhase | str,
    round_number: int,
    instance_id: str,
) -> str:
    if round_number < 0:
        raise ValueError("round_number must be non-negative")
    return f"{job_id}:{match_id or '-'}:{RoundtablePhase(phase).value}:{round_number}:{instance_id}"


@celery_app.task(
    bind=True,
    name="app.workers.tasks.run_provider_phase",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_provider_phase(self: Task[Any, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    return _run_command(PhaseCommand.from_payload(payload), task_id=self.request.id)


def _run_command(command: PhaseCommand, *, task_id: str | None) -> dict[str, Any]:
    global _executor
    if _executor is None:
        from app.workers.executor_bootstrap import resolve_phase_executor

        _executor = cast(PhaseExecutor, resolve_phase_executor())
    return _run_awaitable(_executor.execute(command, celery_task_id=task_id))


def _phase_task(phase: RoundtablePhase) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    def task(payload: Mapping[str, Any]) -> dict[str, Any]:
        command = PhaseCommand.from_payload(payload, forced_phase=phase)
        current_task = getattr(task, "request", None)
        return _run_command(command, task_id=getattr(current_task, "id", None))

    task.__name__ = f"run_{phase.value}"
    return task


def _register_phase_task(phase: RoundtablePhase) -> Any:
    return celery_app.task(
        name=f"app.workers.tasks.run_{phase.value}",
        acks_late=True,
        reject_on_worker_lost=True,
    )(_phase_task(phase))


run_nominate_matches = _register_phase_task(RoundtablePhase.NOMINATE_MATCHES)
run_selection_debate = _register_phase_task(RoundtablePhase.SELECTION_DEBATE)
run_vote_matches = _register_phase_task(RoundtablePhase.VOTE_MATCHES)
run_predict_score = _register_phase_task(RoundtablePhase.PREDICT_SCORE)
run_debate_response = _register_phase_task(RoundtablePhase.DEBATE_RESPONSE)
run_vote_score = _register_phase_task(RoundtablePhase.VOTE_SCORE)
run_form_bet = _register_phase_task(RoundtablePhase.FORM_BET)
run_debate_bet = _register_phase_task(RoundtablePhase.DEBATE_BET)
run_vote_bet = _register_phase_task(RoundtablePhase.VOTE_BET)
run_review_prediction = _register_phase_task(RoundtablePhase.REVIEW_PREDICTION)
run_review_methodology = _register_phase_task(RoundtablePhase.REVIEW_METHODOLOGY)


@celery_app.task(
    name="app.workers.tasks.run_settlement",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_settlement(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Commit one confirmed result through the worker-only settlement RPC."""

    prediction_id = str(payload.get("notarized_prediction_id", "")).strip()
    result_version_id = str(payload.get("result_version_id", "")).strip()
    if not prediction_id or not result_version_id:
        raise ValueError("settlement payload requires prediction and result IDs")
    database_url = os.getenv("DATABASE_URL_ALEA_WORKER")
    if not database_url:
        raise RuntimeError("DATABASE_URL_ALEA_WORKER is required")
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select public.settle_notarized_prediction(%s::uuid, %s::uuid) as value",
                (prediction_id, result_version_id),
            )
            row = cursor.fetchone()
    value = row["value"] if row else None
    if not isinstance(value, Mapping):
        raise RuntimeError("settlement RPC returned an invalid result")
    return dict(value)


@celery_app.task(
    name="app.workers.tasks.run_ranking_recompute",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_ranking_recompute(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Acknowledge the durable ranking invalidation after facts are committed.

    Rankings are computed from immutable ``ranking_facts`` at read time. The
    outbox event is still consumed so an unavailable optional cache cannot leave
    a permanently pending business event.
    """

    settlement_run_id = str(payload.get("settlement_run_id", "")).strip()
    if not settlement_run_id:
        raise ValueError("ranking recompute payload requires settlement_run_id")
    return {"status": "acknowledged", "settlement_run_id": settlement_run_id}


@celery_app.task(
    name="app.workers.tasks.run_postmatch_review",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_postmatch_review(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Acknowledge the post-match review request for the review executor.

    The review Provider phase is separately scheduled once its frozen context is
    assembled; this durable handoff prevents the settlement outbox from being
    treated as an unhandled topic.
    """

    settlement_run_id = str(payload.get("settlement_run_id", "")).strip()
    prediction_id = str(payload.get("notarized_prediction_id", "")).strip()
    if not settlement_run_id or not prediction_id:
        raise ValueError("postmatch review payload requires settlement identifiers")
    return {
        "status": "deferred_to_review_executor",
        "settlement_run_id": settlement_run_id,
        "notarized_prediction_id": prediction_id,
    }


def _run_awaitable(awaitable: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:

        async def wait_for_result() -> dict[str, Any]:
            return await awaitable

        return asyncio.run(wait_for_result())
    if inspect.iscoroutine(awaitable):
        awaitable.close()
    raise RuntimeError("Celery phase tasks must run outside an active asyncio event loop")
