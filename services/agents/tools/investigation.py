from typing import Any

from services.agents.rag import search_knowledge
from services.detector.schemas import IncidentEvidencePacket


class InvestigationTools:
    """Read-only tools over the evidence packet; no raw dataset or hidden truth access."""

    def __init__(self, packet: IncidentEvidencePacket):
        self.packet = packet

    def get_cohort_history(self, dimension: str, value: str) -> dict[str, Any]:
        matches = [
            c.model_dump()
            for c in self.packet.affected_cohorts
            if c.dimension == dimension and c.value == value
        ]
        return {"dimension": dimension, "value": value, "evidence": matches}

    def get_revenue_exposure(self) -> dict[str, int]:
        return {
            "revenue_rate_at_risk_minor": self.packet.revenue_impact.revenue_at_risk_per_hour_minor,
            "projected_revenue_at_risk_minor": self.packet.revenue_impact.revenue_at_risk_minor,
        }

    def get_interaction_evidence(self) -> dict[str, Any]:
        return (
            self.packet.attribution.get("top_interactions", {}) if self.packet.attribution else {}
        )

    def get_failure_signature(self) -> dict[str, float]:
        return self.packet.anomaly_metrics

    def search_payment_knowledge(self, query: str) -> dict[str, Any]:
        return {"query": query, "documents": search_knowledge(query), "type": "DOMAIN_KNOWLEDGE"}
