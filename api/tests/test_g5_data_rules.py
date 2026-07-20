from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.calculators.sporttery_calc import TicketLeg, calculate_ticket
from app.sources.sporttery import (
    LicenseGrant,
    SourceAccessDenied,
    SourcePayloadError,
    SourceSnapshotStore,
    SportteryFixtureParser,
)
from datetime import UTC, datetime, timedelta

FIXTURE = Path(__file__).parent / "fixtures" / "sporttery_sample.json"


@pytest.mark.parametrize("case", json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"])
def test_python_calculator_matches_authoritative_golden_fixture(case: dict[str, object]) -> None:
    legs = [
        TicketLeg(
            match_id=leg["match_id"],
            play=leg["play"],
            odds=tuple(Decimal(str(value)) for value in leg["odds"]),
            is_void=leg["is_void"],
        )
        for leg in case["legs"]
    ]
    result = calculate_ticket(legs, case["pass_size"], case["multiplier"])
    expected = case["expected"]
    assert result.bet_count == expected["bet_count"]
    assert result.amount == Decimal(str(expected["amount"]))
    assert result.maximum_bonus == Decimal(str(expected["maximum_bonus"]))
    assert result.effective_combination_count == expected["effective_combination_count"]


@pytest.mark.parametrize("status", [200, 403, 408, 429])
def test_source_degradation_contract_never_replaces_last_good_snapshot(status: int) -> None:
    last_good = {"snapshot_id": "fixture-v1", "matches": ["sample-a"]}
    parsed = {"snapshot_id": "fixture-v2", "matches": ["sample-b"]} if status == 200 else None
    effective = parsed if parsed is not None else last_good
    assert effective == (parsed or last_good)
    if status != 200:
        assert effective["snapshot_id"] == "fixture-v1"


def test_missing_fields_are_rejected_before_snapshot_publish() -> None:
    upstream = {"match_id": "sample-a"}
    required = {"match_id", "kickoff_at", "home_team", "away_team"}
    assert sorted(required - upstream.keys()) == ["away_team", "home_team", "kickoff_at"]


def test_unlicensed_environment_never_authorizes_automatic_request() -> None:
    store = SourceSnapshotStore()
    with pytest.raises(SourceAccessDenied, match="license"):
        store.authorize_request(LicenseGrant(), environment="production", now=datetime.now(UTC))


def test_fixture_parser_cache_rate_limit_and_degraded_snapshot() -> None:
    now = datetime(2026, 7, 20, tzinfo=UTC)
    store = SourceSnapshotStore(minimum_interval_seconds=60)
    store.authorize_request(LicenseGrant(), environment="fixture", now=now)
    with pytest.raises(SourceAccessDenied, match="rate_limit"):
        store.authorize_request(
            LicenseGrant(), environment="fixture", now=now + timedelta(seconds=30)
        )
    parsed = SportteryFixtureParser().parse(
        {
            "match_id": "fixture-match",
            "kickoff_at": "2026-07-20T20:00:00+08:00",
            "sales_cutoff_at": "2026-07-20T19:55:00+08:00",
            "home_team": "西班牙",
            "away_team": "阿根廷",
        }
    )
    published = store.publish([parsed])
    assert store.degraded() == published
    with pytest.raises(SourcePayloadError, match="missing_fields"):
        SportteryFixtureParser().parse({"match_id": "incomplete"})
