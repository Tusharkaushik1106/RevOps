KNOWLEDGE = [
    {
        "id": "KB-001",
        "title": "Gateway timeouts",
        "text": "A sustained increase in gateway timeout and network errors can indicate gateway degradation or routing/connectivity problems.",
        "type": "DOMAIN_KNOWLEDGE",
    },
    {
        "id": "KB-002",
        "title": "Issuer declines",
        "text": "Issuer decline increases concentrated by issuer should be compared with gateway and payment-method cohorts before selecting a hypothesis.",
        "type": "DOMAIN_KNOWLEDGE",
    },
    {
        "id": "KB-003",
        "title": "Card failures",
        "text": "Card authentication and issuer failures can affect card traffic without implying all payment methods are degraded.",
        "type": "DOMAIN_KNOWLEDGE",
    },
    {
        "id": "KB-004",
        "title": "Recovery routing",
        "text": "Routing affected traffic away from a degraded gateway is a candidate recommendation only when gateway-specific evidence is strong and an alternate route is healthy.",
        "type": "DOMAIN_KNOWLEDGE",
    },
    {
        "id": "KB-005",
        "title": "Retry semantics",
        "text": "Retries should be bounded and applied only to eligible failures after considering duplicate-action and customer-contact policies.",
        "type": "DOMAIN_KNOWLEDGE",
    },
]


def search_knowledge(query: str, limit: int = 3) -> list[dict]:
    terms = set(query.lower().split())
    return sorted(
        KNOWLEDGE, key=lambda d: len(terms & set(d["text"].lower().split())), reverse=True
    )[:limit]
