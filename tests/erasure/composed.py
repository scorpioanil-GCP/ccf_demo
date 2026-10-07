"""Shared SEC-009 erasure helpers for the per-site and per-door controls (`D-IMPL-374` (4)).

``erase(store, index, address)`` plants a GENUINE erasure the way the door
leaves one — write-ahead (fix round 1, ruling (ii)): the index entry first,
then the ``ccf.erasure-record`` it names, filed under an ``ArtifactErase``
capability into the same file store — so the consult's boot validation (the
record is the only authority) finds an agreeing record. ``assert_consults``
holds a site's store to refusing it.
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
from ccf.hitl.principal import ApproverIdentity
from tests.erasure import harness as h

ERASED_AT = datetime(2026, 7, 30, tzinfo=UTC)
REASON = "customer-request"


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


def subject_ref() -> str:
    return str(h.erasure("subject_ref_for")(h.declaration(), h.SUBJECT_CLASS, h.SUBJECT_ID))


def erase(store: Any, index: Any, address: str, *, tenant: str = h.TENANT, artifact_class: str = h.DOC_CLASS) -> Any:
    """Plant one genuine erasure of ``address`` under ``tenant``; return the record."""
    ref = subject_ref()
    approval_ref = "a" * 64
    record_id = content_hash({"tenant_id": tenant, "address": address, "planted": True})
    record = h.erasure("ErasureRecord")(
        tenant_id=tenant,
        record_id=record_id,
        subject_class=h.SUBJECT_CLASS,
        subject_ref=ref,
        addresses=(
            h.erasure("ErasedAddress")(
                content_address=address, artifact_class=artifact_class, key_paths=("customer.id",)
            ),
        ),
        erased_at=ERASED_AT,
        actor=ApproverIdentity(subject_id=h.APPROVER, identity_provider_ref="acme-bank/idp/okta"),
        requested_by=h.REQUESTER,
        authorizing_decision_id="authz-decision-erase-planted",
        approval_policy_ref="ccf-artifact://acme-bank/approval-policy/erasure-officers@1.0.0",
        approval_ref=approval_ref,
        retention_decision=h.erasure("RetentionDecision")(
            policy_ref=h.POLICY_URI, verdict="admit", reason_code="admitted"
        ),
        reason=REASON,
        legal_basis="planted by the test",
    )
    # Write-ahead: the entry first, then the record it names.
    index.append(
        h.erasure("ErasureIndexEntry")(
            tenant_id=tenant,
            content_address=address,
            erasure_record_address=content_hash(record),
            subject_ref=ref,
            approval_ref=approval_ref,
            reason=REASON,
            erased_at=ERASED_AT,
        )
    )
    kind = h.contract("ccf.authz.capability", "ArtifactErase")
    filer = FileArtifactStore(root=_root(store), write_kinds=WriteKinds({h.ERASURE_RECORD_CLASS: (kind,)}))
    filer.put(
        _erase_capability(tenant, f"{h.SUBJECT_CLASS}/{record_id}"),
        DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name=record_id, artifact=record),
    )
    return record


def assert_consults(store: Any, index: Any, *, name: str = "probe", tenant: str = h.TENANT) -> None:
    """File a probe through the site's own store, erase it in the site's own index, require refusal."""
    ref = h.client_put(store, name=name, document={"customer": {"id": h.SUBJECT_ID}, "site": name})
    assert store.get(content_address=ref.content_address)  # served while not erased
    erase(store, index, ref.content_address, tenant=tenant)
    with pytest.raises(h.erasure("ErasedContentRefused")):
        store.get(content_address=ref.content_address)
