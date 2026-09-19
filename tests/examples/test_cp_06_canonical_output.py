"""What `examples/cp-06-canonical-collateral-and-setoff-coverage` actually serves — `CSCC-G01`…`CSCC-G23`.

The canonical rung-6 successor on the paved producer road (`CP-SPEC-006C`,
Gate 1 approved 2026-09-16; CP-14 Gate 2 slice 3). Every figure below is
MEASURED at run time against the live estate; what this module writes down
are the relationships between figures — that haircuts reduce coverage, that
the successor's payload equals the specimen's at one pinned instant, that the
commitment Π uses is the one in the governed view, that a refused decision
reconstructs — never a number restated.

**The specimen is the control.** `examples/cp-06-collateral-and-setoff-coverage`
is frozen (`D-IMPL-261`) and still serves on the low road, so the lane the
successor serves is DECIDED BY MEASUREMENT (`CSCC-G13`): the two declared
facilities at one instant, full canonical payload hashes and a field-level
comparison. Payload equivalence is not contract identity — the successor's
tenant, plan id, policy-bundle version and, since `D-IMPL-341`, its expiry and
its freshness figure are its own by construction and are asserted different,
never averaged in.

**The instants, and the window (`D-IMPL-341`, calibrated 2026-09-18).** The
class declares `ttl_anchor: from_entity_freshness`, and the SDK honors it:
`expires_at` is the freshest asset valuation date the admitted view carries
plus the declared window, which is the appraisal cycle — the valuation cadence
this product's own table declares, and the calibration Dave ruled on
`CP06C-F-05`. Every question below is asked at the CP-14 instant, as it always
was. What the window does NOT establish is asserted rather than assumed: a
facility whose freshest valuation is older than an appraisal cycle is refused
`ttl-bounds` (`CSCC-G24`, on a facility this estate really holds), and the
undated deposit balances are dated by nothing here at all.

**Reads the estate, seeds nothing** (CLAUDE.md §9). Nothing here pins an
estate count; a test that did would have turned the estate back into a
fixture and must be rewritten rather than re-pinned.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement, ContextProductContract, ProductLineage
from ccf.products.expiry import TTLAnchorUndeclared
from ccf.products.product import OpenedProduct, open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.record import NO_PRODUCT_ADDRESS, DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.deployment.conftest import write_artifact
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import THRESHOLD_PARAMETER

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-06-canonical-collateral-and-setoff-coverage"
SPECIMEN = REPO_ROOT / "examples" / "cp-06-collateral-and-setoff-coverage"
CONSUMER = pathlib.Path(__file__).resolve().parent / "cp_06_canonical_paved_consumer"
RUN = EXAMPLE / "run.py"

CP14_INSTANT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
ADMITTED_AT = CP14_INSTANT + timedelta(minutes=7)
#: A pledged facility the source does not size (`ccf_v2.facility.commitment_amount`
#: is NULL, read 2026-09-18): a NON-EMPTY admitted view — its asset anchors the
#: expiry — that the product's own gate refuses for no commitment. The real-path
#: trigger for `CSCC-G10` since the SDK's anchor gate precedes the product's.
NO_COMMITMENT_FACILITY, NO_COMMITMENT_SCOPE = "FAC-3DF1D5", "529900VKCYZW8GZ4WW58"
#: A pledged facility whose freshest valuation (`2025-02-18`, measured
#: 2026-09-18) is older than the declared appraisal-cycle window at the CP-14
#: instant: the subject on which the expiry refusal is REAL. Three of this
#: estate's fifty collateralized facilities are outside the window; this is one.
EXPIRED_FACILITY, EXPIRED_SCOPE = "FAC-D3D1A4", "B3BS7ACMDUWISF18KY76"


def _freshest_valuation(payload: dict[str, Any]) -> datetime:
    """The instant a served answer's expiry must be anchored on, read off the
    answer itself rather than pinned: no estate date appears in this module."""
    return max(datetime.fromisoformat(a["valuation_date"]).replace(tzinfo=UTC) for a in payload["assets"])

INTENT = "lgd-assessment"
FRESHNESS = "as-filed"
PRODUCT_CLASS = "credit-risk.collateral-coverage"

#: The two facilities `CP-SPEC-006C` §A.2 declares, the specimen's MasTec
#: anchor for the released-lien and under-coverage properties, and a scope
#: nobody holds.
CP14_FACILITY, CP14_SCOPE = "FAC-5B8418", "2549001IGRCG4F0RLD36"
SPECIMEN_FACILITY, SPECIMEN_SCOPE = "FAC-044206", "529900E95812SYWMCE44"
MASTEC_FACILITY, MASTEC_SCOPE = "FAC-102496", "549300TMDIT8WREDOF45"
#: The lane baseline: the specimen's payload content addresses at the CP-14
#: instant, recorded in `CP-SPEC-006C` §A.2 on 2026-09-16 as eight-character
#: prefixes and written out in FULL there on 2026-09-18, when the successor was
#: measured against them at each facility's control instant and matched to all
#: sixty-four characters. A SNAPSHOT COMPARISON, and named as one: the frozen
#: specimen cannot re-serve these since `D-IMPL-341` (`CSCC-G13`), so this pin
#: goes red on estate drift and must then be re-MEASURED against the evidence,
#: never re-pinned to whatever the successor happens to serve.
LANE_BASELINE = {"FAC-5B8418": "d22b256eb343768f185ebbe09eed1949a44226cc1ffccc924550dbbc6f29a45c", "FAC-044206": "8e3e567b194b1aad69bd08da53996dc89bbc4d3f9b335da119147c102d2ebe63"}
SCOPE_NOBODY_HOLDS = "A-SCOPE-NOBODY-HOLDS"

ESTATE_VARIABLES = (
    "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER",
    "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
)
#: The specimen reads the SAME estate under its own names.
SPECIMEN_VARIABLES = {
    "CCF_CP_06_FLUREE_URL": "CCF_CP_06C_FLUREE_URL",
    "CCF_CP_06_FLUREE_LEDGER": "CCF_CP_06C_FLUREE_LEDGER",
    "CCF_CP_06_POSTGRES_DSN": "CCF_CP_06C_POSTGRES_DSN",
    "CCF_CP_06_POSTGRES_SCHEMA": "CCF_CP_06C_POSTGRES_SCHEMA",
}
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

PRODUCER_ID = "cp-06-canonical-collateral-and-setoff-coverage-egress"
PRODUCER_TENANT = "cp-06-canonical-demo"
DOOR_TOKEN_VAR = "CCF_CP_06C_DOOR_TOKEN"
DEV_TOKEN = "dev-token-cp-06-canonical-door"
ENDPOINT_VAR = "CCF_TEST_CP06C_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CP06C_PRODUCER_TOKEN"

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
ENVIRONMENT: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))
GATE_ID = CONFIG["product_class"]["declared_product_gate"]["gate_id"]


# --- fixtures and helpers -----------------------------------------------------------


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    """One example tree's modules, whatever ran before — evicted in and out."""
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment, "produce": produce, "projection": projection}
    finally:
        sys.path.remove(str(tree))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    with _tree_modules(EXAMPLE) as loaded:
        yield loaded


@dataclass(frozen=True)
class _Answer:
    """One served answer with its record, for the assertions below."""

    product: Any
    record: DecisionReplayRecord
    served: Any


def _question(
    opened: OpenedProduct, deployment: Any, *, facility: str, scope: str,
    asked_at: datetime = CP14_INSTANT, intent: str = INTENT, **basis: Any,
) -> ProductRequest:
    parameters: dict[str, Any] = {deployment.FACILITY: facility, deployment.BORROWER_SCOPE: [scope]}
    parameters.update({name: value for name, value in basis.items() if value is not None})
    return opened.question(subject=facility, asked_at=asked_at, intent=intent, freshness=FRESHNESS, parameters=parameters)


def _ask(modules: dict[str, Any], scratch: pathlib.Path, **question: Any) -> Any:
    """One question on the paved road, in its own scratch: the outcome as data."""
    with modules["produce"].product(scratch) as opened:
        return opened.answer(_question(opened, modules["deployment"], **question))


def _answer(modules: dict[str, Any], scratch: pathlib.Path, **question: Any) -> _Answer:
    with modules["produce"].product(scratch) as opened:
        outcome = opened.answer(_question(opened, modules["deployment"], **question))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return _Answer(product=outcome.product, record=opened.record_of(outcome), served=outcome)


def _ratio(answer: Any) -> Decimal:
    product = answer.product if hasattr(answer, "product") else answer
    return Decimal(product.payload["coverage"]["coverage_ratio"])


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The CP-14 facility at the CP-14 instant under the class defaults."""
    return _answer(modules, tmp_path_factory.mktemp("served"), facility=CP14_FACILITY, scope=CP14_SCOPE)


@pytest.fixture(scope="module")
def shared(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The specimen's demonstration anchor — the one with a SHARED asset."""
    return _answer(modules, tmp_path_factory.mktemp("shared"), facility=SPECIMEN_FACILITY, scope=SPECIMEN_SCOPE)


def _specimen(facility: str, scope: str, *, intent: str = INTENT, asked_at: datetime = CP14_INSTANT) -> Any:
    """The frozen specimen, in-process, at the given instant against the same estate."""
    environment = {specimen: os.environ[successor] for specimen, successor in SPECIMEN_VARIABLES.items()}
    previous = {name: os.environ.get(name) for name in environment}
    os.environ.update(environment)
    try:
        with _tree_modules(SPECIMEN) as specimen, tempfile.TemporaryDirectory() as scratch:
            asked = specimen["deployment"].request(facility_id=facility, borrower_scope=[scope], asked_at=asked_at)
            asked = asked.model_copy(update={"intent": intent})
            outcome = specimen["produce"].assemble_and_serve(asked=asked, root=pathlib.Path(scratch))
            # The specimen's spine returns its own `Assembled` record; the
            # successor's road returns the `ServedProduct`. Normalized here.
            return outcome if isinstance(outcome, RefusalEnvelope) else outcome.served
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


# --- G01–G09: the specimen's domain properties, held by the successor ---------------


def test_haircuts_reduce_coverage(estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path) -> None:
    """A haircut is a discount; applying one cannot raise coverage.

    Declared product gate `CSCC-G01` (`CP-SPEC-006C` §G.1).
    """
    gross = _answer(modules, tmp_path, facility=CP14_FACILITY, scope=CP14_SCOPE, apply_haircuts=False)
    assert _ratio(gross) > _ratio(served)


def test_valid_setoff_increases_coverage(estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path) -> None:
    """Deposits the bank may apply are additional recovery, never a deduction.

    Declared product gate `CSCC-G02` (`CP-SPEC-006C` §G.1).
    """
    without = _answer(modules, tmp_path, facility=CP14_FACILITY, scope=CP14_SCOPE, include_setoff=False)
    assert _ratio(served) > _ratio(without)
    assert Decimal(without.product.payload["coverage"]["setoff_value"]) == Decimal(0)


def test_contractual_basis_counts_more_setoff_than_enforceable(
    estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path
) -> None:
    """`contractual` is a superset of `enforceable`, so it cannot count less — read
    off each deposit's OWN recorded enforceability in the view (`CSCC-G14`).

    Declared product gate `CSCC-G03` (`CP-SPEC-006C` §G.1).
    """
    contractual = _answer(modules, tmp_path, facility=CP14_FACILITY, scope=CP14_SCOPE, jurisdiction_basis="contractual")
    assert Decimal(contractual.product.payload["coverage"]["setoff_value"]) >= Decimal(served.product.payload["coverage"]["setoff_value"])
    assert _ratio(contractual) >= _ratio(served)
    assert served.product.payload["findings"]["setoff_excluded_as_unenforceable"] > 0


def test_priority_and_pro_rata_disagree_on_a_shared_asset(
    estate: None, modules: dict[str, Any], shared: _Answer, tmp_path: pathlib.Path
) -> None:
    """The two allocation bases must differ where the graph carries a shared asset.

    Declared product gate `CSCC-G04` (`CP-SPEC-006C` §G.1).
    """
    assert shared.product.payload["findings"]["shared_assets"] > 0
    pro_rata = _answer(modules, tmp_path, facility=SPECIMEN_FACILITY, scope=SPECIMEN_SCOPE, shared_collateral="pro-rata")
    assert _ratio(pro_rata) != _ratio(shared)


def test_the_register_reports_a_released_lien(estate: None, modules: dict[str, Any], tmp_path: pathlib.Path) -> None:
    """A lien the contract layer calls secured and the public register says was RELEASED.

    Declared product gate `CSCC-G05` (`CP-SPEC-006C` §G.1).
    """
    mastec = _answer(modules, tmp_path, facility=MASTEC_FACILITY, scope=MASTEC_SCOPE)
    filings = mastec.product.payload["ucc_filings"]
    assert filings, "the register reached no filing for this debtor"
    released = [f for f in filings if "Termination" in f["amendment_actions"]]
    assert released and mastec.product.payload["findings"]["terminated_liens"] == len(released)


def test_the_cp14_facility_is_covered_and_mastec_is_under_covered(
    estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path
) -> None:
    """The direction, never the number: covered above one, under-covered below.

    Declared product gate `CSCC-G06` (`CP-SPEC-006C` §G.1).
    """
    assert _ratio(served) >= Decimal(1) and Decimal(served.product.payload["coverage"]["shortfall"]) == 0
    mastec = _answer(modules, tmp_path, facility=MASTEC_FACILITY, scope=MASTEC_SCOPE)
    assert _ratio(mastec) < Decimal(1) and Decimal(mastec.product.payload["coverage"]["shortfall"]) > 0


def test_valuation_dates_are_per_asset_and_not_flattened(served: _Answer) -> None:
    """§6.4 refuses to let a one-day mark and a one-year appraisal collapse.

    Declared product gate `CSCC-G07` (`CP-SPEC-006C` §G.1).
    """
    assets = served.product.payload["assets"]
    assert assets
    for asset in assets:
        assert asset["valuation_date"] and isinstance(asset["valuation_age_days"], int)


def test_priority_is_carried_on_the_facility_asset_pair(shared: _Answer) -> None:
    """Priority belongs to the PAIR, and the payload says so per claimant.

    Declared product gate `CSCC-G08` (`CP-SPEC-006C` §G.1).
    """
    shared_assets = [a for a in shared.product.payload["assets"] if a["shared_with"]]
    assert shared_assets
    for asset in shared_assets:
        assert asset["allocation_basis"] and asset["lien_position"]


def test_source_ids_are_served_for_business_matching(served: _Answer) -> None:
    """A payload speaking only in content hashes cannot be joined to anything.

    Declared product gate `CSCC-G09` (`CP-SPEC-006C` §G.1).
    """
    for asset in served.product.payload["assets"]:
        assert not asset["uri"].startswith("collateral_node://")
    assert served.product.payload["facility"] == CP14_FACILITY


# --- G10–G12: the gate, dimension 2, the standard door ------------------------------


def test_the_over_allocation_gate_is_declared_identified_and_runs_on_the_governed_path(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """Declared with an identity on the class AND executed by the road: a
    pledged facility the source does not size leaves the admitted view with a
    facility node carrying no commitment, and the refusal that comes back names
    THIS gate as its reason (`product-invariant-refusal`).

    **The trigger moved on 2026-09-18 (`D-IMPL-341`).** It was "a scope nobody
    holds" — an EMPTY view — and since the SDK's TTL-anchor gate runs before
    the product's, an empty view is refused `ttl-anchor-unresolvable` first
    (`CSCC-G20` holds that precedence). Reaching this gate on the real path
    now takes a view WITH evidence to anchor on and WITHOUT a commitment:
    `FAC-3DF1D5`, asked on its valuation day.

    Declared product gate `CSCC-G10` (`CP-SPEC-006C` §G.1).
    """
    declared = CONFIG["product_class"]["declared_product_gate"]
    assert declared["gate_id"] == GATE_ID and declared["gate_version"]
    with modules["produce"].product(tmp_path) as opened:
        denied = opened.answer(_question(opened, modules["deployment"], facility=NO_COMMITMENT_FACILITY, scope=NO_COMMITMENT_SCOPE))
        assert isinstance(denied, RefusalEnvelope), denied
        record = opened.record_of(denied)
    # The disclosed shell names the gate; the gate's own text is INTERNAL —
    # on the record's dimension-5 block, never in the consumer-facing detail.
    assert denied.kind == "product-invariant-refusal" and denied.reason == GATE_ID, (denied.kind, denied.reason)
    assert "no facility commitment" in record.content_generation_path.assembly_refusal
    assert record.context_fabric_snapshot.touched_entities, "the view was empty; the anchor gate would have spoken first"


def test_replay_dimension_two_is_a_superset_of_product_lineage(served: _Answer) -> None:
    """`D-IMPL-310`: every policy version the product carries is a recorded binding.

    Declared product gate `CSCC-G11` (`CP-SPEC-006C` §G.1).
    """
    bindings = {b.key for b in served.record.policy_bindings.bindings}
    versions = {b.version for b in served.record.policy_bindings.bindings}
    assert "request_contract" in bindings
    assert set(served.product.lineage.policy_bundle_versions) <= versions
    assert set(served.product.lineage.operators_invoked) == set(CONFIG["product_class"]["required_operator_keys"])


def test_the_door_is_the_sdk_standard_door_opened_from_the_declaration() -> None:
    """No door module, no `door.yaml`, no script path: the launcher opens the
    SDK's standard door over the opened product and re-implements nothing.

    Declared product gate `CSCC-G12` (`CP-SPEC-006C` §G.1).
    """
    assert not (EXAMPLE / "server" / "door.yaml").exists()
    assert not (EXAMPLE / "backends.yaml").exists()
    tree = ast.parse((EXAMPLE / "server" / "serve.py").read_text(encoding="utf-8"))
    imported = {f"{n.module}.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "ccf_runtime.mcp.product_door.open_door" in imported
    forbidden = {"build_egress_server", "ProducerAssertion", "EntitlementPolicy", "TokenVerifier"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not (forbidden & names), forbidden & names
    assert CONFIG["door"]["producer_id"] == PRODUCER_ID and CONFIG["door"]["producer_tenant"] == CONFIG["tenant_id"]


# --- G13: the lane, measured ---------------------------------------------------------


@pytest.mark.parametrize("facility,scope", [(CP14_FACILITY, CP14_SCOPE), (SPECIMEN_FACILITY, SPECIMEN_SCOPE)])
def test_the_lane_is_measured_the_successor_payload_equals_the_specimens(
    estate: None, modules: dict[str, Any], facility: str, scope: str, tmp_path: pathlib.Path
) -> None:
    """`CP-SPEC-006C` §D.4: at one instant under the class defaults, the
    successor's canonical payload hashes to the specimen's — the full
    sixty-four-character address, not a prefix — so the successor serves
    `1.0.0`, a second producer of the same product. What differs is asserted different: tenant, plan id,
    policy-bundle version — and, since `D-IMPL-341`, the expiry and the
    freshness figure. Payload equivalence is not contract identity.

    **Measured at the CP-14 instant on 2026-09-16** (the historical lane
    measurement, the baseline this test now holds): payloads `d22b256e…` /
    `8e3e567b…` identical, `debt` and `expires_at` equal. **Measured on each
    **Re-measured at the CP-14 instant on 2026-09-18**, after the window was
    calibrated to the appraisal cycle: the successor's payload still hashes to the baseline, and
    its `expires_at` runs from the valuation rather than the question. The
    frozen specimen no longer answers at all — it declares the same anchor over
    a resolver wired with no λ_c table, which is a configuration failure the
    builder refuses (`TTLAnchorUndeclared`) before a question proceeds
    (`D-IMPL-261`: evidence of the SDK's evolution, the specimen untouched).
    Its `F` was, while it served, an asset aged by `now - valuation_age_days` —
    a STORED count that equals the valuation's real age only on the day the
    estate was loaded (two load dates, `2026-08-17` and `2026-08-22`).

    Declared product gate `CSCC-G13` (`CP-SPEC-006C` §G.1).
    """
    instant = CP14_INSTANT
    successor = _answer(modules, tmp_path, facility=facility, scope=scope)
    # THE BASELINE IS THE RECORDED MEASUREMENT (`CP-SPEC-006C` §A.2 / §D.4,
    # 2026-09-16), not a live specimen: the frozen specimen declares this
    # anchor over a resolver wired with no λ_c table, and since Dave's
    # registration ruling that is refused at the BUILDER, so its payload can no
    # longer be re-derived at any instant.
    assert content_hash(successor.product.payload) == LANE_BASELINE[facility], content_hash(successor.product.payload)
    assert successor.product.temporal_boundary == instant
    assert successor.product.expires_at == successor.product.ttl_anchor_at + timedelta(seconds=int(CONFIG["ttl"]["product_ttl_seconds"]))
    assert successor.product.expires_at < instant + timedelta(seconds=int(CONFIG["ttl"]["product_ttl_seconds"])), "the successor's expiry is running from the question"
    with pytest.raises(TTLAnchorUndeclared, match="wired with no λ_c table"):
        _specimen(facility, scope, asked_at=instant)
    assert (successor.product.schema_name, successor.product.schema_version) == (PRODUCT_CLASS, "1.0.0")
    assert CONFIG["product_class"]["schema_version"] == CONFIG["request_contract"]["schema_version"] == "1.0.0"
    # the contract is NOT the same, by construction
    # What is asserted DIFFERENT — tenant, plan id, policy-bundle version — is
    # held against the specimen's declarations now that it serves no contract
    # to read them off: the successor's are its own by construction.
    assert successor.product.tenant_id == PRODUCER_TENANT != yaml.safe_load((SPECIMEN / "ccf_config.yaml").read_text(encoding="utf-8"))["tenant_id"]
    assert successor.product.plan_id.startswith("cp-06-canonical.")


# --- G14: the commitment is read off the governed view ------------------------------


def _with_commitment_scaled(deployment: Any, factor: Decimal, facility: str) -> Callable[[Any], tuple[SignalEnvelope, ...]]:
    """The deployment's own acquire, with the anchor's recorded commitment scaled
    in the ENVELOPE — the governed view then carries the scaled figure."""

    def acquire(context: Any) -> tuple[SignalEnvelope, ...]:
        out: list[SignalEnvelope] = []
        for envelope in deployment.acquire(context):
            payload = envelope.raw_payload
            if payload.get(deployment.KIND) == "facility" and payload.get("ref") == facility and payload.get("commitment"):
                payload = {**payload, "commitment": str(Decimal(payload["commitment"]) * factor)}
                envelope = envelope.model_copy(update={"raw_payload": payload})
            out.append(envelope)
        return tuple(out)

    return acquire


def test_the_commitment_pi_divides_by_is_the_one_in_the_governed_view(
    estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path
) -> None:
    """With every other input fixed, a changed facility commitment in the
    governed view changes the coverage ratio in the inverse proportion; Π's
    constructor takes no commitment and no jurisdiction register, so there is
    no side channel to obtain the old value from.

    Declared product gate `CSCC-G14` (`CP-SPEC-006C` §G.1).
    """
    deployment, produce, projection = modules["deployment"], modules["produce"], modules["projection"]
    constructor = next(
        n for n in ast.walk(ast.parse((EXAMPLE / "projection.py").read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )
    parameters = {a.arg for a in constructor.args.kwonlyargs}
    assert "commitment" not in parameters and "enforceable_jurisdictions" not in parameters, parameters
    with open_product(
        config_root=EXAMPLE, scratch=tmp_path,
        acquire=_with_commitment_scaled(deployment, Decimal(2), CP14_FACILITY),
        project=produce.plan_factory, assess=deployment.assess, gate=deployment.coverage_gate,
    ) as opened:
        doubled = opened.answer(_question(opened, deployment, facility=CP14_FACILITY, scope=CP14_SCOPE))
    assert isinstance(doubled, ServedProduct), getattr(doubled, "detail", doubled)
    assert Decimal(doubled.product.payload["commitment"]) == Decimal(served.product.payload["commitment"]) * 2
    assert doubled.product.payload["coverage"]["total"] == served.product.payload["coverage"]["total"]
    assert _ratio(doubled) == _ratio(served) / 2


# --- G15–G16: the shape, the untouched specimen --------------------------------------


def test_the_structural_classifier_reads_this_tree_as_paved() -> None:
    """`shape_of` is structural — it asks the code, never a roster — and no
    resolver ownership or record call exists in the tree.

    Declared product gate `CSCC-G15` (`CP-SPEC-006C` §G.1).
    """
    spec = importlib.util.spec_from_file_location("_sep", REPO_ROOT / "tests" / "examples" / "test_spine_separation.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.shape_of(EXAMPLE) == "paved"
    forbidden = {"build_governed_resolver", "build_replay_record", "run_gates", "serve"}
    for path in EXAMPLE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        bound = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        called |= {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        assert not (forbidden & (bound | called)) or path.name == "serve.py" and (forbidden & (bound | called)) == {"serve"}, (path, forbidden & (bound | called))


def test_the_specimen_is_untouched_and_no_identity_is_reused(served: _Answer) -> None:
    """cp-06 is frozen under `D-IMPL-261`: ZERO files changed by this work,
    measured against the branch point; and this tree reuses none of the
    specimen's identities — tenant, producer id, plan-id prefix, gate id,
    class ids.

    Declared product gate `CSCC-G16` (`CP-SPEC-006C` §G.1).
    """
    base = subprocess.run(["git", "merge-base", "HEAD", "main"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-only", base, "--", str(SPECIMEN.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert changed == [], f"the frozen specimen was modified: {changed}"
    specimen_config = yaml.safe_load((SPECIMEN / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert CONFIG["tenant_id"] != specimen_config["tenant_id"]
    assert CONFIG["product_class"]["declared_product_gate"]["gate_id"] != specimen_config["product_class"]["declared_product_gate"]["gate_id"]
    assert CONFIG["request_contract"]["class_id"] != specimen_config["request_contract"]["class_id"]
    assert served.product.plan_id.startswith("cp-06-canonical.")
    assert served.product.tenant_id == PRODUCER_TENANT


# --- G17–G18, G21: the CP-14-shaped question through the standard door ---------------


@contextmanager
def producer(estate: None) -> Iterator[str]:
    """The producer process — this tree's own door, spawned via `run.py --door`."""
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


def cp14_question(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
    """The consumer's ONE mapping — `CP-SPEC-014`'s collateral question verbatim:
    the facility is the child's subject and `facility_id`, the obligor its
    borrower scope, no tolerance."""
    return cp14_question_for(CP14_SCOPE)(requirement, request)


def cp14_question_for(scope: str) -> Callable[[ChildRequirement, ProductRequest], ChildQuestion]:
    """The same mapping over another borrower — the scope is the CONSUMER's to
    state, not the parent question's: this consumer's request contract declares
    no `borrower_scope` parameter, and inventing one to reach a second facility
    would change the contract to suit a test."""

    def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        return ChildQuestion(
            subject=request.subject, intent=INTENT, freshness=FRESHNESS,
            parameters={"facility_id": request.subject, "borrower_scope": [scope]},
        )

    return questions


def _consumer_tree(tmp_path: pathlib.Path, *, edit: Callable[[dict[str, Any]], None] | None = None) -> pathlib.Path:
    config = yaml.safe_load((CONSUMER / "ccf_config.yaml").read_text(encoding="utf-8"))
    if edit is not None:
        edit(config)
    root = tmp_path / "consumer"
    root.mkdir(parents=True)
    write_artifact(root, "ccf_config.yaml", config)
    (root / "ccf_environment.yaml").write_text((CONSUMER / "ccf_environment.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    return root


def paved_consumer(tmp_path: pathlib.Path, *, url: str, edit: Callable[[dict[str, Any]], None] | None = None, scope: str = CP14_SCOPE) -> OpenedProduct:
    return open_product(
        config_root=_consumer_tree(tmp_path, edit=edit), scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(), project=fixture.plan_factory, assess=fixture.assess,
        questions=cp14_question_for(scope), environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN}, clock=lambda: ADMITTED_AT,
    )


def ask_consumer(opened: OpenedProduct, *, asked_at: datetime = CP14_INSTANT, subject: str = CP14_FACILITY) -> Any:
    return opened.answer(opened.question(
        subject=subject, asked_at=asked_at, intent="fixture-intent", freshness="fixture-freshness",
        parameters={THRESHOLD_PARAMETER: 1000},
    ))


def consumer_row(opened: OpenedProduct, outcome: Any) -> Any:
    rows = opened.record_of(outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def test_the_cp14_question_is_answered_in_another_process_and_admitted_under_provider_controls(
    estate: None, served: _Answer, tmp_path: pathlib.Path
) -> None:
    """The CP-14-shaped question reaches the successor through the standard
    door in ANOTHER process; the child is admitted under the expected producer
    identity and tenant with `provider-controls`; the retained child is the
    producer's own bytes — the same content address the in-process serve
    reached (`CSCC-G21`).

    Declared product gate `CSCC-G17` (`CP-SPEC-006C` §G.1).
    """
    with producer(estate) as url, paved_consumer(tmp_path, url=url) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        row = consumer_row(opened, outcome)
        child = ContextProductContract.model_validate_json(
            FileArtifactStore(root=opened.scratch / opened.replay.store_dirname).get(content_address=row.child_content_address)
        )
    assert row.outcome_status == "admitted" and row.eligibility_basis == "provider-controls"
    assert (row.producer_id, row.producer_tenant, row.child_schema_name, row.child_schema_version) == (PRODUCER_ID, PRODUCER_TENANT, PRODUCT_CLASS, "1.0.0")
    assert (child.tenant_id, child.temporal_boundary, child.payload["facility"]) == (PRODUCER_TENANT, CP14_INSTANT, CP14_FACILITY)
    assert row.child_replay_ref and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    assert row.child_ttl_anchor == "from_entity_freshness"
    assert row.child_ttl_anchor_at == child.ttl_anchor_at == _freshest_valuation(child.payload)


def test_a_producer_refusal_for_expired_evidence_crosses_as_an_ineligible_child(
    estate: None, tmp_path: pathlib.Path
) -> None:
    """The consumer's half of the same property, through this producer's own
    door: asked about the facility whose evidence outlived the window, the
    producer refuses `ttl-bounds` and the consumer records the child
    `ineligible` with the producer's refusal retained by kind and reason —
    never `admitted`, never `producer-unavailable`. `D-IMPL-341`.
    """
    with producer(estate) as url, paved_consumer(tmp_path, url=url, scope=EXPIRED_SCOPE) as opened:
        outcome = ask_consumer(opened, subject=EXPIRED_FACILITY)
        assert isinstance(outcome, RefusalEnvelope), getattr(outcome, "product", outcome)
        row = consumer_row(opened, outcome)
    assert row.outcome_status == "ineligible" and row.refusal_ref == "ineligible", (row.outcome_status, row.refusal_ref)
    assert (row.producer_refusal_kind, row.producer_refusal_reason) == ("ttl-refusal", "ttl-bounds"), (row.producer_refusal_kind, row.producer_refusal_reason)
    assert row.child_question_address is not None and row.child_replay_ref and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")


def test_the_door_and_the_in_process_run_serve_one_content_address(estate: None, served: _Answer, tmp_path: pathlib.Path) -> None:
    """One question, two deliveries, one address: the child the consumer
    retained through the door hashes to what this process served in-process.

    Declared product gate `CSCC-G21` (`CP-SPEC-006C` §G.1).
    """
    with producer(estate) as url, paved_consumer(tmp_path, url=url) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        row = consumer_row(opened, outcome)
    assert row.child_content_address == content_hash(served.product)
    assert row.child_debt == served.product.debt.debt


@pytest.mark.parametrize(
    "member,value,reason",
    [("producer_id", "somebody-elses-egress", "producer-mismatch"), ("producer_tenant", "somebody-elses-tenant", "producer-tenant-mismatch")],
)
def test_wrong_producer_and_wrong_tenant_refuse_independently(
    estate: None, tmp_path: pathlib.Path, member: str, value: str, reason: str
) -> None:
    """The expected producer identity and tenant come from the REGISTRATION —
    a payload cannot authorize itself by claiming them — and each wrong
    expectation refuses on its own reason with the reason retained.

    Declared product gate `CSCC-G18` (`CP-SPEC-006C` §G.1).
    """

    def edit(config: dict[str, Any]) -> None:
        config["producers"]["collateral"][member] = value

    with producer(estate) as url, paved_consumer(tmp_path, url=url, edit=edit) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, RefusalEnvelope), outcome
        row = consumer_row(opened, outcome)
    assert row.outcome_status != "admitted" and row.refusal_ref == reason


# --- G19–G20: the governed axes the specimen left open --------------------------------


def test_an_unknown_intent_is_refused_on_the_declared_discovery_set(estate: None, modules: dict[str, Any], tmp_path: pathlib.Path) -> None:
    """`intent` is judged on `discovery.intents`; the specimen declares no set
    and serves any intent — a DELIBERATE tightening, reported here rather
    than averaged into the lane comparison.

    Declared product gate `CSCC-G19` (`CP-SPEC-006C` §G.1).
    """
    refused = _ask(modules, tmp_path, facility=CP14_FACILITY, scope=CP14_SCOPE, intent="annual-review")
    assert isinstance(refused, RefusalEnvelope), refused
    assert refused.replay_reference
    assert refused.kind != "ttl-anchor-refusal", "the successor was refused before the intent was judged"
    # The specimen still judges no intent. Until `D-IMPL-341` it SERVED this
    # question; since Dave's registration ruling its wiring is refused at the
    # builder — for the table it does not name, never for the intent
    # (`D-IMPL-261` evidence; the specimen is untouched).
    with pytest.raises(TTLAnchorUndeclared, match="wired with no λ_c table"):
        _specimen(CP14_FACILITY, CP14_SCOPE, intent="annual-review")


def test_a_scope_the_caller_does_not_hold_yields_an_empty_graph_and_a_refusal(
    estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path
) -> None:
    """The policy operator yields an EMPTY graph — never a redacted one — and
    the product refuses rather than serving a coverage of zero over a facility
    the view does not hold. The specimen serves the zero (`CP-SPEC-006C`
    §G.3, a deliberate difference).

    Declared product gate `CSCC-G20` (`CP-SPEC-006C` §G.1).
    """
    assert served.product.payload["assets"], "the entitled read returned nothing"
    with modules["produce"].product(tmp_path) as opened:
        denied = opened.answer(_question(opened, modules["deployment"], facility=CP14_FACILITY, scope=SCOPE_NOBODY_HOLDS))
        assert isinstance(denied, RefusalEnvelope), denied
        record = opened.record_of(denied)
    # PRECEDENCE, since `D-IMPL-341` (2026-09-18): an empty view carries no
    # evidence instant, and the SDK's TTL-anchor gate refuses it before the
    # product's own gate can — `ttl-anchor-refusal` / `ttl-anchor-unresolvable`,
    # where until 341 this refusal named `cp-06-canonical.over-allocation-guard`.
    # The empty-graph properties are unchanged.
    assert (denied.kind, denied.reason) == ("ttl-anchor-refusal", "ttl-anchor-unresolvable"), (denied.kind, denied.reason)
    path = record.content_generation_path
    assert "no evidence instant" in path.assembly_refusal
    assert path.steps and path.product_content_address == NO_PRODUCT_ADDRESS
    assert not record.context_fabric_snapshot.touched_entities
    # The product gate's own no-commitment half, held directly on the shape it
    # would see: a served candidate whose commitment is absent.
    unsized = served.product.model_copy(update={"payload": {**served.product.payload, "commitment": None}})
    assert modules["deployment"].coverage_gate(candidate=unsized) == modules["deployment"].NO_COMMITMENT


# --- G22–G23: a fresh fabric per run; the expiry anchor --------------------------------


def test_a_fresh_fabric_per_run_and_one_determination_across_roots(
    estate: None, modules: dict[str, Any], served: _Answer, tmp_path: pathlib.Path
) -> None:
    """Two questions under one opened product leave two substrate files, and a
    facility served after another under one root hashes to the address it
    hashes to alone.

    Declared product gate `CSCC-G22` (`CP-SPEC-006C` §G.1).
    """
    deployment, produce = modules["deployment"], modules["produce"]
    substrate = ENVIRONMENT["substrate"]
    with produce.product(tmp_path / "shared-root") as opened:
        first = opened.answer(_question(opened, deployment, facility=SPECIMEN_FACILITY, scope=SPECIMEN_SCOPE))
        second = opened.answer(_question(opened, deployment, facility=CP14_FACILITY, scope=CP14_SCOPE))
        minted = sorted((tmp_path / "shared-root").glob(f"{substrate['prefix']}*{substrate['suffix']}"))
    assert len(minted) == 2 and minted[0] != minted[1], minted
    assert isinstance(first, ServedProduct) and isinstance(second, ServedProduct)
    assert content_hash(second.product) == content_hash(served.product)


def test_expires_at_is_anchored_on_the_freshest_valuation_not_the_question(served: _Answer) -> None:
    """The declared anchor, honored since `D-IMPL-341` (validation pass
    2026-09-18; this test was `xfail(strict=True)` evidence of the gap until
    then): `ttl_anchor_at` is the freshest valuation date among the served
    assets as a UTC midnight instant — the claim's own `valid_from`, the clock
    the `collateral_node` row declares — and `expires_at` is that plus the
    declared window (the appraisal cycle, since the calibration of
    2026-09-18), never the question plus the window. The record's
    dimension 5 carries the same instant.

    Declared product gate `CSCC-G23` (`CP-SPEC-006C` §G.1).
    """
    assert CONFIG["product_class"]["ttl_anchor"] == "from_entity_freshness"
    freshest = max(datetime.fromisoformat(a["valuation_date"]).replace(tzinfo=UTC) for a in served.product.payload["assets"])
    window = timedelta(seconds=int(CONFIG["ttl"]["product_ttl_seconds"]))
    assert served.product.ttl_anchor == "from_entity_freshness"
    assert served.product.ttl_anchor_at == freshest
    assert served.product.expires_at == freshest + window
    assert served.product.expires_at != served.product.temporal_boundary + window, "the expiry is running from the question again"
    assert served.record.content_generation_path.ttl_anchor_at == freshest


def _refused(modules: dict[str, Any], scratch: pathlib.Path, **question: Any) -> tuple[RefusalEnvelope, DecisionReplayRecord]:
    """One refused question with its persisted record, read from a fresh store instance."""
    with modules["produce"].product(scratch) as opened:
        outcome = opened.answer(_question(opened, modules["deployment"], **question))
        assert isinstance(outcome, RefusalEnvelope), getattr(outcome, "product", outcome)
        store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        record = DecisionReplayRecord.model_validate_json(store.get(content_address=store.resolve_uri(uri=outcome.replay_reference)))
    return outcome, record


def test_evidence_older_than_the_declared_window_is_refused_by_the_expiry_gate(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The window is a claim that can FAIL, and it fails on a real subject.

    `FAC-D3D1A4`'s freshest asset valuation is `2025-02-18`; the declared
    window is the appraisal cycle, so its coverage expired `2026-02-18`, months
    before the CP-14 instant, and the SDK's TTL gate refuses `ttl-refusal` /
    `ttl-bounds` before any product gate runs. The retained record names the
    evidence-anchored expiry it refused on — the valuation plus the window,
    never the question plus the window.

    Three of this estate's fifty collateralized facilities are outside the
    window and forty-seven are inside (measured 2026-09-18): the term
    discriminates between real subjects, which is what makes the calibration a
    demonstration rather than a number that lets everything through.

    Declared product gate `CSCC-G24` (`CP-SPEC-006C` §G.1).
    """
    window = timedelta(seconds=int(CONFIG["ttl"]["product_ttl_seconds"]))
    assert int(CONFIG["ttl"]["product_ttl_seconds"]) == int(CONFIG["half_life"]["real_property_appraisal"]["half_life_seconds"]), (
        "the window is no longer the appraisal cycle the calibration says it is (`CP06C-F-05`)"
    )
    refused, record = _refused(modules, tmp_path, facility=EXPIRED_FACILITY, scope=EXPIRED_SCOPE)
    assert (refused.kind, refused.reason) == ("ttl-refusal", "ttl-bounds"), (refused.kind, refused.reason)
    retained = json.loads(record.content_generation_path.assembly_refusal)
    expires_at = datetime.fromisoformat(json.loads(retained["fields"]["expires_at"]))
    assert expires_at < CP14_INSTANT < CP14_INSTANT + window
    assert record.content_generation_path.product_content_address == NO_PRODUCT_ADDRESS
    # NO ESTATE DATE IS PINNED HERE. The refusal names an expiry; the anchor it
    # implies is that minus the declared window, and the same facility asked
    # INSIDE its window must serve on exactly that anchor and name it as the
    # freshest valuation in its own payload. The estate closes the loop, so
    # revaluing this facility reds the test as the behavior change it is —
    # the subject is no longer expired — rather than as a stale pin.
    implied_anchor = expires_at - window
    inside = _answer(modules, tmp_path / "inside", facility=EXPIRED_FACILITY, scope=EXPIRED_SCOPE, asked_at=implied_anchor + timedelta(hours=12))
    assert inside.product.ttl_anchor_at == implied_anchor == _freshest_valuation(inside.product.payload), (
        "this facility's evidence moved; re-measure the subject rather than re-pinning the expectation"
    )
    assert inside.product.expires_at == expires_at


# --- identity and reconstruction ------------------------------------------------------


class _FreshEnvironment:
    """A replay environment built from the RECORD and the deployment's own
    documents — no acquisition object, no live view from the serve."""

    def __init__(self, *, modules: dict[str, Any], opened: OpenedProduct, fabric: Any, record: DecisionReplayRecord) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415

        self._produce = modules["produce"]
        path = record.content_generation_path
        assert path.request is not None
        # Π is rebuilt from the EFFECTIVE request the record carries on
        # dimension 2 — the class defaults and policy as they folded at
        # decision time — never from the caller's raw parameters and never
        # from a value this environment resolved for itself.
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        assert isinstance(effective, EffectiveRequest), resolution
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        self._ttl = int(CONFIG["ttl"]["product_ttl_seconds"])
        # The road's own builder over the road's own mapping — the escape hatch
        # `build_arguments` exists to prove: no second architecture.
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver._operator_parameters(self._request),
            view=fabric.handle.reader.as_of(tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary),
            pins=fabric.pins, policy_bundle_key=self._policy_key,
        )
        self.rehydrated = 0

    def resolve_plan(self, *, plan_id: str) -> Any:
        return self._produce.plan_factory(required=self._required, request=self._request)

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        return self._operators

    def rehydrate_product(self, *, record: DecisionReplayRecord, projection: Any) -> ContextProductContract:
        self.rehydrated += 1
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        policy_versions = frozenset(b.version for b in record.policy_bindings.bindings if b.key == self._policy_key)
        return ContextProductContract(
            schema_name=CONFIG["product_class"]["schema_name"], schema_version=CONFIG["product_class"]["schema_version"],
            plan_id=projection.plan_id, tenant_id=record.tenant_id, temporal_boundary=snapshot.temporal_boundary,
            # `D-IMPL-341`: the anchor instant comes off the RECORD (dimension 5), never
            # recomputed; a record without one is the pre-341, decision-anchored shape.
            expires_at=(path.ttl_anchor_at or snapshot.temporal_boundary) + timedelta(seconds=self._ttl),
            ttl_anchor=CONFIG["product_class"]["ttl_anchor"], ttl_anchor_at=path.ttl_anchor_at,
            lineage=ProductLineage(operators_invoked=frozenset(path.operator_plan), policy_bundle_versions=policy_versions, graph_snapshot_at=snapshot.temporal_boundary),
            payload=projection.payload, debt=path.debt, debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency, obligation_in_force=path.obligation_in_force,
        )


@contextmanager
def _reopened_fabric(opened: OpenedProduct) -> Iterator[Any]:
    """The question's own minted substrate, reopened as the replay reader."""
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415

    substrate = ENVIRONMENT["substrate"]
    minted = sorted(opened.scratch.glob(f"{substrate['prefix']}*{substrate['suffix']}"))[-1]
    fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
    try:
        yield fabric
    finally:
        fabric.handle.close()


def test_replay_reproduces_the_served_product_from_the_recorded_graph_inputs(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """Replay rebuilds the plan from the RECORDED request and re-executes over
    the recorded snapshot — the commitment comes back off the graph, never
    from an acquisition object, which no longer exists — and reproduces the
    served bytes exactly.
    """
    from ccf.replay.engine import replay  # noqa: PLC0415

    with modules["produce"].product(tmp_path) as opened:
        outcome = opened.answer(_question(opened, modules["deployment"], facility=CP14_FACILITY, scope=CP14_SCOPE))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        record = opened.record_of(outcome)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            replayed = replay(
                record_address=outcome.replay_ref.content_address,
                store=FileArtifactStore(root=opened.scratch / opened.replay.store_dirname),
                reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment,
            )
    assert replayed.product_content_address == content_hash(outcome.product)
    assert replayed.product.payload["commitment"] == outcome.product.payload["commitment"]
    assert environment.rehydrated == 1


def test_a_refused_determination_reconstructs_through_the_344_path_without_a_product(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The gate refusal (a scope nobody holds) is a post-projection refusal:
    `replay_refusal` re-executes the recorded operator path over the recorded
    snapshot, holds the refusal's evidence to it, and never rehydrates a
    product; `replay()` refuses the same record by name (`D-IMPL-344`).
    """
    from ccf.replay.engine import RefusalReplayOutcome, ReplayRecordKindMismatch, replay, replay_refusal  # noqa: PLC0415

    with modules["produce"].product(tmp_path) as opened:
        denied = opened.answer(_question(opened, modules["deployment"], facility=CP14_FACILITY, scope=SCOPE_NOBODY_HOLDS))
        assert isinstance(denied, RefusalEnvelope), denied
        record = opened.record_of(denied)
        store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        address = store.resolve_uri(uri=denied.replay_reference)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            reconstructed = replay_refusal(record_address=address, store=store, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
            with pytest.raises(ReplayRecordKindMismatch):
                replay(record_address=address, store=store, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert reconstructed.child_contract_addresses == () and environment.rehydrated == 0
    assert reconstructed.graph_snapshot_id == record.context_fabric_snapshot.graph_snapshot_id
    assert "product" not in type(reconstructed).model_fields
