"""The canonical request-contract render — representation without delivery.

``D-IMPL-264`` D-00 (*one declaration of record*), D-02 as amended by
amendment 1 F-5 d, and principle P-1. Dave, verbatim: *"The legal set is
intrinsically advertisable contract truth and must have a canonical SDK
rendering. 24.7 does not invent the Experience Layer surface on which that
rendering is published."* And P-1: *"The request contract is the authority
for legal values; schemas and discovery advertise that authority but never
independently define it."*

What is asserted here, and nothing more:

* the render composes :meth:`ccf.skills.catalog.SkillArgumentSchema.to_input_schema`
  with :attr:`ccf.products.request.ProductRequestContract.argument_domains` —
  an enumerated domain becomes ``enum``, numeric bounds become ``minimum`` /
  ``maximum`` — and a contract with no domains renders byte-identically to
  the argument schema alone;
* the render reads :class:`~ccf.products.request.ArgumentDomain` ONLY: a
  second declaration planted on the base render is refused, not merged;
* the render takes the contract and nothing else — no consumer-side
  conditioning parameter exists to gate what a caller may learn before
  asking, because request validity is not a per-caller matter (D-02).

Nothing here publishes anything: no MCP tool, no HTTP route, no CLI verb
serves the render. That surface is carry row ``24.7-C-01``, deferred by
ruling. Criterion 8.
"""

from __future__ import annotations

import inspect
import json
from decimal import Decimal
from typing import Any

import pytest

from ccf.products.request import ArgumentDomain, ProductRequestContract
from ccf.skills.catalog import (
    SkillArgumentElement,
    SkillArgumentMember,
    SkillArgumentProperty,
    SkillArgumentSchema,
)

CLASS_NAME = "fixture.render"
CLASS_VERSION = "1.0.0"

REQUIRED_LEAF = "required_leaf"
OPTIONAL_LEAF = "optional_leaf"
FLAG = "flag"
RATIO = "ratio"


def _arguments() -> SkillArgumentSchema:
    """A declared parameter surface over every primitive type plus a nest."""
    return SkillArgumentSchema(
        properties={
            REQUIRED_LEAF: SkillArgumentProperty(
                type="string", description="a required top-level parameter"
            ),
            OPTIONAL_LEAF: SkillArgumentProperty(
                type="integer", description="an optional top-level parameter"
            ),
            FLAG: SkillArgumentProperty(type="boolean", description="a flag"),
            RATIO: SkillArgumentProperty(type="number", description="a ratio"),
            "nested": SkillArgumentProperty(
                type="object",
                description="a one-level nested parameter",
                properties={
                    "member": SkillArgumentMember(
                        type="string", description="a nested member"
                    )
                },
                required=("member",),
            ),
            "listed": SkillArgumentProperty(
                type="array",
                description="a list of objects",
                items=SkillArgumentElement(
                    type="object",
                    description="one element",
                    properties={
                        "element_member": SkillArgumentMember(
                            type="string", description="an element member"
                        )
                    },
                    required=("element_member",),
                ),
            ),
        },
        required=(REQUIRED_LEAF,),
    )


def _contract(**overrides: Any) -> ProductRequestContract:
    fields: dict[str, Any] = {
        "semver": "1.0.0",
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "arguments": _arguments(),
    }
    fields.update(overrides)
    return ProductRequestContract(**fields)


def _render(contract: ProductRequestContract) -> dict[str, Any]:
    from ccf.products.request_schema import render_request_input_schema

    return render_request_input_schema(contract)


def _canonical(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True)


# --- (1) no domains: the render IS the argument schema -----------------------


def test_a_contract_with_no_domains_renders_byte_identically_to_the_argument_schema() -> None:
    """P-1's null case: with nothing to derive, nothing is authored."""
    contract = _contract()
    rendered = _render(contract)
    base = contract.arguments.to_input_schema()

    assert rendered == base
    assert _canonical(rendered) == _canonical(base)
    # And the closed-world keys are the argument schema's own, untouched.
    assert rendered["additionalProperties"] is False
    assert rendered["required"] == [REQUIRED_LEAF]
    assert rendered["properties"]["nested"]["additionalProperties"] is False
    assert (
        rendered["properties"]["listed"]["items"]["additionalProperties"] is False
    )


# --- (2) an enumerated domain renders its members as `enum` ------------------


@pytest.mark.parametrize(
    ("parameter", "members", "expected"),
    [
        (REQUIRED_LEAF, ("alpha", "beta"), ["alpha", "beta"]),
        (OPTIONAL_LEAF, (1, 2), [1, 2]),
        (FLAG, (True,), [True]),
        (RATIO, (Decimal("0.5"), Decimal("2")), [0.5, 2]),
    ],
    ids=["string", "integer", "boolean", "number"],
)
def test_an_enumerated_domain_renders_its_members_as_enum(
    parameter: str, members: tuple[Any, ...], expected: list[Any]
) -> None:
    """Members in declared order; an integral Decimal renders as an int.

    ``D-IMPL-264`` D-06 (Dave: *"Any supported primitive type ... Don't
    unnecessarily make this string-specific."*). The Decimal rule — integral
    → ``int``, otherwise ``float`` — is pinned HERE so a later renderer
    cannot quietly emit ``"2"`` or ``2.0`` and still pass.
    """
    contract = _contract(argument_domains={parameter: ArgumentDomain(members=members)})
    rendered = _render(contract)
    base = contract.arguments.to_input_schema()

    property_rendered = rendered["properties"][parameter]
    assert property_rendered["enum"] == expected
    assert [type(value) for value in property_rendered["enum"]] == [
        type(value) for value in expected
    ]
    assert "minimum" not in property_rendered
    assert "maximum" not in property_rendered
    # Everything else on the property is the base render's, exactly.
    assert {k: v for k, v in property_rendered.items() if k != "enum"} == (
        base["properties"][parameter]
    )
    # And no OTHER property moved.
    for name, spec in base["properties"].items():
        if name != parameter:
            assert rendered["properties"][name] == spec, name
    assert rendered["required"] == base["required"]
    assert rendered["additionalProperties"] is base["additionalProperties"]
    assert rendered["type"] == base["type"]
    # The render is JSON-legal as rendered: `json.dumps` accepts it whole.
    assert json.loads(_canonical(rendered))["properties"][parameter]["enum"] == (
        expected
    )


# --- (3) numeric bounds render `minimum` / `maximum` -------------------------


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        (ArgumentDomain(minimum=Decimal("1")), {"minimum": 1}),
        (ArgumentDomain(maximum=Decimal("100")), {"maximum": 100}),
        (
            ArgumentDomain(minimum=Decimal("0.25"), maximum=Decimal("1")),
            {"minimum": 0.25, "maximum": 1},
        ),
    ],
    ids=["floor-only", "ceiling-only", "both"],
)
def test_numeric_bounds_render_minimum_and_maximum(
    domain: ArgumentDomain, expected: dict[str, Any]
) -> None:
    """An absent end is not emitted; the Decimal rule is the enum rule."""
    contract = _contract(argument_domains={OPTIONAL_LEAF: domain})
    rendered = _render(contract)
    base = contract.arguments.to_input_schema()

    property_rendered = rendered["properties"][OPTIONAL_LEAF]
    for key in ("minimum", "maximum"):
        if key in expected:
            assert property_rendered[key] == expected[key]
            assert type(property_rendered[key]) is type(expected[key])
        else:
            assert key not in property_rendered
    assert "enum" not in property_rendered
    assert {
        k: v for k, v in property_rendered.items() if k not in ("minimum", "maximum")
    } == base["properties"][OPTIONAL_LEAF]


def test_two_domains_render_side_by_side() -> None:
    contract = _contract(
        argument_domains={
            REQUIRED_LEAF: ArgumentDomain(members=("alpha",)),
            OPTIONAL_LEAF: ArgumentDomain(minimum=Decimal("1")),
        }
    )
    rendered = _render(contract)
    assert rendered["properties"][REQUIRED_LEAF]["enum"] == ["alpha"]
    assert rendered["properties"][OPTIONAL_LEAF]["minimum"] == 1


# --- (2b) a grammar domain renders its pattern as `pattern` (D-IMPL-357 C4) --


#: The fixture's grammar, never the SDK's (CINV-01).
GRAMMAR = r"[0-9A-Z]{20}"


def test_the_render_advertises_pattern_and_refuses_a_planted_one() -> None:
    """The third shape's derivation. `D-IMPL-357` C4 on P-1's terms: the
    contract is the authority and this module ADVERTISES it, so a declared
    grammar reaches a caller as JSON Schema's own `pattern` keyword rather
    than as a second declaration written here. The planted half is the
    parametrized refusal in section (4), extended with `"pattern"`.
    """
    from ccf.products.request_schema import render_request_input_schema

    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(pattern=GRAMMAR)}
    )
    rendered = render_request_input_schema(contract)
    # ANCHORED on the way out (D-IMPL-357, close panel finding B-1). The
    # declared grammar is judged by `re.fullmatch`; JSON Schema `pattern` is a
    # PARTIAL match, so the verbatim spelling this line used to assert
    # advertised a wider domain than the SDK enforces.
    assert rendered["properties"][REQUIRED_LEAF]["pattern"] == f"^(?:{GRAMMAR})$"
    # Exactly one shape is derived: a grammar contributes no enum and no bounds.
    assert "enum" not in rendered["properties"][REQUIRED_LEAF]
    assert "minimum" not in rendered["properties"][REQUIRED_LEAF]
    assert "maximum" not in rendered["properties"][REQUIRED_LEAF]


def test_the_advertised_grammar_admits_exactly_what_the_SDK_admits() -> None:
    """D-IMPL-357, the close panel of 2026-09-27, finding B-1.

    The contract is the authority for legal values and this module ADVERTISES
    that authority; it may never independently define a wider one
    (``D-IMPL-264`` D-00, P-1). `ArgumentDomain.refuses` judges with
    :func:`re.fullmatch`, and JSON Schema ``pattern`` is a PARTIAL match — so
    an unanchored render admitted any value that merely CONTAINED a match.

    Measured before the fix: a declared ``[A-Z]{3}`` had the SDK answer
    ``not-in-domain`` for ``xxUSDxx`` while the advertised schema admitted it,
    so a generated client, a gateway validator or an examiner reading discovery
    accepted what the governed SDK then refused.

    Judged the way a JSON Schema consumer judges — a PARTIAL search against the
    advertised text — rather than by re-running ``fullmatch``, because
    re-anchoring here would test this test instead of the render.
    """
    import re

    from ccf.products.request_schema import render_request_input_schema

    three_letters = r"[A-Z]{3}"
    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(pattern=three_letters)}
    )
    advertised = render_request_input_schema(contract)["properties"][REQUIRED_LEAF][
        "pattern"
    ]
    domain = ArgumentDomain(pattern=three_letters)

    for value, admitted_by_the_sdk in (("USD", True), ("xxUSDxx", False)):
        assert (domain.refuses(value) is None) is admitted_by_the_sdk, value
        assert (re.search(advertised, value) is not None) is admitted_by_the_sdk, (
            f"the advertised schema disagrees with the SDK on {value!r}"
        )

    # The non-capturing group is load-bearing, not tidiness: a top-level
    # alternation wrapped as `^a|b$` would mean "starts with a, or ends with b"
    # and be wider than the declaration, which is the defect in a new costume.
    alternation = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(pattern=r"AAA|BBB")}
    )
    wrapped = render_request_input_schema(alternation)["properties"][REQUIRED_LEAF][
        "pattern"
    ]
    assert re.search(wrapped, "xAAAx") is None, wrapped
    assert re.search(wrapped, "AAA") is not None, wrapped


def test_a_grammar_domain_leaves_every_other_property_untouched() -> None:
    """The render is derivation, not authorship: only the domained property
    gains a key."""
    from ccf.products.request_schema import render_request_input_schema

    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(pattern=GRAMMAR)}
    )
    rendered = render_request_input_schema(contract)
    base = _contract().arguments.to_input_schema()
    for name, spec in rendered["properties"].items():
        if name == REQUIRED_LEAF:
            continue
        assert spec == base["properties"][name], name


# --- (4) the render reads ArgumentDomain ONLY (P-1) --------------------------


def _planting(key: str, value: Any, *, on: str) -> Any:
    """A `to_input_schema` that carries a second declaration on one property."""
    real = SkillArgumentSchema.to_input_schema

    def planted(self: SkillArgumentSchema) -> dict[str, Any]:
        rendered = real(self)
        rendered["properties"][on][key] = value
        return rendered

    return planted


@pytest.mark.parametrize(
    ("key", "value"),
    [("enum", ["planted"]), ("minimum", 0), ("maximum", 9), ("pattern", "planted")],
)
@pytest.mark.parametrize(
    "on", [REQUIRED_LEAF, OPTIONAL_LEAF], ids=["domained", "not-domained"]
)
def test_the_render_reads_argument_domains_only_and_refuses_a_planted_enum(
    monkeypatch: pytest.MonkeyPatch, key: str, value: Any, on: str
) -> None:
    """A second declaration is refused by name, wherever it is planted.

    P-1: *"schemas ... never independently define it."* On a domained
    property the plant would compete with the declaration of record; on a
    property with no domain it would BE a declaration the contract never
    made. Both are refused, because the base render is not a declaration
    surface for legal values at all. The message names the property and the
    principle.
    """
    monkeypatch.setattr(
        SkillArgumentSchema, "to_input_schema", _planting(key, value, on=on)
    )
    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(members=("alpha", "beta"))}
    )
    # The plant is live: the base render now carries the second declaration.
    assert key in contract.arguments.to_input_schema()["properties"][on]

    with pytest.raises(ValueError) as caught:
        _render(contract)
    message = str(caught.value)
    assert on in message
    assert key in message
    assert "one declaration of record" in message


def test_the_control_plants_nothing_when_not_asked() -> None:
    """The positive half of the control: unpatched, no property carries any of
    the three derived keys, so the refusal above is measuring the plant."""
    base = _contract().arguments.to_input_schema()
    for name, spec in base["properties"].items():
        for key in ("enum", "minimum", "maximum", "pattern"):
            assert key not in spec, (name, key)


# --- (5) the render takes the contract and nothing else ----------------------


def test_the_render_takes_the_contract_and_nothing_else() -> None:
    """D-02's structural form: no parameter could condition what is advertised.

    Dave: *"A caller should be able to know the valid vocabulary before
    making the request ... don't make request validity disclosure-dependent
    here."* A second parameter — whatever its name — would be the place such
    a dependence would be introduced, so the signature is pinned to one.
    """
    from ccf.products.request_schema import render_request_input_schema

    assert list(inspect.signature(render_request_input_schema).parameters) == [
        "contract"
    ]


def test_the_render_does_not_mutate_the_contract() -> None:
    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(members=("alpha",))}
    )
    before = contract.model_dump()
    _render(contract)
    assert contract.model_dump() == before


def test_the_module_publishes_nothing_and_exports_one_name() -> None:
    """Criterion 9's in-tree half: one export, algorithmic, no consumer."""
    import ccf.products.request_schema as module

    assert module.__all__ == ["render_request_input_schema"]
    assert module.__ccf_mode__ == "algorithmic"
