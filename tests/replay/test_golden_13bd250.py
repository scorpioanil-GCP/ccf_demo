"""The golden ``13bd250`` record, replayed at HEAD — both legs of ``D-IMPL-243``.

Whitepaper §7.10; CLAUDE.md §7.4; ``D-IMPL-243`` (Dave: *"No pre-phase record
in ``examples/`` is why this stayed green. The fixture is the gate."*) and
its amendment 1 (*"Fixture still needs both legs: 13bd250 record matches on
marked-``True`` fields; a planted marked-``False`` field refuses by name."*).

The fixture under ``fixtures/golden_13bd250/`` was produced by the
``13bd250`` tree — the Phase 24.5 base, before any 24.5 field existed — by
the command its ``README.md`` records: a SQLite fabric, one envelope, the real
serve path, the decision record in a file-backed ArtifactStore, and a
manifest of every identity the record carries. ``produce.py`` beside it is
the deployment (plan, operators, envelope) and runs under both trees.

**Leg 1 — the match.** HEAD boots over a copy of the committed graph,
re-registers the same Control Plane documents, and ``replay()``s the record.
No :class:`~ccf.replay.engine.ReplayDivergence` and no
:class:`~ccf.replay.engine.ReplayGenerationMismatch`; the per-step
``parameter_hash`` and the ``graph_query_sequence`` pins are asserted equal
explicitly — the two hashes CR-01 named — plus the product address and the
snapshot id. Every 24.5 field the walk, the lineage and the snapshot carry
sits at its sentinel, so under "silence equals yesterday" HEAD renders the
record's walk byte-for-byte as the base tree did.

**The control.** One ``True`` mark disabled in memory — row 1,
``TraversalNeighborhoodParameters.admitted_entity_classes`` — and the same
replay raises ``ReplayDivergence`` on the parameter hash; row 3,
``TraversalSpec.direction``, and it raises on the query pins. That is CR-01
reproduced on demand, and it is what makes leg 1 evidence rather than a
test that cannot fail.

**Leg 2 — the refusal.** A ``False`` planted in memory on a field the record
lacks — row 5, ``ContextFabricSnapshot.store_snapshot_pin``, marked ``True``
in the tree — and the same replay is refused by name,
``canonical_generation_mismatch``, before a binding is resolved. This is what
the ``13bd250`` record would meet had row 5 been ticked non-transparent.

The fixture directory is never written to: every test works on a copy.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.boot import FabricHandle
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import TraversalSpec
from ccf.operators.params import TraversalNeighborhoodParameters
from ccf.replay.engine import (
    ReplayDivergence,
    ReplayGenerationMismatch,
    ReplayOutcome,
    replay,
    resolve_artifact,
)
from ccf.replay.record import ContextFabricSnapshot, DecisionReplayRecord
from tests.replay.authority import replay_store
from tests.replay.test_generation_mismatch import _key_state

FIXTURE = Path(__file__).parent / "fixtures" / "golden_13bd250"
PRODUCING_COMMIT = "13bd250e7a9d9ea12daf596ef86597557aad702f"


def _load_producer() -> Any:
    spec = importlib.util.spec_from_file_location("golden_13bd250_produce", FIXTURE / "produce.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


golden = _load_producer()


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return dict(json.loads((FIXTURE / golden.MANIFEST_FILE).read_text(encoding="utf-8")))


class _Golden:
    """A HEAD deployment over a COPY of the committed graph and store."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bindings = golden.Bindings(ControlPlaneRegistry())
        self.handle: FabricHandle = golden.boot_fabric(
            database_path=root / golden.DATABASE_FILE, bindings=self.bindings
        )
        self.store = replay_store(root / golden.ARTIFACTS_DIR, golden.ARTIFACT_CLASS)

    def replay(self, address: str) -> ReplayOutcome:
        return replay(
            record_address=address,
            store=self.store,
            reader=self.handle.reader,
            control_plane=self.bindings.registry,
            environment=golden.Environment(self.bindings),
        )


@pytest.fixture
def deployment(tmp_path: Path) -> Iterator[_Golden]:
    shutil.copytree(FIXTURE, tmp_path / "golden")
    booted = _Golden(tmp_path / "golden")
    try:
        yield booted
    finally:
        booted.handle.close()


# --- the fixture is what it says it is ------------------------------------------


def test_the_fixture_names_its_producing_commit_and_is_untouched(
    manifest: dict[str, Any],
) -> None:
    assert manifest["producing_commit"] == PRODUCING_COMMIT
    readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
    assert PRODUCING_COMMIT in readme
    assert manifest["record_content_address"] in readme
    # The record's own bytes hash to their address — untouched since 13bd250.
    payload = (FIXTURE / golden.ARTIFACTS_DIR / manifest["record_content_address"]).read_bytes()
    import hashlib

    assert hashlib.sha256(payload).hexdigest() == manifest["record_content_address"]


def test_the_record_resolves_byte_first_under_d_impl_89(
    deployment: _Golden, manifest: dict[str, Any]
) -> None:
    record = resolve_artifact(
        store=deployment.store,
        content_address=manifest["record_content_address"],
        contract=DecisionReplayRecord,
    )
    assert record.tenant_id == golden.TENANT
    assert [step.model_dump() for step in record.content_generation_path.steps] == (
        manifest["steps"]
    )
    assert list(record.content_generation_path.graph_query_sequence) == (
        manifest["graph_query_sequence"]
    )


def test_head_re_registers_the_same_control_plane_versions(
    deployment: _Golden, manifest: dict[str, Any]
) -> None:
    """Silence equals yesterday on the registered documents too (CR-01 (4)).

    The resolution spec carries three 24.5 fields on its relationship rule
    (row 10), all at their sentinels; the product class carries row 8. Every
    version HEAD mints equals the one the base tree minted, which is what
    lets ``_resolve_bindings`` find the recorded policy version at all.
    """
    assert deployment.bindings.spec_version == manifest["resolution_spec_version"]
    assert deployment.bindings.policy_version == manifest["policy_bundle_version"]
    assert deployment.bindings.max_ttl_version == manifest["max_ttl_version"]
    assert content_hash(deployment.bindings.product_class()) == (
        manifest["product_class_content_hash"]
    )


# --- leg 1: the match ----------------------------------------------------------------


def test_leg_1_the_13bd250_record_replays_at_head_with_every_hash_matching(
    deployment: _Golden, manifest: dict[str, Any]
) -> None:
    # The two hashes CR-01 named, computed by HEAD and held against the base
    # tree's, BEFORE the engine compares them for itself.
    assert content_hash(golden.traversal_parameters()) == manifest["traversal_parameter_hash"]
    execution = golden.execute(deployment.handle)
    assert [step.model_dump() for step in execution.steps] == manifest["steps"]
    assert [content_hash(query) for query in execution.executed_queries] == (
        manifest["graph_query_sequence"]
    )

    outcome = deployment.replay(manifest["record_content_address"])

    path = outcome.record.content_generation_path
    assert [step.parameter_hash for step in path.steps] == [
        step["parameter_hash"] for step in manifest["steps"]
    ]
    assert list(path.graph_query_sequence) == manifest["graph_query_sequence"]
    assert outcome.product_content_address == manifest["product_content_address"]
    assert outcome.graph_snapshot_id == manifest["graph_snapshot_id"]
    assert content_hash(outcome.product) == manifest["product_content_address"]


# --- the control: one mark off, and CR-01 is back -----------------------------------


def test_control_disabling_row_1_diverges_on_the_parameter_hash(
    deployment: _Golden, manifest: dict[str, Any]
) -> None:
    with _key_state(TraversalNeighborhoodParameters, "admitted_entity_classes", None):
        assert content_hash(golden.traversal_parameters()) != (
            manifest["traversal_parameter_hash"]
        )
        with pytest.raises(ReplayDivergence, match="differing parameter hash") as diverged:
            deployment.replay(manifest["record_content_address"])
    assert manifest["traversal_parameter_hash"] in str(diverged.value)


def test_control_disabling_row_3_diverges_on_the_query_pins(
    deployment: _Golden, manifest: dict[str, Any]
) -> None:
    with _key_state(TraversalSpec, "direction", None):
        with pytest.raises(ReplayDivergence, match="query sequence differs") as diverged:
            deployment.replay(manifest["record_content_address"])
    assert manifest["graph_query_sequence"][0] in str(diverged.value)


# --- leg 2: the refusal ---------------------------------------------------------------


def test_leg_2_a_planted_boundary_on_a_field_the_record_lacks_refuses_by_name(
    deployment: _Golden, manifest: dict[str, Any]
) -> None:
    address = manifest["record_content_address"]
    stored = json.loads(deployment.store.get(content_address=address))
    assert "store_snapshot_pin" not in stored["context_fabric_snapshot"]
    with _key_state(ContextFabricSnapshot, "store_snapshot_pin", False):
        with pytest.raises(ReplayGenerationMismatch) as refused:
            deployment.replay(address)
    assert refused.value.reason == "canonical_generation_mismatch"
    assert refused.value.fields == (
        "DecisionReplayRecord.context_fabric_snapshot.store_snapshot_pin",
    )
    assert refused.value.content_address == address
