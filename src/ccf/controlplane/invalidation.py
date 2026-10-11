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
nothing here needs one: **records are only ever added, and a boundary only ever
moves forward.**

One record per entity (``D-IMPL-382``)
--------------------------------------
Until 2026-10-11 a tenant's boundaries were one ``EntityInvalidationRegister``
artifact under one key, re-registered whole on every supersession and read whole
on every serve — linear in the number of entities per write and per read, so
quadratic over a tenant's life. Dave adopted Grok's ruling (option A, 07:32 MST):
**each entity's boundary is its own registry artifact**, an
:class:`EntityInvalidationRecord` under
``{tenant}/ccf.entity-invalidation/{sha256(entity_uri)}``. Consequences, stated
rather than discovered:

* **The whole-register content address disappears.** There is no single artifact
  whose hash names a tenant's invalidation state; each entity's record has its own
  address, and **each entity has its own version history** under its own key.
* A supersession reads and writes **one entity's** record; the serve gate reads
  **only the touched entities'** records. Neither processes unrelated entities.
* The tenant's full history is the set of its entity keys' version chains,
  reconstructed by :func:`invalidation_history`.
* The sink writes under :class:`~ccf.authz.capability.InvalidationRecordRegister`,
  which authorizes its own tenant's records of this one class and nothing else.

Algorithmic module (CINV-03). Nothing here reads a clock, calls a model or holds
a graph handle: the boundary instant arrives from the write that caused it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, cast, runtime_checkable

from ccf.authz.capability import Authorized, InvalidationRecordRegister, verify
from ccf.contracts.base import CCFContract

# `artifact_base`, NOT `artifacts`: the latter imports `ccf.products.contract`,
# and `ccf.products.gates` imports this module — so resolving these two names
# through `artifacts` closes an import cycle. `ccf.controlplane.registry`
# reaches for the same lower module for the same reason.
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.controlplane.registry import (
    INVALIDATION_RECORD_CLASS_ID,
    INVALIDATION_RECORD_PREFIX,
    ControlPlaneMissing,
    ControlPlaneProtocol,
    invalidation_record_key,
)

#: The class segment of a tenant's invalidation keys. **The tenant is the key's
#: FIRST segment** (``{tenant}/{class}/…``): the registry's one tenant comparison
#: (``D-IMPL-353`` §1.3) reads the text before the first ``/`` as the key's tenant.
#: The name is kept because every reader of this module knows it.
KEY_PREFIX = INVALIDATION_RECORD_PREFIX

#: A record's own lane. Stated rather than defaulted, because
#: :class:`~ccf.controlplane.artifacts.VersionedArtifact` gives ``semver`` no
#: default on purpose — an artifact declares which lane it is in.
RECORD_SEMVER = "1.0.0"


def register_key(tenant_id: str) -> str:
    """``tenant_id``'s invalidation prefix, ``{tenant}/ccf.entity-invalidation`` — the resource its capability is minted for.

    Since ``D-IMPL-382`` it names no artifact: the records live one level below it, one per entity
    (:func:`record_key`). The name is kept because the composition root and the sink address a
    tenant's invalidation authority by it.
    """
    return f"{tenant_id}/{KEY_PREFIX}"


def record_key(tenant_id: str, entity_uri: str) -> str:
    """The key of ``tenant_id``'s invalidation record for ``entity_uri``."""
    return invalidation_record_key(tenant_id=tenant_id, entity_uri=entity_uri)


class InvalidationUnauthorized(PermissionError):
    """The sink holds no capability for the tenant a supersession names (D-IMPL-353 §1.6; D-IMPL-354; D-IMPL-382).

    A :class:`ControlPlaneInvalidationSink` records boundaries only for the tenants its
    composition root minted a capability for — one capability per tenant, for that tenant's
    invalidation records only. A supersession under any other tenant is not written under a
    fallback and not skipped: it is refused here, before anything is read, because a fabric that
    was not composed for a tenant has no authority to move that tenant's boundary. Raised, never
    returned — this is wiring, not a governance outcome.
    """


class EntityInvalidationRecord(VersionedArtifact):
    """One tenant's invalidation boundary for one entity, and what moved it (``D-IMPL-382``).

    Each record is its own registry artifact under :func:`record_key`; a boundary that advances
    is a new version of the same key, so **each entity has its own version history**.

    Args:
        tenant_id: The tenant whose eligibility state this is. Every field participates in
            identity: nothing was ever written under this class before it existed, so there is no
            yesterday for hash transparency to preserve (``D-IMPL-243``).
        entity_uri: The entity whose effective context changed.
        invalidated_from: The instant from which a product built on older state is ineligible.
            **The superseding observation's own instant**, not the instant the fabric performed
            the write (``D-IMPL-332``'s reasoning, arriving at delivery).
        reason: Why the boundary moved, in the mechanism's own vocabulary.
        source: The claim identity that superseded — what a reader follows to see the change.
    """

    tenant_id: str
    entity_uri: str
    invalidated_from: datetime
    reason: str
    source: str

    def advanced_by(self, later: "EntityInvalidationRecord") -> bool:
        """Whether ``later`` moves this boundary. **A boundary never moves backward.**

        Only a strictly later instant moves it. A late-arriving write whose observation predates
        or equals the standing boundary leaves it alone: the later change already invalidates
        everything the earlier one would have, and moving the boundary back would make a product
        eligible again that a subsequent change had ruled out (``_restitch_chain``'s own posture).
        """
        return later.invalidated_from > self.invalidated_from


#: The registered class. Its id is the one the invalidation-record capability may write.
ENTITY_INVALIDATION_RECORD = ArtifactClass(
    class_id=INVALIDATION_RECORD_CLASS_ID,
    contract=EntityInvalidationRecord,
)


@runtime_checkable
class InvalidationSink(Protocol):
    """Where the single writer reports that an entity's context moved.

    A Protocol rather than a concrete type, on CLAUDE.md §11's terms, and with one shipped
    reference implementation below. The writer holds this and nothing else of the Control Plane —
    it reports a boundary; it does not resolve, version or read one.
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

    Appends synchronously inside the writer's own call (Dave, 2026-09-12: *"The guarantee must
    not depend on a deployment remembering to publish an event"*). Synchronous is also what keeps
    the single-writer model intact — nothing else acquires a handle.
    """

    def __init__(
        self,
        *,
        registry: ControlPlaneProtocol,
        authorities: tuple[Authorized[InvalidationRecordRegister], ...],
    ) -> None:
        """Hold one invalidation-record capability per tenant this sink may record for.

        **Not a composition root** (D-IMPL-354): the sink mints nothing. Its composer —
        :func:`ccf.boot.boot` — mints :class:`~ccf.authz.capability.InvalidationRecordRegister`
        for each composed tenant's :func:`register_key` and hands the capabilities here. Each is
        verified at construction against exactly that prefix, so a capability for another prefix,
        another kind, or no mint at all is refused before the sink exists.

        Raises:
            ccf.authz.capability.CapabilityBypassError: a capability is fabricated,
                retargeted, not ``InvalidationRecordRegister``, or not for its own tenant's
                invalidation prefix.
            InvalidationUnauthorized: two capabilities name one tenant, or none was handed in.
        """
        held: dict[str, Authorized[InvalidationRecordRegister]] = {}
        for authorized in authorities:
            tenant = getattr(authorized, "tenant", None)
            expected = register_key(tenant) if isinstance(tenant, str) and tenant else ""
            verify(authorized, kind=InvalidationRecordRegister, resource=expected)
            if authorized.tenant in held:
                raise InvalidationUnauthorized(
                    f"two invalidation-record capabilities were handed in for tenant"
                    f" {authorized.tenant!r}; a composition mints one per tenant (D-IMPL-354)"
                )
            held[authorized.tenant] = authorized
        if not held:
            raise InvalidationUnauthorized(
                "no invalidation-record capability was handed to the invalidation sink; a fabric"
                " is composed for at least one tenant, and a sink for no tenant could record no"
                " supersession (D-IMPL-354)"
            )
        self._registry = registry
        self._authorities = held

    @property
    def tenants(self) -> frozenset[str]:
        """The tenants this sink holds a capability for — the fabric's composed tenants."""
        return frozenset(self._authorities)

    def boundary(self, tenant_id: str, entity_uri: str) -> EntityInvalidationRecord | None:
        """``entity_uri``'s record for ``tenant_id`` at its latest version, or ``None``."""
        return resolve_record(self._registry, tenant_id=tenant_id, entity_uri=entity_uri)

    def record(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        invalidated_from: datetime,
        reason: str,
        source: str,
    ) -> None:
        """Advance one entity's boundary, as a new audited version of that entity's record.

        The capability is looked up FIRST — before anything is read — so a tenant this fabric was
        not composed for is refused with nothing read and nothing written. Then only this
        entity's record is read and, if the boundary moves, only it is written.

        Raises:
            InvalidationUnauthorized: this sink holds no capability for ``tenant_id``.
        """
        authorized = self._authorities.get(tenant_id)
        if authorized is None:
            raise InvalidationUnauthorized(
                f"a supersession under tenant {tenant_id!r} reached the invalidation sink, and"
                " this fabric holds an invalidation-record capability only for"
                f" {sorted(self._authorities)!r}; the composition root mints one per tenant it"
                " composes for (`boot(..., tenant_ids=...)`), and a tenant it did not name cannot"
                " have its boundary moved (D-IMPL-353 §1.6; D-IMPL-354)"
            )
        incoming = EntityInvalidationRecord(
            semver=RECORD_SEMVER,
            tenant_id=tenant_id,
            entity_uri=entity_uri,
            invalidated_from=invalidated_from,
            reason=reason,
            source=source,
        )
        standing = self.boundary(tenant_id, entity_uri)
        if standing is not None and not standing.advanced_by(incoming):
            # THE BOUNDARY DID NOT MOVE, so nothing is registered. A version per no-op write
            # would fill the audit log with entries that changed nothing.
            return
        self._registry.register_typed(authorized, incoming, ENTITY_INVALIDATION_RECORD)


def resolve_record(
    registry: ControlPlaneProtocol, *, tenant_id: str, entity_uri: str
) -> EntityInvalidationRecord | None:
    """``tenant_id``'s invalidation record for ``entity_uri`` at its latest version, or ``None``.

    ``None`` for an entity nothing has superseded — which is every entity before this mechanism
    ran, and is why the gate is additive. ``resolve_latest`` is the right resolution: eligibility
    is a question about **now**; a replay reproduces the product it recorded and does not re-ask
    whether that product may be served today.
    """
    key = record_key(tenant_id, entity_uri)
    try:
        _, artifact = registry.resolve_latest(key)
    except ControlPlaneMissing:
        return None
    if not isinstance(artifact, EntityInvalidationRecord) or artifact.entity_uri != entity_uri:
        raise TypeError(
            f"{key!r} holds {type(artifact).__name__}"
            f" for {getattr(artifact, 'entity_uri', None)!r}, not this entity's EntityInvalidationRecord"
        )
    return artifact


class _EnumerableRegistry(Protocol):
    """What :func:`invalidation_history` reads: the registry's introspection surface."""

    def keys_of_class(self, class_id: str) -> tuple[str, ...]: ...
    def versions(self, key: str) -> tuple[str, ...]: ...
    def peek(self, key: str, version: str) -> object: ...


def invalidation_history(
    registry: _EnumerableRegistry, *, tenant_id: str
) -> dict[str, tuple[EntityInvalidationRecord, ...]]:
    """Every entity's boundary history for ``tenant_id``, oldest version first — the audit reconstruction.

    The tenant's history is the union of its entity keys' version chains (``D-IMPL-382``): one
    chain per entity, each the sequence of boundaries that entity's record took. Read through
    ``peek`` (introspection, unaudited — it resolves no decision), each version a fresh,
    verified reconstruction.
    """
    prefix = register_key(tenant_id) + "/"
    history: dict[str, tuple[EntityInvalidationRecord, ...]] = {}
    for key in registry.keys_of_class(INVALIDATION_RECORD_CLASS_ID):
        if not key.startswith(prefix):
            continue
        chain = tuple(registry.peek(key, version) for version in registry.versions(key))
        for version_artifact in chain:
            # Refuse, as resolve_record does — never drop or misfile (review of b66ab4fa): every version
            # under this key must be this tenant's record for the entity whose key it is.
            if (
                type(version_artifact) is not EntityInvalidationRecord
                or version_artifact.tenant_id != tenant_id
                or record_key(tenant_id, version_artifact.entity_uri) != key
            ):
                raise TypeError(
                    f"{key!r} holds {type(version_artifact).__name__}"
                    f" for {getattr(version_artifact, 'entity_uri', None)!r}, not this key's"
                    " EntityInvalidationRecord"
                )
        records = cast(tuple[EntityInvalidationRecord, ...], chain)
        if records:
            history[records[-1].entity_uri] = records
    return history
