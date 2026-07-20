from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Mapping, Protocol, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.security import AuthenticatedPrincipal


router = APIRouter(prefix="/v1/admin/real-ledger", tags=["real-ledger"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RealLedgerRecordInput(StrictModel):
    prediction_id: UUID | None = None
    ticket_content: dict[str, Any]
    multiplier: int = Field(ge=1, le=99_999)
    stake: Decimal = Field(gt=0)
    payout: Decimal = Field(default=Decimal("0"), ge=0)
    purchased_at: datetime
    note: str | None = Field(default=None, max_length=1000)


class RealLedgerRecord(RealLedgerRecordInput):
    record_id: UUID
    created_at: datetime
    updated_at: datetime


class RealLedgerSummary(StrictModel):
    total_stake: Decimal = Field(ge=0)
    total_payout: Decimal = Field(ge=0)
    net_profit: Decimal
    hit_rate: Decimal = Field(ge=0, le=1)


class RealLedgerGateway(Protocol):
    async def query(
        self, operation: str, *, actor_id: str, params: Mapping[str, Any]
    ) -> Mapping[str, Any] | Sequence[Mapping[str, Any]] | None: ...

    async def command(
        self,
        operation: str,
        *,
        actor_id: str,
        request_id: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        """Mutate the record and append an admin audit row in one transaction."""
        ...


def require_admin(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(status_code=401, detail="authentication_required")
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="administrator_required")
    return principal


def get_gateway(request: Request) -> RealLedgerGateway:
    gateway = getattr(request.app.state, "real_ledger_gateway", None)
    if gateway is None:
        raise HTTPException(status_code=503, detail="real_ledger_gateway_unavailable")
    return gateway


Admin = Annotated[AuthenticatedPrincipal, Depends(require_admin)]
Gateway = Annotated[RealLedgerGateway, Depends(get_gateway)]
RequestId = Annotated[str, Header(alias="X-Request-ID", min_length=1, max_length=200)]


@router.get("/summary", response_model=RealLedgerSummary)
async def summary(admin: Admin, gateway: Gateway) -> RealLedgerSummary:
    value = await gateway.query("summary", actor_id=admin.subject, params={})
    return _one(value, RealLedgerSummary, not_found=False)


@router.get("/records", response_model=list[RealLedgerRecord])
async def list_records(
    admin: Admin,
    gateway: Gateway,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RealLedgerRecord]:
    values = await gateway.query(
        "list_records", actor_id=admin.subject, params={"cursor": cursor, "limit": limit}
    )
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise HTTPException(status_code=502, detail="invalid_real_ledger_projection")
    return [_one(value, RealLedgerRecord, not_found=False) for value in values]


@router.post("/records", response_model=RealLedgerRecord, status_code=201)
async def create_record(
    body: RealLedgerRecordInput,
    admin: Admin,
    gateway: Gateway,
    request_id: RequestId,
) -> RealLedgerRecord:
    value = await gateway.command(
        "create_record",
        actor_id=admin.subject,
        request_id=request_id,
        payload=body.model_dump(mode="json"),
    )
    return _one(value, RealLedgerRecord, not_found=False)


@router.put("/records/{record_id}", response_model=RealLedgerRecord)
async def update_record(
    record_id: UUID,
    body: RealLedgerRecordInput,
    admin: Admin,
    gateway: Gateway,
    request_id: RequestId,
) -> RealLedgerRecord:
    value = await gateway.command(
        "update_record",
        actor_id=admin.subject,
        request_id=request_id,
        payload={"record_id": str(record_id), **body.model_dump(mode="json")},
    )
    return _one(value, RealLedgerRecord)


@router.delete("/records/{record_id}", status_code=204)
async def delete_record(
    record_id: UUID,
    admin: Admin,
    gateway: Gateway,
    request_id: RequestId,
) -> None:
    value = await gateway.command(
        "delete_record",
        actor_id=admin.subject,
        request_id=request_id,
        payload={"record_id": str(record_id)},
    )
    if value is None:
        raise HTTPException(status_code=404, detail="real_ledger_record_not_found")


def _one(value: Any, model: type[BaseModel], *, not_found: bool = True) -> Any:
    if value is None and not_found:
        raise HTTPException(status_code=404, detail="real_ledger_record_not_found")
    try:
        return model.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid_real_ledger_projection") from exc
