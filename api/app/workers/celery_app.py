from __future__ import annotations

import os

from celery import Celery
from kombu import Queue

celery_app = Celery("alea", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))
celery_app.conf.update(
    task_acks_late=True,
    task_acks_on_failure_or_timeout=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_soft_time_limit=110,
    task_time_limit=120,
    task_default_queue="default",
    task_queues=(Queue("default"), Queue("long"), Queue("dead")),
    task_routes={"app.workers.tasks.run_provider_phase": {"queue": "long"}},
    result_backend=None,
    timezone="Asia/Taipei",
    enable_utc=True,
)
