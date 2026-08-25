from services.detector.schemas import IncidentEvidencePacket, MetricSnapshot
from services.recovery.engine import CounterfactualEngine
from services.recovery.models import Strategy


def packet():
    return IncidentEvidencePacket(
        incident_detected=True,
        state="incident",
        confidence=0.8,
        baseline_metrics=MetricSnapshot(
            transaction_count=100,
            success_count=94,
            failure_count=6,
            total_value_minor=100000,
            successful_value_minor=94000,
            failed_value_minor=6000,
        ),
        observed_metrics=MetricSnapshot(
            transaction_count=100,
            success_count=80,
            failure_count=20,
            total_value_minor=100000,
            successful_value_minor=80000,
            failed_value_minor=20000,
        ),
    )


def test_no_action_and_sweep():
    result = CounterfactualEngine().run(packet())
    assert (
        result.scenarios[0].strategy == Strategy.NO_ACTION
        and len([s for s in result.scenarios if s.strategy == Strategy.REROUTE_TRAFFIC]) == 4
    )


def test_economics_and_optimization():
    result = CounterfactualEngine().run(packet())
    assert all(s.impact.expected_recovered_revenue_minor >= 0 for s in result.scenarios)
    assert result.recommended_scenario_id


def test_deterministic_and_risk():
    assert (
        CounterfactualEngine().run(packet()).model_dump()
        == CounterfactualEngine().run(packet()).model_dump()
    )
