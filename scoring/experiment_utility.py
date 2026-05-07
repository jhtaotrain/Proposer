from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from simulators.damped_oscillator import (
    OscillatorExperimentCondition,
    OscillatorInitialState,
    hypothesis_from_model_payload,
    simulate_trajectory,
)


@dataclass(frozen=True)
class ExperimentUtilityResult:
    experiment_id: str
    experiment_name: str
    utility_score: float
    measured_channels: tuple[str, ...]
    compared_hypotheses: tuple[str, ...]
    pairwise_channel_disagreement: dict[str, float]
    metadata: dict[str, Any]


def score_candidate_experiment(
    *,
    experiment: dict[str, Any],
    compatible_hypotheses: list[dict[str, Any]],
    baseline_initial_state: dict[str, float],
) -> ExperimentUtilityResult:
    """
    Score one candidate experiment by simulating each compatible hypothesis and
    measuring average pairwise disagreement on the experiment's measured channels.

    Version 1 uses average absolute trajectory differences over time, averaged
    across hypothesis pairs and measured channels.
    """
    if len(compatible_hypotheses) < 2:
        raise ValueError("at least two compatible hypotheses are required to score disagreement")

    condition = _condition_from_candidate_experiment(
        experiment=experiment,
        baseline_initial_state=baseline_initial_state,
    )
    traces = [
        (
            hypothesis["name"],
            simulate_trajectory(
                hypothesis=hypothesis_from_model_payload(hypothesis["model"]),
                condition=condition,
            ),
        )
        for hypothesis in compatible_hypotheses
    ]

    pair_scores = []
    channel_totals = {channel: 0.0 for channel in condition.measured_channels}
    pair_count = 0

    for first_index in range(len(traces)):
        first_name, first_trace = traces[first_index]
        for second_index in range(first_index + 1, len(traces)):
            second_name, second_trace = traces[second_index]
            pair_count += 1

            channel_scores = {
                channel: _mean_absolute_difference(
                    first_trace.channels[channel],
                    second_trace.channels[channel],
                )
                for channel in condition.measured_channels
            }
            pair_utility = sum(channel_scores.values()) / len(channel_scores)
            pair_scores.append(pair_utility)

            for channel, score in channel_scores.items():
                channel_totals[channel] += score

    pairwise_channel_disagreement = {
        channel: total / pair_count for channel, total in channel_totals.items()
    }
    utility_score = sum(pair_scores) / len(pair_scores)

    return ExperimentUtilityResult(
        experiment_id=experiment["experiment_id"],
        experiment_name=experiment["name"],
        utility_score=utility_score,
        measured_channels=condition.measured_channels,
        compared_hypotheses=tuple(hypothesis["name"] for hypothesis in compatible_hypotheses),
        pairwise_channel_disagreement=pairwise_channel_disagreement,
        metadata={
            "time_step": condition.time_step,
            "duration": condition.duration,
            "num_hypotheses": len(compatible_hypotheses),
            "num_pairs": pair_count,
        },
    )


def rank_candidate_experiments(
    *,
    candidate_experiments: list[dict[str, Any]],
    compatible_hypotheses: list[dict[str, Any]],
    baseline_initial_state: dict[str, float],
) -> list[ExperimentUtilityResult]:
    results = [
        score_candidate_experiment(
            experiment=experiment,
            compatible_hypotheses=compatible_hypotheses,
            baseline_initial_state=baseline_initial_state,
        )
        for experiment in candidate_experiments
    ]
    return sorted(results, key=lambda result: result.utility_score, reverse=True)


def experiment_ranking_to_oracle_payload(
    ranked_results: list[ExperimentUtilityResult],
    *,
    true_hypothesis_id: str | None = None,
    utility_score_type: str = "pairwise_average_disagreement",
    explanation: str | None = None,
) -> dict[str, Any]:
    if not ranked_results:
        raise ValueError("ranked_results must not be empty")

    best_result = ranked_results[0]
    return {
        "true_hypothesis_id": true_hypothesis_id,
        "best_experiment_id": best_result.experiment_id,
        "experiment_utilities": {
            result.experiment_id: result.utility_score for result in ranked_results
        },
        "utility_score_type": utility_score_type,
        "explanation": explanation,
    }


def _condition_from_candidate_experiment(
    *,
    experiment: dict[str, Any],
    baseline_initial_state: dict[str, float],
) -> OscillatorExperimentCondition:
    measurement_plan = experiment.get("measurement_plan") or {}
    time_window = measurement_plan.get("time_window") or {}
    channels = tuple(measurement_plan.get("channels") or ["x"])
    sampling_rate = float(measurement_plan.get("sampling_rate", 10.0))

    start = float(time_window.get("start", 0.0))
    end = float(time_window["end"]) if "end" in time_window else None
    if end is None:
        raise ValueError(
            f"candidate experiment {experiment.get('experiment_id', '<unknown>')} is missing measurement_plan.time_window.end"
        )
    if abs(start) > 1e-9:
        raise ValueError("version 1 expects candidate experiment time windows to start at 0.0")

    changes = experiment.get("changes") or {}
    experiment_initial_state = dict(baseline_initial_state)

    if "initial_state" in changes:
        for key, value in changes["initial_state"].items():
            experiment_initial_state[key] = float(value)

    return OscillatorExperimentCondition(
        duration=end - start,
        time_step=1.0 / sampling_rate,
        initial_state=OscillatorInitialState(
            x=float(experiment_initial_state["x"]),
            v=float(experiment_initial_state["v"]),
        ),
        measured_channels=channels,
    )


def _mean_absolute_difference(first: list[float], second: list[float]) -> float:
    if len(first) != len(second):
        raise ValueError("series lengths must match to compute disagreement")

    return sum(abs(a - b) for a, b in zip(first, second)) / len(first)
