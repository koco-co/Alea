#!/usr/bin/env python3
"""Validate Alea's local environment without printing any secret value."""

from __future__ import annotations

import argparse
import re
import stat
from pathlib import Path
from urllib.parse import urlsplit


REQUIRED = ("PROJECT_URL", "PUBLISHABLE_KEY", "SECRET_KEY", "PROVIDER_KEK_V1")
DATABASE_URLS = (
    "SUPABASE_DB_URL",
    "DATABASE_URL_ALEA_API",
    "DATABASE_URL_ALEA_WORKER",
    "DATABASE_URL_ALEA_DISPATCHER",
    "DATABASE_URL_ALEA_SCHEDULER",
)
HEX_64 = re.compile(r"^[0-9a-fA-F]{64}$")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected NAME=value")
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip("\"'")
    return values


def validate(path: Path, *, require_database: bool) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path} does not exist"]
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        errors.append(f"{path} permissions must be 0600 (found {mode:04o})")
    try:
        values = parse_env(path)
    except ValueError as exc:
        return [str(exc)]

    for name in REQUIRED:
        if not values.get(name):
            errors.append(f"{name} is missing or empty")

    project_url = values.get("PROJECT_URL", "")
    if project_url.startswith("[") or "](" in project_url:
        errors.append("PROJECT_URL must be a plain URL, not Markdown")
    else:
        parsed = urlsplit(project_url)
        if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(
            ".supabase.co"
        ):
            errors.append("PROJECT_URL must be an https://*.supabase.co URL")

    publishable = values.get("PUBLISHABLE_KEY", "")
    if publishable and not publishable.startswith("sb_publishable_"):
        errors.append("PUBLISHABLE_KEY must be a Supabase publishable key")
    secret = values.get("SECRET_KEY", "")
    if secret and not secret.startswith("sb_secret_"):
        errors.append("SECRET_KEY must be a Supabase secret key")
    kek = values.get("PROVIDER_KEK_V1", "")
    if kek and not HEX_64.fullmatch(kek):
        errors.append("PROVIDER_KEK_V1 must be exactly 64 hexadecimal characters")

    if require_database:
        for name in DATABASE_URLS:
            value = values.get(name, "")
            if not value:
                errors.append(f"{name} is missing or empty")
                continue
            parsed = urlsplit(value)
            if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
                errors.append(f"{name} must be a PostgreSQL DSN")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=".env")
    parser.add_argument("--require-database", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.file), require_database=args.require_database)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Environment validation passed (secret values were not displayed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
