from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from scoring.ambiguity import (
    ambiguity_result_to_schema_payload,
    label_ambiguity_from_hypotheses,
)
from scoring.experiment_utility import (
    experiment_ranking_to_oracle_payload,
    rank_candidate_experiments,
)


def main() -> int:
    scenario_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "example_damped_oscillator_scenario.json"
    )

    with scenario_path.open("r", encoding="utf-8") as handle:
        scenario = json.load(handle)

    initial_state = _infer_initial_state(scenario)
    ambiguity_type = _infer_ambiguity_type(scenario)

    ambiguity_result = label_ambiguity_from_hypotheses(
        hypotheses=scenario["hypotheses"],
        observation_episode=scenario["observations"]["episodes"][0],
        initial_state=initial_state,
        score_type="mse",
        max_score_gap=0.01,
        ambiguity_type=ambiguity_type,
    )

    name_to_id = {
        hypothesis["name"]: hypothesis["hypothesis_id"]
        for hypothesis in scenario["hypotheses"]
    }
    ambiguity_payload = ambiguity_result_to_schema_payload(
        ambiguity_result,
        hypothesis_name_to_id=name_to_id,
    )

    compatible_hypotheses = [
        hypothesis
        for hypothesis in scenario["hypotheses"]
        if hypothesis["name"] in ambiguity_result.compatible_hypotheses
    ]

    experiment_results = rank_candidate_experiments(
        candidate_experiments=scenario["candidate_experiments"],
        compatible_hypotheses=compatible_hypotheses,
        baseline_initial_state=initial_state,
    )
    oracle_payload = experiment_ranking_to_oracle_payload(
        experiment_results,
        true_hypothesis_id=_maybe_true_hypothesis_id(scenario),
    )

    report = {
        "scenario_id": scenario["scenario_id"],
        "domain": scenario["domain"],
        "initial_state_used": initial_state,
        "fit_ranking": [
            {
                "hypothesis_name": result.hypothesis_name,
                "score_type": result.score_type,
                "aggregate_score": result.aggregate_score,
                "per_channel": {
                    channel: {
                        "mse": channel_score.mse,
                        "mae": channel_score.mae,
                    }
                    for channel, channel_score in result.per_channel.items()
                },
            }
            for result in ambiguity_result.ranked_fit_results
        ],
        "ambiguity_assessment": ambiguity_payload,
        "experiment_ranking": [
            {
                "experiment_id": result.experiment_id,
                "experiment_name": result.experiment_name,
                "utility_score": result.utility_score,
                "measured_channels": list(result.measured_channels),
                "compared_hypotheses": list(result.compared_hypotheses),
                "pairwise_channel_disagreement": result.pairwise_channel_disagreement,
                "metadata": result.metadata,
            }
            for result in experiment_results
        ],
        "oracle_ground_truth": oracle_payload,
    }

    print(json.dumps(report, indent=2))
    return 0


def _infer_initial_state(scenario: dict[str, Any]) -> dict[str, float]:
    episode = scenario["observations"]["episodes"][0]
    measured_channels = set(episode["measured_channels"])
    values = episode["values"]

    initial_state = {
        "x": float(values["x"][0]) if "x" in measured_channels else 0.0,
        "v": float(values["v"][0]) if "v" in measured_channels else 0.0,
    }
    return initial_state


def _infer_ambiguity_type(scenario: dict[str, Any]) -> str:
    ambiguity_assessment = scenario.get("ambiguity_assessment") or {}
    return ambiguity_assessment.get("ambiguity_type", "custom")


def _maybe_true_hypothesis_id(scenario: dict[str, Any]) -> str | None:
    ground_truth = scenario.get("ground_truth") or {}
    return ground_truth.get("true_hypothesis_id")


if __name__ == "__main__":
    raise SystemExit(main())
