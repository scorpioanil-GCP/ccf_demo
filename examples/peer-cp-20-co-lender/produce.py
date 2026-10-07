"""Open the co-lender's Context Product on the paved road and answer questions of it.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
table, no column, no LEI, no facility and no number. [ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's three verbs to its two documents — ONE call
answer  ask the opened product one governed question — ONE call
======  ====================================================================

This is the SECOND organization's spine. It is byte-for-byte the same shape as
the consumer's beside it and as every other producer on the ladder — which is
the point of `CLD-G01`: federation across an organizational boundary is not a
different mechanism, it is the same mechanism under a different tenant.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import deployment
import projection
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.products.resolver import ResolverOutcome
from ccf.projection.plan import Perspective, ProjectionPlan
from ccf.controlplane.registry import ControlPlaneRegistry

HERE = Path(__file__).parent


# --8<-- [start:boot]
# A NAMED function rather than a lambda, and the name is load-bearing
# (`D-IMPL-137` row C): the Control Plane must be able to READ off this tree
# that no second operator set was authored. A named factory whose only
# operator source is the `required` tuple the SDK hands it makes that provable.
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.CoLenderPositionProjection(
        plan_id=deployment.plan_id(
            str(request.parameters[deployment.FACILITY]),
            str(request.parameters[deployment.COUNTERPARTY]),
        ),
        # The SDK's set, passed straight through.
        required=required,
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    """Bind this deployment's three verbs to its two documents."""
    return open_product(
        hitl_policy_key="hitl_policy",
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        environ=environ,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    """Answer one question end to end, against ``scratch`` as writable space.

    Returns the governed outcome AS DATA: a ``ServedProduct`` whose replay
    reference proves the record was appended, or a ``RefusalEnvelope`` recorded,
    disclosed and addressed — a position with no attestation record behind it,
    a counterparty this fabric holds nothing for. A refusal is not an
    exception: a position this fabric will not assert is a governed answer.
    """
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
