from __future__ import annotations

import inspect
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence
from uuid import UUID


ZERO = Decimal("0")
ONE = Decimal("1")


class SettlementError(ValueError):
    """Raised when deterministic settlement input violates the frozen contract."""


class SettlementTransactionError(RuntimeError):
    """Raised when the database-owned atomic settlement transaction fails."""


class SettlementState(StrEnum):
    WAITING = "waiting"
    PARTIALLY_SETTLED = "partially_settled"
    CONFLICT_FROZEN = "conflict_frozen"
    SETTLED_HIT = "settled_hit"
    SETTLED_MISS = "settled_miss"
    SETTLED_REFUND = "settled_refund"
    CORRECTED = "corrected"


class LegState(StrEnum):
    PENDING = "pending"
    HIT = "hit"
    MISS = "miss"
    VOID = "void"
    CONFLICT = "conflict"


class AccountEntryKind(StrEnum):
    STAKE = "stake"
    REFUND = "refund"
    PAYOUT = "payout"
    REVERSAL = "reversal"


class PositionOwnerType(StrEnum):
    AI_INSTANCE = "ai_instance"
    CONSENSUS = "consensus"


class PositionDecisionType(StrEnum):
    BET = "bet"
    NO_BET = "no_bet"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    daily_fraction: Decimal
    per_match_fraction: Decimal

    def __post_init__(self) -> None:
        _validate_fraction(self.daily_fraction, "daily_fraction")
        _validate_fraction(self.per_match_fraction, "per_match_fraction")


@dataclass(frozen=True, slots=True)
class RiskContext:
    current_balance: Decimal
    start_of_day_balance: Decimal
    daily_exposure: Decimal = ZERO
    match_exposure: Mapping[str, Decimal] | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("current_balance", self.current_balance),
            ("start_of_day_balance", self.start_of_day_balance),
            ("daily_exposure", self.daily_exposure),
        ):
            if value < ZERO:
                raise SettlementError(f"{name} must be non-negative")
        for match_id, value in (self.match_exposure or {}).items():
            if not match_id or value < ZERO:
                raise SettlementError(
                    "match exposure must use non-empty IDs and non-negative values"
                )


@dataclass(frozen=True, slots=True)
class StakeRequest:
    decision_id: str
    match_ids: tuple[str, ...]
    target_fraction: Decimal
    vote_weight: Decimal = ONE

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise SettlementError("decision_id must not be empty")
        if not self.match_ids or any(not item.strip() for item in self.match_ids):
            raise SettlementError("a bet decision requires at least one match")
        if len(self.match_ids) != len(set(self.match_ids)):
            raise SettlementError("match_ids must be unique within a decision")
        _validate_fraction(self.target_fraction, "target_fraction")
        if self.vote_weight <= ZERO:
            raise SettlementError("vote_weight must be positive")


@dataclass(frozen=True, slots=True)
class StakeAllocation:
    decision_id: str
    nominal_amount: Decimal
    allocated_amount: Decimal
    scale: Decimal
    risk_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SettlementPosition:
    """A frozen account decision eligible for deterministic settlement."""

    position_id: str
    account_id: str
    owner_type: PositionOwnerType
    decision: PositionDecisionType
    plan_source_instance_id: str | None
    owner_instance_id: str | None
    is_platform_winner: bool
    stake: Decimal

    def __post_init__(self) -> None:
        if not self.position_id.strip() or not self.account_id.strip():
            raise SettlementError("position_id and account_id must not be empty")
        if self.stake < ZERO:
            raise SettlementError("position stake must be non-negative")
        if self.decision is PositionDecisionType.NO_BET and self.stake != ZERO:
            raise SettlementError("no_bet must freeze a zero position")
        if self.owner_type is PositionOwnerType.AI_INSTANCE:
            if not self.owner_instance_id or self.plan_source_instance_id != self.owner_instance_id:
                raise SettlementError(
                    "an AI account can settle only that instance's own final plan"
                )
            if self.is_platform_winner:
                raise SettlementError(
                    "an AI account position must not be marked as platform winner"
                )
        elif self.owner_instance_id is not None or not self.is_platform_winner:
            raise SettlementError("a consensus account can settle only a platform-winning plan")

    @property
    def counts_as_invested_match(self) -> bool:
        return self.decision is PositionDecisionType.BET and self.stake > ZERO

    @property
    def counts_toward_participation_coverage(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class TicketLeg:
    leg_id: str
    match_id: str
    fixed_odds: Decimal
    state: LegState

    def __post_init__(self) -> None:
        if not self.leg_id.strip() or not self.match_id.strip():
            raise SettlementError("leg_id and match_id must not be empty")
        if self.fixed_odds <= ONE:
            raise SettlementError("fixed_odds must be greater than 1")


@dataclass(frozen=True, slots=True)
class PassCombination:
    combination_id: str
    leg_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.combination_id.strip() or not self.leg_ids:
            raise SettlementError("a pass combination requires an ID and at least one leg")
        if len(self.leg_ids) != len(set(self.leg_ids)):
            raise SettlementError("leg_ids must be unique within a pass combination")


@dataclass(frozen=True, slots=True)
class TicketSettlement:
    state: SettlementState
    stake: Decimal
    returned_amount: Decimal
    profit: Decimal
    combination_returns: Mapping[str, Decimal]
    terminal_leg_states: Mapping[str, LegState]


@dataclass(frozen=True, slots=True)
class AccountEntry:
    kind: AccountEntryKind
    amount: Decimal
    result_version: str
    reverses_entry_id: str | None = None

    def __post_init__(self) -> None:
        if self.amount == ZERO:
            raise SettlementError("zero-value account entries must not be persisted")
        if not self.result_version.strip():
            raise SettlementError("result_version must not be empty")
        if self.kind is AccountEntryKind.REVERSAL and not self.reverses_entry_id:
            raise SettlementError("reversal entries must reference the entry they reverse")


@dataclass(frozen=True, slots=True)
class SettlementRunResult:
    settlement_run_id: str
    notarized_prediction_id: str
    result_version: str
    state: SettlementState
    idempotent_replay: bool
    account_entry_ids: tuple[str, ...]
    outbox_event_ids: tuple[str, ...]


class RPCClient(Protocol):
    def rpc(self, function_name: str, params: Mapping[str, Any]) -> Any: ...


_TERMINAL_SETTLEMENT_STATES = frozenset(
    {
        SettlementState.SETTLED_HIT,
        SettlementState.SETTLED_MISS,
        SettlementState.SETTLED_REFUND,
        SettlementState.CORRECTED,
    }
)


def transition_settlement_state(
    current: SettlementState,
    legs: Sequence[TicketLeg],
    *,
    official_correction: bool = False,
) -> SettlementState:
    """Advance the settlement state without permitting an untracked regression."""

    target = settlement_state_for_legs(legs)
    if official_correction:
        if current not in _TERMINAL_SETTLEMENT_STATES or target not in _TERMINAL_SETTLEMENT_STATES:
            raise SettlementError("an official correction requires old and new terminal results")
        return SettlementState.CORRECTED
    if current in _TERMINAL_SETTLEMENT_STATES and target != current:
        raise SettlementError("a terminal settlement can change only through official correction")
    allowed = {
        SettlementState.WAITING: {
            SettlementState.WAITING,
            SettlementState.PARTIALLY_SETTLED,
            SettlementState.CONFLICT_FROZEN,
            *_TERMINAL_SETTLEMENT_STATES.difference({SettlementState.CORRECTED}),
        },
        SettlementState.PARTIALLY_SETTLED: {
            SettlementState.PARTIALLY_SETTLED,
            SettlementState.CONFLICT_FROZEN,
            *_TERMINAL_SETTLEMENT_STATES.difference({SettlementState.CORRECTED}),
        },
        SettlementState.CONFLICT_FROZEN: {
            SettlementState.CONFLICT_FROZEN,
            SettlementState.PARTIALLY_SETTLED,
            *_TERMINAL_SETTLEMENT_STATES.difference({SettlementState.CORRECTED}),
        },
    }
    if current in allowed and target not in allowed[current]:
        raise SettlementError(f"invalid settlement transition: {current} -> {target}")
    return target


def settlement_state_for_legs(legs: Sequence[TicketLeg]) -> SettlementState:
    """Resolve the non-corrected state without mutating a prior settlement."""

    if not legs:
        raise SettlementError("at least one ticket leg is required")
    states = {leg.state for leg in legs}
    if LegState.CONFLICT in states:
        return SettlementState.CONFLICT_FROZEN
    if LegState.PENDING in states:
        return (
            SettlementState.WAITING
            if states == {LegState.PENDING}
            else SettlementState.PARTIALLY_SETTLED
        )
    if states == {LegState.VOID}:
        return SettlementState.SETTLED_REFUND
    if LegState.MISS in states:
        return SettlementState.SETTLED_MISS
    return SettlementState.SETTLED_HIT


def settle_ticket(
    *,
    stake: Decimal,
    legs: Sequence[TicketLeg],
    combinations: Sequence[PassCombination],
) -> TicketSettlement:
    """Settle frozen pass combinations, removing void legs from each combination.

    A fully void combination refunds its own stake share. A void leg is not emulated
    by changing its odds to 1.0; it is removed before the original combination is
    evaluated, preserving the frozen pass-type structure.
    """

    if stake < ZERO:
        raise SettlementError("stake must be non-negative")
    state = settlement_state_for_legs(legs)
    by_id = {leg.leg_id: leg for leg in legs}
    if len(by_id) != len(legs):
        raise SettlementError("leg IDs must be unique")
    if not combinations:
        raise SettlementError("at least one pass combination is required")
    for combination in combinations:
        missing = set(combination.leg_ids).difference(by_id)
        if missing:
            raise SettlementError(
                f"combination references unknown legs: {', '.join(sorted(missing))}"
            )
    referenced_leg_ids = {leg_id for combination in combinations for leg_id in combination.leg_ids}
    unreferenced = set(by_id).difference(referenced_leg_ids)
    if unreferenced:
        raise SettlementError(
            f"ticket legs are missing from pass combinations: {', '.join(sorted(unreferenced))}"
        )

    if state in {
        SettlementState.WAITING,
        SettlementState.PARTIALLY_SETTLED,
        SettlementState.CONFLICT_FROZEN,
    }:
        return TicketSettlement(
            state=state,
            stake=stake,
            returned_amount=ZERO,
            profit=ZERO,
            combination_returns={},
            terminal_leg_states={leg.leg_id: leg.state for leg in legs},
        )

    share = stake / Decimal(len(combinations))
    returns: dict[str, Decimal] = {}
    all_combinations_refunded = True
    for combination in combinations:
        live_legs = [
            by_id[item] for item in combination.leg_ids if by_id[item].state is not LegState.VOID
        ]
        if not live_legs:
            returns[combination.combination_id] = share
            continue
        all_combinations_refunded = False
        if any(leg.state is LegState.MISS for leg in live_legs):
            returns[combination.combination_id] = ZERO
            continue
        odds_product = ONE
        for leg in live_legs:
            odds_product *= leg.fixed_odds
        returns[combination.combination_id] = share * odds_product

    returned = sum(returns.values(), ZERO)
    terminal_state = SettlementState.SETTLED_REFUND if all_combinations_refunded else state
    return TicketSettlement(
        state=terminal_state,
        stake=stake,
        returned_amount=returned,
        profit=returned - stake,
        combination_returns=returns,
        terminal_leg_states={leg.leg_id: leg.state for leg in legs},
    )


def allocate_stakes(
    requests: Sequence[StakeRequest],
    *,
    context: RiskContext,
    limits: RiskLimits,
) -> tuple[StakeAllocation, ...]:
    """Apply daily and per-match caps proportionally to affected decisions.

    The daily scale applies to the portfolio; each per-match scale applies only to
    cards containing that match. Consensus callers should first distribute their
    nominal pool by frozen final-vote weights.
    """

    if not requests:
        return ()
    if len({item.decision_id for item in requests}) != len(requests):
        raise SettlementError("decision IDs must be unique")
    nominal = {
        item.decision_id: context.current_balance * item.target_fraction for item in requests
    }
    nominal_total = sum(nominal.values(), ZERO)
    if nominal_total == ZERO:
        return tuple(StakeAllocation(item.decision_id, ZERO, ZERO, ZERO, ()) for item in requests)

    # PRD section 11.1 defines both caps against the balance frozen for this
    # allocation. start_of_day_balance remains part of the audit input, but it
    # must not silently replace the notarization-time current balance.
    daily_cap = context.current_balance * limits.daily_fraction
    daily_remaining = max(ZERO, daily_cap - context.daily_exposure)
    daily_scale = min(ONE, daily_remaining / nominal_total)

    nominal_by_match: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for item in requests:
        for match_id in item.match_ids:
            nominal_by_match[match_id] += nominal[item.decision_id]
    exposure = context.match_exposure or {}
    per_match_cap = context.current_balance * limits.per_match_fraction
    match_scales: dict[str, Decimal] = {}
    for match_id, amount in nominal_by_match.items():
        remaining = max(ZERO, per_match_cap - exposure.get(match_id, ZERO))
        match_scales[match_id] = ONE if amount == ZERO else min(ONE, remaining / amount)

    allocations: list[StakeAllocation] = []
    for item in requests:
        constraints = [(daily_scale, "daily_limit")]
        constraints.extend(
            (match_scales[match_id], f"per_match_limit:{match_id}") for match_id in item.match_ids
        )
        scale = min(value for value, _ in constraints)
        reasons = tuple(reason for value, reason in constraints if value == scale and value < ONE)
        allocations.append(
            StakeAllocation(
                decision_id=item.decision_id,
                nominal_amount=nominal[item.decision_id],
                allocated_amount=nominal[item.decision_id] * scale,
                scale=scale,
                risk_reasons=reasons,
            )
        )
    return tuple(allocations)


def distribute_consensus_fraction(
    requests: Sequence[StakeRequest],
    *,
    total_fraction: Decimal,
) -> tuple[StakeRequest, ...]:
    """Allocate a tied platform portfolio by final weighted-vote share."""

    _validate_fraction(total_fraction, "total_fraction")
    if not requests:
        return ()
    weight_total = sum((item.vote_weight for item in requests), ZERO)
    return tuple(
        StakeRequest(
            decision_id=item.decision_id,
            match_ids=item.match_ids,
            target_fraction=total_fraction * item.vote_weight / weight_total,
            vote_weight=item.vote_weight,
        )
        for item in requests
    )


def settlement_entries(
    *,
    stake: Decimal,
    result: TicketSettlement,
    result_version: str,
) -> tuple[AccountEntry, ...]:
    """Build append-only stake/refund/payout entries for a first settlement."""

    if result.state not in {
        SettlementState.SETTLED_HIT,
        SettlementState.SETTLED_MISS,
        SettlementState.SETTLED_REFUND,
    }:
        return ()
    entries: list[AccountEntry] = []
    if stake > ZERO:
        entries.append(AccountEntry(AccountEntryKind.STAKE, -stake, result_version))
    if result.returned_amount > ZERO:
        kind = (
            AccountEntryKind.REFUND
            if result.state is SettlementState.SETTLED_REFUND
            else AccountEntryKind.PAYOUT
        )
        entries.append(AccountEntry(kind, result.returned_amount, result_version))
    return tuple(entries)


def position_settlement_entries(
    position: SettlementPosition,
    *,
    result: TicketSettlement,
    result_version: str,
) -> tuple[AccountEntry, ...]:
    """Keep no_bet in coverage/audit while guaranteeing it never creates money entries."""

    if position.decision is PositionDecisionType.NO_BET:
        return ()
    return settlement_entries(
        stake=position.stake,
        result=result,
        result_version=result_version,
    )


def correction_entries(
    previous_entries: Sequence[tuple[str, AccountEntry]],
    replacement_entries: Sequence[AccountEntry],
    *,
    result_version: str,
) -> tuple[AccountEntry, ...]:
    """Reverse every prior financial effect, then append the corrected effects."""

    reversals = tuple(
        AccountEntry(
            kind=AccountEntryKind.REVERSAL,
            amount=-entry.amount,
            result_version=result_version,
            reverses_entry_id=entry_id,
        )
        for entry_id, entry in previous_entries
    )
    return reversals + tuple(replacement_entries)


async def settle_notarized_prediction(
    client: RPCClient,
    notarized_prediction_id: UUID | str,
    result_version: UUID | str,
) -> SettlementRunResult:
    """Invoke the sole database transaction allowed to commit a settlement.

    The RPC owns idempotency, immutable entries, balance-cache refresh, card-leg
    projection updates, and ranking/notification/review outbox inserts. Application
    code must not split those writes into separate requests.
    """

    params = {
        "p_notarized_prediction_id": str(notarized_prediction_id),
        "p_result_version_id": str(result_version),
    }
    try:
        value = await _rpc_data(client, "settle_notarized_prediction", params)
        row = (
            value[0]
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes))
            else value
        )
        if not isinstance(row, Mapping):
            raise SettlementTransactionError("settlement RPC returned an invalid result")
        return SettlementRunResult(
            settlement_run_id=_required_string(row, "settlement_run_id"),
            notarized_prediction_id=_required_string(row, "notarized_prediction_id"),
            result_version=_required_string(row, "result_version_id", fallback="result_version"),
            state=SettlementState(_required_string(row, "state")),
            idempotent_replay=bool(row.get("idempotent_replay", False)),
            account_entry_ids=_string_tuple(row.get("account_entry_ids", ())),
            outbox_event_ids=_string_tuple(row.get("outbox_event_ids", ())),
        )
    except SettlementTransactionError:
        raise
    except Exception as exc:
        raise SettlementTransactionError("database settlement transaction failed") from exc


async def _rpc_data(client: RPCClient, name: str, params: Mapping[str, Any]) -> Any:
    query = client.rpc(name, dict(params))
    if inspect.isawaitable(query):
        query = await query
    execute = getattr(query, "execute", None)
    response = execute() if callable(execute) else query
    if inspect.isawaitable(response):
        response = await response
    if getattr(response, "error", None):
        raise SettlementTransactionError(f"{name} RPC failed")
    return getattr(response, "data", response)


def _required_string(row: Mapping[str, Any], key: str, *, fallback: str | None = None) -> str:
    value = row.get(key, row.get(fallback) if fallback else None)
    if not isinstance(value, str) or not value:
        raise SettlementTransactionError(f"settlement RPC result is missing {key}")
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SettlementTransactionError("settlement RPC returned an invalid ID list")
    if any(not isinstance(item, str) or not item for item in value):
        raise SettlementTransactionError("settlement RPC returned an invalid ID")
    return tuple(value)


def _validate_fraction(value: Decimal, name: str) -> None:
    if value < ZERO or value > ONE:
        raise SettlementError(f"{name} must be between 0 and 1")
