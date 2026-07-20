from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

OutputT = TypeVar("OutputT")


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    business_idempotency_key: str = Field(min_length=1)
    input_snapshot_id: UUID | None
    postmatch_review_context_snapshot_id: UUID | None
    methodology_review_context_snapshot_id: UUID | None
    history_context_version_id: UUID | None
    lesson_set_version_id: UUID | None
    model_id: str = Field(min_length=1)
    connection_version: int = Field(ge=1)
    identity_prompt_version: int = Field(ge=1)
    core_methodology_version: int = Field(ge=1)
    phase_prompt_version: int = Field(ge=1)
    output_schema_version: int = Field(ge=1)
    tool_contract_version: int = Field(ge=1)
    generation_parameter_version: int = Field(ge=1)
    timeout_seconds: int = Field(ge=1, le=900)
    max_output_tokens: int = Field(ge=1)


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ProviderResult(BaseModel, Generic[OutputT]):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    provider_request_id: str | None
    model_id: str
    output: OutputT
    usage: Usage
    finish_reason: str | None
    latency_ms: int = Field(ge=0)


class ProviderFailure(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class BaseProvider(Protocol):
    async def nominate_matches(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def selection_debate(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def vote_matches(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def predict_score(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def debate_response(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def vote_score(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def form_bet(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def debate_bet(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def vote_bet(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def review_prediction(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...
    async def review_methodology(
        self, ctx: dict[str, Any], req: ProviderRequest
    ) -> ProviderResult[dict[str, Any]]: ...


ROLE_PREFIX = re.compile(r"(?im)^\s*(system|assistant|developer|tool)\s*:")
INJECTION_PHRASE = re.compile(r"(?i)(ignore (all |the )?(previous|prior)|忽略(以上|前文|之前))")


@dataclass(frozen=True)
class UntrustedText:
    value: str
    suspicious: bool


def isolate_untrusted_text(value: str, *, max_length: int = 20_000) -> UntrustedText:
    normalized = "".join(char for char in value if char in "\n\t" or ord(char) >= 32)
    suspicious = bool(ROLE_PREFIX.search(normalized) or INJECTION_PHRASE.search(normalized))
    normalized = ROLE_PREFIX.sub("[role-label-removed] ", normalized)[:max_length]
    return UntrustedText(
        value=f"<untrusted-data>\n{normalized}\n</untrusted-data>", suspicious=suspicious
    )
