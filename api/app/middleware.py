from __future__ import annotations

import hmac
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from http.cookies import SimpleCookie

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.security import JWTVerifier, SecurityError


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_API_PATHS = {"/v1/auth/login"}
DEFAULT_SUPABASE_URL = "https://qevyqgociclrqhglhqux.supabase.co"


@dataclass(frozen=True)
class RatePolicy:
    prefix: str
    limit: int
    window_seconds: int


DEFAULT_RATE_POLICIES = (
    RatePolicy("/auth/signup", 5, 60),
    RatePolicy("/v1/auth/login", 10, 60),
    RatePolicy("/v1/admin/providers/test", 6, 60),
    RatePolicy("/v1/admin/sync", 4, 60),
    RatePolicy("/v1/admin/roundtables", 6, 60),
    RatePolicy("/v1/images", 4, 60),
)


class SlidingWindowLimiter:
    def __init__(self, policies: tuple[RatePolicy, ...] = DEFAULT_RATE_POLICIES) -> None:
        self.policies = policies
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, path: str, identity: str, now: float | None = None) -> int | None:
        timestamp = time.monotonic() if now is None else now
        policy = next((item for item in self.policies if path.startswith(item.prefix)), None)
        if policy is None:
            return None
        key = (policy.prefix, identity)
        with self._lock:
            hits = self._hits[key]
            cutoff = timestamp - policy.window_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= policy.limit:
                return max(1, int(hits[0] + policy.window_seconds - timestamp))
            hits.append(timestamp)
        return None


def _cookie_value(raw_cookie: str, name: str) -> str | None:
    cookie = SimpleCookie()
    cookie.load(raw_cookie)
    morsel = cookie.get(name)
    return morsel.value if morsel else None


def _bearer_token(authorization: str) -> str | None:
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.casefold() != "bearer":
        return None
    value = token.strip()
    return value or None


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        *,
        verifier: JWTVerifier | None,
        allowed_origins: set[str],
        limiter: SlidingWindowLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self.verifier = verifier
        self.allowed_origins = {origin.rstrip("/") for origin in allowed_origins}
        self.limiter = limiter or SlidingWindowLimiter()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        if request.method == "OPTIONS":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        if request.method in WRITE_METHODS and request.headers.get("cookie"):
            origin = request.headers.get("origin", "").rstrip("/")
            csrf_cookie = _cookie_value(request.headers.get("cookie", ""), "csrf_token")
            csrf_header = request.headers.get("x-csrf-token")
            if origin not in self.allowed_origins or not csrf_cookie or not csrf_header:
                return self._error("csrf_validation_failed", 403, request_id)
            if not hmac.compare_digest(csrf_cookie, csrf_header):
                return self._error("csrf_validation_failed", 403, request_id)

        token = _bearer_token(request.headers.get("authorization", ""))
        if request.url.path.startswith("/v1/") and request.url.path not in PUBLIC_API_PATHS:
            if not token or self.verifier is None:
                return self._error("authentication_required", 401, request_id)
            try:
                request.state.principal = self.verifier.verify(token)
            except SecurityError:
                return self._error("invalid_access_token", 401, request_id)

        principal = getattr(request.state, "principal", None)
        identity = getattr(principal, "subject", None)
        if not identity:
            identity = request.client.host if request.client else "unknown"
        retry_after = self.limiter.check(request.url.path, str(identity))
        if retry_after is not None:
            response = self._error("rate_limit_exceeded", 429, request_id)
            response.headers["Retry-After"] = str(retry_after)
            return response

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _error(code: str, status_code: int, request_id: str) -> JSONResponse:
        response = JSONResponse(
            {"error": {"code": code, "message": "请求无法完成", "request_id": request_id}},
            status_code=status_code,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def configure_security(app: FastAPI, *, verifier: JWTVerifier | None = None) -> None:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost,http://localhost:3000")
    allowed_origins = {item.strip().rstrip("/") for item in raw_origins.split(",") if item.strip()}
    if "*" in allowed_origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must not contain a wildcard")
    if verifier is None:
        issuer = os.getenv("SUPABASE_JWT_ISSUER") or (
            f"{os.getenv('SUPABASE_URL', DEFAULT_SUPABASE_URL).rstrip('/')}/auth/v1"
        )
        verifier = JWTVerifier(
            issuer=issuer,
            audience=os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated"),
            jwks_url=os.getenv("SUPABASE_JWKS_URL"),
        )
    app.add_middleware(
        SecurityMiddleware,
        verifier=verifier,
        allowed_origins=allowed_origins,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allowed_origins),
        allow_credentials=True,
        allow_methods=sorted(WRITE_METHODS | {"GET", "OPTIONS"}),
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
