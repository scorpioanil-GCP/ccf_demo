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

## What is not invented here

A spread observation carries a real observation date and a grade carries a real
effective date, so both envelopes set ``observed_time`` from the SOURCE. Under
`D-IMPL-331`/`D-IMPL-332` that instant survives into ``claim.valid_from``, and
both λ_c rows declare ``decay_basis: valid-from`` — so a two-year-old
observation decays like a two-year-old observation rather than reading as
perfectly fresh because this run just ingested it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timezone
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
#: and `asked_at` are NOT here — they are `ProductRequest` FIELDS (§B.5).
OBLIGORS = "obligors"
WINDOW_DAYS = "window_days"
GRANULARITY = "granularity"
DIVERGENCE_MULTIPLE = "divergence_multiple"

SYSTEM = "credit_estate"

#: Which resolution rule admits each node kind. Four classes, because the
#: reference debt scorer types an observation by its ENTITY CLASS and one class
#: would price a daily spread and a quarterly grade identically.
MATCH_KEY: Mapping[str, str] = {
    "obligor": "obligor_node",
    "instrument": "instrument_node",
    "spread": "spread_node",
    "grade": "grade_node",
}

#: Which endpoint rule resolves each side of each predicate. The rule's
#: `match_key` must be a KEY PRESENT IN THE PAYLOAD, or the envelope mints
#: entities and zero relationships — silently.
ENDPOINT_RULES: Mapping[str, tuple[str, str]] = {
    "hasInstrument": ("obligor_subject", "instrument_object"),
    "pricedAt": ("instrument_subject", "spread_object"),
    "gradedAs": ("obligor_subject", "grade_object"),
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
    *, anchor_lei: str, asked_at: datetime, intent: str = "portfolio-review",
    freshness: str = "daily", window_days: int | None = None,
    granularity: str | None = None,
    divergence_multiple: Decimal | str | None = None,
    debt_tolerance: Decimal | str | None = None,
) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    The four §6.3 axes are FIELDS — they establish which question was asked and
    are what the content address and the replay record resolve against
    (`RSM-G19`). ``asked_at`` arrives from the CALLER; nothing here reads a
    clock (`D-IMPL-98`).
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {OBLIGORS: [anchor_lei]}
    if window_days is not None:
        parameters[WINDOW_DAYS] = int(window_days)
    if granularity is not None:
        parameters[GRANULARITY] = granularity
    if divergence_multiple is not None:
        # A `Decimal`, never a float: this rides the content address, and the
        # canonicalizer refuses floats as not bit-stable.
        parameters[DIVERGENCE_MULTIPLE] = Decimal(str(divergence_multiple))
    if debt_tolerance is not None:
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
    return acquisition.acquire(
        anchor_lei=asked.subject, asked_at=asked.asked_at, window_days=window
    )


def _uri(kind: str, key: str) -> str:
    return f"{kind}://{key}"


def _instant(value: Any) -> datetime:
    """A source date as a timezone-aware instant. No clock is read."""
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _node(
    *, tenant_id: str, at: datetime, uri: str, obligor_id: str, kind: str,
    label: str, body: Mapping[str, Any], observed_time: datetime | None,
    series: Mapping[str, str] | None = None,
) -> SignalEnvelope:
    """One node's attributes. ATTRIBUTED, therefore ingested LAST.

    `series` promotes the attribute that says WHICH LOGICAL SERIES this
    observation belongs to out of `payload_json` and onto the claim, because
    that is where the λ_c row's `series_key_attribute` reads it
    (`D-IMPL-333`). A spread point's series is its BOND; a grade's series is
    its OBLIGOR. Buried in the JSON blob the scorer cannot see it, and every
    bond's history would collapse into one series.
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
            **(series or {}),
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
        envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            subject_rule: subject, "subject_uri": subject,
            object_rule: obj, "object_uri": obj,
            "predicate": predicate,
        },
    )


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime,
) -> tuple[list[SignalEnvelope], list[SignalEnvelope]]:
    """``(edges, nodes)`` for one estate read, in the order they must be written."""
    lei = estate.obligor.lei
    anchor = _uri("obligor", lei)
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    def edge(subject: str, obj: str, predicate: str) -> None:
        edges.append(_edge(tenant_id=tenant_id, at=at, ordinal=len(edges),
                           subject=subject, obj=obj, predicate=predicate))

    nodes.append(_node(
        tenant_id=tenant_id, at=at, uri=anchor, obligor_id=lei, kind="obligor",
        label=estate.obligor.label,
        body={"lei": lei, "label": estate.obligor.label,
              "scale_version": estate.scale_version},
        observed_time=None,
    ))

    for instrument in estate.instruments:
        uri = _uri("instrument", instrument.instrument_id)
        edge(anchor, uri, "hasInstrument")
        nodes.append(_node(
            tenant_id=tenant_id, at=at, uri=uri, obligor_id=lei, kind="instrument",
            label=instrument.instrument_id,
            body={
                "instrument_id": instrument.instrument_id,
                # THE BASIS THE MARKET LEG IS NETTED ON. Fixed at issue and
                # never re-derived from the grade (`CP10-F-04`).
                "issue_band": instrument.issue_band,
                "tenor_years": instrument.tenor_years,
                "maturity": instrument.maturity.isoformat(),
                "seniority": instrument.seniority,
                "coupon_pct": str(instrument.coupon_pct),
            },
            observed_time=None,
        ))

    for point in estate.spreads:
        uri = _uri("spread", f"{point.instrument_id}/{point.obs_date.isoformat()}")
        edge(_uri("instrument", point.instrument_id), uri, "pricedAt")
        nodes.append(_node(
            tenant_id=tenant_id, at=at, uri=uri, obligor_id=lei, kind="spread",
            label=f"{point.instrument_id} {point.obs_date.isoformat()}",
            body={
                "instrument_id": point.instrument_id,
                "obs_date": point.obs_date.isoformat(),
                # THREE COMPONENTS, NEVER PRE-SUMMED (`RSM-G07`).
                "benchmark_bp": str(point.benchmark_bp),
                "market_oas_bp": str(point.market_oas_bp),
                "idiosyncratic_bp": str(point.idiosyncratic_bp),
            },
            # A REAL OBSERVATION DATE. The λ_c row decays against it.
            observed_time=_instant(point.obs_date),
            # THE SERIES THIS POINT BELONGS TO IS ITS BOND. Freshness is read
            # at the leading edge of each bond's own series (`D-IMPL-333`), so
            # a five-year history is evidence rather than staleness.
            series={"instrument_id": point.instrument_id},
        ))

    for grade in estate.grades:
        uri = _uri("grade", f"{lei}/{grade.valid_from.isoformat()}")
        edge(anchor, uri, "gradedAs")
        nodes.append(_node(
            tenant_id=tenant_id, at=at, uri=uri, obligor_id=lei, kind="grade",
            label=f"{grade.grade} from {grade.valid_from.isoformat()}",
            body={
                "grade": grade.grade,
                "notch": estate.scale.get(grade.grade),
                "band": estate.bands.get(grade.grade),
                "valid_from": grade.valid_from.isoformat(),
                "valid_to": grade.valid_to.isoformat() if grade.valid_to else None,
                "asserted_at": grade.asserted_at.isoformat(),
                "trigger": grade.trigger,
                "superseded_by": grade.superseded_by,
                "scale_version": estate.scale_version,
            },
            # THE EFFECTIVE DATE, not the booking date. Both are carried in the
            # body; the one the λ_c row decays against is when it took effect.
            observed_time=_instant(grade.valid_from),
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

    view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=at)
    unattributed = [
        record.claim.entity_uri for record in view.entities
        if not record.claim.attributes.get("node_kind")
    ]
    if unattributed:
        raise AssertionError(
            f"{len(unattributed)} of {len(view.entities)} admitted nodes carry"
            " no attributes after ingestion. The ingestion-order contract was"
            f" violated. First: {sorted(unattributed)[0]!r}"
        )


def build_band_gate(*, asked: ProductRequest) -> Any:
    """The DEPLOYMENT half of the declared product gate (`RSM-G23`).

    The Control Plane owns the gate's IDENTITY; the deployment owns the
    PREDICATE, and the resolver stamps `gate` and `gate_version` from the
    declaration (`D-IMPL-282` R-11).

    **What it refuses.** A payload that presents the residual without naming
    its basis, or that claims an obligor sits in a band it has migrated out of
    without saying so. `CP10-F-04`: the market leg is netted on the band the
    bond was ISSUED into, the error is directional, and the product may not
    present the residual as unqualified "pure issuer deterioration".
    """
    del asked

    def gate(
        *, candidate: ContextProductContract, evidence: object = None
    ) -> str | None:
        payload = candidate.payload
        if payload.get("benchmark_basis") != "static_issue_band":
            return (
                "the payload does not name its benchmark basis as"
                " `static_issue_band`; a residual served without its basis"
                " reads as pure issuer deterioration, which CP10-F-04 says it"
                " is not"
            )
        for series in payload.get("spread_series") or []:
            if series.get("benchmark_basis") != "static_issue_band":
                return (
                    f"spread series {series.get('instrument_id')!r} does not"
                    " name its benchmark basis"
                )
        migration = payload.get("band_migration") or {}
        if "has_migrated_out_of_issue_band" not in migration:
            return (
                "the payload does not state whether the obligor has migrated"
                " out of the band its bonds were issued into"
            )
        summary = payload.get("obligor_spread_summary")
        if summary is not None and not summary.get("dispersion"):
            return (
                "an obligor-level spread summary is served without its"
                " dispersion; a mean over instruments that may be pricing"
                " different things reads as an observation (RSM-G24)"
            )
        return None

    return gate


@dataclass(frozen=True)
class MigrationScenario:
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
    def policy_bundle_key(self) -> str:
        return "policy"

    @property
    def operator_parameter_keys(self) -> tuple[str, ...]:
        return tuple(config()["operators"])

    @property
    def plan_id(self) -> str:
        return f"cp-10.rating-migration/{self.estate.obligor.lei}"

    @property
    def max_ttl_seconds(self) -> int:
        """The CEILING — one day, the fastest series' own cadence."""
        return int(config()["half_life"]["rsm_spread"]["half_life_seconds"])

    @property
    def product_ttl_seconds(self) -> int:
        """Four hours. §B.1 — shorter than the ceiling and stated as a choice."""
        return 4 * 3600

    @property
    def declared(self) -> Mapping[str, Any]:
        defaults = config()["request_contract"]["defaults"]
        return {
            "granularity": self.asked.parameters.get(
                GRANULARITY, defaults["granularity"]
            ),
            "divergence_multiple": self.asked.parameters.get(
                DIVERGENCE_MULTIPLE, Decimal(2)
            ),
        }


def measured_completeness(estate: acquisition.Estate) -> Decimal:
    """`C` — resolved / served, measured on THIS estate read.

    Supplied to the SDK's reference scorer rather than scored here: the SDK
    cannot know that an obligor has no grade history, because that is a fact
    about this estate's registers rather than about the graph. Two terms —
    whether the obligor is rated at all, and spread coverage over the window.
    """
    rated = Decimal(1) if estate.grades else Decimal("0.5")
    expected = max((estate.window_to - estate.window_from).days * 5 // 7, 1)
    per_bond = [
        sum(1 for s in estate.spreads if s.instrument_id == i.instrument_id)
        for i in estate.instruments
    ]
    covered = (
        min(Decimal(1), Decimal(min(per_bond)) / Decimal(expected))
        if per_bond else Decimal(0)
    )
    return (rated * covered).quantize(Decimal("0.0001"))


def measured_semantic_consistency(estate: acquisition.Estate) -> Decimal:
    """`S` — every instrument's issue band resolves to a market OAS series.

    A band with no series is a consistency failure rather than a silent skip:
    the market component could not be netted out, so the residual would not be
    evidence about the obligor.
    """
    if not estate.instruments:
        return Decimal(1)
    priced = {s.instrument_id for s in estate.spreads}
    resolved = sum(1 for i in estate.instruments if i.instrument_id in priced)
    return (Decimal(resolved) / Decimal(len(estate.instruments))).quantize(
        Decimal("0.0001")
    )
