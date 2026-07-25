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

import os
from pathlib import Path

from ccf.artifacts.protocol import ArtifactRef, artifact_uri
from ccf.contracts.canonical import canonical_bytes, content_hash

__ccf_mode__ = "algorithmic"

__all__ = ["FileArtifactStore"]


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
            KeyError: nothing is stored at that address. A ``KeyError`` rather
                than a filesystem error because the caller asked about an
                artifact, not about a file.
        """
        target = self._path(content_address)
        try:
            return target.read_bytes()
        except FileNotFoundError:
            raise KeyError(content_address) from None

    def exists(self, *, content_address: str) -> bool:
        """Whether an artifact is stored at ``content_address``."""
        return self._path(content_address).is_file()
