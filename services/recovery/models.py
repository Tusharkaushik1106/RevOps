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


class CounterfactualResult(BaseModel):
    incident_id: str
    scenarios: list[CounterfactualScenario]
    recommended_scenario_id: str | None = None
    recommendation_reason: str = ""
    audit_trace: list[dict] = Field(default_factory=list)
