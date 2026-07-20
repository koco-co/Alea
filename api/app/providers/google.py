from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx

from app.providers.contract import ProviderFailure, ProviderRequest, ProviderResult, Usage
from app.providers.openai_compat import (
    BUSINESS_METHODS,
    HTTPProvider,
    _json_body,
    _mapping,
    _messages,
    _object_output,
    _optional_int,
    _optional_string,
    _validate_output_schema,
)


class GoogleProvider(HTTPProvider):
    provider_name = "google"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, client=client)

    async def _invoke(
        self, method: str, ctx: Mapping[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        messages = _messages(ctx, method)
        system_parts = [item["content"] for item in messages if item["role"] == "system"]
        contents = [
            {
                "role": "model" if item["role"] == "assistant" else "user",
                "parts": [{"text": item["content"]}],
            }
            for item in messages
            if item["role"] != "system"
        ]
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": req.max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        schema = ctx.get("output_schema")
        if isinstance(schema, Mapping):
            payload["generationConfig"]["responseJsonSchema"] = dict(schema)
        response, latency_ms = await self._post(
            f"/models/{quote(req.model_id, safe='')}:generateContent",
            req=req,
            headers={"content-type": "application/json", "x-request-id": str(req.request_id)},
            params={"key": self._api_key},
            payload=payload,
        )
        body = _json_body(response)
        candidates = body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderFailure(
                "empty_response", "provider returned no candidates", retryable=False
            )
        candidate = _mapping(candidates[0], "candidates[0]")
        content = _mapping(candidate.get("content"), "candidates[0].content")
        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            raise ProviderFailure(
                "empty_response", "provider returned no content parts", retryable=False
            )
        part = _mapping(parts[0], "candidates[0].content.parts[0]")
        output = _object_output(
            part.get("functionCall", {}).get("args")
            if isinstance(part.get("functionCall"), Mapping)
            else part.get("text")
        )
        _validate_output_schema(output, ctx)
        usage = _mapping(body.get("usageMetadata", {}), "usageMetadata")
        return ProviderResult(
            request_id=req.request_id,
            provider_request_id=response.headers.get("x-request-id")
            or _optional_string(body.get("responseId")),
            model_id=req.model_id,
            output=output,
            usage=Usage(
                input_tokens=_optional_int(usage.get("promptTokenCount")),
                output_tokens=_optional_int(usage.get("candidatesTokenCount")),
                total_tokens=_optional_int(usage.get("totalTokenCount")),
            ),
            finish_reason=_optional_string(candidate.get("finishReason")),
            latency_ms=latency_ms,
        )


def _install_business_methods() -> None:
    async def invoke(
        self: GoogleProvider,
        ctx: Mapping[str, Any],
        req: ProviderRequest,
        *,
        _method: str,
    ) -> ProviderResult[dict[str, Any]]:
        return await self._invoke(_method, ctx, req)

    for method in BUSINESS_METHODS:
        setattr(
            GoogleProvider,
            method,
            lambda self, ctx, req, _method=method: invoke(self, ctx, req, _method=_method),
        )


_install_business_methods()

GoogleAdapter = GoogleProvider
