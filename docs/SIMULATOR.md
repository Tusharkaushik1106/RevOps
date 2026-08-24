# Synthetic simulator

The simulator uses a private `IncidentGroundTruth` collection and observable `Payment`/`PaymentEvent` collections. Events contain payment behavior and metadata only; injected causes are represented by changed outcomes during a configured time window.

`Simulator(seed).generate(payments_count, scenario=...)` creates reproducible merchants, repeated customers, skewed amounts, payment methods, issuers, gateways, and chronological events. Scenario definitions live in `config.py`. Revenue calculations use integer minor units in `money.py`.

JSON save/load and chronological replay are provided in `io.py`. The CLI is available through `python -m services.simulator`. Parquet support is intentionally deferred until the dependency policy is finalized.
