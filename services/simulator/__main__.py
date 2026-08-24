import argparse

from .config import SCENARIOS
from .generator import Simulator
from .io import load, replay, save


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--payments", type=int, default=1000)
    g.add_argument("--scenario", choices=[x.value for x in SCENARIOS])
    g.add_argument("--output", default="data/synthetic/example.json")
    r = sub.add_parser("replay")
    r.add_argument("--file", required=True)
    a = p.parse_args()
    if a.command == "generate":
        result = Simulator(a.seed).generate(
            a.payments,
            scenario=SCENARIOS[next((x for x in SCENARIOS if x.value == a.scenario), None)]
            if a.scenario
            else None,
        )
        save(result, a.output)
        print(
            f"Generated: {len(result.payments):,} payments\nScenario: {a.scenario or 'baseline'}\nGround truth: stored separately"
        )
    else:
        print(f"Replayed {sum(1 for _ in replay(load(a.file))):,} events")


if __name__ == "__main__":
    main()
