"""SEC-006 — approver eligibility at the transport and the primitive (`D-IMPL-366`).

RED-FIRST on `main` @ `a236e6ce`, the `D-IMPL-363` shape: every control here is
written to the RULED surface (the SEC-006 brief, revision 3, adopted at
`D-IMPL-366` and its H1–H3 amendment) and fails today for exactly one of two
reasons, named in the failure message:

- **MISSING CONTRACT** — a ruled name or field the tree does not have yet
  (``ccf.hitl.APPROVAL_POLICY`` / ``ApprovalPolicy``, ``PendingHitlEvent
  .requested_by``, the three stamped submission fields).
- **BEHAVIORAL** — the tree admits what the ruling says it must refuse, or
  refuses what it must admit.

Nothing fails at import, collection or fixture setup. Controls marked GREEN
are preservation controls: they pass today and must still pass after the
repair, which is what makes the red ones independent (brief §5, "how the
other sites cannot mask it").

Sites covered here, by the brief's row names: **S1** (transport ``submit``,
T1 and its variants), **S2** (``ApprovalGate.resolve``, T3), **S6**
(``ApprovalPolicy``, T7/T7b), **R1** (the primitive-path record, T8/R1b),
**R2** (the door-path record, T9), **R3** (the pin, T10), **C** (the
revalidation before consumption, T11/T14) and the carried requirement (1)
(caller-supplied audit stamps are overwritten).

Harness reuse (Dave's GO): :mod:`tests.hitl.test_approval_gate` is imported as
a namespace for its fixture helpers — never its test functions — and the
shared SEC-006 harness in :mod:`tests.hitl.sec006_harness` carries the ruled
names. No existing test or fixture is modified; everything here is added
beside them.

Test vocabulary only (CINV-01): no subject, key or tenant here names a real
principal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalGate, GateResolution, GateResolutionRefused
from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport, PendingHitlEvent
from tests.hitl import test_approval_gate as gate_harness
from tests.hitl.capabilities import submit_capability
from tests.hitl.sec006_harness import (
    ELIGIBILITY_CODE,
    REFUSAL_TYPE,
    RemoveSpy,
    contract,
    door_submission,
    expect_eligibility_refusal,
    field,
    plain_hitl_plane,
    register_declared_policy,
    register_typed_policy,
    submit_as,
    transport_state,
)
from tests.replay import test_dimension_extensions as replay_harness

#: The fixture event's own policy key — a DeclaredArtifact today (the
#: pre-change shape every fixture registers), which the ruling makes a
#: WRONG-CLASS policy ref on a bound transport (brief §4 (3): "resolves to
#: something other than an ApprovalPolicy").
FIXTURE_POLICY_KEY = "acme-bank/approval-policy/credit-officer"
TYPED_POLICY_KEY = "acme-bank/approval-policy/sec006-officers"
PIN_POLICY_KEY = "acme-bank/approval-policy/sec006-pin"
_UNSET = object()


# --- local helpers ------------------------------------------------------------


def _gate_event(
    fixture: dict[str, Any],
    *,
    policy_ref: Any = _UNSET,
    requested_by: Any = _UNSET,
    event_class: Any = _UNSET,
    event_key: Any = _UNSET,
) -> PendingHitlEvent:
    """The fixture's pending event, with ruled-surface overrides.

    ``requested_by`` is the RULED field (`D-IMPL-366` G1; brief §4 (2)); a
    tree without it refuses the keyword at the contract boundary
    (``extra=forbid``), which this helper reports as the MISSING CONTRACT it
    is rather than letting a ``ValidationError`` escape as an ERROR.
    """
    document = dict(fixture["event"])
    if policy_ref is not _UNSET:
        document["policy_ref"] = policy_ref
    if event_class is not _UNSET:
        document["event_class"] = event_class
    if event_key is not _UNSET:
        document["event_key"] = event_key
    if requested_by is not _UNSET:
        document["requested_by"] = requested_by
    try:
        return PendingHitlEvent(**document, product_content_hash=content_hash(document))
    except ValidationError as error:
        if requested_by is not _UNSET and "requested_by" in str(error):
            pytest.fail(
                "MISSING CONTRACT: PendingHitlEvent.requested_by (D-IMPL-366 G1;"
                f" brief §4 (2)) does not exist on this tree: {error}"
            )
        raise


def _bound_transport(
    plane: ControlPlaneRegistry, **kwargs: Any
) -> tuple[InMemoryHitlTransport, str]:
    """A transport bound to ``plane`` under a plain (unsigned) HITL policy, so
    the only NEW judgment on the served path is eligibility (brief §5, S1)."""
    hitl_key = plain_hitl_plane(plane)
    return (
        InMemoryHitlTransport(control_plane=plane, hitl_policy_key=hitl_key, **kwargs),
        hitl_key,
    )


def _principal_for(fixture: dict[str, Any], event: PendingHitlEvent) -> Any:
    return gate_harness._principal(fixture, product_content_hash=event.product_content_hash)


# --- S1: the transport refuses at `submit` (T1 and variants) ------------------


def test_t1_bound_transport_refuses_a_wrong_class_policy_ref() -> None:
    """S1, T1d (wrong class) — BEHAVIORAL today.

    The fixture event names the ``credit-officer`` approval policy, which every
    fixture registers today as an UNTYPED ``DeclaredArtifact`` whose
    ``approver_role`` and ``quorum`` no code reads. Under the ruling a bound
    transport judges eligibility against a typed ``ccf.approval-policy``; a
    ref that resolves to anything else is a fail-closed refusal (brief §4
    (3)). Today the door-shaped submission is ADMITTED and recorded.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    register_declared_policy(plane, FIXTURE_POLICY_KEY)
    transport, _ = _bound_transport(plane)
    event = gate_harness._event(fixture)
    transport.enqueue(event=event)
    expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="credit-officer-11"),
        site="S1 transport.submit (wrong-class policy_ref)",
    )
    assert transport.submissions(tenant=event.tenant) == ()
    assert transport.pending(tenant=event.tenant) == (event,)


def test_t1_bound_transport_refuses_an_approval_gate_event_with_no_policy_ref() -> None:
    """S1, T1d (no policy) — BEHAVIORAL today.

    A bound approval-gate event with ``policy_ref=None`` has no policy to be
    eligible under; the ruling refuses rather than admitting an unjudged
    approval (brief §4 (3): "``policy_ref`` is ``None``").
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    transport, _ = _bound_transport(plane)
    event = _gate_event(fixture, policy_ref=None)
    transport.enqueue(event=event)
    expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="credit-officer-11"),
        site="S1 transport.submit (policy_ref=None)",
    )
    assert transport.submissions(tenant=event.tenant) == ()


def test_t1_bound_transport_refuses_an_unresolvable_policy_ref() -> None:
    """S1, T1d (unresolvable) — BEHAVIORAL today.

    A pinned ref to a key nothing was registered under resolves to nothing;
    the ruling refuses (brief §4 (3): "unresolvable"). Today nothing at
    ``submit`` reads the event at all, so the submission lands.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    transport, _ = _bound_transport(plane)
    event = _gate_event(
        fixture, policy_ref="ccf-artifact://acme-bank/approval-policy/nowhere@1.0.0"
    )
    transport.enqueue(event=event)
    expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="credit-officer-11"),
        site="S1 transport.submit (unresolvable policy_ref)",
    )
    assert transport.submissions(tenant=event.tenant) == ()


def test_t1_unbound_transport_admits_as_before() -> None:
    """GREEN preservation. No Control Plane bound: the pre-composition posture,
    no eligibility judgment (brief §4 (3): "Unbound ``control_plane`` → no
    check"). This is what makes T4 in the engine module independent of S1."""
    fixture = gate_harness._hitl()
    transport = InMemoryHitlTransport()
    event = gate_harness._event(fixture)
    transport.enqueue(event=event)
    recorded = submit_as(transport, event, subject_id="credit-officer-11")
    assert transport.submissions(tenant=event.tenant) == (recorded,)


def test_t1_bound_transport_does_not_judge_another_event_class() -> None:
    """GREEN preservation (G6 (a)). Eligibility is dispatched on the event
    class and judged for approval gates ONLY; an ``exception-escalation``
    event on a bound transport is admitted without judgment, whatever its
    ``policy_ref`` names (escalation is the named follow-on, brief §9)."""
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    register_declared_policy(plane, FIXTURE_POLICY_KEY)
    transport, _ = _bound_transport(plane)
    event = _gate_event(fixture, event_class="exception-escalation")
    transport.enqueue(event=event)
    recorded = submit_as(transport, event, subject_id="credit-officer-11")
    assert transport.submissions(tenant=event.tenant) == (recorded,)


def test_t1_bound_transport_refuses_a_principal_outside_the_policy() -> None:
    """S1, T1 — MISSING CONTRACT today (``ccf.hitl.APPROVAL_POLICY``).

    A typed policy naming ``officer-a``; ``officer-z`` submits a door-shaped
    approval. Refused ``ApproverNotEligible`` with the non-enumerating code
    (G3 (a)): the message names no eligible principal.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    typed_uri = register_typed_policy(plane, TYPED_POLICY_KEY, eligible=frozenset({"officer-a"}))
    transport, _ = _bound_transport(plane)
    event = _gate_event(fixture, policy_ref=typed_uri, requested_by="starter-1")
    transport.enqueue(event=event)
    refusal = expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="officer-z"),
        site="S1 transport.submit (principal not in eligible_principals)",
    )
    assert "officer-a" not in str(refusal), (
        f"the refusal enumerates an eligible principal (G3 (a) forbids it): {refusal}"
    )
    assert transport.submissions(tenant=event.tenant) == ()


def test_t1b_bound_transport_refuses_the_requester_approving_their_own_gate() -> None:
    """S1, T1b (self-approval) — MISSING CONTRACT today.

    ``officer-a`` is eligible AND is the recorded requester; requester ≠
    approver is unconditional whenever a policy is bound (RULED, brief §1).
    The message names no eligible principal — including the requester, who
    is one.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    typed_uri = register_typed_policy(
        plane, TYPED_POLICY_KEY, eligible=frozenset({"officer-a", "officer-b"})
    )
    transport, _ = _bound_transport(plane)
    event = _gate_event(fixture, policy_ref=typed_uri, requested_by="officer-a")
    transport.enqueue(event=event)
    refusal = expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="officer-a"),
        site="S1 transport.submit (requester == approver)",
    )
    assert "officer-b" not in str(refusal), f"enumerates an eligible principal: {refusal}"
    assert transport.submissions(tenant=event.tenant) == ()


def test_t1c_bound_transport_refuses_a_gate_event_with_no_requester() -> None:
    """S1, T1c (no ``requested_by``) — MISSING CONTRACT today.

    G5 (a): an approval-gate event with no recorded requester under a bound
    plane REFUSES at resolution (fail-closed) — the in-flight-suspension
    migration posture, stated in the migration note. The approver is
    eligible; the refusal is about the event, not the principal.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    typed_uri = register_typed_policy(plane, TYPED_POLICY_KEY, eligible=frozenset({"officer-a"}))
    transport, _ = _bound_transport(plane)
    event = _gate_event(fixture, policy_ref=typed_uri)  # no requested_by
    transport.enqueue(event=event)
    expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="officer-a"),
        site="S1 transport.submit (requested_by is None)",
    )
    assert transport.submissions(tenant=event.tenant) == ()


def test_t1d_eligibility_is_judged_before_attestation(tmp_path: Path) -> None:
    """S1 ordering, G2 (a) — the control the close panel found missing
    (D-IMPL-366 close panel A4; ruled into this follow-on by Dave, 2026-10-05).

    A bound transport whose HITL policy REQUIRES a signed attestation and whose
    gate event pins a typed approval policy. An INELIGIBLE principal submits
    with NO attestation. Two refusals apply; the ruling orders them:
    eligibility runs BEFORE ``enforce_attestation``, so the refusal is
    ``ApproverNotEligible`` — never ``SignedBindingRequiredRefused``. Severing:
    swap the eligibility block below the attestation block in
    ``InMemoryHitlTransport.submit`` — this test reddens with the
    signed-binding refusal.
    """
    fixture = gate_harness._hitl()
    provider, _kid, keys = gate_harness._signing_env(tmp_path)
    plane, policy_key, _ = gate_harness._required_policy_plane(
        subject_id=gate_harness._subject(fixture), keys=keys
    )
    typed_uri = register_typed_policy(plane, TYPED_POLICY_KEY, eligible=frozenset({"officer-a"}))
    transport = InMemoryHitlTransport(
        control_plane=plane, hitl_policy_key=policy_key, identity_provider=provider
    )
    event = _gate_event(fixture, policy_ref=typed_uri, requested_by="starter-1")
    transport.enqueue(event=event)
    refusal = expect_eligibility_refusal(
        lambda: submit_as(transport, event, subject_id="officer-z"),
        site="S1 transport.submit (ineligible AND unsigned under a signed-required policy)",
    )
    assert "officer-a" not in str(refusal)
    assert transport.submissions(tenant=event.tenant) == ()
    assert transport_state(transport)["nonces"] == frozenset()


# --- S2: the primitive refuses before the claim (T3) ---------------------------


def test_t3_primitive_refuses_before_the_atomic_claim() -> None:
    """S2, T3 — BEHAVIORAL today.

    With an ineligible resolution the primitive refuses **and ``remove`` was
    never called** — the delegating spy records every claim — and the event
    is still pending. If S2 were severed, the primitive would claim, ``submit``
    (S1) would refuse and the rollback would re-enqueue; the spy's
    "``remove`` never called" assertion is red regardless of S1, which is what
    makes this control independent (brief §5, S2).

    The fixture event's policy ref is the wrong class (a ``DeclaredArtifact``),
    so no typed policy is needed for the refusal — the control is BEHAVIORAL
    on today's tree rather than blocked on a missing name.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    register_declared_policy(plane, FIXTURE_POLICY_KEY)
    hitl_key = plain_hitl_plane(plane)
    spy = RemoveSpy(control_plane=plane, hitl_policy_key=hitl_key)
    gate = ApprovalGate(
        transport=spy,
        audit=AuditLog(),
        clock=gate_harness._clock(),
        control_plane=plane,
        hitl_policy_key=hitl_key,
    )
    event = gate_harness._event(fixture)
    spy.enqueue(event=event)
    try:
        outcome = gate.resolve(
            gate_harness._authorized(event.tenant, event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=_principal_for(fixture, event),
        )
    except PermissionError as error:
        assert type(error).__name__ == REFUSAL_TYPE, (
            f"refused, but by {type(error).__name__} rather than {REFUSAL_TYPE}"
            f" (D-IMPL-366 G3 (a)): {error}"
        )
    else:
        if isinstance(outcome, GateResolution):
            pytest.fail(
                "BEHAVIORAL: S2 ApprovalGate.resolve RESOLVED a gate whose policy"
                " ref is not a typed ccf.approval-policy; approver eligibility"
                f" must refuse before the claim (D-IMPL-366): {outcome.outcome!r}"
            )
        assert isinstance(outcome, GateResolutionRefused)
    assert spy.remove_calls == [], (
        f"the primitive took the atomic claim before refusing: {spy.remove_calls}"
    )
    assert spy.pending(tenant=event.tenant) == (event,)
    assert spy.submissions(tenant=event.tenant) == ()


# --- S6: the ApprovalPolicy contract (T7, T7b) ---------------------------------


def test_t7_an_empty_eligible_set_is_refused_at_construction() -> None:
    """S6, T7 — MISSING CONTRACT today (``ccf.hitl.ApprovalPolicy``).

    G7 (a): ``eligible_principals=frozenset()`` is a policy nobody can satisfy
    and is refused at construction, by name.
    """
    approval_policy = contract("ccf.hitl", "ApprovalPolicy", ruling="D-IMPL-366 §4 (1), G7 (a)")
    with pytest.raises(ValidationError) as refused:
        approval_policy(semver="1.0.0", eligible_principals=frozenset())
    assert "eligible_principals" in str(refused.value)


def test_t7b_the_approval_policy_class_is_not_manifest_addressable() -> None:
    """S6, T7b — GREEN today and after the repair.

    ``ccf.approval-policy`` is adopter-registered against its real contract
    and NOT manifest-addressable (RULED; the ``ccf.hitl-policy`` precedent in
    ``ccf.deployment.classes``). Today the id is refused because every unmapped
    ``ccf.`` id is (D-IMPL-84); after the repair it is refused because the
    class is deliberately kept out of the manifest roster. Either way the
    resolver raises — a manifest can never register one.
    """
    from ccf.deployment.classes import resolve_artifact_class

    try:
        resolved = resolve_artifact_class("ccf.approval-policy")
    except Exception:  # noqa: BLE001 — the refusal's type is the resolver's own
        return
    pytest.fail(
        "BEHAVIORAL: ccf.approval-policy resolved as a manifest-addressable class"
        f" ({resolved!r}); it is adopter-registered only (D-IMPL-366, RULED)"
    )


# --- R1: the primitive-path record (T8, R1b) ------------------------------------


def test_t8_the_resolution_block_carries_the_requester_and_the_policy_ref() -> None:
    """R1, T8 — MISSING CONTRACT today (``PendingHitlEvent.requested_by``).

    ``GateResolution.hitl_actions_block`` is the canonical serialization of the
    whole event plus the recorded submission; the event now carries
    ``requested_by`` beside ``policy_ref``, so a reader of dimension 2 can see
    who the self-approval rule compared against (brief §4 (7)). The gate is
    unbound here: the record shape is the subject, not any refusal.
    """
    fixture = gate_harness._hitl()
    gate, transport, _ = gate_harness._gate()
    event = _gate_event(fixture, requested_by="starter-7")
    transport.enqueue(event=event)
    resolution = gate.resolve(
        gate_harness._authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=_principal_for(fixture, event),
    )
    assert isinstance(resolution, GateResolution)
    block = json.loads(resolution.hitl_actions_block)
    assert block["event"]["policy_ref"] == event.policy_ref
    assert block["event"].get("requested_by") == "starter-7", (
        "MISSING CONTRACT: the hitl_actions_block's event carries no requested_by"
        f" (D-IMPL-366 G1; brief §5 R1): {sorted(block['event'])}"
    )


def test_r1b_the_block_lands_on_dimension_2_verbatim_with_the_policy_ref() -> None:
    """R1b — GREEN preservation. The primitive's pre-serialized block, threaded
    by the deployment into ``build_replay_record(hitl_actions=…)``, lands on
    dimension 2 byte-for-byte and already names the event's ``policy_ref``
    (the existing ``test_a_supplied_hitl_block_lands_on_dimension_2_verbatim``
    pattern, applied to a real gate's block)."""
    fixture = gate_harness._hitl()
    gate, transport, _ = gate_harness._gate()
    event = gate_harness._event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        gate_harness._authorized(event.tenant, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=_principal_for(fixture, event),
    )
    assert isinstance(resolution, GateResolution)
    block = resolution.hitl_actions_block
    record = replay_harness._build(hitl_actions=block)
    assert record.policy_bindings.hitl_actions == block
    assert event.policy_ref is not None and event.policy_ref in block


# --- R2: the door-path record (T9) ----------------------------------------------


def test_t9_the_recorded_door_submission_is_stamped_from_the_event() -> None:
    """R2, T9 — MISSING CONTRACT today (the three stamped fields).

    H3 (a) + the H2 requirement: the recorded submission carries
    ``approval_policy_ref == event.policy_ref``, ``requested_by ==
    event.requested_by`` and ``event_state_at_submit == "pending"`` — all
    hash-transparent, stamped by the transport from the event it found and
    revalidated (brief §4 (7), §4b step 6c). The transport is unbound: the
    stamp is a record fact, not a judgment, so it is written whether or not
    eligibility is in play.
    """
    fixture = gate_harness._hitl()
    transport = InMemoryHitlTransport()
    event = _gate_event(fixture, requested_by="starter-7")
    transport.enqueue(event=event)
    recorded = submit_as(transport, event, subject_id="credit-officer-11")
    assert field(recorded, "approval_policy_ref", ruling="D-IMPL-366 H3 (a)") == event.policy_ref
    assert field(recorded, "requested_by", ruling="D-IMPL-366 H3 (a)") == "starter-7"
    assert field(recorded, "event_state_at_submit", ruling="D-IMPL-366 H2") == "pending"


# --- R3: the pin (T10) ----------------------------------------------------------


def test_t10_eligibility_resolves_the_pinned_version_never_latest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R3, T10 — MISSING CONTRACT today (``ccf.hitl.APPROVAL_POLICY``).

    A later ``ApprovalPolicy`` version under the SAME key drops ``officer-b``;
    the event pinned ``@1.0.0`` at suspension, and the version that judges is
    the version the event pinned — replayable (brief §4 (3): "reads no clock
    and no latest"; ``resolve_pinned``). The deployment-wide ``HitlPolicy``
    IS resolved latest per call (E3), so the spy asserts that ``resolve_latest``
    is never asked for the APPROVAL-POLICY key, not that it is never called.
    """
    fixture = gate_harness._hitl()
    plane = ControlPlaneRegistry()
    pinned = register_typed_policy(
        plane, PIN_POLICY_KEY, eligible=frozenset({"officer-a", "officer-b"})
    )
    transport, _ = _bound_transport(plane)
    event = _gate_event(fixture, policy_ref=pinned, requested_by="starter-1")
    transport.enqueue(event=event)
    # The later version, a different content under the same key with a
    # different declared semver (two contents declaring one version would be
    # AmbiguousPinnedVersionError, by design).
    approval_policy_class = contract("ccf.hitl", "APPROVAL_POLICY", ruling="D-IMPL-366 §4 (1)")
    from ccf.controlplane.artifacts import parse_artifact
    from tests.composition import register_typed_at_composition

    register_typed_at_composition(
        plane,
        PIN_POLICY_KEY,
        parse_artifact(
            {"semver": "1.1.0", "eligible_principals": ["officer-a"]}, approval_policy_class
        ),
        approval_policy_class,
    )
    latest_calls: list[str] = []
    original = plane.resolve_latest

    def spy(key: str) -> Any:
        latest_calls.append(key)
        return original(key)

    monkeypatch.setattr(plane, "resolve_latest", spy)
    recorded = submit_as(transport, event, subject_id="officer-b")
    assert transport.submissions(tenant=event.tenant) == (recorded,)
    assert PIN_POLICY_KEY not in latest_calls, (
        f"the eligibility helper resolved the approval policy LATEST: {latest_calls}"
    )
    assert field(recorded, "approval_policy_ref", ruling="D-IMPL-366 H3 (a)") == pinned


# --- C: the revalidation before consumption (T11, T14) -------------------------


def _revalidation_arrangement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[InMemoryHitlTransport, Any, HitlActionSubmission, PendingHitlEvent, PendingHitlEvent]:
    """The second-suspension shape, serialized (carried requirement (3)).

    A signed-required policy for the fixture's credit officer; a bound
    transport; E1 pending under key K; a door-shaped signed submission for K.
    ``enforce_attestation`` is wrapped ONCE so that, between the transport's
    snapshot (E1, ``pending``) and its record, the SELECTED event changes: E1
    is drained and E2 — the same gate re-suspended under the same key with a
    different ``product_content_hash`` — is pending in its place. That is the
    brief's §4b 6a disagreement, "a different event under the same key": the
    re-read of the state for ``(tenant, K)`` no longer finds the snapshot's
    frozen event. It is the only concurrent change in the arrangement, made
    by the test itself and accounted for explicitly. (Appending E2 BEHIND a
    still-pending E1 would leave the selected event and its state unchanged
    and is NOT a refusal under the ruling — whole-queue revalidation is a
    broader requirement nobody ruled.) The event class is NOT the
    approval-gate class, so eligibility is not in play and the control reads
    the revalidation alone.
    """
    import ccf.hitl.transport as transport_module

    fixture = gate_harness._hitl()
    provider, kid, keys = gate_harness._signing_env(tmp_path)
    subject = gate_harness._subject(fixture)
    plane, policy_key, _ = gate_harness._required_policy_plane(subject_id=subject, keys=keys)
    transport = InMemoryHitlTransport(
        control_plane=plane, hitl_policy_key=policy_key, identity_provider=provider
    )
    document = dict(fixture["escalation"]["event"])
    e1 = PendingHitlEvent(**document, product_content_hash=content_hash(document))
    e2 = PendingHitlEvent(
        **document, product_content_hash=content_hash({**document, "suspension": "second"})
    )
    assert e1.event_class != "approval-gate" and e1.product_content_hash != e2.product_content_hash
    transport.enqueue(event=e1)
    principal = gate_harness._principal(fixture, product_content_hash=e1.product_content_hash)
    attestation = gate_harness._attestation(
        provider,
        kid,
        tenant=e1.tenant,
        event_key=e1.event_key,
        action="approve",
        principal=principal,
        subject_id=subject,
        nonce="sec006-revalidation-nonce-1",
    )
    submission = HitlActionSubmission(
        event_key=e1.event_key, action="approve", principal=principal, attestation=attestation
    )
    capability = submit_capability(tenant=e1.tenant, principal=subject, event_key=e1.event_key)
    original = transport_module.enforce_attestation
    armed = {"value": True}

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if armed["value"]:
            armed["value"] = False
            drained = transport.dequeue(tenant=e1.tenant)
            assert drained == e1, drained
            transport.enqueue(event=e2)
        return original(*args, **kwargs)

    monkeypatch.setattr(transport_module, "enforce_attestation", wrapper)
    return transport, capability, submission, e1, e2


def _assert_revalidation_refusal(error: BaseException) -> None:
    """The 6a refusal is the RULED typed name and nothing else.

    Brief §4b 6a: a disagreement between the re-read and the snapshot
    "refuses ``GateActionError``-class" — a typed ``ValueError``-family
    refusal, the class :class:`ccf.hitl.approval_gate.GateActionError`
    belongs to, not a ``PermissionError`` (the eligibility and attestation
    family). The name is a MISSING CONTRACT until the repair lands; any other
    exception — the attestation family above all — is a wrong refusal, not an
    accepted one.
    """
    expected = contract(
        "ccf.hitl.transport",
        "HitlEventRevalidationRefused",
        ruling="D-IMPL-366 §4b 6a, GateActionError-class",
    )
    assert issubclass(expected, ValueError) and not issubclass(expected, PermissionError), (
        f"{expected.__name__} is not GateActionError-class (a ValueError-family refusal)"
    )
    assert isinstance(error, expected), (
        f"refused by {type(error).__name__}, not the ruled revalidation refusal"
        f" {expected.__name__} (D-IMPL-366 §4b 6a): {error}"
    )


def test_t11_a_changed_queue_under_the_key_is_refused_and_mutates_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C, T11 — BEHAVIORAL today.

    Between the snapshot and the record the selected event under the key
    changes — E1 drained, E2 pending in its place; ``submit`` refuses (6a),
    and ``_submissions``, ``_claims`` and ``_seen_nonces`` are byte-for-byte
    what they were — asserted on the transport's state, not on a return
    value. The ONLY difference permitted in the after-state is the test's own
    concurrent E1→E2 replacement on ``pending`` (carried requirement (3): a
    legitimate concurrent change is distinguished from a mutation by the
    refused submission). Today there is no revalidation: the submission is
    recorded and the nonce consumed.
    """
    transport, capability, submission, e1, e2 = _revalidation_arrangement(tmp_path, monkeypatch)
    tenant = e1.tenant
    before = transport_state(transport)
    try:
        recorded = transport.submit(capability, submission=submission)
    except Exception as error:  # noqa: BLE001 — judged by class below, never accepted broadly
        _assert_revalidation_refusal(error)
    else:
        pytest.fail(
            "BEHAVIORAL: transport.submit RECORDED a submission although the"
            " selected event under its key changed between snapshot and record; the"
            " revalidation (D-IMPL-366 §4b step 6a) must refuse it:"
            f" {recorded.event_key!r} state={transport_state(transport)['nonces']!r}"
        )
    after = transport_state(transport)
    expected = dict(before)
    expected["pending"] = {
        **before["pending"],
        tenant: tuple(e for e in before["pending"][tenant] if e != e1) + (e2,),
    }
    assert after == expected, (
        "a refused submission mutated transport state beyond the accounted"
        f" concurrent enqueue:\n before={before!r}\n after={after!r}"
    )


def test_t14_the_nonce_survives_the_refusal_and_is_admitted_once_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C, T14 — BEHAVIORAL today.

    After the revalidation refusal the SAME signed attestation with the SAME
    nonce, re-presented against the now-stable state (E2 pending at snapshot
    and at record), is ADMITTED: the nonce is single-use on success only (D-IMPL-366
    amendment: "refused submissions introduce no state mutations"). Today the
    first presentation lands and consumes the nonce, so the re-presentation
    is refused as a reuse — the measured signature of the withdrawn order in
    which the nonce was inserted before the re-check.
    """
    from ccf.hitl.transport import SignedBindingStaleRefused

    transport, capability, submission, e1, _ = _revalidation_arrangement(tmp_path, monkeypatch)
    try:
        first = transport.submit(capability, submission=submission)
    except Exception as error:  # noqa: BLE001 — judged by class below, never accepted broadly
        _assert_revalidation_refusal(error)
    else:
        pytest.fail(
            "BEHAVIORAL: the first presentation was RECORDED and its nonce consumed,"
            " although the revalidation must refuse it before any nonce is spent"
            f" (D-IMPL-366 §4b: revalidation precedes nonce consumption): {first.event_key!r}"
        )
    try:
        recorded = transport.submit(capability, submission=submission)
    except SignedBindingStaleRefused as error:
        pytest.fail(
            "BEHAVIORAL: the attestation's nonce was consumed by the refused"
            " presentation, so the legitimate re-presentation is refused as a reuse"
            f" (D-IMPL-366 §4b: nonce single-use on success only): {error}"
        )
    assert recorded in transport.submissions(tenant=e1.tenant)
    assert any(nonce == "sec006-revalidation-nonce-1" for _, _, nonce in transport_state(transport)["nonces"])


# --- carried requirement (1): caller-supplied audit stamps are overwritten -----


def test_carried_1_existing_stamps_are_the_transports_not_the_callers() -> None:
    """Carried (1), the four fields that exist today — GREEN preservation.

    ``answered_event_class``, ``answered_workflow_state_ref``,
    ``authorizing_decision_id`` and ``hitl_policy_ref`` presented by the caller
    are recorded with the transport's own values (SEC-001 Tier 0; D-IMPL-353
    §2 P6; `D-IMPL-363` E3). Unbound and unclaimed, the transport's values are
    ``None``, ``None``, the capability's decision id, ``None``.
    """
    fixture = gate_harness._hitl()
    transport = InMemoryHitlTransport()
    event = gate_harness._event(fixture)
    transport.enqueue(event=event)
    forged = door_submission(event, subject_id="credit-officer-11").model_copy(
        update={
            "answered_event_class": "approval-gate",
            "answered_workflow_state_ref": "forged/state",
            "authorizing_decision_id": "forged-decision",
            "hitl_policy_ref": "forged/hitl/policy@9.9.9",
        }
    )
    capability = submit_capability(
        tenant=event.tenant, principal="credit-officer-11", event_key=event.event_key
    )
    recorded = transport.submit(capability, submission=forged)
    assert recorded.answered_event_class is None
    assert recorded.answered_workflow_state_ref is None
    assert recorded.authorizing_decision_id == capability.decision_id
    assert recorded.hitl_policy_ref is None


def test_carried_1_the_new_stamps_are_the_transports_not_the_callers() -> None:
    """Carried (1), the three RULED fields — MISSING CONTRACT today.

    A submission presented with ``approval_policy_ref``, ``requested_by`` and
    ``event_state_at_submit`` already set is recorded with the transport's
    values from the event it found: the event's policy ref, the event's
    requester, ``"pending"``. Today the contract has no such fields and
    ``extra=forbid`` refuses them at construction — reported as the MISSING
    CONTRACT it is.
    """
    fixture = gate_harness._hitl()
    transport = InMemoryHitlTransport()
    event = _gate_event(fixture, requested_by="starter-7")
    transport.enqueue(event=event)
    # Built as a document and validated, never as duplicate keywords: once the
    # fields exist, ``model_dump()`` already carries them at their defaults.
    document = door_submission(event, subject_id="credit-officer-11").model_dump()
    document.update(
        approval_policy_ref="ccf-artifact://acme-bank/approval-policy/forged@1.0.0",
        requested_by="forged-requester",
        event_state_at_submit="claimed",
    )
    try:
        forged = HitlActionSubmission.model_validate(document)
    except ValidationError as error:
        pytest.fail(
            "MISSING CONTRACT: HitlActionSubmission.approval_policy_ref /"
            " requested_by / event_state_at_submit (D-IMPL-366 H3 (a), H2) do not"
            f" exist on this tree: {error}"
        )
    capability = submit_capability(
        tenant=event.tenant, principal="credit-officer-11", event_key=event.event_key
    )
    recorded = transport.submit(capability, submission=forged)
    assert recorded.approval_policy_ref == event.policy_ref
    assert recorded.requested_by == "starter-7"
    assert recorded.event_state_at_submit == "pending"


#: Referenced so the ruled wire code is pinned from this module too (G3 (a)).
assert ELIGIBILITY_CODE == "approver-not-eligible"
