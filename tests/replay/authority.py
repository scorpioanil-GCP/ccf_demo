"""Store and writer helpers for the replay-tree tests — D-IMPL-353 §1.2, §2 P3, test side only.

A deployment declares which artifact classes its own mechanism writes and
under which kinds (:class:`~ccf.artifacts.protocol.WriteKinds`); its
composition root mints one ``ReplayMint`` per governed class and hands each
to its writer. These helpers do exactly that for a test, so a test reads as
the deployment it stands in for and no test constructs a store with an open
replay lane.
"""

from __future__ import annotations

from pathlib import Path

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol, DerivedWrite, WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.replay.serve import QueryPinWriter, ReplayWriter
from tests.controlplane.capabilities import replay_mint

__all__ = ["mechanism_put", "pin_writer", "replay_store", "replay_writer", "write_kinds"]


def write_kinds(*classes: str) -> WriteKinds:
    """Every named class is mechanism-written under ``ReplayMint``."""
    return WriteKinds.declare({artifact_class: (ReplayMint,) for artifact_class in classes})


def replay_store(root: Path, *classes: str) -> FileArtifactStore:
    """A file store whose declared classes are ``classes``, each under ``ReplayMint``."""
    return FileArtifactStore(root=root, write_kinds=write_kinds(*classes))


def replay_writer(
    store: ArtifactStoreProtocol, *, tenant: str, artifact_class: str
) -> ReplayWriter:
    """A replay writer holding the composition-minted capability for ``artifact_class``."""
    return ReplayWriter(
        authorized=replay_mint(tenant=tenant, artifact_class=artifact_class), store=store
    )


def pin_writer(
    store: ArtifactStoreProtocol, *, tenant: str, artifact_class: str
) -> QueryPinWriter:
    """A query-pin writer holding the composition-minted capability for ``artifact_class``."""
    return QueryPinWriter(
        authorized=replay_mint(tenant=tenant, artifact_class=artifact_class), store=store
    )


def mechanism_put(
    store: ArtifactStoreProtocol,
    *,
    tenant: str,
    artifact_class: str,
    name: str,
    artifact: object,
) -> ArtifactRef:
    """File ``artifact`` the way the fabric's own mechanism does: a derived write under ``ReplayMint``.

    For tests that plant a doctored or legacy record into a governed class
    directly — the class must be declared on the store, exactly as it must
    be for the real writer.
    """
    return store.put(
        replay_mint(tenant=tenant, artifact_class=artifact_class),
        DerivedWrite(artifact_class=artifact_class, name=name, artifact=artifact),
    )
