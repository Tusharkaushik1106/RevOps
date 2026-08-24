from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DetectorState(StrEnum):
    NORMAL = "normal"
    ANOMALY = "anomaly"
    INCIDENT = "incident"
    RECOVERING = "recovering"


class DetectorContext(BaseModel):
    state: DetectorState = DetectorState.NORMAL
    candidate_start: datetime | None = None
    confirmed_start: datetime | None = None
    candidate_recovery_start: datetime | None = None
    confirmed_end: datetime | None = None
    persistence_buckets: int = 0
    recovery_buckets: int = 0
    previous_scores: list[float] = Field(default_factory=list)
    top_cohorts: list[dict] = Field(default_factory=list)


class StateMachineConfig(BaseModel):
    confirmation_buckets: int = 3
    recovery_buckets: int = 2
    continue_threshold: float = 0.35
    recovery_threshold: float = 0.20


class IncidentStateMachine:
    def __init__(self, config: StateMachineConfig | None = None):
        self.config = config or StateMachineConfig()

    def observe(
        self, context: DetectorContext, score: float, timestamp: datetime
    ) -> DetectorContext:
        context.previous_scores.append(score)
        if context.state == DetectorState.NORMAL and score >= self.config.continue_threshold:
            context.state = DetectorState.ANOMALY
            context.candidate_start = timestamp
            context.persistence_buckets = 1
        elif context.state == DetectorState.ANOMALY:
            if score >= self.config.continue_threshold:
                context.persistence_buckets += 1
                if context.persistence_buckets >= self.config.confirmation_buckets:
                    context.state = DetectorState.INCIDENT
                    context.confirmed_start = context.candidate_start
            else:
                context.state = DetectorState.NORMAL
                context.candidate_start = None
                context.persistence_buckets = 0
        elif context.state == DetectorState.INCIDENT and score < self.config.recovery_threshold:
            context.state = DetectorState.RECOVERING
            context.candidate_recovery_start = timestamp
            context.recovery_buckets = 1
        elif context.state == DetectorState.RECOVERING:
            if score >= self.config.continue_threshold:
                context.state = DetectorState.INCIDENT
                context.recovery_buckets = 0
            else:
                context.recovery_buckets += 1
                if context.recovery_buckets >= self.config.recovery_buckets:
                    context.state = DetectorState.NORMAL
                    context.confirmed_end = timestamp
        return context
