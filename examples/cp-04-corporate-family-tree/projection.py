"""Π at L5 — shape the composed view into section D.6's emitted contract.

[ADAPT] all of it. [MECHANISM] the ``ProjectionPlan`` Protocol this satisfies.

**THE ONTOLOGY IS SERVED AND IT CONDITIONS Π. IT DOES NOT CONSTRAIN THE WALK.**
Section D.2.1 names four roles for the ontology and this rung builds two of
them here:

* **Role 2 — SERVED.** Every node in the emitted payload carries its FIBO class
  chain, on rung 01's ``payload["counterparty"]["type_chain"]`` precedent. This
  is what makes the product self-describing over MCP: a consuming agent knows an
  SPV is an SPV without a second lookup. Gate ``CFT-G15``.
* **Role 3 — PROJECTION.** The perspective conditions on FIBO CLASS. Two
  declared roles read the SAME class off the SAME ``type_chain`` the graph
  carries, from opposite sides of it, and shape what they detail accordingly.
  Gate ``CFT-G16``.

* **Role 4 — VALIDATION** is ``CFT-G01`` and ``CFT-G02`` and belongs to plan
  ``24.4-10``. The split is deliberate: validation asserts a property of what
  was served, and it is written where the sabotage that must turn it red is
  written, not here.

* **Role 1 — CONSTRAINT — IS STRUCK FROM THIS RUNG**, 2026-08-31 (Dave). There
  is no type-constrained walk, no per-hop admitted-class filter, no anchor or
  depth chosen to make a constraint bite, and no stopped-at node anywhere. The
  reason is measured and closed twice over: over all 748 family nodes no
  LEI-bearing anchor reaches a node outside the 7-class ``LegalPerson``
  ``Corporation`` profile within depth 3 (``D-32``), and the Traversal family
  types the walk on EDGES only, so a node-class admission filter has no SDK
  expression at all (``D-33``). ``seed_entity_classes`` — which
  ``ccf_config.yaml`` declares because the SDK schema requires it — selects walk
  STARTING POINTS (``src/ccf/graph/protocols.py::TraversalSpec``) and never
  filtered neighbors per hop; declaring it reinstates nothing. **The anchor, the
  depth of 3 and the ceiling of 6 are unchanged by the striking**, and no
  positive-property restatement of role 1 appears anywhere in this example —
  that was refused BY NAME as a tautology over a class-homogeneous population.

**THE POPULATION IS CLASS-HOMOGENEOUS AND THAT IS MEASURED, NOT ASSUMED.** All
22 SMCI-subtree nodes carry the IDENTICAL 7-class chain, so no FIBO class
discriminates BETWEEN members — the same measured property that withdrew role 1.
What the two roles' views differ by is therefore the class's presence on ALL of
them, and the conditioning is written so that ONE mutation to ONE node's chain
moves that node in BOTH views, in opposite directions. A hand-written role map
keyed by entity name cannot reproduce that, which is precisely the substitution
``CFT-G16`` is sabotaged with — and it is why the gate must read what the
projection DID rather than what it is called. The word "class" appears in both a
class-conditioned projection and a role map keyed by class name.

**NO DICTIONARY OF ROLE TO ENTITY NAMES EXISTS IN THIS EXAMPLE.** The only
role-keyed document is
``artifacts/source-vocabulary.yaml::perspective_conditioning.roles``, which maps
each role to a SIDE of one declared class axis — ``carries`` or ``lacks`` — and
names no entity at all.

**WHAT THIS MODULE READS AND WHAT IT REFUSES TO RE-DO.** The served member set
is whatever the L4 traversal operator left in the view. This module never
re-walks, never re-filters and never intersects that set with a second
computation: a projection that quietly reapplied the depth bound would make the
operator decorative, and would hide the one place the SDK's walk and this
product's tree disagree. See ``deployment.py::FamilyScenario.depth_by_node`` for
that disagreement, measured, and ``D-36`` for the gap it records.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ccf.graph.protocols import GraphView
from ccf.projection.plan import Perspective, ProjectionOutput

import deployment

#: The word this payload uses where a value could not be evaluated. Never `0`
#: and never `null`-as-a-lookup-that-came-back-empty: a zero reads as a measured
#: nothing, which is a claim about the world (spec section C.4 trap 5).
NOT_EVALUABLE = "NOT_EVALUABLE"

#: The finding this rung adds beside the cycles and the duplicate pairs —
#: `D-IMPL-229`. It carries the ROSTER of the members that resolved to no
#: `ccf_v2.legal_entity` row, never a count, because a right count with a wrong
#: member audits clean forever (`D-13`).
FINDING_UNRESOLVED_JURISDICTION = "unresolved_jurisdiction"


class FamilyTreeProjection:
    """Shape the composed view into the section D.6 emitted contract.

    **Π HERE IS ROLE-CONDITIONING AND THAT IS NEW ON THE LADDER.** At rung 03
    every authorized caller got the same SHAPE and what differed per principal
    was WHICH OBLIGORS EXISTED, settled upstream by Policy. At this rung the
    member set is the same for both declared roles — the family is the family —
    and what differs is WHAT EACH ROLE IS SHOWN ABOUT EACH MEMBER, conditioned
    on the class chain the graph carries.

    **THE SUPPRESSION ARGUMENT STILL HOLDS STRUCTURALLY.** Nothing here filters
    a member out. A member the L4 Policy operator excluded is simply absent from
    the view, so section B.2's suppression-silence rule is a property of the
    composition rather than of a branch this class could forget to take.
    """

    def __init__(
        self,
        *,
        plan_id: str,
        required: tuple[str, ...],
        scenario: Any,
        minted: Mapping[str, str],
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._scenario = scenario
        # SOURCE IRI -> the URI L2 MINTED for it, taken from what
        # `worker.ingest` reported and never recomputed. The graph mints
        # `<entity-class>://<identity-hash>`
        # (`src/ccf/assembly/worker.py::SpecDrivenEntityResolution.identity`)
        # and the identity keys are CONSUMED by the resolver rather than stored
        # back as attributes — so the source IRI is not readable off a served
        # record, and rehashing it here would be this module reimplementing
        # L2's identity rule.
        self._minted = dict(minted)
        self._source_of = {minted_uri: uri for uri, minted_uri in minted.items()}
        # WHAT THIS PROJECTION SERVED, once it has served it. `None` until
        # `invoke` runs, and read back off the emitted node blocks rather than
        # stored ahead of them — see `served_members` for why the distinction is
        # the whole point.
        self._served_members: tuple[str, ...] | None = None

    @property
    def plan_id(self) -> str:
        return self._plan_id

    @property
    def served_members(self) -> tuple[str, ...]:
        """The members this projection PUT IN THE PAYLOAD, in emitted order.

        **THE ONE PLACE THE SERVED ROSTER IS KNOWN, AND IT IS PUBLISHED RATHER
        THAN RECOMPUTED.** `produce.py::measure_debt` needs the served population
        to take `S` over — and `S` over the deployment's SOURCE-READ population
        instead is the wrong denominator the 2026-09-01 close panel found: at
        `max_depth=1` the product served 20 members and still reported `20/22`,
        and `D_c` read `0.0909` at every depth, a scalar that could not move with
        what was actually served. A second computation of "the served members"
        somewhere downstream would rebuild exactly that defect one level up.

        **READ OFF `payload["nodes"]`, NOT OFF THE `served` LOCAL.** The two are
        the same set today and the distinction is what makes the reading
        defect-resistant: a build that filtered members OUT of the emitted node
        blocks — the `CFT-G09` sabotage, dropping the members whose PostgreSQL
        join failed — moves this roster, and therefore moves `S`. A roster
        recorded before the payload was shaped would not notice.

        Raises rather than returning an empty tuple when `invoke` has not run:
        an empty roster is `S = 0` by `_agreement`'s vacuity rule, so a silent
        empty here would present *never projected* as *total disagreement*.
        """
        if self._served_members is None:
            raise RuntimeError(
                "the served roster was read before this projection ran. It is"
                " what `invoke` emitted, so there is nothing to report until it"
                " has emitted something"
            )
        return self._served_members

    def required_operators(self) -> tuple[str, ...]:
        """From the product class's own document — the one authored set."""
        return self._required

    # -- Ontology role 3: the conditioning ----------------------------------

    def _detailed_for(self, role: str, type_chain: Sequence[str]) -> bool:
        """Does ``role`` detail a member carrying ``type_chain``?

        **THE ONLY PLACE A ROLE MEETS A CLASS, AND IT READS THE GRAPH'S OWN
        CHAIN.** One declared axis, two sides. The credit officer details the
        members that CARRY the axis class; the KYC analyst details the ones that
        do NOT — a KYC analyst's subject in a corporate family is the
        non-corporate party, a natural person or a beneficial owner.

        **ONE MUTATION MOVES A NODE IN BOTH VIEWS**, which is what makes
        ``CFT-G16`` able to fail. Strip the axis class from one node's chain and
        that node leaves the credit officer's detailed set and enters the KYC
        analyst's. A role map keyed by entity name would not move at all.

        No membership list, no entity name and no per-role branch on a node
        identity appears anywhere in this method or this module.
        """
        carries = deployment.class_axis_iri() in tuple(type_chain)
        side = deployment.conditioned_roles()[role]
        return carries if side == deployment.AXIS_CARRIES else not carries

    # -- The emitted contract ----------------------------------------------

    def _attributes(self, uri: str) -> Mapping[str, Any] | None:
        """The resolved `legal_entity` row for one member, or ``None``.

        **``None`` IS A NULL RESOLUTION AND NEVER A DROPPED MEMBER** (``D-16``,
        gate ``CFT-G09``). 20 of the SMCI subtree's 22 members hold no row, and
        a build that served only the two that do would return a smaller, tidier,
        WRONG family with no error and a concentration denominator wrong in the
        safe-looking direction.

        **THE JURISDICTION IS WHATEVER THE ROW HOLDS, AND ABSENT WHERE THERE IS
        NO ROW** (``D-IMPL-229``). Dave: *"A missing Postgres row is not
        `US-DE`."* There is no fallback here and no ``or`` — the fill-from-anchor
        sabotage is the addition of exactly one, and it leaves the served
        jurisdiction SET unchanged at ``{NL, US-DE}`` while putting a value on
        20 nodes no source asserted it about.
        """
        node = self._scenario.facts.get(uri)
        lei = None if node is None else node.lei
        if lei is None:
            return None
        row = self._scenario.attributes.rows.get(lei)
        return dict(row) if row else None

    def _node(self, uri: str, record: Any, role: str) -> Mapping[str, Any]:
        """One family member as the section D.6 contract shapes it."""
        node = self._scenario.facts[uri]
        chain = node.type_chain
        detailed = self._detailed_for(role, chain)
        return {
            "uri": uri,
            # The canonical URI L2 minted — the fabric's own name for this
            # member, which exists only because the write path ran.
            "entity_id": record.claim.entity_uri,
            "lei": node.lei,
            "label": node.label,
            # ONTOLOGY ROLE 2 — SERVED, on every node and not on a sample.
            # `CFT-G15` is sabotaged by serving the tree without it.
            "type_chain": list(chain),
            # THE TRUE DIRECTED GENERATION, read at the declared CEILING rather
            # than at the caller's depth. `deployment.py::depth_by_node` records
            # why the two bounds differ and what the L4 walk does instead.
            "depth": self._scenario.generation_by_node.get(uri, NOT_EVALUABLE),
            "attributes": self._attributes(uri) if detailed else None,
            # WHAT THIS ROLE WAS SHOWN AND WHY, carried on the member rather
            # than only at the product: a reader holding one member is owed the
            # conditioning it was shaped under. The class is named by its LOCAL
            # name, the census vocabulary, derived from the declared IRI.
            "conditioning": {
                "role": role,
                "class_axis": deployment.class_axis_local_name(),
                "carries_class_axis": deployment.class_axis_iri() in tuple(chain),
                "detailed": detailed,
            },
        }

    def _finding(self, finding: Any) -> Mapping[str, Any]:
        """One finding, in the four-key shape `expected.yaml` declares.

        Four keys always present and nullable where they do not apply. A cycle
        is A SET PLUS THE EDGE THAT CLOSES IT; the closing edge is what a
        flattened representation loses, and ``CFT-G07`` is sabotaged by dropping
        precisely that.
        """
        return {
            "type": finding.type,
            "predicate": finding.predicate,
            "members": list(finding.members),
            "closing_edge": (
                None if finding.closing_edge is None else list(finding.closing_edge)
            ),
        }

    def _unresolved_finding(self, served: Sequence[str]) -> Mapping[str, Any]:
        """The members this payload resolved no attribute row for — ``D-IMPL-229``.

        **A ROSTER, NEVER A COUNT AND NEVER ``len(findings) > 0``.** That is the
        discipline ``D-13`` fixed for cycles and ``D-IMPL-229`` applies here by
        name: a right count with a wrong member audits clean forever, and a
        roster-blind assertion accepts twenty entirely different nodes.

        **ORTHOGONAL TO THE TREE**, exactly as the cycle findings are. Not one
        member is dropped and not one is marked on the node — the marking would
        put the shortfall on the thing it is a shortfall ABOUT, and 20 of 22 is
        the answer rather than a defect report.

        **SCOPED TO WHAT THIS PAYLOAD SERVED**, and the scope is a deliberate
        difference from the cycle findings beside it. A circuit is a property of
        the FAMILY and is reported whole even where the caller's depth truncates
        it — hiding the headline finding at depth 1 would be the worse error. An
        unresolved attribute row is a property of THIS PAYLOAD's members: a
        member this payload does not carry has no attributes here to be
        unresolved. At the declared default depth of 3 the two scopes coincide
        on all 22.
        """
        return {
            "type": FINDING_UNRESOLVED_JURISDICTION,
            "predicate": None,
            "members": [
                uri
                for uri in served
                if self._scenario.jurisdictions.get(uri) is None
            ],
            "closing_edge": None,
        }

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        """Interpret the composed view for ``perspective``."""
        scenario = self._scenario
        role = perspective.role
        # THE SERVED SET IS WHATEVER THE OPERATORS LEFT, in a stable order.
        # Nothing here re-walks and nothing re-filters.
        by_uri = {
            source: record
            for record in view.entities
            if (source := self._source_of.get(record.claim.entity_uri)) is not None
        }
        served = sorted(by_uri)
        admitted = set(served)

        anchor_uri = scenario.anchor_uri
        anchor_node = scenario.facts.get(anchor_uri)
        nodes = [self._node(uri, by_uri[uri], role) for uri in served]
        payload: dict[str, Any] = {
            "anchor": {
                "uri": anchor_uri,
                "lei": None if anchor_node is None else anchor_node.lei,
                "label": None if anchor_node is None else anchor_node.label,
                "type_chain": (
                    [] if anchor_node is None else list(anchor_node.type_chain)
                ),
            },
            "nodes": nodes,
            # EDGES BETWEEN SERVED MEMBERS ONLY. An edge whose far end the
            # operators did not admit is not served pointing into nothing —
            # which is INV-CH7-40's no-leak-by-absence read at the payload.
            "edges": [
                {
                    "parent": parent,
                    "child": child,
                    "predicate": predicate,
                }
                for parent, child in sorted(scenario.edges.by_pair)
                if parent in admitted and child in admitted
                for predicate in sorted(scenario.edges.predicates_for((parent, child)))
            ],
            "findings": [
                *(self._finding(finding) for finding in scenario.findings),
                self._unresolved_finding(served),
            ],
            "max_depth_applied": scenario.max_depth,
            # THE ATTRIBUTE POLICY ADMITTED ON, RETURNED AS WELL AS FILTERED ON.
            # A product that filters on a field it does not return cannot be
            # audited from its own payload — rung 03's rule, applied to the axis
            # `D-IMPL-229` moved this product onto.
            "family": {
                "attribute": deployment.membership_attribute(),
                "value": scenario.family,
                "source": deployment.membership_source(),
            },
            # THE SERVED JURISDICTION SET, carried on the payload as
            # `D-IMPL-229` requires. **Derived from the node blocks THIS ROLE
            # was actually served**, not from the deployment's own read: a
            # payload-level roster naming values the member blocks beside it do
            # not carry would show a role at the aggregate what it was not shown
            # at the member, which is the shape a suppression leak takes. A
            # member with no resolved row contributes nothing, because a null is
            # not a jurisdiction and a null token inside a closed set is
            # refused by name (`D-IMPL-229`).
            #
            # The CLOSED-WORLD check is upstream of here and is a fact about the
            # FAMILY rather than about a role's view —
            # `deployment.py::refuse_open_jurisdiction_world` runs over the
            # source read, in both directions, before anything is served.
            "jurisdictions": sorted(
                {
                    value
                    for node in nodes
                    if (attributes := node["attributes"]) is not None
                    and (value := attributes.get(deployment.jurisdiction_column()))
                    is not None
                }
            ),
            "perspective_role": role,
            "class_axis": deployment.class_axis_local_name(),
            # HOW MANY MEMBERS THIS ROLE WAS SHOWN DETAIL FOR. Two roles over
            # one family give two different numbers from one class read, which
            # is what §D.2.1 role 3 claims and what `CFT-G16` reads.
            "detailed_members": sorted(
                uri
                for uri in served
                if self._detailed_for(role, scenario.facts[uri].type_chain)
            ),
            "minted_uris": {uri: self._minted[uri] for uri in served},
        }
        # RECORDED FROM THE EMITTED BLOCKS, so what `S` is taken over is what
        # the consumer receives. See `served_members`.
        self._served_members = tuple(node["uri"] for node in payload["nodes"])
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


def plan_class() -> type[FamilyTreeProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return FamilyTreeProjection
