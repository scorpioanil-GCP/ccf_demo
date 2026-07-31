"""examples/04-cross-process — the assembler side, in its own OS process.

Run by ``run.py`` as ``python examples/04-cross-process/producer_child.py``,
or standalone with the same command. A separate process is the entire point:
the producer's fabric, its graph file, its Control Plane registry and its
private key live in this heap; the consumer's live in the parent's. "The
consumer holds no write handle to the producer's graph" is therefore
literally true here rather than argued.

What this child does, in order:

1. Boots a property-intelligence fabric from ``artifacts/`` (fresh domain,
   D-07/D-08 — nothing ported), ingests the event stream through L1, runs
   the four-category operator chain, projects, and gates. Only a
   ``ServableProduct`` goes any further.
2. Constructs the ``site-situation-assembler`` agent through the Agent
   Factory — the only supported construction path (CLAUDE.md §6.4) — from
   its definition artifact, and validates the gated product against the
   agent's context contract (§6.3: a ``ContextAssemblyAgent`` whose output
   is itself a typed Context Product).
3. Signs the product as this peer (detached JWS, D-IMPL-15) and, when the
   parent supplied a consumer URL, emits TWO messages over A2A before
   announcing: the genuine signed envelope, and a deliberately broken one
   that splices the genuine signature onto a different payload — so a real
   tampered envelope traverses a real socket for the parent's negative case.
4. Serves the same product over MCP egress (whitepaper §8.3 Pattern 3) and
   hosts this peer's own A2A endpoint, both on ephemeral loopback ports, and
   prints ``READY {mcp_port} {a2a_port}`` only once both servers report
   started. The parent's blocking ``readline()`` is the gate — no sleeps.

Every domain value — tenant, entity classes, operator parameters, peer
identity, endpoint path, ceilings — comes from ``artifacts/*.yaml``. Delete
the artifacts and this file has nothing to assemble, sign, or serve
(CLAUDE.md §6.4). Zero porting from any prior property system (D-07):
every name and value in those artifacts is invented for this example.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

_EXAMPLE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_ROOT.parents[1]

# The child is spawned as a bare `python <file>`, so it cannot rely on a
# relative PYTHONPATH surviving a cwd change. Resolving the roots from
# __file__ is what makes it runnable from anywhere.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import httpx  # noqa: E402
import yaml  # noqa: E402

from ccf.agents.agent import Agent  # noqa: E402
from ccf.agents.definitions import (  # noqa: E402
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.factory import AgentFactory  # noqa: E402
from ccf.assembly.worker import (  # noqa: E402
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot  # noqa: E402
from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.controlplane.artifacts import (  # noqa: E402
    declared_artifact_class,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.graph.protocols import GraphView  # noqa: E402
from ccf.operators.base import OperatorOutput  # noqa: E402
from ccf.operators.categories import (  # noqa: E402
    PolicyFilter,
    PolicyFilterParameters,
    SimilaritySelect,
    SimilaritySelectParameters,
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.peering.admission import PRODUCER_ASSERTION_HEADER  # noqa: E402
from ccf.peering.identity import (  # noqa: E402
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    SignedContextProduct,
)
from ccf.peering.protocol import PeerRef  # noqa: E402
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf.projection.engine import OperatorRegistry, ProjectionEngine  # noqa: E402
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.signal.envelope import SignalEnvelope, SourceIdentity  # noqa: E402
from ccf.similarity.protocol import TokenOverlapIndex  # noqa: E402

from ccf_runtime.mcp.egress import (  # noqa: E402
    ProductNotServable,
    build_egress_server,
    product_uri,
)
from ccf_runtime.peering.typed_http import TypedHttpWire  # noqa: E402

ARTIFACTS = _EXAMPLE_ROOT / "artifacts"

#: Environment variables the parent sets before spawning. Shared vocabulary
#: between this module and ``run.py`` so the two cannot disagree on a name.
#: Both are optional: run standalone (no consumer to emit to), the child
#: still assembles, signs with a throwaway key, and serves both surfaces.
CONSUMER_URL_VAR = "CCF_EXAMPLE04_CONSUMER_URL"
KEY_DIR_VAR = "CCF_EXAMPLE04_KEY_DIR"


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


class SituationPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes. It declares
    which operators its interpretation depends on and interprets their
    output; it does not run them and cannot tell the engine what ran (which
    is what leaves the L6 lineage gate something real to check).
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


class ProductAddress(NamedTuple):
    """The three segments that name a product on the egress surface."""

    tenant: str
    product_class: str
    version: str

    @property
    def uri(self) -> str:
        return product_uri(
            tenant=self.tenant,
            product_class=self.product_class,
            version=self.version,
        )


class AssembledSituation(NamedTuple):
    """The gated product, its egress address, and its serving identity."""

    servable: ServableProduct
    address: ProductAddress
    server_name: str


def build_situation_product(*, database_path: Path) -> AssembledSituation:
    """Run the property-intelligence slice end to end and gate the result.

    The product is assembled, not fabricated: the whole L1->L6 path runs in
    this process, so the cross-process read on the other side is a read of
    *the fabric's* product rather than of a hand-built dict shaped like one.

    Args:
        database_path: Where this process's throwaway graph lives. Supplied
            by the caller so parent and child cannot collide on a file.

    Returns:
        The gated product plus its egress address and server name.
    """
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    agent_doc = _load("agent.yaml")
    prompt_doc = _load("prompt.yaml")

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])

    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
    )

    # The assembler agent's own artifacts: prompt (axis 6), referenced
    # policy-regime and debt-profile artifacts (axes 4/5), the definition.
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

    handle = boot(
        database_path=database_path,
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
                    permitted_policy_bundle_versions=frozenset({policy_version}),
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
        plan = SituationPlan(
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

        # The served view matches what the deployment declared it expects.
        expected = control["expected"]
        payload = gated.product.payload
        assert payload["entity_count"] == expected["entity_count"], payload
        assert sorted(
            {entry["entity_class"] for entry in payload["entities"]}
        ) == sorted(expected["entity_classes"]), payload
        assert payload["relationship_types"] == sorted(
            expected["relationship_types"]
        ), payload

        # The assembler agent: factory-constructed from its definition
        # artifact — the only supported path (§6.4) — and the gated product
        # validates against its context contract before anything is served.
        agent = AgentFactory(control_plane=registry).construct(
            definition_key=definition_key,
            definition_version=definition_version,
        )
        assert isinstance(agent, Agent)
        assert agent.identity.definition_hash == content_hash(definition)
        assert agent.consume(gated.product, now=now) is gated.product
    finally:
        handle.close()

    return AssembledSituation(
        servable=gated,
        address=ProductAddress(
            tenant=tenant_id,
            product_class=product_class.schema_name,
            version=product_class.schema_version,
        ),
        # Deployment identity, taken from the artifact that owns it rather
        # than written here — a server name in code is a domain value in code.
        server_name=declared_class["plan_id"],
    )


def _tampered(
    genuine: SignedContextProduct, other: SignedContextProduct
) -> SignedContextProduct:
    """Splice ``genuine``'s signature onto ``other``'s payload.

    The result is well-formed — both members were produced by the JOSE
    library — and does not verify, which is precisely the shape a consumer
    must refuse. Constructed by recombining two real envelopes rather than by
    editing bytes, so nothing here hand-rolls base64url.
    """
    return SignedContextProduct(
        payload=other.payload,
        protected=genuine.protected,
        signature=genuine.signature,
    )


def _throwaway_key(directory: Path, key_id: str) -> None:
    """Generate a standalone-mode signing key. Never written to the repo."""
    from joserfc.jwk import ECKey  # noqa: PLC0415

    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )


def main() -> None:
    """Assemble, sign, emit (when a consumer is listening), serve, announce."""
    import anyio
    import uvicorn

    federation = _load("a2a.yaml")
    control = _load("controlplane.yaml")
    consumer_values = federation["consumer"]
    producer_values = federation["producer"]
    now = _instant(control["decision"]["now"])

    consumer_url = os.environ.get(CONSUMER_URL_VAR)

    with tempfile.TemporaryDirectory(prefix="ccf-example04-producer-") as scratch:
        workspace = Path(scratch)
        assembled = build_situation_product(
            database_path=workspace / "producer.sqlite3"
        )
        product = assembled.servable.product

        key_dir_value = os.environ.get(KEY_DIR_VAR)
        if key_dir_value is None:
            key_dir = workspace / "keys"
            key_dir.mkdir()
            _throwaway_key(key_dir, producer_values["key_id"])
        else:
            key_dir = Path(key_dir_value)

        provider = DetachedJwsIdentityProvider(
            key_source=FileBackedKeySource(directory=key_dir)
        )
        genuine = provider.sign(
            product=product,
            key_id=producer_values["key_id"],
            assertions={
                PRODUCER_ASSERTION_HEADER: producer_values["producer_hash"]
            },
        )
        # A second, genuinely different product, signed the same way, purely
        # so its payload member exists to be spliced onto the genuine
        # signature for the parent's negative admission case.
        other = provider.sign(
            product=product.model_copy(
                update={"payload": {**product.payload, "entity_count": -1}}
            ),
            key_id=producer_values["key_id"],
            assertions={
                PRODUCER_ASSERTION_HEADER: producer_values["producer_hash"]
            },
        )

        with httpx.Client(timeout=30.0) as client:
            wire = TypedHttpWire(
                local_peer_id=producer_values["peer_id"],
                endpoints=lambda *, peer: consumer_url or "",
                http_client=client,
                clock=lambda: now,
                receive_path=consumer_values["receive_path"],
                max_request_bytes=consumer_values["max_request_bytes"],
            )
            if consumer_url is not None:
                # Emit, then announce: READY is printed only after both
                # carriages were accepted, so the parent's blocking readline
                # is also the gate on the exchange having happened.
                peer = PeerRef(
                    tenant_id=product.tenant_id,
                    peer_id=consumer_values["peer_id"],
                )
                wire.emit(peer=peer, signed=genuine)
                wire.emit(peer=peer, signed=_tampered(genuine, other))

            # MCP egress: the L6 front door (whitepaper §8.3 Pattern 3).
            def resolve(
                *, tenant: str, product_class: str, version: str
            ) -> ServableProduct:
                requested = ProductAddress(
                    tenant=tenant, product_class=product_class, version=version
                )
                if requested != assembled.address:
                    raise ProductNotServable(str(requested))
                return assembled.servable

            egress = build_egress_server(
                server_name=assembled.server_name, resolver=resolve
            )

            mcp_bound = socket.socket()
            mcp_bound.bind(("127.0.0.1", 0))
            mcp_bound.listen(64)
            mcp_port = mcp_bound.getsockname()[1]

            a2a_bound = socket.socket()
            a2a_bound.bind(("127.0.0.1", 0))
            a2a_bound.listen(64)
            a2a_port = a2a_bound.getsockname()[1]

            mcp_server = uvicorn.Server(
                uvicorn.Config(egress.streamable_http_app(), log_level="error")
            )
            a2a_server = uvicorn.Server(
                uvicorn.Config(wire.asgi_app(), log_level="error")
            )

            async def serve() -> None:
                async def announce() -> None:
                    # A 5 ms poll of *this process's own* server objects —
                    # not the parent-side sleep-and-hope the READY handshake
                    # exists to prevent: it observes real state flags, and
                    # the parent learns nothing until both have flipped.
                    while not (mcp_server.started and a2a_server.started):
                        await anyio.sleep(0.005)
                    print(f"READY {mcp_port} {a2a_port}", flush=True)

                async def serve_mcp() -> None:
                    await mcp_server.serve(sockets=[mcp_bound])

                async def serve_a2a() -> None:
                    await a2a_server.serve(sockets=[a2a_bound])

                async with anyio.create_task_group() as group:
                    group.start_soon(announce)
                    group.start_soon(serve_mcp)
                    group.start_soon(serve_a2a)

            anyio.run(serve)


if __name__ == "__main__":
    main()
