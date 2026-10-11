# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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

from ccf.replay.record import DecisionReplayRecord

from tests.client.conformance import suite
from tests.client.conformance.suite import Provision
from tests.client.conformance.test_inprocess_conformance import QUESTION, SUBJECTS
from tests.client.fixtures import PINNED_SERVED_AT, SERVED_AT_ENV, STDIO_SERVER
from tests.issuance import (
    assert_named_by_its_own_content,
    assert_one_determination_issued_twice,
    differences_modulo_issuance,
    modulo_issuance,
)


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

    Four claims, and each would fail differently. **Restated modulo the per-answer
    issuance** (Dave's E1 (a), ``D-IMPL-378``, 2026-10-08 12:29 MST; ``D-IMPL-358``
    ruling 1 and ``D-IMPL-148`` Addendum A read modulo the issuance): every answer's
    record now carries a fresh issuance and is named by its own content address, so
    all four references differ and the claims are made about the RECORDS they
    resolve to, with the issuance set aside:

    1. **both transports SERVE at both instants** — without this the rest could be
       satisfied by two refusals agreeing with each other;
    2. **equal instants produce EQUAL records** — the two transports' references
       resolve to records byte-identical but for the issuance, across a process
       boundary;
    3. **distinct instants produce DIFFERENT records** — which is ``D-IMPL-243``
       amendment 1 doing what it says: *"Any non-sentinel value is rendered and
       must move the hash"*;
    4. **the determination is one determination** — the records at the two
       instants differ in the serving instant and nothing else, which is exactly
       the `24.11-C-01` distinction: only when the answer was handed over moved.

    **And the child process received the instant it was meant to.** Claim 2 is that
    confirmation: the `mcp+stdio` answer's record is one the CHILD wrote, so its
    matching the in-process record byte-for-byte but for the issuance can only
    happen if the child served at the same instant. Claim 3 adds that it tracks the
    export rather than ignoring it — a child reading its own wall clock would write
    a ``served_at`` unrelated to either instant, and both halves would fail.

    ``suite._ask_each`` is reached directly because this control needs the
    references themselves rather than a comparison verdict, and it is the same
    package's own helper.
    """
    instants = (PINNED_SERVED_AT, PINNED_SERVED_AT + timedelta(minutes=5))
    assert instants[0] != instants[1], "the premise of this control moved"
    subjects = (*SUBJECTS, _mcp_subject())

    refs: dict[tuple[datetime, str], str] = {}
    records: dict[tuple[datetime, str], DecisionReplayRecord] = {}
    for instant in instants:
        monkeypatch.setenv(SERVED_AT_ENV, instant.isoformat())
        for name, (result, root) in suite._ask_each_at(
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
            records[(instant, name)] = DecisionReplayRecord.model_validate_json(
                provision.read_record(root, result.replay_ref)
            )
            assert_named_by_its_own_content(
                result.replay_ref, records[(instant, name)], what=f"`{name}` at {instant.isoformat()}"
            )

    # Every answer was issued apart: four answers, four references.
    assert len(set(refs.values())) == len(refs), sorted(refs.values())
    names = sorted({name for (_, name) in refs})
    for instant in instants:
        # (2) one instant, one record — modulo the per-answer issuance.
        first_name, *others = names
        for other in others:
            assert_one_determination_issued_twice(
                records[(instant, first_name)],
                records[(instant, other)],
                what=f"{first_name} versus {other} at {instant.isoformat()}",
            )

    first, second = (records[(instant, names[0])] for instant in instants)
    # (3) two instants, two records — beyond the issuance.
    assert differences_modulo_issuance(first, second) != [], (
        "two serving instants produced ONE record modulo the issuance — a"
        " non-sentinel `served_at` is inside the record's hash and must move it"
    )
    # (4) ...and one determination, so only the serving instant moved.
    assert first.content_generation_path.served_at == instants[0]
    assert second.content_generation_path.served_at == instants[1]
    assert modulo_issuance(first).content_generation_path.model_copy(
        update={"served_at": instants[1]}
    ) == modulo_issuance(second).content_generation_path, (
        "the records at the two instants differ in more than when the answer"
        " was handed over, so the determination itself is tracking the clock"
    )
    assert differences_modulo_issuance(first, second) == ["content_generation_path"]
