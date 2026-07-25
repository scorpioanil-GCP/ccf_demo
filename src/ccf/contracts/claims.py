"""Claim contracts — the typed units L2 assembles into graph state.

Whitepaper §7.3 specifies the Context Graph's six-tuple ``G(E, R, T, P, Π, L)``;
DESIGN.md §2A.5.1 renders three of those axes as the contract shapes below:

* **E** — :class:`EntityClaim`, a URI-addressable node assertion whose identity
  is stable across sources and time (INV-CH7-18).
* **R** — :class:`RelationshipClaim`, a *typed first-class* relationship, never
  a derived join (INV-CH7-15).
* **T** — the bitemporal axis carried on both: ``observed_at`` (when the fabric
  learned it) against ``valid_from`` / ``valid_to`` (when it holds in the
  world). Keeping both is what makes as-of reads reproduce prior state exactly
  (INV-CH7-14) — supersession is a logical event, never an overwrite.
* **L** — :class:`LineageEntry`, append-only provenance that accumulates by
  set-union rather than replacement: multi-source evidence for the same claim
  is additive, with per-source timestamps and passage anchors preserved
  (INV-CH7-17, INV-CH7-19). The entries are frozen and hashable precisely so
  set-union is the natural operation.

These are the *slice subset* the vertical slice needs (D-05). Debt/trust
scorers, fidelity-lifecycle types, and closed-loop types land with their own
subsystem plans rather than being speculated here.

Entity classes, relationship types, and attribute vocabularies are user
configuration (whitepaper's counterparty/facility/guarantee topology is a
worked domain illustration, INV-CH7-20). This module declares the *shape* and
holds no such values (CLAUDE.md §11, CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.signal.envelope import SourceIdentity

__ccf_mode__ = "algorithmic"

__all__ = [
    "EntityClaim",
    "LineageEntry",
    "PassageAnchor",
    "RelationshipClaim",
]


class PassageAnchor(CCFContract):
    """A passage-level anchor into unstructured source content.

    Whitepaper §7.10.3 / INV-CH7-19: extracted claims are anchored to the
    passage they came from, so a reviewer can trace any claim to its text.

    ``kind`` names the anchor vocabulary (document-shaped, transcript-shaped,
    or whatever a deployment's parser emits) and ``locator`` carries the
    anchor value in that vocabulary. Both are user-supplied: the SDK fixes the
    anchoring *obligation*, never the anchor schema. The richer structured
    anchor shapes DESIGN.md §2A.4.4 enumerates arrive with the Pattern 5
    pipeline plan; this type is what the slice needs to keep L faithful.
    """

    kind: str
    locator: str


class LineageEntry(CCFContract):
    """One append-only provenance record on the L axis.

    DESIGN.md §2A.5.1; INV-CH7-17 (set-union accumulation, deliberately *not*
    idempotent) and INV-CH8-01 (L records source **identity**, not location —
    which is what makes the fabric migration-proof).

    Identity is the whole tuple: the same observation re-delivered under the
    same envelope produces an equal entry and therefore collapses under
    set-union, while genuinely distinct evidence accumulates.
    """

    source: SourceIdentity
    envelope_id: str
    observed_at: datetime
    passage_anchor: PassageAnchor | None = None


class _TemporalClaim(CCFContract):
    """Shared bitemporal + tenancy + lineage surface of every claim.

    ``tenant_id`` is required on every claim: there is no untenanted path
    through the fabric (INV-CH7-16, D-IMPL-05). ``valid_to`` of ``None`` means
    "still valid as far as this observation knows" — not a default value, an
    open interval.
    """

    tenant_id: str
    observed_at: datetime
    valid_from: datetime
    valid_to: datetime | None = None
    lineage: frozenset[LineageEntry]


class EntityClaim(_TemporalClaim):
    """An assertion about one entity node on the E axis.

    Whitepaper §7.3; DESIGN.md §2A.5.1. ``entity_uri`` is the canonical,
    tenant-scoped URI entity resolution converges native identifiers onto
    (INV-CH7-18); ``entity_class`` names its class within the user-declared
    ontology. ``attributes`` is an opaque, deployment-defined attribute map —
    the SDK never enumerates its keys.
    """

    entity_uri: str
    entity_class: str
    attributes: Mapping[str, str] = Field(default_factory=dict)


class RelationshipClaim(_TemporalClaim):
    """An assertion about one typed relationship on the R axis.

    Whitepaper §7.3; DESIGN.md §2A.5.1. Relationships are persisted first-class
    edges, not derived joins, and carry per-relationship-type lineage
    (INV-CH7-20). ``relationship_type`` is user-declared ontology vocabulary.
    """

    relationship_type: str
    subject_uri: str
    object_uri: str
    attributes: Mapping[str, str] = Field(default_factory=dict)
