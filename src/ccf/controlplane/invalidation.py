"""Serve-time dependency invalidation — the register and the sink (``D-IMPL-334``).

**Not an event bus, and not a cascade.** Dave's terminology, 2026-09-12, and the
precision matters because the wrong word would license the wrong build:

    A graph supersession records an **invalidation boundary**. Any previously
    derived product whose snapshot predates that boundary and touched that
    entity becomes **ineligible for future serving**.

That is the whole mechanism. There is no subscriber registry, no notification,
no background worker and no product cache — because the SDK stores no Context
Product to evict (``ccf.replay.serve.DeliveryCapability.deliver`` hands it to
the caller), and therefore **eligibility is a predicate rather than a storage
problem**. The fabric already refuses at serve time on TTL, on debt, on
attestation and on a declared product gate; this adds one more question to that
sequence.

What it can and cannot do
-------------------------
It refuses to **re-serve** a product whose evidence has moved. **It cannot reach
a product a consumer already holds**, and no SDK can — a consumer's memory is
not the fabric's to reach into. `CP-SPEC-011`'s ``EWS-G22`` exists to stop a
product claiming otherwise, and this module's docstring says the same thing at
the mechanism rather than at the example.

A2A is out of scope for v1 (Dave, 2026-09-12): an inbound peer product carries
its own lineage and snapshot, and whether a local boundary may rule on it is a
question this module does not answer.

Why the Control Plane registry
------------------------------
Dave's ruling: the registry, not the ArtifactStore. Eligibility state is audit
state — every append is an audited Control Plane action under an author-visible
version, which is what makes *"why was this refused"* answerable from the record
rather than from a log. The ArtifactStore deliberately offers no delete, and
nothing here needs one: **the register only ever grows, and a boundary only ever
moves forward.**

Algorithmic module (CINV-03). Nothing here reads a clock, calls a model or holds
a graph handle: the boundary instant arrives from the write that caused it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import Field

from ccf.authz.capability import Authorized, CompositionRegister, Register, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
# `artifact_base`, NOT `artifacts`: the latter imports `ccf.products.contract`,
# and `ccf.products.gates` imports this module — so resolving these two names
# through `artifacts` closes an import cycle. `ccf.controlplane.registry`
# reaches for the same lower module for the same reason.
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol

#: The class segment of the Control Plane key a tenant's register lives
#: under. One register per tenant, because eligibility is tenant-scoped and a
#: shared key would let one tenant's supersession refuse another tenant's
#: product. **The tenant is the key's FIRST segment** (``{tenant}/{class}``):
#: the registry's one tenant comparison (``D-IMPL-353`` §1.3,
#: :class:`~ccf.controlplane.registry.CrossTenantKeyRefused`) reads the text
#: before the first ``/`` as the key's tenant, so a class-first key could be
#: registered only by a capability whose tenant was the class name — a lie on
#: the capability. The grammar moved to tenant-first for that reason; the
#: name of the constant is kept because every reader of this module knows it.
KEY_PREFIX = "ccf.entity-invalidation"

#: The register's own lane. Stated rather than defaulted, because
#: :class:`~ccf.controlplane.artifacts.VersionedArtifact` gives ``semver`` no
#: default on purpose — an artifact declares which lane it is in.
REGISTER_SEMVER = "1.0.0"


def register_key(tenant_id: str) -> str:
    """The Control Plane key holding ``tenant_id``'s invalidation register: ``{tenant}/ccf.entity-invalidation``."""
    return f"{tenant_id}/{KEY_PREFIX}"


class InvalidationUnauthorized(PermissionError):
    """The sink holds no ``Register`` capability for the tenant a supersession names (D-IMPL-353 §1.6; D-IMPL-354).

    A :class:`ControlPlaneInvalidationSink` records boundaries only for the
    tenants its composition root minted a capability for — one capability,
    one key, one tenant, handed to it at construction. A supersession under
    any other tenant is not written under a fallback and not skipped: it is
    refused here, before the standing register is even read, because a
    fabric that was not composed for a tenant has no authority to move that
    tenant's boundary. Raised, never returned — this is wiring (the fabric's
    ``tenant_ids`` omit a tenant its claims carry), not a governance outcome.
    """


class EntityInvalidation(CCFContract):
    """One entity's invalidation boundary, and what moved it.

    Args:
        entity_uri: The entity whose effective context changed.
        invalidated_from: The instant from which a product built on older state
            is ineligible. **The superseding observation's own instant**, not
            the instant the fabric performed the write — a boundary derived
            from wall-clock ingestion would refuse products that were correct
            as of the evidence they actually read (``D-IMPL-332``'s reasoning,
            arriving at delivery).
        reason: Why the boundary moved, in the mechanism's own vocabulary.
        source: The claim identity that superseded — what a reader follows to
            see the change itself.
    """

    entity_uri: str
    invalidated_from: datetime
    reason: str
    source: str


class EntityInvalidationRegister(VersionedArtifact):
    """One tenant's entity invalidation boundaries.

    The same shape as :class:`~ccf.controlplane.artifacts.HalfLifeTable` — a
    whole table registered as one artifact, re-registered as a new immutable
    version on each append. One row per **entity**, never one per event: the
    boundary is the latest instant at which that entity's effective context
    changed, and an earlier boundary can refuse nothing a later one does not.

    **Append-only in the sense that matters.** No row is ever removed, a
    boundary only ever advances, and every append is a distinct audited
    registry version — so the full history of appends is recoverable from the
    version chain even though a single version holds only the current
    boundaries.
    """

    tenant_id: str
    #: **NOT hash-transparent, and the reason is that this contract is NEW.**
    #: Hash transparency exists so a field ADDED to an existing contract leaves
    #: yesterday's artifacts byte-identical — *silence equals yesterday*
    #: (``D-IMPL-243``). There is no yesterday here: nothing was ever written
    #: under this class before it existed. So every field participates in
    #: identity, and a register holding one boundary is a different artifact
    #: from an empty one, which is exactly what an auditor needs it to be.
    entries: tuple[EntityInvalidation, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )

    def boundary_for(self, entity_uri: str) -> datetime | None:
        """The invalidation boundary for ``entity_uri``, or ``None``.

        ``None`` is the honest answer for an entity nothing has superseded, and
        it is the answer for every entity before this mechanism existed — which
        is what makes the gate additive.
        """
        for entry in self.entries:
            if entry.entity_uri == entity_uri:
                return entry.invalidated_from
        return None

    def entry_for(self, entity_uri: str) -> EntityInvalidation | None:
        """The whole entry, for a refusal that must name its cause."""
        for entry in self.entries:
            if entry.entity_uri == entity_uri:
                return entry
        return None

    def with_boundary(
        self, invalidation: EntityInvalidation
    ) -> "EntityInvalidationRegister":
        """This register plus ``invalidation``, as a new value.

        **A boundary never moves backward.** A late-arriving write whose
        observation predates the standing boundary leaves it alone: the later
        change already invalidates everything the earlier one would have, and
        moving the boundary back would make a product eligible again that a
        subsequent change had ruled out. This mirrors ``_restitch_chain``'s own
        posture, where a claim observed before the current one slots into
        history rather than displacing it.
        """
        kept: list[EntityInvalidation] = []
        replaced = False
        for entry in self.entries:
            if entry.entity_uri != invalidation.entity_uri:
                kept.append(entry)
                continue
            replaced = True
            kept.append(
                invalidation
                if invalidation.invalidated_from > entry.invalidated_from
                else entry
            )
        if not replaced:
            kept.append(invalidation)
        return EntityInvalidationRegister(
            semver=self.semver,
            tenant_id=self.tenant_id,
            entries=tuple(sorted(kept, key=lambda e: e.entity_uri)),
        )


#: The registered class. Named for what it holds rather than for the event that
#: fills it, because the register is what the gate reads.
ENTITY_INVALIDATION_REGISTER = ArtifactClass(
    class_id="ccf.entity-invalidation-register",
    contract=EntityInvalidationRegister,
)


@runtime_checkable
class InvalidationSink(Protocol):
    """Where the single writer reports that an entity's context moved.

    A Protocol rather than a concrete type, on CLAUDE.md §11's terms, and with
    one shipped reference implementation below. The writer holds this and
    nothing else of the Control Plane — it reports a boundary; it does not
    resolve, version or read one.
    """

    def record(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        invalidated_from: datetime,
        reason: str,
        source: str,
    ) -> None:
        """Record that ``entity_uri``'s effective context changed."""
        ...


class ControlPlaneInvalidationSink:
    """The reference :class:`InvalidationSink`, backed by the registry.

    Appends synchronously inside the writer's own call (Dave, 2026-09-12:
    *"The guarantee must not depend on a deployment remembering to publish an
    event"*). Synchronous is also what keeps the single-writer model intact —
    nothing else acquires a handle, and no second process observes the write.
    """

    def __init__(
        self,
        *,
        registry: ControlPlaneProtocol,
        authorities: tuple[Authorized[CompositionRegister], ...],
    ) -> None:
        """Hold one ``Register`` capability per tenant this sink may record for.

        **Not a composition root** (D-IMPL-354): the sink mints nothing. Its
        composer — :func:`ccf.boot.boot` — mints ``Register`` for
        :func:`register_key` of each tenant it composes the fabric for and
        hands the capabilities here. Each is verified at construction, by the
        seam's own :func:`~ccf.authz.capability.verify`, against exactly the
        key it must open, so a capability for another key, another kind, or
        no mint at all is refused before the sink exists.

        Raises:
            ccf.authz.capability.CapabilityBypassError: a capability is
                fabricated, retargeted, not ``Register``, or not for its own
                tenant's register key.
            InvalidationUnauthorized: two capabilities name one tenant, or
                none was handed in — a sink for no tenant records nothing and
                is a misconfiguration, refused at composition rather than at
                the first supersession.
        """
        held: dict[str, Authorized[CompositionRegister]] = {}
        for authorized in authorities:
            tenant = getattr(authorized, "tenant", None)
            expected = register_key(tenant) if isinstance(tenant, str) and tenant else ""
            verify(authorized, kind=CompositionRegister, resource=expected)
            if authorized.tenant in held:
                raise InvalidationUnauthorized(
                    f"two Register capabilities were handed in for tenant"
                    f" {authorized.tenant!r}'s invalidation register; a"
                    " composition mints one per tenant (D-IMPL-354)"
                )
            held[authorized.tenant] = authorized
        if not held:
            raise InvalidationUnauthorized(
                "no Register capability was handed to the invalidation sink; a"
                " fabric is composed for at least one tenant, and a sink for no"
                " tenant could record no supersession (D-IMPL-354)"
            )
        self._registry = registry
        self._authorities = held

    @property
    def tenants(self) -> frozenset[str]:
        """The tenants this sink holds a capability for — the fabric's composed tenants."""
        return frozenset(self._authorities)

    def register(self, tenant_id: str) -> EntityInvalidationRegister | None:
        """This tenant's register at its latest version, or ``None``.

        ``None`` for a tenant nothing has superseded — which is every tenant
        before this mechanism ran, and is why the gate is additive.
        """
        return resolve_register(self._registry, tenant_id=tenant_id)

    def record(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        invalidated_from: datetime,
        reason: str,
        source: str,
    ) -> None:
        """Append one boundary, as a new audited register version.

        The capability is looked up FIRST — before the standing register is
        read — so a tenant this fabric was not composed for is refused with
        nothing read and nothing written.

        Raises:
            InvalidationUnauthorized: this sink holds no capability for
                ``tenant_id``.
        """
        authorized = self._authorities.get(tenant_id)
        if authorized is None:
            raise InvalidationUnauthorized(
                f"a supersession under tenant {tenant_id!r} reached the"
                " invalidation sink, and this fabric holds a Register"
                f" capability only for {sorted(self._authorities)!r}; the"
                " composition root mints one per tenant it composes for"
                " (`boot(..., tenant_ids=...)`), and a tenant it did not name"
                " cannot have its boundary moved (D-IMPL-353 §1.6; D-IMPL-354)"
            )
        standing = self.register(tenant_id) or EntityInvalidationRegister(
            semver=REGISTER_SEMVER, tenant_id=tenant_id
        )
        moved = standing.with_boundary(
            EntityInvalidation(
                entity_uri=entity_uri,
                invalidated_from=invalidated_from,
                reason=reason,
                source=source,
            )
        )
        if moved == standing:
            # THE BOUNDARY DID NOT MOVE, so nothing is registered. A version
            # per no-op write would fill the audit log with entries that
            # changed nothing, and an auditor counting versions would read
            # activity that never happened.
            return
        self._registry.register_typed(authorized, moved, ENTITY_INVALIDATION_REGISTER)


def resolve_register(
    registry: ControlPlaneProtocol, *, tenant_id: str
) -> EntityInvalidationRegister | None:
    """``tenant_id``'s register at its latest version, or ``None``.

    ``resolve_latest`` is the right resolution here and the docstring's
    *"replay paths must not use this method"* does not bite: eligibility is a
    question about **now**, not about the state a past decision was made under.
    A replay reproduces the product it recorded; it does not re-ask whether
    that product may be served today.
    """
    try:
        _, artifact = registry.resolve_latest(register_key(tenant_id))
    except ControlPlaneMissing:
        return None
    if not isinstance(artifact, EntityInvalidationRegister):
        raise TypeError(
            f"{register_key(tenant_id)!r} holds {type(artifact).__name__}, "
            "not EntityInvalidationRegister"
        )
    return artifact
