from typing import Protocol
from .schemas import Incident, PaymentEvent, PolicyDecision, RecoveryAction


class EventRepository(Protocol):
    def append(self, event: PaymentEvent) -> None: ...


class IncidentDetector(Protocol):
    def detect(self, events: list[PaymentEvent]) -> list[Incident]: ...


class EvidenceAndReasoningService(Protocol):
    def explain(self, incident: Incident, events: list[PaymentEvent]) -> dict: ...


class RecoveryPlanner(Protocol):
    def propose(self, incident: Incident) -> list[RecoveryAction]: ...


class PolicyEngine(Protocol):
    def validate(self, action: RecoveryAction) -> PolicyDecision: ...


class PaymentExecutor(Protocol):
    def execute(self, action: RecoveryAction) -> dict: ...


class OutcomeObserver(Protocol):
    def observe(self, incident_id: str) -> dict: ...
