from collections import Counter

from .domain import Payment, PaymentStatus


def summarize(payments: list[Payment]) -> dict:
    total = len(payments)
    return {
        "payment_count": total,
        "success_rate": sum(p.status == PaymentStatus.SUCCESS for p in payments) / total
        if total
        else 0,
        "failure_rate": sum(p.status == PaymentStatus.FAILED for p in payments) / total
        if total
        else 0,
        "average_transaction_value_minor": sum(p.amount_minor for p in payments) / total
        if total
        else 0,
        "payment_method_distribution": dict(Counter(p.payment_method for p in payments)),
        "issuer_distribution": dict(Counter(p.issuer for p in payments)),
        "gateway_distribution": dict(Counter(p.gateway for p in payments)),
        "merchant_distribution": dict(Counter(p.merchant_id for p in payments)),
    }
