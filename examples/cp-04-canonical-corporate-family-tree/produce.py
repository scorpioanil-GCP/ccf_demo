"""Open one typed Context Product on the paved road and answer questions of it.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
predicate, no table, no column, no entity class, no LEI and no number.
Everything specific to this deployment lives in ``deployment.py``,
``acquisition.py`` and ``projection.py`` beside it, and in the two documents
beside those.

[ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's three verbs to its two documents — ONE call
answer  ask the opened product one governed question — ONE call
======  ====================================================================

**What is NOT here, and their absence is the point.** No registry, no boot
call, no effective-depth re-derivation, no ingest loop, no fourteen-keyword
builder call, no store, no record readback, no ``try/finally`` — and still no
``gate``, ``record`` or ``serve`` region. The canonical spine this replaces
(`D-IMPL-314`'s three regions) carried the first six by hand; as of
`D-IMPL-343` they are the SDK's, and this tree is the second producer to say
so (CP-14 Gate 2 slice 2), after cp-03-canonical.

**The two depths are two authorities and never one number.** The caller's
``max_depth`` is request state: it folds through the class default, the
declared domain and the graph leg's technical capability, and the EFFECTIVE
value that survives is what acquisition walks at — recorded in replay
dimension 2 as the request-contract binding (`D-IMPL-310`). The traversal
operator's ``depth_limit`` is the BACKEND's ceiling, declared once in
``ccf_config.yaml`` and handed to the road as the technical capability.

This file asserts nothing about the domain and prints nothing. What a run
prints is ``run.py``, which carries no marker region.
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
# A NAMED function rather than a lambda, and the name is load-bearing.
# `D-IMPL-137`'s demand — that the Control Plane can see no second operator
# set was authored — is a property something has to be able to READ off this
# tree. A named factory whose ONLY operator source is the `required` tuple the
# SDK hands it makes that provable.
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.CorporateFamilyProjection(
        plan_id=deployment.plan_id(request.subject),
        # The SDK's set, passed straight through. This deployment authors no
        # operator set at all.
        required=required,
        declared=projection.declaration(),
        # From the EFFECTIVE request the SDK hands this factory, never from a
        # value this spine resolved for itself.
        max_depth=int(request.parameters[deployment.MAX_DEPTH]),
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    """Bind this deployment's three verbs to its two documents.

    `ccf_config.yaml` declares the product and every binding; `ccf_environment
    .yaml` names where the two source stores and the door's credential are
    read from. The graph leg's technical ceiling is the one number the
    operator declaration carries, handed to the road as a capability so a
    depth above it is refused by name with authority `technical`.
    """
    return open_product(
        hitl_policy_key="hitl_policy",
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        capabilities=(deployment.traversal_capability(),),
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
    disclosed and addressed — a depth above the ceiling, a family the principal
    may not walk, a debt above the caller's tolerance. A refusal is not an
    exception: a bad question is a bad question rather than a broken deployment.
    """
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
