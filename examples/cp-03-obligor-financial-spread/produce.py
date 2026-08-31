"""The spine — one question, end to end, for `credit-risk.spread`.

[MECHANISM] everything below the deployment seam. [ADAPT] nothing here: this
module names no obligor, no tag, no table, no ratio and no threshold. Every
value it works with arrives from `deployment.py`, which interprets the
documents beside it.

**The nine numbered steps are the specification's §D.2 read as code**, and the
ordering is not a convenience. `Policy` runs before anything reads graph state
(§D.3 step 2, composition invariant 1), the replay record is written before the
product is delivered (INV-CH7-79), and `ServableProduct` is not constructible
outside `run_gates` — so holding one IS the evidence the gates ran, rather than
a claim that they did.

**WHAT THIS RUNG ADDS TO THE SHAPE RUNGS 01 AND 02 ESTABLISHED.** One thing,
and it is visible in a signature rather than in a comment: :meth:`Scenario.debt`
takes **no view**. At rungs 01 and 02 the debt reading was measured over the
composed graph view, because those products carry one entity whose freshness is
one date. This product's freshness is not one date. The graph entity carries
*counts* — how many periods, how many peers — while every period keeps its own
`filed_date`, and §E.1's two decay rates are computed from those. So the
measurement's subject is the scenario, and the argument that would have pointed
at the view is absent because there is nothing in the view to measure. **§A's
claim that temporal validity is an ATTRIBUTE-level property is the reason this
method has a different arity from its neighbors'.**

**TWO REFUSALS ARE RETURNED AS DATA rather than raised.** A question this class
does not answer is a `ProductRequestViolation`; an anchor that resolves to no
obligor — or to an obligor with no facts — is an :class:`AnchorUnresolvable`.
Neither is an exception, because a bad question and a missing obligor are not
broken deployments, and a verdict returned as a value cannot be swallowed by a
bare `except`. §D.2 step 1 makes the unresolvable anchor a `404` and step 3
makes *"the obligor has no facts"* the same `404`: an empty spread is not a
spread of nothing, it is the absence of an answer, and serving `{}` would tell
the caller this company filed no financials.

**THE SEVEN CANONICAL REGIONS ARE THE PUBLISHED SNIPPET SURFACE.** They are
what the documentation page's ``--8<--`` includes address, and they are opened
in the order the fabric is called in — `boot`, `ingest`, `operators`, `project`,
`gate`, `record`, `serve`. Step 3 fills the stub's regions; it does not
renumber them.
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
from ccf.halflife.assessment import DebtAssessment
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

    def debt(self) -> DebtAssessment:
        """D_c over what this question actually assembled (whitepaper §7.7).

        **A method taking NOTHING, where rungs 01 and 02 took the view.** Debt
        is still MEASURED rather than declared — but what it is measured over
        is this product's per-period filing dates, and those are not in the
        graph. The entity L2 admitted carries `spread_periods` and
        `peer_comparison` as COUNTS; the dates each column decays from live on
        the scenario's periods. Handing this method a view would offer it
        something it must not read, and a measurement that reads the wrong
        subject is §E.1's finding rather than its demonstration.
        """


@dataclass(frozen=True)
class AnchorUnresolvable:
    """§D.2 steps 1 and 3's fail-closed refusal — `404`, never an empty payload.

    Returned as DATA, so a caller renders it rather than catching it.

    **Two conditions, one refusal, and collapsing them is deliberate.** The
    anchor may name no obligor at all, or it may name one this estate holds no
    facts for. §D.2 makes both a `404` because the distinction the caller could
    draw from separate answers is not one this product is willing to disclose:
    an LEI probe that could tell *no such obligor* from *an obligor with
    nothing filed* is an enumeration surface over the estate's coverage.

    **And an empty payload would be a false statement rather than a thin one.**
    A spread with no lines reads as *this company reported no financials*,
    which is a claim about the world. The absence of an answer is not an answer
    of zero — the same distinction §C.4 trap 5 draws inside the payload, drawn
    here at the payload's edge.
    """

    anchor: str
    status: int = 404
    reason: str = "anchor-unresolvable"


@dataclass(frozen=True)
class ParameterNotSupported:
    """Standard §2.4's declared-but-inert refusal — `400`, returned as data.

    *"A parameter that appears to work and does not will be relied on in a
    dispute."* The parameter IS part of the uniform surface — it is declared in
    the request contract, so a caller can discover it — and it fails explicitly
    rather than succeeding silently against current state. Those are the two
    halves of §2.4 and neither works without the other: an absent parameter
    tells a caller nothing, and a silently-ignored one tells them something
    false.

    **`as_of` is the one this tier declares and refuses** (§B.5, gate
    `OFS-G06`), and the pressure on it is real rather than theoretical. This
    product's whole subject is that figures change across filings, so *"give me
    the spread as it stood last March"* is the first question a credit officer
    thinks of after seeing `basis` work. It needs ledger time-travel and
    arrives at Tier 3. Answering it with today's spread would be the most
    plausible wrong answer this product could give.
    """

    parameter: str
    reason: str
    status: int = 400


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
    :func:`~ccf.products.gates.run_gates`, so holding one is direct evidence
    the gates ran.
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
) -> Assembled | ProductRequestViolation | AnchorUnresolvable | ParameterNotSupported:
    """Answer one question, end to end, against ``root`` as scratch space."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot. The single
    #    `ccf_config.yaml` names every section in force, `load_config_and_boot`
    #    derives and parses all of them, registers the `role: register` ones,
    #    and boots on the resulting pins. Connection values arrive HERE, from
    #    the caller — never from the config, which declares the backend as a
    #    KIND only. A DSN inside a content-hashed artifact is a DSN persisted
    #    into the audit plane forever.
    booted = load_config_and_boot(config, registry=registry, connection=connection)
    # --8<-- [end:boot]
    try:
        # The one line that crosses the deployment seam: the deployment names
        # its own artifact keys, reads its own store, and hands back this
        # question's values.
        #
        # `None` means the anchor resolved to nothing, or to an obligor this
        # estate holds no facts for. §D.2 makes both a 404 BEFORE the graph is
        # touched — there is no ingest, no view and no projection for a spread
        # that does not exist, and inventing an empty one to keep a happy path
        # alive is the defect this branch prevents.
        scenario = read(booted, request)
        if scenario is None:
            return AnchorUnresolvable(anchor=request.subject)

        # THE DOOR, and this spine is the RESOLVER standing at it. Checked
        # before the graph is touched, so a question this class does not answer
        # costs nothing and returns a reason rather than an approximation.
        # `intent` and `debt_tolerance` are REQUIRED with no default (§B.4), so
        # a request omitting either is refused here as data.
        violation = refuse_request(
            request=scenario.request, declared=scenario.request_contract
        )
        if violation is not None:
            return violation

        # DECLARED BUT INERT — Standard §2.4, checked at the door and BEFORE
        # the graph is touched. The set comes from the deployment's own request
        # contract, so this branch names no parameter of its own — a parameter
        # this tier stops refusing, or starts, is an edit to `ccf_config.yaml`.
        for name, reason in (unsupported or {}).items():
            if name in request.parameters:
                return ParameterNotSupported(parameter=name, reason=reason)

        # --8<-- [start:ingest]
        # 2. L1 → L2. `booted.handle.worker` is the ONLY write handle to L3
        #    anywhere in this process (single-writer, CLAUDE.md §10,
        #    INV-CH7-10). The Postgres estate this deployment READ from is not
        #    reachable from here at all: the fabric's write path leads into the
        #    fabric's own state and nowhere else.
        #
        #    ONE ENVELOPE, and `deployment.source_read` says why at length. The
        #    obvious alternative — one envelope per signal class so annual and
        #    quarterly facts carry their own `observed_time` — does not survive
        #    contact with L2: all of them share this product's single
        #    `match_key`, so the idempotent upsert merges them into one entity
        #    and the last write wins.
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:ingest]

        # --8<-- [start:operators]
        # 3. The graph view at the boundary this deployment named — the
        #    request's own `asked_at`, never a clock, so replay feeds the same
        #    instant back through the same code path.
        view = booted.handle.reader.as_of(
            tenant_id=booted.tenant_id, at=scenario.temporal_boundary
        )

        # 4. The L4 registry, built from WHATEVER parameter sets the deployment
        #    declared. This product declares ONE — `policy.principal-subgraph`,
        #    carrying the calling principal's EXPANDED jurisdiction grant — and
        #    gets a one-operator registry. `OFS-G10` asserts the count is
        #    exactly one and that nothing named `Enrich` is registered: §D.2.1
        #    ruled the attribute batch-select to be L2 assembly rather than an
        #    operator, because `Enrich` does not exist in `src/` and forcing it
        #    into one of the four canonical categories would make the lineage
        #    record say something untrue. If the eight-member vocabulary is
        #    later adopted, that gate turns RED — and the redness is the signal
        #    to reopen the question, not a regression.
        #
        #    The admitted policy-bundle version is looked up from the pins
        #    here, never written into any document.
        operators = build_operator_registry(
            parameters=scenario.operator_parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key=scenario.policy_bundle_key,
        )
        # --8<-- [end:operators]

        # --8<-- [start:project]
        # 5. Π at L5. The plan's required set comes from the product class's
        #    own document, so there is no second authored set to diverge from.
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

        # 7. The lineage the product CLAIMS — filled from the DECLARATION,
        #    never from `execution`. A claim copied out of the execution record
        #    is not a claim, it is a transcript. Gate 2 then holds the two to
        #    strict equality, IN BOTH DIRECTIONS, so a declared operator that
        #    did not run and an operator that ran undeclared are both refusals.
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
            # therefore inside its content address. Measured over the periods
            # this question assembled — two decay rates at once where the
            # spread mixes an annual with a current quarter.
            debt=scenario.debt(),
        )
        # A refusal is not a thing to proceed past. `ServableProduct` is not
        # constructible outside `run_gates` (INV-CH7-52) — and the branch below
        # being REACHABLE is what makes that evidence rather than an assumption.
        #
        # `ttl-bounds` REFUSES 27 OF THE 50 OBLIGORS IN THIS ESTATE, and the
        # refusal is raised rather than routed around. The expiry is the
        # payload's latest `filed_date` plus the declared window, so an obligor
        # whose last filing predates that window has a spread that has expired
        # — which is the correct answer about a company that stopped filing.
        #
        # §E.1.1 IS WHY THIS RUNG AND RUNG 02 ARE READ TOGETHER. Rung 02
        # anchors on a credit agreement's effective date, which can never
        # advance, and refuses 50 of 60 PERMANENTLY. This rung anchors on
        # `filed_date`, which moves every quarter, so its 27 refusals CLEAR AS
        # FILERS FILE. Same primitive, opposite behavior, and the difference is
        # entirely whether the anchored field is re-observed. Widening the
        # window here, or quietly re-anchoring on `asked_at`, would make the
        # numbers look healthy and retire the primitive — `OFS-G09` is the gate
        # that turns RED if anyone does.
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
        #
        #    THE RESTATEMENT IS WHAT MAKES REPLAY FALSIFIABLE HERE (§D.5). A
        #    replayed decision over a since-restated period must reproduce the
        #    figure AS IT STOOD at decision time, not today's. Rungs 01 and 02
        #    had to record that fixture as needing an estate condition nobody
        #    had supplied; this estate holds 321 of them.
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
            # including `basis`, so replay re-asks the same question rather
            # than a similar one. Two `basis` values over a restated obligor
            # are two different answers and `OFS-G11` holds them to two
            # different content addresses.
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
