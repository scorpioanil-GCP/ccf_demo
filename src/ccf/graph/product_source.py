"""The tier-2 read path — an admitted Context Product as a queryable source.

SDK-defined extension (CLAUDE.md §11), attaching to whitepaper §6.6 (the
recursive context-enrichment case: one fabric's Context Product answering
another fabric's read) and §7.3 (the Context Graph as queryable state — here
answered from governed product state rather than a persisted graph). The
Phase 15.2 D-08 ruling is the design of record: **same seam, admitted at
mount** — a :class:`ProductSource` answers the same
:class:`~ccf.graph.protocols.GraphReader` Protocol every substrate answers,
and its constructor accepts only the token-guarded
`AdmittedProduct` (src/ccf/peering/admission.py::AdmittedProduct), the type
`PeeringAdmissionGate.admit` (src/ccf/peering/admission.py::PeeringAdmissionGate)
alone can produce. Admission-as-the-only-door is therefore a **type-system
property**, not a review convention: an unadmitted product cannot exist here,
because the value this module consumes cannot be constructed anywhere else —
every forced path fails at construction with
`AdmissionBypassError` (src/ccf/peering/admission.py::AdmissionBypassError).

**Tier 3 is pre-wired, not deferred.** A lower-trust source class later means
*another gate producing the same admitted wrapper* — a new admission path
constructing the same ``AdmittedProduct`` — and this module changes not at
all. The attestation vocabulary already expresses tier 3 as a value of the
existing schema (D-09; :class:`~ccf.graph.protocols.SourceAttestation`), so
no refactor stands between this seam and a future source class.

**The ephemerality commitment.** The views this source answers are owned by
the execution that asked and terminate in the projection: nothing a
``ProductSource`` answers enters L3, no write handle exists anywhere in this
module, and the single-writer invariant (CLAUDE.md §10, INV-CH7-10) is not
implicated because there is nothing here that could write. The admission
gate's own words carry the same force and are quoted here deliberately —
*"Admission is not a write. What this value confers is the right to be
offered to L2 — L2 remains the only holder of a graph write handle"*
(`AdmittedProduct` at src/ccf/peering/admission.py::AdmittedProduct) — and mounting is
less than an offer: a mounted product is *read*, never offered to L2 at all.

**Why mount performs no payload-size ceiling of its own.** The admission
gate enforces the Control Plane payload ceiling — refusing with
`PayloadTooLargeRefusal` (src/ccf/peering/admission.py::PayloadTooLargeRefusal)
before anything decodes — **before** an ``AdmittedProduct`` can exist, and
this module's constructor accepts only ``AdmittedProduct``. A second ceiling
here would guard a door that cannot be reached with an oversized payload.

**No query engine, by design.** The mounted records are answered by the one
scan-and-filter every adapter degrades to —
`answer` (src/ccf/graph/fallback.py::answer) — whose re-applied as-of
predicate is the *only* as-of enforcement these verbatim payload records
receive (`GQ-12` at docs/GRAPH_QUERY_SEMANTICS.md:237), and whose
set-intersection is the *only* ``allowed_entities`` enforcement (`GQ-15` at
docs/GRAPH_QUERY_SEMANTICS.md:300) — no source-local code exists for
either. Ordering, lineage-at-boundary, supersession-as-of, and freezing come
from the substrate-neutral materialization core
(`materialize_view` at src/ccf/graph/reader.py::materialize_view), never
re-implemented here (`GQ-22` at docs/GRAPH_QUERY_SEMANTICS.md:461). This is
the KV-floor pattern over governed records.

This module imports no transport, no writer, and nothing from
``ccf.graph._writer``. Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import TypeVar

from pydantic import ValidationError

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph import fallback
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphReader,
    GraphView,
    RelationshipRecord,
    SourceAttestation,
)
from ccf.graph.reader import (
    ENTITY_KIND,
    RELATIONSHIP_KIND,
    Row,
    materialize_view,
)
from ccf.peering.admission import AdmittedProduct, verify_admission_provenance
from ccf.products.gates import GateRefusal

__ccf_mode__ = "algorithmic"

__all__ = [
    "GATE_PRODUCT_MOUNT",
    "ProductMountRefusal",
    "ProductSource",
    "mount_product_source",
]

#: The gate name a mount refusal reports. A string rather than an enum for the
#: same reason the admission gates use strings: the value lands in a refusal
#: an operator reads in a log.
GATE_PRODUCT_MOUNT = "product-mount"

#: The well-known top-level payload key of the tier-2 convention
#: (`GQ-25` at docs/GRAPH_QUERY_SEMANTICS.md:502).
_GRAPH_STATE_KEY = "graph_state"


class ProductMountRefusal(GateRefusal):
    """The mount refused: the admitted product carries no answerable graph state.

    A returned value, never an exception — the refusal-value discipline of
    the fabric's gates, derived from
    :class:`~ccf.products.gates.GateRefusal` rather than paralleling it
    (the derivation style of
    `src/ccf/peering/admission.py::AdmissionRefusal`): a product that cannot
    mount meets the
    same gate discipline every other refused product meets, and a caller
    inspecting ``gate`` and ``detail`` reads this refusal exactly as it
    reads an admission or TTL refusal.

    Refusal here is the `GQ-25` at docs/GRAPH_QUERY_SEMANTICS.md:502
    commitment: a payload without the ``graph_state`` shape — or whose items
    fail record validation — refuses **at mount**, before any query is
    asked, so a source that cannot answer correctly is refused while wiring
    rather than discovered mid-question. A malformed ``AdmittedProduct``
    wrapper itself is not a case this value covers: the wrapper is
    impossible to construct outside the admission gate, and the token guard
    already raises
    `AdmissionBypassError` (src/ccf/peering/admission.py::AdmissionBypassError).

    Attributes:
        tenant_id: The tenant the refused product claims — the admitted
            contract's own ``tenant_id``.
        schema_name: The product class of the refused product, so an
            operator reading a log knows *which* product class shipped a
            payload that does not mount.
        reason: What was missing or invalid, machine-shaped: the absent
            key, or the index and contract of the item that failed
            validation. ``detail`` carries the operator-readable sentence.
    """

    tenant_id: str
    schema_name: str
    reason: str


def _refuse(
    admitted: AdmittedProduct, *, reason: str, detail: str
) -> ProductMountRefusal:
    """Build the typed mount refusal carrying the product's identifiers."""
    return ProductMountRefusal(
        gate=GATE_PRODUCT_MOUNT,
        tenant_id=admitted.product.tenant_id,
        schema_name=admitted.product.schema_name,
        reason=reason,
        detail=detail,
    )


_RecordT = TypeVar("_RecordT", EntityRecord, RelationshipRecord)


def _validated_member(
    admitted: AdmittedProduct,
    graph_state: Mapping[str, object],
    member: str,
    contract: type[_RecordT],
) -> tuple[_RecordT, ...] | ProductMountRefusal:
    """Validate one ``graph_state`` member list against its record contract.

    Two checks per item, both mount-time (`GQ-25` at
    docs/GRAPH_QUERY_SEMANTICS.md:502): the item ``model_validate``\\ s
    against the existing record contract, and the validated record claims
    the *product's own* tenant — a payload smuggling another tenant's
    records would otherwise answer them to tenant-matched queries, the
    cross-tenant mix `GQ-27` at docs/GRAPH_QUERY_SEMANTICS.md:529 forbids
    (T-15.2-02).
    """
    items = graph_state.get(member)
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return _refuse(
            admitted,
            reason=f"{_GRAPH_STATE_KEY}.{member} is not a list",
            detail=(
                f"{_GRAPH_STATE_KEY}.{member} must be a list of"
                f" {contract.__name__} items; the payload carries"
                f" {type(items).__name__} (`GQ-25` in"
                " docs/GRAPH_QUERY_SEMANTICS.md)"
            ),
        )
    tenant_id = admitted.product.tenant_id
    records: list[_RecordT] = []
    for index, item in enumerate(items):
        try:
            record = contract.model_validate(item)
        except ValidationError as invalid:
            return _refuse(
                admitted,
                reason=(
                    f"{_GRAPH_STATE_KEY}.{member}[{index}] is not a valid"
                    f" {contract.__name__}"
                ),
                detail=(
                    f"{_GRAPH_STATE_KEY}.{member}[{index}] failed"
                    f" {contract.__name__} validation: {invalid}"
                ),
            )
        if record.claim.tenant_id != tenant_id:
            return _refuse(
                admitted,
                reason=(
                    f"{_GRAPH_STATE_KEY}.{member}[{index}] claims tenant"
                    f" {record.claim.tenant_id!r}"
                ),
                detail=(
                    f"{_GRAPH_STATE_KEY}.{member}[{index}] claims tenant"
                    f" {record.claim.tenant_id!r} but the product is tenant"
                    f" {tenant_id!r}; a mounted source never answers a"
                    " cross-tenant mix (`GQ-27` in"
                    " docs/GRAPH_QUERY_SEMANTICS.md, T-15.2-02)"
                ),
            )
        records.append(record)
    return tuple(records)


def mount_product_source(
    *, admitted: AdmittedProduct
) -> ProductSource | ProductMountRefusal:
    """Mount an admitted product as a queryable tier-2 source — the one door.

    Validates the tier-2 payload convention (`GQ-25` at
    docs/GRAPH_QUERY_SEMANTICS.md:502): the product's payload carries a
    top-level ``graph_state`` mapping holding ``entities`` and
    ``relationships`` lists whose items ``model_validate`` against the
    existing :class:`~ccf.graph.protocols.EntityRecord` /
    :class:`~ccf.graph.protocols.RelationshipRecord` contracts — no new
    schema machinery, and nothing about the records re-shaped for
    transport: they retain their temporal metadata, which is what makes
    the fallback's as-of re-application enforceable over them (`GQ-12` at
    docs/GRAPH_QUERY_SEMANTICS.md:237).

    One check beyond bare record validation: every carried record must
    claim the *product's own* tenant. A payload smuggling another tenant's
    records inside a tenant-scoped product would otherwise answer them to
    that tenant's queries — the cross-tenant mix `GQ-27` at
    docs/GRAPH_QUERY_SEMANTICS.md:529 forbids on every answer (threat
    T-15.2-02) — so the mismatch refuses at mount, where every other
    cannot-answer-correctly condition refuses.

    Returns:
        A :class:`ProductSource` when the payload mounts, otherwise a
        :class:`ProductMountRefusal` naming what was missing or invalid —
        a returned value, never an exception.
    """
    # `D-IMPL-337`. A governed boundary: exported, and mounting relies on the
    # authority that only Control Plane peering admission establishes. A
    # bypass here puts an unverified federated product on the path toward L3.
    admitted = verify_admission_provenance(admitted)

    payload = admitted.product.payload
    graph_state = payload.get(_GRAPH_STATE_KEY)
    if not isinstance(graph_state, Mapping):
        return _refuse(
            admitted,
            reason=f"missing {_GRAPH_STATE_KEY}",
            detail=(
                f"the payload carries no top-level {_GRAPH_STATE_KEY!r}"
                " mapping; a product without the tier-2 payload shape is"
                " not a queryable source (`GQ-25` in"
                " docs/GRAPH_QUERY_SEMANTICS.md)"
            ),
        )

    entities = _validated_member(admitted, graph_state, "entities", EntityRecord)
    if isinstance(entities, ProductMountRefusal):
        return entities
    relationships = _validated_member(
        admitted, graph_state, "relationships", RelationshipRecord
    )
    if isinstance(relationships, ProductMountRefusal):
        return relationships

    return ProductSource(
        admitted=admitted, entities=entities, relationships=relationships
    )


def _entity_row(record: EntityRecord) -> dict[str, object]:
    """Render one validated record back into the core's entity row shape.

    The row vocabulary is exactly what the SQL and dict backends hand the
    materialization core; ``claim_json``'s lineage member is ignored there —
    the lineage supplier is the one source of lineage rows, so the boundary
    rendering cannot be bypassed by what the payload happened to carry
    inline.
    """
    return {
        "entity_uri": record.claim.entity_uri,
        "claim_id": record.claim_id,
        "claim_json": json.dumps(record.claim.model_dump(mode="json")),
        "policy_bundle_version": record.policy_bundle_version,
        "superseded_by": record.superseded_by,
        "superseded_at": (
            None
            if record.superseded_at is None
            else canonical_timestamp(record.superseded_at)
        ),
    }


def _relationship_row(record: RelationshipRecord) -> dict[str, object]:
    """Render one validated record back into the core's relationship row shape."""
    return {
        "relationship_key": record.relationship_key,
        "claim_id": record.claim_id,
        "claim_json": json.dumps(record.claim.model_dump(mode="json")),
        "policy_bundle_version": record.policy_bundle_version,
        "superseded_by": record.superseded_by,
        "superseded_at": (
            None
            if record.superseded_at is None
            else canonical_timestamp(record.superseded_at)
        ),
    }


class ProductSource:
    """A mounted admitted product behind the same seam every substrate answers.

    SDK-defined (CLAUDE.md §11; whitepaper §6.6) — the Phase 15.2 D-08
    tier-2 source. Structurally conforms to
    :class:`~ccf.graph.protocols.GraphReader`; there is no method here that
    mutates state, no writer import anywhere in this module, and the views
    it answers are ephemeral — owned by the asking execution, terminating in
    the projection, never entering L3 (see the module docstring).

    **Constructed through :func:`mount_product_source` only.** The direct
    constructor is private by convention: the mount function is the door,
    because it is where the tier-2 payload convention (`GQ-25` at
    docs/GRAPH_QUERY_SEMANTICS.md:502) is validated and where a
    cannot-answer product is refused as a value. What the constructor
    *types* is the load-bearing D-08 property: it accepts only the
    token-guarded :class:`~ccf.peering.admission.AdmittedProduct`, so a
    source over an unadmitted product cannot exist — and tier 3 later means
    another gate producing the same wrapper, zero refactor here.
    """

    def __init__(
        self,
        *,
        admitted: AdmittedProduct,
        entities: tuple[EntityRecord, ...],
        relationships: tuple[RelationshipRecord, ...],
    ) -> None:
        """Private by convention — :func:`mount_product_source` is the door.

        Args:
            admitted: The token-guarded wrapper only
                ``PeeringAdmissionGate.admit`` can produce. Accepting only
                this type is the D-08 admission seam as a type-system
                property.
            entities: The payload's entity records, already validated
                against :class:`~ccf.graph.protocols.EntityRecord` by the
                mount function.
            relationships: The payload's relationship records, already
                validated against
                :class:`~ccf.graph.protocols.RelationshipRecord`.
        """
        # `D-IMPL-337`. A governed boundary in its own right: `ProductSource`
        # is in `__all__` and this constructor is private BY CONVENTION only,
        # so an externally supplied value reaches it without passing
        # `mount_product_source`. The census filed this as module-private on
        # the strength of the leading underscore in `__init__` — its own false
        # negative, and the reason the registry is the source of truth.
        admitted = verify_admission_provenance(admitted)

        self._admitted = admitted
        self._tenant_id = admitted.product.tenant_id
        self._entities = entities
        self._relationships = relationships
        lineage_rows: dict[tuple[str, str, str], tuple[Row, ...]] = {}
        for record in entities:
            lineage_rows[(ENTITY_KIND, record.claim.entity_uri, record.claim_id)] = (
                tuple(
                    {"entry_json": json.dumps(entry.model_dump(mode="json"))}
                    for entry in record.claim.lineage
                )
            )
        for edge in relationships:
            lineage_rows[
                (RELATIONSHIP_KIND, edge.relationship_key, edge.claim_id)
            ] = tuple(
                {"entry_json": json.dumps(entry.model_dump(mode="json"))}
                for entry in edge.claim.lineage
            )
        self._lineage_rows = lineage_rows

    def _lineage_rows_for(self) -> Callable[[str, str, str], Sequence[Row]]:
        """A lineage supplier over the carried records' own lineage.

        Returns *rows*, not lineage: the boundary rendering happens inside
        the materialization core and cannot be reimplemented here — the
        same arrangement as the SQL client's closure over its
        ``SELECT_LINEAGE`` statement, with an index lookup where the SQL
        client has a query.
        """

        def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
            return self._lineage_rows.get((kind, node_key, claim_id), ())

        return rows_for

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` over the mounted records — fallback semantics, whole.

        What a mounted product answers is `GQ-26` at
        docs/GRAPH_QUERY_SEMANTICS.md:516: the fallback semantics of the
        prose over the product's ``graph_state`` records. No query engine
        exists here — :func:`ccf.graph.fallback.answer` is the whole
        implementation, and two of its behaviors are load-bearing for this
        tier:

        * its re-applied as-of survival predicate is the **only** as-of
          enforcement these verbatim payload records receive — the
          fallback input contract, `GQ-12` at
          docs/GRAPH_QUERY_SEMANTICS.md:237: nothing upstream has
          pre-filtered a mounted payload;
        * its set-intersection is the **only** ``allowed_entities``
          enforcement (`GQ-15` at docs/GRAPH_QUERY_SEMANTICS.md:300) — no
          source-local code exists for the uniform rule, which is exactly
          the D-IMPL-87 resolution's point about the fallback tier.

        The surviving records then order and freeze through the
        substrate-neutral materialization core
        (:func:`ccf.graph.reader.materialize_view` — lineage-at-boundary,
        supersession-as-of, interface-owned ordering per `GQ-22` at
        docs/GRAPH_QUERY_SEMANTICS.md:461), never a local
        re-implementation.

        **Tenant scope:** a query whose ``tenant_id`` does not match the
        mounted product's tenant is answered with the **empty view** —
        never a cross-tenant mix and never a raise — per the source
        tenant-mismatch clause, `GQ-27` at
        docs/GRAPH_QUERY_SEMANTICS.md:529. The contrast that clause states
        is deliberate: ``SnapshotReader`` *raises*
        (:class:`~ccf.replay.snapshots.SnapshotScopeViolation`) on a
        tenant mismatch because a replay pin names exactly one scope — *a
        source answers questions; a pin enforces one.* Both behaviors are
        normative, and they are different on purpose. An empty answer is
        an answer, never an error (`GQ-23` at
        docs/GRAPH_QUERY_SEMANTICS.md:474). ``q.as_of`` arrives as data —
        this method reads no clock.
        """
        # SEC-023 (`D-IMPL-374`, ruling (3)): a mounted peer product's labels were
        # governed by no local L2, so a classification query refuses unless the
        # caller stamped it with the authority it holds itself answerable for.
        from ccf.graph.protocols import require_query_classification_authority

        require_query_classification_authority(q)
        if q.tenant_id != self._tenant_id:
            return GraphView(tenant_id=q.tenant_id, as_of=q.as_of)
        entities, relationships = fallback.answer(
            self._entities, self._relationships, query=q
        )
        return materialize_view(
            entity_rows=tuple(_entity_row(record) for record in entities),
            relationship_rows=tuple(
                _relationship_row(record) for record in relationships
            ),
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            lineage_rows_for=self._lineage_rows_for(),
        )

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Return the state the mounted product holds for ``tenant_id`` at ``at``.

        The D-07 derivation, the same as every reader's: ``as_of`` is
        **defined** as the degenerate everything-question — `GQ-21` at
        docs/GRAPH_QUERY_SEMANTICS.md:446. Identical records, identical
        ordering, identical canonical bytes.
        """
        return self.query(GraphQuery(tenant_id=tenant_id, as_of=at))

    @property
    def attestation(self) -> SourceAttestation:
        """Tier 2 — the mounted admitted product's well-known value (D-09).

        SDK-defined per CLAUDE.md §11: policy bindings were verified at the
        peering admission gate, lineage is carried inside the mounted
        product's payload, and ``peer`` names the federation peer whose
        admission produced the records.
        """
        return SourceAttestation(
            policy_binding="admission-verified",
            lineage="product-carried",
            peer=self._admitted.peer,
        )

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        """Every claim the product carries about ``entity_uri``, oldest first.

        A mounted product answers only what it carries: the history of a
        key is the carried records for that key, verbatim — which is
        already the boundary-``None`` rendering (full lineage, intact
        supersession edges), because payload records retain their temporal
        metadata (`GQ-25` at docs/GRAPH_QUERY_SEMANTICS.md:502). A foreign
        tenant's ask answers empty, the source posture of `GQ-27` at
        docs/GRAPH_QUERY_SEMANTICS.md:529 applied to the history reads.
        """
        if tenant_id != self._tenant_id:
            return ()
        return tuple(
            sorted(
                (
                    record
                    for record in self._entities
                    if record.claim.entity_uri == entity_uri
                ),
                key=lambda record: record.claim.observed_at,
            )
        )

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Every claim the product carries about one edge, oldest first."""
        if tenant_id != self._tenant_id:
            return ()
        return tuple(
            sorted(
                (
                    record
                    for record in self._relationships
                    if record.relationship_key == relationship_key
                ),
                key=lambda record: record.claim.observed_at,
            )
        )


def _graph_reader_conformance(source: ProductSource) -> GraphReader:
    """Structural-typing witness: strict mypy proves the Protocol is satisfied.

    The import-time-conformance discipline of ``ccf.operators.categories``
    applied at the reader seam: a ``ProductSource`` that stopped satisfying
    :class:`~ccf.graph.protocols.GraphReader` would fail the build here,
    not at a distant call site.
    """
    return source
