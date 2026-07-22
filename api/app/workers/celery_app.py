from __future__ import annotations

import os
import threading

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from kombu import Queue

celery_app = Celery(
    "alea",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    include=["app.workers.tasks"],
)
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
    timezone="Asia/Shanghai",
    enable_utc=True,
)


def _write_worker_heartbeat(status: str) -> None:
    database_url = os.getenv("DATABASE_URL_ALEA_WORKER", "").strip()
    if not database_url:
        return
    try:
        import json
        import socket
        import psycopg

        with psycopg.connect(database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into public.service_heartbeats(service_name, status, heartbeat_at, metadata)
                    values ('worker', %s, now(), %s::jsonb)
                    on conflict (service_name) do update
                    set status=excluded.status, heartbeat_at=excluded.heartbeat_at,
                        metadata=excluded.metadata
                    """,
                    (status, json.dumps({"pid": os.getpid(), "host": socket.gethostname()})),
                )
    except Exception:
        # Readiness remains false until a later heartbeat succeeds; worker startup
        # must still expose the original exception if its broker/database is broken.
        return


_heartbeat_stop = threading.Event()


def _heartbeat_loop() -> None:
    while not _heartbeat_stop.wait(15):
        _write_worker_heartbeat("ready")


@worker_ready.connect
def mark_worker_ready(**_: object) -> None:
    _heartbeat_stop.clear()
    _write_worker_heartbeat("ready")
    threading.Thread(target=_heartbeat_loop, name="alea-worker-heartbeat", daemon=True).start()


@worker_shutdown.connect
def mark_worker_stopping(**_: object) -> None:
    _heartbeat_stop.set()
    _write_worker_heartbeat("stopping")
