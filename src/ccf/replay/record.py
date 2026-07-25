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
   binding in force (INV-CH7-82).
3. **Model Version Record** — every invoked model; literally ``"none"`` in
   Mode 1 (INV-CH7-83). A positive claim, not an omission.
4. **Perspective Conditioning** — principal and role in I.1 (INV-CH7-84);
   agent identity, version, and skill-set in force extend this dimension in
   I.2 per CLAUDE.md §6.2.
5. **Content Generation Path** — the operator plan and its executed step
   sequence, plus the content address of the product produced (INV-CH7-85);
   workflow step sequences extend it in I.4 per CLAUDE.md §8.1.

The record is a frozen contract, so it is canonically serializable and
content-addressable: a replay resolves the *exact* record, byte for byte,
rather than something that looks like it (D-IMPL-26).

Nothing here reads a clock. ``recorded_at`` is supplied by the caller, like
every other instant in the fabric.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.products.contract import AssemblyMode, ContextProductContract
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = [
    "MODE_1_MODEL_VERSION",
    "ContentGenerationPath",
    "ContextFabricSnapshot",
    "DecisionReplayRecord",
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

    HITL actions extend this dimension in I.4 (CLAUDE.md §8.2); the shape is
    additive by design.
    """

    bindings: tuple[PolicyBinding, ...]


class ModelVersionRecord(CCFContract):
    """Dimension 3 — the models invoked (INV-CH7-83).

    ``model_version`` defaults to :data:`MODE_1_MODEL_VERSION` because I.1 is
    Mode 1 throughout — the fabric core invokes no model, and the record says
    so rather than staying silent. Mode 2 supplies the real version alongside
    the other three pinned rendering primitives when the LLM packaging stage
    lands.
    """

    assembly_mode: AssemblyMode
    model_version: str = MODE_1_MODEL_VERSION


class PerspectiveConditioning(CCFContract):
    """Dimension 4 — whose viewpoint conditioned the decision (INV-CH7-84).

    Agent identity, agent version, and the skill-set in force extend this in
    I.2 (CLAUDE.md §6.2). ``delegation_chain`` is present now because a
    perspective inherited through a handoff is a different perspective from one
    held directly, and retrofitting that distinction onto historical records is
    impossible.
    """

    principal_id: str
    role: str
    delegation_chain: tuple[str, ...] = ()


class ContentGenerationPath(CCFContract):
    """Dimension 5 — how the delivered content came to be (INV-CH7-85).

    ``steps`` carries the executed order, not merely the set: a
    Policy-before-Similarity run and its forbidden inverse invoke the same
    operators and are not the same decision.
    """

    plan_id: str
    operator_plan: tuple[str, ...]
    steps: tuple[ExecutionStep, ...]
    product_content_address: str


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
) -> DecisionReplayRecord:
    """Assemble the record from what the execution and the product already know.

    Every dimension is derived from artifacts that exist independently of the
    record — the engine's own execution result, the gated product, the
    perspective the caller conditioned on, the Control Plane bindings in force.
    Nothing is re-observed at record time, because a record that measured
    anything itself would be recording the state at *recording* time rather
    than at decision time.
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
        policy_bindings=PolicyBindingsSnapshot(bindings=policy_bindings),
        model_version=ModelVersionRecord(assembly_mode=assembly_mode),
        perspective_conditioning=PerspectiveConditioning(
            principal_id=perspective.principal_id, role=perspective.role
        ),
        content_generation_path=ContentGenerationPath(
            plan_id=execution.plan_id,
            operator_plan=tuple(step.operator_key for step in execution.steps),
            steps=execution.steps,
            product_content_address=content_hash(product),
        ),
    )
