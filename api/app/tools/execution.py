from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

from app.calculators.sporttery_calc import (
    CalculationInput,
    CalculationResult,
    SportteryRules,
    TicketLeg,
    calculate_plan,
)
from app.tools.contract import (
    CalculateTicketArguments,
    CheckWeatherArguments,
    GetMatchDataArguments,
    GetTeamCurrentSeasonStatsArguments,
    ListSelectionCandidatesArguments,
    ToolCall,
    ToolName,
    ToolPhase,
)


class ToolAuthorizationError(PermissionError):
    pass


class SnapshotContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FrozenOfferOption:
    offer_option_id: str
    match_id: str
    play: str
    fixed_odds: Decimal
    sellable: bool = True

    def __post_init__(self) -> None:
        if not self.offer_option_id.strip() or not self.match_id.strip():
            raise ValueError("offer option identifiers must not be empty")
        if self.fixed_odds <= Decimal("1"):
            raise ValueError("fixed odds must be greater than 1")


@dataclass(frozen=True, slots=True)
class FrozenToolSnapshot:
    snapshot_id: str
    job_id: str
    phase: ToolPhase
    participant_instance_ids: frozenset[str]
    match_ids: frozenset[str]
    team_ids: frozenset[str]
    source_record_ids: frozenset[str]
    selection_candidates: tuple[Mapping[str, Any], ...] = ()
    match_views: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
    team_stats: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
    weather: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
    offer_options: Mapping[str, FrozenOfferOption] = MappingProxyType({})
    sporttery_rules: SportteryRules | None = None
    sporttery_rule_version_id: str | None = None

    def __post_init__(self) -> None:
        if not self.snapshot_id.strip() or not self.job_id.strip():
            raise ValueError("snapshot_id and job_id must not be empty")
        if not set(self.match_views).issubset(self.match_ids):
            raise ValueError("match views must belong to the frozen match set")
        if not set(self.weather).issubset(self.match_ids):
            raise ValueError("weather records must belong to the frozen match set")
        if not set(self.team_stats).issubset(self.team_ids):
            raise ValueError("team stats must belong to the frozen team set")
        if any(option.match_id not in self.match_ids for option in self.offer_options.values()):
            raise ValueError("offer options must belong to the frozen match set")


class FrozenSnapshotRepository(Protocol):
    async def load_tool_snapshot(self, snapshot_id: str) -> FrozenToolSnapshot | None: ...


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    job_id: str
    instance_id: str
    phase: ToolPhase
    target_match_id: str | None = None


@dataclass(frozen=True, slots=True)
class TicketValidationReceipt:
    snapshot_id: str
    request_hash: str
    result_hash: str
    resolved_offer_option_ids: tuple[str, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class ToolExecutionOutcome:
    result: Mapping[str, Any]
    ticket_receipt: TicketValidationReceipt | None = None


@dataclass(slots=True)
class ToolExecutor:
    snapshots: FrozenSnapshotRepository
    page_size: int = 50

    async def execute(
        self, call: ToolCall, *, context: ToolExecutionContext
    ) -> ToolExecutionOutcome:
        snapshot_id = _snapshot_id(call)
        snapshot = await self.snapshots.load_tool_snapshot(snapshot_id)
        if snapshot is None:
            raise SnapshotContractError("snapshot_not_found")
        _authorize_snapshot(snapshot, call=call, context=context)
        if call.name is ToolName.LIST_SELECTION_CANDIDATES:
            return ToolExecutionOutcome(self._list_candidates(snapshot, call.arguments))
        if call.name is ToolName.GET_MATCH_DATA:
            return ToolExecutionOutcome(self._get_match(snapshot, call.arguments))
        if call.name is ToolName.GET_TEAM_CURRENT_SEASON_STATS:
            return ToolExecutionOutcome(self._get_team_stats(snapshot, call.arguments))
        if call.name is ToolName.CHECK_WEATHER:
            return ToolExecutionOutcome(self._get_weather(snapshot, call.arguments))
        return self._calculate_ticket(snapshot, call, call.arguments)

    def _list_candidates(self, snapshot: FrozenToolSnapshot, arguments: Any) -> Mapping[str, Any]:
        if not isinstance(arguments, ListSelectionCandidatesArguments):
            raise SnapshotContractError("invalid_selection_arguments")
        try:
            offset = int(arguments.page_cursor or "0")
        except ValueError as exc:
            raise SnapshotContractError("invalid_page_cursor") from exc
        if offset < 0:
            raise SnapshotContractError("invalid_page_cursor")
        page = snapshot.selection_candidates[offset : offset + self.page_size]
        next_offset = offset + len(page)
        return {
            "selection_scope_snapshot_id": snapshot.snapshot_id,
            "candidates": [dict(item) for item in page],
            "next_page_cursor": (
                str(next_offset) if next_offset < len(snapshot.selection_candidates) else None
            ),
        }

    def _get_match(self, snapshot: FrozenToolSnapshot, arguments: Any) -> Mapping[str, Any]:
        if not isinstance(arguments, GetMatchDataArguments):
            raise SnapshotContractError("invalid_match_arguments")
        value = snapshot.match_views.get(arguments.match_id)
        if value is None:
            raise SnapshotContractError("match_not_in_snapshot")
        return dict(value)

    def _get_team_stats(self, snapshot: FrozenToolSnapshot, arguments: Any) -> Mapping[str, Any]:
        if not isinstance(arguments, GetTeamCurrentSeasonStatsArguments):
            raise SnapshotContractError("invalid_team_arguments")
        value = snapshot.team_stats.get(arguments.team_id)
        if value is None:
            raise SnapshotContractError("team_not_in_snapshot")
        return dict(value)

    def _get_weather(self, snapshot: FrozenToolSnapshot, arguments: Any) -> Mapping[str, Any]:
        if not isinstance(arguments, CheckWeatherArguments):
            raise SnapshotContractError("invalid_weather_arguments")
        value = snapshot.weather.get(arguments.match_id)
        if value is None:
            raise SnapshotContractError("weather_not_in_snapshot")
        return dict(value)

    def _calculate_ticket(
        self, snapshot: FrozenToolSnapshot, call: ToolCall, arguments: Any
    ) -> ToolExecutionOutcome:
        if not isinstance(arguments, CalculateTicketArguments):
            raise SnapshotContractError("invalid_ticket_arguments")
        if snapshot.sporttery_rules is None or not snapshot.sporttery_rule_version_id:
            raise SnapshotContractError("sporttery_rules_not_frozen")
        resolved_ids: list[str] = []
        legs: list[TicketLeg] = []
        errors: list[dict[str, str]] = []
        seen_matches: set[str] = set()
        for selection in arguments.selections:
            if selection.match_id in seen_matches:
                errors.append(
                    {
                        "code": "multiple_plays_same_match",
                        "message": "同一方案内同一比赛只能选择一种玩法",
                    }
                )
                continue
            seen_matches.add(selection.match_id)
            odds: list[Decimal] = []
            for option_id in selection.offer_option_ids:
                option = snapshot.offer_options.get(option_id)
                if option is None:
                    errors.append(
                        {"code": "offer_outside_snapshot", "message": f"未知选项 {option_id}"}
                    )
                    continue
                if (
                    option.match_id != selection.match_id
                    or option.play != selection.play
                    or not option.sellable
                ):
                    errors.append(
                        {
                            "code": "offer_ownership_mismatch",
                            "message": f"选项 {option_id} 不属于声明的比赛/玩法或已停售",
                        }
                    )
                    continue
                resolved_ids.append(option_id)
                odds.append(option.fixed_odds)
            if odds:
                legs.append(
                    TicketLeg(
                        match_id=selection.match_id,
                        play=selection.play,  # type: ignore[arg-type]
                        odds=tuple(odds),
                    )
                )
        calculation: CalculationResult | None = None
        if not errors:
            try:
                calculation = calculate_plan(
                    CalculationInput(
                        legs=tuple(legs),
                        pass_types=tuple(arguments.pass_types),
                        multiplier=arguments.multiplier,
                    ),
                    snapshot.sporttery_rules,
                )
            except (TypeError, ValueError) as exc:
                errors.append({"code": "invalid_ticket", "message": str(exc)})
        result: dict[str, Any] = {
            "bet_context_snapshot_id": snapshot.snapshot_id,
            "sporttery_rule_version_id": snapshot.sporttery_rule_version_id,
            "bet_count": calculation.bet_count if calculation else 0,
            "stake": calculation.amount if calculation else Decimal("0"),
            "theoretical_payout": (calculation.maximum_bonus if calculation else Decimal("0")),
            "resolved_offer_option_ids": resolved_ids,
            "validation_errors": errors,
        }
        result_hash = _hash_mapping(result)
        receipt = TicketValidationReceipt(
            snapshot_id=snapshot.snapshot_id,
            request_hash=call.canonical_hash,
            result_hash=result_hash,
            resolved_offer_option_ids=tuple(resolved_ids),
            passed=not errors and calculation is not None,
        )
        return ToolExecutionOutcome(MappingProxyType(result), receipt)


def require_calculate_ticket(
    *,
    candidate_id: str,
    plan: Mapping[str, Any],
    call: ToolCall,
    outcome: ToolExecutionOutcome,
) -> TicketValidationReceipt:
    """Admission gate for bet debate and final-vote candidate sets."""

    if not candidate_id.strip() or call.name is not ToolName.CALCULATE_TICKET:
        raise SnapshotContractError("calculate_ticket_required")
    receipt = outcome.ticket_receipt
    if receipt is None or not receipt.passed or receipt.request_hash != call.canonical_hash:
        raise SnapshotContractError("calculate_ticket_did_not_pass")
    arguments = call.arguments
    if not isinstance(arguments, CalculateTicketArguments):
        raise SnapshotContractError("calculate_ticket_required")
    expected = _plan_signature(plan)
    actual = _plan_signature(
        {
            "legs": [selection.model_dump(mode="json") for selection in arguments.selections],
            "pass_types": arguments.pass_types,
            "multiplier": arguments.multiplier,
        }
    )
    if expected != actual:
        raise SnapshotContractError("ticket_receipt_does_not_match_candidate_plan")
    return receipt


def _authorize_snapshot(
    snapshot: FrozenToolSnapshot, *, call: ToolCall, context: ToolExecutionContext
) -> None:
    if snapshot.job_id != context.job_id:
        raise ToolAuthorizationError("snapshot_belongs_to_another_job")
    if snapshot.phase is not context.phase or call.phase is not context.phase:
        raise ToolAuthorizationError("tool_not_allowed_in_phase")
    if (
        snapshot.participant_instance_ids
        and context.instance_id not in snapshot.participant_instance_ids
    ):
        raise ToolAuthorizationError("instance_not_in_frozen_participants")
    arguments = call.arguments
    match_id = getattr(arguments, "match_id", None)
    if match_id is not None and match_id not in snapshot.match_ids:
        raise ToolAuthorizationError("match_not_in_snapshot")
    if context.target_match_id is not None and match_id not in {None, context.target_match_id}:
        raise ToolAuthorizationError("tool_target_match_mismatch")
    team_id = getattr(arguments, "team_id", None)
    if team_id is not None and team_id not in snapshot.team_ids:
        raise ToolAuthorizationError("team_not_in_snapshot")
    if isinstance(arguments, CalculateTicketArguments):
        if any(selection.match_id not in snapshot.match_ids for selection in arguments.selections):
            raise ToolAuthorizationError("ticket_match_not_in_snapshot")


def _snapshot_id(call: ToolCall) -> str:
    for field in (
        "selection_scope_snapshot_id",
        "input_snapshot_id",
        "bet_context_snapshot_id",
    ):
        value = getattr(call.arguments, field, None)
        if isinstance(value, str):
            return value
    raise SnapshotContractError("snapshot_id_required")


def _plan_signature(plan: Mapping[str, Any]) -> str:
    legs = plan.get("legs")
    pass_types = plan.get("pass_types")
    multiplier = plan.get("multiplier")
    if not isinstance(legs, Sequence) or isinstance(legs, (str, bytes, bytearray)):
        raise SnapshotContractError("candidate_plan_missing_legs")
    normalized_legs: list[dict[str, Any]] = []
    for leg in legs:
        if not isinstance(leg, Mapping):
            raise SnapshotContractError("candidate_plan_has_invalid_leg")
        normalized_legs.append(
            {
                "match_id": leg.get("match_id"),
                "play": leg.get("play"),
                "offer_option_ids": leg.get("offer_option_ids"),
            }
        )
    return _hash_mapping(
        {
            "legs": normalized_legs,
            "pass_types": pass_types,
            "multiplier": multiplier,
        }
    )


def _hash_mapping(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
