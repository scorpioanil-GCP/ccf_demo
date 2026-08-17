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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.claims import EntityClaim, RelationshipClaim
from ccf.peering.protocol import PeerRef

__ccf_mode__ = "algorithmic"

__all__ = [
    "EntityRecord",
    "GraphQuery",
    "GraphReader",
    "GraphView",
    "GraphWriter",
    "LineageMode",
    "PolicyBindingMode",
    "QueryFragment",
    "RelationshipRecord",
    "SourceAttestation",
    "TraversalSpec",
    "UpsertResult",
]

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
    ``src/ccf/operators/params.py::TraversalNeighborhoodParameters``
    field-for-field, so a pushed traversal and an in-process traversal are
    parameterized by the same three facts. A mirror rather than a reuse,
    deliberately: the operator-parameter contracts live in the operator tier
    and ``ccf.operators`` imports *this* module — the mirror keeps the
    dependency pointing one way.

    All three fields are required with no defaults, the D-IMPL-38 discipline
    of the mirrored contract: a default is a value nobody chose.

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
    """

    seed_entity_classes: frozenset[str]
    relationship_types: frozenset[str]
    depth_limit: int


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
        traverse: Traverse family — the bounded typed undirected expansion
            of ``GQ-10``, or ``None`` when the query walks nothing.
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
