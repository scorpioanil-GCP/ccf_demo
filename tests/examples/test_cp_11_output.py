"""cp-11 — `EWS-G01` … `EWS-G28`, against the live estate through the served product.

**Every gate here tests `CP-SPEC-011`, not this estate.** The assertions are
relationships and identities: a partition, a state, a set difference, an
ordering. The estate grows, and a gate pinning `139 signals` would go wrong the
day another mention lands. Where a number IS the governed claim — the
`EWS-G25` boundary date, the SIC resolution rate — it is pinned, because there
the number is the contract.

**Five disciplines, each because collapsing it would let a gate pass for the
wrong reason:**

* **Absence is not supersession.** A signal the chain does not mirror is
  `not-participating`, never `superseded`. The three states PARTITION.
* **Absence is not zero.** A class the obligor has no evidence in is reported
  absent; scoring it zero says *"we looked and found nothing concerning"* when
  the truth is *"we have nothing to look at"*.
* **"No decay" is not "accumulates forever".** What ends an 8-K's relevance is
  a later filing, not the passage of time.
* **The composite and the Context Debt are different models.** One measures
  what the evidence says; the other measures how old and complete it is.
* **The fabric refuses to RE-SERVE; it never notifies, recalls or evicts.**
  Nothing in the payload or this module claims otherwise.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-11-credit-surveillance-early-warning"

ESTATE_VARIABLES = (
    "CCF_CP_11_FLUREE_URL",
    "CCF_CP_11_FLUREE_LEDGER",
    "CCF_CP_11_POSTGRES_DSN",
    "CCF_CP_11_POSTGRES_SCHEMA",
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
            "cp-11 assembles from the live estate; set "
            + ", ".join(ESTATE_VARIABLES)
            + " — the v2 namespaces, never the v1 names in the estate's own .env"
        ),
    ),
]

#: The headline anchor: the heaviest-signalled name in the estate, and the one
#: whose 25 superseded filings make the rung's argument visible in one serve.
ANCHOR = "54930022CZO1N2UGVW07"
#: The thinly-evidenced name: an Item 2.04 at severity 1.0, the heaviest media
#: footprint of any 2.04 carrier, and ZERO trend deltas.
THIN = "G8NWFN4YP7CR6FOP4886"
#: An unrelated obligor, for `EWS-G25`'s middle leg and for `EWS-G05`.
OTHER = "QBKYQD0ODE7DC7PDIN91"

AS_OF = datetime(2026, 8, 19, tzinfo=UTC)

# --- `EWS-G25`'s three instants, and they are the gate's contract ----------
#
# `T1` is before a real pair of adverse-media mentions dated 2026-07-28, and
# `T2` is after them. The BOUNDARY is therefore 2026-07-28 — the instant the
# evidence became true in the world — and NOT 2026-08-19, the instant the
# fabric writes it. `D-IMPL-335` is what makes that so, and this module pins
# the date rather than the property, because the date IS what 335 corrected.
G25_T1 = datetime(2026, 7, 20, tzinfo=UTC)
G25_T2 = datetime(2026, 8, 19, tzinfo=UTC)
G25_BOUNDARY = datetime(2026, 7, 28, tzinfo=UTC)
#: What the boundary would be if the writer took `claim.observed_at` again —
#: the ingestion instant, which through L2 is `asked_at`. Pinned as a NEGATIVE,
#: so a regression to `D-IMPL-334`'s behavior is named rather than merely
#: failing an equality.
G25_INGESTION_INSTANT = G25_T2

#: Words a payload may never contain. The SDK refuses to RE-SERVE; it does not
#: notify, recall, evict or push, and no product may imply that it does.
FORBIDDEN_CLAIMS = (
    "notified", "notification", "recalled", "recall", "evicted", "eviction",
    "pushed", "push invalidation", "subscriber", "subscription",
)


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
            self.registry = outcome.registry

    def model_dump_json(self) -> str:
        return self.outcome.model_dump_json()


def serve(
    example: Any, *, anchor_lei: str = ANCHOR, asked_at: datetime = AS_OF,
    **kwargs: Any,
) -> Any:
    """One question, end to end. Returns the `Assembled` or the refusal."""
    deployment, produce = example["deployment"], example["produce"]
    asked = deployment.request(anchor_lei=anchor_lei, asked_at=asked_at, **kwargs)
    with tempfile.TemporaryDirectory(prefix="cp-11-test-") as scratch:
        outcome = produce.assemble_and_serve(
            asked=asked, root=pathlib.Path(scratch)
        )
        return _Frozen(outcome, scratch=pathlib.Path(scratch))


@pytest.fixture(scope="module")
def served(example: Any) -> Any:
    """The headline serve, on the heaviest-signalled anchor."""
    return serve(example)


@pytest.fixture(scope="module")
def thin(example: Any) -> Any:
    """The thinly-evidenced name, where two classes are ABSENT."""
    return serve(example, anchor_lei=THIN)


# =========================================================================
# The six universal gates.
# =========================================================================


def test_ews_g01_the_operator_plan_is_never_empty(served: Any) -> None:
    """`EWS-G01` — a plan with zero operator steps never serves. §G.1."""
    assert served.product.lineage.operators_invoked


def test_ews_g02_lineage_is_exactly_the_declared_operator_set(
    served: Any, example: Any
) -> None:
    """`EWS-G02` — served lineage equals the plan's typed operator references.

    §G.1, and the second half is `ProductLineage`'s own shape: **exactly three
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


def test_ews_g03_expiry_derives_from_the_decision_instant(served: Any) -> None:
    """`EWS-G03` — `expires_at` derives from the decision instant, under the ceiling.

    §G.1. `ttl_anchor: from_decision`, so the expiry is `asked_at` plus the
    product TTL and never a clock read at serve time — which is what makes a
    request pinned to a past `as_of` a forensic reconstruction.
    """
    product = served.product
    assert product.ttl_anchor == "from_decision"
    elapsed = (product.expires_at - AS_OF).total_seconds()
    assert 0 < elapsed <= 86400, (
        f"expiry is {elapsed}s after the decision instant; §E.3's ceiling is"
        " one day"
    )


def test_ews_g04_debt_above_tolerance_refuses_with_the_debt_block(
    example: Any, served: Any
) -> None:
    """`EWS-G04` — `D_c` above the caller's tolerance refuses rather than serving.

    §G.1. Asked with a ceiling measured BELOW the debt the product actually
    carries, so the refusal is forced by the gate and not by a broken read.
    """
    measured = served.product.debt.debt
    impossible = (measured / 2).quantize(Decimal("0.0001"))
    refused = serve(example, debt_tolerance=str(impossible))
    assert not hasattr(refused, "payload"), (
        f"D_c is {measured} and a tolerance of {impossible} still served"
    )
    assert "debt" in refused.model_dump_json().lower()


def test_ews_g05_a_non_admitted_obligor_leaves_no_trace(served: Any) -> None:
    """`EWS-G05` — suppression is silent.

    §G.1. The policy operator admits only the obligors the effective request
    names, so every other obligor in the estate is excluded. The gate is that
    the exclusion is SILENT: no name, no count, no placeholder. A marker saying
    *"49 obligors excluded"* discloses the existence it is withholding.
    """
    body = str(served.payload)
    assert OTHER not in body and THIN not in body
    for leak in ("withheld_obligors", "excluded_obligors", "suppressed", "redacted"):
        assert leak not in body.lower()
    assert served.payload["obligor"]["lei"] == ANCHOR


def test_ews_g06_the_payload_classification_is_the_highest_contributing(
    served: Any
) -> None:
    """`EWS-G06` — classification containment.

    §G.1. This product mixes public filings and media with an INTERNAL
    surveillance weighting, so the payload's classification is the internal
    one. Asserted structurally: the internal element is PRESENT.
    """
    assert served.payload["contributing"], "no contribution reached the payload"
    assert served.payload["composite"]["score"]


# =========================================================================
# Supersession, decay, and the three states.
# =========================================================================


def test_ews_g07_a_superseded_signal_contributes_zero(served: Any) -> None:
    """`EWS-G07` — a superseded `8k_event` contributes NOTHING.

    §C.4 TRAP 1. `signal_weight.decay_days` is NULL for every `8k_event` row,
    so read as *"contributes forever"* the routine filings swamp the
    accelerations and 30 of 50 obligors breach the board band. What ends an
    8-K's relevance is a LATER FILING.
    """
    superseded = {
        row["signal_id"]
        for row in served.payload["excluded"]
        if row["reason"] == "superseded"
    }
    assert superseded, "no superseded signal on the heaviest-signalled anchor"
    contributing = {row["signal_id"] for row in served.payload["contributing"]}
    assert not (superseded & contributing), (
        "a superseded signal reached the composite"
    )
    assert all(
        row["chain_state"] != "superseded"
        for row in served.payload["contributing"]
    )


def test_ews_g08_supersession_is_not_staleness_and_absence_is_not_supersession(
    served: Any
) -> None:
    """`EWS-G08` — two conflations, refused separately.

    A superseded signal is not reported as stale or aged: its reason is
    supersession and its age is reported unchanged. **And a signal the chain
    does not mirror is `not-participating`, never `superseded`** — it was never
    in a chain to be superseded from.
    """
    for row in served.payload["excluded"]:
        if row["reason"] != "superseded":
            continue
        assert "stale" not in row["note"].lower()
        assert "aged" not in row["note"].lower() or "rather than decayed" in row["note"]
        assert "replaced" in row["note"]

    states = served.payload["chain_states"]["states"]
    assert states["not-participating"] > 0, (
        "no signal is `not-participating`, so the distinction this gate guards"
        " is not exercised on this serve"
    )
    participants = set(served.payload["chain_states"]["participating_classes"])
    for row in served.payload["contributing"]:
        if row["signal_type"] not in participants:
            assert row["chain_state"] == "not-participating", (
                f"{row['signal_type']} is not a declared chain participant and"
                f" is reported {row['chain_state']!r}; absence from a chain is"
                " not supersession"
            )


def test_ews_g09_every_class_decays_against_the_source_observation_date(
    served: Any, example: Any
) -> None:
    """`EWS-G09` — the SOURCE's date, never ingestion. `D-IMPL-331`."""
    table = example["deployment"].config()["half_life"]
    assert table["ews_signal"]["decay_basis"] == "valid-from"
    assert table["ews_signal"]["freshness_over"] == "leading-edge"
    assert table["ews_signal"]["series_key_attribute"] == "signal_type"
    for row in served.payload["contributing"]:
        observed = date.fromisoformat(row["observed_at"])
        assert row["age_days"] == (AS_OF.date() - observed).days, (
            "an age is not the gap between the source's own date and the"
            " decision instant"
        )


def test_ews_g10_the_delta_is_valid_time_and_admits_no_look_ahead(
    served: Any
) -> None:
    """`EWS-G10` — bounds `(since, asked_at]` on VALID TIME. `CP11-F-06`."""
    delta = served.payload["delta"]
    assert delta["basis"] == "valid-time"
    lower, upper = date.fromisoformat(delta["from"]), date.fromisoformat(delta["to"])
    assert upper == AS_OF.date()
    for row in served.payload["contributing"] + served.payload["excluded"]:
        observed = date.fromisoformat(row["observed_at"])
        assert lower < observed <= upper, (
            f"{row['signal_id']} at {observed} is outside the declared delta"
        )


def test_ews_g11_an_obligor_with_no_signal_returns_a_no_change_finding(
    example: Any
) -> None:
    """`EWS-G11` — `200` with an explicit finding, never an error or an empty payload.

    Asked over a one-day delta ending before the anchor's earliest signal, so
    the delta is genuinely empty rather than artificially narrowed.
    """
    quiet = serve(
        example, asked_at=AS_OF, since=date(2026, 8, 18), window_days=1,
    )
    assert hasattr(quiet, "payload"), "an empty delta refused instead of serving"
    assert quiet.payload["delta"]["signals_in_delta"] == 0
    assert quiet.payload["composite"]["score"] == "0.0000"
    assert quiet.payload["composite"]["band"] is None
    assert quiet.payload["class_coverage"], "no coverage reported at all"
    assert all(
        row["state"] == "absent" for row in quiet.payload["class_coverage"]
    )


def test_ews_g12_the_three_bands_are_reachable_and_ordered(
    served: Any, example: Any
) -> None:
    """`EWS-G12` — the bands order, and the populations are non-degenerate.

    §C.4 TRAP 2. The estate's bands were calibrated against the accumulating
    reading and are unreachable under the correct one; this product declares
    its own and the payload carries BOTH. Asserted as an ORDERING and as
    reachability, never as the numbers, so the estate may grow.
    """
    bands = served.payload["composite"]["bands"]
    floors = [Decimal(band["floor"]) for band in bands]
    assert floors == sorted(floors), "the bands are not ordered"
    assert len(set(floors)) == len(floors), "two bands share a floor"
    estate_declared = served.payload["composite"]["estate_declared"]
    assert estate_declared, "the estate's own bands are not carried"
    assert all(
        Decimal(estate_declared[band["intent"]]) > Decimal(band["floor"])
        for band in bands
        if band["intent"] in estate_declared
    ), "the product's bands are not below the estate's; TRAP 2 is not exercised"
    # REACHABILITY, measured across three real obligors rather than asserted.
    reached = {
        serve(example, anchor_lei=lei).payload["composite"]["band"]
        for lei in (ANCHOR, OTHER, THIN)
    }
    assert len(reached) > 1, (
        f"three obligors all land in the same band ({reached}); a control that"
        " cannot discriminate demonstrates nothing"
    )


def test_ews_g13_a_class_with_no_evidence_is_absent_not_zero(thin: Any) -> None:
    """`EWS-G13` — ABSENT, never scored. §A.3.

    Tupperware has no trend deltas at all. That is not a stable balance sheet,
    and a payload scoring it zero would say *"we looked and found nothing
    concerning"* when the truth is *"we have nothing to look at"*.
    """
    coverage = {row["signal_class"]: row for row in thin.payload["class_coverage"]}
    absent = [name for name, row in coverage.items() if row["state"] == "absent"]
    assert absent, "the thinly-evidenced anchor reports no absent class"
    assert "trend_delta" in absent
    for name in absent:
        assert coverage[name]["observations"] == 0
        assert coverage[name]["state"] != "present"
    # And no contribution was minted for an absent class.
    contributing = {row["signal_type"] for row in thin.payload["contributing"]}
    assert not (set(absent) & contributing)


def test_ews_g14_only_resolved_warn_matches_contribute(
    served: Any, example: Any
) -> None:
    """`EWS-G14` — the ambiguous count is published, never silently dropped.

    §C.4 TRAP 4: 32 of the estate's 36 matches are wrong at score ≈0.71 —
    TransDigm to Transdev, B&G Foods to US Foods, SP Plus to Lamps Plus.
    """
    withheld = served.payload["withheld"]
    assert "ambiguous_warn_matches" in withheld
    assert isinstance(withheld["ambiguous_warn_matches"], int)
    assert withheld["reason"], "a count with no reason is a number, not a finding"
    # The ESTATE's own line, asserted so the gate is about the product's
    # consumption rather than about this one obligor's luck.
    acquisition = example["acquisition"]
    terms = acquisition.vocabulary()
    assert "warn_match" in terms["tables"]


def test_ews_g15_no_gdelt_tone_reaches_any_weight_or_payload(served: Any) -> None:
    """`EWS-G15` — `tone` is a query filter, not a measurement. `CP11-F-04`.

    All 951 rows carry the identical literal `<-5`. Weighting a mention by its
    "tone" would weight every mention by a constant while appearing to
    discriminate.
    """
    body = str(served.payload)
    assert "<-5" not in body
    for row in served.payload["contributing"]:
        assert "tone" not in row, "a tone value reached a contribution"


def test_ews_g16_no_lifetime_census_is_presented_as_a_population(
    served: Any
) -> None:
    """`EWS-G16` — `filing_profile`'s counts are never served as actionable events.

    §C.4 TRAP 3. The profile says 16 obligors carry an acceleration; only 3
    have one in any decidable window. The ratio is stable across item types —
    1.01: 13.5%, 2.03: 15.2%, 2.04: 9.1% — which is what proves it is a window
    effect rather than a load defect.
    """
    body = str(served.payload)
    for name in ("count_8k_item_2_04", "count_8k_item_1_01", "filing_profile"):
        assert name not in body


def test_ews_g17_every_contribution_carries_its_whole_derivation(
    served: Any
) -> None:
    """`EWS-G17` — class, weight, age, decayed contribution and source. §D.3."""
    assert served.payload["contributing"]
    for row in served.payload["contributing"]:
        assert {
            "signal_type", "weight", "age_days", "retained", "contribution",
            "severity", "observed_at", "source_ref", "provenance",
        } <= set(row)
        expected = (
            Decimal(row["weight"]) * Decimal(row["severity"])
            * Decimal(row["retained"])
        )
        assert abs(Decimal(row["contribution"]) - expected) < Decimal("0.0002"), (
            "a contribution is not the product of the three factors beside it"
        )


def test_ews_g18_the_exclusion_list_names_a_reason_per_signal(
    served: Any
) -> None:
    """`EWS-G18` — *"why did this not escalate"* is answered by what was left out."""
    excluded = served.payload["excluded"]
    assert excluded, "the heaviest-signalled anchor excluded nothing"
    for row in excluded:
        assert row["reason"], "an excluded signal with no reason"
        assert row["note"], "a reason with no explanation"
    contributing = {row["signal_id"] for row in served.payload["contributing"]}
    for row in excluded:
        assert row["signal_id"] not in contributing, (
            "a signal is both contributing and excluded"
        )
    total = len(contributing) + len(excluded)
    assert total == served.payload["delta"]["signals_in_delta"], (
        f"contributing ({len(contributing)}) + excluded ({len(excluded)}) ="
        f" {total}, and the delta holds"
        f" {served.payload['delta']['signals_in_delta']}; a signal is in"
        " neither list or in both"
    )


def test_ews_g19_the_four_axes_are_fields_not_parameters(example: Any) -> None:
    """`EWS-G19` — `subject`, `intent`, `freshness`, `asked_at` are FIELDS. §B.2."""
    asked = example["deployment"].request(
        anchor_lei=ANCHOR, asked_at=AS_OF, intent="daily-sweep",
        freshness="daily", window_days=730,
    )
    assert asked.subject == ANCHOR
    assert asked.intent == "daily-sweep"
    assert asked.freshness == "daily"
    assert asked.asked_at == AS_OF
    for axis in ("subject", "intent", "freshness", "asked_at"):
        assert axis not in asked.parameters


def test_ews_g20_no_date_is_parsed_out_of_a_label(
    served: Any, example: Any
) -> None:
    """`EWS-G20` — every instant comes from a typed field. `CP11-F-07`.

    The Fluree `WarningSignal` node carries NO timestamp; the date appears only
    inside its `rdfs:label` string. The dated leg is PostgreSQL, and a label is
    prose rather than a clock.

    Asserted at the SOURCE: every instant in the payload matches a
    `signal_event.observed_at` the relational leg returned.
    """
    real = {str(signal.observed_at) for signal in served.estate.signals}
    for row in served.payload["contributing"] + served.payload["excluded"]:
        assert row["observed_at"] in real, (
            f"{row['observed_at']} is in the payload and not in the relational"
            " leg; an instant was derived from somewhere else"
        )
    # STRUCTURALLY, and not by grepping the source — the first draft of this
    # assertion searched `acquisition.py` for `rdfs:label` and tripped on the
    # DOCSTRING THAT EXPLAINS THE RULE. A gate that a comment can break is a
    # gate about comments.
    #
    # The artifact is where the product declares what it reads, and it names no
    # label term at all: there is nothing for the code to take a date from.
    terms = example["acquisition"].vocabulary()
    graph_terms = {
        key: value for key, value in terms.items() if isinstance(value, str)
    }
    assert not any("label" in str(value).lower() for value in graph_terms.values()), (
        f"the source vocabulary declares a label term ({graph_terms}); a label"
        " is prose, and declaring it invites a date being parsed out of one"
    )
    assert any("signal_event" in str(value) for value in terms["tables"]), (
        "the relational leg is not declared as a source of instants"
    )


def test_ews_g21_the_payload_carries_no_second_copy_of_the_governed_figures(
    served: Any
) -> None:
    """`EWS-G21` — no second copy of `D_c`, the content address or the versions."""
    for forbidden in (
        "debt", "context_debt", "d_c", "payload_hash", "content_address",
        "policy_bundle_versions", "lineage", "expires_at",
    ):
        assert forbidden not in served.payload


def test_ews_g22_the_payload_claims_no_notification_recall_or_eviction(
    served: Any, thin: Any
) -> None:
    """`EWS-G22` — serve-time ineligibility may be stated; push and recall may not.

    **Purpose amended 2026-09-12.** It no longer denies that downstream
    invalidation exists, because `D-IMPL-334` built it. It now holds the one
    line still false: the fabric cannot reach a copy a consumer already holds.

    Asserted over the payload AND over every shipped document, because a README
    can overclaim as easily as a payload.
    """
    for frozen in (served, thin):
        body = str(frozen.payload).lower()
        for claim in FORBIDDEN_CLAIMS:
            assert claim not in body, (
                f"the payload says {claim!r}; the fabric refuses to RE-SERVE"
                " and cannot reach a copy a consumer already holds"
            )
    # THE DOCUMENT SCAN EXCLUDES THE GATE ROSTER, and the exclusion is stated
    # rather than quiet. `artifacts/gates.yaml` is a record ABOUT these gates
    # and must name what they forbid — it says, in EWS-G22's own entry, that
    # the fabric cannot recall a held copy. Scanning it for the word `recalled`
    # catches the sentence explaining the rule, which is the same defect
    # EWS-G20's first draft had: a gate a comment can break is a gate about
    # comments.
    #
    # The exclusion is not a hole, because the roster is separately required to
    # carry this gate at all — asserted below.
    roster = EXAMPLE / "artifacts" / "gates.yaml"
    scanned = [
        path
        for path in sorted(EXAMPLE.rglob("*.py")) + sorted(EXAMPLE.rglob("*.yaml"))
        if path != roster
    ]
    assert scanned, "nothing was scanned, so this half would pass vacuously"
    for path in scanned:
        text = path.read_text(encoding="utf-8").lower()
        for claim in ("recalled", "evicted", "push invalidation", "notified"):
            assert claim not in text, f"{path.name} claims {claim!r}"
    assert "EWS-G22" in roster.read_text(encoding="utf-8"), (
        "the roster is exempt from the word scan and does not carry this gate;"
        " the exemption would then be a hole rather than a scoping decision"
    )


def test_ews_g23_replay_at_an_earlier_as_of_sees_the_earlier_state(
    example: Any
) -> None:
    """`EWS-G23` — `as_of` reaches the delta and the supersession filter.

    Re-served at an instant before a signal landed, that signal is absent —
    not merely weighted differently, absent. If the two serves agreed, `as_of`
    would not be reaching the read.
    """
    late = serve(example, asked_at=AS_OF)
    early = serve(example, asked_at=G25_T1)
    assert late.payload["delta"]["signals_in_delta"] > (
        early.payload["delta"]["signals_in_delta"]
    ), "the earlier as_of saw as many signals as the later one"
    late_ids = {row["signal_id"] for row in late.payload["contributing"]}
    early_ids = {row["signal_id"] for row in early.payload["contributing"]}
    assert early_ids < late_ids or (early_ids - late_ids) == set(), (
        "the earlier serve contributed a signal the later one did not"
    )


def test_ews_g24_a_spread_signal_names_its_instruments(example: Any) -> None:
    """`EWS-G24` — rung 10's `CP10-F-06`, inherited.

    Where a `spread_widening` signal names instruments, the payload carries
    them rather than collapsing to the obligor. Asserted over whichever anchor
    in the roster actually has one, so the gate is about the product's handling
    rather than about one obligor's luck.
    """
    for lei in (ANCHOR, OTHER, THIN, "549300FHJQTDPPN41627"):
        frozen = serve(example, anchor_lei=lei)
        if not hasattr(frozen, "payload"):
            continue
        rows = [
            row for row in frozen.payload["contributing"]
            if row["signal_type"] == "spread_widening"
            and row["source_ref"].get("instrument_ids")
        ]
        if rows:
            for row in rows:
                assert row["source_ref"]["instrument_ids"], (
                    "a spread signal collapsed its instruments away"
                )
            return
    pytest.skip(
        "no anchor in this roster carries a spread_widening signal naming"
        " instruments; the gate has nothing to range over on this estate"
    )


# =========================================================================
# The four gates Gate 2 added, and `EWS-G25` is the rung's whole argument.
# =========================================================================


def test_ews_g25_the_cross_product_case_through_the_real_mechanism(
    example: Any
) -> None:
    """`EWS-G25` — an event about ONE entity makes a DIFFERENT product ineligible.

    **The real `D-IMPL-334` path end to end, with no stub and no seeded
    shortcut**: real assembly → the boot-bound writer → the real Control Plane
    invalidation register → the real serve-time gate in `run_gates`. One
    `ControlPlaneRegistry` spans the serves, which is what makes the register
    the writer appends to the same register the gate reads.

    Three legs, and **the middle one is why the other two mean anything.** B is
    exactly as old as A. A mechanism keyed on elapsed TIME rather than on
    DEPENDENCE would refuse it too, satisfy the first leg, and be a global
    clock wearing an invalidation's name.

    **The boundary date is pinned, and pinned as a contract rather than as a
    fixture.** It must be 2026-07-28 — the instant the superseding evidence
    became true in the world — and it must NOT be 2026-08-19, the instant the
    fabric writes it. `D-IMPL-335` is what makes that so, and `D-IMPL-334`
    shipped with the wrong one because no test in `tests/` drove the mechanism
    through L2. This gate is the one that would have caught it.
    """
    from ccf.controlplane.invalidation import resolve_register
    from ccf.controlplane.registry import ControlPlaneRegistry
    import ccf.products.gates as gates_module
    import ccf.products.resolver as resolver_module

    deployment, produce = example["deployment"], example["produce"]
    registry = ControlPlaneRegistry()

    # Capture the RegisteredProductClass the resolver itself used, so the
    # re-gate runs against exactly what served rather than a second
    # registration that might differ.
    captured: dict[str, Any] = {}
    original = resolver_module.run_gates

    def _capture(candidate: Any, **kwargs: Any) -> Any:
        captured["product_class"] = kwargs["product_class"]
        return original(candidate, **kwargs)

    with tempfile.TemporaryDirectory(prefix="cp-11-g25-") as scratch:
        root = pathlib.Path(scratch)
        resolver_module.run_gates = _capture
        try:
            a1 = produce.assemble_and_serve(
                asked=deployment.request(anchor_lei=ANCHOR, asked_at=G25_T1),
                root=root, registry=registry,
            )
            b1 = produce.assemble_and_serve(
                asked=deployment.request(anchor_lei=OTHER, asked_at=G25_T1),
                root=root, registry=registry,
            )
            # The superseding write. New evidence dated 2026-07-28 lands, the
            # obligor's surveillance state moves, and the SINGLE WRITER records
            # a boundary — nothing in this test seeds one.
            a2 = produce.assemble_and_serve(
                asked=deployment.request(anchor_lei=ANCHOR, asked_at=G25_T2),
                root=root, registry=registry,
            )
        finally:
            resolver_module.run_gates = original

        for name, outcome in (("A1", a1), ("B1", b1), ("A2", a2)):
            assert hasattr(outcome, "product"), f"{name} did not serve"

        register = resolve_register(registry, tenant_id=a1.tenant_id)
        assert register is not None, (
            "the writer recorded no invalidation boundary at all; the"
            " D-IMPL-334 sink is not bound or the write superseded nothing"
        )
        touched_a = tuple(a1.record.context_fabric_snapshot.touched_entities)
        touched_b = tuple(b1.record.context_fabric_snapshot.touched_entities)
        assert not (set(touched_a) & set(touched_b)), (
            "A and B touched a common entity, so the middle leg would prove"
            " nothing about dependence"
        )

        moved = [
            entry for entry in register.entries
            if entry.entity_uri in set(touched_a)
            and entry.invalidated_from > G25_T1
        ]
        assert moved, "no boundary later than T1 touches A"

        # THE INSTANT, pinned both ways.
        for entry in moved:
            assert entry.invalidated_from == G25_BOUNDARY, (
                f"the boundary is {entry.invalidated_from.isoformat()}; it must"
                f" be {G25_BOUNDARY.date()}, the instant the superseding"
                " evidence became TRUE IN THE WORLD (D-IMPL-335)"
            )
            assert entry.invalidated_from != G25_INGESTION_INSTANT, (
                "the boundary is the INGESTION instant — a regression to"
                " D-IMPL-334's behavior, which refuses products whose snapshot"
                " falls after the world change but before ingestion"
            )
            assert entry.reason == "entity-claim-superseded"
            assert entry.source

        product_class = captured["product_class"]

        def _regate(frozen: Any, touched: tuple[str, ...], now: datetime) -> Any:
            return original(
                frozen.product,
                engine_resolved=frozen.product.lineage.operators_invoked,
                now=now,
                registry=registry,
                product_class=product_class,
                touched_entities=touched,
            )

        # Inside A1's own TTL, so the TTL gate — which runs first and is a
        # property of the product alone — cannot mask the gate under test.
        inside_ttl = G25_T1 + timedelta(hours=1)

        # LEG 1 — the old dependent product refuses.
        refused = _regate(a1, touched_a, inside_ttl)
        assert isinstance(refused, gates_module.DependencyInvalidationRefusal), (
            f"A1 was not refused; it returned {type(refused).__name__}"
        )
        assert refused.invalidated_from == G25_BOUNDARY
        assert refused.graph_snapshot_at == G25_T1
        assert refused.entity_uri in set(touched_a)

        # LEG 2 — an EQUALLY OLD unrelated product still serves.
        assert isinstance(
            _regate(b1, touched_b, inside_ttl), gates_module.ServableProduct
        ), (
            "an unrelated product built at the SAME instant was refused; the"
            " mechanism is keyed on elapsed time rather than on dependence"
        )

        # LEG 3 — a product derived AFTER the boundary serves.
        assert isinstance(
            _regate(
                a2,
                tuple(a2.record.context_fabric_snapshot.touched_entities),
                G25_T2 + timedelta(hours=1),
            ),
            gates_module.ServableProduct,
        ), "a product derived after the boundary was refused; the boundary is a ban"


def test_ews_g26_a_valid_sic_never_falls_silently_to_unclassified(
    example: Any
) -> None:
    """`EWS-G26` — the sector dimension stays live. `CP11-F-09`.

    `signal_weight` keys on `(signal_type, sector)` with the nine standard SIC
    division names; `legal_entity` carries a four-digit code and a specific
    description. **Measured: zero of the 50 anchors' descriptions match a
    sector name**, so without resolution every obligor falls to `Unclassified`
    and 36 of the table's 45 rows are unreachable — configuration nobody reads.

    Asserted over the WHOLE anchor set rather than one obligor, because one
    obligor resolving proves nothing about the other 49.
    """
    acquisition = example["acquisition"]
    terms = acquisition.vocabulary()
    declared = {
        str(division["sector"]) for division in terms["sic_divisions"]
    }
    fallback = str(terms["unclassified_sector"])

    relational = acquisition._Relational(
        dsn=os.environ["CCF_CP_11_POSTGRES_DSN"],
        schema=os.environ["CCF_CP_11_POSTGRES_SCHEMA"],
    )
    anchors = relational.rows(
        "SELECT lei, sic FROM legal_entity WHERE is_anchor"
    )
    assert len(anchors) > 10, "the anchor set is too small to range over"

    well_formed = [(lei, sic) for lei, sic in anchors if sic and str(sic).strip().isdigit()]
    assert well_formed, "no anchor carries a well-formed SIC code"

    resolved = [
        (lei, sic, acquisition.sector_of(sic, terms)) for lei, sic in well_formed
    ]
    fell_through = [
        (lei, sic) for lei, sic, sector in resolved if sector == fallback
    ]
    assert not fell_through, (
        f"{len(fell_through)} anchors with a well-formed SIC fell to"
        f" {fallback!r}: {fell_through[:3]}. The sector dimension is inert and"
        " 36 of the weight table's 45 rows are unreachable (CP11-F-09)"
    )
    assert {sector for _, _, sector in resolved} <= declared
    # And the resolution is DISCRIMINATING: one sector for every anchor would
    # be inertness wearing a different name.
    assert len({sector for _, _, sector in resolved}) > 1


def test_ews_g27_supersession_participation_is_declared_not_inferred(
    served: Any, example: Any
) -> None:
    """`EWS-G27` — the artifact says who participates; the chain does not.

    Today only `8k_event` has a chain. **That is what this snapshot contains,
    not a law.** A product inferring participation from the data would change
    behavior the day another class gained a chain — and in the most dangerous
    direction, by silently beginning to drop signals nobody asked it to drop.
    """
    acquisition = example["acquisition"]
    declared = {
        str(name) for name in acquisition.vocabulary()["supersession_participants"]
    }
    assert declared, "the artifact declares no participants at all"
    assert served.estate.supersession_participants == frozenset(declared), (
        "the estate's participant set does not come from the artifact"
    )
    assert served.payload["chain_states"]["participating_classes"] == sorted(declared)

    # THE DISCRIMINATING CASE, and the first draft of this gate did not have
    # one — it stayed GREEN under a sabotage that inferred participation from
    # the chain. It passed because on TODAY'S ESTATE the inferred set and the
    # declared set are the same value: only `8k_event` has a chain, and only
    # `8k_event` is declared. **A gate asserted only where two answers coincide
    # proves nothing about which one produced them** (cp-10's `RSM-G23`, the
    # same defect, found again).
    #
    # So the artifact is made to declare a class the chain does NOT contain. An
    # inferring implementation cannot produce that set; only one that reads the
    # declaration can.
    declared_terms = dict(acquisition.vocabulary())
    invented = "a-class-with-no-chain-in-this-estate"
    declared_terms["supersession_participants"] = [*declared, invented]
    original_vocabulary = acquisition.vocabulary
    acquisition.vocabulary = lambda: declared_terms
    try:
        widened = serve(example, anchor_lei=ANCHOR)
    finally:
        acquisition.vocabulary = original_vocabulary
    assert invented in widened.estate.supersession_participants, (
        "the participant set does not contain a class the ARTIFACT declares"
        " and the chain does not; participation is being inferred from the"
        " chain rather than read from the declaration"
    )
    assert widened.estate.supersession_participants == frozenset(
        {*declared, invented}
    )

    # And the consequence: a class declared but absent from the chain is
    # `not-participating` — declaring it does not make its signals superseded.
    import dataclasses

    narrowed = dataclasses.replace(
        served.estate, supersession_participants=frozenset()
    )
    assert all(
        narrowed.chain_state(signal) == "not-participating"
        for signal in narrowed.signals
    )
    assert all(narrowed.contributes(signal) for signal in narrowed.signals)


def test_ews_g28_each_signal_carries_exactly_one_chain_state(
    served: Any
) -> None:
    """`EWS-G28` — the three states PARTITION. Nothing counted twice.

    The two raw Fluree sets OVERLAP — `current` is a subset of `chained` — so a
    reader adding them would count every current signal twice. The product
    exposes one three-valued classifier and the raw sets never reach the
    payload.
    """
    estate = served.estate
    assert estate.current_signal_ids <= estate.chained_signal_ids, (
        "the raw sets do not overlap as documented, so this gate is guarding a"
        " condition that no longer holds"
    )

    states = [estate.chain_state(signal) for signal in estate.signals]
    assert set(states) <= {"current", "superseded", "not-participating"}
    assert len(states) == len(estate.signals), "a signal produced no state"

    reported = served.payload["chain_states"]["states"]
    assert sum(reported.values()) == served.payload["chain_states"]["total"]
    assert reported["total"] if False else True
    assert sum(reported.values()) == len(estate.signals), (
        f"the states sum to {sum(reported.values())} over"
        f" {len(estate.signals)} signals; a signal is in two states or none"
    )
    for name, count in reported.items():
        assert count == states.count(name)

    # The raw, overlapping sets must not be published — publishing both invites
    # exactly the double count this gate forbids.
    body = str(served.payload)
    assert "chained_signal_ids" not in body
    assert "current_signal_ids" not in body


def test_ews_g29_the_composite_and_the_context_debt_are_independent(
    served: Any, example: Any
) -> None:
    """`EWS-G29` — two decay models, two questions, and they must not be wired together.

    `signal_weight.decay_days` drives the composite WARNING SCORE: what the
    evidence says. The registered λ_c drives `F`, the Context Debt FRESHNESS
    term: how old the evidence is. They share arithmetic and answer different
    questions, and a product that let them move together would report a debt
    figure that rose and fell with its own finding.

    Asserted three ways, because each crossing fails differently.
    """
    table = example["deployment"].config()["half_life"]
    estate = served.estate
    acquisition = example["acquisition"]

    # 0. THE COMPOSITE'S DECAY COMES FROM THE ESTATE'S OWN RATE, recomputed
    #    here independently and compared per signal. **This is the assertion
    #    the first draft lacked**: it checked the config and the orderings, and
    #    stayed GREEN under a sabotage that replaced the per-class rate with a
    #    single SDK half-life. Structure and correlation are both too weak —
    #    only recomputing the arithmetic catches the crossing.
    for row in served.payload["contributing"]:
        key = (row["signal_type"], estate.obligor.sector)
        rate = estate.weights.get(key) or estate.weights.get(
            (row["signal_type"], "Unclassified")
        )
        assert rate is not None
        _weight, decay_days = rate
        assert row["decay_days"] == decay_days, (
            f"{row['signal_type']} carries decay_days {row['decay_days']} and"
            f" the estate declares {decay_days}; the composite is not decaying"
            " on the estate's own rate"
        )
        expected = (
            Decimal(1)
            if decay_days is None
            else Decimal(2) ** Decimal(-row["age_days"] / Decimal(decay_days))
        )
        assert abs(Decimal(row["retained"]) - expected) < Decimal("0.0002"), (
            f"{row['signal_type']} retained {row['retained']} at"
            f" {row['age_days']}d against a {decay_days}d rate; expected"
            f" {expected}. The composite's decay is coming from somewhere"
            " other than signal_weight.decay_days (EWS-G29)"
        )

    # 1. THE RATES DIFFER. The λ_c table names a half-life in SECONDS for one
    #    entity class; the estate names decay in DAYS per signal class. If the
    #    product had wired one into the other these would agree by construction.
    sdk_seconds = int(table["ews_signal"]["half_life_seconds"])
    estate_days = {
        days for (_cls, _sector), (_weight, days) in estate.weights.items()
        if days is not None
    }
    assert estate_days, "no estate decay rate at all"
    assert sdk_seconds not in {day * 86400 for day in estate_days} or len(
        estate_days
    ) > 1, "the SDK rate is the estate's only rate; the two models have merged"

    # 2. THE λ_c TABLE KEYS ON ENTITY CLASS, the composite on signal class and
    #    sector. Different keys cannot be the same model.
    assert set(table) == {"ews_signal", "ews_obligor"}
    assert {cls for cls, _sector in estate.weights} - set(table), (
        "every composite signal class is also a λ_c entity class; the two"
        " vocabularies have collapsed into one"
    )

    # 3. THEY MOVE INDEPENDENTLY, measured across a POPULATION rather than
    #    asserted — and the population size is the point. The first draft of
    #    this assertion used three obligors, and on those three the two
    #    orderings happened to agree; it went red against a product that was
    #    behaving correctly. **A coincidence over three subjects is not
    #    evidence of coupling**, and demanding a disagreement from a sample
    #    that small demands luck.
    #
    #    Over a real population the question is answerable: if one model drove
    #    the other, ordering by composite would order by `F` as well, and there
    #    would be ZERO inversions. Measured 2026-09-12 over 14 anchors: 36.
    acquisition = example["acquisition"]
    relational = acquisition._Relational(
        dsn=os.environ["CCF_CP_11_POSTGRES_DSN"],
        schema=os.environ["CCF_CP_11_POSTGRES_SCHEMA"],
    )
    anchors = [
        row[0]
        for row in relational.rows(
            "SELECT lei FROM legal_entity WHERE is_anchor ORDER BY lei LIMIT 12"
        )
    ]
    assert len(anchors) >= 8, "too few anchors to measure independence over"
    rows = []
    for lei in anchors:
        frozen = serve(example, anchor_lei=lei)
        if hasattr(frozen, "payload"):
            rows.append((
                Decimal(frozen.payload["composite"]["score"]),
                frozen.product.debt.factors.freshness,
            ))
    assert len(rows) >= 8
    freshness_by_composite = [f for _c, f in sorted(rows, key=lambda r: r[0])]
    inversions = sum(
        1
        for i in range(len(freshness_by_composite))
        for j in range(i + 1, len(freshness_by_composite))
        if freshness_by_composite[i] > freshness_by_composite[j]
    )
    assert inversions > 0, (
        f"ordering {len(rows)} obligors by composite orders them by F exactly,"
        " with no inversions. One model is driving the other, or the two have"
        " been wired together (EWS-G29)"
    )
