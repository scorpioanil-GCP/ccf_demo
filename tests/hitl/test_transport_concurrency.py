"""WR-02 — the HITL transport's concurrency contract under a live hammer.

Claims pinned here (Phase-9 CONTEXT D-05/D-06/D-07/D-15; D-IMPL-69
adjacency; CLAUDE.md §8.2): :class:`~ccf.hitl.transport.InMemoryHitlTransport`
survives a 24-thread mixed-op hammer with no lost events, no duplicated
events, and no deadlock — the plain :class:`threading.Lock` synchronization
Task 09-03-1 added discharges the ``HITLTransportProtocol`` docstring's
requirement that all methods be safe for concurrent calls from multiple
threads (the FastAPI-threadpool doors invoke it exactly that way). A second,
shorter case hammers the submit path of a D-16-wired transport (an
attestation required, Control Plane resolve + JWS verification per
submission) to show the verification path — which runs outside the lock by
design — introduces no lock-ordering hazard. A third case points the hammer
at the one step that is INSIDE the lock: `D-IMPL-363` E4 / C11(a)'s
single-admission nonce check, where N concurrent presentations of ONE
attestation must admit exactly one and refuse the rest.

Always-on per D-15: no markers, no slow/nightly tagging. Deadlock detection
is bounded ``join(timeout=...)`` + ``pytest.fail`` — no third-party
timeout plugin. All randomness is seeded (``random.Random(seed)``) so a failure
reproduces.
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
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
    SignedBindingStaleRefused,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)
from tests.controlplane.composition import compose_register_typed

ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)

#: 24 threads sits inside the ruled 16-32 envelope (Phase-9 CONTEXT D-07).
THREAD_COUNT = 24
#: Bounded per-thread op count keeps total runtime to seconds.
OPS_PER_THREAD = 300
#: Every join is bounded; a miss is a deadlock verdict, not a hang.
JOIN_TIMEOUT_SECONDS = 30.0
#: Deterministic base seed — per-thread seed is BASE_SEED + thread index.
BASE_SEED = 90_302

from .capabilities import submit_capability

TENANTS = ("acme-bank", "globex", "initech")

APPROVER_KID = "hitl-approver-signing-key"
POLICY_KEY = "acme-bank/hitl/policy"

#: The window this test-as-deployment states (CINV-01 — the SDK supplies no
#: default, and a required policy without one is refused at parse). Wide
#: enough that nothing here depends on execution speed: every ``issued_at``
#: below is stated relative to the FIXED ``ACTION_TIME`` the bindings record,
#: and the verifier reads no clock at all.
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60


def _binding(subject_id: str = "approver-1") -> HumanPrincipalBinding:
    return HumanPrincipalBinding(
        verdict="approve",
        approver=ApproverIdentity(
            subject_id=subject_id,
            identity_provider_ref="test-idp",
        ),
        authentication=AuthenticationContext(
            method="test-method",
            assurance_level="test-level",
            session_ref="test-session",
        ),
        action_time=ACTION_TIME,
        product_content_hash=hashlib.sha256(b"fixture-product").hexdigest(),
    )


def _event(**mutations: Any) -> PendingHitlEvent:
    document: dict[str, Any] = {
        "event_key": "acme-bank/approvals/1",
        "event_class": "approval-gate",
        "tenant": "acme-bank",
        "workflow_state_ref": "workflow-state/covenant-review/run-1",
        "product_content_hash": content_hash({"product": "seen"}),
        "policy_ref": (
            "ccf-artifact://acme-bank/approval-policy/credit-officer@1.0.0"
        ),
    }
    document.update(mutations)
    return PendingHitlEvent.model_validate(document)


def _submission(**mutations: Any) -> HitlActionSubmission:
    document: dict[str, Any] = {
        "event_key": "acme-bank/approvals/1",
        "action": "approve",
        "principal": _binding(),
        "annotation": None,
    }
    document.update(mutations)
    return HitlActionSubmission.model_validate(document)


def _join_all(threads: list[threading.Thread]) -> None:
    """Bounded joins; a missed join is a deadlock, reported as a failure."""
    for thread in threads:
        thread.join(timeout=JOIN_TIMEOUT_SECONDS)
        if thread.is_alive():
            pytest.fail(
                f"thread {thread.name} did not finish within"
                f" {JOIN_TIMEOUT_SECONDS}s — deadlock or livelock in the"
                " transport under concurrent load (WR-02)"
            )


# --- the mixed-op hammer ------------------------------------------------------


def test_mixed_op_hammer_loses_and_duplicates_nothing() -> None:
    """24 threads of seeded-random mixed ops: exactly-once accounting holds.

    Every enqueued event key is namespaced per thread
    (``{tenant}/hammer/{thread}/{i}``), so post-run accounting is
    by-construction checkable: each key was dequeued exactly once OR is
    still pending — never lost, never duplicated — and the number of
    recorded submissions equals the sum of per-thread submit tallies.
    """
    transport = InMemoryHitlTransport()
    barrier = threading.Barrier(THREAD_COUNT)

    enqueued: list[list[str]] = [[] for _ in range(THREAD_COUNT)]
    dequeued: list[list[str]] = [[] for _ in range(THREAD_COUNT)]
    submitted: list[int] = [0] * THREAD_COUNT
    errors: list[BaseException] = []

    def hammer(index: int) -> None:
        rng = random.Random(BASE_SEED + index)
        try:
            barrier.wait(timeout=JOIN_TIMEOUT_SECONDS)
            for i in range(OPS_PER_THREAD):
                tenant = rng.choice(TENANTS)
                op = rng.randrange(5)
                if op == 0:
                    key = f"{tenant}/hammer/{index}/{i}"
                    transport.enqueue(
                        event=_event(event_key=key, tenant=tenant)
                    )
                    enqueued[index].append(key)
                elif op == 1:
                    popped = transport.dequeue(tenant=tenant)
                    if popped is not None:
                        dequeued[index].append(popped.event_key)
                elif op == 2:
                    snapshot = transport.pending(tenant=tenant)
                    assert isinstance(snapshot, tuple)
                elif op == 3:
                    key = f"{tenant}/hammer/{index}/{i}"
                    # A capability per submit, minted for exactly this
                    # tenant and event (D-IMPL-353 §1.2) — the tenant the
                    # record files under is the capability's.
                    transport.submit(
                        submit_capability(
                            tenant=tenant, principal="approver-1", event_key=key
                        ),
                        submission=_submission(event_key=key),
                    )
                    submitted[index] += 1
                else:
                    recorded = transport.submissions(tenant=tenant)
                    assert isinstance(recorded, tuple)
        except BaseException as error:  # noqa: BLE001 - collected for report
            errors.append(error)

    threads = [
        threading.Thread(target=hammer, args=(index,), name=f"hammer-{index}")
        for index in range(THREAD_COUNT)
    ]
    for thread in threads:
        thread.start()
    _join_all(threads)

    assert errors == [], f"worker threads raised: {errors!r}"

    all_enqueued = [key for keys in enqueued for key in keys]
    all_dequeued = [key for keys in dequeued for key in keys]
    still_pending = [
        event.event_key
        for tenant in TENANTS
        for event in transport.pending(tenant=tenant)
    ]

    # No duplication: nothing was dequeued twice, nothing pending twice,
    # and nothing is simultaneously dequeued and pending.
    assert len(all_dequeued) == len(set(all_dequeued))
    assert len(still_pending) == len(set(still_pending))
    assert set(all_dequeued).isdisjoint(still_pending)

    # No loss, no invention: dequeued-once + still-pending == enqueued.
    assert set(all_dequeued) | set(still_pending) == set(all_enqueued)
    assert len(all_dequeued) + len(still_pending) == len(all_enqueued)

    # Submission accounting: everything recorded, nothing lost.
    total_recorded = sum(
        len(transport.submissions(tenant=tenant)) for tenant in TENANTS
    )
    assert total_recorded == sum(submitted)

    # Per-tenant FIFO for single-producer subsets: within one tenant's
    # remaining queue, each producing thread's own keys appear in the
    # order that thread enqueued them.
    for tenant in TENANTS:
        remaining = [
            event.event_key for event in transport.pending(tenant=tenant)
        ]
        for index in range(THREAD_COUNT):
            mine = [
                key
                for key in remaining
                if key.startswith(f"{tenant}/hammer/{index}/")
            ]
            ordered = [key for key in enqueued[index] if key in set(mine)]
            assert mine == ordered


# --- racing removes claim exactly once (WR-02) --------------------------------


def test_racing_removes_for_one_event_yield_exactly_one_claim() -> None:
    """WR-02: for each pending event, any number of concurrent ``remove``
    calls yields exactly one winner — the compare-and-consume the HITL
    primitives' resolve paths claim through, so one human action can
    never become two authority submissions."""
    transport = InMemoryHitlTransport()
    event_count = 50
    keys = [f"acme-bank/race/{i}" for i in range(event_count)]
    for key in keys:
        transport.enqueue(event=_event(event_key=key))

    thread_count = 12
    barrier = threading.Barrier(thread_count)
    claims: list[list[str]] = [[] for _ in range(thread_count)]
    errors: list[BaseException] = []

    def racer(index: int) -> None:
        try:
            barrier.wait(timeout=JOIN_TIMEOUT_SECONDS)
            for key in keys:
                claimed = transport.remove(
                    tenant="acme-bank", event_key=key
                )
                if claimed is not None:
                    claims[index].append(claimed.event_key)
        except BaseException as error:  # noqa: BLE001
            errors.append(error)

    threads = [
        threading.Thread(target=racer, args=(index,), name=f"remove-{index}")
        for index in range(thread_count)
    ]
    for thread in threads:
        thread.start()
    _join_all(threads)

    assert errors == [], f"remove threads raised: {errors!r}"
    all_claims = [key for claimed in claims for key in claimed]
    assert sorted(all_claims) == sorted(keys)  # every event claimed once
    assert len(all_claims) == len(set(all_claims))  # never twice
    assert transport.pending(tenant="acme-bank") == ()


# --- the D-16-wired submit path under load ------------------------------------


def _attesting_fixture(tmp_path: Path) -> tuple[
    InMemoryHitlTransport, DetachedJwsIdentityProvider, HumanPrincipalBinding
]:
    """A transport wired for required attestations, as `D-IMPL-363` E5 leaves
    it: the per-subject trusted keys and the freshness window live INSIDE the
    pinned policy, and the constructor takes no ``trusted_keys`` argument."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    key = ECKey.generate_key("P-256", parameters={"kid": APPROVER_KID})
    (key_dir / f"{APPROVER_KID}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    binding = _binding()
    trusted_keys: Mapping[str, Mapping[str, JsonWebKey]] = {
        binding.approver.subject_id: {APPROVER_KID: key.as_dict(private=False)}
    }
    plane = ControlPlaneRegistry()
    policy = parse_artifact(
        {
            "semver": "1.0.0",
            "signed_binding_required": True,
            "signature_max_age_seconds": MAX_AGE_SECONDS,
            "permitted_clock_skew_seconds": SKEW_SECONDS,
            "trusted_keys": trusted_keys,
        },
        HITL_POLICY,
    )
    assert isinstance(policy, HitlPolicy)
    compose_register_typed(plane, POLICY_KEY, policy, HITL_POLICY)
    transport = InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )
    return transport, provider, binding


def _attestation(
    provider: DetachedJwsIdentityProvider,
    binding: HumanPrincipalBinding,
    *,
    event_key: str,
    nonce: str,
) -> SignedHitlAction:
    """One signed statement about ONE action (`D-IMPL-363` E1).

    ``issued_at`` is the binding's own recorded instant — dead centre of the
    window — because the verifier compares the two and reads no clock; a
    hammer that ran slowly could not move either value.
    """
    return sign_hitl_action(
        HitlActionClaims(
            tenant="acme-bank",
            event_key=event_key,
            action="approve",
            product_content_hash=binding.product_content_hash,
            subject_id=binding.approver.subject_id,
            issued_at=binding.action_time,
            nonce=nonce,
        ),
        provider=provider,
        key_id=APPROVER_KID,
    )


def test_d16_wired_submit_path_hammers_without_lock_ordering_issues(
    tmp_path: Path,
) -> None:
    """Attestation verification per submission, hammered, no deadlock.

    The verification path (Control Plane ``resolve_latest`` + JWS
    verification) runs outside the queue lock by design (D-IMPL-69); this
    case shows the composition holds under concurrent submits — every
    verified submission is recorded exactly once and every join returns.

    Each submission carries its OWN signed statement with a FRESH nonce
    (`D-IMPL-363` E4 / C11(a)): a signed attestation names its event and is
    admitted once, so N submissions mean N attestations. Reuse is the
    subject of the sibling case below, not an accident of this one.
    """
    transport, provider, binding = _attesting_fixture(tmp_path)

    thread_count = 8
    submits_per_thread = 25
    barrier = threading.Barrier(thread_count)
    errors: list[BaseException] = []
    presented: list[list[SignedHitlAction]] = [[] for _ in range(thread_count)]

    def submit_hammer(index: int) -> None:
        try:
            barrier.wait(timeout=JOIN_TIMEOUT_SECONDS)
            for i in range(submits_per_thread):
                key = f"acme-bank/hammer/{index}/{i}"
                attestation = _attestation(
                    provider,
                    binding,
                    event_key=key,
                    nonce=f"nonce-{index}-{i}",
                )
                transport.submit(
                    submit_capability(
                        tenant="acme-bank",
                        principal=binding.approver.subject_id,
                        event_key=key,
                    ),
                    submission=_submission(
                        event_key=key,
                        principal=binding,
                        attestation=attestation,
                    ),
                )
                presented[index].append(attestation)
        except BaseException as error:  # noqa: BLE001
            errors.append(error)

    threads = [
        threading.Thread(
            target=submit_hammer, args=(index,), name=f"submit-{index}"
        )
        for index in range(thread_count)
    ]
    for thread in threads:
        thread.start()
    _join_all(threads)

    assert errors == [], f"submit threads raised: {errors!r}"
    recorded = transport.submissions(tenant="acme-bank")
    assert len(recorded) == thread_count * submits_per_thread
    # Every recorded submission carries the exact attestation presented for
    # its own event — the exact set, not a count.
    expected = {
        (attestation.claims.event_key, attestation.claims.nonce)
        for attestations in presented
        for attestation in attestations
    }
    assert {
        (entry.attestation.claims.event_key, entry.attestation.claims.nonce)
        for entry in recorded
        if entry.attestation is not None
    } == expected
    assert all(entry.attestation is not None for entry in recorded)


# --- one attestation, N racing presentations: exactly one admission -----------


def test_racing_presentations_of_one_attestation_admit_exactly_one(
    tmp_path: Path,
) -> None:
    """`D-IMPL-363` E4 / C11(a): a signed statement is admitted ONCE.

    The nonce check and its insert are one step under the transport's lock,
    after verification and before anything is recorded — so N concurrent
    presentations of the SAME attestation cannot both land. Exactly one
    submission is recorded; every other presentation refuses
    :class:`~ccf.hitl.transport.SignedBindingStaleRefused`, and nothing else
    is raised. The replayed statement is identical bytes, not a near-copy:
    the losers fail on the nonce, not on verification.
    """
    transport, provider, binding = _attesting_fixture(tmp_path)
    event_key = "acme-bank/replay/one-attestation"
    attestation = _attestation(
        provider, binding, event_key=event_key, nonce="nonce-replayed-once"
    )

    thread_count = 16
    barrier = threading.Barrier(thread_count)
    admitted: list[HitlActionSubmission] = []
    refused: list[BaseException] = []
    unexpected: list[BaseException] = []
    bookkeeping = threading.Lock()

    def present(index: int) -> None:
        try:
            barrier.wait(timeout=JOIN_TIMEOUT_SECONDS)
            recorded = transport.submit(
                submit_capability(
                    tenant="acme-bank",
                    principal=binding.approver.subject_id,
                    event_key=event_key,
                ),
                submission=_submission(
                    event_key=event_key,
                    principal=binding,
                    attestation=attestation,
                ),
            )
        except SignedBindingStaleRefused as error:
            with bookkeeping:
                refused.append(error)
        except BaseException as error:  # noqa: BLE001
            with bookkeeping:
                unexpected.append(error)
        else:
            with bookkeeping:
                admitted.append(recorded)

    threads = [
        threading.Thread(target=present, args=(index,), name=f"present-{index}")
        for index in range(thread_count)
    ]
    for thread in threads:
        thread.start()
    _join_all(threads)

    assert unexpected == [], f"unexpected failures: {unexpected!r}"
    assert len(admitted) == 1, (
        "exactly one presentation of one signed statement may be admitted"
        f" (D-IMPL-363 E4); {len(admitted)} were"
    )
    assert len(refused) == thread_count - 1
    # The queue agrees with the callers: one recorded action, carrying the
    # attestation that was presented.
    (only,) = transport.submissions(tenant="acme-bank")
    assert only == admitted[0]
    assert only.attestation == attestation
    # And a LATER, serial presentation of the same statement is refused too —
    # the seen-set is not a race-window artifact.
    with pytest.raises(SignedBindingStaleRefused):
        transport.submit(
            submit_capability(
                tenant="acme-bank",
                principal=binding.approver.subject_id,
                event_key=event_key,
            ),
            submission=_submission(
                event_key=event_key,
                principal=binding,
                attestation=attestation,
            ),
        )
    assert len(transport.submissions(tenant="acme-bank")) == 1
