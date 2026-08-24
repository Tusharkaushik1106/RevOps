from typing import Protocol

from .domain import IncidentType, SimulationRecord


class PaymentSimulator(Protocol):
    def generate(self, seed: int, count: int) -> list[SimulationRecord]: ...
    def inject_incident(self, incident_type: IncidentType) -> None: ...
