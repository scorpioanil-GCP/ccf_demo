"""The one rule for undeclared wire arguments: refused, never dropped.

SDK-defined (CLAUDE.md §7.3 seam 2, §8.3). ``TP-04`` and ``SEC353-J-01`` are
one defect class and get one rule (``D-IMPL-361``; the v1.0.2 design §7.1
item (e)): a harness or a wire client that supplies an argument the declared
schema does not name is **refused**, by a typed error that names the key. Both
legs dropped such keys before this module existed — google-adk 2.5.0 filters a
tool's arguments to the callable's signature, and FastMCP's argument model is a
pydantic model with ``extra="ignore"`` — so the call proceeded as though the
caller had asked a different question than the one it sent.

The declared schemas both legs advertise already say ``additionalProperties:
false`` (:meth:`~ccf.skills.catalog.SkillArgumentSchema.to_input_schema`); this
is the enforcement that makes the advertisement true.

Private by module name: the two consumers are the ADK adapter and the MCP
tenant guard. Publishing :class:`UndeclaredArgumentRefused` on the SDK surface
is a separate, documented surface change.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

__ccf_mode__ = "algorithmic"

__all__ = [
    "UndeclaredArgumentRefused",
    "refuse_undeclared_arguments",
    "undeclared_arguments",
]


class UndeclaredArgumentRefused(Exception):
    """A caller supplied an argument the surface's declared schema does not name.

    ``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``). Deliberately not a
    ``ValueError``: pydantic converts a ``ValueError`` raised inside a validator
    into its own ``ValidationError``, which would erase this type on the FastMCP
    leg. Raised as itself, the refusal stays typed all the way to the wrapper
    the wire library puts around it.

    Attributes:
        surface: The tool name the arguments were supplied to.
        undeclared: The undeclared keys, sorted, never empty.
    """

    def __init__(self, *, surface: str, undeclared: tuple[str, ...]) -> None:
        self.surface = surface
        self.undeclared = undeclared
        super().__init__(
            f"{surface!r} was supplied undeclared argument(s) {list(undeclared)!r};"
            " an argument the declared schema does not name is refused, never"
            " dropped (TP-04, SEC353-J-01; D-IMPL-361)"
        )


def undeclared_arguments(
    arguments: Mapping[str, object], *, declared: Iterable[str]
) -> tuple[str, ...]:
    """The keys of ``arguments`` that ``declared`` does not name, sorted.

    ``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``). Pure and total: an empty
    tuple means every supplied key is declared.
    """
    names = frozenset(declared)
    return tuple(sorted(key for key in arguments if key not in names))


def refuse_undeclared_arguments(
    arguments: Mapping[str, object], *, declared: Iterable[str], surface: str
) -> None:
    """Raise :class:`UndeclaredArgumentRefused` if any supplied key is undeclared.

    ``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``).
    """
    undeclared = undeclared_arguments(arguments, declared=declared)
    if undeclared:
        raise UndeclaredArgumentRefused(surface=surface, undeclared=undeclared)
