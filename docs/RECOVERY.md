# Counterfactual recovery engine

Phase 4 simulates bounded recovery strategies without executing financial actions. `CounterfactualEngine` compares `NO_ACTION`, rerouting sweeps, eligible retries, and targeted cohort recovery using deterministic integer-minor-unit arithmetic. Every scenario carries explicit assumptions and a transparent risk score. Optimization selects the highest expected recovered revenue under a configured risk threshold.

Run the local demonstration with `python -m services.recovery --demo`. The demo uses a typed evidence packet fixture; it does not call Razorpay or mutate payment state.
