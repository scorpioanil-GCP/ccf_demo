"""File-backed ArtifactStore — the development reference implementation.

SDK-defined (CLAUDE.md §7.4); D-12 scopes I.1 to the Protocol plus this
implementation, with the MCP-backed reference store arriving in I.3.

One file per artifact, named for its content address, holding the canonical
bytes and nothing else — no envelope, no metadata sidecar. A reader with the
file and the canonical serializer can verify the address itself, which is the
property that makes the store untrusted infrastructure rather than a trusted
component.

**Write-once, enforced by not writing.** If the address already exists the
bytes are by definition identical, so the store returns the reference without
touching the file. There is no code path here that opens an existing artifact
for writing, and none that removes one: an artifact that a decision was
recorded against cannot be edited out from under the replay that will look for
it years later.

**A write requires the capability for its own action (D-IMPL-353 §1.2).**
``put(authorized, artifact)`` takes no tenant, class or name from its caller:
:func:`~ccf.artifacts.protocol.authorized_write_target` runs first — before
canonicalization, before the address is derived, before any file is opened —
verifies the capability against the kinds the deployment's
:class:`~ccf.artifacts.protocol.WriteKinds` declaration names for the target
class, and resolves the target from the capability (or from the mechanism's
:class:`~ccf.artifacts.protocol.DerivedWrite`). A refused write leaves the
substrate byte-for-byte as it was: no artifact file, no naming-index entry.
The tenant is the capability's (§1.3); ``SEC-004``'s naming-lane forgery is
inexpressible rather than refused, because there is no name parameter to
forge into.

**Owner-only on disk (SEC-014, D-IMPL-368, ruling Q8).** Every regular file
the store creates is ``0o600`` and every directory it creates, intermediate
parents included, is ``0o700`` — fixed mechanism, no configuration, and
regardless of the process umask: the mode is set explicitly on the created
object (``fchmod`` on the open descriptor, ``chmod`` on the created
directory) rather than requested through ``mkdir(mode=...)`` or
``os.open(..., mode)``, which the umask masks. **A root the store did not
create is never chmodded (D-IMPL-369, Dave, 2026-10-05):** a pre-existing root
that is insecure — any mode bit outside ``0o700``, or an owner other than the
process's effective uid — is refused by name with
:class:`InsecureArtifactStoreRoot`, and the refusal leaves its permissions
byte-for-byte unchanged; a pre-existing ``0o700`` root the process owns is
used as found. Pre-existing parents are not the store's and are left as
found. A store-local ``umask`` is
deliberately not used: it is process-wide and leaks to every thread. Replay
records and Control Plane artifacts are decision evidence (CLAUDE.md §7.4);
the host's default umask is not a confidentiality posture for them.

Suitable for development, tests, and single-node deployments. Concurrency
posture is the filesystem's: the write is done to a temporary file and moved
into place, so a reader never observes a partial artifact.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ccf.artifacts.protocol import (
    ArtifactName,
    ArtifactNotFound,
    ArtifactRef,
    ArtifactUriUnresolvable,
    ArtifactWriteAuthority,
    MalformedContentAddress,
    WriteKinds,
    artifact_uri,
    authorized_write_target,
    held_content_address,
    parse_artifact_uri,
)
from ccf.contracts.canonical import canonical_bytes, content_hash

__ccf_mode__ = "algorithmic"

__all__ = ["FileArtifactStore", "InsecureArtifactStoreRoot"]

#: Filename of the naming index. Leading dot so it never collides with a
#: content address, which is always hexadecimal.
_INDEX_FILENAME = ".artifact-names.json"

#: SEC-014 / Q8: fixed owner-only modes. Ruled mechanism, not a deployment
#: knob — a parameter that could only loosen these is one a reviewer would
#: have to prove unused.
_FILE_MODE = 0o600
_DIR_MODE = 0o700


class InsecureArtifactStoreRoot(PermissionError):
    """A pre-existing store root is wider than ``0o700`` or not the process's.

    Refused by name, never repaired (D-IMPL-369, Dave, 2026-10-05: "SDK-created
    roots are owner-only. An insecure pre-existing root is refused by name,
    without chmod."). The store does not chmod a directory it did not create:
    the operator who made the root decides whether to tighten it or to point
    the store elsewhere. The message names the path, the observed mode and
    the observed owner.
    """

    def __init__(self, *, root: Path, mode: int, owner_uid: int, process_uid: int) -> None:
        self.root = root
        self.mode = mode
        self.owner_uid = owner_uid
        self.process_uid = process_uid
        reasons: list[str] = []
        if mode & ~_DIR_MODE:
            reasons.append(f"mode {oct(mode)} is wider than {oct(_DIR_MODE)}")
        if owner_uid != process_uid:
            reasons.append(f"owner uid {owner_uid} is not this process's uid {process_uid}")
        super().__init__(
            f"refusing pre-existing artifact store root {str(root)!r}: "
            + "; ".join(reasons)
            + " — the store does not change permissions it did not create (SEC-014, D-IMPL-369)"
        )


def _refuse_insecure_root(root: Path) -> None:
    """Raise :class:`InsecureArtifactStoreRoot` unless ``root`` is owner-only and ours.

    Reads the mode and owner only; never chmods (D-IMPL-369).
    """
    observed = root.stat()
    mode = observed.st_mode & 0o7777
    process_uid = os.geteuid()
    if mode & ~_DIR_MODE or observed.st_uid != process_uid:
        raise InsecureArtifactStoreRoot(
            root=root, mode=mode, owner_uid=observed.st_uid, process_uid=process_uid
        )


def _make_private_dirs(root: Path) -> None:
    """Create ``root`` and any missing parents, each set to ``0o700``.

    Only directories this call actually creates are chmodded: a parent that
    already existed (or that another process created first) is not the
    store's. A ``root`` this call did not create is checked, never chmodded:
    insecure, it is refused by name (D-IMPL-369).

    Raises:
        FileExistsError: ``root`` exists and is not a directory.
        InsecureArtifactStoreRoot: ``root`` pre-existed and is wider than
            ``0o700`` or not owned by the process's effective uid.
    """
    created: set[Path] = set()
    missing: list[Path] = []
    probe = root
    while not probe.exists():
        missing.append(probe)
        if probe.parent == probe:
            break
        probe = probe.parent
    for directory in reversed(missing):
        try:
            directory.mkdir(mode=_DIR_MODE)
        except FileExistsError:
            continue
        os.chmod(directory, _DIR_MODE)
        created.add(directory)
    if not root.is_dir():
        raise FileExistsError(f"artifact store root {root} exists and is not a directory")
    if root not in created:
        _refuse_insecure_root(root)


def _write_private(path: Path, payload: bytes) -> None:
    """Write ``payload`` to ``path`` as an owner-only (``0o600``) file.

    The mode is set on the descriptor before a byte is written, so the file
    is never observable wider than ``0o600`` — and the staging file's mode is
    the mode the target inherits on ``replace`` (SEC-014, ruling Q8).
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
    try:
        os.fchmod(fd, _FILE_MODE)
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            view = view[written:]
    finally:
        os.close(fd)


class FileArtifactStore:
    """Content-addressed artifacts as files under one directory.

    Args:
        root: Directory the artifacts live in. Created if absent — a store
            that refused to initialize its own directory would push that
            concern into every caller's setup path for no gain. Created
            (with any missing parents) ``0o700``. A root that already
            existed must be ``0o700`` (or narrower) and owned by the process,
            or construction raises :class:`InsecureArtifactStoreRoot` and
            leaves it unchanged (SEC-014, D-IMPL-369; see the module
            docstring).
        write_kinds: The deployment's declaration of which artifact classes
            are mechanism-written and under which kinds (D-IMPL-353 §1.2).
            **Required, no default**: a store whose replay class is
            undeclared refuses the fabric's own writer at first use, loudly,
            rather than leaving the lane open. Everything undeclared is the
            client lane under ``ArtifactWrite``.
    """

    def __init__(self, *, root: Path | str, write_kinds: WriteKinds) -> None:
        self._root = Path(root)
        _make_private_dirs(self._root)
        self._write_kinds = write_kinds

    @property
    def root(self) -> Path:
        return self._root

    @property
    def write_kinds(self) -> WriteKinds:
        """Which artifact classes are mechanism-written here, and by which kinds."""
        return self._write_kinds

    def _path(self, content_address: str) -> Path:
        """The file one content address names, and no other path.

        ``held_content_address`` runs FIRST, so the join below can only ever
        produce a child of the root: a 64-character hex string contains no
        separator, no ``..`` and no leading ``/`` (``D-IMPL-345`` `S-02`).
        Before it, this method was a path join over caller input, and the
        store read whatever the filesystem would give it.
        """
        return self._root / held_content_address(content_address)

    # --- the naming index (D-IMPL-26) --------------------------------------
    #
    # Naming lives on the substrate beside the artifacts, not in this object's
    # memory: a URI written into a replay record must resolve against a process
    # that never stored it, years later. An in-memory index would make the
    # versioned URI useful only to the writer.

    @property
    def _index_path(self) -> Path:
        return self._root / _INDEX_FILENAME

    @staticmethod
    def _name_key(*, tenant_id: str, artifact_class: str, name: str) -> str:
        return f"{tenant_id}/{artifact_class}/{name}"

    def _read_index(self) -> dict[str, list[str]]:
        try:
            raw = self._index_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        loaded: dict[str, list[str]] = json.loads(raw)
        return loaded

    def _write_index(self, index: dict[str, list[str]]) -> None:
        staging = self._root / f"{_INDEX_FILENAME}.{os.getpid()}.partial"
        _write_private(
            staging,
            json.dumps(index, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        staging.replace(self._index_path)

    def _register_name(
        self, *, tenant_id: str, artifact_class: str, name: str, address: str
    ) -> None:
        """Append ``address`` under its name, never replacing what is there.

        Append-only for the same reason the Control Plane registry is: a name
        whose older versions vanished when a newer one arrived would make every
        replay older than the last write unresolvable.
        """
        key = self._name_key(
            tenant_id=tenant_id, artifact_class=artifact_class, name=name
        )
        index = self._read_index()
        versions = index.setdefault(key, [])
        if address in versions:
            return
        versions.append(address)
        self._write_index(index)

    def resolve_uri(self, *, uri: str) -> str:
        """Return the content address ``uri`` names, exactly.

        Raises:
            ccf.artifacts.protocol.MovingTargetRefused: the URI asks for
                ``@latest``. Raised by the shared parser, so every store
                refuses it identically.
            ArtifactUriUnresolvable: the URI is malformed, or names a version
                that was never stored under that name. Note the scoping: a
                version registered under one name does not resolve under
                another, or the tenant and class in the URI would be
                decoration.
        """
        parsed = parse_artifact_uri(uri)
        key = self._name_key(
            tenant_id=parsed.tenant_id,
            artifact_class=parsed.artifact_class,
            name=parsed.name,
        )
        versions = self._read_index().get(key, [])
        if parsed.artifact_version not in versions:
            raise ArtifactUriUnresolvable(
                f"{uri!r} names no version this store registered under {key!r}"
            )
        return parsed.artifact_version

    def names_at(self, *, content_address: str) -> tuple[ArtifactName, ...]:
        """Every ``(tenant, class, name)`` this address was filed under, index order.

        The reverse of the naming index, for the one reader that has to know
        WHAT an address is before deciding HOW to read it: the MCP artifact
        server's hash-addressed resources (``D-IMPL-353`` §2 P5, the join's
        split) route a governed evidence class through the governed dereference
        and serve every other class tenant-scoped, and a bare content address
        says nothing about class or tenant on its own. Content addressing means
        one address may legitimately be filed under several names — the same
        bytes put twice under two names, or by two tenants — so this returns
        all of them and lets the reader take the safe direction over the names
        it may weigh: the artifact server weighs its caller's own tenant's,
        never another tenant's (C8, ``D-IMPL-376`` (6)).

        Empty for an address nothing was filed under, and empty — never a
        path read — for a string that is not a content address
        (``D-IMPL-345`` `S-02`): the shape is checked before the index is
        opened, exactly as :meth:`exists` checks it before the filesystem.
        Introspection only: holding the names confers no read of the bytes.
        """
        try:
            address = held_content_address(content_address)
        except MalformedContentAddress:
            return ()
        found: list[ArtifactName] = []
        for key, versions in self._read_index().items():
            if address not in versions:
                continue
            tenant_id, artifact_class, name = key.split("/", 2)
            found.append(
                ArtifactName(
                    tenant_id=tenant_id,
                    artifact_class=artifact_class,
                    name=name,
                    artifact_version=address,
                )
            )
        return tuple(found)

    def versions(self, *, tenant_id: str, artifact_class: str, name: str) -> tuple[
        str, ...
    ]:
        """Every version registered under one name, oldest first.

        Introspection for the CLI and for tests. Deliberately *not* a way to
        reach the newest one: it returns the whole history and makes the caller
        state which version it means.
        """
        key = self._name_key(
            tenant_id=tenant_id, artifact_class=artifact_class, name=name
        )
        return tuple(self._read_index().get(key, []))

    def put(self, authorized: ArtifactWriteAuthority, artifact: object) -> ArtifactRef:
        """Store ``artifact`` under the capability's tenant; return its content-addressed reference.

        :func:`~ccf.artifacts.protocol.authorized_write_target` runs FIRST —
        before canonicalization, before the address is derived, and before
        any file is opened — so a refused write leaves the substrate
        byte-for-byte as it was: no artifact file, no entry in the naming
        index, and nothing for a later reader to resolve. A refusal that
        wrote the bytes and declined only the name would still leave the
        plant retrievable by address, which is half of ``SEC-004``.

        Raises:
            ccf.authz.capability.CapabilityBypassError: the capability is
                fabricated, retargeted, or not of a kind that writes the
                target class.
            ccf.artifacts.protocol.ArtifactWriteRefused: the target shape.
        """
        target, payload_artifact = authorized_write_target(
            authorized, artifact, write_kinds=self._write_kinds
        )
        payload = canonical_bytes(payload_artifact)
        address = content_hash(payload_artifact)
        file = self._path(address)
        if not file.exists():
            # Write-then-move: a reader either sees no artifact or sees the
            # whole one. A half-written replay record is worse than a missing
            # one, because it looks answerable.
            staging = file.with_name(f".{address}.{os.getpid()}.partial")
            _write_private(staging, payload)
            staging.replace(file)
        self._register_name(
            tenant_id=target.tenant_id,
            artifact_class=target.artifact_class,
            name=target.name,
            address=address,
        )
        return ArtifactRef(
            content_address=address,
            uri=artifact_uri(
                tenant_id=target.tenant_id,
                artifact_class=target.artifact_class,
                name=target.name,
                artifact_version=address,
            ),
            tenant_id=target.tenant_id,
            artifact_class=target.artifact_class,
            name=target.name,
        )

    def get(self, *, content_address: str) -> bytes:
        """Return the canonical bytes stored at ``content_address``.

        Raises:
            ArtifactNotFound: nothing is stored at that address. An artifact
                error rather than a filesystem error because the caller asked
                about an artifact, not about a file — and a replay must be able
                to tell a missing record from an unreachable substrate.
        """
        target = self._path(content_address)
        try:
            return target.read_bytes()
        except FileNotFoundError:
            raise ArtifactNotFound(content_address) from None

    def exists(self, *, content_address: str) -> bool:
        """Whether an artifact is stored at ``content_address``.

        A string that is not a content address answers ``False`` rather than
        raising: this is a boolean question and *no* is the true answer for it
        (``D-IMPL-345`` `S-02`). The filesystem is still never reached — the
        shape decides — and :meth:`get`'s refusal stays typed for the caller
        that wants to tell the two apart.
        """
        try:
            target = self._path(content_address)
        except MalformedContentAddress:
            return False
        return target.is_file()
