"""examples/03-harness-portability — one agent, three harnesses (EXAM-04).

The harness-neutrality proof (CLAUDE.md §7.3): ONE agent definition —
``artifacts/agents/order_insights.yaml``, loaded once, producing one
:class:`~ccf.agents.agent.Agent` object — is executed unmodified under all
three D-IMPL-24 reference adapters, in two modes:

* ``--mode deterministic`` (D-01/D-02, the CI leg): **real harness loop
  machinery over scripted/no-model transports** — a real ``ClaudeSDKClient``
  session over a custom ``Transport``, a real ADK ``Runner``, a real
  compiled LangGraph graph. No network, no keys — a guard fails the run if
  anything opens a socket. Equivalence is **byte-level**: the Context
  Product recovered out of each harness-native carrier is byte-identical
  across the three legs, and the governed replay fields (D-18) are exactly
  equal field by field.
* ``--mode live`` (D-03/D-04, opt-in): the same legs against a live model —
  ``--provider ollama`` (keyless local default) or ``--provider anthropic``
  (gated on ``ANTHROPIC_API_KEY``). Equivalence is **structural, never
  byte-equal**: a live model's output varies by construction, so the
  assertions live on what CCF governs — the same Context Product consumed
  (same class, version, lineage identity), five-dimension replay records
  structurally complete (agent version, model version record, skill-set in
  force), and every effect through governed emission.

A missing harness import is a failure, not a skip (mirroring
``CCF_REQUIRE_HARNESSES=1``). Every domain and deployment value is loaded
from ``artifacts/*.yaml`` (§6.4). Run it: ``make example-03``,
``make example-03-live-ollama``, ``make example-03-live-anthropic``.
"""

from __future__ import annotations

import argparse
import socket
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

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
    DecisionReplayRecord,
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


class DecisionBundle(NamedTuple):
    """Everything both drive modes share: the fabric's one governed decision.

    Built once per run by :func:`_decision`: the booted fabric, the gated and
    consumed Context Product, the ONE factory-constructed agent, the pinned
    rendered instructions, and the record builder every leg's replay record
    goes through. The two modes differ only in how the seam-4 execution is
    produced — scripted (D-02) or live (D-03) — never in the fabric side.
    """

    tenant_id: str
    definition: AgentDefinition
    agent: Agent
    consumed: ContextProductContract
    instructions: tuple[str, ...]
    harnesses: Mapping[str, Mapping[str, Any]]
    build_record: Callable[
        [ContextProductContract, HarnessTrace], DecisionReplayRecord
    ]


@contextmanager
def _decision() -> Iterator[DecisionBundle]:
    """Boot the full L1→L6 fabric from artifacts and yield the shared bundle."""
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
            # --8<-- [start:harness-agent]
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
            # --8<-- [end:harness-agent]

            # --8<-- [start:harness-replay-hook]
            def build_record(
                recovered: ContextProductContract, trace: HarnessTrace
            ) -> DecisionReplayRecord:
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

            # --8<-- [end:harness-replay-hook]
            yield DecisionBundle(
                tenant_id=tenant_id,
                definition=definition,
                agent=agent,
                consumed=consumed,
                instructions=instructions,
                harnesses=harnesses,
                build_record=build_record,
            )
        finally:
            handle.close()


def _deterministic() -> int:
    # Imported here so `--mode live` never requires the deterministic
    # scripted transports (a missing harness anywhere is a failure by
    # design, mirroring CCF_REQUIRE_HARNESSES — both legs modules import all
    # three SDKs unconditionally).
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

    with _decision() as bundle:
        # --- one agent, three harnesses, real loop machinery ----------------
        # --8<-- [start:harness-legs]
        legs = build_legs(bundle.harnesses)
        assert len({leg.harness_id for leg in legs}) == 3
        runs: tuple[LegRun, ...] = tuple(
            drive_leg(
                leg,
                agent=bundle.agent,
                product=bundle.consumed,
                instructions=bundle.instructions,
                build_record=bundle.build_record,
            )
            for leg in legs
        )

        # The consumed product is byte-identical across the three legs —
        # and identical to what the fabric admitted, unaltered (D-02).
        delivered = {run.harness_id: run.product_bytes for run in runs}
        assert len(set(delivered.values())) == 1, {
            name: len(value) for name, value in delivered.items()
        }
        assert set(delivered.values()) == {canonical_bytes(bundle.consumed)}
        # --8<-- [end:harness-legs]

        # --8<-- [start:harness-governed-fields]
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
        # --8<-- [end:harness-governed-fields]

        print("examples/03-harness-portability: OK (deterministic)")
        print(f"  tenant                {bundle.tenant_id}")
        print(f"  agent                 {bundle.definition.name}")
        print(
            f"  agent definition hash {content_hash(bundle.definition)[:16]}…"
        )
        print(f"  legs                  {[run.harness_id for run in runs]}")
        print(
            f"  product bytes         {len(runs[0].product_bytes)}"
            " (identical ×3)"
        )
        print(
            "  governed fields       "
            f"{len(expected_fields)} exactly equal ×3"
        )
        print(
            "  harness traces        3 distinct: "
            + ", ".join(run.trace.model_version for run in runs)
        )
        return 0


def _live(provider_name: str) -> int:
    """The live legs (plan 08-11, D-03/D-04): same fabric, a live model.

    Runner safeguards (review consensus concern 2): every provider call is
    bounded by the per-call timeout from ``CCF_LIVE_TIMEOUT_SECONDS`` /
    ``artifacts/live.yaml``, the whole run by ``runner.budget_seconds``. An
    unreachable provider, an absent key, or a breached budget exits 2 with
    an actionable diagnostic; a failed CCF assertion still fails loudly.
    """
    import asyncio

    import httpx
    from claude_agent_sdk import CLIConnectionError, ProcessError

    from legs.deterministic import dimension_count
    from legs.live import (
        LiveBudget,
        LiveBudgetExceeded,
        ProviderUnavailable,
        build_live_legs,
        drive_live_leg,
        resolve_provider,
    )

    live_cfg = _load("live.yaml")
    runner_cfg = live_cfg["runner"]
    try:
        provider = resolve_provider(
            provider_name, live=live_cfg, runner=runner_cfg
        )
        budget = LiveBudget(seconds=float(runner_cfg["budget_seconds"]))
        with _decision() as bundle:
            legs = build_live_legs(
                harnesses=bundle.harnesses,
                provider=provider,
                runner=runner_cfg,
                budget=budget,
            )
            assert len({leg.harness_id for leg in legs}) == 3
            runs = tuple(
                drive_live_leg(
                    leg,
                    agent=bundle.agent,
                    product=bundle.consumed,
                    instructions=bundle.instructions,
                    build_record=bundle.build_record,
                )
                for leg in legs
            )
    except (ProviderUnavailable, LiveBudgetExceeded) as refusal:
        print(f"examples/03-harness-portability: {refusal}", file=sys.stderr)
        return 2
    except (httpx.HTTPError, asyncio.TimeoutError) as failure:
        print(
            "examples/03-harness-portability: live provider"
            f" {provider_name!r} unreachable or timed out"
            f" ({type(failure).__name__}: {failure}) — start the provider"
            " (e.g. `ollama serve`), point CCF_OLLAMA_BASE_URL at it, or"
            " raise CCF_LIVE_TIMEOUT_SECONDS",
            file=sys.stderr,
        )
        return 2
    except (CLIConnectionError, ProcessError) as failure:
        print(
            "examples/03-harness-portability: the Claude Agent SDK session"
            f" could not complete against provider {provider_name!r}"
            f" ({type(failure).__name__}: {failure})",
            file=sys.stderr,
        )
        return 2

    # --- D-04: structural equivalence, never byte-equality -------------------
    # Same Context Product consumed: same product class, version, and lineage
    # identity — recovered out of each harness's own carrier, not assumed.
    recovered = tuple(
        ContextProductContract.model_validate_json(run.product_bytes)
        for run in runs
    )
    for product in recovered:
        assert product.schema_name == bundle.consumed.schema_name
        assert product.schema_version == bundle.consumed.schema_version
        assert product.tenant_id == bundle.consumed.tenant_id
        assert canonical_bytes(product.lineage) == canonical_bytes(
            bundle.consumed.lineage
        ), "lineage identity diverged under a live leg"

    # Every effect passed through governed emission — one address, whichever
    # harness drove it (the fabric side does not vary with the model).
    assert len({run.emission_address for run in runs}) == 1

    for run in runs:
        # Five typed dimensions, structurally complete (INV-CH7-80).
        assert dimension_count(run.record) == 5, run.harness_id
        # Agent version + skill-set in force populated on dimension 4.
        conditioning = run.record.perspective_conditioning
        assert canonical_bytes(conditioning) == canonical_bytes(
            runs[0].record.perspective_conditioning
        ), "agent conditioning diverged under a live leg"
        # Model version record populated with THIS harness's own live trace.
        assert run.record.model_version.harness_trace == run.trace

    # Three legs, three harnesses, one live model each — traces stay isolated.
    assert len({run.harness_id for run in runs}) == 3

    print(f"examples/03-harness-portability: OK (live, {provider.provider_id})")
    print(f"  tenant                {bundle.tenant_id}")
    print(f"  agent                 {bundle.definition.name}")
    print(f"  provider              {provider.provider_id} ({provider.model})")
    print(f"  legs                  {[run.harness_id for run in runs]}")
    print(
        "  reported models       "
        + ", ".join(run.trace.model_version for run in runs)
    )
    print(
        "  token accounting      "
        + ", ".join(
            f"{run.trace.input_tokens}/{run.trace.output_tokens}"
            for run in runs
        )
    )
    print("  equivalence           structural (D-04): product class,")
    print("                        lineage identity, 5 dimensions, governed")
    print("                        emission — never byte-equal model output")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("deterministic", "live"), required=True
    )
    parser.add_argument("--provider", choices=("ollama", "anthropic"))
    arguments = parser.parse_args()
    if arguments.mode == "live":
        if arguments.provider is None:
            print(
                "examples/03-harness-portability: --mode live requires"
                " --provider ollama|anthropic",
                file=sys.stderr,
            )
            return 2
        return _live(arguments.provider)
    return _deterministic()


if __name__ == "__main__":
    sys.exit(main())
