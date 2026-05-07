from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from simulators.damped_oscillator import (
    OscillatorExperimentCondition,
    OscillatorInitialState,
    SimulationTrace,
    hypothesis_from_model_payload,
    simulate_trajectory,
)


@dataclass(frozen=True)
class ChannelFitScore:
    channel: str
    mse: float
    mae: float


@dataclass(frozen=True)
class HypothesisFitResult:
    hypothesis_name: str
    score_type: str
    aggregate_score: float
    per_channel: dict[str, ChannelFitScore]
    measured_channels: tuple[str, ...]
    predicted_trace: SimulationTrace


def score_hypothesis_fit(
    *,
    hypothesis_name: str,
    model_payload: dict[str, Any],
    observation_episode: dict[str, Any],
    initial_state: dict[str, float],
    score_type: str = "mse",
) -> HypothesisFitResult:
    """
    Score how well a single oscillator hypothesis explains one observation episode.

    The observation episode is expected to follow the structure used in the JSON
    scenario format:
    - measured_channels
    - time
    - values

    For version 1, the simulator condition is reconstructed directly from the
    observation time grid and a caller-provided initial state.
    """
    measured_channels = tuple(observation_episode["measured_channels"])
    time = list(observation_episode["time"])
    values = dict(observation_episode["values"])

    _validate_observation_episode(
        measured_channels=measured_channels,
        time=time,
        values=values,
    )

    condition = _condition_from_observation(
        measured_channels=measured_channels,
        time=time,
        initial_state=initial_state,
    )
    hypothesis = hypothesis_from_model_payload(model_payload)
    predicted_trace = simulate_trajectory(hypothesis=hypothesis, condition=condition)

    per_channel = {
        channel: _score_channel(
            channel=channel,
            observed_values=values[channel],
            predicted_values=predicted_trace.channels[channel],
        )
        for channel in measured_channels
    }

    aggregate_score = _aggregate_score(per_channel=per_channel, score_type=score_type)

    return HypothesisFitResult(
        hypothesis_name=hypothesis_name,
        score_type=score_type,
        aggregate_score=aggregate_score,
        per_channel=per_channel,
        measured_channels=measured_channels,
        predicted_trace=predicted_trace,
    )


def rank_hypotheses_by_fit(
    *,
    hypotheses: list[dict[str, Any]],
    observation_episode: dict[str, Any],
    initial_state: dict[str, float],
    score_type: str = "mse",
) -> list[HypothesisFitResult]:
    """
    Score a list of hypotheses and return them sorted from best fit to worst fit.

    Each hypothesis dict is expected to contain:
    - name
    - model
    """
    results = [
        score_hypothesis_fit(
            hypothesis_name=hypothesis["name"],
            model_payload=hypothesis["model"],
            observation_episode=observation_episode,
            initial_state=initial_state,
            score_type=score_type,
        )
        for hypothesis in hypotheses
    ]
    return sorted(results, key=lambda result: result.aggregate_score)


def _condition_from_observation(
    *,
    measured_channels: tuple[str, ...],
    time: list[float],
    initial_state: dict[str, float],
) -> OscillatorExperimentCondition:
    if len(time) < 2:
        raise ValueError("at least two time points are required to infer a simulation step")

    duration = time[-1] - time[0]
    if duration <= 0.0:
        raise ValueError("observation duration must be positive")

    time_deltas = [time[index + 1] - time[index] for index in range(len(time) - 1)]
    step = time_deltas[0]
    if step <= 0.0:
        raise ValueError("time points must be strictly increasing")

    tolerance = 1e-9
    if any(abs(delta - step) > tolerance for delta in time_deltas[1:]):
        raise ValueError("version 1 requires uniformly sampled observation times")

    if abs(time[0]) > tolerance:
        raise ValueError("version 1 expects observation time to start at 0.0")

    return OscillatorExperimentCondition(
        duration=duration,
        time_step=step,
        initial_state=OscillatorInitialState(
            x=float(initial_state["x"]),
            v=float(initial_state["v"]),
        ),
        measured_channels=measured_channels,
    )


def _validate_observation_episode(
    *,
    measured_channels: tuple[str, ...],
    time: list[float],
    values: dict[str, list[float]],
) -> None:
    if not measured_channels:
        raise ValueError("observation episode must include at least one measured channel")
    if len(time) < 2:
        raise ValueError("observation episode must include at least two time points")

    time_length = len(time)
    missing_channels = [channel for channel in measured_channels if channel not in values]
    if missing_channels:
        raise ValueError(f"missing observed values for channels: {missing_channels}")

    mismatched_lengths = [
        channel for channel in measured_channels if len(values[channel]) != time_length
    ]
    if mismatched_lengths:
        raise ValueError(
            "observation value length must match time length for channels: "
            f"{mismatched_lengths}"
        )


def _score_channel(
    *,
    channel: str,
    observed_values: list[float],
    predicted_values: list[float],
) -> ChannelFitScore:
    if len(observed_values) != len(predicted_values):
        raise ValueError(
            f"observed and predicted series lengths do not match for channel {channel}"
        )

    squared_error_sum = 0.0
    absolute_error_sum = 0.0
    for observed_value, predicted_value in zip(observed_values, predicted_values):
        error = observed_value - predicted_value
        squared_error_sum += error * error
        absolute_error_sum += abs(error)

    num_points = len(observed_values)
    return ChannelFitScore(
        channel=channel,
        mse=squared_error_sum / num_points,
        mae=absolute_error_sum / num_points,
    )


def _aggregate_score(
    *,
    per_channel: dict[str, ChannelFitScore],
    score_type: str,
) -> float:
    if score_type == "mse":
        return sum(score.mse for score in per_channel.values()) / len(per_channel)

    if score_type == "mae":
        return sum(score.mae for score in per_channel.values()) / len(per_channel)

    raise ValueError(f"unsupported score_type: {score_type}")
