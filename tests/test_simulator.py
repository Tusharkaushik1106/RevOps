from services.simulator.config import SCENARIOS
from services.simulator.domain import IncidentType
from services.simulator.generator import Simulator
from services.simulator.money import expected_revenue, observed_revenue, revenue_loss


def test_seed_determinism():
    a = Simulator(42).generate(100)
    b = Simulator(42).generate(100)
    assert a.model_dump() == b.model_dump()


def test_different_seed():
    assert Simulator(1).generate(20).model_dump() != Simulator(2).generate(20).model_dump()


def test_baseline_exists():
    assert len(Simulator().generate(100).payments) == 100


def test_incident_ground_truth_is_separate():
    r = Simulator().generate(500, scenario=SCENARIOS[IncidentType.ISSUER_DEGRADATION])
    assert r.ground_truth and all("incident" not in e.attributes for e in r.events)


def test_revenue():
    assert (
        expected_revenue([10000, 10050], 0.5) == 10025
        and observed_revenue([100, 200]) == 300
        and revenue_loss(400, 300) == 100
    )


def test_scenarios():
    for s in SCENARIOS:
        assert Simulator(42).generate(100, scenario=SCENARIOS[s]).incidents[0].incident_type == s


def test_events_chronological():
    r = Simulator().generate(100)
    assert r.events == sorted(r.events, key=lambda x: x.timestamp)
