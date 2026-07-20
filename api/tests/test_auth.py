from __future__ import annotations

import httpx
import pytest

from app.auth import SignupFailure, SignupRequest, SupabaseAuthGateway


@pytest.mark.asyncio
async def test_signup_persists_consent_with_secret_without_returning_tokens() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/auth/v1/signup":
            return httpx.Response(200, json={"user": {"id": "user-1"}})
        if request.url.path == "/rest/v1/rpc/record_user_consent_from_signup":
            assert request.headers["authorization"] == "Bearer server-secret"
            return httpx.Response(204)
        raise AssertionError(f"unexpected request: {request.url.path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = SupabaseAuthGateway(
            url="https://project.supabase.co",
            publishable_key="public-key",
            secret_key="server-secret",
            client=client,
        )
        result = await gateway.signup(
            SignupRequest(
                email="reader@example.com",
                password="correct-horse-battery-staple",
                age_confirmed=True,
                terms_accepted=True,
            )
        )
    assert result.requires_email_confirmation
    assert [request.url.path for request in requests] == [
        "/auth/v1/signup",
        "/rest/v1/rpc/record_user_consent_from_signup",
    ]


@pytest.mark.asyncio
async def test_signup_deletes_auth_user_when_consent_write_fails() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/auth/v1/signup":
            return httpx.Response(200, json={"user": {"id": "incomplete-user"}})
        if request.url.path == "/rest/v1/rpc/record_user_consent_from_signup":
            return httpx.Response(500)
        if request.url.path == "/auth/v1/admin/users/incomplete-user":
            return httpx.Response(204)
        raise AssertionError(f"unexpected request: {request.url.path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = SupabaseAuthGateway(
            url="https://project.supabase.co",
            publishable_key="public-key",
            secret_key="server-secret",
            client=client,
        )
        with pytest.raises(SignupFailure, match="consent_persistence_failed"):
            await gateway.signup(
                SignupRequest(
                    email="reader@example.com",
                    password="correct-horse-battery-staple",
                    age_confirmed=True,
                    terms_accepted=True,
                )
            )
    assert paths[-1] == "/auth/v1/admin/users/incomplete-user"


@pytest.mark.asyncio
async def test_signup_rejects_missing_consent_before_network() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = SupabaseAuthGateway(
            url="https://project.supabase.co",
            publishable_key="public-key",
            secret_key="server-secret",
            client=client,
        )
        with pytest.raises(SignupFailure, match="consent_required"):
            await gateway.signup(
                SignupRequest(
                    email="reader@example.com",
                    password="correct-horse-battery-staple",
                    age_confirmed=False,
                    terms_accepted=True,
                )
            )
    assert not called
