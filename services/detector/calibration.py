"""Phase 2.9 calibration harness; expected cohorts are evaluator-only assertions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from services.simulator.config import ScenarioConfig
from services.simulator.domain import IncidentType, Issuer
from services.simulator.generator import Simulator
from services.simulator.history import generate_history

from .evaluation_harness import observable
from .sequential import SequentialShadowEvaluator


@dataclass
class CalibrationResult:
    severity: str
    incident_success: float
    detected: bool
    top_cohort: str | None
    delay_minutes: float | None
    hdfc_sample: int
    hdfc_success: float
    hdfc_card_sample: int
    hdfc_card_success: float
    affected_share: float = 0
    interaction_sample: int = 0
    interaction_success: float = 0
    baseline_success: float = 0
    revenue_exposure: int = 0
    incident_start: object | None = None
    incident_end: object | None = None
    eligible_events: int = 0
    affected_events: int = 0
    target_share: float = 0
    target_success: float = 0


SEVERITIES = {"65%": 0.65, "70%": 0.70, "75%": 0.75, "80%": 0.80, "85%": 0.85}


def canonical_world(seed: int, incident_success: float | None, daily_payments: int = 2000):
    history = generate_history(7, seed, daily_payments)
    start = max(p.timestamp for p in history.payments)
    day = datetime(start.year, start.month, start.day, tzinfo=UTC) + timedelta(days=1)
    incident_start = day + timedelta(hours=12)
    scenario = (
        ScenarioConfig(
            incident_type=IncidentType.ISSUER_DEGRADATION,
            target=Issuer.HDFC,
            incident_success_rate=incident_success or 0.94,
            target_success_rate=incident_success,
            incident_start=incident_start,
            incident_end=incident_start + timedelta(minutes=20),
            affected_share=0.40,
            affected_dimensions={"issuer": "hdfc"},
            target_interaction={"issuer": "hdfc", "payment_method": "card"},
            minimum_affected_events=8,
            minimum_interaction_events=8,
        )
        if incident_success
        else None
    )
    evaluation = Simulator(seed + 7).generate(
        daily_payments, start=day, end=day + timedelta(days=1), scenario=scenario
    )
    return history, evaluation


def run_calibration(severity: str, seed: int = 42, daily_payments: int = 2000) -> CalibrationResult:
    history, evaluation = canonical_world(seed, SEVERITIES[severity], daily_payments)
    shadow = SequentialShadowEvaluator(5)
    observations = shadow.run(observable(history), observable(evaluation))
    incidents = [o for o in observations if o.state == "incident"]
    top = incidents[0].trace.top_affected_cohort if incidents else None
    ids = set(
        evaluation.ground_truth[0].calibration_affected_payment_ids
        if evaluation.ground_truth
        else []
    )
    affected = [p for p in evaluation.payments if p.payment_id in ids]
    hdfc = [p for p in affected if p.issuer == Issuer.HDFC]
    hdfc_card = [
        p for p in affected if p.issuer == Issuer.HDFC and p.payment_method.value == "card"
    ]
    eligible = [
        p
        for p in evaluation.payments
        if evaluation.ground_truth
        and evaluation.ground_truth[0].start_time
        <= p.timestamp
        <= evaluation.ground_truth[0].end_time
    ]
    baseline = [
        p for p in history.payments if p.issuer == Issuer.HDFC and p.payment_method.value == "card"
    ]
    truth = evaluation.ground_truth[0]
    return CalibrationResult(
        severity,
        SEVERITIES[severity],
        bool(incidents),
        top,
        None,
        len(hdfc),
        sum(p.status.value == "success" for p in hdfc) / len(hdfc) if hdfc else 0,
        len(hdfc_card),
        sum(p.status.value == "success" for p in hdfc_card) / len(hdfc_card) if hdfc_card else 0,
        len(affected) / len(eligible) if eligible else 0,
        len(hdfc_card),
        sum(p.status.value == "success" for p in hdfc_card) / len(hdfc_card) if hdfc_card else 0,
        sum(p.status.value == "success" for p in baseline) / len(baseline),
        evaluation.ground_truth[0].revenue_exposure_minor if evaluation.ground_truth else 0,
        truth.start_time,
        truth.end_time,
        len(eligible),
        len(affected),
        0.4,
        SEVERITIES[severity],
    )
