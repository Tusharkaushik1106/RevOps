from pydantic import BaseModel, Field

from .pipeline import Aggregate
from .schemas import CohortEvidence


class InteractionEvidence(BaseModel):
    dimensions: tuple[str, str]
    values: tuple[str, str]
    sample_size: int
    baseline: float
    observed: float
    excess_failures: float
    excess_failed_value: int
    contribution: float
    interaction_advantage: float
    evidence_score: float


class AttributionResult(BaseModel):
    top_cohorts: list[CohortEvidence] = Field(default_factory=list)
    top_interactions: list[InteractionEvidence] = Field(default_factory=list)
    incident_excess_failed_value: int = 0
    coverage: float = 0
    confidence: float = 0


class IncidentAttributor:
    DIMENSIONS = ("issuer", "gateway", "payment_method", "merchant_id")
    INTERACTIONS = (
        ("issuer", "payment_method"),
        ("issuer", "gateway"),
        ("gateway", "payment_method"),
    )

    def __init__(
        self,
        historical: dict[str, dict[str, Aggregate]],
        minimum_sample=8,
        minimum_excess_value=1000,
    ):
        self.historical = historical
        self.minimum_sample = minimum_sample
        self.minimum_excess_value = minimum_excess_value
        self.incident = {
            d: {}
            for d in (
                *self.DIMENSIONS,
                "issuer__payment_method",
                "issuer__gateway",
                "gateway__payment_method",
            )
        }

    def update(self, current: dict[str, dict[str, Aggregate]]) -> AttributionResult:
        for dimension, values in current.items():
            for value, metric in values.items():
                self._add(self.incident[dimension].setdefault(value, Aggregate()), metric)
        candidates = []
        total = 0
        for dimension in self.DIMENSIONS:
            for value, metric in self.incident[dimension].items():
                baseline = self.historical.get(dimension, {}).get(value, Aggregate())
                expected = metric.transaction_count * baseline.success_rate
                excess = max(0, expected - metric.success_count)
                excess_value = max(
                    0,
                    round(metric.transaction_value * baseline.success_rate)
                    - metric.successful_value,
                )
                total += excess_value
                if (
                    metric.transaction_count >= self.minimum_sample
                    and excess_value >= self.minimum_excess_value
                ):
                    candidates.append(
                        (dimension, value, metric, baseline, expected, excess, excess_value)
                    )
        cohorts = []
        for dimension, value, metric, baseline, expected, excess, excess_value in candidates:
            contribution = excess_value / total if total else 0
            delta = baseline.success_rate - metric.success_rate
            score = (
                0.55 * contribution
                + 0.3 * min(1, delta / 0.25)
                + 0.15 * min(1, metric.transaction_count / 100)
            )
            cohorts.append(
                CohortEvidence(
                    dimension=dimension,
                    value=value,
                    sample_size=metric.transaction_count,
                    baseline_metric=baseline.success_rate,
                    observed_metric=metric.success_rate,
                    absolute_delta=delta,
                    relative_delta=delta / baseline.success_rate if baseline.success_rate else 0,
                    revenue_exposure_minor=metric.failed_value,
                    evidence_score=score,
                    expected_affected_volume=round(expected),
                    excess_failures=excess,
                    effect_size=delta,
                    economic_contribution=contribution,
                    significance="strong" if delta >= 0.08 else "moderate",
                )
            )
        interactions = []
        for d1, d2 in self.INTERACTIONS:
            for value, metric in self.incident[f"{d1}__{d2}"].items():
                v1, v2 = value.split("|", 1)
                baseline = self.historical.get(f"{d1}__{d2}", {}).get(value, Aggregate())
                excess = max(
                    0, metric.transaction_count * baseline.success_rate - metric.success_count
                )
                excess_value = max(
                    0,
                    round(metric.transaction_value * baseline.success_rate)
                    - metric.successful_value,
                )
                if (
                    metric.transaction_count >= self.minimum_sample
                    and excess_value >= self.minimum_excess_value
                ):
                    interactions.append(
                        InteractionEvidence(
                            dimensions=(d1, d2),
                            values=(v1, v2),
                            sample_size=metric.transaction_count,
                            baseline=baseline.success_rate,
                            observed=metric.success_rate,
                            excess_failures=excess,
                            excess_failed_value=excess_value,
                            contribution=excess_value / total if total else 0,
                            interaction_advantage=excess_value / total if total else 0,
                            evidence_score=excess_value / total if total else 0,
                        )
                    )
        cohorts.sort(key=lambda x: (x.economic_contribution, x.evidence_score), reverse=True)
        interactions.sort(key=lambda x: x.evidence_score, reverse=True)
        return AttributionResult(
            top_cohorts=cohorts[:10],
            top_interactions=interactions[:10],
            incident_excess_failed_value=total,
            coverage=sum(x.economic_contribution for x in cohorts),
            confidence=min(1, sum(x.evidence_score for x in cohorts)),
        )

    @staticmethod
    def _add(target, source):
        target.transaction_count += source.transaction_count
        target.success_count += source.success_count
        target.failure_count += source.failure_count
        target.transaction_value += source.transaction_value
        target.successful_value += source.successful_value
        target.failed_value += source.failed_value
