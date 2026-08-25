from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PaymentEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    merchant_id: str
    payment_id: str | None = None
    amount_minor: int = Field(ge=0)
    currency: str = "INR"
    status: str
    issuer: str | None = None
    payment_method: str | None = None
    gateway: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class IncidentStatus(StrEnum):
    OPEN = "open"
    OBSERVING = "observing"
    RESOLVED = "resolved"
    SAFE_STOPPED = "safe_stopped"


class Incident(BaseModel):
    incident_id: str
    status: IncidentStatus = IncidentStatus.OPEN
    detected_at: datetime
    title: str
    affected_cohort: dict[str, str] = Field(default_factory=dict)
    revenue_at_risk_minor: int = 0
    ground_truth: dict[str, str] | None = None


class RecoveryAction(BaseModel):
    action_id: str
    incident_id: str
    kind: str
    rationale: str = ""
    expected_incremental_recovery_minor: int = 0
    requires_approval: bool = False


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    policy_version: str = "v1-placeholder"


class HealthResponse(BaseModel):
    status: str
    phase: str
