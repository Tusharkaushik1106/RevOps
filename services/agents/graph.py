from langgraph.graph import END, START, StateGraph

from .provider import StructuredInvestigationProvider
from .state import EvidenceItem, InvestigationState


def summarize_incident(state: InvestigationState, provider=None):
    packet = state.evidence_packet
    if packet:
        state.evidence_items = [
            EvidenceItem(
                id="EV-001",
                type="INCIDENT_OBSERVATION",
                claim=f"Observed success rate {packet.observed_metrics.success_rate:.2%} versus baseline {packet.baseline_metrics.success_rate:.2%}.",
                source="IncidentEvidencePacket",
                numeric_values={
                    "observed": packet.observed_metrics.success_rate,
                    "baseline": packet.baseline_metrics.success_rate,
                },
            ),
            EvidenceItem(
                id="EV-002",
                type="INCIDENT_OBSERVATION",
                claim="Revenue impact is present in the quantitative evidence packet.",
                source="IncidentEvidencePacket",
                numeric_values={
                    "revenue_rate_at_risk_minor": packet.revenue_impact.revenue_at_risk_per_hour_minor
                },
            ),
        ]
        state.evidence_items += [
            EvidenceItem(
                id=f"EV-{i + 3:03d}",
                type="INCIDENT_OBSERVATION",
                claim=f"{c.dimension}={c.value} is associated with economic contribution {c.economic_contribution:.2%}.",
                source="IncidentEvidencePacket",
                numeric_values={
                    "contribution": c.economic_contribution,
                    "effect_size": c.effect_size,
                },
            )
            for i, c in enumerate(packet.top_cohorts[:5])
        ]
    state.audit_trace.append(
        {
            "stage": "evidence_extraction",
            "evidence_ids": [e.id for e in state.evidence_items],
            "ground_truth_used": False,
        }
    )
    state.audit_trace.append({"stage": "summarize_incident", "ground_truth_used": False})
    return state


def guard_confirmed_incident(state: InvestigationState):
    if (
        not state.evidence_packet
        or state.evidence_packet.state.value != "incident"
        or not state.evidence_packet.incident_detected
    ):
        state.status = "NO_CONFIRMED_INCIDENT"
        state.audit_trace.append(
            {"stage": "investigation_guard", "status": state.status, "ground_truth_used": False}
        )
    return state


def generate_hypotheses(state: InvestigationState, provider: StructuredInvestigationProvider):
    return _call_provider(state, provider, "generate_hypotheses")


def investigate_hypotheses(state: InvestigationState, provider: StructuredInvestigationProvider):
    return _call_provider(state, provider, "investigate_hypotheses")


def compare_hypotheses(state: InvestigationState, provider: StructuredInvestigationProvider):
    return _call_provider(state, provider, "compare_hypotheses")


def determine_cause(state: InvestigationState, provider: StructuredInvestigationProvider):
    return _call_provider(state, provider, "determine_most_likely_cause")


def generate_recovery_candidates(
    state: InvestigationState, provider: StructuredInvestigationProvider
):
    return _call_provider(state, provider, "generate_recovery_candidates")


def _call_provider(state, provider, instruction):
    try:
        return provider.investigate(state, instruction)
    except Exception as error:  # noqa: BLE001 - provider failures must become structured state
        state.status = "PROVIDER_ERROR"
        state.error = f"{type(error).__name__}: {error}"
        state.audit_trace.append(
            {"stage": instruction, "status": "PROVIDER_ERROR", "error_type": type(error).__name__}
        )
        return state


def build_graph(provider: StructuredInvestigationProvider):
    graph = StateGraph(InvestigationState)
    graph.add_node("guard_confirmed_incident", guard_confirmed_incident)
    graph.add_node("summarize_incident", lambda s: summarize_incident(s, provider))
    graph.add_node("generate_hypotheses", lambda s: generate_hypotheses(s, provider))
    graph.add_node("investigate_hypotheses", lambda s: investigate_hypotheses(s, provider))
    graph.add_node("compare_hypotheses", lambda s: compare_hypotheses(s, provider))
    graph.add_node("determine_cause", lambda s: determine_cause(s, provider))
    graph.add_node(
        "generate_recovery_candidates", lambda s: generate_recovery_candidates(s, provider)
    )
    graph.add_edge(START, "guard_confirmed_incident")
    graph.add_conditional_edges(
        "guard_confirmed_incident",
        lambda s: "investigate" if s.status == "in_progress" else "stop",
        {"investigate": "summarize_incident", "stop": END},
    )
    graph.add_edge("summarize_incident", "generate_hypotheses")
    graph.add_edge("generate_hypotheses", "investigate_hypotheses")
    graph.add_edge("investigate_hypotheses", "compare_hypotheses")
    graph.add_edge("compare_hypotheses", "determine_cause")
    graph.add_edge("determine_cause", "generate_recovery_candidates")
    graph.add_edge("generate_recovery_candidates", END)
    return graph.compile()
