"""The five-dimension Decision Replay record (whitepaper §7.10.1).

Whitepaper §7.10.1 (INV-CH7-80: the five dimensions are inviolate);
DESIGN.md §2B.5. The dimensions, and what each holds in I.1:

1. **Context Fabric Snapshot** — the touched ``G(E, R, T, P, Π, L)`` substate
   at decision time (INV-CH7-81), *logical* per D-IMPL-06: temporal boundary +
   tenant + store-state watermark + the touched-substate manifest that lineage
   strict equality already enumerates. No physical graph copy — a copy per
   decision is what makes year-scale replay intractable, and the manifest plus
   the append-only graph reconstructs the same state. The source attestation
   in force extends this dimension as of 15.2-11 (D-09): the per-dimension
   provenance modes the reading source reported, recorded from execution,
   ``None`` asserting "recorded before source attestation existed".
2. **Policy Bindings Snapshot** — version identifiers of every Control Plane
   binding in force (INV-CH7-82). HITL actions extend this dimension as of
   I.4 (delivered; CLAUDE.md §8.2): the pre-serialized ``hitl_actions`` block
   the HITL primitives report, recorded verbatim. The D-10 survivor cap in
   force extends it as of 15.2-08: the Control-Plane-configured value is a
   dimension-2 fact, ``None`` asserting "no cap configured".
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
   reports, recorded verbatim. The per-round-trip query pins extend it as of
   15.2-08 (D-11): the ordered ``content_hash`` tuple of every ``GraphQuery``
   the segmented engine issued, recorded from execution. The Context Debt in
   force extends it as of 15.5-11 (D-IMPL-100): the ``DebtAssessment`` the
   product carries, derived from the product rather than passed beside it,
   ``None`` asserting "this decision carried no debt assessment". Debt lands
   here rather than on dimension 1 because its CAR band *is* a generation-path
   fact — Forced-LLM invokes a semantic stage, Fail-Closed declines — and
   because it is a property of the delivered product, which is what dimension 5
   already records. The ``ProductRequest`` answered extends it as of 15.5-13
   (D-IMPL-111 limb (b)): the question a decision answered, verbatim, ``None``
   asserting "this decision recorded no request".

The record is a frozen contract, so it is canonically serializable and
content-addressable: a replay resolves the *exact* record, byte for byte,
rather than something that looks like it (D-IMPL-26).

Nothing here reads a clock. ``recorded_at`` is supplied by the caller, like
every other instant in the fabric.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import SourceAttestation
from ccf.graph.registry import AdapterPin
from ccf.halflife.assessment import (
    NO_DEBT_EVIDENCE,
    NO_OBLIGATION_IN_FORCE,
    NO_SOURCE_REFRESH_RECENCY,
    DebtAssessment,
    DebtEvidence,
    SourceRefreshRecency,
)
from ccf.products.contract import AssemblyMode, ContextProductContract
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective

# `ccf.products.request` is imported at the BOTTOM of this module (D-IMPL-56
# pattern; see the note there). Dimension 5 names :class:`ProductRequest` as of
# D-IMPL-111 limb (b), and that module's own dependencies reach `ccf.agents`,
# which reads two names back out of this one.

__ccf_mode__ = "algorithmic"

__all__ = [
    "MODE_1_MODEL_VERSION",
    "NO_ADAPTER",
    "NO_AGENT_DEFINITION",
    "NO_GRANTS_SET_HASH",
    "NO_GRAPH_QUERIES",
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

#: Dimension 5's query-pin value when no seam query is recorded (15.2-08;
#: D-11). A positive claim in the :data:`NO_WORKFLOW_TRACE` voice: "this
#: decision was recorded before the query seam existed / issued no seam reads"
#: is asserted, never inferred from silence — an absent pin sequence and a
#: dropped one would otherwise be the same artifact. The empty tuple rather
#: than a marker string because each element is a ``content_hash`` and the
#: field's shape must stay one shape (the ``workflow_step_sequence``
#: sentinel-default precedent, applied to a tuple-valued field).
NO_GRAPH_QUERIES: Final[tuple[str, ...]] = ()

#: Dimension 2's adapter value when no adapter pin was recorded (15.4-08;
#: D-IMPL-93). A positive claim in the :data:`NO_HITL_ACTIONS` voice: "this
#: decision did not record which adapter answered" is asserted, never inferred
#: from silence — a record written before the pin existed and one whose caller
#: dropped the pin would otherwise be the same artifact, which is the
#: repudiation failure mode every sentinel in this module exists to close.
NO_ADAPTER = "no-adapter"


class ContextFabricSnapshot(CCFContract):
    """Dimension 1 — the logical graph snapshot (INV-CH7-81, D-IMPL-06).

    The source attestation in force extends this dimension as of 15.2-11
    (D-09) through ``source_attestation``, under the sentinel-default
    discipline of every prior record extension (the
    ``workflow_step_sequence`` precedent): dimension 1 is *what state/source
    the decision drew from*, and how the source vouched for its policy
    binding and lineage is a dimension-1 fact — a decision made over a
    mounted tier-2 product and one made over the live graph read different
    kinds of state even when the bytes agree. Recorded from the engine's own
    execution facts, unconditionally, so even a read path that skipped every
    check leaves its provenance posture here (T-15.2-25).

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
        source_attestation: The :class:`~ccf.graph.protocols.SourceAttestation`
            the reading source reported at decision time (D-09), pinned
            verbatim. ``None`` is the positive assertion "recorded before
            source attestation existed" — or an execution against a
            pre-phase reader that reported none — asserted, never inferred
            from silence, exactly as every sentinel default in this record.
    """

    graph_snapshot_id: str
    tenant_id: str
    temporal_boundary: datetime
    store_watermark: str
    touched_entities: tuple[str, ...]
    touched_relationships: tuple[str, ...]
    source_attestation: SourceAttestation | None = None

    @classmethod
    def build(
        cls,
        *,
        tenant_id: str,
        temporal_boundary: datetime,
        store_watermark: str,
        touched_entities: tuple[str, ...],
        touched_relationships: tuple[str, ...],
        source_attestation: SourceAttestation | None = None,
    ) -> "ContextFabricSnapshot":
        """Derive the snapshot id from the state it identifies.

        The id is ``content_hash`` over exactly the four constituents
        D-IMPL-06 names, so two decisions made against identical state share an
        id and any difference in the state produces a different one.

        ``source_attestation`` is deliberately **not** an id constituent: the
        id identifies graph *state*, and two reads of identical state share
        it whatever their sources attested — which is also what keeps
        :func:`~ccf.replay.snapshots.snapshot_of_execution`'s re-derived id
        comparable across records written before and after the field existed.
        The attestation is pinned beside the id and is covered by the
        record's own content address, so it is tamper-evident without being
        identity-bearing.
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
            source_attestation=source_attestation,
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

    The D-10 survivor cap extends this dimension as of 15.2-08 through
    ``survivor_cap``, under the same sentinel-default discipline as
    ``hitl_actions`` (the ``workflow_step_sequence`` precedent): the
    Control-Plane-configured cap in force at decision time is a dimension-2
    fact — the pushed/in-process split depends on plan + data + this value
    (`GQ-18` at docs/GRAPH_QUERY_SEMANTICS.md:342), so a replay must
    re-execute under the cap the decision ran under, never the cap now
    configured. ``None`` is the positive assertion "no cap configured", the
    engine's own default posture — asserted, never inferred from silence.

    The adapter pin extends this dimension as of 15.4-08 through
    ``graph_adapter``, ``graph_adapter_version`` and ``graph_secret_refs``,
    under the same sentinel-default discipline as ``hitl_actions`` and
    ``survivor_cap`` (the ``workflow_step_sequence`` precedent). These are
    dimension-2 facts because the bindings in force at decision time now
    include *which adapter was bound* and *which credential references it ran
    under*: from D-IMPL-93 onward the code behind the graph seam can be a
    third-party distribution, so which one answered and at which version is
    part of what produced the answer, exactly as a policy bundle version is.
    The three defaults — :data:`NO_ADAPTER` twice and the empty tuple — are the
    positive claim "no adapter was recorded", asserted rather than left as an
    absence a reader must interpret.

    ``graph_secret_refs`` carries reference **names** and can never carry a
    resolved credential. That is a mechanism rather than a discipline, in two
    layers: :class:`~ccf.graph.registry.AdapterPin` has no field a value can
    reach, and :func:`~ccf.contracts.canonical.canonical_bytes` refuses
    ``SecretStr`` outright, so a credential could not be hashed into this
    record even by accident. The names are stored **sorted**, so two
    deployments that declared the same references in a different order produce
    the same record: declaration order is not a fact about the decision, and a
    replay comparison that was sensitive to it would report a difference where
    there is none.
    """

    bindings: tuple[PolicyBinding, ...]
    hitl_actions: str = NO_HITL_ACTIONS
    survivor_cap: int | None = None
    graph_adapter: str = NO_ADAPTER
    graph_adapter_version: str = NO_ADAPTER
    graph_secret_refs: tuple[str, ...] = ()


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
    which attaches at this same seam as of I.4 (delivered —
    :mod:`ccf.replay.correlation`): CCF stores a correlation to an external
    model-trace provider, never an ingestion of the trace itself. The hook
    enriches this block *before* it is passed to :func:`build_replay_record`;
    it mints no new field here.

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
            records carry a single element; I.4 workflow chains (delivered)
            extend the same field with no further contract change — a
            workflow execution id followed by the calling agent identities,
            in delegation order, exactly as the field always admitted.
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

    The per-round-trip query pins extend this dimension as of 15.2-08 (D-11)
    through ``graph_query_sequence``: one ``content_hash`` per ``GraphQuery``
    the segmented engine issued, **in execution order** — recorded from the
    engine's own executed-queries sequence (`GQ-20` at
    docs/GRAPH_QUERY_SEMANTICS.md:391), never from plan-side prediction
    (T-15.2-15). A Similarity-bearing execution carries two pins in order; a
    cap-firing execution carries one — the record shows what ran. The full
    canonical bytes of every pinned query land in the ArtifactStore keyed by
    these hashes (:class:`~ccf.replay.serve.QueryPinWriter`), so an auditor
    resolves the literal question from the store without re-running anything.
    Defaults to the positive :data:`NO_GRAPH_QUERIES` sentinel — the
    ``workflow_step_sequence`` precedent — so a record written before the
    query seam existed asserts so and still verifies (D-IMPL-89).

    The Context Debt in force extends this dimension as of 15.5-11 (D-IMPL-100)
    through ``debt``, under the same sentinel-default discipline as every
    extension above it. **Dimension 5 and not dimension 1**, for two reasons
    that point the same way. D_c's routing band *is* a fact about how the
    content came to be — a Forced-LLM signal invokes a semantic stage and a
    Fail-Closed signal declines the decision outright (§7.7 CAR), which is the
    generation path rather than a description of the state read. And debt is a
    property of the **delivered product**, so it belongs beside
    ``product_content_address``, the record's other product-side fact: the
    field a rehydrator reads in order to reproduce the address sits next to the
    address it must reproduce. Dimension 1 stays exactly the four D-IMPL-06
    constituents plus the attestation pin, which is what
    ``tests/replay/test_engine_rehydration.py`` asserts on its field set.

    ``None`` is the positive assertion *this decision carried no debt
    assessment* — the ``source_attestation`` precedent, the same voice and the
    same reason: a record written before the debt seam existed and a record
    whose caller dropped the assessment would otherwise be the same artifact,
    which is the repudiation failure mode every sentinel in this module closes.

    The value is **derived from the product the builder was handed**, never
    passed alongside it. That is what keeps all 30 ``build_replay_record``
    consumers — including two conformance modules — byte-for-byte unchanged,
    and it makes a record that pins a debt its product does not carry
    unrepresentable rather than merely discouraged.

    **What that debt points at extends the same dimension as of 15.6-06**
    (D-IMPL-118) through ``debt_evidence``, and it is here because the ruling
    *obliged* it rather than because it was tidy. The carrier is a top-level
    field on :class:`~ccf.products.contract.ContextProductContract`, a sibling
    of ``debt`` rather than a member of the assessment, so it does **not**
    inherit the reconstruction ride the nested placement would have had:
    :class:`~ccf.projection.plan.ProjectionOutput` carries exactly
    ``(plan_id, payload)``, so a rehydrator handed ``(record, projection)`` can
    produce the value only if this dimension carries it. Without this member,
    every replay of every product raises
    :class:`~ccf.replay.engine.ReplayDivergence`.

    Its value is **derived from the product the builder was handed**, exactly
    as ``debt`` is and for the same reason: the product is already a parameter,
    so no call site moves, and a record pinning evidence its product does not
    carry is unrepresentable rather than merely discouraged.
    :data:`~ccf.halflife.assessment.NO_DEBT_EVIDENCE` is the positive assertion
    *this decision pointed at nothing*, so a record written before this seam
    existed asserts so and still verifies.

    **When the sources last published extends the same dimension as of 15.6-07**
    (D-IMPL-112 gap 2, D-IMPL-117) through ``source_refresh_recency``, for
    exactly the reason ``debt_evidence`` is here: D-IMPL-118 rules all three
    Track B members onto the vessel as top-level fields, so none of them rides
    ``debt`` back and each needs its own member here or every replay diverges.
    It is derived from the product for that field's reason, defaults to
    :data:`~ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY`, and belongs
    beside the ``debt`` whose freshness factor it is deliberately *not* — F is
    a measurement of decay against a budget, and this is a fact about when the
    world outside the fabric last spoke. As of 15.6-13 it carries a
    :class:`~ccf.halflife.assessment.SourceRefreshWindow` — the oldest and the
    newest of the deployment's declared refresh instants — rather than the
    per-source map 15.6-07 shipped, because D-IMPL-124 ruled the field's
    purpose to be freshness rather than source enumeration and took the source
    identities off the vessel. The placement is untouched by that revision: the
    member's spelling, its derivation and its read-back are all exactly what
    they were, and only its type changed.

    **What the signal obliged extends the same dimension as of 15.6-08**
    (D-IMPL-112 gap 3, D-IMPL-117) through ``obligation_in_force``, for the
    reason both members above are here and for one more that is this member's
    own. The shared reason: D-IMPL-118 rules all three Track B members onto the
    vessel as top-level fields, so none rides ``debt`` back and each needs its
    own member here. The extra one: the alternative for *this* value is not
    omission but **re-resolution** — a rehydrator could read the deployment's
    current :class:`~ccf.controlplane.artifacts.DebtProfile` and look the
    obligation up again, which would answer *"what was this decision obliged to
    do?"* with today's answer. That is the substitution D-IMPL-26's
    exact-version rule forbids, and pinning the resolved value here is what
    makes it unavailable rather than merely discouraged. It is derived from the
    product for ``debt``'s reason and defaults to
    :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE`.

    The **question answered** extends this dimension as of 15.5-13
    (D-IMPL-111 limb (b)) through ``request``: the
    :class:`~ccf.products.request.ProductRequest` the caller asked, recorded
    verbatim.

    **Dimension 5 and not dimension 4**, and the choice is the same shape as
    debt's. Dimension 4 answers *"for whom, with what authority?"*
    (``docs/CCF_Whitepaper_1-2.md:3266``) — principal, role, agent identity,
    grants, delegation. A request asserts none of those: role and tenant are
    deliberately absent from it, established by the door from a verified grant
    rather than claimed in the body. What a request *does* determine is the
    generation path — its ``parameters`` reach plan selection through
    D-IMPL-49's ``selection_params`` slot, its ``subject`` seeds the traversal
    (limb (a)), and its ``asked_at`` is the instant the caller asked as of. So
    it belongs beside ``graph_query_sequence``, which it explains: the pins say
    *what this decision asked the graph*, and this field says *which question
    the decision answered*. Before it existed the second was answerable from no
    dimension at all — ``intent`` and ``freshness`` were recorded nowhere, and
    the subject was recoverable by inference from the payload, which is not the
    same property as a pin (``DI-15.5-07``).

    It is a **parameter** of :func:`build_replay_record` rather than a fact read
    off ``execution`` or off ``product``, for the ``adapter`` reason: neither
    has ever seen the request. The engine is handed a plan, a perspective, a
    boundary and — since limb (a) — a seed set; it is never handed the question,
    and L5 importing L6's request surface to carry one would invert the layering
    (CLAUDE.md §10). The product carries the *answer*, not the question.

    ``None`` is the positive assertion *this decision recorded no request* — the
    ``debt`` and ``source_attestation`` voice, and the same reason: a record
    written before this seam existed and one whose caller dropped the question
    would otherwise be the same artifact. Every one of the 32
    ``build_replay_record`` call sites across 28 files is byte-for-byte
    unchanged under it.
    """

    plan_id: str
    operator_plan: tuple[str, ...]
    steps: tuple[ExecutionStep, ...]
    product_content_address: str
    workflow_step_sequence: str = NO_WORKFLOW_TRACE
    graph_query_sequence: tuple[str, ...] = NO_GRAPH_QUERIES
    debt: DebtAssessment | None = None
    debt_evidence: DebtEvidence = NO_DEBT_EVIDENCE
    source_refresh_recency: SourceRefreshRecency = NO_SOURCE_REFRESH_RECENCY
    obligation_in_force: str = NO_OBLIGATION_IN_FORCE
    request: ProductRequest | None = None


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
    adapter: AdapterPin | None = None,
    request: ProductRequest | None = None,
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

    ``adapter`` is the 15.4-08 registration seam (D-IMPL-93), threaded into
    dimension 2 the same way: the caller passes the
    :class:`~ccf.graph.registry.AdapterPin` its booted fabric reported at
    :attr:`ccf.boot.FabricHandle.adapter` and the three dimension-2 fields
    carry its values, with ``secret_refs`` stored sorted. When ``None``, the
    three positive :data:`NO_ADAPTER`/empty-tuple claims apply and every field
    the builder wrote before this extension is byte-for-byte what it was.

    It is a **parameter** rather than a fact read off ``execution`` — which is
    where the 15.2-08 facts below arrive — for two reasons that both point the
    same way. The adapter is a property of the *fabric*, and the execution
    object has never seen the fabric: it carries what the engine ran, not what
    the deployment booted against. And D-06 keeps dimension-2 assembly in
    adopter code, because a dimension 2 assembled by a rule nobody in the
    deployment wrote down is not an audit record.

    The 15.2-08 seam facts arrive on ``execution`` itself, not as new
    parameters — they are execution facts, and execution facts already travel
    here on :class:`~ccf.projection.engine.ExecutionResult`:

    * ``execution.executed_queries`` becomes dimension 5's
      ``graph_query_sequence`` — one ``content_hash`` per issued
      ``GraphQuery``, in execution order (D-11; `GQ-20` at
      docs/GRAPH_QUERY_SEMANTICS.md:391). Derived from what ran, never from
      plan-side prediction (T-15.2-15); an execution recorded before the
      query seam existed, or one built by hand without the field, yields the
      :data:`NO_GRAPH_QUERIES` sentinel exactly as before.
    * ``execution.survivor_cap`` becomes dimension 2's ``survivor_cap`` —
      the D-10 Control-Plane-configured value in force, ``None`` asserting
      no cap was configured.
    * ``execution.source_attestation`` becomes dimension 1's
      ``source_attestation`` (15.2-11, D-09) — the provenance modes the
      reading source reported, threaded by the engine unconditionally; an
      execution recorded before the attestation seam existed, or one built
      by hand without the field, yields the ``None`` sentinel exactly as
      before.

    ``request`` is the 15.5-13 addressability seam (D-IMPL-111 limb (b)),
    threaded into dimension 5 exactly as ``adapter`` is threaded into
    dimension 2 and for the same reason: the question is a property of the
    *call*, and neither the execution nor the product has seen it. The caller
    passes the :class:`~ccf.products.request.ProductRequest` it validated at
    the door and it is recorded verbatim — never re-derived, because a question
    reconstructed from the answer is not the question that was asked. When
    ``None``, dimension 5 carries the positive "no request recorded" claim and
    every field the builder wrote before this extension is byte-for-byte what
    it was.

    ``product.debt`` becomes dimension 5's ``debt`` (15.5-11, D-IMPL-100), on
    the same "already here, so it is derived rather than threaded" reasoning:
    the assessment is a property of the product, the product is already a
    parameter, and reading it off the product is what makes a record pinning a
    debt its product does not carry unrepresentable. A product assembled with
    no assessment yields the ``None`` sentinel, so every call site written
    before this extension is byte-for-byte what it was.

    ``product.debt_evidence`` becomes dimension 5's ``debt_evidence``
    (15.6-06, D-IMPL-118), on the same derivation reasoning — and it is
    load-bearing rather than symmetrical. The carrier is a top-level field on
    the vessel, so it is in the product's content address and *nothing else*
    reaching a rehydrator names it; carrying it here is what makes the address
    move reconstructible instead of merely authorized. A product assembled with
    no pointers yields :data:`~ccf.halflife.assessment.NO_DEBT_EVIDENCE`, so
    every call site written before this extension is byte-for-byte what it was.

    ``product.source_refresh_recency`` becomes dimension 5's
    ``source_refresh_recency`` (15.6-07, D-IMPL-118), on the same derivation
    reasoning and load-bearing for the same reason: it is a top-level vessel
    field, so nothing else reaching a rehydrator names it. A product recording
    no refresh instants yields
    :data:`~ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY`, so every call
    site written before this extension is byte-for-byte what it was.

    ``product.obligation_in_force`` becomes dimension 5's
    ``obligation_in_force`` (15.6-08, D-IMPL-118), on the same derivation
    reasoning and load-bearing for a stronger reason than either: it is a
    top-level vessel field, so nothing else reaching a rehydrator names it —
    and the deployment's *current* debt profile does, which is precisely the
    substitution this pin makes unavailable. A decision made under a
    calibration that bound nothing yields
    :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE`, so every call site
    written before this extension is byte-for-byte what it was.
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
            source_attestation=execution.source_attestation,
        ),
        policy_bindings=PolicyBindingsSnapshot(
            bindings=policy_bindings,
            hitl_actions=hitl_actions if hitl_actions is not None else NO_HITL_ACTIONS,
            survivor_cap=execution.survivor_cap,
            graph_adapter=adapter.name if adapter is not None else NO_ADAPTER,
            graph_adapter_version=(
                adapter.version if adapter is not None else NO_ADAPTER
            ),
            # Sorted here as well as at the pin: a caller may hand-build an
            # AdapterPin, and declaration order is not a fact about the
            # decision — an unsorted tuple would make replay comparison
            # order-sensitive on something that has no order.
            graph_secret_refs=(
                tuple(sorted(adapter.secret_refs)) if adapter is not None else ()
            ),
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
            graph_query_sequence=tuple(
                content_hash(query) for query in execution.executed_queries
            ),
            # D-IMPL-100: read off the product, not off a parameter. The
            # product is already here, so no call site moves — and a record
            # pinning a debt its product does not carry cannot be constructed.
            debt=product.debt,
            # D-IMPL-118: read off the product for debt's reason, and carried
            # at all for a harder one — the carrier is a top-level vessel
            # field, so `(record, projection)` cannot rebuild it from anywhere
            # else and every replay would diverge without this line.
            debt_evidence=product.debt_evidence,
            # D-IMPL-117 gap 2, under the same D-IMPL-118 placement and for
            # the same two reasons: read off the product so no call site
            # moves, and carried at all because a top-level vessel field is
            # reconstructible from nowhere else.
            source_refresh_recency=product.source_refresh_recency,
            # D-IMPL-117 gap 3, under the same D-IMPL-118 placement, and
            # carried for a reason the other two do not have: without this
            # line a rehydrator's only route to the value is the deployment's
            # CURRENT debt profile, which would answer "what was this decision
            # obliged to do?" with today's binding (D-IMPL-26).
            obligation_in_force=product.obligation_in_force,
            # D-IMPL-111 limb (b): the question, verbatim. A parameter and not
            # a derivation — the answer does not contain the question that was
            # asked, and inferring one from the other is what DI-15.5-07
            # recorded as insufficient.
            request=request,
        ),
    )


# Imported at the bottom, deliberately (D-IMPL-56, the pattern
# `ccf.skills.catalog` documents and `ccf.products.request` now applies for the
# same reason). Dimension 5 names :class:`~ccf.products.request.ProductRequest`
# as of D-IMPL-111 limb (b); that module reaches `ccf.skills.catalog`, which
# reaches `ccf.agents.agent`, which reads `NO_GRANTS_SET_HASH` and
# `PerspectiveConditioning` out of *this* module. Both of those exist above, so
# by the time this line runs the cycle closes safely in either import order.
# The deferred annotation on `ContentGenerationPath.request` is then resolved
# explicitly.
from ccf.products.request import ProductRequest  # noqa: E402

ContentGenerationPath.model_rebuild()
