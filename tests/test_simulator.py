from services.simulator.config import SCENARIOS
from services.simulator.diagnostics import summarize
from services.simulator.domain import EventType, IncidentType, Issuer, PaymentStatus
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


def test_subscription_revenue_ground_truth():
    gt = (
        Simulator(42)
        .generate(1000, scenario=SCENARIOS[IncidentType.SUBSCRIPTION_RENEWAL])
        .ground_truth[0]
    )
    assert gt.metric_kind == "subscription_renewal"
    assert gt.affected_renewal_count > 0
    assert (
        gt.renewal_revenue_loss_minor
        == gt.baseline_expected_renewal_revenue_minor - gt.observed_renewal_revenue_minor
    )
    assert gt.renewal_revenue_exposure_minor >= gt.baseline_expected_renewal_revenue_minor


def test_checkout_metrics_and_no_failure_leakage():
    result = Simulator(42).generate(1000, scenario=SCENARIOS[IncidentType.CHECKOUT_ABANDONMENT])
    gt = result.ground_truth[0]
    assert (
        gt.metric_kind == "checkout_abandonment"
        and gt.incident_abandonment_rate > gt.baseline_abandonment_rate
    )
    assert not any(
        e.event_type == EventType.PAYMENT_FAILED and e.attributes.get("stage") == "payment_page"
        for e in result.events
    )


def test_unrelated_issuer_stability():
    r = Simulator(42).generate(10000, scenario=SCENARIOS[IncidentType.ISSUER_DEGRADATION])
    affected = [
        p
        for p in r.payments
        if p.issuer == Issuer.HDFC
        and r.incidents[0].start_time <= p.timestamp <= r.incidents[0].end_time
    ]
    other = [
        p
        for p in r.payments
        if p.issuer != Issuer.HDFC
        and r.incidents[0].start_time <= p.timestamp <= r.incidents[0].end_time
    ]
    assert (
        sum(p.status == PaymentStatus.SUCCESS for p in affected) / len(affected)
        < sum(p.status == PaymentStatus.SUCCESS for p in other) / len(other) - 0.05
    )


def test_unrelated_gateway_and_method_stability():
    for kind, key, unrelated in [
        (IncidentType.GATEWAY_DEGRADATION, "gateway_a", "gateway_b"),
        (IncidentType.PAYMENT_METHOD_DEGRADATION, "upi", "card"),
    ]:
        r = Simulator(42).generate(10000, scenario=SCENARIOS[kind])
        inc = r.incidents[0]
        affected = [
            p
            for p in r.payments
            if str(p.gateway if kind == IncidentType.GATEWAY_DEGRADATION else p.payment_method)
            == key
            and inc.start_time <= p.timestamp <= inc.end_time
        ]
        other = [
            p
            for p in r.payments
            if str(p.gateway if kind == IncidentType.GATEWAY_DEGRADATION else p.payment_method)
            == unrelated
            and inc.start_time <= p.timestamp <= inc.end_time
        ]
        assert (
            sum(p.status == PaymentStatus.SUCCESS for p in affected) / len(affected)
            < sum(p.status == PaymentStatus.SUCCESS for p in other) / len(other) - 0.05
        )


def test_diagnostics():
    summary = summarize(Simulator(42).generate(100).payments)
    assert summary["payment_count"] == 100 and summary["average_transaction_value_minor"] > 0


def test_incident_boundaries():
    r = Simulator(42).generate(1000, scenario=SCENARIOS[IncidentType.GATEWAY_DEGRADATION])
    inc = r.incidents[0]
    assert all(
        inc.start_time <= p.timestamp <= inc.end_time
        or p.timestamp < inc.start_time
        or p.timestamp > inc.end_time
        for p in r.payments
    )
