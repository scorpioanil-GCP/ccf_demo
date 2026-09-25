"""The composition-root recipe for tests — D-IMPL-354, in ONE place.

**Tests are composition roots.** A test that builds a registry, registers the
artifacts its fabric will resolve, builds a store and hands the fabric's own
writers their capabilities is doing exactly what ``ccf.boot``,
``ccf.deployment.manifest`` and ``ccf.products.resolver`` do for a deployment
— and under ``D-IMPL-353`` §1.6 / ``D-IMPL-354`` that is the only sanctioned way
the deployment's OWN writes obtain authority. The ``§4`` lint enumerates the
``src``/``runtime`` composition roots (``COMPOSITION_MINT_SITES``); test and
example composition code is outside its population by the same rule that
keeps ``src``/``runtime`` its population, and this module is where the test
half lives so seventy test files do not each restate the recipe.

**The recipe, identical at every composition root** (the join's clause; the
design's §1.6): the composition appends ONE ``composition`` event to the
Control Plane audit log — the decision being recorded is the deployment's own,
so the deployment's audit plane is where it lands — and mints the capability
with that event's content address as its ``decision_id``::

    event = registry.audit_log.append(
        action="composition", key=<resource>, version=<Kind.action_id>,
        resolved=True, occurred_at=<clock>, actor=COMPOSITION_PRINCIPAL,
    )
    capability = mint_at_composition(
        <Kind>, tenant=<tenant>, principal=COMPOSITION_PRINCIPAL,
        resource=<resource>, decision_id=content_hash(event),
    )

Two kinds and nothing else: ``Register`` on ONE Control Plane key (the tenant
is the key's own tenant segment — derived the way the registry's
``CrossTenantKeyRefused`` check derives it, never chosen here), and
``ReplayMint`` on ONE evidence class for ONE tenant. The overloads on
:func:`~ccf.authz.capability.mint_at_composition` make any other kind a
``mypy --strict`` error and its runtime check refuses it.

Beside :mod:`tests.controlplane.capabilities`, which mints DOOR kinds from an
allowed :class:`~ccf.authz.decision.AuthzDecision` for handle tests, and
:mod:`tests.replay.authority`, whose ``replay_mint``-based writers predate the
audited recipe and stay for the replay tree's handle-level tests. Nothing here
constructs ``Authorized`` or names the sentinel.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    Authorized,
    Register,
    ReplayMint,
    mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.registry import (
    ControlPlaneRegistry,
    CrossTenantKeyRefused,
    RegistrationRefusal,
)

__all__ = [
    "composition_register",
    "composition_replay_mint",
    "declaring_store",
    "register_at_composition",
    "register_typed_at_composition",
    "register_versioned_at_composition",
    "tenant_of_key",
]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def tenant_of_key(key: str) -> str:
    """The tenant segment of a ``{tenant}/{class}/{name}`` Control Plane key.

    Derived exactly as the registry derives it for its one tenant comparison
    (``D-IMPL-353`` §1.3): the text before the first ``/``. A key with no
    tenant segment can be registered by nobody, so it is refused here with the
    registry's own error rather than minted for an empty tenant.
    """
    tenant, separator, _ = key.partition("/")
    if not separator or not tenant:
        raise CrossTenantKeyRefused(
            f"Control Plane key {key!r} has no tenant segment; a composition"
            " root mints Register for `{tenant}/{class}/{name}` and a key that"
            " names no tenant belongs to nobody (D-IMPL-353 §1.3)"
        )
    return tenant


def composition_register(
    registry: ControlPlaneRegistry,
    key: str,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> Authorized[Register]:
    """``Authorized[Register]`` for exactly ``key``, minted by the recipe."""
    tenant = tenant_of_key(key)
    event = registry.audit_log.append(
        action="composition",
        key=key,
        version=Register.action_id,
        resolved=True,
        occurred_at=clock(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        Register,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=key,
        decision_id=content_hash(event),
    )


def composition_replay_mint(
    registry: ControlPlaneRegistry,
    *,
    tenant: str,
    artifact_class: str,
    clock: Callable[[], datetime] = _utc_now,
) -> Authorized[ReplayMint]:
    """``Authorized[ReplayMint]`` for ``artifact_class`` under ``tenant``, minted by the recipe."""
    event = registry.audit_log.append(
        action="composition",
        key=artifact_class,
        version=ReplayMint.action_id,
        resolved=True,
        occurred_at=clock(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        ReplayMint,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=artifact_class,
        decision_id=content_hash(event),
    )


def register_at_composition(
    registry: ControlPlaneRegistry, key: str, artifact: object
) -> str:
    """``registry.register`` under a recipe-minted ``Register`` for ``key``."""
    return registry.register(composition_register(registry, key), artifact)


def register_typed_at_composition(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
) -> str:
    """``registry.register_typed`` under a recipe-minted ``Register`` for ``key``."""
    return registry.register_typed(
        composition_register(registry, key), artifact, artifact_class
    )


def register_versioned_at_composition(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
    *,
    reissuable: bool = False,
) -> str | RegistrationRefusal:
    """``registry.register_versioned`` under a recipe-minted ``Register`` for ``key``."""
    return registry.register_versioned(
        composition_register(registry, key),
        artifact,
        artifact_class,
        reissuable=reissuable,
    )


def declaring_store(root: Path | str, *classes: str) -> FileArtifactStore:
    """A file store declaring every class in ``classes`` mechanism-written under ``ReplayMint``.

    The deployment's declaration (``D-IMPL-353`` §1.2), made by the test as
    the composition root it is: a class not named here is the client lane and
    requires ``Authorized[ArtifactWrite]``; a class named here admits only a
    :class:`~ccf.artifacts.protocol.DerivedWrite` under ``ReplayMint``.
    """
    return FileArtifactStore(
        root=root,
        write_kinds=WriteKinds.declare({name: (ReplayMint,) for name in classes}),
    )
