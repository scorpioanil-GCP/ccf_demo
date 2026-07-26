"""Skill dispatch for the local_callable and tool types (D-08; CLAUDE.md §6.2).

SDK-defined extension (CLAUDE.md §6, not whitepaper-derived). Dispatch maps
one catalog entry plus typed arguments onto an invocation, per binding type:

* **local_callable** — the dotted ``callable_ref`` is resolved via importlib
  and invoked with the arguments mapping; the callable must return a
  ``Mapping[str, str]``, and the result travels back as a typed
  :class:`SkillInvocation` value. Callables resolve only from entries already
  registered as Control Plane artifacts under the tenant trust boundary —
  the ref value lives in the deployment's artifacts and is never accepted
  from decision-time input (T-05-18).
* **tool** — dispatch returns a typed :class:`ToolInvocation` *value*
  carrying the descriptor's command and the arguments. The SDK executes no
  command: like ``Agent.emit_effect``, the returned value is the entire
  dispatch, and carrying it to an executor is the deployment's business
  (mechanism, never an execution surface).
* **mcp / a2a** — the entry is valid and may be granted, but this build
  ships no MCP/A2A dispatch transport: dispatching one raises the typed
  :class:`~ccf.agents.errors.NotYetBound` exception until I.3 binds the
  transports (D-08; RESEARCH Open Question 2 — resolved as exception, since
  a missing transport is a deployment-shape fact, not a bad artifact).

This module holds no skill, no command, and no callable of its own
(CLAUDE.md §11, CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping

from ccf.agents.errors import NotYetBound
from ccf.contracts.base import CCFContract
from ccf.skills.catalog import (
    LocalCallableBinding,
    SkillCatalogEntry,
    ToolBinding,
)

__ccf_mode__ = "algorithmic"

__all__ = ["SkillInvocation", "ToolInvocation", "dispatch_skill"]


class SkillInvocation(CCFContract):
    """The typed result of one executed ``local_callable`` dispatch.

    Attributes:
        skill_name: The catalog entry invoked.
        skill_type: The entry's binding type.
        output: What the callable returned — a string mapping, so the result
            is canonically serializable and can land in provenance.
    """

    skill_name: str
    skill_type: str
    output: Mapping[str, str]


class ToolInvocation(CCFContract):
    """One ``tool`` dispatch, as a returned value the caller carries onward.

    The effect-as-value discipline (CLAUDE.md §7.3 seam 3): the SDK never
    executes the command — the value is the entire dispatch.

    Attributes:
        skill_name: The catalog entry invoked.
        command: The descriptor command, verbatim from the entry's binding.
        arguments: The typed arguments the invocation carries.
    """

    skill_name: str
    command: str
    arguments: Mapping[str, str]


def _invoke_local_callable(
    entry: SkillCatalogEntry,
    binding: LocalCallableBinding,
    arguments: Mapping[str, str],
) -> SkillInvocation:
    """Import and call the entry's declared callable.

    **Accepted risk, stated so it stays visible (IN-06; T-05-18.)** The
    ``importlib.import_module`` + ``getattr`` below executes arbitrary module
    code at dispatch time. What makes that acceptable is a *precondition* on
    the input, not a property of this function: a ``callable_ref`` reaches
    here only from a Control Plane artifact registered inside the tenant
    trust boundary, which in I.2 means an in-repo fixture.

    That precondition does not survive I.3. Once artifacts can arrive over
    MCP artifact stores or A2A federation (CLAUDE.md §7.2/§7.4), a
    ``callable_ref`` is remote-influenced input and this becomes a remote
    code execution path. ``docs/PHASE_I2_GATE.md`` §5 carries it as an
    explicit I.3 threat-model item, alongside the Jinja2 SSTI deferral; the
    control must be decided there before the first non-in-repo artifact
    source is admitted.
    """
    module_name, _, attribute = binding.callable_ref.rpartition(".")
    if not module_name:
        raise TypeError(
            f"skill {entry.name!r} declares callable_ref"
            f" {binding.callable_ref!r}, which names no module; a dotted"
            " module path is required (D-IMPL-12)"
        )
    module = importlib.import_module(module_name)
    target = getattr(module, attribute)
    result = target(dict(arguments))
    if not isinstance(result, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in result.items()
    ):
        raise TypeError(
            f"local callable {binding.callable_ref!r} for skill"
            f" {entry.name!r} returned {type(result).__name__}, not a"
            " Mapping[str, str]; dispatch results must be canonically"
            " serializable typed values"
        )
    return SkillInvocation(
        skill_name=entry.name,
        skill_type=entry.skill_type,
        output=dict(result),
    )


def dispatch_skill(
    entry: SkillCatalogEntry, *, arguments: Mapping[str, str]
) -> SkillInvocation | ToolInvocation:
    """Dispatch one catalog entry with typed arguments (D-08).

    Args:
        entry: The pinned catalog entry a grant made effective. Dispatch
            trusts the entry's binding because admission did the vetting —
            entries reach this function only through the governed grant path.
        arguments: The typed argument mapping the invocation carries.

    Returns:
        A :class:`SkillInvocation` for an executed ``local_callable``, or a
        :class:`ToolInvocation` value for a ``tool``.

    Raises:
        NotYetBound: the entry is ``mcp`` or ``a2a`` — this build lacks the
            transport (I.3 binds it); nothing about the artifact is bad.
        TypeError: a local callable's ref names no module, or its result is
            not a string mapping.
        ModuleNotFoundError: a local callable's declared module does not
            exist in this deployment.
        AttributeError: the declared module holds no such callable.
    """
    binding = entry.binding
    if isinstance(binding, LocalCallableBinding):
        return _invoke_local_callable(entry, binding, arguments)
    if isinstance(binding, ToolBinding):
        return ToolInvocation(
            skill_name=entry.name,
            command=binding.command,
            arguments=dict(arguments),
        )
    raise NotYetBound(
        f"skill {entry.name!r} is a {entry.skill_type!r} entry, and this"
        " build ships no dispatch transport for that type — I.3 binds the"
        " MCP/A2A transports (D-08); the entry itself is valid and remains"
        " granted"
    )
