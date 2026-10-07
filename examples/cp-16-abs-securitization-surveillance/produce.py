"""The paved producer road for `cib.abs-surveillance` — two regions.

`boot` opens the declared product once; `answer` asks one governed question.
Everything else — the effective request, the per-question fabric, the operator
plan, the three L6 gates, the declared gate, the replay record, the door — is
the SDK's (`D-IMPL-343`). This module names no domain value.
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
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.ABSSurveillanceProjection(
        plan_id=deployment.plan_id(),
        required=required,
        as_of=str(request.parameters[deployment.AS_OF]),
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    return open_product(
        hitl_policy_key="hitl_policy",
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.surveillance_gate,
        environ=environ,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
