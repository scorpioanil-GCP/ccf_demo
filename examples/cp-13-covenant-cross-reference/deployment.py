"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

Its boundaries are ruled (`D-IMPL-315`): vocabulary, source access, admission,
and the deployment half of ONE declared product gate. No binder, no universal
gates, no replay record, no serve.

## The ingestion-order contract

Edge envelopes carry two endpoint references and **no attributes**; node
envelopes carry one node's attributes. **Edges are ingested FIRST and nodes
LAST.** A claim carrying fewer attributes at the same URI *supersedes* the
richer one rather than merging.

## A citation is its own entity, and that is the rung's structural decision

`cxr_citation` is separate from `cxr_node`. A node can carry two checked
citations without either becoming a property of the other — which is exactly
the shape the upstream URI collision violated, when two covenants were merged
onto one identity and their anchors became indistinguishable (`CP13-F-01`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
import projection
from ccf.controlplane.artifacts import PerspectiveArtifact
from ccf.deployment import BootedFabric
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: Parameters this deployment reads by name. `subject`, `intent`, `freshness`
#: and `asked_at` are NOT here — they are `ProductRequest` FIELDS (`CXR-G05`).
COVENANT_SOURCES = "covenant_sources"
CORPUS_SCOPE = "corpus_scope"
RESOLVE_DEPTH = "resolve_depth"

SYSTEM = "covenant_cross_reference"

MATCH_KEY: Mapping[str, str] = {
    "anchor": "anchor_node",
    "node": "chain_node",
    "citation": "citation_node",
}

ENDPOINT_RULES: Mapping[str, tuple[str, str]] = {
    "definesVia": ("anchor_subject", "node_object"),
}


def config() -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return document


def connection(*, root: Path) -> Mapping[str, str]:
    """Where the FABRIC's own L3 lives for this run. Never a source store."""
    profile = yaml.safe_load(
        (HERE / "backends.yaml").read_text(encoding="utf-8")
    )["declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {"database_path": str(root / f"{profile['prefix']}{profile['suffix']}")}


def request(
    *, sources: Sequence[str], asked_at: datetime, scope: str | None = None,
    intent: str = "compliance-test", freshness: str = "amendment-driven",
    corpus_scope: str | None = None, resolve_depth: int | None = None,
    debt_tolerance: Decimal | str | None = None,
) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    The four §6.3 axes are FIELDS (`CXR-G05`). ``asked_at`` arrives from the
    CALLER; nothing here reads a clock (`D-IMPL-98`).
    """
    declared = config()["product_class"]
    defaults = config()["request_contract"]["defaults"]
    ordered = sorted(dict.fromkeys(sources))
    if not ordered:
        raise ValueError("a cross-reference needs at least one evidence node")
    if len(ordered) == 1:
        subject = ordered[0]
    elif scope:
        subject = scope
    else:
        raise ValueError(
            "a multi-source request must name its `scope`; the subject rides"
            " the content address, and promoting one of many sources to stand"
            " for the set would answer under a subject nobody asked about"
        )
    parameters: dict[str, Any] = {
        COVENANT_SOURCES: ordered,
        # CARRIED EXPLICITLY EVEN WHEN DEFAULTED. The envelope changes which
        # documents exist for this request, so a consumer must be able to read
        # which envelope was in force off the request itself.
        CORPUS_SCOPE: corpus_scope or defaults[CORPUS_SCOPE],
        RESOLVE_DEPTH: int(
            defaults[RESOLVE_DEPTH] if resolve_depth is None else resolve_depth
        ),
    }
    if debt_tolerance is not None:
        # A `Decimal`, never a float: this rides the content address.
        parameters["debt_tolerance"] = Decimal(str(debt_tolerance))
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=subject, intent=intent, freshness=freshness,
        asked_at=asked_at, parameters=parameters,
    )


def perspective(*, role: str | None = None) -> PerspectiveArtifact:
    declared = dict(config()["default_perspective"])
    if role:
        declared["role"] = role
    return PerspectiveArtifact(semver="1.0.0", **declared)


def acquire_for(asked: ProductRequest, *, principal: str) -> acquisition.Estate:
    defaults = config()["request_contract"]["defaults"]
    return acquisition.acquire(
        source_uris=list(asked.parameters[COVENANT_SOURCES]),
        asked_at=asked.asked_at,
        principal=principal,
        corpus_scope=str(asked.parameters.get(CORPUS_SCOPE, defaults[CORPUS_SCOPE])),
        resolve_depth=int(asked.parameters.get(RESOLVE_DEPTH, defaults[RESOLVE_DEPTH])),
    )


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
    """One typed edge, carrying NO attributes.

    .. warning::

       **Must reach L2 BEFORE either endpoint's node envelope.**
    """
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
) -> tuple[list[SignalEnvelope], list[SignalEnvelope]]:
    """``(edges, nodes)`` for one estate read, in the order they must be written."""
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

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
            promoted={"covenant_type": source.covenant_type or "unknown"},
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
                    # THE SERIES KEY, promoted onto the claim (`CXR-G23`).
                    promoted={"node_kind": member.kind},
                ))
            for citation in member.citations:
                # A CITATION IS ITS OWN ENTITY. Two on one node stay two.
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
    return edges, nodes


def ingest(booted: BootedFabric, estate: acquisition.Estate, *, at: datetime) -> None:
    """Write the estate into L3 through the ONE write handle, in order."""
    edges, nodes = envelopes(estate, tenant_id=booted.tenant_id, at=at)
    worker = booted.handle.worker
    for envelope in edges:
        worker.ingest(envelope)
    for envelope in nodes:
        worker.ingest(envelope)


def build_citation_gate(*, asked: ProductRequest) -> Any:
    """The DEPLOYMENT half of the declared product gate (`CXR-G07`).

    **What it refuses: a citation that is not marked checked, an absence with
    no reason, and a retrieval whose bound is missing.** Those are the three
    ways this product could serve something it has not earned.
    """
    del asked

    def gate(
        *, candidate: ContextProductContract, evidence: object = None
    ) -> str | None:
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
                            " `ex:evidencedBy` named, or it is not emitted"
                            " (CXR-G07)"
                        )
                    if not citation.get("sha256"):
                        return "a citation is served with no recorded sha256"
                for absence in node["not_evidenced"]:
                    if absence.get("reason") not in projection.DEBT_REASONS:
                        return (
                            f"an absence carries reason {absence.get('reason')!r},"
                            " outside the closed vocabulary; an unexplained"
                            " omission makes 'we could not evidence this'"
                            " indistinguishable from 'we did not look'"
                            " (CXR-G08)"
                        )
        retrieval = (payload.get("envelope") or {}).get("retrieval") or {}
        if retrieval.get("bound_applied") != "before-ranking":
            return (
                "the retrieval does not declare that its bound was applied"
                " before ranking (CXR-G09)"
            )
        if "classification" not in (retrieval.get("query_filter") or {}):
            return (
                "the retrieval's query filter carries no classification bound;"
                " a post-filter has already scored impermissible documents and"
                " that computation is itself the leak (CXR-G09)"
            )
        return None

    return gate


@dataclass(frozen=True)
class CrossReferenceScenario:
    """What one run needs — satisfies ``produce.Scenario`` structurally."""

    estate: acquisition.Estate
    asked: ProductRequest

    @property
    def product_class_key(self) -> str:
        return "product_class"

    @property
    def request_contract_key(self) -> str:
        return "request_contract"

    @property
    def operator_parameter_keys(self) -> tuple[str, ...]:
        return tuple(config()["product_class"]["required_operator_keys"])

    @property
    def policy_bundle_key(self) -> str:
        return "policy"

    @property
    def plan_id(self) -> str:
        return f"cp-13.covenant-cross-reference/{self.asked.subject}"

    @property
    def declared(self) -> Mapping[str, Any]:
        return {
            "estate": self.estate,
            "resolve_depth": self.asked.parameters[RESOLVE_DEPTH],
        }

    @property
    def max_ttl_seconds(self) -> int:
        return 1209600

    @property
    def product_ttl_seconds(self) -> int:
        # 7 days (§B.1).
        return 604800
