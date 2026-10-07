"""SEC-009 fix round 5, rulings R1–R5 — the record is door-signed; the erasure workflow, its tenant and the door key are fixed at composition (`D-IMPL-374` (4)).

The round-4 re-review measured three forgeries SUPPORTED, because rulings 2
and 3 were judged against fields a filer writes — the record's
``requested_by`` and ``approval_policy_ref`` and the approval's
``workflow_definition_hash``:

* **b1** — an eligible officer who is also the real requester writes another
  name into ``requested_by`` and approves himself;
* **b2** — an approver pinned in the HITL policy but not an erasure officer
  names another registered workflow of the same tenant whose gate policy
  lists him;
* **b3** — the same, with that workflow and policy in another tenant;

and the validation cache served a do-nothing identity provider's SUPPORTED
verdict to a site composed with a real verifier. Section A inverts each (the
defect ABSENT). It is written to run on the tree before this round as well —
there it composes with the HITL policy key alone and plants an unsigned
record, so it fails on the BEHAVIOR (the forgery read SUPPORTED), never on a
signature error. Sections B–F hold the rulings' named refusals, each asserted
by its reason code so that one severing reddens one test:

* **R1** — the erasure workflow (content hash and tenant) is fixed at
  composition; an approval for any other workflow, or in any other tenant,
  refuses by name; the approval policy is that workflow's gate's, never a
  record field (the field is deleted);
* **R2** — the door signs every record; a record without a verifying door
  signature is ``index-unsupported`` and audited, so ``requested_by`` is what
  the door observed;
* **R3** — the validation cache is keyed by the identity provider instance;
* **R4** — a tenant→authority mapping; a tenant with no authority refuses by
  name;
* **R5** — ``approval-policy-window-unknown`` is exercised; the door refuses a
  transport bound to another HITL key; the docs no longer claim what was
  measured false.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta
from pathlib import Path
from collections.abc import Callable
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.principal import ApproverIdentity
from ccf.hitl.transport import HITL_POLICY, InMemoryHitlTransport
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf.workflow.factory import WorkflowFactory
from tests.composition import register_typed_at_composition, register_versioned_at_composition
from tests.erasure import composed
from tests.erasure import harness as h
from tests.erasure import signing
from tests.hitl.sec006_harness import execute_as_principal, register_typed_policy
from tests.workflow import test_engine as eh

GATE = "erasure-approval"
APPROVAL_POLICY_URI = "ccf-artifact://acme-bank/approval-policy/erasure-officers@1.0.0"
CAROL = "carol-never-requested"
DAVE = "dave"
OTHER = "beta-bank"
SANDBOX = "sandbox-tenant"
REPO = Path(__file__).resolve().parents[2]
FRAGMENT = "docs/surface-changes/374-04-sec-009-minimum-erasure.md"
PAGE = "public/how-to/security-and-deployment.md"


# -- composition, on either side of this round ------------------------------------


def _new_api() -> bool:
    """Whether this tree's consult takes the per-tenant trust root (fix round 5)."""
    return "erasure_trust" in inspect.signature(h.erasure("compose_erasure_consult")).parameters


def _authority(
    plane: h.Plane,
    *,
    tenant: str = h.TENANT,
    hitl_key: str | None = None,
    definition: str | None = None,
    door_keys: Any = None,
) -> Any:
    """The plane's erasure authority: its HITL key, its registered erasure workflow, the test door key."""
    return h.erasure("ErasureAuthority")(
        tenant_id=tenant,
        hitl_policy_key=hitl_key or plane.hitl_policy_key,
        workflow_definition_hash=definition or plane.definition_version,
        door_keys=door_keys or signing.door_keys(),
    )


def _trust(*authorities: Any) -> Any:
    return h.erasure("ErasureTrust")(authorities={a.tenant_id: a for a in authorities})


def _consult(plane: h.Plane, *, provider: Any = None, trust: Any = None, cp: Any = None) -> Any:
    compose = h.erasure("compose_erasure_consult")
    kw: dict[str, Any] = dict(
        index=h.index_of(plane), audit_log=ControlPlaneRegistry().audit_log, clock=h.fabric_clock,
        control_plane=cp or plane.registry, tenant_id=h.TENANT,
    )
    if provider is not None:
        kw["identity_provider"] = provider
    if _new_api():
        kw["erasure_trust"] = trust or _trust(_authority(plane))
    else:
        # The tree before fix round 5 composed with the HITL policy key alone.
        kw["hitl_policy_key"] = plane.hitl_policy_key
    return compose(plane.store, **kw)


def _outcome(consulted: Any, address: str) -> str:
    """``supported`` when the record's own reason is served; else ``unsupported(<reason>)``."""
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=address)
    return "supported" if refused.value.reason == composed.REASON else f"unsupported({refused.value.reason})"


def _pin(plane: h.Plane) -> str:
    return signing.policy_ref(plane.registry, plane.hitl_policy_key)


def _hitl_policy(registry: ControlPlaneRegistry, key: str, trusted: dict[str, Any]) -> str:
    """Register a signed HitlPolicy under ``key``; return its ``key@version`` pin."""
    policy = parse_artifact(
        {"semver": "1.0.0", "signed_binding_required": True, "signature_max_age_seconds": 300,
         "permitted_clock_skew_seconds": 60, "trusted_keys": trusted}, HITL_POLICY,
    )
    register_typed_at_composition(registry, key, policy, HITL_POLICY)
    version, _ = registry.resolve_latest(key)
    return f"{key}@{version}"


def _second_workflow(registry: ControlPlaneRegistry, *, tenant: str, name: str, approval_policy_uri: str) -> str:
    """ANOTHER registered workflow definition — not the deployment's erasure workflow — whose gate is named like the erasure gate."""
    document = dict(eh._load(h.WORKFLOW_FIXTURE)["workflow_definition"])
    document["name"] = f"{name}-workflow"
    document["tenant"] = tenant
    document["task_definition_ref"] = f"ccf-artifact://{tenant}/ccf.task-definition/erasure-request@1.0.0"
    document["gate_policies"] = {GATE: approval_policy_uri}
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    registered = register_versioned_at_composition(registry, f"{tenant}/workflows/{name}", definition, WORKFLOW_DEFINITION)
    assert isinstance(registered, str), registered
    return registered


def _dave_pinned(plane: h.Plane) -> tuple[Path, str]:
    """Dave holds a key pinned in the deployment's OWN HITL policy, beside the eligible officer's; he is not an erasure officer."""
    dave = signing.forger_key_dir()
    pin = _hitl_policy(
        plane.registry, plane.hitl_policy_key,
        {h.APPROVER: {signing.APPROVER_KID: signing.public_jwk()}, DAVE: {signing.APPROVER_KID: signing.public_jwk(dave)}},
    )
    return dave, pin


def _plant(
    plane: h.Plane,
    request: Any,
    *,
    approver: str,
    approver_keys: Path,
    policy_ref: str,
    requested_by: str = h.REQUESTER,
    approval_policy_ref: str = APPROVAL_POLICY_URI,
    definition_hash: str | None = None,
    door: Path | None = None,
    door_signature: Callable[[Any], str] | None = None,
    door_key_id: str = signing.DOOR_KID,
    cap_principal: str = h.REQUESTER,
    issued_at: datetime | None = None,
) -> str:
    """File an approval, an index entry and a record — all a filer holding only ``ArtifactErase`` can file.

    The approval carries a REAL signature by ``approver_keys``. The record's door
    signature is made with ``door`` — ``None`` is the GENUINE door key (the
    strongest forger, so whatever refuses is a judgment after the door
    signature), a directory is a forger's door key — or by ``door_signature``.
    On the tree before this round the entry carries no door signature and the
    record names its approval policy, exactly as a filer wrote it there.
    """
    issued = h.fabric_clock() if issued_at is None else issued_at
    attestation = signing.sign(
        tenant=h.TENANT, event_key=f"{h.TENANT}/{request.request_id}/{GATE}", product_content_hash="1" * 64,
        subject_id=approver, issued_at=issued, directory=approver_keys,
    )
    actor = ApproverIdentity(subject_id=approver, identity_provider_ref="x")
    approval = h.erasure("ErasureApproval")(
        tenant_id=h.TENANT, request_id=request.request_id, approver=actor, verdict="approve", acted_at=issued,
        gate=GATE, gate_state_hash="1" * 64, workflow_definition_hash=definition_hash or plane.definition_version,
        submission_hash="3" * 64, attestation=attestation, hitl_policy_ref=policy_ref,
    )
    cap = h.erase_cap(request, principal=cap_principal)
    address = plane.document.content_address
    filed = plane.store.put(cap, DerivedWrite(artifact_class=h.ERASURE_APPROVAL_CLASS, name="planted", artifact=approval))
    record_type = h.erasure("ErasureRecord")
    fields: dict[str, Any] = dict(
        tenant_id=h.TENANT, record_id="f" * 64, request_id=request.request_id, subject_class=h.SUBJECT_CLASS,
        subject_ref=request.subject_ref,
        addresses=(h.erasure("ErasedAddress")(content_address=address, artifact_class=h.DOC_CLASS, key_paths=("customer.id",)),),
        erased_at=h.fabric_clock(), actor=actor, requested_by=requested_by,
        authorizing_decision_id="authz-decision-erase", approval_ref=filed.content_address,
        retention_decision=h.erasure("RetentionDecision")(policy_ref=h.POLICY_URI, verdict="admit", reason_code="admitted"),
        reason=composed.REASON, legal_basis="filed by a holder of ArtifactErase",
    )
    if "approval_policy_ref" in record_type.model_fields:
        fields["approval_policy_ref"] = approval_policy_ref  # the tree before fix round 5 read it
    record = record_type(**fields)
    entry_type = h.erasure("ErasureIndexEntry")
    entry: dict[str, Any] = dict(
        tenant_id=h.TENANT, content_address=address, erasure_record_address=content_hash(record),
        subject_class=request.subject_class, request_id=request.request_id, subject_ref=request.subject_ref,
        approval_ref=filed.content_address, reason=composed.REASON, erased_at=h.fabric_clock(),
    )
    if "door_signature" in entry_type.model_fields:
        sign = h.erasure("sign_erasure_record")
        entry["door_signature"] = (
            door_signature(record) if door_signature is not None
            else sign(record, signer=signing.door_provider(door), key_id=signing.DOOR_KID)
        )
        entry["door_key_id"] = door_key_id
    h.index_of(plane).append(cap, entry_type(**entry))
    plane.store.put(cap, DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="f" * 64, artifact=record))
    return address


def _judgment(plane: h.Plane, address: str, *, trust: Any = None, cp: Any = None) -> str:
    """The NAMED judgment the consult makes of the entry erasing ``address``: ``supported`` or its reason code."""
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=address)
    assert entry is not None
    provider = h.erasure("reference_approval_verifier")()
    try:
        record, authority = h.erasure("verify_erasure_entry")(
            entry, plane.store.get(content_address=entry.erasure_record_address),
            trust=trust or _trust(_authority(plane)), identity_provider=provider,
        )
        approval = h.erasure("ErasureApproval").model_validate_json(plane.store.get(content_address=record.approval_ref))
        h.erasure("verify_erasure_approval")(
            approval, tenant_id=record.tenant_id, request_id=record.request_id, approver=record.actor,
            requested_by=record.requested_by, authority=authority, control_plane=cp or plane.registry,
            identity_provider=provider,
        )
    except (h.erasure("ErasureRecordInvalid"), h.erasure("ErasureApprovalInvalid")) as refused:
        return str(refused.reason_code)
    return "supported"


def _door(
    plane: h.Plane,
    *,
    transport: Any = None,
    authority: Any = None,
    door_signer: Any = None,
    door_key_id: str = signing.DOOR_KID,
) -> Any:
    return h.door_module("ErasureDoor")(
        engine=plane.engine, factory=WorkflowFactory(control_plane=plane.registry), control_plane=plane.registry,
        transport=transport or plane.transport, authority=authority or _authority(plane),
        door_signer=door_signer or signing.door_provider(), door_key_id=door_key_id,
        store=plane.store, clock=plane.clock, index=h.index_of(plane),
    )


class _AcceptAll:
    """An adopter-supplied identity provider that verifies nothing (ruling 6)."""

    def verify(self, *, signed: Any, public_keys: Any) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)


# -- A. the re-review's measurements, inverted -------------------------------------


def test_b1_an_officer_who_requested_cannot_approve_himself_by_writing_another_requester(tmp_path: Path) -> None:
    """b1: bob is an eligible erasure officer AND the real requester (he holds the
    erase capability); he signs his own approval and writes someone else into
    ``requested_by``. Holding ``ArtifactErase`` does not let him choose who
    counts as the requester."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(
        plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=_pin(plane),
        requested_by=CAROL, cap_principal=h.APPROVER, door=signing.forger_door_key_dir(),
    )
    outcome = _outcome(_consult(plane), address)
    assert outcome.startswith("unsupported"), f"b1: the filer chose who counts as the requester ({outcome})"


def test_b2_an_ineligible_approver_cannot_borrow_another_workflow_of_the_same_tenant(tmp_path: Path) -> None:
    """b2: dave is pinned in the HITL policy but is no erasure officer; he names
    another registered workflow of the same tenant whose gate's policy lists him."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    dave, pin = _dave_pinned(plane)
    expense = register_typed_policy(plane.registry, f"{h.TENANT}/approval-policy/expense-approvers", eligible=frozenset({DAVE}))
    other = _second_workflow(plane.registry, tenant=h.TENANT, name="expense", approval_policy_uri=expense)
    address = _plant(
        plane, request, approver=DAVE, approver_keys=dave, policy_ref=pin, approval_policy_ref=expense,
        definition_hash=other, door=signing.forger_door_key_dir(),
    )
    outcome = _outcome(_consult(plane), address)
    assert outcome.startswith("unsupported"), f"b2: another workflow's gate policy approved the erasure ({outcome})"


def test_b3_an_ineligible_approver_cannot_borrow_a_workflow_of_another_tenant(tmp_path: Path) -> None:
    """b3: the same, with the workflow and the approval policy in another tenant's key space."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    dave, pin = _dave_pinned(plane)
    anyone = register_typed_policy(plane.registry, f"{SANDBOX}/approval-policy/anyone", eligible=frozenset({DAVE}))
    other = _second_workflow(plane.registry, tenant=SANDBOX, name="scratch", approval_policy_uri=anyone)
    address = _plant(
        plane, request, approver=DAVE, approver_keys=dave, policy_ref=pin, approval_policy_ref=anyone,
        definition_hash=other, door=signing.forger_door_key_dir(),
    )
    outcome = _outcome(_consult(plane), address)
    assert outcome.startswith("unsupported"), f"b3: another tenant's workflow approved the erasure ({outcome})"


def test_r3_a_do_nothing_providers_verdict_never_serves_a_real_verifier_site(tmp_path: Path) -> None:
    """The reviewer's three steps, over ONE store, index and Control Plane."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(
        plane, request, approver=h.APPROVER, approver_keys=signing.forger_key_dir(), policy_ref=_pin(plane),
        door=signing.forger_door_key_dir(),
    )
    # 1. A real verifier rejects the forged plant.
    assert _outcome(_consult(plane, provider=signing.provider()), address).startswith("unsupported")
    # 2. A do-nothing provider over the same store and index marks it supported
    #    (the adopter's trust choice, ruling 6).
    assert _outcome(_consult(plane, provider=_AcceptAll()), address) == "supported"
    # 3. A FRESH real-verifier site must not read SUPPORTED from the cache.
    outcome = _outcome(_consult(plane, provider=signing.provider()), address)
    assert outcome.startswith("unsupported"), f"R3: a do-nothing provider's verdict served a real verifier ({outcome})"


# -- B. R1: the erasure workflow and its tenant are fixed at composition -----------


def test_r1_the_record_names_no_approval_policy() -> None:
    """The approval policy is the declared workflow's gate's; the record field a filer wrote is deleted."""
    assert "approval_policy_ref" not in h.erasure("ErasureRecord").model_fields


def test_r1_an_approval_for_another_workflow_is_refused_by_name_even_when_the_door_signed(tmp_path: Path) -> None:
    """The strongest form of b2's mechanism: the door signature GENUINE, the approver
    eligible, the other workflow's gate named like the erasure gate and bound to
    the SAME policy — only the workflow differs."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    lookalike = _second_workflow(plane.registry, tenant=h.TENANT, name="lookalike", approval_policy_uri=APPROVAL_POLICY_URI)
    address = _plant(plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=_pin(plane), definition_hash=lookalike)
    assert _judgment(plane, address) == "approval-workflow-mismatch"
    assert _outcome(_consult(plane), address).startswith("unsupported")


@pytest.mark.parametrize("tenant", [h.TENANT, SANDBOX])
def test_r1_b2_and_b3_in_their_strongest_form_are_refused_by_name(tmp_path: Path, tenant: str) -> None:
    """b2/b3 by a forger who ALSO holds the door key: the workflow the approval names is not the declared one."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    dave, pin = _dave_pinned(plane)
    policy = register_typed_policy(plane.registry, f"{tenant}/approval-policy/dave-approves", eligible=frozenset({DAVE}))
    other = _second_workflow(plane.registry, tenant=tenant, name="dave-workflow", approval_policy_uri=policy)
    address = _plant(plane, request, approver=DAVE, approver_keys=dave, policy_ref=pin, definition_hash=other)
    assert _judgment(plane, address) == "approval-workflow-mismatch"
    assert _outcome(_consult(plane), address).startswith("unsupported")


def test_r1_an_approval_in_another_tenant_is_refused_by_name(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    issued = h.fabric_clock()
    attestation = signing.sign(
        tenant=OTHER, event_key=f"{OTHER}/{request.request_id}/{GATE}", product_content_hash="1" * 64,
        subject_id=h.APPROVER, issued_at=issued,
    )
    actor = ApproverIdentity(subject_id=h.APPROVER, identity_provider_ref="x")
    approval = h.erasure("ErasureApproval")(
        tenant_id=OTHER, request_id=request.request_id, approver=actor, verdict="approve", acted_at=issued, gate=GATE,
        gate_state_hash="1" * 64, workflow_definition_hash=plane.definition_version, submission_hash="3" * 64,
        attestation=attestation, hitl_policy_ref=f"{OTHER}/hitl/erasure-attestation-policy@1.0.0",
    )
    with pytest.raises(h.erasure("ErasureApprovalInvalid")) as refused:
        h.erasure("verify_erasure_approval")(
            approval, tenant_id=OTHER, request_id=request.request_id, approver=actor, requested_by=h.REQUESTER,
            authority=_authority(plane), control_plane=plane.registry, identity_provider=signing.provider(),
        )
    assert refused.value.reason_code == "approval-tenant-mismatch"


def test_r1_the_declared_workflow_must_resolve_in_the_consulting_control_plane(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=_pin(plane))
    assert _judgment(plane, address) == "supported"  # the control: the plane holds the declared workflow
    booted = ControlPlaneRegistry()  # holds the HITL and approval policies, NOT the erasure workflow
    signing.register_signed_policy(booted, subject=h.APPROVER, key=plane.hitl_policy_key)
    register_typed_policy(booted, h.APPROVAL_KEY, eligible=frozenset({h.APPROVER}))
    assert _judgment(plane, address, cp=booted) == "approval-workflow-unresolvable"


def test_r1_the_door_refuses_any_workflow_but_the_declared_erasure_workflow(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = _door(plane)
    lookalike = _second_workflow(plane.registry, tenant=h.TENANT, name="lookalike", approval_policy_uri=APPROVAL_POLICY_URI)
    request = h.request(plane)
    execute = execute_as_principal(tenant=h.TENANT, resource=f"{h.TENANT}/workflows/lookalike", principal=h.REQUESTER)
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.request(execute, definition_version=lookalike, request=request, erase=h.erase_cap(request)))
    assert refused.value.reason_code == "workflow-not-declared"
    assert not plane.transport.pending(tenant=h.TENANT), "a refused request starts no approval"


# -- C. R2: the record is door-signed ----------------------------------------------


def test_r2_a_genuine_erasure_through_the_door_is_door_signed_and_supported(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = _door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    assert record.requested_by == h.REQUESTER  # what the door observed: the engine's recorded starter
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is not None and entry.door_key_id == signing.DOOR_KID
    verified, authority = h.erasure("verify_erasure_entry")(
        entry, plane.store.get(content_address=entry.erasure_record_address),
        trust=_trust(_authority(plane)), identity_provider=signing.provider(),
    )
    assert verified == record and authority.tenant_id == h.TENANT
    assert _outcome(_consult(plane), plane.document.content_address) == "supported"


def _signature_by_the_door_over_another_record(record: Any) -> str:
    """A GENUINE door signature — over a record that says something else."""
    other = record.model_copy(update={"requested_by": "someone-the-door-observed"})
    return str(h.erasure("sign_erasure_record")(other, signer=signing.door_provider(), key_id=signing.DOOR_KID))


def _door_key_signature_without_the_record_assertion(record: Any) -> str:
    """The door's own key, over this record's bytes, but not asserting it signs an erasure record."""
    envelope = signing.door_provider().sign(product=record, key_id=signing.DOOR_KID)
    return f"{envelope.protected}..{envelope.signature}"


@pytest.mark.parametrize(
    "variant",
    ["forger-key", "another-records-signature", "no-record-assertion", "malformed", "key-id-mismatch"],
)
def test_r2_a_record_without_a_verifying_door_signature_is_unsupported_and_audited(tmp_path: Path, variant: str) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    plant: dict[str, Any] = {
        "forger-key": dict(door=signing.forger_door_key_dir()),
        "another-records-signature": dict(door_signature=_signature_by_the_door_over_another_record),
        "no-record-assertion": dict(door_signature=_door_key_signature_without_the_record_assertion),
        "malformed": dict(door_signature=lambda record: "not-a-detached-jws"),
        "key-id-mismatch": dict(door_key_id="a-key-the-authority-does-not-declare"),
    }[variant]
    address = _plant(plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=_pin(plane), **plant)
    assert _judgment(plane, address) == "record-signature-invalid"
    audit = ControlPlaneRegistry().audit_log
    consulted = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=audit, clock=h.fabric_clock, control_plane=plane.registry,
        tenant_id=h.TENANT, erasure_trust=_trust(_authority(plane)),
    )
    assert _outcome(consulted, address) == "unsupported(index-unsupported)"
    assert any(e.action == "erasure_index_unsupported" for e in audit.events())


def test_r2_the_door_refuses_a_signing_key_the_authority_does_not_declare(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    refused = h.erasure("ErasureCompositionRefused")
    with pytest.raises(refused):
        _door(plane, door_signer=signing.door_provider(signing.forger_door_key_dir()))  # the right kid, other material
    with pytest.raises(refused):
        _door(plane, door_key_id="a-key-the-authority-does-not-declare")


def test_r2_a_declared_door_key_carries_no_private_material(tmp_path: Path) -> None:
    import json

    from pydantic import ValidationError

    plane = h.compose(tmp_path)
    private = json.loads((signing.door_key_dir() / f"{signing.DOOR_KID}.jwk").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError, match="private"):
        _authority(plane, door_keys={signing.DOOR_KID: private})


# -- D. R4: a tenant→authority mapping ---------------------------------------------


def _shared_site(tmp_path: Path) -> tuple[Any, Any, ControlPlaneRegistry, str]:
    store = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    ref = h.client_put(store, name="shared", document={"customer": {"id": h.SUBJECT_ID}})
    return store, index, ControlPlaneRegistry(), ref.content_address


def test_r4_each_declared_tenant_erases_at_a_multi_tenant_site(tmp_path: Path) -> None:
    trust_type = h.erasure("ErasureTrust")
    declared = h.contract("tests.composition", "declared_erasure_authority")
    store, index, registry, address = _shared_site(tmp_path)
    acme, beta = declared(h.TENANT), declared(OTHER)
    assert acme.hitl_policy_key != beta.hitl_policy_key  # each tenant's own HITL key
    composed.erase(store, index, address, control_plane=registry, tenant=h.TENANT, authority=acme)
    composed.erase(store, index, address, control_plane=registry, tenant=OTHER, authority=beta)
    tenantless = h.erasure("compose_erasure_consult")(
        store, index=index, audit_log=registry.audit_log, clock=h.fabric_clock, control_plane=registry,
        erasure_trust=trust_type(authorities={h.TENANT: acme, OTHER: beta}),
    )
    for tenant in (h.TENANT, OTHER):
        with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
            tenantless.scoped(tenant).get(content_address=address)
        assert refused.value.reason == composed.REASON, (tenant, refused.value.reason)


def test_r4_a_tenant_with_no_authority_is_refused_by_name(tmp_path: Path) -> None:
    trust_type = h.erasure("ErasureTrust")
    declared = h.contract("tests.composition", "declared_erasure_authority")
    store, index, registry, address = _shared_site(tmp_path)
    acme_only = trust_type(authorities={h.TENANT: declared(h.TENANT)})
    composed.erase(store, index, address, control_plane=registry, tenant=OTHER, authority=declared(OTHER))
    entry = index.lookup(tenant_id=OTHER, content_address=address)
    with pytest.raises(h.erasure("ErasureRecordInvalid")) as refused:
        h.erasure("verify_erasure_entry")(
            entry, store.get(content_address=entry.erasure_record_address), trust=acme_only,
            identity_provider=h.erasure("reference_approval_verifier")(),
        )
    assert refused.value.reason_code == "erasure-tenant-undeclared"
    tenantless = h.erasure("compose_erasure_consult")(
        store, index=index, audit_log=registry.audit_log, clock=h.fabric_clock, control_plane=registry,
        erasure_trust=acme_only,
    )
    with pytest.raises(h.erasure("ErasedContentRefused")) as withheld:
        tenantless.scoped(OTHER).get(content_address=address)
    assert withheld.value.reason == "index-unsupported"


def test_r4_the_trust_is_keyed_by_each_authoritys_own_tenant(tmp_path: Path) -> None:
    from pydantic import ValidationError

    plane = h.compose(tmp_path)
    with pytest.raises(ValidationError):
        _trust(_authority(plane)).model_validate({"authorities": {OTHER: _authority(plane)}})
    with pytest.raises(ValidationError):  # ruling 1: the HITL key lives in its authority's tenant
        _authority(plane, hitl_key=f"{OTHER}/hitl/erasure-attestation-policy")


# -- E. R5: the untested branches, and the door's key ------------------------------


class _UnrecordedRegistration:
    """The plane's Control Plane, whose audit plane omits ONE registration."""

    def __init__(self, inner: ControlPlaneRegistry, *, key: str, version: str) -> None:
        self._inner = inner
        self._key = key
        self._version = version

    def audit_events(self) -> Any:
        return tuple(
            e for e in self._inner.audit_events()
            if not (e.action.startswith("register") and e.key == self._key and e.version == self._version)
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_r5_a_supersession_with_no_recorded_instant_is_refused_by_name(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    old = _pin(plane)
    address = _plant(plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=old)
    _hitl_policy(plane.registry, plane.hitl_policy_key, {h.APPROVER: {"rotated-kid": signing.public_jwk(signing.forger_key_dir())}})
    successor = plane.registry.versions(plane.hitl_policy_key)[-1]
    assert _judgment(plane, address) == "supported"  # the control: the supersession instant is recorded
    forgetful = _UnrecordedRegistration(plane.registry, key=plane.hitl_policy_key, version=successor)
    assert _judgment(plane, address, cp=forgetful) == "approval-policy-window-unknown"


def test_r5_the_door_refuses_a_transport_bound_to_another_hitl_key(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    refused = h.erasure("ErasureCompositionRefused")
    elsewhere = InMemoryHitlTransport(
        control_plane=plane.registry, hitl_policy_key=f"{h.TENANT}/hitl/another-policy", identity_provider=signing.provider()
    )
    with pytest.raises(refused):
        _door(plane, transport=elsewhere)
    with pytest.raises(refused):  # a transport bound to no key at all
        _door(plane, transport=InMemoryHitlTransport(control_plane=plane.registry))
    _door(plane)  # the control: the plane's own transport is bound to the authority's key


def test_r5_the_docs_no_longer_claim_what_was_measured_false() -> None:
    def flat(page: str) -> str:
        return " ".join((REPO / page).read_text(encoding="utf-8").split())

    for page in (FRAGMENT, PAGE):
        text = flat(page)
        assert "registering any other key, in any tenant, no longer helps" not in text, page
        assert "cannot sign a new approval under the old one" not in text, page
    section = flat(PAGE).split("### 4.9", 1)[1].split(" ## ", 1)[0]  # up to the next level-2 heading
    assert "in-process adapter" in section
