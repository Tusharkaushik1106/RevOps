import re

from pydantic import BaseModel, ConfigDict, Field

from .models import CounterfactualResult, CounterfactualScenario, RiskLevel


class DecisionPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    incident_id: str
    selected_strategy: str
    expected_recovery: int
    lower_estimate: int
    upper_estimate: int
    residual_loss: int
    risk: RiskLevel
    risk_threshold: float
    traffic_shift: float
    scenario_id: str
    evidence_ids: tuple[str, ...] = ()
    assumptions: tuple[dict, ...] = ()
    decision_policy: str


class LLMExplanation(BaseModel):
    summary: str
    reasoning: str
    tradeoffs: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    assumption_explanation: str = ""


class ValidatedExplanation(BaseModel):
    valid: bool
    explanation: LLMExplanation
    errors: list[str] = Field(default_factory=list)


def decision_payload(
    result: CounterfactualResult,
    scenario: CounterfactualScenario,
    evidence_ids: list[str] | None = None,
) -> DecisionPayload:
    estimate = scenario.estimate_range
    shift = next((a.value for a in scenario.assumptions if a.name == "traffic_shift"), 0)
    return DecisionPayload(
        incident_id=result.incident_id,
        selected_strategy=scenario.label,
        expected_recovery=scenario.impact.expected_recovered_revenue_minor,
        lower_estimate=estimate.lower
        if estimate
        else scenario.impact.expected_recovered_revenue_minor,
        upper_estimate=estimate.upper
        if estimate
        else scenario.impact.expected_recovered_revenue_minor,
        residual_loss=scenario.impact.residual_loss_minor,
        risk=scenario.risk.level,
        risk_threshold=0.65,
        traffic_shift=float(shift),
        scenario_id=scenario.scenario_id,
        evidence_ids=tuple(evidence_ids or []),
        assumptions=tuple(a.model_dump() for a in scenario.assumptions),
        decision_policy=result.decision_policy,
    )


def validate_explanation(
    payload: DecisionPayload, explanation: LLMExplanation
) -> ValidatedExplanation:
    errors = []
    text = f"{explanation.summary} {explanation.reasoning} {' '.join(explanation.tradeoffs)} {' '.join(explanation.uncertainties)} {explanation.assumption_explanation}"
    if (
        payload.selected_strategy.lower() not in text.lower()
        and payload.scenario_id.lower() not in text.lower()
    ):
        errors.append("selected strategy is not identified")
    expected_tokens = {
        str(payload.expected_recovery),
        str(payload.lower_estimate),
        str(payload.upper_estimate),
        str(payload.residual_loss),
        payload.risk.value,
        str(int(payload.traffic_shift * 100)),
        str(int(payload.risk_threshold * 100)),
    }
    mentioned = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    for token in mentioned:
        if token not in expected_tokens and token not in {
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        }:
            errors.append(f"unsupported numerical claim: {token}")
    if str(payload.expected_recovery) not in text:
        errors.append("expected recovery is missing")
    return ValidatedExplanation(valid=not errors, explanation=explanation, errors=errors)
