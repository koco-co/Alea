from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import RatePolicy, SecurityMiddleware, SlidingWindowLimiter, configure_security


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        SecurityMiddleware,
        verifier=None,
        allowed_origins={"http://localhost:3000"},
        limiter=SlidingWindowLimiter((RatePolicy("/expensive", 1, 60),)),
    )

    @app.post("/write")
    async def write() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/expensive")
    async def expensive() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_cookie_write_requires_matching_origin_and_csrf() -> None:
    client = TestClient(make_app())
    client.cookies.set("csrf_token", "same")
    denied = client.post("/write")
    assert denied.status_code == 403
    accepted = client.post(
        "/write",
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": "same"},
    )
    assert accepted.status_code == 200
    assert accepted.headers["x-request-id"]


def test_high_cost_route_is_rate_limited() -> None:
    client = TestClient(make_app())
    assert client.get("/expensive").status_code == 200
    assert client.get("/expensive").status_code == 429


def test_cors_headers_are_present_on_security_errors() -> None:
    app = FastAPI()
    configure_security(app, verifier=None)
    response = TestClient(app).get(
        "/v1/private",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
