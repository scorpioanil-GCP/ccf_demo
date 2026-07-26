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
from typing import Literal, Protocol, runtime_checkable

from pydantic import field_validator

from ccf.agents.definitions import AgentDefinition
from ccf.artifacts.protocol import parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import ArtifactClass, validate_semver
from ccf.controlplane.audit import AuditAction, AuditLog
from ccf.controlplane.registry import (
    ControlPlaneMissing,
    ControlPlaneRegistry,
    RegistrationRefusal,
)
from ccf.replay.record import NO_GRANTS_SET_HASH
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry

__ccf_mode__ = "algorithmic"

__all__ = [
    "GOVERNANCE_FIELD",
    "SKILL_GRANT",
    "ApprovalOutcome",
    "ApprovalRejected",
    "ApprovalSink",
    "GovernanceUndeclared",
    "GrantLedger",
    "GrantRefusal",
    "GrantState",
    "GrantTransitionError",
    "PolicyRegimeGovernance",
    "PolicyRegimeUnresolvable",
    "RequirementsExceedRegime",
    "SkillGrant",
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


def grant_set_hash(active_grant_hashes: frozenset[str]) -> str:
    """The D-07 identity of an in-force grant set.

    Exactly ``content_hash(frozenset(...))``: canonical serialization sorts
    set members by their own canonical bytes, so the hash is deterministic
    across arrival orders and revocation restores the prior value. No epoch
    counter exists — the set's content is its entire identity (D-07;
    05-RESEARCH.md Pitfall 3).
    """
    return content_hash(frozenset(active_grant_hashes))


class _BoundSkills(Mapping[str, SkillCatalogEntry]):
    """A live, read-only view of one agent's currently-bound skill-set.

    What the harness adapter surfaces as tools (CLAUDE.md §7.3 seam 2):
    skills the agent has not been granted do not exist from this view.
    Resolved from ledger state at access time, so grant and revocation are
    visible immediately without the agent's identity ever changing
    (channel separation, §6.2).
    """

    def __init__(self, ledger: "GrantLedger", agent_definition_hash: str) -> None:
        self._ledger = ledger
        self._agent_definition_hash = agent_definition_hash

    def _current(self) -> dict[str, SkillCatalogEntry]:
        return self._ledger._effective_entries(self._agent_definition_hash)

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

    Args:
        control_plane: The registry grants register into and policy regimes
            resolve from (D-05 versioned path; pinned resolution only).
        catalog: The skill catalog entries are resolved from, by pinned
            version (05-05).
        audit: The append-only log every transition lands in (T-05-16).
        sink: The tier-2 decision surface (D-09).
        clock: Time source for audit timestamps. Injected, never read.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneRegistry,
        catalog: SkillCatalog,
        audit: AuditLog,
        sink: ApprovalSink,
        clock: Callable[[], datetime],
    ) -> None:
        self._control_plane = control_plane
        self._catalog = catalog
        self._audit = audit
        self._sink = sink
        self._clock = clock
        self._states: dict[str, GrantState] = {}
        self._grants: dict[str, SkillGrant] = {}

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

        The same ``{tenant}/{class}/{name}`` key convention and declared-
        version matching the Agent Factory applies (DESIGN.md §3.5); a
        content hash is also accepted as the URI version (D-IMPL-26).
        """
        name = parse_artifact_uri(ref)
        key = f"{name.tenant_id}/{name.artifact_class}/{name.name}"
        for version in self._control_plane.versions(key):
            if version == name.artifact_version:
                return self._control_plane.resolve(key, version)
            try:
                artifact = self._control_plane.resolve(key, version)
            except ControlPlaneMissing:  # pragma: no cover - versions listed
                continue
            declared = getattr(artifact, "artifact_version", None) or getattr(
                artifact, "semver", None
            )
            if declared == name.artifact_version:
                return artifact
        return None

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

        The sequence is fixed: register the grant artifact (D-05 versioned
        path), audit ``grant_requested``, run tier 1, then — only if the
        regime requires it — suspend on the sink. Tier 1 always runs before
        tier 2; a sink never sees a grant tier 1 refused.

        Raises:
            GrantTransitionError: this grant was already decided — a decided
                grant is immutable history; issue a new grant artifact.
            GrantTransitionError: ``grant.agent_definition_hash`` is not the
                content hash of ``definition`` — broken wiring, not a
                governance outcome.
            ccf.skills.catalog.SkillNotInCatalog: the referenced entry is not
                registered at the pinned version (a deployment error).
        """
        grant_hash = content_hash(grant)
        if grant_hash in self._states:
            raise GrantTransitionError(
                f"grant {grant.name!r} ({grant_hash!r}) was already decided"
                f" ({self._states[grant_hash]!r}); a decided grant is"
                " immutable history — issue a new grant artifact (D-09)"
            )
        if grant.agent_definition_hash != content_hash(definition):
            raise GrantTransitionError(
                "grant.agent_definition_hash does not equal the content hash"
                f" of the supplied definition ({grant.agent_definition_hash!r}"
                f" != {content_hash(definition)!r}); a grant references its"
                " agent by canonical identity (D-IMPL-26)"
            )
        registered = self._control_plane.register_versioned(
            skill_grant_key(grant), grant, SKILL_GRANT, actor=actor
        )
        if isinstance(registered, RegistrationRefusal):
            return registered

        self._states[grant_hash] = "requested"
        self._grants[grant_hash] = grant
        self._record(grant, "grant_requested", resolved=True, actor=actor)

        entry = self._catalog.resolve(
            grant.tenant, grant.skill_name, grant.skill_version
        )
        verdict = self._tier_1(grant, definition, entry)
        if isinstance(verdict, GrantRefusal):
            self._states[grant_hash] = "refused"
            self._record(grant, "grant_refused", resolved=False, actor=actor)
            return verdict

        if verdict.grant_requires_approval:
            self._states[grant_hash] = "pending-approval"
            self._record(
                grant, "grant_pending_approval", resolved=True, actor=actor
            )
            outcome = self._sink.decide(grant)
            if not outcome.approved:
                self._states[grant_hash] = "refused"
                self._record(
                    grant,
                    "grant_refused",
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

        self._states[grant_hash] = "effective"
        self._record(
            grant, "grant_effective", resolved=True, actor=effective_actor
        )
        return grant_hash

    def revoke(self, grant_hash: str, *, actor: str) -> None:
        """Revoke one effective grant.

        Raises:
            GrantTransitionError: the hash names no grant this ledger has
                decided, or the grant is not currently effective — the
                machine defines revocation from ``effective`` only.
        """
        state = self._states.get(grant_hash)
        if state != "effective":
            raise GrantTransitionError(
                f"cannot revoke grant {grant_hash!r}: its state is"
                f" {state!r}, and revocation is defined from 'effective'"
                " only (D-09)"
            )
        grant = self._grants[grant_hash]
        self._states[grant_hash] = "revoked"
        self._record(grant, "grant_revoked", resolved=True, actor=actor)

    # -- introspection and identity --------------------------------------------

    def state(self, grant_hash: str) -> GrantState:
        """Return the current state of one decided grant.

        Raises:
            KeyError: the hash names no grant this ledger has seen.
        """
        return self._states[grant_hash]

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
            for grant_hash, state in self._states.items()
            if state == "effective"
            and (
                agent_definition_hash is None
                or self._grants[grant_hash].agent_definition_hash
                == agent_definition_hash
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

    def _effective_entries(
        self, agent_definition_hash: str
    ) -> dict[str, SkillCatalogEntry]:
        entries: dict[str, SkillCatalogEntry] = {}
        for grant_hash in sorted(self.effective_hashes()):
            grant = self._grants[grant_hash]
            if grant.agent_definition_hash != agent_definition_hash:
                continue
            entries[grant.skill_name] = self._catalog.resolve(
                grant.tenant, grant.skill_name, grant.skill_version
            )
        return entries

    def bound_view(
        self, agent_definition_hash: str
    ) -> Mapping[str, SkillCatalogEntry]:
        """A live read-only view of one agent's currently-bound skill-set.

        The mapping the Agent Factory hands to ``Agent`` as ``bound_skills``:
        resolved from ledger state at invoke time, so grants and revocations
        take effect without re-declaring the agent — skill-set changes never
        touch agent identity (CLAUDE.md §6.2; D-07).
        """
        return _BoundSkills(self, agent_definition_hash)
