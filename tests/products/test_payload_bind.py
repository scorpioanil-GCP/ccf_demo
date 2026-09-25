"""Bind-time payload conformity — D-IMPL-102 limb 2, and the gate it is not.

``D-IMPL-102`` resolved payload validation in three parts and this module holds
the second and the third together, because the third is what keeps the second
honest:

2. **Payload conformity is checked at bind — request time.** A payload meets
   its class's *declared* schema on the bound path, where the class a request
   bound to is in hand and its pinned schema is therefore resolvable.
3. **No fourth gate.** ``ccf.products.gates.run_gates`` is untouched. The
   shipped validation gates stay **structural** — every one of their verdicts
   depends only on the product's own shape, never on a schema a user declared
   — and a payload check would have been the first whose verdict a deployment
   could configure.

Limb 1, schema validity at registration, landed in plan ``15.5-07`` and is
tested by ``tests/products/test_class_governance.py``; the comparison both
limbs share is tested by ``tests/products/test_payload_schema.py``. What is
tested *here* is the layer between them: resolving the pin at bind, the
positive meaning of a class that declared no schema, the difference between a
bad product and a broken deployment, and the structural absence of a gate.

Requirements CPS-03, CPS-13.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
from ccf.products.bind import (
    refuse_bound_payload,
    resolve_declared_payload_schema,
)
from ccf.products.contract import (
    NO_PAYLOAD_SCHEMA,
    MaxTTL,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import GateRefusal, run_gates
from ccf.products.payload import (
    PayloadSchemaViolation,
    ProductPayloadSchema,
    refuse_payload,
)
from tests.composition import register_at_composition

MAX_TTL_KEY = "tenant-fixture/max-ttl"
PAYLOAD_SCHEMA_KEY = "tenant-fixture/payload-schema"


def _schema() -> ProductPayloadSchema:
    """A declaration exercising every level D-IMPL-103 admits."""
    return ProductPayloadSchema.model_validate(
        {
            "properties": {
                "alpha": {"type": "string", "description": "a declared string"},
                "beta": {"type": "integer", "description": "a declared integer"},
                "gamma": {
                    "type": "object",
                    "description": "a declared object",
                    "properties": {
                        "delta": {"type": "string", "description": "nested"}
                    },
                    "required": ["delta"],
                },
            },
            "required": ["alpha"],
        }
    )


def _registered(
    *, declare_schema: bool = True
) -> tuple[RegisteredProductClass, ControlPlaneRegistry]:
    registry = ControlPlaneRegistry()
    ttl_version = register_at_composition(registry, MAX_TTL_KEY, MaxTTL(seconds=3600))
    arguments: dict[str, object] = {
        "registry": registry,
        "schema_name": "fixture.bind",
        "schema_version": "1.0.0",
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": MAX_TTL_KEY,
        "max_ttl_version": ttl_version,
    }
    if declare_schema:
        schema_version = register_at_composition(registry, PAYLOAD_SCHEMA_KEY, _schema())
        arguments["payload_schema_key"] = PAYLOAD_SCHEMA_KEY
        arguments["payload_schema_version"] = schema_version
    registered = register_product_class(**arguments)  # type: ignore[arg-type]
    return registered, registry


class TestTheDeclaredSchemaIsResolvedFromThePin:
    """The pin ``15.5-07`` put on the class is what bind resolves against."""

    def test_a_declared_schema_resolves_to_the_pinned_artifact(self) -> None:
        registered, registry = _registered()
        resolved = resolve_declared_payload_schema(
            product_class=registered, registry=registry
        )
        assert resolved == _schema()

    def test_a_class_declaring_no_schema_resolves_to_none(self) -> None:
        """``None`` here asserts *this class declared nothing*, not *nothing
        was looked up* — the ``NO_PAYLOAD_SCHEMA`` sentinel's own posture."""
        registered, registry = _registered(declare_schema=False)
        assert registered.payload_schema_key == NO_PAYLOAD_SCHEMA
        assert (
            resolve_declared_payload_schema(
                product_class=registered, registry=registry
            )
            is None
        )


class TestAConformingPayloadBindsClean:
    def test_a_conforming_payload_returns_none(self) -> None:
        registered, registry = _registered()
        assert (
            refuse_bound_payload(
                payload={"alpha": "a", "beta": 1, "gamma": {"delta": "d"}},
                product_class=registered,
                registry=registry,
            )
            is None
        )

    def test_an_optional_declared_key_may_be_absent(self) -> None:
        registered, registry = _registered()
        assert (
            refuse_bound_payload(
                payload={"alpha": "a"},
                product_class=registered,
                registry=registry,
            )
            is None
        )

    def test_a_class_with_no_declared_schema_admits_any_payload(self) -> None:
        """The compatibility posture, stated rather than inherited: a class
        that has not declared what its payload must look like holds it to
        nothing, which is the honest ``Mapping[str, Any]`` D-IMPL-97 named as
        the gap — visible in the registration, not papered over here."""
        registered, registry = _registered(declare_schema=False)
        assert (
            refuse_bound_payload(
                payload={"anything": object()},
                product_class=registered,
                registry=registry,
            )
            is None
        )


class TestANonConformingPayloadIsRefusedAtBind:
    def test_an_undeclared_key_is_refused_naming_the_declared_set(self) -> None:
        registered, registry = _registered()
        violation = refuse_bound_payload(
            payload={"alpha": "a", "epsilon": "x"},
            product_class=registered,
            registry=registry,
        )
        assert violation is not None
        assert violation.reason == "undeclared-key"
        assert violation.key == "epsilon"
        assert violation.declared_keys == frozenset({"alpha", "beta", "gamma"})

    def test_a_missing_required_key_is_refused_and_named(self) -> None:
        registered, registry = _registered()
        violation = refuse_bound_payload(
            payload={"beta": 1}, product_class=registered, registry=registry
        )
        assert violation is not None
        assert violation.reason == "missing-required-key"
        assert violation.key == "alpha"

    def test_a_type_mismatch_names_both_types(self) -> None:
        registered, registry = _registered()
        violation = refuse_bound_payload(
            payload={"alpha": "a", "beta": "not-an-integer"},
            product_class=registered,
            registry=registry,
        )
        assert violation is not None
        assert violation.reason == "type-mismatch"
        assert violation.key == "beta"
        assert violation.declared_type == "integer"
        assert violation.presented_type == "str"

    def test_a_nested_violation_is_reached_through_the_bind(self) -> None:
        """The bind does not flatten the comparison it delegates to: one level
        down is reached and the path says where."""
        registered, registry = _registered()
        violation = refuse_bound_payload(
            payload={"alpha": "a", "gamma": {"delta": 1}},
            product_class=registered,
            registry=registry,
        )
        assert violation is not None
        assert violation.key == "gamma.delta"
        assert violation.reason == "type-mismatch"


class TestABadProductIsReturnedAndABrokenDeploymentIsRaised:
    """``gates.py``'s posture, applied here: *a broken deployment is not a bad
    product, and the two must not be reported the same way*."""

    def test_a_violation_is_returned_not_raised(self) -> None:
        registered, registry = _registered()
        violation = refuse_bound_payload(
            payload={}, product_class=registered, registry=registry
        )
        assert isinstance(violation, PayloadSchemaViolation)

    def test_a_vanished_pin_raises_control_plane_missing(self) -> None:
        registered, _ = _registered()
        empty = ControlPlaneRegistry()
        register_at_composition(empty, MAX_TTL_KEY, MaxTTL(seconds=3600))
        with pytest.raises(ControlPlaneMissing):
            refuse_bound_payload(
                payload={"alpha": "a"},
                product_class=registered,
                registry=empty,
            )

    def test_a_pin_holding_the_wrong_artifact_raises_type_error(self) -> None:
        registered, _ = _registered()
        other = ControlPlaneRegistry()
        register_at_composition(other, MAX_TTL_KEY, MaxTTL(seconds=3600))
        register_at_composition(other, PAYLOAD_SCHEMA_KEY, MaxTTL(seconds=60))
        substituted = registered.model_copy(
            update={
                "payload_schema_version": other.resolve_latest(
                    PAYLOAD_SCHEMA_KEY
                )[0]
            }
        )
        with pytest.raises(TypeError):
            refuse_bound_payload(
                payload={"alpha": "a"},
                product_class=substituted,
                registry=other,
            )


class TestBindReachesTheOneComparison:
    """Registration-time binding and bind-time checking must not drift into
    two readings of "conforms" — the reason ``refuse_payload`` is one pure
    function, and the reason ``refuse_attestation`` is one before it."""

    @pytest.mark.parametrize(
        "payload",
        [
            {"alpha": "a"},
            {"alpha": "a", "beta": 1},
            {"beta": 1},
            {"alpha": 1},
            {"alpha": "a", "zeta": True},
            {"alpha": "a", "gamma": {"delta": 1}},
        ],
    )
    def test_bind_returns_exactly_what_the_shared_comparison_returns(
        self, payload: dict[str, object]
    ) -> None:
        registered, registry = _registered()
        assert refuse_bound_payload(
            payload=payload, product_class=registered, registry=registry
        ) == refuse_payload(payload=payload, declared=_schema())

    def test_the_bind_module_calls_the_shared_comparison_by_name(self) -> None:
        source = Path("src/ccf/products/bind.py").read_text(encoding="utf-8")
        assert "refuse_payload(" in source


class TestNoFourthGate:
    """D-IMPL-102 limb 3, asserted structurally rather than by convention."""

    def test_run_gates_takes_no_payload_or_schema_parameter(self) -> None:
        parameters = inspect.signature(run_gates).parameters
        assert not [
            name
            for name in parameters
            if "payload" in name or "schema" in name
        ]

    def test_the_gates_module_does_not_name_the_payload_comparison(
        self,
    ) -> None:
        """The canonical sequence is *structural*: every verdict it reaches
        depends on the product's own shape alone. A user-declared schema
        reaching it would make one gate configurable."""
        source = Path("src/ccf/products/gates.py").read_text(encoding="utf-8")
        assert "refuse_payload" not in source
        assert "PayloadSchemaViolation" not in source
        assert "ccf.products.payload" not in source

    def test_a_payload_violation_cannot_travel_as_a_gate_verdict(self) -> None:
        assert not issubclass(PayloadSchemaViolation, GateRefusal)

    def test_the_gates_module_does_not_import_the_bind_module(self) -> None:
        source = Path("src/ccf/products/gates.py").read_text(encoding="utf-8")
        assert "products.bind" not in source


class TestTheBindHoldsNoPrincipalAndNoDomainValue:
    """Entitlement is the door's (plan ``15.5-06``); this module holds none of
    it, and holds no domain value either (CLAUDE.md §11, CINV-01)."""

    def test_no_principal_reaches_the_bind(self) -> None:
        """Asserted over *identifiers*, not prose: the module says in words
        that entitlement is the door's, and the check that matters is that no
        argument, attribute or name here carries one."""
        source = Path("src/ccf/products/bind.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        named = {
            node.arg
            for node in ast.walk(tree)
            if isinstance(node, ast.arg)
        } | {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        assert not [name for name in named if "principal" in name]

    def test_the_module_is_declared_algorithmic(self) -> None:
        import ccf.products.bind as module

        assert module.__ccf_mode__ == "algorithmic"

    def test_the_module_imports_no_clock_and_no_client(self) -> None:
        source = Path("src/ccf/products/bind.py").read_text(encoding="utf-8")
        for forbidden in ("datetime.now", "time.time", "httpx", "requests"):
            assert forbidden not in source
