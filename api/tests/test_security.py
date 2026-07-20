from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import httpx

from app.routers.admin import _command
from app.security import (
    AuthenticatedPrincipal,
    JWTVerifier,
    SafeHttpClient,
    SecurityError,
    redact_sensitive,
    validate_outbound_url,
)
from app.secrets.envelope import EnvelopeCipher, EnvelopeError


def test_jwt_verifies_signature_expiry_issuer_and_audience() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    payload = {
        "sub": "user-1",
        "iss": "https://example.supabase.co/auth/v1",
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "email": "reader@example.com",
        "app_metadata": {"role": "admin"},
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    verifier = JWTVerifier(
        issuer=payload["iss"],
        key_resolver=lambda _: private_key.public_key(),
    )
    principal = verifier.verify(token)
    assert principal.subject == "user-1"
    assert principal.role == "admin"

    wrong_audience = JWTVerifier(
        issuer=payload["iss"],
        audience="wrong",
        key_resolver=lambda _: private_key.public_key(),
    )
    with pytest.raises(SecurityError, match="invalid_access_token"):
        wrong_audience.verify(token)


def test_redaction_removes_headers_keys_and_query_secrets() -> None:
    redacted = redact_sensitive(
        {
            "Authorization": "Bearer secret-token-value",
            "nested": "https://vendor.example/test?api_key=hidden&mode=safe",
            "message": "request used sk-secretvalue123",
        }
    )
    assert redacted["Authorization"] == "[REDACTED]"
    assert "hidden" not in redacted["nested"]
    assert "mode=safe" in redacted["nested"]
    assert "secretvalue" not in redacted["message"]


@pytest.mark.asyncio
async def test_admin_command_preserves_encrypted_envelope_for_database_gateway() -> None:
    class CaptureGateway:
        received: Mapping[str, object] | None = None

        async def command(
            self,
            operation: str,
            *,
            actor_id: str,
            request_id: str,
            payload: Mapping[str, object],
        ) -> Mapping[str, object]:
            del operation, actor_id, request_id
            self.received = payload
            return {"ok": True}

    gateway = CaptureGateway()
    encrypted = {
        "ciphertext": "aa",
        "ciphertext_nonce": "bb",
        "wrapped_dek": "cc",
        "wrapped_dek_nonce": "dd",
        "kek_version": 1,
        "secret_tail": "tail",
    }
    principal = AuthenticatedPrincipal(
        subject="00000000-0000-0000-0000-000000000001",
        role="admin",
        email=None,
        claims={},
    )

    result = await _command(
        gateway,
        "save_provider",
        principal,
        SimpleNamespace(state=SimpleNamespace(request_id="request-1")),
        {"encrypted_secret": encrypted},
    )

    assert result == {"ok": True}
    assert gateway.received == {"encrypted_secret": encrypted}


@pytest.mark.parametrize(
    "url",
    [
        "http://provider.example/v1",
        "https://127.0.0.1/v1",
        "https://169.254.169.254/latest/meta-data",
        "https://metadata.google.internal/computeMetadata/v1",
    ],
)
def test_outbound_url_rejects_ssrf_targets(url: str) -> None:
    with pytest.raises(SecurityError):
        validate_outbound_url(url, resolver=lambda *args, **kwargs: [])


def test_outbound_url_requires_allowlist_and_public_dns() -> None:
    def resolver(
        *args: object, **kwargs: object
    ) -> list[tuple[None, None, None, None, tuple[str, int]]]:
        return [(None, None, None, None, ("203.0.113.9", 443))]

    # Documentation ranges are reserved and intentionally rejected.
    with pytest.raises(SecurityError, match="outbound_address_forbidden"):
        validate_outbound_url("https://provider.example/v1", resolver=resolver)

    def public_resolver(
        *args: object, **kwargs: object
    ) -> list[tuple[None, None, None, None, tuple[str, int]]]:
        return [(None, None, None, None, ("8.8.8.8", 443))]

    assert (
        validate_outbound_url(
            "https://provider.example/v1",
            allowed_hosts={"provider.example"},
            resolver=public_resolver,
        )
        == "https://provider.example/v1"
    )


def test_outbound_url_allows_allowlisted_proxy_synthetic_dns_only_when_enabled() -> None:
    def synthetic_resolver(
        *args: object, **kwargs: object
    ) -> list[tuple[None, None, None, None, tuple[str, int]]]:
        return [(None, None, None, None, ("198.18.0.115", 443))]

    with pytest.raises(SecurityError, match="outbound_address_forbidden"):
        validate_outbound_url(
            "https://api.deepseek.com/v1",
            allowed_hosts={"api.deepseek.com"},
            resolver=synthetic_resolver,
        )

    assert (
        validate_outbound_url(
            "https://api.deepseek.com/v1",
            allowed_hosts={"api.deepseek.com"},
            resolver=synthetic_resolver,
            allow_proxy_synthetic_dns=True,
        )
        == "https://api.deepseek.com/v1"
    )

    with pytest.raises(SecurityError, match="outbound_host_not_allowlisted"):
        validate_outbound_url(
            "https://api.deepseek.com/v1",
            allowed_hosts={"other.example"},
            resolver=synthetic_resolver,
            allow_proxy_synthetic_dns=True,
        )


def test_envelope_roundtrip_tamper_aad_and_rotation() -> None:
    cipher = EnvelopeCipher({1: b"a" * 32, 2: b"b" * 32}, active_version=1)
    encrypted = cipher.encrypt("sk-live-secret", connection_id="conn-1", connection_version=3)
    assert encrypted.secret_tail == "cret"
    assert b"sk-live-secret" not in encrypted.ciphertext
    assert (
        cipher.decrypt(encrypted, connection_id="conn-1", connection_version=3) == "sk-live-secret"
    )
    rotated = cipher.rewrap(
        encrypted,
        connection_id="conn-1",
        connection_version=3,
        target_kek_version=2,
    )
    assert rotated.ciphertext == encrypted.ciphertext
    assert cipher.decrypt(rotated, connection_id="conn-1", connection_version=3) == "sk-live-secret"
    with pytest.raises(EnvelopeError, match="secret_authentication_failed"):
        cipher.decrypt(rotated, connection_id="conn-2", connection_version=3)


@pytest.mark.asyncio
async def test_safe_http_client_rechecks_redirect_type_and_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "/payload"})
        return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}")

    def public_resolver(
        *args: object, **kwargs: object
    ) -> list[tuple[None, None, None, None, tuple[str, int]]]:
        return [(None, None, None, None, ("8.8.8.8", 443))]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        client = SafeHttpClient(
            allowed_hosts={"provider.example"},
            client=transport,
            resolver=public_resolver,
            max_response_bytes=8,
        )
        assert (
            await client.get(
                "https://provider.example/redirect",
                allowed_content_types={"application/json"},
            )
            == b"{}"
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"not json",
            )
        )
    ) as transport:
        client = SafeHttpClient(
            allowed_hosts={"provider.example"},
            client=transport,
            resolver=public_resolver,
        )
        with pytest.raises(SecurityError, match="content_type"):
            await client.get(
                "https://provider.example/payload",
                allowed_content_types={"application/json"},
            )
