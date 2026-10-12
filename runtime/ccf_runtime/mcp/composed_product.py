"""The standard door over a hand-composed product — the shared adapter, once (round 5, item 1).

**SDK-defined** (CLAUDE.md §7.1, §8.3, §11); an extension beyond the
whitepaper, and it says so. Dave, 2026-10-11 20:19 MST: *"Build the listed SDK
repairs in one round. Scope: ... the shared door adapter ... Preserve ...
authorization and record integrity."*

Why this exists
---------------
Since ``D-IMPL-353`` a deployment cannot compose an MCP door by hand: the
Control Plane takes a registration only under a capability SDK composition
mints (``CapabilityBypassError``), and
:func:`~ccf_runtime.mcp.egress.build_egress_server` requires an ``authorizer``
decided over a registered, version-pinned ``ccf.scope-mapping`` that no
deployment can register or declare. The supported path for a product a
deployment composes by hand (its own assembler, its own per-question fabric —
not :func:`~ccf.products.product.open_product`) is the standard door,
:func:`~ccf_runtime.mcp.product_door.open_door` /
:func:`~ccf_runtime.mcp.product_door.open_door_with_verifier`, over anything
conforming to :class:`~ccf_runtime.mcp.product_door.ServesProducts`. Round 3
wrote that conformer three times — cp-07, cp-04 and door-cp-05, ~60 lines each
— and each one did the same things:

1. a fresh :class:`~ccf.controlplane.registry.ControlPlaneRegistry`;
2. one throwaway SDK boot of the deployment's ``ccf_config.yaml`` into it, so the
   SDK's own composition registers what the deployment DECLARED — notably its
   ``product_entitlement:`` (G4-F-04) — and pins its ``policy`` bundle;
3. the policy pin read off that boot;
4. a refusal recorder built by the SDK's
   :func:`~ccf.products.resolver.declared_refusal_recorder` over the
   deployment's replay store and that Control Plane;
5. the declaration, the default perspective, the door binding and the
   environment document, held as the nine members the door reads;
6. ``resolve`` delegated to the deployment's own governed path.

This module is that, once. **It decides nothing and registers nothing of its
own**: the registrations are the SDK boot's (step 2) and the door's
(:func:`~ccf_runtime.mcp.product_door.open_door`'s scope mapping, and its
one-principal entitlement default where — and only where — nothing was
declared); the recorder is the SDK's; every governance decision on the wire is
:func:`~ccf_runtime.mcp.egress.build_egress_server`'s. It mints no capability
and calls no registration door, so it is not a composition root.

What it does not do
-------------------
It does not open the door. The caller opens the standard door over the
:class:`ComposedProduct` with its own verifier, perspective resolver and
transport, exactly as it would over an
:class:`~ccf.products.product.OpenedProduct` — the authorizer and scope mapping
are derived there, identically for both roads.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.controlplane.artifacts import (
    EgressDoorBinding,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import EnvironmentDocument, load_config_and_boot, load_environment_document
from ccf.products.resolver import RefusalRecorderProtocol, declared_refusal_recorder
from ccf.projection.plan import Perspective
from ccf.replay.record import PolicyBinding
from ccf_runtime.mcp.egress import ProductResolverProtocol

__all__ = ["ComposedProduct", "compose_for_door"]

#: What a deployment that records refusals INSIDE its own governed path hands
#: in instead of a finished resolver: a factory over the ONE recorder this
#: composition builds, so the door's entitlement denials and the assembler's
#: own refusals are filed by one recorder under one policy pin (cp-04's shape).
ResolverFactory = Callable[[RefusalRecorderProtocol], ProductResolverProtocol]


@dataclass(frozen=True)
class ComposedProduct:
    """A hand-composed product, held as the nine members the standard door reads.

    Conforms to :class:`~ccf_runtime.mcp.product_door.ServesProducts`. Built
    only by :func:`compose_for_door`.

    Attributes:
        tenant_id: The tenant the deployment's own boot resolved.
        declaration: The deployment's ``product_class`` section, parsed by the boot.
        default_perspective: The perspective the door serves under by default.
        control_plane: The ONE Control Plane the boot registered the
            deployment's declarations into; the door registers into it too.
        refusal_recorder: The ONE recorder every denial is appended through.
        door: The declared door binding (identity asserted on every outcome).
        environment: The environment document naming the door's credential.
        policy_bundle_pin: The ``policy`` pin every refusal record carries.
        replay_store: The store the recorder writes (and a reader reads).
        resolve: The deployment's governed path (``ProductResolverProtocol``).
    """

    tenant_id: str
    declaration: ProductClassDeclaration
    default_perspective: Perspective
    control_plane: ControlPlaneRegistry
    refusal_recorder: RefusalRecorderProtocol
    door: EgressDoorBinding
    environment: EnvironmentDocument
    policy_bundle_pin: PolicyBinding
    replay_store: ArtifactStoreProtocol
    #: The deployment's own governed path, unchanged — held, never called
    #: here. The standard door calls it (``ProductDoor.server`` hands
    #: ``product.resolve`` to :func:`~ccf_runtime.mcp.egress.build_egress_server`),
    #: after its authorizer and entitlement step, exactly as for a paved product.
    resolve: ProductResolverProtocol


def compose_for_door(
    config_path: Path,
    *,
    boot_connection: Mapping[str, object],
    environment_root: Path,
    door: EgressDoorBinding | None,
    replay_store: ArtifactStoreProtocol,
    replay_record_class: str,
    resolver: ProductResolverProtocol | None = None,
    build_resolver: ResolverFactory | None = None,
    default_perspective: Perspective | None = None,
) -> ComposedProduct:
    """Compose a hand-built product for the standard door, the way every such door did.

    Boots ``config_path`` ONCE through the SDK's own
    :func:`~ccf.deployment.load_config_and_boot` into a fresh Control Plane —
    so everything the deployment declared is registered by the SDK's
    composition recipe, its ``product_entitlement:`` included — reads the
    ``policy`` pin off that boot, closes the boot's fabric (nothing reads it;
    the deployment answers each question on its own fabric), and builds the
    refusal recorder with :func:`~ccf.products.resolver.declared_refusal_recorder`
    over ``replay_store`` and that Control Plane.

    Args:
        config_path: The deployment's ``ccf_config.yaml``.
        boot_connection: The connection settings for the one throwaway boot —
            an owned scratch substrate the caller chose.
        environment_root: The directory holding ``ccf_environment.yaml``, whose
            ``door:`` block names the door's credential variable.
        door: The door binding; ``None`` takes the config's own ``door:``
            section, and a deployment declaring neither is refused by name.
        replay_store: Where the recorder files every refusal record.
        replay_record_class: The replay-record class the store declares.
        resolver: The deployment's governed path, finished.
        build_resolver: Instead of ``resolver``: a factory handed the ONE
            recorder, for a governed path that records its own refusals.
        default_perspective: Overrides the config's ``default_perspective``.

    Raises:
        ValueError: neither or both of ``resolver``/``build_resolver``; no door
            binding anywhere; the config declares no ``default_perspective``
            and none was supplied.
    """
    if (resolver is None) == (build_resolver is None):
        raise ValueError(
            "compose_for_door takes exactly one of resolver= (the deployment's"
            " finished governed path) and build_resolver= (a factory handed the"
            " one refusal recorder); neither or both is ambiguous about which"
            " recorder files the deployment's own refusals"
        )
    control_plane = ControlPlaneRegistry()
    booted = load_config_and_boot(
        config_path, registry=control_plane, connection=dict(boot_connection)
    )
    try:
        keys = booted.keys
        if keys is None:
            raise ValueError(
                f"{config_path} did not boot as a single-file deployment config; the"
                " door reads the product class, policy, perspective and door sections"
                " the single-file derivation places (D-IMPL-343)"
            )
        tenant_id = booted.tenant_id
        declaration = booted.artifacts[keys.product_class]
        assert isinstance(declaration, ProductClassDeclaration)  # PRODUCT_CLASS's contract
        policy_pin = PolicyBinding(
            key=keys.policy_bundle, version=booted.pins.version_for(keys.policy_bundle)
        )
        declared_perspective = (
            booted.artifacts[keys.default_perspective]
            if keys.default_perspective is not None
            else None
        )
        declared_door = booted.artifacts[keys.door] if keys.door is not None else None
    finally:
        booted.handle.close()

    if default_perspective is None:
        if not isinstance(declared_perspective, PerspectiveArtifact):
            raise ValueError(
                f"{config_path} declares no 'default_perspective' section and none"
                " was supplied; the door serves under a declared perspective and"
                " holds no default of its own (CINV-01)"
            )
        default_perspective = Perspective(
            principal_id=declared_perspective.principal_id, role=declared_perspective.role
        )
    if door is None:
        if not isinstance(declared_door, EgressDoorBinding):
            raise ValueError(
                f"{config_path} declares no 'door' section and no door binding was"
                " supplied; the standard door asserts the identity a binding"
                " declares and holds no default for it (D-IMPL-343; CINV-01)"
            )
        door = declared_door

    recorder = declared_refusal_recorder(
        control_plane=control_plane,
        artifact_store=replay_store,
        replay_record_class=replay_record_class,
        tenant_id=tenant_id,
        assembly_mode=declaration.assembly_mode,
        policy_bundle_pin=policy_pin,
    )
    if resolver is not None:
        built = resolver
    else:
        assert build_resolver is not None  # exactly one, checked above
        built = build_resolver(recorder)
    return ComposedProduct(
        tenant_id=tenant_id,
        declaration=declaration,
        default_perspective=default_perspective,
        control_plane=control_plane,
        refusal_recorder=recorder,
        door=door,
        environment=load_environment_document(environment_root),
        policy_bundle_pin=policy_pin,
        replay_store=replay_store,
        resolve=built,
    )
