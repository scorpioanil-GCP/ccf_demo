"""cp-10 — `RSM-G01` … `RSM-G24`, against the live estate through the served product.

**Every gate here tests `CP-SPEC-010`, not this estate.** The assertions are
relationships and identities: an ordering, a ratio against a subject's own
baseline, a set difference, a class name. The estate grows, and a gate pinning
`498 observations` would go wrong the day another quote lands without anything
about the contract having changed. Where a number IS the governed claim — the
three §D.4 scenarios, whose figures the specification declares — it is pinned
to a TOLERANCE and to an ORDERING, never to an exact value.

**Four disciplines this module holds, each because collapsing it would let a
gate pass for the wrong reason:**

* **The instrument is the observation unit.** A bond is what trades; the
  obligor-level figure is a derived summary. Detection happens per bond against
  that bond's OWN median, and `CP10-F-06` is the record of what averaging first
  costs — the anchor's peak halved and a term-structure signal erased.
* **Freshness reads the leading edge of each series** (`D-IMPL-333`,
  `CP10-F-07`). Years of daily quotes are evidence, not staleness; `F` ranges
  over the newest quote per bond at or before `as_of`, and the grade in force.
* **Three components, never summed.** The headline spread is the sum a naive
  product reports, and §A.1 is the record of what reporting it costs.
* **A confirmation is three separate tests.** Later, a downgrade, AND
  off-cycle. Temporal proximity alone is not confirmation — quarterly reviews
  land every ~90 days, so some review is near any date (TRAP 2).
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
import tempfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-10-rating-and-spread-migration"

ESTATE_VARIABLES = (
    "CCF_CP_10_FLUREE_URL",
    "CCF_CP_10_FLUREE_LEDGER",
    "CCF_CP_10_POSTGRES_DSN",
    "CCF_CP_10_POSTGRES_SCHEMA",
)

#: Module names this example shares with its siblings. Popped around the import
#: so a sibling's `deployment` already in `sys.modules` cannot answer here.
COLLIDING = ("acquisition", "deployment", "produce", "projection", "run")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.fluree,
    pytest.mark.skipif(
        any(not os.environ.get(name) for name in ESTATE_VARIABLES),
        reason=(
            "cp-10 assembles from the live estate; set "
            + ", ".join(ESTATE_VARIABLES)
            + " — the v2 namespaces, never the v1 names in the estate's own .env"
        ),
    ),
]

# --- the three scenarios `CP-SPEC-010` §D.4 declares ----------------------
#
# Each is pinned because it IS the scenario. The FIGURES are asserted as
# orderings and as multiples of a subject's own baseline, never as exact
# basis points — the estate may gain a quote, and a peak pinned to three
# decimal places would make this module a fixture again.

#: Scenario 1 — the confirmation. Celanese Corp.
ANCHOR = "549300FHJQTDPPN41627"
#: Its 5-year bond, where the episode is. The peak is here and nowhere else.
ANCHOR_BOND = "syn-i-b23153"
#: Its 25-year sibling, which reaches ~1.3x its own median on the SAME day and
#: produces NO episode. The sibling is part of the scenario, not a footnote.
SIBLING_BOND = "syn-i-f87e69"
#: The day the 5-year peaks, and the day the downgrade takes effect.
PEAK_DATE = "2024-12-11"
DOWNGRADE_DATE = "2025-03-17"

#: Scenario 2 — a standing disagreement. Sabre Corp: a bond seven times its own
#: median, and a grade that never moved.
STANDING = "529900VKCYZW8GZ4WW58"
STANDING_BOND = "syn-i-4d322a"

#: Scenario 3 — the market move that is not a deterioration. B&G Foods over a
#: window in which EVERY band widened together.
MARKET_MOVE = "549300TRW1LZMDJZAQ78"
MARKET_MOVE_AS_OF = datetime.fromisoformat("2025-04-07T00:00:00+00:00")
MARKET_MOVE_WINDOW_DAYS = 48

#: The window's end for the two full-window scenarios.
AS_OF = datetime.fromisoformat("2026-08-20T00:00:00+00:00")

#: The threshold, as a multiple of each bond's OWN median.
MULTIPLE = "2.0"

#: The basis every spread figure names. `CP10-F-04` is why it cannot be
#: improved without making the market leg a function of the grade.
BASIS = "static_issue_band"

#: **An obligor that has LEFT its issue band** — measured, 2 of the 30 rated
#: obligors have, and this is the §A.3 divergence case: bonds issued into
#: `BBB`, now graded `BB+`, whose band is `BB`. `RSM-G23` needs it, because on
#: a subject still in its issue band the grade-derived band and the instrument
#: band are the SAME VALUE — and a gate asserted only there passes under the
#: very contamination it exists to refuse. Measured 2026-09-12.
MIGRATED = "5493004HBTOTE9DI9P12"
MIGRATED_ISSUE_BAND = "BBB"
MIGRATED_GRADE_BAND = "BB"

#: Names that may never appear in a payload. The licensing boundary is a
#: presentation boundary too: this product consumes no agency rating, and a
#: payload naming one would misrepresent its own evidence even if every number
#: in it were internal.
FORBIDDEN = ("S&P", "Moody", "Fitch", "TRACE")


@pytest.fixture(scope="module")
def example() -> Iterator[Any]:
    """This example's own modules, whatever ran before."""
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(EXAMPLE))
    try:
        modules = {
            name: importlib.import_module(name)
            for name in ("acquisition", "deployment", "produce", "projection")
        }
        assert pathlib.Path(modules["deployment"].__file__).parent == EXAMPLE
        yield modules
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


class _Frozen:
    """One outcome plus every artifact it wrote, read before the scratch dies.

    Wraps a serve AND a refusal. The two expose different surfaces — only a
    serve has a `payload` — and the wrapper must not paper over that by
    synthesizing an empty one.
    """

    def __init__(self, outcome: Any, *, scratch: pathlib.Path) -> None:
        self.outcome = outcome
        self.artifacts = [
            path.read_text(errors="ignore")
            for path in (scratch / "artifact-store").rglob("*")
            if path.is_file()
        ]
        if hasattr(outcome, "product"):
            self.product = outcome.product
            self.estate = outcome.estate
            self.record = outcome.record
            self.payload = outcome.product.payload

    def model_dump_json(self) -> str:
        """The DISCLOSED envelope, for the suppression gates."""
        return self.outcome.model_dump_json()


def serve(example: Any, *, anchor_lei: str = ANCHOR, asked_at: datetime = AS_OF,
          **kwargs: Any) -> Any:
    """One question, end to end. Returns the `Assembled` or the refusal."""
    deployment, produce = example["deployment"], example["produce"]
    kwargs.setdefault("divergence_multiple", MULTIPLE)
    kwargs.setdefault("debt_tolerance", "0.60")
    asked = deployment.request(
        anchor_lei=anchor_lei, asked_at=asked_at, **kwargs
    )
    with tempfile.TemporaryDirectory(prefix="cp-10-test-") as scratch:
        outcome = produce.assemble_and_serve(
            asked=asked, root=pathlib.Path(scratch)
        )
        return _Frozen(outcome, scratch=pathlib.Path(scratch))


@pytest.fixture(scope="module")
def confirmation(example: Any) -> Any:
    """Scenario 1 — the market moved and the credit file followed."""
    return serve(example)


@pytest.fixture(scope="module")
def standing(example: Any) -> Any:
    """Scenario 2 — a bond 7x its own median against a grade that never moved."""
    return serve(example, anchor_lei=STANDING)


@pytest.fixture(scope="module")
def migrated(example: Any) -> Any:
    """An obligor whose grade has left the band its bonds were issued into."""
    return serve(example, anchor_lei=MIGRATED)


@pytest.fixture(scope="module")
def market_move(example: Any) -> Any:
    """Scenario 3 — every band widened; this obligor did not deteriorate."""
    return serve(
        example, anchor_lei=MARKET_MOVE, asked_at=MARKET_MOVE_AS_OF,
        window_days=MARKET_MOVE_WINDOW_DAYS, granularity="daily",
    )


def _series_for(frozen: Any, instrument_id: str) -> Any:
    for series in frozen.payload["spread_series"]:
        if series["instrument_id"] == instrument_id:
            return series
    raise AssertionError(
        f"{instrument_id!r} is absent from the payload; the scenario this gate"
        f" rests on is not exercised"
    )


def _episode_for(frozen: Any, instrument_id: str) -> Any | None:
    for episode in frozen.payload["episodes"]:
        if episode["instrument_id"] == instrument_id:
            return episode
    return None


# =========================================================================
# The six universal gates.
# =========================================================================


def test_rsm_g01_the_operator_plan_is_never_empty(confirmation: Any) -> None:
    """`RSM-G01` — a plan with zero operator steps never serves.

    §G.1. The served product's lineage names the operators that produced it,
    and an empty set would mean a payload assembled by nothing.
    """
    assert confirmation.product.lineage.operators_invoked, (
        "the product served with an empty operator set"
    )


def test_rsm_g02_lineage_is_exactly_the_declared_operator_set(
    confirmation: Any, example: Any
) -> None:
    """`RSM-G02` — served lineage equals the plan's typed operator references.

    §G.1, and the second half is `ProductLineage`'s own shape: **exactly three
    fields.** A lineage that grew a fourth would be carrying something the
    replay contract does not resolve.
    """
    declared = set(
        example["deployment"].config()["product_class"]["required_operator_keys"]
    )
    assert set(confirmation.product.lineage.operators_invoked) == declared
    assert set(type(confirmation.product.lineage).model_fields) == {
        "operators_invoked", "policy_bundle_versions", "graph_snapshot_at",
    }


def test_rsm_g03_expiry_derives_from_the_decision_instant(
    confirmation: Any, example: Any
) -> None:
    """`RSM-G03` — `expires_at` derives from the decision instant, under the ceiling.

    §G.1. `ttl_anchor: from_decision`, so the expiry is `asked_at` plus the
    product TTL and never a clock read at serve time — which is what makes a
    request pinned to a past `as_of` a forensic reconstruction rather than a
    stale answer (§E.3).
    """
    product = confirmation.product
    assert product.ttl_anchor == "from_decision"
    assert product.expires_at > AS_OF, "the product expired before it was asked for"
    elapsed = (product.expires_at - AS_OF).total_seconds()
    scenario = example["deployment"].MigrationScenario
    ceiling = scenario.__dict__.get("max_ttl_seconds")
    assert 0 < elapsed <= 86400, (
        f"expiry is {elapsed}s after the decision instant; §E.3's ceiling is"
        f" one day — the fastest series' own cadence"
    )
    assert ceiling is None or elapsed <= 86400


def test_rsm_g04_debt_above_tolerance_refuses_with_the_debt_block(
    example: Any
) -> None:
    """`RSM-G04` — `D_c` above the caller's tolerance refuses rather than serving.

    §G.1. Asserted by asking the SAME question with a tolerance BELOW the debt
    the product actually carries, so the refusal is forced by the gate and not
    by a broken estate read: the serve above measures `D_c`, and this asks with
    a ceiling under it.
    """
    served = serve(example, debt_tolerance="0.60")
    measured = served.product.debt.debt
    impossible = (measured / 2).quantize(Decimal("0.0001"))
    refused = serve(example, debt_tolerance=str(impossible))
    assert not hasattr(refused, "payload"), (
        f"D_c is {measured} and a tolerance of {impossible} still served;"
        " the debt gate is not reading the caller's ceiling"
    )
    body = refused.model_dump_json()
    assert "debt" in body.lower(), "the refusal does not carry the debt block"


def test_rsm_g05_a_withheld_obligor_leaves_no_count_or_marker(
    confirmation: Any, standing: Any
) -> None:
    """`RSM-G05` — suppression is silent; a withheld obligor leaves no trace.

    §G.1. **What withholds here is the policy operator**, which admits only the
    obligors the effective request names — so every other obligor in the estate
    is excluded from the subgraph this payload was built over. The gate is that
    the exclusion is SILENT: no name, no count, no placeholder. A marker saying
    *"29 obligors excluded"* discloses the fact of their existence, which is the
    thing being withheld.

    Asserted against a REAL second obligor rather than a made-up string:
    scenario 2's Sabre is in the estate, is not in scenario 1's admitted set,
    and must be invisible in scenario 1's payload — identity, instruments and
    count alike.
    """
    body = str(confirmation.payload)
    assert STANDING not in body, (
        "a non-admitted obligor's identity reached the payload; the policy"
        " operator is not scoping the subgraph"
    )
    for bond in (STANDING_BOND, _series_for(standing, STANDING_BOND)["instrument_id"]):
        assert bond not in body, (
            f"{bond!r} belongs to a non-admitted obligor and is in the payload"
        )
    for leak in ("withheld", "suppressed", "redacted", "excluded", "omitted"):
        assert leak not in body.lower(), (
            f"the payload says {leak!r}; a count or marker of what was withheld"
            " discloses the existence it is withholding"
        )
    # And no count of the population it was drawn from, which would be the
    # same disclosure arriving as arithmetic.
    assert confirmation.payload["obligor"]["lei"] == ANCHOR
    assert set(
        s["instrument_id"] for s in confirmation.payload["spread_series"]
    ) == {ANCHOR_BOND, SIBLING_BOND}


def test_rsm_g06_the_payload_classification_is_the_highest_contributing(
    confirmation: Any
) -> None:
    """`RSM-G06` — classification containment.

    §G.1. This product mixes public market data (FRED OAS series, Treasury
    benchmarks) with an INTERNAL credit grade, so the payload's classification
    is the internal one. Asserted structurally — the internal element is
    PRESENT in a payload the product served, so the product cannot be treating
    itself as public.
    """
    assert confirmation.payload["grade_series"], (
        "no internal grade reached the payload, so the mixed-classification"
        " premise this gate rests on is not exercised"
    )
    assert all(
        g["provenance"] == "synthetic — internal"
        for g in confirmation.payload["grade_series"]
    )


# =========================================================================
# The three signals, their clocks, and the disagreement between them.
# =========================================================================


def test_rsm_g07_the_three_components_are_served_separately(
    confirmation: Any
) -> None:
    """`RSM-G07` — three labeled components, never pre-summed.

    §G.1, and the counterfactual at §A.1 arriving as a gate. A product serving
    `spread_bp` alone would let a market-wide widening read as a deterioration,
    which is the error scenario 3 exists to catch.

    **The sum is asserted ABSENT, not merely the parts present.** A payload
    carrying all three components AND their total still hands a reader the
    number that destroys the signal.
    """
    for series in confirmation.payload["spread_series"]:
        for point in series["points"]:
            assert {"benchmark_bp", "market_oas_bp", "idiosyncratic_bp"} <= set(point)
            assert "spread_bp" not in point, (
                "a pre-summed total rides beside the components; the product's"
                " whole subject is which of the three moved"
            )
            assert "total_bp" not in point


def test_rsm_g08_divergence_is_computed_on_the_issuer_specific_component(
    confirmation: Any, market_move: Any
) -> None:
    """`RSM-G08` — every divergence figure is computed on `idiosyncratic_bp`.

    §G.1. Asserted against the ESTATE rather than against the payload's own
    arithmetic: in scenario 3 the headline moved +166.6 bp while the residual
    moved +1.5 bp, so a detector reading the headline would fire there. It does
    not — which is a stronger statement than any field name.
    """
    episode = _episode_for(confirmation, ANCHOR_BOND)
    assert episode is not None
    series = _series_for(confirmation, ANCHOR_BOND)
    peak = Decimal(episode["peak_idiosyncratic_bp"])
    idiosyncratic = [Decimal(p["idiosyncratic_bp"]) for p in series["points"]]
    assert peak >= max(idiosyncratic), (
        "the reported peak is not the maximum of the ISSUER-SPECIFIC series;"
        " it is being taken from some other component"
    )
    headlines = [
        Decimal(p["benchmark_bp"]) + Decimal(p["market_oas_bp"])
        + Decimal(p["idiosyncratic_bp"])
        for p in series["points"]
    ]
    assert peak < max(headlines), (
        "the reported peak equals the headline; the market component has not"
        " been netted out"
    )
    assert not market_move.payload["episodes"], (
        "scenario 3 produced an episode — a market-wide widening is being read"
        " as an issuer deterioration, which is the error this gate exists for"
    )


def test_rsm_g09_an_episode_is_detected_per_bond_against_its_own_median(
    confirmation: Any
) -> None:
    """`RSM-G09` — per bond, against **that bond's own** median. Never averaged.

    §G.1, TRAP 1 and TRAP 6. The two bonds' medians are ~29.0 and ~29.5 bp —
    normally indistinguishable — and on the SAME day one reaches ~8x its own
    median and the other ~1.3x. Averaging them before detection halves the
    peak and erases a term-structure signal (`CP10-F-06`).

    Three separate assertions, because each fails differently: the 5-year
    produces an episode, the 25-year does NOT, and the multiple is computed
    against the subject's own baseline rather than against the blend.
    """
    anchor = _episode_for(confirmation, ANCHOR_BOND)
    sibling = _episode_for(confirmation, SIBLING_BOND)
    assert anchor is not None, "the 5-year bond's episode was not detected"
    assert sibling is None, (
        "the 25-year sibling produced an episode; it reaches ~1.3x its own"
        " median and must not, or the detector is reading a pooled figure"
    )
    own_median = Decimal(anchor["own_median_bp"])
    blended = Decimal(
        confirmation.payload["obligor_spread_summary"][
            "blended_median_idiosyncratic_bp"
        ]
    )
    assert own_median != blended, (
        "the episode's baseline equals the obligor blend; detection is running"
        " on the derived summary rather than on the bond"
    )
    expected = (Decimal(anchor["peak_idiosyncratic_bp"]) / own_median)
    assert abs(Decimal(anchor["multiple_of_own_median"]) - expected) < Decimal("0.01")
    assert Decimal(anchor["multiple_of_own_median"]) > Decimal(MULTIPLE)


def test_rsm_g10_the_peak_reports_the_grade_in_force_on_that_date(
    confirmation: Any
) -> None:
    """`RSM-G10` — the grade in force AT THE PEAK, not the current grade.

    §G.1 and §D.3. The units are deliberately different: the spread prices a
    BOND, the grade assesses the OBLIGOR. Comparing a past move against a
    present grade is the error — at the peak the obligor was `BB`; by the
    window's end it is `BB-`, and reporting the latter would erase the very
    change the product exists to detect.
    """
    episode = _episode_for(confirmation, ANCHOR_BOND)
    assert episode is not None
    at_peak = episode["grade_in_force_at_peak"]
    current = confirmation.payload["grade_series"][-1]["grade"]
    assert episode["grade_evaluable"] is True
    assert at_peak != current, (
        f"the grade at the peak ({at_peak}) equals the current grade"
        f" ({current}); the product is reading the present rather than the"
        " moment it claims to report"
    )
    in_force_dates = [
        g["valid_from"] for g in confirmation.payload["grade_series"]
        if g["grade"] == at_peak and g["valid_from"] <= PEAK_DATE
    ]
    assert in_force_dates, (
        f"no assertion of {at_peak} took effect on or before {PEAK_DATE}"
    )


def test_rsm_g11_a_confirmation_asserts_all_three_tests_separately(
    confirmation: Any, standing: Any
) -> None:
    """`RSM-G11` — later, a downgrade, AND off-cycle. Each reported on its own.

    §G.1, TRAP 2. **Temporal proximity alone is not confirmation.** Quarterly
    reviews land every ~90 days, so SOME review is near any date — my own
    Gate-1 measurement found six "confirmations" this way where there is one.

    The negative half is scenario 2, and it is a distinct outcome rather than
    an absence: Sabre was rated at the peak and the grade never moved
    (`CP10-F-08`). A product returning the same answer there as for an unrated
    obligor cannot express its own §D.4.
    """
    episode = _episode_for(confirmation, ANCHOR_BOND)
    assert episode is not None
    verdict = episode["confirmation"]
    assert verdict["outcome"] == "changed"
    # THREE TESTS, READ SEPARATELY. `confirms` alone would not say which held.
    assert verdict["is_later"] is True
    assert verdict["is_downgrade"] is True
    assert verdict["is_off_cycle"] is True
    assert verdict["confirms"] is True
    assert verdict["effective"] == DOWNGRADE_DATE
    assert verdict["lag_days"] > 0

    unchanged = _episode_for(standing, STANDING_BOND)
    assert unchanged is not None, "scenario 2's episode was not detected"
    standing_verdict = unchanged["confirmation"]
    assert standing_verdict["outcome"] == "unchanged", (
        "a rated obligor whose grade never moved is being reported the same as"
        " an unrated one; the two are different answers (`CP10-F-08`)"
    )
    assert standing_verdict["confirms"] is False
    assert standing_verdict["grade_in_force_throughout"]
    assert standing_verdict["reviews_after_peak"] >= 1, (
        "the standing disagreement claims no later review at all, which would"
        " make it an absence of evidence rather than a disagreement"
    )


def test_rsm_g12_the_grade_series_is_resampled_never_interpolated(
    confirmation: Any, example: Any
) -> None:
    """`RSM-G12` — every served point is a point that actually occurred.

    §G.1. Interpolation across a grade change would invent intermediate grades
    that never existed. Asserted by set membership against the SOURCE: every
    grade in the payload appears in the estate read, and every spread date in
    the payload is a date the source actually carries.
    """
    real_grades = {str(g.grade) for g in confirmation.estate.grades}
    assert real_grades, "the estate read carried no grade at all"
    for grade in confirmation.payload["grade_series"]:
        assert str(grade["grade"]) in real_grades, (
            f"{grade['grade']!r} is in the payload and not in the source"
        )
    real_dates = {str(s.obs_date) for s in confirmation.estate.spreads}
    for series in confirmation.payload["spread_series"]:
        for point in series["points"]:
            assert point["obs_date"] in real_dates, (
                f"{point['obs_date']} is in the payload and not in the source;"
                " a resampler that invents a bucket midpoint has interpolated"
            )


def test_rsm_g13_both_clocks_are_served_and_are_distinguishable(
    confirmation: Any
) -> None:
    """`RSM-G13` — `validFrom` and `assertedAt` are both served, and differ.

    §G.1. When a grade took effect and when the system learned it are two
    different facts, and this estate's booking lag is 1-5 days. A payload
    carrying one of them, or carrying both with the same value everywhere, has
    collapsed the two clocks.
    """
    grades = confirmation.payload["grade_series"]
    assert grades
    for grade in grades:
        assert grade["valid_from"] and grade["asserted_at"]
        assert grade["booking_lag_days"] is not None

    # THE TWO INSTANTS THEMSELVES MUST DIFFER IN THE PAYLOAD, and this is the
    # assertion the gate's first draft lacked. It checked only that
    # `booking_lag_days` was positive — and `booking_lag_days` is derived from
    # the SOURCE record, so a payload serving `asserted_at = valid_from` left
    # the lag correct and the gate green. A sabotage collapsing the two clocks
    # passed. Read the served values, never a figure computed beside them.
    distinguishable = [
        g for g in grades if g["asserted_at"] != g["valid_from"]
    ]
    assert distinguishable, (
        "every assertion serves `asserted_at` equal to `valid_from`; the two"
        " clocks have been collapsed into one at the payload boundary"
    )
    for grade in distinguishable:
        expected = (
            date.fromisoformat(str(grade["asserted_at"]))
            - date.fromisoformat(str(grade["valid_from"]))
        ).days
        assert grade["booking_lag_days"] == expected, (
            "the reported booking lag does not equal the gap between the two"
            " served instants; it is being computed from something else"
        )
    lags = {g["booking_lag_days"] for g in grades}
    assert any(lag > 0 for lag in lags), (
        "every booking lag is zero; the two clocks are carrying one value"
    )


def test_rsm_g14_every_series_declares_its_own_cadence_and_window(
    confirmation: Any
) -> None:
    """`RSM-G14` — per series: native cadence, resampled cadence, window.

    §G.1. A single product-level freshness figure over a daily spread and a
    quarterly grade would be actively misleading — the spread between them is
    NINETY-FOLD, and that asymmetry is the rung's subject.
    """
    register = confirmation.payload["series_register"]
    assert register
    for row in register:
        assert {"series", "unit", "native_cadence", "resampled_cadence",
                "window_from", "window_to", "observations"} <= set(row)
    units = {row["unit"] for row in register}
    assert units == {"instrument", "obligor"}, (
        f"the register carries units {units}; the spread hangs off the BOND and"
        " the grade off the OBLIGOR, and flattening them would hide the"
        " asymmetry §D.3 makes structural"
    )
    cadences = {row["native_cadence"] for row in register}
    assert len(cadences) > 1, (
        "every series declares the same native cadence; the ninety-fold spread"
        " this product exists to preserve has been flattened"
    )


def test_rsm_g15_each_class_decays_against_its_own_lambda_and_valid_from(
    confirmation: Any, example: Any
) -> None:
    """`RSM-G15` — own λ_c, `valid-from` basis, and the LEADING EDGE of the series.

    §G.1 and §E.1.1. Three separate claims, and each was a defect before it was
    a gate:

    * **`decay_basis: valid-from`** (`D-IMPL-331`) — rung 9 measured a product
      reporting perfect freshness for two-year-old observations because it
      decayed against ingestion time.
    * **Separate classes** — one λ_c over both would price a daily quote and a
      quarterly grade identically.
    * **`freshness_over: leading-edge`** (`D-IMPL-333`, `CP10-F-07`) — the mean
      over 996 historical quotes drove `F` to 0.004750 and the product to
      `fail_closed` with a two-day-old newest quote. Now 2 observations enter
      `F`, one per bond.
    """
    table = example["deployment"].config()["half_life"]
    assert table["rsm_spread"]["decay_basis"] == "valid-from"
    assert table["rsm_grade"]["decay_basis"] == "valid-from"
    assert (
        table["rsm_spread"]["half_life_seconds"]
        != table["rsm_grade"]["half_life_seconds"]
    ), "both moving classes share one half-life; the asymmetry is gone"
    assert table["rsm_spread"]["freshness_over"] == "leading-edge"
    assert table["rsm_grade"]["freshness_over"] == "leading-edge"
    assert table["rsm_spread"]["series_key_attribute"] == "instrument_id", (
        "the spread's series key is not the bond; without it every bond's"
        " history collapses into one series, which reads as a working"
        " configuration and is not one"
    )
    # THE MEASURED CONSEQUENCE, not just the declaration. Hundreds of
    # observations reach the view; `F` is nonetheless a current-state figure.
    observations = sum(
        s["observations"] for s in confirmation.payload["spread_series"]
    )
    assert observations > 100, "the archive this gate is about is not present"
    assert confirmation.product.debt.factors.freshness > Decimal("0.1"), (
        "`F` reads as an archive-length figure rather than a current-state one;"
        " leading-edge freshness is declared but is not reaching the scorer"
    )


def test_rsm_g16_the_supersession_chain_is_served_and_points_forward(
    confirmation: Any
) -> None:
    """`RSM-G16` — every superseded grade points forward; a history is a chain.

    §G.1. A bitemporal history served as an unordered SET loses the thing that
    makes it a history. Each assertion carries its successor, and the chain's
    single open end is the grade in force now.
    """
    grades = confirmation.payload["grade_series"]
    assert len(grades) > 1, "a single assertion cannot exercise a chain"
    open_ended = [g for g in grades if not g["superseded_by"]]
    assert len(open_ended) == 1, (
        f"{len(open_ended)} assertions have no successor; exactly one grade is"
        " in force, and the rest must each name what replaced it"
    )
    assert open_ended[0] is grades[-1], (
        "the open end of the chain is not the latest assertion"
    )
    assert all(g["valid_to"] for g in grades[:-1]), (
        "a superseded assertion carries no `valid_to`; it would read as still"
        " in force"
    )


def test_rsm_g17_an_unknown_obligor_refuses_distinctly_from_one_with_no_spreads(
    example: Any
) -> None:
    """`RSM-G17` — a request error and a fact about the world are different answers.

    §G.1 and §D.7. An obligor the estate does not hold is a `404`: the question
    named something that does not exist. An obligor that exists but carries no
    spread is a `200` with the series `NOT_EVALUABLE` — a fact about the world,
    not a malformed request. Collapsing them tells a caller to fix their input
    when the input was right.
    """
    acquisition = example["acquisition"]
    with pytest.raises(acquisition.UnknownObligor) as unknown:
        serve(example, anchor_lei="549300NOTANOBLIGOR0")
    message = str(unknown.value).lower()
    assert "not available" in message or "404" in message
    # The distinction is in the refusal's own vocabulary: it names the obligor
    # as absent, never the spread series as absent.
    assert "spread" not in message, (
        "the unknown-obligor refusal talks about spreads; a caller cannot tell"
        " a bad identifier from an unpriced name"
    )


def test_rsm_g18_the_issuer_specific_component_names_its_own_provenance(
    confirmation: Any
) -> None:
    """`RSM-G18` — labeled `synthetic — engineered`, and no TRACE anywhere.

    §G.1, `CP10-F-01`. The vault's §C assumed FINRA TRACE for this leg;
    measured, the estate holds none — identifiers are `syn-i-*` and the
    issuer-specific figure is a RESIDUAL, not an observed trade. A product that
    let a reader believe otherwise would misrepresent its own evidence.
    """
    body = str(confirmation.payload)
    for series in confirmation.payload["spread_series"]:
        provenance = series["component_provenance"]
        assert "synthetic — engineered" in provenance["idiosyncratic_bp"]
        assert "residual" in provenance["idiosyncratic_bp"].lower()
        assert "public" in provenance["benchmark_bp"]
        assert "public" in provenance["market_oas_bp"]
    assert "TRACE" not in body, (
        "the payload names TRACE; this estate holds none and the product must"
        " not imply an observed trade price"
    )


def test_rsm_g19_the_four_axes_are_fields_not_parameters(example: Any) -> None:
    """`RSM-G19` — `subject`, `intent`, `freshness`, `asked_at` are FIELDS.

    §G.1 and §B.5. The four §6.3 axes establish WHICH QUESTION was asked, and
    they are what the content address and the replay record resolve against.
    Demoting one into `parameters` would make it an ordinary argument, and two
    different questions could then share an identity.
    """
    deployment = example["deployment"]
    asked = deployment.request(
        anchor_lei=ANCHOR, asked_at=AS_OF, intent="portfolio-review",
        freshness="daily", window_days=730,
    )
    assert asked.subject == ANCHOR
    assert asked.intent == "portfolio-review"
    assert asked.freshness == "daily"
    assert asked.asked_at == AS_OF
    for axis in ("subject", "intent", "freshness", "asked_at"):
        assert axis not in asked.parameters, (
            f"{axis!r} rides in `parameters` as well as in its field; a second"
            " copy can disagree with the first"
        )


def test_rsm_g20_every_grade_carries_its_scale_and_names_no_agency(
    confirmation: Any
) -> None:
    """`RSM-G20` — scale id and provenance per grade; no agency name anywhere.

    §G.1 and §0.4. Agency ratings are licensed and not redistributable, and an
    SDK example ships with the SDK and is copied by adopters. The boundary can
    fail by PRESENTATION as easily as by content: a payload naming an agency
    would misrepresent its evidence even if every number in it were internal.
    """
    for grade in confirmation.payload["grade_series"]:
        assert grade["scale_version"], "a grade carries no scale id"
        assert grade["provenance"] == "synthetic — internal"
    body = str(confirmation.payload)
    for name in FORBIDDEN:
        assert name not in body, f"the payload names {name!r}"


def test_rsm_g21_the_payload_carries_no_second_copy_of_the_governed_figures(
    confirmation: Any
) -> None:
    """`RSM-G21` — no second copy of `D_c`, the content address, or the versions.

    §G.1. These live on the CONTRACT, and a payload carrying its own copy
    creates two figures that can disagree — with nothing to say which is
    authoritative. The single-source discipline is what makes the contract's
    value citable.
    """
    payload = confirmation.payload
    for forbidden in (
        "debt", "context_debt", "d_c", "payload_hash", "content_address",
        "policy_bundle_versions", "lineage", "expires_at",
    ):
        assert forbidden not in payload, (
            f"the payload carries its own {forbidden!r}; the contract already"
            " does, and two copies of one figure can disagree"
        )


def test_rsm_g22_a_market_wide_widening_produces_no_episode(
    market_move: Any
) -> None:
    """`RSM-G22` — scenario 3, the error in the opposite direction.

    §G.1 and §D.4. Over `2025-02-18 → 2025-04-07` every band widened together —
    `B` +165.0 bp, `BB` +150.5, `BBB` +51.2, `A` +36.0, `AA` +28.9. This
    obligor's HEADLINE moved +166.6 bp; its RESIDUAL moved +1.5 bp. All three
    signals agree nothing happened to this obligor.

    **This is the more common error**: 22 of the 30 rated obligors show the
    same pattern over this window, so a product reading the headline would
    report a deterioration for most of the book.
    """
    assert market_move.payload["spread_series"], (
        "no series reached the payload, so this gate would pass vacuously"
    )
    assert not market_move.payload["episodes"], (
        "a market-wide widening produced an episode; the market component is"
        " not being netted out"
    )
    # The premise, asserted rather than assumed: the residual really is flat
    # over this window while the market component really did move.
    for series in market_move.payload["spread_series"]:
        residuals = [Decimal(p["idiosyncratic_bp"]) for p in series["points"]]
        median = Decimal(series["median_idiosyncratic_bp"])
        assert max(residuals) < median * Decimal(MULTIPLE), (
            "the residual exceeded the threshold, so this window is not the"
            " flat-residual scenario the gate is written against"
        )
        market = {Decimal(p["market_oas_bp"]) for p in series["points"]}
        assert len(market) > 1, (
            "the market component is constant over the window; the widening"
            " this scenario is built on is absent from the read"
        )


def test_rsm_g23_every_spread_figure_names_its_basis(
    confirmation: Any, migrated: Any
) -> None:
    """`RSM-G23` — `static_issue_band`, flagged on migration, never grade-derived.

    §G.1 and `CP10-F-04`. Four bindings, each asserted separately:

    1. every spread figure NAMES its basis;
    2. an obligor whose grade has left its issue band is FLAGGED;
    3. the payload never calls the residual unqualified *"pure issuer
       deterioration"*;
    4. **no band is ever derived from the internal grade** — that would make
       the market component a function of the grade the divergence is measured
       against, and a residual computed that way could not disagree with it.
    """
    payload = confirmation.payload
    assert payload["benchmark_basis"] == BASIS
    for series in payload["spread_series"]:
        assert series["benchmark_basis"] == BASIS
    for episode in payload["episodes"]:
        assert episode["benchmark_basis"] == BASIS

    migration = payload["band_migration"]
    assert migration["basis"] == BASIS
    assert "has_migrated_out_of_issue_band" in migration
    assert migration["issue_bands"], "no issue band was reported at all"
    assert "no band is inferred from the internal grade" in migration["note"]

    body = str(payload).lower()
    assert "pure issuer deterioration" not in body, (
        "the payload claims a precision the basis does not support"
    )
    # The fourth binding, and it is asserted on a subject where the two answers
    # DIFFER. On an obligor still in its issue band, the grade-derived band and
    # the instrument band are the same value — so a gate asserted only on the
    # anchor passes under the very contamination it exists to refuse. Measured:
    # this obligor's bonds were issued into `BBB` and its grade now maps to
    # `BB`, so a band derived from the grade is visibly the wrong one.
    instrument_bands = {str(i.issue_band) for i in migrated.estate.instruments}
    assert instrument_bands == {MIGRATED_ISSUE_BAND}
    migrated_report = migrated.payload["band_migration"]
    assert set(migrated_report["issue_bands"]) == instrument_bands, (
        "the reported issue bands do not match the instruments' own; the band"
        " is being derived from the internal grade, which would make the"
        " market component a function of the grade the divergence is measured"
        " against (`CP10-F-04`)"
    )
    assert migrated_report["current_grade_band"] == MIGRATED_GRADE_BAND
    assert migrated_report["has_migrated_out_of_issue_band"] is True, (
        "an obligor that has left its issue band is not flagged; the residual"
        " is less precise for exactly the obligors this product cares most"
        " about, and the payload must say so"
    )
    assert "less precise" in migrated_report["effect_on_residual"]
    # And the anchor, which has NOT migrated, is reported as such rather than
    # flagged indiscriminately.
    assert migration["has_migrated_out_of_issue_band"] is False
    assert set(migration["issue_bands"]) == {
        str(i.issue_band) for i in confirmation.estate.instruments
    }


def test_rsm_g24_an_obligor_level_figure_never_travels_without_its_dispersion(
    confirmation: Any
) -> None:
    """`RSM-G24` — the summary carries the per-bond values it summarizes.

    §G.1, TRAP 6. An obligor-level spread is a mean over instruments that may
    be pricing different things: measured, **5,267 (obligor, date) pairs in
    this estate carry one bond at more than twice the other**. A summary served
    alone reads as an observation, and that is how the anchor's peak came to be
    halved in my own Gate-1 measurement (`CP10-F-06`).
    """
    summary = confirmation.payload["obligor_spread_summary"]
    assert summary is not None
    assert summary["kind"] == "derived-summary"
    dispersion = summary["dispersion"]
    assert dispersion["per_bond_median_bp"]
    assert dispersion["per_bond_peak_bp"]
    served = {s["instrument_id"] for s in confirmation.payload["spread_series"]}
    assert set(dispersion["per_bond_median_bp"]) == served, (
        "the dispersion does not cover every bond the summary was computed"
        " from; a reader cannot tell whether it describes a bond or no bond"
    )
    assert set(dispersion["per_bond_peak_bp"]) == served
    assert summary["caution"], "the summary travels without its caution"
    # The dispersion is not decorative here: the two peaks differ by ~6x.
    peaks = [Decimal(v) for v in dispersion["per_bond_peak_bp"].values()]
    assert max(peaks) / min(peaks) > 2, (
        "the two bonds' peaks are within 2x, so this serve does not exercise"
        " the dispersion the gate is about"
    )
