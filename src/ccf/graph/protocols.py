"""The ``GraphStore`` seam: the ``GraphReader`` / ``GraphWriter`` Protocol split.

Whitepaper §7.3 (the Context Graph as a first-class persisted computational
primitive); DESIGN.md §2A.5.2 (the D-IMPL-34 six-semantics requirement surface)
and §2A.5.3 (layer 1 of the D-IMPL-41 single-writer stack).

**Why two Protocols rather than one store.** The split is the seam every other
layer of single-writer enforcement hangs on. A read-path component's
constructor accepts a :class:`GraphReader`; there is therefore no write handle
in its signature to inject, and the absence is a *structural property of the
type*, not a convention someone maintains (INV-CH7-10, INV-CH7-15). Strict
mypy turns a write attempt on a reader into a build failure.

**The six semantics** every conforming backend must provide (D-IMPL-34), each
exercised by ``tests/conformance/test_graphstore.py`` against every backend:

1. compound uniqueness on ``(tenant_id, entity_uri)`` *at the persistence
   tier*, not the application layer (INV-CH7-16);
2. idempotent upsert with set-union lineage accumulation (INV-CH7-17) — the
   upsert is idempotent, the lineage deliberately is not;
3. logical supersession via ``superseded_by`` / ``superseded_at`` with as-of
   reads (INV-CH7-21);
4. append-only-forward — no claim content is ever updated, no row ever deleted
   (INV-CH7-04);
5. per-relationship-type edge lineage (INV-CH7-20);
6. bitemporal read support (INV-CH7-14).

Physical layout — table decomposition, indexing, partitioning — is
backend-internal (the whitepaper's "~10 collections" is reference grounding,
not a normative count).

**The query vocabulary (Phase 15.2).** :class:`GraphQuery`,
:class:`TraversalSpec`, :class:`QueryFragment`, and :class:`SourceAttestation`
render the normative vocabulary of ``docs/GRAPH_QUERY_SEMANTICS.md``
(semantics version 1.0.0) as frozen values. The prose decides; these
contracts carry it — a dispute about what a query means is resolved by
quoting the clause, never by reading an adapter.

**The temporal vocabulary (Phase 24.5, ledger rows ``24.5-L-03`` /
``24.5-L-01``).** :data:`TEMPORAL_AXES` names the three time axes a graph read
can be bounded on — event time, transaction time, CCF ``as_of`` — as distinct
SDK vocabulary; :class:`StoreSnapshotPin` carries a transaction-time pin as a
value :class:`GraphQuery.as_of` structurally cannot accept; and
:class:`SnapshotPinnable` is the Protocol a reader implements when its
substrate can answer at a pinned transaction. ``D-IMPL-88`` is the ruling the
three uphold: a store's transaction counter never implements ``as_of``.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from types import TracebackType
from typing import Final, Literal, Protocol, runtime_checkable

from pydantic import Field, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.contracts.claims import EntityClaim, RelationshipClaim
from ccf.peering.protocol import PeerRef

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_STORE_SNAPSHOT_PIN",
    "TEMPORAL_AXES",
    "WRITER_LEASE_SCOPES",
    "EntityRecord",
    "GraphQuery",
    "GraphReader",
    "GraphView",
    "GraphWriter",
    "LineageMode",
    "PolicyBindingMode",
    "ProcessScopedWriterLease",
    "QueryFragment",
    "RelationshipRecord",
    "SnapshotPinnable",
    "SourceAttestation",
    "StoreSnapshotPin",
    "TemporalAxis",
    "TraversalDepthCapability",
    "TraversalDirection",
    "TraversalSpec",
    "UpsertResult",
    "WriterLease",
    "WriterLeaseHeld",
    "WriterLeaseRequired",
    "WriterLeaseScope",
    "WriterLeaseSource",
    "acquire_declared_writer_lease",
]

#: The three time axes a graph read can be bounded on — closed vocabulary,
#: SDK-defined per CLAUDE.md §11 (ledger row ``24.5-L-03``). One definition,
#: so every surface that names an axis — a pin's declared axis, an adapter's
#: module docstring, a replay record — spells it from here and cannot drift.
#: The three are DIFFERENT facts about a claim, and no one of them stands in
#: for another:
#:
#: * ``"event-time"`` is when the WORLD changed — a claim's ``observed_at``
#:   and its ``valid_from`` / ``valid_to`` window (whitepaper §7.3, the T
#:   axis); on Fluree this is what its backdatable ``@iso:`` addressing
#:   speaks. Arbitrary, non-monotone, frequently late-arriving: data.
#: * ``"transaction-time"`` is when the STORE recorded it — Fluree's
#:   monotonic commit counter ``t``, a SQL substrate's nothing at all. It
#:   advances on a data no-op and orders writes, not observations. A fact
#:   about a read, worth recording as lineage, and never a temporal cut.
#: * ``"as-of"`` is CCF's own cut over observations — ``GraphQuery.as_of``,
#:   the observed-time boundary every answer applies (``GQ-07`` at
#:   docs/GRAPH_QUERY_SEMANTICS.md:148, INV-CH7-14). ``D-IMPL-88``: a
#:   transaction counter never implements it, because the two diverge on
#:   exactly the late arrivals and supersessions the cut exists to render.
TemporalAxis = Literal["event-time", "transaction-time", "as-of"]

#: The closed roster of :data:`TemporalAxis`, in the order the sentences above
#: state them — the ``ccf.operators.base.CATEGORY_ORDER`` form, so a consumer
#: can iterate the vocabulary rather than re-list it.
TEMPORAL_AXES: Final[tuple[TemporalAxis, ...]] = (
    "event-time",
    "transaction-time",
    "as-of",
)

#: The closed policy-binding mode vocabulary of :class:`SourceAttestation`
#: (D-09) — SDK-defined per CLAUDE.md §11. Named so that every surface that
#: references the vocabulary (the attestation itself, a product class's
#: accepted-mode sets, the gate refusal) spells it from one definition and
#: cannot drift.
PolicyBindingMode = Literal["assembly-stamped", "admission-verified", "none"]

#: The closed lineage mode vocabulary of :class:`SourceAttestation` (D-09) —
#: SDK-defined per CLAUDE.md §11. One definition for every referencing
#: surface, exactly as :data:`PolicyBindingMode`.
LineageMode = Literal["graph-supplied", "product-carried", "none"]

#: The closed direction vocabulary of :class:`TraversalSpec` (ledger row
#: ``24.5-L-06``; `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201) — SDK-defined
#: per CLAUDE.md §11, one definition exactly as :data:`PolicyBindingMode`.
#: ``"undirected"`` crosses an edge from either endpoint — the 1.0.x walk, a
#: NEIGHBORHOOD. ``"forward"`` crosses an edge only from ``subject_uri`` to
#: ``object_uri`` AS STORED — the graph's own orientation, so the walk reaches
#: DESCENDANTS in whatever sense the deployment normalized at ingest (a
#: deployment that wants parent→child stores parent→child; the fabric does
#: not reorient). No ``"backward"``: a reverse walk is the same edge stored the
#: other way, and a third value nobody has needed is a value nobody chose.
TraversalDirection = Literal["undirected", "forward"]


def _policy_family_is_partial(
    versions: frozenset[str] | None,
    attribute_by_class: Mapping[str, str] | None,
    classifications: frozenset[str] | None,
) -> bool:
    """True when some but not all policy-family fields are present.

    A family, when present, carries **all** of its fields; a
    partially-specified family is not a legal value and the contract refuses
    it at construction (``GQ-02`` at docs/GRAPH_QUERY_SEMANTICS.md:64).
    Shared by :class:`GraphQuery` and :class:`QueryFragment`, which carry the
    same three policy-family fields.
    """
    present = (
        versions is not None,
        attribute_by_class is not None,
        classifications is not None,
    )
    return any(present) and not all(present)


class EntityRecord(CCFContract):
    """One persisted entity claim as the graph holds it.

    Whitepaper §7.3; DESIGN.md §2A.3.3 (supersession record shape).

    The record is the claim *plus* the graph-side facts the claim itself cannot
    carry: its content identity, the Control Plane policy bundle bound to it at
    assembly time (the P axis, stamped at assembly and never post-processed),
    and the supersession edge.

    Attributes:
        claim_id: Content identity of the claim's non-lineage fields. Lineage
            is excluded deliberately: L accumulates by set-union over the life
            of a claim (INV-CH7-17), so an identity that moved when evidence
            arrived would make "the same claim" unaddressable.
        claim: The claim itself, with lineage as accumulated to date.
        policy_bundle_version: Control Plane version of the policy bundle in
            force when this claim was assembled (INV-CH7-03).
        superseded_by: ``claim_id`` of the claim that superseded this one, or
            ``None`` while it is current. The prior claim *remains* — overwrite
            in place would make replay at T+2 years structurally impossible.
        superseded_at: When supersession took effect, on the observed-time axis.
    """

    claim_id: str
    claim: EntityClaim
    policy_bundle_version: str
    superseded_by: str | None = None
    superseded_at: datetime | None = None


class RelationshipRecord(CCFContract):
    """One persisted relationship claim as the graph holds it.

    Whitepaper §7.3; INV-CH7-20 (relationships are typed first-class persisted
    edges carrying their own per-relationship-type lineage, never derived
    joins). Fields mirror :class:`EntityRecord`; ``relationship_key`` is the
    backend-neutral content identity of the edge's ``(type, subject, object)``
    triple.
    """

    relationship_key: str
    claim_id: str
    claim: RelationshipClaim
    policy_bundle_version: str
    superseded_by: str | None = None
    superseded_at: datetime | None = None


class GraphView(CCFContract):
    """An immutable as-of view of one tenant's graph state.

    Whitepaper §7.3 / INV-CH7-14: an as-of read against ``at`` re-renders the
    state the fabric held at ``at`` exactly — claims observed later are absent,
    and claims superseded later are still current. That is what makes historical
    queries free of future-information leakage, and it is the precondition for
    Decision Replay.

    The view is a frozen contract rather than a live cursor: an operator
    (whitepaper §7.4) is a pure function over graph state, and a state that can
    change under it is not a value it can be pure over. Records are ordered
    deterministically (entities by ``entity_uri``, relationships by
    ``relationship_key``) so canonical serialization of a view is stable.
    """

    tenant_id: str
    as_of: datetime
    entities: tuple[EntityRecord, ...] = ()
    relationships: tuple[RelationshipRecord, ...] = ()


class UpsertResult(CCFContract):
    """Outcome of one write through the single :class:`GraphWriter` handle.

    Reports what the graph actually did, not what was asked, so callers and
    conformance tests can distinguish the three outcomes the D-IMPL-34
    semantics separate: a genuinely new claim, an idempotent re-arrival that
    only accumulated lineage, and a supersession.

    Attributes:
        node_key: ``entity_uri`` for an entity, ``relationship_key`` for an
            edge.
        claim_id: Content identity of the claim written or matched.
        claim_created: Whether a new claim row was appended. ``False`` means the
            arriving claim was byte-identical to the current one (semantic 2).
        lineage_added: How many lineage entries were genuinely new. Zero on a
            replayed envelope; positive when a second source corroborates the
            same claim (INV-CH7-17).
        superseded_claim_id: ``claim_id`` of the claim this write superseded, or
            ``None``. Nothing was deleted or overwritten either way.
    """

    node_key: str
    claim_id: str
    claim_created: bool
    lineage_added: int
    superseded_claim_id: str | None = None


class TraversalSpec(CCFContract):
    """The traverse family of a :class:`GraphQuery` — where a walk may go.

    Whitepaper §7.4 (Traversal as a canonical operator category, INV-CH7-24);
    ``GQ-02`` at docs/GRAPH_QUERY_SEMANTICS.md:64. Mirrors
    ``src/ccf/operators/params.py::TraversalNeighborhoodParameters`` (and its
    directed sibling ``src/ccf/operators/params.py::TraversalDescendantsParameters``)
    field-for-field, so a pushed traversal and an in-process traversal are
    parameterized by the same facts. A mirror rather than a reuse,
    deliberately: the operator-parameter contracts live in the operator tier
    and ``ccf.operators`` imports *this* module — the mirror keeps the
    dependency pointing one way.

    The three original fields are required with no defaults, the D-IMPL-38
    discipline of the mirrored contract: a default is a value nobody chose.
    ``admitted_entity_classes`` is the spec's first additive sentinel field
    (the ``allowed_entities`` precedent on :class:`GraphQuery`; semantics
    version 1.1.0, ledger row ``24.5-L-05``): ``None`` is the positive
    assertion "every class is admissible on a hop" — today's behavior — and
    a set admits a hop only onto an entity whose class is a member.

    Attributes:
        seed_entity_classes: Walk starting points, in ontology vocabulary —
            entities of these classes seed the walk (``GQ-11`` at
            docs/GRAPH_QUERY_SEMANTICS.md:222).
        relationship_types: Which typed edges the walk may cross. Edges of
            other types are not crossable and are absent from the answer
            even when both endpoints are reached (``GQ-10`` at
            docs/GRAPH_QUERY_SEMANTICS.md:201).
        depth_limit: Maximum hops from a walk starting point. ``0`` is a
            legal, meaningful bound — the starting points only, not an error
            and not "unlimited" (``GQ-10``).
        admitted_entity_classes: Node-class ADMISSION on the walk. Filters
            REACHED nodes and never walk STARTS — ``GQ-11`` selects starts
            and ``GQ-10``'s "seeds are included" stands, so a start of an
            unadmitted class is in the answer and still expands. An entity
            absent from the view's class map is not admitted. ``None``
            admits every class (the 1.0.x behavior). Hash-transparent at
            ``None`` (``D-IMPL-243``): omitted from the canonical form at
            that value, so a query pin computed before the field existed
            still matches; any set is rendered and moves the pin.
        direction: Which way an edge may be crossed
            (:data:`TraversalDirection`; ledger row ``24.5-L-06``).
            ``"undirected"`` — the default and the 1.0.x behavior — crosses
            an edge from either endpoint; ``"forward"`` crosses it only from
            ``subject_uri`` to ``object_uri`` as stored. The direction is
            fixed by which operator emitted the spec
            (``src/ccf/operators/categories.py::TraversalNeighborhood`` is
            undirected, ``src/ccf/operators/categories.py::TraversalDescendants``
            is forward), never by an artifact value. A pushed answerer that
            cannot express the direction declines the whole query to the
            fallback (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583; D-04).
            Hash-transparent at ``"undirected"`` (``D-IMPL-243``): the
            undirected walk is the 1.0.x walk, so it is omitted from the
            canonical form at that value; ``"forward"`` is rendered and
            moves the pin.
    """

    seed_entity_classes: frozenset[str]
    relationship_types: frozenset[str]
    depth_limit: int
    admitted_entity_classes: frozenset[str] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    direction: TraversalDirection = Field(
        default="undirected", json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class GraphQuery(CCFContract):
    """One question against graph state, as a frozen value.

    Whitepaper §7.3 (the Context Graph as queryable persisted state) and
    §7.4 (operators as the intent the query renders); the normative
    vocabulary is ``GQ-01`` at docs/GRAPH_QUERY_SEMANTICS.md:48 — this
    contract renders the prose clause-for-clause and decides nothing of its
    own.

    **The question is a value.** Because the query is frozen,
    ``content_hash(q)`` (``src/ccf/contracts/canonical.py::content_hash``)
    is well-defined and serves as replay's per-round-trip pin (D-02;
    ``GQ-20`` at docs/GRAPH_QUERY_SEMANTICS.md:391). Tenant scope arrives
    *inside* the frozen value, so the D-IMPL-05 keyword-only rule is
    satisfied by the contract rather than the argument list, and ``as_of``
    arrives as data — no answerer, and no code below the caller of the
    seam, may read a clock (whitepaper §7.10 determinism).

    **No version field, by decision (D-12).** The vocabulary is versioned
    through the ``docs/GRAPH_QUERY_SEMANTICS.md`` semver lane only: it
    evolves by additive sentinel-defaulted fields under the existing
    frozen/``extra=forbid`` discipline — ``allowed_entities`` is itself the
    first such field — and the differential conformance suite is the
    compatibility check. A version discriminator inside the value would
    make two identical questions hash differently across vocabulary
    revisions.

    Construction refusals, straight from the prose:

    * a partially-specified policy family is refused — a family, when
      present, carries all of its fields (``GQ-02`` at
      docs/GRAPH_QUERY_SEMANTICS.md:64);
    * ``seeds`` without a traverse family is refused — there is no walk for
      the seeds to start, and a constraint-shaped field must not constrain
      nothing (``GQ-03`` at docs/GRAPH_QUERY_SEMANTICS.md:87).

    The degenerate query — only ``tenant_id`` and ``as_of`` — is the
    everything-question, not an error: its answer is the tenant's full
    as-of view, and it is the definition of ``as_of()`` (``GQ-05`` at
    docs/GRAPH_QUERY_SEMANTICS.md:122; ``GQ-21`` at
    docs/GRAPH_QUERY_SEMANTICS.md:446).

    Attributes:
        tenant_id: Every question is tenant-scoped; there is no untenanted
            path through the fabric (D-IMPL-05).
        as_of: The observed-time boundary of the answer, applied to every
            answer whether or not any predicate family is present
            (``GQ-07`` at docs/GRAPH_QUERY_SEMANTICS.md:148).
        permitted_policy_bundle_versions: Policy family — mirrors
            ``src/ccf/operators/params.py::PolicyFilterParameters``. Which
            Control Plane policy-bundle versions the principal is admitted
            to read state stamped under (``GQ-08`` at
            docs/GRAPH_QUERY_SEMANTICS.md:163).
        classification_attribute_by_class: Policy family — ``entity_class
            -> attribute key`` carrying that class's classification. A
            class with no declared classification attribute is
            inadmissible (``GQ-08``).
        permitted_classifications: Policy family — the classification
            values the principal may see; an entity carrying no value for
            its class's classification attribute is inadmissible
            (``GQ-08``).
        require_valid_at_boundary: Temporal family — mirrors
            ``src/ccf/operators/params.py::TemporalAsOfParameters``. When
            true, a record additionally survives only if its valid
            interval covers the boundary (``GQ-09`` at
            docs/GRAPH_QUERY_SEMANTICS.md:186). ``None`` means the family
            is absent: no constraint beyond the always-applied as-of cut.
        traverse: Traverse family — the bounded typed expansion of ``GQ-10``
            (undirected, or forward only under the spec's ``direction``;
            node-class admission when it names ``admitted_entity_classes``),
            or ``None`` when the query walks nothing.
        seeds: Explicit entity-URI walk starting points, with exactly one
            meaning everywhere: walk starting points (``GQ-03`` at
            docs/GRAPH_QUERY_SEMANTICS.md:87). Authored by the caller of
            the seam — in the segmented execution path, the engine — and
            never part of any operator's fragment. Refused without a
            traverse family.
        allowed_entities: The survivor set of the multi-segment design —
            ``D-IMPL-87`` at docs/DECISIONS.md — engine-authored
            segment-boundary data, never an operator's contribution
            (``GQ-04`` at docs/GRAPH_QUERY_SEMANTICS.md:98). Its three
            values are three different facts. ``None`` is the positive
            assertion "no survivor constraint": it holds on first segments
            and on every segment of a fully-pushable plan, so the common
            no-Similarity case is untouched by this field's existence. The
            empty frozenset is a legal value whose answer is the empty
            view — "the survivor set is empty" and "there is no
            survivor-set constraint" are different questions. A non-empty
            set applies the uniform rule (``GQ-15`` at
            docs/GRAPH_QUERY_SEMANTICS.md:300): every operator family
            computes within the set, traversal may not cross outside it,
            relationships require both endpoints in-set (``GQ-16`` at
            docs/GRAPH_QUERY_SEMANTICS.md:316), and seeds keep exactly one
            meaning — walk starting points.
    """

    tenant_id: str
    as_of: datetime
    permitted_policy_bundle_versions: frozenset[str] | None = None
    classification_attribute_by_class: Mapping[str, str] | None = None
    permitted_classifications: frozenset[str] | None = None
    require_valid_at_boundary: bool | None = None
    traverse: TraversalSpec | None = None
    seeds: frozenset[str] | None = None
    allowed_entities: frozenset[str] | None = None

    @model_validator(mode="after")
    def _policy_family_is_whole(self) -> GraphQuery:
        if _policy_family_is_partial(
            self.permitted_policy_bundle_versions,
            self.classification_attribute_by_class,
            self.permitted_classifications,
        ):
            raise ValueError(
                "a policy family carries all of its fields or none of them;"
                " a partially-specified family is not a legal value"
                " (`GQ-02` in docs/GRAPH_QUERY_SEMANTICS.md)"
            )
        return self

    @model_validator(mode="after")
    def _seeds_start_a_walk(self) -> GraphQuery:
        if self.seeds is not None and self.traverse is None:
            raise ValueError(
                "seeds without a traverse family are not well-formed: there"
                " is no walk for the seeds to start"
                " (`GQ-03` in docs/GRAPH_QUERY_SEMANTICS.md)"
            )
        return self


class QueryFragment(CCFContract):
    """One operator's contribution to a segment's query.

    Whitepaper §7.4 (operators as declared, replayable intent); ``GQ-06`` at
    docs/GRAPH_QUERY_SEMANTICS.md:132. A fragment carries at most one of the
    three predicate families of ``GQ-02`` — and nothing else: never seeds,
    never ``allowed_entities``. The survivor set is engine-authored
    segment-boundary data (``GQ-04`` at docs/GRAPH_QUERY_SEMANTICS.md:98); a
    fragment structurally cannot carry it, so no operator's declared intent
    can widen or replace the constraint — the entity-resurrection defect is
    closed by the field's absence, not by review.

    **The union rule** (``GQ-06``). Fragments within a segment union
    field-wise into one :class:`GraphQuery`, with at most one fragment per
    family: two fragments claiming the same family is a broken plan and is
    refused at plan compilation — never merged, because a merge rule would
    silently decide which operator's parameters win, and a
    decided-by-accident parameter set cannot be replayed against an intent.

    Attributes:
        permitted_policy_bundle_versions: Policy family, as on
            :class:`GraphQuery`; present only when this fragment is the
            policy contribution.
        classification_attribute_by_class: Policy family, as on
            :class:`GraphQuery`.
        permitted_classifications: Policy family, as on :class:`GraphQuery`.
        require_valid_at_boundary: Temporal family, as on
            :class:`GraphQuery`; present only when this fragment is the
            temporal contribution.
        traverse: Traverse family; present only when this fragment is the
            traversal contribution.
    """

    permitted_policy_bundle_versions: frozenset[str] | None = None
    classification_attribute_by_class: Mapping[str, str] | None = None
    permitted_classifications: frozenset[str] | None = None
    require_valid_at_boundary: bool | None = None
    traverse: TraversalSpec | None = None

    @model_validator(mode="after")
    def _policy_family_is_whole(self) -> QueryFragment:
        if _policy_family_is_partial(
            self.permitted_policy_bundle_versions,
            self.classification_attribute_by_class,
            self.permitted_classifications,
        ):
            raise ValueError(
                "a policy family carries all of its fields or none of them;"
                " a partially-specified family is not a legal value"
                " (`GQ-02` in docs/GRAPH_QUERY_SEMANTICS.md)"
            )
        return self

    @model_validator(mode="after")
    def _at_most_one_family(self) -> QueryFragment:
        families_present = sum(
            (
                self.permitted_policy_bundle_versions is not None
                or self.classification_attribute_by_class is not None
                or self.permitted_classifications is not None,
                self.require_valid_at_boundary is not None,
                self.traverse is not None,
            )
        )
        if families_present > 1:
            raise ValueError(
                "a fragment is one operator's contribution: at most one of"
                " the three predicate families"
                " (`GQ-06` in docs/GRAPH_QUERY_SEMANTICS.md)"
            )
        return self


class SourceAttestation(CCFContract):
    """Per-dimension provenance modes of one graph-state source — SDK-defined.

    An SDK extension beyond the whitepaper, labeled per CLAUDE.md §11: the
    whitepaper commits to lineage (§7.3) and replay (§7.10); the mode
    vocabulary by which a *source* attests how its answers acquired policy
    binding and lineage is SDK mechanism, per the Phase 15.2 D-09 ruling
    (``.planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-CONTEXT.md``).

    **The three tiers are three well-known values of one schema**, not three
    schemas:

    * tier 1, the live graph — ``policy_binding="assembly-stamped"``,
      ``lineage="graph-supplied"``, ``peer=None``;
    * tier 2, a mounted admitted product — the modes
      ``"admission-verified"`` / ``"product-carried"`` with ``peer`` naming
      the admitting federation peer;
    * tier 3, an unattested source — ``"none"`` / ``"none"`` / ``None``,
      expressible **today**. That is the no-refactor commitment met by
      construction: admitting a lower-trust source class later changes no
      schema, only which value a reader reports.

    **Temporal correctness is deliberately not an attestation dimension.**
    The as-of cut is a conformance obligation every answerer owes on every
    answer (D-09 scoping note; ``GQ-07`` at
    docs/GRAPH_QUERY_SEMANTICS.md:148) — a source cannot opt out of it, so
    there is no mode to report.

    Frozen and canonically serializable, so the attestation in force pins
    into replay with zero new mechanism.

    Attributes:
        policy_binding: How answered records acquired their policy binding —
            stamped at assembly by the fabric's own L2, verified at the
            peering admission gate, or not attested at all.
        lineage: Where lineage on answered records comes from — the graph's
            own accumulated L, carried inside a mounted product's payload,
            or not attested at all.
        peer: The federation peer whose admission produced the mounted
            records, for tier-2 sources; ``None`` where no peer is
            involved. Required rather than defaulted: "no peer" is an
            assertion the constructor makes, not a value nobody chose.
    """

    policy_binding: PolicyBindingMode
    lineage: LineageMode
    peer: PeerRef | None


class StoreSnapshotPin(CCFContract):
    """A store-native transaction pin — the ``"transaction-time"`` axis, as a value.

    SDK-defined per CLAUDE.md §11, an extension beside the whitepaper's T axis
    (§7.3) and its replay commitment (§7.10): ``D-IMPL-240`` (2) routes the
    Fluree pin through this type, and ``D-IMPL-88`` is why the type exists at
    all. Its axis is :data:`TemporalAxis` ``"transaction-time"`` and nothing
    else: it says *which state of the store* a read saw, never *which
    observations* the read admitted.

    **Deliberately not a** ``datetime``, and deliberately not an ``int``. A
    pin is substrate-shaped — Fluree renders an integer ``t``, a SQL substrate
    has no native pin, a content-addressed store might render a digest — and
    no arithmetic is ever done on it, so it travels as text. And because it
    is a model rather than an instant, :attr:`GraphQuery.as_of` cannot accept
    it: pydantic refuses a model where a ``datetime`` is typed, and that
    refusal IS the ``D-IMPL-88`` guard at the type level. A caller who tries
    to implement the observed-time cut with a transaction counter gets a
    validation error at the seam rather than a silently wrong answer.

    Attributes:
        substrate: Which store family minted the pin, in the adapter's own
            vocabulary (``ccf.graph.backends.fluree.FLUREE_SUBSTRATE``). A
            reader refuses a pin minted by a different substrate.
        pin: The substrate's rendering of its own head — Fluree's ``t`` as
            decimal text. Opaque to everything outside the adapter that
            minted it.
    """

    substrate: str
    pin: str


#: The positive sentinel "this read carried no store-native pin" — the
#: ``NO_*`` voice of ``ccf.replay.record`` (``NO_GRANTS_SET_HASH``,
#: ``NO_HARNESS``, ``NO_ADAPTER``): a SQLite or Postgres deployment asserts the
#: absence rather than carrying a fake ``t``, and a consumer distinguishes
#: "no pin" from "a pin" by equality against one value instead of by ``None``.
NO_STORE_SNAPSHOT_PIN: Final[StoreSnapshotPin] = StoreSnapshotPin(
    substrate="none", pin="no-store-snapshot-pin"
)


@runtime_checkable
class GraphReader(Protocol):
    """Read-only access to graph state — the only graph handle L4+ receives.

    DESIGN.md §2A.5.2/§2A.5.3. ``tenant_id`` is keyword-only and required on
    every method (D-IMPL-05): there is no code path that resolves an entity
    without tenant scope, and making it keyword-only means a positional
    argument can never silently land in the tenant slot.
    """

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Return the state ``tenant_id``'s graph held at observed-time ``at``.

        An empty graph yields an empty view, never an error: "nothing is known"
        is a legitimate answer that operators compose over.

        Defined as the degenerate query — `GQ-21` at
        docs/GRAPH_QUERY_SEMANTICS.md:446 (D-07): identical records,
        identical ordering, identical canonical bytes to
        ``query(GraphQuery(tenant_id=tenant_id, as_of=at))``.
        """
        ...

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` with the frozen as-of view its clauses define.

        Tenant scope arrives *inside* the frozen value, so the D-IMPL-05
        keyword-only rule is satisfied by the contract rather than the
        argument list (`GQ-01` at docs/GRAPH_QUERY_SEMANTICS.md:48), and
        ``as_of`` arrives as data — no answerer may read a clock. A
        conformant answerer answers any well-formed query, degrading
        internally to scan-and-filter where it holds no native translation
        (`GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554, D-04) — there is no
        capability negotiation and no refusal path on this seam.

        An empty answer is a legitimate value, never an error: "nothing is
        known", "everything was excluded", and "the walk started nowhere"
        all answer with the empty view, and operators compose over it
        exactly as over any other view (`GQ-23` at
        docs/GRAPH_QUERY_SEMANTICS.md:474).
        """
        ...

    @property
    def attestation(self) -> SourceAttestation:
        """Per-dimension provenance modes of this source — SDK-defined.

        An SDK extension beyond the whitepaper, labeled per CLAUDE.md §11:
        how a source's answers acquired their policy binding and lineage
        (the D-09 mode vocabulary of :class:`SourceAttestation`). The live
        graph reports tier 1 — ``"assembly-stamped"`` /
        ``"graph-supplied"`` / ``peer=None``; a mounted admitted product
        reports tier 2; an unattested source tier 3. Frozen and
        canonically serializable, so the attestation in force pins into
        replay with zero new mechanism.
        """
        ...

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        """Return every claim ever made about ``entity_uri``, oldest first.

        Superseded claims are included with their supersession edges intact —
        the append-only-forward semantic (INV-CH7-04) is only observable if the
        superseded claims remain readable.
        """
        ...

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Return every claim ever made about one edge, oldest first."""
        ...


@runtime_checkable
class SnapshotPinnable(Protocol):
    """A reader whose substrate can answer at a pinned transaction — SDK-defined.

    An SDK extension beside :class:`GraphReader`, labeled per CLAUDE.md §11;
    the whitepaper commits to replay (§7.10) and this is one substrate-level
    means of resolving an exact prior state for it (``D-IMPL-240`` (2),
    ledger row ``24.5-L-01``). **Structural typing, by design**: a reader
    that cannot pin simply does not implement these two members — every
    reader shipped before this Protocol stays exactly as it is, with no
    stub to add — and a consumer asks ``isinstance(reader, SnapshotPinnable)``
    rather than reading a capability flag. Nothing on :class:`GraphReader` changes
    (D-10: the graph Protocol gains, never changes, signatures).

    **Two axes, never one.** ``query_pinned`` bounds the STORE by ``pin``
    and bounds the OBSERVATIONS by ``q.as_of``, and applies both: the pin
    says which committed state of the substrate the read may see, and the
    as-of cut then runs over that state exactly as it runs over the head.
    Neither stands in for the other (``D-IMPL-88``): a pin is not an as-of
    instant and an as-of instant is not a pin, and an implementation that
    is offered the wrong kind refuses it with a ``TypeError`` naming the
    ruling.
    """

    def snapshot_pin(self) -> StoreSnapshotPin:
        """The substrate's current head pin — read once, a fact about the read.

        Recorded beside ``graph_snapshot_at``, never inside it: this is
        lineage about *which state the store was in*, not a temporal
        boundary. Under the single-writer invariant (INV-CH7-10) the head
        cannot move underneath a read issued in the same call.
        """
        ...

    def query_pinned(self, q: GraphQuery, *, pin: StoreSnapshotPin) -> GraphView:
        """Answer ``q`` as ``query`` would if the store were rolled back to ``pin``.

        Every as-of predicate of ``q`` still applies — the pin bounds the
        STORE, ``q.as_of`` bounds the OBSERVATIONS; two axes, never one. The
        answer is byte-identical to what ``query(q)`` would return on a
        store frozen at ``pin`` (D-04: the fallback is the oracle).

        Raises:
            TypeError: ``pin`` is not a :class:`StoreSnapshotPin` (a
                ``datetime``, an ``int``, a ``str`` offered as a pin — the
                ``D-IMPL-88`` refusal), or was minted by another substrate.
            LookupError: ``pin`` names a state the store has not reached.
        """
        ...


@runtime_checkable
class TraversalDepthCapability(Protocol):
    """A store that can say how deep it is technically able to walk — SDK-defined.

    An SDK extension beside :class:`GraphReader`, labeled per CLAUDE.md §11;
    the ruling is ``D-IMPL-253`` Q21 (Dave: *"6 is measurement/default history;
    100 is the genuine technical capability boundary"*). It exists so that a
    substrate limit can be **refused by name** one layer up, in
    :mod:`ccf.products.constraints`, with authority ``technical`` and a
    capability identity as its provenance — rather than authored as a number in
    product code, which would be a bound nobody measured (CINV-01).

    **Structural typing, by design**, exactly as :class:`SnapshotPinnable` is:
    a store with no ceiling simply does not implement these two members — the
    SQLite and Postgres reference stores answer any depth by scan-and-filter
    and have none to report, so they stay exactly as they are with no stub to
    add — and a consumer asks ``isinstance(store, TraversalDepthCapability)``
    rather than reading a capability flag. Nothing on :class:`GraphReader` or
    :class:`GraphWriter` changes (D-10: the graph Protocol gains, never
    changes, signatures).

    **This adds no refusal path to the graph seam and must not be read as
    one.** An over-ceiling ``depth_limit`` at a backend still declines the
    native translation and is answered by the memory-bounded fallback (`GQ-29`
    at docs/GRAPH_QUERY_SEMANTICS.md:554; *"there is no capability negotiation
    and no refusal path on this seam"*). What this Protocol does is let a layer
    that *has* a governed response ask the question before the read.
    """

    @property
    def max_traversal_depth(self) -> int:
        """The deepest traversal this substrate can be asked for natively.

        A property of the adapter's own injection surface, not of any domain
        and not of any deployment's policy — which is why it is read off the
        object rather than declared in an artifact.
        """
        ...

    @property
    def capability_identity(self) -> str:
        """Credential-free identity of the substrate the bound belongs to.

        What an examiner resolves the bound's source by: the value recorded on
        a ``capability``-kind
        :class:`~ccf.products.provenance.ProvenanceSource`, which has no
        version lane because a capability is a property of the substrate in
        force rather than a versioned document (``D-IMPL-253`` amendment 2 (1)).
        """
        ...


@runtime_checkable
class GraphWriter(Protocol):
    """The sole mutation surface of the Context Graph (INV-CH7-10).

    DESIGN.md §2A.5.3. Exactly one implementation of this Protocol exists in a
    running fabric; it is constructed by the composition root
    (:mod:`ccf.boot`) and injected into the L2 Assembly worker and nowhere
    else. The concrete class lives in the import-restricted ``ccf.graph._writer``
    module, so no module outside ``ccf.assembly`` / ``ccf.boot`` can even name
    it (CINV-02).

    ``policy_bundle_version`` is a required argument rather than something the
    writer looks up: policy is bound *at assembly time* and travels with the
    subgraph — the fabric does not persist state first and ask who may see it
    afterwards (INV-CH7-03).

    **The lifecycle obligation is part of the contract** (review finding F6).
    This Protocol used to declare the two upserts and stop, while the runtime
    required a third method the reader of this file could not see: the
    composition root calls ``close()`` on shutdown, and a writer that has no
    ``close`` leaves the graph marked as written-to for the life of the
    process. A public contract that under-declares what the runtime requires is
    the ``DI-15.4-05`` gap producing a defect rather than an inconvenience, so
    the contract now says what it needs.

    ``close`` is the **composition root's** to call, not L2's. Nothing about
    declaring it here changes who owns the lifecycle; it changes what a reader
    of the documented surface knows they must implement.
    """

    def upsert_entity(
        self,
        *,
        tenant_id: str,
        claim: EntityClaim,
        policy_bundle_version: str,
    ) -> UpsertResult:
        """Idempotently upsert an entity claim, accumulating lineage by union.

        Raises:
            ValueError: ``claim.tenant_id`` disagrees with ``tenant_id``.
        """
        ...

    def upsert_relationship(
        self,
        *,
        tenant_id: str,
        claim: RelationshipClaim,
        policy_bundle_version: str,
    ) -> UpsertResult:
        """Idempotently upsert a relationship claim, with per-edge lineage."""
        ...

    def close(self) -> None:
        """Retire this writer and release its graph for a subsequent boot.

        Shutdown, not an escape hatch: a retired writer refuses every further
        write, so this cannot be used to hold two usable writers at once. It
        must be **idempotent** — the composition root's handle is also a
        context manager, so ``with handle:`` around a body that also closes is
        two calls written by someone doing nothing wrong.

        Releasing the graph is the load-bearing half. A writer whose ``close``
        does not release leaves the fabric refusing every later boot over that
        graph (INV-CH7-10); this is why
        :func:`ccf.graph._writer.adopt_writer` refuses a returned writer that
        is not a :class:`~ccf.graph._writer.BaseGraphWriter`, whose ``close``
        is the implementation of this method every adapter inherits.
        """
        ...


# --- The writer lease (SEC-013, D-IMPL-372) ----------------------------------
#
# Why the lease type lives HERE rather than beside the live-writer table in
# ``ccf.graph._writer``: a backend store returns it, and the CINV-02 lint
# (``tools/lints/harness_imports.py::WRITER_OK_MODULES``) forbids a backend's
# reader-side store module from importing ``_writer``, while ``cinv02-backend-
# import`` forbids ``_writer`` from importing a backend. This module is the one
# both sides may already import, so the seam's vocabulary is defined once here
# and ``_writer`` reaches the store's lease structurally.

#: What a writer lease's exclusion covers, by name. A closed vocabulary.
#:
#: ``"cross-process"`` — the substrate itself refuses a second holder, whichever
#: process asks (the SQLite ``flock`` sidecar, the Postgres session advisory
#: lock). ``"process"`` — a **disclosure, not enforcement**: the only exclusion
#: is the composition root's in-process live-writer table, so the single-writer
#: invariant (INV-CH7-10) is NOT enforced across processes on that substrate.
WriterLeaseScope = Literal["cross-process", "process"]

#: The two :data:`WriterLeaseScope` values, for a refusal that names them.
WRITER_LEASE_SCOPES: Final[tuple[WriterLeaseScope, ...]] = (
    "cross-process",
    "process",
)


class WriterLeaseHeld(RuntimeError):
    """The substrate refused the writer lease: another holder has the graph.

    SEC-013 (D-IMPL-372); an SDK extension of whitepaper §7.3 / INV-CH7-10.
    Raised by a store's ``writer_lease()`` and translated by the composition
    root's mint (``src/ccf/graph/_writer.py::mint_boot_token``) into the same
    ``SingleWriterViolation`` an in-process second boot raises. It is a
    separate type only because a backend store may not import ``_writer``.
    The message names the lease kind and the resource, never a credential.
    """


class WriterLease(Protocol):
    """A held, exclusive claim on a graph's single writer — or a declaration.

    SEC-013 (D-IMPL-372); SDK extension of whitepaper §7.3 and INV-CH7-10,
    CLAUDE.md §10 ("the single-writer invariant ... is architectural, not
    advisory"). Returned by ``BackendStore.writer_lease()``
    (``src/ccf/graph/registry.py::BackendStore``), acquired by the mint and
    held for the writer's life; never acquired at store open, because a
    read-only store over a live graph is legitimate.

    :attr:`scope` says what the exclusion covers. A ``"process"`` lease is a
    disclosure, not enforcement — the invariant is not enforced across
    processes on that substrate, so it is correct only where no second
    process can reach the graph; a persistent network store mints only under
    a declared ``"cross-process"`` lease (:func:`acquire_declared_writer_lease`,
    SEC-013, D-IMPL-374).

    :meth:`release` must be idempotent. The lease is also a context manager
    whose exit releases it.
    """

    @property
    def scope(self) -> WriterLeaseScope:
        """What the exclusion covers: ``"cross-process"`` or ``"process"``."""
        ...

    @property
    def mechanism(self) -> str:
        """The lease kind and resource, credential-free, for refusals and audit."""
        ...

    def release(self) -> None:
        """Give the lease back. **Must be idempotent.**"""
        ...

    def __enter__(self) -> WriterLease: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class ProcessScopedWriterLease:
    """The ``"process"``-scope declaration a store without a substrate lease returns.

    SEC-013 (D-IMPL-372). **A disclosure, not enforcement.** Acquiring and
    releasing it do nothing; the only exclusion on such a substrate is the
    composition root's in-process live-writer table, so two *processes* over
    one graph on this substrate are NOT refused. Exact for a store whose graph
    no second process can reach (an in-process dict). A persistent network
    store does not return it: it mints only under a deployment-declared
    ``"cross-process"`` lease, and :func:`acquire_declared_writer_lease`
    refuses a declared ``"process"`` lease by name (SEC-013, D-IMPL-374).

    Args:
        substrate: The adapter's name, so the declaration says whose it is.
    """

    def __init__(self, *, substrate: str) -> None:
        self._substrate = substrate

    @property
    def scope(self) -> WriterLeaseScope:
        return "process"

    @property
    def mechanism(self) -> str:
        return (
            f"{self._substrate}: process scope only (declared, not enforced"
            " across processes)"
        )

    def release(self) -> None:
        return None

    def __enter__(self) -> ProcessScopedWriterLease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()

    def __repr__(self) -> str:
        return f"ProcessScopedWriterLease(substrate={self._substrate!r})"


#: A declared, not-yet-held writer lease: calling it with the store's graph
#: identity ACQUIRES the lease for that graph.
#:
#: SEC-013 (D-IMPL-374 (1)); SDK extension of whitepaper §7.3 / INV-CH7-10.
#: What a deployment hands a persistent network store's constructor
#: (``writer_lease=``). The store never calls it at open — only its
#: ``writer_lease()`` does, which only the composition root's mint
#: (``src/ccf/graph/_writer.py::mint_boot_token``) calls — so a read-only store
#: over a live graph still takes no lease. The store passes its own
#: credential-free graph identity, so a lease keyed by mechanism on the
#: identity cannot be pointed at a resource a second writer of the same graph
#: does not also reach: the reference lock-directory lease
#: (``src/ccf/graph/leases.py::lock_directory_writer_lease``) derives its lock
#: file from the identity's SHA-256 inside a declared absolute directory. A
#: deployment may instead declare a lease keyed on a resource it names (the
#: reference advisory-lock lease over a session and a lease schema); it then
#: owns making every writer of the graph name the same resource.
WriterLeaseSource = Callable[[str], WriterLease]


class WriterLeaseRequired(RuntimeError):
    """A persistent network store refused to mint: no held cross-process lease was declared.

    SEC-013 (D-IMPL-374 (1)); an SDK extension of whitepaper §7.3 /
    INV-CH7-10. Refuse-when-undeclared, the temporal window's posture: a
    store whose graph a second process can reach must not mint a writer under
    the ``"process"`` disclosure, because that disclosure excludes nothing
    across processes (the hole SEC-013 names: the live-writer table is
    process-local). Raised by :func:`acquire_declared_writer_lease`, from the
    store's ``writer_lease()``, on the mint path — before any token exists, so
    a refused mint marks nothing live and a corrected, leased retry boots.
    The message names the substrate and the credential-free graph identity,
    never a credential.
    """


def acquire_declared_writer_lease(
    source: WriterLeaseSource | None, *, substrate: str, graph_identity: str
) -> WriterLease:
    """Acquire a persistent network store's declared writer lease, or refuse by name.

    SEC-013 (D-IMPL-374 (1)); SDK extension of whitepaper §7.3 / INV-CH7-10.
    The one implementation every persistent network store's ``writer_lease()``
    delegates to, so the refusal cannot drift between adapters:

    * ``source`` is ``None`` — no lease was declared: refuse with
      :class:`WriterLeaseRequired`.
    * Calling ``source`` raises :class:`WriterLeaseHeld` — another holder, in
      any process, has the lease: propagated unchanged, so the mint refuses it
      as the same ``SingleWriterViolation`` an in-process second boot raises.
    * The acquired lease's scope is not ``"cross-process"`` — a declared
      ``"process"`` disclosure is no lease at all: the lease is released and
      the mint is refused with :class:`WriterLeaseRequired`.

    Args:
        source: The deployment-declared lease, or ``None`` when none was.
        substrate: The adapter's name, for the refusal.
        graph_identity: The store's credential-free graph identity.

    Returns:
        The HELD lease, for the mint to keep for the writer's life.

    Raises:
        WriterLeaseRequired: no lease was declared, or the declared lease does
            not exclude across processes.
        WriterLeaseHeld: another holder has the declared lease.
    """
    if source is None:
        raise WriterLeaseRequired(
            f"the {substrate} store for graph {graph_identity!r} has no declared"
            " writer lease; a persistent network store mints a writer only"
            " under a held cross-process lease the deployment declares"
            " (SEC-013, D-IMPL-374)"
        )
    lease = source(graph_identity)
    scope = getattr(lease, "scope", None)
    if scope != "cross-process":
        try:
            release = getattr(lease, "release", None)
            if callable(release):
                release()
        finally:
            raise WriterLeaseRequired(
                f"the writer lease declared for the {substrate} store for graph"
                f" {graph_identity!r} has scope {scope!r}; a persistent network"
                " store mints a writer only under a held 'cross-process' lease"
                " (SEC-013, D-IMPL-374)"
            )
    return lease
