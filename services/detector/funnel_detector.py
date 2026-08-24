from .pipeline import CanonicalBucketEngine
from .state import DetectorContext, IncidentStateMachine


class FunnelDetector:
    def __init__(self, bucket_minutes=5):
        self.engine = CanonicalBucketEngine(bucket_minutes)
        self.machine = IncidentStateMachine()

    def process(self, events: list[dict]):
        buckets = self.engine.build(events)
        context = DetectorContext()
        output = []
        for bucket in buckets:
            starts = [e for e in bucket.events if e.get("event_type") == "checkout_started"]
            abandoned = {
                e.get("payment_id")
                for e in bucket.events
                if e.get("event_type") == "checkout_abandoned"
            }
            rate = len(abandoned) / len(starts) if starts else 0
            context = self.machine.observe(
                context, min(1, rate * 4) if len(starts) >= 10 else 0, bucket.bucket_start
            )
            output.append(
                {
                    "bucket": bucket,
                    "abandonment_rate": rate,
                    "started": len(starts),
                    "state": context.state,
                }
            )
        return output
