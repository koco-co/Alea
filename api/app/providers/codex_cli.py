from __future__ import annotations

import json
import time
from typing import Any, Final

import httpx

from app.providers.contract import ProviderFailure, ProviderRequest, ProviderResult, Usage


PHASES: Final[tuple[str, ...]] = (
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


def phase_schema(phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError("unknown Codex provider phase")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["phase", "payload", "confidence"],
        "properties": {
            "phase": {"type": "string", "const": phase},
            "payload": {
                "type": "object",
                "additionalProperties": False,
                "required": ["summary"],
                "properties": {"summary": {"type": "string"}},
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


class CodexCliProvider:
    """BaseProvider adapter for the isolated Alea Codex runner."""

    def __init__(
        self,
        *,
        runner_url: str,
        runner_token: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.runner_url = runner_url.rstrip("/")
        self.runner_token = runner_token
        self.client = client or httpx.AsyncClient(timeout=920)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _execute(
        self, phase: str, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        started = time.monotonic()
        response = await self.client.post(
            f"{self.runner_url}/internal/v1/execute",
            headers={"X-Alea-Runner-Token": self.runner_token},
            json={
                "request_id": str(req.request_id),
                "phase": phase,
                "model": req.model_id,
                "timeout_seconds": req.timeout_seconds,
                "prompt": (
                    "You are an Alea football analysis provider. Return only the requested "
                    "structured result. Never use tools, commands, files, MCP, or the web.\n"
                    f"Phase: {phase}\nContext JSON: "
                    f"{json.dumps(ctx, ensure_ascii=False, separators=(',', ':'))}"
                ),
                "output_schema": phase_schema(phase),
            },
        )
        if response.status_code != 200:
            code = response.json().get("detail", "codex_runner_unavailable")
            raise ProviderFailure(str(code), "Codex runner request failed", retryable=True)
        body = response.json()
        return ProviderResult(
            request_id=req.request_id,
            provider_request_id=body["execution_id"],
            model_id=req.model_id,
            output=body["output"],
            usage=Usage.model_validate(body.get("usage", {})),
            finish_reason="stop",
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def nominate_matches(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("nominate_matches", ctx, req)

    async def selection_debate(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("selection_debate", ctx, req)

    async def vote_matches(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("vote_matches", ctx, req)

    async def predict_score(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("predict_score", ctx, req)

    async def debate_response(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("debate_response", ctx, req)

    async def vote_score(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("vote_score", ctx, req)

    async def form_bet(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("form_bet", ctx, req)

    async def debate_bet(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("debate_bet", ctx, req)

    async def vote_bet(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("vote_bet", ctx, req)

    async def review_prediction(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("review_prediction", ctx, req)

    async def review_methodology(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute("review_methodology", ctx, req)
