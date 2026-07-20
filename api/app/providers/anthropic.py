from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from app.providers.contract import ProviderRequest, ProviderResult, Usage
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


class AnthropicProvider(HTTPProvider):
    provider_name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        anthropic_version: str = "2023-06-01",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, client=client)
        self.anthropic_version = anthropic_version

    async def _invoke(
        self, method: str, ctx: Mapping[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        messages = _messages(ctx, method)
        system_parts = [item["content"] for item in messages if item["role"] == "system"]
        api_messages = [item for item in messages if item["role"] != "system"]
        response, latency_ms = await self._post(
            "/messages",
            req=req,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": self.anthropic_version,
                "content-type": "application/json",
                "x-request-id": str(req.request_id),
            },
            payload={
                "model": req.model_id,
                "max_tokens": req.max_output_tokens,
                "system": "\n\n".join(system_parts),
                "messages": api_messages,
            },
        )
        body = _json_body(response)
        content = body.get("content")
        if not isinstance(content, list) or not content:
            from app.providers.contract import ProviderFailure

            raise ProviderFailure("empty_response", "provider returned no content", retryable=False)
        block = _mapping(content[0], "content[0]")
        output = _object_output(
            block.get("input") if block.get("type") == "tool_use" else block.get("text")
        )
        _validate_output_schema(output, ctx)
        usage = _mapping(body.get("usage", {}), "usage")
        input_tokens = _optional_int(usage.get("input_tokens"))
        output_tokens = _optional_int(usage.get("output_tokens"))
        total = (
            None if input_tokens is None or output_tokens is None else input_tokens + output_tokens
        )
        return ProviderResult(
            request_id=req.request_id,
            provider_request_id=response.headers.get("request-id")
            or _optional_string(body.get("id")),
            model_id=str(body.get("model") or req.model_id),
            output=output,
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total),
            finish_reason=_optional_string(body.get("stop_reason")),
            latency_ms=latency_ms,
        )


def _install_business_methods() -> None:
    async def invoke(
        self: AnthropicProvider,
        ctx: Mapping[str, Any],
        req: ProviderRequest,
        *,
        _method: str,
    ) -> ProviderResult[dict[str, Any]]:
        return await self._invoke(_method, ctx, req)

    for method in BUSINESS_METHODS:
        setattr(
            AnthropicProvider,
            method,
            lambda self, ctx, req, _method=method: invoke(self, ctx, req, _method=_method),
        )


_install_business_methods()

AnthropicAdapter = AnthropicProvider
