"""Open the co-lender composite on the paved road and answer questions of it.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. [ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's verbs and its child seam to its two documents
answer  ask the opened composite one governed question — ONE call
======  ====================================================================

**What is NOT here.** No MCP client, no producer registration, no admission
gate construction, no ledger, no record readback. One producer — a SECOND
ORGANIZATION's — is registered from `ccf_config.yaml`, its answer is held to
that registration, and the child row is recorded, by the SDK.

**What IS here that should not have to be**: the `build_children=` keyword.
Every other composite on this ladder declares its chain and hands the road a
`questions=` mapping. This one cannot, because `include_federated` is a
request parameter and only the child-resolution seam can honor one. The cost
is `deployment.FederatedChildren` and is measured as `CLD-F-04`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

import acquisition
import deployment
import projection
from ccf.products.composite import ChildContractView
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.products.resolver import ResolverOutcome
from ccf.projection.plan import Perspective, ProjectionPlan
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import ErasureTrust

HERE = Path(__file__).parent


# --8<-- [start:boot]
def _tenant() -> str:
    """This deployment's own tenant, read from the one document that declares it.

    The projection compares an admitted child's tenant against it to derive
    the claim's provenance (`CLD-G15`), so the value is READ rather than
    restated here — a second statement of a tenant is a second authority.
    """
    document = yaml.safe_load((HERE / "ccf_config.yaml").read_text(encoding="utf-8"))
    return str(document["tenant_id"])


class CoLenderPlanFactory:
    """A NAMED plan factory — `D-IMPL-137` row C, and the name is load-bearing.

    Declares :meth:`build_with_children`, through which the ADMITTED child's
    contract reaches the plan. The SDK calls that overload when a composition
    reached no refusal, and the plain call otherwise; a lambda could declare
    neither, which is why this is a class.
    """

    def _plan(
        self, *, required: tuple[str, ...], request: ProductRequest,
        children: ChildContractView | None,
    ) -> ProjectionPlan:
        policy = acquisition.federation_policy()
        return projection.CoLenderPositionPlan(
            plan_id=deployment.plan_id(str(request.parameters[deployment.FACILITY])),
            # The SDK's set, passed straight through. This deployment authors
            # no operator set at all.
            required=required,
            request=request,
            children=children,
            tenant_id=_tenant(),
            latency_bound_ms=int(policy["declared_latency_bound_ms"]),
        )

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
        return self._plan(required=required, request=request, children=None)

    def build_with_children(
        self, *, required: tuple[str, ...], request: ProductRequest,
        children: ChildContractView,
    ) -> ProjectionPlan:
        return self._plan(required=required, request=request, children=children)


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    """Bind this deployment's verbs and its child seam to its two documents.

    ONE `FederatedChildren` per opened product — never a shared module object,
    so two opened composites cannot see each other's sources or each other's
    dispatch count.
    """
    children = deployment.FederatedChildren()
    opened = open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=CoLenderPlanFactory(),
        assess=deployment.assess,
        build_children=children.factory,
        environ=environ,
    )
    # The envelope check reads OUR OWN stores; the settings it reads are the
    # ones the road resolved from the environment document at open — bound
    # here, once, never resolved a second time.
    children.bind(opened.sources)
    return opened
# --8<-- [end:boot]


# --8<-- [start:answer]
def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    """Answer one syndicate question end to end, against ``scratch``.

    Returns the governed outcome AS DATA: a ``ServedProduct`` whose replay
    reference proves the record was appended, or a ``RefusalEnvelope`` recorded,
    disclosed and addressed — an ask outside the negotiated envelope, a peer
    that refused its own position, a facility we do not hold. A refusal is not
    an exception.
    """
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
