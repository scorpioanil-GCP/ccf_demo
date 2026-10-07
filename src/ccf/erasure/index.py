"""The durable erasure index — ``ErasureIndexProtocol`` and its file-backed reference (SEC-009; `D-IMPL-374` (4)).

Fix-round-1 ruling C1, as amended by rulings (i) and (ii). The artifact store is
immutable and version-pinned by design, so "the erasures in force" — state
that grows — lives in an append-only index of its own, declared at
composition and REQUIRED at every store construction site.

**The record is the only authority** (U7). Every entry names its erasure
record's content address, the hashed subject, the tenant, the erased address
and the approval reference; the decorating store validates every entry
against its record (:mod:`ccf.erasure.store`) and refuses to serve an address
whose entry disagrees, auditing ``erasure_index_unsupported`` (design §8).

**Grows only.** :meth:`ErasureIndexProtocol.append` is the one write; an
identical entry is idempotent, a different entry for an already-erased
``(tenant, address)`` is refused (:class:`ErasureIndexEntryExists`), and no
removal or un-erasure verb exists (U6).

**Write-ahead** (ruling (ii)): the erasure door appends the entry BEFORE it
files the record, so a record with no entry cannot exist and no listing of the
store is needed; an entry whose record never arrived is the §8 disagreement.

Algorithmic module (CINV-03): no clock is read here.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERASURE_INDEX_FILENAME",
    "ErasureIndexEntryExists",
    "ErasureIndexEntry",
    "ErasureIndexProtocol",
    "FileErasureIndex",
    "erasure_index_at",
]

#: The conventional file name of a deployment's index beside its file-backed
#: artifact store: dot-prefixed and not a content address, so the store's
#: read path (``held_content_address``) can never serve it.
ERASURE_INDEX_FILENAME: Final[str] = ".erasure-index.jsonl"


class ErasureIndexEntryExists(ValueError):
    """An already-erased ``(tenant, address)`` was offered a different entry; the index never replaces one (SEC-009; `D-IMPL-374` (4))."""


class ErasureIndexEntry(CCFContract):
    """One erased address within one tenant, naming its authority record (SEC-009; `D-IMPL-374` (4)).

    Attributes:
        tenant_id: The tenant the erasure withholds within (I6).
        content_address: The erased artifact.
        erasure_record_address: The content address of the ``ccf.erasure-record``
            that is the authority for this entry.
        subject_ref: The salted subject reference the record carries.
        approval_ref: The content hash of the recorded approval the record carries.
        reason: The admitted erasure reason (disclosed at ``reasoned``).
        erased_at: The record's ``erased_at`` (disclosed at ``reasoned``).
    """

    tenant_id: str
    content_address: str
    erasure_record_address: str
    subject_ref: str
    approval_ref: str
    reason: str
    erased_at: datetime


@runtime_checkable
class ErasureIndexProtocol(Protocol):
    """The append-only erasure index every store construction site declares (SEC-009; `D-IMPL-374` (4), C1).

    ``lookup`` is O(1) per ``(tenant, address)`` (I7); ``entries`` and
    ``tenants`` serve the decorating store's boot validation.
    """

    def append(self, entry: ErasureIndexEntry) -> None:
        """Durably add ``entry``; idempotent for an identical entry.

        Raises:
            ErasureIndexEntryExists: a different entry already erases the address
                within the tenant.
        """
        ...

    def lookup(self, *, tenant_id: str, content_address: str) -> ErasureIndexEntry | None:
        """The entry erasing ``content_address`` within ``tenant_id``, or ``None``."""
        ...

    def entries(self, *, tenant_id: str) -> tuple[ErasureIndexEntry, ...]:
        """Every entry of ``tenant_id``, in append order."""
        ...

    def tenants(self) -> frozenset[str]:
        """Every tenant that holds at least one entry."""
        ...


class FileErasureIndex:
    """The reference :class:`ErasureIndexProtocol`: append-only JSON lines, fsync on append (SEC-009; `D-IMPL-374` (4)).

    One file per deployment. Entries are held in memory keyed by
    ``(tenant, address)`` for O(1) lookup; a read first picks up any lines
    another process appended since (one ``stat`` — the file only grows), so
    two processes over one file agree. A line that does not parse is refused
    at load rather than skipped: an index that silently dropped an entry would
    un-erase its address.

    Args:
        path: The index file. Created (with parents) on the first append.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._offset = 0
        self._by_key: dict[tuple[str, str], ErasureIndexEntry] = {}
        self._by_tenant: dict[str, list[ErasureIndexEntry]] = {}
        with self._lock:
            self._catch_up()

    @property
    def path(self) -> Path:
        """The index file."""
        return self._path

    def _catch_up(self) -> None:
        try:
            size = self._path.stat().st_size
        except FileNotFoundError:
            return
        if size <= self._offset:
            return
        with self._path.open("rb") as handle:
            handle.seek(self._offset)
            tail = handle.read(size - self._offset)
        last = tail.rfind(b"\n")
        if last < 0:
            return  # a line still being written; read it next time
        for line in tail[:last].split(b"\n"):
            if line.strip():
                self._admit(ErasureIndexEntry.model_validate_json(line))
        self._offset += last + 1

    def _admit(self, entry: ErasureIndexEntry) -> None:
        key = (entry.tenant_id, entry.content_address)
        if key in self._by_key:
            return  # the first entry stands; a later conflicting line was refused at append
        self._by_key[key] = entry
        self._by_tenant.setdefault(entry.tenant_id, []).append(entry)

    def append(self, entry: ErasureIndexEntry) -> None:
        with self._lock:
            self._catch_up()
            standing = self._by_key.get((entry.tenant_id, entry.content_address))
            if standing is not None:
                if standing == entry:
                    return
                raise ErasureIndexEntryExists(
                    f"{entry.content_address!r} is already erased within tenant"
                    f" {entry.tenant_id!r} under another record; an erasure index"
                    " entry is never replaced (SEC-009; U6)"
                )
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = canonical_bytes(entry) + b"\n"
            descriptor = os.open(self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(descriptor, line)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._catch_up()

    def lookup(self, *, tenant_id: str, content_address: str) -> ErasureIndexEntry | None:
        with self._lock:
            self._catch_up()
            return self._by_key.get((tenant_id, content_address))

    def entries(self, *, tenant_id: str) -> tuple[ErasureIndexEntry, ...]:
        with self._lock:
            self._catch_up()
            return tuple(self._by_tenant.get(tenant_id, ()))

    def tenants(self) -> frozenset[str]:
        with self._lock:
            self._catch_up()
            return frozenset(self._by_tenant)

    def __repr__(self) -> str:
        return f"FileErasureIndex({str(self._path)!r})"


def erasure_index_at(store_root: Path | str) -> FileErasureIndex:
    """The conventional file index beside a file-backed store rooted at ``store_root`` (SEC-009; `D-IMPL-374` (4)).

    What the in-process and local-CLI composition sites use: their existing
    declared store root fixes the index's path, so one deployment has one file.
    """
    return FileErasureIndex(Path(store_root) / ERASURE_INDEX_FILENAME)

