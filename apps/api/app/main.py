from functools import lru_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.agents.graph import build_graph
from services.agents.provider import MockInvestigationProvider
from services.agents.state import InvestigationState
from services.detector.calibration import canonical_world
from services.detector.evaluation_harness import observable
from services.detector.pipeline import Aggregate
from services.detector.schemas import IncidentEvidencePacket, MetricSnapshot, RevenueImpact
from services.detector.sequential import SequentialShadowEvaluator
from services.recovery.engine import CounterfactualEngine
from services.recovery.explanation import LLMExplanation, decision_payload, validate_explanation

from .config import get_settings

settings = get_settings()
app = FastAPI(title="Revenue Incident Commander API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    phase: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", phase="0-foundation")


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {"service": "api", "status": "configured", "implementation": "foundation-only"}


@app.on_event("startup")
def warm_command_center() -> None:
    command_center()


@app.get("/api/v1/command-center")
@lru_cache(maxsize=1)
def command_center() -> dict:
    history, evaluation = canonical_world(42, 0.65, 10000)
    shadow = SequentialShadowEvaluator(5)
    observations = shadow.run(observable(history), observable(evaluation))
    confirmed = next((item for item in observations if item.state == "incident"), None)
    if not confirmed:
        return {
            "mode": "SIMULATION",
            "status": "NO_CONFIRMED_INCIDENT",
            "incident": None,
            "audit": [{"stage": "detector", "status": "no_confirmed_incident"}],
        }
    payments = [p.model_dump(mode="json") for p in evaluation.payments]
    aggregate = Aggregate(
        transaction_count=len(payments),
        success_count=sum(p["status"] == "success" for p in payments),
        failure_count=sum(p["status"] == "failed" for p in payments),
        transaction_value=sum(p["amount_minor"] for p in payments),
        successful_value=sum(p["amount_minor"] for p in payments if p["status"] == "success"),
        failed_value=sum(p["amount_minor"] for p in payments if p["status"] == "failed"),
    )
    attribution = shadow.session.latest_attribution
    packet = IncidentEvidencePacket(
        state="incident",
        incident_detected=True,
        confidence=confirmed.trace.confidence_components.get("current_score", 0),
        baseline_metrics=MetricSnapshot(success_rate=confirmed.trace.baseline_success_rate or 0),
        observed_metrics=MetricSnapshot(
            transaction_count=aggregate.transaction_count,
            success_count=aggregate.success_count,
            failure_count=aggregate.failure_count,
            success_rate=aggregate.success_rate,
            failure_rate=1 - aggregate.success_rate,
            total_value_minor=aggregate.transaction_value,
            successful_value_minor=aggregate.successful_value,
            failed_value_minor=aggregate.failed_value,
        ),
        revenue_impact=RevenueImpact(revenue_at_risk_per_hour_minor=aggregate.failed_value),
        top_cohorts=attribution.top_cohorts,
        affected_cohorts=attribution.top_cohorts,
        attribution=attribution.model_dump(),
        incident_window={"confirmed_start": confirmed.bucket_start},
    )
    investigation = build_graph(MockInvestigationProvider()).invoke(
        InvestigationState(evidence_packet=packet)
    )
    result = CounterfactualEngine().run(packet, incident_id="demo-incident")
    selected = next(s for s in result.scenarios if s.scenario_id == result.recommended_scenario_id)
    payload = decision_payload(result, selected)
    explanation = LLMExplanation(
        summary=f"{selected.label} is the deterministic recommendation.",
        reasoning=f"Expected recovery is {payload.expected_recovery} with residual loss {payload.residual_loss} and {payload.risk.value} risk.",
        tradeoffs=["Higher traffic shifts increase exposure risk."],
        uncertainties=["The interval is a heuristic estimate."],
    )
    validation = validate_explanation(payload, explanation)
    return {
        "mode": "SIMULATION",
        "status": "READY",
        "incident": packet.model_dump(mode="json"),
        "counterfactual": result.model_dump(mode="json"),
        "investigation": investigation,
        "decision_payload": payload.model_dump(mode="json"),
        "explanation": validation.model_dump(mode="json"),
        "validation": {
            "valid": validation.valid,
            "status": "validated" if validation.valid else "INVALID_EXPLANATION",
        },
        "audit": [
            {"stage": "detector", "status": "confirmed"},
            {"stage": "investigation", "status": "validated"},
            {"stage": "counterfactual", "status": "complete"},
            {"stage": "decision", "status": "selected"},
        ],
    }


from functools import lru_cache
