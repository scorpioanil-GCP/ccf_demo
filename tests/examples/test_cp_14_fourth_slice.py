"""CP-14 completion — five children through five doors, both outcomes, the four proofs.

The CP-14 completion GO (Dave, 2026-09-17). The covenant slot is RE-POINTED to
the paved successor `examples/cp-13-canonical-covenant-cross-reference`; the
exposure slot reaches frozen cp-05 through the wrapper door
`examples/door-cp-05-credit-exposure-rollup`; the covenant question is now
DETERMINED by the consumer from the obligor's own facility documents
(`CP14-F-28`). This module asks the same composite the same question with all
FIVE doors live, each in its own process, at the governed tolerance and at the
labeled diagnostic, and holds what the GO asked to be demonstrated:

1. **The normal governed question** (0.25) — every producer that measures a
   debt above the memo's tolerance withholds; the composite refuses on its
   required slots; five rows persist; the producers' own reasons are retained.
2. **The labeled diagnostic** (1.0) — whichever children serve are admitted
   under `provider-controls`; what the composite then does is MEASURED, never
   promised.
3. **A meaningful child-content change changes the corresponding parent
   payload field** — a controlled question variant on one child, every other
   input fixed.
4. **Acquisition and composition use the same admitted child contracts** — the
   address the memo composed from is the address the row admitted.
5. **Served reconstruction uses retained inputs without calling providers
   again** — replay with every producer process exited.
6. **Refused reconstruction preserves the admitted-child evidence and follows
   the recorded execution path** — `replay_refusal` with the producers exited.

**Reads the estate, seeds nothing.** The five producer processes and the
consumer's own roster and ledger legs read the live estate.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.products.child_resolver import ChildQuestion
from ccf.products.composition import compose_expiry, compose_lineage
from ccf.products.contract import ChildRequirement, ContextProductContract, MaxTTL, ProductLineage
from ccf.products.product import open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.record import NO_FABRIC_READ, DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.examples.test_cp_03_canonical_cross_deployment import DEV_TOKEN, producer as spread_producer
from tests.examples.test_cp_14_first_slice import BGC, BGC_FACILITY, CHILD_CLASSES, CP14_INSTANT, EXAMPLE, modules  # noqa: F401
from tests.examples.test_cp_14_second_slice import _rows, family_producer
from tests.examples.test_cp_14_third_slice import collateral_producer

pytestmark = [pytest.mark.postgres, pytest.mark.fluree, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
COVENANT_EXAMPLE = REPO_ROOT / "examples" / "cp-13-canonical-covenant-cross-reference"
EXPOSURE_DOOR = REPO_ROOT / "examples" / "door-cp-05-credit-exposure-rollup"
PRODUCER_TREES = (
    REPO_ROOT / "examples" / "cp-03-canonical-obligor-financial-spread",
    REPO_ROOT / "examples" / "cp-04-canonical-corporate-family-tree",
    REPO_ROOT / "examples" / "cp-05-credit-exposure-rollup",
    REPO_ROOT / "examples" / "cp-06-canonical-collateral-and-setoff-coverage",
    COVENANT_EXAMPLE, EXPOSURE_DOOR,
)
SPREAD, FAMILY, EXPOSURE, COLLATERAL, COVENANT = CHILD_CLASSES
PRODUCERS = {
    SPREAD: ("cp-03-canonical-obligor-financial-spread-egress", "cp-03-canonical-demo"),
    FAMILY: ("cp-04-canonical-corporate-family-tree-egress", "cp-04-canonical-demo"),
    EXPOSURE: ("cp-05-credit-exposure-rollup-egress", "cp-05-demo"),
    COLLATERAL: ("cp-06-canonical-collateral-and-setoff-coverage-egress", "cp-06-canonical-demo"),
    COVENANT: ("cp-13-canonical-covenant-cross-reference-egress", "cp-13-canonical-demo"),
}
GOVERNED, DIAGNOSTIC = "0.25", "1.0"
#: The document key BGC's one facility names on the roster (measured 2026-09-17),
#: read back from the question the consumer asked — never pinned as a count.
CP14_DOCUMENT = "0001213900-26-057808:ea029103901ex10-1.htm"

ESTATE_VARIABLES = (
    "CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA", "CCF_CP_14_FLUREE_URL", "CCF_CP_14_FLUREE_LEDGER",
    "CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA",
    "CCF_CP_04C_FLUREE_URL", "CCF_CP_04C_FLUREE_LEDGER", "CCF_CP_04C_POSTGRES_DSN", "CCF_CP_04C_POSTGRES_SCHEMA",
    "CCF_CP_05_FLUREE_URL", "CCF_CP_05_FLUREE_LEDGER", "CCF_CP_05_POSTGRES_DSN", "CCF_CP_05_POSTGRES_SCHEMA",
    "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER", "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
    "CCF_CP_13C_POSTGRES_DSN", "CCF_CP_13C_POSTGRES_SCHEMA", "CCF_CP_13C_FLUREE_URL", "CCF_CP_13C_FLUREE_LEDGER",
    "CCF_CP_13C_MONGO_URI", "CCF_CP_13C_MONGO_DB",
)
CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
ENVIRONMENT: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _door(run: pathlib.Path, token_var: str) -> Iterator[str]:
    """One producer process — a tree's own `run.py --door`, the credential SET through its declared name."""
    env = {**os.environ, token_var: DEV_TOKEN}
    process = subprocess.Popen([sys.executable, str(run), "--door"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"{run.parent.name}'s door did not announce readiness ({announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def covenant_producer() -> Any:
    return _door(COVENANT_EXAMPLE / "run.py", "CCF_CP_13C_DOOR_TOKEN")


def exposure_producer() -> Any:
    return _door(EXPOSURE_DOOR / "run.py", "CCF_CP_05_DOOR_TOKEN")


@contextmanager
def five_doors(estate: None) -> Iterator[dict[str, str]]:
    """All five producers, each in its own process; the consumer's environment mapping."""
    with ExitStack() as stack:
        urls = {
            "SPREAD": stack.enter_context(spread_producer(estate)),
            "FAMILY": stack.enter_context(family_producer()),
            "EXPOSURE": stack.enter_context(exposure_producer()),
            "COLLATERAL": stack.enter_context(collateral_producer()),
            "COVENANT": stack.enter_context(covenant_producer()),
        }
        yield {
            "CCF_CP_14_POSTGRES_DSN": os.environ["CCF_CP_14_POSTGRES_DSN"],
            "CCF_CP_14_POSTGRES_SCHEMA": os.environ["CCF_CP_14_POSTGRES_SCHEMA"],
            "CCF_CP_14_FLUREE_URL": os.environ["CCF_CP_14_FLUREE_URL"],
            "CCF_CP_14_FLUREE_LEDGER": os.environ["CCF_CP_14_FLUREE_LEDGER"],
            **{f"CCF_CP14_{name}_URL": url for name, url in urls.items()},
            **{f"CCF_CP14_{name}_TOKEN": DEV_TOKEN for name in urls},
        }


def _question(opened: Any, deployment: Any, *, tolerance: str) -> ProductRequest:
    return opened.question(
        subject=BGC, asked_at=CP14_INSTANT, intent="annual-review", freshness="decision-scoped",
        parameters={deployment.AS_OF: CP14_INSTANT.isoformat(), deployment.DEBT_TOLERANCE: Decimal(tolerance), deployment.FACILITY_ID: BGC_FACILITY},
    )


def _record_of(opened: Any, outcome: Any) -> DecisionReplayRecord:
    fresh = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    if isinstance(outcome, ServedProduct):
        address = outcome.replay_ref.content_address
    else:
        address = fresh.resolve_uri(uri=outcome.replay_reference)
    return DecisionReplayRecord.model_validate_json(fresh.get(content_address=address))


def _ask(modules: tuple[Any, Any], scratch: pathlib.Path, *, environ: dict[str, str], tolerance: str) -> tuple[Any, Any, DecisionReplayRecord]:
    """One memo question on the paved road; the record reloaded from a FRESH store instance."""
    produce, deployment = modules
    with produce.product(scratch, environ=environ) as opened:
        outcome = opened.answer(_question(opened, deployment, tolerance=tolerance))
        return opened, outcome, _record_of(opened, outcome)


def _retained(opened: Any, address: str) -> ContextProductContract:
    store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    contract = ContextProductContract.model_validate_json(store.get(content_address=address))
    assert content_hash(contract) == address
    return contract


@pytest.fixture(scope="module")
def both(modules: tuple[Any, Any], estate: None, tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Any, Any, DecisionReplayRecord]]:
    """Both questions with FIVE doors live — asked once per module; every producer
    process has exited by the time any test reads the results."""
    scratch = tmp_path_factory.mktemp("slice4")
    with five_doors(estate) as environ:
        return {tolerance: _ask(modules, scratch / tolerance, environ=environ, tolerance=tolerance) for tolerance in (DIAGNOSTIC, GOVERNED)}


# --- both outcomes, measured ------------------------------------------------------------


def test_the_governed_question_withholds_where_producers_withhold_and_refuses_the_composite(both: dict[str, Any]) -> None:
    """At the memo's own tolerance every producer whose measured debt exceeds it
    withholds (`ineligible`, the producer's reason retained); every child that
    serves under it is admitted; the composite refuses on its required slots
    with all five rows persisted — the refusal path, and only that, is proven
    here (spec §D.3 scenario 8).

    Declared product gate `CMC-G18` (`CP-SPEC-014` §D.5).
    Declared product gate `CMC-G22` (`CP-SPEC-014` §D.5).
    Declared product gate `CMC-G26` (`CP-SPEC-014` §D.5).
    """
    opened, outcome, record = both[GOVERNED]
    assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "composite-child-refusal" and outcome.reason == "child_admission"
    rows = _rows(record)
    assert all(row.child_question_address is not None for row in rows.values()), "a producer was not asked"
    assert {row.outcome_status for row in rows.values()} <= {"admitted", "ineligible"}, {c: r.outcome_status for c, r in rows.items()}
    withheld = {c for c, r in rows.items() if r.outcome_status == "ineligible"}
    admitted = {c for c, r in rows.items() if r.outcome_status == "admitted"}
    assert withheld and admitted, "the governed question must show both a withholding producer and an admitted one on this estate"
    for product_class in admitted:
        _retained(opened, rows[product_class].child_content_address)
    retained = json.loads(record.content_generation_path.assembly_refusal)["detail"]
    assert "tolerance-exceeded" in retained and "producer-unavailable" not in retained and "no-producing-skill" not in retained, retained
    assert "tolerance-exceeded" not in outcome.detail, "the disclosed envelope stays minimal (CMC-G26)"
    for product_class, row in rows.items():
        assert (row.producer_id, row.producer_tenant) == PRODUCERS[product_class], (product_class, row.producer_id, row.producer_tenant)


def test_the_diagnostic_admits_every_child_that_serves_and_the_composite_outcome_is_measured(both: dict[str, Any]) -> None:
    """At the labeled diagnostic every producer serves and every child is
    admitted under `provider-controls` from its own registration; what the
    composite then does is stated as measured — served, with five sections
    composed from five admitted contracts, or refused on its own gates."""
    opened, outcome, record = both[DIAGNOSTIC]
    rows = _rows(record)
    for product_class, row in rows.items():
        assert row.outcome_status == "admitted" and row.eligibility_basis == "provider-controls", (product_class, row.outcome_status, row.refusal_ref)
        assert row.child_asked_at == CP14_INSTANT and row.child_content_address
        assert (row.producer_id, row.producer_tenant) == PRODUCERS[product_class]
        child = _retained(opened, row.child_content_address)
        assert child.tenant_id == PRODUCERS[product_class][1] and child.temporal_boundary == CP14_INSTANT
    assert isinstance(outcome, ServedProduct), (type(outcome).__name__, getattr(outcome, "kind", None), getattr(outcome, "detail", None))
    sections = outcome.product.payload["sections"]
    assert sorted(sections) == sorted(CHILD_CLASSES)
    assert isinstance(sections[EXPOSURE]["summary"]["gross_committed"], int) and sections[EXPOSURE]["summary"]["gross_committed"] > 0
    assert Decimal(sections[COLLATERAL]["summary"]["coverage_ratio"]) > 0 and sections[COLLATERAL]["summary"]["facility"] == BGC_FACILITY
    assert sections[COVENANT]["summary"]["checked_citations"] >= 0 and sections[COVENANT]["summary"]["chain_nodes"] > 0
    assert sections[FAMILY]["summary"]["entities"] > 1
    assert sections[SPREAD]["summary"]["periods"] > 0


def test_acquisition_and_composition_use_the_same_admitted_child_contracts(both: dict[str, Any]) -> None:
    """The address each section was composed from is the address the row
    admitted — five for five — and the memo's lineage is the set-union of its
    own operators with every admitted child's, and outlives no admitted child.

    Declared product gate `CMC-G02` (`CP-SPEC-014` §D.5).
    Declared product gate `CMC-G03` (`CP-SPEC-014` §D.5).
    Declared product gate `CMC-G20` (`CP-SPEC-014` §D.5).
    """
    opened, outcome, record = both[DIAGNOSTIC]
    assert isinstance(outcome, ServedProduct)
    rows = _rows(record)
    sections = outcome.product.payload["sections"]
    for product_class, row in rows.items():
        assert sections[product_class]["child_content_address"] == row.child_content_address, product_class
        assert sections[product_class]["child_tenant"] == row.producer_tenant
    children_ops = set().union(*(set(row.child_operators_invoked or ()) for row in rows.values()))
    own = set(CONFIG["product_class"]["required_operator_keys"])
    assert set(outcome.product.lineage.operators_invoked) == own | children_ops
    assert set(record.content_generation_path.operator_plan) == own
    stalest = min(row.child_expires_at for row in rows.values() if row.child_expires_at)
    assert outcome.product.expires_at <= stalest, "the memo outlives its stalest admitted child (CMC-G03)"
    assert outcome.product.expires_at <= CP14_INSTANT + timedelta(seconds=int(CONFIG["ttl"]["max_ttl_seconds"])) + timedelta(hours=1)


def test_inherited_debt_is_the_per_factor_minimum_across_children_weak_on_different_factors(both: dict[str, Any]) -> None:
    """Two children weak on DIFFERENT factors — the exposure child on freshness,
    the covenant child on completeness — so the per-factor minimum and the
    scalar maximum of child debts disagree, and the memo carries the minimum
    per factor.

    Declared product gate `CMC-G19` (`CP-SPEC-014` §D.5).
    """
    opened, outcome, record = both[DIAGNOSTIC]
    assert isinstance(outcome, ServedProduct)
    rows = _rows(record)
    exposure = _retained(opened, rows[EXPOSURE].child_content_address)
    covenant = _retained(opened, rows[COVENANT].child_content_address)
    assert Decimal(str(exposure.debt.factors.freshness)) < Decimal(str(covenant.debt.factors.freshness))
    assert Decimal(str(covenant.debt.factors.completeness)) < Decimal(str(exposure.debt.factors.completeness))
    children = [_retained(opened, row.child_content_address) for row in rows.values()]
    memo = outcome.product.debt.factors
    assert Decimal(str(memo.freshness)) <= min(Decimal(str(c.debt.factors.freshness)) for c in children)
    assert Decimal(str(memo.completeness)) <= min(Decimal(str(c.debt.factors.completeness)) for c in children)
    assert Decimal(str(memo.semantic_consistency)) <= min(Decimal(str(c.debt.factors.semantic_consistency)) for c in children)


# --- the content-composition proof (a controlled variant) --------------------------------


def _variant_questions(deployment: Any) -> Any:
    """The deployment's own mapping with ONE change: the collateral child is
    asked WITHOUT haircuts — a meaningful content change on one child, every
    other question byte-identical."""

    def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        asked = deployment.questions(requirement, request)
        if requirement.product_class != COLLATERAL:
            return asked
        return ChildQuestion(subject=asked.subject, intent=asked.intent, freshness=asked.freshness, parameters={**asked.parameters, "apply_haircuts": False})

    return questions


def test_a_meaningful_child_content_change_changes_the_corresponding_parent_field(
    both: dict[str, Any], modules: tuple[Any, Any], estate: None, tmp_path: pathlib.Path
) -> None:
    """A CONTROLLED variant, identified as such: the collateral child asked
    without haircuts, every other input fixed. The collateral section's coverage
    figure and address move, the other four sections' addresses do not, and the
    memo's own address moves with its child.

    Declared product gate `CMC-G28` (`CP-SPEC-014` §D.5).
    """
    opened, baseline, record = both[DIAGNOSTIC]
    assert isinstance(baseline, ServedProduct)
    produce, deployment = modules
    with five_doors(estate) as environ:
        variant = open_product(
            config_root=EXAMPLE, scratch=tmp_path / "variant", acquire=deployment.acquire, project=produce.MemoPlanFactory(),
            assess=deployment.assess, questions=_variant_questions(deployment), environ=environ,
        )
        with variant as opened_variant:
            deployment.questions.bind(opened_variant.sources)
            outcome = opened_variant.answer(_question(opened_variant, deployment, tolerance=DIAGNOSTIC))
            assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
            variant_rows = _rows(_record_of(opened_variant, outcome))
    base_rows = _rows(record)
    base_sections, variant_sections = baseline.product.payload["sections"], outcome.product.payload["sections"]
    assert Decimal(variant_sections[COLLATERAL]["summary"]["coverage_ratio"]) > Decimal(base_sections[COLLATERAL]["summary"]["coverage_ratio"])
    assert variant_sections[COLLATERAL]["child_content_address"] != base_sections[COLLATERAL]["child_content_address"]
    assert variant_rows[COLLATERAL].child_content_address == variant_sections[COLLATERAL]["child_content_address"]
    for product_class in (SPREAD, FAMILY, EXPOSURE, COVENANT):
        assert variant_sections[product_class] == base_sections[product_class], product_class
        assert variant_rows[product_class].child_content_address == base_rows[product_class].child_content_address
    assert content_hash(outcome.product.payload) != content_hash(baseline.product.payload)


# --- the covenant question is DETERMINED, not invented ------------------------------------


def test_the_covenant_question_names_the_obligors_own_evidence_nodes(both: dict[str, Any], modules: tuple[Any, Any]) -> None:
    """The consumer determined the covenant question from the obligor's facility
    documents: the mapping, bound to the deployment's own sources, names the
    evidence nodes of BGC's own document and nothing below them; the admitted
    child answers exactly those sources (the parent logic `CP14-F-28` owed)."""
    opened, outcome, record = both[DIAGNOSTIC]
    assert isinstance(outcome, ServedProduct)
    _produce, deployment = modules
    row = _rows(record)[COVENANT]
    requirement = next(r for r in opened.declaration.requires if r.product_class == COVENANT)
    deployment.questions.bind(opened.sources)
    asked = deployment.questions(requirement, record.content_generation_path.request.model_copy(update={"parameters": {
        deployment.AS_OF: CP14_INSTANT.isoformat(), deployment.DEBT_TOLERANCE: Decimal(DIAGNOSTIC), deployment.FACILITY_ID: BGC_FACILITY, deployment.MEMO_TYPE: "annual-review",
    }}))
    sources = asked.parameters["covenant_sources"]
    assert sources and all(CP14_DOCUMENT.split(":")[0].replace("-", "") in s for s in sources), sources
    assert set(asked.parameters) == {"covenant_sources", "debt_tolerance"} and asked.subject == BGC
    child = _retained(opened, row.child_content_address)
    assert sorted(s["source_uri"] for s in child.payload["cross_references"]) == sorted(sources)
    assert child.plan_id.endswith(f"/{BGC}")


# --- reconstruction with every producer exited --------------------------------------------


class _MemoReplayEnvironment:
    """A replay environment built from the RECORD and the memo's two documents —
    the children come from the RETAINED contracts, never from a producer."""

    def __init__(self, *, modules: tuple[Any, Any], opened: Any, fabric: Any, record: DecisionReplayRecord) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        self._produce = modules[0]
        path = record.content_generation_path
        assert path.request is not None
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver._operator_parameters(self._request),
            view=fabric.handle.reader.as_of(tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary),
            pins=fabric.pins, policy_bundle_key=self._policy_key,
        )
        self.composite_plans = 0

    def resolve_plan(self, *, plan_id: str) -> Any:
        raise LookupError(f"{plan_id!r} is a composite plan and needs its children")

    def resolve_composite_plan(self, *, plan_id: str, children: Any) -> Any:
        self.composite_plans += 1
        return self._produce.MemoPlanFactory().build_with_children(required=self._required, request=self._request, children=children)

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        return self._operators

    def rehydrate_product(self, *, record: DecisionReplayRecord, projection: Any) -> ContextProductContract:
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        rows = tuple(r for r in path.child_resolutions if r.outcome_status == "admitted")
        own = ProductLineage(
            operators_invoked=frozenset(path.operator_plan),
            policy_bundle_versions=frozenset(b.version for b in record.policy_bindings.bindings if b.key == self._policy_key),
            graph_snapshot_at=snapshot.temporal_boundary,
        )
        lineage = compose_lineage([own, *(ProductLineage(
            operators_invoked=r.child_operators_invoked or frozenset(), policy_bundle_versions=r.child_policy_bundle_versions or frozenset(),
            graph_snapshot_at=r.child_graph_snapshot_at or snapshot.temporal_boundary,
        ) for r in rows)])
        return ContextProductContract(
            schema_name=CONFIG["product_class"]["schema_name"], schema_version=CONFIG["product_class"]["schema_version"],
            plan_id=projection.plan_id, tenant_id=record.tenant_id, temporal_boundary=snapshot.temporal_boundary,
            expires_at=compose_expiry(
                constituent_validities=[r.child_expires_at for r in rows if r.child_expires_at],
                max_ttl=MaxTTL(seconds=int(CONFIG["ttl"]["max_ttl_seconds"])), ttl_anchor_at=record.recorded_at,
            ),
            ttl_anchor=CONFIG["product_class"]["ttl_anchor"], lineage=lineage, payload=projection.payload,
            debt=path.debt, debt_evidence=path.debt_evidence, source_refresh_recency=path.source_refresh_recency,
            obligation_in_force=path.obligation_in_force,
        )


@contextmanager
def _reopened_fabric(opened: Any) -> Iterator[Any]:
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415

    substrate = ENVIRONMENT["substrate"]
    minted = sorted(opened.scratch.glob(f"{substrate['prefix']}*{substrate['suffix']}"))[-1]
    fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
    try:
        yield fabric
    finally:
        fabric.handle.close()


def test_served_reconstruction_uses_retained_inputs_without_calling_any_provider(both: dict[str, Any], modules: tuple[Any, Any]) -> None:
    """Every producer process has exited. Replay rebuilds the child-contract view
    from the RETAINED contracts, hands it to the memo's own plan factory, re-
    executes the recorded operator path over the recorded snapshot, and
    reproduces the served bytes exactly.

    Declared product gate `CMC-G29` (`CP-SPEC-014` §D.5).
    """
    from ccf.replay.engine import replay  # noqa: PLC0415

    opened, outcome, record = both[DIAGNOSTIC]
    assert isinstance(outcome, ServedProduct)
    with _reopened_fabric(opened) as fabric:
        environment = _MemoReplayEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
        replayed = replay(
            record_address=outcome.replay_ref.content_address, store=FileArtifactStore(root=opened.scratch / opened.replay.store_dirname),
            reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment,
        )
    assert environment.composite_plans == 1
    assert replayed.product_content_address == content_hash(outcome.product)
    assert replayed.product.payload["sections"] == outcome.product.payload["sections"]


def test_refused_reconstruction_preserves_the_admitted_child_evidence_and_the_recorded_path(both: dict[str, Any], modules: tuple[Any, Any]) -> None:
    """The governed refusal reconstructs with every producer exited: every admitted
    child's bytes resolve from a fresh store instance and re-hash, `replay_refusal`
    returns exactly those addresses consulting no plan, operator or product, and
    `replay()` refuses the record by name.

    Declared product gate `CMC-G17` (`CP-SPEC-014` §D.5).
    """
    from ccf.replay.engine import RefusalReplayOutcome, ReplayRecordKindMismatch, replay, replay_refusal  # noqa: PLC0415

    opened, outcome, record = both[GOVERNED]
    assert isinstance(outcome, RefusalEnvelope)
    rows = _rows(record)
    admitted = sorted(row.child_content_address for row in rows.values() if row.outcome_status == "admitted")
    assert admitted
    store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    address = store.resolve_uri(uri=outcome.replay_reference)
    with _reopened_fabric(opened) as fabric:
        environment = _MemoReplayEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
        reconstructed = replay_refusal(record_address=address, store=store, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
        with pytest.raises(ReplayRecordKindMismatch):
            replay(record_address=address, store=store, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert sorted(reconstructed.child_contract_addresses) == admitted and environment.composite_plans == 0
    # The recorded execution path: the admission refusal happened before any
    # fabric read, and the reconstruction says so rather than inventing one.
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ


# --- the consumer's shape ------------------------------------------------------------------


def test_the_consumer_imports_no_producer_and_rebuilds_no_child_material(both: dict[str, Any]) -> None:
    """No producer module in the consumer process (six trees, five other
    processes); no hand-built child machinery; the consumer's own two legs read
    the roster's identity and document keys and the ledger's anchors and nothing
    a child supplies.

    Declared product gate `CMC-G23` (`CP-SPEC-014` §D.5).
    Declared product gate `CMC-G27` (`CP-SPEC-014` §D.5).
    """
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        for tree in PRODUCER_TREES:
            assert not origin.startswith(str(tree)), f"a producer's {origin} was imported into the consumer"
    forbidden = ("McpSkillRegistry", "register_declared_producer", "SkillCatalog(", "GrantLedger(", "SkillGrant(", "QuestionBoundChildResolver",
                 "CompositeAdmissionGate", "build_governed_resolver", "AgentDefinition(", "compose_debt_factors", "resolve_child_outcomes")
    for name in ("produce.py", "deployment.py", "projection.py", "acquisition.py", "run.py"):
        text = (EXAMPLE / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{name} constructs {token}"
    vocabulary = yaml.safe_load((EXAMPLE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8"))["declaration"]
    assert set(vocabulary["tables"].values()) <= {"legal_entity", "memo_context_debt", "facility"}
    acquisition = (EXAMPLE / "acquisition.py").read_text(encoding="utf-8")
    for table in ("collateral_pledge", "corporate_ownership_record", "financial_fact", "covenant_definition"):
        assert table not in acquisition
    tree = ast.parse(acquisition)
    literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not any("ex:crossReferences" in s or "evidencedBy" in s for s in literals), "the consumer follows a covenant edge"
    _opened, _outcome, record = both[DIAGNOSTIC]
    assert record.tenant_id == "cp-14-demo"
