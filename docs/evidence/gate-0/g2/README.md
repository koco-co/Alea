# G2 — Realtime Broadcast and deterministic backfill

Status: **partially verified offline; cloud authorization test blocked**.

The local sequencer tests cover subscribe-before-backfill races, duplicate events,
explicit gaps, and reconnect recovery. Cloud execution must additionally prove private
topic authorization for unpublished/published jobs and rejection of client Broadcast.

```bash
cd api
uv run --locked pytest tests/test_g2_realtime.py -v
```

Do not mark G2 passed if the database-backed test skips.
