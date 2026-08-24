import math


def z_score(observed: float, expected: float, sample_size: int) -> float:
    if sample_size <= 1 or expected in (0, 1):
        return 0.0
    standard_error = math.sqrt(expected * (1 - expected) / sample_size)
    return (observed - expected) / standard_error if standard_error else 0.0


def score_signals(
    rate_delta: float,
    failure_delta: float,
    revenue_delta: float,
    persistence: float,
    sample_factor: float,
) -> tuple[float, dict[str, str]]:
    components = {
        "success_rate_deviation": "high"
        if rate_delta >= 0.10
        else "medium"
        if rate_delta >= 0.05
        else "low",
        "failure_rate_deviation": "high"
        if failure_delta >= 0.10
        else "medium"
        if failure_delta >= 0.05
        else "low",
        "revenue_exposure": "high"
        if revenue_delta >= 0.10
        else "medium"
        if revenue_delta >= 0.03
        else "low",
        "persistence": "high" if persistence >= 0.8 else "medium" if persistence >= 0.4 else "low",
        "sample_size": "high" if sample_factor >= 1 else "medium",
    }
    return min(
        1.0,
        max(
            0.0,
            0.35 * min(1, rate_delta / 0.2)
            + 0.2 * min(1, failure_delta / 0.2)
            + 0.2 * min(1, revenue_delta / 0.3)
            + 0.15 * persistence
            + 0.1 * sample_factor,
        ),
    ), components
