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
    artifact_uri,
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
    """

    def __init__(self, *, root: Path | str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _path(self, content_address: str) -> Path:
        return self._root / content_address

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

    def put(
        self, *, tenant_id: str, artifact_class: str, name: str, artifact: object
    ) -> ArtifactRef:
        """Store ``artifact``; return its content-addressed reference."""
        payload = canonical_bytes(artifact)
        address = content_hash(artifact)
        target = self._path(address)
        if not target.exists():
            # Write-then-move: a reader either sees no artifact or sees the
            # whole one. A half-written replay record is worse than a missing
            # one, because it looks answerable.
            staging = target.with_name(f".{address}.{os.getpid()}.partial")
            staging.write_bytes(payload)
            staging.replace(target)
        self._register_name(
            tenant_id=tenant_id,
            artifact_class=artifact_class,
            name=name,
            address=address,
        )
        return ArtifactRef(
            content_address=address,
            uri=artifact_uri(
                tenant_id=tenant_id,
                artifact_class=artifact_class,
                name=name,
                artifact_version=address,
            ),
            tenant_id=tenant_id,
            artifact_class=artifact_class,
            name=name,
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
        """Whether an artifact is stored at ``content_address``."""
        return self._path(content_address).is_file()
