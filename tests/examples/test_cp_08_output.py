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
INSTANT = datetime.now(UTC)


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
    """
    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN

    at_the_time = _serve(example, as_of=drawdown, known_as_of=drawdown)
    knowing_now = _serve(example, as_of=drawdown, known_as_of="2026-09-11")

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
    single-timeline problem back one layer up."""
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
    """Valid time is monotone in the direction its name implies, `known_as_of` held."""
    early = _serve(example, as_of="2025-06-01", known_as_of="2026-09-11")
    late = _serve(example, as_of="2026-09-11", known_as_of="2026-09-11")
    assert set(_ids(early, "amendments_in_force_and_known")) <= set(
        _ids(late, "amendments_in_force_and_known")
    )


def test_a_later_known_as_of_admits_no_fewer_amendments(
    example: tuple[Any, Any, Any]
) -> None:
    """Assertion time is monotone too, `as_of` held — the sibling of the above."""
    _, _, run = example
    drawdown = run.DEMONSTRATION_DRAWDOWN
    early = _serve(example, as_of=drawdown, known_as_of=drawdown)
    late = _serve(example, as_of=drawdown, known_as_of="2026-09-11")
    assert set(_ids(early, "amendments_in_force_and_known")) <= set(
        _ids(late, "amendments_in_force_and_known")
    )


def test_every_admitted_amendment_satisfies_BOTH_filters(
    example: tuple[Any, Any, Any]
) -> None:
    """Temporal coherence, read off the served answer.

    An admitted amendment violating either bound means one of the two filters
    was dropped — which is the product answering a question nobody asked.
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
    now = _serve(example, as_of=drawdown, known_as_of="2026-09-11")

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
    claim about the world. They mean opposite things."""
    import acquisition  # noqa: PLC0415

    with pytest.raises(acquisition.UnknownFacility):
        _serve(example, facility="FAC-NOT-A-FACILITY", as_of="2025-09-09",
               known_as_of="2025-09-09")


@pytest.mark.parametrize("parameter", ["include_superseded", "evaluate_headroom"])
def test_a_declared_and_inert_parameter_is_refused_by_name(
    example: tuple[Any, Any, Any], parameter: str
) -> None:
    """Declared-and-refused, never silently dropped.

    A parameter that vanished would read as *unsupported by oversight*; refused
    by name with its declared reason reads as *unsupported by decision*.
    """
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    outcome = _serve(example, as_of="2025-09-09", known_as_of="2025-09-09",
                     **{parameter: True})
    assert isinstance(outcome, RefusalEnvelope), (
        f"{parameter} was honored or ignored rather than refused"
    )
    # The refusal names the parameter in its own field rather than only in
    # prose, so a consumer can route on it without parsing a sentence.
    assert outcome.key == parameter, outcome
    assert outcome.reason == "not-supported-at-tier", outcome
    assert outcome.detail, "refused with no declared reason"


def test_the_transaction_point_is_lineage_and_not_product_identity(
    example: tuple[Any, Any, Any]
) -> None:
    """Where the evidence lived is not what the answer says.

    The store's transaction point is recorded so the read is reproducible; it is
    not part of what the product asserts, so it must not enter the payload.
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
    instant = datetime.now(UTC)
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
    instant = datetime.now(UTC)
    omitted = _serve(example, asked_at=instant)
    window = omitted.product.payload["window"]
    assert window["as_of"] == instant.date().isoformat()
    assert window["known_as_of"] == instant.date().isoformat()

    later = _serve(example, asked_at=instant + timedelta(days=3))
    assert later.product.payload["window"]["as_of"] > window["as_of"], (
        "the declared default did not move with the question, so it is behaving"
        " as a literal rather than as a relative default"
    )
