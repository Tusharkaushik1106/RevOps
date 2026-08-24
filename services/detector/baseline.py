from .aggregation import aggregate
from .schemas import MetricSnapshot


def estimate_baseline(rows: list[dict], minimum_sample_size: int = 20) -> MetricSnapshot:
    if len(rows) < minimum_sample_size:
        return MetricSnapshot()
    return aggregate(rows)
