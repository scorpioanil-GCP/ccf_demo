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

This module is algorithmic (CINV-03): no LLM client on this path, ever. The
gate sequence and the replay append are the algorithmic half of the
Algorithmic ⇄ Semantic Alternation (whitepaper §7.6.6), and a model call
anywhere in the composition would put an unrecorded, irreproducible step
between a candidate and its content address.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Final, Protocol, TypeVar, runtime_checkable

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DebtProfile,
    DeclaredArtifact,
    HalfLifeTable,
    OperatorParametersArtifact,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.deployment import BootedFabric, build_operator_registry
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.gates import ServableProduct, run_gates
from ccf.products.refusal import RefusalEnvelope, RequestIdentity, envelope_for
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    refuse_request,
)
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionPlan
from ccf.replay.record import PolicyBinding, build_replay_record
from ccf.replay.serve import QueryPinWriter, ReplayWriter, ServedProduct, serve

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEBT_SCORER_INPUTS",
    "AssemblyDebtScorerProtocol",
    "GovernedResolver",
    "ProductNotResolvable",
    "ProjectionPlanFactoryProtocol",
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
    """

    def __call__(self, *, view: GraphView) -> DebtAssessment:
        """Assess ``D_c`` over the graph state this question assembled."""
        ...


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
        policy_bundle_key: The key whose pinned version becomes the admitted
            bundle version and the product's policy binding.
        plan_factory: How this deployment builds Π for one question.
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
    plan_factory: ProjectionPlanFactoryProtocol
    debt_scorer: AssemblyDebtScorerProtocol
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
        2. **The request is checked before the graph is touched.** A question
           this class does not answer costs nothing and comes back with a
           reason rather than an approximation.
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
        7. **The gates run**, and their refusal is returned as a value.
        8. **The record is built, then persisted, and only a completed append
           yields a delivery.** No branch here reaches a served product without
           a recorded decision, because :func:`~ccf.replay.serve.serve` has
           none to offer.

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
                uncaught. A failure to record is a failure to serve.
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

        # THE DOOR, and this composition is the resolver standing at it. The
        # comparison the two shipped doors cannot make, because neither holds
        # the registered class it compares against (`D-IMPL-121`).
        violation = refuse_request(
            request=request, declared=self._request_contract(declaration)
        )
        if violation is not None:
            # No lineage: a request-conformity verdict is reached before the
            # graph is touched and *has* none. `envelope_for` refuses one here,
            # which is what makes the assembly-boundary split structural.
            return envelope_for(violation, request=identity)

        view = self.fabric.handle.reader.as_of(
            tenant_id=self.fabric.tenant_id, at=request.asked_at
        )
        operators = build_operator_registry(
            parameters=self._operator_parameters(),
            view=view,
            pins=self.fabric.pins,
            policy_bundle_key=self.policy_bundle_key,
        )
        required = tuple(declaration.required_operator_keys)
        execution = ProjectionEngine(
            reader=self.fabric.handle.reader, registry=operators
        ).execute(
            plan=self.plan_factory(required=required, request=request),
            perspective=perspective,
            tenant_id=self.fabric.tenant_id,
            temporal_boundary=request.asked_at,
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
            debt=self.debt_scorer(view=execution.view),
        )

        gated = run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=request.asked_at,
            registry=self.control_plane,
            product_class=registered,
            source_attestation=execution.source_attestation,
        )
        if not isinstance(gated, ServableProduct):
            # A refusal is a value, and it travels with the lineage the
            # candidate claimed — a gate refusal has a candidate behind it, so
            # saying it has no lineage would be a different and false claim.
            return envelope_for(
                gated, request=identity, pre_assembly_lineage=candidate.lineage
            )

        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key=self.policy_bundle_key, version=policy_version),
            ),
            assembly_mode=registered.assembly_mode,
            recorded_at=request.asked_at,
            request=request,
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
        """
        artifact = self.fabric.artifacts.get(self.request_contract_key)
        if isinstance(artifact, DeclaredArtifact):
            return ProductRequestContract.from_declared(artifact)
        return self._artifact(self.request_contract_key, ProductRequestContract)

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
    artifact_store: ArtifactStoreProtocol,
    replay_record_class: str,
    query_pin_class: str,
    max_ttl_seconds: int,
    product_ttl_seconds: int,
    half_life_key: str | None = None,
    debt_profile_key: str | None = None,
    declared_completeness: Decimal | None = None,
    declared_semantic_consistency: Decimal | None = None,
    debt_scorer: AssemblyDebtScorerProtocol | None = None,
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
            seam stays substrate-agnostic — selecting a file-backed store from
            a declared path is the calling surface's act, not this one's.
        replay_record_class: Artifact class replay records are filed under.
        query_pin_class: Artifact class executed-query bytes are filed under.
        max_ttl_seconds: The class's TTL ceiling.
        product_ttl_seconds: A served product's own lifetime. Two figures, and
            they stay two.
        half_life_key: Manifest key of this deployment's ``λ_c`` table.
        debt_profile_key: Manifest key of its ``D_c`` bands.
        declared_completeness: The ``C`` this deployment asserts, in ``[0, 1]``.
        declared_semantic_consistency: The ``S`` it asserts, in ``[0, 1]``.
        debt_scorer: A conforming scorer that **overrides** the reference.

    Returns:
        The composed resolver, ready to be handed to a delivery surface.

    Raises:
        TypeError: both a scorer and the material to build one were supplied,
            or neither was. An argument-shape mistake, so the exception Python
            already reserves for one — and never a governed refusal, because
            nobody asked a question yet.
        ProductNotResolvable: ``half_life_key`` or ``debt_profile_key`` names no
            artifact on the booted fabric, or names one of another class.
        ValueError: a declared factor lies outside ``[0, 1]``. Raised by
            :class:`~ccf.products.debt_scorer.DeclaredFactor`, where the value
            was authored, rather than three frames later.
    """
    # Keyed by name rather than zipped against :data:`DEBT_SCORER_INPUTS`
    # positionally: a positional pairing goes on running after somebody reorders
    # the constant, and reports the wrong argument in both refusals below.
    # `tests/products/test_resolver_defaults.py::test_the_named_inputs_are_this_helper_s_own_optional_parameters`
    # holds the constant and this signature to each other in both directions.
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
            policy_bundle_key=policy_bundle_key,
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
            artifact_store=artifact_store,
            replay_record_class=replay_record_class,
            query_pin_class=query_pin_class,
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
        artifact_store=artifact_store,
        replay_record_class=replay_record_class,
        query_pin_class=query_pin_class,
        max_ttl_seconds=max_ttl_seconds,
        product_ttl_seconds=product_ttl_seconds,
    )
