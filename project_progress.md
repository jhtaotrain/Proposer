# Project Progress

## 2026-05-08

### Completed

- Aligned the no-simulator prompt wording with the current disagreement-based oracle.
- Updated [prompting/render_prompt.py](D:/science_agent/Proposer/prompting/render_prompt.py:1) so both `plain` and `contrast` modes ask for the experiment expected to produce the largest hypothesis separation, rather than the smallest discriminating experiment.
- Updated the oscillator scenario generator goal text in [generation/build_oscillator_scenarios.py](D:/science_agent/Proposer/generation/build_oscillator_scenarios.py:1).
- Regenerated the two files in [generated_scenarios](D:/science_agent/Proposer/generated_scenarios:1) so their visible `goal.success_criterion` matches the current oracle.
- Updated the illustrative example and README goal text to match the current max-separation benchmark setting.
- Added external generation controls to [agents/run_llm_baseline.py](D:/science_agent/Proposer/agents/run_llm_baseline.py:1) and [agents/external_model.py](D:/science_agent/Proposer/agents/external_model.py:1), including temperature, top-p, top-k, max tokens, and vLLM/Qwen-style thinking flags.
- Updated [README.md](D:/science_agent/Proposer/README.md:1) with an example command for running Qwen-style thinking models through vLLM.

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

- Add a small batch runner so we can score many scenarios and summarize aggregate ambiguity accuracy and experiment-selection accuracy across a generated set.
