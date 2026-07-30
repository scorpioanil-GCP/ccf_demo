"""The ``workflow`` noun — invocations/status/resume (D-IMPL-23; ORCH-01).

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

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneMissing
from ccf.workflow.factory import Workflow, WorkflowConstructionError
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import refusal_response
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
        try:
            return deps.workflow_factory.construct(
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
    async def invoke(
        request: WorkflowInvocationRequest,
    ) -> WorkflowOutcome | JSONResponse:
        workflow = _construct(
            request.definition_key, request.definition_version
        )
        outcome = await deps.workflow_engine.execute(
            workflow, execution_id=request.execution_id
        )
        return _respond(outcome)

    @router.post(
        "/resumptions",
        response_model=_Progressed,
        summary="Workflow resume (D-IMPL-23)",
    )
    async def resume(
        request: WorkflowResumptionRequest,
    ) -> WorkflowOutcome | JSONResponse:
        workflow = _construct(
            request.definition_key, request.definition_version
        )
        outcome = await deps.workflow_engine.resume(
            workflow,
            execution_id=request.execution_id,
            decision=request.decision,
        )
        return _respond(outcome)

    @router.get(
        "/execution",
        response_model=WorkflowStateRecord,
        summary="Workflow status (D-IMPL-23)",
    )
    def execution(tenant: str, execution_id: str) -> WorkflowStateRecord:
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
