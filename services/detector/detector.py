from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .aggregation import aggregate, bucket_payments
from .cohorts import rank_cohorts
from .revenue import revenue_at_risk
from .schemas import DetectionState, IncidentEvidencePacket, MetricSnapshot, ObservableInput


class DetectorConfig:
    window_minutes = 15
    minimum_bucket_sample_size = 40
    minimum_affected_cohort_size = 8
    minimum_metric_deviation = 0.08
    minimum_revenue_exposure_minor = 10_000
    minimum_persistence_buckets = 3
    continuation_deviation = 0.05
    recovery_buckets = 2


class IncidentDetector:
    """Observable-only, persistence-aware detector. It never reads evaluator metadata."""

    def __init__(self, config: DetectorConfig | None = None):
        self.config = config or DetectorConfig()

    def detect(self, observable: ObservableInput) -> IncidentEvidencePacket:
        if any(event.get("event_type") == "checkout_started" for event in observable.events):
            return self._detect_checkout(observable)
        if any(event.get("event_type") == "renewal_attempted" for event in observable.events):
            return self._detect_renewal(observable)
        return self._detect_payments(observable)

    def _detect_payments(self, observable: ObservableInput) -> IncidentEvidencePacket:
        payments = observable.payments
        overall = aggregate(payments)
        buckets = bucket_payments(payments, self.config.window_minutes)
        dimensions = ("issuer", "gateway", "payment_method", "merchant_id")
        candidates = []
        for timestamp, rows in buckets.items():
            if len(rows) < self.config.minimum_bucket_sample_size:
                continue
            best = self._best_cohort_signal(payments, rows, dimensions)
            if (
                best
                and best[2] >= self.config.minimum_metric_deviation
                and best[1] >= self.config.minimum_affected_cohort_size
            ):
                candidates.append((timestamp, rows, best))
        run = self._strongest_run(candidates)
        if len(run) < self.config.minimum_persistence_buckets:
            return self._packet(DetectionState.NORMAL, overall, overall, {"persistence": "low"})
        start = run[0][0]
        end = run[-1][0] + timedelta(minutes=self.config.window_minutes)
        affected = [
            row for row in payments if start <= datetime.fromisoformat(row["timestamp"]) <= end
        ]
        before_after = [
            row for row in payments if not start <= datetime.fromisoformat(row["timestamp"]) <= end
        ]
        observed = aggregate(affected)
        baseline = (
            aggregate(before_after)
            if len(before_after) >= self.config.minimum_bucket_sample_size
            else overall
        )
        impact = revenue_at_risk(
            baseline, observed, max(1, int((end - start).total_seconds() / 60))
        )
        cohorts = rank_cohorts(before_after, affected)
        financial = min(
            1.0, impact.revenue_at_risk_minor / max(1, self.config.minimum_revenue_exposure_minor)
        )
        concentration = min(1.0, run[0][2][2] / 0.25)
        persistence = min(1.0, len(run) / max(1, self.config.minimum_persistence_buckets + 2))
        state = (
            DetectionState.INCIDENT
            if impact.revenue_at_risk_minor >= self.config.minimum_revenue_exposure_minor
            and cohorts
            and concentration >= 0.32
            else DetectionState.ANOMALY
        )
        confidence = min(
            1.0,
            0.35 * concentration
            + 0.3 * persistence
            + 0.2 * min(1, len(affected) / 200)
            + 0.15 * min(1, financial),
        )
        return IncidentEvidencePacket(
            state=state,
            incident_detected=state == DetectionState.INCIDENT,
            confidence=confidence,
            detection_timestamp=datetime.now(UTC),
            incident_window={
                "candidate_start": start,
                "confirmed_start": start,
                "candidate_end": end,
                "confirmed_end": end,
                "duration_minutes": int((end - start).total_seconds() / 60),
            },
            baseline_metrics=baseline,
            observed_metrics=observed,
            anomaly_metrics={
                "success_rate_delta": baseline.success_rate - observed.success_rate,
                "failure_rate_delta": observed.failure_rate - baseline.failure_rate,
                "persistence_buckets": float(len(run)),
            },
            affected_cohorts=cohorts,
            top_cohorts=cohorts[:5],
            revenue_impact=impact,
            supporting_signals={
                "cohort_concentration": "high" if concentration >= 0.7 else "medium",
                "persistence": "high" if persistence >= 0.7 else "medium",
                "financial_materiality": "high" if financial >= 1 else "medium",
            },
            diagnostics={
                "persistence_score": persistence,
                "sample_size_score": min(1, len(affected) / 200),
                "financial_materiality": min(1, financial),
                "cohort_concentration": concentration,
            },
        )

    def _detect_checkout(self, observable: ObservableInput) -> IncidentEvidencePacket:
        events = observable.events
        starts = [e for e in events if e.get("event_type") == "checkout_started"]
        abandoned = {
            e.get("payment_id") for e in events if e.get("event_type") == "checkout_abandoned"
        }
        baseline = [e for e in starts if e.get("payment_id") not in abandoned]
        observed = [e for e in starts if e.get("payment_id") in abandoned]
        rate = len(observed) / len(starts) if starts else 0
        baseline_rate = 0.05
        delta = rate - baseline_rate
        detected = len(starts) >= self.config.minimum_bucket_sample_size and delta >= 0.03
        snapshot = MetricSnapshot(
            transaction_count=len(starts),
            success_count=len(starts) - len(observed),
            failure_count=len(observed),
            success_rate=1 - rate,
            failure_rate=rate,
            total_value_minor=sum(int(e.get("amount_minor", 0)) for e in starts),
            successful_value_minor=sum(int(e.get("amount_minor", 0)) for e in baseline),
            failed_value_minor=sum(int(e.get("amount_minor", 0)) for e in observed),
        )
        return IncidentEvidencePacket(
            state=DetectionState.INCIDENT if detected else DetectionState.NORMAL,
            incident_detected=detected,
            confidence=min(1, abs(delta) * 4),
            detection_timestamp=datetime.now(UTC),
            baseline_metrics=snapshot,
            observed_metrics=snapshot,
            anomaly_metrics={"abandonment_delta": delta},
            revenue_impact=revenue_at_risk(snapshot, snapshot, 60),
            supporting_signals={"funnel_stage": "payment_page"},
            metric_kind="checkout_abandonment",
        )

    def _detect_renewal(self, observable: ObservableInput) -> IncidentEvidencePacket:
        attempts = [e for e in observable.events if e.get("event_type") == "renewal_attempted"]
        successes = [e for e in observable.events if e.get("event_type") == "renewal_success"]
        observed_rate = len(successes) / len(attempts) if attempts else 0
        baseline_rate = 0.94
        delta = baseline_rate - observed_rate
        total = sum(int(e.get("amount_minor", 0)) for e in attempts)
        success_value = sum(int(e.get("amount_minor", 0)) for e in successes)
        snap = MetricSnapshot(
            transaction_count=len(attempts),
            success_count=len(successes),
            failure_count=len(attempts) - len(successes),
            success_rate=observed_rate,
            failure_rate=1 - observed_rate,
            total_value_minor=total,
            successful_value_minor=success_value,
            failed_value_minor=total - success_value,
        )
        base = snap.model_copy(
            update={
                "success_rate": baseline_rate,
                "successful_value_minor": round(total * baseline_rate),
            }
        )
        detected = len(attempts) >= 20 and delta >= 0.02
        return IncidentEvidencePacket(
            state=DetectionState.INCIDENT if detected else DetectionState.NORMAL,
            incident_detected=detected,
            confidence=min(1, delta * 4),
            detection_timestamp=datetime.now(UTC),
            baseline_metrics=base,
            observed_metrics=snap,
            anomaly_metrics={"renewal_success_delta": delta},
            revenue_impact=revenue_at_risk(base, snap, 60),
            supporting_signals={"renewal_success": "high" if delta >= 0.15 else "medium"},
            metric_kind="subscription_renewal",
        )

    def _best_cohort_signal(self, all_rows, rows, dimensions):
        best = None
        for dimension in dimensions:
            values = {str(row.get(dimension)) for row in rows if row.get(dimension) is not None}
            for value in values:
                cohort = [row for row in rows if str(row.get(dimension)) == value]
                baseline = [row for row in all_rows if str(row.get(dimension)) == value]
                delta = aggregate(baseline).success_rate - aggregate(cohort).success_rate
                if len(cohort) >= self.config.minimum_affected_cohort_size and (
                    best is None or delta > best[2]
                ):
                    best = (dimension, len(cohort), delta, value)
        return best

    def _strongest_run(self, candidates):
        if not candidates:
            return []
        groups = defaultdict(list)
        for item in candidates:
            groups[(item[2][0], item[2][3])].append(item)
        runs = []
        for group in groups.values():
            group.sort(key=lambda x: x[0])
            current = [group[0]]
            for item in group[1:]:
                if item[0] - current[-1][0] <= timedelta(minutes=self.config.window_minutes):
                    current.append(item)
                else:
                    runs.append(current)
                    current = [item]
            runs.append(current)
        return max(runs, key=lambda x: (len(x), sum(i[2][2] for i in x)), default=[])

    @staticmethod
    def _packet(state, baseline, observed, signals):
        return IncidentEvidencePacket(
            state=state,
            incident_detected=False,
            confidence=0,
            baseline_metrics=baseline,
            observed_metrics=observed,
            supporting_signals=signals,
        )
