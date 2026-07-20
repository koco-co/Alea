from __future__ import annotations

import json
from typing import Any, Final

from app.providers.cli_executor import execute_cli_phase
from app.providers.contract import ProviderRequest, ProviderResult


BUSINESS_METHODS: Final[tuple[str, ...]] = (
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
    if phase not in BUSINESS_METHODS:
        raise ValueError("unknown_cli_provider_phase")
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


class CliProvider:
    """Provider contract backed by an administrator-configured local CLI path."""

    def __init__(self, *, runtime_key: str, executable_path: str) -> None:
        self.runtime_key = runtime_key
        self.executable_path = executable_path

    async def _execute(
        self,
        phase: str,
        ctx: dict[str, Any],
        req: ProviderRequest,
    ) -> ProviderResult[dict[str, Any]]:
        result = await execute_cli_phase(
            runtime_key=self.runtime_key,
            executable_path=self.executable_path,
            model_id=req.model_id,
            prompt=(
                "You are an Alea football analysis provider. Return only the requested "
                "structured result. Never use tools, commands, files, MCP, or the web.\n"
                f"Phase: {phase}\nContext JSON: "
                f"{json.dumps(ctx, ensure_ascii=False, separators=(',', ':'), default=str)}"
            ),
            output_schema=phase_schema(phase),
            timeout_seconds=req.timeout_seconds,
        )
        return ProviderResult(
            request_id=req.request_id,
            provider_request_id=result.execution_id,
            model_id=req.model_id,
            output=result.output,
            usage=result.usage,
            finish_reason="stop",
            latency_ms=result.latency_ms,
        )


def _install_business_methods() -> None:
    async def invoke(
        self: CliProvider,
        ctx: dict[str, Any],
        req: ProviderRequest,
        *,
        method: str,
    ) -> ProviderResult[dict[str, Any]]:
        return await self._execute(method, ctx, req)

    for method_name in BUSINESS_METHODS:
        setattr(
            CliProvider,
            method_name,
            lambda self, ctx, req, method=method_name: invoke(self, ctx, req, method=method),
        )


_install_business_methods()
