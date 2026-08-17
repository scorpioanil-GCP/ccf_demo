"""The two guards that decide what a question is allowed to be.

``D-11`` types the adapter seam and :class:`~ccf.client.wire.WireRequest` is the
question half of it. Two field validators refuse a value that cannot cross:
:meth:`~ccf.client.wire.WireRequest._parameters_survive_the_wire`, shipped with
plan ``17-04``, and
:meth:`~ccf.client.wire.WireRequest._temporal_boundary_survives_the_wire`, added
by ``D-IMPL-151`` finding ``B0b``.

Why this module exists at all
------------------------------
**The parameters guard shipped with no test.** ``grep`` for its message, for
``_unstable_parameter`` and for the phrase *wire-stable* across ``tests/``
returned nothing before this module, so a guard whose whole job is to fire had
nothing watching whether it does. That is the same class as the findings this
phase is closing — a check nobody would notice going quiet — so the older guard
is covered here beside the new one rather than left as it was found.

What ``B0b`` measured, and what the second guard is for
-------------------------------------------------------
Running the two commands ``examples/hw1-companies-over-revenue/README.md``
documents, with the offset stripped off ``--as-of``:

* ``inprocess:`` raised ``CanonicalizationError`` out of the SQLite graph
  backend;
* ``mcp+stdio:`` raised ``TransportError``, because the far door refused the
  naive ``asked_at`` by name and a *raised* door refusal reaches a client as a
  wire error.

One caller mistake, two exception classes, and on one transport it was reported
as *the wire never spoke* — ``D-10``'s inversion. The guard moves the refusal to
the seam, before any transport is chosen, so the failure is the same object on
every transport and names the spelling that works.

Why this is **not** a conformance leg, stated so it is not read as an omission
-------------------------------------------------------------------------------
The obvious next move is a naive-``as_of`` :class:`Question` in
``tests/client/conformance``, and it is the wrong one. The guard's whole
property is that the refusal happens *before an adapter is reached*, so after
this repair there is no per-transport behaviour left for a parity leg to
compare: two subjects would run the identical validator and agree because they
are the same code, not because two transports were held to a standard. That is a
leg that cannot fail — this phase's own recurring defect, added deliberately.
What the property needs instead is an assertion that no transport is reached at
all, which is
:func:`test_a_naive_as_of_is_refused_before_any_transport_is_reached` below, and
it is non-vacuous with one adapter. ``tests/client/conformance/suite.py`` is
therefore untouched, as ``D-IMPL-148`` requires and ``D-IMPL-151`` did not lift.

Product identities and parameter names below are this module's own test
vocabulary; the SDK holds none of them (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Final

import pytest
from pydantic import ValidationError

from ccf.client.client import ProductClient
from ccf.client.wire import WireOutcome, WireRequest

#: Test vocabulary — a class name and the one parameter these questions carry.
PRODUCT_ID: Final = "ccf.test-product"
PARAMETER: Final = "minimum_score"

#: The instant the README's documented command pins, with and without its
#: offset. The same wall-clock moment, so the only thing moving is the offset.
AWARE: Final = datetime(2026, 8, 1, tzinfo=UTC)
NAIVE: Final = datetime(2026, 8, 1)


class _NeverReached:
    """An adapter that fails loudly if a guard let a bad question through.

    A :class:`~ccf.client.wire.TransportAdapter` by structure and never by
    inheritance, so it is exactly what the client will accept and nothing more.
    """

    def __init__(self) -> None:
        self.asked: list[WireRequest] = []

    def ask(self, request: WireRequest) -> WireOutcome:
        self.asked.append(request)
        raise AssertionError(
            "a question the seam should have refused reached a transport —"
            f" {request!r}"
        )


# ---------------------------------------------------------------------------
# `B0b` — the temporal boundary.
# ---------------------------------------------------------------------------


def test_an_aware_temporal_boundary_is_carried_unchanged() -> None:
    """The guard admits what it must, or it would be a guard against asking.

    Asserted first and deliberately: a validator that refused every instant
    would pass every "is it refused?" test below while making the field
    unusable.
    """
    request = WireRequest(
        product_id=PRODUCT_ID, parameters={PARAMETER: 11}, temporal_boundary=AWARE
    )

    assert request.temporal_boundary == AWARE


def test_a_non_utc_offset_is_carried_unchanged() -> None:
    """Aware means *carries an offset*, never *is UTC*.

    ``D-IMPL-38`` refuses an ambiguous instant, not a non-UTC one — a caller in
    a named zone has stated their boundary exactly as unambiguously as a caller
    in UTC, and narrowing this guard to UTC would be the fabric degrading a
    caller's value (``D-08``) in the name of checking it.
    """
    elsewhere = datetime(2026, 8, 1, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    request = WireRequest(
        product_id=PRODUCT_ID,
        parameters={PARAMETER: 11},
        temporal_boundary=elsewhere,
    )

    assert request.temporal_boundary == elsewhere


def test_no_temporal_boundary_is_a_question_and_not_a_naive_one() -> None:
    """``None`` survives the guard: it is *defer to the server's instant*.

    ``D-04``. Folding it in with the naive case would make the ordinary
    question — *what is true now* — unaskable.
    """
    request = WireRequest(
        product_id=PRODUCT_ID, parameters={PARAMETER: 11}, temporal_boundary=None
    )

    assert request.temporal_boundary is None


def test_a_naive_temporal_boundary_is_refused_at_construction() -> None:
    """``B0b``: the value the README's command produced without its offset."""
    with pytest.raises(ValidationError, match="no UTC offset"):
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: 11},
            temporal_boundary=NAIVE,
        )


def test_the_refusal_names_a_spelling_that_works() -> None:
    """The message's job is to end the caller's problem, not to report it.

    The same standard the parameters guard set for itself — *"the message can
    name the wire-stable spelling"* — held to the new guard, because a refusal
    that names no repair sends a caller to read the validator.
    """
    with pytest.raises(ValidationError) as refused:
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: 11},
            temporal_boundary=NAIVE,
        )

    message = str(refused.value)
    assert "tzinfo=UTC" in message
    assert "D-IMPL-38" in message


def test_a_naive_as_of_is_refused_before_any_transport_is_reached() -> None:
    """The ``D-10`` inversion, closed at the seam rather than per transport.

    This is the property ``B0b`` is actually about. The adapter here raises if
    it is reached at all, so the test fails one way if the guard is missing —
    which is what makes it a statement about *where* the refusal happens rather
    than merely *that* it happens.
    """
    adapter = _NeverReached()
    client = ProductClient(product_id=PRODUCT_ID, adapter=adapter)

    with pytest.raises(ValidationError, match="no UTC offset"):
        client.ask(parameters={PARAMETER: 11}, as_of=NAIVE)

    assert adapter.asked == []


def test_the_naive_refusal_is_not_a_transport_error() -> None:
    """A caller's malformed argument is never reported as an outage.

    ``D-10`` reserves :class:`~ccf.client.errors.TransportError` for *the wire
    never spoke*, and the measured ``mcp+stdio`` behaviour before this guard was
    exactly that misreport. A retry loop wrapped around ``except
    TransportError`` would re-ask a question that can never succeed.
    """
    from ccf.client.errors import TransportError

    client = ProductClient(product_id=PRODUCT_ID, adapter=_NeverReached())

    with pytest.raises(ValidationError) as refused:
        client.ask(parameters={PARAMETER: 11}, as_of=NAIVE)

    assert not isinstance(refused.value, TransportError)


# ---------------------------------------------------------------------------
# The older guard, covered here because nothing else covered it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(Decimal("1.5"), id="decimal"),
        pytest.param(AWARE, id="instant"),
        pytest.param((1, 2), id="tuple"),
        pytest.param(frozenset({1}), id="set"),
    ],
)
def test_a_parameter_that_would_come_back_a_different_type_is_refused(
    value: Any,
) -> None:
    """``17-04``'s guard, exercised for the first time.

    Each of these is a value the canonical serializer renders *correctly* and
    which comes back as something else through an ``Any``-annotated field: a
    ``Decimal`` and an instant as text, a tuple and a set as lists.
    """
    with pytest.raises(ValidationError, match="does not survive"):
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: value},
            temporal_boundary=AWARE,
        )


def test_the_parameters_guard_reaches_inside_nested_values() -> None:
    """A dotted path, because a guard that checked only the top level is a
    guard a caller walks around by nesting one level.
    """
    with pytest.raises(ValidationError, match=r"parameters\.window\[1\]"):
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={"window": [1, Decimal("2.5")]},
            temporal_boundary=AWARE,
        )


def test_wire_stable_parameters_are_carried_unchanged() -> None:
    """The converse, so the guard is not passing by refusing everything."""
    parameters = {
        PARAMETER: 11,
        "region": "north",
        "exact": True,
        "absent": None,
        "nested": {"limit": 3, "tags": ["a", "b"]},
    }

    request = WireRequest(
        product_id=PRODUCT_ID, parameters=parameters, temporal_boundary=AWARE
    )

    assert dict(request.parameters) == parameters
