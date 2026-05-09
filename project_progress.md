# Project Progress

## 2026-05-09

### Completed

- Added a dependency-free stderr progress bar to [agents/run_batch_baseline.py](D:/science_agent/Proposer/agents/run_batch_baseline.py:1), including current scenario, completed count, and ok/error counts.
- Added `--no-progress` for quiet batch runs while preserving one-flushed-JSONL-row-per-scenario output.
- Tightened the external model system prompt in [agents/external_model.py](D:/science_agent/Proposer/agents/external_model.py:1) so external providers are explicitly asked to return only the prediction JSON object without markdown, commentary, or analysis.
- Updated `compare` prompt mode in [prompting/render_prompt.py](D:/science_agent/Proposer/prompting/render_prompt.py:1) so the candidate comparison stays internal and the visible output matches the evaluator contract: `is_ambiguous`, `compatible_hypotheses`, `chosen_experiment_id`, and `reasoning`.
- Removed the bulky `candidate_comparison` output field from the `compare` prompt because the evaluator does not consume it and it encouraged long, fragile local-model outputs.
- Refined `compare` guidance so excitation is helpful only if it increases measured trajectory disagreement more than a longer measurement window or added channel would.
- Confirmed the original `compare` run stopped after 30/100 rows; the batch runner itself had no 30-row cap.
- Reran Qwen/Qwen3.6-35B-A3B `compare` with `temperature=0`, `max_tokens=2048`, and `thinking=off` before the prompt refinement:
  - output: `results/qwen_compare_rerun_thinking_off.jsonl`
  - 100 ok, 0 errors
  - exact: 0.15
  - utility ratio: 0.528
  - normalized regret: 0.520
  - near-optimal@0.8: 0.24
  - near-optimal@0.5: 0.47
- Diagnosed that pre-refinement `compare` over-selected `increase_initial_velocity`:
  - oracle best families: 45 velocity-channel, 34 extended-window, 21 initial-velocity
  - model predictions: 66 initial-velocity, 33 velocity-channel, 1 extended-window
- Reran the refined `compare` prompt with the same controlled settings:
  - output: `results/qwen_compare_fixed_thinking_off.jsonl`
  - 100 ok, 0 errors
  - exact: 0.27
  - utility ratio: 0.637
  - normalized regret: 0.404
  - near-optimal@0.8: 0.35
  - near-optimal@0.5: 0.61
- Reran `contrast` with the same controlled settings for an apples-to-apples comparison:
  - output: `results/qwen_contrast_thinking_off.jsonl`
  - 100 ok, 0 errors
  - exact: 0.06
  - utility ratio: 0.447
  - normalized regret: 0.611
  - near-optimal@0.8: 0.13
  - near-optimal@0.5: 0.37
- Compared controlled `compare` versus controlled `contrast` and found `compare` higher on utility ratio in 52 scenarios, `contrast` higher in 6, and 42 rough ties.
- Observed that the refined `compare` prompt fixed the strongest initial-velocity bias but shifted toward velocity-channel measurements:
  - model predictions: 58 velocity-channel, 42 initial-velocity, 0 extended-window
  - remaining failure surface: extended-window oracle cases still receive 0 exact matches.
- Added tagged thinking-output support in [agents/external_model.py](D:/science_agent/Proposer/agents/external_model.py:1): vLLM runs with `--external-thinking on` now ask the model to put reasoning in `<think>...</think>` and the final prediction JSON in `<answer>...</answer>`.
- Updated the external parser to prefer JSON found inside the last `<answer>...</answer>` block, then fall back to the existing object-extraction parser for older/raw JSON outputs.
- Updated [README.md](D:/science_agent/Proposer/README.md:1) with progress-bar behavior, strict JSON guidance for Qwen/vLLM runs, tagged `<think>` / `<answer>` thinking-on parsing, controlled run commands, latest metrics, and the remaining family-bias diagnosis.
- Verified tagged parsing with local parser checks and a live Qwen/Qwen3.6-35B-A3B `--external-thinking on` smoke test on `generated_osc_linear_parameter_pair_012`, which parsed successfully and selected the oracle-best `E3`.
- Inspected the full tagged thinking-on `compare` batch:
  - output: `results/qwen_compare_thinking_tagged.jsonl`
  - 76 ok, 24 errors
  - exact: 0.579 on successful rows
  - utility ratio: 0.783 on successful rows
  - normalized regret: 0.246 on successful rows
  - near-optimal@0.8: 0.618 on successful rows
  - near-optimal@0.5: 0.763 on successful rows
  - on the 76 shared successful scenarios, tagged thinking-on outperformed fixed thinking-off compare (`utility_ratio=0.783` vs `0.623`)
  - remaining issue: parse failures still show no `<answer>` tag in the saved preview, so the model often spends too long in free reasoning before reaching the final tagged JSON.
- Reran only the 24 failed tagged thinking-on `compare` scenarios with `--external-max-tokens 8192`:
  - output: `results/qwen_compare_thinking_tagged_failed_8192.jsonl`
  - 24 ok, 0 errors
  - exact: 0.542
  - utility ratio: 0.831
  - normalized regret: 0.187
  - near-optimal@0.8: 0.75
  - near-optimal@0.5: 0.833
- Merged the original 76 successful tagged rows with the 24 successful 8192-token retries for an effective 100-scenario tagged thinking-on `compare` result:
  - exact: 0.57
  - utility ratio: 0.795
  - normalized regret: 0.232
  - near-optimal@0.8: 0.65
  - near-optimal@0.5: 0.78
  - predicted families: 42 initial-velocity, 37 extended-window, 21 velocity-channel

### Next Suggested Step

- Add a small analysis script for result JSONL files so family-distribution diagnostics and prompt-mode comparisons are reproducible instead of one-off shell snippets.
- Refine `compare` further to make extended observation windows competitive when the discriminating signal accumulates slowly over time.

## 2026-05-08

### Completed

- Aligned the no-simulator prompt wording with the current disagreement-based oracle.
- Updated [prompting/render_prompt.py](D:/science_agent/Proposer/prompting/render_prompt.py:1) so both `plain` and `contrast` modes ask for the experiment expected to produce the largest hypothesis separation, rather than the smallest discriminating experiment.
- Updated the oscillator scenario generator goal text in [generation/build_oscillator_scenarios.py](D:/science_agent/Proposer/generation/build_oscillator_scenarios.py:1).
- Regenerated the two files in [generated_scenarios](D:/science_agent/Proposer/generated_scenarios:1) so their visible `goal.success_criterion` matches the current oracle.
- Updated the illustrative example and README goal text to match the current max-separation benchmark setting.
- Added external generation controls to [agents/run_llm_baseline.py](D:/science_agent/Proposer/agents/run_llm_baseline.py:1) and [agents/external_model.py](D:/science_agent/Proposer/agents/external_model.py:1), including temperature, top-p, top-k, max tokens, and vLLM/Qwen-style thinking flags.
- Updated [README.md](D:/science_agent/Proposer/README.md:1) with an example command for running Qwen-style thinking models through vLLM.
- Added utility-regret evaluation metrics to [evaluation/compare_prediction_to_oracle.py](D:/science_agent/Proposer/evaluation/compare_prediction_to_oracle.py:1): predicted utility, oracle-best utility, raw regret, normalized regret, utility ratio, and near-optimal accuracy at 0.8 and 0.5.
- Verified the regret metrics on oracle-best, near-miss, and invalid experiment predictions for the generated nonlinear-vs-linear scenario.
- Added [agents/run_batch_baseline.py](D:/science_agent/Proposer/agents/run_batch_baseline.py:1), which runs a baseline over a scenario glob, writes JSONL per-scenario results, and prints aggregate accuracy/regret metrics.
- Refactored [agents/run_llm_baseline.py](D:/science_agent/Proposer/agents/run_llm_baseline.py:1) so the single-scenario and batch runners share the same prompt/prediction/external-model options.
- Smoke-tested the batch runner on the two generated scenarios with the heuristic baseline.
- Expanded [generation/build_oscillator_scenarios.py](D:/science_agent/Proposer/generation/build_oscillator_scenarios.py:1) into a seeded, filtered batch generator with `--num-scenarios`, `--seed`, `--output-dir`, `--max-attempts`, and `--clear-output`.
- Regenerated 20 oscillator scenarios under [generated_scenarios](D:/science_agent/Proposer/generated_scenarios:1) using `--num-scenarios 20 --seed 7`.
- Validated all 20 generated scenarios against the Pydantic schema and smoke-tested them with the batch heuristic runner.
- Hardened the external model parser in [agents/external_model.py](D:/science_agent/Proposer/agents/external_model.py:1) to handle fenced outputs, Python-style dictionaries, single quotes, lowercase booleans/nulls, and extra reasoning text before the prediction object.
- Updated [agents/run_batch_baseline.py](D:/science_agent/Proposer/agents/run_batch_baseline.py:1) so parse failures include a raw model output preview for debugging.
- Added `compare` prompt mode in [prompting/render_prompt.py](D:/science_agent/Proposer/prompting/render_prompt.py:1), which asks the model to compare each candidate experiment using channel capture, accumulation duration, excitation strength, and expected total separation before choosing.
- Extended the shared runner CLI so both single-scenario and batch runs accept `--prompt-mode compare`.

## 2026-05-05

### Completed

- Added a damped-oscillator simulator module at [simulators/damped_oscillator.py](D:/science_agent/Proposer/simulators/damped_oscillator.py:1).
- Added the `simulators` package marker at [simulators/__init__.py](D:/science_agent/Proposer/simulators/__init__.py:1).
- Ran a local smoke test to verify the simulator imports cleanly and produces `x`/`v` trajectories for a simple linear-damping case.
- Added hypothesis fit scoring at [scoring/hypothesis_fit.py](D:/science_agent/Proposer/scoring/hypothesis_fit.py:1).
- Added the `scoring` package marker at [scoring/__init__.py](D:/science_agent/Proposer/scoring/__init__.py:1).
- Ran a local fit-ranking smoke test against the example oscillator scenario and confirmed the two hypotheses receive very similar MSE scores, which matches the intended ambiguity of the example.
- Added ambiguity labeling at [scoring/ambiguity.py](D:/science_agent/Proposer/scoring/ambiguity.py:1).
- Ran a local ambiguity-labeling smoke test against the example oscillator scenario and confirmed it is labeled ambiguous under the current fit-score band rule.
- Added candidate experiment utility scoring at [scoring/experiment_utility.py](D:/science_agent/Proposer/scoring/experiment_utility.py:1).
- Ran a local experiment-ranking smoke test against the example oscillator scenario and confirmed the scorer produces a full oracle-style ranking over candidate experiments.
- Added an end-to-end backend runner at [run_oracle_pipeline.py](D:/science_agent/Proposer/run_oracle_pipeline.py:1).
- Ran the full oracle pipeline on the example scenario and confirmed it produces a single JSON report containing fit ranking, ambiguity assessment, experiment ranking, and oracle ground-truth output.
- Added a scenario generator at [generation/build_oscillator_scenarios.py](D:/science_agent/Proposer/generation/build_oscillator_scenarios.py:1).
- Added the `generation` package marker at [generation/__init__.py](D:/science_agent/Proposer/generation/__init__.py:1).
- Generated two oscillator scenarios under [generated_scenarios](D:/science_agent/Proposer/generated_scenarios:1).
- Ran the oracle pipeline on a generated scenario and confirmed the generated file is internally consistent with the current backend scoring logic.

## 2026-05-06

### Completed

- Upgraded the oscillator scenario generator so candidate experiments are explicit parameterized variants instead of one arbitrary instance per intervention family.
- Added generator helpers for window-extension, sampling-rate, velocity-channel, and initial-velocity experiment families.
- Regenerated the oscillator scenarios in [generated_scenarios](D:/science_agent/Proposer/generated_scenarios:1) with the expanded candidate library.
- Re-ran the oracle pipeline on the nonlinear-vs-linear generated scenario and confirmed the best experiment is now `E3 = extend_window_to_3s` under the current disagreement-based oracle.
- Updated [README.md](D:/science_agent/Proposer/README.md:1) to document parameterized experiment variants and the `experiment_family` / `parameterization` metadata pattern.
- Switched generated experiment naming from absolute values to ratio-based labels such as `extend_window_by_6x` and `increase_sampling_rate_by_5x`.
- Added explicit reference-scale handling for initial-velocity interventions, which now appear as names like `increase_initial_velocity_by_2x_ref` because the baseline scenario starts at zero initial velocity.
- Regenerated the oscillator scenarios and confirmed the oracle output now uses the ratio-based experiment names consistently.
- Added prompt rendering utilities at [prompting/render_prompt.py](D:/science_agent/Proposer/prompting/render_prompt.py:1) and [prompting/__init__.py](D:/science_agent/Proposer/prompting/__init__.py:1).
- Added prediction-vs-oracle evaluation at [evaluation/compare_prediction_to_oracle.py](D:/science_agent/Proposer/evaluation/compare_prediction_to_oracle.py:1) and [evaluation/__init__.py](D:/science_agent/Proposer/evaluation/__init__.py:1).
- Added the first no-simulator baseline runner at [agents/run_llm_baseline.py](D:/science_agent/Proposer/agents/run_llm_baseline.py:1).
- Ran smoke tests for both `plain` and `contrast` prompt modes on a generated scenario and confirmed the runner produces prompt text, structured predictions, and automatic oracle comparison.
- Observed the first useful failure signal: the heuristic baseline correctly predicts ambiguity but chooses `E1` instead of the oracle-best `E3`.
- Added external model integration at [agents/external_model.py](D:/science_agent/Proposer/agents/external_model.py:1).
- Extended [agents/run_llm_baseline.py](D:/science_agent/Proposer/agents/run_llm_baseline.py:1) with:
  - `external` prediction mode
  - `openai` and `vllm` provider options
  - prompt export via `--write-prompt`
  - prediction template export via `--write-prediction-template`
- Generated and verified a `from-file` prediction template containing allowed hypothesis and experiment ids.
- Ran local mock-server integration tests confirming the external prediction path works for a vLLM-style OpenAI-compatible endpoint.
- Updated [README.md](D:/science_agent/Proposer/README.md:1) with concrete usage examples for `openai`, `vllm`, and the manual `from-file` workflow.

### Simulator Scope

The current simulator supports:

- linear damping hypotheses with parameters `m`, `c`, and `k`
- weak nonlinear damping hypotheses with parameters `m`, `c1`, `c2`, and `k`
- optional sinusoidal drive via amplitude and frequency parameters
- fixed-step RK4 integration
- measurement output for channels `x` and `v`

### Notes

- The simulator is intended for benchmark generation and oracle evaluation, not for direct LLM access in the main no-simulator setting.
- It includes helpers to construct simulator hypotheses from schema-style parameter payloads so it can later plug into scenario generation and scoring code.
- The first fit scorer assumes a uniformly sampled observation episode that starts at `t = 0.0`, and it requires the caller to provide the experiment initial state explicitly.
- The first experiment utility scorer uses average pairwise absolute trajectory disagreement over the measured channels as its utility.
- The current executable oracle ranks `E1` above `E4` for the example scenario, which does not match the hand-written example label. This means the example JSON should now be treated as illustrative rather than oracle-validated until we reconcile the scenario design and scoring rule.
- The generated scenarios are a better starting point for evaluation than the hand-written example because their ambiguity labels and best-experiment labels are produced by the same backend oracle that will be used for scoring.
- The candidate experiment library is now less arbitrary because each main intervention family can appear with several concrete parameter settings, allowing both the oracle and later the LLM to choose among explicit variants.
- Ratio-based naming makes candidate experiments easier to compare across scenarios because the labels are normalized to the baseline setup instead of tied to one absolute value scale.
- The current baseline runner now supports three prediction paths: `heuristic`, `from-file`, and `external`.
- The `vllm` mode uses an OpenAI-style `/v1/chat/completions` endpoint and does not require an API key by default, which makes it suitable for common local vLLM setups.

### Next Suggested Step

- Completed on 2026-05-09. The next step is to turn the ad hoc result-slicing analysis into a reusable script and continue addressing the extended-window under-selection bias.
