"""R-01 — the record must describe the product that is about to leave.

`D-IMPL-279` (Dave, 2026-09-08), narrowing `D-IMPL-278` row 1: *"The fabric must
establish correspondence between the candidate product, the governed execution
record, and the replay record before delivery."* And on where it belongs:
*"I would not put the primary enforcement in MCP. MCP is transport. The
canonical enforcement point should be in the governed fulfillment spine, before
transport encoding."*

**What this protects, in one sentence:** a delivery whose replay record is about
a different product than the one being delivered is refused at
:func:`~ccf.replay.serve.serve`, before anything is persisted.

**Why it is one test and not a suite.** `D-IMPL-276` asks for *one direct
regression test* naming the SDK behavior it protects, and the behavior is a
single comparison. The positive control lives inside the same test rather than
beside it, because a refusal test with no control is the failure mode this
project has recorded most often: an assertion that would pass against a
function that refused everything.

**The evidence this was needed.** Measured on cp-05 before the comparison
existed (`CP-SPEC-005` §D.10 question 1): a `ServedProduct` whose payload
claimed 9,999 family members, wrapping a replay record whose dimension 1
observed 77, crossed `ccf.products.door::served_answer` unremarked. The door
proved a record *existed* and never read it. Both operands were already inside
:func:`serve`, which already refuses a query-pin disagreement of exactly this
shape — only the comparison over the product was missing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
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
from ccf.replay.serve import ProductRecordMismatch, ReplayWriter, ServedProduct, serve
from ccf.authz.capability import Register
from tests.controlplane.capabilities import register_capability
from tests.replay.authority import replay_store, replay_writer

TENANT = "tenant-fixture"
NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
BOUNDARY = NOW - timedelta(minutes=5)
OPERATOR = "policy.principal-subgraph"
RECORD_CLASS = "ccf.test.decision-replay-record"


def _product(payload: dict[str, object]) -> ContextProductContract:
    """One contract, differing from its sibling only in payload."""
    return ContextProductContract(
        schema_name="fixture.exposure-summary",
        schema_version="1.0.0",
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=60),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({OPERATOR}),
            policy_bundle_versions=frozenset({"policy-version-fixture"}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload=payload,
    )


def _servable(product: ContextProductContract) -> ServableProduct:
    """A gated product, obtained the only way one can be obtained.

    The gate token is never reached for: a `ServableProduct` forged around the
    gates would exercise a path the fabric does not have, and this test's whole
    subject is what happens to a product the gates DID admit.
    """
    registry = ControlPlaneRegistry()
    key = "test/product/max-ttl"
    version = registry.register(register_capability(key, Register), MaxTTL(seconds=900))
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
        product,
        engine_resolved=frozenset({OPERATOR}),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    return gated


def _record_about(product: ContextProductContract) -> DecisionReplayRecord:
    """A five-dimension record whose dimension 5 addresses ``product``."""
    return DecisionReplayRecord(
        tenant_id=TENANT,
        recorded_at=NOW,
        context_fabric_snapshot=ContextFabricSnapshot.build(
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
            store_watermark="watermark-fixture",
            touched_entities=("counterparty://a",),
            touched_relationships=("edge://a",),
        ),
        policy_bindings=PolicyBindingsSnapshot(
            bindings=(PolicyBinding(key="test/policy-bundle", version="v-fixture"),)
        ),
        model_version=ModelVersionRecord(assembly_mode="algorithmic"),
        perspective_conditioning=PerspectiveConditioning(
            principal_id="analyst-1", role="credit-analyst"
        ),
        content_generation_path=ContentGenerationPath(
            plan_id="fixture.plan",
            operator_plan=(OPERATOR,),
            steps=(
                ExecutionStep(
                    operator_key=OPERATOR,
                    category="policy",
                    parameter_hash="0" * 64,
                ),
            ),
            product_content_address=content_hash(product),
        ),
    )


def test_serve_refuses_a_record_that_describes_a_different_product(
    tmp_path: Path,
) -> None:
    """The correspondence, with its control, in the order that makes both real.

    **Control first.** A record built about the product it is served with
    delivers, and the returned `ServedProduct` carries the reference of the
    record that authorized it. Without this half, a `serve` that refused every
    call would satisfy the assertion below.

    **Then the regression.** The SAME gated product, handed a record built
    about a DIFFERENT one, is refused — before any store write, which is what
    the attempt count proves. The two products differ only in payload, so the
    refusal cannot be coming from the class, the lane, the lineage or the TTL.
    """
    truth = _product({"family": {"members": 77}})
    tampered = _product({"family": {"members": 9999}})
    assert content_hash(truth) != content_hash(tampered), (
        "the two fixtures must differ, or this test measures nothing"
    )

    store = replay_store(tmp_path / "artifacts", RECORD_CLASS)
    writer = replay_writer(store, tenant=TENANT, artifact_class=RECORD_CLASS)

    # --- CONTROL: the record is about the product being served --------------
    served = serve(
        product=_servable(truth),
        record=_record_about(truth),
        replay_writer=writer,
    )
    assert isinstance(served, ServedProduct)
    assert store.exists(content_address=served.replay_ref.content_address)

    # --- REGRESSION: the record is about a different product ----------------
    # THE DELTA, NOT AN ABSOLUTE. The store keeps an index file beside its
    # content-addressed artifacts, so a count of files says more about the
    # store's bookkeeping than about this call. What must be zero is what the
    # refused call ADDED.
    before = {p for p in (tmp_path / "artifacts").rglob("*") if p.is_file()}

    with pytest.raises(ProductRecordMismatch) as refused:
        serve(
            product=_servable(tampered),
            record=_record_about(truth),
            replay_writer=writer,
        )
    detail = str(refused.value)
    assert content_hash(truth) in detail, "the refusal names what the record described"
    assert content_hash(tampered) in detail, "the refusal names what was handed in"

    # NOTHING WAS PERSISTED BY THE REFUSED CALL, which is what "before anything
    # is persisted" has to mean to be worth asserting.
    after = {p for p in (tmp_path / "artifacts").rglob("*") if p.is_file()}
    assert after == before, (
        f"the refused call persisted {[p.name for p in sorted(after - before)]}"
    )
