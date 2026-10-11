# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The approval sink decides on the grant as built, never on what the state store rewrote (``D-IMPL-380``, fourth round).

Dave, 2026-10-10 10:58 MST (the ``D-IMPL-380`` amendment, ruling 1 (a)), verbatim: *"The skill-grant ledger is the
same hole. Copy before the save. The approver sees the grant as built, not as the store rewrote it. The 09:18
principle already covers it."* The 09:18 principle: *"Do not treat the state store as trusted."*

``src/ccf/skills/grants.py::GrantLedger._put_state`` is the one function every grant state write passes through (the
only ``self._writer.write(`` in the module). At ``06414dbd`` it handed the Control Plane state store
``GrantStateRecord(state=state, grant=grant)`` built around the ledger's OWN ``SkillGrant``, and on the approval path
the ledger writes ``pending-approval`` and then calls ``self._sink.decide(grant)`` with that same object. A state store
that rewrote the grant inside the write had its rewrite reach the approval sink, and the grant went ``effective``
(Fable seat, F-1, probe ``delta-3/fable-probes/test_zz_probe_grant_state_alias.py``; reproduced by the coordinator).

The attacker: a state store whose ``put`` rewrites the ``skill_name`` of the grant inside every grant-state record it
is handed (``object.__setattr__``; a grant is a frozen model) and then saves it. The world is
``tests/skills/test_grants.py``'s, under the ``gated`` regime (``grant_requires_approval: true``), so the grant passes
through the approval sink. The test asserts the sink received a grant equal to the grant as built: its content hash,
and its ``skill_name`` unaltered.

The saved-bytes limit, state-store form, is what this does not test: the state store saves its altered copy, and a
later reader of the saved record reads what it saved. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.skills.grants import GRANT_STATE, GrantStateRecord
from tests.skills.test_grants import _World, fixture, instant  # noqa: F401 — pytest fixtures, used by name

SUFFIX = "-state-store-rewrite"


def _rewriting_state_store(monkeypatch: pytest.MonkeyPatch, world: _World) -> list[str]:
    """Make the registry's state store rewrite ``skill_name`` of the grant in every grant-state record it is handed."""
    store = world.registry.state_store
    real = store.put
    rewrites: list[str] = []

    def put(authorized: Any, record_class: str, record: object, **kwargs: Any) -> Any:
        if record_class == GRANT_STATE and isinstance(record, GrantStateRecord):
            name = record.grant.skill_name
            if not name.endswith(SUFFIX):
                object.__setattr__(record.grant, "skill_name", f"{name}{SUFFIX}")
                rewrites.append(record.state)
        return real(authorized, record_class, record, **kwargs)

    monkeypatch.setattr(store, "put", put)
    return rewrites


def test_a_state_store_that_rewrites_the_grant_leaves_the_approval_sink_deciding_the_grant_as_built(
    fixture: dict[str, Any],  # noqa: F811 — the pytest fixture, used by name
    instant: datetime,  # noqa: F811 — the pytest fixture, used by name
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _World(fixture, instant, approve=True)
    rewrites = _rewriting_state_store(monkeypatch, world)
    definition = world.definition("gated")
    grant = world.grant("metrics_tool", definition)
    # Taken before the ledger sees the grant: the store may rewrite the very object the test holds.
    as_built_hash = content_hash(grant)
    as_built_name = grant.skill_name

    outcome = world.ledger.request(world.grant_cap(definition), grant, definition=definition)

    assert rewrites, "the case was not constructed: the state store must have been handed a grant-state record"
    saved = world.registry.state_store.get(GRANT_STATE, f"{world.tenant}/{as_built_hash}")
    assert isinstance(saved, GrantStateRecord), f"no grant state record: {saved!r}"
    assert saved.grant.skill_name.endswith(SUFFIX), (
        "the case was not constructed: the state store must have saved its rewrite"
    )

    # Every property is checked before any is asserted, so a red names each one that failed.
    problems: list[str] = []
    decided = world.sink.decided
    if len(decided) != 1:
        problems.append(f"the approval sink was asked {len(decided)} times, not once: {decided!r}")
    for seen in decided:
        if seen.skill_name != as_built_name:
            problems.append(f"the approval sink saw skill_name {seen.skill_name!r}, not {as_built_name!r}")
        if content_hash(seen) != as_built_hash:
            problems.append(f"the approval sink saw a grant hashing to {content_hash(seen)}, not {as_built_hash}")
    if grant.skill_name != as_built_name:
        problems.append(f"the caller's own grant was rewritten to skill_name {grant.skill_name!r}")
    assert not problems, f"outcome {outcome!r}: " + "; ".join(problems)
