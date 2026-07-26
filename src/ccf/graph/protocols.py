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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.claims import EntityClaim, RelationshipClaim

__ccf_mode__ = "algorithmic"

__all__ = [
    "EntityRecord",
    "GraphReader",
    "GraphView",
    "GraphWriter",
    "RelationshipRecord",
    "UpsertResult",
]


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
