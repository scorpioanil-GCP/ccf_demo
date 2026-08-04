"""examples/02-skilling — governed skilling, channel 2 (EXAM-03).

Grant a skill to a running agent through the Control Plane, exercise it,
and revoke it — with the governance compatibility check refusing an
impermissible grant, every transition audited, and the skill-set in force
captured in the Decision Replay record. Clinical-trials-operations domain,
keyless and model-free (D-12) on SQLite and the file-backed ArtifactStore.

What this demonstrates, as assertions (CLAUDE.md §6.2):

* **The agent definition never changes.** Skilling is the capability
  channel; ``artifacts/agent.yaml`` is byte-identical before and after the
  whole grant/exercise/revoke cycle, and the definition's content hash —
  the agent's identity — never moves.
* **Tier-1 governance is structural and non-waivable.** A grant whose
  declared requirements exceed the agent's policy regime is refused with a
  typed returned value naming the excess scopes; nothing binds.
* **Every grant and revocation is audited** on the one Control Plane audit
  log (grant_requested, grant_effective, grant_refused, grant_revoked).
* **Replay captures the skill-set in force** (D-07): the record built at
  the exercise step carries the in-force grant-set hash in dimension 4 —
  a decision replays against the skills the agent actually had.

Every domain value — scopes, skill entries, grants, expected outputs — is
loaded from ``artifacts/*.yaml`` (§6.4). Run it: ``make example-02``.
Exit 0 means every assertion held, including the governance refusal.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.agents.agent import Agent
from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.agents.errors import SkillNotBound
from ccf.agents.factory import AgentFactory
from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    PolicyFilter,
    PolicyFilterParameters,
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
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.dispatch import SkillInvocation
from ccf.skills.grants import (
    ApprovalOutcome,
    GrantRefusal,
    GrantLedger,
    RequirementsExceedRegime,
    SkillGrant,
    grant_set_hash,
)

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38).
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


class TrialOpsPlan:
    # The deployment's Π — deployment code, like every projection.

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
    # ApprovalSink conformance for a deployment whose regime declares
    # `grant_requires_approval: false`: tier 2 must never be consulted, and
    # a consultation is a hard failure rather than a silent approval.

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError(
            "tier-2 sink consulted under an auto regime (D-IMPL-29)"
        )


def _bind_callable(record: Mapping[str, Any]) -> Any:
    # Composition-root callable factory (D-19): mechanism only — the output
    # content is artifact data, merged with the typed arguments at invoke
    # time. Deterministic and side-effect free.
    def _invoke(arguments: Mapping[str, str]) -> dict[str, Any]:
        return {**record, **arguments}

    return _invoke


def main() -> int:
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    agent_doc = _load("agent.yaml")
    skills_doc = _load("skills.yaml")

    # The byte-identity baseline: the agent definition artifact as authored,
    # before any channel-2 activity (§6.2 — skilling never re-declares).
    definition_bytes_before = (ARTIFACTS / "agent.yaml").read_bytes()

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])
    actor: str = skills_doc["actors"]["requesting_actor"]

    with tempfile.TemporaryDirectory(prefix="ccf-skilling-") as scratch:
        root = Path(scratch)

        # --- Control Plane: one registry, one audit log, injected clock -----
        audit = AuditLog()
        registry = ControlPlaneRegistry(clock=lambda: now, audit_log=audit)
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
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
        definition_hash = content_hash(definition)

        # --- boot the minimal fabric and serve one product ------------------
        handle = boot(
            database_path=root / "skilling.sqlite3",
            registry=registry,
            resolution_spec_key=keys["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=keys["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        try:
            for envelope in _envelopes(ontology, events):
                handle.worker.ingest(envelope)

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
            plan = TrialOpsPlan(
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
            assert (
                gated.product.payload["entity_count"]
                == expected["entity_count"]
            ), gated.product.payload

            # --8<-- [start:skill-catalog]
            # --- (1) register skills in the Control Plane catalog -----------
            catalog = SkillCatalog(registry)
            for document in skills_doc["skills"].values():
                entry = parse_artifact(document, SKILL_CATALOG_ENTRY)
                assert isinstance(entry, SkillCatalogEntry)
                registered = catalog.register(entry)
                assert isinstance(registered, str)

            ledger = GrantLedger(
                control_plane=registry,
                catalog=catalog,
                sink=UnconsultedSink(),
                clock=lambda: now,
            )

            # The running agent: factory-constructed once, holding the
            # ledger's LIVE bound view — grants and revocations below take
            # effect at invoke time without touching agent identity (D-07).
            callables = CallableRegistry()
            callables.register(
                skills_doc["callable"]["registered_key"],
                _bind_callable(skills_doc["callable"]["output_record"]),
            )
            agent = AgentFactory(
                control_plane=registry, callable_registry=callables
            ).construct(
                definition_key=definition_key,
                definition_version=definition_version,
                bound_skills=ledger.bound_view(definition_hash),
            )
            assert isinstance(agent, Agent)
            assert agent.bound_skill_names == ()
            assert ledger.grant_set_hash(definition_hash) == NO_GRANTS_SET_HASH
            # --8<-- [end:skill-catalog]

            permitted_name = skills_doc["grants"]["permitted"]["skill_name"]
            impermissible_name = skills_doc["grants"]["impermissible"][
                "skill_name"
            ]

            # --8<-- [start:skill-grant]
            # --- (2) grant the permitted skill via the Control Plane --------
            permitted = SkillGrant(
                agent_definition_hash=definition_hash,
                **skills_doc["grants"]["permitted"],
            )
            outcome = ledger.request(permitted, definition=definition, actor=actor)
            assert outcome == content_hash(permitted)
            assert ledger.state(content_hash(permitted)) == "effective"
            grant_actions = [
                event.action
                for event in audit.events()
                if event.action.startswith("grant_")
            ]
            assert grant_actions == ["grant_requested", "grant_effective"]
            in_force = ledger.grant_set_hash(definition_hash)
            assert in_force != NO_GRANTS_SET_HASH
            assert in_force == grant_set_hash(
                frozenset({content_hash(permitted)})
            )
            assert agent.bound_skill_names == (permitted_name,)
            # --8<-- [end:skill-grant]

            # --8<-- [start:skill-exercise]
            # --- (3) exercise it (deterministic local callable, D-19) -------
            consumed = agent.consume(gated.product, now=now)
            assert consumed is gated.product
            invocation = agent.invoke_skill(
                permitted_name, arguments=skills_doc["dispatch"]["arguments"]
            )
            assert isinstance(invocation, SkillInvocation)
            assert dict(invocation.output) == skills_doc["dispatch"][
                "expected_output"
            ]
            # --8<-- [end:skill-exercise]

            # Replay at the exercise step: dimension 4 carries the skill-set
            # in force (D-07) — the decision replays against the skills the
            # agent actually had, not the skills it has later.
            conditioning = agent.perspective_conditioning(
                principal_id=perspective.principal_id,
                grant_set_hash=ledger.grant_set_hash(definition_hash),
            )
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
            assert restored.perspective_conditioning.grant_set_hash == in_force
            assert (
                restored.perspective_conditioning.grant_set_hash
                != NO_GRANTS_SET_HASH
            )
            assert (
                restored.perspective_conditioning.agent_definition_hash
                == definition_hash
            )

            # --8<-- [start:skill-refusal]
            # --- (4) the impermissible grant is refused by governance -------
            impermissible = SkillGrant(
                agent_definition_hash=definition_hash,
                **skills_doc["grants"]["impermissible"],
            )
            refusal = ledger.request(
                impermissible, definition=definition, actor=actor
            )
            assert isinstance(refusal, GrantRefusal), refusal
            assert isinstance(refusal, RequirementsExceedRegime), refusal
            assert refusal.excess_scopes == frozenset(
                skills_doc["expected_excess"]["scopes"]
            )
            assert ledger.state(content_hash(impermissible)) == "refused"
            refused_event = [
                event
                for event in audit.events()
                if event.action.startswith("grant_")
            ][-1]
            assert refused_event.action == "grant_refused"
            assert refused_event.resolved is False
            # Nothing bound: the skill does not exist from the agent's
            # surface, and the in-force set identity did not move.
            assert agent.bound_skill_names == (permitted_name,)
            assert ledger.grant_set_hash(definition_hash) == in_force
            try:
                agent.invoke_skill(impermissible_name)
            except SkillNotBound:
                pass
            else:
                raise AssertionError("impermissible skill was bound")
            # --8<-- [end:skill-refusal]

            # --8<-- [start:skill-revoke]
            # --- (5) revoke the permitted skill ------------------------------
            ledger.revoke(content_hash(permitted), actor=actor)
            assert ledger.state(content_hash(permitted)) == "revoked"
            grant_actions = [
                event.action
                for event in audit.events()
                if event.action.startswith("grant_")
            ]
            assert grant_actions == [
                "grant_requested",
                "grant_effective",
                "grant_requested",
                "grant_refused",
                "grant_revoked",
            ]
            assert ledger.grant_set_hash(definition_hash) == NO_GRANTS_SET_HASH
            # The live bound view: revocation takes effect at invoke time,
            # on the same constructed agent (D-07).
            assert agent.bound_skill_names == ()
            try:
                agent.invoke_skill(permitted_name)
            except SkillNotBound:
                pass
            else:
                raise AssertionError("revoked skill still bound")
            # --8<-- [end:skill-revoke]

            # --- (6) the agent was never re-declared -------------------------
            assert (
                ARTIFACTS / "agent.yaml"
            ).read_bytes() == definition_bytes_before
            assert content_hash(definition) == definition_hash
            assert registry.versions(definition_key) == (definition_version,)

            print("examples/02-skilling: OK")
            print(f"  tenant                 {tenant_id}")
            print(f"  agent                  {definition.name}")
            print(f"  granted+exercised      {permitted_name}")
            print(f"  refused (tier 1)       {impermissible_name}")
            print(f"  excess scopes named    {sorted(refusal.excess_scopes)}")
            print(f"  in-force hash (dim 4)  {in_force[:16]}…")
            print("  definition artifact    byte-identical (never re-declared)")
            return 0
        finally:
            handle.close()


if __name__ == "__main__":
    sys.exit(main())
