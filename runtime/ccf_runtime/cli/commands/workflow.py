"""The ``workflow`` noun — invoke/resume/status (D-IMPL-22; ORCH-01).

Invocation carries a pinned definition reference; the route constructs
through the WorkflowFactory handle path — the CLI never touches a raw
definition.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _invoke(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="POST",
            path="/workflow/invocations",
            json={
                "definition_key": args.definition_key,
                "definition_version": args.definition_version,
                "execution_id": args.execution_id,
            },
        ),
    )


def _resume(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="POST",
            path="/workflow/resumptions",
            json={
                "definition_key": args.definition_key,
                "definition_version": args.definition_version,
                "execution_id": args.execution_id,
                "decision": args.decision,
            },
        ),
    )


def _status(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path="/workflow/execution",
            params={"tenant": args.tenant, "execution_id": args.execution_id},
        ),
    )


def _pinned(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--definition-key", required=True)
    parser.add_argument("--definition-version", required=True)
    parser.add_argument("--execution-id", required=True)


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the workflow noun and its ruled verbs."""
    noun = subparsers.add_parser("workflow", help="workflow executions")
    verbs = noun.add_subparsers(dest="verb", required=True)

    invoke = verbs.add_parser("invoke", help="invoke a pinned definition")
    _pinned(invoke)
    invoke.set_defaults(build=_invoke)

    resume = verbs.add_parser("resume", help="resume with a decision")
    _pinned(resume)
    resume.add_argument("--decision", required=True)
    resume.set_defaults(build=_resume)

    status = verbs.add_parser("status", help="execution state record")
    status.add_argument("--tenant", required=True)
    status.add_argument("--execution-id", required=True)
    status.set_defaults(build=_status)
