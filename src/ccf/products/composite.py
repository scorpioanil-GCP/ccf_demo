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
from typing import Final, Literal, Protocol, cast, get_args, runtime_checkable

from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from decimal import Decimal

from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import compose_debt_factors
from ccf.peering.admission import PRODUCER_ASSERTION_HEADER, AdmittedProduct
from ccf.peering.eligibility import (
    ELIGIBILITY_ASSERTION_HEADER,
    EligibilityAssertion,
    EligibilityAssertionMalformed,
    decode_eligibility_assertion,
)
from ccf.products.composition import (
    ConstituentValidity,
    compose_expiry,
    compose_lineage,
    refuse_mixing,
)
from ccf.products.contract import (
    ChildRequirement,
    ConstituentValidityFloors,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
)
from ccf.products.gates import GateRefusal, refuse_dependency_invalidation
from ccf.replay.record import CHILD_ADMITTED, ChildResolution
from ccf.skills.catalog import NO_PRODUCT_CLASS, SkillCatalogEntry
from ccf.skills.grants import BoundSkillView

__ccf_mode__ = "algorithmic"

__all__ = [
    "ELIGIBILITY_LOCAL_REGISTER",
    "ELIGIBILITY_PRODUCER_ATTESTED",
    "GATE_CHILD_ADMISSION",
    "CHILD_REFUSAL_REASONS",
    "EligibilityEvidence",
    "eligibility_evidence_policy_key",
    "ELIGIBILITY_EVIDENCE_POLICY",
    "EligibilityEvidencePolicy",
    "AdmittedChild",
    "AmbiguousProducerError",
    "ChildAdmissionBypassError",
    "ChildAdmissionRefusal",
    "ChildCandidate",
    "ChildInvocation",
    "ChildRefusalReason",
    "CompositeAdmissionGate",
    "CompositeChildResolverProtocol",
    "CompositionOutcome",
    "compose_children",
    "invocation_from_dispatch",
    "LocalFabricAttestor",
    "LocalProvenance",
    "ProvenanceForgeryError",
    "ResolvedProducer",
    "VerifiedPeerProvenance",
    "peer_provenance_from_admitted",
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


#: The closed set of causes composite admission can refuse for (`D-IMPL-336`
#: Amendment 3, F11). A ``Literal`` and not a bare ``str``: the earlier shape
#: let ``reason="unauthorised"`` — one letter from the token the vocabulary
#: reserves — be silently demoted to a generic rejection by ``_status_for``'s
#: catch-all, so whether a governance failure survived into the audit record
#: depended on an undocumented spelling convention.
ChildRefusalReason = Literal[
    "class-mismatch",
    "version-incompatible",
    "as-of-mismatch",
    "address-mismatch",
    "debt-unassessable",
    "ineligible",
    "eligibility-evidence-missing",
    "eligibility-evidence-mismatch",
    "eligibility-evidence-stale",
    "eligibility-bound-undeclared",
    "composition-unwired",
    "tenant-mismatch",
    "provenance-unverified",
    "no-producing-skill",
    "ambiguous-producer",
    "unauthorized",
    "requirement-mismatch",
    "undeclared-outcome",
    "unsupported-outcome",
    "mixing-refused",
]

CHILD_REFUSAL_REASONS: Final[frozenset[str]] = frozenset(get_args(ChildRefusalReason))


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
    reason: ChildRefusalReason
    # `D-IMPL-336` Amendment 3, F9 — TWO addresses, never one.
    #
    # ``reported_content_address`` is what the producer's door claimed.
    # ``verified_content_address`` is what this gate recomputed from the
    # contract's canonical bytes, and is present ONLY when the two agreed.
    #
    # The earlier shape carried one field holding the REPORTED value, so on an
    # ``address-mismatch`` — the one refusal where the gate has just PROVED the
    # reported value wrong — the audit record retained the disproven string as
    # the rejected product's identity. Amendment 2 requires a rejected
    # product's identity to be retained; Amendment 3 requires it not to be a
    # value the gate refuted.
    #
    # Both ``False`` — a generation boundary, not transparent. A refusal that
    # omitted these would make "no product was produced" and "a product was
    # produced, rejected, and its identity dropped" the same artifact.
    reported_content_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    verified_content_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )


class EligibilityEvidencePolicy(CCFContract):
    """How old a producer's eligibility check may be (`D-IMPL-336` Am. 3, F7).

    A **Control Plane artifact**, because both members are values and the SDK
    holds none (``D-IMPL-38``). There is no default and no calibration: a
    deployment that admits peered children declares this, and one that has not
    gets an explicit refusal rather than an invented bound.

    **Validated against the ACTUAL ADMISSION TIME, never against ``asked_at``.**
    That distinction is the whole of the ruling: ``asked_at`` is a
    reconstruction instant and may be historical, so a producer legitimately
    checks eligibility *today* for a request *about last quarter*. Comparing
    the two would refuse every honest peered answer about the past — measured
    on this tree's own fixtures, where ``checked_at`` is correctly later than
    ``asked_at``.

    Attributes:
        max_evidence_age_seconds: How long after ``checked_at`` the producer's
            determination may still authorize an admission.
        permitted_clock_skew_seconds: How far *ahead* of admission time a
            producer's clock may run before its evidence is refused as
            impossible rather than merely fresh.
    """

    max_evidence_age_seconds: int
    permitted_clock_skew_seconds: int

    @field_validator("max_evidence_age_seconds", "permitted_clock_skew_seconds")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                "an evidence-age bound is a duration and cannot be negative;"
                f" got {value}"
            )
        return value


#: The artifact class a deployment registers its evidence bound under.
ELIGIBILITY_EVIDENCE_POLICY = ArtifactClass(
    class_id="ccf.eligibility-evidence-policy", contract=EligibilityEvidencePolicy
)


def eligibility_evidence_policy_key(*, tenant_id: str) -> str:
    """The Control Plane key the bound registers under, per tenant."""
    return f"{tenant_id}/{ELIGIBILITY_EVIDENCE_POLICY.class_id}"


class ProvenanceForgeryError(TypeError):
    """Provenance evidence was constructed outside its minting authority."""


@dataclass(frozen=True)
class _EligibilityRefused:
    """Why eligibility could not be established, as a value.

    A distinct type rather than a ``(reason, detail)`` tuple, because success
    now also returns a pair and ``isinstance(x, tuple)`` would no longer
    discriminate them — the shape of bug this module exists to refuse.
    """

    reason: str
    detail: str


@dataclass(frozen=True)
class EligibilityEvidence:
    """The verified attestation a peered child was admitted on (F7).

    Recorded so replay can name *which* evidence authorized a child. The
    earlier record carried only ``eligibility_basis="producer-attested"``,
    which says an assertion existed and nothing about which one — so a
    reviewer could not re-verify the decision.

    ``checked_at`` is the producer's own eligibility-check instant, kept
    **separate** from the reconstruction instant and from source observation
    times. ``assertion_address`` is the content hash of the verified
    assertion, so the record points at an artifact rather than restating it.
    """

    checked_at: datetime
    assertion_address: str
    producer: str


_LOCAL_PROVENANCE_TOKEN = object()
_PEER_PROVENANCE_TOKEN = object()


class ChildProvenance:
    """Where a child came from, as EVIDENCE rather than as a caller's label.

    `D-IMPL-336` Amendment 3, F3/F6/F16. The earlier shape was a caller-chosen
    dataclass: a deployment wrote ``ProducedHere("anything")`` and the gate
    believed it, or hand-built a ``protected_header`` dict and the gate read a
    "signed" assertion nobody had verified. Relabelling one peered child
    ``ProducedHere`` skipped attestation entirely.

    Both subclasses are now **minted by an authority and unconstructible
    through the supported interfaces otherwise** — the
    :class:`~ccf.peering.admission.AdmittedProduct` pattern, which this tree
    already uses to keep an unverified federated product away from L2.

    **`touched_entities` lives here, not on the candidate.** It is execution
    evidence about what the child actually read, so it must arrive from
    whatever executed the child — never as an optional keyword the assembler
    may omit. Omitting it used to skip the invalidation register while still
    recording that the register had authorized the child.
    """

    __slots__ = ("_touched_entities",)

    def __init__(self, touched_entities: tuple[str, ...]) -> None:
        self._touched_entities = touched_entities

    @property
    def touched_entities(self) -> tuple[str, ...]:
        """The entities the child's execution actually read.

        A tuple, never ``None``: ``()`` is the *verified* claim that the child
        read nothing, and there is no way to express "I did not look" — which
        is the state the register cannot answer for and must refuse.
        """
        return self._touched_entities


class LocalProvenance(ChildProvenance):
    """This fabric produced the child; its own register is authoritative.

    Minted only by :class:`LocalFabricAttestor`, which is itself constructed at
    the composition root from booted state. A caller cannot assert *"produced
    here"* — that claim is the deployment's boot context to make.
    """

    __slots__ = ("_attestor_id",)

    def __init__(
        self, *, attestor_id: str, touched_entities: tuple[str, ...], token: object
    ) -> None:
        if token is not _LOCAL_PROVENANCE_TOKEN:
            raise ProvenanceForgeryError(
                "LocalProvenance is minted only by"
                " ccf.products.composite.LocalFabricAttestor, which is built at"
                " the composition root from booted state. A caller asserting"
                " it produced a child locally is asserting the one thing this"
                " evidence exists to establish (D-IMPL-336 Amendment 3, F6)"
            )
        super().__init__(touched_entities)
        self._attestor_id = attestor_id

    @property
    def attestor_id(self) -> str:
        """Which boot-bound attestor vouched for this child's locality.

        Recorded in replay so the ``local-register`` basis names its source —
        the earlier row asserted an authority and named no one.
        """
        return self._attestor_id


class VerifiedPeerProvenance(ChildProvenance):
    """Another fabric produced it, and its envelope has been VERIFIED.

    Minted only from a peering result whose signature, peer trust and policy
    bindings the existing :class:`~ccf.peering.admission.PeeringAdmissionGate`
    has already checked — see :func:`peer_provenance_from_admitted`. A
    hand-built header dictionary cannot become one of these, which is F16's
    whole requirement.

    ``header`` is therefore the **authenticated** protected header, not a
    caller's mapping: on this tree a JWS protected header is part of the
    signing input, so a member read from a verified envelope is covered by the
    signature exactly as the payload is.
    """

    __slots__ = ("_header", "_peer_id", "_producer")

    def __init__(
        self,
        *,
        peer_id: str,
        producer: str,
        header: Mapping[str, object],
        touched_entities: tuple[str, ...],
        token: object,
    ) -> None:
        if token is not _PEER_PROVENANCE_TOKEN:
            raise ProvenanceForgeryError(
                "VerifiedPeerProvenance is minted only from a verified peering"
                " admission (peer_provenance_from_admitted). A protected"
                " header a caller assembled has had no signature checked, and"
                " reading an eligibility assertion out of it would attest"
                " nothing (D-IMPL-336 Amendment 3, F16)"
            )
        super().__init__(touched_entities)
        self._peer_id = peer_id
        self._producer = producer
        self._header = header

    @property
    def peer_id(self) -> str:
        """The peer whose signature the peering gate verified."""
        return self._peer_id

    @property
    def producer(self) -> str:
        """The producing agent identity the VERIFIED header asserted.

        Taken from the authenticated header rather than from a sibling field
        the caller also wrote — the earlier gate compared
        ``assertion.producer`` against ``candidate.fabric.fabric_id``, both of
        which the same caller supplied, so the check compared a string to
        itself.
        """
        return self._producer

    @property
    def header(self) -> Mapping[str, object]:
        """The authenticated protected header."""
        return self._header


class LocalFabricAttestor:
    """Boot-bound authority for *"this fabric produced it"*.

    Constructed once at the composition root and injected. It holds no
    registry and introduces no fabric-identity axis — **Dave's Amendment 3
    prohibitions are explicit on both** — it is simply the object a deployment
    can only obtain by having booted, so possessing it is what distinguishes
    the fabric's own assembler from a caller passing a string.
    """

    __slots__ = ("_attestor_id",)

    def __init__(self, *, attestor_id: str) -> None:
        self._attestor_id = attestor_id

    def attest(self, *, touched_entities: tuple[str, ...]) -> LocalProvenance:
        """Vouch that this fabric executed the child, and for what it read."""
        return LocalProvenance(
            attestor_id=self._attestor_id,
            touched_entities=tuple(touched_entities),
            token=_LOCAL_PROVENANCE_TOKEN,
        )


def peer_provenance_from_admitted(
    admitted: AdmittedProduct, *, touched_entities: tuple[str, ...]
) -> VerifiedPeerProvenance:
    """Carry a VERIFIED peering admission into composite provenance (F16).

    Takes :class:`~ccf.peering.admission.AdmittedProduct` — a type the peering
    gate alone constructs, and only after signature verification, peer
    entitlement and policy-binding checks. **The argument is the evidence those
    checks ran**, which is what a hand-built header dictionary can never be.

    The header is read off the admitted product rather than passed alongside
    it, so there is no seam at which a caller could substitute an unverified
    mapping for the verified one.

    Raises:
        ProvenanceForgeryError: the admitted product carries no authenticated
            header. Reachable only from an ``AdmittedProduct`` built before
            that member existed; refused rather than treated as "no claims",
            because a peered child with no verifiable header has no
            establishable eligibility (F16 with Amendment 3's *absence is not
            eligible*).
    """
    header = admitted.protected_header
    if header is None:
        raise ProvenanceForgeryError(
            "this AdmittedProduct carries no authenticated protected header, so"
            " nothing read from it could be attributed to the verified peer;"
            " composite provenance requires the verified envelope, not an"
            " envelope-shaped value (D-IMPL-336 Amendment 3, F16)"
        )
    return VerifiedPeerProvenance(
        peer_id=admitted.peer.peer_id,
        producer=str(header.get(PRODUCER_ASSERTION_HEADER, "")),
        header=header,
        touched_entities=tuple(touched_entities),
        token=_PEER_PROVENANCE_TOKEN,
    )


_INVOCATION_TOKEN = object()


class ChildInvocation:
    """Evidence that an ACTUAL grant resolution and skill invocation ran (F4).

    `D-IMPL-336` Amendment 3. The earlier candidate carried ``skill_name``,
    ``skill_version`` and ``grant_hash`` as plain strings the assembler wrote,
    which admission never compared against anything and replay recorded
    verbatim. A child produced by a skill the agent was never granted was
    admitted whenever the contract checks passed, and the record named whatever
    grant the caller typed.

    Minted only by :func:`invocation_from_dispatch`, which takes the resolved
    catalog entry itself — so the identity recorded is the entry's own pinned
    ``artifact_version`` and the grant's own hash, never a caller's spelling of
    them.
    """

    __slots__ = ("_entry_version", "_grant_hash", "_skill_name")

    def __init__(
        self, *, skill_name: str, entry_version: str, grant_hash: str, token: object
    ) -> None:
        if token is not _INVOCATION_TOKEN:
            raise ProvenanceForgeryError(
                "ChildInvocation is minted only by"
                " ccf.products.composite.invocation_from_dispatch, from the"
                " catalog entry a grant actually made effective. Accepting"
                " caller-written skill and grant strings is what let an"
                " ungranted producer be recorded as an authorized one"
                " (D-IMPL-336 Amendment 3, F4)"
            )
        self._skill_name = skill_name
        self._entry_version = entry_version
        self._grant_hash = grant_hash

    @property
    def skill_name(self) -> str:
        """The resolved entry's own name."""
        return self._skill_name

    @property
    def entry_version(self) -> str:
        """The resolved entry's pinned ``artifact_version``."""
        return self._entry_version

    @property
    def grant_hash(self) -> str:
        """The governed binding identity that made the entry effective."""
        return self._grant_hash


_PRODUCER_TOKEN = object()


class ResolvedProducer:
    """The grant AND the entry it made effective, resolved together (**O2**).

    `D-IMPL-336` O2. Amendment 3 replaced the caller's free skill strings with
    a catalog entry, which closed half the hole: the entry was real, and the
    ``grant_hash`` beside it was still whatever the assembler typed. So a child
    produced by a genuinely granted skill could be recorded against a grant
    that authorized something else, or against one that had been revoked, and
    nothing compared the two. The panel's phrase for the residual was exact —
    *"the token replaced free strings but did not bind them"*.

    Minted only by :func:`resolve_producing_grant`, from a
    :class:`~ccf.skills.grants.BoundSkillView` — the ledger's own live view,
    whose constructor is module-private for this same reason (WR-03). Both
    halves therefore come from ledger state at resolution time and a caller
    supplies neither.

    **Unforgeable through the supported interfaces**, which is this module's
    standing threat model and not a claim about ``object.__new__``.
    """

    __slots__ = ("_entry", "_grant_hash")

    def __init__(
        self, *, entry: SkillCatalogEntry, grant_hash: str, token: object
    ) -> None:
        if token is not _PRODUCER_TOKEN:
            raise ProvenanceForgeryError(
                "ResolvedProducer is minted only by"
                " ccf.products.composite.resolve_producing_grant, which reads"
                " both the entry and the grant that put it in force from the"
                " agent's BoundSkillView. Pairing an entry with a"
                " caller-chosen grant hash is what let an authorized producer"
                " be recorded against an unrelated grant (D-IMPL-336 O2)"
            )
        self._entry = entry
        self._grant_hash = grant_hash

    @property
    def entry(self) -> SkillCatalogEntry:
        """The catalog entry the in-force grant resolves to."""
        return self._entry

    @property
    def grant_hash(self) -> str:
        """The hash of the grant that put :attr:`entry` in force."""
        return self._grant_hash


def invocation_from_dispatch(producer: ResolvedProducer) -> ChildInvocation:
    """Record what a real grant resolution produced (F4, **O2**).

    Takes the :class:`ResolvedProducer` :func:`resolve_producing_grant`
    returned — entry and grant together — so neither the version nor the
    authority recorded can disagree with what the ledger holds.

    **The ``grant_hash`` keyword is gone deliberately.** While it existed this
    function would mint authority from any entry plus any string, which is
    precisely what O2 named. There is no compatibility shim: an accepted
    parameter that no longer binds anything is the defect class this work
    exists to repair.
    """
    return ChildInvocation(
        skill_name=producer.entry.name,
        entry_version=producer.entry.artifact_version,
        grant_hash=producer.grant_hash,
        token=_INVOCATION_TOKEN,
    )


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
    provenance: ChildProvenance
    invocation: "ChildInvocation"


_CHILD_ADMISSION_TOKEN = object()


class AdmittedChild:
    """A child this composite's Control Plane has admitted.

    Not constructible outside :meth:`CompositeAdmissionGate.admit` through any
    supported interface. Holding one is the evidence every check ran — which is
    why :func:`compose_children` takes this type and nothing weaker.

    **It also carries WHAT the checks ran against** (`D-IMPL-336` Amendment 3,
    F2/F15). The earlier shape proved admission *happened* and said nothing
    about the requirement, instant or invocation it happened under, so
    :func:`compose_children` had no way to re-bind it and trusted a mapping key
    instead. An admitted child admitted for class A composed under a class-B
    slot; children admitted at two different instants composed together. The
    binding travels with the capability now, and composition re-checks it.
    """

    __slots__ = (
        "_asked_at",
        "_candidate",
        "_eligibility_basis",
        "_evidence",
        "_factors",
        "_invocation",
        "_verified_address",
    )

    def __init__(
        self,
        candidate: ChildCandidate,
        eligibility_basis: str,
        factors: DebtFactors,
        asked_at: datetime,
        composition_invocation: str,
        verified_address: str,
        evidence: "EligibilityEvidence | None",
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
        self._asked_at = asked_at
        self._invocation = composition_invocation
        self._verified_address = verified_address
        self._evidence = evidence

    @property
    def candidate(self) -> ChildCandidate:
        """What was admitted, with its resolution provenance."""
        return self._candidate

    @property
    def contract(self) -> ContextProductContract:
        """The admitted child's typed contract."""
        return self._candidate.contract

    @property
    def requirement(self) -> ChildRequirement:
        """**The requirement this child was admitted AGAINST** (F2).

        Composition compares this to the slot it is being used to satisfy. It
        is not the same question as "which key was it filed under", and the
        earlier code could only ask the second one.
        """
        return self._candidate.requirement

    @property
    def asked_at(self) -> datetime:
        """The reconstruction instant admission ran at (F15).

        A composite has exactly one. Carrying it here is what lets
        :func:`compose_children` assert that, rather than each ``admit`` call
        asserting it about itself and nothing checking they agree.
        """
        return self._asked_at

    @property
    def composition_invocation(self) -> str:
        """The composition invocation admission ran under (F15).

        The anti-replay binding survived per child and dissolved at the
        composition until this field existed.
        """
        return self._invocation

    @property
    def verified_content_address(self) -> str:
        """The address this gate RECOMPUTED and matched — never the reported
        one (F9). Only a verified value is ever labelled as identity."""
        return self._verified_address

    @property
    def eligibility_basis(self) -> str:
        """Which authority established eligibility — recorded, not assumed.

        A local child's eligibility comes from this tenant's register; a peered
        child's from the producer's attestation. Those are different evidence
        with different trust, and an auditor must be able to tell which
        authorized this child.
        """
        return self._eligibility_basis

    @property
    def eligibility_evidence(self) -> "EligibilityEvidence | None":
        """The verified attestation a peered child was admitted on (F7).

        ``None`` for a locally produced child, whose authority is the register
        rather than an assertion. Carried so replay can name *which* evidence
        authorized the child, which the earlier record could not.
        """
        return self._evidence

    @property
    def factors(self) -> DebtFactors:
        """The child's assessed F, C and S — never a scalar.

        The composite's debt is the per-factor minimum, so a record carrying
        only each child's ``D_c`` could not re-derive it.
        """
        return self._factors


def resolve_producing_grant(
    requirement: ChildRequirement,
    bound_skills: BoundSkillView,
) -> ResolvedProducer | None:
    """Find the in-force grant whose entry produces ``requirement``'s class.

    Resolution is **class to skill, never skill to class**: a requirement that
    could name an implementation would make the composite depend on the thing
    this pattern exists to decouple from.

    **The argument is the agent's live** :class:`~ccf.skills.grants.BoundSkillView`
    **and not any mapping** (`D-IMPL-336` **O2**). The looser type was a door
    — a plain dict of entries carries no evidence that any of them was ever
    granted, so "resolved from the in-force grants" was a claim in the
    docstring rather than a property of the call. The view resolves from ledger
    state at access time, so a revoked grant stops producing here immediately.

    Returns:
        A :class:`ResolvedProducer` pairing the one matching entry with the
        grant hash that put it in force, or ``None`` when no granted skill
        produces the class. ``None`` is a requirement-level outcome — required
        refuses, and optional takes its declared absence treatment.

    Raises:
        AmbiguousProducerError: two or more granted entries produce it.
    """
    candidates = [
        name
        for name, entry in bound_skills.items()
        if entry.produces != NO_PRODUCT_CLASS
        and entry.produces == requirement.product_class
    ]
    if not candidates:
        return None
    if len(candidates) > 1:
        names = sorted(candidates)
        raise AmbiguousProducerError(
            f"{len(candidates)} in-force grants declare they produce"
            f" {requirement.product_class!r} ({', '.join(names)}); this build"
            " refuses rather than applying a tie-breaker, because any rule the"
            " SDK chose would make composition and replay depend on something"
            " the deployment never declared (D-IMPL-336). Interchangeability is"
            " proven by substitution, not by simultaneous grant"
        )
    name = candidates[0]
    return ResolvedProducer(
        entry=bound_skills[name],
        # The ledger's own answer to "which grant authorized this", never a
        # value that arrived beside the entry.
        grant_hash=bound_skills.grant_hash_for(name),
        token=_PRODUCER_TOKEN,
    )


class CompositeAdmissionGate:
    """The one gate every child passes, whatever produced it.

    **Uniform by construction.** The common checks run over every child from
    every skill type; the cross-boundary checks run *in addition* for a child
    produced elsewhere. The asymmetry is never a fast path — a locally produced
    child is never exempted from a common check on the grounds that it was
    produced locally, because *"the composite should not care how a child was
    constructed"* is only true if it checks them the same way.

    **`D-IMPL-336` Amendment 3 moved the trust boundary to this gate's
    INPUTS.** The panel's root cause (a) was that everything checked lived
    inside ``contract`` while everything asserted *about* it — tenant, fabric,
    touched entities, requirement, grant, composition identity, whether the
    "signed" header was ever signed — was taken on faith. Those now arrive as
    minted evidence (:class:`ChildProvenance`, :class:`ChildInvocation`) that a
    caller cannot author, so the gate verifies the child **and** its context.

    The checks, in order, first refusal returned:

    1. **Tenant** — the child is this gate's tenant's. The precedent is exact:
       :meth:`~ccf.peering.admission.PeeringAdmissionGate._check_policy_bindings`
       opens with the same comparison under *"trust is per tenant"*, and it
       fires for cross-fabric products too, so a peered child legitimately
       claims the consumer's tenant.
    2. **Class match** — the child is the class the requirement named.
    3. **Version compatibility** — inside the requirement's declared lane.
    4. **Reconstruction instant** — the child answered *this* composition's
       ``asked_at``.
    5. **Content address** — recomputed here; the reported value is retained
       separately and never labelled as identity (F9).
    6. **Assessable debt** — *unknown debt is not zero*.
    7. **Eligibility** — from the authority the producing fabric determines,
       with a peered child's evidence age held to a **declared** bound (F7).
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
        admitted_at: datetime,
        composition_invocation: str,
    ) -> AdmittedChild | ChildAdmissionRefusal:
        """Run every check over ``candidate``; see the class docstring.

        Args:
            candidate: The served child with its **minted** provenance and
                invocation evidence.
            asked_at: **The composite's single reconstruction instant**, which
                may be historical.
            admitted_at: **When this admission is actually running.** Distinct
                from ``asked_at`` by ruling, and the only instant a producer's
                evidence age is measured against (F7). Passed rather than read
                from a clock, so the decision stays replayable.
            composition_invocation: This composition's invocation identity.
        """
        requirement = candidate.requirement
        contract = candidate.contract
        reported = candidate.content_address
        # Recomputed FIRST, before any refusal can be built, so every refusal
        # carries the honest pair (F9).
        recomputed = content_hash(contract)
        verified = recomputed if recomputed == reported else None

        def refuse(reason: ChildRefusalReason, detail: str) -> ChildAdmissionRefusal:
            return ChildAdmissionRefusal(
                gate=GATE_CHILD_ADMISSION,
                detail=detail,
                product_class=requirement.product_class,
                reason=reason,
                reported_content_address=reported,
                verified_content_address=verified,
            )

        if contract.tenant_id != self._tenant_id:
            return refuse(
                "tenant-mismatch",
                f"the child claims tenant {contract.tenant_id!r} and this gate"
                f" admits for {self._tenant_id!r}; trust is per tenant, and a"
                " child that merely claims another tenant would otherwise"
                " escape this fabric's invalidation register entirely",
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
                f" under the rule {requirement.compatibility_rule()}",
            )

        if contract.temporal_boundary != asked_at:
            return refuse(
                "as-of-mismatch",
                f"child answered as of {contract.temporal_boundary.isoformat()}"
                f" and this composition asked as of {asked_at.isoformat()};"
                " a composite has exactly one reconstruction instant, and a"
                " child from another cannot be composed",
            )

        if verified is None:
            return refuse(
                "address-mismatch",
                f"the child's door reported {reported!r} and its canonical"
                f" bytes hash to {recomputed!r}; the address is recomputed here"
                " and never trusted from the producer. Both values are"
                " retained separately — the reported one is evidence of what"
                " was claimed, never of what was served",
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
            admitted_at=admitted_at,
            composition_invocation=composition_invocation,
        )
        if isinstance(established, _EligibilityRefused):
            return refuse(
                cast(ChildRefusalReason, established.reason), established.detail
            )
        basis, evidence = established

        return AdmittedChild(
            candidate,
            basis,
            contract.debt.factors,
            asked_at,
            composition_invocation,
            verified,
            evidence,
            _CHILD_ADMISSION_TOKEN,
        )

    def _establish_eligibility(
        self,
        *,
        candidate: ChildCandidate,
        admitted_at: datetime,
        composition_invocation: str,
    ) -> tuple[str, EligibilityEvidence | None] | _EligibilityRefused:
        """Answer *may this child still serve*, from the right authority.

        **The authority follows the producing fabric, not a transport label.**
        Where this fabric produced the child its own register decides; where
        another did, only that producer's verified attestation can establish
        eligibility, and **the local register's silence never can** — silence
        is *don't know*, and reading it as *pass* is the measurement failure
        this project's rules forbid.
        """
        provenance = candidate.provenance
        contract = candidate.contract

        # The local register can always REFUSE — anything this fabric knows to
        # be superseded is superseded whoever produced it. `touched_entities`
        # is a tuple by construction now (F3): the provenance evidence carries
        # it, so there is no "I did not look" state to mistake for a pass.
        local_refusal = refuse_dependency_invalidation(
            contract,
            registry=self._registry,
            touched_entities=provenance.touched_entities,
        )
        if local_refusal is not None:
            return _EligibilityRefused(
                "ineligible",
                "this fabric's invalidation register refuses the child:"
                f" {local_refusal.detail}",
            )

        if isinstance(provenance, LocalProvenance):
            return (ELIGIBILITY_LOCAL_REGISTER, None)

        if not isinstance(provenance, VerifiedPeerProvenance):
            return _EligibilityRefused(
                "provenance-unverified",
                "the child's provenance is neither a boot-attested local"
                " production nor a verified peering admission, so no authority"
                " for its eligibility can be identified (D-IMPL-336 Am. 3)",
            )

        try:
            assertion = decode_eligibility_assertion(
                provenance.header.get(ELIGIBILITY_ASSERTION_HEADER)
            )
        except EligibilityAssertionMalformed as error:
            return _EligibilityRefused("eligibility-evidence-missing", str(error))

        mismatch = self._binding_mismatch(
            assertion,
            candidate=candidate,
            provenance=provenance,
            composition_invocation=composition_invocation,
        )
        if mismatch is not None:
            return _EligibilityRefused("eligibility-evidence-mismatch", mismatch)

        stale = self._evidence_too_old(assertion, admitted_at=admitted_at)
        if stale is not None:
            return stale

        if not assertion.eligible:
            return _EligibilityRefused(
                "ineligible",
                "the producing fabric attests this child is NOT eligible as of"
                f" {assertion.checked_at.isoformat()}; a signed negative is a"
                " governed answer and is honored",
            )
        return (
            ELIGIBILITY_PRODUCER_ATTESTED,
            EligibilityEvidence(
                checked_at=assertion.checked_at,
                assertion_address=content_hash(assertion),
                producer=assertion.producer,
            ),
        )

    def _evidence_too_old(
        self, assertion: EligibilityAssertion, *, admitted_at: datetime
    ) -> _EligibilityRefused | None:
        """Hold the producer's check to a DECLARED age bound (F7).

        Measured against ``admitted_at`` — when this admission is running —
        and **never** against the reconstruction instant, which may legitimately
        be years earlier than an honest check.

        A deployment that admits peered children and has declared no bound gets
        an explicit refusal. The SDK holds no duration and invents none
        (``D-IMPL-38``).
        """
        key = eligibility_evidence_policy_key(tenant_id=self._tenant_id)
        policy: object = None
        try:
            # `resolve_latest` returns (version, artifact); the artifact is the
            # second member, and reading the tuple as the artifact was a live
            # bug caught by mypy before any test ran.
            _version, policy = self._registry.resolve_latest(key)
        except ControlPlaneMissing:
            # NARROW, deliberately. A bare `except` here would swallow a
            # registry outage and report it as an undeclared bound, which is a
            # different fact with a different remedy.
            policy = None
        if not isinstance(policy, EligibilityEvidencePolicy):
            return _EligibilityRefused(
                # Its OWN reason: a tenant that declared no bound has a
                # configuration error, and saying "your peer's evidence is
                # stale" would name the wrong party.
                "eligibility-bound-undeclared",
                "this tenant has declared no eligibility-evidence bound at"
                f" {key!r}, so how old a producer's check may be is unknown."
                " Refused rather than defaulted: the SDK holds no duration"
                " (D-IMPL-38), and an unbounded attestation would authorize a"
                " determination of any age (D-IMPL-336 Am. 3, F7)",
            )

        age = (admitted_at - assertion.checked_at).total_seconds()
        if age > policy.max_evidence_age_seconds:
            return _EligibilityRefused(
                "eligibility-evidence-stale",
                f"the producer checked eligibility at"
                f" {assertion.checked_at.isoformat()}, {int(age)}s before this"
                f" admission at {admitted_at.isoformat()}; the declared maximum"
                f" evidence age is {policy.max_evidence_age_seconds}s",
            )
        if -age > policy.permitted_clock_skew_seconds:
            return _EligibilityRefused(
                "eligibility-evidence-stale",
                f"the producer's check is dated {assertion.checked_at.isoformat()},"
                f" {int(-age)}s AFTER this admission at"
                f" {admitted_at.isoformat()}; the declared permitted clock skew"
                f" is {policy.permitted_clock_skew_seconds}s. Evidence from the"
                " future is refused rather than treated as maximally fresh",
            )
        return None

    def _binding_mismatch(
        self,
        assertion: EligibilityAssertion,
        *,
        candidate: ChildCandidate,
        provenance: VerifiedPeerProvenance,
        composition_invocation: str,
    ) -> str | None:
        """Check every EQUALITY binding — five of them, and the count is stated.

        `D-IMPL-336` Amendment 3 corrects the documentation the panel caught:
        the assertion binds five facts by **equality** here, and its
        ``checked_at`` is held to a **declared age bound** in
        :meth:`_evidence_too_old`. Those are different checks and the module no
        longer claims otherwise.

        ``producer`` is compared against the identity the **verified** header
        asserted, not against a sibling field the same caller wrote — the
        earlier comparison held two caller-supplied strings against each other.
        """
        if assertion.child_content_address != candidate.content_address:
            return (
                "the eligibility assertion is about"
                f" {assertion.child_content_address!r} and this child is"
                f" {candidate.content_address!r}"
            )
        if assertion.requested_as_of != candidate.contract.temporal_boundary:
            return (
                "the eligibility assertion was made for reconstruction instant"
                f" {assertion.requested_as_of.isoformat()} and the child answers"
                f" for {candidate.contract.temporal_boundary.isoformat()}"
            )
        if assertion.producer != provenance.producer:
            return (
                f"the eligibility assertion names producer"
                f" {assertion.producer!r} and the VERIFIED envelope was"
                f" produced by {provenance.producer!r}"
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
                f" {composition_invocation!r}; the binding is to one"
                " invocation, so an assertion cannot be carried into a"
                " different composition"
            )
        return None



@runtime_checkable
class CompositeChildResolverProtocol(Protocol):
    """Produce the admitted-or-refused child set for a composite (`D-IMPL-336`).

    **The SDK ships this Protocol and never an implementation**, because
    resolving a requirement to a granted skill, dispatching it and delivering
    the child is agent orchestration — the harness's, exactly as the agent loop
    is (CLAUDE.md §7.3, §8.1). What the SDK owns is the declaration, the
    admission and the composition on either side of this call.

    A conforming implementation:

    * reads ``requires`` **from the registered class**, never from a list a
      caller supplied;
    * resolves each requirement to an in-force grant with
      :func:`resolve_producing_grant`, and lets
      :class:`AmbiguousProducerError` propagate rather than picking one;
    * dispatches that grant's skill and delivers the child through its own
      governed door;
    * mints :class:`ChildInvocation` from the resolved entry and
      :class:`ChildProvenance` from boot or from a verified peering
      admission — never from strings it wrote itself;
    * offers each result to :meth:`CompositeAdmissionGate.admit` and returns
      what came back.

    Returning ``None`` for a class means **no in-force grant produces it**,
    which is the one honest absence: it is the only outcome that takes an
    optional requirement's declared absence treatment.
    """

    def __call__(
        self,
        *,
        requirements: Sequence[ChildRequirement],
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
    ) -> Mapping[str, object]:
        """Resolve, invoke, deliver and admit; return one outcome per class."""
        ...


@dataclass(frozen=True)
class CompositionOutcome:
    """What a composition produced: all four ruled laws, or a refusal.

    **The rows are present either way.** A composite that refused still records
    every requirement and its disposition, because a requirement that produced
    nothing and left no row would be indistinguishable from one that was never
    declared — the silent omission this surface exists to prevent.

    **`D-IMPL-336` Amendment 3, F14 — this carries all four composition laws,
    not one.** `D-IMPL-31` and `D-IMPL-104` between them rule four:
    per-factor debt, lineage set-union, the expiry floor, and the
    mixing refusal. The earlier outcome carried only ``factors``, so a caller
    using the API as designed could not compute the floor at all and replay
    could not tell whether it had been applied — the laws shipped in
    :mod:`ccf.products.composition` and this module never imported them.

    Attributes:
        factors: The per-factor minimum over the parent and its admitted
            children (`D-IMPL-104`). ``None`` exactly when ``refusal`` is set.
        lineage: The N-way set-union over the admitted children's lineages
            (`D-IMPL-31`), so every constituent's provenance stays resolvable
            from the composite. ``None`` when refused.
        expires_at: The composite's validity, floored by the stalest admitted
            constituent (`D-IMPL-31`), so a composite is never labelled fresher
            than its stalest child. ``None`` when refused.
        refusal: The governed "no", including a
            :class:`~ccf.products.composition.MixingRefusal` rendered as a
            child-admission refusal when a constituent breached its declared
            validity floor.
        admitted_operators: The union over the ADMITTED CHILDREN's operator
            sets alone — never including the parent's own (`R4`).

            This is Gate 2's missing operand. :attr:`lineage` is the union
            *including* the parent, so a caller holding only that cannot tell
            the parent's declared half from its children's, and the two must
            stay separable: the composite's engine-resolved set is the
            parent's execution unioned with this, while the parent's OWN
            declaration is still held to its OWN execution by strict equality.
            Collapsing them would let a child that happens to invoke operator
            X mask the parent's declaration having drifted onto X.

            ``frozenset()`` when nothing was admitted, which is the honest
            claim that no child contributed an operator — and it leaves the
            composite's operand exactly equal to a non-composite's.
    """

    factors: DebtFactors | None
    resolutions: tuple[ChildResolution, ...]
    refusal: ChildAdmissionRefusal | None
    lineage: ProductLineage | None = None
    expires_at: datetime | None = None
    admitted_operators: frozenset[str] = frozenset()

    @property
    def served(self) -> bool:
        """Whether the composite may be assembled from this outcome."""
        return self.refusal is None


def compose_children(
    *,
    own_factors: DebtFactors,
    requirements: Sequence[ChildRequirement],
    # `object` and not the narrow union, DELIBERATELY (F13). The narrow type
    # says an unsupported value cannot arrive, and mypy then proves the guard
    # below unreachable — which is exactly the assumption that let a raw
    # contract be read as "nothing was produced". The guard is the mechanism;
    # the type must admit the case it guards.
    outcomes: Mapping[str, object],
    asked_at: datetime,
    composition_invocation: str,
    own_lineage: ProductLineage,
    max_ttl: MaxTTL,
    ttl_anchor_at: datetime,
    validity_floors: ConstituentValidityFloors,
) -> CompositionOutcome:
    """Compose an admitted child set, or refuse, and record every requirement.

    Walks ``requirements`` **in declaration order** — the order rows appear in
    replay and the order a refusal names.

    **`D-IMPL-336` Amendment 3 re-binds every child to THIS composition.** The
    earlier body keyed on ``outcomes.get(requirement.product_class)`` and
    trusted whatever it found: an admitted child could satisfy a slot it was
    never checked against, children admitted at different instants composed
    together, an undeclared key vanished silently, and an unsupported object
    was read as *nothing was produced*. Each of those is now a refusal.

    Args:
        own_factors: What the parent itself assembled.
        requirements: The composite class's declared requirements, **read from
            the registered declaration** — never a replacement list.
        outcomes: Per ``product_class``: the admitted child, the refusal that
            came back, or ``None`` for a requirement no granted skill produced.
        asked_at: The composite's single reconstruction instant. Every admitted
            child must have been admitted at exactly this instant.
        ttl_anchor_at: The instant the composite's TTL runs from — the
            **decision** instant, not the reconstruction one (`D-IMPL-308`).
            Passed rather than derived so this function reads no clock and so
            a composite and a non-composite of one class anchor identically
            (`R6`: they did not, and two governed answers collided on one
            content address).
        composition_invocation: This composition's invocation identity. Every
            admitted child must have been admitted under exactly this one.
    """
    rows: list[ChildResolution] = []
    admitted_factors: list[DebtFactors] = []
    admitted_children: list[AdmittedChild] = []
    refusal: ChildAdmissionRefusal | None = None

    def first(candidate_refusal: ChildAdmissionRefusal) -> None:
        nonlocal refusal
        if refusal is None:
            refusal = candidate_refusal

    def bare(
        reason: ChildRefusalReason, product_class: str, detail: str
    ) -> ChildAdmissionRefusal:
        return ChildAdmissionRefusal(
            gate=GATE_CHILD_ADMISSION,
            detail=detail,
            product_class=product_class,
            reason=reason,
        )

    # --- F12: the declared list must be coherent, at execution too ----------
    # The registration validator enforces this on the artifact; enforcing it
    # here as well is what closes the gap between a declaration surface and an
    # execution surface that were previously unconnected.
    declared: list[str] = []
    for requirement in requirements:
        if requirement.product_class in declared:
            return CompositionOutcome(
                factors=None,
                # No rows: the declaration itself is incoherent, so there is no
                # per-requirement disposition to record. Distinct from the
                # undeclared-key case below, which HAS dispositions.
                resolutions=(),
                refusal=bare(
                    "requirement-mismatch",
                    requirement.product_class,
                    f"product class {requirement.product_class!r} appears twice"
                    " in the requirement list; two requirements naming one"
                    " class have no distinct resolution, and a record carrying"
                    " both would assert two dispositions of one requirement",
                ),
            )
        declared.append(requirement.product_class)

    # --- F17: an outcome naming no declared slot is refused, not dropped ----
    undeclared = sorted(set(outcomes) - set(declared))
    undeclared_refusal = (
        bare(
            "undeclared-outcome",
            undeclared[0],
            f"outcomes name {undeclared!r}, which this class does not require."
            " Silently discarding them would drop a produced child and its debt"
            " from both the arithmetic and the record",
        )
        if undeclared
        else None
    )
    # NOT returned here. The declared requirements still have dispositions, and
    # returning early would wipe the whole audit trace of every validly
    # produced child for this decision — losing more evidence than the defect
    # being refused. The rows are built below and the refusal is applied after.

    if undeclared_refusal is not None:
        first(undeclared_refusal)

    for requirement in requirements:
        outcome = outcomes.get(requirement.product_class)

        if isinstance(outcome, AdmittedChild):
            mismatch = _rebinding_failure(
                outcome,
                requirement=requirement,
                asked_at=asked_at,
                composition_invocation=composition_invocation,
            )
            if mismatch is not None:
                reason, detail = mismatch
                rows.append(
                    ChildResolution(
                        required_product_class=requirement.product_class,
                        required=requirement.required,
                        outcome_status=_status_for(reason),
                        child_reported_address=outcome.candidate.content_address,
                        # The identity IS verified — admission established it —
                        # so it is retained. Only an address the gate DISPROVED
                        # is withheld from this field (F9).
                        child_content_address=outcome.verified_content_address,
                        producing_fabric=_fabric_of(outcome.candidate.provenance),
                        refusal_ref=reason,
                    )
                )
                first(bare(reason, requirement.product_class, detail))
                continue
            rows.append(_row_for_admitted(requirement, outcome))
            admitted_factors.append(outcome.factors)
            admitted_children.append(outcome)
            continue

        if isinstance(outcome, ChildAdmissionRefusal):
            # F1 RULED: a child that was INVOKED and refused, or produced and
            # rejected, refuses the composite — **even for an optional slot**.
            # Optional means optional ABSENCE, not optional governance. There
            # is no rate at which a governance failure is priced, and wrapping
            # one as an empty served product is forbidden.
            rows.append(
                ChildResolution(
                    required_product_class=requirement.product_class,
                    required=requirement.required,
                    outcome_status=_status_for(outcome.reason),
                    child_reported_address=outcome.reported_content_address,
                    child_content_address=outcome.verified_content_address,
                    refusal_ref=outcome.reason,
                )
            )
            first(outcome)
            continue

        if outcome is not None:
            # F13: an unexpected object is NOT "nothing was produced". Reading
            # it as an absence let a raw contract be composed at the declared
            # absence cost under an optional slot.
            rows.append(
                ChildResolution(
                    required_product_class=requirement.product_class,
                    required=requirement.required,
                    outcome_status=_status_for("unsupported-outcome"),
                    refusal_ref="unsupported-outcome",
                )
            )
            first(
                bare(
                    "unsupported-outcome",
                    requirement.product_class,
                    f"the outcome for {requirement.product_class!r} is a"
                    f" {type(outcome).__name__}, which is neither an"
                    " AdmittedChild nor a ChildAdmissionRefusal. A caller"
                    " reaching past the gate is a deployment defect, and"
                    " reading it as an absence would compose an unadmitted"
                    " product at the declared absence cost",
                )
            )
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
            first(
                bare(
                    "no-producing-skill",
                    requirement.product_class,
                    "no in-force grant declares it produces"
                    f" {requirement.product_class!r}, and the requirement is"
                    " required; a composite never silently omits one",
                )
            )
            continue

        # F1 RULED: optional + HONEST no-producing-skill takes the declared
        # absence treatment. This is the only branch that does, and the reason
        # is that it is the only branch where nothing was ever invoked.
        treatment = requirement.absence_treatment
        assert treatment is not None  # ChildRequirement guarantees it
        rows.append(
            ChildResolution(
                required_product_class=requirement.product_class,
                required=False,
                outcome_status="optional-absent",
            )
        )
        admitted_factors.append(
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

    # --- F14: the OTHER THREE ruled laws, which were shipped and uncalled ---
    #
    # `refuse_mixing` first, because D-IMPL-31 rules that a constituent whose
    # remaining validity breaches its declared floor refuses assembly outright
    # — a composite must not be built at all rather than built and labelled.
    # The three laws below take CONSTITUENTS, and a composition whose only
    # requirement was optional and honestly absent has none — `refuse_mixing`
    # and `compose_lineage` both RAISE on an empty set, deliberately, because
    # composing nothing is a wiring defect everywhere else. Here it is a legal
    # outcome: the class asked for something optional, nothing produced it, and
    # the declared absence treatment already priced that. So the laws run over
    # the admitted set when there is one, and the parent's own terms stand when
    # there is not.
    if not admitted_children:
        return CompositionOutcome(
            factors=compose_debt_factors(own_factors, admitted_factors),
            resolutions=tuple(rows),
            refusal=None,
            lineage=own_lineage,
            expires_at=None,
        )

    mixing = refuse_mixing(
        constituents=[
            ConstituentValidity(
                constituent_id=child.verified_content_address,
                signal_type=child.contract.schema_name,
                expires_at=child.contract.expires_at,
            )
            for child in admitted_children
        ],
        floors=validity_floors,
        # Remaining validity is judged at the DECISION instant, for the same
        # reason the expiry is anchored there.
        evaluated_at=ttl_anchor_at,
    )
    if mixing is not None:
        return CompositionOutcome(
            factors=None,
            resolutions=tuple(rows),
            refusal=ChildAdmissionRefusal(
                gate=GATE_CHILD_ADMISSION,
                detail=(
                    "a constituent breached its declared validity floor, so"
                    f" this composite is not assembled at all: {mixing.detail}"
                ),
                product_class=mixing.constituent_id,
                reason="mixing-refused",
            ),
        )

    return CompositionOutcome(
        factors=compose_debt_factors(own_factors, admitted_factors),
        resolutions=tuple(rows),
        refusal=None,
        # The N-way set-union, so every child's provenance stays resolvable.
        lineage=compose_lineage(
            [own_lineage, *(c.contract.lineage for c in admitted_children)]
        ),
        # The floor. A composite is never labelled fresher than its stalest
        # constituent — and this is now a property of the shipped path, not of
        # a helper a test called with two literal datetimes.
        expires_at=compose_expiry(
            constituent_validities=[
                c.contract.expires_at for c in admitted_children
            ],
            max_ttl=max_ttl,
            ttl_anchor_at=ttl_anchor_at,
        ),
        # `R4`. Read off each child's OWN contract lineage, which is
        # engine-resolved evidence rather than a claim: it passed that child's
        # own Gate 2 at its own delivery, and admission recomputed the child's
        # content address, so the lineage carried here is the verified one.
        admitted_operators=frozenset().union(
            *(c.contract.lineage.operators_invoked for c in admitted_children)
        ),
    )


def _rebinding_failure(
    admitted: AdmittedChild,
    *,
    requirement: ChildRequirement,
    asked_at: datetime,
    composition_invocation: str,
) -> tuple[ChildRefusalReason, str] | None:
    """Re-check that this admission was for THIS slot and THIS composition.

    `D-IMPL-336` Amendment 3, F2/F15. Admission proves checks ran; this proves
    they ran against the requirement the child is now being used to satisfy,
    at this composition's instant, under this composition's invocation.
    """
    if admitted.requirement != requirement:
        return (
            "requirement-mismatch",
            f"this child was admitted against"
            f" {admitted.requirement.product_class!r} at floor"
            f" {admitted.requirement.compatible_from} and is being composed"
            f" against {requirement.product_class!r} at floor"
            f" {requirement.compatible_from}; admission is evidence about the"
            " requirement it ran for and cannot be carried to another",
        )
    if not requirement.accepts(child_version=admitted.contract.schema_version):
        return (
            "version-incompatible",
            f"child is {admitted.contract.schema_version} and this slot"
            f" composes over {requirement.compatible_from} under"
            f" {requirement.compatibility_rule()}",
        )
    if admitted.asked_at != asked_at:
        return (
            "as-of-mismatch",
            f"this child was admitted for reconstruction instant"
            f" {admitted.asked_at.isoformat()} and this composition is"
            f" {asked_at.isoformat()}; a composite has exactly ONE, and"
            " individually valid admissions from different instants must not"
            " combine",
        )
    if admitted.composition_invocation != composition_invocation:
        return (
            "requirement-mismatch",
            f"this child was admitted under composition"
            f" {admitted.composition_invocation!r} and this is"
            f" {composition_invocation!r}; the binding is to one invocation",
        )
    return None


_REASON_TO_STATUS: Final[Mapping[str, str]] = {
    # Governance outcomes keep their own token — these are the four absences
    # `record.py` says must stay distinct.
    "ineligible": "ineligible",
    "unauthorized": "unauthorized",
    "no-producing-skill": "no-producing-skill",
    "ambiguous-producer": "ambiguous-producer",
    # Eligibility EVIDENCE failures are eligibility failures, not generic
    # rejections. The earlier code folded all three into
    # `rejected-at-admission`, so an auditor counting eligibility failures
    # across peered children under-counted.
    "eligibility-evidence-missing": "ineligible",
    "eligibility-evidence-mismatch": "ineligible",
    "eligibility-evidence-stale": "ineligible",
    # A tenant that declared no bound is a CONFIGURATION error, not a verdict
    # about this child's evidence. Conflating them told an operator their
    # peer's attestation was stale when the truth was that nothing said how
    # stale is too stale.
    "eligibility-bound-undeclared": "unauthorized",
    "composition-unwired": "unauthorized",
    # Provenance and tenancy are authorization-shaped, not data-shaped.
    "tenant-mismatch": "unauthorized",
    "provenance-unverified": "unauthorized",
    # The rest are genuine admission rejections: the child was produced and
    # did not meet the contract.
    "class-mismatch": "rejected-at-admission",
    "version-incompatible": "rejected-at-admission",
    "as-of-mismatch": "rejected-at-admission",
    "address-mismatch": "rejected-at-admission",
    "debt-unassessable": "rejected-at-admission",
    "requirement-mismatch": "rejected-at-admission",
    "undeclared-outcome": "rejected-at-admission",
    "unsupported-outcome": "rejected-at-admission",
    "mixing-refused": "rejected-at-admission",
}


def _status_for(reason: str) -> str:
    """Map an admission cause to its closed ``outcome_status`` token.

    Raises:
        ValueError: ``reason`` is outside :data:`CHILD_REFUSAL_REASONS`. A
            broken deployment, not a bad product — and raised rather than
            silently downgraded, which is F11's whole point.
    """
    try:
        return _REASON_TO_STATUS[reason]
    except KeyError:
        raise ValueError(
            f"refusal reason {reason!r} is outside the closed vocabulary"
            f" {sorted(CHILD_REFUSAL_REASONS)}; this build refuses to guess a"
            " replay status rather than demote an unrecognized governance"
            " failure to a generic rejection (D-IMPL-336 Amendment 3, F11)"
        ) from None


def _fabric_of(provenance: ChildProvenance) -> str | None:
    """Name the fabric an eligibility claim was made ABOUT.

    Shared by the admitted and the rejected row alike: the panel's F6 point was
    that a mislabelled production left no trace, and a rejected child whose
    fabric went unrecorded would leave the same gap on the other branch.
    """
    if isinstance(provenance, LocalProvenance):
        return provenance.attestor_id
    if isinstance(provenance, VerifiedPeerProvenance):
        return provenance.peer_id
    return None


def _row_for_admitted(
    requirement: ChildRequirement, admitted: AdmittedChild
) -> ChildResolution:
    """Every field admission checked, recorded — nothing re-derived later."""
    candidate = admitted.candidate
    contract = admitted.contract
    debt = contract.debt
    assert debt is not None  # admission refuses an unassessable child
    provenance = candidate.provenance
    evidence = admitted.eligibility_evidence
    return ChildResolution(
        required_product_class=requirement.product_class,
        required=requirement.required,
        outcome_status=CHILD_ADMITTED,
        # F4: the resolved entry's own identity, not a caller's spelling.
        producing_skill_name=candidate.invocation.skill_name,
        producing_skill_version=candidate.invocation.entry_version,
        grant_hash=candidate.invocation.grant_hash,
        # F9: verified and reported, kept apart.
        child_content_address=admitted.verified_content_address,
        child_reported_address=candidate.content_address,
        child_schema_name=contract.schema_name,
        child_schema_version=contract.schema_version,
        child_asked_at=admitted.asked_at,
        child_graph_snapshot_at=contract.lineage.graph_snapshot_at,
        child_debt=debt.debt,
        child_debt_factors=debt.factors,
        child_policy_bundle_versions=contract.lineage.policy_bundle_versions,
        child_lineage_ref=content_hash(contract.lineage),
        eligibility_basis=admitted.eligibility_basis,
        # F6: name the fabric the basis was claimed about.
        producing_fabric=(
            provenance.attestor_id
            if isinstance(provenance, LocalProvenance)
            else provenance.peer_id
            if isinstance(provenance, VerifiedPeerProvenance)
            else None
        ),
        # F7: the producer's check instant and the assertion it came from.
        child_eligibility_checked_at=(
            evidence.checked_at if evidence is not None else None
        ),
        child_eligibility_assertion_address=(
            evidence.assertion_address if evidence is not None else None
        ),
    )
