# Detector hardening

The detector is a deterministic quantitative boundary. It consumes observable payment and funnel events only; simulator evaluator metadata is not part of detector execution.

The lifecycle context supports `NORMAL`, `ANOMALY`, `INCIDENT`, and `RECOVERING`. Confirmation requires repeated evidence; recovery requires repeated weak evidence. `IncidentEvidencePacket` exposes diagnostics and ranked cohorts without making causal claims.

Payment cohort ranking combines deviation, sample size, excess failures, failed value, and economic contribution. A large economically meaningful cohort can therefore outrank a tiny cohort with a larger percentage change.

Checkout and renewal events have dedicated detector paths and are not routed through generic payment success-rate logic. Further bucket-level funnel and renewal calibration remains an explicit follow-up before Phase 3.
