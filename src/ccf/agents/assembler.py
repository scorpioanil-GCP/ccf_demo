"""The assembler surface — the producer side of a Context Product.

**SDK-defined** (CLAUDE.md §6.1/§6.2/§6.4). The whitepaper does not commit this
surface: Chapter 3 describes agents as *consumers* of the fabric, and §7.6
describes the delivered product, but nothing there specifies what produces one.
The ruling of record is ``docs/DECISIONS.md`` **D-IMPL-97** ruling 2 (Dave,
2026-08-10): *"The assembler, which I agree should be a Protocol, is what makes
the ContextProduct a KYC_ContextProduct"*, and then *"Agent becomes the
implementation protocol."*

**The split, stated once so it is not re-derived wrongly: Protocol for the
producer, standardised vessel for the produced — and the Protocol's
implementation is a declared agent.** A deployment does not subclass anything
here and does not add a module to ``/src`` to get its own assembler. It declares
an agent from the ``context_assembly`` archetype
(:class:`~ccf.agents.archetypes.ArchetypeComponent`), the Agent Factory builds
it, and that agent — a Control Plane artifact, data rather than code — is what
implements this Protocol. The SDK's ``/src`` contains archetypes and never
agents; an agent found in library code is a defect of the same severity as a
hard-coded half-life table (CLAUDE.md §6.1).

**Why this is a new surface rather than a fill-in-the-blank on the archetype.**
:class:`~ccf.agents.archetypes.ArchetypeComponent` is *declarative* —
``archetype_id``, ``fabric_interaction_pattern``, ``replay_obligations``,
``configuration_defaults`` — so ``_ContextAssemblyComponent`` declares the
emission **pattern** (``"typed-product-emission"``) and two replay obligations,
and carries no assembly behaviour at all: no source binding, no enlistment, no
emission. This module is the behavioural surface; the archetype is the seam it
attaches to, and the two obligations the archetype already declares are exactly
what an outcome here has to be able to satisfy.

**Why the agent is the right implementation, and why that is confirmation
rather than convenience.** Specialization axis 5 — the half-life and debt
profile — is already a **required** field on every agent definition
(``halflife_debt_profile``, a pinned ``ccf-artifact://`` reference resolving to
a :class:`~ccf.controlplane.artifacts.DebtProfile`). A product's debt
configuration therefore already has a version-pinned home, and it is on the
agent. Axis 2 binds which product schemas it emits, axis 3 its perspective,
axis 4 the policy regime bounding what it may consult, axis 6 its instruction
artifacts; and channel 2 — skilling — governs which tools and peer agents it
may enlist, with every grant and revocation already landing in replay.

**Two structural invariants hold across this surface by construction, not by
caller discipline.**

* **Single-writer** (CLAUDE.md §10). An assembler's entire effect is the
  :class:`AssemblyOutcome` it returns. There is no write handle on this
  surface and no method that takes one; carrying an outcome into the graph is
  L2's job, exactly as it is for :meth:`ccf.agents.agent.Agent.emit_effect`.
* **Algorithmic ⇄ Semantic Alternation** (whitepaper §7.6.6; CINV-03). Content
  produced by an enlisted agent re-enters as
  :class:`~ccf.projection.acquisition.AcquiredContent` — through
  :meth:`ccf.projection.engine.ProjectionEngine.execute`'s
  ``recorded_acquisitions`` slot, carrying a content address a replay re-feeds
  — never as payload. :class:`AssemblyOutcome` gives it exactly one route, and
  a field enumeration in ``tests/agents/test_assembler.py`` keeps it at one:
  a docstring cannot fail when somebody adds a second.

**No harness import reaches this module** (CINV-02, CLAUDE.md §7.3). Nothing
here is a reasoning loop, and none ships: enlistment travels through the skill
catalog and the adapter seam. There is no ``run``, ``step``, ``plan`` or
``loop`` on this surface and there never will be.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import model_validator

from ccf.agents.agent import Agent
from ccf.agents.errors import AssemblyRefusal, AssemblyRefused
from ccf.products.request import (
    ProductRequestContract,
    ProductRequestViolation,
    refuse_request,
)
from ccf.contracts.base import CCFContract
from ccf.projection.acquisition import AcquiredContent
from ccf.projection.plan import Perspective, ProjectionOutput

if TYPE_CHECKING:  # pragma: no cover - typing only
    # Deferred for the reason :mod:`ccf.agents.agent` defers
    # ``ccf.skills.dispatch``, and against a cycle that is real rather than
    # hypothetical: ``ccf.products.request`` imports
    # :class:`~ccf.skills.catalog.SkillArgumentSchema`, and ``ccf.skills``
    # imports ``ccf.agents.definitions`` — which initializes this package. A
    # module-level import here would make the success of that graph depend on
    # which module a caller reached first, the non-determinism D-IMPL-37
    # rejects.
    #
    # **That caution was MEASURED rather than inherited when D-60 landed, and
    # it did not fire.** Sweeping all 141 ``ccf`` modules, each imported first
    # in a fresh interpreter: the module-level ``from ccf.products.request
    # import ...`` above breaks **0**, against a baseline of 0 on the
    # unmodified tree and a positive control — ``from ccf.products.refusal
    # import RefusalEnvelope`` in the same position — breaking **15**. The
    # difference is that ``ccf.products.request`` already defers its own
    # cycle-closing import to the bottom of its module (D-IMPL-56), while
    # ``ccf.products.refusal`` does not. The control is what makes the 0 a
    # measurement rather than a sweep that was not running.
    #
    # ``ProductRequest`` stays here because it appears only in annotations,
    # which ``from __future__ import annotations`` leaves unevaluated.
    from ccf.products.request import ProductRequest

__ccf_mode__ = "algorithmic"

__all__ = [
    "DETERMINISTIC_ASSEMBLER_ID",
    "DETERMINISTIC_ASSEMBLER_VERSION",
    "NO_CONSULTATIONS",
    "AssemblyOutcome",
    "ConsultationRecord",
    "ContextAssemblerProtocol",
    "DeterministicAssembler",
]

#: Identity of the SDK's reference assembler. Pinned into an outcome alongside
#: the payload it produced, so a decision re-traces against the assembler it
#: actually ran under rather than the one installed today — the reason
#: :data:`~ccf.halflife.debt.FRESHNESS_SCORER_ID` exists in its own module.
DETERMINISTIC_ASSEMBLER_ID = "ccf.reference.deterministic-assembler"
DETERMINISTIC_ASSEMBLER_VERSION = "1.0.0"


class ConsultationRecord(CCFContract):
    """What an assembly was permitted to consult, and what it was refused.

    SDK-defined (CLAUDE.md §6.2 axis 4). *What a product was permitted to
    consult* is what makes a product's identity auditable: replay answers not
    only what an assembly returned but what it was allowed to reach for, so a
    decision made under a narrower policy regime is distinguishable from the
    same decision made under a wider one.

    **Targets are opaque identifiers the SDK never interprets** — sources,
    tools and peer agents alike, in the posture
    :class:`~ccf.skills.catalog.SkillRequirements` states for its own module.
    No consultation vocabulary exists here, and none is enumerated anywhere in
    ``/src``: what a deployment's identifiers mean is the deployment's
    statement (CINV-01).

    Both tuples are held **sorted, unique and disjoint**, because they
    participate in canonical serialization and therefore in content identity: a
    record whose ordering depended on the order a scheduler happened to visit
    its targets would hash differently for the same assembly, which is the
    non-determinism replay cannot survive. Disjoint because a target that was
    both permitted and refused describes no decision the Control Plane could
    have made.

    Attributes:
        permitted: The consultation targets policy admitted, sorted.
        refused: The consultation targets policy declined, sorted. A non-empty
            refused set is the visible half of axis 4 doing its job.
    """

    permitted: tuple[str, ...]
    refused: tuple[str, ...]

    @model_validator(mode="after")
    def _sets_are_canonical(self) -> "ConsultationRecord":
        for name, values in (
            ("permitted", self.permitted),
            ("refused", self.refused),
        ):
            if len(set(values)) != len(values):
                raise ValueError(
                    f"{name} names a consultation target twice"
                    f" ({sorted(values)!r}); a target is consulted or not, and"
                    " a duplicate would make one assembly hash two ways"
                    " (docs/DECISIONS.md D-IMPL-97)"
                )
            if tuple(sorted(values)) != tuple(values):
                raise ValueError(
                    f"{name} is not sorted ({list(values)!r}); consultation"
                    " sets participate in content identity, so their ordering"
                    " cannot depend on visit order"
                    " (docs/DECISIONS.md D-IMPL-97)"
                )
        overlap = sorted(set(self.permitted) & set(self.refused))
        if overlap:
            raise ValueError(
                f"consultation target(s) {overlap!r} are recorded as both"
                " permitted and refused; axis 4 admits a target or declines"
                " it, and both at once describes no Control Plane decision"
                " (CLAUDE.md §6.2)"
            )
        return self


#: The positive claim that an assembly consulted nothing.
#:
#: A named sentinel rather than a bare pair of empty tuples, in the
#: :data:`~ccf.replay.record.NO_GRANTS_SET_HASH` voice: *this assembly reached
#: for nothing outside itself* is a statement an auditor can read, and it is
#: distinguishable from a record somebody forgot to populate only because the
#: claim is named.
NO_CONSULTATIONS = ConsultationRecord(permitted=(), refused=())


class AssemblyOutcome(CCFContract):
    """Everything one assembly produced — a value the caller carries onward.

    SDK-defined (D-IMPL-97 ruling 2). Frozen and ``extra=forbid`` by
    inheritance from :class:`~ccf.contracts.base.CCFContract`.

    **The whole effect is this return value.** Nothing on this type is a
    handle, a session, or a callback, and there is no method here that writes:
    single-writer holds across the seam by construction, and carrying an
    outcome into L3 is L2's job (CLAUDE.md §10, §7.3 seam 3) — the shape
    :class:`~ccf.agents.agent.EmittedEffect` already establishes.

    **``acquisitions`` is the only route content produced by an enlisted agent
    may travel.** ``payload`` is Π's output, which is algorithmic by
    construction; anything a model produced re-enters through
    :meth:`ccf.projection.engine.ProjectionEngine.execute`'s
    ``recorded_acquisitions`` slot, with the content address that makes a
    replay a re-feed rather than a re-fetch (whitepaper §7.6.6; INV-CH7-31).
    The one-route property is asserted by field enumeration rather than
    described, because a docstring cannot fail when a second route is added.

    Attributes:
        payload: What the assembly produced, unchanged from Π's output.
            Canonical-serializability is the payload author's obligation, as
            everywhere else in the fabric.
        consultations: What the assembly was permitted and refused (axis 4).
        acquisitions: Content acquired at decision time, each with its content
            address. Empty is the ordinary case for a wholly deterministic
            assembly.
        assembler_id: Identity of the assembler that ran.
        assembler_version: Its version. Both travel because the assembler in
            force is part of what a decision replays against — a payload is
            only reproducible alongside the computation that produced it.
        skill_set_in_force: The channel-2 skill names bound **at assembly
            time**, sorted. A decision replays against the skills the agent
            actually had, never the skills it has now (CLAUDE.md §6.2; D-07).
        halflife_debt_profile: The pinned ``ccf-artifact://`` reference to the
            axis-5 profile the assembly ran under. A ref rather than the
            resolved artifact, for the reason
            :class:`~ccf.agents.definitions.VersionedRef` gives: the profile
            has its own lane, and inlining it would give one record two version
            identities.
    """

    payload: Mapping[str, Any]
    consultations: ConsultationRecord
    acquisitions: tuple[AcquiredContent, ...]
    assembler_id: str
    assembler_version: str
    skill_set_in_force: tuple[str, ...]
    halflife_debt_profile: str


@runtime_checkable
class ContextAssemblerProtocol(Protocol):
    """The seam a Context Product's producer implements (D-IMPL-97 ruling 2).

    A Protocol rather than a base class, for the reason
    :class:`~ccf.halflife.debt.DebtFactorScorerProtocol` gives for its own
    case: a deployment substitutes its own assembler by **conforming**, never
    by inheriting, and the SDK's reference implementation carries no privileged
    status. Conformance is structural — the discipline
    :class:`~ccf.agents.archetypes.ArchetypeComponent` already applies to
    archetypes.

    ``assembler_id`` and ``assembler_version`` are on the surface for the
    reason ``scorer_id``/``scorer_version`` are on theirs: the assembler in
    force must be **pinnable into replay**, because what made a vessel this
    particular product is how it was assembled, and that is only re-checkable
    against the assembler that did it.

    :meth:`assemble` is keyword-only. A three-value call whose arguments could
    transpose is the failure ``ProductResolverProtocol`` keeps out of the
    egress seam by the same means; here the cost of a transposition would be an
    assembly attributed to the wrong tenant.
    """

    @property
    def assembler_id(self) -> str:
        """Stable identity of this assembler."""
        ...

    @property
    def assembler_version(self) -> str:
        """Version of this assembler's assembly behaviour."""
        ...

    def assemble(
        self,
        *,
        request: ProductRequest,
        perspective: Perspective,
        tenant_id: str,
    ) -> AssemblyOutcome | ProductRequestViolation | AssemblyRefusal:
        """Assemble one answer to ``request`` for ``perspective``.

        Reads no clock: the instant is ``request.asked_at``, supplied by the
        caller at serve time and by replay at replay time through the same code
        path — the property :mod:`ccf.products.request` exists to preserve.

        **A governed refusal is RETURNED, never raised** (D-60, D-IMPL-214).
        :class:`~ccf.products.request.ProductRequestViolation`'s own docstring
        states the posture this widening finally lets a conforming assembler
        honour: *a refusal returned as data cannot be swallowed by a bare*
        ``except``. An implementation that has decided the question does not
        conform to its declared contract returns the violation; it does not
        raise one. ``24.5-L-11`` widened the union once more, additively, by
        :class:`~ccf.agents.errors.AssemblyRefusal` — the assembler's *own*
        refusal (a tier it does not serve, a capability it lacks) as a value —
        so that a conforming assembler can return it rather than raising
        :class:`~ccf.agents.errors.AssemblyRefused` and having the verdict
        reach a client as ``ToolError`` prose.

        **The boundary between the two channels, in one sentence:** a
        *governed* refusal — this question does not conform to the contract it
        addresses — is DATA and returns here, while an *identity* disagreement
        — this question was asked of the wrong tenant, or under a role this
        agent was not declared for — stays
        :class:`~ccf.agents.errors.AssemblyRefused`, because it says the caller
        reached the wrong agent rather than that the answer is a refusal.

        Return types are covariant, so an implementation that only ever
        succeeds keeps ``-> AssemblyOutcome`` and stays conforming; nothing in
        the tree had to widen its own annotation for this change.
        """
        ...


@dataclass(frozen=True)
class DeterministicAssembler:
    """The SDK's reference assembler: mechanism, with nothing domain in it.

    SDK-defined. It exists for two reasons and no third: to prove the Protocol
    composes against a real factory-built agent, and to give a deployment
    something to diff its own assembler against. It consults nothing, records
    an empty permitted set and an empty refused set, and returns Π's payload
    unchanged.

    **It is deliberately not a worked assembler for any domain.** A product
    class named after a business process, or a reference assembler shaped like
    one, would be exactly the defect CLAUDE.md §6.1 rates at half-life-table
    severity — the taxonomy of products is configuration, and code holds
    interpreters rather than the things interpreted (§6.4).

    What it *does* carry is the governed part, read off the declared agent
    rather than chosen here: the channel-2 skill-set in force at the moment
    :meth:`assemble` runs, and the pinned axis-5 profile reference. Both are
    read at assembly time, not at construction time, so a grant or revocation
    between the two is visible in the outcome (D-07).

    Args:
        agent: The declared agent this assembler runs as — built by
            :class:`~ccf.agents.factory.AgentFactory` from a definition
            artifact, which is the only supported path (CLAUDE.md §6.4).
        projection: Π's output for this assembly. Held rather than computed
            here: running the two-stage execution is
            :class:`~ccf.projection.engine.ProjectionEngine`'s job, and an
            assembler that re-implemented it would be a second reading of what
            Π means.
        acquisitions: Content acquired at decision time, in resolution order.
            Empty is the deterministic case.
        request_contract: The declared request contract this assembler judges a
            question's conformity against, or ``None`` — the default — to judge
            none. **Optional on purpose.** With it absent this assembler is
            byte-for-byte what it was, so no caller that predates D-60 moves.
            With it present, :meth:`assemble` makes ONE call into
            :func:`~ccf.products.request.refuse_request` and RETURNS the
            resulting :class:`~ccf.products.request.ProductRequestViolation`
            as data.

            **This teaches the reference assembler no domain rule** (D-IMPL-214,
            CLAUDE.md §11). The contract is a Control Plane artifact the
            deployment authored and `refuse_request` is the SDK's own door
            function; nothing here evaluates a threshold, a routing table or a
            business condition, and this assembler still consults nothing and
            still returns Π's payload unchanged.
    """

    agent: Agent
    projection: ProjectionOutput
    acquisitions: tuple[AcquiredContent, ...] = field(default=())
    request_contract: ProductRequestContract | None = field(default=None)

    @property
    def assembler_id(self) -> str:
        return DETERMINISTIC_ASSEMBLER_ID

    @property
    def assembler_version(self) -> str:
        return DETERMINISTIC_ASSEMBLER_VERSION

    def assemble(
        self,
        *,
        request: ProductRequest,
        perspective: Perspective,
        tenant_id: str,
    ) -> AssemblyOutcome | ProductRequestViolation:
        """Return the governed outcome for ``request`` under ``perspective``.

        Two refusals, both raised rather than repaired and both naming each
        side, in the
        :func:`~ccf.deployment.binder.refuse_operator_set_divergence` posture:
        an assembler does not choose which of two disagreeing statements is
        right, because only the deployment's author knows which was meant.

        **A third refusal, and it RETURNS rather than raises** (D-60): when
        this assembler was constructed with a ``request_contract`` and the
        question does not conform to it, the
        :class:`~ccf.products.request.ProductRequestViolation` is the return
        value. **Ordered AFTER the two identity checks on purpose** — a
        question asked of the wrong agent is not a question about a contract's
        conformity, and answering the conformity question first would give a
        confident verdict on the wrong one, which is exactly what
        :func:`~ccf.products.request.refuse_request`'s own address-before-
        parameters ordering exists to prevent.

        Returns:
            The :class:`AssemblyOutcome`, or a
            :class:`~ccf.products.request.ProductRequestViolation` when a
            declared contract was supplied and the question does not conform.

        Raises:
            AssemblyRefused: ``tenant_id`` is not the declared agent's tenant,
                or ``perspective`` is not the axis-3 role it was declared
                under. Identity, not conformity — see the Protocol's own
                boundary sentence.
        """
        declared = self.agent.definition
        if tenant_id != declared.tenant:
            raise AssemblyRefused(
                f"assembly for tenant {tenant_id!r} was asked of an agent"
                f" declared for tenant {declared.tenant!r} (question:"
                f" {request.schema_name!r}@{request.schema_version!r}); an"
                " agent assembles for its own tenant and no other"
                " (CLAUDE.md §6.2)"
            )
        if perspective.role != declared.perspective.role:
            raise AssemblyRefused(
                f"assembly under role {perspective.role!r} was asked of an"
                f" agent declared under role {declared.perspective.role!r}"
                f" (question: {request.schema_name!r}); axis 3 is channel-1"
                " identity, so a different perspective is a different agent"
                " (CLAUDE.md §6.2)"
            )
        if self.request_contract is not None:
            violation = refuse_request(
                request=request, declared=self.request_contract
            )
            if violation is not None:
                return violation
        return AssemblyOutcome(
            payload=self.projection.payload,
            consultations=NO_CONSULTATIONS,
            acquisitions=self.acquisitions,
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            skill_set_in_force=self.agent.bound_skill_names,
            halflife_debt_profile=declared.halflife_debt_profile.ref,
        )
