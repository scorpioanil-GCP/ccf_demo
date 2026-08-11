"""The product-entitlement artifact: lane, closure, entitlement, tenancy.

Named per property defended, on the shape ``tests/peering/test_trust_policy.py``
already proves for the A2A boundary.

Two of these exist because a weaker suite would pass against a broken
implementation:

* the **field-enumeration** test makes "this contract cannot express a bypass"
  a claim the suite enforces rather than one the docstring asserts — a
  docstring cannot fail when a later contributor adds ``unrestricted_principal``;
* the **two-tenant** test is the D-23 obligation: an entitlement check that is
  right with one tenant and wrong with two is the CR-01 defect class, and a
  single-tenant suite would not see it.

Principal identifiers, role names and product-class names are all fixture
vocabulary. The SDK enumerates none of them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    PrincipalNotEntitled,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    ProductEntitlementViolation,
    product_entitlement_key,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

PRINCIPAL = "analyst-4471"
OTHER_PRINCIPAL = "auditor-9902"
TENANT_ONE = "acme-bank"
TENANT_TWO = "borealis-bank"
UNGRANTED_ROLE = "chief-risk-officer"
UNGRANTED_SCHEMA = "acme-bank.some-other-product"


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def _schema_name() -> str:
    schema: str = _fixture("controlplane.yaml")["product_class"]["schema_name"]
    return schema


def _role() -> str:
    role: str = _fixture("controlplane.yaml")["perspective"]["role"]
    return role


def grant(
    *,
    schema_names: frozenset[str] | None = None,
    roles: frozenset[str] | None = None,
) -> ProductEntitlementGrant:
    return ProductEntitlementGrant(
        permitted_schema_names=(
            schema_names if schema_names is not None else frozenset({_schema_name()})
        ),
        permitted_roles=(roles if roles is not None else frozenset({_role()})),
    )


def policy(
    *, tenant_id: str = TENANT_ONE, **kwargs: Any
) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant_id,
        policy_version="1.0.0",
        principals={PRINCIPAL: grant(**kwargs)},
    )


# --- the semver lane -------------------------------------------------------


def test_a_policy_without_a_version_lane_cannot_be_constructed() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(  # type: ignore[call-arg]
            tenant_id=TENANT_ONE, principals={PRINCIPAL: grant()}
        )


def test_a_policy_with_a_malformed_version_lane_is_refused() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(
            tenant_id=TENANT_ONE,
            policy_version="one",
            principals={PRINCIPAL: grant()},
        )


def test_a_policy_naming_no_principals_is_refused() -> None:
    """An empty policy is indistinguishable from a forgotten one."""
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(
            tenant_id=TENANT_ONE, policy_version="1.0.0", principals={}
        )


# --- closure ---------------------------------------------------------------


def test_an_unknown_field_on_a_policy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(
            tenant_id=TENANT_ONE,
            policy_version="1.0.0",
            principals={PRINCIPAL: grant()},
            unrestricted_principal=PRINCIPAL,  # type: ignore[call-arg]
        )


def test_an_unknown_field_on_a_grant_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementGrant(
            permitted_schema_names=frozenset(),
            permitted_roles=frozenset(),
            allow_all_schemas=True,  # type: ignore[call-arg]
        )


# --- entitlement -----------------------------------------------------------


def test_a_principal_may_receive_only_the_classes_its_grant_lists() -> None:
    entry = policy().grant_for(principal_id=PRINCIPAL)
    entry.require_schema(schema_name=_schema_name())
    with pytest.raises(ProductEntitlementViolation):
        entry.require_schema(schema_name=UNGRANTED_SCHEMA)


def test_a_principal_may_assert_only_the_roles_its_grant_lists() -> None:
    entry = policy().grant_for(principal_id=PRINCIPAL)
    entry.require_role(role=_role())
    with pytest.raises(ProductEntitlementViolation):
        entry.require_role(role=UNGRANTED_ROLE)


def test_an_empty_grant_permits_nothing_rather_than_everything() -> None:
    """The permissive reading of an empty set is the bypass in disguise."""
    entry = ProductEntitlementGrant(
        permitted_schema_names=frozenset(), permitted_roles=frozenset()
    )
    with pytest.raises(ProductEntitlementViolation):
        entry.require_schema(schema_name=_schema_name())
    with pytest.raises(ProductEntitlementViolation):
        entry.require_role(role=_role())


def test_an_unconfigured_principal_is_refused_not_given_an_empty_grant() -> None:
    with pytest.raises(PrincipalNotEntitled):
        policy().grant_for(principal_id=OTHER_PRINCIPAL)


def test_neither_resolution_surface_returns_a_boolean() -> None:
    """A refusal a caller can read as "not sure" is not a refusal.

    Both checks return ``None`` on success, so there is no truthy/falsy value
    an admission path could branch on and mistake for a verdict.
    """
    entry = policy().grant_for(principal_id=PRINCIPAL)
    assert entry.require_schema(schema_name=_schema_name()) is None
    assert entry.require_role(role=_role()) is None


# --- the key derivation ----------------------------------------------------


def test_the_key_derivation_is_a_pure_function_of_its_argument() -> None:
    key = product_entitlement_key(tenant_id=TENANT_ONE)
    assert key == product_entitlement_key(tenant_id=TENANT_ONE)
    assert key.startswith(f"{PRODUCT_ENTITLEMENT_POLICY.class_id}/")
    assert TENANT_ONE in key


def test_two_tenants_never_share_a_control_plane_key() -> None:
    assert product_entitlement_key(
        tenant_id=TENANT_ONE
    ) != product_entitlement_key(tenant_id=TENANT_TWO)
