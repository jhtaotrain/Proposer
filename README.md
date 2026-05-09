# Science Agent Scenario Format

This project defines a structured data format for scientific reasoning tasks where an agent must:

1. inspect current experimental observations,
2. decide whether the evidence is still ambiguous,
3. and, if so, choose the most useful next experiment.

The canonical example in this repository is [example_damped_oscillator_scenario.json](D:/science_agent/Proposer/example_damped_oscillator_scenario.json:1), and the schema is defined in [science_agent_schema.py](D:/science_agent/Proposer/science_agent_schema.py:1).

## Files

- [science_agent_schema.py](D:/science_agent/Proposer/science_agent_schema.py:1): Pydantic schema for scenario data.
- [example_damped_oscillator_scenario.json](D:/science_agent/Proposer/example_damped_oscillator_scenario.json:1): Example scenario instance.
- [proposed_experiment_summary.md](D:/science_agent/Proposer/proposed_experiment_summary.md:1): Original design discussion and research framing.

## Top-Level JSON Structure

Each JSON file represents one `Scenario`.

```json
{
  "schema_version": "0.1",
  "scenario_id": "osc_lin_vs_nonlinear_001",
  "domain": "damped_oscillator",
  "goal": { ... },
  "observations": { ... },
  "hypotheses": [ ... ],
  "candidate_experiments": [ ... ],
  "ambiguity_assessment": { ... },
  "ground_truth": { ... },
  "metadata": { ... }
}
```

## Field-by-Field Description

### `schema_version`

Schema version for the scenario file.

- Type: `string`
- Purpose: allows the format to evolve without silently breaking old data
- Example: `"0.1"`

### `scenario_id`

Unique identifier for the scenario.

- Type: `string`
- Purpose: lets us track a sample across evaluation, debugging, and dataset generation
- Example: `"osc_lin_vs_nonlinear_001"`

### `domain`

Scientific domain or task family for the scenario.

- Type: `string`
- Current examples:
  - `"damped_oscillator"`
  - `"circuit"`
  - `"custom"`
- Purpose: makes it possible to support multiple scientific systems with one common format

## `goal`

Describes what the agent is trying to achieve in this scenario.

```json
"goal": {
  "type": "distinguish_hypotheses",
  "description": "Determine which damping mechanism best explains the observed trajectory.",
  "success_criterion": "Select the candidate experiment expected to produce the largest separation between the remaining plausible hypotheses."
}
```

### `goal.type`

High-level task category.

- Type: `string`
- Current supported values:
  - `"identify_mechanism"`
  - `"estimate_parameters"`
  - `"distinguish_hypotheses"`
  - `"optimize_outcome"`
  - `"custom"`

### `goal.description`

Natural-language description of the scientific objective.

- Type: `string`
- Purpose: useful for agent prompting and human interpretation

### `goal.success_criterion`

Optional description of what counts as success.

- Type: `string | null`
- Purpose: clarifies the evaluation target for the scenario

## `observations`

Contains the current evidence available to the agent.

```json
"observations": {
  "episodes": [ ... ],
  "observability": { ... }
}
```

### `observations.episodes`

List of observation episodes. An episode is one experimental run or one measurement record.

- Type: `list`
- Purpose: supports multiple runs, multiple conditions, and later real datasets

Each episode contains:

#### `episode_id`

Identifier for this observation record.

- Type: `string`

#### `condition_id`

Identifier for the experimental condition under which the observation was collected.

- Type: `string`
- Example: `"baseline_short_window"`

#### `measured_channels`

Names of the variables actually observed in this episode.

- Type: `list[string]`
- Example: `["x"]`
- Purpose: distinguishes observed variables from hidden state variables

#### `time`

Time points associated with the measurements.

- Type: `list[float]`
- Purpose: stores the time axis explicitly so irregular sampling is possible later

#### `values`

Measured data values keyed by channel name.

- Type: `object`
- Example:

```json
"values": {
  "x": [1.0, 0.961, 0.857, 0.703, 0.517, 0.319]
}
```

- Rule: every channel in `measured_channels` must appear here
- Rule: each value array must have the same length as `time`

#### `noise_model`

Optional description of measurement noise.

- Type: `object | null`
- Example:

```json
"noise_model": {
  "type": "gaussian",
  "std": 0.02
}
```

Fields inside `noise_model`:

- `type`: current options are `"gaussian"`, `"uniform"`, `"none"`, `"custom"`
- `std`: optional standard deviation for simple Gaussian noise
- `parameters`: optional extra dictionary for custom noise settings

#### `summary_stats`

Optional scalar summaries extracted from the raw trace.

- Type: `object`
- Example:

```json
"summary_stats": {
  "observed_peak_count": 1,
  "window_duration": 0.5
}
```

- Purpose: supports tasks where we want the agent to see summaries in addition to or instead of raw data

#### `metadata`

Optional episode-specific extra information.

- Type: `object`

### `observations.observability`

Describes which variables are observable and which are hidden.

```json
"observability": {
  "available_channels": ["x"],
  "hidden_channels": ["v"],
  "notes": "Only position is measured in the current run."
}
```

Fields:

- `available_channels`: variables that can currently be measured
- `hidden_channels`: known but currently unobserved variables
- `notes`: optional explanation

## `hypotheses`

List of scientific hypotheses still under consideration.

```json
"hypotheses": [
  { ... },
  { ... }
]
```

Each hypothesis contains:

### `hypothesis_id`

Unique identifier for the hypothesis.

- Type: `string`
- Example: `"H1"`

### `name`

Short label for the hypothesis.

- Type: `string`
- Example: `"linear_damping"`

### `description`

Natural-language description of the mechanism.

- Type: `string`

### `family`

Model family for the hypothesis.

- Type: `string`
- Current supported values:
  - `"ode"`
  - `"discrete_dynamics"`
  - `"circuit"`
  - `"probabilistic"`
  - `"empirical_black_box"`
  - `"custom"`

### `mechanism_tags`

Tags that capture the scientific mechanism.

- Type: `list[string]`
- Examples:
  - `["linear_damping"]`
  - `["nonlinear_damping"]`

### `model`

Structured, machine-readable representation of the hypothesis.

```json
"model": {
  "state_variables": ["x", "v"],
  "observed_variables": ["x"],
  "parameters": {
    "m": 1.0,
    "c": 0.3,
    "k": 2.0
  },
  "equations": {
    "type": "symbolic_ode",
    "state_order": ["x", "v"],
    "rhs": [
      "v",
      "(-c * v - k * x) / m"
    ]
  }
}
```

Fields inside `model`:

#### `state_variables`

All latent or explicit state variables used by the model.

- Type: `list[string]`
- Example: `["x", "v"]`

#### `observed_variables`

State variables or outputs the current hypothesis maps to observations.

- Type: `list[string]`

#### `parameters`

Parameter values or parameter settings for this hypothesis.

- Type: `object`
- Example:

```json
"parameters": {
  "m": 1.0,
  "c1": 0.24,
  "c2": 0.08,
  "k": 2.0
}
```

#### `equations`

Structured symbolic representation of the model equations.

- Type: `object | null`

Fields inside `equations`:

- `type`: current options are `"symbolic_ode"`, `"symbolic_algebraic"`, `"custom"`
- `state_order`: ordering of states expected by the equation system
- `rhs`: right-hand side expressions for state evolution
- `expression`: optional single-expression form for non-ODE cases

#### `simulator_ref`

Optional reference to a simulator implementation.

- Type: `string | null`
- Purpose: allows later connection between schema data and executable code

#### `metadata`

Optional model-specific extra information.

- Type: `object`

### `fit_to_current_data`

Optional fit score describing how well this hypothesis explains the current observations.

```json
"fit_to_current_data": {
  "score": 0.013,
  "score_type": "mse"
}
```

Fields:

- `score`: numeric fit value
- `score_type`: current options are `"mse"`, `"nll"`, `"mae"`, `"custom"`
- `details`: optional extra breakdown

This field is especially useful for ambiguity detection because the agent or evaluator can determine whether several hypotheses remain similarly plausible.

## `candidate_experiments`

Discrete list of next experiments the agent may choose from.

```json
"candidate_experiments": [
  { ... },
  { ... }
]
```

Each experiment contains:

### `experiment_id`

Unique identifier for the candidate experiment.

- Type: `string`
- Example: `"E4"`

### `name`

Short experiment label.

- Type: `string`
- Examples:
  - `"extend_window_by_6x"`
  - `"increase_sampling_rate_by_5x"`
  - `"increase_initial_velocity_by_2x_ref"`

### `description`

Natural-language description of the experiment.

- Type: `string`

### `intervention_type`

The broad type of intervention being performed.

- Type: `string`
- Current supported values:
  - `"measurement_change"`
  - `"initial_condition_change"`
  - `"input_change"`
  - `"multi_factor"`
  - `"custom"`

### `changes`

Structured description of what is changed relative to the current setup.

- Type: `object`
- Examples:
  - changing the time window
  - increasing sampling rate
  - adding measured channels
  - changing initial conditions

This field is intentionally flexible because future scientific domains may need different intervention parameters.

In the current oscillator generator, candidate experiments are represented as
explicit parameterized variants rather than one arbitrary instance per family.
For example:

- multiple window extensions like `2x`, `4x`, `6x` the baseline duration
- multiple sampling rates like `2x`, `5x`, `10x` the baseline sampling rate
- multiple initial-velocity interventions like `1x_ref`, `2x_ref`

This keeps the task discrete while making the benchmark less dependent on one
handpicked parameter choice.

For interventions where the baseline value is zero, such as initial velocity in
the current oscillator scenarios, the generator uses an explicit nonzero
reference scale and marks the variant name with `_ref`.

### `measurement_plan`

Describes what will be measured under this candidate experiment.

```json
"measurement_plan": {
  "channels": ["x", "v"],
  "sampling_rate": 10.0,
  "time_window": {
    "start": 0.0,
    "end": 0.5
  }
}
```

Fields:

- `channels`: variables to measure
- `sampling_rate`: planned sampling frequency
- `time_window`: measurement start and end time
- `metadata`: optional extra information

Generated oscillator scenarios use `measurement_plan.metadata` to record:

- `experiment_family`: the abstract intervention family
- `parameterization`: the concrete parameter values used for this candidate

### `ambiguity_tags`

Tags indicating what type of ambiguity this experiment is expected to address.

- Type: `list[string]`
- Current supported values:
  - `"short_window"`
  - `"low_resolution"`
  - `"hidden_variable"`
  - `"weak_excitation"`
  - `"parameter_degeneracy"`
  - `"none"`
  - `"custom"`

Examples:

- extending the horizon may target `"short_window"`
- adding a velocity measurement may target `"hidden_variable"`
- increasing drive or initial velocity may target `"weak_excitation"`

### `cost`

Optional scalar cost for the candidate experiment.

- Type: `float | null`
- Purpose: enables future cost-aware experiment selection

### `metadata`

Optional experiment-specific extra information.

- Type: `object`

Generated oscillator scenarios currently use this field for:

- `experiment_family`
- `parameterization`

This preserves both the high-level action type and the exact instantiated
variant being scored by the oracle.

## `ambiguity_assessment`

Optional structured label describing whether the current evidence is sufficient to distinguish the hypotheses.

```json
"ambiguity_assessment": {
  "is_ambiguous": true,
  "compatible_hypotheses": ["H1", "H2"],
  "rejected_hypotheses": [],
  "ambiguity_type": "short_window",
  "criterion": {
    "type": "fit_score_band",
    "threshold": 0.01,
    "parameters": {
      "best_score": 0.013,
      "max_allowed_gap": 0.01
    }
  },
  "explanation": "Both hypotheses fit the short position-only trajectory nearly equally well."
}
```

Fields:

### `is_ambiguous`

Whether the current evidence is still unresolved.

- Type: `boolean`

### `compatible_hypotheses`

Hypotheses that remain plausible under the current observations.

- Type: `list[string]`
- Rule: each item must match an existing `hypothesis_id`

### `rejected_hypotheses`

Hypotheses considered inconsistent with the current evidence.

- Type: `list[string]`
- Rule: each item must match an existing `hypothesis_id`

### `ambiguity_type`

High-level reason why the evidence is still ambiguous.

- Type: `string`
- Current values:
  - `"short_window"`
  - `"low_resolution"`
  - `"hidden_variable"`
  - `"weak_excitation"`
  - `"parameter_degeneracy"`
  - `"none"`
  - `"custom"`

### `criterion`

Structured record of how ambiguity was decided.

Fields:

- `type`: name of the decision rule
- `threshold`: optional numeric cutoff
- `parameters`: optional details of the rule

Example:

- `type = "fit_score_band"` means several hypotheses are kept if their fit scores are within a threshold of the best score

### `explanation`

Optional human-readable explanation of the ambiguity judgment.

- Type: `string | null`

## `ground_truth`

Optional oracle label used for supervised evaluation or benchmark generation.

```json
"ground_truth": {
  "true_hypothesis_id": "H2",
  "best_experiment_id": "E4",
  "experiment_utilities": {
    "E1": 0.42,
    "E2": 0.09,
    "E3": 0.31,
    "E4": 0.68
  },
  "utility_score_type": "predicted_disagreement",
  "explanation": "A stronger initial velocity drives the system into a regime where nonlinear damping produces larger disagreement."
}
```

Fields:

### `true_hypothesis_id`

The actual generating hypothesis, if known.

- Type: `string | null`
- Rule: must match one of the `hypothesis_id` values if present

### `best_experiment_id`

The oracle-best next experiment.

- Type: `string | null`
- Rule: must match one of the `experiment_id` values if present

### `experiment_utilities`

Utility scores for candidate experiments.

- Type: `object`
- Format: maps `experiment_id -> score`
- Purpose: supports ranking-based evaluation, not just top-1 choice

### `utility_score_type`

Describes how the utility was computed.

- Type: `string | null`
- Current values:
  - `"predicted_disagreement"`
  - `"pairwise_average_disagreement"`
  - `"min_pairwise_disagreement"`
  - `"custom"`

### `explanation`

Human-readable explanation for why the best experiment is useful.

- Type: `string | null`

## `metadata`

Optional scenario-level provenance and dataset-generation information.

```json
"metadata": {
  "generator": "manual_prototype_v1",
  "seed": 7,
  "difficulty": "medium",
  "source": "programmatic",
  "notes": "Prototype sample for schema validation and prompt-design work."
}
```

Fields:

- `generator`: dataset or script name that produced the sample
- `seed`: random seed if generated stochastically
- `difficulty`: informal difficulty label
- `source`: where the sample came from
- `notes`: free-form comments

## Validation Rules

The schema currently enforces several important consistency checks:

- every `hypothesis_id` must be unique
- every `experiment_id` must be unique
- every measured channel must appear in `values`
- every channel in `values` must be listed in `measured_channels`
- every value array must have the same length as `time`
- `ground_truth.true_hypothesis_id` must refer to an existing hypothesis if present
- `ground_truth.best_experiment_id` must refer to an existing experiment if present
- `ambiguity_assessment.compatible_hypotheses` must refer to existing hypotheses
- `ambiguity_assessment.rejected_hypotheses` must refer to existing hypotheses

## Why This Format Was Chosen

This format is designed to scale from the first toy benchmark to a broader science-agent system.

It supports:

- synthetic and real observations
- multiple scientific domains
- structured hypotheses with executable meaning
- discrete experiment selection
- ambiguity detection
- oracle labeling for evaluation
- future agent prompting built from structured data

The key principle is that the JSON is the source of truth. Natural-language prompts can be rendered from it later, but should not replace the structured representation.

## LLM Evaluation Modes

The benchmark runner at [agents/run_llm_baseline.py](D:/science_agent/Proposer/agents/run_llm_baseline.py:1)
supports three prediction paths:

- `heuristic`: a simple rule-based no-simulator baseline
- `from-file`: load a manually prepared structured prediction JSON
- `external`: call an external model automatically

### External Providers

The `external` mode currently supports:

- `openai`: the real OpenAI chat completions API
- `vllm`: a local or remote vLLM server exposing an OpenAI-style `/v1/chat/completions` endpoint

Example with OpenAI:

```powershell
$env:OPENAI_API_KEY="your_key_here"
python agents/run_llm_baseline.py generated_scenarios/generated_osc_nonlinear_vs_linear_001.json --prediction-mode external --external-provider openai --external-model gpt-4.1-mini
```

Example with vLLM:

```powershell
python agents/run_llm_baseline.py generated_scenarios/generated_osc_nonlinear_vs_linear_001.json --prediction-mode external --external-provider vllm --external-model your-model-name --external-base-url http://localhost:8000/v1/chat/completions
```

Example with a Qwen-style thinking model served through vLLM:

```powershell
python agents/run_llm_baseline.py generated_scenarios/generated_osc_nonlinear_vs_linear_001.json --prompt-mode contrast --prediction-mode external --external-provider vllm --external-model Qwen/Qwen3.6-35B-A3B --external-base-url http://localhost:8000/v1/chat/completions --external-temperature 1.0 --external-top-p 0.95 --external-top-k 20 --external-max-tokens 4096 --external-thinking on --external-timeout-sec 180
```

The extra sampling controls are useful for local reasoning models. `--external-top-k`
and `--external-thinking` are sent only to the `vllm` provider. For Qwen-style
reasoning output, runs with `--external-thinking on` ask the model to write
free reasoning inside `<think>...</think>` and the final prediction JSON inside
`<answer>...</answer>`. The parser prefers the JSON inside the final
`<answer>` block and then falls back to the older object-extraction parser. For
strict JSON evaluation without explicit reasoning text, `--external-thinking off`
is still the most reliable setting.

### Batch Evaluation

Use [agents/run_batch_baseline.py](D:/science_agent/Proposer/agents/run_batch_baseline.py:1)
to run the same baseline over many scenario files and write one JSON result per
line:

```powershell
python agents/run_batch_baseline.py --scenario-glob "generated_scenarios/*.json" --output-jsonl results/qwen_contrast.jsonl --prompt-mode contrast --prediction-mode external --external-provider vllm --external-model Qwen/Qwen3.6-35B-A3B --external-base-url http://localhost:8000/v1/chat/completions --external-temperature 1.0 --external-top-p 0.95 --external-top-k 20 --external-max-tokens 4096 --external-thinking on --external-timeout-sec 180 --continue-on-error
```

The batch runner prints a stderr progress bar by default, including the current
scenario, completed count, and ok/error counts. Use `--no-progress` to disable
it. JSONL rows are flushed after each scenario, so an interrupted run can be
inspected with `tail -1 <output-jsonl>`.

For a quick local smoke test without a model server:

```powershell
python agents/run_batch_baseline.py --scenario-glob "generated_scenarios/*.json" --output-jsonl results/heuristic.jsonl --prompt-mode contrast --prediction-mode heuristic
```

The printed summary reports aggregate accuracy, regret, utility ratio, and
near-optimal rates across successful rows.

The external parser accepts strict JSON as well as common local-model variants
such as fenced JSON, Python-style dictionaries with single quotes, and lowercase
`true` / `false` / `null` values. If parsing still fails, batch error rows include
a short raw-output preview for debugging.

The prompt renderer supports three modes:

- `plain`: direct ambiguity and experiment-choice instructions
- `contrast`: asks the model to contrast surviving hypotheses before choosing
- `compare`: asks the model to compare each candidate experiment internally using channel capture, accumulation duration, excitation strength, and expected measured trajectory separation before choosing

Example compare-mode run:

```powershell
python agents/run_batch_baseline.py --scenario-glob "generated_scenarios/*.json" --output-jsonl results/qwen_compare_fixed_thinking_off.jsonl --prompt-mode compare --prediction-mode external --external-provider vllm --external-model Qwen/Qwen3.6-35B-A3B --external-base-url http://localhost:8000/v1/chat/completions --external-temperature 0 --external-max-tokens 2048 --external-thinking off --external-timeout-sec 180 --continue-on-error
```

Example compare-mode run that keeps Qwen-style thinking enabled while using the
tagged answer parser:

```powershell
python agents/run_batch_baseline.py --scenario-glob "generated_scenarios/*.json" --output-jsonl results/qwen_compare_thinking_tagged.jsonl --prompt-mode compare --prediction-mode external --external-provider vllm --external-model Qwen/Qwen3.6-35B-A3B --external-base-url http://localhost:8000/v1/chat/completions --external-temperature 1.0 --external-top-p 0.95 --external-top-k 20 --external-max-tokens 4096 --external-thinking on --external-timeout-sec 180 --continue-on-error
```

Recent controlled Qwen/Qwen3.6-35B-A3B runs on the 100 generated scenarios used
`temperature=0`, `thinking=off`, and `max_tokens=2048`:

| result file | prompt mode | ok/errors | exact | utility ratio | normalized regret | near-opt 0.8 | near-opt 0.5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `results/qwen_compare_fixed_thinking_off.jsonl` | `compare` | 100/0 | 0.27 | 0.637 | 0.404 | 0.35 | 0.61 |
| `results/qwen_contrast_thinking_off.jsonl` | `contrast` | 100/0 | 0.06 | 0.447 | 0.611 | 0.13 | 0.37 |

The fixed `compare` prompt improved over the earlier thinking-off compare run
(`exact=0.15`, `utility_ratio=0.528`) by making excitation subordinate to
measured trajectory separation. Its remaining bias is over-selecting velocity
measurements and never selecting extended-window experiments, even though the
oracle best family is split across velocity channels, extended windows, and
initial-velocity interventions.

### Scenario Generation

Use [generation/build_oscillator_scenarios.py](D:/science_agent/Proposer/generation/build_oscillator_scenarios.py:1)
to generate a filtered batch of damped-oscillator scenarios:

```powershell
python generation/build_oscillator_scenarios.py --num-scenarios 20 --seed 7 --output-dir generated_scenarios --clear-output
```

The generator samples oscillator hypothesis pairs, baseline windows, sampling
rates, initial conditions, and candidate experiment libraries. It keeps only
scenarios that remain ambiguous under the current observations and have a usable
oracle utility ranking. The current generated batch includes oracle-best
experiments from multiple intervention families, including extended observation
windows, velocity-channel measurements, and increased initial velocity.

### Manual `from-file` Workflow

To export a prompt and a prediction template for manual model use:

```powershell
python agents/run_llm_baseline.py generated_scenarios/generated_osc_nonlinear_vs_linear_001.json --write-prompt prompt.txt --write-prediction-template prediction_template.json
```

Then evaluate a filled template with:

```powershell
python agents/run_llm_baseline.py generated_scenarios/generated_osc_nonlinear_vs_linear_001.json --prediction-mode from-file --prediction-file prediction.json
```

### Evaluation Metrics

The evaluator reports strict correctness plus utility-aware near-miss metrics.

- `chosen_experiment_correct`: whether the predicted experiment exactly matches the oracle-best experiment.
- `predicted_experiment_valid`: whether the predicted experiment id appears in the candidate set.
- `predicted_experiment_utility`: oracle utility assigned to the predicted experiment. Invalid predictions receive the worst candidate utility.
- `oracle_best_utility`: utility of the oracle-best experiment.
- `raw_utility_regret`: `oracle_best_utility - predicted_experiment_utility`.
- `normalized_utility_regret`: regret divided by the utility range between the oracle-best and worst candidates. Lower is better.
- `utility_ratio`: `predicted_experiment_utility / oracle_best_utility`. Higher is better.
- `near_optimal_at_0_8`: whether the predicted experiment reaches at least 80% of oracle-best utility.
- `near_optimal_at_0_5`: whether the predicted experiment reaches at least 50% of oracle-best utility.

## Next Suggested Additions

The schema is ready for the next layer of the project:

- a damped-oscillator simulator interface
- a function to score hypothesis fit to observations
- an ambiguity decision rule implementation
- an oracle utility computation for candidate experiments
- a prompt renderer that turns a `Scenario` into model input

## Project Architecture

This project naturally separates into two systems:

- the LLM-facing agent, which must reason from the provided observations, hypotheses, and candidate experiments
- the benchmark backend, which generates scenarios and determines the oracle answers for evaluation

This separation is important. The main LLM setting should not depend on simulator access, while the benchmark backend should use simulators and scoring logic to decide whether a case is truly ambiguous and which experiment is actually most discriminative.

### 1. Scenario Generator + Simulator

This is the backend component that creates scientific reasoning problems in a controlled way.

What it does:

- defines a true underlying system
- generates observed data under restricted measurement conditions
- constructs competing hypotheses that can all plausibly explain the current data
- defines candidate next experiments
- simulates what each hypothesis predicts under each candidate experiment

Why it matters:

- this is how benchmark instances are created
- it ensures the ambiguity is real rather than just described in prose
- it gives the project a reproducible source of truth

How to implement it:

- start with one domain, the damped oscillator
- create a module such as `simulators/damped_oscillator.py`
- implement a function that simulates trajectories from:
  - a hypothesis
  - initial conditions
  - an observation window
  - a sampling rate
  - optional noise
- create a scenario-building module such as `generation/build_oscillator_scenario.py`
- for each scenario:
  - choose a true hypothesis and parameter setting
  - generate limited observations
  - define 2 to 4 competing hypotheses
  - define a discrete library of candidate experiments
  - serialize the result into the schema in this repository

Version 1 scope:

- measure only a small number of channels, such as position `x`
- induce ambiguity with short windows, low resolution, hidden variables, or weak excitation
- keep candidate experiments discrete rather than free-form

### 2. Oracle Labeler

This is the component that determines the correct answer for evaluation.

What it does:

- decides whether the current evidence is still ambiguous
- scores each candidate experiment by how well it distinguishes plausible hypotheses
- identifies the oracle-best next experiment

Why it matters:

- this is how we know whether the LLM made the right choice
- it produces target labels for both ambiguity detection and next-experiment selection

How to implement it:

- create `scoring/ambiguity.py`
- create `scoring/experiment_utility.py`

For ambiguity assessment:

- compute a fit score for each hypothesis against the observed data
- keep all hypotheses within a threshold of the best fit
- if more than one hypothesis survives, mark the case as ambiguous

For experiment utility:

- for each candidate experiment
- simulate the predicted response under each surviving hypothesis
- compute disagreement between those predicted responses
- use that disagreement as the experiment utility

Simple starting choices:

- fit score: mean squared error on observed channels
- utility: average absolute trajectory difference between hypotheses

Where the results go:

- write ambiguity outputs into `ambiguity_assessment`
- write oracle experiment ranking outputs into `ground_truth`

Important boundary:

- this logic is for the evaluator and dataset generator
- the LLM should not see these oracle scores in the main no-simulator setting

### 3. LLM Prompt Runner

This is the actual science-agent side of the project.

What it does:

- turns a structured `Scenario` into model input
- asks the model whether the evidence is sufficient
- asks the model to choose the best next experiment if the case is unresolved
- records the model output in a structured form

Why it matters:

- this is the core capability the project is studying
- this is where the main benchmark claim lives

How to implement it:

- create `prompting/render_prompt.py`
- create `agents/run_llm_baseline.py`

The prompt renderer should expose:

- the scientific goal
- the current observations
- the competing hypotheses
- the candidate experiments

The prompt renderer should not expose in the main setting:

- simulator outputs
- fit scores
- oracle labels

Recommended prompt styles for version 1:

- plain direct prompt
- hypothesis-contrast prompt

Recommended output format:

```json
{
  "is_ambiguous": true,
  "compatible_hypotheses": ["H1", "H2"],
  "chosen_experiment_id": "E4",
  "reasoning": "The current short window does not reveal whether damping is velocity dependent. Increasing initial velocity should amplify nonlinear effects."
}
```

Implementation note:

- keep model outputs machine-parseable whenever possible
- avoid relying only on long free-form text answers

### 4. Evaluator

This component compares model predictions against oracle labels.

What it does:

- measures whether the model correctly recognized ambiguity
- measures whether the model selected the best next experiment
- optionally evaluates rankings and explanation quality later

Why it matters:

- this is how benchmark performance is reported
- this is how we detect stable failure modes

How to implement it:

- create `evaluation/evaluate_predictions.py`

Useful starting metrics:

- ambiguity classification accuracy
- top-1 experiment selection accuracy
- top-k accuracy if needed
- rank correlation if the model outputs full rankings later

Useful error categories to log:

- premature commitment to one hypothesis
- choosing a generic safe experiment
- targeting the wrong source of ambiguity
- choosing a more expensive experiment when a smaller one would suffice

Implementation note:

- explanation grading should be optional at first
- the first goal is clean structural evaluation of the decision

## Recommended Implementation Order

The best build order for the first end-to-end prototype is:

1. `simulators/damped_oscillator.py`
2. `generation/build_oscillator_scenario.py`
3. `scoring/ambiguity.py`
4. `scoring/experiment_utility.py`
5. `prompting/render_prompt.py`
6. `evaluation/evaluate_predictions.py`

This gives the project a full loop:

1. generate a scenario
2. assign oracle ambiguity and best-experiment labels
3. run the LLM without simulator access
4. evaluate the LLM output against the oracle

## What Not to Overbuild Yet

For version 1, it is better to avoid:

- multi-domain code support beyond what the schema already allows
- free-form generation of new experiments
- heavy optimal-design machinery
- training-based methods
- full simulator access for the LLM in the main benchmark setting

The first milestone should be much smaller:

- generate valid ambiguous oscillator scenarios
- compute oracle-best next experiments
- test whether LLMs fail on this task without simulator access
