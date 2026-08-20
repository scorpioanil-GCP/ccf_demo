"""Does binding MCP into the suite actually compare anything? Two controls say yes.

``D-22``. ``test_the_suite_fires.py`` proves the suite's *assertions* fire
against a synthetic divergent subject. It cannot prove that **this** binding
puts a real second transport where those assertions can see it — a factory
returning an adapter that quietly agreed with in-process by construction would
pass every leg in ``test_mcp_conformance.py`` while comparing nothing.

So each control below passes a **divergent `mcp+stdio` subject** into the
**real** ``suite.assert_served_parity``, alongside the **real** in-process
subject, and asserts it raises. Both wrappers subclass the shipped
:class:`~ccf.client.adapters.mcp_stdio.McpStdioAdapter` and still spawn a real
child process over real pipes; each diverges in exactly one way, downstream of
the transport. Nothing in ``src/`` or ``runtime/`` is edited and reverted, and
nothing here re-implements an assertion — a control that tested a copy would
prove the copy fires.

**The first control is the one this plan exists for.** ``replay_ref`` is the
field ``D-IMPL-148`` was raised about: it is compared by
``assert_served_parity`` through ``result_fields()``, which derives its list
from ``Result`` rather than writing it down, so nobody can see the comparison by
reading it. The control makes it visible — an MCP door that dropped the
reference would be caught, which is what makes *"both doors carry it"* a
measurement rather than a claim.
"""

from __future__ import annotations

import pytest

from ccf.client.codec import encode_outcome
from ccf.client.wire import WireOutcome, WireRequest

from tests.client.conformance import suite
from tests.client.conformance.suite import AdapterSubject, Provision
from tests.client.conformance.test_inprocess_conformance import (
    OTHER_PARAMETERS,
    QUESTION,
)
from tests.client.conformance.test_inprocess_conformance import SUBJECTS as IN_PROCESS
from tests.client.conformance.test_mcp_conformance import (
    break_over_stdio,
    connect_over_stdio,
)
from ccf.client.adapters.mcp_stdio import SCHEME, McpStdioAdapter

pytestmark = pytest.mark.conformance


class _DropsTheReplayReference(McpStdioAdapter):
    """The real transport, with the replay reference discarded on the way back."""

    def ask(self, request: WireRequest) -> bytes:
        # A raw parse, never `decode_outcome`: this control is producing an
        # outcome the parity leg must reject, and routing it through the
        # client's own checks on the way would prove the decoder fires rather
        # than that the leg fires.
        answered = WireOutcome.model_validate_json(super().ask(request))
        return encode_outcome(answered.model_copy(update={"replay_ref": None}))


class _AnswersAnotherQuestion(McpStdioAdapter):
    """The real transport, asked one question and echoing a different one.

    The substitution is downstream of the wire and upstream of the echo check,
    so the codec sees a perfectly well-formed outcome for the question it
    thinks it asked — which is exactly the failure a parity comparison must
    catch and a payload-only comparison would not.
    """

    def ask(self, request: WireRequest) -> bytes:
        # A raw parse for the same reason as above, and here a stronger one:
        # this control is deliberately producing a CROSSED echo, which
        # `decode_outcome` exists to reject — so parsing through it would raise
        # here, before the mutation, and the control would prove the decoder
        # fires rather than that the parity leg does.
        answered = WireOutcome.model_validate_json(
            super().ask(request.model_copy(update={"parameters": OTHER_PARAMETERS}))
        )
        # `19-03` DELETES this re-label to produce the phase's single-transport
        # control: with it gone the client raises on the crossed echo, which is
        # the whole of `B0` being closed. It is worth noticing rather than
        # passing over that the re-label is NOT a construction — it is a
        # `model_copy` of what came off the wire — so no construction counter
        # can see it, which is a limit `19-05`'s AST gate has to state in its
        # own docstring rather than imply.
        return encode_outcome(answered.model_copy(update={"request": request}))


def _subject(adapter: type[McpStdioAdapter]) -> AdapterSubject:
    """An `mcp+stdio` subject whose healthy factory builds ``adapter``."""

    def connect(root: object) -> McpStdioAdapter:
        healthy = connect_over_stdio(root)  # type: ignore[arg-type]
        return adapter(healthy._address)

    return AdapterSubject(
        name=SCHEME, connect=connect, break_transport=break_over_stdio  # type: ignore[arg-type]
    )


def test_served_parity_fires_on_an_mcp_door_that_drops_the_replay_reference(
    provision: Provision,
) -> None:
    """The field `D-IMPL-148` was raised about is genuinely compared."""
    with pytest.raises(AssertionError) as fired:
        suite.assert_served_parity(
            (*IN_PROCESS, _subject(_DropsTheReplayReference)),
            provision=provision,
            question=QUESTION,
        )
    assert "replay_ref" in str(fired.value)


def test_served_parity_fires_on_an_mcp_transport_answering_another_question(
    provision: Provision,
) -> None:
    """A different answer under the asked question's name is caught, by address."""
    with pytest.raises(AssertionError) as fired:
        suite.assert_served_parity(
            (*IN_PROCESS, _subject(_AnswersAnotherQuestion)),
            provision=provision,
            question=QUESTION,
        )
    assert "content_address" in str(fired.value)


def test_one_instant_fires_on_an_mcp_door_deciding_otherwise_at_that_instant(
    provision: Provision,
) -> None:
    """The `D-IMPL-149` leg, with a real second door inside the comparison.

    ``assert_one_instant_is_one_decision`` is new, and a new cross-adapter leg
    is exactly where this phase's recurring defect lands: it would be green
    against these two subjects whether or not the MCP door were really in the
    comparison. So the divergent door is put *into* the shipped leg here, the
    same way the two controls above do it for served parity.

    ``_AnswersAnotherQuestion`` is the right divergence for this leg because it
    moves the *answer* and not the *instant*: the door answers a different
    threshold, so it still echoes the pinned instant and still anchors to it,
    and the only thing left to catch it is the comparison across subjects.
    """
    with pytest.raises(AssertionError) as fired:
        suite.assert_one_instant_is_one_decision(
            (*IN_PROCESS, _subject(_AnswersAnotherQuestion)),
            provision=provision,
            question=QUESTION,
        )

    message = str(fired.value)
    assert "content_address" in message
    assert "graph state anchored at" not in message, (
        "the divergent door moved its anchor as well, so this control fired on"
        " the per-subject check and says nothing about whether the MCP door is"
        " inside the cross-adapter comparison"
    )
