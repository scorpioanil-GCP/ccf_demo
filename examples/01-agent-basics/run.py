"""examples/01-agent-basics — archetype/agent separation, six axes (EXAM-02).

Declare an agent from the ``AnalyticsInsightsAgent`` archetype via a
definition artifact, construct it through the Agent Factory — the only
supported construction path (CLAUDE.md §6.4) — and run it against a small
field-service fabric's served Context Product, keyless and model-free
(D-12) on SQLite and the file-backed ArtifactStore (D-13).

What this demonstrates, as assertions:

* **Archetype vs agent (§6.1).** The archetype (``analytics_insights``) is
  SDK mechanism; the agent (``response-time-analytics``) is a declared,
  versioned Control Plane artifact in ``artifacts/agent.yaml``. No agent
  exists in code anywhere in this directory.
* **All six specialization axes (§6.2 channel 1)** resolve from the
  definition artifact: archetype binding, context contract, perspective,
  policy regime ref, half-life/debt profile ref, instruction bindings.
* **Factory-only construction.** ``AgentFactory.construct`` resolves every
  referenced artifact through Control Plane resolution at pinned versions;
  nothing here instantiates ``Agent`` directly.
* **Replay dimension 4 (D-06).** The agent's identity — definition content
  hash, versioned URI, archetype composition — lands in the served
  decision's replay record and survives a store round trip.

Every domain value is loaded from ``artifacts/*.yaml``; the deterministic
analyst stub below is mechanism whose canned output content is artifact
data (D-12). Run it: ``make example-01``. Exit 0 means every assertion
held.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.factory import AgentFactory
from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    DebtProfile,
    HalfLifeTable,
    declared_artifact_class,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtFactors, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.llm import LLMClientProtocol
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    PolicyFilter,
    PolicyFilterParameters,
    SimilaritySelect,
    SimilaritySelectParameters,
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    NO_GRANTS_SET_HASH,
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38). Attaching UTC at the
    # artifact boundary is the loader's job; the fabric never guesses.
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    return EntityResolutionSpec(
        semver=ontology["artifact_version"],
        entity_rules=tuple(
            EntityResolutionRule(
                match_key=rule["match_key"],
                entity_class=rule["entity_class"],
                identity_keys=tuple(rule["identity_keys"]),
                attribute_keys=tuple(rule.get("attribute_keys", ())),
            )
            for rule in ontology["entity_rules"]
        ),
        relationship_rules=tuple(
            RelationshipResolutionRule(
                relationship_type=rule["relationship_type"],
                subject_entity_class=rule["subject_entity_class"],
                object_entity_class=rule["object_entity_class"],
            )
            for rule in ontology["relationship_rules"]
        ),
    )


def _envelopes(ontology: Any, events: Any) -> tuple[SignalEnvelope, ...]:
    return tuple(
        SignalEnvelope(
            tenant_id=ontology["tenant_id"],
            envelope_id=item["envelope_id"],
            source=SourceIdentity(system_id=item["source_system_id"]),
            ingestion_timestamp=_instant(item["ingestion_timestamp"]),
            observed_time=_instant(item["observed_time"]),
            raw_payload=dict(item["payload"]),
        )
        for item in events["envelopes"]
    )


class FieldServicePlan:
    # The deployment's Π — deployment code, like every projection. It
    # declares which operators its interpretation depends on and interprets
    # their output; it cannot tell the engine what ran (L6 lineage gate).

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
    # The injected deterministic LLM seam (D-12): a scripted
    # `LLMClientProtocol` stub. The class is mechanism only — the model
    # identifier and every output record are artifact data
    # (artifacts/analysis_output.yaml), never string literals here.

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


def main() -> int:
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    prompt_doc = _load("prompt.yaml")
    agent_doc = _load("agent.yaml")
    analysis = _load("analysis_output.yaml")
    halflife = _load("halflife.yaml")

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])

    with tempfile.TemporaryDirectory(prefix="ccf-agent-basics-") as scratch:
        root = Path(scratch)

        # --- Control Plane: fabric artifacts + the agent's artifacts --------
        registry = ControlPlaneRegistry()
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
        )

        # --8<-- [start:agent-artifacts]
        # Axis-6 target: the prompt artifact, registered typed (D-13).
        prompt = parse_artifact(prompt_doc["prompt_artifact"], PROMPT_ARTIFACT)
        assert isinstance(prompt, PromptArtifact)
        registry.register_typed(
            prompt_doc["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
        )

        # Axis-4/axis-5 targets: the declared artifacts the definition
        # references by versioned URI, registered under their declared keys.
        for reference in agent_doc["referenced_artifacts"].values():
            artifact_class = declared_artifact_class(reference["class_id"])
            declared = parse_artifact(
                {
                    "class_id": reference["class_id"],
                    "semver": reference["semver"],
                    "declaration": reference["declaration"],
                },
                artifact_class,
            )
            registry.register_typed(reference["key"], declared, artifact_class)

        # The agent definition itself: a versioned Control Plane artifact.
        definition = parse_artifact(agent_doc["agent_definition"], AGENT_DEFINITION)
        assert isinstance(definition, AgentDefinition)
        definition_key = agent_doc["keys"]["agent_definition"]
        definition_version = registry.register_versioned(
            definition_key, definition, AGENT_DEFINITION
        )
        assert isinstance(definition_version, str)
        # --8<-- [end:agent-artifacts]

        # --- boot the fabric (SQLite) and ingest via L1 ---------------------
        handle = boot(
            database_path=root / "agent-basics.sqlite3",
            registry=registry,
            resolution_spec_key=keys["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=keys["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        try:
            for envelope in _envelopes(ontology, events):
                handle.worker.ingest(envelope)

            # --- L4/L5: the four-category operator chain, from artifacts ----
            params = control["operator_parameters"]
            operators = OperatorRegistry()
            operators.register(
                PolicyFilter(
                    parameters=PolicyFilterParameters(
                        permitted_policy_bundle_versions=frozenset(
                            {policy_version}
                        ),
                        classification_attribute_by_class=dict(
                            ontology["classification_attribute_by_class"]
                        ),
                        permitted_classifications=frozenset(
                            params["policy"]["permitted_classifications"]
                        ),
                    )
                )
            )
            corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
            view = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
            corpus = {
                (tenant_id, record.claim.entity_uri): record.claim.attributes[
                    corpus_attribute[record.claim.entity_class]
                ]
                for record in view.entities
                if record.claim.entity_class in corpus_attribute
            }
            operators.register(
                SimilaritySelect(
                    parameters=SimilaritySelectParameters(
                        query=params["similarity"]["query"],
                        minimum_score_percent=params["similarity"][
                            "minimum_score_percent"
                        ],
                        ranked_entity_classes=frozenset(
                            params["similarity"]["ranked_entity_classes"]
                        ),
                    ),
                    index=TokenOverlapIndex(
                        corpus=corpus,
                        index_version=params["similarity"]["index_version"],
                    ),
                )
            )
            operators.register(
                TemporalAsOf(
                    parameters=TemporalAsOfParameters(
                        require_valid_at_boundary=params["temporal"][
                            "require_valid_at_boundary"
                        ]
                    )
                )
            )
            operators.register(
                TraversalNeighborhood(
                    parameters=TraversalNeighborhoodParameters(
                        seed_entity_classes=frozenset(
                            params["traversal"]["seed_entity_classes"]
                        ),
                        relationship_types=frozenset(
                            params["traversal"]["relationship_types"]
                        ),
                        depth_limit=params["traversal"]["depth_limit"],
                    )
                )
            )

            declared_class = control["product_class"]
            plan = FieldServicePlan(
                plan_id=declared_class["plan_id"], required=operators.keys()
            )
            perspective = Perspective(
                principal_id=control["perspective"]["principal_id"],
                role=control["perspective"]["role"],
            )
            engine = ProjectionEngine(reader=handle.reader, registry=operators)
            execution = engine.execute(
                plan=plan,
                perspective=perspective,
                tenant_id=tenant_id,
                temporal_boundary=boundary,
            )

            # --- L6: gates, then a servable product -------------------------
            max_ttl_version = registry.register(
                keys["max_ttl"], MaxTTL(seconds=control["max_ttl_seconds"])
            )
            product_class = register_product_class(
                registry=registry,
                schema_name=declared_class["schema_name"],
                schema_version=declared_class["schema_version"],
                ttl_anchor=declared_class["ttl_anchor"],
                assembly_mode=declared_class["assembly_mode"],
                max_ttl_key=keys["max_ttl"],
                max_ttl_version=max_ttl_version,
            )
            candidate = ContextProductContract(
                schema_name=product_class.schema_name,
                schema_version=product_class.schema_version,
                plan_id=execution.plan_id,
                tenant_id=tenant_id,
                temporal_boundary=boundary,
                expires_at=now
                + timedelta(seconds=declared_class["product_ttl_seconds"]),
                ttl_anchor=product_class.ttl_anchor,
                lineage=ProductLineage(
                    operators_invoked=execution.operators_invoked,
                    policy_bundle_versions=frozenset({policy_version}),
                    graph_snapshot_at=boundary,
                ),
                payload=execution.projection.payload,
            )
            gated = run_gates(
                candidate,
                engine_resolved=execution.operators_invoked,
                now=now,
                registry=registry,
                product_class=product_class,
            )
            assert isinstance(gated, ServableProduct), gated
            expected = control["expected"]
            payload = gated.product.payload
            assert payload["entity_count"] == expected["entity_count"], payload
            assert sorted(
                {entry["entity_class"] for entry in payload["entities"]}
            ) == sorted(expected["entity_classes"]), payload
            # axis 3 witness: the served payload's conditioning role is the
            # definition's declared Π role — rebinding the perspective
            # changes this served field.
            assert (
                payload["role"]
                == expected["role"]
                == definition.perspective.role
            ), payload
            # axis 4 witness: the regime-excluded entity class appears
            # nowhere in the served view — exclusion is asserted by name.
            assert not (
                {entry["entity_class"] for entry in payload["entities"]}
                & set(expected["excluded_entity_classes"])
            ), payload

            # --8<-- [start:agent-factory]
            # --- the Agent Factory: the only construction path (§6.4) -------
            agent = AgentFactory(control_plane=registry).construct(
                definition_key=definition_key,
                definition_version=definition_version,
            )
            assert isinstance(agent, Agent)

            # Archetype/agent separation (§6.1): identity derives from the
            # definition artifact, never from anything in code.
            assert agent.identity.definition_hash == content_hash(definition)
            assert agent.identity.definition_uri == (
                f"ccf-artifact://{definition.tenant}/"
                f"{AGENT_DEFINITION.class_id}/{definition.name}"
                f"@{definition.artifact_version}"
            )
            # --8<-- [end:agent-factory]

            # --8<-- [start:specialization-axes]
            # --- all six specialization axes resolve (§6.2 channel 1) -------
            # axis 1 — archetype binding, in declaration order (D-IMPL-19)
            declared_archetypes = tuple(
                agent_doc["agent_definition"]["archetypes"]
            )
            assert agent.identity.archetype_composition == declared_archetypes
            assert (
                tuple(c.archetype_id for c in agent.components)
                == declared_archetypes
            )
            # axis 2 — context contract: the served product is admitted
            consumed = agent.consume(gated.product, now=now)
            assert consumed is gated.product
            # axis 2 witness: the consumed product's class is exactly the
            # class the definition's context contract declares.
            contract = agent_doc["agent_definition"]["context_contract"][
                "consumes"
            ][0]
            assert gated.product.schema_name == contract["product_class"]
            assert gated.product.schema_version == contract["schema_version"]
            # axis 3 — perspective: the Π role from the definition
            conditioning = agent.perspective_conditioning(
                principal_id=perspective.principal_id,
                grant_set_hash=NO_GRANTS_SET_HASH,
            )
            assert conditioning.role == definition.perspective.role
            # axes 4 & 5 — policy regime and half-life/debt profile refs
            # resolved through the Control Plane at pinned versions: the
            # factory refuses an unresolvable ref, and each declared key is
            # registered with at least one version.
            for reference in agent_doc["referenced_artifacts"].values():
                assert registry.versions(reference["key"]), reference["key"]
            assert definition.policy_regime.ref.endswith(
                "@" + agent_doc["referenced_artifacts"]["policy_regime"]["semver"]
            )
            assert definition.halflife_debt_profile.ref.endswith(
                "@"
                + agent_doc["referenced_artifacts"]["halflife_debt_profile"][
                    "semver"
                ]
            )
            # axis 6 — instruction bindings: the resolved prompt artifact
            # travels with the agent; parameters match its declaration (D-13)
            binding = definition.instruction_bindings[0]
            resolved = agent.instruction_artifact(binding.prompt)
            assert isinstance(resolved, PromptArtifact)
            assert frozenset(resolved.declared_parameters) == frozenset(
                binding.parameters
            )
            # --8<-- [end:specialization-axes]

            # --- axis 5 made observable: the debt profile gates (§7.7) ------
            # axis 5 witness: the definition's referenced debt profile is
            # parsed typed from its declaration, minus deployment-only keys.
            axis5 = agent_doc["referenced_artifacts"]["halflife_debt_profile"]
            profile = parse_artifact(
                {
                    "semver": axis5["semver"],
                    **{
                        name: axis5["declaration"][name]
                        for name in DebtProfile.model_fields
                        if name in axis5["declaration"]
                    },
                },
                DEBT_PROFILE,
            )
            assert isinstance(profile, DebtProfile)
            table = parse_artifact(
                halflife["half_life_table"], HALF_LIFE_TABLE
            )
            assert isinstance(table, HalfLifeTable)
            evaluation = halflife["debt_evaluation"]
            scorer = FreshnessScorer(
                table=table, risk_sensitivity=profile.risk_sensitivity
            )
            factors = DebtFactors(
                freshness=scorer.score(
                    tuple(
                        Observation(
                            observation_type=item["observation_type"],
                            observed_at=_instant(item["observed_at"]),
                        )
                        for item in evaluation["observations"]
                    ),
                    now=now,
                ),
                completeness=evaluation["completeness"],
                semantic_consistency=evaluation["semantic_consistency"],
            )
            assessment = assess_debt(factors, profile=profile)
            # axis 5 witness: the CAR routing state the assessed D_c lands
            # in matches the reviewed expectation the artifacts declare.
            assert (
                assessment.signal.value == evaluation["expected_signal"]
            ), assessment
            assert assessment.debt > profile.forced_llm_threshold, assessment
            assert assessment.debt <= profile.fail_closed_threshold, assessment

            # --- run the agent's analytic step (D-12, keyless) --------------
            analyst = ScriptedAnalyst(
                model_version=analysis["model_version"],
                outputs=tuple(analysis["outputs"]),
            )
            assert isinstance(analyst, LLMClientProtocol)
            effect = agent.emit_effect(dict(analyst.next_output()))
            assert isinstance(effect, EmittedEffect)
            assert effect.agent_definition_hash == agent.identity.definition_hash
            assert effect.payload == analysis["outputs"][0]

            # --- replay: agent identity/version in dimension 4 (D-06) -------
            record = build_replay_record(
                execution=execution,
                product=gated.product,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(
                        key=keys["policy_bundle"], version=policy_version
                    ),
                ),
                assembly_mode=declared_class["assembly_mode"],
                recorded_at=now,
                agent_conditioning=conditioning,
            )
            store = FileArtifactStore(root=root / "artifacts")
            served = serve(
                product=gated,
                record=record,
                replay_writer=ReplayWriter(
                    store=store,
                    artifact_class=control["artifacts"]["replay_record_class"],
                ),
            )
            restored = DecisionReplayRecord.model_validate_json(
                store.get(content_address=served.replay_ref.content_address)
            )
            assert restored == record
            # --8<-- [start:agent-replay]
            dimension_four = restored.perspective_conditioning
            assert dimension_four.agent_definition_hash == content_hash(
                definition
            )
            assert dimension_four.agent_definition_uri == (
                agent.identity.definition_uri
            )
            assert dimension_four.agent_definition_uri.endswith(
                "@" + definition.artifact_version
            )
            assert dimension_four.archetype_composition == declared_archetypes
            assert dimension_four.grant_set_hash == NO_GRANTS_SET_HASH
            assert dimension_four.delegation_chain == (
                perspective.principal_id,
            )
            # --8<-- [end:agent-replay]

            print("examples/01-agent-basics: OK")
            print(f"  tenant                 {tenant_id}")
            print(f"  agent                  {definition.name}")
            print(f"  agent version          {definition.artifact_version}")
            print(f"  archetypes             {list(declared_archetypes)}")
            print(f"  consumed product       {gated.product.schema_name}")
            print(f"  context debt D_c       {assessment.debt}")
            print(f"  debt signal (axis 5)   {assessment.signal.value}")
            print(
                "  dim-4 definition hash  "
                f"{dimension_four.agent_definition_hash[:16]}…"
            )
            return 0
        finally:
            handle.close()


if __name__ == "__main__":
    sys.exit(main())
