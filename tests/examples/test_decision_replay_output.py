"""The decision-replay example's assertions, grouped by replay dimension (D-09).

``examples/06-decision-replay/run.py`` used to carry its own guarantee: 101
``assert`` statements and 29 ``print`` summaries, checked by ``make example-06``
exiting zero. D-09 moves that guarantee here, because ``make examples`` proves a
spine *runs* and ``pytest`` proves it is *correct*.

This is the largest relocation in the suite, and the example it relocates is the
one whose subject is the five-dimension Decision Replay record itself
(whitepaper §7.10.1). So the tests below are grouped by **the dimension each one
covers**, and the mapping is stated rather than implied:

======================================  ==================================
Dimension                                Covered by
======================================  ==================================
1 — Context Fabric Snapshot              :func:`test_dimension_1_snapshot_is_at_the_declared_boundary`,
                                         :func:`test_dimension_1_the_reproduction_is_byte_equal`
2 — Policy Bindings Snapshot             :func:`test_dimension_2_carries_the_pin_the_adopter_selected`,
                                         :func:`test_dimension_2_the_record_is_version_sensitive`,
                                         :func:`test_dimension_2_carries_the_approval_verbatim`,
                                         :func:`test_dimension_2_carries_both_override_values`
3 — Model Version Record                 :func:`test_dimension_3_a_keyless_deployment_records_no_model`
4 — Perspective Conditioning             :func:`test_dimension_4_carries_the_declared_perspective`,
                                         :func:`test_dimension_4_the_agent_resolves_at_its_recorded_hash`,
                                         :func:`test_dimension_4_the_prompt_resolves_at_the_pinned_version`,
                                         :func:`test_dimension_4_the_skill_set_in_force_recomputes`
5 — Content Generation Path              :func:`test_dimension_5_carries_the_declared_plan_id`,
                                         :func:`test_dimension_5_carries_the_workflow_step_sequence`
======================================  ==================================

Where each relocated assertion came from
-----------------------------------------

Pre-rewrite line numbers are against the file at the plan's base commit, so the
"nothing lost" claim is auditable rather than merely stated:

===========================================  ==========================
pre-rewrite ``run.py`` line                   relocated to
===========================================  ==========================
:628 ``signed_binding_required is True``      :func:`test_the_d16_policy_in_force_requires_a_signed_binding`
:717 ``isinstance(gated, ServableProduct)``   the spine itself (a refusal now
                                              raises) **and**
                                              :func:`test_the_product_passed_all_three_gates`
:719 ``entity_count``                         :func:`test_the_served_payload_matches_the_declared_expectation`
:754 ``granted == content_hash(grant)``       :func:`test_the_grant_was_admitted_at_its_content_identity`
:756 ``in_force == grant_set_hash(...)``      :func:`test_dimension_4_the_skill_set_in_force_recomputes`
:757 ``agent.consume(...) is product``        :func:`test_the_agent_consumed_the_gated_product_itself`
:763 skill dispatch output                    :func:`test_the_skill_produced_the_declared_output`
:802 ``suspended.gate``                       :func:`test_the_workflow_suspended_at_the_declared_gate`
:847 ``status_code == 403``                   :func:`test_the_unmapped_scope_is_refused_deny_by_default`
:849 ``ERROR_TENANT_UNAUTHORIZED``            :func:`test_the_unmapped_scope_is_refused_deny_by_default`
:857 one deny in the audit log                :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`
:858 deny actor                               :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`
:859 deny mapping version                     :func:`test_the_deny_landed_in_the_audit_log_at_the_mapping_version`
:866 ``pending.product_content_hash``          :func:`test_the_approver_signed_the_hash_of_what_they_were_shown`
:891 approver subject id                      :func:`test_dimension_2_carries_the_approval_verbatim`
:892 ``submission.signed_binding``             :func:`test_dimension_2_carries_the_approval_verbatim`
:910 ``outcome.terminal_state``                :func:`test_the_workflow_completed_at_the_declared_terminal`
:965 proposal-time hash (TOCTOU)              :func:`test_the_overrider_echoed_the_proposal_time_hash`
:991 ``resolution.record.overridden``          :func:`test_the_override_resolved_as_the_artifact_directed`
:992 ``resolution.record.original``            :func:`test_the_override_resolved_as_the_artifact_directed`
:994 ``resolution.record.final``               :func:`test_the_override_resolved_as_the_artifact_directed`
:997/:1001 both values in the block            :func:`test_dimension_2_carries_both_override_values`
:1101 byte-equal reproduction                  :func:`test_dimension_1_the_reproduction_is_byte_equal`
:1104 address agreement                        :func:`test_dimension_1_the_reproduction_is_byte_equal`
:1118 dimension-4 URI ends at the version      :func:`test_dimension_4_the_agent_resolves_at_its_recorded_hash`
:1121 resolved definition content hash         :func:`test_dimension_4_the_agent_resolves_at_its_recorded_hash`
:1134 prompt artifact version                  :func:`test_dimension_4_the_prompt_resolves_at_the_pinned_version`
:1145 grant-set hash recomputation             :func:`test_dimension_4_the_skill_set_in_force_recomputes`
:1154/:1162/:1163/:1166 binding verification   :func:`test_dimension_2_carries_the_approval_verbatim`,
                                               :func:`test_the_approver_signed_the_hash_of_what_they_were_shown`
:1171 workflow trace on dimension 5            :func:`test_dimension_5_carries_the_workflow_step_sequence`
:1186 override reproduction byte-equal         :func:`test_the_override_record_reproduces_the_same_product`
:1193/:1194/:1195 override round-trip          :func:`test_dimension_2_carries_both_override_values`
:1197/:1201 both values byte-present           :func:`test_dimension_2_carries_both_override_values`
:1206/:1212/:1213 overrider signature          :func:`test_the_overriders_signature_verifies_from_the_record`
:1231 moving-target refused                    :func:`test_a_moving_target_ref_is_refused`
:1251 ``mutated != resolved``                  :func:`test_dimension_2_the_record_is_version_sensitive`
:1269 reproduction refuses                     :func:`test_dimension_2_the_record_is_version_sensitive`
:1288-:1316 the printed summary                covered across the dimension
                                               tests above
===========================================  ==========================

**Absorbed rather than relocated**, and named so the count reconciles: the
pre-rewrite file carried 14 pure ``isinstance`` narrowings over values whose
types are now fixed by ``load_artifact``'s own contract validation or by the
result dataclass's annotations (:600, :605, :610, :613, :620, :625, :627, :639,
:726, :727, :747, :762, :805, :990). Those asserted nothing about this
deployment; they narrowed a type mypy now narrows. :901's
``dequeue(...) is not None`` is likewise absorbed — the spine unpacks exactly one
submission, which fails louder than the assertion did.

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

* **Independent expectations.** ``expected.yaml`` declares what the *served
  product* should contain. Nothing in the pipeline derives those numbers from
  that file — they follow from the events, the resolution spec and the four
  operators — so changing either side alone makes the assertion fail.
* **Propagation checks.** The temporal boundary, the perspective role, the
  declared gate, the terminal state and the required operator set are each read
  from an artifact by ``run.py`` *and* by this module, so the artifact is a
  single source and editing it moves both ends together. These fail on a
  **wiring** fault, not on an artifact edit.
* **SDK mechanism claims** — that a keyless deployment records
  ``model_version: none``, that the replay reference is the record's own content
  hash, that a moving-target ref raises ``MovingTargetRefused`` — are asserted
  directly, because they are claims about the SDK rather than about this domain.

``test_dimension_4_the_skill_set_in_force_recomputes`` deserves a specific
caveat, because it is the shape this phase has repeatedly over-claimed: it
recomputes ``grant_set_hash`` from the grant **resolved out of the
ArtifactStore**, and compares it against the value the record carries. The two
ends are the store and the record, which is a real independence — but the grant
that went into the store and the grant the ledger hashed are one object, so this
detects a broken store round-trip or a broken recording, not a wrong grant.

Every domain expectation is read from an artifact, never inlined (CINV-01 reaches
``tests/`` under D-IMPL-78).

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest

from ccf.artifacts.protocol import (
    LATEST_VERSION_TOKEN,
    MovingTargetRefused,
    artifact_uri,
)
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.identity_binding import verify_principal_binding
from ccf.hitl.override import OverrideActionRecord
from ccf.hitl.transport import HITL_POLICY, HitlPolicy
from ccf.replay.engine import (
    ReplayUnresolvable,
    replay,
    resolve_artifact_at_uri,
)
from ccf.replay.record import DecisionReplayRecord
from ccf.skills.grants import grant_set_hash
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "06-decision-replay" / "run.py"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause (plan 15-13, R7).
    """
    name = "decision_replay_under_test"
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
def result(
    example: Any, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Any]:
    """One run of the spine, shared across the module.

    The fabric handle is left OPEN by ``run`` — the replay leg reads through its
    reader, and so do this module's own negative probes — so closing it is this
    fixture's job.
    """
    root = tmp_path_factory.mktemp("decision-replay")
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


def _stored_record(result: Any) -> DecisionReplayRecord:
    """The canonical record, read back out of the ArtifactStore."""
    return DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )


# --- the gates and the served product --------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :717. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran."""
    assert result.product is not None
    assert result.served.replay_ref is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """What the product claims ran is exactly what the engine resolved
    (Gate 2, INV-CH7-47).

    **What the two sides now are.** The left is the Control Plane CLAIM — the
    product class's ``required_operator_keys``, transcribed into the Contract's
    lineage. The right is the engine's report of executing the plan, which the
    plan built from ``artifacts/projection-requirements.yaml``. Before Phase
    15.1 both sides were ``execution.operators_invoked`` and this assertion
    compared one object against itself.

    **What it still does not show.** The engine is a faithful transcriber of the
    plan, not an independent witness of it: it builds ``operators_invoked`` and
    its steps in one loop over the same operator plan. So what this verifies is
    ASSEMBLY-PATH INTEGRITY — that the product served was assembled by the path
    the deployment claimed — and not that the claim was right. Authorable drift
    between the two documents fails upstream, at
    ``refuse_operator_set_divergence``, before the engine ever runs. A
    deployment that read one of those two artifacts into the other would
    collapse that binder, and this assertion would not see it.
    """
    assert result.product.lineage.operators_invoked == result.operators_invoked


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """The set the product class DECLARED it requires is exactly the set the
    engine RESOLVED.

    **What this does and does not prove.** ``operators_invoked`` is planned from
    ``plan.required_operators()``, which since Phase 15.1 this deployment feeds
    from ``projection-requirements.yaml`` — a document separate from the
    ``product-class.yaml`` this assertion's left side reads. So editing either
    artifact alone no longer moves both ends silently: it makes the two
    documents disagree, and ``refuse_operator_set_divergence`` refuses the run
    before the engine executes. This assertion is therefore reachable only when
    the two documents already agree, which is why it is not the phase's drift
    check and is not claimed as one.

    What it still guards is the ``operators.keys()`` shortcut in either the
    record phase or the replay environment — a plan that answered from the
    operator registry rather than from its artifact would make both this and
    Gate 2 compare a value against itself (plan 15-13, R6). And the residual is
    unchanged in kind: a deployment that transcribed one of the two artifacts
    out of the other collapses the binder, so dual authorship stays
    convention-assisted at the authoring boundary (D-IMPL-86).
    """
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(result.operators_invoked)


def test_the_served_payload_matches_the_declared_expectation(result: Any) -> None:
    """Pre-rewrite :719, and the two payload facts its print summarized.

    An independent expectation: the RESTRICTED spur is gone because policy
    substituted it out with its edge, and the routine-load feeder is gone because
    similarity ranked it out. This fails if any of the four operators stops
    working.
    """
    expected = _declaration(result, "expected")
    payload = result.product.payload

    assert payload["entity_count"] == expected["entity_count"], payload
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == sorted(
        expected["entity_classes"]
    ), payload
    assert payload["relationship_types"] == sorted(
        expected["relationship_types"]
    ), payload


# --- dimension 1 — Context Fabric Snapshot ---------------------------------


def test_dimension_1_snapshot_is_at_the_declared_boundary(result: Any) -> None:
    """A propagation check: the boundary `decision.yaml` names is the boundary
    the record snapshots at."""
    decision = _declaration(result, "decision")
    assert _stored_record(result).context_fabric_snapshot.temporal_boundary == (
        datetime.fromisoformat(decision["temporal_boundary"])
    )


def test_dimension_1_the_reproduction_is_byte_equal(result: Any) -> None:
    """Pre-rewrite :1101 and :1104 — the example's whole point.

    Byte equality through the canonical serializer, not field-by-field equality:
    the same bytes, from a re-execution against the logical snapshot the record
    names (whitepaper §7.10).
    """
    assert canonical_bytes(result.reproduced) == canonical_bytes(result.product)
    assert (
        result.reproduced_address
        == result.reproduced_record.content_generation_path.product_content_address
    )


def test_the_replay_record_is_in_the_store_content_addressed(result: Any) -> None:
    """SDK mechanism: the address IS the record's own content hash."""
    address = result.served.replay_ref.content_address
    assert result.store.exists(content_address=address)
    assert address == content_hash(result.record)


def test_the_stored_record_round_trips_exactly(result: Any) -> None:
    """Not merely parseable — equal."""
    assert _stored_record(result) == result.record


# --- dimension 2 — Policy Bindings Snapshot --------------------------------


def test_dimension_2_carries_the_pin_the_adopter_selected(result: Any) -> None:
    """The binding the spine selected by an explicit ``pins.version_for``
    lookup is the binding the record carries, and it is the one version the
    product's lineage claims.

    The record's binding and the product's lineage are built by two separate
    calls taking two different argument shapes (``PolicyBinding(key=, version=)``
    against a bare version set), so this fails if either is wired to the wrong
    pin. It does NOT independently re-derive the version — the pin has one
    source, by design (D-06 keeps the selection in adopter hands), and claiming
    otherwise would be the tautology this module exists to avoid.
    """
    restored = _stored_record(result)
    assert [binding.version for binding in restored.policy_bindings.bindings] == [
        result.policy_version
    ]
    assert result.product.lineage.policy_bundle_versions == frozenset(
        {result.policy_version}
    )
    # And the reproduction carries it unchanged: a replay that re-derived
    # dimension 2 from the live Control Plane rather than reading it out of the
    # record would reproduce against whatever is in force NOW.
    assert [
        binding.version
        for binding in result.reproduced_record.policy_bindings.bindings
    ] == [result.policy_version]


def test_dimension_2_the_record_is_version_sensitive(result: Any) -> None:
    """Pre-rewrite :1251 and :1269.

    The spine stored a COPY of the record with its recorded policy-bundle version
    bumped to one the Control Plane never registered. Replaying that copy must
    REFUSE — an audit record that reproduced against a version that was never in
    force would be descriptive rather than binding.
    """
    probes = _declaration(result, "replay-probes")
    mutated = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.mutated_record_address)
    )
    assert mutated != result.reproduced_record
    assert [binding.version for binding in mutated.policy_bindings.bindings] == [
        probes["unregistered_policy_version"]
    ]

    with pytest.raises(ReplayUnresolvable):
        replay(
            record_address=result.mutated_record_address,
            store=result.store,
            reader=result.booted.handle.reader,
            control_plane=result.registry,
            environment=result.environment,
        )


def test_dimension_2_carries_the_approval_verbatim(result: Any) -> None:
    """Pre-rewrite :891, :892, :1154, :1162, :1163.

    The approval's signed binding verifies from the RECORD alone — nothing from
    the live run is consulted except the public keys — and the principal it
    reproduces is byte-identical to the recorded submission's, with the
    grant-derived subject the token table names.
    """
    action = HitlActionRecord.model_validate_json(
        _stored_record(result).policy_bindings.hitl_actions
    )
    assert action.submission.signed_binding is not None
    reproduced = verify_principal_binding(
        action.submission.signed_binding,
        provider=result.identity_provider,
        public_keys=result.trusted_keys,
    )
    assert reproduced == action.submission.principal
    assert reproduced.approver.subject_id == result.approver_client_id


def test_dimension_2_carries_both_override_values(result: Any) -> None:
    """Pre-rewrite :997, :1001, :1193, :1194, :1195, :1197, :1201.

    §8.2 requires BOTH the agent's original output and the human's override in
    the record. Asserted twice over, deliberately: the typed
    ``OverrideActionRecord`` round-trips out of the reproduced record, AND both
    canonical serializations appear literally in the recorded block — an override
    that lost the original would be unrepudiable, so this is not a place to trust
    a parser.
    """
    block = result.reproduced_override_record.policy_bindings.hitl_actions
    determination = result.override_original.__class__
    action = OverrideActionRecord[determination].model_validate_json(block)

    assert action.overridden == result.override_overridden
    assert action.original == result.override_original
    assert action.final == result.override_final
    assert canonical_bytes(result.override_original).decode("utf-8") in block
    assert canonical_bytes(result.override_final).decode("utf-8") in block


# --- dimension 3 — Model Version Record ------------------------------------


def test_dimension_3_a_keyless_deployment_records_no_model(result: Any) -> None:
    """SDK mechanism claim, asserted directly: nothing in this run calls a model,
    and dimension 3 says so rather than being absent."""
    assert _stored_record(result).model_version.model_version == "none"


# --- dimension 4 — Perspective Conditioning --------------------------------


def test_dimension_4_carries_the_declared_perspective(result: Any) -> None:
    """A propagation check against `perspective.yaml`."""
    perspective = result.artifacts["perspective"]
    assert _stored_record(result).perspective_conditioning.role == perspective.role


def test_dimension_4_the_agent_resolves_at_its_recorded_hash(result: Any) -> None:
    """Pre-rewrite :1118 and :1121.

    The definition comes back from the store at the content address dimension 4
    recorded — not by name, not at "latest" — and the versioned URI the record
    carries ends at exactly that artifact's own version.
    """
    dimension_four = _stored_record(result).perspective_conditioning
    assert dimension_four.agent_definition_uri.endswith(
        f"@{result.resolved_definition.artifact_version}"
    )
    assert content_hash(result.resolved_definition) == content_hash(
        result.definition
    )
    assert dimension_four.agent_definition_hash == content_hash(result.definition)


def test_dimension_4_the_prompt_resolves_at_the_pinned_version(result: Any) -> None:
    """Pre-rewrite :1134. The prompt resolves at the version the RESOLVED
    definition's instruction binding pins, not at whatever is in the store."""
    assert (
        result.resolved_prompt.artifact_version
        == result.resolved_prompt_pinned_version
    )
    assert content_hash(result.resolved_prompt) == content_hash(result.prompt)


def test_dimension_4_the_skill_set_in_force_recomputes(result: Any) -> None:
    """Pre-rewrite :756 and :1145.

    The decision replays against the skills the agent ACTUALLY had: the recorded
    grant-set hash recomputes from the grant resolved back out of the store. See
    the module docstring for what this does and does not prove.
    """
    recomputed = grant_set_hash(frozenset({content_hash(result.resolved_grant)}))
    assert _stored_record(result).perspective_conditioning.grant_set_hash == (
        recomputed
    )
    assert result.grant_set_hash == recomputed


def test_a_moving_target_ref_is_refused(result: Any) -> None:
    """Pre-rewrite :1231 (D-IMPL-26).

    The only place the moving-target token appears in this example. Replay
    resolves exact versions; a ref asking for "latest" is refused rather than
    answered, because an audit trail that resolved a moving target would
    reproduce a different decision tomorrow.
    """
    moving_target = artifact_uri(
        tenant_id=result.tenant_id,
        artifact_class=result.agent_definition_class,
        name=result.definition.name,
        artifact_version=LATEST_VERSION_TOKEN,
    )
    with pytest.raises(MovingTargetRefused):
        resolve_artifact_at_uri(
            store=result.store,
            uri=moving_target,
            contract=result.definition.__class__,
        )


# --- dimension 5 — Content Generation Path ---------------------------------


def test_dimension_5_carries_the_declared_plan_id(result: Any) -> None:
    """A propagation check: the plan id `product-governance.yaml` declares is
    the plan id dimension 5 records, and the one the replay environment
    resolved."""
    governance = _declaration(result, "product-governance")
    assert _stored_record(result).content_generation_path.plan_id == (
        governance["plan_id"]
    )
    assert result.product.plan_id == governance["plan_id"]
    # The replay environment resolved the SAME plan by id, so the reproduction
    # is an interpretation of the graph the record named, not a fresh one.
    assert result.reproduced.plan_id == governance["plan_id"]


def test_dimension_5_carries_the_workflow_step_sequence(result: Any) -> None:
    """Pre-rewrite :1171. The engine's own serialization of the step sequence,
    verbatim and non-empty (§8.1)."""
    block = _stored_record(result).content_generation_path.workflow_step_sequence
    assert block.startswith("[")
    assert result.suspended_gate in block


# --- the agent and its governed skill --------------------------------------


def test_the_grant_was_admitted_at_its_content_identity(result: Any) -> None:
    """Pre-rewrite :754. The ledger admits a grant AT its content hash — the
    address it returns is what the grant IS, not a name it was filed under."""
    assert result.granted_address == content_hash(result.grant)


def test_the_agent_consumed_the_gated_product_itself(result: Any) -> None:
    """Pre-rewrite :757. Identity, not equality: the agent consumes the very
    product the gates admitted, so there is no re-validated copy in between."""
    assert result.consumed is result.product


def test_the_skill_produced_the_declared_output(result: Any) -> None:
    """Pre-rewrite :763. An independent expectation from
    `skill-dispatch.yaml`."""
    dispatch = _declaration(result, "skill-dispatch")
    assert result.skill_output == dispatch["dispatch"]["expected_output"]


# --- the workflow and the hardened HITL door -------------------------------


def test_the_d16_policy_in_force_requires_a_signed_binding(result: Any) -> None:
    """Pre-rewrite :628.

    Read back off the Control Plane rather than off the file: what matters is
    the policy the transport actually consulted. A deployment that dropped the
    requirement would still have approved — silently, and unverifiably at replay.
    """
    registration = _declaration(result, "agent-registration")
    _, policy = result.registry.resolve_latest(registration["hitl_policy_key"])
    assert isinstance(policy, HitlPolicy)
    assert policy.signed_binding_required is True


def test_the_workflow_suspended_at_the_declared_gate(result: Any) -> None:
    """Pre-rewrite :802. A propagation check against `hitl-drive.yaml`."""
    human = _declaration(result, "hitl-drive")
    assert result.suspended_gate == human["drive"]["expected_gate"]


def test_the_workflow_completed_at_the_declared_terminal(result: Any) -> None:
    """Pre-rewrite :910."""
    human = _declaration(result, "hitl-drive")
    assert result.terminal_state == human["drive"]["resume_decision"]


def test_the_approver_signed_the_hash_of_what_they_were_shown(
    result: Any,
) -> None:
    """Pre-rewrite :866 and :1166.

    The TOCTOU property, from two directions: the event the approver was shown
    hashes the workflow state that was actually suspended, and the binding they
    signed echoes that same hash.

    ``suspended_state_hash`` is captured by the spine **at suspension**, before
    the resume mutates the state record. Hashing the record here instead would
    hash the completed workflow and compare two unrelated values — which is the
    shape of check that fails for the wrong reason, or worse, passes for one.
    """
    action = HitlActionRecord.model_validate_json(
        _stored_record(result).policy_bindings.hitl_actions
    )
    assert action.event.product_content_hash == result.suspended_state_hash
    assert (
        action.submission.principal.product_content_hash
        == action.event.product_content_hash
    )


def test_the_unmapped_scope_is_refused_deny_by_default(result: Any) -> None:
    """Pre-rewrite :847 and :849.

    The outsider token is AUTHENTICATED — its table entry is active — but its
    scope is absent from the scope mapping, so deny-by-default refuses it with
    the typed 403. The error code is the shared constant, never prose.
    """
    assert result.authz_refusal_status == 403
    assert result.authz_refusal_code == ERROR_TENANT_UNAUTHORIZED
    # Not a blanket refusal: the approver's own request succeeded in the same
    # run, against the same door, under the same mapping.
    assert result.authz_refused_client_id != result.approver_client_id


def test_the_deny_landed_in_the_audit_log_at_the_mapping_version(
    result: Any,
) -> None:
    """Pre-rewrite :857, :858, :859.

    Both outcomes land in the ONE Control Plane audit log, and the deny carries
    the exact scope-mapping version in force (D-09/D-10) — a refusal nobody can
    attribute to a version is not an audit record.
    """
    denied = [
        event
        for event in result.audit.events()
        if event.action == "authz_decision" and not event.resolved
    ]
    assert len(denied) == 1
    assert denied[0].actor == result.authz_refused_client_id
    assert denied[0].version == result.scope_mapping_version


# --- the OverrideBoundary --------------------------------------------------


def test_the_overrider_echoed_the_proposal_time_hash(result: Any) -> None:
    """Pre-rewrite :965 (T-07-17/T-07-39 TOCTOU doctrine).

    What the overrider signed is the hash of the value they were PROPOSED, not
    of whatever the boundary holds afterwards.
    """
    assert result.override_resolution.record.original == result.override_original
    signed = result.override_resolution.record.submission.principal
    assert signed.product_content_hash == content_hash(result.override_original)


def test_the_override_resolved_as_the_artifact_directed(result: Any) -> None:
    """Pre-rewrite :991, :992, :994.

    A propagation check against `hitl-drive.yaml`'s `override.drive.action`:
    flipping it to `confirm` must still produce a recorded action, never an
    absence.
    """
    override = _declaration(result, "hitl-drive")["override"]
    record = result.override_resolution.record
    assert record.overridden == (override["drive"]["action"] == "override")
    assert record.original.model_dump(mode="json") == override["original"]
    expected_final = (
        override["substitute"] if record.overridden else override["original"]
    )
    assert record.final.model_dump(mode="json") == expected_final


def test_the_override_record_reproduces_the_same_product(result: Any) -> None:
    """Pre-rewrite :1186. The override decision's OWN record replays, and the
    product it reproduces is byte-equal to the original."""
    assert canonical_bytes(result.reproduced_override_product) == canonical_bytes(
        result.product
    )


def test_the_overriders_signature_verifies_from_the_record(result: Any) -> None:
    """Pre-rewrite :1206, :1212, :1213 (D-14/D-16)."""
    block = result.reproduced_override_record.policy_bindings.hitl_actions
    action = OverrideActionRecord[
        result.override_original.__class__
    ].model_validate_json(block)
    assert action.submission.signed_binding is not None
    reproduced = verify_principal_binding(
        action.submission.signed_binding,
        provider=result.identity_provider,
        public_keys=result.trusted_keys,
    )
    assert reproduced == action.submission.principal
    assert reproduced.approver.subject_id == result.approver_client_id
