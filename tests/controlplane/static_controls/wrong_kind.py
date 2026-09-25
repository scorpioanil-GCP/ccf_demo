"""STATIC NEGATIVE CONTROL — D-IMPL-353 §9, Lane HANDLES. This file is meant to FAIL mypy.

Checked on its own by ``tests/controlplane/test_static_controls.py``, which
asserts the EXACT diagnostics below, one per marked line. **It carries no
suppression comment and no cast** — that is the control's whole point: a
handler holding a capability of the wrong kind cannot hand it to one of the
``src/`` handles without silencing the type checker, and §4's lint refuses the
silencing.

If any marked line ever type-checks clean, the static tooth is gone for that
handle.
"""

from __future__ import annotations

from ccf.artifacts.file_store import FileArtifactStore
from ccf.authz.capability import (
    ArtifactRead,
    ArtifactWrite,
    Authorized,
    Execute,
    ReplayMint,
    SkillGrant,
    SkillRevoke,
)
from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore, StateWriteToken
from ccf.replay.serve import QueryPinWriter, ReplayWriter
from ccf.skills.grants import GrantLedger, SkillGrant as SkillGrantArtifact


def a_reader_tries_every_write_handle(
    read: Authorized[ArtifactRead],
    registry: ControlPlaneRegistry,
    state: InMemoryStateStore,
    store: FileArtifactStore,
    token: StateWriteToken,
    event: AuditEvent,
) -> None:
    registry.register(read, {"a": 1})                                   # WRONG-KIND-1
    registry.register_typed(read, {"a": 1}, artifact_class=None)        # WRONG-KIND-2
    registry.register_versioned(read, {"a": 1}, artifact_class=None)    # WRONG-KIND-3
    state.put(read, "cls", "record", record_id="r", token=token)        # WRONG-KIND-4
    store.put(read, {"a": 1})                                            # WRONG-KIND-5
    ReplayWriter(authorized=read, store=store)                           # WRONG-KIND-6
    QueryPinWriter(authorized=read, store=store)                         # WRONG-KIND-7


def the_grant_kinds_are_not_interchangeable(
    grant: Authorized[SkillGrant],
    revoke: Authorized[SkillRevoke],
    ledger: GrantLedger,
    artifact: SkillGrantArtifact,
    definition: object,
) -> None:
    ledger.request(revoke, artifact, definition=definition)              # WRONG-KIND-8
    ledger.revoke(grant)                                                 # WRONG-KIND-9


def a_client_write_is_not_a_replay_mint(
    write: Authorized[ArtifactWrite],
    execute: Authorized[Execute],
    store: FileArtifactStore,
) -> None:
    ReplayWriter(authorized=write, store=store)                          # WRONG-KIND-10
    ReplayWriter(authorized=execute, store=store)                        # WRONG-KIND-11


def the_right_kinds_are_clean(
    mint: Authorized[ReplayMint],
    write: Authorized[ArtifactWrite],
    execute: Authorized[Execute],
    grant: Authorized[SkillGrant],
    revoke: Authorized[SkillRevoke],
    store: FileArtifactStore,
    state: InMemoryStateStore,
    ledger: GrantLedger,
    artifact: SkillGrantArtifact,
    token: StateWriteToken,
) -> None:
    """The positive half, in the same file: these lines carry NO marker and
    must produce NO diagnostic, so a red above is the kind, not the file."""
    ReplayWriter(authorized=mint, store=store)
    store.put(write, {"a": 1})
    store.put(execute, {"a": 1})
    state.put(execute, "cls", "record", record_id="r", token=token)
    state.put(grant, "cls", "record", record_id="r", token=token)
    ledger.revoke(revoke)
