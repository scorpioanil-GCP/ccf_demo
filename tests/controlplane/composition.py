"""Composition-root registrations for tests — the D-IMPL-354 recipe, test side only.

A test fixture that boots a fabric — registering a resolution spec, a policy
bundle, an HITL policy, a MAX_TTL, or a fixture agent's referenced artifacts
— is standing in for the deployment's composition root. Under ``D-IMPL-353``
§1.2 the registry's handles REQUIRE a capability for their own action, and
under ``D-IMPL-354`` (PROPOSED, awaiting Dave) the composition root is the
one caller that may mint ``Register`` — for ONE Control Plane key at a time,
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


def composition_register_capability(
    registry: ControlPlaneRegistry, key: str, *, tenant: str | None = None
) -> Authorized[Register]:
    """``Authorized[Register]`` for exactly ``key``, recorded on ``registry``'s audit log.

    The tenant defaults to the key's own tenant segment — the text before the
    first ``/`` of the ``{tenant}/{class}/{name}`` grammar — because a
    composition root registers under the tenant it composes for, and the
    registry's one tenant comparison (§1.3) refuses anything else. A caller
    that wants the *disagreeing* case passes ``tenant`` explicitly.
    """
    if tenant is None:
        segment, separator, _ = key.partition("/")
        tenant = segment if separator and segment else key
    event = registry.audit_log.append(
        action="composition",
        key=key,
        version=Register.action_id,
        resolved=True,
        occurred_at=COMPOSED_AT,
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        Register,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=key,
        decision_id=content_hash(event),
    )


def compose_register(registry: ControlPlaneRegistry, key: str, artifact: object) -> str:
    """``registry.register`` under a composition-minted capability for ``key``."""
    return registry.register(composition_register_capability(registry, key), artifact)


def compose_register_typed(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
) -> str:
    """``registry.register_typed`` under a composition-minted capability for ``key``."""
    return registry.register_typed(
        composition_register_capability(registry, key), artifact, artifact_class
    )


def compose_register_versioned(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
    *,
    reissuable: bool = False,
) -> str | RegistrationRefusal:
    """``registry.register_versioned`` under a composition-minted capability for ``key``.

    Returns the handle's own outcome unchanged — a version, or the typed
    refusal the D-05 bump check produces — so a test asserting a refusal
    asserts the registry's, not the helper's.
    """
    return registry.register_versioned(
        composition_register_capability(registry, key),
        artifact,
        artifact_class,
        reissuable=reissuable,
    )
