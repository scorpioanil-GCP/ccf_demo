"""[MECHANISM] The CCF call spine — every line here is a fabric call an adopter must make.

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
gate    register the product class and run the three L6 gates
record  build the five-dimension Decision Replay record
serve   persist the record, then deliver (whitepaper §7.10)
======  ==========================================================

**What the deployment supplies.** :class:`DeploymentBinding` and
:class:`Scenario` below are Protocols, not base classes: they are the list of
things the fabric needs from you, stated as structure rather than as prose
(CLAUDE.md §11, *Prefer Protocols over inheritance*). ``deployment.py`` imports
nothing from this module and this module imports nothing from it — the two are
held together structurally, which is the same posture
:class:`ccf.projection.plan.ProjectionPlan` takes.

**Import discipline (A-1).** Every ``ccf.deployment`` import below is spelled
``from ccf.deployment import X`` — the package, never a submodule of it.
Submodule fully-qualified names such as ``ccf.deployment.manifest`` are
implementation detail, and an adopter's call site never names one.

This file asserts nothing and prints nothing. Its assertions live in
``tests/examples/test_s1_01_output.py`` (phase 16 CONTEXT `D-09`).
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
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord, PolicyBinding, build_replay_record
from ccf.replay.serve import ReplayWriter, ServedProduct, serve
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
    def temporal_boundary(self) -> datetime:
        """The instant the graph is read at. Data, never a clock read."""

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


class DeploymentBinding(Protocol):
    """The four things the fabric asks a deployment to supply.

    Read this as the adoption checklist. Everything else in ``deployment.py``
    is that deployment's own business.
    """

    @property
    def manifest(self) -> Path:
        """The one document naming every artifact in force."""

    def connection(self, *, root: Path) -> Mapping[str, str]:
        """Substrate connection values, supplied by the CALLER, never by the
        manifest — a connection string in a content-hashed artifact would be
        persisted into the audit plane forever."""

    def read(self, booted: BootedFabric) -> Scenario:
        """Name this deployment's own artifact keys and read the run's values."""

    @property
    def plan_class(self) -> Callable[..., ProjectionPlan]:
        """Π, as a class the fabric constructs rather than an object it is handed.

        A projection is deployment code and is never a rewrite target
        (whitepaper §7.5) — but it is CONSTRUCTED in the ``project`` region
        below, one statement before the binder, because the statement that binds
        its authored operator set to the product class's claim has to be able to
        see the object it binds (design E2, D-IMPL-86 as corrected 2026-08-05).
        A plan handed over ready-made is a plan no binder can be shown to have
        been given.
        """


@dataclass(frozen=True)
class Assembled:
    """What one run of the spine produced, for a caller to inspect.

    The spine *returns* its state rather than checking it, so that
    ``tests/examples/test_s1_01_output.py`` can hold the assertions where a test
    runner will actually run them (phase 16 CONTEXT `D-09`).
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    operators_invoked: tuple[str, ...]
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    deployment: DeploymentBinding, *, root: Path
) -> Assembled:
    """Run the fabric once, end to end, against ``root`` as its scratch directory."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    #    Connection values arrive HERE, from the caller — never from the
    #    manifest, which declares the backend as a KIND only.
    booted = load_and_boot(
        deployment.manifest,
        registry=registry,
        connection=deployment.connection(root=root),
    )
    # --8<-- [end:boot]
    try:
        # The one line that crosses the boundary this example is about: the
        # deployment names its own artifact keys and hands back the run's
        # values. Everything below reads those values and nothing else.
        scenario = deployment.read(booted)

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
        plan = deployment.plan_class(
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
        product_class = register_product_class(
            registry=registry,
            schema_name=declared.schema_name,
            schema_version=declared.schema_version,
            ttl_anchor=declared.ttl_anchor,
            assembly_mode=declared.assembly_mode,
            max_ttl_key=declared.max_ttl_key,
            max_ttl_version=max_ttl_version,
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
        )
        # --8<-- [end:record]

        # --8<-- [start:serve]
        # The record is persisted BEFORE the product is delivered, and delivery
        # is what the successful append returns — there is no branch that
        # reaches a served product without a recorded decision (INV-CH7-79).
        store = FileArtifactStore(root=root / scenario.artifact_store_dirname)
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=store, artifact_class=scenario.replay_record_class
            ),
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
