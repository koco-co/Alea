from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


class NotarizationError(RuntimeError):
    """Raised when the database-owned notarization transaction fails."""


class RPCClient(Protocol):
    def rpc(self, function_name: str, params: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True, slots=True)
class NotarizedPredictionRef:
    notarized_prediction_id: str
    match_run_id: str


@dataclass(frozen=True, slots=True)
class ProjectionRefreshResult:
    execution_audits_inserted: int
    notarized_predictions_inserted: int
    roundtable_events_inserted: int


@dataclass(frozen=True, slots=True)
class NotarizationResult:
    predictions: tuple[NotarizedPredictionRef, ...]
    projections: ProjectionRefreshResult | None = None


async def notarize_roundtable(
    client: RPCClient,
    job_id: UUID | str,
    *,
    refresh_public_projections: bool = True,
) -> NotarizationResult:
    """Invoke the security-definer ledger transaction and optional projection refresh.

    Locking, quorum rechecks, immutable inserts, risk reservation and the final
    state transition stay inside PostgreSQL. The application role must never
    emulate the transaction with direct table writes.
    """

    normalized_job_id = str(job_id)
    try:
        rows = await _rpc_data(client, "notarize_roundtable", {"p_job_id": normalized_job_id})
        predictions = _prediction_refs(rows)
        projections = None
        if refresh_public_projections:
            projection_data = await _rpc_data(
                client,
                "refresh_public_roundtable_projections",
                {"p_job_id": normalized_job_id},
            )
            projections = _projection_result(projection_data)
    except NotarizationError:
        raise
    except Exception as exc:
        raise NotarizationError("database notarization transaction failed") from exc
    return NotarizationResult(predictions=predictions, projections=projections)


async def refresh_public_roundtable_projections(
    client: RPCClient, job_id: UUID | str
) -> ProjectionRefreshResult:
    data = await _rpc_data(
        client,
        "refresh_public_roundtable_projections",
        {"p_job_id": str(job_id)},
    )
    return _projection_result(data)


async def _rpc_data(client: RPCClient, name: str, params: Mapping[str, Any]) -> Any:
    query = client.rpc(name, dict(params))
    if inspect.isawaitable(query):
        query = await query
    execute = getattr(query, "execute", None)
    response = execute() if callable(execute) else query
    if inspect.isawaitable(response):
        response = await response
    error = getattr(response, "error", None)
    if error:
        raise NotarizationError(f"{name} RPC failed")
    return getattr(response, "data", response)


def _prediction_refs(value: Any) -> tuple[NotarizedPredictionRef, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise NotarizationError("notarize_roundtable returned an invalid result")
    result: list[NotarizedPredictionRef] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise NotarizationError("notarize_roundtable returned an invalid row")
        prediction_id = row.get("notarized_prediction_id")
        match_run_id = row.get("notarized_match_run_id", row.get("match_run_id"))
        if not isinstance(prediction_id, str) or not isinstance(match_run_id, str):
            raise NotarizationError("notarize_roundtable returned an incomplete row")
        result.append(NotarizedPredictionRef(prediction_id, match_run_id))
    return tuple(result)


def _projection_result(value: Any) -> ProjectionRefreshResult:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        value = value[0] if value else {}
    if not isinstance(value, Mapping):
        raise NotarizationError("projection refresh returned an invalid result")
    return ProjectionRefreshResult(
        execution_audits_inserted=_count(value, "execution_audits_inserted"),
        notarized_predictions_inserted=_count(value, "notarized_predictions_inserted"),
        roundtable_events_inserted=_count(value, "roundtable_events_inserted"),
    )


def _count(value: Mapping[str, Any], key: str) -> int:
    count = value.get(key, 0)
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise NotarizationError(f"projection count {key} is invalid")
    return count
