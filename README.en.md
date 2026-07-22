# Alea

Alea is a multi-provider football analysis, roundtable, audit, simulation, settlement, and review platform for China Sports Lottery football products.

> Research and entertainment only. It is not betting advice. Unlicensed Sporttery sales data, odds, and results must remain unavailable or pending confirmation.

## Local development

Requirements: Python 3.12, uv, Bun 1.3.10, Docker, and Supabase CLI 2.109.1. A local AI CLI is required only when validating that specific CLI connection; Alea does not scan `PATH`.

```bash
chmod 600 .env
make env-check
make bootstrap
make dev
```

The root `.env` contains server-side configuration names such as `PROJECT_URL`, `PUBLISHABLE_KEY`, `SECRET_KEY`, `PROVIDER_KEK_V1`, migration DSNs, and least-privilege service-role DSNs. Never copy secrets into Web configuration or Git.

Common checks:

```bash
make check
make db-push ENV=local
make db-push ENV=staging
```

Product behavior is defined by `docs/产品需求文档.md`, architecture by `docs/技术架构设计文档.md`, and visual rules by `DESIGN.md`.

<!-- ALEA-HARDENING-FIXPACK-2026-07-21: implementation-status -->
## Implementation status and release gates

- Roundtable start requires three distinct instances across at least two provider families.
- Autonomous and specified selection accept only authorized, on-sale, pre-cutoff Sporttery offers with an odds snapshot.
- The worker idempotently creates the first `predict_score` phase and uses `ALEA_PHASE_EXECUTOR_FACTORY=app.workers.production_executor:create_phase_executor`; the local fixture chain has been verified through notarization.
- Historical backfills require an adapter licensed for automated access, caching, historical storage, public display, and redistribution. This repository does not include an authorization-bypassing scraper.
- The real local API/CLI multi-phase chain is verified. No licensed historical dataset was provided, so no historical backfill is claimed; full-stack E2E and browser evidence remain tracked in the latest QA report.

Verification:

```bash
python scripts/verify_hardening_contracts.py
make test-hardening
```

## Current boundaries

- A roundtable must use exactly three qualified instances across at least two Provider families; otherwise it ends as `no_quorum`.
- `/console/admin/lineup` manages both API vendors and administrator-specified absolute CLI paths. No standalone runner daemon is deployed.
- The Sporttery Web Source stays disabled until permission is confirmed. Gate 0 historical-data validation uses explicitly labeled football-sale fixtures only.
- Database and Storage migration, off-site logical backup, and clean-environment restore are documented in [the backup and restore runbook](docs/deployment/database-backup-restore.md).
- No repository license is attached by default. Third-party references are currently documented in `docs/THIRD_PARTY_REFERENCES.md` and remain subject to the final file audit.
