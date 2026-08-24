def expected_revenue(amounts: list[int], rate: float) -> int:
    return round(sum(amounts) * rate)


def observed_revenue(amounts: list[int]) -> int:
    return sum(amounts)


def revenue_loss(baseline: int, observed: int) -> int:
    return max(0, baseline - observed)


def revenue_exposure(amounts: list[int]) -> int:
    return sum(amounts)
