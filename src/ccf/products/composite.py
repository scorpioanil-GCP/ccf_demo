"""Composite Context Products — the swarm pattern's composition surface.

**SDK-defined** (CLAUDE.md §11). The ruling of record is
``docs/DECISIONS.md`` **D-IMPL-336** (Dave, 2026-09-13) and its two
amendments:

    *"Skills produce governed Context Products. Agents orchestrate skills.
    Composite Context Products declare the child Context Product classes they
    require."* — and the foundation under it, *"Agents have skills; Context
    Products have state."*

The reusable unit is the **skill**: a Covenant Skill builds covenant context
for a credit memo, a surveillance workflow, an onboarding workflow or a
refinancing workflow, and the Context Product is that skill's governed output
**for one request**. A composite therefore depends on Context Product
*contracts*, never on named skill implementations.

**This is the aggregate-product surface `D-IMPL-104` deferred.** That entry
(Dave, 2026-08-11) ruled the *meaning* of composite debt — per-factor maximum
across constituents — and waited: *"Implementation can wait until the surface
appears; the meaning cannot."* The combinator it predicted is
:func:`~ccf.halflife.debt.compose_debt_factors`, one pure function beside
``context_debt`` adding zero weights, and this module is what calls it.

What this module is, and the three things it is not
----------------------------------------------------

It resolves a declared requirement to a granted skill, admits what that skill
served, and composes the admitted set. It is **not** a scheduler, **not** a DAG
runtime, and **not** an orchestrator. Running child skills concurrently is the
harness's, exactly as the agent loop is (CLAUDE.md §7.3); the SDK ships the
declaration, the resolution, the admission and the composition, and schedules
nothing.

Admission is a capability, not a convention
--------------------------------------------

:class:`AdmittedChild` is constructed only by :meth:`CompositeAdmissionGate.
admit`. Holding one *is* the evidence the checks ran, which is why
:func:`compose_children` takes this type and not a contract, a payload or a
:class:`~ccf.products.door.DoorOutcome`. The precedent is exact —
:class:`~ccf.peering.admission.AdmittedProduct` guards L2's federated entrance
the same way.

**The strength of that claim, stated accurately.** The token makes the bypass
unreachable through the **supported interfaces** — import, constructor,
subclass — and a runtime check fires when one is attempted. It is **not**
absolute unforgeability: Python admits ``object.__new__``, attribute injection
and module patching, and no token defends against those. The honest claim is
the one ``AdmittedProduct`` makes, and it is enough for the property that
matters here, which is that *"compose the unauthorized child and filter it
afterwards"* has no supported spelling.

That property is load-bearing because of ``CXR-G22``: a post-filter and a
pre-filter return **the same hits**, so the served payload cannot distinguish
them. **A correct-looking final payload does not prove the path was
authorized.**

Eligibility authority follows the producing fabric, not the skill label
-----------------------------------------------------------------------

A ``local_callable``, ``tool``, ``mcp`` or ``peering`` label says how bytes
were fetched. It does not say whose Control Plane knows the entities'
invalidation state. Where the producing fabric is this one, the local
:class:`~ccf.controlplane.invalidation.EntityInvalidationRegister` is
authoritative (``D-IMPL-334``/``D-IMPL-335``, reused — no second invalidation
mechanism is built). Where it is another fabric, the producer's signed
:class:`~ccf.peering.eligibility.EligibilityAssertion` is, and **local-register
silence can never establish remote eligibility**: silence is *don't know*, and
collapsing that into *pass* is the measurement failure this project's reading
rules exist to prevent.

Errors: raised vs returned
--------------------------

Both shapes, on this tree's standing distinction.
:class:`ChildAdmissionBypassError` and :class:`AmbiguousProducerError` are
**raised**: both are deployment defects — a caller reaching past the gate, and
an agent granted two producers of one class. Every refusal about a *product* is
**returned** as a value, so it cannot be swallowed by a bare ``except`` and so
it can be recorded.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from pydantic import Field

from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.controlplane.registry import ControlPlaneProtocol
from decimal import Decimal

from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import compose_debt_factors
from ccf.peering.eligibility import (
    ELIGIBILITY_ASSERTION_HEADER,
    EligibilityAssertion,
    EligibilityAssertionMalformed,
    decode_eligibility_assertion,
)
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.gates import GateRefusal, refuse_dependency_invalidation
from ccf.replay.record import CHILD_ADMITTED, ChildResolution
from ccf.skills.catalog import NO_PRODUCT_CLASS, SkillCatalogEntry

__ccf_mode__ = "algorithmic"

__all__ = [
    "ELIGIBILITY_LOCAL_REGISTER",
    "ELIGIBILITY_PRODUCER_ATTESTED",
    "GATE_CHILD_ADMISSION",
    "AdmittedChild",
    "AmbiguousProducerError",
    "ChildAdmissionBypassError",
    "ChildAdmissionRefusal",
    "ChildCandidate",
    "CompositeAdmissionGate",
    "CompositionOutcome",
    "compose_children",
    "ProducedElsewhere",
    "ProducedHere",
    "ProducingFabric",
    "resolve_producing_grant",
]

#: The gate identifier every child-admission refusal carries.
GATE_CHILD_ADMISSION: Final = "child_admission"

#: ``eligibility_basis`` when this fabric's own register was authoritative.
ELIGIBILITY_LOCAL_REGISTER: Final = "local-register"

#: ``eligibility_basis`` when the producing fabric attested it.
ELIGIBILITY_PRODUCER_ATTESTED: Final = "producer-attested"

#: A strength factor at full strength. Not a tunable and not a threshold: the
#: identity element of the per-factor minimum, used where a declared absence
#: constrains only completeness.
_UNIT = Decimal(1)


class ChildAdmissionBypassError(TypeError):
    """An admitted child was constructed outside the admission gate."""


class AmbiguousProducerError(RuntimeError):
    """Two or more in-force grants declare they produce one class.

    Raised, not returned: this is a **deployment** fact — an agent was granted
    two producers of the same class — and not a statement about any product.

    **No tie-breaker is applied, by ruling** (`D-IMPL-336` Amendment 2). Any
    rule the SDK invented — grant order, name sort, most recent — would make
    the composite's behavior, and its replay, depend on something the
    deployment never declared. Interchangeability is instead proven by
    **substitution**: grant A and serve, revoke A and grant B, and observe the
    requirement, the admission path and the composite contract unchanged.
    """


class ChildAdmissionRefusal(GateRefusal):
    """A governed "no" about one child. Returned, never raised.

    Attributes:
        product_class: The requirement this refusal is about.
        reason: The machine-readable cause — one of the ``outcome_status``
            vocabulary a :class:`~ccf.replay.record.ChildResolution` records.
        child_content_address: The rejected product's address **when one is
            known**. ``None`` only when no product was produced at all.

            **A product produced but rejected is not a product that never
            existed** (`D-IMPL-336` Amendment 2): its known identity is
            retained here, and in replay, so an admission failure cannot be
            mistaken for an absence. Disclosure of that identity in a *served*
            payload remains the deployment's policy call; retention in replay
            is not optional.
    """

    product_class: str
    reason: str
    # ``False`` — a generation boundary, not transparent. A refusal that
    # omitted the key would make "no product was produced" and "a product was
    # produced, rejected, and its identity dropped" the same artifact, which is
    # exactly the distinction Amendment 2 ruled must survive.
    child_content_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )


@dataclass(frozen=True)
class ProducingFabric:
    """Which fabric produced a child, and what that implies for eligibility.

    Not the skill type. ``ProducedHere`` and ``ProducedElsewhere`` are the two
    answers that change *whose register decides*, and a deployment states which
    applies rather than the SDK inferring it from a transport label.
    """

    fabric_id: str


@dataclass(frozen=True)
class ProducedHere(ProducingFabric):
    """This fabric produced the child; the local register is authoritative."""


@dataclass(frozen=True)
class ProducedElsewhere(ProducingFabric):
    """Another fabric produced it; only its signed attestation can establish
    eligibility, and the local register may refuse but never authorize."""

    protected_header: Mapping[str, object]


@dataclass(frozen=True)
class ChildCandidate:
    """One served child, with everything admission needs to judge it.

    ``contract`` is the typed product the child's own ``deliver()`` served, and
    ``content_address`` is what its door reported. The gate **recomputes** the
    address from the contract rather than trusting the reported one, on the
    ``DoorOutcome`` discipline: a consumer's hash of the producer's bytes is
    the check, and a value taken on faith checks nothing.
    """

    requirement: ChildRequirement
    contract: ContextProductContract
    content_address: str
    fabric: ProducingFabric
    skill_name: str
    skill_version: str
    grant_hash: str
    touched_entities: tuple[str, ...] | None = None


_CHILD_ADMISSION_TOKEN = object()


class AdmittedChild:
    """A child this composite's Control Plane has admitted.

    Not constructible outside :meth:`CompositeAdmissionGate.admit` through any
    supported interface. Holding one is the evidence every check ran — which is
    why :func:`compose_children` takes this type and nothing weaker.
    """

    __slots__ = ("_candidate", "_eligibility_basis", "_factors")

    def __init__(
        self,
        candidate: ChildCandidate,
        eligibility_basis: str,
        factors: DebtFactors,
        token: object,
    ) -> None:
        if token is not _CHILD_ADMISSION_TOKEN:
            raise ChildAdmissionBypassError(
                "AdmittedChild is constructed only by"
                " ccf.products.composite.CompositeAdmissionGate.admit; child"
                " admission is the only path by which a served child product"
                " becomes composable (D-IMPL-336). Composing first and"
                " filtering afterwards is the CXR-G22 failure: a post-filter"
                " and a pre-filter return the same hits, so the payload cannot"
                " tell them apart"
            )
        self._candidate = candidate
        self._eligibility_basis = eligibility_basis
        self._factors = factors

    @property
    def candidate(self) -> ChildCandidate:
        """What was admitted, with its resolution provenance."""
        return self._candidate

    @property
    def contract(self) -> ContextProductContract:
        """The admitted child's typed contract."""
        return self._candidate.contract

    @property
    def eligibility_basis(self) -> str:
        """Which authority established eligibility — recorded, not assumed.

        A local child's eligibility comes from this tenant's register; a peered
        child's from the producer's attestation. Those are different evidence
        with different trust, and an auditor must be able to tell which
        authorized this child. Recording only *"eligible"* would make them
        indistinguishable.
        """
        return self._eligibility_basis

    @property
    def factors(self) -> DebtFactors:
        """The child's assessed F, C and S — never a scalar.

        The composite's debt is the per-factor minimum, so a record carrying
        only each child's ``D_c`` could not re-derive it.
        """
        return self._factors


def resolve_producing_grant(
    requirement: ChildRequirement,
    bound_skills: Mapping[str, SkillCatalogEntry],
) -> SkillCatalogEntry | None:
    """Find the in-force grant whose entry produces ``requirement``'s class.

    Resolution is **class to skill, never skill to class**: a requirement that
    could name an implementation would make the composite depend on the thing
    this pattern exists to decouple from.

    Returns:
        The one matching entry, or ``None`` when no granted skill produces the
        class. ``None`` is a requirement-level outcome — required refuses, and
        optional takes its declared absence treatment.

    Raises:
        AmbiguousProducerError: two or more granted entries produce it.
    """
    candidates = [
        entry
        for entry in bound_skills.values()
        if entry.produces != NO_PRODUCT_CLASS
        and entry.produces == requirement.product_class
    ]
    if not candidates:
        return None
    if len(candidates) > 1:
        names = sorted(entry.name for entry in candidates)
        raise AmbiguousProducerError(
            f"{len(candidates)} in-force grants declare they produce"
            f" {requirement.product_class!r} ({', '.join(names)}); this build"
            " refuses rather than applying a tie-breaker, because any rule the"
            " SDK chose would make composition and replay depend on something"
            " the deployment never declared (D-IMPL-336). Interchangeability is"
            " proven by substitution, not by simultaneous grant"
        )
    return candidates[0]


class CompositeAdmissionGate:
    """The one gate every child passes, whatever produced it.

    **Uniform by construction.** The common checks below run over every child
    from every skill type; the cross-boundary checks run *in addition* for a
    child produced elsewhere. The asymmetry is never a fast path — a locally
    produced child is never exempted from a common check on the grounds that it
    was produced locally, because *"the composite should not care how a child
    was constructed"* is only true if it checks them the same way.

    The common checks, in order, first refusal returned:

    1. **Class match** — the child is the class the requirement named.
    2. **Version compatibility** — inside the requirement's declared lane.
    3. **Reconstruction instant** — the child answered *this* composition's
       ``asked_at``. Not adjusted, not re-requested, not "close enough".
    4. **Content address** — recomputed from the contract, never trusted.
    5. **Assessable debt** — the child carries a debt assessment. *Unknown debt
       is not zero*: a child with none is refused rather than composed with
       assumed-good factors.
    6. **Eligibility** — from the authority the producing fabric determines.
    """

    def __init__(
        self,
        *,
        tenant_id: str,
        consumer_scope: str,
        registry: ControlPlaneProtocol,
    ) -> None:
        self._tenant_id = tenant_id
        self._consumer_scope = consumer_scope
        self._registry = registry

    def admit(
        self,
        *,
        candidate: ChildCandidate,
        asked_at: datetime,
        composition_invocation: str,
    ) -> AdmittedChild | ChildAdmissionRefusal:
        """Run every check over ``candidate``; see the class docstring.

        Args:
            candidate: The served child and its resolution provenance.
            asked_at: **The composite's single reconstruction instant.** Passed
                to every child and compared against what each answered.
            composition_invocation: This composition's invocation identity.
                Binds a peered child's eligibility attestation so a previously
                valid one cannot be replayed into a later composition.
        """
        requirement = candidate.requirement
        contract = candidate.contract
        address = candidate.content_address

        def refuse(reason: str, detail: str) -> ChildAdmissionRefusal:
            return ChildAdmissionRefusal(
                gate=GATE_CHILD_ADMISSION,
                detail=detail,
                product_class=requirement.product_class,
                reason=reason,
                child_content_address=address,
            )

        if contract.schema_name != requirement.product_class:
            return refuse(
                "class-mismatch",
                f"requirement names {requirement.product_class!r} and the"
                f" child served {contract.schema_name!r}; a skill whose"
                " `produces` disagrees with what it emitted cannot satisfy it",
            )

        if not requirement.accepts(child_version=contract.schema_version):
            return refuse(
                "version-incompatible",
                f"child is {contract.schema_name}@{contract.schema_version} and"
                f" this composite composes over {requirement.compatible_from}"
                " and later on the same major lane",
            )

        if contract.temporal_boundary != asked_at:
            return refuse(
                "as-of-mismatch",
                f"child answered as of {contract.temporal_boundary.isoformat()}"
                f" and this composition asked as of {asked_at.isoformat()};"
                " a composite has exactly one reconstruction instant, and a"
                " child from another cannot be composed",
            )

        recomputed = content_hash(contract)
        if recomputed != address:
            return refuse(
                "address-mismatch",
                f"the child's door reported {address!r} and its canonical bytes"
                f" hash to {recomputed!r}; the address is recomputed here and"
                " never trusted from the producer",
            )

        if contract.debt is None:
            return refuse(
                "debt-unassessable",
                "the child carries no debt assessment; unknown debt is not"
                " zero, and composing it would give the parent assumed-good"
                " factors it has no evidence for (D-IMPL-336)",
            )

        established = self._establish_eligibility(
            candidate=candidate,
            asked_at=asked_at,
            composition_invocation=composition_invocation,
        )
        if isinstance(established, tuple):
            reason, detail = established
            return refuse(reason, detail)
        basis_or_refusal = established

        return AdmittedChild(
            candidate,
            basis_or_refusal,
            contract.debt.factors,
            _CHILD_ADMISSION_TOKEN,
        )

    def _establish_eligibility(
        self,
        *,
        candidate: ChildCandidate,
        asked_at: datetime,
        composition_invocation: str,
    ) -> str | tuple[str, str]:
        """Answer *may this child still serve*, from the right authority.

        Returns the ``eligibility_basis`` on a pass, or a ``(reason, detail)``
        pair the caller renders as a refusal — a pair rather than a refusal
        value so this method never has to know the requirement it is judging.
        """
        fabric = candidate.fabric
        contract = candidate.contract

        # The local register can always REFUSE — anything this fabric knows to
        # be superseded is superseded whoever produced it. What it can never do
        # is SUPPLY eligibility for a product built elsewhere.
        local_refusal = refuse_dependency_invalidation(
            contract,
            registry=self._registry,
            touched_entities=candidate.touched_entities,
        )
        if local_refusal is not None:
            return (
                "ineligible",
                "this fabric's invalidation register refuses the child:"
                f" {local_refusal.detail}",
            )

        if isinstance(fabric, ProducedHere):
            return ELIGIBILITY_LOCAL_REGISTER

        if not isinstance(fabric, ProducedElsewhere):
            return (
                "ineligible",
                "the producing fabric is undeclared, so no authority for this"
                " child's eligibility can be identified; the local register's"
                " silence is not a pass (D-IMPL-336)",
            )

        try:
            assertion = decode_eligibility_assertion(
                fabric.protected_header.get(ELIGIBILITY_ASSERTION_HEADER)
            )
        except EligibilityAssertionMalformed as error:
            return ("eligibility-evidence-missing", str(error))

        mismatch = self._binding_mismatch(
            assertion,
            candidate=candidate,
            asked_at=asked_at,
            composition_invocation=composition_invocation,
        )
        if mismatch is not None:
            return ("eligibility-evidence-mismatch", mismatch)

        if not assertion.eligible:
            return (
                "ineligible",
                "the producing fabric attests this child is NOT eligible as of"
                f" {assertion.checked_at.isoformat()}; a signed negative is a"
                " governed answer and is honored",
            )
        return ELIGIBILITY_PRODUCER_ATTESTED

    def _binding_mismatch(
        self,
        assertion: EligibilityAssertion,
        *,
        candidate: ChildCandidate,
        asked_at: datetime,
        composition_invocation: str,
    ) -> str | None:
        """Check every binding. Any one wrong is evidence about another thing.

        Each mismatch names both sides, on the refusal discipline this tree
        holds: the caller re-derives neither operand. **All five bindings are
        checked** — an assertion lifted from another product, another instant,
        another producer, another consumer or another invocation is refused,
        and the last of those is what makes replay detectable.
        """
        if assertion.child_content_address != candidate.content_address:
            return (
                "the eligibility assertion is about"
                f" {assertion.child_content_address!r} and this child is"
                f" {candidate.content_address!r}"
            )
        if assertion.requested_as_of != asked_at:
            return (
                "the eligibility assertion was made for reconstruction instant"
                f" {assertion.requested_as_of.isoformat()} and this composition"
                f" asked as of {asked_at.isoformat()}"
            )
        if assertion.producer != candidate.fabric.fabric_id:
            return (
                "the eligibility assertion names producer"
                f" {assertion.producer!r} and the child came from"
                f" {candidate.fabric.fabric_id!r}"
            )
        if assertion.consumer_scope != self._consumer_scope:
            return (
                "the eligibility assertion was minted for consumer"
                f" {assertion.consumer_scope!r} and this gate admits for"
                f" {self._consumer_scope!r}; an assertion is not bearer"
                " currency"
            )
        if assertion.composition_invocation != composition_invocation:
            return (
                "the eligibility assertion was minted for composition"
                f" {assertion.composition_invocation!r} and this is"
                f" {composition_invocation!r}; an assertion is single-use, and"
                " re-presenting a previously valid one is replay"
            )
        return None


@dataclass(frozen=True)
class CompositionOutcome:
    """What a composition produced: composed factors, or a refusal, plus rows.

    **The rows are present either way.** A composite that refused still records
    every requirement and its disposition, because a requirement that produced
    nothing and left no row would be indistinguishable from one that was never
    declared — the silent omission this surface exists to prevent.
    """

    factors: DebtFactors | None
    resolutions: tuple[ChildResolution, ...]
    refusal: ChildAdmissionRefusal | None

    @property
    def served(self) -> bool:
        """Whether the composite may be assembled from this outcome."""
        return self.refusal is None


def compose_children(
    *,
    own_factors: DebtFactors,
    requirements: Sequence[ChildRequirement],
    outcomes: Mapping[str, AdmittedChild | ChildAdmissionRefusal | None],
) -> CompositionOutcome:
    """Compose an admitted child set, or refuse, and record every requirement.

    Walks ``requirements`` **in declaration order** — the order rows appear in
    replay and the order a refusal names, which is why
    :attr:`~ccf.products.contract.RegisteredProductClass.requires` is a tuple
    and not a set. An unordered collection cannot carry an order, and this
    tree has shipped that defect twice.

    Args:
        own_factors: What the parent itself assembled.
        requirements: The composite class's declared requirements.
        outcomes: Per ``product_class``: the admitted child, the refusal that
            came back, or ``None`` for a requirement no granted skill produced.

    Returns:
        A :class:`CompositionOutcome`. ``factors`` is ``None`` exactly when
        ``refusal`` is set.
    """
    rows: list[ChildResolution] = []
    admitted: list[DebtFactors] = []
    refusal: ChildAdmissionRefusal | None = None

    for requirement in requirements:
        outcome = outcomes.get(requirement.product_class)

        if isinstance(outcome, AdmittedChild):
            rows.append(_row_for_admitted(requirement, outcome))
            admitted.append(outcome.factors)
            continue

        if isinstance(outcome, ChildAdmissionRefusal):
            # A product WAS produced and then rejected. Its known identity is
            # retained (D-IMPL-336 Amendment 2): discarding it would make an
            # admission failure indistinguishable from an absence.
            rows.append(
                ChildResolution(
                    required_product_class=requirement.product_class,
                    required=requirement.required,
                    outcome_status=_status_for(outcome.reason),
                    child_content_address=outcome.child_content_address,
                    refusal_ref=outcome.reason,
                )
            )
            if requirement.required and refusal is None:
                refusal = outcome
            continue

        # Nothing was produced at all — no invented fields.
        if requirement.required:
            rows.append(
                ChildResolution(
                    required_product_class=requirement.product_class,
                    required=True,
                    outcome_status="no-producing-skill",
                )
            )
            if refusal is None:
                refusal = ChildAdmissionRefusal(
                    gate=GATE_CHILD_ADMISSION,
                    detail=(
                        "no in-force grant declares it produces"
                        f" {requirement.product_class!r}, and the requirement"
                        " is required; a composite never silently omits one"
                    ),
                    product_class=requirement.product_class,
                    reason="no-producing-skill",
                )
            continue

        # Optional and declared absent. The treatment is the CLASS's, and the
        # SDK holds no default — what a missing optional input costs is a
        # domain judgement (D-IMPL-336, D-IMPL-38).
        treatment = requirement.absence_treatment
        assert treatment is not None  # ChildRequirement guarantees it
        rows.append(
            ChildResolution(
                required_product_class=requirement.product_class,
                required=False,
                outcome_status="optional-absent",
            )
        )
        admitted.append(
            DebtFactors(
                freshness=_UNIT,
                completeness=treatment.completeness_when_absent,
                semantic_consistency=_UNIT,
            )
        )

    if refusal is not None:
        return CompositionOutcome(
            factors=None, resolutions=tuple(rows), refusal=refusal
        )
    return CompositionOutcome(
        factors=compose_debt_factors(own_factors, admitted),
        resolutions=tuple(rows),
        refusal=None,
    )


def _status_for(reason: str) -> str:
    """Map an admission cause to its closed ``outcome_status`` token.

    The four absences stay distinct (D-IMPL-336 Amendment 2): an eligibility
    failure and an authorization failure are governed events, and letting
    either read as ``optional-absent`` would present a governance failure as a
    data gap.
    """
    if reason == "ineligible":
        return "ineligible"
    if reason == "unauthorized":
        return "unauthorized"
    if reason == "no-producing-skill":
        return "no-producing-skill"
    return "rejected-at-admission"


def _row_for_admitted(
    requirement: ChildRequirement, admitted: AdmittedChild
) -> ChildResolution:
    """Every field admission checked, recorded — nothing re-derived later."""
    candidate = admitted.candidate
    contract = admitted.contract
    debt = contract.debt
    assert debt is not None  # admission refuses an unassessable child
    return ChildResolution(
        required_product_class=requirement.product_class,
        required=requirement.required,
        outcome_status=CHILD_ADMITTED,
        producing_skill_name=candidate.skill_name,
        producing_skill_version=candidate.skill_version,
        grant_hash=candidate.grant_hash,
        child_content_address=candidate.content_address,
        child_schema_name=contract.schema_name,
        child_schema_version=contract.schema_version,
        child_asked_at=contract.temporal_boundary,
        child_graph_snapshot_at=contract.lineage.graph_snapshot_at,
        child_debt=debt.debt,
        child_debt_factors=debt.factors,
        child_policy_bundle_versions=contract.lineage.policy_bundle_versions,
        child_lineage_ref=content_hash(contract.lineage),
        eligibility_basis=admitted.eligibility_basis,
    )
