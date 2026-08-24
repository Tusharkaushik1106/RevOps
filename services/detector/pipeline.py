from datetime import datetime, timedelta

from pydantic import BaseModel, Field


class Bucket(BaseModel):
    bucket_id: str
    bucket_start: datetime
    bucket_end: datetime
    events: list[dict] = Field(default_factory=list)


class Aggregate(BaseModel):
    transaction_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    transaction_value: int = 0
    successful_value: int = 0
    failed_value: int = 0

    @property
    def success_rate(self):
        return self.success_count / self.transaction_count if self.transaction_count else 0


class IndexedAggregates(BaseModel):
    by_bucket: dict[str, Aggregate] = Field(default_factory=dict)
    by_dimension: dict[str, dict[str, dict[str, Aggregate]]] = Field(default_factory=dict)


class CanonicalBucketEngine:
    def __init__(self, bucket_minutes: int = 5):
        self.bucket_minutes = bucket_minutes

    def build(self, events: list[dict], timestamp_key="timestamp") -> list[Bucket]:
        if not events:
            return []
        times = [datetime.fromisoformat(e[timestamp_key]) for e in events]
        start = min(times).replace(second=0, microsecond=0)
        start = start - timedelta(minutes=start.minute % self.bucket_minutes)
        end = max(times)
        count = int((end - start).total_seconds() // (self.bucket_minutes * 60)) + 1
        buckets = [
            Bucket(
                bucket_id=f"bucket_{i:06d}",
                bucket_start=start + timedelta(minutes=i * self.bucket_minutes),
                bucket_end=start + timedelta(minutes=(i + 1) * self.bucket_minutes),
            )
            for i in range(count)
        ]
        for event, t in zip(events, times):
            buckets[int((t - start).total_seconds() // (self.bucket_minutes * 60))].events.append(
                event
            )
        return buckets


class AggregateEngine:
    DIMENSIONS = (
        "merchant_id",
        "issuer",
        "gateway",
        "payment_method",
        "device_type",
        "geo",
        "failure_code",
        "issuer__payment_method",
        "issuer__gateway",
        "gateway__payment_method",
    )

    def build(self, buckets: list[Bucket]) -> IndexedAggregates:
        result = IndexedAggregates(by_dimension={d: {} for d in self.DIMENSIONS})
        for bucket in buckets:
            overall = Aggregate()
            for event in bucket.events:
                if event.get("event_type") not in (None, "payment_attempted"):
                    continue
                status = event.get("status", event.get("attributes", {}).get("status"))
                amount = int(event.get("amount_minor", 0))
                overall.transaction_count += 1
                overall.transaction_value += amount
                overall.success_count += status == "success"
                overall.failure_count += status == "failed"
                overall.successful_value += amount if status == "success" else 0
                overall.failed_value += amount if status == "failed" else 0
                for dim in self.DIMENSIONS:
                    value = event.get(dim) or event.get("attributes", {}).get(dim)
                    attrs = event.get("attributes", {})
                    if dim == "issuer__payment_method":
                        value = f"{event.get('issuer') or attrs.get('issuer')}|{event.get('payment_method') or attrs.get('payment_method')}"
                    elif dim == "issuer__gateway":
                        value = f"{event.get('issuer') or attrs.get('issuer')}|{event.get('gateway') or attrs.get('gateway')}"
                    elif dim == "gateway__payment_method":
                        value = f"{event.get('gateway') or attrs.get('gateway')}|{event.get('payment_method') or attrs.get('payment_method')}"
                    if value is None:
                        continue
                    result.by_dimension[dim].setdefault(str(value), {}).setdefault(
                        bucket.bucket_id, Aggregate()
                    )
                    target = result.by_dimension[dim][str(value)][bucket.bucket_id]
                    target.transaction_count += 1
                    target.transaction_value += amount
                    target.success_count += status == "success"
                    target.failure_count += status == "failed"
                    target.successful_value += amount if status == "success" else 0
                    target.failed_value += amount if status == "failed" else 0
            result.by_bucket[bucket.bucket_id] = overall
        return result
