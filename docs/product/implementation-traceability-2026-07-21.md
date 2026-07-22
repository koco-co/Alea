# Product-to-implementation traceability — 2026-07-21

| Requirement | Enforced by | Automated evidence | Current state |
| --- | --- | --- | --- |
| Three effective participants | API request model, API distinctness check, database command wrapper, worker initializer | `test_roundtable_hardening_contract.py`, hardening contract gate | Implemented |
| At least two Provider families | Database command wrapper and worker initializer | SQL contract test | Implemented |
| Only wagerable Sporttery offers | `alea_is_sporttery_offer_eligible` and strict roundtable command wrapper | SQL contract test; local authorized fixture returned `True`; clean reset passed | Implemented |
| No empty roundtable | Strict database wrapper | SQL contract test | Implemented |
| API and CLI share a runtime contract | `PhaseExecutor` plus `app.workers.production_executor:create_phase_executor` | executor bootstrap unit tests; real DeepSeek + Codex execution | Implemented |
| Durable lifecycle reaches Provider work | Worker lifecycle task, database initializer, Outbox phase message | real local run completed through notarize | Implemented for prediction/bet phases |
| Post-match review and ticket settlement | `postmatch_review_contexts`, `settlement_reviews`, `settlement_position_plans`, worker settlement RPC and production phase executor | local authorized fixture: 3/3 review phases succeeded, review completion event persisted, 1x1 hit returned 250.00, repeated settlement/review calls idempotently replayed | Implemented for the supported frozen single-match ticket shapes; authorized history remains absent |
| Historical source authorization | `BackfillSourcePolicy` | backfill policy unit tests | Implemented |
| Historical data already synchronized | Sync coverage view and future batch evidence | No production batch evidence | Not complete |
| Admin users/settings are database-backed | `/console/admin/users`, `/console/admin/settings`, versioned admin RPCs and audit log | Empty-reset migration smoke: 2 users queried, disable/restore and setting version write; container E2E settings save | Implemented |
| Real full-stack E2E and visual validation | Docker API/Web/Redis/Dispatcher/Worker/Scheduler plus in-app Browser evidence | Playwright real auth 20/20 at 1440×900 and 390×844 in both host and production-container paths; Docker `/readyz` HTTP 200; in-app Browser inspected lineup API/CLI tabs plus sync, roundtable no-quorum, predictions empty and calculator unavailable states | Key states verified; all-route visual regression remains |
| Documentation reflects implementation | Chinese/English README status blocks, this matrix, QA report | hardening verifier | Partially synchronized |

The PRD, architecture, prototype, implementation plan, rule version, migration, tests,
and QA report must all point to the same release commit. Historical documents should
be marked superseded rather than silently deleted.
