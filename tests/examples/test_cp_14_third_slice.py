"""CP-14 Gate 2, slice 3 — three independently admitted children through three paved producers.

The collateral slot is RE-POINTED to the paved successor
`examples/cp-06-canonical-collateral-and-setoff-coverage` (`D-GATE-cp-06-canonical`,
lane `1.0.0` by measurement). The question the slot is asked did not move: the
facility the memo's request names is the child's subject and `facility_id`, the
obligor is its borrower scope, intent `lgd-assessment`, freshness `as-filed`, no
tolerance (`CP14-F-20`). This module asks the same CP-14 composite the same first
question with THREE doors live — the canonical spread, the family, the collateral
successor — each in its own process.

What is held, exactly:

1. **The three-child diagnostic** at spread tolerance 1.0: spread, family AND
   collateral admitted simultaneously, from three producer registrations under
   three producer tenants, at three producer-owned content addresses, all
   `provider-controls`; the collateral child answers the facility the memo named;
   the composite still refuses on the two unreachable required slots
   (exposure, covenant), with all five rows persisted.
2. **The real 0.25 result** with three doors live: the spread withholds at the
   memo's tolerance (`ineligible` on the row, the producer's reason retained),
   the family and the collateral — which takes no tolerance — are admitted, and
   the composite refuses on its required spread.
3. **Both refused records reconstruct from the consumer's own store** with all
   three producer processes exited (`D-IMPL-344`): every admitted child's bytes
   retained at the row's address, `replay_refusal` returning with the admitted
   addresses, no plan, operator or product consulted.

**Reads the estate, seeds nothing.** The three producer processes read the live
estate; this module reads none of it directly.
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
from ccf.products.contract import ContextProductContract
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import NO_FABRIC_READ, DecisionReplayRecord
from tests.examples.test_cp_03_canonical_cross_deployment import DEV_TOKEN, producer as spread_producer
from tests.examples.test_cp_14_first_slice import (
    BGC,
    BGC_FACILITY,
    CHILD_CLASSES,
    CP14_INSTANT,
    EXAMPLE,
    UNREACHABLE,
    modules,  # noqa: F401  # the CP-14 modules, imported from their own directory
)
from tests.examples.test_cp_14_second_slice import (
    FAMILY_PRODUCER_ID,
    FAMILY_TENANT,
    SPREAD_PRODUCER_ID,
    SPREAD_TENANT,
    _rows,
    family_producer,
)

pytestmark = [pytest.mark.postgres, pytest.mark.fluree]

COLLATERAL_EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "cp-06-canonical-collateral-and-setoff-coverage"
COLLATERAL_RUN = COLLATERAL_EXAMPLE / "run.py"
COLLATERAL_PRODUCER_ID = "cp-06-canonical-collateral-and-setoff-coverage-egress"
COLLATERAL_TENANT = "cp-06-canonical-demo"
COLLATERAL_TOKEN_VAR = "CCF_CP_06C_DOOR_TOKEN"

ESTATE_VARIABLES = (
    "CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA", "CCF_CP_14_FLUREE_URL", "CCF_CP_14_FLUREE_LEDGER",
    "CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA",
    "CCF_CP_04C_FLUREE_URL", "CCF_CP_04C_FLUREE_LEDGER", "CCF_CP_04C_POSTGRES_DSN", "CCF_CP_04C_POSTGRES_SCHEMA",
    "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER", "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
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
def collateral_producer() -> Iterator[str]:
    """The collateral producer process — the successor's own paved door, `run.py --door`."""
    env = {**os.environ, COLLATERAL_TOKEN_VAR: DEV_TOKEN}
    process = subprocess.Popen(
        [sys.executable, str(COLLATERAL_RUN), "--door"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the collateral door did not announce readiness ({announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _environ(*, spread_url: str, family_url: str, collateral_url: str) -> dict[str, str]:
    return {
        "CCF_CP_14_POSTGRES_DSN": os.environ["CCF_CP_14_POSTGRES_DSN"],
        "CCF_CP_14_POSTGRES_SCHEMA": os.environ["CCF_CP_14_POSTGRES_SCHEMA"],
        # The ledger leg the covenant question is determined from (`CP14-F-28`),
        # named by the tree's environment document since the completion slice.
        "CCF_CP_14_FLUREE_URL": os.environ["CCF_CP_14_FLUREE_URL"],
        "CCF_CP_14_FLUREE_LEDGER": os.environ["CCF_CP_14_FLUREE_LEDGER"],
        "CCF_CP14_SPREAD_URL": spread_url, "CCF_CP14_SPREAD_TOKEN": DEV_TOKEN,
        "CCF_CP14_FAMILY_URL": family_url, "CCF_CP14_FAMILY_TOKEN": DEV_TOKEN,
        "CCF_CP14_COLLATERAL_URL": collateral_url, "CCF_CP14_COLLATERAL_TOKEN": DEV_TOKEN,
        **{f"CCF_CP14_{name}_URL": UNREACHABLE for name in ("EXPOSURE", "COVENANT")},
        **{f"CCF_CP14_{name}_TOKEN": "no-door-exists" for name in ("EXPOSURE", "COVENANT")},
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
        assert isinstance(outcome, RefusalEnvelope), outcome
        address = fresh.resolve_uri(uri=outcome.replay_reference)
        return opened, outcome, DecisionReplayRecord.model_validate_json(fresh.get(content_address=address))


@pytest.fixture(scope="module")
def both(modules: tuple[Any, Any], estate: None, tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Any, Any, DecisionReplayRecord]]:
    """Both questions with THREE doors live — asked once per module; the producer
    processes have exited by the time any test reads the results."""
    scratch = tmp_path_factory.mktemp("slice3")
    with spread_producer(estate) as spread_url, family_producer() as family_url, collateral_producer() as collateral_url:
        environ = _environ(spread_url=spread_url, family_url=family_url, collateral_url=collateral_url)
        return {
            tolerance: _ask(modules, scratch / tolerance, environ=environ, tolerance=tolerance)
            for tolerance in ("1.0", "0.25")
        }


def _retained(opened: Any, address: str) -> ContextProductContract:
    store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    contract = ContextProductContract.model_validate_json(store.get(content_address=address))
    assert content_hash(contract) == address
    return contract


def test_three_children_are_admitted_simultaneously_from_three_producers(both: dict[str, Any]) -> None:
    """The diagnostic at 1.0: spread, family and collateral admitted at once, from
    three registrations under three tenants at three producer-owned addresses,
    all `provider-controls`; the collateral child answers the facility the memo
    named; the composite still refuses on the two unreachable required slots."""
    opened, outcome, record = both["1.0"]
    rows = _rows(record)
    admitted = {c: rows[c] for c in ("credit-risk.spread", "reference.corporate-family", "credit-risk.collateral-coverage")}
    for product_class, row in admitted.items():
        assert row.outcome_status == "admitted" and row.eligibility_basis == "provider-controls", (product_class, row)
        assert row.child_content_address and row.child_asked_at == CP14_INSTANT
    assert {(r.producer_id, r.producer_tenant) for r in admitted.values()} == {
        (SPREAD_PRODUCER_ID, SPREAD_TENANT), (FAMILY_PRODUCER_ID, FAMILY_TENANT), (COLLATERAL_PRODUCER_ID, COLLATERAL_TENANT),
    }
    collateral = _retained(opened, admitted["credit-risk.collateral-coverage"].child_content_address)
    assert (collateral.schema_name, collateral.schema_version, collateral.tenant_id) == ("credit-risk.collateral-coverage", "1.0.0", COLLATERAL_TENANT)
    assert collateral.payload["facility"] == BGC_FACILITY
    assert Decimal(collateral.payload["coverage"]["coverage_ratio"]) > 0
    assert all(rows[c].outcome_status == "producer-unavailable" for c in ("credit-risk.exposure-rollup", "credit-risk.covenant-cross-reference"))
    assert outcome.kind == "composite-child-refusal"
    assert [r.required_product_class for r in record.content_generation_path.child_resolutions] == list(CHILD_CLASSES)


def test_the_real_question_admits_family_and_collateral_and_withholds_the_spread(both: dict[str, Any]) -> None:
    """At the memo's own tolerance the spread is withheld by its producer and
    crosses as `ineligible` with the reason retained (`CP14-F-30`); the family
    and the collateral — whose contract takes no tolerance — are admitted; the
    composite refuses on its required spread."""
    opened, outcome, record = both["0.25"]
    rows = _rows(record)
    assert rows["credit-risk.spread"].outcome_status == "ineligible"
    assert rows["credit-risk.spread"].refusal_ref, "the producer's reason was not retained"
    for product_class in ("reference.corporate-family", "credit-risk.collateral-coverage"):
        assert rows[product_class].outcome_status == "admitted", (product_class, rows[product_class])
        _retained(opened, rows[product_class].child_content_address)
    assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "composite-child-refusal"


def test_the_collateral_question_is_the_facility_specific_one_the_ruling_fixed(both: dict[str, Any]) -> None:
    """`CP14-F-20`: the memo names the facility; the child's subject is that
    facility; the row's question identity is the memo's, never a derived one.
    The retained child's payload is over `FAC-5B8418`, not an obligor roll-up.

    Held on BOTH the retained child and the retained question since 2026-09-18.
    The question half was added while `D-IMPL-341`'s collateral calibration was
    open and this child was refused for expired evidence — with the window
    ruled to the appraisal cycle the child is retained again, so the original
    payload assertion is restored rather than replaced, and the question
    assertion stays beside it because it proves the consumer's own half."""
    from ccf.replay.engine import retained_child_question  # noqa: PLC0415

    opened, _outcome, record = both["1.0"]
    row = _rows(record)["credit-risk.collateral-coverage"]
    assert row.child_question_address, "no question identity on the row"
    child = _retained(opened, row.child_content_address)
    assert child.payload["facility"] == BGC_FACILITY
    assert "debt_tolerance" not in child.payload.get("basis", {}), "a tolerance was invented for the collateral child"
    question = retained_child_question(store=FileArtifactStore(root=opened.scratch / opened.replay.store_dirname), row=row)
    assert content_hash(question) == row.child_question_address
    assert question.subject == BGC_FACILITY
    assert "debt_tolerance" not in json.dumps(json.loads(question.request).get("parameters", {})), "a tolerance was invented for the collateral child"


def test_the_consumer_imported_no_producer(both: dict[str, Any]) -> None:
    """No producer assembler in the consumer process — three producers, three other processes."""
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        assert not origin.startswith(str(COLLATERAL_EXAMPLE)), f"the collateral producer's {origin} was imported into the consumer"
    _opened, _outcome, record = both["1.0"]
    assert record.tenant_id == "cp-14-demo"


@pytest.mark.parametrize("tolerance,expected", [("1.0", 3), ("0.25", 2)])
def test_both_refused_records_reconstruct_with_every_admitted_child_retained(
    both: dict[str, Any], modules: tuple[Any, Any], tolerance: str, expected: int
) -> None:
    """`D-IMPL-344` on three children: with the producer processes exited, every
    admitted address resolves from a fresh store instance and re-hashes, and
    `replay_refusal` reconstructs the refused determination consulting no plan,
    operator or product; `replay()` refuses the record by name."""
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.replay.engine import RefusalReplayOutcome, ReplayRecordKindMismatch, replay, replay_refusal  # noqa: PLC0415

    opened, outcome, record = both[tolerance]
    rows = _rows(record)
    admitted = {c: r.child_content_address for c, r in rows.items() if r.outcome_status == "admitted"}
    assert len(admitted) == expected, admitted

    class _NeverConsulted:
        def resolve_plan(self, **_: Any) -> Any:
            raise AssertionError("resolve_plan was reached")

        def resolve_composite_plan(self, **_: Any) -> Any:
            raise AssertionError("resolve_composite_plan was reached")

        def resolve_operators(self, **_: Any) -> Any:
            raise AssertionError("resolve_operators was reached")

        def rehydrate_product(self, **_: Any) -> Any:
            raise AssertionError("rehydrate_product was reached")

    fresh = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    for address in admitted.values():
        assert content_hash(ContextProductContract.model_validate_json(fresh.get(content_address=address))) == address
    minted = sorted(opened.scratch.glob("cp14_memo_*.sqlite3"))[-1]
    fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
    try:
        record_address = fresh.resolve_uri(uri=outcome.replay_reference)
        reconstructed = replay_refusal(
            record_address=record_address, store=fresh, reader=fabric.handle.reader,
            control_plane=opened.control_plane, environment=_NeverConsulted(),
        )
        with pytest.raises(ReplayRecordKindMismatch):
            replay(record_address=record_address, store=fresh, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=_NeverConsulted())
    finally:
        fabric.handle.close()
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert set(reconstructed.child_contract_addresses) == set(admitted.values())
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
