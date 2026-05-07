from __future__ import annotations

from typing import Any


def compare_prediction_to_oracle(
    *,
    scenario: dict[str, Any],
    prediction: dict[str, Any],
) -> dict[str, Any]:
    oracle_ambiguity = scenario.get("ambiguity_assessment") or {}
    oracle_ground_truth = scenario.get("ground_truth") or {}

    predicted_compatible = set(prediction.get("compatible_hypotheses") or [])
    oracle_compatible = set(oracle_ambiguity.get("compatible_hypotheses") or [])

    return {
        "scenario_id": scenario["scenario_id"],
        "ambiguity_accuracy": prediction.get("is_ambiguous") == oracle_ambiguity.get("is_ambiguous"),
        "compatible_hypotheses_exact_match": predicted_compatible == oracle_compatible,
        "chosen_experiment_correct": prediction.get("chosen_experiment_id") == oracle_ground_truth.get("best_experiment_id"),
        "oracle_best_experiment_id": oracle_ground_truth.get("best_experiment_id"),
        "predicted_experiment_id": prediction.get("chosen_experiment_id"),
        "oracle_is_ambiguous": oracle_ambiguity.get("is_ambiguous"),
        "predicted_is_ambiguous": prediction.get("is_ambiguous"),
        "oracle_compatible_hypotheses": sorted(oracle_compatible),
        "predicted_compatible_hypotheses": sorted(predicted_compatible),
    }
