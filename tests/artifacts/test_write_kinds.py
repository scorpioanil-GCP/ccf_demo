"""§9 controls for ``ArtifactStoreProtocol.put`` — D-IMPL-353 §1.2, §1.3, §1.5, §2 P3.

``put(authorized, artifact)`` takes no tenant, class or name from its caller.
The kind it requires is looked up per artifact class from the store's
:class:`WriteKinds` declaration; the target comes from the capability's
resource (an addressed write, ``"<class>/<name>"``) or from the mechanism's
own :class:`DerivedWrite` (a derived write into a declared class). This module
proves, on BOTH shipped stores:

* **positive** — the right kind for the right target files under
  ``authorized.tenant`` only, and the wrapper of a derived write never reaches
  the substrate (the content address is the inner artifact's);
* **wrong kind** — a genuine capability of any other kind, including the
  client's ``ArtifactWrite`` against a declared class (the ``SEC-004`` plant),
  dies at ``verify`` with no file and no naming-index entry;
* **wrong resource** — a write capability for X cannot file Y: by retargeted
  resource (dies at ``verify``) or by presenting a ``DerivedWrite`` for an
  undeclared class (refused after ``verify``, still nothing written);
* **fabrication** and **retargeting**, every route, nothing written;
* **the MCP store refuses before the wire** — a closed port still answers the
  capability refusal, and the positive control reaches the wire.

``SEC-004``'s original measurement (a client naming its bytes into the replay
lane) is now inexpressible rather than refused: there is no name parameter to
forge into, and the replay class requires ``ReplayMint``, which no door mints.
"""

from __future__ import annotations

import inspect
import json
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from ccf.artifacts import file_store as file_store_module
from ccf.artifacts import mcp_store as mcp_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import (
    ArtifactStoreProtocol,
    ArtifactWriteRefused,
    DerivedWrite,
    WriteKinds,
    WriteKindsDeclarationError,
    authorized_write_target,
)
from ccf.authz.capability import (
    ActionKind,
    ArtifactRead,
    ArtifactWrite,
    CapabilityBypassError,
    Execute,
    HitlSubmit,
    Register,
    ReplayMint,
    Resume,
)
from ccf.contracts.canonical import canonical_bytes, content_hash
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
from tests.controlplane.capabilities import (
    RETARGETS,
    capability,
    fabrications,
    replay_mint,
    retarget,
)

# Deployment vocabulary, declared in this test the way a deployment declares it
# — the SDK enumerates no artifact class (CLAUDE.md §6.4).
REPLAY_CLASS = "ccf.replay-record"
QUERY_PIN_CLASS = "ccf.graph-query"
TRACE_CLASS = "ccf.workflow-trace"
OPEN_CLASS = "acme.analyst-scratch"

TENANT = "acme"
NAME = "snapshot-2026-09-24"
OPEN_TARGET = f"{OPEN_CLASS}/{NAME}"

CALL_TIMEOUT_SECONDS = 5.0

#: Exactly the shape a request body admits: a JSON object.
CLIENT_PAYLOAD: dict[str, object] = {"decision": "authorized the trade", "planted": True}


def _declaration() -> WriteKinds:
    return WriteKinds.declare(
        {
            REPLAY_CLASS: (ReplayMint,),
            QUERY_PIN_CLASS: (ReplayMint,),
            TRACE_CLASS: (Execute, Resume),
        }
    )


@pytest.fixture
def store(tmp_path: Path) -> FileArtifactStore:
    return FileArtifactStore(root=tmp_path / "artifacts", write_kinds=_declaration())


@pytest.fixture
def closed_url() -> str:
    """An endpoint nothing is listening on — bound and released, not guessed."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return f"http://127.0.0.1:{port}/mcp"


def _record() -> DecisionReplayRecord:
    when = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
    snapshot = ContextFabricSnapshot.build(
        tenant_id=TENANT,
        temporal_boundary=when,
        store_watermark="watermark",
        touched_entities=("counterparty://a",),
        touched_relationships=(),
    )
    return DecisionReplayRecord(
        tenant_id=TENANT,
        recorded_at=when,
        context_fabric_snapshot=snapshot,
        policy_bindings=PolicyBindingsSnapshot(
            bindings=(PolicyBinding(key=f"{TENANT}/policy-bundle/x", version="v1"),)
        ),
        model_version=ModelVersionRecord(assembly_mode="algorithmic"),
        perspective_conditioning=PerspectiveConditioning(principal_id="p", role="r"),
        content_generation_path=ContentGenerationPath(
            plan_id="plan",
            operator_plan=("policy.principal-subgraph",),
            steps=(
                ExecutionStep(
                    operator_key="policy.principal-subgraph",
                    category="policy",
                    parameter_hash="0" * 64,
                ),
            ),
            product_content_address="0" * 64,
        ),
    )


def _substrate_untouched(store: FileArtifactStore) -> None:
    """No artifact file and no naming index — byte-for-byte as constructed."""
    listed = sorted(p.name for p in store.root.iterdir())
    assert listed == [], listed


def _index(store: FileArtifactStore) -> dict[str, list[str]]:
    loaded: dict[str, list[str]] = json.loads(
        (store.root / ".artifact-names.json").read_text(encoding="utf-8")
    )
    return loaded


# --- the declaration --------------------------------------------------------------


class TestWriteKinds:
    def test_an_undeclared_class_requires_artifact_write_and_nothing_else(self) -> None:
        kinds = _declaration()
        assert kinds.for_class(OPEN_CLASS) == (ArtifactWrite,)
        assert not kinds.is_declared(OPEN_CLASS)

    def test_a_declared_class_requires_exactly_what_was_declared(self) -> None:
        kinds = _declaration()
        assert kinds.for_class(REPLAY_CLASS) == (ReplayMint,)
        assert kinds.for_class(TRACE_CLASS) == (Execute, Resume)
        assert kinds.declared_classes == frozenset({REPLAY_CLASS, QUERY_PIN_CLASS, TRACE_CLASS})

    @pytest.mark.parametrize("bad", ["", " x", "x ", "a/b"])
    def test_an_unenforceable_class_id_is_refused_at_declaration(self, bad: str) -> None:
        with pytest.raises(WriteKindsDeclarationError):
            WriteKinds.declare({bad: (ReplayMint,)})

    def test_the_separator_rule_is_about_a_real_collision(self) -> None:
        """``class="a/b", name="x"`` and ``class="a", name="b/x"`` share the
        naming key ``t/a/b/x``. The resource grammar splits at the FIRST
        separator, so the first form is not even expressible as a target —
        and a declaration that tried to reserve ``a/b`` would reserve nothing."""
        target, _ = authorized_write_target(
            capability(ArtifactWrite, tenant=TENANT, resource="a/b/x"),
            {"i": 1},
            write_kinds=WriteKinds.declare({}),
        )
        assert (target.artifact_class, target.name) == ("a", "b/x")

    def test_a_class_declared_without_a_kind_is_refused(self) -> None:
        with pytest.raises(WriteKindsDeclarationError):
            WriteKinds.declare({REPLAY_CLASS: ()})

    def test_a_declaration_may_not_name_the_client_kind(self) -> None:
        """Two lanes and no class in both — a class a door and mechanism could
        both file under is the naming lane ``SEC-004`` closed."""
        with pytest.raises(WriteKindsDeclarationError, match="ArtifactWrite"):
            WriteKinds.declare({OPEN_CLASS: (ArtifactWrite,)})

    def test_a_declaration_may_not_name_a_non_kind(self) -> None:
        with pytest.raises(WriteKindsDeclarationError):
            WriteKinds.declare({REPLAY_CLASS: cast(Any, ("replay.mint",))})

    def test_the_stores_take_the_declaration_with_no_default(self) -> None:
        for store_type in (FileArtifactStore, McpArtifactStore):
            param = inspect.signature(store_type.__init__).parameters["write_kinds"]
            assert param.default is inspect.Parameter.empty, store_type
            assert param.kind is inspect.Parameter.KEYWORD_ONLY


# --- positive ----------------------------------------------------------------------


class TestPositive:
    def test_an_addressed_client_write_files_under_the_capabilitys_tenant(
        self, store: FileArtifactStore
    ) -> None:
        authorized = capability(ArtifactWrite, tenant=TENANT, resource=OPEN_TARGET)
        ref = store.put(authorized, CLIENT_PAYLOAD)
        assert (ref.tenant_id, ref.artifact_class, ref.name) == (TENANT, OPEN_CLASS, NAME)
        assert ref.content_address == content_hash(CLIENT_PAYLOAD)
        assert ref.uri == f"ccf-artifact://{TENANT}/{OPEN_CLASS}/{NAME}@{ref.content_address}"
        assert store.resolve_uri(uri=ref.uri) == ref.content_address
        assert store.get(content_address=ref.content_address) == canonical_bytes(CLIENT_PAYLOAD)
        assert list(_index(store)) == [f"{TENANT}/{OPEN_CLASS}/{NAME}"]

    def test_the_tenant_is_the_capabilitys_whatever_the_payload_says(
        self, store: FileArtifactStore
    ) -> None:
        authorized = capability(ArtifactWrite, tenant="other-bank", resource=OPEN_TARGET)
        ref = store.put(authorized, {"tenant_id": TENANT, "claim": "not mine"})
        assert ref.tenant_id == "other-bank"
        assert list(_index(store)) == [f"other-bank/{OPEN_CLASS}/{NAME}"]

    def test_a_derived_write_under_replay_mint_files_the_inner_artifact(
        self, store: FileArtifactStore
    ) -> None:
        """§2 P3, the fabric's own writer: the composition-minted capability
        binds the class; the mechanism names the record; the wrapper never
        reaches the substrate."""
        record = _record()
        ref = store.put(
            replay_mint(tenant=TENANT, artifact_class=REPLAY_CLASS),
            DerivedWrite(artifact_class=REPLAY_CLASS, name=NAME, artifact=record),
        )
        assert (ref.tenant_id, ref.artifact_class, ref.name) == (TENANT, REPLAY_CLASS, NAME)
        assert ref.content_address == content_hash(record)
        assert store.get(content_address=ref.content_address) == canonical_bytes(record)
        assert store.resolve_uri(uri=ref.uri) == ref.content_address

    @pytest.mark.parametrize("kind", [Execute, Resume])
    def test_a_derived_write_under_either_declared_engine_kind_is_admitted(
        self, store: FileArtifactStore, kind: type[ActionKind]
    ) -> None:
        authorized = capability(kind, tenant=TENANT, resource=f"{TENANT}/ccf.workflow-definition/x")
        ref = store.put(
            authorized, DerivedWrite(artifact_class=TRACE_CLASS, name="exec-1", artifact=("t",))
        )
        assert (ref.tenant_id, ref.artifact_class, ref.name) == (TENANT, TRACE_CLASS, "exec-1")

    def test_the_two_stores_expose_the_declaration_they_were_built_with(
        self, store: FileArtifactStore, closed_url: str
    ) -> None:
        kinds = _declaration()
        assert store.write_kinds.declared_classes == kinds.declared_classes
        with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
            remote = McpArtifactStore(url=closed_url, bridge=bridge, write_kinds=kinds)
            assert remote.write_kinds is kinds
            assert isinstance(remote, ArtifactStoreProtocol)
        assert isinstance(store, ArtifactStoreProtocol)


# --- wrong kind --------------------------------------------------------------------


class TestWrongKind:
    def test_a_client_capability_cannot_write_the_replay_class(
        self, store: FileArtifactStore
    ) -> None:
        """``SEC-004``'s plant, under the capability: a genuine ``artifact.write``
        decision for ``ccf.replay-record/<name>`` — the mapping author allowed
        it — still cannot file, because the class requires ``ReplayMint``."""
        authorized = capability(ArtifactWrite, tenant=TENANT, resource=f"{REPLAY_CLASS}/{NAME}")
        with pytest.raises(CapabilityBypassError, match="kind"):
            store.put(authorized, CLIENT_PAYLOAD)
        _substrate_untouched(store)

    @pytest.mark.parametrize("wrong", [Register, ArtifactRead, Execute, HitlSubmit, ReplayMint])
    def test_a_non_client_kind_cannot_write_the_client_lane(
        self, store: FileArtifactStore, wrong: type[ActionKind]
    ) -> None:
        if wrong is ReplayMint:
            authorized: object = replay_mint(tenant=TENANT, artifact_class=OPEN_CLASS)
        else:
            authorized = capability(wrong, tenant=TENANT, resource=OPEN_TARGET)
        with pytest.raises(CapabilityBypassError, match="kind"):
            store.put(cast(Any, authorized), CLIENT_PAYLOAD)
        _substrate_untouched(store)

    def test_an_engine_kind_cannot_write_the_replay_class(self, store: FileArtifactStore) -> None:
        authorized = capability(Execute, tenant=TENANT, resource=f"{TENANT}/ccf.workflow-definition/x")
        with pytest.raises(CapabilityBypassError, match="kind"):
            store.put(authorized, DerivedWrite(artifact_class=REPLAY_CLASS, name=NAME, artifact=_record()))
        _substrate_untouched(store)

    def test_the_kind_is_checked_by_identity_not_by_subclass(self, store: FileArtifactStore) -> None:
        class LooksLikeArtifactWrite(ArtifactWrite):
            pass

        with pytest.raises(CapabilityBypassError):
            store.put(
                cast(Any, capability(LooksLikeArtifactWrite, tenant=TENANT, resource=OPEN_TARGET)),
                CLIENT_PAYLOAD,
            )
        _substrate_untouched(store)


# --- wrong resource (§1.5f) ---------------------------------------------------------


class TestWrongResource:
    def test_a_write_capability_for_x_cannot_name_y_through_a_derived_write(
        self, store: FileArtifactStore
    ) -> None:
        """The store has no name parameter; the only way to hand it another
        target is the mechanism shape, and an undeclared class refuses it."""
        authorized = capability(ArtifactWrite, tenant=TENANT, resource=OPEN_TARGET)
        with pytest.raises(ArtifactWriteRefused):
            store.put(authorized, DerivedWrite(artifact_class=OPEN_CLASS, name="other", artifact=CLIENT_PAYLOAD))
        _substrate_untouched(store)

    def test_a_write_capability_for_x_retargeted_to_y_dies_at_verify(
        self, store: FileArtifactStore
    ) -> None:
        cap = capability(ArtifactWrite, tenant=TENANT, resource=OPEN_TARGET)
        retarget(cap, "resource", f"{OPEN_CLASS}/other")
        with pytest.raises(CapabilityBypassError):
            store.put(cap, CLIENT_PAYLOAD)
        _substrate_untouched(store)

    @pytest.mark.parametrize("resource", ["", OPEN_CLASS, f"{OPEN_CLASS}/", f"/{NAME}"])
    def test_a_genuine_capability_whose_resource_is_not_a_target_is_refused_after_verify(
        self, store: FileArtifactStore, resource: str
    ) -> None:
        authorized = capability(ArtifactWrite, tenant=TENANT, resource=resource)
        with pytest.raises(ArtifactWriteRefused):
            store.put(authorized, CLIENT_PAYLOAD)
        _substrate_untouched(store)

    def test_a_replay_mint_for_one_class_may_not_derive_into_the_open_lane(
        self, store: FileArtifactStore
    ) -> None:
        """Refused at ``verify`` — the open lane's kind is ``ArtifactWrite`` and
        the capability is ``ReplayMint`` — before the shape is even considered."""
        with pytest.raises(CapabilityBypassError, match="kind"):
            store.put(
                replay_mint(tenant=TENANT, artifact_class=REPLAY_CLASS),
                DerivedWrite(artifact_class=OPEN_CLASS, name=NAME, artifact=CLIENT_PAYLOAD),
            )
        _substrate_untouched(store)


# --- fabrication ---------------------------------------------------------------------


class TestFabrication:
    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(ArtifactWrite, tenant=TENANT, resource=OPEN_TARGET)),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_every_fabrication_dies_at_verify_on_both_shapes(
        self, store: FileArtifactStore, label: str, fake: object
    ) -> None:
        with pytest.raises(CapabilityBypassError):
            store.put(cast(Any, fake), CLIENT_PAYLOAD)
        with pytest.raises(CapabilityBypassError):
            store.put(cast(Any, fake), DerivedWrite(artifact_class=REPLAY_CLASS, name=NAME, artifact=_record()))
        _substrate_untouched(store)


# --- retargeting (§1.5g) ---------------------------------------------------------------


class TestRetargeting:
    @pytest.mark.parametrize("field", sorted(RETARGETS))
    def test_a_forced_retarget_writes_nothing_under_either_target(
        self, store: FileArtifactStore, field: str
    ) -> None:
        cap = capability(ArtifactWrite, tenant=TENANT, resource=OPEN_TARGET)
        retarget(cap, field, RETARGETS[field])
        with pytest.raises(CapabilityBypassError):
            store.put(cap, CLIENT_PAYLOAD)
        _substrate_untouched(store)

    def test_a_kind_retargeted_to_replay_mint_confers_nothing(self, store: FileArtifactStore) -> None:
        cap = capability(ArtifactWrite, tenant=TENANT, resource=REPLAY_CLASS)
        retarget(cap, "kind", ReplayMint)
        assert getattr(cap, "kind") is ReplayMint  # the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            store.put(cast(Any, cap), DerivedWrite(artifact_class=REPLAY_CLASS, name=NAME, artifact=_record()))
        _substrate_untouched(store)


# --- every transport inherits the same refusal ----------------------------------------


def test_the_mcp_store_refuses_before_the_wire(closed_url: str) -> None:
    """Nothing is listening, and the answer is still the capability refusal —
    only possible if the check ran before the call left the process."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        remote = McpArtifactStore(url=closed_url, bridge=bridge, write_kinds=_declaration())
        with pytest.raises(CapabilityBypassError):
            remote.put(
                capability(ArtifactWrite, tenant=TENANT, resource=f"{REPLAY_CLASS}/{NAME}"),
                CLIENT_PAYLOAD,
            )
        with pytest.raises(CapabilityBypassError):
            remote.put(cast(Any, object()), CLIENT_PAYLOAD)


def test_the_mcp_store_still_reaches_the_wire_for_a_right_kind_write(closed_url: str) -> None:
    """The positive control: the right kind DOES dial out and fails as an
    outage, so the refusal above was not a store that had stopped working."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        remote = McpArtifactStore(url=closed_url, bridge=bridge, write_kinds=_declaration())
        with pytest.raises(McpServerUnreachable):
            remote.put(capability(ArtifactWrite, tenant=TENANT, resource=OPEN_TARGET), CLIENT_PAYLOAD)


def test_both_shipped_stores_run_the_one_shared_resolver_first() -> None:
    """A check each store spelled for itself would let the two disagree."""
    for module in (file_store_module, mcp_store_module):
        source = inspect.getsource(module)
        assert "authorized_write_target(" in source, module.__name__
        body = inspect.getsource(getattr(module, module.__all__[0]).put)
        first_statement = body.split('"""')[2].strip().splitlines()[0]
        assert "authorized_write_target(" in first_statement, first_statement


def test_put_offers_no_parameter_that_names_the_target() -> None:
    for surface in (ArtifactStoreProtocol, FileArtifactStore, McpArtifactStore):
        params = inspect.signature(surface.put).parameters
        assert list(params) == ["self", "authorized", "artifact"], (surface, list(params))


# --- no door uses the mechanism shape ------------------------------------------------


def _tracked_python_files() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[2]
    listed = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    return tuple(root / relative for relative in listed)


def test_no_transport_door_builds_a_derived_write() -> None:
    """``DerivedWrite`` is the fabric's own shape. A door — HTTP route, MCP
    body — names its target through the capability the gate minted, never by
    constructing the mechanism shape. Population named, positive control kept."""
    tracked = _tracked_python_files()
    doors = [
        p for p in tracked
        if "/runtime/ccf_runtime/http_api/" in str(p) or "/runtime/ccf_runtime/mcp/" in str(p)
    ]
    assert len(doors) > 10, len(doors)
    assert any(p.name == "artifact.py" for p in doors)
    defined = [p for p in tracked if p.name == "protocol.py" and "class DerivedWrite" in p.read_text(encoding="utf-8")]
    assert defined, "the scan found the definition nowhere — it is not measuring"
    used = [p for p in tracked if p.name == "serve.py" and "DerivedWrite(" in p.read_text(encoding="utf-8")]
    assert used, "the scan found no mechanism use — it is not measuring"
    offenders = sorted(str(p) for p in doors if "DerivedWrite(" in p.read_text(encoding="utf-8"))
    assert offenders == [], offenders
