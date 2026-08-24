from .schemas import MetricSnapshot, RevenueImpact


def revenue_at_risk(
    baseline: MetricSnapshot, observed: MetricSnapshot, duration_minutes: int
) -> RevenueImpact:
    loss_per_window = max(0, baseline.successful_value_minor - observed.successful_value_minor)
    velocity = round(loss_per_window / duration_minutes) if duration_minutes else 0
    return RevenueImpact(
        revenue_at_risk_minor=loss_per_window,
        revenue_at_risk_per_minute_minor=velocity,
        revenue_at_risk_per_hour_minor=velocity * 60,
        gross_affected_value_minor=observed.total_value_minor,
        observed_successful_value_minor=observed.successful_value_minor,
        expected_successful_value_minor=baseline.successful_value_minor,
    )
