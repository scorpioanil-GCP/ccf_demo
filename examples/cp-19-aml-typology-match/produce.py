"""The paved producer road for `compliance.aml-typology` — two regions, and the SDK owns the rest.

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

HERE = Path(__file__).parent


# --8<-- [start:boot]
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.AmlTypologyProjection(
        plan_id=deployment.plan_id(),
        # The SDK's set, passed straight through. This deployment authors no
        # operator set at all.
        required=required,
        # From the EFFECTIVE request the SDK hands this factory — the class's
        # relative default already resolved when the caller stated nothing.
        as_of=str(request.parameters[deployment.AS_OF]),
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    return open_product(
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.dispositions_gate,
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
