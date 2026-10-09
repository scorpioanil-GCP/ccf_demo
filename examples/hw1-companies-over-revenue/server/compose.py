"""Boot HW-1's deployment and hold what the SDK's standard door serves.

A separate file from ``serve.py`` because the door and the boot are different
concerns, and a reader who opens the program ``binding.yaml`` names should find
a server there rather than a fabric composition. ``serve.py`` is about the MCP
door: the documents it reads, its stdio identity, the one call that runs it.
This is everything that has to exist before there is anything to serve, and it
would be the same work behind any other door.

**It composes through the SDK's public seams and nothing private.** Every name
imported below is exported from its package. The in-process transport composes
the same resolver in ``ccf.client.adapters.inprocess::_boot``, which is private
and deliberately not used: a demonstration of adoptability that reached into
the SDK's private surface would demonstrate the opposite. So this module states
with public names what that function states: the keys placed under the booted
tenant (``D-IMPL-354``), the evidence classes the store's writers file under
``ReplayMint`` (``D-IMPL-353`` §1.2), and the durable erasure index with the
declared erasure authority (``SEC-009``). The two compositions are two copies of
one statement, so a change to either is a change to both.

Everything it needs arrives in the loaded ``binding.yaml`` document, the same
document the in-process adapter reads, so both transports compose the *same*
governed resolver from the *same* declared values. That is what makes "the same
answer over two transports" a property rather than a coincidence.

What the door needs is the structural
:class:`~ccf_runtime.mcp.product_door.ServesProducts`: nine members, every one
of which this deployment already holds. :class:`ComposedDeployment` carries
them, and :func:`~ccf_runtime.mcp.product_door.open_door` does the rest (the
entitlement policy, the scope mapping its authorizer decides under, the token
source, the perspective resolver and the egress server). None of that is
restated here.
"""

from __future__ import annotations

from dataclasses import dataclass

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.client.adapters.binding_document import (
    BindingDocument,
    conforming_plan_factory,
    load_reference,
)
from ccf.controlplane.artifacts import EgressDoorBinding, ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry, namespaced_key
from ccf.deployment import BootedFabric, EnvironmentDocument, load_config_and_boot
from ccf.erasure import erasure_index_at
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.request import ProductRequest
from ccf.products.resolver import (
    GovernedResolver,
    RefusalRecorderProtocol,
    ResolverOutcome,
    build_governed_resolver,
)
from ccf.projection.plan import Perspective


@dataclass(frozen=True)
class ComposedDeployment:
    """One booted deployment, carrying the nine members the standard door reads.

    Frozen and handle-carrying for the reason
    :class:`~ccf.deployment.BootedFabric` gives for its own shape: a live handle
    has no canonical serialization and never belongs in a content hash.

    Seven are held and two are read off them, so no fact has two homes: the
    tenant is the booted fabric's, and the recorder every denial is appended
    through is the resolver's own, over the resolver's own store
    (``D-IMPL-256``).
    """

    fabric: BootedFabric
    control_plane: ControlPlaneRegistry
    resolver: GovernedResolver
    declaration: ProductClassDeclaration
    default_perspective: Perspective
    door: EgressDoorBinding
    environment: EnvironmentDocument

    @property
    def tenant_id(self) -> str:
        """The tenant this deployment booted as, off the fabric itself."""
        return self.fabric.tenant_id

    @property
    def refusal_recorder(self) -> RefusalRecorderProtocol:
        """The resolver's own recorder: one record form for door and fabric."""
        return self.resolver.refusal_recorder

    def resolve(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome:
        """Answer one question through the governed resolver, unchanged."""
        return self.resolver(
            tenant=tenant,
            product_class=product_class,
            version=version,
            perspective=perspective,
            request=request,
        )


def compose(
    document: BindingDocument,
    *,
    door: EgressDoorBinding,
    environment: EnvironmentDocument,
) -> ComposedDeployment:
    """Boot the deployment ``document`` describes and build its resolver.

    The public path, step for step: boot the fabric into a fresh Control Plane,
    place every key ``binding.yaml`` names under the tenant the boot resolved,
    and hand the result to
    :func:`~ccf.products.resolver.build_governed_resolver`, which is where the
    SDK selects its own reference debt scorer so a deployment supplying only
    data never has to know the Protocol exists.

    ``door`` and ``environment`` are the door's two documents, read by
    ``serve.py``. They are carried here, not interpreted: the door reads them.

    Returns:
        The deployment as the standard door reads it.
    """
    control_plane = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        document.config, registry=control_plane, connection=document.connection
    )

    # `binding.yaml` names the keys the way the config loader derived them
    # (`product_class`, `policy`, ...), and the loader placed each under the
    # resolved tenant at boot (`D-IMPL-354`), so they are read under it here.
    def under(key: str) -> str:
        return namespaced_key(tenant=fabric.tenant_id, key=key)

    declaration = fabric.artifacts[under(document.product_class_key)]
    if not isinstance(declaration, ProductClassDeclaration):
        raise TypeError(
            f"`{document.product_class_key}` in {document.config} is not a"
            " product class declaration"
        )

    resolver = build_governed_resolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=under(document.product_class_key),
        request_contract_key=under(document.request_contract_key),
        operator_parameter_keys=tuple(
            under(key) for key in document.operator_parameter_keys
        ),
        policy_bundle_key=under(document.policy_bundle_key),
        plan_factory=conforming_plan_factory(
            load_reference(document.plan, root=document.root, key="plan"),
            reference=document.plan,
            root=document.root,
        ),
        # The store states which classes the fabric's own writers file and
        # under which kind (`D-IMPL-353` §1.2): the two classes `binding.yaml`
        # names and the SDK's admitted-child class, each under `ReplayMint`.
        # The resolver refuses at construction if a class it files is missing.
        artifact_store=FileArtifactStore(
            root=document.artifact_store,
            write_kinds=WriteKinds.declare(
                {
                    document.replay_record_class: (ReplayMint,),
                    document.query_pin_class: (ReplayMint,),
                    ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,),
                }
            ),
        ),
        # SEC-009 (`D-IMPL-374` (4)): the durable erasure index beside the
        # declared store, and the erasure authority `binding.yaml` declares.
        erasure_index=erasure_index_at(document.artifact_store),
        erasure_trust=document.erasure_trust(tenant_id=fabric.tenant_id),
        replay_record_class=document.replay_record_class,
        query_pin_class=document.query_pin_class,
        max_ttl_seconds=document.max_ttl_seconds,
        product_ttl_seconds=document.product_ttl_seconds,
        half_life_key=under(document.debt.half_life_key),
        debt_profile_key=under(document.debt.debt_profile_key),
        declared_completeness=document.debt.completeness,
        declared_semantic_consistency=document.debt.semantic_consistency,
    )

    return ComposedDeployment(
        fabric=fabric,
        control_plane=control_plane,
        resolver=resolver,
        declaration=declaration,
        # The perspective the in-process transport serves under, from the same
        # document, so the two transports answer for one principal in one role.
        default_perspective=document.perspective,
        door=door,
        environment=environment,
    )
