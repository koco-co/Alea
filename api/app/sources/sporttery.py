from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


class SourceAccessDenied(RuntimeError):
    pass


class SourcePayloadError(ValueError):
    pass


@dataclass(frozen=True)
class LicenseGrant:
    automatic_access: bool = False
    caching: bool = False
    public_display: bool = False
    historical_storage: bool = False
    redistribution: bool = False
    valid_until: datetime | None = None

    def permits_production(self, now: datetime | None = None) -> bool:
        checked_at = now or datetime.now(UTC)
        return (
            self.automatic_access
            and self.caching
            and self.public_display
            and self.historical_storage
            and self.redistribution
            and (self.valid_until is None or self.valid_until > checked_at)
        )


@dataclass(frozen=True)
class ParsedMatch:
    match_id: str
    kickoff_at: datetime
    sales_cutoff_at: datetime
    home_team: str
    away_team: str


class SportteryFixtureParser:
    required_fields = {
        "match_id",
        "kickoff_at",
        "sales_cutoff_at",
        "home_team",
        "away_team",
    }

    def parse(self, payload: dict[str, Any]) -> ParsedMatch:
        missing = sorted(self.required_fields - payload.keys())
        if missing:
            raise SourcePayloadError(f"missing_fields:{','.join(missing)}")
        try:
            kickoff_at = datetime.fromisoformat(str(payload["kickoff_at"]).replace("Z", "+00:00"))
            cutoff_at = datetime.fromisoformat(
                str(payload["sales_cutoff_at"]).replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise SourcePayloadError("invalid_datetime") from exc
        if kickoff_at.tzinfo is None or cutoff_at.tzinfo is None or cutoff_at > kickoff_at:
            raise SourcePayloadError("invalid_match_timing")
        return ParsedMatch(
            match_id=str(payload["match_id"]),
            kickoff_at=kickoff_at,
            sales_cutoff_at=cutoff_at,
            home_team=str(payload["home_team"]),
            away_team=str(payload["away_team"]),
        )


class SourceSnapshotStore:
    def __init__(self, *, minimum_interval_seconds: int = 60) -> None:
        self.minimum_interval = timedelta(seconds=minimum_interval_seconds)
        self.last_request_at: datetime | None = None
        self.last_good: tuple[ParsedMatch, ...] = ()

    def authorize_request(
        self,
        license_grant: LicenseGrant,
        *,
        environment: str,
        now: datetime,
    ) -> None:
        if environment != "fixture" and not license_grant.permits_production(now):
            raise SourceAccessDenied("source_license_does_not_cover_requested_use")
        if self.last_request_at and now - self.last_request_at < self.minimum_interval:
            raise SourceAccessDenied("source_rate_limit_window")
        self.last_request_at = now

    def publish(self, matches: list[ParsedMatch]) -> tuple[ParsedMatch, ...]:
        if not matches:
            raise SourcePayloadError("empty_snapshot")
        self.last_good = tuple(matches)
        return self.last_good

    def degraded(self) -> tuple[ParsedMatch, ...]:
        return self.last_good
