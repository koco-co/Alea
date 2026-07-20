from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence

from app.workers.celery_app import celery_app


class ScheduleKind(StrEnum):
    DATA_SYNC = "data_sync"
    ROUNDTABLE = "roundtable"
    AUTO_REVIEW = "auto_review"
    BACKGROUND_CHECK = "background_check"


class MisfirePolicy(StrEnum):
    SKIP = "skip"
    FIRE_ONCE = "fire_once"


SCHEDULE_TOPICS: Mapping[ScheduleKind, str] = {
    ScheduleKind.DATA_SYNC: "schedule.data_sync",
    ScheduleKind.ROUNDTABLE: "schedule.roundtable",
    ScheduleKind.AUTO_REVIEW: "schedule.auto_review",
    ScheduleKind.BACKGROUND_CHECK: "schedule.background_check",
}


@dataclass(frozen=True, slots=True)
class DueSchedule:
    schedule_id: str
    kind: ScheduleKind
    business_date: date
    scheduled_for: datetime
    payload: Mapping[str, Any]
    misfire_grace_seconds: int = 300
    misfire_policy: MisfirePolicy = MisfirePolicy.SKIP

    def __post_init__(self) -> None:
        if not self.schedule_id.strip():
            raise ValueError("schedule_id must not be empty")
        if self.scheduled_for.tzinfo is None:
            raise ValueError("scheduled_for must be timezone-aware")
        if self.misfire_grace_seconds < 0:
            raise ValueError("misfire_grace_seconds must be non-negative")

    @property
    def business_idempotency_key(self) -> str:
        return schedule_idempotency_key(self.schedule_id, self.business_date)


@dataclass(frozen=True, slots=True)
class SchedulerStats:
    due: int = 0
    enqueued: int = 0
    duplicate: int = 0
    misfired: int = 0
    failed: int = 0


class SchedulerRepository(Protocol):
    async def list_due_schedules(self, *, now: datetime, limit: int) -> Sequence[DueSchedule]: ...

    async def claim_and_enqueue(
        self,
        *,
        schedule_id: str,
        business_date: date,
        scheduled_for: datetime,
        business_idempotency_key: str,
        topic: str,
        payload: Mapping[str, Any],
        lease_owner: str,
        lease_seconds: int,
        now: datetime,
    ) -> bool:
        """Atomically claim schedule_id+business_date and append one outbox row."""
        ...

    async def record_misfire(
        self,
        *,
        schedule_id: str,
        business_date: date,
        scheduled_for: datetime,
        observed_at: datetime,
        policy: MisfirePolicy,
    ) -> None: ...


async def schedule_once(
    repository: SchedulerRepository,
    *,
    lease_owner: str,
    now: datetime | None = None,
    limit: int = 100,
    lease_seconds: int = 60,
) -> SchedulerStats:
    timestamp = _utc(now)
    if not lease_owner.strip() or limit < 1 or lease_seconds < 1:
        raise ValueError("lease_owner, limit, and lease_seconds must be valid")
    due = await repository.list_due_schedules(now=timestamp, limit=limit)
    enqueued = duplicate = misfired = failed = 0
    for item in due:
        lateness = max(0.0, (timestamp - item.scheduled_for.astimezone(UTC)).total_seconds())
        if lateness > item.misfire_grace_seconds and item.misfire_policy is MisfirePolicy.SKIP:
            misfired += 1
            await repository.record_misfire(
                schedule_id=item.schedule_id,
                business_date=item.business_date,
                scheduled_for=item.scheduled_for,
                observed_at=timestamp,
                policy=item.misfire_policy,
            )
            continue
        try:
            claimed = await repository.claim_and_enqueue(
                schedule_id=item.schedule_id,
                business_date=item.business_date,
                scheduled_for=item.scheduled_for,
                business_idempotency_key=item.business_idempotency_key,
                topic=SCHEDULE_TOPICS[item.kind],
                payload={
                    **dict(item.payload),
                    "schedule_id": item.schedule_id,
                    "business_date": item.business_date.isoformat(),
                    "scheduled_for": item.scheduled_for.isoformat(),
                },
                lease_owner=lease_owner,
                lease_seconds=lease_seconds,
                now=timestamp,
            )
        except Exception:
            failed += 1
        else:
            if claimed:
                enqueued += 1
            else:
                duplicate += 1
    return SchedulerStats(
        due=len(due),
        enqueued=enqueued,
        duplicate=duplicate,
        misfired=misfired,
        failed=failed,
    )


def schedule_idempotency_key(schedule_id: str, business_date: date) -> str:
    if not schedule_id.strip():
        raise ValueError("schedule_id must not be empty")
    return f"schedule:{schedule_id}:{business_date.isoformat()}"


_repository: SchedulerRepository | None = None


def configure_scheduler_repository(repository: SchedulerRepository) -> None:
    global _repository
    _repository = repository


@celery_app.task(name="app.workers.scheduler.tick", acks_late=True)
def scheduler_tick(*, lease_owner: str = "celery-beat") -> dict[str, int]:
    if _repository is None:
        raise RuntimeError("scheduler repository has not been configured")
    result = _run_awaitable(schedule_once(_repository, lease_owner=lease_owner))
    return {
        "due": result.due,
        "enqueued": result.enqueued,
        "duplicate": result.duplicate,
        "misfired": result.misfired,
        "failed": result.failed,
    }


DEFAULT_BEAT_SCHEDULE: Mapping[str, Mapping[str, Any]] = {
    "alea-database-scheduler": {
        "task": "app.workers.scheduler.tick",
        "schedule": 30.0,
        "options": {"expires": 25},
    }
}
celery_app.conf.beat_schedule = {
    **dict(getattr(celery_app.conf, "beat_schedule", {}) or {}),
    **DEFAULT_BEAT_SCHEDULE,
}


def _run_awaitable(awaitable: Any) -> SchedulerStats:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    if inspect.iscoroutine(awaitable):
        awaitable.close()
    raise RuntimeError("scheduler tick must run outside an active asyncio event loop")


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
