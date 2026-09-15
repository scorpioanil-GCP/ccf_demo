"""The paved road: one object that turns *declare + acquire + project + assess* into a governed product.

**SDK-defined** (CLAUDE.md §11); the ruling of record is `D-IMPL-343`
(Dave, 2026-09-15) and its design, ``docs/D-IMPL-343-DESIGN.md``. The
measurement that opened it: the canonical spread producer carried roughly as
much SDK plumbing as domain logic — a boot, an effective-request re-derivation
copied into seven trees, a fifteen-keyword builder call, two replay stores,
three refusal recorders and a 243-line door — and one copy of that plumbing
had already drifted from the contract (`CP03C-F-07`). *"If a developer needs
roughly as much SDK plumbing as domain logic to publish and consume a Context
Product, that is a launch adoption problem."*

**One facade over the ruled mechanisms, never two architectures.** Everything
below orchestrates :func:`~ccf.deployment.load_config_and_boot`,
:func:`~ccf.products.resolver.build_governed_resolver` and the declared
bindings a ``ccf_config.yaml`` already carries. There is no second resolver,
no second registry, no second recorder and no second replay store here; a
deployment that needs one thing different reads :meth:`OpenedProduct
.build_arguments` — the exact keyword mapping this object hands the builder —
edits one entry, and calls the builder itself. The low road stays the low
road (Dave: *"Do not make the paved road the only road."*).

Who owns what — the ruled split
---------------------------------
The developer owns **acquire**, **project**, **assess**, the **declaration**
(``ccf_config.yaml``) and, for a composite, the question mapping. The SDK owns
boot, the effective request, the ingest loop with its tenant/instant bounds,
serve and refuse, the door, the replay store and recorder, producer
registration, grant and dispatch, and remote acquisition. Every value a
question needs arrives from the two documents beside the code — the Control
Plane document and the environment document — and none is restated here or in
an adopter's spine.

What one question does, in order (the mechanism)
--------------------------------------------------
1. **Boot.** A fresh dev fabric is minted under the caller's ``scratch`` from
   the environment's ``substrate:`` (a per-question file, so two questions can
   never share a graph — `CP03C-F-02` cannot recur), and
   :func:`~ccf.deployment.load_config_and_boot` registers the deployment's
   sections into the ONE Control Plane this object holds. Per-question
   re-registration of identical content is idempotent on every path
   (:mod:`ccf.controlplane.registry`; each outcome is still audited).
2. **Resolve, then acquire, then read** — inside :class:`~ccf.products
   .resolver.GovernedResolver`, through the declared acquisition seam
   (`D-IMPL-343` R-4). The resolver derives the EFFECTIVE request once and
   hands it to this object's seam; the seam calls the deployment's ``acquire``
   with it, refuses any envelope that names another tenant or another instant,
   and ingests through L2's one writer. Nothing here re-derives a resolved
   value, and a refused question never acquires.
3. **Serve or refuse**, through the builder, with the declared bindings: the
   TTL figures from ``ttl:``, the record and pin classes and the store from
   ``replay:``, the decision-instant parameter from the class declaration, the
   ONE recorder this object built at open — the same object its door holds.

What this object refuses at open, by name (never at the first question)
-------------------------------------------------------------------------
No ``replay:`` or ``ttl:`` section; no ``request_contract`` or
``default_perspective``; a declared product gate with no ``gate=`` or a
``gate=`` against a class declaring none (`D-IMPL-282` R-11, held here as
well as at the builder); a class declaring ``requires`` with no child
resolver; a ``scratch`` inside ``config_root``; an environment variable a
source names that the process lacks (with the document's own remedy); a
``door:`` asserting a tenant other than the deployment's (R-6, refused by the
loader).

Single-writer, stated
---------------------
This module is a **producer-side composition root** — the role every
canonical ``produce.py`` and hw1's ``compose.py`` play today — and it is the
only module under ``ccf.products`` that reaches ``fabric.handle.worker``. It
does so inside the acquisition seam, on the deployment's behalf, through L2's
:class:`~ccf.assembly.worker.AssemblyWorker`; it holds no writer of its own
and the resolver it builds holds none (CLAUDE.md §10). The invariant is held
by ``tests/invariants/test_paved_road_writer_reach.py``.

Not on this road, by ruling (`D-IMPL-343` GO): fan-out, swarm scheduling,
dynamic producer selection, a parameterized-product DSL, generators, and the
two open release findings `D-IMPL-341` (the entity-freshness expiry) and
`D-IMPL-342` (refused-child evidence beyond R-13's retained reason).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, runtime_checkable

from ccf.agents.definitions import AgentDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    EGRESS_DOOR,
    MCP_PRODUCER,
    PERSPECTIVE,
    PRODUCT_CLASS,
    REPLAY_BINDING,
    TTL_BINDING,
    DebtProfile,
    DeploymentConfig,
    EgressDoorBinding,
    HalfLifeTable,
    McpProducerRegistration,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ReplayBinding,
    TtlBinding,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.deployment.classes import resolve_artifact_class
from ccf.deployment.config import DerivedDeployment, derive_deployment
from ccf.deployment.environment import (
    EnvironmentDocument,
    load_environment_document,
    resolve_values,
)
from ccf.deployment.keys import DeploymentKeys
from ccf.deployment.manifest import register_manifest_entries
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.mcp.client import SyncMcpBridge, bearer_client_factory
from ccf.products.child_resolver import ChildQuestions, QuestionBoundChildResolver
from ccf.products.composite import (
    ChildContractView,
    CompositeAdmissionGate,
    CompositeChildResolverProtocol,
    RequestAwareChildResolverProtocol,
)
from ccf.products.constraints import PolicyConstraintResolver, TechnicalCapability
from ccf.products.contract import version_satisfies_floor
from ccf.products.refusal import RefusalEnvelope, RequestIdentity, envelope_for
from ccf.products.request import ProductRequest, ProductRequestViolation
from ccf.products.resolver import (
    ProductGateProtocol,
    ProductNotResolvable,
    ProjectionPlanFactoryProtocol,
    ReplayRefusalRecorder,
    ResolverOutcome,
    build_governed_resolver,
    declared_refusal_recorder,
)
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord, PolicyBinding, ResolutionNotApplicable
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope, refuse_foreign_envelope
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry
from ccf.skills.dispatch import McpSkillRegistry
from ccf.skills.grants import ApprovalOutcome, ApprovalSink, GrantLedger, SkillGrant
from ccf.skills.producers import register_declared_producer

__ccf_mode__ = "algorithmic"

__all__ = [
    "AcquireProtocol",
    "AcquisitionContext",
    "AssessProtocol",
    "AssessmentContext",
    "OpenedProduct",
    "open_product",
]


def _utc_now() -> datetime:
    """The process's UTC clock — the one place this module names it."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class AcquisitionContext:
    """What a deployment's ``acquire`` is handed for one question.

    Attributes:
        request: The EFFECTIVE request — defaults applied, the constraints in
            force folded, the caller's values where they are in bounds. The
            values governance resolved, so what the deployment reads its
            sources at is what the governed path serves (`CP04C-F-02`).
        perspective: Whose view the answer is served under. Which principal
            asks may change WHICH entities a source read expands to (a
            jurisdiction grant, say); that expansion is the deployment's own.
        tenant_id: The tenant every envelope must be stamped for.
        sources: Every source setting the environment document declared, by
            the deployment's own names, resolved to values ONCE at open.
        instant: The question's ``asked_at`` — the instant every envelope's
            ``ingestion_timestamp`` must carry, and the clock an SDK L1
            adapter used inside ``acquire`` is constructed with
            (``clock=lambda: context.instant``).
    """

    request: ProductRequest
    perspective: Perspective
    tenant_id: str
    sources: Mapping[str, Mapping[str, str]]
    instant: datetime


@dataclass(frozen=True)
class AssessmentContext:
    """What a deployment's ``assess`` is handed for one question.

    Attributes:
        view: The composed post-operator view — the rows that survived being
            read, exactly what the reference scorer measures over.
        evidence: What the execution observed about its own search.
        decided_at: The DECISION INSTANT, as the class declares it — the same
            value the product's expiry runs from (`D-IMPL-308`,
            `D-IMPL-343` R-3c). Never a clock; never ``asked_at`` unless the
            class declares no distinct instant.
        half_life: The booted λ_c table, when the deployment declares one —
            the exact document the pins record, never a second parse.
        profile: The booted D_c profile, likewise.
        children: The admitted children's contracts for a composite; ``None``
            for every other product.
    """

    view: GraphView
    evidence: ExecutionEvidence | None
    decided_at: datetime
    half_life: HalfLifeTable | None
    profile: DebtProfile | None
    children: ChildContractView | None


@runtime_checkable
class AcquireProtocol(Protocol):
    """The developer's acquisition: read the sources, emit dated L1 envelopes.

    Returns an iterable of :class:`~ccf.signal.envelope.SignalEnvelope`, each
    stamped for the context's tenant at the context's instant and carrying
    the claim's own age as ``observed_time`` (`D-IMPL-331`, `CP03C-F-08`). An
    empty iterable is a legitimate answer: nothing is written, and the
    governed path then refuses on the product's own gate, with a record.
    """

    def __call__(self, context: AcquisitionContext) -> Iterable[SignalEnvelope]: ...


@runtime_checkable
class AssessProtocol(Protocol):
    """The developer's debt rule over what one question assembled (whitepaper §7.7)."""

    def __call__(self, context: AssessmentContext) -> DebtAssessment: ...


class _AssessAdapter:
    """Adapts an :class:`AssessProtocol` onto the resolver's instant-aware seam.

    Conforms to :class:`~ccf.products.resolver.InstantAwareDebtScorerProtocol`
    (asked first by the resolver, with the decision instant and the children)
    and, structurally, to :class:`~ccf.products.resolver.AssemblyDebtScorerProtocol`
    so it can be handed to the builder — whose instant-blind call this adapter
    refuses by name rather than answering with an instant it does not have.
    """

    def __init__(
        self,
        assess: AssessProtocol,
        *,
        half_life: HalfLifeTable | None,
        profile: DebtProfile | None,
    ) -> None:
        self._assess = assess
        self._half_life = half_life
        self._profile = profile

    def score_at(
        self,
        *,
        view: GraphView,
        evidence: ExecutionEvidence | None,
        decided_at: datetime,
        children: ChildContractView | None,
    ) -> DebtAssessment:
        return self._assess(
            AssessmentContext(
                view=view,
                evidence=evidence,
                decided_at=decided_at,
                half_life=self._half_life,
                profile=self._profile,
                children=children,
            )
        )

    def __call__(
        self, *, view: GraphView, evidence: ExecutionEvidence | None = None
    ) -> DebtAssessment:
        raise TypeError(
            "the paved road's assessment adapter is asked through the"
            " instant-aware seam (`score_at`) and never through the"
            " instant-blind call; a resolver reaching it here is one built"
            " before D-IMPL-343 R-3c, which the paved road does not compose"
        )


class OpenedProduct:
    """One declared product, opened: ask it questions, serve it, hand it to a door.

    Constructed by :func:`open_product` and by nothing else. Holds NO booted
    fabric between questions — every question boots its own (§1 of the module
    docstring) — and holds exactly the things that are per-deployment rather
    than per-question: the parsed declaration and bindings, the ONE Control
    Plane, the ONE artifact store, the ONE refusal recorder, the resolved
    source settings, and the three developer callables.

    A context manager, so ``with open_product(...) as opened:`` releases what
    it holds — the one MCP bridge a consuming deployment's producers are
    reached over, when the deployment declares any (``producers:``); nothing
    otherwise.

    For a consumer, :attr:`mcp_skills` is the ONE
    :class:`~ccf.skills.dispatch.McpSkillRegistry` every declared producer was
    registered on at open, whether the composite chain was derived or handed
    in through ``children=`` — so the hatch composes over the registrations
    the deployment declared, never a second registry.
    """

    def __init__(
        self,
        *,
        config_root: Path,
        config_path: Path,
        scratch: Path,
        config: DeploymentConfig,
        environment: EnvironmentDocument,
        keys: DeploymentKeys,
        tenant_id: str,
        declaration: ProductClassDeclaration,
        replay: ReplayBinding,
        ttl: TtlBinding,
        door: EgressDoorBinding | None,
        default_perspective: PerspectiveArtifact,
        sources: Mapping[str, Mapping[str, str]],
        control_plane: ControlPlaneRegistry,
        artifact_store: ArtifactStoreProtocol,
        refusal_recorder: ReplayRefusalRecorder,
        acquire: AcquireProtocol,
        project: ProjectionPlanFactoryProtocol,
        assess: AssessProtocol,
        gate: ProductGateProtocol | None,
        clock: Callable[[], datetime],
        constraint_resolver: PolicyConstraintResolver | None,
        capabilities: tuple[TechnicalCapability, ...] | None,
        children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None,
        mcp_skills: McpSkillRegistry | None = None,
        bridge: SyncMcpBridge | None = None,
        agent: AgentDefinition | None = None,
    ) -> None:
        self.config_root = config_root
        self.config_path = config_path
        self.scratch = scratch
        self.config = config
        self.environment = environment
        self.keys = keys
        self.tenant_id = tenant_id
        self.declaration = declaration
        self.replay = replay
        self.ttl = ttl
        self.door = door
        self.default_perspective = default_perspective
        self.sources = sources
        self.control_plane = control_plane
        self.artifact_store = artifact_store
        self.refusal_recorder = refusal_recorder
        self.mcp_skills = mcp_skills
        self.agent = agent
        self._bridge = bridge
        self._acquire = acquire
        self._project = project
        self._assess = assess
        self._gate = gate
        self._clock = clock
        self._constraint_resolver = constraint_resolver
        self._capabilities = capabilities
        self._children = children

    # --- the developer's three verbs ------------------------------------------

    def question(
        self,
        *,
        subject: str,
        asked_at: datetime,
        intent: str,
        freshness: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> ProductRequest:
        """One question of this product — the class and lane come from the declaration.

        The four axes are whitepaper §6.3's, and ``intent`` is one of them:
        it is judged against the class's declared ``discovery`` by the
        resolver, and it is never a parameter (`D-IMPL-264` D-01). Every
        spread of parameters the caller omits is omitted, so the class default
        the declaration carries is what resolves — a different thing from
        passing the default's value, and the resolution records which.
        """
        return ProductRequest(
            schema_name=self.declaration.schema_name,
            schema_version=self.declaration.schema_version,
            subject=subject,
            intent=intent,
            freshness=freshness,
            asked_at=asked_at,
            parameters=dict(parameters or {}),
        )

    def answer(
        self, request: ProductRequest, *, perspective: Perspective | None = None
    ) -> ResolverOutcome:
        """Answer ``request`` end to end: boot, resolve, acquire, serve or refuse.

        Returns the governed outcome AS DATA — a
        :class:`~ccf.replay.serve.ServedProduct` whose replay reference proves
        the record was appended, or a :class:`~ccf.products.refusal.RefusalEnvelope`
        recorded, disclosed and addressed. A bad question is a bad question
        rather than a broken deployment; a verdict returned as a value cannot
        be swallowed by a bare ``except``.

        ``perspective`` defaults to the declared ``default_perspective``; a
        deployment asking as somebody else states that principal's grant on
        the request's own parameters, where the effective request records it.
        """
        fabric = self._boot()
        try:
            resolver = build_governed_resolver(**self.build_arguments(fabric))
            return resolver(
                tenant=self.tenant_id,
                product_class=self.declaration.schema_name,
                version=self.declaration.schema_version,
                perspective=perspective if perspective is not None else self.default_perspective,
                request=request,
            )
        finally:
            fabric.handle.close()

    def record_of(self, outcome: ResolverOutcome) -> DecisionReplayRecord:
        """The decision record behind ``outcome``, read from the ONE store.

        Served and refused decisions alike: a served product carries its
        record's content address on ``replay_ref``; a refusal carries the
        record's URI, which the store resolves. One store, so one read idiom.
        """
        if isinstance(outcome, ServedProduct):
            address = outcome.replay_ref.content_address
        else:
            address = self.artifact_store.resolve_uri(uri=outcome.replay_reference)
        return DecisionReplayRecord.model_validate_json(
            self.artifact_store.get(content_address=address)
        )

    # --- the low road, reachable from the paved surface --------------------------

    def build_arguments(self, fabric: BootedFabric) -> dict[str, Any]:
        """The exact keyword mapping :meth:`answer` hands :func:`build_governed_resolver`.

        The escape hatch, and the proof that the facade adds no second
        architecture: a deployment that needs one thing different copies this
        mapping, edits one entry and calls the builder itself. Every key is
        READ — off :attr:`~ccf.deployment.BootedFabric.keys`, the parsed
        bindings, or a callable the deployment supplied — and none is a value
        restated here. The TTL figures and the decision-instant parameter are
        deliberately ABSENT: the builder reads them from the fabric's declared
        `ttl:` binding and the class declaration (`D-IMPL-343` R-3), and a
        mapping that named them would be the second authority the ruling
        deletes.
        """
        keys = fabric.keys
        assert keys is not None  # `load_config_and_boot` always sets it
        assert keys.request_contract is not None  # refused at open otherwise
        half_life = fabric.artifacts.get(keys.half_life) if keys.half_life else None
        profile = fabric.artifacts.get(keys.debt_profile) if keys.debt_profile else None
        assert half_life is None or isinstance(half_life, HalfLifeTable)
        assert profile is None or isinstance(profile, DebtProfile)
        arguments: dict[str, Any] = {
            "fabric": fabric,
            "control_plane": self.control_plane,
            "product_class_key": keys.product_class,
            "request_contract_key": keys.request_contract,
            "operator_parameter_keys": keys.operator_parameters,
            "policy_bundle_key": keys.policy_bundle,
            "plan_factory": self._project,
            "debt_scorer": _AssessAdapter(self._assess, half_life=half_life, profile=profile),
            "debt_profile_key": keys.debt_profile,
            "product_gate": self._gate,
            "artifact_store": self.artifact_store,
            "replay_record_class": self.replay.record_class,
            "query_pin_class": self.replay.query_pin_class,
            "refusal_recorder": self.refusal_recorder,
            "acquisition": self._acquisition_seam(fabric),
            "composite_children": self._children,
            "admission_clock": self._clock,
        }
        if self._constraint_resolver is not None:
            arguments["constraint_resolver"] = self._constraint_resolver
        if self._capabilities is not None:
            arguments["capabilities"] = self._capabilities
        return arguments

    # --- what a door holds --------------------------------------------------------

    def resolve(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome:
        """:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` — what the standard door calls.

        The door refuses exactly one thing of its own — an address it does not
        serve, judged before any assembly and RECORDED the same way an
        assembled refusal is, by the same recorder, into the same store. A
        wrong CLASS never reaches this method through the standard door: the
        derived entitlement permits exactly the declared class, so the door's
        governed entitlement step denies it first. Everything else is the
        governed path's verdict.

        **The lane an address names is a FLOOR** (`D-IMPL-343` R-13: *"Exact
        address at serve while floor at open is a defect"*). A consumer
        declares the lane it composes over as a floor at every boundary — the
        requirement's ``compatible_from``, the registration's
        ``versions_from`` — and asks at that floor; this door serves its ONE
        declared lane when that lane lies inside the floor's major and at or
        above it, and the answer carries the served lane, which admission
        holds to the consumer's own floor again. A floor the served lane does
        not satisfy — another major, or above what is served — is refused
        ``class-mismatch`` at ``key="schema_version"``, as data, with BOTH
        lanes retained in the record: the "bad question" reading of
        `D-IMPL-253` Q15 the two shipped doors already took (R-9), never
        tightened to "exact lane only".

        Wire parameters cross verbatim (`D-IMPL-302`; `D-IMPL-264` D-04): no
        coercion happens here, so a hand-typed ``"periods": "8"`` is refused
        by the contract by name rather than quietly widened (R-8).

        Raises:
            ProductNotResolvable: the address names another tenant, or the
                call carries no request — a broken deployment (this door is
                tool-only and has no standing answer), never a governed "no".
        """
        if tenant != self.tenant_id:
            raise ProductNotResolvable(
                f"this product serves tenant {self.tenant_id!r} and was called"
                f" for {tenant!r}; the tenant is established by the calling"
                " surface, and a product opened for one tenant cannot answer"
                " for another"
            )
        if request is None:
            raise ProductNotResolvable(
                f"{self.declaration.schema_name!r} is a parameterized class"
                " with no standing answer; the standard door exposes the"
                " request tool only, so a call carrying no request reaches"
                " nothing this product can answer"
            )
        declared_name = self.declaration.schema_name
        served_lane = self.declaration.schema_version
        if product_class != declared_name:
            return self._refuse_address(
                request,
                perspective=perspective,
                address=(product_class, version),
                key="schema_name",
                detail=(
                    f"this product serves {declared_name!r} at lane {served_lane!r}"
                    f" and was addressed for {product_class!r} at lane {version!r}"
                ),
            )
        if not version_satisfies_floor(floor=version, version=served_lane):
            return self._refuse_address(
                request,
                perspective=perspective,
                address=(product_class, version),
                key="schema_version",
                detail=(
                    f"this product serves {declared_name!r} at lane {served_lane!r},"
                    f" and the address asks from floor {version!r}; a served lane"
                    " satisfies a floor when it shares the floor's major and is"
                    f" at or above it, and {served_lane!r} does not satisfy"
                    f" {version!r} (D-IMPL-343 R-13)"
                ),
            )
        if request.schema_version != served_lane:
            # The floor was satisfied: the question is answered at the ONE
            # lane this product serves, and the record says which.
            request = request.model_copy(update={"schema_version": served_lane})
        return self.answer(request, perspective=perspective)

    def _refuse_address(
        self,
        request: ProductRequest,
        *,
        perspective: Perspective,
        address: tuple[str, str],
        key: str,
        detail: str,
    ) -> RefusalEnvelope:
        """Record and return the door's one own refusal — an address this product does not serve."""
        product_class, version = address
        identity = RequestIdentity(
            product_id=product_class,
            product_version=version,
            parameters=request.parameters,
            temporal_boundary=request.asked_at,
        )
        violation = ProductRequestViolation(
            reason="class-mismatch",
            key=key,
            declared_type=f"{self.declaration.schema_name}@{self.declaration.schema_version}",
            presented_type=f"{product_class}@{version}",
            declared_keys=frozenset(),
            presented_keys=frozenset(),
            detail=detail,
        )
        return self.refusal_recorder.record(
            envelope_for(violation, request=identity),
            perspective=perspective,
            recorded_at=self._clock(),
            request=request,
            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
        )

    # --- lifecycle -------------------------------------------------------------------

    def close(self) -> None:
        """Release what this object holds between questions: the producers' one bridge, if any.

        Idempotent. A deployment declaring no ``producers:`` holds nothing
        that needs releasing.
        """
        if self._bridge is not None:
            self._bridge.close()

    def __enter__(self) -> OpenedProduct:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # --- the mechanism ------------------------------------------------------------------

    def _boot(self) -> BootedFabric:
        """Mint a fresh per-question fabric under ``scratch`` and boot it.

        The substrate's SETTING, prefix and suffix are the environment
        document's; the uuid is what makes "per question" true rather than
        nominal (`CP03C-F-02`: a door answering several questions under one
        root booted the SAME file every time). Nothing here names a backend.
        """
        substrate = self.environment.substrate
        minted = self.scratch / f"{substrate.prefix}_{uuid.uuid4().hex}{substrate.suffix}"
        return load_config_and_boot(
            self.config_path,
            registry=self.control_plane,
            connection={substrate.setting: str(minted)},
        )

    def _acquisition_seam(self, fabric: BootedFabric) -> Callable[..., None]:
        """The declared acquisition boundary for one question (`D-IMPL-343` R-4).

        Called by the resolver ONCE, with the EFFECTIVE request, after
        resolution and before the graph read. The deployment's ``acquire``
        runs at the values governance resolved; every envelope is held to the
        tenant and the instant before L2's one writer sees it.
        """
        worker = fabric.handle.worker
        tenant_id = self.tenant_id
        sources = self.sources
        acquire = self._acquire

        def seam(*, request: ProductRequest, perspective: Perspective) -> None:
            context = AcquisitionContext(
                request=request,
                perspective=perspective,
                tenant_id=tenant_id,
                sources=sources,
                instant=request.asked_at,
            )
            for envelope in acquire(context):
                refuse_foreign_envelope(envelope, tenant_id=tenant_id, asked_at=request.asked_at)
                worker.ingest(envelope)

        return seam


def _parsed(
    documents: Mapping[str, Mapping[str, Any]], key: str | None, section: str, expected: Any
) -> Any:
    if key is None:
        raise ValueError(
            f"this deployment declares no '{section}' section, and the paved"
            f" road reads one: declare '{section}' in ccf_config.yaml, or"
            " compose the deployment through `build_governed_resolver` directly"
            " (D-IMPL-343)"
        )
    return parse_artifact(documents[key], expected)


def open_product(
    *,
    config_root: Path | str,
    scratch: Path | str,
    acquire: AcquireProtocol,
    project: ProjectionPlanFactoryProtocol,
    assess: AssessProtocol,
    gate: ProductGateProtocol | None = None,
    questions: ChildQuestions | None = None,
    clock: Callable[[], datetime] = _utc_now,
    environ: Mapping[str, str] | None = None,
    control_plane: ControlPlaneRegistry | None = None,
    artifact_store: ArtifactStoreProtocol | None = None,
    constraint_resolver: PolicyConstraintResolver | None = None,
    capabilities: tuple[TechnicalCapability, ...] | None = None,
    approval_sink: ApprovalSink | None = None,
    children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None = None,
) -> OpenedProduct:
    """Open the declared product under ``config_root``: bind the verbs, read the bindings, refuse early.

    Reads the two documents (``ccf_config.yaml`` through the environment
    document's ``config``, and ``ccf_environment.yaml``), derives the manifest
    keys, parses the bindings the road reads, resolves every source variable
    the environment names, and builds the ONE store and the ONE recorder.
    **Boots nothing**: every question boots its own fabric (module docstring,
    §1), so opening is cheap and refuses only on what a document says.

    **A consumer opens the same way** (`D-IMPL-343`, the consumer half). A
    deployment declaring ``producers:`` has every declared producer registered
    at open on ONE :class:`~ccf.skills.dispatch.McpSkillRegistry` over ONE
    bridge — the endpoint and credential read from the environment by the
    NAMES the registration declares, never a value in either document — and
    the registry is exposed as :attr:`OpenedProduct.mcp_skills` whether the
    child chain is derived or handed in. A class declaring ``requires`` then
    derives its chain from the declarations beside it: the ``agent:`` section
    is the composing agent (R-2), each ``skills:`` entry is one governed
    ``mcp_product`` skill (R-7), one grant per skill is requested through the
    :class:`~ccf.skills.grants.GrantLedger` under the deployment's own policy
    regime (idempotent over a shared registry: a skill already bound to this
    agent is not re-requested), and ``questions=`` — the developer's ONE
    mapping — is bound into a
    :class:`~ccf.products.child_resolver.QuestionBoundChildResolver` behind
    the :class:`~ccf.products.composite.CompositeAdmissionGate`. Nothing here
    is a second grant resolution, dispatch, admission or composition: each
    is the `D-IMPL-336`–`340` object, constructed once from declared keys.

    Args:
        config_root: The directory holding the two documents. Read-only.
        scratch: A writable directory: per-question substrate files and the
            replay store (under the declared ``store_dirname``) live here.
            Refused inside ``config_root`` by name — a tree that wrote its
            own fabrics beside its own documents would be one nobody could
            clean.
        acquire: The deployment's acquisition (:class:`AcquireProtocol`).
        project: The deployment's NAMED plan factory (`D-IMPL-137`: its only
            operator source is the ``required`` tuple the SDK hands it).
        assess: The deployment's debt rule (:class:`AssessProtocol`).
            Required in v0 (`D-IMPL-343` R-3c): the reference scorer's two
            declared factors have no Control Plane home yet.
        gate: The deployment's predicate for the class's declared product
            gate, or ``None`` for a class declaring none — both-or-neither
            (`D-IMPL-282` R-11), refused HERE when they disagree.
        questions: For a composite, the developer's mapping from one declared
            requirement and the composite's EFFECTIVE request to the governed
            question its producer is asked
            (:data:`~ccf.products.child_resolver.ChildQuestions`) — *"given
            this parent request, what should requirement X be asked?"*.
            Required exactly when the class declares ``requires`` and no
            ``children=`` is handed in; refused otherwise.
        clock: The one clock: admission time, the grant ledger's audit
            instant, and the instant a door-side refusal is recorded at. The
            entitlement audit's wall clock stays the door's own, by ruling.
        environ: Where the environment document's names — source settings,
            producer endpoints and credentials — are resolved from;
            ``os.environ`` when omitted. Passed in rather than reached for,
            so a test supplies a mapping.
        control_plane: A registry to open INTO, or ``None`` for a fresh one.
        artifact_store: Any :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol`
            (an MCP-backed store, say). Wins under `D-IMPL-282` R-12; the
            declared ``store_dirname`` is then unread. ``None`` builds the
            file-backed reference store under ``scratch``.
        constraint_resolver: A deployment's own
            :class:`~ccf.products.constraints.PolicyConstraintResolver`, or
            ``None`` for the SDK's reference over this registry.
        capabilities: The technical capabilities the fabric reports, or
            ``None`` to ask the booted fabric.
        approval_sink: The `D-IMPL-29` tier-2 hatch — where a derived grant
            suspends when the deployment's policy regime declares
            ``grant_requires_approval``. ``None`` for a regime that does not;
            a regime that does and no sink is refused at open by name.
        children: A hand-built child resolver for a class declaring
            ``requires`` — the composite hatch, and the low road's way onto
            this surface. It composes over :attr:`OpenedProduct.mcp_skills`
            when the deployment declares producers. Refused together with
            ``questions=``, or with an ``agent:`` or ``skills:`` section: a
            deployment declares its chain or hands one in, never both.

    Raises:
        ValueError: any open-time refusal in the module docstring — each
            names the section or the key; a grant the Control Plane refused,
            with the refusal's own detail.
        FileNotFoundError: the environment document is absent.
        ccf.deployment.environment.EnvironmentMissing: a variable a source
            names is unset; the document's remedy is the message.
        ccf.skills.producers.ProducerEnvironmentMissing: a variable a producer
            registration names is unset.
    """
    root = Path(config_root).resolve()
    scratch_root = Path(scratch).resolve()
    if scratch_root == root or root in scratch_root.parents:
        raise ValueError(
            f"scratch {scratch_root} lies inside the config root {root}; the"
            " per-question fabrics and the replay store are written under"
            " scratch and never beside the deployment's documents (D-IMPL-343)"
        )
    environment = load_environment_document(root)
    config_path = root / environment.config
    config = load_artifact(config_path.read_text(encoding="utf-8"), DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)  # DEPLOYMENT_CONFIG's contract
    if config.tenant_id is None:
        raise ValueError(
            "ccf_config.yaml declares no tenant_id; on the paved road the"
            " deployment's tenant is declared once, in the document every"
            " other tenant-bearing value is held to (D-IMPL-343)"
        )
    derived = derive_deployment(config, config_filename=config_path.name)
    keys = derived.keys
    documents = derived.documents

    declaration = parse_artifact(documents[keys.product_class], PRODUCT_CLASS)
    assert isinstance(declaration, ProductClassDeclaration)
    replay = _parsed(documents, keys.replay, "replay", REPLAY_BINDING)
    assert isinstance(replay, ReplayBinding)
    ttl = _parsed(documents, keys.ttl, "ttl", TTL_BINDING)
    assert isinstance(ttl, TtlBinding)
    default_perspective = _parsed(
        documents, keys.default_perspective, "default_perspective", PERSPECTIVE
    )
    assert isinstance(default_perspective, PerspectiveArtifact)
    door: EgressDoorBinding | None = None
    if keys.door is not None:
        parsed_door = parse_artifact(documents[keys.door], EGRESS_DOOR)
        assert isinstance(parsed_door, EgressDoorBinding)
        door = parsed_door
    if keys.request_contract is None:
        raise ValueError(
            "this deployment declares no 'request_contract' section; a"
            " governed product is a question answered against a declared"
            " request surface, so the paved road reads one (D-IMPL-343)"
        )

    declared_gate = declaration.declared_product_gate
    if declared_gate.gate_id and gate is None:
        raise ValueError(
            f"the product class declares the runtime gate {declared_gate.gate_id!r}"
            f" at version {declared_gate.gate_version!r}, and this call supplies"
            " no `gate=` to run it; a declared check nothing executes is a"
            " check that stops checking without going red (D-IMPL-282 R-11)"
        )
    if gate is not None and not declared_gate.gate_id:
        raise ValueError(
            "this call supplies a `gate=` and the product class declares none,"
            " so the SDK has no identity to stamp on a refusal it produced;"
            " declare `declared_product_gate` on the class, or drop the"
            " argument (D-IMPL-282 R-11)"
        )
    _refuse_half_wired_composite(declaration, keys, questions=questions, children=children)

    resolved_environ = os.environ if environ is None else environ
    sources = resolve_values(environment.sources, resolved_environ)

    scratch_root.mkdir(parents=True, exist_ok=True)
    registry = control_plane if control_plane is not None else ControlPlaneRegistry()
    store: ArtifactStoreProtocol = (
        artifact_store
        if artifact_store is not None
        else FileArtifactStore(root=scratch_root / replay.store_dirname)
    )
    # The bundle pin the boot WILL mint, computed the way the registry mints
    # it — the content address of the parsed artifact (`D-IMPL-26`) — so the
    # one recorder can exist before any fabric does and record the same pin
    # every question's resolver records.
    policy_entry = next(
        entry for entry in derived.manifest.artifacts if entry.key == keys.policy_bundle
    )
    policy_artifact = parse_artifact(
        documents[keys.policy_bundle], resolve_artifact_class(policy_entry.class_id)
    )
    recorder = declared_refusal_recorder(
        control_plane=registry,
        artifact_store=store,
        replay_record_class=replay.record_class,
        tenant_id=config.tenant_id,
        assembly_mode=declaration.assembly_mode,
        policy_bundle_pin=PolicyBinding(
            key=keys.policy_bundle, version=content_hash(policy_artifact)
        ),
    )

    # --- the consumer half: producers, then the derived chain ---------------------
    bridge: SyncMcpBridge | None = None
    mcp_skills: McpSkillRegistry | None = None
    agent: AgentDefinition | None = None
    child_resolver: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None = children
    try:
        if keys.producers:
            bridge, mcp_skills = _register_declared_producers(
                derived, registry=registry, environment=environment, environ=resolved_environ, clock=clock
            )
        if declaration.requires and children is None:
            assert questions is not None  # `_refuse_half_wired_composite` held it
            agent, child_resolver = _derive_consumer_chain(
                derived,
                declaration=declaration,
                registry=registry,
                store=store,
                mcp_skills=mcp_skills,
                questions=questions,
                clock=clock,
                approval_sink=approval_sink,
            )
    except BaseException:
        if bridge is not None:
            bridge.close()
        raise

    return OpenedProduct(
        config_root=root,
        config_path=config_path,
        scratch=scratch_root,
        config=config,
        environment=environment,
        keys=keys,
        tenant_id=config.tenant_id,
        declaration=declaration,
        replay=replay,
        ttl=ttl,
        door=door,
        default_perspective=default_perspective,
        sources=sources,
        control_plane=registry,
        artifact_store=store,
        refusal_recorder=recorder,
        acquire=acquire,
        project=project,
        assess=assess,
        gate=gate,
        clock=clock,
        constraint_resolver=constraint_resolver,
        capabilities=capabilities,
        children=child_resolver,
        mcp_skills=mcp_skills,
        bridge=bridge,
        agent=agent,
    )


def _refuse_half_wired_composite(
    declaration: ProductClassDeclaration,
    keys: DeploymentKeys,
    *,
    questions: ChildQuestions | None,
    children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None,
) -> None:
    """A composite is declared whole or handed in whole — every mixed state refused by name.

    Four declarations make a derived chain: ``requires`` on the class,
    ``producers:``, ``skills:``, ``agent:`` — and one keyword, ``questions=``.
    One keyword makes a handed-in chain: ``children=``. What is refused: a
    class with ``requires`` and neither; a class without ``requires`` and
    either; both at once; a handed-in chain beside a declared ``agent:`` or
    ``skills:`` (which one would govern is exactly the ambiguity a declared
    deployment cannot carry); and a derived chain missing any of its four
    declarations, each named with the section that fills it.
    """
    requires = declaration.requires
    if not requires:
        if children is not None:
            raise ValueError(
                "this call supplies `children=` and the product class declares no"
                " `requires`; a child resolver with nothing to resolve is wiring"
                " that nothing exercises (D-IMPL-343)"
            )
        if questions is not None:
            raise ValueError(
                "this call supplies `questions=` and the product class declares"
                " no `requires`; a question mapping for no child is wiring that"
                " nothing exercises (D-IMPL-343)"
            )
        return
    if children is not None:
        if questions is not None:
            raise ValueError(
                "this call supplies both `children=` and `questions=`; a composite"
                " hands its chain in through the hatch or has it derived from"
                " `questions=` and the declarations beside it, never both"
                " (D-IMPL-343)"
            )
        if keys.agent is not None or keys.skills:
            declared = [s for s, present in (("agent", keys.agent), ("skills", keys.skills)) if present]
            raise ValueError(
                f"this call supplies `children=` and the config declares {declared!r};"
                " a handed-in chain beside a declared one leaves the question of"
                " which governs, so a deployment declares its chain or hands one"
                " in, never both (D-IMPL-343)"
            )
        return
    if questions is None:
        raise ValueError(
            f"the product class declares {len(requires)} child requirement(s)"
            " and this call supplies no `questions=`; the mapping from the"
            " composite's effective request to each child's governed question"
            " is the developer's own and the SDK holds no default for it —"
            " supply `questions=` beside the `producers:`, `skills:` and"
            " `agent:` declarations, or hand a resolver in through `children=`"
            " (D-IMPL-343; D-IMPL-38)"
        )
    missing = [
        section
        for section, present in (
            ("producers", keys.producers),
            ("skills", keys.skills),
            ("agent", keys.agent),
        )
        if not present
    ]
    if missing:
        raise ValueError(
            f"the product class declares {len(requires)} child requirement(s)"
            f" and the config declares no {missing!r} section; a composite on"
            " the paved road names the producers it asks (`producers:`), the"
            " governed skills that ask them (`skills:`) and the agent the"
            " grants bind to (`agent:`, CLAUDE.md §6.4 — the SDK synthesizes no"
            " agent); or hand a resolver in through `children=` (D-IMPL-343)"
        )


def _register_declared_producers(
    derived: DerivedDeployment,
    *,
    registry: ControlPlaneRegistry,
    environment: EnvironmentDocument,
    environ: Mapping[str, str],
    clock: Callable[[], datetime],
) -> tuple[SyncMcpBridge, McpSkillRegistry]:
    """Every ``producers.*`` registration onto ONE registry over ONE bridge (`D-IMPL-340`).

    The endpoint and the credential are read from the environment by the
    names the registration declares — the only place either value ever
    exists in the process — and the credential rides the shared MCP client
    as a bearer token through :func:`~ccf.mcp.client.bearer_client_factory`.
    The deadline is the environment document's one ``remote`` setting.
    """
    remote = environment.remote
    if remote is None:
        raise ValueError(
            "the config declares `producers:` and the environment document"
            " names no `remote` block; the deadline every producer call is"
            " held to is deployment environment, declared as"
            " `remote: {call_timeout_seconds: N}` (D-IMPL-343; D-IMPL-340)"
        )
    timeout = float(remote.call_timeout_seconds)
    bridge = SyncMcpBridge(call_timeout_seconds=timeout)
    mcp_skills = McpSkillRegistry(audit_log=registry.audit_log, clock=clock)
    for key in derived.keys.producers:
        artifact = parse_artifact(derived.documents[key], MCP_PRODUCER)
        assert isinstance(artifact, McpProducerRegistration)  # MCP_PRODUCER's contract
        register_declared_producer(
            mcp_skills,
            artifact=artifact,
            environ=environ,
            bridge=bridge,
            credential_factory=partial(bearer_client_factory, timeout_seconds=timeout),
        )
    return bridge, mcp_skills


class _NoApprovalSink:
    """The tier-2 surface when the deployment supplied none: refuses by name, never decides.

    Reached only when the policy regime declares ``grant_requires_approval``
    — a regime that does not never consults the sink. The ledger's own
    no-wedged-states guard settles the grant ``refused`` and re-raises, so an
    open over such a regime fails at open with this message, and the SDK
    approves nothing on the deployment's behalf (`D-IMPL-29`; `D-IMPL-38`).
    """

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise ValueError(
            f"the policy regime requires approval for grant {grant.name!r} and"
            " this open supplied no `approval_sink=`; tier-2 approval is the"
            " deployment's decision surface and the SDK holds no default for"
            " it (D-IMPL-29; D-IMPL-343)"
        )


def _derive_consumer_chain(
    derived: DerivedDeployment,
    *,
    declaration: ProductClassDeclaration,
    registry: ControlPlaneRegistry,
    store: ArtifactStoreProtocol,
    mcp_skills: McpSkillRegistry | None,
    questions: ChildQuestions,
    clock: Callable[[], datetime],
    approval_sink: ApprovalSink | None,
) -> tuple[AgentDefinition, QuestionBoundChildResolver]:
    """The declared chain: agent → catalog → grant → question-bound resolver → gate.

    Registers what the ledger resolves — the policy regime, the agent and the
    skill entries — through the manifest's ONE register loop
    (:func:`~ccf.deployment.manifest.register_manifest_entries`; every
    question's boot registers the same content again, idempotently), then
    requests one grant per skill entry for the agent under the deployment's
    regime. The grant is derived from the entry it binds and nothing else:
    its lanes are the entry's own two, its name is the entry's, and its agent
    is the agent's content hash (`D-IMPL-26`). A skill already bound to this
    agent on the registry is not re-requested.
    """
    keys = derived.keys
    assert keys.agent is not None and keys.skills and keys.policy_bundle  # held by the caller
    if mcp_skills is None:
        raise ValueError(
            "the product class declares `requires` and the config declares no"
            " `producers:`; a derived chain asks declared producers and none"
            " are declared (D-IMPL-343; D-IMPL-340)"
        )
    wanted = frozenset({keys.policy_bundle, keys.agent, *keys.skills})
    parsed = {
        entry.key: parse_artifact(derived.documents[entry.key], resolve_artifact_class(entry.class_id))
        for entry in derived.manifest.artifacts
        if entry.key in wanted
    }
    register_manifest_entries(derived.manifest, parsed, registry=registry, only=wanted)

    agent = parsed[keys.agent]
    assert isinstance(agent, AgentDefinition)  # its entry names AGENT_DEFINITION
    agent_hash = content_hash(agent)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=SkillCatalog(registry),
        sink=approval_sink if approval_sink is not None else _NoApprovalSink(),
        clock=clock,
    )
    bound = ledger.bound_view(agent_hash)
    produced: set[str] = set()
    for key in keys.skills:
        entry = parsed[key]
        assert isinstance(entry, SkillCatalogEntry)  # its entry names SKILL_CATALOG_ENTRY
        produced.add(entry.produces)
        if entry.name in bound:
            continue  # idempotent over a shared registry: already in force for this agent
        outcome = ledger.request(
            SkillGrant(
                schema_version=entry.schema_version,
                artifact_version=entry.artifact_version,
                name=entry.name,
                tenant=entry.tenant,
                agent_definition_hash=agent_hash,
                skill_name=entry.name,
                skill_version=entry.artifact_version,
            ),
            definition=agent,
            actor=agent.name,
        )
        if not isinstance(outcome, str):
            raise ValueError(
                f"the grant derived for skill {entry.name!r} was refused by the"
                f" Control Plane ({type(outcome).__name__}):"
                f" {getattr(outcome, 'detail', outcome)!s}; a composite whose"
                " agent may not bind the skill that produces a required class"
                " cannot compose it (D-IMPL-343 R-7; D-IMPL-29)"
            )
    for requirement in declaration.requires:
        if requirement.required and requirement.product_class not in produced:
            raise ValueError(
                f"the product class requires {requirement.product_class!r} and"
                " no `skills:` entry produces it; a required child with no"
                " declared way to acquire it would refuse every question"
                " `no-producing-skill` — declare the skill, or make the"
                " requirement optional with an absence treatment (D-IMPL-343)"
            )
    gate = CompositeAdmissionGate(
        tenant_id=agent.tenant,
        consumer_scope=f"consumer://{agent.tenant}/{agent.name}",
        registry=registry,
    )
    return agent, QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=gate,
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=store,
        mcp_skills=mcp_skills,
    )
