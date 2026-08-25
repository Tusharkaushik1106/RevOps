"""Single Phase 2 audit entry point. Truth is used only after observable evaluation."""

from services.simulator.domain import IncidentType
from services.simulator.history import generate_evaluation

from .calibration import run_calibration
from .evaluation_harness import evaluate_clean_baselines


def run_authoritative(seeds=(42, 43, 44, 45, 46), payments=2000):
    report = {"clean": evaluate_clean_baselines(seeds, payments), "canonical": [], "scenarios": []}
    for seed in seeds:
        result = run_calibration("65%", seed, payments)
        report["canonical"].append(result.__dict__)
    for scenario in (
        IncidentType.ISSUER_DEGRADATION,
        IncidentType.GATEWAY_DEGRADATION,
        IncidentType.PAYMENT_METHOD_DEGRADATION,
        IncidentType.MERCHANT_DEGRADATION,
        IncidentType.CHECKOUT_ABANDONMENT,
        IncidentType.SUBSCRIPTION_RENEWAL,
    ):
        world = generate_evaluation(7, seeds[0], scenario, payments)
        report["scenarios"].append(
            {
                "scenario": scenario.value,
                "evaluation_events": len(world.evaluation.events),
                "truth_available_to_evaluator": bool(world.hidden_truth),
            }
        )
    return report
