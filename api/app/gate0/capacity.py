from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkloadAssumptions:
    daily_roundtables: int
    matches_per_roundtable: int
    provider_instances: int
    attempts_per_instance: int
    average_input_tokens: int
    average_output_tokens: int
    events_per_match: int
    peak_live_users: int
    retention_days: int

    def validate(self) -> None:
        values = self.__dict__
        if any(not isinstance(value, int) or value <= 0 for value in values.values()):
            raise ValueError("all capacity assumptions must be positive integers")
        if not 1 <= self.provider_instances <= 12:
            raise ValueError("provider_instances must be between 1 and 12")
        if self.attempts_per_instance < 2:
            raise ValueError("attempts_per_instance must be at least 2")


@dataclass(frozen=True)
class CapacityEstimate:
    daily_provider_calls: int
    daily_tokens: int
    daily_events: int
    retained_events: int
    peak_realtime_connections: int


def estimate_capacity(assumptions: WorkloadAssumptions) -> CapacityEstimate:
    assumptions.validate()
    selection_calls = 3 * assumptions.provider_instances * assumptions.attempts_per_instance
    per_match_calls = 3 * assumptions.provider_instances * assumptions.attempts_per_instance
    bet_calls = 3 * assumptions.provider_instances * assumptions.attempts_per_instance
    review_calls = 2 * assumptions.provider_instances * assumptions.attempts_per_instance
    daily_calls = assumptions.daily_roundtables * (
        selection_calls
        + assumptions.matches_per_roundtable * per_match_calls
        + bet_calls
        + review_calls
    )
    daily_events = (
        assumptions.daily_roundtables
        * assumptions.matches_per_roundtable
        * assumptions.events_per_match
    )
    return CapacityEstimate(
        daily_provider_calls=daily_calls,
        daily_tokens=daily_calls
        * (assumptions.average_input_tokens + assumptions.average_output_tokens),
        daily_events=daily_events,
        retained_events=daily_events * assumptions.retention_days,
        peak_realtime_connections=assumptions.peak_live_users,
    )
