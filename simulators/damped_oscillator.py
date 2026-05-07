from __future__ import annotations

from dataclasses import dataclass, field
from math import cos
from typing import Any


@dataclass(frozen=True)
class OscillatorInitialState:
    x: float
    v: float


@dataclass(frozen=True)
class OscillatorExperimentCondition:
    duration: float
    time_step: float
    initial_state: OscillatorInitialState
    measured_channels: tuple[str, ...] = ("x",)


@dataclass(frozen=True)
class DriveConfig:
    amplitude: float
    frequency: float
    phase: float = 0.0


@dataclass(frozen=True)
class LinearDampingHypothesis:
    m: float
    c: float
    k: float
    drive: DriveConfig | None = None


@dataclass(frozen=True)
class NonlinearDampingHypothesis:
    m: float
    c1: float
    c2: float
    k: float
    drive: DriveConfig | None = None


OscillatorHypothesis = LinearDampingHypothesis | NonlinearDampingHypothesis


@dataclass(frozen=True)
class SimulationTrace:
    time: list[float]
    channels: dict[str, list[float]]
    metadata: dict[str, Any] = field(default_factory=dict)


def simulate_trajectory(
    hypothesis: OscillatorHypothesis,
    condition: OscillatorExperimentCondition,
) -> SimulationTrace:
    """
    Simulate a damped oscillator trajectory with a fixed-step RK4 integrator.

    The supported hypothesis families are:
    - linear damping: m x'' + c x' + k x = drive(t)
    - weak nonlinear damping: m x'' + (c1 + c2 |x'|) x' + k x = drive(t)
    """
    _validate_condition(condition)

    num_steps = int(round(condition.duration / condition.time_step))
    time = [step * condition.time_step for step in range(num_steps + 1)]

    x = condition.initial_state.x
    v = condition.initial_state.v

    full_channels = {"x": [x], "v": [v]}

    for step_index in range(num_steps):
        t = time[step_index]
        x, v = _rk4_step(hypothesis=hypothesis, t=t, x=x, v=v, dt=condition.time_step)
        full_channels["x"].append(x)
        full_channels["v"].append(v)

    channels = {
        channel: full_channels[channel]
        for channel in condition.measured_channels
    }

    return SimulationTrace(
        time=time,
        channels=channels,
        metadata={
            "hypothesis_type": type(hypothesis).__name__,
            "duration": condition.duration,
            "time_step": condition.time_step,
        },
    )


def hypothesis_from_model_payload(model_payload: dict[str, Any]) -> OscillatorHypothesis:
    """
    Convert a schema-style hypothesis model payload into a simulator hypothesis.

    Expected parameter keys:
    - linear damping: m, c, k
    - nonlinear damping: m, c1, c2, k

    Optional drive keys:
    - A / amplitude
    - omega / frequency
    - phase
    """
    parameters = dict(model_payload.get("parameters", {}))
    drive = _drive_from_parameters(parameters)

    if {"m", "c", "k"}.issubset(parameters):
        return LinearDampingHypothesis(
            m=float(parameters["m"]),
            c=float(parameters["c"]),
            k=float(parameters["k"]),
            drive=drive,
        )

    if {"m", "c1", "c2", "k"}.issubset(parameters):
        return NonlinearDampingHypothesis(
            m=float(parameters["m"]),
            c1=float(parameters["c1"]),
            c2=float(parameters["c2"]),
            k=float(parameters["k"]),
            drive=drive,
        )

    raise ValueError(
        "unsupported oscillator parameterization; expected linear {m,c,k} or nonlinear {m,c1,c2,k}"
    )


def condition_from_measurement_plan(
    *,
    duration: float,
    sampling_rate: float,
    initial_state: dict[str, float],
    measured_channels: list[str] | tuple[str, ...],
) -> OscillatorExperimentCondition:
    if sampling_rate <= 0.0:
        raise ValueError("sampling_rate must be positive")

    return OscillatorExperimentCondition(
        duration=duration,
        time_step=1.0 / sampling_rate,
        initial_state=OscillatorInitialState(
            x=float(initial_state["x"]),
            v=float(initial_state["v"]),
        ),
        measured_channels=tuple(measured_channels),
    )


def _validate_condition(condition: OscillatorExperimentCondition) -> None:
    if condition.duration <= 0.0:
        raise ValueError("duration must be positive")
    if condition.time_step <= 0.0:
        raise ValueError("time_step must be positive")
    if not condition.measured_channels:
        raise ValueError("at least one measured channel is required")

    unsupported_channels = [
        channel for channel in condition.measured_channels if channel not in {"x", "v"}
    ]
    if unsupported_channels:
        raise ValueError(f"unsupported measured channels: {unsupported_channels}")


def _rk4_step(
    *,
    hypothesis: OscillatorHypothesis,
    t: float,
    x: float,
    v: float,
    dt: float,
) -> tuple[float, float]:
    k1_x, k1_v = _derivatives(hypothesis=hypothesis, t=t, x=x, v=v)
    k2_x, k2_v = _derivatives(
        hypothesis=hypothesis,
        t=t + 0.5 * dt,
        x=x + 0.5 * dt * k1_x,
        v=v + 0.5 * dt * k1_v,
    )
    k3_x, k3_v = _derivatives(
        hypothesis=hypothesis,
        t=t + 0.5 * dt,
        x=x + 0.5 * dt * k2_x,
        v=v + 0.5 * dt * k2_v,
    )
    k4_x, k4_v = _derivatives(
        hypothesis=hypothesis,
        t=t + dt,
        x=x + dt * k3_x,
        v=v + dt * k3_v,
    )

    next_x = x + (dt / 6.0) * (k1_x + 2.0 * k2_x + 2.0 * k3_x + k4_x)
    next_v = v + (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v)
    return next_x, next_v


def _derivatives(
    *,
    hypothesis: OscillatorHypothesis,
    t: float,
    x: float,
    v: float,
) -> tuple[float, float]:
    drive_force = _drive_force(hypothesis.drive, t)

    if isinstance(hypothesis, LinearDampingHypothesis):
        acceleration = (drive_force - hypothesis.c * v - hypothesis.k * x) / hypothesis.m
        return v, acceleration

    damping = (hypothesis.c1 + hypothesis.c2 * abs(v)) * v
    acceleration = (drive_force - damping - hypothesis.k * x) / hypothesis.m
    return v, acceleration


def _drive_from_parameters(parameters: dict[str, Any]) -> DriveConfig | None:
    amplitude = parameters.get("A", parameters.get("amplitude"))
    frequency = parameters.get("omega", parameters.get("frequency"))
    if amplitude is None or frequency is None:
        return None

    return DriveConfig(
        amplitude=float(amplitude),
        frequency=float(frequency),
        phase=float(parameters.get("phase", 0.0)),
    )


def _drive_force(drive: DriveConfig | None, t: float) -> float:
    if drive is None:
        return 0.0
    return drive.amplitude * cos(drive.frequency * t + drive.phase)
