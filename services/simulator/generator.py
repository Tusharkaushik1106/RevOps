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
        inc = self._incident(start, end, scenario)
        for i in range(payments_count):
            m = self.rng.choices(ms, weights=[x.baseline_daily_volume for x in ms])[0]
            c = self.rng.choice([x for x in cs if x.merchant_id == m.merchant_id])
            t = start + (end - start) * self.rng.random()
            amount = max(
                100, round(self.rng.lognormvariate(math.log(m.average_order_value_minor), 0.65))
            )
            method = c.preferred_payment_method
            g = self.rng.choices(
                list(m.gateway_distribution), weights=list(m.gateway_distribution.values())
            )[0]
            issuer = self.rng.choice(list(Issuer))
            rate = self._rate(method, g, issuer)
            affected = self._affected(inc, m, method, g, issuer, t)
            success = self.rng.random() < (
                inc.parameters.get("incident_success_rate", rate) if affected and inc else rate
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
                            merchant_id=m.merchant_id,
                            customer_id=c.customer_id,
                            amount_minor=amount,
                        ),
                        PaymentEvent(
                            event_id=f"checkout_{i:06d}_page",
                            event_type=EventType.PAYMENT_PAGE_VIEWED,
                            timestamp=t + timedelta(seconds=1),
                            merchant_id=m.merchant_id,
                            customer_id=c.customer_id,
                            amount_minor=amount,
                        ),
                    ]
                )
                if affected or self.rng.random() < 0.05:
                    ev.append(
                        PaymentEvent(
                            event_id=f"checkout_{i:06d}_abandoned",
                            event_type=EventType.CHECKOUT_ABANDONED,
                            timestamp=t + timedelta(seconds=2),
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
        truth = [self._truth(inc, ps)] if inc else []
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
        a = s + (e - s) * c.start_fraction
        return Incident(
            incident_id="incident_000",
            incident_type=c.incident_type,
            start_time=a,
            end_time=a + (e - s) * c.duration_fraction,
            severity=c.severity,
            affected_dimensions={"target": str(c.target)},
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

    def _truth(self, inc, ps):
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
        )
