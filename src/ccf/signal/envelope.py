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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import Field

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "IngressTemporalBound",
    "SignalEnvelope",
    "SourceIdentity",
    "TemporalWriteRefused",
    "refuse_foreign_envelope",
]


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


class TemporalWriteRefused(ValueError):
    """An envelope may not be written: its instant is outside the declared window.

    `D-IMPL-358` step 8. Raised BEFORE L2's single writer sees the envelope, so no
    claim lands and nothing is restamped. A `ValueError`, matching this module's
    existing refusal idiom (:func:`refuse_foreign_envelope`) and the worker's own
    (`IdentityRefused`) rather than inventing a new failure family.

    Every field an operator needs to act is an ATTRIBUTE, not only prose: which
    tenant, which instant, which policy key was consulted, and why it refused. A
    refusal that only says "refused" cannot be acted on, and ruling 11 admits no
    default and no fabricated binding to fall back to.

    The instant is carried VERBATIM. It is not rounded, clamped or restamped — the
    refusal reports the instant it was handed, which is the one the caller supplied.
    """

    def __init__(
        self,
        *,
        envelope_id: str,
        tenant_id: str,
        instant: datetime,
        policy_key: str,
        reason: str,
        detail: str,
    ) -> None:
        self.envelope_id = envelope_id
        self.tenant_id = tenant_id
        self.instant = instant
        self.policy_key = policy_key
        self.reason = reason
        self.detail = detail
        super().__init__(
            f"envelope {envelope_id!r} for tenant {tenant_id!r} is stamped"
            f" {instant.isoformat()} and may not be written: {reason} —"
            f" {detail} (policy key {policy_key!r}; D-IMPL-358 step 8)"
        )


@dataclass(frozen=True)
class IngressTemporalBound:
    """The composition tenant roster, with each tenant's temporal policy PINNED.

    `D-IMPL-358` step 8. The tenant-bound temporal write guard, and it lives HERE —
    beside :func:`refuse_foreign_envelope`, the boundary check the paved road already
    runs on every envelope before L2 — rather than inside
    :class:`~ccf.assembly.worker.AssemblyWorker`. The worker stays tenant-free and
    clock-free: it acquires no clock and invents no tenant, which is `D-IMPL-159` and
    the single-writer discipline both left intact.

    **Composition state, bound once.** The roster and the pinned policies are fixed at
    boot. Nothing on the judging path consults the registry, so there is no
    ``resolve_latest`` per envelope — the same reason
    :class:`~ccf.assembly.worker.AssemblyWorker` resolves its policy-bundle pin once in
    its constructor rather than once per write.

    **The envelope's tenant is a CLAIM, never a selector.** A tenant absent from the
    roster is refused, in the same family as an envelope stamped for another tenant. A
    tenant present on it selects the policy that was pinned FOR IT at composition. No
    envelope can introduce a tenant, cause a resolution, or reach an unpinned policy.

    **The evaluation instant is handed in.** This class reads no clock.
    """

    pinned: Mapping[str, object]

    @classmethod
    def at_composition(
        cls, *, registry: object, tenant_ids: Sequence[str]
    ) -> "IngressTemporalBound":
        """Pin each roster tenant's temporal policy, once, at the composition root.

        An UNDECLARED policy is pinned as its own absence rather than raising here:
        composition succeeds and the refusal happens at the write, where it can name
        the envelope it refused. Failing at boot would take down a fabric whose other
        tenants are declared, and would report the fact without the thing it applies to.
        """
        from ccf.controlplane.temporal_boundary import resolve_temporal_boundary

        return cls(
            pinned={
                tenant_id: resolve_temporal_boundary(
                    registry=registry,  # type: ignore[arg-type]
                    tenant_id=tenant_id,
                )
                for tenant_id in tenant_ids
            }
        )

    def refuse_outside_window(
        self, envelope: "SignalEnvelope", *, now: datetime
    ) -> None:
        """Refuse ``envelope`` unless its ingestion instant is inside the window.

        ``now`` is supplied by the ingress caller — the same instant the door read
        once — for the reason `ingest_admitted` already states of its own parameter:
        *"a write path that read a clock would not replay."*

        Only ``ingestion_timestamp`` is judged. ``observed_time`` (which lands as a
        claim's ``valid_from``) is VALID time — how far back a fact may have been true
        — and is a different axis from the window in which the fabric may accept a
        write. Bounding it here would refuse legitimate back-dated valid-time.

        Raises:
            TemporalWriteRefused: the tenant is not on the composition roster, the
                tenant declared no temporal boundary, or the instant falls outside
                the declared window.
        """
        # Deferred: `ccf.products.product` imports this module, so a module-level
        # import of the products-side judgment would close a cycle. The arithmetic is
        # reused rather than restated — one authority for "outside the window".
        from ccf.controlplane.temporal_boundary import (
            PinnedTemporalBoundary,
            TemporalBoundaryUndeclared,
            temporal_boundary_policy_key,
        )
        from ccf.products.refusal import refuse_temporal_bound

        claimed = envelope.tenant_id
        instant = envelope.ingestion_timestamp
        if claimed not in self.pinned:
            raise TemporalWriteRefused(
                envelope_id=envelope.envelope_id,
                tenant_id=claimed,
                instant=instant,
                policy_key=temporal_boundary_policy_key(tenant_id=claimed),
                reason="tenant-not-on-the-composition-roster",
                detail=(
                    "this fabric was composed for"
                    f" {sorted(self.pinned)!r} and an envelope names its own tenant"
                    " rather than choosing one — a tenant absent from the roster is"
                    " refused, never adopted"
                ),
            )

        bound = self.pinned[claimed]
        assert isinstance(bound, PinnedTemporalBoundary | TemporalBoundaryUndeclared)
        refusal = refuse_temporal_bound(
            pinned=bound,
            served_at=now,
            asked_at=instant,
            decision_instant=instant,
        )
        if refusal is None:
            return
        raise TemporalWriteRefused(
            envelope_id=envelope.envelope_id,
            tenant_id=claimed,
            instant=instant,
            policy_key=(
                bound.key
                if isinstance(bound, PinnedTemporalBoundary | TemporalBoundaryUndeclared)
                else temporal_boundary_policy_key(tenant_id=claimed)
            ),
            reason=refusal.reason,
            detail=refusal.detail,
        )
