"""The canonical rendering of a request contract's argument schema.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). The rulings of record
are ``D-IMPL-264`` D-00, D-02 as refined by amendment 1 (F-5 d), and
principle P-1 (Dave, 2026-09-05). The whitepaper hook is §6.3
**Addressability**: a product class exposes an interface a caller queries by
name, and what that interface accepts is part of what it declares.

**One declaration of record** (D-00). A closed set of legal values, or a
numeric domain, is declared in exactly one place —
:attr:`ccf.products.request.ProductRequestContract.argument_domains`, as an
:class:`~ccf.products.request.ArgumentDomain` — and this module DERIVES the
advertised ``enum`` and ``minimum`` / ``maximum`` from it. P-1, Dave
verbatim: *"The request contract is the authority for legal values; schemas
and discovery advertise that authority but never independently define it."*
That is why the render is a function over the contract and not a field on
the schema type: :class:`~ccf.skills.catalog.SkillArgumentProperty` has no
``enum`` (it is ``extra=forbid``), so no declaration can plant one — and if
the base render ever carried one anyway, :func:`render_request_input_schema`
refuses it rather than merging two declarations that could disagree.

**Representation without delivery** (D-02 amendment 1, F-5 d). Dave, verbatim:
*"The legal set is intrinsically advertisable contract truth and must have a
canonical SDK rendering. 24.7 does not invent the Experience Layer surface on
which that rendering is published."* And: *"Do not create a new MCP or HTTP
publication surface in 24.7."* **This module publishes nothing.** No MCP
tool or resource, no HTTP route and no CLI verb serves the render, and no
module in ``src/`` or ``runtime/`` consumes it. On which Experience Layer
surface a caller learns the valid vocabulary before asking is carry row
``24.7-C-01`` — the ``D-IMPL-22`` / ``D-IMPL-23`` class of question
(CLAUDE.md §8.3), deferred by ruling and not this module's.

**One parameter, deliberately.** The render takes the contract and nothing
else. D-02, Dave: *"A caller should be able to know the valid vocabulary
before making the request."* Request validity is not a per-caller matter, so
there is no consumer-side conditioning input here; a second parameter would
be exactly the place such a dependence would be introduced, and
``tests/products/test_request_schema_render.py`` pins the signature to one.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ccf.products.request import ArgumentDomain, ProductRequestContract

__ccf_mode__ = "algorithmic"

__all__ = ["render_request_input_schema"]


def render_request_input_schema(contract: ProductRequestContract) -> dict[str, Any]:
    """Render ``contract``'s argument schema with its declared domains derived in.

    Composes :meth:`ccf.skills.catalog.SkillArgumentSchema.to_input_schema`
    over ``contract.arguments`` and then, for each declared
    :class:`~ccf.products.request.ArgumentDomain`, sets exactly one of two
    things on that parameter's property: ``enum`` (the enumerated shape,
    members in declared order) or ``minimum`` and/or ``maximum`` (the
    numeric shape, an absent end not emitted). Pure and total over the
    contract; nothing is authored. A contract with no domains renders
    byte-identically to ``to_input_schema()`` alone.

    Numbers are rendered in the JSON-legal form nearest the author's intent:
    an integral :class:`~decimal.Decimal` becomes an ``int`` and any other
    becomes a ``float``. ``bool`` members stay ``bool`` (the enumerated shape
    reads ``bool`` first — :func:`ccf.products.request._member_class`).

    Raises:
        ValueError: the base render already carries ``enum``, ``minimum`` or
            ``maximum`` on any property. That is a second declaration of
            legal values outside the one declaration of record (D-00, P-1),
            and it is refused by name — on a domained property because it
            would compete with the declaration, on any other because it
            would BE a declaration the contract never made.
    """
    rendered = contract.arguments.to_input_schema()
    properties: dict[str, Any] = rendered["properties"]
    _refuse_a_second_declaration(properties)
    for name, domain in contract.argument_domains.items():
        properties[name].update(_derived_keys(domain))
    return rendered


def _refuse_a_second_declaration(properties: dict[str, Any]) -> None:
    """The base render is not a declaration surface for legal values."""
    for name, spec in properties.items():
        planted = [key for key in ("enum", "minimum", "maximum") if key in spec]
        if planted:
            raise ValueError(
                f"the argument schema's own render carries {planted} on "
                f"parameter {name!r}; the legal values of a parameter have one "
                "declaration of record — ArgumentDomain on the request "
                "contract — and this render derives from it rather than "
                "merging a second declaration that could disagree "
                "(D-IMPL-264 D-00, P-1)"
            )


def _derived_keys(domain: ArgumentDomain) -> dict[str, Any]:
    """What one domain contributes to its parameter's rendered property."""
    if domain.members is not None:
        return {"enum": [_render_value(member) for member in domain.members]}
    derived: dict[str, Any] = {}
    if domain.minimum is not None:
        derived["minimum"] = _render_value(domain.minimum)
    if domain.maximum is not None:
        derived["maximum"] = _render_value(domain.maximum)
    return derived


def _render_value(value: str | int | bool | Decimal) -> str | int | bool | float:
    """One declared value in JSON-legal form; only a Decimal is translated."""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value
