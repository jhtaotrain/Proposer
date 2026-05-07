from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Domain(str, Enum):
    DAMPED_OSCILLATOR = "damped_oscillator"
    CIRCUIT = "circuit"
    CUSTOM = "custom"


class GoalType(str, Enum):
    IDENTIFY_MECHANISM = "identify_mechanism"
    ESTIMATE_PARAMETERS = "estimate_parameters"
    DISTINGUISH_HYPOTHESES = "distinguish_hypotheses"
    OPTIMIZE_OUTCOME = "optimize_outcome"
    CUSTOM = "custom"


class HypothesisFamily(str, Enum):
    ODE = "ode"
    DISCRETE_DYNAMICS = "discrete_dynamics"
    CIRCUIT = "circuit"
    PROBABILISTIC = "probabilistic"
    EMPIRICAL_BLACK_BOX = "empirical_black_box"
    CUSTOM = "custom"


class EquationType(str, Enum):
    SYMBOLIC_ODE = "symbolic_ode"
    SYMBOLIC_ALGEBRAIC = "symbolic_algebraic"
    CUSTOM = "custom"


class NoiseModelType(str, Enum):
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    NONE = "none"
    CUSTOM = "custom"


class InterventionType(str, Enum):
    MEASUREMENT_CHANGE = "measurement_change"
    INITIAL_CONDITION_CHANGE = "initial_condition_change"
    INPUT_CHANGE = "input_change"
    MULTI_FACTOR = "multi_factor"
    CUSTOM = "custom"


class AmbiguityType(str, Enum):
    SHORT_WINDOW = "short_window"
    LOW_RESOLUTION = "low_resolution"
    HIDDEN_VARIABLE = "hidden_variable"
    WEAK_EXCITATION = "weak_excitation"
    PARAMETER_DEGENERACY = "parameter_degeneracy"
    NONE = "none"
    CUSTOM = "custom"


class FitScoreType(str, Enum):
    MSE = "mse"
    NLL = "nll"
    MAE = "mae"
    CUSTOM = "custom"


class UtilityScoreType(str, Enum):
    PREDICTED_DISAGREEMENT = "predicted_disagreement"
    PAIRWISE_AVERAGE_DISAGREEMENT = "pairwise_average_disagreement"
    MIN_PAIRWISE_DISAGREEMENT = "min_pairwise_disagreement"
    CUSTOM = "custom"


class Goal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: GoalType
    description: str
    success_criterion: str | None = None


class NoiseModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: NoiseModelType
    std: float | None = Field(default=None, ge=0.0)
    parameters: dict[str, Any] = Field(default_factory=dict)


class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: float
    end: float

    @model_validator(mode="after")
    def validate_window(self) -> "TimeWindow":
        if self.end <= self.start:
            raise ValueError("time window end must be greater than start")
        return self


class ObservationEpisode(BaseModel):
    model_config = ConfigDict(extra="allow")

    episode_id: str
    condition_id: str
    measured_channels: list[str] = Field(min_length=1)
    time: list[float] = Field(min_length=1)
    values: dict[str, list[float]]
    noise_model: NoiseModel | None = None
    summary_stats: dict[str, float | int | str | bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_channels(self) -> "ObservationEpisode":
        time_len = len(self.time)
        missing = [channel for channel in self.measured_channels if channel not in self.values]
        if missing:
            raise ValueError(f"missing value arrays for measured channels: {missing}")

        extra = [channel for channel in self.values if channel not in self.measured_channels]
        if extra:
            raise ValueError(f"values provided for channels not listed in measured_channels: {extra}")

        bad_lengths = [
            channel for channel, series in self.values.items() if len(series) != time_len
        ]
        if bad_lengths:
            raise ValueError(
                "all value arrays must match time length; mismatched channels: "
                f"{bad_lengths}"
            )

        return self


class Observability(BaseModel):
    model_config = ConfigDict(extra="allow")

    available_channels: list[str] = Field(default_factory=list)
    hidden_channels: list[str] = Field(default_factory=list)
    notes: str | None = None


class Observations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episodes: list[ObservationEpisode] = Field(min_length=1)
    observability: Observability | None = None


class EquationModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: EquationType
    state_order: list[str] = Field(default_factory=list)
    rhs: list[str] = Field(default_factory=list)
    expression: str | None = None


class HypothesisModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    state_variables: list[str] = Field(default_factory=list)
    observed_variables: list[str] = Field(default_factory=list)
    parameters: dict[str, float | int | str | bool] = Field(default_factory=dict)
    equations: EquationModel | None = None
    simulator_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FitToCurrentData(BaseModel):
    model_config = ConfigDict(extra="allow")

    score: float
    score_type: FitScoreType
    details: dict[str, Any] = Field(default_factory=dict)


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    name: str
    description: str
    family: HypothesisFamily
    mechanism_tags: list[str] = Field(default_factory=list)
    model: HypothesisModel
    fit_to_current_data: FitToCurrentData | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeasurementPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    channels: list[str] = Field(default_factory=list)
    sampling_rate: float | None = Field(default=None, gt=0.0)
    time_window: TimeWindow | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateExperiment(BaseModel):
    model_config = ConfigDict(extra="allow")

    experiment_id: str
    name: str
    description: str
    intervention_type: InterventionType
    changes: dict[str, Any] = Field(default_factory=dict)
    measurement_plan: MeasurementPlan | None = None
    ambiguity_tags: list[AmbiguityType] = Field(default_factory=list)
    cost: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AmbiguityCriterion(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    threshold: float | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AmbiguityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_ambiguous: bool
    compatible_hypotheses: list[str] = Field(default_factory=list)
    rejected_hypotheses: list[str] = Field(default_factory=list)
    ambiguity_type: AmbiguityType = AmbiguityType.NONE
    criterion: AmbiguityCriterion
    explanation: str | None = None


class OracleLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    true_hypothesis_id: str | None = None
    best_experiment_id: str | None = None
    experiment_utilities: dict[str, float] = Field(default_factory=dict)
    utility_score_type: UtilityScoreType | None = None
    explanation: str | None = None


class ScenarioMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    generator: str | None = None
    seed: int | None = None
    difficulty: str | None = None
    source: str | None = None
    notes: str | None = None


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    scenario_id: str
    domain: Domain
    goal: Goal
    observations: Observations
    hypotheses: list[Hypothesis] = Field(min_length=1)
    candidate_experiments: list[CandidateExperiment] = Field(min_length=1)
    ambiguity_assessment: AmbiguityAssessment | None = None
    ground_truth: OracleLabel | None = None
    metadata: ScenarioMetadata = Field(default_factory=ScenarioMetadata)

    @model_validator(mode="after")
    def validate_cross_references(self) -> "Scenario":
        hypothesis_ids = {hypothesis.hypothesis_id for hypothesis in self.hypotheses}
        if len(hypothesis_ids) != len(self.hypotheses):
            raise ValueError("hypothesis_id values must be unique")

        experiment_ids = {
            experiment.experiment_id for experiment in self.candidate_experiments
        }
        if len(experiment_ids) != len(self.candidate_experiments):
            raise ValueError("experiment_id values must be unique")

        if self.ambiguity_assessment is not None:
            unknown_compatible = [
                hypothesis_id
                for hypothesis_id in self.ambiguity_assessment.compatible_hypotheses
                if hypothesis_id not in hypothesis_ids
            ]
            if unknown_compatible:
                raise ValueError(
                    "ambiguity_assessment references unknown compatible hypotheses: "
                    f"{unknown_compatible}"
                )

            unknown_rejected = [
                hypothesis_id
                for hypothesis_id in self.ambiguity_assessment.rejected_hypotheses
                if hypothesis_id not in hypothesis_ids
            ]
            if unknown_rejected:
                raise ValueError(
                    "ambiguity_assessment references unknown rejected hypotheses: "
                    f"{unknown_rejected}"
                )

        if self.ground_truth is not None:
            if (
                self.ground_truth.true_hypothesis_id is not None
                and self.ground_truth.true_hypothesis_id not in hypothesis_ids
            ):
                raise ValueError("ground_truth.true_hypothesis_id references unknown hypothesis")

            if (
                self.ground_truth.best_experiment_id is not None
                and self.ground_truth.best_experiment_id not in experiment_ids
            ):
                raise ValueError("ground_truth.best_experiment_id references unknown experiment")

            unknown_utility_experiments = [
                experiment_id
                for experiment_id in self.ground_truth.experiment_utilities
                if experiment_id not in experiment_ids
            ]
            if unknown_utility_experiments:
                raise ValueError(
                    "ground_truth.experiment_utilities references unknown experiments: "
                    f"{unknown_utility_experiments}"
                )

        return self
