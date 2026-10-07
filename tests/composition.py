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

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import (
    CompositionRegister,
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
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry, skill_catalog_key

__all__ = [
    "composition_register",
    "composition_replay_mint",
    "declaring_store",
    "register_at_composition",
    "register_skill_entry",
    "register_typed_at_composition",
    "register_versioned_at_composition",
    "tenant_of_key",
    "register_fixture_approval_policies",
    "without_approval_policies",
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
) -> Authorized[CompositionRegister]:
    """``Authorized[CompositionRegister]`` for exactly ``key``, minted by the recipe."""
    tenant = tenant_of_key(key)
    event = registry.audit_log.append(
        action="composition",
        key=key,
        version=CompositionRegister.action_id,
        resolved=True,
        occurred_at=clock(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        CompositionRegister,
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


def declare_wide_temporal_boundary(
    registry: ControlPlaneRegistry, *, tenant_id: str
) -> str:
    """Declare a deliberately WIDE `TemporalBoundaryPolicy` for a fixture tenant.

    `D-IMPL-358` step 5 ruling 11: a deployment that declares no temporal boundary
    REFUSES every question — no SDK default and no fallback window. So a fixture
    that means to serve has to declare one, and this is the one place that does it
    so ~20 fixtures cannot drift into ~20 different windows.

    **Wide on purpose.** The window is not what those fixtures are about, and a
    narrow one here would make every unrelated case depend on the fixture's clock —
    which is how a suite acquires a calendar dependency nobody chose. A test that
    is ABOUT the window declares its own narrow one instead.
    """
    from ccf.controlplane.temporal_boundary import (
        TEMPORAL_BOUNDARY_POLICY,
        TemporalBoundaryPolicy,
        temporal_boundary_policy_key,
    )

    return register_typed_at_composition(
        registry,
        temporal_boundary_policy_key(tenant_id=tenant_id),
        TemporalBoundaryPolicy(
            max_past_seconds=10**9, permitted_clock_skew_seconds=10**9
        ),
        TEMPORAL_BOUNDARY_POLICY,
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


def register_skill_entry(
    catalog: SkillCatalog, registry: ControlPlaneRegistry, entry: SkillCatalogEntry
) -> str | RegistrationRefusal:
    """``catalog.register`` under a recipe-minted ``Register`` for exactly the entry's own key.

    The catalog derives the key from the entry and binds the capability to it
    (``D-IMPL-353`` §1.5f); a deployment declaring a catalog entry at boot is
    a composition-time registration (``D-IMPL-354``), which is what a test
    composing its own catalog is doing.
    """
    return catalog.register(composition_register(registry, skill_catalog_key(entry)), entry)


# --- SEC-006 (D-IMPL-366): the typed approval policies the fixtures pin -------

APPROVAL_POLICY_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "banking" / "approval_policies.yaml"
)


def without_approval_policies(references: Mapping[str, Any]) -> dict[str, Any]:
    """``referenced_artifacts`` minus its PRE-CHANGE ``approval-policy`` entries.

    The historical workflow fixtures still carry a DeclaredArtifact approval
    policy in ``referenced_artifacts`` (the fixture rule: nothing is rewritten);
    the factory now refuses that shape by ruling (`D-IMPL-366` §4 (5)), so a
    closure registers everything else here and the typed policy through
    :func:`register_fixture_approval_policies` under the same key.
    """
    return {
        name: reference
        for name, reference in references.items()
        if reference["class_id"] != "approval-policy"
    }


def register_fixture_approval_policies(registry: ControlPlaneRegistry) -> dict[str, str]:
    """Register every typed ``ccf.approval-policy`` in the banking fixture.

    Returns ``{key: pinned ccf-artifact:// URI}`` for each policy registered —
    the URIs the historical workflow fixtures' ``gate_policies`` already carry.
    Registered through ``register_typed`` against the real contract (adopter
    registration; the class is not manifest-addressable by ruling).
    """
    import yaml

    from ccf.controlplane.artifacts import parse_artifact
    from ccf.hitl.approval_policy import APPROVAL_POLICY

    loaded: dict[str, Any] = yaml.safe_load(APPROVAL_POLICY_FIXTURE.read_text())
    pinned: dict[str, str] = {}
    for entry in loaded["policies"].values():
        key = entry["key"]
        policy = parse_artifact(entry["policy"], APPROVAL_POLICY)
        register_typed_at_composition(registry, key, policy, APPROVAL_POLICY)
        tenant, artifact_class, name = key.split("/")
        pinned[key] = f"ccf-artifact://{tenant}/{artifact_class}/{name}@{entry['policy']['semver']}"
    return pinned


class MemoryErasureIndex:
    """An in-memory ``ErasureIndexProtocol`` test double (SEC-009; fix round 1 C1).

    For tests that compose a store but erase nothing: every store construction
    site REQUIRES a declared erasure index, and this is the declared "nothing is
    erased here". Tests that erase use the shipped ``FileErasureIndex``.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], Any] = {}

    def append(self, authorized: Any, entry: Any) -> None:
        from ccf.erasure import require_append_authority

        # The Protocol's I3 contract (fix round 2): the ERASE capability bound
        # to the entry's request, the same check the shipped index makes.
        require_append_authority(authorized, entry)
        key = (entry.tenant_id, entry.content_address)
        standing = self._entries.get(key)
        if standing is not None and standing != entry:
            from ccf.erasure import ErasureIndexEntryExists

            raise ErasureIndexEntryExists(f"{key!r} is already erased")
        self._entries[key] = entry

    def lookup(self, *, tenant_id: str, content_address: str) -> Any:
        return self._entries.get((tenant_id, content_address))

    def entries(self, *, tenant_id: str) -> tuple[Any, ...]:
        return tuple(e for (t, _a), e in self._entries.items() if t == tenant_id)

    def tenants(self) -> frozenset[str]:
        return frozenset(t for t, _a in self._entries)


def no_erasures() -> MemoryErasureIndex:
    """A fresh, empty declared erasure index for a test composition."""
    return MemoryErasureIndex()


def declared_hitl_policy_key(tenant: str = "acme-bank") -> str:
    """The HITL policy key a test deployment declares (SEC-009, fix round 4, ruling 1).

    The same key the deployment's HITL transport is bound to, and the key every
    erasure approval must pin; test vocabulary under the test tenant (CINV-01).
    """
    return f"{tenant}/hitl/erasure-attestation-policy"
