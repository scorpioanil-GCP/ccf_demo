"""CP-14 Gate 2, slice 2 — two independently admitted children through two paved producers.

The second producer, `examples/cp-04-canonical-corporate-family-tree`, was
re-expressed on the paved producer road (`open_product` → `open_door`, Dave's
class A) and serves `reference.corporate-family @ 2.0.0` from ANOTHER process
through `run.py --door`, exactly as the canonical spread does. This module
asks the same CP-14 composite the same first question with BOTH doors live.

What is held, exactly:

1. **The two-child diagnostic** at spread tolerance 1.0 — a diagnostic that
   lets the spread through so multi-child composition can be exercised, never
   the normal memo outcome: the canonical spread AND the family are admitted
   simultaneously, from two producer registrations under two producer tenants,
   at two producer-owned content addresses, both `provider-controls`; the
   consumer imported no producer assembler and read no child-domain store; the
   composite still refuses on the three unreachable required slots, with all
   five rows persisted.
2. **The real 0.25 result** with both doors live: the spread withholds (the
   measured estate state), the family's own answer at the memo's tolerance is
   whatever the family's producer decides, and the composite refuses — the
   production question is not raised to obtain a serve.
3. **`CP14-F-32`, measured**: on the refused composite the admitted children's
   bytes are not in the consumer's store; each admitted child's retained
   content address resolves, byte for byte, in ITS PRODUCER's own ArtifactStore
   — the same immutable address, reconstructible where the producer keeps it.

**Reads the estate, seeds nothing.**
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.examples.test_cp_03_canonical_cross_deployment import DEV_TOKEN, producer as spread_producer
from tests.examples.test_cp_14_first_slice import (
    BGC,
    BGC_FACILITY,
    CHILD_CLASSES,
    CP14_INSTANT,
    DEMONSTRATION_SPREAD_ADDRESS,
    EXAMPLE,
    UNREACHABLE,
    modules,  # noqa: F401  # the CP-14 modules, imported from their own directory
)

pytestmark = [pytest.mark.postgres, pytest.mark.fluree]

FAMILY_EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "cp-04-canonical-corporate-family-tree"
SPREAD_EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "cp-03-canonical-obligor-financial-spread"
FAMILY_RUN = FAMILY_EXAMPLE / "run.py"
FAMILY_PRODUCER_ID = "cp-04-canonical-corporate-family-tree-egress"
FAMILY_TENANT = "cp-04-canonical-demo"
SPREAD_PRODUCER_ID = "cp-03-canonical-obligor-financial-spread-egress"
SPREAD_TENANT = "cp-03-canonical-demo"

ESTATE_VARIABLES = (
    "CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA",
    "CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA",
    "CCF_CP_04C_FLUREE_URL", "CCF_CP_04C_FLUREE_LEDGER", "CCF_CP_04C_POSTGRES_DSN", "CCF_CP_04C_POSTGRES_SCHEMA",
)


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def family_producer() -> Iterator[str]:
    """The family producer process — cp-04-canonical's own paved door, `run.py --door`."""
    env = {**os.environ, "CCF_CP_04C_DOOR_TOKEN": DEV_TOKEN}
    process = subprocess.Popen(
        [sys.executable, str(FAMILY_RUN), "--door"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the family door did not announce readiness ({announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _environ(*, spread_url: str, family_url: str) -> dict[str, str]:
    return {
        "CCF_CP_14_POSTGRES_DSN": os.environ["CCF_CP_14_POSTGRES_DSN"],
        "CCF_CP_14_POSTGRES_SCHEMA": os.environ["CCF_CP_14_POSTGRES_SCHEMA"],
        "CCF_CP14_SPREAD_URL": spread_url, "CCF_CP14_SPREAD_TOKEN": DEV_TOKEN,
        "CCF_CP14_FAMILY_URL": family_url, "CCF_CP14_FAMILY_TOKEN": DEV_TOKEN,
        **{f"CCF_CP14_{name}_URL": UNREACHABLE for name in ("EXPOSURE", "COLLATERAL", "COVENANT")},
        **{f"CCF_CP14_{name}_TOKEN": "no-door-exists" for name in ("EXPOSURE", "COLLATERAL", "COVENANT")},
    }


def _ask(modules: tuple[Any, Any], scratch: pathlib.Path, *, environ: dict[str, str], tolerance: str) -> tuple[Any, Any, DecisionReplayRecord]:
    produce, deployment = modules
    with produce.product(scratch, environ=environ) as opened:
        asked = opened.question(
            subject=BGC, asked_at=CP14_INSTANT, intent="annual-review", freshness="decision-scoped",
            parameters={deployment.AS_OF: CP14_INSTANT.isoformat(), deployment.DEBT_TOLERANCE: Decimal(tolerance), deployment.FACILITY_ID: BGC_FACILITY},
        )
        outcome = opened.answer(asked)
        fresh = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        address = outcome.replay_ref.content_address if isinstance(outcome, ServedProduct) else fresh.resolve_uri(uri=outcome.replay_reference)
        return opened, outcome, DecisionReplayRecord.model_validate_json(fresh.get(content_address=address))


def _rows(record: DecisionReplayRecord) -> dict[str, Any]:
    rows = record.content_generation_path.child_resolutions
    assert [row.required_product_class for row in rows] == list(CHILD_CLASSES), rows
    return {row.required_product_class: row for row in rows}


@pytest.fixture(scope="module")
def two_child_diagnostic(modules: tuple[Any, Any], estate: None, tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any, DecisionReplayRecord]:
    """The diagnostic at spread tolerance 1.0 with BOTH doors live — asked once per module."""
    scratch = tmp_path_factory.mktemp("diag")
    with spread_producer(estate) as spread_url, family_producer() as family_url:
        return _ask(modules, scratch / "scratch", environ=_environ(spread_url=spread_url, family_url=family_url), tolerance="1.0")


def test_two_children_are_admitted_simultaneously_from_two_producers(
    two_child_diagnostic: tuple[Any, Any, DecisionReplayRecord],
) -> None:
    """Diagnostic, not the normal memo outcome: the spread is let through at 1.0
    so composition over TWO admitted remote children can be exercised."""
    opened, outcome, record = two_child_diagnostic
    rows = _rows(record)
    spread, family = rows["credit-risk.spread"], rows["reference.corporate-family"]
    # canonical spread admitted; second child admitted
    assert spread.outcome_status == "admitted" and family.outcome_status == "admitted"
    # two distinct producer registrations, two producer tenants
    assert (spread.producer_id, spread.producer_tenant) == (SPREAD_PRODUCER_ID, SPREAD_TENANT)
    assert (family.producer_id, family.producer_tenant) == (FAMILY_PRODUCER_ID, FAMILY_TENANT)
    assert spread.producer_registration_address != family.producer_registration_address
    assert spread.producer_server == "canonical-spread-producer" and family.producer_server == "canonical-family-producer"
    # two producer-owned content addresses, provider-controls for both
    assert spread.child_content_address == DEMONSTRATION_SPREAD_ADDRESS
    assert family.child_content_address is not None and family.child_content_address != spread.child_content_address
    assert spread.eligibility_basis == family.eligibility_basis == "provider-controls"
    assert spread.child_schema_version == "1.1.0" and family.child_schema_version == "2.0.0"
    assert spread.child_asked_at == family.child_asked_at == CP14_INSTANT
    # two question identities, each the producer's echo held to what was sent
    assert spread.child_question_address and family.child_question_address and spread.child_question_address != family.child_question_address
    # the producers' own replay references, retained as their claims
    assert spread.child_replay_ref is not None and spread.child_replay_ref.startswith(f"ccf-artifact://{SPREAD_TENANT}/")
    assert family.child_replay_ref is not None and family.child_replay_ref.startswith(f"ccf-artifact://{FAMILY_TENANT}/")
    # the composite still refuses: three required slots are unreachable
    assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "composite-child-refusal"
    assert all(rows[c].outcome_status == "producer-unavailable" for c in CHILD_CLASSES[2:])


def test_the_consumer_imported_no_producer_and_read_no_child_store(two_child_diagnostic: tuple[Any, Any, DecisionReplayRecord]) -> None:
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        assert not origin.startswith(str(SPREAD_EXAMPLE)), f"the spread producer's {origin} was imported into the consumer"
        assert not origin.startswith(str(FAMILY_EXAMPLE)), f"the family producer's {origin} was imported into the consumer"
    # No child-domain store is read by CP-14's own leg: its one query names the roster tables only.
    source = (EXAMPLE / "acquisition.py").read_text(encoding="utf-8")
    for table in ("financial_fact", "corporate_ownership_record", "facility", "collateral_pledge", "fibo-v2", "SPARQL"):
        assert table not in source, f"CP-14 reads child-owned material: {table}"


def test_the_same_admitted_instances_flow_into_composition(two_child_diagnostic: tuple[Any, Any, DecisionReplayRecord]) -> None:
    """The child view the parent's Π would receive is the admitted instances by
    address: the record's rows and the composition's admitted set name the same
    two addresses, and nothing else was admitted."""
    _opened, _outcome, record = two_child_diagnostic
    rows = _rows(record)
    admitted = {c: rows[c].child_content_address for c in CHILD_CLASSES if rows[c].outcome_status == "admitted"}
    assert set(admitted) == {"credit-risk.spread", "reference.corporate-family"}
    assert len(set(admitted.values())) == 2


def test_the_real_question_at_the_governed_tolerance_still_refuses_with_both_doors_live(
    tmp_path: pathlib.Path, modules: tuple[Any, Any], estate: None
) -> None:
    """The production question: 0.25, not raised. The spread withholds under the
    measured estate state; the family answers at the memo's tolerance on its own
    debt; the composite refuses. Distinct from the diagnostic, visibly."""
    with spread_producer(estate) as spread_url, family_producer() as family_url:
        _opened, outcome, record = _ask(modules, tmp_path / "scratch", environ=_environ(spread_url=spread_url, family_url=family_url), tolerance="0.25")
    assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "composite-child-refusal"
    rows = _rows(record)
    spread = rows["credit-risk.spread"]
    assert spread.outcome_status == "ineligible" and spread.producer_id == SPREAD_PRODUCER_ID
    retained = json.loads(record.content_generation_path.assembly_refusal)["detail"]
    assert "tolerance-exceeded" in retained and "no-producing-skill" not in retained, retained
    family = rows["reference.corporate-family"]
    assert family.producer_id == FAMILY_PRODUCER_ID and family.child_question_address is not None
    assert family.outcome_status in {"admitted", "ineligible"}, family.outcome_status


def test_f32_a_refused_composite_that_admitted_a_child_is_reconstructed_from_its_own_store(
    two_child_diagnostic: tuple[Any, Any, DecisionReplayRecord],
    modules: tuple[Any, Any],
    estate: None,
    tmp_path: pathlib.Path,
) -> None:
    """`CP14-F-32` — the measurement preserved, the assertion inverted (`D-IMPL-344`).

    **What was measured on 2026-09-15, and stays on the finding's row:** the
    consumer's store held the five rows and the refusal record but not the
    admitted children's contracts — `GovernedResolver._retain_child_contracts`
    filed admitted bytes on the NON-BLOCKING composition path only — while
    `ccf.replay.engine.replay` rebuilt the child view from the store for ANY
    record with admitted rows, so both diagnostic records were UNREPLAYABLE
    from the store that recorded them (`ReplayUnresolvable`, naming the
    admitted child's address); and the producer's own store never holds a
    served product's bytes, so no retained immutable artifact resolved the
    address anywhere. Classified launch-blocking; STOP; `D-IMPL-344`.

    **What is asserted now, positively, for BOTH slice-2 records** — the
    `1.0` diagnostic (spread and family admitted, three slots unreachable) and
    the real `0.25` question (family admitted, spread withheld by its producer):

    1. every admitted row's address resolves from a FRESH instance of the
       consumer's store and the bytes re-hash to it;
    2. `replay_refusal` reconstructs the refused determination from that store
       and the consumer's own fabric **after both producer processes have
       exited** — the environment handed to it raises if any member is
       consulted, so the pre-projection path provably resolves no plan and no
       operator — returning the admitted addresses, `no-fabric-read` as the
       snapshot id and the recorded refusal block re-canonicalized equal;
    3. `replay()` refuses the same record by name — a secondary check, never
       the closure: the record-kind guard alone would have turned the old
       `raises` red with retention still broken.

    Nothing is copied into CP-14. The producers' own stores still hold no
    product bytes; that is not a defect and is no longer load-bearing.
    """
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.products.contract import ContextProductContract  # noqa: PLC0415
    from ccf.replay.engine import (  # noqa: PLC0415
        RefusalReplayOutcome,
        ReplayRecordKindMismatch,
        replay,
        replay_refusal,
    )
    from ccf.replay.record import NO_FABRIC_READ  # noqa: PLC0415

    with spread_producer(estate) as spread_url, family_producer() as family_url:
        real = _ask(modules, tmp_path / "real", environ=_environ(spread_url=spread_url, family_url=family_url), tolerance="0.25")
    # Both producer processes have exited here; nothing below can reach one.

    class _NeverConsulted:
        """A refusal before projection resolves no plan, no operator, no product."""

        def resolve_plan(self, **_: Any) -> Any:
            raise AssertionError("resolve_plan was reached")

        def resolve_composite_plan(self, **_: Any) -> Any:
            raise AssertionError("resolve_composite_plan was reached")

        def resolve_operators(self, **_: Any) -> Any:
            raise AssertionError("resolve_operators was reached")

        def rehydrate_product(self, **_: Any) -> Any:
            raise AssertionError("rehydrate_product was reached")

    expected_admitted = {
        "1.0": {"credit-risk.spread", "reference.corporate-family"},
        "0.25": {"reference.corporate-family"},
    }
    for tolerance, (opened, outcome, record) in (("1.0", two_child_diagnostic), ("0.25", real)):
        assert isinstance(outcome, RefusalEnvelope), (tolerance, outcome)
        rows = _rows(record)
        admitted = {
            product_class: row.child_content_address
            for product_class, row in rows.items()
            if row.outcome_status == "admitted"
        }
        assert set(admitted) == expected_admitted[tolerance], (tolerance, admitted)
        if tolerance == "0.25":
            # The spread withheld at its producer's door crosses as `ineligible`
            # on the row, the producer's reason retained in the detail — the
            # `CP14-F-30` / `D-IMPL-342` fact, unchanged by 344.
            assert rows["credit-risk.spread"].outcome_status == "ineligible", rows["credit-risk.spread"]
        assert record.content_generation_path.plan_id == NO_FABRIC_READ

        # 1. the admitted bytes, from a fresh store instance, re-hashing to the row's address
        consumer_store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        for product_class, address in admitted.items():
            assert address, (tolerance, product_class)
            contract = ContextProductContract.model_validate_json(consumer_store.get(content_address=address))
            assert content_hash(contract) == address, (tolerance, product_class)
            assert contract.schema_name == product_class

        # 2. the refused determination, reconstructed with the producers stopped
        minted = sorted(opened.scratch.glob("cp14_memo_*.sqlite3"))[-1]
        fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
        try:
            record_address = consumer_store.resolve_uri(uri=outcome.replay_reference)
            reconstructed = replay_refusal(
                record_address=record_address,
                store=consumer_store, reader=fabric.handle.reader, control_plane=opened.control_plane,
                environment=_NeverConsulted(),
            )
            assert isinstance(reconstructed, RefusalReplayOutcome)
            assert set(reconstructed.child_contract_addresses) == set(admitted.values()), tolerance
            assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
            assert reconstructed.assembly_refusal == record.content_generation_path.assembly_refusal
            assert reconstructed.record == record
            assert reconstructed.record_content_address == record_address
            assert "product" not in type(reconstructed).model_fields

            # 3. the served entry point refuses the refused record by name (secondary)
            with pytest.raises(ReplayRecordKindMismatch):
                replay(
                    record_address=record_address,
                    store=consumer_store, reader=fabric.handle.reader, control_plane=opened.control_plane,
                    environment=_NeverConsulted(),
                )
        finally:
            fabric.handle.close()
