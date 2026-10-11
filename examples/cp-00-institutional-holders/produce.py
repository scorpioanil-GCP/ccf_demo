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

AMENDED 2026-10-11 — compatibility repair (Dave, ruling 3 of 2026-10-11 16:23
MST; ``examples/AMENDMENTS-2026-10-11.md``). Everything above describes the
spine as it was frozen, and is kept as that record. The hand-composed half of
it — registering the MaxTTL and the request contract, running the gates,
building the record, constructing the replay and query-pin writers — no longer
exists on the SDK's surface: since ``D-IMPL-353``/``D-IMPL-354`` a Control
Plane registration or a replay write needs a capability only an SDK
composition root can mint. So steps 3–7 now run inside the SDK's
:func:`~ccf.products.resolver.build_governed_resolver`, which registers the
class from this deployment's declarations, executes the same declared
operators, Π, the three L6 gates and the five-dimension record, and serves.
The marker regions follow the SDK's canonical shape (``D-IMPL-306``): ``boot``
is unchanged; ``acquire`` is the old ``ingest`` with the deployment's read and
the request check before it; ``govern`` hands the resolver the same Π and the
same D_c this deployment always computed, composes it, and asks it the
question. The resolver owns ``gate``, ``record`` and ``serve``, so this module
no longer publishes regions by those names. The question, the operators, the
threshold, the TTL, the debt arithmetic and the payload are the deployment's,
unchanged. The original text of this file is in git at the specimen's
branch point.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.controlplane.artifacts import (
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.erasure import ErasureTrust, erasure_index_at
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.contract import ContextProductContract
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    refuse_request,
)
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
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
    def product_class_key(self) -> str:
        """The placed key the product class declaration is filed under.

        AMENDED 2026-10-11: the governed resolver resolves the class off the
        booted fabric by this key.
        """

    @property
    def half_life_key(self) -> str:
        """The placed key of this deployment's λ_c table.

        AMENDED 2026-10-11: the clock the ``from_entity_freshness`` expiry runs
        from (``decay_basis: valid-from``), named once.
        """

    @property
    def ttl_seconds(self) -> int:
        """The declared product lifetime, from ``artifacts/ttl.yaml``."""

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

    :attr:`gated` was the :class:`~ccf.products.gates.ServableProduct` itself (AMENDED 2026-10-11: now the resolver's ``ServedProduct``; see the field)
    rather than only the contract inside it. The type is not constructible
    outside :func:`~ccf.products.gates.run_gates`, so holding one is direct
    evidence the gates ran; :attr:`product` alone would leave that evidence
    reachable only by inference from the fact that delivery happened.
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    #: AMENDED 2026-10-11: the resolver's delivery. ``ServableProduct`` is no
    #: longer handed to a deployment: the gates run inside the SDK's resolver,
    #: whose only path to a ``ServedProduct`` is ``DeliveryCapability.deliver``
    #: over a ``ServableProduct`` after the record is appended — so holding this,
    #: with its record readable from the store, is the evidence the gates ran.
    gated: ServedProduct
    operators_invoked: frozenset[str]
    view: GraphView
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


class GovernedRefusal(RuntimeError):
    """The governed resolver refused a question this class otherwise answers.

    AMENDED 2026-10-11. Before the repair a gate refusal raised a bare
    ``RuntimeError`` from this module; the resolver now returns it as a
    :class:`~ccf.products.refusal.RefusalEnvelope`, carried here so a caller
    can read its reason and replay reference rather than a message about them.
    """

    def __init__(self, envelope: RefusalEnvelope) -> None:
        super().__init__(f"the governed resolver refused this question: {envelope!r}")
        self.envelope = envelope


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

    Raises:
        GovernedRefusal: the governed resolver refused a question that conforms
            to the request contract (AMENDED 2026-10-11).
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
        # --8<-- [start:acquire]
        # The one line that crosses the boundary this example is about: the
        # deployment names its own artifact keys and hands back this question's
        # values. Everything below reads those values and nothing else.
        scenario = read(booted, request)

        # THE DOOR's first check, kept here so a question this class does not
        # answer is still returned as a `ProductRequestViolation` before the
        # graph is touched. The resolver repeats it; the two read one contract.
        violation = refuse_request(
            request=scenario.request, declared=scenario.request_contract
        )
        if violation is not None:
            return violation

        # 2. L1 → L2. `booted.handle.worker` is the ONLY write handle to L3
        #    anywhere in this process; nothing else holds one and nothing can
        #    obtain one (single-writer, CLAUDE.md §10, INV-CH7-10). The source
        #    estate this deployment read from is not reachable from here at all:
        #    the fabric's write path leads into the fabric's own state and
        #    nowhere else.
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. Π at L5, constructed by the fabric from the `required` set the SDK
        #    hands it — the product class's own document — so there is no
        #    second authored operator set to diverge from. A NAMED function, so
        #    a static check can read that its only operator source is
        #    `required`. The D_c scorer is this deployment's own, measured over
        #    the view the operators left standing; the view is kept for the
        #    caller as the last readable evidence the write path executed.
        witnessed: dict[str, GraphView] = {}

        def plan_factory(
            *, required: tuple[str, ...], request: ProductRequest
        ) -> ProjectionPlan:
            return plan_class(
                plan_id=scenario.plan_id, required=required, scenario=scenario
            )

        def debt_scorer(*, view: GraphView, evidence: object = None) -> DebtAssessment:
            witnessed["view"] = view
            return scenario.debt(view)

        # 4. The governed resolver. It registers this class's MaxTTL and request
        #    surface from the deployment's declarations (a registration now
        #    needs a capability only an SDK composition root mints), builds the
        #    L4 registry from the declared parameter sets, runs Π, holds the
        #    claimed lineage to what ran (gate 2's strict equality), runs the
        #    three L6 gates, and builds the five-dimension record — all before
        #    anything is delivered. Every argument is a NAME or a declared
        #    number read from this deployment's artifacts, never a value
        #    written here. The store declares what the fabric's own writers
        #    file into it and under which kind (D-IMPL-353 §1.2).
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
            request_contract_key=scenario.request_contract_key,
            operator_parameter_keys=tuple(scenario.operator_parameters),
            policy_bundle_key=scenario.policy_bundle_key,
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
            # The λ_c table the `from_entity_freshness` expiry runs from.
            evidence_clock_key=scenario.half_life_key,
            artifact_store=store,
            # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
            erasure_trust=ErasureTrust(authorities={}),
            erasure_index=erasure_index_at(store.root),
            replay_record_class=scenario.replay_record_class,
            query_pin_class=scenario.query_pin_class,
            max_ttl_seconds=scenario.max_ttl_seconds,
            product_ttl_seconds=scenario.ttl_seconds,
        )

        # 5. Ask. The record is persisted BEFORE the product is delivered, and
        #    delivery is what the successful append returns — no branch reaches
        #    a served product without a recorded decision (INV-CH7-79). A
        #    refusal is a value; this specimen promises a served answer, so a
        #    refusal is raised by name with its envelope.
        served = resolve(
            tenant=booted.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=scenario.request,
        )
        if not isinstance(served, ServedProduct):
            raise GovernedRefusal(served)
        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=served.replay_ref.content_address)
        )
        # --8<-- [end:govern]

        return Assembled(
            tenant_id=booted.tenant_id,
            scenario=scenario,
            product=served.product,
            gated=served,
            # From the RECORD's own account of the plan, so a lineage check
            # against it compares two things rather than one with itself.
            operators_invoked=frozenset(record.content_generation_path.operator_plan),
            view=witnessed["view"],
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()
