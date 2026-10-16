# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
road (Dave: *"Do not make the paved road the only road."*). On the low road the
temporal write guard this module composes at its acquisition seam is the
adopter's to compose (`D-IMPL-364` SEC-008 B1, ruled outside scope).

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
1. **Boot.** A fresh dev fabric is minted under the evidence root (the
   caller's ``evidence_root``, or ``scratch`` when none is supplied) from
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
resolver; a ``scratch`` or ``evidence_root`` inside ``config_root``, or one
inside the other; an environment variable a
source names that the process lacks (with the document's own remedy); a
``door:`` asserting a tenant other than the deployment's (R-6, refused by the
loader); a ``substrate:`` setting the declared adapter does not take as a
path, so no question's store could be verified fresh
(:class:`~ccf.products.resolver.AcquisitionOverUnverifiableStore`; SEC-020
P4 (a), ``D-IMPL-378``).

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

import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, runtime_checkable

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactNotFound, ArtifactStoreProtocol, WriteKinds
from ccf.erasure.errors import ErasedContentRefused
from ccf.erasure.index import ErasureIndexProtocol, erasure_index_at
from ccf.erasure.store import (
    ErasureCompositionRefused,
    ErasureConsultingStore,
    ErasureIndexUnavailable,
    compose_erasure_consult,
)
from ccf.erasure.trust import ErasureTrust
from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    Authorized,
    CompositionRegister,
    DeclaredSkillGrant,
    ReplayMint,
    SkillGrant as SkillGrantKind,
    mint_at_composition,
)
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
from ccf.boot import compose_invalidation_sink
from ccf.controlplane.invalidation import ControlPlaneInvalidationSink
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
from ccf.deployment.manifest import (
    _path_valued_settings,
    keys_under_tenant,
    manifest_under_tenant,
    register_manifest_entries,
)
from ccf.graph.leases import LOCK_DIRECTORY_SETTING, sdk_managed_lock_directory
from ccf.graph.protocols import GraphView
from ccf.graph.registry import resolve as resolve_backend
from ccf.halflife.debt import DebtAssessment
from ccf.mcp.client import SyncMcpBridge, bearer_client_factory
from ccf.products.child_resolver import ChildQuestions, QuestionBoundChildResolver
from ccf.products.composite import (
    ADMITTED_CHILD_CONTRACT_CLASS,
    CHILD_QUESTION_CLASS,
    ChildContractView,
    CompositeAdmissionGate,
    CompositeChildResolverProtocol,
    RequestAwareChildResolverProtocol,
)
from ccf.products.constraints import PolicyConstraintResolver, TechnicalCapability
from ccf.products.contract import version_satisfies_floor
from ccf.products.disclosure import DisclosureLevel
from ccf.products.provenance import ProvenanceSource
from ccf.products.refusal import RefusalEnvelope, RequestIdentity, envelope_for
from ccf.products.request import ProductRequest, ProductRequestViolation
from ccf.products.resolver import (
    AcquisitionOverUnverifiableStore,
    PopulationQuestion,
    ProductGateProtocol,
    ProductNotResolvable,
    _refuse_shared_owner,
    ProjectionPlanFactoryProtocol,
    RefusalRecorderProtocol,
    ReplayRefusalRecorder,
    ResolverOutcome,
    PackagingTraceProtocol,
    build_governed_resolver,
    declared_refusal_recorder,
)
# G1-SDK-01 (Dave, 2026-10-11 16:23 MST, ruling 4): the resolver's own default
# clock, so "the caller composed no clock" is the identity test
# `compose_serve_clock` makes, rather than two different function objects.
from ccf.products.resolver import _utc_now as _sdk_serve_clock
from ccf.products.demonstration_clock import compose_serve_clock
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.expiry import refuse_undeclared_ttl_anchor
from ccf.projection.plan import Perspective
from ccf.replay.engine import (
    ErasedReplayOutcome,
    RefusalReplayOutcome,
    ReplayDivergence,
    ReplayOutcome,
    replay,
    replay_refusal,
)
from ccf.replay.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceEntry,
    NoGraphRetained,
    ReplayEvidenceAltered,
    ReplayEvidenceIndex,
    ReplayEvidenceUnavailable,
    file_sha256,
    require_record_address,
)
from ccf.replay.provenance import require_filed_by_record_writer
from ccf.replay.record import (
    NO_PRODUCT_ADDRESS,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
)
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import (
    IngressTemporalBound,
    SignalEnvelope,
    refuse_foreign_envelope,
)
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry
from ccf.skills.dispatch import McpSkillRegistry
from ccf.skills.grants import (
    ApprovalSink,
    GrantLedger,
    GrantRefusal,
    RefusingApprovalSink,
    SkillGrant,
)
from ccf.skills.producers import register_declared_producer

__ccf_mode__ = "algorithmic"

__all__ = [
    "AcquireProtocol",
    "AcquisitionContext",
    "PopulationAcquireProtocol",
    "PopulationAcquisitionContext",
    "AssessProtocol",
    "AssessmentContext",
    "ChildResolverFactory",
    "ConsumerContext",
    "DeclaredGrantRefused",
    "GrantNotInForce",
    "OpenedProduct",
    "open_product",
]


class GrantNotInForce(PermissionError):
    """A declared skill is not granted to the composing agent, and the paved road cannot grant it (D-IMPL-353 §1.6; D-IMPL-354).

    Until D-IMPL-353, :func:`open_product` derived the consumer chain by
    **requesting one grant per declared skill on the deployment's behalf** —
    the agent granting itself, under ``actor=agent.name``. A grant is a
    ``skill.grant`` door action: :meth:`~ccf.skills.grants.GrantLedger.request`
    requires ``Authorized[SkillGrant]``, a door kind that
    :func:`~ccf.authz.capability.mint_at_composition` refuses by overload and
    at runtime, because the composition root may mint exactly ``ReplayMint``
    and ``Register`` and nothing else. So the paved road **cannot** grant, and
    does not pretend to: it registers the declared agent, skills and regime
    (composition-time registrations, under ``Register``), reads which skills
    are already bound to the agent on this Control Plane, and refuses — by
    name, before anything is composed — when one the class needs is not. A
    grant made through a governed door by an authorized principal is what
    puts it in force; a deployment that could grant itself skills at open was
    the ambient authority the capability removes.

    **Ruled 2026-10-11 (Dave, 16:23 MST, ruling 4).** A deployment's DECLARED
    grants (``grants:`` in ``ccf_config.yaml``) are requested at composition,
    under the composition kind
    :class:`~ccf.authz.capability.DeclaredSkillGrant`, through the ledger's own
    tier 1 and tier 2 (:func:`open_product`; :class:`DeclaredGrantRefused` when
    the ledger refuses). This refusal now means the skill was declared under
    ``skills:`` and neither declared under ``grants:`` nor granted at a door.
    """


class DeclaredGrantRefused(GrantNotInForce):
    """A grant the deployment DECLARED (``grants:``) was refused by the grant ledger's own governance.

    Ruling 4 (Dave, 2026-10-11 16:23 MST; SDK-defined). The declared grant ran
    through :meth:`~ccf.skills.grants.GrantLedger.request` — tier 1, the
    policy-regime compatibility check, and tier 2, the regime's approval sink —
    and was not put in force. Raised at open, by name, before anything is
    composed; the refusal the ledger returned is :attr:`refusal` (``None`` when
    the grant was requested and left pending an approval the sink did not give).
    """

    def __init__(self, message: str, *, skill: str, refusal: object | None) -> None:
        super().__init__(message)
        self.skill = skill
        self.refusal = refusal


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
        instant: The question's ``asked_at`` — the bounded as-of boundary,
            not the fabric's clock. It is the instant every envelope's
            ``ingestion_timestamp`` must carry on this road
            (``refuse_foreign_envelope``) and what an SDK L1 adapter used
            inside ``acquire`` is constructed with
            (``clock=lambda: context.instant``); it reached ``acquire`` only
            after the resolver judged it inside the tenant's declared temporal
            window (`D-IMPL-358` D5). The fabric's own instants are read
            elsewhere — ``served_at`` once per serve in the resolver, and the
            write guard's ``ingress_at`` at the seam — and are never stamped
            onto the envelope: the observation stamp stays the question's
            bounded instant by ruling (`D-IMPL-364` SEC-008 B4; the bitemporal
            as-of read is the open row `D-IMPL-365`).
    """

    request: ProductRequest
    perspective: Perspective
    tenant_id: str
    sources: Mapping[str, Mapping[str, str]]
    instant: datetime


@dataclass(frozen=True)
class PopulationAcquisitionContext:
    """What a deployment's population phase is handed for one question.

    SEC-020, ``D-IMPL-378`` (Q7; SDK-defined, CLAUDE.md §11).
    :class:`AcquisitionContext` without the request: ``question`` is the
    effective request WITHOUT its subject
    (:class:`~ccf.products.resolver.PopulationQuestion`), so the part of the
    acquisition a deployment declares subject-independent cannot read the
    asked identifier from anything it is handed.

    Attributes:
        question: The effective request without its subject.
        perspective: Whose view the answer is served under.
        tenant_id: The tenant every envelope must be stamped for.
        sources: Every source setting the environment document declared.
        instant: The question's ``asked_at``, as on :class:`AcquisitionContext`.
    """

    question: PopulationQuestion
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


@dataclass(frozen=True)
class ConsumerContext:
    """What a hand-built child resolver is handed when it composes on the paved surface.

    The low road's hatch, made intentional (`D-IMPL-343`, the panel's finding
    on this half): a resolver built BEFORE open cannot see the registry the
    facade populates from ``producers:``, so a deployment that wants the
    SDK's registrations under its own resolver hands in a FACTORY
    (``build_children=``) and receives, here, exactly the objects the derived
    chain is built from — the ONE Control Plane, the ONE store, the ONE
    registry every declared producer is on, the deployment's tenant and its
    clock. Nothing here is a second instance of anything.

    Attributes:
        tenant_id: The deployment's tenant.
        control_plane: The registry the deployment opens into.
        artifact_store: The one replay store.
        mcp_skills: The registry the declared producers were registered on,
            or ``None`` when the deployment declares none.
        clock: The one clock.
        derived_children: The chain the SDK DERIVED from the deployment's own
            ``producers:``, ``skills:``, ``agent:`` and ``grants:`` declarations,
            registered and granted by composition — present when the deployment
            declares that chain beside ``build_children=`` (G4-F-08; Dave,
            2026-10-11 16:23 MST, ruling 4), ``None`` otherwise. A factory that
            only decides WHETHER to ask an optional child for this request (a
            request-scoped switch) wraps it and writes nothing to the Control
            Plane; whether a missing child refuses stays the requirement's own
            declaration (``required`` / ``absence_treatment``), judged by the
            composite, never by the factory.
        agent: The declared agent that chain's grants bind to, or ``None``.
    """

    tenant_id: str
    control_plane: ControlPlaneRegistry
    artifact_store: ArtifactStoreProtocol
    mcp_skills: McpSkillRegistry | None
    clock: Callable[[], datetime]
    derived_children: QuestionBoundChildResolver | None = None
    agent: AgentDefinition | None = None


#: The factory form of the composite hatch: given the facade's own objects,
#: return the child resolver the deployment composes with.
ChildResolverFactory = Callable[
    [ConsumerContext], CompositeChildResolverProtocol | RequestAwareChildResolverProtocol
]


@runtime_checkable
class AcquireProtocol(Protocol):
    """The developer's acquisition: read the sources, emit dated L1 envelopes.

    Returns an iterable of :class:`~ccf.signal.envelope.SignalEnvelope`, each
    stamped for the context's tenant at the context's instant and carrying
    the claim's own age as ``observed_time`` (`D-IMPL-331`, `CP03C-F-08`). An
    empty iterable is a legitimate answer: nothing is written, and the
    governed path then refuses on the product's own gate, with a record.

    **Called once more for a class that may withhold** (SEC-020, ``D-IMPL-378``
    ruling P6 (a); Q10 amended to exactly this call). When the class may
    withhold its subject and the plan factory declares no early policy, the
    paved road first calls ``acquire`` with a context whose request carries
    :data:`~ccf.products.resolver.UNHELD_SUBJECT_PROBE` as its subject,
    immediately before the call for the question's subject. What it returns
    for that identifier is ingested like any answer, and if it changed the
    fabric the question is refused,
    :class:`~ccf.products.resolver.PopulationReadInSubjectKeyedPhase`, before
    ``acquire`` is handed the question's subject. Return nothing for an
    identifier your sources do not hold: a held refusal for the probe
    identifier refuses every question (OWED-RULINGS-3 item 4 (b)), answered
    and recorded as
    :data:`~ccf.products.resolver.UNHELD_SUBJECT_PROBE_REFUSAL`, the SDK's one
    constant, with no part of the refusal as ``acquire`` stated it
    (``D-IMPL-378`` repair 2.3 (b)). Read what does not depend on the subject
    in ``population`` instead (:class:`PopulationAcquireProtocol`).
    SEC-020 stays OPEN: an ``acquire`` that recognizes the probe identifier is
    not detected.

    **Called twice more under a declared early policy** (``D-IMPL-378``
    decision 4 (a); Q10 amended to exactly these calls). When the plan factory
    declares an early policy, the paved road first calls ``acquire`` with
    :data:`~ccf.products.resolver.UNHELD_SUBJECT_PROBE` and then with the
    policy's declared stand-in as the subject, immediately before the call for
    the question, and refuses the question,
    :class:`~ccf.products.resolver.UndisclosedSubjectSubstituteIsHeld`, if the
    fabric names the stand-in or if what ``acquire`` returned for the stand-in
    added anything to what it returned for the probe identifier — an entity, a
    relationship, a claim value, or evidence from another source or passage; the
    envelope id and the receipt instant each delivery carries are set aside
    (``D-IMPL-378`` repair 1.3). Hold nothing for the stand-in you declare.
    Under such a policy, a refusal ``acquire`` raises, for any question of the
    class, is served and recorded as
    :data:`~ccf.products.resolver.EARLY_POLICY_ACQUISITION_REFUSAL`: its own
    kind, cause, code and text are not kept (``D-IMPL-378`` repair 2.2 (a)).
    """

    def __call__(self, context: AcquisitionContext) -> Iterable[SignalEnvelope]: ...


@runtime_checkable
class PopulationAcquireProtocol(Protocol):
    """The deployment's population phase: read what does not depend on the subject (SEC-020 Q7).

    ``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). Declared to
    :func:`open_product` as ``population``, on an object separate from
    ``acquire`` (one shared owner is refused at open,
    :class:`~ccf.products.resolver.PopulationPhaseSharesAnOwner`). The paved
    road calls it once per question, FIRST, with a
    :class:`PopulationAcquisitionContext` — no request, no subject — and then
    ``acquire`` for the subject-keyed phase, also once for the question's
    subject (plus, for a class that may withhold and declares no early policy,
    once for the P6 probe immediately before it, and, for a class with a
    declared early policy, twice to verify its stand-in;
    :class:`AcquireProtocol`).
    Both phases' envelopes are held to the tenant and the instant and ingested
    through the same L2 worker. The two must not overlap: an entity the
    population phase returns
    is not returned again by ``acquire``.
    """

    def __call__(self, context: PopulationAcquisitionContext) -> Iterable[SignalEnvelope]: ...


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
        evidence_root: Path,
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
        erasure_index: ErasureIndexProtocol,
        erasure_trust: ErasureTrust,
        refusal_recorder: ReplayRefusalRecorder,
        acquire: AcquireProtocol,
        project: ProjectionPlanFactoryProtocol,
        assess: AssessProtocol,
        gate: ProductGateProtocol | None,
        clock: Callable[[], datetime],
        constraint_resolver: PolicyConstraintResolver | None,
        capabilities: tuple[TechnicalCapability, ...] | None,
        children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None,
        packaging_trace: PackagingTraceProtocol | None = None,
        mcp_skills: McpSkillRegistry | None = None,
        bridge: SyncMcpBridge | None = None,
        agent: AgentDefinition | None = None,
        population: PopulationAcquireProtocol | None = None,
        honors_demonstration_serve_instant: bool = False,
        invalidation_sink: ControlPlaneInvalidationSink | None = None,
    ) -> None:
        self.config_root = config_root
        self.config_path = config_path
        self.scratch = scratch
        #: `D-IMPL-383` (Dave, 2026-10-16): where the durable replay evidence
        #: lives — the per-question graphs, the default replay store and the
        #: decision → graph index. ``scratch`` itself when the caller supplied
        #: no ``evidence_root``, so an undeclared root keeps today's behavior.
        self.evidence_root = evidence_root
        self.config = config
        # P1 (a) (D-IMPL-378; Tuesday GO item 4): the standard product boot
        # supplies the SDK-managed identity-lock directory, computed once at
        # open so an unusable one refuses before any question. Only for an
        # adapter whose connection contract takes the lock-directory setting;
        # nothing here names a substrate (CINV-04). It sits under the root the
        # graphs are minted in, so every process writing one of those files
        # takes the same lock whatever its own scratch is.
        self.writer_lock_directory: str | None = None
        if LOCK_DIRECTORY_SETTING in resolve_backend(config.backend).registration.config_model.model_fields:
            self.writer_lock_directory = sdk_managed_lock_directory(os.path.realpath(evidence_root))
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
        #: SEC-009 (`D-IMPL-374` (4), C1): the durable erasure index this
        #: product's store consults and every resolver it builds is handed.
        self.erasure_index = erasure_index
        #: SEC-009 (fix round 5, R1, R2, R4): the deployment's per-tenant
        #: erasure trust root the store verifies every erasure against — and
        #: which every resolver and door built over this product composes with.
        self.erasure_trust = erasure_trust
        self._refusal_recorder = refusal_recorder
        #: `D-IMPL-383`: the decision → retained-graph index, under the
        #: evidence root beside the declared store, named from it, never inside it.
        self.evidence = ReplayEvidenceIndex(
            evidence_root=evidence_root,
            index_root=evidence_root / f"{replay.store_dirname}-evidence-index",
            tenant_id=tenant_id,
        )
        self._invalidation_sink = invalidation_sink
        self.mcp_skills = mcp_skills
        self.agent = agent
        self._bridge = bridge
        self._acquire = acquire
        self._population = population
        self._project = project
        self._assess = assess
        self._gate = gate
        self._clock = clock
        #: G1-SDK-01: the startup snapshot (C1-late, ruled (a)). True only when
        #: the deployment's ``ccf_config.yaml`` declared
        #: ``demonstration_serve_instant:`` at open AND the caller composed no
        #: clock of its own. A declaration registered after open is not this
        #: snapshot, so it still meets the composed clock and is refused by name.
        self._honors_demonstration_serve_instant = honors_demonstration_serve_instant
        self._constraint_resolver = constraint_resolver
        self._capabilities = capabilities
        self._children = children
        self._packaging_trace = packaging_trace

    @property
    def invalidation_sink(self) -> ControlPlaneInvalidationSink:
        """Where this deployment records an invalidation boundary an external event sets.

        SDK-defined (CLAUDE.md §8.1, §11; round 5, item 4 — Dave, 2026-10-11
        20:19 MST: *"Invalidation must use the existing scoped writer
        capability."*). Composed once, at open, over this product's ONE Control
        Plane by :func:`ccf.boot.compose_invalidation_sink` — the recipe every
        fabric boot uses for its graph writer — holding the
        ``InvalidationRecordRegister`` capability for THIS product's tenant
        only. ``record(tenant_id=..., entity_uri=..., invalidated_from=...,
        reason=..., source=...)`` advances that entity's boundary as a new
        audited version of its record (a boundary that does not move registers
        nothing); a tenant this product was not opened for is refused
        :class:`~ccf.controlplane.invalidation.InvalidationUnauthorized` before
        anything is read or written. Every later question's dependency
        invalidation gate reads the record.

        Raises:
            RuntimeError: this object was not built by :func:`open_product`.
        """
        if self._invalidation_sink is None:
            raise RuntimeError(
                "this OpenedProduct holds no invalidation sink; it is composed by"
                " open_product, the composition root that mints its capability"
            )
        return self._invalidation_sink

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
        chosen = perspective if perspective is not None else self.default_perspective
        admitted = self._admit_lane(
            request, perspective=chosen, address=(request.schema_name, request.schema_version)
        )
        if isinstance(admitted, RefusalEnvelope):
            return self._published(admitted, request=request, graph=None)
        # `D-IMPL-383`: the pending marker is written BEFORE the graph is
        # minted, the mapping is published only AFTER the graph is closed, and
        # the outcome is returned only after that. An interruption anywhere in
        # between leaves the marker — the explicit incomplete state.
        minted = self._mint()
        # Wall-clock instants, never the deployment's clock: evidence must not
        # change what the decision sees, and a composed clock can tick per read.
        self.evidence.begin(graph=minted.name, request=admitted, started_at=_utc_now())
        fabric = self._boot(minted)
        try:
            resolver = build_governed_resolver(**self.build_arguments(fabric))
            outcome = resolver(
                tenant=self.tenant_id,
                product_class=self.declaration.schema_name,
                version=self.declaration.schema_version,
                perspective=chosen,
                request=admitted,
            )
        finally:
            fabric.handle.close()
        return self._published(outcome, request=admitted, graph=minted)

    def record_of(self, outcome: ResolverOutcome) -> DecisionReplayRecord:
        """The decision record behind ``outcome``, read from the ONE store.

        Served and refused decisions alike: a served product carries its
        record's content address on ``replay_ref``; a refusal carries the
        record's URI, which the store resolves. One store, so one read idiom.

        The bytes there are returned as a record only where they hash to the
        address the outcome names — the replay engine's own arithmetic
        (:func:`~ccf.replay.engine.resolve_artifact`, ``D-IMPL-89``), so bytes
        altered under a reference are refused rather than handed back as the
        decision's (Dave's E1 (a), ``D-IMPL-378``: *"Preserve record
        content-address integrity"*) — and only where the store shows the
        fabric's record writer filed them under the tenant they name
        (`D-IMPL-378`): an outcome can name any address, and a record-shaped
        artifact filed on a client lane is not a decision record.

        **An operator/auditor handle** (Dave's E2 (i), ``D-IMPL-378``,
        2026-10-08: *"trusted operator/auditor handles holding the underlying
        store may remain unrestricted. Agent-accessible in-process interfaces
        must still enforce Q12."*). Its caller holds this product's
        ArtifactStore (``artifact_store``) and can read the same bytes
        directly, so it is not held to Q12's default-deny on owner read-back.
        An agent reads records only through the governed evidence reads
        (``runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference``),
        which hold it. Handing an opened product, or anything else holding the
        store, to an agent hands the agent the store (measured by
        ``tests/http_api/test_sec020_e2i_operator_boundary.py``).

        Raises:
            ccf.replay.engine.ReplayDivergence: the stored bytes do not hash to
                the address the outcome names.
            ccf.replay.provenance.RecordNotFiledByRecordWriter: the store
                shows no such filing — an
                :class:`~ccf.artifacts.protocol.ArtifactNotFound`, as an
                address holding nothing is.
            ccf.replay.provenance.UnattributableRecordStore: the store cannot
                say who filed an address.
        """
        if isinstance(outcome, ServedProduct):
            address = outcome.replay_ref.content_address
        else:
            address = self.artifact_store.resolve_uri(uri=outcome.replay_reference)
        payload = self.artifact_store.get(content_address=address)
        # E1 (a) (`D-IMPL-378`): byte fidelity FIRST, as replay holds it — the
        # address is the sha256 of the stored canonical bytes, so the raw
        # payload is what is verified, before it is believed or parsed.
        reproduced = hashlib.sha256(payload).hexdigest()
        if reproduced != address:
            raise ReplayDivergence(
                f"the bytes at {address!r} hash to {reproduced!r}; the store"
                " returned bytes that are not the record this outcome names"
                " (D-IMPL-89; D-IMPL-378 E1 (a))"
            )
        record = DecisionReplayRecord.model_validate_json(payload)
        require_filed_by_record_writer(
            self.artifact_store, content_address=address, tenant_id=record.tenant_id
        )
        return record

    # --- durable, addressable replay evidence (`D-IMPL-383`) -------------------------

    @property
    def refusal_recorder(self) -> RefusalRecorderProtocol:
        """The recorder a DOOR records its own denials through — each one mapped (`D-IMPL-383`).

        A door's entitlement step refuses before :meth:`resolve` runs and
        records through this seam, never through :meth:`answer`. This recorder
        appends the record through the product's own one, then publishes the
        decision's no-graph evidence mapping, so a door-recorded refusal replays
        like every other refusal reached before a graph (instruction 5) and is
        never reported as interrupted (close panel, 2026-10-15).
        """
        return _EvidencePublishingRecorder(inner=self._refusal_recorder, opened=self)

    def _require_mapping_agrees(self, entry: EvidenceEntry, payload: bytes) -> None:
        """Raise :class:`ReplayDivergence` where ``entry`` contradicts the record's own bytes."""
        reproduced = hashlib.sha256(payload).hexdigest()
        if reproduced != entry.record_address:
            raise ReplayDivergence(
                f"the bytes at {entry.record_address!r} hash to {reproduced!r}; the store"
                " returned bytes that are not the decision record (D-IMPL-89)"
            )
        record = DecisionReplayRecord.model_validate_json(payload)
        served = record.content_generation_path.product_content_address != NO_PRODUCT_ADDRESS
        if served != (entry.outcome == "served"):
            raise ReplayDivergence(
                f"the evidence mapping for {entry.record_address} says {entry.outcome!r},"
                f" and the decision record says {'served' if served else 'refused'};"
                " the index was altered"
            )
        if record.tenant_id != entry.tenant_id:
            raise ReplayDivergence(
                f"the evidence mapping for {entry.record_address} names tenant"
                f" {entry.tenant_id!r}, and the decision record names {record.tenant_id!r}"
            )

    def _published_refusal(
        self, envelope: RefusalEnvelope, *, request: ProductRequest | None, recorded_at: datetime
    ) -> None:
        """Publish the no-graph mapping of a refusal a door recorded directly."""
        identity = envelope.request
        self.evidence.publish(
            EvidenceEntry(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                record_address=self.artifact_store.resolve_uri(uri=envelope.replay_reference),
                tenant_id=self.tenant_id,
                outcome="refused",
                refusal_reason=envelope.reason,
                product_class=request.schema_name if request is not None else identity.product_id,
                product_version=(
                    request.schema_version if request is not None else identity.product_version or ""
                ),
                subject=request.subject if request is not None else "",
                parameters=(
                    request.model_dump(mode="json")["parameters"]
                    if request is not None
                    else json.loads(json.dumps(dict(identity.parameters), default=str))
                ),
                asked_at=request.asked_at if request is not None else identity.temporal_boundary or recorded_at,
                decided_at=_utc_now(),
                graph=None,
                graph_required=False,
                graph_sha256=None,
            )
        )

    def _published(
        self, outcome: ResolverOutcome, *, request: ProductRequest, graph: Path | None
    ) -> ResolverOutcome:
        """Publish ``outcome``'s evidence mapping, then return it — the last step of every decision.

        ``graph`` is the question's closed substrate, or ``None`` for a refusal
        reached before one was minted, which the mapping then states as "no
        graph required" (the reviewer's instruction 5). A failure to publish
        propagates: the decision's record exists, its pending marker stays,
        and the outcome is NOT returned as durably replayable (instruction 3).
        """
        if isinstance(outcome, ServedProduct):
            address = outcome.replay_ref.content_address
            refusal_reason = None
        else:
            address = self.artifact_store.resolve_uri(uri=outcome.replay_reference)
            refusal_reason = outcome.reason
        self.evidence.publish(
            EvidenceEntry(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                record_address=address,
                tenant_id=self.tenant_id,
                outcome="served" if refusal_reason is None else "refused",
                refusal_reason=refusal_reason,
                product_class=request.schema_name,
                product_version=request.schema_version,
                subject=request.subject,
                parameters=request.model_dump(mode="json")["parameters"],
                asked_at=request.asked_at,
                decided_at=_utc_now(),
                graph=None if graph is None else graph.name,
                graph_required=graph is not None,
                graph_sha256=None if graph is None else file_sha256(graph),
            )
        )
        return outcome

    def replay_decision(
        self, record_address: str
    ) -> ReplayOutcome | RefusalReplayOutcome | ErasedReplayOutcome:
        """Replay the decision recorded at ``record_address`` from its retained evidence.

        SDK-defined (CLAUDE.md §7.4, §8.3; `D-IMPL-383`). Resolves the
        decision's evidence mapping by its record address, checks the retained
        graph is present and byte-identical to what the question closed, boots
        it READ-ONLY through the deployment's own boot path, rebuilds the
        recorded environment and hands everything to the existing engine —
        :func:`~ccf.replay.engine.replay` for a served decision,
        :func:`~ccf.replay.engine.replay_refusal` for a refused one. Every
        engine check is retained; nothing here re-derives from a source.

        The low-level engine calls, which take an explicit reader, are
        unchanged; this is a convenience over them.

        **An operator/auditor handle**, as :meth:`record_of` is: its caller
        holds this product's store.

        Raises:
            ValueError: ``record_address`` is not a content address.
            ccf.replay.evidence.ReplayEvidenceUnavailable: no mapping was
                published (the decision is unknown, or was interrupted before
                its mapping — reported as incomplete), the retained graph is
                gone, or the store no longer holds the record.
            ccf.replay.evidence.ReplayEvidenceAltered: the retained graph's
                bytes changed after the decision — a divergence, never
                "missing".
            ccf.replay.engine.ReplayDivergence: the record's bytes, or the
                reproduction, disagree with what was recorded.
        """
        from ccf.replay.environment import RecordedEnvironment  # noqa: PLC0415 (cycle)

        require_record_address(record_address)
        entry = self.evidence.entry(record_address)
        if entry is None:
            if self.artifact_store.exists(content_address=record_address):
                detail = (
                    "the decision record is in the store but this tenant's evidence index"
                    " holds no mapping for it: the decision is incomplete (interrupted"
                    " between writing its record and publishing its mapping) or is not"
                    " this tenant's"
                )
            else:
                detail = "neither a decision record nor an evidence mapping exists for this address"
            pending = self.evidence.incomplete()
            if pending:
                detail += f"; {len(pending)} incomplete decision(s) are held in this evidence root"
            raise ReplayEvidenceUnavailable(record_address=record_address, detail=detail)
        try:
            payload: bytes | None = self.artifact_store.get(content_address=record_address)
        except ErasedContentRefused:
            # SEC-009 (`D-IMPL-374` (4)): an erasure is a recorded decision, not
            # an absence. The engine meets the same refusal at its prologue and
            # returns the disclosure, before it would consult a graph.
            payload = None
        except ArtifactNotFound:
            raise ReplayEvidenceUnavailable(
                record_address=record_address,
                detail="the evidence mapping names this decision, and the store no longer holds its record",
            ) from None
        if payload is not None:
            # Instruction 4: the content-addressed RECORD is the authority, and a
            # mutable mapping that disagrees with it is corruption — divergence,
            # never "missing" (close panel, 2026-10-15).
            self._require_mapping_agrees(entry, payload)
        if payload is None or entry.graph is None:
            not_read = NoGraphRetained(record_address)
            engine = replay if entry.outcome == "served" else replay_refusal
            # The record's policy bindings resolve against the Control Plane,
            # which this deployment registers only as part of a boot. A replay
            # after a restart that boots no graph would find it empty (close
            # panel, 2026-10-15: a pre-graph refusal replayed FIRST after a
            # restart was `ReplayUnresolvable`). So the deployment is booted
            # once over an empty, throwaway substrate outside the evidence root,
            # purely to register, and closed; the engine is still handed
            # `NoGraphRetained`, so no graph is read for this decision.
            with tempfile.TemporaryDirectory(prefix="ccf-replay-register-") as throwaway:
                registering = self._boot(Path(throwaway) / self._mint().name)
                registering.handle.close()
            return engine(
                record_address=record_address,
                store=self.artifact_store,
                reader=not_read,  # never consulted: see NoGraphRetained
                control_plane=self.control_plane,
                environment=not_read,
            )
        graph = self.evidence.graph_path(entry)
        if graph.is_symlink():
            raise ReplayDivergence(
                f"the retained graph {entry.graph!r} for {record_address} is a symlink;"
                " retained evidence lives under the evidence root, and a link to"
                " anywhere else is not that evidence, whatever bytes it reaches"
            )
        if not graph.is_file():
            raise ReplayEvidenceUnavailable(
                record_address=record_address,
                path=entry.graph,
                detail="the retained graph this decision read is no longer in the evidence root",
            )
        found = file_sha256(graph)
        assert entry.graph_sha256 is not None  # the entry's own validator holds this
        if found != entry.graph_sha256:
            raise ReplayEvidenceAltered(
                record_address=record_address,
                path=entry.graph,
                expected_sha256=entry.graph_sha256,
                found_sha256=found,
            )
        reproduced = hashlib.sha256(payload).hexdigest()
        if reproduced != record_address:
            raise ReplayDivergence(
                f"the bytes at {record_address!r} hash to {reproduced!r}; the store"
                " returned bytes that are not the decision record (D-IMPL-89)"
            )
        record = DecisionReplayRecord.model_validate_json(payload)
        fabric = load_config_and_boot(
            self.config_path,
            registry=self.control_plane,
            connection=self._connection(graph),
            read_only=True,
        )
        try:
            environment = RecordedEnvironment(record=record, opened=self, fabric=fabric)
            if entry.outcome == "served":
                return replay(
                    record_address=record_address,
                    store=self.artifact_store,
                    reader=fabric.handle.reader,
                    control_plane=self.control_plane,
                    environment=environment,
                )
            return replay_refusal(
                record_address=record_address,
                store=self.artifact_store,
                reader=fabric.handle.reader,
                control_plane=self.control_plane,
                environment=environment,
            )
        finally:
            fabric.handle.close()

    # --- the serve clock (G1-SDK-01) ---------------------------------------------

    def _admission_clock(self) -> Callable[[], datetime]:
        """The clock handed to the builder as ``admission_clock``.

        Where the deployment declared a demonstration serve instant at open and
        the caller composed no clock, it is the SDK's own default clock, so
        :func:`~ccf.products.demonstration_clock.compose_serve_clock` reads "no
        composed clock" and serves at the declaration, with every one of its
        checks (several declarations, the SDK's own development backends).
        Otherwise it is the clock this product was opened with — a declaration
        beside it is two authorities, refused by name.
        """
        return _sdk_serve_clock if self._honors_demonstration_serve_instant else self._clock

    def _ingress_clock(self, fabric: BootedFabric) -> Callable[[], datetime]:
        """The fabric's instant the ingress temporal guard judges envelopes at.

        On a declared demonstration instant it is the declared serve clock, so
        the write guard and the serve judge one question against one instant;
        it is composed through the same
        :func:`~ccf.products.demonstration_clock.compose_serve_clock`, so every
        refusal the resolver would raise is raised here first, before anything
        is acquired. Otherwise it is the opened clock, as before.
        """
        if not self._honors_demonstration_serve_instant:
            return self._clock
        return compose_serve_clock(
            control_plane=self.control_plane,
            fabric=fabric,
            artifact_store=self.artifact_store,
            admission_clock=_sdk_serve_clock,
            sdk_clock=_sdk_serve_clock,
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
            # `D-IMPL-341`: the λ_c table's manifest key, stated for the
            # resolver — the adapter above already reads the table for `F`; the
            # resolver reads it for the instant an evidence-anchored window runs
            # from, and pins it on the record.
            "evidence_clock_key": keys.half_life,
            "product_gate": self._gate,
            "artifact_store": self.artifact_store,
            "erasure_index": self.erasure_index,
            "erasure_trust": self.erasure_trust,
            "replay_record_class": self.replay.record_class,
            "query_pin_class": self.replay.query_pin_class,
            "refusal_recorder": self._refusal_recorder,
            "acquisition": self._acquisition_seam(fabric),
            # SEC-020 Q7 (`D-IMPL-378`): the declared population phase, stated
            # only when the deployment declared one.
            **(
                {"population_acquisition": self._population_seam(fabric)}
                if self._population is not None
                else {}
            ),
            # §7.10.4's Mode 2 footprint. `None` for every Mode 1 deployment,
            # and dimension 3's no-packaging sentinel is then the true claim.
            "packaging_trace": self._packaging_trace,
            "composite_children": self._children,
            "admission_clock": self._admission_clock(),
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
        by the contract by name rather than quietly widened (R-8). The lane
        admission is :meth:`_admit_lane`, shared with :meth:`answer`.

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
        admitted = self._admit_lane(request, perspective=perspective, address=(product_class, version))
        if isinstance(admitted, RefusalEnvelope):
            return self._published(admitted, request=request, graph=None)
        return self.answer(admitted, perspective=perspective)

    def _admit_lane(
        self, request: ProductRequest, *, perspective: Perspective, address: tuple[str, str]
    ) -> ProductRequest | RefusalEnvelope:
        """Hold an address — class and FLOOR — to this product, once, for both public verbs.

        :meth:`resolve` holds the door's address; :meth:`answer` holds the
        request's own class and lane the same way, so a request carrying a
        floor is served at the served lane whichever verb it reaches (the
        panel's finding on this half: the two verbs had diverged). Returns the
        request to answer — at the ONE lane this product serves, so the record
        says which — or the recorded ``class-mismatch`` refusal.
        """
        product_class, version = address
        declared_name = self.declaration.schema_name
        served_lane = self.declaration.schema_version
        if product_class != declared_name:
            return self._refuse_address(
                request,
                perspective=perspective,
                address=address,
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
                address=address,
                key="schema_version",
                detail=(
                    f"this product serves {declared_name!r} at lane {served_lane!r},"
                    f" and the address asks from floor {version!r}; a served lane"
                    " satisfies a floor when it shares the floor's major and is"
                    f" at or above it, and {served_lane!r} does not satisfy"
                    f" {version!r} (D-IMPL-343 R-13)"
                ),
            )
        if request.schema_version != served_lane or request.schema_name != declared_name:
            return request.model_copy(
                update={"schema_name": declared_name, "schema_version": served_lane}
            )
        return request

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
        # `D-IMPL-358` step 5, and this site is the reason the rule is worth
        # stating as a rule. A question boundary WAS available here — three lines
        # above, ``request.asked_at`` already supplies ``temporal_boundary`` on
        # the identity — and ``recorded_at`` took the live clock anyway, so an
        # address refusal's dimension-1 boundary moved with when the refusal
        # happened rather than with what was asked. The two instants are now
        # separate and both are carried: the QUESTION's instant bounds the
        # record, and the LIVE instant this door determined at is measured ONCE
        # here and travels as ``served_at`` beside it.
        determined_at = self._clock()
        return self._refusal_recorder.record(
            envelope_for(violation, request=identity),
            perspective=perspective,
            recorded_at=request.asked_at,
            served_at=determined_at,
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

    def _boot(self, minted: Path | None = None) -> BootedFabric:
        """Mint a fresh per-question fabric under the evidence root and boot it.

        ``minted`` is the path :meth:`_mint` chose, when the caller needed it
        before the boot (:meth:`answer` writes the evidence marker first);
        otherwise one is minted here.

        The substrate's SETTING, prefix and suffix are the environment
        document's; the uuid is what makes "per question" true rather than
        nominal (`CP03C-F-02`: a door answering several questions under one
        root booted the SAME file every time). Nothing here names a backend.

        Booted ``for_question`` (SEC-020, ``D-IMPL-378`` Q9): the boot verifies
        the minted substrate does not exist yet, and the governed call that
        acquires into this fabric claims it for the one question it answers.
        """
        return load_config_and_boot(
            self.config_path,
            registry=self.control_plane,
            connection=self._connection(self._mint() if minted is None else minted),
            for_question=True,
        )

    def _mint(self) -> Path:
        """The path of a fresh per-question substrate under the evidence root (not yet created)."""
        substrate = self.environment.substrate
        return self.evidence_root / f"{substrate.prefix}_{uuid.uuid4().hex}{substrate.suffix}"

    def _connection(self, substrate_path: Path) -> dict[str, object]:
        """The connection settings that point the declared adapter at ``substrate_path``."""
        connection: dict[str, object] = {self.environment.substrate.setting: str(substrate_path)}
        if self.writer_lock_directory is not None:
            connection[LOCK_DIRECTORY_SETTING] = self.writer_lock_directory
        return connection

    def _acquisition_seam(
        self,
        fabric: BootedFabric,
        *,
        population_phase: PopulationAcquireProtocol | None = None,
    ) -> Callable[..., None]:
        """The declared acquisition boundary for one question (`D-IMPL-343` R-4).

        Called by the resolver ONCE for the question's subject, with the
        EFFECTIVE request, after resolution and before the graph read. Before
        that call, and only one of the two, as :class:`AcquireProtocol` states:
        for a class the P6 probe reads, once more, with
        :data:`~ccf.products.resolver.UNHELD_SUBJECT_PROBE` as the subject
        (``D-IMPL-378`` ruling P6 (a)); for a class with a declared early
        policy, which the probe does not read, twice more, with the probe
        identifier and then the declared stand-in (``D-IMPL-378`` decision
        4 (a)). The deployment's ``acquire`` runs at the values governance
        resolved; every envelope is held to the tenant and the instant before
        L2's one writer sees it.

        With ``population_phase`` (SEC-020 Q7, ``D-IMPL-378``; see
        :meth:`_population_seam`) it returns the declared population phase
        instead: called once per question, before the subject-keyed seam, and
        handed a :class:`PopulationAcquisitionContext` and nothing else. Both
        phases reach the writer through the one guarded loop below, so this
        method stays the L2 writer's only governed caller (`D-IMPL-364` B1).
        """
        worker = fabric.handle.worker
        tenant_id = self.tenant_id
        sources = self.sources
        acquire = self._acquire
        # `D-IMPL-358` step 8: the tenant-bound temporal write guard, composed HERE
        # — the trusted ingress composition — and bound ONCE per seam rather than
        # per envelope. The roster is this deployment's own tenant and the policy
        # is pinned for it at composition, so nothing on the ingest path resolves
        # a policy and no envelope can introduce a tenant.
        temporal_bound = IngressTemporalBound.at_composition(
            registry=self.control_plane, tenant_ids=(tenant_id,)
        )
        clock = self._ingress_clock(fabric)

        def ingest(envelopes: Iterable[SignalEnvelope], *, asked_at: datetime) -> None:
            # THE FABRIC'S instant, read ONCE per acquisition and handed to the
            # guard — never `request.asked_at`. `refuse_foreign_envelope` above
            # already requires `ingestion_timestamp == asked_at` on this road, so
            # judging the instant against the question's own would compare a value
            # with itself: the age would always be zero and the guard could never
            # fire. Measured — the first draft of this wiring did exactly that and
            # the end-to-end control caught it.
            ingress_at = clock()
            for envelope in envelopes:
                refuse_foreign_envelope(envelope, tenant_id=tenant_id, asked_at=asked_at)
                # BEFORE the single writer sees it. An out-of-window or undeclared
                # envelope raises here, so no claim lands and nothing is restamped.
                # The raise is `TemporalWriteRefused`, which `SDK_SEAM_REFUSALS`
                # converts into a governed refusal WITH a record at this seam
                # (`D-IMPL-364` SEC-008 B2) — this is a governed serve, so the
                # record is the serve's own, not one fabricated for a write.
                temporal_bound.refuse_outside_window(envelope, now=ingress_at)
                worker.ingest(envelope)

        if population_phase is not None:
            declared = population_phase

            def population(*, question: PopulationQuestion, perspective: Perspective) -> None:
                context = PopulationAcquisitionContext(
                    question=question,
                    perspective=perspective,
                    tenant_id=tenant_id,
                    sources=sources,
                    instant=question.asked_at,
                )
                ingest(declared(context), asked_at=question.asked_at)

            return population

        def seam(*, request: ProductRequest, perspective: Perspective) -> None:
            context = AcquisitionContext(
                request=request,
                perspective=perspective,
                tenant_id=tenant_id,
                sources=sources,
                instant=request.asked_at,
            )
            ingest(acquire(context), asked_at=request.asked_at)

        return seam

    def _population_seam(self, fabric: BootedFabric) -> Callable[..., None]:
        """The declared population phase for one question (SEC-020 Q7, ``D-IMPL-378``).

        Called by the resolver once per question, before the subject-keyed
        seam, with a question that carries no subject; the deployment's
        ``population`` is handed a :class:`PopulationAcquisitionContext`
        built from it and nothing else. Composed by :meth:`_acquisition_seam`,
        so it reaches L2's one writer through the same guarded loop.
        """
        population_phase = self._population
        assert population_phase is not None  # stated only when declared
        return self._acquisition_seam(fabric, population_phase=population_phase)


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
    evidence_root: Path | str | None = None,
    acquire: AcquireProtocol,
    project: ProjectionPlanFactoryProtocol,
    assess: AssessProtocol,
    gate: ProductGateProtocol | None = None,
    questions: ChildQuestions | None = None,
    clock: Callable[[], datetime] = _utc_now,
    environ: Mapping[str, str] | None = None,
    control_plane: ControlPlaneRegistry,
    erasure_trust: ErasureTrust,
    artifact_store: ArtifactStoreProtocol | None = None,
    constraint_resolver: PolicyConstraintResolver | None = None,
    capabilities: tuple[TechnicalCapability, ...] | None = None,
    approval_sink: ApprovalSink | None = None,
    children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None = None,
    build_children: ChildResolverFactory | None = None,
    packaging_trace: PackagingTraceProtocol | None = None,
    erasure_index: ErasureIndexProtocol | None = None,
    population: PopulationAcquireProtocol | None = None,
) -> OpenedProduct:
    """Open the declared product under ``config_root``: bind the verbs, read the bindings, refuse early.

    Reads the two documents (``ccf_config.yaml`` through the environment
    document's ``config``, and ``ccf_environment.yaml``), derives the manifest
    keys, parses the bindings the road reads, resolves every source variable
    the environment names, and builds the ONE store and the ONE recorder.
    **Boots nothing**: every question boots its own fabric (module docstring,
    §1), so opening is cheap and refuses only on what a document says. So a
    process that only opens cannot replay an earlier record: build the replay
    environment first,
    :class:`~ccf.replay.environment.RecordedEnvironment` (`D-IMPL-378` R-A2).

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
        scratch: The ephemeral working directory. With no ``evidence_root``
            it is also the evidence root: per-question substrate files, the
            replay store (under the declared ``store_dirname``) and its
            evidence index live here. Refused inside ``config_root`` by name
            — a tree that wrote its own fabrics beside its own documents would
            be one nobody could clean.
        evidence_root: The durable directory for replay evidence (`D-IMPL-383`,
            Dave, 2026-10-16): when supplied, the per-question substrate files,
            the default replay store and the decision → graph index live here
            instead of under ``scratch``, so a decision replays by its record
            address after a restart. ``None`` keeps everything under
            ``scratch``. Never read from the environment by the SDK: a
            launcher that takes the location from a variable validates it and
            passes it here. Refused inside ``config_root``, and refused when it
            and ``scratch`` lie one inside the other.
        acquire: The deployment's acquisition (:class:`AcquireProtocol`).
        population: The deployment's population phase, when part of
            what it reads does not depend on the subject
            (:class:`PopulationAcquireProtocol`; SEC-020 Q7, ``D-IMPL-378``):
            called once per question before ``acquire`` and handed no subject.
            Refused at open when it shares an owner with ``acquire``
            (:class:`~ccf.products.resolver.PopulationPhaseSharesAnOwner`), or
            when the walk that looks for one cannot read what an object it
            reaches holds (:class:`~ccf.products.resolver.SharedOwnerWalkIncomplete`).
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
        control_plane: The DEPLOYMENT's registry, opened INTO. **Required, no
            default and no fresh-registry fallback** (SEC-009, fix round 4,
            ruling 5): the erasure consult verifies every approval's HITL
            policy, approval policy and workflow definition through it, so a
            registry that lacked them would mark every genuine erasure
            ``index-unsupported``. ``None`` is refused by name.
        erasure_trust: The deployment's erasure trust root (SEC-009, fix round
            5, R1, R2, R4): for each tenant that may erase — this product's, for
            a single-tenant deployment — an
            :class:`~ccf.erasure.ErasureAuthority` naming the HITL policy key
            its HITL transport is bound to, its erasure workflow's content hash
            and the erasure door's public key. The store verifies the door's
            record signature and every approval against it; a deployment that
            runs no erasure door declares none (``ErasureTrust(authorities={})``)
            and every erasure its index names reads ``index-unsupported``.
            **Required, no default** (CINV-01).
        artifact_store: Any :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol`
            (an MCP-backed store, say). Wins under `D-IMPL-282` R-12; the
            declared ``store_dirname`` is then unread. ``None`` builds the
            file-backed reference store under the evidence root.
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
            ``requires`` — the composite hatch in its fully external form: the
            low road built entirely beside this surface, holding its own
            registrations. Refused together with ``questions=``, with an
            ``agent:`` or ``skills:`` section, or with ``producers:`` (a
            resolver built before open cannot see the facade's registry, so
            declared producers beside it would be a second registry nobody
            composes over — use ``build_children=`` for that).
        build_children: The hatch in its composed form: a factory handed a
            :class:`ConsumerContext` — the facade's one Control Plane, store,
            producer registry, tenant and clock — returning the resolver the
            deployment composes with. The SDK registers ``producers:`` and the
            deployment builds everything else the low road builds. Refused
            beside ``children=``, ``questions=``, ``agent:`` or ``skills:``.
        erasure_index: The supplied ``artifact_store``'s own durable erasure
            index (SEC-009; fix round 2, N1). Required with a raw supplied
            store; a store already composed through
            :func:`~ccf.erasure.compose_erasure_consult` carries its own, and
            one presented beside it must be the same index by path. ``None``
            with no supplied store derives the index from the evidence root.

    Raises:
        ValueError: any open-time refusal in the module docstring — each
            names the section or the key; a grant the Control Plane refused,
            with the refusal's own detail.
        ccf.products.resolver.AcquisitionOverUnverifiableStore: the
            environment's ``substrate.setting`` is not a path-valued setting
            of the adapter ``ccf_config.yaml`` declares, so the store this road
            mints per question could never be verified fresh (SEC-020 P4 (a),
            ``D-IMPL-378``). Read off the adapter's declared connection
            contract: nothing is minted, booted or connected to.
        FileNotFoundError: the environment document is absent.
        ccf.deployment.environment.EnvironmentMissing: a variable a source
            names is unset; the document's remedy is the message.
        ccf.skills.producers.ProducerEnvironmentMissing: a variable a producer
            registration names is unset.
        ccf.erasure.ErasureIndexUnavailable: a raw supplied store came without
            its erasure index, a composed one is scoped to another tenant, or
            the ``erasure_index`` presented is not the selected store's own.
    """
    root = Path(config_root).resolve()
    scratch_root = Path(scratch).resolve()
    if scratch_root == root or root in scratch_root.parents:
        raise ValueError(
            f"scratch {scratch_root} lies inside the config root {root}; the"
            " per-question fabrics and the replay store are written under"
            " scratch and never beside the deployment's documents (D-IMPL-343)"
        )
    evidence_dir = scratch_root if evidence_root is None else Path(evidence_root).resolve()
    if evidence_root is not None:
        if evidence_dir == root or root in evidence_dir.parents:
            raise ValueError(
                f"evidence_root {evidence_dir} lies inside the config root {root};"
                " retained replay evidence is never written beside the"
                " deployment's documents (D-IMPL-383, D-IMPL-343)"
            )
        if (
            evidence_dir == scratch_root
            or scratch_root in evidence_dir.parents
            or evidence_dir in scratch_root.parents
        ):
            raise ValueError(
                f"evidence_root {evidence_dir} and scratch {scratch_root} lie one"
                " inside the other; the durable evidence and the ephemeral working"
                " directory are distinct, so removing one never removes the other"
                " (D-IMPL-383)"
            )
    # SEC-020 Q7 (`D-IMPL-378`): an unsupported combination of the two declared
    # acquisition phases is refused at open, before any document is read.
    if population is not None:
        _refuse_shared_owner(population, acquire)
    environment = load_environment_document(root)
    config_path = root / environment.config
    config = load_artifact(config_path.read_text(encoding="utf-8"), DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)  # DEPLOYMENT_CONFIG's contract
    # SEC-020 P4 (a) made strict (`D-IMPL-378`; Dave, 2026-10-08 12:29 MST:
    # *"Unsupported network compositions must refuse before questions run"*):
    # this road acquires into a store it mints for every question, and a
    # substrate setting the declared adapter does not take as a path names no
    # store the SDK can verify fresh. Read off the adapter's declared contract,
    # so nothing is minted, booted or connected to.
    if environment.substrate.setting not in _path_valued_settings(config.backend):
        raise AcquisitionOverUnverifiableStore(
            "the paved road boots a fresh store for every question, at a path"
            f" it mints into the substrate setting {environment.substrate.setting!r},"
            f" and the {config.backend!r} adapter takes no path-valued setting by"
            " that name, so no question's store could be verified fresh; every"
            " question would be refused (SEC-020, P4)"
        )
    # `D-IMPL-341` R-3 (first row), at the paved road's registration moment:
    # a class declaring `ttl_anchor: from_entity_freshness` over a λ_c table
    # with no `decay_basis: valid-from` row could never be honored by any
    # data, and is refused by name at open rather than served
    # decision-anchored under an evidence-anchored label.
    refuse_undeclared_ttl_anchor(
        ttl_anchor=str(config.product_class.get("ttl_anchor", "from_decision")),
        entries=config.half_life,
        product_class=str(config.product_class.get("schema_name", "?")),
    )
    if config.tenant_id is None:
        raise ValueError(
            "ccf_config.yaml declares no tenant_id; on the paved road the"
            " deployment's tenant is declared once, in the document every"
            " other tenant-bearing value is held to (D-IMPL-343)"
        )
    derived = derive_deployment(config, config_filename=config_path.name)
    keys = derived.keys
    documents = derived.documents
    # The strings on the Control Plane: every per-question boot places the derived
    # keys under the deployment's tenant (D-IMPL-354), so what this product exposes,
    # pins and resolves by is the placed key — the bare `keys` above index only the
    # derivation's own documents.
    placed = keys_under_tenant(keys, tenant=config.tenant_id)

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
    _refuse_half_wired_composite(
        declaration, keys, questions=questions, children=children, build_children=build_children
    )

    resolved_environ = os.environ if environ is None else environ
    sources = resolve_values(environment.sources, resolved_environ)

    scratch_root.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    # SEC-009 (fix round 4, ruling 5): no fresh-registry fallback. The consult
    # verifies against THIS registry, so it must be the deployment's.
    if control_plane is None:
        raise ErasureCompositionRefused(
            "open_product takes the deployment's Control Plane (control_plane=);"
            " there is no fresh-registry fallback, because the erasure consult"
            " verifies every approval through it and a registry lacking the"
            " deployment's HITL policy would mark every genuine erasure"
            " index-unsupported (SEC-009; D-IMPL-374 (4), fix round 4, ruling 5)"
        )
    registry = control_plane
    selected: ArtifactStoreProtocol = (
        artifact_store
        if artifact_store is not None
        # The deployment's declaration of what its own mechanism writes and
        # under which kind (D-IMPL-353 §1.2): the two replay classes the
        # `replay:` binding names, and the SDK's two composite evidence
        # classes, all `ReplayMint`. A caller-supplied store carries its own
        # declaration; the resolver refuses one that omits a class it files.
        else FileArtifactStore(
            root=evidence_dir / replay.store_dirname,
            write_kinds=WriteKinds.declare(
                {
                    replay.record_class: (ReplayMint,),
                    replay.query_pin_class: (ReplayMint,),
                    ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,),
                    CHILD_QUESTION_CLASS: (ReplayMint,),
                }
            ),
        )
    )
    # SEC-009 (`D-IMPL-374` (4), ruling 2; fix round 1 C1, (i)): the erasure
    # consult is composed around whichever store was selected — supplied or
    # default — over the deployment's durable erasure index, which this
    # in-process site takes from its evidence root, scoped to the
    # tenant it serves, so `record_of` and every resolver read refuse erased
    # content.
    #
    # Fix round 2, N1: the index is the SELECTED store's own. A supplied store
    # already composed carries its index (its tenant scope must be this
    # product's, or none); a raw supplied store must come with its index; only
    # the default store derives one from the evidence root. Any index presented
    # alongside must be the same index, by path.
    if isinstance(artifact_store, ErasureConsultingStore):
        if artifact_store.tenant_id not in (None, config.tenant_id):
            raise ErasureIndexUnavailable(
                f"the supplied store is scoped to tenant {artifact_store.tenant_id!r},"
                f" not this product's {config.tenant_id!r} (SEC-009; N1)"
            )
        own_index: ErasureIndexProtocol = artifact_store.index
    elif artifact_store is not None:
        if erasure_index is None:
            raise ErasureIndexUnavailable(
                "a supplied artifact store must come with its own erasure index"
                " (pass erasure_index=, or supply a store composed through"
                " compose_erasure_consult); consulting it against an index derived"
                " from the scratch root would miss every erasure filed against it"
                " (SEC-009; D-IMPL-374 (4), N1)"
            )
        own_index = erasure_index
    else:
        own_index = erasure_index_at(evidence_dir / replay.store_dirname)
    if (
        erasure_index is not None
        and erasure_index is not own_index
        and getattr(erasure_index, "path", object()) != getattr(own_index, "path", None)
    ):
        raise ErasureIndexUnavailable(
            "the erasure_index presented is not the selected store's own index"
            " (compared by path; SEC-009; N1)"
        )
    erasure_index = own_index
    store: ArtifactStoreProtocol = compose_erasure_consult(
        selected,
        index=erasure_index,
        audit_log=registry.audit_log,
        clock=clock,
        # Fix rounds 4 and 5: approvals and the door's record signatures
        # verify here, against the deployment's per-tenant trust root.
        control_plane=registry,
        erasure_trust=erasure_trust,
        tenant_id=config.tenant_id,
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
            key=placed.policy_bundle, version=content_hash(policy_artifact)
        ),
    )

    # G4-F-04 (Dave, 2026-10-11 16:23 MST, ruling 4): the deployment's DECLARED
    # entitlement policy (`product_entitlement:`), registered HERE, at open, by
    # this composition root under a `Register` minted for exactly its key —
    # because a door composed over this product decides entitlement before any
    # question boots. Every boot re-registers the same content (idempotent).
    _register_declared_entitlement(
        registry,
        documents=documents,
        config=config,
        tenant=config.tenant_id,
        declaration=declaration,
        clock=clock,
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
        if build_children is not None:
            # G4-F-08 (Dave, 2026-10-11 16:23 MST, ruling 4): a deployment that
            # DECLARES its chain beside `build_children=` has it derived here —
            # registered and granted by composition, exactly as the derived
            # road does — and the factory is handed it. The factory composes
            # over it (a request-scoped switch for an optional child); it
            # registers nothing.
            derived_children: QuestionBoundChildResolver | None = None
            if keys.agent is not None:
                assert questions is not None  # `_refuse_half_wired_composite` held it
                agent, derived_children = _derive_consumer_chain(
                    derived,
                    tenant=config.tenant_id,
                    declaration=declaration,
                    registry=registry,
                    store=store,
                    mcp_skills=mcp_skills,
                    questions=questions,
                    clock=clock,
                    approval_sink=approval_sink,
                    declared_grants=config.grants,
                )
            child_resolver = build_children(
                ConsumerContext(
                    tenant_id=config.tenant_id,
                    control_plane=registry,
                    artifact_store=store,
                    mcp_skills=mcp_skills,
                    clock=clock,
                    derived_children=derived_children,
                    agent=agent,
                )
            )
        elif declaration.requires and children is None:
            assert questions is not None  # `_refuse_half_wired_composite` held it
            agent, child_resolver = _derive_consumer_chain(
                derived,
                tenant=config.tenant_id,
                declaration=declaration,
                registry=registry,
                store=store,
                mcp_skills=mcp_skills,
                questions=questions,
                clock=clock,
                approval_sink=approval_sink,
                declared_grants=config.grants,
            )
    except BaseException:
        if bridge is not None:
            bridge.close()
        raise

    return OpenedProduct(
        config_root=root,
        config_path=config_path,
        scratch=scratch_root,
        evidence_root=evidence_dir,
        config=config,
        environment=environment,
        keys=placed,
        tenant_id=config.tenant_id,
        declaration=declaration,
        replay=replay,
        ttl=ttl,
        door=door,
        default_perspective=default_perspective,
        sources=sources,
        control_plane=registry,
        artifact_store=store,
        erasure_index=erasure_index,
        erasure_trust=erasure_trust,
        refusal_recorder=recorder,
        acquire=acquire,
        project=project,
        assess=assess,
        gate=gate,
        clock=clock,
        constraint_resolver=constraint_resolver,
        capabilities=capabilities,
        children=child_resolver,
        packaging_trace=packaging_trace,
        mcp_skills=mcp_skills,
        bridge=bridge,
        agent=agent,
        population=population,
        # G1-SDK-01: the snapshot taken at open — the deployment's document
        # declares an instant and the caller composed no clock of its own.
        honors_demonstration_serve_instant=(
            clock is _utc_now and config.demonstration_serve_instant is not None
        ),
        # Round 5, item 4: the scoped invalidation writer, for this tenant only,
        # composed under the recipe every fabric boot uses (D-IMPL-354; D-IMPL-382).
        invalidation_sink=compose_invalidation_sink(registry, tenant_ids=(config.tenant_id,)),
    )


def _refuse_half_wired_composite(
    declaration: ProductClassDeclaration,
    keys: DeploymentKeys,
    *,
    questions: ChildQuestions | None,
    children: CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None,
    build_children: ChildResolverFactory | None,
) -> None:
    """A composite is declared whole or handed in whole — every mixed state refused by name.

    Four declarations make a derived chain: ``requires`` on the class,
    ``producers:``, ``skills:``, ``agent:`` — and one keyword, ``questions=``.
    One keyword makes a handed-in chain: ``children=`` (fully external) or
    ``build_children=`` (composed over the facade's registry). What is
    refused: a class with ``requires`` and none of them; a class without
    ``requires`` and any of them; two of them at once; a handed-in chain
    beside a declared ``agent:`` or ``skills:`` (which one would govern is
    exactly the ambiguity a declared deployment cannot carry); ``children=``
    beside ``producers:`` (a resolver built before open cannot see the
    facade's registry, so the declared registrations would be a second one
    nobody composes over); and a derived chain missing any of its four
    declarations, each named with the section that fills it.
    """
    requires = declaration.requires
    handed = [
        name
        for name, value in (("children=", children), ("build_children=", build_children))
        if value is not None
    ]
    if not requires:
        for name in handed:
            raise ValueError(
                f"this call supplies `{name}` and the product class declares no"
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
    if len(handed) == 2:
        raise ValueError(
            "this call supplies both `children=` and `build_children=`; the hatch"
            " is a resolver OR a factory for one, never both (D-IMPL-343)"
        )
    if handed == ["build_children="] and (keys.agent is not None or keys.skills):
        # G4-F-08 (Dave, 2026-10-11 16:23 MST, ruling 4): a factory beside a
        # COMPLETE declared chain is handed that chain (`ConsumerContext
        # .derived_children`) — the declared chain governs, registered and
        # granted by composition, and the factory only composes over it. Every
        # half-declared chain is still refused below, by name.
        if questions is None:
            raise ValueError(
                "this call supplies `build_children=` beside a declared"
                " `agent:`/`skills:` chain and no `questions=`; the SDK derives the"
                " declared chain for the factory and needs the question mapping"
                " to do so (G4-F-08; D-IMPL-343)"
            )
    elif handed:
        (name,) = handed
        if questions is not None:
            raise ValueError(
                f"this call supplies both `{name}` and `questions=`; a composite"
                " hands its chain in through the hatch or has it derived from"
                " `questions=` and the declarations beside it, never both"
                " (D-IMPL-343)"
            )
        if keys.agent is not None or keys.skills:
            declared = [s for s, present in (("agent", keys.agent), ("skills", keys.skills)) if present]
            raise ValueError(
                f"this call supplies `{name}` and the config declares {declared!r};"
                " a handed-in chain beside a declared one leaves the question of"
                " which governs, so a deployment declares its chain or hands one"
                " in, never both (D-IMPL-343)"
            )
        if children is not None and keys.producers:
            raise ValueError(
                "this call supplies `children=` and the config declares"
                " `producers:`; a resolver built before open cannot see the"
                " registry the facade populates from those declarations, so they"
                " would be a second registry nothing composes over — hand in a"
                " factory through `build_children=` to compose over the SDK's"
                " registrations, or register the producers on the low road and"
                " drop `producers:` (D-IMPL-343)"
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


def _register_declared_entitlement(
    registry: ControlPlaneRegistry,
    *,
    documents: Mapping[str, Mapping[str, Any]],
    config: DeploymentConfig,
    tenant: str,
    declaration: ProductClassDeclaration,
    clock: Callable[[], datetime],
) -> None:
    """Register the declared ``product_entitlement:`` policy under the composition recipe (G4-F-04).

    ``tenant`` is the deployment's tenant AFTER :func:`open_product` refused a
    config that declares none (D-IMPL-343), passed in already checked so the
    key and the ``CompositionRegister`` mint below are typed against a real
    tenant rather than ``config.tenant_id``'s ``str | None``.

    Nothing when the deployment declares none — the door then registers its
    own one-principal policy, as before. A declared policy is held to THIS
    product: every grant may name only the class this deployment serves, so a
    deployment cannot entitle a principal to a class its fabric does not serve
    (the rule the door's own derivation states). Refused by name at open.
    """
    if config.product_entitlement is None:
        return
    key = product_entitlement_key(tenant_id=tenant)
    policy = parse_artifact(documents[key], PRODUCT_ENTITLEMENT_POLICY)
    if not isinstance(policy, ProductEntitlementPolicy):  # PRODUCT_ENTITLEMENT_POLICY's contract
        raise TypeError(
            f"{key!r} parsed as {type(policy).__name__}, not the"
            " ProductEntitlementPolicy its artifact class declares"
        )
    for principal_id, grant in policy.principals.items():
        foreign = sorted(set(grant.permitted_schema_names) - {declaration.schema_name})
        if foreign:
            raise ValueError(
                f"the `product_entitlement:` section grants {principal_id!r}"
                f" {foreign!r}, and this deployment serves only"
                f" {declaration.schema_name!r}; a deployment entitles principals to"
                " the class it serves and no other (G4-F-04)"
            )
    event = registry.audit_log.append(
        action="composition",
        key=key,
        version=CompositionRegister.action_id,
        resolved=True,
        occurred_at=clock(),
        actor=COMPOSITION_PRINCIPAL,
    )
    registry.register_typed(
        mint_at_composition(
            CompositionRegister,
            tenant=tenant,
            principal=COMPOSITION_PRINCIPAL,
            resource=key,
            decision_id=content_hash(event),
        ),
        policy,
        PRODUCT_ENTITLEMENT_POLICY,
    )


def _request_declared_grants(
    ledger: GrantLedger,
    *,
    registry: ControlPlaneRegistry,
    agent: AgentDefinition,
    entries: list[Any],
    declared: tuple[str, ...] | None,
    clock: Callable[[], datetime],
) -> None:
    """Request each DECLARED grant through the ledger, at composition (ruling 4).

    One ``DeclaredSkillGrant`` per declared skill, minted for exactly the agent
    definition's key from a recorded ``composition`` decision on the Control
    Plane's own audit log. A skill already bound to the agent is left alone (the
    caller's version check then holds it to the declaration). A refusal — or a
    grant left pending an approval the sink did not give — raises
    :class:`DeclaredGrantRefused` by name; nothing is granted around it.
    """
    if not declared:
        return
    by_name = {entry.name: entry for entry in entries if isinstance(entry, SkillCatalogEntry)}
    unknown = sorted(set(declared) - set(by_name))
    if unknown:
        raise ValueError(
            f"`grants:` names {unknown!r}, which no `skills:` entry declares; a"
            " deployment grants its agent only skills it declares (ruling 4,"
            " 2026-10-11) — declare the skill under `skills:`, or remove the grant"
        )
    agent_key = f"{agent.tenant}/{AGENT_DEFINITION.class_id}/{agent.name}"
    agent_hash = content_hash(agent)
    for name in declared:
        if name in ledger.bound_view(agent_hash):
            continue
        entry = by_name[name]
        event = registry.audit_log.append(
            action="composition",
            key=agent_key,
            version=DeclaredSkillGrant.action_id,
            resolved=True,
            occurred_at=clock(),
            actor=COMPOSITION_PRINCIPAL,
        )
        outcome = ledger.request(
            mint_at_composition(
                DeclaredSkillGrant,
                tenant=agent.tenant,
                principal=COMPOSITION_PRINCIPAL,
                resource=agent_key,
                decision_id=content_hash(event),
            ),
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
        )
        if isinstance(outcome, str) and name in ledger.bound_view(agent_hash):
            continue
        refusal = outcome if isinstance(outcome, GrantRefusal) else None
        detail = refusal.detail if refusal is not None else (
            "the grant was requested and is not in force (pending an approval"
            " the deployment's approval sink did not give, or refused at"
            f" registration: {outcome!r})"
        )
        raise DeclaredGrantRefused(
            f"the declared grant of skill {name!r} to agent {agent.name!r}"
            f" (tenant {agent.tenant!r}) was refused by the grant ledger's own"
            f" governance: {detail} (ruling 4, 2026-10-11)",
            skill=name,
            refusal=refusal,
        )


def _mint_child_question_authority(
    registry: ControlPlaneRegistry, *, tenant: str, clock: Callable[[], datetime]
) -> Authorized[ReplayMint]:
    """The composition recipe (D-IMPL-354) for the consumer's child-question class.

    :func:`open_product` is a composition root (`COMPOSITION_MINT_SITES`); the
    :class:`~ccf.products.child_resolver.QuestionBoundChildResolver` it
    composes is not, and receives this at construction. The decision is
    recorded on the Control Plane's own audit log and the capability carries
    that event's content address as its ``decision_id``; one class, one
    tenant — the consumer tenant the gate admits for.
    """
    event = registry.audit_log.append(
        action="composition",
        key=CHILD_QUESTION_CLASS,
        version=ReplayMint.action_id,
        resolved=True,
        occurred_at=clock(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        ReplayMint,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=CHILD_QUESTION_CLASS,
        decision_id=content_hash(event),
    )


def _derive_consumer_chain(
    derived: DerivedDeployment,
    *,
    tenant: str,
    declaration: ProductClassDeclaration,
    registry: ControlPlaneRegistry,
    store: ArtifactStoreProtocol,
    mcp_skills: McpSkillRegistry | None,
    questions: ChildQuestions,
    clock: Callable[[], datetime],
    approval_sink: ApprovalSink | None,
    declared_grants: tuple[str, ...] | None = None,
) -> tuple[AgentDefinition, QuestionBoundChildResolver]:
    """The declared chain: agent → catalog → grant → question-bound resolver → gate.

    Registers what the ledger resolves — the policy regime, the agent and the
    skill entries — placed under ``tenant`` (D-IMPL-354) and registered
    through the manifest's ONE register loop
    (:func:`~ccf.deployment.manifest.register_manifest_entries`; every
    question's boot registers the same content again, idempotently), then
    **reads** which declared skills are bound to the agent on this Control
    Plane and refuses, by name, any that is not (:class:`GrantNotInForce`).
    It requests no grant: a grant is a ``skill.grant`` door action requiring
    ``Authorized[SkillGrant]``, which a composition root cannot mint
    (D-IMPL-353 §1.6; D-IMPL-354). A skill bound at another version than the
    one declared is refused rather than superseded, as before.
    """
    declared_keys = derived.keys
    assert declared_keys.agent is not None and declared_keys.skills and declared_keys.policy_bundle  # held by the caller
    if mcp_skills is None:
        raise ValueError(
            "the product class declares `requires` and the config declares no"
            " `producers:`; a derived chain asks declared producers and none"
            " are declared (D-IMPL-343; D-IMPL-340)"
        )
    declared_wanted = frozenset({declared_keys.policy_bundle, declared_keys.agent, *declared_keys.skills})
    declared = {
        entry.key: parse_artifact(derived.documents[entry.key], resolve_artifact_class(entry.class_id))
        for entry in derived.manifest.artifacts
        if entry.key in declared_wanted
    }
    # This is the consumer's composition root: every key the derived manifest
    # names is placed under the deployment's own tenant BEFORE the one register
    # loop mints for it — the same derivation `load_config_and_boot` applies to
    # the paved road, so the key an artifact registers under and the key this
    # chain reads it back by are one string by construction (D-IMPL-354;
    # D-IMPL-353 §1.3). The loop itself admits no key outside a tenant.
    manifest, parsed, keys = manifest_under_tenant(
        derived.manifest, declared, declared_keys, tenant=tenant
    )
    assert keys is not None and keys.agent is not None  # every field kept; `agent` held above
    wanted = frozenset({keys.policy_bundle, keys.agent, *keys.skills})
    register_manifest_entries(manifest, parsed, registry=registry, tenant=tenant, only=wanted)

    agent = parsed[keys.agent]
    assert isinstance(agent, AgentDefinition)  # its entry names AGENT_DEFINITION
    agent_hash = content_hash(agent)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=SkillCatalog(registry),
        sink=approval_sink if approval_sink is not None else RefusingApprovalSink(),
        clock=clock,
    )
    # Ruling 4 (Dave, 2026-10-11 16:23 MST): the grants the deployment DECLARED
    # (`grants:`) are requested HERE, at composition, through the ledger's own
    # governance — tier 1 (the regime's compatibility check), tier 2 (the
    # regime's approval sink), the audit and state records a door grant gets —
    # under a `DeclaredSkillGrant` minted for exactly this agent definition. A
    # declared label that names no declared skill is refused by name; a skill
    # declared under `skills:` and NOT listed under `grants:` is not requested,
    # so it meets the not-in-force refusal below exactly as before.
    _request_declared_grants(
        ledger,
        registry=registry,
        agent=agent,
        entries=[parsed[key] for key in keys.skills],
        declared=declared_grants,
        clock=clock,
    )
    bound = ledger.bound_view(agent_hash)
    produced: set[str] = set()
    not_in_force: list[str] = []
    for key in keys.skills:
        entry = parsed[key]
        assert isinstance(entry, SkillCatalogEntry)  # its entry names SKILL_CATALOG_ENTRY
        produced.add(entry.produces)
        if entry.name in bound:
            in_force = bound[entry.name]
            if content_hash(in_force) != content_hash(entry):
                # Idempotent means THE SAME grant: a skill bound to this agent at
                # another version is a standing Control Plane fact this open did
                # not make and will not silently supersede — revocation is a
                # governance action (CLAUDE.md §6.2), never a side effect of
                # editing a section (panel finding, this half).
                raise ValueError(
                    f"skill {entry.name!r} is bound to agent {agent.name!r} on this"
                    f" Control Plane at artifact_version {in_force.artifact_version!r}"
                    f" (content {content_hash(in_force)[:12]}…) and the `skills:`"
                    f" section now declares artifact_version {entry.artifact_version!r}"
                    f" (content {content_hash(entry)[:12]}…); revoke the grant in"
                    " force, or restore the declared version — a bound skill is"
                    " never superseded by an edit (D-IMPL-343; D-IMPL-29)"
                )
            continue  # in force on this Control Plane: composes
        not_in_force.append(entry.name)
    if not_in_force:
        raise GrantNotInForce(
            f"skill(s) {not_in_force!r} declared in `skills:` are not granted to"
            f" agent {agent.name!r} (tenant {agent.tenant!r}) on this Control"
            " Plane, and the paved road cannot grant them: a grant is the"
            f" {SkillGrantKind.action_id!r} door action, requiring"
            " Authorized[SkillGrant], which a composition root may not mint"
            " (D-IMPL-353 §1.6; D-IMPL-354). Declare them under `grants:` in the"
            " deployment's config (ruling 4, 2026-10-11: requested at composition"
            " through the ledger's own governance), or grant them through a"
            " governed door as an authorized principal, then open the product"
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
        # D-IMPL-354: minted HERE, by the composition root, for the consumer
        # tenant the gate admits for; the resolver holds it and mints nothing.
        authorized=_mint_child_question_authority(registry, tenant=agent.tenant, clock=clock),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=store,
        mcp_skills=mcp_skills,
    )


class _EvidencePublishingRecorder:
    """A :class:`RefusalRecorderProtocol` that maps every refusal it records (`D-IMPL-383`).

    SDK-defined (CLAUDE.md §7.4). Appends through the product's own recorder,
    then publishes the decision's no-graph evidence mapping; anything else is
    the inner recorder's. ``**kwargs`` passes every keyword the protocol takes,
    ``subject_withholding`` included, so the builders' compatibility check
    (:func:`~ccf.products.resolver.refuse_incompatible_refusal_recorder`) holds.
    """

    def __init__(self, *, inner: ReplayRefusalRecorder, opened: OpenedProduct) -> None:
        self._inner = inner
        self._opened = opened

    def record(
        self,
        envelope: RefusalEnvelope,
        *,
        recorded_at: datetime,
        request: ProductRequest | None = None,
        **kwargs: Any,
    ) -> RefusalEnvelope:
        recorded = self._inner.record(envelope, recorded_at=recorded_at, request=request, **kwargs)
        self._opened._published_refusal(recorded, request=request, recorded_at=recorded_at)
        return recorded

    # The members the delivery boundaries check for by protocol. A runtime
    # protocol check reads the CLASS (static lookup), so these are declared
    # here rather than reached through ``__getattr__`` (close panel fixes,
    # 2026-10-15: 481 doors refused a wrapper that forwarded them dynamically),
    # each with the inner recorder's own type, so nothing forces a member past
    # the type checker (D-IMPL-353 §1.5b).
    @property
    def tenant_id(self) -> str:
        return self._inner.tenant_id

    @property
    def replay_record_class(self) -> str:
        return self._inner.replay_record_class

    @property
    def artifact_store(self) -> ArtifactStoreProtocol:
        return self._inner.artifact_store

    # The inner recorder's own reader, handed through as the field it is: no
    # parameter list here, so no principal id is named below the door
    # (`tests/invariants/test_mcp_role_separation.py`).
    @property
    def disclosure_level_for(self) -> Callable[..., tuple[DisclosureLevel, ProvenanceSource | None]]:
        return self._inner.disclosure_level_for

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
