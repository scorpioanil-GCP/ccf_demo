"""Skill dispatch for the local_callable and tool types (D-08; CLAUDE.md §6.2).

SDK-defined extension (CLAUDE.md §6, not whitepaper-derived). Dispatch maps
one catalog entry plus typed arguments onto an invocation, per binding type:

* **local_callable** — the ``callable_ref`` is a *key* into the injected
  :class:`~ccf.skills.callables.CallableRegistry`, which the composition root
  populated at boot; the resolved callable is invoked with the arguments
  mapping, must return a ``Mapping[str, str]``, and the result travels back
  as a typed :class:`SkillInvocation` value. This module imports nothing at
  dispatch time: a catalog entry can only name a callable this deployment
  already chose to offer, whatever artifact source the entry arrived from
  (D-19; IN-06).
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

from collections.abc import Mapping

from ccf.agents.errors import NotYetBound
from ccf.contracts.base import CCFContract
from ccf.skills.callables import CallableRegistry
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
    *,
    callable_registry: CallableRegistry,
) -> SkillInvocation:
    """Resolve the entry's declared callable key and call it.

    **The resolved property (D-19, replacing the I.2 IN-06 / T-05-18
    posture).** ``callable_ref`` is a key into ``callable_registry``, which
    this deployment's composition root populated at boot. Dispatch imports
    nothing and looks up no attribute, so an entry naming ``os.system``
    resolves to no registered key and is refused with
    :class:`~ccf.skills.callables.CallableNotRegistered` — without anything
    being imported. I.2 stated a precondition on where the ref came from;
    this function states a property of how it is resolved, which is what the
    MCP and A2A artifact sources of I.3 require (CLAUDE.md §7.2/§7.4).

    The registry is injected, never a module global: two deployments in one
    process resolve against their own registries (D-23).
    """
    target = callable_registry.resolve(binding.callable_ref)
    result = target(dict(arguments))
    if not isinstance(result, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in result.items()
    ):
        raise TypeError(
            f"local callable registered under {binding.callable_ref!r} for skill"
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
    entry: SkillCatalogEntry,
    *,
    arguments: Mapping[str, str],
    callable_registry: CallableRegistry,
) -> SkillInvocation | ToolInvocation:
    """Dispatch one catalog entry with typed arguments (D-08).

    Args:
        entry: The pinned catalog entry a grant made effective. Dispatch
            trusts the entry's *admissibility* because admission did the
            vetting; it does not trust its ``callable_ref`` to name anything
            runnable — that is the registry's to answer (D-19).
        arguments: The typed argument mapping the invocation carries.
        callable_registry: The deployment's boot-time callable registry,
            injected from the composition root. A ``local_callable`` entry
            resolves here or not at all.

    Returns:
        A :class:`SkillInvocation` for an executed ``local_callable``, or a
        :class:`ToolInvocation` value for a ``tool``.

    Raises:
        NotYetBound: the entry is ``mcp`` or ``a2a`` — this build lacks the
            transport (I.3 binds it); nothing about the artifact is bad.
        TypeError: a local callable's result is not a string mapping.
        ccf.skills.callables.CallableNotRegistered: a local callable's
            ``callable_ref`` names no key this deployment registered. An
            exception, not a returned governance refusal: broken wiring or a
            hostile artifact means the deployment is wrong, which is the same
            line the refusal-vs-exception rule already draws.
    """
    binding = entry.binding
    if isinstance(binding, LocalCallableBinding):
        return _invoke_local_callable(
            entry, binding, arguments, callable_registry=callable_registry
        )
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
