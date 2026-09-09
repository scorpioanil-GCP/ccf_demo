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

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final, Protocol, TypeVar, runtime_checkable

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DebtProfile,
    DeclaredArtifact,
    HalfLifeTable,
    OperatorParametersArtifact,
    ProductClassDeclaration,
    ReplayBinding,
)
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.deployment import BootedFabric, build_operator_registry
from ccf.graph.protocols import GraphView, TraversalDepthCapability
from ccf.halflife.debt import DebtAssessment
from ccf.products.contract import (
    AssemblyMode,
    ComputedEmptyFinding,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
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
    ProductInvariantRefusal,
    ServableProduct,
    refuse_over_tolerance,
    run_gates,
)
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.refusal import (
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
    "AssemblyDebtScorerProtocol",
    "GovernedResolver",
    "ProductGateProtocol",
    "ProductNotResolvable",
    "ProjectionPlanFactoryProtocol",
    "RefusalRecorderProtocol",
    "ReplayRefusalRecorder",
    "ResolverOutcome",
    "ServedProductResolverProtocol",
    "build_governed_resolver",
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

    **What arrives as a manifest key rather than as an object.** Four of the
    thirteen — the product class, the request contract, the operator parameter
    sets and the policy bundle — are named by *key* and read off
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
    — are closed as of ``24.11-02``; two remain.** The closed ones are kept in
    this roster rather than deleted from it, because what a composition *used
    to* get wrong is what says why the line that fixes it is load-bearing:

    ``24.10-F-06`` — **CLOSED, ``24.11-02``**
        A product class whose operator set included the **Similarity**
        category — one of whitepaper §7.4's four — could not be served at all.
        :func:`~ccf.deployment.build_operator_registry` was called below with
        no ``similarity_index_version``, which that builder requires exactly
        when a similarity artifact is present (``D-IMPL-38``, and rightly: an
        unversioned index is one replay cannot be held against). There was no
        field here and no argument on :func:`build_governed_resolver`, and the
        registry is built inside :meth:`__call__` — so a deployment had
        nowhere to supply it, and every such call died three frames below a
        composition it had no way to configure. The version is now a
        **deployment-owned field** on this class, defaultless like every other
        (:attr:`similarity_index_version`), handed to that builder unchanged.
        It is a field rather than a value read off some artifact because the
        SDK has **no declaration home for it today**: the deployment that
        measured this — ``examples/s1-01-hello-context-product`` — authors it
        in an *adopter-namespaced* governance document the SDK cannot read,
        and :class:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact`
        carries no ``index_version``. Which of those should become its
        governed home is a live question and deliberately not answered here
        (``D-IMPL-291``, *what this does not decide*). Regressed directly at
        ``tests/products/test_resolver_seam.py::
        test_a_similarity_class_is_servable_only_with_the_declared_index_version``.
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
    ``24.10-F-08``
        The candidate below sets none of ``obligation_in_force``,
        ``source_refresh_recency`` or ``debt_evidence``, and offers no seam
        for them. All three are inside the product's content address, so this
        is not an omission a deployment can repair afterwards: measured, a
        product served for a question landing in ``forced_llm`` says the
        deployment is obliged to do nothing where that deployment's own
        :class:`~ccf.controlplane.artifacts.DebtProfile` binds an obligation.
    ``24.10-F-09``
        ``expires_at``, the gate instant and ``recorded_at`` all derive from
        ``request.asked_at``, so a class declaring a **decision instant**
        distinct from the graph boundary finds nothing reads it.

    The remaining two are recorded here rather than fixed here.
    ``D-IMPL-282``: *"No broader API redesign is authorized up front"* — the
    escalation they earn is Dave's ruling to make, and the tests are what go
    loudly red when a seam lands without its finding being closed. ``F-07``
    and ``F-06`` are the two that have had that ruling (``D-IMPL-290``,
    ``D-IMPL-291``), and each was taken **alone**: one repair per row, so that
    what a row moved stays attributable to what a row changed.

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
        similarity_index_version: The version identity this deployment assigns
            to the corpus state its similarity artifact ranks against
            (INV-CH7-27, ``D-IMPL-38``), or ``None`` when
            ``operator_parameter_keys`` names no similarity artifact
            (``24.11-02`` / ``24.10-F-06``). Handed straight to
            :func:`~ccf.deployment.build_operator_registry`, which requires it
            **exactly when** a similarity artifact is present and refuses it
            when one is not — so this field carries the deployment's answer to
            that builder's question rather than a second opinion about it, and
            a mismatched pair is refused there, by the message that already
            explains why an unversioned index is one replay cannot be held
            against.

            **Deployment-owned and therefore defaultless**, on
            ``product_gate``'s reasoning: ``None`` is a deployment stating that
            it ranks against no index, not a value this class assumed on its
            behalf. The SDK cannot mint one — a version derived from the
            parameters artifact's own pin would be identical across two
            different corpus boundaries, which is precisely the identity the
            determinism contract exists to distinguish.
        policy_bundle_key: The key whose pinned version becomes the admitted
            bundle version and the product's policy binding.
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
    similarity_index_version: str | None
    policy_bundle_key: str
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

        view = self.fabric.handle.reader.as_of(
            tenant_id=self.fabric.tenant_id, at=request.asked_at
        )
        operators = build_operator_registry(
            parameters=self._operator_parameters(),
            view=view,
            pins=self.fabric.pins,
            policy_bundle_key=self.policy_bundle_key,
            # `24.11-02` / `24.10-F-06` (`D-IMPL-38`). Absent this argument a
            # product class whose operator set includes the **Similarity**
            # category — one of whitepaper §7.4's four — could not be served
            # at all: this builder requires the version exactly when a
            # similarity artifact is present, and refused every such call
            # three frames below a composition that had nowhere to supply it.
            #
            # Passed unconditionally, `None` included, rather than folded in
            # only when a similarity artifact is present. The builder already
            # refuses BOTH mismatches by name — a version with no artifact,
            # and an artifact with no version — and a conditional here would
            # be this composition deciding which of the two halves the
            # deployment meant, from the same material the builder reads.
            # `None` is the deployment's positive statement that it ranks
            # against no index, and it reaches the builder as one.
            similarity_index_version=self.similarity_index_version,
        )
        required = tuple(declaration.required_operator_keys)
        execution = ProjectionEngine(
            reader=self.fabric.handle.reader, registry=operators
        ).execute(
            plan=self.plan_factory(required=required, request=effective_request),
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

        registered = self._register(declaration)
        policy_version = self.fabric.pins.version_for(self.policy_bundle_key)
        candidate = ContextProductContract(
            schema_name=registered.schema_name,
            schema_version=registered.schema_version,
            plan_id=execution.plan_id,
            tenant_id=self.fabric.tenant_id,
            temporal_boundary=request.asked_at,
            expires_at=request.asked_at
            + timedelta(seconds=self.product_ttl_seconds),
            ttl_anchor=registered.ttl_anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(required),
                policy_bundle_versions=frozenset({policy_version}),
                graph_snapshot_at=request.asked_at,
                # 24.5-L-02: the head the engine read once before its first
                # query, beside the temporal anchor and never inside it.
                store_snapshot_pin=execution.store_snapshot_pin,
            ),
            payload=execution.projection.payload,
            # 24.6-05 (`24.6-L-06`, `D-IMPL-255` (2)): the scorer is told what
            # the execution observed about its own search, so that D_c is
            # derived from evidence rather than from how many rows came back.
            debt=self.debt_scorer(
                view=execution.view, evidence=ExecutionEvidence.of(execution)
            ),
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

        gated = run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=request.asked_at,
            registry=self.control_plane,
            product_class=registered,
            source_attestation=execution.source_attestation,
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
            store_snapshot_pin=execution.store_snapshot_pin,
            debt=candidate.debt,
            computed_empty=candidate.computed_empty,
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
            )

        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key=self.policy_bundle_key, version=policy_version),
                *applied,
            ),
            assembly_mode=registered.assembly_mode,
            recorded_at=request.asked_at,
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

    # --- the one minting seam ----------------------------------------------

    def _record_refusal(
        self,
        *,
        envelope: RefusalEnvelope,
        execution: ExecutionResult | None,
        request: ProductRequest,
        perspective: Perspective,
        policy_bindings: tuple[PolicyBinding, ...] = (),
        resolution: EffectiveRequest | ResolutionNotApplicable,
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

    def _operator_parameters(self) -> dict[str, OperatorParametersArtifact]:
        """The adopter-side idiom: name your own keys, no type filtering."""
        return {
            key: self._artifact(key, OperatorParametersArtifact)
            for key in self.operator_parameter_keys
        }

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


def build_governed_resolver(
    *,
    fabric: BootedFabric,
    control_plane: ControlPlaneProtocol,
    product_class_key: str,
    request_contract_key: str,
    operator_parameter_keys: tuple[str, ...],
    policy_bundle_key: str,
    plan_factory: ProjectionPlanFactoryProtocol,
    max_ttl_seconds: int,
    product_ttl_seconds: int,
    similarity_index_version: str | None = None,
    artifact_store: ArtifactStoreProtocol | None = None,
    replay_record_class: str | None = None,
    query_pin_class: str | None = None,
    artifact_store_root: Path | None = None,
    half_life_key: str | None = None,
    debt_profile_key: str | None = None,
    declared_completeness: Decimal | None = None,
    declared_semantic_consistency: Decimal | None = None,
    debt_scorer: AssemblyDebtScorerProtocol | None = None,
    product_gate: ProductGateProtocol | None = None,
    constraint_resolver: PolicyConstraintResolver | None = None,
    capabilities: tuple[TechnicalCapability, ...] | None = None,
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
    ``24.11-02``, leaving two. Read
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

    The one that *was* an argument problem is now an argument
    (``24.11-02`` / ``24.10-F-06``, ``D-IMPL-291`` (5)): a deployment
    declaring a **similarity** operator-parameters artifact among
    ``operator_parameter_keys`` passes ``similarity_index_version``, which
    reaches :func:`~ccf.deployment.build_operator_registry` through the
    resolver's own field. It is an *argument* rather than a value read off a
    declaration because the SDK has nowhere for a deployment to declare it —
    :class:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact`
    carries no ``index_version`` and no reserved Control Plane section names
    one — and inventing that home is a ruling rather than a repair. Until one
    exists this argument sits beside ``max_ttl_seconds`` and
    ``product_ttl_seconds``: values only the deployment can author, which the
    SDK will not mint on its behalf.

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
        similarity_index_version: The version identity this deployment assigns
            to the corpus its similarity artifact ranks against
            (``D-IMPL-38``). **Required exactly when**
            ``operator_parameter_keys`` names a similarity artifact, and
            refused when it does not — both by
            :func:`~ccf.deployment.build_operator_registry`, whose two
            refusals this helper deliberately does not restate. Optional
            *here* and defaultless on :class:`GovernedResolver` for
            ``product_gate``'s reason: most deployments rank against no index,
            and this is where the SDK's own choice for them is made rather
            than assumed by the composition (``24.11-02`` / ``24.10-F-06``).
        half_life_key: Manifest key of this deployment's ``λ_c`` table.
        debt_profile_key: Manifest key of its ``D_c`` bands.
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
    refuse_undeclared_class_default(
        schema_name=boot_declaration.schema_name,
        schema_version=boot_declaration.schema_version,
        serve_obligations=boot_declaration.serve_obligations,
        declared=_request_contract_on(fabric, key=request_contract_key),
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
    recorder = ReplayRefusalRecorder(
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
        name for name in DEBT_SCORER_INPUTS if declared[name] is not None
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
            similarity_index_version=similarity_index_version,
            policy_bundle_key=policy_bundle_key,
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
            product_gate=product_gate,
            constraint_resolver=resolution_seam,
            capabilities=technical,
            refusal_recorder=recorder,
            artifact_store=store,
            replay_record_class=record_class,
            query_pin_class=pin_class,
            max_ttl_seconds=max_ttl_seconds,
            product_ttl_seconds=product_ttl_seconds,
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
        similarity_index_version=similarity_index_version,
        policy_bundle_key=policy_bundle_key,
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
        max_ttl_seconds=max_ttl_seconds,
        product_ttl_seconds=product_ttl_seconds,
    )
