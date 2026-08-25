from services.detector.schemas import IncidentEvidencePacket

from .models import *
from .policy import DecisionPolicy, choose


class CounterfactualEngine:
    def __init__(
        self,
        risk_threshold: float = 0.65,
        policy: DecisionPolicy = DecisionPolicy.MAXIMIZE_RECOVERY_UNDER_RISK_LIMIT,
    ):
        self.risk_threshold = risk_threshold
        self.policy = policy

    def run(
        self,
        packet: IncidentEvidencePacket,
        incident_id: str = "incident",
        observation_minutes: int = 60,
    ) -> CounterfactualResult:
        baseline = max(
            packet.baseline_metrics.successful_value_minor,
            packet.observed_metrics.total_value_minor,
        )
        observed = packet.observed_metrics.successful_value_minor
        loss = max(0, baseline - observed)
        failed_value = packet.observed_metrics.failed_value_minor
        scenarios = [
            self._scenario(
                "none",
                Strategy.NO_ACTION,
                "Do nothing",
                0,
                failed_value,
                loss,
                0,
                0,
                observation_minutes,
            ),
            *(self._reroute(packet, loss, failed_value, observation_minutes)),
            self._retry(packet, loss, observation_minutes),
            self._target(packet, loss, observation_minutes),
        ]
        pareto = []
        for scenario in scenarios:
            value = scenario.impact.expected_recovered_revenue_minor
            scenario.estimate_range = EstimateRange(
                expected=value, lower=round(value * 0.85), upper=round(value * 1.15)
            )
            scenario.dominated = any(
                other.impact.expected_recovered_revenue_minor >= value
                and other.risk.score <= scenario.risk.score
                and other.scenario_id != scenario.scenario_id
                for other in scenarios
            )
            pareto.append(scenario.scenario_id) if not scenario.dominated else None
        best = choose(scenarios, self.policy, self.risk_threshold)
        return CounterfactualResult(
            incident_id=incident_id,
            scenarios=scenarios,
            recommended_scenario_id=best.scenario_id,
            recommendation_reason=f"Selected highest expected recovered revenue under {self.policy.value} and risk threshold {self.risk_threshold:.0%}.",
            pareto_scenario_ids=pareto,
            decision_policy=self.policy.value,
            audit_trace=[
                {
                    "stage": "counterfactual_simulation",
                    "ground_truth_used": False,
                    "scenario_count": len(scenarios),
                }
            ],
        )

    def _reroute(self, packet, loss, failed_value, minutes):
        return [
            self._scenario(
                f"reroute_{int(share * 100)}",
                Strategy.REROUTE_TRAFFIC,
                f"Reroute {int(share * 100)}%",
                share,
                failed_value,
                loss,
                round(failed_value * share * 0.82),
                round(packet.observed_metrics.transaction_count * share),
                minutes,
            )
            for share in (0.25, 0.5, 0.75, 1.0)
        ]

    def _retry(self, packet, loss, minutes):
        return self._scenario(
            "retry_eligible",
            Strategy.RETRY_ELIGIBLE_FAILURES,
            "Retry eligible failures",
            0,
            packet.observed_metrics.failed_value_minor,
            loss,
            round(packet.observed_metrics.failed_value_minor * 0.35),
            round(packet.observed_metrics.failure_count * 0.5),
            minutes,
            extra=[
                RecoveryAssumption(name="eligible_failure_share", value=0.5),
                RecoveryAssumption(name="retry_success_rate", value=0.35),
            ],
        )

    def _target(self, packet, loss, minutes):
        cohort = packet.top_cohorts or packet.affected_cohorts
        share = min(0.5, sum(c.economic_contribution for c in cohort[:2])) if cohort else 0.25
        return self._scenario(
            "targeted_cohort",
            Strategy.TARGETED_RECOVERY,
            "Targeted affected cohort",
            0,
            packet.observed_metrics.failed_value_minor,
            loss,
            round(packet.observed_metrics.failed_value_minor * share * 0.45),
            round(packet.observed_metrics.failure_count * share),
            minutes,
            extra=[
                RecoveryAssumption(name="target_cohort_share", value=share),
                RecoveryAssumption(name="targeted_recovery_rate", value=0.45),
            ],
        )

    def _scenario(
        self,
        sid,
        strategy,
        label,
        shift,
        failed_value,
        loss,
        recovered,
        volume,
        minutes,
        extra=None,
    ):
        risk_score = min(
            1, 0.1 + shift * 0.8 + (0.2 if strategy == Strategy.RETRY_ELIGIBLE_FAILURES else 0)
        )
        level = (
            RiskLevel.HIGH
            if risk_score >= 0.65
            else RiskLevel.MEDIUM
            if risk_score >= 0.35
            else RiskLevel.LOW
        )
        assumptions = [
            RecoveryAssumption(name="observation_minutes", value=minutes),
            RecoveryAssumption(name="traffic_shift", value=shift),
            *(extra or []),
        ]
        impact = EconomicImpact(
            incident_revenue_loss_minor=loss,
            counterfactual_revenue_loss_minor=max(0, loss - recovered),
            expected_recovered_revenue_minor=recovered,
            recovery_rate=recovered / loss if loss else 0,
            residual_loss_minor=max(0, loss - recovered),
            incremental_successes=round(volume * 0.35),
            intervention_volume=volume,
        )
        return CounterfactualScenario(
            scenario_id=sid,
            strategy=strategy,
            label=label,
            assumptions=assumptions,
            impact=impact,
            risk=RiskAssessment(
                level=level,
                score=risk_score,
                explanation="Transparent deterministic risk from traffic shift and intervention uncertainty.",
            ),
        )
