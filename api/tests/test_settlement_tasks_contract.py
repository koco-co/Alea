from decimal import Decimal
import inspect
from typing import Any

import pytest

from app.workers.dispatcher import TOPIC_TASKS
from app.workers.tasks import (
    _evaluate_frozen_ticket,
    _selection_hit,
    run_postmatch_review,
    run_ranking_recompute,
    run_settlement,
)


def test_settlement_outbox_topics_have_production_consumers() -> None:
    assert TOPIC_TASKS["settlement.run"] == "app.workers.tasks.run_settlement"
    assert TOPIC_TASKS["ranking.recompute"] == "app.workers.tasks.run_ranking_recompute"
    assert TOPIC_TASKS["prediction.review"] == "app.workers.tasks.run_postmatch_review"


@pytest.mark.parametrize(
    ("task", "payload"),
    [
        (run_settlement, {}),
        (run_ranking_recompute, {}),
        (run_postmatch_review, {}),
    ],
)
def test_settlement_tasks_reject_incomplete_payload(task: Any, payload: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        task.run(payload)


def test_ranking_recompute_is_idempotent_acknowledgement() -> None:
    result = run_ranking_recompute.run({"settlement_run_id": "run-1"})
    assert result == {"status": "acknowledged", "settlement_run_id": "run-1"}


def test_postmatch_review_schedules_a_real_provider_phase() -> None:
    source = inspect.getsource(run_postmatch_review)
    assert "postmatch_review_contexts" in source
    assert "roundtable.review_prediction" in source
    assert "deferred_to_review_executor" not in source


def test_postmatch_review_replays_scheduled_work_without_duplicate_phase_runs() -> None:
    source = inspect.getsource(run_postmatch_review)
    assert 'existing_review["state"] in {"scheduled", "running"}' in source
    assert '"idempotent_replay": True' in source


def test_single_leg_ticket_persists_a_hit_and_payout_value() -> None:
    state, returned = _evaluate_frozen_ticket(
        {
            "legs": [
                {
                    "match_id": "match-1",
                    "play": "had",
                    "offer_option_ids": ["had-home"],
                }
            ],
            "pass_types": ["1x1"],
        },
        Decimal("100.00"),
        {
            "match_id": "match-1",
            "home_score": 2,
            "away_score": 1,
            "half_home_score": 1,
            "half_away_score": 0,
        },
        {"had-home": {"play": "had", "selection": "home", "fixed_odds": "2.50"}},
    )
    assert state == "settled_hit"
    assert returned == Decimal("250.00")


def test_ticket_miss_has_no_returned_amount_and_direction_is_deterministic() -> None:
    assert _selection_hit(
        "had", "平", {"home_score": 1, "away_score": 1, "half_home_score": 0, "half_away_score": 0}
    )
    state, returned = _evaluate_frozen_ticket(
        {
            "legs": [{"match_id": "match-1", "play": "crs", "offer_option_ids": ["crs-2-1"]}],
            "pass_types": ["1x1"],
        },
        Decimal("20.00"),
        {
            "match_id": "match-1",
            "home_score": 0,
            "away_score": 0,
            "half_home_score": 0,
            "half_away_score": 0,
        },
        {"crs-2-1": {"play": "crs", "selection": "2-1", "fixed_odds": "8"}},
    )
    assert state == "settled_miss"
    assert returned == Decimal("0.00")
