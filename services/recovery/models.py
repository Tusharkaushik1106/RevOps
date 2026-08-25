from enum import StrEnum

from pydantic import BaseModel, Field


class Strategy(StrEnum):
    NO_ACTION = "no_action"
    REROUTE_TRAFFIC = "reroute_traffic"
    RETRY_ELIGIBLE_FAILURES = "retry_eligible_failures"
    TARGETED_RECOVERY = "targeted_recovery"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecoveryAssumption(BaseModel):
    name: str
    value: float | int | str
    source: str = "explicit_assumption"
    description: str = ""


class EvidenceProvenance(BaseModel):
    source: str
    sample_size: int = 0
    metric: str
    value: float | int
    confidence: str = "medium"
    comparable_dimensions: dict[str, str] = Field(default_factory=dict)


class EstimateRange(BaseModel):
    expected: int
    lower: int
    upper: int
    confidence: str = "heuristic"
    method: str = "deterministic interval around expected value"


class EconomicImpact(BaseModel):
    incident_revenue_loss_minor: int = 0
    counterfactual_revenue_loss_minor: int = 0
    expected_recovered_revenue_minor: int = 0
    recovery_rate: float = 0
    residual_loss_minor: int = 0
    incremental_successes: int = 0
    intervention_volume: int = 0


class RiskAssessment(BaseModel):
    level: RiskLevel
    score: float
    explanation: str


class CounterfactualScenario(BaseModel):
    scenario_id: str
    strategy: Strategy
    label: str
    assumptions: list[RecoveryAssumption] = Field(default_factory=list)
    impact: EconomicImpact = Field(default_factory=EconomicImpact)
    risk: RiskAssessment | None = None
    estimate_range: EstimateRange | None = None
    evidence_used: list[EvidenceProvenance] = Field(default_factory=list)
    dominated: bool = False


class CounterfactualResult(BaseModel):
    incident_id: str
    scenarios: list[CounterfactualScenario]
    recommended_scenario_id: str | None = None
    recommendation_reason: str = ""
    audit_trace: list[dict] = Field(default_factory=list)
    pareto_scenario_ids: list[str] = Field(default_factory=list)
    decision_policy: str = "maximize_recovery_under_risk_limit"
