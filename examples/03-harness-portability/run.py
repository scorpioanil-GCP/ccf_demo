"""examples/03-harness-portability — one agent, three harnesses (EXAM-04).

The harness-neutrality proof (CLAUDE.md §7.3): ONE agent definition —
``artifacts/agents/agent-definition.yaml``, loaded once, producing one
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

**Where the deterministic leg's assertions live.** They are not in this file
any more. ``tests/examples/test_harness_portability_output.py`` holds them,
including the two-harness equivalence assertion this example exists for,
because ``make example-03`` proves a spine *runs* and ``pytest`` proves it is
*correct* (D-09). The live legs keep their assertions here: they are excluded
from ``make ci`` by design, so a runner that could fail them does not exist.

A missing harness import is a failure, not a skip (mirroring
``CCF_REQUIRE_HARNESSES=1``). Every domain and deployment value is loaded
from ``artifacts/*.yaml`` and enumerated by ``artifacts/manifest.yaml``
(§6.4). Run it: ``make example-03``, ``make example-03-live-ollama``,
``make example-03-live-anthropic``.
"""

from __future__ import annotations

import argparse
import socket
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.agents.prompts import render_instruction
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
    declared_artifact_class,
    load_artifact,
)
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
    NO_GRANTS_SET_HASH,
    DecisionReplayRecord,
    HarnessTrace,
    PolicyBinding,
    build_replay_record,
)

EXAMPLE_DIR = Path(__file__).resolve().parent
ARTIFACTS = EXAMPLE_DIR / "artifacts"
MANIFEST = ARTIFACTS / "manifest.yaml"

#: The opt-in live legs' provider and runner configuration. Not a manifest
#: entry: the live legs are excluded from ``make ci``, so the CI leg has no
#: business parsing configuration for a mode it never enters.
LIVE_DOCUMENT = ARTIFACTS / "live.yaml"

sys.path.insert(0, str(EXAMPLE_DIR))


class OrderExperiencePlan:
    """The deployment's Π — deployment code, like every projection.

    It declares which operators its interpretation depends on and interprets
    their output; it cannot tell the engine what ran (L6 lineage gate).

    ``required`` is passed in from ``projection-requirements.yaml`` — **this
    plan's own authored document**, not the product class's (design E2,
    D-IMPL-86 and its correction of 2026-08-05). The product class declares the
    Control Plane *claim*; this document declares what the plan requires. Two
    authored documents, and ``refuse_operator_set_divergence`` in ``decision``
    below refuses when they disagree — which is where drift an author could
    write actually fails.

    Neither is ever read off the operator registry: a plan returning the
    registry's own keys would make the plan agree with whatever happened to be
    registered, which is a different collapse from the one E2 closes and still
    worth refusing to write.
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


@dataclass(frozen=True)
class DecisionBundle:
    """Everything both drive modes share: the fabric's one governed decision.

    Built once per run by :func:`decision`: the parsed artifacts, the gated and
    consumed Context Product, the ONE factory-constructed agent, the pinned
    rendered instructions, and the record builder every leg's replay record
    goes through. The two modes differ only in how the seam-4 execution is
    produced — scripted (D-02) or live (D-03) — never in the fabric side.

    The bundle is what ``tests/examples/test_harness_portability_output.py``
    receives, so the relocated assertions run against the same state the drive
    ran against rather than against a second, re-derived one.
    """

    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    definition: AgentDefinition
    agent: Agent
    product: ContextProductContract
    consumed: ContextProductContract
    operators_invoked: tuple[str, ...]
    instructions: tuple[str, ...]
    harnesses: Mapping[str, Mapping[str, Any]]
    build_record: Callable[
        [ContextProductContract, HarnessTrace], DecisionReplayRecord
    ]


@contextmanager
def decision(*, root: Path) -> Iterator[DecisionBundle]:
    """Boot the full L1→L6 fabric from artifacts and yield the shared bundle."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every fabric artifact in force, `load_and_boot` parses all of
    #    them, registers the `role: register` ones into the SAME registry the
    #    agent's artifacts went into, and boots on the resulting pins.
    booted = load_and_boot(
        MANIFEST,
        registry=registry,
        database_path=str(root / "portability.sqlite3"),
    )
    # --8<-- [end:boot]
    try:
        # Each artifact comes back under its own manifest key, already
        # validated against the class the manifest declared for it.
        events = cast(SignalBatch, booted.artifacts["events"])
        decision_inputs = cast(DeclaredArtifact, booted.artifacts["decision"])
        governance = cast(
            DeclaredArtifact, booted.artifacts["product-governance"]
        )
        harnesses = cast(DeclaredArtifact, booted.artifacts["harnesses"])
        declared = cast(
            ProductClassDeclaration, booted.artifacts["product-class"]
        )
        # E2's other authored operator set: what the PLAN requires, as opposed
        # to what the product class CLAIMS. Two manifest keys, two documents.
        requirements = cast(
            ProjectionRequirements, booted.artifacts["projection-requirements"]
        )
        perspective = cast(
            PerspectiveArtifact, booted.artifacts["perspective"]
        )

        boundary = datetime.fromisoformat(
            decision_inputs.declaration["temporal_boundary"]
        )
        now = datetime.fromisoformat(decision_inputs.declaration["now"])

        # --- the agent's own Control Plane, into the SAME registry ----------
        # This is NOT marshalling: an agent is a declared, versioned Control
        # Plane artifact (§6.1), and putting one in force is an adopter act
        # with an audit consequence. It stays visible for the same reason the
        # MaxTTL registration below does.
        #
        # `register_versioned` rather than `register_typed`, on both SDK-owned
        # classes: it runs the D-05 hash-verified bump check, which is why
        # `ccf.agent-definition` and `ccf.prompt-artifact` are deliberately not
        # manifest-addressable — `load_and_boot`'s path would skip it.
        # --8<-- [start:harness-agent-controlplane]
        agent_registration = cast(
            DeclaredArtifact, booted.artifacts["agent-registration"]
        ).declaration

        for reference in agent_registration["referenced"]:
            artifact_class = declared_artifact_class(reference["class_id"])
            registry.register_typed(
                reference["key"],
                load_artifact(
                    (ARTIFACTS / reference["path"]).read_text(encoding="utf-8"),
                    artifact_class,
                ),
                artifact_class,
            )

        prompt_entry = agent_registration["prompt_artifact"]
        registry.register_versioned(
            prompt_entry["key"],
            load_artifact(
                (ARTIFACTS / prompt_entry["path"]).read_text(encoding="utf-8"),
                PROMPT_ARTIFACT,
            ),
            PROMPT_ARTIFACT,
        )

        definition_entry = agent_registration["agent_definition"]
        definition = cast(
            AgentDefinition,
            load_artifact(
                (ARTIFACTS / definition_entry["path"]).read_text(
                    encoding="utf-8"
                ),
                AGENT_DEFINITION,
            ),
        )
        definition_key = definition_entry["key"]
        definition_version = registry.register_versioned(
            definition_key, definition, AGENT_DEFINITION
        )
        # --8<-- [end:harness-agent-controlplane]

        # --8<-- [start:ingest]
        # 2. Ingest from the batch the manifest declared `role: load`.
        for envelope in events.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:ingest]

        # --8<-- [start:operators]
        # 3. The graph view at the temporal boundary this deployment named.
        view = booted.handle.reader.as_of(
            tenant_id=booted.tenant_id, at=boundary
        )

        # 4. The operator-parameters mapping, assembled by naming this
        #    deployment's OWN manifest keys — configuration an adopter reads
        #    and edits, deliberately not an isinstance filter.
        parameters: Mapping[str, OperatorParametersArtifact] = {
            key: cast(OperatorParametersArtifact, booted.artifacts[key])
            for key in ("traversal", "temporal", "policy", "similarity")
        }

        # 5. The four-category operator chain (L4), from those artifacts.
        operators = build_operator_registry(
            parameters=parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key="policy-bundle",
            similarity_index_version=governance.declaration[
                "similarity_index_version"
            ],
        )
        # --8<-- [end:operators]

        # --8<-- [start:project]
        # 6. Project (L5). The plan reads its identity AND its operator set
        #    from `projection-requirements.yaml` — its own authored document,
        #    never the product class's declaration and never the operator
        #    registry's keys.
        #
        #    The plan is bound to a name so the binder has somewhere to stand:
        #    `refuse_operator_set_divergence` belongs BETWEEN plan construction
        #    and `execute`, and constructing the plan inline as the `plan=`
        #    argument leaves no statement between the two (D-IMPL-86's
        #    correction of 2026-08-05). It refuses when the product class's
        #    claim and the plan's requirements disagree, and it refuses rather
        #    than repairing — only the author of the two documents knows which
        #    one they meant. This is where authorable drift fails; Gate 2 below
        #    is a different check (see step 8).
        plan = OrderExperiencePlan(
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
        # --8<-- [end:project]

        # --8<-- [start:gate]
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

        # 8. The lineage the product CLAIMS, and the gates.
        #
        #    `operators_invoked` is filled from the PRODUCT CLASS's declaration
        #    — the Control Plane claim — and never from `execution`. What Gate 2
        #    then verifies is ASSEMBLY-PATH INTEGRITY: that the product served
        #    was assembled by the path the deployment claimed. The engine is a
        #    faithful transcriber of the plan rather than an independent witness
        #    of it, so this is not two independent sources meeting; drift an
        #    author could write has already failed upstream, at the binder in
        #    step 6.
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
        # --8<-- [end:gate]

        # --- ONE agent object, constructed once, factory-only (§6.4) --------
        # --8<-- [start:harness-agent]
        agent = AgentFactory(control_plane=registry).construct(
            definition_key=definition_key,
            definition_version=definition_version,
        )
        consumed = agent.consume(gated.product, now=now)

        # The pinned instructions, rendered exactly once, by the fabric; every
        # leg receives the same rendered string (T-06-64).
        binding = definition.instruction_bindings[0]
        instructions = (
            render_instruction(
                binding=binding,
                artifact=agent.instruction_artifact(binding.prompt),
                parameter_values={
                    "order_ref": decision_inputs.declaration[
                        "instruction_parameters"
                    ]["order_ref"],
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
            # Dimension 5's product_content_address derives from the product
            # recovered from THIS leg's carrier: an adapter that corrupted what
            # it delivered moves the address and the governed comparison goes
            # red naming the field.
            return build_replay_record(
                execution=execution,
                product=recovered,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(key="policy-bundle", version=policy_version),
                ),
                assembly_mode=declared.assembly_mode,
                recorded_at=now,
                agent_conditioning=conditioning,
                harness_trace=trace,
            )

        # --8<-- [end:harness-replay-hook]
        yield DecisionBundle(
            tenant_id=booted.tenant_id,
            artifacts=booted.artifacts,
            definition=definition,
            agent=agent,
            product=gated.product,
            consumed=consumed,
            operators_invoked=execution.operators_invoked,
            instructions=instructions,
            harnesses=harnesses.declaration,
            build_record=build_record,
        )
    finally:
        booted.handle.close()


@dataclass(frozen=True)
class PortabilityResult:
    """What one deterministic drive produced, for a caller to inspect.

    The drive returns its state rather than checking it here, so that
    ``tests/examples/test_harness_portability_output.py`` can hold the
    assertions — the two-harness equivalence assertion among them — where a
    test runner will actually run them.
    """

    bundle: DecisionBundle
    runs: tuple[Any, ...]


def drive_deterministic(*, root: Path) -> PortabilityResult:
    """Run the three deterministic legs and return what they produced."""
    # Imported here so `--mode live` never requires the deterministic scripted
    # transports (a missing harness anywhere is a failure by design, mirroring
    # CCF_REQUIRE_HARNESSES — both legs modules import all three SDKs
    # unconditionally).
    from legs.deterministic import LegRun, build_legs, drive_leg, install_no_model_guard

    # The guard is scoped to the drive: it patches process-global names, and
    # this function runs inside `pytest` as well as under `make example-03`, so
    # an unscoped patch would refuse egress for every later test in the same
    # process.
    with install_no_model_guard():
        # The guard is only evidence if it fires. A guard that silently failed
        # to install would leave every "no network" claim below unbacked, so
        # the example refuses to proceed rather than reporting a property it
        # did not establish.
        try:
            socket.create_connection(("127.0.0.1", 9))
        except AssertionError:
            pass
        else:  # pragma: no cover - a broken guard is a broken example
            raise RuntimeError("the no-model guard is not installed")

        with decision(root=root) as bundle:
            # --8<-- [start:harness-legs]
            # One agent, one product, three harnesses — the legs differ only in
            # which adapter carries the product and reports the trace.
            legs = build_legs(bundle.harnesses)
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
            # --8<-- [end:harness-legs]
            return PortabilityResult(bundle=bundle, runs=runs)


def _deterministic() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-portability-") as scratch:
        drive_deterministic(root=Path(scratch))
    return 0


def _live(provider_name: str) -> int:
    """The live legs (plan 08-11, D-03/D-04): same fabric, a live model.

    These assertions stay in this file, unlike the deterministic leg's. The
    live legs are excluded from ``make ci`` (D-11/D-12), so relocating them to
    ``pytest`` would move them somewhere nothing runs them — the opposite of
    D-09's reason for the move.

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

    live_cfg = cast(
        DeclaredArtifact,
        load_artifact(
            LIVE_DOCUMENT.read_text(encoding="utf-8"),
            declared_artifact_class("atlas-commerce.live-runner"),
        ),
    ).declaration
    runner_cfg = live_cfg["runner"]
    with tempfile.TemporaryDirectory(prefix="ccf-portability-live-") as scratch:
        try:
            provider = resolve_provider(
                provider_name, live=live_cfg, runner=runner_cfg
            )
            budget = LiveBudget(seconds=float(runner_cfg["budget_seconds"]))
            with decision(root=Path(scratch)) as bundle:
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
    print(f"  agent definition hash {content_hash(bundle.definition)[:16]}…")
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
