"""The `mcp+stdio` transport, bound into the conformance suite as its second subject.

``D-15``, and **the acceptance test for plan ``17-07``'s design**: ``suite.py``
said a second module exactly like the first would change nothing in it, and
binding a real second transport is what makes that claim non-trivial. A factory,
a break hook and one call per property were the whole of it —
``git diff tests/client/conformance/suite.py`` is empty.

Every leg compares **both** subjects, so the cross-adapter comparisons stop
degenerating to self-comparisons. The questions are imported from the in-process
binding rather than restated, so *the same question* is literally the same
object and cannot drift into two.

**One leg used to take the MCP subject alone, and no longer does.** When this
module was written, ``assert_decision_instant_is_auditable`` refused a question
that named its own instant and then compared the recovered ``graph_snapshot_at``
*across* subjects — but with ``as_of=None`` each subject reads a clock, so two
of them recover two instants milliseconds apart (measured: 116 ms). That made
the leg unsatisfiable for **any** two subjects, MCP or not, and this module
called it with one subject while recording the contradiction as a finding
against ``17-07`` — narrowing the assertion was not open, ``D-IMPL-148`` having
ruled that the suite is not weakened to admit an adapter. ``D-IMPL-149`` (Dave,
2026-08-17) split the leg instead: the per-subject recovery property keeps its
unpinned question and now takes **both** subjects, and the cross-adapter half
became :func:`~tests.client.conformance.suite.assert_one_instant_is_one_decision`,
which runs under an instant the test pins and refuses an unpinned one. Both are
called below with the full pair.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ccf.client.adapters.mcp_stdio import SCHEME, McpStdioAdapter

from tests.client.conformance import suite
from tests.client.conformance.suite import AdapterSubject, Provision
from tests.client.conformance.test_inprocess_conformance import (
    OTHER_PARAMETERS,
    QUESTION,
    REFUSING_QUESTION,
    UNPINNED_QUESTION,
)
from tests.client.conformance.test_inprocess_conformance import SUBJECTS as IN_PROCESS
from tests.client.fixtures import declare_server

pytestmark = pytest.mark.conformance

#: The program the break hook writes, beside the deployment and never inside it
#: — a deployment root holds one Python module by ``D-IMPL-141`` Amendment A.3,
#: and ``server:`` resolves against the directory holding the root (``D-10``).
BROKEN_SERVER = "broken_server.py"


def connect_over_stdio(root: Path) -> McpStdioAdapter:
    """A healthy adapter reaching ``root``, which declares its own server.

    The address is the root and nothing else (``D-05``); the program the child
    runs is the ``server:`` the ``provision`` fixture wrote into this copy.
    """
    return McpStdioAdapter(str(root))


def break_over_stdio(root: Path) -> McpStdioAdapter:
    """Point the deployment at a program that dies, so the pipe closes.

    The hook owns this root and raises nothing itself. Since ``18.1-02`` it
    returns the same class the healthy factory returns **and the same address**
    — byte-identical, because the address is now only the root. The two
    factories differ in exactly one thing: what ``server:`` says in the copied
    ``binding.yaml``. That is a strictly stronger form of the claim this
    docstring used to make, and it is what makes the wire-failure leg a
    statement about a damaged substrate rather than about a substituted object.
    """
    broken = root.parent / BROKEN_SERVER
    broken.write_text("raise SystemExit(1)\n", encoding="utf-8")
    declare_server(root, broken)
    return McpStdioAdapter(str(root))


#: This transport, as one subject. Named on its own because the controls in
#: ``test_the_mcp_binding_fires.py`` build divergent twins of it.
MCP = AdapterSubject(
    name=SCHEME, connect=connect_over_stdio, break_transport=break_over_stdio
)

#: Both real transports. ``17-07`` wrote *"one subject today; 17-10 appends"*.
SUBJECTS = (*IN_PROCESS, MCP)


def test_served_parity(provision: Provision) -> None:
    """`D-15(a)`: same question, same instant, identical fields and address."""
    suite.assert_served_parity(SUBJECTS, provision=provision, question=QUESTION)


def test_refusal_parity(provision: Provision) -> None:
    """`D-15(b)`: the same governed no, with the same reason, key and kind."""
    suite.assert_refusal_parity(
        SUBJECTS, provision=provision, refusing_question=REFUSING_QUESTION
    )


def test_guard_parity(provision: Provision) -> None:
    """`D-15(c)`: every post-assembly field raises on a refused result."""
    suite.assert_guard_parity(
        SUBJECTS, provision=provision, refusing_question=REFUSING_QUESTION
    )


def test_wire_failure_parity(provision: Provision) -> None:
    """`D-15(d)`: a killed transport raises and a refusal does not."""
    suite.assert_wire_failure_parity(
        SUBJECTS,
        provision=provision,
        question=QUESTION,
        refusing_question=REFUSING_QUESTION,
    )


def test_two_thresholds_are_two_content_addresses(provision: Provision) -> None:
    """`D-23`, through both transports — the caller's number is in the address."""
    suite.assert_two_parameters_are_two_addresses(
        SUBJECTS,
        provision=provision,
        question=QUESTION,
        other_parameters=OTHER_PARAMETERS,
    )


def test_one_question_is_one_content_address(provision: Provision) -> None:
    """`D-23`'s cross-adapter half, now genuinely across two transports."""
    suite.assert_one_question_is_one_address(
        SUBJECTS, provision=provision, question=QUESTION
    )


def test_the_decision_instant_is_auditable(provision: Provision) -> None:
    """`DEF-17-07`, per subject and now over both — each recovers its own instant."""
    suite.assert_decision_instant_is_auditable(
        SUBJECTS,
        provision=provision,
        question=UNPINNED_QUESTION,
        refusing_question=REFUSING_QUESTION,
    )


def test_one_instant_is_one_decision(provision: Provision) -> None:
    """`DEF-17-07`'s cross-adapter half, across two real transports at one instant."""
    suite.assert_one_instant_is_one_decision(
        SUBJECTS, provision=provision, question=QUESTION
    )


def test_a_crossed_echo_is_caught(provision: Provision) -> None:
    """`C-12`/`P3`: both transports' clients refuse an answer to another question."""
    suite.assert_a_crossed_echo_is_caught(
        SUBJECTS, provision=provision, question=QUESTION
    )


def test_an_altered_vessel_is_caught(provision: Provision) -> None:
    """`C-12`/`P3`: both transports' clients refuse a vessel that lost its address."""
    suite.assert_an_altered_vessel_is_caught(
        SUBJECTS, provision=provision, question=QUESTION
    )
