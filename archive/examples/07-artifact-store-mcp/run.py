"""examples/07-artifact-store-mcp — the §7.4 pluggability proof (EXAM-08).

One fabric workload — boot from a manifest, ingest through L1, run the
four-category operator chain, project, gate, record the decision, persist the
product and its replay record — executed twice: once against the file-backed
``FileArtifactStore``, once against the MCP-backed reference store running in a
real subprocess. **Nothing else in the deployment changes** (CLAUDE.md §7.4).

That claim is made *structural* rather than asserted, in three ways an adopter
can see from this file alone:

1. **Both runs load the same manifest.** ``artifacts/manifest.yaml`` enumerates
   every Control Plane artifact in force, and :func:`workload` names it as a
   module constant — there is no per-run manifest, no override argument, and no
   branch that could substitute one.
2. **The store is a call-site binding, not a manifest field.** Which substrate
   persists artifacts is a deployment *environment* choice, exactly as a
   database DSN is (D-08), so it is passed in as ``store_config`` and lives in
   ``artifacts/store_{file,mcp}.yaml``. A ``store:`` field on the manifest
   would content-hash the substrate into replay dimension 2 and would make the
   two runs differ in *what was in force* — destroying the claim.
3. **The workload takes exactly one parameter.** ``workload(store_config)``
   is the entire difference between run one and run two. Anything else that
   varied would have to be a second parameter, and there is not one.

What this demonstrates, as assertions in
``tests/examples/test_artifact_store_output.py`` (D-09):

* **Byte equality.** The served Context Product's canonical bytes are identical
  across the two runs — the substrate is invisible to the fabric.
* **Same artifacts, exact versions.** The same artifact classes land at the
  same content addresses under the same versioned URIs on both stores, and
  every URI the MCP run recorded resolves against a *fresh* client to its exact
  address (never "latest") with the exact bytes behind it.
* **Configuration, not code.** Deleting the artifacts leaves this driver
  nothing to run (CLAUDE.md §6.4).

Domain values (logistics, D-09 — the swap is the point, the domain is scenery)
all live in ``artifacts/*.yaml``. Run it: ``make example-07``. Exit 0 means the
spine ran under both stores; any failure prints the store child's captured
stderr and exits nonzero.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol
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
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable
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
from ccf.replay.record import PolicyBinding, build_replay_record
from ccf.replay.serve import ReplayWriter, serve

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
CHILD = Path(__file__).resolve().parent / "mcp_store_child.py"

#: The ONE manifest both store-backed runs boot from. A module constant rather
#: than a parameter, deliberately: "nothing else in the deployment changes" is
#: only a demonstration while there is no way for the two runs to load
#: different Control Plane state, and a parameter would be exactly that way.
MANIFEST = ARTIFACTS / "manifest.yaml"

#: The class id both store-config documents declare. A store config is
#: deployment-authored — the SDK owns no schema for "which substrate persists
#: your artifacts" — so it lands on the open `DeclaredArtifact` envelope.
STORE_CONFIG_CLASS = "nordhaven-logistics.artifact-store-config"

#: Deadline every synchronous MCP call is bounded by, the grace given to a
#: terminated child before escalating to SIGKILL, and the health-check
#: cadence. Process-lifecycle mechanism values, not domain values.
CALL_TIMEOUT_SECONDS = 20.0
TERMINATE_TIMEOUT_SECONDS = 10
HEALTH_CHECK_ATTEMPTS = 5
HEALTH_CHECK_INTERVAL_SECONDS = 1.0


class ShipmentPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    ``required`` is passed in from ``projection-requirements.yaml`` — **this
    plan's own authored document**, not the product class's (design E2,
    D-IMPL-86 and its correction of 2026-08-05). The product class declares the
    Control Plane *claim*; this document declares what the plan requires. Two
    authored documents, and ``refuse_operator_set_divergence`` in
    :func:`workload` refuses when they disagree — which is where drift an
    author could write actually fails.

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


# --- the one store seam ------------------------------------------------------
#
# A factory keyed by the config artifact's declared `type`. This is the only
# place in the file a backend is named, and the workload below receives
# whatever the artifact declared — no conditional around workload logic.


# --8<-- [start:store-factory]
def _file_store(declared: Any, stack: ExitStack) -> ArtifactStoreProtocol:
    return FileArtifactStore(root=os.environ[declared["root_env"]])


def _mcp_store(declared: Any, stack: ExitStack) -> ArtifactStoreProtocol:
    auth = declared["auth"]

    def authorized_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"Authorization": f"Bearer {auth['token']}"}
        )

    bridge = stack.enter_context(
        SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS)
    )
    return McpArtifactStore(
        url=os.environ[declared["endpoint_env"]],
        bridge=bridge,
        http_client_factory=authorized_client,
    )


_STORE_FACTORIES: Mapping[
    str, Callable[[Any, ExitStack], ArtifactStoreProtocol]
] = {"file": _file_store, "mcp": _mcp_store}


def store_declaration(config_name: str) -> Mapping[str, Any]:
    """The store the named config artifact declares, parsed and validated.

    Read through the SDK's own artifact loader rather than a bare YAML parse,
    so a store config gets the same closed-world envelope contract every other
    deployment-authored document gets.
    """
    document = (ARTIFACTS / config_name).read_text(encoding="utf-8")
    parsed = cast(
        DeclaredArtifact,
        load_artifact(document, declared_artifact_class(STORE_CONFIG_CLASS)),
    )
    return parsed.declaration


def build_store(config_name: str, stack: ExitStack) -> ArtifactStoreProtocol:
    """Construct the store the named config artifact declares."""
    declared = store_declaration(config_name)
    return _STORE_FACTORIES[declared["type"]](declared, stack)
    # --8<-- [end:store-factory]


# --- the one workload --------------------------------------------------------


@dataclass(frozen=True)
class WorkloadResult:
    """What one run of the workload produced, for a caller to inspect.

    The workload returns its state rather than checking it here, so that
    ``tests/examples/test_artifact_store_output.py`` can hold the assertions
    where a test runner will actually run them.
    """

    product_bytes: bytes
    refs: Mapping[str, ArtifactRef]
    artifacts: Mapping[str, CCFContract]
    product: ContextProductContract
    operators_invoked: tuple[str, ...]


def workload(store_config: str) -> WorkloadResult:
    """Run the full fabric workload against the configured store.

    Called exactly twice, with only ``store_config`` differing — that is the
    structural form of "nothing else in the deployment changes". The parameter
    list is one item long on purpose: anything else that varied between the two
    runs would have to appear here, and nothing does.

    Args:
        store_config: The file name of the store-config artifact to bind.
            **The only per-run input.** Not a manifest field (D-08's reasoning:
            a substrate is an environment choice, and one in a content-hashed
            artifact would land in replay dimension 2).

    Returns:
        The served product's canonical bytes, the refs of every artifact
        persisted to the store keyed by artifact role, and the parsed artifacts
        the run booted from.
    """
    registry = ControlPlaneRegistry()

    with tempfile.TemporaryDirectory(prefix="ccf-example07-run-") as scratch:
        root = Path(scratch)

        # --8<-- [start:boot]
        # 1. One call, one manifest — THE SAME manifest on both runs. It names
        #    every artifact in force; `load_and_boot` parses all of them,
        #    registers the `role: register` ones, and boots on the pins.
        booted = load_and_boot(
            MANIFEST,
            registry=registry,
            connection={"database_path": str(root / "fabric.sqlite3")},
        )
        # --8<-- [end:boot]
        try:
            events = cast(SignalBatch, booted.artifacts["events"])
            decision = cast(DeclaredArtifact, booted.artifacts["decision"])
            governance = cast(
                DeclaredArtifact, booted.artifacts["product-governance"]
            )
            declared = cast(
                ProductClassDeclaration, booted.artifacts["product-class"]
            )
            # E2's other authored operator set: what the PLAN requires, as
            # opposed to what the product class CLAIMS. Two manifest keys, two
            # documents — and one manifest, so both store legs read both.
            requirements = cast(
                ProjectionRequirements,
                booted.artifacts["projection-requirements"],
            )
            perspective = cast(
                PerspectiveArtifact, booted.artifacts["perspective"]
            )

            boundary = datetime.fromisoformat(
                decision.declaration["temporal_boundary"]
            )
            now = datetime.fromisoformat(decision.declaration["now"])

            # 2. Ingest from the batch the manifest declared `role: load`.
            for envelope in events.envelopes:
                booted.handle.worker.ingest(envelope)

            # 3. The graph view at the temporal boundary this deployment named.
            view = booted.handle.reader.as_of(
                tenant_id=booted.tenant_id, at=boundary
            )

            # 4. The operator-parameters mapping, assembled by naming this
            #    deployment's OWN manifest keys — configuration an adopter
            #    reads and edits, deliberately not an isinstance filter.
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

            # 6. Project (L5). The plan reads its identity AND its operator set
            #    from `projection-requirements.yaml` — its own authored
            #    document, never the product class's declaration and never the
            #    operator registry's keys.
            #
            #    The plan is bound to a name so the binder has somewhere to
            #    stand: `refuse_operator_set_divergence` belongs BETWEEN plan
            #    construction and `execute`, and constructing the plan inline as
            #    the `plan=` argument leaves no statement between the two
            #    (D-IMPL-86's correction of 2026-08-05). It refuses when the
            #    product class's claim and the plan's requirements disagree, and
            #    it refuses rather than repairing — only the author of the two
            #    documents knows which one they meant. This is where authorable
            #    drift fails; Gate 2 below is a different check (see step 8).
            plan = ShipmentPlan(
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

            # 7. L6 — and this cluster stays in adopter code deliberately.
            #    Gate 3 compares the class's TTL CEILING against this product's
            #    own `expires_at`, which is only a check while the two are
            #    independently authored. Registering the MaxTTL value here is
            #    what MINTS `max_ttl_version`; a helper that minted the pin and
            #    stamped the product would compare a value against itself, so
            #    the SDK ships no such helper.
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
            #    `operators_invoked` is filled from the PRODUCT CLASS's
            #    declaration — the Control Plane claim — and never from
            #    `execution`. What Gate 2 then verifies is ASSEMBLY-PATH
            #    INTEGRITY: that the product served was assembled by the path
            #    the deployment claimed. The engine is a faithful transcriber of
            #    the plan rather than an independent witness of it, so this is
            #    not two independent sources meeting; drift an author could
            #    write has already failed upstream, at the binder in step 6.
            policy_version = booted.pins.version_for("policy-bundle")
            candidate = ContextProductContract(
                schema_name=product_class.schema_name,
                schema_version=product_class.schema_version,
                plan_id=execution.plan_id,
                tenant_id=booted.tenant_id,
                temporal_boundary=boundary,
                expires_at=now
                + timedelta(
                    seconds=governance.declaration["product_ttl_seconds"]
                ),
                ttl_anchor=product_class.ttl_anchor,
                lineage=ProductLineage(
                    operators_invoked=frozenset(
                        declared.required_operator_keys
                    ),
                    policy_bundle_versions=frozenset({policy_version}),
                    graph_snapshot_at=boundary,
                ),
                payload=execution.projection.payload,
            )
            # A refusal is not a thing to proceed past: `ServableProduct` is
            # not constructible outside `run_gates`, so holding one IS the
            # evidence the gates ran (INV-CH7-52).
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
                        "the three validation gates refused this product:"
                        f" {refusal}"
                    )

            # Replay before delivery. `policy_bindings` is built here, from the
            # pins the adopter reads off `BootedFabric.pins`: D-06 keeps the
            # SELECTION of which bindings are in force in adopter hands.
            record = build_replay_record(
                execution=execution,
                product=gated.product,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(key="policy-bundle", version=policy_version),
                ),
                assembly_mode=declared.assembly_mode,
                recorded_at=now,
            )

            # --- persistence: the ONLY store-touching lines in the workload --
            # --8<-- [start:store-persist]
            with ExitStack() as stack:
                store = build_store(store_config, stack)
                served = serve(
                    product=gated,
                    record=record,
                    replay_writer=ReplayWriter(
                        store=store,
                        artifact_class=governance.declaration[
                            "replay_record_class"
                        ],
                    ),
                )
                product_ref = store.put(
                    tenant_id=booted.tenant_id,
                    artifact_class=governance.declaration[
                        "product_artifact_class"
                    ],
                    name=governance.declaration["product_artifact_name"],
                    artifact=gated.product,
                )
                bundle_ref = store.put(
                    tenant_id=booted.tenant_id,
                    artifact_class=governance.declaration[
                        "policy_bundle_artifact_class"
                    ],
                    name=governance.declaration[
                        "policy_bundle_artifact_name"
                    ],
                    artifact=booted.artifacts["policy-bundle"],
                )
            # --8<-- [end:store-persist]
            return WorkloadResult(
                product_bytes=canonical_bytes(gated.product),
                refs={
                    "replay_record": served.replay_ref,
                    "product": product_ref,
                    "policy_bundle": bundle_ref,
                },
                artifacts=booted.artifacts,
                product=gated.product,
                operators_invoked=execution.operators_invoked,
            )
        finally:
            booted.handle.close()


# --- child lifecycle and health ---------------------------------------------


def _health_check(store_config: str) -> None:
    """Prove the MCP store answers before running the workload against it.

    Up to five attempts a second apart against the store's presence surface.
    A child that never becomes healthy surfaces here as a clear startup error
    rather than as a masked connection failure mid-workload.
    """
    probe = content_hash(
        load_artifact(
            (ARTIFACTS / "policy-bundle.yaml").read_text(encoding="utf-8"),
            declared_artifact_class("nordhaven-logistics.policy-bundle"),
        )
    )
    last: Exception | None = None
    for _ in range(HEALTH_CHECK_ATTEMPTS):
        with ExitStack() as stack:
            store = build_store(store_config, stack)
            try:
                store.exists(content_address=probe)
                return
            except McpServerUnreachable as refused:
                last = refused
        time.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
    raise RuntimeError(
        f"the MCP artifact store never became healthy "
        f"({HEALTH_CHECK_ATTEMPTS} attempts): {last}"
    )


@dataclass(frozen=True)
class SwapResult:
    """Both runs of the one workload, and the live MCP store behind the second.

    ``mcp_store_factory`` is handed to the caller still *usable*: the
    "resolves against a FRESH client, at its exact version, never latest"
    assertion has to open a new client while the server child is still up, and
    a result object that outlived the child could not support it.
    """

    over_file: WorkloadResult
    over_mcp: WorkloadResult
    mcp_store_factory: Callable[[ExitStack], ArtifactStoreProtocol]


def run(*, root: Path, observe: Callable[[SwapResult], None]) -> None:
    """Run the workload over both stores and hand the pair to ``observe``.

    ``observe`` is called while the MCP server child is still running, because
    the strongest assertion in this example — every recorded URI resolves at
    its exact version against a *fresh* client — needs a live server. A
    function that returned the pair and tore the child down first would leave
    that assertion unmakeable, and an example that quietly cannot make its own
    strongest claim is the failure mode this rewrite is guarding against.
    """
    store_mcp = store_declaration("store_mcp.yaml")
    store_file = store_declaration("store_file.yaml")

    proc: subprocess.Popen[bytes] | None = None
    stderr_path = root / "mcp-store-child.stderr"
    try:
        # --- run 1: the file-backed store ---------------------------------
        # --8<-- [start:store-swap]
        os.environ[store_file["root_env"]] = str(root / "file-artifacts")
        over_file = workload("store_file.yaml")

        # --- spawn the MCP artifact server, READY handshake ---------------
        with stderr_path.open("wb") as stderr_sink:
            proc = subprocess.Popen(
                [sys.executable, str(CHILD)],
                stdout=subprocess.PIPE,
                stderr=stderr_sink,
                start_new_session=True,
            )
        if proc.stdout is None:  # pragma: no cover - Popen contract
            raise RuntimeError("the store child was spawned without a stdout")
        announcement = proc.stdout.readline().decode().strip()
        if not announcement.startswith("READY "):
            raise RuntimeError(
                f"store child did not announce readiness: {announcement!r}"
            )
        port = int(announcement.split()[1])
        os.environ[store_mcp["endpoint_env"]] = f"http://127.0.0.1:{port}/mcp"
        _health_check("store_mcp.yaml")

        # --- run 2: the identical workload, MCP-backed store --------------
        over_mcp = workload("store_mcp.yaml")
        # --8<-- [end:store-swap]

        observe(
            SwapResult(
                over_file=over_file,
                over_mcp=over_mcp,
                mcp_store_factory=lambda stack: build_store(
                    "store_mcp.yaml", stack
                ),
            )
        )
    finally:
        if proc is not None:
            # Reap the whole process group: the child owns a server, and an
            # orphaned server holds its port past this run's lifetime.
            group = os.getpgid(proc.pid)
            try:
                os.killpg(group, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            if proc.stdout is not None:
                proc.stdout.close()
        if stderr_path.exists():
            captured = stderr_path.read_text(encoding="utf-8")
            if captured:
                print("mcp store child stderr:\n" + captured, file=sys.stderr)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-example07-") as scratch:
        try:
            run(root=Path(scratch), observe=lambda _: None)
        except BaseException:
            traceback.print_exc()
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
