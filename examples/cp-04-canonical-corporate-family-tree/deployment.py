"""The deployment's own vocabulary and its three verbs: acquire, project's plan id, assess.

[ADAPT] everything here — every name is this product's. [MECHANISM] the two
context types imported from the SDK; nothing else is SDK code.

**Re-expressed on the paved road** (`D-IMPL-343`; CP-14 Gate 2 slice 2). The
canonical spine this module used to serve — a boot, a connection minted from
``backends.yaml``, an effective-depth RE-DERIVATION through the SDK's own
constraint resolver, an ingest loop over the one write handle, a scenario
object restating five manifest keys and two TTL figures — is gone. What
remains is what only this deployment can say: how the two source stores are
read at the EFFECTIVE request the SDK hands in, how a family becomes dated
claims under the fabric's vocabulary, and what its Context Debt is.

**Thin edges first, attributed nodes last** — still this module's contract,
now held by the ORDER in which :func:`acquire` yields envelopes: the paved
seam ingests them in that order through L2's one writer. The post-ingest
assertion the canonical spine ran over the view has no home on this road (the
seam holds no reader) and is recorded as dropped in ``FINDINGS.md``.

**One authority for the graph leg's ceiling.** ``backends.yaml`` restated the
traversal operator's ``depth_limit`` as ``max_traversal_depth``; the technical
capability is now read off the one declaration in ``ccf_config.yaml``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.constraints import CAPABILITY_TRAVERSAL_DEPTH, TechnicalCapability
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from projection import CHAIN_SEPARATOR

HERE = Path(__file__).parent

#: The request-contract argument names — the contract's, restated nowhere.
ANCHOR = "lei"
FAMILIES = "families"
MAX_DEPTH = "max_depth"

#: The environment document's names for the two source legs.
SOURCE_GRAPH = "corporate_family_graph"
SOURCE_ATTRIBUTES = "corporate_family_attributes"

#: The one operator whose declared ceiling IS the graph leg's technical
#: capability (`ccf_config.yaml::operators`).
TRAVERSAL_OPERATOR = "traversal.typed-neighborhood"


def config() -> Mapping[str, Any]:
    """The one Control Plane document, parsed — read for the declared ceiling only."""
    parsed: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return parsed


def plan_id(anchor_lei: str) -> str:
    return f"cp-04-canonical.corporate-family/{anchor_lei}"


def traversal_capability() -> TechnicalCapability:
    """The graph leg's declared traversal ceiling, as a technical capability.

    Read off the traversal operator's own ``depth_limit`` — the backend ceiling
    ``ccf_config.yaml`` declares — rather than a second statement of the same
    number in a second document. Supplying it is what lets a request above the
    ceiling be refused as a governed determination with authority ``technical``
    rather than silently answered at a depth nobody asked for.
    """
    ceiling = int(config()["operators"][TRAVERSAL_OPERATOR]["depth_limit"])
    return TechnicalCapability(
        capability=CAPABILITY_TRAVERSAL_DEPTH,
        maximum=Decimal(ceiling),
        identity=f"{TRAVERSAL_OPERATOR}/depth_limit={ceiling}",
    )


# ---------------------------------------------------------------------------
# From the effective request to a read; from a read to fabric state.
# ---------------------------------------------------------------------------


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Read both source stores at the depth THIS ask is allowed to walk; hand back dated claims.

    The depth is the EFFECTIVE request's — the class default where the caller
    omitted one, the caller's value where it is in bounds — handed here by the
    resolver through the declared seam (`D-IMPL-343` R-4), so L3, the operator
    view and the payload are the same set (`CP04C-F-02`). A refused request
    never reaches this function. An unresolvable anchor still RAISES here
    (`CP14-F-21`, open): the walk's own contract, unchanged by the road.
    """
    effective = context.request.parameters
    family = acquisition.acquire(
        anchor_lei=str(effective[ANCHOR]),
        depth=int(effective[MAX_DEPTH]),
        graph=context.sources[SOURCE_GRAPH],
        attributes=context.sources[SOURCE_ATTRIBUTES],
    )
    return envelopes(family, tenant_id=context.tenant_id, at=context.instant)


def envelopes(
    family: acquisition.Family, *, tenant_id: str, at: datetime
) -> tuple[SignalEnvelope, ...]:
    """The family as dated claims — EDGES FIRST, NODES LAST, and the order is the contract."""
    return (
        *(
            _edge_envelope(edge, tenant_id=tenant_id, at=at, ordinal=ordinal)
            for ordinal, edge in enumerate(family.edges)
        ),
        *(_node_envelope(family, node, tenant_id=tenant_id, at=at) for node in family.nodes),
    )


def _node_envelope(
    family: acquisition.Family, node: acquisition.Node, *, tenant_id: str,
    at: datetime,
) -> SignalEnvelope:
    """One node's attributes, under the fabric's own vocabulary."""
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{node.uri}",
        source=SourceIdentity(system_id=SOURCE_GRAPH),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "node_ref": node.uri,
            "entity_uri": node.uri,
            "lei": node.lei or "",
            "label": node.label or "",
            "type_chain": CHAIN_SEPARATOR.join(node.type_chain),
            "family_id": family.family_id,
            "depth": str(node.depth),
            "attributes_resolved": str(
                bool(node.lei and node.lei in family.attributes)
            ).lower(),
        },
    )


def _edge_envelope(
    edge: acquisition.Edge, *, tenant_id: str, at: datetime, ordinal: int
) -> SignalEnvelope:
    """One typed family edge, carrying NO attributes.

    .. warning::
       **This envelope must reach L2 BEFORE the node envelope for either of
       its endpoints.** It resolves both endpoints as entities, and it has no
       attributes to give them, so the claim it mints is thin. **The last
       claim at a URI wins; it does not merge** — a thin claim arriving after
       an attributed one supersedes it, and the node is then served with no
       name, no LEI and no class chain, with nothing raised. :func:`envelopes`
       yields every edge before any node for exactly this reason.
    """
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id=SOURCE_GRAPH),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "parent_ref": edge.source_uri,
            "parent_uri": edge.source_uri,
            "child_ref": edge.target_uri,
            "child_uri": edge.target_uri,
            "predicate": edge.predicate,
        },
    )


# ---------------------------------------------------------------------------
# Context Debt.
# ---------------------------------------------------------------------------


def assess(context: AssessmentContext) -> DebtAssessment:
    """`D_c` over the view the OPERATORS produced — see `CP04C-F-02`.

    Unchanged in substance from the canonical spine's ``debt``: freshness and
    completeness are 1 and consistency is the resolved share of the admitted
    nodes. The D_c profile is the BOOTED artifact the paved road hands here —
    the exact document the pins record — never a second parse of the config.

    .. warning::
       ``GovernedResolver`` hands this scorer the graph view the operators
       produced, not the projection's output; because this deployment applies
       the caller's depth at Π, the payload can serve fewer nodes than the
       scorer counted (`CP04C-F-02`, recorded and not this module's to decide
       unilaterally).
    """
    assert context.profile is not None
    entities = list(context.view.entities)
    resolved = sum(
        1
        for record in entities
        if record.claim.attributes.get("attributes_resolved") == "true"
    )
    served = Decimal(resolved) / Decimal(len(entities)) if entities else Decimal(0)
    return assess_debt(
        DebtFactors(
            freshness=Decimal(1),
            completeness=Decimal(1),
            semantic_consistency=served,
        ),
        profile=context.profile,
    )
