from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.external_model import get_external_prediction
from evaluation.compare_prediction_to_oracle import compare_prediction_to_oracle
from prompting.render_prompt import render_prompt


def main() -> int:
    parser = build_arg_parser(
        description="Render a no-simulator prompt and produce a structured baseline prediction."
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario_path)
    with scenario_path.open("r", encoding="utf-8") as handle:
        scenario = json.load(handle)

    prompt = render_prompt(scenario, mode=args.prompt_mode)
    if args.write_prompt:
        Path(args.write_prompt).write_text(prompt, encoding="utf-8")
    if args.write_prediction_template:
        template = build_prediction_template(scenario)
        Path(args.write_prediction_template).write_text(
            json.dumps(template, indent=2),
            encoding="utf-8",
        )
    prediction = get_prediction_from_args(
        scenario=scenario,
        prompt=prompt,
        args=args,
    )
    evaluation = compare_prediction_to_oracle(scenario=scenario, prediction=prediction)

    report = {
        "scenario_id": scenario["scenario_id"],
        "prompt_mode": args.prompt_mode,
        "prediction_mode": args.prediction_mode,
        "external_generation_config": external_generation_config_from_args(args),
        "prompt": prompt,
        "prediction": prediction,
        "evaluation": evaluation,
    }
    print(json.dumps(report, indent=2))
    return 0


def build_arg_parser(
    *,
    description: str,
    include_scenario_path: bool = True,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    if include_scenario_path:
        parser.add_argument(
            "scenario_path",
            nargs="?",
            default="generated_scenarios/generated_osc_nonlinear_vs_linear_001.json",
            help="Path to a scenario JSON file.",
        )
    parser.add_argument(
        "--prompt-mode",
        default="plain",
        choices=["plain", "contrast", "compare"],
        help="Prompt style to render.",
    )
    parser.add_argument(
        "--prediction-mode",
        default="heuristic",
        choices=["heuristic", "from-file", "external"],
        help="How to obtain the structured prediction.",
    )
    parser.add_argument(
        "--prediction-file",
        default=None,
        help="Path to a JSON file with a structured model prediction when using --prediction-mode from-file.",
    )
    parser.add_argument(
        "--write-prediction-template",
        default=None,
        help="Write a JSON prediction template to this path and continue running.",
    )
    parser.add_argument(
        "--write-prompt",
        default=None,
        help="Write the rendered prompt text to this path and continue running.",
    )
    parser.add_argument(
        "--external-provider",
        default="openai",
        choices=["openai", "vllm"],
        help="External model provider when using --prediction-mode external.",
    )
    parser.add_argument(
        "--external-model",
        default="gpt-4.1-mini",
        help="Model name for --prediction-mode external.",
    )
    parser.add_argument(
        "--external-base-url",
        default=None,
        help="Optional override for the external provider endpoint.",
    )
    parser.add_argument(
        "--external-api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the API key for OpenAI-style providers.",
    )
    parser.add_argument(
        "--external-timeout-sec",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds for external model calls.",
    )
    parser.add_argument(
        "--external-temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for external model calls.",
    )
    parser.add_argument(
        "--external-top-p",
        type=float,
        default=None,
        help="Optional nucleus sampling top-p value for external model calls.",
    )
    parser.add_argument(
        "--external-top-k",
        type=int,
        default=None,
        help="Optional top-k value. Sent only to vLLM-style providers.",
    )
    parser.add_argument(
        "--external-max-tokens",
        type=int,
        default=None,
        help="Optional maximum number of generated tokens for external model calls.",
    )
    parser.add_argument(
        "--external-thinking",
        default="default",
        choices=["default", "on", "off"],
        help=(
            "Optional Qwen-style thinking control for vLLM chat templates. "
            "Use 'on' to pass enable_thinking=true and 'off' for false."
        ),
    )
    return parser


def get_prediction_from_args(
    *,
    scenario: dict[str, Any],
    prompt: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return _get_prediction(
        scenario=scenario,
        prompt=prompt,
        prediction_mode=args.prediction_mode,
        prediction_file=args.prediction_file,
        external_provider=args.external_provider,
        external_model=args.external_model,
        external_base_url=args.external_base_url,
        external_api_key_env=args.external_api_key_env,
        external_timeout_sec=args.external_timeout_sec,
        external_temperature=args.external_temperature,
        external_top_p=args.external_top_p,
        external_top_k=args.external_top_k,
        external_max_tokens=args.external_max_tokens,
        external_thinking=args.external_thinking,
    )


def _get_prediction(
    *,
    scenario: dict[str, Any],
    prompt: str,
    prediction_mode: str,
    prediction_file: str | None,
    external_provider: str,
    external_model: str,
    external_base_url: str | None,
    external_api_key_env: str,
    external_timeout_sec: float,
    external_temperature: float,
    external_top_p: float | None,
    external_top_k: int | None,
    external_max_tokens: int | None,
    external_thinking: str,
) -> dict[str, Any]:
    if prediction_mode == "heuristic":
        return _heuristic_prediction(scenario)

    if prediction_mode == "from-file":
        if not prediction_file:
            raise ValueError("--prediction-file is required when --prediction-mode from-file is used")
        with Path(prediction_file).open("r", encoding="utf-8") as handle:
            return _normalize_prediction(json.load(handle))

    if prediction_mode == "external":
        return get_external_prediction(
            prompt=prompt,
            provider=external_provider,
            model=external_model,
            base_url=external_base_url,
            api_key_env=external_api_key_env,
            timeout_sec=external_timeout_sec,
            temperature=external_temperature,
            top_p=external_top_p,
            top_k=external_top_k,
            max_tokens=external_max_tokens,
            thinking=external_thinking,
        )

    raise ValueError(f"unsupported prediction_mode: {prediction_mode}")


def external_generation_config_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.prediction_mode != "external":
        return None

    return {
        "provider": args.external_provider,
        "model": args.external_model,
        "base_url": args.external_base_url,
        "temperature": args.external_temperature,
        "top_p": args.external_top_p,
        "top_k": args.external_top_k,
        "max_tokens": args.external_max_tokens,
        "thinking": args.external_thinking,
        "timeout_sec": args.external_timeout_sec,
    }


def build_prediction_template(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_ambiguous": None,
        "compatible_hypotheses": [],
        "chosen_experiment_id": None,
        "reasoning": "",
        "_guidance": {
            "allowed_hypothesis_ids": [
                hypothesis["hypothesis_id"] for hypothesis in scenario["hypotheses"]
            ],
            "allowed_experiment_ids": [
                experiment["experiment_id"] for experiment in scenario["candidate_experiments"]
            ],
            "notes": [
                "Fill only the top-level prediction fields for evaluation.",
                "Set chosen_experiment_id to null if the evidence is not ambiguous.",
            ],
        },
    }


def _heuristic_prediction(scenario: dict[str, Any]) -> dict[str, Any]:
    """
    Simple no-simulator heuristic baseline.

    This is intentionally lightweight and benchmark-facing rather than oracle-backed:
    - if multiple hypotheses are present, predict ambiguity
    - use ambiguity tags and cost to pick a cheap experiment that matches the named ambiguity type
    """
    hypotheses = scenario["hypotheses"]
    ambiguity_type = ((scenario.get("ambiguity_assessment") or {}).get("ambiguity_type")) or "custom"

    matching_experiments = [
        experiment
        for experiment in scenario["candidate_experiments"]
        if ambiguity_type in (experiment.get("ambiguity_tags") or [])
    ]
    if matching_experiments:
        chosen_experiment = sorted(
            matching_experiments,
            key=lambda experiment: (
                float(experiment.get("cost", 0.0)),
                experiment["experiment_id"],
            ),
        )[0]
    else:
        chosen_experiment = sorted(
            scenario["candidate_experiments"],
            key=lambda experiment: (
                float(experiment.get("cost", 0.0)),
                experiment["experiment_id"],
            ),
        )[0]

    return {
        "is_ambiguous": len(hypotheses) > 1,
        "compatible_hypotheses": [hypothesis["hypothesis_id"] for hypothesis in hypotheses],
        "chosen_experiment_id": chosen_experiment["experiment_id"] if len(hypotheses) > 1 else None,
        "reasoning": (
            "Heuristic baseline: treat multiple hypotheses as unresolved and choose the cheapest "
            "candidate tagged for the current ambiguity type."
        ),
    }


def _normalize_prediction(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_ambiguous": parsed.get("is_ambiguous"),
        "compatible_hypotheses": list(parsed.get("compatible_hypotheses") or []),
        "chosen_experiment_id": parsed.get("chosen_experiment_id"),
        "reasoning": str(parsed.get("reasoning", "")),
    }


if __name__ == "__main__":
    raise SystemExit(main())
