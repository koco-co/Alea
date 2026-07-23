from __future__ import annotations

import json
from collections.abc import Mapping
from uuid import uuid4

import httpx
import pytest

from app.providers.anthropic import AnthropicProvider
from app.providers.catalog import API_PROVIDER_CATALOG, ApiProviderDefinition
from app.providers.contract import ProviderFailure, ProviderRequest
from app.providers.google import GoogleProvider
from app.providers.openai import OpenAIProvider
from app.providers.openai_compat import BUSINESS_METHODS, OpenAICompatProvider, _object_output


@pytest.fixture()
def provider_request() -> ProviderRequest:
    return ProviderRequest(
        request_id=uuid4(),
        business_idempotency_key="api-contract-test",
        input_snapshot_id=None,
        postmatch_review_context_snapshot_id=None,
        methodology_review_context_snapshot_id=None,
        history_context_version_id=None,
        lesson_set_version_id=None,
        model_id="contract-model",
        connection_version=1,
        identity_prompt_version=1,
        core_methodology_version=1,
        phase_prompt_version=1,
        output_schema_version=1,
        tool_contract_version=1,
        generation_parameter_version=1,
        timeout_seconds=5,
        max_output_tokens=300,
    )


def _schema(method: str) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["phase", "payload", "confidence"],
        "properties": {
            "phase": {"type": "string", "const": method},
            "payload": {
                "type": "object",
                "additionalProperties": False,
                "required": ["summary"],
                "properties": {"summary": {"type": "string", "minLength": 1}},
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _transport(definition: ApiProviderDefinition, method: str) -> httpx.MockTransport:
    output = {"phase": method, "payload": {"summary": "ok"}, "confidence": 0.6}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        if definition.adapter != "google":
            assert "contract-secret" not in str(request.url)
        if definition.adapter in {"openai", "openai_compat"}:
            body: Mapping[str, object] = {
                "id": "request-openai",
                "model": "contract-model",
                "choices": [
                    {
                        "message": {"content": json.dumps(output)},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            }
        elif definition.adapter == "anthropic":
            body = {
                "id": "request-anthropic",
                "model": "contract-model",
                "content": [{"type": "text", "text": json.dumps(output)}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "stop_reason": "end_turn",
            }
        else:
            body = {
                "responseId": "request-google",
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(output)}],
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "totalTokenCount": 15,
                },
            }
        return httpx.Response(200, json=body, headers={"x-request-id": "contract-request"})

    return httpx.MockTransport(handler)


def _provider(
    definition: ApiProviderDefinition,
    client: httpx.AsyncClient,
) -> OpenAICompatProvider | AnthropicProvider | GoogleProvider:
    common = {
        "api_key": "contract-secret",
        "base_url": (
            definition.default_base_url
            if definition.default_base_url
            else "https://compatible.example/v1"
        ),
        "client": client,
    }
    if definition.adapter == "openai":
        return OpenAIProvider(**common)
    if definition.adapter == "anthropic":
        return AnthropicProvider(**common)
    if definition.adapter == "google":
        return GoogleProvider(**common)
    return OpenAICompatProvider(
        **common,
        requires_api_key=definition.requires_api_key,
        allow_local_http=definition.allow_local_http,
        supports_json_schema=definition.supports_json_schema,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("definition", API_PROVIDER_CATALOG, ids=lambda item: item.key)
@pytest.mark.parametrize("method", BUSINESS_METHODS)
async def test_every_api_catalog_entry_satisfies_all_eleven_provider_methods(
    definition: ApiProviderDefinition,
    method: str,
    provider_request: ProviderRequest,
) -> None:
    transport = _transport(definition, method)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = _provider(definition, client)
        result = await getattr(provider, method)(
            {"output_schema": _schema(method)},
            provider_request,
        )

    assert result.output["phase"] == method
    assert result.usage.total_tokens == 15
    assert result.provider_request_id


@pytest.mark.asyncio
async def test_native_adapter_rejects_schema_invalid_output(
    provider_request: ProviderRequest,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": '{"phase":"wrong"}'}],
                "usage": {},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = AnthropicProvider(api_key="contract-secret", client=client)
        with pytest.raises(ProviderFailure, match="schema validation") as captured:
            await provider.predict_score(
                {"output_schema": _schema("predict_score")},
                provider_request,
            )
    assert captured.value.code == "schema_validation_failed"


@pytest.mark.asyncio
async def test_json_object_fallback_includes_exact_schema_instruction(
    provider_request: ProviderRequest,
) -> None:
    expected_schema = _schema("predict_score")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        instruction = body["messages"][0]
        assert instruction["role"] == "system"
        assert "do not move top-level fields into payload" in instruction["content"]
        assert (
            json.dumps(
                expected_schema,
                ensure_ascii=False,
                sort_keys=True,
            )
            in instruction["content"]
        )
        return httpx.Response(
            200,
            json={
                "id": "fallback-request",
                "model": "deepseek-chat",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "phase": "predict_score",
                                    "payload": {"summary": "ok"},
                                    "confidence": 0.5,
                                }
                            )
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatProvider(
            api_key="contract-secret",
            base_url="https://api.deepseek.com",
            client=client,
            supports_json_schema=False,
        )
        result = await provider.predict_score(
            {"output_schema": expected_schema},
            provider_request,
        )

    assert result.output["confidence"] == 0.5


def test_json_object_parser_accepts_a_single_json_code_fence() -> None:
    assert _object_output('```json\n{"summary":"ok"}\n```') == {"summary": "ok"}
