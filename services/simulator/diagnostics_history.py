from collections import defaultdict
from statistics import mean, median, pstdev


def metric_distribution(payments):
    groups = defaultdict(list)
    for p in payments:
        groups[p.timestamp.hour].append(1 if p.status.value == "success" else 0)
    return {
        str(k): {
            "mean": mean(v),
            "median": median(v),
            "stddev": pstdev(v) if len(v) > 1 else 0,
            "count": len(v),
        }
        for k, v in groups.items()
    }
