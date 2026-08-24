from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PaymentMethod(StrEnum):
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"


class Issuer(StrEnum):
    HDFC = "hdfc"
    ICICI = "icici"
    SBI = "sbi"
    AXIS = "axis"
    KOTAK = "kotak"
    OTHER = "other"


class Gateway(StrEnum):
    GATEWAY_A = "gateway_a"
    GATEWAY_B = "gateway_b"
    GATEWAY_C = "gateway_c"


class PaymentStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class FailureCode(StrEnum):
    ISSUER_DECLINE = "issuer_decline"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    TIMEOUT = "timeout"
    GATEWAY_ERROR = "gateway_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_FAILURE = "authentication_failure"
    PAYMENT_METHOD_UNAVAILABLE = "payment_method_unavailable"
    UNKNOWN = "unknown"


class EventType(StrEnum):
    CHECKOUT_STARTED = "checkout_started"
    PAYMENT_PAGE_VIEWED = "payment_page_viewed"
    PAYMENT_ATTEMPTED = "payment_attempted"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    CHECKOUT_ABANDONED = "checkout_abandoned"
    RENEWAL_ATTEMPTED = "renewal_attempted"
    RENEWAL_SUCCESS = "renewal_success"
    RENEWAL_FAILED = "renewal_failed"


class IncidentType(StrEnum):
    ISSUER_DEGRADATION = "issuer_degradation"
    GATEWAY_DEGRADATION = "gateway_degradation"
    PAYMENT_METHOD_DEGRADATION = "payment_method_degradation"
    MERCHANT_DEGRADATION = "merchant_specific_degradation"
    CHECKOUT_ABANDONMENT = "checkout_abandonment_spike"
    SUBSCRIPTION_RENEWAL = "subscription_renewal_degradation"


class Merchant(BaseModel):
    merchant_id: str
    name: str
    category: str
    baseline_daily_volume: int
    average_order_value_minor: int
    payment_method_distribution: dict[PaymentMethod, float]
    gateway_distribution: dict[Gateway, float]
    subscription_share: float


class Customer(BaseModel):
    customer_id: str
    merchant_id: str
    created_at: datetime
    lifetime_value_minor: int
    transaction_frequency: float
    preferred_payment_method: PaymentMethod
    device_type: str
    geo: str
    subscription_status: str


class Order(BaseModel):
    order_id: str
    merchant_id: str
    customer_id: str
    created_at: datetime
    amount_minor: int
    currency: str = "INR"


class Subscription(BaseModel):
    subscription_id: str
    merchant_id: str
    customer_id: str
    amount_minor: int
    billing_interval: str
    next_billing_at: datetime
    status: str = "active"


class Payment(BaseModel):
    payment_id: str
    merchant_id: str
    customer_id: str
    order_id: str
    timestamp: datetime
    amount_minor: int
    currency: str
    payment_method: PaymentMethod
    issuer: Issuer
    gateway: Gateway
    device_type: str
    geo: str
    failure_code: FailureCode | None
    status: PaymentStatus
    attempt_number: int = 1
    subscription_id: str | None = None


class PaymentEvent(BaseModel):
    event_id: str
    event_type: EventType
    timestamp: datetime
    payment_id: str | None = None
    merchant_id: str | None = None
    customer_id: str | None = None
    amount_minor: int = 0
    attributes: dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    incident_id: str
    incident_type: IncidentType
    start_time: datetime
    end_time: datetime
    severity: str
    affected_dimensions: dict[str, str]
    parameters: dict[str, Any] = Field(default_factory=dict)


class IncidentGroundTruth(BaseModel):
    incident_id: str
    incident_type: IncidentType
    actual_root_cause: str
    affected_dimensions: dict[str, str]
    affected_cohort: dict[str, str]
    start_time: datetime
    end_time: datetime
    severity: str
    baseline_expected_success: float
    incident_success: float
    affected_transaction_count: int
    baseline_expected_revenue_minor: int
    observed_revenue_minor: int
    revenue_exposure_minor: int
    revenue_loss_minor: int


class Intervention(BaseModel):
    intervention_id: str
    payment_id: str
    action: str
    timestamp: datetime


class InterventionOutcome(BaseModel):
    intervention_id: str
    success: bool
    recovered_amount_minor: int
    observed_at: datetime


class SimulationResult(BaseModel):
    merchants: list[Merchant] = Field(default_factory=list)
    customers: list[Customer] = Field(default_factory=list)
    orders: list[Order] = Field(default_factory=list)
    payments: list[Payment] = Field(default_factory=list)
    events: list[PaymentEvent] = Field(default_factory=list)
    subscriptions: list[Subscription] = Field(default_factory=list)
    incidents: list[Incident] = Field(default_factory=list)
    ground_truth: list[IncidentGroundTruth] = Field(default_factory=list)
