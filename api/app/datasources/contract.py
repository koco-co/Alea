from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Generic, Mapping, Protocol, Sequence, TypeVar


T = TypeVar("T")


class DeploymentMode(StrEnum):
    GATE0_LOCAL = "gate0_local"
    PERSONAL = "personal"
    STAGING = "staging"
    PRODUCTION = "production"


class FactState(StrEnum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    CONFLICT = "conflict"


class TrustLevel(StrEnum):
    AUTHORITATIVE = "authoritative"
    LICENSED = "licensed"
    ADMIN_IMPORT = "admin_import"
    FIXTURE = "fixture"
    CANDIDATE = "candidate"


TRUST_ORDER: Mapping[TrustLevel, int] = MappingProxyType(
    {
        TrustLevel.AUTHORITATIVE: 50,
        TrustLevel.LICENSED: 40,
        TrustLevel.ADMIN_IMPORT: 30,
        TrustLevel.FIXTURE: 20,
        TrustLevel.CANDIDATE: 10,
    }
)


@dataclass(frozen=True, slots=True)
class SourcedFact(Generic[T]):
    """A business fact with the provenance required by TECH 5.3."""

    state: FactState
    value: T | None = None
    source_record_ids: tuple[str, ...] = ()
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    expires_at: datetime | None = None
    confidence: float = 0.0
    trust: TrustLevel | None = None
    source_id: str | None = None
    deployment_mode: DeploymentMode | None = None
    missing_fields: tuple[str, ...] = ()
    parser_version: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if len(self.source_record_ids) != len(set(self.source_record_ids)):
            raise ValueError("source_record_ids must be unique")
        if len(self.missing_fields) != len(set(self.missing_fields)):
            raise ValueError("missing_fields must be unique")
        for timestamp in (self.observed_at, self.valid_from, self.expires_at):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError("fact timestamps must be timezone-aware")
        if self.state in {FactState.AVAILABLE, FactState.PARTIAL}:
            if self.value is None or not self.source_record_ids or self.observed_at is None:
                raise ValueError("available facts require value, source records, and observed_at")
            if self.trust is None or not self.source_id:
                raise ValueError("available facts require trust and source_id")
        if self.state is FactState.UNAVAILABLE and self.value is not None:
            raise ValueError("unavailable facts must not contain a value")

    @property
    def stale(self) -> bool:
        return self.expires_at is not None and self.expires_at <= datetime.now(UTC)

    @classmethod
    def unavailable(
        cls, *, missing_fields: Sequence[str] = (), deployment_mode: DeploymentMode | None = None
    ) -> SourcedFact[Any]:
        return cls(
            state=FactState.UNAVAILABLE,
            missing_fields=tuple(dict.fromkeys(missing_fields)),
            deployment_mode=deployment_mode,
        )


@dataclass(frozen=True, slots=True)
class SourceObservation(Generic[T]):
    value: T
    source_record_id: str
    observed_at: datetime
    valid_from: datetime | None = None
    expires_at: datetime | None = None
    confidence: float = 1.0
    missing_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_record_id.strip():
            raise ValueError("source_record_id must not be empty")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


class LicenseRegistry(Protocol):
    def allows(self, *, source: str, purposes: set[str]) -> bool: ...


class DataSourceAdapter(Protocol):
    source_id: str
    capabilities: frozenset[str]
    deployment_modes: frozenset[DeploymentMode]
    trust: TrustLevel
    parser_version: str
    automated: bool
    required_purposes: frozenset[str]

    async def fetch(self, capability: str, subject_id: str) -> SourceObservation[Any] | None: ...


@dataclass(frozen=True, slots=True)
class SourceFailure:
    source_id: str
    error_code: str


@dataclass(slots=True)
class MatchDataService:
    """Resolve match facts through a licensed, deployment-aware degradation chain.

    Adapters are ordered by explicit trust and configured priority. A lower-trust
    source can restore availability but never silently overwrites a fact returned
    by a stronger source in the same request.
    """

    deployment_mode: DeploymentMode
    sources: Sequence[DataSourceAdapter]
    license_registry: LicenseRegistry | None = None
    failures: list[SourceFailure] = field(default_factory=list, init=False)

    async def get_team_form(self, team_id: str) -> SourcedFact[Any]:
        return await self.get_fact("team_form", team_id)

    async def get_odds(self, match_id: str) -> SourcedFact[Any]:
        return await self.get_fact("odds", match_id)

    async def get_match(self, match_id: str) -> SourcedFact[Any]:
        return await self.get_fact("match", match_id)

    async def get_result(self, match_id: str) -> SourcedFact[Any]:
        return await self.get_fact("result", match_id)

    async def get_fact(self, capability: str, subject_id: str) -> SourcedFact[Any]:
        if not capability.strip() or not subject_id.strip():
            raise ValueError("capability and subject_id must not be empty")
        self.failures.clear()
        for source in self.enabled_sources(capability=capability):
            try:
                observation = await _fetch(source, capability, subject_id)
            except Exception as exc:
                self.failures.append(SourceFailure(source.source_id, type(exc).__name__))
                continue
            if observation is None:
                continue
            return self.to_sourced_fact(observation, source)
        return SourcedFact.unavailable(
            missing_fields=(capability,), deployment_mode=self.deployment_mode
        )

    def enabled_sources(self, *, capability: str) -> tuple[DataSourceAdapter, ...]:
        enabled = [
            source
            for source in self.sources
            if capability in source.capabilities
            and self.deployment_mode in source.deployment_modes
            and self._licensed(source)
        ]
        return tuple(
            sorted(
                enabled,
                key=lambda source: (-TRUST_ORDER[source.trust], source.source_id),
            )
        )

    def to_sourced_fact(
        self, observation: SourceObservation[T], source: DataSourceAdapter
    ) -> SourcedFact[T]:
        missing = tuple(dict.fromkeys(observation.missing_fields))
        return SourcedFact(
            state=FactState.PARTIAL if missing else FactState.AVAILABLE,
            value=observation.value,
            source_record_ids=(observation.source_record_id,),
            observed_at=observation.observed_at.astimezone(UTC),
            valid_from=_utc_optional(observation.valid_from),
            expires_at=_utc_optional(observation.expires_at),
            confidence=observation.confidence,
            trust=source.trust,
            source_id=source.source_id,
            deployment_mode=self.deployment_mode,
            missing_fields=missing,
            parser_version=source.parser_version,
        )

    def _licensed(self, source: DataSourceAdapter) -> bool:
        if not source.automated:
            return True
        if self.license_registry is None:
            return False
        purposes = set(source.required_purposes)
        if self.deployment_mode in {DeploymentMode.STAGING, DeploymentMode.PRODUCTION}:
            purposes.update({"automated_access", "cache", "display", "redistribution"})
        return self.license_registry.allows(source=source.source_id, purposes=purposes)


async def _fetch(
    source: DataSourceAdapter, capability: str, subject_id: str
) -> SourceObservation[Any] | None:
    method = getattr(source, f"get_{capability}", None)
    result = method(subject_id) if callable(method) else source.fetch(capability, subject_id)
    if inspect.isawaitable(result):
        return await result
    raise TypeError(f"source {source.source_id} returned a non-awaitable result")


def prefer_fact(current: SourcedFact[T], candidate: SourcedFact[T]) -> SourcedFact[T]:
    """Keep the strongest existing fact and surface equal-trust disagreement."""

    if current.state is FactState.UNAVAILABLE:
        return candidate
    if candidate.state is FactState.UNAVAILABLE:
        return current
    current_rank = TRUST_ORDER.get(current.trust or TrustLevel.CANDIDATE, 0)
    candidate_rank = TRUST_ORDER.get(candidate.trust or TrustLevel.CANDIDATE, 0)
    if candidate_rank > current_rank:
        return candidate
    if candidate_rank < current_rank or current.value == candidate.value:
        return current
    return SourcedFact(
        state=FactState.CONFLICT,
        value=None,
        source_record_ids=tuple(
            dict.fromkeys(current.source_record_ids + candidate.source_record_ids)
        ),
        observed_at=max(filter(None, (current.observed_at, candidate.observed_at)), default=None),
        confidence=min(current.confidence, candidate.confidence),
        trust=current.trust,
        source_id=current.source_id,
        deployment_mode=current.deployment_mode,
        missing_fields=("conflicting_values",),
    )


def _utc_optional(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)
