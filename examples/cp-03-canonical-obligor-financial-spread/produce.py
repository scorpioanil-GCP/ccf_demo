"""Open one typed Context Product on the paved road and answer questions of it.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
table, no column, no tag, no ratio, no LEI and no number. Everything specific
to this deployment lives in ``deployment.py`` and ``acquisition.py`` beside it,
and in the two documents beside those.

[ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's three verbs to its two documents — ONE call
answer  ask the opened product one governed question — ONE call
======  ====================================================================

**What is NOT here, and their absence is the point.** No registry, no boot
call, no effective-request derivation, no ingest loop, no fifteen-keyword
builder call, no store, no record readback, no ``try/finally`` — and still no
``gate``, ``record`` or ``serve`` region and no call to ``run_gates``,
``build_replay_record`` or ``serve`` anywhere in this tree. The door, the graph
view, the operator, Π, the three L6 gates, the product's own declared gate, the
five-dimension replay record, the query pins and the delivery are ONE object
the SDK owns, and as of `D-IMPL-343` so are the boot, the effective request,
the ingest boundary, the replay binding and the recorder. What this file says
is which callables are this deployment's — and that is all a spine has to say.

This file asserts nothing about the domain and prints nothing. What a run
prints is ``run.py``, which carries no marker region, so no printed line is
published-snippet surface.
"""

from __future__ import annotations

from pathlib import Path

import deployment
import projection
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.products.resolver import ResolverOutcome
from ccf.projection.plan import Perspective, ProjectionPlan

HERE = Path(__file__).parent


# --8<-- [start:boot]
# A NAMED function rather than a lambda, and the name is load-bearing.
# `D-IMPL-137`'s demand — that the Control Plane can see no second operator
# set was authored — is a property something has to be able to READ off this
# tree. A named factory whose ONLY operator source is the `required` tuple the
# SDK hands it makes that provable.
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.FinancialSpreadProjection(
        plan_id=deployment.plan_id(request.subject),
        # The SDK's set, passed straight through. This deployment authors no
        # operator set at all.
        required=required,
        # From the EFFECTIVE request the SDK hands this factory, never from a
        # value this spine resolved for itself.
        subject=request.subject,
    )


def product(scratch: Path) -> OpenedProduct:
    """Bind this deployment's three verbs to its two documents.

    `ccf_config.yaml` declares the product and every binding; `ccf_environment
    .yaml` names where the source store and the door's credential are read
    from. Every value a question needs comes from one of the two — the spine
    restates none — and the SDK refuses, at open and by name, anything the
    documents disagree on.
    """
    return open_product(
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.freshness_window_gate,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None
) -> ResolverOutcome:
    """Answer one question end to end, against ``scratch`` as writable space.

    Returns the governed outcome AS DATA: a ``ServedProduct`` whose replay
    reference proves the record was appended, or a ``RefusalEnvelope`` recorded,
    disclosed and addressed — a wrong intent, an out-of-domain parameter, an
    obligor the principal may not see, a spread outside its declared window, a
    debt above the caller's tolerance. A refusal is not an exception: a bad
    question is a bad question rather than a broken deployment, and a verdict
    returned as a value cannot be swallowed by a bare ``except``.
    """
    with product(scratch) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
