from .detector import IncidentDetector
from .schemas import ObservableInput


def evaluate(
    detector: IncidentDetector, observable: ObservableInput, expected_window: tuple | None = None
) -> dict:
    packet = detector.detect(observable)
    return {
        "detected": packet.incident_detected,
        "confidence": packet.confidence,
        "window": packet.incident_window,
        "revenue_at_risk_minor": packet.revenue_impact.revenue_at_risk_minor,
    }
