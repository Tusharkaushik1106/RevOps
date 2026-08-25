from enum import StrEnum

from .models import CounterfactualScenario


class DecisionPolicy(StrEnum):
    MAXIMIZE_RECOVERY_UNDER_RISK_LIMIT = "maximize_recovery_under_risk_limit"
    MAXIMIZE_RECOVERY_PER_RISK = "maximize_recovery_per_unit_risk"
    BALANCED = "balanced_recovery_risk"


def choose(scenarios: list[CounterfactualScenario], policy: DecisionPolicy, risk_limit: float):
    eligible = [s for s in scenarios if s.risk and s.risk.score <= risk_limit]
    if not eligible:
        return scenarios[0]
    if policy == DecisionPolicy.MAXIMIZE_RECOVERY_PER_RISK:
        return max(
            eligible,
            key=lambda s: s.impact.expected_recovered_revenue_minor / max(0.01, s.risk.score),
        )
    if policy == DecisionPolicy.BALANCED:
        return max(
            eligible, key=lambda s: s.impact.expected_recovered_revenue_minor * (1 - s.risk.score)
        )
    return max(eligible, key=lambda s: s.impact.expected_recovered_revenue_minor)
