from collections import defaultdict


def gateway_metrics(
    payments: list[dict], dimensions: dict[str, str] | None = None
) -> dict[str, dict]:
    groups = defaultdict(list)
    for payment in payments:
        if dimensions and any(str(payment.get(k)) != v for k, v in dimensions.items()):
            continue
        groups[str(payment.get("gateway"))].append(payment)
    return {
        key: {
            "sample_size": len(rows),
            "success_rate": sum(row.get("status") == "success" for row in rows) / len(rows)
            if rows
            else 0,
            "transaction_value": sum(int(row.get("amount_minor", 0)) for row in rows),
        }
        for key, rows in groups.items()
    }
