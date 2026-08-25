# Phase 2.4 detector pipeline

The refactor introduces a canonical five-minute bucket axis, explicit empty buckets, and indexed aggregates. `CanonicalBucketEngine` owns time normalization; `AggregateEngine` builds bucket and dimension indexes in one pass. `PaymentDetector`, `FunnelDetector`, and `RenewalDetector` consume chronological buckets and update a state context without looking ahead.

The pipeline is ground-truth blind. Evaluation code remains the only place that may compare detector output with simulator truth. The indexed payment path processes 100,000 payments in approximately 3.5 seconds on the current laptop; the broader evaluation and attribution criteria still require calibration.
