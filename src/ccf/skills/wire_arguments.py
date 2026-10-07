"""One argument rule for every skill call: declared, present, and of the declared type.

SDK-defined (CLAUDE.md §6.2 channel 2, §7.3 seam 2, §8.3). ``TP-04`` and
``SEC353-J-01`` are one defect class and get one rule (``D-IMPL-361``; the
v1.0.2 design §7.1 item (e)). The first fix (Task 3) refused an undeclared
wire argument on the ADK leg and at every FastMCP door. Its review measured the
rest of the class: :meth:`ccf.agents.agent.Agent.invoke_skill` — the seam every
harness leg crosses — validated nothing against the bound entry's declared
:class:`~ccf.skills.catalog.SkillArgumentSchema`, so an undeclared key, a
missing required argument and a wrong-typed value were dispatched and audited.

The rule, enforced at that seam before any dispatch (``TP-04`` follow-on,
``D-IMPL-361``):

* **undeclared** — a key the schema does not name is refused by name, never
  dropped;
* **missing** — a required argument that is absent is refused by name;
* **mistyped** — a value whose JSON type is not the declared ``type`` is refused
  by name, never coerced (a list where ``string`` is declared is not its
  ``str``).

The closed world is the same one :meth:`SkillArgumentSchema.to_input_schema`
advertises — ``additionalProperties: false`` at every object level — so the
rule recurses into the one level of declared object members and array elements
the schema can express, and a nested violation is named by its path
(``owner.percent``, ``owners[2].percent``).

**The refusal text is bounded**, because it is audited: each category echoes at
most eight names, each truncated to sixty-four characters, plus the category's total count. The
exception attributes keep every name in full for programmatic use.

Every refusal is an :class:`ArgumentRefused`; the concrete class names the
first category present, in the order undeclared, missing, mistyped, and the
instance carries all three. Deliberately not a ``ValueError``: pydantic
converts a ``ValueError`` raised inside a validator into its own
``ValidationError``, which would erase this type on the FastMCP leg.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ccf.skills.catalog import (
        SkillArgumentElement,
        SkillArgumentMember,
        SkillArgumentProperty,
        SkillArgumentSchema,
    )

__ccf_mode__ = "algorithmic"

__all__ = [
    "ArgumentRefused",
    "MissingArgumentRefused",
    "MistypedArgumentRefused",
    "UndeclaredArgumentRefused",
    "refuse_unconforming_arguments",
    "refuse_undeclared_arguments",
    "undeclared_arguments",
]

#: How many names one refusal category echoes into the refusal text. A bound
#: on the audited reason field, not a policy value.
_ECHOED_KEY_LIMIT = 8

#: How many characters of each echoed name the refusal text carries.
_ECHOED_KEY_CHARACTERS = 64


def _echo(names: tuple[str, ...]) -> str:
    shown = [name[:_ECHOED_KEY_CHARACTERS] for name in names[:_ECHOED_KEY_LIMIT]]
    return f"{shown!r} ({len(names)} total)"


class ArgumentRefused(Exception):
    """Presented arguments violate the surface's declared argument schema.

    ``TP-04`` follow-on (``D-IMPL-361``). The family root: catch this to catch
    every refusal of the one argument rule. The concrete subclass raised names
    the first category present (undeclared, then missing, then mistyped); the
    instance carries all three.

    Attributes:
        surface: The skill or tool name the arguments were presented to.
        undeclared: Keys (or nested paths) the schema does not name, sorted.
        missing: Required names (or nested paths) that are absent, sorted.
        mistyped: Names (or nested paths) whose value is not the declared
            JSON type, sorted.
    """

    def __init__(
        self,
        *,
        surface: str,
        undeclared: tuple[str, ...] = (),
        missing: tuple[str, ...] = (),
        mistyped: tuple[str, ...] = (),
    ) -> None:
        self.surface = surface
        self.undeclared = undeclared
        self.missing = missing
        self.mistyped = mistyped
        faults = [
            f"{label} {_echo(names)}"
            for label, names in (
                ("undeclared argument(s)", undeclared),
                ("missing required argument(s)", missing),
                ("argument(s) not of the declared type", mistyped),
            )
            if names
        ]
        super().__init__(
            f"{surface[:_ECHOED_KEY_CHARACTERS]!r} was refused its arguments: "
            + "; ".join(faults)
            + " — arguments must be exactly what the declared schema names,"
            " present where required and of the declared type; they are"
            " refused, never dropped or coerced (TP-04, SEC353-J-01; D-IMPL-361)"
        )


class UndeclaredArgumentRefused(ArgumentRefused):
    """A caller supplied an argument the surface's declared schema does not name.

    ``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``). Raised when any undeclared key
    is present, whatever else is wrong.
    """


class MissingArgumentRefused(ArgumentRefused):
    """A required argument of the declared schema is absent.

    ``TP-04`` follow-on (``D-IMPL-361``). Raised when no key is undeclared and
    at least one required argument is missing.
    """


class MistypedArgumentRefused(ArgumentRefused):
    """An argument's value is not of the JSON type the declared schema names.

    ``TP-04`` follow-on (``D-IMPL-361``). Raised when every key is declared and
    present and at least one value has the wrong type.
    """


def _conforms(value: object, declared: str) -> bool:
    """Whether ``value`` is an instance of the declared JSON Schema type.

    ``bool`` is not a number here (JSON keeps them apart even though Python
    does not), a float with no fractional part is an ``integer`` (as JSON
    Schema says), and a non-finite float is no JSON number at all.
    """
    if declared == "string":
        return isinstance(value, str)
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "integer":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (
            isinstance(value, float) and math.isfinite(value) and value.is_integer()
        )
    if declared == "number":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (
            isinstance(value, float) and math.isfinite(value)
        )
    if declared == "array":
        return isinstance(value, (list, tuple))
    if declared == "object":
        return isinstance(value, Mapping)
    return False  # pragma: no cover - JsonSchemaType is a closed Literal


def _object_violations(
    arguments: Mapping[Any, object],
    *,
    properties: Mapping[str, SkillArgumentProperty]
    | Mapping[str, SkillArgumentMember],
    required: Iterable[str],
    prefix: str,
) -> Iterator[tuple[str, str]]:
    """``(category, path)`` for every violation in one object level."""
    for key in arguments:
        if key not in properties:
            yield "undeclared", f"{prefix}{key}"
    for name in required:
        if name not in arguments:
            yield "missing", f"{prefix}{name}"
    for name, spec in properties.items():
        if name in arguments:
            yield from _value_violations(arguments[name], spec=spec, path=f"{prefix}{name}")


def _value_violations(
    value: object,
    *,
    spec: SkillArgumentProperty | SkillArgumentElement | SkillArgumentMember,
    path: str,
) -> Iterator[tuple[str, str]]:
    """Violations of one value against its spec, recursing into declared nesting."""
    if not _conforms(value, spec.type):
        yield "mistyped", path
        return
    members = getattr(spec, "properties", None)
    if members is not None and isinstance(value, Mapping):
        yield from _object_violations(
            value,
            properties=members,
            required=getattr(spec, "required", ()),
            prefix=f"{path}.",
        )
    element = getattr(spec, "items", None)
    if element is not None and isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _value_violations(item, spec=element, path=f"{path}[{index}]")


def _argument_violations(
    arguments: Mapping[str, object], *, schema: SkillArgumentSchema
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """``(undeclared, missing, mistyped)`` for ``arguments`` against ``schema``.

    ``TP-04`` follow-on (``D-IMPL-361``). Pure and total: three empty tuples
    mean the arguments conform. Each tuple is sorted.
    """
    found: dict[str, list[str]] = {"undeclared": [], "missing": [], "mistyped": []}
    for category, path in _object_violations(
        arguments, properties=schema.properties, required=schema.required, prefix=""
    ):
        found[category].append(path)
    return (
        tuple(sorted(found["undeclared"])),
        tuple(sorted(found["missing"])),
        tuple(sorted(found["mistyped"])),
    )


def refuse_unconforming_arguments(
    arguments: Mapping[str, object], *, schema: SkillArgumentSchema, surface: str
) -> None:
    """Raise the :class:`ArgumentRefused` family unless ``arguments`` conform.

    ``TP-04`` follow-on (``D-IMPL-361``). The one rule: every key declared,
    every required argument present, every value of its declared JSON type —
    at the top level and through the declared nesting.

    Raises:
        UndeclaredArgumentRefused: a key (or nested key) is undeclared.
        MissingArgumentRefused: otherwise, a required argument is absent.
        MistypedArgumentRefused: otherwise, a value has the wrong type.
    """
    undeclared, missing, mistyped = _argument_violations(arguments, schema=schema)
    refused: type[ArgumentRefused]
    if undeclared:
        refused = UndeclaredArgumentRefused
    elif missing:
        refused = MissingArgumentRefused
    elif mistyped:
        refused = MistypedArgumentRefused
    else:
        return
    raise refused(
        surface=surface, undeclared=undeclared, missing=missing, mistyped=mistyped
    )


def undeclared_arguments(
    arguments: Mapping[str, object], *, declared: Iterable[str]
) -> tuple[str, ...]:
    """The keys of ``arguments`` that ``declared`` does not name, sorted.

    ``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``). Pure and total: an empty
    tuple means every supplied key is declared. For a surface whose declared
    names are all it knows (a FastMCP argument model) rather than a
    :class:`~ccf.skills.catalog.SkillArgumentSchema`.
    """
    names = frozenset(declared)
    return tuple(sorted(key for key in arguments if key not in names))


def refuse_undeclared_arguments(
    arguments: Mapping[str, object], *, declared: Iterable[str], surface: str
) -> None:
    """Raise :class:`UndeclaredArgumentRefused` if any supplied key is undeclared.

    ``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``). The undeclared-key half of the
    rule alone, for a surface that holds declared names but no
    :class:`~ccf.skills.catalog.SkillArgumentSchema`; its message shape is the
    family's.
    """
    undeclared = undeclared_arguments(arguments, declared=declared)
    if undeclared:
        raise UndeclaredArgumentRefused(surface=surface, undeclared=undeclared)
