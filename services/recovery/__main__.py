import argparse

from services.detector.schemas import IncidentEvidencePacket, MetricSnapshot

from .engine import CounterfactualEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.parse_args()
    packet = IncidentEvidencePacket(
        incident_detected=True,
        state="incident",
        confidence=0.8,
        baseline_metrics=MetricSnapshot(
            transaction_count=1000,
            success_count=940,
            failure_count=60,
            total_value_minor=1000000,
            successful_value_minor=940000,
            failed_value_minor=60000,
        ),
        observed_metrics=MetricSnapshot(
            transaction_count=1000,
            success_count=780,
            failure_count=220,
            total_value_minor=1000000,
            successful_value_minor=780000,
            failed_value_minor=220000,
        ),
    )
    result = CounterfactualEngine().run(packet, incident_id="demo-incident")
    print("COUNTERFACTUAL RECOVERY\n")
    [
        print(
            f"{s.label}: recovered={s.impact.expected_recovered_revenue_minor} residual={s.impact.residual_loss_minor} risk={s.risk.level.value}"
        )
        for s in result.scenarios
    ]
    print(
        f"Recommended: {result.recommended_scenario_id}\n{result.recommendation_reason}\nNo financial action executed."
    )


if __name__ == "__main__":
    main()
