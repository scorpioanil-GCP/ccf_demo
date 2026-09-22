"""What `examples/cp-21-large-exposure` determines, and against which rules.

Sixteen of the twenty-one declared gates of `CP-SPEC-021` §G.1 execute here;
the gate's own positive controls live in `test_cp_21_sabotage.py`.

Every assertion is a RELATIONSHIP or an IDENTITY and never an estate count.
**Reads the curated estate, seeds nothing** (CLAUDE.md §9).

THE FOUR THINGS THIS RUNG EXISTS TO PROVE, and where each is proved:

1. the group is DERIVED, and `connection_basis` moves membership -> aggregate
   exposure -> headroom, end to end (`LEX-G02`, `LEX-G03`, `LEX-G04`);
2. the capital base is normalized at the acquisition boundary with a DECLARED
   factor, both figures survive, and the gate is on the REGULATORY CONSEQUENCE
   rather than on a constant (`LEX-G06`, `LEX-G07`);
3. a limit is a percentage of capital OR an absolute amount, selected from an
   effective-dated regime at the determination instant (`LEX-G05`, `LEX-G09`);
4. the freshness asymmetry is disclosed and never fused (`LEX-G14`).
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

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-21-large-exposure"

ESTATE_VARIABLES = (
    "CCF_CP_21_POSTGRES_DSN", "CCF_CP_21_POSTGRES_SCHEMA",
    "CCF_CP_21_FLUREE_URL", "CCF_CP_21_FLUREE_LEDGER",
    "CCF_CP_21_MONGO_URI", "CCF_CP_21_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]

ANCHOR: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]

BREACHING: dict[str, Any] = QUESTION["breaching_case"]
FITS: dict[str, Any] = QUESTION["fits_after_mitigation_case"]
CONTRAST: dict[str, Any] = QUESTION["basis_contrast"]

CREDIT_OFFICER = ("PRIN-CO-001", "credit-officer")
COMMITTEE = ("PRIN-CM-002", "committee")
EXAMINER = ("PRIN-EX-003", "examiner")


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-21 estate is not configured: {', '.join(missing)} unset"
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
    principal: tuple[str, str] = CREDIT_OFFICER, anchor: str = ANCHOR, intent: str = INTENT,
    proposal: Mapping[str, Any] | None = None, **params: Any,
) -> Any:
    deployment, produce = modules["deployment"], modules["produce"]
    with produce.product(scratch) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: AS_OF}
        parameters.update({k: v for k, v in params.items() if v is not None})
        if proposal is not None:
            parameters[deployment.PROPOSAL] = dict(proposal)
        asked = produce.large_exposure_question(
            opened, anchor=anchor, asked_at=ASKED_AT, intent=intent, freshness=FRESHNESS,
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


def limit_row(payload: Mapping[str, Any], limit_id: str, *, key: str = "without_proposal") -> Mapping[str, Any]:
    rows = [r for r in payload["evaluation"][key] if r["limit_id"] == limit_id]
    assert rows, f"no `{limit_id}` row in evaluation.{key}"
    return rows[0]


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Answer]:
    root = tmp_path_factory.mktemp("cp21")
    return {
        "breaching": answer(modules, root / "br", anchor=BREACHING["anchor"],
                            proposal=BREACHING["proposal"]),
        "committee": answer(modules, root / "cm", principal=COMMITTEE,
                            intent="committee-review", anchor=BREACHING["anchor"]),
        "examiner": answer(modules, root / "ex", principal=EXAMINER,
                           intent="supervisory-request", anchor=BREACHING["anchor"]),
    }


# =========================================================================
# LEX-G01 — the plan
# =========================================================================


def test_the_served_plan_matches_the_declaration_and_runs_policy_first(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `LEX-G01` (`CP-SPEC-021` §G.1).

    Asserted against THIS class's declaration, not a fixed four: the rung
    declares three keys and `LEX-F-03` records why the specification's fourth
    (Similarity) is not one of them.

    `lineage.operators_invoked` is a `frozenset` and carries no order, so the
    ORDER limb is asserted against replay dimension 5 — the ordered
    `content_generation_path.operator_plan` — which is where order lives.
    """
    declared = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    keys = list(declared["product_class"]["required_operator_keys"])
    served_product = served["breaching"]
    assert set(served_product.product.lineage.operators_invoked) == set(keys)

    plan = list(served_product.record.content_generation_path.operator_plan)
    assert plan, "replay dimension 5 carries no ordered operator plan"
    assert plan[0].startswith("policy."), f"Policy did not run first; the plan was {plan}"


# =========================================================================
# LEX-G02 / LEX-G03 / LEX-G04 — the DERIVED group and the formative basis
# =========================================================================


def test_the_group_is_derived_and_declares_the_basis_that_derived_it(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gates `LEX-G02` and `LEX-G03` (`CP-SPEC-021` §G.1)."""
    group = served["breaching"].payload["group"]
    assert group["derived"] == "true"
    assert group["connection_basis"] in QUESTION["connection_bases"]
    assert int(group["member_count"]) >= 1
    for member in served["breaching"].payload["members"]:
        assert member["in_group"] == "true"
        assert member["admitted_by"], "a member is served without saying what admitted it"


def test_the_connection_basis_moves_membership_exposure_and_headroom(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """THE WHOLE CAUSAL CHAIN, not merely that the parameter arrives.

    Declared product gate `LEX-G04` (`CP-SPEC-021` §B.3, ruled 2026-09-21).

    Asked WITHOUT mitigation, because with mitigation recognized this anchor's
    counted exposure is its drawn balance and both bases read zero there — a
    true fact about the estate that would make the last link of the chain
    untestable. The relationship asserted is the ORDERING, never a figure.
    """
    deployment = modules["deployment"]
    anchor = CONTRAST["anchor"]
    narrow = answer(modules, tmp_path / "control", anchor=anchor,
                    **{deployment.CONNECTION_BASIS: "control",
                       deployment.APPLY_MITIGATION: False})
    wide = answer(modules, tmp_path / "both", anchor=anchor,
                  **{deployment.CONNECTION_BASIS: "both",
                     deployment.APPLY_MITIGATION: False})

    # 1. MEMBERSHIP moves.
    narrow_members = int(narrow.payload["group"]["member_count"])
    wide_members = int(wide.payload["group"]["member_count"])
    assert wide_members > narrow_members, (
        "`both` admits control edges AND dependency edges, so it cannot serve fewer members"
    )
    # 2. therefore AGGREGATE EXPOSURE moves.
    narrow_total = Decimal(narrow.payload["aggregate_exposure"]["total_commitment"])
    wide_total = Decimal(wide.payload["aggregate_exposure"]["total_commitment"])
    assert wide_total > narrow_total
    # 3. therefore HEADROOM moves, and in the direction more exposure implies.
    limit_id = "regulatory-large-exposure"
    narrow_headroom = Decimal(limit_row(narrow.payload, limit_id)["headroom"])
    wide_headroom = Decimal(limit_row(wide.payload, limit_id)["headroom"])
    assert wide_headroom < narrow_headroom, (
        "a larger group consumed no more of the limit; the basis stopped being formative"
    )
    # 4. and the two determinations are DIFFERENT PRODUCTS.
    assert narrow.address != wide.address


def test_a_basis_outside_the_declared_domain_is_refused_not_narrowed(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Declared product gate `LEX-G03` (`D-IMPL-251`: constraints refuse).

    AND THE DOMAIN IS DECLARED IN ONE PLACE. `connection_basis` decides the
    answer, so its admissible set is a routing vocabulary and lives in
    `artifacts/source-vocabulary.yaml`, not in a tuple in code. The config's
    `argument_domains` states the same list because the SDK derives the
    caller-facing schema from there; asserting the two equal is what stops a
    domain widened in one place and honored in the other — which was measured
    happening, and is recorded as `LEX-F-07`.
    """
    deployment, acquisition = modules["deployment"], modules["acquisition"]
    declared = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    domain = declared["request_contract"]["argument_domains"]["connection_basis"]["members"]
    assert list(acquisition.connection_bases()) == list(domain), (
        "the acquisition seam and the request contract disagree about the admissible bases"
    )
    outcome = ask(modules, tmp_path, **{deployment.CONNECTION_BASIS: "vibes"})
    assert not isinstance(outcome, Answer), "an undeclared basis was served"


# =========================================================================
# LEX-G05 / LEX-G09 / LEX-G10 — the effective-dated regime and its rule form
# =========================================================================


def test_the_regime_in_force_at_the_instant_is_the_one_selected(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """A regime not yet in force at the instant is REFUSED, not substituted.

    Declared product gate `LEX-G05` (`CP-SPEC-021` §C.2, ruled 2026-09-21).

    `reg-o` begins 2026-01-01. At the pinned instant it is in force and serves;
    at the control instant it is not, and the same question over the same
    anchor is refused instead of quietly answered under a different regime.

    THE CONTROL INSTANT IS CHOSEN SO THE TEST CAN ONLY PASS FOR THIS REASON.
    An instant before 2023-06-30 has no capital base at all, so the product
    refuses there whatever the regime selector does — a test asked at such an
    instant goes green with the selector disabled, which was measured and is
    recorded as `LEX-F-06`. The companion assertion below is what closes it:
    at the SAME instant, `pra-2022` SERVES.
    """
    deployment = modules["deployment"]
    control = QUESTION["regime_effective_dating_control"]
    absolute = QUESTION["absolute_limit_regime"]

    now = answer(modules, tmp_path / "now", anchor=BREACHING["anchor"],
                 **{deployment.REGIME: absolute})
    assert now.payload["regime_in_force"]["regime_id"].endswith(absolute)

    before = ask(modules, tmp_path / "before", anchor=BREACHING["anchor"],
                 **{deployment.REGIME: control["not_yet_in_force"],
                    deployment.AS_OF: control["instant"]})
    assert not isinstance(before, Answer), (
        "a regime not yet effective at the determination instant was served anyway"
    )
    # AND THE INSTANT ITSELF IS SERVEABLE — so the refusal above is about the
    # regime, not about the instant.
    alongside = answer(modules, tmp_path / "alongside", anchor=BREACHING["anchor"],
                       **{deployment.REGIME: control["in_force"],
                          deployment.AS_OF: control["instant"]})
    assert alongside.payload["regime_in_force"]["regime_id"].endswith(control["in_force"])


def test_an_expired_regime_is_not_applied_to_a_later_determination(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """IN FORCE MEANS IN FORCE AT BOTH ENDS.

    Declared product gate `LEX-G05` (`CP-SPEC-021` §C.2). The estate's CRR
    version carries an `effectiveTo`; applying repealed law to a 2026
    determination is the failure this refuses.
    """
    deployment = modules["deployment"]
    expired = QUESTION["regime_not_in_force_at_asked_at"]
    outcome = ask(modules, tmp_path, anchor=BREACHING["anchor"],
                  **{deployment.REGIME: expired})
    assert not isinstance(outcome, Answer), "a repealed regime governed a later determination"


def test_the_alternate_rule_shape_is_expressible_and_named(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """An ABSOLUTE limit and a PERCENTAGE limit are both first-class.

    Declared product gate `LEX-G09` (`CP-SPEC-021` §C.2, ruled 2026-09-21).
    Regulation O's limit is an absolute amount; a product that assumed
    `percentage x capital` could not express it at all.
    """
    deployment = modules["deployment"]
    percentage = answer(modules, tmp_path / "pct", anchor=BREACHING["anchor"],
                        **{deployment.REGIME: QUESTION["default_regime"]})
    absolute = answer(modules, tmp_path / "abs", anchor=BREACHING["anchor"],
                      **{deployment.REGIME: QUESTION["absolute_limit_regime"]})

    assert percentage.payload["regime_in_force"]["rule_form"] == "percentage-of-capital"
    assert absolute.payload["regime_in_force"]["rule_form"] == "absolute-amount"
    # THE SHAPES ARE GENUINELY DIFFERENT: the percentage limit scales with the
    # capital base and the absolute one does not.
    capital = Decimal(percentage.payload["capital_base"]["normalized_value"])
    assert Decimal(percentage.payload["regime_in_force"]["limit_value"]) > capital / Decimal(100)
    assert Decimal(absolute.payload["regime_in_force"]["limit_value"]) < capital / Decimal(1000)


def test_the_determination_names_all_five_regime_facts(served: Mapping[str, Answer]) -> None:
    """Declared product gate `LEX-G10` (`CP-SPEC-021` §G.1)."""
    regime = served["breaching"].payload["regime_in_force"]
    for key in ("regime_id", "effective_from", "effective_basis", "rule_form",
                "limit_value", "authority"):
        assert regime.get(key), f"the determination states no {key!r}"


# =========================================================================
# LEX-G06 / LEX-G07 — THE UNITS GATE, on the regulatory consequence
# =========================================================================


def test_unit_provenance_survives_normalization(served: Mapping[str, Answer]) -> None:
    """Both figures, both units, and the arithmetic consumes the normalized one.

    Declared product gate `LEX-G07` (`Q2`, ruled 2026-09-21).
    """
    capital = served["breaching"].payload["capital_base"]
    for key in ("raw_value", "source_unit", "normalized_value", "normalized_unit",
                "unit_authority", "report_date", "age_days"):
        assert capital.get(key) not in (None, ""), f"`capital_base` drops {key!r}"
    assert capital["source_unit"] != capital["normalized_unit"]
    assert capital["consumed_by_arithmetic"] == "normalized_value"
    # The relationship, never the factor: the normalized figure is strictly
    # larger, because the source reports in thousands.
    assert Decimal(capital["normalized_value"]) > Decimal(capital["raw_value"])


def test_the_engineered_proposals_reproduce_the_estate_s_own_outcomes(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """THE UNITS GATE, AND IT IS ON THE REGULATORY CONSEQUENCE.

    Declared product gate `LEX-G06` (`Q2`, ruled 2026-09-21). NOT gated on a
    conversion constant: an implementation carrying the right factor and
    applying it wrongly still fails here, because what is asserted is that the
    estate's own `expected_outcome` labels come back out.

    The two engineered rows are written against DIFFERENT anchors, so each is
    asked on its own.
    """
    for case in (BREACHING, FITS):
        served = answer(modules, tmp_path / case["anchor"], anchor=case["anchor"],
                        proposal=case["proposal"])
        evaluation = served.payload["evaluation"]
        outcome = evaluation["regulatory_outcome"]
        expected = "breaches" if case["breaches_with_mitigation"] else "fits"
        assert outcome == expected, (
            f"{case['legal_name']} came out {outcome!r}; the estate labels that row"
            f" {case['expected_outcome']!r}"
        )


def test_the_dimensionally_wrong_reading_is_refused_by_consequence(
    served: Mapping[str, Answer],
) -> None:
    """THE NEGATIVE CONTROL for the units gate.

    Declared product gate `LEX-G06` (`CP-SPEC-021` §C.3 trap 1). A Tier 1
    reading of the raw figure gives a percentage limit three orders of
    magnitude below the exposures it is measured against — which is not a
    close call, it is dimensionally wrong, and the gate refuses it.
    """
    payload = served["breaching"].payload
    raw = Decimal(payload["capital_base"]["raw_value"])
    for row in payload["evaluation"]["without_proposal"]:
        if row["rule_form"] != "percentage-of-capital":
            continue
        assert Decimal(row["limit_value"]) > raw, (
            f"limit {row['limit_id']!r} evaluates below the RAW capital figure, which is what"
            f" an unnormalized implementation produces"
        )


# =========================================================================
# LEX-G08 / LEX-G20 — anchoring, and judgment kept distinguishable
# =========================================================================


def test_every_cited_provision_resolves_to_quoted_text_and_no_hash_is_minted(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `LEX-G08` (ruled 2026-09-21).

    These passages carry no `sha256` in this estate, so anchoring is proved by
    a resolvable authority, a resolvable passage and the rulebook's own words.
    A minted hash would look like provenance and prove nothing.
    """
    regime = served["breaching"].payload["regime_in_force"]
    assert regime["provisions"], "the regime cites nothing"
    assert int(regime["provisions_resolved"]) == int(regime["provisions_cited"])
    for provision in regime["provisions"]:
        assert provision["resolved"] == "true"
        assert provision["quoted_text"].strip()
        assert provision["hash_available"] == "false", (
            "a hash appeared where the estate carries none"
        )


def test_economic_dependency_members_carry_their_basis_and_provenance(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """A judgment stays distinguishable from a filing.

    Declared product gate `LEX-G20` (`CP-SPEC-021` §C.3).
    """
    deployment = modules["deployment"]
    served = answer(modules, tmp_path, anchor=CONTRAST["anchor"],
                    **{deployment.CONNECTION_BASIS: "both"})
    dependent = [m for m in served.payload["members"]
                 if m["admitted_by"] == "economic-dependency"]
    assert dependent, "the contrast anchor admitted no dependency members"
    for member in dependent:
        assert member["dependency_basis"], "a judgment edge states no basis"
        assert "synthetic" in member["dependency_provenance"], (
            "a judgment edge does not declare itself synthetic"
        )


# =========================================================================
# LEX-G11 / LEX-G12 / LEX-G13 / LEX-G15 — the limits and the counting
# =========================================================================


def test_both_internal_authorities_are_served_and_the_conflict_is_visible(
    served: Mapping[str, Answer],
) -> None:
    """NEITHER SOURCE IS PRESENTED AS WRONG, and the selecting rule is NAMED.

    Declared product gate `LEX-G11` (ruled 2026-09-21).
    """
    payload = served["breaching"].payload
    authorities = {row["authority"] for row in payload["limits"]}
    assert len(authorities) >= 2, f"only {authorities} served"
    conflict = payload["limit_authority_conflict"]
    assert conflict is not None, "the two authorities agree; the conflict has gone"
    assert len(conflict["authorities"]) >= 2
    assert conflict["selected_by_rule"], "one authority was chosen without naming the rule"
    # The CONSERVATIVE one binds, and that is what the named rule says.
    chosen = next(a for a in conflict["authorities"]
                  if a["authority"] == conflict["selected_authority"])
    assert all(Decimal(chosen["limit_pct_of_capital"]) <= Decimal(a["limit_pct_of_capital"])
               for a in conflict["authorities"])


def test_the_product_identifies_which_limit_binds_first(served: Mapping[str, Answer]) -> None:
    """NOT merely that some limit binds.

    Declared product gate `LEX-G12` (`CP-SPEC-021` §G.1).
    """
    evaluation = served["breaching"].payload["evaluation"]
    assert evaluation["binding_limit_id"]
    assert evaluation["binding_limit_authority"]
    binding = Decimal(evaluation["binding_limit_headroom"])
    for row in evaluation["without_proposal"]:
        assert Decimal(row["headroom"]) >= binding, (
            f"{row['limit_id']!r} has less headroom than the limit named as binding first"
        )


def test_each_limit_is_evaluated_under_its_own_counting_rules(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `LEX-G13` (`CP-SPEC-021` §G.1).

    Two limits over ONE group legitimately count two different exposures, and
    the product says which rules it applied to each.
    """
    payload = served["breaching"].payload
    registered = {row["limit_id"]: row for row in payload["limits"]
                  if row["authority"] == "relational-limit-register"}
    assert registered, "the relational register served no limit"
    for row in registered.values():
        assert row["counts_guarantees"] in ("true", "false")
        assert row["counts_undrawn"] in ("true", "false")
        assert row["connection_basis"]

    counted = {row["limit_id"]: row for row in payload["evaluation"]["without_proposal"]}
    excluding = [row for row in counted.values()
                 if "undrawn-excluded-by-counting-rule" in row["counting_rules_applied"]]
    assert excluding, "no limit exercised its own undrawn counting rule"


def test_mitigation_is_load_bearing(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The SAME group evaluates differently with and without it.

    Declared product gate `LEX-G15` (`CP-SPEC-021` §G.1). Measured on this
    estate, it is what turns the engineered $59.4bn proposal from a breach
    into a fit — so it is not a flag that travels, it is a flag that decides.
    """
    deployment = modules["deployment"]
    with_relief = answer(modules, tmp_path / "with", anchor=FITS["anchor"],
                         proposal=FITS["proposal"])
    without = answer(modules, tmp_path / "without", anchor=FITS["anchor"],
                     proposal=FITS["proposal"],
                     **{deployment.APPLY_MITIGATION: False})

    assert with_relief.payload["evaluation"]["mitigation_applied"] == "true"
    assert without.payload["evaluation"]["mitigation_applied"] == "false"
    limit_id = "regulatory-large-exposure"
    relieved = limit_row(with_relief.payload, limit_id, key="with_proposal")
    gross = limit_row(without.payload, limit_id, key="with_proposal")
    assert Decimal(relieved["exposure_counted"]) < Decimal(gross["exposure_counted"])
    assert relieved["breached"] == "false" and gross["breached"] == "true", (
        "mitigation did not change the outcome; the flag reached nothing that decides"
    )
    assert with_relief.address != without.address


# =========================================================================
# LEX-G14 — the freshness asymmetry, disclosed and never fused
# =========================================================================


def test_the_freshness_asymmetry_is_disclosed_and_not_resolved(
    served: Mapping[str, Answer],
) -> None:
    """FOUR PROHIBITIONS, and the disclosure that replaces them.

    Declared product gate `LEX-G14` (ruled 2026-09-21). The product does not
    pretend capital is intraday, does not age exposure to the capital date,
    does not refresh capital to the exposure instant, and mints no single
    fused timestamp.
    """
    payload = served["breaching"].payload
    asymmetry = payload["freshness_asymmetry"]
    assert asymmetry["exposure_cadence"] != asymmetry["capital_cadence"]
    assert asymmetry["resolved"] == "false"
    assert int(asymmetry["capital_age_days"]) > 0
    # The denominator's own date travels WITH the ratio, not beside it.
    assert asymmetry["capital_report_date"] == payload["capital_base"]["report_date"]
    assert asymmetry["exposure_instant"] != asymmetry["capital_report_date"]
    for forbidden in ("combined_freshness_at", "fused_as_of", "effective_freshness"):
        assert forbidden not in payload, f"a fused freshness key `{forbidden}` appeared"


# =========================================================================
# LEX-G16 / LEX-G17 / LEX-G19 — the proposal is an assumption
# =========================================================================


def test_the_proposal_is_computed_with_and_without_and_both_are_served(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `LEX-G16` (`CP-SPEC-021` §G.1)."""
    evaluation = served["breaching"].payload["evaluation"]
    assert evaluation["without_proposal"] and evaluation["with_proposal"]
    assert evaluation["proposal_basis"] == "assumption"
    limit_id = "regulatory-large-exposure"
    before = Decimal(limit_row(served["breaching"].payload, limit_id)["exposure_counted"])
    after = Decimal(limit_row(served["breaching"].payload, limit_id,
                              key="with_proposal")["exposure_counted"])
    assert after > before


def test_a_noncanonical_proposal_magnitude_is_refused_never_coerced(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Declared product gate `LEX-G17` (rung 24's `Q1`, carried).

    Rounding would produce a content address nobody could reproduce, so the
    fractional form is refused at the deployment's own seam with a diagnostic
    naming the parameter and its canonical unit.
    """
    acquisition = modules["acquisition"]
    with pytest.raises(acquisition.NoncanonicalMagnitude) as raised:
        acquisition.bind_proposal({"facility_type": "Term Loan",
                                   "commitment_usd": 75000000000.5,
                                   "obligor_lei": BREACHING["anchor"]})
    assert "commitment_usd" in str(raised.value)
    assert "INTEGER" in str(raised.value)


def test_an_undeclared_proposal_member_is_refused(
    estate: None, modules: dict[str, Any],
) -> None:
    """THE OBJECT IS CLOSED.

    Declared product gate `LEX-G17` (`CP-SPEC-021` §B.3).
    """
    acquisition = modules["acquisition"]
    with pytest.raises(ValueError, match="undeclared"):
        acquisition.bind_proposal({"commitment_usd": 1, "tenor_years": 5})


def test_two_proposals_over_one_instant_and_group_give_identical_debt(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """A HYPOTHETICAL IS NOT EVIDENCE.

    Declared product gate `LEX-G19` (rung 24's governing rule, carried). The
    proposal changes the determination and must not change Context Debt: debt
    measures the evidence that was observed, and a proposal was not observed.
    """
    anchor = BREACHING["anchor"]
    one = answer(modules, tmp_path / "one", anchor=anchor, proposal=BREACHING["proposal"])
    two = answer(modules, tmp_path / "two", anchor=anchor,
                 proposal={**dict(BREACHING["proposal"]), "commitment_usd": 1_000_000})

    assert one.payload["evaluation"]["proposal_commitment"] != \
        two.payload["evaluation"]["proposal_commitment"], "the two proposals did not differ"
    assert one.payload["population_debt"] == two.payload["population_debt"], (
        "a proposal moved Context Debt; the hypothetical became evidence"
    )
    assert one.address != two.address, "two different proposals hashed the same"


# =========================================================================
# LEX-G18 / LEX-G21 — the renderings and replay
# =========================================================================


def test_the_three_renderings_do_not_collapse(served: Mapping[str, Answer]) -> None:
    """Declared product gate `LEX-G18` (`CP-SPEC-021` §G.1)."""
    officer = set(served["breaching"].payload)
    committee = set(served["committee"].payload)
    examiner = set(served["examiner"].payload)
    assert officer != committee != examiner
    assert "methodology" in examiner and "replay_attribution" in examiner
    assert "methodology" not in committee and "replay_attribution" not in committee
    assert "concentration_view" in committee and "concentration_view" not in examiner
    assert served["examiner"].product.lineage.policy_bundle_versions, (
        "the examiner rendering carries no policy bundle version"
    )


def test_replay_reconstructs_the_determination_and_a_changed_input_does_not(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """SAME anchor, regime, basis, instant and proposal -> SAME bytes.

    Declared product gate `LEX-G21` (`CP-SPEC-021` §G.1). The ledger point is
    DISCLOSED rather than asserted: this estate exposes no route returning
    Fluree's `t` (`LEX-F-04`), and a minted one would make replay look
    reconstructible when it is not.
    """
    deployment = modules["deployment"]
    anchor = CONTRAST["anchor"]
    first = answer(modules, tmp_path / "a", anchor=anchor,
                   **{deployment.CONNECTION_BASIS: "both"})
    again = answer(modules, tmp_path / "b", anchor=anchor,
                   **{deployment.CONNECTION_BASIS: "both"})
    assert first.address == again.address, "one question over one instant served two answers"

    changed_basis = answer(modules, tmp_path / "c", anchor=anchor,
                           **{deployment.CONNECTION_BASIS: "control"})
    changed_regime = answer(modules, tmp_path / "d", anchor=anchor,
                            **{deployment.CONNECTION_BASIS: "both",
                               deployment.REGIME: QUESTION["absolute_limit_regime"]})
    assert changed_basis.address != first.address
    assert changed_regime.address != first.address

    anchor_member = first.payload["replay_attribution"] if "replay_attribution" in first.payload \
        else None
    if anchor_member is not None:  # pragma: no cover - the officer rendering omits it
        assert anchor_member["ledger_point_resolvable"] in ("true", "false")


def test_the_examiner_replay_anchor_discloses_an_unresolvable_ledger_point(
    served: Mapping[str, Answer],
) -> None:
    """Declared product gate `LEX-G21` (`LEX-F-04`, measured 2026-09-21)."""
    anchor = served["examiner"].payload["replay_attribution"]
    for key in ("plan_id", "regime_id", "connection_basis", "capital_report_date",
                "determination_instant"):
        assert anchor.get(key), f"the replay anchor names no {key!r}"
    assert anchor["ledger_point_resolvable"] in ("true", "false")
    if anchor["ledger_point_resolvable"] == "false":
        assert anchor["ledger_t"] == "unreported", "an unresolvable ledger point was minted"
