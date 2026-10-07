"""The erasure-consulting store — the ONE consult at the substrate read (G4; SEC-009, `D-IMPL-374` (4)).

Design ``D-IMPL-367`` §3 with fix-round-1 rulings C1, (i), (ii), I3, I6, I7.
The consult lives inside the store the deployment holds, as a decorator
around whatever store it is given, composed at EVERY store construction site
through :func:`compose_erasure_consult`, over a REQUIRED
:class:`~ccf.erasure.ErasureIndexProtocol` — a composition without a declared
index refuses by name (:class:`ErasureIndexUnavailable`). On an empty index
the decorator is identity.

* **Tenant scope (I6, ruling (i)).** A store composed for a tenant — or the
  per-tenant view :meth:`ErasureConsultingStore.scoped` a multi-tenant door
  takes for the caller's VERIFIED tenant — withholds only what that tenant
  erased, with the erasure's reason, instant and record address. A
  tenantless read (the replay engine, ``record_of``, child admission, the MCP
  client lane) WITHHOLDS if any tenant erased the address, with the reason and
  record address REDACTED, so no tenant learns another's erasure.
* **The record is the only authority (U7, §8, I3).** At composition every
  entry of every tenant (``tenants()`` → ``entries()``) is validated against
  its ``ccf.erasure-record``, read through the inner store: the bytes must
  hash to the entry's record address and the record must name the tenant,
  the address, the hashed subject and the approval reference the entry
  carries. An entry that fails — its record missing (a completion that died
  between the write-ahead entry and the record) or disagreeing — still
  withholds its address, with the reason ``index-unsupported`` and nothing
  of the record, and is audited ``erasure_index_unsupported``. An entry
  appended after composition is validated the first time a read meets it.
* **O(1) per read (I7).** A scoped read is one ``lookup``; a tenantless read
  is one ``lookup`` per tenant. No read scans entries.

:meth:`ErasureConsultingStore.get` and :meth:`ErasureConsultingStore.resolve_uri`
consult; :meth:`ErasureConsultingStore.exists` does **not** (U8); ``put``
passes through. The Protocol's four verbs are unchanged and no removal or
un-erasure surface exists (U6). Algorithmic module (CINV-03): the
``index-unsupported`` audit event is stamped with the fabric clock injected at
composition (ruling 3), never a wall clock and never the disputed entry's own
``erased_at``.

**Boot validation is memoized per index head** (ruling 4): the key is the
index's identity (its file path, for the file index), its entry count and the
store's identity (its root, for a file store), so a site that composes once
per question — the governed resolver — does not re-read every record; an
append changes the count and invalidates it. Only SUPPORTED entries are
memoized: an unsupported one is re-judged, and audited, by every composition.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Final

from pydantic import ValidationError

from ccf.artifacts.protocol import (
    ArtifactName,
    ArtifactRef,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    ArtifactWriteAuthority,
    WriteKinds,
)
from ccf.controlplane.audit import AuditLog
from ccf.erasure.contracts import ERASURE_RECORD_CLASS, ErasureRecord
from ccf.erasure.index import ErasureIndexEntry, ErasureIndexProtocol

__ccf_mode__ = "algorithmic"

__all__ = [
    "INDEX_UNSUPPORTED",
    "ErasedContentRefused",
    "ErasureConsultingStore",
    "ErasureIndexUnavailable",
    "compose_erasure_consult",
]

#: The reason a withheld address carries when its index entry is not supported
#: by an agreeing erasure record (design §8; mechanism vocabulary).
INDEX_UNSUPPORTED: Final[str] = "index-unsupported"


class ErasedContentRefused(ArtifactStoreError):
    """The address holds content a recorded erasure says is not served (SEC-009; `D-IMPL-374` (4)).

    Raised by :class:`ErasureConsultingStore` on a read of an erased address,
    in place of the bytes. An :class:`~ccf.artifacts.protocol.ArtifactStoreError`
    and deliberately **not** an ``ArtifactNotFound`` nor a ``LookupError``: an
    erasure is a recorded decision, not an absence (G5).

    Carries the erasure's record address, reason and instant **only** for a
    read scoped to the erasing tenant; a tenantless read, and an entry the
    record does not support, carry ``None`` there (I6; §8). Never anything of
    the subject, and the message carries no record address (M8). The bytes it
    withholds remain on the substrate; no destruction is claimed.
    """

    def __init__(
        self,
        *,
        content_address: str,
        erasure_record_address: str | None,
        reason: str | None,
        erased_at: datetime | None,
    ) -> None:
        super().__init__(f"{content_address!r} was erased and is not served (SEC-009)")
        self.content_address = content_address
        self.erasure_record_address = erasure_record_address
        self.reason = reason
        self.erased_at = erased_at


class ErasureIndexUnavailable(TypeError):
    """A store construction site declared no erasure index (SEC-009; `D-IMPL-374` (4), C1).

    Raised at composition — where an operator sees it — never at a read: a
    store that could not consult would serve erased bytes silently.
    """


#: Supported-entry keys per (index head, store) — ruling 4. Bounded: the oldest
#: head is dropped past the bound, which only costs a re-validation.
_VALIDATED_HEADS: dict[tuple[str, int, str], frozenset[tuple[str, str, str]]] = {}
_VALIDATED_HEADS_BOUND: Final[int] = 64
_VALIDATED_HEADS_LOCK = threading.Lock()


def _identity(subject: object, attribute: str) -> str:
    named = getattr(subject, attribute, None)
    return f"{attribute}:{named}" if named is not None else f"id:{id(subject)}"


class _Verdicts:
    """Validation results shared by a composed store and its tenant views."""

    def __init__(self) -> None:
        self.valid: set[tuple[str, str, str]] = set()
        self.audited: set[tuple[str, str, str]] = set()


class ErasureConsultingStore:
    """An :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` that refuses to serve erased content (SEC-009; `D-IMPL-374` (4)).

    Construct through :func:`compose_erasure_consult`.
    """

    def __init__(
        self,
        inner: ArtifactStoreProtocol,
        *,
        index: ErasureIndexProtocol,
        audit_log: AuditLog,
        clock: Callable[[], datetime],
        tenant_id: str | None,
        _verdicts: _Verdicts | None = None,
    ) -> None:
        self._inner = inner
        self._index = index
        self._audit_log = audit_log
        self._clock = clock
        self._tenant_id = tenant_id
        self._verdicts = _Verdicts() if _verdicts is None else _verdicts

    # -- composition introspection ------------------------------------------------

    @property
    def inner(self) -> ArtifactStoreProtocol:
        """The decorated store."""
        return self._inner

    @property
    def index(self) -> ErasureIndexProtocol:
        """The declared erasure index."""
        return self._index

    @property
    def tenant_id(self) -> str | None:
        """The tenant this view is scoped to, or ``None`` for tenantless reads."""
        return self._tenant_id

    @property
    def write_kinds(self) -> WriteKinds | None:
        """The inner store's write-kinds declaration, so wiring checks read through the decorator."""
        declared = getattr(self._inner, "write_kinds", None)
        return declared if isinstance(declared, WriteKinds) else None

    def names_at(self, *, content_address: str) -> tuple[ArtifactName, ...]:
        """The inner store's naming introspection — never a byte read.

        Raises:
            AttributeError: the inner store answers no naming (C2 then refuses
                an erasure over it by name, ``class-unverifiable``).
        """
        names = getattr(self._inner, "names_at")
        found: tuple[ArtifactName, ...] = names(content_address=content_address)
        return found

    def scoped(self, tenant_id: str) -> "ErasureConsultingStore":
        """This store as one tenant's view (I6): withholds only what ``tenant_id`` erased."""
        return ErasureConsultingStore(
            self._inner,
            index=self._index,
            audit_log=self._audit_log,
            clock=self._clock,
            tenant_id=tenant_id,
            _verdicts=self._verdicts,
        )

    def validate_all(self) -> None:
        """Validate every entry of every tenant against its record (boot; §8), memoized per index head (ruling 4)."""
        entries = [
            entry
            for tenant in sorted(self._index.tenants())
            for entry in self._index.entries(tenant_id=tenant)
        ]
        head = (_identity(self._index, "path"), len(entries), _identity(self._inner, "root"))
        with _VALIDATED_HEADS_LOCK:
            known = _VALIDATED_HEADS.get(head)
        keys = {(e.tenant_id, e.content_address, e.erasure_record_address) for e in entries}
        if known is not None:
            self._verdicts.valid |= known & keys
        for entry in entries:
            self._supported(entry)
        with _VALIDATED_HEADS_LOCK:
            _VALIDATED_HEADS[head] = frozenset(self._verdicts.valid & keys)
            while len(_VALIDATED_HEADS) > _VALIDATED_HEADS_BOUND:
                _VALIDATED_HEADS.pop(next(iter(_VALIDATED_HEADS)))

    # -- the consult -------------------------------------------------------------------

    def _supported(self, entry: ErasureIndexEntry) -> bool:
        """Whether ``entry``'s record exists and agrees; audits a disagreement once."""
        key = (entry.tenant_id, entry.content_address, entry.erasure_record_address)
        if key in self._verdicts.valid:
            return True
        try:
            payload = self._inner.get(content_address=entry.erasure_record_address)
            record = ErasureRecord.model_validate_json(payload)
            agrees = (
                hashlib.sha256(payload).hexdigest() == entry.erasure_record_address
                and record.tenant_id == entry.tenant_id
                and record.subject_ref == entry.subject_ref
                and record.approval_ref == entry.approval_ref
                and entry.content_address in {a.content_address for a in record.addresses}
            )
        except (ArtifactStoreError, KeyError, OSError, ValidationError, ValueError):
            agrees = False
        if agrees:
            self._verdicts.valid.add(key)
            return True
        if key not in self._verdicts.audited:
            self._verdicts.audited.add(key)
            self._audit_log.append(
                action="erasure_index_unsupported",
                key=f"{entry.tenant_id}/{entry.content_address}",
                version=entry.erasure_record_address,
                resolved=False,
                occurred_at=self._clock(),
                artifact_class=ERASURE_RECORD_CLASS,
            )
        return False

    def _refusal(self, entry: ErasureIndexEntry, *, disclose: bool) -> ErasedContentRefused:
        supported = self._supported(entry)
        if not supported:
            return ErasedContentRefused(
                content_address=entry.content_address,
                erasure_record_address=None,
                reason=INDEX_UNSUPPORTED if disclose else None,
                erased_at=None,
            )
        return ErasedContentRefused(
            content_address=entry.content_address,
            erasure_record_address=entry.erasure_record_address if disclose else None,
            reason=entry.reason if disclose else None,
            erased_at=entry.erased_at if disclose else None,
        )

    def _consult(self, content_address: str) -> None:
        """THE consult: refuse an address the index names as erased."""
        if self._tenant_id is not None:
            entry = self._index.lookup(tenant_id=self._tenant_id, content_address=content_address)
            if entry is not None:
                raise self._refusal(entry, disclose=True)
            return
        for tenant in sorted(self._index.tenants()):
            entry = self._index.lookup(tenant_id=tenant, content_address=content_address)
            if entry is not None:
                raise self._refusal(entry, disclose=False)

    # -- the four Protocol verbs -------------------------------------------------------

    def put(self, authorized: ArtifactWriteAuthority, artifact: object) -> ArtifactRef:
        """Pass through to the inner store: erasure is a read-side control (SEC-009)."""
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        """The inner store's bytes, unless the index names the address erased (SEC-009).

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


def compose_erasure_consult(
    store: ArtifactStoreProtocol,
    *,
    index: ErasureIndexProtocol,
    audit_log: AuditLog,
    clock: Callable[[], datetime],
    tenant_id: str | None = None,
) -> ErasureConsultingStore:
    """THE composition helper every store construction site uses (SEC-009; `D-IMPL-374` (4), C1, (i), U12).

    Wraps ``store`` over the REQUIRED ``index`` and the REQUIRED fabric
    ``clock`` (which stamps the ``index-unsupported`` audit; ruling 3),
    validates every entry against its record (§8; memoized per index head,
    ruling 4), and returns the store scoped to ``tenant_id`` — or
    tenantless (``None``) for a multi-tenant site whose doors take
    :meth:`ErasureConsultingStore.scoped` views for the caller's verified
    tenant. A store already composed is re-scoped, never re-wrapped, and must
    have been composed over the SAME index (M1).

    Raises:
        ErasureIndexUnavailable: ``index`` is not an
            :class:`~ccf.erasure.ErasureIndexProtocol`, or ``store`` was already
            composed over a different index.
    """
    if not isinstance(index, ErasureIndexProtocol):
        raise ErasureIndexUnavailable(
            f"{type(index).__name__} is not an ErasureIndexProtocol; every store"
            " construction site declares its durable erasure index, and a store"
            " that cannot consult would serve erased content (SEC-009; D-IMPL-374"
            " (4), C1)"
        )
    if isinstance(store, ErasureConsultingStore):
        if store.index is not index:
            raise ErasureIndexUnavailable(
                "this store was already composed over a different erasure index;"
                " re-composing it over another would consult the wrong erasures"
                " (SEC-009; M1)"
            )
        if store.tenant_id == tenant_id:
            return store
        return store.scoped(tenant_id) if tenant_id is not None else ErasureConsultingStore(
            store.inner, index=index, audit_log=audit_log, clock=clock, tenant_id=None
        )
    composed = ErasureConsultingStore(
        store, index=index, audit_log=audit_log, clock=clock, tenant_id=tenant_id
    )
    composed.validate_all()
    return composed
