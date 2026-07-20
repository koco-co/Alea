#!/usr/bin/env python3
"""Bootstrap the first Alea administrator with migration-level credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def auth_user_id(url: str, secret_key: str, email: str) -> str:
    request = Request(
        f"{url.rstrip('/')}/auth/v1/admin/users?page=1&per_page=1000",
        headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}"},
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - configured Supabase URL
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Supabase Auth Admin lookup failed with HTTP {exc.code}") from exc

    users = payload.get("users", payload if isinstance(payload, list) else [])
    matches = [user for user in users if user.get("email", "").casefold() == email.casefold()]
    if len(matches) != 1:
        raise RuntimeError(f"expected one existing Auth user for {email!r}, found {len(matches)}")
    return str(matches[0]["id"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--env", choices=("local", "staging", "production"), required=True)
    args = parser.parse_args()

    env_file = ROOT / f".env.{args.env}"
    if not env_file.is_file():
        raise SystemExit(f"ERROR: {env_file} not found")
    config = {**load_env_file(env_file), **os.environ}
    required = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_DB_URL")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise SystemExit(f"ERROR: missing {', '.join(missing)}")

    user_id = auth_user_id(config["SUPABASE_URL"], config["SUPABASE_SECRET_KEY"], args.email)
    reason = f"initial deployment bootstrap for {args.env}"
    with psycopg.connect(config["SUPABASE_DB_URL"]) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("select count(*) from profiles where role = 'admin' and status = 'active'")
                if cursor.fetchone()[0] != 0:
                    raise RuntimeError("an active administrator already exists; bootstrap is one-time only")
                cursor.execute("select id from auth.users where id = %s", (user_id,))
                if cursor.fetchone() is None:
                    raise RuntimeError("Auth user is not visible in the target database")
                cursor.execute(
                    """
                    insert into profiles (id, role, status)
                    values (%s, 'admin', 'active')
                    on conflict (id) do update set role = 'admin', status = 'active', updated_at = now()
                    """,
                    (user_id,),
                )
                cursor.execute(
                    "insert into admin_role_grants (user_id, action, granted_by, reason, active) values (%s, 'grant', null, %s, true)",
                    (user_id, reason),
                )
                cursor.execute(
                    "insert into admin_audit_logs (actor_id, action, target_type, target_id, detail_redacted) values (null, 'bootstrap_admin', 'profile', %s, jsonb_build_object('environment', %s))",
                    (user_id, args.env),
                )
    print(f"bootstrapped first administrator for {args.email} in {args.env}")


if __name__ == "__main__":
    main()
