"""SEC-009 fix round 4, rulings 1–6 — the requester never chooses the trust root (`D-IMPL-374` (4)).

The re-review's twelve probes, each asserting its defect is ABSENT, plus the
ruling-5 composition refusals and the production restart shape:

1. **The HITL policy key is fixed at composition.** The consult takes the
   deployment's key and refuses, by name, an approval naming any other key
   (a policy the forger registered; a policy in another tenant's key space).
2. **Approver ≠ requester, and approver eligible** under the approval policy
   the record names, resolved at its exact version — the transport's door rule
   applied again at the consult.
3. **The gate is the workflow definition's.** The consult resolves the
   definition by ``workflow_definition_hash`` and requires ``approval.gate`` to
   be one of its HITL gates, bound to the record's approval policy.
4. **Revocation.** A signature dated after the pinned version's supersession
   refuses; an approval made while that version was current stays valid; the
   validation cache is keyed by the Control Plane's policy HEAD, so a
   registration invalidates a cached verdict and the global memo.
5. **No fresh-registry fallback**, and re-composition with a different Control
   Plane, identity provider or HITL policy key refuses by name.
6. An adopter-supplied provider that verifies nothing accepts everything — the
   adopter's trust choice, stated in the fragment and §4.10.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.principal import ApproverIdentity
from ccf.hitl.transport import HITL_POLICY
from tests.composition import register_typed_at_composition
from tests.erasure import composed
from tests.erasure import harness as h
from tests.erasure import signing
from tests.erasure.test_sec009_fix2 import _entry, _forged_record
from tests.hitl.sec006_harness import register_typed_policy

GATE = "erasure-approval"
APPROVAL_POLICY_URI = "ccf-artifact://acme-bank/approval-policy/erasure-officers@1.0.0"
REPO = Path(__file__).resolve().parents[2]


def _compose(plane: h.Plane, *, cp: Any = None, provider: Any = None, trust: Any = None) -> tuple[Any, Any]:
    audit = ControlPlaneRegistry().audit_log
    kw: dict[str, Any] = {} if provider is None else {"identity_provider": provider}
    consulted = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=audit, clock=h.fabric_clock,
        control_plane=cp or plane.registry, tenant_id=h.TENANT,
        erasure_trust=h.trust(plane) if trust is None else trust, **kw,
    )
    return consulted, audit


def _outcome(plane: h.Plane, address: str, *, consulted: Any = None, **kw: Any) -> str:
    """``supported`` when the record's own reason is served; else ``unsupported``."""
    if consulted is None:
        consulted, _audit = _compose(plane, **kw)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=address)
    return "supported" if refused.value.reason == composed.REASON else f"unsupported({refused.value.reason})"


def _plant(
    plane: h.Plane,
    request: Any,
    *,
    subject: str,
    directory: Path,
    policy_ref: str,
    tenant_claim: str = h.TENANT,
    action: str = "approve",
    event_key: str | None = None,
    gate: str = GATE,
    requested_by: str = h.REQUESTER,
    issued_at: Any = None,
    definition_hash: str | None = None,
) -> str:
    """File an approval, an entry and a record naming it, under the requester's capability — and,
    the strongest forger (fix round 5), the GENUINE door key, so the judgment each test names
    is what refuses, never the door signature."""
    issued = h.fabric_clock() if issued_at is None else issued_at
    attestation = signing.sign(
        tenant=tenant_claim, event_key=event_key or f"{h.TENANT}/{request.request_id}/{gate}",
        product_content_hash="1" * 64, subject_id=subject, issued_at=issued, action=action, directory=directory,
    )
    actor = ApproverIdentity(subject_id=subject, identity_provider_ref="x")
    approval = h.erasure("ErasureApproval")(
        tenant_id=h.TENANT, request_id=request.request_id, approver=actor, verdict="approve",
        acted_at=issued, gate=gate, gate_state_hash="1" * 64,
        workflow_definition_hash=plane.definition_version if definition_hash is None else definition_hash,
        submission_hash="3" * 64, attestation=attestation, hitl_policy_ref=policy_ref,
    )
    address = plane.document.content_address
    filed = plane.store.put(
        h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_APPROVAL_CLASS, name="planted", artifact=approval)
    )
    record = _forged_record(
        request, address, approval_ref=filed.content_address, actor=actor, requested_by=requested_by,
    )
    h.index_of(plane).append(h.erase_cap(request), _entry(request, address, content_hash(record), record=record, approval_ref=filed.content_address))
    plane.store.put(h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="f" * 64, artifact=record))
    return address


def _hitl_policy(registry: ControlPlaneRegistry, key: str, trusted: dict[str, Any]) -> str:
    """Register a signed HitlPolicy under ``key`` and return its ``key@version`` pin."""
    policy = parse_artifact(
        {"semver": "1.0.0", "signed_binding_required": True, "signature_max_age_seconds": 300,
         "permitted_clock_skew_seconds": 60, "trusted_keys": trusted}, HITL_POLICY,
    )
    register_typed_at_composition(registry, key, policy, HITL_POLICY)
    version, _ = registry.resolve_latest(key)
    return f"{key}@{version}"


def _pin(plane: h.Plane) -> str:
    return signing.policy_ref(plane.registry, plane.hitl_policy_key)


# -- the probes, inverted ------------------------------------------------------------


def test_control_a_genuine_shaped_plant_by_the_pinned_key_is_supported(tmp_path: Path) -> None:
    """Positive control: every ruling satisfied, the real pinned key — SUPPORTED."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=_pin(plane))
    assert _outcome(plane, address) == "supported"


def test_a_the_strongest_forger_is_unsupported(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.forger_key_dir(), policy_ref=_pin(plane))
    assert _outcome(plane, address).startswith("unsupported")


@pytest.mark.parametrize(
    "kw", [dict(action="reject"), dict(tenant_claim="other-bank"), dict(event_key="acme-bank/another-request/" + GATE)]
)
def test_b_a_real_signature_over_wrong_claims_is_unsupported(tmp_path: Path, kw: dict[str, Any]) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=_pin(plane), **kw)
    assert _outcome(plane, address).startswith("unsupported")


def test_b_a_gate_the_workflow_definition_does_not_declare_is_unsupported(tmp_path: Path) -> None:
    """Ruling 3: a real signature over ``{tenant}/{request}/<any name>`` approves nothing."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=_pin(plane), gate="not-a-gate-of-this-workflow")
    assert _outcome(plane, address).startswith("unsupported")


def test_b_a_workflow_definition_hash_the_control_plane_does_not_hold_is_unsupported(tmp_path: Path) -> None:
    """Ruling 3 (and fix round 5, R1): the gate is bound to the DECLARED definition, fixed at
    composition by hash, not to free text — any other hash is refused."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=_pin(plane), definition_hash="2" * 64)
    assert _outcome(plane, address).startswith("unsupported")


def test_c1_a_policy_the_forger_registered_in_the_same_tenant_is_unsupported(tmp_path: Path) -> None:
    """Ruling 1: the requester's artifact may name the version, never the key."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    forger = signing.forger_key_dir()
    ref = _hitl_policy(plane.registry, "acme-bank/sandbox/alice-scratch-policy", {h.APPROVER: {signing.APPROVER_KID: signing.public_jwk(forger)}})
    address = _plant(plane, request, subject=h.APPROVER, directory=forger, policy_ref=ref)
    assert _outcome(plane, address).startswith("unsupported")


def test_c2_a_policy_in_another_tenants_key_space_is_unsupported(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    forger = signing.forger_key_dir()
    ref = _hitl_policy(plane.registry, "evil-tenant/hitl/policy", {h.APPROVER: {signing.APPROVER_KID: signing.public_jwk(forger)}})
    address = _plant(plane, request, subject=h.APPROVER, directory=forger, policy_ref=ref)
    assert _outcome(plane, address).startswith("unsupported")


def test_c2_the_consult_refuses_a_deployment_key_outside_the_approvals_tenant(tmp_path: Path) -> None:
    """Ruling 1, second clause: even the composed key must be in the approval's tenant — refused
    now at COMPOSITION (fix round 5, R4): an authority's HITL key lies under its own tenant, and
    an approval in any other tenant is refused by name (R1)."""
    from pydantic import ValidationError

    plane = h.compose(tmp_path)
    foreign = "evil-tenant/hitl/erasure-attestation-policy"
    with pytest.raises(ValidationError, match="does not lie under tenant"):
        h.erasure("ErasureAuthority")(
            tenant_id=h.TENANT, hitl_policy_key=foreign,
            workflow_definition_hash=plane.definition_version, door_keys=signing.door_keys(),
        )


def test_c3_self_approval_by_a_legitimately_pinned_requester_is_unsupported(tmp_path: Path) -> None:
    """Ruling 2: the requester holds a pinned key in the deployment's OWN policy and signs for her own request."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    alice = signing.forger_key_dir()
    ref = _hitl_policy(
        plane.registry, plane.hitl_policy_key,
        {h.APPROVER: {signing.APPROVER_KID: signing.public_jwk()}, h.REQUESTER: {signing.APPROVER_KID: signing.public_jwk(alice)}},
    )
    address = _plant(plane, request, subject=h.REQUESTER, directory=alice, policy_ref=ref, requested_by=h.REQUESTER)
    assert _outcome(plane, address).startswith("unsupported")


def test_c3_an_approver_the_approval_policy_does_not_name_is_unsupported(tmp_path: Path) -> None:
    """Ruling 2: pinned in the HITL policy, but not eligible under the record's approval policy."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    dave = signing.forger_key_dir()
    ref = _hitl_policy(
        plane.registry, plane.hitl_policy_key,
        {h.APPROVER: {signing.APPROVER_KID: signing.public_jwk()}, "dave": {signing.APPROVER_KID: signing.public_jwk(dave)}},
    )
    address = _plant(plane, request, subject="dave", directory=dave, policy_ref=ref)
    assert _outcome(plane, address).startswith("unsupported")


class _AcceptAll:
    def verify(self, *, signed: Any, public_keys: Any) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)


def test_d_an_adopter_provider_that_verifies_nothing_accepts_everything_and_the_docs_say_so(tmp_path: Path) -> None:
    """Ruling 6: the adopter's trust choice — stated where an adopter reads."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.forger_key_dir(), policy_ref=_pin(plane))
    assert _outcome(plane, address, provider=_AcceptAll()) == "supported"
    sentence = "verifies nothing accepts everything"
    for page in ("docs/surface-changes/374-04-sec-009-minimum-erasure.md", "public/how-to/security-and-deployment.md"):
        assert sentence in " ".join((REPO / page).read_text(encoding="utf-8").split()), page  # wrap-tolerant


# -- ruling 4: revocation and the cache ---------------------------------------------


def _rotate(plane: h.Plane) -> Any:
    """Register a NEXT version of the deployment's HITL policy that drops the approver's key; return its registration instant."""
    _hitl_policy(plane.registry, plane.hitl_policy_key, {h.APPROVER: {"rotated-kid": signing.public_jwk(signing.forger_key_dir())}})
    versions = plane.registry.versions(plane.hitl_policy_key)
    return next(
        e.occurred_at for e in plane.registry.audit_events()
        if e.action.startswith("register") and e.resolved and e.key == plane.hitl_policy_key and e.version == versions[-1]
    )


def test_f_a_signature_dated_after_supersession_under_a_dropped_key_is_unsupported(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    old = _pin(plane)
    superseded_at = _rotate(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=old, issued_at=superseded_at + timedelta(hours=1))
    assert _outcome(plane, address).startswith("unsupported")


def test_f_an_approval_made_while_the_old_version_was_current_stays_valid(tmp_path: Path) -> None:
    """Replay determinism: the rotation does not unmake an approval that was genuine when given."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    old = _pin(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=old, issued_at=h.fabric_clock())
    assert _outcome(plane, address) == "supported"
    _rotate(plane)
    assert _outcome(plane, address) == "supported"


def test_f_a_cached_verdict_does_not_survive_a_policy_registration(tmp_path: Path) -> None:
    """The validation cache is keyed by the policy HEAD: a registration re-judges the same consult object."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    old = _pin(plane)
    # Dated AHEAD of the registry clock: supported while the pinned version is
    # current (open-ended), refused once a later registration supersedes it.
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=old, issued_at=h.fabric_clock() + timedelta(days=1))
    consulted, _audit = _compose(plane)
    assert _outcome(plane, address, consulted=consulted) == "supported"
    _rotate(plane)
    assert _outcome(plane, address, consulted=consulted).startswith("unsupported")


class _Counting:
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.reads: list[str] = []

    def get(self, *, content_address: str) -> bytes:
        self.reads.append(content_address)
        return self.inner.get(content_address=content_address)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def test_f_the_global_memo_is_keyed_by_the_policy_head_not_the_control_plane_identity(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(plane, request, subject=h.APPROVER, directory=signing.key_dir(), policy_ref=_pin(plane))
    counting = _Counting(plane.store)
    compose = h.erasure("compose_erasure_consult")

    def fresh() -> None:
        compose(counting, index=h.index_of(plane), audit_log=ControlPlaneRegistry().audit_log, clock=h.fabric_clock,
                control_plane=plane.registry, tenant_id=h.TENANT, erasure_trust=h.trust(plane))

    fresh()
    fresh()
    assert counting.reads.count(address) == 0 and len(counting.reads) == 2, counting.reads  # record + approval, once
    _rotate(plane)
    fresh()
    assert len(counting.reads) == 4, counting.reads  # re-validated after the registration


# -- ruling 5: no fresh-registry fallback, no silent re-composition ------------------


def test_the_consult_refuses_to_compose_without_the_deployments_control_plane(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    with pytest.raises(h.erasure("ErasureCompositionRefused")):
        h.erasure("compose_erasure_consult")(
            plane.store, index=h.index_of(plane), audit_log=plane.registry.audit_log, clock=h.fabric_clock,
            control_plane=None, tenant_id=h.TENANT, erasure_trust=h.trust(plane),
        )


def test_open_product_has_no_fresh_registry_fallback(tmp_path: Path) -> None:
    from tests.products import test_paved_road as pr

    root = pr._write_tree(tmp_path)
    with pytest.raises(h.erasure("ErasureCompositionRefused")):
        pr._open(root, tmp_path / "scratch", control_plane=None)


@pytest.mark.parametrize("axis", ["control_plane", "identity_provider", "erasure_trust"])
def test_recomposing_a_composed_store_with_a_different_trust_root_refuses_by_name(tmp_path: Path, axis: str) -> None:
    plane = h.compose(tmp_path)
    compose = h.erasure("compose_erasure_consult")
    arguments: dict[str, Any] = dict(
        index=h.index_of(plane), audit_log=plane.registry.audit_log, clock=h.fabric_clock,
        control_plane=plane.registry, tenant_id=h.TENANT, erasure_trust=h.trust(plane),
    )
    store = compose(plane.store, **arguments)
    assert compose(store, **arguments) is store
    assert compose(store, **{**arguments, "erasure_trust": h.trust(plane)}) is store  # an EQUAL trust is the same root
    different = {
        "control_plane": ControlPlaneRegistry(),
        "identity_provider": _AcceptAll(),
        "erasure_trust": h.erasure("ErasureTrust")(authorities={}),
    }
    with pytest.raises(h.erasure("ErasureCompositionRefused")):
        compose(store, **{**arguments, axis: different[axis]})


# -- the production restart shape ---------------------------------------------------


def test_a_genuine_erasure_stays_supported_through_a_restart_whose_clock_is_later(tmp_path: Path) -> None:
    """The deployment restarts, re-registers the same policy versions at a LATER
    instant, and reopens the index: the approval it made before the restart is
    still SUPPORTED. (The measurement behind ruling 4's lower bound.)"""
    from tests.workflow import test_engine as eh

    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    approval = h.erasure("ErasureApproval").model_validate_json(plane.store.get(content_address=record.approval_ref))
    ticking = eh._ticking_clock()

    def later() -> Any:  # the restarted registry's clock is a day past the approval's instant
        return ticking() + timedelta(days=1)

    assert later() > approval.acted_at
    restarted = ControlPlaneRegistry(clock=later)
    signing.register_signed_policy(restarted, subject=h.APPROVER)
    register_typed_policy(restarted, h.APPROVAL_KEY, eligible=frozenset({h.APPROVER}))
    composed.register_erasure_workflow(restarted, tenant=h.TENANT)
    assert _outcome(plane, plane.document.content_address, cp=restarted) == "supported"
