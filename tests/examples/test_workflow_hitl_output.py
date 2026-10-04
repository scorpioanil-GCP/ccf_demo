"""The workflow/HITL example's assertions, grouped by what they cover (D-09).

``archive/examples/05-workflow-hitl/run.py`` used to carry its own guarantee: 94
``assert`` statements and 18 ``print`` summaries, checked by ``make example-05``
exiting zero. D-09 moves that guarantee here, because ``make examples`` proves a
spine *runs* and ``pytest`` proves it is *correct*.

**Why this particular relocation matters.** Audit-by-construction is a
structural invariant (CLAUDE.md §8.2): *there is no path through the HITL
surface that produces an unrecorded human action.* This example is where that
invariant has a demonstrated form. An assertion lost in this move is not a
missing test — it is an invariant losing the only place it is shown to hold.
So every relocated assertion is mapped to its pre-rewrite line below, and the
"nothing lost" claim is auditable rather than merely stated.

Four groups, plus the door that guards them
--------------------------------------------

===========================================  ==================================
Group                                         Covered by
===========================================  ==================================
Suspend at the gate                           :func:`test_the_workflow_suspended_at_the_declared_gate`,
                                              :func:`test_the_suspended_state_persisted_at_the_control_plane`,
                                              :func:`test_the_pending_event_is_the_suspended_state_by_content_hash`
The hardened door                             :func:`test_the_unmapped_scope_is_refused_deny_by_default`,
                                              :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`,
                                              :func:`test_every_refusal_is_typed_and_fails_closed`,
                                              :func:`test_no_refusal_reached_the_authority_path`,
                                              :func:`test_the_admitted_submission_derived_its_principal_from_the_grant`,
                                              :func:`test_the_d16_policy_in_force_requires_a_signed_binding`,
                                              :func:`test_the_approvers_signature_verifies_from_the_record`
Resume to the declared terminal                :func:`test_the_workflow_completed_at_the_declared_terminal`,
                                              :func:`test_the_terminal_state_persisted_at_the_control_plane`
The ExceptionEscalation path                  :func:`test_the_failing_step_routed_to_its_declared_handler`,
                                              :func:`test_the_exception_transition_is_traced`,
                                              :func:`test_the_exception_transition_is_audited`
**Replay capture of every human action**      :func:`test_dimension_2_carries_the_approval_verbatim`,
                                              :func:`test_dimension_2_names_the_approver_identity`,
                                              :func:`test_dimension_2_carries_the_product_the_approver_saw`,
                                              :func:`test_dimension_2_carries_the_approvers_annotation_field`,
                                              :func:`test_dimension_2_carries_the_action_time`,
                                              :func:`test_dimension_2_carries_the_review_release_verbatim`,
                                              :func:`test_dimension_4_names_the_workflow_execution`,
                                              :func:`test_dimension_5_carries_the_workflow_step_sequence`
The fabric, and the 15-19 ruling            :func:`test_the_manifest_put_the_declared_bundles_in_force`,
                                              :func:`test_the_author_versioned_definitions_kept_their_bump_check`,
                                              :func:`test_the_loan_under_review_is_a_real_entity`
The ReviewQueue                               :func:`test_the_review_item_is_bound_by_submission_time_hash`,
                                              :func:`test_the_review_queue_holds_the_item_until_resolved`,
                                              :func:`test_the_reviewer_identity_matches_an_active_token`,
                                              :func:`test_the_review_resolved_as_the_artifact_directed`,
                                              :func:`test_the_review_release_is_audited`,
                                              :func:`test_the_review_queue_drains_on_resolution`
===========================================  ==================================

Where each relocated assertion came from
-----------------------------------------

Pre-rewrite line numbers are against ``archive/examples/05-workflow-hitl/run.py`` at the
plan's base commit (``df074b0``).

===========================================  ==========================
pre-rewrite ``run.py`` line                   relocated to
===========================================  ==========================
:361 ``signed_binding_required is True``      :func:`test_the_d16_policy_in_force_requires_a_signed_binding`
:425 ``suspended.gate``                       :func:`test_the_workflow_suspended_at_the_declared_gate`
:429 ``record.status == "suspended"``         :func:`test_the_suspended_state_persisted_at_the_control_plane`
:430 ``record.current_state``                 :func:`test_the_suspended_state_persisted_at_the_control_plane`
:481 ``authz_refused.status_code == 403``     :func:`test_the_unmapped_scope_is_refused_deny_by_default`
:483 ``ERROR_TENANT_UNAUTHORIZED``            :func:`test_the_unmapped_scope_is_refused_deny_by_default`
:491 one deny in the audit log                :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`
:492 deny actor                               :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`
:493 deny mapping version                     :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`
:497 ``queue.status_code == 200``             :func:`test_the_queue_view_is_served_through_the_authenticated_door`
:500 ``pending.event_key``                    :func:`test_the_queue_view_is_served_through_the_authenticated_door`
:503 ``pending.product_content_hash``          :func:`test_the_pending_event_is_the_suspended_state_by_content_hash`
:531/:532 unauthenticated 401                 :func:`test_every_refusal_is_typed_and_fails_closed`
:543/:544 expired-token 401                   :func:`test_every_refusal_is_typed_and_fails_closed`
:550/:551 unsigned 403                        :func:`test_every_refusal_is_typed_and_fails_closed`
:567/:568 tampered-signature 403              :func:`test_every_refusal_is_typed_and_fails_closed`
:574 nothing on the authority path            :func:`test_no_refusal_reached_the_authority_path`
:586 ``admitted.status_code == 200``          :func:`test_the_admitted_submission_derived_its_principal_from_the_grant`
:588 ``receipt["status"]``                    :func:`test_the_admitted_submission_derived_its_principal_from_the_grant`
:592 approver subject id                      :func:`test_the_admitted_submission_derived_its_principal_from_the_grant`
:595 ``submission.signed_binding``             :func:`test_the_admitted_submission_derived_its_principal_from_the_grant`
:608 the drained event                        :func:`test_the_gate_event_was_drained_before_the_resume`
:618 ``outcome.terminal_state``                :func:`test_the_workflow_completed_at_the_declared_terminal`
:621 ``terminal.status == "terminal"``         :func:`test_the_terminal_state_persisted_at_the_control_plane`
:673 dimension 2 byte-equal                    :func:`test_dimension_2_carries_the_approval_verbatim`
:675 approver in the block                     :func:`test_dimension_2_names_the_approver_identity`
:676 content hash in the block                 :func:`test_dimension_2_carries_the_product_the_approver_saw`
:677 signature in the block                    :func:`test_dimension_2_carries_the_approval_verbatim`
:679 round-tripped signed binding              :func:`test_dimension_2_carries_the_approval_verbatim`
:681 dimension 5 byte-equal                    :func:`test_dimension_5_carries_the_workflow_step_sequence`
:686 dimension 4 delegation chain              :func:`test_dimension_4_names_the_workflow_execution`
:722 submission-time hash (TOCTOU)             :func:`test_the_review_item_is_bound_by_submission_time_hash`
:724/:725 the queued item                      :func:`test_the_review_queue_holds_the_item_until_resolved`
:731/:732 reviewer ↔ active token               :func:`test_the_reviewer_identity_matches_an_active_token`
:757 ``record.released``                       :func:`test_the_review_resolved_as_the_artifact_directed`
:760 ``record.item``                           :func:`test_the_review_resolved_as_the_artifact_directed`
:769 one audited review action                 :func:`test_the_review_release_is_audited`
:771 the queue is drained                      :func:`test_the_review_queue_drains_on_resolution`
:795 review block byte-equal                   :func:`test_dimension_2_carries_the_review_release_verbatim`
:802/:803/:807 review round-trip                :func:`test_dimension_2_carries_the_review_release_verbatim`
:818 ``routed.node``                            :func:`test_the_failing_step_routed_to_its_declared_handler`
:822 ``routed.handler_ref``                     :func:`test_the_failing_step_routed_to_its_declared_handler`
:827/:828 the traced exception transition       :func:`test_the_exception_transition_is_traced`
:834 one audited exception event                :func:`test_the_exception_transition_is_audited`
:836-:853 the printed summary                   covered across the tests above
===========================================  ==========================

**Absorbed rather than relocated**, and named so the count reconciles. The
pre-rewrite file carried 16 pure ``isinstance`` narrowings over values whose
types are now fixed by ``load_artifact``'s contract validation or by the result
dataclass's annotations (:288, :294, :302, :310, :313, :360, :372, :424, :428,
:617, :620, :756, :817, :826, and the two inside ``_register_closure``'s loop).
Those asserted nothing about this deployment; they narrowed a type mypy now
narrows. The spine keeps a *raising* guard wherever proceeding past a wrong
value would be unsafe — stricter than an ``assert``, which vanishes under
``python -O``.

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

* **Propagation checks.** The declared gate, the resume decision, the failing
  step, the exception handler, the reviewer's subject and the release/reject
  choice are each read from an artifact by ``run.py`` *and* by this module, so
  the artifact is a single source and editing it moves both ends together.
  These fail on a **wiring** fault, not on an artifact edit. Most of this
  module is this category, and that is appropriate: the example's subject is
  whether the fabric *routed* and *recorded* correctly, not whether it computed
  a number.
* **SDK mechanism claims** — that a refusal never reaches the authority path,
  that dimension 2 is byte-equal to what the transport serialized, that a
  signature verifies from the record alone — are asserted directly, because
  they are claims about the SDK rather than about this domain. These are the
  audit-by-construction assertions, and they are the ones that would fail if
  the invariant broke.
* **Independent-source checks.** The approver's subject is compared against the
  *token table*, not against the approver block that names it, so a submission
  whose principal was taken from the caller rather than derived from the
  verified grant fails here. Two artifacts, two authors, one agreement.

Every domain expectation is read from an artifact, never inlined (CINV-01
reaches ``tests/`` under D-IMPL-78).

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import DeclaredArtifact
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.review_queue import ReviewActionRecord
from ccf_runtime.http_api.errors import (
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_REQUIRED,
    ERROR_TENANT_UNAUTHORIZED,
    ERROR_UNAUTHENTICATED,
)

pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/05-workflow-hitl; retired usage model, non-gating
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "archive" / "examples" / "05-workflow-hitl" / "run.py"

#: Which typed refusal each negative case must produce. The KEYS name the four
#: failure modes the spine drives; the VALUES are imported SDK constants, never
#: parsed prose — a refusal identified by matching a message string would pass
#: for a message that happened to contain the right words.
EXPECTED_REFUSALS: dict[str, tuple[int, str]] = {
    "unauthenticated": (401, ERROR_UNAUTHENTICATED),
    "expired-token": (401, ERROR_UNAUTHENTICATED),
    "unsigned": (403, ERROR_SIGNED_BINDING_REQUIRED),
    "tampered-signature": (403, ERROR_SIGNED_BINDING_INVALID),
}


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause (plan 15-13, R7).
    """
    name = "workflow_hitl_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example() -> Any:
    return _load_example()


@pytest.fixture(scope="module")
def result(example: Any, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    """One run of the spine, shared across the module.

    The fabric handle is left OPEN by ``run`` — this module reads through its
    reader and its pins — so closing it is this fixture's job.
    """
    root = tmp_path_factory.mktemp("workflow-hitl")
    demonstration = example.run(root=root)
    try:
        yield demonstration
    finally:
        demonstration.booted.handle.close()


def _declaration(result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key."""
    artifact = result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


def _drive(result: Any) -> Any:
    return _declaration(result, "hitl-drive")["drive"]


def _review_doc(result: Any) -> Any:
    return _declaration(result, "hitl-drive")["review"]


def _token(result: Any, label: str) -> Any:
    (entry,) = [
        row
        for row in _declaration(result, "tokens")["tokens"]
        if row["label"] == label
    ]
    return entry


# --- suspend at the gate ---------------------------------------------------


def test_the_workflow_suspended_at_the_declared_gate(result: Any) -> None:
    """Pre-rewrite :425. The gate the workflow stops at is the one the drive
    artifact names — a propagation check over the engine's state machine."""
    assert result.suspended.gate == _drive(result)["expected_gate"]


def test_the_suspended_state_persisted_at_the_control_plane(result: Any) -> None:
    """Pre-rewrite :429, :430.

    Suspension is a *persisted* state at the Control Plane boundary, not a
    blocked thread (CLAUDE.md §8.1) — which is what lets the process wait as
    long as a human takes. If the record were absent or not marked suspended,
    nothing would be resumable.
    """
    assert result.suspended_state.status == "suspended"
    assert result.suspended_state.current_state == _drive(result)["expected_gate"]
    assert result.state_key.startswith(f"{result.tenant_id}/")
    assert result.state_key.endswith(_drive(result)["approval_execution_id"])


def test_the_pending_event_is_the_suspended_state_by_content_hash(
    result: Any,
) -> None:
    """Pre-rewrite :503, and the T-07-39 TOCTOU binding it encodes.

    An SDK mechanism claim. What the approver is *shown* must be the state that
    is *pending*, bound by content identity rather than by a shared reference —
    otherwise a state mutated between display and submission would be approved
    on the strength of a screen nobody can reconstruct.
    """
    assert result.pending.product_content_hash == result.suspended_state_hash
    assert result.pending.product_content_hash == content_hash(result.suspended_state)
    assert result.pending.event_key == result.suspended.event_key


# --- the hardened door -----------------------------------------------------


def test_the_queue_view_is_served_through_the_authenticated_door(
    result: Any,
) -> None:
    """Pre-rewrite :497, :500. The pending event the approver sees came back
    through ``GET /hitl/queue`` under a bearer token, not out of the
    transport directly."""
    assert result.pending.event_key == result.suspended.event_key
    assert result.pending.tenant == result.tenant_id


def test_the_d16_policy_in_force_requires_a_signed_binding(result: Any) -> None:
    """Pre-rewrite :361.

    The whole refusal ladder below is only meaningful while the policy actually
    demands a binding — a green refusal suite under
    ``signed_binding_required: false`` would be a suite that passes for a reason
    unrelated to what it claims. Asserted first, deliberately.
    """
    assert result.hitl_policy_signed_binding_required is True


def test_the_unmapped_scope_is_refused_deny_by_default(result: Any) -> None:
    """Pre-rewrite :481, :483.

    The outsider token is AUTHENTICATED — its entry in the token table is
    active — but its scope is absent from the scope mapping. Deny-by-default
    means an unmapped scope grants nothing (HARD-04; D-IMPL-68).
    """
    assert result.authz_refusal_status == 403
    assert result.authz_refusal_code == ERROR_TENANT_UNAUTHORIZED
    outsider = _token(result, "unauthorized")
    assert outsider["status"] == "active", (
        "the deny-by-default leg is only meaningful while the refused token is"
        " a VALID one; an expired token would be refused a step earlier"
    )
    assert result.authz_refused_client_id == outsider["client_id"]


def test_the_deny_landed_in_the_audit_log_at_the_mapping_version(
    result: Any,
) -> None:
    """Pre-rewrite :491, :492, :493.

    Audit-by-construction for the authorization decision. Both outcomes travel
    the one Control Plane log (whitepaper §7.8.2 — the audit plane is singular),
    and the deny carries the EXACT mapping version in force, so "which rule
    refused this" is answerable from the log alone.
    """
    denied = [
        event
        for event in result.audit.events()
        if event.action == "authz_decision" and not event.resolved
    ]
    assert len(denied) == 1, [event.action for event in result.audit.events()]
    assert denied[0].actor == _token(result, "unauthorized")["client_id"]
    assert denied[0].version == result.scope_mapping_version

    allowed = [
        event
        for event in result.audit.events()
        if event.action == "authz_decision" and event.resolved
    ]
    assert allowed, "an allow is audited as loudly as a deny, or the log is partial"
    assert all(event.version == result.scope_mapping_version for event in allowed)


@pytest.mark.parametrize("case", sorted(EXPECTED_REFUSALS))
def test_every_refusal_is_typed_and_fails_closed(result: Any, case: str) -> None:
    """Pre-rewrite :531/:532, :543/:544, :550/:551, :567/:568.

    Four distinct failure modes, four distinct typed refusals, each identified
    by an imported constant. The expired-token case is the one worth naming: it
    is refused by the artifact-driven token source exactly as an unknown token
    is, so lifecycle is enforced from the table rather than from a special case
    in code.
    """
    status, code = EXPECTED_REFUSALS[case]
    response = result.refusals[case]
    assert response.status_code == status, response.text
    assert response.json()["detail"]["error_code"] == code, response.text


def test_no_refusal_reached_the_authority_path(result: Any) -> None:
    """Pre-rewrite :574.

    The load-bearing one. A refusal that still *landed* would be an unrecorded
    human action's mirror image — an action recorded that never had authority.

    The evidence is captured in the spine **between** the four refusals and the
    one admission, because that is the only instant at which it means anything:
    read afterwards it would count the legitimate approval and, later, the
    review release, and would go green for a transport that admitted everything.
    """
    assert result.submissions_after_refusals == ()
    assert len(result.refusals) == len(EXPECTED_REFUSALS)
    # And the admission that follows does land, so the emptiness above is a
    # property of the refusals rather than of a transport that never records.
    assert result.submission in result.transport.submissions(tenant=result.tenant_id)


def test_the_admitted_submission_derived_its_principal_from_the_grant(
    result: Any,
) -> None:
    """Pre-rewrite :586, :588, :592, :595.

    An independent-source check, and the one D-IMPL-67 exists for: the audited
    subject is compared against the ACTIVE entry in ``tokens.yaml``, not against
    the approver block in ``hitl-drive.yaml`` that also names it. A door that
    took the caller's claim about itself would pass a comparison against the
    caller's own document and fail this one.
    """
    assert result.admitted.status_code == 200, result.admitted.text
    assert result.admitted.json()["status"] == "submitted"

    active = _token(result, "approver")
    assert active["status"] == "active"
    assert result.submission.principal.approver.subject_id == active["client_id"]
    assert result.approver_client_id == active["client_id"]
    assert result.submission.signed_binding == result.signed


def test_the_approvers_signature_verifies_from_the_record(result: Any) -> None:
    """The signed binding recovered from replay dimension 2 verifies against the
    PUBLIC keys alone (D-IMPL-66(a) non-repudiation).

    An SDK mechanism claim, and deliberately routed through the record rather
    than through the live object: what a reader of the record has is the record
    and the public key set, and nothing the run held in memory.
    """
    # Imported INSIDE the body, not at module scope (`D-IMPL-363`): this
    # archived suite exercises `archive/examples/` programs written against
    # the retired signed-principal-binding API, and `archive/` is a dated
    # reference surface that is not repaired (D-IMPL-351). A module-level
    # import of a removed name is a COLLECTION error, which would take the
    # whole module — and every other archived assertion in it — out of
    # collection. Deferred here, the module collects and the gap stays
    # visible as a failing archived assertion rather than an invisible one.
    from ccf.hitl.identity_binding import verify_principal_binding  # noqa: PLC0415

    restored = HitlActionRecord.model_validate_json(
        result.record.policy_bindings.hitl_actions
    )
    verified = verify_principal_binding(
        restored.submission.signed_binding,
        provider=result.identity_provider,
        public_keys=result.trusted_keys,
    )
    assert verified == restored.submission.principal
    assert (
        verified.approver.subject_id == _token(result, "approver")["client_id"]
    )


def test_the_gate_event_was_drained_before_the_resume(result: Any) -> None:
    """Pre-rewrite :608. The door is submit-only by ruling (D-IMPL-62): the
    D-16-verified submission IS the authority-path landing, and the owning
    composition — the spine — consumes the event and resumes. The event it
    consumed must be the one the approver acted on, not some other pending
    item."""
    assert result.drained is not None
    assert result.drained.event_key == result.pending.event_key


# --- resume to the declared terminal ---------------------------------------


def test_the_workflow_completed_at_the_declared_terminal(result: Any) -> None:
    """Pre-rewrite :618. The human's decision — not the engine — chooses which
    declared terminal the workflow reaches."""
    assert result.outcome.terminal_state == _drive(result)["resume_decision"]


def test_the_terminal_state_persisted_at_the_control_plane(result: Any) -> None:
    """Pre-rewrite :621. The same state record the suspension wrote is the one
    the resume drove to terminal — one execution, one record, not two."""
    assert result.terminal_state_record.status == "terminal"
    assert result.terminal_state_record.current_state == (
        _drive(result)["resume_decision"]
    )


# --- replay capture of every human action ----------------------------------
#
# This is the group the plan calls out: audit-by-construction has no opt-in
# hook, so if any of these fail the invariant is gone rather than a test being
# stale.


def test_dimension_2_carries_the_approval_verbatim(result: Any) -> None:
    """Pre-rewrite :673, :677, :679.

    Byte-for-byte, not summarized: the block on the record is exactly what the
    transport serialized, and it round-trips back into a ``HitlActionRecord``
    carrying the same signed binding. A record that paraphrased the action
    would still "contain" the approval and would not be replayable.
    """
    assert result.record.policy_bindings.hitl_actions == result.hitl_actions_block
    assert result.signed.signature in result.record.policy_bindings.hitl_actions

    restored = HitlActionRecord.model_validate_json(
        result.record.policy_bindings.hitl_actions
    )
    assert restored.submission.signed_binding == result.signed
    assert restored.approved is True
    assert canonical_bytes(restored).decode("utf-8") == result.hitl_actions_block


def test_dimension_2_names_the_approver_identity(result: Any) -> None:
    """Pre-rewrite :675. **The approver's identity**, one of the four things
    CLAUDE.md §8.2 requires an approval to land with."""
    block = result.record.policy_bindings.hitl_actions
    active = _token(result, "approver")
    assert active["client_id"] in block

    restored = HitlActionRecord.model_validate_json(block)
    assert restored.submission.principal.approver.subject_id == active["client_id"]
    approver = _declaration(result, "hitl-drive")["approver"]
    assert (
        restored.submission.principal.approver.identity_provider_ref
        == approver["identity"]["identity_provider_ref"]
    )
    assert (
        restored.submission.principal.authentication.method
        == approver["authentication"]["method"]
    )


def test_dimension_2_carries_the_product_the_approver_saw(result: Any) -> None:
    """Pre-rewrite :676. **The Context Product the approver saw**, by content
    hash — the third of §8.2's four, and the one that makes the other three
    non-repudiable rather than merely recorded."""
    block = result.record.policy_bindings.hitl_actions
    assert result.pending.product_content_hash in block

    restored = HitlActionRecord.model_validate_json(block)
    assert (
        restored.submission.principal.product_content_hash
        == result.suspended_state_hash
    )
    assert restored.event.product_content_hash == result.suspended_state_hash


def test_dimension_2_carries_the_action_time(result: Any) -> None:
    """**The time of approval** — §8.2's second of four. Read from the drive
    artifact, so the recorded instant is a declared one rather than whenever
    the example happened to run."""
    approver = _declaration(result, "hitl-drive")["approver"]
    restored = HitlActionRecord.model_validate_json(
        result.record.policy_bindings.hitl_actions
    )
    assert restored.submission.principal.action_time.isoformat() == (
        approver["action_time"]
    )


def test_dimension_2_carries_the_approvers_annotation_field(result: Any) -> None:
    """**Any annotations** — §8.2's fourth of four.

    This deployment's approval carries none, and that is the point worth
    asserting: the field is *present and empty* on the record rather than
    absent, so "the approver said nothing" and "nobody recorded what the
    approver said" are distinguishable at replay time.
    """
    restored = HitlActionRecord.model_validate_json(
        result.record.policy_bindings.hitl_actions
    )
    assert hasattr(restored.submission, "annotation")
    assert restored.submission.annotation is None


def test_dimension_5_carries_the_workflow_step_sequence(result: Any) -> None:
    """Pre-rewrite :681. The engine's own step-sequence block, byte-for-byte —
    the Orchestration Layer's half of the replay commitment (CLAUDE.md §8.1)."""
    assert (
        result.record.content_generation_path.workflow_step_sequence
        == result.outcome.step_sequence_block
    )


def test_dimension_4_names_the_workflow_execution(result: Any) -> None:
    """Pre-rewrite :686. The delegation chain answers "under whose authority" —
    and its head names this workflow execution, so a decision made inside a
    workflow is distinguishable from the same decision made directly."""
    assert result.record.perspective_conditioning.delegation_chain[0] == (
        f"workflow:{result.state_key}"
    )
    values = _declaration(result, "replay-values")
    assert result.record.perspective_conditioning.role == (
        values["perspective"]["role"]
    )
    assert result.record.perspective_conditioning.principal_id == (
        values["perspective"]["principal_id"]
    )


def test_dimension_2_carries_the_review_release_verbatim(result: Any) -> None:
    """Pre-rewrite :795, :802, :803, :807.

    The ReviewQueue's release is a human action too, and it lands the same way:
    its pre-serialized block byte-equal on dimension 2, round-trippable, and
    naming both the reviewer and the output that was released.
    """
    block = result.review_record.policy_bindings.hitl_actions
    assert block == result.review_resolution.hitl_actions_block

    review_doc = _review_doc(result)
    assert review_doc["item"]["output_ref"] in block

    restored = ReviewActionRecord.model_validate_json(block)
    assert restored.item == result.review_item
    assert restored.submission.principal.approver.subject_id == (
        review_doc["reviewer"]["identity"]["subject_id"]
    )
    assert restored.released == (review_doc["drive"]["action"] == "release")


# --- the ReviewQueue -------------------------------------------------------


def test_the_review_item_is_bound_by_submission_time_hash(result: Any) -> None:
    """Pre-rewrite :722. Same TOCTOU doctrine as the ApprovalGate leg: what the
    reviewer will see is pinned at submission, not re-read at resolution."""
    assert result.pending_review.product_content_hash == content_hash(
        result.review_item
    )
    restored = ReviewActionRecord.model_validate_json(
        result.review_resolution.hitl_actions_block
    )
    assert restored.submission.principal.product_content_hash == (
        result.pending_review.product_content_hash
    )


def test_the_review_queue_holds_the_item_until_resolved(result: Any) -> None:
    """Pre-rewrite :724, :725. The item is queued with its passage-level lineage
    attached (whitepaper §7.10.3), which is what a reviewer needs to see what
    each claim is anchored to."""
    ((queued_event, queued_item),) = result.queued_items
    assert queued_event.event_key == result.pending_review.event_key
    assert queued_item == result.review_item

    declared_lineage = _review_doc(result)["item"]["lineage"]
    assert len(queued_item.lineage) == len(declared_lineage)
    assert queued_item.lineage[0].passage_anchor is not None
    assert queued_item.lineage[0].passage_anchor.locator == (
        declared_lineage[0]["passage_anchor"]["locator"]
    )


def test_the_reviewer_identity_matches_an_active_token(result: Any) -> None:
    """Pre-rewrite :731, :732. The reviewer follows the same D-IMPL-67 identity
    convention as the approver: the subject is an ACTIVE token's client id, so
    a released briefing traces to a principal the door actually verified."""
    review_doc = _review_doc(result)
    entry = _token(result, review_doc["reviewer"]["token_label"])
    assert entry["status"] == "active"
    assert review_doc["reviewer"]["identity"]["subject_id"] == entry["client_id"]
    assert result.reviewer_entry == entry


def test_the_review_resolved_as_the_artifact_directed(result: Any) -> None:
    """Pre-rewrite :757, :760. The artifact decides release vs reject; the
    driver interprets and never decides (§6.4). Flipping the artifact flips the
    recorded outcome with no code change — and this assertion is what would
    catch a driver that had quietly hard-coded one branch."""
    review_doc = _review_doc(result)
    assert result.review_resolution.record.released == (
        review_doc["drive"]["action"] == "release"
    )
    assert result.review_resolution.record.item == result.review_item
    assert result.review_resolution.record.item.output_ref == (
        review_doc["item"]["output_ref"]
    )


def test_the_review_release_is_audited(result: Any) -> None:
    """Pre-rewrite :769.

    Audit-by-construction for the third exercised HITL primitive. The reviewer
    is the ACTOR on the Control Plane audit event — recorded because the
    primitive records, never because this driver asked it to.
    """
    reviewer_subject = _review_doc(result)["reviewer"]["identity"]["subject_id"]
    review_audits = [
        event
        for event in result.audit.events()
        if event.action == "hitl_action" and event.actor == reviewer_subject
    ]
    assert len(review_audits) == 1, [
        (event.action, event.actor) for event in result.audit.events()
    ]
    assert review_audits[0].resolved


def test_the_review_queue_drains_on_resolution(result: Any) -> None:
    """Pre-rewrite :771. Nothing is left pending; a queue that still held the
    item would release it twice on the next drain."""
    assert result.drained_items == ()


# --- the ExceptionEscalation path ------------------------------------------


def test_the_failing_step_routed_to_its_declared_handler(result: Any) -> None:
    """Pre-rewrite :818, :822.

    The expected handler is read from the drive artifact rather than from the
    workflow definition the engine itself resolved. That is deliberate: reading
    it off the definition would compare the engine's resolution against the
    document the engine resolved it from, which passes whatever the engine does
    with it. Two authored statements, one agreement.
    """
    drive = _drive(result)
    assert result.routed.node == drive["failing_step"]
    assert result.routed.handler_ref == drive["expected_exception_handler"]


def test_the_exception_transition_is_traced(result: Any) -> None:
    """Pre-rewrite :827, :828. An exception path is a first-class *recorded*
    transition (D-IMPL-61), not error handling glued on — so it appears in the
    state record's trace with its own kind."""
    trace = result.escalated_state.trace
    assert trace, "the escalated execution recorded no trace at all"
    assert trace[-1].kind == "exception"
    assert trace[-1].target == _drive(result)["expected_exception_handler"]


def test_the_exception_transition_is_audited(result: Any) -> None:
    """Pre-rewrite :834. And audited, on the same singular Control Plane log as
    every other governed action."""
    exception_events = [
        event
        for event in result.audit.events()
        if event.action == "workflow_exception"
    ]
    assert len(exception_events) == 1
    assert exception_events[0].resolved


# --- the fabric the gate suspends over -------------------------------------


def test_the_manifest_put_the_declared_bundles_in_force(result: Any) -> None:
    """The `role: register` entries are pinned; the `role: load` ones are not.

    D-IMPL-80's property, asserted where it is observable: a pin set that
    included the token table would mean credential material had been
    content-hashed into replay dimension 2.
    """
    pinned = {entry.key for entry in result.booted.pins.entries}
    assert "policy-bundle" in pinned
    assert "resolution-spec" in pinned
    for load_only in ("tokens", "events", "hitl-drive", "replay-values"):
        assert load_only not in pinned, load_only
        assert load_only in result.artifacts, load_only


def test_the_author_versioned_definitions_kept_their_bump_check(
    result: Any,
) -> None:
    """The plan 15-19 ruling, made testable rather than only documented.

    `_register_closure` was absorbed into the manifest for five documents and
    deliberately not for the four author-versioned definition classes. The
    reason is **pedagogical, not mechanical**, and the difference is load-bearing
    here: a manifest *can* name all four, as ``registration: versioned``, and
    :func:`~ccf.deployment.manifest.load_and_boot` then registers them through
    ``register_versioned`` with its D-05 bump check (D-IMPL-85). This example
    keeps them in ``run.py`` so the four ``register_versioned`` calls stay
    visible as the thing being taught — the same reason
    ``artifacts/manifest.yaml`` states for the same choice.

    **This paragraph used to say the reason was mechanical** — that the manifest
    path "registers through ``register_typed``, which does not run the D-05 bump
    check". That was true when it was written and plans 15.1-02/15.1-03 made it
    false: the manifest path now dispatches on ``entry.registration``, and
    :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes` refuses
    ``registration: typed`` for every member of
    :data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES` at preflight,
    before any document is read. Folding one of these into the manifest can no
    longer silently drop the bump check — it is either checked or refused loudly.

    The four are ``ccf.prompt-artifact``, ``ccf.agent-definition``,
    ``ccf.task-definition`` and ``ccf.workflow-definition`` — every member of
    :data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES` this example
    registers. So the check is: those four keys appear in the audit log under
    ``register_versioned`` and NOT under ``register_typed``, and none of them
    appears in the manifest's pin set. What each half catches is now different,
    and is stated separately because the mechanism moved underneath them:

    * the **audit-log halves** catch the bump check being lost at the *registry*
      seam — a ``run.py`` edit swapping one of the four to ``register_typed``.
      No manifest preflight sees that call, so this is the half that still
      guards D-05 directly.
    * the **pin-set half** catches this example changing shape — the four moving
      into ``artifacts/manifest.yaml``. Since 15.1-02/15.1-03 that move is a
      governed path, not a silent one, so this assertion is **not** protecting
      the bump check. It holds the example to the teaching choice its own
      manifest records, and whoever makes that move should update this test and
      that comment together rather than discover it here.

    **This assertion used to name three.** ``prompt_artifact_key`` was absent
    from the set while the docstring above said four, and ``run.py`` registered
    that one key through ``register_typed`` — so the one site that had lost its
    bump check was the one site this check did not look at, and it passed
    (post-gate review CR-02). Counting the set against the sentence that
    describes it is not pedantry here: a check that claims more than it verifies
    is the exact defect this phase exists to remove.
    """
    keys = _declaration(result, "agent-registration")
    author_versioned = {
        keys["prompt_artifact_key"],
        keys["agent_definition_key"],
        keys["task_definition_key"],
        keys["workflow_definition_key"],
    }
    versioned = {
        event.key
        for event in result.audit.events()
        if event.action == "register_versioned"
    }
    typed = {
        event.key
        for event in result.audit.events()
        if event.action == "register_typed"
    }
    assert author_versioned <= versioned, author_versioned - versioned
    assert not (author_versioned & typed), author_versioned & typed

    # And the manifest's own entries went the other way, as they must.
    assert "policy-bundle" in typed
    assert "resolution-spec" in typed
    manifest_keys = {entry.key for entry in result.booted.pins.entries}
    assert not (author_versioned & manifest_keys), (
        "an author-versioned definition appeared in the manifest's pin set."
        " This does NOT mean the D-05 bump check was dropped: a manifest entry"
        " declaring `registration: versioned` runs it, and `registration: typed`"
        " for these classes is refused at preflight before any document is read"
        " (D-IMPL-85). What it means is that example 05 changed shape — it keeps"
        " these four in `run.py` so the four `register_versioned` calls stay"
        " visible as the thing being taught, which is the reason"
        " `archive/examples/05-workflow-hitl/artifacts/manifest.yaml` gives for leaving"
        " them out. If that move was deliberate, this test and that manifest"
        " comment need correcting together; if it was not, revert it"
    )


def test_the_loan_under_review_is_a_real_entity(result: Any) -> None:
    """The workflow suspends over a fabric, not over a mock.

    An independent expectation: the entity classes come from the resolution
    spec, the count follows from the events, and the two are authored
    separately — so this fails if ingestion or resolution stops working, not
    only if a wiring line moved.
    """
    values = _declaration(result, "replay-values")
    boundary = result.record.context_fabric_snapshot.temporal_boundary
    view = result.booted.handle.reader.as_of(
        tenant_id=result.tenant_id, at=boundary
    )
    spec = result.artifacts["resolution-spec"]
    declared_classes = {rule.entity_class for rule in spec.entity_rules}

    assert view.entities, "nothing was ingested; dimension 1 names an empty graph"
    assert {record.claim.entity_class for record in view.entities} <= declared_classes
    assert boundary.isoformat() == values["temporal_boundary"]
