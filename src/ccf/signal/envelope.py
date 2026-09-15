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

__all__ = ["SignalEnvelope", "SourceIdentity", "refuse_foreign_envelope"]


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


def refuse_foreign_envelope(
    envelope: SignalEnvelope, *, tenant_id: str, asked_at: datetime
) -> None:
    """Refuse an envelope that is not this question's to ingest (`D-IMPL-343`).

    The boundary check the paved road's ingest loop runs on every envelope a
    deployment's ``acquire`` hands back, before L2's one writer sees it. Two
    refusals, each by name, and the rule behind the second is the one nothing
    on the public surface stated until `CP03C-F-08` measured its absence:

    * **tenant** — an envelope stamped for another tenant would enter this
      fabric's graph under this tenant's key space, which is the cross-tenant
      leak the single-writer discipline exists to keep structural.
    * **ingestion instant** — ``ingestion_timestamp`` must equal the instant
      the question is asked as of. L2 records a claim's ``observed_at`` as the
      moment the FABRIC learned it (`D-IMPL-331`; ``DECISIONS.md`` on
      *"observed_at = ingestion timestamp"*), and the question's ``asked_at``
      is the as-of boundary the view is read at. A claim ingested "after" the
      boundary is invisible to the view that answers the question, and one
      ingested "before" it lets the run's own reading of the source look older
      than the run. The canonical trees all stamp the request instant; this
      makes that a refused-if-not rather than a convention each copies. A
      source that must stamp its own ingestion instant is a long-lived fabric
      and composes on the low road, where no per-question boundary exists.

    Raises:
        ValueError: the envelope names another tenant, or is stamped for an
            instant other than ``asked_at``.
    """
    if envelope.tenant_id != tenant_id:
        raise ValueError(
            f"envelope {envelope.envelope_id!r} is stamped for tenant"
            f" {envelope.tenant_id!r} and this fabric runs as {tenant_id!r};"
            " a deployment's acquisition emits envelopes for its own tenant"
            " and no other (D-IMPL-343)"
        )
    if envelope.ingestion_timestamp != asked_at:
        raise ValueError(
            f"envelope {envelope.envelope_id!r} is stamped ingested at"
            f" {envelope.ingestion_timestamp.isoformat()!r} and the question is"
            f" asked as of {asked_at.isoformat()!r}; on the paved road the"
            " fabric learns every claim at the question's own instant, so the"
            " as-of view reads what the run acquired and a claim's own age is"
            " carried by `observed_time` (D-IMPL-343; D-IMPL-331, CP03C-F-08)"
        )
