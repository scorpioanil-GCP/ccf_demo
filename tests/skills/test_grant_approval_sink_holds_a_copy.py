# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The approval sink is handed a copy; the ledger keeps and saves its own grant (``D-IMPL-380``, fifth round).

Dave, 2026-10-10 12:57 MST (the ``D-IMPL-380`` amendment, ruling 2 (a)), verbatim: *"Copy before the approver is
handed the grant. An approver that rewrites the ledger's own object leaves a grant in effect whose saved bytes do not
match its id. That is the same hole, one handoff later."* *"The ledger keeps its own copy"* *"has to be true of the
object the approver receives."* And at 13:24 MST: *"The approver receives `grant.model_copy(deep=True)`. The ledger
keeps and saves its own grant. The test requires all three: the saved grant matches its id, the audit entry names the
original, and the ledger's own grant is untouched."*

``src/ccf/skills/grants.py::GrantLedger._decide`` at ``197f5b4f`` handed the approval sink the ledger's own grant
(``outcome = self._sink.decide(grant)``), and every later state write in the same passage is built from that object.
A sink that rewrote it and approved left the grant ``effective`` with a saved record that does not hash to its record
id, a ``grant_effective`` audit ``version`` naming the rewrite, and the caller's object rewritten (builder B-2, Fable
seat F-1 on the fourth-round delta review; reproduced by the coordinator at ``197f5b4f``).

The attacker: an approval sink whose ``decide`` rewrites the ``skill_name`` of the grant it receives
(``object.__setattr__``; a grant is a frozen model) and approves. The world is ``tests/skills/test_grants.py``'s,
under the ``gated`` regime (``grant_requires_approval: true``), so the grant passes through the approval sink. The
three properties are collected before any is asserted, so a red names each one that failed. Fixture vocabulary only
(CINV-01).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.skills.grants import GRANT_STATE, GrantStateRecord, SkillGrant
from tests.skills.test_grants import _World, fixture, instant  # noqa: F401 — pytest fixtures, used by name

SUFFIX = "-approver-rewrite"


def _rewriting_sink(monkeypatch: pytest.MonkeyPatch, world: _World) -> list[str]:
    """Make the world's approval sink rewrite ``skill_name`` on the grant it receives, then decide as scripted."""
    sink = world.sink
    real = sink.decide
    rewrites: list[str] = []

    def decide(grant: SkillGrant) -> Any:
        name = grant.skill_name
        if not name.endswith(SUFFIX):
            object.__setattr__(grant, "skill_name", f"{name}{SUFFIX}")
            rewrites.append(name)
        return real(grant)

    monkeypatch.setattr(sink, "decide", decide)
    return rewrites


def test_an_approver_that_rewrites_the_grant_it_receives_leaves_the_saved_grant_the_audit_and_the_ledgers_grant_as_built(
    fixture: dict[str, Any],  # noqa: F811 — the pytest fixture, used by name
    instant: datetime,  # noqa: F811 — the pytest fixture, used by name
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _World(fixture, instant, approve=True)
    rewrites = _rewriting_sink(monkeypatch, world)
    definition = world.definition("gated")
    grant = world.grant("metrics_tool", definition)
    # Taken before the ledger sees the grant: the sink may rewrite the very object the test holds.
    as_built_hash = content_hash(grant)
    as_built_name = grant.skill_name

    outcome = world.ledger.request(world.grant_cap(definition), grant, definition=definition)

    assert rewrites, "the case was not constructed: the approval sink must have been handed a grant to rewrite"
    assert outcome == as_built_hash, f"the case was not constructed: the grant must have gone effective: {outcome!r}"
    record_id = f"{world.tenant}/{as_built_hash}"
    saved = world.registry.state_store.get(GRANT_STATE, record_id)
    assert isinstance(saved, GrantStateRecord), f"no grant state record under {record_id}: {saved!r}"
    assert saved.state == "effective", f"the case was not constructed: the saved state is {saved.state!r}"
    effective_events = [event for event in world.audit.events() if event.action == "grant_effective"]
    assert len(effective_events) == 1, f"expected one grant_effective event, got {effective_events!r}"

    # Every property is checked before any is asserted, so a red names each one that failed.
    problems: list[str] = []
    # (i) The saved `effective` record's grant hashes to its record id: the grant as built.
    if content_hash(saved.grant) != as_built_hash:
        problems.append(
            f"(i) the saved effective grant hashes to {content_hash(saved.grant)}, not its record id"
            f" {as_built_hash} (saved skill_name {saved.grant.skill_name!r})"
        )
    # (ii) The `grant_effective` audit event names the grant as built.
    if effective_events[0].version != as_built_hash:
        problems.append(
            f"(ii) the grant_effective audit version is {effective_events[0].version}, not the grant as built"
            f" {as_built_hash}"
        )
    # (iii) The ledger's own grant, the caller's object, is untouched.
    if grant.skill_name != as_built_name or content_hash(grant) != as_built_hash:
        problems.append(f"(iii) the ledger's own grant was rewritten to skill_name {grant.skill_name!r}")
    assert not problems, f"outcome {outcome!r}: " + "; ".join(problems)
