"""`D-IMPL-358` step 5: the injected fabric clock, and why the parity legs pass.

**What this module guards.** `served_at` is read once per governed invocation and
is non-sentinel, so it is INSIDE the replay record's hash — Dave's own rule in
``ccf/contracts/canonical.py``: *"Any non-sentinel value is rendered and must move
the hash."* Two serves at two wall times are therefore two record versions, by
design. The conformance parity legs compare `replay_ref` across transports, and
their own contract has always been *"the same question **at the same instant**"* —
a condition the fixture did not establish until the clock became injectable.

So the legs are green because BOTH subjects are composed against one now, and
these two controls hold exactly that: the channel that carries the instant to a
child process cannot drift, and removing it turns the parity leg red.
"""

from __future__ import annotations

import pytest

from tests.client.conformance import suite
from tests.client.conformance.suite import Provision
from tests.client.conformance.test_inprocess_conformance import QUESTION, SUBJECTS
from tests.client.fixtures import SERVED_AT_ENV, STDIO_SERVER


def test_the_two_spellings_of_the_channel_agree() -> None:
    """The server program spells the env var; this holds it to the constant.

    ``stdio_server.py`` is launched as a PROGRAM, so it has no package context
    through which to import its own package, and the name is spelled there. A
    second spelling is admissible in this codebase only when something holds the
    two equal — otherwise renaming the constant would silently stop pinning the
    child and every parity leg would go on passing on the in-process side while
    comparing it against a live clock.
    """
    source = STDIO_SERVER.read_text(encoding="utf-8")
    assert f'_SERVED_AT_ENV = "{SERVED_AT_ENV}"' in source, (
        f"the server program does not spell {SERVED_AT_ENV!r}; the pin no longer"
        " reaches the child process"
    )


def test_without_the_pin_the_transports_disagree(
    provision: Provision, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: the parity legs are green BECAUSE of the pin.

    Removing the export leaves the child composing against the real fabric clock
    while the in-process subject stays pinned, so the two answer one question at
    two instants and their replay records take two versions. If this passed, the
    pin would be decoration and the parity legs would be green for some other
    reason — which is the state this whole module exists to rule out.

    It asserts the DISAGREEMENT, not a particular message: what matters is that
    the comparison fails, and pinning the wording would make this control break
    every time the suite improves its own reporting.
    """
    monkeypatch.delenv(SERVED_AT_ENV, raising=False)

    with pytest.raises(AssertionError):
        suite.assert_served_parity(
            (*SUBJECTS, _mcp_subject()), provision=provision, question=QUESTION
        )


def _mcp_subject() -> object:
    """The `mcp+stdio` subject, imported late so a collection error names itself."""
    from tests.client.conformance.test_mcp_conformance import MCP

    return MCP
