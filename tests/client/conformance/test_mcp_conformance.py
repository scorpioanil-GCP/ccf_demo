"""The `mcp+stdio` transport, bound into the conformance suite as its second subject.

``D-15``, and **the acceptance test for plan ``17-07``'s design**: ``suite.py``
said a second module exactly like the first would change nothing in it, and
binding a real second transport is what makes that claim non-trivial. A factory,
a break hook and one call per property were the whole of it —
``git diff tests/client/conformance/suite.py`` is empty.

Every leg but the last compares **both** subjects, so the cross-adapter
comparisons stop degenerating to self-comparisons. The questions are imported
from the in-process binding rather than restated, so *the same question* is
literally the same object and cannot drift into two.

**The last leg takes the MCP subject alone, and that is a finding rather than a
dodge.** ``assert_decision_instant_is_auditable`` refuses a question that names
its own instant and then compares the recovered ``graph_snapshot_at`` *across*
subjects — but with ``as_of=None`` each subject reads a clock, so two of them
recover two instants milliseconds apart (measured: 116 ms). The leg is therefore
unsatisfiable for **any** two subjects, MCP or not. Its per-subject property is
real and is asserted here; the plan's SUMMARY records the cross-subject half as
a defect in ``17-07``. Narrowing the assertion was not open — ``D-IMPL-148``
rules that the suite is not weakened to admit an adapter.
"""

from __future__ import annotations

import shlex
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
from tests.client.fixtures import STDIO_SERVER

pytestmark = pytest.mark.conformance

#: The program the break hook writes, beside the deployment and never inside it
#: — a deployment root holds one Python module by ``D-IMPL-141`` Amendment A.3.
BROKEN_SERVER = "broken_server.py"


def connect_over_stdio(root: Path) -> McpStdioAdapter:
    """A healthy adapter launching this deployment's own server against ``root``."""
    return McpStdioAdapter(shlex.join([str(STDIO_SERVER), str(root)]))


def break_over_stdio(root: Path) -> McpStdioAdapter:
    """Point the binding at a program that dies, so the pipe closes on the client.

    The hook owns this root, raises nothing itself, and returns the same class
    the healthy factory returns — so the leg measures a damaged substrate rather
    than a substituted object.
    """
    broken = root.parent / BROKEN_SERVER
    broken.write_text("raise SystemExit(1)\n", encoding="utf-8")
    return McpStdioAdapter(shlex.join([str(broken), str(root)]))


#: This transport alone, for the one leg that cannot compare two.
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
    """`DEF-17-07`, per-subject — see the module docstring for why not both."""
    suite.assert_decision_instant_is_auditable(
        (MCP,),
        provision=provision,
        question=UNPINNED_QUESTION,
        refusing_question=REFUSING_QUESTION,
    )
