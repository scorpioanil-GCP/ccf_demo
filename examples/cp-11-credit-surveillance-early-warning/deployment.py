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

## Why the obligor is a graph entity

Because `D-IMPL-334` names entities. An invalidation boundary is recorded
against an `entity_uri`, and the serve-time gate reads the product's own
`touched_entities`. The obligor must therefore BE one — which it also is on the
merits, since it is what every signal is about.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.controlplane.artifacts import PerspectiveArtifact
from ccf.deployment import BootedFabric
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: Parameters this deployment reads by name. `subject`, `intent`, `freshness`
#: and `asked_at` are NOT here — they are `ProductRequest` FIELDS (§B.2).
OBLIGORS = "obligors"
SINCE = "since"
WINDOW_DAYS = "window_days"

SYSTEM = "credit_surveillance"

#: Which resolution rule admits each node kind.
MATCH_KEY: Mapping[str, str] = {
    "obligor": "obligor_node",
    "signal": "signal_node",
}

#: Which endpoint rule resolves each side of each predicate. The rule's
#: `match_key` must be a KEY PRESENT IN THE PAYLOAD, or the envelope mints
#: entities and zero relationships — silently.
ENDPOINT_RULES: Mapping[str, tuple[str, str]] = {
    "signalAbout": ("obligor_subject", "signal_object"),
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
    *, anchor_lei: str, asked_at: datetime, intent: str = "daily-sweep",
    freshness: str = "daily", since: date | None = None,
    window_days: int | None = None,
    debt_tolerance: Decimal | str | None = None,
) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    The four §6.3 axes are FIELDS — they establish which question was asked and
    are what the content address and the replay record resolve against
    (`EWS-G19`). ``asked_at`` arrives from the CALLER; nothing here reads a
    clock (`D-IMPL-98`).
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {OBLIGORS: [anchor_lei]}
    if since is not None:
        parameters[SINCE] = since.isoformat()
    if window_days is not None:
        parameters[WINDOW_DAYS] = int(window_days)
    if debt_tolerance is not None:
        # A `Decimal`, never a float: this rides the content address, and the
        # canonicalizer refuses floats as not bit-stable.
        parameters["debt_tolerance"] = Decimal(str(debt_tolerance))
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=anchor_lei,
        intent=intent,
        freshness=freshness,
        asked_at=asked_at,
        parameters=parameters,
    )


def perspective() -> PerspectiveArtifact:
    declared = dict(config()["default_perspective"])
    return PerspectiveArtifact(semver="1.0.0", **declared)


def acquire_for(asked: ProductRequest) -> acquisition.Estate:
    declared = config()["request_contract"]["defaults"]
    window = int(asked.parameters.get(WINDOW_DAYS, declared["window_days"]))
    raw_since = asked.parameters.get(SINCE)
    return acquisition.acquire(
        anchor_lei=asked.subject,
        asked_at=asked.asked_at,
        since=date.fromisoformat(raw_since) if raw_since else None,
        window_days=window,
    )


def obligor_uri(lei: str) -> str:
    """The entity URI an invalidation boundary would name (`D-IMPL-334`)."""
    return f"obligor://{lei}"


def _uri(kind: str, key: str) -> str:
    return f"{kind}://{key}"


def _instant(value: Any) -> datetime:
    """A source date as a timezone-aware instant. No clock is read."""
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _node(
    *, tenant_id: str, at: datetime, uri: str, obligor_id: str, kind: str,
    label: str, body: Mapping[str, Any], observed_time: datetime | None,
    promoted: Mapping[str, str] | None = None,
) -> SignalEnvelope:
    """One node's attributes. ATTRIBUTED, therefore ingested LAST.

    `promoted` lifts an attribute out of `payload_json` and onto the claim,
    because that is where a λ_c row's `series_key_attribute` reads it. Buried
    in the JSON blob the scorer cannot see it and every class collapses into
    one series.
    """
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        # THE SOURCE'S OWN INSTANT where one exists, `None` where none does.
        # `D-IMPL-332` preserves the absence; `D-IMPL-331` lets the λ_c row
        # decide which instant it decays against.
        observed_time=observed_time,
        raw_payload={
            MATCH_KEY[kind]: uri,
            "entity_uri": uri,
            "obligor_id": obligor_id,
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
    anchor = obligor_uri(estate.obligor.lei)
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    def edge(subject: str, obj: str, predicate: str) -> None:
        edges.append(_edge(
            tenant_id=tenant_id, at=at, ordinal=len(edges),
            subject=subject, obj=obj, predicate=predicate,
        ))

    # THE OBLIGOR'S SURVEILLANCE STATE, not only its identity — and this is
    # what makes `D-IMPL-334` mean anything here.
    #
    # An obligor node carrying only `lei`, `legal_name`, `sic` and `sector`
    # never changes, so a new filing would supersede nothing and no
    # invalidation boundary would ever be recorded against the obligor. The
    # claim would deduplicate and the fabric would be right to say nothing
    # happened — to the IDENTITY, nothing did.
    #
    # What a surveillance product means by "this obligor's context changed" is
    # that its evidence moved. So the claim carries the leading edge of that
    # evidence, and `observed_time` IS that edge: when a new signal lands the
    # claim differs, the single writer supersedes the old one, and the boundary
    # it records is the NEW SIGNAL'S OWN INSTANT rather than the instant of
    # this write (`D-IMPL-334`'s contract, and `D-IMPL-332`'s reasoning).
    latest_signal_at = (
        max(signal.observed_at for signal in estate.signals)
        if estate.signals
        else None
    )
    nodes.append(_node(
        tenant_id=tenant_id, at=at, uri=anchor, obligor_id=estate.obligor.lei,
        kind="obligor", label=estate.obligor.legal_name,
        body={
            "lei": estate.obligor.lei,
            "legal_name": estate.obligor.legal_name,
            "sic": estate.obligor.sic,
            "sector": estate.obligor.sector,
            "latest_signal_at": (
                latest_signal_at.isoformat() if latest_signal_at else None
            ),
            "signals_observed": len(estate.signals),
        },
        observed_time=_instant(latest_signal_at) if latest_signal_at else None,
    ))

    for signal in estate.signals:
        uri = _uri("signal", signal.signal_id)
        edge(anchor, uri, "signalAbout")
        nodes.append(_node(
            tenant_id=tenant_id, at=at, uri=uri,
            obligor_id=estate.obligor.lei, kind="signal",
            label=f"{signal.signal_type} {signal.observed_at.isoformat()}",
            body={
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type,
                "observed_at": signal.observed_at.isoformat(),
                "severity": str(signal.severity),
                "item": signal.item,
                "provenance": signal.provenance,
            },
            # A REAL OBSERVATION DATE, from PostgreSQL. The graph carries no
            # timestamp at all (`CP11-F-07`) and no date is parsed from a label.
            observed_time=_instant(signal.observed_at),
            # THE SERIES KEY, promoted onto the claim (`D-IMPL-333`).
            promoted={"signal_type": signal.signal_type},
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


def build_exclusion_gate(*, asked: ProductRequest) -> Any:
    """The DEPLOYMENT half of the declared product gate (`EWS-G18`).

    The Control Plane owns the gate's IDENTITY; the deployment owns the
    PREDICATE, and the resolver stamps `gate` and `gate_version` from the
    declaration (`D-IMPL-282` R-11).

    **What it refuses.** A payload whose composite cannot be audited: one that
    reports a score without the contributions behind it, or that drops a signal
    from the delta without saying why. *"Why did this name not escalate"* is
    answered by what was left out, and a product that could not answer it would
    be a number with no argument.
    """
    del asked

    def gate(
        *, candidate: ContextProductContract, evidence: object = None
    ) -> str | None:
        payload = candidate.payload
        composite = payload.get("composite") or {}
        if "score" not in composite:
            return "the payload reports no composite score"
        if "contributing" not in payload:
            return (
                "the payload reports a composite with no contributing set; a"
                " score without its derivation cannot be audited (EWS-G17)"
            )
        if "excluded" not in payload:
            return (
                "the payload carries no exclusion list; 'why did this name not"
                " escalate' is answered by what was left out (EWS-G18)"
            )
        states = (payload.get("chain_states") or {}).get("states")
        if states is None:
            return "the payload does not report the chain-state partition"
        total = (payload.get("chain_states") or {}).get("total")
        if total != sum(states.values()):
            return (
                "the chain states do not partition the signal set; a signal"
                " counted in two states is counted twice (EWS-G28)"
            )
        return None

    return gate


@dataclass(frozen=True)
class SurveillanceScenario:
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
        return f"cp-11.early-warning/{self.asked.subject}"

    @property
    def declared(self) -> Mapping[str, Any]:
        return {"estate": self.estate, "intent": self.asked.intent}

    @property
    def max_ttl_seconds(self) -> int:
        return 86400

    @property
    def product_ttl_seconds(self) -> int:
        return 21600


def measured_completeness(estate: acquisition.Estate) -> Decimal:
    """How many of the five signal classes this obligor has any evidence in.

    A real measurement, not a declaration. Tupperware exercises it: no trend
    deltas at all, so completeness is strictly below 1 and the payload says
    which class is absent rather than scoring it zero.
    """
    from projection import SIGNAL_CLASSES

    present = {s.signal_type for s in estate.signals}
    covered = sum(1 for name in SIGNAL_CLASSES if name in present)
    return (Decimal(covered) / Decimal(len(SIGNAL_CLASSES))).quantize(
        Decimal("0.0001")
    )


def measured_semantic_consistency(estate: acquisition.Estate) -> Decimal:
    """Whether every consumed signal resolves to a declared weight row.

    A signal whose class has no weight in any sector is a consistency failure,
    not a silent skip: the product would otherwise report a composite computed
    over fewer signals than it received, with nothing saying so.
    """
    if not estate.signals:
        return Decimal("1.0000")
    resolvable = sum(
        1
        for signal in estate.signals
        if (signal.signal_type, estate.obligor.sector) in estate.weights
        or (signal.signal_type, "Unclassified") in estate.weights
    )
    return (Decimal(resolvable) / Decimal(len(estate.signals))).quantize(
        Decimal("0.0001")
    )
