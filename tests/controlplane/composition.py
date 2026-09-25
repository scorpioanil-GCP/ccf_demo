"""Composition-root registrations for tests — the D-IMPL-354 recipe, test side only.

A test fixture that boots a fabric — registering a resolution spec, a policy
bundle, an HITL policy, a MAX_TTL, or a fixture agent's referenced artifacts
— is standing in for the deployment's composition root. Under ``D-IMPL-353``
§1.2 the registry's handles REQUIRE a capability for their own action, and
under ``D-IMPL-354`` (PROPOSED, awaiting Dave) the composition root is the
one caller that may mint ``CompositionRegister`` — for ONE Control Plane key at a time,
after recording that decision on the audit log the registry itself keeps.
These helpers do exactly that: the audit event is appended first, the
capability is minted from its content hash, and the handle is called with
it. Nothing here names the sentinel or constructs ``Authorized``; the
capability comes from :func:`ccf.authz.capability.mint_at_composition`, the
only producer of a composition kind.

Tests are composition roots outside the §4 lint's scope by the same rule
that keeps ``src``/``runtime`` its population (``D-IMPL-354``); a test that
registers through these helpers reads as the deployment it stands in for.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ccf.authz.capability import (
    CompositionRegister,
    COMPOSITION_PRINCIPAL,
    Authorized,
    Register,
    mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import ArtifactClass
from ccf.controlplane.registry import ControlPlaneRegistry, RegistrationRefusal

__all__ = [
    "COMPOSED_AT",
    "compose_register",
    "compose_register_typed",
    "compose_register_versioned",
    "composition_register_capability",
]

#: The fixed instant every composition decision in a test is recorded at, so
#: the audit event — and therefore the capability's ``decision_id`` — is the
#: same bytes on every run of the same test.
COMPOSED_AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


# The canonical recipe lives in ``tests/composition.py`` (Lane J-SRC's shared
# fixture module). These names stay for the files that import them and
# DELEGATE — one implementation of the composition recipe in tests/, not two.
from tests.composition import (  # noqa: E402
    composition_register as _composition_register,
    register_at_composition as _register_at_composition,
    register_typed_at_composition as _register_typed_at_composition,
    register_versioned_at_composition as _register_versioned_at_composition,
    tenant_of_key as _tenant_of_key,
)


def composition_register_capability(
    registry: ControlPlaneRegistry, key: str, tenant: str
) -> Authorized[CompositionRegister]:
    """A genuine ``Authorized[CompositionRegister]`` for ``key`` — the canonical recipe.

    ``tenant`` must be the key's own tenant segment (the registry refuses any
    other); it is kept as a parameter so a caller's expectation is checked
    rather than silently replaced.
    """
    assert tenant == _tenant_of_key(key), (tenant, key)
    return _composition_register(registry, key)


def compose_register(registry: ControlPlaneRegistry, key: str, artifact: object) -> str:
    return _register_at_composition(registry, key, artifact)


def compose_register_typed(
    registry: ControlPlaneRegistry, key: str, artifact: object, artifact_class: ArtifactClass
) -> str:
    return _register_typed_at_composition(registry, key, artifact, artifact_class)


def compose_register_versioned(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
    reissuable: bool = False,
) -> object:
    return _register_versioned_at_composition(
        registry, key, artifact, artifact_class, reissuable=reissuable
    )
