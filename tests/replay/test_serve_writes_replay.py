"""Delivery is unreachable without the replay append (04-RESEARCH.md Pattern 5).

Whitepaper §7.10.1 (the five inviolate dimensions, INV-CH7-79/80); CLAUDE.md
§11 ("Decision Replay is enforced at write time, not retrofitted"); DESIGN.md
§2B.5. Written before the implementation per D-15.

The structural claim under test is not "serve happens to write a record". It is
that **there is no way to obtain the delivery capability except by successfully
appending the record**: the writer *returns* the capability, and the capability
cannot be constructed any other way. A store that fails therefore produces no
delivery — not by a check someone remembered to write, but because nothing
handed the caller anything to deliver with.

Also pinned here: the file-backed ArtifactStore's content addressing, byte
round-trip, and write-once behaviour (threat T-04-11).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.gates import ServableProduct
from ccf.projection.engine import ExecutionStep
from ccf.replay.record import (
    MODE_1_MODEL_VERSION,
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    ModelVersionRecord,
    PerspectiveConditioning,
    PolicyBinding,
    PolicyBindingsSnapshot,
)
from ccf.replay.serve import DeliveryCapability, ReplayWriter, serve

TENANT = "tenant-fixture"
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
ARTIFACT_CLASS = "decision-replay-record"


def _product() -> ContextProductContract:
    return ContextProductContract(
        schema_name="fixture.exposure-summary",
        schema_version="1.0.0",
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=60),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"policy.principal-subgraph"}),
            policy_bundle_versions=frozenset({"policy-version-fixture"}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={},
    )


def _servable() -> ServableProduct:
    """A gated product, obtained the only way one can be obtained.

    This test module deliberately does not fabricate a ``ServableProduct`` by
    reaching for the gate token: the gate suite owns that boundary, and a
    replay test that forged one would be exercising a path the fabric does not
    have. The gate sequence is re-run here through its public entry point.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.contract import MaxTTL, register_product_class
    from ccf.products.gates import run_gates

    registry = ControlPlaneRegistry()
    key = "test/product/max-ttl"
    version = registry.register(key, MaxTTL(seconds=900))
    product_class = register_product_class(
        registry=registry,
        schema_name="fixture.exposure-summary",
        schema_version="1.0.0",
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=key,
        max_ttl_version=version,
    )
    gated = run_gates(
        _product(),
        engine_resolved=frozenset({"policy.principal-subgraph"}),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    return gated


def _record() -> DecisionReplayRecord:
    snapshot = ContextFabricSnapshot.build(
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        store_watermark="watermark-fixture",
        touched_entities=("counterparty://a",),
        touched_relationships=("edge://a",),
    )
    return DecisionReplayRecord(
        tenant_id=TENANT,
        recorded_at=NOW,
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
            product_content_address=content_hash(_product()),
        ),
    )


class _FailingStore:
    """A store whose append fails. Conforms to the Protocol; refuses to work."""

    def __init__(self) -> None:
        self.attempts = 0

    def put(
        self, *, tenant_id: str, artifact_class: str, name: str, artifact: object
    ) -> ArtifactRef:
        self.attempts += 1
        raise OSError("artifact store unavailable")

    def get(self, *, content_address: str) -> bytes:  # pragma: no cover
        raise KeyError(content_address)

    def exists(self, *, content_address: str) -> bool:  # pragma: no cover
        return False


# --- the replay record -----------------------------------------------------


def test_the_record_carries_all_five_dimensions() -> None:
    record = _record()
    assert record.context_fabric_snapshot.graph_snapshot_id  # 1
    assert record.policy_bindings.bindings  # 2
    assert record.model_version.model_version == MODE_1_MODEL_VERSION  # 3
    assert record.perspective_conditioning.role  # 4
    assert record.content_generation_path.steps  # 5


def test_mode_1_records_no_model() -> None:
    """Dimension 3 is literally "none" in Mode 1 (INV-CH7-83).

    Not an empty string and not an omitted field: "no model was invoked" is a
    positive claim the record makes, and an absent field would be
    indistinguishable from a record that forgot to look.
    """
    assert _record().model_version.model_version == "none"


def test_the_snapshot_is_logical_not_a_graph_copy() -> None:
    """D-IMPL-06: the id is derived, the substate is a manifest of names."""
    snapshot = _record().context_fabric_snapshot
    assert snapshot.graph_snapshot_id == ContextFabricSnapshot.build(
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
        store_watermark=snapshot.store_watermark,
        touched_entities=snapshot.touched_entities,
        touched_relationships=snapshot.touched_relationships,
    ).graph_snapshot_id
    assert snapshot.touched_entities == ("counterparty://a",)


def test_a_different_watermark_yields_a_different_snapshot_id() -> None:
    """The id must actually depend on the state it claims to identify."""
    base = _record().context_fabric_snapshot
    other = ContextFabricSnapshot.build(
        tenant_id=base.tenant_id,
        temporal_boundary=base.temporal_boundary,
        store_watermark="watermark-other",
        touched_entities=base.touched_entities,
        touched_relationships=base.touched_relationships,
    )
    assert other.graph_snapshot_id != base.graph_snapshot_id


# --- the file-backed ArtifactStore (D-IMPL-26, threat T-04-11) -------------


def test_put_addresses_by_content_hash_and_get_round_trips(tmp_path: Path) -> None:
    store = FileArtifactStore(root=tmp_path)
    record = _record()
    ref = store.put(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name="decision-1",
        artifact=record,
    )
    assert ref.content_address == content_hash(record)
    assert store.get(content_address=ref.content_address) == canonical_bytes(record)
    assert store.exists(content_address=ref.content_address)


def test_the_versioned_uri_names_the_hash_never_latest(tmp_path: Path) -> None:
    """D-IMPL-26: a replay reference stores the hash, never a moving target."""
    store = FileArtifactStore(root=tmp_path)
    ref = store.put(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name="decision-1",
        artifact=_record(),
    )
    assert ref.uri.startswith("ccf-artifact://")
    assert ref.uri.endswith(f"@{ref.content_address}")
    assert "latest" not in ref.uri


def test_identical_content_yields_one_immutable_artifact(tmp_path: Path) -> None:
    store = FileArtifactStore(root=tmp_path)
    first = store.put(
        tenant_id=TENANT, artifact_class=ARTIFACT_CLASS, name="d", artifact=_record()
    )
    before = store.get(content_address=first.content_address)
    second = store.put(
        tenant_id=TENANT, artifact_class=ARTIFACT_CLASS, name="d", artifact=_record()
    )
    assert second.content_address == first.content_address
    assert store.get(content_address=first.content_address) == before
    # Content-addressed artifacts only: the naming index is store bookkeeping
    # and is deliberately named with a leading dot so it can never collide with
    # a content address (which is hexadecimal).
    assert len([p for p in tmp_path.iterdir() if not p.name.startswith(".")]) == 1


def test_getting_an_unknown_address_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        FileArtifactStore(root=tmp_path).get(content_address="0" * 64)


# --- serve: the replay append gates delivery -------------------------------


def test_serve_writes_the_record_then_delivers(tmp_path: Path) -> None:
    store = FileArtifactStore(root=tmp_path)
    record = _record()
    served = serve(
        product=_servable(),
        record=record,
        replay_writer=ReplayWriter(store=store, artifact_class=ARTIFACT_CLASS),
    )
    assert served.product.schema_name == "fixture.exposure-summary"
    # The record is in the store, addressed by its own content, before the
    # caller ever saw a product.
    assert store.exists(content_address=served.replay_ref.content_address)
    assert served.replay_ref.content_address == content_hash(record)


def test_a_failing_store_yields_no_delivery(tmp_path: Path) -> None:
    """The repudiation threat T-04-10, closed structurally.

    The store refuses; ``serve`` raises; nothing is delivered — and there is no
    branch to audit that "forgets" the record, because the delivery capability
    is what the successful append returns.
    """
    store = _FailingStore()
    with pytest.raises(OSError):
        serve(
            product=_servable(),
            record=_record(),
            replay_writer=ReplayWriter(store=store, artifact_class=ARTIFACT_CLASS),
        )
    assert store.attempts == 1


def test_the_delivery_capability_cannot_be_constructed_directly() -> None:
    """The other half of the same claim: no capability without an append."""
    with pytest.raises(TypeError):
        DeliveryCapability(
            ArtifactRef(
                content_address="0" * 64,
                uri="ccf-artifact://t/c/n@" + "0" * 64,
                tenant_id=TENANT,
                artifact_class=ARTIFACT_CLASS,
                name="n",
            ),
            object(),
        )


def test_the_stored_record_round_trips_to_the_same_content_hash(
    tmp_path: Path,
) -> None:
    """A replay resolves the exact bytes the decision was recorded against."""
    store = FileArtifactStore(root=tmp_path)
    record = _record()
    served = serve(
        product=_servable(),
        record=record,
        replay_writer=ReplayWriter(store=store, artifact_class=ARTIFACT_CLASS),
    )
    raw = store.get(content_address=served.replay_ref.content_address)
    restored: Any = DecisionReplayRecord.model_validate_json(raw)
    assert content_hash(restored) == served.replay_ref.content_address
