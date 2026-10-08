"""The approval-gate limits, through the served doors (D-IMPL-377 close-out §4d).

RED FIRST, NOW THE ACCEPTANCE TESTS, like their in-process sibling
``tests/workflow/test_approval_gate_limits.py``, whose docstring states the
limits, Dave's rulings (*"Disclosure alone does not close them."*, and the
``D-IMPL-378`` fix) and how these tests assert: the hole's own end state
first, then the refusing mechanism by name. Here every human action and every
resumption travels the shipped HTTP doors (``POST /hitl/actions``, ``POST /workflow/resumptions``,
``POST /workflow/invocations``, ``GET /hitl/queue``), over the suite's own
governed application (``tests/http_api/conftest.py::Fabric`` and
``tests/http_api/gate_fixtures.py::build_gate_app``), driven in process over
httpx's ASGI transport exactly as the rest of this package drives it.

* **(a) Two processes, one durable store.** Two governed applications, each
  over its own fabric (its own Control Plane registry, engine and state-store
  object), share one backing state store and one HITL transport: the stand-ins
  for the database and the authority path that every replica of a deployment
  reaches. SIMULATED IN ONE PROCESS, and said so. Each fabric's registry is
  given its store after the fixture built it, because the fixture takes none;
  each original store is checked empty first, so nothing it held is lost.
* **(b) The outvoted rejection, at the action door.** Twice: once while the
  step after the gate is running (a deployment's step, holding on its own I/O,
  with no engine method touched), and once held inside the resumption's
  terminal commit at the storage layer, which is the shape the close-out
  words: the execution completes at the APPROVING terminal with both verdicts
  standing.
* **(b') The verdict after the passage, at the doors.** Sequential: the
  queue view still offers a passed gate as pending, and the action door
  records a late verdict on it as a verdict on an open gate.
* **(c) One execution id started twice, at the invocation door.**

A second eligible officer, ``credit-officer-7``, holds a token of its own
(``extra_grants``); the fixture's approver is ``credit-officer-11``. Both are
eligible under the covenant gate's policy
(``tests/fixtures/banking/approval_policies.yaml``) and under the typed policy
this module registers for the two-gate workflow, and neither is the starter.
Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ccf.agents.definitions import TASK_DEFINITION
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.state import InMemoryStateStore
from ccf_runtime.http_api.errors import ERROR_HITL_GATE_CLOSED
from ccf_runtime.workflow.engine import WorkflowEngine
from http_api.composition_authority import register_versioned_at_composition
from http_api.conftest import Fabric, _register_workflow
from http_api.gate_fixtures import (
    APPROVER_CLIENT_ID,
    SCOPE_EVERYTHING,
    TOKEN_APPROVER,
    TOKEN_EVERYTHING,
    build_gate_app,
    grant,
)
from tests.hitl.sec006_harness import register_typed_policy
from tests.workflow import test_engine as eh
from tests.workflow.test_approval_gate_limits import (
    ALREADY_EXISTS,
    APPROVING_TERMINAL,
    COVENANT_GATE,
    FIRST_GATE,
    RUNNING,
    START,
    SharedBackingStore,
    StandInRecords,
    terminal_write,
)
from tests.workflow.test_resume_single_flight import (
    DOWNSTREAM,
    HOLD_SECONDS,
    NEXT_GATE,
    Worker,
)

TWO_GATE_WORKFLOW = "workflows/two_gate_release_workflow.yaml"
TWO_GATE_TASK = "tasks/two_gate_release_task.yaml"
POLICY_KEY = "acme-bank/approval-policy/sec006-officers"
OFFICER_2_CLIENT_ID = "credit-officer-7"
TOKEN_OFFICER_2 = "gate-token-officer-2"
EXECUTION = "door-limits"
STARTER = {"Authorization": f"Bearer {TOKEN_EVERYTHING}"}
APPROVER = {"Authorization": f"Bearer {TOKEN_APPROVER}"}
OFFICER_2 = {"Authorization": f"Bearer {TOKEN_OFFICER_2}"}
#: The conflict refusal's own phrase
#: (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``).
CONFLICT = "carries conflicting human verdicts"


class HoldingBindings(eh._Bindings):
    """The suite's node-binding double, except that the FIRST call of ``held``
    waits until :attr:`release` is set, as any step doing real I/O waits on it.
    :attr:`entered` is set when that call begins. Later calls are the double's
    own. Both events are used on one event loop only."""

    def __init__(self, held: str) -> None:
        super().__init__()
        self._step = held
        self._taken = False
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name == self._step and not self._taken:
            self._taken = True
            self.entered.set()
            await asyncio.wait_for(self.release.wait(), HOLD_SECONDS)
        return await super().run_skill(tenant=tenant, step_name=step_name, ref=ref)


@dataclass
class Door:
    """One governed application over one fabric, and the workflow it serves."""

    app: Any
    fabric: Fabric
    key: str
    version: str


def fabric_at(root: Path, *, two_gate: bool) -> tuple[Fabric, str, str]:
    """The suite's fabric, with the two-gate release workflow registered beside
    the covenant workflow when ``two_gate`` (its first gate's approve route
    leads to a real node, the covenant gate's straight to a terminal)."""
    root.mkdir(parents=True)
    fabric = Fabric(root)
    if not two_gate:
        key, version = fabric.covenant
        return fabric, key, version
    register_typed_policy(
        fabric.registry,
        POLICY_KEY,
        eligible=frozenset({APPROVER_CLIENT_ID, OFFICER_2_CLIENT_ID}),
    )
    task = parse_artifact(eh._load(TWO_GATE_TASK)["task_definition"], TASK_DEFINITION)
    register_versioned_at_composition(
        fabric.registry,
        eh._load(TWO_GATE_WORKFLOW)["keys"]["task_definition"],
        task,
        TASK_DEFINITION,
    )
    key, version = _register_workflow(fabric.registry, TWO_GATE_WORKFLOW)
    return fabric, key, version


def give_state_store(fabric: Fabric, store: InMemoryStateStore) -> None:
    """The composition root's choice of state store, made after the fixture
    built its registry (the fixture takes none). The original store must be
    empty, so the swap loses nothing."""
    original = fabric.registry.state_store
    assert isinstance(original, InMemoryStateStore)
    assert not getattr(original, "_records"), "the fixture's store already holds state"
    fabric.registry._state_store = store


def open_door(fabric: Fabric, key: str, version: str, root: Path, bindings: eh._Bindings) -> Door:
    """Rebuild the fabric's engine with its own arguments and ``bindings``, then
    build the governed application over it, recognizing ``credit-officer-7``."""
    fabric.engine = WorkflowEngine(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        hitl_transport=fabric.hitl,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=fabric.clock,
        debt_binding=eh._PermissiveDebt(),
    )
    tenant = str(fabric.product_address.tenant)
    gate = build_gate_app(
        fabric,
        root,
        extra_grants={TOKEN_OFFICER_2: grant(OFFICER_2_CLIENT_ID, (SCOPE_EVERYTHING,), (tenant,))},
    )
    return Door(app=gate.app, fabric=fabric, key=key, version=version)


def client(door: Door) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=door.app), base_url="http://fabric.invalid"
    )


async def invoke(c: httpx.AsyncClient, door: Door) -> dict[str, Any]:
    response = await c.post(
        "/workflow/invocations",
        json={"definition_key": door.key, "definition_version": door.version, "execution_id": EXECUTION},
        headers=STARTER,
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def bound_hash(door: Door, tenant: str, event_key: str) -> str:
    return next(
        event.product_content_hash
        for event in door.fabric.hitl.pending(tenant=tenant)
        if event.event_key == event_key
    )


async def act(
    c: httpx.AsyncClient, *, event_key: str, bound: str, action: str, headers: dict[str, str]
) -> httpx.Response:
    return await c.post(
        "/hitl/actions",
        json={"event_key": event_key, "action": action, "product_content_hash": bound, "annotation": None},
        headers=headers,
    )


async def resume_at(c: httpx.AsyncClient, door: Door, decision: str) -> httpx.Response:
    return await c.post(
        "/workflow/resumptions",
        json={
            "definition_key": door.key,
            "definition_version": door.version,
            "execution_id": EXECUTION,
            "decision": decision,
        },
        headers=STARTER,
    )


def attributed(doors: tuple[Door, ...], state_key: str) -> list[str | None]:
    """Every attributed ``workflow_resumed`` row for the execution, across doors."""
    return [
        event.actor
        for door in doors
        for event in door.fabric.registry.audit_log.events()
        if event.key == state_key
        and event.action == "workflow_resumed"
        and event.resolved
        and event.actor is not None
    ]


def rejection_outcome(response: httpx.Response) -> tuple[bool, str]:
    """(standing, description) for officer-2's rejection at the action door.

    200: recorded; it stands unless recorded as ``missing`` (D-IMPL-366 H2:
    recorded unjudged, never authority). 409: refused by a state or
    concurrency mechanism, one way a fix can close the hole. 403: an identity,
    eligibility or attestation refusal, which means the control is broken, so
    it fails here rather than reading as a fix.
    """
    assert response.status_code != 403, (
        f"the control is broken: officer-2 was refused for who they are: {response.text}"
    )
    if response.status_code == 409:
        return False, f"refused 409: {response.json()}"
    assert response.status_code == 200, response.text
    state = response.json()["submission"]["event_state_at_submit"]
    return state != "missing", f"recorded with event_state_at_submit={state!r}"


# --- (a) two processes, one durable store ----------------------------------------


def two_doors(tmp_path: Path, bindings: eh._Bindings) -> tuple[Door, Door]:
    """Two governed applications over one durable state store and one transport."""
    records = StandInRecords()
    fabric_a, key_a, version_a = fabric_at(tmp_path / "fabric-a", two_gate=True)
    fabric_b, key_b, version_b = fabric_at(tmp_path / "fabric-b", two_gate=True)
    give_state_store(fabric_a, SharedBackingStore(records))
    give_state_store(fabric_b, SharedBackingStore(records))
    fabric_b.hitl = fabric_a.hitl  # the one authority path both replicas reach
    fabric_a.hitl.scope = "shared"  # type: ignore[misc]  # it declares itself shared (D-IMPL-378)
    door_a = open_door(fabric_a, key_a, version_a, tmp_path / "gate-a", bindings)
    door_b = open_door(fabric_b, key_b, version_b, tmp_path / "gate-b", bindings)
    assert door_a.fabric.registry.state_store is not door_b.fabric.registry.state_store
    return door_a, door_b


def test_two_processes_over_one_durable_store_spend_one_approval_once_at_the_doors(
    tmp_path: Path,
) -> None:
    """Limit (a), through the doors. ``credit-officer-11`` approves ONCE at
    process A's action door. Process A's resumption enters the step after the
    gate and waits there on its I/O; process B's resumption of the same
    execution runs to its end meanwhile; then A's step returns.

    Before ``D-IMPL-378`` both resumptions answered 200: the step after the
    gate ran twice on one approval, each process's audit log carried one
    attributed row, and the next gate held two pending events. The in-process control of the same
    shape, in one process, is
    ``tests/http_api/test_resume_single_flight_door.py::test_two_concurrent_resumptions_at_the_door_pass_the_gate_once``.
    """
    bindings = HoldingBindings(DOWNSTREAM)
    door_a, door_b = two_doors(tmp_path, bindings)

    async def flow() -> tuple[str, list[httpx.Response]]:
        async with client(door_a) as a, client(door_b) as b:
            body = await invoke(a, door_a)
            tenant, event_key = body["tenant"], body["event_key"]
            approved = await act(
                a, event_key=event_key, bound=bound_hash(door_a, tenant, event_key),
                action="approve", headers=APPROVER,
            )
            assert approved.status_code == 200, approved.text
            first = asyncio.create_task(resume_at(a, door_a, DOWNSTREAM))
            await asyncio.wait_for(bindings.entered.wait(), HOLD_SECONDS)
            # Mid-passage, the status door of the OTHER process answers
            # `running`: the passage committed before its step began.
            status = await b.get(
                "/workflow/execution", params={"execution_id": EXECUTION}, headers=STARTER
            )
            assert status.status_code == 200, status.text
            assert status.json()["status"] == "running", status.json()
            second = await resume_at(b, door_b, DOWNSTREAM)
            bindings.release.set()
            return tenant, [await first, second]

    tenant, answered = asyncio.run(flow())
    state_key = f"{tenant}/{EXECUTION}"
    runs = bindings.ran.count(f"skill:{DOWNSTREAM}")
    rows = attributed((door_a, door_b), state_key)
    next_gate = [
        event
        for event in door_a.fabric.hitl.pending(tenant=tenant)
        if event.event_key == f"{state_key}/{NEXT_GATE}"
    ]
    statuses = sorted(response.status_code for response in answered)
    problems = []
    if runs != 1:
        problems.append(f"the step after the gate ({DOWNSTREAM}) ran {runs} times")
    if rows != [APPROVER_CLIENT_ID]:
        problems.append(f"attributed workflow_resumed rows across the processes: {rows}")
    if len(next_gate) != 1:
        problems.append(f"pending events at {NEXT_GATE}: {len(next_gate)}")
    if statuses != [200, 409]:
        problems.append(f"resumption statuses: {statuses}")
    assert not problems, (
        "LIMIT (a) AT THE DOORS: ONE approval became more than one passage"
        " across two processes over one durable store: " + "; ".join(problems)
    )
    # D-IMPL-378, by name: B finds the passage A committed before its step —
    # still running — and is refused, typed, before it runs anything.
    refused = next(r for r in answered if r.status_code == 409)
    assert RUNNING in refused.json()["reason"], refused.json()


def test_either_door_alone_passes_the_gate_on_the_one_approval(tmp_path: Path) -> None:
    """Positive control for limit (a): process B's door ALONE, resuming on the
    approval recorded at process A's door, passes the gate once; so a refusal
    in the red test above can only come from the two resumptions meeting."""
    bindings = eh._Bindings()
    door_a, door_b = two_doors(tmp_path, bindings)

    async def flow() -> httpx.Response:
        async with client(door_a) as a, client(door_b) as b:
            body = await invoke(a, door_a)
            tenant, event_key = body["tenant"], body["event_key"]
            approved = await act(
                a, event_key=event_key, bound=bound_hash(door_a, tenant, event_key),
                action="approve", headers=APPROVER,
            )
            assert approved.status_code == 200, approved.text
            return await resume_at(b, door_b, DOWNSTREAM)

    resumed = asyncio.run(flow())
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["gate"] == NEXT_GATE
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1


# --- (b) the outvoted rejection, at the action door --------------------------------


def test_a_rejection_posted_while_the_step_after_the_gate_runs_is_not_outvoted(
    tmp_path: Path,
) -> None:
    """Limit (b), at its widest. ``credit-officer-11`` approves; the resumption
    passes the gate and enters the step after it, which waits on its own I/O;
    meanwhile ``credit-officer-7`` posts a rejection of the SAME suspension at
    the action door; the step returns.

    Before ``D-IMPL-378`` the action door answered 200 and recorded the
    rejection against a gate it still called pending, while the execution had
    left that gate on the approving route. Nothing in the engine was touched to open this window:
    it is as wide as the step after the gate takes, and that is the
    deployment's own code.
    """
    bindings = HoldingBindings(DOWNSTREAM)
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=True)
    door = open_door(fabric, key, version, tmp_path / "gate", bindings)

    async def flow() -> tuple[httpx.Response, httpx.Response]:
        async with client(door) as c:
            body = await invoke(c, door)
            tenant, event_key = body["tenant"], body["event_key"]
            bound = bound_hash(door, tenant, event_key)
            approved = await act(c, event_key=event_key, bound=bound, action="approve", headers=APPROVER)
            assert approved.status_code == 200, approved.text
            passage = asyncio.create_task(resume_at(c, door, DOWNSTREAM))
            await asyncio.wait_for(bindings.entered.wait(), HOLD_SECONDS)
            rejected = await act(c, event_key=event_key, bound=bound, action="reject", headers=OFFICER_2)
            bindings.release.set()
            return await passage, rejected

    resumed, rejected = asyncio.run(flow())
    standing, described = rejection_outcome(rejected)
    passed = resumed.status_code == 200 and resumed.json().get("gate") == NEXT_GATE
    assert not (passed and standing), (
        "LIMIT (b) AT THE ACTION DOOR: credit-officer-7's rejection was"
        f" {described} while the step after {FIRST_GATE!r} ran, and the"
        f" execution left that gate on the approving route (now at {NEXT_GATE!r}):"
        " the rejection was outvoted"
    )
    # D-IMPL-378, by name: the gate's closure refuses the verdict at the door.
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["detail"]["error_code"] == ERROR_HITL_GATE_CLOSED, rejected.json()


def test_the_same_rejection_posted_before_the_resumption_refuses_it(tmp_path: Path) -> None:
    """Positive control for limit (b), green before and after ``D-IMPL-378``:
    posted BEFORE the
    resumption, the same officer's rejection is admitted (200) and the
    resumption refuses for the conflict (409, the conflict refusal's phrase).
    So officer-2 is eligible and admitted, and only timing decides the
    outcome in the red tests."""
    bindings = eh._Bindings()
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=True)
    door = open_door(fabric, key, version, tmp_path / "gate", bindings)

    async def flow() -> tuple[httpx.Response, httpx.Response]:
        async with client(door) as c:
            body = await invoke(c, door)
            tenant, event_key = body["tenant"], body["event_key"]
            bound = bound_hash(door, tenant, event_key)
            approved = await act(c, event_key=event_key, bound=bound, action="approve", headers=APPROVER)
            assert approved.status_code == 200, approved.text
            rejected = await act(c, event_key=event_key, bound=bound, action="reject", headers=OFFICER_2)
            return rejected, await resume_at(c, door, DOWNSTREAM)

    rejected, resumed = asyncio.run(flow())
    assert rejected.status_code == 200, rejected.text
    assert resumed.status_code == 409, resumed.text
    assert CONFLICT in resumed.json()["reason"]
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 0


def test_a_rejection_posted_during_the_terminal_commit_is_not_outvoted_at_the_door(
    tmp_path: Path,
) -> None:
    """Limit (b), exactly as the close-out words it, at the doors. The covenant
    gate routes straight to its terminals. ``credit-officer-11`` approves; the
    resumption, posted on its own thread and event loop, decides and is held
    inside its terminal commit at the storage layer; ``credit-officer-7``
    posts a rejection at the action door from the main thread; the commit is
    released.

    Before ``D-IMPL-378`` both answered 200: the execution completed at the
    APPROVING terminal with both verdicts standing.
    """
    records = StandInRecords()
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=False)
    give_state_store(fabric, SharedBackingStore(records, scope="process"))
    door = open_door(fabric, key, version, tmp_path / "gate", eh._Bindings())

    async def start() -> tuple[str, str, str]:
        async with client(door) as c:
            body = await invoke(c, door)
            assert body["gate"] == COVENANT_GATE, body
            tenant, event_key = body["tenant"], body["event_key"]
            bound = bound_hash(door, tenant, event_key)
            approved = await act(c, event_key=event_key, bound=bound, action="approve", headers=APPROVER)
            assert approved.status_code == 200, approved.text
            return tenant, event_key, bound

    async def resume_once() -> httpx.Response:
        async with client(door) as c:
            return await resume_at(c, door, APPROVING_TERMINAL)

    async def reject(event_key: str, bound: str) -> httpx.Response:
        async with client(door) as c:
            return await act(c, event_key=event_key, bound=bound, action="reject", headers=OFFICER_2)

    tenant, event_key, bound = asyncio.run(start())
    records.arm_write(terminal_write)
    held = Worker(lambda: asyncio.run(resume_once())).start()
    try:
        assert records.held.wait(HOLD_SECONDS), "the resumption never reached its commit"
        rejected = asyncio.run(reject(event_key, bound))
    finally:
        records.release.set()
    resumed = held.join()

    standing, described = rejection_outcome(rejected)
    passed = (
        resumed.status_code == 200
        and resumed.json().get("terminal_state") == APPROVING_TERMINAL
    )
    assert not (passed and standing), (
        "LIMIT (b) AT THE DOORS: credit-officer-7's rejection was"
        f" {described} during the resumption's commit, and the execution"
        f" completed at {APPROVING_TERMINAL!r}: the rejection was outvoted"
    )
    # D-IMPL-378, by name: the gate's closure refuses the verdict at the door.
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["detail"]["error_code"] == ERROR_HITL_GATE_CLOSED, rejected.json()


# --- (b') the verdict after the passage, at the doors -----------------------------


def test_a_passed_gate_is_neither_offered_nor_accepted_as_pending_at_the_doors(
    tmp_path: Path,
) -> None:
    """Limit (b'), sequential. ``credit-officer-11`` approves; the execution
    resumes and completes at the approving terminal (200). Then the queue
    view is read, and ``credit-officer-7`` posts a rejection of the same
    suspension.

    Before ``D-IMPL-378`` ``GET /hitl/queue`` still listed the passed gate's
    event, and the action door answered 200 with ``event_pending: true`` and
    recorded the late rejection as a verdict on an open gate: a human was told
    the gate was open and that their rejection was submitted, after the
    execution it would have stopped had completed.
    """
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=False)
    door = open_door(fabric, key, version, tmp_path / "gate", eh._Bindings())

    async def flow() -> tuple[httpx.Response, list[dict[str, Any]], httpx.Response, str]:
        async with client(door) as c:
            body = await invoke(c, door)
            tenant, event_key = body["tenant"], body["event_key"]
            bound = bound_hash(door, tenant, event_key)
            approved = await act(c, event_key=event_key, bound=bound, action="approve", headers=APPROVER)
            assert approved.status_code == 200, approved.text
            resumed = await resume_at(c, door, APPROVING_TERMINAL)
            queue = await c.get("/hitl/queue", headers=OFFICER_2)
            assert queue.status_code == 200, queue.text
            rejected = await act(c, event_key=event_key, bound=bound, action="reject", headers=OFFICER_2)
            return resumed, queue.json(), rejected, event_key

    resumed, queue, rejected, event_key = asyncio.run(flow())
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["terminal_state"] == APPROVING_TERMINAL
    problems = []
    if any(event["event_key"] == event_key for event in queue):
        problems.append("GET /hitl/queue still lists the passed gate's event")
    standing, described = rejection_outcome(rejected)
    if standing:
        receipt = rejected.json()
        problems.append(
            f"the late rejection was {described}, and the receipt says"
            f" event_pending={receipt['event_pending']}"
        )
    assert not problems, "LIMIT (b') AT THE DOORS: " + "; ".join(problems)
    # D-IMPL-378, by name: the gate's closure refuses the verdict at the door.
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["detail"]["error_code"] == ERROR_HITL_GATE_CLOSED, rejected.json()
    # Nothing was recorded: the passed suspension holds the approval alone.
    verdicts = [
        s.action
        for s in fabric.hitl.submissions(tenant=str(fabric.product_address.tenant))
        if s.event_key == event_key
    ]
    assert verdicts == ["approve"], verdicts


# --- (c) one execution id started twice, at the invocation door --------------------


def test_two_invocations_of_one_execution_id_at_the_door_run_the_start_node_once(
    tmp_path: Path,
) -> None:
    """Limit (c), through the invocation door. The first invocation enters the
    start node and waits there on its I/O; a second invocation of the SAME
    execution id runs to its end meanwhile; then the first returns.

    Before ``D-IMPL-378`` both answered 200: the start node ran twice, and the
    first gate held two pending events, one bound to a state record the other
    overwrote."""
    bindings = HoldingBindings(START)
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=True)
    door = open_door(fabric, key, version, tmp_path / "gate", bindings)

    async def flow() -> list[httpx.Response]:
        async with client(door) as c:
            request = {"definition_key": key, "definition_version": version, "execution_id": EXECUTION}
            first = asyncio.create_task(c.post("/workflow/invocations", json=request, headers=STARTER))
            await asyncio.wait_for(bindings.entered.wait(), HOLD_SECONDS)
            second = await c.post("/workflow/invocations", json=request, headers=STARTER)
            bindings.release.set()
            return [await first, second]

    answered = asyncio.run(flow())
    tenant = str(fabric.product_address.tenant)
    runs = bindings.ran.count(f"skill:{START}")
    pending_first = [
        event
        for event in fabric.hitl.pending(tenant=tenant)
        if event.event_key == f"{tenant}/{EXECUTION}/{FIRST_GATE}"
    ]
    statuses = sorted(response.status_code for response in answered)
    problems = []
    if runs != 1:
        problems.append(f"the start node ran {runs} times")
    if len(pending_first) != 1:
        problems.append(f"pending events at {FIRST_GATE}: {len(pending_first)}")
    if statuses != [200, 409]:
        problems.append(f"invocation statuses: {statuses}")
    assert not problems, (
        "LIMIT (c) AT THE DOOR: one execution id was started twice: " + "; ".join(problems)
    )
    # D-IMPL-378, by name: the create-if-absent start.
    refused = next(r for r in answered if r.status_code == 409)
    assert ALREADY_EXISTS in refused.json()["reason"], refused.json()

