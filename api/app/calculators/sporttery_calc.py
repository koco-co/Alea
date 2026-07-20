from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import combinations
from math import prod
from typing import Literal, overload

SportteryPlay = Literal["had", "hhad", "crs", "ttg", "hafu"]
ResultCorrectionSource = Literal["sporttery_official", "competition_organizer"]

PASS_TYPE_COMPONENT_SIZES: dict[str, tuple[int, ...]] = {
    "1x1": (1,),
    "2x1": (2,),
    "3x1": (3,),
    "3x3": (2,),
    "3x4": (2, 3),
    "4x1": (4,),
    "4x4": (3,),
    "4x5": (3, 4),
    "4x6": (2,),
    "4x11": (2, 3, 4),
    "5x1": (5,),
    "5x5": (4,),
    "5x6": (4, 5),
    "5x10": (2,),
    "5x16": (3, 4, 5),
    "5x20": (2, 3),
    "5x26": (2, 3, 4, 5),
    "6x1": (6,),
    "6x6": (5,),
    "6x7": (5, 6),
    "6x15": (2,),
    "6x20": (3,),
    "6x22": (4, 5, 6),
    "6x35": (2, 3),
    "6x42": (3, 4, 5, 6),
    "6x50": (2, 3, 4),
    "6x57": (2, 3, 4, 5, 6),
    "7x1": (7,),
    "7x7": (6,),
    "7x8": (6, 7),
    "7x21": (5,),
    "7x35": (4,),
    "7x120": (2, 3, 4, 5, 6, 7),
    "8x1": (8,),
    "8x8": (7,),
    "8x9": (7, 8),
    "8x28": (6,),
    "8x56": (5,),
    "8x70": (4,),
    "8x247": (2, 3, 4, 5, 6, 7, 8),
}


@dataclass(frozen=True)
class PayoutCap:
    minimum_legs: int
    maximum_legs: int
    amount: Decimal


@dataclass(frozen=True)
class SportteryRules:
    version: int
    effective_at: str
    unit_stake: Decimal
    maximum_multiplier: int
    maximum_ticket_amount: Decimal
    maximum_pass_size_by_play: dict[SportteryPlay, int]
    pass_type_component_sizes: dict[str, tuple[int, ...]]
    payout_caps: tuple[PayoutCap, ...]


DEFAULT_SPORTTERY_RULES = SportteryRules(
    version=1,
    effective_at="2026-07-20T00:00:00+08:00",
    unit_stake=Decimal("2.00"),
    maximum_multiplier=50,
    maximum_ticket_amount=Decimal("6000.00"),
    maximum_pass_size_by_play={
        "had": 8,
        "hhad": 8,
        "crs": 4,
        "ttg": 6,
        "hafu": 4,
    },
    pass_type_component_sizes=PASS_TYPE_COMPONENT_SIZES,
    payout_caps=(
        PayoutCap(1, 1, Decimal("100000.00")),
        PayoutCap(2, 3, Decimal("200000.00")),
        PayoutCap(4, 5, Decimal("500000.00")),
        PayoutCap(6, 8, Decimal("1000000.00")),
    ),
)


@dataclass(frozen=True)
class TicketLeg:
    match_id: str
    play: SportteryPlay
    odds: tuple[Decimal, ...]
    is_void: bool = False
    is_banker: bool = False


@dataclass(frozen=True)
class CalculationInput:
    legs: tuple[TicketLeg, ...]
    pass_types: tuple[str, ...]
    multiplier: int = 1
    banker_match_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CalculationResult:
    rules_version: int
    bet_count: int
    amount: Decimal
    expanded_combination_count: int
    uncapped_maximum_bonus: Decimal
    maximum_bonus: Decimal
    payout_cap: Decimal
    payout_cap_exceeded: bool
    amount_cap_exceeded: bool


@dataclass(frozen=True)
class TicketResult:
    """Compatibility result for the Gate 0 three-argument API."""

    bet_count: int
    amount: Decimal
    maximum_bonus: Decimal
    effective_combination_count: int


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _parse_pass_type(pass_type: str) -> tuple[int, int]:
    try:
        match_count, bet_count = (int(part) for part in pass_type.split("x", maxsplit=1))
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid pass type: {pass_type}") from error
    return match_count, bet_count


def _selected_bankers(input_value: CalculationInput) -> set[str]:
    bankers = set(input_value.banker_match_ids)
    bankers.update(leg.match_id for leg in input_value.legs if leg.is_banker)
    return bankers


def _expand_with_bankers(
    legs: tuple[TicketLeg, ...], component_size: int, banker_ids: set[str]
) -> list[tuple[TicketLeg, ...]]:
    bankers = tuple(leg for leg in legs if leg.match_id in banker_ids)
    drags = tuple(leg for leg in legs if leg.match_id not in banker_ids)
    return [bankers + selection for selection in combinations(drags, component_size - len(bankers))]


def _payout_cap_for_legs(leg_count: int, rules: SportteryRules) -> Decimal:
    for band in rules.payout_caps:
        if band.minimum_legs <= leg_count <= band.maximum_legs:
            return band.amount
    raise ValueError(f"no payout cap is configured for {leg_count} legs")


def validate_input(
    input_value: CalculationInput, rules: SportteryRules = DEFAULT_SPORTTERY_RULES
) -> None:
    if (
        isinstance(input_value.multiplier, bool)
        or not isinstance(input_value.multiplier, int)
        or not 1 <= input_value.multiplier <= rules.maximum_multiplier
    ):
        raise ValueError(f"multiplier must be between 1 and {rules.maximum_multiplier}")
    if not input_value.legs:
        raise ValueError("at least one leg is required")
    if not input_value.pass_types:
        raise ValueError("at least one pass type is required")
    if len(set(input_value.pass_types)) != len(input_value.pass_types):
        raise ValueError("pass types must be unique")
    if len({leg.match_id for leg in input_value.legs}) != len(input_value.legs):
        raise ValueError("a ticket may contain at most one play per match")

    for leg in input_value.legs:
        if leg.play not in rules.maximum_pass_size_by_play:
            raise ValueError(f"unsupported play: {leg.play}")
        if not leg.odds or any(not odd.is_finite() or odd <= 1 for odd in leg.odds):
            raise ValueError("each leg requires finite fixed odds greater than 1")

    dynamic_maximum = min(rules.maximum_pass_size_by_play[leg.play] for leg in input_value.legs)
    if len(input_value.legs) > dynamic_maximum:
        raise ValueError(f"selected plays allow at most {dynamic_maximum} legs")

    banker_ids = _selected_bankers(input_value)
    selected_ids = {leg.match_id for leg in input_value.legs}
    if not banker_ids <= selected_ids:
        raise ValueError("every banker must reference a selected match")

    minimum_component_size = 9
    for pass_type in input_value.pass_types:
        component_sizes = rules.pass_type_component_sizes.get(pass_type)
        if component_sizes is None:
            raise ValueError(f"unsupported pass type: {pass_type}")
        match_count, bet_count = _parse_pass_type(pass_type)
        if bet_count > 1 and len(input_value.legs) != match_count:
            raise ValueError(f"{pass_type} requires exactly {match_count} legs")
        if bet_count == 1 and len(input_value.legs) < match_count:
            raise ValueError(f"{pass_type} requires at least {match_count} legs")
        if match_count > dynamic_maximum:
            raise ValueError(f"{pass_type} exceeds the selected plays' {dynamic_maximum}-leg limit")
        minimum_component_size = min(minimum_component_size, *component_sizes)
    if len(banker_ids) >= minimum_component_size:
        raise ValueError(f"banker count must be less than {minimum_component_size}")


def calculate_plan(
    input_value: CalculationInput, rules: SportteryRules = DEFAULT_SPORTTERY_RULES
) -> CalculationResult:
    validate_input(input_value, rules)
    banker_ids = _selected_bankers(input_value)
    bet_count = 0
    expanded_count = 0
    uncapped_bonus = Decimal("0")

    for pass_type in input_value.pass_types:
        for component_size in rules.pass_type_component_sizes[pass_type]:
            for combo in _expand_with_bankers(input_value.legs, component_size, banker_ids):
                expanded_count += 1
                original_bet_count = prod(len(leg.odds) for leg in combo)
                bet_count += original_bet_count
                void_legs = tuple(leg for leg in combo if leg.is_void)
                effective_legs = tuple(leg for leg in combo if not leg.is_void)
                void_duplicate_count = prod(len(leg.odds) for leg in void_legs)
                if not effective_legs:
                    line_payout = rules.unit_stake * input_value.multiplier * original_bet_count
                else:
                    line_payout = (
                        rules.unit_stake
                        * input_value.multiplier
                        * void_duplicate_count
                        * prod(max(leg.odds) for leg in effective_legs)
                    )
                uncapped_bonus += _money(line_payout)

    amount = _money(rules.unit_stake * input_value.multiplier * bet_count)
    uncapped_bonus = _money(uncapped_bonus)
    payout_cap_leg_count = max(
        _parse_pass_type(pass_type)[0] for pass_type in input_value.pass_types
    )
    payout_cap = _payout_cap_for_legs(payout_cap_leg_count, rules)
    return CalculationResult(
        rules_version=rules.version,
        bet_count=bet_count,
        amount=amount,
        expanded_combination_count=expanded_count,
        uncapped_maximum_bonus=uncapped_bonus,
        maximum_bonus=min(uncapped_bonus, payout_cap),
        payout_cap=payout_cap,
        payout_cap_exceeded=uncapped_bonus > payout_cap,
        amount_cap_exceeded=amount > rules.maximum_ticket_amount,
    )


def requires_result_recalculation(source: ResultCorrectionSource) -> bool:
    return source == "sporttery_official"


def validate_combo(
    legs: list[TicketLeg],
    pass_size: int,
    multiplier: int,
    rules: SportteryRules = DEFAULT_SPORTTERY_RULES,
) -> None:
    if not 1 <= pass_size <= 8:
        raise ValueError("pass_size must be between 1 and 8")
    validate_input(
        CalculationInput(tuple(legs), (f"{pass_size}x1",), multiplier),
        rules,
    )


@overload
def calculate_ticket(
    input_value: CalculationInput,
    pass_size: SportteryRules = DEFAULT_SPORTTERY_RULES,
    multiplier: int = 1,
) -> CalculationResult: ...


@overload
def calculate_ticket(
    input_value: list[TicketLeg],
    pass_size: int,
    multiplier: int = 1,
) -> TicketResult: ...


def calculate_ticket(
    input_value: CalculationInput | list[TicketLeg],
    pass_size: int | SportteryRules = DEFAULT_SPORTTERY_RULES,
    multiplier: int = 1,
) -> CalculationResult | TicketResult:
    if isinstance(input_value, CalculationInput):
        if isinstance(pass_size, int):
            raise TypeError("CalculationInput must be followed by SportteryRules, not pass_size")
        return calculate_plan(input_value, pass_size)
    if not isinstance(pass_size, int):
        raise TypeError("the legacy list API requires an integer pass_size")
    validate_combo(input_value, pass_size, multiplier)
    result = calculate_plan(CalculationInput(tuple(input_value), (f"{pass_size}x1",), multiplier))
    return TicketResult(
        bet_count=result.bet_count,
        amount=result.amount,
        maximum_bonus=result.maximum_bonus,
        effective_combination_count=result.bet_count,
    )
