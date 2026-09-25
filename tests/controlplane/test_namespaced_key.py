"""The Control Plane key grammar's one derivation for a deployment's own keys.

D-IMPL-353 §1.3 / D-IMPL-354 (join). A Control Plane key is
``{tenant}/{class}[/{name}]`` and the registry reads the tenant as the
segment before the first ``/``. The SDK's config loader derives section keys
from labels (``product_class``, ``agent``, ``policy``) with no tenant
segment, and the paved-road binding document names them the same way; both
were refused outright once every registration required a capability for the
key's own tenant. ``namespaced_key`` is the single place a deployment's bare
key becomes a keyed one — under the deployment's resolved tenant — and the
single place a prefixed key is confined to the tenant before anything is minted.
"""

from __future__ import annotations

import pytest

from ccf.controlplane.registry import namespaced_key


def test_a_bare_key_is_placed_under_the_tenant() -> None:
    assert namespaced_key(tenant="acme-bank", key="product_class") == "acme-bank/product_class"


def test_a_key_already_under_the_tenant_is_unchanged() -> None:
    key = "acme-bank/ccf.product-class/loans"
    assert namespaced_key(tenant="acme-bank", key=key) == key


def test_a_key_under_another_prefix_is_confined_under_the_tenant() -> None:
    """A leading segment is not a tenant claim (a label may contain `/`); the
    deployment can never land outside its own tenant, and the confined key is
    what the audit log shows."""
    assert (
        namespaced_key(tenant="acme-bank", key="beta-bank/product_class")
        == "acme-bank/beta-bank/product_class"
    )
    assert (
        namespaced_key(tenant="cp-05-demo", key="policy_constraints.cp-05/policy/ceiling")
        == "cp-05-demo/policy_constraints.cp-05/policy/ceiling"
    )


@pytest.mark.parametrize("bad", ["", " ", "/x", "acme-bank/", "a//b"])
def test_an_unusable_key_or_tenant_is_refused(bad: str) -> None:
    with pytest.raises(ValueError):
        namespaced_key(tenant="acme-bank", key=bad)
    with pytest.raises(ValueError):
        namespaced_key(tenant=bad, key="product_class")
