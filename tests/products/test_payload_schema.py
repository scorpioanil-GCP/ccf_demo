"""The declared payload schema and its one shared conformity comparison.

``D-IMPL-97`` ruling 1 made the payload a **declared schema** rather than an
unchecked ``Mapping[str, Any]``; ``D-IMPL-102`` then ruled *where* the two
checks land — **schema validity at registration**, **payload conformity at
bind (request time)** — and ruled explicitly that **no fourth gate** joins
``run_gates``. This module holds the comparison both limbs share, so the two
cannot drift into two readings of "conforms", and it holds the alias that
makes ``D-IMPL-103``'s *extend in place* visible at the product surface rather
than duplicated there.

Requirement CPS-03.
"""

from __future__ import annotations

import ast
import inspect
from decimal import Decimal
from typing import Any

import pytest

from ccf.products import payload as payload_module
from ccf.products.payload import (
    PayloadSchemaViolation,
    ProductPayloadSchema,
    refuse_payload,
)
from ccf.skills.catalog import SkillArgumentSchema


def _schema(document: dict[str, Any]) -> SkillArgumentSchema:
    return SkillArgumentSchema.model_validate(document)


FLAT = {
    "properties": {
        "counterparty": {"type": "string", "description": "URI"},
        "exposure": {"type": "number", "description": "amount"},
        "breached": {"type": "boolean", "description": "covenant breach"},
        "facility_count": {"type": "integer", "description": "count"},
    },
    "required": ["counterparty", "exposure"],
}

NESTED = {
    "properties": {
        "beneficial_owners": {
            "type": "array",
            "description": "UBO list",
            "items": {
                "type": "object",
                "description": "one owner",
                "properties": {
                    "party_uri": {"type": "string", "description": "URI"},
                    "percent": {"type": "number", "description": "share"},
                },
                "required": ["party_uri", "percent"],
            },
        },
        "ownership": {
            "type": "object",
            "description": "by party",
            "properties": {
                "party_uri": {"type": "string", "description": "URI"},
            },
            "required": ["party_uri"],
        },
    },
    "required": ["beneficial_owners"],
}


class TestTheAliasIsTheRuledMachineryAndNotACopy:
    """``D-IMPL-103`` ruled branch (i) — extend in place, do not duplicate."""

    def test_the_product_payload_schema_is_the_skill_argument_schema(self) -> None:
        """One type, two names — never two types.

        Branch (ii), a nesting-capable sibling, was measured at **five**
        duplicated symbols and ruled out. The alias exists so the product
        surface has the name ``D-IMPL-97`` asks for while the machinery stays
        the one already proven; that it is an alias rather than a subclass is
        the whole content of the ruling and is asserted, not described.
        """
        assert ProductPayloadSchema is SkillArgumentSchema


class TestAConformingPayloadIsAccepted:
    def test_a_flat_conforming_payload_returns_none(self) -> None:
        assert (
            refuse_payload(
                payload={
                    "counterparty": "urn:cp:1",
                    "exposure": Decimal("10"),
                    "breached": False,
                    "facility_count": 3,
                },
                declared=_schema(FLAT),
            )
            is None
        )

    def test_an_optional_property_may_be_absent(self) -> None:
        assert (
            refuse_payload(
                payload={"counterparty": "urn:cp:1", "exposure": 10},
                declared=_schema(FLAT),
            )
            is None
        )

    def test_a_nested_conforming_payload_returns_none(self) -> None:
        assert (
            refuse_payload(
                payload={
                    "beneficial_owners": [
                        {"party_uri": "urn:p:1", "percent": Decimal("30")},
                        {"party_uri": "urn:p:2", "percent": Decimal("26")},
                    ],
                    "ownership": {"party_uri": "urn:p:1"},
                },
                declared=_schema(NESTED),
            )
            is None
        )

    def test_an_empty_schema_accepts_only_an_empty_payload(self) -> None:
        empty = _schema({"properties": {}, "required": []})
        assert refuse_payload(payload={}, declared=empty) is None
        assert refuse_payload(payload={"any": 1}, declared=empty) is not None


class TestAViolationCarriesBothSides:
    """The ``AttestationRefusal`` voice: no caller re-derives either side."""

    def test_an_undeclared_key_is_refused(self) -> None:
        violation = refuse_payload(
            payload={"counterparty": "urn:cp:1", "exposure": 1, "smuggled": "x"},
            declared=_schema(FLAT),
        )
        assert isinstance(violation, PayloadSchemaViolation)
        assert violation.reason == "undeclared-key"
        assert violation.key == "smuggled"
        assert "smuggled" in violation.presented_keys
        assert "smuggled" not in violation.declared_keys
        assert violation.declared_keys == frozenset(FLAT["properties"])

    def test_a_missing_required_key_is_refused_and_named(self) -> None:
        violation = refuse_payload(
            payload={"counterparty": "urn:cp:1"}, declared=_schema(FLAT)
        )
        assert isinstance(violation, PayloadSchemaViolation)
        assert violation.reason == "missing-required-key"
        assert violation.key == "exposure"
        assert "exposure" in violation.declared_keys
        assert "exposure" not in violation.presented_keys

    def test_a_wrong_declared_type_is_refused_naming_both_types(self) -> None:
        violation = refuse_payload(
            payload={"counterparty": 7, "exposure": 1}, declared=_schema(FLAT)
        )
        assert isinstance(violation, PayloadSchemaViolation)
        assert violation.reason == "type-mismatch"
        assert violation.key == "counterparty"
        assert violation.declared_type == "string"
        assert violation.presented_type == "int"

    def test_a_boolean_is_not_an_integer(self) -> None:
        """``bool`` subclasses ``int`` in Python and does not in JSON Schema."""
        violation = refuse_payload(
            payload={
                "counterparty": "urn:cp:1",
                "exposure": 1,
                "facility_count": True,
            },
            declared=_schema(FLAT),
        )
        assert violation is not None
        assert violation.reason == "type-mismatch"
        assert violation.key == "facility_count"

    def test_a_float_is_refused_where_a_number_is_declared(self) -> None:
        """A payload the fabric could not canonically serialize is not valid.

        ``ccf.contracts.canonical`` refuses ``float`` outright — binary
        floating point is not bit-stable across platforms — so admitting one
        here would declare conformant a payload that cannot reach a content
        address. ``int`` and ``Decimal`` are the numeric forms this tree has.
        """
        violation = refuse_payload(
            payload={"counterparty": "urn:cp:1", "exposure": 1.5},
            declared=_schema(FLAT),
        )
        assert violation is not None
        assert violation.reason == "type-mismatch"
        assert violation.key == "exposure"
        assert violation.declared_type == "number"

    def test_the_detail_names_the_key_and_both_sides(self) -> None:
        violation = refuse_payload(
            payload={"counterparty": 7, "exposure": 1}, declared=_schema(FLAT)
        )
        assert violation is not None
        assert "counterparty" in violation.detail
        assert "string" in violation.detail
        assert "int" in violation.detail


class TestNestedViolationsAreReachedAndPathNamed:
    def test_an_undeclared_key_inside_a_nested_object_is_refused(self) -> None:
        violation = refuse_payload(
            payload={
                "beneficial_owners": [],
                "ownership": {"party_uri": "urn:p:1", "smuggled": 1},
            },
            declared=_schema(NESTED),
        )
        assert violation is not None
        assert violation.reason == "undeclared-key"
        assert violation.key == "ownership.smuggled"

    def test_a_wrong_type_inside_a_list_item_is_refused(self) -> None:
        violation = refuse_payload(
            payload={"beneficial_owners": [{"party_uri": 1, "percent": 30}]},
            declared=_schema(NESTED),
        )
        assert violation is not None
        assert violation.reason == "type-mismatch"
        assert violation.key == "beneficial_owners[].party_uri"
        assert violation.declared_type == "string"

    def test_a_missing_required_key_inside_a_list_item_is_refused(self) -> None:
        violation = refuse_payload(
            payload={"beneficial_owners": [{"party_uri": "urn:p:1"}]},
            declared=_schema(NESTED),
        )
        assert violation is not None
        assert violation.reason == "missing-required-key"
        assert violation.key == "beneficial_owners[].percent"

    def test_a_non_list_where_an_array_is_declared_is_refused(self) -> None:
        violation = refuse_payload(
            payload={"beneficial_owners": "not a list"},
            declared=_schema(NESTED),
        )
        assert violation is not None
        assert violation.reason == "type-mismatch"
        assert violation.key == "beneficial_owners"
        assert violation.declared_type == "array"


class TestTheComparisonIsDeterministicAndPure:
    def test_the_first_violation_is_deterministic_across_key_orders(self) -> None:
        """Two payloads differing only in insertion order refuse identically."""
        declared = _schema(FLAT)
        first = refuse_payload(
            payload={"b_extra": 1, "a_extra": 1, "counterparty": "x", "exposure": 1},
            declared=declared,
        )
        second = refuse_payload(
            payload={"a_extra": 1, "b_extra": 1, "counterparty": "x", "exposure": 1},
            declared=declared,
        )
        assert first is not None and second is not None
        assert first.key == second.key == "a_extra"

    def test_the_module_performs_no_io_and_reads_no_clock(self) -> None:
        """The purity ``refuse_attestation``'s docstring claims, asserted.

        An AST walk rather than a docstring: the claim is that the comparison
        is a pure function of its two arguments, and a comparison that reached
        a clock or a registry would make the same payload conform at one
        moment and not at another.
        """
        forbidden_calls = {"open", "input", "print"}
        forbidden_attrs = {"now", "utcnow", "today", "resolve", "read_text"}
        tree = ast.parse(inspect.getsource(payload_module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    assert func.id not in forbidden_calls, func.id
                if isinstance(func, ast.Attribute):
                    assert func.attr not in forbidden_attrs, func.attr
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [
                    node.module or "",
                    *[alias.name for alias in node.names],
                ]
                for name in names:
                    root = name.split(".")[0]
                    assert root not in {
                        "io",
                        "os",
                        "socket",
                        "pathlib",
                        "requests",
                        "httpx",
                        "sqlite3",
                        "random",
                        "time",
                    }, name

    def test_the_module_is_declared_algorithmic(self) -> None:
        assert payload_module.__ccf_mode__ == "algorithmic"


class TestTheModuleHoldsNoDomainValues:
    """CLAUDE.md §11 — mechanism, not values."""

    @pytest.mark.parametrize(
        "forbidden",
        ["counterparty", "exposure", "beneficial_owner", "credit", "kyc"],
    )
    def test_no_domain_property_name_appears_in_the_module(
        self, forbidden: str
    ) -> None:
        assert forbidden not in inspect.getsource(payload_module).lower()
