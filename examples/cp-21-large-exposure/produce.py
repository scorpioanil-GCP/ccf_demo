"""The paved producer road for `risk.large-exposure` — two regions.

`boot` opens the declared product once; `answer` asks one governed question.
Everything else is the SDK's (`D-IMPL-343`). This module names no domain value.

`large_exposure_question` IS THE DEPLOYMENT'S OWN SEAM, and it does exactly one
thing the SDK does not: it refuses a NONCANONICAL PROPOSAL MAGNITUDE before a
request exists (`Q1`, carried from rung 24). See the docstring there for what
that is and — just as importantly — what it is not.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import acquisition
import deployment
import projection
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.products.resolver import ResolverOutcome
from ccf.projection.plan import Perspective, ProjectionPlan

HERE = Path(__file__).parent


# --8<-- [start:boot]
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.LargeExposureProjection(
        plan_id=deployment.plan_id(),
        required=required,
        as_of=str(request.parameters[deployment.AS_OF]),
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    return open_product(
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.large_exposure_gate,
        environ=environ,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def large_exposure_question(
    opened: OpenedProduct, *, anchor: str, asked_at: datetime, intent: str, freshness: str,
    **parameters: Any,
) -> ProductRequest:
    """One anchor's question, with the proposal checked at the deployment's seam.

    THE PROPOSAL'S MAGNITUDES ARE INTEGERS IN CANONICAL UNITS — whole dollars,
    because a commitment is a whole-dollar amount. A fractional form is REFUSED
    here, never coerced.

    WHAT THIS SEAM IS AND IS NOT. The SDK refuses a float anyway —
    `canonical_bytes` rejects it as not bit-stable, which is correct and is the
    real backstop — but it does so by RAISING during request canonicalization,
    before the request contract is ever consulted. So the refusal is loud and
    nothing is coerced, yet it is not a governed refusal carrying a replay
    reference. That is the `D-IMPL-304` residual shape, recorded as `LEX-F-02`
    and NOT repaired here. What this seam adds is a diagnostic an adopter can
    act on — naming the parameter and its canonical unit — rather than a bare
    encoding error.

    There is no member-list canonicalization on this rung: CP-21's population
    is DERIVED from the graph at the ledger point, not supplied by the caller,
    so rung 23's set-canonicalization seam has nothing to canonicalize here.
    """
    proposal = parameters.get(deployment.PROPOSAL)
    if isinstance(proposal, Mapping):
        acquisition.refuse_noncanonical(proposal)
    return opened.question(subject=anchor, asked_at=asked_at, intent=intent,
                           freshness=freshness, parameters=parameters)


def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
