# G4 — Provider contract and capability reports

Status: **fake provider ready; real vendor/model capability and variance runs blocked**.

```bash
cd api
uv run --locked pytest tests/test_g4_provider_contract.py -v
```

The fake suite covers all eleven business methods, timeout, rate limiting, invalid JSON,
refusal, untrusted role labels, and instruction-injection text isolation. A vendor/model
is not eligible for `enabled=true` until its own report records all eleven contracts,
usage, upstream request ID, error classes, and at least five repeated identical calls.

## Required reports

| Vendor/model | 11 methods | Repetitions | attempts_per_instance | Result |
|---|---:|---:|---:|---|
| DeepSeek / exact model TBD | not run | 0/5 | pending | blocked by network/runtime configuration |
| OpenAI | not configured | 0/5 | pending | missing key |
| Anthropic | not configured | 0/5 | pending | missing key |
| Kimi | not configured | 0/5 | pending | missing key |

Never place API keys or upstream response bodies in this directory.
