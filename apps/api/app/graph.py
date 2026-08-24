"""LangGraph orchestration skeleton; nodes are intentionally placeholders."""
from typing import TypedDict
from langgraph.graph import END, START, StateGraph


class IncidentState(TypedDict, total=False):
    incident_id: str
    events: list[dict]
    evidence: dict
    hypotheses: list[dict]
    revenue_at_risk_minor: int
    candidate_actions: list[dict]
    policy_decisions: list[dict]
    execution_results: list[dict]
    outcomes: list[dict]
    stop_reason: str


def placeholder_node(state: IncidentState) -> IncidentState:
    return state


def build_graph():
    graph = StateGraph(IncidentState)
    stages = ["detect_incident", "gather_evidence", "generate_hypotheses", "validate_hypotheses", "estimate_revenue_at_risk", "generate_candidate_actions", "score_candidate_actions", "policy_check", "execute", "observe_outcome", "recalculate"]
    for stage in stages:
        graph.add_node(stage, placeholder_node)
    graph.add_edge(START, stages[0])
    for current, following in zip(stages, stages[1:]):
        graph.add_edge(current, following)
    graph.add_edge(stages[-1], END)
    return graph.compile()
