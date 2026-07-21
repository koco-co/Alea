from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.routers import admin
from app.secrets.envelope import EncryptedSecret, EnvelopeEncryption
from app.security import AuthenticatedPrincipal


class ProviderGateway:
    def __init__(self, secret_record: Mapping[str, Any] | None = None) -> None:
        self.secret_record = secret_record
        self.command_operation: str | None = None
        self.command_payload: Mapping[str, Any] | None = None

    async def query(
        self,
        operation: str,
        *,
        actor_id: str,
        params: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        del actor_id, params
        assert operation == "provider_secret"
        return self.secret_record

    async def command(
        self,
        operation: str,
        *,
        actor_id: str,
        request_id: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        del actor_id, request_id
        self.command_operation = operation
        self.command_payload = payload
        return {
            "provider_id": str(uuid4()),
            "connection_id": payload.get("connection_id"),
        }


@pytest.fixture()
def admin_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="00000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@example.test",
        claims={},
    )


def _encrypted_record(secret: str, connection_id: str, version: int) -> dict[str, Any]:
    encrypted = EnvelopeEncryption().encrypt(
        secret,
        connection_id=connection_id,
        connection_version=version,
    )
    return {
        key: value.hex() if isinstance(value, bytes) else value
        for key, value in encrypted.as_record().items()
    }


@pytest.mark.asyncio
async def test_saved_api_secret_can_be_reused_without_reaching_the_browser(
    monkeypatch: pytest.MonkeyPatch,
    admin_principal: AuthenticatedPrincipal,
) -> None:
    monkeypatch.setenv("PROVIDER_KEK_V1", "11" * 32)
    old_connection_id = str(uuid4())
    gateway = ProviderGateway(_encrypted_record("deepseek-secret", old_connection_id, 3))

    resolved = await admin._load_provider_api_key(
        gateway,
        admin_principal,
        connection_id=UUID(old_connection_id),
        connection_version=3,
        provider_key="deepseek",
    )

    assert resolved == "deepseek-secret"


@pytest.mark.asyncio
async def test_save_provider_reencrypts_inherited_secret_for_new_version(
    monkeypatch: pytest.MonkeyPatch,
    admin_principal: AuthenticatedPrincipal,
) -> None:
    monkeypatch.setenv("PROVIDER_KEK_V1", "22" * 32)
    old_connection_id = str(uuid4())
    new_connection_id = uuid4()
    gateway = ProviderGateway(_encrypted_record("deepseek-secret", old_connection_id, 1))

    async def passed_test(
        body: admin.TestApiProviderRequest,
        *,
        api_key: str | None = None,
    ) -> Mapping[str, Any]:
        assert body.provider_key == "deepseek"
        assert api_key == "deepseek-secret"
        return {"status": "passed", "error_code": None, "latency_ms": 8}

    monkeypatch.setattr(admin, "_test_api_configuration", passed_test)
    body = admin.SaveProviderRequest(
        provider_key="deepseek",
        connection_id=new_connection_id,
        connection_version=2,
        display_name="DeepSeek",
        execution_mode="api",
        protocol="openai_compat",
        api_url="https://api.deepseek.com",
        model_id="deepseek-chat",
        allowed_api_domains=["api.deepseek.com"],
        previous_connection_id=old_connection_id,
        previous_connection_version=1,
        enabled=True,
    )

    await admin.save_provider(
        new_connection_id,
        body,
        SimpleNamespace(state=SimpleNamespace(request_id="request-1")),
        admin_principal,
        gateway,
    )

    assert gateway.command_operation == "save_provider"
    assert gateway.command_payload is not None
    assert "api_key" not in gateway.command_payload
    envelope_record = gateway.command_payload["encrypted_secret"]
    envelope = EncryptedSecret(
        ciphertext=bytes.fromhex(envelope_record["ciphertext"]),
        ciphertext_nonce=bytes.fromhex(envelope_record["ciphertext_nonce"]),
        wrapped_dek=bytes.fromhex(envelope_record["wrapped_dek"]),
        wrapped_dek_nonce=bytes.fromhex(envelope_record["wrapped_dek_nonce"]),
        kek_version=envelope_record["kek_version"],
        secret_tail=envelope_record["secret_tail"],
    )
    assert (
        EnvelopeEncryption().decrypt(
            envelope,
            connection_id=new_connection_id,
            connection_version=2,
        )
        == "deepseek-secret"
    )


def test_api_provider_validation_rejects_private_and_incomplete_secret_references() -> None:
    with pytest.raises(HTTPException, match="invalid_api_provider_url"):
        admin._validate_api_provider_request(
            admin.SaveProviderRequest(
                provider_key="openai_compatible",
                connection_id=uuid4(),
                connection_version=1,
                display_name="Private endpoint",
                execution_mode="api",
                protocol="openai_compat",
                api_url="https://127.0.0.1/v1",
                model_id="model-1",
                allowed_api_domains=["127.0.0.1"],
                api_key="secret",
            )
        )

    with pytest.raises(HTTPException, match="incomplete_previous_connection_reference"):
        admin._validate_api_provider_request(
            admin.SaveProviderRequest(
                provider_key="deepseek",
                connection_id=uuid4(),
                connection_version=2,
                display_name="DeepSeek",
                execution_mode="api",
                protocol="openai_compat",
                api_url="https://api.deepseek.com",
                model_id="deepseek-chat",
                allowed_api_domains=["api.deepseek.com"],
                previous_connection_id=uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_cli_probe_runs_a_real_structured_schema_test(
    monkeypatch: pytest.MonkeyPatch,
    admin_principal: AuthenticatedPrincipal,
) -> None:
    async def probe(*args: Any, **kwargs: Any) -> SimpleNamespace:
        del args, kwargs
        return SimpleNamespace(
            runtime_key="codex",
            executable_path="/opt/homebrew/bin/codex",
            version="codex-cli test",
            auth_status="authenticated",
            models=("gpt-test",),
            status="passed",
            error_code=None,
        )

    class FakeCliProvider:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["runtime_key"] == "codex"

        async def predict_score(self, context: Mapping[str, Any], request: Any) -> SimpleNamespace:
            assert context["source"] == "admin_connection_test"
            assert request.model_id == "gpt-test"
            return SimpleNamespace(latency_ms=42)

    monkeypatch.setattr(admin, "probe_cli_runtime", probe)
    monkeypatch.setattr(admin, "CliProvider", FakeCliProvider)
    result = await admin.probe_provider_cli_runtime(
        admin.ProbeCliRuntimeRequest(
            runtime_key="codex",
            executable_path="/opt/homebrew/bin/codex",
            model_id="gpt-test",
        ),
        admin_principal,
    )

    assert result["status"] == "passed"
    assert result["schema_status"] == "passed"
    assert result["latency_ms"] == 42


@pytest.mark.asyncio
async def test_clear_secret_and_retire_provider_use_audited_commands(
    admin_principal: AuthenticatedPrincipal,
) -> None:
    gateway = ProviderGateway()
    request = SimpleNamespace(state=SimpleNamespace(request_id="request-2"))
    connection_id = uuid4()
    provider_id = uuid4()

    await admin.clear_provider_secret(connection_id, request, admin_principal, gateway)
    assert gateway.command_operation == "clear_provider_secret"
    assert gateway.command_payload == {"connection_id": str(connection_id)}

    await admin.retire_provider(provider_id, request, admin_principal, gateway)
    assert gateway.command_operation == "retire_provider"
    assert gateway.command_payload == {"provider_id": str(provider_id)}
