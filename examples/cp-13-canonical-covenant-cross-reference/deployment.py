"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. This file names all of it and makes no fabric call the spine does not.

**Its boundaries are ruled** (`D-IMPL-315`, `D-IMPL-343`): vocabulary, source
access, the envelopes, the debt reading and the deployment half of ONE declared
product gate. No boot, no effective-request derivation, no ingest loop, no
binder, no record, no serve — those are the paved road's.

## The evidence is fabric state (`CP-SPEC-013C` §0.1)

The specimen handed its Π the whole acquisition result through a closure — the
sources with their chains and citations, the policy envelope that bounded the
retrieval, the governing register — and computed two debt factors off that
object. None of it was in the graph, so replay could not reconstruct the payload
from the snapshot. Here each admitted anchor node carries its chain
(``source_json``), the envelope (``envelope_json``), the governing register
(``governing_json``) and the declared seed as claims; the chain nodes and
citations are still ingested as their own entities for the traversal and the
lineage; Π and the debt reading read the governed view and nothing beside it.

## The entitlement principal is the perspective's role

The specimen took ``principal`` as a per-call argument on neither the request
nor the perspective. The ``corpus_entitlement`` register keys on the role names
the specimen passed (``credit-officer``, ``control-room``,
``relationship-manager``), so on the road the principal the acquisition checks
is ``context.perspective.role`` — the deployment's declared default at the door,
or the perspective a local caller states. Nothing names itself.

## The ingestion-order contract

Edges FIRST, attributed nodes LAST (`D-IMPL-316`): a claim carrying fewer
attributes at the same URI supersedes the richer one. The road ingests in the
order this module returns.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

import acquisition
import projection
from ccf.products.contract import ContextProductContract
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.halflife.assessment import DebtAssessment
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: The request parameters this deployment reads by name — `CP-SPEC-013C` §B.2.
COVENANT_SOURCES = "covenant_sources"
CORPUS_SCOPE = "corpus_scope"
RESOLVE_DEPTH = "resolve_depth"

#: The three sources `ccf_environment.yaml` declares, by the names it declares.
SOURCE_RELATIONAL = "covenant_relational"
SOURCE_GRAPH = "covenant_graph"
SOURCE_DOCUMENTS = "covenant_documents"

SYSTEM = "covenant_cross_reference"
PLAN_ID_PREFIX = "cp-13-canonical.covenant-cross-reference"

MATCH_KEY: Mapping[str, str] = {
    "anchor": "anchor_node",
    "node": "chain_node",
    "citation": "citation_node",
}
ENDPOINT_RULES: Mapping[str, tuple[str, str]] = {
    "definesVia": ("anchor_subject", "node_object"),
}


def config() -> Mapping[str, Any]:
    """The single deployment document, parsed — read only for the plan-id convention."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return document


def plan_id(subject: str) -> str:
    return f"{PLAN_ID_PREFIX}/{subject}"


# ---------------------------------------------------------------------------
# acquire — read the three legs at the EFFECTIVE parameters; hand back claims.
# ---------------------------------------------------------------------------


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Read the three sources for the evidence nodes the effective request names.

    ``corpus_scope`` and ``resolve_depth`` are the EFFECTIVE values — the class
    defaults where the caller omitted them — handed here by the road
    (`D-IMPL-343` R-4). The entitlement principal is the perspective's role.
    An unknown covenant source and an unentitled scope RAISE here, exactly as
    the specimen's acquisition raises them (`CXRC-G10`, `CXRC-G14`): the
    walk's own contract, unchanged by the road.
    """
    effective = context.request.parameters
    estate = acquisition.acquire(
        source_uris=list(effective[COVENANT_SOURCES]),
        asked_at=context.request.asked_at,
        principal=context.perspective.role,
        corpus_scope=str(effective[CORPUS_SCOPE]),
        resolve_depth=int(effective[RESOLVE_DEPTH]),
        relational_settings=context.sources[SOURCE_RELATIONAL],
        graph_settings=context.sources[SOURCE_GRAPH],
        document_settings=context.sources[SOURCE_DOCUMENTS],
    )
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant)


def evidence_sources(*, limit: int | None, graph_settings: Mapping[str, str]) -> list[str]:
    """The demonstration's default evidence nodes, chosen off the ledger (run.py's helper)."""
    return acquisition.evidence_sources(limit=limit, graph_settings=graph_settings)


# ---------------------------------------------------------------------------
# From a read to fabric state — one envelope per dated claim.
# ---------------------------------------------------------------------------


def _node(
    *, tenant_id: str, at: datetime, uri: str, source_uri: str, kind: str,
    label: str, body: Mapping[str, Any], observed_time: datetime | None,
    promoted: Mapping[str, str] | None = None,
) -> SignalEnvelope:
    """One node's attributes. ATTRIBUTED, therefore ingested LAST."""
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=observed_time,
        raw_payload={
            MATCH_KEY[kind]: uri,
            "entity_uri": uri,
            "source_uri": source_uri,
            "node_kind": kind,
            "label": label,
            "payload_json": json.dumps(body, sort_keys=True, default=str),
            **(promoted or {}),
        },
    )


def _edge(
    *, tenant_id: str, at: datetime, ordinal: int, subject: str, obj: str,
    predicate: str,
) -> SignalEnvelope:
    """One typed edge, carrying NO attributes. Must precede either endpoint's node."""
    subject_rule, object_rule = ENDPOINT_RULES[predicate]
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{predicate}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            subject_rule: subject, object_rule: obj,
            "subject_uri": subject, "object_uri": obj, "predicate": predicate,
        },
    )


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime,
) -> tuple[SignalEnvelope, ...]:
    """Every edge, then every node — one tuple, in the order the road ingests.

    The ANCHOR NODE CARRIES ITS EVIDENCE: its chain as the payload will serve it,
    the envelope and the governing register (identical on every anchor of one
    read — a claim per admitted source, so a source the policy operator does
    not admit carries nothing into the view), and the declared seed.
    """
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []
    envelope_json = json.dumps(projection.envelope_claim(estate), sort_keys=True, default=str)
    governing_json = json.dumps(projection.governing_claim(estate), sort_keys=True, default=str)
    for source in estate.sources:
        nodes.append(_node(
            tenant_id=tenant_id, at=at, uri=source.uri, source_uri=source.uri,
            kind="anchor", label=source.covenant_type or "anchor",
            body={
                "covenant_type": source.covenant_type,
                "threshold": source.threshold,
                "document_id": source.document_id,
            },
            observed_time=None,
            promoted={
                "covenant_type": source.covenant_type or "unknown",
                "source_json": json.dumps(projection.source_claim(estate, source), sort_keys=True, default=str),
                "envelope_json": envelope_json,
                "governing_json": governing_json,
                "seeded_on": estate.seeded_on,
            },
        ))
        for member in source.chain:
            if member.uri != source.uri:
                edges.append(_edge(
                    tenant_id=tenant_id, at=at, ordinal=len(edges),
                    subject=source.uri, obj=member.uri, predicate="definesVia",
                ))
                nodes.append(_node(
                    tenant_id=tenant_id, at=at, uri=member.uri,
                    source_uri=source.uri, kind="node",
                    label=f"{member.kind} d{member.depth}",
                    body={
                        "kind": member.kind,
                        "depth": member.depth,
                        "not_evidenced": [u.reason for u in member.uncitable],
                    },
                    observed_time=None,
                    promoted={"node_kind": member.kind},
                ))
            for citation in member.citations:
                nodes.append(_node(
                    tenant_id=tenant_id, at=at,
                    uri=f"cxr_citation://{citation.passage_id}",
                    source_uri=source.uri, kind="citation",
                    label=citation.heading or citation.passage_id,
                    body={
                        "passage_id": citation.passage_id,
                        "document_id": citation.document_id,
                        "start_offset": citation.start_offset,
                        "end_offset": citation.end_offset,
                        "sha256": citation.sha256,
                    },
                    observed_time=None,
                    promoted={
                        "document_id": citation.document_id,
                        "sha256": citation.sha256,
                    },
                ))
    return (*edges, *nodes)


# ---------------------------------------------------------------------------
# assess — D_c over the governed view.
# ---------------------------------------------------------------------------


def assess(context: AssessmentContext) -> DebtAssessment:
    """`D_c` over the governed VIEW, by the SDK's own reference scorer.

    The same scorer the low road runs, handed the same two figures the
    specimen declared — except that here the two are READ OFF THE VIEW: `C` is
    the share of chain nodes carrying a checked citation and `S` the share of
    absences carrying a closed-vocabulary reason, both off the admitted
    anchors' own chains (`CXRC-G15`), so a source the caller may not read
    counts for nothing and replay re-derives both from the snapshot. `F` is the
    SDK's freshness scorer over the view's observations with the booted λ_c
    table; every class of this product decays `supersede-only` (`CP13-F-12`),
    so it reads 1 and the pin says who read it. The three scorer pins are the
    specimen's own (`D-IMPL-47`).
    """
    assert context.half_life is not None and context.profile is not None
    scorer = AssemblyDebtScorer(
        table=context.half_life,
        profile=context.profile,
        completeness=DeclaredFactor(value=projection.view_completeness(context.view)),
        semantic_consistency=DeclaredFactor(value=projection.view_semantic_consistency(context.view)),
    )
    return scorer(view=context.view, evidence=context.evidence)


# ---------------------------------------------------------------------------
# gate — the deployment half of `cp-13-canonical.citations-are-checked`.
# ---------------------------------------------------------------------------


def citation_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """What it refuses: a citation not marked checked, an absence with no
    reason, a retrieval whose bound is missing — and, on the road, a read that
    admitted no evidence node at all (the envelope cannot then be served)."""
    payload = candidate.payload
    if "cross_references" not in payload:
        return "the payload reports no cross-references"
    summary = payload.get("citation_summary") or {}
    if "checked_citations" not in summary:
        return "the payload reports no citation summary"
    for source in payload["cross_references"]:
        for node in source["chain"]:
            for citation in node["citations"]:
                if citation.get("checked") is not True:
                    return (
                        "a citation is served without `checked: true`; every"
                        " emitted citation is re-hashed against the passage"
                        " `ex:evidencedBy` named, or it is not emitted (CXRC-G07)"
                    )
                if not citation.get("sha256"):
                    return "a citation is served with no recorded sha256"
            for absence in node["not_evidenced"]:
                if absence.get("reason") not in projection.DEBT_REASONS:
                    return (
                        f"an absence carries reason {absence.get('reason')!r},"
                        " outside the closed vocabulary (CXRC-G08)"
                    )
    retrieval = (payload.get("envelope") or {}).get("retrieval") or {}
    if retrieval.get("bound_applied") != "before-ranking":
        return (
            "the retrieval does not declare that its bound was applied before"
            " ranking, or no evidence node was admitted to carry it (CXRC-G09)"
        )
    if "classification" not in (retrieval.get("query_filter") or {}):
        return (
            "the retrieval's query filter carries no classification bound;"
            " a post-filter has already scored impermissible documents (CXRC-G09)"
        )
    return None
