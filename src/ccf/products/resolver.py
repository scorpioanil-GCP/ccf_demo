"""The seam that yields a *gate-admitted* product, declared in ``src/``.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). The whitepaper
specifies the Context Product Contract (§6.3), the three validation gates
(§7.6) and the Decision Replay record (§7.10); it specifies no client, and so
no seam through which a client reaches a served product. The ruling of record
is ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` **Amendment 1
§B** (Dave, 2026-08-15): *the resolver Protocol is declared in* ``src/``, *and
the SDK ships its reference implementation in* ``src/`` *as well*.

Why the ruling was needed
-------------------------
Phase 17 research measured that **no** ``src/``-resident seam yields a
gate-admitted product, and that **no** module under ``src/`` imports
``ccf_runtime``. The two seams that do yield one live in ``runtime/``, behind
the two MCP doors. The nearest ``src/`` seam,
:class:`~ccf.agents.assembler.ContextAssemblerProtocol`, sits one level *below*
the vessel: its :class:`~ccf.agents.assembler.AssemblyOutcome` carries a
payload, and no contract, no gates and no replay record. A client had no
implementable path.

That gap has a second face. The SDK ships every *part* of assemble → gate →
serve — :func:`~ccf.products.gates.run_gates` and
:func:`~ccf.replay.serve.serve` are both ``src/``-resident — and has never
shipped the *composition*, so every deployment writes it. The rejected first
example wrote it in front of a reader who wanted to ask one question. **The
missing resolver and the oversized example are the same defect seen from two
directions**, which is why :class:`GovernedResolver` ships here rather than
being described in a guide.

The two widenings, and the measured reason for each
---------------------------------------------------
This seam's five arguments are copied from
:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` **exactly** — same
names, same order, same keyword-only discipline, same nullability — so a
deployment that already wrote a resolver for a door recognises the signature on
sight and maintains one shape rather than two. Only the *return type* widens,
in the two ways research measured to be missing:

**DIV-2 — a replay reference.** The seam returns
:class:`~ccf.replay.serve.ServedProduct`, not
:class:`~ccf.products.gates.ServableProduct`. The first carries ``product``
*and* ``replay_ref``; the second carries only the product.
:mod:`ccf.replay.serve` records the measurement plainly in its own docstring:
all three shipped delivery paths serialize the servable's product and **none**
of them reads its replay reference. The seam being typed to the narrower vessel
is precisely why no door can reach a replay reference. The ruled client
``Result`` exposes one, so the seam must carry one.

**DIV-4 — a refusal.** Every refusal the fabric produces behind the current
seam has nowhere to go: the seam admits no refusal in its union, so a
``GateRefusal`` or a request-conformity verdict either becomes an exception or
becomes silence. :class:`~ccf.products.refusal.RefusalEnvelope` is where it
goes, and :data:`ResolverOutcome` is the union that carries it.

A named divergence, recorded rather than left to be discovered
--------------------------------------------------------------
**The two** ``runtime/`` **seams are unchanged by this module**, and both
remain typed to the narrower vessel:
:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` and
:class:`~ccf_runtime.mcp.experience.ExperienceProductResolverProtocol`. So
there are, for now, two return shapes across three seams. Unifying them is not
in scope for this phase, is not ruled, and would be a door's worth of work;
stating the divergence here is what keeps it a known cost rather than a
surprise for whoever reads the three seams side by side.

Where the debt scorer's default lives, and what the choice cost
----------------------------------------------------------------
The 2026-08-16 spec §6 requires the reference debt scorer to be selected
automatically *"when the caller does not pass one"*, so that **a deployment
providing only data never has to know the Protocol exists** — and it leaves the
location open: :class:`GovernedResolver` itself, or *"a thin*
``build_governed_resolver(...)`` *helper"*.

**It is the helper**, and the choice was forced by two measurements rather than
settled by taste:

1. **The default is not a value; it is a construction that needs four inputs
   this class does not hold.** :class:`~ccf.products.debt_scorer.AssemblyDebtScorer`
   takes a ``λ_c`` table, a debt profile, and a
   :class:`~ccf.halflife.debt.DebtFactorScorerProtocol` for each of ``C`` and
   ``S``. Only the first two are resolvable from the booted fabric, and only
   given the *keys* that name them; ``C`` and ``S`` have **no** SDK
   measurement at all (:class:`~ccf.halflife.assessment.DebtFactors` records
   that position in its own words). Defaulting on the class would therefore
   have grown it from thirteen arguments to seventeen — four of them dead
   whenever an explicit scorer *is* supplied — in order to give one argument a
   default. A default that enlarges its own seam is not a default.
2. **A shipped assertion already forbids it, and weakening a shipped assertion
   to admit a feature is this phase's signature defect.**
   ``tests/products/test_resolver_seam.py::test_no_constructor_argument_carries_a_default``
   reads every field off the dataclass and requires ``default`` and
   ``default_factory`` to be ``MISSING``. Defaulting here would have required
   deleting or narrowing that test.

So :class:`GovernedResolver` keeps the property its docstring claims —
*"nothing has a default"* — verbatim and under test, and
:func:`build_governed_resolver` is the seam where the SDK selects its own
reference implementation. **What that costs, stated rather than glossed:** there
are now two ways to obtain a resolver, and a reader who finds only the class
will not learn that the SDK ships a scorer. That cost is paid down here, at the
class's own ``debt_scorer`` attribute, and in the helper's docstring — not left
for a reader to discover from a support ticket. **A second default should not be
added without re-reading both measurements above**, because the argument that
selected a helper is about *this* Protocol's shape and does not transfer for
free.

Dependency direction
--------------------
This module lives in :mod:`ccf.products`, beside :mod:`ccf.products.gates` and
:mod:`ccf.products.request`, because it is **product machinery a client
consumes** rather than client machinery. The edge therefore runs one way:
``ccf.client`` depends on ``ccf.products``, never the reverse. A resolver
importing the client would make the fabric's product surface conditional on a
delivery surface, which is the inversion CLAUDE.md §10 keeps out of the layer
stack.

No boundary is crossed to achieve any of this: nothing imported below leaves
``ccf``. ``tests/invariants/test_src_does_not_import_runtime.py`` asserts that
for the whole tree rather than for this module's good intentions.

**Determination → Authority → Disclosure → Delivery** — the architectural
invariant of ``D-IMPL-254``, SDK-defined under CLAUDE.md §11 and not
whitepaper-derived (the whitepaper is deliberately not edited, ``D-IMPL-253``
Q28). Dave's text: *"Internal truth, governing authority, and permitted
disclosure are distinct concerns. The fabric preserves the governed truth of
why a determination was reached; Policy determines what of that truth may cross
the consumer boundary; the response shell expresses only the permitted
disclosure. Decision Replay preserves sufficient governed evidence to
reconstruct both the determination and the disclosure decision."*

**This module is where the four layers meet, and it is the only place they
do.** :class:`GovernedResolver` resolves the request against its authorities
(Authority), assembles and gates it (Determination), and hands every governed
"no" to :class:`ReplayRefusalRecorder` — the one seam that records the internal
truth and returns the shell :func:`~ccf.products.disclosure.disclose` permitted
(Disclosure). What a door does with that shell is Delivery, and a door decides
nothing.

This module is algorithmic (CINV-03): no LLM client on this path, ever. The
gate sequence and the replay append are the algorithmic half of the
Algorithmic ⇄ Semantic Alternation (whitepaper §7.6.6), and a model call
anywhere in the composition would put an unrecorded, irreproducible step
between a candidate and its content address.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final, Protocol, TypeVar, runtime_checkable

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DebtProfile,
    RequestBoundParameter,
    DeclaredArtifact,
    HalfLifeTable,
    OperatorParametersArtifact,
    ProductClassDeclaration,
    ReplayBinding,
    TtlBinding,
)
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.deployment import (
    BootedFabric,
    build_operator_registry,
    refuse_operator_set_divergence,
)
from ccf.graph.protocols import GraphView, TraversalDepthCapability
from pydantic import ValidationError

from ccf.halflife.assessment import NO_OBLIGATION_IN_FORCE
from ccf.products.composite import (
    ADMITTED_CHILD_CONTRACT_CLASS,
    ChildAdmissionRefusal,
    ChildContractView,
    CompositeChildResolverProtocol,
    RequestAwareChildResolverProtocol,
    CompositionOutcome,
    GATE_CHILD_ADMISSION,
    child_contract_view,
    compose_children,
    resolve_child_outcomes,
)
from ccf.halflife.debt import DebtAssessment, DebtSignal, assess_debt, context_debt
from ccf.products.contract import (
    AssemblyMode,
    ComputedEmptyFinding,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.halflife.assessment import (
    DebtFactors,
    NO_SOURCE_REFRESH_RECENCY,
    SourceRefreshRecency,
)
from ccf.products.expiry import (
    FROM_ENTITY_FRESHNESS,
    TTLAnchorResolution,
    refuse_undeclared_ttl_anchor,
    resolve_ttl_anchor,
)
from ccf.products.debt_scorer import (
    AssemblyDebtScorer,
    DeclaredFactor,
    ExecutionEvidence,
    emptiness_of,
)
from ccf.products.constraints import (
    CAPABILITY_TRAVERSAL_DEPTH,
    PolicyConstraintResolver,
    ReferencePolicyConstraintResolver,
    TechnicalCapability,
    _ConstraintSource,
)
from ccf.products.disclosure import (
    DISCLOSURE_MINIMAL,
    DisclosureLevel,
    disclose,
)
from ccf.products.entitlement import (
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import (
    DEBT_TOLERANCE_PARAMETER,
    GATE_LINEAGE_EQUALITY,
    GateRefusal,
    TTLAnchorRefusal,
    LineageMismatchRefusal,
    ProductInvariantRefusal,
    ServableProduct,
    refuse_over_tolerance,
    run_gates,
)
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    GovernedRefusalRaised,
    RefusalEnvelope,
    RefusalEvidence,
    RequestIdentity,
    envelope_for,
)
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    refuse_intent,
    refuse_undeclared_class_default,
    request_seeds,
)
from ccf.projection.engine import ExecutionResult, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionPlan
from ccf.replay.record import (
    ChildResolution,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from ccf.replay.serve import (
    QueryPinWriter,
    ReplayWriter,
    ServedProduct,
    record_refusal,
    serve,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEBT_SCORER_INPUTS",
    "AcquisitionSeamProtocol",
    "AssemblyDebtScorerProtocol",
    "GovernedResolver",
    "InstantAwareDebtScorerProtocol",
    "ProductGateProtocol",
    "ProductNotResolvable",
    "ChildAwareDebtScorerProtocol",
    "CompositePlanFactoryProtocol",
    "ProjectionPlanFactoryProtocol",
    "RefusalRecorderProtocol",
    "ReplayRefusalRecorder",
    "ResolverOutcome",
    "ServedProductResolverProtocol",
    "build_governed_resolver",
    "declared_refusal_recorder",
]

_Artifact = TypeVar("_Artifact", bound=CCFContract)

#: The four values :func:`build_governed_resolver` needs to construct the SDK's
#: reference debt scorer, named once so the refusals below enumerate them from
#: one place rather than from three hand-written lists.
#:
#: **Why the reference needs four inputs at all**, when "the SDK ships a
#: default" sounds like it should need none: two of ``D_c``'s three factors have
#: no SDK measurement, and the two that name Control Plane artifacts cannot be
#: discovered — the 2026-08-16 spec §6 rules out *"discovery or registration
#: machinery"* in this change, so a key is named or it is not resolvable. What
#: the default supplies is the **machinery** (the ``GraphView`` → ``DebtFactors``
#: adapter, the decay computation, the pinning) and never the **values**.
DEBT_SCORER_INPUTS: Final[tuple[str, ...]] = (
    "half_life_key",
    "debt_profile_key",
    "declared_completeness",
    "declared_semantic_consistency",
)


#: Of those four, the ones that are material for the reference scorer and for
#: **nothing else**.
#:
#: ``24.11-03`` / ``24.10-F-08``. ``debt_profile_key`` is deliberately absent,
#: and its absence is the repair. The mutual exclusion below refuses an
#: explicit ``debt_scorer`` alongside scorer material on the stated ground that
#: *"the material for building the reference would be read by nothing"* — true
#: of these three, and no longer true of the profile. A ``DebtProfile`` also
#: binds the obligation the served product carries, which ``D-IMPL-118`` gave
#: **its own identity on the vessel** rather than making it a rider on debt.
#:
#: So the two are alternatives about **scoring** and never about the
#: **declaration**: a deployment may supply its own scorer *and* name its bands,
#: and before ``24.11-03`` it could not — which made an obligation unreachable
#: on the governed path for every deployment that scores for itself.
_SCORER_ONLY_INPUTS: Final[tuple[str, ...]] = (
    "half_life_key",
    "declared_completeness",
    "declared_semantic_consistency",
)


#: What a resolver returns: a served product, or the refusal that stands
#: instead of one.
#:
#: A **named** alias rather than an inline union, so the two halves are one
#: nameable thing a ``match`` statement, a decoder and a docstring can all
#: spell identically. An inline union spelled at each of those sites is three
#: places to add a third member to, and the client's decoder is required to be
#: total over exactly this set.
#:
#: Both halves are frozen, ``extra=forbid`` contracts, so an outcome is a value
#: the caller carries onward — it holds no handle, no session and no callback,
#: which is what lets the same shape cross an in-process call and a wire.
ResolverOutcome = ServedProduct | RefusalEnvelope


class ProductNotResolvable(LookupError):
    """The resolver holds no product at the address it was called with.

    An **absence**, so a ``LookupError``, in the voice
    :class:`~ccf_runtime.mcp.egress.ProductNotServable` already uses at the
    egress door. Deliberately a distinct type rather than that one: importing
    it would be the first ``src`` → ``runtime`` edge in the tree, which is
    exactly what Amendment 1 §B ruled out. The two are siblings by shape, not
    by inheritance, and neither is reachable from the other's tree.

    **Raised, never returned**, and the distinction is the one
    :class:`~ccf.products.request.ProductRequestViolation` draws for itself: a
    question this class does not answer is a *bad question* and comes back as a
    refusal value, while an address this resolver was never wired to serve is a
    *broken deployment* and comes back as an exception. Reporting the two the
    same way would let a mis-wiring read to a caller as a governed "no".
    """


@runtime_checkable
class ServedProductResolverProtocol(Protocol):
    """What a deployment plugs into an in-process delivery surface.

    A Protocol rather than a base class (CLAUDE.md §11), for the reason
    :class:`~ccf.agents.assembler.ContextAssemblerProtocol` gives for its own
    case: a deployment substitutes its own resolver by **conforming**, and the
    SDK's reference implementation carries no privileged status.
    :class:`GovernedResolver` is something a deployment instantiates and
    supplies — never something the SDK invokes on its own authority.

    ``@runtime_checkable`` so a delivery surface can assert conformance at the
    boundary it is handed one, rather than discovering a shape mismatch inside
    a call it has already accepted. The check is structural and covers the
    presence of ``__call__``, not its signature; the signature is mypy's job,
    and this module is inside ``[tool.mypy] files``.

    **Two refusals a resolver must call, and no door will call for it.** This
    obligation is inherited verbatim from the two ``runtime/`` seams, whose
    docstrings argue it at length, and it is restated rather than referenced
    because a resolver author reading *this* Protocol is the person it falls
    on:

    - A resolver that does not call
      :func:`~ccf.products.request.refuse_request` **serves against an
      unchecked request** — the question is answered without ever being
      compared to the surface its product class declared.
    - A resolver that does not call
      :func:`~ccf.products.bind.refuse_bound_payload` **serves an unvalidated
      payload against a schema its own class declared**, which from a
      consumer's seat is indistinguishable from there being no schema at all.

    **Why a delivery surface cannot make either call for the resolver.** Both
    comparisons take the :class:`~ccf.products.contract.RegisteredProductClass`
    as their second operand, and a surface holding a tenant, a class name, a
    version, a perspective and a request holds no such thing — the registered
    class is resolved *behind* this seam. The SDK cannot call a comparison
    whose second operand it does not have, and reaching for it at the surface
    would put an SDK-owned verdict on the serve path that ``D-IMPL-102`` limb 3
    declined. :class:`GovernedResolver` discharges the obligation; a deployment
    writing its own discharges it itself.
    """

    def __call__(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome:
        """Return the gate-admitted product at that address, or the refusal.

        Keyword-only, so a signature of same-typed strings cannot be called
        with the tenant and the class transposed.

        Args:
            tenant: The tenant the product is addressed under. Established by
                the calling surface, never claimed by the caller's body.
            product_class: The Context Product class being requested.
            version: The class's own semver lane (INV-CH7-49). Lanes are per
                class and are never compared across classes.
            perspective: The Π role-conditioning the surface resolved and the
                deployment's entitlement policy authorized. Required and
                non-nullable, and deliberately not defaulted: a resolver
                quietly constructing its own perspective is indistinguishable
                from one honouring the surface's, and a parameter defaulting to
                ``None`` would recreate exactly that ambiguity one layer down.
            request: The typed question the caller asked, or ``None`` when
                **the surface carries no way to ask**. Required with no
                default; ``None`` is a positive assertion rather than a missing
                value, and it is spelled that way because the ``ccf-product://``
                template has three segments and no query surface among them.
                A surface that does have one passes a request whenever a caller
                supplies one.

        Returns:
            A :class:`~ccf.replay.serve.ServedProduct` — the vessel paired with
            the reference of the replay record whose successful append
            authorized its delivery — or a
            :class:`~ccf.products.refusal.RefusalEnvelope` carrying the
            governed "no" with its kind intact.

        Raises:
            ProductNotResolvable: no product at that address.
        """
        ...


@runtime_checkable
class ProjectionPlanFactoryProtocol(Protocol):
    """How a deployment builds its Π for one question.

    A factory rather than a plan, because a plan that is going to interpret a
    caller's parameters has to *see* them: the whole distinction between an
    aggregated product and an assembled one is that the question reaches the
    interpretation. Handing a resolver one long-lived plan would either freeze
    the parameters at wiring time — the *configurable rather than callable*
    defect :mod:`ccf.products.request` was written to correct — or force every
    plan to be mutable, which replay cannot tolerate.

    The SDK ships no implementation of this, and could not: which operator
    outputs mean what, and what the payload of an answer looks like, is the
    deployment's whole contribution.

    **That is now a ruling rather than an assumption.** CLAUDE.md §11 asks for a
    reference implementation beside every Protocol, so the absence was put to
    Dave and measured:
    ``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
    **Amendment A.2** records that
    :class:`~ccf.projection.plan.ProjectionPlan` is itself a Protocol — code,
    not data — that no declarative plan artifact exists in the tree, and that a
    reference factory would therefore have to *invent* the mapping from a
    :class:`~ccf.graph.protocols.GraphView` of entities onto a payload schema's
    declared fields. A "pass-through" reference plan was proposed and withdrawn
    for doing the same invention less visibly. The ruling, in substance: *§11
    does not require the impossible; it requires a reference implementation
    when one can be pure mechanism, and here it cannot.* A declarative plan
    surface is named there as future work, and it is what would close this.

    The sibling seam :class:`AssemblyDebtScorerProtocol` was measured the other
    way in the same amendment and **does** carry a shipped reference; the two
    Protocols look symmetrical and are not.
    """

    def __call__(
        self, *, required: tuple[str, ...], request: ProductRequest
    ) -> ProjectionPlan:
        """Build the plan that answers ``request``.

        Args:
            required: The operator keys the product class's own document
                declares. Passed in rather than read by the plan, so a
                deployment authoring one operator set cannot accidentally
                author a second one for Gate 2 to diverge from.
            request: The question, carrying the parameters the interpretation
                applies and the instant it is asked as of.
        """
        ...


@runtime_checkable
class CompositePlanFactoryProtocol(Protocol):
    """A plan factory that can build the parent's Π over its children's contracts.

    `D-IMPL-339`. An **optional companion** to
    :class:`ProjectionPlanFactoryProtocol`, on the
    :class:`~ccf.products.debt_scorer.EvidenceAwareFactorScorer` precedent —
    two seams rather than one widened seam. Adding a defaulted parameter to
    the base Protocol would not make any existing factory accept it, so a
    factory that can read the admitted children declares so by implementing
    this method, and the resolver decides which call to make **structurally**
    — never by probing a signature and retrying without the keyword.

    A factory implementing only ``__call__`` keeps working unchanged: a
    composite whose factory does not implement this is served exactly as it
    was, with the children contributing governance only.
    """

    def build_with_children(
        self,
        *,
        required: tuple[str, ...],
        request: ProductRequest,
        children: ChildContractView,
    ) -> ProjectionPlan:
        """Build the plan that answers ``request`` over ``children``.

        Args:
            required: As for :class:`ProjectionPlanFactoryProtocol`.
            request: As for :class:`ProjectionPlanFactoryProtocol`.
            children: The admitted children's contracts, keyed by the
                declared requirement's ``product_class``. Read-only. Every
                value came through :class:`~ccf.products.composite.CompositeAdmissionGate`
                and was re-bound to this composition before the view existed.
        """
        ...


@runtime_checkable
class ChildAwareDebtScorerProtocol(Protocol):
    """A debt scorer that can read the admitted children's contracts.

    `D-IMPL-339`. The companion to :class:`AssemblyDebtScorerProtocol` on the
    same precedent as :class:`CompositePlanFactoryProtocol` above: a parent
    whose own ``C`` or ``S`` depends on what its children reported — how many
    required legs carried positive data, say — needs those contracts at
    assessment time, per request, and this is the one path by which they
    arrive. A scorer implementing only ``__call__`` is asked exactly as before.
    """

    def score_with_children(
        self,
        *,
        view: GraphView,
        evidence: ExecutionEvidence | None,
        children: ChildContractView,
    ) -> DebtAssessment:
        """Assess ``D_c`` over ``view``, with the children's contracts in hand."""
        ...


@runtime_checkable
class AssemblyDebtScorerProtocol(Protocol):
    """How a deployment measures ``D_c`` over what one question assembled.

    Whitepaper §7.7. A Protocol and not a computation this module performs,
    because the SDK ships the *machinery* for debt and never the *values* — and
    the choice this seam hides is bigger than a threshold: measuring freshness
    over the rows a question **read** rather than over the rows that **survived
    being read** gives a different number, and which one is right depends on
    what the product means.

    **That reasoning stands; the conclusion this docstring used to draw from it
    does not.** It previously asserted that the SDK ships no implementation and
    that scoring debt here would be *"choosing for every deployment, which is
    CLAUDE.md §6.4 firing."* The ruling of record is
    ``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
    **Amendment A.1** (Dave, 2026-08-16): that **overstates the objection**. A
    documented, overridable default is not a choice imposed on every
    deployment; it is what a reference implementation *is*, and CLAUDE.md §11 —
    *"Reference implementations ship alongside Protocols"* — requires a default
    here rather than an absence. Shipping none did not spare any deployment the
    choice; it made every deployment write the adapter *and* make the choice,
    unstated, in its own tree.

    **The shipped reference is**
    :class:`~ccf.products.debt_scorer.AssemblyDebtScorer`, and it makes the
    choice explicitly rather than avoiding it: it measures over **the rows that
    survived being read** — exactly the entity records of the view it is handed,
    which under :class:`GovernedResolver` is the composed post-operator view —
    because the seam carries one view and recovering the rows the question
    *read* would need a second graph consultation at a second boundary, which
    the Decision Replay record does not describe. Its own docstring carries the
    statement in full, with the observable consequence and the override path.

    **The Protocol's real point is unchanged.** A deployment whose product
    means something different — one measuring how fresh the *consulted source
    data* was, or one counting edges as observations — supplies its own
    conforming callable, and the SDK invokes the reference one never.

    It takes the *view* rather than the payload because debt is measured
    against the assembly, not declared beside it.

    **``evidence`` joined the seam at ``24.6-05``** (``24.6-L-06``,
    ``D-IMPL-255`` (2)). ``D_c`` may not be derived from how many rows came
    back — *"Cardinality never determines Context Debt. Evidence determines
    Context Debt."* — so a conforming scorer is handed what the execution
    observed about its own search: queries issued, operators invoked and
    returned empty, source attestation, snapshot pin. It is keyword-only with
    a ``None`` default, which is *no evidence was supplied*; a scorer is free
    to ignore it, and the shipped reference passes it on to the deployment's
    ``C``/``S`` scorers that declare themselves able to read it
    (:class:`~ccf.products.debt_scorer.EvidenceAwareFactorScorer`).
    **A deployment scorer written before ``24.6-05`` must accept the keyword**
    — the governed resolver always passes it, because a resolver that decided
    per-scorer whether to tell the truth about the search would be two seams
    wearing one name.
    """

    def __call__(
        self,
        *,
        view: GraphView,
        evidence: ExecutionEvidence | None = None,
    ) -> DebtAssessment:
        """Assess ``D_c`` over the graph state this question assembled."""
        ...


@runtime_checkable
class ProductGateProtocol(Protocol):
    """How a deployment holds a product to its class's OWN declared invariant.

    **SDK-defined** (CLAUDE.md §11). The ruling of record is ``D-IMPL-282``
    ``R-11`` option 1a (Dave, 2026-09-08): *"Use a Protocol-typed callable
    supplied to* ``build_governed_resolver``, *analogous to* ``debt_scorer``.
    *The gate identity/version remain declared in the Control Plane;
    implementation is deployment-supplied."* And the boundary on it, from the
    same sitting: *"the runtime gate is not a new universal policy vocabulary.
    It is a declared product invariant with a governed identity, whose
    implementation is supplied by the deployment."*

    **What ``R-11`` supersedes, exactly.** ``D-IMPL-225`` amendment 3 said of
    ``D-IMPL-224``'s declared gates: *"There is no ``ProductGate`` Protocol, no
    serve path for them, and the SDK's universal gates stay the only serve-time
    gates."* ``R-11`` supersedes **the first two limbs and no more** — this
    Protocol exists and there is a path on which it runs. **The third limb
    stands**: a conforming callable is not a member of
    :func:`~ccf.products.gates.run_gates`' sequence, joins no token to the gate
    roster, and :data:`~ccf.products.gates.GATE_DECLARED_OBLIGATIONS` with its
    one-member ``Literal`` is untouched. The supersession is recorded here and
    on :class:`~ccf.products.gates.ProductInvariantRefusal` rather than only in
    a plan file, because a supersession that lives in a plan is one the next
    reader of these modules will not find.

    **Two halves, and they stay apart.** The Control Plane owns the gate's
    IDENTITY —
    :attr:`~ccf.controlplane.artifacts.ProductClassDeclaration.declared_product_gate`
    — and the deployment owns the PREDICATE. That is why a conforming callable
    returns a *detail string* and never an identity: the resolver stamps
    ``gate`` and ``gate_version`` from the declaration, so a deployment's gate
    cannot claim to be a different gate than the one its class declared, and
    ``D-14``'s *"which gate produced the refusal"* is a fact an examiner can
    trust rather than a claim the failing code made about itself.

    **Where it runs**, and it is ruled rather than convenient
    (``D-IMPL-282``, ``D-12``): *"after candidate construction and before
    fitness/fulfillment"* — in
    :meth:`GovernedResolver.__call__`, between :func:`run_gates` returning a
    :class:`~ccf.products.gates.ServableProduct` and
    :func:`~ccf.products.gates.refuse_over_tolerance` withholding one. So it
    never runs on a candidate the universal gates refused (there is no product
    to hold an invariant against) and it runs before an applicable tolerance
    can withhold fulfillment, because whether the answer is RIGHT is a
    different question from whether it is FIT.

    **No expression language, no rule DSL, no gate registry** (``D-11``,
    ``D-13``). The invariant is Python the deployment already writes, in the
    deployment's own tree, exactly as ``plan_factory`` and ``debt_scorer`` are.
    The SDK never parses it and never authors one.

    **A deployment gate that raises or hangs is the deployment's own
    latency and failure budget**, on the same footing as the other two
    deployment-supplied seams. Wrapping this call in a timeout would be the
    SDK choosing a deployment's budget for it, which is what CLAUDE.md §11
    refuses.
    """

    def __call__(
        self,
        *,
        candidate: ContextProductContract,
        evidence: ExecutionEvidence | None = None,
    ) -> str | None:
        """Hold ``candidate`` to the class's declared invariant.

        Args:
            candidate: The product the deployment is about to serve. The
                invariant is a property of the answer, so the answer is what
                is handed over — not the view, which is what
                :class:`AssemblyDebtScorerProtocol` takes, because debt is a
                property of the assembly and this is not.
            evidence: What the execution observed about its own search,
                keyword-only with a ``None`` default for the reason the debt
                scorer's carries one: a gate is free to ignore it, and the
                resolver always passes it, because a resolver that decided
                per-gate whether to tell the truth about the search would be
                two seams wearing one name.

        Returns:
            ``None`` to admit, or a non-empty string describing the violation
            in the deployment's own words. The SDK carries that string into
            :attr:`~ccf.products.gates.GateRefusal.detail` and never parses it:
            an invariant's failure mode is the product's to describe. An empty
            string admits — it is not a violation nobody worded, and a gate
            that means to refuse says why.
        """
        ...


@runtime_checkable
class AcquisitionSeamProtocol(Protocol):
    """The declared acquisition boundary on the governed call (`D-IMPL-343` R-4).

    **SDK-defined** (CLAUDE.md §11); the rulings of record are ``D-IMPL-279``
    ``R-09`` — *"it should accept an acquisition result / prepared context
    input produced through a declared acquisition interface"* — and Dave's
    ``D-IMPL-343`` ruling R-4, verbatim: *"Effective-request derivation runs
    once, on the governed call, and acquisition consumes that outcome. A
    preview API that re-runs constraint resolution is a second derivation and
    fails D-IMPL-289."*

    **What the seam is.** One callable a deployment (or the paved road's
    facade on its behalf) hands :class:`GovernedResolver`, invoked by
    :meth:`GovernedResolver.__call__` exactly once per question, **after** the
    effective request has been resolved — defaults applied, the constraints
    in force folded, the technical capabilities held, the intent judged — and
    **before** the graph is read at the question's boundary. It receives the
    EFFECTIVE request, so what a deployment reads its sources at is the value
    governance resolved, never a second derivation of it: the seven copies of
    ``ReferencePolicyConstraintResolver`` the canonical trees carried to guess
    that value are what this seam deletes (``D-IMPL-289``: deleted, not
    relocated).

    **What the seam is not.** It is not the resolver acquiring. The callable
    is the deployment's composition root — the paved road's
    :class:`~ccf.products.product.OpenedProduct`, or a hand-composed spine —
    and it is that root that reads a source and ingests through L2's one
    writer. :class:`GovernedResolver` holds no writer, hands no envelope to
    one, and cannot: what its docstring says about that boundary is unchanged
    by this Protocol, which adds a call and no capability. A refused question
    never reaches the seam, so a refused request acquires nothing — by the
    ordering rather than by a check the deployment remembers to write.

    ``perspective`` travels because which principal asks changes WHICH
    ENTITIES a source read may expand (a jurisdiction grant, say), and the
    deployment's acquisition is where that expansion legitimately happens.
    """

    def __call__(self, *, request: ProductRequest, perspective: Perspective) -> None:
        """Acquire and ingest whatever answering ``request`` needs; return nothing."""
        ...


@runtime_checkable
class InstantAwareDebtScorerProtocol(Protocol):
    """A debt scorer that is handed the DECISION INSTANT (`D-IMPL-343` R-3c).

    The second structural companion to :class:`AssemblyDebtScorerProtocol`,
    on exactly :class:`ChildAwareDebtScorerProtocol`'s precedent
    (`D-IMPL-339`): a scorer declares that it can read the instant the answer
    is produced as of — and, for a composite, the admitted children — by
    implementing this method, and the resolver decides which call to make
    **structurally**, never by probing a signature.

    **Why the instant has to arrive, rather than be closed over.** A scorer
    that measures freshness needs *now*, and before this seam every canonical
    tree wrote a closure over ``asked_at`` — which is the graph boundary, not
    the decision instant, and the two differ for any class declaring
    :attr:`~ccf.controlplane.artifacts.ProductClassDeclaration.decision_instant_parameter`
    (``24.10-F-09``, ``D-IMPL-308``). ``decided_at`` here IS the resolver's
    own :meth:`GovernedResolver._decision_instant` — the same value the
    product's expiry runs from and the record's ``recorded_at`` carries — so
    a deployment's freshness reading and the SDK's expiry can no longer
    disagree about when the answer was produced.

    A scorer implementing only ``__call__`` is asked exactly as before, and a
    child-aware scorer keeps its own call; this Protocol is checked first
    because it is the widest, and a scorer implementing more than one is
    asked through the widest one it declares.
    """

    def score_at(
        self,
        *,
        view: GraphView,
        evidence: ExecutionEvidence | None,
        decided_at: datetime,
        children: ChildContractView | None,
    ) -> DebtAssessment:
        """Assess ``D_c`` over ``view`` as of ``decided_at``, children in hand."""
        ...


@runtime_checkable
class RefusalRecorderProtocol(Protocol):
    """The ONE seam through which a governed refusal reaches the replay writer.

    **SDK-defined** (CLAUDE.md §11); the rulings of record are ``D-IMPL-253``
    Q13 (*"Refusal is itself a decision and deserves the same five-dimensional
    replay model. Do not create second-class replay."*) and ``D-IMPL-256``,
    whose invariant this seam exists to make structural rather than
    conventional:

        *"Every governed determination that crosses a CCF delivery boundary —
        fulfilled or refused, tool or resource, authorized or denied — must
        reach the replay writer before the response is released. A delivery
        boundary unable to satisfy that invariant is unavailable, not partially
        governed."*

    **Why a seam and not a function.** Four callers mint through it and they do
    not share a caller's shape: this module's own three refusal branches, the
    governed delivery-boundary step every entitling door calls
    (``runtime/ccf_runtime/authz/delivery_boundary.py``), and an assembler's
    own wrappers. A Protocol is what lets all four hold *one* recorder — one
    :class:`~ccf.replay.serve.ReplayWriter`, over one artifact store — while a
    deployment that files records elsewhere substitutes its own by conforming.

    **What must NOT happen here, stated because it is the failure this seam
    prevents.** ``D-IMPL-256`` again, in Dave's words: *"make sure the
    architecture does not accidentally make the transport responsible for
    minting replay. The sequence should conceptually remain: request →
    identity/policy → determination → replay → disclosure shaping → transport
    encoding, not: request → determination → HTTP/MCP → transport notices
    refusal → writes replay. Replay belongs to the governed determination, not
    to HTTP or MCP."* No module under ``runtime/ccf_runtime/http_api/`` or
    ``runtime/ccf_runtime/mcp/`` calls this seam; the governed step does, and
    the transports encode what it returns.

    ``@runtime_checkable`` so a delivery boundary can assert conformance at the
    point it is handed one rather than discovering a shape mismatch inside a
    determination it has already made. The check is structural and covers the
    presence of ``record``, not its signature; the signature is mypy's job.
    """

    def record(
        self,
        envelope: RefusalEnvelope,
        *,
        perspective: Perspective,
        recorded_at: datetime,
        request: ProductRequest | None = None,
        execution: ExecutionResult | None = None,
        policy_bindings: tuple[PolicyBinding, ...] = (),
        assembler_id: str | None = None,
        assembler_version: str | None = None,
        resolution: EffectiveRequest | ResolutionNotApplicable,
        child_resolutions: tuple[ChildResolution, ...] = (),
    ) -> RefusalEnvelope:
        """Append ``envelope``'s decision record, then return it with its address.

        The ordering is the whole mechanism and it is not negotiable: the
        record is appended **first**, and the shell the caller gets back is the
        one the append produced an address for. A caller that received a shell
        has, by construction, a recorded decision behind it.

        Args:
            envelope: The governed "no", as the determination produced it. Its
                :attr:`~ccf.products.refusal.RefusalEnvelope.replay_reference`
                is expected to be the sentinel; whatever it carries, the
                **recorded** shell carries the sentinel, because a record whose
                content address covered a reference to itself could not be
                content-addressed at all.
            perspective: Whose viewpoint the determination was reached under,
                **already resolved** — dimension 4, recorded verbatim.

                It is a :class:`~ccf.projection.plan.Perspective` rather than a
                ``principal_id`` and a ``role``, and that is a structural
                requirement rather than a convenience: ``15.5-RESEARCH.md``
                Pitfall 3 forbids a ``principal_id`` **parameter** anywhere
                under ``ccf/products``, ``ccf/projection`` or ``ccf/replay``,
                and ``tests/invariants/test_mcp_role_separation.py`` walks the
                three trees for one. Entitlement is decided at the door and
                everything below receives an already-resolved perspective; a
                seam that took the two halves apart would be assembling
                identity one layer too low.

                A delivery boundary that denies before any Π role is resolved
                passes :data:`~ccf.replay.record.NO_ROLE_RESOLVED` as the role
                — a positive claim the **door** makes, rather than a ``None``
                this seam would have to interpret on the door's behalf.
            recorded_at: The determination's own instant. For a resolver
                refusal that is the question's ``asked_at``; for a
                delivery-boundary denial it is the deployment's declared
                entitlement clock, and it is the **same** instant the
                envelope's
                :attr:`~ccf.products.refusal.ResourceRequestIdentity.determined_at`
                carries — the shell and its record cannot disagree about when
                the fabric decided.
            request: The typed question, when there was one. ``None`` for a
                standing-resource denial, which is a governed request in a
                different request form (``D-IMPL-256`` (1)).
            execution: The execution behind the refusal, when the graph was
                read. ``None`` makes dimension 1 the positive *unread* claim.
            policy_bindings: Control Plane pins in force, beyond whatever the
                recorder was constructed with.
            assembler_id: The assembler in force, and ``assembler_version`` its
                lane — dimension 4 (``D-IMPL-253`` Q16).
            resolution: The resolution state — dimension 2 (``D-IMPL-253``
                Q1/Q6; ``D-IMPL-264`` D-10). REQUIRED, with no default, as of
                24.7-04: the
                :class:`~ccf.products.provenance.EffectiveRequest` the
                Authority layer produced — complete, or the partial record it
                established before refusing (D-07) — or a
                :class:`~ccf.replay.record.ResolutionNotApplicable` marker
                stating, with its reason, that no resolution applies (D-09).
                A caller that ran no resolver says so; this seam never says
                it on the caller's behalf. ``D-IMPL-264`` amendment 1 (F-3 a), Dave verbatim: *"Any API that
        constructs or delegates construction of a replay record must require
        an explicit resolution state: effective/partial resolution or explicit
        not-applicable marker. No intermediate layer may manufacture the
        marker from omission."*

        Returns:
            The same envelope with its
            :attr:`~ccf.products.refusal.RefusalEnvelope.replay_reference` set
            to where the record landed.

        Raises:
            Exception: whatever the artifact store raises, deliberately
                uncaught. A failure to record is a failure to respond.
        """
        ...


def _disclosure_reader(
    control_plane: ControlPlaneProtocol,
) -> Callable[..., tuple[DisclosureLevel, ProvenanceSource | None]]:
    """A :attr:`ReplayRefusalRecorder.disclosure_level_for` over one registry.

    ``24.6-L-16``; ``D-IMPL-253`` Q17. Resolves the tenant's
    :class:`~ccf.products.entitlement.ProductEntitlementPolicy` under
    :func:`~ccf.products.entitlement.product_entitlement_key`, reads the
    principal's own override when the grant declares one, and falls back to the
    tenant's level. **No registered policy is
    :data:`~ccf.products.disclosure.DISCLOSURE_MINIMAL` with a ``None``
    source** — the safe default, and the ``None`` says positively that no
    policy set it rather than leaving a reader to guess.

    Read **per call**, with no cache and no TTL, on
    :class:`~ccf_runtime.authz.product_entitlement.ControlPlaneProductEntitlementSource`'s
    own reasoning (D-07): a posture tightened in the Control Plane must govern
    the next determination.

    A near-miss is refused rather than interpreted, in that source's shape too:
    an artifact under the key that is not a policy, or one whose own
    ``tenant_id`` is not the tenant it was found under, raises. Disclosing
    under a policy that names another tenant is exactly the elevation
    ``T-24.6-29`` describes.

    The returned closure is keyword-permissive for the reason
    :func:`_minimal_disclosure` is: naming ``principal_id`` as a parameter
    under ``ccf/products`` is what ``15.5-RESEARCH.md`` Pitfall 3 forbids.
    """

    def read(**asked: object) -> tuple[DisclosureLevel, ProvenanceSource | None]:
        tenant = str(asked["tenant"])
        principal = str(asked["principal_id"])
        key = product_entitlement_key(tenant_id=tenant)
        try:
            version, resolved = control_plane.resolve_latest(key)
        except LookupError:
            # Deny-by-default in the disclosure dimension: a tenant with no
            # registered entitlement policy discloses minimally. The exception
            # type is the registry's (`ControlPlaneMissing`, a `LookupError`),
            # and catching it structurally rather than by name keeps this
            # module free of a second import of the registry's error
            # vocabulary. ONLY the lookup failure is "no policy": a registry
            # that failed for any other reason propagates, because answering
            # `(minimal, None)` for it would record *no policy is registered*
            # as the disclosure's provenance when the truth is that the policy
            # could not be read — a false claim in replay dimension 5, found by
            # the Phase 24.6 close panel.
            return DISCLOSURE_MINIMAL, None
        if not isinstance(resolved, ProductEntitlementPolicy):
            raise TypeError(
                f"artifact under {key!r} is not a ProductEntitlementPolicy"
                f" (got {type(resolved).__name__}); the disclosure level is"
                " read from the tenant's own entitlement policy and a"
                " near-miss is refused, never interpreted"
            )
        if resolved.tenant_id != tenant:
            raise ValueError(
                f"policy under {key!r} declares tenant {resolved.tenant_id!r},"
                f" not {tenant!r}; disclosing under another tenant's policy is"
                " the elevation the tenant-scoped key exists to prevent"
            )
        source = ProvenanceSource(kind="artifact", identity=key, version=version)
        grant = resolved.principals.get(principal)
        if grant is not None and grant.disclosure_level is not None:
            return grant.disclosure_level, source
        return resolved.disclosure_level, source

    return read


def _minimal_disclosure(
    **_read: object,
) -> tuple[DisclosureLevel, ProvenanceSource | None]:
    """The posture a recorder with nothing to ask can honestly report.

    ``D-IMPL-253`` Q17: *"Suppression silence should be policy-controlled, with
    minimal disclosure as the safe default."* A recorder constructed without a
    Control Plane reader cannot resolve any tenant's policy, so
    :data:`~ccf.products.disclosure.DISCLOSURE_MINIMAL` is not a fallback here —
    it is the only true answer, and the ``None`` source says positively that no
    policy set it.

    Keyword-permissive so it satisfies the seam's shape without naming the two
    keywords: a default that declared ``principal_id`` would put that parameter
    under ``ccf/products``, which ``15.5-RESEARCH.md`` Pitfall 3 forbids and
    ``tests/invariants/test_mcp_role_separation.py`` fails on.
    """
    return DISCLOSURE_MINIMAL, None


@dataclass(frozen=True, kw_only=True)
class ReplayRefusalRecorder:
    """The SDK's reference :class:`RefusalRecorderProtocol` — one writer, one store.

    **SDK-defined** (CLAUDE.md §11), and the reference implementation CLAUDE.md
    §11 requires beside every Protocol. It composes exactly two shipped things
    and invents nothing: :func:`~ccf.replay.record.build_replay_record` with
    the refusal as its outcome, and :func:`~ccf.replay.serve.record_refusal`
    over a :class:`~ccf.replay.serve.ReplayWriter` — the **same** writer class
    the served path uses, over the store the deployment already handed its
    resolver. That sameness is the substance of *"do not create second-class
    replay"*: a second writer, or a second record shape, would be exactly that.

    It is also why the ArtifactStore never becomes a second writer to the graph
    (CLAUDE.md §7.4, §10): this type holds a store and no graph handle, and
    nothing below reaches one.

    Attributes:
        artifact_store: Where the record lands. A substrate reached *through*
            mechanism.
        replay_record_class: The artifact class replay records are filed under.
            Deployment vocabulary, supplied rather than assumed.
        tenant_id: The tenant every determination this recorder writes was made
            under. A refusal carries no vessel to read it off, so it is stated
            once here rather than at each call — a recorder is bound to a
            deployment exactly as its resolver is.
        assembly_mode: The mode dimension 3 records.
            :func:`~ccf.replay.record.build_replay_record` takes it with no
            default, so it is held here rather than defaulted into existence.
        policy_bundle_pin: The bundle in force, prepended to every record's
            bindings. ``None`` — the default — means the record's bindings are
            **exactly** the caller's tuple, which is the honest posture for a
            recorder wired by a delivery boundary that holds no bundle key.
        disclosure_level_for: How this recorder reads the posture in force
            (``24.6-L-16``; ``D-IMPL-253`` Q17). Called as
            ``(tenant=..., principal_id=...)`` and returning the level with the
            Control Plane source that set it.

            **Keyed by principal, not by**
            :class:`~ccf.projection.plan.Perspective`: a delivery-boundary
            denial has a principal and no resolved role at all
            (``NO_ROLE_RESOLVED``), and it must disclose under the same reader
            a resolver refusal for that principal would. A signature that
            needed a role would have made the two paths disclose differently,
            which is the observational difference ``D-IMPL-253`` amendment 2
            (4) forbids.

            The default is :func:`_minimal_disclosure`, which reads nothing and
            answers ``(DISCLOSURE_MINIMAL, None)``. A recorder wired with no
            Control Plane to ask cannot resolve a policy, and the safe default
            is the only coherent answer — asserted here rather than left to a
            caller to remember. :func:`build_governed_resolver` supplies a
            reader over the deployment's own registry.
    """

    artifact_store: ArtifactStoreProtocol
    replay_record_class: str
    tenant_id: str
    assembly_mode: AssemblyMode
    policy_bundle_pin: PolicyBinding | None = None
    # A `default_factory` rather than a bare `default`, and the reason is a
    # measurement rather than a style: a function object's `repr` carries its
    # memory address, and `docs/surface/v0.2-surface.json` renders this
    # dataclass's `__init__` signature — so a plain default would put
    # `<function _minimal_disclosure at 0x…>` in a committed manifest, which is
    # a different document on every run. `dataclasses` renders a factory's
    # default as the stable `<factory>` sentinel.
    # (`tests/test_surface_shape_capture.py::test_the_serialized_manifest_carries_no_memory_addresses`.)
    disclosure_level_for: Callable[
        ..., tuple[DisclosureLevel, ProvenanceSource | None]
    ] = field(default_factory=lambda: _minimal_disclosure)

    def record(
        self,
        envelope: RefusalEnvelope,
        *,
        perspective: Perspective,
        recorded_at: datetime,
        request: ProductRequest | None = None,
        execution: ExecutionResult | None = None,
        policy_bindings: tuple[PolicyBinding, ...] = (),
        assembler_id: str | None = None,
        assembler_version: str | None = None,
        resolution: EffectiveRequest | ResolutionNotApplicable,
        child_resolutions: tuple[ChildResolution, ...] = (),
    ) -> RefusalEnvelope:
        """Disclose, append the INTERNAL truth, then hand back the shell.

        See :meth:`RefusalRecorderProtocol.record` for the argument contract.
        ``resolution`` is passed through to the builder exactly as received
        and is required here for the reason it is required there
        (24.7-04; ``D-IMPL-264`` amendment 1 (F-3 a), Dave verbatim: *"Any API that
        constructs or delegates construction of a replay record must require
        an explicit resolution state: effective/partial resolution or explicit
        not-applicable marker. No intermediate layer may manufacture the
        marker from omission."*).

        **The order is the architecture** (``D-IMPL-254``). The record is built
        from the **internal** envelope — the determination as the fabric
        reached it, whole — together with the
        :class:`~ccf.products.disclosure.DisclosureDecision` that produced the
        shell; what is returned is the **disclosed** envelope with its address
        attached. So replay reconstructs both *what was determined* and *why
        the consumer saw the particular response it saw*, which is the pair
        ``D-IMPL-254`` requires and which recording only the shell would lose.

        Dave, ``D-IMPL-253`` Q27: *"Don't destroy audit truth merely to achieve
        external suppression silence."* Recording the disclosed form would be
        exactly that.

        There is **one** entry to this seam and there is deliberately no
        disclose-without-recording entry beside it: ``D-IMPL-256`` (1) makes
        every delivery-boundary denial hold an instant, so a caller that wanted
        a disclosed shell without a record would be asking for the replay hole
        the ruling closed. The name that shape would have carried is spelled
        nowhere in ``src/``, so the grep that proves its absence is a clean
        zero (the ``24.6-04`` precedent for a retired identifier). **No caller of this seam calls**
        :func:`~ccf.products.disclosure.disclose` **itself** — the resolver's
        own branches, the governed delivery-boundary step and an assembler's
        wrappers all reach disclosure only through here, so one determination
        cannot be disclosed twice by two readings of the policy.
        """
        level, disclosure_policy = self.disclosure_level_for(
            tenant=self.tenant_id, principal_id=perspective.principal_id
        )
        disclosed, decision = disclose(
            envelope, level=level, policy=disclosure_policy
        )
        record = build_replay_record(
            execution=execution,
            product=None,
            refusal=envelope,
            # Recorded verbatim: identity is resolved at the door and this seam
            # constructs none of it (Pitfall 3).
            perspective=perspective,
            policy_bindings=(
                *(
                    (self.policy_bundle_pin,)
                    if self.policy_bundle_pin is not None
                    else ()
                ),
                *policy_bindings,
            ),
            assembly_mode=self.assembly_mode,
            recorded_at=recorded_at,
            tenant_id=self.tenant_id,
            assembler_id=assembler_id,
            assembler_version=assembler_version,
            # `CMP-R-01`. One row per DECLARED requirement, refused or not, so
            # a refused composite's record names the children it tried. `()`
            # for every non-composite refusal, which is the true claim rather
            # than a filler — and it is hash-transparent, so no existing
            # record's content address moves.
            child_resolutions=child_resolutions,
            # Dimension 5's own record of the Disclosure layer, pre-serialized
            # in the SDK's one canonical form — the `hitl_actions` and
            # `workflow_step_sequence` discipline: a block the layer that made
            # the decision produced, recorded verbatim rather than rebuilt here.
            disclosure=canonical_bytes(decision).decode("utf-8"),
            resolution=resolution,
            request=request,
        )
        reference = record_refusal(
            record=record,
            replay_writer=ReplayWriter(
                store=self.artifact_store,
                artifact_class=self.replay_record_class,
            ),
        )
        return disclosed.model_copy(update={"replay_reference": reference.uri})


def _artifact_on(
    fabric: BootedFabric, *, key: str, expected: type[_Artifact]
) -> _Artifact:
    """One parsed artifact off ``fabric``, or a wiring refusal naming both sides.

    The narrowing is not ceremony. A manifest key is a string, and a resolver
    handed the wrong one would otherwise fail somewhere further down with a
    message about a field, at which point the actual defect — this key names
    that artifact — is two layers away from what is reported.

    Module-level rather than a method because
    :func:`build_governed_resolver` needs the identical check *before* a
    resolver exists, and the manifest read staying in **one** place is what
    ``17-11`` deferred to this plan.

    Raises:
        ProductNotResolvable: the key names no artifact, or names one of
            another class. A broken deployment, so an exception rather than a
            governed "no" — the distinction :class:`ProductNotResolvable` draws
            for itself.
    """
    try:
        artifact = fabric.artifacts[key]
    except KeyError as absent:
        raise ProductNotResolvable(
            f"manifest key {key!r} names no artifact on the booted fabric;"
            f" the manifest declares {sorted(fabric.artifacts)}"
        ) from absent
    if not isinstance(artifact, expected):
        raise ProductNotResolvable(
            f"manifest key {key!r} holds {type(artifact).__name__}, and this"
            f" resolver reads it as {expected.__name__}"
        )
    return artifact


def _refuse_unbindable_request_parameter(
    *,
    parameters: Mapping[str, OperatorParametersArtifact],
    declared: ProductRequestContract | None,
    request_contract_key: str,
) -> None:
    """Raise unless every request-bound operator parameter names a declared argument.

    ``24.11-04`` / ``D-IMPL-295``, in
    :func:`~ccf.products.request.refuse_undeclared_class_default`'s shape and
    for its reason: a binding naming a parameter the request contract does not
    expose is a **malformed declaration**, and it should fail where the two
    documents disagree rather than three frames down on the first call that
    happens to exercise it.

    **Existence only, and the narrowness is deliberate.** This asks whether the
    contract declares the name; it says nothing about the value's type. Judging
    the type here would mean comparing a JSON-Schema ``type`` against a Python
    field annotation — a second type system, kept in step with the first by
    hand, disagreeing with it the first time either moves. The artifact's own
    validation already settles the type when the value arrives
    (:meth:`GovernedResolver._bind_declared_request_values` revalidates), so
    there is exactly one authority on the question and it is the field itself.

    A deployment naming no request contract is not checked: it has no
    declaration for a binding to disagree with, and the resolution path refuses
    the binding when the value fails to arrive.

    Raises:
        ProductNotResolvable: a binding names an argument the contract does not
            declare, naming the operator key, the field, the parameter and the
            arguments the contract does expose.
    """
    if declared is None:
        return
    exposed = set(declared.arguments.properties)
    for key, artifact in sorted(parameters.items()):
        for name, value in artifact:
            if not isinstance(value, RequestBoundParameter):
                continue
            if value.parameter not in exposed:
                raise ProductNotResolvable(
                    f"operator parameters {key!r} bind {name!r} to request"
                    f" parameter {value.parameter!r}, which the request"
                    f" contract {request_contract_key!r} does not declare;"
                    f" it exposes {sorted(exposed)}. A binding and the contract"
                    " it binds to are one declaration in two documents, and"
                    " they disagree (D-IMPL-295)"
                )


def _request_contract_on(
    fabric: BootedFabric, *, key: str
) -> ProductRequestContract:
    """One request contract off ``fabric``, however the manifest authored it.

    Module-level for :func:`_artifact_on`'s reason, which
    :func:`build_governed_resolver` now needs a second time: the
    ``D-IMPL-258`` (5) check runs at boot, *before* a resolver exists, and it
    must read the contract exactly as :meth:`GovernedResolver._request_contract`
    will read it at request time. Two transcriptions of one manifest key are
    two chances to disagree about what a class's request surface is, and the
    check whose whole subject is that surface is the worst place to disagree.

    Raises:
        ProductNotResolvable: the key names no artifact, or names one that is
            neither a declared artifact nor a request contract.
    """
    artifact = fabric.artifacts.get(key)
    if isinstance(artifact, DeclaredArtifact):
        return ProductRequestContract.from_declared(artifact)
    return _artifact_on(fabric, key=key, expected=ProductRequestContract)


def _capabilities_of(fabric: BootedFabric) -> tuple[TechnicalCapability, ...]:
    """The technical limits the booted fabric can be asked for, if any.

    ``D-IMPL-253`` Q21. Structural, on the
    :class:`~ccf.graph.protocols.SnapshotPinnable` idiom: whatever the boot
    handed back is *asked* whether it reports a traversal ceiling, and a
    substrate that reports none contributes nothing — no flag, no stub, and no
    number invented on its behalf.

    **What this reaches today, measured rather than assumed.**
    :class:`~ccf.boot.FabricHandle` exposes a *reader*, and the two ceilinged
    backends declare their bound on the *store*, which the handle deliberately
    does not carry. So for every shipped boot path this derives the empty tuple
    — the honest answer, since nothing the resolver is handed can report a
    ceiling — and a deployment that holds its store passes ``capabilities``
    explicitly to :func:`build_governed_resolver` or to
    :class:`GovernedResolver`. The walk is written over both objects so that a
    handle or reader which later reports one is picked up with no edit here.

    Duplicate identities are collapsed, so a handle and its reader that are the
    same object — or two objects reporting one substrate — contribute one bound
    rather than two identical ones.
    """
    found: dict[tuple[str, str], TechnicalCapability] = {}
    for candidate in (fabric.handle, getattr(fabric.handle, "reader", None)):
        if not isinstance(candidate, TraversalDepthCapability):
            continue
        capability = TechnicalCapability(
            capability=CAPABILITY_TRAVERSAL_DEPTH,
            maximum=Decimal(candidate.max_traversal_depth),
            identity=candidate.capability_identity,
        )
        found.setdefault(
            (capability.capability, capability.identity), capability
        )
    return tuple(found[key] for key in sorted(found))



def _utc_now() -> datetime:
    """The process's UTC clock.

    The default for :func:`build_governed_resolver`'s ``admission_clock``
    (`D-IMPL-336` **O3**), and the same one-line shape
    :mod:`ccf.controlplane.registry` already uses for the same reason: the
    machinery takes a clock so a test can pin an instant, and exactly one
    place names the real one.
    """
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class GovernedResolver:
    """The SDK's reference composition: assemble → gate → record → serve.

    **A reference implementation a deployment instantiates and supplies, never
    a resolver the SDK invokes on its own authority.** It carries exactly the
    privileged status :class:`~ccf.agents.assembler.DeterministicAssembler`
    carries against its own Protocol, which is none: conformance is structural,
    the SDK calls nothing here by itself, and a deployment substituting its own
    resolver loses no capability.

    **Every value this composition needs that the SDK cannot know arrives from
    outside it, and nothing has a default.** That is the constraint Amendment 1
    §B attaches to the ruling and the reason this module is allowed to exist at
    all: the composition is *mechanism* — an ordering, and the gate and replay
    obligations along it — while every threshold, class name, policy key, TTL
    figure, operator parameter set and artifact-class token stays a Control
    Plane artifact or a constructor argument the deployment authored. A
    defaulted TTL, a defaulted product class or a defaulted threshold here
    would be a defect of the same severity as a half-life table in library
    code (CLAUDE.md §6.4).

    ``kw_only=True`` for the reason the Protocol is keyword-only: several
    arguments are same-typed strings, and a transposition would resolve a
    different artifact without failing.

    **What arrives as a manifest key rather than as an object.** Five — the
    product class, the request contract, the operator parameter sets, the
    policy bundle and the debt profile — are named by *key* and read off
    :attr:`~ccf.deployment.BootedFabric.artifacts`. That is
    :func:`~ccf.deployment.load_and_boot`'s own recommended idiom, and it buys
    a governance property a passed object cannot: the declaration this resolver
    serves is provably the one the manifest put in force, rather than one a
    caller assembled beside it. A key holding the wrong artifact class is a
    wiring defect and is refused on the first call, naming both sides.

    **What deliberately stays a constructor argument.** The projection factory
    and the debt scorer are behavior rather than declaration and have no
    artifact form — so they are *supplied*, and neither is defaulted here; a
    deployment that wants the SDK to choose its scorer calls
    :func:`build_governed_resolver`, which is where the choosing lives. The
    two differ in what a deployment can supply: the SDK ships
    :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` for the second and
    ships nothing for the first, because Amendment A.1 of the 2026-08-16 spec
    ruled a reference plan factory impossible as scoped — a
    :class:`~ccf.projection.plan.ProjectionPlan` is itself a Protocol, no
    declarative plan artifact exists, and mapping operator outputs onto a
    declared payload shape is invention rather than mapping. The
    artifact store is a substrate, not Control Plane state. The two
    artifact-class tokens are deployment vocabulary, exactly as
    :class:`~ccf.replay.serve.ReplayWriter` already treats its own. And the two
    TTL figures **stay two**: the class's ceiling is registered here to mint
    its pin, and the product's own lifetime is authored separately, because a
    single figure serving as both would have Gate 3 compare a ceiling against
    itself — the failure :func:`~ccf.deployment.load_and_boot` warns about in
    its own docstring.

    **What this composition does not do, and will not learn to.** It hands no
    envelope to the L1 writer, creates no store, mints no schema and boots
    nothing: the deployment it is handed is already booted and already
    populated. A resolver that provisioned would make a client call a
    producer-side act, which is the boundary the client design draws in its §7,
    and it would need a write handle to the graph — which this type is
    constructed without and cannot obtain (single-writer, CLAUDE.md §10). The
    absence is structural rather than described: nothing below reaches
    ``fabric.handle.worker``.

    **What it cannot serve yet, measured against the SDK's own worked example**
    (``24.10-04`` / ``R-03``; ``D-IMPL-282``). That ruling opened
    ``examples/s1-01-hello-context-product/spine.py`` so that *"can an author
    reach this composition?"* could be answered by trying rather than by
    asserting. It was tried, against a live substrate, and **it could not**.
    Four seams were absent; each carries an executable test in
    ``tests/examples/test_s1_01_governed_resolver_adoption.py``, and none of
    them is a defect in the example. **Two — ``24.10-F-06`` and ``24.10-F-07``
    — are closed as of ``24.11-02b``; two remain.** The closed ones are kept in
    this roster rather than deleted from it, because what a composition *used
    to* get wrong is what says why the line that fixes it is load-bearing:

    ``24.10-F-06`` — **CLOSED in two parts, ``24.11-02`` then ``24.11-02b``**
        A product class whose operator set included the **Similarity**
        category — one of whitepaper §7.4's four — could not be served at all.
        :func:`~ccf.deployment.build_operator_registry` was called below with
        no ``similarity_index_version``, which that builder then required
        exactly when a similarity artifact was present (``D-IMPL-38``, and
        rightly: an unversioned index is one replay cannot be held against).
        There was no field here and no argument on
        :func:`build_governed_resolver`, and the registry is built inside
        :meth:`__call__` — so a deployment had nowhere to supply it, and every
        such call died three frames below a composition it had no way to
        configure.

        ``24.11-02`` fixed the propagation by giving this class a
        deployment-owned ``similarity_index_version`` field. **That closed the
        runtime seam and left the architecture open**, and Dave ruled it
        insufficient (``D-IMPL-292``): *"the deployment still has to tell the
        resolver something that materially affects operator behavior and
        reproducibility … it must not remain an ungoverned deployment-supplied
        semantic value."* A workaround relocated from test code into caller
        code is still a workaround (``D-IMPL-289``).

        **``24.11-02b`` moved the authority to the declaration**, and there is
        consequently *nothing here* to see: the field is gone, the argument on
        :func:`build_governed_resolver` is gone, and this class passes no
        version to the builder. The value is declared on
        :class:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact`
        — an artifact this resolver already loads by manifest key, already
        hands the builder, and whose content hash is already in the pin set —
        so the corpus identity a determination ranked against is now visible in
        replay dimension 2 where it previously appeared nowhere. Dave's
        authority model, verbatim: *"declaration owns the version → resolver
        consumes it → deployment supplies the implementation, not an alternate
        semantic version."* One site, not a precedence order. Regressed
        directly at ``tests/products/test_resolver_seam.py::
        test_the_declared_index_version_is_the_only_authority``.
    ``24.10-F-07`` — **CLOSED, ``24.11-01``**
        :meth:`__call__` executed Π with **no seeds**, while
        :mod:`ccf.replay.engine` replays with
        ``seeds=``:func:`~ccf.products.request.request_seeds`. Two questions
        about two different subjects therefore compiled to the same graph query
        and pinned identically — ``DI-15.5-07``, which ``D-IMPL-111`` limb (a)
        closed on the hand-built path — and a served product whose plan walks
        was replay-divergent by construction. :meth:`__call__` now passes
        ``seeds=request_seeds(request)``, derived from the **caller's**
        request: the same object it hands
        :func:`~ccf.replay.record.build_replay_record`, which dimension 5
        carries verbatim and :mod:`ccf.replay.engine` reads back — so the two
        paths are one reading of one object rather than two derivations that
        could drift. Regressed directly at ``tests/products/
        test_resolver_seam.py::
        test_two_subjects_cannot_collapse_to_one_question_to_the_graph``.
    ``24.10-F-08`` — **obligation limb CLOSED at** ``24.11-03``
        The candidate below set none of ``obligation_in_force``,
        ``source_refresh_recency`` or ``debt_evidence``. All three are inside
        the product's content address, so none is an omission a deployment can
        repair afterwards. ``24.11-03`` closed the first: the candidate now
        composes :meth:`_obligation_in_force`, which reads the profile named by
        :attr:`debt_profile_key` and asks it what it binds to the state the
        assessment landed in. Two changes carried it, and the second was the
        one the probe found — :func:`build_governed_resolver` had treated the
        profile key as scorer material *only*, so a deployment supplying its
        own scorer could not declare its bands at all and could never carry an
        obligation. Regressed at ``tests/products/test_resolver_seam.py::
        test_the_served_product_carries_the_obligation_the_profile_bound``
        with its negative control beside it, and the ``s1-01`` adoption test
        that carried this finding is un-quarantined and passing unchanged.

        **The other two limbs stay open, and neither is a dropped join.**
        Measured at ``24.11-03``: nothing in ``src/`` or ``runtime/``
        constructs a :class:`~ccf.halflife.assessment.SourceRefreshWindow` or a
        :class:`~ccf.halflife.assessment.DebtEvidencePointer`, and no SDK
        artifact declares either — so composing them is not a join the resolver
        drops but an authority the SDK does not have. For source-refresh
        recency that absence is *ruled* (``D-IMPL-124``: the SDK ships no
        reducer, because one would decide which of a deployment's sources count
        toward the window). For evidence pointers it is a standing prohibition
        (``D-IMPL-119`` limb 4) whose named precondition — a perspective-scoped
        view in the assembly path — this path still does not meet. Giving
        either a declaration home is an architecture question and is not this
        row's.
    ``24.10-F-09``
        ``expires_at``, the gate instant and ``recorded_at`` all derive from
        ``request.asked_at``, so a class declaring a **decision instant**
        distinct from the graph boundary finds nothing reads it.

    What remains is recorded here rather than fixed here. ``D-IMPL-282``:
    *"No broader API redesign is authorized up front"* — the escalation it
    earns is Dave's ruling to make, and the tests are what go loudly red when a
    seam lands without its finding being closed. ``F-07``, ``F-06`` and
    ``F-08``'s obligation limb are the three that have had that ruling
    (``D-IMPL-290``, ``D-IMPL-291``, ``D-IMPL-292``), and each was taken
    **alone**: one repair per row, so that what a row moved stays attributable
    to what a row changed.

    Attributes:
        fabric: The booted deployment, exactly as
            :func:`~ccf.deployment.load_and_boot` returned it — so an adopter
            hands back what they were given rather than unpacking it. Supplies
            the L3 **reader** (never a writer: single-writer holds across this
            seam by construction, CLAUDE.md §10), the resolved pins, the tenant
            and the parsed artifacts.
        control_plane: The Control Plane the fabric booted against. A caller
            argument and never constructed here, on
            :func:`~ccf.deployment.load_and_boot`'s own reasoning: a registry
            built behind the adopter's back would split the audit sequence in
            two, and the Control Plane is the audit plane, singular.
        product_class_key: Manifest key of the
            :class:`~ccf.controlplane.artifacts.ProductClassDeclaration` this
            resolver serves.
        request_contract_key: Manifest key of the request surface that class
            declares. Read as a :class:`~ccf.products.request.ProductRequestContract`,
            or through :meth:`~ccf.products.request.ProductRequestContract.from_declared`
            when the manifest authored it in an adopter namespace — which is the
            ordinary case, and the transcription ``D-IMPL-126`` exists to spare
            every adopter.
        operator_parameter_keys: Manifest keys of the operator-parameters
            artifacts this deployment declared — **however many**. One yields a
            one-operator registry; this resolver holds no fixed set of four
            keys and never counts them (``D-IMPL-132``).

            **A similarity artifact named here carries its own corpus version
            identity** and needs no companion field (``24.11-02b`` /
            ``D-IMPL-292``; see ``24.10-F-06`` above). This class holds no
            ``similarity_index_version``: the artifact these keys resolve to is
            handed to :func:`~ccf.deployment.build_operator_registry`, and the
            builder reads
            :attr:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact.index_version`
            off it. A field here would be a second site for one semantic value,
            and a deployment able to state a version other than the one it
            declared is a deployment able to make its own determination
            irreproducible.
        policy_bundle_key: The key whose pinned version becomes the admitted
            bundle version and the product's policy binding.
        debt_profile_key: Manifest key of this deployment's ``D_c`` bands, whose
            ``signal_obligations`` bind the obligation the served product
            carries (``24.11-03``, ``24.10-F-08``). ``None`` is admissible and
            is the positive claim that this deployment declares no bands — never
            a default, for every other field's reason. **Independent of**
            ``debt_scorer``: a deployment that scores for itself may still
            declare its bands, because ``D-IMPL-118`` gave the obligation its
            own identity on the vessel rather than making it a rider on debt.
        plan_factory: How this deployment builds Π for one question.
        constraint_resolver: How this deployment resolves a question's
            parameters against every authority that bounds them — the class's
            declared defaults, the caller's values, the Control Plane's policy
            constraints in force at ``asked_at``, and the substrate's technical
            capabilities (``D-IMPL-253`` Q8). No default here for the reason
            ``debt_scorer`` has none: this class is the auditable, defaultless
            composition, and :func:`build_governed_resolver` is where the SDK's
            own :class:`~ccf.products.constraints.ReferencePolicyConstraintResolver`
            is chosen.
        capabilities: The technical limits in force, read off the substrate by
            whoever wired this resolver. Supplied rather than discovered here,
            because the fabric hands back a *reader* and the ceiling is a
            property of the *store* — and because a resolver that went looking
            for capabilities would be deciding, on its own authority, which
            substrate facts govern a question. The empty tuple is the positive
            statement that no technical bound applies, which is every
            deployment on a store that declares none.
        debt_scorer: How this deployment measures ``D_c`` over an assembly.
            :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` is the shipped
            reference, and **it is what** :func:`build_governed_resolver`
            **selects when no scorer is passed** — a deployment reaching the
            fabric through that helper never names it and never has to know the
            Protocol exists. Supplying it *here* is the deployment's act, never
            this class's, which is why the field has no default: this class is
            the auditable, defaultless composition, and the helper is where the
            SDK's own reference is chosen. See the module docstring for the
            measurement that split them.
        product_gate: The deployment's own implementation of the invariant its
            product class DECLARES, or ``None`` when the class declares none
            (``24.10-02`` / ``R-11``; ``D-IMPL-282`` option 1a). Written in
            ``debt_scorer``'s voice and for its reason: the SDK ships the
            machinery and never the values, and here the value is the invariant
            itself. What it may say is bounded — a violation string or
            ``None`` — because the gate's IDENTITY is the Control Plane's
            (:attr:`~ccf.controlplane.artifacts.ProductClassDeclaration.declared_product_gate`)
            and this class stamps it onto the refusal rather than accepting it
            from the callable.

            **The two halves must agree, and** :func:`build_governed_resolver`
            **refuses at build time when they do not**: a callable against a
            class declaring no gate is a check nothing governs, and a declared
            gate with no callable is *"a default that nothing exercises*, which
            *is a check that stops checking without going red."* No default
            here, for ``debt_scorer``'s reason — ``None`` is a value the
            deployment states, not one this class assumes.
        refusal_recorder: The ONE seam through which every governed refusal
            this composition produces reaches the replay writer
            (``24.6-07``; ``D-IMPL-253`` Q13, ``D-IMPL-256``). No default here
            for ``debt_scorer``'s reason — this class is the auditable,
            defaultless composition, and :func:`build_governed_resolver` is
            where the SDK's own :class:`ReplayRefusalRecorder` is chosen over
            the store and tenant this resolver was already handed.

            It is a **field** and not a method because three other callers mint
            through it: the governed delivery-boundary step every entitling
            door calls, and an assembler's own wrappers. One resolver, one
            recorder, one writer, one store — which is what makes *"no second
            writer"* a fact about the wiring rather than a rule people follow.
        artifact_store: Where the replay record and the executed queries' bytes
            land. A substrate reached *through* this mechanism, never a second
            writer to the graph (CLAUDE.md §7.4).
        replay_record_class: The artifact class replay records are filed under.
        query_pin_class: The artifact class executed queries' bytes are filed
            under.
        max_ttl_seconds: The class's TTL **ceiling**. Registering it is what
            mints ``max_ttl_version``, which is why the class document cannot
            declare it.
        product_ttl_seconds: How long a product this resolver serves stays
            servable. Independent of the ceiling by construction; Gate 3
            compares the two.
    """

    fabric: BootedFabric
    control_plane: ControlPlaneProtocol
    product_class_key: str
    request_contract_key: str
    operator_parameter_keys: tuple[str, ...]
    policy_bundle_key: str
    debt_profile_key: str | None
    plan_factory: ProjectionPlanFactoryProtocol
    debt_scorer: AssemblyDebtScorerProtocol
    product_gate: ProductGateProtocol | None
    constraint_resolver: PolicyConstraintResolver
    capabilities: tuple[TechnicalCapability, ...]
    refusal_recorder: RefusalRecorderProtocol
    artifact_store: ArtifactStoreProtocol
    replay_record_class: str
    query_pin_class: str
    max_ttl_seconds: int
    product_ttl_seconds: int
    #: `D-IMPL-336` Amendment 3, F0 — how this deployment resolves, invokes,
    #: delivers and admits the children a composite class declares. ``None``
    #: for every non-composite deployment, which is every one shipped before
    #: this surface; a class that declares ``requires`` against a resolver
    #: with no child resolver is REFUSED rather than served without them.
    #:
    #: The SDK ships the Protocol **and** a reference implementation —
    #: :class:`~ccf.products.child_resolver.GrantBoundChildResolver` — under
    #: CLAUDE.md §11. This comment said the opposite until close panel 2; the
    #: correction is `D-IMPL-336` Amendment 5, which ruled that resolving a
    #: grant and dispatching it once is not an agent loop. What stays out of
    #: `src/` is the scheduler, the swarm loop and any new identity axis.
    composite_children: (
        CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None
    )

    #: `D-IMPL-336` **O3** — the trusted runtime clock a child admission is
    #: judged against.
    #:
    #: Admission time is **not** the decision instant. `D-IMPL-308` lets a
    #: class declare its decision instant from the request, which is right for
    #: expiry — a reconstruction of a historical decision expires from when
    #: that decision was produced. It is wrong for eligibility: `F7`'s
    #: evidence-age bound asks *how old is this evidence NOW*, and answering it
    #: with a declared historical instant lets a request move the window its
    #: own evidence is checked in. The earlier behavior was conservative in
    #: practice — the skew check refused rather than admitted — but a check
    #: whose safety depends on which way the caller's declared instant happens
    #: to fall is not a check.
    #:
    #: Injected rather than read from the wall clock here, so the boundary is
    #: testable exactly; the default lives in
    #: :func:`build_governed_resolver`, never on this class, which permits no
    #: constructor defaults at all.
    admission_clock: Callable[[], datetime]

    #: The request-contract argument that carries this class's DECISION
    #: INSTANT, or ``None`` when the class declares none — `24.10-F-09`,
    #: `D-IMPL-308`.
    #:
    #: **The graph boundary and the decision instant are two different facts**
    #: and this resolver used to have only one. ``request.asked_at`` is *when
    #: the graph is observed*; the decision instant is *when the answer is
    #: produced*, and a class may legitimately declare them apart — `s1-01`
    #: declares a boundary of ``00:00``, a decision instant of ``00:05`` and an
    #: expiry of ``00:15``, and proves by that spread that nothing in the path
    #: reads a clock.
    #:
    #: **Coincidence is allowed; collapse is not** (`D-IMPL-308`). A class
    #: declaring no such parameter leaves this ``None`` and every instant
    #: continues to derive from ``asked_at``, which is what
    #: `s1-00-companies-over-revenue` legitimately does. What this forbids is
    #: substituting one for the other when the class says they differ.
    decision_instant_parameter: str | None

    #: When this deployment's sources last published — `24.10-F-08`,
    #: `D-IMPL-308`.
    #:
    #: **Declaration-owned evidence, and it is inside the content address.** A
    #: refresh window is a fact about the world upstream of the fabric: the
    #: deployment knows it and no operator can observe it, which is why it
    #: arrives here as a declared value rather than being derived from the
    #: view. The candidate below used to set nothing, so a deployment that
    #: declared a window watched the canonical path drop it silently — and
    #: because the field is sealed, that is not an omission a deployment can
    #: repair afterwards.
    source_refresh_recency: SourceRefreshRecency

    #: `D-IMPL-343` R-4 — the declared acquisition boundary, or ``None`` for a
    #: deployment whose fabric is populated before this resolver is reached
    #: (every deployment shipped before the seam existed, and every hw1-shaped
    #: long-lived fabric). When present it is called ONCE per question, with
    #: the EFFECTIVE request, between resolution and the graph read — see
    #: :class:`AcquisitionSeamProtocol` for what it is and is not. No default
    #: here for the class's own reason; :func:`build_governed_resolver`
    #: defaults it to ``None``.
    acquisition: AcquisitionSeamProtocol | None
    # `D-IMPL-341`: the manifest key of this deployment's λ_c table, when it
    # has one. Read at the mint to derive an evidence-anchored expiry from the
    # same observations the freshness factor scores, and pinned on the record
    # for such a serve so replay re-derives the anchor under the same table.
    # ``None`` for a resolver wired without a table — an evidence-anchored
    # class then refuses by name at gate 3 rather than anchoring on anything.
    half_life_key: str | None

    def _decision_instant(
        self, request: ProductRequest, effective_request: ProductRequest
    ) -> datetime:
        """When the answer is produced, as the class declares it.

        Read off the EFFECTIVE request, so a decision instant supplied by a
        default or narrowed by policy is the one that governs — the same
        authority chain every other argument travels.

        Falls back to ``request.asked_at`` when the class declares no such
        parameter, which keeps every existing deployment on the behavior it
        already had. The parse is the SDK's for `D-IMPL-302`'s reason: the
        party holding the declaration is the party that converts it.
        """
        if self.decision_instant_parameter is None:
            return request.asked_at
        declared = effective_request.parameters.get(self.decision_instant_parameter)
        if declared is None:
            return request.asked_at
        if isinstance(declared, datetime):
            return declared
        return datetime.fromisoformat(str(declared).replace("Z", "+00:00"))

    def __call__(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome:
        """Answer one question end to end, or return the refusal that stands.

        The ordering is the mechanism, and each step is where it is for a
        reason the composition would lose if it moved:

        1. **The address is checked first.** A call for a tenant or a class
           this resolver was never wired to serve is a mis-wiring, and it
           raises rather than being reported as a governed "no".
        2. **The question is RESOLVED before the graph is touched, and the
           resolution is what is checked.** The class's declared defaults are
           applied, the caller's values overlaid, the policy constraints in
           force at ``asked_at`` resolved with their provenance, the technical
           capabilities held against them — and only then is the *effective*
           request checked against the declared surface. The order is ruled
           (``D-IMPL-253`` Q8; ``D-IMPL-254`` — this is the **Authority**
           layer's place in Determination → Authority → Disclosure →
           Delivery), and it is the whole reason a default can mean something:
           a parameter the caller omitted reaches the closed-world comparison
           as the value the class declared, rather than as an omission. A
           question this class does not answer still costs nothing and still
           comes back with a reason rather than an approximation.
        3. **The graph is read at the boundary the question named.** The
           instant is ``request.asked_at`` — supplied by a caller at serve time
           and by replay at replay time, through this same code path, which is
           the entire reason nothing here reads a clock.
        4. **The operator registry is built from whatever the deployment
           declared**, then Π runs at L5.
        5. **The class registers**, minting the pins Gate 3 and the request
           surface are re-resolvable against.
        6. **The candidate claims its lineage from the declaration, never from
           the execution.** A claim copied out of the execution record is not a
           claim, it is a transcript — and Gate 2 then has two independently
           authored sets to hold to strict equality.
        7. **The gates run**, and their refusal is returned as a value. An
           ADMITTED product is then held to the applicable tolerance —
           default, caller or policy — and withheld by name if it is exceeded
           (:func:`~ccf.products.gates.refuse_over_tolerance`, ``24.6-L-05``).
           That step is deliberately after the gates and deliberately not one
           of them: a gate decides whether a product may exist, and this
           decides whether a product that does exist is delivered.
        8. **The record is built, then persisted, and only a completed append
           yields a delivery.** No branch here reaches a served product without
           a recorded decision, because :func:`~ccf.replay.serve.serve` has
           none to offer.
        9. **And every refusal is recorded the same way, first** (``24.6-07``;
           ``D-IMPL-253`` Q13). All three refusal branches — the resolution
           verdict, the gate refusal, the withheld fulfillment — go through
           :meth:`_record_refusal` into the one
           :class:`RefusalRecorderProtocol`, which appends through the **same**
           :class:`~ccf.replay.serve.ReplayWriter` over the same store and then
           hands back the shell with its own address on it. A shell that left
           this method has a recorded decision behind it, by construction and
           not by review: the append happens before the return, and a store
           failure propagates out of it with no branch reaching a returned
           shell.

        Registration is content-addressed, so a second call registers identical
        content to an identical version; the audit log carries both attempts,
        which is the Control Plane being the audit plane rather than a leak.

        Raises:
            ProductNotResolvable: the address names a tenant or a class this
                resolver does not serve, or the call carried no request.
            ccf.controlplane.registry.ControlPlaneMissing: a pin has
                disappeared since registration — a broken deployment, which
                this seam reports differently from a bad question.
            Exception: whatever the artifact store raises, deliberately
                uncaught. A failure to record is a failure to serve — and as of
                ``24.6-07`` a failure to *refuse*, on the same posture: a
                governed "no" released without its record is a determination
                with no audit, and ``D-IMPL-256`` refuses to make auditability
                contingent on the outcome.
        """
        declaration = self._declaration()
        if tenant != self.fabric.tenant_id:
            raise ProductNotResolvable(
                f"this resolver serves tenant {self.fabric.tenant_id!r} and was"
                f" called for {tenant!r}; the tenant is established by the"
                " calling surface and a resolver bound to a booted fabric"
                " cannot answer for another one"
            )
        if (product_class, version) != (
            declaration.schema_name,
            declaration.schema_version,
        ):
            raise ProductNotResolvable(
                f"this resolver serves {declaration.schema_name!r} at lane"
                f" {declaration.schema_version!r} and was called for"
                f" {product_class!r} at lane {version!r}; the declaration comes"
                f" from manifest key {self.product_class_key!r}"
            )
        if request is None:
            raise ProductNotResolvable(
                f"this resolver validates a question against"
                f" {declaration.schema_name!r}'s declared request surface and"
                " derives the decision instant from it, so a call carrying no"
                " request has nothing to validate and no instant to read; the"
                " seam admits `None` because a surface with no query segment"
                " must be able to say so, and such a surface needs a resolver"
                " that answers without one"
            )

        identity = RequestIdentity(
            product_id=product_class,
            product_version=version,
            parameters=request.parameters,
            temporal_boundary=request.asked_at,
        )

        # 24.7-07: is this class registered to serve the intent the request is
        # addressed with? An ADDRESSING verdict, and it precedes resolution for
        # the reason `_refuse_address` states for the lane check: judging the
        # parameters of a request for a class that does not serve its intent
        # is a confident verdict about the wrong question. Judged HERE, where
        # the declaration that carries `discovery` is in scope, and not inside
        # `refuse_request`, which never sees it — so direct validators that
        # hold no declaration never judge intent (D-09). Three states
        # (`D-IMPL-264` D-01 as amended, F-1 a): no declaration
        # (`NOT_DISCOVERABLE`) → unjudged, every existing deployment serves
        # as it did; declared and a member → serves; declared and not a member
        # — including a declared EMPTY set — → refused as data.
        violation = refuse_intent(request=request, discovery=declaration.discovery)
        if violation is not None:
            # No resolution ran, and the record says so positively rather than
            # by omission (D-09/D-10, P-2). What DID decide this outcome is the
            # class's declared intent set, so the deciding declaration IS
            # pinned — minted the way `class_source` mints it below, so the pin
            # resolves to the exact bytes that declared the set (`D-IMPL-264`
            # amendment 3 B-3 a, Dave: *"The refusal was decided by the class's
            # declared intent set, so replay should preserve the declaration
            # that actually governed the outcome"*). No request contract and no
            # constraint is pinned, because none was resolved against — which
            # is what lets replay read *request-contract pin + applicable
            # constraint pins* as the evidence that resolution ran, and never
            # a class-declaration pin (D-11 as narrowed by the same amendment).
            return self._record_refusal(
                envelope=envelope_for(violation, request=identity),
                execution=None,
                request=request,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(
                        key=self.product_class_key, version=content_hash(declaration)
                    ),
                ),
                resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
            )

        # THE DOOR, and this composition is the resolver standing at it. The
        # comparison the two shipped doors cannot make, because neither holds
        # the registered class it compares against (`D-IMPL-121`) — and, as of
        # `24.6-03`, the Control Plane read no door could make either.
        declared = self._request_contract(declaration)
        outcome = self.constraint_resolver.resolve(
            product_class=product_class,
            request=request,
            declared=declared,
            declared_source=ProvenanceSource(
                kind="artifact",
                identity=self.request_contract_key,
                # The version the registry assigns this content, minted the way
                # `ControlPlaneRegistry.register` mints it — a content address
                # (`D-IMPL-26`). So the pin this resolution records and the pin
                # `_register` mints below are the same pin by construction,
                # rather than two reads that could disagree.
                version=content_hash(declared),
            ),
            perspective=perspective,
            intent=request.intent,
            tenant=self.fabric.tenant_id,
            capabilities=self.capabilities,
            # 24.6-04: the product class's own declared characteristic reaches
            # the resolution as a DEFAULT and never as a ceiling (`D-IMPL-251`
            # C1=A). The key is omitted when the class declares nothing, so a
            # class with no opinion contributes no authority — rather than an
            # authority whose value happens to be `None`.
            class_defaults=self._class_defaults(declaration),
            class_source=ProvenanceSource(
                kind="artifact",
                identity=self.product_class_key,
                # The declaration's content address, minted the way
                # `ControlPlaneRegistry.register` mints one (`D-IMPL-26`), so
                # the pin recorded beside a defaulted value resolves to the
                # exact bytes that declared it.
                version=content_hash(declaration),
            ),
        )
        if outcome.refusal is not None:
            # No lineage: every one of these is reached while the effective
            # request is still being built, which is strictly before the graph
            # is touched. `envelope_for` refuses a lineage here, which is what
            # makes the assembly-boundary split structural.
            #
            # 24.6-07: and no execution, so dimension 1 says positively that
            # nothing was read. The bundle pin is the recorder's. What DID
            # govern this is the resolution that ran up to the refusal —
            # defaults applied, the constraints in force folded, capabilities
            # consulted — and that partial work is governed truth. It rides on
            # dimension 2 with the pins it was resolved from, exactly as a
            # completed resolution does on the two post-assembly branches
            # below (`D-IMPL-264` D-07, Dave: *"'It failed before producing
            # an effective request' must not erase what resolution already
            # established."*). The shell carries the same partial record as
            # its `provenance`, so the record and the shell cannot disagree.
            return self._record_refusal(
                envelope=envelope_for(
                    outcome.refusal,
                    request=identity,
                    policy_bindings=outcome.evidence.applied,
                    provenance=outcome.evidence,
                ),
                execution=None,
                request=request,
                perspective=perspective,
                policy_bindings=self._applied_bindings(outcome.evidence),
                resolution=outcome.evidence,
            )
        effective = outcome.evidence
        # The engine answers the EFFECTIVE question — defaults applied, policy
        # bounds in force. It is a SIBLING of the caller's request and never a
        # replacement: `identity.parameters` and the request that lands in
        # replay dimension 5 both keep what the caller supplied, so a refusal
        # can still say "you asked for X and policy P bounds you to Y", and the
        # resolution that turned one into the other is dimension 2's
        # (`D-IMPL-253` Q1 — *"do not collapse authority after resolution"*).
        effective_request = request.model_copy(
            update={"parameters": dict(effective.values())}
        )

        # `D-IMPL-343` R-4: THE DECLARED ACQUISITION SEAM, HERE AND ONLY HERE.
        # The question is resolved (above) and the graph is not yet read
        # (below), so what the deployment reads its sources at is the value
        # governance resolved — the one derivation — and a refused request
        # never reaches this line. The seam is the composition root's: it
        # reads and it ingests through L2's one writer; this resolver hands
        # it a request and holds no handle to anything it writes.
        if self.acquisition is not None:
            try:
                self.acquisition(request=effective_request, perspective=perspective)
            except GovernedRefusalRaised as raised:
                # `D-IMPL-304`: a governed determination the seam HELD and could
                # not return — recorded through this composition's ONE minting
                # seam with the resolution THIS resolver established, and
                # returned as data. Only this type; any other exception the
                # seam raises propagates exactly as before.
                return self._refuse_raised_at_acquisition(
                    raised, request=request, identity=identity,
                    perspective=perspective, effective=effective,
                )

        view = self.fabric.handle.reader.as_of(
            tenant_id=self.fabric.tenant_id, at=request.asked_at
        )
        operators = build_operator_registry(
            parameters=self._operator_parameters(effective_request),
            view=view,
            pins=self.fabric.pins,
            policy_bundle_key=self.policy_bundle_key,
            # `24.11-02b` / `24.10-F-06` (`D-IMPL-292`). No index version
            # travels here, and its ABSENCE is the repair rather than an
            # omission. `24.11-02` passed one from a field on this class,
            # which fixed the propagation and left a decision-affecting
            # semantic value in ungoverned deployment hands. It is now
            # declared on the similarity artifact — one of the very artifacts
            # `_operator_parameters()` returns on the line above — so the
            # builder reads the corpus identity off the same declaration it
            # already reads the corpus map off, and this composition states
            # no opinion about a value it does not own.
        )
        required = tuple(declaration.required_operator_keys)
        registered = self._register(declaration)
        policy_version = self.fabric.pins.version_for(self.policy_bundle_key)
        own_lineage = ProductLineage(
            operators_invoked=frozenset(required),
            policy_bundle_versions=frozenset({policy_version}),
            graph_snapshot_at=request.asked_at,
        )
        # --- `D-IMPL-339`: ACQUIRE AND ADMIT CHILDREN ONCE, BEFORE THE PLAN ----
        #
        # The approved order: child-independent request / policy / declaration
        # checks (all above) -> acquire and admit children once -> the
        # read-only child-contract view -> the parent's plan -> the parent's
        # own assessment -> compose using the SAME acquired outcomes -> the
        # existing gates, tolerance, delivery / refusal and replay. Only the
        # acquisition half moves here; `compose_children` runs below, after
        # the assessment it needs, over exactly these `outcomes`.
        #
        # `registered`, `policy_version` and `own_lineage` moved up with it:
        # none reads the projection. What stays below is what does —
        # `assessed`, `decided_at` and the composition laws.
        composed: CompositionOutcome | None = None
        outcomes: Mapping[str, object] | None = None
        children: ChildContractView | None = None
        invocation = ""
        if registered.requires:
            # One governed question, one invocation identity — derived from the
            # request so it is stable under replay and cannot be chosen per
            # child (F8: invocation-bound, and the binding is to THIS one).
            invocation = f"composition://{content_hash(request)}"
            # Read ONCE per composition. Two children admitted against two
            # readings of a clock would be judged in two windows, and the
            # rows would disagree about when the composition admitted them.
            admitted_at = self.admission_clock()
            if self.composite_children is None:
                composed = CompositionOutcome(
                    factors=None,
                    resolutions=(),
                    refusal=ChildAdmissionRefusal(
                        gate=GATE_CHILD_ADMISSION,
                        detail=(
                            f"class {registered.schema_name!r} declares"
                            f" {len(registered.requires)} child requirement(s)"
                            " and this deployment wired no composite child"
                            " resolver, so they could not be satisfied."
                            " Refused rather than served without them: a"
                            " declared requirement execution ignores is the"
                            " defect this block exists to close"
                        ),
                        product_class=registered.schema_name,
                        reason="no-producing-skill",
                    ),
                )
            else:
                # `D-IMPL-340`. A resolver that declares it takes the composite's
                # EFFECTIVE request — defaults applied, policy narrowed, the same
                # authority chain every argument travels — receives it; every other
                # resolver takes the call it always took. Structural `isinstance` on
                # a capability Protocol, on the `CompositePlanFactoryProtocol`
                # precedent: no defaulted keyword, no `TypeError` probing.
                if isinstance(
                    self.composite_children, RequestAwareChildResolverProtocol
                ):
                    outcomes = self.composite_children.resolve_for(
                        requirements=registered.requires,
                        asked_at=request.asked_at,
                        # `O3`: the trusted runtime clock, NOT `decided_at`.
                        admitted_at=admitted_at,
                        composition_invocation=invocation,
                        # `D-IMPL-336` Amendment 5: peering admission extends the
                        # consumer's lineage by set-union.
                        consumer_lineage=own_lineage,
                        request=effective_request,
                    )
                else:
                    outcomes = self.composite_children(
                        requirements=registered.requires,
                        asked_at=request.asked_at,
                        # `O3`: the trusted runtime clock, NOT `decided_at`.
                        admitted_at=admitted_at,
                        composition_invocation=invocation,
                        # `D-IMPL-336` Amendment 5: peering admission extends the
                        # consumer's lineage by set-union.
                        consumer_lineage=own_lineage,
                    )
                # The per-requirement walk — provenance, slot / instant /
                # invocation re-binding, the refusal branches — runs HERE,
                # before any child-dependent computation, and the view is
                # derived only from what passed it (`D-IMPL-339` Q1, Q2).
                resolved = resolve_child_outcomes(
                    requirements=registered.requires,
                    outcomes=outcomes,
                    asked_at=request.asked_at,
                    composition_invocation=invocation,
                )
                # `D-IMPL-344`: RETENTION FOLLOWS ADMISSION, NOT COMPOSITION
                # SUCCESS. Every contract this walk admitted is filed by content
                # address HERE — before the blocking split — so a partially
                # admitted set (one child admitted, a required sibling refused
                # or unreachable, the parent's plan never run) keeps the bytes
                # its refusal record's row names. Read off `resolved.admitted`
                # directly: the view below refuses a blocked resolution by
                # design (`D-IMPL-339` Q2), and a view over a set known not to
                # compose was never the prerequisite for keeping what WAS
                # admitted. Replay rebuilds from what was consumed — never from
                # a provider call, a latest-version lookup or a live closure —
                # on every exit, not only the served one. A store that cannot
                # file raises here, before any record is minted (§3 of the
                # design): a determination whose evidence was not kept is not
                # recorded as though it had been.
                self._retain_child_contracts(
                    child.contract for child in resolved.admitted
                )
                if resolved.blocking:
                    composed = CompositionOutcome(
                        factors=None,
                        resolutions=resolved.rows,
                        refusal=resolved.refusal,
                    )
                else:
                    children = child_contract_view(resolved)
            if composed is not None and composed.refusal is not None:
                # A KNOWN BLOCKING OUTCOME BEFORE PROJECTION (`D-IMPL-339` Q2):
                # a required child absent, an invoked child refused or rejected
                # at admission, or no resolver wired. Child-dependent
                # computation does not run. Recorded through the same seam a
                # pre-assembly refusal takes — no execution, no lineage, and
                # dimension 1 says positively that nothing was read — with
                # every child row the walk produced (`D-IMPL-338`).
                return self._record_refusal(
                    envelope=envelope_for(
                        composed.refusal,
                        request=identity,
                        policy_bindings=effective.applied,
                        provenance=effective,
                    ),
                    execution=None,
                    request=request,
                    perspective=perspective,
                    policy_bindings=self._applied_bindings(effective),
                    resolution=effective,
                    child_resolutions=composed.resolutions,
                )

        # `D-IMPL-300`: the plan is a NAMED LOCAL so the binder has somewhere to
        # stand. `D-IMPL-86`'s correction of 2026-08-05 puts the check between
        # plan construction and `execute`, and on this path that moment exists
        # ONLY here — `plan_factory` is invoked by the resolver, so no adopter
        # code sits between the two. Found by cp-05's canonical adoption: its
        # hand-composed spine called the binder, and the migrated program had
        # nowhere legitimate to.
        # `D-IMPL-339`: a composite-capable factory receives the admitted
        # children's contracts; every other factory is called EXACTLY as it
        # always was. The capability is declared structurally, never inferred
        # from a signature, and never probed with a TypeError-and-retry.
        if children is not None and isinstance(self.plan_factory, CompositePlanFactoryProtocol):
            plan = self.plan_factory.build_with_children(
                required=required, request=effective_request, children=children
            )
        else:
            plan = self.plan_factory(required=required, request=effective_request)
        # The product class's `required_operator_keys` and the plan's own
        # `required_operators()` are two separately authored documents (design
        # E2). Gate 2 below compares the declaration against what the engine
        # RESOLVED, which is a different and later invariant: it catches the
        # divergence after a product has already been assembled from a set the
        # deployment's own claim contradicts. Refusing here is what keeps that
        # assembly from happening at all.
        refuse_operator_set_divergence(declared=declaration, plan=plan)
        execution = ProjectionEngine(
            reader=self.fabric.handle.reader, registry=operators
        ).execute(
            plan=plan,
            perspective=perspective,
            tenant_id=self.fabric.tenant_id,
            temporal_boundary=request.asked_at,
            # `24.11-01` / `24.10-F-07` (`D-IMPL-111` limb (a), Dave,
            # 2026-08-11): *the request seeds the traversal*. Absent this
            # argument the canonical path executed with `seeds=None` while
            # `ccf.replay.engine` replayed with
            # `seeds=request_seeds(path.request)`, so two questions about two
            # different subjects compiled to the SAME graph query and pinned
            # identically in dimension 5 — `DI-15.5-07` exactly, reproduced on
            # the canonical path after limb (a) had already closed it on the
            # hand-built one.
            #
            # **`request`, not `effective_request`, and the reason is the
            # invariant rather than a preference.** `build_replay_record` below
            # is handed `request=request`, which `ccf.replay.record` writes
            # verbatim to `ContentGenerationPath.request`, which
            # `ccf.replay.engine` reads back as `request_seeds(path.request)`.
            # Seeding from the CALLER's request is therefore the SAME function
            # applied to the SAME object on both paths — the "one reading, used
            # on both paths" `request_seeds` exists to be. `effective_request`
            # is a sibling that today carries an identical `subject` (it differs
            # only in `parameters`), so it would agree by coincidence and not by
            # construction: it is a SECOND derivation, and a second derivation
            # is precisely the drift that would replay a different question
            # under this decision's identifier.
            seeds=request_seeds(request),
        )

        # `24.10-F-09` / `D-IMPL-308`. Bound ONCE and read FOUR times below —
        # the product's expiry, the gate instant, the record's `recorded_at`
        # and, as of `D-IMPL-343` R-3c, the instant an instant-aware scorer
        # measures freshness as of — are four statements about the same
        # moment, and deriving them separately is how they drift apart. Hoisted
        # above the scorer call for that fourth reader; it reads only the two
        # requests, so nothing about the value moved.
        decided_at = self._decision_instant(request, effective_request)

        # `24.11-03` / `24.10-F-08`: hoisted out of the constructor because two
        # members are now derived from it — the assessment itself and the
        # obligation bound to the state it landed in — and scoring twice could
        # put a product's debt and its obligation on different sides of a band.
        # `D-IMPL-343` R-3c: an instant-aware scorer is asked FIRST and is
        # handed the decision instant and the admitted children (None for a
        # non-composite) — the widest seam, so a scorer declaring it is asked
        # through it. `D-IMPL-339`: a child-aware scorer receives the same view
        # the plan did, so the parent's own child-dependent `C` / `S` reach its
        # assessment per request; every other scorer is asked as before.
        if isinstance(self.debt_scorer, InstantAwareDebtScorerProtocol):
            assessed = self.debt_scorer.score_at(
                view=execution.view,
                evidence=ExecutionEvidence.of(execution),
                decided_at=decided_at,
                children=children,
            )
        elif children is not None and isinstance(self.debt_scorer, ChildAwareDebtScorerProtocol):
            assessed = self.debt_scorer.score_with_children(
                view=execution.view,
                evidence=ExecutionEvidence.of(execution),
                children=children,
            )
        else:
            assessed = self.debt_scorer(
                view=execution.view, evidence=ExecutionEvidence.of(execution)
            )

        # --- composite assembly (`D-IMPL-336` Amendment 3, F0) -------------
        #
        # THE DECLARATION IS READ FROM THE REGISTERED CLASS. Until this block
        # existed the whole composite surface had no caller: a class could
        # declare `requires` and be served with no composition, no admission
        # and no replay rows — `D-IMPL-324`'s "declaration is not a door",
        # applied to an entire feature.
        #
        # `composed` stays None for every non-composite product, which is
        # every product shipped before this, and everything below is inert.
        #
        # `D-IMPL-339` split where a composition refusal is recorded. A KNOWN
        # BLOCKING outcome — a required child absent, an invoked child refused
        # or rejected at admission, no resolver wired — returned ABOVE, before
        # the plan, through the pre-assembly seam. What can still refuse HERE
        # is the composition of an admitted set — the mixing law — and that
        # refusal is carried, as before, to the same post-gate path a gate
        # refusal takes, so it and a TTL refusal are recorded by one mechanism.
        # --- `D-IMPL-339`: COMPOSE USING THE SAME ACQUIRED OUTCOMES ------------
        # `outcomes` is the one acquisition above; content (the view the plan
        # received) and governance (the laws applied here) refer to the same
        # admitted products. Nothing is re-acquired, looked up or rebuilt.
        # --- `D-IMPL-341`: THE TTL ANCHOR, RESOLVED ONCE FOR BOTH BRANCHES ----
        # The decision instant for a `from_decision` class; for a
        # `from_entity_freshness` class the freshest `valid-from` leading edge
        # over the SAME observations the freshness factor just scored — the
        # deployment's declared decay clock, read once more. Nothing here is
        # minted, read off a payload, or defaulted: a set with no usable
        # instant is gate 3's own refusal (R-3), recorded below with the
        # child rows a composite already resolved.
        anchor = resolve_ttl_anchor(
            ttl_anchor=registered.ttl_anchor,
            view=execution.view,
            table=self._half_life_table(),
            decided_at=decided_at,
            product_class=registered.schema_name,
        )
        anchored_at = (
            anchor.anchor_at if isinstance(anchor, TTLAnchorResolution) else decided_at
        )
        if outcomes is not None:
            composed = compose_children(
                own_factors=assessed.factors,
                requirements=registered.requires,
                outcomes=outcomes,
                asked_at=request.asked_at,
                composition_invocation=invocation,
                own_lineage=own_lineage,
                max_ttl=MaxTTL(seconds=self.product_ttl_seconds),
                # `R6` — THE TTL ANCHOR IS `decided_at`, NOT `asked_at`.
                # The first version passed the reconstruction instant here
                # while the non-composite branch below anchored at the
                # decision instant, silently reverting `D-IMPL-308` for
                # composites only. Measured consequence: a class with a
                # declared decision instant served a SHORTER window as a
                # composite than as a plain product, and the two landed on
                # the same content address — two governed answers, one
                # identity. The anchor is the same instant on both
                # branches now, which is what `D-IMPL-308` says it is:
                # the TTL runs from when the answer was PRODUCED.
                ttl_anchor_at=anchored_at,
                validity_floors=registered.constituent_validity_floors,
            )
            if composed is not None and composed.factors is not None:
                # `24.11-03`'s hazard, respected: the composed factors replace
                # the parent's own BEFORE `obligation_in_force` is derived
                # below, so a composite's reported debt and its obligation
                # cannot land on different sides of a routing band.
                #
                # `R2` — AND THE SIGNAL IS RE-DERIVED, not carried forward.
                # The first version of this block kept `signal=assessed.signal`
                # while replacing the debt and the factors, so a composite
                # whose composed D_c crossed fail-closed was served with
                # `signal=ok` and the routine obligation. The signal is the
                # thing the band is read from, so carrying the parent's own
                # made the comment above it false: re-deriving it from the
                # COMPOSED factors under the same profile is what makes the
                # claim true.
                assessed = self._reassess(composed.factors, fallback=assessed)

        # `D-IMPL-338`. THE CHILD EVIDENCE IS BOUND ONCE, HERE, AND READ BY
        # EVERY EXIT BELOW — the served record and all four post-acquisition
        # refusals. `CMP-R-01` widened the recorder seam and threaded the rows
        # through the served path and the COMPOSITION refusal only; the three
        # refusals that can follow a successful composition (universal gate,
        # declared product gate, tolerance) each called `_record_refusal`
        # without them, so a composite refused for excess INHERITED debt wrote
        # a record that did not say which children it inherited it from.
        # Enumerated rather than patched at the first omission found: every
        # refusal exit below this line passes `child_rows`,
        # and the two refusals ABOVE the composite block pass nothing — no
        # child was considered there, and `()` is the true claim rather than
        # an invented outcome.
        child_rows: tuple[ChildResolution, ...] = (
            composed.resolutions if composed is not None else ()
        )
        if isinstance(anchor, TTLAnchorRefusal):
            return self._record_refusal(
                envelope=envelope_for(
                    anchor,
                    request=identity,
                    policy_bindings=effective.applied,
                    provenance=effective,
                ),
                execution=execution,
                request=request,
                perspective=perspective,
                policy_bindings=self._applied_bindings(effective),
                resolution=effective,
                child_resolutions=child_rows,
            )

        candidate = ContextProductContract(
            schema_name=registered.schema_name,
            schema_version=registered.schema_version,
            plan_id=execution.plan_id,
            tenant_id=self.fabric.tenant_id,
            # THE BOUNDARY STAYS `asked_at` AND THE EXPIRY DOES NOT.
            # `temporal_boundary` is when the graph was observed; the TTL runs
            # from when the answer was PRODUCED (`24.10-F-09`, `D-IMPL-308`).
            # They are equal whenever a class declares no decision instant.
            temporal_boundary=request.asked_at,
            # `D-IMPL-336` F14: a composite's expiry is FLOORED by its
            # stalest admitted constituent, so it can never be labelled
            # fresher than the child it depends on. Non-composites keep the
            # declared window exactly as before.
            expires_at=(
                composed.expires_at
                if composed is not None and composed.expires_at is not None
                else anchored_at + timedelta(seconds=self.product_ttl_seconds)
            ),
            ttl_anchor=registered.ttl_anchor,
            # `D-IMPL-341` R-2: every new product states the instant its
            # anchor resolved to, on every class.
            ttl_anchor_at=anchor.anchor_at,
            # `D-IMPL-336` F14: and its lineage is the N-way set-union over
            # every admitted child's, so each constituent's provenance stays
            # resolvable from the composite.
            #
            # `D-IMPL-309`: the engine's store head is NOT sealed here. It is
            # execution provenance and it is recorded in replay dimension 1
            # from `execution.store_snapshot_pin`, so an ambient ledger
            # advancing between two runs of one governed question cannot mint
            # a second product identity (`MOD-05`).
            lineage=(
                composed.lineage
                if composed is not None and composed.lineage is not None
                else own_lineage
            ),
            payload=execution.projection.payload,
            # `24.10-F-08` / `D-IMPL-308`: the window this deployment DECLARED,
            # carried rather than dropped. Inside the content address, so a
            # deployment cannot add it afterwards.
            source_refresh_recency=self.source_refresh_recency,
            # 24.6-05 (`24.6-L-06`, `D-IMPL-255` (2)): the scorer is told what
            # the execution observed about its own search, so that D_c is
            # derived from evidence rather than from how many rows came back.
            debt=assessed,
            # `24.11-03` / `24.10-F-08`: the obligation this deployment's own
            # profile binds to the state `assessed` landed in. Derived from
            # THAT assessment rather than from a second scoring call — the
            # product must not be able to carry an obligation bound to a
            # routing state other than the one it reports.
            obligation_in_force=self._obligation_in_force(assessed.signal),
            # 24.6-05 (`D-IMPL-242` amendment 1, `D-IMPL-253` Q11/Q12): an
            # operator that RAN and returned nothing computed something, so
            # its emptiness is served as a finding rather than refused on
            # cardinality. `None` when no operator returned empty — the claim
            # every product made before this field existed.
            computed_empty=ComputedEmptyFinding.of(
                execution,
                emptiness=emptiness_of(ExecutionEvidence.of(execution)),
            ),
        )

        # `R4`, the other half. Widening Gate 2's operand for composites opens
        # a hole unless the parent's OWN declaration is held to its OWN
        # execution first: if the engine ran operator X while the class
        # declared only Y, and a child happens to invoke X, then X is on both
        # sides of the widened comparison and the parent's drift is masked.
        #
        # So the two halves are checked separately and both strictly. This one
        # is the pre-composition question — "did THIS fabric run what THIS
        # class declared" — and it is exactly what Gate 2 asked before
        # composites existed, which is why the refusal is the same type with
        # the same gate identifier and reaches the caller identically.
        #
        # Proven by sabotage: `test_r4_the_union_CANNOT_mask_the_parents_own_
        # declaration_drifting` perturbs the engine's set and gives the child
        # precisely the drifted operator.
        own_declared = frozenset(required)
        drifted: GateRefusal | None = (
            LineageMismatchRefusal(
                gate=GATE_LINEAGE_EQUALITY,
                detail=(
                    f"composite {registered.schema_name!r} declares operators "
                    f"{sorted(own_declared)} but its own engine resolved "
                    f"{sorted(execution.operators_invoked)}; a composite's "
                    "admitted children widen what the composition resolved, "
                    "never what the parent itself declared, so this half stays "
                    "strict in both directions (INV-CH7-47, D-IMPL-336 R4)"
                ),
                declared=own_declared,
                resolved=execution.operators_invoked,
            )
            if composed is not None and own_declared != execution.operators_invoked
            else None
        )

        gated: ServableProduct | GateRefusal
        if drifted is not None:
            gated = drifted
        else:
            gated = run_gates(
                candidate,
                # `R4` — THE COMPOSITE'S ENGINE-RESOLVED SET INCLUDES ITS ADMITTED
                # CHILDREN'S OPERATORS. **PROPOSED reading of INV-CH7-47, pending
                # Dave's ruling at `D-IMPL-336` checkpoint 1.**
                #
                # Gate 2 compares the candidate's declared operators against what
                # the engine resolved, by strict equality in both directions. A
                # composite's lineage is the `D-IMPL-31` N-way union, which
                # includes every admitted child's operators — and this fabric's
                # engine never ran those, because the child did. So before this
                # line a composite could serve only while every child invoked a
                # SUBSET of the parent's own operators, which a real child of a
                # different class never does: it exists to answer a different
                # question. Measured, with the control, at
                # `test_r4_a_composite_serves_with_a_child_that_ran_ITS_OWN_operators`.
                #
                # The two obvious alternatives each break a standing ruling — a
                # subset check abandons INV-CH7-47's strictness, and declaring
                # only the parent's own operators abandons `D-IMPL-31`'s union —
                # so the operand widens instead, and Gate 2 itself is untouched.
                # Each child's set is engine-resolved evidence: it passed that
                # child's own Gate 2 at its own delivery.
                #
                # Strictly additive for every non-composite: `composed` is None,
                # the union is with `frozenset()`, and the operand is the value it
                # has always been.
                engine_resolved=execution.operators_invoked
                | (composed.admitted_operators if composed is not None else frozenset()),
                # The TTL gate asks whether this product expires within bounds OF
                # THE MOMENT IT WAS DECIDED, which is the instant its expiry runs
                # from (`D-IMPL-308`).
                now=decided_at,
                registry=self.control_plane,
                product_class=registered,
                source_attestation=execution.source_attestation,
                # `D-IMPL-334`: the entities this execution actually read — the same
                # value replay dimension 1 records. The gate asks whether any of
                # them moved after the snapshot this product was built at.
                touched_entities=execution.touched_entities(),
            )
        # 24.6-03/24.6-07: every source the resolution consulted, by exact
        # `(key, version)`. Derived ONCE and shared by the served record and
        # every refusal record below — two derivations would let a refused
        # decision and a fulfilled one disagree about what governed them.
        applied = self._applied_bindings(effective)
        # 24.6-07: what the fabric is PERMITTED to show of the search behind a
        # post-assembly refusal. The candidate's own facts, read off the same
        # execution the served product would have been recorded from — never
        # re-derived, so a refusal shell cannot describe a different search
        # from the one that ran.
        evidence = RefusalEvidence(
            operators_invoked=execution.operators_invoked,
            plan_id=execution.plan_id,
            debt=candidate.debt,
            computed_empty=candidate.computed_empty,
        )
        # `D-IMPL-336` Amendment 3, F0: a composition refusal is recorded by
        # the SAME mechanism a gate refusal is, and BEFORE the universal gates
        # report on a candidate whose children never arrived. Placed here
        # rather than at the composition itself so one refusal path serves
        # both, and so the refusal travels with the candidate's own lineage
        # and evidence exactly as a TTL refusal does.
        if composed is not None and composed.refusal is not None:
            return self._record_refusal(
                # `CMP-R-01` CLOSED. `compose_children` builds a row for every
                # requirement and this path used to drop them, because the
                # recorder is a public seam that had no parameter for them —
                # so the one case where a reader most needs to know WHICH child
                # failed was the case the record did not say. The seam was
                # widened under Amendment 5 §5, with the surface recorded
                # first; the rows travel now.
                envelope=envelope_for(
                    composed.refusal,
                    request=identity,
                    pre_assembly_lineage=candidate.lineage,
                    policy_bindings=effective.applied,
                    evidence=evidence,
                    provenance=effective,
                ),
                execution=execution,
                request=request,
                perspective=perspective,
                policy_bindings=applied,
                resolution=effective,
                child_resolutions=child_rows,
            )

        if not isinstance(gated, ServableProduct):
            # A refusal is a value, and it travels with the lineage the
            # candidate claimed — a gate refusal has a candidate behind it, so
            # saying it has no lineage would be a different and false claim.
            return self._record_refusal(
                envelope=envelope_for(
                    gated,
                    request=identity,
                    pre_assembly_lineage=candidate.lineage,
                    policy_bindings=effective.applied,
                    evidence=evidence,
                    provenance=effective,
                ),
                execution=execution,
                request=request,
                perspective=perspective,
                policy_bindings=applied,
                resolution=effective,
                # `D-IMPL-338`: the children this candidate was composed from.
                child_resolutions=child_rows,
            )

        # `24.10-02` / `R-11` (`D-IMPL-282` option 1a), and the placement is
        # the ruling: *"It executes after candidate construction and before
        # fitness/fulfillment."* The universal gates have ADMITTED this
        # product, so there is something to hold an invariant against; the
        # tolerance comparison below has not run, so a product that is WRONG
        # is reported as wrong rather than as unfit. Two different questions,
        # and the order between them is what keeps them two.
        #
        # The identity is read from the Control Plane and stamped here. The
        # deployment's callable returns a detail string and nothing else, so a
        # gate cannot claim to be a different gate than the one its class
        # declared — which is what makes `D-14`'s "which gate produced the
        # refusal" a fact rather than a claim the failing code made about
        # itself.
        if self.product_gate is not None:
            gate_violation = self.product_gate(
                candidate=gated.product, evidence=ExecutionEvidence.of(execution)
            )
            if gate_violation:
                declared_gate = self._declaration().declared_product_gate
                return self._record_refusal(
                    # `evidence`, `applied` and `effective` are the values
                    # derived ONCE above the gate branch and shared by every
                    # post-assembly refusal. Deriving them again here would let
                    # a refused determination and a fulfilled one disagree
                    # about what governed them, which is the comment already
                    # standing at that site.
                    envelope=envelope_for(
                        ProductInvariantRefusal(
                            gate=declared_gate.gate_id,
                            gate_version=declared_gate.gate_version,
                            detail=gate_violation,
                        ),
                        request=identity,
                        pre_assembly_lineage=candidate.lineage,
                        policy_bindings=effective.applied,
                        evidence=evidence,
                        provenance=effective,
                    ),
                    execution=execution,
                    request=request,
                    perspective=perspective,
                    policy_bindings=applied,
                    resolution=effective,
                    # `D-IMPL-338`: the children this candidate was composed from.
                    child_resolutions=child_rows,
                )

        # 24.6-04, the delivery boundary: the gates ADMITTED this product, and
        # only now is it held to the one applicable tolerance — the class's
        # default, the caller's own value or a policy's, folded exactly once
        # upstream by the Authority layer with the authority that set it
        # recorded (`D-IMPL-254`). Nothing is folded here, because a second
        # fold is the scalar collapse this phase removed and the place a class
        # preference could re-acquire the power `D-IMPL-251` C1 took from it.
        # The product was constructible; what is withheld is fulfillment.
        # Nothing about the principal or the perspective reaches this
        # comparison (`D-IMPL-105`): D_c is entitlement-neutral, as assessed.
        withheld = refuse_over_tolerance(
            gated, tolerance=effective.parameter(DEBT_TOLERANCE_PARAMETER)
        )
        if withheld is not None:
            return self._record_refusal(
                envelope=envelope_for(
                    withheld,
                    request=identity,
                    pre_assembly_lineage=candidate.lineage,
                    policy_bindings=effective.applied,
                    evidence=evidence,
                    provenance=effective,
                ),
                execution=execution,
                request=request,
                perspective=perspective,
                policy_bindings=applied,
                resolution=effective,
                # `D-IMPL-338`: a tolerance refusal is the case that most needs
                # its children named — the debt it refused on is inherited.
                child_resolutions=child_rows,
            )

        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key=self.policy_bundle_key, version=policy_version),
                *applied,
                # `D-IMPL-341` R-5: an evidence-anchored serve pins the λ_c
                # table it anchored under, so replay re-derives the anchor
                # under the same declarations, never today's.
                *self._ttl_anchor_pins(anchor),
            ),
            assembly_mode=registered.assembly_mode,
            # WHEN THE DECISION WAS TAKEN, not when the graph was read
            # (`D-IMPL-308`). Dimension 5 already carries `asked_at` on the
            # request it holds, so the record says both rather than one twice.
            recorded_at=decided_at,
            request=request,
            # 24.6-07: the assembler in force, on the served path and on every
            # refusal path alike (`D-IMPL-253` Q16). This resolver holds no
            # `ContextAssemblerProtocol` — it composes assemble → gate → serve
            # itself — so it passes `None` and lets dimension 4's
            # `NO_ASSEMBLER` sentinel say exactly that, rather than inventing
            # an identity for a collaborator that does not exist. A resolver
            # that DOES hold one wires its own id and version here.
            assembler_id=self._assembler_id(),
            assembler_version=self._assembler_version(),
            # `D-IMPL-336` Amendment 3, F0 — the per-child rows, GENERATED
            # FROM EXECUTION. Empty for every non-composite decision, which is
            # what keeps those records byte-identical to the ones written
            # before this surface existed.
            child_resolutions=child_rows,
            # 24.6-03: what was resolved, and on whose authority — dimension 2,
            # beside the versions it was resolved from (`D-IMPL-254`).
            resolution=effective,
        )
        return serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=self.artifact_store, artifact_class=self.replay_record_class
            ),
            query_pin_writer=QueryPinWriter(
                store=self.artifact_store, artifact_class=self.query_pin_class
            ),
            executed_queries=execution.executed_queries,
        )

    def _retain_child_contracts(
        self, contracts: Iterable[ContextProductContract]
    ) -> None:
        """File each admitted child's contract by content address (`D-IMPL-339`).

        Nothing else retains a served product's bytes — the writer files the
        record and the query pins, never the product — so the parent's
        child-contract view would be unrebuildable after the fact. Filed under
        :data:`~ccf.products.composite.ADMITTED_CHILD_CONTRACT_CLASS` on this
        fabric's own store, idempotently: the address IS the identity, and a
        second composition consuming the same child files nothing twice.

        Takes the admitted **contracts** and not a
        :class:`~ccf.products.composite.ChildContractView` (`D-IMPL-344`): the
        view exists only for a composition that reached no refusal, while
        retention follows admission on every exit. The caller hands over
        exactly what :func:`~ccf.products.composite.resolve_child_outcomes`
        admitted, so nothing that was refused, rejected, absent or unreachable
        can arrive here.

        The store's address for the bytes must equal
        :func:`~ccf.contracts.canonical.content_hash` of the contract — the
        same address the child row records — or replay could not resolve the
        row to the bytes. A store that hashed differently is refused here,
        loudly, rather than discovered at replay.
        """
        for contract in contracts:
            address = content_hash(contract)
            if self.artifact_store.exists(content_address=address):
                continue
            filed = self.artifact_store.put(
                tenant_id=self.fabric.tenant_id,
                artifact_class=ADMITTED_CHILD_CONTRACT_CLASS,
                name=address,
                artifact=contract,
            )
            if filed.content_address != address:
                raise RuntimeError(
                    "the artifact store filed an admitted child contract at"
                    f" {filed.content_address!r} but its content address is"
                    f" {address!r}; replay resolves child rows by content"
                    " address and this store would break that (D-IMPL-339)"
                )

    # --- the one minting seam ----------------------------------------------

    def _refuse_raised_at_acquisition(
        self,
        raised: GovernedRefusalRaised,
        *,
        request: ProductRequest,
        identity: RequestIdentity,
        perspective: Perspective,
        effective: EffectiveRequest,
    ) -> RefusalEnvelope:
        """The typed handoff caught at the acquisition seam (`D-IMPL-304`).

        The resolution completed before the seam ran — that is the seam's
        contract — so dimension 2 carries THIS resolver's evidence, which is
        the truth about what governance resolved, and the raiser's stated
        state is held to it: :data:`~ccf.products.refusal.RESOLVED_BY_THE_RESOLVER`
        or the same evidence are consistent; an explicit not-applicable marker
        is a contradiction (resolution DID run) and is refused as the
        programming error it is rather than recorded as a false statement.
        An envelope the raiser had already recorded passes through; a bare
        refusal is enveloped with the request identity and the resolution
        provenance exactly as the resolver's own pre-view refusals are.
        """
        if isinstance(raised.resolution, ResolutionNotApplicable):
            raise TypeError(
                "a GovernedRefusalRaised at the acquisition seam states"
                " ResolutionNotApplicable, but this resolver resolved the effective"
                " request before calling the seam; state RESOLVED_BY_THE_RESOLVER"
                " or the resolver's own evidence (D-IMPL-304)"
            ) from raised
        if isinstance(raised.refusal, RefusalEnvelope):
            if raised.refusal.replay_reference != NO_REPLAY_REFERENCE:
                return raised.refusal
            envelope = raised.refusal
        else:
            envelope = envelope_for(
                raised.refusal,
                request=identity,
                policy_bindings=effective.applied,
                provenance=effective,
            )
        return self._record_refusal(
            envelope=envelope,
            execution=None,
            request=request,
            perspective=perspective,
            policy_bindings=self._applied_bindings(effective),
            resolution=effective,
        )

    def _record_refusal(
        self,
        *,
        envelope: RefusalEnvelope,
        execution: ExecutionResult | None,
        request: ProductRequest,
        perspective: Perspective,
        policy_bindings: tuple[PolicyBinding, ...] = (),
        resolution: EffectiveRequest | ResolutionNotApplicable,
        child_resolutions: tuple[ChildResolution, ...] = (),
    ) -> RefusalEnvelope:
        """Mint this refusal's decision record, then return the addressed shell.

        ``24.6-07``; ``D-IMPL-253`` Q13. A **thin** call into
        :attr:`refusal_recorder` and nothing else — every governed refusal this
        composition produces goes through here, and nothing in ``src/`` calls
        :func:`~ccf.replay.serve.record_refusal` except the recorder itself.

        The instant is ``request.asked_at`` for the reason nothing in this
        module reads a clock: the caller supplies it at serve time and replay
        supplies it at replay time, through this same code path.

        ``resolution`` is required with no default (24.7-04): every branch
        that reaches here ran the resolution step and passes what it
        established — complete or partial (D-07) — and this thin layer
        never substitutes a marker for what a branch did not say. ``D-IMPL-264`` amendment 1 (F-3 a), Dave verbatim: *"Any API that
        constructs or delegates construction of a replay record must require
        an explicit resolution state: effective/partial resolution or explicit
        not-applicable marker. No intermediate layer may manufacture the
        marker from omission."*

        Raises:
            Exception: whatever the artifact store raises, deliberately
                uncaught. *A failure to record is a failure to serve* — and
                24.6-07 extends that sentence to a governed "no": a refusal
                released without its record is a determination with no audit,
                which is the repudiation `D-IMPL-256` refuses to make
                contingent on the outcome.
        """
        return self.refusal_recorder.record(
            envelope,
            perspective=perspective,
            recorded_at=request.asked_at,
            request=request,
            execution=execution,
            policy_bindings=policy_bindings,
            assembler_id=self._assembler_id(),
            assembler_version=self._assembler_version(),
            resolution=resolution,
            # `CMP-R-01`: what the composition tried, on the refused branch
            # too. `()` for every non-composite, which is what they mean.
            child_resolutions=child_resolutions,
        )

    def _applied_bindings(
        self, effective: EffectiveRequest
    ) -> tuple[PolicyBinding, ...]:
        """Every source the resolution consulted, by exact ``(key, version)``.

        ``24.6-03``: the constraint artifacts in force at ``asked_at``, the
        request contract's own pin, and the entitlement policy when an override
        was verified against it.

        Sources with no version lane (the request's own identity, a backend
        capability) are **not** bindings: :class:`PolicyBinding` is a Control
        Plane pin, and minting a lane for a capability is the fake artifact
        ``D-IMPL-253`` amendment 2 (1) forbids. They travel whole inside
        ``request_resolution``.

        Derived once and shared by the served record and every refusal record,
        because two derivations would let a refused decision and a fulfilled
        one disagree about what governed them (``24.6-07``).
        """
        return (
            *(
                PolicyBinding(key=source.identity, version=source.version)
                for source in effective.applied
                if source.kind == "artifact" and source.version is not None
            ),
            *(
                PolicyBinding(
                    key=override.grant_source.identity,
                    version=override.grant_source.version,
                )
                for override in effective.overrides
                if override.grant_source is not None
                and override.grant_source.version is not None
            ),
        )

    def _assembler_id(self) -> str | None:
        """The assembler in force, for replay dimension 4 — ``None`` here.

        ``D-IMPL-253`` Q16 with ``D-IMPL-245`` amendment 1. This composition
        holds no :class:`~ccf.agents.assembler.ContextAssemblerProtocol`: it
        *is* the assembly, composing engine → gates → serve itself. So it
        passes ``None`` and the record's :data:`~ccf.replay.record.NO_ASSEMBLER`
        sentinel makes that a positive claim rather than a silence.

        A method rather than an inline ``None`` so the two call sites — served
        and refused — read the same answer from one place, and so a resolver
        that later does hold an assembler has one line to change rather than
        two that could drift.
        """
        return None

    def _assembler_version(self) -> str | None:
        """The assembler's lane. ``None`` here; see :meth:`_assembler_id`."""
        return None

    # --- reading what the manifest put in force ----------------------------

    def _half_life_table(self) -> HalfLifeTable | None:
        """The deployment's λ_c table, when the resolver was wired with one (`D-IMPL-341`)."""
        if self.half_life_key is None:
            return None
        return self._artifact(self.half_life_key, HalfLifeTable)

    def _ttl_anchor_pins(self, anchor: TTLAnchorResolution) -> tuple[PolicyBinding, ...]:
        """The λ_c table pin an evidence-anchored serve records (`D-IMPL-341` R-5).

        Only for ``from_entity_freshness``: a decision-anchored record needs
        no table to re-derive its anchor, and pinning one would move the bytes
        of every record for nothing.
        """
        if anchor.basis != FROM_ENTITY_FRESHNESS or self.half_life_key is None:
            return ()
        return (
            PolicyBinding(
                key=self.half_life_key,
                version=self.fabric.pins.version_for(self.half_life_key),
            ),
        )

    def _artifact(self, key: str, expected: type[_Artifact]) -> _Artifact:
        """One parsed artifact, or a wiring refusal naming both sides.

        Delegates to :func:`_artifact_on` rather than repeating it, so the
        narrowing a resolver performs at call time and the one
        :func:`build_governed_resolver` performs at construction time are the
        same check with the same message. Two copies would drift, and the
        adopter would be told two different things about one mistake.
        """
        return _artifact_on(self.fabric, key=key, expected=expected)

    def _declaration(self) -> ProductClassDeclaration:
        """The Control Plane claim: what this product says produced it."""
        return self._artifact(self.product_class_key, ProductClassDeclaration)

    def _class_defaults(
        self, declaration: ProductClassDeclaration
    ) -> Mapping[str, object]:
        """What the product CLASS declares about omission — today one name.

        ``24.6-L-04``, ``D-IMPL-251`` C1=A. The class's
        :attr:`~ccf.products.contract.ServeObligations.default_debt_tolerance`
        is a declared *characteristic*, so it reaches the Authority layer as a
        default under the SDK's own parameter name
        (:data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER`) — never as a
        ceiling this layer folds.

        The key is **omitted** when the class declares nothing, rather than
        present at ``None``. A mapping carrying ``{"debt_tolerance": None}``
        would record an authority that established a non-value, and the
        resolution's own comparisons would then have to ask whether a resolved
        value means anything. Absence is what "this class has no opinion"
        looks like.
        """
        tolerance = declaration.serve_obligations.default_debt_tolerance
        if tolerance is None:
            return {}
        return {DEBT_TOLERANCE_PARAMETER: tolerance}

    def _request_contract(
        self, declaration: ProductClassDeclaration
    ) -> ProductRequestContract:
        """The request surface, however the manifest authored it.

        A request contract is ordinarily declared in an **adopter** namespace,
        so a manifest resolves it to a
        :class:`~ccf.controlplane.artifacts.DeclaredArtifact` and the four
        fields have to be read out of its declaration. ``D-IMPL-126`` shipped
        the named constructor for exactly that, and calling it here is the SDK
        doing the transcription once instead of every adopter doing it. A
        deployment that already holds a typed contract passes straight through.

        Delegates to :func:`_request_contract_on` for :meth:`_artifact`'s
        reason: the read this resolver performs at request time and the one
        :func:`build_governed_resolver` performs at boot are the same read.
        """
        return _request_contract_on(self.fabric, key=self.request_contract_key)

    def _operator_parameters(
        self, effective_request: ProductRequest
    ) -> dict[str, OperatorParametersArtifact]:
        """The adopter-side idiom: name your own keys, no type filtering.

        ``24.11-04`` / ``24.10-F-11`` (``D-IMPL-295``): the EFFECTIVE request is
        a parameter here, and it is the last link of the authority chain —
        Control Plane envelope -> :func:`~ccf.products.constraints.
        resolve_effective_request` -> declared binding -> operator. Before it,
        this method took no request at all, so an operator parameter whose value
        is knowable only per request could not be declared, and the one
        deployment that needed one substituted a value into its own resolved
        artifact at runtime.

        **The effective request and never the caller's.** Binding from
        ``request`` would take the raw value and bypass class defaults, policy
        bounds and technical capabilities at the exact final step those exist to
        govern — the substitution this closes, wearing a different hat.
        Regressed by ``test_the_call_site_binds_from_the_effective_request_not_
        the_callers``, which exists because swapping this one argument left the
        whole tree green.
        """
        return {
            key: self._bind_declared_request_values(
                self._artifact(key, OperatorParametersArtifact),
                key=key,
                effective_request=effective_request,
            )
            for key in self.operator_parameter_keys
        }

    def _bind_declared_request_values(
        self,
        artifact: OperatorParametersArtifact,
        *,
        key: str,
        effective_request: ProductRequest,
    ) -> OperatorParametersArtifact:
        """One artifact with every request-bound field replaced by its value.

        ``24.11-04`` / ``D-IMPL-295``. Returns the artifact unchanged when it
        declares no binding, which is every artifact shipped before this row.

        **Revalidated rather than copied.** :meth:`pydantic.BaseModel.
        model_copy` does not validate, so a bound value of the wrong type would
        reach the operator wearing the declared field's name. Reconstruction
        puts the effective value through the field's own declared type, so the
        compatibility this binding promises is enforced by the same machinery
        that enforces it for a literal — one type system rather than a second
        one written here to compare against it.

        Raises:
            ProductNotResolvable: the binding names a parameter the effective
                request does not carry, or carries a value the target field
                refuses. Both are wiring defects rather than governed "no"s —
                the deployment declared a binding its own request contract does
                not support, which no caller can fix.
        """
        bound = {
            name: value
            for name, value in artifact
            if isinstance(value, RequestBoundParameter)
        }
        if not bound:
            return artifact
        supplied = dict(effective_request.parameters)
        replacements: dict[str, object] = {}
        for name, binding in bound.items():
            if binding.parameter not in supplied:
                raise ProductNotResolvable(
                    f"operator parameters {key!r} bind {name!r} to request"
                    f" parameter {binding.parameter!r}, which the effective"
                    f" request does not carry; it offers {sorted(supplied)}."
                    " The binding is declared against a request contract that"
                    " does not declare the parameter"
                )
            replacements[name] = supplied[binding.parameter]
        document = artifact.model_dump()
        document.update(replacements)
        try:
            return type(artifact).model_validate(document)
        except ValidationError as mismatch:
            raise ProductNotResolvable(
                f"operator parameters {key!r} bind {sorted(replacements)} from"
                f" the effective request, and the value(s) do not satisfy the"
                f" declared field type(s): {mismatch}. A binding supplies a"
                " value; it never converts one (D-IMPL-295)"
            ) from mismatch

    def _reassess(
        self, factors: DebtFactors, *, fallback: DebtAssessment
    ) -> DebtAssessment:
        """Re-derive the routing signal from COMPOSED factors (`R2`).

        Read through the same manifest key `_obligation_in_force` uses, for the
        same reason: the profile that routes a composite is provably the one
        the manifest put in force, not one assembled beside it.

        A deployment that declares no bands keeps the scorer's own signal —
        there is nothing to re-route against, and inventing a band here would
        be the SDK holding a value (`D-IMPL-38`).
        """
        debt = context_debt(factors)
        if self.debt_profile_key is None:
            return DebtAssessment(
                debt=debt,
                signal=fallback.signal,
                factors=factors,
                scorers=fallback.scorers,
            )
        profile = self._artifact(self.debt_profile_key, DebtProfile)
        assessed = assess_debt(factors, profile=profile)
        return DebtAssessment(
            debt=assessed.debt,
            signal=assessed.signal,
            factors=factors,
            scorers=fallback.scorers,
        )

    def _obligation_in_force(self, signal: DebtSignal) -> str:
        """What this deployment's profile binds to the state debt landed in.

        ``24.11-03`` closes ``24.10-F-08``'s obligation limb. ``D-IMPL-117``
        says the SDK owes *"the structure and the API to populate and extract"*
        a signal-to-obligation binding, and **owes no obligation vocabulary**:
        :meth:`~ccf.controlplane.artifacts.DebtProfile.obligation_for` is the
        extract half — *"and the whole of it"*, in its own words — and this is
        the populate half on the governed path. Nothing here judges what a
        reference means; the binding is read off the deployment's declaration
        and carried verbatim.

        **Read by manifest key, never from a passed object**, for the reason
        this class's docstring gives for every other key: the profile served is
        provably the one the manifest put in force rather than one a caller
        assembled beside it. ``obligation_for`` states the same constraint from
        its side — nothing reaches the Control Plane for a *"latest"*, because
        the resolved value travels **inside the product's content address**
        (``D-IMPL-26``, ``D-IMPL-118``) and a substituted one would replay as
        though it had been in force.

        Returns :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE` when
        this deployment names no profile. That is the **positive claim that
        nothing was bound**, not a silent default: a deployment supplying its
        own scorer and declaring no bands has declared no obligation, which is
        exactly how ``obligation_for`` resolves an unbound state within a
        profile. A partly-bound estate is the ordinary case rather than a
        defect.
        """
        if self.debt_profile_key is None:
            return NO_OBLIGATION_IN_FORCE
        profile = self._artifact(self.debt_profile_key, DebtProfile)
        return profile.obligation_for(signal)

    def _register(
        self, declaration: ProductClassDeclaration
    ) -> RegisteredProductClass:
        """Register the class, forwarding every governance field it declares.

        The two registrations that must happen here rather than at boot: the
        ``MAX_TTL`` value, because registering it is what mints the pin Gate 3
        resolves; and the request contract, so its pin is re-resolvable years
        later against the surface a question was actually validated against.

        Every remaining governance field is forwarded off the declaration
        rather than left to :func:`~ccf.products.contract.register_product_class`'s
        defaults. The defaults are shipped and governed, but a deployment that
        *declared* accepted lineage modes and then had them silently replaced
        by a default would have written a policy the fabric never enforced.
        """
        max_ttl_version = self.control_plane.register(
            declaration.max_ttl_key, MaxTTL(seconds=self.max_ttl_seconds)
        )
        request_contract_version = self.control_plane.register(
            self.request_contract_key,
            self._request_contract(declaration),
        )
        return register_product_class(
            registry=self.control_plane,
            schema_name=declaration.schema_name,
            schema_version=declaration.schema_version,
            ttl_anchor=declaration.ttl_anchor,
            assembly_mode=declaration.assembly_mode,
            max_ttl_key=declaration.max_ttl_key,
            max_ttl_version=max_ttl_version,
            accepted_policy_binding_modes=declaration.accepted_policy_binding_modes,
            accepted_lineage_modes=declaration.accepted_lineage_modes,
            freshness_sla=declaration.freshness_sla,
            discovery=declaration.discovery,
            addressability=declaration.addressability,
            constituent_validity_floors=declaration.constituent_validity_floors,
            request_contract_key=self.request_contract_key,
            requires=declaration.requires,
            request_contract_version=request_contract_version,
            # 24.5-L-14 / L-26: the declared obligations reach the gate off
            # the registered value, exactly as the accepted modes do.
            serve_obligations=declaration.serve_obligations,
        )


def _replay_binding_on(fabric: BootedFabric) -> ReplayBinding | None:
    """The one :class:`ReplayBinding` a booted fabric declares, or ``None``.

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-282``
    ``R-12`` (Dave, 2026-09-08). The read half of the Control Plane's replay
    binding: :func:`build_governed_resolver` asks the fabric what this
    deployment declared, and uses it only for the members its caller did not
    supply.

    ``None`` is a **statement**, not a failure — a deployment that declares no
    binding is the ordinary case for every `ccf_config.yaml` written before the
    section existed, and the caller's refusal (which names both sources) is
    what speaks about it.

    **More than one is refused rather than resolved**, in
    :func:`~ccf.deployment.config._refuse_operator_set_divergence`'s voice and
    for its reason: two declarations that cannot both be what their author
    meant, compared before anything is wired, refused rather than reconciled.
    Picking the first would be a rule that silently changes behavior the day a
    second binding is registered, and only the deployment's author knows which
    was meant. Every key holding one is named, so the fix does not need a
    search.

    Raises:
        TypeError: the fabric declares more than one binding. An
            argument-shape mistake — the deployment was wired ambiguously —
            so the exception Python reserves for one, and never a governed
            refusal, because nobody asked a question yet.
    """
    declared = sorted(
        key
        for key, artifact in fabric.artifacts.items()
        if isinstance(artifact, ReplayBinding)
    )
    if not declared:
        return None
    if len(declared) > 1:
        raise TypeError(
            "this deployment declares more than one replay binding —"
            f" {', '.join(repr(key) for key in declared)} — and this call"
            " omits at least one of `artifact_store`, `replay_record_class`"
            " and `query_pin_class`, so which binding was meant is a question"
            " only the deployment's author can answer. Refusing beats picking"
            " (`D-IMPL-282` `R-12`): register one binding, or pass the three"
            " arguments explicitly"
        )
    binding = fabric.artifacts[declared[0]]
    assert isinstance(binding, ReplayBinding)  # narrowed by the filter above
    return binding


def _declared_member(
    binding: ReplayBinding | None, *, member: str, argument: str
) -> str:
    """One member of the declared binding, or the neither-source refusal.

    ``D-IMPL-282`` ``R-12``, Dave: *"Do not silently invent a replay backend
    when neither source provides one."* So there is no default here and no
    warning — a resolver that could not reach a replay writer would be a
    resolver whose only remaining move is to serve an unrecorded decision, and
    ``D-IMPL-256``'s invariant is that such a boundary is *unavailable*, not
    partially governed.

    Both places the value could have come from are named, because a caller
    reading this should not have to work out whether the fix is an argument or
    a section.

    Raises:
        TypeError: neither the call nor the Control Plane supplies ``member``.
    """
    if binding is None:
        raise TypeError(
            f"this call omits `{argument}` and this deployment's Control Plane"
            f" declares no replay binding, so nothing supplies it. State"
            f" `{argument}` on the call, or declare a `replay:` section naming"
            f" `{member}` in the deployment's ccf_config.yaml — the SDK does"
            " not invent a replay backend when neither source provides one"
            " (`D-IMPL-282` `R-12`)"
        )
    value = getattr(binding, member)
    assert isinstance(value, str)  # ReplayBinding declares all three as str
    return value


def _ttl_binding_on(fabric: BootedFabric) -> TtlBinding | None:
    """The one :class:`~ccf.controlplane.artifacts.TtlBinding` a fabric declares, or ``None``.

    `D-IMPL-343` R-3a, on :func:`_replay_binding_on`'s shape and for its
    reason: ``None`` is a statement (every config written before the `ttl:`
    section existed declares none, and the two builder keywords still supply
    the figures), and more than one is refused rather than resolved.

    Raises:
        TypeError: the fabric declares more than one TTL binding.
    """
    declared = sorted(
        key for key, artifact in fabric.artifacts.items() if isinstance(artifact, TtlBinding)
    )
    if not declared:
        return None
    if len(declared) > 1:
        raise TypeError(
            "this deployment declares more than one TTL binding —"
            f" {', '.join(repr(key) for key in declared)} — so which window"
            " was meant is a question only the deployment's author can"
            " answer (D-IMPL-343 R-3a): declare one `ttl:` section"
        )
    binding = fabric.artifacts[declared[0]]
    assert isinstance(binding, TtlBinding)  # narrowed by the filter above
    return binding


def _resolve_ttl(
    fabric: BootedFabric, *, max_ttl_seconds: int | None, product_ttl_seconds: int | None
) -> tuple[int, int]:
    """The class ceiling and the product lifetime — one authority, two readers.

    `D-IMPL-343` R-3a, `D-IMPL-292` applied to the two TTL figures. Per
    figure: the call's value when the declaration has none; the declaration's
    when the call is silent; **both, held equal**, when both speak — and a
    disagreement is refused with both values named rather than resolved by
    precedence, because a builder keyword that could silently override a
    declared window is exactly the second authority the ruling deletes. When
    neither source supplies a figure the refusal names both places it could
    have come from, on `_declared_member`'s posture: the SDK invents no TTL.

    Raises:
        TypeError: a figure is supplied by neither source, or by both with
            different values.
    """
    binding = _ttl_binding_on(fabric)
    resolved: list[int] = []
    for argument, member, supplied in (
        ("max_ttl_seconds", "max_ttl_seconds", max_ttl_seconds),
        ("product_ttl_seconds", "product_ttl_seconds", product_ttl_seconds),
    ):
        declared = None if binding is None else int(getattr(binding, member))
        if supplied is None and declared is None:
            raise TypeError(
                f"this call omits `{argument}` and this deployment's Control"
                " Plane declares no `ttl:` binding, so nothing supplies it."
                f" State `{argument}` on the call, or declare a `ttl:` section"
                f" naming `{member}` in the deployment's ccf_config.yaml — the"
                " SDK does not invent a TTL when neither source provides one"
                " (D-IMPL-343 R-3a; D-IMPL-292)"
            )
        if supplied is not None and declared is not None and supplied != declared:
            raise TypeError(
                f"this call states `{argument}={supplied}` and this"
                f" deployment's `ttl:` binding declares `{member}: {declared}`;"
                " a declared value has one authority, and a call that could"
                " override it silently would be a second one (D-IMPL-343 R-3a;"
                " D-IMPL-292) — drop the argument, or correct the declaration"
            )
        resolved.append(int(supplied if supplied is not None else declared))  # type: ignore[arg-type]
    return resolved[0], resolved[1]


def declared_refusal_recorder(
    *,
    control_plane: ControlPlaneProtocol,
    artifact_store: ArtifactStoreProtocol,
    replay_record_class: str,
    tenant_id: str,
    assembly_mode: AssemblyMode,
    policy_bundle_pin: PolicyBinding,
) -> ReplayRefusalRecorder:
    """ONE :class:`ReplayRefusalRecorder` for a deployment, built once, shared everywhere.

    `D-IMPL-343` (design §5.3, §5.4). The recorder :func:`build_governed_resolver`
    builds for itself is bound to the store, class, tenant, mode and bundle pin
    the call supplied — and before this function a door that needed the same
    recorder could not reach it, because the canonical trees built their
    resolver per question inside a function that returned only the outcome.
    So every one of those doors built a SECOND recorder over a SECOND store,
    and served and refused decisions were filed in two places under a class
    each module restated (`CP03C-F-07`'s neighborhood). This is the same
    construction the builder performs, exposed so a composition root can build
    the recorder ONCE — from the declared `replay:` binding and the bundle's
    content address — and hand the same object to the resolver (through
    ``refusal_recorder=``) and to
    :func:`~ccf_runtime.mcp.egress.build_egress_server`.

    ``policy_bundle_pin.version`` is the bundle's content address, which is
    what the registry mints for it (`D-IMPL-26`), so a caller holding the
    parsed bundle can build this before anything is booted and the pin it
    records is the pin the boot will mint.
    """
    return ReplayRefusalRecorder(
        artifact_store=artifact_store,
        replay_record_class=replay_record_class,
        tenant_id=tenant_id,
        assembly_mode=assembly_mode,
        policy_bundle_pin=policy_bundle_pin,
        disclosure_level_for=_disclosure_reader(control_plane),
    )


def build_governed_resolver(
    *,
    fabric: BootedFabric,
    control_plane: ControlPlaneProtocol,
    product_class_key: str,
    request_contract_key: str,
    operator_parameter_keys: tuple[str, ...],
    policy_bundle_key: str,
    plan_factory: ProjectionPlanFactoryProtocol,
    #: `D-IMPL-343` R-3a (`D-IMPL-292` applied): optional, and read from the
    #: deployment's declared `ttl:` binding when omitted. A call stating a
    #: value that DIFFERS from the declaration is refused with both named —
    #: an argument for a declared value is one more place to be wrong.
    max_ttl_seconds: int | None = None,
    product_ttl_seconds: int | None = None,
    decision_instant_parameter: str | None = None,
    source_refresh_recency: SourceRefreshRecency = NO_SOURCE_REFRESH_RECENCY,
    #: `D-IMPL-336` Amendment 3, F0. Defaulted HERE and required on the
    #: resolver itself: the dataclass forbids defaults so every deployment
    #: states its posture explicitly, while this factory — which most
    #: deployments call — keeps the non-composite default that every product
    #: shipped before this surface had.
    composite_children: (
        CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None
    ) = None,
    #: `D-IMPL-336` **O3** — the clock a child admission is judged against.
    #: Defaults to the process's UTC clock, which is the right value for a
    #: deployment; tests inject a fixed instant so the evidence-age and skew
    #: boundaries can be asserted exactly rather than approached.
    admission_clock: Callable[[], datetime] = _utc_now,
    artifact_store: ArtifactStoreProtocol | None = None,
    replay_record_class: str | None = None,
    query_pin_class: str | None = None,
    artifact_store_root: Path | None = None,
    half_life_key: str | None = None,
    debt_profile_key: str | None = None,
    declared_completeness: Decimal | None = None,
    evidence_clock_key: str | None = None,
    declared_semantic_consistency: Decimal | None = None,
    debt_scorer: AssemblyDebtScorerProtocol | None = None,
    product_gate: ProductGateProtocol | None = None,
    constraint_resolver: PolicyConstraintResolver | None = None,
    capabilities: tuple[TechnicalCapability, ...] | None = None,
    #: `D-IMPL-343`: the ONE recorder a deployment may hand in so its door and
    #: its resolver share a writer (see :func:`declared_refusal_recorder`);
    #: ``None`` selects the SDK's own over the store this call chose, exactly
    #: as before. And the declared acquisition seam (R-4), ``None`` for every
    #: deployment whose fabric is populated before the resolver is reached.
    refusal_recorder: RefusalRecorderProtocol | None = None,
    acquisition: AcquisitionSeamProtocol | None = None,
) -> GovernedResolver:
    """Build a :class:`GovernedResolver`, selecting the SDK's reference scorer.

    **SDK-defined** (CLAUDE.md §11); the ruling of record is
    ``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
    §6 and **Amendment A.3** (Dave, 2026-08-16). This is the *"thin*
    ``build_governed_resolver(...)`` *helper"* §6 names, and the module
    docstring records the two measurements that put the default here rather
    than on the class.

    What this helper is for
    -----------------------
    **A deployment that provides only data never has to know
    :class:`AssemblyDebtScorerProtocol` exists.** Everything below is plain
    data plus the three fabric objects plus the single permitted projection
    reference (Amendment A.3) — and the debt scorer arrives from the SDK. A
    deployment reaching the fabric through this seam imports no scorer, writes
    no ``GraphView`` → :class:`~ccf.halflife.assessment.DebtFactors` adapter,
    and makes no row-selection choice in its own tree.

    How far that reaches, measured rather than claimed
    ---------------------------------------------------
    ``24.10-04`` / ``R-03`` (``D-IMPL-282``) tried this seam from the SDK's own
    worked example, ``examples/s1-01-hello-context-product/spine.py``, against
    a live substrate. **The example could not adopt it**, and four absent seams
    were why — of which ``24.10-F-06`` and ``24.10-F-07`` are closed as of
    ``24.11-02b``, leaving two. Read
    :class:`GovernedResolver`'s own docstring for ``24.10-F-06`` through
    ``24.10-F-09`` and ``tests/examples/
    test_s1_01_governed_resolver_adoption.py`` for the executable roster. One
    of the two bears directly on the arguments below and is worth knowing
    before wiring rather than after:

    * A ``debt_scorer`` supplied here measures ``D_c`` at the *graph boundary*,
      because that is the only instant the resolver has; a deployment whose
      class declares a distinct decision instant will find it unread
      (``24.10-F-09``).

    It is recorded, and not fixed here: ``D-IMPL-282`` authorizes *"no
    broader API redesign … up front"*, so what it earns is a ruling.

    The one that *looked* like an argument problem turned out not to be one.
    ``24.11-02`` added a ``similarity_index_version`` argument here, and Dave
    ruled that insufficient (``D-IMPL-292``): a corpus's version identity is
    *decision-affecting operator configuration*, and an argument makes it an
    ungoverned value the deployment restates in code. **There is no such
    argument below, and its absence is the repair.** A deployment declaring a
    **similarity** operator-parameters artifact among
    ``operator_parameter_keys`` declares
    :attr:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact.index_version`
    *on that artifact*, and :func:`~ccf.deployment.build_operator_registry`
    reads it there. That is the difference between a value in the pin set and a
    value in a call — and it is why this argument is not offered even as an
    optional convenience: an optional second site is still a site at which a
    deployment can contradict its own declaration.

    What "the default" can and cannot mean here
    --------------------------------------------
    It means the **machinery**, and it can never mean the **values**. The
    reference scorer needs four inputs (:data:`DEBT_SCORER_INPUTS`), and none of
    the four is something the SDK may invent:

    * ``half_life_key`` / ``debt_profile_key`` name **Control Plane artifacts**.
      They are keys rather than discovered artifacts because §6 rules out *"new
      discovery or registration machinery in this change"* — a fabric holding
      two ``λ_c`` tables has no SDK-knowable right answer, and picking the only
      one present would be a rule that silently changes behaviour the day a
      second is registered.
    * ``declared_completeness`` / ``declared_semantic_consistency`` are the two
      factors with **no SDK measurement at all**.
      :class:`~ccf.halflife.assessment.DebtFactors` states that position in its
      own docstring, and ``17-11`` rejected each candidate default in turn
      (``C = 1`` is a number the SDK chose inside a delivered product's content
      address; ``C = 0`` fail-closes every deployment; deriving ``C`` from the
      table's breadth couples completeness to how many observation types a
      deployment happens to calibrate). They travel through
      :class:`~ccf.products.debt_scorer.DeclaredFactor`, so each lands in the
      Decision Replay record under its own :class:`~ccf.halflife.assessment.ScorerPin`
      (``D-IMPL-47``) and an examiner can tell an assertion from a measurement.

    So this helper defaults the *adapter*, the *decay computation* and the
    *pinning* — the parts that were mechanism the SDK declined to ship — and
    defaults nothing a deployment is entitled to decide.

    **The replay binding defaults the WIRING and never a replay semantic**
    (`R-12`; ``D-IMPL-282``, Dave, 2026-09-08). Three arguments —
    ``artifact_store``, ``replay_record_class``, ``query_pin_class`` — may now
    be omitted, and the deployment's own `ccf.replay-binding` supplies what the
    call left out, **per member**: a call naming ``replay_record_class`` and
    omitting the other two takes the explicit record class and the declared
    query-pin class and store. The precedence, in Dave's own order, is
    *explicit builder argument > Control Plane replay binding > no
    binding/refusal according to existing availability semantics*, and the
    third step is a refusal rather than a fallback because *"Do not silently
    invent a replay backend when neither source provides one."*

    What forced the argument, recorded here because a helper that grew one
    without saying why is how this seam accumulates arguments nobody can
    account for: cp-05 measured that a deployment's replay binding had nowhere
    declared to live — `examples/cp-05-credit-exposure-rollup/artifacts
    /replay.yaml` — so the three strings lived either as module constants in a
    deployment's own Python or as an adopter-namespaced artifact beside the
    config, and neither is the Control Plane. What the binding may carry is
    bounded by the same ruling: *"No product-specific replay semantics in the
    Control Plane—only deployment binding/configuration."* It says where
    records go, never what a record means.

    The two argument shapes, and why supplying neither or both is refused
    ---------------------------------------------------------------------
    Exactly one of these is a valid call:

    * **the data-only path** — the four :data:`DEBT_SCORER_INPUTS`, no
      ``debt_scorer``. The SDK builds
      :class:`~ccf.products.debt_scorer.AssemblyDebtScorer`.
    * **the override path** — ``debt_scorer``, none of the four. A deployment
      whose product means something the reference does not measure supplies its
      own conforming callable, exactly as the Protocol intends.

    Neither is refused rather than defaulted, because a resolver built with no
    scorer and no material would be a resolver with **no way to measure debt**,
    and the only thing left for it to do is serve an unscored product — the
    failure Risk 3 of the spec names: *"a default that nothing exercises is a
    check that stops checking without going red."* Both are refused because
    silently ignoring four supplied arguments is how a deployment comes to
    believe a ``λ_c`` key is in force when it is not.

    Args:
        fabric: The booted deployment, as :func:`~ccf.deployment.load_and_boot`
            returned it.
        control_plane: The Control Plane the fabric booted against.
        product_class_key: Manifest key of the served class declaration.
        request_contract_key: Manifest key of its request surface.
        operator_parameter_keys: Manifest keys of the operator parameters —
            however many (``D-IMPL-132``).
        policy_bundle_key: Manifest key of the policy regime in force.
        plan_factory: The deployment's Π factory. The **one** thing measurement
            said cannot be data (Amendment A.2), and therefore the one thing
            this helper cannot default.
        artifact_store: Where replay records and executed-query bytes land. A
            substrate reached *through* mechanism, never a second writer
            (CLAUDE.md §7.4). Taken as an object rather than a path so this
            seam stays substrate-agnostic. **Optional since `R-12`**: when it
            is omitted the deployment's declared binding supplies a
            file-backed store rooted at ``artifact_store_root /
            <declared store_dirname>``; when both sources are silent the build
            refuses.
        replay_record_class: Artifact class replay records are filed under.
            **Optional since `R-12`** — the declared binding's
            ``record_class`` when the call omits it.
        query_pin_class: Artifact class executed-query bytes are filed under.
            **Optional since `R-12`** — the declared binding's
            ``query_pin_class`` when the call omits it.
        artifact_store_root: The directory the declared ``store_dirname`` is
            joined onto. Required only when the *binding* is what supplies the
            store, and refused-when-absent rather than defaulted: a root taken
            from the process's working directory would put a deployment's
            decision records wherever it happened to be started from. Ignored
            when ``artifact_store`` is passed, because an object needs no root.
        max_ttl_seconds: The class's TTL ceiling.
        product_ttl_seconds: A served product's own lifetime. Two figures, and
            they stay two.
        half_life_key: Manifest key of this deployment's ``λ_c`` table.
        debt_profile_key: Manifest key of its ``D_c`` bands. **The one input
            here that is not only scorer material** (``24.11-03``,
            ``24.10-F-08``): the same profile binds the obligation the served
            product carries, so this may accompany an explicit ``debt_scorer``
            where the other three may not — the exclusion below is about
            *scoring*, never about the *declaration*.
        declared_completeness: The ``C`` this deployment asserts, in ``[0, 1]``.
        declared_semantic_consistency: The ``S`` it asserts, in ``[0, 1]``.
        debt_scorer: A conforming scorer that **overrides** the reference.
        product_gate: The deployment's implementation of the invariant its
            product class declares (``24.10-02`` / ``R-11``; ``D-IMPL-282``
            option 1a). Unlike ``debt_scorer`` this has **no reference
            implementation and cannot have one**: the SDK ships the machinery
            for every seam it defines (CLAUDE.md §11), and the machinery here
            is the identity, the execution point and the refusal — the
            predicate is the product's own meaning, which no SDK could supply.
            So the pairing is not default-versus-override but declared-versus-
            supplied, and **both mismatches are refused** rather than
            defaulted: see the ``Raises`` note below.
        constraint_resolver: A conforming resolver that **overrides** the
            reference. When omitted, the SDK selects
            :class:`~ccf.products.constraints.ReferencePolicyConstraintResolver`
            over the same Control Plane this fabric booted against, keyed to
            this tenant's entitlement policy through
            :func:`~ccf.products.entitlement.product_entitlement_key` — so a
            deployment that registered one gets its overrides verified without
            naming anything, and a deployment that registered none entitles no
            override, which is deny-by-default rather than an error. Unlike the
            debt scorer this default needs **no material**: the resolver reads
            what the deployment already registered, so there is no pair of
            argument shapes here and none is refused (``24.6-03``).
        capabilities: The technical limits in force. When omitted they are
            derived structurally from what the boot handed back
            (:func:`_capabilities_of`), which is the empty tuple for every
            shipped boot path — the handle carries a reader and the ceiling is
            the store's. Pass them explicitly to bound a parameter by a
            substrate limit; the binding that says *which* parameter is the
            request contract's (``capability_bindings``).

    **The refusal recorder is selected here too, and it takes no argument**
    (``24.6-07``; ``D-IMPL-253`` Q13). :class:`ReplayRefusalRecorder` needs the
    store, the artifact class and the tenant — all three already arguments —
    plus the assembly mode and the bundle pin, both read off what the manifest
    put in force. So unlike the debt scorer there is no pair of argument shapes
    here and none is refused: a deployment reaching the fabric through this
    seam gets a governed refusal path without naming anything, and the
    ``D-IMPL-256`` invariant *"a delivery boundary unable to reach the replay
    writer is unavailable, not partially governed"* holds by wiring.

    A deployment that files its refusal records elsewhere constructs
    :class:`GovernedResolver` directly with its own
    :class:`RefusalRecorderProtocol`.

    Returns:
        The composed resolver, ready to be handed to a delivery surface.

    Raises:
        TypeError: a ``product_gate`` was supplied against a class declaring
            none, or a class declaring one was built with no callable. The
            second is the one that matters: a declared gate nothing executes is
            *"a default that nothing exercises*, which *is a check that stops
            checking without going red"* — an audit would report an invariant
            in force that had never run. The first is refused rather than
            ignored because a deployment silently running an ungoverned
            predicate inside the determination path would have no identity to
            record it under. Also raised when both a scorer and the material to
            build one were supplied, or neither was. An argument-shape mistake, so the exception Python
            already reserves for one — and never a governed refusal, because
            nobody asked a question yet. Also raised when a replay member is
            supplied by neither the call nor a declared binding, when the
            binding is what supplies the store and no ``artifact_store_root``
            was given, and when the fabric declares more than one binding —
            see :func:`_replay_binding_on` and :func:`_declared_member`.
        ProductNotResolvable: ``half_life_key`` or ``debt_profile_key`` names no
            artifact on the booted fabric, or names one of another class; or
            ``product_class_key`` / ``request_contract_key`` does.
        ProductClassRegistrationError: the product class declares a default for
            a parameter its request contract does not declare as an argument —
            an internally inconsistent declaration, refused at boot under
            ``D-IMPL-258`` (5) rather than in front of a caller.
        ValueError: a declared factor lies outside ``[0, 1]``. Raised by
            :class:`~ccf.products.debt_scorer.DeclaredFactor`, where the value
            was authored, rather than three frames later.
    """
    # `D-IMPL-258` (5), FIRST, before any other wiring decision: a product class
    # whose declared default names a parameter its own request contract does not
    # expose is an internally inconsistent declaration, and Dave ruled that it
    # *"should fail registration/configuration/boot validation, not produce a
    # shell to a caller."* This is the boot half; registration's half is in
    # `ccf.products.contract.register_product_class`. It runs first because a
    # deployment that cannot answer coherently should not get as far as choosing
    # a debt scorer, and because a failure here names the two documents that
    # disagree rather than whatever fell over later.
    boot_declaration = _artifact_on(
        fabric, key=product_class_key, expected=ProductClassDeclaration
    )
    # `D-IMPL-341`: the λ_c table the resolver anchors an evidence-anchored
    # expiry on and pins on the record. It is `half_life_key` when this call
    # lets the helper build the reference scorer, and `evidence_clock_key` —
    # the same manifest key, stated once more — when a supplied scorer already
    # reads the table (the paved road), because the scorer and the resolver
    # read it for two different things: `F`, and the instant the window runs
    # from. Neither is a value; both name the deployment's one table.
    if half_life_key is not None and evidence_clock_key is not None and half_life_key != evidence_clock_key:
        raise TypeError(
            f"this call names `half_life_key={half_life_key!r}` and"
            f" `evidence_clock_key={evidence_clock_key!r}`; a deployment has one"
            " λ_c table, so the two keys must agree or only one be given"
            " (D-IMPL-341)"
        )
    resolver_table_key = half_life_key if half_life_key is not None else evidence_clock_key
    # `D-IMPL-341` R-3 (first row), for a resolver wired by hand: the same
    # registration-time refusal the config derivation makes, over the table
    # this builder is about to anchor with.
    if resolver_table_key is not None:
        refuse_undeclared_ttl_anchor(
            ttl_anchor=boot_declaration.ttl_anchor,
            entries=_artifact_on(fabric, key=resolver_table_key, expected=HalfLifeTable).entries,
            product_class=boot_declaration.schema_name,
        )
    refuse_undeclared_class_default(
        schema_name=boot_declaration.schema_name,
        schema_version=boot_declaration.schema_version,
        serve_obligations=boot_declaration.serve_obligations,
        declared=_request_contract_on(fabric, key=request_contract_key),
    )

    # `24.11-04` / `D-IMPL-295`, immediately after and for the same reason: a
    # request-bound operator parameter naming an argument the contract does not
    # declare is two documents disagreeing, and boot is where they are both in
    # hand. Existence only — the artifact's own validation owns the type.
    _refuse_unbindable_request_parameter(
        parameters={
            key: _artifact_on(fabric, key=key, expected=OperatorParametersArtifact)
            for key in operator_parameter_keys
        },
        declared=_request_contract_on(fabric, key=request_contract_key),
        request_contract_key=request_contract_key,
    )

    # `R-11` (`D-IMPL-282` option 1a), immediately after: the class's declared
    # gate and the supplied callable must agree, and BOTH mismatches are
    # refused. Read off the declaration already parsed above rather than a
    # second read, so what the check sees is what the resolver will stamp.
    declared_gate = boot_declaration.declared_product_gate
    if declared_gate.gate_id and product_gate is None:
        raise TypeError(
            f"the product class {product_class_key!r} declares the runtime"
            f" gate {declared_gate.gate_id!r} at version"
            f" {declared_gate.gate_version!r}, and this call supplies no"
            " `product_gate` to run it. A declared check that nothing executes"
            " is a check that stops checking without going red, and an audit"
            " would read the declaration as an invariant in force. Pass the"
            " deployment's callable, or remove `declared_product_gate` from"
            " the class document (`D-IMPL-282` `R-11`)"
        )
    if product_gate is not None and not declared_gate.gate_id:
        raise TypeError(
            "this call supplies a `product_gate` and the product class"
            f" {product_class_key!r} declares none, so the SDK has no identity"
            " to stamp on a refusal it produced and replay could not say which"
            " gate refused. Declare `declared_product_gate` on the class"
            " document with the gate's id and version, or drop the argument"
            " (`D-IMPL-282` `R-11`; the identity is the Control Plane's half"
            " and the implementation is the deployment's)"
        )

    # `R-12` (`D-IMPL-282`), SECOND — before the constraint-resolver branch and
    # before any scorer material is read, so a wiring mistake is reported
    # before anything else is chosen. Per member, in Dave's ruled order:
    # explicit argument, then the deployment's declared binding, then a
    # refusal that names both places the value could have come from.
    # Asked only when something is actually missing, and that is what makes
    # the ambiguity refusal below a statement about this CALL rather than about
    # this deployment: a fabric declaring two bindings and a call naming all
    # three arguments has asked nothing ambiguous, and refusing it would break
    # a deployment that had already resolved its own ambiguity.
    binding = (
        _replay_binding_on(fabric)
        if artifact_store is None
        or replay_record_class is None
        or query_pin_class is None
        else None
    )
    record_class = (
        replay_record_class
        if replay_record_class is not None
        else _declared_member(
            binding, member="record_class", argument="replay_record_class"
        )
    )
    pin_class = (
        query_pin_class
        if query_pin_class is not None
        else _declared_member(
            binding, member="query_pin_class", argument="query_pin_class"
        )
    )
    if artifact_store is not None:
        store: ArtifactStoreProtocol = artifact_store
    else:
        dirname = _declared_member(
            binding, member="store_dirname", argument="artifact_store"
        )
        if artifact_store_root is None:
            raise TypeError(
                "this call omits `artifact_store` and this deployment declares"
                f" store_dirname {dirname!r}, which is half a location: a"
                " dirname is relative to a root, and the other half is the"
                " caller's. Pass `artifact_store_root`, or pass"
                " `artifact_store` — the SDK does not root a deployment's"
                " decision records at whichever directory the process happened"
                " to start in (`D-IMPL-282` `R-12`)"
            )
        # The file-backed reference store is what a dirname can select; a
        # deployment on the MCP-backed store passes `artifact_store` and wins
        # under the precedence above. See `ReplayBinding`'s own docstring,
        # where the limitation is recorded rather than left to be discovered.
        store = FileArtifactStore(root=Path(artifact_store_root) / dirname)

    # `D-IMPL-343` R-3a, THIRD: the two TTL figures, from the call or from the
    # declared `ttl:` binding, held EQUAL when both speak and refused when
    # neither does. Before the R-12 scorer material for the R-12 reason.
    ceiling, lifetime = _resolve_ttl(
        fabric, max_ttl_seconds=max_ttl_seconds, product_ttl_seconds=product_ttl_seconds
    )
    # `D-IMPL-343` R-3b, the same shape for the decision instant: the class
    # DECLARES which request parameter carries it, this call may restate it,
    # and the two are held equal — a keyword that could name a different
    # parameter than the declaration would be the ungoverned second authority
    # `24.10-F-09` recorded and `D-IMPL-292` refuses.
    declared_instant = boot_declaration.decision_instant_parameter
    if decision_instant_parameter is None:
        decision_instant_parameter = declared_instant
    elif declared_instant is not None and declared_instant != decision_instant_parameter:
        raise TypeError(
            f"this call states `decision_instant_parameter={decision_instant_parameter!r}`"
            f" and the product class {product_class_key!r} declares"
            f" `decision_instant_parameter: {declared_instant}`; the class's"
            " declaration is the one authority for which argument carries the"
            " decision instant (D-IMPL-343 R-3b; D-IMPL-292) — drop the"
            " argument, or correct the declaration"
        )

    # Keyed by name rather than zipped against :data:`DEBT_SCORER_INPUTS`
    # positionally: a positional pairing goes on running after somebody reorders
    # the constant, and reports the wrong argument in both refusals below.
    # `tests/products/test_resolver_defaults.py::test_the_named_inputs_are_this_helper_s_own_optional_parameters`
    # holds the constant and this signature to each other in both directions.
    resolution_seam: PolicyConstraintResolver
    if constraint_resolver is not None:
        resolution_seam = constraint_resolver
    elif isinstance(control_plane, _ConstraintSource):
        resolution_seam = ReferencePolicyConstraintResolver(
            control_plane=control_plane,
            entitlement_key=product_entitlement_key(tenant_id=fabric.tenant_id),
        )
    else:
        # Structural, and checked rather than assumed: the reference resolver
        # needs a read surface `ControlPlaneProtocol` does not promise —
        # `keys_of_class`, `versions` and `peek`, which are how "what is in
        # force at this instant" is answered without reaching for the latest
        # version. The shipped `ControlPlaneRegistry` has all three. A plane
        # that does not is a wiring fact the caller can fix two ways, and both
        # are named.
        raise TypeError(
            "this call supplies no `constraint_resolver`, and the Control"
            f" Plane it was given ({type(control_plane).__name__}) does not"
            " offer the read surface the SDK's reference resolver needs:"
            " `keys_of_class`, `versions`, `peek` and `resolve`. Pass a"
            " conforming `PolicyConstraintResolver`, or a Control Plane that"
            " can be asked which constraints are in force"
        )
    technical = (
        _capabilities_of(fabric) if capabilities is None else capabilities
    )

    # 24.6-07: the SDK's own refusal recorder, over the store and tenant this
    # call already supplies. It is selected here for `debt_scorer`'s reason —
    # `GovernedResolver` is the auditable, defaultless composition and this
    # helper is where the SDK chooses its own reference — and it needs no
    # material a deployment is entitled to decide: the store, the artifact
    # class and the tenant are already arguments, and the assembly mode and
    # bundle pin are read off what the manifest put in force.
    #
    # Both are read HERE rather than per call, deliberately: a recorder is
    # bound to a deployment exactly as its resolver is, and a mode or a pin
    # re-read at each refusal could describe a deployment that had changed
    # since the determination it is recording.
    #
    # `D-IMPL-343`: a recorder the deployment already holds wins — the paved
    # road builds ONE over the declared binding and hands the same object to
    # this resolver and to its door, so a served and a refused decision cannot
    # land in two stores or under two classes. Nothing about the recorder the
    # SDK builds when none is handed in has changed.
    recorder: RefusalRecorderProtocol = refusal_recorder if refusal_recorder is not None else ReplayRefusalRecorder(
        artifact_store=store,
        replay_record_class=record_class,
        tenant_id=fabric.tenant_id,
        assembly_mode=_artifact_on(
            fabric, key=product_class_key, expected=ProductClassDeclaration
        ).assembly_mode,
        policy_bundle_pin=PolicyBinding(
            key=policy_bundle_key,
            version=fabric.pins.version_for(policy_bundle_key),
        ),
        # 24.6-08: the posture in force, read from the deployment's own
        # registry per call for `ControlPlaneProductEntitlementSource`'s reason
        # (no cache, no TTL — a level changed in the Control Plane governs the
        # next determination, not the one after a process restart).
        disclosure_level_for=_disclosure_reader(control_plane),
    )

    declared: dict[str, object | None] = {
        "half_life_key": half_life_key,
        "debt_profile_key": debt_profile_key,
        "declared_completeness": declared_completeness,
        "declared_semantic_consistency": declared_semantic_consistency,
    }
    supplied = tuple(
        name for name in _SCORER_ONLY_INPUTS if declared[name] is not None
    )

    if debt_scorer is not None:
        if supplied:
            raise TypeError(
                "this call supplies both `debt_scorer` and"
                f" {', '.join(repr(name) for name in supplied)}, and the two are"
                " alternatives rather than layers: an explicit scorer replaces"
                " the SDK's reference entirely, so the material for building the"
                " reference would be read by nothing. Pass the scorer, or pass"
                f" {', '.join(repr(name) for name in DEBT_SCORER_INPUTS)} and let"
                " this helper select"
                " `ccf.products.debt_scorer.AssemblyDebtScorer`"
            )
        return GovernedResolver(
            fabric=fabric,
            control_plane=control_plane,
            product_class_key=product_class_key,
            request_contract_key=request_contract_key,
            operator_parameter_keys=operator_parameter_keys,
            policy_bundle_key=policy_bundle_key,
            # `24.11-03` / `24.10-F-08`: passed through on BOTH legs. A
            # deployment supplying its own scorer may still declare bands,
            # and the obligation it binds is not the scorer's to carry.
            debt_profile_key=debt_profile_key,
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
            product_gate=product_gate,
            constraint_resolver=resolution_seam,
            capabilities=technical,
            refusal_recorder=recorder,
            artifact_store=store,
            replay_record_class=record_class,
            query_pin_class=pin_class,
            max_ttl_seconds=ceiling,
            product_ttl_seconds=lifetime,
            decision_instant_parameter=decision_instant_parameter,
            source_refresh_recency=source_refresh_recency,
            composite_children=composite_children,
            admission_clock=admission_clock,
            acquisition=acquisition,
            half_life_key=resolver_table_key,
        )

    if (
        half_life_key is None
        or debt_profile_key is None
        or declared_completeness is None
        or declared_semantic_consistency is None
    ):
        missing = tuple(
            name for name in DEBT_SCORER_INPUTS if name not in supplied
        )
        raise TypeError(
            "this call supplies no `debt_scorer` and omits"
            f" {', '.join(repr(name) for name in missing)}, so there is nothing"
            " to measure `D_c` with. The SDK's reference scorer is the default"
            " and it is a construction rather than a value: it needs the two"
            " Control Plane keys naming this deployment's λ_c table and D_c"
            " bands, and the two factors the SDK has no measurement for. A"
            " resolver built without them could only serve an unscored product,"
            " which is why this is refused rather than defaulted"
        )

    return GovernedResolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=product_class_key,
        request_contract_key=request_contract_key,
        operator_parameter_keys=operator_parameter_keys,
        policy_bundle_key=policy_bundle_key,
        debt_profile_key=debt_profile_key,
        plan_factory=plan_factory,
        debt_scorer=AssemblyDebtScorer(
            table=_artifact_on(fabric, key=half_life_key, expected=HalfLifeTable),
            profile=_artifact_on(
                fabric, key=debt_profile_key, expected=DebtProfile
            ),
            completeness=DeclaredFactor(value=declared_completeness),
            semantic_consistency=DeclaredFactor(
                value=declared_semantic_consistency
            ),
        ),
        product_gate=product_gate,
        constraint_resolver=resolution_seam,
        capabilities=technical,
        refusal_recorder=recorder,
        artifact_store=store,
        replay_record_class=record_class,
        query_pin_class=pin_class,
        max_ttl_seconds=ceiling,
        product_ttl_seconds=lifetime,
        decision_instant_parameter=decision_instant_parameter,
        source_refresh_recency=source_refresh_recency,
        composite_children=composite_children,
        admission_clock=admission_clock,
        acquisition=acquisition,
        half_life_key=resolver_table_key,
    )
