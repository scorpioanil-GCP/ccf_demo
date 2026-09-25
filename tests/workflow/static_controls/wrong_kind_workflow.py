"""STATIC NEGATIVE CONTROL — D-IMPL-353 §1.4/§1.5(b) at the workflow surface.

This file is meant to FAIL mypy. It is excluded from the package mypy run
and checked on its own by ``tests/workflow/test_workflow_static.py``, which
asserts the EXACT diagnostics below. **No suppression comment, no cast.**

Three wrong-kind calls against the REAL signatures (not stand-ins) and one
handler that reaches a handle with no capability at all (§1.4: "a handler
with no capability does not type-check").

If this file ever type-checks clean, the static tooth is gone from the
engine and the factory.
"""

from __future__ import annotations

from ccf.authz.capability import ArtifactRead, Authorized, Execute, Resume
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.workflow.engine import WorkflowEngine


async def an_execute_capability_reaches_resume(
    engine: WorkflowEngine, workflow: Workflow, execute: Authorized[Execute]
) -> None:
    await engine.resume(execute, workflow, execution_id="e", decision="d")  # WRONG-KIND-1


async def a_resume_capability_reaches_execute(
    engine: WorkflowEngine, workflow: Workflow, resume: Authorized[Resume]
) -> None:
    await engine.execute(resume, workflow, execution_id="e")  # WRONG-KIND-2


def a_read_capability_reaches_the_factory(
    factory: WorkflowFactory, read: Authorized[ArtifactRead]
) -> None:
    factory.construct(read, definition_version="1.0.0")  # WRONG-KIND-3


def a_handler_with_no_capability(factory: WorkflowFactory, version: str) -> None:
    factory.construct(definition_version=version)  # NO-CAPABILITY-1
