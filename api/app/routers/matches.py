from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Mapping, Protocol, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.security import AuthenticatedPrincipal


router = APIRouter(prefix="/v1/matches", tags=["matches"])


class MatchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: UUID
    competition: str
    home_team: str
    away_team: str
    kickoff_at: datetime
    sales_cutoff_at: datetime | None = None
    state: str
    data_completeness: float = Field(ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    latest_observed_at: datetime | None = None


class MatchPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matches: list[MatchSummary]
    next_cursor: str | None = None
    freshness_state: str


class MatchDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    match_id: UUID
    source_record_ids: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class SourceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    source_label: str
    observed_at: datetime
    valid_from: datetime | None = None
    expires_at: datetime | None = None
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)


class MatchGateway(Protocol):
    async def list_matches(
        self,
        *,
        business_date: str | None,
        state: str | None,
        cursor: str | None,
        limit: int,
        viewer_id: str,
    ) -> Mapping[str, Any]: ...

    async def get_match(self, match_id: str, *, viewer_id: str) -> Mapping[str, Any] | None: ...

    async def get_match_sources(
        self, match_id: str, *, viewer_id: str
    ) -> Sequence[Mapping[str, Any]]: ...


def require_authenticated(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )
    return principal


def get_match_gateway(request: Request) -> MatchGateway:
    gateway = getattr(request.app.state, "match_gateway", None)
    if gateway is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="match_gateway_unavailable",
        )
    return gateway


Principal = Annotated[AuthenticatedPrincipal, Depends(require_authenticated)]
Gateway = Annotated[MatchGateway, Depends(get_match_gateway)]


@router.get("", response_model=MatchPage)
async def list_matches(
    principal: Principal,
    gateway: Gateway,
    business_date: str | None = Query(default=None),
    state_filter: str | None = Query(default=None, alias="state"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> MatchPage:
    try:
        value = await gateway.list_matches(
            business_date=business_date,
            state=state_filter,
            cursor=cursor,
            limit=limit,
            viewer_id=principal.subject,
        )
        return MatchPage.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid_match_projection") from exc


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match(match_id: UUID, principal: Principal, gateway: Gateway) -> MatchDetail:
    try:
        value = await gateway.get_match(str(match_id), viewer_id=principal.subject)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="match_forbidden") from exc
    if value is None:
        raise HTTPException(status_code=404, detail="match_not_found")
    try:
        return MatchDetail.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid_match_projection") from exc


@router.get("/{match_id}/sources", response_model=list[SourceProjection])
async def get_match_sources(
    match_id: UUID, principal: Principal, gateway: Gateway
) -> list[SourceProjection]:
    try:
        rows = await gateway.get_match_sources(str(match_id), viewer_id=principal.subject)
        return [SourceProjection.model_validate(row) for row in rows]
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="match_sources_forbidden") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid_source_projection") from exc
