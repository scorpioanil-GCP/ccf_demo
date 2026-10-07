"""Frozen cp-05's exposure rollup reached through the SDK's standard door — the escape hatch, proven.

`examples/door-cp-05-credit-exposure-rollup` is a binding adapter (the CP-14
completion GO, exposure option 3): the frozen specimen's low road,
`produce.produce_governed`, presented to `open_door` through the door's own
structural contract. What this module holds is what Dave asked to be preserved
and proven through that door, from ANOTHER process, by a paved consumer holding
the same registration CP-14 holds:

* the CP-14-shaped question is admitted at the diagnostic tolerance and
  WITHHELD at the governed one — both outcomes, neither promised;
* materiality changes the presented subset, never the underlying totals;
* the declared limit regime governs the calculation, and deduplication and
  reconciliation still operate under it;
* a question at any instant but the recorded one is refused BY NAME, never
  answered at the pin and presented as the caller's;
* the door and the in-process run serve one content address;
* wrong producer id and wrong tenant refuse independently;
* a pre-resolution refusal — the `D-IMPL-304` reproduction — is a RECORDED
  governed refusal through this door, reaching the consumer as `ineligible`
  with the producer's refusal identity (closed 2026-09-18; the frozen
  specimen's own door is unchanged).

**Reads the estate, seeds nothing.** No estate figure is pinned; every
assertion is a relationship between two answers.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.erasure import ErasureTrust
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.product import OpenedProduct, open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.serve import ServedProduct
from tests.deployment.conftest import write_artifact
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import THRESHOLD_PARAMETER
from ccf.controlplane.registry import ControlPlaneRegistry

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "examples" / "door-cp-05-credit-exposure-rollup"
SPECIMEN = REPO_ROOT / "examples" / "cp-05-credit-exposure-rollup"
CONSUMER = pathlib.Path(__file__).resolve().parent / "cp_05_door_paved_consumer"
RUN = WRAPPER / "run.py"

#: The one instant the frozen tree answers at — CP-14's demonstration instant
#: coincides with it — and an instant it does not.
PIN = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
OTHER_INSTANT = PIN + timedelta(days=1)
ADMITTED_AT = PIN + timedelta(minutes=7)
BGC = "2549001IGRCG4F0RLD36"
REGIS = "5493000Q1S5TJIDIQH89"
INTENT = "internal-appetite"
GROUP_LIMIT = "group-limit-test"
FRESHNESS = "as-booked"
PRODUCT_CLASS = "credit-risk.exposure-rollup"
GOVERNED_TOLERANCE = "0.25"
DIAGNOSTIC_TOLERANCE = "1.0"

ESTATE_VARIABLES = ("CCF_CP_05_FLUREE_URL", "CCF_CP_05_FLUREE_LEDGER", "CCF_CP_05_POSTGRES_DSN", "CCF_CP_05_POSTGRES_SCHEMA")
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
PRODUCER_ID = "cp-05-credit-exposure-rollup-egress"
PRODUCER_TENANT = "cp-05-demo"
DOOR_TOKEN_VAR = "CCF_CP_05_DOOR_TOKEN"
DEV_TOKEN = "dev-token-cp-05-door"
ENDPOINT_VAR = "CCF_TEST_CP05D_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CP05D_PRODUCER_TOKEN"
DOOR: dict[str, Any] = yaml.safe_load((WRAPPER / "artifacts" / "door.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = f"the curated estate is not configured: {', '.join(missing)} unset (Fluree `fibo-v2`, PostgreSQL `ccf_v2`)"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def producer(estate: None) -> Iterator[str]:
    """The producer process — the wrapper's door, spawned via `run.py --door`."""
    env = {**os.environ, DOOR_TOKEN_VAR: DEV_TOKEN}
    process = subprocess.Popen([sys.executable, str(RUN), "--door"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the door did not announce readiness (got {announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def question_for(*, tolerance: str | None, materiality: str | None = None, intent: str = INTENT) -> Callable[[ChildRequirement, ProductRequest], ChildQuestion]:
    """The consumer's ONE mapping — CP-14's exposure question: the obligor is the
    subject and its own family, `internal-appetite`, `as-booked`, the tolerance
    the consumer holds; `materiality` only where a proof asks for it."""

    def cp14_question(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        parameters: dict[str, Any] = {"families": [request.subject]}
        if tolerance is not None:
            parameters["debt_tolerance"] = tolerance
        if materiality is not None:
            parameters["materiality"] = materiality
        return ChildQuestion(subject=request.subject, intent=intent, freshness=FRESHNESS, parameters=parameters)

    return cp14_question


def _consumer_tree(tmp_path: pathlib.Path, *, edit: Callable[[dict[str, Any]], None] | None = None) -> pathlib.Path:
    config = yaml.safe_load((CONSUMER / "ccf_config.yaml").read_text(encoding="utf-8"))
    if edit is not None:
        edit(config)
    root = tmp_path / "consumer"
    root.mkdir(parents=True)
    write_artifact(root, "ccf_config.yaml", config)
    (root / "ccf_environment.yaml").write_text((CONSUMER / "ccf_environment.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    return root


def paved_consumer(tmp_path: pathlib.Path, *, url: str, questions: Any, edit: Callable[[dict[str, Any]], None] | None = None) -> OpenedProduct:
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=_consumer_tree(tmp_path, edit=edit), scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(), project=fixture.plan_factory, assess=fixture.assess,
        questions=questions, environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN}, clock=lambda: ADMITTED_AT,
    )


def ask_consumer(opened: OpenedProduct, *, subject: str = BGC, asked_at: datetime = PIN) -> Any:
    return opened.answer(opened.question(subject=subject, asked_at=asked_at, intent="fixture-intent", freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000}))


def consumer_row(opened: OpenedProduct, outcome: Any) -> Any:
    rows = opened.record_of(outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def _retained_child(opened: OpenedProduct, row: Any) -> ContextProductContract:
    return ContextProductContract.model_validate_json(
        FileArtifactStore(root=opened.scratch / opened.replay.store_dirname).get(content_address=row.child_content_address)
    )


def through_the_door(url: str, tmp_path: pathlib.Path, *, subject: str = BGC, asked_at: datetime = PIN, edit: Any = None, **question: Any) -> tuple[Any, Any, ContextProductContract | None]:
    """One question through the door: the composite outcome, the child row, the retained child."""
    with paved_consumer(tmp_path, url=url, questions=question_for(**question), edit=edit) as opened:
        outcome = ask_consumer(opened, subject=subject, asked_at=asked_at)
        row = consumer_row(opened, outcome)
        # Retention follows ADMISSION (`D-IMPL-344`): a child refused on admission
        # may carry an address on its row and no bytes in the consumer's store.
        child = _retained_child(opened, row) if row.outcome_status == "admitted" else None
        record = opened.record_of(outcome)
    return outcome, row, child, record


@pytest.fixture(scope="module")
def door(estate: None) -> Iterator[str]:
    with producer(estate) as url:
        yield url


@pytest.fixture(scope="module")
def admitted(door: str, tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any, ContextProductContract, Any]:
    """The CP-14-shaped question for BGC at the DIAGNOSTIC tolerance, through the door."""
    outcome, row, child, record = through_the_door(door, tmp_path_factory.mktemp("admitted"), tolerance=DIAGNOSTIC_TOLERANCE)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
    assert child is not None
    return outcome, row, child, record


def _direct(**question: Any) -> Any:
    """The frozen specimen's low road, in-process: the same call the adapter makes."""
    saved = {n: sys.modules.pop(n, None) for n in ("deployment", "produce", "assembler", "projection")}
    sys.path.insert(0, str(SPECIMEN))
    try:
        import produce  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as scratch:
            _payload, governed, _record = produce.produce_governed(replay_root=pathlib.Path(scratch) / "replay", **question)
            return governed
    finally:
        sys.path.remove(str(SPECIMEN))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


# --- both outcomes, neither promised ---------------------------------------------------


def test_the_cp14_question_is_admitted_through_the_door_at_the_diagnostic_tolerance(admitted: Any) -> None:
    """At the labeled diagnostic tolerance the frozen producer SERVES, and the
    paved consumer admits the child under the registration's identity with
    `provider-controls`: the retained child is cp-05's own contract, minted under
    cp-05's tenant at the recorded instant, about the obligor asked."""
    _outcome, row, child, _record = admitted
    assert row.outcome_status == "admitted" and row.eligibility_basis == "provider-controls"
    assert (row.producer_id, row.producer_tenant, row.child_schema_name, row.child_schema_version) == (PRODUCER_ID, PRODUCER_TENANT, PRODUCT_CLASS, "1.0.0")
    assert (child.tenant_id, child.temporal_boundary, child.payload["anchor"]["lei"]) == (PRODUCER_TENANT, PIN, BGC)
    assert child.payload["intent"] == INTENT and child.payload["family"]["nodes"] > 1
    assert row.child_replay_ref and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    assert Decimal(child.debt.debt) > Decimal(GOVERNED_TOLERANCE), "the diagnostic is a diagnostic only while the governed tolerance would withhold"


def test_the_governed_tolerance_withholds_and_the_refusal_is_retained(door: str, tmp_path: pathlib.Path) -> None:
    """At the governed 0.25 the same producer WITHHOLDS (`tolerance-exceeded`):
    the required slot is refused, the composite refuses, and the producer's own
    reason is retained on the record — never re-labelled `producer-unavailable`."""
    outcome, row, child, record = through_the_door(door, tmp_path, tolerance=GOVERNED_TOLERANCE)
    assert isinstance(outcome, RefusalEnvelope), outcome
    assert outcome.kind == "composite-child-refusal" and child is None
    assert row.outcome_status == "ineligible" and row.child_question_address is not None
    assert (row.producer_id, row.producer_tenant) == (PRODUCER_ID, PRODUCER_TENANT)
    retained = json.loads(record.content_generation_path.assembly_refusal)["detail"]
    assert "tolerance-exceeded" in retained and "producer-unavailable" not in retained, retained


# --- the exposure relationships Dave asked to be preserved and proven ------------------


def test_materiality_changes_the_presented_subset_not_the_totals(door: str, admitted: Any, tmp_path: pathlib.Path) -> None:
    """`D-IMPL-299`: assembly determines exposure; projection decides which of it
    is material. Two materialities through the door: the material roster and its
    floor move, the gross and adjusted totals and the family do not, and every
    facility-holding member is either material or residual under both."""
    _o, _r, coarse, _rec = admitted  # the class default, 0.05
    _outcome, _row, fine, _record = through_the_door(door, tmp_path, tolerance=DIAGNOSTIC_TOLERANCE, materiality="0.02")
    assert fine is not None
    assert Decimal(fine.payload["threshold"]) < Decimal(coarse.payload["threshold"])
    assert fine.payload["measures"] == coarse.payload["measures"]
    assert fine.payload["family"] == coarse.payload["family"]
    assert fine.payload["reconciliation"] == coarse.payload["reconciliation"]
    assert len(fine.payload["material"]) > len(coarse.payload["material"])
    assert fine.payload["floor_committed"] < coarse.payload["floor_committed"]
    for payload in (fine.payload, coarse.payload):
        assert len(payload["material"]) + payload["residual_entities"] == payload["family"]["members_holding_facilities"]
    assert content_hash(fine.payload) != content_hash(coarse.payload)


def test_the_declared_limit_regime_governs_the_calculation_and_dedup_and_reconciliation_operate(door: str, tmp_path: pathlib.Path) -> None:
    """Two limit regimes over the specimen's own anchor: the regime that counts
    guarantees and undrawn amounts deduplicates guarantee paths and adjusts the
    total below gross; the regime that counts neither leaves adjusted equal to
    gross with no undrawn. The gross total is the same under both, the
    reconciliation guard runs under both, and the two hash to different addresses."""
    _o1, _r1, appetite, _rec1 = through_the_door(door, tmp_path / "appetite", subject=REGIS, tolerance=DIAGNOSTIC_TOLERANCE, intent=INTENT)
    _o2, _r2, group, _rec2 = through_the_door(door, tmp_path / "group", subject=REGIS, tolerance=DIAGNOSTIC_TOLERANCE, intent=GROUP_LIMIT)
    assert appetite is not None and group is not None
    a, g = appetite.payload, group.payload
    assert a["policy_version"] != g["policy_version"] and a["policy"] != g["policy"]
    assert a["measures"]["gross"] == g["measures"]["gross"]
    assert not a["policy"]["counts_guarantees"] and not a["policy"]["counts_undrawn"]
    assert a["measures"]["adjusted"]["undrawn"] == 0 and a["measures"]["adjusted"]["committed"] == a["measures"]["gross"]["committed"]
    assert g["policy"]["counts_guarantees"] and g["policy"]["counts_undrawn"]
    assert g["guarantee_dedup"]["cases"] > 0, "no guarantee path was deduplicated under the regime that counts guarantees; the proof is vacuous on this anchor"
    assert g["measures"]["adjusted"]["committed"] < g["measures"]["gross"]["committed"]
    for payload in (a, g):
        assert payload["reconciliation"]["family_gross_committed"] == payload["measures"]["gross"]["committed"]
        assert isinstance(payload["reconciliation"]["plausible"], bool) and payload["reconciliation"]["anchor_committed"] > 0
    assert content_hash(appetite) != content_hash(group)


# --- the instant guard, one address, identity ------------------------------------------


def test_a_question_at_another_instant_is_refused_by_name_never_answered_at_the_pin(door: str, tmp_path: pathlib.Path) -> None:
    """The frozen assembly takes no instant. A question asked at any instant but
    the recorded one is refused by name with a replay record — never answered at
    the pin and presented as the caller's, which a consumer's admission could not
    tell apart (`CP05D-F-01`)."""
    outcome, row, child, record = through_the_door(door, tmp_path, asked_at=OTHER_INSTANT, tolerance=DIAGNOSTIC_TOLERANCE)
    assert isinstance(outcome, RefusalEnvelope) and child is None
    # The row carries the SDK's admission verdict; the producer's own reason and
    # words are retained on the record's dimension-5 block (`D-IMPL-342` open:
    # no producer replay reference on the refused row).
    assert row.outcome_status == "ineligible" and row.child_question_address is not None
    retained = json.loads(record.content_generation_path.assembly_refusal)["detail"]
    # The consumer retains the producer's refusal KIND, REASON and KEY; the
    # producer's own prose (which names the pin) stays on the producer's
    # record, unreachable from here (`CP05D-F-02`, the `D-IMPL-342` neighborhood).
    assert "not-supported-at-tier" in retained and "asked_at" in retained, retained
    assert "producer-unavailable" not in retained


def test_the_door_and_the_in_process_run_serve_one_content_address(admitted: Any) -> None:
    """The child the consumer retained through the door hashes to what the frozen
    low road serves in-process for the same question — one product, one address."""
    _o, row, child, _rec = admitted
    direct = _direct(anchor=BGC, intent=INTENT, debt_tolerance=DIAGNOSTIC_TOLERANCE)
    assert isinstance(direct, ServedProduct), getattr(direct, "detail", direct)
    assert row.child_content_address == content_hash(direct.product) == content_hash(child)
    assert row.child_debt == direct.product.debt.debt


@pytest.mark.parametrize(
    "member,value,reason",
    [("producer_id", "somebody-elses-egress", "producer-mismatch"), ("producer_tenant", "somebody-elses-tenant", "producer-tenant-mismatch")],
)
def test_wrong_producer_and_wrong_tenant_refuse_independently(door: str, tmp_path: pathlib.Path, member: str, value: str, reason: str) -> None:
    """The expected producer identity and tenant come from the REGISTRATION; each
    wrong expectation refuses on its own reason with the reason retained."""

    def edit(config: dict[str, Any]) -> None:
        config["producers"]["exposure"][member] = value

    outcome, row, child, _record = through_the_door(door, tmp_path, tolerance=DIAGNOSTIC_TOLERANCE, edit=edit)
    assert isinstance(outcome, RefusalEnvelope) and child is None
    assert row.outcome_status != "admitted" and row.refusal_ref == reason


# --- the known carry, and the shape of the hatch ----------------------------------------


def test_a_pre_resolution_refusal_is_a_recorded_governed_refusal_not_a_runtime_failure(door: str, tmp_path: pathlib.Path) -> None:
    """`D-IMPL-304`, CLOSED on this door: a materiality above the regime's
    ceiling is judged by the frozen tree BEFORE its resolver runs, and until
    2026-09-18 that judgment RAISED and reached the consumer as a runtime
    failure (`producer-unavailable`, no record). The adapter now hands the
    specimen's real resolution outcome up as the typed governed handoff, the
    standard door records it at the question's instant, and the consumer's
    row reads `ineligible` with the producer's refusal identity — the
    `constraint-refusal` and its policy authority — never `producer-unavailable`
    merely because the adapter could not return its determination. The
    FROZEN specimen's own door is unchanged and still raises
    (`tests/examples/test_cp_05_mcp_door.py` asserts it); `D-IMPL-342`'s
    per-row reason and child replay reference remain separate."""
    outcome, row, child, record = through_the_door(door, tmp_path, tolerance=DIAGNOSTIC_TOLERANCE, materiality="0.10")
    assert isinstance(outcome, RefusalEnvelope) and child is None
    assert row.outcome_status == "ineligible", row.outcome_status
    assert row.child_question_address is not None
    assert (row.producer_id, row.producer_tenant) == (PRODUCER_ID, PRODUCER_TENANT)
    retained = json.loads(record.content_generation_path.assembly_refusal)
    assert "constraint-refusal" in retained["detail"], retained["detail"]
    assert "producer-unavailable" not in retained["detail"] and "ccf-runtime-failure" not in retained["detail"]
    assert json.loads(retained["fields"]["producer_id"]) == PRODUCER_ID


#: An LEI the estate does not hold — the frozen tree raises `LookupError` for it,
#: which is a FAULT (no determination was made), not a refusal.
NOBODY = "0000000000000000FAKE"


def test_a_genuine_fault_in_the_frozen_tree_still_reads_as_producer_unavailable(door: str, tmp_path: pathlib.Path) -> None:
    """`D-IMPL-304`'s other half at the adopting wrapper: the typed handoff is
    raised ONLY from the specimen's real resolution outcome. A fault the frozen
    tree raises — an anchor the estate does not hold, a `LookupError` — keeps
    its opaque treatment and reaches the consumer as `producer-unavailable`; the
    adapter fabricates no refusal from an exception."""
    outcome, row, child, _record = through_the_door(door, tmp_path, subject=NOBODY, tolerance=DIAGNOSTIC_TOLERANCE)
    assert isinstance(outcome, RefusalEnvelope) and child is None
    assert row.outcome_status == "producer-unavailable", row.outcome_status
    assert row.child_replay_ref is None


def test_the_wrapper_is_a_binding_adapter_over_the_standard_door_and_the_specimen_is_untouched() -> None:
    """The wrapper imports the SDK's door and the frozen specimen's own
    `produce_governed`; it re-implements no door, no resolver, no record; and
    the frozen tree has ZERO files changed by this work."""
    base = subprocess.run(["git", "merge-base", "HEAD", "main"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    changed = subprocess.run(["git", "diff", "--name-only", base, "--", str(SPECIMEN.relative_to(REPO_ROOT))], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert changed == [], f"the frozen specimen was modified: {changed}"
    forbidden = {"build_egress_server", "build_governed_resolver", "GovernedResolver", "ProducerAssertion", "TokenVerifier", "AuthSettings", "FastMCP", "FileTokenSource", "build_replay_record"}
    serve_tree = ast.parse((WRAPPER / "server" / "serve.py").read_text(encoding="utf-8"))
    adapter_tree = ast.parse((WRAPPER / "adapter.py").read_text(encoding="utf-8"))
    for tree in (serve_tree, adapter_tree):
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not (forbidden & names), forbidden & names
    imported = {f"{n.module}.{a.name}" for n in ast.walk(serve_tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "ccf_runtime.mcp.product_door.open_door" in imported
    called = {n.func.attr for n in ast.walk(adapter_tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "produce_governed" in called
    assert not (WRAPPER / "ccf_config.yaml").exists() and not (WRAPPER / "produce.py").exists()
    declaration = DOOR["declaration"]
    assert (declaration["producer_id"], declaration["producer_tenant"], declaration["required_scope"]) == (PRODUCER_ID, PRODUCER_TENANT, "ccf:egress")
    specimen_config = yaml.safe_load((SPECIMEN / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert declaration["producer_tenant"] == specimen_config["tenant_id"]
