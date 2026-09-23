"""The two-tier skill grant machinery (CLAUDE.md §6.2 channel 2; D-IMPL-29).

SDK-defined extension (CLAUDE.md §6, not whitepaper-derived). A grant is how
a capability reaches an agent: a declared, versioned Control Plane artifact
referencing the agent definition by content hash and the catalog entry by
pinned version, admitted through two tiers of governance (D-IMPL-29):

**Tier 1 — the non-waivable policy-compatibility check.** Structural set
logic over opaque identifiers, never interpretation: the entry's declared
``required_scopes`` must be a subset of the policy regime's permitted scopes,
and its ``required_context_products`` a subset of the product classes the
agent's context contract consumes. An agent whose policy regime is missing,
unresolvable, or ungoverned cannot be granted anything — refusal, never a
silent default (D-IMPL-38; 05-RESEARCH.md Pitfall 4). Tier-1 refusals are
*returned* typed values in the
:class:`~ccf.products.gates.GateRefusal` style: a refused grant is a normal
governance outcome the caller inspects, not a broken fabric.

**Tier 2 — the approval workflow, behind the ApprovalSink Protocol.** Whether
a grant needs approval is the policy regime artifact's statement (the
``skill_governance`` block), never code. The state machine — requested →
pending-approval → effective/refused, plus revoked — runs the same way for
every sink (D-09): I.2 decides through a scripted test double; I.4's real
ApprovalGate joins with zero state-machine change.

**Every transition is audited** through the injected
:class:`~ccf.controlplane.audit.AuditLog` with the injected clock, refusals
included (``resolved=False``) — the audit plane is only credible if it
records what it turned away (T-05-16).

**The in-force skill-set has its own identity (D-07):**
``content_hash(frozenset(active grant hashes))``. A frozenset, deliberately:
canonical serialization sorts set members by their own canonical bytes, so
the hash is arrival-order-independent and revocation restores the prior
value exactly. No epoch counter and no version bump exists here — skilling
changes what an agent *can currently do*, never *who it is* (channel
separation, CLAUDE.md §6.2).

This module holds no scope vocabulary, no approval rule, and no approver
(CLAUDE.md §11, CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.controlplane.audit import AuditAction, AuditEvent, AuditLog
from ccf.controlplane.state import AuditedStateWriter
from ccf.controlplane.registry import (
    ControlPlaneRegistry,
    RegistrationRefusal,
)
from ccf.controlplane.resolution import resolve_pinned
from ccf.replay.record import NO_GRANTS_SET_HASH
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry

if TYPE_CHECKING:
    # Annotation-only: importing the agents package at runtime would create a
    # cycle now that ccf.agents.agent imports BoundSkillView from this module
    # (WR-03 typed seam).
    from ccf.agents.definitions import AgentDefinition

__ccf_mode__ = "algorithmic"

__all__ = [
    "GOVERNANCE_FIELD",
    "GRANT_STATE",
    "SKILL_GRANT",
    "ApprovalOutcome",
    "ApprovalRejected",
    "ApprovalSink",
    "BoundSkillView",
    "GovernanceUndeclared",
    "GrantCollisionError",
    "GrantLedger",
    "GrantRefusal",
    "GrantState",
    "GrantStateRecord",
    "GrantTransitionError",
    "PolicyRegimeGovernance",
    "PolicyRegimeUnresolvable",
    "RefusingApprovalSink",
    "RequirementsExceedRegime",
    "SkillGrant",
    "SplitAuditPlaneError",
    "TenantMismatch",
    "grant_set_hash",
    "skill_grant_key",
]

#: The grant states (D-09). ``requested`` is transient — a request resolves
#: to effective or refused within one :meth:`GrantLedger.request` call in
#: I.2, because the sink decides synchronously; the state exists so I.4's
#: suspending gate extends the machine without re-shaping it.
GrantState = Literal[
    "requested", "pending-approval", "effective", "refused", "revoked"
]

#: The record class grant state occupies on the Control Plane's state seam
#: (:mod:`ccf.controlplane.state`). Namespaces grant state away from every
#: other mutable-state machine sharing one store — I.4's suspended workflow
#: state foremost. Mechanism identifier, not a domain value.
GRANT_STATE = "ccf.skill-grant-state"


CHECK_TIER_1 = "tier-1-policy-compatibility"
CHECK_TIER_2 = "tier-2-approval"

#: The field inside a policy-regime declaration that carries the
#: :class:`PolicyRegimeGovernance` envelope. Mechanism schema, not a domain
#: value — the SDK names the envelope exactly as it names ``requirements`` on
#: a catalog entry; which scopes the envelope permits and whether grants need
#: approval are the deployment's statements, made in its own artifacts.
GOVERNANCE_FIELD = "skill_governance"


class GrantTransitionError(RuntimeError):
    """A grant state transition that the machine does not define.

    Raised — never repaired — because an undefined transition (revoking a
    refused grant, re-requesting a decided one) is broken wiring in the
    caller, not an expected governance outcome (I.1 refusal-vs-exception
    line: refusals are values; a misused state machine is an exception).
    """


class SplitAuditPlaneError(ValueError):
    """A ledger was handed an audit log its registry does not record into.

    Raised — never reconciled — because the Control Plane *is* the audit
    plane (INV-CH7-71; CLAUDE.md §10), singular. A ledger auditing into one
    log while the registry its grants register into audits into another
    produces two partial journals and no complete one: the registration of a
    grant would live in one, its ``grant_effective`` transition in the other,
    and neither would answer "what was in force" on its own. The WR-07
    closure established the singular plane by making a shared log
    *injectable*; this makes it unavoidable (IN-03).
    """


class GrantCollisionError(RuntimeError):
    """Two effective grants bind the same skill name for one agent (WR-05).

    Raised — never resolved by hash order — because a same-name
    double-effective state is a governance-state defect the operator must
    repair (revoke one grant), not an ordering choice the SDK may silently
    make: during an upgrade window the bound version would otherwise be a
    hash-lottery while the dimension-4 grant-set hash included both.
    Carries the skill name and both grant hashes.
    """

    def __init__(
        self, skill_name: str, first_hash: str, second_hash: str
    ) -> None:
        self.skill_name = skill_name
        self.first_hash = first_hash
        self.second_hash = second_hash
        super().__init__(
            f"two effective grants bind skill {skill_name!r} for one agent"
            f" ({first_hash!r} and {second_hash!r}); a same-name"
            " double-effective state is a governance-state defect — revoke"
            " one grant (D-09; WR-05)"
        )


class SkillGrant(CCFContract):
    """One skill grant — a declared, versioned Control Plane artifact.

    CLAUDE.md §6.2 channel 2; D-IMPL-12/29. A grant *references*, never
    copies: the agent by definition content hash (D-IMPL-26 canonical
    identity) and the catalog entry by pinned version — upgrading a skill is
    a new entry version and a new grant, both audited. The grant's own
    content hash is its identity and the member the D-07 grant-set hash is
    computed over.

    Two-field versioning per D-IMPL-28: ``schema_version`` is this class's
    lane; ``artifact_version`` is the author's content claim, hash-verified
    at registration (D-05).
    """

    schema_version: str
    artifact_version: str
    name: str
    tenant: str
    agent_definition_hash: str
    skill_name: str
    skill_version: str

    @field_validator("schema_version", "artifact_version")
    @classmethod
    def _versions_are_semver(cls, value: str) -> str:
        return validate_semver(value)


#: The skill-grant artifact class (CLAUDE.md §6.2; D-IMPL-29).
SKILL_GRANT = ArtifactClass(class_id="ccf.skill-grant", contract=SkillGrant)


def skill_grant_key(grant: SkillGrant) -> str:
    """The Control Plane key a grant registers under.

    The ``{tenant}/{artifact_class}/{name}`` convention every other artifact
    uses — derived from the grant and the class identity, never spelled by a
    caller.
    """
    return f"{grant.tenant}/{SKILL_GRANT.class_id}/{grant.name}"


class GrantStateRecord(CCFContract):
    """One grant's mutable state, as it lives on the Control Plane seam.

    Mutable *until terminal* in the D-IMPL-27 sense — the machine replaces
    this record as the grant transitions — while the record itself is a
    value, like every contract here. It pairs the state with the grant it
    describes because the ledger's replay-facing folds need the grant's
    ``agent_definition_hash`` and ``skill_name`` to answer per-agent
    questions, and re-resolving each from the registry on every fold would
    make a set-identity computation depend on resolution succeeding.

    Attributes:
        state: Where this grant sits in the D-09 machine.
        grant: The grant artifact this state belongs to.
    """

    state: GrantState
    grant: SkillGrant


class PolicyRegimeGovernance(CCFContract):
    """The skilling envelope a policy regime declares (D-IMPL-29 tier 1/2).

    The mechanism-schema block the tier-1 check compares against and the
    tier-2 flag is read from. Both members are required with no default: a
    regime that says nothing about skilling has not permitted anything, and
    an agent bound to it cannot be granted anything (D-IMPL-38).

    Attributes:
        permitted_scopes: The envelope of requirement identifiers agents
            under this regime may bind. Opaque to the SDK (Pitfall 4).
        grant_requires_approval: Whether tier 2 routes grants through the
            ApprovalSink. The deployment's statement, never code (D-09).
    """

    permitted_scopes: frozenset[str]
    grant_requires_approval: bool


class GrantRefusal(CCFContract):
    """Base of the structured refusals the grant machinery returns.

    The :class:`~ccf.products.gates.GateRefusal` discipline: a refusal is a
    returned value a caller cannot swallow with a bare ``except`` and cannot
    accidentally proceed past — there is no effective grant in its hands to
    proceed with.

    Attributes:
        check: Which governance check refused (tier 1 or tier 2).
        detail: Human-readable statement for the operator reading a log; the
            typed subclass fields carry the machine-readable version.
    """

    check: str
    detail: str


class PolicyRegimeUnresolvable(GrantRefusal):
    """Tier 1: the agent's policy regime resolves to nothing.

    An agent definition without a resolvable policy regime cannot be granted
    anything — refusal, never a silent default (D-IMPL-29; D-IMPL-38).
    """

    ref: str


class GovernanceUndeclared(GrantRefusal):
    """Tier 1: the policy regime declares no valid skilling envelope.

    A regime silent about skilling has permitted nothing. Silence and an
    explicit empty envelope are different author statements (D-IMPL-38).
    """

    ref: str


class RequirementsExceedRegime(GrantRefusal):
    """Tier 1: the entry's declared requirements exceed the agent's envelope.

    Both excess sets are carried — opaque identifiers, structurally compared
    — so the caller sees exactly what the regime or context contract would
    have to permit, without re-deriving either (T-05-15).
    """

    excess_scopes: frozenset[str]
    excess_context_products: frozenset[str]


class TenantMismatch(GrantRefusal):
    """Tier 1: the grant path crosses a tenant boundary (WR-02).

    A grant whose own tenant, or whose resolved catalog entry's tenant,
    differs from the agent definition's tenant is inadmissible: the skilling
    channel confers capabilities, and tenant isolation there is mechanism,
    not a deployment value. Modeled as a returned tier-1 governance refusal
    (not a transition error) because the artifact is well-formed and the
    caller may be handling third-party grant documents — the refusal is
    audited like every other tier-1 refusal (T-05-16).
    """

    grant_tenant: str
    entry_tenant: str
    definition_tenant: str


class ApprovalRejected(GrantRefusal):
    """Tier 2: the ApprovalSink rejected the grant.

    A rejection is a governance verdict, not an error; the approver id
    travels with the refusal because the refusal is audited under it.
    """

    approver_id: str


class ApprovalOutcome(CCFContract):
    """A sink's verdict on one grant (D-09).

    Attributes:
        approved: The verdict.
        approver_id: Who decided, as an id string the sink supplies. The SDK
            never synthesizes an identity; binding this id to a verified
            human principal is D-IMPL-21 (I.4) — accepted as out of scope for
            I.2 (T-05-19).
    """

    approved: bool
    approver_id: str


@runtime_checkable
class ApprovalSink(Protocol):
    """The tier-2 decision surface a grant suspends on (D-09).

    One method, deliberately: the state machine owns every transition and
    every audit record, so a conforming sink *cannot* drop the audit
    obligation — it never touches the log. It is handed the grant value and
    returns a typed verdict; everything else (how the decision was reached,
    whether a human was involved, how long it took) is the sink's business.
    I.2 conforms via a scripted test double; I.4's ApprovalGate conforms with
    zero state-machine change and joins the conformance suite unchanged.
    """

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        """Return the verdict for ``grant``."""
        ...


class RefusingApprovalSink:
    """The conforming sink for a deployment that has no tier-2 surface.

    `D-IMPL-346`. **It refuses; it is not a permissive default**, and the
    distinction is the whole reason this class exists rather than a defaulted
    ``sink=None``. A regime declaring ``grant_requires_approval`` and reaching a
    sink that approved would have the SDK deciding tier-2 on the deployment's
    behalf, which `D-IMPL-29` and `D-IMPL-343` refuse. The ledger's own
    no-wedged-states guard settles the grant ``refused`` and re-raises, so an
    open over such a regime fails at open, by name.

    **Why it is public.** It was the SDK's own private ``_NoApprovalSink``,
    reachable only through :func:`~ccf.products.product.open_product`. A
    deployment that builds a :class:`GrantLedger` directly — which a composite
    hand-building its consumer chain must — had to supply a sink it could not
    name, and cp-20 **copied the private class verbatim** into its own tree
    (`CLD-F-04`). A public need with no legal spelling is a surface defect; this
    is the spelling.

    A regime that does not require approval never consults a sink at all, so
    passing this is the correct declaration of *"no tier-2 surface here"*
    rather than a weakening of one.
    """

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        """Refuse by name, naming the argument the deployment did not supply."""
        raise ValueError(
            f"the policy regime requires approval for grant {grant.name!r} and"
            " this open supplied no `approval_sink=`; tier-2 approval is the"
            " deployment's decision surface and the SDK holds no default for"
            " it (D-IMPL-29; D-IMPL-343)"
        )


def grant_set_hash(active_grant_hashes: frozenset[str]) -> str:
    """The D-07 identity of an in-force grant set.

    Exactly ``content_hash(frozenset(...))``: canonical serialization sorts
    set members by their own canonical bytes, so the hash is deterministic
    across arrival orders and revocation restores the prior value. No epoch
    counter exists — the set's content is its entire identity (D-07;
    05-RESEARCH.md Pitfall 3).
    """
    return content_hash(frozenset(active_grant_hashes))


class BoundSkillView(Mapping[str, SkillCatalogEntry]):
    """A live, read-only view of one agent's currently-bound skill-set.

    What the harness adapter surfaces as tools (CLAUDE.md §7.3 seam 2):
    skills the agent has not been granted do not exist from this view.
    Resolved from ledger state at access time, so grant and revocation are
    visible immediately without the agent's identity ever changing
    (channel separation, §6.2).

    **Constructor discipline is module-private (WR-03).** The only supported
    producer is :meth:`GrantLedger.bound_view`; nothing outside this module
    constructs one. The type exists precisely so the Agent Factory's
    ``bound_skills`` seam admits ledger-produced views and nothing else —
    an arbitrary mapping cannot be injected at the supported construction
    path, which is what makes skill-set capture a by-construction property
    rather than caller discipline (CLAUDE.md §6.2).
    """

    def __init__(self, ledger: "GrantLedger", agent_definition_hash: str) -> None:
        self._ledger = ledger
        self._agent_definition_hash = agent_definition_hash

    def _current(self) -> dict[str, SkillCatalogEntry]:
        return self._ledger._effective_entries(self._agent_definition_hash)

    def grant_hash_for(self, name: str) -> str:
        """The hash of the grant that put ``name`` in force for this agent.

        `D-IMPL-336` **O2**. A bound skill is not authority on its own — the
        grant is — and until this method existed there was no supported way to
        ask which grant authorized a bound entry. Composite child invocation
        reads it here rather than accepting one, so the identity that reaches
        replay is the ledger's and never a caller's spelling of it.

        Resolved at access time from ledger state, like every other read on
        this view, so a revoked grant stops answering immediately.

        Raises:
            KeyError: ``name`` is not bound for this agent. Skills the agent
                has not been granted do not exist from this view, and asking
                for their authority is the same question as asking for them.
        """
        return self._ledger._effective_grants(self._agent_definition_hash)[name][0]

    def __getitem__(self, name: str) -> SkillCatalogEntry:
        return self._current()[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._current())

    def __len__(self) -> int:
        return len(self._current())


class GrantLedger:
    """The grant state machine, tier-1 check, and D-07 set identity.

    Everything is injected — registry, catalog, audit log, sink, clock — in
    the constructor-injection discipline of every Control Plane service:
    the ledger holds no keys, no vocabulary, and no wall clock of its own.

    **The ledger holds no state of its own (WR-05).** Grant *artifacts* are
    immutable and register append-only into the Control Plane; grant *state*
    is mutable until terminal and therefore lives on the Control Plane's
    state seam (:class:`~ccf.controlplane.state.ControlPlaneStateStore`),
    which is exactly where D-IMPL-27's mutability split and D-IMPL-18's
    "Control Plane's storage seam" place it. Two properties follow, and both
    are pinned by tests:

    * Any ledger over one Control Plane agrees with every other about which
      grants are effective. Reading state from the plane rather than from
      the reader makes divergence unrepresentable — the same shape as the
      catalog, whose membership derives from registry state (IN-03).
    * :meth:`grant_set_hash` is therefore reproducible on a freshly
      constructed ledger, which is what CLAUDE.md §6.2 requires of replay:
      a decision replays against the skill-set the agent actually had, and a
      set identity that only the deciding instance could compute would not
      survive the replay it exists to serve.

    Durability across a restart is the injected store's business, not the
    ledger's. The v0 default is in-process, matching the Control Plane it
    sits in (CLAUDE.md §13); a deployment that needs grant state to outlive
    the process supplies a conforming store and changes nothing here. The
    suspending ApprovalGate that I.4 brings inherits this seam rather than
    introducing a second answer.

    Args:
        control_plane: The registry grants register into and policy regimes
            resolve from (D-05 versioned path; pinned resolution only).
        catalog: The skill catalog entries are resolved from, by pinned
            version (05-05).
        audit: The append-only log every transition lands in (T-05-16).
            Optional, and constrained: the Control Plane is the audit plane
            and there is one of it (INV-CH7-71), so this defaults to — and
            may only be — ``control_plane.audit_log``. Passing any other log
            raises :class:`SplitAuditPlaneError` rather than silently
            splitting the journal (IN-03). The parameter survives its own
            redundancy only as an explicitness affordance for callers that
            prefer to name the log they are wiring.
        sink: The tier-2 decision surface (D-09).
        clock: Time source for audit timestamps. Injected, never read.

    Note:
        Grant state is read from and written to ``control_plane.state_store``
        under the :data:`GRANT_STATE` record class. The ledger caches none of
        it (WR-05).

    Raises:
        SplitAuditPlaneError: ``audit`` is a log other than
            ``control_plane.audit_log``.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneRegistry,
        catalog: SkillCatalog,
        sink: ApprovalSink,
        clock: Callable[[], datetime],
        audit: AuditLog | None = None,
    ) -> None:
        if audit is not None and audit is not control_plane.audit_log:
            raise SplitAuditPlaneError(
                "the ledger's audit log is not the log its Control Plane"
                " registry records into; grant registrations and grant"
                " transitions would land in two partial journals and no"
                " complete one. Omit `audit` (it defaults to"
                " `control_plane.audit_log`) or pass that same log"
                " (INV-CH7-71; CLAUDE.md §10; IN-03)"
            )
        audit = control_plane.audit_log if audit is None else audit
        self._control_plane = control_plane
        self._catalog = catalog
        self._audit = audit
        self._sink = sink
        self._clock = clock
        self._state_store = control_plane.state_store
        # The 07-02 D-20 closure: state writes travel the audited surface,
        # which appends the ledger's own domain transition event — one event
        # per transition, on the one shared log (D-08/D-09; INV-CH7-71).
        self._writer = AuditedStateWriter(
            store=control_plane.state_store, audit=audit
        )

    # -- state (on the Control Plane seam, never on this instance) -----------

    def _record_for(self, grant_hash: str) -> GrantStateRecord | None:
        """The state record for one grant, or ``None`` if unseen."""
        record = self._state_store.get(GRANT_STATE, grant_hash)
        if record is None:
            return None
        if not isinstance(record, GrantStateRecord):
            raise GrantTransitionError(
                f"the Control Plane state store returned a"
                f" {type(record).__name__} under grant state key"
                f" {grant_hash!r}, not a GrantStateRecord; the"
                f" {GRANT_STATE!r} record class is the grant machine's alone"
                " (D-IMPL-18/27)"
            )
        return record

    def _put_state(
        self,
        grant_hash: str,
        state: GrantState,
        grant: SkillGrant,
        *,
        action: AuditAction,
        resolved: bool,
        actor: str | None,
    ) -> None:
        """Write one grant's state through the audited write surface (D-09).

        Retrofitted onto :class:`~ccf.controlplane.state.AuditedStateWriter`
        in 07-02: the ledger's existing domain transition event travels as
        the write's required event, so the write evidence rides on the
        ``grant_*`` action itself — one event per transition, never a second
        generic entry (INV-CH7-71).
        """
        self._writer.write(
            GRANT_STATE,
            grant_hash,
            GrantStateRecord(state=state, grant=grant),
            event=AuditEvent(
                sequence=0,  # reassigned by the log; sequencing is its own
                action=action,
                key=skill_grant_key(grant),
                version=content_hash(grant),
                resolved=resolved,
                occurred_at=self._clock(),
                actor=actor,
                artifact_class=SKILL_GRANT.class_id,
            ),
        )

    def _records(self) -> tuple[tuple[str, GrantStateRecord], ...]:
        """Every grant state record on this Control Plane, hash-sorted."""
        return tuple(
            (grant_hash, record)
            for grant_hash, record in self._state_store.items(GRANT_STATE)
            if isinstance(record, GrantStateRecord)
        )

    # -- audit ---------------------------------------------------------------

    def _record(
        self,
        grant: SkillGrant,
        action: AuditAction,
        *,
        resolved: bool,
        actor: str | None,
    ) -> None:
        self._audit.append(
            action=action,
            key=skill_grant_key(grant),
            version=content_hash(grant),
            resolved=resolved,
            occurred_at=self._clock(),
            actor=actor,
            artifact_class=SKILL_GRANT.class_id,
        )

    # -- tier 1 ---------------------------------------------------------------

    def _resolve_policy_regime(self, ref: str) -> object | None:
        """Resolve the definition's pinned policy-regime ref, or ``None``.

        Delegates to the shared
        :func:`~ccf.controlplane.resolution.resolve_pinned` (IN-01), which is
        the same pinned-resolution rule the Agent Factory applies (DESIGN.md
        §3.5): ``{tenant}/{class}/{name}`` key derivation, a content hash
        accepted as the URI version (D-IMPL-26), declared-version probing
        through the unaudited
        :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.peek`, and one
        audited resolution on the content actually returned (WR-08).

        The ledger keeps the helper's ``None`` as ``None``: an unresolvable
        regime is a governance outcome here (tier 1 returns
        :class:`PolicyRegimeUnresolvable`), not the definition error the
        factory raises on the same miss.

        Raises:
            AmbiguousPinnedVersionError: two different contents under the key
                declare the same semver the ref pins (WR-08) — the tier-1
                governance input must be exactly one content.
        """
        return resolve_pinned(self._control_plane, ref)

    def _governance(
        self, regime: object, ref: str
    ) -> PolicyRegimeGovernance | GovernanceUndeclared:
        declaration = getattr(regime, "declaration", None)
        if not isinstance(declaration, Mapping):
            block = None
        else:
            block = declaration.get(GOVERNANCE_FIELD)
        if block is None:
            return GovernanceUndeclared(
                check=CHECK_TIER_1,
                ref=ref,
                detail=(
                    f"policy regime {ref!r} declares no {GOVERNANCE_FIELD!r}"
                    " envelope; a regime silent about skilling has permitted"
                    " nothing, and an agent bound to it cannot be granted"
                    " anything (D-IMPL-29; D-IMPL-38 — no silent defaults)"
                ),
            )
        try:
            return PolicyRegimeGovernance.model_validate(block)
        except ValueError as error:
            return GovernanceUndeclared(
                check=CHECK_TIER_1,
                ref=ref,
                detail=(
                    f"policy regime {ref!r} carries a malformed"
                    f" {GOVERNANCE_FIELD!r} envelope: {error} (D-IMPL-29)"
                ),
            )

    def _tier_1(
        self,
        grant: SkillGrant,
        definition: AgentDefinition,
        entry: SkillCatalogEntry,
    ) -> PolicyRegimeGovernance | GrantRefusal:
        """The non-waivable check: structural subset logic, opaque ids."""
        ref = definition.policy_regime.ref
        regime = self._resolve_policy_regime(ref)
        if regime is None:
            return PolicyRegimeUnresolvable(
                check=CHECK_TIER_1,
                ref=ref,
                detail=(
                    f"policy regime {ref!r} resolves to nothing the Control"
                    " Plane has registered; an agent without a policy regime"
                    " cannot be granted anything (D-IMPL-29; D-IMPL-38)"
                ),
            )
        governance = self._governance(regime, ref)
        if isinstance(governance, GovernanceUndeclared):
            return governance
        consumed = frozenset(
            product.product_class
            for product in definition.context_contract.consumes
        )
        excess_scopes = (
            entry.requirements.required_scopes - governance.permitted_scopes
        )
        excess_products = (
            entry.requirements.required_context_products - consumed
        )
        if excess_scopes or excess_products:
            return RequirementsExceedRegime(
                check=CHECK_TIER_1,
                excess_scopes=excess_scopes,
                excess_context_products=excess_products,
                detail=(
                    f"skill {entry.name!r} declares requirements the agent's"
                    f" envelope does not cover — excess scopes"
                    f" {sorted(excess_scopes)!r}, excess context products"
                    f" {sorted(excess_products)!r}; the tier-1 check is"
                    " structural and non-waivable (D-IMPL-29; T-05-15)"
                ),
            )
        return governance

    # -- the state machine -----------------------------------------------------

    def request(
        self,
        grant: SkillGrant,
        *,
        definition: AgentDefinition,
        actor: str,
    ) -> str | GrantRefusal | RegistrationRefusal:
        """Run one grant through both tiers; return its hash or a refusal.

        The sequence is fixed: resolve the referenced catalog entry (so a
        missing entry leaves the ledger untouched and the same grant content
        hash re-requestable once the entry exists — WR-04), verify tenant
        coherence (a returned :class:`TenantMismatch` refusal — WR-02),
        register the grant artifact (D-05 versioned path), audit
        ``grant_requested``, run tier 1, then — only if the regime requires
        it — suspend on the sink. Tier 1 always runs before tier 2; a sink
        never sees a grant tier 1 refused.

        **An inadmissible cross-tenant grant never enters the registry
        (IN-04).** The tenant check runs *before* registration, not after,
        because registration is append-only and irreversible: a grant whose
        tenant differs from its agent's would otherwise be written
        permanently under the *foreign* tenant's key namespace and stay
        resolvable there, in a Control Plane the requesting deployment owns
        but that tenant prefix does not belong to — a refusal that
        nonetheless leaves a durable artifact behind is not a refusal. The
        check needs only ``grant``, ``entry``, and ``definition``, all of
        which are in hand before anything is written. The grant is still
        settled terminally ``refused`` and the refusal still audited: the
        deployment learns what was turned away, and the Control Plane keeps
        nothing it turned away.

        **Retry after a refusal is a re-issued grant (WR-02).** A grant is
        single-use: once decided it is never re-requested. The supported
        retry — after a tier-2 rejection, or after a tier-1 refusal the
        deployment has since remedied by widening the regime — is a new grant
        artifact with a bumped ``artifact_version``, registered under the
        same key. Its content hash differs, so the state machine sees a fresh
        request, and the registration is admitted as a re-issue rather than
        refused as an empty bump. Renaming the grant is *not* required and is
        the wrong move: it mints a second Control Plane key for one request.

        **No path leaves a grant wedged (WR-01).** Once the first state
        mutation happens, every remaining step runs under an exception guard:
        any exception — including one raised by the injected
        :class:`ApprovalSink`, which is arbitrary Protocol code the ledger
        does not trust to return — settles the grant in the terminal
        ``refused`` state, audits the refusal, and re-raises unchanged. A
        grant is therefore never observable in ``requested`` or
        ``pending-approval`` after this call returns or raises, and no grant
        is left in a state the machine defines no exit from.

        Raises:
            GrantTransitionError: this Control Plane has already seen this
                grant — a grant artifact is single-use; issue a new grant
                artifact. Single-use is a property of the plane, not of the
                ledger instance that first saw it (WR-05).
            GrantTransitionError: ``grant.agent_definition_hash`` is not the
                content hash of ``definition`` — broken wiring, not a
                governance outcome.
            ccf.skills.catalog.SkillNotInCatalog: the referenced entry is not
                registered at the pinned version (a deployment error). Raised
                before any state mutation, after a ``grant_refused``
                (``resolved=False``) audit record — the audit plane records
                what it turned away without wedging a phantom request.
        """
        grant_hash = content_hash(grant)
        seen = self._record_for(grant_hash)
        if seen is not None:
            state = seen.state
            decided = state not in ("requested", "pending-approval")
            raise GrantTransitionError(
                f"grant {grant.name!r} ({grant_hash!r}) was already"
                f" {'decided' if decided else 'seen'} (state {state!r}); a"
                " grant artifact is single-use — issue a new grant artifact"
                " with a bumped artifact_version, which registers as a new"
                " request rather than an empty bump (D-09; WR-02)"
            )
        if grant.agent_definition_hash != content_hash(definition):
            raise GrantTransitionError(
                "grant.agent_definition_hash does not equal the content hash"
                f" of the supplied definition ({grant.agent_definition_hash!r}"
                f" != {content_hash(definition)!r}); a grant references its"
                " agent by canonical identity (D-IMPL-26)"
            )
        try:
            entry = self._catalog.resolve(
                grant.tenant, grant.skill_name, grant.skill_version
            )
        except LookupError:
            self._record(grant, "grant_refused", resolved=False, actor=actor)
            raise

        # Before registration, deliberately (IN-04). Registration is
        # append-only; a cross-tenant grant admitted here would be written
        # forever under the foreign tenant's key namespace and stay
        # resolvable there. Everything the check needs is already in hand.
        mismatch = self._tenant_mismatch(grant, definition, entry)
        if mismatch is not None:
            self._put_state(
                grant_hash,
                "refused",
                grant,
                action="grant_refused",
                resolved=False,
                actor=actor,
            )
            return mismatch

        # `reissuable` because a grant is a single-use *request*, not an
        # evolving document (WR-02). The documented remediation after a
        # tier-2 rejection is to issue a new grant artifact; that re-issue
        # legitimately differs from the declined one in `artifact_version`
        # alone, which the D-05 empty-bump refusal would otherwise reject —
        # leaving the retry path reachable only by renaming the grant, i.e.
        # by minting a second Control Plane key for the same request.
        registered = self._control_plane.register_versioned(
            skill_grant_key(grant), grant, SKILL_GRANT, actor=actor, reissuable=True
        )
        if isinstance(registered, RegistrationRefusal):
            return registered

        self._put_state(
            grant_hash,
            "requested",
            grant,
            action="grant_requested",
            resolved=True,
            actor=actor,
        )

        # No wedged states, on any path (WR-01). Everything after the first
        # state mutation runs under this guard: an exception raised downstream
        # — an ambiguous pinned policy regime, or an ApprovalSink (arbitrary
        # Protocol code) that raises rather than returning a verdict — would
        # otherwise strand the grant in `requested` / `pending-approval`
        # forever, states the machine defines no exit from (revocation is
        # defined from `effective` only). The guard settles the grant in the
        # terminal `refused` state and audits the refusal (T-05-16: the audit
        # plane records what it turned away) before re-raising the original
        # exception unchanged — the caller still sees the real failure.
        try:
            return self._decide(
                grant, grant_hash, definition=definition, entry=entry, actor=actor
            )
        except Exception:
            self._put_state(
                grant_hash,
                "refused",
                grant,
                action="grant_refused",
                resolved=False,
                actor=actor,
            )
            raise

    def _tenant_mismatch(
        self,
        grant: SkillGrant,
        definition: AgentDefinition,
        entry: SkillCatalogEntry,
    ) -> TenantMismatch | None:
        """The tenant-coherence check, as a pure verdict (WR-02; IN-04).

        Pure — it mutates nothing and audits nothing — precisely so it can
        run before registration, where the caller still has the option of
        writing nothing at all.
        """
        if (
            grant.tenant == definition.tenant
            and entry.tenant == definition.tenant
        ):
            return None
        return TenantMismatch(
            check=CHECK_TIER_1,
            grant_tenant=grant.tenant,
            entry_tenant=entry.tenant,
            definition_tenant=definition.tenant,
            detail=(
                f"grant tenant {grant.tenant!r} / entry tenant"
                f" {entry.tenant!r} do not both equal the agent"
                f" definition's tenant {definition.tenant!r}; the"
                " skilling channel never crosses a tenant boundary"
                " (WR-02; CLAUDE.md §6.2)"
            ),
        )

    def _decide(
        self,
        grant: SkillGrant,
        grant_hash: str,
        *,
        definition: AgentDefinition,
        entry: SkillCatalogEntry,
        actor: str,
    ) -> str | GrantRefusal:
        """Tier 1, then tier 2 — the decided part of the run.

        Split out of :meth:`request` so every post-mutation path sits inside
        one exception guard (WR-01); it carries no state-machine rule of its
        own beyond the transitions it performs. Tenant coherence is *not*
        checked here — it runs before registration (IN-04), so by the time
        this method is reached the grant is already known tenant-coherent.
        """
        verdict = self._tier_1(grant, definition, entry)
        if isinstance(verdict, GrantRefusal):
            self._put_state(
                grant_hash,
                "refused",
                grant,
                action="grant_refused",
                resolved=False,
                actor=actor,
            )
            return verdict

        if verdict.grant_requires_approval:
            self._put_state(
                grant_hash,
                "pending-approval",
                grant,
                action="grant_pending_approval",
                resolved=True,
                actor=actor,
            )
            outcome = self._sink.decide(grant)
            if not outcome.approved:
                self._put_state(
                    grant_hash,
                    "refused",
                    grant,
                    action="grant_refused",
                    resolved=False,
                    actor=outcome.approver_id,
                )
                return ApprovalRejected(
                    check=CHECK_TIER_2,
                    approver_id=outcome.approver_id,
                    detail=(
                        f"grant {grant.name!r} rejected by the approval sink"
                        f" (approver {outcome.approver_id!r}; D-09)"
                    ),
                )
            effective_actor = outcome.approver_id
        else:
            effective_actor = actor

        self._put_state(
            grant_hash,
            "effective",
            grant,
            action="grant_effective",
            resolved=True,
            actor=effective_actor,
        )
        return grant_hash

    def revoke(self, grant_hash: str, *, actor: str) -> None:
        """Revoke one effective grant.

        Raises:
            GrantTransitionError: the hash names no grant decided on this
                Control Plane, or the grant is not currently effective — the
                machine defines revocation from ``effective`` only.
        """
        record = self._record_for(grant_hash)
        state = None if record is None else record.state
        if record is None or state != "effective":
            raise GrantTransitionError(
                f"cannot revoke grant {grant_hash!r}: its state is"
                f" {state!r}, and revocation is defined from 'effective'"
                " only (D-09)"
            )
        self._put_state(
            grant_hash,
            "revoked",
            record.grant,
            action="grant_revoked",
            resolved=True,
            actor=actor,
        )

    # -- introspection and identity --------------------------------------------

    def state(self, grant_hash: str) -> GrantState:
        """Return the current state of one decided grant.

        Raises:
            KeyError: the hash names no grant on this Control Plane.
        """
        record = self._record_for(grant_hash)
        if record is None:
            raise KeyError(grant_hash)
        return record.state

    def effective_hashes(self, agent_definition_hash: str | None = None) -> frozenset[str]:
        """The content hashes of currently-effective grants.

        With ``agent_definition_hash`` supplied, only that agent's effective
        grants are returned — the per-agent view every replay-facing caller
        must use (CLAUDE.md §6.2: a decision replays against the skills *the
        agent* actually had). With ``None``, the ledger-wide view across all
        agents is returned — an operator-inspection convenience only, never
        an identity input for any one agent's replay record.
        """
        return frozenset(
            grant_hash
            for grant_hash, record in self._records()
            if record.state == "effective"
            and (
                agent_definition_hash is None
                or record.grant.agent_definition_hash == agent_definition_hash
            )
        )

    def grant_set_hash(self, agent_definition_hash: str) -> str:
        """The D-07 identity of one agent's in-force skill-set, at this instant.

        Per-agent, deliberately required: the value lands in replay
        dimension 4 as *this agent's* skill-set in force, so it is computed
        over exactly the grants referencing ``agent_definition_hash`` — a
        grant to another agent sharing this ledger never moves it
        (CLAUDE.md §6.2; CR-01).

        The positive :data:`~ccf.replay.record.NO_GRANTS_SET_HASH` claim when
        nothing is in force for this agent — "this agent holds zero effective
        grants" is asserted, never left as an absence a reader must interpret.
        """
        active = self.effective_hashes(agent_definition_hash)
        if not active:
            return NO_GRANTS_SET_HASH
        return grant_set_hash(active)

    def _effective_grants(
        self, agent_definition_hash: str
    ) -> dict[str, tuple[str, SkillCatalogEntry]]:
        """One agent's bound skills, each WITH the grant hash authorizing it.

        The grant hash was already resolved here — as ``holders``, to detect
        collisions — and then discarded. `D-IMPL-336` **O2** is what that
        discarding cost: the composite surface had no way to learn which grant
        authorized a bound skill, so ``invocation_from_dispatch`` took the
        hash as a caller-supplied string and the audit record named whatever
        the assembler typed. Returned now, so the authority and the capability
        travel together and the caller cannot substitute either.
        """
        grants: dict[str, tuple[str, SkillCatalogEntry]] = {}
        effective = dict(self._records())
        for grant_hash in sorted(self.effective_hashes()):
            grant = effective[grant_hash].grant
            if grant.agent_definition_hash != agent_definition_hash:
                continue
            if grant.skill_name in grants:
                raise GrantCollisionError(
                    grant.skill_name, grants[grant.skill_name][0], grant_hash
                )
            grants[grant.skill_name] = (
                grant_hash,
                self._catalog.resolve(
                    grant.tenant, grant.skill_name, grant.skill_version
                ),
            )
        return grants

    def _effective_entries(
        self, agent_definition_hash: str
    ) -> dict[str, SkillCatalogEntry]:
        return {
            name: entry
            for name, (_grant_hash, entry) in self._effective_grants(
                agent_definition_hash
            ).items()
        }

    def bound_view(self, agent_definition_hash: str) -> BoundSkillView:
        """A live read-only view of one agent's currently-bound skill-set.

        The typed :class:`BoundSkillView` the Agent Factory hands to
        ``Agent`` as ``bound_skills`` — this method is the type's only
        supported producer (WR-03): resolved from ledger state at invoke
        time, so grants and revocations take effect without re-declaring the
        agent — skill-set changes never touch agent identity
        (CLAUDE.md §6.2; D-07).
        """
        return BoundSkillView(self, agent_definition_hash)
