"""P2 — the tenant on the write IS the capability's tenant (D-IMPL-353 §1.3).

Fable's reproduction, as tests that assert INEXPRESSIBILITY rather than a
403. Written first in fork shape (commit 5b621a9d) and watched fail by
succeeding: a ``WorkflowStateRecord(tenant='acme-bank', status='suspended')``
under ``acme-bank/exec-p2`` with acme-bank's gate event pending, all from a
capability minted for ``beta-bank``. This version asserts the closed shape:

* **P2-1** a capability for tenant B on tenant A's workflow key constructs
  NO handle — the factory's one tenant comparison refuses it, typed, naming
  both tenants — so nothing exists under A and nothing sits on A's queue;
* **P2-2** a genuine ``Authorized[Execute]`` handed to ``resume`` dies at
  ``verify`` (wrong kind) before the state store is read;
* **P2-3** a genuine ``Execute`` capability for definition X cannot run
  definition Y (wrong resource), and the factory has no parameter through
  which Y could even be named;
* the engine files under the capability's tenant, never the artifact's — a
  handle constructed under A's capability and executed under B's files
  under B (this is the test the "derive the key from
  ``workflow.definition.tenant`` again" sabotage reddens);
* fabrication controls at all three handles; and the structural control that
  no module in the engine or the driver tree reads ``definition.tenant``.

Every capability here is minted through the real ``mint`` over an allowed
decision (:mod:`tests.workflow.capabilities`); none is constructed.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest

import ccf_runtime.orchestration.adk.driver as adk_driver
import ccf_runtime.orchestration.claude_agent.driver as claude_driver
import ccf_runtime.orchestration.langgraph.driver as langgraph_driver
import ccf_runtime.orchestration.reference as reference_driver
import ccf_runtime.workflow.engine as engine_module
from ccf.authz.capability import (
    Authorized,
    CapabilityBypassError,
    Execute,
    Resume,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf.workflow.factory import (
    Workflow,
    WorkflowFactory,
    WorkflowTenantMismatchError,
)
from ccf_runtime.workflow.engine import WorkflowSuspended
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

from tests.workflow.capabilities import (
    execute_as,
    execute_capability,
    resume_as,
    resume_capability,
)
from tests.workflow.test_engine import (  # noqa: F401 — `registry` is the fixture
    _covenant,
    _engine,
    _refresh,
    _workflow_definition_document,
    registry,
)

ACME = "acme-bank"
BETA = "beta-bank"
ACME_KEY = "acme-bank/workflows/covenant-review"


def _register_acme_covenant(registry: ControlPlaneRegistry) -> str:
    """Register acme-bank's covenant-review definition under ACME_KEY."""
    definition = _workflow_definition_document(
        "workflows/covenant_review_workflow.yaml"
    )
    assert definition.tenant == ACME
    version = registry.register_versioned(ACME_KEY, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return version


def _keys_under(registry: ControlPlaneRegistry, tenant: str) -> list[str]:
    """Every workflow-state key filed under ``tenant`` — the population."""
    return [
        key
        for key, _ in registry.state_store.items(WORKFLOW_STATE)
        if key.startswith(f"{tenant}/")
    ]


def _workflow_audit_events(registry: ControlPlaneRegistry) -> list[Any]:
    return [
        event
        for event in registry.audit_log.events()
        if str(event.action).startswith("workflow_")
    ]


# --- P2-1: the cross-tenant invocation cannot be constructed -----------------


def test_p2_a_capability_for_tenant_b_constructs_no_handle_on_tenant_as_key(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The reproduction, closed. B's authorizer allowed ``workflow.invoke``
    on A's key; the factory refuses at construction — one typed refusal
    naming both tenants — so there is no handle to execute, and therefore
    nothing under A and nothing on A's queue. Not a 403: an execution
    filed under A on B's authority is not a state this surface can reach."""
    engine, transport, bindings = _engine(registry, tmp_path)
    version = _register_acme_covenant(registry)
    authorized = execute_capability(tenant=BETA, resource=ACME_KEY)
    assert authorized.tenant == BETA and authorized.resource == ACME_KEY

    with pytest.raises(WorkflowTenantMismatchError) as refused:
        WorkflowFactory(control_plane=registry).construct(
            authorized, definition_version=version
        )
    message = str(refused.value)
    assert BETA in message and ACME in message and ACME_KEY in message

    # Nothing exists under A (or under B): no state, no HITL event, no node
    # ran, no workflow audit event — the population is the whole store.
    assert _keys_under(registry, ACME) == []
    assert _keys_under(registry, BETA) == []
    assert transport.pending(tenant=ACME) == ()
    assert transport.pending(tenant=BETA) == ()
    assert bindings.ran == []
    assert _workflow_audit_events(registry) == []
    del engine


def test_p2_the_same_capability_for_tenant_a_constructs_and_files_under_a(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The positive control for P2-1: the identical decision minted for A
    constructs, executes and files under A — so the refusal above is the
    tenant, not the key, the version or the fixture."""
    engine, transport, _ = _engine(registry, tmp_path)
    version = _register_acme_covenant(registry)
    authorized = execute_capability(tenant=ACME, resource=ACME_KEY)
    workflow = WorkflowFactory(control_plane=registry).construct(
        authorized, definition_version=version
    )
    assert workflow.definition_key == ACME_KEY
    outcome = asyncio.run(engine.execute(authorized, workflow, execution_id="exec-p2"))
    assert isinstance(outcome, WorkflowSuspended)
    assert outcome.tenant == ACME
    assert _keys_under(registry, ACME) == [f"{ACME}/exec-p2"]
    assert len(transport.pending(tenant=ACME)) == 1


# --- P2-2: an Execute capability handed to resume dies at verify -------------


def test_p2_an_execute_capability_handed_to_resume_dies_at_verify(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Wrong kind. *Start a workflow* is not *carry a decision past its
    gate* (§1.5). The refusal is raised by ``verify`` before the state store
    is read: the suspended record is untouched and no ``workflow_resumed``
    audit event — not even a refusal — is appended."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(
        engine.execute(execute_as(workflow), workflow, execution_id="exec-1")
    )
    assert isinstance(suspended, WorkflowSuspended)
    events_before = len(registry.audit_log.events())

    genuine_execute = execute_as(workflow)
    with pytest.raises(CapabilityBypassError, match="kind"):
        asyncio.run(
            engine.resume(
                cast(Authorized[Resume], genuine_execute),
                workflow,
                execution_id="exec-1",
                decision="approved",
            )
        )
    record = registry.state_store.get(WORKFLOW_STATE, f"{ACME}/exec-1")
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
    assert len(transport.pending(tenant=ACME)) == 1
    assert len(registry.audit_log.events()) == events_before


def test_a_resume_capability_cannot_start_an_execution(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The mirror of P2-2: ``Resume`` is not ``Execute`` either."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _refresh(registry)
    with pytest.raises(CapabilityBypassError, match="kind"):
        asyncio.run(
            engine.execute(
                cast(Authorized[Execute], resume_as(workflow)),
                workflow,
                execution_id="exec-1",
            )
        )
    assert _keys_under(registry, ACME) == []
    assert transport.pending(tenant=ACME) == ()


# --- P2-3: a capability for definition X cannot run definition Y -------------


def test_p2_a_capability_for_definition_x_cannot_run_definition_y(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Wrong resource, right kind and right tenant. The engine binds the
    capability to the handle's own key (§1.5f), so an ``Execute`` minted for
    the covenant-review key does not run the certificate-refresh handle."""
    engine, transport, bindings = _engine(registry, tmp_path)
    covenant = _covenant(registry)
    refresh = _refresh(registry)
    assert covenant.definition_key != refresh.definition_key
    for_covenant = execute_as(covenant)
    with pytest.raises(CapabilityBypassError, match="resource"):
        asyncio.run(engine.execute(for_covenant, refresh, execution_id="exec-xy"))
    assert _keys_under(registry, ACME) == []
    assert transport.pending(tenant=ACME) == ()
    assert bindings.ran == []


def test_p2_the_factory_has_no_parameter_through_which_y_could_be_named(
    registry: ControlPlaneRegistry,
) -> None:
    """The factory half of P2-3: the key IS ``authorized.resource``. There
    is no ``definition_key`` parameter, so "construct Y under X's
    capability" is not a call that can be written."""
    parameters = inspect.signature(WorkflowFactory.construct).parameters
    assert "definition_key" not in parameters
    assert list(parameters) == ["self", "authorized", "definition_version"]
    version = _register_acme_covenant(registry)
    authorized = execute_capability(tenant=ACME, resource=ACME_KEY)
    with pytest.raises(TypeError):
        WorkflowFactory(control_plane=registry).construct(  # type: ignore[call-arg]
            authorized,
            definition_key="acme-bank/workflows/certificate-refresh",
            definition_version=version,
        )
    handle = WorkflowFactory(control_plane=registry).construct(
        authorized, definition_version=version
    )
    assert handle.definition_key == authorized.resource


# --- the tenant is the capability's, not the artifact's ----------------------


def test_the_execution_is_filed_under_the_capabilitys_tenant_not_the_artifacts(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """§1.3 verbatim: the engine receives ``authorized`` for tenant X and
    files under X. Here a handle constructed under A's capability is run
    under B's capability for the same key — an in-process divergence the
    served path never produces, and exactly the case that distinguishes
    "the key is derived from the capability" from "the key is derived from
    the artifact". Nothing lands under A; everything lands under B."""
    engine, transport, _ = _engine(registry, tmp_path)
    version = _register_acme_covenant(registry)
    as_acme = execute_capability(tenant=ACME, resource=ACME_KEY)
    workflow = WorkflowFactory(control_plane=registry).construct(
        as_acme, definition_version=version
    )
    assert workflow.definition.tenant == ACME  # the artifact still says A
    as_beta = execute_capability(tenant=BETA, resource=ACME_KEY)

    outcome = asyncio.run(engine.execute(as_beta, workflow, execution_id="exec-div"))

    assert isinstance(outcome, WorkflowSuspended)
    assert outcome.tenant == BETA
    assert _keys_under(registry, ACME) == []
    assert _keys_under(registry, BETA) == [f"{BETA}/exec-div"]
    record = registry.state_store.get(WORKFLOW_STATE, f"{BETA}/exec-div")
    assert isinstance(record, WorkflowStateRecord)
    assert record.tenant == BETA
    assert transport.pending(tenant=ACME) == ()
    (pending,) = transport.pending(tenant=BETA)
    assert pending.tenant == BETA
    assert pending.workflow_state_ref == f"{BETA}/exec-div"
    # And B's resume finds it where B's capability says it is.
    assert transport.remove(tenant=BETA, event_key=outcome.event_key) is not None


# --- fabrication controls at all three handles --------------------------------


def _fabrications() -> list[tuple[str, object]]:
    skipped_init = Authorized.__new__(Authorized)
    return [
        ("mock", Mock(spec=Authorized)),
        ("object", object()),
        ("subclass-skipping-init", skipped_init),
        ("none", None),
    ]


@pytest.mark.parametrize("label,fake", _fabrications(), ids=lambda x: x if isinstance(x, str) else "")
def test_a_fabricated_capability_dies_at_every_handle(
    registry: ControlPlaneRegistry, tmp_path: Path, label: str, fake: object
) -> None:
    engine, transport, bindings = _engine(registry, tmp_path)
    version = _register_acme_covenant(registry)
    workflow = _covenant(registry)
    with pytest.raises(CapabilityBypassError):
        WorkflowFactory(control_plane=registry).construct(
            cast(Authorized[Execute], fake), definition_version=version
        )
    with pytest.raises(CapabilityBypassError):
        asyncio.run(
            engine.execute(cast(Authorized[Execute], fake), workflow, execution_id="exec-f")
        )
    with pytest.raises(CapabilityBypassError):
        asyncio.run(
            engine.resume(
                cast(Authorized[Resume], fake),
                workflow,
                execution_id="exec-f",
                decision="approved",
            )
        )
    assert _keys_under(registry, ACME) == [], label
    assert transport.pending(tenant=ACME) == ()
    assert bindings.ran == []


def test_a_retargeted_capability_confers_no_authority_here(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """§1.5g at this surface: a genuine capability for A whose ``tenant`` is
    forced to B by ``object.__setattr__`` is neither A's nor B's — it dies at
    ``verify`` on construct and on execute, and nothing is filed anywhere."""
    engine, transport, _ = _engine(registry, tmp_path)
    version = _register_acme_covenant(registry)
    genuine = execute_capability(tenant=ACME, resource=ACME_KEY)
    workflow = WorkflowFactory(control_plane=registry).construct(
        genuine, definition_version=version
    )
    retargeted = execute_capability(tenant=ACME, resource=ACME_KEY)
    with pytest.raises(CapabilityBypassError):
        retargeted.tenant = BETA  # type: ignore[misc]
    object.__setattr__(retargeted, "tenant", BETA)
    with pytest.raises(CapabilityBypassError):
        WorkflowFactory(control_plane=registry).construct(
            retargeted, definition_version=version
        )
    with pytest.raises(CapabilityBypassError):
        asyncio.run(engine.execute(retargeted, workflow, execution_id="exec-rt"))
    assert _keys_under(registry, ACME) == []
    assert _keys_under(registry, BETA) == []
    assert transport.pending(tenant=ACME) == () and transport.pending(tenant=BETA) == ()


# --- structural: nothing downstream of the factory reads the artifact's tenant


@pytest.mark.parametrize(
    "module,keys_position",
    [
        (engine_module, True),
        (reference_driver, False),  # a pass-through: holds no position at all
        (langgraph_driver, True),
        (adk_driver, True),
        (claude_driver, True),
    ],
    ids=lambda m: m.__name__ if hasattr(m, "__name__") else "",
)
def test_no_module_downstream_of_the_factory_reads_the_artifacts_tenant(
    module: Any, keys_position: bool
) -> None:
    """§1.3: "after that there is no tenant anywhere in the engine except the
    capability's." Held structurally over the engine and every driver leg:
    the source never names ``definition.tenant``, and every module that keys
    position by tenant keys it by ``authorized.tenant``. The factory is the
    one module allowed to read the artifact's tenant — for its single
    comparison and for the URI the artifact states about itself."""
    source = inspect.getsource(module)
    assert "definition.tenant" not in source
    assert "authorized" in source
    if keys_position:
        assert "authorized.tenant" in source


def test_the_factory_compares_the_tenant_exactly_once() -> None:
    """One comparison, at construction (§1.3). Counted in the source so a
    second one — or none — is a red test rather than a code-review remark."""
    import ccf.workflow.factory as factory_module

    source = inspect.getsource(factory_module)
    assert source.count("definition.tenant != authorized.tenant") == 1


def test_the_handle_carries_the_key_it_was_constructed_from(
    registry: ControlPlaneRegistry,
) -> None:
    workflow: Workflow = _covenant(registry)
    assert workflow.definition_key == ACME_KEY
    assert workflow.definition_key == execute_as(workflow).resource
