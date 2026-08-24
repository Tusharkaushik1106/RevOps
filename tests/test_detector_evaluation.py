from services.detector.evaluation_harness import evaluate_clean_baselines, evaluate_scenario
from services.simulator.domain import IncidentType


def test_clean_baseline_matrix_is_measurable():
    report = evaluate_clean_baselines((1, 2, 3, 4, 5), 1000)
    assert len(report["runs"]) == 5


def test_scenario_measurement_is_deterministic():
    a = evaluate_scenario(IncidentType.ISSUER_DEGRADATION, 42, 1000)
    b = evaluate_scenario(IncidentType.ISSUER_DEGRADATION, 42, 1000)
    assert a == b
