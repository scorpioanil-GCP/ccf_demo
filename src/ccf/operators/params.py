"""Declared parameter contracts, one per canonical operator category.

Whitepaper §7.4 (the four canonical categories and their determinism
contracts); DESIGN.md §2B.1; D-IMPL-38 (declared-schema, no silent defaults).

**Why the parameters live apart from the operators.** An operator is
mechanism; its parameters are Control Plane *values* that a deployment
declares, versions, and replays against. Separating the two makes the
boundary a module boundary rather than a paragraph in a docstring: this
module is what the Control Plane registers and what
``content_hash`` pins into every provenance sub-chain, while
:mod:`ccf.operators.categories` holds the code that interprets it.

**No field in this module carries a default.** Not a threshold, not a depth
limit, not a score floor, not a flag. Every value is required at plan time
and must arrive from a Control Plane artifact or from the caller. A default
is a value nobody chose, and a value nobody chose cannot be audited, cannot
be versioned, and silently changes the meaning of a replay when the SDK
revises it (D-IMPL-38; CINV-01b enforces this mechanically for modules named
like this one).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from ccf.operators.base import OperatorParameters

__ccf_mode__ = "algorithmic"

__all__ = [
    "PolicyFilterParameters",
    "SimilaritySelectParameters",
    "TemporalAsOfParameters",
    "TraversalNeighborhoodParameters",
]


class PolicyFilterParameters(OperatorParameters):
    """Declared parameters of the Policy category.

    Attributes:
        permitted_policy_bundle_versions: Which Control Plane policy-bundle
            versions this principal is admitted to read state stamped under.
        classification_attribute_by_class: ``entity_class -> attribute key``
            carrying that class's classification. Per class rather than one
            global key, because classes carry their sensitivity in their own
            vocabulary — two classes in the same deployment routinely carry
            their sensitivity in differently-named fields. An entity class
            absent from this mapping is inadmissible.
        permitted_classifications: The classification values the principal may
            see. Everything else — *including an entity carrying no
            classification at all* — is excluded: the fabric does not admit
            state it cannot prove is admissible.

            Read the mechanism, not the name (ledger row ``24.5-L-28``). This
            is a **generic attribute-value allowlist**: the set of values
            admitted for whichever attribute ``classification_attribute_by_class``
            names for the record's entity class, tested by exact membership in
            :meth:`~ccf.operators.categories.PolicyFilter._admits`. The name
            comes from the Policy operator's sensitivity use — data
            classification such as MNPI is the whitepaper's headline example
            (§7.4) — but the mechanism admits any per-class attribute value,
            and §7.4 itself names entitlement, jurisdiction and regulatory
            constraint as the operator's scope. cp-01 binds it to
            ``legal_jurisdiction`` so the allowlist is the calling principal's
            jurisdiction grant set; that binding is a deployment value
            (``D-09``), not a second mechanism. The name is not changed —
            a bounded correction (``D-07.1``): it is whitepaper vocabulary,
            and the surface manifest records signatures, not prose.
    """

    permitted_policy_bundle_versions: frozenset[str]
    classification_attribute_by_class: Mapping[str, str]
    permitted_classifications: frozenset[str]


class SimilaritySelectParameters(OperatorParameters):
    """Declared parameters of the Similarity category.

    Attributes:
        query: The corpus query. A *parameter*, not a prompt: it is matched
            lexically by the index, never sent to a model (Mode 1).
        minimum_score_percent: Integer inclusion floor on the ``0..100`` scale.
            Integer because floats have no canonical rendering.
        ranked_entity_classes: Which entity classes are subject to ranking.
            Classes outside this set pass through untouched — a similarity
            operator that silently deleted every entity class it was not asked
            about would not be ranking, it would be filtering.
    """

    query: str
    minimum_score_percent: int
    ranked_entity_classes: frozenset[str]


class TemporalAsOfParameters(OperatorParameters):
    """Declared parameters of the Temporal category.

    Attributes:
        require_valid_at_boundary: When true, a claim survives only if its
            *valid* interval covers the boundary, not merely if the fabric had
            observed it by then. The two questions — "what did we know?" and
            "what was true?" — are the two axes of the bitemporal model, and
            which one a decision needs is a decision-class property, so it is
            declared rather than assumed.
    """

    require_valid_at_boundary: bool


class TraversalNeighborhoodParameters(OperatorParameters):
    """Declared parameters of the Traversal category.

    Attributes:
        seed_entity_classes: Where the walk starts, in ontology vocabulary.
        relationship_types: Which typed edges the walk may cross. Typed, per
            INV-CH7-20 — a walk over "all edges" is not a bounded expansion of
            relevance, it is a table scan with extra steps.
        depth_limit: Maximum hops from a seed. Required, no default: the bound
            is the operator's entire correctness claim (INV-CH7-24), and a
            default bound is one nobody chose.
    """

    seed_entity_classes: frozenset[str]
    relationship_types: frozenset[str]
    depth_limit: int
