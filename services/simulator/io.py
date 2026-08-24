from pathlib import Path

from .domain import SimulationResult


def save(result: SimulationResult, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def load(path: str) -> SimulationResult:
    return SimulationResult.model_validate_json(Path(path).read_text(encoding="utf-8"))


def replay(result: SimulationResult):
    yield from sorted(result.events, key=lambda e: e.timestamp)
