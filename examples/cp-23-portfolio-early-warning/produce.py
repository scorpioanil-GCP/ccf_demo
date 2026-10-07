"""The paved producer road for `cib.portfolio-early-warning` — two regions.

`boot` opens the declared product once; `answer` asks one governed question.
Everything else is the SDK's (`D-IMPL-343`). This module names no domain value.

`book_question` IS THE CANONICALIZATION SEAM (`Q2`, ruled 2026-09-21). It is
the one place a member list becomes a request parameter, and it canonicalizes
there — before the effective request exists — because CP-23 knows its
membership is semantically a set. Two orderings of one membership therefore
build the same request and hash to the same address (`PEW-G05`), while a
different membership still hashes differently (`PEW-G06`).
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
    return projection.PortfolioProjection(
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
        gate=deployment.portfolio_gate,
        environ=environ,
    )
# --8<-- [end:boot]


# --8<-- [start:answer]
def book_question(
    opened: OpenedProduct, *, book: str, asked_at: datetime, intent: str, freshness: str,
    members: Sequence[str] | None = None, **parameters: Any,
) -> ProductRequest:
    """One book's question, with its membership CANONICALIZED first (`Q2`)."""
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
