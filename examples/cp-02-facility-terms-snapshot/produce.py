"""The spine — one question, end to end, for `reference.facility.v1`.

[MECHANISM] everything below the deployment seam. [ADAPT] nothing here: the
whole point of this module is that it names no facility, no borrower,
no table and no threshold. Every value it works with arrives from
`deployment.py`, which in turn interprets the documents beside it.

**The nine numbered steps are the specification's §D.2 read as code**, and the
ordering is not a convenience. `Policy` runs before anything reads graph state
(Standard §10.3), the replay record is written before the product is delivered
(INV-CH7-79), and `ServableProduct` is not constructible outside `run_gates` —
so holding one IS the evidence the gates ran, rather than a claim that they did.

**TWO REFUSALS ARE RETURNED AS DATA rather than raised.** A question this class
does not answer is a `ProductRequestViolation`; an anchor that resolves to no
facility is an :class:`AnchorUnresolvable`. Neither is an exception, because a
bad question and a missing facility are not broken deployments — and a verdict
returned as a value cannot be swallowed by a bare ``except``. §D.2 step 1 is
explicit that an unresolvable anchor is a `404` and *"never an empty payload"*,
and it matters more for an INSTRUMENT than for an identity: a `facility_id` has
no external registry behind it (§C.3), so an empty payload would read as "this
facility has no terms" — a claim about the world rather than about the request.

**THE SEVEN CANONICAL REGIONS ARE HERE FROM THE FIRST COMMIT.** `cp-01` shipped
without them and four gate checks reported it for months; the regions are what
the published page's ``--8<--`` includes address, so a tree that publishes
snippets and carries no regions has a page with nothing to include.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.artifacts import ProductClassDeclaration
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
    """What this spine asks a deployment to supply.

    Structural, never inherited: `deployment.py` satisfies this by having the
    members, not by importing anything from here. That is what keeps the
    dependency pointing one way — the spine knows the SHAPE of a deployment's
    answers and nothing about this particular product.
    """

    @property
    def envelopes(self) -> Sequence[SignalEnvelope]: ...

    @property
    def request(self) -> ProductRequest: ...

    @property
    def request_contract(self) -> ProductRequestContract: ...

    @property
    def request_contract_key(self) -> str: ...

    @property
    def product_class(self) -> ProductClassDeclaration: ...

    @property
    def perspective(self) -> Any: ...

    @property
    def operator_parameters(self) -> Mapping[str, Any]: ...

    @property
    def policy_bundle_key(self) -> str: ...

    @property
    def plan_id(self) -> str: ...

    @property
    def temporal_boundary(self) -> datetime: ...

    @property
    def now(self) -> datetime: ...

    @property
    def expires_at(self) -> datetime: ...

    @property
    def max_ttl_seconds(self) -> int: ...

    @property
    def replay_record_class(self) -> str: ...

    @property
    def query_pin_class(self) -> str: ...

    @property
    def artifact_store_dirname(self) -> str: ...

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question actually assembled (whitepaper §7.7).

        A method, and it takes the view, because debt is MEASURED against the
        assembly rather than declared beside it.
        """


@dataclass(frozen=True)
class AnchorUnresolvable:
    """§D.2 step 1's fail-closed refusal — `404`, never an empty payload.

    Returned as DATA, so a caller renders it rather than catching it. The
    distinction the specification draws is worth keeping in the type system:
    *no such entity* and *an entity with nothing in it* are different answers,
    and a product that returns the second for the first has told the caller
    something false about the world.
    """

    anchor: str
    status: int = 404
    reason: str = "anchor-unresolvable"


@dataclass(frozen=True)
class Assembled:
    """What one run produced, for a caller to inspect.

    The spine *returns* its state rather than checking it, so the assertions
    can live where a test runner will actually run them.

    :attr:`view` is the composed graph state Π ran over — the last readable
    evidence that the write path executed at all, and an empty one is what a
    mis-set boundary produces. :attr:`gated` is the
    :class:`~ccf.products.gates.ServableProduct` itself rather than only the
    contract inside it: the type is not constructible outside
    :func:`~ccf.products.gates.run_gates`, so holding one is direct evidence the
    gates ran.
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
    read: Callable[[BootedFabric, ProductRequest], Scenario | None],
    plan_class: Callable[..., ProjectionPlan],
    request: ProductRequest,
    root: Path,
    unsupported: Mapping[str, str] | None = None,
) -> Assembled | ProductRequestViolation | AnchorUnresolvable:
    """Answer one question, end to end, against ``root`` as scratch space."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot. The single
    #    `ccf_config.yaml` names every section in force, `load_config_and_boot`
    #    derives and parses all of them, registers the `role: register` ones,
    #    and boots on the resulting pins. Connection values arrive HERE, from
    #    the caller — never from the config, which declares the backend as a
    #    KIND only.
    booted = load_config_and_boot(config, registry=registry, connection=connection)
    # --8<-- [end:boot]
    try:
        # The one line that crosses the deployment seam: the deployment names
        # its own artifact keys and hands back this question's values.
        #
        # `None` means the anchor resolved to nothing. §D.2 step 1 makes that a
        # 404 BEFORE the graph is touched — there is no ingest, no view and no
        # projection for an entity that does not exist, and inventing an empty
        # one to keep a happy path alive is the defect this branch prevents.
        scenario = read(booted, request)
        if scenario is None:
            return AnchorUnresolvable(anchor=request.subject)

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
        #    anywhere in this process (single-writer, CLAUDE.md §10,
        #    INV-CH7-10). The source estate this deployment READ from is not
        #    reachable from here at all: the fabric's write path leads into the
        #    fabric's own state and nowhere else.
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:ingest]

        # --8<-- [start:operators]
        # 3. The graph view at the boundary this deployment named.
        view = booted.handle.reader.as_of(
            tenant_id=booted.tenant_id, at=scenario.temporal_boundary
        )

        # 4. The L4 registry, built from WHATEVER parameter sets the deployment
        #    declared. This product declares ONE — `policy.principal-subgraph`,
        #    carrying the calling principal's expanded jurisdiction grant — and
        #    gets a one-operator registry. The operators are an aid to assembly,
        #    not a mandatory pipeline. The admitted policy-bundle version is
        #    looked up from the pins here, never written into any document.
        operators = build_operator_registry(
            parameters=scenario.operator_parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key=scenario.policy_bundle_key,
        )
        # --8<-- [end:operators]

        # --8<-- [start:project]
        # 5. Π at L5. The plan's required set comes from the product class's own
        #    document, so there is no second authored set to diverge from.
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
        #    call through the deployment rather than through the class.
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
        #    equality, IN BOTH DIRECTIONS, so a declared operator that did not
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
        # constructible outside `run_gates` (INV-CH7-52) — and the branch below
        # being REACHABLE is what makes that evidence rather than an assumption.
        #
        # THIS IS WHERE §F.4 FINDING 1 SURFACES, AND IT IS THIS PRODUCT'S
        # HEADLINE. `_refuse_ttl` requires `now < expires_at`, and `expires_at`
        # is the credit agreement's own effective date plus 90 days. Effective
        # dates span seven years across this estate, so 50 of the 60 facilities
        # land in the past and are refused on their first call — including all
        # 43 that carry an amendment history.
        #
        # The refusal is RAISED here rather than routed around, because the run
        # producing it is the evidence the finding is taken back with
        # (`FTS-G09`). Widening the window, or quietly re-anchoring on
        # `retrieved_at`, would make the numbers look healthy and retire the
        # primitive: that column carries ONE distinct value across all 60 rows,
        # so it would give every facility the same expiry (§E.5).
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
        # 8. Replay BEFORE delivery. `policy_bindings` is built here, by the
        #    adopter, because dimension 2 assembled by a rule nobody in the
        #    deployment wrote down is not an audit record.
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
        # 9. The record is persisted BEFORE the product is delivered, and
        #    delivery is what the successful append returns — no branch reaches
        #    a served product without a recorded decision (INV-CH7-79).
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
