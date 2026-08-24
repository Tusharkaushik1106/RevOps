from datetime import UTC, datetime, timedelta

from services.detector.pipeline import AggregateEngine, CanonicalBucketEngine


def test_canonical_engine_includes_empty_buckets():
    start = datetime(2025, 1, 1, tzinfo=UTC)
    events = [
        {"timestamp": start.isoformat(), "status": "success", "amount_minor": 100},
        {
            "timestamp": (start + timedelta(minutes=10)).isoformat(),
            "status": "failed",
            "amount_minor": 100,
        },
    ]
    buckets = CanonicalBucketEngine(5).build(events)
    assert len(buckets) == 3 and not buckets[1].events


def test_aggregate_engine_indexes_once():
    start = datetime(2025, 1, 1, tzinfo=UTC)
    events = [
        {
            "timestamp": start.isoformat(),
            "status": "success",
            "amount_minor": 100,
            "issuer": "hdfc",
            "event_type": "payment_attempted",
        }
    ]
    buckets = CanonicalBucketEngine().build(events)
    index = AggregateEngine().build(buckets)
    assert (
        index.by_bucket[buckets[0].bucket_id].successful_value == 100
        and "hdfc" in index.by_dimension["issuer"]
    )
