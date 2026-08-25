# Phase 2 evaluation

`python -m services.detector evaluate --payments 2000` is the single audit entry point for clean baselines, calibrated canonical incidents, and scenario-world construction. Detector runtime receives observable data only; hidden truth is retained by evaluator-side objects and is never passed into detector constructors or sessions.

The evaluation report is intentionally diagnostic. A passing test suite does not imply Phase 2 readiness: acceptance requires clean-baseline precision, stable cohort attribution, funnel/renewal validation, lifecycle metrics, window metrics, and performance measurements.
