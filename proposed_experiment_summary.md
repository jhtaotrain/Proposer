# Proposed Experiment Summary

## 1. Project framing

### Primary framing
The main paper should frame the project as:

> **studying LLM scientific reasoning ability**, rather than claiming to have built a fully useful “LLM physicist” or “LLM experimental scientist.”

### Core capability of interest
The target capability is:

> when multiple scientific hypotheses are all compatible with current observations, can an LLM recognize that the problem is still unresolved and choose the **minimal discriminating experiment**?

### Why this framing is safer for AI top venues
The recommended main claim is:

> **We study a neglected dimension of LLM scientific reasoning: selecting minimal discriminating experiments under competing hypotheses.**

Not:

> We build a useful LLM physicist / experimental scientist.

The reason is that the second claim is too large and invites reviewer demands about:
- real experimental deployment
- comparison against classical experiment-design methods
- realistic noise and hardware constraints
- strong external validity

The more top-conference-friendly framing is:
- define a capability
- formalize it clearly
- build a controlled benchmark
- diagnose failure modes
- show a lightweight improvement

---

## 2. Main proposed problem

### Working title
**Minimal Discriminating Experiment for Scientific Hypotheses**

### One-sentence definition
Given current observations and multiple competing scientific hypotheses that all explain them, select the **smallest next experiment** that best distinguishes between the hypotheses.

### What the task is *not*
This task is **not**:
- generic prompt engineering
- a standard ambiguity benchmark
- a generic abstention benchmark
- just a clarifying-question benchmark
- a full autonomous scientific-discovery system

### What the task *is*
It is a benchmark and reasoning task about:
- **scientific identifiability**
- **hypothesis discrimination**
- **experiment selection under uncertainty**

---

## 3. Key distinction from nearby work

### Nearby general benchmark families
Nearby work in general LLM evaluation often studies:
- missing variables
- underspecified problems
- ambiguous user intent
- whether the model should abstain
- whether the model should ask a clarifying question

### Proposed distinction
In the proposed task:
- the problem statement can be complete
- the current observations can be valid
- but the evidence still does **not uniquely identify** the true mechanism

So the problem is not:

> “what missing value should I ask for?”

It is:

> “which next experiment would most efficiently distinguish competing hypotheses?”

This makes the object closer to:
- **scientific identifiability**
- **model discrimination**
- **experiment design under competing theories**

---

## 4. Minimum viable benchmark design

The benchmark should be:

> **small, clean, and programmatically generated**

It should **not** initially be a giant manually annotated benchmark.

### Recommended style
A **controlled evaluation suite**, not a broad real-world benchmark.

### Initial scope
Use only **1–2 toy system families**:
1. damped oscillators
2. simple RC / RLC-style circuits

This is sufficient for a first paper if:
- the task is clean
- the oracle is stable
- the failure mode is sharp

---

## 5. Family 1: damped oscillator

### Example competing hypotheses

#### Hypothesis \(H_1\): linear damping
\[
m \ddot{x} + c \dot{x} + kx = 0
\]

#### Hypothesis \(H_2\): weak nonlinear damping
\[
m \ddot{x} + \left(c_1 + c_2 |\dot{x}|\right)\dot{x} + kx = 0
\]

#### Hypothesis \(H_3\): linear damping with small external drive
\[
m \ddot{x} + c \dot{x} + kx = A\cos(\omega t)
\]

### Design principle
Only provide:
- a short time window
- weak excitation
- limited measurement channels
- or low-resolution observations

so that multiple hypotheses remain plausible given current data.

### Candidate experiment library
Use a **discrete** experiment space, for example:
- extend the observation window
- increase the sampling rate
- change the initial displacement
- change the initial velocity
- observe the energy envelope instead of only position
- sweep the driving frequency
- measure phase lag
- add another observation channel

---

## 6. Family 2: simple circuit systems

### Example competing hypotheses
- \(H_1\): first-order RC
- \(H_2\): RLC but approximately first-order in the currently observed regime
- \(H_3\): RC + measurement lag
- \(H_4\): two parameter settings with nearly identical short-time response

### Candidate experiment library
Again use a **discrete** candidate set, for example:
- change pulse width
- change input frequency
- extend observation time
- measure current in addition to voltage
- change initial capacitor voltage
- compare step input vs sinusoidal input

---

## 7. Data format per benchmark sample

Each benchmark sample should contain five objects.

### 1. Observed data \(D\)
Examples:
- a short time series
- sparse measurements
- a small set of summary statistics

### 2. Competing hypotheses
\[
\{H_1, H_2, \dots, H_n\}
\]

### 3. Candidate experiment set
\[
\mathcal{E} = \{e_1, e_2, \dots, e_k\}
\]

### 4. Oracle experiment ranking or score
Each experiment gets a utility value indicating how discriminative it is.

### 5. Explanation label
A short explanation of why the best experiment is useful.

---

## 8. Oracle definition

The first version should **not** use a complicated Bayesian optimal-design framework.

Instead, define a simple operational oracle based on **predicted disagreement**.

### For each candidate experiment \(e\)
Under each hypothesis \(H_i\), simulate the predicted response:
\[
y_i^{(e)}(t)
\]

### Two-hypothesis utility
One simple oracle score is:
\[
U(e) = \frac{1}{T}\sum_{t=1}^{T} \frac{|y_1^{(e)}(t)-y_2^{(e)}(t)|}{\sigma+\epsilon}
\]

where:
- \(T\) is the number of time points
- \(\sigma\) is a normalization term, e.g. noise scale
- \(\epsilon\) prevents division by zero

### More than two hypotheses
For \(n>2\), use:
- average pairwise disagreement, or
- minimum pairwise disagreement

For example:
\[
U_{\text{avg}}(e)=\frac{2}{n(n-1)}\sum_{i<j}\frac{1}{T}\sum_t |y_i^{(e)}(t)-y_j^{(e)}(t)|
\]

### Why this oracle is enough
The contribution is **not** a new theory of optimal experiment design.

The contribution is:
- defining a clean scientific reasoning task
- giving it a stable, interpretable oracle
- studying whether LLMs understand this object

---

## 9. Task formulation

### Task 1: decide whether the current evidence is still unresolved
Input:
- current observations
- competing hypotheses

Output:
- whether the current evidence uniquely identifies a hypothesis

This is a useful supporting subtask.

### Task 2: choose the best next experiment
This is the **main task**.

Input:
- current observations
- competing hypotheses
- a discrete set of candidate experiments

Output:
- the best next experiment
- a short explanation

### Task 3: rank all candidate experiments
Optional secondary task:
- produce a ranking over all candidate experiments

---

## 10. What should *not* be done in version 1

The first version should avoid:
- free-form generation of experiments
- open-world experiment spaces
- real lab data
- too many scientific domains
- heavy finetuning
- complicated optimal-design theory

The first goal is:

> **define the task clearly and show strong failure signal**

---

## 11. Recommended benchmark scale

The intended benchmark can be intentionally small.

### Suggested first benchmark
- **2 system families**
- **20–40 mother scenarios per family**
- **6–10 candidate experiments per scenario**
- roughly **200–400 total instances**

This is enough if:
- the task is clean
- the oracle is stable
- the error mode is interpretable
- methods show meaningful gains

---

## 12. Baseline design

### Baseline 1: random choice
Pick an experiment uniformly at random.

### Baseline 2: simple heuristic
Use fixed rules like:
- always extend the time window
- always measure more variables
- always increase resolution

### Baseline 3: plain prompting
Give the model:
- observations
- candidate hypotheses
- candidate experiments

and ask it to choose the best next experiment.

### Baseline 4: hypothesis-contrast prompting
Require the model to:
1. state what parts of the current observations are explained by multiple hypotheses
2. state what differences each candidate experiment would amplify
3. choose the **minimal discriminating experiment**

This is a stronger no-training baseline.

---

## 13. Proposed methods

Three method candidates were proposed.

# Method candidate A: Disagreement-aware reranking

## Core idea
Do **not** trust the LLM’s final choice directly.

Instead:
1. ask the LLM to score or rank experiments
2. compute a few **cheap physics-informed features**
3. rerank experiments using both sources

### Generic scoring form
\[
\text{FinalScore}(e)
=
\alpha \cdot \text{LLMScore}(e)
+
\beta \cdot \text{Spread}(e)
+
\gamma \cdot \text{Sensitivity}(e)
+
\delta \cdot \text{AmbiguityShift}(e)
\]

where:
- \(\text{LLMScore}(e)\): the model’s verbal or numeric preference
- \(\text{Spread}(e)\): predicted response disagreement under competing hypotheses
- \(\text{Sensitivity}(e)\): whether the experiment reveals mechanism-sensitive differences
- \(\text{AmbiguityShift}(e)\): whether the experiment directly addresses the current ambiguity source

---

## Feature 1: predicted response spread

For a candidate experiment \(e\), simulate predictions under different hypotheses:
\[
y_1^{(e)}(t), y_2^{(e)}(t), \dots
\]

Then compute a spread score.

### Two-hypothesis version
\[
\text{Spread}(e)=\frac{1}{T}\sum_t |y_1^{(e)}(t)-y_2^{(e)}(t)|
\]

### Intuition
- large spread: the experiment separates the hypotheses
- small spread: the experiment is unlikely to help

---

## Feature 2: observed sensitivity proxy

Spread asks whether predictions are far apart.

Sensitivity asks whether the experiment perturbs the **right mechanism**.

Use a summary statistic \(\phi\) that is physically meaningful, such as:
- peak decay rate
- phase lag
- zero-crossing interval
- overshoot magnitude

Then define:
\[
\text{Sensitivity}(e)=|\phi(y_1^{(e)})-\phi(y_2^{(e)})|
\]

### Intuition
- spread measures raw output separation
- sensitivity measures whether separation appears in a mechanism-relevant observable

---

## Feature 3: ambiguity shift

### Why this feature was proposed
Current indistinguishability often has a dominant **source of ambiguity**, such as:
- short-window ambiguity
- low-resolution ambiguity
- hidden-variable ambiguity
- weak-excitation ambiguity

The first version does **not** need to learn this source with a latent variable model.

Instead, simply **define ambiguity types manually**.

### Example ambiguity types
- **short-window ambiguity**: the observation window is too short
- **low-resolution ambiguity**: the sampling is too coarse
- **hidden-variable ambiguity**: the wrong variable is being observed
- **weak-excitation ambiguity**: the system is not driven into a revealing regime

### Experiment tags
For each candidate experiment, annotate whether it addresses each ambiguity type.

For example:

| Experiment | short-window | low-resolution | hidden-variable | weak-excitation |
|---|---:|---:|---:|---:|
| extend observation window | 1 | 0 | 0 | 0 |
| increase sampling rate | 0 | 1 | 0 | 0 |
| observe velocity/current | 0 | 0 | 1 | 0 |
| increase initial velocity / drive | 0 | 0 | 0 | 1 |

### Binary ambiguity-shift score
If the current sample has a known ambiguity type, define:
\[
\text{AmbiguityShift}(e)=\mathbf{1}[\text{experiment addresses current ambiguity type}]
\]

### Interpretation
- \(1\): the experiment directly targets the current ambiguity source
- \(0\): it does not

This already gives a useful “is this experiment actually on target?” feature.

---

## Why method A may work
It combines:
- the LLM’s high-level semantic reasoning
- cheap structure-aware physics signals

So it directly corrects a typical LLM weakness:

> the model can sound scientifically plausible, yet still choose a poor discriminating experiment.

---

## Main caveat for method A
The reranking features must remain **cheap** and **coarse**.

If they become too strong, a reviewer may say:
- the method is just leaking the oracle
- the simulator already solved the task

So the features should not be identical to the full oracle.

---

# Method candidate B: Hypothesis contrast prompting

## Core idea
Do not let the model directly choose an experiment.

Instead, structure the prompt so that the model must:
1. identify what aspects of the observations are currently explained by multiple hypotheses
2. explain what differences each candidate experiment would amplify
3. choose the minimal discriminating experiment

### Why this may help
Plain prompting often causes two failure modes.

#### Failure mode 1: premature commitment
The model decides too early that one hypothesis is true and then chooses an experiment that merely supports that hypothesis.

#### Failure mode 2: generic safe experiment choice
The model picks vague experiments like:
- measure more data
- observe longer
- collect another sample

These may sound reasonable but are often not the **most discriminative**.

Hypothesis contrast prompting forces the model to think in terms of:
- shared explanatory regions
- unresolved mechanism differences
- experiments that amplify those differences

### Role in the project
This is a strong **zero-training baseline**.

By itself, it may look like prompt engineering, so it is safer as:
- a strong baseline
- or the reasoning front-end of a stronger hybrid method

---

# Method candidate C: Tiny verifier

## Core idea
Instead of generating the best experiment directly, train a very small classifier or scorer to estimate the usefulness of each candidate experiment.

### Input features can be very small
Examples:
- current ambiguity type
- candidate experiment metadata
- simple observed statistics
- hypothesis-pair type

### Output
A usefulness score, for example:
\[
\text{VerifierScore}(e) \in [0,1]
\]
or a binary label:
\[
\text{Useful}(e)\in\{0,1\}
\]

### Tiny model examples
- logistic regression
- XGBoost
- small MLP

This may not need a GPU at all.

### Why it may work
The task is highly structured.

If ambiguity type and experiment type have stable relations, a tiny verifier can learn patterns like:
- short-window ambiguity \(\rightarrow\) extending horizon helps
- hidden-variable ambiguity \(\rightarrow\) measuring a new channel helps
- weak-excitation ambiguity \(\rightarrow\) stronger excitation helps

### Best use of method C
It is likely strongest as a component in a **hybrid system**, not necessarily as the only method.

---

## 14. Relationship between the three methods

### Method B
Acts as a **reasoning scaffold**.

### Method C
Acts as a **structured usefulness scorer**.

### Method A
Acts as the main **hybrid reranking framework**.

### Most recommended combinations
#### Recommended combination 1
**B + A**
- use contrast prompting for better LLM reasoning
- then use disagreement-aware reranking

#### Recommended combination 2
**B + C**
- use contrast prompting for explanation
- use the tiny verifier for structured scoring

#### Full combination
**B + A + C**
- B gives interpretable reasoning
- A adds physics-informed features
- C adds learned structure-aware scoring

For version 1, there is no need to implement all three.

---

## 15. Training recommendation

### Initial recommendation
**Do not train at first.**

The first objective is not:
- “can I finetune a stronger model?”

The first objective is:
- “does the benchmark show a stable and interesting failure mode?”

### Suggested project phases

#### Phase 1: pure evaluation, no training
Goal:
- test whether the task has signal
- measure how frontier models fail
- produce an error taxonomy

Use:
- local open models
- one strong API model if available
- plain prompting
- hypothesis-contrast prompting

#### Phase 2: lightweight test-time method
Goal:
- see whether small structure-aware interventions help

Use:
- disagreement-aware reranking
- possibly a tiny verifier
- no heavy finetuning

#### Phase 3: train only if needed
Only after:
- the benchmark is stable
- the failure modes are sharp
- lightweight methods have reached their limit

Then consider training a small reranker or verifier.

---

## 16. Should the LLM get access to a simulator?

### Short answer
Yes, but **in layers**.

The recommendation was:

> **do not start with full simulator access**

because otherwise the project can become:
- a tool-use paper
- a simulator-oracle pipeline
- no longer a clean test of scientific reasoning

### Three recommended settings

#### Setting 1: no simulator access
Input:
- current observations
- competing hypotheses
- candidate experiments

Goal:
- test raw scientific reasoning ability

This should be the **main benchmark setting**.

#### Setting 2: cheap feature-level simulator access
The model does not directly query a full simulator.

Instead it gets:
- spread
- sensitivity
- ambiguity-shift
- other small structured summaries

Goal:
- test whether a little structure-aware scientific information helps

This is the preferred method setting.

#### Setting 3: full simulator access
The model can inspect simulated candidate responses.

Goal:
- treat this as an upper bound or analysis condition
- measure whether the issue is only lack of tools, or deeper reasoning

### Recommended scientific-method hierarchy
- main conclusion: **no simulator**
- method highlight: **cheap structured simulator-derived features**
- upper bound / analysis: **full simulator access**

---

## 17. Recommended experiment matrix

A natural experiment matrix is:

| Method | No simulator | Cheap features | Full simulator |
|---|---:|---:|---:|
| Plain prompt | ✓ |  |  |
| Hypothesis-contrast prompt | ✓ |  |  |
| Reranking with spread/sensitivity/ambiguity-shift |  | ✓ |  |
| LLM with full simulator summaries |  |  | ✓ |

This lets the paper answer three questions:
1. how good is the raw reasoning ability?
2. how much do a few structured scientific features help?
3. even with full tools, does the model still fail to reason correctly?

---

## 18. Core paper message

The motivation should be capability-centered, not product-centered.

### Recommended main motivation
The paper should say:

> We study a neglected dimension of LLM scientific reasoning: selecting minimal discriminating experiments under competing hypotheses.

### Not recommended as the main claim
Avoid centering the paper on:

> We built a useful LLM physicist / experimental scientist.

That can still appear as:
- long-term motivation
- broader impact
- future work

but not as the main scientific claim.

---

## 19. What counts as minimum success

The project is worth continuing if the first benchmark shows all of the following:

### 1. Strong models are far from solved
Top-1 experiment-selection accuracy should be meaningfully below ceiling.

### 2. Models often recognize uncertainty but still choose poor experiments
This would show that the failure is not only confidence calibration, but also experiment reasoning.

### 3. Errors form a clean taxonomy
Examples:
- overusing “extend the time window”
- failing to identify the right observation variable
- not recognizing weak-excitation ambiguity

### 4. A lightweight method improves performance
A simple reranker or verifier should give clear gains.

If these four hold, the project has real potential.

---

## 20. One-week prototype recommendation

Before building the whole benchmark, a smoke test should be done.

### 48-hour / one-week prototype
Use only the damped-oscillator family:
1. define 2 competing hypotheses
2. define 6 candidate experiments
3. manually build 10–20 examples
4. run 2–3 models
5. inspect whether they systematically choose poor experiments

### Goal of the smoke test
Not to get final results, but to answer:
- does this task have signal?
- do models fail in stable, interpretable ways?
- is the oracle sensible?

If not, the project should be revised early.

---

## 21. Summary of the strongest current recommendation

### Main research direction
**Minimal Discriminating Experiment for Scientific Hypotheses**

### Best initial benchmark style
- small
- synthetic / semi-synthetic
- controlled
- discrete candidate experiment set
- one or two physics families

### Best initial methodology
1. no-training baselines
2. hypothesis-contrast prompting
3. disagreement-aware reranking with cheap structured features
4. optional tiny verifier

### Best main paper framing
The paper should be about:

> **LLM scientific reasoning ability under competing hypotheses**

with “AI scientist” positioned only as a longer-term motivation.

