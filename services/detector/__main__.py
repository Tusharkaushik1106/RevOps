import argparse
import sys

from services.simulator.io import load

from .detector import IncidentDetector
from .schemas import ObservableInput


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--file", required=True)
    args = parser.parse_args()
    result = load(args.file)
    observable = ObservableInput(
        payments=[p.model_dump(mode="json") for p in result.payments],
        events=[e.model_dump(mode="json") for e in result.events],
    )
    packet = IncidentDetector().detect(observable)
    print(
        f"Incident detected: {'YES' if packet.incident_detected else 'NO'}\nConfidence: {packet.confidence:.0%}\nObserved success: {packet.observed_metrics.success_rate:.2%}\nBaseline success: {packet.baseline_metrics.success_rate:.2%}\nRevenue at risk: ₹{packet.revenue_impact.revenue_at_risk_per_hour_minor:,}/hour\nTop affected cohorts:"
    )
    [print(f"{i}. {c.dimension} = {c.value}") for i, c in enumerate(packet.affected_cohorts[:3], 1)]


if __name__ == "__main__":
    main()
