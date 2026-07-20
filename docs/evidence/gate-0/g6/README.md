# G6 — Backup, capacity, and cost

Status: **blocked on production choices and executable infrastructure**.

## Inputs requiring product confirmation

| Input | Candidate for validation | Confirmed |
|---|---:|---|
| RPO | 15 minutes | no |
| RTO | 4 hours | no |
| Daily roundtables | 20 / 100 / 500 scenarios | no |
| Matches per table | 3 / 6 / 10 scenarios | no |
| Enabled instances | 3 / 7 / 12 scenarios | no |
| Debate rounds | 1 / 2 / 3 scenarios | no |
| Peak live viewers | 50 / 500 / 5,000 scenarios | no |
| Event retention | 90 / 365 / 1,095 days | no |
| Monthly budget ceiling | TBD | no |

## Load model

For a prediction table with `M` matches, `I` instances, and `R` score-debate rounds,
the upper-bound model calls before retries are:

```text
selection = 3I
score = M × I × (2 + R)
bet = 3I
review = M × I when enabled
total = selection + score + bet + review
```

Event volume must be measured from the implementation, not assumed. The load test must
record p50/p95/p99 API latency, Realtime lag and reconnect recovery, PostgreSQL CPU/IO/
connections, Redis memory/eviction, worker queue depth, retry rate, provider tokens/cost,
and headroom at the chosen peak.

## Required closure evidence

1. Named Supabase, managed Redis, and persistent worker platform plans.
2. A staging load-test report at the confirmed peak plus 30% headroom.
3. Alert thresholds and an estimated monthly bill under normal and peak scenarios.
4. One encrypted isolated restore with manifest/hash validation and measured RPO/RTO.
5. Product sign-off on RPO, RTO, retention, and budget.
