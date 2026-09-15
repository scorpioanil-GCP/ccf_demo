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

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Final,
    Literal,
    Protocol,
    TypeGuard,
    cast,
    get_args,
    runtime_checkable,
)

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
    EligibilityEvidence,
    EligibilityRefused,
    verify_child_eligibility,
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
from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.replay.record import (
    CHILD_ADMITTED,
    ChildResolution,
    DecisionReplayRecord,
)
from ccf.products.producer import ProducerAssertion
from ccf.products.request import ProductRequest
from ccf.skills.catalog import NO_PRODUCT_CLASS, SkillCatalogEntry
from ccf.skills.dispatch import verify_mcp_product_invocation
from ccf.skills.grants import BoundSkillView

if TYPE_CHECKING:  # the door imports the refusal module, which imports this one
    from ccf.products.door import WireRequest

__ccf_mode__ = "algorithmic"

__all__ = [
    "ADMITTED_CHILD_CONTRACT_CLASS",
    "ChildContractView",
    "ChildOutcomeResolution",
    "child_contract_view",
    "resolve_child_outcomes",
    "ELIGIBILITY_LOCAL_REGISTER",
    "ELIGIBILITY_PROVIDER_CONTROLS",
    "ELIGIBILITY_PRODUCER_ATTESTED",
    "GATE_CHILD_ADMISSION",
    "CHILD_REFUSAL_REASONS",
    "EligibilityEvidence",
    "AdmittedChild",
    "AmbiguousProducerError",
    "ChildAdmissionBypassError",
    "ChildAdmissionRefusal",
    "ChildCandidate",
    "ChildAcquisition",
    "ChildInvocation",
    "ChildRefusalReason",
    "CompositeAdmissionGate",
    "CompositeChildResolverProtocol",
    "RequestAwareChildResolverProtocol",
    "CompositionOutcome",
    "compose_children",
    "invocation_from_dispatch",
    "ProvenanceForgeryError",
    "ResolvedProducer",
    "resolve_producing_grant",
]

#: The artifact class the consuming fabric files an ADMITTED child's contract
#: under, by content address, at decision time (`D-IMPL-339`). A mechanism
#: token like `GATE_CHILD_ADMISSION` below, not a domain value: nothing else
#: retains a served product's bytes, and replay must rebuild the parent's
#: child-contract view from what it consumed — never from a provider call.
ADMITTED_CHILD_CONTRACT_CLASS: Final = "ccf.admitted-child-contract"

#: The gate identifier every child-admission refusal carries.
GATE_CHILD_ADMISSION: Final = "child_admission"

#: ``eligibility_basis`` when this fabric's own register was authoritative.
ELIGIBILITY_LOCAL_REGISTER: Final = "local-register"

#: ``eligibility_basis`` when the producing fabric attested it.
ELIGIBILITY_PRODUCER_ATTESTED: Final = "producer-attested"

#: ``eligibility_basis`` when the PROVIDER's own access controls governed the
#: read and this fabric holds no execution record for the child — the MCP case
#: (`D-IMPL-336` Amendment 5). A positive statement about which authority
#: applied, never an absence: the local register was not consulted, and this
#: row says so rather than leaving a reader to infer that it passed.
ELIGIBILITY_PROVIDER_CONTROLS: Final = "provider-controls"

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
    # `D-IMPL-340` — the producer leg. Wrong producer and wrong producer
    # tenant are DISTINCT by ruling; equality is a binding check, never an
    # authorization.
    "producer-tenant-mismatch",
    "producer-mismatch",
    "producer-unasserted",
    "question-mismatch",
    "producer-unavailable",
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
    # `D-IMPL-340` — the producer relationship a refusal was made under, from
    # the registration the registry resolved (never from the answer), so a
    # refused `mcp_product` row still names the exact producer. Transparent at
    # ``None``: every refusal on every other leg hashes as it did.
    producer_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_tenant: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_registration_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producer_server: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    question_address: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class ProvenanceForgeryError(TypeError):
    """Provenance evidence was constructed outside its minting authority."""


_INVOCATION_TOKEN = object()


#: How the child was acquired — read off the DISPATCH RESULT TYPE, never
#: asserted by a caller. `D-IMPL-336` **Amendment 5**: this is the *provider
#: relationship*, which is the axis that decides which controls apply.
#:
#: **`D-IMPL-59` separates MCP from Peering and so does this.** Dave's
#: correction, verbatim: *"MCP is not automatically peering… Apply the existing
#: controls for the actual provider relationship; do not require a new signed
#: envelope merely because acquisition uses MCP. A genuinely peered product
#: must still pass peering verification, regardless of how the skill retrieves
#: it."*
ChildAcquisition = Literal["local-dispatch", "mcp", "mcp-product", "peered"]

#: What each acquisition kind is evidenced by, and what it may therefore claim.
#:
#: Keyed on the dispatch result's TYPE NAME and cross-checked against the
#: ``skill_type`` the entry declares and the one the dispatch stamped onto its
#: own result. The close panel found the single-key version spoofable: a
#: hand-built ``SkillInvocation`` naming a genuinely MCP-bound entry yielded
#: ``local-dispatch`` with caller-chosen touched entities, which is exactly the
#: relabelling Dave's ruling forbids — *"a local skill fetching a remote
#: product must not relabel that product as locally produced to bypass its
#: applicable checks."* Three facts must now agree.
_ACQUISITION_OF: Final[dict[str, tuple[ChildAcquisition, str]]] = {
    "SkillInvocation": ("local-dispatch", "local_callable"),
    "McpInvocation": ("mcp", "mcp"),
    # `D-IMPL-340`: a producer ASKED a governed question. Its own kind, so
    # the producer admission leg runs for it and for nothing else.
    "McpProductInvocation": ("mcp-product", "mcp_product"),
    "PeeringInvocation": ("peered", "peering"),
}


class ChildInvocation:
    """Evidence that an ACTUAL grant resolution and skill dispatch ran.

    `D-IMPL-336` Amendment 3 replaced the assembler's free ``skill_name`` /
    ``skill_version`` / ``grant_hash`` strings with a resolved catalog entry;
    **O2** bound the grant hash to the ledger; **Amendment 5** binds the
    *dispatch* as well, and makes this the ONLY provenance the composite
    carries.

    Dave: *"Obtain invocation attribution directly from the existing grant and
    dispatch execution records — not caller-written grant hashes or identity
    strings."* So both halves come from machinery: the grant from
    :class:`ResolvedProducer` (the ledger's), the acquisition kind from the
    **type of the dispatch result** (:mod:`ccf.skills.dispatch`'s).

    **This replaces the whole `LocalFabricAttestor` / `LocalProvenance` /
    `VerifiedPeerProvenance` layer, which is deleted.** That layer asked a
    second time whether a child was authorized. The grant authorizes invoking
    the skill; the provider's own controls govern what the invocation may
    return; composition duplicates neither.

    Minted only by :func:`invocation_from_dispatch`.
    """

    __slots__ = (
        "_acquisition",
        "_entry_version",
        "_grant_hash",
        "_producer_id",
        "_producer_registration_address",
        "_producer_server",
        "_producer_tenant",
        "_question_address",
        "_skill_name",
        "_touched_entities",
    )

    def __init__(
        self,
        *,
        skill_name: str,
        entry_version: str,
        grant_hash: str,
        acquisition: ChildAcquisition,
        touched_entities: tuple[str, ...] | None,
        token: object,
        producer_id: str | None = None,
        producer_tenant: str | None = None,
        producer_registration_address: str | None = None,
        producer_server: str | None = None,
        question_address: str | None = None,
    ) -> None:
        if token is not _INVOCATION_TOKEN:
            raise ProvenanceForgeryError(
                "ChildInvocation is minted only by"
                " ccf.products.composite.invocation_from_dispatch, from a grant"
                " the ledger made effective and a dispatch that actually ran."
                " Accepting caller-written skill, grant or acquisition strings"
                " is what let an ungranted producer be recorded as an"
                " authorized one (D-IMPL-336 F4, O2, Amendment 5)"
            )
        self._skill_name = skill_name
        self._entry_version = entry_version
        self._grant_hash = grant_hash
        self._acquisition = acquisition
        self._touched_entities = touched_entities
        self._producer_id = producer_id
        self._producer_tenant = producer_tenant
        self._producer_registration_address = producer_registration_address
        self._producer_server = producer_server
        self._question_address = question_address

    @property
    def producer_id(self) -> str | None:
        """`D-IMPL-340`: the identity the registration expects (``mcp-product`` only)."""
        return self._producer_id

    @property
    def producer_tenant(self) -> str | None:
        """`D-IMPL-340`: the tenant the registration expects (``mcp-product`` only)."""
        return self._producer_tenant

    @property
    def producer_registration_address(self) -> str | None:
        """`D-IMPL-340`: the ``ccf.mcp-producer`` document's content address."""
        return self._producer_registration_address

    @property
    def producer_server(self) -> str | None:
        """`D-IMPL-340`: the logical producer name the binding selected."""
        return self._producer_server

    @property
    def question_address(self) -> str | None:
        """`D-IMPL-340`: ``sha256`` of the canonical question sent."""
        return self._question_address

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

    @property
    def acquisition(self) -> ChildAcquisition:
        """The provider relationship, from the dispatch result's own type."""
        return self._acquisition

    @property
    def touched_entities(self) -> tuple[str, ...] | None:
        """What the child's execution read, when this fabric can know it.

        ``None`` is a POSITIVE statement and not an omission: *the child was
        produced by a provider whose execution record this fabric does not
        hold*. Dave's ruling is explicit — *"do not require access to a remote
        provider's internal replay store"* — so for an ``mcp`` or ``peered``
        child there is nothing here to read, and the local invalidation
        register is **not** consulted and **not** claimed as the authority.

        For a ``local-dispatch`` child it is read from the child's own
        persisted replay record, never from a caller. ``()`` there is the
        verified claim that the child read nothing.

        `F3`'s defect was omitting this and still recording that the register
        had authorized the child. What closes F3 is that the *basis* is
        recorded alongside — never that the value is always present.
        """
        return self._touched_entities


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

    __slots__ = ("_entry", "_grant_hash", "_producer_provenance")

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
        # `D-IMPL-337`. The PROVENANCE, distinct from the type, set only on
        # the path that read both halves from the ledger. `isinstance` proves
        # nominal membership; a subclass skipping this `__init__` satisfies it
        # while no grant resolution ran.
        self._producer_provenance = _PRODUCER_TOKEN

    @property
    def entry(self) -> SkillCatalogEntry:
        """The catalog entry the in-force grant resolves to."""
        return self._entry

    @property
    def grant_hash(self) -> str:
        """The hash of the grant that put :attr:`entry` in force."""
        return self._grant_hash


def verify_resolved_producer_provenance(producer: object) -> "ResolvedProducer":
    """Establish that ``producer`` came from :func:`resolve_producing_grant`.

    `D-IMPL-337`'s verifier for :class:`ResolvedProducer`. **The check is the
    provenance, not the type.** The previous check here was
    ``isinstance(producer, ResolvedProducer)``, added against a measured
    `SimpleNamespace` forgery — it closed the duck-typed class and left the
    nominal one open: a subclass skipping the guarded ``__init__`` satisfies
    `isinstance` while no grant was ever resolved.

    Returns the value, narrowed, so a caller cannot verify and then forget to
    use the result.

    Raises:
        ProvenanceForgeryError: the value did not come from
            :func:`resolve_producing_grant`.
    """
    if getattr(producer, "_producer_provenance", None) is not _PRODUCER_TOKEN:
        raise ProvenanceForgeryError(
            "this value carries no evidence of grant resolution."
            " ccf.products.composite.resolve_producing_grant is the only path"
            " that establishes it, and neither a structurally compatible"
            " object nor a subclass of ResolvedProducer that skipped its"
            " guarded __init__ acquires it — so a grant hash nobody granted"
            " cannot be recorded as one that was (D-IMPL-337, D-IMPL-336 O2)"
        )
    return cast("ResolvedProducer", producer)


def _has_child_provenance(value: object) -> TypeGuard["AdmittedChild"]:
    """Whether ``value`` came through :meth:`CompositeAdmissionGate.admit`.

    The predicate form of :func:`verify_child_admission_provenance`, for the
    one caller that must **branch** rather than raise: `compose_children`
    dispatches four ways, and a value failing this test is not an error — it
    falls to the `unsupported-outcome` branch, which is the established
    semantics for *an object that is not a supported outcome*.

    **A `TypeGuard`, so the narrowing is the PROVENANCE check's** rather than a
    second `isinstance` added to satisfy the type checker — which would have
    put back the very mechanism `D-IMPL-337` rejects, in a place no reviewer
    would look. `outcomes` stays `Mapping[str, object]`.
    """
    return getattr(value, "_child_provenance", None) is _CHILD_ADMISSION_TOKEN


def verify_child_admission_provenance(child: object) -> "AdmittedChild":
    """Establish that ``child`` came through :meth:`CompositeAdmissionGate.admit`.

    `D-IMPL-337`'s verifier for :class:`AdmittedChild`. Possessing one is meant
    to be the evidence that every admission check ran — tenant, class, version
    lane, reconstruction instant, content address, assessable debt and
    eligibility. The type proves none of them.

    Raises:
        ProvenanceForgeryError: the value did not come through the gate.
    """
    if getattr(child, "_child_provenance", None) is not _CHILD_ADMISSION_TOKEN:
        raise ProvenanceForgeryError(
            "this value carries no evidence of composite child admission."
            " ccf.products.composite.CompositeAdmissionGate.admit is the only"
            " path that establishes it (D-IMPL-337, D-IMPL-336)"
        )
    return cast("AdmittedChild", child)


def invocation_from_dispatch(
    producer: ResolvedProducer,
    dispatched: object,
    *,
    touched_entities: tuple[str, ...] | None = None,
) -> ChildInvocation:
    """Record what a real grant resolution AND a real dispatch produced.

    `D-IMPL-336` **Amendment 5**. Both arguments are machinery output:
    ``producer`` is what :func:`resolve_producing_grant` returned from the
    ledger, and ``dispatched`` is what :func:`ccf.skills.dispatch.dispatch_skill`
    returned. The acquisition kind is the dispatch result's **type** — so the
    provider relationship is observed, never declared.

    Args:
        producer: The entry and the grant that made it effective.
        dispatched: The dispatch result. A ``ToolInvocation`` is refused: a
            tool dispatch is an effect-as-value that this SDK never executes,
            so nothing was produced and there is no child to admit.
        touched_entities: For a ``local-dispatch`` child only — what the
            child's own persisted execution record says it read. Supplying it
            for a remote acquisition is refused rather than ignored, because a
            consumer cannot have read a provider's internal replay store and a
            value that arrived anyway is not evidence.

    Raises:
        ProvenanceForgeryError: the dispatch names a different skill than the
            grant resolved, the dispatch kind produces no product, or
            ``touched_entities`` was supplied for an acquisition that cannot
            have them.
    """
    # `D-IMPL-337`. **PROVENANCE, not `isinstance`** — which this line was
    # until now, and the history is the argument.
    #
    # The second close panel's HIGH finding was that `ResolvedProducer` is
    # token-minted so it cannot be forged, and its ONLY consumer never asked
    # whether it had one: a `SimpleNamespace` carrying `entry.name`,
    # `entry.artifact_version`, `entry.skill_type` and `grant_hash` satisfied
    # every dereference below and minted a `ChildInvocation` recording a grant
    # hash that was in no ledger — measured, through the public import, as
    # `ACCEPTED: fake-skill 1.0.0 not-from-any-ledger`. The repair was
    # `isinstance`, which closed the duck-typed class.
    #
    # `D-IMPL-337` then measured that `isinstance` proves nominal membership
    # and NOT that the guarded path ran: a subclass skipping the guarded
    # `__init__` satisfies it while no grant was ever resolved. So the check
    # is the provenance the ledger read establishes.
    #
    # The three-fact cross-check below still does not help on its own and
    # could not: with a forged producer all three facts are values the SAME
    # caller authored, so they agree by construction. A capability token binds
    # nothing unless the consumer demands the provenance.
    producer = verify_resolved_producer_provenance(producer)
    mapped = _ACQUISITION_OF.get(type(dispatched).__name__)
    if mapped is None:
        raise ProvenanceForgeryError(
            f"a {type(dispatched).__name__} dispatch produces no Context"
            " Product, so there is no child to admit. A composite child comes"
            " from a local callable, an MCP resource or a peering endpoint"
            " (D-IMPL-336 Amendment 5)"
        )
    kind, expected_skill_type = mapped
    # THREE facts, held to each other. The result's type says how it was
    # acquired; the ENTRY says what kind of skill the grant made effective;
    # and the dispatch stamps its own `skill_type` onto the result it returns.
    # A real dispatch cannot make these disagree — only a hand-built result
    # can, which is what the close panel demonstrated.
    if producer.entry.skill_type != expected_skill_type:
        raise ProvenanceForgeryError(
            f"the grant made a {producer.entry.skill_type!r} skill effective"
            f" and the dispatch result is a {type(dispatched).__name__}, which"
            f" would record this child as {kind!r}. A remote product relabelled"
            " as locally produced would take the local invalidation register's"
            " authority for a decision it never saw (D-IMPL-336 Amendment 5)"
        )
    stamped = getattr(dispatched, "skill_type", None)
    if stamped != expected_skill_type:
        raise ProvenanceForgeryError(
            f"the dispatch result reports skill_type {stamped!r} and its own"
            f" type implies {expected_skill_type!r}; a result whose two halves"
            " disagree was not produced by ccf.skills.dispatch.dispatch_skill"
            " (D-IMPL-336 Amendment 5)"
        )
    name = getattr(dispatched, "skill_name", None)
    if name != producer.entry.name:
        raise ProvenanceForgeryError(
            f"the grant resolved skill {producer.entry.name!r} and the dispatch"
            f" result names {name!r}; an invocation record pairing one skill's"
            " authority with another skill's execution is the defect this"
            " evidence exists to prevent (D-IMPL-336 Amendment 5)"
        )
    if touched_entities is not None and kind != "local-dispatch":
        raise ProvenanceForgeryError(
            f"touched entities were supplied for a {kind!r} child. This fabric"
            " does not hold that provider's execution record, so the value"
            " cannot have been read from one — and admitting it would let the"
            " local invalidation register be claimed as an authority over a"
            " decision it never saw (D-IMPL-336 Amendment 5)"
        )
    if kind != "mcp-product":
        return ChildInvocation(
            skill_name=producer.entry.name,
            entry_version=producer.entry.artifact_version,
            grant_hash=producer.grant_hash,
            acquisition=kind,
            touched_entities=touched_entities,
            token=_INVOCATION_TOKEN,
        )
    # `D-IMPL-340`. The producer members are copied from a dispatch value the
    # registry MINTED — `verify_mcp_product_invocation` checks the mint, not
    # the class (`D-IMPL-337`) — so what admission holds the answer to is what
    # the deployment registered, never what a caller typed.
    asked = verify_mcp_product_invocation(dispatched)
    return ChildInvocation(
        skill_name=producer.entry.name,
        entry_version=producer.entry.artifact_version,
        grant_hash=producer.grant_hash,
        acquisition=kind,
        touched_entities=touched_entities,
        token=_INVOCATION_TOKEN,
        producer_id=asked.producer_id,
        producer_tenant=asked.producer_tenant,
        producer_registration_address=asked.producer_registration_address,
        producer_server=asked.server,
        question_address=asked.question_address,
    )


@dataclass(frozen=True)
class ChildCandidate:
    """One served child, with everything admission needs to judge it.

    ``contract`` is the typed product the provider served, and
    ``content_address`` is what its door reported. The gate **recomputes** the
    address from the contract rather than trusting the reported one, on the
    ``DoorOutcome`` discipline: a consumer's hash of the producer's bytes is
    the check, and a value taken on faith checks nothing.

    **`D-IMPL-336` Amendment 5 removed the ``provenance`` member.** It carried
    a parallel authorization layer — an attestor-minted "this fabric produced
    it" or a hand-carried peer envelope — on top of the grant that had already
    authorized the invocation. What remains is the invocation (grant +
    dispatch) and, for a peered child alone, the peering gate's own verified
    result.
    """

    requirement: ChildRequirement
    contract: ContextProductContract
    content_address: str
    invocation: "ChildInvocation"
    #: `D-IMPL-336` **Amendment 5**. The peering gate's VERIFIED result, for a
    #: peered child and only for one. ``None`` for local and MCP acquisition.
    #:
    #: The composite does not verify a signature, check peer trust or read a
    #: protected header — :class:`~ccf.peering.admission.PeeringAdmissionGate`
    #: does all three and this type is the evidence it ran. Dave's ruling:
    #: *"composition consumes the verified result or refusal."*
    admission: AdmittedProduct | None = None
    #: `D-IMPL-340`. What the producer's door CLAIMED about itself, its echo of
    #: the question, and its own replay reference — three claims, all held to
    #: the invocation (the registration) by the producer admission leg and
    #: none of them an authority. ``None`` on every other acquisition kind.
    producer_assertion: ProducerAssertion | None = None
    question_echo: "WireRequest | None" = None
    child_replay_ref: str | None = None


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
        "_admitted_at",
        "_asked_at",
        "_candidate",
        "_child_provenance",
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
        admitted_at: datetime,
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
        self._admitted_at = admitted_at
        # `D-IMPL-337`. Set only inside `CompositeAdmissionGate.admit`, the
        # one path that ran every admission check. The type alone proves none
        # of them ran.
        self._child_provenance = _CHILD_ADMISSION_TOKEN

    @property
    def admitted_at(self) -> datetime:
        """When admission judged it, from the trusted runtime clock (`O3`).

        Distinct from :attr:`asked_at`, which is the one reconstruction instant
        every constituent of a composition shares. Carried so replay can say
        when each child was let in, not only what it was asked.
        """
        return self._admitted_at

    @property
    def candidate(self) -> ChildCandidate:
        """What was admitted, with its resolution evidence."""
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
    minted evidence — :class:`ChildInvocation`, carrying the grant the ledger
    made effective and the acquisition kind read off the dispatch result's own
    type — that a caller cannot author, so the gate verifies the child **and**
    its context. (Amendment 3 also minted a ``ChildProvenance`` here;
    **Amendment 5 removed it**, because it asked a second time whether an
    invocation the grant had already authorized was authorized.)

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

        invocation = candidate.invocation

        def refuse(reason: ChildRefusalReason, detail: str) -> ChildAdmissionRefusal:
            return ChildAdmissionRefusal(
                gate=GATE_CHILD_ADMISSION,
                detail=detail,
                product_class=requirement.product_class,
                reason=reason,
                reported_content_address=reported,
                verified_content_address=verified,
                # `D-IMPL-340`: a refusal on the producer leg still names the
                # exact producer relationship — from the invocation, i.e. the
                # registration, never from the answer.
                producer_id=invocation.producer_id,
                producer_tenant=invocation.producer_tenant,
                producer_registration_address=invocation.producer_registration_address,
                producer_server=invocation.producer_server,
                question_address=invocation.question_address,
            )

        if invocation.acquisition == "mcp-product":
            # `D-IMPL-340` ruling 3 and 8. The child was governed under its
            # PRODUCER's tenant, and the consumer's expectation of which
            # producer and which tenant comes from its own registration. The
            # composite's tenant is not compared here and is never set equal
            # to the producer's to pass; the local-dispatch check below is
            # not weakened.
            held = self._hold_to_registration(candidate, refuse)
            if held is not None:
                return held
        elif contract.tenant_id != self._tenant_id:
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
        if isinstance(established, EligibilityRefused):
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
            admitted_at,
            _CHILD_ADMISSION_TOKEN,
        )

    def _hold_to_registration(
        self,
        candidate: ChildCandidate,
        refuse: Callable[[ChildRefusalReason, str], ChildAdmissionRefusal],
    ) -> ChildAdmissionRefusal | None:
        """The producer leg (`D-IMPL-340`): hold three claims to the registration.

        The expectations — ``producer_id`` and ``producer_tenant`` — sit on
        the invocation, copied from the registration the registry resolved
        for the grant's binding. The candidate's contract, its door's producer
        assertion and its echo of the question are **claims**. Each is held to
        the expectation; a claim that matches merely fails to refuse, because
        the grant and the registration authorized the acquisition before any
        bytes arrived. Four refusals, each on exactly one path, and wrong
        producer is distinct from wrong producer tenant by ruling.
        """
        invocation = candidate.invocation
        contract = candidate.contract
        expected_tenant = invocation.producer_tenant
        expected_producer = invocation.producer_id
        assert expected_tenant is not None and expected_producer is not None
        if contract.tenant_id != expected_tenant:
            return refuse(
                "producer-tenant-mismatch",
                f"the child was governed under tenant {contract.tenant_id!r}"
                f" and the producer registration expects {expected_tenant!r};"
                " the registration is the authority for the producer-side"
                " tenant and the answer is evidence held against it"
                " (D-IMPL-340)",
            )
        replay_ref = candidate.child_replay_ref
        if replay_ref is not None:
            claimed_tenant = _replay_ref_tenant(replay_ref)
            if claimed_tenant != expected_tenant:
                return refuse(
                    "producer-tenant-mismatch",
                    f"the child's replay reference sits under tenant"
                    f" {claimed_tenant!r} and the producer registration"
                    f" expects {expected_tenant!r}; a product and its record"
                    " are governed under one tenant (D-IMPL-340)",
                )
        assertion = candidate.producer_assertion
        if assertion is None:
            return refuse(
                "producer-unasserted",
                "the producer's door stamped no producer assertion on its"
                " answer, so there is nothing to hold to the registration's"
                f" expected producer {expected_producer!r}; a door built"
                " without an identity cannot be composed as a registered"
                " producer (D-IMPL-340)",
            )
        if assertion.producer_id != expected_producer:
            return refuse(
                "producer-mismatch",
                f"the answer asserts producer {assertion.producer_id!r} and the"
                f" registration expects {expected_producer!r}; the consumer"
                " contacted the registered endpoint and the answer names"
                " another producer, which is a misrouting to refuse, never an"
                " identity to adopt (D-IMPL-340)",
            )
        if assertion.tenant_id != expected_tenant:
            return refuse(
                "producer-tenant-mismatch",
                f"the answer asserts tenant {assertion.tenant_id!r} for"
                f" producer {expected_producer!r} and the registration expects"
                f" {expected_tenant!r} (D-IMPL-340)",
            )
        echo = candidate.question_echo
        if echo is None or content_hash(echo) != invocation.question_address:
            return refuse(
                "question-mismatch",
                "the producer's echo of the question does not match the"
                " question this composition sent"
                f" ({invocation.question_address!r}); an answer to a different"
                " question is not this child (D-IMPL-340)",
            )
        return None

    def _establish_eligibility(
        self,
        *,
        candidate: ChildCandidate,
        admitted_at: datetime,
        composition_invocation: str,
    ) -> tuple[str, EligibilityEvidence | None] | EligibilityRefused:
        """Answer *may this child still serve*, from the right authority.

        **`D-IMPL-336` Amendment 5 — the authority follows the PROVIDER
        RELATIONSHIP, not the transport.** Dave: *"MCP is not automatically
        peering… Apply the existing controls for the actual provider
        relationship."* So the three acquisitions answer differently, and each
        answer names the authority that actually gave it:

        * ``local-dispatch`` — this fabric ran the skill and holds the child's
          execution record, so its own invalidation register decides
          (`D-IMPL-334`/`D-IMPL-335`). The entities come from that record.
        * ``mcp`` — the provider's own authenticated, authorized access
          governed the read, and this fabric holds no execution record for it.
          The local register is **not consulted and not claimed**: reading its
          silence as a pass is exactly the *don't-know-collapsed-into-pass*
          failure this project's rules forbid.
        * ``peered`` — only the producer's verified attestation can establish
          it, and the verification lives in :mod:`ccf.peering.eligibility`.
          This method **consumes** its verdict; the five equality bindings and
          the declared age bound are no longer restated here.
        """
        acquisition = candidate.invocation.acquisition

        if acquisition == "local-dispatch":
            touched = candidate.invocation.touched_entities
            if touched is None:
                # **The close panel's headline finding, and it was a REGRESSION
                # this module introduced.** Amendment 3 closed `F3` by making
                # `touched_entities` always present; Amendment 5 made it
                # optional so a remote child need not force a read of its
                # provider's replay store — and left this leg admitting `None`.
                #
                # `refuse_dependency_invalidation` returns `None` immediately
                # for `None` (`gates.py`, the deliberate pre-`D-IMPL-334`
                # compatibility posture Dave ruled must not change), so the
                # register was never resolved and the row still recorded
                # `local-register` as the authority. Measured: a child on a
                # SUPERSEDED entity admitted, with the control beside it — the
                # same child with `touched` supplied refuses.
                #
                # A local child is one THIS fabric dispatched, so its execution
                # record is this fabric's to hold. Not holding one is *don't
                # know*, and don't-know must never read as *pass*. Unlike the
                # `mcp` leg below there is no other authority to name: nobody
                # checked. So it refuses, and it refuses as MISSING EVIDENCE
                # rather than as `ineligible` — the child may be perfectly
                # eligible; what is absent is the means to say so.
                return EligibilityRefused(
                    "eligibility-evidence-missing",
                    "this child was dispatched locally but carries no record of"
                    " what its execution read, so this fabric's invalidation"
                    " register cannot be consulted about it. Refused rather"
                    " than admitted: the register's silence here is 'not"
                    " asked', not 'nothing was superseded' (D-IMPL-336 F3,"
                    " re-opened and re-closed at the close panel)",
                )
            local_refusal = refuse_dependency_invalidation(
                candidate.contract,
                registry=self._registry,
                touched_entities=touched,
            )
            if local_refusal is not None:
                return EligibilityRefused(
                    "ineligible",
                    "this fabric's invalidation register refuses the child:"
                    f" {local_refusal.detail}",
                )
            return (ELIGIBILITY_LOCAL_REGISTER, None)

        if acquisition in ("mcp", "mcp-product"):
            # No local claim is made and none is available. The basis records
            # WHICH authority governed the read so a replay reader is never
            # left inferring that this fabric checked something it could not.
            return (ELIGIBILITY_PROVIDER_CONTROLS, None)

        admission = candidate.admission
        if admission is None:
            return EligibilityRefused(
                "provenance-unverified",
                "this child was acquired over a peering endpoint and carries no"
                " PeeringAdmissionGate result, so its signature, its peer's"
                " entitlement and its policy bindings are all unverified."
                " Composition does not verify them itself and does not admit"
                " on the transport's word (D-IMPL-336 Amendment 5)",
            )
        header = admission.protected_header
        if header is None:
            return EligibilityRefused(
                "provenance-unverified",
                "the peering admission carries no authenticated protected"
                " header, so nothing read from it could be attributed to the"
                " verified peer",
            )
        verdict = verify_child_eligibility(
            header=header,
            child_content_address=candidate.content_address,
            requested_as_of=candidate.contract.temporal_boundary,
            verified_producer=str(header.get(PRODUCER_ASSERTION_HEADER, "")),
            consumer_scope=self._consumer_scope,
            composition_invocation=composition_invocation,
            admitted_at=admitted_at,
            registry=self._registry,
            tenant_id=self._tenant_id,
        )
        if isinstance(verdict, EligibilityRefused):
            return verdict
        return (ELIGIBILITY_PRODUCER_ATTESTED, verdict)


@runtime_checkable
class CompositeChildResolverProtocol(Protocol):
    """Produce the admitted-or-refused child set for a composite (`D-IMPL-336`).

    **The SDK ships this Protocol AND a reference implementation** —
    :class:`~ccf.products.child_resolver.GrantBoundChildResolver` — under
    CLAUDE.md §11 (*"Reference implementations ship alongside Protocols"*).

    **This paragraph said the opposite until the close panel caught it**, and
    the correction is a ruling rather than a preference. Amendment 3 read
    §7.3/§8.1 — the SDK never ships an agent loop — as covering acquisition
    too. Dave's Amendment 5 settles it: resolving a requirement to a granted
    skill and dispatching it once is not a loop, and *"the skill that the
    composite agent has knows how to acquire the atomic context product and
    roll it in"*. What stays out of `src/` is the scheduler, the swarm loop and
    any new identity axis. A deployment substituting its own resolver still
    loses no capability.

    A conforming implementation:

    * reads ``requires`` **from the registered class**, never from a list a
      caller supplied;
    * resolves each requirement to an in-force grant with
      :func:`resolve_producing_grant`, and lets
      :class:`AmbiguousProducerError` propagate rather than picking one;
    * dispatches that grant's skill and delivers the child through its own
      governed door;
    * mints :class:`ChildInvocation` from the resolved entry and
      :class:`ChildInvocation` from the grant and the dispatch, and for a
      peered child the :class:`~ccf.peering.admission.AdmittedProduct` a
      verified peering
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
        consumer_lineage: ProductLineage,
    ) -> Mapping[str, object]:
        """Resolve, invoke, deliver and admit; return one outcome per class.

        ``consumer_lineage`` is the composing product's own L axis, which
        :meth:`~ccf.peering.admission.PeeringAdmissionGate.admit` requires to
        extend lineage by set-union at the boundary (`D-IMPL-336` Amendment 5).
        Passed because a resolver that acquires a peered child cannot verify it
        without one, and inventing a lineage on its behalf would make the
        union a fiction.
        """
        ...



@runtime_checkable
class RequestAwareChildResolverProtocol(Protocol):
    """A child resolver that takes the composite's EFFECTIVE request (`D-IMPL-340`).

    A **capability** Protocol on the `D-IMPL-339` precedent
    (:class:`~ccf.products.resolver.CompositePlanFactoryProtocol`): the
    resolver declares, structurally, that it wants the request the composite
    resolved — defaults applied, policy narrowed — so its child questions
    derive from the same authority chain every other argument travels.
    :class:`~ccf.products.resolver.GovernedResolver` calls ``resolve_for`` on
    a resolver that declares it and the legacy call on one that does not;
    :class:`CompositeChildResolverProtocol` is not widened, because *"adding a
    defaulted parameter to a Protocol does not make existing implementations
    accept that keyword."*

    Returns the same ``product class → outcome`` mapping the legacy call
    does, judged by the same gate.
    """

    def resolve_for(
        self,
        *,
        requirements: Sequence[ChildRequirement],
        request: ProductRequest,
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
        consumer_lineage: ProductLineage,
    ) -> Mapping[str, object]: ...

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


@dataclass(frozen=True)
class ChildOutcomeResolution:
    """Every declared requirement's disposition, re-bound to THIS composition.

    `D-IMPL-339`. The per-requirement walk :func:`compose_children` always
    performed — provenance (`D-IMPL-337`), slot / instant / invocation
    re-binding (Amendment 3), the four refusal branches and the one honest
    absence — factored out so it can run **before** the parent's plan is
    built, and so the read-only child-contract view the plan receives is
    derived only from children that passed it. :func:`compose_children` calls
    this and then applies the four composition laws to exactly what it
    returns; nothing about its behavior changed.

    Attributes:
        rows: One :class:`~ccf.replay.record.ChildResolution` per declared
            requirement, in declaration order — whether or not the walk
            refused.
        admitted: The admitted children, in declaration order.
        admitted_factors: Their debt factors, plus the declared-absence
            factor for each optional requirement nothing produced.
        refusal: The FIRST refusal the walk reached, or ``None``. **Any**
            refusal here is a known blocking outcome: a required child absent,
            an invoked child refused or rejected at admission, an unsupported
            object, an undeclared or duplicated slot. Optional absence is not
            a refusal and does not block.
    """

    rows: tuple[ChildResolution, ...]
    admitted: tuple[AdmittedChild, ...]
    admitted_factors: tuple[DebtFactors, ...]
    refusal: ChildAdmissionRefusal | None

    @property
    def blocking(self) -> bool:
        """Whether child-dependent computation must not run (`D-IMPL-339` Q2)."""
        return self.refusal is not None


class ChildContractView(Mapping[str, ContextProductContract]):
    """The admitted children's contracts, read-only, keyed by declared class.

    `D-IMPL-339`. What the parent's plan receives: **contracts, not admission
    machinery.** Built by :func:`child_contract_view` from a
    :class:`ChildOutcomeResolution` that reached no refusal — so every value
    here came through :meth:`CompositeAdmissionGate.admit` and was re-bound to
    this composition before the view existed — or, on replay, by
    :func:`ccf.replay.engine.replay` from the contracts retained by content
    address at decision time. It is a :class:`~collections.abc.Mapping` and
    nothing more: no setters, no invented graph view, no second acquisition.
    """

    __slots__ = ("_contracts",)

    def __init__(self, contracts: Mapping[str, ContextProductContract]) -> None:
        self._contracts: dict[str, ContextProductContract] = dict(contracts)

    def __getitem__(self, product_class: str) -> ContextProductContract:
        return self._contracts[product_class]

    def __iter__(self) -> Iterator[str]:
        return iter(self._contracts)

    def __len__(self) -> int:
        return len(self._contracts)

    def __repr__(self) -> str:
        return f"ChildContractView({sorted(self._contracts)})"


def child_contract_view(resolved: ChildOutcomeResolution) -> ChildContractView:
    """Derive the plan's view from a resolution that reached no refusal.

    Raises:
        ValueError: ``resolved`` carries a refusal. A view over a blocked
            composition would let child-dependent computation run on a set
            that is already known not to compose (`D-IMPL-339` Q2).
    """
    if resolved.refusal is not None:
        raise ValueError(
            "no child-contract view over a blocked composition:"
            f" {resolved.refusal.reason!r} on {resolved.refusal.product_class!r}"
            " (D-IMPL-339)"
        )
    return ChildContractView(
        {child.requirement.product_class: child.contract for child in resolved.admitted}
    )


def resolve_child_outcomes(
    *,
    requirements: Sequence[ChildRequirement],
    outcomes: Mapping[str, object],
    asked_at: datetime,
    composition_invocation: str,
) -> ChildOutcomeResolution:
    """The per-requirement walk, in declaration order (`D-IMPL-339`).

    Exactly the dispositions :func:`compose_children` has always made, and
    the only place they are made. See :class:`ChildOutcomeResolution`.
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
            return ChildOutcomeResolution(
                admitted=(),
                admitted_factors=(),
                # No rows: the declaration itself is incoherent, so there is no
                # per-requirement disposition to record. Distinct from the
                # undeclared-key case below, which HAS dispositions.
                rows=(),
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

        # `D-IMPL-337`. **PROVENANCE, not `isinstance`.** This branch decides
        # whether a value is a governed child, so it is an authority decision
        # and the ruled invariant applies: a subclass of `AdmittedChild` that
        # skipped the gate satisfies `isinstance` while no admission check ran.
        #
        # **`outcomes` stays `Mapping[str, object]`, deliberately** — the F13
        # reasoning is unchanged and is the reason this works: a narrow type
        # would let mypy prove the guard below unreachable, which is exactly
        # the assumption that once let a raw contract be read as *nothing was
        # produced*.
        #
        # **The branch ORDER is load-bearing and unchanged.** A forgery falls
        # past this test to the `unsupported-outcome` branch below — it must
        # never become an honest absence (`None`) or a governed child refusal,
        # because neither of those is what happened.
        if _has_child_provenance(outcome):
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
                        producing_fabric=_provider_of(outcome.candidate),
                        refusal_ref=reason,
                        producer_id=outcome.candidate.invocation.producer_id,
                        producer_tenant=outcome.candidate.invocation.producer_tenant,
                        producer_registration_address=(
                            outcome.candidate.invocation.producer_registration_address
                        ),
                        producer_server=outcome.candidate.invocation.producer_server,
                        child_question_address=(
                            outcome.candidate.invocation.question_address
                        ),
                        child_replay_ref=outcome.candidate.child_replay_ref,
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
                    producer_id=outcome.producer_id,
                    producer_tenant=outcome.producer_tenant,
                    producer_registration_address=(
                        outcome.producer_registration_address
                    ),
                    producer_server=outcome.producer_server,
                    child_question_address=outcome.question_address,
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

    return ChildOutcomeResolution(
        rows=tuple(rows),
        admitted=tuple(admitted_children),
        admitted_factors=tuple(admitted_factors),
        refusal=refusal,
    )


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
    resolved = resolve_child_outcomes(
        requirements=requirements,
        outcomes=outcomes,
        asked_at=asked_at,
        composition_invocation=composition_invocation,
    )
    rows = list(resolved.rows)
    admitted_factors = list(resolved.admitted_factors)
    admitted_children = list(resolved.admitted)
    refusal = resolved.refusal
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
    # `D-IMPL-340`. The producer leg's identity and tenancy checks are
    # authorization-shaped; an echo that does not match the question sent is
    # a produced product that did not meet the contract; and a registered
    # producer that could not answer keeps its own token (ruling 1).
    "producer-tenant-mismatch": "unauthorized",
    "producer-mismatch": "unauthorized",
    "producer-unasserted": "unauthorized",
    "question-mismatch": "rejected-at-admission",
    "producer-unavailable": "producer-unavailable",
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


def _replay_ref_tenant(replay_ref: str) -> str | None:
    """The tenant segment of a ``ccf-artifact://<tenant>/<class>/<name>@<v>`` URI.

    Read as text and never resolved: this fabric holds no remote provider's
    store (`D-IMPL-336` Amendment 5), so the reference is a claim the producer
    leg holds to the registration, not a record it fetches. ``None`` for a
    reference of any other shape, which the leg then treats as a mismatch.
    """
    prefix = "ccf-artifact://"
    if not replay_ref.startswith(prefix):
        return None
    rest = replay_ref[len(prefix):]
    tenant, separator, _ = rest.partition("/")
    return tenant if separator and tenant else None


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


def _provider_of(candidate: ChildCandidate) -> str | None:
    """Name the provider an eligibility claim was made ABOUT.

    Shared by the admitted and the rejected row alike: the panel's F6 point was
    that a mislabelled production left no trace, and a rejected child whose
    provider went unrecorded would leave the same gap on the other branch.

    **`D-IMPL-336` Amendment 5** reads this off evidence rather than off a
    provenance label. A peered child names the peer the peering gate VERIFIED.
    A local or MCP child names no fabric, and that is correct rather than
    missing: naming one would be this fabric asserting an identity for a
    producer it did not authenticate, which is the whole class of claim
    Amendment 5 removed.
    """
    if candidate.invocation.acquisition == "mcp-product":
        # `D-IMPL-340`: the registered producer — a governed name the
        # deployment declared, not an identity this fabric authenticated.
        return candidate.invocation.producer_id
    admission = candidate.admission
    return None if admission is None else admission.peer.peer_id


def _row_for_admitted(
    requirement: ChildRequirement, admitted: AdmittedChild
) -> ChildResolution:
    """Every field admission checked, recorded — nothing re-derived later."""
    candidate = admitted.candidate
    contract = admitted.contract
    debt = contract.debt
    assert debt is not None  # admission refuses an unassessable child
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
        # `R5`: the lineage REF identifies, these two REBUILD. A composite's
        # lineage is the union over its children's and its expiry is floored by
        # the stalest of them, so without both a rehydrator cannot reproduce
        # the composite — and therefore cannot reproduce its content address.
        child_operators_invoked=contract.lineage.operators_invoked,
        child_expires_at=contract.expires_at,
        child_admitted_at=admitted.admitted_at,
        eligibility_basis=admitted.eligibility_basis,
        # F6: name the provider the basis was claimed about.
        producing_fabric=_provider_of(candidate),
        # F7: the producer's check instant and the assertion it came from.
        child_eligibility_checked_at=(
            evidence.checked_at if evidence is not None else None
        ),
        child_eligibility_assertion_address=(
            evidence.assertion_address if evidence is not None else None
        ),
        producer_id=candidate.invocation.producer_id,
        producer_tenant=candidate.invocation.producer_tenant,
        producer_registration_address=(
            candidate.invocation.producer_registration_address
        ),
        producer_server=candidate.invocation.producer_server,
        child_question_address=candidate.invocation.question_address,
        child_replay_ref=candidate.child_replay_ref,
    )
