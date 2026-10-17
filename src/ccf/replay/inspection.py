# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""What a retained decision says about itself — the "why" behind the replay front-end (`D-IMPL-383`).

SDK-defined extension (CLAUDE.md §8.3 "replay queries"); whitepaper §7.10.1 is
unchanged by it. :func:`explain_decision` reads ONE decision record from the
store, at its exact content address, and lifts out what an auditor asks of it:
why a refusal refused, which policy versions and request inputs were in force
(and who supplied each input), and which graph snapshot it read, as of when.

Nothing here re-derives anything. Every value is copied from the record — the
refusal sentence is the refusal envelope's own ``detail``, written when the
decision was made — so the explanation is exactly as trustworthy as the record,
and is checkable against it. It needs no retained graph: a decision whose graph
is gone can still be explained, though it can no longer be replayed.

**An operator/auditor handle**, as
:meth:`~ccf.products.product.OpenedProduct.record_of` is. The refusal detail
read here is the internal one; a caller at a minimal disclosure level was shown
less. Whoever can run this holds the product's store.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import JsonValue

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.replay.evidence import ReplayEvidenceIndex, ReplayEvidenceUnavailable, require_record_address
from ccf.replay.record import (
    NO_ASSEMBLY_REFUSAL,
    NO_FABRIC_READ,
    NO_REQUEST_RESOLUTION,
    DecisionReplayRecord,
)

__ccf_mode__ = "algorithmic"

__all__ = ["DecisionExplanation", "ParameterOrigin", "PolicyVersion", "explain_decision"]


class PolicyVersion(CCFContract):
    """One Control Plane binding in force, by key and pinned version (dimension 2)."""

    key: str
    version: str


class ParameterOrigin(CCFContract):
    """One request input as the decision resolved it, and who supplied it.

    Attributes:
        authority: ``caller`` when the request supplied the value; otherwise
            where the value came from (``default`` — the request contract's).
        source: The artifact (or the request) the value was read from.
        source_version: That artifact's pinned version; ``None`` for the request.
    """

    name: str
    value: JsonValue
    authority: str
    source: str
    source_version: str | None


class DecisionExplanation(CCFContract):
    """A decision, as its own record states it.

    Attributes:
        refusal_kind / refusal_reason / refusal_detail: The refusal envelope's
            kind, reason code and full sentence; all ``None`` when served.
        read_graph: Whether the decision read a graph at all. A refusal reached
            before any graph read none, and every snapshot field is ``None``.
        as_of: The temporal boundary the graph was read at.
        entities_touched / relationships_touched: How many graph entities and
            relationships the decision read.
        debt_signal / debt: The Context Debt gate's signal and value, when one
            was computed.
    """

    record_address: str
    outcome: Literal["served", "refused"]
    product_class: str
    product_version: str
    subject: str
    asked_at: datetime
    decided_at: datetime
    principal_id: str
    role: str
    refusal_kind: str | None
    refusal_reason: str | None
    refusal_detail: str | None
    policies: tuple[PolicyVersion, ...]
    parameters: tuple[ParameterOrigin, ...]
    read_graph: bool
    graph_snapshot_id: str | None
    as_of: datetime | None
    entities_touched: int | None
    relationships_touched: int | None
    operators: tuple[str, ...]
    debt_signal: str | None
    debt: str | None


def explain_decision(
    *, store: ArtifactStoreProtocol, evidence: ReplayEvidenceIndex, record_address: str
) -> DecisionExplanation:
    """Explain the decision recorded at ``record_address``, from its record alone.

    Raises:
        ValueError: ``record_address`` is not a content address.
        ccf.replay.evidence.ReplayEvidenceUnavailable: the evidence index holds
            no mapping for the address (not this tenant's, unknown, or
            interrupted), or the store no longer holds the record.
    """
    require_record_address(record_address)
    entry = evidence.entry(record_address)
    if entry is None:
        raise ReplayEvidenceUnavailable(
            record_address=record_address, detail="this evidence root holds no decision at that address"
        )
    if not store.exists(content_address=record_address):
        raise ReplayEvidenceUnavailable(
            record_address=record_address,
            detail="the evidence mapping names this decision, and the store no longer holds its record",
        )
    record = DecisionReplayRecord.model_validate_json(store.get(content_address=record_address))
    snapshot = record.context_fabric_snapshot
    path = record.content_generation_path
    refusal = _canonical(path.assembly_refusal, absent=NO_ASSEMBLY_REFUSAL)
    resolution = _canonical(record.policy_bindings.request_resolution, absent=NO_REQUEST_RESOLUTION)
    read_graph = path.plan_id != NO_FABRIC_READ
    return DecisionExplanation(
        record_address=record_address,
        outcome=entry.outcome,
        product_class=entry.product_class,
        product_version=entry.product_version,
        subject=entry.subject,
        asked_at=entry.asked_at,
        decided_at=entry.decided_at,
        principal_id=record.perspective_conditioning.principal_id,
        role=record.perspective_conditioning.role,
        refusal_kind=None if refusal is None else refusal.get("kind"),
        refusal_reason=entry.refusal_reason,
        refusal_detail=None if refusal is None else refusal.get("detail"),
        policies=tuple(PolicyVersion(key=b.key, version=b.version) for b in record.policy_bindings.bindings),
        parameters=tuple(_parameter(p) for p in (resolution or {}).get("parameters", ())),
        read_graph=read_graph,
        graph_snapshot_id=snapshot.graph_snapshot_id if read_graph else None,
        as_of=snapshot.temporal_boundary if read_graph else None,
        entities_touched=len(snapshot.touched_entities) if read_graph else None,
        relationships_touched=len(snapshot.touched_relationships) if read_graph else None,
        operators=tuple(path.operator_plan),
        debt_signal=None if path.debt is None else str(path.debt.signal),
        debt=None if path.debt is None else str(path.debt.debt),
    )


def _canonical(block: str, *, absent: str) -> dict[str, Any] | None:
    """A record block stored as canonical JSON text, or ``None`` at its stated-absent sentinel."""
    if block == absent:
        return None
    parsed = json.loads(block)
    if not isinstance(parsed, dict):
        raise ValueError(f"a recorded block is not a JSON object: {block[:80]!r}")
    return parsed


def _parameter(resolved: dict[str, Any]) -> ParameterOrigin:
    source = resolved.get("source") or {}
    return ParameterOrigin(
        name=resolved["name"],
        value=resolved.get("value"),
        authority=resolved["authority"],
        source=str(source.get("identity")),
        source_version=source.get("version"),
    )
