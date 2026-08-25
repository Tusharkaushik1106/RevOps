# Phase 3 causal investigation

Phase 3 introduces a LangGraph investigation boundary over the Phase 2 evidence packet. The graph summarizes the confirmed incident, generates and compares hypotheses, retrieves read-only evidence, selects the strongest supported explanation, and proposes recovery candidates. It has no payment execution authority.

The provider boundary supports Gemini through `GeminiProvider`; tests use `MockInvestigationProvider`. Runtime tools receive the typed evidence packet and indexed observable summaries only. Hidden simulator ground truth is evaluator-only and is not part of agent state or tools.
