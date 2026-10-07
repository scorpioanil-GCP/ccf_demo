"""Assemble one typed Context Product and serve it, end to end.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call an
adopter must make. There is **no domain vocabulary in it at all** — no table, no
column, no entity, no artifact key, no substrate, no parameter name, and no
number. Everything specific to *this* deployment lives in ``deployment.py``
beside it, and in ``artifacts/config/*.yaml`` beside that.

[ADAPT] nothing.

That separation is the point (phase 16 CONTEXT ``D-11``), and it answers a
reader's complaint in a reader's words: *"I can't tell from looking at the code
which code is example code and which code is required by the CCF."* The answer
is structural rather than editorial — two files, one per side.

**This is the production side of a second, different cut** (``D-IMPL-127``).
``consume.py`` is the client. Both halves run in one process here, and the
boundary is still a file boundary, because remoteness is a deployment fact and
not an architectural one. HW-2 replaces ``consume.py`` and nothing else.

**This spine IS the resolver.** :func:`~ccf.products.request.refuse_request`'s
own docstring says it is *"called by the deployment's own resolver, not by any
door"* (``D-IMPL-121``). That is the fact ``D-IMPL-133`` turns on, and it is why
this product class can declare a genuinely required parameter: validation lives
here, where the registered class is held, rather than at a door that never holds
one.

**The seven steps**, each wrapped in one of Phase 14 ``D-07``'s named marker
regions — these seven and no others:

======  ==========================================================
marker  what the fabric does
======  ==========================================================
boot    load the manifest, register what it puts in force, boot L2/L3
ingest  hand L1 envelopes to the one writer (single-writer, CLAUDE.md §10)
operators build the L4 registry from the parameter sets the deployment declared
project run Π at L5
gate    register the class and its request surface, run the three L6 gates
record  build the five-dimension Decision Replay record
serve   persist the record, then deliver (whitepaper §7.10)
======  ==========================================================

**What this spine deliberately does NOT carry**, each a real governance surface
that ``s1-01`` exercises and a first example does not need. Naming the absences
is what stops a reader concluding they do not exist:

* no ``debt_evidence`` — what the debt points at (``D-IMPL-118``);
* no ``source_refresh_recency`` — when the sources last published
  (``D-IMPL-112`` gap 2);
* no ``obligation_in_force`` — what the signal obliges the deployment to do
  (``D-IMPL-112`` gap 3);
* no ``refuse_operator_set_divergence`` — design E2's guard compares two
  independently authored operator sets, and this deployment authors one.

This file asserts nothing and prints nothing. Its assertions are in
``tests/examples/test_s1_00_output.py``; what a run prints is in ``consume.py``,
which carries no marker region, so no printed line is published-snippet surface.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ccf.erasure import erasure_index_at
from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.artifacts import (
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.products.contract import ContextProductContract
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope


class Scenario(Protocol):
    """What one run needs from the deployment's own artifacts.

    Every member is a *mechanism role* — never a domain value. The values behind
    them are read from ``artifacts/config/*.yaml`` by ``deployment.py``, which is
    the only place this deployment's vocabulary is written down. A Protocol, not
    a base class: the two modules import nothing from each other and are held
    together structurally (CLAUDE.md §11).
    """

    @property
    def envelopes(self) -> Sequence[SignalEnvelope]:
        """The L1 signal this run ingests."""

    @property
    def request(self) -> ProductRequest:
        """The question asked. Not an artifact — an argument."""

    @property
    def request_contract(self) -> ProductRequestContract:
        """The request surface the class declares (D-IMPL-98)."""

    @property
    def request_contract_key(self) -> str:
        """The Control Plane key the request contract registers under."""

    @property
    def product_class_key(self) -> str:
        """The config key the product class declaration is filed under."""

    @property
    def product_class(self) -> ProductClassDeclaration:
        """The Control Plane *claim*: what this product says produced it."""

    @property
    def perspective(self) -> PerspectiveArtifact:
        """The Π role-conditioning this product is served under."""

    @property
    def operator_parameters(self) -> Mapping[str, OperatorParametersArtifact]:
        """Manifest key → parsed operator-parameters artifact, one per category.

        **However many the deployment declared.** One entry yields a
        one-operator registry; this spine holds no fixed set of keys and never
        counts them (``D-IMPL-132``).
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
        """When this product stops being servable."""

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
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    operators_invoked: frozenset[str]
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
) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Five things the fabric asks a deployment to supply arrive as ordinary
    arguments — the same call shape the rest of the suite uses, so a reader
    moving from here to ``s1-01`` sees one shape rather than two.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the question is not one this class answers. A refusal is not an exception:
    a bad question is a bad question, not a broken deployment, and a verdict
    returned as a value cannot be swallowed by a bare ``except``.

    **The carrier is the envelope, not the violation** (``D-IMPL-311``).
    :class:`~ccf.products.request.ProductRequestViolation` is the internal
    producer/contract representation — what the door's comparison *found*;
    :class:`~ccf.products.refusal.RefusalEnvelope` is the canonical
    consumer-facing governed refusal — what a caller is *told*. Before
    canonical adoption this deployment returned the first because it performed
    the comparison itself and had nothing else to hand back. It now returns the
    second, which carries the same ``reason`` and ``key`` and additionally a
    ``replay_reference``: the refusal is recorded, so a consumer holding it can
    name the decision record that authorized saying no.
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the single
    #    `ccf_config.yaml` names every section in force, `load_config_and_boot`
    #    derives and parses all of them, registers the `role: register` ones,
    #    and boots on the resulting pins (`D-IMPL-136`'s AMENDMENT).
    #    Connection values arrive HERE, from the caller — never from the
    #    config, which declares the backend as a KIND only.
    booted = load_config_and_boot(manifest, registry=registry, connection=connection)
    # --8<-- [end:boot]
    try:
        # --8<-- [start:acquire]
        # 2. The one line that crosses the boundary this example is about: the
        #    deployment names its own config keys and hands back this question's
        #    values. Everything below reads those values and nothing else.
        #
        #    Then L1 -> L2. `booted.handle.worker` is the ONLY write handle to
        #    L3 anywhere in this process (single-writer, CLAUDE.md §10,
        #    INV-CH7-10); ingestion happens here rather than inside the resolver
        #    because `GovernedResolver` is handed a fabric already populated.
        scenario = read(booted, request)
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. The door, the graph view, the one operator, Π, the three L6 gates,
        #    the five-dimension record, the query pins, the persisted append and
        #    the delivery are ONE object the SDK owns. What is left here is this
        #    deployment's own seams: which config keys, which Π, which D_c.
        #
        #    Every argument is a NAME or a callable, never a value: the
        #    threshold, the curve, the boundary and the TTL ceiling all live in
        #    `ccf_config.yaml` and none of them is restated here (CLAUDE.md §6.4).
        #
        #    **Two arguments this deployment deliberately does NOT pass.** It
        #    names no `decision_instant_parameter`, because it reads the graph
        #    and stamps the decision at the same instant and says so by naming
        #    none — coincidence, not collapse (`D-IMPL-308`). And it declares no
        #    `source_refresh_recency`, because it never had one to declare; the
        #    SDK's empty window is the positive statement that this estate makes
        #    no such claim, not an omission.
        # Named functions rather than lambdas, on `cp-05`'s shape. A lambda is
        # unreadable to a static check, and `D-IMPL-137`'s demand — that the
        # Control Plane can see no second operator set was authored — is a
        # property something has to be able to READ off this tree. A named
        # factory whose only operator source is the `required` parameter makes
        # that provable rather than merely true.
        def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
            return plan_class(
                plan_id=scenario.plan_id, required=required, scenario=scenario
            )

        def debt_scorer(*, view: GraphView, evidence: object = None) -> DebtAssessment:
            return scenario.debt(view)

        store = FileArtifactStore(root=root / scenario.artifact_store_dirname)
        resolve = build_governed_resolver(
            fabric=booted,
            control_plane=registry,
            product_class_key=scenario.product_class_key,
            request_contract_key=scenario.request_contract_key,
            operator_parameter_keys=tuple(scenario.operator_parameters),
            policy_bundle_key=scenario.policy_bundle_key,
            # Π is deployment code and is never a rewrite target (whitepaper
            # §7.5). The factory's only operator source is the `required` the
            # SDK hands it: this deployment authors no operator set at all, so
            # there is nothing to diverge from and no divergence guard to call.
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
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
        )
        outcome = resolve(
            tenant=booted.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=request,
        )
        # --8<-- [end:govern]

        if not isinstance(outcome, ServedProduct):
            return outcome

        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=outcome.replay_ref.content_address)
        )
        return Assembled(
            tenant_id=booted.tenant_id,
            scenario=scenario,
            product=outcome.product,
            # From the RECORD's own account of the plan, never from the
            # product's lineage: the two are compared elsewhere, and sourcing
            # both from one object would compare a value with itself.
            operators_invoked=frozenset(
                record.content_generation_path.operator_plan
            ),
            record=record,
            served=outcome,
            store=store,
        )
    finally:
        booted.handle.close()
