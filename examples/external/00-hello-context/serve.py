"""examples/external/00-hello-context — the fabric side, one black-box process.

The external consumer's whole view of CCF is this server: an authenticated
MCP front door (CLAUDE.md §8.3 — "the primary surface for external agent
runtimes consuming the fabric"; §7.1 — MCP as the Experience Layer access
surface; whitepaper §8.3 Pattern 3 — Context Products as MCP Resources).
Client legs hold an MCP URL and a bearer token, nothing else.

What this process does, in order:

1. Boots a small financial-services fabric from ``artifacts/``: one
   borrower, one revolving credit facility, a handful of financial signals.
   Ingests through L1, runs the four-category operator chain, projects,
   gates. Only a ``ServableProduct`` goes any further.
2. Hosts the Experience-surface MCP server (``build_experience_server`` —
   the only surface with the D-12-required auth machinery; the raw egress
   server has no auth parameters, which is why this deployment composes
   the front door rather than the egress role). Bearer-token auth is on
   from day one; the verifier reads ``artifacts/tokens.yaml`` and there is
   no anonymous mode.
3. Composes — never registers — the three external-consumption tools
   the SDK promoted (D-IMPL-74): the provider closures for
   ``get_context`` (the mid-loop tool an external agent calls) and the
   read-only ``get_lineage`` / ``get_replay_record`` are passed *into*
   ``build_experience_server`` along with their artifact-carried prose
   and the ``tool_allowlist`` from ``artifacts/experience.yaml``. The
   allowlist advertises exactly those three tools; the agent tools are
   absent from it, so they are never registered (D-05 — registration-time
   omission). A concrete (non-templated) product resource is added so
   browsing clients see something listable. Tool names and prose come
   from the artifact, never from this file (CLAUDE.md §6.4).
4. Serves every externally-delivered product through
   ``ccf.replay.serve.ReplayWriter`` -> ``DeliveryCapability`` against a
   file-backed ArtifactStore, so the five-dimension Decision Replay record
   (whitepaper §7.10) lands BEFORE the bytes leave, by construction — and
   records the inbound request itself (requesting identity from the
   verified token via ``get_access_token()``, the tool arguments or
   resource URI, a timestamp) with zero client obligation.
5. Binds port 0 on loopback and prints ``READY <port>`` once uvicorn
   reports started. The parent's blocking ``readline()`` is the gate.

Every domain and deployment value — tenant, entity vocabulary, operator
parameters, tool prose, token table, auth issuer — comes from
``artifacts/*.yaml``. Delete the artifacts and this file has nothing to
assemble or serve (CLAUDE.md §6.4). Nothing here modifies ``/src`` or
``/runtime``; this is deployment composition over shipped mechanism.
"""

from __future__ import annotations

import hmac
import socket
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

_EXAMPLE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_ROOT.parents[2]

# Spawned as a bare `python <file>`, so it cannot rely on a relative
# PYTHONPATH surviving a cwd change. Resolving the roots from __file__ is
# what makes it runnable from anywhere.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import yaml  # noqa: E402
from mcp.server.auth.middleware.auth_context import get_access_token  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.artifacts.protocol import ArtifactRef  # noqa: E402
from ccf.assembly.worker import (  # noqa: E402
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot  # noqa: E402
from ccf.contracts.base import CCFContract  # noqa: E402
from ccf.contracts.canonical import canonical_bytes  # noqa: E402
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
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf.projection.engine import (  # noqa: E402
    ExecutionResult,
    OperatorRegistry,
    ProjectionEngine,
)
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.replay.record import (  # noqa: E402
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve  # noqa: E402
from ccf.signal.envelope import SignalEnvelope, SourceIdentity  # noqa: E402
from ccf.similarity.protocol import TokenOverlapIndex  # noqa: E402

from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, TokenGrant  # noqa: E402
from ccf_runtime.mcp.experience import (  # noqa: E402
    GET_CONTEXT_TOOL,
    GET_LINEAGE_TOOL,
    GET_REPLAY_RECORD_TOOL,
    ExperienceProductNotServable,
    build_experience_server,
    experience_product_uri,
)

ARTIFACTS = _EXAMPLE_ROOT / "artifacts"

#: Artifact key -> the SDK tool constant that key's provider is bound to
#: in the `build_experience_server` call below. The artifact carries the
#: names and the prose (§6.4); the binding of key to seam is the thing
#: this file interprets, so it is the thing that must be checked.
TOOL_NAME_BINDINGS: tuple[tuple[str, str], ...] = (
    ("get_context", GET_CONTEXT_TOOL),
    ("get_lineage", GET_LINEAGE_TOOL),
    ("get_replay_record", GET_REPLAY_RECORD_TOOL),
)


def validate_tool_names(tools: Mapping[str, Any]) -> None:
    """Refuse composition when an artifact tool name is not the SDK's (D-02).

    `build_experience_server` registers the three promoted consumption
    tools under the SDK's own constants; the artifact's `tools.*.name`
    values are what the deployment *believes* it advertises. A divergence
    is silent today and only surfaces when a caller invokes a tool that
    was never registered — so it fails here, at composition time, before
    the server starts, naming the artifact key, the declared value, and
    the expected constant.

    D-02/D-05 (Dave, 2026-08-02). No warn-and-continue.
    """
    for artifact_key, constant in TOOL_NAME_BINDINGS:
        declared = tools[artifact_key]["name"]
        if declared != constant:
            raise ValueError(
                f"experience.yaml tools.{artifact_key}.name is {declared!r}; "
                f"the SDK tool constant this deployment binds it to is "
                f"{constant!r} — rename the artifact value or bind a "
                f"different tool"
            )


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38). Attaching UTC at the
    # artifact boundary is the loader's job; the fabric never guesses.
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class ArtifactTokenSource:
    """TokenSourceProtocol over the token-table artifact (example-05 pattern).

    Only ACTIVE entries yield a grant; the revoked entry refuses exactly as
    an unknown token does (fail closed). Constant-time comparison, as the
    shipped file source does.
    """

    def __init__(self, *, path: Path) -> None:
        self._path = path

    def grant_for(self, *, token: str) -> TokenGrant | None:
        table = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        for entry in table["tokens"]:
            if entry["status"] != "active":
                continue
            if hmac.compare_digest(entry["token"], token):
                return TokenGrant(
                    client_id=entry["client_id"],
                    scopes=tuple(entry["scopes"]),
                )
        return None


class ServeRequestRecord(CCFContract):
    """The inbound request, captured fabric-side (D-13; zero client obligation).

    Who asked (the verified token's client identity), what they asked for
    (tool arguments or resource URI), when, and which replay record the
    delivery landed under — so the serve event and the decision record name
    each other.
    """

    client_id: str
    request: str
    requested_at: datetime
    replay_uri: str


class CreditContextPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes. It declares
    which operators its interpretation depends on and interprets their
    output; it does not run them (which is what leaves the L6 lineage gate
    something real to check).
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
    """The three segments that name a product on the front-door surface."""

    tenant: str
    product_class: str
    version: str


class AssembledContext(NamedTuple):
    """Everything a serve needs: the gated product and its replay inputs."""

    servable: ServableProduct
    address: ProductAddress
    record: DecisionReplayRecord


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


def _operators(
    *,
    ontology: Any,
    params: Any,
    policy_version: str,
    corpus: Mapping[tuple[str, str], str],
) -> OperatorRegistry:
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
                corpus=dict(corpus),
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
    return operators


def build_credit_context(*, database_path: Path) -> AssembledContext:
    """Run the finserv slice end to end, gate it, and build its replay record.

    The product is assembled, not fabricated: the whole L1->L6 path runs in
    this process, so an external client's read is a read of *the fabric's*
    product rather than of a hand-built dict shaped like one.
    """
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    product_doc = _load("product.yaml")

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

        corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
        view = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
        corpus = {
            (tenant_id, record.claim.entity_uri): record.claim.attributes[
                corpus_attribute[record.claim.entity_class]
            ]
            for record in view.entities
            if record.claim.entity_class in corpus_attribute
        }
        operators = _operators(
            ontology=ontology,
            params=control["operator_parameters"],
            policy_version=policy_version,
            corpus=corpus,
        )

        declared_class = product_doc["product_class"]
        plan = CreditContextPlan(
            plan_id=declared_class["plan_id"], required=operators.keys()
        )
        perspective = Perspective(
            principal_id=control["perspective"]["principal_id"],
            role=control["perspective"]["role"],
        )
        engine = ProjectionEngine(reader=handle.reader, registry=operators)
        execution: ExecutionResult = engine.execute(
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

        # Fabric-side self-check: the served view matches what the
        # deployment declared it expects — before anything external sees it.
        expected = product_doc["expected"]
        payload = gated.product.payload
        assert payload["entity_count"] == expected["entity_count"], payload
        assert sorted(
            {entry["entity_class"] for entry in payload["entities"]}
        ) == sorted(expected["entity_classes"]), payload
        assert payload["relationship_types"] == sorted(
            expected["relationship_types"]
        ), payload

        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key=keys["policy_bundle"], version=policy_version),
            ),
            assembly_mode=declared_class["assembly_mode"],
            recorded_at=now,
        )
    finally:
        handle.close()

    return AssembledContext(
        servable=gated,
        address=ProductAddress(
            tenant=tenant_id,
            product_class=product_class.schema_name,
            version=product_class.schema_version,
        ),
        record=record,
    )


def main() -> None:
    """Assemble, gate, host the authenticated front door, announce READY."""
    import anyio
    import uvicorn

    control = _load("controlplane.yaml")
    product_doc = _load("product.yaml")
    experience = _load("experience.yaml")

    store = FileArtifactStore(root=_EXAMPLE_ROOT / ".store")
    writer = ReplayWriter(
        store=store,
        artifact_class=control["artifacts"]["replay_record_class"],
    )
    serve_request_class: str = control["artifacts"]["serve_request_class"]

    with tempfile.TemporaryDirectory(prefix="ccf-ext00-fabric-") as scratch:
        assembled = build_credit_context(
            database_path=Path(scratch) / "fabric.sqlite3"
        )
        latest: dict[str, ArtifactRef | None] = {"replay_ref": None}

        def _serve_recorded(request: str) -> bytes:
            # D-13/D-14: the replay record is appended BEFORE the bytes can
            # exist to return (the delivery is a method on the value the
            # append returned), and the inbound request — verified identity,
            # arguments or URI, timestamp — is captured fabric-side. The
            # client carries no obligation.
            token = get_access_token()
            assert token is not None  # auth middleware refused already if not
            served = serve(
                product=assembled.servable,
                record=assembled.record,
                replay_writer=writer,
            )
            latest["replay_ref"] = served.replay_ref
            store.put(
                tenant_id=assembled.address.tenant,
                artifact_class=serve_request_class,
                name=token.client_id,
                artifact=ServeRequestRecord(
                    client_id=token.client_id,
                    request=request,
                    requested_at=datetime.now(UTC),
                    replay_uri=served.replay_ref.uri,
                ),
            )
            return canonical_bytes(served.product)

        def resolve(
            *, tenant: str, product_class: str, version: str
        ) -> ServableProduct:
            requested = ProductAddress(
                tenant=tenant, product_class=product_class, version=version
            )
            if requested != assembled.address:
                raise ExperienceProductNotServable(str(requested))
            _serve_recorded(
                experience_product_uri(
                    tenant=tenant, product_class=product_class, version=version
                )
            )
            return assembled.servable

        def agent_directory(*, tenant: str) -> tuple[()]:
            # Artifacts-declared empty exposure (hello-world scope). The
            # agent tools are absent from the artifact's tool_allowlist,
            # so this seam is never reachable from the wire.
            del tenant
            return tuple(experience["agent_exposure"]["agents"])

        def agent_invoker(**_: object) -> str:
            raise RuntimeError(experience["agent_exposure"]["invocation_refusal"])

        focus = product_doc["focus"]

        def context_provider(*, tenant: str, entity: str) -> str:
            if (
                tenant != assembled.address.tenant
                or entity != focus["entity_ref"]
            ):
                raise ExperienceProductNotServable(f"{tenant}/{entity}")
            return _serve_recorded(
                f"get_context tenant={tenant} entity={entity}"
            ).decode("utf-8")

        def lineage_provider() -> str:
            return canonical_bytes(assembled.servable.product.lineage).decode(
                "utf-8"
            )

        def replay_record_reader() -> str:
            ref = latest["replay_ref"]
            if ref is None:
                raise ExperienceProductNotServable(
                    "no product has been served yet"
                )
            return store.get(content_address=ref.content_address).decode(
                "utf-8"
            )

        # Composition, not registration (D-15): the promoted tools live in
        # the shipped builder; this deployment supplies provider closures,
        # artifact-carried prose, and the artifact-carried allowlist, which
        # names exactly the three consumption tools — so the agent tools
        # are never registered and cannot be advertised (D-05, D-IMPL-74).
        auth_values = experience["auth"]
        tools = experience["tools"]
        validate_tool_names(tools)
        server = build_experience_server(
            server_name=experience["server_name"],
            product_resolver=resolve,
            agent_directory=agent_directory,
            agent_invoker=agent_invoker,
            context_provider=context_provider,
            lineage_provider=lineage_provider,
            replay_record_reader=replay_record_reader,
            get_context_description=tools["get_context"]["description"],
            get_lineage_description=tools["get_lineage"]["description"],
            get_replay_record_description=tools["get_replay_record"][
                "description"
            ],
            token_verifier=SourceBackedTokenVerifier(
                source=ArtifactTokenSource(path=ARTIFACTS / "tokens.yaml")
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl(auth_values["issuer_url"]),
                resource_server_url=AnyHttpUrl(auth_values["resource_server_url"]),
                required_scopes=[auth_values["required_scope"]],
            ),
            tool_allowlist=frozenset(experience["tool_allowlist"]),
        )

        # Concrete (non-templated) resource for the hello product, so
        # resources/list shows a browsable entry even in clients that do
        # not surface resource templates.
        concrete_uri = experience_product_uri(
            tenant=assembled.address.tenant,
            product_class=assembled.address.product_class,
            version=assembled.address.version,
        )

        @server.resource(concrete_uri, mime_type="application/json")
        def hello_product() -> str:
            return _serve_recorded(concrete_uri).decode("utf-8")

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]
        http_server = uvicorn.Server(
            uvicorn.Config(server.streamable_http_app(), log_level="error")
        )

        async def host() -> None:
            async def announce() -> None:
                while not http_server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async def serve_http() -> None:
                await http_server.serve(sockets=[bound])

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                group.start_soon(serve_http)

        anyio.run(host)


if __name__ == "__main__":
    main()
