"""Who ultimately owns this company, and whose stake crosses the reporting threshold?

That is the question this program answers, and no record of any source system
states its answer. Ownership runs through intermediaries, so a real interest is
a sum over paths — what a party holds directly, plus its fraction of whatever
the companies it holds hold in turn — and the total appears in no document.
This program assembles the chain into a graph, aggregates across the hops,
applies the threshold the regime in force sets, and serves the result as a
typed, gated, replay-ready Context Product.

**The question is ASKED, not configured.** Which company and as of which
instant arrive on a typed :class:`~ccf.products.request.ProductRequest` the
caller hands in, validated at the door against the request surface the product
class declared (whitepaper §6.3 *Addressability*, D-IMPL-98). One class, any
company, any instant — which is the difference between the verb *aggregate* and
the verb *assemble*, and the reason this file takes a ``request`` argument.

**This file is the fabric's half of answering it.** [MECHANISM] The CCF call
spine — every line here is a fabric call an adopter must make. Which company,
at which instant, under which threshold, and which resolved class counts as a
natural person are none of its business.

[ADAPT] nothing. There is no domain vocabulary in this file: no entity class, no
source system, no identifier, no threshold, no policy version, no query and no
boundary. Everything specific to *this* deployment lives in ``deployment.py``
beside it, and in ``artifacts/*.yaml`` beside that.

That separation is the point of this example (phase 16 CONTEXT `D-11`). The
complaint it answers is a reader's, in a reader's words: *"I can't tell from
looking at the code which code is example code and which code is required by
the CCF."* The answer here is structural rather than editorial — two files, one
per side of the question, legible from the repository and not only from the
rendered site.

**The seven steps, in order.** Each is wrapped in one of Phase 14 `D-07`'s named
marker regions, and `D-11` adds no new marker vocabulary — these seven and no
others:

======  ==========================================================
marker  what the fabric does
======  ==========================================================
boot    load the manifest, register what it puts in force, boot L2/L3
ingest  hand L1 envelopes to the one writer (single-writer, CLAUDE.md §10)
operators build the four-category L4 registry at a named boundary
project bind the two authored operator sets, then run Π at L5
gate    register the product class and its request surface, refuse a
        question the class does not answer, run the three L6 gates
record  build the five-dimension Decision Replay record
serve   persist the question's bytes, persist the record, then deliver
        (whitepaper §7.10)
======  ==========================================================

**What the deployment supplies.** Five ordinary arguments to
:func:`assemble_and_serve` — the manifest, the connection values, the reader,
Π, and the question being asked — which is the call shape every other example
in this suite makes.
:class:`Scenario` below is a Protocol, not a base class: it is the list of
values the fabric reads off one run, stated as structure rather than as prose
(CLAUDE.md §11, *Prefer Protocols over inheritance*). ``deployment.py`` imports
nothing from this module and this module imports nothing from it — the two are
held together structurally, which is the same posture
:class:`ccf.projection.plan.ProjectionPlan` takes.

**Import discipline (A-1).** Every ``ccf.deployment`` import below is spelled
``from ccf.deployment import X`` — the package, never a submodule of it.
Submodule fully-qualified names such as ``ccf.deployment.manifest`` are
implementation detail, and an adopter's call site never names one.

This file asserts nothing and prints nothing. Its assertions live in
``tests/examples/test_s1_01_output.py``, where a test runner will run them; what
the run prints lives in ``report.py``, which carries no marker region, so no
printed line is published-snippet surface (`16-CONTEXT.md:392-397`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DebtProfile,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import (
    BootedFabric,
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
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
    refuse_request,
    request_seeds,
)
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from ccf.replay.serve import (
    QueryPinWriter,
    ReplayWriter,
    ServedProduct,
    serve,
)
from ccf.signal.envelope import SignalEnvelope


class Scenario(Protocol):
    """What one run needs from the deployment's own artifacts.

    Every member is a *mechanism role* — "the instant this decision is asked
    about", "the operator parameter set" — never a domain value. The values
    behind them are read from ``artifacts/*.yaml`` by ``deployment.py``, which
    is the only place this deployment's artifact keys are written down.
    """

    @property
    def envelopes(self) -> Sequence[SignalEnvelope]:
        """The L1 signal this run ingests."""

    @property
    def request(self) -> ProductRequest:
        """The question the caller asked. Not an artifact — an argument."""

    @property
    def request_contract(self) -> ProductRequestContract:
        """The request surface the product class declares (D-IMPL-98)."""

    @property
    def request_contract_key(self) -> str:
        """The Control Plane key the request contract is registered under."""

    @property
    def query_pin_class(self) -> str:
        """The artifact class the executed graph queries are persisted under."""

    @property
    def temporal_boundary(self) -> datetime:
        """The instant the graph is read at. Data, never a clock read.

        Read off :attr:`request` by the deployment, so replay feeds the
        recorded boundary back through this same path.
        """

    @property
    def now(self) -> datetime:
        """The decision instant TTL and replay are stamped against."""

    @property
    def expires_at(self) -> datetime:
        """When this product stops being servable — authored, not derived."""

    @property
    def operator_parameters(self) -> Mapping[str, OperatorParametersArtifact]:
        """Manifest key → parsed operator-parameters artifact, one per category."""

    @property
    def policy_bundle_key(self) -> str:
        """The Control Plane key whose pin becomes the admitted bundle version."""

    @property
    def similarity_index_version(self) -> str:
        """The version identity this deployment assigns its corpus (INV-CH7-27)."""

    @property
    def product_class(self) -> ProductClassDeclaration:
        """The Control Plane *claim*: what this product says produced it."""

    @property
    def plan_id(self) -> str:
        """The projection's identity, from the projection's OWN document."""

    @property
    def required_operator_keys(self) -> tuple[str, ...]:
        """The projection's OWN operator set, from its own document (design E2)."""

    @property
    def perspective(self) -> PerspectiveArtifact:
        """The Π role-conditioning this product is served under."""

    @property
    def max_ttl_seconds(self) -> int:
        """The class's TTL ceiling. Registering it is what mints its pin."""

    @property
    def replay_record_class(self) -> str:
        """The artifact class the replay writer stores the record under."""

    @property
    def artifact_store_dirname(self) -> str:
        """Where under the run root the file-backed ArtifactStore lives."""

    @property
    def artifacts(self) -> Mapping[str, CCFContract]:
        """Every artifact the manifest named, parsed, under its own key."""

    @property
    def debt_profile(self) -> DebtProfile:
        """The resolved, version-pinned CAR calibration for this class.

        Read for two things and only two: the risk-sensitivity multiplier the
        freshness scorer runs under, and — since gap 3 — the obligation this
        deployment bound to whichever routing state the assessment lands in.
        Both are declared in ``artifacts/debt-profile.yaml``. The artifact is
        already resolved and pinned by the time it arrives here, so nothing on
        this path ever reaches the Control Plane for a "latest" (D-IMPL-26).
        """

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question actually assembled (whitepaper §7.7).

        A method rather than a property, and it takes the view, because debt is
        MEASURED against the assembly rather than declared beside it. What
        counts as an observation, what a complete assembly holds, and which
        factors a declared scorer produced are the deployment's answers; the
        curve, the scorer and the CAR bands are the SDK's.
        """


@dataclass(frozen=True)
class Assembled:
    """What one run of the spine produced, for a caller to inspect.

    The spine *returns* its state rather than checking it, so that
    ``tests/examples/test_s1_01_output.py`` can hold the assertions where a test
    runner will actually run them.
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    operators_invoked: tuple[str, ...]
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *,
    manifest: Path,
    connection: Mapping[str, object],
    read: Callable[[BootedFabric, ProductRequest], Scenario],
    plan_class: Callable[..., ProjectionPlan],
    request: ProductRequest,
    root: Path,
) -> Assembled:
    """Answer one question, end to end, against ``root`` as its scratch directory.

    The five things the fabric asks a deployment to supply arrive as ordinary
    arguments, and each is one line of the caller's wiring:

    ``manifest``
        The one document naming every artifact in force.
    ``connection``
        Substrate connection values, supplied by the CALLER, never by the
        manifest — a connection string in a content-hashed artifact would be
        persisted into the audit plane forever.
    ``read``
        Names the deployment's own artifact keys and reads the values for THIS
        question — including the two instants, which it takes off ``request``
        rather than off any document.
    ``request``
        The question: which entity, for what decision, under what temporal
        requirement, as of when (whitepaper §6.3 *Addressability*). Validated
        against the class's declared request contract before anything is
        assembled, so a malformed question is refused rather than answered
        approximately.
    ``plan_class``
        Π, as a class the fabric constructs rather than an object it is handed.
        A projection is deployment code and is never a rewrite target
        (whitepaper §7.5) — but it is CONSTRUCTED in the ``project`` region
        below, one statement before the binder, because the statement that binds
        its authored operator set to the product class's claim has to be able to
        see the object it binds (design E2, D-IMPL-86 as corrected 2026-08-05).
        A plan handed over ready-made is a plan no binder can be shown to have
        been given.
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    #    Connection values arrive HERE, from the caller — never from the
    #    manifest, which declares the backend as a KIND only.
    booted = load_and_boot(
        manifest,
        registry=registry,
        connection=connection,
    )
    # --8<-- [end:boot]
    try:
        # The one line that crosses the boundary this example is about: the
        # deployment names its own artifact keys and hands back this question's
        # values. Everything below reads those values and nothing else.
        scenario = read(booted, request)

        # The door: is this a question this class answers? Checked BEFORE the
        # graph is touched, because a malformed question deserves a refusal and
        # not an approximate answer. The verdict is a RETURNED VALUE rather than
        # a raised exception — a bad question is a bad question, not a broken
        # deployment, and a refusal returned as data cannot be swallowed by a
        # bare `except`. Nothing about the caller's identity is on the request:
        # role and tenant are things a door ESTABLISHES from a verified grant,
        # never things a request CLAIMS (D-IMPL-98, plan `15.5-06`).
        match refuse_request(
            request=scenario.request, declared=scenario.request_contract
        ):
            case None:
                pass
            case violation:
                raise RuntimeError(
                    f"the request surface refused this question: {violation}"
                )

        # --8<-- [start:ingest]
        # 2. L1 → L2. `booted.handle.worker` is the ONLY write handle to L3 that
        #    exists anywhere in this process; nothing else in either module holds
        #    one, and nothing can obtain one (single-writer, CLAUDE.md §10,
        #    INV-CH7-10).
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:ingest]

        # --8<-- [start:operators]
        # 3. The graph view at the temporal boundary this deployment named.
        #    Which boundary a decision is asked at is a deployment decision, so
        #    it stays an explicit line here.
        view = booted.handle.reader.as_of(
            tenant_id=booted.tenant_id, at=scenario.temporal_boundary
        )

        # 4. The four-category operator chain (L4), built from the deployment's
        #    parameter artifacts. The view is in the signature because the
        #    similarity corpus is read out of the graph at the boundary above,
        #    never lazily at first invocation.
        operators = build_operator_registry(
            parameters=scenario.operator_parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key=scenario.policy_bundle_key,
            similarity_index_version=scenario.similarity_index_version,
        )
        # --8<-- [end:operators]

        # --8<-- [start:project]
        # 5. Project (L5). The plan's `required` comes from the projection's OWN
        #    `projection-requirements.yaml`; the product class's
        #    `required_operator_keys` is the separate authored document. The
        #    binder call between the two lines below is where a disagreement
        #    between them fails: before anything is assembled, by refusal rather
        #    than repair (design E2, D-IMPL-86).
        #
        #    The plan is a named local rather than an argument expression for
        #    exactly that reason — the binder has to be handed the same object
        #    the engine will run.
        plan = plan_class(
            plan_id=scenario.plan_id,
            required=scenario.required_operator_keys,
            scenario=scenario,
        )
        refuse_operator_set_divergence(declared=scenario.product_class, plan=plan)
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=plan,
            perspective=scenario.perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=scenario.temporal_boundary,
            # WHERE THE WALK BEGINS IS PART OF THE QUESTION (D-IMPL-111 limb
            # (a)). The request's subject is the entity anchor of the
            # whitepaper's address pattern, so it seeds the traversal — which
            # is what puts the *subject* inside the compiled graph query and
            # therefore inside the pins replay dimension 5 records. Before
            # this, two questions about two different companies pinned
            # identically (`DI-15.5-07`). Derived through the SDK's one
            # reading, the same one replay derives it through.
            seeds=request_seeds(scenario.request),
        )
        # --8<-- [end:project]

        # --8<-- [start:gate]
        # 6. L6 — and this cluster stays in adopter code deliberately.
        #
        #    Gate 3 compares the class's TTL CEILING against this product's own
        #    `expires_at`. That is only a check while the two are independently
        #    authored. Registering the MaxTTL value here is what MINTS
        #    `max_ttl_version` — the pin is a content hash of what was
        #    registered, which is why the product-class artifact cannot declare
        #    it. A helper that minted the pin and stamped the product would be
        #    comparing a value against itself, so the SDK ships no such helper.
        declared = scenario.product_class
        max_ttl_version = registry.register(
            declared.max_ttl_key, MaxTTL(seconds=scenario.max_ttl_seconds)
        )
        #    The class's REQUEST SURFACE is registered on the same discipline,
        #    and for the same reason: the pin is a content hash of what was
        #    registered, so the contract document cannot declare it.
        #    `register_product_class` resolves the pin and refuses a contract
        #    declared for another class or another lane — a mis-wiring no shape
        #    comparison could see (D-IMPL-98). The question itself was already
        #    refused-or-admitted against this same contract, above, before the
        #    graph was touched.
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

        # 7. The lineage the product CLAIMS, and the gates.
        #
        #    `operators_invoked` is filled from the product-class DECLARATION —
        #    the Control Plane's statement of what this product was computed by
        #    — and never from `execution`. A claim copied out of the execution
        #    record is not a claim, it is a transcript (D-IMPL-86).
        #
        #    What Gate 2 then verifies is ASSEMBLY-PATH INTEGRITY: the claim
        #    transcribed into this Contract equals the engine's execution of the
        #    plan. The engine is a faithful TRANSCRIBER of the plan rather than
        #    an independent witness of it — it builds `operators_invoked` and
        #    `steps` in one loop over the same operator plan, so there is no
        #    return path where invoked != planned. Gate 2 therefore does not
        #    catch a producer misdeclaring. Authorable drift fails upstream
        #    instead, at the binder call in step 5.
        policy_version = booted.pins.version_for(scenario.policy_bundle_key)
        # Measured ONCE, then used twice. The obligation the deployment declared
        # answers to the routing state THIS assessment landed in, so resolving
        # it from a second `scenario.debt(...)` call would risk binding the
        # obligation of a signal the delivered product does not carry.
        assessment = scenario.debt(execution.view)
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
            # HOW MUCH TO TRUST THE ANSWER, delivered WITH the answer
            # (D-IMPL-100). D_c *"is a runtime signal the agent must consume as
            # a first-class decision input, not a log-line to be read after the
            # fact"* (`docs/CCF_Whitepaper_1-2.md:2696`), so it rides the vessel
            # and is inside the product's content address — a delivered debt an
            # auditor could not reconstruct would be a claim rather than a
            # measurement. Measured against `execution.view`: what the
            # operators actually left standing, not what the artifacts hoped
            # for.
            debt=assessment,
            # WHAT THE DEBT POINTS AT, beside the debt rather than inside it
            # (D-IMPL-118 `qa-toplevel`) — so it is in the product's content
            # address on its own account, and dimension 5 carries a matching
            # member that every `rehydrate_product` reads back.
            #
            # This deployment emits NOTHING into it, and that is a ruling
            # rather than an oversight: D-IMPL-119 limb 3(b), *"omit evidence
            # pointers entirely until a later phase adds principal scoping to
            # the assembly path"*. `KycScenario.debt_evidence` carries the full
            # reasoning and is the one place a later phase edits.
            debt_evidence=scenario.debt_evidence(execution.view),
            # WHEN THE SOURCES LAST PUBLISHED, beside the freshness factor it
            # is deliberately not (D-IMPL-112 gap 2, D-IMPL-117), under the
            # same `qa-toplevel` placement D-IMPL-118 ruled for all three Track
            # B members.
            #
            # DECLARED by the deployment rather than measured off the view —
            # which is why this reads a scenario attribute where the two lines
            # above call a method taking `execution.view`. `debt.factors
            # .freshness` is a number the fabric computed about its own decay;
            # this is a fact about the world upstream, and the fabric has no
            # way to observe it. `artifacts/product-governance.yaml` is where
            # it is authored and where an adopter changes it.
            #
            # AND IT NAMES NO SOURCE (D-IMPL-124). The artifact declares three
            # per-source entries with human-interpretable references;
            # `deployment.py::_declared_refresh_window` reduced them to the
            # window they span before this line ever saw a value, so what goes
            # on the product is two instants — no reference, no count. The
            # boundary is in the deployment and not in the SDK because only the
            # deployment knows its own set of sources is complete.
            source_refresh_recency=scenario.source_refresh_recency,
            # WHAT THE SIGNAL OBLIGES THIS DEPLOYMENT TO DO, under the same
            # `qa-toplevel` placement again (D-IMPL-112 gap 3, D-IMPL-117,
            # D-IMPL-118).
            #
            # The SDK carried the binding mechanism and NOT ONE WORD of the
            # vocabulary: `artifacts/debt-profile.yaml` is where a KYC
            # deployment says what Forced-LLM and Fail-Closed require of it, and
            # `DebtProfile.obligation_for` is the whole of what the fabric
            # supplies. Nothing in CCF reads this string and acts on it —
            # acting on it would mean the SDK had chosen the vocabulary.
            #
            # Resolved for the signal THIS assessment carries, so the delivered
            # product records what this decision was obliged to do rather than
            # the whole calibration. It is inside the content address, so the
            # replay engine reproduces the obligation in force at decision time
            # even if this artifact is rebound tomorrow (D-IMPL-26).
            obligation_in_force=scenario.debt_profile.obligation_for(
                assessment.signal
            ),
        )
        # A refusal is not a thing to proceed past: `ServableProduct` is not
        # constructible outside `run_gates`, so holding one IS the evidence the
        # gates ran (INV-CH7-52).
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
        # Replay before delivery. `policy_bindings` is built here, from the pins
        # the adopter reads off `BootedFabric.pins`: which bindings are in force
        # stays a deployment statement, because dimension 2 assembled by a rule
        # nobody in the deployment wrote down is not an audit record.
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=scenario.perspective,
            policy_bindings=(
                PolicyBinding(
                    key=scenario.policy_bundle_key, version=policy_version
                ),
            ),
            assembly_mode=declared.assembly_mode,
            recorded_at=scenario.now,
            # WHICH QUESTION THIS DECISION ANSWERED, in the record itself
            # (D-IMPL-111 limb (b)). The pins below say what was asked of the
            # GRAPH; this says what was asked of the PRODUCT — subject, intent,
            # freshness and the instant it was asked as of. `intent` and
            # `freshness` are in no other dimension, and replay reads the
            # subject back off this field to re-seed the traversal, so the
            # record is what makes the decision reproducible rather than
            # merely described.
            request=scenario.request,
            # WHETHER THE QUESTION'S PARAMETERS WERE RESOLVED, stated
            # POSITIVELY (D-IMPL-264 D-09/D-10). This spine runs no resolution
            # step: it has no policy-constraint resolver, applies no class
            # default and folds no caller override, so the honest value is the
            # marker with its reason and not a resolution nobody performed.
            # Omitting the argument is a `TypeError` by design — a record that
            # cannot say whether resolution ran is an integrity failure rather
            # than a terse record.
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        )
        # --8<-- [end:record]

        # --8<-- [start:serve]
        # The record is persisted BEFORE the product is delivered, and delivery
        # is what the successful append returns — there is no branch that
        # reaches a served product without a recorded decision (INV-CH7-79).
        #
        # WHICH QUESTION THIS DECISION ANSWERED IS PINNED, not described. The
        # record's `graph_query_sequence` is one content hash per graph query
        # the engine actually issued; handing `serve` the queries themselves,
        # with a writer to persist them, makes every pin RESOLVABLE — the
        # canonical bytes land in the store BEFORE the record is appended, so
        # no moment exists at which a recorded pin dangles (T-15.2-28). Without
        # the writer the pins are still recorded and nothing can resolve them,
        # which is the repudiation gap this example closed (plan `15.5-13`; the
        # mechanism is plan `15.2-08`'s and had never been exercised).
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
            operators_invoked=execution.operators_invoked,
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()
