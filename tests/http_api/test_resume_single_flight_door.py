"""Two concurrent resumptions of one suspension, through the served door (D-IMPL-377).

RED FIRST. ``POST /workflow/resumptions`` is an ``async`` handler on the
event loop (``runtime/ccf_runtime/http_api/routes/workflow.py::build_router``).
Two requests for one approved suspension therefore interleave wherever the
engine awaits, and the engine awaits the downstream node. Measured on
2026-10-07 against 34a1f6bf: both requests answered 200, the node ran twice,
and two ``workflow_resumed`` rows carried the one approver.

The deployment is the suite's own governed application
(``tests/http_api/conftest.py::Fabric`` and
``tests/http_api/gate_fixtures.py::build_gate_app``), driven in process over
httpx's ASGI transport exactly as the rest of this package drives it. It makes
two composition-root choices, and nothing else differs:

* the SEC-006 two-gate release workflow is registered beside the covenant
  workflow. The covenant gate routes straight to a terminal, so it has no
  downstream node that could run twice. The typed policy's eligible set holds
  the door's approver client and not its starter;
* the engine's node binding awaits once in the downstream step, as any real
  I/O-bound skill does
  (``tests/workflow/test_resume_single_flight.py::AwaitingBindings``).

The red test asserts the node runs once, exactly one attributed row exists,
and the second request is refused BY THE CLAIM: HTTP 409, the same status and
the same refusal body the sequential control below returns, identified by the
claim's own phrase.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

from ccf.agents.definitions import TASK_DEFINITION
from ccf.controlplane.artifacts import parse_artifact
from ccf_runtime.workflow.engine import WorkflowEngine
from http_api.composition_authority import register_versioned_at_composition
from http_api.conftest import Fabric, _register_workflow
from http_api.gate_fixtures import (
    APPROVER_CLIENT_ID,
    TOKEN_APPROVER,
    TOKEN_EVERYTHING,
    build_gate_app,
)
from tests.hitl.sec006_harness import register_typed_policy
from tests.workflow import test_engine as eh
from tests.workflow.test_resume_single_flight import (
    DOWNSTREAM,
    IN_FLIGHT,
    NEXT_GATE,
    AwaitingBindings,
)

TWO_GATE_WORKFLOW = "workflows/two_gate_release_workflow.yaml"
TWO_GATE_TASK = "tasks/two_gate_release_task.yaml"
POLICY_KEY = "acme-bank/approval-policy/sec006-officers"
EXECUTION = "door-single-flight"
STARTER = {"Authorization": f"Bearer {TOKEN_EVERYTHING}"}
APPROVER = {"Authorization": f"Bearer {TOKEN_APPROVER}"}


def door(tmp_path: Path) -> tuple[Any, Fabric, AwaitingBindings, str, str]:
    """The governed application over a fabric carrying the two-gate workflow."""
    fabric_root = tmp_path / "fabric"
    gate_root = tmp_path / "gate"
    fabric_root.mkdir()
    gate_root.mkdir()
    fabric = Fabric(fabric_root)
    register_typed_policy(
        fabric.registry, POLICY_KEY, eligible=frozenset({APPROVER_CLIENT_ID})
    )
    task = parse_artifact(eh._load(TWO_GATE_TASK)["task_definition"], TASK_DEFINITION)
    register_versioned_at_composition(
        fabric.registry,
        eh._load(TWO_GATE_WORKFLOW)["keys"]["task_definition"],
        task,
        TASK_DEFINITION,
    )
    key, version = _register_workflow(fabric.registry, TWO_GATE_WORKFLOW)
    bindings = AwaitingBindings()
    # The fixture's own engine arguments, with the awaiting node binding.
    fabric.engine = WorkflowEngine(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        hitl_transport=fabric.hitl,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=fabric.clock,
        debt_binding=eh._PermissiveDebt(),
    )
    return build_gate_app(fabric, gate_root).app, fabric, bindings, key, version


def resumptions(
    app: Any, fabric: Fabric, key: str, version: str, *, concurrent: bool
) -> tuple[str, list[httpx.Response]]:
    """Invoke, approve ONCE at the action door, then resume twice."""

    async def flow() -> tuple[str, list[httpx.Response]]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            invoked = await client.post(
                "/workflow/invocations",
                json={
                    "definition_key": key,
                    "definition_version": version,
                    "execution_id": EXECUTION,
                },
                headers=STARTER,
            )
            assert invoked.status_code == 200, invoked.text
            body = invoked.json()
            assert body["gate"] == "first-approval", body
            pending = next(
                event
                for event in fabric.hitl.pending(tenant=body["tenant"])
                if event.event_key == body["event_key"]
            )
            acted = await client.post(
                "/hitl/actions",
                json={
                    "event_key": body["event_key"],
                    "action": "approve",
                    "product_content_hash": pending.product_content_hash,
                    "annotation": None,
                },
                headers=APPROVER,
            )
            assert acted.status_code == 200, acted.text
            resume = {
                "definition_key": key,
                "definition_version": version,
                "execution_id": EXECUTION,
                "decision": DOWNSTREAM,
            }

            async def one() -> httpx.Response:
                return await client.post(
                    "/workflow/resumptions", json=resume, headers=STARTER
                )

            if concurrent:
                answered = list(await asyncio.gather(one(), one()))
            else:
                answered = [await one(), await one()]
            return body["tenant"], answered

    return asyncio.run(flow())


def attributed_resumptions(fabric: Fabric, state_key: str) -> list[str | None]:
    return [
        event.actor
        for event in fabric.registry.audit_log.events()
        if event.key == state_key
        and event.action == "workflow_resumed"
        and event.resolved
        and event.actor is not None
    ]


def test_two_concurrent_resumptions_at_the_door_pass_the_gate_once(
    tmp_path: Path,
) -> None:
    """Two concurrent ``POST /workflow/resumptions`` for one approval: the node
    runs once, one attributed row, and the second is a 409 from the claim."""
    app, fabric, bindings, key, version = door(tmp_path)
    tenant, answered = resumptions(app, fabric, key, version, concurrent=True)
    runs = bindings.ran.count(f"skill:{DOWNSTREAM}")
    assert runs == 1, f"the downstream node ran {runs} times on one approval"
    attributed = attributed_resumptions(fabric, f"{tenant}/{EXECUTION}")
    assert attributed == [APPROVER_CLIENT_ID], (
        f"attributed workflow_resumed rows on one approval: {attributed}"
    )
    statuses = sorted(response.status_code for response in answered)
    assert statuses == [200, 409], [r.text for r in answered]
    passed = next(r for r in answered if r.status_code == 200)
    refused = next(r for r in answered if r.status_code == 409)
    assert passed.json()["gate"] == NEXT_GATE
    assert IN_FLIGHT in refused.json()["reason"], refused.json()
    # The sequential refusal's body: the refusal contract and nothing else.
    assert set(refused.json()) == {"tenant", "execution_id", "reason"}


def test_sequential_resumptions_at_the_door_refuse_the_second_for_its_authority(
    tmp_path: Path,
) -> None:
    """The control: one after the other, the second request reads the next
    gate and is refused because no approval for THAT suspension exists. It
    gets the same 409 and the same body shape, and the claim never answers."""
    app, fabric, bindings, key, version = door(tmp_path)
    tenant, answered = resumptions(app, fabric, key, version, concurrent=False)
    assert [r.status_code for r in answered] == [200, 409], [r.text for r in answered]
    assert answered[0].json()["gate"] == NEXT_GATE
    reason = answered[1].json()["reason"]
    assert "no approval for this suspension" in reason
    assert IN_FLIGHT not in reason
    assert set(answered[1].json()) == {"tenant", "execution_id", "reason"}
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1
    assert attributed_resumptions(fabric, f"{tenant}/{EXECUTION}") == [
        APPROVER_CLIENT_ID
    ]
