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

**Phase 19 changed what a divergent subject can be, and this module records
it.** Once the door mints its own echo (``C-01``) and the seam carries bytes
(``C-05``), a subject that crosses the *question* is refused by the client
before any comparison runs, so it can no longer stand inside a parity leg —
measured and asserted in
:func:`test_a_crossed_question_no_longer_reaches_the_parity_comparison`. The
divergence that still reaches a parity leg is a door that **decides otherwise**
and is honest about it (:class:`_DecidesOtherwise`), which is the divergence a
client holding one answer structurally cannot detect and therefore the one
comparing two transports is for. Both classes are kept; neither is rewritten.
"""

from __future__ import annotations

from typing import Final

import pytest

from ccf.client.codec import encode_outcome
from ccf.client.errors import TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract

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

#: The synthetic marker :class:`_DecidesOtherwise` appends to the vessel's
#: ``plan_id``. Synthetic on purpose: no deployment vocabulary enters a control
#: module, and the neutrality this package claims stays true.
_DECIDED_OTHERWISE: Final[str] = "~decided-otherwise"


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
    """The real transport, asked one question and asking the door another.

    **This class changed meaning when the seam changed** (``C-05``, ``C-11``,
    Phase 19), and the history is kept rather than rewritten. It used to end by
    re-labelling the outcome's echo back to the request it was handed —
    ``model_copy(update={"request": request})`` — because until ``19-01`` the
    door carried no request identity and an adapter that did not re-label
    produced an outcome the codec could not tell apart from an honest one.
    Under that seam this class demonstrated that a crossed question was **not**
    caught at the client and had to be caught by comparing two transports.

    ``19-03`` deleted the re-label, and what is left is one expression. The
    door now mints its own echo from the question it parsed, so this transport
    comes back saying plainly that it asked something else, and the client's
    own comparison refuses it — see
    :mod:`tests.client.conformance.test_a_crossed_question_is_caught_on_one_transport`
    for that property asserted on one transport at a time, and
    :func:`test_a_crossed_question_no_longer_reaches_the_parity_comparison`
    below for the consequence: this subject can no longer serve as a parity
    control, because the crossing is caught before any comparison runs.
    :class:`_DecidesOtherwise` is what replaced it in that role.
    """

    def ask(self, request: WireRequest) -> bytes:
        return super().ask(
            request.model_copy(update={"parameters": OTHER_PARAMETERS})
        )


class _DecidesOtherwise(McpStdioAdapter):
    """The real transport, honest about the question and divergent in the answer.

    The parity control :class:`_AnswersAnotherQuestion` used to be, rebuilt as
    a divergence the client's own integrity checks **admit by design** — which
    is what makes it the right subject for a cross-adapter leg after Phase 19.
    The echo is the door's own and is untouched; the vessel is altered; the
    content address is recomputed over the altered vessel, so the producer's
    claim about its own bytes is true. Nothing in
    :func:`~ccf.client.codec.check_outcome` can object: this is a door that
    decided otherwise and said so accurately, and a client holding one answer
    has nothing to hold it against. Only a comparison across transports can
    catch it, which is precisely why parity still earns its keep once the
    single-transport checks are live.

    The alteration is a synthetic marker on the vessel's ``plan_id``: a real
    content change that keeps the vessel a valid contract, moves the content
    address, leaves ``lineage.graph_snapshot_at`` exactly where the door put it
    — so the leg below can still assert the anchor did *not* move — and spells
    no deployment vocabulary.
    """

    def ask(self, request: WireRequest) -> bytes:
        # A raw parse for the reason `_DropsTheReplayReference` states.
        answered = WireOutcome.model_validate_json(super().ask(request))
        if answered.product_json is None:  # pragma: no cover - question serves
            raise AssertionError(
                "this control was handed a refusal, which carries no vessel to"
                " decide otherwise about"
            )
        vessel = ContextProductContract.model_validate_json(
            answered.product_json
        )
        otherwise = vessel.model_copy(
            update={"plan_id": vessel.plan_id + _DECIDED_OTHERWISE}
        )
        return encode_outcome(
            answered.model_copy(
                update={
                    "product_json": canonical_bytes(otherwise).decode("utf-8"),
                    # Recomputed, not carried over: a door that decided
                    # otherwise and lied about the address would be caught by
                    # `verify_content_address` and this control would then be
                    # proving the codec fires rather than that parity does.
                    "content_address": content_hash(otherwise),
                }
            )
        )


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


def test_served_parity_fires_on_an_mcp_door_that_decided_otherwise(
    provision: Provision,
) -> None:
    """A different answer under the asked question's name is caught, by address.

    This test was written against :class:`_AnswersAnotherQuestion` and was
    retargeted to :class:`_DecidesOtherwise` when ``19-03`` deleted that
    class's echo re-label. The property it holds is unchanged and its assertion
    is word for word the one it always made; what changed is that a *crossed
    question* is now refused by the client before any comparison happens
    (measured — see
    :func:`test_a_crossed_question_no_longer_reaches_the_parity_comparison`),
    so a subject that crosses the question can no longer reach this leg. A door
    that decides otherwise and addresses its answer honestly still can, and it
    is the divergence a client holding one answer structurally cannot detect.
    """
    with pytest.raises(AssertionError) as fired:
        suite.assert_served_parity(
            (*IN_PROCESS, _subject(_DecidesOtherwise)),
            provision=provision,
            question=QUESTION,
        )
    assert "content_address" in str(fired.value)


def test_a_crossed_question_no_longer_reaches_the_parity_comparison(
    provision: Provision,
) -> None:
    """`C-05`/`C-11`: the client refuses the crossing before parity can compare.

    The retargeted assertion about :class:`_AnswersAnotherQuestion`, and the
    reason :class:`_DecidesOtherwise` had to be written. Before Phase 19 this
    subject was a **parity** control: the client could not tell it apart from
    an honest one, so only a comparison across two transports caught it. The
    seam retype (``C-05``) and the producer-minted echo (``C-01``) closed that,
    and this asserts the closure from the outside — the shipped parity leg
    raises :class:`~ccf.client.errors.TransportError` out of the client rather
    than reaching its own ``AssertionError``.

    The single-transport statement of the same property, which is the phase's
    success sentence, lives in
    :mod:`tests.client.conformance.test_a_crossed_question_is_caught_on_one_transport`.
    This one records what the change did to *this module*, so a later reader
    does not have to reconstruct why the class stopped being usable here.
    """
    with pytest.raises(TransportError) as caught:
        suite.assert_served_parity(
            (*IN_PROCESS, _subject(_AnswersAnotherQuestion)),
            provision=provision,
            question=QUESTION,
        )
    assert "different question" in str(caught.value)


def test_one_instant_fires_on_an_mcp_door_deciding_otherwise_at_that_instant(
    provision: Provision,
) -> None:
    """The `D-IMPL-149` leg, with a real second door inside the comparison.

    ``assert_one_instant_is_one_decision`` is new, and a new cross-adapter leg
    is exactly where this phase's recurring defect lands: it would be green
    against these two subjects whether or not the MCP door were really in the
    comparison. So the divergent door is put *into* the shipped leg here, the
    same way the two controls above do it for served parity.

    ``_DecidesOtherwise`` is the right divergence for this leg because it moves
    the *answer* and not the *instant*: the door emits a different vessel, so
    it still echoes the pinned instant and still anchors to it, and the only
    thing left to catch it is the comparison across subjects. It replaced
    ``_AnswersAnotherQuestion`` here when ``19-03`` deleted that class's echo
    re-label — a crossed question is now refused by the client before this leg
    can compare anything, which would have turned this control into a
    restatement of the codec's own check.
    """
    with pytest.raises(AssertionError) as fired:
        suite.assert_one_instant_is_one_decision(
            (*IN_PROCESS, _subject(_DecidesOtherwise)),
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
