"""The erasure index — a registry MIRROR of erasure records (U7 (b); SEC-009, `D-IMPL-374` (4)).

Design ``D-IMPL-367`` §2.3 U7 (b), ruled: the index the consult reads is an
append-only Control Plane *registry* entry per tenant, on the
``EntityInvalidationRegister`` precedent (``D-IMPL-334``) — audited, versioned,
grows only. **The erasure record is the only authority**; the mirror is a
derived view. An entry the mirror names is served as erased whether or not a
record supports it — the fail-closed direction of design §8's disagreement row.

**Grows only.** :class:`ErasureIndexMirror` has an append and no removal, no
un-erasure verb exists anywhere (U6), and the consult reads EVERY registered
version — so a later version that omits an address cannot un-erase it.

The read (:class:`ErasureIndex`) uses the registry's UNAUDITED introspection
(``keys_of_class``, ``versions``, ``peek``): the consult runs on every artifact
read, and an audit event per read would record resolutions that are not
governance acts (the ``resolve_pinned`` WR-08 reasoning).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from pydantic import Field

from ccf.authz.capability import Authorized, CompositionRegister, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.controlplane.registry import ControlPlaneRegistry

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERASURE_INDEX",
    "ERASURE_INDEX_SEMVER",
    "ErasureIndex",
    "ErasureIndexEntry",
    "ErasureIndexMirror",
    "ErasureIndexSource",
    "append_to_erasure_index",
    "erasure_index_key",
]

#: The mirror's own semver lane (stated, never defaulted).
ERASURE_INDEX_SEMVER: Final[str] = "1.0.0"

_KEY_CLASS: Final[str] = "ccf.erasure-index"


def erasure_index_key(tenant_id: str) -> str:
    """The Control Plane key of ``tenant_id``'s mirror: ``{tenant}/ccf.erasure-index`` (SEC-009; `D-IMPL-374` (4))."""
    return f"{tenant_id}/{_KEY_CLASS}"


class ErasureIndexEntry(CCFContract):
    """One erased address, as the consult needs it — and nothing of the subject (SEC-009; `D-IMPL-374` (4)).

    Attributes:
        content_address: The erased artifact's address.
        erasure_record_address: The content address of the authority record.
        reason: The admitted erasure reason, from the policy's closed set (disclosed at ``reasoned``).
        erased_at: The record's ``erased_at`` (disclosed at ``reasoned``).
    """

    content_address: str
    erasure_record_address: str
    reason: str
    erased_at: datetime


class ErasureIndexMirror(VersionedArtifact):
    """One tenant's erased addresses — re-registered as a new immutable version per append (SEC-009; `D-IMPL-374` (4))."""

    tenant_id: str
    entries: tuple[ErasureIndexEntry, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )

    def entry_for(self, content_address: str) -> ErasureIndexEntry | None:
        """The entry for ``content_address``, or ``None``."""
        return next((e for e in self.entries if e.content_address == content_address), None)

    def with_entries(self, added: tuple[ErasureIndexEntry, ...]) -> "ErasureIndexMirror":
        """This mirror plus ``added``; an address already present keeps its first entry (grows only)."""
        kept = {e.content_address: e for e in self.entries}
        for entry in added:
            kept.setdefault(entry.content_address, entry)
        return ErasureIndexMirror(
            semver=self.semver,
            tenant_id=self.tenant_id,
            entries=tuple(sorted(kept.values(), key=lambda e: e.content_address)),
        )


#: The mirror's registered class (U7 (b)).
ERASURE_INDEX = ArtifactClass(class_id=_KEY_CLASS, contract=ErasureIndexMirror)


@runtime_checkable
class ErasureIndexSource(Protocol):
    """The unaudited registry introspection the consult reads (SEC-009; `D-IMPL-374` (4))."""

    def keys_of_class(self, class_id: str) -> tuple[str, ...]: ...

    def versions(self, key: str) -> tuple[str, ...]: ...

    def peek(self, key: str, version: str) -> object: ...


class ErasureIndex:
    """The consult's read of every tenant's mirror (SEC-009; `D-IMPL-374` (4)).

    Content addressing means one address may be filed by several tenants; an
    erasure of an address is therefore served as erased to every reader — the
    safe direction, since the bytes at the address are the same bytes.
    """

    def __init__(self, source: ErasureIndexSource) -> None:
        self._source = source

    def lookup(self, content_address: str) -> ErasureIndexEntry | None:
        """The entry naming ``content_address`` in ANY version of any tenant's mirror, or ``None``.

        **Every version, oldest first — never only the newest** (U6). The
        mirror is append-only by its own writer, but the registry accepts any
        well-typed version from a holder of the key's ``Register``
        capability; reading only the newest would let a later version that
        omits an address un-erase it by omission. Reading the whole history
        makes an erasure, once mirrored, permanent for the consult.

        Raises:
            TypeError: a key bound to the mirror class holds something else —
                a broken registry, refused rather than read as "not erased".
        """
        for key in self._source.keys_of_class(ERASURE_INDEX.class_id):
            for version in self._source.versions(key):
                mirror = self._source.peek(key, version)
                if not isinstance(mirror, ErasureIndexMirror):
                    raise TypeError(
                        f"{key!r} holds {type(mirror).__name__}, not ErasureIndexMirror"
                        " (SEC-009)"
                    )
                entry = mirror.entry_for(content_address)
                if entry is not None:
                    return entry
        return None


def append_to_erasure_index(
    registry: ControlPlaneRegistry,
    authorized: Authorized[CompositionRegister],
    entries: tuple[ErasureIndexEntry, ...],
) -> str:
    """Append ``entries`` to the capability's tenant mirror as a new audited version (SEC-009; `D-IMPL-374` (4)).

    The capability is a composition-minted ``Register`` for exactly
    :func:`erasure_index_key` of its tenant (``D-IMPL-354``), verified first.

    Raises:
        ccf.authz.capability.CapabilityBypassError: fabricated, retargeted or
            wrong-kind capability.
    """
    tenant = getattr(authorized, "tenant", "")
    verify(authorized, kind=CompositionRegister, resource=erasure_index_key(str(tenant)))
    key = erasure_index_key(authorized.tenant)
    versions = registry.versions(key)
    standing = registry.peek(key, versions[-1]) if versions else None
    if not isinstance(standing, ErasureIndexMirror):
        standing = ErasureIndexMirror(semver=ERASURE_INDEX_SEMVER, tenant_id=authorized.tenant)
    return registry.register_typed(authorized, standing.with_entries(entries), ERASURE_INDEX)
