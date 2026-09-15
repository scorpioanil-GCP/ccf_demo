"""What `examples/cp-03-canonical-obligor-financial-spread` actually serves.

Direct and behavior-oriented: every figure below is MEASURED at run time
against the live estate, and the module writes down no number it did not
observe. What it does write down are the *relationships* between figures —
that `D_c = 1 − F·C·S` over the view, that a refusal names its gate, that the
served spread is the fabric's own state, that replay carries more than the
product does — because those are the claims the example exists to make.

**The negative boundaries are tests too.** This successor serves the SAME
product as the frozen `examples/cp-03-obligor-financial-spread` specimen
(`CP14-F-22`) and must not borrow its identity: not its content address, not
its replay record, not its debt figure, and not one byte of its tree. And the
two defects that keep the specimen from serving — `intent` declared as an
argument, `build_replay_record` called without a resolution binding — are
asserted absent here by construction, with the SDK's own refusal of the first
shape kept as a control rather than trusted.

**Reads the estate, seeds nothing** (CLAUDE.md §9). Every assertion holds at
any roster size; a test here that pinned an estate count would have turned the
estate back into a fixture and must be rewritten rather than re-pinned.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-03-canonical-obligor-financial-spread"
SPECIMEN = REPO_ROOT / "examples" / "cp-03-obligor-financial-spread"

#: The instant `CP-SPEC-014` asks its children at — held, not tuned (`CP14-F-19`).
CP14_INSTANT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

#: The intent and freshness this class serves — `run.py`'s own constants.
INTENT = "annual-review"
FRESHNESS = "filing-cadence"


def _config() -> dict[str, Any]:
    """The tree's ONE Control Plane document, as the declaration authority."""
    document: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    return document


def _environment() -> dict[str, Any]:
    """The tree's environment document — the NAMES, never a value."""
    document: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))
    return document


def _settings() -> dict[str, str]:
    """The source settings, resolved from the variables the environment names."""
    source = _environment()["sources"]["financial_spread"]
    return {name: os.environ[value["from_env"]] for name, value in source.items()}


@dataclass(frozen=True)
class _Answer:
    """One served answer, with its record, for the assertions below."""

    product: Any
    record: Any
    served: Any

#: Module names EVERY example in this repository ships. `produce.py` does a bare
#: `import deployment`, so whichever example was imported first wins the name
#: for the rest of the session unless evicted.
COLLIDING_NAMES = ("acquisition", "deployment", "produce", "projection")


def _demonstration(name: str) -> str:
    """A `run.py` constant, read from the example rather than restated."""
    tree = ast.parse((EXAMPLE / "run.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise AssertionError(f"run.py declares no {name}")


@pytest.fixture(scope="module")
def example_modules() -> Iterator[tuple[Any, Any, Any]]:
    """This example's `deployment`, `produce` and `acquisition`, whatever ran before.

    Evicted on the way in so this module gets its own, and on the way out so the
    next module gets its own rather than inheriting these.
    """
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING_NAMES}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == EXAMPLE, (
            "imported another example's `deployment`; the eviction did not hold"
        )
        yield deployment, produce, acquisition
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING_NAMES:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


#: The two variables the example itself reads. The test supplies NOTHING: it
#: runs against whatever estate the operator pointed the example at.
ESTATE_VARIABLES = ("CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA")

#: Set where a missing estate must FAIL rather than skip.
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"


@pytest.fixture(scope="module")
def estate() -> str:
    """The LIVE estate, read-only, seeded with nothing (CLAUDE.md §9)."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the live estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespace — PostgreSQL schema `ccf_v2` —"
            " never the v1 name in `ccf_dataprep/.env` (CLAUDE.md §9)"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)
    return os.environ["CCF_CP_03C_POSTGRES_SCHEMA"]


def _ask(modules: tuple[Any, Any, Any], **question: Any) -> Any:
    """One question on the paved road, in its own scratch: served with its record, or the refusal."""
    from ccf.projection.plan import Perspective  # noqa: PLC0415

    deployment, produce, _ = modules
    principal = question.pop("principal_id", None)
    lei = question.pop("lei", _demonstration("DEMONSTRATION_ANCHOR"))
    asked_at = question.pop("asked_at", CP14_INSTANT)
    intent = question.pop("intent", INTENT)
    parameters: dict[str, Any] = {deployment.DEBT_TOLERANCE: Decimal(str(question.pop("debt_tolerance", "1.0"))), **question}
    with tempfile.TemporaryDirectory() as scratch, produce.product(pathlib.Path(scratch)) as opened:
        perspective = None
        if principal is not None and principal != opened.default_perspective.principal_id:
            # Ask as somebody else: that principal's grant is STATED on the request.
            parameters.update(deployment.grant_parameters(principal, settings=opened.sources[deployment.SOURCE]))
            perspective = Perspective(principal_id=principal, role=opened.default_perspective.role)
        asked = opened.question(subject=lei, asked_at=asked_at, intent=intent, freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(asked, perspective=perspective)
        if _is_refusal(outcome):
            return outcome
        return _Answer(product=outcome.product, record=opened.record_of(outcome), served=outcome)


@pytest.fixture(scope="module")
def served(estate: str, example_modules: tuple[Any, Any, Any]) -> Any:
    """The demonstration obligor at the CP-14 instant, tolerance wide open."""
    outcome = _ask(example_modules)
    assert not _is_refusal(outcome), getattr(outcome, "reason", outcome)
    return outcome


def _is_refusal(outcome: Any) -> bool:
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    return isinstance(outcome, RefusalEnvelope)


def _lines(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [line for period in payload["periods"] for line in period["lines"].values()]


# --- the governed serve ------------------------------------------------------


def test_a_governed_served_product_of_the_required_class(
    served: Any, estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """The acceptance criterion: a real `ServedProduct` through the current
    governed resolver — `credit-risk.spread` on the lane `CP-SPEC-014` requires,
    its `asked_at` the CP-14 instant, a canonical content address, a debt
    assessment, and a replay record the served reference resolves to. Two runs
    of the same question agree byte for byte.

    Declared product gate `OFC-G01` (`CP-SPEC-003C` §G.1).
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415
    from ccf.replay.serve import ServedProduct  # noqa: PLC0415

    product = served.product
    assert isinstance(served.served, ServedProduct)
    assert product.schema_name == "credit-risk.spread"
    assert product.schema_version == "1.1.0"
    assert product.schema_version != "1.0.0", "the frozen specimen's lane is not this tree's"
    assert product.schema_version.split(".")[0] == "1", "CP-14 pins the major at 1.0.0"
    assert product.temporal_boundary == CP14_INSTANT
    assert product.tenant_id == "cp-03-canonical-demo"
    assert product.debt is not None and Decimal(0) <= product.debt.debt <= Decimal(1)
    assert served.record.content_generation_path.product_content_address == content_hash(product)
    again = _ask(example_modules)
    assert content_hash(again.product) == content_hash(product)


#: The one operator this product's specification names (`CP-SPEC-003C` §B.1:
#: "`policy.principal-subgraph`, and no other"). A literal on purpose: read
#: from the config it would agree with any second operator the config grew.
THE_ONE_OPERATOR = frozenset({"policy.principal-subgraph"})


def dimension_two_problems(record: Any, product: Any) -> list[str]:
    """Every way replay dimension 2 fails to cover the product's lineage.

    The predicate `OFC-G02` asserts empty and `OFC-G26` proves can be non-empty.
    Named rather than inlined so a negative control can reach the SAME
    comparison the gate makes, on a record it mutated.
    """
    problems: list[str] = []
    bindings = record.policy_bindings.bindings
    versions = {binding.version for binding in bindings}
    keys = {binding.key for binding in bindings}
    missing = set(product.lineage.policy_bundle_versions) - versions
    if missing:
        problems.append(f"dimension 2 does not cover lineage policy version(s) {sorted(missing)}")
    if "request_contract" not in keys:
        problems.append("dimension 2 carries no request-contract binding")
    invoked = set(product.lineage.operators_invoked)
    if invoked != set(THE_ONE_OPERATOR):
        problems.append(f"operators invoked {sorted(invoked)} are not exactly {sorted(THE_ONE_OPERATOR)}")
    if any("enrich" in name.lower() for name in invoked):
        problems.append("an operator named Enrich was invoked")
    return problems


def test_replay_dimension_two_is_a_superset_of_the_product_lineage(served: Any) -> None:
    """The record carries every governed artifact the product's lineage names,
    and more (the request contract that judged the question), and the operators
    invoked are exactly the ONE the class declares — nothing named `Enrich`.

    Declared product gate `OFC-G02` (`CP-SPEC-003C` §G.1).
    """
    assert dimension_two_problems(served.record, served.product) == []


# --- the rung's subject: per-attribute temporal validity as fabric state ------


def fabric_state_problems(record: Any, payload: dict[str, Any]) -> list[str]:
    """Every way the graph the record touched fails to BE the spread the payload
    serves — one `obligor`, one `spread_period` per served column, one
    `spread_line` per served line, the obligor's own URI among them.

    The predicate `OFC-G03` asserts empty and `OFC-G27` proves can be non-empty.
    A payload-only representation — the specimen's one entity carrying the
    whole spread — touches an obligor and nothing else, and this says so.
    """
    problems: list[str] = []
    touched = record.context_fabric_snapshot.touched_entities
    by_class: dict[str, int] = {}
    for uri in touched:
        by_class[uri.split("://")[0]] = by_class.get(uri.split("://")[0], 0) + 1
    if by_class.get("obligor") != 1:
        problems.append(f"{by_class.get('obligor', 0)} obligor entities touched, not 1")
    if by_class.get("spread_period", 0) != len(payload["periods"]):
        problems.append(f"{by_class.get('spread_period', 0)} spread_period entities touched for {len(payload['periods'])} served columns")
    if by_class.get("spread_line", 0) != len(_lines(payload)):
        problems.append(f"{by_class.get('spread_line', 0)} spread_line entities touched for {len(_lines(payload))} served lines")
    if payload["obligor"]["entity_id"] not in touched:
        problems.append("the served obligor's URI is not among the touched entities")
    return problems


def test_the_spread_is_fabric_state_not_a_payload_carried_in(served: Any) -> None:
    """Every served period and every served line is an entity the graph holds:
    replay dimension 1's touched set covers one `spread_period` per column and
    one `spread_line` per line, and the obligor. Π read the VIEW.

    Declared product gate `OFC-G03` (`CP-SPEC-003C` §G.1).
    """
    assert fabric_state_problems(served.record, served.product.payload) == []


def test_every_reported_figure_names_the_filing_that_asserted_it(served: Any) -> None:
    """Per attribute, not per product: every reported line carries its own
    `accession`, `filed_date`, `form` and `basis_applied`; the spread as a whole
    rests on MORE THAN ONE filing (a stitched spread), which a product-level
    stamp would erase; and the freshest of them is the served anchor.

    Declared product gate `OFC-G04` (`CP-SPEC-003C` §G.1).
    """
    payload = served.product.payload
    reported = [line for line in _lines(payload) if not line["derived"] and "accession" in line]
    assert reported, "no reported line at all"
    for line in reported:
        assert line["accession"] and line["filed_date"] and line["form"]
        assert line["basis_applied"] == payload["basis_applied"]
    assert len({line["accession"] for line in reported}) > 1
    assert max(line["filed_date"] for line in reported) == payload["latest_filed_in_payload"]
    # A declared line this obligor never filed is the WORD with a reason, never `0`.
    unfiled = [line for line in _lines(payload) if not line["derived"] and "accession" not in line]
    for line in unfiled:
        assert line["value"] == "NOT_EVALUABLE" and line["reason"]
    assert not any(line["value"] == "0" for line in unfiled)


def test_debt_is_the_specimens_method_read_off_the_graph(served: Any) -> None:
    """`D_c = 1 − F·C·S`: `C` is the evaluable fraction of declared lines in the
    payload, `S` is 1 (one store), and `F` is BELOW 1 — every column ages from
    its own filing under `decay_basis: valid-from`, not from the instant the
    fabric learned it. The debt is about the answer.

    Declared product gate `OFC-G05` (`CP-SPEC-003C` §G.1).
    """
    debt = served.product.debt
    lines = _lines(served.product.payload)
    evaluable = sum(1 for line in lines if line["value"] != "NOT_EVALUABLE")
    assert debt.factors.completeness == Decimal(evaluable) / Decimal(len(lines))
    assert debt.factors.semantic_consistency == Decimal(1)
    assert Decimal(0) < debt.factors.freshness < Decimal(1)
    assert debt.debt == Decimal(1) - debt.factors.freshness * debt.factors.completeness * debt.factors.semantic_consistency


# --- the declared window, and the SDK gap it stands beside ---------------------


def test_the_declared_window_is_held_by_the_products_own_gate(
    served: Any, estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """A spread whose freshest filing plus the declared window is not after the
    asked instant is REFUSED by the declared product gate, as a governed
    refusal naming the gate; the served one's anchor is inside the window.
    `STALE_AT_THE_INSTANT` is an obligor the estate shows filed before the
    window at the CP-14 instant; the refusal clears when it files again.

    Declared product gate `OFC-G06` (`CP-SPEC-003C` §G.1).
    """
    window = timedelta(seconds=int(_config()["ttl"]["product_ttl_seconds"]))
    anchor = datetime.fromisoformat(served.product.payload["latest_filed_in_payload"]).replace(tzinfo=UTC)
    assert CP14_INSTANT < anchor + window
    stale = _ask(example_modules, lei=_demonstration("STALE_AT_THE_INSTANT"))
    assert _is_refusal(stale)
    assert stale.reason == _config()["product_class"]["declared_product_gate"]["gate_id"]
    assert stale.kind == "product-invariant-refusal"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "CP03C-F-01: the governed path anchors the served contract's expires_at at"
        " the decision instant for every class; the declared ttl_anchor"
        " from_entity_freshness is recorded on the contract and not computed."
        " Turns red (XPASS) the day the SDK honors the declaration."
    ),
)
def test_expires_at_is_anchored_on_the_filing_not_the_question(
    served: Any, example_modules: tuple[Any, Any, Any]
) -> None:
    """The declaration says the expiry runs from the freshest filing in the
    payload. Measured: the governed path runs it from `asked_at`. This test
    asserts the DECLARATION and is quarantined as evidence of the gap.

    Declared product gate `OFC-G07` (`CP-SPEC-003C` §G.1).
    """
    window = timedelta(seconds=int(_config()["ttl"]["product_ttl_seconds"]))
    anchor = datetime.fromisoformat(served.product.payload["latest_filed_in_payload"]).replace(tzinfo=UTC)
    assert served.product.ttl_anchor == "from_entity_freshness"
    assert served.product.expires_at == anchor + window


# --- entitlement: suppression is indistinguishable from absence ---------------


def test_suppression_is_indistinguishable_from_absence(
    served: Any, estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """An obligor the principal may not see and an obligor that does not exist
    refuse with ONE reason, ONE kind, ONE detail and ONE field set. No count,
    no marker, no placeholder. That the principal's grant does not reach the
    obligor's jurisdiction is read from the estate, not assumed.

    Declared product gate `OFC-G08` (`CP-SPEC-003C` §G.1).
    """
    _, _, acquisition = example_modules
    unentitled = _demonstration("PRINCIPAL_WITH_NO_GRANT")
    jurisdiction = served.product.payload["obligor"]["obligor_jurisdiction"]
    assert jurisdiction not in acquisition.grant_for(unentitled, settings=_settings())
    absent = _ask(example_modules, lei="000000000000000000XX")
    suppressed = _ask(example_modules, principal_id=unentitled)
    assert _is_refusal(absent) and _is_refusal(suppressed)
    shell = ("reason", "kind", "detail", "fields", "key", "disclosure")
    assert {k: getattr(absent, k) for k in shell} == {k: getattr(suppressed, k) for k in shell}
    # And an entitled principal other than the default DOES see the obligor.
    entitled = _ask(example_modules, principal_id=_demonstration("PRINCIPAL_WITH_A_WIDER_GRANT"))
    assert not _is_refusal(entitled), getattr(entitled, "reason", entitled)


# --- intent: the axis the specimen declared as an argument --------------------


def test_intent_is_a_governed_axis_and_the_specimens_shadow_is_refused(
    estate: str, example_modules: tuple[Any, Any, Any], tmp_path: pathlib.Path
) -> None:
    """Defect A, both halves. The sibling judges `intent` against its declared
    discovery set and refuses a wrong one `class-mismatch` at `key=intent`, as
    data. And the SPECIMEN's shape — `intent` under `arguments.properties` —
    is refused by the SDK at contract construction: injected into a copy of
    this tree's own config, the boot refuses it by name. The sibling's own
    contract constructs.

    Declared product gate `OFC-G09` (`CP-SPEC-003C` §G.1).
    """
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.products.request import ProductRequestContract  # noqa: PLC0415

    wrong = _ask(example_modules, intent="covenant-check")
    assert _is_refusal(wrong)
    assert wrong.reason == "class-mismatch" and wrong.key == "intent"

    document = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert "intent" not in document["request_contract"]["arguments"]["properties"]
    shadow = yaml.safe_load(yaml.safe_dump(document))
    shadow["request_contract"]["arguments"]["properties"]["intent"] = {
        "type": "string", "description": "the specimen's shadow of the top-level axis",
    }
    path = tmp_path / "ccf_config.yaml"
    path.write_text(yaml.safe_dump(shadow), encoding="utf-8")
    with pytest.raises(Exception, match="shadow"):
        booted = load_config_and_boot(
            path, registry=ControlPlaneRegistry(), connection={"database_path": str(tmp_path / "shadow.sqlite3")}
        )
        try:
            ProductRequestContract.from_declared(booted.artifacts["request_contract"])
        finally:
            booted.handle.close()


# --- the declared refusals, as data -------------------------------------------


def test_declared_refusals_arrive_as_data_with_a_record(
    estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """`as_of` is declared and refused `not-supported-at-tier`; a `peer_basis`
    outside the declared domain is `not-in-domain`; a missing `debt_tolerance`
    is `missing-required-parameter`. Each names its key and carries a replay
    reference — nothing raised, nothing silently honored.

    Declared product gate `OFC-G10` (`CP-SPEC-003C` §G.1).
    """
    deployment, produce, _ = example_modules
    with tempfile.TemporaryDirectory() as scratch, produce.product(pathlib.Path(scratch)) as opened:
        asked = opened.question(
            subject=_demonstration("DEMONSTRATION_ANCHOR"), asked_at=CP14_INSTANT, intent=INTENT, freshness=FRESHNESS,
            parameters={deployment.DEBT_TOLERANCE: Decimal("1.0")},
        )
        with_as_of = opened.answer(asked.model_copy(update={"parameters": {**asked.parameters, "as_of": "2025-12-31"}}))
        missing = opened.answer(asked.model_copy(update={"parameters": {}}))
    assert _is_refusal(with_as_of) and with_as_of.reason == "not-supported-at-tier" and with_as_of.key == "as_of"
    domain = _ask(example_modules, peer_basis="sic-and-size")
    assert _is_refusal(domain) and domain.reason == "not-in-domain" and domain.key == "peer_basis"
    assert _is_refusal(missing) and missing.reason == "missing-required-parameter" and missing.key == "debt_tolerance"
    for refusal in (with_as_of, domain, missing):
        assert refusal.replay_reference.startswith("ccf-artifact://cp-03-canonical-demo/")


def test_the_callers_tolerance_governs_and_the_debt_does_not_move_with_it(
    served: Any, estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """At `CP-SPEC-014`'s own tolerance the spread is WITHHELD with the debt
    block; at a wide tolerance the same question serves the same assessment.
    The number did not move to fit the ceiling — estate truth, preserved.

    Declared product gate `OFC-G11` (`CP-SPEC-003C` §G.1).
    """
    withheld = _ask(example_modules, debt_tolerance="0.25")
    assert _is_refusal(withheld) and withheld.reason == "tolerance-exceeded"
    assert served.product.debt.debt > Decimal("0.25")
    assert served.product.debt.signal in {"forced_llm", "fail_closed"}


def test_the_basis_changes_a_figure_only_where_a_later_filing_changed_it(
    served: Any, estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """`latest-restated` lets the LATEST accession speak for every fact-cell,
    `as-reported` the EARLIEST. A cell filed more than once therefore names a
    different filing under the two bases; its VALUE differs only where a later
    filing changed it — exactly the lines marked `restated`. The basis selects
    within a cell, never across cells: both payloads carry the same columns
    and the same lines.

    Declared product gate `OFC-G12` (`CP-SPEC-003C` §G.1).
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    restated = _ask(example_modules, basis="latest-restated")
    assert not _is_refusal(restated)
    assert restated.product.payload["basis_applied"] == "latest-restated"

    def reported(outcome: Any) -> dict[tuple[str, str, str], dict[str, Any]]:
        return {
            (p["period_end"], p["fiscal_period"], n): l
            for p in outcome.product.payload["periods"]
            for n, l in p["lines"].items()
            if not l["derived"] and "accession" in l
        }

    first, second = reported(served), reported(restated)
    assert set(first) == set(second), "the basis changed WHICH cells exist"
    value_changed = {key for key in first if first[key]["value"] != second[key]["value"]}
    assert value_changed, "no restated figure to observe on this obligor"
    for key in value_changed:
        assert first[key]["restated"] and second[key]["restated"], key
    filing_changed = {key for key in first if first[key]["accession"] != second[key]["accession"]}
    assert value_changed <= filing_changed
    assert content_hash(served.product) != content_hash(restated.product)


# --- the canonical shape, read off the tree -------------------------------------


def _classifier() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_spine_separation", REPO_ROOT / "tests" / "examples" / "test_spine_separation.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_structural_classifier_reads_this_tree_as_canonical() -> None:
    """Defect B, absent by construction — and, as of `D-IMPL-343`, the whole
    governed spine too. Something here opens the product on the PAVED road
    (`open_product`, which composes `GovernedResolver` on this tree's behalf),
    nothing here composes the resolver itself, and nothing here calls
    `run_gates`, `build_replay_record` or `serve` — so the specimen's call
    with no resolution binding has nowhere to exist, and the tree publishes
    ONE spine rather than two. The classifier reads `"paved"`; a tree that
    did both would read `"double-spined"` and be refused by name.

    Declared product gate `OFC-G13` (`CP-SPEC-003C` §G.1).
    """
    classifier = _classifier()
    assert classifier.shape_of(EXAMPLE) == "paved"
    assert classifier.paved_entry(EXAMPLE)
    assert classifier.resolver_ownership(EXAMPLE) == []
    assert classifier.governed_seam_calls(EXAMPLE) == {}
    assert classifier.legacy_governance_regions(EXAMPLE) == []
    assert classifier.spine_problems(EXAMPLE) == []
    for path in EXAMPLE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "build_replay_record(" not in text, path
        # `D-IMPL-343` criterion 4: the paved road can make neither of these.
        assert "ProductRequestViolation(" not in text, path
        assert "ReferencePolicyConstraintResolver(" not in text, path


def test_the_plan_factory_takes_its_operators_only_from_required() -> None:
    """`D-IMPL-137` row C, read off the tree by the SDK's own predicate; the
    factory is NAMED so the property is readable rather than merely true.

    Declared product gate `OFC-G14` (`CP-SPEC-003C` §G.1).
    """
    spec = importlib.util.spec_from_file_location(
        "_gate_two", REPO_ROOT / "tests" / "products" / "test_gate_two_call_shape.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    path = EXAMPLE / "produce.py"
    factory = next(
        node for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef) and node.name == "plan_factory"
    )
    assert module._sdk_supplied_operator_set(factory, path)
    assert module._constructed_plan_sources(factory, None) == (("required",),)


# --- the negative boundaries ----------------------------------------------------


def test_the_specimen_is_untouched_and_no_identity_is_reused(served: Any) -> None:
    """cp-03 is frozen under `D-IMPL-261`: ZERO files changed by this work,
    measured against the branch point. And this determination is its own —
    not the specimen's published content address, not its replay record, not
    its debt figure, and no snippet include from its tree.

    Declared product gate `OFC-G15` (`CP-SPEC-003C` §G.1).
    """
    base = subprocess.run(
        ["git", "merge-base", "HEAD", "main"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-only", base, "--", str(SPECIMEN.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert changed == [], f"the frozen specimen was modified: {changed}"
    assert served.product.debt.debt != Decimal("0.8782"), "the specimen's published debt figure"
    specimen_identities = {
        "e2a0224fa5c9",  # the specimen's published content address
        "ad70fa4b5110",  # its published replay record
    }
    for path in EXAMPLE.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for identity in specimen_identities:
            assert identity not in text, f"{path.name} reuses specimen identity {identity}"
        assert "cp-03-obligor-financial-spread/" not in text.replace(
            "examples/cp-03-obligor-financial-spread", "«named-in-prose»"
        ), f"{path.name} includes a snippet from the frozen specimen"


# --- the shared-fabric defect the door probe found (`CP03C-F-02`) --------------


def test_a_fresh_fabric_per_run_and_one_determination_across_roots(
    served: Any, estate: str, example_modules: tuple[Any, Any, Any]
) -> None:
    """The paved road mints a FRESH fabric per question under one scratch, from
    the substrate the environment document declares: two questions under one
    opened product leave two substrate files. So several questions under ONE
    scratch are several fabrics — an obligor served after another under the
    same scratch hashes to the address it hashes to alone. Measured before the
    per-question mint existed (`CP03C-F-02`): the second obligor's view held
    the first, and the debt was scored over both. The mechanism is the SDK's
    now, not a uuid this tree remembers.

    Declared product gate `OFC-G24` (`CP-SPEC-003C` §G.1).
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    deployment, produce, _ = example_modules
    substrate = _environment()["substrate"]
    instant = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)  # the stale obligor's own serving instant

    def question(opened: Any, lei: str) -> Any:
        return opened.question(
            subject=lei, asked_at=instant, intent=INTENT, freshness=FRESHNESS,
            parameters={deployment.DEBT_TOLERANCE: Decimal("1.0")},
        )

    with tempfile.TemporaryDirectory() as scratch, produce.product(pathlib.Path(scratch)) as opened:
        first = opened.answer(question(opened, _demonstration("DEMONSTRATION_ANCHOR")))
        second = opened.answer(question(opened, _demonstration("STALE_AT_THE_INSTANT")))
        minted = sorted(pathlib.Path(scratch).glob(f"{substrate['prefix']}_*{substrate['suffix']}"))
        assert len(minted) == 2 and minted[0] != minted[1], minted
    assert not _is_refusal(first) and not _is_refusal(second)
    with tempfile.TemporaryDirectory() as fresh, produce.product(pathlib.Path(fresh)) as opened:
        alone = opened.answer(question(opened, _demonstration("STALE_AT_THE_INSTANT")))
    assert not _is_refusal(alone)
    assert content_hash(second.product) == content_hash(alone.product)
    assert second.product.debt.debt == alone.product.debt.debt


def test_the_projection_serves_the_subjects_claims_and_no_others(
    example_modules: tuple[Any, Any, Any]
) -> None:
    """Π is scoped to the request's subject: handed a view holding TWO
    obligors' spreads, it serves the subject's periods and lines and none of
    the other's, and handed a view holding only the other's it serves no
    obligor at all — which the product's own gate then refuses. No estate is
    needed to prove a projection; the view is built here.

    Declared product gate `OFC-G25` (`CP-SPEC-003C` §G.1).
    """
    from ccf.contracts.claims import EntityClaim, LineageEntry  # noqa: PLC0415
    from ccf.graph.protocols import EntityRecord, GraphView  # noqa: PLC0415
    from ccf.projection.plan import Perspective  # noqa: PLC0415
    from ccf.signal.envelope import SourceIdentity  # noqa: PLC0415

    sys.path.insert(0, str(EXAMPLE))
    try:
        import projection  # noqa: PLC0415
    finally:
        sys.path.remove(str(EXAMPLE))

    at = CP14_INSTANT

    def record(entity_class: str, ref: str, **attributes: str) -> EntityRecord:
        claim = EntityClaim(
            tenant_id="t", observed_at=at, entity_uri=f"{entity_class}://{ref}", entity_class=entity_class,
            attributes=attributes,
            lineage=frozenset({LineageEntry(source=SourceIdentity(system_id="test"), envelope_id=ref, observed_at=at)}),
        )
        return EntityRecord(claim_id=ref, claim=claim, policy_bundle_version="v")

    def spread(lei: str) -> list[EntityRecord]:
        common = {"lei": lei, "obligor_jurisdiction": "US-DE"}
        return [
            record("obligor", f"o-{lei}", **common, cik="1", obligor_legal_name=lei, fiscal_year_end_month="12",
                   latest_filed_date="2026-08-10", formally_restated="false", basis_applied="as-reported",
                   spread_periods="1", peer_cohort_basis="sic", peer_sic="6200", peer_cohort_size="0"),
            record("spread_period", f"p-{lei}", **common, period_end="2026-06-30", fiscal_period="Q2",
                   signal_class="quarterly_facts", latest_filed="2026-08-10"),
            record("spread_line", f"l-{lei}", **common, period_end="2026-06-30", fiscal_period="Q2", line="revenue",
                   derived="false", value=f"{len(lei)}", unit="USD", kind="duration", period_start="2026-04-01",
                   filed_date="2026-08-10", accession=f"acc-{lei}", form="10-Q", basis_applied="as-reported",
                   restated="false", restatement_class="NOT_EVALUABLE", kind_conflict="false", inputs="", reason=""),
        ]

    mine, theirs = "LEI-MINE-000000000001", "LEI-THEIRS-00000000002"
    both = GraphView(tenant_id="t", as_of=at, entities=tuple(spread(theirs) + spread(mine)))
    plan = projection.FinancialSpreadProjection(plan_id="p", required=("policy.principal-subgraph",), subject=mine)
    perspective = Perspective(principal_id="PRIN-COV-001", role="analyst")
    payload = plan.invoke(view=both, operator_outputs={}, perspective=perspective, temporal_boundary=at).payload
    assert payload["obligor"]["lei"] == mine
    assert payload["obligor"]["entity_id"] == f"obligor://o-{mine}"
    assert [p["lines"]["revenue"]["accession"] for p in payload["periods"]] == [f"acc-{mine}"]

    only_theirs = GraphView(tenant_id="t", as_of=at, entities=tuple(spread(theirs)))
    payload = plan.invoke(view=only_theirs, operator_outputs={}, perspective=perspective, temporal_boundary=at).payload
    assert payload["obligor"] is None


# --- negative controls for the two predicates (the ruling on S14 / S16) ----------


def test_the_dimension_two_predicate_refuses_a_record_that_no_longer_covers_the_lineage(
    served: Any,
) -> None:
    """`OFC-G02`'s comparison can fail, shown on the served record itself, one
    relationship at a time: the request-contract binding removed from
    dimension 2; the lineage's policy version removed from dimension 2; a
    second operator in the lineage; an operator named Enrich. Each is refused
    by name, and the untouched record passes.

    THE LIMITATION, stated rather than claimed away: no SDK guard makes these
    states unreachable. Dimension 2 is built by
    `GovernedResolver._applied_bindings` from the sources the resolution
    consulted and stored verbatim by `build_replay_record`; no validator
    cross-checks it against the product's lineage, so a record whose
    dimension 2 omits the contract binding still CONSTRUCTS (asserted below).
    A deployment on the canonical path never touches dimension 2, which is why
    the tree-level mutation that reaches this assertion is a second declared
    operator (the sabotage record's S14b) and not a broken binding. This
    control proves the assertion can fail; it does not prove the SDK refuses
    the state.

    Declared product gate `OFC-G26` (`CP-SPEC-003C` §G.1).
    """
    from ccf.replay.record import DecisionReplayRecord  # noqa: PLC0415

    record, product = served.record, served.product
    assert dimension_two_problems(record, product) == []

    def with_bindings(keep: Any) -> Any:
        snapshot = record.policy_bindings
        return record.model_copy(
            update={"policy_bindings": snapshot.model_copy(update={"bindings": tuple(b for b in snapshot.bindings if keep(b))})}
        )

    without_contract = with_bindings(lambda b: b.key != "request_contract")
    assert any("request-contract" in p for p in dimension_two_problems(without_contract, product))
    version = next(iter(product.lineage.policy_bundle_versions))
    without_policy = with_bindings(lambda b: b.version != version)
    assert any("does not cover" in p for p in dimension_two_problems(without_policy, product))

    def with_operators(names: frozenset[str]) -> Any:
        return product.model_copy(update={"lineage": product.lineage.model_copy(update={"operators_invoked": names})})

    second = with_operators(product.lineage.operators_invoked | {"traversal.typed-neighborhood"})
    assert any("not exactly" in p for p in dimension_two_problems(record, second))
    enriched = with_operators(product.lineage.operators_invoked | {"enrich.narrative"})
    assert any("Enrich" in p for p in dimension_two_problems(record, enriched))

    # No upstream guard: the defective record constructs.
    DecisionReplayRecord.model_validate(without_contract.model_dump(mode="json"))


def test_the_fabric_state_predicate_refuses_a_payload_only_representation(served: Any) -> None:
    """`OFC-G03`'s comparison can fail, shown on the served record itself: a
    dimension 1 that touched the obligor and nothing else — the specimen's
    one-entity representation, with the spread carried in the payload rather
    than held by the graph — is refused for its missing periods and lines; a
    dimension 1 missing one line is refused for that line; the untouched
    record passes.

    THE LIMITATION, stated: the touched set is the SDK's own record of the
    entities the execution read (`ExecutionEvidence` → dimension 1), and no
    validator compares it to the payload. The state is reachable from a
    deployment by construction — ingest one envelope and render the periods
    from a side channel — which the sabotage record's S16b does; this control
    proves the assertion can fail, it does not prove the SDK refuses the state.

    Declared product gate `OFC-G27` (`CP-SPEC-003C` §G.1).
    """
    from ccf.replay.record import DecisionReplayRecord  # noqa: PLC0415

    record, payload = served.record, served.product.payload
    assert fabric_state_problems(record, payload) == []
    snapshot = record.context_fabric_snapshot
    touched = snapshot.touched_entities

    def with_touched(keep: Any) -> Any:
        return record.model_copy(
            update={"context_fabric_snapshot": snapshot.model_copy(update={"touched_entities": type(touched)(u for u in touched if keep(u))})}
        )

    payload_only = with_touched(lambda u: u.startswith("obligor://"))
    problems = fabric_state_problems(payload_only, payload)
    assert any("spread_period" in p for p in problems) and any("spread_line" in p for p in problems)
    one_line = next(u for u in touched if u.startswith("spread_line://"))
    assert any("spread_line" in p for p in fabric_state_problems(with_touched(lambda u: u != one_line), payload))

    # No upstream guard: the defective record constructs.
    DecisionReplayRecord.model_validate(payload_only.model_dump(mode="json"))
