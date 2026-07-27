"""The callable registry: which local callables a deployment offers by name.

SDK-defined extension (CLAUDE.md §6.2, the skilling channel — not
whitepaper-derived); D-IMPL-37 (explicit boot-time registration, never import
side effects) supplies the registration shape; IN-06 / D-19 supplies the
reason this module exists at all.

Registration is an explicit call at the composition root. No entry points, no
decorators, no import side effects — a registry populated by imports has a
population that depends on import order, and a dispatch is only reproducible
if the registry it resolves against is.

**A ``callable_ref`` is a key here, never a module path.** Dispatch resolves
the reference against what this deployment's composition root registered, and
neither this module nor dispatch imports anything to answer, and neither
resolves a dotted path: a free-form module path is not a value this surface
can express — there is nothing here that could act on one. That is the
D-19 control — it makes the I.2 accepted risk (IN-06; ``docs/PHASE_I2_GATE.md``
§5) unrepresentable rather than merely refused, which matters because I.3 lets
catalog entries arrive over MCP artifact stores and A2A federation
(CLAUDE.md §7.2/§7.4) and so invalidates T-05-18's precondition on the input.

**Append-only, like the Control Plane it mirrors.** There is no ``unregister``
and no overwrite: a duplicate key is fatal at registration rather than a silent
last-writer-wins. Two callables answering to one key means every catalog entry
naming it is ambiguous, and keeping one of them makes the ambiguity invisible.

**Not an ambient namespace.** A registry is an ordinary object held by the
composition root that constructed it. Two deployments in one process each
resolve against their own registry, so neither can observe or shadow the
other's registrations (D-23).

This module holds no callable and no key of its own (CLAUDE.md §11, CINV-01).
Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

__ccf_mode__ = "algorithmic"

__all__ = [
    "CallableNotRegistered",
    "CallableRegistry",
    "DuplicateCallableKey",
    "SkillCallable",
]

#: What a registered local callable must be: one typed argument mapping in,
#: one string mapping out. The same shape dispatch has always invoked — the
#: contract is unchanged, only the way the target is found.
SkillCallable = Callable[[Mapping[str, str]], Mapping[str, str]]


class DuplicateCallableKey(ValueError):
    """A callable key was registered twice (a boot failure, never a merge).

    Deliberately fatal: two callables answering to one key means every catalog
    entry naming it is ambiguous, and silently keeping one of them makes the
    ambiguity invisible.
    """


class CallableNotRegistered(LookupError):
    """A catalog entry named a callable key this deployment does not hold.

    The property the D-19 control buys, stated plainly: the SDK resolves
    callable keys against what this deployment's composition root registered,
    so a catalog entry arriving over MCP or A2A can name nothing this process
    did not already choose to offer. The I.2 posture (IN-06; T-05-18) was a
    *precondition on the input* — that the ref came from an in-repo artifact —
    and I.3 invalidates it; this exception is what replaces it, because
    resolution now consults a table rather than an importer.
    """


class CallableRegistry:
    """Boot-time registry of local callables, with fail-fast duplicate detection."""

    def __init__(self) -> None:
        self._callables: dict[str, SkillCallable] = {}

    def register(self, key: str, fn: SkillCallable) -> None:
        """Register ``fn`` under ``key``.

        Raises:
            DuplicateCallableKey: ``key`` is already registered.
        """
        if key in self._callables:
            raise DuplicateCallableKey(f"callable key {key!r} is already registered")
        self._callables[key] = fn

    def resolve(self, key: str) -> SkillCallable:
        """Return the callable registered under ``key``.

        Raises:
            CallableNotRegistered: nothing is registered under ``key``. Note
                what does *not* happen on this path: no module is imported and
                no attribute is looked up, so an unregistered key costs a
                dictionary miss rather than executing whatever it names.
        """
        try:
            return self._callables[key]
        except KeyError:
            raise CallableNotRegistered(
                f"no callable registered under {key!r}"
            ) from None

    def keys(self) -> tuple[str, ...]:
        """Every registered key, sorted — introspection for the CLI and tests."""
        return tuple(sorted(self._callables))

    def __contains__(self, key: object) -> bool:
        return key in self._callables

    def __len__(self) -> int:
        return len(self._callables)
