import pytest
from pydantic import ValidationError

from services.detector.schemas import IncidentEvidencePacket, MetricSnapshot
from services.recovery.engine import CounterfactualEngine
from services.recovery.explanation import LLMExplanation, decision_payload, validate_explanation


def payload():
    result = CounterfactualEngine().run(
        IncidentEvidencePacket(
            incident_detected=True,
            state="incident",
            confidence=0.8,
            baseline_metrics=MetricSnapshot(successful_value_minor=94000, total_value_minor=100000),
            observed_metrics=MetricSnapshot(
                successful_value_minor=80000, total_value_minor=100000, failed_value_minor=20000
            ),
        )
    )
    scenario = next(s for s in result.scenarios if s.scenario_id == result.recommended_scenario_id)
    return decision_payload(result, scenario)


def test_valid_explanation():
    p = payload()
    text = f"{p.selected_strategy} is recommended with expected recovery {p.expected_recovery}, residual loss {p.residual_loss}, risk {p.risk.value}, and traffic shift {int(p.traffic_shift * 100)}%."
    assert validate_explanation(p, LLMExplanation(summary=text, reasoning=text)).valid


def test_wrong_recovery_and_fabrication_rejected():
    p = payload()
    result = validate_explanation(
        p, LLMExplanation(summary=f"{p.selected_strategy} recovers 999999", reasoning="risk low")
    )
    assert not result.valid and result.errors


def test_payload_is_deterministic_and_frozen():
    p = payload()
    assert p == payload()
    with pytest.raises(ValidationError):
        p.expected_recovery = 1
