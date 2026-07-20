from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


class NotificationKind(StrEnum):
    PREDICTION_PUBLISHED = "prediction_published"
    PREDICTION_WITHDRAWN = "prediction_withdrawn"
    MATCH_SETTLED = "match_settled"
    TICKET_SETTLED = "ticket_settled"
    FOLLOWED_MATCH_UPDATE = "followed_match_update"
    SYSTEM = "system"


TERMINAL_LEG_STATES = frozenset({"hit", "miss", "refund", "void", "cancelled"})


@dataclass(frozen=True, slots=True)
class NotificationPreference:
    user_id: str
    enabled_kinds: frozenset[NotificationKind]
    notifications_enabled: bool = True

    def allows(self, kind: NotificationKind) -> bool:
        return self.notifications_enabled and kind in self.enabled_kinds


@dataclass(frozen=True, slots=True)
class NotificationCandidate:
    user_id: str
    kind: NotificationKind
    source_event_id: str
    aggregate_id: str
    title: str
    body: str
    payload: Mapping[str, Any]
    source_version: str = "1"


@dataclass(frozen=True, slots=True)
class Notification:
    idempotency_key: str
    user_id: str
    kind: NotificationKind
    title: str
    body: str
    payload: Mapping[str, Any]
    created_at: datetime
    read_at: datetime | None = None

    @property
    def unread(self) -> bool:
        return self.read_at is None


def notification_idempotency_key(candidate: NotificationCandidate) -> str:
    """Stable key suitable for a database UNIQUE constraint and outbox retries."""

    parts = (
        candidate.user_id.strip(),
        candidate.kind.value,
        candidate.source_event_id.strip(),
        candidate.aggregate_id.strip(),
        candidate.source_version.strip(),
    )
    if any(not part for part in parts):
        raise ValueError("notification idempotency inputs must not be empty")
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def generate_notifications(
    candidates: Iterable[NotificationCandidate],
    preferences: Mapping[str, NotificationPreference],
    *,
    existing_idempotency_keys: Iterable[str] = (),
    now: datetime | None = None,
) -> tuple[Notification, ...]:
    """Generate preference-aware, retry-safe notifications without persistence side effects."""

    timestamp = _utc(now)
    seen = set(existing_idempotency_keys)
    generated: list[Notification] = []
    for candidate in candidates:
        preference = preferences.get(candidate.user_id)
        if preference is None or not preference.allows(candidate.kind):
            continue
        key = notification_idempotency_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        generated.append(
            Notification(
                idempotency_key=key,
                user_id=candidate.user_id,
                kind=candidate.kind,
                title=candidate.title.strip(),
                body=candidate.body.strip(),
                payload=MappingProxyType(_copy_mapping(candidate.payload)),
                created_at=timestamp,
            )
        )
    return tuple(generated)


def ticket_terminal_notification(
    *,
    user_id: str,
    ticket_id: str,
    settlement_run_id: str,
    leg_states: Sequence[str],
    title: str,
    body: str,
    payload: Mapping[str, Any],
) -> NotificationCandidate | None:
    """Return one ticket-level notification only after every leg reaches a terminal state."""

    if not leg_states or any(state not in TERMINAL_LEG_STATES for state in leg_states):
        return None
    return NotificationCandidate(
        user_id=user_id,
        kind=NotificationKind.TICKET_SETTLED,
        source_event_id=settlement_run_id,
        aggregate_id=ticket_id,
        title=title,
        body=body,
        payload={**dict(payload), "leg_states": list(leg_states)},
    )


def mark_notification_read(
    notification: Notification, *, now: datetime | None = None
) -> Notification:
    if notification.read_at is not None:
        return notification
    return replace(notification, read_at=_utc(now))


def mark_all_read(
    notifications: Iterable[Notification], *, user_id: str, now: datetime | None = None
) -> tuple[Notification, ...]:
    timestamp = _utc(now)
    return tuple(
        replace(item, read_at=timestamp)
        if item.user_id == user_id and item.read_at is None
        else item
        for item in notifications
    )


def unread_count(notifications: Iterable[Notification], *, user_id: str) -> int:
    return sum(1 for item in notifications if item.user_id == user_id and item.unread)


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, child in value.items():
        if isinstance(child, Mapping):
            result[str(key)] = _copy_mapping(child)
        elif isinstance(child, Sequence) and not isinstance(child, (str, bytes, bytearray)):
            result[str(key)] = list(child)
        else:
            result[str(key)] = child
    return result


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
