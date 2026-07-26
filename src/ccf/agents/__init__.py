"""The Agent Specialization Framework (CLAUDE.md §6 — SDK-defined extension).

Everything in this package is an **SDK extension beyond the whitepaper**:
Chapter 3 of the whitepaper describes agents as consumers of the fabric; the
specialization framework — archetype/agent separation (§6.1), the two
specialization channels (§6.2), the six archetypes (§6.3), and the Agent &
Task Factory with the No-Hardcoding Rule (§6.4) — is committed by CLAUDE.md,
not by the whitepaper, and every public docstring here says so.

The load-bearing separation: **archetypes are SDK code; agents are declared,
versioned Control Plane artifacts.** This package holds schemas, validators,
archetype mechanism, and factories — never an agent. An agent found in library
code is a defect of the same severity as a hard-coded half-life table
(CLAUDE.md §6.1).
"""

from __future__ import annotations

from ccf.agents.agent import Agent, AgentIdentity, EmittedEffect
from ccf.agents.archetypes import (
    ARCHETYPES,
    ArchetypeComponent,
    ConfigurationDefault,
    ReplayObligation,
    analytics_insights,
    content_generation,
    context_assembly,
    document_intelligence,
    monitoring_surveillance,
    workflow_task,
)
from ccf.agents.composition import (
    ComposedArchetype,
    CompositionContradiction,
    DefaultConflict,
    compose,
)
from ccf.agents.factory import (
    AgentFactory,
    ControlPlaneResolution,
    Task,
    TaskFactory,
    TaskIdentity,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "ARCHETYPES",
    "Agent",
    "AgentFactory",
    "AgentIdentity",
    "ArchetypeComponent",
    "ComposedArchetype",
    "CompositionContradiction",
    "ConfigurationDefault",
    "ControlPlaneResolution",
    "DefaultConflict",
    "EmittedEffect",
    "ReplayObligation",
    "Task",
    "TaskFactory",
    "TaskIdentity",
    "analytics_insights",
    "compose",
    "content_generation",
    "context_assembly",
    "document_intelligence",
    "monitoring_surveillance",
    "workflow_task",
]
