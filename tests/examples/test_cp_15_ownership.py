"""What `examples/cp-15-kyc-refresh-beneficial-ownership` serves, and to whom.

Ten of the twenty declared gates of `CP-SPEC-015` §G.1 execute here; the six
HITL gates live in `test_cp_15_review.py`, three self-sabotaging gates in
`test_cp_15_sabotage.py` and the replay gate in `test_cp_15_replay.py`.

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
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.product import OpenedProduct
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-15-kyc-refresh-beneficial-ownership"

ESTATE_VARIABLES = (
    "CCF_CP_15_POSTGRES_DSN", "CCF_CP_15_POSTGRES_SCHEMA",
    "CCF_CP_15_FLUREE_URL", "CCF_CP_15_FLUREE_LEDGER",
    "CCF_CP_15_MONGO_URI", "CCF_CP_15_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "review", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
PERSPECTIVES: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "perspectives.yaml").read_text(encoding="utf-8"))["declaration"]

SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
CONTRAST_ENTITY: str = QUESTION["intent_contrast_entity"]
ABOVE_ENTITY: str = QUESTION["above_threshold_entity"]

#: The one principal the ESTATE entitles to person data, and one it does not.
ENTITLED = ("PRIN-KYC-004", "kyc-analyst")
UNENTITLED = ("PRIN-COV-001", "coverage-banker")


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the cp-15 estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415
        import review  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment, "produce": produce,
               "projection": projection, "review": review}
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
    def persons(self) -> set[str]:
        return {row["person_key"] for row in self.payload["ownership_chain"]}


def answer(
    modules: dict[str, Any], scratch: pathlib.Path, *,
    principal: tuple[str, str] = ENTITLED, subject: str = SUBJECT,
    intent: str = INTENT, **params: Any,
) -> Answer:
    """One question on the paved road, in its own scratch, as the stated principal."""
    deployment = modules["deployment"]
    with modules["produce"].product(scratch) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: AS_OF}
        parameters.update({k: v for k, v in params.items() if v is not None})
        asked = opened.question(subject=subject, asked_at=ASKED_AT, intent=intent,
                                freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=principal[0], role=principal[1])
        )
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return Answer(role=principal[1], product=outcome.product,
                      record=opened.record_of(outcome), served=outcome)


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Answer]:
    """The demonstration entity, to the entitled principal and an unentitled one."""
    root = tmp_path_factory.mktemp("cp15")
    return {
        "entitled": answer(modules, root / "entitled", principal=ENTITLED),
        "unentitled": answer(modules, root / "unentitled", principal=UNENTITLED),
    }


# =========================================================================
# UBO-G01 / UBO-G02 / UBO-G03 — Policy first, and the residency envelope
# =========================================================================


def test_the_served_plan_runs_policy_before_similarity(served: Mapping[str, Answer]) -> None:
    """The order is a SERVED fact, read off the product rather than the config.

    Declared product gate `UBO-G01` (`CP-SPEC-015` §G.1).
    """
    for reply in served.values():
        invoked = set(reply.product.lineage.operators_invoked)
        assert {"policy.principal-subgraph", "similarity.corpus-select",
                "temporal.as-of-boundary", "traversal.typed-neighborhood"} <= invoked, invoked
        plan = list(reply.record.content_generation_path.operator_plan)
        assert plan.index("policy.principal-subgraph") < plan.index("similarity.corpus-select"), plan


def test_no_person_outside_the_residency_entitlement_is_served(
    served: Mapping[str, Answer]
) -> None:
    """A person the envelope excludes is never minted, and nothing counts them.

    Declared product gate `UBO-G02` (`CP-SPEC-015` §G.1). Two limbs, and the
    second is the one that is easy to lose: no member, count or marker may
    state how many person records were withheld, because a count of what was
    withheld is itself disclosure.
    """
    unentitled = served["unentitled"]
    entitled = served["entitled"]
    restricted = {row["person_key"] for row in entitled.payload["ownership_chain"]
                  if row["classification"] == "person-restricted"}
    assert restricted, "the demonstration entity carries no person-restricted record; the gate would be vacuous"

    assert not (unentitled.persons & restricted), sorted(unentitled.persons & restricted)
    rendered = canonical_bytes(unentitled.product).decode("utf-8")
    for person_key in restricted:
        assert person_key not in rendered, f"the unentitled vessel names {person_key}"
    # The second limb: no count of what was withheld.
    for key in unentitled.payload:
        assert "withheld" not in key.lower(), key
    assert "withheld" not in rendered.lower()


def test_the_entitled_principal_sees_a_strict_superset(served: Mapping[str, Answer]) -> None:
    """Same entity, same instant, two principals, two products.

    Declared product gate `UBO-G03` (`CP-SPEC-015` §G.1). A superset rather
    than merely a difference: the entitlement adds person records and removes
    none, so the two products are ordered rather than simply unalike.
    """
    entitled, unentitled = served["entitled"], served["unentitled"]
    assert unentitled.persons < entitled.persons, (sorted(unentitled.persons), sorted(entitled.persons))
    assert content_hash(entitled.product) != content_hash(unentitled.product)
    # And it is the SAME question: same entity, same instant, same threshold.
    assert entitled.payload["entity"]["entity_id"] == unentitled.payload["entity"]["entity_id"]
    assert entitled.payload["applicable_threshold"] == unentitled.payload["applicable_threshold"]


# =========================================================================
# UBO-G04 / UBO-G05 / UBO-G06 / UBO-G08 — confidence, threshold, intent
# =========================================================================


def test_every_person_carries_a_resolution_confidence(served: Mapping[str, Answer]) -> None:
    """A person resolved to an unknown degree is not served silently.

    Declared product gate `UBO-G04` (`CP-SPEC-015` §G.1). Where the estate
    holds no crosswalk row the confidence reads `unresolved` — a stated
    absence, never a number nobody asserted.
    """
    chain = served["entitled"].payload["ownership_chain"]
    assert chain, "the demonstration entity has no chain; the gate would be vacuous"
    for person in chain:
        confidence = person["resolution_confidence"]
        assert confidence, person
        assert confidence == "unresolved" or Decimal(confidence) >= 0


def test_the_threshold_partitions_the_chain_in_both_directions(
    served: Mapping[str, Answer]
) -> None:
    """Reportable is at or above; a finding is below. Both directions.

    Declared product gate `UBO-G05` (`CP-SPEC-015` §G.1). Asserting only one
    direction would pass a product that reported everybody.
    """
    payload = served["entitled"].payload
    bound = Decimal(payload["applicable_threshold"])
    for person in payload["reportable_owners"]:
        assert Decimal(person["effective_pct"]) >= bound, person
    for person in payload["sub_threshold_findings"]:
        assert Decimal(person["effective_pct"]) < bound, person
    # The partition is exhaustive: every person is on exactly one side.
    partitioned = {p["person_key"] for p in payload["reportable_owners"]} | {
        p["person_key"] for p in payload["sub_threshold_findings"]}
    assert partitioned == {p["person_key"] for p in payload["ownership_chain"]}


def test_the_intent_selects_the_threshold(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """One entity, two intents, two thresholds — and the SAME person moves.

    Declared product gate `UBO-G06` (`CP-SPEC-015` §G.1). The contrast entity
    is named by the artifact and its percentages are read live: under the
    broader intent its beneficial owner is a sub-threshold finding, and under
    the stricter one the very same person is a reportable owner. The
    thresholds and the ranks are never pinned.
    """
    broad = answer(modules, tmp_path / "broad", subject=CONTRAST_ENTITY, intent="onboarding")
    strict = answer(modules, tmp_path / "strict", subject=CONTRAST_ENTITY,
                    intent="enhanced-due-diligence")

    assert Decimal(strict.payload["applicable_threshold"]) < Decimal(broad.payload["applicable_threshold"])
    assert broad.persons == strict.persons, "the two intents saw different people; the contrast is not the threshold"
    moved = broad.persons & {p["person_key"] for p in strict.payload["reportable_owners"]}
    assert moved, "no person became reportable under the stricter threshold"
    assert moved <= {p["person_key"] for p in broad.payload["sub_threshold_findings"]}, (
        "the person reportable under the stricter intent was already reportable under the broader one"
    )
    assert content_hash(broad.product) != content_hash(strict.product)


def test_a_below_floor_resolution_is_a_finding_not_an_absence(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """A low-confidence match stays in the product and is named.

    Declared product gate `UBO-G08` (`CP-SPEC-015` §G.1). Raising the
    confidence floor must turn resolutions INTO findings rather than removing
    them: the count of resolutions served does not fall, and the count marked
    below the floor rises.
    """
    base = answer(modules, tmp_path / "base", subject=CONTRAST_ENTITY)
    resolutions = base.payload["resolution_findings"]
    assert len(resolutions) > 1, "the contrast entity has too few resolutions to move one"

    # Read the scores LIVE and pick a floor just above the lowest one that is
    # not already below the base floor, so exactly one resolution must flip.
    scores = sorted(Decimal(r["match_score"]) for r in resolutions
                    if r["below_floor"] != "true")
    assert scores, "every resolution is already below the floor; nothing can flip"
    floor = scores[0] + Decimal("0.0001")

    raised = answer(modules, tmp_path / "raised", subject=CONTRAST_ENTITY,
                    **{modules["deployment"].MIN_CONFIDENCE: str(floor)})
    assert Decimal(raised.payload["min_confidence"]) > Decimal(base.payload["min_confidence"])

    served_base = {r["person_key"] + r["source_system"] for r in resolutions}
    served_raised = {r["person_key"] + r["source_system"] for r in raised.payload["resolution_findings"]}
    assert served_raised == served_base, "raising the floor REMOVED resolutions instead of flagging them"
    below_base = sum(1 for r in resolutions if r["below_floor"] == "true")
    below_raised = sum(1 for r in raised.payload["resolution_findings"] if r["below_floor"] == "true")
    assert below_raised > below_base, (below_base, below_raised)


# =========================================================================
# UBO-G14 / UBO-G15 / UBO-G19 — shape, contradiction, cycles
# =========================================================================


def test_each_perspective_serves_its_declared_member_set(served: Mapping[str, Answer]) -> None:
    """The member set equals the declared shape, exactly.

    Declared product gate `UBO-G14` (`CP-SPEC-015` §G.1). The expected set is
    built HERE, from the artifact read by this module, never from the
    projection's own reader.
    """
    for reply in served.values():
        declared = set(PERSPECTIVES["common_members"]) | set(
            PERSPECTIVES["perspectives"][reply.role]["members"])
        assert set(reply.payload) == declared, (reply.role, sorted(set(reply.payload) ^ declared))
    shapes = {reply.role: frozenset(reply.payload) for reply in served.values()}
    assert len(set(shapes.values())) == len(served), shapes


def test_a_contradicting_declaration_is_served_beside_the_computed_figure(
    served: Mapping[str, Answer]
) -> None:
    """The contradiction is the finding, not something to reconcile away.

    Declared product gate `UBO-G15` (`CP-SPEC-015` §G.1). A declaration that
    disagrees with the computed chain carries BOTH figures and says it
    disagrees; the computed figure is never overwritten by the declared one.
    """
    payload = served["entitled"].payload
    declarations = payload["document_declarations"]
    assert declarations, "the demonstration entity carries no declaration; the gate would be vacuous"
    computed = {p["effective_pct"] for p in payload["ownership_chain"]}
    for declaration in declarations:
        assert declaration["computed_pct"], declaration
        assert declaration["computed_pct"] in computed, (
            "a declaration's computed figure is not one the chain actually produced"
        )
        if declaration["contradicts"] == "true":
            assert declaration["declared_pct"] != declaration["computed_pct"], declaration


def test_the_cycle_member_is_served_honestly_empty(served: Mapping[str, Answer]) -> None:
    """Absence represented honestly — and nothing else broken by it.

    Declared product gate `UBO-G19` (`CP-SPEC-015` §G.1, ruled 2026-09-21).
    No ownership cycles exist in this estate and none was engineered. Four
    limbs, which together are the whole of what the ruling asked:

    1. the member is PRESENT and empty — not omitted, which would make its
       absence informative, and not filled;
    2. NO CYCLE IS INVENTED — nothing anywhere in the served product asserts
       one;
    3. the empty cycle evidence does not invalidate unrelated findings — the
       chain, the threshold partition, the resolutions and the screening all
       survive it;
    4. the product REMAINS ACTIONABLE on the evidence the estate contains.
    """
    payload = served["entitled"].payload
    assert "cycle_findings" in payload, "the member is omitted; its absence would be informative"
    assert payload["cycle_findings"] == [], payload["cycle_findings"]

    rendered = canonical_bytes(served["entitled"].product).decode("utf-8").lower()
    assert "revisited" not in rendered, "something in the product asserts a cycle"

    # The unrelated findings all survive.
    assert payload["ownership_chain"], "an empty cycle member took the chain with it"
    assert payload["applicable_threshold"], "an empty cycle member took the threshold with it"
    assert payload["resolution_findings"], "an empty cycle member took the resolutions with it"
    assert payload["sanctions_findings"], "an empty cycle member took the screening with it"
    # Actionable: the product says something a KYC analyst can act on.
    assert payload["reportable_owners"] or payload["sub_threshold_findings"], (
        "the product reports neither an owner nor a finding; it is not actionable"
    )


def test_an_above_threshold_entity_reports_an_owner(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The positive control for the whole threshold machinery.

    Claims no gate. Without it, every threshold assertion above could be
    satisfied by a product that reports nobody, for any reason.
    """
    reply = answer(modules, tmp_path / "above", subject=ABOVE_ENTITY)
    assert reply.payload["reportable_owners"], "the above-threshold entity reports no owner at all"
    bound = Decimal(reply.payload["applicable_threshold"])
    for person in reply.payload["reportable_owners"]:
        assert Decimal(person["effective_pct"]) >= bound


def test_the_cycle_member_reports_a_cycle_when_one_exists(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The positive control for `UBO-G19`, and the reason it is not vacuous.

    Claims no gate of its own; it is what makes `UBO-G19`'s "no cycle is
    invented" a two-sided measurement rather than a tautology on an estate
    that contains none.

    **The estate has no ownership cycles and Dave ruled that none be
    engineered into it** (`CP-SPEC-015` §F.4.2). So the cycle is injected
    IN-PROCESS, into the claims one question acquires, and never written
    anywhere: one extra hop whose owned node is a node an earlier hop already
    owned. The product must then report it — which proves the member is a
    measurement of the served view rather than a constant, and therefore that
    its emptiness everywhere else is a fact rather than a default.
    """
    acquisition = modules["acquisition"]
    original = acquisition._records

    def with_a_cycle(*args: Any, **kwargs: Any) -> Any:
        records, withheld = original(*args, **kwargs)
        hops = [r for r in records if r.entity_class == "hop"]
        if not hops:
            pytest.skip("this entity has no ownership hops to close into a cycle")
        first, last = hops[0], hops[-1]
        closing = acquisition.Record(
            entity_class="hop", edge_type="hasOwnershipHop",
            entity_uri=last.entity_uri + ":closing",
            attributes={**dict(last.attributes),
                        "hop_index": str(len(hops)),
                        "owner_id": last.attributes["owned_id"],
                        "owned_id": first.attributes["owner_id"]},
            dated=None,
        )
        return (*records, closing), withheld

    monkeypatch.setattr(acquisition, "_records", with_a_cycle)
    cycling = answer(modules, tmp_path / "cycling")
    monkeypatch.undo()

    findings = cycling.payload["cycle_findings"]
    assert findings, "a cycle was present in the view and the product reported none"
    for finding in findings:
        assert finding["path"], finding
        assert finding["revisited"], finding
        assert "->" in finding["path"], finding

    # And the same question WITHOUT the injection reports none, so the
    # difference is the cycle and not the instrument.
    clean = answer(modules, tmp_path / "clean")
    assert clean.payload["cycle_findings"] == []
