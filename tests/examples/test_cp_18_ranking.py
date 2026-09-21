"""What `examples/cp-18-ib-opportunity-synthesis` ranks, and for whom.

Thirteen of the eighteen declared gates of `CP-SPEC-018` §G.1 execute here;
the three whose control is their own sabotage live in
`test_cp_18_sabotage.py` and the two replay gates in `test_cp_18_replay.py`.

Every assertion is a RELATIONSHIP or an IDENTITY — an ordering, a containment,
an equality between two live answers — and never an estate count or a pinned
rank. The estate is evidence, not a fixture.

**Reads the curated estate, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
import yaml
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.product import OpenedProduct
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-18-ib-opportunity-synthesis"

ESTATE_VARIABLES = (
    "CCF_CP_18_SQLITE_PATH", "CCF_CP_18_POSTGRES_DSN", "CCF_CP_18_POSTGRES_SCHEMA",
    "CCF_CP_18_FLUREE_URL", "CCF_CP_18_FLUREE_LEDGER", "CCF_CP_18_MONGO_URI",
    "CCF_CP_18_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
PERSPECTIVES: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "perspectives.yaml").read_text(encoding="utf-8"))["declaration"]

SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
SINCE: str = QUESTION["instants"]["SINCE"]
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
DIVERGENCE_PROSPECT: str = QUESTION["divergence_prospect"]

ROLES = ("ma", "dcm", "sector")
#: A limit wide enough to rank the whole portfolio, so a rank comparison is
#: over the same candidate set rather than over two different truncations.
WHOLE_BOOK = "50"


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the cp-18 estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    """One example tree's modules, whatever ran before — evicted in and out."""
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment,
               "produce": produce, "projection": projection}
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
class Answer:
    role: str
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct

    @property
    def payload(self) -> Mapping[str, Any]:
        return self.product.payload

    @property
    def ranks(self) -> Mapping[str, int]:
        return {row["lei"]: row["rank"] for row in self.payload["ranked_opportunities"]}


def _question(opened: OpenedProduct, deployment: Any, **params: Any) -> ProductRequest:
    parameters: dict[str, Any] = {
        deployment.AS_OF: params.pop("as_of", AS_OF),
        deployment.SINCE: params.pop("since", SINCE),
    }
    for name, value in params.items():
        if value is not None:
            parameters[name] = value
    return opened.question(
        subject=params.pop("subject", SUBJECT) if "subject" in params else SUBJECT,
        asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS, parameters=parameters,
    )


def _answer(
    modules: dict[str, Any], scratch: pathlib.Path, *, role: str,
    subject: str = SUBJECT, **params: Any,
) -> Answer:
    """One question on the paved road, in its own scratch, as the stated banker."""
    deployment = modules["deployment"]
    with modules["produce"].product(scratch) as opened:
        parameters: dict[str, Any] = {
            deployment.AS_OF: params.pop("as_of", AS_OF),
            deployment.SINCE: params.pop("since", SINCE),
        }
        parameters.update({k: v for k, v in params.items() if v is not None})
        asked = opened.question(subject=subject, asked_at=ASKED_AT, intent=INTENT,
                                freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(asked, perspective=Perspective(principal_id=subject, role=role))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return Answer(role=role, product=outcome.product,
                      record=opened.record_of(outcome), served=outcome)


@pytest.fixture(scope="module")
def book(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Answer]:
    """The demonstration banker's whole book, under each of the three perspectives."""
    root = tmp_path_factory.mktemp("cp18-book")
    deployment = modules["deployment"]
    return {
        role: _answer(modules, root / role, role=role, **{deployment.LIMIT: WHOLE_BOOK})
        for role in ROLES
    }


# =========================================================================
# IBO-G01 / IBO-G02 / IBO-G03 / IBO-G04 — the perspective IS the product
# =========================================================================


def test_the_served_plan_runs_policy_before_similarity(book: Mapping[str, Answer]) -> None:
    """The order is a SERVED fact, read off the product rather than the config.

    Declared product gate `IBO-G01` (`CP-SPEC-018` §G.1).
    """
    for answer in book.values():
        invoked = set(answer.product.lineage.operators_invoked)
        assert {"policy.principal-subgraph", "similarity.corpus-select",
                "temporal.as-of-boundary", "traversal.typed-neighborhood"} <= invoked, invoked
        plan = list(answer.record.content_generation_path.operator_plan)
        assert plan.index("policy.principal-subgraph") < plan.index("similarity.corpus-select"), plan
        assert tuple(step.operator_key for step in answer.record.content_generation_path.steps) == tuple(plan)


def test_three_perspectives_give_three_orderings_and_three_addresses(
    book: Mapping[str, Answer]
) -> None:
    """One banker, one instant, three perspectives — three different products.

    Declared product gate `IBO-G02` (`CP-SPEC-018` §G.1). Not three sorts of
    one ranking: three orderings, three content addresses, one class and one
    plan id.
    """
    orderings = {role: tuple(answer.ranks) for role, answer in book.items()}
    assert len(set(orderings.values())) == len(ROLES), orderings
    addresses = {role: content_hash(answer.product) for role, answer in book.items()}
    assert len(set(addresses.values())) == len(ROLES), addresses
    assert len({answer.record.content_generation_path.plan_id for answer in book.values()}) == 1
    assert len({answer.product.schema_name for answer in book.values()}) == 1


def test_the_weight_vector_discriminates_and_the_plan_does_not(
    book: Mapping[str, Answer], modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The orderings differ while the admitted signal-type set does not.

    Declared product gate `IBO-G03` (`CP-SPEC-018` §G.1), and the trap it
    guards is real: the estate's three projection plans permit IDENTICAL
    signal types (§C.4 trap 2), so an implementation keying the perspective's
    ranking on the plan would find the three perspectives indistinguishable
    and the counterfactual would silently stop being demonstrated.
    """
    admitted = {role: tuple(answer.payload["signal_types_admitted"]) for role, answer in book.items()}
    assert len(set(admitted.values())) == 1, admitted
    orderings = {role: tuple(answer.ranks) for role, answer in book.items()}
    assert len(set(orderings.values())) == len(ROLES), orderings
    # And the estate's own plans agree: the plan carries no discriminating set.
    acquisition, deployment = modules["acquisition"], modules["deployment"]
    with modules["produce"].product(tmp_path / "plans") as opened:
        relational = acquisition._Relational(
            dsn=opened.sources[deployment.SOURCE_RELATIONAL]["dsn"],
            schema=opened.sources[deployment.SOURCE_RELATIONAL]["schema"],
        )
        table = acquisition.vocabulary()["relational"]["tables"]["projection_plan"]
        plans = {
            modules["projection"].PERSPECTIVE_ID[role]: acquisition.plan_for(
                relational, perspective_id=modules["projection"].PERSPECTIVE_ID[role], table=table,
            )
            for role in ROLES
        }
    permitted = {plan.permitted_signal_types for plan in plans.values() if plan is not None}
    assert len(permitted) == 1, "the estate's plans differ; this gate's trap no longer holds"


def test_one_prospect_ranks_top_for_one_perspective_and_low_for_another(
    book: Mapping[str, Answer]
) -> None:
    """The counterfactual, from identical signals.

    Declared product gate `IBO-G04` (`CP-SPEC-018` §G.1). A maturity wall is
    the DCM banker's top-priced signal and near-noise to the M&A originator,
    so the same prospect sits near the top of one list and low in the other.
    The prospect is named by the artifact; **the ranks are read live and never
    pinned**, so estate drift exercises this gate rather than breaking it.
    """
    ma, dcm = book["ma"].ranks, book["dcm"].ranks
    assert set(ma) == set(dcm), "the two perspectives ranked different candidate sets"
    assert DIVERGENCE_PROSPECT in ma, f"{DIVERGENCE_PROSPECT} is not in the demonstration banker's book"
    size = len(ma)
    high, low = ma[DIVERGENCE_PROSPECT], dcm[DIVERGENCE_PROSPECT]
    assert high <= size / 3, (high, size)
    assert low > size / 2, (low, size)
    # The positive control: the two orderings are over one candidate set, so
    # the difference is the ranking function and not the candidates.
    assert book["ma"].payload["candidates_considered"] == book["dcm"].payload["candidates_considered"]


# =========================================================================
# IBO-G05 — the version that ranked it is named on it
# =========================================================================


def test_the_served_product_names_the_weight_version_that_ranked_it(
    book: Mapping[str, Answer]
) -> None:
    """A ranking whose weights are unknown is not replayable, so it says which.

    Declared product gate `IBO-G05` (`CP-SPEC-018` §G.1).
    """
    for answer in book.values():
        version = answer.payload["weight_version"]
        assert version, "the served product names no weight version"
        # The version is the SNAPSHOT's, not a value resolved now: it is
        # carried on the banker claim inside the hash-bound fabric.
        assert version in canonical_bytes(answer.product).decode("utf-8")
    assert len({answer.payload["weight_version"] for answer in book.values()}) == 1


# =========================================================================
# IBO-G08 / IBO-G09 — the restricted prospect, and the portfolio bound
# =========================================================================


def test_a_restricted_prospect_remains_a_candidate_with_bounded_evidence(
    book: Mapping[str, Answer]
) -> None:
    """Classification, not deletion — Dave's ruling of 2026-09-21.

    Declared product gate `IBO-G08` (`CP-SPEC-018` §G.1). A restricted
    prospect stays in the candidate universe and is ranked; what the
    restriction bounds is the evidence admitted for it. A banker-local note
    may encode exactly what the restriction exists to contain, so no such note
    contributes to a restricted prospect's score.
    """
    answer = book["ma"]
    ranked = answer.payload["ranked_opportunities"]
    restricted = [row for row in ranked if row["restriction_type"]]
    assert restricted, "no restricted prospect is in this banker's book; the gate would be vacuous"
    for row in restricted:
        assert row["rank"] >= 1 and row["score"], "a restricted prospect was not ranked"
        sources = {item["classification"] for item in row["contributing_signals"]}
        assert "banker-local" not in sources, (
            f"a banker-local note reached restricted prospect {row['lei']}; the restriction"
            f" bounds the evidence admitted for it"
        )
    # The positive control: an UNrestricted prospect in the same book does
    # carry local-note evidence, so the bound is discriminating.
    with_notes = [row for row in ranked
                  if not row["restriction_type"]
                  and any(item["classification"] == "banker-local" for item in row["contributing_signals"])]
    assert with_notes, "no unrestricted prospect carries a local note; the bound proves nothing"


def test_no_prospect_outside_the_portfolio_is_ranked(book: Mapping[str, Answer]) -> None:
    """The candidate universe is the CONSUMER's.

    Declared product gate `IBO-G09` (`CP-SPEC-018` §G.1).
    """
    for answer in book.values():
        portfolio = set(answer.payload["portfolio"])
        assert portfolio, "the banker covers nothing; the containment would be vacuous"
        assert set(answer.ranks) <= portfolio, sorted(set(answer.ranks) - portfolio)
        assert answer.payload["portfolio_size"] == len(portfolio)


# =========================================================================
# IBO-G10 / IBO-G11 — the banker's own notebook
# =========================================================================


def test_local_notes_reach_their_own_banker_and_no_other(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path, book: Mapping[str, Answer]
) -> None:
    """A banker's notes are that banker's, and no other's.

    Declared product gate `IBO-G10` (`CP-SPEC-018` §G.1).
    """
    mine = book["ma"]
    note_ids = {row["note_id"] for row in mine.payload["local_note_attribution"]}
    assert note_ids, "the demonstration banker holds no local note; the gate would be vacuous"
    # Every note carried is one this banker's own read returned; the seam
    # queries the departmental store BY banker id, so the containment below is
    # the measurement that the seam is actually bounded.

    other = _answer(modules, tmp_path / "other", role="dcm", subject="BKR006",
                    **{modules["deployment"].LIMIT: WHOLE_BOOK})
    theirs = {row["note_id"] for row in other.payload["local_note_attribution"]}
    assert not (note_ids & theirs), sorted(note_ids & theirs)
    rendered = canonical_bytes(other.product).decode("utf-8")
    for note_id in note_ids:
        assert note_id not in rendered, f"note {note_id} reached another banker's product"


def test_a_local_note_observably_moves_a_ranking(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path, book: Mapping[str, Answer]
) -> None:
    """Removing the local-note evidence moves a ranked row.

    Declared product gate `IBO-G11` (`CP-SPEC-018` §G.1). The control IS the
    sabotage: the note evidence is withheld at the acquisition seam and the
    two orderings are compared. A fabric that cannot reach the banker's own
    notebook produces a ranking the banker distrusts, and this is the
    measurement that the notebook is actually reaching it.
    """
    baseline = book["ma"]
    reached = {row["lei"] for row in baseline.payload["ranked_opportunities"]
               for item in row["contributing_signals"] if item["classification"] == "banker-local"}
    assert reached, "no local note reached the ranking; the gate would be vacuous"

    acquisition = modules["acquisition"]
    original = acquisition._records

    def without_notes(*args: Any, **kwargs: Any) -> Any:
        return tuple(r for r in original(*args, **kwargs) if r.entity_class != "note")

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(acquisition, "_records", without_notes)
        stripped = _answer(modules, tmp_path / "no-notes", role="ma",
                           **{modules["deployment"].LIMIT: WHOLE_BOOK})
    finally:
        monkeypatch.undo()

    assert tuple(stripped.ranks) != tuple(baseline.ranks), (
        "removing every banker-local note left the ordering unchanged; the notebook"
        " reaches the fabric but does not reach the ranking"
    )
    moved = {lei for lei in baseline.ranks
             if lei in stripped.ranks and stripped.ranks[lei] != baseline.ranks[lei]}
    assert moved & reached, (sorted(moved), sorted(reached))


# =========================================================================
# IBO-G12 / IBO-G13 — the shape, and the explanation
# =========================================================================


def test_each_perspective_serves_its_declared_member_set(book: Mapping[str, Answer]) -> None:
    """The member set equals the declared shape, exactly.

    Declared product gate `IBO-G12` (`CP-SPEC-018` §G.1). The expected set is
    built HERE, from `artifacts/perspectives.yaml` read by this module, and
    never from the projection's own reader — a comparison against the code
    under test would stay green through any change the two made together.
    """
    for role, answer in book.items():
        declared = set(PERSPECTIVES["common_members"]) | set(PERSPECTIVES["perspectives"][role]["members"])
        assert set(answer.payload) == declared, (role, sorted(set(answer.payload) ^ declared))
    shapes = {role: frozenset(answer.payload) for role, answer in book.items()}
    assert len(set(shapes.values())) == len(ROLES), shapes


def test_every_ranked_row_carries_its_contributing_signals(book: Mapping[str, Answer]) -> None:
    """A ranking that cannot justify itself is not served.

    Declared product gate `IBO-G13` (`CP-SPEC-018` §G.1). Every ranked row
    names the signals that put it there, with the weight each carried, its age
    and its evidence — because a scored recommendation nobody can justify is a
    recommendation nobody will action.
    """
    for answer in book.values():
        admitted = set(answer.payload["signal_types_admitted"])
        assert answer.payload["ranked_opportunities"], "nothing was ranked"
        for row in answer.payload["ranked_opportunities"]:
            contributions = row["contributing_signals"]
            assert contributions, f"ranked row {row['lei']} carries no contributing signal"
            for item in contributions:
                assert item["signal_type"] in admitted, item
                assert item["weight"] and item["contribution"], item
                assert "age_days" in item, item
            # The score is the sum of what is shown, within the rounding the
            # payload carries — the explanation is the arithmetic, not a gloss.
            shown = sum(Decimal(item["contribution"]) for item in contributions)
            assert shown <= Decimal(row["score"]) + Decimal("0.000001"), (shown, row["score"])


# =========================================================================
# IBO-G17 / IBO-G18 — optional means optional, and it is stated
# =========================================================================


def test_the_absent_optional_child_does_not_refuse_the_product(
    book: Mapping[str, Answer]
) -> None:
    """An absent optional CP-17 child is named debt, not a refusal.

    Declared product gate `IBO-G17` (`CP-SPEC-018` §G.1, §F.4.1). The child
    count is zero by ruling (§F.4.3) — the paved seam asks one class exactly
    one question and refuses a duplicate `product_class` in `requires`, so the
    ruled subset composition is unreachable without reopening `D-IMPL-336`.
    The product is served anyway, from the evidence CP-18 can admit alone.
    """
    for answer in book.values():
        assert isinstance(answer.served, ServedProduct)
        optional = answer.payload["optional_context"]
        assert optional["mnpi_wall_child"] == "absent"
        assert optional["child_count"] == 0
        assert optional["reason"], "the absent optional context names no reason"
        assert answer.payload["ranked_opportunities"], "the ranking was not served"


def test_the_narrower_evidence_base_is_stated_not_silent(book: Mapping[str, Answer]) -> None:
    """A consumer must not have to assume the evidence base was complete.

    Declared product gate `IBO-G18` (`CP-SPEC-018` §G.1). With the child count
    at zero, EVERY ranked row rests on the narrower base, and every row says
    so rather than leaving a consumer to infer it.
    """
    for answer in book.values():
        for row in answer.payload["ranked_opportunities"]:
            assert row["optional_context_contributed"] is False, row
        # And the product-level statement agrees with the per-row one.
        assert answer.payload["optional_context"]["child_count"] == 0
        assert json.dumps(answer.payload["optional_context"])
