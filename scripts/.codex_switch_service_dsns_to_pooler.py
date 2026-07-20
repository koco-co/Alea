#!/usr/bin/env python3
"""Switch generated service-role DSNs to the IPv4 session pooler."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ENV_PATH = Path(".env")
PROJECT_REF = "qevyqgociclrqhglhqux"
POOLER_HOST = "aws-0-us-east-1.pooler.supabase.com"
NAMES = {
    "DATABASE_URL_ALEA_API",
    "DATABASE_URL_ALEA_WORKER",
    "DATABASE_URL_ALEA_DISPATCHER",
    "DATABASE_URL_ALEA_SCHEDULER",
}


def main() -> int:
    updated: list[str] = []
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if not separator or name not in NAMES:
            updated.append(line)
            continue
        parsed = urlsplit(value)
        if not parsed.username or parsed.password is None:
            raise ValueError(f"{name} is not a credentialed PostgreSQL DSN")
        netloc = (
            f"{parsed.username}.{PROJECT_REF}:{parsed.password}"
            f"@{POOLER_HOST}:5432"
        )
        updated.append(
            f"{name}={urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ''))}"
        )

    ENV_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")
    os.chmod(ENV_PATH, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
