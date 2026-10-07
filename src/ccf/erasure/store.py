"""The erasure-consulting store — the ONE consult at the substrate read (G4; SEC-009, `D-IMPL-374` (4)).

Design ``D-IMPL-367`` §3: the consult lives inside the store the deployment
holds, as a decorator around whatever store it is given, so every in-process
read site, both doors and anything written later reads through it. U12, ruled:
composed ALWAYS (``ccf_runtime.http_api.app.create_app`` wraps the store it is
handed); on an empty index it is identity.

* :meth:`ErasureConsultingStore.get` and :meth:`ErasureConsultingStore.resolve_uri`
  consult the registry mirror and raise
  :class:`ErasedContentRefused` — never the bytes.
* :meth:`ErasureConsultingStore.exists` does **not** consult (U8): it answers
  the store's truth, which ``put``'s idempotency relies on.
* :meth:`ErasureConsultingStore.put` passes through: erasure is a read-side
  control, and an erasure record is itself written through this verb.

The Protocol's four verbs are unchanged and the decorator adds no removal or
un-erasure surface (U6). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from ccf.artifacts.protocol import (
    ArtifactRef,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    ArtifactWriteAuthority,
    WriteKinds,
)
from ccf.erasure.index import ErasureIndex

__ccf_mode__ = "algorithmic"

__all__ = ["ErasedContentRefused", "ErasureConsultingStore"]


class ErasedContentRefused(ArtifactStoreError):
    """The address holds content a recorded erasure says is not served (SEC-009; `D-IMPL-374` (4)).

    Raised by :class:`ErasureConsultingStore` on a read of an erased address,
    in place of the bytes. An :class:`~ccf.artifacts.protocol.ArtifactStoreError`
    sibling of ``ArtifactUriUnresolvable`` (design ``D-IMPL-367`` §3) and
    deliberately **not** an ``ArtifactNotFound`` and not a ``LookupError``: an
    erasure is a recorded decision, not an absence, and a site that swallowed
    it into "not found" would be the silent-absence defect G5 forbids. Every
    reader either maps it to its own positive outcome or lets it propagate to
    a door that does.

    Carries the erasure record's address, the admitted reason and the erasure
    instant — **never anything of the subject**. The bytes it withholds remain
    on the substrate; no destruction is claimed (``D-IMPL-367`` O1).
    """

    def __init__(
        self, *, content_address: str, erasure_record_address: str, reason: str, erased_at: datetime
    ) -> None:
        super().__init__(
            f"{content_address!r} was erased by the record at"
            f" {erasure_record_address!r} and is not served (SEC-009)"
        )
        self.content_address = content_address
        self.erasure_record_address = erasure_record_address
        self.reason = reason
        self.erased_at = erased_at


class ErasureConsultingStore:
    """An :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` that refuses to serve erased content (SEC-009; `D-IMPL-374` (4)).

    Args:
        inner: The store the deployment composed. A store already wrapped is
            not wrapped twice (:meth:`around`).
        index: The registry-mirror reader the consult asks.
    """

    def __init__(self, inner: ArtifactStoreProtocol, *, index: ErasureIndex) -> None:
        self._inner = inner
        self._index = index

    @classmethod
    def around(cls, store: ArtifactStoreProtocol, *, index: ErasureIndex) -> "ErasureConsultingStore":
        """``store`` decorated — or ``store`` itself when it already is (composition is idempotent)."""
        return store if isinstance(store, cls) else cls(store, index=index)

    @property
    def inner(self) -> ArtifactStoreProtocol:
        """The decorated store."""
        return self._inner

    @property
    def write_kinds(self) -> WriteKinds | None:
        """The inner store's write-kinds declaration, so wiring checks read through the decorator."""
        declared = getattr(self._inner, "write_kinds", None)
        return declared if isinstance(declared, WriteKinds) else None

    def _consult(self, content_address: str) -> None:
        """THE consult: refuse an address the mirror names as erased."""
        entry = self._index.lookup(content_address)
        if entry is not None:
            raise ErasedContentRefused(
                content_address=content_address,
                erasure_record_address=entry.erasure_record_address,
                reason=entry.reason,
                erased_at=entry.erased_at,
            )

    def put(self, authorized: ArtifactWriteAuthority, artifact: object) -> ArtifactRef:
        """Pass through to the inner store: erasure is a read-side control (SEC-009)."""
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        """The inner store's bytes, unless the mirror names the address erased (SEC-009).

        Raises:
            ErasedContentRefused: the address was erased.
        """
        self._consult(content_address)
        return self._inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        """The inner store's truth; deliberately NOT consulted (U8; SEC-009)."""
        return self._inner.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        """The inner store's resolution, refused when it names an erased address (SEC-009).

        Raises:
            ErasedContentRefused: the resolved address was erased.
        """
        address = self._inner.resolve_uri(uri=uri)
        self._consult(address)
        return address
