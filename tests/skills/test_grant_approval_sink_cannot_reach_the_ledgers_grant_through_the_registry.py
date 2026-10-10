"""An approval sink that reaches the Control Plane registry cannot reach the ledger's own grant (``D-IMPL-380``, sixth round).

The fifth round handed the approval sink ``grant.model_copy(deep=True)``
(``src/ccf/skills/grants.py``, ruling 2 (a)) and its test passed. The Fable
seat on that round's delta review showed the copy was *bypassable*, and the
coordinator reproduced it at ``ef84f801``: the copy is content-identical, so
``skill_grant_key(copy)`` and ``content_hash(copy)`` are exactly the
``(key, version)`` under which ``GrantLedger.request`` filed the ledger's own
object with ``register_versioned``; ``ControlPlaneRegistry.peek`` returned
that instance by reference, unaudited; and a sink that rewrote it left the
saved ``effective`` grant hashing to something other than its record id, the
``grant_effective`` audit version naming the rewrite, the caller's grant
rewritten, and the registry's own ``resolve`` contract broken. Dave, 14:44
MST: *"The copy at the approver is not a fix. The copy has the same content,
so it is the address of the live object. ``registry.peek`` hands that object
back, and the sink rewrites it. The shipped test passes because it never does
that lookup."*

This test does that lookup. It is the exploit the Fable seat wrote, kept as the
regression, with the consistency the sixth-round order requires checked by
name: the grant as built, the approver's view, the caller's result and the
grant audit references all agree.

RED FIRST: fails at ``ef84f801`` on properties (i)–(iv). Green once the
registry holds and serves reconstructions (the sixth-round repair).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.skills.grants import GRANT_STATE, GrantStateRecord, SkillGrant, skill_grant_key
from tests.skills.test_grants import _World, fixture, instant  # noqa: F401

SUFFIX = "-via-registry"


def test_a_sink_that_rewrites_the_grant_it_finds_in_the_registry_changes_nothing_the_ledger_keeps(
    fixture: dict[str, Any], instant: datetime, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    world = _World(fixture, instant, approve=True)
    sink = world.sink
    real = sink.decide
    reached: list[tuple[bool, bool]] = []

    def decide(copy: SkillGrant) -> Any:
        # The sink was handed a copy. The copy's content is the live object's
        # registry address; an unaudited `peek` is the second door.
        live = world.registry.peek(skill_grant_key(copy), content_hash(copy))
        reached.append((live is copy, isinstance(live, SkillGrant)))
        object.__setattr__(live, "skill_name", f"{live.skill_name}{SUFFIX}")
        return real(copy)

    monkeypatch.setattr(sink, "decide", decide)
    definition = world.definition("gated")
    grant = world.grant("metrics_tool", definition)
    as_built_hash = content_hash(grant)
    as_built_name = grant.skill_name

    outcome = world.ledger.request(world.grant_cap(definition), grant, definition=definition)

    # The construction: the sink did reach a SkillGrant through the registry that is not its copy.
    assert reached == [(False, True)], reached

    record_id = f"{world.tenant}/{as_built_hash}"
    saved = world.registry.state_store.get(GRANT_STATE, record_id)
    assert isinstance(saved, GrantStateRecord) and saved.state == "effective", saved
    grant_events = [e for e in world.audit.events() if e.action.startswith("grant_")]
    effective_events = [e for e in grant_events if e.action == "grant_effective"]
    assert len(effective_events) == 1, effective_events

    problems: list[str] = []
    # (i) the saved effective grant is the grant as built, under the id it hashes to
    if content_hash(saved.grant) != as_built_hash:
        problems.append(
            f"(i) the saved effective grant hashes to {content_hash(saved.grant)}, not its record id"
            f" {as_built_hash}; saved skill_name={saved.grant.skill_name!r}"
        )
    # (ii) every grant audit reference names the grant as built
    wrong = [(e.action, e.version) for e in grant_events if e.version != as_built_hash]
    if wrong:
        problems.append(f"(ii) grant audit references name something other than the grant as built: {wrong!r}")
    # (iii) the ledger's and the caller's own grant is untouched
    if grant.skill_name != as_built_name or content_hash(grant) != as_built_hash:
        problems.append(f"(iii) the caller's own grant was rewritten to {grant.skill_name!r}")
    # (iv) the registry's own contract holds: the registered version resolves to content hashing to it
    registered = world.registry.resolve(skill_grant_key(grant), as_built_hash)
    if content_hash(registered) != as_built_hash:
        problems.append(f"(iv) registry.resolve(key, {as_built_hash[:12]}…) returns content hashing to {content_hash(registered)[:12]}…")
    # the approver's view and the caller's result
    if [g.skill_name for g in sink.decided] != [as_built_name]:
        problems.append(f"the approver's view was {[g.skill_name for g in sink.decided]!r}, not [{as_built_name!r}]")
    if outcome != as_built_hash:
        problems.append(f"the caller's result {outcome!r} is not the grant as built {as_built_hash}")
    assert not problems, "\n  ".join(["", *problems])
