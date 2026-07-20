from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Mapping, Protocol, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.security import AuthenticatedPrincipal


router = APIRouter(prefix="/v1/roundtables", tags=["roundtables"])

PUBLIC_PAYLOAD_FIELDS = frozenset(
    {
        "phase",
        "round_number",
        "match_id",
        "speaker_codename",
        "message",
        "stance",
        "previous_vote",
        "new_vote",
        "source_record_ids",
        "sources",
        "claim_status",
        "status",
        "reason",
        "consensus",
        "raw_votes",
        "participant_count",
        "notarized_count",
    }
)


class RoundtableEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    job_id: UUID
    event_seq: int = Field(gt=0)
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]
    created_at: datetime


class RoundtableEventPage(BaseModel):
    events: list[RoundtableEvent]
    last_event_seq: int = Field(ge=0)
    has_more: bool


class RoundtableEventGateway(Protocol):
    async def read_events(
        self,
        job_id: str,
        *,
        after_seq: int,
        limit: int,
        visibility: str,
        viewer_id: str,
    ) -> Sequence[Mapping[str, Any] | RoundtableEvent]: ...


def require_authenticated(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )
    return principal


def get_event_gateway(request: Request) -> RoundtableEventGateway:
    gateway = getattr(request.app.state, "roundtable_event_gateway", None)
    if gateway is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="roundtable_event_gateway_unavailable",
        )
    return gateway


Principal = Annotated[AuthenticatedPrincipal, Depends(require_authenticated)]
Gateway = Annotated[RoundtableEventGateway, Depends(get_event_gateway)]


@router.get("/{job_id}/events", response_model=RoundtableEventPage)
async def backfill_roundtable_events(
    job_id: UUID,
    principal: Principal,
    gateway: Gateway,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> RoundtableEventPage:
    """Backfill the persistent event log after the private channel subscribes.

    Admins read the internal stream. Registered users read only the explicit public
    projection, so unpublished pre-cutoff payloads and provider internals never
    cross this API boundary.
    """

    visibility = "internal" if principal.role == "admin" else "public"
    try:
        rows = await gateway.read_events(
            str(job_id),
            after_seq=after_seq,
            limit=limit + 1,
            visibility=visibility,
            viewer_id=principal.subject,
        )
        events = [_coerce_event(row, visibility=visibility) for row in rows]
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="roundtable_events_forbidden") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid_roundtable_event_projection") from exc

    events.sort(key=lambda item: item.event_seq)
    if any(event.job_id != job_id or event.event_seq <= after_seq for event in events):
        raise HTTPException(status_code=502, detail="invalid_roundtable_event_projection")
    sequences = [event.event_seq for event in events]
    if len(sequences) != len(set(sequences)):
        raise HTTPException(status_code=502, detail="duplicate_roundtable_event_sequence")
    has_more = len(events) > limit
    page = events[:limit]
    return RoundtableEventPage(
        events=page,
        last_event_seq=page[-1].event_seq if page else after_seq,
        has_more=has_more,
    )


def project_public_event(event: RoundtableEvent) -> RoundtableEvent:
    """Apply the same explicit field whitelist used by the public DB projection."""

    return event.model_copy(
        update={
            "payload": {
                key: value for key, value in event.payload.items() if key in PUBLIC_PAYLOAD_FIELDS
            }
        }
    )


def _coerce_event(
    value: Mapping[str, Any] | RoundtableEvent,
    *,
    visibility: str,
) -> RoundtableEvent:
    if isinstance(value, RoundtableEvent):
        event = value
    else:
        data = dict(value)
        event = RoundtableEvent.model_validate(
            {
                "id": data.get("id", data.get("source_event_id")),
                "job_id": data.get("job_id"),
                "event_seq": data.get("event_seq"),
                "event_type": data.get("event_type"),
                "payload": data.get("payload", data.get("public_payload")),
                "created_at": data.get("created_at"),
            }
        )
    return project_public_event(event) if visibility == "public" else event
