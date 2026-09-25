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

__all__ = ["FileArtifactStore"]

#: Filename of the naming index. Leading dot so it never collides with a
#: content address, which is always hexadecimal.
_INDEX_FILENAME = ".artifact-names.json"


class FileArtifactStore:
    """Content-addressed artifacts as files under one directory.

    Args:
        root: Directory the artifacts live in. Created if absent — a store
            that refused to initialize its own directory would push that
            concern into every caller's setup path for no gain.
        write_kinds: The deployment's declaration of which artifact classes
            are mechanism-written and under which kinds (D-IMPL-353 §1.2).
            **Required, no default**: a store whose replay class is
            undeclared refuses the fabric's own writer at first use, loudly,
            rather than leaving the lane open. Everything undeclared is the
            client lane under ``ArtifactWrite``.
    """

    def __init__(self, *, root: Path | str, write_kinds: WriteKinds) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
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
        staging.write_text(
            json.dumps(index, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
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
            staging.write_bytes(payload)
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
