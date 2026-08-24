from collections import defaultdict
from datetime import datetime, timedelta

from .schemas import MetricSnapshot


def _snapshot(rows: list[dict]) -> MetricSnapshot:
    success = sum(r.get("status") == "success" for r in rows)
    failed = sum(r.get("status") == "failed" for r in rows)
    total = len(rows)
    value = sum(int(r.get("amount_minor", 0)) for r in rows)
    successful_value = sum(
        int(r.get("amount_minor", 0)) for r in rows if r.get("status") == "success"
    )
    return MetricSnapshot(
        transaction_count=total,
        success_count=success,
        failure_count=failed,
        success_rate=success / total if total else 0,
        failure_rate=failed / total if total else 0,
        total_value_minor=value,
        successful_value_minor=successful_value,
        failed_value_minor=value - successful_value,
    )


def bucket_payments(payments: list[dict], window_minutes: int = 15) -> dict[datetime, list[dict]]:
    if not payments:
        return {}
    origin = min(datetime.fromisoformat(p["timestamp"]) for p in payments)
    size = timedelta(minutes=window_minutes)
    buckets = defaultdict(list)
    for payment in payments:
        timestamp = datetime.fromisoformat(payment["timestamp"])
        bucket = origin + ((timestamp - origin) // size) * size
        buckets[bucket].append(payment)
    return dict(sorted(buckets.items()))


def aggregate(payments: list[dict]) -> MetricSnapshot:
    return _snapshot(payments)
