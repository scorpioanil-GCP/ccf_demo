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
from ccf.artifacts.protocol import ArtifactNotFound
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


def test_f32_a_refused_composite_that_admitted_a_child_cannot_be_replayed_from_its_own_store(
    two_child_diagnostic: tuple[Any, Any, DecisionReplayRecord], tmp_path: pathlib.Path
) -> None:
    """`CP14-F-32`, measured — a STOP condition (launch-level replay defect).

    Three facts, each held here:

    1. The consumer's store holds the rows and the refusal record, not the
       admitted children's contracts: `GovernedResolver._retain_child_contracts`
       files admitted bytes on the NON-BLOCKING composition path only, and both
       diagnostic records are blocked by three unreachable required slots.
    2. The producer's own store holds its record and its query pins, never the
       served product's bytes (the record names `product_content_address`);
       the product is re-derivable there only by re-execution while the
       producer's fabric snapshot exists. No retained immutable artifact
       resolves the address anywhere.
    3. `ccf.replay.engine.replay` rebuilds the child view from the store for ANY
       record with admitted rows, so the refused parent's record is
       UNREPLAYABLE from the store that recorded it: `ReplayUnresolvable`,
       naming the admitted child's address.

    **Written to go red when the SDK is fixed**: once admitted-child bytes are
    retained on every exit (as `D-IMPL-338` made the rows survive every exit),
    the `raises` below fails and this assertion must flip with the ruling that
    closed the finding. Nothing is copied into CP-14 to repair it.
    """
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.replay.engine import ReplayUnresolvable, replay  # noqa: PLC0415

    opened, outcome, record = two_child_diagnostic
    assert isinstance(outcome, RefusalEnvelope)
    rows = _rows(record)
    consumer_store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    for product_class in ("credit-risk.spread", "reference.corporate-family"):
        with pytest.raises(ArtifactNotFound):
            consumer_store.get(content_address=rows[product_class].child_content_address)

    class _Environment:
        """The three Protocol members; replay must fail BEFORE any is consulted."""

        def resolve_plan(self, *, plan_id: str) -> Any:
            raise LookupError("not reached")

        def resolve_composite_plan(self, *, plan_id: str, children: Any) -> Any:
            raise LookupError("not reached")

        def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
            raise LookupError("not reached")

    minted = sorted(opened.scratch.glob("cp14_memo_*.sqlite3"))[-1]
    fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
    try:
        with pytest.raises(ReplayUnresolvable, match="is not retained in the store") as refused:
            replay(
                record_address=consumer_store.resolve_uri(uri=outcome.replay_reference),
                store=consumer_store, reader=fabric.handle.reader, control_plane=opened.control_plane,
                environment=_Environment(),
            )
    finally:
        fabric.handle.close()
    assert rows["credit-risk.spread"].child_content_address in str(refused.value)

    # The producer's side, for the record: its store retains no product bytes either.
    saved = {name: sys.modules.pop(name, None) for name in ("acquisition", "deployment", "produce", "projection")}
    sys.path.insert(0, str(FAMILY_EXAMPLE))
    try:
        import deployment as family_deployment  # noqa: PLC0415
        import produce as family_produce  # noqa: PLC0415

        with family_produce.product(tmp_path / "family-scratch") as family:
            asked = family.question(
                subject=BGC, asked_at=CP14_INSTANT, intent="credit-concentration", freshness="as-filed",
                parameters={family_deployment.ANCHOR: BGC, family_deployment.FAMILIES: [BGC], "debt_tolerance": Decimal("1.0")},
            )
            served = family.answer(asked)
            assert isinstance(served, ServedProduct), getattr(served, "detail", served)
            assert content_hash(served.product) == rows["reference.corporate-family"].child_content_address, "the same question, the same address"
            producer_store = FileArtifactStore(root=family.scratch / family.replay.store_dirname)
            with pytest.raises(ArtifactNotFound):
                producer_store.get(content_address=content_hash(served.product))
    finally:
        sys.path.remove(str(FAMILY_EXAMPLE))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module
