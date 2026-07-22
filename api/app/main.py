from __future__ import annotations

import inspect
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.auth import SignupFailure, SignupRequest, SupabaseAuthGateway
from app.middleware import configure_security
from app.routers import admin, ledger, matches, real_ledger, roundtable, settings
from app.runtime import BusinessGateway, DatasourceFactory, ProviderFactory


def _create_supabase_client() -> Any | None:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    secret_key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if not url or not secret_key:
        return None

    from supabase import ClientOptions, create_client

    return create_client(
        url,
        secret_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


async def _connect_database() -> Any | None:
    database_url = os.getenv("DATABASE_URL_ALEA_API")
    if not database_url:
        return None
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - exercised only by a broken deployment
        raise RuntimeError(
            "DATABASE_URL_ALEA_API is configured but psycopg is not installed"
        ) from exc
    from psycopg.rows import dict_row

    return await psycopg.AsyncConnection.connect(
        database_url,
        autocommit=True,
        row_factory=dict_row,
    )


async def _close_resource(resource: Any | None) -> None:
    close = getattr(resource, "close", None)
    if not callable(close):
        return
    result = close()
    if inspect.isawaitable(result):
        await result


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    supabase_client = None
    database = None
    gateway = None
    datasource_factory = DatasourceFactory()
    provider_factory = ProviderFactory()
    app.state.supabase = None
    app.state.database = None
    app.state.datasource_factory = datasource_factory
    app.state.provider_factory = provider_factory
    for attribute in (
        "admin_gateway",
        "roundtable_event_gateway",
        "match_gateway",
        "ledger_gateway",
        "real_ledger_gateway",
        "settings_gateway",
    ):
        setattr(app.state, attribute, None)
    try:
        supabase_client = _create_supabase_client()
        database = await _connect_database()
        if database is not None:
            gateway = BusinessGateway(
                database,
                datasource_factory=datasource_factory,
                provider_factory=provider_factory,
                privileged_supabase=supabase_client,
            )
        app.state.supabase = supabase_client
        app.state.database = database
        if gateway is not None:
            app.state.admin_gateway = gateway
            app.state.roundtable_event_gateway = gateway
            app.state.match_gateway = gateway
            app.state.ledger_gateway = gateway
            app.state.real_ledger_gateway = gateway
            app.state.settings_gateway = gateway
        yield
    finally:
        await _close_resource(database)
        await _close_resource(supabase_client)
        app.state.database = None
        app.state.supabase = None
        for attribute in (
            "admin_gateway",
            "roundtable_event_gateway",
            "match_gateway",
            "ledger_gateway",
            "real_ledger_gateway",
            "settings_gateway",
        ):
            setattr(app.state, attribute, None)


app = FastAPI(title="Alea API", version="0.1.0", lifespan=lifespan)
configure_security(app)
app.include_router(admin.router)
app.include_router(roundtable.router)
app.include_router(matches.router)
app.include_router(ledger.router)
app.include_router(ledger.rankings_router)
app.include_router(real_ledger.router)
app.include_router(settings.router)
app.include_router(settings.messages_router)
app.include_router(settings.admin_settings_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Process liveness only; dependency health belongs to /readyz."""
    return {"service": "alea-api", "status": "ok"}


@app.get("/livez", tags=["system"])
async def liveness() -> dict[str, str]:
    return {"service": "alea-api", "status": "ok"}


@app.get("/readyz", tags=["system"])
async def readiness() -> JSONResponse:
    checks: dict[str, bool] = {
        "database": False,
        "migration": False,
        "redis": False,
        "supabase": app.state.supabase is not None,
        "dispatcher": False,
        "worker": False,
        "executor_factory": bool(os.getenv("ALEA_PHASE_EXECUTOR_FACTORY", "").strip()),
    }
    database = getattr(app.state, "database", None)
    if database is not None:
        try:
            async with database.cursor() as cursor:
                await cursor.execute("select 1")
                database_row = await cursor.fetchone()
                checks["database"] = bool(database_row and next(iter(database_row.values())) == 1)
                await cursor.execute(
                    "select max(version) from supabase_migrations.schema_migrations"
                )
                latest = await cursor.fetchone()
                latest_value = next(iter(latest.values())) if latest else None
                checks["migration"] = bool(latest_value and str(latest_value) >= "20260722010000")
                await cursor.execute(
                    """
                    select service_name, status
                    from public.service_heartbeats
                    where heartbeat_at > now() - interval '45 seconds'
                    """
                )
                heartbeat_rows = await cursor.fetchall()
                for heartbeat_row in heartbeat_rows:
                    service_name = heartbeat_row["service_name"]
                    service_status = heartbeat_row["status"]
                    if service_status == "ready" and service_name in {"dispatcher", "worker"}:
                        checks[service_name] = True
        except Exception:
            pass
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        redis_client = None
        try:
            from redis.asyncio import from_url

            redis_client = from_url(redis_url)  # type: ignore[no-untyped-call]
            checks["redis"] = bool(await redis_client.ping())
        except Exception:
            checks["redis"] = False
        finally:
            if redis_client is not None:
                await redis_client.aclose()
    missing = [name for name, passed in checks.items() if not passed]
    status_code = 503 if missing else 200
    return JSONResponse(
        {
            "service": "alea-api",
            "status": "not_ready" if missing else "ready",
            "missing": missing,
            "checks": checks,
        },
        status_code=status_code,
    )


@app.post("/auth/signup", status_code=201, tags=["auth"])
async def signup(request: SignupRequest) -> JSONResponse:
    required = {
        "url": os.getenv("SUPABASE_URL"),
        "publishable_key": os.getenv("SUPABASE_PUBLISHABLE_KEY"),
        "secret_key": os.getenv("SUPABASE_SECRET_KEY"),
    }
    if not all(required.values()):
        return JSONResponse({"error": "auth_unavailable"}, status_code=503)
    gateway = SupabaseAuthGateway(
        url=required["url"] or "",
        publishable_key=required["publishable_key"] or "",
        secret_key=required["secret_key"] or "",
    )
    try:
        result = await gateway.signup(request)
    except SignupFailure as exc:
        return JSONResponse({"error": exc.code}, status_code=exc.status_code)
    finally:
        await gateway.close()
    return JSONResponse(
        {"requiresEmailConfirmation": result.requires_email_confirmation},
        status_code=201,
    )
