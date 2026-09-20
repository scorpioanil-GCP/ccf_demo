"""Sabotage and relational gates of `examples/cp-17-mnpi-wall-enforcement` —
`MWE-G03`, `MWE-G06`, `MWE-G07`, `MWE-G09`, `MWE-G12`, `MWE-G16`.

Every sabotage here is IN-PROCESS: the tree's `deployment.acquire` is wrapped
through `monkeypatch` before `produce.product(...)` opens the product (the
road hands `deployment.acquire` to `open_product` at call time), so the
per-request fabric receives exactly what the wrapper emits and the estate is
never touched by a write. The relational gates compare two answers the same
road served; nothing pins a count or a date (CLAUDE.md §9).

Reads the curated estate, seeds nothing.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import canonical_bytes
from ccf.products.product import AcquisitionContext, OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.products.test_policy_emptied_view_disclosure import _diff_paths

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-17-mnpi-wall-enforcement"

ESTATE_VARIABLES = (
    "CCF_CP_17_SQLITE_PATH",
    "CCF_CP_17_POSTGRES_DSN", "CCF_CP_17_POSTGRES_SCHEMA",
    "CCF_CP_17_FLUREE_URL", "CCF_CP_17_FLUREE_LEDGER",
    "CCF_CP_17_MONGO_URI", "CCF_CP_17_MONGO_DB",
    "CCF_CP_17_TOKEN_COVERAGE", "CCF_CP_17_TOKEN_RESEARCH",
    "CCF_CP_17_TOKEN_TRADER", "CCF_CP_17_TOKEN_KYC",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
INSTANTS: dict[str, datetime] = {name: datetime.fromisoformat(value) for name, value in QUESTION["instants"].items()}
T1 = INSTANTS["T1"]
DEMONSTRATION_ISSUER: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]

#: The trader's freshness COMPARISON issuer (`CP-SPEC-017` §C.4 trap 7) — a
#: subject the position clock is read on, never a wall subject.
FRESHNESS_COMPARISON_ISSUER = "2549004GGE2APGNT6O92"
#: Two LEIs with no issuer row: the A6 comparators (`CP-SPEC-017` §D.3 step 1.2).
NONEXISTENT_ISSUERS = ("0000000000000000NOPE", "0000000000000000NADA")
#: The tolerance at which an empty view is SERVED rather than withheld.
DIAGNOSTIC_TOLERANCE = "1.0"
#: A classification outside the product's vocabulary, for the Policy sabotage.
FOREIGN_CLASSIFICATION = "sabotage-classified"

ROLE_BANKER = "coverage-banker"
ROLE_ANALYST = "research-analyst"
ROLE_TRADER = "trader"
SOURCE_RELATIONAL = "relational"
SOURCE_CONTROL_ROOM = "control_room"
OPERATOR_POLICY = "policy.principal-subgraph"
OPERATOR_SIMILARITY = "similarity.corpus-select"
REQUIRED_OPERATORS: frozenset[str] = frozenset(CONFIG["product_class"]["required_operator_keys"])
GATE_ID: str = CONFIG["product_class"]["declared_product_gate"]["gate_id"]


# --- fixtures and helpers ---------------------------------------------------------


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


@pytest.fixture(scope="module")
def principals(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Perspective]:
    """Role → in-process perspective, from the estate's own principal register.

    The principal ids are the ones the environment document names credentials
    for; the role each carries is read from `ccf_v2.principal`, as `run.py`
    reads it. Only the roles `artifacts/perspectives.yaml` declares are kept,
    so the ungranted principal drops out here by data, not by name.
    """
    with modules["produce"].product(tmp_path_factory.mktemp("register")) as opened:
        roles = modules["acquisition"].principal_roles(relational_settings=opened.sources[SOURCE_RELATIONAL])
        credentialed = tuple(opened.sources["credentials"])
    declared = modules["projection"].ROLE_MEMBERS
    chosen = {
        roles[principal_id]: Perspective(principal_id=principal_id, role=roles[principal_id])
        for principal_id in credentialed
        if roles.get(principal_id) in declared
    }
    assert set(chosen) == set(declared), f"the register maps {sorted(chosen)} of `perspectives.yaml`"
    return chosen


@dataclass(frozen=True)
class _Answer:
    """One outcome on the paved road with the record behind it."""

    outcome: Any
    record: DecisionReplayRecord

    @property
    def product(self) -> Any:
        assert isinstance(self.outcome, ServedProduct), getattr(self.outcome, "detail", self.outcome)
        return self.outcome.product

    @property
    def refusal(self) -> RefusalEnvelope:
        assert isinstance(self.outcome, RefusalEnvelope), f"served `{type(self.outcome).__name__}`"
        return self.outcome


def _question(opened: OpenedProduct, *, subject: str, asked_at: datetime, **params: Any) -> ProductRequest:
    parameters = {name: value for name, value in params.items() if value is not None}
    return opened.question(subject=subject, asked_at=asked_at, intent=INTENT, freshness=FRESHNESS, parameters=parameters)


def _answer(
    modules: dict[str, Any], scratch: pathlib.Path, *, perspective: Perspective,
    subject: str = DEMONSTRATION_ISSUER, asked_at: datetime = T1, **params: Any,
) -> _Answer:
    """One question on the paved road, in its own scratch: the outcome as data."""
    with modules["produce"].product(scratch) as opened:
        outcome = opened.answer(_question(opened, subject=subject, asked_at=asked_at, **params), perspective=perspective)
        return _Answer(outcome=outcome, record=opened.record_of(outcome))


Wrapper = Callable[[Callable[[AcquisitionContext], tuple[SignalEnvelope, ...]], AcquisitionContext], tuple[SignalEnvelope, ...]]


def _sabotage(monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], wrapper: Wrapper) -> None:
    """Wrap the tree's `acquire` BEFORE the product opens, so the road binds the wrapper."""
    deployment = modules["deployment"]
    original = deployment.acquire
    monkeypatch.setattr(deployment, "acquire", lambda context: wrapper(original, context))


def _note_ids(envelopes: tuple[SignalEnvelope, ...]) -> set[str]:
    """The research notes among ``envelopes``, by the deployment's own match key."""
    return {
        str(envelope.raw_payload["note_id"])
        for envelope in envelopes
        if "research_node" in envelope.raw_payload
    }


def _relabelled(envelopes: tuple[SignalEnvelope, ...]) -> tuple[SignalEnvelope, ...]:
    """Every classified claim re-labelled OUTSIDE the product's vocabulary."""
    return tuple(
        envelope.model_copy(update={"raw_payload": {**envelope.raw_payload, "classification": FOREIGN_CLASSIFICATION}})
        if "classification" in envelope.raw_payload
        else envelope
        for envelope in envelopes
    )


def _declassified(original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    return _relabelled(original(context))


def _freshness(answer: _Answer) -> Decimal:
    return Decimal(str(answer.product.debt.factors.freshness))


def _latest_position_date(answer: _Answer) -> date:
    positions = answer.product.payload["positions"]
    assert positions, "the trader's view holds no position"
    return max(date.fromisoformat(str(item["as_of"])) for item in positions)


def _vessel(answer: _Answer) -> dict[str, Any]:
    return answer.product.model_dump(mode="json")


# --- the served baselines, one question each ---------------------------------------


@pytest.fixture(scope="module")
def banker_t1(modules: dict[str, Any], principals: dict[str, Perspective], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    return _answer(modules, tmp_path_factory.mktemp("banker"), perspective=principals[ROLE_BANKER])


@pytest.fixture(scope="module")
def analyst_t1(modules: dict[str, Any], principals: dict[str, Perspective], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    return _answer(modules, tmp_path_factory.mktemp("analyst"), perspective=principals[ROLE_ANALYST])


@pytest.fixture(scope="module")
def trader_t1(modules: dict[str, Any], principals: dict[str, Perspective], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    return _answer(modules, tmp_path_factory.mktemp("trader"), perspective=principals[ROLE_TRADER])


@pytest.fixture(scope="module")
def trader_comparison(modules: dict[str, Any], principals: dict[str, Perspective], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    return _answer(
        modules, tmp_path_factory.mktemp("trader-comparison"), perspective=principals[ROLE_TRADER],
        subject=FRESHNESS_COMPARISON_ISSUER,
    )


@pytest.fixture(scope="module")
def nonexistent_served(modules: dict[str, Any], principals: dict[str, Perspective], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """A subject with no issuer row, under the analyst, at the diagnostic tolerance."""
    return _answer(
        modules, tmp_path_factory.mktemp("nonexistent"), perspective=principals[ROLE_ANALYST],
        subject=NONEXISTENT_ISSUERS[0], debt_tolerance=DIAGNOSTIC_TOLERANCE,
    )


@pytest.fixture(scope="module")
def nonexistent_withheld(modules: dict[str, Any], principals: dict[str, Perspective], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The same subject at the class default tolerance: withheld, as data."""
    return _answer(
        modules, tmp_path_factory.mktemp("nonexistent-withheld"), perspective=principals[ROLE_ANALYST],
        subject=NONEXISTENT_ISSUERS[0],
    )


# --- G03: the declared gate's refusal branch ------------------------------------------


def test_an_edge_outside_the_principal_vocabulary_is_refused_by_the_declared_gate(
    monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], principals: dict[str, Perspective],
    analyst_t1: _Answer, tmp_path: pathlib.Path,
) -> None:
    """Vocabulary containment: ONE extra edge minted into the analyst's fabric,
    of a type the class walks but the analyst's plan does not permit, with an
    endpoint the Policy operator keeps — so the edge survives to Π — turns
    the served product into a `product-invariant-refusal` under the declared
    gate, and the record names the breach. The un-sabotaged analyst is served.

    Declared product gate `MWE-G03` (`CP-SPEC-017` §G.1).
    """
    acquisition, deployment = modules["acquisition"], modules["deployment"]
    terms = acquisition.vocabulary()
    analyst = principals[ROLE_ANALYST]
    assert isinstance(analyst_t1.outcome, ServedProduct)
    foreign_type = terms["edges"]["position"]
    assert foreign_type not in analyst_t1.product.payload["plan"]["permitted_edge_types"]

    def inject(original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        emitted = original(context)
        dated = (context.request.asked_at - timedelta(days=1)).date()
        record = acquisition.Record(
            entity_class="position", edge_type=foreign_type, dated=dated,
            entity_uri=f"{terms['entity_uri_prefix']['position']}SABOTAGE-1",
            attributes={
                "position_id": "SABOTAGE-1", "book": "sabotage", "quantity": "1", "as_of": dated.isoformat(),
                "classification": terms["classification"]["assignment"]["position"],
            },
        )
        issuer_uri = f"{terms['entity_uri_prefix']['issuer']}{context.request.subject}"
        edge = deployment._edge(tenant_id=context.tenant_id, at=context.instant, ordinal=len(emitted), subject=issuer_uri, record=record)
        node = deployment._node(tenant_id=context.tenant_id, at=context.instant, record=record)
        return (edge, node, *emitted)

    _sabotage(monkeypatch, modules, inject)
    sabotaged = _answer(modules, tmp_path, perspective=analyst)
    refusal = sabotaged.refusal
    assert refusal.kind == "product-invariant-refusal", refusal.kind
    assert refusal.reason == GATE_ID, refusal.reason
    breach = sabotaged.record.content_generation_path.assembly_refusal
    assert foreign_type in breach and "MWE-G03" in breach, "the record's `assembly_refusal` names no breach"
    assert sabotaged.record.perspective_conditioning.principal_id == analyst.principal_id


# --- G06: the Policy operator, live --------------------------------------------------


def test_a_claim_outside_the_classification_vocabulary_never_reaches_the_product(
    monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], principals: dict[str, Perspective], tmp_path: pathlib.Path,
) -> None:
    """The Policy operator is live: every claim acquisition emitted for the
    analyst, re-labelled with a classification outside the vocabulary, is
    removed before anything ranks or walks — together with the edges minted
    to it (`GQ-16` closure). At the diagnostic tolerance the empty view is
    served with `policy.principal-subgraph` among the operators that returned
    empty and no research note id in its canonical bytes; at the class
    default it is withheld as tolerance-exceeded, with no note id either.

    Declared product gate `MWE-G06` (`CP-SPEC-017` §G.1).
    """
    analyst = principals[ROLE_ANALYST]
    emitted: list[SignalEnvelope] = []

    def declassify(original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        envelopes = original(context)
        emitted.extend(envelopes)
        return _relabelled(envelopes)

    _sabotage(monkeypatch, modules, declassify)
    served = _answer(modules, tmp_path / "served", perspective=analyst, debt_tolerance=DIAGNOSTIC_TOLERANCE)
    withheld = _answer(modules, tmp_path / "withheld", perspective=analyst)

    note_ids = _note_ids(tuple(emitted))
    assert note_ids, "acquisition emitted no `research_node`"
    product = served.product
    assert product.payload["research"] == [] and product.payload["edge_types_served"] == []
    assert product.computed_empty is not None, "no `computed_empty` finding on an emptied view"
    assert OPERATOR_POLICY in product.computed_empty.operators_returned_empty
    served_bytes = canonical_bytes(product)
    leaked = sorted(note_id for note_id in note_ids if note_id.encode("utf-8") in served_bytes)
    assert not leaked, f"note ids `{leaked}` survive in the served bytes"

    refusal = withheld.refusal
    assert refusal.kind == "tolerance-exceeded", refusal.kind
    refusal_text = refusal.model_dump_json() + withheld.record.model_dump_json()
    assert not any(note_id in refusal_text for note_id in note_ids), "a note id rides the refusal"


# --- G07: policy before similarity --------------------------------------------------


def test_policy_forms_the_view_before_similarity_ranks_it(
    monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], principals: dict[str, Perspective],
    analyst_t1: _Answer, tmp_path: pathlib.Path,
) -> None:
    """Policy before similarity: the served plan runs `policy.principal-subgraph`
    ahead of `similarity.corpus-select`; every research note the analyst is
    served is one acquisition emitted inside the analyst's envelope, and the
    served set is bounded by that floor (the similarity floor keeps some);
    and when Policy removes every claim, Similarity ranks nothing — it is
    among the operators that returned empty, not a ranking over the removed.

    Declared product gate `MWE-G07` (`CP-SPEC-017` §G.1).
    """
    analyst = principals[ROLE_ANALYST]
    plan = analyst_t1.record.content_generation_path.operator_plan
    assert plan.index(OPERATOR_POLICY) < plan.index(OPERATOR_SIMILARITY), plan

    emitted: list[SignalEnvelope] = []

    def record_only(original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        envelopes = original(context)
        emitted.extend(envelopes)
        return envelopes

    _sabotage(monkeypatch, modules, record_only)
    recorded = _answer(modules, tmp_path / "recorded", perspective=analyst)
    acquired = _note_ids(tuple(emitted))
    served = {str(item["note_id"]) for item in recorded.product.payload["research"]}
    assert served and acquired, "no `research` note served or acquired"
    assert served <= acquired, f"served notes `{sorted(served - acquired)}` were never acquired"
    assert served == {str(item["note_id"]) for item in analyst_t1.product.payload["research"]}

    _sabotage(monkeypatch, modules, _declassified)
    emptied = _answer(modules, tmp_path / "emptied", perspective=analyst, debt_tolerance=DIAGNOSTIC_TOLERANCE)
    finding = emptied.product.computed_empty
    assert finding is not None and OPERATOR_SIMILARITY in finding.operators_returned_empty
    assert OPERATOR_POLICY in finding.operators_returned_empty


# --- G09: the control room first ------------------------------------------------------


def test_an_unreachable_control_room_stops_every_principal(
    monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], principals: dict[str, Perspective], tmp_path: pathlib.Path,
) -> None:
    """The control room is read first and is mandatory: with the departmental
    store pointed at a path that does not exist, no principal is served — the
    banker, the analyst and the trader each stop with the control room named.

    Declared product gate `MWE-G09` (`CP-SPEC-017` §G.1).
    """
    acquisition = modules["acquisition"]
    missing = str(tmp_path / "no-such-departmental.sqlite")

    def without_control_room(original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        sources = {**context.sources, SOURCE_CONTROL_ROOM: {**context.sources[SOURCE_CONTROL_ROOM], "path": missing}}
        return original(replace(context, sources=sources))

    _sabotage(monkeypatch, modules, without_control_room)
    for role, perspective in sorted(principals.items()):
        # A raise through `opened.answer`, not a governed refusal — see the
        # findings this module reports (the `CP13C-F-03` class).
        with pytest.raises(acquisition.ControlRoomUnreachable) as stopped:
            _answer(modules, tmp_path / role, perspective=perspective)
        assert missing in str(stopped.value), f"`{role}` stopped without naming the store"


# --- G12: supersede-only classes, and the one that decays ------------------------------


def test_supersede_only_classes_read_fresh_and_positions_decay_by_as_of(
    banker_t1: _Answer, analyst_t1: _Answer, trader_t1: _Answer, trader_comparison: _Answer,
) -> None:
    """Every class the banker and the analyst are served decays supersede-only,
    so their freshness is exactly one. The trader's position decays on its
    `as_of` clock: on the demonstration issuer freshness is below one, on the
    comparison issuer it is at least as high, and the two order the same way
    as the latest position dates the payloads carry — the ordering, never
    the number.

    Declared product gate `MWE-G12` (`CP-SPEC-017` §G.1).
    """
    assert _freshness(banker_t1) == Decimal(1) and _freshness(analyst_t1) == Decimal(1)
    demonstration, comparison = _freshness(trader_t1), _freshness(trader_comparison)
    assert demonstration < Decimal(1), f"position freshness `{demonstration}` does not decay"
    assert comparison >= demonstration, f"`{comparison}` < `{demonstration}`"
    assert _latest_position_date(trader_comparison) >= _latest_position_date(trader_t1)
    assert _latest_position_date(trader_t1) <= T1.date()


# --- G16: A6, the existence oracle ------------------------------------------------------


def test_a_policy_emptied_subject_reads_as_a_nonexistent_one(
    monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], principals: dict[str, Perspective],
    analyst_t1: _Answer, nonexistent_served: _Answer, nonexistent_withheld: _Answer, tmp_path: pathlib.Path,
) -> None:
    """A6 on the paved serve path, under the analyst: a subject whose every
    claim Policy removed and a subject with no issuer row are served
    path-for-path equal at the diagnostic tolerance, each with every operator
    returned empty; at the class default both are withheld with one kind, one
    detail and one field set. Positive control: the assembled demonstration
    issuer differs from the nonexistent one under `payload` and under
    `computed_empty`. Two different nonexistent LEIs are byte-identical.

    Declared product gate `MWE-G16` (`CP-SPEC-017` §G.1).
    """
    analyst = principals[ROLE_ANALYST]
    empty = nonexistent_served.product
    assert empty.computed_empty is not None and set(empty.computed_empty.operators_returned_empty) == REQUIRED_OPERATORS

    _sabotage(monkeypatch, modules, _declassified)
    emptied_served = _answer(modules, tmp_path / "emptied", perspective=analyst, debt_tolerance=DIAGNOSTIC_TOLERANCE)
    emptied_withheld = _answer(modules, tmp_path / "emptied-withheld", perspective=analyst)
    monkeypatch.undo()
    other_nonexistent = _answer(
        modules, tmp_path / "other", perspective=analyst, subject=NONEXISTENT_ISSUERS[1], debt_tolerance=DIAGNOSTIC_TOLERANCE,
    )

    leaked = _diff_paths(_vessel(emptied_served), _vessel(nonexistent_served))
    assert not leaked, f"the vessels differ at `{sorted(leaked)}`"

    walled, missing = emptied_withheld.refusal, nonexistent_withheld.refusal
    assert (walled.kind, walled.detail, dict(walled.fields)) == (missing.kind, missing.detail, dict(missing.fields))

    distinguished = _diff_paths(_vessel(analyst_t1), _vessel(nonexistent_served))
    assert any(path.startswith("payload") for path in distinguished), sorted(distinguished)
    assert any(path.startswith("computed_empty") for path in distinguished), sorted(distinguished)

    assert canonical_bytes(other_nonexistent.product) == canonical_bytes(empty)


# --- a finding kept executable: the gate's ceiling travels with the candidate ------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "CP17-F-10: `deployment.wall_gate` reads `permitted_edge_types` off the candidate's own"
        " `plan` member, which acquisition wrote from `context.perspective`; an acquisition keyed"
        " to another principal carries that principal's plan and is served under the asking role"
    ),
)
def test_an_acquisition_keyed_to_another_principal_is_not_refused(
    monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], principals: dict[str, Perspective], tmp_path: pathlib.Path,
) -> None:
    """The analyst's question, acquired under the banker's perspective: the
    banker's engagement edges reach the analyst's vessel through
    `edge_types_served` and `entities_in_view`, the payload's `plan` is the
    banker's, and the declared gate — whose ceiling is that very member —
    admits it. Asserted as a refusal so the strict expected failure goes red
    the day the gate reads the ceiling from the credential instead.
    """
    banker, analyst = principals[ROLE_BANKER], principals[ROLE_ANALYST]

    def as_banker(original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        return original(replace(context, perspective=banker))

    _sabotage(monkeypatch, modules, as_banker)
    mis_keyed = _answer(modules, tmp_path, perspective=analyst)
    assert isinstance(mis_keyed.outcome, RefusalEnvelope), (
        f"served under `{mis_keyed.record.perspective_conditioning.role}`"
        f" with edges {mis_keyed.product.payload['edge_types_served']}"
    )
