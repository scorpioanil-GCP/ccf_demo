"""The ``provision`` fixture hands out a root whose ``server:`` RESOLVES.

``T-18.1-13``. ``binding.yaml``'s ``server:`` key resolves against the
directory **holding** the deployment (``D-10``), and the committed fixture and
its program ship in that relationship. A copy that took only ``deployment/``
would inherit a declaration pointing at nothing.

**Nothing reads that value yet.** The conformance factories still build the
two-token ``mcp+stdio`` address, so an unprovisioned root would sit here
silently until the grammar flip in ``18.1-02`` — at which point every MCP leg
would fail, and, worse, the *healthy* leg would fail alongside the refusal
legs. A key-absent refusal cannot be told apart from a harness that is simply
broken, so ``D-06``'s control would pass for the wrong reason. That is the
defect ``CLNT-12`` exists to prevent, and it has been realized in this phase
once already: ``18.1-PATTERNS.md`` §5(b) claimed this provisioning was
unnecessary and two plans inherited the error.

This module exists because a provisioning site nothing asserts on is a
provisioning site nobody watches failing. It is the assertion that makes the
wiring in ``conftest.py`` a check rather than a hope.
"""

from __future__ import annotations

import pytest

from ccf.client.adapters.binding_document import load_binding_document

from tests.client.conformance.suite import Provision

pytestmark = pytest.mark.conformance


def test_a_provisioned_root_declares_a_program_that_is_there(
    provision: Provision,
) -> None:
    """The positive claim, on the fixture the whole conformance package uses."""
    root = provision("declares-a-server")

    document = load_binding_document(root)

    assert document.server is not None, "the copied deployment declares a server"
    assert document.server.is_file(), (
        "and the program is actually there — a declaration resolving to nothing"
        " is what makes a later refusal fire for the wrong reason"
    )
    assert document.server.parent == root.parent.resolve(), (
        "in the copied root's PARENT, which is where `server:` resolves"
    )


def test_every_root_the_fixture_hands_out_is_provisioned(
    provision: Provision,
) -> None:
    """Not just the first one.

    ``provision`` hands out a fresh directory per call and a single test runs
    two legs. A site that provisioned only the root it happened to be asked for
    first would satisfy the check above and break the second transport.
    """
    roots = [provision("first"), provision("second")]

    assert len({root.parent for root in roots}) == 2, "two distinct deployments"
    for root in roots:
        server = load_binding_document(root).server
        assert server is not None and server.is_file(), (
            f"the root at {root} declares a program that is not there"
        )
