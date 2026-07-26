"""Typed failures of the agent-definition surface (CLAUDE.md §6 — SDK-defined).

The taxonomy mirrors :class:`~ccf.controlplane.artifacts.ArtifactLoadError`:
raised — never repaired — because each failure mode is a silent-corruption
risk if softened. A definition that almost satisfies its schema, or a prompt
whose parameters almost match its template, is exactly the artifact that
produces an unreplayable decision later.

``NotYetBound`` (a skill referenced before any grant bound it) lands with the
skilling plan; it is deliberately absent here rather than stubbed.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__ = ["AgentDefinitionError", "PromptValidationError"]


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
