"""The `SignalEnvelope` — L1's one normalization target.

Whitepaper §7.1 (Signal Layer) and §8.3 (integration patterns); DESIGN.md
§2A.2.1 fixes the schema per the D-IMPL-33 ruling: the whitepaper-enumerated
core (``source``, ``ingestion_timestamp``, ``observed_time``, ``raw_payload``)
plus ``tenant_id`` (INV-CH7-16 — no untenanted path), an SDK-assigned
``envelope_id`` anchoring the L axis (INV-CH7-14), an opaque
``source_metadata`` extension block, and ``extra=forbid`` throughout.

The payload stays opaque *by type*, which is what makes "L1 does not
interpret" a structural property rather than a coding convention: there is no
entity or relationship field on this contract for an over-eager adapter to
populate. Interpretation is L2's monopoly, and L2 is the only writer to L3.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import Field

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = ["SignalEnvelope", "SourceIdentity"]


class SourceIdentity(CCFContract):
    """Structured identity of the system a signal came from.

    INV-CH8-01: lineage records source **identity, not location**. A hostname,
    connection string, or bucket path would bind the fabric's history to a
    deployment topology and break the moment the estate migrates; a stable
    logical ``system_id`` does not. Where that id comes from is deployment
    configuration — the SDK never enumerates source systems.
    """

    system_id: str


class SignalEnvelope(CCFContract):
    """The canonical L1 event envelope; the L1→L2 handoff artifact.

    DESIGN.md §2A.2.1 (D-IMPL-33 schema ruling); whitepaper §7.1.

    Attributes:
        tenant_id: Tenant scope, required on every envelope. Single-tenant
            deployments are the degenerate one-fixed-tenant case, never a
            separate mode (D-IMPL-05).
        envelope_id: SDK-assigned identity. Lineage entries and the
            re-hydration recipe (D-IMPL-44) address signals by this id.
        source: Logical identity of the emitting system.
        ingestion_timestamp: When the fabric received the signal.
        observed_time: When the event occurred at the source, when the source
            can say. ``None`` means unknown — L2 reconciles against the
            bitemporal T axis rather than guessing a value here.
        raw_payload: The source record, opaque to L1. Its keys are the
            source's vocabulary, never the fabric's.
        source_metadata: Adapter-supplied extension block, also opaque.
    """

    tenant_id: str
    envelope_id: str
    source: SourceIdentity
    ingestion_timestamp: datetime
    observed_time: datetime | None = None
    raw_payload: Mapping[str, Any]
    source_metadata: Mapping[str, Any] = Field(default_factory=dict)
