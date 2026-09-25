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


# --- 10-02 Task 3: release-surface signed-binding verification (D-IMPL-69) ---


def _signing_env(tmp_path: Path) -> tuple[Any, str, dict[str, Any]]:
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


def _bound_queue(
    tmp_path: Path,
) -> tuple[ReviewQueue, InMemoryHitlTransport, Any, str]:
    from ccf.controlplane.artifacts import parse_artifact
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.hitl.transport import HITL_POLICY

    provider, kid, trusted = _signing_env(tmp_path)
    plane = ControlPlaneRegistry()
    policy_key = "acme-bank/hitl/policy"
    compose_register_typed(plane,
        policy_key,
        parse_artifact(
            {"semver": "1.0.0", "signed_binding_required": True},
            HITL_POLICY,
        ),
        HITL_POLICY,
    )
    transport = InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
        trusted_keys=trusted,
    )
    queue = ReviewQueue(
        transport=transport,
        audit=AuditLog(),
        clock=_clock(),
        control_plane=plane,
        hitl_policy_key=policy_key,
        identity_provider=provider,
        trusted_keys=trusted,
    )
    return queue, transport, provider, kid


def test_review_required_and_unsigned_release_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.identity_binding import sign_principal_binding
    from ccf.hitl.transport import SignedBindingRequiredRefused

    fixture = _hitl()
    queue, transport, provider, kid = _bound_queue(tmp_path)
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
    # A subsequent valid release of the SAME event succeeds.
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    resolution = queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        signed_binding=signed,
    )
    assert isinstance(resolution, ReviewResolution)


def test_review_required_and_tampered_binding_is_refused_event_pending(
    tmp_path: Path,
) -> None:
    from ccf.hitl.identity_binding import sign_principal_binding
    from ccf.hitl.transport import SignedBindingInvalidRefused

    fixture = _hitl()
    queue, transport, provider, kid = _bound_queue(tmp_path)
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        queue.release(
            _authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=principal,
            signed_binding=tampered,
        )
    assert len(transport.pending(tenant=document["tenant"])) == 1
    assert transport.submissions(tenant=document["tenant"]) == ()


def test_review_required_and_valid_binding_passes_both_layers(
    tmp_path: Path,
) -> None:
    """The transport's own second verification also passes (D-13)."""
    from ccf.hitl.identity_binding import sign_principal_binding

    fixture = _hitl()
    queue, transport, provider, kid = _bound_queue(tmp_path)
    document, item = _submit(queue, fixture)
    principal = _principal(
        fixture, "credit_officer", product_content_hash=content_hash(item)
    )
    signed = sign_principal_binding(principal, provider=provider, key_id=kid)
    resolution = queue.release(
        _authorized(document["tenant"], document["event_key"]),
        event_key=document["event_key"],
        principal=principal,
        signed_binding=signed,
    )
    assert isinstance(resolution, ReviewResolution)
    recorded = transport.submissions(tenant=document["tenant"])
    assert len(recorded) == 1
    assert recorded[0].signed_binding == signed


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
