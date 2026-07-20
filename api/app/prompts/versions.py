from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence


class PromptArtifactKind(StrEnum):
    IDENTITY = "identity"
    CORE_METHODOLOGY = "core_methodology"
    PHASE_INSTRUCTION = "phase_instruction"
    OUTPUT_SCHEMA = "output_schema"
    TOOL_CONTRACT = "tool_contract"


@dataclass(frozen=True, slots=True)
class PromptVersion:
    version_id: str
    key: str
    version: int
    kind: PromptArtifactKind
    content: Any
    published_at: datetime
    content_hash: str

    def __post_init__(self) -> None:
        if not self.version_id.strip() or not self.key.strip() or not self.content_hash.strip():
            raise ValueError("prompt version identifiers must not be empty")
        if self.version < 1:
            raise ValueError("prompt version must be positive")
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")


class PromptVersionRepository(Protocol):
    async def get_prompt_version(self, *, key: str, version: int) -> Mapping[str, Any] | None: ...


class PromptVersionNotFound(LookupError):
    pass


class PromptVersionMismatch(ValueError):
    pass


@dataclass(slots=True)
class PromptVersionLoader:
    repository: PromptVersionRepository

    async def load(
        self,
        *,
        key: str,
        version: int,
        expected_kind: PromptArtifactKind | None = None,
    ) -> PromptVersion:
        if not key.strip() or version < 1:
            raise ValueError("key must be non-empty and version must be positive")
        row = await self.repository.get_prompt_version(key=key, version=version)
        if row is None:
            raise PromptVersionNotFound(f"prompt version not found: {key}@{version}")
        artifact = _coerce_prompt_version(row)
        if artifact.key != key or artifact.version != version:
            raise PromptVersionMismatch("repository returned a different prompt key or version")
        if expected_kind is not None and artifact.kind is not expected_kind:
            raise PromptVersionMismatch(
                f"{key}@{version} is {artifact.kind.value}, expected {expected_kind.value}"
            )
        return artifact

    async def load_many(
        self,
        selections: Sequence[tuple[str, int, PromptArtifactKind]],
    ) -> Mapping[str, PromptVersion]:
        loaded: dict[str, PromptVersion] = {}
        for key, version, kind in selections:
            if key in loaded:
                raise ValueError(f"duplicate prompt key: {key}")
            loaded[key] = await self.load(key=key, version=version, expected_kind=kind)
        return MappingProxyType(loaded)


@dataclass(slots=True)
class InMemoryPromptVersionRepository:
    """Small deterministic repository useful for Gate 0 and contract tests."""

    rows: Mapping[tuple[str, int], Mapping[str, Any]]

    async def get_prompt_version(self, *, key: str, version: int) -> Mapping[str, Any] | None:
        return self.rows.get((key, version))


def _coerce_prompt_version(row: Mapping[str, Any]) -> PromptVersion:
    try:
        kind = PromptArtifactKind(str(row["kind"]))
        published_at = row["published_at"]
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if not isinstance(published_at, datetime):
            raise TypeError("published_at must be a datetime")
        return PromptVersion(
            version_id=str(row["version_id"]),
            key=str(row["key"]),
            version=int(row["version"]),
            kind=kind,
            content=row["content"],
            published_at=published_at.astimezone(UTC),
            content_hash=str(row["content_hash"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PromptVersionMismatch("invalid prompt version projection") from exc
