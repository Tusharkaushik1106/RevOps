from typing import Any

from pydantic import BaseModel, Field

from services.detector.schemas import IncidentEvidencePacket


class Hypothesis(BaseModel):
    id: str
    claim: str
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    confidence: float = 0
    evidence_strength: str = "unknown"
    uncertainties: list[str] = Field(default_factory=list)
    quantitative_rationale: str = "Evidence unavailable."


class EvidenceItem(BaseModel):
    id: str
    type: str
    claim: str
    source: str
    window: str = ""
    numeric_values: dict[str, float | int] = Field(default_factory=dict)
    confidence: str = "medium"


class RecoveryCandidate(BaseModel):
    action: str
    rationale: str
    expected_information: str = ""
    expected_benefit: str = "Evidence unavailable."
    risk: str = "Evidence unavailable."
    preconditions: list[str] = Field(default_factory=list)
    monitoring: str = ""
    rollback: str = ""
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class InvestigationState(BaseModel):
    incident: dict[str, Any] = Field(default_factory=dict)
    evidence_packet: IncidentEvidencePacket | None = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    retrieved_evidence: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    hypothesis_scores: dict[str, float] = Field(default_factory=dict)
    selected_hypothesis: Hypothesis | None = None
    confidence: float = 0
    uncertainties: list[str] = Field(default_factory=list)
    recommended_actions: list[RecoveryCandidate] = Field(default_factory=list)
    audit_trace: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "in_progress"
    error: str | None = None

    def validate_evidence_references(self) -> bool:
        valid = {item.id for item in self.evidence_items}
        return all(
            ref in valid
            for h in self.hypotheses
            for ref in [*h.supporting_evidence, *h.contradicting_evidence]
        )


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
