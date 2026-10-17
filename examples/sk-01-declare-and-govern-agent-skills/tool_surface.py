# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Movement 3 — what a model would see: the agent's tool list, from the Claude Agent SDK adapter.

**THIS FILE IS GLUE, AND IT IS FINDING SK01-F-02.** It is the ONLY file in this
example that constructs ``GrantLedger(``, ``SkillCatalog(`` or ``AgentFactory(``,
and it does so because the SDK gives an adopter no other way to reach the
paved agent's tool surface: :class:`~ccf.products.product.OpenedProduct`
exposes the agent's DEFINITION (``opened.agent``) but no constructed ``Agent``
and no grant ledger, and nothing in ``src/`` or ``runtime/`` builds one from an
opened product. So this file rebuilds what the SDK already built at open — a
second ledger and catalog over the same Control Plane, the agent key
(``opened.keys.agent``) and the content-hash version rule — and it may only run
AFTER the first question has been answered: before that the agent's pinned
debt-profile reference resolves to nothing the Control Plane has registered,
and the factory refuses (``AgentDefinitionError``). None of that is stated on
the public surface; FINDINGS.md records it.

**NO MODEL IS CALLED, AND NOTHING IS SPAWNED.** The adapter is asked for two
pure things: :meth:`expose_skills` (the agent's currently-bound skills, filtered
to the types that have a harness tool surface) and :meth:`inject_context` (the
harness-native ``ClaudeAgentOptions`` carrier, whose ``allowed_tools`` is
exactly that list). No ``ClaudeSDKClient``, no ``query``, no ``transport()``.
The per-call prompt directory the carrier writes is removed before returning.

**WHY THE LIST IS EMPTY, AND WHY THAT IS CORRECT.** This agent's one skill,
``collateral-ask``, asks another product. Its type is ``mcp_product``: the
product performs the ask and admits the answer under the producer's controls,
so it is never a tool a model calls (TP-03). Only ``tool``, ``mcp`` and
``local_callable`` skills appear here — and today an example cannot declare or
grant one (SK01-F-01).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from ccf.agents.factory import AgentFactory
from ccf.contracts.canonical import content_hash
from ccf.products.product import OpenedProduct
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger, RefusingApprovalSink
from ccf.skills.toolsurface import HARNESS_EXPOSABLE_SKILL_TYPES
from ccf_runtime.adapters.claude_agent.adapter import ClaudeAgentAdapter

HERE = Path(__file__).parent


def harness() -> Mapping[str, Any]:
    """The adapter's constructor values (``artifacts/harness.yaml``)."""
    document: Mapping[str, Any] = yaml.safe_load((HERE / "artifacts" / "harness.yaml").read_text(encoding="utf-8"))
    return document["declaration"]


@dataclass(frozen=True)
class ToolSurface:
    """What the harness would be handed for this agent, and why."""

    #: The agent's currently-bound skills, by name, with each one's type.
    bound: Mapping[str, str]
    #: The skill names the adapter exposes as harness tools.
    exposed: tuple[str, ...]
    #: ``ClaudeAgentOptions.allowed_tools`` on the carrier.
    allowed_tools: tuple[str, ...]
    #: The skill types that have a harness tool surface.
    exposable_types: frozenset[str]
    #: The constructed agent's definition hash — equal to ``content_hash(opened.agent)``.
    definition_hash: str


def tool_surface(opened: OpenedProduct, *, instant: datetime) -> ToolSurface:
    """The paved agent's tool surface, through the Claude Agent SDK adapter, with no model call.

    ``instant`` is the grant ledger's clock; this function only READS ledger
    state (``bound_view``), so it records nothing at that instant.
    """
    assert opened.agent is not None and opened.keys.agent is not None
    definition_hash = content_hash(opened.agent)
    # --- SK01-F-02 glue: a second ledger and catalog over the SAME Control Plane ---
    ledger = GrantLedger(
        control_plane=opened.control_plane,
        catalog=SkillCatalog(opened.control_plane),
        sink=RefusingApprovalSink(),
        clock=lambda: instant,
    )
    bound_view = ledger.bound_view(definition_hash)
    agent = AgentFactory(control_plane=opened.control_plane, mcp_skills=opened.mcp_skills).construct(
        definition_key=opened.keys.agent,
        definition_version=definition_hash,
        bound_skills=bound_view,
    )
    # --- end of glue ---------------------------------------------------------------
    values = harness()
    adapter = ClaudeAgentAdapter(
        model=str(values["model"]),
        mcp_server_name=str(values["mcp_server_name"]),
        mcp_server_version=str(values["mcp_server_version"]),
        effects=values["effects"],
    )
    try:
        exposed = adapter.expose_skills(agent=agent)
        carrier: Any = adapter.inject_context(agent=agent, products=(), instructions=())
        allowed = tuple(carrier.allowed_tools)
    finally:
        adapter.remove_prompt_directories()
    return ToolSurface(
        bound={name: str(bound_view[name].skill_type) for name in agent.bound_skill_names},
        exposed=exposed,
        allowed_tools=allowed,
        exposable_types=HARNESS_EXPOSABLE_SKILL_TYPES,
        definition_hash=agent.identity.definition_hash,
    )
