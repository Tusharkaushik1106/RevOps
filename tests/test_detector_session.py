from datetime import UTC, datetime

from services.detector.pipeline import CanonicalBucketEngine
from services.detector.session import DetectorSession


def test_session_initializes_index_once_and_ingests_incrementally():
    start = datetime(2025, 1, 1, tzinfo=UTC)
    row = {"timestamp": start.isoformat(), "status": "success", "amount_minor": 100}
    session = DetectorSession()
    session.initialize([row])
    buckets = CanonicalBucketEngine().build([row])
    [session.ingest(b) for b in buckets]
    assert session.initialization_count == 1 and session.evaluation_count == 1
