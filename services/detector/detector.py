from datetime import UTC, datetime, timedelta

from .aggregation import aggregate, bucket_payments
from .anomaly import score_signals
from .cohorts import rank_cohorts
from .revenue import revenue_at_risk
from .schemas import IncidentEvidencePacket, ObservableInput


class DetectorConfig:
    minimum_sample_size = 20
    minimum_deviation = 0.015
    minimum_persistence_buckets = 2
    window_minutes = 15


class IncidentDetector:
    def __init__(self, config: DetectorConfig | None = None):
        self.config = config or DetectorConfig()

    def detect(self, observable: ObservableInput) -> IncidentEvidencePacket:
        payments = observable.payments
        buckets = bucket_payments(payments, self.config.window_minutes)
        overall = aggregate(payments)
        candidates = []
        for timestamp, rows in buckets.items():
            current = aggregate(rows)
            delta = overall.success_rate - current.success_rate
            cohort_signal = max(
                (
                    self._cohort_delta(payments, rows, dimension)
                    for dimension in ("issuer", "gateway", "payment_method", "merchant_id")
                ),
                default=0,
            )
            if len(rows) >= self.config.minimum_sample_size and (
                delta >= self.config.minimum_deviation or cohort_signal >= 0.10
            ):
                candidates.append((timestamp, rows, current, max(delta, cohort_signal)))
        if not candidates:
            return IncidentEvidencePacket(
                incident_detected=False,
                confidence=0,
                baseline_metrics=overall,
                observed_metrics=overall,
                supporting_signals={"success_rate_deviation": "low", "persistence": "low"},
            )
        ordered = sorted(candidates, key=lambda x: x[0])
        runs = []
        current_run = [ordered[0]]
        for item in ordered[1:]:
            if item[0] - current_run[-1][0] <= timedelta(minutes=self.config.window_minutes):
                current_run.append(item)
            else:
                runs.append(current_run)
                current_run = [item]
        runs.append(current_run)
        strongest = max(runs, key=lambda run: (len(run), sum(x[3] for x in run)))
        start = strongest[0][0]
        end = strongest[-1][0] + timedelta(minutes=self.config.window_minutes)
        affected = [p for p in payments if start <= datetime.fromisoformat(p["timestamp"]) <= end]
        observed = aggregate(affected)
        baseline_rows = [
            p for p in payments if not start <= datetime.fromisoformat(p["timestamp"]) <= end
        ]
        baseline = (
            aggregate(baseline_rows)
            if len(baseline_rows) >= self.config.minimum_sample_size
            else overall
        )
        persistence = min(1, len(candidates) / max(1, len(buckets)))
        delta = baseline.success_rate - observed.success_rate
        score, signals = score_signals(
            delta,
            observed.failure_rate - baseline.failure_rate,
            (baseline.total_value_minor - observed.total_value_minor) / baseline.total_value_minor
            if baseline.total_value_minor
            else 0,
            persistence,
            min(1, len(affected) / 100),
        )
        return IncidentEvidencePacket(
            incident_detected=score >= 0.35,
            confidence=score,
            detection_timestamp=datetime.now(UTC),
            incident_window={
                "possible_start": start,
                "confirmed_start": start,
                "end": end,
                "duration_minutes": int((end - start).total_seconds() / 60),
            },
            baseline_metrics=baseline,
            observed_metrics=observed,
            anomaly_metrics={
                "success_rate_delta": delta,
                "failure_rate_delta": observed.failure_rate - baseline.failure_rate,
                "persistence": persistence,
            },
            affected_cohorts=rank_cohorts(baseline_rows, affected),
            revenue_impact=revenue_at_risk(
                baseline, observed, int((end - start).total_seconds() / 60)
            ),
            supporting_signals=signals,
        )

    @staticmethod
    def _cohort_delta(all_rows: list[dict], bucket_rows: list[dict], dimension: str) -> float:
        values = {str(row.get(dimension)) for row in bucket_rows if row.get(dimension) is not None}
        deltas = []
        for value in values:
            base = [row for row in all_rows if str(row.get(dimension)) == value]
            current = [row for row in bucket_rows if str(row.get(dimension)) == value]
            if len(current) >= 5:
                deltas.append(aggregate(base).success_rate - aggregate(current).success_rate)
        return max(deltas, default=0)
