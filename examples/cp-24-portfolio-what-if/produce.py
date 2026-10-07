"""The paved producer road for `cib.portfolio-what-if` — two regions.

`boot` opens the declared product once; `answer` asks one governed question.
Everything else is the SDK's (`D-IMPL-343`). This module names no domain value.

`book_question` IS THE CANONICALIZATION SEAM (`Q2`, ruled 2026-09-21). It is
the one place a member list becomes a request parameter, and it canonicalizes
there — before the effective request exists — because CP-23 knows its
membership is semantically a set. Two orderings of one membership therefore
build the same request and hash to the same address (`WIF-G05`), while a
different membership still hashes differently (`WIF-G06`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import ErasureTrust

HERE = Path(__file__).parent


# --8<-- [start:boot]
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.WhatIfProjection(
        plan_id=deployment.plan_id(),
        required=required,
        as_of=str(request.parameters[deployment.AS_OF]),
    )


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.what_if_gate,
        environ=environ,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def book_question(
    opened: OpenedProduct, *, book: str, asked_at: datetime, intent: str, freshness: str,
    members: Sequence[str] | None = None, **parameters: Any,
) -> ProductRequest:
    """One book's question, canonicalized at the deployment's own seam.

    TWO THINGS HAPPEN HERE AND NOWHERE ELSE:

    - the member set is CANONICALIZED, because membership is semantically a
      set (rung 23's `Q2`, reused unchanged);
    - the scenario's magnitudes are checked to be INTEGERS IN CANONICAL UNITS
      before a request is built (`Q1`).

    ON THE SECOND, AND WHAT IT IS AND IS NOT. The SDK refuses a float anyway —
    `canonical_bytes` rejects it as not bit-stable, which is correct and is the
    backstop — but it does so by RAISING during request canonicalization,
    before the request contract is ever consulted. So the refusal is loud and
    nothing is coerced, yet it is not a governed refusal carrying a replay
    reference. That is the `D-IMPL-304` residual shape and is recorded as
    `WIF-F-02`, not repaired here. What this seam adds is a diagnostic an
    adopter can act on — naming the parameter and the canonical unit — rather
    than a bare encoding error.
    """
    scenario = parameters.get(deployment.SCENARIO)
    if isinstance(scenario, Mapping):
        acquisition.refuse_noncanonical(scenario)
    canonical = acquisition.canonical_members(members)
    if canonical:
        parameters[deployment.MEMBERS] = list(canonical)
    return opened.question(subject=book, asked_at=asked_at, intent=intent,
                           freshness=freshness, parameters=parameters)


def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
