# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Open one typed Context Product on the paved road and answer questions of it.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
covenant, no citation, no passage, no entitlement and no number. Everything
specific to this deployment lives in ``deployment.py``, ``acquisition.py`` and
``projection.py`` beside it, and in the two documents beside those.

[ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's three verbs to its two documents — ONE call
answer  ask the opened product one governed question — ONE call
======  ====================================================================

**What is NOT here, and their absence is the point.** The frozen specimen
(`examples/cp-13-covenant-cross-reference/produce.py`) booted a registry,
minted a connection, derived the effective request by hand, ran the ingest
loop, built the resolver from fourteen keywords — and handed Π the acquisition
result through a closure the graph never carried, with the two debt factors
measured off that same object. As of `D-IMPL-343` the first six are the
SDK's, and the last is this tree's reason to exist: **Π and the debt reading
read the governed view** (`CP-SPEC-013C` §0.1).

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
from ccf.erasure import ErasureTrust

HERE = Path(__file__).parent


# --8<-- [start:boot]
# A NAMED function rather than a lambda, and the name is load-bearing.
# `D-IMPL-137`'s demand — that the Control Plane can see no second operator
# set was authored — is a property something has to be able to READ off this
# tree. A named factory whose ONLY operator source is the `required` tuple the
# SDK hands it makes that provable.
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return projection.CovenantCrossReferenceProjection(
        plan_id=deployment.plan_id(request.subject),
        # The SDK's set, passed straight through. This deployment authors no
        # operator set at all.
        required=required,
        # From the EFFECTIVE request the SDK hands this factory, never from a
        # value this spine resolved for itself — and nothing from the read: the
        # seed Π declares is the anchor's own claim in the view.
        resolve_depth=int(request.parameters[deployment.RESOLVE_DEPTH]),
    )


def _withholds_no_subject() -> bool:
    """``plan_factory``'s positive declaration (`D-IMPL-378` E2 (ii) (d)).

    ``NonWithholdingPlanFactoryProtocol``: ``ccf_config.yaml`` affirms
    ``subject_withholding: never``, and the SDK builds this class only over a
    factory that says so. True of what ``plan_factory`` builds:
    ``projection.CovenantCrossReferenceProjection.invoke`` returns ``ProjectionOutput``
    with a plan id and a payload and never the withheld signal, for any
    subject or principal.
    """
    return True


#: A NAMED ``def`` carries the declaration as an attribute: the structural form
#: of the companion protocol for a function.
plan_factory.withholds_no_subject = _withholds_no_subject  # type: ignore[attr-defined]


def product(
    scratch: Path, *, environ: Mapping[str, str] | None = None, config_root: Path = HERE
) -> OpenedProduct:
    """Bind this deployment's three verbs and its declared gate to its two documents.

    `ccf_config.yaml` declares the product and every binding; `ccf_environment
    .yaml` names where the three source stores and the door's credential are
    read from.

    ``config_root`` is the DEPLOYMENT — this tree, unless a deployer (a test)
    opens a copy of its two documents declaring a different demonstration serve
    instant, or none (`tests/examples/demonstration_deployment.py`; amended
    2026-10-11). Nothing on a question can move the serve clock.
    """
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=config_root,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.citation_gate,
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
    disclosed and addressed — a debt above the caller's tolerance, a citation
    the declared gate would not serve. A refusal is not an exception. What
    still RAISES is the acquisition's own contract, unchanged by the road: an
    unknown evidence node and an unentitled scope (`CXRC-G10`, `CXRC-G14`).
    """
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
