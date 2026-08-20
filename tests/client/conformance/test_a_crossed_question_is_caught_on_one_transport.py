"""One client, one adapter, one deployment: a crossed question is caught here.

``C-11`` (Phase 19), and the ROADMAP's own success sentence for this phase:
*"a control that answers a different question must be caught by a
single-transport client, not only by the cross-adapter parity diff."* Parity is
blind by construction to a check broken identically on both subjects, which is
exactly how ``D-IMPL-151`` finding ``B0`` survived Phase 18's suite — every leg
that could have caught it was comparing two transports that were wrong in the
same way.

So **no assertion in this module compares two subjects.** Each one names a
single transport, drives the real
:class:`~ccf.client.client.ProductClient` over a single provisioned
deployment, and asserts what that one client did. A leg here whose failure mode
were *"the two disagreed"* would not have discharged the phase, however green it
ran.

The discipline the neighbouring control modules state applies unchanged:
nothing in ``src/`` or ``runtime/`` is edited and reverted — every sabotage
below is a subclass, a wrapper or an in-memory byte edit — and nothing here
re-implements an assertion. Each hostile subject **subclasses or wraps the
shipped adapter**, because a control that tests a copy proves only that the
copy fires.

Every value the questions carry is read off the fixture deployment's own
documents. They are imported from
:mod:`tests.client.conformance.test_inprocess_conformance` rather than restated,
on the rule :mod:`tests.client.conformance.test_mcp_conformance` already sets —
*the same question* is then literally the same object and cannot drift into two
— and that module derives them from ``ccf_config.yaml`` and the seeded rows, so
the No-Hardcoding Rule (CLAUDE.md §6.4, scoped over ``tests`` through
``tools/lints/__main__.py::RULE_TREE_SCOPE``) is satisfied at the one place the
vocabulary enters.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import ClassVar, Final

import pytest

from ccf.client.adapters.inprocess import InProcessAdapter
from ccf.client.adapters.mcp_stdio import McpStdioAdapter
from ccf.client.client import ProductClient
from ccf.client.codec import encode_outcome
from ccf.client.errors import TransportError
from ccf.client.wire import TransportAdapter, WireOutcome, WireRequest
from ccf.products.contract import ContextProductContract

from tests.client.conformance.suite import Provision, Question
from tests.client.conformance.test_inprocess_conformance import (
    OTHER_PARAMETERS,
    QUESTION,
    UNPINNED_QUESTION,
)

pytestmark = pytest.mark.conformance

#: The phrase :func:`~ccf.client.codec.check_outcome` raises with when an
#: outcome echoes a question other than the one that was sent. Asserted on
#: instead of a digest value, because a control that asserted a digest would be
#: restating the implementation rather than discriminating a diagnosis.
CROSSED_QUESTION_REFUSAL: Final[str] = "different question"

#: The phrase :func:`~ccf.client.codec.verify_content_address` raises with when
#: the received vessel does not hash to the address the wire claimed for it.
#: Deliberately different from :data:`CROSSED_QUESTION_REFUSAL`, so neither
#: half of this module can pass on the other's failure.
ALTERED_VESSEL_REFUSAL: Final[str] = "content address"

#: The wording the MCP door refuses a temporal disagreement with (``C-18``),
#: which reaches this client inside a
#: :class:`~ccf.client.errors.TransportError` with the server's own text in
#: front of it. Deliberately different from :data:`CROSSED_QUESTION_REFUSAL` so
#: the two crossings cannot pass on each other's failure.
TEMPORAL_DISAGREEMENT_REFUSAL: Final[str] = (
    "cannot be echoed as a question asked as-of another"
)

#: What the sentinel below holds when the client raised and produced nothing.
#: A caught crossing produces **no** ``Result`` at all — not a refusal — and
#: this module asserts that the same way
#: :func:`~tests.client.conformance.suite.assert_wire_failure_parity` does.
_NOTHING: Final = object()


class _InProcessAnswersAnotherQuestion(InProcessAdapter):
    """The shipped in-process transport, asking the door a different question.

    Since ``C-05`` retyped the seam to bytes there is nothing else to write:
    the door mints its own echo from the question it parsed, so a transport
    that asks ``B`` gets an outcome that says ``B``, and the client's
    comparison against the ``A`` it sent is the only thing standing between a
    caller and an answer to a question nobody asked. **That there is nothing
    else to write is the property** — under the previous seam this class had to
    re-label the echo from client state to be a crossing at all, which is the
    reconstruction ``B0`` names.
    """

    def ask(self, request: WireRequest) -> bytes:
        return super().ask(
            request.model_copy(update={"parameters": OTHER_PARAMETERS})
        )


class _McpAnswersAnotherQuestion(McpStdioAdapter):
    """The shipped ``mcp+stdio`` transport, asking the door a different question.

    One expression, for the reason
    :class:`_InProcessAnswersAnotherQuestion` states. A real child process over
    real pipes still answers; the only difference from an honest adapter is
    which question it carried.
    """

    def ask(self, request: WireRequest) -> bytes:
        return super().ask(
            request.model_copy(update={"parameters": OTHER_PARAMETERS})
        )


class _McpMovesTheDoorsInstant(McpStdioAdapter):
    """The shipped transport, altering the instant the door answers at.

    ``C-18``. ``parameters`` is one axis of three, and the two classes above
    cross that one. This crosses a different axis by a different route: because
    ``C-15`` keeps the clock read client-side, a **concrete** ``as_of`` crosses
    this pipe **twice** — once inside the encoded ``request`` that becomes the
    echo, and once as the separate ``asked_at`` tool argument the door actually
    answers against. A transport altering only the second returns a perfectly
    matching echo for an answer computed at another instant, which is ``B0``'s
    own failure mode surviving on the third axis of a comparison ``C-03``
    defines as total.

    **The override is `_call`, not `ask`, and that is the point.**
    :meth:`~ccf.client.adapters.mcp_stdio.McpStdioAdapter.ask` is what builds
    the ``arguments`` mapping, and this control must alter **one entry of it**
    while leaving the encoded ``request`` untouched — an override of ``ask``
    could only move both together, which would be re-proving the crossed
    question above.

    **The delegation names the class rather than spelling zero-argument
    `super()`.** ``_call`` is a ``staticmethod``, and zero-argument ``super()``
    inside one has no ``__class__`` cell bound the way an instance method does:
    it would resolve against the first positional argument — here a
    :class:`~pathlib.Path` — and raise ``TypeError`` before this control ever
    reached its assertion.

    **One microsecond is the magnitude, deliberately.** It is enough for the
    door's equality check, and small enough that nothing else about the
    resolver's answer moves — so a failure here is attributable to the instant
    and not to a different graph state.

    The instant it substituted is recorded on the class, so the residual test
    below can assert *which* instant the door was made to answer at rather than
    merely that nothing raised.
    """

    #: The instants this class substituted, most recent last. Class state
    #: because ``_call`` is a ``staticmethod``, which is itself forced by the
    #: shipped signature this control must keep in order to delegate to it.
    substituted: ClassVar[list[datetime]] = []

    @staticmethod
    async def _call(
        program: Path, root: Path, arguments: dict[str, object]
    ) -> str:
        moved = datetime.fromisoformat(
            str(arguments["asked_at"])
        ) + timedelta(microseconds=1)
        _McpMovesTheDoorsInstant.substituted.append(moved)
        arguments["asked_at"] = moved.isoformat()
        return await McpStdioAdapter._call(program, root, arguments)


def assert_a_crossed_question_is_caught(
    *,
    hostile: InProcessAdapter | McpStdioAdapter,
    honest: InProcessAdapter | McpStdioAdapter,
    question: Question,
) -> None:
    """One client over ``hostile`` must refuse; one over ``honest`` must not.

    Takes **already-built** adapters rather than a factory, so the control on
    this function can hand it an honest adapter in the ``hostile`` slot and
    watch the assertion itself fail.

    Three things, in this order:

    1. the client over ``hostile`` raises, and the raised type is **exactly**
       :class:`~ccf.client.errors.TransportError` — not the
       :class:`~ccf.client.errors.BindingError` subclass, which would let a
       connection failure pass for a caught crossing;
    2. **no** ``Result`` was produced — refused or otherwise. A caught crossing
       is not a governed "no"; asserting it the way
       :func:`~tests.client.conformance.suite.assert_wire_failure_parity`
       asserts the same distinction is what keeps the two apart;
    3. the client over ``honest``, on the **same** question against its own
       provisioned root, is served and not refused — the vacuity guard, without
       which a transport where *everything* raises would pass limb 1.

    Raises:
        AssertionError: limb 2 or limb 3 failed.
        pytest.fail.Exception: limb 1 failed — the client did not raise, or
            raised without the discriminating wording.
    """
    produced: object = _NOTHING
    with pytest.raises(
        TransportError, match=CROSSED_QUESTION_REFUSAL
    ) as caught:
        produced = ProductClient(
            product_id=question.product_id, adapter=hostile
        ).ask(parameters=question.parameters, as_of=question.as_of)
    if type(caught.value) is not TransportError:
        raise AssertionError(
            "the crossed question was refused with a"
            f" `{type(caught.value).__name__}` rather than a `TransportError`"
            " itself — `BindingError` subclasses `TransportError`, so this"
            " assertion checks the exact `D-10` type and refuses to count a"
            " connection failure as a caught crossing"
        )
    if produced is not _NOTHING:
        raise AssertionError(
            "the client produced a `Result` as well as raising on the crossed"
            f" question — {produced!r}. A caught crossing yields no result at"
            " all, refused or otherwise, and a caller handed one would branch"
            " on an answer the fabric never gave"
        )

    served = ProductClient(product_id=question.product_id, adapter=honest).ask(
        parameters=question.parameters, as_of=question.as_of
    )
    if served.refused:
        raise AssertionError(
            "the honest adapter refused the same question, so this assertion"
            " never showed that the crossing is what was caught — a transport"
            " that refused everything would otherwise have passed the check"
            " above"
        )


def test_a_crossed_question_is_caught_over_the_in_process_transport(
    provision: Provision,
) -> None:
    """`P1`, on one transport: `inprocess` alone, and no second subject."""
    assert_a_crossed_question_is_caught(
        hostile=_InProcessAnswersAnotherQuestion(str(provision("crossed"))),
        honest=InProcessAdapter(str(provision("honest"))),
        question=QUESTION,
    )


def test_a_crossed_question_is_caught_over_the_mcp_transport(
    provision: Provision,
) -> None:
    """`P1`, on the other transport: `mcp+stdio` alone, and no second subject.

    An independent single-transport proof, never one two-subject proof. The
    in-process leg above is not consulted here and nothing is compared between
    them.
    """
    assert_a_crossed_question_is_caught(
        hostile=_McpAnswersAnotherQuestion(str(provision("crossed"))),
        honest=McpStdioAdapter(str(provision("honest"))),
        question=QUESTION,
    )


def test_control_the_assertion_fails_when_it_is_handed_an_honest_adapter(
    provision: Provision,
) -> None:
    """`D-22`: hand the assertion an honest adapter and it must notice.

    The control on the control. Without it,
    :func:`assert_a_crossed_question_is_caught` could be an assertion that
    passes for every subject there is, which is precisely the defect this
    phase exists to close one layer down.

    It fails on the **first** limb — the client did not raise — and the two
    checks below are what keep it from passing for the wrong reason: the
    failure is ``pytest``'s own *did not raise*, and the vacuity limb's wording
    is absent from it.
    """
    with pytest.raises(pytest.fail.Exception) as fired:
        assert_a_crossed_question_is_caught(
            hostile=InProcessAdapter(str(provision("honest-in-the-hostile-slot"))),
            honest=InProcessAdapter(str(provision("honest"))),
            question=QUESTION,
        )

    message = str(fired.value)
    assert "DID NOT RAISE" in message
    assert "refused everything" not in message, (
        "the assertion failed on its vacuity limb rather than on the client's"
        " silence, so this control says nothing about whether an uncaught"
        " crossing is noticed"
    )


def test_a_door_answering_at_another_instant_is_caught_when_the_boundary_is_concrete(
    provision: Provision,
) -> None:
    """`C-18`, live: the temporal axis cross-checked on one transport.

    The crossing the parameter-flipping adapters cannot produce, because it
    moves ``asked_at`` **alone** — the encoded request is byte-identical to the
    one an honest adapter would have sent, so the echo matches perfectly and
    only the door's own cross-check of the two copies can catch it.
    """
    produced: object = _NOTHING
    with pytest.raises(
        TransportError, match=TEMPORAL_DISAGREEMENT_REFUSAL
    ) as caught:
        produced = ProductClient(
            product_id=QUESTION.product_id,
            adapter=_McpMovesTheDoorsInstant(str(provision("moved-instant"))),
        ).ask(parameters=QUESTION.parameters, as_of=QUESTION.as_of)

    assert type(caught.value) is TransportError
    assert produced is _NOTHING, (
        "the client produced a result as well as raising on a door that"
        " answered at another instant"
    )


def test_the_unmutated_adapter_serves_the_same_concrete_question(
    provision: Provision,
) -> None:
    """The vacuity guard for `C-18`'s cross-check.

    The shipped :class:`~ccf.client.adapters.mcp_stdio.McpStdioAdapter`, on the
    same concrete question against its own provisioned root, is served — so the
    leg above caught the moved instant and not "this transport raises".
    """
    served = ProductClient(
        product_id=QUESTION.product_id,
        adapter=McpStdioAdapter(str(provision("unmutated"))),
    ).ask(parameters=QUESTION.parameters, as_of=QUESTION.as_of)

    assert not served.refused


def test_an_absent_boundary_leaves_the_moved_instant_undetectable(
    provision: Provision,
) -> None:
    """`C-18`'s declared residual, asserted as a measurement rather than described.

    The same hostile class, asked with ``as_of=None``, does **not** raise and
    is served: the client resolved the clock (``C-15``), so the instant crosses
    this pipe **once** and the door has nothing to compare it to. This is
    ``C-18``'s stated limit, it is named in ``C-10``'s undetected list by
    ``19-07`` and in the decision log by ``19-08``, and a future phase moving
    the clock resolution producer-side is what closes it.

    It is a **passing** test and deliberately carries no expected-failure
    marker: writing the boundary down as a measurement is what stops it
    moving quietly, and in the one phase whose subject is claims matching
    what the code does, a caveat in prose would be exactly the wrong
    instrument. Were the door ever to gain a way to check this path, this
    test goes red and somebody has to come and read it.
    """
    _McpMovesTheDoorsInstant.substituted.clear()
    served = ProductClient(
        product_id=UNPINNED_QUESTION.product_id,
        adapter=_McpMovesTheDoorsInstant(str(provision("moved-and-unpinned"))),
    ).ask(
        parameters=UNPINNED_QUESTION.parameters, as_of=UNPINNED_QUESTION.as_of
    )

    assert not served.refused
    # `C-02`: the echo is *as asked*, so it says `None` — which is precisely
    # why there is no second copy of the instant for the door to disagree with.
    assert served.temporal_boundary is None
    # And the door answered at the instant the transport chose. The residual is
    # not "the check is weak here"; it is that on this path the client holds
    # nothing that could contradict the transport.
    assert served.lineage.graph_snapshot_at == (
        _McpMovesTheDoorsInstant.substituted[-1]
    )


# ---------------------------------------------------------------------------
# `P2` — a vessel whose bytes no longer match the address its producer computed.
# ---------------------------------------------------------------------------


def _alter_the_vessel(raw: bytes) -> bytes:
    """Move the served vessel's bytes and leave the producer's claim alone.

    Corruption, truncation or a re-serializing intermediary, in the smallest
    form that is still a byte change: one space immediately inside the vessel
    text's opening brace. ``content_address`` stays exactly where the producer
    put it, so the address the client recomputes is what disagrees.

    **The edited text is still valid JSON and still a valid contract**, and the
    tests below assert both rather than asserting it here — a tamper that broke
    the vessel's well-formedness would be caught by the parser or by the
    contract check, and the leg would then be proving that the parser fires.
    """
    # A raw parse, and deliberately **not** `decode_outcome`: the decoder runs
    # the very checks this edit exists to trip, so it would raise before the
    # edit could be made.
    outcome = WireOutcome.model_validate_json(raw)
    vessel = outcome.product_json
    if vessel is None:  # pragma: no cover - the question below serves
        raise AssertionError(
            "this edit was handed a refusal, which carries no vessel to alter"
        )
    inside = vessel.index("{") + 1
    return encode_outcome(
        outcome.model_copy(
            update={"product_json": vessel[:inside] + " " + vessel[inside:]}
        )
    )


class _Editing:
    """A transport that edits the producer's bytes on the way back.

    A **wrapper** rather than a subclass, because one class has to stand over
    either shipped adapter and neither is the other's base. It satisfies
    :class:`~ccf.client.wire.TransportAdapter` structurally, holds the adapter
    the honest factory built, and does one thing to what came back.

    It is written here rather than imported from
    :mod:`tests.client.conformance.suite`, which ships a decorator of the same
    shape for the ``C-12`` legs. The two are deliberately independent, on the
    precedent ``19-05`` set when it mirrored rather than imported
    ``count_result_construction_sites``: a change to one must not silently
    change the other, and the suite's version is a private member of a module
    whose own legs fail with ``AssertionError`` from inside the suite, while
    everything here fails with ``TransportError`` out of one client.

    The bytes it produced are kept so the discrimination guard can assert
    against **what the client actually refused**, rather than against a second
    application of the edit that nothing consumed.
    """

    def __init__(self, inner: TransportAdapter, edit: Callable[[bytes], bytes]):
        self._inner = inner
        self._edit = edit
        self.edited: bytes | None = None

    def ask(self, request: WireRequest) -> bytes:
        self.edited = self._edit(self._inner.ask(request))
        return self.edited


def assert_an_altered_vessel_is_caught(
    *,
    hostile: TransportAdapter,
    honest: TransportAdapter,
    question: Question,
) -> None:
    """One client over ``hostile`` must refuse; one over ``honest`` must not.

    The same three limbs, in the same order and for the same reasons, as
    :func:`assert_a_crossed_question_is_caught` — and the same shape, so the
    control on this function can hand it an honest adapter in the ``hostile``
    slot. What differs is the wording it discriminates on: the address, never
    the echo, so neither half of this module can pass on the other's failure.

    Raises:
        AssertionError: limb 2 or limb 3 failed.
        pytest.fail.Exception: limb 1 failed.
    """
    produced: object = _NOTHING
    with pytest.raises(TransportError, match=ALTERED_VESSEL_REFUSAL) as caught:
        produced = ProductClient(
            product_id=question.product_id, adapter=hostile
        ).ask(parameters=question.parameters, as_of=question.as_of)
    if type(caught.value) is not TransportError:
        raise AssertionError(
            "the altered vessel was refused with a"
            f" `{type(caught.value).__name__}` rather than a `TransportError`"
            " itself — `BindingError` subclasses `TransportError`, so this"
            " assertion checks the exact `D-10` type"
        )
    if produced is not _NOTHING:
        raise AssertionError(
            "the client produced a `Result` as well as raising on the altered"
            f" vessel — {produced!r}. A vessel that does not match its own"
            " address yields no result at all, refused or otherwise"
        )

    served = ProductClient(product_id=question.product_id, adapter=honest).ask(
        parameters=question.parameters, as_of=question.as_of
    )
    if served.refused:
        raise AssertionError(
            "the honest adapter refused the same question, so this assertion"
            " never showed that the alteration is what was caught — a"
            " transport that refused everything would otherwise have passed"
            " the check above"
        )


def _assert_the_tamper_stayed_well_formed(edited: bytes | None) -> None:
    """The discrimination guard, as an assertion rather than as an argument.

    The tampered vessel must still parse as JSON **and** still validate as a
    :class:`~ccf.products.contract.ContextProductContract`, so the
    ``TransportError`` above is attributable to the address recomputation and
    not to :func:`~ccf.client.codec.decode_outcome`'s malformed-bytes branch or
    to the contract check beside it. Without this, a control that corrupted the
    bytes into unparseability would prove the parser fires and the test would
    still be green.
    """
    if edited is None:
        raise AssertionError(
            "the wrapper recorded no edited bytes, so this guard has nothing"
            " to discriminate on and the leg above may have raised before the"
            " edit was ever applied"
        )
    tampered = WireOutcome.model_validate_json(edited).product_json
    if tampered is None:
        raise AssertionError("the edited outcome carries no vessel at all")
    try:
        json.loads(tampered)
        ContextProductContract.model_validate_json(tampered)
    except Exception as unattributable:
        raise AssertionError(
            "the tampered vessel no longer parses as JSON or no longer"
            f" validates as a product contract — {unattributable}. The"
            " `TransportError` the leg caught is therefore not attributable to"
            " the address recomputation: `check_outcome` runs"
            " `verify_content_address` BEFORE it parses the contract, so a"
            " vessel corrupted into unparseability raises with the same"
            " address wording and the leg stays green while proving nothing"
        ) from unattributable


def test_an_altered_vessel_is_caught_over_the_in_process_transport(
    provision: Provision,
) -> None:
    """`P2`(a), on one transport: `inprocess` alone, and no second subject."""
    hostile = _Editing(
        InProcessAdapter(str(provision("altered"))), _alter_the_vessel
    )
    assert_an_altered_vessel_is_caught(
        hostile=hostile,
        honest=InProcessAdapter(str(provision("honest"))),
        question=QUESTION,
    )
    _assert_the_tamper_stayed_well_formed(hostile.edited)


def test_an_altered_vessel_is_caught_over_the_mcp_transport(
    provision: Provision,
) -> None:
    """`P2`(a), on the other transport: `mcp+stdio` alone, independently."""
    hostile = _Editing(
        McpStdioAdapter(str(provision("altered"))), _alter_the_vessel
    )
    assert_an_altered_vessel_is_caught(
        hostile=hostile,
        honest=McpStdioAdapter(str(provision("honest"))),
        question=QUESTION,
    )
    _assert_the_tamper_stayed_well_formed(hostile.edited)


def test_control_the_vessel_assertion_fails_when_it_is_handed_an_honest_adapter(
    provision: Provision,
) -> None:
    """`D-22`: the control on :func:`assert_an_altered_vessel_is_caught`.

    Handed an unwrapped honest adapter in the ``hostile`` slot, the assertion
    must notice that nothing was caught. It fails on the **first** limb, and
    the two checks below keep it from passing for the wrong reason.
    """
    with pytest.raises(pytest.fail.Exception) as fired:
        assert_an_altered_vessel_is_caught(
            hostile=InProcessAdapter(str(provision("honest-in-the-hostile-slot"))),
            honest=InProcessAdapter(str(provision("honest"))),
            question=QUESTION,
        )

    message = str(fired.value)
    assert "DID NOT RAISE" in message
    assert "refused everything" not in message, (
        "the assertion failed on its vacuity limb rather than on the client's"
        " silence, so this control says nothing about whether an undetected"
        " alteration is noticed"
    )
