from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from .config import SCENARIOS
from .domain import IncidentType, Payment, PaymentEvent, SimulationResult
from .generator import Simulator


class ObservableDataset(BaseModel):
    payments: list[Payment] = Field(default_factory=list)
    events: list[PaymentEvent] = Field(default_factory=list)


class EvaluationWorld(BaseModel):
    history: ObservableDataset
    evaluation: ObservableDataset
    hidden_truth: list[dict] = Field(default_factory=list)


def _observable(result: SimulationResult) -> ObservableDataset:
    return ObservableDataset(payments=result.payments, events=result.events)


def generate_history(
    days: int = 7, seed: int = 42, payments_per_day: int = 10000, start_date: datetime | None = None
) -> ObservableDataset:
    start = start_date or datetime(2025, 1, 1, tzinfo=UTC)
    payments = []
    events = []
    for day in range(days):
        result = Simulator(seed + day).generate(
            payments_per_day, start=start + timedelta(days=day), end=start + timedelta(days=day + 1)
        )
        payments.extend(result.payments)
        events.extend(result.events)
    return ObservableDataset(payments=payments, events=sorted(events, key=lambda e: e.timestamp))


def generate_evaluation(
    history_days: int = 7,
    seed: int = 42,
    scenario: IncidentType | None = None,
    payments_per_day: int = 10000,
) -> EvaluationWorld:
    history = generate_history(history_days, seed, payments_per_day)
    start = max(p.timestamp for p in history.payments) + timedelta(seconds=1)
    day_start = datetime(start.year, start.month, start.day, tzinfo=UTC) + timedelta(days=1)
    result = Simulator(seed + history_days).generate(
        payments_per_day,
        start=day_start,
        end=day_start + timedelta(days=1),
        scenario=SCENARIOS[scenario] if scenario else None,
    )
    return EvaluationWorld(
        history=history,
        evaluation=_observable(result),
        hidden_truth=[x.model_dump(mode="json") for x in result.ground_truth],
    )
