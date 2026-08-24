import argparse
import sys

from .config import SCENARIOS
from .generator import Simulator
from .history import generate_evaluation, generate_history
from .io import load, replay, save


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--payments", type=int, default=1000)
    g.add_argument("--scenario", choices=[x.value for x in SCENARIOS])
    g.add_argument("--output", default="data/synthetic/example.json")
    r = sub.add_parser("replay")
    r.add_argument("--file", required=True)
    h = sub.add_parser("generate-history")
    h.add_argument("--days", type=int, default=7)
    h.add_argument("--seed", type=int, default=42)
    h.add_argument("--payments", type=int, default=10000)
    h.add_argument("--output", default="data/synthetic/history.json")
    e = sub.add_parser("generate-evaluation")
    e.add_argument("--history-days", type=int, default=7)
    e.add_argument("--seed", type=int, default=42)
    e.add_argument("--payments", type=int, default=10000)
    e.add_argument("--scenario", choices=[x.value for x in SCENARIOS])
    e.add_argument("--output", default="data/synthetic/evaluation.json")
    a = p.parse_args()
    if a.command == "generate":
        result = Simulator(a.seed).generate(
            a.payments,
            scenario=SCENARIOS[next((x for x in SCENARIOS if x.value == a.scenario), None)]
            if a.scenario
            else None,
        )
        save(result, a.output)
        print(f"Generated: {len(result.payments):,} payments\nScenario: {a.scenario or 'baseline'}")
        if result.ground_truth:
            truth = result.ground_truth[0]
            if truth.metric_kind == "checkout_abandonment":
                print(
                    f"Baseline abandonment: {truth.baseline_abandonment_rate:.2%}\nIncident abandonment: {truth.incident_abandonment_rate:.2%}\nIncremental abandonment: {truth.incremental_abandonment_rate:.2%}\nRevenue exposed: ₹{truth.revenue_exposure_minor:,}"
                )
            elif truth.metric_kind == "subscription_renewal":
                print(
                    f"Baseline renewal success: {truth.baseline_expected_success:.2%}\nIncident renewal success: {truth.incident_success:.2%}\nRenewal revenue exposed: ₹{truth.renewal_revenue_exposure_minor:,}"
                )
            else:
                print(
                    f"Baseline success: {truth.baseline_expected_success:.2%}\nIncident success: {truth.incident_success:.2%}\nRevenue exposed: ₹{truth.revenue_exposure_minor:,}"
                )
        print("Ground truth: stored separately")
    elif a.command == "replay":
        print(f"Replayed {sum(1 for _ in replay(load(a.file))):,} events")
    elif a.command == "generate-history":
        generate_history(a.days, a.seed, a.payments).model_dump_json(indent=2)
        from pathlib import Path

        Path(a.output).write_text(
            generate_history(a.days, a.seed, a.payments).model_dump_json(indent=2), encoding="utf-8"
        )
        print(f"Generated {a.days} clean history days: {a.output}")
    else:
        scenario = next((x for x in SCENARIOS if x.value == a.scenario), None)
        world = generate_evaluation(a.history_days, a.seed, scenario, a.payments)
        from pathlib import Path

        Path(a.output).write_text(world.model_dump_json(indent=2), encoding="utf-8")
        print(f"Generated {a.history_days} history days plus evaluation day: {a.output}")


if __name__ == "__main__":
    main()
