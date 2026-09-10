"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. This file names all of it and makes no fabric call the spine does not.
Delete ``ccf_config.yaml`` and nothing here has anything left to interpret,
which is the No-Hardcoding Rule (CLAUDE.md §6.4) being structural rather than
aspirational.

**Its boundaries are ruled** (`D-IMPL-315`): vocabulary, source access and
admission. No binder, no gates, no replay record, no serve — those are
``GovernedResolver``'s, and ``produce.py`` hands it the seam.

## The ingestion-order contract, and why it is a contract

Two kinds of envelope reach L2 from here:

* **edge envelopes**, carrying two endpoint references and a predicate, and
  deliberately no attributes — an edge asserts that two nodes are related and
  nothing about what either node *is*;
* **node envelopes**, carrying one node's attributes.

**Edges are ingested FIRST and nodes LAST, and that order is load-bearing.**
Measured on this SDK: a claim carrying fewer attributes at the same URI
*supersedes* the richer one rather than merging into it, so an edge envelope
arriving after a node envelope erases that node's attributes and the payload
then serves a node with no name, no LEI and no class chain. Nothing raises.

The order is therefore enforced here rather than remembered:
:func:`ingest` is the only function that writes, it emits both kinds itself,
and it asserts the resulting state before returning. **This deployment does not
ask the SDK for attribute-merge semantics** — that would be widening the fabric
to avoid stating an ordering, and the ordering is a true fact about how this
estate's evidence arrives (`D-IMPL-316`, the ingestion-order contract).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.controlplane.artifacts import (
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.controlplane.artifacts import DebtProfile
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.constraints import CAPABILITY_TRAVERSAL_DEPTH, TechnicalCapability
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from projection import CHAIN_SEPARATOR

HERE = Path(__file__).parent

#: The request parameters this deployment reads by name.
ANCHOR = "lei"
FAMILIES = "families"
MAX_DEPTH = "max_depth"


def config() -> Mapping[str, Any]:
    """The single deployment document, parsed."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return document


def connection(*, root: Path) -> Mapping[str, str]:
    """Where the FABRIC's own L3 lives for this run. Never a source store."""
    profile = yaml.safe_load(
        (HERE / "backends.yaml").read_text(encoding="utf-8")
    )["declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {
        "database_path": str(
            root / f"{profile['prefix']}{profile['suffix']}"
        )
    }


def request(
    *, anchor_lei: str, families: Sequence[str], asked_at: datetime,
    max_depth: int | None = None,
) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    ``max_depth`` is omitted entirely when the caller did not supply one, so
    the class default in ``ccf_config.yaml`` is what resolves — read from the
    declaration rather than restated here, where it would become a second
    authority for one number.
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {ANCHOR: anchor_lei, FAMILIES: list(families)}
    if max_depth is not None:
        parameters[MAX_DEPTH] = max_depth
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=anchor_lei,
        intent="credit-concentration",
        freshness="standard",
        asked_at=asked_at,
        parameters=parameters,
    )


def perspective() -> PerspectiveArtifact:
    """The Π role-conditioning this product is served under."""
    declared = dict(config()["default_perspective"])
    return PerspectiveArtifact(semver="1.0.0", **declared)


def traversal_capability() -> TechnicalCapability:
    """The graph leg's declared traversal ceiling, as a technical capability.

    Read from ``backends.yaml`` — a deployment fact, not Control Plane state.
    Supplying it is what lets a request above the ceiling be refused as a
    governed determination with authority ``technical`` rather than silently
    answered at a depth nobody asked for.
    """
    declared = yaml.safe_load((HERE / "backends.yaml").read_text(encoding="utf-8"))
    ceiling = declared["declaration"]["sources"]["corporate_family_graph"]["settings"][
        "max_traversal_depth"
    ]
    return TechnicalCapability(
        capability=CAPABILITY_TRAVERSAL_DEPTH,
        maximum=Decimal(str(ceiling)),
        # What the ceiling is a property OF. Named so replay can tell one
        # backend's limit from another's.
        identity=f"corporate_family_graph/max_traversal_depth={ceiling}",
    )


def acquire_for(booted: BootedFabric, asked: ProductRequest) -> acquisition.Family:
    """Read both source stores for the question asked.

    **At the BACKEND's declared ceiling, not at the caller's depth**, and the
    distinction is the successor's sharpest structural point. The caller's
    ``max_depth`` is governed request state and is applied at Π, where
    `GovernedResolver` hands the plan factory the EFFECTIVE request. Reading at
    the caller's depth would require this deployment to resolve the effective
    request BEFORE the resolver does, which is a second authority for one value
    and the very substitution cp-04 was repaired of.

    The consequence, stated plainly: the source read is the SAME for every
    depth, so what a caller's number changes is the payload — and therefore the
    product's content address — rather than what was fetched.
    """
    ceiling = int(traversal_capability().maximum)
    return acquisition.acquire(
        anchor_lei=str(asked.parameters[ANCHOR]), depth=ceiling
    )


def _node_envelope(
    family: acquisition.Family, node: acquisition.Node, *, tenant_id: str,
    at: datetime,
) -> SignalEnvelope:
    """One node's attributes, under the fabric's own vocabulary."""
    # ATTRIBUTED, therefore LAST. See `_edge_envelope`'s warning: this claim
    # is the one that must survive, and it only survives if nothing thin
    # arrives at this URI after it.
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{node.uri}",
        source=SourceIdentity(system_id="corporate_family_graph"),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "node_ref": node.uri,
            "entity_uri": node.uri,
            "lei": node.lei or "",
            "label": node.label or "",
            "type_chain": CHAIN_SEPARATOR.join(node.type_chain),
            # Minted at admission by the walk, never inherited or joined in.
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
       attributes to give them, so the claim it mints is thin.

       **The last claim at a URI wins; it does not merge.** Measured on this
       SDK: a thin claim arriving after an attributed one supersedes it, and
       the node is then served with no name, no LEI and no class chain, with
       nothing raised. Chronological intuition says "edges are facts we learn
       later, so ingest them later" — that intuition is what erases the
       attributes, and it is why this warning sits beside the envelope rather
       than only in the module docstring.

       Whether last-wins-empty is the right rule for multi-source accumulation
       (INV-CH7-17) is a separate question and deliberately NOT answered here.
       This spine does not merge attributes, and it does not ask the SDK to.
    """
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id="corporate_family_graph"),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "parent_ref": edge.source_uri,
            "parent_uri": edge.source_uri,
            "child_ref": edge.target_uri,
            "child_uri": edge.target_uri,
            # SELECTS among the six declared rules. It cannot name a type no
            # rule declares: the comparison is against the rule.
            "predicate": edge.predicate,
        },
    )


def ingest(
    booted: BootedFabric, family: acquisition.Family, *, at: datetime
) -> None:
    """Write the family into L3 through the ONE write handle, in order.

    ``booted.handle.worker`` is the only write handle to L3 anywhere in this
    process (single-writer, CLAUDE.md §10).

    **Edges first, nodes last** — the module docstring's contract. Asserted
    rather than trusted: a node whose attributes were erased by a later thin
    claim is served silently, so the check has to be here, where the write
    happened, rather than in a test that may not be run.
    """
    worker = booted.handle.worker

    # =====================================================================
    # MEASURED PRODUCER INVARIANT — NOT A STYLISTIC PREFERENCE.
    #
    #   Emit thin relationship envelopes FIRST.
    #   Admit richer attributed entity claims AFTERWARD.
    #
    # A later thin claim SUPERSEDES the richer entity at the same URI and can
    # ERASE its attributes. Measured on this SDK: an attributed claim carrying
    # {lei, label, type_chain, family_id} became {} when an endpoint-only claim
    # for the same URI arrived after it. Nothing raised, and the product then
    # serves nodes with no name, no LEI and no class chain.
    #
    # This is exactly the kind of "cleanup" a later reader reverses on
    # chronological intuition — "edges are facts we learn later, so ingest them
    # later." That intuition is what erases the attributes. Do not reorder
    # these two loops. The assertion below is what makes a reorder loud instead
    # of silent.
    #
    # Whether last-claim-wins is the right rule for multi-source accumulation
    # (INV-CH7-17) is a separate question, deliberately not answered here. This
    # spine does not merge attributes and does not ask the SDK to.
    # =====================================================================
    for ordinal, edge in enumerate(family.edges):
        worker.ingest(_edge_envelope(edge, tenant_id=booted.tenant_id, at=at, ordinal=ordinal))
    for node in family.nodes:
        worker.ingest(_node_envelope(family, node, tenant_id=booted.tenant_id, at=at))

    view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=at)
    unattributed = [
        record.claim.entity_uri
        for record in view.entities
        if not record.claim.attributes.get("family_id")
    ]
    if unattributed:
        raise AssertionError(
            f"{len(unattributed)} of {len(view.entities)} admitted nodes carry no"
            " attributes after ingestion. The ingestion-order contract was"
            " violated: an endpoint-only claim arrived after the node's own"
            f" claim and superseded it. First: {sorted(unattributed)[0]!r}"
        )


def debt(view: GraphView) -> DebtAssessment:
    """D_c over the view the OPERATORS produced — see `CP04C-F-02`.

    .. warning::

       **This is not yet the served roster, and the difference is measured.**
       ``GovernedResolver`` hands this scorer ``execution.view`` — the graph
       view the operators produced — not the projection's output. Because this
       deployment applies the caller's depth at Π, the payload can serve fewer
       nodes than the scorer counted: measured on this family, the scorer sees
       50 nodes / 30 resolved at every depth while the payload serves 36/16 at
       depth 1 and 49/29 at depth 3. ``D_c`` is therefore **0.4 at every
       depth** — a scalar that cannot move with the answer, which is exactly
       the wrong-denominator defect cp-04's own specification was corrected for.

       This is **not** an SDK defect. The SDK measures debt over what was
       assembled; a projection that then serves less is choosing to. The fix
       belongs on this side of the seam and is recorded as `CP04C-F-02`,
       because choosing it interacts with a ruled constraint and is not this
       module's to decide unilaterally.
    """
    entities = list(view.entities)
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
            # The one factor this estate can actually move. Freshness and
            # completeness are 1 and SAID to be 1 rather than quietly assumed:
            # every served node was observed in this run's own read, and every
            # node the walk admitted is in the payload. What varies is whether
            # the ATTRIBUTE leg had a row for it.
            semantic_consistency=served,
        ),
        profile=DebtProfile.model_validate(
            {"semver": "1.0.0", **config()["debt_profile"]}
        ),
    )


@dataclass(frozen=True)
class FamilyScenario:
    """What one run needs — satisfies ``produce.Scenario`` structurally."""

    family: acquisition.Family
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
        """However many the deployment declared — never a fixed count."""
        return tuple(config()["operators"])

    @property
    def plan_id(self) -> str:
        return f"cp-04-canonical.corporate-family/{self.family.anchor_lei}"

    @property
    def max_ttl_seconds(self) -> int:
        return int(
            timedelta(days=int(config()["half_life"]["ownership_edges"]["half_life_seconds"] // 86400)).total_seconds()
        )

    @property
    def product_ttl_seconds(self) -> int:
        """From the entity freshness anchor the class declares."""
        return int(config()["half_life"]["entity_attributes"]["half_life_seconds"])
