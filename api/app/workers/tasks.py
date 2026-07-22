from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum
from itertools import combinations, product
from re import search
from typing import Any, Protocol, cast
from uuid import uuid4

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
    result = dict(value)
    settlement_run_id = str(result.get("settlement_run_id", "")).strip()
    if not settlement_run_id:
        raise RuntimeError("settlement RPC returned no settlement run")
    result["position_settlements"] = _settle_position_batch(
        database_url,
        settlement_run_id=settlement_run_id,
    )
    return result


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
    """Freeze a post-match context and enqueue one real review phase per instance."""

    settlement_run_id = str(payload.get("settlement_run_id", "")).strip()
    prediction_id = str(payload.get("notarized_prediction_id", "")).strip()
    if not settlement_run_id or not prediction_id:
        raise ValueError("postmatch review payload requires settlement identifiers")
    database_url = os.getenv("DATABASE_URL_ALEA_WORKER")
    if not database_url:
        raise RuntimeError("DATABASE_URL_ALEA_WORKER is required")
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select sr.id as settlement_run_id, sr.result_version_id,
                       sr.notarized_prediction_id, n.job_id, n.match_run_id,
                       mrun.match_id,
                       n.payload as prediction_payload,
                       jsonb_build_object(
                         'match_id', mr.match_id,
                         'home_score', mr.home_score,
                         'away_score', mr.away_score,
                         'half_home_score', mr.half_home_score,
                         'half_away_score', mr.half_away_score,
                         'result_version', mr.result_version
                       ) as result_payload
                from public.settlement_runs sr
                join public.notarized_predictions n on n.id=sr.notarized_prediction_id
                join public.roundtable_match_runs mrun on mrun.id=n.match_run_id
                join public.match_results mr on mr.id=sr.result_version_id
                where sr.id=%s::uuid and sr.notarized_prediction_id=%s::uuid
                for update of sr
                """,
                (settlement_run_id, prediction_id),
            )
            run = cursor.fetchone()
            if run is None:
                raise ValueError("postmatch settlement run not found")
            cursor.execute(
                """
                select id, state, context_id, phase_count
                from public.settlement_reviews
                where settlement_run_id=%s::uuid
                for update
                """,
                (settlement_run_id,),
            )
            existing_review = cursor.fetchone()
            if existing_review is not None and existing_review["state"] == "completed":
                return {
                    "status": "completed",
                    "settlement_run_id": settlement_run_id,
                    "notarized_prediction_id": prediction_id,
                    "phase_count": existing_review["phase_count"],
                    "idempotent_replay": True,
                }
            if existing_review is not None and existing_review["state"] in {"scheduled", "running"}:
                return {
                    "status": existing_review["state"],
                    "settlement_run_id": settlement_run_id,
                    "notarized_prediction_id": prediction_id,
                    "context_id": str(existing_review["context_id"]),
                    "phase_count": existing_review["phase_count"],
                    "idempotent_replay": True,
                }
            cursor.execute(
                """
                select ai_instance_id, provider_family, frozen_config
                from public.roundtable_participants
                where job_id=%s::uuid
                order by codename
                """,
                (str(run["job_id"]),),
            )
            participants = cursor.fetchall()
            if len(participants) < 3 or len({row["provider_family"] for row in participants}) < 2:
                raise ValueError("postmatch review requires quorum")
            cursor.execute(
                """
                select ai_instance_id, phase, payload
                from public.roundtable_results
                where job_id=%s::uuid and (match_run_id=%s::uuid or phase='bet_vote')
                  and phase in ('score_vote', 'bet_vote')
                order by created_at, id
                """,
                (str(run["job_id"]), str(run["match_run_id"])),
            )
            prior_results = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select ai_instance_id, exact_score_hit, direction_hit,
                       total_goals_hit, half_full_hit
                from public.ranking_facts
                where settlement_run_id=%s::uuid
                order by ai_instance_id
                """,
                (settlement_run_id,),
            )
            ranking_facts = [dict(row) for row in cursor.fetchall()]
            context_payload = {
                "settlement_run_id": settlement_run_id,
                "notarized_prediction_id": prediction_id,
                "result_version_id": str(run["result_version_id"]),
                "job_id": str(run["job_id"]),
                "match_run_id": str(run["match_run_id"]),
                "prediction": run["prediction_payload"],
                "result": run["result_payload"],
                "prior_results": prior_results,
                "ranking_facts": ranking_facts,
            }
            serialized = json.dumps(
                context_payload,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
            context_hash = hashlib.sha256(serialized.encode()).hexdigest()
            context_id = existing_review["context_id"] if existing_review is not None else uuid4()
            cursor.execute(
                """
                insert into public.postmatch_review_contexts
                  (id, settlement_run_id, notarized_prediction_id, result_version_id, payload, payload_hash)
                values (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::jsonb, %s)
                on conflict (settlement_run_id) do nothing
                """,
                (
                    str(context_id),
                    settlement_run_id,
                    prediction_id,
                    str(run["result_version_id"]),
                    serialized,
                    context_hash,
                ),
            )
            cursor.execute(
                "select id from public.postmatch_review_contexts where settlement_run_id=%s::uuid",
                (settlement_run_id,),
            )
            context_row = cursor.fetchone()
            if context_row is None:
                raise RuntimeError("post-match review context was not persisted")
            context_id = context_row["id"]
            cursor.execute(
                """
                insert into public.settlement_reviews
                  (settlement_run_id, context_id, state, phase_count)
                values (%s::uuid, %s::uuid, 'scheduled', %s)
                on conflict (settlement_run_id) do update
                set state=case when settlement_reviews.state='completed'
                               then settlement_reviews.state else 'scheduled' end,
                    context_id=excluded.context_id,
                    phase_count=excluded.phase_count,
                    error_code=null
                """,
                (settlement_run_id, str(context_id), len(participants)),
            )
            phase_count = 0
            for participant in participants:
                instance_id = str(participant["ai_instance_id"])
                match_id = str(run["match_id"])
                key = f"{run['job_id']}:{match_id}:review_prediction:0:{instance_id}"
                cursor.execute(
                    """
                    insert into public.roundtable_phase_runs
                      (job_id, match_run_id, ai_instance_id, phase, round_number,
                       attempt, business_idempotency_key, status)
                    values (%s::uuid, null, %s::uuid, 'review_prediction', 0, 1, %s, 'pending')
                    on conflict (business_idempotency_key) do nothing
                    returning id
                    """,
                    (str(run["job_id"]), instance_id, key),
                )
                phase_run = cursor.fetchone()
                if phase_run is None:
                    continue
                phase_run_id = str(phase_run["id"])
                outbox_payload = {
                    "job_id": str(run["job_id"]),
                    "match_id": match_id,
                    "phase": "review_prediction",
                    "round_number": 0,
                    "instance_id": instance_id,
                    "payload": {
                        "phase_run_id": phase_run_id,
                        "match_run_id": str(run["match_run_id"]),
                        "postmatch_review_context_id": str(context_id),
                        "participant_config": participant["frozen_config"],
                    },
                }
                cursor.execute(
                    """
                    insert into public.outbox_events(topic, business_idempotency_key, payload)
                    values ('roundtable.review_prediction', %s, %s::jsonb)
                    on conflict (business_idempotency_key) do nothing
                    """,
                    ("phase:" + key, json.dumps(outbox_payload, ensure_ascii=False)),
                )
                phase_count += 1
            connection.commit()
    return {
        "status": "scheduled",
        "settlement_run_id": settlement_run_id,
        "notarized_prediction_id": prediction_id,
        "context_id": str(context_id),
        "phase_count": phase_count,
        "idempotent_replay": False,
    }


def _settle_position_batch(database_url: str, *, settlement_run_id: str) -> list[dict[str, Any]]:
    """Evaluate frozen tickets and commit their money effects through one RPC per position."""

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select sp.id, sp.owner_type, sp.owner_id, sp.decision, sp.stake,
                       sr.result_version_id, n.job_id, n.match_run_id,
                       mr.match_id, mr.home_score, mr.away_score,
                       mr.half_home_score, mr.half_away_score
                from public.settlement_positions sp
                join public.settlement_runs sr on sr.id=sp.settlement_run_id
                join public.notarized_predictions n on n.id=sr.notarized_prediction_id
                join public.match_results mr on mr.id=sr.result_version_id
                where sp.settlement_run_id=%s::uuid
                order by sp.owner_type, sp.owner_id
                """,
                (settlement_run_id,),
            )
            positions = cursor.fetchall()
            if not positions:
                raise ValueError("settlement produced no positions")
            job_id = str(positions[0]["job_id"])
            match_id = str(positions[0]["match_id"])
            result: dict[str, int | str] = {
                "match_id": match_id,
                "home_score": int(positions[0]["home_score"]),
                "away_score": int(positions[0]["away_score"]),
                "half_home_score": int(positions[0]["half_home_score"]),
                "half_away_score": int(positions[0]["half_away_score"]),
            }
            cursor.execute(
                """
                select play_type, values
                from public.match_odds_snapshots
                where match_id=%s::uuid
                order by observed_at desc
                """,
                (match_id,),
            )
            odds = _flatten_frozen_odds(cursor.fetchall())
            cursor.execute(
                """
                select ai_instance_id, payload
                from public.roundtable_results
                where job_id=%s::uuid and phase in ('bet_vote', 'form_bet', 'debate_bet')
                order by created_at, id
                """,
                (job_id,),
            )
            bet_results = [dict(row) for row in cursor.fetchall()]
            outcomes: list[dict[str, Any]] = []
            for position in positions:
                position_id = str(position["id"])
                if position["decision"] == "no_bet":
                    state, returned = "settled_refund", Decimal("0")
                    plan = None
                else:
                    plan = _resolve_frozen_plan(position, bet_results)
                    if plan is None:
                        raise ValueError(f"bet position {position_id} has no frozen plan")
                    state, returned = _evaluate_frozen_ticket(
                        plan, Decimal(str(position["stake"])), result, odds
                    )
                    serialized_plan = json.dumps(
                        plan, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
                    )
                    cursor.execute(
                        """
                        insert into public.settlement_position_plans
                          (position_id, settlement_run_id, plan, payload_hash)
                        values (%s::uuid, %s::uuid, %s::jsonb, %s)
                        on conflict (position_id) do nothing
                        """,
                        (
                            position_id,
                            settlement_run_id,
                            serialized_plan,
                            hashlib.sha256(serialized_plan.encode()).hexdigest(),
                        ),
                    )
                cursor.execute(
                    """
                    select public.apply_settlement_position(%s::uuid, %s, %s::numeric) as value
                    """,
                    (position_id, state, str(returned)),
                )
                applied_row = cursor.fetchone()
                if applied_row is None:
                    raise RuntimeError("settlement position RPC returned no result")
                applied = applied_row["value"]
                outcomes.append(
                    {
                        "position_id": position_id,
                        "state": state,
                        "returned_amount": str(returned),
                        "applied": applied,
                    }
                )
            connection.commit()
    return outcomes


def _resolve_frozen_plan(
    position: Mapping[str, Any], results: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    owner_id = str(position["owner_id"])
    candidates: list[Mapping[str, Any]] = []
    for row in results:
        if position["owner_type"] == "ai_instance" and str(row["ai_instance_id"]) != owner_id:
            continue
        payload = row["payload"]
        if not isinstance(payload, Mapping) or payload.get("decision") != "bet":
            continue
        plan = payload.get("plan")
        if isinstance(plan, Mapping):
            candidates.append(plan)
    return candidates[0] if candidates else None


def _flatten_frozen_odds(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    flattened: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        values = row["values"]
        if isinstance(values, Mapping):
            values = values.get("options", values)
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if not isinstance(value, Mapping):
                continue
            option_id = value.get("offer_option_id") or value.get("id")
            if isinstance(option_id, str) and option_id not in flattened:
                flattened[option_id] = {
                    "play": str(value.get("play") or row["play_type"]),
                    "selection": str(value.get("selection") or value.get("label") or ""),
                    "fixed_odds": value.get("fixed_odds"),
                }
    return flattened


def _evaluate_frozen_ticket(
    plan: Mapping[str, Any],
    stake: Decimal,
    result: Mapping[str, int | str],
    odds: Mapping[str, Mapping[str, Any]],
) -> tuple[str, Decimal]:
    from app.calculators.sporttery_calc import PASS_TYPE_COMPONENT_SIZES

    legs = plan.get("legs")
    pass_types = plan.get("pass_types")
    if not isinstance(legs, list) or not legs or not isinstance(pass_types, list) or not pass_types:
        raise ValueError("frozen bet plan is incomplete")
    choices: list[list[tuple[Decimal, bool]]] = []
    for leg in legs:
        if not isinstance(leg, Mapping) or not isinstance(leg.get("offer_option_ids"), list):
            raise ValueError("frozen bet leg is incomplete")
        if str(leg.get("match_id")) != str(result["match_id"]):
            raise ValueError("settlement result does not cover every bet leg")
        leg_choices: list[tuple[Decimal, bool]] = []
        for option_id in leg["offer_option_ids"]:
            option = odds.get(str(option_id))
            if option is None or option["fixed_odds"] is None:
                raise ValueError(f"frozen odds missing for {option_id}")
            leg_choices.append(
                (
                    Decimal(str(option["fixed_odds"])),
                    _selection_hit(
                        str(leg.get("play")),
                        str(option["selection"]),
                        result,
                    ),
                )
            )
        if not leg_choices:
            raise ValueError("frozen bet leg has no options")
        choices.append(leg_choices)

    expanded_lines = 0
    for pass_type in pass_types:
        components = PASS_TYPE_COMPONENT_SIZES.get(str(pass_type))
        if not components:
            raise ValueError(f"unsupported settlement pass type {pass_type}")
        match_count = int(str(pass_type).split("x", 1)[0])
        if match_count != len(legs):
            raise ValueError("settlement currently requires a complete frozen leg set")
        for component_size in components:
            for indexes in combinations(range(len(legs)), component_size):
                expanded_lines += _choice_count([choices[index] for index in indexes])
    if expanded_lines <= 0:
        raise ValueError("frozen ticket expanded to no lines")
    share = stake / Decimal(expanded_lines)
    returned = Decimal("0")
    for pass_type in pass_types:
        components = PASS_TYPE_COMPONENT_SIZES[str(pass_type)]
        for component_size in components:
            for indexes in combinations(range(len(legs)), component_size):
                for selected in product(*(choices[index] for index in indexes)):
                    if all(hit for _, hit in selected):
                        odds_product = Decimal("1")
                        for fixed_odds, _ in selected:
                            odds_product *= fixed_odds
                        returned += share * odds_product
    returned = returned.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return ("settled_hit" if returned > 0 else "settled_miss"), returned


def _choice_count(choices: list[list[tuple[Decimal, bool]]]) -> int:
    count = 1
    for options in choices:
        count *= len(options)
    return count


def _selection_hit(play: str, selection: str, result: Mapping[str, int | str]) -> bool:
    normalized = selection.strip().casefold().replace("：", ":")
    full_home = int(result["home_score"])
    full_away = int(result["away_score"])
    half_home = int(result["half_home_score"])
    half_away = int(result["half_away_score"])
    if play in {"had", "hhad"}:
        direction = _direction(full_home, full_away)
        return _normalize_direction(normalized) == direction
    if play == "crs":
        match = search(r"(\d+)\s*[-:比]\s*(\d+)", normalized)
        return bool(match and int(match.group(1)) == full_home and int(match.group(2)) == full_away)
    if play == "ttg":
        match = search(r"\d+", normalized)
        if not match:
            return False
        total = full_home + full_away
        target = int(match.group(0))
        return total >= target if "+" in normalized else total == target
    if play == "hafu":
        chars = [_normalize_direction(item) for item in re_split_direction(normalized)]
        return (
            len(chars) == 2
            and chars[0] == _direction(half_home, half_away)
            and chars[1] == _direction(full_home, full_away)
        )
    raise ValueError(f"unsupported settlement play {play}")


def _direction(home: int, away: int) -> str:
    return "home" if home > away else "away" if home < away else "draw"


def _normalize_direction(value: str) -> str:
    if value in {"home", "主胜", "胜", "1", "h", "home win"}:
        return "home"
    if value in {"away", "客胜", "负", "2", "a", "away win"}:
        return "away"
    if value in {"draw", "平", "x", "0"}:
        return "draw"
    return value


def re_split_direction(value: str) -> list[str]:
    compact = value.replace("/", "-").replace("比", "-").replace("胜", "胜-")
    if "-" in compact:
        return [item for item in compact.split("-") if item]
    if len(compact) == 2:
        return [compact[0], compact[1]]
    return [compact]


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
