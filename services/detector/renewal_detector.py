from .pipeline import CanonicalBucketEngine
from .state import DetectorContext, IncidentStateMachine


class RenewalDetector:
    def __init__(self, bucket_minutes=5):
        self.engine = CanonicalBucketEngine(bucket_minutes)
        self.machine = IncidentStateMachine()

    def process(self, events: list[dict]):
        buckets = self.engine.build(events)
        context = DetectorContext()
        output = []
        for bucket in buckets:
            attempts = [e for e in bucket.events if e.get("event_type") == "renewal_attempted"]
            successes = [e for e in bucket.events if e.get("event_type") == "renewal_success"]
            rate = len(successes) / len(attempts) if attempts else 0
            score = min(1, max(0, (0.94 - rate) * 4)) if len(attempts) >= 5 else 0
            context = self.machine.observe(context, score, bucket.bucket_start)
            output.append(
                {
                    "bucket": bucket,
                    "attempts": len(attempts),
                    "successes": len(successes),
                    "success_rate": rate,
                    "state": context.state,
                }
            )
        return output
