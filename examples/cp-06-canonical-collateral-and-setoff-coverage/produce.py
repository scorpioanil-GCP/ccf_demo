"""Assemble one typed Context Product and serve it, end to end.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
predicate, no table, no column, no asset class, no haircut and no number.
Everything specific to this deployment lives in ``deployment.py``,
``acquisition.py`` and ``projection.py`` beside it, and in the two documents
beside those.

[ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's four callables to its two documents — ONE call
answer  ask the opened product one governed question — ONE call
======  ====================================================================

**What is NOT here, and their absence is the point.** No registry, no boot
call, no effective-request derivation, no ingest loop, no fifteen-keyword
builder call, no store, no record readback, no ``try/finally`` — and still no
``gate``, ``record`` or ``serve`` region and no call to ``run_gates``,
``build_replay_record`` or ``serve`` anywhere in this tree. The door, the graph
view, both operators, Π, the three L6 gates, the product's own declared gate,
the five-dimension replay record, the query pins and the delivery are ONE
object the SDK owns. The frozen specimen this succeeds
(``examples/cp-06-collateral-and-setoff-coverage``) composed the resolver by
hand and wrote its own door; the difference between the two trees is the
measurement `CP-SPEC-006C` §G.3 records.

**Π receives the effective request and nothing from the side.** The facility's
commitment is fabric state — on the facility node, read off the governed view
(`CSCC-G14`) — which is why the plan factory below builds Π from the request
alone.

This file asserts nothing about the domain and prints nothing. What a run
prints is ``run.py``, which carries no marker region, so no printed line is
published-snippet surface.
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


# A NAMED function rather than a lambda, and the name is load-bearing:
# `D-IMPL-137`'s demand — that the Control Plane can see no second operator set
# was authored — is a property something has to be able to READ off this tree.
# Its only operator source is the `required` tuple the SDK hands it.
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    values = request.parameters
    return projection.CollateralCoverageProjection(
        plan_id=deployment.plan_id(request.subject),
        required=required,
        declared=projection.declaration(),
        anchor=str(values[deployment.FACILITY]),
        apply_haircuts=bool(values[deployment.APPLY_HAIRCUTS]),
        shared_collateral=str(values[deployment.SHARED_COLLATERAL]),
        jurisdiction_basis=str(values[deployment.JURISDICTION_BASIS]),
    )


# --8<-- [start:boot]
def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    """Open the product: one call binds this deployment's callables to its two documents.

    `ccf_config.yaml` declares the product and every binding; `ccf_environment
    .yaml` names where the two source stores and the door's credential are
    read from. Every value a question needs comes from one of the two — the
    spine restates none — and the SDK refuses, at open and by name, anything
    the documents disagree on. ``environ`` is the caller's environment to read
    those names from; ``None`` reads the process's.
    """
    return open_product(
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.coverage_gate,
        environ=environ,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None
) -> ResolverOutcome:
    """Answer one question against ``scratch`` as this run's own fabric.

    Returns the governed outcome AS DATA: a ``ServedProduct`` whose replay
    reference proves the record was appended, or a ``RefusalEnvelope``
    recorded, disclosed and addressed — a wrong intent, an out-of-domain
    parameter, a scope the caller does not hold, a facility the view does not
    know the size of, an over-allocated asset. A refusal is not an exception.
    """
    with product(scratch) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
