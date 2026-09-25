"""The ``workflow`` noun — invocations/status/resume (D-IMPL-23; ORCH-01).

**The tenant is the grant's (``SEC-002``).** ``GET /execution`` used to take
``tenant`` as a query parameter and build its state key from it, so a
recognized bearer read any tenant's workflow state by typing its name. The
parameter is **deleted** and the key's tenant half comes from the verified
grant; ``execution_id`` stays, and is also this route's authorization
resource.

Invocation goes through the WorkflowFactory handle path and nothing else:
the route resolves the pinned definition through the factory (ORCH-01 "via
the Task Factory", held at the HTTP boundary too) and delegates to the
injected :class:`~ccf_runtime.workflow.engine.WorkflowEngine`. Suspension
is a typed 200 response — a suspended workflow is an expected outcome, not
an error — and the engine's typed refusals map to 409 with the refusal
body. Broken wiring raises and surfaces as an opaque 500 (T-07-26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Union

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ccf.authz.capability import Execute, Resume, WorkflowStatusRead
from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneMissing
from ccf.workflow.factory import Workflow, WorkflowConstructionError
from ccf_runtime.authz.refusals import (
    ACTION_WORKFLOW_INVOKE,
    ACTION_WORKFLOW_RESUME,
    ACTION_WORKFLOW_STATUS_READ,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.grants import authorized_from_request
from ccf_runtime.http_api.routes import _required_handle, refusal_response
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowExceptionRouted,
    WorkflowOutcome,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

__ccf_mode__ = "algorithmic"

__all__ = ["WorkflowInvocationRequest", "WorkflowResumptionRequest", "build_router"]

_Progressed = Union[WorkflowSuspended, WorkflowCompleted, WorkflowExceptionRouted]


class WorkflowInvocationRequest(CCFContract):
    """One invocation: the pinned definition reference and an execution id."""

    definition_key: str
    definition_version: str
    execution_id: str


class WorkflowResumptionRequest(CCFContract):
    """One resumption: the same pinned reference plus the human's decision."""

    definition_key: str
    definition_version: str
    execution_id: str
    decision: str


def build_router(deps: ApiDependencies) -> APIRouter:
    """The workflow router over the injected factory and engine."""
    router = APIRouter()

    def _construct(definition_key: str, definition_version: str) -> Workflow:
        # Narrowed once per body (D-IMPL-126 item (3)): a deployment that
        # exposes no workflow invocation wired no factory, and this route
        # refuses with a typed 503 naming the field rather than dereferencing
        # `None`. `_construct` is the shared body both invoking routes reach
        # the factory through, so one call here covers both.
        #
        # JOIN (§1.2/§1.3, Lane ENGINE): `factory.construct(authorized,
        # definition_version)` — the key becomes `authorized.resource` and the
        # factory checks the artifact's tenant against `authorized.tenant`
        # once. Left on today's signature.
        factory = _required_handle(
            deps.workflow_factory,
            field="workflow_factory",
            routes="workflow invocation or resumption",
        )
        try:
            return factory.construct(
                definition_key=definition_key,
                definition_version=definition_version,
            )
        except ControlPlaneMissing as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        except WorkflowConstructionError as bad:
            raise HTTPException(status_code=422, detail=str(bad)) from bad

    def _respond(outcome: WorkflowOutcome) -> WorkflowOutcome | JSONResponse:
        if isinstance(outcome, WorkflowResumeRefused):
            return refusal_response(outcome, status_code=409)
        return outcome

    @router.post(
        "/invocations",
        response_model=_Progressed,
        summary="Workflow invoke (D-IMPL-23)",
    )
    @authorizes(
        ACTION_WORKFLOW_INVOKE,
        resource=ResourceBinding.body("definition_key"),
    )
    async def invoke(
        body: WorkflowInvocationRequest, request: Request
    ) -> WorkflowOutcome | JSONResponse:
        # D-IMPL-353 §1.4: the capability for THIS action, or nothing.
        authorized = authorized_from_request(request, kind=Execute)
        assert authorized.resource == body.definition_key
        workflow = _construct(body.definition_key, body.definition_version)
        # Narrowed after the construction, not before: the refusals are read in
        # the order the route needs the handles, so an operator wiring a
        # workflow door is told about the factory before the engine.
        engine = _required_handle(
            deps.workflow_engine,
            field="workflow_engine",
            routes="workflow invocation",
        )
        # JOIN (§1.2, Lane ENGINE): `engine.execute(authorized, workflow, *,
        # execution_id=...)`. Left on today's signature.
        outcome = await engine.execute(workflow, execution_id=body.execution_id)
        return _respond(outcome)

    @router.post(
        "/resumptions",
        response_model=_Progressed,
        summary="Workflow resume (D-IMPL-23)",
    )
    # Its own action id, never `workflow.invoke`: resumption is the verb that
    # carries a human decision past an approval gate, and a deployment that
    # granted *start a workflow* has not thereby granted *approve one*.
    @authorizes(
        ACTION_WORKFLOW_RESUME,
        resource=ResourceBinding.body("definition_key"),
    )
    async def resume(
        body: WorkflowResumptionRequest, request: Request
    ) -> WorkflowOutcome | JSONResponse:
        # D-IMPL-353 §1.4: `Authorized[Resume]`, and never `Authorized[Execute]`
        # — starting a workflow is not approving one.
        authorized = authorized_from_request(request, kind=Resume)
        assert authorized.resource == body.definition_key
        workflow = _construct(body.definition_key, body.definition_version)
        engine = _required_handle(
            deps.workflow_engine,
            field="workflow_engine",
            routes="workflow resumption",
        )
        # JOIN (§1.2, Lane ENGINE): `engine.resume(authorized, workflow, *,
        # execution_id=..., decision=...)`. Left on today's signature.
        outcome = await engine.resume(
            workflow,
            execution_id=body.execution_id,
            decision=body.decision,
        )
        return _respond(outcome)

    @router.get(
        "/execution",
        response_model=WorkflowStateRecord,
        summary="Workflow status (D-IMPL-23)",
    )
    @authorizes(
        ACTION_WORKFLOW_STATUS_READ,
        resource=ResourceBinding.query("execution_id"),
    )
    def execution(execution_id: str, request: Request) -> WorkflowStateRecord:
        # `SEC-002` / D-IMPL-353 §1.3: the tenant half of the state key is the
        # CAPABILITY's — selected by the gate from the verified grant's set.
        # There is no `tenant` parameter to supply one, which is why reading
        # another tenant's execution is unrepresentable rather than refused.
        tenant = authorized_from_request(request, kind=WorkflowStatusRead).tenant
        record = deps.control_plane.state_store.get(
            WORKFLOW_STATE, f"{tenant}/{execution_id}"
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"no execution exists under {tenant}/{execution_id}",
            )
        if not isinstance(record, WorkflowStateRecord):
            raise TypeError(
                "the Control Plane state store returned a foreign record"
                " under a workflow state key (D-IMPL-18/27)"
            )
        return record

    return router
