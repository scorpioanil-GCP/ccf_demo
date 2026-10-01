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

from datetime import datetime, timedelta

import pytest

from tests.client.conformance import suite
from tests.client.conformance.suite import Provision
from tests.client.conformance.test_inprocess_conformance import QUESTION, SUBJECTS
from tests.client.fixtures import PINNED_SERVED_AT, SERVED_AT_ENV, STDIO_SERVER


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


def test_two_in_window_instants_agree_across_transports_and_differ_from_each_other(
    provision: Provision, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The companion control: the hash rule stated as four measurements.

    The export-removal control above proves the parity check can DETECT a problem.
    It does not, by itself, prove the thing the rule actually says — that two
    serving instants produce two record versions while one produces one. This does,
    with both instants INSIDE the product's valid serving window so that every
    answer is a served answer rather than a refusal:

    the question is asked as of 12:00, the class declares a 600-second product
    window anchored ``from_decision`` and a 3600-second ceiling, so ``expires_at``
    is 12:10 and the gate admits any serving instant in ``[11:10, 12:10)``. 12:00
    and 12:05 both sit there.

    Four claims, and each would fail differently:

    1. **both transports SERVE at both instants** — without this the rest could be
       satisfied by two refusals agreeing with each other;
    2. **equal instants produce EQUAL replay references** — byte-identical,
       ``@version`` included, across a process boundary;
    3. **distinct instants produce DIFFERENT versions** — which is
       ``D-IMPL-243`` amendment 1 doing what it says: *"Any non-sentinel value is
       rendered and must move the hash"*;
    4. **the record NAME is the same in all four answers** — the determination is
       one determination. Only the stored record differs, which is exactly the
       `24.11-C-01` distinction and the reason dropping the version from the
       comparison would have hidden a real difference rather than tolerated a
       spurious one.

    **And the child process received the instant it was meant to.** Claim 2 is that
    confirmation: the `mcp+stdio` answer's version is a hash over a record the CHILD
    wrote, so its matching the in-process version byte-for-byte can only happen if
    the child served at the same instant. Claim 3 adds that it tracks the export
    rather than ignoring it — a child reading its own wall clock would produce a
    version unrelated to either instant, and both halves would fail.

    ``suite._ask_each`` is reached directly because this control needs the
    references themselves rather than a comparison verdict, and it is the same
    package's own helper.
    """
    instants = (PINNED_SERVED_AT, PINNED_SERVED_AT + timedelta(minutes=5))
    assert instants[0] != instants[1], "the premise of this control moved"
    subjects = (*SUBJECTS, _mcp_subject())

    refs: dict[tuple[datetime, str], str] = {}
    for instant in instants:
        monkeypatch.setenv(SERVED_AT_ENV, instant.isoformat())
        for name, result in suite._ask_each(
            subjects, provision=provision, question=QUESTION
        ).items():
            # (1) every answer is SERVED.
            assert not result.refused, (
                f"`{name}` refused at {instant.isoformat()} — both instants are"
                " inside the declared serving window, so a refusal here means the"
                " window or the pin is wrong and the comparison never happened"
            )
            assert result.replay_ref is not None
            refs[(instant, name)] = result.replay_ref

    names = [name for (_, name) in refs]
    for instant in instants:
        at = {refs[(instant, name)] for name in names}
        # (2) one instant, one reference — `@version` included.
        assert len(at) == 1, (
            f"the transports disagreed at {instant.isoformat()}: {sorted(at)}"
        )

    first, second = ({refs[(i, n)] for n in names}.pop() for i in instants)
    # (3) two instants, two versions.
    assert first != second, (
        "two serving instants produced ONE record version — a non-sentinel"
        " `served_at` is inside the record's hash and must move it"
    )
    # (4) ...and one determination, so only the version moved.
    assert first.rsplit("@", 1)[0] == second.rsplit("@", 1)[0], (
        "the record NAME moved with the instant, so the determination's own"
        " identity is tracking the clock — only the stored record should"
    )
    assert first.rsplit("@", 1)[1] != second.rsplit("@", 1)[1]
