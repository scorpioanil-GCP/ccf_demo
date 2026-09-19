"""This deployment's own seams: its vocabulary, its envelopes, its gate.

**No governance lives here.** The door, both operators, `Π`, the L6 gates, the
five-dimension record and the delivery are one object the SDK owns
(`build_governed_resolver`). What this module contributes is what only a
deployment can know: which config keys, which envelopes, what counts as a
temporally coherent answer. **Not `D_c`** — this product declares no debt
metric of its own and the SDK's reference assessment applies (§E.2).

**THE TWO CLOCKS ARE NOT APPLIED HERE.** `as_of` bounds the READ (acquisition
issues it as a source-side filter); `known_as_of` is deliberately carried no
further than L3, because the assertion-time cut is `Π`'s and `Π` needs the
amendments that cut excludes in order to say WHICH AXIS excluded them. A
deployment that filtered by `assertedAt` before ingestion would leave the
exclusion record unfillable and put the product's whole subject outside the
fabric, where nothing replays it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

import acquisition

from ccf.controlplane.artifacts import PerspectiveArtifact
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.deployment import BootedFabric
from ccf.products.constraints import (
    ReferencePolicyConstraintResolver,
    TechnicalCapability,
)
from ccf.products.provenance import ProvenanceSource
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.contracts.canonical import content_hash

HERE = Path(__file__).parent

#: The declared parameter names, read back from the artifact by the tests so a
#: rename moves both sides at once.
FACILITY = "facility_id"
PRINCIPAL_SCOPE = "principal_scope"
AS_OF = "as_of"
KNOWN_AS_OF = "known_as_of"

#: The fabric's own kind vocabulary — the `classification_attribute_by_class`
#: values in `ccf_config.yaml`, which the operators admit on.
#: The attribute the operators classify on — the `kind` key the
#: `classification_attribute_by_class` mapping names in `ccf_config.yaml`.
#: The registered operator whose `depth_limit` is the backend ceiling. Named
#: once so the capability read and the config cannot drift.
TRAVERSAL_OPERATOR = "traversal.typed-neighborhood"

_KIND = "kind"

KIND_FACILITY = "facility"
KIND_AMENDMENT = "amendment"
KIND_COVENANT = "covenant"


def config() -> Mapping[str, Any]:
    return yaml.safe_load((HERE / "ccf_config.yaml").read_text(encoding="utf-8"))


def vocabulary() -> Mapping[str, Any]:
    """The SOURCES' names, from their own artifact — never from this module."""
    return yaml.safe_load(
        (HERE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8")
    )["declaration"]


def connection(*, root: Path) -> Mapping[str, str]:
    """Where the FABRIC's own L3 lives for this run. Never a source store."""
    profile = yaml.safe_load(
        (HERE / "backends.yaml").read_text(encoding="utf-8")
    )["declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {"database_path": str(root / f"{profile['prefix']}{profile['suffix']}")}


def perspective() -> PerspectiveArtifact:
    return PerspectiveArtifact(semver="1.0.0", **dict(config()["default_perspective"]))


def traversal_capability() -> TechnicalCapability:
    """The graph leg's ceiling, as a technical capability the SDK reads."""
    from ccf.products.constraints import CAPABILITY_TRAVERSAL_DEPTH

    return TechnicalCapability(
        capability=CAPABILITY_TRAVERSAL_DEPTH,
        maximum=Decimal(
            int(config()["operators"][TRAVERSAL_OPERATOR]["depth_limit"])
        ),
        identity="cp-08-covenant-graph",
    )


def request(
    *, facility_id: str | None, principal_scope: Sequence[str] | None,
    asked_at: datetime, as_of: str | None = None,
    known_as_of: str | None = None, **inert: Any,
) -> ProductRequest:
    """The question asked. A parameter the caller omitted stays omitted.

    **`as_of` and `known_as_of` are omitted rather than defaulted here**, so
    the class's RELATIVE defaults resolve — the identity offset, meaning the
    request's own instant (`D-IMPL-328`). Computing today's date in this
    function would be the deployment injecting `asked_at`, which is precisely
    what `D-IMPL-315` keeps out and what `D-IMPL-328` exists so nobody has to
    do.

    `**inert` carries the declared-and-inert parameters through unchanged when
    a caller sends one, so the CONTROL PLANE issues the refusal rather than
    this function silently dropping it.
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {}
    if facility_id is not None:
        parameters[FACILITY] = facility_id
    if principal_scope is not None:
        parameters[PRINCIPAL_SCOPE] = list(principal_scope)
    for name, value in ((AS_OF, as_of), (KNOWN_AS_OF, known_as_of)):
        if value is not None:
            parameters[name] = value
    parameters.update({k: v for k, v in inert.items() if v is not None})
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=facility_id or "",
        intent="drawdown-dispute",
        freshness="standard",
        asked_at=asked_at,
        parameters=parameters,
    )


def effective(
    booted: BootedFabric, registry: ControlPlaneProtocol, asked: ProductRequest
) -> Mapping[str, Any]:
    """What this ask is permitted to be, as the SDK's own resolver derives it.

    Acquisition needs `as_of` because it bounds the READ. This is the same
    resolver `GovernedResolver` uses, at the same instant, so the value here is
    the value the governed path resolves moments later — including the class's
    relative default when the caller omitted the parameter.

    Returns the empty mapping when the Control Plane refuses, and
    :func:`acquire_for` then touches no source store.
    """
    declared = ProductRequestContract.from_declared(
        booted.artifacts.get("request_contract")
    )
    source = ProvenanceSource(
        kind="artifact", identity="request_contract", version=content_hash(declared)
    )
    outcome = ReferencePolicyConstraintResolver(
        control_plane=registry, entitlement_key=None
    ).resolve(
        product_class=asked.schema_name, request=asked, declared=declared,
        declared_source=source, perspective=perspective(), intent=asked.intent,
        tenant=booted.tenant_id, capabilities=(traversal_capability(),),
        class_defaults=declared.defaults, class_source=source,
    )
    return {} if outcome.refusal is not None else outcome.evidence.values()


def acquire_for(
    booted: BootedFabric, registry: ControlPlaneProtocol, asked: ProductRequest,
    *, at_transaction: str | None = None,
) -> acquisition.FacilityWindow:
    """Read both stores for the question, at the bound governance resolved.

    **A refused question is not read.** Falling back to the caller's raw
    parameters here would run the read at bounds governance declined to grant.
    """
    import os

    values = effective(booted, registry, asked)
    if not values:
        # The Control Plane refused. Nothing is read, and NOTHING IS RAISED:
        # the governed path issues that refusal moments from now as data, and
        # an exception here would replace a governed determination with this
        # deployment's own error.
        return acquisition.nothing_acquired(
            str(asked.parameters.get(FACILITY, ""))
        )
    return acquisition.acquire(
        facility_id=str(values[FACILITY]),
        # VALID TIME bounds the read. ASSERTION TIME deliberately does not —
        # see the module docstring.
        as_of=str(values[AS_OF]),
        graph_url=os.environ["CCF_CP_08_FLUREE_URL"],
        graph_ledger=os.environ["CCF_CP_08_FLUREE_LEDGER"],
        postgres_dsn=os.environ["CCF_CP_08_POSTGRES_DSN"],
        postgres_schema=os.environ["CCF_CP_08_POSTGRES_SCHEMA"],
        vocabulary=vocabulary(),
        at_transaction=at_transaction,
    )


def _edge(source_id: str, target_id: str, relationship: str, *,
          source_key: str, tenant_id: str, at: datetime, ordinal: int) -> Any:
    """One typed edge, carrying NO attributes.

    .. warning::

       **Thin edges are emitted FIRST and attributed nodes LAST.** The last
       claim at a URI wins and does not merge, so an edge arriving after a node
       supersedes it and the node is then served with no kind and no terms —
       and NOTHING RAISES. The assertion in :func:`ingest` is what makes a
       reorder loud instead of silent. Do not "tidy" it.
    """
    from ccf.signal.envelope import SignalEnvelope, SourceIdentity

    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{relationship}/{ordinal}/{source_id}",
        source=SourceIdentity(system_id="covenant_graph"),
        ingestion_timestamp=at,
        observed_time=at,
        # EACH EDGE TYPE CARRIES ITS OWN SOURCE KEY — `amendment_ref` or
        # `covenant_ref` — because a resolution rule is selected by the payload
        # key it matches. Sharing one `source_id` across both types minted
        # every covenant endpoint as an amendment; measured, 4 of 11 admitted
        # nodes then carried no kind and the ingestion guard below caught it.
        raw_payload={source_key: source_id, "facility_ref": target_id,
                     "relationship": relationship},
    )


def _booking_instant(value: str | None) -> datetime | None:
    """An amendment's booking date, as the claim's own instant — or ``None``.

    `D-IMPL-341` (validation pass 2026-09-18): the amendment claim's
    ``valid_from`` is the instant the source ASSERTED it — the booking date,
    this product's assertion-time axis — because that is the clock §E.3
    anchors the TTL on ("the latest assertion in the SCORED OBSERVATION SET",
    as that clause was corrected on 2026-09-18) and the clock the `amendment`
    λ_c row now decays against. A date widens to
    midnight UTC, losslessly; an amendment the source never booked carries
    ``None`` and contributes no instant, exactly as it is placeable on no
    assertion axis. The request instant is never substituted.
    """
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _node(entity_id: str, kind: str, attributes: Mapping[str, str], *,
          tenant_id: str, at: datetime, observed: datetime | None) -> Any:
    """One attributed node. ``observed`` is the claim's own instant, stated at
    every call: the booking date for an amendment, the request instant for a
    facility or covenant record the source dates by nothing (`D-IMPL-341`)."""
    from ccf.signal.envelope import SignalEnvelope, SourceIdentity

    payload = {"kind": kind, **attributes}
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{kind}/{entity_id}",
        source=SourceIdentity(system_id="covenant_graph"),
        ingestion_timestamp=at,
        observed_time=observed,
        raw_payload=payload,
    )


def ingest(
    booted: BootedFabric, window: acquisition.FacilityWindow, *, at: datetime
) -> None:
    """Write the window into L3 through the ONE write handle, edges first.

    ``booted.handle.worker`` is the only write handle to L3 anywhere in this
    process (single-writer, CLAUDE.md §10).

    **EVERY amendment the valid-time read admitted is ingested**, including the
    ones `known_as_of` will exclude. That is deliberate and it is the design
    choice this product turns on: `Π` cannot report which axis excluded an
    amendment if the amendment never reached L3.
    """
    worker = booted.handle.worker
    v = vocabulary()

    ordinal = 0
    for amendment in window.amendments:
        worker.ingest(_edge(amendment.amendment_id, window.facility_id, "amends",
                            source_key="amendment_ref",
                            tenant_id=booted.tenant_id, at=at, ordinal=ordinal))
        ordinal += 1
    for covenant in window.covenants:
        worker.ingest(_edge(covenant.covenant_id, window.facility_id, "covenantOf",
                            source_key="covenant_ref",
                            tenant_id=booted.tenant_id, at=at, ordinal=ordinal))
        ordinal += 1

    # THE ANCHOR MATCHES ON ITS OWN KEY, and the reason is measured. Every
    # node carries `facility_id` so the policy operator can classify it — which
    # means every node ALSO matches a facility rule keyed on `facility_id`, and
    # the last covenant ingested then overwrote the facility's own claim with
    # `kind: covenant`. The entity survived with a kind, so the ingestion guard
    # below could not see it; the payload served five covenants where the
    # source had four. A distinct anchor key is what keeps the two apart.
    worker.ingest(_node(window.facility_id, KIND_FACILITY,
                        {"facility_anchor": window.facility_id,
                         "facility_id": window.facility_id},
                        tenant_id=booted.tenant_id, at=at, observed=at))
    for amendment in window.amendments:
        worker.ingest(_node(
            amendment.amendment_id, KIND_AMENDMENT,
            {
                "amendment_id": amendment.amendment_id,
                # MINTED AT ADMISSION BY THIS DEPLOYMENT, never joined in from
                # a source. The policy operator classifies on it: the envelope
                # is "whose facility subgraph may this principal see", so every
                # node in that subgraph has to carry the facility's id or the
                # principal-subgraph admits the facility alone.
                "facility_id": window.facility_id,
                "amendment_number": "" if amendment.number is None else str(amendment.number),
                "valid_from": amendment.valid_from or "",
                "valid_to": amendment.valid_to or "",
                # EMPTY rather than absent when the source has none, and
                # empty rather than `valid_from`: defaulting a missing
                # assertion time would make every booking lag vanish. All 25
                # facility amendments in this estate carry one, so this is the
                # product's rule rather than a case the estate forces.
                "asserted_at": amendment.asserted_at or "",
                "booking_lag_days": (
                    "" if amendment.booking_lag_days is None
                    else str(amendment.booking_lag_days)
                ),
            },
            tenant_id=booted.tenant_id, at=at,
            # THE BOOKING DATE IS THE CLAIM'S OWN INSTANT (`D-IMPL-341`).
            observed=_booking_instant(amendment.asserted_at)))
    for covenant in window.covenants:
        worker.ingest(_node(
            covenant.covenant_id, KIND_COVENANT,
            {
                "covenant_id": covenant.covenant_id,
                "facility_id": window.facility_id,
                "covenant_type": covenant.covenant_type or "",
                "threshold": covenant.threshold or "",
                "threshold_unit": covenant.threshold_unit or "",
            },
            tenant_id=booted.tenant_id, at=at, observed=at))

    view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=at)
    unkinded = [
        record.claim.entity_uri
        for record in view.entities
        if not record.claim.attributes.get("kind")
    ]
    if unkinded:
        raise AssertionError(
            f"{len(unkinded)} of {len(view.entities)} admitted nodes carry no kind"
            " after ingestion. The ingestion-order contract was violated: a thin"
            " edge claim arrived after a node's own claim and superseded it."
            f" First: {sorted(unkinded)[0]!r}"
        )


def declared_debt_factor(name: str) -> str:
    """One of the two `D_c` factors this deployment DECLARES rather than computes.

    The SDK's reference scorer derives freshness from the λ_c table and the
    observations' own ages; completeness and semantic consistency are
    statements only the deployment can make. They live in
    ``artifacts/debt-declaration.yaml``, which carries the measurement behind
    each — values belong in artifacts, not in code (CLAUDE.md §6.4).
    """
    return str(
        yaml.safe_load(
            (HERE / "artifacts" / "debt-declaration.yaml").read_text(encoding="utf-8")
        )["declaration"][name]
    )


@dataclass(frozen=True)
class CovenantScenario:
    """What one run needs — satisfies ``produce``'s structural expectation."""

    window: acquisition.FacilityWindow
    asked: ProductRequest
    booted_at: datetime

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
        return f"cp-08.covenant-in-force/{self.window.facility_id}"

    @property
    def max_ttl_seconds(self) -> int:
        return int(config()["half_life"]["covenant"]["half_life_seconds"])

    @property
    def product_ttl_seconds(self) -> int:
        """From the entity-freshness anchor the class declares.

        **THE DUAL TTL `CP-SPEC-008` §E.3 DESCRIBES IS NOT IMPLEMENTED HERE**,
        and its absence is stated rather than left to be noticed. A closed
        as-of answer should carry a longer TTL than a live one, and choosing
        the boundary between *closed* and *live* is a governance decision this
        module may not take alone. `CIF-G15` is therefore the one declared gate
        with no implementation behind it yet, and it is named in the roster as
        outstanding rather than quietly dropped.
        """
        return int(config()["half_life"]["amendment"]["half_life_seconds"])


def temporal_coherence_violation(candidate: Any) -> str | None:
    """The class's declared invariant, held against the answer about to be served.

    **Every admitted amendment satisfies BOTH bounds.** An admitted amendment
    violating either means one of the two filters was dropped somewhere between
    the read and the projection — and a product that dropped one is answering a
    different question from the one asked, with no outward sign that it did.

    Returns a violation string or ``None``. The gate's governed IDENTITY is the
    Control Plane's (`cp-08.temporal-coherence`); this callable supplies only
    what counts as a violation, because no universal vocabulary has a token for
    an invariant that belongs to one product.
    """
    payload = getattr(candidate, "payload", None)
    if not isinstance(payload, Mapping):
        return None
    window = payload.get("window") or {}
    as_of, known_as_of = window.get("as_of"), window.get("known_as_of")
    if not as_of or not known_as_of:
        return (
            "the payload carries no window, so neither temporal bound can be"
            " checked against what was served"
        )
    for entry in payload.get("amendments_in_force_and_known", ()):
        valid_from, asserted_at = entry.get("valid_from"), entry.get("asserted_at")
        identifier = entry.get("amendment_id")
        if not valid_from or valid_from > as_of:
            return (
                f"{identifier} was served as in force at as_of={as_of} with"
                f" effective date {valid_from!r}: the valid-time filter was"
                " dropped"
            )
        if not asserted_at or asserted_at > known_as_of:
            return (
                f"{identifier} was served as known at known_as_of={known_as_of}"
                f" with booking date {asserted_at!r}: the assertion-time filter"
                " was dropped"
            )
    return None
