"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

Its boundaries are ruled (`D-IMPL-315`): vocabulary, source access, admission,
and the deployment half of ONE declared product gate. No binder, no universal
gates, no replay record, no serve — those are ``GovernedResolver``'s.

## The ingestion-order contract

Edge envelopes carry two endpoint references and **no attributes**; node
envelopes carry one node's attributes. **Edges are ingested FIRST and nodes
LAST.** A claim carrying fewer attributes at the same URI *supersedes* the
richer one rather than merging, so an edge arriving after a node erases that
node's attributes and nothing raises.

## What reaches the fabric's clock, and what does not

An observation envelope's ``observed_time`` is the instant the system
**RECORDED** — `Observation.recorded_at`, straight off the ledger. The
corrected instant is never written, never stored and never read back: it is
computed inside Π, used to compare two systems, and discarded (`FXR-G24`).

That is not a precaution. `settlement` runs `+47 s` fast and `risk` runs
`−112 s` slow, so on those two classes the recorded and corrected instants
genuinely differ — and a λ_c row aged against the corrected instant would make
the SDK's freshness figure a function of this product's own alignment model.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
import projection
from ccf.controlplane.artifacts import PerspectiveArtifact
from ccf.deployment import BootedFabric
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: Parameters this deployment reads by name. `subject`, `intent`, `freshness`
#: and `asked_at` are NOT here — they are `ProductRequest` FIELDS (`FXR-G16`).
TRADES = "trades"
ALIGN_CLOCKS = "align_clocks"
COMPARE_AT = "compare_at"
MATERIALITY_PIPS = "materiality_pips"

SYSTEM = "fx_reconciliation"

#: Which resolution rule admits each node kind.
MATCH_KEY: Mapping[str, str] = {
    "trade": "trade_node",
    "observation": "observation_node",
}

#: Which endpoint rule resolves each side of each predicate. The rule's
#: `match_key` must be a KEY PRESENT IN THE PAYLOAD, or the envelope mints
#: entities and zero relationships — silently.
ENDPOINT_RULES: Mapping[str, tuple[str, str]] = {
    "observedIn": ("trade_subject", "observation_object"),
}


def config() -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return document


def connection(*, root: Path) -> Mapping[str, str]:
    """Where the FABRIC's own L3 lives for this run. Never a source store."""
    profile = yaml.safe_load(
        (HERE / "backends.yaml").read_text(encoding="utf-8")
    )["declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {"database_path": str(root / f"{profile['prefix']}{profile['suffix']}")}


def request(
    *, trades: Sequence[str], asked_at: datetime, scope: str | None = None,
    intent: str = "break-investigation", freshness: str = "intraday",
    align_clocks: bool | None = None, compare_at: str | None = None,
    materiality_pips: Decimal | str | None = None,
    debt_tolerance: Decimal | str | None = None,
) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    The four §6.3 axes are FIELDS — they establish which question was asked and
    are what the content address and the replay record resolve against
    (`FXR-G16`). ``asked_at`` arrives from the CALLER; nothing here reads a
    clock (`D-IMPL-98`).

    ``subject`` is the trade for a single-trade request and the caller's named
    ``scope`` for a set. A set is not nameless — a reconciliation over the
    designated break population is *about* that population — and inventing a
    name here, or quietly promoting the first trade to stand for sixty, would
    put a subject in the content address that the caller never asked about.
    """
    declared = config()["product_class"]
    defaults = config()["request_contract"]["defaults"]
    ordered = sorted(dict.fromkeys(trades))
    if not ordered:
        raise ValueError("a reconciliation needs at least one trade")
    if len(ordered) == 1:
        subject = ordered[0]
    elif scope:
        subject = scope
    else:
        raise ValueError(
            "a multi-trade request must name its `scope`; the subject rides the"
            " content address, and promoting one of sixty trades to stand for"
            " the set would answer under a subject nobody asked about"
        )
    parameters: dict[str, Any] = {
        TRADES: ordered,
        ALIGN_CLOCKS: (
            defaults[ALIGN_CLOCKS] if align_clocks is None else bool(align_clocks)
        ),
        # CARRIED EXPLICITLY EVEN WHEN DEFAULTED, because the answer differs
        # between the two values and a consumer must be able to read which
        # question was asked off the request itself (§B.2a).
        COMPARE_AT: compare_at or defaults[COMPARE_AT],
    }
    if materiality_pips is not None:
        # A `Decimal`, never a float: this rides the content address, and the
        # canonicalizer refuses floats as not bit-stable.
        parameters[MATERIALITY_PIPS] = Decimal(str(materiality_pips))
    if debt_tolerance is not None:
        parameters["debt_tolerance"] = Decimal(str(debt_tolerance))
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=subject,
        intent=intent,
        freshness=freshness,
        asked_at=asked_at,
        parameters=parameters,
    )


def perspective() -> PerspectiveArtifact:
    declared = dict(config()["default_perspective"])
    return PerspectiveArtifact(semver="1.0.0", **declared)


def acquire_for(asked: ProductRequest) -> acquisition.Estate:
    defaults = config()["request_contract"]["defaults"]
    return acquisition.acquire(
        trade_ids=list(asked.parameters[TRADES]),
        asked_at=asked.asked_at,
        compare_at=str(asked.parameters.get(COMPARE_AT, defaults[COMPARE_AT])),
    )


def trade_uri(trade_id: str) -> str:
    return f"fxr_trade://{trade_id}"


def observation_uri(observation: acquisition.Observation) -> str:
    return (
        f"fxr_observation://{observation.trade_id}"
        f"-{observation.system}-{observation.amendment_seq}"
    )


def _node(
    *, tenant_id: str, at: datetime, uri: str, trade_id: str, kind: str,
    label: str, body: Mapping[str, Any], observed_time: datetime | None,
    promoted: Mapping[str, str] | None = None,
) -> SignalEnvelope:
    """One node's attributes. ATTRIBUTED, therefore ingested LAST.

    `promoted` lifts an attribute out of `payload_json` and onto the claim,
    because that is where a λ_c row's `series_key_attribute` reads it.
    """
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=observed_time,
        raw_payload={
            MATCH_KEY[kind]: uri,
            "entity_uri": uri,
            "trade_id": trade_id,
            "node_kind": kind,
            "label": label,
            "payload_json": json.dumps(body, sort_keys=True, default=str),
            **(promoted or {}),
        },
    )


def _edge(
    *, tenant_id: str, at: datetime, ordinal: int, subject: str, obj: str,
    predicate: str,
) -> SignalEnvelope:
    """One typed edge, carrying NO attributes.

    .. warning::

       **Must reach L2 BEFORE either endpoint's node envelope.** It resolves
       both endpoints and has no attributes to give them, so a thin claim
       arriving after an attributed one supersedes it, silently.
    """
    subject_rule, object_rule = ENDPOINT_RULES[predicate]
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{predicate}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            subject_rule: subject,
            object_rule: obj,
            "subject_uri": subject,
            "object_uri": obj,
            "predicate": predicate,
        },
    )


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime,
) -> tuple[list[SignalEnvelope], list[SignalEnvelope]]:
    """``(edges, nodes)`` for one estate read, in the order they must be written."""
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    for trade in estate.trades:
        anchor = trade_uri(trade.trade_id)
        nodes.append(_node(
            tenant_id=tenant_id, at=at, uri=anchor, trade_id=trade.trade_id,
            kind="trade", label=f"{trade.pair} {trade.trade_id}",
            body={
                "trade_id": trade.trade_id,
                "pair": trade.pair,
                "execution_ts": trade.execution_ts.isoformat(),
                "value_date": str(trade.value_date),
                # A BAND, carried as a band. Nothing reconstructs a notional
                # from it, and no figure derived from one appears anywhere
                # downstream (`FXR-G17`).
                "notional_band": trade.notional_band,
                "counterparty_lei": trade.counterparty_lei,
            },
            # THE TRADE'S OWN WORLD TIME. Its class is `supersede-only`, so
            # this is not a decay basis; it is the honest instant for the
            # claim and it is what an amendment supersedes against.
            observed_time=trade.execution_ts,
        ))

        # EVERY amendment, not only the one this comparison instant selects.
        # The graph carries the observation HISTORY because that is what
        # `as_of` reconstruction reads (`FXR-G03`); which of them Π compares is
        # the request's choice and is made in Π, not here.
        for system in ("trading", "settlement", "risk"):
            for observation in estate.observations.get(
                (trade.trade_id, system), ()
            ):
                uri = observation_uri(observation)
                edges.append(_edge(
                    tenant_id=tenant_id, at=at, ordinal=len(edges),
                    subject=anchor, obj=uri, predicate="observedIn",
                ))
                nodes.append(_node(
                    tenant_id=tenant_id, at=at, uri=uri,
                    trade_id=trade.trade_id, kind="observation",
                    label=(
                        f"{observation.system} amd {observation.amendment_seq}"
                    ),
                    body={
                        "trade_id": observation.trade_id,
                        "system_name": observation.system,
                        "amendment_seq": observation.amendment_seq,
                        "value_rate": str(observation.value_rate),
                        "recorded_at": observation.recorded_at.isoformat(),
                        "clock_offset_seconds": observation.clock_offset_seconds,
                    },
                    # THE INSTANT THE SYSTEM RECORDED, from the ledger. NOT
                    # `observation.corrected_at` — see the module docstring,
                    # and `FXR-G24`, which asserts this on `settlement` and
                    # `risk`, where the two instants actually differ.
                    observed_time=observation.recorded_at,
                    # THE SERIES KEY, promoted onto the claim (`FXR-G14`).
                    promoted={"system_name": observation.system},
                ))
    return edges, nodes


def ingest(booted: BootedFabric, estate: acquisition.Estate, *, at: datetime) -> None:
    """Write the estate into L3 through the ONE write handle, in order."""
    edges, nodes = envelopes(estate, tenant_id=booted.tenant_id, at=at)
    worker = booted.handle.worker
    for envelope in edges:
        worker.ingest(envelope)
    for envelope in nodes:
        worker.ingest(envelope)


#: Payload keys that would let a consumer count system-pair breaks. None of
#: them is produced; the gate refuses if one ever appears.
PAIRWISE_KEYS = frozenset({
    "pairwise", "pairwise_breaks", "system_pairs", "pair_breaks",
    "comparisons", "system_pair_breaks",
})


def build_verdict_gate(*, asked: ProductRequest) -> Any:
    """The DEPLOYMENT half of the declared product gate (`FXR-G07`).

    The Control Plane owns the gate's IDENTITY; the deployment owns the
    PREDICATE, and the resolver stamps `gate` and `gate_version` from the
    declaration (`D-IMPL-282` R-11).

    **What it refuses: a payload whose unit of analysis has drifted.** Exactly
    one verdict per requested trade, no trade counted twice, and no field a
    consumer could count to arrive at the pairwise number. Measured, three
    systems over 60 break trades give 120 pairwise comparisons over 60
    underlying divergences — exactly `2.00×` — and a middle office told it has
    120 breaks staffs for twice the work (§B.3, TRAP 1).
    """
    requested = list(asked.parameters[TRADES])

    def gate(
        *, candidate: ContextProductContract, evidence: object = None
    ) -> str | None:
        payload = candidate.payload
        rows = payload.get("reconciliations")
        if rows is None:
            return "the payload reports no reconciliations"
        seen = [row["trade_id"] for row in rows]
        if len(seen) != len(set(seen)):
            return (
                "a trade carries more than one verdict; the unit of analysis is"
                " the trade and a second verdict for one trade is TRAP 1"
                " arriving through the back door (FXR-G07)"
            )
        if sorted(seen) != sorted(requested):
            return (
                "the reconciled set is not the requested set; a trade dropped"
                " from the answer is an omission the caller cannot see"
            )
        if payload.get("observations") != len(rows):
            return (
                "the reported observation count does not equal the number of"
                " verdicts served (FXR-G22)"
            )
        leaked = PAIRWISE_KEYS & set(payload)
        if leaked:
            return (
                f"the payload exposes {sorted(leaked)!r}, which a consumer can"
                " count to arrive at the pairwise number; pairwise variance"
                " lives beneath a verdict as an explanation of it, never"
                " beside it as a peer (FXR-G07, FXR-G22)"
            )
        for row in rows:
            if row["verdict"] not in projection.VERDICTS:
                return (
                    f"the verdict {row['verdict']!r} is outside the closed"
                    " classification vocabulary (FXR-G21)"
                )
        return None

    return gate


@dataclass(frozen=True)
class ReconciliationScenario:
    """What one run needs — satisfies ``produce.Scenario`` structurally."""

    estate: acquisition.Estate
    asked: ProductRequest

    @property
    def product_class_key(self) -> str:
        return "product_class"

    @property
    def request_contract_key(self) -> str:
        return "request_contract"

    @property
    def operator_parameter_keys(self) -> tuple[str, ...]:
        return tuple(config()["product_class"]["required_operator_keys"])

    @property
    def policy_bundle_key(self) -> str:
        return "policy"

    @property
    def plan_id(self) -> str:
        return f"cp-12.fx-reconciliation/{self.asked.subject}"

    @property
    def declared(self) -> Mapping[str, Any]:
        return {
            "estate": self.estate,
            "intent": self.asked.intent,
            "align_clocks": bool(self.asked.parameters[ALIGN_CLOCKS]),
            "materiality_pips": self.asked.parameters.get(MATERIALITY_PIPS),
        }

    @property
    def max_ttl_seconds(self) -> int:
        return 14400

    @property
    def product_ttl_seconds(self) -> int:
        # One hour for a live reconciliation (§B.1).
        return 3600


def measured_completeness(estate: acquisition.Estate) -> Decimal:
    """How many of the three systems actually reported, per trade.

    A real measurement, not a declaration: the denominator is three systems per
    requested trade and the numerator is the observations the comparison
    instant resolved. A trade one system never reported is genuinely less
    complete, and a two-system reconciliation cannot partition two-against-one
    at all.
    """
    from projection import SYSTEMS

    expected = len(estate.trades) * len(SYSTEMS)
    if not expected:
        return Decimal("1.0000")
    present = sum(
        1
        for trade in estate.trades
        for system in SYSTEMS
        if estate.at(trade.trade_id, system) is not None
    )
    return (Decimal(present) / Decimal(expected)).quantize(Decimal("0.0001"))


def measured_semantic_consistency(estate: acquisition.Estate) -> Decimal:
    """Whether every trade's pair resolves to a declared pip scale.

    A pair the artifact does not name cannot have its variance expressed in
    pips at all, so the product would be comparing rate differences across
    incomparable scales — TRAP 5 — and reporting a number anyway. That is a
    consistency failure, not a silent skip.
    """
    if not estate.trades:
        return Decimal("1.0000")
    resolvable = sum(1 for trade in estate.trades if trade.pair in estate.pips)
    return (Decimal(resolvable) / Decimal(len(estate.trades))).quantize(
        Decimal("0.0001")
    )
