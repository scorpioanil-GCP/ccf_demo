"""SEC-005, the remaining leg — the controls `D-IMPL-363` adds beyond the doors.

The two door suites (``tests/http_api/test_sec005_attestation_door.py``,
``tests/mcp/test_sec005_attestation_door.py``) pin the HTTP and MCP halves of
the signed-claims / time-window repair. This module pins the three properties
that are not a door's to demonstrate:

* **T10 — the admitting policy reaches replay.** A gate resolution under a
  required, attested submission carries the pinned ``key@version`` of the
  :class:`~ccf.hitl.transport.HitlPolicy` that admitted it, inside the
  ``hitl_actions_block``, and that block lands verbatim on replay dimension 2
  (``replay.policy_bindings.hitl_actions``). The recorded answer therefore
  says *which window and which keys* decided its admission, not merely that
  something was signed.
* **T11 — one verifier, no clock.** The transport site and a primitive site
  are the same :func:`~ccf.hitl.transport.enforce_attestation` invoked
  independently (D-13 — no trust marker crosses the seam), so verifying the
  SAME recorded submission at either site returns the same claims. The
  function takes no clock parameter at all: every comparison is between the
  signed claims, the capability, the door-minted binding and the pinned
  policy, which is what makes it deterministic across repeated calls and
  across a JSON round-trip of the recorded submission.
* **T12 — replay re-verification.** Re-running the verifier over the RECORDED
  submission, against the EXACT policy version the submission pins, reproduces
  the admission; a recorded attestation with one claim altered is refused. The
  two constructor guards that keep a claim set judgeable at all — a
  timezone-aware ``issued_at`` and a non-empty ``nonce`` — are pinned here too.

Fixture vocabulary is deployment vocabulary (CINV-01).
"""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey
from pydantic import ValidationError

from ccf.authz.capability import Authorized, HitlSubmit
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
from ccf.hitl.identity_binding import (
    HitlActionClaims,
    SignedHitlAction,
    sign_hitl_action,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlActionSubmission,
    HitlPolicy,
    InMemoryHitlTransport,
    PendingHitlEvent,
    SignedBindingInvalidRefused,
    enforce_attestation,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from tests.controlplane.composition import compose_register_typed

from .capabilities import submit_capability

APPROVER_KID = "sec005-approver-signing-key"
POLICY_KEY = "acme-bank/hitl/attestation-policy"
TENANT = "acme-bank"
SUBJECT = "credit-officer-7"
EVENT_KEY = "acme-bank/exec-hitl/sec005-gate"

#: The window this test-as-deployment states (CINV-01 — no SDK default).
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60

#: The door-minted instant the binding records. FIXED: the verifier windows
#: ``issued_at`` against THIS value and reads no clock, so nothing here races
#: a wall clock (`D-IMPL-363` C7).
ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)


# --- fixtures: keys, the ruled policy, a wired transport ---------------------


@pytest.fixture
def key_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "keys"
    directory.mkdir()
    key = ECKey.generate_key("P-256", parameters={"kid": APPROVER_KID})
    (directory / f"{APPROVER_KID}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return directory


@pytest.fixture
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


def _public_jwk(key_dir: Path, kid: str) -> JsonWebKey:
    private = json.loads((key_dir / f"{kid}.jwk").read_text(encoding="utf-8"))
    return ECKey.import_key(private).as_dict(private=False)


def _ruled_policy_document(key_dir: Path) -> dict[str, Any]:
    """The policy `D-IMPL-363` rules (E3, E5, C6(a)): the window and the
    per-subject trusted keys live INSIDE the pinned policy."""
    return {
        "semver": "1.0.0",
        "signed_binding_required": True,
        "signature_max_age_seconds": MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": SKEW_SECONDS,
        "trusted_keys": {SUBJECT: {APPROVER_KID: _public_jwk(key_dir, APPROVER_KID)}},
    }


@pytest.fixture
def plane(key_dir: Path) -> ControlPlaneRegistry:
    registry = ControlPlaneRegistry()
    policy = parse_artifact(_ruled_policy_document(key_dir), HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    compose_register_typed(registry, POLICY_KEY, policy, HITL_POLICY)
    return registry


@pytest.fixture
def transport(
    plane: ControlPlaneRegistry, provider: DetachedJwsIdentityProvider
) -> InMemoryHitlTransport:
    return InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )


def _authorized(event_key: str = EVENT_KEY) -> Authorized[HitlSubmit]:
    return submit_capability(
        tenant=TENANT, principal=SUBJECT, event_key=event_key
    )


def _binding(product_content_hash: str) -> HumanPrincipalBinding:
    return HumanPrincipalBinding(
        verdict="approve",
        approver=ApproverIdentity(
            subject_id=SUBJECT, identity_provider_ref="oidc:acme-bank-sso"
        ),
        authentication=AuthenticationContext(
            method="oidc", assurance_level="aal2", session_ref="session-01HZX"
        ),
        action_time=ACTION_TIME,
        product_content_hash=product_content_hash,
    )


def _claims(
    *,
    product_content_hash: str,
    event_key: str = EVENT_KEY,
    action: str = "approve",
    issued_at: datetime = ACTION_TIME,
    nonce: str = "nonce-sec005-controls-1",
) -> HitlActionClaims:
    return HitlActionClaims(
        tenant=TENANT,
        event_key=event_key,
        action=action,
        product_content_hash=product_content_hash,
        subject_id=SUBJECT,
        issued_at=issued_at,
        nonce=nonce,
    )


def _attest(
    claims: HitlActionClaims, provider: DetachedJwsIdentityProvider
) -> SignedHitlAction:
    return sign_hitl_action(claims, provider=provider, key_id=APPROVER_KID)


def _pending_event() -> PendingHitlEvent:
    document = {
        "event_key": EVENT_KEY,
        "event_class": "approval-gate",
        "tenant": TENANT,
        "workflow_state_ref": "acme-bank/exec-hitl",
    }
    return PendingHitlEvent(
        **document, product_content_hash=content_hash(document)
    )


def _ticking_clock() -> Any:
    """A clock that advances on every read — the gate's audit stamps move, the
    verifier's judgement does not (`D-IMPL-363` C7)."""
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _resolve_attested_gate(
    transport: InMemoryHitlTransport,
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    *,
    issued_at: datetime = ACTION_TIME,
) -> tuple[GateResolution, SignedHitlAction, PendingHitlEvent]:
    """Drive one gate resolution under a required, attested submission."""
    gate = ApprovalGate(
        transport=transport,
        audit=AuditLog(),
        clock=_ticking_clock(),
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )
    event = _pending_event()
    transport.enqueue(event=event)
    principal = _binding(event.product_content_hash)
    attestation = _attest(
        _claims(
            product_content_hash=event.product_content_hash,
            issued_at=issued_at,
        ),
        provider,
    )
    resolution = gate.resolve(
        _authorized(),
        event_key=event.event_key,
        action="approve",
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, GateResolution)
    return resolution, attestation, event


# --- the replay-record builder (the 07-07 slice shape, as test_replay_e2e) ---


def _replay_record(*, hitl_actions: str | None) -> DecisionReplayRecord:
    """The 07-07 slice's builder shape, threading a primitive's verbatim block
    through the ``hitl_actions`` keyword into dimension 2."""
    boundary = datetime(2026, 2, 1, tzinfo=UTC)
    execution = ExecutionResult(
        plan_id="plan-1",
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id="plan-1", payload={"k": "v"}),
        view=GraphView(tenant_id=TENANT, as_of=boundary),
    )
    product = ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id=TENANT,
        temporal_boundary=boundary,
        expires_at=datetime(2026, 4, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=boundary,
        ),
        payload={"k": "v"},
    )
    return build_replay_record(
        execution=execution,
        product=product,
        perspective=Perspective(principal_id="principal-1", role="analyst"),
        policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
        assembly_mode="algorithmic",
        recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        hitl_actions=hitl_actions,
    )


# --- T10: the admitting policy reaches dimension 2 ---------------------------


def test_t10_the_admitting_policy_pin_reaches_replay_dimension_2(
    transport: InMemoryHitlTransport,
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """`D-IMPL-363` E3: the recorded submission names the policy that admitted
    it, the gate's ``hitl_actions_block`` carries that recorded submission, and
    the block lands verbatim on ``replay.policy_bindings.hitl_actions``. So the
    replay record answers *which window and which keys* decided this
    admission."""
    resolution, attestation, event = _resolve_attested_gate(
        transport, plane, provider
    )
    (recorded,) = transport.submissions(tenant=TENANT)
    # The transport stamped the pin; the caller did not author it.
    assert recorded.hitl_policy_ref is not None
    key, _, version = recorded.hitl_policy_ref.partition("@")
    assert key == POLICY_KEY
    assert version
    # The resolution block embeds the RECORDED submission, pin included.
    assert recorded.hitl_policy_ref in resolution.hitl_actions_block
    assert attestation.signature in resolution.hitl_actions_block
    # ... and the block lands byte-for-byte on dimension 2.
    replay = _replay_record(hitl_actions=resolution.hitl_actions_block)
    assert replay.policy_bindings.hitl_actions == resolution.hitl_actions_block
    assert recorded.hitl_policy_ref in replay.policy_bindings.hitl_actions
    # The record round-trips to its typed form with the pin intact.
    from ccf.hitl.approval_gate import HitlActionRecord

    rehydrated = HitlActionRecord.model_validate_json(
        replay.policy_bindings.hitl_actions
    )
    assert rehydrated.submission.hitl_policy_ref == recorded.hitl_policy_ref
    assert rehydrated.submission.attestation == attestation
    assert rehydrated.event == event


# --- T11: one verifier, no clock, deterministic ------------------------------


def test_t11_enforce_attestation_takes_no_clock_parameter() -> None:
    """`D-IMPL-363` E2: the shared verifier reads NO clock. Not "reads a clock
    it is given" — there is no parameter through which one could be supplied,
    which is what makes the transport site (which has no clock) and a replay
    judge identically."""
    signature = inspect.signature(enforce_attestation)
    assert set(signature.parameters) == {
        "authorized",
        "submission",
        "identity_provider",
        "policy",
    }


def test_t11_transport_and_primitive_sites_verify_one_recorded_submission_identically(
    transport: InMemoryHitlTransport,
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """D-13 / E2: the primitive and the transport invoke ONE verifier
    independently, with no marker passing between them. Re-verifying the same
    recorded submission returns the same claims every time — twice in a row,
    and after the submission has been through a JSON round-trip, which is the
    shape a stored record comes back in."""
    _resolution, attestation, _event = _resolve_attested_gate(
        transport, plane, provider
    )
    (recorded,) = transport.submissions(tenant=TENANT)
    assert recorded.hitl_policy_ref is not None
    policy = plane.resolve(POLICY_KEY, recorded.hitl_policy_ref.split("@", 1)[1])
    assert isinstance(policy, HitlPolicy)

    def verify_once(submission: HitlActionSubmission) -> HitlActionClaims:
        return enforce_attestation(
            _authorized(),
            submission,
            identity_provider=provider,
            policy=policy,
        )

    first = verify_once(recorded)
    second = verify_once(recorded)
    assert first == second == attestation.claims
    # Through a JSON round-trip: identical bytes in, identical claims out.
    rehydrated = HitlActionSubmission.model_validate_json(
        recorded.model_dump_json()
    )
    assert rehydrated == recorded
    assert verify_once(rehydrated) == first


# --- T12: replay re-verification, and the claim-set constructor guards -------


def test_t12_replay_re_verification_reproduces_the_admission(
    transport: InMemoryHitlTransport,
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """`D-IMPL-363` E3: replay resolves the EXACT pinned policy version — never
    "latest" — and re-running the verifier over the recorded submission
    reproduces the admission it recorded."""
    _resolution, attestation, _event = _resolve_attested_gate(
        transport, plane, provider
    )
    (recorded,) = transport.submissions(tenant=TENANT)
    assert recorded.hitl_policy_ref is not None
    key, _, version = recorded.hitl_policy_ref.partition("@")
    pinned = plane.resolve(key, version)
    assert isinstance(pinned, HitlPolicy)
    reproduced = enforce_attestation(
        _authorized(),
        recorded,
        identity_provider=provider,
        policy=pinned,
    )
    assert reproduced == attestation.claims


def test_t12_a_tampered_recorded_attestation_is_refused_on_replay(
    transport: InMemoryHitlTransport,
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """One claim altered on the stored record — the signature no longer covers
    the claims the verifier recomputes — and the replay refuses rather than
    reporting the admission it never granted."""
    _resolution, attestation, _event = _resolve_attested_gate(
        transport, plane, provider
    )
    (recorded,) = transport.submissions(tenant=TENANT)
    assert recorded.hitl_policy_ref is not None
    pinned = plane.resolve(
        POLICY_KEY, recorded.hitl_policy_ref.split("@", 1)[1]
    )
    assert isinstance(pinned, HitlPolicy)
    tampered_claims = attestation.claims.model_copy(
        update={
            "product_content_hash": hashlib.sha256(b"another-product").hexdigest()
        }
    )
    tampered = recorded.model_copy(
        update={
            "attestation": attestation.model_copy(
                update={"claims": tampered_claims}
            )
        }
    )
    with pytest.raises(SignedBindingInvalidRefused):
        enforce_attestation(
            _authorized(),
            tampered,
            identity_provider=provider,
            policy=pinned,
        )


def test_t12_the_claim_set_refuses_a_naive_instant_and_an_empty_nonce() -> None:
    """The two constructor guards that keep a claim set judgeable at all
    (`D-IMPL-363` C7; D-IMPL-38): a naive ``issued_at`` would be windowed in
    whatever zone the reader assumed, and an empty ``nonce`` cannot be the
    single-admission key the transport refuses a reuse of."""
    good = _claims(product_content_hash=content_hash({"product": "seen"}))
    assert isinstance(good, CCFContract)
    with pytest.raises(ValidationError, match="timezone-aware"):
        HitlActionClaims(
            tenant=TENANT,
            event_key=EVENT_KEY,
            action="approve",
            product_content_hash=good.product_content_hash,
            subject_id=SUBJECT,
            issued_at=datetime(2026, 7, 30, 12, 0, 0),
            nonce="nonce-naive",
        )
    with pytest.raises(ValidationError, match="cannot be empty"):
        HitlActionClaims(
            tenant=TENANT,
            event_key=EVENT_KEY,
            action="approve",
            product_content_hash=good.product_content_hash,
            subject_id=SUBJECT,
            issued_at=ACTION_TIME,
            nonce="",
        )
