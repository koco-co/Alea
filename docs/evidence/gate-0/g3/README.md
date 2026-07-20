# G3 — Celery recovery

Status: **unit contract ready; process-level fault experiment blocked**.

```bash
cd api
uv run --locked pytest tests/test_g3_celery_recovery.py -v
```

Before passing G3, run the worker/Redis/Dispatcher stack and record duplicate delivery,
graceful stop, `kill -9`, Redis restart, Dispatcher restart, timeout, late result, Beat
overlap, and poison-message experiments. This sandbox cannot access the Docker daemon,
so no process-level result or pass claim is recorded yet.
