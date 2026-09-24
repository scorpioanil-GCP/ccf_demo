"""Governed record classes are not client-writable (``SEC-004``).

The store's ``put`` took four values — tenant, class, name, payload — and filed
whatever it was handed. Every one of those values arrives off the wire at the
HTTP door (``runtime/ccf_runtime/http_api/routes/artifact.py``,
``ArtifactPutRequest``) and off the MCP ``put_artifact`` tool, so **a client
chose which artifact class its bytes were filed under, including the class a
deployment keeps its Decision Replay records in.**

Measured against ``a8df2959`` before this module existed, with the four values
a request body supplies and nothing else::

    put ACCEPTED -> cf129f99d0702...85e8ad2586d
    uri          -> ccf-artifact://acme/ccf.replay-record/snapshot-2026-09-24@cf129f9...
    resolve_uri  -> cf129f99d0702...85e8ad2586d
    get          -> b'{"decision":"authorized the trade","planted":true,...}'

The planted bytes were resolvable through the governed naming lane. Content
addressing does not help: it proves INTEGRITY (these bytes hash to this
address) and never PROVENANCE (who wrote them), so a replay that resolved that
URI would reproduce the plant and validate it as genuine.

**Why the repair is at the store and not at the door.** Authorizing ``put`` at
the HTTP route converts unauthorized forgery into authorized forgery — any
principal holding artifact-write could still mint a replay record — and leaves
the MCP tool, the CLI and every future transport to re-derive the same rule.
The refusal therefore lives on the write path every transport already reaches
(``ccf.artifacts.protocol.held_writable_class``), which is where
``held_content_address`` put the read-path refusal for ``D-IMPL-345`` `S-02`
and for the same reason: *"the doors are not where the substrate is touched"*.

Subject: :mod:`ccf.artifacts.protocol`, :mod:`ccf.artifacts.file_store`,
:mod:`ccf.artifacts.mcp_store`.
"""

from __future__ import annotations

import inspect
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ccf.artifacts import file_store as file_store_module
from ccf.artifacts import mcp_store as mcp_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import (
    NOTHING_GOVERNED,
    ArtifactNotFound,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    ArtifactUriUnresolvable,
    GovernedClassDeclarationError,
    GovernedRecordClasses,
    GovernedWriteForgery,
    GovernedWriteHandle,
    GovernedWriteRefused,
    GovernedWriteToken,
    held_writable_class,
)
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable
from ccf.projection.engine import ExecutionStep
from ccf.replay.record import (
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    ModelVersionRecord,
    PerspectiveConditioning,
    PolicyBinding,
    PolicyBindingsSnapshot,
)
from ccf.replay.serve import ReplayWriter

# Deployment vocabulary, declared in this test the way a deployment declares it
# — the SDK enumerates no artifact class (CLAUDE.md §6.4, the No-Hardcoding
# Rule). `ccf.replay-record` is spelled here only because THIS test is the
# deployment; `src/ccf/replay/serve.py` takes the same string as a constructor
# argument and calls it "supplied rather than assumed".
REPLAY_CLASS = "ccf.replay-record"
QUERY_PIN_CLASS = "ccf.graph-query"
OPEN_CLASS = "acme.analyst-scratch"

TENANT = "acme"
NAME = "snapshot-2026-09-24"

#: Short: every MCP call in this module is expected to fail fast against an
#: endpoint nothing is listening on.
CALL_TIMEOUT_SECONDS = 5.0

#: Exactly the shape `ArtifactPutRequest.artifact` admits: a JSON object.
CLIENT_PAYLOAD: dict[str, object] = {"decision": "authorized the trade", "planted": True}


@pytest.fixture
def governed() -> GovernedRecordClasses:
    return GovernedRecordClasses.declare(REPLAY_CLASS, QUERY_PIN_CLASS)


@pytest.fixture
def store(tmp_path: Path, governed: GovernedRecordClasses) -> FileArtifactStore:
    return FileArtifactStore(root=tmp_path / "artifacts", governed=governed)


@pytest.fixture
def closed_url() -> str:
    """An endpoint nothing is listening on — bound and released, not guessed."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return f"http://127.0.0.1:{port}/mcp"


# --- the defect, closed ----------------------------------------------------


def test_a_client_shaped_put_cannot_file_bytes_under_a_governed_class(
    store: FileArtifactStore,
) -> None:
    """The measured attack, as the HTTP door forwards it."""
    with pytest.raises(GovernedWriteRefused):
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
        )


def test_the_refusal_leaves_no_bytes_and_no_registered_name(
    store: FileArtifactStore,
) -> None:
    """Refused before canonicalization, addressing and the substrate.

    A refusal that wrote the bytes and declined only the name would still leave
    the plant retrievable by address, which is half of the attack.
    """
    with pytest.raises(GovernedWriteRefused):
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
        )
    assert store.versions(
        tenant_id=TENANT, artifact_class=REPLAY_CLASS, name=NAME
    ) == ()
    # Nothing at all was written: the store's directory holds no artifact file
    # and no naming index.
    assert sorted(p.name for p in store.root.iterdir()) == []


def test_every_governed_class_in_one_declaration_is_refused(
    store: FileArtifactStore,
) -> None:
    """Not just the first member — a declaration is a set, not a headline."""
    for governed_class in (REPLAY_CLASS, QUERY_PIN_CLASS):
        with pytest.raises(GovernedWriteRefused):
            store.put(
                tenant_id=TENANT,
                artifact_class=governed_class,
                name=NAME,
                artifact=CLIENT_PAYLOAD,
            )


def test_an_undeclared_class_is_still_client_writable(
    store: FileArtifactStore,
) -> None:
    """The positive control. A guard that refused everything would pass every
    refusal test above while breaking the store."""
    ref = store.put(
        tenant_id=TENANT,
        artifact_class=OPEN_CLASS,
        name=NAME,
        artifact=CLIENT_PAYLOAD,
    )
    assert store.get(content_address=ref.content_address)
    assert store.resolve_uri(uri=ref.uri) == ref.content_address


def test_a_store_that_declares_nothing_writes_every_class(tmp_path: Path) -> None:
    """``NOTHING_GOVERNED`` is the default, so no existing deployment changes.

    The declaration is the deployment's, and a deployment that has not made one
    is in the posture it was in before this module — which is why the
    declaration is named in the report as the thing an adopter must now add.
    """
    store = FileArtifactStore(root=tmp_path / "open")
    assert store.governed is NOTHING_GOVERNED
    ref = store.put(
        tenant_id=TENANT,
        artifact_class=REPLAY_CLASS,
        name=NAME,
        artifact=CLIENT_PAYLOAD,
    )
    assert store.resolve_uri(uri=ref.uri) == ref.content_address


# --- how the fabric's own writer still writes ------------------------------


def _record() -> DecisionReplayRecord:
    snapshot = ContextFabricSnapshot.build(
        tenant_id=TENANT,
        temporal_boundary=datetime(2026, 3, 2, 11, 59, tzinfo=UTC),
        store_watermark="watermark-fixture",
        touched_entities=("counterparty://a",),
        touched_relationships=("edge://a",),
    )
    return DecisionReplayRecord(
        tenant_id=TENANT,
        recorded_at=datetime(2026, 3, 2, 12, 0, tzinfo=UTC),
        context_fabric_snapshot=snapshot,
        policy_bindings=PolicyBindingsSnapshot(
            bindings=(PolicyBinding(key="test/policy-bundle", version="v-fixture"),)
        ),
        model_version=ModelVersionRecord(assembly_mode="algorithmic"),
        perspective_conditioning=PerspectiveConditioning(
            principal_id="analyst-1", role="credit-analyst"
        ),
        content_generation_path=ContentGenerationPath(
            plan_id="fixture.plan",
            operator_plan=("policy.principal-subgraph",),
            steps=(
                ExecutionStep(
                    operator_key="policy.principal-subgraph",
                    category="policy",
                    parameter_hash="0" * 64,
                ),
            ),
            product_content_address="a" * 64,
        ),
    )


def test_the_fabric_writes_a_governed_record_through_the_minting_handle(
    store: FileArtifactStore,
) -> None:
    minting = GovernedWriteHandle(store)
    ref = minting.put(
        tenant_id=TENANT,
        artifact_class=REPLAY_CLASS,
        name=NAME,
        artifact=CLIENT_PAYLOAD,
    )
    assert ref.artifact_class == REPLAY_CLASS
    assert store.get(content_address=ref.content_address)
    assert store.resolve_uri(uri=ref.uri) == ref.content_address


def test_the_sdks_own_replay_writer_is_unchanged_over_a_minting_handle(
    store: FileArtifactStore,
) -> None:
    """``ReplayWriter`` was not edited, and does not need to be.

    It takes an ``ArtifactStoreProtocol``; the handle IS one. The deployment
    injects the minting handle where it injects the store today — the same
    boot-time dependency injection CLAUDE.md §10 already uses to keep a write
    handle out of the wrong hands.
    """
    writer = ReplayWriter(
        store=GovernedWriteHandle(store), artifact_class=REPLAY_CLASS
    )
    record = _record()
    capability = writer.write_replay_record(record=record)
    assert capability is not None
    assert store.get(
        content_address=store.resolve_uri(
            uri=f"ccf-artifact://{TENANT}/{REPLAY_CLASS}/"
            f"{record.context_fabric_snapshot.graph_snapshot_id}@"
            f"{_only_version(store, record)}"
        )
    )


def _only_version(store: FileArtifactStore, record: DecisionReplayRecord) -> str:
    versions = store.versions(
        tenant_id=TENANT,
        artifact_class=REPLAY_CLASS,
        name=record.context_fabric_snapshot.graph_snapshot_id,
    )
    assert len(versions) == 1, versions
    return versions[0]


def test_the_same_replay_writer_over_a_bare_store_is_refused(
    store: FileArtifactStore,
) -> None:
    """The other half of the control: the handle is what authorizes, not the
    writer's identity. A ``ReplayWriter`` handed the client-facing store is
    refused exactly as a client is."""
    writer = ReplayWriter(store=store, artifact_class=REPLAY_CLASS)
    with pytest.raises(GovernedWriteRefused):
        writer.write_replay_record(record=_record())


def test_the_minting_handle_delegates_reads_unchanged(
    store: FileArtifactStore,
) -> None:
    minting = GovernedWriteHandle(store)
    ref = minting.put(
        tenant_id=TENANT, artifact_class=REPLAY_CLASS, name=NAME, artifact={"a": 1}
    )
    assert minting.get(content_address=ref.content_address) == store.get(
        content_address=ref.content_address
    )
    assert minting.exists(content_address=ref.content_address) is True
    assert minting.resolve_uri(uri=ref.uri) == ref.content_address


# --- rule 3: nothing a caller sends decides the guard ----------------------


@pytest.mark.parametrize(
    "wire_value",
    [
        True,
        1,
        "minted",
        {"_minted": True},
        [1, 2],
        SimpleNamespace(_minted=True),
        SimpleNamespace(_minted=object()),
    ],
    ids=[
        "bool",
        "int",
        "string",
        "object-naming-the-private-slot",
        "list",
        "namespace-truthy-slot",
        "namespace-foreign-sentinel",
    ],
)
def test_no_wire_shaped_value_can_mint(
    store: FileArtifactStore, wire_value: object
) -> None:
    """Every value a JSON body could carry, and two duck-typed near-misses.

    A truthiness check (``if minted:``) would pass all seven. The guard is
    identity against a module-private sentinel, so none of them mint.
    """
    with pytest.raises(GovernedWriteForgery):
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
            minted=wire_value,  # type: ignore[arg-type]
        )


def test_the_token_cannot_be_constructed_outside_its_one_producer() -> None:
    with pytest.raises(GovernedWriteForgery):
        GovernedWriteToken(object())


def test_a_subclass_that_skips_the_constructor_does_not_mint(
    store: FileArtifactStore,
) -> None:
    """``__init__`` is not the gate; the mint check is.

    :class:`ccf.controlplane.state.StateWriteToken`'s posture — the store
    verifies the mint rather than trusting the type, so a subclass that never
    ran the guarded constructor is refused at the write.
    """

    class Impostor(GovernedWriteToken):
        def __init__(self) -> None:  # deliberately does not call super()
            pass

    with pytest.raises(GovernedWriteForgery):
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
            minted=Impostor(),
        )


def test_put_offers_no_parameter_that_turns_the_guard_off() -> None:
    """The applicability of the refusal is not a caller's argument.

    ``put`` takes the four naming/payload values a request body supplies plus
    ``minted``, and ``minted``'s only effect is to require MORE authority, never
    less. There is no ``force``, no ``overwrite``, no ``governed`` override and
    no way to restate the declaration per call.
    """
    parameters = set(inspect.signature(FileArtifactStore.put).parameters)
    assert parameters == {
        "self",
        "tenant_id",
        "artifact_class",
        "name",
        "artifact",
        "minted",
    }
    for forbidden in ("force", "overwrite", "governed", "skip_governance", "unsafe"):
        assert forbidden not in parameters, forbidden


def test_the_declaration_comes_from_the_store_never_from_the_call(
    store: FileArtifactStore,
) -> None:
    """The value the guard COMPARES against is deployment-side and frozen."""
    assert store.governed.governs(REPLAY_CLASS)
    with pytest.raises(Exception):
        store.governed.class_ids.add(OPEN_CLASS)  # type: ignore[attr-defined]
    with pytest.raises(Exception):
        store.governed.class_ids = frozenset()  # type: ignore[misc]


# --- the naming lane cannot be reached around ------------------------------


def test_a_governed_class_id_containing_a_separator_is_refused_at_declaration() -> None:
    """Measured reason, not a style rule.

    The file store's naming key is ``f"{tenant}/{artifact_class}/{name}"``. With
    a slash-free class id the target key has exactly two separators, so the only
    ``(tenant, class, name)`` triple that produces it is the one naming the
    governed class — which the guard refuses. A class id containing a slash
    breaks that: ``class="a/b", name="x"`` and ``class="a", name="b/x"`` land on
    the identical key, and only the first is refused. The declaration therefore
    refuses such an id at boot, where an operator sees it, rather than admitting
    a lane with a documented bypass.
    """
    with pytest.raises(GovernedClassDeclarationError):
        GovernedRecordClasses.declare("a/b")


def test_the_separator_rule_closes_a_real_collision(tmp_path: Path) -> None:
    """The positive control for the rule above: without it, the split works."""
    store = FileArtifactStore(root=tmp_path / "s")
    left = store.put(tenant_id="t", artifact_class="a/b", name="x", artifact={"i": 1})
    right = store.put(tenant_id="t", artifact_class="a", name="b/x", artifact={"i": 2})
    # Two different triples, one naming lane — which is why a governed class id
    # is never allowed to contain the separator.
    assert store.versions(tenant_id="t", artifact_class="a/b", name="x") == (
        left.content_address,
        right.content_address,
    )


@pytest.mark.parametrize(
    "bad", ["", "   ", " ccf.replay-record", "ccf.replay-record ", "a/b", "/x"]
)
def test_a_declaration_refuses_an_unusable_class_id(bad: str) -> None:
    with pytest.raises(GovernedClassDeclarationError):
        GovernedRecordClasses.declare(bad)


def test_a_near_miss_spelling_is_admitted_and_lands_in_a_different_lane(
    store: FileArtifactStore,
) -> None:
    """Comparison is exact, deliberately.

    Normalizing (casefold, strip) would make two genuinely distinct naming
    lanes compare equal, which is a worse defect than the one it would prevent.
    A caller spelling the class differently is not refused — and gains nothing,
    because its bytes register under a key no genuine URI resolves.
    """
    near_miss = REPLAY_CLASS.upper()
    ref = store.put(
        tenant_id=TENANT, artifact_class=near_miss, name=NAME, artifact=CLIENT_PAYLOAD
    )
    assert store.versions(tenant_id=TENANT, artifact_class=REPLAY_CLASS, name=NAME) == ()
    with pytest.raises(ArtifactUriUnresolvable):
        store.resolve_uri(
            uri=f"ccf-artifact://{TENANT}/{REPLAY_CLASS}/{NAME}@{ref.content_address}"
        )


# --- the refusal does not become an oracle ---------------------------------


def test_the_refusal_does_not_vary_with_what_the_store_already_holds(
    store: FileArtifactStore,
) -> None:
    """A write refusal that leaked existence would be the read-path oracle
    ``D-IMPL-253`` amendment 2 (4) closed, rebuilt on the write path."""
    with pytest.raises(GovernedWriteRefused) as never_seen:
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
        )
    # Now make the very same bytes exist in the store, under an open class.
    store.put(
        tenant_id=TENANT,
        artifact_class=OPEN_CLASS,
        name=NAME,
        artifact=CLIENT_PAYLOAD,
    )
    with pytest.raises(GovernedWriteRefused) as already_held:
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
        )
    assert type(already_held.value) is type(never_seen.value)
    assert str(already_held.value) == str(never_seen.value)


def test_the_refusal_names_only_what_the_caller_supplied(
    store: FileArtifactStore,
) -> None:
    """R-4's rule for refusal shells, applied here: echo the caller's own
    member and recover nothing else. The message must not enumerate the
    deployment's declaration."""
    with pytest.raises(GovernedWriteRefused) as refused:
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
        )
    message = str(refused.value)
    assert REPLAY_CLASS in message
    assert QUERY_PIN_CLASS not in message
    assert NAME not in message
    assert TENANT not in message


def test_the_write_refusal_is_neither_an_absence_nor_a_substrate_failure(
    store: FileArtifactStore,
) -> None:
    """It is a determination.

    Not an :class:`ArtifactNotFound` — that would tell a caller its write
    vanished rather than that it was refused, and would be caught by every
    ``except ArtifactNotFound`` written for reads. Not an ``OSError`` — that is
    the substrate's family, and a governed refusal never reaches the substrate.
    """
    with pytest.raises(GovernedWriteRefused) as refused:
        store.put(
            tenant_id=TENANT,
            artifact_class=REPLAY_CLASS,
            name=NAME,
            artifact=CLIENT_PAYLOAD,
        )
    assert isinstance(refused.value, ArtifactStoreError)
    assert not isinstance(refused.value, ArtifactNotFound)
    assert not isinstance(refused.value, OSError)


# --- every transport inherits the same refusal -----------------------------


def test_the_mcp_store_refuses_before_the_wire(
    closed_url: str, governed: GovernedRecordClasses
) -> None:
    """Nothing is listening, and the answer is still the governed refusal —
    which is only possible if the check ran before the call left the process."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        remote = McpArtifactStore(url=closed_url, bridge=bridge, governed=governed)
        with pytest.raises(GovernedWriteRefused):
            remote.put(
                tenant_id=TENANT,
                artifact_class=REPLAY_CLASS,
                name=NAME,
                artifact=CLIENT_PAYLOAD,
            )


def test_the_mcp_store_still_reaches_the_wire_for_an_undeclared_class(
    closed_url: str, governed: GovernedRecordClasses
) -> None:
    """The positive control for the test above: an open class DOES dial out and
    fails as an outage, so the governed refusal was not an artifact of a store
    that had stopped working."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        remote = McpArtifactStore(url=closed_url, bridge=bridge, governed=governed)
        with pytest.raises(McpServerUnreachable):
            remote.put(
                tenant_id=TENANT,
                artifact_class=OPEN_CLASS,
                name=NAME,
                artifact=CLIENT_PAYLOAD,
            )


def test_both_shipped_stores_run_the_one_shared_check() -> None:
    """A refusal each store spelled for itself would let the two disagree —
    the reason ``held_content_address`` lives on the Protocol module."""
    for module in (file_store_module, mcp_store_module):
        source = inspect.getsource(module)
        assert "held_writable_class(" in source, module.__name__


def test_a_governing_store_still_conforms_to_the_protocol_structurally(
    store: FileArtifactStore, governed: GovernedRecordClasses
) -> None:
    assert isinstance(store, ArtifactStoreProtocol)
    assert isinstance(GovernedWriteHandle(store), ArtifactStoreProtocol)


def test_the_check_is_total_over_the_declaration() -> None:
    """``held_writable_class`` returns its argument unchanged when it passes —
    so a call site reads as a pass-through and cannot silently rewrite a class.
    """
    declaration = GovernedRecordClasses.declare(REPLAY_CLASS)
    assert held_writable_class(OPEN_CLASS, governed=declaration, minted=None) == (
        OPEN_CLASS
    )
    with pytest.raises(GovernedWriteRefused):
        held_writable_class(REPLAY_CLASS, governed=declaration, minted=None)


# --- no door mints ---------------------------------------------------------


def _tracked_python_files() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[2]
    listed = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return tuple(root / relative for relative in listed)


def test_no_transport_door_mints_a_governed_write() -> None:
    """The D-22-scope cover the ``StateWriteToken`` precedent promises.

    Python has no language barrier that stops a door from importing the
    minting handle; what stops a *client* is that no request body can produce
    one. This names the population and the roster so a door that started
    minting would be a failing test rather than a code review someone skipped.
    """
    tracked = _tracked_python_files()
    # Positive control 1: the population is real and includes the doors.
    runtime_files = [p for p in tracked if "/runtime/ccf_runtime/" in str(p)]
    assert len(runtime_files) > 20, len(runtime_files)
    assert any(p.name == "artifact.py" for p in runtime_files)
    # Positive control 2: the scan finds the name where it is defined.
    definition = [
        p
        for p in tracked
        if "GovernedWriteHandle" in p.read_text(encoding="utf-8")
        and p.name == "protocol.py"
    ]
    assert definition, "the scan found the name nowhere — it is not measuring"

    minting_doors = sorted(
        str(p)
        for p in runtime_files
        if "GovernedWriteHandle" in p.read_text(encoding="utf-8")
        or "GovernedWriteToken" in p.read_text(encoding="utf-8")
    )
    assert minting_doors == [], minting_doors


def test_the_governed_declaration_is_canonically_serializable() -> None:
    """It is Control Plane configuration, so it must be recordable.

    A declaration that could not be canonicalized could not be pinned into a
    replay record, and "which classes were governed when this was written" is
    exactly the kind of question replay is for.
    """
    from ccf.contracts.canonical import canonical_bytes

    declared = GovernedRecordClasses.declare(QUERY_PIN_CLASS, REPLAY_CLASS)
    assert canonical_bytes(declared) == canonical_bytes(
        GovernedRecordClasses.declare(REPLAY_CLASS, QUERY_PIN_CLASS)
    )


def test_typing_of_the_handle_is_not_any() -> None:
    """Guard against the handle degrading to ``Any`` under ``mypy --strict``."""
    assert GovernedWriteHandle.put.__annotations__["return"] is not Any
