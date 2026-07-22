#!/usr/bin/env python3
"""Static release gate for the Alea hardening invariants."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{path}: missing required contract(s): {missing}")


def forbid(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    present = [needle for needle in needles if needle in text]
    if present:
        raise AssertionError(f"{path}: forbidden contract(s) present: {present}")


def tracked_generated_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return []
    prefixes = (".tmp/", "playwright-report/", "test-results/")
    return [line for line in result.stdout.splitlines() if line.startswith(prefixes)]


def main() -> int:
    try:
        require(
            "api/app/workers/tasks.py",
            "alea_worker_initialize_roundtable",
            "resolve_phase_executor",
        )
        require(
            "api/app/routers/admin.py",
            "Field(min_length=3, max_length=3)",
            "three_distinct_instances_required",
            "scheduled_roundtable_not_supported",
        )
        for path in ("api/app/main.py", "api/app/middleware.py"):
            forbid(path, "qevyqgociclrqhglhqux.supabase.co", "DEFAULT_SUPABASE_URL")
        require("api/app/main.py", '@app.get("/readyz"', 'os.getenv("SUPABASE_URL")')
        require(
            "api/app/middleware.py",
            "SUPABASE_JWT_ISSUER or SUPABASE_URL is required",
        )
        forbid("api/app/auth.py", '"terms-v1"', '"privacy-v1"', '"risk-v1"')
        require(
            "api/app/auth.py",
            "ALEA_TERMS_VERSION",
            "ALEA_PRIVACY_VERSION",
            "ALEA_RISK_VERSION",
        )
        require("api/app/workers/celery_app.py", 'timezone="Asia/Shanghai"')
        require(
            "supabase/migrations/20260721020000_roundtable_execution_hardening.sql",
            "roundtable requires exactly three distinct instances",
            "at least two provider families",
            "no_eligible_sporttery_matches",
            "alea_is_sporttery_offer_eligible",
            "roundtable.predict_score",
        )
        generated = tracked_generated_files()
        if generated:
            raise AssertionError(f"generated files are tracked: {generated}")
    except (AssertionError, OSError) as exc:
        print(f"hardening-contracts: FAILED: {exc}", file=sys.stderr)
        return 1
    print("hardening-contracts: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
