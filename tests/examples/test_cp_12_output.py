"""cp-12 — `FXR-G01` … `FXR-G27`, against the live estate through the served product.

**Every gate here tests `CP-SPEC-012`, not this estate.** The assertions are
relationships and identities: a partition, a closure, a set difference, a
count that is the contract. Where a number IS the governed claim — the 60-vs-120
unit ratio, the 20.0-hour weekend staleness, USD/JPY's `0.01` pip — it is
pinned, because there the number is what the gate exists to hold.

**The six trap gates carry an extra obligation, and it is the spec's own
(§F.1a):**

> A trap gate must DISTINGUISH the wrong mechanism from the right one. Two
> answers coinciding is not evidence.

So `FXR-G22` … `FXR-G27` each construct the defective mechanism in the test,
run it on the same data, and assert the two answers DIFFER. cp-10's trap gate 23
and cp-11's trap gate 27 were both green under their own sabotage because each
asserted only where the two mechanisms happened to agree; that is the failure
this shape exists to make impossible.

**Four disciplines, each because collapsing it would let a gate pass for the
wrong reason:**

* **The unit is the TRADE.** Three systems give three pairs and every break
  partitions two-against-one, so counting pairs reports one divergence twice —
  exactly `2.00x`, measured.
* **`not-evaluable` is not zero.** Where the tick series cannot resolve the
  interval, the timing component is unknown. A zero there is a claim.
* **`no-break` is not a fourth classification.** It says there is nothing to
  classify, and the classification vocabulary stays three.
* **The corrected instant is this product's, not the fabric's.** It compares
  two systems and reaches no `valid_from`, no `observed_at` and no debt term.
"""

from __future__ import annotations

import hashlib
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
EXAMPLE = REPO_ROOT / "examples" / "cp-12-fx-post-trade-reconciliation"

ESTATE_VARIABLES = (
    "CCF_CP_12_FLUREE_URL",
    "CCF_CP_12_FLUREE_LEDGER",
    "CCF_CP_12_POSTGRES_DSN",
    "CCF_CP_12_POSTGRES_SCHEMA",
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
            "cp-12 assembles from the live estate; set "
            + ", ".join(ESTATE_VARIABLES)
            + " — the v2 namespaces, never the v1 names in the estate's own .env"
        ),
    ),
]

# --- The named cases, each selected because it is a DIVERGENCE case --------
#
# `WORKED` is §A.3: risk and trading correct to the same true instant and agree
# exactly; settlement observes 33 minutes later. It is also the hidden-break
# case — amendment 1 reconciled it, so at `latest` there is nothing there.
WORKED = "TRD-W12-0002"
#: §D.3 scenario 2. All three systems correct to 07:34:39 and trading alone
#: differs: a zero timing interval, so nothing about timing explains it.
GENUINE = "TRD-W12-0004"
#: TRAP 4. The nearest preceding tick is 20.0 hours old across the weekend.
STALE = "TRD-W12-0124"
#: TRAP 5. USD/JPY, where the pip is `0.01` and not `0.0001`.
JPY = "TRD-W12-0424"
#: TRAP 2. The corrected observation gap is 296 s against a 300 s series.
SUBTICK = "TRD-W12-0235"
#: A trade with no `break_record` row and no amendment — `FXR-G15`'s subject.
CLEAN = "TRD-W12-0001"

WORKED_CASES = [WORKED, GENUINE, STALE, JPY]
SCOPE = "w12-worked-cases"

#: Just past the right edge of the trade window (executions run 2026-08-06 ..
#: 2026-08-13). Every observation is knowable; nothing later exists.
AS_OF = datetime(2026, 8, 14, tzinfo=UTC)

#: The measured pip scales. These ARE the contract — `FXR-G12` and `FXR-G26`
#: exist because defaulting the first to the second reads 100x too small.
JPY_PIP = Decimal("0.01")
MAJOR_PIP = Decimal("0.0001")

#: TRAP 1, measured. 60 break trades, 120 pairwise comparisons above 0.5 pip.
BREAK_TRADES = 60
PAIRWISE_RATIO = 2

#: TRAP 4, measured: 72,041 s ≈ 20.0 hours.
STALE_TICK_HOURS = 20.0

#: The six universal gates plus every behavioral gate name, so a gate that
#: stops executing is visible as an absence rather than as a silent pass.
GATE_IDS = tuple(f"FXR-G{n:02d}" for n in range(1, 28))


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
    """One outcome plus what it wrote, read before the scratch dies."""

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
            self.rows = {
                row["trade_id"]: row for row in self.payload["reconciliations"]
            }

    @property
    def address(self) -> str:
        return self.record.content_generation_path.product_content_address


def serve(
    example: Any, *, trades: list[str] | None = None, scope: str = SCOPE,
    asked_at: datetime = AS_OF, **kwargs: Any,
) -> Any:
    """One question, end to end. Returns the `_Frozen` or the refusal."""
    deployment, produce = example["deployment"], example["produce"]
    asked = deployment.request(
        trades=trades if trades is not None else WORKED_CASES,
        scope=scope, asked_at=asked_at, **kwargs,
    )
    with tempfile.TemporaryDirectory(prefix="cp-12-test-") as scratch:
        outcome = produce.assemble_and_serve(
            asked=asked, root=pathlib.Path(scratch)
        )
        return _Frozen(outcome, scratch=pathlib.Path(scratch))


@pytest.fixture(scope="module")
def served(example: Any) -> Any:
    """The headline serve: the four worked cases, at amendment 0, aligned."""
    return serve(example)


@pytest.fixture(scope="module")
def latest(example: Any) -> Any:
    """The same question asked of current state — what a conventional
    reconciliation sees, and what `FXR-G23` measures against."""
    return serve(example, compare_at="latest")


@pytest.fixture(scope="module")
def unaligned(example: Any) -> Any:
    """The same question with the clock correction disabled."""
    return serve(example, align_clocks=False)


def break_population(example: Any) -> list[str]:
    """The designated break trades, read from the estate rather than pinned.

    `break_record` is a designated SAMPLE (`CP12-F-07`), and reading it here
    keeps `FXR-G22` measuring the ratio rather than a number typed into a test.
    """
    acquisition = example["acquisition"]
    relational = acquisition._Relational(
        dsn=os.environ["CCF_CP_12_POSTGRES_DSN"],
        schema=os.environ["CCF_CP_12_POSTGRES_SCHEMA"],
    )
    return [
        row[0]
        for row in relational.rows("SELECT trade_id FROM break_record ORDER BY trade_id")
    ]


@pytest.fixture(scope="module")
def population(example: Any) -> Any:
    """Every designated break trade, at amendment 0. `FXR-G22`'s subject."""
    return serve(
        example, trades=break_population(example), scope="w12-designated-breaks"
    )


# =========================================================================
# The six universal gates.
# =========================================================================


def test_fxr_g01_the_operator_plan_is_never_empty(served: Any) -> None:
    """`FXR-G01` — a plan with zero operator steps never serves. §F.1."""
    assert served.product.lineage.operators_invoked


def test_fxr_g02_lineage_is_exactly_the_declared_operator_set(
    served: Any, example: Any
) -> None:
    """`FXR-G02` — served lineage equals the plan's typed operator references.

    §F.1, and the second half is `ProductLineage`'s own shape: **exactly three
    fields**. A lineage that grew a fourth would carry something the replay
    contract does not resolve.
    """
    declared = set(
        example["deployment"].config()["product_class"]["required_operator_keys"]
    )
    assert set(served.product.lineage.operators_invoked) == declared
    assert set(type(served.product.lineage).model_fields) == {
        "operators_invoked", "policy_bundle_versions", "graph_snapshot_at",
    }


def test_fxr_g03_the_reconciliation_is_performed_at_the_requested_as_of(
    example: Any, served: Any
) -> None:
    """`FXR-G03` — the reconciliation runs at the requested `as_of` over the
    observation history, and an `as_of` before an amendment sees the
    pre-amendment values. §F.1, TRAP 3 and TRAP 6.

    The subject is `TRD-W12-0002`, whose amendment 1 reconciled the break. Asked
    at `compare_at=latest` with an `as_of` BEFORE that amendment, the only
    observations admissible are amendment 0's — so current state still shows the
    break. Asked at the later instant, current state has forgotten it.

    That is the whole of `as_of` reaching the observation selection. If the two
    answers were the same, `as_of` would be decorative.
    """
    acquisition = example["acquisition"]
    estate = acquisition.acquire(
        trade_ids=[WORKED], asked_at=AS_OF, compare_at="latest"
    )
    # STRICTLY BEFORE the FIRST amendment-1 record. Taking the last one instead
    # admits the whole amendment, which is how this gate first went green for
    # the wrong reason: at that instant current state IS the reconciled state
    # and both readings agree.
    first_amendment = min(
        observation.recorded_at
        for key, series in estate.observations.items()
        if key[0] == WORKED
        for observation in series
        if observation.amendment_seq > 0
    )
    before = serve(
        example, trades=[WORKED], scope=WORKED, compare_at="latest",
        asked_at=first_amendment - timedelta(seconds=1),
    )
    after = serve(
        example, trades=[WORKED], scope=WORKED, compare_at="latest",
        asked_at=AS_OF,
    )
    assert before.rows[WORKED]["verdict"] != "no-break", (
        "asked before the amendment, current state must still show the break;"
        " `as_of` is not reaching the observation selection"
    )
    assert after.rows[WORKED]["verdict"] == "no-break"
    assert {row["amendment_seq"] for row in before.rows[WORKED]["systems"]} == {0}
    assert {row["amendment_seq"] for row in after.rows[WORKED]["systems"]} != {0}


def test_fxr_g04_expiry_derives_from_the_decision_instant(served: Any) -> None:
    """`FXR-G04` — `expires_at` derives from the decision instant, under the
    ceiling. §F.1.

    `ttl_anchor: from_decision`, so the expiry is `asked_at` plus the product
    TTL and never a clock read at serve time — which is what makes a request
    pinned to a past `as_of` a forensic reconstruction rather than an
    already-expired answer.
    """
    product = served.product
    assert product.ttl_anchor == "from_decision"
    elapsed = (product.expires_at - AS_OF).total_seconds()
    assert 0 < elapsed <= 14400, (
        f"expiry is {elapsed}s after the decision instant; §B.1 declares one"
        " hour and the ceiling is four"
    )


def test_fxr_g05_the_three_instants_are_carried_separately(served: Any) -> None:
    """`FXR-G05` — every system value carries its recorded instant, its clock
    offset and its corrected instant, separately. §F.1.

    Asserted where the three actually differ. On `trading` the offset is `0` and
    recorded equals corrected, so a payload that conflated them would look
    correct there — which is exactly the coincidence §F.1a forbids relying on.
    """
    for trade_id in WORKED_CASES:
        for system in served.rows[trade_id]["systems"]:
            assert {"recorded_at", "clock_offset_seconds", "corrected_at"} <= set(
                system
            )
            recorded = datetime.fromisoformat(system["recorded_at"])
            corrected = datetime.fromisoformat(system["corrected_at"])
            offset = system["clock_offset_seconds"]
            assert (recorded - corrected).total_seconds() == offset
            if system["system"] != "trading":
                assert offset != 0 and recorded != corrected, (
                    f"{system['system']} carries a zero offset; the estate"
                    " records +47 s for settlement and -112 s for risk, and a"
                    " gate asserted only on `trading` would prove nothing"
                )


def test_fxr_g06_debt_above_tolerance_refuses_with_the_debt_block(
    example: Any, served: Any
) -> None:
    """`FXR-G06` — `D_c` above the caller's tolerance refuses rather than serving.

    §F.1. Asked with a ceiling measured BELOW the debt the product actually
    carries, so the refusal is forced by the gate and not by a broken read.
    """
    from ccf.products.refusal import RefusalEnvelope

    measured = served.product.debt.debt
    tighter = (measured / 2).quantize(Decimal("0.000001"))

    # THE DEPLOYMENT'S OWN HALF, asserted first. The refusal is the SDK's, but
    # it can only fire on a ceiling that actually reaches the request — a
    # `debt_tolerance` dropped on the way in would make every serve succeed and
    # the gate below would never get the chance to fail.
    asked = example["deployment"].request(
        trades=WORKED_CASES, scope=SCOPE, asked_at=AS_OF, debt_tolerance=tighter
    )
    assert asked.parameters["debt_tolerance"] == tighter
    assert isinstance(asked.parameters["debt_tolerance"], Decimal), (
        "the ceiling rides the content address, and a float is not bit-stable"
    )
    outcome = serve(example, debt_tolerance=tighter).outcome
    assert isinstance(outcome, RefusalEnvelope), (
        f"measured D_c {measured} against a ceiling of {tighter} served anyway"
    )
    # The SDK's own kind for this refusal. Named exactly rather than matched on
    # the substring "debt", which `tolerance-exceeded` does not contain — a
    # looser assertion here would have passed against any refusal at all.
    assert outcome.kind == "tolerance-exceeded"
    assert outcome.disclosure == "minimal", (
        "a debt refusal disclosed more than the minimal envelope; the"
        " determination belongs in the replay record, not in the consumer's"
        " copy"
    )


# =========================================================================
# The behavioral gates — `FXR-G07` … `FXR-G21`.
# =========================================================================


def test_fxr_g07_exactly_one_verdict_per_trade(served: Any, example: Any) -> None:
    """`FXR-G07` — exactly one verdict per trade, and the payload exposes no
    countable pairwise break list. §F.1, TRAP 1.

    The declared product gate (`FXR-G07.one-verdict-per-trade`) enforces the
    same thing on the serve path; this asserts it on the answer AND proves the
    gate is armed by handing it a doubled payload.
    """
    rows = served.payload["reconciliations"]
    assert len(rows) == len(WORKED_CASES)
    assert [row["trade_id"] for row in rows] == sorted(WORKED_CASES)
    assert served.payload["observations"] == len(rows)
    assert not (example["deployment"].PAIRWISE_KEYS & set(served.payload))

    # The gate is not merely declared. Hand it the pairwise payload and watch
    # it refuse — a gate nobody can make fire is a declaration, not a control.
    gate = example["deployment"].build_verdict_gate(
        asked=example["deployment"].request(
            trades=WORKED_CASES, scope=SCOPE, asked_at=AS_OF
        )
    )

    class _Candidate:
        payload = {**served.payload,
                   "reconciliations": rows + rows,
                   "observations": 2 * len(rows)}

    assert gate(candidate=_Candidate()) is not None


def test_fxr_g08_the_divergent_system_is_named_only_where_one_is_isolated(
    population: Any, example: Any
) -> None:
    """`FXR-G08` — where the partition is `(1, 2)` the divergent system is
    named; where it is `(1, 1, 1)` the payload says no system is isolated
    rather than picking one. §F.1.

    **The `(1, 2)` half is asserted on all 60 real partitions.** The named
    system must be the SINGLETON — naming a member of the agreeing pair would
    still produce a plausible-looking answer, and would blame a system that
    agrees with another.

    **The `(1, 1, 1)` half is `not-required` on this estate, and the absence is
    asserted rather than assumed.** Measured across all 500 trades at a
    threshold of 0.01 pip — two hundred times finer than `break-investigation`
    uses — every trade is either all-three-agree (440) or exactly-two-agree
    (60). No three-way disagreement exists at any materiality, so a gate that
    claimed to test that limb would be passing over an empty set. The assertion
    below states the measured shape; if the estate ever grows a three-way case
    it goes red and the limb becomes testable.
    """
    shapes = set()
    for row in population.payload["reconciliations"]:
        groups = row["agreement_groups"]
        sizes = tuple(sorted(len(group) for group in groups))
        shapes.add(sizes)
        if sizes == (1, 2):
            singleton = next(group for group in groups if len(group) == 1)
            agreeing = next(group for group in groups if len(group) == 2)
            assert row["divergent_system"] == singleton[0], (
                f"{row['trade_id']}: named {row['divergent_system']!r}, which is"
                f" not the isolated system {singleton[0]!r}"
            )
            assert row["divergent_system"] not in agreeing, (
                f"{row['trade_id']}: the named system agrees with another, so"
                " it is not the one out"
            )
        elif sizes == (1, 1, 1):
            assert row["divergent_system"] is None
            assert row["verdict"] == "not-evaluable"
            assert row["decomposition"]["reason"] == "three-way-disagreement"
        else:
            assert row["verdict"] == "no-break"
            assert row["divergent_system"] is None

    assert (1, 2) in shapes, "no two-against-one partition; the gate is vacuous"
    assert (1, 1, 1) not in shapes, (
        "a three-way disagreement appeared. Measured 2026-09-12 there were none"
        " in 500 trades at any threshold down to 0.01 pip, so this limb was"
        " recorded `not-required`. It is now testable and must be sabotaged."
    )


def test_fxr_g09_the_decomposition_closes_or_refuses(population: Any) -> None:
    """`FXR-G09` — timing-attributable + residual = total variance, or the
    decomposition is `not-evaluable` with a reason. §F.1, §D.5.

    A silent gap means a system's observation time was dropped from the
    alignment, which is why the closure is asserted arithmetically here rather
    than trusted from the `closes` flag the payload carries.
    """
    evaluated = 0
    for row in population.payload["reconciliations"]:
        d = row["decomposition"]
        if d["state"] == "evaluated":
            evaluated += 1
            total = Decimal(d["total_pips"])
            timing = Decimal(d["timing_attributable_pips"])
            residual = Decimal(d["residual_pips"])
            assert timing + residual == total, (
                f"{row['trade_id']}: {timing} + {residual} != {total}"
            )
            assert d["closes"] is True
        elif d["state"] == "not-evaluable":
            assert d["reason"]
            assert d["timing_attributable_pips"] is None
            assert d["residual_pips"] is None
        else:
            assert d["state"] == "no-break"
    assert evaluated, "no decomposition was evaluated; the closure is untested"


def test_fxr_g10_a_sub_tick_interval_is_not_evaluable_never_zero(
    example: Any
) -> None:
    """`FXR-G10` — a decomposition across an interval shorter than the tick
    spacing is `not-evaluable`, never zero. §F.1, TRAP 2.

    `TRD-W12-0235`'s corrected observation gap is 296 s against a 300 s series.
    A zero timing component there would say *the market did not move*, when the
    truth is *the series cannot see whether it did*.
    """
    served = serve(example, trades=[SUBTICK], scope=SUBTICK)
    row = served.rows[SUBTICK]
    d = row["decomposition"]
    assert row["verdict"] == "not-evaluable"
    assert d["reason"] == "interval-below-tick-spacing"
    assert d["timing_attributable_pips"] is None
    gap = Decimal(d["compared_gap_seconds"])
    assert 0 < gap < served.payload["comparison"]["tick_spacing_seconds"]


def test_fxr_g11_tick_staleness_is_carried_and_a_stale_tick_refuses(
    served: Any
) -> None:
    """`FXR-G11` — the staleness of the tick used is carried, and a stale tick
    yields `not-evaluable`. §F.1, TRAP 4.

    `TRD-W12-0124`'s nearest preceding tick is 20.0 hours old across the
    weekend gap. The staleness is in the payload because a consumer cannot
    otherwise tell a revaluation against a fresh tick from one against a tick
    from the previous trading day.
    """
    d = served.rows[STALE]["decomposition"]
    assert served.rows[STALE]["verdict"] == "not-evaluable"
    assert d["reason"] == "stale-tick"
    hours = Decimal(d["stale_seconds"]) / 3600
    assert abs(hours - Decimal(str(STALE_TICK_HOURS))) < 1

    for row in served.payload["reconciliations"]:
        if row["decomposition"]["state"] == "evaluated":
            assert "tick_staleness_seconds" in row["decomposition"]


def test_fxr_g12_every_variance_is_in_pips_at_the_declared_scale(
    served: Any, example: Any
) -> None:
    """`FXR-G12` — every variance is expressed in pips, and USD/JPY resolves at
    `0.01` while the others resolve at `0.0001`. §F.1, TRAP 5.

    **Asserted on the SERVED figure, not on the table.** An earlier version of
    this gate checked `pip_scale()` and the pair label, and stayed green while
    `Estate.pip` was sabotaged to return `0.0001` for everything — because it
    never exercised the lookup. A declaration nothing reads is documentation,
    not control. So the gate recomputes each served variance from the raw rates
    and the declared scale and requires them to match, which can only hold if
    the scale the product used is the scale the artifact declares.
    """
    declared = example["acquisition"].pip_scale()
    assert declared["USD/JPY"] == JPY_PIP
    assert {value for pair, value in declared.items() if pair != "USD/JPY"} == {
        MAJOR_PIP
    }
    estate = served.estate
    scales = set()
    for row in served.payload["reconciliations"]:
        if row["decomposition"]["state"] == "no-break":
            continue
        divergent = row["divergent_system"]
        other = next(
            system for group in row["agreement_groups"] if len(group) > 1
            for system in group
        )
        a = estate.at(row["trade_id"], divergent)
        b = estate.at(row["trade_id"], other)
        raw = abs(a.value_rate - b.value_rate)
        pip = declared[row["pair"]]
        scales.add(pip)
        expected = (raw / pip).quantize(Decimal("0.01"))
        assert Decimal(row["decomposition"]["total_pips"]) == expected, (
            f"{row['trade_id']} ({row['pair']}): served"
            f" {row['decomposition']['total_pips']} pips; the raw difference"
            f" {raw} at the declared scale {pip} is {expected}"
        )
        for key, value in row["decomposition"].items():
            if key.endswith("_pips") and value is not None:
                Decimal(value)

    assert scales == {JPY_PIP, MAJOR_PIP}, (
        f"the worked cases exercised only {scales}; a gate that never saw both"
        " scales could not tell a correct lookup from a constant"
    )
    assert served.payload["comparison"]["materiality_pips"]


def test_fxr_g13_disabling_the_alignment_changes_the_answer_and_the_address(
    served: Any, unaligned: Any
) -> None:
    """`FXR-G13` — `align_clocks=false` produces a different answer AND a
    different content address on the same trades and instant. §F.1.

    Both halves matter. A parameter that changed the address without changing
    the answer would be riding the request identity without reaching the
    computation; one that changed the answer without the address would make two
    different answers indistinguishable to a cache.
    """
    assert served.address != unaligned.address
    differing = [
        trade_id
        for trade_id in WORKED_CASES
        if served.rows[trade_id]["verdict"] != unaligned.rows[trade_id]["verdict"]
    ]
    assert differing, (
        "the clock correction changed no verdict; it is not reaching the"
        " comparison"
    )
    # And it is visible in the payload which question was asked.
    assert served.payload["comparison"]["align_clocks"] is True
    assert unaligned.payload["comparison"]["align_clocks"] is False
    for row in unaligned.payload["reconciliations"]:
        for system in row["systems"]:
            assert system["corrected_at"] is None, (
                "an unaligned answer must not carry a corrected instant; it"
                " would imply a correction the caller declined"
            )


def test_fxr_g14_the_series_key_is_a_first_class_claim_attribute(
    example: Any, served: Any
) -> None:
    """`FXR-G14` — the λ_c row declares `freshness_over: leading-edge` with
    `series_key_attribute: system_name`, and that attribute is a first-class
    CLAIM attribute rather than a key inside a serialized blob. §F.1.

    Structural on both halves. The scorer reads a series key off the claim; a
    key present only inside `payload_json` resolves to `None`, all three systems
    collapse into one series, and `F` silently measures something else.
    """
    config = example["deployment"].config()
    row = config["half_life"]["fxr_observation"]
    assert row["freshness_over"] == "leading-edge"
    assert row["series_key_attribute"] == "system_name"
    assert row["decay_basis"] == "valid-from"

    rules = {
        rule["match_key"]: rule
        for rule in config["resolution"]["entity_rules"]
    }
    assert "system_name" in rules["observation_node"]["attribute_keys"], (
        "`system_name` is not an admitted claim attribute; the scorer would"
        " read it as None and every system would share one series"
    )

    # And the envelope actually carries it at the top level, not only inside
    # the JSON body.
    edges, nodes = example["deployment"].envelopes(
        served.estate, tenant_id="t", at=AS_OF
    )
    observations = [
        node for node in nodes if node.raw_payload["node_kind"] == "observation"
    ]
    assert observations
    for node in observations:
        assert node.raw_payload["system_name"] in ("trading", "settlement", "risk")


def test_fxr_g15_a_trade_whose_systems_agree_serves_an_explicit_no_break(
    example: Any
) -> None:
    """`FXR-G15` — a trade whose systems all agree serves with an explicit
    `no-break` verdict. §F.1, §D.5.

    Not an empty payload and not an omission. A reconciliation that dropped
    clean trades would make *"we found nothing"* and *"we did not look"*
    indistinguishable.
    """
    served = serve(example, trades=[CLEAN], scope=CLEAN)
    row = served.rows[CLEAN]
    assert row["verdict"] == "no-break"
    assert row["divergent_system"] is None
    assert row["decomposition"]["state"] == "no-break"
    assert len(row["agreement_groups"]) == 1
    assert served.payload["observations"] == 1


def test_fxr_g16_the_four_axes_are_request_fields(example: Any) -> None:
    """`FXR-G16` — the four §6.3 axes are `ProductRequest` FIELDS, absent from
    `parameters`. §F.1.

    A subject demoted into the parameter bag is a subject the content address
    and the replay record no longer resolve against.
    """
    asked = example["deployment"].request(
        trades=WORKED_CASES, scope=SCOPE, asked_at=AS_OF
    )
    for axis in ("subject", "intent", "freshness", "asked_at"):
        assert getattr(asked, axis) is not None
        assert axis not in asked.parameters
    assert asked.subject == SCOPE

    # A single-trade request is ABOUT that trade, and a multi-trade request
    # refuses to promote one of its members to stand for the set.
    single = example["deployment"].request(
        trades=[WORKED], asked_at=AS_OF
    )
    assert single.subject == WORKED
    with pytest.raises(ValueError, match="scope"):
        example["deployment"].request(trades=WORKED_CASES, asked_at=AS_OF)


def test_fxr_g17_no_notional_figure_appears_anywhere(served: Any) -> None:
    """`FXR-G17` — no notional figure appears anywhere in the payload; the band
    is carried as a band. §F.1, `CP12-F-08`.

    Part 43 caps and bands large notionals to protect participant anonymity.
    Reconstructing a number from a band would undo that, and this product
    computes nothing that would need one — every variance it reports is in
    pips, which is a property of the rate and not of the size.
    """
    for row in served.payload["reconciliations"]:
        band = row["notional_band"]
        assert isinstance(band, str) and "-" in band
        assert "notional" not in {
            key for key in row if key != "notional_band"
        }
    blob = json.dumps(served.payload, default=str)
    for forbidden in ("notional_usd", "notional_amount", "notional_value"):
        assert forbidden not in blob


def test_fxr_g18_the_absent_legs_are_named_absent_not_empty(served: Any) -> None:
    """`FXR-G18` — the payload claims no settlement, netting or ISO 20022
    content, and where it names the leg at all it names it ABSENT rather than
    empty or zero. §F.1, `CP12-F-01`.

    A predicate nothing asserts is not a predicate asserting nothing. Measured,
    `settlesVia` and `netsWith` are absent from this estate's vocabulary — not
    present with a count of zero.
    """
    legs = served.payload["absent_legs"]
    assert set(legs) >= {"settlesVia", "netsWith", "settlement_instruction"}
    assert set(legs.values()) == {"absent"}
    for value in legs.values():
        assert value not in (0, "0", [], {}, None)


def test_fxr_g19_no_figure_is_served_twice(served: Any) -> None:
    """`FXR-G19` — the payload carries no second copy of `D_c`, the content
    address or the policy versions. §F.1.

    Two copies of one figure is two things that can disagree, and the
    disagreement would be invisible: the envelope carries the authoritative
    copy, so a payload copy is a stale duplicate waiting to happen.
    """
    def keys(node: Any) -> Iterator[str]:
        """Every KEY in the payload, at any depth.

        Keys, and deliberately not a substring grep over the serialized blob:
        `d_c` is a substring of `estate_designated_class`, and a grep flagged
        the correct payload. cp-11's gate 20 failed the same way — an
        instrument that reads text rather than structure trips on text that is
        simply about its own subject.
        """
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    present = {key.lower() for key in keys(served.payload)}
    for forbidden in (
        "debt", "context_debt", "d_c", "payload_hash", "content_address",
        "policy_bundle_version", "policy_bundle_versions", "expires_at",
        "ttl_seconds",
    ):
        assert forbidden not in present, (
            f"the payload carries a {forbidden!r} key, which the envelope"
            " already carries authoritatively; two copies of one figure is two"
            " things that can disagree"
        )


def test_fxr_g20_an_unknown_trade_refuses_distinctly_from_no_break(
    example: Any
) -> None:
    """`FXR-G20` — an unknown trade refuses distinctly from a trade with no
    break. §F.1, §D.5.

    A request error and a fact about the world. Collapsing them would let
    *"that trade does not exist"* read as *"that trade reconciles cleanly"*,
    which is the more dangerous of the two answers to get wrong.
    """
    acquisition = example["acquisition"]
    with pytest.raises(acquisition.UnknownTrade):
        serve(example, trades=["TRD-W12-NO-SUCH-TRADE"], scope="missing")

    clean = serve(example, trades=[CLEAN], scope=CLEAN)
    assert clean.rows[CLEAN]["verdict"] == "no-break"


def test_fxr_g21_the_classification_vocabulary_is_exactly_three(
    served: Any, population: Any, example: Any
) -> None:
    """`FXR-G21` — the classification vocabulary is exactly `timing`,
    `genuine`, `not-evaluable`; the two classes the article names but the
    estate cannot evidence are absent. §F.1, `CP12-F-03`.

    Structural, and read off the SERVED payload rather than grepped out of
    source text — cp-11's gate 20 went red against correct code because it
    grepped, and tripped on the docstring explaining its own rule.

    `no-break` is not a fourth class: it says there is nothing to classify.
    """
    projection = example["projection"]
    assert projection.CLASSIFICATIONS == ("timing", "genuine", "not-evaluable")
    assert served.payload["comparison"]["classification_vocabulary"] == list(
        projection.CLASSIFICATIONS
    )
    served_verdicts = {
        row["verdict"] for row in population.payload["reconciliations"]
    }
    assert served_verdicts <= set(projection.VERDICTS)
    assert not served_verdicts & {"amendment-lag", "revaluation-basis"}
    assert set(population.payload["verdict_counts"]) == set(projection.VERDICTS)


# =========================================================================
# THE SIX TRAP GATES — `FXR-G22` … `FXR-G27`.
#
# Each one builds the DEFECTIVE mechanism the trap names, runs it on the same
# data, and asserts the two answers DIFFER. §F.1a:
#
#   > A trap gate must DISTINGUISH the wrong mechanism from the right one. Two
#   > answers coinciding is not evidence.
#
# That is not a stylistic preference. cp-10's trap gate 23 and cp-11's trap gate 27
# were each GREEN under their own sabotage, because each asserted only where
# the correct and defective mechanisms happened to produce the same value.
# =========================================================================


def _pairwise_count(estate: Any, projection: Any, *, threshold: Decimal) -> int:
    """THE DEFECTIVE MECHANISM of TRAP 1, built here so it can be measured.

    The obvious reading: three systems give three pairs, so count the pairs
    that disagree materially. It is wrong because when settlement disagrees
    with trading it also disagrees with risk, so one divergence is reported
    twice — and a middle office told it has 120 breaks staffs for twice the
    work.
    """
    import itertools

    count = 0
    for trade in estate.trades:
        pip = estate.pip(trade.pair)
        seen = {
            system: estate.at(trade.trade_id, system)
            for system in projection.SYSTEMS
            if estate.at(trade.trade_id, system) is not None
        }
        for a, b in itertools.combinations(sorted(seen), 2):
            if abs(seen[a].value_rate - seen[b].value_rate) / pip >= threshold:
                count += 1
    return count


def test_fxr_g22_the_unit_is_the_trade_and_the_pairwise_count_doubles_it(
    population: Any, example: Any
) -> None:
    """`FXR-G22` — TRAP 1. The product reports one observation per break trade;
    a pairwise implementation reports twice as many. §F.1a.

    **The divergence is exact and systematic.** Every one of the designated
    break trades partitions two-against-one — 60 of 60, measured, with no other
    shape present — so the pairwise count is precisely `2.00x` the number of
    underlying divergences. The gate asserts the product's count, the defective
    count, and the ratio between them, then asserts no payload field lets a
    consumer arrive at the larger number by counting.
    """
    projection = example["projection"]
    trades = population.payload["reconciliations"]
    assert len(trades) == BREAK_TRADES
    assert population.payload["observations"] == BREAK_TRADES

    threshold = Decimal(population.payload["comparison"]["materiality_pips"])
    doubled = _pairwise_count(
        population.estate, projection, threshold=Decimal("0.5")
    )
    assert doubled == PAIRWISE_RATIO * BREAK_TRADES, (
        f"the pairwise mechanism produced {doubled} comparisons over"
        f" {BREAK_TRADES} trades; TRAP 1's measured ratio is"
        f" {PAIRWISE_RATIO}.00x"
    )
    assert doubled != population.payload["observations"], (
        "the two mechanisms agree, so this gate proves nothing"
    )

    # And the pairwise number is not reachable by counting anything served.
    blob = json.dumps(population.payload, default=str)
    assert not (example["deployment"].PAIRWISE_KEYS & set(population.payload))
    for row in trades:
        assert isinstance(row["verdict"], str)
        assert len(row["agreement_groups"]) <= 3
    assert str(doubled) not in json.dumps(population.payload["verdict_counts"])
    del blob, threshold


def test_fxr_g23_latest_state_hides_breaks_that_amendment_zero_reports(
    example: Any
) -> None:
    """`FXR-G23` — TRAP 3 and TRAP 6. Asserted on the trades that are material
    at amendment 0 and immaterial at latest. §F.1a, §A.2.

    **Both answers are required, so the two mechanisms cannot be confused for
    one.** At `compare_at=amendment-0` the product reports a break; a
    latest-state implementation reports none — because the amendment
    reconciled the two systems and current state has forgotten the break
    happened.

    **It is NOT asserted on a trade with no amendment**, where both readings
    agree and the gate would prove nothing. Every trade in the divergence set
    is checked to carry an amendment above 0.
    """
    trades = break_population(example)
    at_zero = serve(example, trades=trades, scope="w12-g23-amendment-0")
    at_latest = serve(
        example, trades=trades, scope="w12-g23-latest", compare_at="latest"
    )
    hidden = [
        trade_id
        for trade_id in trades
        if at_zero.rows[trade_id]["verdict"] != "no-break"
        and at_latest.rows[trade_id]["verdict"] == "no-break"
    ]
    assert hidden, (
        "no break is hidden by latest state, so the two mechanisms agree and"
        " this gate proves nothing"
    )
    assert WORKED in hidden, (
        f"{WORKED} is §A.3's worked case and must be among the hidden breaks"
    )
    for trade_id in hidden:
        amendments = {
            row["amendment_seq"] for row in at_latest.rows[trade_id]["systems"]
        }
        assert max(amendments) > 0, (
            f"{trade_id} carries no amendment; at a trade with none the two"
            " readings coincide and the gate would be vacuous (§F.1a)"
        )
        assert {row["amendment_seq"] for row in at_zero.rows[trade_id]["systems"]} == {0}

    # And the comparison instant in force is carried, so a consumer can tell
    # which question was answered (§B.2a).
    assert at_zero.payload["comparison"]["compare_at"] == "amendment-0"
    assert at_latest.payload["comparison"]["compare_at"] == "latest"
    assert at_zero.address != at_latest.address


def test_fxr_g24_the_corrected_instant_reaches_no_fabric_temporal_field(
    example: Any
) -> None:
    """`FXR-G24` — TRAP 6's second half. The λ_c path ages an observation
    against the RECORDED instant; the corrected instant reaches no
    `valid_from`, no `observed_at` and no Context Debt term. §F.1a, §B.4.

    **Asserted where the two instants differ** — on `risk` (offset −112 s) and
    `settlement` (offset +47 s), never on `trading`, whose offset is `0` and
    where recorded and corrected are the same value. A gate asserted only on
    `trading` would pass against a fabric that had swallowed the correction
    whole.

    Proved through the REAL L2 path: boot, ingest, read the claims back out of
    L3, and compare against the observations the estate returned.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.deployment import load_config_and_boot

    deployment = example["deployment"]
    asked = deployment.request(trades=[WORKED], asked_at=AS_OF)
    estate = deployment.acquire_for(asked)

    # Keyed on `(system, amendment)` and NOT on a URI this test constructs: L2
    # mints its own `fxr_observation://<sha256>`, so a lookup by the
    # deployment's URI finds nothing and the gate passes over an empty set
    # (`D-IMPL-316`'s lesson, and cp-11 learned it the same way).
    recorded_by_key = {}
    corrected_by_key = {}
    for system in ("settlement", "risk"):
        for observation in estate.observations[(WORKED, system)]:
            key = (system, observation.amendment_seq)
            recorded_by_key[key] = observation.recorded_at
            corrected_by_key[key] = observation.corrected_at
    assert recorded_by_key, "no skewed-clock observation reached the gate"
    assert all(
        recorded_by_key[key] != corrected_by_key[key] for key in recorded_by_key
    ), (
        "recorded and corrected coincide on every observation under test; the"
        " estate records +47 s for settlement and -112 s for risk, so this"
        " gate must be asserted where they differ (§F.1a)"
    )

    with tempfile.TemporaryDirectory(prefix="cp-12-g24-") as scratch:
        booted = load_config_and_boot(
            EXAMPLE / "ccf_config.yaml",
            registry=ControlPlaneRegistry(),
            connection=deployment.connection(root=pathlib.Path(scratch)),
        )
        try:
            deployment.ingest(booted, estate, at=AS_OF)
            view = booted.handle.reader.as_of(
                tenant_id=booted.tenant_id, at=AS_OF
            )
            checked = 0
            for record in view.entities:
                claim = record.claim
                if claim.entity_class != "fxr_observation":
                    continue
                body = json.loads(claim.attributes["payload_json"])
                key = (claim.attributes["system_name"], body["amendment_seq"])
                if key not in recorded_by_key:
                    continue
                checked += 1
                assert claim.valid_from == recorded_by_key[key], (
                    f"{key}: valid_from is {claim.valid_from}, not the instant"
                    f" the system recorded ({recorded_by_key[key]})"
                )
                assert claim.valid_from != corrected_by_key[key]
                assert claim.observed_at != corrected_by_key[key], (
                    f"{key}: the corrected instant reached `observed_at`; the"
                    " fabric's freshness figure would become a function of this"
                    " product's own alignment model"
                )
            assert checked == len(recorded_by_key), (
                f"{checked} of {len(recorded_by_key)} skewed observations"
                " reached L3; a gate that ranged over fewer would pass over a"
                " set it never found"
            )
        finally:
            booted.handle.close()


def test_fxr_g25_a_residual_implementation_answers_where_the_product_refuses(
    population: Any, example: Any
) -> None:
    """`FXR-G25` — TRAP 2. Asserted on every break whose corrected observation
    gap is SHORTER than the tick spacing. §F.1a.

    **The correct product returns `not-evaluable`; a residual-magnitude
    implementation returns a confident verdict on every one of them.** Both are
    computed here on the same trades, and the gate asserts they differ — a gate
    that checked only the correct answer would pass against a product that had
    never had the rule.

    **Why the refusal is right, stated as arithmetic rather than as caution.**
    The tick series resolves to 300 s. Where the interval is shorter, the two
    ticks the revaluation uses are either the SAME tick — so the attributed
    market move is zero, which says *the market did not move* when the truth is
    *the series cannot see whether it did* — or ADJACENT ticks, so the
    attributed move spans a full bucket and is credited to a shorter interval.
    Both are artifacts of where the bucket boundaries fell, and the gate
    asserts that one of the two holds on every case it ranges over.
    """
    projection = example["projection"]
    estate = population.estate
    spacing = Decimal(population.payload["comparison"]["tick_spacing_seconds"])
    threshold = Decimal(population.payload["comparison"]["materiality_pips"])

    subtick = [
        row for row in population.payload["reconciliations"]
        if row["decomposition"]["state"] == "not-evaluable"
        and row["decomposition"]["reason"] == "interval-below-tick-spacing"
    ]
    assert subtick, (
        "no break falls below the tick spacing, so there is nothing for the two"
        " mechanisms to diverge on"
    )

    collisions = 0
    for row in subtick:
        trade_id = row["trade_id"]
        gap = Decimal(row["decomposition"]["compared_gap_seconds"])
        assert 0 < gap < spacing

        trade = next(t for t in estate.trades if t.trade_id == trade_id)
        pip = estate.pip(trade.pair)
        divergent = row["divergent_system"]
        other = next(
            system for group in row["agreement_groups"] if len(group) > 1
            for system in group
        )
        a, b = estate.at(trade_id, divergent), estate.at(trade_id, other)
        total = abs(a.value_rate - b.value_rate) / pip
        ta = estate.tick_at(trade.pair, a.corrected_at)
        tb = estate.tick_at(trade.pair, b.corrected_at)

        # THE DEFECTIVE MECHANISM: revalue at each corrected instant, subtract,
        # and classify on what is left — with no floor at all.
        naive_timing = abs(ta.rate - tb.rate) / pip
        naive_residual = total - naive_timing
        naive_verdict = "genuine" if abs(naive_residual) >= threshold else "timing"

        assert naive_verdict in projection.CLASSIFICATIONS
        assert naive_verdict != row["verdict"], (
            f"{trade_id}: the residual mechanism answered {naive_verdict!r} and"
            f" the product answered {row['verdict']!r}; if these agreed the"
            " gate would be asserting a coincidence (§F.1a)"
        )

        # And the revaluation is demonstrably an artifact of the bucketing.
        span = abs((ta.obs_ts - tb.obs_ts).total_seconds())
        if span == 0:
            collisions += 1
            assert naive_timing == 0, (
                f"{trade_id}: one tick serves both instants, so a revaluation"
                " must attribute exactly zero market move"
            )
        else:
            assert Decimal(str(span)) >= spacing, (
                f"{trade_id}: the ticks are {span}s apart, below the series'"
                " own resolution, which should be impossible"
            )
            assert Decimal(str(span)) > gap, (
                f"{trade_id}: the attributed move spans {span}s and is credited"
                f" to a {gap}s interval"
            )
    assert collisions, (
        "no sub-tick break put both instants in one bucket, so the zero-timing"
        " artifact TRAP 2 names is not exercised"
    )


def test_fxr_g26_an_unnormalised_jpy_variance_reads_a_hundred_times_small(
    served: Any, example: Any
) -> None:
    """`FXR-G26` — TRAP 5. Asserted on a USD/JPY break, where the pip is `0.01`.
    §F.1a.

    **Normalised it reports pips above the threshold; unnormalised it reads
    100x smaller and passes every threshold.** Both figures are computed here
    and the gate asserts the defective one falls BELOW the materiality
    threshold while the correct one is above it — that is the divergence, and
    it is why the gate must not be asserted on a `0.0001` pair, where the two
    differ by a factor the thresholds may not separate.
    """
    estate = served.estate
    trade = next(t for t in estate.trades if t.trade_id == JPY)
    assert trade.pair == "USD/JPY"
    assert estate.pip("USD/JPY") == JPY_PIP
    assert estate.pip("EUR/USD") == MAJOR_PIP

    row = served.rows[JPY]
    divergent = row["divergent_system"]
    other = next(
        system for group in row["agreement_groups"] if len(group) > 1
        for system in group
    )
    a, b = estate.at(JPY, divergent), estate.at(JPY, other)
    raw = abs(a.value_rate - b.value_rate)

    # THE CORRECT MECHANISM and THE DEFECTIVE ONE, side by side. The defect is
    # comparing the raw rate difference as though it were already in pips,
    # which is what happens the moment a pair's scale is not looked up.
    correct = raw / JPY_PIP
    defective = raw
    threshold = Decimal(served.payload["comparison"]["materiality_pips"])

    assert correct == Decimal(row["decomposition"]["total_pips"]).quantize(
        Decimal("0.01")
    ) or abs(correct - Decimal(row["decomposition"]["total_pips"])) < Decimal("0.01")
    assert correct >= threshold, (
        "the correct normalisation does not clear the threshold on this trade,"
        " so there is no divergence to assert"
    )
    assert defective < threshold, (
        f"the unnormalised difference {defective} already clears the threshold;"
        " the 100x scale error would be invisible here and the gate would be"
        " asserting a coincidence (§F.1a)"
    )
    assert correct / defective == 100, (
        "USD/JPY's pip is 0.01 and the default is 0.0001, so the scale error is"
        f" exactly 100x; measured {correct / defective}x"
    )
    del example


def test_fxr_g27_a_stale_weekend_tick_produces_a_number_with_no_meaning(
    served: Any, example: Any
) -> None:
    """`FXR-G27` — TRAP 4. Asserted on the break whose nearest preceding tick is
    20.0 hours old. §F.1a.

    **The correct product returns `not-evaluable` and carries the staleness; a
    naive implementation returns a large negative residual on a raw variance
    of about 8 pips.** The two answers are not close, which is what makes this
    gate cheap and decisive — and both are computed here rather than one being
    asserted and the other assumed.
    """
    projection = example["projection"]
    row = served.rows[STALE]
    assert row["verdict"] == "not-evaluable"
    assert row["decomposition"]["reason"] == "stale-tick"

    estate = served.estate
    trade = next(t for t in estate.trades if t.trade_id == STALE)
    pip = estate.pip(trade.pair)
    divergent = row["divergent_system"]
    other = next(
        system for group in row["agreement_groups"] if len(group) > 1
        for system in group
    )
    a, b = estate.at(STALE, divergent), estate.at(STALE, other)
    total = abs(a.value_rate - b.value_rate) / pip
    ta = estate.tick_at(trade.pair, a.corrected_at)
    tb = estate.tick_at(trade.pair, b.corrected_at)
    naive_residual = total - abs(ta.rate - tb.rate) / pip

    staleness = max(
        (a.corrected_at - ta.obs_ts).total_seconds(),
        (b.corrected_at - tb.obs_ts).total_seconds(),
    )
    assert staleness / 3600 > 2 * STALE_TICK_HOURS / 3, (
        f"the tick under this break is only {staleness / 3600:.1f} h old; the"
        " weekend gap this gate is about is not present"
    )
    assert abs(naive_residual) > 10 * total, (
        f"the naive residual is {naive_residual} against a raw variance of"
        f" {total}; if the two were close the gate would be asserting a"
        " coincidence (§F.1a)"
    )
    assert row["decomposition"]["residual_pips"] is None, (
        "the product reported a residual against a 20-hour-old tick"
    )
    assert projection.CLASSIFICATIONS
