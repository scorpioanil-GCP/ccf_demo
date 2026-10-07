"""The durable erasure index — ``ErasureIndexProtocol`` and its file-backed reference (SEC-009; `D-IMPL-374` (4)).

Fix-round-1 ruling C1 as amended by rulings (i) and (ii), and fix-round-2
rulings I3, (a) and N3. The artifact store is immutable and version-pinned by
design, so "the erasures in force" — state that grows — lives in an
append-only index of its own, declared at composition and REQUIRED at every
store construction site.

**The record is the only authority** (U7). Every entry names its erasure
record's content address, the request it answers, the hashed subject, the
tenant, the erased address and the approval reference, and carries the
erasure door's signature over the record (fix round 5, R2); the decorating
store verifies that signature and validates every entry against its record
(:mod:`ccf.erasure.store`), and refuses to serve an address whose entry
disagrees, auditing ``erasure_index_unsupported`` (design §8).

**Only the erasure door writes it** (I3). :meth:`ErasureIndexProtocol.append`
takes the ``ArtifactErase`` capability bound to the entry's own request
(``"<subject_class>/<request_id>"``) and the entry's tenant; anything else is
refused by name before a byte is written.

**Grows only.** An identical entry is idempotent, a different entry for an
already-erased ``(tenant, address)`` is refused (:class:`ErasureIndexEntryExists`),
and no removal or un-erasure verb exists (U6).

**The file is private and chained** (fix round 2 (a)). The reference file is
opened ``O_NOFOLLOW``; it and its parent must be owned by the effective user,
the file mode ``0600`` and the parent ``0700``, or the index is refused by
name (:class:`~ccf.erasure.ErasureIndexInsecure`). Every line carries the
hash of the line before it, so an edited, reordered or interleaved line
breaks the chain and the index is refused (:class:`~ccf.erasure.ErasureIndexCorrupt`,
fail closed). **Residual, stated plainly:** a truncated TAIL leaves a valid
shorter chain and is not detectable without state kept outside the file — an
attacker with write access to the index file can un-erase its tail; the file
modes and the deployment's filesystem controls are the mitigation.

**A torn line fails closed, and is repaired by hand** (fix round 4, re-review
M-a). A process killed in the middle of an append can leave a partial last
line; the next append lands after it, the two read as one malformed line, and
the index is refused as :class:`~ccf.erasure.ErasureIndexCorrupt` — every read
under it is withheld. That stays the posture: the SDK never guesses which of
two merged writes was meant. The SDK ships no repair tool; an operator repairs
the file with every process that composes it stopped:

1. Copy the index file aside, unchanged, as evidence.
2. Find the longest prefix of complete, newline-terminated lines whose chain
   verifies from :data:`GENESIS` — each line parses, and its ``previous`` is
   the sha256 of the line before it (the first line's is ``GENESIS``).
3. Truncate the file to exactly that prefix, keeping its owner and mode
   ``0600``.
4. Restore the removed suffix BEFORE any reader starts — until then its
   addresses are not withheld, which is why readers stay stopped:

   - the TORN entry belongs to a completion that died inside its append, before
     the workflow resumed, so its execution is still suspended: re-run the
     door's ``complete`` with the same request and erase authorization, and the
     write-ahead protocol re-appends it;
   - every COMPLETE line after the torn one (from the evidence copy) is a valid
     entry another completion appended: re-append it, unchanged, through
     :meth:`ErasureIndexProtocol.append` under the ``ArtifactErase`` capability
     for its own request. The consult re-validates each against its record and
     its signed approval, so a line that was not genuine stays unsupported.
5. Restart.

Algorithmic module (CINV-03): no clock is read here.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import threading
from datetime import datetime
from pathlib import Path
from typing import Final, NoReturn, Protocol, runtime_checkable

from pydantic import ValidationError

from ccf.artifacts.file_store import InsecureArtifactStoreRoot, _make_private_dirs
from ccf.authz.capability import ArtifactErase, Authorized, CapabilityBypassError, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.erasure.errors import ErasureIndexCorrupt, ErasureIndexInsecure

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERASURE_INDEX_FILENAME",
    "require_append_authority",
    "GENESIS",
    "ErasureIndexEntry",
    "ErasureIndexEntryExists",
    "ErasureIndexProtocol",
    "FileErasureIndex",
    "erasure_index_at",
]

#: The conventional file name of a deployment's index beside its file-backed
#: artifact store: dot-prefixed and not a content address, so the store's
#: read path (``held_content_address``) can never serve it.
ERASURE_INDEX_FILENAME: Final[str] = ".erasure-index.jsonl"

#: The predecessor hash the FIRST line of a chain names (fix round 2 (a)).
GENESIS: Final[str] = "0" * 64


class ErasureIndexEntryExists(ValueError):
    """An already-erased ``(tenant, address)`` was offered a different entry; the index never replaces one (SEC-009; `D-IMPL-374` (4))."""


class ErasureIndexEntry(CCFContract):
    """One erased address within one tenant, naming its authority record and its request (SEC-009; `D-IMPL-374` (4)).

    Attributes:
        tenant_id: The tenant the erasure withholds within (I6).
        content_address: The erased artifact.
        erasure_record_address: The content address of the ``ccf.erasure-record``
            that is the authority for this entry.
        subject_class: The request's subject class — with ``request_id``, the
            resource the appending ``ArtifactErase`` capability is bound to (I3).
        request_id: The content identity of the erasure request it answers.
        subject_ref: The salted subject reference the record carries.
        approval_ref: The content hash of the recorded approval the record carries.
        reason: The admitted erasure reason; served only when it equals the
            record's (N2).
        erased_at: The record's ``erased_at``; served only when it equals the
            record's (N2).
        door_signature: The erasure door's detached signature
            (``protected..signature``) over the record's canonical bytes — the
            bytes the store holds at ``erasure_record_address`` (fix round 5,
            R2). Carried here rather than in the record because an ES256
            signature is not deterministic: a retried completion reuses the
            signature its prior attempt appended, so the write-ahead entries
            and the record stay byte-identical across retries (I4).
        door_key_id: The door key the signature was made under — one the
            tenant's declared authority names.
    """

    tenant_id: str
    content_address: str
    erasure_record_address: str
    subject_class: str
    request_id: str
    subject_ref: str
    approval_ref: str
    reason: str
    erased_at: datetime
    door_signature: str
    door_key_id: str


@runtime_checkable
class ErasureIndexProtocol(Protocol):
    """The append-only erasure index every store construction site declares (SEC-009; `D-IMPL-374` (4), C1).

    ``lookup`` is O(1) per ``(tenant, address)`` (I7); ``entries`` and
    ``tenants`` serve the decorating store's boot validation. ``append`` is the
    erasure door's alone (I3).
    """

    def append(self, authorized: Authorized[ArtifactErase], entry: ErasureIndexEntry) -> None:
        """Durably add ``entry`` under the erase capability for its own request; idempotent for an identical entry.

        Raises:
            ccf.authz.capability.CapabilityBypassError: ``authorized`` is not a
                genuine ``ArtifactErase`` for ``"<subject_class>/<request_id>"``
                of the entry, or is for another tenant.
            ErasureIndexEntryExists: a different entry already erases the
                address within the tenant.
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


def require_append_authority(authorized: Authorized[ArtifactErase], entry: ErasureIndexEntry) -> None:
    """The append check every index runs first (I3): the erase capability for this entry's request and tenant.

    Raises:
        ccf.authz.capability.CapabilityBypassError: anything else.
    """
    verify(authorized, kind=ArtifactErase, resource=f"{entry.subject_class}/{entry.request_id}")
    if authorized.tenant != entry.tenant_id:
        raise CapabilityBypassError(
            "the erase capability is for another tenant than the index entry it"
            " would append (SEC-009; D-IMPL-374 (4), I3)"
        )


def _private_parent(directory: Path) -> None:
    """The index's directory: created owner-only, or refused by name — the FILE STORE's policy.

    Fix round 4 (re-review M-b): the same mechanism the artifact store applies
    to its root (:func:`ccf.artifacts.file_store._make_private_dirs`). Every
    directory this call creates, intermediate parents included, is chmodded
    ``0o700``; a directory that already existed is never chmodded and is refused
    when any mode bit lies outside ``0o700`` (special bits included) or it is
    not owned by this process's effective uid.
    """
    try:
        _make_private_dirs(directory)
    except InsecureArtifactStoreRoot as loose:
        raise ErasureIndexInsecure(
            f"the erasure index's directory {str(directory)!r} must be owned by this"
            " process's user with no mode bit outside 0700 (SEC-009; fix round 2 (a);"
            f" the artifact store's root policy, SEC-014): {loose}"
        ) from loose
    except FileExistsError as not_a_directory:
        raise ErasureIndexInsecure(
            f"the erasure index's directory {str(directory)!r} is not a directory"
        ) from not_a_directory


def _private_file(path: Path) -> None:
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise ErasureIndexInsecure(
            f"the erasure index {str(path)!r} is not a regular file (a symlink is"
            " refused) (SEC-009; fix round 2 (a))"
        )
    if status.st_uid != os.geteuid() or stat.S_IMODE(status.st_mode) != 0o600:
        raise ErasureIndexInsecure(
            f"the erasure index {str(path)!r} must be owned by this process's user"
            " and mode 0600 (SEC-009; fix round 2 (a))"
        )


class FileErasureIndex:
    """The reference :class:`ErasureIndexProtocol`: a private, hash-chained, append-only JSON-lines file (SEC-009; `D-IMPL-374` (4)).

    One file per deployment, fsynced on every append. Each line is
    ``{"entry": <entry>, "previous": <sha256 of the previous line>}``.
    Entries are held in memory keyed by ``(tenant, address)`` for O(1) lookup;
    a read first picks up lines another process appended since (one ``stat``),
    holding the chain across them. A line that does not parse, or breaks the
    chain, makes the index CORRUPT: every method then raises
    :class:`~ccf.erasure.ErasureIndexCorrupt` until the file is repaired —
    an index that cannot say what is erased never serves "nothing is erased".

    Args:
        path: The index file. Its directory is created ``0700`` if absent.

    Raises:
        ccf.erasure.ErasureIndexInsecure: the file or its directory is not
            private to this process's user (fix round 2 (a)).
        ccf.erasure.ErasureIndexCorrupt: the existing file is not an unbroken chain.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        _private_parent(self._path.parent)
        _private_file(self._path)
        self._lock = threading.Lock()
        self._offset = 0
        self._head = GENESIS
        self._corrupt: str | None = None
        self._by_key: dict[tuple[str, str], ErasureIndexEntry] = {}
        self._by_tenant: dict[str, list[ErasureIndexEntry]] = {}
        with self._lock:
            self._catch_up()

    @property
    def path(self) -> Path:
        """The index file."""
        return self._path

    def _fail(self, detail: str) -> NoReturn:
        self._corrupt = detail
        raise ErasureIndexCorrupt(detail)

    def _catch_up(self) -> None:
        if self._corrupt is not None:
            raise ErasureIndexCorrupt(self._corrupt)
        try:
            descriptor = os.open(self._path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return
        except OSError as refused:
            raise ErasureIndexInsecure(
                f"the erasure index {str(self._path)!r} could not be opened without"
                f" following a link ({refused}) (SEC-009; fix round 2 (a))"
            ) from refused
        try:
            size = os.fstat(descriptor).st_size
            if size < self._offset:
                self._fail("the file shrank below what this process already read")
            if size == self._offset:
                return
            os.lseek(descriptor, self._offset, os.SEEK_SET)
            tail = b""
            while len(tail) < size - self._offset:
                chunk = os.read(descriptor, size - self._offset - len(tail))
                if not chunk:
                    break
                tail += chunk
        finally:
            os.close(descriptor)
        last = tail.rfind(b"\n")
        if last < 0:
            return  # a line still being written; read it next time
        for line in tail[:last].split(b"\n"):
            if not line.strip():
                self._fail("an empty line breaks the chain")
            try:
                parsed = json.loads(line)
                previous = parsed["previous"]
                entry = ErasureIndexEntry.model_validate(parsed["entry"])
            except (ValueError, KeyError, TypeError, ValidationError) as error:
                self._fail(f"a line does not parse ({type(error).__name__})")
            if previous != self._head:
                self._fail("a line's predecessor hash breaks the chain")
            self._head = hashlib.sha256(line).hexdigest()
            self._admit(entry)
        self._offset += last + 1

    def _admit(self, entry: ErasureIndexEntry) -> None:
        key = (entry.tenant_id, entry.content_address)
        if key in self._by_key:
            if self._by_key[key] != entry:
                self._fail("two lines erase one address with different entries")
            return
        self._by_key[key] = entry
        self._by_tenant.setdefault(entry.tenant_id, []).append(entry)

    def append(self, authorized: Authorized[ArtifactErase], entry: ErasureIndexEntry) -> None:
        require_append_authority(authorized, entry)
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
            _private_parent(self._path.parent)
            _private_file(self._path)
            descriptor = os.open(
                self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600
            )
            try:
                # One writer at a time ACROSS processes: the chain's next line
                # names the head as it stands under the lock.
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                os.fchmod(descriptor, 0o600)
                self._catch_up()
                standing = self._by_key.get((entry.tenant_id, entry.content_address))
                if standing is not None:
                    if standing == entry:
                        return
                    raise ErasureIndexEntryExists(
                        f"{entry.content_address!r} is already erased within tenant"
                        f" {entry.tenant_id!r} under another record (SEC-009; U6)"
                    )
                line = canonical_bytes({"entry": entry, "previous": self._head}) + b"\n"
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
