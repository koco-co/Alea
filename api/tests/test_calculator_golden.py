from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.calculators.sporttery_calc import (
    CalculationInput,
    SportteryPlay,
    TicketLeg,
    calculate_plan,
    calculate_ticket,
    requires_result_recalculation,
)

SAMPLE_FIXTURE = Path(__file__).parent / "fixtures" / "sporttery_sample.json"


def leg(
    match_id: str,
    play: SportteryPlay = "had",
    odds: tuple[str, ...] = ("2",),
    *,
    is_void: bool = False,
    is_banker: bool = False,
) -> TicketLeg:
    return TicketLeg(
        match_id=match_id,
        play=play,
        odds=tuple(Decimal(odd) for odd in odds),
        is_void=is_void,
        is_banker=is_banker,
    )


@pytest.mark.parametrize("case", json.loads(SAMPLE_FIXTURE.read_text(encoding="utf-8"))["cases"])
def test_gate_zero_shared_fixture_remains_compatible(case: dict[str, object]) -> None:
    legs = [
        TicketLeg(
            match_id=item["match_id"],
            play=item["play"],
            odds=tuple(Decimal(str(value)) for value in item["odds"]),
            is_void=item["is_void"],
        )
        for item in case["legs"]
    ]
    result = calculate_ticket(legs, case["pass_size"], case["multiplier"])
    expected = case["expected"]
    assert result.bet_count == expected["bet_count"]
    assert result.amount == Decimal(str(expected["amount"]))
    assert result.maximum_bonus == Decimal(str(expected["maximum_bonus"]))


@pytest.mark.parametrize(
    ("play", "maximum_pass_size"),
    [("had", 8), ("hhad", 8), ("crs", 4), ("ttg", 6), ("hafu", 4)],
)
def test_five_plays_have_golden_single_and_dynamic_limit(
    play: SportteryPlay, maximum_pass_size: int
) -> None:
    result = calculate_plan(CalculationInput((leg("a", play, ("1.8",)),), ("1x1",)))
    assert result.bet_count == 1
    assert result.amount == Decimal("2.00")
    assert result.maximum_bonus == Decimal("3.60")

    too_many = tuple(leg(str(index), play) for index in range(maximum_pass_size + 1))
    with pytest.raises(ValueError, match=f"at most {maximum_pass_size} legs"):
        calculate_plan(CalculationInput(too_many, (f"{maximum_pass_size}x1",)))


def test_compound_selections_use_highest_compatible_outcome_for_maximum_bonus() -> None:
    result = calculate_plan(
        CalculationInput(
            (leg("a", "had", ("1.5", "2.5")), leg("b", "ttg", ("1.8", "3"))),
            ("2x1",),
        )
    )
    assert result.bet_count == 4
    assert result.amount == Decimal("8.00")
    assert result.expanded_combination_count == 1
    assert result.maximum_bonus == Decimal("15.00")


@pytest.mark.parametrize("size", range(2, 9))
def test_simple_passes_two_through_eight(size: int) -> None:
    legs = tuple(leg(str(index), "had", ("1.5",)) for index in range(size))
    result = calculate_plan(CalculationInput(legs, (f"{size}x1",)))
    assert result.bet_count == 1
    assert result.expanded_combination_count == 1
    assert result.amount == Decimal("2.00")


def test_free_pass_banker_and_four_by_eleven_golden_results() -> None:
    free_pass = calculate_plan(CalculationInput((leg("a"), leg("b"), leg("c")), ("2x1", "3x1")))
    assert (free_pass.bet_count, free_pass.maximum_bonus) == (4, Decimal("40.00"))

    banker = calculate_plan(
        CalculationInput(
            (leg("a", is_banker=True), leg("b"), leg("c")),
            ("2x1",),
        )
    )
    assert (banker.bet_count, banker.maximum_bonus) == (2, Decimal("16.00"))

    four_by_eleven = calculate_plan(
        CalculationInput((leg("a"), leg("b"), leg("c"), leg("d")), ("4x11",))
    )
    assert four_by_eleven.expanded_combination_count == 11
    assert four_by_eleven.bet_count == 11
    assert four_by_eleven.amount == Decimal("22.00")
    assert four_by_eleven.maximum_bonus == Decimal("144.00")


def test_rounding_caps_and_void_recalculation() -> None:
    rounded = calculate_plan(CalculationInput((leg("a", odds=("1.0025",)),), ("1x1",)))
    assert rounded.maximum_bonus == Decimal("2.01")

    amount_overage = calculate_plan(
        CalculationInput(
            tuple(leg(str(index), odds=("1.5", "2")) for index in range(8)),
            ("8x247",),
        )
    )
    assert amount_overage.amount == Decimal("13088.00")
    assert amount_overage.amount_cap_exceeded is True

    payout_overage = calculate_plan(
        CalculationInput(
            tuple(leg(str(index), odds=("1000",)) for index in range(6)),
            ("6x1",),
        )
    )
    assert payout_overage.uncapped_maximum_bonus == Decimal("2000000000000000000.00")
    assert payout_overage.maximum_bonus == Decimal("1000000.00")
    assert payout_overage.payout_cap_exceeded is True

    void_result = calculate_plan(
        CalculationInput(
            (
                leg("void", odds=("1.8", "2.2"), is_void=True),
                leg("valid", odds=("3",)),
            ),
            ("2x1",),
        )
    )
    assert void_result.bet_count == 2
    assert void_result.amount == Decimal("4.00")
    assert void_result.maximum_bonus == Decimal("12.00")


def test_result_correction_only_recalculates_for_official_sporttery_change() -> None:
    assert requires_result_recalculation("sporttery_official") is True
    assert requires_result_recalculation("competition_organizer") is False
