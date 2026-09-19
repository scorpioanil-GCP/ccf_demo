"""cp-08 — the two clocks, measured against the estate through the served product.

**What this module pins, and why each one needs its own test.**

The product answers *which amendments bound this facility on the drawdown date,
and which of them had the institution booked by then*. Everything below is a
property of that answer, asserted as a RELATIONSHIP rather than as a count: the
estate grows, and a test pinning `25 amendments` would make itself wrong the day
another facility lands.

The one exception is the demonstration facility's own amendment ids, and they
are pinned deliberately — `AMD-01BB3F-2`'s 52-day booking lag with a drawdown
inside it is the engineered element the product exists to make visible, and a
test that did not name it could pass against a facility where the two clocks
never diverge.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from typing import Any, Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-08-covenant-in-force-as-of"

ESTATE_VARIABLES = (
    "CCF_CP_08_FLUREE_URL",
    "CCF_CP_08_FLUREE_LEDGER",
    "CCF_CP_08_POSTGRES_DSN",
    "CCF_CP_08_POSTGRES_SCHEMA",
)

#: Module names this example shares with its siblings. Popped around the import
#: so a sibling's `deployment` already in `sys.modules` cannot answer here.
COLLIDING = ("acquisition", "deployment", "produce", "projection", "run")

pytestmark = pytest.mark.skipif(
    any(not os.environ.get(name) for name in ESTATE_VARIABLES),
    reason=(
        "cp-08 assembles from the live estate; set "
        + ", ".join(ESTATE_VARIABLES)
        + " — the v2 namespaces, never the v1 names in the estate's own .env"
    ),
)


@pytest.fixture(scope="module")
def example() -> Iterator[tuple[Any, Any, Any]]:
    """This example's own modules, whatever ran before."""
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(EXAMPLE))
    try:
        deployment = importlib.import_module("deployment")
        produce = importlib.import_module("produce")
        run = importlib.import_module("run")
        assert pathlib.Path(deployment.__file__).parent == EXAMPLE
        yield deployment, produce, run
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


#: One instant for every serve in a comparison. The decision instant is part of
#: the determination — it sets the product's expiry — so two serves a
#: millisecond apart are two different questions and correctly reach two
#: different content addresses.
#:
#: **THE POSITIVE CONTROL, distinguished from the historical demonstration**
#: (`D-IMPL-341`, validation pass 2026-09-18). Until 341 this instant was the
#: wall clock: the expiry ran from the question, so the answer never aged.
#: Now the class's declared anchor is honored — `expires_at` is the freshest
#: amendment BOOKING among the facility's amendments plus the 180-day
#: amendment half-life — and the demonstration facility's freshest booking is
#: `2025-10-05` (`AMD-01BB3F-2`), so a wall-clock question has been refused
#: `ttl-bounds` since `2026-04-03` and stays refused until the ledger books a
#: newer amendment. That refusal is the correct answer and is asserted below
#: (`test_the_wall_clock_question_is_refused_because_its_evidence_has_expired`);
#: the serving tests ask on the booking day itself, the natural instant inside
#: the window, and nothing about the data, the window or the tolerance moved.
INSTANT = datetime(2025, 10, 5, 12, 0, tzinfo=UTC)

#: "Knowing now" for the bitemporal comparisons: the asked instant's own date.
#: It was the literal `2026-09-11` while the asked instant was the wall clock.
KNOWING_NOW = INSTANT.date().isoformat()


def _serve(example: tuple[Any, Any, Any], *, facility: str | None = None,
           **kwargs: Any) -> Any:
    deployment, produce, run = example
    anchor = facility or run.DEMONSTRATION_FACILITY
    asked = deployment.request(
        facility_id=anchor, principal_scope=[anchor],
        asked_at=kwargs.pop("asked_at", INSTANT), **kwargs,
    )
    with tempfile.TemporaryDirectory(prefix="cp-08-test-") as scratch:
        return produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))


def _ids(outcome: Any, key: str) -> list[str]:
    return [entry["amendment_id"] for entry in outcome.product.payload[key]]


def _excluded_by(outcome: Any, amendment_id: str) -> str | None:
    for entry in outcome.product.payload["amendments_excluded"]:
        if entry["amendment_id"] == amendment_id:
            return entry["excluded_by"]
    return None


# --- (1) the two clocks --------------------------------------------------


def test_moving_known_as_of_alone_changes_the_admitted_set(
    example: tuple[Any, Any, Any]
) -> None:
    """**The product's whole subject**, and the one claim everything else serves.

    Same facility, same `as_of`, and only `known_as_of` moves. A single-timeline
    store returns one answer to both and signals nothing.

    The difference is asserted to be EXACTLY the amendment whose booking lag was
    engineered, not merely non-empty: a product that dropped an arbitrary
    amendment on the later run would also make the two sets differ.

    Declared product gate `CIF-G03` (`CP-SPEC-008` §G.1).
    """
    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN

    at_the_time = _serve(example, as_of=drawdown, known_as_of=drawdown)
    knowing_now = _serve(example, as_of=drawdown, known_as_of=KNOWING_NOW)

    admitted_then = set(_ids(at_the_time, "amendments_in_force_and_known"))
    admitted_now = set(_ids(knowing_now, "amendments_in_force_and_known"))

    assert admitted_then < admitted_now, (
        "moving `known_as_of` forward did not admit more amendments; the"
        " assertion-time filter is not reaching the answer"
    )
    assert admitted_now - admitted_then == {"AMD-01BB3F-2"}, (
        "the two answers differ by something other than the amendment whose"
        f" booking lag was engineered: {sorted(admitted_now - admitted_then)}"
    )


def test_the_excluded_amendment_names_the_assertion_time_axis(
    example: tuple[Any, Any, Any]
) -> None:
    """A consumer must be able to tell WHY an amendment is absent.

    The axis is a token the payload carries, not prose a reader interprets. An
    amendment absent because it was not yet in force and one absent because the
    institution had not yet learned of it are different facts.
    """
    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN
    outcome = _serve(example, as_of=drawdown, known_as_of=drawdown)

    import projection  # noqa: PLC0415

    assert _excluded_by(outcome, "AMD-01BB3F-2") == projection.AXIS_ASSERTION_TIME
    assert projection.AXIS_ASSERTION_TIME != projection.AXIS_VALID_TIME, (
        "the two axes share one token, so the payload cannot distinguish them"
    )


def test_every_excluded_amendment_carries_an_axis_and_a_reason(
    example: tuple[Any, Any, Any]
) -> None:
    """No omission is unexplained. One reason string for all axes would be the
    single-timeline problem back one layer up.

    Declared product gate `CIF-G06` (`CP-SPEC-008` §G.1).
    """
    import projection  # noqa: PLC0415

    known_axes = {
        projection.AXIS_VALID_TIME,
        projection.AXIS_ASSERTION_TIME,
        projection.AXIS_UNPLACEABLE,
    }
    _, _, run = example
    outcome = _serve(example, as_of=run.DEMONSTRATION_DRAWDOWN,
                     known_as_of=run.DEMONSTRATION_DRAWDOWN)
    excluded = outcome.product.payload["amendments_excluded"]
    assert excluded, "nothing was excluded, so this proves nothing about the record"
    for entry in excluded:
        assert entry["excluded_by"] in known_axes, entry
        assert entry["because"], f"{entry['amendment_id']} excluded with no reason"


# --- (2) monotonicity on each axis ---------------------------------------


def test_a_later_as_of_admits_no_fewer_amendments(
    example: tuple[Any, Any, Any]
) -> None:
    """Valid time is monotone in the direction its name implies, `known_as_of` held.

    Declared product gate `CIF-G01` (`CP-SPEC-008` §G.1).
    """
    early = _serve(example, as_of="2025-06-01", known_as_of=KNOWING_NOW)
    late = _serve(example, as_of=KNOWING_NOW, known_as_of=KNOWING_NOW)
    assert set(_ids(early, "amendments_in_force_and_known")) <= set(
        _ids(late, "amendments_in_force_and_known")
    )


def test_a_later_known_as_of_admits_no_fewer_amendments(
    example: tuple[Any, Any, Any]
) -> None:
    """Assertion time is monotone too, `as_of` held — the sibling of the above.

    Declared product gate `CIF-G02` (`CP-SPEC-008` §G.1).
    """
    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN
    early = _serve(example, as_of=drawdown, known_as_of=drawdown)
    late = _serve(example, as_of=drawdown, known_as_of=KNOWING_NOW)
    assert set(_ids(early, "amendments_in_force_and_known")) <= set(
        _ids(late, "amendments_in_force_and_known")
    )


def test_every_admitted_amendment_satisfies_BOTH_filters(
    example: tuple[Any, Any, Any]
) -> None:
    """Temporal coherence, read off the served answer.

    An admitted amendment violating either bound means one of the two filters
    was dropped — which is the product answering a question nobody asked.

    Declared product gate `CIF-G04` (`CP-SPEC-008` §G.1).
    """
    _, _, run = example
    as_of, known_as_of = run.DEMONSTRATION_DRAWDOWN, "2026-01-15"
    outcome = _serve(example, as_of=as_of, known_as_of=known_as_of)
    admitted = outcome.product.payload["amendments_in_force_and_known"]
    assert admitted, "nothing admitted, so coherence is vacuous here"
    for entry in admitted:
        assert entry["valid_from"] is not None and entry["valid_from"] <= as_of, entry
        assert entry["asserted_at"] is not None, entry
        assert entry["asserted_at"] <= known_as_of, entry


# --- (3) the covenants, and what the product refuses to claim about them ---


def test_the_covenants_are_served_and_labelled_unversioned(
    example: tuple[Any, Any, Any]
) -> None:
    """The one place a consumer could read more history into the answer.

    The label is a payload FIELD rather than a note in a README, because a
    consumer parsing the payload never sees the README.

    Declared product gate `CIF-G12` (`CP-SPEC-008` §G.1).
    """
    _, _, run = example
    outcome = _serve(example, as_of=run.DEMONSTRATION_DRAWDOWN,
                     known_as_of=run.DEMONSTRATION_DRAWDOWN)
    payload = outcome.product.payload
    covenants = payload["covenants"]

    assert covenants, "no covenant served at all"
    assert payload["covenant_terms_are_unversioned"] is True
    assert payload["covenant_terms_note"].strip(), "the label carries no explanation"
    for covenant in covenants:
        assert covenant["covenant_type"], covenant
        assert covenant["covenant_id"], covenant


def test_the_covenant_set_does_not_move_with_either_clock(
    example: tuple[Any, Any, Any]
) -> None:
    """The honest converse of the label, asserted rather than described.

    The estate carries no assertion time on a covenant, so a covenant set that
    CHANGED with `known_as_of` could only have done so by inventing one.
    """
    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN
    then = _serve(example, as_of=drawdown, known_as_of=drawdown)
    now = _serve(example, as_of=drawdown, known_as_of=KNOWING_NOW)

    def identities(outcome: Any) -> set[str]:
        return {c["covenant_id"] for c in outcome.product.payload["covenants"]}

    assert identities(then) == identities(now), (
        "the covenant set moved with `known_as_of`, which this estate cannot"
        " support — an assertion time was invented somewhere"
    )


# --- (4) refusals and provenance -----------------------------------------


def test_an_unresolvable_facility_refuses_rather_than_returning_nothing(
    example: tuple[Any, Any, Any]
) -> None:
    """An unknown facility is a claim about the REQUEST; an empty answer is a
    claim about the world. They mean opposite things.

    Declared product gate `CIF-G11` (`CP-SPEC-008` §G.1).
    """
    import acquisition  # noqa: PLC0415

    with pytest.raises(acquisition.UnknownFacility):
        _serve(example, facility="FAC-NOT-A-FACILITY", as_of="2025-09-09",
               known_as_of="2025-09-09")


def test_a_declared_and_inert_parameter_is_refused_by_name(
    example: tuple[Any, Any, Any]
) -> None:
    """Declared-and-refused, never silently dropped.

    A parameter that vanished would read as *unsupported by oversight*; refused
    by name with its declared reason reads as *unsupported by decision*. Both
    declared parameters are checked here rather than parametrized, so the gate
    roster can name one executing node id.

    Declared product gate `CIF-G10` (`CP-SPEC-008` §G.1).
    """
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    for parameter in ("include_superseded", "evaluate_headroom"):
        outcome = _serve(example, as_of="2025-09-09", known_as_of="2025-09-09",
                         **{parameter: True})
        assert isinstance(outcome, RefusalEnvelope), (
            f"{parameter} was honored or ignored rather than refused"
        )
        # The refusal names the parameter in its own field rather than only in
        # prose, so a consumer can route on it without parsing a sentence.
        assert outcome.key == parameter, outcome
        assert outcome.reason == "not-supported-at-tier", outcome
        assert outcome.detail, f"{parameter} refused with no declared reason"


def test_the_transaction_point_is_lineage_and_not_product_identity(
    example: tuple[Any, Any, Any]
) -> None:
    """Where the evidence lived is not what the answer says.

    The store's transaction point is recorded so the read is reproducible; it is
    not part of what the product asserts, so it must not enter the payload.

    Declared product gate `CIF-G09` (`CP-SPEC-008` §G.1).
    """
    _, _, run = example
    outcome = _serve(example, as_of=run.DEMONSTRATION_DRAWDOWN,
                     known_as_of=run.DEMONSTRATION_DRAWDOWN)
    assert outcome.window.graph_pin, "no transaction point was recorded at all"
    import json  # noqa: PLC0415

    rendered = json.dumps(outcome.product.payload, default=str)
    assert outcome.window.graph_pin not in rendered, (
        "the store's transaction point reached the payload; it is execution"
        " provenance, not something the answer claims"
    )


# --- (5) determinism ------------------------------------------------------


def test_one_question_at_one_instant_reaches_one_answer(
    example: tuple[Any, Any, Any]
) -> None:
    """And the control: a different instant is a different determination.

    Without the second half this would also pass against a product that ignored
    time entirely.
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN
    instant = INSTANT
    first = _serve(example, as_of=drawdown, known_as_of=drawdown, asked_at=instant)
    second = _serve(example, as_of=drawdown, known_as_of=drawdown, asked_at=instant)
    assert content_hash(first.product) == content_hash(second.product)

    later = _serve(example, as_of=drawdown, known_as_of=drawdown,
                   asked_at=instant + timedelta(hours=1))
    assert content_hash(later.product) != content_hash(first.product)


def test_the_declared_defaults_resolve_to_the_requests_own_instant(
    example: tuple[Any, Any, Any]
) -> None:
    """Omitting an instant is a different act from passing today's date.

    Both defaults are declared relative to the request's own instant, so the
    resolved window MOVES with the question — which a literal date in the
    contract would not.
    """
    instant = INSTANT
    omitted = _serve(example, asked_at=instant)
    window = omitted.product.payload["window"]
    assert window["as_of"] == instant.date().isoformat()
    assert window["known_as_of"] == instant.date().isoformat()

    later = _serve(example, asked_at=instant + timedelta(days=3))
    assert later.product.payload["window"]["as_of"] > window["as_of"], (
        "the declared default did not move with the question, so it is behaving"
        " as a literal rather than as a relative default"
    )


# --- (5b) the evidence-anchored expiry (`D-IMPL-341`, 2026-09-18) --------------


def test_the_expiry_runs_from_the_freshest_booking_not_the_question(
    example: tuple[Any, Any, Any]
) -> None:
    """`CP-SPEC-008` §E.3: the TTL is anchored on the latest assertion, never on
    request time. Since `D-IMPL-341` the served contract carries the anchor it
    ran from — `ttl_anchor_at` — and it is the freshest `assertedAt` among the
    facility's amendments at or before the question, as a UTC midnight instant,
    with `expires_at` that plus the `amendment` half-life. The same question an
    hour later reaches the same anchor and the same expiry: the window belongs
    to the evidence.

    **The scored set, not the served subset, and the two differ measurably.**
    The anchor is the freshest booking in the ADMITTED VIEW — the observation
    set the freshness factor scores (`D-IMPL-341` R-1). A closed question
    (`as_of` = `known_as_of` = the drawdown) serves `AMD-01BB3F-1` alone and
    excludes `AMD-01BB3F-2` on the assertion axis, yet anchors on `-2`'s booking
    all the same, because `-2` is in the view the scorer read. §E.3 said "among
    the served set" when this was raised as `CP08-F-05`; Dave ruled on
    2026-09-18 that the SPECIFICATION was wrong, and it now names the scored
    observation set. This test holds the corrected clause.
    """
    from decimal import Decimal  # noqa: PLC0415

    deployment, _, run = example
    live = _serve(example)
    bookings = sorted(datetime.fromisoformat(a["asserted_at"]).replace(tzinfo=UTC)
                      for a in live.product.payload["amendments_in_force_and_known"] if a["asserted_at"])
    freshest = bookings[-1]
    window = timedelta(seconds=int(deployment.config()["half_life"]["amendment"]["half_life_seconds"]))
    assert live.product.ttl_anchor == "from_entity_freshness"
    assert live.product.ttl_anchor_at == freshest
    assert live.product.expires_at == freshest + window
    assert live.product.expires_at != INSTANT + window, "the expiry is running from the question again"
    assert Decimal("0") < live.product.debt.factors.freshness < Decimal("1"), "freshness no longer moves with the booking date"

    later = _serve(example, asked_at=INSTANT + timedelta(hours=1))
    assert (later.product.ttl_anchor_at, later.product.expires_at) == (freshest, freshest + window)

    drawdown = run.DEMONSTRATION_DRAWDOWN
    closed = _serve(example, as_of=drawdown, known_as_of=drawdown)
    assert _excluded_by(closed, "AMD-01BB3F-2") is not None, "the closed question did not exclude the late booking"
    assert closed.product.ttl_anchor_at == freshest, "the anchor is read from the scored view, not the served set (CP08-F-05)"


def test_the_wall_clock_question_is_refused_because_its_evidence_has_expired(
    example: tuple[Any, Any, Any]
) -> None:
    """The historical demonstration, preserved as a measurement: asked now, the
    facility's freshest booking plus 180 days lies in the past, and the SDK's
    TTL gate refuses `ttl-bounds` before any product gate runs. Until
    `D-IMPL-341` this question served, with an expiry that ran from the
    question and never aged — the incorrect serve the correction replaces. A
    question one day inside the window still serves; one day past it does not.
    """
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    deployment, _, _ = example
    window = timedelta(seconds=int(deployment.config()["half_life"]["amendment"]["half_life_seconds"]))
    served = _serve(example)
    edge = served.product.expires_at
    assert edge == served.product.ttl_anchor_at + window
    assert edge < datetime.now(UTC), "the demonstration's window has not closed yet; this control is vacuous today"

    refused = _serve(example, asked_at=datetime.now(UTC))
    assert isinstance(refused, RefusalEnvelope), getattr(refused, "product", refused)
    assert (refused.kind, refused.reason) == ("ttl-refusal", "ttl-bounds")

    inside = _serve(example, asked_at=edge - timedelta(days=1))
    assert not isinstance(inside, RefusalEnvelope) and inside.product.expires_at == edge
    past = _serve(example, asked_at=edge + timedelta(days=1))
    assert isinstance(past, RefusalEnvelope) and (past.kind, past.reason) == ("ttl-refusal", "ttl-bounds")


# --- (6) the declared invariant, the replay pin, and the decision record ---


def test_the_temporal_coherence_gate_passes_a_correct_answer(
    example: tuple[Any, Any, Any]
) -> None:
    """The positive control for the two sabotages below.

    A gate that only ever refuses proves nothing about the answers it admits.
    """
    _, _, run = example
    outcome = _serve(example, as_of=run.DEMONSTRATION_DRAWDOWN,
                     known_as_of=run.DEMONSTRATION_DRAWDOWN)
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    assert not isinstance(outcome, RefusalEnvelope), outcome


def test_an_incoherent_answer_is_refused_by_the_declared_gate(
    example: tuple[Any, Any, Any]
) -> None:
    """Each bound sabotaged SEPARATELY, because a gate holding one limb of a
    two-limb invariant is half a gate.

    Not parametrized, deliberately: the gate roster names one executing node id
    per gate, and a parametrized id would either need the roster's schema
    widened or would pin the gate to one of its two limbs. The loop below keeps
    both limbs independent and names which one failed.

    The subject is the deployment's own callable over a tampered payload rather
    than a mutated module: the invariant is a property of the ANSWER, so the
    answer is what is corrupted.

    Declared product gate `CIF-G05` (`CP-SPEC-008` §G.1).
    """
    import copy  # noqa: PLC0415

    deployment, _, run = example
    outcome = _serve(example, as_of=run.DEMONSTRATION_DRAWDOWN,
                     known_as_of=run.DEMONSTRATION_DRAWDOWN)

    assert deployment.temporal_coherence_violation(outcome.product) is None, (
        "a correct answer was refused, so every refusal below proves nothing"
    )

    for field, bound in (("valid_from", "valid-time"),
                         ("asserted_at", "assertion-time")):
        tampered = copy.deepcopy(outcome.product.payload)
        admitted = tampered["amendments_in_force_and_known"]
        assert admitted, "nothing admitted, so this sabotage has no subject"
        # A date beyond BOTH declared instants, so the served amendment now
        # violates exactly the bound under test.
        admitted[0][field] = "2099-01-01"

        class _Tampered:
            payload = tampered

        violation = deployment.temporal_coherence_violation(_Tampered())
        assert violation is not None, (
            f"a served amendment violating the {bound} bound was not caught —"
            " the gate holds at most one of its two limbs"
        )
        assert admitted[0]["amendment_id"] in violation, (field, violation)
        assert "dropped" in violation, (field, violation)


def test_re_serving_at_a_recorded_transaction_point_reproduces_the_answer(
    example: tuple[Any, Any, Any]
) -> None:
    """The reproducibility claim, and it is measured rather than asserted.

    Serve, take the transaction point the product recorded, and re-serve bounded
    at it. The same question against the same store state must reach the same
    content address — which is what makes a decision re-examinable later.

    The instant is pinned across both serves because the decision instant is
    part of the determination; varying it would be a different question.

    Declared product gate `CIF-G08` (`CP-SPEC-008` §G.1).
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    deployment, produce, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN
    instant = INSTANT

    first = _serve(example, as_of=drawdown, known_as_of=drawdown, asked_at=instant)
    recorded = first.window.graph_pin
    assert recorded, "the product recorded no transaction point to replay against"

    asked = deployment.request(
        facility_id=run.DEMONSTRATION_FACILITY,
        principal_scope=[run.DEMONSTRATION_FACILITY],
        asked_at=instant, as_of=drawdown, known_as_of=drawdown,
    )
    with tempfile.TemporaryDirectory(prefix="cp-08-replay-") as scratch:
        replayed = produce.assemble_and_serve(
            asked=asked, root=pathlib.Path(scratch), at_transaction=recorded
        )

    assert content_hash(replayed.product) == content_hash(first.product), (
        "re-serving at the recorded transaction point produced a different"
        " answer, so the record does not pin what it claims to"
    )


def test_a_transaction_point_the_ledger_has_not_reached_is_refused(
    example: tuple[Any, Any, Any]
) -> None:
    """The control for the test above.

    Without it, a pin that were silently ignored would reproduce the answer too
    — and the reproduction would be proving nothing.
    """
    import httpx  # noqa: PLC0415

    deployment, produce, run = example
    asked = deployment.request(
        facility_id=run.DEMONSTRATION_FACILITY,
        principal_scope=[run.DEMONSTRATION_FACILITY],
        asked_at=datetime.now(UTC), as_of=run.DEMONSTRATION_DRAWDOWN,
        known_as_of=run.DEMONSTRATION_DRAWDOWN,
    )
    with tempfile.TemporaryDirectory(prefix="cp-08-ahead-") as scratch:
        with pytest.raises(httpx.HTTPStatusError):
            produce.assemble_and_serve(
                asked=asked, root=pathlib.Path(scratch),
                at_transaction="99999999",
            )


def test_the_product_policy_lineage_is_carried_by_the_decision_record(
    example: tuple[Any, Any, Any]
) -> None:
    """Every policy bundle the PRODUCT cites is one the RECORD carries.

    The record may carry governed artifacts the product's own lineage does not
    — the request contract among them — because replay reconstructs the
    environment the decision was made in, not only the evidence it cited. What
    it may never do is carry LESS than the product cited: a bundle named in
    lineage and missing from replay is a decision that cannot be reconstructed.

    **The non-emptiness assertion is load-bearing, and it is why this gate
    carries a new id.** Its predecessor compared a set read from an attribute
    `ProductLineage` does not have (`policy_bindings`); the left side was
    therefore always empty, `cited <= recorded` was trivially true, and the
    gate degenerated to *"a decision record exists"*. A one-sided subset check
    that cannot fail on omission is the vacuity variant this project has found
    five ways. The field that actually carries the citation is
    `policy_bundle_versions`, and the comparison below is against VERSIONS
    rather than keys because a bundle's identity is its version.

    Both limbs are sabotaged in-test rather than by hand, so neither can go
    silently inert the way the predecessor did.

    Declared product gate `CIF-G16` (`CP-SPEC-008` §G.1).
    """
    _, _, run = example
    outcome = _serve(example, as_of=run.DEMONSTRATION_DRAWDOWN,
                     known_as_of=run.DEMONSTRATION_DRAWDOWN)

    def carried(cited: set[str], recorded: set[str]) -> bool:
        """The gate's whole predicate, so the sabotages exercise what ships."""
        return bool(cited) and cited <= recorded

    bindings = outcome.record.policy_bindings.bindings
    assert bindings, "the decision record carries no policy binding at all"

    recorded = {binding.version for binding in bindings}
    cited = set(outcome.product.lineage.policy_bundle_versions or ())

    assert carried(cited, recorded), (
        "the product cites a policy bundle the decision record does not carry,"
        f" or cites none at all: cited={sorted(cited)}"
        f" missing={sorted(cited - recorded)}"
    )

    # SABOTAGE 1 — strike the cited versions out of the record. The product
    # still cites them, so replay no longer accounts for what the answer used.
    assert not carried(cited, recorded - cited), (
        "removing every cited bundle version from the decision record left the"
        " predicate satisfied — it cannot fail on omission"
    )
    # SABOTAGE 2 — empty the product's lineage. A product citing nothing is
    # trivially a subset of everything, which is precisely how the predecessor
    # gate passed while proving nothing.
    assert not carried(set(), recorded), (
        "a product citing no policy bundle at all satisfied the predicate"
    )
