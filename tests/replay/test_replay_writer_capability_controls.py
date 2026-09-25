"""§9 controls for ``ReplayWriter`` / ``QueryPinWriter`` — D-IMPL-353 §1.3, §2 P3.

The fabric's own writers hold the one capability no door mints,
``Authorized[ReplayMint]``, obtained by the composition root through
``mint_at_composition`` and verified at construction so a mis-wired root
fails before any request. Sabotage S9 (dropping that construction-time
``verify``) and S10 (dropping the record-tenant refusal) reddened nothing in
the first pass — every replay test minted a genuine capability through the
helper. These controls are what those severings now redden.

Nothing here reaches a store's ``put`` with a bad capability on purpose: the
store's own controls (``tests/artifacts/test_write_kinds.py``) own that
tooth. What is measured here is the WRITER's: construction refuses, and a
record or query naming another tenant is refused before the store is touched.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.authz.capability import (
    ActionKind,
    ArtifactWrite,
    CapabilityBypassError,
    Execute,
    Register,
    ReplayMint,
)
from ccf.graph.protocols import GraphQuery
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
from ccf.replay.serve import QueryPinWriter, ReplayTenantMismatch, ReplayWriter
from tests.controlplane.capabilities import (
    RETARGETS,
    capability,
    fabrications,
    replay_mint,
    retarget,
)
from tests.replay.authority import replay_store

TENANT = "tenant-fixture"
RECORD_CLASS = "decision-replay-record"
QUERY_CLASS = "ccf.graph-query"
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _record(tenant: str = TENANT) -> DecisionReplayRecord:
    snapshot = ContextFabricSnapshot.build(
        tenant_id=tenant,
        temporal_boundary=NOW - timedelta(minutes=1),
        store_watermark="watermark",
        touched_entities=("counterparty://a",),
        touched_relationships=(),
    )
    return DecisionReplayRecord(
        tenant_id=tenant,
        recorded_at=NOW,
        context_fabric_snapshot=snapshot,
        policy_bindings=PolicyBindingsSnapshot(
            bindings=(PolicyBinding(key=f"{tenant}/policy-bundle/x", version="v1"),)
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


@pytest.fixture
def store(tmp_path: Path) -> FileArtifactStore:
    return replay_store(tmp_path / "artifacts", RECORD_CLASS, QUERY_CLASS)


def _substrate_untouched(store: FileArtifactStore) -> None:
    assert sorted(p.name for p in store.root.iterdir()) == []


# --- construction: the writer verifies what it is handed ------------------------------


class TestConstruction:
    def test_a_genuine_replay_mint_constructs_and_exposes_its_tenant_and_class(
        self, store: FileArtifactStore
    ) -> None:
        writer = ReplayWriter(authorized=replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS), store=store)
        assert (writer.tenant_id, writer.artifact_class) == (TENANT, RECORD_CLASS)
        pins = QueryPinWriter(authorized=replay_mint(tenant=TENANT, artifact_class=QUERY_CLASS), store=store)
        assert (pins.tenant_id, pins.artifact_class) == (TENANT, QUERY_CLASS)

    @pytest.mark.parametrize("wrong", [ArtifactWrite, Execute, Register])
    def test_a_door_kind_does_not_construct_a_replay_writer(
        self, store: FileArtifactStore, wrong: type[ActionKind]
    ) -> None:
        cap = capability(wrong, tenant=TENANT, resource=RECORD_CLASS)
        with pytest.raises(CapabilityBypassError, match="kind"):
            ReplayWriter(authorized=cast(Any, cap), store=store)
        with pytest.raises(CapabilityBypassError, match="kind"):
            QueryPinWriter(authorized=cast(Any, cap), store=store)

    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(ReplayMint, tenant=TENANT, resource=RECORD_CLASS)),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_every_fabrication_dies_at_construction(
        self, store: FileArtifactStore, label: str, fake: object
    ) -> None:
        with pytest.raises(CapabilityBypassError):
            ReplayWriter(authorized=cast(Any, fake), store=store)
        with pytest.raises(CapabilityBypassError):
            QueryPinWriter(authorized=cast(Any, fake), store=store)

    @pytest.mark.parametrize("field", sorted(RETARGETS))
    def test_a_retargeted_replay_mint_does_not_construct(
        self, store: FileArtifactStore, field: str
    ) -> None:
        cap = replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS)
        retarget(cap, field, RETARGETS[field])
        with pytest.raises(CapabilityBypassError):
            ReplayWriter(authorized=cap, store=store)

    def test_a_kind_retargeted_to_replay_mint_does_not_construct(self, store: FileArtifactStore) -> None:
        cap = capability(ArtifactWrite, tenant=TENANT, resource=RECORD_CLASS)
        retarget(cap, "kind", ReplayMint)
        assert getattr(cap, "kind") is ReplayMint  # the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            ReplayWriter(authorized=cast(Any, cap), store=store)

    def test_the_writers_take_no_class_and_no_tenant_parameter(self) -> None:
        import inspect

        for writer in (ReplayWriter, QueryPinWriter):
            params = inspect.signature(writer.__init__).parameters
            assert set(params) == {"self", "authorized", "store"}, (writer, set(params))
        assert "tenant_id" not in inspect.signature(QueryPinWriter.write_query_bytes).parameters


# --- §1.3: the tenant is the capability's, and a record may not name another -----------


class TestTenant:
    def test_a_record_naming_another_tenant_is_refused_before_the_store_is_touched(
        self, store: FileArtifactStore
    ) -> None:
        writer = ReplayWriter(authorized=replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS), store=store)
        with pytest.raises(ReplayTenantMismatch):
            writer.write_replay_record(record=_record(tenant="other-bank"))
        _substrate_untouched(store)

    def test_a_record_naming_the_capabilitys_tenant_is_filed_under_it(
        self, store: FileArtifactStore
    ) -> None:
        writer = ReplayWriter(authorized=replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS), store=store)
        delivery = writer.write_replay_record(record=_record())
        assert (delivery.replay_ref.tenant_id, delivery.replay_ref.artifact_class) == (TENANT, RECORD_CLASS)

    def test_a_query_naming_another_tenant_is_refused_before_the_store_is_touched(
        self, store: FileArtifactStore
    ) -> None:
        pins = QueryPinWriter(authorized=replay_mint(tenant=TENANT, artifact_class=QUERY_CLASS), store=store)
        foreign = GraphQuery(tenant_id="other-bank", as_of=NOW)
        with pytest.raises(ReplayTenantMismatch):
            pins.write_query_bytes(queries=(GraphQuery(tenant_id=TENANT, as_of=NOW), foreign))
        _substrate_untouched(store)
