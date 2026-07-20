from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Mapping, Protocol, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.security import AuthenticatedPrincipal


router = APIRouter(prefix="/v1/ledger", tags=["ledger"])
rankings_router = APIRouter(prefix="/v1/rankings", tags=["rankings"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LedgerAccount(StrictModel):
    account_id: UUID
    owner_type: str
    owner_id: str | None = None
    display_name: str
    initial_balance: Decimal = Field(ge=0)
    current_balance: Decimal = Field(ge=0)
    net_return_rate: Decimal
    maximum_drawdown_rate: Decimal = Field(ge=0)
    invested_match_count: int = Field(ge=0)
    hit_match_count: int = Field(ge=0)


class LedgerEntry(StrictModel):
    entry_id: UUID
    account_id: UUID
    entry_type: str
    amount: Decimal
    balance_after: Decimal = Field(ge=0)
    notarized_prediction_id: UUID | None = None
    result_version: int | None = Field(default=None, ge=1)
    created_at: datetime


class EquityPoint(StrictModel):
    at: datetime
    balance: Decimal = Field(ge=0)
    net_value: Decimal = Field(ge=0)


class LedgerPage(StrictModel):
    items: list[dict[str, Any]]
    next_cursor: str | None = None


class RankingRow(StrictModel):
    ai_instance_id: UUID
    display_name: str
    formula_version_id: UUID
    settled_count: int = Field(ge=0)
    participation_coverage: Decimal = Field(ge=0, le=1)
    raw_score: Decimal = Field(ge=0, le=100)
    smoothed_score: Decimal = Field(ge=0, le=100)
    exact_score_rate: Decimal = Field(ge=0, le=1)
    direction_rate: Decimal = Field(ge=0, le=1)
    total_goals_rate: Decimal = Field(ge=0, le=1)
    half_full_rate: Decimal = Field(ge=0, le=1)
    eligible_for_rank: bool
    eligibility_reasons: list[str] = Field(default_factory=list)
    rank: int | None = Field(default=None, ge=1)


class LedgerGateway(Protocol):
    async def query(
        self,
        operation: str,
        *,
        viewer_id: str,
        params: Mapping[str, Any],
    ) -> Mapping[str, Any] | Sequence[Mapping[str, Any]] | None: ...


def require_authenticated(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(status_code=401, detail="authentication_required")
    return principal


def get_ledger_gateway(request: Request) -> LedgerGateway:
    gateway = getattr(request.app.state, "ledger_gateway", None)
    if gateway is None:
        raise HTTPException(status_code=503, detail="ledger_gateway_unavailable")
    return gateway


Principal = Annotated[AuthenticatedPrincipal, Depends(require_authenticated)]
Gateway = Annotated[LedgerGateway, Depends(get_ledger_gateway)]


@router.get("/accounts", response_model=list[LedgerAccount])
async def list_accounts(principal: Principal, gateway: Gateway) -> list[LedgerAccount]:
    rows = await _query_sequence(gateway, "list_accounts", principal, {})
    return _validate_list(rows, LedgerAccount, "invalid_ledger_projection")


@router.get("/accounts/{account_id}", response_model=LedgerAccount)
async def get_account(account_id: UUID, principal: Principal, gateway: Gateway) -> LedgerAccount:
    value = await _query_mapping(gateway, "get_account", principal, {"account_id": str(account_id)})
    if value is None:
        raise HTTPException(status_code=404, detail="ledger_account_not_found")
    return _validate_one(value, LedgerAccount, "invalid_ledger_projection")


@router.get("/accounts/{account_id}/entries", response_model=LedgerPage)
async def list_entries(
    account_id: UUID,
    principal: Principal,
    gateway: Gateway,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> LedgerPage:
    value = await _query_mapping(
        gateway,
        "list_entries",
        principal,
        {"account_id": str(account_id), "cursor": cursor, "limit": limit},
    )
    if value is None:
        raise HTTPException(status_code=404, detail="ledger_account_not_found")
    page = _validate_one(value, LedgerPage, "invalid_ledger_projection")
    _validate_list(page.items, LedgerEntry, "invalid_ledger_projection")
    return page


@router.get("/accounts/{account_id}/equity", response_model=list[EquityPoint])
async def account_equity(
    account_id: UUID,
    principal: Principal,
    gateway: Gateway,
    range_name: str = Query(default="30d", alias="range", pattern="^(7d|30d|all)$"),
) -> list[EquityPoint]:
    rows = await _query_sequence(
        gateway,
        "account_equity",
        principal,
        {"account_id": str(account_id), "range": range_name},
    )
    return _validate_list(rows, EquityPoint, "invalid_ledger_projection")


@router.get("/accounts/{account_id}/positions", response_model=LedgerPage)
async def list_positions(
    account_id: UUID,
    principal: Principal,
    gateway: Gateway,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> LedgerPage:
    value = await _query_mapping(
        gateway,
        "list_positions",
        principal,
        {"account_id": str(account_id), "cursor": cursor, "limit": limit},
    )
    if value is None:
        raise HTTPException(status_code=404, detail="ledger_account_not_found")
    return _validate_one(value, LedgerPage, "invalid_ledger_projection")


@rankings_router.get("", response_model=list[RankingRow])
async def list_rankings(
    principal: Principal,
    gateway: Gateway,
    dimension: str = Query(default="composite"),
    range_name: str = Query(default="all", alias="range", pattern="^(7d|30d|all)$"),
    formula_version_id: UUID | None = Query(default=None),
) -> list[RankingRow]:
    rows = await _query_sequence(
        gateway,
        "list_rankings",
        principal,
        {
            "dimension": dimension,
            "range": range_name,
            "formula_version_id": str(formula_version_id) if formula_version_id else None,
        },
    )
    return _validate_list(rows, RankingRow, "invalid_ranking_projection")


@rankings_router.get("/{ai_instance_id}", response_model=dict[str, Any])
async def ranking_profile(
    ai_instance_id: UUID, principal: Principal, gateway: Gateway
) -> dict[str, Any]:
    value = await _query_mapping(
        gateway,
        "ranking_profile",
        principal,
        {"ai_instance_id": str(ai_instance_id)},
    )
    if value is None:
        raise HTTPException(status_code=404, detail="ranking_profile_not_found")
    return dict(value)


async def _query_mapping(
    gateway: LedgerGateway,
    operation: str,
    principal: AuthenticatedPrincipal,
    params: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    try:
        value = await gateway.query(operation, viewer_id=principal.subject, params=params)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="ledger_forbidden") from exc
    if value is not None and not isinstance(value, Mapping):
        raise HTTPException(status_code=502, detail="invalid_ledger_projection")
    return value


async def _query_sequence(
    gateway: LedgerGateway,
    operation: str,
    principal: AuthenticatedPrincipal,
    params: Mapping[str, Any],
) -> Sequence[Mapping[str, Any]]:
    try:
        value = await gateway.query(operation, viewer_id=principal.subject, params=params)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="ledger_forbidden") from exc
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise HTTPException(status_code=502, detail="invalid_ledger_projection")
    return value


def _validate_one(value: Any, model: type[BaseModel], detail: str) -> Any:
    try:
        return model.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc


def _validate_list(values: Sequence[Any], model: type[BaseModel], detail: str) -> list[Any]:
    return [_validate_one(value, model, detail) for value in values]
