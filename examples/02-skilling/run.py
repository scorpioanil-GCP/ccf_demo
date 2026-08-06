"""examples/02-skilling — governed skilling, channel 2 (EXAM-03).

Grant a skill to a running agent through the Control Plane, exercise it, and
revoke it — with the governance compatibility check refusing an impermissible
grant, every transition audited, and the skill-set in force captured in the
Decision Replay record. Clinical-trials-operations domain, keyless and
model-free (D-12) on SQLite and the file-backed ArtifactStore.

This file is the **call spine** an adopter would actually write, and nothing
else. It asserts nothing and prints nothing: its assertions live in
``tests/examples/test_skilling_output.py``, where they are run by ``pytest`` and
can fail a build (D-09). ``make example-02`` running clean means the spine
executed.

What the spine demonstrates (CLAUDE.md §6.2):

* **The agent definition never changes.** Skilling is the capability channel;
  ``artifacts/agent-definition.yaml`` is byte-identical before and after the
  whole grant/exercise/revoke cycle, and the definition's content hash — the
  agent's identity — never moves.
* **Tier-1 governance is structural and non-waivable.** A grant whose declared
  requirements exceed the agent's policy regime is refused with a typed
  returned value naming the excess scopes; nothing binds.
* **Every grant and revocation is audited** on the one Control Plane audit log.
* **Replay captures the skill-set in force** (D-07): the record built at the
  exercise step carries the in-force grant-set hash in dimension 4 — a decision
  replays against the skills the agent actually had.

**Three operators, not four.** This fabric registers a traversal, a temporal
and a policy operator and no similarity operator. That is expressed only by
which artifacts ``artifacts/manifest.yaml`` names: the ``parameters`` mapping
handed to ``build_operator_registry`` has three entries. No flag, no ``None``,
no disabled operator.

Two further documents each declare those same three keys, separately, and
which three they name has to agree (design E2, D-IMPL-86):
``artifacts/projection-requirements.yaml`` is the PROJECTION's requirement and
is what ``TrialOpsPlan`` is built from; ``artifacts/product-class.yaml`` is the
product's CLAIM and is what fills ``lineage.operators_invoked``. ``run``
refuses before it projects if the two disagree.

Every domain value — scopes, catalog entries, grants, expected outputs — is
loaded from ``artifacts/*.yaml`` (§6.4). Run it: ``make example-02``.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from ccf.agents.agent import Agent
from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.agents.factory import AgentFactory
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
    declared_artifact_class,
    load_artifact,
)
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import (
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, ServedProduct, serve
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog
from ccf.skills.dispatch import SkillInvocation
from ccf.skills.grants import (
    ApprovalOutcome,
    GrantLedger,
    GrantRefusal,
    SkillGrant,
)

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MANIFEST = ARTIFACTS / "manifest.yaml"

#: Read one line before the manifest: the decision instant is the clock this
#: deployment injects into the Control Plane registry, and that registry is an
#: argument to `load_and_boot`.
DECISION_DOCUMENT = ARTIFACTS / "decision.yaml"

#: Author-versioned, so registered here rather than by the manifest — see the
#: `agent-registration.yaml` and `skilling-scenario.yaml` documents.
AGENT_DEFINITION_DOCUMENT = ARTIFACTS / "agent-definition.yaml"


class TrialOpsPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    ``required`` is passed in from ``artifacts/projection-requirements.yaml``
    — this projection's OWN authored operator set, three keys here, matching
    the three operators this deployment registers — and never read off the
    operator registry, which would make the plan's requirements a restatement
    of whatever happens to be registered.

    The product class's ``required_operator_keys`` names the same three keys
    and is a different statement about a different thing: the CLAIM the product
    carries into ``lineage.operators_invoked``. Two documents, one per side,
    held together by the operator-set binder in :mod:`ccf.deployment`, which
    ``run`` below calls between constructing this plan and executing it — so a
    disagreement between the two is a refusal rather than an identity nobody
    can see (design E2, D-IMPL-86).
    """

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "entity_class": record.claim.entity_class,
                    }
                    for record in view.entities
                ],
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
            },
        )


class UnconsultedSink:
    """ApprovalSink conformance for an auto regime (D-IMPL-29).

    The agent's regime declares ``grant_requires_approval: false``, so tier 2
    must never be consulted — and a consultation is a hard failure rather than
    a silent approval.
    """

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError("tier-2 sink consulted under an auto regime (D-IMPL-29)")


def _bind_callable(record: Mapping[str, Any]) -> Any:
    """Composition-root callable factory (D-19).

    Mechanism only — the output content is artifact data, merged with the typed
    arguments at invoke time. Deterministic and side-effect free.
    """

    def _invoke(arguments: Mapping[str, str]) -> dict[str, Any]:
        return {**record, **arguments}

    return _invoke


@dataclass(frozen=True)
class SkillingResult:
    """What one run of the spine produced, for a caller to inspect."""

    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    audit: AuditLog
    definition: AgentDefinition
    definition_hash: str
    definition_version: str
    definition_bytes_before: bytes
    definition_bytes_after: bytes
    registry: ControlPlaneRegistry
    catalog: SkillCatalog
    ledger: GrantLedger
    agent: Agent
    bound_before_grant: tuple[str, ...]
    grant_set_hash_before_grant: str
    product: ContextProductContract
    consumed: ContextProductContract
    operator_keys: tuple[str, ...]
    operators_invoked: tuple[str, ...]
    permitted_grant: SkillGrant
    permitted_grant_outcome: object
    permitted_state_after_grant: str
    permitted_state_after_revocation: str
    grant_set_hash_in_force: str
    bound_after_grant: tuple[str, ...]
    invocation: SkillInvocation
    refusal: GrantRefusal
    bound_after_refusal: tuple[str, ...]
    grant_set_hash_after_refusal: str
    bound_after_revocation: tuple[str, ...]
    grant_set_hash_after_revocation: str
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def run(*, root: Path) -> SkillingResult:
    """Run the fabric, the agent and the full skilling cycle once."""
    # The byte-identity baseline: the agent definition artifact as authored,
    # before any channel-2 activity (§6.2 — skilling never re-declares).
    definition_bytes_before = AGENT_DEFINITION_DOCUMENT.read_bytes()

    decision = cast(
        DeclaredArtifact,
        load_artifact(
            DECISION_DOCUMENT.read_text(encoding="utf-8"),
            declared_artifact_class("helix-trials.decision-inputs"),
        ),
    )
    boundary = datetime.fromisoformat(decision.declaration["temporal_boundary"])
    now = datetime.fromisoformat(decision.declaration["now"])

    # One registry, one audit log, one injected clock — shared by the fabric,
    # the catalog and the grant ledger, because the Control Plane is the audit
    # plane, singular (whitepaper §7.8.2).
    audit = AuditLog()
    registry = ControlPlaneRegistry(clock=lambda: now, audit_log=audit)

    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(root / "skilling.sqlite3")
    )
    try:
        events = cast(SignalBatch, booted.artifacts["events"])
        governance = cast(DeclaredArtifact, booted.artifacts["product-governance"])
        declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
        # The projection's own operator set, authored separately from the claim
        # `declared` carries. Design E2 keeps these two documents apart on
        # purpose; the binder below is what keeps them in agreement.
        requirements = cast(
            ProjectionRequirements, booted.artifacts["projection-requirements"]
        )
        perspective = cast(PerspectiveArtifact, booted.artifacts["perspective"])
        registration = cast(DeclaredArtifact, booted.artifacts["agent-registration"])
        scenario = cast(
            DeclaredArtifact, booted.artifacts["skilling-scenario"]
        ).declaration

        # The agent definition: author-versioned, so registered through the
        # D-05 bump-check path rather than by the manifest.
        definition = AGENT_DEFINITION.validate(
            load_artifact(
                AGENT_DEFINITION_DOCUMENT.read_text(encoding="utf-8"),
                AGENT_DEFINITION,
            )
        )
        definition_key = registration.declaration["agent_definition_key"]
        match registry.register_versioned(
            definition_key, definition, AGENT_DEFINITION
        ):
            case str() as definition_version:
                pass
            case refused_definition:
                raise RuntimeError(
                    f"the Control Plane refused the agent definition:"
                    f" {refused_definition}"
                )
        definition_hash = content_hash(definition)

        for envelope in events.envelopes:
            booted.handle.worker.ingest(envelope)

        view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)

        # THREE manifest keys, not four. Which operators exist is this
        # deployment's decision, expressed by which artifacts it declares — the
        # builder holds no fixed set of categories.
        parameters = {
            key: cast(Any, booted.artifacts[key])
            for key in ("traversal", "temporal", "policy")
        }
        operators = build_operator_registry(
            parameters=parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key="policy-bundle",
        )

        # The plan's three keys come from the projection's own
        # `projection-requirements.yaml` — never from the operator registry's
        # keys. The product class's `required_operator_keys` is the separate
        # document naming the same three, and the binder call between the two
        # lines below is where a disagreement between them fails: before
        # anything is assembled, by refusal rather than repair (design E2,
        # D-IMPL-86).
        #
        # The plan is a named local rather than an argument expression for
        # exactly that reason — the binder has to be handed the same object the
        # engine will run.
        plan = TrialOpsPlan(
            plan_id=requirements.plan_id,
            required=requirements.required_operator_keys,
        )
        refuse_operator_set_divergence(declared=declared, plan=plan)
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=plan,
            perspective=perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
        )

        # L6 — the MAX_TTL registration and the product-class registration stay
        # in adopter code: the pin is minted by registering the ceiling, so a
        # helper doing both would make Gate 3 compare a value against itself.
        max_ttl_version = registry.register(
            declared.max_ttl_key,
            MaxTTL(seconds=governance.declaration["max_ttl_seconds"]),
        )
        product_class = register_product_class(
            registry=registry,
            schema_name=declared.schema_name,
            schema_version=declared.schema_version,
            ttl_anchor=declared.ttl_anchor,
            assembly_mode=declared.assembly_mode,
            max_ttl_key=declared.max_ttl_key,
            max_ttl_version=max_ttl_version,
        )
        # The lineage the product CLAIMS, and the gates.
        #
        # `operators_invoked` is filled from the product-class DECLARATION — the
        # Control Plane's statement of what this product was computed by — and
        # never from `execution`. That is design E2's first element (D-IMPL-86):
        # a claim copied out of the execution record is not a claim, it is a
        # transcript.
        #
        # `engine_resolved` stays the engine's own value, and what Gate 2 then
        # verifies is ASSEMBLY-PATH INTEGRITY: the claim transcribed into this
        # Contract equals the engine's execution of the plan. The engine is a
        # faithful TRANSCRIBER of the plan rather than an independent witness of
        # it — it builds `operators_invoked` and `steps` in one loop over the
        # same operator plan, so there is no return path where invoked ≠
        # planned. Gate 2 therefore does not catch a producer misdeclaring;
        # authorable drift fails upstream, at the binder call above.
        policy_version = booted.pins.version_for("policy-bundle")
        candidate = ContextProductContract(
            schema_name=product_class.schema_name,
            schema_version=product_class.schema_version,
            plan_id=execution.plan_id,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
            expires_at=now
            + timedelta(seconds=governance.declaration["product_ttl_seconds"]),
            ttl_anchor=product_class.ttl_anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(declared.required_operator_keys),
                policy_bundle_versions=frozenset({policy_version}),
                graph_snapshot_at=boundary,
            ),
            payload=execution.projection.payload,
        )
        match run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=now,
            registry=registry,
            product_class=product_class,
        ):
            case ServableProduct() as gated:
                pass
            case refused_product:
                raise RuntimeError(
                    f"the three validation gates refused this product:"
                    f" {refused_product}"
                )

        # --8<-- [start:skill-catalog]
        # (1) Register the catalog the scenario artifact enumerates. Each entry
        #     is author-versioned; `SkillCatalog.register` goes through the same
        #     D-05 bump check, which is why the catalog is not in the manifest.
        catalog = SkillCatalog(registry)
        for name in scenario["catalog_documents"]:
            match catalog.register(
                SKILL_CATALOG_ENTRY.validate(
                    load_artifact(
                        (ARTIFACTS / name).read_text(encoding="utf-8"),
                        SKILL_CATALOG_ENTRY,
                    )
                )
            ):
                case str():
                    pass
                case refused_entry:
                    raise RuntimeError(
                        f"the Control Plane refused catalog entry {name}:"
                        f" {refused_entry}"
                    )

        ledger = GrantLedger(
            control_plane=registry,
            catalog=catalog,
            sink=UnconsultedSink(),
            clock=lambda: now,
        )

        # The running agent: factory-constructed once, holding the ledger's LIVE
        # bound view — grants and revocations below take effect at invoke time
        # without touching agent identity (D-07).
        callables = CallableRegistry()
        callables.register(
            scenario["callable"]["registered_key"],
            _bind_callable(scenario["callable"]["output_record"]),
        )
        agent = AgentFactory(
            control_plane=registry, callable_registry=callables
        ).construct(
            definition_key=definition_key,
            definition_version=definition_version,
            bound_skills=ledger.bound_view(definition_hash),
        )
        # --8<-- [end:skill-catalog]

        # Before any grant: nothing is bound, and the zero-grant identity is a
        # positive value rather than an absence (WR-01).
        bound_before_grant = agent.bound_skill_names
        grant_set_hash_before_grant = ledger.grant_set_hash(definition_hash)

        # --8<-- [start:skill-grant]
        # (2) Grant the permitted skill through the Control Plane. Tier 1 is
        #     the compatibility check against the agent's axis-4 regime; it is
        #     mechanism, not policy, and it is not waivable.
        permitted = SkillGrant(
            agent_definition_hash=definition_hash,
            **scenario["grants"]["permitted"],
        )
        permitted_grant_outcome = ledger.request(
            permitted,
            definition=definition,
            actor=scenario["actors"]["requesting_actor"],
        )
        # The ledger is LIVE: its state moves as the cycle proceeds, so each
        # state is read at the step that produced it rather than at the end.
        permitted_state_after_grant = ledger.state(content_hash(permitted))
        grant_set_hash_in_force = ledger.grant_set_hash(definition_hash)
        bound_after_grant = agent.bound_skill_names
        # --8<-- [end:skill-grant]

        # --8<-- [start:skill-exercise]
        # (3) Exercise it, over a deterministic local callable (D-19). The
        #     agent consumes the gated product under its axis-2 contract first.
        consumed = agent.consume(gated.product, now=now)
        invocation = agent.invoke_skill(
            permitted.skill_name, arguments=scenario["dispatch"]["arguments"]
        )
        # --8<-- [end:skill-exercise]

        # Replay at the exercise step: dimension 4 carries the skill-set in
        # force (D-07) — the decision replays against the skills the agent
        # actually had, not the skills it has later. The grant-set hash is
        # CAPTURED from the ledger here, never re-derived at record time.
        conditioning = agent.perspective_conditioning(
            principal_id=perspective.principal_id,
            grant_set_hash=ledger.grant_set_hash(definition_hash),
        )
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key="policy-bundle", version=policy_version),
            ),
            assembly_mode=declared.assembly_mode,
            recorded_at=now,
            agent_conditioning=conditioning,
        )
        store = FileArtifactStore(root=root / "artifacts")
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=store,
                artifact_class=governance.declaration["replay_record_class"],
            ),
        )

        # --8<-- [start:skill-refusal]
        # (4) The impermissible grant. A refusal is a bad request, not a broken
        #     fabric, so it is a typed RETURNED VALUE naming the excess scopes —
        #     and it is audited exactly like an accepted grant.
        impermissible = SkillGrant(
            agent_definition_hash=definition_hash,
            **scenario["grants"]["impermissible"],
        )
        outcome = ledger.request(
            impermissible,
            definition=definition,
            actor=scenario["actors"]["requesting_actor"],
        )
        match outcome:
            case GrantRefusal() as refusal:
                pass
            case bound:
                raise RuntimeError(
                    f"governance admitted a grant exceeding the agent's regime:"
                    f" {bound}"
                )
        bound_after_refusal = agent.bound_skill_names
        grant_set_hash_after_refusal = ledger.grant_set_hash(definition_hash)
        # --8<-- [end:skill-refusal]

        # --8<-- [start:skill-revoke]
        # (5) Revoke. The live bound view means revocation takes effect at
        #     invoke time on the same constructed agent, with no re-declaration
        #     and no change to agent identity (D-07).
        ledger.revoke(
            content_hash(permitted), actor=scenario["actors"]["requesting_actor"]
        )
        permitted_state_after_revocation = ledger.state(content_hash(permitted))
        bound_after_revocation = agent.bound_skill_names
        grant_set_hash_after_revocation = ledger.grant_set_hash(definition_hash)
        # --8<-- [end:skill-revoke]

        # The ENGINE's transcription of the plan, carried out beside the served
        # product. It is deliberately not the same value as
        # `product.lineage.operators_invoked` any more: that is the product's
        # claim, from the product-class declaration. Returning both is what lets
        # `tests/examples/test_skilling_output.py` compare two things.
        engine_transcription = execution.operators_invoked

        return SkillingResult(
            tenant_id=booted.tenant_id,
            artifacts=booted.artifacts,
            audit=audit,
            definition=definition,
            definition_hash=definition_hash,
            definition_version=definition_version,
            definition_bytes_before=definition_bytes_before,
            definition_bytes_after=AGENT_DEFINITION_DOCUMENT.read_bytes(),
            registry=registry,
            catalog=catalog,
            ledger=ledger,
            agent=agent,
            bound_before_grant=bound_before_grant,
            grant_set_hash_before_grant=grant_set_hash_before_grant,
            product=gated.product,
            consumed=consumed,
            operator_keys=operators.keys(),
            operators_invoked=engine_transcription,
            permitted_grant=permitted,
            permitted_grant_outcome=permitted_grant_outcome,
            permitted_state_after_grant=permitted_state_after_grant,
            permitted_state_after_revocation=permitted_state_after_revocation,
            grant_set_hash_in_force=grant_set_hash_in_force,
            bound_after_grant=bound_after_grant,
            invocation=invocation,
            refusal=refusal,
            bound_after_refusal=bound_after_refusal,
            grant_set_hash_after_refusal=grant_set_hash_after_refusal,
            bound_after_revocation=bound_after_revocation,
            grant_set_hash_after_revocation=grant_set_hash_after_revocation,
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-skilling-") as scratch:
        run(root=Path(scratch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
