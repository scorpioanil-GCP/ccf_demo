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

    def ask(self, request: WireRequest) -> WireOutcome:
        answered = super().ask(request)
        return answered.model_copy(update={"replay_ref": None})


class _AnswersAnotherQuestion(McpStdioAdapter):
    """The real transport, asked one question and echoing a different one.

    The substitution is downstream of the wire and upstream of the echo check,
    so the codec sees a perfectly well-formed outcome for the question it
    thinks it asked — which is exactly the failure a parity comparison must
    catch and a payload-only comparison would not.
    """

    def ask(self, request: WireRequest) -> WireOutcome:
        answered = super().ask(
            request.model_copy(update={"parameters": OTHER_PARAMETERS})
        )
        return answered.model_copy(update={"request": request})


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
