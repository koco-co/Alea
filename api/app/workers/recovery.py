from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class DeliveryState(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class Checkpoint:
    idempotency_key: str
    state: DeliveryState = DeliveryState.PENDING
    attempt: int = 0
    lease_until: datetime | None = None
    result_hash: str | None = None

    def claim(self, now: datetime, lease_seconds: int = 60) -> bool:
        if self.state in (DeliveryState.SUCCEEDED, DeliveryState.DEAD):
            return False
        if self.state == DeliveryState.LEASED and self.lease_until and self.lease_until >= now:
            return False
        self.state = DeliveryState.LEASED
        self.attempt += 1
        self.lease_until = now + timedelta(seconds=lease_seconds)
        return True

    def complete(self, result_hash: str) -> bool:
        if self.state == DeliveryState.SUCCEEDED:
            return self.result_hash == result_hash
        if self.state != DeliveryState.LEASED:
            return False
        self.state = DeliveryState.SUCCEEDED
        self.result_hash = result_hash
        self.lease_until = None
        return True

    def fail(self, max_attempts: int) -> None:
        self.state = DeliveryState.DEAD if self.attempt >= max_attempts else DeliveryState.FAILED
        self.lease_until = None

    def release(self) -> bool:
        """Release a lease during graceful shutdown without consuming a new attempt."""
        if self.state != DeliveryState.LEASED:
            return False
        self.state = DeliveryState.PENDING
        self.lease_until = None
        return True


@dataclass
class OutboxCheckpoint:
    business_key: str
    state: DeliveryState = DeliveryState.PENDING
    attempt: int = 0
    lease_until: datetime | None = None
    broker_message_id: str | None = None

    def claim(self, now: datetime, *, lease_seconds: int = 30) -> bool:
        if self.state in {DeliveryState.SUCCEEDED, DeliveryState.DEAD}:
            return False
        if self.state == DeliveryState.LEASED and self.lease_until and self.lease_until >= now:
            return False
        self.state = DeliveryState.LEASED
        self.attempt += 1
        self.lease_until = now + timedelta(seconds=lease_seconds)
        return True

    def mark_published(self, broker_message_id: str) -> bool:
        if self.state == DeliveryState.SUCCEEDED:
            return self.broker_message_id == broker_message_id
        if self.state != DeliveryState.LEASED:
            return False
        self.state = DeliveryState.SUCCEEDED
        self.broker_message_id = broker_message_id
        self.lease_until = None
        return True


def utc_now() -> datetime:
    return datetime.now(UTC)
