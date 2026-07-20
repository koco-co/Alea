from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from celery import Celery

from app.workers.celery_app import celery_app


TOPIC_TASKS: Mapping[str, str] = {
    "roundtable.phase": "app.workers.tasks.run_provider_phase",
    "roundtable.nominate_matches": "app.workers.tasks.run_nominate_matches",
    "roundtable.selection_debate": "app.workers.tasks.run_selection_debate",
    "roundtable.vote_matches": "app.workers.tasks.run_vote_matches",
    "roundtable.predict_score": "app.workers.tasks.run_predict_score",
    "roundtable.debate_response": "app.workers.tasks.run_debate_response",
    "roundtable.vote_score": "app.workers.tasks.run_vote_score",
    "roundtable.form_bet": "app.workers.tasks.run_form_bet",
    "roundtable.debate_bet": "app.workers.tasks.run_debate_bet",
    "roundtable.vote_bet": "app.workers.tasks.run_vote_bet",
    "roundtable.review_prediction": "app.workers.tasks.run_review_prediction",
    "roundtable.review_methodology": "app.workers.tasks.run_review_methodology",
}


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    event_id: str
    topic: str
    business_idempotency_key: str
    payload: Mapping[str, Any]
    attempt: int


@dataclass(frozen=True, slots=True)
class DispatchStats:
    claimed: int = 0
    published: int = 0
    failed: int = 0


class OutboxRepository(Protocol):
    async def claim_batch(
        self,
        *,
        lease_owner: str,
        limit: int,
        lease_seconds: int,
        now: datetime,
    ) -> Sequence[OutboxEvent]:
        """Claim due pending/failed/expired rows using FOR UPDATE SKIP LOCKED."""
        ...

    async def mark_published(
        self, event_id: str, *, broker_message_id: str, published_at: datetime
    ) -> None: ...

    async def mark_failed(
        self, event_id: str, *, error_code: str, detail_redacted: str, dead: bool
    ) -> None: ...


class RecoveryRepository(Protocol):
    async def recover_expired_phase_leases(self, *, now: datetime, limit: int) -> int: ...

    async def enqueue_unfinished_phases(self, *, now: datetime, limit: int) -> int: ...

    async def recover_expired_outbox_leases(self, *, now: datetime, limit: int) -> int: ...


class CeleryPublisher:
    def __init__(self, app: Celery = celery_app) -> None:
        self.app = app

    def publish(self, event: OutboxEvent) -> str:
        task_name = TOPIC_TASKS.get(event.topic)
        if task_name is None:
            raise ValueError(f"outbox topic is not dispatchable: {event.topic}")
        message_id = str(uuid5(NAMESPACE_URL, event.business_idempotency_key))
        self.app.send_task(
            task_name,
            args=[dict(event.payload)],
            task_id=message_id,
            headers={"business_idempotency_key": event.business_idempotency_key},
        )
        return message_id


async def dispatch_once(
    repository: OutboxRepository,
    *,
    lease_owner: str,
    publisher: CeleryPublisher | None = None,
    limit: int = 100,
    lease_seconds: int = 30,
    max_attempts: int = 5,
    now: datetime | None = None,
) -> DispatchStats:
    timestamp = _utc(now)
    events = await repository.claim_batch(
        lease_owner=lease_owner,
        limit=limit,
        lease_seconds=lease_seconds,
        now=timestamp,
    )
    sent = 0
    failed = 0
    broker = publisher or CeleryPublisher()
    for event in events:
        try:
            message_id = broker.publish(event)
        except Exception as exc:
            failed += 1
            await repository.mark_failed(
                event.event_id,
                error_code=type(exc).__name__,
                detail_redacted="broker publish failed",
                dead=event.attempt >= max_attempts,
            )
        else:
            sent += 1
            await repository.mark_published(
                event.event_id,
                broker_message_id=message_id,
                published_at=timestamp,
            )
    return DispatchStats(claimed=len(events), published=sent, failed=failed)


async def scan_recovery_once(
    repository: RecoveryRepository,
    *,
    limit: int = 100,
    now: datetime | None = None,
) -> dict[str, int]:
    """Recover expired leases, unfinished phases, and unpublished outbox rows."""

    timestamp = _utc(now)
    phase_leases = await repository.recover_expired_phase_leases(now=timestamp, limit=limit)
    unfinished = await repository.enqueue_unfinished_phases(now=timestamp, limit=limit)
    outbox_leases = await repository.recover_expired_outbox_leases(now=timestamp, limit=limit)
    return {
        "expired_phase_leases": phase_leases,
        "unfinished_phases": unfinished,
        "expired_outbox_leases": outbox_leases,
    }


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)

