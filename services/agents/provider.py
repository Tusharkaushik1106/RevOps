from typing import Protocol

from apps.api.app.config import get_settings
from .rag import search_knowledge

from .state import Hypothesis, InvestigationState, RecoveryCandidate


class StructuredInvestigationProvider(Protocol):
    def investigate(self, state: InvestigationState, instruction: str) -> InvestigationState: ...


class GeminiProvider:
    """Gemini adapter boundary. The SDK is imported lazily and credentials stay in environment config."""

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.gemini_model
        self.api_key = settings.gemini_api_key

    def investigate(self, state: InvestigationState, instruction: str) -> InvestigationState:
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is missing from the configured environment")
        model = ChatGoogleGenerativeAI(model=self.model, google_api_key=self.api_key, temperature=0)
        structured = model.with_structured_output(InvestigationState)
        prompt = f"You are a cautious revenue incident investigator. {instruction}. Use only supplied evidence; distinguish observations from hypotheses and never invent facts. Current state: {state.model_dump_json()}"
        return structured.invoke(prompt)


class MockInvestigationProvider:
    def investigate(self, state: InvestigationState, instruction: str) -> InvestigationState:
        if instruction == "generate_hypotheses":
            refs = [e.id for e in state.evidence_items]
            cohort = next(
                (
                    e
                    for e in state.evidence_items
                    if e.type == "INCIDENT_OBSERVATION" and "contribution" in e.numeric_values
                ),
                None,
            )
            claim = (
                cohort.claim
                if cohort
                else "The incident has a measurable success-rate and revenue deviation."
            )
            state.hypotheses = [
                Hypothesis(
                    id="H1",
                    claim=f"{claim} This is the strongest supported localized explanation, not causal proof.",
                    supporting_evidence=refs[2:3] or refs[:1],
                    confidence=0.7,
                    evidence_strength="medium",
                    uncertainties=["Association is not causal."],
                ),
                Hypothesis(
                    id="H2",
                    claim="A broader payment infrastructure degradation may explain the observed failure signature.",
                    supporting_evidence=refs[:1],
                    confidence=0.4,
                    evidence_strength="low",
                    uncertainties=["Gateway and issuer evidence needs comparison."],
                ),
            ]
        elif instruction == "compare_hypotheses" and state.hypotheses:
            state.hypothesis_scores = {h.id: h.confidence for h in state.hypotheses}
            state.selected_hypothesis = max(state.hypotheses, key=lambda h: h.confidence)
            state.confidence = state.selected_hypothesis.confidence
        elif instruction == "investigate_hypotheses":
            query = (
                state.selected_hypothesis.claim
                if state.selected_hypothesis
                else "payment failure signature gateway issuer timeout"
            )
            state.retrieved_evidence.extend(search_knowledge(query))
            state.audit_trace.append(
                {
                    "stage": "domain_knowledge_retrieval",
                    "type": "DOMAIN_KNOWLEDGE",
                    "ground_truth_used": False,
                }
            )
        elif instruction == "generate_recovery_candidates":
            state.recommended_actions = [
                RecoveryCandidate(
                    action="Investigate bounded routing or retry options for the affected cohort.",
                    rationale="Evidence supports investigation only; no action is executed.",
                    expected_information="Requires policy and alternate-route health checks.",
                    expected_benefit="Potentially reduce exposure for the associated cohort.",
                    risk="Traffic may move to another degraded route.",
                    preconditions=[
                        "Confirm alternate route health",
                        "Pass deterministic policy checks",
                    ],
                    monitoring="Track cohort success rate and revenue rate at risk.",
                    rollback="Restore prior route if success rate worsens.",
                    supporting_evidence_ids=[e.id for e in state.evidence_items],
                )
            ]
        state.audit_trace.append(
            {"stage": instruction, "provider": "mock", "ground_truth_used": False}
        )
        return state
