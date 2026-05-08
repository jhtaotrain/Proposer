from __future__ import annotations

import argparse
import json
from copy import deepcopy
from math import ceil
from pathlib import Path
import random
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scoring.ambiguity import (
    ambiguity_result_to_schema_payload,
    label_ambiguity_from_hypotheses,
)
from scoring.experiment_utility import (
    experiment_ranking_to_oracle_payload,
    rank_candidate_experiments,
)
from simulators.damped_oscillator import (
    hypothesis_from_model_payload,
    simulate_trajectory,
)


OUTPUT_DIR = Path("generated_scenarios")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate oracle-labeled damped-oscillator benchmark scenarios."
    )
    parser.add_argument(
        "--num-scenarios",
        type=int,
        default=20,
        help="Number of accepted scenarios to write.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for sampled scenario specs.",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR.as_posix(),
        help="Directory for generated scenario JSON files.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Maximum sampled specs to try before stopping.",
    )
    parser.add_argument(
        "--clear-output",
        action="store_true",
        help="Delete existing generated_osc_*.json files in the output directory before writing.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    if args.clear_output:
        for path in output_dir.glob("generated_osc_*.json"):
            path.unlink()

    scenario_specs = generate_scenario_specs(
        num_scenarios=args.num_scenarios,
        seed=args.seed,
        max_attempts=args.max_attempts,
    )

    written_files = []
    for spec in scenario_specs:
        scenario = build_scenario(spec)
        output_path = output_dir / f"{scenario['scenario_id']}.json"
        output_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
        written_files.append(output_path)

    print(f"generated {len(written_files)} scenario file(s)")
    for path in written_files:
        print(path.as_posix())
    return 0


def generate_scenario_specs(
    *,
    num_scenarios: int,
    seed: int,
    max_attempts: int | None = None,
) -> list[dict[str, Any]]:
    if num_scenarios <= 0:
        raise ValueError("num_scenarios must be positive")

    rng = random.Random(seed)
    attempts_limit = max_attempts or num_scenarios * 200
    specs: list[dict[str, Any]] = []
    best_family_counts: dict[str, int] = {}
    max_per_best_family = max(2, ceil(num_scenarios * 0.45))

    legacy_specs = [
        _nonlinear_vs_linear_short_window_spec(),
        _linear_vs_driven_short_window_spec(),
    ]
    for legacy_spec in legacy_specs[:num_scenarios]:
        scenario = build_scenario(legacy_spec)
        best_family = _best_experiment_family(scenario)
        specs.append(legacy_spec)
        best_family_counts[best_family] = best_family_counts.get(best_family, 0) + 1

    attempts = 0
    candidate_index = 1
    while len(specs) < num_scenarios and attempts < attempts_limit:
        attempts += 1
        spec = _sample_scenario_spec(
            rng=rng,
            scenario_index=candidate_index,
            seed=seed,
        )
        candidate_index += 1

        try:
            scenario = build_scenario(spec)
        except ValueError:
            continue

        if not _passes_quality_filters(scenario):
            continue

        best_family = _best_experiment_family(scenario)
        if best_family_counts.get(best_family, 0) >= max_per_best_family:
            continue

        specs.append(spec)
        best_family_counts[best_family] = best_family_counts.get(best_family, 0) + 1

    if len(specs) < num_scenarios:
        print(
            "warning: generated only "
            f"{len(specs)} accepted scenario(s) after {attempts} attempt(s)",
            file=sys.stderr,
        )

    return specs


def build_scenario(spec: dict[str, Any]) -> dict[str, Any]:
    true_hypothesis = spec["true_hypothesis"]
    baseline_condition = deepcopy(spec["baseline_condition"])
    baseline_initial_state = deepcopy(baseline_condition["initial_state"])

    observation_episode = _generate_observation_episode(
        episode_id="obs_1",
        condition_id=baseline_condition["condition_id"],
        hypothesis=true_hypothesis,
        condition=baseline_condition,
    )

    hypotheses = [
        _build_hypothesis_entry(item)
        for item in spec["candidate_hypotheses"]
    ]

    ambiguity_result = label_ambiguity_from_hypotheses(
        hypotheses=hypotheses,
        observation_episode=observation_episode,
        initial_state=baseline_initial_state,
        score_type="mse",
        max_score_gap=spec["ambiguity_rule"]["max_score_gap"],
        ambiguity_type=spec["ambiguity_rule"]["ambiguity_type"],
    )

    name_to_id = {hypothesis["name"]: hypothesis["hypothesis_id"] for hypothesis in hypotheses}
    ambiguity_payload = ambiguity_result_to_schema_payload(
        ambiguity_result,
        hypothesis_name_to_id=name_to_id,
    )

    candidate_experiments = deepcopy(spec["candidate_experiments"])
    compatible_hypotheses = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis["name"] in ambiguity_result.compatible_hypotheses
    ]

    experiment_ranking = rank_candidate_experiments(
        candidate_experiments=candidate_experiments,
        compatible_hypotheses=compatible_hypotheses,
        baseline_initial_state=baseline_initial_state,
    )
    oracle_payload = experiment_ranking_to_oracle_payload(
        experiment_ranking,
        true_hypothesis_id=spec["true_hypothesis"]["hypothesis_id"],
        explanation=(
            "Generated by the oscillator backend oracle using pairwise disagreement "
            "over simulated candidate experiment responses."
        ),
    )

    return {
        "schema_version": "0.1",
        "scenario_id": spec["scenario_id"],
        "domain": "damped_oscillator",
        "goal": deepcopy(spec["goal"]),
        "observations": {
            "episodes": [observation_episode],
            "observability": deepcopy(spec["observability"]),
        },
        "hypotheses": hypotheses,
        "candidate_experiments": candidate_experiments,
        "ambiguity_assessment": ambiguity_payload,
        "ground_truth": oracle_payload,
        "metadata": deepcopy(spec["metadata"]),
    }


def _generate_observation_episode(
    *,
    episode_id: str,
    condition_id: str,
    hypothesis: dict[str, Any],
    condition: dict[str, Any],
) -> dict[str, Any]:
    simulator_hypothesis = hypothesis_from_model_payload(hypothesis["model"])
    trace = simulate_trajectory(
        hypothesis=simulator_hypothesis,
        condition=_simulator_condition_from_config(condition),
    )

    return {
        "episode_id": episode_id,
        "condition_id": condition_id,
        "measured_channels": list(condition["measured_channels"]),
        "time": trace.time,
        "values": trace.channels,
        "noise_model": {
            "type": "none",
            "parameters": {},
        },
        "summary_stats": {
            "window_duration": condition["duration"],
            "sampling_rate": condition["sampling_rate"],
        },
        "metadata": {
            "initial_state": deepcopy(condition["initial_state"]),
        },
    }


def _build_hypothesis_entry(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothesis_id": spec["hypothesis_id"],
        "name": spec["name"],
        "description": spec["description"],
        "family": "ode",
        "mechanism_tags": list(spec["mechanism_tags"]),
        "model": deepcopy(spec["model"]),
    }


def _simulator_condition_from_config(condition: dict[str, Any]):
    from simulators.damped_oscillator import (
        OscillatorExperimentCondition,
        OscillatorInitialState,
    )

    return OscillatorExperimentCondition(
        duration=float(condition["duration"]),
        time_step=1.0 / float(condition["sampling_rate"]),
        initial_state=OscillatorInitialState(
            x=float(condition["initial_state"]["x"]),
            v=float(condition["initial_state"]["v"]),
        ),
        measured_channels=tuple(condition["measured_channels"]),
    )


def _common_goal() -> dict[str, Any]:
    return {
        "type": "distinguish_hypotheses",
        "description": "Determine which mechanism best explains the current damped-oscillator observations.",
        "success_criterion": "Choose the candidate experiment expected to produce the largest separation between the remaining plausible hypotheses.",
    }


def _common_candidate_experiments() -> list[dict[str, Any]]:
    return _candidate_experiments_for_condition(
        baseline_duration=0.5,
        baseline_sampling_rate=10.0,
        library_style="window",
    )


def _candidate_experiments_for_condition(
    *,
    baseline_duration: float,
    baseline_sampling_rate: float,
    library_style: str,
) -> list[dict[str, Any]]:
    if library_style == "excitation":
        window_ratios = [1.5, 2.0, 3.0]
        velocity_window_ratios = [1.0, 2.0]
        initial_velocity_values = [0.75, 1.5, 2.25]
    elif library_style == "velocity":
        window_ratios = [1.5, 2.0]
        velocity_window_ratios = [2.0, 4.0]
        initial_velocity_values = [0.75, 1.5]
    elif library_style == "sampling":
        window_ratios = [1.25, 1.5, 2.0]
        velocity_window_ratios = [1.0, 1.5]
        initial_velocity_values = [0.75, 1.5]
    else:
        window_ratios = [2.0, 4.0, 6.0]
        velocity_window_ratios = [1.0, 2.0]
        initial_velocity_values = [0.75, 1.5]

    sampling_ratios = [2.0, 5.0, 10.0]
    reference_initial_velocity = 0.75
    experiments: list[dict[str, Any]] = []
    next_id = 1

    for ratio, cost in zip(window_ratios, [1.0, 1.2, 1.4]):
        experiments.append(
            _window_experiment(
                f"E{next_id}",
                end_time=baseline_duration * ratio,
                sampling_rate=baseline_sampling_rate,
                baseline_end_time=baseline_duration,
                cost=cost,
            )
        )
        next_id += 1

    for ratio, cost in zip(sampling_ratios, [1.0, 1.2, 1.4]):
        experiments.append(
            _sampling_experiment(
                f"E{next_id}",
                sampling_rate=baseline_sampling_rate * ratio,
                baseline_sampling_rate=baseline_sampling_rate,
                baseline_duration=baseline_duration,
                cost=cost,
            )
        )
        next_id += 1

    for ratio, cost in zip(velocity_window_ratios, [1.5, 1.8]):
        experiments.append(
            _velocity_channel_experiment(
                f"E{next_id}",
                duration=baseline_duration * ratio,
                sampling_rate=baseline_sampling_rate,
                baseline_end_time=baseline_duration,
                cost=cost,
            )
        )
        next_id += 1

    for initial_velocity, cost in zip(initial_velocity_values, [1.2, 1.5, 1.8]):
        experiments.append(
            _initial_velocity_experiment(
                f"E{next_id}",
                initial_velocity=initial_velocity,
                reference_initial_velocity=reference_initial_velocity,
                duration=baseline_duration * 2.0,
                baseline_end_time=baseline_duration,
                sampling_rate=baseline_sampling_rate,
                cost=cost,
            )
        )
        next_id += 1

    return experiments


def _legacy_common_candidate_experiments() -> list[dict[str, Any]]:
    experiments = [
        _window_experiment("E1", end_time=1.0, sampling_rate=10.0, baseline_end_time=0.5, cost=1.0),
        _window_experiment("E2", end_time=2.0, sampling_rate=10.0, baseline_end_time=0.5, cost=1.2),
        _window_experiment("E3", end_time=3.0, sampling_rate=10.0, baseline_end_time=0.5, cost=1.4),
        _sampling_experiment("E4", sampling_rate=20.0, baseline_sampling_rate=10.0, baseline_duration=0.5, cost=1.0),
        _sampling_experiment("E5", sampling_rate=50.0, baseline_sampling_rate=10.0, baseline_duration=0.5, cost=1.2),
        _sampling_experiment("E6", sampling_rate=100.0, baseline_sampling_rate=10.0, baseline_duration=0.5, cost=1.4),
        _velocity_channel_experiment("E7", duration=0.5, sampling_rate=10.0, baseline_end_time=0.5, cost=1.5),
        _velocity_channel_experiment("E8", duration=1.0, sampling_rate=10.0, baseline_end_time=0.5, cost=1.8),
        _initial_velocity_experiment(
            "E9",
            initial_velocity=0.75,
            reference_initial_velocity=0.75,
            duration=1.0,
            baseline_end_time=0.5,
            sampling_rate=10.0,
            cost=1.2,
        ),
        _initial_velocity_experiment(
            "E10",
            initial_velocity=1.5,
            reference_initial_velocity=0.75,
            duration=1.0,
            baseline_end_time=0.5,
            sampling_rate=10.0,
            cost=1.5,
        ),
    ]
    return experiments


def _window_experiment(
    experiment_id: str,
    *,
    end_time: float,
    sampling_rate: float,
    baseline_end_time: float,
    cost: float,
) -> dict[str, Any]:
    window_ratio = end_time / baseline_end_time
    return {
        "experiment_id": experiment_id,
        "name": f"extend_window_by_{_format_ratio_token(window_ratio)}x",
        "description": (
            f"Measure position over a window {window_ratio:.1f}x the baseline duration using the same initial condition."
        ),
        "intervention_type": "measurement_change",
        "changes": {
            "time_window": {"start": 0.0, "end": end_time},
        },
        "measurement_plan": {
            "channels": ["x"],
            "sampling_rate": sampling_rate,
            "time_window": {"start": 0.0, "end": end_time},
            "metadata": {
                "experiment_family": "extend_observation_window",
                "parameterization": {
                    "window_ratio": window_ratio,
                    "baseline_end_time": baseline_end_time,
                    "end_time": end_time,
                },
            },
        },
        "ambiguity_tags": ["short_window"],
        "cost": cost,
        "metadata": {
            "experiment_family": "extend_observation_window",
            "parameterization": {
                "window_ratio": window_ratio,
                "baseline_end_time": baseline_end_time,
                "end_time": end_time,
                "sampling_rate": sampling_rate,
            },
        },
    }


def _sampling_experiment(
    experiment_id: str,
    *,
    sampling_rate: float,
    baseline_sampling_rate: float,
    baseline_duration: float,
    cost: float,
) -> dict[str, Any]:
    sampling_ratio = sampling_rate / baseline_sampling_rate
    return {
        "experiment_id": experiment_id,
        "name": f"increase_sampling_rate_by_{_format_ratio_token(sampling_ratio)}x",
        "description": (
            f"Measure position over the baseline window at {sampling_ratio:.1f}x the baseline sampling rate."
        ),
        "intervention_type": "measurement_change",
        "changes": {"sampling_rate": sampling_rate},
        "measurement_plan": {
            "channels": ["x"],
            "sampling_rate": sampling_rate,
            "time_window": {"start": 0.0, "end": baseline_duration},
            "metadata": {
                "experiment_family": "increase_sampling_rate",
                "parameterization": {
                    "sampling_rate_ratio": sampling_ratio,
                    "baseline_sampling_rate": baseline_sampling_rate,
                    "sampling_rate": sampling_rate,
                    "baseline_duration": baseline_duration,
                },
            },
        },
        "ambiguity_tags": ["low_resolution"],
        "cost": cost,
        "metadata": {
            "experiment_family": "increase_sampling_rate",
            "parameterization": {
                "sampling_rate_ratio": sampling_ratio,
                "baseline_sampling_rate": baseline_sampling_rate,
                "sampling_rate": sampling_rate,
                "baseline_duration": baseline_duration,
            },
        },
    }


def _velocity_channel_experiment(
    experiment_id: str,
    *,
    duration: float,
    sampling_rate: float,
    baseline_end_time: float,
    cost: float,
) -> dict[str, Any]:
    window_ratio = duration / baseline_end_time
    return {
        "experiment_id": experiment_id,
        "name": f"measure_velocity_window_by_{_format_ratio_token(window_ratio)}x",
        "description": (
            f"Measure velocity together with position over a window {window_ratio:.1f}x the baseline duration."
        ),
        "intervention_type": "measurement_change",
        "changes": {"add_channels": ["v"]},
        "measurement_plan": {
            "channels": ["x", "v"],
            "sampling_rate": sampling_rate,
            "time_window": {"start": 0.0, "end": duration},
            "metadata": {
                "experiment_family": "measure_velocity_channel",
                "parameterization": {
                    "window_ratio": window_ratio,
                    "baseline_end_time": baseline_end_time,
                    "duration": duration,
                    "sampling_rate": sampling_rate,
                },
            },
        },
        "ambiguity_tags": ["hidden_variable"],
        "cost": cost,
        "metadata": {
            "experiment_family": "measure_velocity_channel",
            "parameterization": {
                "window_ratio": window_ratio,
                "baseline_end_time": baseline_end_time,
                "duration": duration,
                "sampling_rate": sampling_rate,
            },
        },
    }


def _initial_velocity_experiment(
    experiment_id: str,
    *,
    initial_velocity: float,
    reference_initial_velocity: float,
    duration: float,
    baseline_end_time: float,
    sampling_rate: float,
    cost: float,
) -> dict[str, Any]:
    velocity_ratio = initial_velocity / reference_initial_velocity
    window_ratio = duration / baseline_end_time
    return {
        "experiment_id": experiment_id,
        "name": f"increase_initial_velocity_by_{_format_ratio_token(velocity_ratio)}x_ref",
        "description": (
            f"Repeat the run with initial velocity {velocity_ratio:.1f}x a reference excitation scale and observe position over {window_ratio:.1f}x the baseline duration."
        ),
        "intervention_type": "initial_condition_change",
        "changes": {
            "initial_state": {"x": 1.0, "v": initial_velocity},
        },
        "measurement_plan": {
            "channels": ["x"],
            "sampling_rate": sampling_rate,
            "time_window": {"start": 0.0, "end": duration},
            "metadata": {
                "experiment_family": "increase_initial_velocity",
                "parameterization": {
                    "initial_velocity_ratio": velocity_ratio,
                    "reference_initial_velocity": reference_initial_velocity,
                    "initial_velocity": initial_velocity,
                    "window_ratio": window_ratio,
                    "baseline_end_time": baseline_end_time,
                    "duration": duration,
                    "sampling_rate": sampling_rate,
                },
            },
        },
        "ambiguity_tags": ["weak_excitation"],
        "cost": cost,
        "metadata": {
            "experiment_family": "increase_initial_velocity",
            "parameterization": {
                "initial_velocity_ratio": velocity_ratio,
                "reference_initial_velocity": reference_initial_velocity,
                "initial_velocity": initial_velocity,
                "window_ratio": window_ratio,
                "baseline_end_time": baseline_end_time,
                "duration": duration,
                "sampling_rate": sampling_rate,
            },
        },
    }


def _format_numeric_token(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", "p")


def _format_ratio_token(value: float) -> str:
    return _format_numeric_token(value)


def _sample_scenario_spec(
    *,
    rng: random.Random,
    scenario_index: int,
    seed: int,
) -> dict[str, Any]:
    pair_type = rng.choice(
        [
            "linear_vs_nonlinear",
            "linear_vs_driven",
            "nonlinear_vs_driven",
            "linear_parameter_pair",
        ]
    )
    library_style = rng.choice(["window", "excitation", "velocity", "sampling"])
    baseline_duration = rng.choice([0.3, 0.5, 0.8])
    baseline_sampling_rate = rng.choice([5.0, 10.0, 20.0])
    initial_velocity = rng.choice([0.0, 0.15, 0.3, 0.5])

    hypothesis_pair = _sample_hypothesis_pair(pair_type=pair_type, rng=rng)
    true_hypothesis = rng.choice(hypothesis_pair)
    scenario_id = f"generated_osc_{pair_type}_{scenario_index:03d}"
    difficulty = _difficulty_from_baseline(
        baseline_duration=baseline_duration,
        initial_velocity=initial_velocity,
    )

    return {
        "scenario_id": scenario_id,
        "goal": _common_goal(),
        "baseline_condition": {
            "condition_id": (
                f"baseline_{_format_numeric_token(baseline_duration)}s_"
                f"{_format_numeric_token(baseline_sampling_rate)}hz"
            ),
            "duration": baseline_duration,
            "sampling_rate": baseline_sampling_rate,
            "initial_state": {"x": 1.0, "v": initial_velocity},
            "measured_channels": ["x"],
        },
        "observability": {
            "available_channels": ["x"],
            "hidden_channels": ["v"],
            "notes": (
                "Baseline observation uses a limited, position-only window. "
                "The experimental initial state is recorded in episode metadata."
            ),
        },
        "true_hypothesis": true_hypothesis,
        "candidate_hypotheses": hypothesis_pair,
        "candidate_experiments": _candidate_experiments_for_condition(
            baseline_duration=baseline_duration,
            baseline_sampling_rate=baseline_sampling_rate,
            library_style=library_style,
        ),
        "ambiguity_rule": {
            "max_score_gap": rng.choice([0.0025, 0.005, 0.01]),
            "ambiguity_type": _ambiguity_type_from_library_style(library_style),
        },
        "metadata": {
            "generator": "build_oscillator_scenarios.py",
            "seed": seed,
            "difficulty": difficulty,
            "source": "programmatic_sampled",
            "notes": (
                f"Sampled oscillator scenario with pair_type={pair_type}, "
                f"library_style={library_style}."
            ),
            "pair_type": pair_type,
            "candidate_library_style": library_style,
        },
    }


def _sample_hypothesis_pair(
    *,
    pair_type: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    if pair_type == "linear_vs_nonlinear":
        k = rng.choice([1.5, 2.0, 2.5])
        c = rng.choice([0.22, 0.3, 0.38])
        nonlinear_c2 = rng.choice([0.05, 0.08, 0.12, 0.18])
        return [
            _linear_hypothesis(
                hypothesis_id="H1",
                name="linear_damping",
                description="A damped oscillator with linear viscous damping.",
                m=1.0,
                c=c,
                k=k,
            ),
            _nonlinear_hypothesis(
                hypothesis_id="H2",
                name="weak_nonlinear_damping",
                description="A damped oscillator with velocity-dependent nonlinear damping.",
                m=1.0,
                c1=max(0.05, c - nonlinear_c2),
                c2=nonlinear_c2,
                k=k,
            ),
        ]

    if pair_type == "linear_vs_driven":
        k = rng.choice([1.5, 2.0, 2.5])
        c = rng.choice([0.22, 0.3, 0.38])
        return [
            _linear_hypothesis(
                hypothesis_id="H1",
                name="linear_damping",
                description="A damped oscillator with linear viscous damping and no external drive.",
                m=1.0,
                c=c,
                k=k,
            ),
            _linear_hypothesis(
                hypothesis_id="H2",
                name="weak_external_drive",
                description="A damped oscillator with a weak sinusoidal external drive.",
                m=1.0,
                c=c,
                k=k,
                drive_amplitude=rng.choice([0.015, 0.03, 0.05, 0.08]),
                drive_frequency=rng.choice([1.2, 1.8, 2.4]),
            ),
        ]

    if pair_type == "nonlinear_vs_driven":
        k = rng.choice([1.5, 2.0, 2.5])
        c = rng.choice([0.22, 0.3, 0.38])
        return [
            _nonlinear_hypothesis(
                hypothesis_id="H1",
                name="weak_nonlinear_damping",
                description="A damped oscillator with velocity-dependent nonlinear damping.",
                m=1.0,
                c1=max(0.05, c - 0.08),
                c2=rng.choice([0.05, 0.08, 0.12]),
                k=k,
            ),
            _linear_hypothesis(
                hypothesis_id="H2",
                name="weak_external_drive",
                description="A damped oscillator with a weak sinusoidal external drive.",
                m=1.0,
                c=c,
                k=k,
                drive_amplitude=rng.choice([0.015, 0.03, 0.05]),
                drive_frequency=rng.choice([1.2, 1.8, 2.4]),
            ),
        ]

    if pair_type == "linear_parameter_pair":
        k = rng.choice([1.5, 2.0, 2.5])
        c = rng.choice([0.22, 0.3, 0.38])
        return [
            _linear_hypothesis(
                hypothesis_id="H1",
                name="linear_low_damping",
                description="A damped oscillator with a slightly lower damping coefficient.",
                m=1.0,
                c=c,
                k=k,
            ),
            _linear_hypothesis(
                hypothesis_id="H2",
                name="linear_high_damping",
                description="A damped oscillator with a slightly higher damping coefficient.",
                m=1.0,
                c=c + rng.choice([0.03, 0.05, 0.08]),
                k=k + rng.choice([-0.05, 0.0, 0.05]),
            ),
        ]

    raise ValueError(f"unsupported pair_type: {pair_type}")


def _linear_hypothesis(
    *,
    hypothesis_id: str,
    name: str,
    description: str,
    m: float,
    c: float,
    k: float,
    drive_amplitude: float | None = None,
    drive_frequency: float | None = None,
) -> dict[str, Any]:
    parameters: dict[str, float] = {"m": m, "c": c, "k": k}
    rhs = "(-c * v - k * x) / m"
    mechanism_tags = ["linear_damping"]
    if drive_amplitude is not None and drive_frequency is not None:
        parameters["A"] = drive_amplitude
        parameters["omega"] = drive_frequency
        rhs = "(-c * v - k * x + A * cos(omega * t)) / m"
        mechanism_tags = ["external_drive"]

    return {
        "hypothesis_id": hypothesis_id,
        "name": name,
        "description": description,
        "mechanism_tags": mechanism_tags,
        "model": {
            "state_variables": ["x", "v"],
            "observed_variables": ["x"],
            "parameters": parameters,
            "equations": {
                "type": "symbolic_ode",
                "state_order": ["x", "v"],
                "rhs": ["v", rhs],
            },
        },
    }


def _nonlinear_hypothesis(
    *,
    hypothesis_id: str,
    name: str,
    description: str,
    m: float,
    c1: float,
    c2: float,
    k: float,
) -> dict[str, Any]:
    return {
        "hypothesis_id": hypothesis_id,
        "name": name,
        "description": description,
        "mechanism_tags": ["nonlinear_damping"],
        "model": {
            "state_variables": ["x", "v"],
            "observed_variables": ["x"],
            "parameters": {"m": m, "c1": c1, "c2": c2, "k": k},
            "equations": {
                "type": "symbolic_ode",
                "state_order": ["x", "v"],
                "rhs": [
                    "v",
                    "(-(c1 + c2 * abs(v)) * v - k * x) / m",
                ],
            },
        },
    }


def _ambiguity_type_from_library_style(library_style: str) -> str:
    return {
        "window": "short_window",
        "excitation": "weak_excitation",
        "velocity": "hidden_variable",
        "sampling": "low_resolution",
    }.get(library_style, "custom")


def _difficulty_from_baseline(
    *,
    baseline_duration: float,
    initial_velocity: float,
) -> str:
    if baseline_duration <= 0.3 and initial_velocity <= 0.15:
        return "hard"
    if baseline_duration <= 0.5:
        return "medium"
    return "easy"


def _passes_quality_filters(scenario: dict[str, Any]) -> bool:
    ambiguity = scenario.get("ambiguity_assessment") or {}
    if not ambiguity.get("is_ambiguous"):
        return False
    if len(ambiguity.get("compatible_hypotheses") or []) < 2:
        return False

    utilities = (scenario.get("ground_truth") or {}).get("experiment_utilities") or {}
    if len(utilities) < 2:
        return False

    ranked_utilities = sorted((float(value) for value in utilities.values()), reverse=True)
    best = ranked_utilities[0]
    second_best = ranked_utilities[1]
    worst = ranked_utilities[-1]

    if best <= 1e-5:
        return False
    if best - worst <= 1e-6:
        return False
    if second_best <= 0.0:
        return False

    best_to_second_ratio = best / second_best
    return 1.02 <= best_to_second_ratio <= 20.0


def _best_experiment_family(scenario: dict[str, Any]) -> str:
    best_experiment_id = (scenario.get("ground_truth") or {}).get("best_experiment_id")
    for experiment in scenario.get("candidate_experiments", []):
        if experiment["experiment_id"] == best_experiment_id:
            return (
                experiment.get("metadata", {})
                .get("experiment_family", "unknown")
            )
    return "unknown"


def _nonlinear_vs_linear_short_window_spec() -> dict[str, Any]:
    return {
        "scenario_id": "generated_osc_nonlinear_vs_linear_001",
        "goal": _common_goal(),
        "baseline_condition": {
            "condition_id": "baseline_short_window",
            "duration": 0.5,
            "sampling_rate": 10.0,
            "initial_state": {"x": 1.0, "v": 0.0},
            "measured_channels": ["x"],
        },
        "observability": {
            "available_channels": ["x"],
            "hidden_channels": ["v"],
            "notes": "Baseline observation uses a short, position-only window.",
        },
        "true_hypothesis": {
            "hypothesis_id": "H2",
            "name": "weak_nonlinear_damping",
            "description": "A damped oscillator with velocity-dependent nonlinear damping.",
            "mechanism_tags": ["nonlinear_damping"],
            "model": {
                "state_variables": ["x", "v"],
                "observed_variables": ["x"],
                "parameters": {"m": 1.0, "c1": 0.24, "c2": 0.08, "k": 2.0},
                "equations": {
                    "type": "symbolic_ode",
                    "state_order": ["x", "v"],
                    "rhs": [
                        "v",
                        "(-(c1 + c2 * abs(v)) * v - k * x) / m",
                    ],
                },
            },
        },
        "candidate_hypotheses": [
            {
                "hypothesis_id": "H1",
                "name": "linear_damping",
                "description": "A damped oscillator with linear viscous damping.",
                "mechanism_tags": ["linear_damping"],
                "model": {
                    "state_variables": ["x", "v"],
                    "observed_variables": ["x"],
                    "parameters": {"m": 1.0, "c": 0.3, "k": 2.0},
                    "equations": {
                        "type": "symbolic_ode",
                        "state_order": ["x", "v"],
                        "rhs": ["v", "(-c * v - k * x) / m"],
                    },
                },
            },
            {
                "hypothesis_id": "H2",
                "name": "weak_nonlinear_damping",
                "description": "A damped oscillator with velocity-dependent nonlinear damping.",
                "mechanism_tags": ["nonlinear_damping"],
                "model": {
                    "state_variables": ["x", "v"],
                    "observed_variables": ["x"],
                    "parameters": {"m": 1.0, "c1": 0.24, "c2": 0.08, "k": 2.0},
                    "equations": {
                        "type": "symbolic_ode",
                        "state_order": ["x", "v"],
                        "rhs": [
                            "v",
                            "(-(c1 + c2 * abs(v)) * v - k * x) / m",
                        ],
                    },
                },
            },
        ],
        "candidate_experiments": _common_candidate_experiments(),
        "ambiguity_rule": {
            "max_score_gap": 0.01,
            "ambiguity_type": "short_window",
        },
        "metadata": {
            "generator": "build_oscillator_scenarios.py",
            "seed": 0,
            "difficulty": "medium",
            "source": "programmatic",
            "notes": "Generated short-window ambiguity scenario for nonlinear vs linear damping.",
        },
    }


def _linear_vs_driven_short_window_spec() -> dict[str, Any]:
    return {
        "scenario_id": "generated_osc_linear_vs_driven_001",
        "goal": _common_goal(),
        "baseline_condition": {
            "condition_id": "baseline_short_window",
            "duration": 0.5,
            "sampling_rate": 10.0,
            "initial_state": {"x": 1.0, "v": 0.0},
            "measured_channels": ["x"],
        },
        "observability": {
            "available_channels": ["x"],
            "hidden_channels": ["v"],
            "notes": "Baseline observation uses a short, position-only window.",
        },
        "true_hypothesis": {
            "hypothesis_id": "H2",
            "name": "weak_external_drive",
            "description": "A damped oscillator with a weak sinusoidal external drive.",
            "mechanism_tags": ["external_drive"],
            "model": {
                "state_variables": ["x", "v"],
                "observed_variables": ["x"],
                "parameters": {
                    "m": 1.0,
                    "c": 0.3,
                    "k": 2.0,
                    "A": 0.03,
                    "omega": 1.8,
                },
                "equations": {
                    "type": "symbolic_ode",
                    "state_order": ["x", "v"],
                    "rhs": [
                        "v",
                        "(-c * v - k * x + A * cos(omega * t)) / m",
                    ],
                },
            },
        },
        "candidate_hypotheses": [
            {
                "hypothesis_id": "H1",
                "name": "linear_damping",
                "description": "A damped oscillator with linear viscous damping and no external drive.",
                "mechanism_tags": ["linear_damping"],
                "model": {
                    "state_variables": ["x", "v"],
                    "observed_variables": ["x"],
                    "parameters": {"m": 1.0, "c": 0.3, "k": 2.0},
                    "equations": {
                        "type": "symbolic_ode",
                        "state_order": ["x", "v"],
                        "rhs": ["v", "(-c * v - k * x) / m"],
                    },
                },
            },
            {
                "hypothesis_id": "H2",
                "name": "weak_external_drive",
                "description": "A damped oscillator with a weak sinusoidal external drive.",
                "mechanism_tags": ["external_drive"],
                "model": {
                    "state_variables": ["x", "v"],
                    "observed_variables": ["x"],
                    "parameters": {
                        "m": 1.0,
                        "c": 0.3,
                        "k": 2.0,
                        "A": 0.03,
                        "omega": 1.8,
                    },
                    "equations": {
                        "type": "symbolic_ode",
                        "state_order": ["x", "v"],
                        "rhs": [
                            "v",
                            "(-c * v - k * x + A * cos(omega * t)) / m",
                        ],
                    },
                },
            },
        ],
        "candidate_experiments": _common_candidate_experiments(),
        "ambiguity_rule": {
            "max_score_gap": 0.01,
            "ambiguity_type": "short_window",
        },
        "metadata": {
            "generator": "build_oscillator_scenarios.py",
            "seed": 1,
            "difficulty": "medium",
            "source": "programmatic",
            "notes": "Generated short-window ambiguity scenario for linear damping vs weak external drive.",
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
