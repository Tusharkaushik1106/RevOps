from .pipeline import Aggregate, AggregateEngine, Bucket, CanonicalBucketEngine, IndexedAggregates
from .schemas import ConfirmationTrace
from .state import DetectorContext, IncidentStateMachine


class DetectorSession:
    """Incremental observable-only payment session; historical index is built once."""

    def __init__(self, bucket_minutes=5):
        self.bucket_engine = CanonicalBucketEngine(bucket_minutes)
        self.aggregate_engine = AggregateEngine()
        self.historical_index = IndexedAggregates()
        self.context = DetectorContext()
        self.initialization_count = 0
        self.evaluation_count = 0
        self.traces = []
        self.history_rates = []
        self.machine = IncidentStateMachine()

    def initialize(self, history_events: list[dict]):
        self.historical_index = self.aggregate_engine.build(
            self.bucket_engine.build(history_events)
        )
        self.initialization_count += 1
        self.history_rates = [
            a.success_rate for a in self.historical_index.by_bucket.values() if a.transaction_count
        ]

    def ingest(self, bucket: Bucket):
        current = self.aggregate_engine.build([bucket]).by_bucket.get(bucket.bucket_id, Aggregate())
        baseline = sum(self.history_rates) / len(self.history_rates) if self.history_rates else None
        score = (
            0
            if baseline is None or current.transaction_count < 20
            else min(1, max(0, (baseline - current.success_rate) * 5))
        )
        before = self.context.state.value
        self.context = self.machine.observe(self.context, score, bucket.bucket_start)
        self.evaluation_count += 1
        trace = ConfirmationTrace(
            bucket_start=bucket.bucket_start,
            state_before=before,
            state_after=self.context.state.value,
            global_success_rate=current.success_rate,
            baseline_success_rate=baseline,
            baseline_confidence="high" if len(self.history_rates) >= 3 else "insufficient",
            global_deviation=(baseline - current.success_rate) if baseline is not None else 0,
            sample_size=current.transaction_count,
            persistence_count=self.context.persistence_buckets,
            financial_materiality_minor=current.failed_value,
            confidence_components={
                "history_buckets": float(len(self.history_rates)),
                "current_score": score,
            },
        )
        self.traces.append(trace)
        self.history_rates.append(current.success_rate) if current.transaction_count else None
        return trace
