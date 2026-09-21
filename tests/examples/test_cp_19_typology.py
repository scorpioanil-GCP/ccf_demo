"""What `examples/cp-19-aml-typology-match` serves to three perspectives.

Twelve of the fourteen declared gates of `CP-SPEC-019` §G.1 execute here; the
two that are their own sabotage live in `test_cp_19_sabotage.py` and the
replay gate in `test_cp_19_replay.py`.

Every assertion is a RELATIONSHIP or an IDENTITY — an ordering, a containment,
an equality between two live answers — and never an estate count. The estate
is evidence, not a fixture: a figure pinned here would make it one.
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
from typing import Any

import pytest
import yaml
from ccf.contracts.canonical import canonical_bytes
from ccf.products.product import OpenedProduct
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-19-aml-typology-match"
QUESTION = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
PERSPECTIVES = yaml.safe_load((EXAMPLE / "artifacts" / "perspectives.yaml").read_text(encoding="utf-8"))["declaration"]

SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
INSTANTS: Mapping[str, str] = QUESTION["instants"]
CONFIDENTIAL_SAR_ALERT: str = QUESTION["confidential_sar_alert"]
SHAPE_COMPARATOR_ALERT: str = QUESTION["shape_comparator_alert"]
NONEXISTENT: tuple[str, ...] = tuple(QUESTION["nonexistent_alerts"])

L1 = Perspective(principal_id="PRIN-AML-L1", role="l1")
L2 = Perspective(principal_id="PRIN-AML-L2", role="l2")
EXAMINER = Perspective(principal_id="PRIN-AML-EXAM", role="examiner")

ESTATE_VARIABLES = (
    "CCF_CP_19_SQLITE_PATH", "CCF_CP_19_POSTGRES_DSN", "CCF_CP_19_POSTGRES_SCHEMA",
    "CCF_CP_19_FLUREE_URL", "CCF_CP_19_FLUREE_LEDGER", "CCF_CP_19_MONGO_URI",
    "CCF_CP_19_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]


@pytest.fixture(scope="module")
def estate() -> None:
    """The live estate, or a skip. Never a fixture standing in for it."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(f"CCF_REQUIRE_ESTATE is set and {missing} are not exported")
        pytest.skip(f"the cp-19 estate is not exported: {missing}")
    return None


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
    perspective: Perspective
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct

    @property
    def payload(self) -> Mapping[str, Any]:
        return self.product.payload


def _question(
    opened: OpenedProduct, deployment: Any, *, as_of: str | None = None,
    network_depth: str | None = None, debt_tolerance: str | None = None,
    subject: str = SUBJECT,
) -> ProductRequest:
    parameters: dict[str, Any] = {}
    if as_of is not None:
        parameters[deployment.AS_OF] = as_of
    if network_depth is not None:
        parameters[deployment.NETWORK_DEPTH] = network_depth
    if debt_tolerance is not None:
        parameters["debt_tolerance"] = debt_tolerance
    return opened.question(
        subject=subject, asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS, parameters=parameters
    )


def _answer(
    modules: dict[str, Any], scratch: pathlib.Path, *, perspective: Perspective, **question: Any
) -> Answer:
    """One question on the paved road, in its own scratch, as the stated perspective."""
    with modules["produce"].product(scratch) as opened:
        outcome = opened.answer(_question(opened, modules["deployment"], **question), perspective=perspective)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return Answer(perspective=perspective, product=outcome.product,
                      record=opened.record_of(outcome), served=outcome)


# --- the served baselines, one question each --------------------------------------


@pytest.fixture(scope="module")
def early(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Answer]:
    """The three perspectives, at the EARLIER posture instant."""
    root = tmp_path_factory.mktemp("cp19-early")
    return {
        name: _answer(modules, root / name, perspective=who,
                      as_of=INSTANTS["AS_OF_EARLY"], network_depth="2")
        for name, who in (("l1", L1), ("l2", L2), ("examiner", EXAMINER))
    }


@pytest.fixture(scope="module")
def late(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Answer:
    """The L1 analyst at the LATER posture instant — the same alert."""
    return _answer(modules, tmp_path_factory.mktemp("cp19-late"), perspective=L1,
                   as_of=INSTANTS["AS_OF_LATE"], network_depth="2")


# =========================================================================
# ATM-G01 / ATM-G02 — policy before similarity, and containment
# =========================================================================


def test_the_served_plan_runs_policy_before_similarity(early: Mapping[str, Answer]) -> None:
    """The order is a SERVED fact, read off the product rather than the config.

    Declared product gate `ATM-G01` (`CP-SPEC-019` §G.1). The whitepaper's
    §7.4(c) four-operator composition: what makes Policy-before-Similarity a
    guarantee rather than a comment is that the product carries the order it
    ran in, and an auditor reads it there.
    """
    for answer in early.values():
        invoked = list(answer.product.lineage.operators_invoked)
        assert "policy.principal-subgraph" in invoked, invoked
        assert "similarity.corpus-select" in invoked, invoked
        plan = list(answer.record.content_generation_path.operator_plan)
        assert plan.index("policy.principal-subgraph") < plan.index("similarity.corpus-select"), plan
        assert tuple(step.operator_key for step in answer.record.content_generation_path.steps) == tuple(plan)
        # All four categories composed, not two.
        assert {"temporal.as-of-boundary", "traversal.typed-neighborhood"} <= set(invoked), invoked


def test_every_served_classification_is_inside_the_vocabulary(early: Mapping[str, Answer]) -> None:
    """Nothing outside the declared vocabulary survives the Policy step.

    Declared product gate `ATM-G02` (`CP-SPEC-019` §G.1).
    """
    vocabulary = set(PERSPECTIVES["classification_vocabulary"])
    for answer in early.values():
        for member in PERSPECTIVES["classified_list_members"]:
            for item in answer.payload.get(member) or ():
                assert item["classification"] in vocabulary, (member, item)


# =========================================================================
# ATM-G03 — the permitted set bounds what is generated
# =========================================================================


def test_every_disposition_candidate_is_inside_the_permitted_set(
    early: Mapping[str, Answer], late: Answer
) -> None:
    """A disposition the posture forbids is never a candidate.

    Declared product gate `ATM-G03` (`CP-SPEC-019` §G.1). Not generated and
    then filtered: the candidate list is built FROM the permitted set, so the
    containment is by construction and this assertion is the proof of it.
    """
    for answer in (*early.values(), late):
        permitted = set(answer.payload["permitted_dispositions"])
        candidates = answer.payload.get("disposition_candidates")
        if candidates is None:
            continue  # this perspective's plan carries no candidates at all
        proposed = {item["disposition"] for item in candidates}
        assert proposed <= permitted, (proposed - permitted, permitted)


# =========================================================================
# ATM-G05 / ATM-G06 — the posture at `as_of` governs
# =========================================================================


def test_the_posture_at_as_of_governs_and_the_two_instants_differ(
    early: Mapping[str, Answer], late: Answer
) -> None:
    """One alert, two instants, two permitted sets.

    Declared product gate `ATM-G05` (`CP-SPEC-019` §G.1). The Policy Blind
    counterfactual made measurable: an examiner reviewing a disposition
    entered under the earlier posture must evaluate it against that posture.
    The assertion is the DIFFERENCE and the direction, never the membership
    of either set as a literal.
    """
    earlier = set(early["l1"].payload["permitted_dispositions"])
    later = set(late.payload["permitted_dispositions"])
    assert earlier != later, (earlier, later)
    assert earlier and later, "both instants must permit something for the contrast to mean anything"
    # And what each perspective may PROPOSE follows its own instant's bound.
    assert {c["disposition"] for c in early["l1"].payload["disposition_candidates"]} <= earlier
    assert {c["disposition"] for c in late.payload["disposition_candidates"]} <= later


def test_the_served_posture_is_the_one_effective_at_as_of(
    early: Mapping[str, Answer], late: Answer
) -> None:
    """The product names WHICH posture governed, and it tracks `as_of`.

    Declared product gate `ATM-G06` (`CP-SPEC-019` §G.1).
    """
    earlier = early["l1"].payload["posture"]
    later = late.payload["posture"]
    assert earlier is not None and later is not None
    assert earlier["posture_id"] != later["posture_id"], (earlier, later)
    assert earlier["effective_from"] < later["effective_from"], (earlier, later)
    # Each posture's own effective date is at or before the instant asked.
    assert earlier["effective_from"] <= INSTANTS["AS_OF_EARLY"][:10]
    assert later["effective_from"] <= INSTANTS["AS_OF_LATE"][:10]


# =========================================================================
# ATM-G07 / ATM-G08 — the shape is the perspective's
# =========================================================================


def test_each_perspective_serves_its_declared_member_set(early: Mapping[str, Answer]) -> None:
    """The member set equals the declared shape, exactly.

    Declared product gate `ATM-G07` (`CP-SPEC-019` §G.1). Equality, not
    containment: a member the plan does not declare is absent, and a member it
    declares is present even when empty.

    The expected set is built HERE, from `artifacts/perspectives.yaml` read by
    this module, and never from the projection's own reader — a comparison
    against the code under test would stay green through any change the two
    made together, which is the shape of an assertion that proves nothing.
    """
    for name, answer in early.items():
        declared = set(PERSPECTIVES["common_members"]) | set(PERSPECTIVES["perspectives"][name]["members"])
        assert set(answer.payload) == declared, (name, sorted(set(answer.payload) ^ declared))
    # And the three shapes genuinely differ, or the gate would be vacuous.
    shapes = {name: frozenset(answer.payload) for name, answer in early.items()}
    assert len(set(shapes.values())) == 3, shapes


def test_the_member_set_does_not_vary_with_the_alert(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """One perspective, two alerts, one shape and two contents.

    Declared product gate `ATM-G08` (`CP-SPEC-019` §G.1). The member set is a
    function of the perspective and never of the subject — which is what makes
    an empty member uninformative about the alert.

    The comparator is chosen so the two alerts DIFFER in a member's content
    while agreeing on the shape: one carries prior-alert lineage and the other
    carries none. Compared against an alert whose members were empty on the
    same side, an implementation that simply dropped empty members would have
    passed this test — which is how the first comparator was found wanting.
    """
    first = _answer(modules, tmp_path / "first", perspective=EXAMINER,
                    as_of=INSTANTS["AS_OF_LATE"], network_depth="2")
    second = _answer(modules, tmp_path / "second", perspective=EXAMINER,
                     as_of=INSTANTS["AS_OF_LATE"], network_depth="2",
                     subject=SHAPE_COMPARATOR_ALERT)
    assert set(first.payload) == set(second.payload)
    assert first.payload["alert"]["alert_id"] != second.payload["alert"]["alert_id"]
    # The positive control: one member is present-and-empty on one side and
    # present-and-populated on the other, so the shared shape is a claim about
    # the perspective rather than about two alerts that happen to look alike.
    empty_here = {name for name, value in first.payload.items() if isinstance(value, list) and not value}
    empty_there = {name for name, value in second.payload.items() if isinstance(value, list) and not value}
    assert empty_here != empty_there, (sorted(empty_here), sorted(empty_there))


# =========================================================================
# ATM-G09 / ATM-G10 — the existence of a SAR is itself restricted
# =========================================================================


def test_the_l1_analyst_is_told_nothing_about_a_sar(early: Mapping[str, Answer]) -> None:
    """No member, no count, no marker — and no byte.

    Declared product gate `ATM-G09` (`CP-SPEC-019` §G.1). The demonstration
    alert carries a SAR that `l2` and the examiner both receive, so this is a
    measured silence rather than an absence of anything to hide.
    """
    l1_payload = early["l1"].payload
    assert "sar_filing_history" not in l1_payload, sorted(l1_payload)
    # The comparison that makes it load-bearing: the others DID receive one.
    assert early["l2"].payload["sar_filing_history"], "no SAR reached l2; the silence proves nothing"
    sar_ids = {row["sar_id"] for row in early["l2"].payload["sar_filing_history"]}
    rendered = canonical_bytes(early["l1"].product).decode("utf-8")
    for sar_id in sar_ids:
        assert sar_id not in rendered, f"the l1 vessel names {sar_id}"
    assert "sar" not in json.dumps(l1_payload).lower().replace("sar_filing_history", "")


def test_a_confidential_sar_reaches_the_examiner_alone(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """`restricted` reaches two perspectives; `confidential` reaches one.

    Declared product gate `ATM-G10` (`CP-SPEC-019` §G.1). Two classifications,
    two audiences — so the departmental read is discriminating rather than
    merely present.
    """
    l2 = _answer(modules, tmp_path / "l2", perspective=L2, as_of=INSTANTS["AS_OF_LATE"],
                 network_depth="2", subject=CONFIDENTIAL_SAR_ALERT)
    examiner = _answer(modules, tmp_path / "exam", perspective=EXAMINER, as_of=INSTANTS["AS_OF_LATE"],
                       network_depth="2", subject=CONFIDENTIAL_SAR_ALERT)
    confidential = [row for row in examiner.payload["sar_filing_history"]
                    if row["classification"] == "sar-confidential"]
    assert confidential, "the confidential-SAR alert carried none; the gate would be vacuous"
    assert not l2.payload["sar_filing_history"], l2.payload["sar_filing_history"]
    for row in confidential:
        assert row["sar_id"] not in canonical_bytes(l2.product).decode("utf-8")


# =========================================================================
# ATM-G11 / ATM-G12 — residency and anchoring
# =========================================================================


def test_constrained_resident_detail_requires_the_declared_entitlement(
    early: Mapping[str, Answer], modules: dict[str, Any]
) -> None:
    """A constrained resident is admitted only under the declared entitlement.

    Declared product gate `ATM-G11` (`CP-SPEC-019` §G.1). None of this
    deployment's three perspectives maps to a principal carrying
    `sees_eu_person_data`, so the measured property is the containment: no
    party from the constrained set appears in any served network.
    """
    acquisition = modules["acquisition"]
    constrained = acquisition._EU_ISO3
    for name, answer in early.items():
        for member in ("counterparty_network", "ownership_chain"):
            for row in answer.payload.get(member) or ():
                assert row["jurisdiction"].upper() not in constrained, (name, member, row)


def test_every_typology_match_is_anchored_to_an_advisory_passage(
    early: Mapping[str, Answer]
) -> None:
    """A match with nothing behind it is not served.

    Declared product gate `ATM-G12` (`CP-SPEC-019` §G.1). The examiner's
    reasoning trail is where the anchors are readable; the assertion is that
    every match has one there.
    """
    examiner = early["examiner"].payload
    matches = examiner["typology_matches"]
    assert matches, "no typology matched; the anchoring gate would be vacuous"
    anchored = {row["typology_id"].lower() for row in examiner["reasoning_trail"]}
    assert anchored, "the reasoning trail carries no advisory passage"
    for match in matches:
        token = match["typology_id"].replace("TYP-", "").lower()
        assert any(token in anchor for anchor in anchored), (match, sorted(anchored))
    # Every anchor names a real advisory document, not a placeholder.
    for row in examiner["reasoning_trail"]:
        assert row["advisory_number"], row
        assert row["document_id"], row
