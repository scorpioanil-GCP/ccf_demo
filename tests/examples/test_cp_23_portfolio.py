"""What `examples/cp-23-portfolio-early-warning` serves, and to whom.

Fifteen of the nineteen declared gates of `CP-SPEC-023` §G.1 execute here; the
gate's own positive controls live in `test_cp_23_sabotage.py`.

Every assertion is a RELATIONSHIP or an IDENTITY and never an estate count.
**Reads the curated estate, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

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
from ccf.contracts.canonical import content_hash
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-23-portfolio-early-warning"

ESTATE_VARIABLES = (
    "CCF_CP_23_POSTGRES_DSN", "CCF_CP_23_POSTGRES_SCHEMA",
    "CCF_CP_23_FLUREE_URL", "CCF_CP_23_FLUREE_LEDGER",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
TIERS: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "severity-tiers.yaml").read_text(encoding="utf-8"))["declaration"]

BOOK: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
OTHER_BOOK: str = QUESTION["other_book"]

COVERAGE = ("PRIN-PM-001", "coverage")
CREDIT = ("PRIN-CO-002", "credit")
PRODUCT = ("PRIN-PR-003", "product")


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-23 estate is not configured: {', '.join(missing)} unset"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
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
    with tree_modules(EXAMPLE) as loaded:
        yield loaded


@dataclass(frozen=True)
class Answer:
    role: str
    product: Any
    record: DecisionReplayRecord

    @property
    def payload(self) -> Mapping[str, Any]:
        return self.product.payload

    @property
    def address(self) -> str:
        return content_hash(self.product)


def ask(
    modules: dict[str, Any], scratch: pathlib.Path, *,
    principal: tuple[str, str] = COVERAGE, book: str = BOOK, intent: str = INTENT,
    members: list[str] | None = None, **params: Any,
) -> Any:
    deployment, produce = modules["deployment"], modules["produce"]
    with produce.product(scratch) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: AS_OF}
        parameters.update({k: v for k, v in params.items() if v is not None})
        asked = produce.book_question(
            opened, book=book, asked_at=ASKED_AT, intent=intent, freshness=FRESHNESS,
            members=members, **parameters,
        )
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=principal[0], role=principal[1]))
        if not isinstance(outcome, ServedProduct):
            return outcome
        return Answer(role=principal[1], product=outcome.product, record=opened.record_of(outcome))


def answer(modules: dict[str, Any], scratch: pathlib.Path, **kwargs: Any) -> Answer:
    outcome = ask(modules, scratch, **kwargs)
    assert isinstance(outcome, Answer), getattr(outcome, "detail", outcome)
    return outcome


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Answer]:
    root = tmp_path_factory.mktemp("cp23")
    return {
        "coverage": answer(modules, root / "cov", principal=COVERAGE),
        "credit": answer(modules, root / "cre", principal=CREDIT, intent="credit-review"),
        "product": answer(modules, root / "pro", principal=PRODUCT),
    }


# =========================================================================
# PEW-G01 / PEW-G03 — the declared plan, and population grain
# =========================================================================


def test_the_served_plan_matches_the_declaration_and_runs_policy_first(
    served: Mapping[str, Answer],
) -> None:
    """THREE operator keys, not a fixed four — there is no ranked corpus here.

    The order is read off replay dimension 5; the product's own
    `operators_invoked` is a `frozenset` and can say nothing about order
    (`ABS-F-04`, rung 16).

    Declared product gate `PEW-G01` (`CP-SPEC-023` §G.1).
    """
    declared = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    keys = set(declared["product_class"]["required_operator_keys"])
    assert "similarity.corpus-select" not in keys, "this product declares no ranked corpus"
    for reply in served.values():
        assert set(reply.product.lineage.operators_invoked) == keys, (
            "the served operator set is the declaration, not a fixed four"
        )
        plan = reply.record.content_generation_path.operator_plan
        assert plan.index("policy.principal-subgraph") == 0, f"Policy runs first; executed {plan}"


def test_the_book_is_served_at_population_grain(served: Mapping[str, Answer]) -> None:
    """The member count is a served fact and the measures are set properties.

    Declared product gate `PEW-G03` (`CP-SPEC-023` §G.1).
    """
    reply = served["coverage"]
    population = reply.payload["population"]
    assert len(population) > 1, "a population of one would not exercise this rung"
    assert int(reply.payload["member_count"]) == len(population)
    # The measures span the population rather than describing one member.
    assert len(reply.payload["utilization"]) == len(population)
    assert int(reply.payload["population_debt"]["members"]) == len(population)


# =========================================================================
# PEW-G02 / PEW-G04 — containment, and narrowing
# =========================================================================


def test_every_served_member_declares_book_membership(served: Mapping[str, Answer]) -> None:
    """Membership is an ENTITY ATTRIBUTE, so per-member supersession reaches the register.

    Declared product gate `PEW-G02` (`CP-SPEC-023` §C.3 trap 1, §G.1).
    """
    for reply in served.values():
        for member in reply.payload["population"]:
            assert member["in_book"] == "true", f"{member['lei']} is served without membership"


def test_a_member_outside_the_book_is_refused_by_name(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """`members` NARROWS and never widens.

    Declared product gate `PEW-G04` (`CP-SPEC-023` §B.3, §G.1).
    """
    whole = answer(modules, tmp_path / "whole")
    inside = [row["lei"] for row in whole.payload["population"]][:2]

    narrowed = answer(modules, tmp_path / "narrow", members=inside)
    assert len(narrowed.payload["population"]) == len(inside), "the population narrowed"

    outcome = ask(modules, tmp_path / "outside", members=[*inside, "NOT-A-REAL-LEI-000000"])
    assert not isinstance(outcome, Answer), "a member outside the book is never served"
    # AND IT IS THE CONTAINMENT CHECK THAT REFUSES, not a downstream count
    # mismatch: a served product whose population merely came out short would
    # also fail `PEW-G03`, so the mechanism is asserted at its own seam.
    acquisition = modules["acquisition"]
    with pytest.raises(acquisition.NotInBook):
        acquisition.acquire(
            banker_id=BOOK, as_of=ASKED_AT, intent=INTENT, perspective="coverage",
            members=[*inside, "NOT-A-REAL-LEI-000000"], requested_classes=(),
            requested_floor=None,
            relational_settings={"dsn": os.environ["CCF_CP_23_POSTGRES_DSN"],
                                 "schema": os.environ["CCF_CP_23_POSTGRES_SCHEMA"]},
            graph_settings={"url": os.environ["CCF_CP_23_FLUREE_URL"],
                            "ledger": os.environ["CCF_CP_23_FLUREE_LEDGER"]},
        )


# =========================================================================
# PEW-G05 / PEW-G06 — `Q2`, and they cannot satisfy each other
# =========================================================================


def test_two_orderings_of_one_membership_are_one_determination(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The DEPLOYMENT canonicalizes, because membership is semantically a set.

    Declared product gate `PEW-G05` (`CP-SPEC-023` §F.4 `Q2`, ruled 2026-09-21).
    """
    whole = answer(modules, tmp_path / "w")
    trio = [row["lei"] for row in whole.payload["population"]][:3]
    forward = answer(modules, tmp_path / "f", members=list(trio))
    reverse = answer(modules, tmp_path / "r", members=list(reversed(trio)))
    assert forward.address == reverse.address, (
        "two orderings of one membership must be ONE determination after canonicalization"
    )
    assert forward.payload["book"]["member_digest"] == reverse.payload["book"]["member_digest"]
    # THE PRODUCT'S PAYLOAD SORTS ITS OWN POPULATION, so the address alone
    # cannot tell whether the REQUEST was canonicalized. The effective request
    # is where canonicalization has to land, and the replay record carries it.
    forward_members = forward.record.content_generation_path.request.parameters["members"]
    reverse_members = reverse.record.content_generation_path.request.parameters["members"]
    assert forward_members == reverse_members == sorted(trio), (
        "the EFFECTIVE REQUEST must carry the canonical member order, or two orderings"
        " are two determinations in the record even where the payload agrees"
    )


def test_a_different_membership_is_a_different_determination(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The CONVERSE — so `PEW-G05` cannot be met by collapsing everything.

    Declared product gate `PEW-G06` (`CP-SPEC-023` §F.4 `Q2`, ruled 2026-09-21).
    """
    whole = answer(modules, tmp_path / "w")
    leis = [row["lei"] for row in whole.payload["population"]]
    first = answer(modules, tmp_path / "a", members=leis[:3])
    second = answer(modules, tmp_path / "b", members=[*leis[:2], leis[3]])
    assert first.address != second.address, (
        "a genuinely different membership must be a different determination"
    )


# =========================================================================
# PEW-G07 — three roles, one book
# =========================================================================


def test_the_payload_shape_follows_the_role_not_the_book(served: Mapping[str, Answer]) -> None:
    """A role that may not see covenant history carries no empty covenant member.

    Declared product gate `PEW-G07` (`CP-SPEC-023` §A, §G.1).
    """
    shapes = {role: frozenset(reply.payload) for role, reply in served.items()}
    assert len(set(shapes.values())) > 1, "the roles must not all see the same shape"
    assert "covenant_history" in shapes["credit"] and "concentration" in shapes["credit"]
    assert "covenant_history" not in shapes["coverage"]
    # And the `product` role sees a strictly smaller POPULATION — its members
    # are only those with a facility.
    assert len(served["product"].payload["population"]) < len(served["coverage"].payload["population"])
    for member in served["product"].payload["utilization"]:
        assert member["has_facility"] == "true", "the product role sees facility-covered members only"


# =========================================================================
# PEW-G08 — the tier artifact is the authority
# =========================================================================


def test_every_tier_names_the_artifact_that_assigned_it(served: Mapping[str, Answer]) -> None:
    """No tier is hard-coded; the Control Plane artifact decides.

    Declared product gate `PEW-G08` (`CP-SPEC-023` §G.1).
    """
    declared = {str(tier["label"]) for tier in TIERS["tiers"]}
    signals = served["coverage"].payload["early_warning"]
    assert signals, "the demonstration book carries signals"
    labels = {row["tier_label"] for row in signals}
    assert labels <= declared, f"{labels - declared} are not declared tiers"
    assert len(labels) > 1, "a single tier for every signal would not exercise the artifact"
    for row in signals:
        assert row["tier_policy_version"], "each tiered signal names the artifact version"


def test_a_severity_floor_below_the_declared_one_is_refused(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """A floor may be RAISED and never lowered.

    Declared product gate `PEW-G08` (`CP-SPEC-023` §B.3, §G.1).
    """
    base = answer(modules, tmp_path / "lo")
    raised = answer(modules, tmp_path / "hi", severity_floor="0.45")
    assert len(raised.payload["early_warning"]) < len(base.payload["early_warning"]), (
        "raising the floor admits strictly fewer signals"
    )

    # A floor BELOW the declared one is refused by name.
    outcome = ask(modules, tmp_path / "under", severity_floor="-0.5")
    assert not isinstance(outcome, Answer), "a floor below the declared one is refused"

    # AND RAISING IT HAS A REAL COST, which is the SDK working rather than
    # failing: narrowing what the book looks at thins its evidence, debt rises,
    # and above the declared tolerance the product is WITHHELD rather than
    # served thin (`PEW-F-02`).
    severe = ask(modules, tmp_path / "severe", severity_floor="0.9")
    assert not isinstance(severe, Answer), "a floor that empties the evidence is withheld"
    assert severe.kind == "tolerance-exceeded", (
        f"the withholding names the tolerance it exceeded; got {severe.kind}"
    )


# =========================================================================
# PEW-G09 / PEW-G10 — freshness per class, and the TTL anchor
# =========================================================================


def test_freshness_is_reported_per_class_and_never_as_one_book_number(
    served: Mapping[str, Answer],
) -> None:
    """Which class is weak must be visible; an average would hide a stale one.

    Declared product gates `PEW-G09` and `PEW-G10` (`CP-SPEC-023` §C.2, ruled
    2026-09-21).
    """
    rows = served["coverage"].payload["signal_freshness_by_class"]
    assert len(rows) > 1, "more than one signal class must reach the book"
    ages = [int(row["age_days"]) for row in rows]
    assert ages == sorted(ages, reverse=True), "the weakest class is reported first"
    assert max(ages) > min(ages), (
        "the classes must differ in age, or per-class freshness demonstrates nothing"
    )
    for row in rows:
        assert row["signal_class"] and row["newest_observed_at"], "each class names its own instant"
    # NO single portfolio freshness timestamp.
    for key in served["coverage"].payload:
        assert "book_freshness" not in key and key != "portfolio_freshness_at"


def test_expiry_is_anchored_on_the_decision_not_on_the_evidence(
    served: Mapping[str, Answer],
) -> None:
    """A book's evidence has many ages, so none of them can anchor its expiry.

    Declared product gate `PEW-G11` (`CP-SPEC-023` §E.1, §G.1).
    """
    config = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert config["product_class"]["ttl_anchor"] == "from_decision"
    reply = served["coverage"]
    # The evidence's age lives in the per-class freshness, where it belongs.
    assert reply.payload["signal_freshness_by_class"], "the evidence's age is still reported"
    assert reply.product.expires_at is not None


# =========================================================================
# PEW-G11 / PEW-G12 — `Q1`, worst factor, understandable BY FACTOR
# =========================================================================


def test_population_debt_is_the_sdk_per_factor_minimum(served: Mapping[str, Answer]) -> None:
    """The ruled law, and the product says which law it used.

    Declared product gate `PEW-G12` (`CP-SPEC-023` §F.4 `Q1`, ruled 2026-09-21).
    """
    debt = served["coverage"].payload["population_debt"]
    assert debt["rule"] == "per-factor-minimum"
    assert debt["rule_authority"] == "D-IMPL-104"
    for factor in ("freshness", "completeness", "semantic_consistency"):
        assert Decimal(debt[factor]) <= Decimal("1")


def test_population_debt_names_the_member_each_weak_factor_came_from(
    served: Mapping[str, Answer], modules: dict[str, Any],
) -> None:
    """Understandable BY FACTOR — a weak member cannot hide behind the aggregate.

    Declared product gate `PEW-G12` (`CP-SPEC-023` §F.4 `Q1`, ruled 2026-09-21).
    """
    reply = served["coverage"]
    debt = reply.payload["population_debt"]
    weakest = debt["weakest_by_factor"]
    served_leis = {row["lei"] for row in reply.payload["population"]}
    assert set(weakest) == {"freshness", "completeness", "semantic_consistency"}
    for factor, lei in weakest.items():
        assert lei in served_leis, f"the weakest member on {factor} is not in the population"
    # And the named member really is at the composed floor for that factor.
    projection = modules["projection"]
    factors = dict(projection.member_factors(_view_of(reply)))
    for factor, lei in weakest.items():
        assert getattr(factors[lei], factor) == Decimal(debt[factor]), (
            f"the member named weakest on {factor} is not the one at the floor"
        )


def _view_of(reply: Answer) -> Any:
    """The served product's own view is not retained; rebuild from the payload.

    `member_factors` needs a `GraphView`; the test re-derives the same factors
    from the served payload instead, so it checks the SERVED claim rather than
    re-running the projection.
    """

    class _Claim:
        def __init__(self, entity_class: str, attributes: Mapping[str, str]) -> None:
            self.entity_class, self.attributes = entity_class, attributes

    class _Record:
        def __init__(self, claim: Any) -> None:
            self.claim = claim

    class _View:
        def __init__(self, entities: list[Any]) -> None:
            self.entities, self.relationships = entities, []

    entities = [_Record(_Claim("member", row)) for row in reply.payload["population"]]
    entities += [
        _Record(_Claim(row["signal_class"], {"lei": row["lei"]}))
        for row in reply.payload["early_warning"]
    ]
    entities += [
        _Record(_Claim("facility", {"lei": row["lei"]}))
        for row in reply.payload["utilization"] if row["has_facility"] == "true"
    ]
    return _View(entities)


# =========================================================================
# PEW-G15 / PEW-G16 / PEW-G17 — the honest limbs
# =========================================================================


def test_an_undrawn_facility_is_distinguishable_from_an_unobserved_one(
    served: Mapping[str, Answer],
) -> None:
    """Zero utilization carries its drawdown count.

    Declared product gate `PEW-G15` (`CP-SPEC-023` §C.3 trap 3, §G.1).
    """
    rows = [r for r in served["coverage"].payload["utilization"] if r["has_facility"] == "true"]
    assert rows, "the book has facilities"
    for row in rows:
        assert row["drawdown_count"] != "", "every facility row states how many drawdowns it saw"
        if row["utilization_pct"] in ("0.00", "0"):
            assert row["drawdown_count"] == "0" or Decimal(row["drawn"]) == 0


def test_members_without_a_facility_remain_members(served: Mapping[str, Answer]) -> None:
    """Dropping them would make the book's utilization look like the whole book's.

    Declared product gate `PEW-G16` (`CP-SPEC-023` §C.3 trap 4, §G.1).
    """
    reply = served["coverage"]
    uncovered = [r for r in reply.payload["utilization"] if r["has_facility"] == "false"]
    assert uncovered, "this book has members with no facility"
    covered = {r["lei"] for r in reply.payload["utilization"] if r["has_facility"] == "true"}
    assert len(covered) < len(reply.payload["population"])
    assert int(reply.payload["book"]["facility_covered_count"]) == len(covered)
    assert any(f["finding"] == "members-without-a-facility" for f in reply.payload["findings"])


def test_zero_active_covenant_pressure_is_not_absent_history(
    served: Mapping[str, Answer],
) -> None:
    """The member is served with both numbers, never dropped for being quiet.

    Declared product gate `PEW-G17` (`CP-SPEC-023` §C.3 trap 2, ruled 2026-09-21).
    """
    history = served["credit"].payload["covenant_history"]
    assert history is not None, "the covenant member is present for the role that sees it"
    assert int(history["historical_breaches"]) > 0, "this book carries covenant history"
    assert int(history["active_breaches"]) == 0, "and none of it is currently active"
    assert int(history["cured_breaches"]) == int(history["historical_breaches"])
    assert history["breaches"], "each breach is served, not only counted"


# =========================================================================
# PEW-G18 — the CP-21 boundary
# =========================================================================


def test_concentration_uses_only_this_rungs_declared_threshold(
    served: Mapping[str, Answer],
) -> None:
    """CP-23 must not implement CP-21's regulatory large-exposure arithmetic.

    Declared product gate `PEW-G18` (`CP-SPEC-023` §C.3 trap 5, ruled 2026-09-21).
    """
    concentration = served["credit"].payload["concentration"]
    assert concentration["threshold_authority"] == "cp-23.severity-tiers"
    assert concentration["single_name_threshold_pct"] == str(
        TIERS["concentration"]["single_name_threshold_pct"])
    assert concentration["basis"] == "committed-exposure"

    # AND THE SOURCE SIDE: CP-21's inputs are named NOWHERE in this tree.
    forbidden = ("limit_definition", "bank_capital", "connection_basis")
    for module in ("acquisition.py", "deployment.py", "projection.py"):
        source = (EXAMPLE / module).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines()
            if not line.strip().startswith("#") and "`" not in line
        )
        for name in forbidden:
            assert name not in code, (
                f"{module} names `{name}`, which is CP-21's regulatory input (PEW-G18)"
            )
    vocabulary = (EXAMPLE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8")
    tables = yaml.safe_load(vocabulary)["declaration"]["relational"]["tables"]
    for name in forbidden:
        assert name not in tables.values(), f"the declared tables name `{name}` (PEW-G18)"


# =========================================================================
# PEW-G19 — replay and identity
# =========================================================================


def test_the_determination_replays_and_identity_holds(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path, served: Mapping[str, Answer],
) -> None:
    """Same book, instant and role hash the same; a different book does not.

    Declared product gate `PEW-G19` (`CP-SPEC-023` §D.5, §G.1).
    """
    again = answer(modules, tmp_path / "again", principal=COVERAGE)
    assert again.address == served["coverage"].address, "the same question is the same bytes"

    other = answer(modules, tmp_path / "other", book=OTHER_BOOK, principal=COVERAGE)
    assert other.address != served["coverage"].address, "a different book is a different product"

    record = served["coverage"].record
    assert record.content_generation_path.product_content_address == served["coverage"].address
    assert record.perspective_conditioning.role == "coverage"
    assert record.content_generation_path.request.parameters["as_of"] == AS_OF


# =========================================================================
# PEW-G13 / PEW-G14 — the entitlement's cost, and what assembly touched
# =========================================================================


def test_a_member_the_role_excluded_still_counts_against_completeness(
    served: Mapping[str, Answer],
) -> None:
    """The book genuinely IS less complete for a role that may not see part of it.

    Saying otherwise would hide the cost of the entitlement rather than
    measure it (rungs 15 and 16, reused).

    Declared product gate `PEW-G13` (`CP-SPEC-023` §E.2, §G.1).
    """
    narrow = served["product"]     # facility-covered members only
    wide = served["coverage"]      # every member
    assert len(narrow.payload["population"]) < len(wide.payload["population"])
    # THE NARROWED ROLE IS PENALIZED FOR WHAT IT CANNOT SEE. Its completeness
    # carries the share of the book it was served, so the entitlement is not
    # free. (The two roles ask over different populations, so their totals are
    # not ordered — what the rule requires is that the exclusion is COUNTED.)
    assert narrow.payload["book"]["book_member_total"] == wide.payload["book"]["book_member_total"]
    assert int(narrow.payload["book"]["book_member_total"]) > len(narrow.payload["population"]), (
        "the narrowed role must still know how large the book actually is"
    )
    assert narrow.product.debt is not None and wide.product.debt is not None
    assert Decimal(str(narrow.product.debt.factors.completeness)) < Decimal("1"), (
        "a role that saw 14 of 25 members must not reach full completeness"
    )


def test_what_assembly_materialized_is_a_served_fact(served: Mapping[str, Answer]) -> None:
    """It tracks the population, not the estate.

    Declared product gate `PEW-G14` (`CP-SPEC-023` §D.3, §G.1).
    """
    reply = served["coverage"]
    materialized = int(reply.payload["book"]["records_materialized"])
    members = len(reply.payload["population"])
    assert materialized > 0, "the count is served"
    assert materialized >= members, "every member became at least one claim"
    # The estate holds 1,000 coverage rows over 40 books; one book's assembly
    # must not scale with the estate.
    assert materialized < 100 * members, (
        f"{materialized} records for {members} members; the count tracks the estate"
        f" rather than the population"
    )
