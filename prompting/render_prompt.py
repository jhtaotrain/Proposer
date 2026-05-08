from __future__ import annotations

import json
from typing import Any


def render_prompt(
    scenario: dict[str, Any],
    *,
    mode: str = "plain",
) -> str:
    if mode == "plain":
        return _render_plain_prompt(scenario)
    if mode == "contrast":
        return _render_contrast_prompt(scenario)
    if mode == "compare":
        return _render_compare_prompt(scenario)
    raise ValueError(f"unsupported prompt mode: {mode}")


def build_llm_visible_payload(scenario: dict[str, Any]) -> dict[str, Any]:
    """
    Return only the fields the no-simulator LLM is allowed to see.
    """
    return {
        "scenario_id": scenario["scenario_id"],
        "domain": scenario["domain"],
        "goal": scenario["goal"],
        "observations": scenario["observations"],
        "hypotheses": [
            {
                "hypothesis_id": hypothesis["hypothesis_id"],
                "name": hypothesis["name"],
                "description": hypothesis["description"],
                "family": hypothesis["family"],
                "mechanism_tags": hypothesis.get("mechanism_tags", []),
                "model": {
                    "state_variables": hypothesis["model"].get("state_variables", []),
                    "observed_variables": hypothesis["model"].get("observed_variables", []),
                    "parameters": hypothesis["model"].get("parameters", {}),
                    "equations": hypothesis["model"].get("equations"),
                },
            }
            for hypothesis in scenario["hypotheses"]
        ],
        "candidate_experiments": [
            {
                "experiment_id": experiment["experiment_id"],
                "name": experiment["name"],
                "description": experiment["description"],
                "intervention_type": experiment["intervention_type"],
                "changes": experiment.get("changes", {}),
                "measurement_plan": experiment.get("measurement_plan"),
                "ambiguity_tags": experiment.get("ambiguity_tags", []),
                "cost": experiment.get("cost"),
                "metadata": experiment.get("metadata", {}),
            }
            for experiment in scenario["candidate_experiments"]
        ],
    }


def _render_plain_prompt(scenario: dict[str, Any]) -> str:
    payload = build_llm_visible_payload(scenario)
    instructions = {
        "task": [
            "Decide whether the current evidence is still ambiguous.",
            "If it is ambiguous, identify which hypotheses remain plausible.",
            "Choose the single best next experiment from the candidate list.",
            "Prefer the experiment expected to produce the largest separation between the remaining hypotheses.",
        ],
        "output_format": {
            "is_ambiguous": "boolean",
            "compatible_hypotheses": ["hypothesis_id"],
            "chosen_experiment_id": "experiment_id or null",
            "reasoning": "short explanation",
        },
        "rules": [
            "Use only the provided observations, hypotheses, and candidate experiments.",
            "Do not assume access to a simulator or hidden oracle scores.",
            "If the evidence is not ambiguous, set chosen_experiment_id to null.",
        ],
    }
    return (
        "You are helping plan the immediate next scientific experiment.\n\n"
        "Instructions:\n"
        f"{json.dumps(instructions, indent=2)}\n\n"
        "Scenario:\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _render_contrast_prompt(scenario: dict[str, Any]) -> str:
    payload = build_llm_visible_payload(scenario)
    instructions = {
        "task": [
            "First identify which parts of the current observations are explained by multiple hypotheses.",
            "Then explain what difference each candidate experiment would amplify.",
            "Then choose the experiment expected to produce the largest separation between the remaining hypotheses.",
        ],
        "required_reasoning_steps": [
            "State why the current evidence may still be unresolved.",
            "Contrast the remaining hypotheses rather than committing early to one of them.",
            "Choose the experiment that best amplifies the unresolved difference.",
        ],
        "output_format": {
            "is_ambiguous": "boolean",
            "compatible_hypotheses": ["hypothesis_id"],
            "chosen_experiment_id": "experiment_id or null",
            "reasoning": "short explanation focused on unresolved differences",
        },
    }
    return (
        "You are evaluating competing scientific hypotheses and must select the next discriminating experiment.\n\n"
        "Instructions:\n"
        f"{json.dumps(instructions, indent=2)}\n\n"
        "Scenario:\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _render_compare_prompt(scenario: dict[str, Any]) -> str:
    payload = build_llm_visible_payload(scenario)
    instructions = {
        "task": [
            "Decide whether the current evidence is still ambiguous.",
            "If it is ambiguous, identify which hypotheses remain plausible.",
            "Compare every candidate experiment before choosing.",
            "Choose the experiment expected to produce the largest accumulated separation in the measured response.",
        ],
        "candidate_comparison_guidance": [
            "For each candidate, estimate what hypothesis difference it probes.",
            "Estimate whether the planned measured channels capture that difference.",
            "Estimate how long the difference can accumulate over the proposed measurement window.",
            "Estimate whether the intervention increases mechanism-relevant excitation.",
            "Use qualitative or rough quantitative estimates only; do not assume hidden simulator outputs or oracle scores.",
        ],
        "output_format": {
            "is_ambiguous": "boolean",
            "compatible_hypotheses": ["hypothesis_id"],
            "candidate_comparison": [
                {
                    "experiment_id": "experiment_id",
                    "probed_difference": "short phrase",
                    "channel_capture": "low | medium | high",
                    "accumulation_duration": "short | medium | long",
                    "excitation_strength": "low | medium | high",
                    "expected_total_separation": "low | medium | high",
                }
            ],
            "chosen_experiment_id": "experiment_id or null",
            "reasoning": "short explanation comparing the chosen experiment against the strongest alternatives",
        },
        "rules": [
            "Use only the provided observations, hypotheses, and candidate experiments.",
            "Do not assume access to a simulator or hidden oracle scores.",
            "If the evidence is not ambiguous, set chosen_experiment_id to null.",
            "The final chosen_experiment_id must be one of the provided candidate experiment ids, or null if not ambiguous.",
        ],
    }
    return (
        "You are evaluating competing scientific hypotheses and must estimate which next experiment will most separate them.\n\n"
        "Instructions:\n"
        f"{json.dumps(instructions, indent=2)}\n\n"
        "Scenario:\n"
        f"{json.dumps(payload, indent=2)}"
    )
