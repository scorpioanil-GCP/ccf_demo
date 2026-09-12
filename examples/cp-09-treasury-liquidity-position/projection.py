"""Π — what this role is served, shaped from the admitted subgraph.

[ADAPT] everything here. [MECHANISM] nothing.

The projection reads the graph view and nothing else. It opens no store, reads
no clock and computes no debt: `temporal_boundary` is the decision instant the
SDK hands it, and every age below is measured against that rather than against
`datetime.now()`.

**The four temporal classes are kept apart here, because here is where they
would otherwise be flattened** (`CP-SPEC-009` §D.3). Every element the payload
carries declares its `temporal_class`, and three rules follow from the
declaration rather than from a comment:

* a `reporting-period-end` never enters the signal register's age arithmetic —
  `cash_fact_asof` is the closing label of a filing window, not an instant;
* an `unobserved-holding` carries no `observed_at`, and none is synthesized
  from the request — inheriting `asked_at` would manufacture a freshness claim
  out of the act of asking (`TLP-G15`);
* `policy-effectivity` is selected by comparing `validFrom` to the decision
  instant, which acquisition already did; a posture has no age here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

#: Attribute keys the resolution spec mints onto every node.
CLIENT_ID = "client_id"
NODE_KIND = "node_kind"
LABEL = "label"
LEI = "lei"
PAYLOAD = "payload_json"
OBSERVED_RECORDED = "observed_at_recorded"

#: The four temporal classes, as the payload spells them.
MARKET_OBSERVATION = "market-observation"
POLICY_EFFECTIVITY = "policy-effectivity"
REPORTING_PERIOD_END = "reporting-period-end"
UNOBSERVED_HOLDING = "unobserved-holding"


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    """Money as a STRING, never a float.

    A float would make the content address a function of the platform's
    rounding, and this product's whole claim is that the same question returns
    the same bytes.
    """
    return format(value.quantize(Decimal("0.01")), "f")


class TreasuryLiquidityProjection:
    """Cash and rate posture at one instant, with every age kept separate."""

    def __init__(
        self, *, plan_id: str, required: tuple[str, ...],
        declared: Mapping[str, Any],
    ) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set of its own and has none to author.
        self._required = required
        self._declared = declared

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The set the SDK supplied, returned unchanged."""
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        by_kind: dict[str, list[Mapping[str, Any]]] = {}
        for record in view.entities:
            attributes = record.claim.attributes
            kind = attributes.get(NODE_KIND)
            if not kind:
                continue
            body = json.loads(attributes.get(PAYLOAD) or "{}")
            by_kind.setdefault(kind, []).append(
                {
                    "uri": record.claim.entity_uri,
                    "label": attributes.get(LABEL) or None,
                    "lei": attributes.get(LEI) or None,
                    "observed_at_recorded": attributes.get(OBSERVED_RECORDED) == "true",
                    **body,
                }
            )

        client = (by_kind.get("client") or [{}])[0]
        deposits = sorted(by_kind.get("deposit", []), key=lambda e: str(e["uri"]))
        positions = sorted(by_kind.get("position", []), key=lambda e: str(e["uri"]))
        counterparties = {
            str(e.get("lei")): e for e in by_kind.get("counterparty", [])
        }
        # TWO NODE KINDS, ONE REGISTER. The rate and FX classes are separate
        # entity classes because they carry different λ_c — that is what makes
        # the per-class table reachable — but both are `market-observation`
        # elements and the register is where the product accounts for them
        # together (`TLP-G14`).
        signals = sorted(
            [*by_kind.get("rate", []), *by_kind.get("fx", [])],
            key=lambda e: str(e.get("signal_id")),
        )
        postures = sorted(by_kind.get("posture", []), key=lambda e: str(e.get("jurisdiction")))

        home = str(client.get("home_currency") or "")
        rates = {
            str(s["pair"]): _decimal(s["value"])
            for s in signals
            if s.get("signal_class") == "fx-reference" and s.get("pair")
        }

        liquidity = self._liquidity(deposits, home=home, rates=rates)
        concentration = self._concentration(positions, counterparties, client)
        mandate = self._mandate(positions, client, at=temporal_boundary)

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "asked_at": temporal_boundary.isoformat(),
                "client": {
                    "lei": client.get("lei"),
                    "label": client.get("label"),
                    "mandate_id": client.get("mandate_id"),
                    "intent": client.get("intent"),
                    "home_currency": home or None,
                },
                "liquidity": liquidity,
                "concentration": concentration,
                "mandate_checks": mandate,
                # EFFECTIVITY, NOT AGE. Each entry is the version in force at
                # the decision instant, and it carries no age because a posture
                # is never stale — it is in force or it is not.
                "regulatory_posture": [
                    {
                        "jurisdiction": p.get("jurisdiction"),
                        "level": p.get("level"),
                        "valid_from": p.get("valid_from"),
                        "version_id": p.get("version_id"),
                        "temporal_class": POLICY_EFFECTIVITY,
                    }
                    for p in postures
                ],
                # A PERIOD END, NEVER AN OBSERVATION. Its age is reported in
                # DAYS SINCE THE PERIOD CLOSED, which is what the figure
                # actually supports, and it is absent from the signal register.
                "filing_evidence": self._filing(client, at=temporal_boundary),
                "signal_register": self._register(signals, at=temporal_boundary),
                # Named absences, so a reader never has to infer one from a
                # silence (`TLP-G22`).
                "absent_signal_sources": list(self._declared.get("absent_sources", ())),
            },
        )

    def _liquidity(
        self, deposits: Sequence[Mapping[str, Any]], *, home: str,
        rates: Mapping[str, Decimal],
    ) -> Mapping[str, Any]:
        """Balances by currency, converted to home where a rate was required.

        **No `observed_at` appears on a holding**, here or anywhere: the estate
        recorded none, and the payload publishes that absence rather than
        inheriting the request instant (`CP09-F-01`, `TLP-G15`).
        """
        by_currency: dict[str, dict[str, Any]] = {}
        for deposit in deposits:
            currency = str(deposit.get("currency"))
            entry = by_currency.setdefault(
                currency,
                {
                    "currency": currency, "account_count": 0,
                    "balance": Decimal("0"), "temporal_class": UNOBSERVED_HOLDING,
                },
            )
            entry["account_count"] += 1
            entry["balance"] += _decimal(deposit.get("balance", 0))

        rows: list[Mapping[str, Any]] = []
        total = Decimal("0")
        unconvertible: list[str] = []
        for currency in sorted(by_currency):
            entry = by_currency[currency]
            balance: Decimal = entry["balance"]
            if currency == home:
                converted, pair, rate = balance, None, None
            else:
                pair = f"{currency}/{home}"
                rate = rates.get(pair)
                if rate is None:
                    unconvertible.append(currency)
                    converted = None
                else:
                    converted = balance / rate if currency == "JPY" else balance * rate
            if converted is not None:
                total += converted
            rows.append(
                {
                    "currency": currency,
                    "account_count": entry["account_count"],
                    "balance": _money(balance),
                    "fx_pair": pair,
                    "fx_rate": None if rate is None else format(rate, "f"),
                    "balance_in_home": None if converted is None else _money(converted),
                    # THE HOLDING'S OWN CLASS. It has no observation time and
                    # the payload says which class it is, not merely that a
                    # field is missing.
                    "temporal_class": UNOBSERVED_HOLDING,
                }
            )
        return {
            "home_currency": home or None,
            "by_currency": rows,
            "home_currency_total": _money(total),
            # A currency whose conversion had no rate is NOT EVALUABLE and says
            # so; it is not silently dropped from the total.
            "not_evaluable": sorted(unconvertible),
        }

    def _concentration(
        self, positions: Sequence[Mapping[str, Any]],
        counterparties: Mapping[str, Mapping[str, Any]],
        client: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Three verdicts, and the coverage that makes the third meaningful.

        **`limit-unknown` is a verdict, not a silence.** A counterparty with no
        limit row is not a counterparty within its limit, and a product with two
        verdicts reports the client compliant when it cannot know that
        (`TLP-G12`, `TLP-G13`).
        """
        limits = {
            str(k): _decimal(v) for k, v in (client.get("limits") or {}).items()
        }
        exposure: dict[str, Decimal] = {}
        for position in positions:
            lei = str(position.get("counterparty_lei"))
            exposure[lei] = exposure.get(lei, Decimal("0")) + _decimal(
                position.get("notional", 0)
            )
        total = sum(exposure.values(), Decimal("0"))

        rows: list[Mapping[str, Any]] = []
        for lei in sorted(exposure, key=lambda k: (-exposure[k], k)):
            share = (
                Decimal("0") if total == 0
                else (exposure[lei] * 100 / total).quantize(Decimal("0.01"))
            )
            limit = limits.get(lei)
            if limit is None:
                verdict = "limit-unknown"
            elif share > limit:
                verdict = "breach"
            else:
                verdict = "within-limit"
            rows.append(
                {
                    "counterparty_lei": lei,
                    "counterparty_label": (counterparties.get(lei) or {}).get("label"),
                    "notional": _money(exposure[lei]),
                    "share_pct": format(share, "f"),
                    "limit_pct": None if limit is None else format(limit, "f"),
                    "verdict": verdict,
                    "temporal_class": UNOBSERVED_HOLDING,
                }
            )
        covered = sum(1 for row in rows if row["verdict"] != "limit-unknown")
        return {
            "counterparties": rows,
            "total_notional": _money(total),
            "verdict_counts": {
                "breach": sum(1 for r in rows if r["verdict"] == "breach"),
                "within-limit": sum(1 for r in rows if r["verdict"] == "within-limit"),
                "limit-unknown": sum(1 for r in rows if r["verdict"] == "limit-unknown"),
            },
            # THE RATIO, PUBLISHED. Without it "no breach" reads as "compliant"
            # and the difference is the whole point of the third verdict.
            "limit_coverage": {"covered": covered, "counterparties": len(rows)},
        }

    def _mandate(
        self, positions: Sequence[Mapping[str, Any]], client: Mapping[str, Any],
        *, at: datetime,
    ) -> Mapping[str, Any]:
        """The two mandate checks, reported SEPARATELY.

        Measured 2026-09-11: every mandate in this estate permits all three
        instrument kinds, so the KIND check never fires and the TENOR check
        does. Running both and reporting them apart is what lets a reader see
        which one discriminated (`CP09-F-02`, `TLP-G16`).
        """
        permitted = {
            str(k): int(v) for k, v in (client.get("permitted") or {}).items()
        }
        kind_violations = [
            str(p.get("position_id")) for p in positions
            if str(p.get("instrument_kind")) not in permitted
        ]
        tenor_violations = []
        for position in positions:
            kind = str(position.get("instrument_kind"))
            bound = permitted.get(kind)
            maturity = position.get("maturity_date")
            if bound is None or not maturity:
                continue
            days = (datetime.fromisoformat(str(maturity)).date() - at.date()).days
            if days > bound:
                tenor_violations.append(
                    {
                        "position_id": str(position.get("position_id")),
                        "instrument_kind": kind,
                        "maturity_date": str(maturity),
                        "days_to_maturity": days,
                        "max_tenor_days": bound,
                    }
                )
        return {
            "kind_not_permitted": sorted(kind_violations),
            "kind_check_evaluated": bool(permitted),
            "tenor_exceeded": sorted(
                tenor_violations, key=lambda e: str(e["position_id"])
            ),
        }

    def _filing(
        self, client: Mapping[str, Any], *, at: datetime
    ) -> Mapping[str, Any] | None:
        """The quarterly cash figure, labeled as the period end it is."""
        period_end = client.get("cash_fact_asof")
        if not period_end:
            return None
        closed = datetime.fromisoformat(str(period_end)).date()
        if closed > at.date():
            # **`as_of` BOUNDS A PERIOD END; it does not decay one** (§D.3).
            # A quarter closing after the decision instant is NOT YET
            # KNOWABLE, and serving it would be look-ahead — the figure would
            # not have existed when the question was asked. Caught by this
            # example's own output: the first run reported the anchor's
            # 2026-06-30 quarter as `-13 days ago` at a 2026-06-17 decision,
            # which is a negative age and therefore a tell.
            return {
                "reported_cash": None,
                "period_end": str(period_end),
                "temporal_class": REPORTING_PERIOD_END,
                "days_since_period_end": None,
                "status": "not-yet-knowable",
            }
        return {
            "reported_cash": str(client.get("reported_cash")),
            "period_end": str(period_end),
            # NOT an observation instant, and the name says so. The age is
            # DAYS SINCE THE PERIOD CLOSED — what the figure supports — and
            # this element is absent from the signal register entirely.
            "temporal_class": REPORTING_PERIOD_END,
            "days_since_period_end": (at.date() - closed).days,
            "status": "reported",
        }

    def _register(
        self, signals: Sequence[Mapping[str, Any]], *, at: datetime
    ) -> Sequence[Mapping[str, Any]]:
        """Every PARTICIPATING observation, with its age at the decision instant.

        Only `market-observation` elements appear here. A holding has no
        observation time, a posture has effectivity rather than age, and a
        filing figure is a period end — putting any of the three in this list
        would be the flattening §D.3 exists to prevent (`TLP-G14`).
        """
        rows = []
        for signal in signals:
            observed = signal.get("observed_at")
            if not observed:
                continue
            moment = datetime.fromisoformat(str(observed))
            rows.append(
                {
                    "signal_id": signal.get("signal_id"),
                    "signal_class": signal.get("signal_class"),
                    "source": signal.get("source"),
                    "label": signal.get("label"),
                    "observed_at": moment.isoformat(),
                    "age_seconds": int((at - moment).total_seconds()),
                    "temporal_class": MARKET_OBSERVATION,
                }
            )
        return sorted(rows, key=lambda e: (str(e["signal_class"]), str(e["signal_id"])))


def plan_class() -> type[TreasuryLiquidityProjection]:
    """The plan type, for a test that needs it without constructing one."""
    return TreasuryLiquidityProjection
