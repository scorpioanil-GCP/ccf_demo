"""Blocker 1 — `preferred` guidance holding a Decimal and holding a name must not share an address.

Ruled 2026-10-11 12:35 MST (Grok's review of GROK-BRIEF-7, adopted by Dave): option A, a
hash-transparent ``preferred_decimal`` kind flag on ``PolicyConstraint``. Red first, on the property:

* ``PolicyConstraint(preferred, Decimal("4"))`` and ``PolicyConstraint(preferred, "4")`` are unequal
  and must have different content hashes (today: identical);
* a Decimal under ``preferred`` round-trips through the registry as a Decimal (today: refused,
  because the reconstruction reads the quoted number back as text);
* the canonical bytes of every EXISTING accepted form — a ``preferred`` name, ``preferred`` numeric
  text, ``maximum``, ``allowed_set``, ``required`` — are byte-identical to what they were at
  ``63bea494`` (pins, green before and after: existing forms keep their addresses);
* the flag, the operator and the value agree (Dave: *"Test consistency between the flag, operator,
  and value."*).

What the address claim is, precisely (Dave: *"Do not imply that old ambiguous bytes can reveal their
original type."*): every form that was accepted before keeps its address; numeric ``preferred``
guidance gains a distinct one. Bytes written before the flag existed carry no flag, and they mean the
name form — there was never an accepted Decimal form to confuse them with, because the registry has
refused it since the sixth round.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import POLICY_CONSTRAINT, ConstraintApplicability, PolicyConstraint
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.composition import register_typed_at_composition


def _pc(operator: str, value: object, **extra: object) -> PolicyConstraint:
    return PolicyConstraint(
        semver="1.0.0", policy_id="kind-fixture", applies_to=ConstraintApplicability(), parameter="depth",
        operator=operator, value=value, source_authority="fixture-authority",
        effective_from=datetime(2026, 1, 1, tzinfo=UTC), reason="fixture reason", **extra,
    )


#: Content addresses of the existing accepted forms, measured at 63bea494 before the flag existed.
BASELINE = {
    "preferred-name": ("preferred", "tier-a", "21ca6a2e779d4fcd7f2477991638db0ec68989dd48639ef47114e68ec1a497d6"),
    "preferred-numeric-text": ("preferred", "4", "5082475c47c5157accedab55fa051e675a371d1ef2e276ac9885ae56c0530608"),
    "maximum": ("maximum", Decimal("4"), "8365a6cd17e80de78f73e08297112eb1b83ac43638a3e7bd772d9fd25c7711aa"),
    "allowed_set": ("allowed_set", ("tier-a",), "3ed2e688a03bc0ba2e375fc174a222f499ca4b125044befd3511a272d66a6f4f"),
    "required": ("required", None, "730e83d6934ef80306c56a1160d3d5f8ded3e2fa1ae53723422859916d759b46"),
}


@pytest.mark.parametrize("form", sorted(BASELINE))
def test_every_existing_accepted_form_keeps_its_address(form: str) -> None:
    operator, value, address = BASELINE[form]
    constraint = _pc(operator, value)
    assert content_hash(constraint) == address
    assert b"preferred_decimal" not in canonical_bytes(constraint)


def test_numeric_and_name_preferred_guidance_have_different_addresses() -> None:
    numeric, name = _pc("preferred", Decimal("4")), _pc("preferred", "4")
    assert numeric != name
    assert content_hash(numeric) != content_hash(name)
    assert content_hash(name) == BASELINE["preferred-numeric-text"][2]


@pytest.mark.parametrize("value", [Decimal("4"), Decimal("0.10"), Decimal("2000")])
def test_a_decimal_under_preferred_round_trips_through_the_registry_as_a_decimal(value: Decimal) -> None:
    registry = ControlPlaneRegistry()
    version = register_typed_at_composition(registry, "acme/policy/guidance", _pc("preferred", value), POLICY_CONSTRAINT)
    for served in (registry.resolve("acme/policy/guidance", version), registry.peek("acme/policy/guidance", version)):
        assert isinstance(served, PolicyConstraint)
        assert type(served.value) is Decimal and served.value == value
    assert version == content_hash(_pc("preferred", value))


def test_a_name_under_preferred_round_trips_as_a_name() -> None:
    registry = ControlPlaneRegistry()
    version = register_typed_at_composition(registry, "acme/policy/guidance", _pc("preferred", "4"), POLICY_CONSTRAINT)
    served = registry.resolve("acme/policy/guidance", version)
    assert type(served.value) is str and served.value == "4"


def test_the_flag_operator_and_value_agree() -> None:
    """Consistency: the flag is exactly 'preferred with a Decimal'. Every other combination is refused."""
    assert _pc("preferred", Decimal("4")).preferred_decimal is True
    assert _pc("preferred", "4").preferred_decimal is False
    assert _pc("maximum", Decimal("4")).preferred_decimal is False
    for operator, value, flag in (
        ("preferred", Decimal("4"), False),   # a Decimal declared as the name form
        ("preferred", "tier-a", True),        # the flag over a value that is not a number
        ("maximum", Decimal("4"), True),      # the flag on another operator
        ("allowed_set", ("tier-a",), True),
        ("required", None, True),
    ):
        with pytest.raises(ValidationError):
            _pc(operator, value, preferred_decimal=flag)


def test_a_document_reads_a_quoted_number_as_a_decimal_only_when_it_carries_the_flag() -> None:
    document = _pc("preferred", "4").model_dump(mode="json")
    assert type(PolicyConstraint.model_validate(document).value) is str
    flagged = {**document, "preferred_decimal": True}
    parsed = PolicyConstraint.model_validate(flagged)
    assert type(parsed.value) is Decimal and parsed.value == Decimal("4")
    assert parsed == _pc("preferred", Decimal("4"))
