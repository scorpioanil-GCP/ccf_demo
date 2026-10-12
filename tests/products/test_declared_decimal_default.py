# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A request contract can declare a DECIMAL default for a ``number`` argument (CP05-R2-F-01).

**The finding** (``NEEDS-SDK.md``, r2-frozen fork, cp-05/door-cp-05; carried to
cp-14's exposure child). A Control Plane document quotes its numbers — the
registry refuses a bare float as *"not bit-stable across platforms"* — so a
declared ``materiality: "0.05"`` default arrives as TEXT. The request contract
then judged that text against the declared ``number`` type and refused it
(``declares defaults it cannot honor``), so the declaration had no way to say
"omission means 0.05". With SEC-019 (``D-IMPL-356`` D11) a policy ``maximum`` on
the parameter then refused every question that omitted it ``required-absent``.

**Ruled** (Dave, 2026-10-11 20:19 MST, item 1): *"decimal defaults ... Preserve
exact decimal meaning."* The repair is the existing caller-side rule,
:func:`ccf.products.request.decode_declared_request` (``D-IMPL-302``), applied to
the declared default by the SAME function: declared ``number`` + canonical
decimal text -> exact :class:`~decimal.Decimal`, built from the text and never
through a binary float. Nothing else is decoded.

**Why no kind flag** (contrast ``PolicyConstraint.preferred_decimal``). That flag
exists because under ``preferred`` a quoted value may be a decimal OR a name,
and both render to the same canonical bytes. Here the kind is already in the
same document's bytes: the argument's declared ``type``. A ``number`` argument's
text default is decoded; a ``string`` argument's identical text stays a string.
And the decoded decimal renders back to exactly the text it was read from
(``CANONICAL_DECIMAL`` admits no exponent), so the contract's canonical bytes —
and so its content address — are the bytes of what the author wrote.

Every name and number below is this module's own fixture vocabulary (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import DeclaredArtifact
from ccf.products import constraints as constraints_module
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    decode_declared_request,
)
from ccf.products.provenance import ProvenanceSource
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

from tests.products.test_policy_constraints import _pinned

CLASS_NAME = "fixture.decimal-default"
CLASS_VERSION = "1.0.0"
CONTRACT_KEY = "fixture.request-contract"
INSTANT = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

SHARE = "share"  # declared `number` — the cp-05 `materiality` shape
COUNT = "count"  # declared `integer`
LABEL = "label"  # declared `string`

DECLARED_TEXT = "0.05"
EXACT = Decimal(DECLARED_TEXT)


def _arguments() -> dict[str, Any]:
    return SkillArgumentSchema(
        properties={
            SHARE: SkillArgumentProperty(type="number", description="a fixture share"),
            COUNT: SkillArgumentProperty(type="integer", description="a fixture count"),
            LABEL: SkillArgumentProperty(type="string", description="a fixture label"),
        },
        required=(),
    ).model_dump(mode="json")


def _declared(defaults: dict[str, Any]) -> DeclaredArtifact:
    """The document path: what a manifest hands ``from_declared``."""
    return DeclaredArtifact(
        semver="1.0.0",
        class_id=CONTRACT_KEY,
        declaration={
            "schema_name": CLASS_NAME,
            "schema_version": CLASS_VERSION,
            "arguments": _arguments(),
            "defaults": defaults,
        },
    )


def _read(defaults: dict[str, Any]) -> ProductRequestContract | str:
    """The contract, or the refusal text — so a refusal fails an ASSERTION, by name."""
    try:
        return ProductRequestContract.from_declared(_declared(defaults))
    except ValueError as refused:
        return str(refused)


# --- the permitted case -------------------------------------------------------


def test_a_quoted_decimal_default_for_a_number_argument_is_the_exact_decimal() -> None:
    contract = _read({SHARE: DECLARED_TEXT})

    assert isinstance(contract, ProductRequestContract), contract
    value = contract.defaults[SHARE]
    assert type(value) is Decimal
    assert value == EXACT
    # Exact, not the nearest double: a float route would carry 0.05000000000000000277...
    assert value.as_tuple() == EXACT.as_tuple()
    assert str(value) == DECLARED_TEXT


def test_the_default_and_a_caller_stating_the_same_text_are_one_value() -> None:
    """One rule for both: the default is decoded by the function that decodes callers."""
    contract = _read({SHARE: DECLARED_TEXT})
    assert isinstance(contract, ProductRequestContract), contract
    caller = decode_declared_request(
        ProductRequest(
            schema_name=CLASS_NAME,
            schema_version=CLASS_VERSION,
            subject="fixture:subject/one",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=INSTANT,
            parameters={SHARE: DECLARED_TEXT},
        ),
        contract,
    )
    assert caller.parameters[SHARE] == contract.defaults[SHARE]
    assert caller.parameters[SHARE].as_tuple() == contract.defaults[SHARE].as_tuple()


def test_the_canonical_bytes_carry_the_text_the_author_wrote() -> None:
    """Content address stable: the decimal renders back to exactly its declared text,
    a JSON round trip re-reads the same value, and trailing zeros are NOT normalized
    away (``"0.050"`` is its own declaration and its own address)."""
    contract = _read({SHARE: DECLARED_TEXT})
    assert isinstance(contract, ProductRequestContract), contract

    assert b'"0.05"' in canonical_bytes(contract)
    again = ProductRequestContract.model_validate_json(contract.model_dump_json())
    assert again == contract
    assert type(again.defaults[SHARE]) is Decimal
    assert canonical_bytes(again) == canonical_bytes(contract)

    wider = _read({SHARE: "0.050"})
    assert isinstance(wider, ProductRequestContract), wider
    assert str(wider.defaults[SHARE]) == "0.050"
    assert content_hash(wider) != content_hash(contract)


def test_a_string_argument_keeps_the_same_text_as_text() -> None:
    """The kind comes from the declared type: identical text under ``string`` is a name."""
    contract = _read({LABEL: DECLARED_TEXT})
    assert isinstance(contract, ProductRequestContract), contract
    assert contract.defaults[LABEL] == DECLARED_TEXT
    assert type(contract.defaults[LABEL]) is str


def test_the_decimal_default_reaches_the_effective_request_and_satisfies_a_policy_bound() -> None:
    """The cp-05 shape: omission + a policy ``maximum`` of the same figure is SERVED
    at the exact default, authority ``default`` — not refused ``required-absent``."""
    contract = _read({SHARE: DECLARED_TEXT})
    assert isinstance(contract, ProductRequestContract), contract
    outcome = constraints_module.resolve_effective_request(
        request=ProductRequest(
            schema_name=CLASS_NAME,
            schema_version=CLASS_VERSION,
            subject="fixture:subject/one",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=INSTANT,
            parameters={},
        ),
        declared=contract,
        declared_source=ProvenanceSource(
            kind="artifact", identity=CONTRACT_KEY, version="1.0.0"
        ),
        constraints=(
            _pinned(parameter=SHARE, operator="maximum", value=Decimal(DECLARED_TEXT)),
        ),
        capabilities=(),
        capability_bindings={},
        verified_overrides=(),
        perspective=Perspective(principal_id="fixture-principal", role="fixture-role"),
        tenant="fixture-tenant",
        served_at=INSTANT,
    )
    assert outcome.refusal is None, outcome.refusal
    share = outcome.evidence.parameter(SHARE)
    assert share.authority == "default"
    assert type(share.value) is Decimal
    assert share.value.as_tuple() == EXACT.as_tuple()


# --- the refused cases: nothing else is decoded -------------------------------


@pytest.mark.parametrize(
    ("name", "text"),
    [
        pytest.param(SHARE, "5e-2", id="exponent-form"),
        pytest.param(SHARE, " 0.05", id="padded"),
        pytest.param(SHARE, "NaN", id="not-a-number"),
        pytest.param(SHARE, "Infinity", id="infinite"),
        pytest.param(SHARE, "+0.05", id="leading-plus"),
        pytest.param(COUNT, "5", id="integer-argument-text"),
    ],
)
def test_text_that_is_not_a_canonical_decimal_for_a_number_is_still_refused(
    name: str, text: str
) -> None:
    refused = _read({name: text})
    assert isinstance(refused, str), f"{text!r} under {name!r} was admitted"
    assert "declares defaults it cannot honor" in refused
    assert name in refused


def test_a_python_float_default_is_still_refused() -> None:
    """No float anywhere: a binary float is not the decimal the author meant."""
    with pytest.raises(ValueError) as raised:
        ProductRequestContract(
            semver="1.0.0",
            schema_name=CLASS_NAME,
            schema_version=CLASS_VERSION,
            arguments=SkillArgumentSchema.model_validate(_arguments()),
            defaults={SHARE: 0.05},
        )
    assert "declares defaults it cannot honor" in str(raised.value)
