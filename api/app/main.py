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


DEFAULT_SUPABASE_URL = "https://qevyqgociclrqhglhqux.supabase.co"


def _create_supabase_client() -> Any | None:
    secret_key = os.getenv("SUPABASE_SECRET_KEY")
    if not secret_key:
        return None

    from supabase import ClientOptions, create_client

    url = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL).rstrip("/")
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
    return await psycopg.AsyncConnection.connect(database_url, autocommit=True)


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
    app.state.supabase = None
    app.state.database = None
    try:
        supabase_client = _create_supabase_client()
        database = await _connect_database()
        app.state.supabase = supabase_client
        app.state.database = database
        yield
    finally:
        await _close_resource(database)
        await _close_resource(supabase_client)
        app.state.database = None
        app.state.supabase = None


app = FastAPI(title="Alea API", version="0.1.0", lifespan=lifespan)
configure_security(app)
app.include_router(admin.router)
app.include_router(roundtable.router)
app.include_router(matches.router)
app.include_router(ledger.router)
app.include_router(real_ledger.router)
app.include_router(settings.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"service": "alea-api", "status": "ok"}


@app.post("/auth/signup", status_code=201, tags=["auth"])
async def signup(request: SignupRequest) -> JSONResponse:
    required = {
        "url": os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL),
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
