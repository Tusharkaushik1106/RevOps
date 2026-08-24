from .aggregation import aggregate
from .schemas import CohortEvidence

DIMENSIONS = (
    "issuer",
    "gateway",
    "payment_method",
    "merchant_id",
    "geo",
    "device_type",
    "failure_code",
)


def rank_cohorts(
    baseline_rows: list[dict], observed_rows: list[dict], dimension_names=DIMENSIONS
) -> list[CohortEvidence]:
    output = []
    for dimension in dimension_names:
        values = {str(r.get(dimension)) for r in observed_rows if r.get(dimension) is not None}
        for value in values:
            base = aggregate([r for r in baseline_rows if str(r.get(dimension)) == value])
            obs = aggregate([r for r in observed_rows if str(r.get(dimension)) == value])
            delta = base.success_rate - obs.success_rate
            if obs.transaction_count >= 20 and delta > 0.02:
                output.append(
                    CohortEvidence(
                        dimension=dimension,
                        value=value,
                        sample_size=obs.transaction_count,
                        baseline_metric=base.success_rate,
                        observed_metric=obs.success_rate,
                        absolute_delta=delta,
                        relative_delta=delta / base.success_rate if base.success_rate else 0,
                        revenue_exposure_minor=obs.failed_value_minor,
                        evidence_score=min(1, delta * 3) * min(1, obs.transaction_count / 100),
                    )
                )
    return sorted(output, key=lambda x: x.evidence_score, reverse=True)
