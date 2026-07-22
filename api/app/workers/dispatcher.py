from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from celery import Celery

from app.workers.celery_app import celery_app


TOPIC_TASKS: Mapping[str, str] = {
    "roundtable.lifecycle": "app.workers.tasks.run_roundtable_lifecycle",
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


class PostgresOutboxRepository:
    """Minimal dispatcher-owned database boundary."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    @classmethod
    async def connect(cls, database_url: str) -> PostgresOutboxRepository:
        import psycopg
        from psycopg.rows import dict_row

        connection = await psycopg.AsyncConnection.connect(
            database_url,
            autocommit=True,
            row_factory=dict_row,
        )
        return cls(connection)

    async def close(self) -> None:
        await self.connection.close()

    async def heartbeat(self, status: str = "ready") -> None:
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                """
                insert into public.service_heartbeats(service_name, status, heartbeat_at, metadata)
                values ('dispatcher', %s, now(), %s::jsonb)
                on conflict (service_name) do update
                set status=excluded.status, heartbeat_at=excluded.heartbeat_at,
                    metadata=excluded.metadata
                """,
                (status, json.dumps({"pid": os.getpid(), "host": socket.gethostname()})),
            )

    async def claim_batch(
        self,
        *,
        lease_owner: str,
        limit: int,
        lease_seconds: int,
        now: datetime,
    ) -> Sequence[OutboxEvent]:
        lease_until = now + timedelta(seconds=lease_seconds)
        statement = """
            with candidates as (
              select id
              from outbox_events
              where available_at <= %s
                and (
                  status in ('pending', 'failed')
                  or (status = 'leased' and lease_until < %s)
                )
              order by available_at, created_at, id
              for update skip locked
              limit %s
            )
            update outbox_events event
            set status = 'leased',
                lease_owner = %s,
                lease_until = %s,
                attempt = event.attempt + 1,
                error_code = null,
                error_detail_redacted = null
            from candidates
            where event.id = candidates.id
            returning event.id::text as event_id, event.topic,
                      event.business_idempotency_key, event.payload, event.attempt
        """
        async with self.connection.transaction():
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    statement,
                    (now, now, limit, lease_owner, lease_until),
                )
                rows = await cursor.fetchall()
        return [
            OutboxEvent(
                event_id=str(row["event_id"]),
                topic=str(row["topic"]),
                business_idempotency_key=str(row["business_idempotency_key"]),
                payload=dict(row["payload"]),
                attempt=int(row["attempt"]),
            )
            for row in rows
        ]

    async def mark_published(
        self,
        event_id: str,
        *,
        broker_message_id: str,
        published_at: datetime,
    ) -> None:
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                """
                update outbox_events
                set status = 'published', broker_message_id = %s,
                    published_at = %s, lease_owner = null, lease_until = null
                where id = %s::uuid and status = 'leased'
                """,
                (broker_message_id, published_at, event_id),
            )

    async def mark_failed(
        self,
        event_id: str,
        *,
        error_code: str,
        detail_redacted: str,
        dead: bool,
    ) -> None:
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                """
                update outbox_events
                set status = %s::outbox_status, error_code = %s,
                    error_detail_redacted = %s, lease_owner = null, lease_until = null
                where id = %s::uuid and status = 'leased'
                """,
                ("dead" if dead else "failed", error_code[:100], detail_redacted[:500], event_id),
            )


async def run_dispatcher() -> None:
    database_url = os.getenv("DATABASE_URL_ALEA_DISPATCHER")
    if not database_url:
        raise RuntimeError("DATABASE_URL_ALEA_DISPATCHER is required")
    interval = max(0.1, float(os.getenv("DISPATCHER_POLL_SECONDS", "1")))
    batch_size = max(1, min(500, int(os.getenv("DISPATCHER_BATCH_SIZE", "100"))))
    lease_owner = f"dispatcher:{socket.gethostname()}:{os.getpid()}"
    repository = await PostgresOutboxRepository.connect(database_url)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signal_name, stop.set)
    try:
        await repository.heartbeat("ready")
        while not stop.is_set():
            await repository.heartbeat("ready")
            stats = await dispatch_once(
                repository,
                lease_owner=lease_owner,
                limit=batch_size,
            )
            if stats.claimed == 0:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=interval)
                except TimeoutError:
                    pass
    finally:
        await repository.heartbeat("stopping")
        await repository.close()


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
