import argparse
import json

from services.detector.calibration import canonical_world
from services.detector.evaluation_harness import observable
from services.detector.pipeline import Aggregate
from services.detector.schemas import IncidentEvidencePacket, MetricSnapshot, RevenueImpact
from services.detector.sequential import SequentialShadowEvaluator

from .graph import build_graph
from .provider import GeminiProvider, MockInvestigationProvider
from .state import InvestigationState


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "gemini"], default="mock")
    parser.add_argument("--payments", type=int, default=10000)
    args = parser.parse_args()
    history, evaluation = canonical_world(42, 0.65, args.payments)
    shadow = SequentialShadowEvaluator(5)
    observations = shadow.run(observable(history), observable(evaluation))
    confirmed = next((item for item in observations if item.state == "incident"), None)
    metrics = [p.model_dump(mode="json") for p in evaluation.payments]
    total = Aggregate(
        transaction_count=len(metrics),
        success_count=sum(p["status"] == "success" for p in metrics),
        failure_count=sum(p["status"] == "failed" for p in metrics),
        transaction_value=sum(p["amount_minor"] for p in metrics),
        successful_value=sum(p["amount_minor"] for p in metrics if p["status"] == "success"),
        failed_value=sum(p["amount_minor"] for p in metrics if p["status"] == "failed"),
    )
    attribution = shadow.session.latest_attribution
    packet = IncidentEvidencePacket(
        state="incident" if confirmed else "normal",
        incident_detected=bool(confirmed),
        confidence=confirmed.trace.confidence_components.get("current_score", 0)
        if confirmed
        else 0,
        baseline_metrics=MetricSnapshot(),
        observed_metrics=MetricSnapshot(
            transaction_count=total.transaction_count,
            success_count=total.success_count,
            failure_count=total.failure_count,
            success_rate=total.success_rate,
            failure_rate=1 - total.success_rate,
            total_value_minor=total.transaction_value,
            successful_value_minor=total.successful_value,
            failed_value_minor=total.failed_value,
        ),
        revenue_impact=RevenueImpact(revenue_at_risk_per_hour_minor=total.failed_value),
        incident_window={"confirmed_start": confirmed.bucket_start} if confirmed else {},
        top_cohorts=attribution.top_cohorts,
        affected_cohorts=attribution.top_cohorts,
        attribution=attribution.model_dump(),
    )
    provider = MockInvestigationProvider() if args.provider == "mock" else GeminiProvider()
    result = build_graph(provider).invoke(InvestigationState(evidence_packet=packet))
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()
