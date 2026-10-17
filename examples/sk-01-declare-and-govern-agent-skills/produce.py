# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Open the facility collateral brief on the paved road — and with it, its governed agent.

**This file is the fabric's half.** [MECHANISM] every line here is a CCF call
an adopter must make. [ADAPT] nothing.

**What opening does for the skill chain.** ``open_product`` reads
``ccf_config.yaml``'s five skill-chain declarations — ``policy.skill_governance``,
``producers``, ``skills``, ``agent`` and ``grants`` — registers the regime, the
agent definition and the derived skill catalog entry on the Control Plane the
caller hands in, and REQUESTS each declared grant through the grant ledger:
tier 1 (the skill's required scopes against the regime's permitted scopes),
tier 2 (the regime's approval rule), and the audit log. A refused grant raises
:class:`~ccf.products.product.DeclaredGrantRefused` HERE, by name, before
anything is composed; nothing is opened and nothing can be asked.

**What is NOT here.** No skill catalog, no grant ledger, no grant, no agent
definition, no producer registration, no MCP client, no admission gate, no
child resolver. Those exist because the documents declared them.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import deployment
import projection
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import ErasureTrust
from ccf.products.composite import ChildContractView
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.projection.plan import ProjectionPlan

HERE = Path(__file__).parent

#: The over-reach deployment: this tree's two documents with only the skill block
#: changed (version 1.1.0, one scope the regime does not permit).
OVER_REACH = HERE / "variants" / "over-reach"


# --8<-- [start:boot]
class BriefPlanFactory:
    """A NAMED factory whose only operator source is the ``required`` tuple the SDK hands it.

    Both seams (`D-IMPL-339`): the plain call, and ``build_with_children``,
    through which the ADMITTED child's contract reaches Π.
    """

    def _plan(self, *, required: tuple[str, ...], request: ProductRequest, children: ChildContractView | None) -> ProjectionPlan:
        return projection.FacilityCollateralBriefProjection(
            plan_id=deployment.plan_id(request.subject),
            required=required,
            facility_id=str(request.parameters[deployment.QUESTION["brief"]["facility_parameter"]]),
            children=children,  # type: ignore[arg-type]
        )

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
        return self._plan(required=required, request=request, children=None)

    def build_with_children(
        self, *, required: tuple[str, ...], request: ProductRequest, children: ChildContractView
    ) -> ProjectionPlan:
        return self._plan(required=required, request=request, children=children)

    def withholds_no_subject(self) -> bool:
        """The positive declaration a ``never`` class needs (`D-IMPL-378` E2 (ii) (d)).

        True of everything this factory builds: both seams build
        ``projection.FacilityCollateralBriefProjection``, whose ``invoke``
        never raises the withheld signal.
        """
        return True


def product(
    scratch: Path,
    *,
    control_plane: ControlPlaneRegistry,
    config_root: Path = HERE,
    environ: Mapping[str, str] | None = None,
    read_sources: bool = True,
) -> OpenedProduct:
    """Open the deployment at ``config_root`` into ``control_plane``.

    The caller owns ``control_plane`` so it can read that registry's audit log
    afterwards — including after a refused open, when there is no opened
    product to ask. ``config_root`` is this tree, or ``OVER_REACH``.
    ``read_sources=False`` opens to inspect only: no source setting is resolved
    and nothing can be asked, but every open-time check — the grant requests
    among them — still runs.
    """
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=control_plane,
        config_root=config_root,
        scratch=scratch,
        acquire=deployment.acquire,
        project=BriefPlanFactory(),
        assess=deployment.assess,
        questions=deployment.questions,
        environ=environ,
        read_sources=read_sources,
    )
# --8<-- [end:boot]
