#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", "tests/test_g1_auth_rls.py", "tests/test_g2_realtime.py", "tests/test_g3_celery_recovery.py", "tests/test_g4_provider_contract.py", "tests/test_g5_data_rules.py", "tests/test_g6_capacity.py"]
    completed = subprocess.run(command, cwd=API, check=False)
    external = {
        "g1_real_database": all(
            os.getenv(name)
            for name in ("GATE0_DATABASE_URL", "GATE0_ADMIN_USER_ID", "GATE0_USER_ID")
        ),
        "g4_real_provider_capability": os.getenv("GATE0_REAL_PROVIDER_VERIFIED") == "1",
        "g5_production_data_license": os.getenv("GATE0_DATA_LICENSE_VERIFIED") == "1",
        "g6_plan_budget_rpo_rto": os.getenv("GATE0_G6_APPROVED") == "1",
        "g6_isolated_restore": os.getenv("GATE0_RESTORE_VERIFIED") == "1",
        "g6_load_test": os.getenv("GATE0_LOAD_VERIFIED") == "1",
    }
    summary = {
        "test_exit_code": completed.returncode,
        "external_checks": external,
        "gate0_passed": completed.returncode == 0 and all(external.values()),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["gate0_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
