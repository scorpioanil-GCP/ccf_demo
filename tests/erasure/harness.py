"""Shared composition for the SEC-009 erasure controls (`D-IMPL-374` (4)).

Test vocabulary only (CINV-01): ``alice`` (the requester), ``bob`` (the
eligible approver), ``carol`` (the resumer) and the ``kyc-note`` class name no
real principal or deployment class.

Every ruled-but-absent name is imported INSIDE :func:`erasure` /
:func:`door_module` and reported as a MISSING CONTRACT, so on a tree without
the mechanism every control is red for that one named reason and nothing fails
at collection.
"""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.agents.definitions import TASK_DEFINITION
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, WriteKinds
from ccf.authz.capability import ArtifactWrite, Execute, Resume, mint
from ccf.authz.decision import AuthzDecision
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.workflow.engine import WorkflowEngine
from tests.http_api.composition_authority import WORKFLOW_TRACE_CLASS
from tests.composition import (
    composition_register,
    register_typed_at_composition,
    register_versioned_at_composition,
)
from tests.hitl.capabilities import submit_capability
from tests.hitl.sec006_harness import (
    door_submission,
    execute_as_principal,
    plain_hitl_plane,
    register_typed_policy,
    resume_as_principal,
)
from tests.erasure import signing
from tests.workflow import test_engine as eh

TENANT = "acme-bank"
DOC_CLASS = "kyc-note"
SUBJECT_CLASS = "natural-person"
SUBJECT_ID = "customer-42"
REQUESTER = "alice"
APPROVER = "bob"
RESUMER = "carol"
APPROVAL_KEY = f"{TENANT}/approval-policy/erasure-officers"
POLICY_KEY = f"{TENANT}/ccf.retention-hold-policy/erasure"
POLICY_URI = f"ccf-artifact://{TENANT}/ccf.retention-hold-policy/erasure@1.0.0"
DECL_KEY = f"{TENANT}/ccf.erasure-subject-declaration/subjects"
DECL_URI = f"ccf-artifact://{TENANT}/ccf.erasure-subject-declaration/subjects@1.0.0"
WORKFLOW_FIXTURE = "workflows/erasure_request_workflow.yaml"
TASK_FIXTURE = "tasks/erasure_request_task.yaml"
ERASURE_RECORD_CLASS = "ccf.erasure-record"
ERASURE_APPROVAL_CLASS = "ccf.erasure-approval"
NOW = datetime(2026, 7, 30, tzinfo=UTC)
STORED_LONG_AGO = NOW - timedelta(days=4000)


def contract(module: str, name: str) -> Any:
    """The ruled name, or a MISSING CONTRACT failure that names it (SEC-009)."""
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        pytest.fail(
            f"MISSING CONTRACT: {module}.{name} (SEC-009; D-IMPL-374 (4)) does not"
            " exist on this tree"
        )


def erasure(name: str) -> Any:
    return contract("ccf.erasure", name)


def door_module(name: str) -> Any:
    return contract("ccf_runtime.erasure", name)


def run(coroutine: Any) -> Any:
    return asyncio.run(coroutine)


def _allowed(*, action_id: str, resource: str) -> AuthzDecision:
    return AuthzDecision(
        allowed=True,
        matched_scope_pattern=TENANT,
        matched_resource_pattern=resource,
        artifact_version="1.0.0",
        action_id=action_id,
        tenant=TENANT,
        resource=resource,
    )


def client_put(store: Any, *, name: str, document: dict[str, Any]) -> ArtifactRef:
    """File a deployment document on the client lane, under a genuine ArtifactWrite."""
    resource = f"{DOC_CLASS}/{name}"
    authorized = mint(
        ArtifactWrite,
        decision=_allowed(action_id=ArtifactWrite.action_id, resource=resource),
        principal="filer",
        decision_id=f"authz-decision-put-{name}",
    )
    ref: ArtifactRef = store.put(authorized, document)
    return ref


def write_kinds() -> WriteKinds:
    """The deployment declares the erasure record mechanism-written under the
    ERASE kind (fix round 1, I3) — never a workflow's Resume."""
    return WriteKinds(
        {
            WORKFLOW_TRACE_CLASS: (Execute, Resume),
            ERASURE_RECORD_CLASS: (contract("ccf.authz.capability", "ArtifactErase"),),
            # Fix round 3, I3 part 2: the recorded approval, filed by the door
            # under the same ERASE kind before the index append.
            ERASURE_APPROVAL_CLASS: (contract("ccf.authz.capability", "ArtifactErase"),),
        }
    )


@dataclass
class Plane:
    registry: ControlPlaneRegistry
    store: FileArtifactStore
    transport: InMemoryHitlTransport
    engine: WorkflowEngine
    clock: Any
    definition_version: str
    document: ArtifactRef
    index_path: Path
    #: The HITL policy the transport and gate are bound to — the SIGNED one
    #: pinning the SEC-005 test key for the approver, unless composed unsigned.
    hitl_policy_key: str
    signed: bool

    @property
    def authority(self) -> Any:
        """The plane's erasure authority (fix round 5, R1, R2): its HITL policy key, the erasure
        workflow it registered, and the test door key's public half."""
        return erasure("ErasureAuthority")(
            tenant_id=TENANT,
            hitl_policy_key=self.hitl_policy_key,
            workflow_definition_hash=self.definition_version,
            door_keys=signing.door_keys(),
        )


def trust(plane: Plane) -> Any:
    """The erasure trust a single-tenant site over ``plane`` composes with: the plane's one authority."""
    return erasure("ErasureTrust")(authorities={TENANT: plane.authority})


def declaration(*, key_paths: tuple[str, ...] = ("customer.id",), identifier_kind: str = "opaque") -> Any:
    return erasure("ErasureSubjectDeclaration")(
        semver="1.0.0",
        tenant_id=TENANT,
        subjects=(
            erasure("ErasureSubjectClass")(
                class_id=SUBJECT_CLASS,
                key_paths=key_paths,
                artifact_classes=(DOC_CLASS,),
                identifier_kind=identifier_kind,
                subject_ref_salt="test-salt-not-a-secret",
            ),
        ),
    )


def retention(*, holds: tuple[Any, ...] = (), minimum_age: timedelta | None = None, semver: str = "1.0.0", erasable: bool = True) -> Any:
    return erasure("RetentionHoldPolicy")(
        semver=semver,
        tenant_id=TENANT,
        classes={
            DOC_CLASS: erasure("ClassRetention")(
                erasable=erasable,
                reasons=("customer-request",),
                holds=holds,
                minimum_age=minimum_age,
            )
        },
    )


def register_policy(registry: ControlPlaneRegistry, policy: Any) -> None:
    register_typed_at_composition(registry, POLICY_KEY, policy, erasure("RETENTION_HOLD_POLICY"))


def compose(tmp_path: Path, *, policy: Any | None = None, gated: bool = True, signed: bool = True) -> Plane:
    registry = ControlPlaneRegistry(clock=eh._ticking_clock())
    # Fix round 4: an erasure approval is bound to a SIGNED HITL attestation,
    # so the plane's transport and gate run under a signed policy pinning the
    # SEC-005 test key for the approver (unsigned only when a test asks).
    hitl_key = signing.register_signed_policy(registry, subject=APPROVER) if signed else plain_hitl_plane(registry)
    register_typed_policy(registry, APPROVAL_KEY, eligible=frozenset({APPROVER}))
    register_typed_at_composition(registry, DECL_KEY, declaration(), erasure("ERASURE_SUBJECT_DECLARATION"))
    register_policy(registry, retention() if policy is None else policy)
    task = parse_artifact(eh._load(TASK_FIXTURE)["task_definition"], TASK_DEFINITION)
    fixture = eh._load(WORKFLOW_FIXTURE)
    register_versioned_at_composition(registry, fixture["keys"]["task_definition"], task, TASK_DEFINITION)
    document = fixture["workflow_definition"]
    if not gated:
        document = {**document, "gate_policies": {}}
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    version = register_versioned_at_composition(
        registry, fixture["keys"]["workflow_definition"], definition, WORKFLOW_DEFINITION
    )
    assert isinstance(version, str), version
    store = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=write_kinds())
    transport = InMemoryHitlTransport(
        control_plane=registry, hitl_policy_key=hitl_key, identity_provider=signing.provider()
    )
    clock = eh._ticking_clock()
    bindings = eh._Bindings(failing=frozenset())
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=store,
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=clock,
    )
    doc = client_put(store, name="note-1", document={"customer": {"id": SUBJECT_ID}, "note": "kyc"})
    index_path = tmp_path / "artifacts" / ".erasure-index.jsonl"
    return Plane(registry, store, transport, engine, clock, version, doc, index_path, hitl_key, signed)


def index_of(plane: Plane) -> Any:
    """The plane's durable erasure index, opened fresh from its file (C1)."""
    return erasure("FileErasureIndex")(plane.index_path)


def door(plane: Plane, *, store: Any = None) -> Any:
    """The plane's erasure door: its authority, the test door key's signer (fix round 5, R2)."""
    return door_module("ErasureDoor")(
        engine=plane.engine,
        factory=WorkflowFactory(control_plane=plane.registry),
        control_plane=plane.registry,
        transport=plane.transport,
        authority=plane.authority,
        door_signer=signing.door_provider(),
        door_key_id=signing.DOOR_KID,
        store=plane.store if store is None else store,
        clock=plane.clock,
        index=index_of(plane),
    )


def request(plane: Plane, *, retained_since: datetime = STORED_LONG_AGO) -> Any:
    subject_ref = erasure("subject_ref_for")(declaration(), SUBJECT_CLASS, SUBJECT_ID)
    return erasure("ErasureRequest")(
        tenant_id=TENANT,
        subject_declaration_ref=DECL_URI,
        subject_class=SUBJECT_CLASS,
        subject_ref=subject_ref,
        addresses=(
            erasure("RequestedAddress")(
                content_address=plane.document.content_address,
                artifact_class=DOC_CLASS,
                retained_since=retained_since,
            ),
        ),
        reason="customer-request",
        legal_basis="opaque basis text the SDK never parses",
        retention_policy_ref=POLICY_URI,
    )


def execute_cap() -> Any:
    return execute_as_principal(tenant=TENANT, resource=WORKFLOW_KEY, principal=REQUESTER)


def resume_cap() -> Any:
    return resume_as_principal(tenant=TENANT, resource=WORKFLOW_KEY, principal=RESUMER)


WORKFLOW_KEY = f"{TENANT}/workflows/erasure-request"


def pending(plane: Plane, event_key: str) -> PendingHitlEvent:
    return next(e for e in plane.transport.pending(tenant=TENANT) if e.event_key == event_key)


def approve(plane: Plane, event: PendingHitlEvent, *, approver: str = APPROVER) -> GateResolution:
    gate = ApprovalGate(
        transport=plane.transport,
        audit=plane.registry.audit_log,
        clock=plane.clock,
        control_plane=plane.registry,
        hitl_policy_key=plane.hitl_policy_key,
        identity_provider=signing.provider(),
    )
    principal = door_submission(event, subject_id=approver).principal
    attestation = (
        signing.sign(
            tenant=TENANT,
            event_key=event.event_key,
            product_content_hash=event.product_content_hash,
            subject_id=approver,
            issued_at=principal.action_time,
        )
        if plane.signed
        else None
    )
    resolution = gate.resolve(
        submit_capability(tenant=TENANT, principal=approver, event_key=event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, GateResolution), resolution
    return resolution


def erase_cap(request: Any, *, principal: str = REQUESTER) -> Any:
    """A genuine ``Authorized[ArtifactErase]`` for exactly this request (ruling 3)."""
    kind = contract("ccf.authz.capability", "ArtifactErase")
    target = f"{request.subject_class}/{request.request_id}"
    return mint(
        kind,
        decision=_allowed(action_id=kind.action_id, resource=target),
        principal=principal,
        decision_id="authz-decision-erase",
    )


def index_path(plane: Plane) -> Path:
    """Where this plane's durable erasure index lives (fix round 1, C1)."""
    path = getattr(plane, "index_path", None)
    if path is None:
        pytest.fail("MISSING CONTRACT: the plane declares no durable erasure index (SEC-009; C1)")
    return Path(path)


def fabric_clock() -> datetime:
    """The injected fabric clock test compositions stamp audits with (ruling 3)."""
    return NOW
