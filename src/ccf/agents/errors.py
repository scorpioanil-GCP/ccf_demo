"""Typed failures of the agent-definition surface (CLAUDE.md §6 — SDK-defined).

The taxonomy mirrors :class:`~ccf.controlplane.artifacts.ArtifactLoadError`:
raised — never repaired — because each failure mode is a silent-corruption
risk if softened. A definition that almost satisfies its schema, or a prompt
whose parameters almost match its template, is exactly the artifact that
produces an unreplayable decision later.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__ = [
    "AgentConstructionError",
    "AgentDefinitionError",
    "ConsumptionRefused",
    "NotYetBound",
    "PromptValidationError",
    "SkillNotBound",
]


class AgentDefinitionError(ValueError):
    """An agent definition artifact cannot be admitted as written.

    Raised — never repaired — for defects the schema alone cannot express:
    the schema layer refuses malformed documents at parse time, and this error
    covers definition-level rule violations discovered after parsing
    (CLAUDE.md §6.4; D-IMPL-28).
    """


class PromptValidationError(ValueError):
    """A prompt artifact or instruction binding fails parse-only validation.

    Raised — never repaired — when a template's undeclared variables and its
    declared parameters differ in either direction, when a binding's declared
    parameters mismatch the artifact's, or when the template itself does not
    parse (D-13; CLAUDE.md §6.2 axis 6).
    """


class AgentConstructionError(ValueError):
    """The inputs handed to ``Agent`` do not describe one coherent agent.

    Raised by the ``Agent`` constructor when the identity block, the
    definition, and the composed components disagree — a mismatched content
    hash, a composition that is not the definition's declared archetype list,
    or components that do not realize it. The factory computes these inputs
    from one resolved definition, so this firing means construction was
    attempted around the factory or against drifted state (CLAUDE.md §6.4;
    D-12: the constructor validates, the lint enforces no-bypass — no token).
    """


class SkillNotBound(KeyError):
    """An agent was asked to invoke a skill no grant has bound to it.

    ``KeyError``-shaped because the bound skill-set is a mapping and an absent
    capability is an absent key — but typed, because "this agent does not
    currently have that capability" is a governance fact (CLAUDE.md §6.2
    channel 2), not a lookup accident. Grants land with the skilling wave.
    """


class NotYetBound(RuntimeError):
    """A granted ``mcp`` or ``a2a`` skill was dispatched in a build that
    lacks its transport.

    An **exception, not a returned refusal**, and the line is deliberate
    (PATTERNS "Refusal vs exception line"; 05-RESEARCH.md Open Question 2 —
    RESOLVED as typed exception): nothing about the artifact is bad — the
    entry validated, registered, and passed both governance tiers — but this
    *build* ships no MCP/A2A dispatch transport (D-08; I.3 binds them).
    A missing transport is a deployment-shape fact, like a missing Control
    Plane key, not an expected governance outcome a caller inspects.
    """


class ConsumptionRefused(ValueError):
    """A Context Product was refused at the agent's consumption seam.

    Raised — never degraded around — when a product falls outside the agent's
    context contract (axis 2), belongs to another tenant, or is TTL-expired:
    an expired product is contract-invalid, not stale (INV-CH6-05; DESIGN.md
    §3.1 — the base refuses rather than degrading).
    """
