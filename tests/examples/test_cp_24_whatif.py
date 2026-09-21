"""What `examples/cp-24-portfolio-what-if` serves, and under which assumptions.

Thirteen of the seventeen declared gates of `CP-SPEC-024` §G.1 execute here;
the gate's own positive controls live in `test_cp_24_sabotage.py`.

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
EXAMPLE = REPO_ROOT / "examples" / "cp-24-portfolio-what-if"

ESTATE_VARIABLES = (
    "CCF_CP_24_POSTGRES_DSN", "CCF_CP_24_POSTGRES_SCHEMA",
    "CCF_CP_24_FLUREE_URL", "CCF_CP_24_FLUREE_LEDGER",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SENSITIVITIES: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "sensitivities.yaml").read_text(encoding="utf-8"))["declaration"]

BOOK: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
SCENARIO: dict[str, Any] = dict(QUESTION["scenario"])
ALTERNATE: dict[str, Any] = dict(QUESTION["alternate_scenario"])
STRESSED_CLASS: str = QUESTION["stressed_class"]

COVERAGE = ("PRIN-PM-001", "coverage")
CREDIT = ("PRIN-CO-002", "credit")
PRODUCT = ("PRIN-PR-003", "product")


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-24 estate is not configured: {', '.join(missing)} unset"
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
    scenario: Mapping[str, Any] | None = None, members: list[str] | None = None,
    **params: Any,
) -> Any:
    deployment, produce = modules["deployment"], modules["produce"]
    with produce.product(scratch) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: AS_OF}
        parameters.update({k: v for k, v in params.items() if v is not None})
        asked = produce.book_question(
            opened, book=book, asked_at=ASKED_AT, intent=intent, freshness=FRESHNESS,
            members=members, scenario=dict(SCENARIO if scenario is None else scenario),
            **parameters,
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
    root = tmp_path_factory.mktemp("cp24")
    return {
        "coverage": answer(modules, root / "cov", principal=COVERAGE),
        "credit": answer(modules, root / "cre", principal=CREDIT, intent="credit-review"),
        "alternate": answer(modules, root / "alt", principal=CREDIT, intent="credit-review",
                            scenario=ALTERNATE),
    }


# =========================================================================
# WIF-G01 / WIF-G02 / WIF-G03 — the plan and the closed object
# =========================================================================


def test_the_served_plan_matches_the_declaration_and_runs_policy_first(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G01` (`CP-SPEC-024` §G.1)."""
    declared = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    keys = set(declared["product_class"]["required_operator_keys"])
    for reply in served.values():
        assert set(reply.product.lineage.operators_invoked) == keys
        plan = reply.record.content_generation_path.operator_plan
        assert plan.index("policy.principal-subgraph") == 0, f"Policy runs first; executed {plan}"


def test_the_scenario_object_is_closed(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """An undeclared member is refused, and a third level is not expressible.

    Declared product gate `WIF-G02` (`CP-SPEC-024` §B.4, ruled 2026-09-21).
    """
    outcome = ask(modules, tmp_path / "a", scenario={**SCENARIO, "bogus_member": 1})
    assert not isinstance(outcome, Answer), "an undeclared scenario member is never served"
    assert outcome.kind == "product-request-violation"
    assert outcome.reason == "undeclared-parameter"

    # THE ONE-LEVEL CEILING IS STRUCTURAL, not a rule this deployment enforces:
    # the SDK's member type carries neither `properties` nor `items`, so a
    # third level cannot be declared at all.
    from ccf.skills.catalog import SkillArgumentMember  # noqa: PLC0415

    fields = set(SkillArgumentMember.model_fields)
    assert "properties" not in fields and "items" not in fields, (
        "a scenario member must not be able to declare a further level"
    )


def test_a_magnitude_outside_its_declared_bounds_is_refused(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Declared product gate `WIF-G03` (`CP-SPEC-024` §B.4, §G.1)."""
    bounds = SENSITIVITIES["bounds"]["rate_shift_bp"]
    too_big = int(bounds["maximum"]) + 1
    outcome = ask(modules, tmp_path / "b", scenario={**SCENARIO, "rate_shift_bp": too_big})
    assert not isinstance(outcome, Answer), "a magnitude outside the declared domain is refused"
    # And a magnitude INSIDE the domain is served, so the gate is not vacuous.
    assert isinstance(
        ask(modules, tmp_path / "c", scenario={**SCENARIO, "rate_shift_bp": int(bounds["maximum"])}),
        Answer,
    )


# =========================================================================
# WIF-G04 — a noncanonical form is REFUSED, never coerced
# =========================================================================


def test_a_noncanonical_fractional_magnitude_is_refused_never_coerced(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Ruled 2026-09-21: refused, not coerced. No rounding, ever.

    The refusal is a RAISE rather than a governed envelope, because request
    canonicalization runs before the request contract is consulted — the
    `D-IMPL-304` residual shape, recorded as `WIF-F-02` and not repaired here.
    What the gate proves is the part that is ruled: it is **refused**, and no
    coerced or rounded value is ever served.

    Declared product gate `WIF-G04` (`CP-SPEC-024` §B.4, `Q1`).
    """
    acquisition = modules["acquisition"]
    with pytest.raises(acquisition.NoncanonicalMagnitude) as refusal:
        ask(modules, tmp_path / "f", scenario={**SCENARIO, "rate_shift_bp": 0.015})
    assert "basis points" in str(refusal.value), "the refusal names the canonical unit"

    # AND NOTHING IS ROUNDED: the equivalent-looking integer is a DIFFERENT
    # question, not the same one recovered.
    integral = answer(modules, tmp_path / "g", scenario={**SCENARIO, "rate_shift_bp": 150})
    assert integral.payload["scenario"]["rate_shift_bp"] == "150"

    # The SDK's own refusal is the backstop, and it refuses too.
    from ccf.contracts.canonical import CanonicalizationError, canonical_bytes  # noqa: PLC0415
    from ccf.products.request import ProductRequest  # noqa: PLC0415

    with pytest.raises(CanonicalizationError):
        canonical_bytes(ProductRequest(
            schema_name="x.y", schema_version="1.0.0", subject="B", intent="i",
            freshness="event-driven", asked_at=ASKED_AT, parameters={"s": {"v": 0.015}},
        ))


# =========================================================================
# WIF-G06 / WIF-G07 / WIF-G08 — the fact/hypothetical separation
# =========================================================================


def test_no_claim_carries_a_scenario_magnitude(
    served: Mapping[str, Answer], modules: dict[str, Any],
) -> None:
    """THE GOVERNING RULE's first consequence: assumptions never enter the fabric.

    Declared product gate `WIF-G06` (`CP-SPEC-024` §D.3, ruled 2026-09-21).
    """
    # Nothing in the acquisition path may mint a scenario magnitude as a claim.
    source = (EXAMPLE / "acquisition.py").read_text(encoding="utf-8")
    body = source.split("def _members(")[1]
    for forbidden in ("rate_shift_bp", "collateral_shift_bp"):
        assert forbidden not in body, (
            f"a record builder names `{forbidden}`; a scenario magnitude must never become a claim"
        )
    # And the served evidence classes carry no scenario key.
    reply = served["credit"]
    for member in reply.payload["population"]:
        assert "rate_shift_bp" not in member and "collateral_shift_bp" not in member
    for item in reply.payload["collateral_impact"]:
        # The DERIVED member may name the assumption it used — that is the
        # labelling — but the OBSERVED fields must be the estate's own.
        assert item["observed_valuation"] and item["observed_at"]


def test_the_assumptions_are_labelled_and_every_derived_measure_names_one(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G07` (`CP-SPEC-024` §D.3, ruled 2026-09-21)."""
    reply = served["credit"]
    scenario = reply.payload["scenario"]
    assert scenario["basis"] == "assumption", "the assumptions say they are assumptions"
    assert scenario["units"] == "basis_points"
    assert "no source lineage" in scenario["note"]

    for member in ("interest_impact", "collateral_impact"):
        rows = reply.payload[member]
        assert rows, f"`{member}` is not vacuous"
        for row in rows:
            assert row["basis"] == "scenario", f"{member} carries an unlabelled measure"
            assert row["from_assumption"], f"{member} carries a measure naming no assumption"


def test_every_stressed_figure_is_served_beside_its_observed_one(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G08` (`CP-SPEC-024` §D.3, ruled 2026-09-21)."""
    reply = served["credit"]
    for row in reply.payload["interest_impact"]:
        assert row["observed_rate_pct"] and row["shifted_rate_pct"]
        assert Decimal(row["shifted_rate_pct"]) != Decimal(row["observed_rate_pct"]), (
            "a nonzero shift must move the rate, or the limb demonstrates nothing"
        )
    for row in reply.payload["collateral_impact"]:
        assert row["observed_valuation"] and row["stressed_valuation"]

    observed = reply.payload["observed_state"]
    assert observed["basis"] == "observed"
    assert observed["base_rate_observed_at"], "the observed rate states when it was observed"


def test_the_base_rate_is_observed_and_the_shifted_rate_is_derived(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G09` (`CP-SPEC-024` §C.3 trap 1, §G.1)."""
    reply = served["credit"]
    observed = reply.payload["observed_state"]
    base = Decimal(observed["base_rate_pct"])
    shift_bp = Decimal(reply.payload["scenario"]["rate_shift_bp"])
    expected = base + shift_bp * Decimal(str(SENSITIVITIES["basis_point"])) * Decimal(100)
    for row in reply.payload["interest_impact"]:
        assert Decimal(row["shifted_rate_pct"]) == expected, (
            "the shifted rate is the observed base plus the stated shift, and nothing else"
        )


# =========================================================================
# WIF-G10 / WIF-G11 / WIF-G12 — the shift's reach, and stale-stays-stale
# =========================================================================


def test_the_collateral_shift_applies_only_to_the_named_class(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G10` (`CP-SPEC-024` §G.1)."""
    rows = served["credit"].payload["collateral_impact"]
    shifted = [r for r in rows if r["category"] == STRESSED_CLASS]
    others = [r for r in rows if r["category"] != STRESSED_CLASS]
    assert shifted and others, "the book carries both the stressed class and others"
    for row in shifted:
        assert row["shift_applied"] == "true"
        assert Decimal(row["stressed_valuation"]) != Decimal(row["observed_valuation"])
    for row in others:
        assert row["shift_applied"] == "false"
        assert Decimal(row["stressed_valuation"]) == Decimal(row["observed_valuation"]), (
            "a class the scenario did not name is not moved"
        )


def test_a_stressed_stale_valuation_is_still_stale(served: Mapping[str, Answer]) -> None:
    """LOAD-BEARING: a scenario does not refresh its factual inputs.

    Declared product gate `WIF-G11` (`CP-SPEC-024` §C.3 trap 2, ruled 2026-09-21).
    """
    rows = served["credit"].payload["collateral_impact"]
    stale = [r for r in rows if int(r["observed_age_days"]) > 180]
    assert stale, "this book carries stale collateral, or the gate proves nothing"
    for row in stale:
        assert row["observed_at"], "the observation's instant travels with the derived figure"
        assert int(row["observed_age_days"]) > 180, "and so does its age"
    assert any(
        f["finding"] == "stressed-stale-valuations" for f in served["credit"].payload["findings"]
    ), "stressing stale evidence is a named finding, not a silent one"


def test_arithmetic_resets_no_observed_instant(served: Mapping[str, Answer]) -> None:
    """Nothing — instant, age, TTL or debt — moves because a calculation ran.

    Declared product gate `WIF-G12` (`CP-SPEC-024` §C.3 trap 2, ruled 2026-09-21).
    """
    reply = served["credit"]
    for row in reply.payload["collateral_impact"]:
        assert row["valuation_instant_used"] == row["observed_at"], (
            "the instant used by the arithmetic is the observation's own"
        )
    # And the alternate scenario, which stresses HARDER, moves no instant.
    alternate = {r["asset_id"]: r for r in served["alternate"].payload["collateral_impact"]}
    for row in reply.payload["collateral_impact"]:
        twin = alternate[row["asset_id"]]
        assert twin["observed_at"] == row["observed_at"]
        assert twin["observed_age_days"] == row["observed_age_days"]
        assert twin["observed_valuation"] == row["observed_valuation"]


# =========================================================================
# WIF-G13 — THE GOVERNING RULE, proved directly
# =========================================================================


def test_context_debt_is_unchanged_when_only_the_scenario_changes(
    served: Mapping[str, Answer],
) -> None:
    """Observed evidence determines debt. Assumptions never do.

    Declared product gate `WIF-G13` (`CP-SPEC-024` §D.3, ruled 2026-09-21).
    """
    base, alternate = served["credit"], served["alternate"]
    assert base.payload["scenario"] != alternate.payload["scenario"], (
        "the two scenarios must actually differ, or the gate is vacuous"
    )
    assert base.product.debt is not None and alternate.product.debt is not None
    assert base.product.debt.debt == alternate.product.debt.debt, (
        "two scenarios over one instant and population must give identical Context Debt"
    )
    assert base.payload["population_debt"] == alternate.payload["population_debt"]
    # And the derived measures DID move, so the two products are not identical.
    assert base.payload["collateral_impact"] != alternate.payload["collateral_impact"]


# =========================================================================
# WIF-G14 / WIF-G17 — the roll-up, and the CP-21 boundary
# =========================================================================


def test_the_coverage_rollup_names_which_members_cross_the_floor(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G14` (`CP-SPEC-024` §B.2, §G.1)."""
    rollup = served["credit"].payload["coverage_rollup"]
    assert rollup["basis"] == "scenario"
    assert int(rollup["members_evaluated"]) > 0
    named = set(rollup["below_floor_leis"])
    counted = int(rollup["members_below_floor"])
    assert len(named) == counted, "the names and the count agree"
    flagged = {r["lei"] for r in rollup["members"] if r["below_floor"] == "true"}
    assert flagged == named, "every member counted below the floor is named"


def test_cp21_regulatory_inputs_are_named_nowhere(served: Mapping[str, Answer]) -> None:
    """The CP-23 boundary, preserved.

    Declared product gate `WIF-G17` (`CP-SPEC-024` §C.3 trap 4, ruled 2026-09-21).
    """
    forbidden = ("limit_definition", "bank_capital", "connection_basis")
    for module in ("acquisition.py", "deployment.py", "projection.py"):
        source = (EXAMPLE / module).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines()
            if not line.strip().startswith("#") and "`" not in line
        )
        for name in forbidden:
            assert name not in code, f"{module} names `{name}`, which is CP-21's input (WIF-G17)"
    tables = yaml.safe_load(
        (EXAMPLE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8")
    )["declaration"]["relational"]["tables"]
    for name in forbidden:
        assert name not in tables.values()


# =========================================================================
# WIF-G15 / WIF-G16 — replay, and scenario identity
# =========================================================================


def test_the_same_canonical_assumptions_replay_to_the_same_address(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path, served: Mapping[str, Answer],
) -> None:
    """Declared product gate `WIF-G15` (`CP-SPEC-024` §D.5, ruled 2026-09-21)."""
    again = answer(modules, tmp_path / "again", principal=CREDIT, intent="credit-review")
    assert again.address == served["credit"].address

    record = served["credit"].record
    assert record.content_generation_path.product_content_address == served["credit"].address
    # THE ASSUMPTIONS ARE IN THE EFFECTIVE REQUEST — replay evidence, not a claim.
    recorded = record.content_generation_path.request.parameters["scenario"]
    assert int(recorded["rate_shift_bp"]) == int(SCENARIO["rate_shift_bp"])


def test_a_changed_assumption_is_a_changed_determination(
    served: Mapping[str, Answer],
) -> None:
    """So `WIF-G15` cannot be met by ignoring the scenario.

    Declared product gate `WIF-G16` (`CP-SPEC-024` §D.5, ruled 2026-09-21).
    """
    assert served["credit"].address != served["alternate"].address, (
        "a changed assumption must be a changed determination"
    )
