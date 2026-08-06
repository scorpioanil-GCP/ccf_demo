"""examples/external/00-hello-context — the fabric side, one black-box process.

The external consumer's whole view of CCF is this server: an authenticated
MCP front door (CLAUDE.md §8.3 — "the primary surface for external agent
runtimes consuming the fabric"; §7.1 — MCP as the Experience Layer access
surface; whitepaper §8.3 Pattern 3 — Context Products as MCP Resources).
Client legs hold an MCP URL and a bearer token, nothing else.

What this process does, in order:

1. Boots a small financial-services fabric from ``artifacts/manifest.yaml``:
   one borrower, one revolving credit facility, a handful of financial
   signals. One ``load_and_boot`` call replaces what used to be a
   hand-written loader, a resolution-spec marshaller, a registration
   prologue and a ``boot`` call; ``build_operator_registry`` replaces the
   61-line inline operator block. Ingests through L1, runs the
   four-category operator chain, projects, gates. Only a ``ServableProduct``
   goes any further.
2. Hosts the Experience-surface MCP server (``build_experience_server`` —
   the only surface with the D-12-required auth machinery; the raw egress
   server has no auth parameters, which is why this deployment composes
   the front door rather than the egress role). Bearer-token auth is on
   from day one; the verifier reads the token table the manifest loaded
   and there is no anonymous mode.
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

This file makes no domain claim about what it assembled.
:func:`build_credit_context` returns what it built — including the parsed
artifact set — and the assertions about it live in
``tests/examples/test_ext00_serve_output.py``, where a runner can fail a
build (D-09). The one ``print`` here is the READY handshake, which is
process protocol rather than narration and cannot move.

Every domain and deployment value — tenant, entity vocabulary, operator
parameters, tool prose, token table, auth issuer — comes from
``artifacts/*.yaml``, enumerated by ``artifacts/manifest.yaml``. Delete the
artifacts and this file has nothing to assemble or serve (CLAUDE.md §6.4).
Nothing here modifies ``/src`` or ``/runtime``; this is deployment
composition over shipped mechanism.
"""

from __future__ import annotations

import hmac
import socket
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple, cast

_EXAMPLE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_ROOT.parents[2]

# Spawned as a bare `python <file>`, so it cannot rely on a relative
# PYTHONPATH surviving a cwd change. Resolving the roots from __file__ is
# what makes it runnable from anywhere.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from mcp.server.auth.middleware.auth_context import get_access_token  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.artifacts.protocol import ArtifactRef  # noqa: E402
from ccf.contracts.base import CCFContract  # noqa: E402
from ccf.contracts.canonical import canonical_bytes  # noqa: E402
from ccf.controlplane.artifacts import (  # noqa: E402
    DeclaredArtifact,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
)
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.deployment import (  # noqa: E402
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
from ccf.graph.protocols import GraphView  # noqa: E402
from ccf.operators.base import OperatorOutput  # noqa: E402
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf.projection.engine import ProjectionEngine  # noqa: E402
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.replay.record import (  # noqa: E402
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve  # noqa: E402

from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, TokenGrant  # noqa: E402
from ccf_runtime.mcp.experience import (  # noqa: E402
    GET_CONTEXT_TOOL,
    GET_LINEAGE_TOOL,
    GET_REPLAY_RECORD_TOOL,
    LIST_AGENTS_TOOL,
    ExperienceProductNotServable,
    build_experience_server,
    experience_product_uri,
)

ARTIFACTS = _EXAMPLE_ROOT / "artifacts"
MANIFEST = ARTIFACTS / "manifest.yaml"

#: The manifest keys whose artifacts configure the four operator categories.
#: Named literals, deliberately: they are this deployment's own vocabulary and
#: an adopter reads and edits them. An `isinstance` filter or a class-id match
#: would be type introspection, and copied across the suite it would be a new
#: duplication class of exactly the sort this surface exists to remove.
OPERATOR_PARAMETER_KEYS: tuple[str, ...] = (
    "traversal",
    "temporal",
    "policy",
    "similarity",
)

#: The manifest key the policy bundle is in force under. `build_operator_registry`
#: looks its pinned version up and completes the policy operator's parameter set
#: from it (D-IMPL-76) — the deployment names which bundle it admits, the SDK
#: only resolves the pin.
POLICY_BUNDLE_KEY = "policy-bundle"

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


def validate_agent_exposure(
    agent_exposure: Mapping[str, Any], tool_allowlist: Sequence[str]
) -> None:
    """Refuse composition when declared agents could never be served.

    This deployment exposes no agents, so it allowlists neither agent tool
    and supplies neither agent seam (D-03). Adding an entry under
    `agent_exposure.agents` is the README's "what to change first"
    instinct, and it must not fail somewhere downstream: without
    `list_agents` allowlisted the entry is simply unreachable, and with it
    allowlisted the raw artifact mapping would flow untyped into the SDK's
    `ExposedAgent` surface and blow up at call time. Validation belongs at
    the artifact boundary, never deferred (CLAUDE.md §11).
    """
    declared = agent_exposure["agents"]
    if declared and LIST_AGENTS_TOOL not in tool_allowlist:
        raise ValueError(
            f"experience.yaml agent_exposure.agents declares "
            f"{len(declared)} agent(s), but {LIST_AGENTS_TOOL!r} is absent "
            f"from tool_allowlist, so no caller could ever see them — add "
            f"the tool to the allowlist and pass an agent_directory that "
            f"validates each entry into an ExposedAgent"
        )


def get_context_request_label(*, tenant: str, entity: str) -> str:
    """The ``ServeRequestRecord.request`` descriptor for a get_context serve.

    Every serve — the templated Experience resource AND the `get_context`
    tool — appends a `ServeRequestRecord` under the same verified
    `client_id`, and each names the delivery it recorded. A caller that
    wants the record for ONE specific serve therefore has to identify that
    serve, not reach for "newest in the store": `run.py`'s D-16
    reproduction did the latter and silently depended on `_mcp_probe`
    calling `read_resource` before `call_tool` (IN-04). One function, used
    by the writer here and by the reader in `run.py`, is the seam that
    makes the selection explicit instead of positional.
    """
    return f"get_context tenant={tenant} entity={entity}"


class ArtifactTokenSource:
    """TokenSourceProtocol over the token-table artifact (example-05 pattern).

    Only ACTIVE entries yield a grant; the revoked entry refuses exactly as
    an unknown token does (fail closed). Constant-time comparison, as the
    shipped file source does. The entries arrive already parsed off
    ``BootedFabric.artifacts``, so there is no second read of the file to
    drift from the first.
    """

    def __init__(self, *, entries: Sequence[Mapping[str, Any]]) -> None:
        self._entries = tuple(entries)

    def grant_for(self, *, token: str) -> TokenGrant | None:
        for entry in self._entries:
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

    ``required`` is passed in from ``artifacts/projection-requirements.yaml``
    (``ccf.projection-requirements``) — the projection's OWN document, not the
    product class's and not the operator registry's keys. Under design E2
    (``docs/DECISIONS.md`` D-IMPL-86 and its correction of 2026-08-05) the two
    operator sets a deployment authors are separate documents:
    ``product-class.yaml``'s ``required_operator_keys`` is the Control Plane
    **claim** that fills the product's lineage, and this one is what the plan
    requires. ``refuse_operator_set_divergence`` binds them, between plan
    construction and ``ProjectionEngine.execute``, and that is where
    **authorable drift** fails.

    Feeding ``required`` from the product-class declaration instead would not be
    a second source at all: the declaration would reach the engine's
    ``operators_invoked`` through five pure transforms with no branch, so the
    two would be identical by construction and nothing an author could write
    would separate them. Both of this example's plan sites read the requirements
    artifact and both call the binder — this one and
    ``run.py``'s ``HelloReplayEnvironment.resolve_plan``.
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
    """Everything a serve needs: the gated product, its replay inputs, and the
    artifact set the deployment was assembled from.

    ``artifacts`` is on here rather than re-read by every caller because
    ``load_and_boot`` already parsed and validated every document; a second
    read is a second answer that can drift from the first. It is also what
    lets ``tests/examples/test_ext00_serve_output.py`` assert against the same
    authored values this process ran on.
    """

    servable: ServableProduct
    address: ProductAddress
    record: DecisionReplayRecord
    artifacts: Mapping[str, CCFContract]


def build_credit_context(*, database_path: Path) -> AssembledContext:
    """Run the finserv slice end to end, gate it, and build its replay record.

    The product is assembled, not fabricated: the whole L1->L6 path runs in
    this process, so an external client's read is a read of *the fabric's*
    product rather than of a hand-built dict shaped like one.
    """
    registry = ControlPlaneRegistry()

    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(database_path)
    )
    try:
        # Each artifact comes back under its own manifest key, already validated
        # against the class the manifest declared for it — so these casts restate
        # what `load_and_boot` already enforced. A wrong `class_id` in the
        # manifest fails at parse, before this line runs.
        events = cast(SignalBatch, booted.artifacts["events"])
        decision = cast(DeclaredArtifact, booted.artifacts["decision"])
        governance = cast(DeclaredArtifact, booted.artifacts["product-governance"])
        declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
        requirements = cast(
            ProjectionRequirements, booted.artifacts["projection-requirements"]
        )
        perspective = cast(PerspectiveArtifact, booted.artifacts["perspective"])

        boundary = datetime.fromisoformat(decision.declaration["temporal_boundary"])
        now = datetime.fromisoformat(decision.declaration["now"])

        # 2. Ingest from the batch the manifest declared `role: load`.
        for envelope in events.envelopes:
            booted.handle.worker.ingest(envelope)

        # 3. The graph view at the temporal boundary this deployment named.
        #    Which boundary a deployment reads its corpus at is a deployment
        #    decision, so it stays an explicit line here.
        view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)

        # 4/5. The four-category operator chain (L4), built from the artifacts
        #      the manifest already parsed. The similarity index's corpus is
        #      read out of `view` at the boundary above, which is why the
        #      builder takes the view rather than lazily binding one.
        parameters: Mapping[str, OperatorParametersArtifact] = {
            key: cast(OperatorParametersArtifact, booted.artifacts[key])
            for key in OPERATOR_PARAMETER_KEYS
        }
        operators = build_operator_registry(
            parameters=parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=governance.declaration[
                "similarity_index_version"
            ],
        )

        # 6. Project (L5). The plan's `required` comes from the projection's OWN
        #    artifact — never from the operator registry's keys, and never from
        #    the product class, which is the claim rather than the plan's input.
        #
        #    The plan is a named local so the binder has a statement to occupy:
        #    the refusal belongs BETWEEN plan construction and `execute`
        #    (D-IMPL-86's correction of 2026-08-05), and a plan built inline as
        #    `execute`'s own argument leaves no such line. Edit either authored
        #    document alone and this front door refuses to compose, before a
        #    product is assembled from a set the deployment's claim contradicts.
        plan = CreditContextPlan(
            plan_id=governance.declaration["plan_id"],
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

        # 7. L6 — and this cluster stays in deployment code deliberately.
        #
        #    Gate 3 compares the class's TTL CEILING against this product's own
        #    `expires_at`. That is only a check while the two are independently
        #    authored. Registering the MaxTTL value here is what MINTS
        #    `max_ttl_version` — the pin is a content hash of what was
        #    registered, which is why the product-class artifact cannot declare
        #    it. A helper that minted the pin and stamped the product would be
        #    comparing a value against itself, so the SDK ships no such helper
        #    and these lines survive the ergonomics phase on purpose.
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
        #    The claim is the product class's `required_operator_keys` — the
        #    Control Plane's authored statement of what this product's assembly
        #    depends on. It is never `execution.operators_invoked`: filling the
        #    claim from the engine's own report would make Gate 2 compare a
        #    value against itself.
        #
        #    What Gate 2 then verifies is ASSEMBLY-PATH INTEGRITY: that the
        #    product served was assembled by the path the deployment claimed.
        #    The engine is a faithful transcriber of the plan rather than an
        #    independent witness of it — it builds its invoked set and its steps
        #    in one loop over the same operator plan — so the gate catches an
        #    assembly that departed from the plan, not a claim that was wrong to
        #    begin with. Authorable drift fails upstream, at
        #    `refuse_operator_set_divergence` in step 6.
        policy_version = booted.pins.version_for(POLICY_BUNDLE_KEY)
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
        # A refusal is not a thing to proceed past, and a bare `assert` would
        # vanish under `python -O`: `ServableProduct` is not constructible
        # outside `run_gates`, so holding one IS the evidence the gates ran
        # (INV-CH7-52). Nothing external ever sees an ungated product.
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
                raise ExperienceProductNotServable(
                    f"the three validation gates refused this product: {refusal}"
                )

        # Replay before delivery. `policy_bindings` is built here, from the
        # pins read off `BootedFabric.pins`: D-06 keeps the SELECTION of which
        # bindings are in force in deployment hands, because dimension 2
        # assembled by a rule nobody in the deployment wrote down is not an
        # audit record.
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key=POLICY_BUNDLE_KEY, version=policy_version),
            ),
            assembly_mode=declared.assembly_mode,
            recorded_at=now,
        )
    finally:
        booted.handle.close()

    return AssembledContext(
        servable=gated,
        address=ProductAddress(
            tenant=booted.tenant_id,
            product_class=product_class.schema_name,
            version=product_class.schema_version,
        ),
        record=record,
        artifacts=booted.artifacts,
    )


def main() -> None:
    """Assemble, gate, host the authenticated front door, announce READY."""
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="ccf-ext00-fabric-") as scratch:
        assembled = build_credit_context(
            database_path=Path(scratch) / "fabric.sqlite3"
        )
        governance = cast(
            DeclaredArtifact, assembled.artifacts["product-governance"]
        ).declaration
        experience = cast(
            DeclaredArtifact, assembled.artifacts["experience"]
        ).declaration
        focus = cast(DeclaredArtifact, assembled.artifacts["focus"]).declaration
        token_entries = cast(
            DeclaredArtifact, assembled.artifacts["tokens"]
        ).declaration["tokens"]

        store = FileArtifactStore(root=_EXAMPLE_ROOT / ".store")
        writer = ReplayWriter(
            store=store, artifact_class=governance["replay_record_class"]
        )
        serve_request_class: str = governance["serve_request_class"]

        # Keyed by the VERIFIED client identity, not a single process-global
        # slot. A shared slot served whichever record was written last to
        # whichever caller asked next: client A's decision record was
        # readable by client B, and under concurrency a caller could read a
        # record that was not its own even with one client. The
        # ServeRequestRecord below is already per-client_id, so the
        # deployment distinguishes callers everywhere else too.
        latest: dict[str, ArtifactRef] = {}

        def _serve_recorded(request: str) -> bytes:
            # D-13/D-14: the replay record is appended BEFORE the bytes can
            # exist to return (the delivery is a method on the value the
            # append returned), and the inbound request — verified identity,
            # arguments or URI, timestamp — is captured fabric-side. The
            # client carries no obligation.
            token = get_access_token()
            if token is None:
                # Unreachable behind the auth middleware, which refuses an
                # unverified caller before the tool body runs — but the
                # dereference below is a guarantee, not a hint, and a bare
                # assert would vanish under `python -O`.
                raise ExperienceProductNotServable(
                    "no verified access token in context"
                )
            served = serve(
                product=assembled.servable,
                record=assembled.record,
                replay_writer=writer,
            )
            latest[token.client_id] = served.replay_ref
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

        def context_provider(*, tenant: str, entity: str) -> str:
            if (
                tenant != assembled.address.tenant
                or entity != focus["entity_ref"]
            ):
                raise ExperienceProductNotServable(f"{tenant}/{entity}")
            return _serve_recorded(
                get_context_request_label(tenant=tenant, entity=entity)
            ).decode("utf-8")

        def lineage_provider() -> str:
            return canonical_bytes(assembled.servable.product.lineage).decode(
                "utf-8"
            )

        def replay_record_reader() -> str:
            # Read back under the SAME verified identity that wrote it: a
            # caller reads its own decision record and no one else's.
            token = get_access_token()
            if token is None:
                raise ExperienceProductNotServable(
                    "no verified access token in context"
                )
            ref = latest.get(token.client_id)
            if ref is None:
                raise ExperienceProductNotServable(
                    "no product has been served to this client yet"
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
        validate_agent_exposure(
            experience["agent_exposure"], experience["tool_allowlist"]
        )
        # No agent_directory / agent_invoker: the agent tools are absent
        # from the artifact allowlist, so the builder registers neither and
        # requires neither (D-03). A deployment that exposes agents
        # allowlists the tools and supplies the seams; this one does not
        # hand in dead callables to satisfy a signature.
        server = build_experience_server(
            server_name=experience["server_name"],
            product_resolver=resolve,
            context_provider=context_provider,
            lineage_provider=lineage_provider,
            replay_record_reader=replay_record_reader,
            get_context_description=tools["get_context"]["description"],
            get_lineage_description=tools["get_lineage"]["description"],
            get_replay_record_description=tools["get_replay_record"][
                "description"
            ],
            token_verifier=SourceBackedTokenVerifier(
                source=ArtifactTokenSource(entries=token_entries)
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
