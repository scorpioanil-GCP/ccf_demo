"""Assemble one typed Context Product and serve it, end to end.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call an
adopter must make. **There is no domain vocabulary in it at all** — no table, no
column, no entity, no artifact key, no substrate, no parameter name and no
number. Everything specific to *this* product lives in ``deployment.py`` beside
it, and in ``ccf_config.yaml`` and ``artifacts/*.yaml`` beside that.

[ADAPT] nothing.

**Delete ``ccf_config.yaml`` and nothing in this module has anything left to
interpret.** That is the No-Hardcoding Rule (CLAUDE.md §6.4) made structural
rather than aspirational, and it is the property this example is asserted
against: an example whose code still ran meaningfully with its artifacts
deleted would have violated it.

**The graph and the system of record are two different substrates here, and
that is a deployment fact rather than an architectural one.** The fabric's
state lives in a per-run local store that this process creates and discards;
the source estate is a separate store that this deployment only ever reads. CCF
does not require the two to differ and does not require them to match — nothing
in this module knows which arrangement it is running under, because the kinds
are declared in ``ccf_config.yaml`` and composed in ``backends.yaml``. The
smaller example that shares one substrate for both is not showing a rule; it is
showing one deployment. The single-writer invariant (CLAUDE.md §10) is what
holds in *either* arrangement, and it holds in the ``ingest`` region below.

**This spine IS the resolver.** :func:`~ccf.products.request.refuse_request`'s
own docstring says it is *"called by the deployment's own resolver, not by any
door"*. That is why this product class can declare a genuinely required
parameter: validation lives here, where the registered class is held, rather
than at a door that never holds one.

**The seven steps**, each wrapped in one of the named marker regions — these
seven and no others:

======  ==========================================================
marker  what the fabric does
======  ==========================================================
boot    load the one config, register what it puts in force, boot L2/L3
ingest  hand L1 envelopes to the one writer (single-writer, CLAUDE.md §10)
operators build the L4 registry from the parameter sets the deployment declared
project run Π at L5
gate    register the class and its request surface, run the three L6 gates
record  build the five-dimension Decision Replay record
serve   persist the record, then deliver (whitepaper §7.10)
======  ==========================================================

**Holding a** :class:`~ccf.products.gates.ServableProduct` **is this run's
evidence that the three validation gates ran** — the type is not constructible
outside :func:`~ccf.products.gates.run_gates`, which refuses with
:class:`~ccf.products.gates.GateBypassError`. What makes that *evidence* rather
than an assumption is that **the other branch of the match below is reachable**:
a refusal is a value this module can receive, and it raises on it. A gate result
nothing could have failed would be a decoration.

**What this spine deliberately does NOT carry.** Naming the absences is what
stops a reader concluding the surfaces do not exist:

* no ``debt_evidence`` — the debt figure is delivered, what it points at is not;
* no ``source_refresh_recency`` and no ``obligation_in_force``;
* no ``refuse_operator_set_divergence`` — that guard compares two independently
  authored operator sets, and this deployment authors one, in the product
  class's own document;
* no ``source_attestation``, so
  :func:`~ccf.products.gates.refuse_attestation` passes unconditionally. It sits
  in the same sequence as the three gates and is **not** a fourth one; naming it
  as a gate would overstate what runs;
* no similarity index, and therefore no corpus version to mint;
* **no door.** The perspective is named by the deployment's own configuration
  rather than resolved from a verified entitlement grant, because there is no
  caller identity to verify in an in-process run. A deployment with a door
  resolves it there instead, and nothing else in this sequence changes.

This module asserts nothing and prints nothing. Its assertions live in the
example's test module; what a run prints lives in ``consume.py``, which carries
no marker region, so nothing it prints is published-snippet surface.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.artifacts import (
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, build_operator_registry, load_config_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    refuse_request,
)
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord, PolicyBinding, build_replay_record
from ccf.replay.serve import QueryPinWriter, ReplayWriter, ServedProduct, serve
from ccf.signal.envelope import SignalEnvelope


class Scenario(Protocol):
    """What one run needs from the deployment's own artifacts.

    **Every member is a mechanism ROLE, never a domain value.** The values
    behind them are read from ``ccf_config.yaml`` and ``artifacts/*.yaml`` by
    ``deployment.py``, which is the only place this product's vocabulary is
    written down.

    A Protocol rather than a base class, and the two modules import nothing from
    each other: the fabric's half and the adopter's half are held together
    structurally, so a reader can tell which is which without being told
    (CLAUDE.md §11).
    """

    @property
    def envelopes(self) -> Sequence[SignalEnvelope]:
        """The L1 signal this run ingests."""

    @property
    def request(self) -> ProductRequest:
        """The question asked. Not an artifact — an argument."""

    @property
    def request_contract(self) -> ProductRequestContract:
        """The request surface the class declares."""

    @property
    def request_contract_key(self) -> str:
        """The Control Plane key the request contract registers under."""

    @property
    def product_class(self) -> ProductClassDeclaration:
        """The Control Plane *claim*: what this product says produced it."""

    @property
    def perspective(self) -> PerspectiveArtifact:
        """The Π role-conditioning this product is served under."""

    @property
    def operator_parameters(self) -> Mapping[str, OperatorParametersArtifact]:
        """Manifest key → parsed operator-parameters artifact, one per category.

        **However many the deployment declared.** This spine holds no fixed set
        of keys and never counts them: a deployment declaring one gets a
        one-operator registry, and one declaring several gets several.
        """

    @property
    def policy_bundle_key(self) -> str:
        """The key whose pin becomes the admitted bundle version."""

    @property
    def plan_id(self) -> str:
        """The projection's identity."""

    @property
    def temporal_boundary(self) -> datetime:
        """The instant the graph is read at. Data, never a clock read."""

    @property
    def now(self) -> datetime:
        """The decision instant TTL and replay are stamped against."""

    @property
    def expires_at(self) -> datetime:
        """When this product stops being servable.

        Derived by the deployment from what its own artifacts declare — the
        anchor the class names and the duration the deployment declares — never
        from a clock and never from a constant in this module.
        """

    @property
    def max_ttl_seconds(self) -> int:
        """The class's TTL ceiling. Registering it is what mints its pin."""

    @property
    def replay_record_class(self) -> str:
        """The artifact class the replay writer stores the record under."""

    @property
    def query_pin_class(self) -> str:
        """The artifact class executed graph queries are persisted under."""

    @property
    def artifact_store_dirname(self) -> str:
        """Where under the run root the file-backed ArtifactStore lives."""

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question actually assembled (whitepaper §7.7).

        A method, and it takes the view, because debt is MEASURED against the
        assembly rather than declared beside it.
        """


@dataclass(frozen=True)
class Assembled:
    """What one run produced, for a caller to inspect.

    The spine *returns* its state rather than checking it, so the assertions can
    live where a test runner will actually run them.

    Two of the fields are carried for a reason rather than for completeness,
    and it is the same reason twice: **the example's own assembly-recipe
    declares a runtime witness for every step, and a witness that cannot reach
    its subject is not a witness.**

    :attr:`view` is the composed graph state Π ran over. The handle is closed
    before this value is returned, so the view is the last readable evidence
    that the write path executed at all — an empty one is what a mis-set
    boundary produces, and no shipped gate catches that.

    :attr:`gated` is the :class:`~ccf.products.gates.ServableProduct` itself
    rather than only the contract inside it. The type is not constructible
    outside :func:`~ccf.products.gates.run_gates`, so holding one is direct
    evidence the gates ran; :attr:`product` alone would leave that evidence
    reachable only by inference from the fact that delivery happened.
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    gated: ServableProduct
    operators_invoked: frozenset[str]
    view: GraphView
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *,
    config: Path,
    connection: Mapping[str, object],
    read: Callable[[BootedFabric, ProductRequest], Scenario],
    plan_class: Callable[..., ProjectionPlan],
    request: ProductRequest,
    root: Path,
) -> Assembled | ProductRequestViolation:
    """Answer one question, end to end, against ``root`` as scratch space.

    What the fabric asks a deployment to supply arrives as ordinary arguments,
    in the same call shape the rest of the suite uses, so a reader moving
    between examples sees one shape rather than several.

    Returns the :class:`~ccf.products.request.ProductRequestViolation` **as
    data** when the question is not one this class answers. A refusal is not an
    exception: a bad question is a bad question, not a broken deployment, and a
    verdict returned as a value cannot be swallowed by a bare ``except``.
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot. The single
    #    `ccf_config.yaml` names every section in force, `load_config_and_boot`
    #    derives and parses all of them, registers the `role: register` ones,
    #    and boots on the resulting pins.
    #    Connection values arrive HERE, from the caller — never from the config,
    #    which declares the backend as a KIND only. That is what lets one
    #    deployment put its graph and its source estate on different substrates
    #    without a line of this module knowing.
    booted = load_config_and_boot(config, registry=registry, connection=connection)
    # --8<-- [end:boot]
    try:
        # The one line that crosses the boundary this example is about: the
        # deployment names its own artifact keys and hands back this question's
        # values. Everything below reads those values and nothing else.
        scenario = read(booted, request)

        # THE DOOR, and this spine is the RESOLVER standing at it. Checked
        # before the graph is touched, so a question this class does not answer
        # costs nothing and returns a reason rather than an approximation.
        violation = refuse_request(
            request=scenario.request, declared=scenario.request_contract
        )
        if violation is not None:
            return violation

        # --8<-- [start:ingest]
        # 2. L1 → L2. `booted.handle.worker` is the ONLY write handle to L3
        #    anywhere in this process; nothing else holds one and nothing can
        #    obtain one (single-writer, CLAUDE.md §10, INV-CH7-10). The source
        #    estate this deployment read from is not reachable from here at all:
        #    the fabric's write path leads into the fabric's own state and
        #    nowhere else.
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:ingest]

        # --8<-- [start:operators]
        # 3. The graph view at the boundary this deployment named.
        view = booted.handle.reader.as_of(
            tenant_id=booted.tenant_id, at=scenario.temporal_boundary
        )

        # 4. The L4 registry, built from WHATEVER parameter sets the deployment
        #    declared. `build_operator_registry` holds no fixed set of keys, so
        #    a deployment that needs one category passes one and gets one — the
        #    operators are an aid to assembly, not a mandatory pipeline. The
        #    admitted policy-bundle version is looked up from the pins here,
        #    never written into any document: it is a content hash of what was
        #    registered.
        operators = build_operator_registry(
            parameters=scenario.operator_parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key=scenario.policy_bundle_key,
        )
        # --8<-- [end:operators]

        # --8<-- [start:project]
        # 5. Π at L5. The plan's required set comes from the product class's own
        #    document, so there is no second authored set to diverge from and no
        #    divergence guard to call.
        plan = plan_class(
            plan_id=scenario.plan_id,
            required=tuple(scenario.product_class.required_operator_keys),
            scenario=scenario,
        )
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=plan,
            perspective=scenario.perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=scenario.temporal_boundary,
        )
        # --8<-- [end:project]

        # --8<-- [start:gate]
        # 6. L6. Registering the MaxTTL value is what MINTS `max_ttl_version` —
        #    the pin is a content hash of what was registered, which is why the
        #    class document cannot declare it and why the ceiling reaches this
        #    call through the deployment rather than through the class. The
        #    request surface registers on the same discipline, and
        #    `register_product_class` refuses a contract declared for another
        #    class or another lane.
        declared = scenario.product_class
        max_ttl_version = registry.register(
            declared.max_ttl_key, MaxTTL(seconds=scenario.max_ttl_seconds)
        )
        request_contract_version = registry.register(
            scenario.request_contract_key, scenario.request_contract
        )
        product_class = register_product_class(
            registry=registry,
            schema_name=declared.schema_name,
            schema_version=declared.schema_version,
            ttl_anchor=declared.ttl_anchor,
            assembly_mode=declared.assembly_mode,
            max_ttl_key=declared.max_ttl_key,
            max_ttl_version=max_ttl_version,
            request_contract_key=scenario.request_contract_key,
            request_contract_version=request_contract_version,
        )

        # 7. The lineage the product CLAIMS — filled from the DECLARATION, never
        #    from `execution`. A claim copied out of the execution record is not
        #    a claim, it is a transcript. Gate 2 then holds the two to strict
        #    equality, in both directions, so a declared operator that did not
        #    run and an operator that ran undeclared are both refusals.
        policy_version = booted.pins.version_for(scenario.policy_bundle_key)
        candidate = ContextProductContract(
            schema_name=product_class.schema_name,
            schema_version=product_class.schema_version,
            plan_id=execution.plan_id,
            tenant_id=booted.tenant_id,
            temporal_boundary=scenario.temporal_boundary,
            expires_at=scenario.expires_at,
            ttl_anchor=product_class.ttl_anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(declared.required_operator_keys),
                policy_bundle_versions=frozenset({policy_version}),
                graph_snapshot_at=scenario.temporal_boundary,
            ),
            payload=execution.projection.payload,
            # HOW MUCH TO TRUST THE ANSWER, delivered WITH the answer and
            # therefore inside its content address. Measured against what the
            # operators actually left standing, not declared beside it.
            debt=scenario.debt(execution.view),
        )
        # A refusal is not a thing to proceed past. `ServableProduct` is not
        # constructible outside `run_gates`, so holding one IS the evidence the
        # gates ran (INV-CH7-52) — and the branch below being REACHABLE is what
        # makes that evidence rather than an assumption.
        match run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=scenario.now,
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

        # --8<-- [start:record]
        # Replay before delivery. `policy_bindings` is built here, by the
        # adopter, because dimension 2 assembled by a rule nobody in the
        # deployment wrote down is not an audit record.
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=scenario.perspective,
            policy_bindings=(
                PolicyBinding(key=scenario.policy_bundle_key, version=policy_version),
            ),
            assembly_mode=declared.assembly_mode,
            recorded_at=scenario.now,
            # WHICH QUESTION THIS DECISION ANSWERED, in the record itself —
            # including the parameters the caller supplied, so replay re-asks
            # the same question rather than a similar one.
            request=scenario.request,
        )
        # --8<-- [end:record]

        # --8<-- [start:serve]
        # The record is persisted BEFORE the product is delivered, and delivery
        # is what the successful append returns — no branch reaches a served
        # product without a recorded decision (INV-CH7-79). Handing `serve` the
        # executed queries with a writer makes every recorded pin RESOLVABLE.
        store = FileArtifactStore(root=root / scenario.artifact_store_dirname)
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=store, artifact_class=scenario.replay_record_class
            ),
            query_pin_writer=QueryPinWriter(
                store=store, artifact_class=scenario.query_pin_class
            ),
            executed_queries=execution.executed_queries,
        )
        # --8<-- [end:serve]

        return Assembled(
            tenant_id=booted.tenant_id,
            scenario=scenario,
            product=gated.product,
            gated=gated,
            operators_invoked=execution.operators_invoked,
            view=execution.view,
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()
