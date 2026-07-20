from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev


@dataclass(frozen=True)
class ModelCapability:
    vendor: str
    model_id: str
    structured_output: bool
    usage: bool
    request_id: bool
    methods_passed: tuple[str, ...]
    attempts_per_instance: int | None
    enabled: bool


REQUIRED_METHODS = (
    "nominate_matches", "selection_debate", "vote_matches", "predict_score",
    "debate_response", "vote_score", "form_bet", "debate_bet", "vote_bet",
    "review_prediction", "review_methodology",
)


def can_enable(capability: ModelCapability) -> bool:
    return (
        capability.structured_output
        and capability.usage
        and capability.request_id
        and set(capability.methods_passed) == set(REQUIRED_METHODS)
        and capability.attempts_per_instance is not None
        and 2 <= capability.attempts_per_instance
    )


@dataclass(frozen=True)
class VarianceExperiment:
    output_hashes: tuple[str, ...]
    metric_values: tuple[float, ...]


def recommend_attempts_per_instance(experiment: VarianceExperiment) -> int:
    if len(experiment.output_hashes) < 5 or len(experiment.metric_values) < 5:
        raise ValueError("provider variance experiments require at least five repetitions")
    if len(experiment.output_hashes) != len(experiment.metric_values):
        raise ValueError("output hashes and metric values must have equal sample sizes")
    unique_ratio = len(set(experiment.output_hashes)) / len(experiment.output_hashes)
    metric_spread = pstdev(experiment.metric_values)
    if unique_ratio <= 0.4 and metric_spread <= 0.02:
        return 2
    if unique_ratio <= 0.7 and metric_spread <= 0.08:
        return 3
    return 5
