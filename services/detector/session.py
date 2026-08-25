from .attribution import AttributionResult, IncidentAttributor
from .pipeline import Aggregate, AggregateEngine, Bucket, CanonicalBucketEngine, IndexedAggregates
from .schemas import CohortEvidence, ConfirmationTrace
from .state import DetectorContext, IncidentStateMachine


class DetectorSession:
    """Incremental observable-only payment session; historical index is built once."""

    def __init__(self, bucket_minutes=5):
        self.bucket_engine = CanonicalBucketEngine(bucket_minutes)
        self.aggregate_engine = AggregateEngine()
        self.historical_index = IndexedAggregates()
        self.historical_cohorts = {
            d: {}
            for d in (
                "issuer",
                "gateway",
                "payment_method",
                "merchant_id",
                "issuer__payment_method",
                "issuer__gateway",
                "gateway__payment_method",
            )
        }
        self.context = DetectorContext()
        self.initialization_count = 0
        self.evaluation_count = 0
        self.traces = []
        self.history_rates = []
        self.machine = IncidentStateMachine()
        self.attributor = IncidentAttributor(self.historical_cohorts)
        self.latest_attribution = AttributionResult()
        self.latest_cohorts = []

    def initialize(self, history_events: list[dict]):
        self.historical_index = self.aggregate_engine.build(
            self.bucket_engine.build(history_events)
        )
        self.initialization_count += 1
        self.history_rates = [
            a.success_rate for a in self.historical_index.by_bucket.values() if a.transaction_count
        ]
        for dimension in self.historical_cohorts:
            for value, buckets in self.historical_index.by_dimension[dimension].items():
                total = Aggregate()
                for item in buckets.values():
                    self._add(total, item)
                self.historical_cohorts[dimension][value] = total

    def ingest(self, bucket: Bucket):
        current_index = self.aggregate_engine.build([bucket])
        current = current_index.by_bucket.get(bucket.bucket_id, Aggregate())
        baseline = sum(self.history_rates) / len(self.history_rates) if self.history_rates else None
        evidence = self._cohort_evidence(current_index)
        self.latest_cohorts = evidence
        cohort_score = max((e.evidence_score for e in evidence if e.sample_size >= 20), default=0)
        global_score = (
            0
            if baseline is None or current.transaction_count < 20
            else min(1, max(0, (baseline - current.success_rate) * 5))
        )
        # Detection confirmation is intentionally independent of attribution.
        # Cohort evidence is recorded for diagnostics and activated only after INCIDENT.
        score = global_score
        before = self.context.state.value
        self.context = self.machine.observe(self.context, score, bucket.bucket_start)
        self.evaluation_count += 1
        if self.context.state.value == "incident":
            self.latest_attribution = self.attributor.update(current_index.by_dimension)
        top = (
            self.latest_attribution.top_cohorts[0]
            if self.latest_attribution.top_cohorts
            else (evidence[0] if evidence else None)
        )
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
            top_affected_cohort=f"{top.dimension}={top.value}" if top else None,
            cohort_effect=top.effect_size if top else 0,
            cohort_contribution=top.economic_contribution if top else 0,
            confidence_components={
                "history_buckets": float(len(self.history_rates)),
                "current_score": score,
                "global_score": global_score,
                "cohort_score": cohort_score,
            },
        )
        self.traces.append(trace)
        self.history_rates.append(current.success_rate) if current.transaction_count else None
        self._update_history(current_index)
        return trace

    def _cohort_evidence(self, index):
        candidates = []
        total_excess = 0
        for dimension in self.historical_cohorts:
            for value, buckets in index.by_dimension[dimension].items():
                current = next(iter(buckets.values()), Aggregate())
                base = self.historical_cohorts[dimension].get(value, Aggregate())
                delta = base.success_rate - current.success_rate
                excess = max(
                    0, current.transaction_count * base.success_rate - current.success_count
                )
                excess_value = max(
                    0,
                    round(current.transaction_value * base.success_rate) - current.successful_value,
                )
                total_excess += excess_value
                if current.transaction_count >= 8 and delta > 0.02:
                    candidates.append(
                        (dimension, value, current, base, delta, excess, excess_value)
                    )
        output = []
        for dimension, value, current, base, delta, excess, excess_value in candidates:
            contribution = excess_value / total_excess if total_excess else 0
            evidence = (
                0.5 * contribution
                + 0.3 * min(1, delta / 0.25)
                + 0.2 * min(1, current.transaction_count / 50)
            )
            output.append(
                CohortEvidence(
                    dimension=dimension,
                    value=value,
                    sample_size=current.transaction_count,
                    baseline_metric=base.success_rate,
                    observed_metric=current.success_rate,
                    absolute_delta=delta,
                    relative_delta=delta / base.success_rate if base.success_rate else 0,
                    revenue_exposure_minor=current.failed_value,
                    evidence_score=evidence,
                    expected_affected_volume=round(current.transaction_count * base.success_rate),
                    excess_failures=excess,
                    effect_size=delta,
                    economic_contribution=contribution,
                    significance="strong"
                    if current.transaction_count >= 20 and delta >= 0.08
                    else "moderate",
                )
            )
        return sorted(
            output, key=lambda e: (e.economic_contribution, e.evidence_score), reverse=True
        )

    def _update_history(self, index):
        for dimension in self.historical_cohorts:
            for value, buckets in index.by_dimension[dimension].items():
                self._add(
                    self.historical_cohorts[dimension].setdefault(value, Aggregate()),
                    next(iter(buckets.values()), Aggregate()),
                )

    @staticmethod
    def _add(target, source):
        target.transaction_count += source.transaction_count
        target.success_count += source.success_count
        target.failure_count += source.failure_count
        target.transaction_value += source.transaction_value
        target.successful_value += source.successful_value
        target.failed_value += source.failed_value
