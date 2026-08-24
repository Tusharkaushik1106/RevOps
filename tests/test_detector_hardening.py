from datetime import UTC, datetime

from services.detector.state import DetectorContext, DetectorState, IncidentStateMachine


def test_state_machine_requires_persistence_and_recovers():
    machine = IncidentStateMachine()
    context = DetectorContext()
    t = datetime(2025, 1, 1, tzinfo=UTC)
    machine.observe(context, 0.5, t)
    assert context.state == DetectorState.ANOMALY
    machine.observe(context, 0.5, t)
    assert context.state == DetectorState.ANOMALY
    machine.observe(context, 0.5, t)
    assert context.state == DetectorState.INCIDENT
    machine.observe(context, 0.1, t)
    assert context.state == DetectorState.RECOVERING
    machine.observe(context, 0.1, t)
    assert context.state == DetectorState.NORMAL


def test_state_machine_reenters_incident_during_recovery():
    machine = IncidentStateMachine()
    context = DetectorContext()
    t = datetime(2025, 1, 1, tzinfo=UTC)
    for _ in range(3):
        machine.observe(context, 0.5, t)
    machine.observe(context, 0.1, t)
    machine.observe(context, 0.5, t)
    assert context.state == DetectorState.INCIDENT
