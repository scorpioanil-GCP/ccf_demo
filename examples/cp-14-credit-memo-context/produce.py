"""Open the credit-memo composite on the paved road and answer questions of it.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it** beyond the names
`deployment.py` declares. [ADAPT] nothing.

**Two regions, and no others** (`D-IMPL-343`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    bind the deployment's verbs and its ONE question mapping to its two
        documents — ONE call
answer  ask the opened composite one governed question — ONE call
======  ====================================================================

**What is NOT here, and their absence is the whole point of this slice.** No
skill registry, no producer registration, no MCP client, no catalog entry, no
grant, no agent definition, no admission gate, no child resolver, no ledger, no
record readback. Five producers are registered, five skills and grants derived,
five questions asked, five answers held to their registrations and admitted or
refused, and five child rows recorded — from the declarations in
`ccf_config.yaml` and the mapping in `deployment.py`, by the SDK.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import deployment
import projection
from ccf.products.composite import ChildContractView
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.products.resolver import ResolverOutcome
from ccf.projection.plan import Perspective, ProjectionPlan
from ccf.controlplane.registry import ControlPlaneRegistry

HERE = Path(__file__).parent


# --8<-- [start:boot]
class MemoPlanFactory:
    """A NAMED factory whose only operator source is the `required` tuple the SDK hands it.

    Implements both seams (`D-IMPL-339`): the plain call, and
    `build_with_children`, through which the ADMITTED children's contracts reach
    the parent's Π — the one path by which a child's content reaches the memo.
    """

    def _plan(self, *, required: tuple[str, ...], request: ProductRequest, children: Mapping[str, object] | None) -> ProjectionPlan:
        parameters = request.parameters
        return projection.CreditMemoContextProjection(
            plan_id=deployment.plan_id(request.subject),
            required=required,
            subject=request.subject,
            memo_type=str(parameters[deployment.MEMO_TYPE]),
            decision_instant=str(parameters[deployment.AS_OF]),
            facility_id=str(parameters[deployment.FACILITY_ID]),
            children=children,  # type: ignore[arg-type]
        )

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
        return self._plan(required=required, request=request, children=None)

    def build_with_children(
        self, *, required: tuple[str, ...], request: ProductRequest, children: ChildContractView
    ) -> ProjectionPlan:
        return self._plan(required=required, request=request, children=children)


def product(scratch: Path, *, environ: Mapping[str, str] | None = None) -> OpenedProduct:
    """Bind this deployment's verbs and its question mapping to its two documents.

    `ccf_config.yaml` declares the product, what it requires, who may provide
    each class, the skills that ask and the agent that holds their grants;
    `ccf_environment.yaml` names where the roster store and the five producers'
    endpoints and credentials are read from. The SDK refuses, at open and by
    name, anything the documents disagree on, and registers every producer.
    """
    # ONE mapping per opened product — never a shared module object, so two
    # opened products cannot see each other's sources (close review, 2026-09-17).
    questions = deployment.MemoQuestions()
    opened = open_product(
        hitl_policy_key="hitl_policy",
        control_plane=ControlPlaneRegistry(),
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=MemoPlanFactory(),
        assess=deployment.assess,
        questions=questions,
        environ=environ,
    )
    # The question mapping determines the covenant question from the
    # deployment's own sources; the settings it reads are the ones the road
    # resolved from the environment document at open — bound here, once,
    # never resolved a second time (`CP14-F-34`).
    questions.bind(opened.sources)
    return opened
# --8<-- [end:boot]


# --8<-- [start:answer]
def assemble_and_serve(
    *, asked: ProductRequest, scratch: Path, perspective: Perspective | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolverOutcome:
    """Answer one memo question end to end, against ``scratch`` as writable space.

    Returns the governed outcome AS DATA: a ``ServedProduct`` whose replay
    reference proves the record was appended, or a ``RefusalEnvelope`` recorded,
    disclosed and addressed — a required child withheld by its own producer, a
    producer that could not be reached, an obligor not on the roster, a debt
    above the memo's tolerance. A refusal is not an exception.
    """
    with product(scratch, environ=environ) as opened:
        return opened.answer(asked, perspective=perspective)
# --8<-- [end:answer]
