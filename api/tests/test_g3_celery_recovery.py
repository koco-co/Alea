from datetime import UTC, datetime, timedelta

from app.workers.celery_app import celery_app
from app.workers.recovery import Checkpoint, DeliveryState, OutboxCheckpoint


def test_celery_delivery_contract() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_time_limit == 120
    assert celery_app.conf.result_backend is None


def test_duplicate_delivery_has_one_terminal_result() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checkpoint = Checkpoint("job:match:phase:0:instance")
    assert checkpoint.claim(now)
    assert not checkpoint.claim(now + timedelta(seconds=1))
    assert checkpoint.complete("result-v1")
    assert checkpoint.complete("result-v1")
    assert checkpoint.state == DeliveryState.SUCCEEDED
    assert not checkpoint.complete("conflicting-late-result")


def test_killed_worker_lease_can_be_reclaimed() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checkpoint = Checkpoint("recoverable")
    assert checkpoint.claim(now, lease_seconds=5)
    assert not checkpoint.claim(now + timedelta(seconds=5))
    assert checkpoint.claim(now + timedelta(seconds=6))
    assert checkpoint.attempt == 2


def test_timeout_and_poison_task_do_not_loop_forever() -> None:
    checkpoint = Checkpoint("poison")
    now = datetime(2026, 7, 20, tzinfo=UTC)
    for attempt in range(1, 4):
        assert checkpoint.claim(now + timedelta(minutes=attempt))
        checkpoint.fail(max_attempts=3)
    assert checkpoint.state == DeliveryState.DEAD
    assert not checkpoint.claim(now + timedelta(hours=1))


def test_beat_overlap_uses_stable_business_key() -> None:
    first = Checkpoint("schedule-id:2026-07-20")
    duplicate = Checkpoint("schedule-id:2026-07-20")
    assert first.idempotency_key == duplicate.idempotency_key


def test_graceful_stop_releases_lease_for_immediate_recovery() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checkpoint = Checkpoint("graceful")
    assert checkpoint.claim(now, lease_seconds=120)
    assert checkpoint.release()
    assert checkpoint.claim(now + timedelta(seconds=1))


def test_redis_restart_redelivery_reuses_business_checkpoint() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checkpoint = Checkpoint("provider-call:stable")
    assert checkpoint.claim(now)
    assert checkpoint.complete("one-charge-and-result")
    assert not checkpoint.claim(now + timedelta(minutes=5))
    assert checkpoint.complete("one-charge-and-result")


def test_dispatcher_restart_reclaims_expired_outbox_without_duplicate_publish() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    outbox = OutboxCheckpoint("roundtable:completed")
    assert outbox.claim(now, lease_seconds=10)
    assert not outbox.claim(now + timedelta(seconds=10))
    assert outbox.claim(now + timedelta(seconds=11))
    assert outbox.mark_published("broker-1")
    assert outbox.mark_published("broker-1")
    assert not outbox.mark_published("broker-duplicate")


def test_late_result_after_timeout_cannot_replace_terminal_result() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checkpoint = Checkpoint("timeout")
    assert checkpoint.claim(now, lease_seconds=5)
    checkpoint.fail(max_attempts=2)
    assert checkpoint.claim(now + timedelta(seconds=6))
    assert checkpoint.complete("retry-result")
    assert not checkpoint.complete("late-first-attempt-result")
