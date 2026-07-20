import pytest

from app.gate0.capacity import WorkloadAssumptions, estimate_capacity


def test_capacity_model_exposes_provider_token_event_and_realtime_load() -> None:
    estimate = estimate_capacity(
        WorkloadAssumptions(
            daily_roundtables=20,
            matches_per_roundtable=5,
            provider_instances=3,
            attempts_per_instance=2,
            average_input_tokens=4_000,
            average_output_tokens=1_000,
            events_per_match=24,
            peak_live_users=500,
            retention_days=90,
        )
    )
    assert estimate.daily_provider_calls == 2_760
    assert estimate.daily_tokens == 13_800_000
    assert estimate.daily_events == 2_400
    assert estimate.retained_events == 216_000
    assert estimate.peak_realtime_connections == 500


def test_capacity_model_rejects_single_attempt_methodology() -> None:
    assumptions = WorkloadAssumptions(1, 1, 1, 1, 1, 1, 1, 1, 1)
    with pytest.raises(ValueError, match="attempts_per_instance"):
        estimate_capacity(assumptions)
