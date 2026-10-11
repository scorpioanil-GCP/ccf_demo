"""What `examples/cp-13-canonical-covenant-cross-reference` actually serves — `CXRC-G01`…`CXRC-G25`.

The canonical rung-13 successor on the paved producer road (`CP-SPEC-013C`;
the CP-14 completion GO of 2026-09-17). Every figure below is MEASURED at run
time against the live estate; what this module writes down are the
relationships between figures — that every served citation is checked, that
the successor's payload equals the specimen's at one pinned instant, that the
evidence Π serves is the one in the governed view, that a refused decision
reconstructs — never a number restated.

**The specimen is the control.** `examples/cp-13-covenant-cross-reference` is
frozen (`D-IMPL-261`) and still serves on the low road, so the lane the
successor serves is DECIDED BY MEASUREMENT (`CXRC-G14`): the four demonstration
sources at the specimen's instant, full canonical payload hashes and a
field-level comparison. Payload equivalence is not contract identity — the
successor's tenant, plan id and policy-bundle version are its own by
construction and are asserted different, never averaged in.

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

from ccf.erasure import ErasureTrust
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement, ContextProductContract, ProductLineage
from ccf.products.product import OpenedProduct, open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.deployment.conftest import write_artifact
from tests.examples.specimen_base import branch_point
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import THRESHOLD_PARAMETER
from ccf.controlplane.registry import ControlPlaneRegistry

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-13-canonical-covenant-cross-reference"
SPECIMEN = REPO_ROOT / "examples" / "cp-13-covenant-cross-reference"
CONSUMER = pathlib.Path(__file__).resolve().parent / "cp_13_canonical_paved_consumer"
RUN = EXAMPLE / "run.py"

#: The specimen's demonstration instant and scope, and the README's earlier
#: instant — the governing register differs between the two.
AS_OF = datetime(2026, 9, 13, tzinfo=UTC)
EARLIER = datetime(2025, 8, 12, tzinfo=UTC)
ADMITTED_AT = AS_OF + timedelta(minutes=7)
SCOPE = "covenant-cross-reference-demo"
INTENT = "compliance-test"
FRESHNESS = "amendment-driven"
PRODUCT_CLASS = "credit-risk.covenant-cross-reference"

#: `CP-SPEC-014`'s obligor and the facility document the roster names for it —
#: the join the consumer makes to DETERMINE its covenant question (`CP14-F-28`).
CP14_LEI = "2549001IGRCG4F0RLD36"
CP14_DOCUMENT = "0001213900-26-057808:ea029103901ex10-1.htm"
CP14_FRESHNESS = "as-filed"
DIAGNOSTIC_TOLERANCE = "1.0"

ESTATE_VARIABLES = (
    "CCF_CP_13C_POSTGRES_DSN", "CCF_CP_13C_POSTGRES_SCHEMA",
    "CCF_CP_13C_FLUREE_URL", "CCF_CP_13C_FLUREE_LEDGER",
    "CCF_CP_13C_MONGO_URI", "CCF_CP_13C_MONGO_DB",
)
#: The specimen reads the SAME estate under its own names.
SPECIMEN_VARIABLES = {name.replace("CCF_CP_13C_", "CCF_CP_13_"): name for name in ESTATE_VARIABLES}
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

PRODUCER_ID = "cp-13-canonical-covenant-cross-reference-egress"
PRODUCER_TENANT = "cp-13-canonical-demo"
DOOR_TOKEN_VAR = "CCF_CP_13C_DOOR_TOKEN"
DEV_TOKEN = "dev-token-cp-13-canonical-door"
ENDPOINT_VAR = "CCF_TEST_CP13C_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CP13C_PRODUCER_TOKEN"

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
ENVIRONMENT: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))
GATE_ID = CONFIG["product_class"]["declared_product_gate"]["gate_id"]
DEFAULT_ROLE = CONFIG["default_perspective"]["role"]


# --- fixtures and helpers -----------------------------------------------------------


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
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


def _graph_settings() -> dict[str, str]:
    return {"url": os.environ["CCF_CP_13C_FLUREE_URL"], "ledger": os.environ["CCF_CP_13C_FLUREE_LEDGER"]}


def _mongo() -> Any:
    from pymongo import MongoClient  # noqa: PLC0415

    return MongoClient(os.environ["CCF_CP_13C_MONGO_URI"])[os.environ["CCF_CP_13C_MONGO_DB"]]


@pytest.fixture(scope="module")
def sources(estate: None, modules: dict[str, Any]) -> list[str]:
    """The specimen's demonstration question: the first four evidence nodes off the ledger."""
    chosen = modules["acquisition"].evidence_sources(limit=4, graph_settings=_graph_settings())
    assert len(chosen) == 4, chosen
    return chosen


@pytest.fixture(scope="module")
def cp14_sources(estate: None, modules: dict[str, Any]) -> list[str]:
    """The evidence nodes of the CP-14 obligor's facility document — the join
    the consumer makes to determine its question, never to answer it."""
    acquisition = modules["acquisition"]
    terms = acquisition.vocabulary()
    graph = acquisition._Graph(**_graph_settings())
    rows = graph.select(
        f"SELECT DISTINCT ?s FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['passage_anchor_class']}> . ?s <{terms['defined_by']}> ?o ."
        f" ?s <{terms['anchor_predicates']['document_id']}> \"{CP14_DOCUMENT}\" }}"
    )
    chosen = sorted(r["s"] for r in rows)
    assert chosen, f"the CP-14 facility document {CP14_DOCUMENT} carries no evidence node with a chain"
    return chosen


@dataclass(frozen=True)
class _Answer:
    """One served answer with its record, for the assertions below."""

    product: Any
    record: DecisionReplayRecord
    served: Any


def _question(
    opened: OpenedProduct, deployment: Any, *, sources: list[str], subject: str | None = None,
    asked_at: datetime = AS_OF, intent: str = INTENT, freshness: str = FRESHNESS, **params: Any,
) -> ProductRequest:
    parameters: dict[str, Any] = {deployment.COVENANT_SOURCES: list(sources)}
    parameters.update({name: value for name, value in params.items() if value is not None})
    if subject is None:
        subject = sources[0] if len(sources) == 1 else SCOPE
    return opened.question(subject=subject, asked_at=asked_at, intent=intent, freshness=freshness, parameters=parameters)


def _perspective(opened: OpenedProduct, role: str | None) -> Perspective | None:
    if role is None:
        return None
    return Perspective(principal_id=opened.default_perspective.principal_id, role=role)


def _ask(modules: dict[str, Any], scratch: pathlib.Path, *, role: str | None = None, **question: Any) -> Any:
    """One question on the paved road, in its own scratch: the outcome as data."""
    with modules["produce"].product(scratch) as opened:
        return opened.answer(_question(opened, modules["deployment"], **question), perspective=_perspective(opened, role))


def _answer(modules: dict[str, Any], scratch: pathlib.Path, *, role: str | None = None, **question: Any) -> _Answer:
    with modules["produce"].product(scratch) as opened:
        outcome = opened.answer(_question(opened, modules["deployment"], **question), perspective=_perspective(opened, role))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return _Answer(product=outcome.product, record=opened.record_of(outcome), served=outcome)


def _nodes(answer: _Answer) -> list[dict[str, Any]]:
    return [node for source in answer.product.payload["cross_references"] for node in source["chain"]]


def _citations(answer: _Answer) -> list[dict[str, Any]]:
    return [citation for node in _nodes(answer) for citation in node["citations"]]


def _factor(answer: _Answer, name: str) -> Decimal:
    return Decimal(str(getattr(answer.product.debt.factors, name)))


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], sources: list[str], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The demonstration question under the declared perspective and the class defaults."""
    return _answer(modules, tmp_path_factory.mktemp("served"), sources=sources)


@pytest.fixture(scope="module")
def widened(estate: None, modules: dict[str, Any], sources: list[str], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The same sources under the control room's wider entitlement."""
    return _answer(modules, tmp_path_factory.mktemp("widened"), sources=sources, role="control-room", corpus_scope="filed-and-internal")


@pytest.fixture(scope="module")
def memo(estate: None, modules: dict[str, Any], cp14_sources: list[str], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The CP-14-shaped question in-process: the obligor as the scope, its
    document's evidence nodes, `as-filed`, the DIAGNOSTIC tolerance."""
    return _answer(
        modules, tmp_path_factory.mktemp("memo"), sources=cp14_sources, subject=CP14_LEI,
        freshness=CP14_FRESHNESS, debt_tolerance=DIAGNOSTIC_TOLERANCE,
    )


def _specimen(sources: list[str], *, intent: str = INTENT) -> Any:
    """The frozen specimen, in-process, at the same instant against the same estate."""
    environment = {specimen: os.environ[successor] for specimen, successor in SPECIMEN_VARIABLES.items()}
    previous = {name: os.environ.get(name) for name in environment}
    os.environ.update(environment)
    try:
        with _tree_modules(SPECIMEN) as specimen, tempfile.TemporaryDirectory() as scratch:
            asked = specimen["deployment"].request(sources=sources, asked_at=AS_OF, scope=SCOPE)
            asked = asked.model_copy(update={"intent": intent})
            outcome = specimen["produce"].assemble_and_serve(asked=asked, root=pathlib.Path(scratch), principal=DEFAULT_ROLE)
            # The specimen's spine returns its own `Assembled` record; the
            # successor's road returns the `ServedProduct`. Normalized here.
            return outcome if isinstance(outcome, RefusalEnvelope) else outcome.served
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _field_differences(a: Any, b: Any, path: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append(f"{path}/{key}: present on one side only")
            else:
                out += _field_differences(a[key], b[key], f"{path}/{key}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: {len(a)} vs {len(b)} members")
        out += [d for x, y in zip(a, b) for d in _field_differences(x, y, f"{path}[]")]
    elif a != b:
        out.append(f"{path}: {a!r} vs {b!r}")
    return out


# --- G01–G02: the citation unit, and the reason for every absence ------------------


def test_every_served_citation_is_checked_against_the_named_passage(served: _Answer, modules: dict[str, Any]) -> None:
    """The citation unit is the named passage reached through `ex:evidencedBy`:
    every served citation carries `checked: true`, the passage's own sha256 and
    a real span; the anchor predicates on the evidence node are never the
    citation, so a node with no evidence edge emits none.

    Declared product gate `CXRC-G01` (`CP-SPEC-013C` §G.1).
    """
    citations = _citations(served)
    assert citations, "the demonstration served no checked citation at all"
    for citation in citations:
        assert citation["checked"] is True and citation["sha256"]
        assert int(citation["end_offset"]) > int(citation["start_offset"])
        assert citation["anchor"]["kind"] == modules["projection"].ANCHOR_KIND and citation["anchor"]["locator"]
    assert served.product.payload["citation_summary"]["checked_citations"] == len(citations)


def test_an_unquotable_node_emits_no_citation_and_is_debt_with_a_reason(served: _Answer, modules: dict[str, Any]) -> None:
    """A point anchor and an unverifiable span emit NO citation and are reported
    as debt with a reason from the closed vocabulary — `ex:declaredAt` names a
    limitation and does not lift it.

    Declared product gate `CXRC-G02` (`CP-SPEC-013C` §G.1).
    """
    reasons = modules["projection"].DEBT_REASONS
    absences = [absence for node in _nodes(served) for absence in node["not_evidenced"]]
    assert absences, "every chain node was quotable; the debt limb is vacuous on this question"
    for absence in absences:
        assert absence["reason"] in reasons and absence["note"]
    for node in _nodes(served):
        if any(a["reason"] == "point-anchor" for a in node["not_evidenced"]):
            assert node["citations"] == []
    summary = served.product.payload["citation_summary"]
    assert set(summary["not_evidenced"]) == set(reasons) and summary["not_evidenced_total"] == len(absences)
    assert tuple(summary["debt_reason_vocabulary"]) == tuple(reasons)


# --- G03–G04: the envelope bounds the retrieval; an unentitled role is refused -------


def test_the_bound_is_applied_before_ranking_and_two_roles_receive_different_addresses(served: _Answer, widened: _Answer) -> None:
    """The permitted classification set is an ARGUMENT to the retrieval, never a
    predicate over its results, and two roles with different entitlements
    receive different content addresses.

    Declared product gate `CXRC-G03` (`CP-SPEC-013C` §G.1).
    """
    for answer in (served, widened):
        retrieval = answer.product.payload["envelope"]["retrieval"]
        assert retrieval["bound_applied"] == "before-ranking"
        assert set(retrieval["query_filter"]["classification"]["$in"]) == set(answer.product.payload["envelope"]["permitted_classifications"])
    assert set(served.product.payload["envelope"]["permitted_classifications"]) < set(widened.product.payload["envelope"]["permitted_classifications"])
    assert widened.product.payload["envelope"]["retrieval"]["candidates_examined"] >= served.product.payload["envelope"]["retrieval"]["candidates_examined"]
    assert content_hash(served.product.payload) != content_hash(widened.product.payload)


def test_a_role_with_no_entitlement_row_is_refused_never_narrowed(estate: None, modules: dict[str, Any], sources: list[str], tmp_path: pathlib.Path) -> None:
    """A role with no entitlement row for the requested scope is REFUSED —
    the walk's own exception, exactly as the specimen raises it — and never
    silently answered at the narrower scope.

    Declared product gate `CXRC-G04` (`CP-SPEC-013C` §G.1).
    """
    with pytest.raises(modules["acquisition"].ScopeNotEntitled, match="refused rather than narrowed"):
        _ask(modules, tmp_path, sources=sources, role="relationship-manager", corpus_scope="filed-and-internal")


# --- G05–G10: the governing axis, the seed, the two walk refusals, the absences ------


def test_the_governing_text_is_selected_by_governs_from_at_the_instant(estate: None, modules: dict[str, Any], sources: list[str], served: _Answer, tmp_path: pathlib.Path) -> None:
    """The governing register is chosen by `governs_from` at `as_of`, never by
    `filed_date`; an earlier instant governs no more documents than a later
    one over the same population, and the two figures partition it.

    Declared product gate `CXRC-G05` (`CP-SPEC-013C` §G.1).
    """
    now = served.product.payload["governing_text"]
    assert now["axis"] == "governs_from" and now["not_axis"] == "filed_date"
    assert now["as_of"] == AS_OF.date().isoformat()
    earlier = _answer(modules, tmp_path, sources=sources, asked_at=EARLIER).product.payload["governing_text"]
    assert earlier["documents_in_force"] + earlier["documents_not_yet_governing"] == now["documents_in_force"] + now["documents_not_yet_governing"]
    assert earlier["documents_in_force"] <= now["documents_in_force"]
    assert earlier["documents_not_yet_governing"] >= now["documents_not_yet_governing"]


def test_the_payload_declares_the_seed(served: _Answer, modules: dict[str, Any]) -> None:
    """Which node set the traversal seeded on is DECLARED in the payload and is
    the anchor class the operator declaration seeds on.

    Declared product gate `CXRC-G06` (`CP-SPEC-013C` §G.1).
    """
    traversal = served.product.payload["traversal"]
    assert traversal["seeded_on"] == modules["acquisition"].SEED
    assert modules["acquisition"].vocabulary()["passage_anchor_class"].endswith(traversal["seeded_on"].split(":")[-1])
    assert CONFIG["operators"]["traversal.typed-neighborhood"]["seed_entity_classes"] == ["cxr_anchor"]
    assert traversal["resolve_depth"] == CONFIG["request_contract"]["defaults"]["resolve_depth"]
    assert traversal["sources"] == len(served.product.payload["cross_references"])


def test_an_unknown_evidence_node_refuses_distinctly(estate: None, modules: dict[str, Any], tmp_path: pathlib.Path) -> None:
    """An unknown evidence node is a request error (404), distinct from a
    node with no definition chain — the walk's own exception, as the specimen
    raises it.

    Declared product gate `CXRC-G07` (`CP-SPEC-013C` §G.1).
    """
    with pytest.raises(modules["acquisition"].UnknownCovenantSource, match="404"):
        _ask(modules, tmp_path, sources=["http://example.org/fibo/COVSRC-NOBODY-DECLARED-THIS"])


def test_no_passage_text_is_served_outside_the_permitted_set(served: _Answer, widened: _Answer) -> None:
    """Every cited document and every retrieved memorandum is classified within
    the role's permitted set, at any depth.

    Declared product gate `CXRC-G08` (`CP-SPEC-013C` §G.1).
    """
    store = _mongo()
    for answer in (served, widened):
        permitted = set(answer.product.payload["envelope"]["permitted_classifications"])
        for citation in _citations(answer):
            row = store["document"].find_one({"document_id": citation["document_id"]}, {"classification": 1})
            assert row is not None and row["classification"] in permitted, citation["document_id"]
        for hit in answer.product.payload["envelope"]["retrieval"]["hits"]:
            assert hit["classification"] in permitted, hit


def test_governed_by_is_absent_and_not_invented(served: _Answer) -> None:
    """`ex:governedBy` is measured absent; the payload says so and substitutes
    no proxy edge for it.

    Declared product gate `CXRC-G09` (`CP-SPEC-013C` §G.1).
    """
    leg = served.product.payload["absent_legs"]["governedBy"]
    assert leg["state"] == "absent" and leg["note"]
    for node in _nodes(served):
        assert "governedBy" not in node and "governed_by" not in node


def test_an_absent_embedding_is_not_evaluable(widened: _Answer) -> None:
    """A memorandum inside the permitted set that carries no embedding is
    reported as unreachable-by-similarity with that reason, beside the count
    of candidates that were ranked — never as "no relevant result".

    Declared product gate `CXRC-G10` (`CP-SPEC-013C` §G.1).
    """
    retrieval = widened.product.payload["envelope"]["retrieval"]
    absent = retrieval["not_evaluable"]
    assert absent["count"] > 0, "every eligible memorandum is embedded; the gate is vacuous on this estate"
    assert absent["reason"] == "no-embedding" and absent["note"] and len(absent["ids"]) == absent["count"]
    assert len(retrieval["hits"]) <= retrieval["candidates_examined"]


# --- G11–G13: the tolerance, dimension 2, the standard door ---------------------------


def test_debt_above_tolerance_refuses_with_the_debt_block(estate: None, modules: dict[str, Any], sources: list[str], served: _Answer, tmp_path: pathlib.Path) -> None:
    """A caller's tolerance below the measured debt withholds the product with
    the debt block on the record — the product was constructible, and says so.

    Declared product gate `CXRC-G11` (`CP-SPEC-013C` §G.1).
    """
    tolerance = Decimal("0.10")
    assert served.product.debt.debt > tolerance
    with modules["produce"].product(tmp_path) as opened:
        refused = opened.answer(_question(opened, modules["deployment"], sources=sources, debt_tolerance=str(tolerance)))
        assert isinstance(refused, RefusalEnvelope), refused
        record = opened.record_of(refused)
    assert refused.kind == "tolerance-exceeded" and refused.replay_reference
    assert record.content_generation_path.debt is not None and record.content_generation_path.debt.debt == served.product.debt.debt
    assert "0.10" in record.content_generation_path.assembly_refusal


def test_replay_dimension_two_is_a_superset_of_product_lineage(served: _Answer) -> None:
    """`D-IMPL-310`: every policy version the product carries is a recorded binding.

    Declared product gate `CXRC-G12` (`CP-SPEC-013C` §G.1).
    """
    bindings = {b.key for b in served.record.policy_bindings.bindings}
    versions = {b.version for b in served.record.policy_bindings.bindings}
    assert "request_contract" in bindings
    assert set(served.product.lineage.policy_bundle_versions) <= versions
    assert set(served.product.lineage.operators_invoked) == set(CONFIG["product_class"]["required_operator_keys"])


def test_the_door_is_the_sdk_standard_door_opened_from_the_declaration() -> None:
    """No door module, no `door.yaml`, no `backends.yaml`: the launcher opens
    the SDK's standard door over the opened product and re-implements nothing.

    Declared product gate `CXRC-G13` (`CP-SPEC-013C` §G.1).
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


# --- G14: the lane, measured ---------------------------------------------------------


def test_the_lane_is_measured_the_successor_payload_equals_the_specimens(served: _Answer, sources: list[str]) -> None:
    """`CP-SPEC-013C` §D.4: at the specimen's instant under the class defaults
    and the declared perspective, the successor's canonical payload hashes to
    the specimen's — full hashes and a field-level comparison — so the
    successor serves `1.0.0`, a second producer of the same product. What
    differs is asserted different: tenant, plan id, policy-bundle version.
    Payload equivalence is not contract identity.

    Declared product gate `CXRC-G14` (`CP-SPEC-013C` §G.1).
    """
    specimen = _specimen(sources)
    assert isinstance(specimen, ServedProduct), getattr(specimen, "detail", specimen)
    assert content_hash(served.product.payload) == content_hash(specimen.product.payload)
    assert _field_differences(json.loads(canonical_bytes(specimen.product.payload)), json.loads(canonical_bytes(served.product.payload))) == []
    # The whole assessment is equal — value, factors, signal AND the three
    # scorer pins `D-IMPL-47` records: the SDK's freshness scorer for `F`, the
    # SDK's declared-factor scorer for the `C` and `S` this deployment reads
    # off the governed view and declares to it.
    assert served.product.debt == specimen.product.debt
    assert served.product.expires_at == specimen.product.expires_at
    assert served.product.lineage.operators_invoked == specimen.product.lineage.operators_invoked
    assert (served.product.schema_name, served.product.schema_version) == (PRODUCT_CLASS, "1.0.0") == (specimen.product.schema_name, specimen.product.schema_version)
    assert CONFIG["product_class"]["schema_version"] == CONFIG["request_contract"]["schema_version"] == "1.0.0"
    # the contract is NOT the same, by construction
    assert served.product.tenant_id != specimen.product.tenant_id
    assert served.product.plan_id != specimen.product.plan_id
    assert served.product.lineage.policy_bundle_versions != specimen.product.lineage.policy_bundle_versions
    assert content_hash(served.product) != content_hash(specimen.product)


# --- G15: the evidence is the view ---------------------------------------------------


def _with_one_cited_node_unevidenced(deployment: Any) -> tuple[Callable[[Any], tuple[SignalEnvelope, ...]], dict[str, int]]:
    """The deployment's own acquire, with the first cited chain node's citations
    moved to an explained absence IN THE ENVELOPE — the governed view then
    carries a chain with one fewer evidenced node."""
    dropped = {"citations": 0}

    def acquire(context: Any) -> tuple[SignalEnvelope, ...]:
        out: list[SignalEnvelope] = []
        for envelope in deployment.acquire(context):
            payload = envelope.raw_payload
            if not dropped["citations"] and payload.get("node_kind") == "anchor":
                source = json.loads(payload["source_json"])
                for node in source["chain"]:
                    if node["citations"]:
                        dropped["citations"] = len(node["citations"])
                        node["citations"] = []
                        node["not_evidenced"] = [*node["not_evidenced"], {"reason": "sha256-mismatch", "note": "the view was altered for CXRC-G15"}]
                        break
                if dropped["citations"]:
                    envelope = envelope.model_copy(update={"raw_payload": {**payload, "source_json": json.dumps(source, sort_keys=True, default=str)}})
            out.append(envelope)
        return tuple(out)

    return acquire, dropped


def test_the_evidence_pi_serves_is_the_one_in_the_governed_view(estate: None, modules: dict[str, Any], sources: list[str], served: _Answer, tmp_path: pathlib.Path) -> None:
    """With every other input fixed, a changed chain in the governed view
    changes the served citations AND the debt factor `C` in step; Π's
    constructor takes no estate and no source, so there is no side channel
    to obtain the old evidence from.

    Declared product gate `CXRC-G15` (`CP-SPEC-013C` §G.1).
    """
    deployment, produce = modules["deployment"], modules["produce"]
    constructor = next(
        n for n in ast.walk(ast.parse((EXAMPLE / "projection.py").read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )
    parameters = {a.arg for a in constructor.args.kwonlyargs}
    assert not parameters & {"declared", "estate", "sources", "acquisition"}, parameters
    acquire, dropped = _with_one_cited_node_unevidenced(deployment)
    with open_product(config_root=EXAMPLE, scratch=tmp_path, acquire=acquire, project=produce.plan_factory, assess=deployment.assess, gate=deployment.citation_gate, control_plane=ControlPlaneRegistry(), erasure_trust=ErasureTrust(authorities={})) as opened:
        altered = opened.answer(_question(opened, deployment, sources=sources))
    assert isinstance(altered, ServedProduct), getattr(altered, "detail", altered)
    assert dropped["citations"] > 0
    before, after = served.product.payload["citation_summary"], altered.product.payload["citation_summary"]
    assert after["checked_citations"] == before["checked_citations"] - dropped["citations"]
    assert after["not_evidenced"]["sha256-mismatch"] == before["not_evidenced"]["sha256-mismatch"] + 1
    assert after["chain_nodes"] == before["chain_nodes"]
    assert Decimal(str(altered.product.debt.factors.completeness)) < _factor(served, "completeness")
    assert altered.product.debt.debt > served.product.debt.debt
    assert content_hash(altered.product.payload) != content_hash(served.product.payload)


# --- G16–G17: the shape, the untouched specimen --------------------------------------


def test_the_structural_classifier_reads_this_tree_as_paved() -> None:
    """`shape_of` is structural — it asks the code, never a roster — and no
    resolver ownership or record call exists in the tree.

    Declared product gate `CXRC-G16` (`CP-SPEC-013C` §G.1).
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
    """cp-13 is frozen under `D-IMPL-261`: ZERO files changed by this work,
    measured against the branch point; and this tree reuses none of the
    specimen's identities — tenant, producer id, plan-id prefix, gate id,
    class ids.

    Declared product gate `CXRC-G17` (`CP-SPEC-013C` §G.1).
    """
    base = branch_point(REPO_ROOT)
    changed = subprocess.run(
        ["git", "diff", "--name-only", base, "--", str(SPECIMEN.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert changed == [], f"the frozen specimen was modified: {changed}"
    specimen_config = yaml.safe_load((SPECIMEN / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert CONFIG["tenant_id"] != specimen_config["tenant_id"]
    assert CONFIG["product_class"]["declared_product_gate"]["gate_id"] != specimen_config["product_class"]["declared_product_gate"]["gate_id"]
    assert CONFIG["request_contract"]["class_id"] != specimen_config["request_contract"]["class_id"]
    assert CONFIG["policy"]["class_id"] != specimen_config["policy"]["class_id"]
    assert served.product.plan_id.startswith("cp-13-canonical.")
    assert served.product.tenant_id == PRODUCER_TENANT


# --- G18–G20, G22: the CP-14-shaped question through the standard door ---------------


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


def cp14_question_for(sources: list[str]) -> Callable[[ChildRequirement, ProductRequest], ChildQuestion]:
    """The consumer's ONE mapping — `CP-SPEC-014`'s covenant question: the
    obligor is the child's subject (its scope), the evidence nodes of its
    facility document are the sources, `as-filed`, and the tolerance is the
    consumer's — here the DIAGNOSTIC value, never the governed one."""

    def cp14_question(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        return ChildQuestion(
            subject=request.subject, intent=INTENT, freshness=CP14_FRESHNESS,
            parameters={"covenant_sources": list(sources), "debt_tolerance": DIAGNOSTIC_TOLERANCE},
        )

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


def paved_consumer(tmp_path: pathlib.Path, *, url: str, sources: list[str], edit: Callable[[dict[str, Any]], None] | None = None) -> OpenedProduct:
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=_consumer_tree(tmp_path, edit=edit), scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(), project=fixture.plan_factory, assess=fixture.assess,
        questions=cp14_question_for(sources), environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN}, clock=lambda: ADMITTED_AT,
    )


def ask_consumer(opened: OpenedProduct) -> Any:
    return opened.answer(opened.question(subject=CP14_LEI, asked_at=AS_OF, intent="fixture-intent", freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000}))


def consumer_row(opened: OpenedProduct, outcome: Any) -> Any:
    rows = opened.record_of(outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def _retained_child(opened: OpenedProduct, row: Any) -> ContextProductContract:
    return ContextProductContract.model_validate_json(
        FileArtifactStore(root=opened.scratch / opened.replay.store_dirname).get(content_address=row.child_content_address)
    )


def test_the_cp14_question_is_answered_in_another_process_and_admitted_under_provider_controls(
    estate: None, memo: _Answer, cp14_sources: list[str], tmp_path: pathlib.Path
) -> None:
    """The CP-14-shaped question reaches the successor through the standard
    door in ANOTHER process; the child is admitted under the expected producer
    identity and tenant with `provider-controls`; the retained child is the
    producer's own bytes, about the obligor's own evidence nodes.

    Declared product gate `CXRC-G18` (`CP-SPEC-013C` §G.1).
    """
    with producer(estate) as url, paved_consumer(tmp_path, url=url, sources=cp14_sources) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        row = consumer_row(opened, outcome)
        child = _retained_child(opened, row)
    assert row.outcome_status == "admitted" and row.eligibility_basis == "provider-controls"
    assert (row.producer_id, row.producer_tenant, row.child_schema_name, row.child_schema_version) == (PRODUCER_ID, PRODUCER_TENANT, PRODUCT_CLASS, "1.0.0")
    assert (child.tenant_id, child.temporal_boundary) == (PRODUCER_TENANT, AS_OF)
    assert sorted(s["source_uri"] for s in child.payload["cross_references"]) == sorted(cp14_sources)
    assert child.plan_id.endswith(f"/{CP14_LEI}")
    assert row.child_replay_ref and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")


@pytest.mark.parametrize(
    "member,value,reason",
    [("producer_id", "somebody-elses-egress", "producer-mismatch"), ("producer_tenant", "somebody-elses-tenant", "producer-tenant-mismatch")],
)
def test_wrong_producer_and_wrong_tenant_refuse_independently(
    estate: None, cp14_sources: list[str], tmp_path: pathlib.Path, member: str, value: str, reason: str
) -> None:
    """The expected producer identity and tenant come from the REGISTRATION —
    a payload cannot authorize itself by claiming them — and each wrong
    expectation refuses on its own reason with the reason retained.

    Declared product gate `CXRC-G19` (`CP-SPEC-013C` §G.1).
    """

    def edit(config: dict[str, Any]) -> None:
        config["producers"]["covenant"][member] = value

    with producer(estate) as url, paved_consumer(tmp_path, url=url, sources=cp14_sources, edit=edit) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, RefusalEnvelope), outcome
        row = consumer_row(opened, outcome)
    assert row.outcome_status != "admitted" and row.refusal_ref == reason


def test_the_door_and_the_in_process_run_serve_one_content_address(estate: None, memo: _Answer, cp14_sources: list[str], tmp_path: pathlib.Path) -> None:
    """One question, two deliveries, one address: the child the consumer
    retained through the door hashes to what this process served in-process.

    Declared product gate `CXRC-G20` (`CP-SPEC-013C` §G.1).
    """
    with producer(estate) as url, paved_consumer(tmp_path, url=url, sources=cp14_sources) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        row = consumer_row(opened, outcome)
    assert row.child_content_address == content_hash(memo.product)
    assert row.child_debt == memo.product.debt.debt


def test_the_entitlement_principal_is_the_perspectives_role(estate: None, served: _Answer, widened: _Answer, cp14_sources: list[str], tmp_path: pathlib.Path) -> None:
    """Through the door every caller is served as the DECLARED credit officer;
    in-process a stated perspective changes the principal the envelope
    reports; no request parameter names a principal at all.

    Declared product gate `CXRC-G22` (`CP-SPEC-013C` §G.1).
    """
    assert "principal" not in CONFIG["request_contract"]["arguments"]["properties"]
    assert served.product.payload["envelope"]["principal"] == served.product.payload["role"] == DEFAULT_ROLE
    assert widened.product.payload["envelope"]["principal"] == widened.product.payload["role"] == "control-room"
    with producer(estate) as url, paved_consumer(tmp_path, url=url, sources=cp14_sources) as opened:
        outcome = ask_consumer(opened)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        child = _retained_child(opened, consumer_row(opened, outcome))
    assert child.payload["envelope"]["principal"] == child.payload["role"] == DEFAULT_ROLE


# --- G21, G23: the governed axes the specimen left open --------------------------------


def test_an_unknown_intent_is_refused_on_the_declared_discovery_set(estate: None, modules: dict[str, Any], sources: list[str], tmp_path: pathlib.Path) -> None:
    """`intent` is judged on `discovery.intents`; the specimen declares no set
    and serves any intent — a DELIBERATE tightening, reported here rather
    than averaged into the lane comparison.

    Declared product gate `CXRC-G21` (`CP-SPEC-013C` §G.1).
    """
    refused = _ask(modules, tmp_path, sources=sources, intent="annual-review")
    assert isinstance(refused, RefusalEnvelope), refused
    assert refused.reason == "class-mismatch" and refused.replay_reference
    specimen = _specimen(sources, intent="annual-review")
    assert not isinstance(specimen, RefusalEnvelope), "the specimen now refuses unknown intents; this contrast is stale"


def test_a_question_admitting_no_evidence_node_is_refused_never_served_empty(estate: None, modules: dict[str, Any], tmp_path: pathlib.Path) -> None:
    """A question that names no evidence node admits nothing to the view; the
    declared lineage obligation on `cross_references` refuses it with a
    record. The specimen raised `ValueError` before any read (`CP-SPEC-013C`
    §G.3, a deliberate difference).

    Declared product gate `CXRC-G23` (`CP-SPEC-013C` §G.1).
    """
    with modules["produce"].product(tmp_path) as opened:
        refused = opened.answer(_question(opened, modules["deployment"], sources=[], subject=SCOPE))
        assert isinstance(refused, RefusalEnvelope), refused
        record = opened.record_of(refused)
    assert refused.kind == "declared-obligation-refusal" and refused.replay_reference
    assert "cross_references" in record.content_generation_path.assembly_refusal
    assert not record.context_fabric_snapshot.touched_entities


# --- G24: a fresh fabric per run --------------------------------------------------------


def test_a_fresh_fabric_per_run_and_one_determination_across_roots(
    estate: None, modules: dict[str, Any], sources: list[str], cp14_sources: list[str], memo: _Answer, tmp_path: pathlib.Path
) -> None:
    """Two questions under one opened product leave two substrate files, and a
    question served after another under one root hashes to the address it
    hashes to alone.

    Declared product gate `CXRC-G24` (`CP-SPEC-013C` §G.1).
    """
    deployment, produce = modules["deployment"], modules["produce"]
    substrate = ENVIRONMENT["substrate"]
    with produce.product(tmp_path / "shared-root") as opened:
        first = opened.answer(_question(opened, deployment, sources=sources))
        second = opened.answer(_question(opened, deployment, sources=cp14_sources, subject=CP14_LEI, freshness=CP14_FRESHNESS, debt_tolerance=DIAGNOSTIC_TOLERANCE))
        minted = sorted((tmp_path / "shared-root").glob(f"{substrate['prefix']}*{substrate['suffix']}"))
    assert len(minted) == 2 and minted[0] != minted[1], minted
    assert isinstance(first, ServedProduct) and isinstance(second, ServedProduct)
    assert content_hash(second.product) == content_hash(memo.product)


# --- G25: identity and reconstruction ---------------------------------------------------


class _FreshEnvironment:
    """A replay environment built from the RECORD and the deployment's own
    documents — no acquisition object, no live view from the serve."""

    def __init__(self, *, modules: dict[str, Any], opened: OpenedProduct, fabric: Any, record: DecisionReplayRecord) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        self._produce = modules["produce"]
        path = record.content_generation_path
        assert path.request is not None
        # Π is rebuilt from the EFFECTIVE request the record carries on
        # dimension 2 — the class defaults as they folded at decision time.
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        assert isinstance(effective, EffectiveRequest), resolution
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        self._ttl = int(CONFIG["ttl"]["product_ttl_seconds"])
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver.operator_parameters(self._request),
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


def test_replay_reproduces_the_served_product_and_a_refusal_reconstructs(
    estate: None, modules: dict[str, Any], sources: list[str], tmp_path: pathlib.Path
) -> None:
    """Replay rebuilds the plan from the RECORDED request and re-executes over
    the recorded snapshot — the chains, the envelope and the governing register
    come back off the graph, never from an acquisition object, which no longer
    exists — and reproduces the served bytes exactly; and the debt reading over
    the replayed view agrees with the record. A tolerance refusal reconstructs
    through `replay_refusal` with no product rehydrated, and `replay()` refuses
    the same record by name (`D-IMPL-344`).

    Declared product gate `CXRC-G25` (`CP-SPEC-013C` §G.1).
    """
    from ccf.replay.engine import RefusalReplayOutcome, ReplayRecordKindMismatch, replay, replay_refusal  # noqa: PLC0415

    deployment, produce, projection = modules["deployment"], modules["produce"], modules["projection"]
    with produce.product(tmp_path / "served") as opened:
        outcome = opened.answer(_question(opened, deployment, sources=sources))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        record = opened.record_of(outcome)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            replayed = replay(
                record_address=outcome.replay_ref.content_address,
                store=FileArtifactStore(root=opened.scratch / opened.replay.store_dirname),
                reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment,
            )
            view = fabric.handle.reader.as_of(tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary)
            assert projection.view_completeness(view) == Decimal(str(outcome.product.debt.factors.completeness))
            assert projection.view_semantic_consistency(view) == Decimal(str(outcome.product.debt.factors.semantic_consistency))
    assert replayed.product_content_address == content_hash(outcome.product)
    assert replayed.product.payload["citation_summary"] == outcome.product.payload["citation_summary"]
    assert environment.rehydrated == 1

    with produce.product(tmp_path / "refused") as opened:
        refused = opened.answer(_question(opened, deployment, sources=sources, debt_tolerance="0.10"))
        assert isinstance(refused, RefusalEnvelope), refused
        record = opened.record_of(refused)
        store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        address = store.resolve_uri(uri=refused.replay_reference)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            reconstructed = replay_refusal(record_address=address, store=store, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
            with pytest.raises(ReplayRecordKindMismatch):
                replay(record_address=address, store=store, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert reconstructed.child_contract_addresses == () and environment.rehydrated == 0
    assert reconstructed.graph_snapshot_id == record.context_fabric_snapshot.graph_snapshot_id
    assert "product" not in type(reconstructed).model_fields
