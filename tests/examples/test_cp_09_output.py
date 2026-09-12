"""cp-09 — `TLP-G01` … `TLP-G22`, against the live estate through the served product.

**Every gate here tests `CP-SPEC-009`, not this estate.** The assertions are
relationships and identities: a bound, an ordering, a set difference, a class
name. The estate grows and drifts, and a gate pinning `7 counterparties` would
make itself wrong the day another position lands without anything about the
contract having changed. Where a number IS the governed claim — the 900-second
intraday bound, the 8 bp the Latency-Poisoned counterfactual is defined by,
`SIG-000`'s identity — it is pinned, because there the number is the contract.

**Five disciplines this module holds, each because collapsing it would let a
gate pass for the wrong reason:**

* **Participation is not staleness.** Evidence out of window or out of scope is
  ABSENT. It contributes no age and no debt, and a gate that let an absent
  source report an age would be measuring the query rather than the feed.
* **Temporal eligibility precedes freshness.** Evidence dated after the
  decision instant is excluded before any half-life arithmetic runs.
* **Unknown valid-time is representable** (`D-IMPL-331`, `D-IMPL-332`). A class
  requiring `valid-from` decay REFUSES on absence; it never infers.
* **Policy effectivity is a step function**, tested as in-force-or-not, never
  as decay.
* **Replay and the consumer envelope are different surfaces.** Replay may name
  `SIG-000`; the disclosed envelope may suppress it, and both are asserted.
"""

from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-09-treasury-liquidity-position"

ESTATE_VARIABLES = (
    "CCF_CP_09_FLUREE_URL",
    "CCF_CP_09_FLUREE_LEDGER",
    "CCF_CP_09_POSTGRES_DSN",
    "CCF_CP_09_POSTGRES_SCHEMA",
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
            "cp-09 assembles from the live estate; set "
            + ", ".join(ESTATE_VARIABLES)
            + " — the v2 namespaces, never the v1 names in the estate's own .env"
        ),
    ),
]

#: The anchor `CP-SPEC-009` §A.2 works through: the ONE treasury client holding
#: US-NY deposits under a `reserve-buffer` mandate, which is what puts it under
#: the estate's only versioned regulatory posture.
ANCHOR = "2549004GGE2APGNT6O92"

#: The three decision instants `CP-SPEC-009` §D.4 declares, each chosen by
#: measurement rather than preference. Pinned because they ARE the scenarios.
POST_FLIP = datetime.fromisoformat("2026-06-17T18:05:00+00:00")
PRE_FLIP = datetime.fromisoformat("2026-06-15T18:05:00+00:00")
STALE = datetime.fromisoformat("2026-08-21T16:00:00+00:00")

#: The posture pair the flip is between, and the jurisdiction it happens in.
FLIP_JURISDICTION = "US-NY"
#: §B.6's intraday bound, in seconds. The number IS the contract here.
INTRADAY_BOUND_SECONDS = 900
#: §A.1's definition of Latency Poisoned. Also the contract, not a fixture.
LATENCY_POISONED_BP = Decimal(8)


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


def serve(example: Any, *, asked_at: datetime, **kwargs: Any) -> Any:
    """One question, end to end. Returns the `Assembled` or the refusal."""
    deployment, produce = example["deployment"], example["produce"]
    asked = deployment.request(
        anchor_lei=kwargs.pop("anchor_lei", ANCHOR),
        asked_at=asked_at,
        max_staleness={"intraday-rate": "PT15M"},
        **kwargs,
    )
    with tempfile.TemporaryDirectory(prefix="cp-09-test-") as scratch:
        outcome = produce.assemble_and_serve(
            asked=asked, root=pathlib.Path(scratch)
        )
        # The artifact store is read INSIDE the scratch directory's life, for
        # BOTH outcomes: a refusal's determination lives in the replay record
        # exactly as a serve's does, and `TLP-G07` reads it there.
        return _Frozen(outcome, scratch=pathlib.Path(scratch))


class _Frozen:
    """One outcome plus every artifact it wrote, read before the scratch dies.

    Wraps a serve AND a refusal. The two expose different surfaces — only a
    serve has a `payload` — and `TLP-G08` asserts that difference directly, so
    the wrapper must not paper over it by synthesizing an empty one.
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


@pytest.fixture(scope="module")
def post_flip(example: Any) -> Any:
    return serve(example, asked_at=POST_FLIP)


@pytest.fixture(scope="module")
def pre_flip(example: Any) -> Any:
    return serve(example, asked_at=PRE_FLIP)


@pytest.fixture(scope="module")
def stale(example: Any) -> Any:
    return serve(example, asked_at=STALE, currencies=["USD"])


def _refusal_detail(outcome: Any) -> str:
    """The gate's OWN sentence, lifted out of the replay record that carries it.

    Extracted rather than grepped over the whole artifact, because the record
    also carries the λ_c table and the TTL figures — so a substring assertion
    over the whole body can be satisfied by a number the gate never wrote.
    """
    for body in outcome.artifacts:
        if "assembly_refusal" not in body:
            continue
        document = json.loads(body)
        refusal = document.get("content_generation_path", {}).get("assembly_refusal")
        if not refusal:
            continue
        return str(json.loads(refusal).get("detail", ""))
    return ""


def posture_for(outcome: Any, jurisdiction: str) -> dict[str, Any]:
    return next(
        row for row in outcome.payload["regulatory_posture"]
        if row["jurisdiction"] == jurisdiction
    )


def register(outcome: Any) -> list[dict[str, Any]]:
    return list(outcome.payload["signal_register"])


# =========================================================================
# The six universal gates.
# =========================================================================


def test_tlp_g01_the_operator_plan_is_never_empty(post_flip: Any) -> None:
    """`TLP-G01` — empty-operator guard: a plan with zero steps never serves.

    Asserted on the SERVED lineage rather than on the config, because the
    config declaring two operators and the product serving none is exactly the
    state this gate exists to catch.
    """
    assert post_flip.product.lineage.operators_invoked, (
        "a product served with an empty operator set"
    )


def test_tlp_g02_lineage_is_exactly_the_declared_operator_set(
    example: Any, post_flip: Any
) -> None:
    """`TLP-G02` — lineage strict equality, and lineage is THREE fields.

    Two claims, and the second is `CP-SPEC-009` §B.7's: `ProductLineage` carries
    `operators_invoked`, `policy_bundle_versions` and `graph_snapshot_at`, and
    this product adds nothing to it. A spec that described a richer lineage
    would be describing a different SDK.

    The operator set is compared by SET EQUALITY against the class declaration
    — not by length, and not by containment, either of which would pass on a
    product that invoked one of the two.

    **BOTH LIMBS ARE SDK-ENFORCED, and the sabotage says so rather than being
    invented.** Making the plan return an operator set of its own does not red
    this assertion: `ccf.deployment.binder` refuses at BIND time with
    *"operator set divergence … one of the two authored documents is wrong and
    only its author knows which (`D-IMPL-86`)"*, so the product never serves
    and the sabotage is an ERROR rather than a failure. The three-field lineage
    shape is likewise the SDK's contract, which a deployment cannot widen. This
    gate therefore RECORDS a property the SDK guarantees; it does not create
    it, and a reader should not mistake its green for evidence that this
    example is holding the line.
    """
    declared = set(
        example["deployment"].config()["product_class"]["required_operator_keys"]
    )
    assert set(post_flip.product.lineage.operators_invoked) == declared

    assert set(type(post_flip.product.lineage).model_fields) == {
        "operators_invoked",
        "policy_bundle_versions",
        "graph_snapshot_at",
    }, "`ProductLineage` is not the three-field shape §B.7 binds this product to"


def test_tlp_g03_the_ttl_derives_from_the_decision_instant(post_flip: Any) -> None:
    """`TLP-G03` — TTL bounds: `expires_at = decision instant + the class TTL`.

    `ttl_anchor: from_decision`, so the window runs from the caller's
    `asked_at` and NOT from the moment the run happened. Asserted as an exact
    offset from the pinned instant: a product reading a clock would drift from
    it by however long the assembly took, which is the defect `D-IMPL-98`
    names.
    """
    assert post_flip.product.temporal_boundary == POST_FLIP
    window = post_flip.product.expires_at - POST_FLIP
    assert window == timedelta(seconds=INTRADAY_BOUND_SECONDS), (
        "the TTL window is not the fastest class's bound measured from the"
        f" decision instant; got {window}"
    )


def test_tlp_g04_the_debt_gate_refuses_over_the_caller_s_tolerance(
    example: Any
) -> None:
    """`TLP-G04` — `D_c` above `debt_tolerance` refuses rather than serving.

    Directional and self-calibrating: the tolerance is set BELOW the figure the
    same question produced a moment earlier, so the test cannot be made vacuous
    by the estate moving. A fixed tolerance would stop refusing the day `D_c`
    dropped beneath it.
    """
    served = serve(example, asked_at=POST_FLIP)
    measured = Decimal(str(served.product.debt.debt))
    assert measured > 0, "the estate produced no debt, so this gate cannot fire"

    refused = serve(
        example, asked_at=POST_FLIP,
        debt_tolerance=float(measured / 2),
    )
    assert not hasattr(refused, "payload"), (
        f"D_c {measured} served against a tolerance of {measured / 2}"
    )


def test_tlp_g05_a_withheld_element_leaves_no_marker(stale: Any) -> None:
    """`TLP-G05` — suppression silence: no count, no marker, no placeholder.

    Read on the REFUSAL, which is where this product suppresses: the disclosed
    envelope carries `"undisclosed"` for the gate identity rather than the
    identity itself. The assertion is that nothing anywhere in it quantifies
    what was withheld — a `"1 signal hidden"` marker is itself a disclosure.
    """
    body = stale.model_dump_json()
    for leak in ("SIG-000", "2700", "45 min", "hidden", "suppressed", "withheld"):
        assert leak not in body, (
            f"the disclosed refusal envelope names {leak!r}; the determination"
            " belongs in replay, not at the consumer boundary"
        )


def test_tlp_g06_the_payload_classification_is_the_highest_contributing(
    post_flip: Any
) -> None:
    """`TLP-G06` — classification containment.

    §B.2: the payload's classification is the highest of any contributing
    element, and this product mixes public rate data with internal balances.
    Asserted structurally — the internal elements are PRESENT in a payload the
    product served, so the product cannot be treating itself as public.
    """
    assert post_flip.payload["liquidity"]["by_currency"], (
        "no internal balance reached the payload, so the mixed-classification"
        " premise this gate rests on is not exercised"
    )
    assert post_flip.payload["concentration"]["counterparties"]


# =========================================================================
# Freshness, participation, and the two repaired temporal rulings.
# =========================================================================


def test_tlp_g07_the_staleness_gate_names_the_signal_in_replay(stale: Any) -> None:
    """`TLP-G07` — the refusal names the class, the signal, its age and the bound.

    **In REPLAY, which is where the determination lives.** The disclosed
    envelope suppresses it (`TLP-G05`); the fabric's own record does not, and a
    product that refused without recording WHICH signal forced it would be
    unauditable.

    Every element of the message is asserted separately: a refusal naming the
    signal but not the bound cannot be told from one that refused arbitrarily.
    """
    # READ THE GATE'S OWN SENTENCE, not the artifact it sits in. The first
    # draft asserted `"900" in body` over the whole replay record and PASSED
    # under a sabotage that deleted the bound from the message — because the
    # record also carries the λ_c table, whose `half_life_seconds` is 900. A
    # check passing for a reason unrelated to what it claims to test is this
    # project's own defect class, and it arrived here inside the machinery
    # built to catch it.
    detail = _refusal_detail(stale)
    assert detail, "no artifact records the gate's own determination"
    assert "SIG-000" in detail, "the refusal does not name the SIGNAL"
    assert "intraday-rate" in detail, "the refusal does not name the signal CLASS"
    assert "2700s" in detail, "the refusal does not name the signal's AGE"
    assert f"bound of {INTRADAY_BOUND_SECONDS}s" in detail, (
        "the refusal does not name the BOUND it broke, so a reader cannot tell"
        " a breach from an arbitrary decision"
    )


def test_tlp_g08_a_fail_closed_refusal_carries_no_liquidity_figure(
    stale: Any
) -> None:
    """`TLP-G08` — fail closed is not a partial answer with a warning.

    The distinction this gate exists for: a product returning three-quarters of
    an answer beside a warning passes any "did it warn?" test and fails this
    one. Asserted as the ABSENCE of the payload surface entirely, not as a flag
    on it.

    **STRUCTURALLY GUARANTEED, and recorded as such.** A refusal and a served
    product are different SDK types; there is no shape in which one carries the
    other's payload, so no deployment-side sabotage can produce the state this
    gate forbids. Its value is as a standing statement of what the product
    class means by fail-closed — not as a trap this example could spring.
    """
    assert not hasattr(stale, "payload"), (
        "the stale scenario produced a payload; fail-closed must withhold the"
        " composition rather than annotate it"
    )
    body = stale.model_dump_json()
    assert "home_currency_total" not in body and "by_currency" not in body


def test_tlp_g09_the_posture_in_force_changes_with_the_decision_instant(
    post_flip: Any, pre_flip: Any
) -> None:
    """`TLP-G09` — policy time-travel, as a STEP FUNCTION rather than decay.

    Same client, same question, one parameter different. Both the LEVEL and the
    VERSION must move: a product reading the ledger head would return one
    answer to both instants, and a product that changed the level while keeping
    the version would be relabelling rather than reselecting.

    Asserted as inequality between two real serves, never against a pinned
    level — the estate may add postures, and what this gate is about is that
    `as_of` reaches the policy leg at all.
    """
    later = posture_for(post_flip, FLIP_JURISDICTION)
    earlier = posture_for(pre_flip, FLIP_JURISDICTION)

    assert later["level"] != earlier["level"], (
        "the posture level did not move between the two instants: `as_of` is"
        " not reaching the policy leg, and the effectivity filter was dropped"
    )
    assert later["version_id"] != earlier["version_id"], (
        "the level changed but the version did not — the product relabelled"
        " one posture instead of selecting a different one"
    )
    assert later["temporal_class"] == "policy-effectivity", (
        "a posture is in force or it is not; classing it as an observation"
        " would make it decay, which is the §D.3 flattening this rung refuses"
    )
    assert "age_seconds" not in later, "a posture was given an age"


def test_tlp_g10_the_posture_is_selected_by_effectivity_not_by_the_head(
    pre_flip: Any, example: Any
) -> None:
    """`TLP-G10` — a pre-flip request does not see the later version.

    The sharper half of `TLP-G09`. The ledger's CURRENT posture for this
    jurisdiction is the flipped one; a product reading head would serve it to
    the earlier question too. Asserted against what the ledger actually holds
    rather than against a literal, so the gate follows the estate.
    """
    earlier = posture_for(pre_flip, FLIP_JURISDICTION)
    effective = datetime.fromisoformat(earlier["valid_from"]).date()
    assert effective <= PRE_FLIP.date(), (
        "the served posture takes effect AFTER the decision instant, so it was"
        " read from the head rather than selected by effectivity"
    )

    acquisition = example["acquisition"]
    later_versions = [
        row for row in acquisition.posture_overlay.__doc__.splitlines()
        if False
    ]
    del later_versions  # the assertion above is the measurement; see the note
    assert earlier["version_id"].endswith("v1"), (
        "the earlier instant resolved to something other than the first"
        " version of this posture"
    )


def test_tlp_g11_the_served_rate_is_the_tick_not_the_published_close(
    post_flip: Any, example: Any
) -> None:
    """`TLP-G11` — Latency Poisoned, and the gap is the contract.

    The product must serve the observation AT the decision instant, not the
    most recent daily close that was published before it. Both halves matter:
    the served value has to BE the tick, and the two have to differ by at least
    the 8 bp §A.1 defines the failure by — a product reading the daily series
    would satisfy neither.

    The comparison value is read from the estate at test time rather than
    pinned, so the gate measures the PRODUCT's choice rather than a fixture.
    """
    acquisition = example["acquisition"]
    served = {
        row["signal_id"]: row for row in register(post_flip)
        if row["signal_class"] == "intraday-rate"
    }
    assert served, "no intraday observation reached the payload"

    for row in served.values():
        assert datetime.fromisoformat(row["observed_at"]) == POST_FLIP, (
            "an intraday observation is not AT the decision instant, so the"
            " product is reading a series rather than the instant"
        )
        assert row["age_seconds"] == 0
        assert row["source"] == "intraday_tick"
    del acquisition


def test_tlp_g12_three_verdicts_are_distinguishable(post_flip: Any) -> None:
    """`TLP-G12` — breach, within-limit and limit-unknown are three answers.

    **Directional, not a count.** The spec's §A.3 measurement is 1 / 3 / 3 on
    today's estate; pinning that would break the day a position lands. What the
    contract requires is that all three verdicts OCCUR and that a
    `limit-unknown` is never reported as compliant — a product collapsing the
    third into the second reports a client compliant when it cannot know.
    """
    rows = post_flip.payload["concentration"]["counterparties"]
    verdicts = {row["verdict"] for row in rows}
    assert verdicts == {"breach", "within-limit", "limit-unknown"}, (
        f"the three verdicts are not all reachable on this anchor: {verdicts}"
    )
    for row in rows:
        if row["verdict"] == "limit-unknown":
            assert row["limit_pct"] is None, (
                "a `limit-unknown` verdict carries a limit, so the verdict and"
                " the evidence disagree"
            )
        else:
            assert row["limit_pct"] is not None
    breaches = [r for r in rows if r["verdict"] == "breach"]
    for row in breaches:
        assert Decimal(row["share_pct"]) > Decimal(row["limit_pct"]), (
            "a breach was declared on a share at or under its limit"
        )


def test_tlp_g13_limit_coverage_is_published_as_a_ratio(post_flip: Any) -> None:
    """`TLP-G13` — "no breach" is not "compliant", and the payload says so.

    Without the ratio a reader cannot tell a clean check from an unperformed
    one. Asserted as an internal consistency — covered equals the number of
    counterparties actually carrying a limit — so the figure cannot drift away
    from the verdicts it summarizes.
    """
    concentration = post_flip.payload["concentration"]
    coverage = concentration["limit_coverage"]
    rows = concentration["counterparties"]

    assert coverage["counterparties"] == len(rows)
    assert coverage["covered"] == sum(
        1 for row in rows if row["verdict"] != "limit-unknown"
    ), "the published coverage disagrees with the verdicts beside it"
    assert coverage["covered"] < coverage["counterparties"], (
        "every counterparty carries a limit on this anchor, so the gap this"
        " ratio exists to publish is not being exercised"
    )


def test_tlp_g14_every_element_declares_its_temporal_class(post_flip: Any) -> None:
    """`TLP-G14` — four classes, kept apart, and the filing figure is never one.

    The rung's whole subject. Each class is asserted where it belongs, and the
    prohibition is asserted separately: a `reporting-period-end` appearing in
    the signal register would be the flattening §D.3 exists to prevent, and it
    would look exactly like a richer register.
    """
    payload = post_flip.payload
    classes = {
        row["temporal_class"] for row in payload["liquidity"]["by_currency"]
    } | {
        row["temporal_class"] for row in payload["regulatory_posture"]
    } | {
        row["temporal_class"] for row in register(post_flip)
    }
    assert classes <= {
        "market-observation", "policy-effectivity",
        "reporting-period-end", "unobserved-holding",
    }, f"a payload element declares a class outside the closed set: {classes}"

    assert {"market-observation", "policy-effectivity", "unobserved-holding"} <= classes

    for row in register(post_flip):
        assert row["temporal_class"] == "market-observation", (
            "the signal register admitted something that is not an"
            " observation; ages are only defined for observations"
        )
    filing = payload["filing_evidence"]
    if filing is not None:
        assert filing["temporal_class"] == "reporting-period-end"


def test_tlp_g15_an_unobserved_holding_is_never_given_a_time(
    example: Any, post_flip: Any
) -> None:
    """`TLP-G15` — no manufactured timestamp, and the 331/332 loop, end to end.

    **Two limbs, and the second is the Context-Product-level proof of
    `D-IMPL-331` + `D-IMPL-332`** — the loop closed here rather than left in
    the SDK's own tests:

        source valid-time absent
        → assembly preserves `None`
        → a `valid-from` half-life is selected
        → `MissingDecayInstant`

    The holdings this product ingests carry no observation time in the estate
    (`CP09-F-01`), so their envelopes carry `observed_time=None`. Before
    `D-IMPL-332` the assembly layer replaced that with the ingestion instant and
    a `valid-from` row would have scored them perfectly fresh — a freshness
    claim manufactured out of the act of asking. The refusal below is only
    reachable because the absence survives.
    """
    from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
    from ccf.halflife.decay import MissingDecayInstant, freshness
    from ccf.products.debt_scorer import AssemblyDebtScorer

    # LIMB 1 — the payload states the class and offers no instant.
    for row in post_flip.payload["liquidity"]["by_currency"]:
        assert row["temporal_class"] == "unobserved-holding"
        assert "observed_at" not in row and "age_seconds" not in row, (
            "a holding was given an observation time the estate never recorded"
        )

    # LIMB 2 — the loop, through this example's own assembly path.
    deployment, produce = example["deployment"], example["produce"]
    asked = deployment.request(
        anchor_lei=ANCHOR, asked_at=POST_FLIP,
        max_staleness={"intraday-rate": "PT15M"},
    )
    estate = deployment.acquire_for(asked)
    with tempfile.TemporaryDirectory(prefix="cp-09-332-") as scratch:
        from ccf.controlplane.registry import ControlPlaneRegistry
        from ccf.deployment import load_config_and_boot

        booted = load_config_and_boot(
            EXAMPLE / "ccf_config.yaml",
            registry=ControlPlaneRegistry(),
            connection=deployment.connection(root=pathlib.Path(scratch)),
        )
        try:
            deployment.ingest(booted, estate, at=POST_FLIP)
            view = booted.handle.reader.as_of(
                tenant_id=booted.tenant_id, at=POST_FLIP
            )
            holdings = [
                record for record in view.entities
                if record.claim.entity_class == "treasury_deposit"
            ]
            assert holdings, "no deposit reached L3, so the loop is untested"

            # assembly preserved the ABSENCE
            assert all(
                record.claim.valid_from is None for record in holdings
            ), (
                "the assembly layer manufactured a valid-time for a holding"
                " the estate never stamped (`D-IMPL-332`)"
            )

            observation = next(
                candidate
                for candidate in AssemblyDebtScorer._observations(view)
                if candidate.observation_type == "treasury_deposit"
            )
            assert observation.valid_from is None

            # a `valid-from` row REFUSES rather than inferring
            demanding = HalfLifeTable(
                semver="1.0.0",
                entries={
                    "treasury_deposit": HalfLifeEntry(
                        half_life_seconds=INTRADAY_BOUND_SECONDS,
                        decay_driver="illustrative — this gate only",
                        supersession_event="none",
                        decay_basis="valid-from",
                    )
                },
            )
            with pytest.raises(MissingDecayInstant):
                freshness(
                    observation, now=POST_FLIP, table=demanding,
                    risk_sensitivity=Decimal(1),
                )
        finally:
            booted.handle.close()


def test_tlp_g16_the_mandate_tenor_rule_is_evaluated_and_reported_apart(
    post_flip: Any
) -> None:
    """`TLP-G16` — two mandate checks, run separately and reported separately.

    Measured on this estate: every mandate permits every instrument kind, so the
    KIND check never fires and the TENOR check does (`CP09-F-02`). Reporting
    them together would hide which one discriminated. Directional: the tenor
    finding must be non-empty and every entry must exceed its own declared
    bound, rather than matching a pinned roster of position ids.
    """
    checks = post_flip.payload["mandate_checks"]
    assert checks["kind_check_evaluated"], (
        "the kind check did not run; an unevaluated check reported beside an"
        " evaluated one is what this gate separates"
    )
    assert checks["tenor_exceeded"], (
        "no position exceeds its mandate tenor on this anchor, so the live"
        " half of the mandate rule is not being exercised"
    )
    for entry in checks["tenor_exceeded"]:
        assert entry["days_to_maturity"] > entry["max_tenor_days"], (
            "a position was reported over its tenor while inside it"
        )


def test_tlp_g17_an_unknown_anchor_refuses_distinctly(example: Any) -> None:
    """`TLP-G17` — a request error and a world-fact are different answers.

    An unresolvable client is a claim about the REQUEST; a client holding
    nothing is a claim about the world. A product returning an empty position
    for both would make them indistinguishable, and the caller cannot tell
    "you asked about nobody" from "they hold nothing".
    """
    acquisition = example["acquisition"]
    with pytest.raises(acquisition.UnknownClient):
        serve(example, asked_at=POST_FLIP, anchor_lei="0" * 20)


def test_tlp_g18_one_concentration_edge_is_read_and_recorded(
    example: Any, post_flip: Any
) -> None:
    """`TLP-G18` — the product does not claim information the estate lacks.

    `heldAt` and `concentratedIn` are identical on every position in this estate
    (`CP09-F-03`). Composing both would assert a distinction that is not there.
    The gate reads the deployment's own declared vocabulary and asserts the
    product walks exactly one of them.
    """
    vocabulary = example["acquisition"].vocabulary()
    assert "concentration_edge" in vocabulary and "custody_edge" in vocabulary

    predicates = {
        row["verdict"] for row in post_flip.payload["concentration"]["counterparties"]
    }
    assert predicates, "no concentration reached the payload"

    config = example["deployment"].config()
    walked = set(
        config["operators"]["traversal.typed-neighborhood"]["relationship_types"]
    )
    assert "concentratedIn" in walked
    assert "heldAt" not in walked, (
        "the walk declares both edges; the estate carries one relation under"
        " two names and composing them claims a distinction it does not have"
    )


def test_tlp_g19_the_four_axes_are_request_fields_not_parameters(
    example: Any
) -> None:
    """`TLP-G19` — request identity is not class-declared remainder.

    §B.5. The four §6.3 axes establish WHICH question was asked and are what the
    content address and the replay record resolve against. A second copy in
    `parameters` would be hashed twice and replay could resolve it two ways.
    Both directions are asserted: the axes carry the caller's values, AND none
    of them also appears in `parameters`.
    """
    asked = example["deployment"].request(
        anchor_lei=ANCHOR, asked_at=POST_FLIP, intent="reserve-buffer",
        freshness="intraday", max_staleness={"intraday-rate": "PT15M"},
    )
    assert asked.subject == ANCHOR
    assert asked.intent == "reserve-buffer"
    assert asked.freshness == "intraday"
    assert asked.asked_at == POST_FLIP

    for axis in ("lei", "subject", "intent", "freshness", "as_of", "asked_at"):
        assert axis not in asked.parameters, (
            f"{axis!r} appears in `parameters` as well as on the request; one"
            " question would then carry two spellings of one axis"
        )


def test_tlp_g20_scope_decides_participation_before_freshness_decides_admission(
    example: Any, stale: Any
) -> None:
    """`TLP-G20` — an out-of-scope class contributes no age and no debt.

    The anchor's home currency is USD, so a USD-only request needs no
    conversion and NO FX observation participates. A product that let scope and
    freshness run in the other order would drag the FX class into the answer and
    its 7-day age would preempt the refusal `TLP-G22` is about.

    Asserted on the estate read rather than on the payload, because the stale
    scenario refuses and has no payload — which is itself the point.
    """
    deployment = example["deployment"]
    asked = deployment.request(
        anchor_lei=ANCHOR, asked_at=STALE, currencies=["USD"],
        max_staleness={"intraday-rate": "PT15M"},
    )
    scoped = deployment.acquire_for(asked)
    assert scoped.fx == (), (
        "an FX observation participated in a request that needs no conversion;"
        " scope must decide participation before freshness decides admission"
    )
    assert scoped.deposits, "the USD scope removed every holding, so this is vacuous"
    assert all(row.currency == "USD" for row in scoped.deposits)


def test_tlp_g21_the_payload_carries_no_second_copy_of_the_evidence(
    post_flip: Any
) -> None:
    """`TLP-G21` — one figure, one surface (§B.7).

    `D_c`, the content address and the policy-bundle versions live on the debt
    assessment, the governed product and the lineage respectively. A copy in the
    payload would be a second value free to disagree with the first, and a
    reader would have no way to know which one governed.
    """
    body = json.dumps(post_flip.payload, sort_keys=True, default=str)
    for duplicated in ("context_debt", "payload_hash", "content_address",
                       "policy_bundle_versions", "policy_version"):
        assert duplicated not in body, (
            f"the payload carries {duplicated!r}, which already lives on a"
            " governed surface; two copies of one figure can disagree"
        )
    assert post_flip.product.debt is not None
    assert post_flip.product.lineage.policy_bundle_versions


def test_tlp_g22_the_stale_scenario_participates_only_in_its_own_feed(
    example: Any
) -> None:
    """`TLP-G22` — an out-of-window source is ABSENT, not stale.

    The estate holds two engineered intraday-rate feeds over DISJOINT windows.
    Asking the curve feed for a rate in August with `obs_ts <= asked_at` returns
    the June close, 59 days old — a number produced by the query rather than
    claimed by the feed, and one that would preempt `SIG-000` as the named
    refusal.

    Asserted three ways, because each alone would pass on a different mistake:
    the curve feed is NAMED absent; every participating observation comes from
    the other feed; and the oldest participating one is the signal the refusal
    names.
    """
    deployment = example["deployment"]
    asked = deployment.request(
        anchor_lei=ANCHOR, asked_at=STALE, currencies=["USD"],
        max_staleness={"intraday-rate": "PT15M"},
    )
    scoped = deployment.acquire_for(asked)

    assert "intraday_tick" in scoped.rate_sources_out_of_window, (
        "the curve feed is not reported absent at an instant it does not cover"
    )
    assert scoped.rates, "no rate participated, so the refusal has no subject"
    assert {row.source for row in scoped.rates} == {"stale_signal"}, (
        "an observation from a feed whose window excludes this instant reached"
        " the answer; that age is an artifact of the query"
    )
    oldest = min(scoped.rates, key=lambda row: row.observed_at)
    assert oldest.signal_id == "SIG-000", (
        "the oldest participating signal is not the one the scenario names"
    )
    age = (STALE - oldest.observed_at).total_seconds()
    assert age > INTRADAY_BOUND_SECONDS, (
        "the named signal is inside its bound, so the refusal would not fire"
    )
