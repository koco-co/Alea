from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar
from urllib.parse import urlsplit

import httpx
from jsonschema import ValidationError, validate

from app.providers.contract import ProviderFailure, ProviderRequest, ProviderResult, Usage


BUSINESS_METHODS = (
    "nominate_matches",
    "selection_debate",
    "vote_matches",
    "predict_score",
    "debate_response",
    "vote_score",
    "form_bet",
    "debate_bet",
    "vote_bet",
    "review_prediction",
    "review_methodology",
)


class HTTPProvider:
    """Shared, injectable HTTP boundary for native and compatible providers."""

    provider_name: ClassVar[str] = "provider"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
        requires_api_key: bool = True,
        allow_local_http: bool = False,
        supports_json_schema: bool = True,
    ) -> None:
        if requires_api_key and not api_key.strip():
            raise ValueError("api_key must not be empty")
        _validate_provider_base_url(base_url, allow_local_http=allow_local_http)
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client
        self._default_headers = dict(default_headers or {})
        self._requires_api_key = requires_api_key
        self._supports_json_schema = supports_json_schema

    async def _post(
        self,
        path: str,
        *,
        req: ProviderRequest,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
    ) -> tuple[httpx.Response, int]:
        started = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            response = await client.post(
                f"{self.base_url}/{path.lstrip('/')}",
                json=dict(payload),
                headers={**self._default_headers, **headers},
                params=params,
                timeout=req.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "provider request timed out", retryable=True) from exc
        except httpx.TransportError as exc:
            raise ProviderFailure(
                "transport_error", "provider transport failed", retryable=True
            ) from exc
        finally:
            if owns_client:
                await client.aclose()
        latency_ms = max(0, round((time.perf_counter() - started) * 1000))
        _raise_for_status(response, self.provider_name)
        return response, latency_ms


class OpenAICompatProvider(HTTPProvider):
    """Adapter for OpenAI-compatible chat-completions APIs.

    DeepSeek, Kimi and Qwen connections use this class with their approved HTTPS
    endpoint. Connection allow-list enforcement belongs to configuration loading,
    before a provider object is constructed.
    """

    provider_name = "openai_compat"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
        requires_api_key: bool = True,
        allow_local_http: bool = False,
        supports_json_schema: bool = True,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            client=client,
            default_headers=default_headers,
            requires_api_key=requires_api_key,
            allow_local_http=allow_local_http,
            supports_json_schema=supports_json_schema,
        )

    async def _invoke(
        self, method: str, ctx: Mapping[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        response, latency_ms = await self._post(
            "/chat/completions",
            req=req,
            headers={
                **({"Authorization": f"Bearer {self._api_key}"} if self._api_key.strip() else {}),
                "Content-Type": "application/json",
                "Idempotency-Key": req.business_idempotency_key,
                "X-Request-ID": str(req.request_id),
            },
            payload={
                "model": req.model_id,
                "messages": _messages(
                    ctx,
                    method,
                    include_schema_instruction=not self._supports_json_schema,
                ),
                "max_tokens": req.max_output_tokens,
                "response_format": _openai_response_format(
                    ctx, supports_json_schema=self._supports_json_schema
                ),
            },
        )
        body = _json_body(response)
        choices = _list(body.get("choices"), "choices")
        if not choices:
            raise ProviderFailure("empty_response", "provider returned no choices", retryable=False)
        choice = _mapping(choices[0], "choices[0]")
        message = _mapping(choice.get("message"), "choices[0].message")
        output = _object_output(message.get("content"))
        _validate_output_schema(output, ctx)
        usage_body = _mapping(body.get("usage", {}), "usage")
        return ProviderResult(
            request_id=req.request_id,
            provider_request_id=_header_or_string(response, body.get("id")),
            model_id=str(body.get("model") or req.model_id),
            output=output,
            usage=Usage(
                input_tokens=_optional_int(usage_body.get("prompt_tokens")),
                output_tokens=_optional_int(usage_body.get("completion_tokens")),
                total_tokens=_optional_int(usage_body.get("total_tokens")),
            ),
            finish_reason=_optional_string(choice.get("finish_reason")),
            latency_ms=latency_ms,
        )


def _install_business_methods() -> None:
    async def invoke(
        self: OpenAICompatProvider,
        ctx: Mapping[str, Any],
        req: ProviderRequest,
        *,
        _method: str,
    ) -> ProviderResult[dict[str, Any]]:
        return await self._invoke(_method, ctx, req)

    for method in BUSINESS_METHODS:
        setattr(
            OpenAICompatProvider,
            method,
            lambda self, ctx, req, _method=method: invoke(self, ctx, req, _method=_method),
        )


def _validate_provider_base_url(base_url: str, *, allow_local_http: bool) -> None:
    parsed = urlsplit(base_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("provider base_url contains forbidden URL components")
    if parsed.scheme == "https" and parsed.hostname:
        return
    local_hosts = {"127.0.0.1", "localhost", "::1", "host.docker.internal"}
    if (
        allow_local_http
        and parsed.scheme == "http"
        and parsed.hostname is not None
        and parsed.hostname.casefold() in local_hosts
    ):
        return
    raise ValueError("provider base_url must use HTTPS or an approved local HTTP host")


def _messages(
    ctx: Mapping[str, Any],
    method: str,
    *,
    include_schema_instruction: bool = False,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    schema = ctx.get("output_schema")
    if include_schema_instruction and isinstance(schema, Mapping):
        messages.append(
            {
                "role": "system",
                "content": (
                    "Return exactly one JSON object and no Markdown or commentary. "
                    "The JSON object must validate against this exact JSON Schema. "
                    "Keep every required field at the schema-defined level; do not "
                    "move top-level fields into payload:\n"
                    + json.dumps(dict(schema), ensure_ascii=False, sort_keys=True)
                ),
            }
        )
    supplied = ctx.get("messages")
    if isinstance(supplied, Sequence) and not isinstance(supplied, (str, bytes, bytearray)):
        for index, item in enumerate(supplied):
            mapping = _mapping(item, f"messages[{index}]")
            role = mapping.get("role")
            content = mapping.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(content, str):
                raise ProviderFailure("invalid_context", "invalid prompt message", retryable=False)
            messages.append({"role": role, "content": content})
        return messages
    messages.append(
        {
            "role": "user",
            "content": json.dumps(
                {"business_method": method, "context": dict(ctx)},
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
        }
    )
    return messages


def _openai_response_format(
    ctx: Mapping[str, Any], *, supports_json_schema: bool = True
) -> dict[str, Any]:
    schema = ctx.get("output_schema")
    if supports_json_schema and isinstance(schema, Mapping):
        return {
            "type": "json_schema",
            "json_schema": {"name": "alea_phase_result", "strict": True, "schema": dict(schema)},
        }
    return {"type": "json_object"}


def _object_output(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        raise ProviderFailure("invalid_json", "provider content is not JSON", retryable=False)
    candidates = [value.strip()]
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value.strip(), re.IGNORECASE | re.DOTALL)
    if fenced is not None:
        candidates.append(fenced.group(1).strip())
    decoded: Any = None
    for candidate in candidates:
        try:
            decoded = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if decoded is None:
        raise ProviderFailure("invalid_json", "provider returned invalid JSON", retryable=False)
    if not isinstance(decoded, dict):
        raise ProviderFailure(
            "invalid_json", "provider JSON root must be an object", retryable=False
        )
    return decoded


def _validate_output_schema(output: Mapping[str, Any], ctx: Mapping[str, Any]) -> None:
    schema = ctx.get("output_schema")
    if not isinstance(schema, Mapping):
        return
    try:
        validate(instance=dict(output), schema=dict(schema))
    except ValidationError as exc:
        raise ProviderFailure(
            "schema_validation_failed",
            "provider output failed schema validation",
            retryable=False,
        ) from exc


def _json_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise ProviderFailure(
            "invalid_json", "provider returned invalid JSON", retryable=False
        ) from exc
    return dict(_mapping(body, "response"))


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderFailure(
            "invalid_response", f"provider field {field} is invalid", retryable=False
        )
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderFailure(
            "invalid_response", f"provider field {field} is invalid", retryable=False
        )
    return value


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _header_or_string(response: httpx.Response, fallback: Any) -> str | None:
    request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
    return request_id or _optional_string(fallback)


def _raise_for_status(response: httpx.Response, provider_name: str) -> None:
    if response.is_success:
        return
    status = response.status_code
    if status in {408, 409, 429} or status >= 500:
        code, retryable = (
            ("rate_limited", True) if status == 429 else ("provider_unavailable", True)
        )
    elif status in {401, 403}:
        code, retryable = "authentication_failed", False
    else:
        code, retryable = "provider_rejected", False
    raise ProviderFailure(
        code, f"{provider_name} request failed with HTTP {status}", retryable=retryable
    )


_install_business_methods()

OpenAICompatibleProvider = OpenAICompatProvider
