import math
import random
from datetime import UTC, datetime, timedelta

from .config import ScenarioConfig
from .domain import *
from .money import expected_revenue, observed_revenue, revenue_exposure, revenue_loss


class Simulator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(
        self,
        payments_count: int = 1000,
        start: datetime | None = None,
        end: datetime | None = None,
        scenario: ScenarioConfig | None = None,
    ) -> SimulationResult:
        start = start or datetime(2025, 1, 1, tzinfo=UTC)
        end = end or start + timedelta(days=1)
        ms = self._merchants()
        cs = self._customers(ms)
        subs = [
            Subscription(
                subscription_id=f"sub_{i:04d}",
                merchant_id=c.merchant_id,
                customer_id=c.customer_id,
                amount_minor=1000,
                billing_interval="monthly",
                next_billing_at=start,
            )
            for i, c in enumerate(cs)
            if c.subscription_status == "active"
        ]
        ps = []
        ev = []
        calibration_affected_ids = []
        inc = self._incident(start, end, scenario)
        generated_times = [start + (end - start) * self.rng.random() for _ in range(payments_count)]
        calibration_assignments = set()
        calibration_success_assignments = set()
        if scenario and scenario.affected_share is not None and inc:
            eligible_indices = [
                i
                for i, timestamp in enumerate(generated_times)
                if inc.start_time <= timestamp <= inc.end_time
            ]
            quota = round(len(eligible_indices) * scenario.affected_share)
            if quota < scenario.minimum_affected_events:
                raise ValueError(
                    f"Calibration scenario infeasible: eligible events {len(eligible_indices)} cannot satisfy minimum affected events"
                )
            calibration_assignments = set(self.rng.sample(eligible_indices, quota))
            target_successes = round(
                len(calibration_assignments)
                * (scenario.target_success_rate or scenario.incident_success_rate)
            )
            calibration_success_assignments = set(
                self.rng.sample(list(calibration_assignments), target_successes)
            )
        for i in range(payments_count):
            m = self.rng.choices(ms, weights=[x.baseline_daily_volume for x in ms])[0]
            c = self.rng.choice([x for x in cs if x.merchant_id == m.merchant_id])
            t = generated_times[i]
            amount = max(
                100, round(self.rng.lognormvariate(math.log(m.average_order_value_minor), 0.65))
            )
            method = c.preferred_payment_method
            g = self.rng.choices(
                list(m.gateway_distribution), weights=list(m.gateway_distribution.values())
            )[0]
            issuer = self.rng.choice(list(Issuer))
            calibration_window = bool(
                scenario
                and scenario.affected_share is not None
                and inc
                and inc.start_time <= t <= inc.end_time
            )
            calibration_affected = calibration_window and i in calibration_assignments
            if calibration_affected:
                for dimension, value in scenario.affected_dimensions.items():
                    if dimension == "issuer":
                        issuer = Issuer(value)
                    if dimension == "payment_method":
                        method = PaymentMethod(value)
                if scenario.target_interaction:
                    for dimension, value in scenario.target_interaction.items():
                        if dimension == "issuer":
                            issuer = Issuer(value)
                        if dimension == "payment_method":
                            method = PaymentMethod(value)
            rate = self._rate(method, g, issuer)
            affected = self._affected(inc, m, method, g, issuer, t)
            affected = affected or calibration_affected
            success_rate = (
                scenario.target_success_rate
                if calibration_affected and scenario and scenario.target_success_rate is not None
                else (
                    inc.parameters.get("incident_success_rate", rate) if affected and inc else rate
                )
            )
            success = (
                (i in calibration_success_assignments)
                if calibration_affected
                else self.rng.random() < success_rate
            )
            status = PaymentStatus.SUCCESS if success else PaymentStatus.FAILED
            fail = (
                None
                if success
                else (
                    FailureCode.TIMEOUT if inc and affected else self.rng.choice(list(FailureCode))
                )
            )
            pid = f"payment_{i:06d}"
            if calibration_affected:
                calibration_affected_ids.append(pid)
            oid = f"order_{i:06d}"
            p = Payment(
                payment_id=pid,
                merchant_id=m.merchant_id,
                customer_id=c.customer_id,
                order_id=oid,
                timestamp=t,
                amount_minor=amount,
                currency="INR",
                payment_method=method,
                issuer=issuer,
                gateway=g,
                device_type=c.device_type,
                geo=c.geo,
                failure_code=fail,
                status=status,
            )
            ps.append(p)
            ev += self._events(p)
            if scenario and scenario.incident_type == IncidentType.CHECKOUT_ABANDONMENT:
                ev.extend(
                    [
                        PaymentEvent(
                            event_id=f"checkout_{i:06d}_started",
                            event_type=EventType.CHECKOUT_STARTED,
                            timestamp=t,
                            payment_id=pid,
                            merchant_id=m.merchant_id,
                            customer_id=c.customer_id,
                            amount_minor=amount,
                        ),
                        PaymentEvent(
                            event_id=f"checkout_{i:06d}_page",
                            event_type=EventType.PAYMENT_PAGE_VIEWED,
                            timestamp=t + timedelta(seconds=1),
                            payment_id=pid,
                            merchant_id=m.merchant_id,
                            customer_id=c.customer_id,
                            amount_minor=amount,
                        ),
                    ]
                )
                in_window = inc is not None and inc.start_time <= t <= inc.end_time
                if (in_window and self.rng.random() < scenario.abandonment_multiplier * 0.05) or (
                    not in_window and self.rng.random() < 0.05
                ):
                    ev.append(
                        PaymentEvent(
                            event_id=f"checkout_{i:06d}_abandoned",
                            event_type=EventType.CHECKOUT_ABANDONED,
                            timestamp=t + timedelta(seconds=2),
                            payment_id=pid,
                            merchant_id=m.merchant_id,
                            customer_id=c.customer_id,
                            amount_minor=amount,
                            attributes={"stage": "payment_page"},
                        )
                    )
        if scenario and scenario.incident_type == IncidentType.SUBSCRIPTION_RENEWAL:
            for i, sub in enumerate(subs):
                t = start + (end - start) * self.rng.random()
                affected = inc.start_time <= t <= inc.end_time
                success = self.rng.random() < (scenario.incident_success_rate if affected else 0.94)
                ev.append(
                    PaymentEvent(
                        event_id=f"renewal_{i:04d}_attempt",
                        event_type=EventType.RENEWAL_ATTEMPTED,
                        timestamp=t,
                        merchant_id=sub.merchant_id,
                        customer_id=sub.customer_id,
                        amount_minor=sub.amount_minor,
                        attributes={"subscription_id": sub.subscription_id},
                    )
                )
                ev.append(
                    PaymentEvent(
                        event_id=f"renewal_{i:04d}_result",
                        event_type=EventType.RENEWAL_SUCCESS
                        if success
                        else EventType.RENEWAL_FAILED,
                        timestamp=t + timedelta(seconds=1),
                        merchant_id=sub.merchant_id,
                        customer_id=sub.customer_id,
                        amount_minor=sub.amount_minor,
                        attributes={"subscription_id": sub.subscription_id},
                    )
                )
        if (
            scenario
            and scenario.affected_share is not None
            and len(calibration_affected_ids)
            < max(scenario.minimum_affected_events, scenario.minimum_interaction_events)
        ):
            raise ValueError(
                f"Calibration scenario infeasible: affected events {len(calibration_affected_ids)} < required {scenario.minimum_affected_events}"
            )
        truth = [self._truth(inc, ps, ev, calibration_affected_ids)] if inc else []
        return SimulationResult(
            merchants=ms,
            customers=cs,
            orders=[
                Order(
                    order_id=f"order_{i:06d}",
                    merchant_id=p.merchant_id,
                    customer_id=p.customer_id,
                    created_at=p.timestamp,
                    amount_minor=p.amount_minor,
                )
                for i, p in enumerate(ps)
            ],
            payments=ps,
            events=sorted(ev, key=lambda x: x.timestamp),
            subscriptions=subs,
            incidents=[inc] if inc else [],
            ground_truth=truth,
        )

    def _merchants(self):
        specs = [
            ("ecommerce", 1800, 3500, 0.1),
            ("saas", 500, 8500, 0.7),
            ("education", 700, 2800, 0.3),
            ("travel", 350, 12000, 0.2),
            ("digital_services", 1200, 1500, 0.15),
        ]
        return [
            Merchant(
                merchant_id=f"merchant_{i:03d}",
                name=f"Merchant {i}",
                category=cat,
                baseline_daily_volume=vol,
                average_order_value_minor=a,
                payment_method_distribution={
                    PaymentMethod.CARD: 0.45,
                    PaymentMethod.UPI: 0.35,
                    PaymentMethod.NETBANKING: 0.12,
                    PaymentMethod.WALLET: 0.08,
                },
                gateway_distribution={
                    Gateway.GATEWAY_A: 0.5,
                    Gateway.GATEWAY_B: 0.3,
                    Gateway.GATEWAY_C: 0.2,
                },
                subscription_share=sub,
            )
            for i, (cat, vol, a, sub) in enumerate(specs)
        ]

    def _customers(self, ms):
        return [
            Customer(
                customer_id=f"customer_{m.merchant_id}_{i:03d}",
                merchant_id=m.merchant_id,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                lifetime_value_minor=m.average_order_value_minor * 4,
                transaction_frequency=4,
                preferred_payment_method=self.rng.choice(list(PaymentMethod)),
                device_type=self.rng.choice(["mobile", "desktop"]),
                geo=self.rng.choice(["IN-N", "IN-S", "IN-W", "IN-E"]),
                subscription_status="active"
                if self.rng.random() < m.subscription_share
                else "none",
            )
            for m in ms
            for i in range(40)
        ]

    def _rate(self, m, g, i):
        return (
            {
                PaymentMethod.CARD: 0.94,
                PaymentMethod.UPI: 0.93,
                PaymentMethod.NETBANKING: 0.91,
                PaymentMethod.WALLET: 0.90,
            }[m]
            * {Gateway.GATEWAY_A: 0.99, Gateway.GATEWAY_B: 0.98, Gateway.GATEWAY_C: 0.97}[g]
            * {
                Issuer.HDFC: 1,
                Issuer.ICICI: 0.99,
                Issuer.SBI: 0.97,
                Issuer.AXIS: 0.98,
                Issuer.KOTAK: 0.985,
                Issuer.OTHER: 0.96,
            }[i]
        )

    def _incident(self, s, e, c):
        if not c:
            return None
        a = c.incident_start or s + (e - s) * c.start_fraction
        incident_end = c.incident_end or a + (e - s) * c.duration_fraction
        return Incident(
            incident_id="incident_000",
            incident_type=c.incident_type,
            start_time=a,
            end_time=incident_end,
            severity=c.severity,
            affected_dimensions=c.affected_dimensions or {"target": str(c.target)},
            parameters=c.model_dump(),
        )

    def _affected(self, inc, m, pm, g, i, t):
        if not inc or not inc.start_time <= t <= inc.end_time:
            return False
        target = inc.parameters["target"]
        return (
            (inc.incident_type == IncidentType.ISSUER_DEGRADATION and str(i) == target)
            or (inc.incident_type == IncidentType.GATEWAY_DEGRADATION and str(g) == target)
            or (inc.incident_type == IncidentType.PAYMENT_METHOD_DEGRADATION and str(pm) == target)
            or (inc.incident_type == IncidentType.MERCHANT_DEGRADATION and m.merchant_id == target)
        )

    def _events(self, p):
        a = PaymentEvent(
            event_id=p.payment_id + "_attempt",
            event_type=EventType.PAYMENT_ATTEMPTED,
            timestamp=p.timestamp,
            payment_id=p.payment_id,
            merchant_id=p.merchant_id,
            customer_id=p.customer_id,
            amount_minor=p.amount_minor,
            attributes={"method": p.payment_method, "issuer": p.issuer, "gateway": p.gateway},
        )
        b = PaymentEvent(
            event_id=p.payment_id + "_result",
            event_type=EventType.PAYMENT_SUCCESS
            if p.status == PaymentStatus.SUCCESS
            else EventType.PAYMENT_FAILED,
            timestamp=p.timestamp + timedelta(seconds=1),
            payment_id=p.payment_id,
            merchant_id=p.merchant_id,
            customer_id=p.customer_id,
            amount_minor=p.amount_minor,
            attributes={"status": p.status},
        )
        return [a, b]

    def _truth(self, inc, ps, ev, calibration_affected_ids=None):
        if inc.incident_type == IncidentType.CHECKOUT_ABANDONMENT:
            in_window = [
                e
                for e in ev
                if e.event_type == EventType.CHECKOUT_STARTED
                and inc.start_time <= e.timestamp <= inc.end_time
            ]
            outside = [
                e
                for e in ev
                if e.event_type == EventType.CHECKOUT_STARTED
                and not inc.start_time <= e.timestamp <= inc.end_time
            ]
            abandoned = {e.payment_id for e in ev if e.event_type == EventType.CHECKOUT_ABANDONED}
            abandoned_window = sum(e.payment_id in abandoned for e in in_window)
            abandoned_outside = sum(e.payment_id in abandoned for e in outside)
            baseline = abandoned_outside / len(outside) if outside else 0
            incident = abandoned_window / len(in_window) if in_window else 0
            exposed = sum(e.amount_minor for e in in_window if e.payment_id in abandoned)
            return IncidentGroundTruth(
                incident_id=inc.incident_id,
                incident_type=inc.incident_type,
                actual_root_cause=inc.incident_type.value,
                affected_dimensions=inc.affected_dimensions,
                affected_cohort=inc.affected_dimensions,
                start_time=inc.start_time,
                end_time=inc.end_time,
                severity=inc.severity,
                baseline_expected_success=0,
                incident_success=0,
                affected_transaction_count=0,
                baseline_expected_revenue_minor=0,
                observed_revenue_minor=0,
                revenue_exposure_minor=exposed,
                revenue_loss_minor=exposed,
                metric_kind="checkout_abandonment",
                baseline_abandonment_rate=baseline,
                incident_abandonment_rate=incident,
                incremental_abandonment_rate=incident - baseline,
                affected_checkout_count=len(in_window),
                calibration_affected_payment_ids=calibration_affected_ids or [],
            )
        if inc.incident_type == IncidentType.SUBSCRIPTION_RENEWAL:
            renewals = [
                e
                for e in ev
                if e.event_type == EventType.RENEWAL_ATTEMPTED
                and inc.start_time <= e.timestamp <= inc.end_time
            ]
            amounts = [e.amount_minor for e in renewals]
            observed = sum(
                e.amount_minor
                for e in ev
                if e.event_type == EventType.RENEWAL_SUCCESS
                and inc.start_time <= e.timestamp <= inc.end_time
            )
            baseline = expected_revenue(amounts, 0.94)
            return IncidentGroundTruth(
                incident_id=inc.incident_id,
                incident_type=inc.incident_type,
                actual_root_cause=inc.incident_type.value,
                affected_dimensions=inc.affected_dimensions,
                affected_cohort=inc.affected_dimensions,
                start_time=inc.start_time,
                end_time=inc.end_time,
                severity=inc.severity,
                baseline_expected_success=0.94,
                incident_success=observed / sum(amounts) if amounts else 0,
                affected_transaction_count=0,
                baseline_expected_revenue_minor=baseline,
                observed_revenue_minor=observed,
                revenue_exposure_minor=revenue_exposure(amounts),
                revenue_loss_minor=revenue_loss(baseline, observed),
                metric_kind="subscription_renewal",
                baseline_expected_renewal_revenue_minor=baseline,
                observed_renewal_revenue_minor=observed,
                renewal_revenue_loss_minor=revenue_loss(baseline, observed),
                renewal_revenue_exposure_minor=revenue_exposure(amounts),
                affected_renewal_count=len(renewals),
                calibration_affected_payment_ids=calibration_affected_ids or [],
            )
        cohort = [
            p
            for p in ps
            if inc.start_time <= p.timestamp <= inc.end_time
            and self._affected(
                inc,
                next(m for m in self._merchants() if m.merchant_id == p.merchant_id),
                p.payment_method,
                p.gateway,
                p.issuer,
                p.timestamp,
            )
        ]
        amounts = [p.amount_minor for p in cohort]
        base = expected_revenue(amounts, 0.94)
        obs = observed_revenue(
            [p.amount_minor for p in cohort if p.status == PaymentStatus.SUCCESS]
        )
        return IncidentGroundTruth(
            incident_id=inc.incident_id,
            incident_type=inc.incident_type,
            actual_root_cause=inc.incident_type.value,
            affected_dimensions=inc.affected_dimensions,
            affected_cohort=inc.affected_dimensions,
            start_time=inc.start_time,
            end_time=inc.end_time,
            severity=inc.severity,
            baseline_expected_success=0.94,
            incident_success=obs / sum(amounts) if amounts else 0,
            affected_transaction_count=len(cohort),
            baseline_expected_revenue_minor=base,
            observed_revenue_minor=obs,
            revenue_exposure_minor=revenue_exposure(amounts),
            revenue_loss_minor=revenue_loss(base, obs),
            calibration_affected_payment_ids=calibration_affected_ids or [],
        )
