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

from ccf.erasure import erasure_index_at
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DebtProfile,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, SourceRefreshRecency
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
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
        """The Control Plane key the request contract is registered under.

        **Not the manifest key.** This is the pin the class's governance
        document declares; :attr:`request_contract_artifact_key` below is the
        name the manifest files the artifact under, and the resolver resolves
        artifacts off the booted fabric, so it needs the second. Handed the
        first it refuses by name with the manifest's whole key list — a good
        refusal, and the reason the two are separate members rather than one.
        """

    @property
    def request_contract_artifact_key(self) -> str:
        """The MANIFEST key the request contract artifact is filed under."""

    @property
    def product_class_key(self) -> str:
        """The manifest key the product class declaration is filed under."""

    @property
    def debt_profile_key(self) -> str:
        """The manifest key this deployment's D_c bands are filed under.

        Naming it is the whole of wiring the obligation seam: the binding is
        authored in the artifact and the resolver reads it from there, so no
        band value is ever restated in code (CLAUDE.md §6.4).
        """

    @property
    def decision_instant_parameter(self) -> str:
        """Which request-contract argument carries this class's decision instant.

        ``D-IMPL-308``: the graph is read when the caller said and the answer
        is produced when the class says, and this names the second without
        restating its value. A class whose two instants coincide declares
        ``None`` here — a positive statement that they are the same moment,
        not an absence.
        """

    @property
    def source_refresh_recency(self) -> SourceRefreshRecency:
        """When this estate's sources last published, as the deployment declares it.

        ``D-IMPL-308`` / ``24.10-F-08``: declared evidence, because no operator
        can observe it, and carried inside the product's content address so a
        deployment cannot add it afterwards.
        """

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
    service_instant: datetime | None = None,
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
    #    registers them into the Control Plane and boots L2/L3 behind the
    #    single writer. The connection values come from the CALLER, never from
    #    the manifest — a connection string inside a content-hashed artifact
    #    would be persisted into the audit plane forever.
    booted = load_and_boot(manifest, registry=registry, connection=connection)
    # --8<-- [end:boot]

    try:
        # --8<-- [start:acquire]
        # 2. The deployment reads its own artifacts for THIS question and hands
        #    L1 its envelopes. `read` names every artifact key this deployment
        #    uses; nothing below names one. Ingestion goes through the worker
        #    because L2 is the only writer to the graph (CLAUDE.md §10), and it
        #    happens HERE rather than inside the resolver because
        #    `GovernedResolver` hands no envelope to the L1 writer — it is
        #    given a fabric that is already booted and already populated.
        scenario = read(booted, request)
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. Everything the seven-region spine used to perform by hand — the
        #    operator registry, the two-stage plan, the binder that holds the
        #    projection's authored operator set to the class's claim, the three
        #    L6 gates, the five-dimension record, the query pins, the persisted
        #    append and the delivery — is ONE object the SDK owns. What is left
        #    here is the deployment's own seams: which artifacts, which Π, which
        #    D_c, and the question.
        #
        #    Every argument below is a NAME, never a value. The bands live in
        #    `debt-profile.yaml`, the ceiling and the two instants in
        #    `product-governance.yaml`, the operator parameters in their four
        #    documents; this file restates none of them (CLAUDE.md §6.4).
        # The deployment's declaration of what its own mechanism writes and
        # under which kind (D-IMPL-353 §1.2): the two replay classes
        # `product-governance.yaml` names and the SDK's admitted-child class,
        # all `ReplayMint`. The resolver mints against this declaration and
        # refuses at construction if a class it files is missing; everything
        # undeclared stays the client lane.
        store = FileArtifactStore(
            root=root / scenario.artifact_store_dirname,
            write_kinds=WriteKinds.declare(
                {
                    scenario.replay_record_class: (ReplayMint,),
                    scenario.query_pin_class: (ReplayMint,),
                    ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,),
                }
            ),
        )
        resolve = build_governed_resolver(
            fabric=booted,
            control_plane=registry,
            product_class_key=scenario.product_class_key,
            # The MANIFEST key, not the class's declared pin: the resolver
            # resolves artifacts off the booted fabric. See `Scenario`.
            request_contract_key=scenario.request_contract_artifact_key,
            operator_parameter_keys=tuple(scenario.operator_parameters),
            policy_bundle_key=scenario.policy_bundle_key,
            debt_profile_key=scenario.debt_profile_key,
            # Π is deployment code and is never a rewrite target (whitepaper
            # §7.5). The fabric constructs it, so the binder can be shown the
            # object it binds — the plan arrives as a class, not ready-made.
            plan_factory=lambda *, required, request: plan_class(
                plan_id=scenario.plan_id, required=required, scenario=scenario
            ),
            debt_scorer=lambda *, view, evidence=None: scenario.debt(view),
            artifact_store=store,
            # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
            hitl_policy_key="hitl_policy",
            erasure_index=erasure_index_at(store.root),
            replay_record_class=scenario.replay_record_class,
            query_pin_class=scenario.query_pin_class,
            max_ttl_seconds=scenario.max_ttl_seconds,
            product_ttl_seconds=int(
                (scenario.expires_at - scenario.now).total_seconds()
            ),
            # `D-IMPL-308`: this class's decision instant is distinct from its
            # graph boundary, and naming the argument is the whole of the
            # wiring — the value travels on the request.
            decision_instant_parameter=scenario.decision_instant_parameter,
            source_refresh_recency=scenario.source_refresh_recency,
            # `D-IMPL-358` step 13. THE SERVE INSTANT, when the caller composed
            # one. The fabric judges a governed serve at this instant — Gate 3's
            # comparand and the temporal bound's — so a controlled historical
            # simulation has to be able to say what "now" is for the run it is
            # simulating. The seam is the SDK's own `admission_clock`.
            #
            # Passed ONLY when supplied: omitted, the SDK's process clock stands,
            # which is the right value for a deployment answering live questions.
            # This file invents no default and reads no clock itself — a default
            # here would be the spine deciding what time it is on a deployment's
            # behalf.
            #
            # The instant arrives as an ARGUMENT, never off `request`. A serve
            # instant taken from caller input would let any question move the
            # fabric's clock, which is the opposite of a trusted instant.
            **(
                {"admission_clock": lambda: service_instant}
                if service_instant is not None
                else {}
            ),
        )
        served = resolve(
            tenant=booted.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=request,
        )
        # --8<-- [end:govern]

        if not isinstance(served, ServedProduct):
            # A governed refusal is a value, not an exception — but this
            # example exists to show a product being served, so a refusal here
            # is a broken run rather than a demonstration. Named, so the
            # refusal's own reason reaches the reader instead of an
            # AttributeError three frames later.
            raise RuntimeError(
                f"the governed resolver refused this question: {served!r}"
            )

        # The record is read back out of the store rather than kept from the
        # call, because that is what an auditor holding the product and nothing
        # else would do: the reference travels ON the product.
        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=served.replay_ref.content_address)
        )
        return Assembled(
            tenant_id=booted.tenant_id,
            scenario=scenario,
            product=served.product,
            # From the RECORD's own account of the plan, not from the product's
            # lineage — `tests/examples/test_s1_01_output.py` asserts the two
            # agree, and sourcing this from the lineage would make that
            # assertion compare a value with itself.
            operators_invoked=frozenset(
                record.content_generation_path.operator_plan
            ),
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()
