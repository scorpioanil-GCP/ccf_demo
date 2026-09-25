"""The resolver's composition mint reads its tenant off the MAX_TTL key — RECORDED, not fixed (D-IMPL-354, join panel round 2).

Cursor's F-COMP-01 at the D-IMPL-353 join's second panel: `_mint_register_at_composition`
mints ``Register`` for whatever segment ``ProductClassDeclaration.max_ttl_key`` begins
with — the shape the register loop had before the first panel. The join tried the
same fix (tell the mint the fabric's tenant, refuse any other) and 159 tests went red,
because ``max_ttl_key`` is authored INSIDE the product-class declaration and is not
tenant-keyed by any grammar the SDK enforces: the deployment fixtures name
``tenant-fixture/max-ttl`` under tenants ``replay-binding-fixture-tenant`` and
``paved-child-tenant``, the client fixture names ``fixture/widgets-over-score/max-ttl``
under ``tenant-client-fixture``, and cp-05's FROZEN declaration names
``cp-05/product/credit-exposure-rollup/max-ttl`` under ``cp-05-demo``. So the MAX_TTL
artifact is registered under a pseudo-tenant segment that two deployments could share —
the collision `D-IMPL-354` exists to prevent. Closing it is a ruling: enforce the
``{tenant}/{class}/{name}`` grammar on ``max_ttl_key`` as `D-IMPL-343` R-2 does for an
agent's refs (breaks cp-05's frozen declaration — a ledger row), or have the loader
place it. These two tests pin the CURRENT behavior so the ruling's implementation
turns them red rather than silently changing what a composition root mints for.
"""

from __future__ import annotations

import pytest

from ccf.authz.capability import COMPOSITION_PRINCIPAL, CompositionRegister, Register, verify
from ccf.controlplane.registry import ControlPlaneRegistry, CrossTenantKeyRefused
from ccf.products.resolver import _mint_register_at_composition


def test_the_mint_is_for_whatever_segment_the_max_ttl_key_names_recorded_hazard() -> None:
    registry = ControlPlaneRegistry()
    key = "some-other-segment/product/max-ttl"
    authorized = _mint_register_at_composition(registry, key=key)
    verify(authorized, kind=CompositionRegister, resource=key)
    # The hazard, stated as the assertion the ruling will flip: the tenant is the
    # key's first segment, whatever fabric this resolver composes for.
    assert authorized.tenant == "some-other-segment"
    assert authorized.principal == COMPOSITION_PRINCIPAL
    (event,) = registry.audit_events()
    assert event.action == "composition" and event.key == key


def test_a_key_with_no_segment_is_refused_before_anything_is_minted() -> None:
    registry = ControlPlaneRegistry()
    with pytest.raises(CrossTenantKeyRefused, match="no tenant segment"):
        _mint_register_at_composition(registry, key="max-ttl")
    assert registry.audit_events() == ()
