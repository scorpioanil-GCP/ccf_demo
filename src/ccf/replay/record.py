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
   dimension-2 fact, ``None`` asserting "no cap configured". The **request
   resolution** extends it as of 24.6-03 (``D-IMPL-253`` Q1/Q6,
   ``D-IMPL-254``): the ``EffectiveRequest`` the Authority layer produced —
   which authority set each parameter's value, which constraint bounded it, and
   whether an override was entitled — rendered from the value, with the
   constraint versions pinned beside it as bindings, so an examiner resolves
   the policy that was in force *then*.
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

import secrets
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Final, Literal

from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import (
    HASH_TRANSPARENT_KEY,
    canonical_bytes,
    content_hash,
)
from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    SourceAttestation,
    StoreSnapshotPin,
)
from ccf.graph.registry import AdapterPin
from ccf.halflife.assessment import (
    DebtFactors,
    NO_DEBT_EVIDENCE,
    NO_OBLIGATION_IN_FORCE,
    NO_SOURCE_REFRESH_RECENCY,
    DebtAssessment,
    DebtEvidence,
    ObligationInForce,
    SourceRefreshRecency,
)
from ccf.products.contract import AssemblyMode, ComputedEmptyFinding, ContextProductContract
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective

# `ccf.products.request` is imported at the BOTTOM of this module (D-IMPL-56
# pattern; see the note there). Dimension 5 names :class:`ProductRequest` as of
# D-IMPL-111 limb (b), and that module's own dependencies reach `ccf.agents`,
# which reads two names back out of this one.

__ccf_mode__ = "algorithmic"

if TYPE_CHECKING:  # pragma: no cover - typing only
    # Typing-only, and deliberately so. This module is imported by
    # `ccf.agents.agent` (it reads `NO_GRANTS_SET_HASH` and
    # `PerspectiveConditioning` from here), so a RUNTIME import of
    # `ccf.agents.assembler` would close a cycle in one import order and not
    # the other — the non-determinism D-IMPL-37 rejects. Function annotations
    # are never evaluated at runtime, so the quoted annotation on
    # :func:`mint_assembly_refusal` costs nothing. The value this module
    # actually needs at runtime, `ProductRequestViolation`, joins the existing
    # bottom import instead (D-IMPL-56).
    from ccf.agents.assembler import AssemblyOutcome

    # 24.6-03: typing-only for the same reason. `ccf.products.provenance`
    # imports nothing but `ccf.contracts`, so a runtime import would close
    # no cycle — but the value is only ever an annotation here, and the
    # module's discipline is that a name reaches the runtime namespace when
    # the runtime needs it.
    from ccf.products.provenance import EffectiveRequest

    # 24.6-07: typing-only, and this one is NOT a discipline choice — it is
    # forced, and measured. Dimension 5 admits the refusal VALUE
    # (`D-IMPL-253` Q13), and `ccf.products.refusal` imports
    # `ccf.agents.errors`, whose package `__init__` imports `ccf.agents.agent`,
    # which reads two names out of *this* module. So `refusal` → this module
    # is a real cycle in the import order that starts at `refusal`, and even
    # the bottom-import idiom below cannot close it: entering at `refusal`
    # reaches this module before `refusal` has bound a single name.
    # The three values are therefore imported inside the two function bodies
    # that need them (`_refusal_names`), which run long after both modules
    # have finished loading.
    from ccf.products.refusal import RefusalEnvelope

__all__ = [
    "CHILD_ADMITTED",
    "CHILD_OUTCOME_STATUSES",
    "MODE_1_MODEL_VERSION",
    "NO_ADAPTER",
    "NO_ASSEMBLER",
    "NO_DISCLOSURE_DECISION",
    "NO_FABRIC_READ",
    "NO_PRODUCT_ADDRESS",
    "NO_REQUEST_RESOLUTION",
    "NO_ROLE_RESOLVED",
    "NO_ASSEMBLY_REFUSAL",
    "NO_AGENT_DEFINITION",
    "FalseAssemblyRefusalClaimError",
    "mint_assembly_refusal",
    "NO_GRANTS_SET_HASH",
    "NO_GRAPH_QUERIES",
    "NO_HARNESS",
    "NO_HARNESS_TRACE",
    "NO_PACKAGING",
    "NO_PACKAGING_TRACE",
    "NO_REFUSAL_SEAM",
    "NO_HITL_ACTIONS",
    "NO_ISSUANCE",
    "UNSTATED_SUBJECT_WITHHOLDING",
    "NO_WORKFLOW_TRACE",
    "ChildResolution",
    "ContentGenerationPath",
    "ContextFabricSnapshot",
    "DecisionReplayRecord",
    "HarnessTrace",
    "ModelVersionRecord",
    "PackagingTrace",
    "PerspectiveConditioning",
    "REFUSAL_SEAMS",
    "PolicyBinding",
    "PolicyBindingsSnapshot",
    "ResolutionNotApplicable",
    "ResolutionNotApplicableReason",
    "build_replay_record",
    "new_issuance",
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

#: Dimension 3's packaging-block value when no LLM packaging stage ran
#: (`D-IMPL-346`). A positive claim in the :data:`MODE_1_MODEL_VERSION` voice:
#: every Mode-1 decision *asserts* that nothing packaged its result rather
#: than leaving a field absent for a reader to interpret.
NO_PACKAGING = "no-packaging"

#: Dimension 5's seam value when a refusal was not held at a deployment seam
#: (`D-IMPL-347` A2). A positive claim in the :data:`NO_ASSEMBLY_REFUSAL` voice:
#: the resolver's OWN refusals — an unresolvable request, a failed gate, a
#: policy-emptied view — assert that no deployment seam held them, rather than
#: leaving a field absent for a reader to read as "seam unknown".
NO_REFUSAL_SEAM = "not-seam-held"

#: The four deployment-supplied seams a governed refusal can be held at
#: (`D-IMPL-347` A2, Dave 2026-09-23). **Closed, and closed deliberately**:
#: these are exactly the callables a deployment supplies to
#: :func:`~ccf.products.resolver.build_governed_resolver`, which is the whole
#: reason their refusals are data rather than defects. A fifth name would mean
#: a fifth seam exists, and that is a design change rather than a vocabulary
#: one. Without this field the four wraps collapse into one undifferentiated
#: "no" and A2 is un-auditable (Dave: *"Without it, A2 is un-auditable"*).
REFUSAL_SEAMS: Final[frozenset[str]] = frozenset(
    {"acquisition", "build_children", "plan_factory", "product_gate"}
)

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

#: ``outcome_status`` when a child was admitted and composed (D-IMPL-336).
CHILD_ADMITTED: Final = "admitted"

#: The closed ``outcome_status`` vocabulary (D-IMPL-336). Closed so that the
#: four ways a child can be absent stay distinct: a **declared** optional
#: absence, a governed **refusal**, an **eligibility** failure and an
#: **authorization** failure are different events, and collapsing any pair
#: would let a governance failure read as a data gap.
CHILD_OUTCOME_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CHILD_ADMITTED,
        "refused",
        "rejected-at-admission",
        "no-producing-skill",
        "ambiguous-producer",
        "optional-absent",
        "ineligible",
        "unauthorized",
        # `D-IMPL-340` ruling 1: a registered, governed producer that could
        # not answer. Its own token, so "we could not reach the producer" is
        # never read as a rejection of a product that was produced.
        "producer-unavailable",
    }
)

#: Dimension 5's workflow value when no workflow orchestrated the decision
#: (I.4; CLAUDE.md §8.1). A positive claim mirroring :data:`NO_HITL_ACTIONS`:
#: "this decision was not a workflow step" is asserted, never inferred from
#: silence.
NO_WORKFLOW_TRACE = "no-workflow-trace"

#: Dimension 5's assembler-seam value when the decision met no governed
#: refusal (D-60; D-IMPL-214 Reading B). A positive claim in the
#: :data:`NO_HITL_ACTIONS` voice: "this decision encountered no governed
#: refusal at the assembler seam" is ASSERTED, never inferred from silence —
#: a decision that met none and a decision whose caller dropped the block
#: would otherwise be the same artifact, which is the repudiation failure
#: mode every sentinel in this module exists to close.
NO_ASSEMBLY_REFUSAL = "no-assembly-refusal"

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

#: Dimension 2's request-resolution value when no resolution was recorded
#: (24.6-03; ``D-IMPL-243``, ``D-IMPL-253`` Q6). A positive claim in the
#: :data:`NO_HITL_ACTIONS` voice: *"this decision recorded no resolution of the
#: question's parameters against the authorities that bound them"* is asserted,
#: never inferred from silence — a record written before the Authority layer
#: existed and one whose caller dropped the resolution would otherwise be the
#: same artifact, which is the repudiation failure mode every sentinel in this
#: module exists to close.
NO_REQUEST_RESOLUTION = "no-request-resolution"

#: The closed reason vocabulary of :class:`ResolutionNotApplicable` (24.7-04;
#: ``D-IMPL-264`` D-09/D-10). Hyphenated lowercase like every sentinel in
#: this module. Two reasons, and a marker states exactly one of them:
#:
#: ``no-resolution-step``
#:     The path that minted the record never invokes a constraint resolver
#:     — a direct validator, a test fixture. ``D-IMPL-264`` D-09: *"A path
#:     that never invokes resolution should say so explicitly. Do not
#:     redefine all direct validators as defective merely because the newer
#:     resolver exists."*
#: ``refused-before-resolution``
#:     The determination was reached before resolution could begin — a
#:     delivery-boundary denial of entitlement, or of a standing resource's
#:     existence, decided at the door with no resolver in the frame.
ResolutionNotApplicableReason = Literal[
    "no-resolution-step", "refused-before-resolution"
]


class ResolutionNotApplicable(CCFContract):
    """Dimension 2's request-resolution value when NO resolution applies — a
    positive claim, with its reason (24.7-04; ``D-IMPL-264`` D-09/D-10, P-2).

    SDK-defined (CLAUDE.md §11); the whitepaper hook is §7.10's completeness
    commitment — a record missing any one of the five dimensions leaves a
    whole class of audit question with no answer — applied to dimension 2's
    resolution: a record that says nothing about whether the question's
    parameters were resolved leaves *"was this decision governed by the
    constraints in force?"* unanswerable.

    A positive claim in the :data:`NO_REQUEST_RESOLUTION` voice, and the
    claim that sentinel could never quite make. Dave, ``D-IMPL-264`` P-2:
    *"`not applicable` is an explicit governed fact with a reason. Missing
    resolution information is an internal integrity failure."* The sentinel
    said *no resolution was recorded* — which a dropped resolution also
    says. This marker says *no resolution applies, and here is why* — which
    a dropped resolution cannot say, because a caller has to construct it to
    state it, and :func:`build_replay_record` refuses to mint a record
    without either this or the resolution that ran (D-10).

    ``reason`` is REQUIRED and closed (:data:`ResolutionNotApplicableReason`):
    an author who never stated why resolution does not apply has not stated
    non-applicability — the :class:`~ccf.products.provenance.ProvenanceSource`
    discipline. No default means no hash-transparency key and no roster
    entry (``D-IMPL-243``): the marker's canonical bytes are the reason and
    nothing else. The builder renders it into
    :attr:`PolicyBindingsSnapshot.request_resolution` from the VALUE through
    :func:`~ccf.contracts.canonical.canonical_bytes`, never accepted
    pre-serialized — so it is a JSON object string there, distinguishable
    from the legacy sentinel by shape, and it reads back as itself.

    Attributes:
        reason: Why no resolution applies to this decision.
    """

    reason: ResolutionNotApplicableReason

#: Dimension 1's watermark when the decision read **no** graph state at all
#: (24.6-07; ``D-IMPL-253`` Q13). A positive claim in the
#: :data:`NO_HITL_ACTIONS` voice, and the one this phase most needed: a refusal
#: reached before the graph is touched has no store watermark, and an empty
#: string or an omitted dimension would say *the state was empty* or *the state
#: was dropped* — three different facts collapsed into one. **"There is none"**
#: is what this asserts, and :meth:`ContextFabricSnapshot.unread` is the only
#: way to say it.
NO_FABRIC_READ = "no-fabric-read"

#: Dimension 4's assembler value when no
#: :class:`~ccf.agents.assembler.ContextAssemblerProtocol` produced the
#: decision (24.6-07; CLAUDE.md §6.2, ``D-IMPL-253`` Q16, ``D-IMPL-245``
#: amendment 1). A positive claim in the :data:`NO_AGENT_DEFINITION` voice:
#: every fabric-direct decision — the reference resolver holds no assembler —
#: *asserts* that none was in force rather than leaving a field for a reader to
#: interpret. A decision made by no assembler and one whose caller dropped the
#: assembler's identity would otherwise be the same artifact.
NO_ASSEMBLER = "no-assembler"

#: Dimension 5's disclosure value when no disclosure decision was applied
#: (24.6-07; ``D-IMPL-254``'s Disclosure layer, filled by ``24.6-08``). A
#: positive claim in the :data:`NO_WORKFLOW_TRACE` voice: *"nothing decided
#: what of this determination may cross a consumer boundary"* — which is the
#: internal, undisclosed form, and is what every record written before the
#: Disclosure layer existed was saying.
NO_DISCLOSURE_DECISION = "no-disclosure-decision"

#: Dimension 5's content address when the decision produced **no product**
#: (24.6-07; ``D-IMPL-253`` Q13). A positive claim rather than an empty string:
#: an address is a ``sha256`` and every real one is 64 hex characters, so a
#: reader that met ``""`` would be left deciding whether the decision produced
#: nothing or the address was lost. A refusal produced nothing, and this says
#: so — which is also why :attr:`ContentGenerationPath.product_content_address`
#: stays a **required** field and gains no ``None``.
NO_PRODUCT_ADDRESS = "no-product-address"

#: The positive claim *this record was not issued to a caller under its own
#: identifier* (Dave's Q11, 2026-10-07; ``D-IMPL-378``; SDK-defined, CLAUDE.md
#: §11). Every record written before
#: :attr:`ContentGenerationPath.issuance` existed reads as this, and so does a
#: record built by a writer that issues none; the member is hash-transparent at
#: it, so no such record's bytes or address move.
NO_ISSUANCE = "no-issuance"

#: The positive claim *this record does not say whether its class's answers may
#: withhold their subject* (Dave's Q12, 2026-10-07; ``D-IMPL-378``;
#: SDK-defined, CLAUDE.md §11). Every record written before
#: :attr:`ContentGenerationPath.subject_withholding` existed reads as this, and
#: so does a record its writer did not mark; the governed evidence read treats
#: it as a class that may withhold, so such a record is never read back by its
#: owner. Hash-transparent: no such record's bytes or address move.
UNSTATED_SUBJECT_WITHHOLDING = "unstated"


def new_issuance() -> str:
    """A fresh per-answer issuance identifier: 256 bits from the OS's CSPRNG.

    **Dave's Q11 (2026-10-07; ``D-IMPL-378``), SDK-defined (CLAUDE.md §11):**
    *"Equal public references must not identify different immutable record
    contents."* A governed determination's record carries one of these in
    :attr:`ContentGenerationPath.issuance`, minted where the determination is
    made (the governed resolver's served path and the reference refusal
    recorder), so every answer's record is a distinct immutable content whose
    address no caller can compute, and the reference that names it — which the
    record writer files under that address — is issued per answer. Nothing a
    caller supplies and nothing the answer read reaches it.

    64 lowercase hexadecimal characters, the shape of a content address.
    """
    return secrets.token_hex(32)

#: Dimension 4's ``role`` when the decision was reached before any Π role was
#: resolved (24.6-07; ``D-IMPL-256`` (1)). A door-level entitlement denial is
#: decided *at* the delivery boundary — before the resolver runs, and therefore
#: before a perspective's role is established — so the record must say the role
#: was never resolved rather than invent one or leave the required field blank.
#:
#: **A positive claim in an existing required field, and not a new field.** The
#: alternative — ``role: str | None`` — would make every reader of dimension 4
#: handle a null, for one caller's benefit, and would change the shape of a
#: field 40-odd call sites already write.
NO_ROLE_RESOLVED = "no-role-resolved"


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
        store_snapshot_pin: The substrate's transaction-time head the
            execution read under (ledger row 24.5-L-02, D-IMPL-240) — the
            :class:`~ccf.graph.protocols.StoreSnapshotPin` the engine took
            once before its first query, pinned verbatim so replay resolves
            **exactly** this state or refuses (CLAUDE.md §7.4: exact
            versions, never "latest"). Recorded beside ``temporal_boundary``
            and never inside it (D-IMPL-88).
            :data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN` is the positive
            assertion "this substrate exposes no native pin" — a record
            written before the field existed, or an execution over a reader
            that cannot pin — asserted, never inferred from silence, exactly
            as ``source_attestation``'s ``None``. Hash-transparent at the
            sentinel (``D-IMPL-243``): a record written before this field
            existed carries the same dimension-1 bytes, so the field is
            omitted from the canonical form at that value and rendered at
            any real pin.
    """

    graph_snapshot_id: str
    tenant_id: str
    temporal_boundary: datetime
    store_watermark: str
    touched_entities: tuple[str, ...]
    touched_relationships: tuple[str, ...]
    source_attestation: SourceAttestation | None = None
    store_snapshot_pin: StoreSnapshotPin = Field(
        default=NO_STORE_SNAPSHOT_PIN, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

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
        store_snapshot_pin: StoreSnapshotPin = NO_STORE_SNAPSHOT_PIN,
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

        ``store_snapshot_pin`` (24.5-L-02) is deliberately **not** an id
        constituent either, for the same reason: the id identifies graph
        *state*, and this keeps the re-derived id comparable across records
        written before and after the field existed. The pin is pinned beside
        the id, is inside the record's content address (tamper-evident), and
        :func:`~ccf.replay.engine.replay` compares it separately — a pin that
        moved between record and rehydration is
        :class:`~ccf.replay.engine.ReplayDivergence`.
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
            store_snapshot_pin=store_snapshot_pin,
        )

    @classmethod
    def unread(
        cls, *, tenant_id: str, temporal_boundary: datetime
    ) -> "ContextFabricSnapshot":
        """Dimension 1 for a decision that read **no** graph state (24.6-07).

        ``D-IMPL-253`` Q13 (Dave: *"Refusal is itself a decision and deserves
        the same five-dimensional replay model. Do not create second-class
        replay."*). A refusal reached before the graph is touched — a
        request-conformity verdict, a constraint refusal, a door-level
        entitlement denial — still has a dimension 1, and what that dimension
        must say is *there is none*.

        It is a **named constructor** rather than a set of arguments a caller
        assembles, for :meth:`build`'s reason and one more of its own. The
        shared reason: the snapshot id is derived rather than assigned, so the
        only way to produce a truthful one is to hand the state to a
        constructor. Its own: *"nothing was read"* has exactly one spelling
        here, and a caller that reached for :meth:`build` with an empty
        watermark and empty tuples would produce a **different** and false
        claim — that the graph was read and found empty.

        The id is ``content_hash`` over that positive claim, so two unread
        refusals at one instant for one tenant share an id — which is correct:
        the dimension identifies the state a decision drew from, and those two
        decisions drew from the same nothing. What distinguishes them is
        dimension 5, where the refusal itself is recorded.

        Args:
            tenant_id: The tenant whose door (and recorder) made the
                determination. The tenant the caller ADDRESSED can differ and
                rides on the refusal's resource identity and on the policy pin
                dimension 2 names (`D-IMPL-253` D-34).
            temporal_boundary: The instant it was made against — the question's
                own ``asked_at``, or a delivery boundary's determination
                instant.

        Returns:
            The dimension-1 snapshot asserting :data:`NO_FABRIC_READ`, with
            empty touched sets and no attestation: nothing was read, so
            nothing attested and nothing was touched.
        """
        return cls.build(
            tenant_id=tenant_id,
            temporal_boundary=temporal_boundary,
            store_watermark=NO_FABRIC_READ,
            touched_entities=(),
            touched_relationships=(),
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

    The **request resolution** extends this dimension as of 24.6-03 through
    ``request_resolution``, under the same sentinel-default discipline as
    ``survivor_cap`` and the adapter pin. It is a dimension-2 fact for the
    reason the bundle version is one: the bindings in force at decision time
    now include *which policy constraints bounded which parameter, on whose
    authority, and whether an override was entitled* — the
    :class:`~ccf.products.provenance.EffectiveRequest` the Authority layer
    produced (``D-IMPL-254``), rendered as its own canonical bytes so that one
    resolution cannot land as a family of blocks.

    Recording it here rather than deriving it at replay is the whole point of
    ``D-IMPL-253`` Q6: the constraint versions in force are pinned beside it as
    :class:`PolicyBinding` rows, so an examiner resolves *the policy that was in
    force then* rather than the policy that is in force now. The default is the
    positive :data:`NO_REQUEST_RESOLUTION` claim, and it is hash-transparent at
    that value (``D-IMPL-243``) — so every record written before the Authority
    layer existed keeps its content address, byte for byte.

    The field holds one of **three forms**, and only the first is a
    compatibility claim (24.7-04; ``D-IMPL-264`` D-10, D-12): the legacy
    sentinel :data:`NO_REQUEST_RESOLUTION`, read off every record written
    before 24.7 and off any record parsed from bytes that omit the field —
    the field's default, which the builder no longer writes; the canonical
    bytes of the :class:`~ccf.products.provenance.EffectiveRequest` that
    resolution produced, complete or partial; or the canonical bytes of a
    :class:`ResolutionNotApplicable` marker stating, with its reason, that no
    resolution applies. The type stays ``str`` and the default stays the
    sentinel so that no committed record's address moves; a new record
    carries one of the two canonical forms because
    :func:`build_replay_record` refuses to mint one without an explicit
    resolution state.
    """

    bindings: tuple[PolicyBinding, ...]
    hitl_actions: str = NO_HITL_ACTIONS
    survivor_cap: int | None = None
    graph_adapter: str = NO_ADAPTER
    graph_adapter_version: str = NO_ADAPTER
    graph_secret_refs: tuple[str, ...] = ()
    request_resolution: str = Field(
        default=NO_REQUEST_RESOLUTION, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


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


class PackagingTrace(CCFContract):
    """Dimension 3's Mode-2 packaging block (whitepaper §7.10.4; `D-IMPL-346`).

    SDK-defined, and an **extension** of dimension 3 on the
    :class:`HarnessTrace` precedent — never a sixth dimension. INV-CH7-80 makes
    the five dimensions inviolate, and what a packaging stage invoked is
    model-attributable, so :class:`ModelVersionRecord` is where it belongs.

    **What Mode 2 is, and what it is not.** Assembly Mode 2 is an
    algorithmically-assembled Context Product that an LLM then packages into a
    delivered form — a banker's memo over a credit-memo-context product, say.
    The packaging is a **derivative view**: the algorithmic substrate remains
    the artifact-of-record, and §7.10.4's watchpoint is that the packaging must
    not have altered the algorithmic conclusion. Nothing here licenses a model
    call inside the algorithmic path; Algorithmic ⇄ Semantic Alternation
    (whitepaper §7.6.6) is unchanged.

    **Why the values are pinned here rather than dereferenced.** §7.10.4 names
    four pinned rendering primitives: model version, temperature, prompt
    template and output hash. Three could be reached by resolving the agent
    definition and the prompt artifact it binds, and one — the temperature —
    could not be reached at all. Dave, 2026-09-23, on a pre-launch surface:
    pin them so an examiner reads the packaging from the record without a
    dereference. The *values* still originate in Control Plane artifacts; this
    block records which ones were in force, the way
    :class:`PolicyBindingsSnapshot` records a policy version rather than owning
    a policy.

    Every field defaults to a positive sentinel, so a partially-reported
    packaging still asserts what it does not know instead of going quiet, and a
    Mode-1 record says *no packaging stage ran* rather than staying silent.

    Attributes:
        model_version: The model the packaging stage invoked, as the stage
            reported it. Distinct from :attr:`ModelVersionRecord.model_version`,
            which the fabric alone writes, for the reason
            :class:`HarnessTrace` gives: conflating the two would let a
            packaging stage overwrite a governed field.
        temperature: The sampling temperature in force, as text so an
            unreported value is a named absence rather than a numeric default
            a reader could mistake for a declared ``0.0``.
        prompt_artifact_uri: The versioned URI of the prompt artifact the stage
            bound (the No-Hardcoding Rule, CLAUDE.md §6.4, already requires the
            prompt to be an artifact rather than an inline string).
        prompt_artifact_hash: That artifact's content hash — the identity, per
            the `D-IMPL-26` replay rule; the URI is for humans and stores.
        output_hash: Content hash of the packaged output. The *substrate's*
            address stays :attr:`ContentGenerationPath.product_content_address`;
            this is the derivative view's, and holding both is what lets an
            examiner ask whether the packaging moved the conclusion.
    """

    model_version: str = Field(
        default=NO_PACKAGING, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    temperature: str = Field(
        default=NO_PACKAGING, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    prompt_artifact_uri: str = Field(
        default=NO_PACKAGING, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    prompt_artifact_hash: str = Field(
        default=NO_PACKAGING, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    output_hash: str = Field(
        default=NO_PACKAGING, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


#: Dimension 3's packaging block when no packaging stage ran (`D-IMPL-346`).
#: The whole sub-structure in its positive no-packaging form, on the
#: :data:`NO_HARNESS_TRACE` precedent: one named value rather than five field
#: defaults a reader must reassemble.
NO_PACKAGING_TRACE = PackagingTrace()


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
    packaging_trace: PackagingTrace = Field(
        default=NO_PACKAGING_TRACE,
        json_schema_extra={HASH_TRANSPARENT_KEY: True},
    )


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
        assembler_id: Which
            :class:`~ccf.agents.assembler.ContextAssemblerProtocol` produced
            the decision, and ``assembler_version`` at which version
            (24.6-07). **Dimension 4 and not a sixth block**, on
            ``D-IMPL-253`` Q16's ruling (Dave: *"Perspective Conditioning is
            the better home for assembler identity/version given the existing
            model."*) and on CLAUDE.md §6.2's own placement of agent identity
            and version here. ``D-IMPL-245`` amendment 1 deferred the carriage
            to this phase; before it an assembler's identity travelled only in
            its own transcript, so *"which assembler produced this?"* was
            answerable from no dimension at all.

            :data:`NO_ASSEMBLER` on both is the positive claim that none was in
            force — the SDK's reference resolver holds no assembler, so it
            passes neither and the record asserts so rather than going quiet.
            Hash-transparent at that sentinel (``D-IMPL-243``): every record
            written before this extension keeps its content address, byte for
            byte.
        assembler_version: The assembler's own version lane. See
            ``assembler_id``.
    """

    principal_id: str
    role: str
    agent_definition_hash: str = NO_AGENT_DEFINITION
    agent_definition_uri: str = NO_AGENT_DEFINITION
    archetype_composition: tuple[str, ...] = ()
    grant_set_hash: str = NO_GRANTS_SET_HASH
    delegation_chain: tuple[str, ...] = (NO_AGENT_DEFINITION,)
    assembler_id: str = Field(
        default=NO_ASSEMBLER, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    assembler_version: str = Field(
        default=NO_ASSEMBLER, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

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


class FalseAssemblyRefusalClaimError(ValueError):
    """A dimension-5 block would record a false no-refusal claim.

    Raised — never repaired — on
    :class:`~ccf.agents.errors.FalseGrantClaimError`'s exact reasoning: a
    caller that hands :func:`mint_assembly_refusal` a governed refusal while
    asserting :data:`NO_ASSEMBLY_REFUSAL` is recording something it already
    knows cannot be true, and recording it would corrupt replay dimension 5
    at write time. The symmetric case is refused too — asserting a refusal
    over an outcome that is not one.

    **It lives here rather than in** ``ccf/agents/errors.py`` **because that
    module is outside this phase's ruled file roster** (D-IMPL-214), and the
    roster is judged by set equality rather than by convenience.
    """



class ChildResolution(CCFContract):
    """One composite requirement, what satisfied it, and what came back.

    **SDK-defined** (CLAUDE.md §11; ``docs/DECISIONS.md`` **D-IMPL-336**). The
    mapping ``required product class → skill/grant → child address``, which no
    hash of a set can carry: ``grant_set_hash`` on dimension 4 answers *which
    skills was this agent holding*, and cannot answer *which one satisfied
    which requirement*. Both are kept, in different dimensions.

    **Dimension 5 and not dimension 4.** Dimension 4 answers *"for whom, with
    what authority?"* — principal, role, agent identity, grants, delegation.
    This answers what was invoked, in what order, and what came back, which is
    the generation path. It is the same reasoning ``request`` was placed here
    under, and the same reasoning ``debt`` was: *"debt is a property of the
    delivered product"*, and so is a child's.

    **Every child-side member is optional and ABSENT when no child was
    produced.** A refused or missing requirement is recorded without inventing
    a timestamp, an address or a debt figure — ``None`` here is dimension 5's
    established voice for *this decision recorded none*, and a placeholder
    would be a fact the record does not have.

    **A product produced but rejected at admission is not a product that never
    existed** (`D-IMPL-336` Amendment 2). Its ``child_content_address`` is
    retained alongside ``outcome_status`` and ``refusal_ref``, because
    discarding what was rejected would make an admission failure
    indistinguishable from an absence. Whether that identity is *disclosed* in
    a served payload is the deployment's policy call; its retention here is
    not optional.

    Attributes:
        required_product_class: The class the composite required.
        required: Whether the composite could be served without it.
        outcome_status: One of :data:`CHILD_OUTCOME_STATUSES`.
        producing_skill_name: The catalog entry that satisfied it, when one
            was resolved.
        producing_skill_version: That entry's pinned ``artifact_version``.
        grant_hash: The governed binding identity — which grant made the entry
            effective.
        child_content_address: The served (or rejected) product's address.
        child_schema_name: What the child actually declared itself to be.
        child_schema_version: Observed, never predicted, and checked against
            the requirement's declared lane.
        child_asked_at: The child's reconstruction instant. Equal to the
            composite's ``asked_at`` on every admitted child — a composite has
            exactly one.
        child_graph_snapshot_at: The child's own temporal anchor.
        child_debt: The child's ``D_c``.
        child_debt_factors: Its F, C and S. **Recorded as the triple and not
            only the scalar**, because the composite's debt is the per-factor
            minimum and a record of scalars could not re-derive it.
        child_policy_bundle_versions: The child's policy versions.
        child_lineage_ref: The child's lineage identity — a hash, which
            identifies a lineage without reproducing it.
        child_operators_invoked: The child's own operator set (`R5`). The
            identity above is enough to COMPARE two lineages and not enough to
            REBUILD one, and a composite's lineage is the union over its
            children's (`D-IMPL-31`). Without this, no rehydrator could
            reproduce the composite's lineage, and therefore not its content
            address either.
        child_expires_at: The child's own expiry (`R5`). The composite's is
            floored by the stalest constituent, so a record carrying only the
            composite's expiry cannot show that the floor was applied — or
            re-derive it.
        child_admitted_at: When admission judged this child, from the trusted
            runtime clock (`O3`). Distinct from ``child_asked_at``, which is
            the reconstruction instant every constituent shares.
        eligibility_basis: Which authority established eligibility —
            :data:`~ccf.products.composite.ELIGIBILITY_LOCAL_REGISTER` or
            :data:`~ccf.products.composite.ELIGIBILITY_PRODUCER_ATTESTED`.
            Recorded rather than assumed: a local child's eligibility and a
            peered child's are different evidence with different trust, and
            *"eligible"* alone would make them indistinguishable.
        refusal_ref: The child's refusal, when it refused or was rejected.
        producer_id: `D-IMPL-340` — the identity the deployment's producer
            registration expects, copied from that registration at dispatch.
            Recorded on every ``mcp_product`` row, admitted or not, so replay
            names the exact producer relationship.
        producer_tenant: The tenant that registration says the producer
            governs under — what the child's own tenant was held to.
        producer_registration_address: The content address of the
            ``ccf.mcp-producer`` document the acquisition ran under — the
            governance context, without the endpoint or credential it named.
        producer_server: The logical producer name the granted binding
            selected. A name, never an address.
        child_question_address: ``sha256`` of the canonical question sent —
            the question's identity, which the producer's echo was held to.
        child_replay_ref: The producer's own replay-record reference, as its
            door reported it — on an admitted row, on a served-then-rejected
            row, and since `D-IMPL-342` on a row the producer's own door
            refused. **Retained as the producer's claim** — this fabric never
            resolves it (Dave: *"do not require access to a remote provider's
            internal replay store"*).
        producer_refusal_kind: `D-IMPL-342`. When the child's own door refused
            and the producer's claims held: the refusal kind that door
            disclosed. Evidence beside the admission verdict, never a
            replacement for it — ``outcome_status`` and ``refusal_ref`` still
            read ``ineligible``. ``None`` everywhere else, including a row
            written before the member existed.
        producer_refusal_reason: `D-IMPL-342`. The producer's own reason token
            as disclosed (a closed-vocabulary member or a declared gate id).
            Its prose ``detail`` is not carried on the row.
        producer_refusal_key: `D-IMPL-342`. The parameter key that refusal
            named, when it named one.
        child_question_ref: `D-IMPL-342` / `CP14-F-35`. The versioned URI the
            parent's own store returned when it retained the question's
            identity bytes at ``child_question_address``
            (:data:`~ccf.products.composite.CHILD_QUESTION_CLASS`). Present
            only when the bytes were filed — the reference is the store's
            answer, never computed from the address — so replay holds every
            row that carries one and leaves a row without one unheld BY
            NAME: a pre-342 record replays as it did.
        child_ttl_anchor: `D-IMPL-341`. The child's declared TTL anchor
            (``from_decision`` | ``from_entity_freshness``), from its contract.
        child_ttl_anchor_at: `D-IMPL-341`. The instant that anchor resolved
            to, from the child's contract — ``None`` for a child minted before
            the member existed, in which case a consumer may state only the
            producer's expiry and declared anchor, never an evidence age.
    """

    # Every optional member below is marked ``False`` — a generation boundary,
    # and NOT hash-transparent. `ChildResolution` is a new contract, so there
    # is no earlier record whose silence has to be preserved; what there is, is
    # a record that must say *"we do not know"* out loud. Rendering ``null``
    # makes an unknown a PRESENT statement in the canonical bytes, where
    # omitting the key would make "no address was known" and "this build forgot
    # to record one" the same artifact — which is the repudiation failure mode
    # every sentinel in this module closes, arriving from the other direction.
    required_product_class: str
    required: bool
    outcome_status: str
    producing_skill_name: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    producing_skill_version: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    grant_hash: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    # `D-IMPL-336` Amendment 3, F9 — the VERIFIED address, present only when
    # this fabric recomputed it and it matched. Never a value a producer
    # claimed and the gate disproved.
    child_content_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    # What the producer's door CLAIMED, kept beside it and labelled as such.
    # On an address-mismatch these differ, and the record says which is which
    # rather than presenting the refuted one as identity.
    child_reported_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    # `D-IMPL-336` Amendment 3, F6 — which fabric the eligibility claim was
    # made about. `eligibility_basis` said an authority answered and never
    # named it, so a mislabelled local production left no trace.
    producing_fabric: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    # `D-IMPL-336` Amendment 3, F7 — the producer's own eligibility-check
    # instant and the address of the verified assertion it came from. Recorded
    # so replay can re-verify WHICH evidence authorized a peered child; the
    # earlier row carried neither.
    child_eligibility_checked_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_eligibility_assertion_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_schema_name: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_schema_version: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_asked_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_graph_snapshot_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_debt: Decimal | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_debt_factors: DebtFactors | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_policy_bundle_versions: frozenset[str] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_lineage_ref: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_operators_invoked: frozenset[str] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_expires_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    child_admitted_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    eligibility_basis: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    refusal_ref: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    # `D-IMPL-340` — the producer relationship, from the registration the
    # registry resolved and never from the answer. Marked ``True``: a row
    # written before these members existed, or for a child acquired any other
    # way, hashes exactly as it did.
    producer_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_tenant: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_registration_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_server: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    child_question_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    child_replay_ref: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # `D-IMPL-342` — the refusing producer's own evidence and the retained
    # question's reference. ``True`` for the same reason the producer members
    # are: a stored row lacking them reloads to the address it was written at.
    producer_refusal_kind: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_refusal_reason: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_refusal_key: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    child_question_ref: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # `D-IMPL-341`: the admitted child's declared anchor and the instant it
    # resolved to, copied from the child's contract, so a consumer can print
    # what §8 of the design permits without inferring it from `expires_at`.
    child_ttl_anchor: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    child_ttl_anchor_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @model_validator(mode="after")
    def _producer_refusal_evidence_names_a_refusing_door(self) -> "ChildResolution":
        """`D-IMPL-342`: producer refusal evidence exists only where the child's
        own door refused — ``outcome_status`` AND ``refusal_ref`` both
        ``ineligible``. A served child rejected at the gate carries the
        producer's replay reference and NO producer refusal; an
        eligibility-evidence refusal shares the status token but not the
        reason; an unreachable producer disclosed nothing. Any other pairing
        is a writer inventing evidence, refused at construction rather than
        discovered at audit. (The local invalidation register's own
        ``ineligible`` refusal of a locally dispatched child shares both
        tokens; that leg mints no producer evidence, and the tokens alone
        cannot tell the two apart — a closed-vocabulary limit, recorded.)"""
        evidence = (
            self.producer_refusal_kind,
            self.producer_refusal_reason,
            self.producer_refusal_key,
        )
        refused_by_its_door = (
            self.outcome_status == "ineligible" and self.refusal_ref == "ineligible"
        )
        if any(member is not None for member in evidence) and not refused_by_its_door:
            raise ValueError(
                "producer refusal evidence"
                f" (kind={self.producer_refusal_kind!r},"
                f" reason={self.producer_refusal_reason!r},"
                f" key={self.producer_refusal_key!r}) on a row whose"
                f" outcome_status is {self.outcome_status!r} and refusal_ref"
                f" {self.refusal_ref!r}; a producer's own refusal is recorded"
                " only where its door refused (ineligible / ineligible), never"
                " fabricated onto an admitted, rejected, eligibility-refused or"
                " unreachable child (D-IMPL-342)"
            )
        if self.child_question_ref is not None and self.child_question_address is None:
            raise ValueError(
                "a retained-question reference without a question address; the"
                " reference names bytes whose identity the row does not record"
                " (D-IMPL-342 / CP14-F-35)"
            )
        return self

    @model_validator(mode="after")
    def _status_is_known(self) -> "ChildResolution":
        if self.outcome_status not in CHILD_OUTCOME_STATUSES:
            raise ValueError(
                f"outcome_status {self.outcome_status!r} is not one of"
                f" {sorted(CHILD_OUTCOME_STATUSES)}; the vocabulary is closed"
                " so a governance failure cannot be recorded as a data gap"
                " (D-IMPL-336)"
            )
        return self

    @model_validator(mode="after")
    def _served_rows_carry_what_they_claim(self) -> "ChildResolution":
        """An admitted row without its child's state is not a record of one."""
        if self.outcome_status != CHILD_ADMITTED:
            return self
        missing = [
            name
            for name in (
                "child_content_address",
                "child_schema_name",
                "child_schema_version",
                "child_asked_at",
                "child_debt",
                "child_debt_factors",
                "eligibility_basis",
            )
            if getattr(self, name) is None
        ]
        if missing:
            raise ValueError(
                f"an admitted child's row omits {', '.join(missing)}; a row"
                " claiming admission must carry the state admission checked,"
                " or replay pins a decision it cannot reproduce (D-IMPL-336)"
            )
        return self


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
    :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE`. It is carried as
    :data:`~ccf.halflife.assessment.ObligationInForce` — the same validated
    shape the vessel carries, so a record on disk cannot be rehydrated into a
    blank the vessel would have refused.

    **The scope of that last sentence, since a reader will generalise it.** It
    is a claim about the *validation boundaries* — construction and
    ``model_validate``, which is every deserialisation path — and Phase 15.6's
    single-agent review verified it holds at both. It is **not** a claim that
    the field cannot hold a blank: ``model_construct`` and
    ``model_copy(update=…)`` skip validation, as they do for every Pydantic
    contract in this tree, so either would seat a value this field's validator
    refuses. That is latent rather than live — no site in ``src/``, ``runtime/``
    or ``examples/`` applies either idiom to this field or to its two siblings —
    and it is recorded here rather than closed, because closing it means
    forbidding ``model_construct`` on the contract, which is a change to how
    every carrier in the fabric is built and therefore a ruling rather than a
    repair.

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
    would otherwise be the same artifact. Every one of the **40**
    ``build_replay_record`` call sites across **30 files** is byte-for-byte
    unchanged under it — a present-tense claim, so the figure is re-enumerated
    by AST at each phase that touches this builder rather than carried
    forward. It read *32 across 28* when plan 15.5-13 wrote it and that was
    true then; it is corrected here rather than left to rot (D-65).

    **The disclosure decision extends this dimension as of 24.6-07**
    (``D-IMPL-254``) through ``disclosure_decision``, under the same
    sentinel-default discipline as everything above it. It is here rather than
    on dimension 2 because it is a fact about *how the content that crossed
    came to be* rather than about which bindings were in force: Policy sets
    what **may** cross (dimension 2's regime), and this records which level was
    actually **applied** to produce the statement a consumer saw. Without it,
    replay can reconstruct the determination and not *"why the consumer saw the
    particular response it saw"* — which ``D-IMPL-254`` names as one of the
    four mistakes the four-layer separation exists to prevent.

    :data:`NO_DISCLOSURE_DECISION` is the positive assertion *nothing decided
    what may cross* — the internal, undisclosed form. ``24.6-08`` is the plan
    that fills it; this one gives it the slot and the sentinel, so no record
    written before that plan moves.

    ``product_content_address`` stays **required**, and a decision that
    produced no product carries :data:`NO_PRODUCT_ADDRESS` there. A ``None``
    would make every reader of this dimension handle a null for the refusal
    case's benefit, and would say *the address is unknown* where the true claim
    is *there is no product to address*.
    """

    plan_id: str
    operator_plan: tuple[str, ...]
    steps: tuple[ExecutionStep, ...]
    product_content_address: str
    disclosure_decision: str = Field(
        default=NO_DISCLOSURE_DECISION,
        json_schema_extra={HASH_TRANSPARENT_KEY: True},
    )
    workflow_step_sequence: str = NO_WORKFLOW_TRACE
    assembly_refusal: str = NO_ASSEMBLY_REFUSAL
    #: `D-IMPL-347` A2 — WHICH deployment seam held this refusal, one of
    #: :data:`REFUSAL_SEAMS`, or :data:`NO_REFUSAL_SEAM` when the resolver
    #: refused on its own account. Hash-transparent at its sentinel, so no
    #: record written before this field existed moves address.
    refusal_seam: str = Field(
        default=NO_REFUSAL_SEAM, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    graph_query_sequence: tuple[str, ...] = NO_GRAPH_QUERIES
    debt: DebtAssessment | None = None
    debt_evidence: DebtEvidence = NO_DEBT_EVIDENCE
    source_refresh_recency: SourceRefreshRecency = NO_SOURCE_REFRESH_RECENCY
    obligation_in_force: ObligationInForce = NO_OBLIGATION_IN_FORCE
    request: ProductRequest | None = None
    # `D-IMPL-341` R-2/R-5: the instant the served product's TTL anchor
    # resolved to, copied from the product so replay can re-derive it and hold
    # the two equal. ``None`` on every record written before the member
    # existed — decision-anchored by definition of the sentinel — and replay
    # skips the anchor hold for such a record explicitly, by name.
    ttl_anchor_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # SEC-020 (`D-IMPL-370` Q12 (a), its final rule `D-IMPL-371`): the served
    # product's EMPTY FINDING, copied from the product exactly as
    # `ttl_anchor_at` is, so replay rehydrates it rather than re-deriving it.
    # It is inside the product's address whenever it is not `None`, and before
    # this member existed no record carried it, so every product served WITH a
    # finding — a computed-empty answer, and every withheld subject — rebuilt
    # without one and failed replay with `ReplayDivergence` on its content
    # address. It is the governed resolver's finding, which for a withheld
    # subject is the unseeded re-execution's (`D-IMPL-371`), never replay's.
    # Hash-transparent at `None`, so every record written before this member
    # existed keeps its bytes and address; such a record now replays under
    # `src/ccf/replay/engine.py::replay`'s compatibility rule (`D-IMPL-378`),
    # which the record's own product address arbitrates.
    computed_empty: ComputedEmptyFinding | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # `D-IMPL-358` ruling 1 — WHEN THE ANSWER WAS SERVED, read once from the
    # fabric-controlled clock at `GovernedResolver.__call__` entry. A third
    # instant, distinct from both of the two this dimension already relates:
    # `request.asked_at` is what the question asks AS OF, `recorded_at` is when
    # the decision was taken, and this is when it was handed over.
    #
    # TRANSPARENT AT THE SENTINEL, and the mark is the ruling rather than a
    # preference. `None` — every record written before this member existed —
    # canonicalizes exactly as it did, so no pre-1.0.2 address moves and the
    # member's mere schema presence is not a generation boundary. A populated
    # value participates in the address, so **two serves of one question are
    # two records**: which determination, produced when, is the audit reading a
    # bank needs.
    #
    # Deliberately NOT `ChildResolution.child_admitted_at`'s mark, which is
    # `{HASH_TRANSPARENT_KEY: False}` — a declared generation boundary. The
    # accepted design asserted transparency while citing that field as its
    # precedent; the two are different marks and ruling 1 settles that this one
    # takes `True`. The precedent to read instead is `ttl_anchor_at` above: the
    # same shape, the same sentinel, on this same class.
    served_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    child_resolutions: tuple[ChildResolution, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # Dave's Q11 (2026-10-07; `D-IMPL-378`) — THE IDENTIFIER THIS ANSWER WAS
    # ISSUED UNDER (`new_issuance`), minted where the determination is made. It
    # makes every answer's record a distinct immutable content, so the record's
    # content address — the name and the version of the reference the caller is
    # handed — is unique per answer and computable by nobody who does not hold
    # the record: two answers never share a reference, and a reference never
    # reflects what the answer read. A recorded fact: replay reads it and never
    # re-derives it. Transparent at `NO_ISSUANCE`, so every record written
    # before it existed keeps its bytes and address.
    issuance: str = Field(
        default=NO_ISSUANCE, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # Dave's Q12 (2026-10-07; `D-IMPL-378`) — WHAT THE DECIDING CLASS AFFIRMED
    # about withholding its subject, recorded from its declaration
    # (`ProductClassDeclaration.subject_withholding`) by the determination that
    # wrote the record. The governed evidence read hands a record that read the
    # fabric back to its owner only when this says `"never"` and the tenant
    # lists the class; anything else — `"may-withhold"`, or the sentinel every
    # older record carries — stays off every evidence door, which is how the
    # restriction reaches existing records. Transparent at the sentinel.
    subject_withholding: str = Field(
        default=UNSTATED_SUBJECT_WITHHOLDING,
        json_schema_extra={HASH_TRANSPARENT_KEY: True},
    )

    @field_validator("issuance")
    @classmethod
    def _issuance_is_a_token_or_the_sentinel(cls, value: str) -> str:
        if value != NO_ISSUANCE and (
            len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)
        ):
            raise ValueError(
                "issuance is either NO_ISSUANCE or 64 lowercase hexadecimal"
                " characters minted by new_issuance()"
            )
        return value


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


def _refusal_names() -> tuple[type[CCFContract], Mapping[type[CCFContract], str], str]:
    """``(RefusalEnvelope, REFUSAL_KINDS, NO_REPLAY_REFERENCE)``, imported late.

    A function-local import, and the reason is a measured cycle rather than a
    preference (see the ``TYPE_CHECKING`` block at the top of this module):
    :mod:`ccf.products.refusal` reaches :mod:`ccf.agents.agent`, which reads
    :data:`NO_GRANTS_SET_HASH` and :class:`PerspectiveConditioning` out of
    here. Entering the tree at ``refusal`` therefore reaches this module before
    ``refusal`` has bound any name, which even the bottom-import idiom at the
    end of this file cannot survive.

    Named once rather than repeated at three call sites, so the reason is
    stated once and the three cannot drift into importing different things.
    """
    from ccf.products.refusal import (
        NO_REPLAY_REFERENCE,
        REFUSAL_KINDS,
        RefusalEnvelope,
    )

    return RefusalEnvelope, REFUSAL_KINDS, NO_REPLAY_REFERENCE


def _is_refusal_value(outcome: object) -> bool:
    """``outcome`` is a governed refusal this record can carry (24.6-07).

    Three admissible shapes, and the widening is the whole of ``D-IMPL-253``
    Q13's *"do not create second-class replay"*:

    * a :class:`~ccf.products.refusal.RefusalEnvelope` — **any** of the
      shipped :data:`~ccf.products.refusal.REFUSAL_KINDS`, since the envelope
      is the one shape every one of them crosses in;
    * a bare refusal value of any of those kinds, which is what an assembler
      or a gate returns before a door envelopes it;
    * a :class:`~ccf.products.request.ProductRequestViolation` — already
      covered by the line above, and named here because it is the **legacy**
      form D-60 shipped and the one every record written before ``24.6-07``
      carries.

    Membership is by exact type against ``REFUSAL_KINDS``, never
    ``isinstance``, for :func:`~ccf.products.refusal.envelope_for`'s reason: an
    ``isinstance`` chain would admit an unknown subclass as its nearest known
    ancestor and record the wrong kind — a well-formed audit record carrying a
    false answer.
    """
    envelope_class, kinds, _ = _refusal_names()
    if isinstance(outcome, envelope_class):
        return True
    return isinstance(outcome, CCFContract) and type(outcome) in kinds


def mint_assembly_refusal(
    outcome: "AssemblyOutcome | ProductRequestViolation | RefusalEnvelope | CCFContract",
    *,
    claimed: str | None = None,
) -> str:
    """Derive dimension 5's refusal block from the governed refusal itself.

    **The block is DERIVED from the value, never hand-claimed.** An adopter's
    assembler calls this with whatever
    :meth:`~ccf.agents.assembler.ContextAssemblerProtocol.assemble` returned
    and passes the result to :func:`build_replay_record`; the builder records
    those bytes verbatim rather than reconstructing them, exactly as it does
    for ``hitl_actions`` and ``workflow_step_sequence``.

    **Widened in 24.6-07** (``24.6-L-08``, ``D-IMPL-253`` Q13) from *the one
    refusal the assembler seam can produce* to **any**
    :data:`~ccf.products.refusal.REFUSAL_KINDS` member and to the
    :class:`~ccf.products.refusal.RefusalEnvelope` that carries it. That is
    what closes the hole :func:`build_replay_record`'s own docstring recorded
    as open for phase 24.1.1: Reading A wanted the refusal **value** to travel
    into the builder rather than a pre-serialized block, and this is that
    reading, arriving with the ruling that asked for it.

    Args:
        outcome: What the seam produced — an
            :class:`~ccf.agents.assembler.AssemblyOutcome`, a
            :class:`~ccf.products.refusal.RefusalEnvelope`, or any bare refusal
            value :data:`~ccf.products.refusal.REFUSAL_KINDS` names. Anything
            else is *not a refusal*, which is a valid answer here.
        claimed: The block the caller intends to record, when it wants that
            intention checked against ``outcome``. ``None`` — the default —
            asks for no check and simply derives.

    Returns:
        The canonical bytes of the refusal, decoded, or
        :data:`NO_ASSEMBLY_REFUSAL` when the outcome is not a refusal.

    Raises:
        FalseAssemblyRefusalClaimError: ``claimed`` contradicts ``outcome`` in
            either direction.
    """
    if _is_refusal_value(outcome):
        if claimed is not None and claimed == NO_ASSEMBLY_REFUSAL:
            reason = getattr(outcome, "reason", type(outcome).__name__)
            raise FalseAssemblyRefusalClaimError(
                "the seam returned a governed refusal"
                f" ({reason!r}) while the caller asserted"
                f" {NO_ASSEMBLY_REFUSAL!r}; a decision that was refused and a"
                " decision whose caller dropped the refusal would otherwise be"
                " the same artifact"
            )
        return canonical_bytes(outcome).decode("utf-8")
    if claimed is not None and claimed != NO_ASSEMBLY_REFUSAL:
        raise FalseAssemblyRefusalClaimError(
            "the caller asserted a governed refusal while the seam"
            " returned an outcome; asserting a refusal that did not happen"
            " corrupts dimension 5 exactly as dropping one does"
        )
    return NO_ASSEMBLY_REFUSAL


def _admissible_refusal_block(block: str) -> str:
    """``block`` if it is the sentinel or a real refusal, else refuse it.

    A hand-written block that merely *looks* like a refusal is the flattening
    :func:`~ccf.products.refusal.envelope_for` exists to forbid, so the builder
    admits only the positive sentinel or a value that round-trips as one of the
    two governed shapes:

    * a :class:`~ccf.products.refusal.RefusalEnvelope` — the shell form every
      shipped refusal kind crosses in, and what ``24.6-07`` records for every
      refusal the delivery boundary reaches;
    * a :class:`~ccf.products.request.ProductRequestViolation` — the **legacy**
      form D-60 shipped, still admitted so every record written before
      ``24.6-07`` still round-trips.

    The two cannot be confused: both are ``extra=forbid`` and neither's
    required field set is a subset of the other's, so a block validates as at
    most one of them. The envelope is tried first because it is what the tree
    now mints; the violation is the fallback, which is what makes this a
    widening rather than a replacement.
    """
    if block == NO_ASSEMBLY_REFUSAL:
        return block
    envelope_class, _, _ = _refusal_names()
    refusal: CCFContract
    try:
        refusal = envelope_class.model_validate_json(block)
    except ValueError as not_an_envelope:
        try:
            refusal = ProductRequestViolation.model_validate_json(block)
        except ValueError as invalid:
            raise ValueError(
                "assembly_refusal must be either the positive sentinel"
                f" {NO_ASSEMBLY_REFUSAL!r} or the canonical serialization of a"
                " governed refusal — a `RefusalEnvelope`, or the legacy"
                " `ProductRequestViolation` D-60 shipped; the value given is"
                f" neither (as an envelope: {not_an_envelope}; as a violation:"
                f" {invalid})"
            ) from invalid
    # RE-CANONICALIZED, not returned verbatim. Validating that a block *parses*
    # and then storing the caller's own bytes would let one refusal land as a
    # FAMILY of blocks — reorder the keys, change the whitespace, and dimension
    # 5 differs for an identical refusal. Replay identity is a property of the
    # VALUE, so the value is what is re-serialized here. The close panel found
    # this: the refusal message claimed "canonical serialization" while the
    # check proved only "parses", which is shape-checked and identity-claimed.
    return canonical_bytes(refusal).decode("utf-8")


def _conditioned(
    conditioning: PerspectiveConditioning,
    *,
    assembler_id: str | None,
    assembler_version: str | None,
) -> PerspectiveConditioning:
    """Dimension 4 with the assembler in force stamped onto it (24.6-07).

    ``D-IMPL-253`` Q16; CLAUDE.md §6.2. Returned **unchanged** when neither
    value was supplied, so the extension is inert for every caller written
    before it — the two fields keep their :data:`NO_ASSEMBLER` defaults and
    the conditioning is the same object, not a re-validated copy of it.

    ``model_copy`` rather than reconstruction: an ``agent_conditioning`` a
    caller serialized from its own construction-time identity must keep every
    field it carried, and re-listing them here would be a transcription that
    silently drops the next field somebody adds.
    """
    if assembler_id is None and assembler_version is None:
        return conditioning
    return conditioning.model_copy(
        update={
            "assembler_id": (
                assembler_id if assembler_id is not None else NO_ASSEMBLER
            ),
            "assembler_version": (
                assembler_version
                if assembler_version is not None
                else NO_ASSEMBLER
            ),
        }
    )


def build_replay_record(
    *,
    execution: ExecutionResult | None,
    product: ContextProductContract | None,
    perspective: Perspective,
    policy_bindings: tuple[PolicyBinding, ...],
    assembly_mode: AssemblyMode,
    recorded_at: datetime,
    resolution: "EffectiveRequest | ResolutionNotApplicable",
    refusal: "RefusalEnvelope | None" = None,
    tenant_id: str | None = None,
    assembler_id: str | None = None,
    assembler_version: str | None = None,
    disclosure: str | None = None,
    agent_conditioning: PerspectiveConditioning | None = None,
    harness_trace: HarnessTrace | None = None,
    packaging_trace: PackagingTrace | None = None,
    served_at: datetime | None = None,
    hitl_actions: str | None = None,
    workflow_step_sequence: str | None = None,
    assembly_refusal: str | None = None,
    refusal_seam: str = NO_REFUSAL_SEAM,
    adapter: AdapterPin | None = None,
    request: ProductRequest | None = None,
    child_resolutions: tuple[ChildResolution, ...] = (),
    issuance: str | None = None,
    subject_withholding: str | None = None,
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

    ``assembly_refusal`` is the D-60 assembler seam (D-IMPL-214 Reading B):
    the pre-serialized block :func:`mint_assembly_refusal` derived from what
    the assembler returned, recorded **verbatim** and never reconstructed
    here, defaulting to :data:`NO_ASSEMBLY_REFUSAL`. Admitted only when it is
    that sentinel or a value that round-trips as a
    :class:`~ccf.products.request.ProductRequestViolation`.

    **What this did NOT close, and what 24.6-07 closed.** A caller that never
    calls :func:`mint_assembly_refusal` and hand-passes the sentinel while
    holding a refusal still produces a well-formed, FALSE record on the
    *served* path. The shape check above stops a *fabricated* block; it does
    not stop a *truthful-looking silence*, and
    :class:`FalseAssemblyRefusalClaimError` reaches only callers that ask for
    the check. Phase 24.1.1 recorded that closing it needs the refusal VALUE to
    travel in here rather than a pre-serialized block — Reading A's shape,
    refused then because it pulls :mod:`ccf.replay.serve` and
    :mod:`ccf.products.resolver` in. ``D-IMPL-253`` Q13 asked for exactly that
    reading, and ``refusal`` below is it: on the refusal path the value
    arrives, this builder mints the block itself, and there is no silence for a
    caller to pass. The **served** path's residual stands unchanged.

    ``refusal`` is the 24.6-07 refusal path (``24.6-L-08``; ``D-IMPL-253``
    Q13 — Dave: *"Refusal is itself a decision and deserves the same
    five-dimensional replay model. Do not create second-class replay."*).
    **Exactly one** of ``product`` and ``refusal`` is passed, and passing
    ``product`` requires an ``execution``; the guard is at the top of the body
    rather than in a docstring, because a record carrying both or neither is
    not a record of anything.

    What a refusal outcome does to each dimension:

    1. With no ``execution`` — a refusal reached before the graph was touched
       — dimension 1 is :meth:`ContextFabricSnapshot.unread`, carrying the
       positive :data:`NO_FABRIC_READ` claim. With one — a gate or tolerance
       refusal, which has a real execution behind it — dimension 1 is built
       **exactly** as a served product's, because the same state was read.
    2. Unchanged: the bindings, the resolution and the adapter are facts about
       the governed inputs, and a refusal has the same ones a fulfillment
       would have had.
    3. Unchanged.
    4. ``role`` is the role the determination was made under; it may be
       :data:`NO_ROLE_RESOLVED` — the positive claim that no role of the
       caller's was established before the delivery boundary denied
       (``D-IMPL-260`` P-D).
    5. ``product_content_address`` is :data:`NO_PRODUCT_ADDRESS`, ``steps`` is
       empty, ``plan_id`` comes from the execution or asserts
       :data:`NO_FABRIC_READ`, ``debt`` comes from the refusal's own permitted
       evidence when it carries any, and ``assembly_refusal`` is the envelope
       **as it stood before it learned its own address**: the recorded shell
       always carries :data:`~ccf.products.refusal.NO_REPLAY_REFERENCE`,
       because a record whose content address covered a reference to itself
       could not be content-addressed at all.

    ``tenant_id`` is required exactly when there is no ``product`` to read it
    off; supplying it beside a product is refused rather than silently
    preferred, because two sources for one fact is how a record comes to
    disagree with the vessel it describes.

    ``assembler_id`` / ``assembler_version`` are the ``D-IMPL-245`` amendment 1
    carriage (``D-IMPL-253`` Q16; CLAUDE.md §6.2), threaded onto dimension 4
    for a **served and a refused** outcome alike — which assembler produced
    the decision is the same question either way. ``None`` yields the positive
    :data:`NO_ASSEMBLER` claim, and every field the builder wrote before this
    extension is byte-for-byte what it was.

    ``disclosure`` is the Disclosure layer's own record (``D-IMPL-254``),
    threaded onto dimension 5. ``None`` yields
    :data:`NO_DISCLOSURE_DECISION`. ``24.6-08`` is the plan that passes it.

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

    ``resolution`` is the 24.6-03 Authority seam (``D-IMPL-253`` Q1/Q6,
    ``D-IMPL-254``), threaded into dimension 2 exactly as ``adapter`` is —
    and, as of 24.7-04, REQUIRED (``D-IMPL-264`` D-10, P-2). The caller
    states one of two things: the
    :class:`~ccf.products.provenance.EffectiveRequest` its constraint
    resolver produced — complete, or the partial record a resolver
    established before refusing (D-07) — or a :class:`ResolutionNotApplicable`
    marker with the reason no resolution applies (D-09). This builder renders
    either — from the **value**, with
    :func:`~ccf.contracts.canonical.canonical_bytes`, so one resolution has
    one rendering and a marker is never accepted pre-serialized.

    There is no third choice. Omitting ``resolution`` is a ``TypeError`` at
    the call — the signature has no default to fall back to — and passing
    ``None`` is a ``ValueError`` from the first guard below. Dave: *"No
    implicit omission for new records"*; *"Missing resolution information
    is an internal integrity failure."* Nothing here infers the marker from
    an absent argument: a record that cannot say whether resolution ran is
    not built. The legacy :data:`NO_REQUEST_RESOLUTION` sentinel is still
    what a record written before this extension reads (D-12) — it is the
    field's default, never this builder's output.

    It is a **parameter** and not a fact read off ``execution`` for
    ``adapter``'s first reason: the resolution happens *before* the engine runs
    — that is what makes it able to bound the question the engine is given — so
    the execution object has never seen it.

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

    ``issuance`` is the identifier the answer is issued under (Dave's Q11,
    2026-10-07; ``D-IMPL-378``): a fresh :func:`new_issuance` value from the
    determination that issues the answer — the governed resolver's served path
    and the reference refusal recorder — recorded verbatim in dimension 5 and
    never minted here, so a record built for comparison keeps
    :data:`NO_ISSUANCE` and its address.

    ``subject_withholding`` is what the deciding class's declaration affirms
    about withholding its subject (Dave's Q12; ``D-IMPL-378``), passed by the
    determination that knows the class and recorded verbatim in dimension 5;
    ``None`` records :data:`UNSTATED_SUBJECT_WITHHOLDING`.
    """
    # 24.7-04: the resolution-state guard, FIRST — before any outcome is
    # judged — because a missing resolution state is not a malformed outcome,
    # it is an integrity failure of the caller (`D-IMPL-264` P-2). `None` is
    # the omission the ruling closed; the signature has no default, so an
    # omitted keyword never reaches here at all.
    if resolution is None:
        raise ValueError(
            "build_replay_record requires an explicit resolution state: the"
            " `EffectiveRequest` the resolution produced (complete or partial),"
            " or a `ResolutionNotApplicable` marker stating why none applies."
            " `None` is neither. `D-IMPL-264` D-10 / P-2: \"`not applicable`"
            " is an explicit governed fact with a reason. Missing resolution"
            " information is an internal integrity failure.\""
        )
    # Function-local for the reason `_refusal_names` is (DEF-17-02): the
    # module-scope import is typing-only, and the runtime needs the value
    # only here.
    from ccf.products.provenance import EffectiveRequest

    if not isinstance(resolution, (EffectiveRequest, ResolutionNotApplicable)):
        raise ValueError(
            "the resolution state is rendered from the VALUE, once, by this"
            " builder, and is never accepted pre-serialized: pass the"
            " `EffectiveRequest` or the `ResolutionNotApplicable` marker"
            f" itself, not a {type(resolution).__name__}. A block a caller"
            " serialized could be a family of blocks (24.6-03)"
        )
    # 24.6-07: the outcome guard, next and before anything is derived. A
    # record carrying both halves would describe two decisions and a record
    # carrying neither would describe none, so both are unrepresentable rather
    # than merely discouraged — the `DoorOutcome._exactly_one_half` posture,
    # applied where the record is minted.
    if (product is None) == (refusal is None):
        raise ValueError(
            "build_replay_record records exactly one outcome: a `product`"
            " (a fulfilled decision) or a `refusal` (a governed no), never"
            " both and never neither. A refusal is a decision and deserves the"
            " same five dimensions (`D-IMPL-253` Q13), which is why it is an"
            " outcome here rather than an annotation on a product record"
        )
    if product is not None and execution is None:
        raise ValueError(
            "a fulfilled decision is recorded from the execution that produced"
            " it: dimensions 1 and 5 are derived from `execution`, and a"
            " product recorded without one would carry an invented fabric"
            " snapshot and an empty generation path. Only a refusal may be"
            " recorded with no execution, and only when the fabric genuinely"
            " read nothing"
        )
    if product is not None and tenant_id is not None:
        raise ValueError(
            "`tenant_id` is read off the product when there is one, so passing"
            " both is two sources for one fact — which is how a record comes"
            " to disagree with the vessel it describes. Pass `tenant_id` only"
            " on the refusal path, where there is no vessel to read it from"
        )
    if product is None and tenant_id is None:
        raise ValueError(
            "a refusal carries no vessel, so the tenant the determination was"
            " made under has to be stated: pass `tenant_id`"
        )
    if refusal is not None and assembly_refusal is not None:
        raise ValueError(
            "`refusal` and `assembly_refusal` are two spellings of one"
            " dimension-5 fact and this call supplies both. `refusal` is the"
            " VALUE, from which this builder mints the block itself;"
            " `assembly_refusal` is the pre-serialized block the assembler"
            " seam has passed since D-60. Accepting both would mean silently"
            " preferring one, and a caller whose block was dropped would have"
            " no way to tell. Pass the value"
        )

    _, _, no_replay_reference = _refusal_names()
    recorded_tenant = product.tenant_id if product is not None else tenant_id
    assert recorded_tenant is not None  # the four guards above establish this
    boundary = (
        product.temporal_boundary if product is not None else recorded_at
    )

    if execution is not None:
        snapshot = ContextFabricSnapshot.build(
            tenant_id=recorded_tenant,
            temporal_boundary=boundary,
            store_watermark=execution.state_watermark(),
            touched_entities=execution.touched_entities(),
            touched_relationships=execution.touched_relationships(),
            source_attestation=execution.source_attestation,
            # 24.5-L-02: the head the engine read under, into dimension 1
            # exactly where the attestation goes and for the same reason —
            # replay resolves this pin, never the head now.
            store_snapshot_pin=execution.store_snapshot_pin,
        )
    else:
        # 24.6-07: nothing was read, and dimension 1 SAYS so. Never
        # `build(...)` with an empty watermark — that would claim the graph
        # was read and found empty, which is a different and false fact.
        snapshot = ContextFabricSnapshot.unread(
            tenant_id=recorded_tenant, temporal_boundary=boundary
        )

    return DecisionReplayRecord(
        tenant_id=recorded_tenant,
        recorded_at=recorded_at,
        context_fabric_snapshot=snapshot,
        policy_bindings=PolicyBindingsSnapshot(
            bindings=policy_bindings,
            hitl_actions=hitl_actions if hitl_actions is not None else NO_HITL_ACTIONS,
            survivor_cap=(
                execution.survivor_cap if execution is not None else None
            ),
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
            # 24.6-03: the Authority layer's own value, rendered once from the
            # VALUE rather than accepted as a pre-serialized block — the
            # `_admissible_refusal_block` argument, applied where it can be
            # applied absolutely: a resolution cannot land as a family of
            # blocks because the caller never hands one over. 24.7-04: the
            # same expression renders the not-applicable marker; there is no
            # sentinel branch because there is no `None` to reach it
            # (`D-IMPL-264` D-10). The sentinel stays the FIELD default so a
            # record parsed from bytes that omit it still reads it (D-12).
            request_resolution=canonical_bytes(resolution).decode("utf-8"),
        ),
        model_version=ModelVersionRecord(
            assembly_mode=assembly_mode,
            harness_trace=harness_trace
            if harness_trace is not None
            else NO_HARNESS_TRACE,
            # §7.10.4's Mode 2 footprint, recorded VERBATIM from the packaging
            # stage rather than re-derived from the payload here. A record
            # that re-observed the pins would be reporting what the payload
            # says now, not what the packager did — and the whole point of
            # holding `output_hash` beside `product_content_address` is to let
            # an examiner ask whether those two ever disagreed.
            #
            # `None` keeps the no-packaging sentinel, which is the TRUE claim
            # for Mode 1 and for any Mode 2 deployment that supplies no
            # trace — and `PKG-G09` is what stops the latter passing silently.
            packaging_trace=packaging_trace
            if packaging_trace is not None
            else NO_PACKAGING_TRACE,
        ),
        # 24.6-07: dimension 4 is the caller's conditioning, then the
        # assembler's identity stamped onto it. A `model_copy` rather than two
        # construction branches, so an `agent_conditioning` a caller
        # serialized keeps every field it carried and gains only what this
        # extension adds — CLAUDE.md §6.2 puts agent identity here, and
        # `D-IMPL-253` Q16 puts the assembler's beside it.
        perspective_conditioning=_conditioned(
            agent_conditioning
            or PerspectiveConditioning(
                principal_id=perspective.principal_id,
                role=perspective.role,
                delegation_chain=(perspective.principal_id,),
            ),
            assembler_id=assembler_id,
            assembler_version=assembler_version,
        ),
        content_generation_path=ContentGenerationPath(
            # 24.6-07: a refusal reached before any plan ran has no plan, and
            # the same positive claim dimension 1 makes is the honest one
            # here — nothing was read, so nothing was planned over it.
            plan_id=execution.plan_id if execution is not None else NO_FABRIC_READ,
            operator_plan=(
                tuple(step.operator_key for step in execution.steps)
                if execution is not None
                else ()
            ),
            steps=execution.steps if execution is not None else (),
            # 24.6-07: a refusal produced nothing to address, and says so.
            product_content_address=(
                content_hash(product)
                if product is not None
                else NO_PRODUCT_ADDRESS
            ),
            disclosure_decision=(
                disclosure if disclosure is not None else NO_DISCLOSURE_DECISION
            ),
            # `D-IMPL-336` Amendment 3, F0 — the per-child rows, GENERATED FROM
            # EXECUTION. Until this parameter existed the field could be
            # declared and never written, which is why a composite could be
            # recorded with no evidence that any child was ever admitted.
            child_resolutions=child_resolutions,
            ttl_anchor_at=product.ttl_anchor_at if product is not None else None,
            # SEC-020: the empty finding, copied as `ttl_anchor_at` is.
            computed_empty=product.computed_empty if product is not None else None,
            # `D-IMPL-358` step 4. Passed rather than derived: `ttl_anchor_at`
            # above can be read off the product because the product carries it,
            # and no artifact carries the instant the answer was handed over —
            # only the resolver that read the clock knows it. Defaults to `None`,
            # so every caller that does not supply it writes a record whose
            # address is exactly what it was.
            served_at=served_at,
            # Dave's Q11 (`D-IMPL-378`): passed, never minted here — the
            # determination that issues the answer mints it (`new_issuance`),
            # so a record built for comparison or by a writer that issues none
            # keeps the sentinel and its address.
            issuance=issuance if issuance is not None else NO_ISSUANCE,
            # Dave's Q12 (`D-IMPL-378`): passed by the determination that knows
            # the deciding class; a writer that does not say leaves the sentinel.
            subject_withholding=(
                subject_withholding
                if subject_withholding is not None
                else UNSTATED_SUBJECT_WITHHOLDING
            ),
            workflow_step_sequence=workflow_step_sequence
            if workflow_step_sequence is not None
            else NO_WORKFLOW_TRACE,
            # 24.6-07: on the refusal path the VALUE arrives and this builder
            # mints the block — Reading A's shape, which is what closes the
            # truthful-looking-silence hole the served path still carries. The
            # recorded shell is the shell BEFORE it learned its own address:
            # a record whose content address covered a reference to itself
            # could not be content-addressed at all.
            assembly_refusal=(
                mint_assembly_refusal(
                    refusal.model_copy(
                        update={"replay_reference": no_replay_reference}
                    )
                )
                if refusal is not None
                else (
                    _admissible_refusal_block(assembly_refusal)
                    if assembly_refusal is not None
                    else NO_ASSEMBLY_REFUSAL
                )
            ),
            refusal_seam=refusal_seam,
            graph_query_sequence=(
                tuple(content_hash(query) for query in execution.executed_queries)
                if execution is not None
                else NO_GRAPH_QUERIES
            ),
            # D-IMPL-100: read off the product, not off a parameter. The
            # product is already here, so no call site moves — and a record
            # pinning a debt its product does not carry cannot be constructed.
            #
            # 24.6-07: on the refusal path the same reasoning reaches one step
            # further out — the assessment is read off the refusal's own
            # PERMITTED evidence, so a record pinning a debt the shell does
            # not carry is equally unrepresentable.
            debt=(
                product.debt
                if product is not None
                else (
                    refusal.evidence.debt
                    if refusal is not None and refusal.evidence is not None
                    else None
                )
            ),
            # D-IMPL-118: read off the product for debt's reason, and carried
            # at all for a harder one — the carrier is a top-level vessel
            # field, so `(record, projection)` cannot rebuild it from anywhere
            # else and every replay would diverge without this line.
            debt_evidence=(
                product.debt_evidence if product is not None else NO_DEBT_EVIDENCE
            ),
            # D-IMPL-117 gap 2, under the same D-IMPL-118 placement and for
            # the same two reasons: read off the product so no call site
            # moves, and carried at all because a top-level vessel field is
            # reconstructible from nowhere else.
            source_refresh_recency=(
                product.source_refresh_recency
                if product is not None
                else NO_SOURCE_REFRESH_RECENCY
            ),
            # D-IMPL-117 gap 3, under the same D-IMPL-118 placement, and
            # carried for a reason the other two do not have: without this
            # line a rehydrator's only route to the value is the deployment's
            # CURRENT debt profile, which would answer "what was this decision
            # obliged to do?" with today's binding (D-IMPL-26).
            obligation_in_force=(
                product.obligation_in_force
                if product is not None
                else NO_OBLIGATION_IN_FORCE
            ),
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
from ccf.products.request import (  # noqa: E402
    ProductRequest,
    ProductRequestViolation,
)

ContentGenerationPath.model_rebuild()
