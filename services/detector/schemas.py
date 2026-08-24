from datetime import datetime

from pydantic import BaseModel, Field


class ObservableInput(BaseModel):
    payments: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)


class MetricSnapshot(BaseModel):
    transaction_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0
    failure_rate: float = 0
    total_value_minor: int = 0
    successful_value_minor: int = 0
    failed_value_minor: int = 0


class CohortEvidence(BaseModel):
    dimension: str
    value: str
    sample_size: int
    baseline_metric: float
    observed_metric: float
    absolute_delta: float
    relative_delta: float
    revenue_exposure_minor: int
    evidence_score: float


class RevenueImpact(BaseModel):
    revenue_at_risk_minor: int = 0
    revenue_at_risk_per_minute_minor: int = 0
    revenue_at_risk_per_hour_minor: int = 0
    gross_affected_value_minor: int = 0
    observed_successful_value_minor: int = 0
    expected_successful_value_minor: int = 0


class IncidentEvidencePacket(BaseModel):
    incident_detected: bool
    confidence: float
    detection_timestamp: datetime | None = None
    incident_window: dict[str, datetime | int | None] = Field(default_factory=dict)
    baseline_metrics: MetricSnapshot
    observed_metrics: MetricSnapshot
    anomaly_metrics: dict[str, float] = Field(default_factory=dict)
    affected_cohorts: list[CohortEvidence] = Field(default_factory=list)
    revenue_impact: RevenueImpact = Field(default_factory=RevenueImpact)
    supporting_signals: dict[str, str] = Field(default_factory=dict)
    detector_version: str = "phase2-statistical-v1"
    metric_kind: str = "payment_success"
