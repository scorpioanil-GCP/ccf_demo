"""examples/01-agent-basics — archetype/agent separation, six axes (EXAM-02).

Declare an agent from the ``AnalyticsInsightsAgent`` archetype via a definition
artifact, construct it through the Agent Factory — the only supported
construction path (CLAUDE.md §6.4) — and run it against a small field-service
fabric's served Context Product, keyless and model-free (D-12) on SQLite and
the file-backed ArtifactStore (D-13).

This file is the **call spine** an adopter would actually write, and nothing
else. It asserts nothing and prints nothing: its assertions live in
``tests/examples/test_agent_basics_output.py``, where they are run by ``pytest``
and can fail a build (D-09). ``make example-01`` running clean means the spine
executed.

What the spine demonstrates, and where each demonstration is checked:

* **Archetype vs agent (§6.1).** The archetype (``analytics_insights``) is SDK
  mechanism; the agent (``response-time-analytics``) is a declared, versioned
  Control Plane artifact in ``artifacts/agent-definition.yaml``. No agent exists
  in code anywhere in this directory.
* **All six specialization axes (§6.2 channel 1)** resolve from that artifact:
  archetype binding, context contract, perspective, policy regime ref,
  half-life/debt profile ref, instruction bindings.
* **Factory-only construction.** ``AgentFactory.construct`` resolves every
  referenced artifact through Control Plane resolution at pinned versions.
* **Replay dimension 4 (D-06).** The agent's identity — definition content
  hash, versioned URI, archetype composition — lands in the served decision's
  replay record and survives a store round trip.

**Two registration paths, and the split is deliberate.** The fabric's artifacts
come from ``artifacts/manifest.yaml`` through one ``load_and_boot`` call. The
agent definition and the prompt artifact do not: they carry D-IMPL-28 two-field
versioning and must register through ``register_versioned``, which holds the
author's ``artifact_version`` claim against content identity (the D-05 bump
check) — and ``load_and_boot`` registers through ``register_typed``, which does
not. Routing them through the manifest would silently drop that check, so those
two registrations stay here, reading their keys from
``artifacts/agent-registration.yaml``.

Every domain value is loaded from ``artifacts/*.yaml``; the deterministic
analyst stub below is mechanism whose canned output content is artifact data
(D-12). Run it: ``make example-01``.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.definitions import AGENT_DEFINITION, PROMPT_ARTIFACT, AgentDefinition
from ccf.agents.factory import AgentFactory
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    DebtProfile,
    DeclaredArtifact,
    HalfLifeTable,
    PerspectiveArtifact,
    ProductClassDeclaration,
    SignalBatch,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import build_operator_registry, load_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
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
    NO_GRANTS_SET_HASH,
    PerspectiveConditioning,
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, ServedProduct, serve

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MANIFEST = ARTIFACTS / "manifest.yaml"

#: The two author-versioned documents the manifest deliberately does not carry.
#: See the module docstring: they need ``register_versioned``'s D-05 bump check.
AGENT_DEFINITION_DOCUMENT = ARTIFACTS / "agent-definition.yaml"
PROMPT_ARTIFACT_DOCUMENT = ARTIFACTS / "prompt-artifact.yaml"


class FieldServicePlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes (whitepaper
    §7.5). It declares which operators its interpretation depends on and
    interprets their output; it cannot tell the engine what ran, which is what
    leaves the L6 lineage gate something real to check.

    ``required`` is passed in from the product-class artifact's
    ``required_operator_keys``, never read off the operator registry: Gate 2
    compares the declaration against the engine's resolution, and a plan
    returning the registry's own keys would make that a value against itself.
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


class ScriptedAnalyst:
    """The injected deterministic LLM seam (D-12): a scripted client stub.

    The class is mechanism only — the model identifier and every output record
    are artifact data (``artifacts/analysis-output.yaml``), never literals here.
    """

    def __init__(
        self, *, model_version: str, outputs: tuple[Mapping[str, Any], ...]
    ) -> None:
        self._model_version = model_version
        self._outputs = list(outputs)

    @property
    def model_version(self) -> str:
        return self._model_version

    def next_output(self) -> Mapping[str, Any]:
        return self._outputs.pop(0)


@dataclass(frozen=True)
class AgentBasicsResult:
    """What one run of the spine produced, for a caller to inspect.

    The example returns its state rather than checking it here, so that
    ``tests/examples/test_agent_basics_output.py`` can hold the assertions where
    a test runner will actually run them.
    """

    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    registry: ControlPlaneRegistry
    definition: AgentDefinition
    definition_version: str
    agent: Agent
    product: ContextProductContract
    consumed: ContextProductContract
    operators_invoked: tuple[str, ...]
    conditioning: PerspectiveConditioning
    assessment: DebtAssessment
    profile: DebtProfile
    analyst: ScriptedAnalyst
    effect: EmittedEffect
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def run(*, root: Path) -> AgentBasicsResult:
    """Run the fabric and the agent once against ``root`` as scratch space."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every fabric artifact in force, `load_and_boot` parses all of
    #    them, registers the `role: register` ones, and boots on the pins.
    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(root / "agent-basics.sqlite3")
    )
    # --8<-- [end:boot]
    try:
        events = cast(SignalBatch, booted.artifacts["events"])
        decision = cast(DeclaredArtifact, booted.artifacts["decision"])
        governance = cast(DeclaredArtifact, booted.artifacts["product-governance"])
        declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
        perspective = cast(PerspectiveArtifact, booted.artifacts["perspective"])
        registration = cast(DeclaredArtifact, booted.artifacts["agent-registration"])

        boundary = datetime.fromisoformat(decision.declaration["temporal_boundary"])
        now = datetime.fromisoformat(decision.declaration["now"])

        # --8<-- [start:agent-artifacts]
        # 2. The two AUTHOR-VERSIONED artifacts, registered here rather than by
        #    the manifest. `register_versioned` holds the author's
        #    `artifact_version` claim against content identity — the D-05 bump
        #    check — and `load_and_boot`'s `register_typed` path does not. A
        #    manifest entry for either would drop that check silently.
        prompt = load_artifact(
            PROMPT_ARTIFACT_DOCUMENT.read_text(encoding="utf-8"), PROMPT_ARTIFACT
        )
        registry.register_versioned(
            registration.declaration["prompt_artifact_key"], prompt, PROMPT_ARTIFACT
        )

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
            case refusal:
                raise RuntimeError(
                    f"the Control Plane refused the agent definition: {refusal}"
                )
        # --8<-- [end:agent-artifacts]

        # 3. Ingest from the batch the manifest declared `role: load`.
        for envelope in events.envelopes:
            booted.handle.worker.ingest(envelope)

        # 4. The graph view at the temporal boundary this deployment named.
        view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)

        # 5. The operator-parameters mapping, assembled by naming this
        #    deployment's OWN manifest keys — configuration an adopter reads and
        #    edits, deliberately not an isinstance filter or a class-id match.
        parameters = {
            key: cast(Any, booted.artifacts[key])
            for key in ("traversal", "temporal", "policy", "similarity")
        }
        operators = build_operator_registry(
            parameters=parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key="policy-bundle",
            similarity_index_version=governance.declaration[
                "similarity_index_version"
            ],
        )

        # 6. Project (L5). The plan's `required` comes from the product-class
        #    artifact — never from the operator registry's own keys, which would
        #    make Gate 2 compare a value against itself.
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=FieldServicePlan(
                plan_id=governance.declaration["plan_id"],
                required=declared.required_operator_keys,
            ),
            perspective=perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
        )

        # 7. L6 — and this cluster stays in adopter code deliberately.
        #
        #    Gate 3 compares the class's TTL CEILING against this product's own
        #    `expires_at`. That is only a check while the two are independently
        #    authored. Registering the MaxTTL value here is what MINTS
        #    `max_ttl_version` — the pin is a content hash of what was
        #    registered, which is why the product-class artifact cannot declare
        #    it. A helper that minted the pin and stamped the product would be
        #    comparing a value against itself, so the SDK ships no such helper.
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

        # 8. The lineage the product CLAIMS, and the gates. `engine_resolved` is
        #    passed as a separate argument from a second, independent source —
        #    the engine's own resolution — because Gate 2 exists to catch a
        #    producer misdeclaring.
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
                operators_invoked=execution.operators_invoked,
                policy_bundle_versions=frozenset({policy_version}),
                graph_snapshot_at=boundary,
            ),
            payload=execution.projection.payload,
        )
        # A refusal is not a thing to proceed past: `ServableProduct` is not
        # constructible outside `run_gates`, so holding one IS the evidence the
        # gates ran (INV-CH7-52).
        match run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=now,
            registry=registry,
            product_class=product_class,
        ):
            case ServableProduct() as gated:
                pass
            case refusal:
                raise RuntimeError(
                    f"the three validation gates refused this product: {refusal}"
                )

        # --8<-- [start:agent-factory]
        # 9. The Agent Factory: the only construction path (§6.4). It resolves
        #    the definition and both referenced artifacts at pinned versions,
        #    composes the declared archetypes, and validates axis 6 against the
        #    prompt artifact it resolved.
        agent = AgentFactory(control_plane=registry).construct(
            definition_key=definition_key,
            definition_version=definition_version,
        )
        # --8<-- [end:agent-factory]

        # --8<-- [start:specialization-axes]
        # 10. Axis 2 — the context contract admits the served product; axis 3 —
        #     the Π conditioning the definition declares, which is what lands in
        #     replay dimension 4.
        consumed = agent.consume(gated.product, now=now)
        conditioning = agent.perspective_conditioning(
            principal_id=perspective.principal_id,
            grant_set_hash=NO_GRANTS_SET_HASH,
        )
        # --8<-- [end:specialization-axes]

        # 11. Axis 5 made observable: score the declared observations against
        #     the λ_c table at the decision instant and assess D_c under the
        #     agent's OWN referenced debt profile — the CAR routing state
        #     (whitepaper §7.7) is a property of the agent's axis-5 declaration,
        #     not of this file.
        axis5 = cast(
            DeclaredArtifact,
            booted.artifacts[registration.declaration["halflife_debt_profile_key"]],
        )
        profile = cast(
            DebtProfile, parse_artifact(dict(axis5.declaration), DEBT_PROFILE)
        )
        evaluation = cast(
            DeclaredArtifact, booted.artifacts["debt-evaluation"]
        ).declaration
        table = cast(HalfLifeTable, booted.artifacts["half-life-table"])
        assessment = assess_debt(
            DebtFactors(
                freshness=FreshnessScorer(
                    table=table, risk_sensitivity=profile.risk_sensitivity
                ).score(
                    tuple(
                        Observation.model_validate(item)
                        for item in evaluation["observations"]
                    ),
                    now=now,
                ),
                completeness=evaluation["completeness"],
                semantic_consistency=evaluation["semantic_consistency"],
            ),
            profile=profile,
        )

        # 12. The agent's analytic step, over the deterministic seam (D-12).
        analysis = cast(DeclaredArtifact, booted.artifacts["analysis-output"])
        analyst = ScriptedAnalyst(
            model_version=analysis.declaration["model_version"],
            outputs=tuple(analysis.declaration["outputs"]),
        )
        effect = agent.emit_effect(dict(analyst.next_output()))

        # --8<-- [start:agent-replay]
        # 13. Replay before delivery. `agent_conditioning` is what carries the
        #     agent's identity, version and archetype composition into
        #     dimension 4 (D-06); `policy_bindings` is built here from the pins
        #     the adopter reads off `BootedFabric.pins`, because dimension 2
        #     assembled by a rule nobody wrote down is not an audit record.
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
        # --8<-- [end:agent-replay]

        store = FileArtifactStore(root=root / "artifacts")
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=store,
                artifact_class=governance.declaration["replay_record_class"],
            ),
        )

        return AgentBasicsResult(
            tenant_id=booted.tenant_id,
            artifacts=booted.artifacts,
            registry=registry,
            definition=definition,
            definition_version=definition_version,
            agent=agent,
            product=gated.product,
            consumed=consumed,
            operators_invoked=execution.operators_invoked,
            conditioning=conditioning,
            assessment=assessment,
            profile=profile,
            analyst=analyst,
            effect=effect,
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-agent-basics-") as scratch:
        run(root=Path(scratch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
