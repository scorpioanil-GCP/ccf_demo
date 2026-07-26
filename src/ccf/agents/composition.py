"""The D-IMPL-19 ordered-composition rules as pure functions.

SDK-defined (CLAUDE.md §6.3 — archetypes are functional categories, not
exclusive categories; a monitoring agent can also be an assembler). Multi-
archetype agents are **ordered composition with explicit conflict rules**
(D-IMPL-19, RESOLVED):

* identical obligations contributed twice are **deduplicated**;
* conflicting configuration defaults resolve by **declaration order**, with
  the conflict reported — the factory converts each reported fact into the
  audible factory warning; this module never emits one, so composition
  stays a pure function of its inputs;
* hard contradictions — the same obligation key contributed with
  incompatible required values — are a **construction error**
  (:class:`CompositionContradiction`).

Identity and equality decisions use
:func:`~ccf.contracts.canonical.canonical_bytes` over the obligation and
default contracts — never Python object identity — so "identical" and
"contradictory" are decidable the same way replay compares anything else
in the fabric (canonical.py: nothing else in the SDK may define its own
canonical form).

Pure functions over typed inputs: no I/O, no clock, no warning emission
(CINV-03). Same inputs, same output; order is meaningful and preserved.
"""

from __future__ import annotations

from collections.abc import Sequence

from ccf.agents.archetypes import (
    ArchetypeComponent,
    ConfigurationDefault,
    ReplayObligation,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes

__ccf_mode__ = "algorithmic"

__all__ = [
    "ComposedArchetype",
    "CompositionContradiction",
    "DefaultConflict",
    "compose",
]


class DefaultConflict(CCFContract):
    """One order-resolved configuration-default conflict (D-IMPL-19).

    A typed fact, not a side effect: the composition result carries the
    conflict so the resolution is never silent — the factory names the key
    and both archetypes in its warning, and the fact itself remains
    canonical-serializable evidence of what was resolved and how.

    Attributes:
        key: The configuration key both archetypes contributed.
        winning_archetype: The first-declared contributor; its value stands.
        winning_value: The value that stands.
        losing_archetype: The later contributor whose value was not taken.
        losing_value: The value that was not taken.
    """

    key: str
    winning_archetype: str
    winning_value: str
    losing_archetype: str
    losing_value: str


class ComposedArchetype(CCFContract):
    """The typed result of composing archetype bundles in declaration order.

    Attributes:
        archetype_ids: The composed identifiers, declaration order preserved
            (channel-1 identity; lands in replay dimension 4).
        obligations: The merged replay obligations, first-contribution order,
            byte-identical contributions deduplicated.
        defaults: The merged configuration defaults, one per key,
            declaration order winning on conflict.
        conflicts: The order-resolved default conflicts, as typed facts.
    """

    archetype_ids: tuple[str, ...]
    obligations: tuple[ReplayObligation, ...]
    defaults: tuple[ConfigurationDefault, ...]
    conflicts: tuple[DefaultConflict, ...]


class CompositionContradiction(ValueError):
    """Two archetypes contribute mutually exclusive obligations.

    The contradiction predicate on the obligation contract: the same
    obligation ``name`` contributed with different required values (canonical
    bytes differ). Unlike a default conflict — a preference the declaration
    order can legitimately resolve — an obligation is a replay requirement,
    and two incompatible requirements under one key cannot both hold.
    Raised, never resolved: the factory propagates it as a construction
    failure (D-IMPL-19 rule 3).
    """


def compose(components: Sequence[ArchetypeComponent]) -> ComposedArchetype:
    """Compose ``components`` in declaration order under the D-IMPL-19 rules.

    Pure: no I/O, no clock, no warning emission — conflicts come back as
    typed facts for the caller (the factory) to report.

    Raises:
        CompositionContradiction: the same obligation key is contributed
            with incompatible required values (rule 3).
    """
    obligations: list[ReplayObligation] = []
    seen_obligation_bytes: set[bytes] = set()
    obligation_owner: dict[str, tuple[str, ReplayObligation]] = {}

    defaults: list[ConfigurationDefault] = []
    default_owner: dict[str, tuple[str, ConfigurationDefault]] = {}
    conflicts: list[DefaultConflict] = []

    for component in components:
        identifier = component.archetype_id
        for obligation in component.replay_obligations():
            rendered = canonical_bytes(obligation)
            if rendered in seen_obligation_bytes:
                continue  # rule 1: identical contributions dedupe
            held = obligation_owner.get(obligation.name)
            if held is not None:
                holder_id, held_obligation = held
                raise CompositionContradiction(
                    f"obligation {obligation.name!r} is contributed with"
                    f" incompatible required values by {holder_id!r}"
                    f" ({held_obligation.obligation!r}) and {identifier!r}"
                    f" ({obligation.obligation!r}); two replay requirements"
                    " under one key cannot both hold (D-IMPL-19 rule 3)"
                )
            seen_obligation_bytes.add(rendered)
            obligation_owner[obligation.name] = (identifier, obligation)
            obligations.append(obligation)
        for default in component.configuration_defaults():
            held_default = default_owner.get(default.name)
            if held_default is None:
                default_owner[default.name] = (identifier, default)
                defaults.append(default)
                continue
            holder_id, winning = held_default
            if canonical_bytes(winning) == canonical_bytes(default):
                continue  # identical default: dedupe, no fact to report
            conflicts.append(  # rule 2: declaration order wins, reported
                DefaultConflict(
                    key=default.name,
                    winning_archetype=holder_id,
                    winning_value=winning.value,
                    losing_archetype=identifier,
                    losing_value=default.value,
                )
            )

    return ComposedArchetype(
        archetype_ids=tuple(c.archetype_id for c in components),
        obligations=tuple(obligations),
        defaults=tuple(defaults),
        conflicts=tuple(conflicts),
    )
