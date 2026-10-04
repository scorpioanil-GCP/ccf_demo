"""``ReviewQueue`` — the asynchronous review HITL primitive (07-08).

Written before the implementation per the TDD discipline. The claims:

A queued item exposes the output reference plus its passage-level lineage
— the real :class:`~ccf.contracts.claims.LineageEntry` /
:class:`~ccf.contracts.claims.PassageAnchor` types, not a string — so a
reviewer can see what each claim anchors to (whitepaper §7.10.3); an item
without lineage is unconstructible; release requires a bound review action
and lands on dimension 2 (a rejection is audited ``resolved=False``); two
reviewers on two tenants' queues are isolated (D-23); resolving an event
the queue does not hold raises (broken wiring, I.1 line).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.authz.capability import Authorized, HitlSubmit
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.contracts.claims import LineageEntry, PassageAnchor
from ccf.controlplane.audit import AuditLog
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.review_queue import (
    ReviewActionRecord,
    ReviewQueue,
    ReviewQueueItem,
    ReviewResolution,
    UnknownReviewEventError,
)
from ccf.hitl.transport import PendingHitlEvent, HitlActionSubmission, InMemoryHitlTransport
from tests.controlplane.composition import compose_register_typed

from .capabilities import submit_capability

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _hitl() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "hitl.yaml").read_text()
    )
    return loaded


def _authorized(tenant: str, event_key: str) -> Authorized[HitlSubmit]:
    """The capability a resolver presents (D-IMPL-353 §1.2): minted for
    exactly this tenant and event, for the fixture's credit officer — the
    subject every binding below names, so the transport's actor check and
    the capability agree."""
    subject = _hitl()["approvers"]["credit_officer"]["identity"]["subject_id"]
    return submit_capability(
        tenant=tenant, principal=subject, event_key=event_key
    )


def _clock() -> Any:
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _principal(
    fixture: dict[str, Any], approver_key: str, *, product_content_hash: str
) -> HumanPrincipalBinding:
    approver = fixture["approvers"][approver_key]
    return HumanPrincipalBinding(
        verdict="approve",
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _queue() -> tuple[ReviewQueue, InMemoryHitlTransport, AuditLog]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    queue = ReviewQueue(transport=transport, audit=audit, clock=_clock())
    return queue, transport, audit


def _item(document: dict[str, Any]) -> ReviewQueueItem:
    return ReviewQueueItem(
        output_ref=document["output_ref"],
        lineage=tuple(
            LineageEntry(**entry) for entry in document["lineage"]
        ),
    )


def _submit(
    queue: ReviewQueue, fixture: dict[str, Any]
) -> tuple[dict[str, Any], ReviewQueueItem]:
    document = fixture["review"]["event"]
    item = _item(fixture["review"]["item"])
    queue.submit_for_review(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        item=item,
        policy_ref=document.get("policy_ref"),
    )
    return document, item


def test_a_queued_item_exposes_passage_level_lineage() -> None:
    """The reviewer sees the output plus what each claim anchors to, in the
    real lineage types (whitepaper §7.10.3), never a string."""
    fixture = _hitl()
    queue, transport, _ = _queue()
    document, item = _submit(queue, fixture)
    ((event, queued),) = queue.items(tenant=document["tenant"])
    assert queued == item
    assert isinstance(queued.lineage[0], LineageEntry)
    anchor = queued.lineage[0].passage_anchor
    assert isinstance(anchor, PassageAnchor)
    expected = fixture["review"]["item"]["lineage"][0]["passage_anchor"]
    assert anchor.kind == expected["kind"]
    assert anchor.locator == expected["locator"]
    assert event.event_class == "review-queue"
    assert event.product_content_hash == content_hash(item)
    (pending,) = transport.pending(tenant=document["tenant"])
    assert pending == event


def test_an_item_without_lineage_is_unconstructible() -> None:
    """Citation-aware review is the point: no lineage, no queue item."""
    fixture = _hitl()
    with pytest.raises(ValidationError):
        ReviewQueueItem(
            output_ref=fixture["review"]["item"]["output_ref"], lineage=()
        )


def test_an_unbound_release_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (D-22
    type-unrepresentable leg)."""
    fixture = _hitl()
    document = fixture["review"]["event"]
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=document["event_key"],
            action="approve",
        )


def test_a_release_is_a_bound_action_on_dimension_two() -> None:
    fixture = _hitl()
    queue, transport, audit = _queue()
    document, item = _submit(queue, fixture)
    resolution = queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert isinstance(resolution, ReviewResolution)
    assert isinstance(resolution.record, ReviewActionRecord)
    assert resolution.record.released
    assert resolution.record.item == item
    assert resolution.hitl_actions_block == canonical_bytes(
        resolution.record
    ).decode("utf-8")
    assert queue.items(tenant=document["tenant"]) == ()
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "approve"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_a_rejection_is_recorded_resolved_false() -> None:
    fixture = _hitl()
    queue, _, audit = _queue()
    document, item = _submit(queue, fixture)
    resolution = queue.reject(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert isinstance(resolution, ReviewResolution)
    assert not resolution.record.released
    events = audit.events()
    assert events[-1].action == "hitl_action" and not events[-1].resolved


def test_two_tenants_queues_are_isolated() -> None:
    """D-23: a view of one tenant's queue says nothing about another's, and
    resolving one tenant's item never touches the other's queue."""
    fixture = _hitl()
    queue, _, _ = _queue()
    document, item = _submit(queue, fixture)
    other = fixture["review"]["other_tenant"]
    other_item = _item(other["item"])
    queue.submit_for_review(
        tenant=other["event"]["tenant"],
        event_key=other["event"]["event_key"],
        workflow_state_ref=other["event"]["workflow_state_ref"],
        item=other_item,
    )
    ((_, mine),) = queue.items(tenant=document["tenant"])
    assert mine == item
    ((_, theirs),) = queue.items(tenant=other["event"]["tenant"])
    assert theirs == other_item
    queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert queue.items(tenant=document["tenant"]) == ()
    assert len(queue.items(tenant=other["event"]["tenant"])) == 1


def test_releasing_on_a_second_instance_is_typed_and_mutates_nothing() -> None:
    """WR-01: the transport may be shared across primitive instances, but
    the queued item is per-instance side-band state. Releasing on an
    instance that did not queue the item raises the typed broken-wiring
    error *before* any transport mutation — never a bare ``KeyError``
    after the authority path already recorded the action."""
    fixture = _hitl()
    queue, transport, audit = _queue()
    document, item = _submit(queue, fixture)

    other = ReviewQueue(transport=transport, audit=audit, clock=_clock())
    with pytest.raises(UnknownReviewEventError):
        other.release(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=_principal(
                fixture,
                "credit_officer",
                product_content_hash=content_hash(item),
            ),
        )

    # Nothing landed on the authority path and the event survives.
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_releasing_an_unknown_event_raises() -> None:
    fixture = _hitl()
    queue, _, _ = _queue()
    document = fixture["review"]["event"]
    with pytest.raises(UnknownReviewEventError):
        queue.release(
            _authorized(document["tenant"], "acme-bank/exec-rev/no-such-event"),
            event_key="acme-bank/exec-rev/no-such-event",
            principal=_principal(
                fixture,
                "credit_officer",
                product_content_hash=content_hash({"any": "thing"}),
            ),
        )


# --- 10-02 Task 3 / `D-IMPL-363`: release-surface attestation verification ---
#
# SEC-005's remaining leg (`D-IMPL-363`) replaced the signed door-minted
# binding with signer-stated `HitlActionClaims` carried as an `attestation`,
# and moved BOTH the trust map and the freshness window INSIDE the pinned
# `HitlPolicy` (E3/E5) — there is no `trusted_keys` constructor argument on the
# transport or on a primitive any more. These tests sign `issued_at` equal to
# the binding's FIXED `action_time`: that is the recorded instant the
# directional window is judged against (E2), so no participant reads a clock.
#
# `ReviewQueue` DERIVES the action it submits — ``approve`` from `release`,
# ``reject`` from `reject` — so the signed `action` must equal that derived
# verdict, and a signature over the other one refuses as a mismatch.

#: Deployment vocabulary for this suite (CINV-01): the window the pinned policy
#: declares. Both are REQUIRED whenever `signed_binding_required` is true.
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60


def _signing_env(tmp_path: Path) -> tuple[Any, str, dict[str, Any]]:
    """A provider, its key id, and the public-JWK map for ONE approver subject."""
    import json as _json

    from joserfc.jwk import ECKey

    from ccf.peering.identity import (
        DetachedJwsIdentityProvider,
        FileBackedKeySource,
    )

    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    kid = "review-approver-key"
    key = ECKey.generate_key("P-256", parameters={"kid": kid})
    (key_dir / f"{kid}.jwk").write_text(
        _json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    return provider, kid, {kid: key.as_dict(private=False)}


def _subject(fixture: dict[str, Any], approver_key: str) -> str:
    """The approver subject the named fixture approver signs under."""
    subject: str = fixture["approvers"][approver_key]["identity"]["subject_id"]
    return subject


def _ruled_policy_document(
    *, subject_id: str, keys: dict[str, Any]
) -> dict[str, Any]:
    """The HITL policy `D-IMPL-363` E3/E5 rules: requiredness, the directional
    freshness window, and the per-subject trusted keys — the ONE trust source."""
    return {
        "semver": "1.0.0",
        "signed_binding_required": True,
        "signature_max_age_seconds": MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": SKEW_SECONDS,
        "trusted_keys": {subject_id: keys},
    }


def _bound_queue(
    tmp_path: Path, fixture: dict[str, Any]
) -> tuple[ReviewQueue, InMemoryHitlTransport, Any, str, str]:
    """The queue, its transport, the signer's provider and key id, and the
    ``key@version`` the transport stamps on an admitted submission — derived
    from the registry's own resolution (`D-IMPL-363` E3), never a literal."""
    from ccf.controlplane.artifacts import parse_artifact
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.hitl.transport import HITL_POLICY, resolve_hitl_policy

    provider, kid, keys = _signing_env(tmp_path)
    plane = ControlPlaneRegistry()
    policy_key = "acme-bank/hitl/policy"
    compose_register_typed(
        plane,
        policy_key,
        parse_artifact(
            _ruled_policy_document(
                subject_id=_subject(fixture, "credit_officer"), keys=keys
            ),
            HITL_POLICY,
        ),
        HITL_POLICY,
    )
    resolved = resolve_hitl_policy(
        control_plane=plane, hitl_policy_key=policy_key
    )
    assert resolved is not None
    version, policy = resolved
    transport = InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
    )
    queue = ReviewQueue(
        transport=transport,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
    )
    return (
        queue,
        transport,
        provider,
        kid,
        policy.pinned_ref(key=policy_key, version=version),
    )


def _attestation(
    provider: Any,
    kid: str,
    *,
    tenant: str,
    event_key: str,
    action: str,
    principal: HumanPrincipalBinding,
    subject_id: str,
    nonce: str,
) -> Any:
    """A signed attestation over exactly what a signer can state (E1).

    ``issued_at`` is the binding's own ``action_time`` — the fixed instant the
    door recorded — so the directional window is satisfied exactly, without any
    participant reading a clock (E2/E3).
    """
    from ccf.hitl.identity_binding import HitlActionClaims, sign_hitl_action

    return sign_hitl_action(
        HitlActionClaims(
            tenant=tenant,
            event_key=event_key,
            action=action,
            product_content_hash=principal.product_content_hash,
            subject_id=subject_id,
            issued_at=principal.action_time,
            nonce=nonce,
        ),
        provider=provider,
        key_id=kid,
    )


def test_review_required_and_unsigned_release_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.transport import SignedBindingRequiredRefused

    fixture = _hitl()
    queue, transport, provider, kid, _ = _bound_queue(tmp_path, fixture)
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    with pytest.raises(SignedBindingRequiredRefused):
        queue.release(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
        )
    # The pending event survives the refusal.
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()
    # A subsequent valid release of the SAME event succeeds. `release` derives
    # the action `approve` — and that is what is signed.
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture, "credit_officer"),
        nonce="review-nonce-after-unsigned",
    )
    resolution = queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, ReviewResolution)


def test_review_required_and_tampered_attestation_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """A tampered SIGNATURE refuses invalid and the event stays pending.

    Successor to
    ``test_review_required_and_tampered_binding_is_refused_event_pending``: the
    same property over the `D-IMPL-363` attestation rather than the removed
    signed binding.
    """
    from ccf.hitl.transport import SignedBindingInvalidRefused

    fixture = _hitl()
    queue, transport, provider, kid, _ = _bound_queue(tmp_path, fixture)
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture, "credit_officer"),
        nonce="review-nonce-tampered",
    )
    tampered = attestation.model_copy(
        update={"signature": attestation.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        queue.release(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            attestation=tampered,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_review_required_and_an_attestation_for_the_other_derived_action_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    """`D-IMPL-363` C1(a): the signed action must equal the action the queue
    DERIVES, and a signature over the other one authorizes nothing.

    The sibling a tampered signature cannot reach. The signature is genuine and
    the key is declared for this subject, so it verifies; the reviewer signed
    ``reject`` while the call is a `release`, whose derived action is
    ``approve``. Refused as a MISMATCH naming the `action` claim, with the item
    still queued: a signature over a rejection may not be spent as a release.
    """
    from ccf.hitl.transport import SignedBindingMismatchRefused

    fixture = _hitl()
    queue, transport, provider, kid, _ = _bound_queue(tmp_path, fixture)
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="reject",  # signed for the opposite derived action
        principal=principal,
        subject_id=_subject(fixture, "credit_officer"),
        nonce="review-nonce-other-derived-action",
    )
    with pytest.raises(SignedBindingMismatchRefused, match=r"\['action'\]"):
        queue.release(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            attestation=attestation,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_review_required_and_valid_attestation_passes_both_layers(
    tmp_path: Path,
) -> None:
    """The transport's own second verification also passes (D-13).

    Successor to ``test_review_required_and_valid_binding_passes_both_layers``:
    one attestation satisfies the primitive's verification AND the transport's
    independent re-verification, the recorded submission carries it, and the
    record names the pinned policy that admitted it (`D-IMPL-363` E3).
    """
    fixture = _hitl()
    queue, transport, provider, kid, pinned_ref = _bound_queue(
        tmp_path, fixture
    )
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    attestation = _attestation(
        provider,
        kid,
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=principal,
        subject_id=_subject(fixture, "credit_officer"),
        nonce="review-nonce-valid",
    )
    resolution = queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, ReviewResolution)
    recorded = transport.submissions(tenant=document["tenant"])
    assert len(recorded) == 1
    assert recorded[0].attestation == attestation
    assert recorded[0].hitl_policy_ref == pinned_ref


def test_review_unbound_kwargs_behave_as_before() -> None:
    """No Control Plane bound: byte-identical pre-Phase-10 behavior."""
    fixture = _hitl()
    queue, transport, _ = _queue()
    document, item = _submit(queue, fixture)
    resolution = queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=_principal(
            fixture,
            "credit_officer",
            product_content_hash=content_hash(item),
        ),
    )
    assert isinstance(resolution, ReviewResolution)


# --- D-IMPL-353 §1.2: the primitive requires the capability for ITS action ----
#
# The resolver mutates (``remove`` claims the event) and audits (a hash
# mismatch writes ``resolved=False``) BEFORE it submits, so the capability
# is verified at entry — a wrong kind or a capability minted for another
# event dies before the queue is read, before anything is audited, and
# before any claim is taken. Without these controls, severing ``verify`` at
# the primitive would redden nothing.


def test_a_queue_read_capability_dies_at_the_primitive_before_anything_is_touched() -> None:
    from ccf.authz.capability import CapabilityBypassError

    from .capabilities import queue_read_capability

    fixture = _hitl()
    queue, transport, audit = _queue()
    document, _item_queued = _submit(queue, fixture)
    ((event, _queued),) = queue.items(tenant=document["tenant"])
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=document["event_key"] + "-decoy",
            event_class="review-queue",
            tenant=document["tenant"],
            workflow_state_ref="decoy/exec",
            product_content_hash="e" * 64,
        )
    )
    # Two events, so a claim taken BEFORE the capability died (and given back
    # at the tail on rollback) shows up as a reorder rather than as nothing.
    pending_before = transport.pending(tenant=document["tenant"])
    assert len(pending_before) == 2
    audit_before = audit.events()
    principal = _principal(
        fixture, "credit_officer", product_content_hash=event.product_content_hash
    )
    read = queue_read_capability(
        tenant=document["tenant"], principal="credit-officer-11", resource=document["event_key"]
    )
    with pytest.raises(CapabilityBypassError, match="kind"):
        queue.release(
            read,  # type: ignore[arg-type]
            event_key=document["event_key"],
            principal=principal,
        )
    assert transport.pending(tenant=document["tenant"]) == pending_before
    assert transport.submissions(tenant=document["tenant"]) == ()
    assert audit.events() == audit_before


def test_a_capability_for_another_event_dies_at_the_primitive() -> None:
    from ccf.authz.capability import CapabilityBypassError

    fixture = _hitl()
    queue, transport, audit = _queue()
    document, _item_queued = _submit(queue, fixture)
    ((event, _queued),) = queue.items(tenant=document["tenant"])
    transport.enqueue(
        event=PendingHitlEvent(
            event_key=document["event_key"] + "-decoy",
            event_class="review-queue",
            tenant=document["tenant"],
            workflow_state_ref="decoy/exec",
            product_content_hash="e" * 64,
        )
    )
    # Two events, so a claim taken BEFORE the capability died (and given back
    # at the tail on rollback) shows up as a reorder rather than as nothing.
    pending_before = transport.pending(tenant=document["tenant"])
    assert len(pending_before) == 2
    audit_before = audit.events()
    principal = _principal(
        fixture, "credit_officer", product_content_hash=event.product_content_hash
    )
    with pytest.raises(CapabilityBypassError, match="resource"):
        queue.reject(
            _authorized(document["tenant"], "some-other-event"),
            event_key=document["event_key"],
            principal=principal,
        )
    assert transport.pending(tenant=document["tenant"]) == pending_before
    assert transport.submissions(tenant=document["tenant"]) == ()
    assert audit.events() == audit_before


def test_the_record_carries_the_authorizing_decision_id() -> None:
    """The recorded submission is the transport's stamped copy: the replay
    block names the authorization that produced the action (D-IMPL-353 §9),
    never the primitive's pre-stamp input."""
    fixture = _hitl()
    queue, transport, _ = _queue()
    document, item = _submit(queue, fixture)
    authorized = _authorized(document["tenant"], document["event_key"])
    resolution = queue.release(
        authorized,
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert isinstance(resolution, ReviewResolution)
    assert (
        resolution.record.submission.authorizing_decision_id
        == authorized.decision_id
    )
    assert authorized.decision_id in resolution.hitl_actions_block


def _queue_over_an_unverifying_transport(
    tmp_path: Path, fixture: dict[str, Any]
) -> tuple[Any, InMemoryHitlTransport, Any, str]:
    """The primitive bound to the ruled policy, over a transport bound to NO
    Control Plane — the transport resolves no policy and verifies nothing, so
    whatever refuses here is the primitive's own verification (CR-363-09)."""
    from ccf.controlplane.artifacts import parse_artifact
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.hitl.transport import HITL_POLICY

    provider, kid, keys = _signing_env(tmp_path)
    plane = ControlPlaneRegistry()
    policy_key = "acme-bank/hitl/policy"
    compose_register_typed(
        plane,
        policy_key,
        parse_artifact(
            _ruled_policy_document(subject_id=_subject(fixture, "credit_officer"), keys=keys),
            HITL_POLICY,
        ),
        HITL_POLICY,
    )
    unverifying = InMemoryHitlTransport()
    primitive = ReviewQueue(
        transport=unverifying,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
    )
    return primitive, unverifying, provider, kid


def test_review_queue_verifies_the_attestation_independently_of_the_transport(
    tmp_path: Path,
) -> None:
    """D-13 / D-IMPL-69: the queue's verification is its OWN, not the transport's.

    Every other signed test here binds BOTH halves — the real deployment shape —
    and that is exactly why none of them can say WHICH half refused: with the
    queue's own enforcement severed, the transport still refuses at ``submit``
    and the queue still raises. Measured at the close panel (`D-IMPL-363`
    CR-363-09): disabling this primitive's enforcement branch left every test
    green. So this control removes the OTHER half. The transport is bound to no
    Control Plane and therefore verifies nothing; the queue alone holds the
    policy key. If it did not verify independently, an unsigned release would be
    admitted and recorded, and a signature over the OTHER action would be
    admitted — no trust marker crosses the layer seam in either direction
    (D-13), so each layer has to do the work itself.
    """
    from ccf.hitl.transport import (
        SignedBindingMismatchRefused,
        SignedBindingRequiredRefused,
    )

    fixture = _hitl()
    queue, unverifying, provider, kid = _queue_over_an_unverifying_transport(
        tmp_path, fixture
    )
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    authorized = _authorized(document["tenant"], document["event_key"])
    # Leg 1 — unsigned: only the queue can refuse this.
    with pytest.raises(SignedBindingRequiredRefused):
        queue.release(
            authorized,
            event_key=document["event_key"],
            principal=principal,
        )
    # Leg 2 — `release` derives `approve`; a genuine signature over `reject`
    # is refused by the queue's own verifier, the only one that runs here.
    with pytest.raises(SignedBindingMismatchRefused):
        queue.release(
            authorized,
            event_key=document["event_key"],
            principal=principal,
            attestation=_attestation(
                provider,
                kid,
                tenant=document["tenant"],
                event_key=document["event_key"],
                action="reject",
                principal=principal,
                subject_id=_subject(fixture, "credit_officer"),
                nonce="review-independent-nonce-swapped",
            ),
        )
    assert len(unverifying.pending(tenant=document["tenant"])) == 1
    assert unverifying.submissions(tenant=document["tenant"]) == ()
    # Positive control: the honest attestation is admitted and recorded with
    # NO policy ref — the transport resolved none; the queue verified.
    resolution = queue.release(
        authorized,
        event_key=document["event_key"],
        principal=principal,
        attestation=_attestation(
            provider,
            kid,
            tenant=document["tenant"],
            event_key=document["event_key"],
            action="approve",
            principal=principal,
            subject_id=_subject(fixture, "credit_officer"),
            nonce="review-independent-nonce-honest",
        ),
    )
    assert isinstance(resolution, ReviewResolution)
    recorded = unverifying.submissions(tenant=document["tenant"])
    assert len(recorded) == 1
    assert recorded[0].hitl_policy_ref is None
