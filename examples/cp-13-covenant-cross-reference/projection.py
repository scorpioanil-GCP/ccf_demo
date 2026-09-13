"""Π — the definition chain, its checked citations, and its debt.

[ADAPT] everything here. [MECHANISM] nothing.

**This module emits no citation it has not checked, and explains every one it
withholds.** Those are the same rule seen from two sides: a payload that
silently dropped an unauditable claim would be indistinguishable from one where
the claim never existed, and *"we could not evidence this"* is the answer a
credit officer needs.

Five things it refuses to do, each because one was measured:

* **Emit an extracted span because the text looks right.** All 49
  `CovenantDefinition` nodes carry a correct span, no `passageSha256` and no
  `evidencedBy`. 47 of 48 extractable spans read as genuine definitions, and
  **0** can be checked by any passage. That is the trap (`CXR-G19`).
* **Treat `ex:declaredAt` as a repair.** It marks a point anchor as intentional.
  It supplies no end offset (`CXR-G16`).
* **Guess an `endOffset`.** 158 `DefinedTerm` nodes have none and will not be
  given one.
* **Read "no embedding" as "nothing relevant".** 18 of 40 memoranda are
  unsearchable, which is a limitation and not a result (`CXR-G18`).
* **Assert a governing edge it cannot read.** `ex:governedBy` is 0 assertions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

import acquisition
from ccf.contracts.claims import PassageAnchor
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

#: The anchor vocabulary this deployment uses in `PassageAnchor.kind`. The SDK
#: fixes the anchoring OBLIGATION and deliberately not the anchor schema
#: (whitepaper §7.10.3 / `INV-CH7-19`), so the vocabulary is the deployment's.
ANCHOR_KIND = "mongodb-passage-id"

#: Why a chain node carries no citation. A CLOSED set — an unexplained
#: omission is the thing this product exists to refuse.
DEBT_REASONS: tuple[str, ...] = (
    "span-unverifiable",
    "point-anchor",
    "passage-has-no-sha256",
    "passage-not-found",
    "sha256-mismatch",
    "no-evidence-edge",
)


class CovenantCrossReferenceProjection:
    """The chain, the checked citations, and the reason for every absence."""

    def __init__(
        self, *, plan_id: str, required: tuple[str, ...], declared: Mapping[str, Any]
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._declared = declared

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The SDK's own set, passed straight through."""
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        del operator_outputs
        estate: acquisition.Estate = self._declared["estate"]
        in_view = {record.claim.entity_uri for record in view.entities}
        sources = [self._source(estate, source) for source in estate.sources]
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "asked_at": temporal_boundary.isoformat(),
                # WHAT THE TRAVERSAL SEEDED ON, declared rather than implied
                # (`CXR-G12`). The type whose NAME matches the question reaches
                # depth 3 once; this one reaches it 26 times.
                "traversal": {
                    "seeded_on": estate.seeded_on,
                    "resolve_depth": int(self._declared["resolve_depth"]),
                    "sources": len(sources),
                },
                "envelope": self._envelope(estate),
                "governing_text": self._governing(estate),
                "cross_references": sources,
                "citation_summary": self._summary(sources),
                "absent_legs": self._absent_legs(),
                "graph": {"entities_in_view": len(in_view)},
            },
        )

    # -- the envelope ------------------------------------------------------

    def _envelope(self, estate: acquisition.Estate) -> Mapping[str, Any]:
        """The policy envelope, and the proof that it bounded the retrieval.

        `candidates_examined` is the load-bearing figure (`CXR-G09`): with the
        bound applied first it equals the permitted, embedded population; a
        post-filter would have scored the whole corpus and this number would
        exceed it. A consumer can tell the two apart from the payload alone.
        """
        entitlement = estate.entitlement
        retrieval = estate.retrieval
        return {
            "principal": entitlement.principal,
            "corpus_scope": entitlement.corpus_scope,
            "permitted_classifications": sorted(entitlement.permitted_classes),
            "permitted_documents": len(entitlement.permitted_documents),
            "excluded_for_missing_classification": (
                entitlement.unclassified_excluded
            ),
            "retrieval": {
                "bound_applied": "before-ranking",
                "query_filter": dict(retrieval.query_filter),
                "candidates_examined": retrieval.candidates_examined,
                # NOT "no results". These are eligible and unsearchable, and
                # the payload says which (`CXR-G18`).
                "not_evaluable": {
                    "count": len(retrieval.not_evaluable),
                    "reason": "no-embedding",
                    "note": (
                        "these documents are inside the permitted set and carry"
                        " no embedding, so similarity cannot reach them at all."
                        " This is a limitation of the corpus, not a finding that"
                        " nothing is relevant"
                    ),
                    "ids": list(retrieval.not_evaluable),
                },
                "hits": [dict(hit) for hit in retrieval.hits],
            },
        }

    # -- the governing text ------------------------------------------------

    def _governing(self, estate: acquisition.Estate) -> Mapping[str, Any]:
        """Which text is in force at `as_of`, by `governs_from`.

        **Never by `filed_date`** (`CXR-G11`). An amendment is filed after it
        begins governing, and a product keyed on the filing date serves the old
        text for the gap between them.
        """
        as_of = estate.as_of.date()
        in_force = {
            document_id: governs.isoformat()
            for document_id, governs in estate.governs_from.items()
            if governs <= as_of
        }
        return {
            "axis": "governs_from",
            "not_axis": "filed_date",
            "as_of": as_of.isoformat(),
            "documents_in_force": len(in_force),
            "documents_not_yet_governing": len(estate.governs_from) - len(in_force),
        }

    # -- one source --------------------------------------------------------

    def _source(
        self, estate: acquisition.Estate, source: acquisition.EvidenceSource
    ) -> Mapping[str, Any]:
        return {
            "source_uri": source.uri,
            "covenant_type": source.covenant_type,
            "threshold": source.threshold,
            "document_id": source.document_id,
            "chain": [self._node(node) for node in source.chain],
        }

    def _node(self, node: acquisition.ChainNode) -> Mapping[str, Any]:
        return {
            "uri": node.uri,
            "kind": node.kind,
            "depth": node.depth,
            # EVERY citation here has been re-hashed against the passage the
            # `ex:evidencedBy` edge named. There is no other constructor.
            "citations": [self._citation(c) for c in node.citations],
            # AND EVERY ABSENCE IS EXPLAINED. The payload never simply omits.
            "not_evidenced": [
                {"reason": u.reason, "note": u.note} for u in node.uncitable
            ],
            # What the node CLAIMS about its own anchors, reported as the
            # multi-valued sets they are and never collapsed into a pairing.
            "anchor_claims": {
                name: list(values) for name, values in node.anchor_claims.items()
            },
        }

    def _citation(self, citation: acquisition.Citation) -> Mapping[str, Any]:
        """One checked citation, carrying the SDK's own anchor type.

        `PassageAnchor` is `ccf.contracts.claims`' — the SDK fixes the
        anchoring obligation, the deployment names the vocabulary. The anchor
        rides the CLAIM here and never `ProductLineage`, which is exactly three
        fields (§B.1a, `CXR-G02`).
        """
        anchor = PassageAnchor(kind=ANCHOR_KIND, locator=citation.locator)
        return {
            "anchor": {"kind": anchor.kind, "locator": anchor.locator},
            "document_id": citation.document_id,
            "start_offset": citation.start_offset,
            "end_offset": citation.end_offset,
            "sha256": citation.sha256,
            "checked": True,
            "heading": citation.heading,
            "alignment": citation.alignment,
            "text": citation.text,
        }

    # -- the summary -------------------------------------------------------

    def _summary(self, sources: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        checked = 0
        reasons = {reason: 0 for reason in DEBT_REASONS}
        nodes = 0
        for source in sources:
            for node in source["chain"]:
                nodes += 1
                checked += len(node["citations"])
                for absence in node["not_evidenced"]:
                    reasons[absence["reason"]] += 1
        return {
            "chain_nodes": nodes,
            "checked_citations": checked,
            "not_evidenced": reasons,
            "not_evidenced_total": sum(reasons.values()),
            # THE CLOSED SET, served so a consumer reads it off the answer
            # rather than inferring it from the reasons this run happened to
            # produce.
            "debt_reason_vocabulary": list(DEBT_REASONS),
        }

    def _absent_legs(self) -> Mapping[str, Any]:
        """What this estate does not carry, reported ABSENT rather than empty.

        `ex:governedBy` is named by the vault's schema for this product and
        measures **0 assertions** here. The payload asserts no governing edge
        and substitutes no proxy for one (`CXR-G17`).
        """
        return {
            "governedBy": {
                "state": "absent",
                "note": (
                    "named as a relationship by this product's published schema"
                    " and measured at 0 assertions in this estate; no governing"
                    " edge is asserted and no proxy is substituted for one"
                ),
            }
        }


def measured_completeness(estate: acquisition.Estate) -> Decimal:
    """How many chain nodes carry at least one checked citation.

    A real measurement and the honest one for this product: a definition chain
    whose nodes cannot be evidenced is genuinely less complete, and on this
    estate that is most of them.
    """
    nodes = [node for source in estate.sources for node in source.chain]
    if not nodes:
        return Decimal("1.0000")
    evidenced = sum(1 for node in nodes if node.citations)
    return (Decimal(evidenced) / Decimal(len(nodes))).quantize(Decimal("0.0001"))


def measured_semantic_consistency(estate: acquisition.Estate) -> Decimal:
    """Whether every absence carries a reason from the closed set.

    An unexplained omission is the inconsistency this product is about: it
    makes *"we looked and could not evidence it"* indistinguishable from *"we
    did not look"*.
    """
    absences = [
        absence
        for source in estate.sources
        for node in source.chain
        for absence in node.uncitable
    ]
    if not absences:
        return Decimal("1.0000")
    explained = sum(1 for a in absences if a.reason in DEBT_REASONS and a.note)
    return (Decimal(explained) / Decimal(len(absences))).quantize(Decimal("0.0001"))
