from services.agents.graph import build_graph
from services.agents.provider import GeminiProvider, MockInvestigationProvider
from services.agents.rag import search_knowledge
from services.agents.state import EvidenceItem, Hypothesis, InvestigationState
from services.agents.tools.investigation import InvestigationTools
from services.detector.schemas import IncidentEvidencePacket, MetricSnapshot


def packet():
    return IncidentEvidencePacket(
        incident_detected=True,
        confidence=0.8,
        baseline_metrics=MetricSnapshot(),
        observed_metrics=MetricSnapshot(),
    )


def test_graph_compiles_and_mock_runs():
    graph = build_graph(MockInvestigationProvider())
    state = InvestigationState(evidence_packet=packet())
    result = graph.invoke(state)
    assert result["audit_trace"][-1]["ground_truth_used"] is False


def test_tools_are_read_only_and_packet_bound():
    tools = InvestigationTools(packet())
    assert tools.get_failure_signature() == {}
    assert "ground_truth" not in str(tools.get_revenue_exposure()).lower()


def test_hypothesis_state_is_structured():
    state = InvestigationState(evidence_packet=packet())
    assert state.evidence_packet.incident_detected


def test_rag_is_labelled_domain_knowledge():
    assert search_knowledge("gateway timeout")[0]["type"] == "DOMAIN_KNOWLEDGE"


def test_hallucinated_evidence_reference_is_rejected():
    state = InvestigationState(
        evidence_items=[EvidenceItem(id="EV-001", type="OBSERVATION", claim="x", source="test")],
        hypotheses=[Hypothesis(id="H1", claim="x", supporting_evidence=["EV-999"])],
    )
    assert state.validate_evidence_references() is False


def test_normal_packet_is_not_investigated():
    from services.agents.graph import build_graph

    normal = IncidentEvidencePacket(
        incident_detected=False,
        confidence=0,
        baseline_metrics=MetricSnapshot(),
        observed_metrics=MetricSnapshot(),
    )
    result = build_graph(MockInvestigationProvider()).invoke(
        InvestigationState(evidence_packet=normal)
    )
    assert (
        result["status"] == "NO_CONFIRMED_INCIDENT"
        and not result["hypotheses"]
        and not result["recommended_actions"]
    )


def test_gemini_missing_key_is_safe(monkeypatch):
    from apps.api.app.config import get_settings

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    provider = GeminiProvider()
    provider.api_key = None
    try:
        provider.investigate(InvestigationState(), "test")
    except RuntimeError as error:
        assert "GEMINI_API_KEY" in str(error)
    else:
        raise AssertionError("missing Gemini key did not fail safely")
    get_settings.cache_clear()
