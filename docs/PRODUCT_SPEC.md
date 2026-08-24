# Revenue Incident Commander

## 1. Product Overview

Revenue Incident Commander is an AI-powered revenue recovery intelligence system designed for payment businesses and merchants.

The system does NOT simply retry failed payments.

It detects revenue-impacting payment incidents, identifies likely root causes, estimates revenue at risk, evaluates multiple possible recovery interventions, selects the action with the highest expected incremental recovery value, enforces deterministic financial policies, executes bounded actions through Razorpay test APIs, observes outcomes, and measures incremental revenue recovered.

The core product thesis is:

> Recover revenue incidents, not merely failed payments.

A payment failure is an individual event.

A revenue incident is a coordinated degradation involving dimensions such as:

- payment method
- issuer
- gateway
- merchant
- customer cohort
- geography
- device
- transaction amount
- time
- failure reason
- historical payment behavior

The MVP focuses on identifying these incidents and autonomously deciding the most economically valuable recovery response.

---

# 2. Primary MVP Scenario

The primary MVP scenario is:

Payment degradation
→ incident detection
→ affected cohort identification
→ causal diagnosis
→ revenue-at-risk estimation
→ recovery strategy generation
→ incremental recovery estimation
→ deterministic policy validation
→ bounded execution
→ outcome observation
→ counterfactual evaluation

Example:

A merchant normally has a 94% payment success rate.

A sudden degradation occurs:

- overall success rate falls to 87%
- failures are concentrated among a particular issuer
- a particular payment method is disproportionately affected
- the degradation begins at a specific time
- other payment methods remain within normal ranges

The system should:

1. Detect the incident.
2. Identify the affected cohort.
3. Generate possible root causes.
4. Gather supporting evidence.
5. Estimate confidence for each hypothesis.
6. Calculate revenue currently at risk.
7. Generate candidate recovery actions.
8. Estimate expected recovery from each action.
9. Estimate incremental recovery over doing nothing.
10. Select the economically strongest action.
11. Apply deterministic policy controls.
12. Execute the action through a mock or Razorpay test-mode adapter.
13. Observe the result.
14. Calculate actual recovery.
15. Compare against the expected baseline.
16. Report incremental recovered revenue.

---

# 3. Core Product Flow

The system follows this conceptual pipeline:

Payment Events
→ Incident Detection
→ Evidence Gathering
→ Root Cause Analysis
→ Revenue Impact Estimation
→ Recovery Strategy Generation
→ Recovery/Uplift Scoring
→ Policy Validation
→ Action Execution
→ Outcome Observation
→ Counterfactual Evaluation
→ Learning/Evaluation

---

# 4. Core Product Principle

The product should optimize for:

## Incremental recovered revenue

It must distinguish between:

- gross recovered revenue
- expected baseline recovery
- incremental recovered revenue

Example:

If a cohort naturally recovers ₹7.3 lakh without intervention and the agent cohort recovers ₹10.1 lakh:

Gross recovered revenue:

₹10.1 lakh

Expected baseline:

₹7.3 lakh

Incremental recovered revenue:

₹2.8 lakh

The system should prioritize the incremental value rather than taking credit for revenue that would have recovered anyway.

---

# 5. AI Responsibilities

AI must be used where it provides meaningful value.

## LLM Responsibilities

LLMs may be used for:

- evidence synthesis
- root-cause reasoning
- hypothesis generation
- ambiguous incident analysis
- recovery strategy reasoning
- structured explanations
- recovery communication generation
- summarization of complex incident traces

LLMs must not be trusted with unrestricted financial authority.

---

# 6. Classical ML / Statistical Responsibilities

Classical ML and statistical methods should handle quantitative prediction.

Potential components include:

## Incident Detection

Use methods such as:

- rolling baselines
- z-score analysis
- EWMA
- change-point detection
- statistical significance testing
- anomaly detection

The implementation should begin with simple interpretable methods before introducing unnecessary complexity.

## Recovery Probability

Estimate:

P(recovery | action)

Potential models:

- LightGBM
- XGBoost
- scikit-learn models

Features may include:

- payment amount
- payment method
- issuer
- gateway
- merchant category
- customer tenure
- customer history
- failure code
- retry count
- timestamp
- device
- geography
- subscription age
- previous recovery behavior

## Uplift / Incremental Recovery

Estimate:

P(recovery | action) - P(recovery | no action)

For candidate actions such as:

- retry
- route change
- payment link
- alternate payment method
- customer communication
- wait
- escalation

The system should calculate expected economic value rather than simply selecting the action with the highest raw recovery probability.

---

# 7. Revenue-at-Risk

The system should estimate:

- current revenue velocity
- affected transaction volume
- estimated revenue exposure
- expected loss if the incident continues
- recoverable revenue
- expected incremental recovery

The exact financial formulas should remain deterministic and implemented in Python rather than generated by an LLM.

---

# 8. LangGraph Agent Architecture

LangGraph should provide stateful orchestration.

The conceptual graph is:

START
→ DetectIncident
→ GatherEvidence
→ GenerateHypotheses
→ ValidateHypotheses
→ EstimateRevenueAtRisk
→ GenerateRecoveryPlans
→ ScoreRecoveryPlans
→ PolicyCheck
→ ExecuteAction
→ ObserveOutcome
→ Recalculate
→ Stop or Continue

The graph must support persistent typed state.

A RecoveryCase should be able to contain:

- incident
- merchant context
- payment context
- affected cohort
- evidence
- root-cause hypotheses
- confidence scores
- revenue-at-risk estimate
- candidate actions
- expected recovery
- expected incremental recovery
- selected action
- policy decision
- execution result
- observed outcome
- evaluation result
- audit information

---

# 9. Policy Governor

The Policy Governor must be deterministic.

LLMs cannot override it.

Potential policies include:

- maximum retries
- customer contact cooldown
- maximum customer contacts
- maximum automatic action value
- maximum discount
- human approval threshold
- duplicate-action protection
- stopping conditions

Example:

MAX_RETRIES = 2

MAX_CUSTOMER_CONTACTS = 3

MAX_DISCOUNT = 5%

HUMAN_APPROVAL_THRESHOLD = ₹10,000

These values are examples and should eventually be configurable per merchant.

The policy layer must reject actions that violate constraints.

---

# 10. Execution Layer

The execution layer abstracts financial actions.

Potential actions:

- retry payment
- create payment link
- initiate alternate recovery method
- routing/recovery action
- customer communication
- wait
- human escalation

The initial implementation should use mock execution.

Razorpay Test Mode should be integrated later through a dedicated adapter.

The system must never depend directly on Razorpay-specific implementation details throughout the codebase.

---

# 11. Razorpay Integration

Razorpay should be treated as the payment infrastructure/actuator layer.

The MVP should use Razorpay Test Mode only.

Potential integrations include:

- payment creation
- payment status
- orders
- subscriptions
- payment links
- webhooks

Production payment credentials must never be used.

All credentials must be stored in environment variables.

---

# 12. Synthetic Revenue Simulation

Because the MVP does not have access to production payment data, it must include a synthetic payment/revenue simulator.

The simulator should generate:

- merchants
- customers
- orders
- payments
- payment events
- failures
- interventions
- outcomes

The simulator must maintain known ground truth.

Controlled incident types should eventually include:

1. issuer degradation
2. gateway degradation
3. payment-method degradation
4. merchant-specific degradation
5. checkout abandonment spike
6. subscription renewal degradation

The simulator should allow controlled injection of incidents.

Example:

Normal success rate:

94%

Injected issuer degradation:

success rate falls to 86%

The ground-truth incident cause should be known to the simulator but hidden from the agent.

This allows objective evaluation.

---

# 13. Counterfactual Evaluation

The system should support controlled experiments.

Example:

10,000 affected payments

5,000 control

5,000 agent intervention

Measure:

Control recovery:
₹7.3 lakh

Agent recovery:
₹10.1 lakh

Incremental recovery:
₹2.8 lakh

The evaluation system should calculate:

- gross recovery
- baseline recovery
- incremental recovery
- recovery rate
- intervention rate
- unnecessary interventions
- policy violations
- duplicate actions
- time to recovery
- stopping accuracy

---

# 14. Evaluation Bench

The project should eventually contain a repeatable evaluation environment.

Compare:

1. Fixed Retry Baseline
2. Basic ML Recovery Baseline
3. Revenue Incident Commander

Metrics:

- incident detection precision
- incident detection recall
- root-cause accuracy
- revenue-at-risk estimation error
- recovery prediction quality
- uplift estimation quality
- gross recovered revenue
- incremental recovered revenue
- intervention cost
- unnecessary interventions
- policy violations
- duplicate actions
- time to recovery
- safe-stop accuracy

The evaluation should be reproducible using fixed random seeds.

---

# 15. RAG

RAG should support contextual reasoning but should not be the core product.

Potential knowledge sources:

- payment error semantics
- retry rules
- merchant policies
- recovery playbooks
- communication policies
- Razorpay API documentation
- payment-method behavior
- operational policies
- compliance constraints

Preferred architecture:

Local embedding model
→ PostgreSQL pgvector

Do not introduce a paid vector database.

Embeddings should run locally.

---

# 16. Cost Constraint

The complete MVP must be buildable for ₹0.

Preferred stack:

- Next.js
- TypeScript
- Vercel free tier
- FastAPI
- Python
- Supabase PostgreSQL
- pgvector
- local sentence-transformer embeddings
- local ML models
- Gemini free tier where available
- LangGraph
- Razorpay Test Mode
- Docker for local development

Do not introduce paid infrastructure.

Do not introduce AWS in the initial MVP.

Do not introduce:

- Kubernetes
- Kafka
- paid vector databases
- paid model APIs
- GPU infrastructure
- unnecessary distributed systems

The system must be capable of running on a normal developer laptop.

---

# 17. Architecture Principles

1. Intelligence over infrastructure.
2. LLMs reason; deterministic systems authorize.
3. Financial calculations must be deterministic.
4. Every important decision must be explainable.
5. Every agent action must be auditable.
6. Evaluation must be reproducible.
7. The system should fail safely.
8. The system should know when to stop pursuing recovery.
9. Prefer simple architecture over premature distributed systems.
10. Do not add technology merely for the sake of appearing sophisticated.

---

# 18. Planned Technology Stack

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts
- React Flow

## Backend

- Python
- FastAPI
- Pydantic

## Agents

- LangGraph
- LangChain where useful
- Gemini-compatible LLM abstraction

## ML

- Python
- NumPy
- Pandas or Polars
- SciPy
- scikit-learn
- XGBoost or LightGBM
- statsmodels where useful

## Database

- PostgreSQL
- Supabase
- pgvector

## Embeddings

- local sentence-transformer model

## Payment

- Razorpay Test Mode

## Local Development

- Docker Compose
- Git

---

# 19. Initial Repository Architecture

The repository should eventually follow this structure:

apps/
    dashboard/

services/
    api/
    agents/
    ml/
    simulator/
    policy/
    executor/

packages/
    schemas/

data/
    synthetic/
    evaluation/

docs/

infra/
    docker/

scripts/

tests/

---

# 20. Current Development Phase

## PHASE 0 — FOUNDATION ONLY

The immediate goal is to establish the repository foundation.

At this phase:

DO:

- create repository structure
- configure frontend
- configure backend
- configure Python tooling
- configure TypeScript tooling
- create typed schemas
- create service boundaries
- create database models/migrations
- create configuration system
- create placeholder interfaces
- create testing infrastructure
- create Docker Compose
- create README
- create architecture documentation
- create development commands

DO NOT:

- build the actual recovery algorithm
- train ML models
- build the real agent
- create the final UI
- implement real Razorpay actions
- populate a large dataset
- add unnecessary infrastructure
- invent additional product features

Every unfinished component should have a clear interface and TODO rather than fake functionality.

The next phase after foundation verification will be:

## PHASE 1 — SYNTHETIC REVENUE SIMULATOR

The simulator will be built before the main AI agent because the simulator provides the controlled environment and ground truth required to evaluate the system.