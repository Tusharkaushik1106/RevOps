from pydantic import BaseModel

class PolicyInput(BaseModel):
    action: dict
    retry_count: int = 0
    customer_contacts: int = 0
    action_amount_minor: int = 0
    discount_percent: float = 0
    duplicate: bool = False

class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    requires_human_approval: bool = False

class SafeDefaultPolicy:
    def evaluate(self, value: PolicyInput) -> PolicyDecision:
        if value.duplicate:
            return PolicyDecision(allowed=False, reason="duplicate action")
        return PolicyDecision(allowed=False, reason="no automatic actions enabled in Phase 0")
