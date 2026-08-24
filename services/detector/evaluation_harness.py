"""Phase 2.3 evaluation code. Ground truth is accessed only in this module."""

from dataclasses import dataclass
from time import perf_counter

from services.simulator.config import SCENARIOS
from services.simulator.domain import IncidentType
from services.simulator.generator import Simulator

from .detector import IncidentDetector
from .schemas import ObservableInput


@dataclass
class ScenarioMeasurement:
    scenario: str
    detected: bool
    state: str
    top_cohort: str | None
    delay_minutes: float | None
    window_iou: float | None
    revenue_risk_error_pct: float | None


def observable(result) -> ObservableInput:
    return ObservableInput(
        payments=[p.model_dump(mode="json") for p in result.payments],
        events=[e.model_dump(mode="json") for e in result.events],
    )


def interval_iou(predicted: dict, actual) -> float | None:
    if not actual or not predicted.get("confirmed_start"):
        return None
    ps, pe = predicted["confirmed_start"], predicted.get("confirmed_end") or predicted.get("end")
    as_, ae = actual.start_time, actual.end_time
    if not ps or not pe:
        return None
    intersection = max(0, (min(pe, ae) - max(ps, as_)).total_seconds())
    union = max(0, (max(pe, ae) - min(ps, as_)).total_seconds())
    return intersection / union if union else 0


def evaluate_scenario(
    scenario: IncidentType, seed: int = 42, payments: int = 10000
) -> ScenarioMeasurement:
    result = Simulator(seed).generate(payments, scenario=SCENARIOS[scenario])
    packet = IncidentDetector().detect(observable(result))
    truth = result.ground_truth[0] if result.ground_truth else None
    top = (
        packet.top_cohorts[0]
        if packet.top_cohorts
        else (packet.affected_cohorts[0] if packet.affected_cohorts else None)
    )
    actual_risk = truth.revenue_exposure_minor if truth else None
    predicted = packet.revenue_impact.revenue_at_risk_minor
    error = abs(predicted - actual_risk) / actual_risk * 100 if actual_risk else None
    delay = (
        (packet.incident_window.get("confirmed_start") - truth.start_time).total_seconds() / 60
        if truth and packet.incident_window.get("confirmed_start")
        else None
    )
    return ScenarioMeasurement(
        scenario.value,
        packet.incident_detected,
        packet.state.value,
        f"{top.dimension}={top.value}" if top else None,
        delay,
        interval_iou(packet.incident_window, truth),
        error,
    )


def evaluate_clean_baselines(seeds=(1, 2, 3, 4, 5), payments=10000) -> dict:
    rows = []
    for seed in seeds:
        result = Simulator(seed).generate(payments)
        packet = IncidentDetector().detect(observable(result))
        rows.append(
            {
                "seed": seed,
                "state": packet.state.value,
                "confirmed_incident": packet.incident_detected,
                "confidence": packet.confidence,
            }
        )
    return {
        "runs": rows,
        "confirmed_incidents": sum(r["confirmed_incident"] for r in rows),
        "false_positive_rate": sum(r["confirmed_incident"] for r in rows) / len(rows),
    }


def benchmark(seed=42, payments=100000) -> dict:
    t0 = perf_counter()
    result = Simulator(seed).generate(payments)
    loaded = perf_counter()
    inp = observable(result)
    observed = perf_counter()
    packet = IncidentDetector().detect(inp)
    detected = perf_counter()
    return {
        "events": len(inp.events),
        "generation_seconds": loaded - t0,
        "input_seconds": observed - loaded,
        "detection_seconds": detected - observed,
        "total_seconds": detected - t0,
        "events_per_second": len(inp.events) / (detected - t0),
        "state": packet.state.value,
    }


def run_matrix() -> dict:
    scenarios = [
        IncidentType.ISSUER_DEGRADATION,
        IncidentType.GATEWAY_DEGRADATION,
        IncidentType.PAYMENT_METHOD_DEGRADATION,
        IncidentType.MERCHANT_DEGRADATION,
        IncidentType.CHECKOUT_ABANDONMENT,
        IncidentType.SUBSCRIPTION_RENEWAL,
    ]
    return {
        "clean": evaluate_clean_baselines(),
        "scenarios": [evaluate_scenario(s) for s in scenarios],
    }
