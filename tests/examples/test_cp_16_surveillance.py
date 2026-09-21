"""What `examples/cp-16-abs-securitization-surveillance` serves, and to whom.

Eleven of the twenty-one declared gates of `CP-SPEC-016` §G.1 execute here;
the granularity and cost gates live in `test_cp_16_granularity.py`, the
self-sabotaging gates in `test_cp_16_sabotage.py` and the replay gate in
`test_cp_16_replay.py`.

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
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-16-abs-securitization-surveillance"

ESTATE_VARIABLES = (
    "CCF_CP_16_POSTGRES_DSN", "CCF_CP_16_POSTGRES_SCHEMA",
    "CCF_CP_16_FLUREE_URL", "CCF_CP_16_FLUREE_LEDGER",
    "CCF_CP_16_MONGO_URI", "CCF_CP_16_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
PERSPECTIVES: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "perspectives.yaml").read_text(encoding="utf-8"))["declaration"]

SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
AFTER_AMENDMENT: str = QUESTION["instants"]["AFTER_AMENDMENT"]
BEFORE_AMENDMENT: str = QUESTION["instants"]["BEFORE_AMENDMENT"]
CONTRAST: dict[str, Any] = QUESTION["as_of_contrast"]
UNANCHORED: str = QUESTION["unanchored_trigger_id"]
UNVALUED: str = QUESTION["unvalued_trigger_id"]
UNAMENDED: str = QUESTION["unamended_deal"]

#: The three roles, most entitled first.
DESK = ("PRIN-SFD-001", "structured-finance-desk")
RISK = ("PRIN-CRR-002", "credit-risk")
REPORTING = ("PRIN-CLR-003", "client-reporting")


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the cp-16 estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
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
    served: ServedProduct

    @property
    def payload(self) -> Mapping[str, Any]:
        return self.product.payload

    @property
    def triggers(self) -> list[Mapping[str, Any]]:
        return list(self.payload["triggers"])

    def trigger(self, trigger_id: str) -> Mapping[str, Any] | None:
        return next((row for row in self.triggers if row["trigger_id"] == trigger_id), None)


def ask(
    modules: dict[str, Any], scratch: pathlib.Path, *,
    principal: tuple[str, str] = DESK, subject: str = SUBJECT,
    intent: str = INTENT, as_of: str = AS_OF, **params: Any,
) -> Any:
    """One question on the paved road, in its own scratch, as the stated principal."""
    deployment = modules["deployment"]
    with modules["produce"].product(scratch) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: as_of}
        parameters.update({k: v for k, v in params.items() if v is not None})
        # `as_of` IS the decision instant (`CP-SPEC-016` §F.4.1), so a
        # historical question is DECIDED at the instant it asks about. Holding
        # `asked_at` at today while moving `as_of` back would ask for a product
        # whose evidence-anchored expiry is already months past.
        asked = opened.question(subject=subject, asked_at=datetime.fromisoformat(as_of),
                                intent=intent, freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=principal[0], role=principal[1])
        )
        if not isinstance(outcome, ServedProduct):
            return outcome
        return Answer(role=principal[1], product=outcome.product,
                      record=opened.record_of(outcome), served=outcome)


def answer(modules: dict[str, Any], scratch: pathlib.Path, **kwargs: Any) -> Answer:
    outcome = ask(modules, scratch, **kwargs)
    assert isinstance(outcome, Answer), getattr(outcome, "detail", outcome)
    return outcome


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Answer]:
    """The demonstration deal at both instants, and to two different roles."""
    root = tmp_path_factory.mktemp("cp16")
    return {
        "after": answer(modules, root / "after", as_of=AFTER_AMENDMENT),
        "before": answer(modules, root / "before", as_of=BEFORE_AMENDMENT),
        "risk": answer(modules, root / "risk", principal=RISK, granularity="cohort"),
    }


# =========================================================================
# ABS-G01 / ABS-G02 — the served plan, and the structure read off the graph
# =========================================================================


def test_the_served_plan_runs_policy_before_similarity(served: Mapping[str, Answer]) -> None:
    """Policy bounds the corpus before Similarity ranks it — as EXECUTED.

    THE ORDER IS READ OFF THE REPLAY RECORD, NOT THE PRODUCT. A product's
    `lineage.operators_invoked` is a `frozenset`: it says WHICH operators ran
    and can say nothing about their order, so asserting an order against it
    would be reading an unordered collection as a sequence. The executed order
    lives in replay dimension 5, `content_generation_path.operator_plan`, an
    ordered tuple built from the execution's own steps.

    Declared product gate `ABS-G01` (`CP-SPEC-016` §G.1).
    """
    for reply in served.values():
        invoked = reply.product.lineage.operators_invoked
        assert isinstance(invoked, frozenset), (
            "if this ever becomes a sequence, the order limb below should read it too"
        )
        assert {"policy.principal-subgraph", "similarity.corpus-select"} <= invoked

        plan = reply.record.content_generation_path.operator_plan
        assert plan.index("policy.principal-subgraph") < plan.index("similarity.corpus-select"), (
            f"Policy must bound the corpus before Similarity ranks it; executed {plan}"
        )


def test_tranche_seniority_is_read_from_the_graph(served: Mapping[str, Answer]) -> None:
    """Seniority ORDERS the tranches, and the order comes from the served claims.

    Declared product gate `ABS-G02` (`CP-SPEC-016` §G.1).
    """
    tranches = served["after"].payload["tranches"]
    assert tranches, "the demonstration deal has tranches"
    ranks = [int(row["seniority_rank"]) for row in tranches]
    assert ranks == sorted(ranks), "tranches are served in seniority order"
    assert len({row["tranche_id"] for row in tranches}) == len(tranches), "each tranche once"
    # The senior-most tranche is strictly senior to the junior-most: a relation,
    # never a count, so estate drift exercises the gate instead of breaking it.
    assert ranks[0] < ranks[-1] or len(ranks) == 1


def test_tranche_ordering_is_by_seniority_and_not_by_identifier(
    modules: dict[str, Any],
) -> None:
    """POSITIVE CONTROL for `ABS-G02`, and it is why that gate is not vacuous.

    Every tranche identifier in this estate happens to sort into seniority
    order, so removing the sort entirely leaves the served order unchanged and
    the estate cannot tell a measurement from a coincidence. This feeds the
    projection a case where the two orders DISAGREE — measured 2026-09-21,
    `ABS-F-07`.

    Declared product gate `ABS-G02` (`CP-SPEC-016` §G.1).
    """
    projection = modules["projection"]
    disagreeing = [
        {"tranche_id": "Z-most-senior", "class_name": "A", "seniority_rank": "0",
         "cusip": "", "interest_rate": "1", "interest_rate_basis": "fixed",
         "classification": "public"},
        {"tranche_id": "A-most-junior", "class_name": "D", "seniority_rank": "5",
         "cusip": "", "interest_rate": "2", "interest_rate_basis": "fixed",
         "classification": "public"},
    ]
    ordered = projection._tranches({"tranche": disagreeing})
    assert [row["tranche_id"] for row in ordered] == ["Z-most-senior", "A-most-junior"], (
        "seniority orders the tranches; the identifier does not"
    )


# =========================================================================
# ABS-G03 / ABS-G04 — the amendment, and how it is reached
# =========================================================================


def test_the_trigger_in_force_depends_on_the_instant(served: Mapping[str, Answer]) -> None:
    """A 2026 pool is not evaluated against a 2022 definition.

    Declared product gate `ABS-G03` (`CP-SPEC-016` §G.1).
    """
    after = served["after"].trigger(CONTRAST["amended_trigger_id"])
    before = served["before"].trigger(CONTRAST["original_trigger_id"])
    assert after is not None, "the amended definition is in force after its valid_from"
    assert before is not None, "the original definition is in force before it"
    assert served["after"].trigger(CONTRAST["original_trigger_id"]) is None, (
        "the superseded definition is not also served as in force"
    )
    assert served["before"].trigger(CONTRAST["amended_trigger_id"]) is None, (
        "a definition not yet valid at the instant is not disclosed"
    )
    # The amendment MOVED the threshold, so the choice of instant changes the
    # answer materially rather than cosmetically.
    assert Decimal(after["threshold_value"]) != Decimal(before["threshold_value"])


def test_the_amendment_is_reached_by_supersession_not_by_name(
    served: Mapping[str, Answer], modules: dict[str, Any],
) -> None:
    """The two-hop walk is the estate's own structure; no name join is invented.

    Declared product gate `ABS-G04` (`CP-SPEC-016` §G.1).
    """
    amended = served["after"].trigger(CONTRAST["amended_trigger_id"])
    assert amended is not None
    assert CONTRAST["original_trigger_id"] in amended["supersedes"], (
        "the in-force definition names what it actually replaced"
    )
    # And the link is a real edge rather than a shared prefix: the two ids do
    # NOT stand in a name relation the walk could have guessed from.
    source = (EXAMPLE / "acquisition.py").read_text(encoding="utf-8")
    assert "supersededBy" in source, "supersession is followed by its predicate"
    assert "startswith(" not in source.split("def _triggers")[1].split("def ")[0], (
        "the trigger family is not assembled by a name-prefix match"
    )


# =========================================================================
# ABS-G06 / ABS-G07 — the two anchoring invariants, separately
# =========================================================================


def test_every_publicly_sourced_threshold_carries_a_rehashable_anchor(
    served: Mapping[str, Answer],
) -> None:
    """Anchoring invariant ONE. A public threshold resolves to filed text.

    Declared product gate `ABS-G06` (`CP-SPEC-016` §F.4.0, §G.1).
    """
    public = [row for row in served["after"].triggers if row["source_classification"] == "public"]
    assert public, "the estate carries publicly sourced thresholds"
    for row in public:
        assert row["anchored"] == "true", f"{row['trigger_id']} is public and must be anchored"
        assert row["anchor_passage_id"], "the anchor names its passage"
        assert row["anchor_sha256"], "the anchor carries the hash that lets it be re-checked"
        assert row["anchor_text"].strip(), "the anchor carries the filed words themselves"


def test_every_threshold_without_a_public_anchor_is_named_unanchored(
    served: Mapping[str, Answer],
) -> None:
    """Anchoring invariant TWO, and it cannot be satisfied by the first.

    Declared product gate `ABS-G07` (`CP-SPEC-016` §F.4.0, §G.1, Route B).
    """
    reply = served["after"]
    unanchored = [row for row in reply.triggers if row["anchored"] == "false"]
    named = {row["trigger_id"] for row in reply.payload["unanchored_thresholds"]}
    assert {row["trigger_id"] for row in unanchored} == named, (
        "what is served unanchored and what is named unanchored are the same set"
    )
    assert UNANCHORED in named, "the engineered amendment is the estate's unanchored threshold"

    subject = reply.trigger(UNANCHORED)
    assert subject is not None
    assert subject["source_classification"] != "public", (
        "an unanchored threshold is classified by what actually sourced it"
    )
    # NOTHING MAY IMPLY A PASSAGE EXISTS.
    for key in ("anchor_id", "anchor_text", "anchor_passage_id", "anchor_document_id", "anchor_sha256"):
        assert key not in subject, f"{key} on an unanchored threshold implies filed text that does not exist"
    # And it is named in the findings, not only flagged.
    assert any(
        finding["finding"] == "threshold-has-no-public-anchor" and finding["subject"] == UNANCHORED
        for finding in reply.payload["findings"]
    ), "the missing public anchor is a named finding"


def test_the_unanchored_threshold_is_served_not_refused(served: Mapping[str, Answer]) -> None:
    """Route B: the amendment stays observable at the instant it governs.

    Declared product gate `ABS-G07` (`CP-SPEC-016` §F.4, Route B).
    """
    subject = served["after"].trigger(UNANCHORED)
    assert subject is not None, "the amended threshold is served, not refused"
    assert Decimal(subject["threshold_value"]) > 0, "it carries its actual threshold"
    proximity = next(
        row for row in served["after"].payload["trigger_proximity"]
        if row["trigger_id"] == UNANCHORED
    )
    assert proximity["distance"] is not None, (
        "the unanchored threshold is still evaluated; Route B marks it, it does not mute it"
    )


# =========================================================================
# ABS-G16 / ABS-G17 — a finding is not an absence
# =========================================================================


def test_a_threshold_that_is_a_formula_is_a_finding_not_a_zero(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """An uncomputable proximity names its reason rather than reading as breached.

    Declared product gate `ABS-G16` (`CP-SPEC-016` §C.3 trap 3, §G.1).
    """
    reply = answer(modules, tmp_path, subject=UNAMENDED)
    subject = reply.trigger(UNVALUED)
    assert subject is not None, "the formula-defined threshold is served, not dropped"
    assert subject["threshold_value"] == "", "it carries no numeric value, because it has none"
    proximity = next(
        row for row in reply.payload["trigger_proximity"] if row["trigger_id"] == UNVALUED
    )
    assert proximity["distance"] is None, "no distance is invented"
    assert proximity["uncomputable_reason"], "the reason is named"
    assert any(
        finding["finding"] == "threshold-is-not-a-number" and finding["subject"] == UNVALUED
        for finding in reply.payload["findings"]
    )


def test_a_two_component_threshold_keeps_both_components(served: Mapping[str, Answer]) -> None:
    """Neither component of a greater-of test is silently discarded.

    Declared product gate `ABS-G17` (`CP-SPEC-016` §C.3 trap 4, §G.1).
    """
    multi = [row for row in served["after"].triggers if len(row["threshold_components"]) > 1]
    assert multi, "the estate carries at least one two-component threshold"
    for row in multi:
        assert row["threshold_value"] in row["threshold_components"], (
            "the served value is one of the components, and the others remain visible"
        )


# =========================================================================
# ABS-G18 — the depositor-scoped filing
# =========================================================================


def test_repurchase_activity_is_depositor_scoped_with_a_stated_absence(
    served: Mapping[str, Answer],
) -> None:
    """ABS-15G covers a shelf, so no per-deal join is invented.

    Declared product gate `ABS-G18` (`CP-SPEC-016` §C.3 trap 2, §G.1).
    """
    rows = served["after"].payload["repurchase_activity"]
    assert rows, "the demonstration depositor has filings"
    for row in rows:
        assert row["deal_attributed"] == "false", (
            "the estate attributes no filing to a single trust, and the product says so"
        )
        assert row["depositor_cik"], "the filing is scoped by the depositor it names"
    assert any(
        finding["finding"] == "repurchase-activity-is-depositor-scoped"
        for finding in served["after"].payload["findings"]
    ), "the scope limitation is a named finding, not a silent shape"


# =========================================================================
# ABS-G19 / ABS-G20 — two observation types, and the evidence-anchored TTL
# =========================================================================


def test_standing_state_and_dated_events_are_different_classes(
    served: Mapping[str, Answer], modules: dict[str, Any],
) -> None:
    """`D-IMPL-332`: a dated class refuses an undated claim; a standing one does not.

    Declared product gate `ABS-G19` (`CP-SPEC-016` §E.1, §G.1).
    """
    config = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    half_life = config["half_life"]
    for standing in ("deal", "tranche", "trigger", "anchor"):
        assert half_life[standing]["decay"] == "supersede-only", (
            f"`{standing}` is standing state and carries no event date of its own"
        )
        assert "decay_basis" not in half_life[standing]
    for dated in ("cohort", "loan", "benchmark", "repurchase"):
        assert half_life[dated]["decay_basis"] == "valid-from", (
            f"`{dated}` is a dated event and its decay is anchored on the day it happened"
        )
        assert half_life[dated]["half_life_seconds"] > 0
    # And the product actually MINTS them that way. Reading the declaration
    # alone would pass against a deployment that ignored it, so the minting is
    # exercised: a standing record carries no observed time, a dated one does.
    deployment, acquisition = modules["deployment"], modules["acquisition"]
    at = datetime.fromisoformat(AS_OF)
    standing = acquisition.Record(entity_class="trigger", edge_type="hasTrigger",
                                  entity_uri="urn:t", attributes={}, dated=None)
    dated = acquisition.Record(entity_class="cohort", edge_type="hasCohort",
                               entity_uri="urn:c", attributes={}, dated=at.date())
    assert deployment._node(tenant_id="t", at=at, record=standing).observed_time is None
    assert deployment._node(tenant_id="t", at=at, record=dated).observed_time is not None


def test_expiry_rides_the_reporting_period_not_request_time(served: Mapping[str, Answer]) -> None:
    """The TTL anchor is the evidence's own freshness.

    Declared product gate `ABS-G20` (`CP-SPEC-016` §E.1, §G.1).
    """
    config = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert config["product_class"]["ttl_anchor"] == "from_entity_freshness"
    after, before = served["after"], served["before"]
    # The two instants read different reporting periods, so their expiries are
    # anchored on different evidence — a relation that holds at any pool size.
    assert after.payload["pool_performance"]["period"] != before.payload["pool_performance"]["period"]
    assert after.product.expires_at != before.product.expires_at, (
        "expiry follows the evidence's period rather than the moment of asking"
    )


# =========================================================================
# ABS-G22 — a subject with no evidence, and the absence of an oracle
# =========================================================================


def test_a_subject_with_no_evidence_is_refused_indistinguishably(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Existence is not an oracle.

    This product anchors its expiry on the evidence's own freshness, so a
    question with NO evidence at the instant has nothing to anchor on and is
    refused rather than served empty. What matters for governance is that the
    refusal is UNIFORM: a deal that does not exist and a real deal with no
    reporting period at the instant are indistinguishable to the caller, so the
    product cannot be used to ask whether a deal exists.

    Declared product gate `ABS-G22` (`CP-SPEC-016` §B.1, §G.1).
    """
    nonexistent = QUESTION["nonexistent_deals"][0]
    outcomes = {
        "nonexistent": ask(modules, tmp_path / "a", subject=nonexistent),
        "real-deal-no-period": ask(modules, tmp_path / "b", subject=SUBJECT,
                                   as_of="2020-01-31T00:00:00+00:00"),
        "nonexistent-no-period": ask(modules, tmp_path / "c", subject=nonexistent,
                                     as_of="2020-01-31T00:00:00+00:00"),
    }
    for label, outcome in outcomes.items():
        assert not isinstance(outcome, Answer), f"{label} served a product"
    shapes = {(o.kind, o.reason, o.detail) for o in outcomes.values()}
    assert len(shapes) == 1, (
        f"the refusals differ by subject and are therefore an existence oracle: {shapes}"
    )
    # And a subject WITH evidence is served, so the gate is not vacuously true.
    assert isinstance(ask(modules, tmp_path / "d", subject=SUBJECT), Answer)
