from dataclasses import dataclass

from .pipeline import CanonicalBucketEngine
from .schemas import ObservableInput
from .session import DetectorSession


@dataclass
class ShadowObservation:
    bucket_start: object
    state: str
    trace: object


class SequentialShadowEvaluator:
    """Feeds buckets in order; hidden evaluation metadata is never passed to the detector."""

    def __init__(self, bucket_minutes=5):
        self.bucket_engine = CanonicalBucketEngine(bucket_minutes)

    def run(self, history: ObservableInput, evaluation: ObservableInput) -> list[ShadowObservation]:
        session = DetectorSession(self.bucket_engine.bucket_minutes)
        session.initialize([{**p, "event_type": "payment_attempted"} for p in history.payments])
        observations = []
        buckets = self.bucket_engine.build(evaluation.payments)
        for bucket in buckets:
            trace = session.ingest(bucket)
            observations.append(ShadowObservation(bucket.bucket_start, trace.state_after, trace))
        self.session = session
        return observations
