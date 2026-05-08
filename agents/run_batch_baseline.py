from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.run_llm_baseline import (  # noqa: E402
    build_arg_parser,
    external_generation_config_from_args,
    get_prediction_from_args,
)
from evaluation.compare_prediction_to_oracle import compare_prediction_to_oracle  # noqa: E402
from prompting.render_prompt import render_prompt  # noqa: E402


METRIC_KEYS = [
    "ambiguity_accuracy",
    "compatible_hypotheses_exact_match",
    "chosen_experiment_correct",
    "predicted_experiment_valid",
    "utility_ratio",
    "normalized_utility_regret",
    "near_optimal_at_0_8",
    "near_optimal_at_0_5",
]


def main() -> int:
    parser = build_arg_parser(
        description="Run a no-simulator baseline over a batch of scenario JSON files.",
        include_scenario_path=False,
    )
    _add_batch_arguments(parser)
    args = parser.parse_args()

    scenario_paths = _resolve_scenario_paths(args.scenario_glob)
    if not scenario_paths:
        raise ValueError(f"no scenario files matched: {args.scenario_glob}")

    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with output_path.open("w", encoding="utf-8") as handle:
        for index, scenario_path in enumerate(scenario_paths, start=1):
            row = _run_one_scenario(
                scenario_path=scenario_path,
                args=args,
                index=index,
                total=len(scenario_paths),
            )
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()

            if row["status"] == "error" and not args.continue_on_error:
                raise RuntimeError(
                    f"failed on {scenario_path}: {row.get('error_type')}: {row.get('error')}"
                )

    summary = _build_summary(
        rows=rows,
        scenario_glob=args.scenario_glob,
        output_jsonl=output_path,
        args=args,
    )
    print(json.dumps(summary, indent=2))
    return 0


def _add_batch_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--scenario-glob",
        default="generated_scenarios/*.json",
        help="Glob pattern for scenario JSON files.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="results/batch_baseline.jsonl",
        help="Path to write one JSON result per scenario.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Record per-scenario errors and continue instead of stopping the batch.",
    )

    for action in parser._actions:
        if action.dest in {"prediction_file", "write_prediction_template", "write_prompt"}:
            action.help = argparse.SUPPRESS


def _resolve_scenario_paths(pattern: str) -> list[Path]:
    return [
        Path(path)
        for path in sorted(glob.glob(pattern))
        if Path(path).is_file()
    ]


def _run_one_scenario(
    *,
    scenario_path: Path,
    args: argparse.Namespace,
    index: int,
    total: int,
) -> dict[str, Any]:
    try:
        with scenario_path.open("r", encoding="utf-8") as handle:
            scenario = json.load(handle)

        prompt = render_prompt(scenario, mode=args.prompt_mode)
        prediction = get_prediction_from_args(
            scenario=scenario,
            prompt=prompt,
            args=args,
        )
        evaluation = compare_prediction_to_oracle(
            scenario=scenario,
            prediction=prediction,
        )

        return {
            "status": "ok",
            "batch_index": index,
            "batch_total": total,
            "scenario_id": scenario["scenario_id"],
            "scenario_path": scenario_path.as_posix(),
            "prompt_mode": args.prompt_mode,
            "prediction_mode": args.prediction_mode,
            "external_generation_config": external_generation_config_from_args(args),
            "prediction": prediction,
            "evaluation": evaluation,
        }
    except Exception as exc:
        return {
            "status": "error",
            "batch_index": index,
            "batch_total": total,
            "scenario_id": None,
            "scenario_path": scenario_path.as_posix(),
            "prompt_mode": args.prompt_mode,
            "prediction_mode": args.prediction_mode,
            "external_generation_config": external_generation_config_from_args(args),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_model_output_preview": getattr(exc, "raw_output_preview", None),
        }


def _build_summary(
    *,
    rows: list[dict[str, Any]],
    scenario_glob: str,
    output_jsonl: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    ok_rows = [row for row in rows if row["status"] == "ok"]
    error_rows = [row for row in rows if row["status"] == "error"]

    metric_means = {
        f"mean_{metric_key}": _mean_metric(ok_rows, metric_key)
        for metric_key in METRIC_KEYS
    }

    return {
        "scenario_glob": scenario_glob,
        "output_jsonl": output_jsonl.as_posix(),
        "num_scenarios": len(rows),
        "num_ok": len(ok_rows),
        "num_errors": len(error_rows),
        "prompt_mode": args.prompt_mode,
        "prediction_mode": args.prediction_mode,
        "external_generation_config": external_generation_config_from_args(args),
        **metric_means,
        "errors": [
            {
                "scenario_path": row["scenario_path"],
                "error_type": row.get("error_type"),
                "error": row.get("error"),
                "raw_model_output_preview": row.get("raw_model_output_preview"),
            }
            for row in error_rows
        ],
    }


def _mean_metric(rows: list[dict[str, Any]], metric_key: str) -> float | None:
    values = []
    for row in rows:
        value = row.get("evaluation", {}).get(metric_key)
        if isinstance(value, bool):
            values.append(float(value))
        elif isinstance(value, int | float):
            values.append(float(value))

    if not values:
        return None
    return sum(values) / len(values)


if __name__ == "__main__":
    raise SystemExit(main())
