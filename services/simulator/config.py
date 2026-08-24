from pydantic import BaseModel

from .domain import Gateway, IncidentType, Issuer, PaymentMethod


class ScenarioConfig(BaseModel):
    incident_type: IncidentType
    target: str | None = None
    severity: str = "high"
    incident_success_rate: float = 0.78
    start_fraction: float = 0.45
    duration_fraction: float = 0.2
    abandonment_multiplier: float = 2.0


SCENARIOS = {
    IncidentType.ISSUER_DEGRADATION: ScenarioConfig(
        incident_type=IncidentType.ISSUER_DEGRADATION, target=Issuer.HDFC
    ),
    IncidentType.GATEWAY_DEGRADATION: ScenarioConfig(
        incident_type=IncidentType.GATEWAY_DEGRADATION,
        target=Gateway.GATEWAY_A,
        incident_success_rate=0.76,
    ),
    IncidentType.PAYMENT_METHOD_DEGRADATION: ScenarioConfig(
        incident_type=IncidentType.PAYMENT_METHOD_DEGRADATION,
        target=PaymentMethod.UPI,
        incident_success_rate=0.74,
    ),
    IncidentType.MERCHANT_DEGRADATION: ScenarioConfig(
        incident_type=IncidentType.MERCHANT_DEGRADATION,
        target="merchant_000",
        incident_success_rate=0.76,
    ),
    IncidentType.CHECKOUT_ABANDONMENT: ScenarioConfig(
        incident_type=IncidentType.CHECKOUT_ABANDONMENT, target="payment_page"
    ),
    IncidentType.SUBSCRIPTION_RENEWAL: ScenarioConfig(
        incident_type=IncidentType.SUBSCRIPTION_RENEWAL,
        target="renewal",
        incident_success_rate=0.70,
    ),
}
