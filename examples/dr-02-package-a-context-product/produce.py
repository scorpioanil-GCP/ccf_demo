"""Open the product, ask it one question, serve or refuse.

The spine. It restates no value either document carries and it holds no domain
knowledge — the vocabulary is `deployment.py`'s and the payload shape is
`projection.py`'s.
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
from ccf.erasure import ErasureTrust

HERE = Path(__file__).parent

__all__ = ["assemble_and_serve", "plan_factory", "product"]


def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    """A NAMED factory, never a lambda — the SDK's predicate has to see it.

    The `required` set is the SDK's and is handed straight through: this
    deployment authors no operator set of its own, which is what qualifies it
    for the `D-IMPL-141` SDK-supplied exemption.
    """
    values = request.parameters
    return projection.PackagedMemoProjection(
        plan_id=deployment.plan_id(str(values[deployment.FACILITY])),
        required=required,
        anchor=str(values[deployment.FACILITY]),
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    """Open the product: one call binds this deployment's callables to its documents.

    `gate=` is `deployment.packaging_gate` and the class declares its identity,
    which are both-or-neither: without the declaration the SDK has no identity
    to stamp on a refusal the gate produced, and replay could not say which
    gate refused.
    """
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.packaging_gate,
        # §7.10.4's Mode 2 footprint. Without this the payload would carry the
        # packaging pins and replay dimension 3 would read `no-packaging` on
        # every field — measured, and recorded as `PKG-F-08`.
        packaging_trace=deployment.packaging_trace,
        environ=environ,
    )


def assemble_and_serve(
    *,
    asked: ProductRequest,
    scratch: Path,
    perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    """Answer one memo question end to end.

    Returns the governed outcome AS DATA: a `ServedProduct` whose replay
    reference proves the record was appended, or a `RefusalEnvelope` recorded,
    disclosed and addressed — an upstream that refused, a packager that would
    not render, or prose the smoothing gate would not stand behind. A refusal
    is not an exception.
    """
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
