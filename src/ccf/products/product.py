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
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, runtime_checkable

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    EGRESS_DOOR,
    PERSPECTIVE,
    PRODUCT_CLASS,
    REPLAY_BINDING,
    TTL_BINDING,
    DebtProfile,
    DeploymentConfig,
    EgressDoorBinding,
    HalfLifeTable,
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
from ccf.deployment.config import derive_deployment
from ccf.deployment.environment import (
    EnvironmentDocument,
    load_environment_document,
    resolve_values,
)
from ccf.deployment.keys import DeploymentKeys
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.products.composite import (
    ChildContractView,
    CompositeChildResolverProtocol,
    RequestAwareChildResolverProtocol,
)
from ccf.products.constraints import PolicyConstraintResolver, TechnicalCapability
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
    it holds; today that is nothing that needs releasing, and the shape is
    kept so the consumer half's bridge has a place to close.
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
        governed entitlement step denies it first. A wrong LANE does reach it,
        and is refused ``class-mismatch`` at ``key="schema_version"``, as data
        — the "bad question" reading of `D-IMPL-253` Q15 the two shipped doors
        already took (`D-IMPL-343` R-9). Everything else is the governed
        path's verdict.

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
        declared = (self.declaration.schema_name, self.declaration.schema_version)
        if (product_class, version) != declared:
            identity = RequestIdentity(
                product_id=product_class,
                product_version=version,
                parameters=request.parameters,
                temporal_boundary=request.asked_at,
            )
            violation = ProductRequestViolation(
                reason="class-mismatch",
                key="schema_version" if product_class == declared[0] else "schema_name",
                declared_type=f"{declared[0]}@{declared[1]}",
                presented_type=f"{product_class}@{version}",
                declared_keys=frozenset(),
                presented_keys=frozenset(),
                detail=(
                    f"this product serves {declared[0]!r} at lane {declared[1]!r}"
                    f" and was addressed for {product_class!r} at lane {version!r}"
                ),
            )
            return self.refusal_recorder.record(
                envelope_for(violation, request=identity),
                perspective=perspective,
                recorded_at=self._clock(),
                request=request,
                resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
            )
        return self.answer(request, perspective=perspective)

    # --- lifecycle -------------------------------------------------------------------

    def close(self) -> None:
        """Release what this object holds between questions — nothing, today."""

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
    clock: Callable[[], datetime] = _utc_now,
    environ: Mapping[str, str] | None = None,
    control_plane: ControlPlaneRegistry | None = None,
    artifact_store: ArtifactStoreProtocol | None = None,
    constraint_resolver: PolicyConstraintResolver | None = None,
    capabilities: tuple[TechnicalCapability, ...] | None = None,
    children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None = None,
) -> OpenedProduct:
    """Open the declared product under ``config_root``: bind the three verbs, read the bindings, refuse early.

    Reads the two documents (``ccf_config.yaml`` through the environment
    document's ``config``, and ``ccf_environment.yaml``), derives the manifest
    keys, parses the bindings the road reads, resolves every source variable
    the environment names, and builds the ONE store and the ONE recorder.
    **Boots nothing**: every question boots its own fabric (module docstring,
    §1), so opening is cheap and refuses only on what a document says.

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
        clock: The one clock: admission time, and the instant a door-side
            refusal is recorded at. The entitlement audit's wall clock stays
            the door's own, by ruling.
        environ: Where the environment document's names are resolved from;
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
        children: A hand-built child resolver for a class declaring
            ``requires`` — the composite hatch. The derived consumer chain
            (``producers:`` + ``agent:`` + a question mapping) is the consumer
            half of `D-IMPL-343` and lands with it; until then a composite on
            the road hands its resolver in here.

    Raises:
        ValueError: any open-time refusal in the module docstring — each
            names the section or the key.
        FileNotFoundError: the environment document is absent.
        ccf.deployment.environment.EnvironmentMissing: a variable a source
            names is unset; the document's remedy is the message.
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
    if declaration.requires and children is None:
        raise ValueError(
            f"the product class declares {len(declaration.requires)} child"
            " requirement(s) and this call wires no child resolver; the"
            " derived consumer chain is the consumer half of D-IMPL-343, and"
            " until it lands a composite on the paved road hands its resolver"
            " in through `children=`"
        )
    if children is not None and not declaration.requires:
        raise ValueError(
            "this call supplies `children=` and the product class declares no"
            " `requires`; a child resolver with nothing to resolve is wiring"
            " that nothing exercises (D-IMPL-343)"
        )

    sources = resolve_values(environment.sources, os.environ if environ is None else environ)

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
        children=children,
    )
