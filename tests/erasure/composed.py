"""Shared SEC-009 erasure helpers for the per-site and per-door controls (`D-IMPL-374` (4)).

``erase(store, index, address)`` plants a GENUINE-SHAPED erasure the way the
door leaves one — the recorded ``ccf.erasure-approval`` first (fix round 3),
then the index entry (write-ahead, fix round 1 ruling (ii)), then the
``ccf.erasure-record`` it names, all under the ``ArtifactErase`` capability
bound to the request (fix round 2, I3) into the same file store — so the
consult's boot validation finds an agreeing record and approval.
``assert_consults`` holds a site's store to refusing it.

**This helper BYPASSES THE DOOR ON PURPOSE, and lives under ``tests/`` only**
(coordinator ruling on fix round 2's second block). It exercises the CONSULT —
every store construction site's refusal — not the door's admission: several
sites erase replay inputs or run on planes with no declared erasure workflow,
which the door rightly refuses. The approval it files was given by no human;
a production deployment can only obtain one through the door's recorded gate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import DerivedWrite, WriteKinds
from ccf.authz.capability import mint
from ccf.authz.decision import AuthzDecision
from ccf.contracts.canonical import content_hash
from ccf.agents.definitions import TASK_DEFINITION
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneMissing
from ccf.hitl.principal import ApproverIdentity
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from tests.composition import declared_hitl_policy_key, register_versioned_at_composition
from tests.erasure import harness as h
from tests.erasure import signing
from tests.hitl.sec006_harness import register_typed_policy
from tests.workflow import test_engine as eh

ERASED_AT = datetime(2026, 7, 30, tzinfo=UTC)
REASON = "customer-request"
#: The fixture workflow's one approval gate (fix round 4, ruling 3).
GATE = "erasure-approval"


def _tenant_of(key: str) -> str:
    return key.partition("/")[0]


def approval_policy_uri(tenant: str) -> str:
    return f"ccf-artifact://{tenant}/approval-policy/erasure-officers@1.0.0"


def register_erasure_workflow(registry: Any, *, tenant: str) -> str:
    """Register the fixture erasure workflow (and its task) under ``tenant``; return the definition's content address.

    Idempotent: a registry that already holds the same content under the key
    is left as it is. The fixture names ``acme-bank``; under another tenant its
    tenant field and pinned references are rewritten to that tenant.
    """
    fixture = eh._load(h.WORKFLOW_FIXTURE)
    task_key = f"{tenant}/ccf.task-definition/erasure-request"
    workflow_key = f"{tenant}/workflows/erasure-request"
    document = dict(fixture["workflow_definition"])
    document["tenant"] = tenant
    document["task_definition_ref"] = f"ccf-artifact://{task_key}@1.0.0"
    document["gate_policies"] = {GATE: approval_policy_uri(tenant)}
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    wanted = content_hash(definition)
    if wanted in registry.versions(workflow_key):
        return wanted
    task = parse_artifact(eh._load(h.TASK_FIXTURE)["task_definition"], TASK_DEFINITION)
    register_versioned_at_composition(registry, task_key, task, TASK_DEFINITION)
    registered = register_versioned_at_composition(registry, workflow_key, definition, WORKFLOW_DEFINITION)
    assert registered == wanted, registered
    return wanted


def register_approval_policy(registry: Any, *, tenant: str) -> None:
    key = f"{tenant}/approval-policy/erasure-officers"
    try:
        registry.resolve_latest(key)
    except ControlPlaneMissing:
        register_typed_policy(registry, key, eligible=frozenset({h.APPROVER}))


def _root(store: Any) -> Any:
    inner = getattr(store, "inner", store)
    return getattr(inner, "_root")


def _erase_capability(tenant: str, resource: str) -> Any:
    kind = h.contract("ccf.authz.capability", "ArtifactErase")
    return mint(
        kind,
        decision=AuthzDecision(
            allowed=True, matched_scope_pattern=tenant, matched_resource_pattern=resource,
            artifact_version="1.0.0", action_id=kind.action_id, tenant=tenant, resource=resource,
        ),
        principal="erasure-officer",
        decision_id="authz-decision-erase-planted",
    )


def append_as(index: Any, entry: Any) -> None:
    """Append ``entry`` under the ERASE capability bound to ITS request (fix round 2, I3)."""
    index.append(_erase_capability(entry.tenant_id, f"{entry.subject_class}/{entry.request_id}"), entry)


def subject_ref() -> str:
    return str(h.erasure("subject_ref_for")(h.declaration(), h.SUBJECT_CLASS, h.SUBJECT_ID))


def erase(
    store: Any,
    index: Any,
    address: str,
    *,
    control_plane: Any,
    tenant: str = h.TENANT,
    artifact_class: str = h.DOC_CLASS,
    hitl_policy_key: str | None = None,
) -> Any:
    """Plant one genuine-shaped erasure of ``address`` under ``tenant``; return the record.

    ``control_plane`` is the site's OWN Control Plane. Everything the consult
    verifies (fix round 4, rulings 1–4) is registered there: the signed HITL
    policy pinning the SEC-005 test key for the approver under the site's
    HITL policy key — ``hitl_policy_key``, or the composed store's own — the
    approval policy naming the approver eligible, and the fixture erasure
    workflow whose gate the approval names. The approver is never the
    requester.
    """
    key = hitl_policy_key or getattr(store, "hitl_policy_key", None) or declared_hitl_policy_key(tenant)
    assert _tenant_of(key) == tenant, (key, tenant)  # the site's key must be in the planting tenant
    ref = subject_ref()
    record_id = content_hash({"tenant_id": tenant, "address": address, "planted": True})
    actor = ApproverIdentity(subject_id=h.APPROVER, identity_provider_ref="acme-bank/idp/okta")
    # A REAL signature by the SEC-005 test key, pinned for the approver in a
    # HITL policy registered in the site's own Control Plane — never a
    # placeholder (fix round 4).
    signing.register_signed_policy(control_plane, subject=h.APPROVER, key=key)
    register_approval_policy(control_plane, tenant=tenant)
    definition_hash = register_erasure_workflow(control_plane, tenant=tenant)
    gate_state = content_hash({"planted-gate-state": address, "tenant": tenant})
    attestation = signing.sign(
        tenant=tenant,
        event_key=f"{tenant}/{record_id}/{GATE}",
        product_content_hash=gate_state,
        subject_id=h.APPROVER,
        issued_at=ERASED_AT,
    )
    approval = h.erasure("ErasureApproval")(
        tenant_id=tenant,
        request_id=record_id,
        approver=actor,
        verdict="approve",
        acted_at=attestation.claims.issued_at,
        gate=GATE,
        gate_state_hash=gate_state,
        workflow_definition_hash=definition_hash,
        submission_hash=content_hash({"planted-submission": address}),
        attestation=attestation,
        hitl_policy_ref=signing.policy_ref(control_plane, key),
    )
    approval_ref = content_hash(approval)
    record = h.erasure("ErasureRecord")(
        tenant_id=tenant,
        record_id=record_id,
        request_id=record_id,
        subject_class=h.SUBJECT_CLASS,
        subject_ref=ref,
        addresses=(
            h.erasure("ErasedAddress")(
                content_address=address, artifact_class=artifact_class, key_paths=("customer.id",)
            ),
        ),
        erased_at=ERASED_AT,
        actor=actor,
        requested_by=h.REQUESTER,
        authorizing_decision_id="authz-decision-erase-planted",
        approval_policy_ref=approval_policy_uri(tenant),
        approval_ref=approval_ref,
        retention_decision=h.erasure("RetentionDecision")(
            policy_ref=h.POLICY_URI, verdict="admit", reason_code="admitted"
        ),
        reason=REASON,
        legal_basis="planted by the test",
    )
    # Write-ahead: the entry first, then the record it names — both under the
    # ERASE capability bound to this request (fix round 2, I3).
    erase_cap = _erase_capability(tenant, f"{h.SUBJECT_CLASS}/{record_id}")
    kind = h.contract("ccf.authz.capability", "ArtifactErase")
    filer = FileArtifactStore(
        root=_root(store),
        write_kinds=WriteKinds({h.ERASURE_RECORD_CLASS: (kind,), h.ERASURE_APPROVAL_CLASS: (kind,)}),
    )
    filer.put(erase_cap, DerivedWrite(artifact_class=h.ERASURE_APPROVAL_CLASS, name=approval_ref, artifact=approval))
    index.append(
        erase_cap,
        h.erasure("ErasureIndexEntry")(
            tenant_id=tenant,
            content_address=address,
            erasure_record_address=content_hash(record),
            subject_class=h.SUBJECT_CLASS,
            request_id=record_id,
            subject_ref=ref,
            approval_ref=approval_ref,
            reason=REASON,
            erased_at=ERASED_AT,
        ),
    )
    filer.put(
        erase_cap,
        DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name=record_id, artifact=record),
    )
    return record


def assert_consults(
    store: Any, index: Any, *, control_plane: Any, name: str = "probe", tenant: str = h.TENANT
) -> None:
    """File a probe through the site's own store, erase it in the site's own index, require refusal.

    The refusal must be the SUPPORTED one (the record's reason), not
    ``index-unsupported``: a site whose consult cannot verify the signed approval
    through ``control_plane`` would also refuse, for the wrong reason (fix round 4).
    """
    ref = h.client_put(store, name=name, document={"customer": {"id": h.SUBJECT_ID}, "site": name})
    assert store.get(content_address=ref.content_address)  # served while not erased
    erase(store, index, ref.content_address, control_plane=control_plane, tenant=tenant)
    with pytest.raises(h.erasure("ErasedContentRefused")):
        store.get(content_address=ref.content_address)
    # A tenantless view discloses no facts by design; the erasing tenant's view does.
    view = store if store.tenant_id is not None else store.scoped(tenant)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        view.get(content_address=ref.content_address)
    assert refused.value.reason == REASON, refused.value.reason
