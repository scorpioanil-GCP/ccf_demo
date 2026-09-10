"""The store head is execution provenance, not determination identity (``D-IMPL-309``).

`MOD-05` measured two runs of one governed question — same subject, same
declared instants, same policy — whose served products were byte-identical
but for the substrate's transaction-time head, ``74342`` against ``74409``.
The head sat inside :class:`~ccf.products.contract.ProductLineage`, so it sat
inside the content address, and a ledger advancing because of activity
unrelated to the question minted a new product identity. The ladder's central
claim is *same question → same answer*.

``D-IMPL-309`` rules the head **execution provenance**: recorded
authoritatively in :class:`~ccf.replay.record.ContextFabricSnapshot` and
reached through the replay reference, and absent from the sealed product and
refusal models. The reason it is *absent* rather than *excluded from the
hash* is measured, not assumed:
:func:`~ccf.contracts.canonical.canonical_bytes` is simultaneously the address
input, the persisted representation and the wire representation, so a field
omitted from it is not excluded from identity — it is **erased**, and
re-validated back into
:data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN`, which is the positive
assertion *this substrate exposes no native head*. That is a false fact
manufactured by the fabric about its own evidence.

Determination identity and execution evidence are overlapping but different
sets. What this module asserts, in both directions:

* the head is on none of the three sealed models, so no execution difference
  can reach a product address through it;
* a round trip through the canonical form manufactures no pin at all, because
  there is no field to manufacture one into;
* the head is still recorded per execution in dimension 1, still derived from
  the execution rather than from the product, and still compared at replay.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    GraphView,
    StoreSnapshotPin,
)
from ccf.products.contract import (
    ComputedEmptyFinding,
    ContextProductContract,
    ProductLineage,
)
from ccf.products.refusal import RefusalEvidence
from ccf.projection.engine import ExecutionResult, ExecutionStep, ProjectionOutput
from ccf.replay.record import ContextFabricSnapshot
from ccf.replay.snapshots import snapshot_of_execution

BOUNDARY = datetime(2026, 3, 2, 11, 59, tzinfo=UTC)
RUN_1 = StoreSnapshotPin(substrate="fluree", pin="74342")
RUN_2 = StoreSnapshotPin(substrate="fluree", pin="74409")

#: The models whose ``canonical_bytes`` are at once their address, their
#: stored form and their wire form. A store head on any of these is erased by
#: the round trip that reads it back, so ``D-IMPL-309`` puts it on none.
_SEALED = (ProductLineage, ComputedEmptyFinding, RefusalEvidence)


def _execution(pin: StoreSnapshotPin) -> ExecutionResult:
    return ExecutionResult(
        plan_id="plan-fixture",
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id="plan-fixture", payload={"k": "v"}),
        view=GraphView(tenant_id="tenant-fixture", as_of=BOUNDARY),
        store_snapshot_pin=pin,
    )


def _product() -> ContextProductContract:
    return ContextProductContract(
        schema_name="ccf.test.provenance",
        schema_version="1.0.0",
        plan_id="plan-fixture",
        tenant_id="tenant-fixture",
        temporal_boundary=BOUNDARY,
        expires_at=BOUNDARY + timedelta(seconds=60),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"policy.principal-subgraph"}),
            policy_bundle_versions=frozenset({"policy-version-fixture"}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={"exposure_state": "fixture"},
    )


# --- the head is on none of the sealed models -------------------------------


def test_no_sealed_model_declares_a_store_head() -> None:
    """Structural, and it is the whole of why an ambient head cannot move an address.

    A field that does not exist cannot be filled from an execution, so this
    single assertion does what a per-field exclusion rule would have had to
    do at every future site as well.
    """
    carrying = [
        model.__name__
        for model in _SEALED
        if "store_snapshot_pin" in model.model_fields
    ]
    assert carrying == []


def test_a_sealed_model_refuses_a_store_head_outright() -> None:
    """The sharp form: not "it is ignored" but "it cannot be said here".

    ``extra=forbid`` on :class:`~ccf.contracts.base.CCFContract` turns the
    removal into a refusal by name, so a deployment that tries to seal its
    substrate's head into an answer is told where the head belongs rather
    than having its value quietly dropped. A field merely excluded from the
    hash would have accepted this call and then erased the value on the
    round trip — which is the defect the ruling was measured against.
    """
    for model, kwargs in (
        (
            ProductLineage,
            {
                "operators_invoked": frozenset({"o"}),
                "policy_bundle_versions": frozenset({"v"}),
                "graph_snapshot_at": BOUNDARY,
            },
        ),
        (
            ComputedEmptyFinding,
            {
                "operators_returned_empty": frozenset({"o"}),
                "operators_invoked": frozenset({"o"}),
                "plan_id": "plan-fixture",
                "emptiness": "attested",
            },
        ),
        (
            RefusalEvidence,
            {"operators_invoked": frozenset({"o"}), "plan_id": "plan-fixture"},
        ),
    ):
        with pytest.raises(ValidationError, match="store_snapshot_pin"):
            model(**kwargs, store_snapshot_pin=RUN_1)  # type: ignore[arg-type]


def test_the_sealed_models_still_carry_what_the_determination_is_made_of() -> None:
    """The converse: this removed provenance, not the determination's inputs."""
    assert "graph_snapshot_at" in ProductLineage.model_fields
    assert "policy_bundle_versions" in ProductLineage.model_fields
    assert "operators_invoked" in ProductLineage.model_fields
    assert "plan_id" in ComputedEmptyFinding.model_fields
    assert "operators_invoked" in RefusalEvidence.model_fields


# --- the round trip manufactures nothing ------------------------------------


def test_a_round_trip_does_not_manufacture_a_no_pin_claim() -> None:
    """The measurement that decided the ruling, as a standing assertion.

    Under the excluded-from-the-hash reading this product came back asserting
    ``substrate='none' pin='no-store-snapshot-pin'`` — a claim about a
    substrate that nobody made and that was not true. Now there is no field
    to make it with, and the product that went out is the product that
    comes back.
    """
    sent = _product()
    wire = canonical_bytes(sent)
    assert b"store_snapshot_pin" not in wire
    assert b"no-store-snapshot-pin" not in wire
    back = ContextProductContract.model_validate_json(wire)
    assert back == sent
    assert content_hash(back) == content_hash(sent)


def test_the_governed_temporal_view_still_moves_the_address() -> None:
    """A positive control: this removed one field, not the address's meaning."""
    later = _product().model_copy(
        update={"temporal_boundary": BOUNDARY + timedelta(hours=1)}
    )
    assert content_hash(later) != content_hash(_product())


# --- and the head is still recorded, per execution --------------------------


def test_the_record_still_declares_the_head() -> None:
    assert "store_snapshot_pin" in ContextFabricSnapshot.model_fields


def test_two_ambient_heads_are_two_records() -> None:
    """Recorded, and recorded *differently* — the evidence is not flattened.

    Derived from the execution, never from the product, which is why removing
    the field from the product leaves this untouched: ``snapshot_of_execution``
    reads ``execution.store_snapshot_pin``.
    """
    first = snapshot_of_execution(
        execution=_execution(RUN_1),
        tenant_id="tenant-fixture",
        temporal_boundary=BOUNDARY,
    )
    second = snapshot_of_execution(
        execution=_execution(RUN_2),
        tenant_id="tenant-fixture",
        temporal_boundary=BOUNDARY,
    )
    assert first.store_snapshot_pin == RUN_1
    assert second.store_snapshot_pin == RUN_2
    assert first.store_snapshot_pin != second.store_snapshot_pin


def test_two_ambient_heads_are_one_graph_substate() -> None:
    """The two executions differ in NOTHING but the head, so the id agrees.

    Without this the test above would pass on two unrelated executions and
    prove nothing about ambient movement.
    """
    first = snapshot_of_execution(
        execution=_execution(RUN_1),
        tenant_id="tenant-fixture",
        temporal_boundary=BOUNDARY,
    )
    second = snapshot_of_execution(
        execution=_execution(RUN_2),
        tenant_id="tenant-fixture",
        temporal_boundary=BOUNDARY,
    )
    assert first.graph_snapshot_id == second.graph_snapshot_id


def test_a_substrate_with_no_head_still_says_so_in_the_record() -> None:
    """The sentinel keeps its meaning where the evidence lives."""
    snapshot = snapshot_of_execution(
        execution=_execution(NO_STORE_SNAPSHOT_PIN),
        tenant_id="tenant-fixture",
        temporal_boundary=BOUNDARY,
    )
    assert snapshot.store_snapshot_pin == NO_STORE_SNAPSHOT_PIN
