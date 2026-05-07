from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scoring.hypothesis_fit import HypothesisFitResult, rank_hypotheses_by_fit


@dataclass(frozen=True)
class AmbiguityLabelResult:
    is_ambiguous: bool
    compatible_hypotheses: tuple[str, ...]
    rejected_hypotheses: tuple[str, ...]
    ambiguity_type: str
    criterion: dict[str, Any]
    explanation: str
    ranked_fit_results: tuple[HypothesisFitResult, ...]


def label_ambiguity_from_ranked_fits(
    ranked_fit_results: list[HypothesisFitResult],
    *,
    max_score_gap: float,
    ambiguity_type: str = "custom",
) -> AmbiguityLabelResult:
    """
    Label ambiguity by keeping all hypotheses whose fit score is within
    `max_score_gap` of the best score.
    """
    if not ranked_fit_results:
        raise ValueError("ranked_fit_results must not be empty")
    if max_score_gap < 0.0:
        raise ValueError("max_score_gap must be non-negative")

    best_score = ranked_fit_results[0].aggregate_score
    compatible = [
        result.hypothesis_name
        for result in ranked_fit_results
        if result.aggregate_score - best_score <= max_score_gap
    ]
    rejected = [
        result.hypothesis_name
        for result in ranked_fit_results
        if result.hypothesis_name not in compatible
    ]

    is_ambiguous = len(compatible) > 1
    explanation = _build_explanation(
        compatible_hypotheses=compatible,
        rejected_hypotheses=rejected,
        max_score_gap=max_score_gap,
        best_score=best_score,
        is_ambiguous=is_ambiguous,
    )

    return AmbiguityLabelResult(
        is_ambiguous=is_ambiguous,
        compatible_hypotheses=tuple(compatible),
        rejected_hypotheses=tuple(rejected),
        ambiguity_type=ambiguity_type if is_ambiguous else "none",
        criterion={
            "type": "fit_score_band",
            "threshold": max_score_gap,
            "parameters": {
                "best_score": best_score,
                "score_type": ranked_fit_results[0].score_type,
            },
        },
        explanation=explanation,
        ranked_fit_results=tuple(ranked_fit_results),
    )


def label_ambiguity_from_hypotheses(
    *,
    hypotheses: list[dict[str, Any]],
    observation_episode: dict[str, Any],
    initial_state: dict[str, float],
    score_type: str = "mse",
    max_score_gap: float = 0.01,
    ambiguity_type: str = "custom",
) -> AmbiguityLabelResult:
    """
    End-to-end ambiguity labeling: score hypotheses against the current episode
    and then apply a best-score band criterion.
    """
    ranked_fit_results = rank_hypotheses_by_fit(
        hypotheses=hypotheses,
        observation_episode=observation_episode,
        initial_state=initial_state,
        score_type=score_type,
    )
    return label_ambiguity_from_ranked_fits(
        ranked_fit_results=ranked_fit_results,
        max_score_gap=max_score_gap,
        ambiguity_type=ambiguity_type,
    )


def ambiguity_result_to_schema_payload(
    result: AmbiguityLabelResult,
    *,
    hypothesis_name_to_id: dict[str, str],
) -> dict[str, Any]:
    """
    Convert an ambiguity label result into the JSON payload shape used by the
    scenario schema.
    """
    return {
        "is_ambiguous": result.is_ambiguous,
        "compatible_hypotheses": [
            hypothesis_name_to_id[name] for name in result.compatible_hypotheses
        ],
        "rejected_hypotheses": [
            hypothesis_name_to_id[name] for name in result.rejected_hypotheses
        ],
        "ambiguity_type": result.ambiguity_type,
        "criterion": result.criterion,
        "explanation": result.explanation,
    }


def _build_explanation(
    *,
    compatible_hypotheses: list[str],
    rejected_hypotheses: list[str],
    max_score_gap: float,
    best_score: float,
    is_ambiguous: bool,
) -> str:
    if is_ambiguous:
        compatible_text = ", ".join(compatible_hypotheses)
        return (
            "Multiple hypotheses remain compatible with the current observations. "
            f"The kept hypotheses ({compatible_text}) all fall within {max_score_gap} "
            f"of the best fit score {best_score:.6f}."
        )

    kept = compatible_hypotheses[0]
    if rejected_hypotheses:
        rejected_text = ", ".join(rejected_hypotheses)
        return (
            f"The current evidence is treated as resolved in favor of {kept}. "
            f"All other hypotheses ({rejected_text}) fall outside the allowed fit-score "
            f"gap of {max_score_gap} from the best score {best_score:.6f}."
        )

    return (
        f"The current evidence is treated as resolved in favor of {kept}. "
        "No competing hypotheses remain after fit-based filtering."
    )
