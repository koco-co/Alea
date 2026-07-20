# G1 — Auth, RLS, and runtime roles

Status: **blocked — not executed against Supabase Cloud**.

## Required environment

- Migrations `00001`–`00003` applied to the target project.
- `GATE0_DATABASE_URL` set to a migration-capable connection used only by this test.
- Runtime roles created and assigned passwords outside version control.
- An existing Auth user for the one-time administrator bootstrap.

## Reproduction

```bash
cd api
uv run --locked pytest tests/test_g1_auth_rls.py -v
cd ..
make bootstrap-admin EMAIL='<existing-user-email>' ENV=local
```

Record the command, exit code, passed/failed/skipped counts, project reference, and
redacted evidence here after execution. No Gate pass is claimed while any test skips.
