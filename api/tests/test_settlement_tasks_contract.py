import pytest

from app.workers.dispatcher import TOPIC_TASKS
from app.workers.tasks import run_postmatch_review, run_ranking_recompute, run_settlement


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
def test_settlement_tasks_reject_incomplete_payload(task, payload) -> None:
    with pytest.raises(ValueError):
        task.run(payload)


def test_ranking_recompute_is_idempotent_acknowledgement() -> None:
    result = run_ranking_recompute.run({"settlement_run_id": "run-1"})
    assert result == {"status": "acknowledged", "settlement_run_id": "run-1"}


def test_postmatch_review_preserves_durable_identifiers() -> None:
    result = run_postmatch_review.run(
        {"settlement_run_id": "run-1", "notarized_prediction_id": "prediction-1"}
    )
    assert result == {
        "status": "deferred_to_review_executor",
        "settlement_run_id": "run-1",
        "notarized_prediction_id": "prediction-1",
    }
