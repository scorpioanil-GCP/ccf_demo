"""Boot HW-1's deployment and build the governed resolver its wiring declares.

A separate file from ``serve.py`` because the door and the boot are different
concerns, and a reader who opens the program ``binding.yaml`` names should find
a server there rather than a fabric composition. ``serve.py`` is about the MCP
door — its governance values, its stdio identity, the one call that runs it.
This is everything that has to exist before there is anything to serve, and it
would be the same work behind any other door.

**It composes through the SDK's public seams and nothing private.** Every name
imported below is exported from its package. There is a private
``ccf.client.adapters.inprocess::_boot`` that does this same composition for the
in-process transport, and it is deliberately not used: a demonstration of
adoptability that reached into the SDK's private surface would demonstrate the
opposite. What this file does with public names, an adopter can do.

Everything it needs arrives in the loaded ``binding.yaml`` document — the same
document the in-process adapter reads, so both transports compose the *same*
governed resolver from the *same* declared values. That is what makes "the same
answer over two transports" a property rather than a coincidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from ccf.artifacts.file_store import FileArtifactStore
from ccf.client.adapters.binding_document import (
    BindingDocument,
    conforming_plan_factory,
    load_reference,
)
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneProtocol, ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import (
    ServedProductResolverProtocol,
    build_governed_resolver,
)


@dataclass(frozen=True)
class ComposedDeployment:
    """One booted deployment, carrying exactly what a door needs to serve.

    Frozen and handle-carrying for the reason
    :class:`~ccf.deployment.BootedFabric` gives for its own shape: a live handle
    has no canonical serialization and never belongs in a content hash.

    Three values and no fourth. The binding document is not among them: the door
    already holds it — it is what the door passed in — and a bundle that handed
    it back would be inviting a reader to wonder which copy is authoritative.
    """

    fabric: BootedFabric
    control_plane: ControlPlaneProtocol
    resolver: ServedProductResolverProtocol


def compose(document: BindingDocument) -> ComposedDeployment:
    """Boot the deployment ``document`` describes and build its resolver.

    The public path, step for step: boot the fabric, resolve the one permitted
    projection reference, and hand all of it to
    :func:`~ccf.products.resolver.build_governed_resolver`, which is where the
    SDK selects its own reference debt scorer so a deployment supplying only
    data never has to know the Protocol exists. Then register the entitlement
    policy that decides who this fabric will answer, because a resolver nobody
    is entitled to reach is not yet a deployment a door can open.

    Returns:
        The booted fabric, the Control Plane it registered into, and the
        governed resolver — the three values a door serves with.
    """
    control_plane = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        document.config, registry=control_plane, connection=document.connection
    )
    resolver = build_governed_resolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=document.product_class_key,
        request_contract_key=document.request_contract_key,
        operator_parameter_keys=document.operator_parameter_keys,
        policy_bundle_key=document.policy_bundle_key,
        plan_factory=conforming_plan_factory(
            load_reference(document.plan, root=document.root, key="plan"),
            reference=document.plan,
            root=document.root,
        ),
        artifact_store=FileArtifactStore(root=document.artifact_store),
        replay_record_class=document.replay_record_class,
        query_pin_class=document.query_pin_class,
        max_ttl_seconds=document.max_ttl_seconds,
        product_ttl_seconds=document.product_ttl_seconds,
        half_life_key=document.debt.half_life_key,
        debt_profile_key=document.debt.debt_profile_key,
        declared_completeness=document.debt.completeness,
        declared_semantic_consistency=document.debt.semantic_consistency,
    )

    declaration = fabric.artifacts[document.product_class_key]
    if not isinstance(declaration, ProductClassDeclaration):
        raise TypeError(
            f"`{document.product_class_key}` in {document.config} is not a"
            " product class declaration"
        )

    # The permitted class and the permitted role are the ones this deployment
    # actually serves and assembles under — taken from the registered class and
    # from `binding.yaml`'s `perspective:`, never restated here, so an
    # entitlement cannot name a class this fabric does not serve.
    perspective = document.perspective
    control_plane.register_typed(
        product_entitlement_key(tenant_id=fabric.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=fabric.tenant_id,
            policy_version=declaration.schema_version,
            principals={
                perspective.principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({declaration.schema_name}),
                    permitted_roles=frozenset({perspective.role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    return ComposedDeployment(
        fabric=fabric, control_plane=control_plane, resolver=resolver
    )
