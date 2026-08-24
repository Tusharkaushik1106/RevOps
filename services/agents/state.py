from typing import Any
from pydantic import BaseModel, Field

class RecoveryCase(BaseModel):
    incident: dict[str, Any] | None = None
    merchant_context: dict[str, Any] = Field(default_factory=dict)
    payment_context: dict[str, Any] = Field(default_factory=dict)
    affected_cohort: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    revenue_at_risk: dict[str, Any] | None = None
    candidate_actions: list[dict[str, Any]] = Field(default_factory=list)
    selected_action: dict[str, Any] | None = None
    policy_decision: dict[str, Any] | None = None
    execution_result: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None
    evaluation_result: dict[str, Any] | None = None
    audit_information: list[dict[str, Any]] = Field(default_factory=list)
