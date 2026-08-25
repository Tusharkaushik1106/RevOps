from .pipeline import AggregateEngine, CanonicalBucketEngine
from .schemas import ConfirmationTrace, ObservableInput
from .state import DetectorContext, IncidentStateMachine


class PaymentDetector:
    def __init__(self, bucket_minutes=5):
        self.buckets = CanonicalBucketEngine(bucket_minutes)
        self.aggregates = AggregateEngine()
        self.machine = IncidentStateMachine()

    def process(self, observable: ObservableInput):
        payments = [
            {
                **p,
                "event_type": "payment_attempted",
                "attributes": {
                    "issuer": p.get("issuer"),
                    "gateway": p.get("gateway"),
                    "payment_method": p.get("payment_method"),
                    "device_type": p.get("device_type"),
                    "geo": p.get("geo"),
                    "failure_code": p.get("failure_code"),
                },
            }
            for p in observable.payments
        ]
        buckets = self.buckets.build(payments)
        index = self.aggregates.build(buckets)
        context = DetectorContext()
        packets = []
        self.traces = []
        history = []
        for bucket in buckets:
            aggregate = index.by_bucket[bucket.bucket_id]
            baseline = sum(history) / len(history) if history else None
            score = (
                0
                if aggregate.transaction_count < 20 or baseline is None
                else min(1, max(0, (baseline - aggregate.success_rate) * 5))
            )
            state_before = context.state.value
            context = self.machine.observe(context, score, bucket.bucket_start)
            packets.append((bucket, context.model_copy(deep=True)))
            self.traces.append(
                ConfirmationTrace(
                    bucket_start=bucket.bucket_start,
                    state_before=state_before,
                    state_after=context.state.value,
                    global_success_rate=aggregate.success_rate,
                    baseline_success_rate=baseline,
                    baseline_confidence="high" if len(history) >= 3 else "insufficient",
                    global_deviation=(baseline - aggregate.success_rate)
                    if baseline is not None
                    else 0,
                    sample_size=aggregate.transaction_count,
                    persistence_count=context.persistence_buckets,
                    confidence_components={
                        "history_buckets": float(len(history)),
                        "current_score": score,
                    },
                )
            )
            if aggregate.transaction_count:
                history.append(aggregate.success_rate)
        return packets
