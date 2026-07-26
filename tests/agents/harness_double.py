"""The D-03 test-double harness driver — /tests only, never ships.

This is **NOT a harness** (CLAUDE.md §7.3: CCF never ships or absorbs an
agent loop, and this module is not an exception — it is the proof that the
slice can be exercised without one). It is a linear, deterministic script
that drives the concrete ``Agent``'s three fabric seams exactly once each,
in a fixed order, and returns what came back:

1. consume one prepared Context Product,
2. attempt one bound-skill invocation by name (for an ungranted name the
   typed ``SkillNotBound`` is the *expected* outcome and is captured, never
   retried; for a name a governed grant bound — grants landed in 05-06 —
   the invocation succeeds and ``None`` is returned in its place),
3. emit one effect as a returned typed value.

No loop over agent turns, no retries, no branching on outputs, no model, no
clock reads — ``now`` is supplied by the caller like every other instant in
the fabric. It imports no harness package and lives in ``/tests`` fixtures
only (D-03; RESEARCH Pitfall 5: any convenience feature added here is the
start of a de-facto loop and a review defect).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.errors import SkillNotBound
from ccf.products.contract import ContextProductContract


def drive_slice(
    *,
    agent: Agent,
    product: ContextProductContract,
    now: datetime,
    skill_name: str,
    effect_payload: Mapping[str, Any],
) -> tuple[ContextProductContract, SkillNotBound | None, EmittedEffect]:
    """Drive the three seams once each, sequentially and deterministically.

    Returns the consumed product, the typed unbound-skill error (``None``
    when a governed grant bound ``skill_name`` — the live channel-2 path
    since 05-06), and the emitted effect value.
    """
    consumed = agent.consume(product, now=now)
    unbound: SkillNotBound | None
    try:
        agent.invoke_skill(skill_name)
    except SkillNotBound as error:
        unbound = error
    else:
        unbound = None
    effect = agent.emit_effect(effect_payload)
    return consumed, unbound, effect
