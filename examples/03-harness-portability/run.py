"""examples/03-harness-portability — one agent, three harnesses (EXAM-04).

The harness-neutrality proof (CLAUDE.md §7.3): ONE agent definition —
``artifacts/agents/order_insights.yaml``, loaded once, producing one
:class:`~ccf.agents.agent.Agent` object — is executed unmodified under all
three D-IMPL-24 reference adapters, on **real harness loop machinery over
scripted/no-model transports** (D-01/D-02): a real ``ClaudeSDKClient``
session over a custom ``Transport``, a real ADK ``Runner``, a real compiled
LangGraph graph. No network, no keys — a guard fails the run if anything
opens a socket.

What this demonstrates, as assertions:

* **Byte-level equivalence (D-02).** The Context Product each harness
  consumed — recovered out of each harness-native carrier, not assumed —
  is byte-identical across the three legs, and equal to what the fabric
  admitted. The governed replay fields (D-18) are exactly equal, field by
  field.
* **Harness attribution stays isolated.** Each leg's ``harness_trace``
  names its own harness, carries the model and trace id that harness's own
  run reported, and differs per harness — a governed field that diverged
  or a trace that collapsed would both fail loudly.
* **Advisory A3, example-side.** The Claude leg's seam-4 input is a
  ``ResultMessage`` the real SDK session constructed over the scripted
  wire — not a hand-built one.
* **Five dimensions, live.** Every leg's replay record carries exactly the
  five typed dimensions (INV-CH7-80).

A missing harness import is a failure, not a skip (mirroring
``CCF_REQUIRE_HARNESSES=1``). Every domain and deployment value is loaded
from ``artifacts/*.yaml`` (§6.4). Run it: ``make example-03``. The live
legs (``--mode live``) land in plan 08-11; the flag surface is stable now.
"""

from __future__ import annotations

import argparse
import socket
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.factory import AgentFactory
from ccf.agents.prompts import render_instruction
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
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
    HarnessTrace,
    PolicyBinding,
    build_replay_record,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex

EXAMPLE_DIR = Path(__file__).resolve().parent
ARTIFACTS = EXAMPLE_DIR / "artifacts"

sys.path.insert(0, str(EXAMPLE_DIR))


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


class OrderExperiencePlan:
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


def _deterministic() -> int:
    # Imported here so `--mode live` never requires the harness SDKs the
    # deterministic legs import unconditionally (a missing harness there is
    # a failure by design, mirroring CCF_REQUIRE_HARNESSES).
    from legs.deterministic import (
        LegRun,
        build_legs,
        dimension_count,
        drive_leg,
        governed_fields,
        install_no_model_guard,
    )

    install_no_model_guard()
    # The guard is only evidence if it fires.
    try:
        socket.create_connection(("127.0.0.1", 9))
    except AssertionError:
        pass
    else:  # pragma: no cover - a broken guard is a broken example
        raise AssertionError("the no-model guard is not installed")

    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    prompt_doc = _load("prompt.yaml")
    harnesses = _load("harnesses.yaml")

    # Exactly ONE agent definition artifact is shared by all legs (D-01).
    agent_files = sorted((ARTIFACTS / "agents").glob("*.yaml"))
    assert len(agent_files) == 1, agent_files
    agent_doc = yaml.safe_load(agent_files[0].read_text(encoding="utf-8"))

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])

    with tempfile.TemporaryDirectory(prefix="ccf-portability-") as scratch:
        root = Path(scratch)

        # --- Control Plane: fabric artifacts + the agent's artifacts --------
        registry = ControlPlaneRegistry()
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
        )
        prompt = parse_artifact(prompt_doc["prompt_artifact"], PROMPT_ARTIFACT)
        assert isinstance(prompt, PromptArtifact)
        registry.register_typed(
            prompt_doc["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
        )
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

        definition = parse_artifact(agent_doc["agent_definition"], AGENT_DEFINITION)
        assert isinstance(definition, AgentDefinition)
        definition_key = agent_doc["keys"]["agent_definition"]
        definition_version = registry.register_versioned(
            definition_key, definition, AGENT_DEFINITION
        )
        assert isinstance(definition_version, str)

        # --- boot the fabric (SQLite) and ingest via L1 ---------------------
        handle = boot(
            database_path=root / "portability.sqlite3",
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
            plan = OrderExperiencePlan(
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

            # --- ONE agent object, constructed once, factory-only (§6.4) ----
            agent = AgentFactory(control_plane=registry).construct(
                definition_key=definition_key,
                definition_version=definition_version,
            )
            assert isinstance(agent, Agent)
            consumed = agent.consume(gated.product, now=now)

            # The pinned instructions, rendered exactly once, by the fabric;
            # every leg receives the same rendered string (T-06-64).
            binding = definition.instruction_bindings[0]
            instructions = (
                render_instruction(
                    binding=binding,
                    artifact=agent.instruction_artifact(binding.prompt),
                    parameter_values={
                        "order_ref": control["instruction_parameters"][
                            "order_ref"
                        ],
                        "as_of": boundary.isoformat(),
                    },
                ),
            )

            conditioning = agent.perspective_conditioning(
                principal_id=perspective.principal_id,
                grant_set_hash=NO_GRANTS_SET_HASH,
            )

            def build_record(
                recovered: ContextProductContract, trace: HarnessTrace
            ) -> Any:
                # Dimension 5's product_content_address derives from the
                # product recovered from THIS leg's carrier: an adapter that
                # corrupted what it delivered moves the address and the
                # governed comparison goes red naming the field.
                return build_replay_record(
                    execution=execution,
                    product=recovered,
                    perspective=perspective,
                    policy_bindings=(
                        PolicyBinding(
                            key=keys["policy_bundle"], version=policy_version
                        ),
                    ),
                    assembly_mode=declared_class["assembly_mode"],
                    recorded_at=now,
                    agent_conditioning=conditioning,
                    harness_trace=trace,
                )

            # --- one agent, three harnesses, real loop machinery ------------
            legs = build_legs(harnesses)
            assert len({leg.harness_id for leg in legs}) == 3
            runs: tuple[LegRun, ...] = tuple(
                drive_leg(
                    leg,
                    agent=agent,
                    product=consumed,
                    instructions=instructions,
                    build_record=build_record,
                )
                for leg in legs
            )

            # The consumed product is byte-identical across the three legs —
            # and identical to what the fabric admitted, unaltered (D-02).
            delivered = {run.harness_id: run.product_bytes for run in runs}
            assert len(set(delivered.values())) == 1, {
                name: len(value) for name, value in delivered.items()
            }
            assert set(delivered.values()) == {canonical_bytes(consumed)}

            # The governed emission is one effect, whichever harness drove it.
            assert len({run.emission_address for run in runs}) == 1

            # Governed replay fields exactly equal, field by field (D-18).
            reference, *others = runs
            expected_fields = governed_fields(reference.record)
            for run in others:
                actual = governed_fields(run.record)
                assert set(actual) == set(expected_fields)
                for name in sorted(expected_fields):
                    assert actual[name] == expected_fields[name], (
                        f"governed replay field {name!r} diverged between"
                        f" {reference.harness_id} and {run.harness_id}"
                    )

            # Harness attribution stays isolated — and differs per harness.
            assert (
                len({canonical_bytes(run.trace) for run in runs}) == 3
            ), "the three harness traces collapsed"
            for run in runs:
                assert "harness_trace" not in governed_fields(run.record)

            # Each record is structurally complete: five dimensions, live.
            for run in runs:
                assert dimension_count(run.record) == 5, run.harness_id

            print("examples/03-harness-portability: OK (deterministic)")
            print(f"  tenant                {tenant_id}")
            print(f"  agent                 {definition.name}")
            print(f"  agent definition hash {content_hash(definition)[:16]}…")
            print(f"  legs                  {[run.harness_id for run in runs]}")
            print(f"  product bytes         {len(runs[0].product_bytes)} (identical ×3)")
            print(
                "  governed fields       "
                f"{len(expected_fields)} exactly equal ×3"
            )
            print(
                "  harness traces        3 distinct: "
                + ", ".join(run.trace.model_version for run in runs)
            )
            return 0
        finally:
            handle.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("deterministic", "live"), required=True
    )
    parser.add_argument("--provider", choices=("ollama", "anthropic"))
    arguments = parser.parse_args()
    if arguments.mode == "live":
        print(
            "examples/03-harness-portability: live legs land in plan 08-11",
            file=sys.stderr,
        )
        return 2
    return _deterministic()


if __name__ == "__main__":
    sys.exit(main())
