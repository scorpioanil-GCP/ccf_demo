"""Π — the role-conditioned view of the family this product serves.

[ADAPT] everything. [MECHANISM] the two Protocol members: `required_operators`
and `invoke`. Π is deployment code by construction (whitepaper §7.5); the fabric
constructs this class and calls it, and never rewrites what it does.

**Everything served here is read off the GRAPH VIEW the resolver hands in.**
Not off the acquisition result, not off a scenario object carried in from the
side. The two legs' facts became fabric state at L2, they were shaped by the
policy envelope and the walk at L4, and what survives is what a consumer is
told. Reading around the view would serve rows the policy operator excluded.

**Cycles are enumerated HERE, inside the resolver's call to this projection**,
because an ownership circuit is a property of the admitted subgraph and cannot
be known before the admission is known. The graph store has no in-store
graph-algorithm library, so the enumeration is application-side — which the
assembly recipe declares as `operator: null` rather than pretending a registered
operator ran. A step that declares a Standard name but is not a registered
operator does not enter `operators_invoked`, and lineage strict equality is why
that distinction is load-bearing rather than tidy.

**A cycle is a FINDING, not an error.** Mutual and circular ownership is
ordinary in real corporate structures — this fixture's family carries 22 mutual
pairs — and a product that raised on one would be unable to describe the estates
it exists to describe. The circuit is returned with an ordered roster and its
closing edge, so a reader can see the loop rather than be told one exists.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent

#: The attribute the walk mints at admission, carried on every node.
FAMILY_ID = "family_id"

#: Attribute keys the vocabulary layer writes onto an admitted node.
DEPTH = "depth"
LEI = "lei"
LABEL = "label"
TYPE_CHAIN = "type_chain"
RESOLVED = "attributes_resolved"

#: How a multi-valued class chain is carried through a `Mapping[str, str]`.
#: The separator is declared once here and read back once below, so the
#: encoding has one definition rather than two that could drift.
CHAIN_SEPARATOR = " | "


def declaration() -> Mapping[str, Any]:
    """Π's declared values, read from `artifacts/projection.yaml`."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "projection.yaml").read_text(encoding="utf-8")
    )
    return document["declaration"]


def _circuits(
    edges: Sequence[tuple[str, str]], *, max_length: int
) -> list[tuple[str, ...]]:
    """Every elementary circuit up to `max_length`, each counted once.

    Bounded depth-first search from each node, with two properties that make
    the result a set rather than a bag:

    * a circuit is recorded under its **canonical rotation** — rotated to start
      at its lexicographically smallest member — so one loop found from three
      different starts is one entry, not three;
    * expansion only follows nodes ordered after the start, which stops the
      same circuit being re-discovered from each of its own members.

    Returned sorted, because a payload whose ordering depends on dictionary
    iteration is a payload whose content address depends on it too.
    """
    adjacency: dict[str, set[str]] = {}
    for subject, obj in edges:
        adjacency.setdefault(subject, set()).add(obj)

    found: set[tuple[str, ...]] = set()
    for start in sorted(adjacency):
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for following in sorted(adjacency.get(node, ())):
                if following == start and len(path) >= 2:
                    pivot = path.index(min(path))
                    found.add(tuple(path[pivot:] + path[:pivot]))
                elif (
                    following not in path
                    and len(path) < max_length
                    and following > start
                ):
                    stack.append((following, [*path, following]))
    return sorted(found)


class CorporateFamilyProjection:
    """The family as a typed tree, its class chains, and its cycles.

    The role conditions on the FIBO class chain each node carries rather than on
    a hand-written role map, which is what lets a different terminal condition
    become a different class predicate instead of a different code path.
    """

    def __init__(
        self, *, plan_id: str, required: tuple[str, ...], declared: Mapping[str, Any]
    ) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set of its own and has none to author.
        self._required = required
        self._declared = declared

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The set the SDK supplied, returned unchanged."""
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        """Shape the admitted subgraph into what this role is served."""
        cycles = self._declared["cycles"]

        nodes = [
            {
                "uri": record.claim.entity_uri,
                "lei": record.claim.attributes.get(LEI) or None,
                "label": record.claim.attributes.get(LABEL) or None,
                "depth": int(record.claim.attributes.get(DEPTH, "0")),
                "type_chain": [
                    name
                    for name in record.claim.attributes.get(
                        TYPE_CHAIN, ""
                    ).split(CHAIN_SEPARATOR)
                    if name
                ],
                # Whether the ATTRIBUTE leg resolved this node. Served as a
                # fact rather than implied by absent keys, because "no row" and
                # "a row of nulls" are different claims about the world.
                "attributes_resolved": record.claim.attributes.get(RESOLVED) == "true",
            }
            for record in view.entities
        ]
        nodes.sort(key=lambda entry: str(entry["uri"]))

        relationships = sorted(
            (
                {
                    "subject": record.claim.subject_uri,
                    "predicate": record.claim.relationship_type,
                    "object": record.claim.object_uri,
                }
                for record in view.relationships
            ),
            key=lambda entry: (
                str(entry["subject"]),
                str(entry["predicate"]),
                str(entry["object"]),
            ),
        )

        circuits = _circuits(
            [
                (record.claim.subject_uri, record.claim.object_uri)
                for record in view.relationships
            ],
            max_length=int(cycles["max_length"]),
        )
        cap = int(cycles["roster_cap"])

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "family_id": next(
                    (
                        record.claim.attributes[FAMILY_ID]
                        for record in view.entities
                        if FAMILY_ID in record.claim.attributes
                    ),
                    None,
                ),
                "node_count": len(nodes),
                "relationship_count": len(relationships),
                "resolved_count": sum(
                    1 for entry in nodes if entry["attributes_resolved"]
                ),
                "nodes": nodes,
                "relationships": relationships,
                "findings": {
                    "cycles_found": len(circuits),
                    "max_length_enumerated": int(cycles["max_length"]),
                    # The roster can be shorter than the count, and when it is,
                    # the payload says so in its own fields rather than leaving
                    # a reader to compare two numbers and guess.
                    "roster_truncated": len(circuits) > cap,
                    "cycles": [
                        {
                            "members": list(circuit),
                            # The edge that closes the loop, named explicitly.
                            # A roster alone leaves a reader to infer which hop
                            # returns to the start.
                            "closing_edge": {
                                "subject": circuit[-1],
                                "object": circuit[0],
                            },
                        }
                        for circuit in circuits[:cap]
                    ],
                },
            },
        )


def plan_class() -> type[CorporateFamilyProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return CorporateFamilyProjection
