"""examples/04-cross-process — the assembler side, in its own OS process.

Run by ``run.py`` as ``python examples/04-cross-process/producer_child.py``, or
standalone with the same command. A separate process is the entire point: the
producer's fabric, its graph file, its Control Plane registry and its private
key live in this heap; the consumer's live in the parent's. "The consumer holds
no write handle to the producer's graph" is therefore literally true here rather
than argued.

What this child does, in order:

1. Boots a fabric from ``artifacts/producer-manifest.yaml``, ingests the event
   stream through L1, runs the four-category operator chain, projects, and
   gates. Only a ``ServableProduct`` goes any further.
2. Constructs the assembler agent through the Agent Factory — the only supported
   construction path (CLAUDE.md §6.4) — from its definition artifact, and
   validates the gated product against the agent's context contract (§6.3: a
   ``ContextAssemblyAgent`` whose output is itself a typed Context Product).
3. Signs the product as this peer (detached JWS, D-IMPL-15) and, when the parent
   supplied a consumer URL, emits TWO messages over A2A before announcing: the
   genuine signed envelope, and a deliberately broken one that splices the
   genuine signature onto a different payload — so a real tampered envelope
   traverses a real socket for the parent's negative case.
4. Serves the same product over MCP egress (whitepaper §8.3 Pattern 3) and hosts
   this peer's own A2A endpoint, both on ephemeral loopback ports, and prints
   ``READY {mcp_port} {a2a_port}`` only once both servers report started. The
   parent's blocking ``readline()`` is the gate — no sleeps.

This file asserts nothing. :func:`build_situation_product` returns what it
built, and the assertions about it live in
``tests/examples/test_cross_process_output.py`` where a runner can fail a build
(D-09).

Every domain value — tenant, entity classes, operator parameters, peer identity,
endpoint path, ceilings — comes from ``artifacts/*.yaml``, enumerated by
``artifacts/producer-manifest.yaml``. Delete the artifacts and this file has
nothing to assemble, sign, or serve (CLAUDE.md §6.4).
"""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple, cast

_EXAMPLE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_ROOT.parents[1]

# The child is spawned as a bare `python <file>`, so it cannot rely on a
# relative PYTHONPATH surviving a cwd change. Resolving the roots from
# __file__ is what makes it runnable from anywhere.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from ccf.agents.agent import Agent  # noqa: E402
from ccf.agents.definitions import (  # noqa: E402
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.factory import AgentFactory  # noqa: E402
from ccf.controlplane.artifacts import (  # noqa: E402
    DeclaredArtifact,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    SignalBatch,
    load_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.deployment import build_operator_registry, load_and_boot  # noqa: E402
from ccf.graph.protocols import GraphView  # noqa: E402
from ccf.operators.base import OperatorOutput  # noqa: E402
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
from ccf.projection.engine import ProjectionEngine  # noqa: E402
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402

from ccf_runtime.mcp.egress import (  # noqa: E402
    ProductNotServable,
    build_egress_server,
    product_uri,
)
from ccf_runtime.peering.typed_http import TypedHttpWire  # noqa: E402

ARTIFACTS = _EXAMPLE_ROOT / "artifacts"
MANIFEST = ARTIFACTS / "producer-manifest.yaml"

#: The two author-versioned documents the manifest deliberately does not name.
#: See the module docstring in ``artifacts/agent-registration.yaml``: they need
#: ``register_versioned``'s D-05 bump check, which ``load_and_boot`` does not do.
AGENT_DEFINITION_DOCUMENT = ARTIFACTS / "agent-definition.yaml"
PROMPT_ARTIFACT_DOCUMENT = ARTIFACTS / "prompt-artifact.yaml"

#: Environment variables the parent sets before spawning. Shared vocabulary
#: between this module and ``run.py`` so the two cannot disagree on a name.
#: Both are optional: run standalone (no consumer to emit to), the child
#: still assembles, signs with a throwaway key, and serves both surfaces.
CONSUMER_URL_VAR = "CCF_EXAMPLE04_CONSUMER_URL"
KEY_DIR_VAR = "CCF_EXAMPLE04_KEY_DIR"


class SituationPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes. It declares
    which operators its interpretation depends on and interprets their output;
    it does not run them and cannot tell the engine what ran (which is what
    leaves the L6 lineage gate something real to check).

    ``required`` is passed in from the product-class artifact's
    ``required_operator_keys``, never read off the operator registry. The
    declaration and the engine's resolution must stay two independent
    mechanisms: Gate 2 compares them, and a plan that returned the registry's
    own keys would make that comparison a value against itself.
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
    """The gated product, its egress address, its serving identity, its agent.

    Returned rather than asserted about, so
    ``tests/examples/test_cross_process_output.py`` can hold the producer-side
    assertions where a test runner will actually run them (D-09).
    """

    servable: ServableProduct
    address: ProductAddress
    server_name: str
    agent: Agent
    definition: AgentDefinition
    definition_version: str
    expected: Mapping[str, object]
    peering: Mapping[str, str | int]
    declared_operator_keys: tuple[str, ...]
    operators_invoked: tuple[str, ...]
    now: datetime


def build_situation_product(*, database_path: Path) -> AssembledSituation:
    """Run the producer slice end to end and gate the result.

    The product is assembled, not fabricated: the whole L1->L6 path runs in
    this process, so the cross-process read on the other side is a read of
    *the fabric's* product rather than of a hand-built dict shaped like one.

    Args:
        database_path: Where this process's throwaway graph lives. Supplied
            by the caller so parent and child cannot collide on a file.

    Returns:
        The gated product plus its egress address, server name, and the
        factory-constructed agent that validated it.
    """
    registry = ControlPlaneRegistry()

    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(database_path)
    )
    try:
        events = cast(SignalBatch, booted.artifacts["events"])
        decision = cast(DeclaredArtifact, booted.artifacts["decision"])
        expected = cast(DeclaredArtifact, booted.artifacts["expected"])
        governance = cast(DeclaredArtifact, booted.artifacts["product-governance"])
        declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
        perspective = cast(PerspectiveArtifact, booted.artifacts["perspective"])
        registration = cast(DeclaredArtifact, booted.artifacts["agent-registration"])
        peering = cast(DeclaredArtifact, booted.artifacts["producer-peering"])

        boundary = datetime.fromisoformat(decision.declaration["temporal_boundary"])
        now = datetime.fromisoformat(decision.declaration["now"])

        # 2. The two AUTHOR-VERSIONED artifacts, registered here rather than by
        #    the manifest. `register_versioned` holds the author's
        #    `artifact_version` claim against content identity — the D-05 bump
        #    check — and `load_and_boot`'s `register_typed` path does not.
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

        # 3. Ingest from the batch the manifest declared `role: load`.
        for envelope in events.envelopes:
            booted.handle.worker.ingest(envelope)

        # 4. The graph view at the temporal boundary this deployment named.
        view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)

        # 5. The operator-parameters mapping, assembled by naming this
        #    deployment's OWN manifest keys — configuration an adopter reads and
        #    edits, deliberately not an isinstance filter or a class-id match.
        parameters: Mapping[str, OperatorParametersArtifact] = {
            key: cast(OperatorParametersArtifact, booted.artifacts[key])
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
        #    artifact — never from the operator registry's own keys.
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=SituationPlan(
                plan_id=governance.declaration["plan_id"],
                required=declared.required_operator_keys,
            ),
            perspective=perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
        )

        # 7. L6 — and this cluster stays in adopter code deliberately. Gate 3
        #    compares the class's TTL CEILING against this product's own
        #    `expires_at`, and that is only a check while the two are
        #    independently authored. Registering the MaxTTL here is what MINTS
        #    `max_ttl_version`; a helper that minted the pin and stamped the
        #    product would be comparing a value against itself.
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
        #    producer misdeclaring. This policy version is also what the
        #    consumer's trust policy holds this peer to at admission (§7.2).
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

        # 9. The assembler agent: factory-constructed from its definition
        #    artifact — the only supported path (§6.4) — and the gated product
        #    validates against its context contract before anything is served.
        agent = AgentFactory(control_plane=registry).construct(
            definition_key=definition_key,
            definition_version=definition_version,
        )
        agent.consume(gated.product, now=now)
    finally:
        booted.handle.close()

    return AssembledSituation(
        servable=gated,
        address=ProductAddress(
            tenant=booted.tenant_id,
            product_class=product_class.schema_name,
            version=product_class.schema_version,
        ),
        # Deployment identity, taken from the artifact that owns it rather
        # than written here — a server name in code is a domain value in code.
        server_name=governance.declaration["plan_id"],
        agent=agent,
        definition=definition,
        definition_version=definition_version,
        expected=expected.declaration,
        peering=peering.declaration,
        declared_operator_keys=declared.required_operator_keys,
        operators_invoked=execution.operators_invoked,
        now=now,
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
    import httpx
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="ccf-example04-producer-") as scratch:
        workspace = Path(scratch)
        assembled = build_situation_product(
            database_path=workspace / "producer.sqlite3"
        )
        product = assembled.servable.product
        now = assembled.now
        # This peer's own federation identity, from its own Control Plane. The
        # consumer's matching entitlement is a separate document on the
        # consumer's side; nothing here reads it.
        peering = assembled.peering
        key_id = str(peering["key_id"])

        key_dir_value = os.environ.get(KEY_DIR_VAR)
        if key_dir_value is None:
            key_dir = workspace / "keys"
            key_dir.mkdir()
            _throwaway_key(key_dir, key_id)
        else:
            key_dir = Path(key_dir_value)

        provider = DetachedJwsIdentityProvider(
            key_source=FileBackedKeySource(directory=key_dir)
        )
        producer_hash = str(peering["producer_hash"])
        genuine = provider.sign(
            product=product,
            key_id=key_id,
            assertions={PRODUCER_ASSERTION_HEADER: producer_hash},
        )
        # A second, genuinely different product, signed the same way, purely
        # so its payload member exists to be spliced onto the genuine
        # signature for the parent's negative admission case.
        other = provider.sign(
            product=product.model_copy(
                update={"payload": {**product.payload, "entity_count": -1}}
            ),
            key_id=key_id,
            assertions={PRODUCER_ASSERTION_HEADER: producer_hash},
        )

        consumer_url = os.environ.get(CONSUMER_URL_VAR)
        with httpx.Client(timeout=30.0) as client:
            wire = TypedHttpWire(
                local_peer_id=str(peering["peer_id"]),
                endpoints=lambda *, peer: consumer_url or "",
                http_client=client,
                clock=lambda: now,
                receive_path=str(peering["receive_path"]),
                max_request_bytes=int(peering["max_request_bytes"]),
            )
            if consumer_url is not None:
                # Emit, then announce: READY is printed only after both
                # carriages were accepted, so the parent's blocking readline
                # is also the gate on the exchange having happened.
                peer = PeerRef(
                    tenant_id=product.tenant_id,
                    peer_id=str(peering["consumer_peer_id"]),
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
