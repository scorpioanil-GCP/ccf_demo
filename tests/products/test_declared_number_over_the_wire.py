"""`D-IMPL-302` — a declared ``number`` crosses the wire as canonical decimal text.

Both SDK surfaces were individually right and their composition made a
legitimate request impossible: the product contract refused a ``str`` with
``type-mismatch``, and :class:`~ccf.products.door.WireRequest` refused a
``float`` because *"canonical JSON renders it as text, so the decoded echo
would differ from what was sent"*. A fractional ``number`` had no
representation, and cp-05 was the first product whose numeric arguments were
consequential enough to need one.

The fix keeps the two representations apart rather than erasing either: the
wire keeps ``"0.05"`` and its echo check, and the governed request carries
exact ``Decimal("0.05")``.
"""

from __future__ import annotations

import json
from decimal import Decimal
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    decode_declared_request,
    refuse_request,
)
from ccf.products.constraints import resolve_effective_request
from ccf.products.provenance import ProvenanceSource
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

ASKED_AT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

#: The fixture's own vocabulary. The SDK ships no parameter names.
MATERIALITY = "materiality"
LEXICAL = "0.05"


def _declared() -> ProductRequestContract:
    """A class declaring one `number` argument — cp-05's shape, not its content."""
    return ProductRequestContract(
        semver="1.0.0",
        schema_name="fixture.numeric",
        schema_version="1.0.0",
        arguments=SkillArgumentSchema(
            properties={
                MATERIALITY: SkillArgumentProperty(
                    type="number", description="a share of group exposure"
                )
            },
            required=(),
        ),
    )


def _asked(value: Any) -> ProductRequest:
    return ProductRequest(
        schema_name="fixture.numeric",
        schema_version="1.0.0",
        subject="fixture-subject",
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=ASKED_AT,
        parameters={MATERIALITY: value},
    )


def test_the_lexical_form_survives_the_wire_unchanged() -> None:
    """(1) The wire keeps `"0.05"` exactly, and the echo check still runs on it."""
    wire = WireRequest(
        product_id="fixture.numeric",
        parameters={MATERIALITY: LEXICAL},
        temporal_boundary=ASKED_AT,
    )
    encoded = canonical_bytes(wire).decode("utf-8")

    assert json.loads(encoded)["parameters"][MATERIALITY] == LEXICAL
    assert WireRequest.model_validate_json(encoded) == wire


def test_the_decode_yields_an_exact_decimal() -> None:
    """(2) and (6) — exact, and provably not via a binary float.

    `Decimal("0.05")` and `Decimal(0.05)` are different numbers: the second is
    the nearest double and is not 5/100. Asserting equality with the first
    would pass for either if the comparison were loose, so the float form is
    named and excluded explicitly.
    """
    decoded = decode_declared_request(_asked(LEXICAL), _declared())
    value = decoded.parameters[MATERIALITY]

    assert isinstance(value, Decimal)
    assert value == Decimal(LEXICAL)
    assert value != Decimal(0.05), (
        "the decimal was built through a binary float; 0.05 is not"
        " representable in IEEE-754 and the exact value is what governs"
    )
    assert not isinstance(value, float)


def test_the_incoming_request_is_not_mutated() -> None:
    """A NEW request is returned, so the lexical form stays available."""
    asked = _asked(LEXICAL)

    decoded = decode_declared_request(asked, _declared())

    assert asked.parameters[MATERIALITY] == LEXICAL, "the caller's object moved"
    assert decoded is not asked


def test_the_contract_accepts_the_decoded_value_and_refused_the_text() -> None:
    """(3) — and the control, which is the finding itself.

    Undecoded, the very same request is refused `type-mismatch`. That refusal
    is what made a declared `number` unaskable over MCP, so it is asserted
    here rather than described: it says the decode is load-bearing and not
    decoration.
    """
    declared = _declared()

    assert refuse_request(request=_asked(LEXICAL), declared=declared) is not None
    assert (
        refuse_request(
            request=decode_declared_request(_asked(LEXICAL), declared),
            declared=declared,
        )
        is None
    )


@pytest.mark.parametrize(
    "malformed",
    ["NaN", "Infinity", "-Infinity", "1e-2", "0.05 ", " 0.05", "+0.05", "0,05", ""],
)
def test_a_non_canonical_lexical_form_is_not_decoded(malformed: str) -> None:
    """(5) — and the decoder mints no refusal of its own.

    `Decimal` would happily parse `NaN`, `Infinity` and `1e-2`; none is what a
    product contract means by *number*, and letting Python's parser define the
    wire contract by accident is the failure the narrow pattern prevents. The
    value passes through UNCHANGED so `refuse_request` refuses it by name —
    the contract comparison is the one place that verdict belongs.
    """
    declared = _declared()

    decoded = decode_declared_request(_asked(malformed), declared)

    assert decoded.parameters[MATERIALITY] == malformed
    assert refuse_request(request=decoded, declared=declared) is not None


def test_nothing_but_a_declared_number_is_decoded() -> None:
    """The ruled boundary: no `"true"`, no `"123"`, no dates, no promotion."""
    declared = ProductRequestContract(
        semver="1.0.0",
        schema_name="fixture.numeric",
        schema_version="1.0.0",
        arguments=SkillArgumentSchema(
            properties={
                "flag": SkillArgumentProperty(type="boolean", description="f"),
                "count": SkillArgumentProperty(type="integer", description="c"),
                "label": SkillArgumentProperty(type="string", description="l"),
            },
            required=(),
        ),
    )
    asked = ProductRequest(
        schema_name="fixture.numeric",
        schema_version="1.0.0",
        subject="s",
        intent="i",
        freshness="f",
        asked_at=ASKED_AT,
        parameters={"flag": "true", "count": "123", "label": "0.05"},
    )

    decoded = decode_declared_request(asked, declared)

    assert decoded.parameters == {"flag": "true", "count": "123", "label": "0.05"}


def test_an_undeclared_or_already_numeric_parameter_passes_through() -> None:
    """Numbers already numeric are untouched; unknown names are the contract's."""
    declared = _declared()

    already = decode_declared_request(_asked(Decimal("0.05")), declared)
    assert already.parameters[MATERIALITY] == Decimal("0.05")

    integral = decode_declared_request(_asked(3), declared)
    assert integral.parameters[MATERIALITY] == 3


def test_the_governed_resolution_computes_over_the_decoded_number() -> None:
    """(4) — the WIRING, which none of the tests above can see.

    Every assertion so far calls :func:`decode_declared_request` directly, so
    all of them pass whether or not governed resolution ever calls it.
    **Measured: removing the call from `resolve_effective_request` left the
    entire `tests/products` tree green.** This is the test that fails when the
    wiring goes.

    It asserts on the EFFECTIVE parameter — what the contract was held
    against, what any bound is compared with, and what replay dimension 2
    records with its authority — so a decode that happened somewhere the
    governed path could not see it would not satisfy this.
    """
    outcome = resolve_effective_request(
        request=_asked(LEXICAL),
        declared=_declared(),
        declared_source=ProvenanceSource(
            kind="artifact", identity="tenant-fixture/request-contract", version="1.0.0"
        ),
        constraints=(),
        capabilities=(),
        capability_bindings={},
        verified_overrides=(),
        perspective=Perspective(principal_id="fixture-principal", role="fixture-role"),
        tenant="fixture-tenant",
        served_at=_asked(LEXICAL).asked_at,
    )

    assert outcome.refusal is None, (
        f"the governed path refused a legitimate declared number: {outcome.refusal}"
    )
    effective = {p.name: p for p in outcome.evidence.parameters}
    value = effective[MATERIALITY].value

    assert isinstance(value, Decimal), (
        "the effective parameter is not numeric, so resolution computed over"
        " the lexical form and replay would record text where a number governs"
    )
    assert value == Decimal(LEXICAL)
    assert value != Decimal(0.05), "an IEEE float reached the governed value"
    assert effective[MATERIALITY].authority == "caller", (
        "the caller supplied this value, so the authority must say so — the"
        " decode must not have moved where the value came from"
    )
