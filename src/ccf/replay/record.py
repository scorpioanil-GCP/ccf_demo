"""The five-dimension Decision Replay record (whitepaper §7.10.1).

Whitepaper §7.10.1 (INV-CH7-80: the five dimensions are inviolate);
DESIGN.md §2B.5. The dimensions, and what each holds in I.1:

1. **Context Fabric Snapshot** — the touched ``G(E, R, T, P, Π, L)`` substate
   at decision time (INV-CH7-81), *logical* per D-IMPL-06: temporal boundary +
   tenant + store-state watermark + the touched-substate manifest that lineage
   strict equality already enumerates. No physical graph copy — a copy per
   decision is what makes year-scale replay intractable, and the manifest plus
   the append-only graph reconstructs the same state.
2. **Policy Bindings Snapshot** — version identifiers of every Control Plane
   binding in force (INV-CH7-82). HITL actions extend this dimension as of
   I.4 (delivered; CLAUDE.md §8.2): the pre-serialized ``hitl_actions`` block
   the HITL primitives report, recorded verbatim.
3. **Model Version Record** — every invoked model; literally ``"none"`` in
   Mode 1 (INV-CH7-83). A positive claim, not an omission. Harness-attributable
   values — which harness ran the loop, the model version *it* reported, its
   execution-trace reference, its token counts — extend this dimension in I.3
   as the named :class:`HarnessTrace` sub-structure, per CLAUDE.md §7.3 seam 4
   and D-25.
4. **Perspective Conditioning** — principal and role in I.1 (INV-CH7-84);
   agent identity, version, and skill-set in force extend this dimension in
   I.2 per CLAUDE.md §6.2.
5. **Content Generation Path** — the operator plan and its executed step
   sequence, plus the content address of the product produced (INV-CH7-85);
   workflow step sequences extend it as of I.4 (delivered; CLAUDE.md §8.1) as
   the pre-serialized ``workflow_step_sequence`` block the workflow engine
   reports, recorded verbatim.

The record is a frozen contract, so it is canonically serializable and
content-addressable: a replay resolves the *exact* record, byte for byte,
rather than something that looks like it (D-IMPL-26).

Nothing here reads a clock. ``recorded_at`` is supplied by the caller, like
every other instant in the fabric.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.products.contract import AssemblyMode, ContextProductContract
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = [
    "MODE_1_MODEL_VERSION",
    "NO_AGENT_DEFINITION",
    "NO_GRANTS_SET_HASH",
    "NO_HARNESS",
    "NO_HARNESS_TRACE",
    "NO_HITL_ACTIONS",
    "NO_WORKFLOW_TRACE",
    "ContentGenerationPath",
    "ContextFabricSnapshot",
    "DecisionReplayRecord",
    "HarnessTrace",
    "ModelVersionRecord",
    "PerspectiveConditioning",
    "PolicyBinding",
    "PolicyBindingsSnapshot",
    "build_replay_record",
]

#: Dimension 3's value when no model was invoked (INV-CH7-83, Mode 1). The
#: whitepaper's own wording; recorded rather than omitted so that "no model
#: participated" is something the record asserts.
MODE_1_MODEL_VERSION = "none"

#: Dimension 4's grant-set value when no skill grant is in force (D-06/D-07).
#: A positive claim mirroring :data:`MODE_1_MODEL_VERSION`: "this decision ran
#: under zero grants" is asserted, never left as an absence a reader must
#: interpret. The skilling wave replaces it with the grant-set content hash.
NO_GRANTS_SET_HASH = "no-grants"

#: Dimension 3's harness-attributable value when no harness participated (D-25).
#: A positive claim in the :data:`MODE_1_MODEL_VERSION` voice: every fabric-direct
#: decision, and every decision an adapter did not mediate, *asserts* that no
#: harness ran rather than leaving a field absent for a reader to interpret. An
#: absent trace and a dropped trace would otherwise be the same artifact.
NO_HARNESS = "no-harness"

#: Dimension 4's agent-identity value when no agent participated (D-06).
#: Pre-agent records — the whole of I.1, and any fabric-direct decision — carry
#: this in the definition-hash and definition-URI fields, and as the single
#: element of a delegation chain that has no delegating agent.
NO_AGENT_DEFINITION = "no-agent"

#: Dimension 2's HITL-actions value when no human acted on the decision (I.4;
#: CLAUDE.md §8.2). A positive claim in the :data:`MODE_1_MODEL_VERSION` voice:
#: every fabric-direct decision, and every decision no HITL gate mediated,
#: *asserts* that no human action occurred rather than leaving a field absent
#: for a reader to interpret. An absent action and a dropped action would
#: otherwise be the same artifact — the audit-by-construction failure mode.
NO_HITL_ACTIONS = "no-hitl-actions"

#: Dimension 5's workflow value when no workflow orchestrated the decision
#: (I.4; CLAUDE.md §8.1). A positive claim mirroring :data:`NO_HITL_ACTIONS`:
#: "this decision was not a workflow step" is asserted, never inferred from
#: silence.
NO_WORKFLOW_TRACE = "no-workflow-trace"


class ContextFabricSnapshot(CCFContract):
    """Dimension 1 — the logical graph snapshot (INV-CH7-81, D-IMPL-06).

    Attributes:
        graph_snapshot_id: Derived identity of the state below. Derived, not
            assigned: an id someone chose could be reused across two different
            states, and a replay comparing ids would then agree about
            disagreeing state.
        tenant_id: Tenant scope of the read.
        temporal_boundary: The as-of instant the decision was made against.
        store_watermark: Content address of the graph state actually read.
        touched_entities: Entity URIs in the substate, sorted.
        touched_relationships: Relationship keys in the substate, sorted.
    """

    graph_snapshot_id: str
    tenant_id: str
    temporal_boundary: datetime
    store_watermark: str
    touched_entities: tuple[str, ...]
    touched_relationships: tuple[str, ...]

    @classmethod
    def build(
        cls,
        *,
        tenant_id: str,
        temporal_boundary: datetime,
        store_watermark: str,
        touched_entities: tuple[str, ...],
        touched_relationships: tuple[str, ...],
    ) -> "ContextFabricSnapshot":
        """Derive the snapshot id from the state it identifies.

        The id is ``content_hash`` over exactly the four constituents
        D-IMPL-06 names, so two decisions made against identical state share an
        id and any difference in the state produces a different one.
        """
        return cls(
            graph_snapshot_id=content_hash(
                {
                    "tenant_id": tenant_id,
                    "temporal_boundary": temporal_boundary,
                    "store_watermark": store_watermark,
                    "touched_entities": list(touched_entities),
                    "touched_relationships": list(touched_relationships),
                }
            ),
            tenant_id=tenant_id,
            temporal_boundary=temporal_boundary,
            store_watermark=store_watermark,
            touched_entities=touched_entities,
            touched_relationships=touched_relationships,
        )


class PolicyBinding(CCFContract):
    """One Control Plane binding, by key and pinned version."""

    key: str
    version: str


class PolicyBindingsSnapshot(CCFContract):
    """Dimension 2 — every binding in force at decision time (INV-CH7-82).

    HITL actions extend this dimension as of I.4 (delivered; CLAUDE.md §8.2)
    through ``hitl_actions``: the pre-serialized canonical block the HITL
    primitives (ApprovalGate, ExceptionEscalation, OverrideBoundary,
    ReviewQueue) report at build time, recorded verbatim — derived from what
    the primitive reported, never reconstructed here. Defaults to the positive
    :data:`NO_HITL_ACTIONS` sentinel so a decision no human touched says so.
    """

    bindings: tuple[PolicyBinding, ...]
    hitl_actions: str = NO_HITL_ACTIONS


class HarnessTrace(CCFContract):
    """Dimension 3's harness-attributable sub-structure (D-25; CLAUDE.md §7.3).

    SDK-defined, and an **extension** of dimension 3 — never a sixth dimension.
    INV-CH7-80 makes the five dimensions inviolate, and the harness-attributable
    values are model-attributable values, so :class:`ModelVersionRecord` is where
    they belong.

    The values here are what the harness adapter *reported* at its replay-hooks
    seam (CLAUDE.md §7.3 seam 4). They are recorded verbatim and are the fields
    D-18 excludes from the portability comparison: one agent definition run under
    three adapters agrees exactly on everything CCF governs — the consumed
    product, the grant-set hash, the agent definition hash, the policy bundle
    versions, lineage — and differs here, which is the whole point of confining
    them to a named block. A comparison that included them would fail always;
    a record that omitted them would lose the attribution.

    The trace-reference fields are shaped for D-IMPL-45's ``TraceCorrelationHook``,
    which attaches at this same seam in I.4: CCF stores a correlation to an
    external model-trace provider, never an ingestion of the trace itself.

    Every field defaults to a positive sentinel, so a partially-reported trace
    still asserts what it does not know instead of going quiet.

    Attributes:
        harness_id: Which harness ran the loop. :data:`NO_HARNESS` when none did.
        model_version: The model version the *harness* reported, which is not
            necessarily the fabric's own dimension-3 ``model_version``: the
            fabric records what it invoked, the harness records what it invoked,
            and conflating the two would let a harness overwrite a governed field.
        trace_provider: The external trace provider the harness correlated to
            (D-IMPL-45), or :data:`NO_HARNESS`.
        trace_id: The provider-scoped trace identifier, or :data:`NO_HARNESS`.
        input_tokens: Tokens the harness reported consuming; ``0`` when unreported.
        output_tokens: Tokens the harness reported producing; ``0`` when unreported.
    """

    harness_id: str = NO_HARNESS
    model_version: str = NO_HARNESS
    trace_provider: str = NO_HARNESS
    trace_id: str = NO_HARNESS
    input_tokens: int = 0
    output_tokens: int = 0


#: Dimension 3's harness block when no harness participated (D-25). The whole
#: sub-structure in its positive no-harness form, so the default is one named
#: value rather than six field defaults a reader must reassemble.
NO_HARNESS_TRACE = HarnessTrace()


class ModelVersionRecord(CCFContract):
    """Dimension 3 — the models invoked (INV-CH7-83).

    ``model_version`` defaults to :data:`MODE_1_MODEL_VERSION` because I.1 is
    Mode 1 throughout — the fabric core invokes no model, and the record says
    so rather than staying silent. Mode 2 supplies the real version alongside
    the other three pinned rendering primitives when the LLM packaging stage
    lands.

    Extended once, in I.3, with ``harness_trace`` (D-25): the harness-attributable
    values live in their own named block and never touch ``assembly_mode`` or
    ``model_version``, which stay governed fields the fabric alone writes.
    """

    assembly_mode: AssemblyMode
    model_version: str = MODE_1_MODEL_VERSION
    harness_trace: HarnessTrace = NO_HARNESS_TRACE


class PerspectiveConditioning(CCFContract):
    """Dimension 4 — whose viewpoint conditioned the decision (INV-CH7-84).

    Extended once, in I.2, with the complete D-06 field set (CLAUDE.md §6.2;
    D-07 stability rule): which agent, which version, which composition, which
    grants — answerable from the record alone. Every value here is serialized
    from artifact-resolved state captured at construction/grant time, never
    re-derived from live objects: a record that re-observed anything would
    describe the state at recording time, not at decision time.

    Attributes:
        principal_id: The originating principal.
        role: The Π role conditioning the view.
        agent_definition_hash: Content hash of the agent definition in force —
            canonical identity (D-IMPL-26). :data:`NO_AGENT_DEFINITION` when no
            agent participated: a positive claim, not an omission.
        agent_definition_uri: The definition's versioned URI, carried as
            annotation per the D-IMPL-26 replay rule (the hash is the
            identity; the URI is for humans and stores).
        archetype_composition: The composed archetype list, in D-IMPL-19
            declaration order. Empty exactly when no agent participated.
        grant_set_hash: Content hash of the in-force skill grant set (D-07).
            Defaults to :data:`NO_GRANTS_SET_HASH` until skilling lands.
        delegation_chain: From originating principal to acting agent identity
            (DESIGN.md §3.6, INV-CH7-84). Never empty: pre-agent records carry
            the single-element :data:`NO_AGENT_DEFINITION` sentinel; I.2
            records carry a single element; I.4 workflow chains extend the
            same field with no further contract change.
    """

    principal_id: str
    role: str
    agent_definition_hash: str = NO_AGENT_DEFINITION
    agent_definition_uri: str = NO_AGENT_DEFINITION
    archetype_composition: tuple[str, ...] = ()
    grant_set_hash: str = NO_GRANTS_SET_HASH
    delegation_chain: tuple[str, ...] = (NO_AGENT_DEFINITION,)

    @field_validator("delegation_chain")
    @classmethod
    def _chain_is_never_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError(
                "delegation_chain must not be empty: a decision with no"
                " delegating agent carries the single-element no-agent"
                " sentinel, never silence (D-06; INV-CH7-84)"
            )
        return value


class ContentGenerationPath(CCFContract):
    """Dimension 5 — how the delivered content came to be (INV-CH7-85).

    ``steps`` carries the executed order, not merely the set: a
    Policy-before-Similarity run and its forbidden inverse invoke the same
    operators and are not the same decision.

    Workflow step sequences extend this dimension as of I.4 (delivered;
    CLAUDE.md §8.1) through ``workflow_step_sequence``: the pre-serialized
    canonical block the workflow engine reports at build time, recorded
    verbatim. Defaults to the positive :data:`NO_WORKFLOW_TRACE` sentinel so
    a fabric-direct decision asserts it was not a workflow step.
    """

    plan_id: str
    operator_plan: tuple[str, ...]
    steps: tuple[ExecutionStep, ...]
    product_content_address: str
    workflow_step_sequence: str = NO_WORKFLOW_TRACE


class DecisionReplayRecord(CCFContract):
    """One decision, forensically reconstructible (INV-CH7-79/80).

    Frozen and canonically serializable, so the record has a content address
    and a replay resolves that exact address — never "the record under this
    name", which is a moving target (D-IMPL-26).
    """

    tenant_id: str
    recorded_at: datetime
    context_fabric_snapshot: ContextFabricSnapshot
    policy_bindings: PolicyBindingsSnapshot
    model_version: ModelVersionRecord
    perspective_conditioning: PerspectiveConditioning
    content_generation_path: ContentGenerationPath


def build_replay_record(
    *,
    execution: ExecutionResult,
    product: ContextProductContract,
    perspective: Perspective,
    policy_bindings: tuple[PolicyBinding, ...],
    assembly_mode: AssemblyMode,
    recorded_at: datetime,
    agent_conditioning: PerspectiveConditioning | None = None,
    harness_trace: HarnessTrace | None = None,
    hitl_actions: str | None = None,
    workflow_step_sequence: str | None = None,
) -> DecisionReplayRecord:
    """Assemble the record from what the execution and the product already know.

    Every dimension is derived from artifacts that exist independently of the
    record — the engine's own execution result, the gated product, the
    perspective the caller conditioned on, the Control Plane bindings in force.
    Nothing is re-observed at record time, because a record that measured
    anything itself would be recording the state at *recording* time rather
    than at decision time.

    ``agent_conditioning`` is the I.2 agent seam (D-06): when an agent made
    the decision, the caller passes the conditioning the agent serialized
    from its construction-time identity
    (:meth:`ccf.agents.agent.Agent.perspective_conditioning`) and it is
    recorded verbatim — derived, never reconstructed here. When ``None``
    (every fabric-direct decision, and the whole of I.1), dimension 4 carries
    the positive no-agent/no-grants claims and the single-element
    originating-principal delegation chain, exactly as before.

    ``harness_trace`` is the I.3 adapter seam (D-25), threaded into dimension 3
    exactly as ``agent_conditioning`` is threaded into dimension 4: when a
    harness adapter mediated the decision, the caller passes the block the
    adapter reported at its replay-hooks seam (CLAUDE.md §7.3 seam 4) and it is
    recorded verbatim — derived from what the adapter reported, never
    reconstructed here. When ``None`` (every fabric-direct decision, and the
    whole of I.1 and I.2), dimension 3 carries the positive
    :data:`NO_HARNESS_TRACE` claim and every field the builder wrote before this
    extension is byte-for-byte what it was.

    ``hitl_actions`` is the I.4 HITL seam (CLAUDE.md §8.2), threaded into
    dimension 2 exactly as the two seams above are threaded into theirs: when
    a HITL primitive mediated the decision, the caller passes the block the
    primitive pre-serialized and it is recorded verbatim — derived from what
    the caller reported, never reconstructed here. When ``None``, dimension 2
    carries the positive :data:`NO_HITL_ACTIONS` claim.

    ``workflow_step_sequence`` is the I.4 workflow seam (CLAUDE.md §8.1),
    threaded into dimension 5 the same way: the workflow engine's
    pre-serialized step-sequence block, recorded verbatim, defaulting to the
    positive :data:`NO_WORKFLOW_TRACE` claim.
    """
    return DecisionReplayRecord(
        tenant_id=product.tenant_id,
        recorded_at=recorded_at,
        context_fabric_snapshot=ContextFabricSnapshot.build(
            tenant_id=product.tenant_id,
            temporal_boundary=product.temporal_boundary,
            store_watermark=execution.state_watermark(),
            touched_entities=execution.touched_entities(),
            touched_relationships=execution.touched_relationships(),
        ),
        policy_bindings=PolicyBindingsSnapshot(
            bindings=policy_bindings,
            hitl_actions=hitl_actions if hitl_actions is not None else NO_HITL_ACTIONS,
        ),
        model_version=ModelVersionRecord(
            assembly_mode=assembly_mode,
            harness_trace=harness_trace
            if harness_trace is not None
            else NO_HARNESS_TRACE,
        ),
        perspective_conditioning=agent_conditioning
        or PerspectiveConditioning(
            principal_id=perspective.principal_id,
            role=perspective.role,
            delegation_chain=(perspective.principal_id,),
        ),
        content_generation_path=ContentGenerationPath(
            plan_id=execution.plan_id,
            operator_plan=tuple(step.operator_key for step in execution.steps),
            steps=execution.steps,
            product_content_address=content_hash(product),
            workflow_step_sequence=workflow_step_sequence
            if workflow_step_sequence is not None
            else NO_WORKFLOW_TRACE,
        ),
    )
