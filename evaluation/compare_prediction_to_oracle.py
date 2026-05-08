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
    regret_metrics = _compute_experiment_regret_metrics(
        predicted_experiment_id=prediction.get("chosen_experiment_id"),
        oracle_ground_truth=oracle_ground_truth,
    )

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
        **regret_metrics,
    }


def _compute_experiment_regret_metrics(
    *,
    predicted_experiment_id: Any,
    oracle_ground_truth: dict[str, Any],
) -> dict[str, Any]:
    utilities = oracle_ground_truth.get("experiment_utilities") or {}
    best_experiment_id = oracle_ground_truth.get("best_experiment_id")

    empty_metrics = {
        "predicted_experiment_valid": predicted_experiment_id in utilities,
        "predicted_experiment_utility": None,
        "oracle_best_utility": None,
        "oracle_worst_utility": None,
        "raw_utility_regret": None,
        "normalized_utility_regret": None,
        "utility_ratio": None,
        "near_optimal_at_0_8": None,
        "near_optimal_at_0_5": None,
    }
    if not utilities or best_experiment_id not in utilities:
        return empty_metrics

    numeric_utilities = {
        experiment_id: float(utility)
        for experiment_id, utility in utilities.items()
    }
    best_utility = numeric_utilities[best_experiment_id]
    worst_utility = min(numeric_utilities.values())

    predicted_valid = predicted_experiment_id in numeric_utilities
    predicted_utility = (
        numeric_utilities[predicted_experiment_id]
        if predicted_valid
        else worst_utility
    )

    raw_regret = best_utility - predicted_utility
    utility_range = best_utility - worst_utility
    normalized_regret = raw_regret / utility_range if utility_range > 0.0 else 0.0
    utility_ratio = predicted_utility / best_utility if best_utility > 0.0 else None

    return {
        "predicted_experiment_valid": predicted_valid,
        "predicted_experiment_utility": predicted_utility,
        "oracle_best_utility": best_utility,
        "oracle_worst_utility": worst_utility,
        "raw_utility_regret": raw_regret,
        "normalized_utility_regret": normalized_regret,
        "utility_ratio": utility_ratio,
        "near_optimal_at_0_8": (
            predicted_utility >= 0.8 * best_utility if best_utility > 0.0 else None
        ),
        "near_optimal_at_0_5": (
            predicted_utility >= 0.5 * best_utility if best_utility > 0.0 else None
        ),
    }
