"""The versioned Control Plane registry (SDK-defined mechanism).

Whitepaper §7.8 (Control Plane / Data Plane separation; the Control Plane as
audit plane) and DESIGN.md §7; registry mechanics themselves are SDK-defined
per CLAUDE.md §10/§13. Three properties are load-bearing and are why this lands
before any subsystem that reads configuration — so no subsystem invents a
divergent stub:

**Append-only versioning.** Registering under a key that already has versions
appends; it never mutates or removes a prior version. A decision made at T
must still resolve the configuration that was in force at T two years later
(whitepaper §7.10), which is impossible if configuration is overwritten.
Versions are ``content_hash`` values over the canonical form (D-IMPL-26), so
version identity *is* content identity: re-registering byte-identical content
is idempotent and yields the same version rather than a spurious new one.

**Explicit pinning.** :meth:`ControlPlaneRegistry.resolve` requires a version.
"Latest" is reachable only through the separately named
:meth:`ControlPlaneRegistry.resolve_latest`, so a replay path cannot drift onto
a moving target by omission — resolving "latest" is a decision a caller has to
write down.

**No silent defaults (D-IMPL-38).** An unregistered key or version raises
:class:`ControlPlaneMissing`. There is no fallback value, no ``None`` return,
and no ``default=`` parameter: a missing configuration value is a deployment
error that must surface at the point of use, not a condition the fabric papers
over with a number nobody chose.

**Typed registration.** :meth:`ControlPlaneRegistry.register_typed` validates an
artifact against a declared
:class:`~ccf.controlplane.artifact_base.ArtifactClass`
before it is stored. Untyped :meth:`~ControlPlaneRegistry.register` remains,
because artifact classes whose schema belongs to a deployment rather than to
the SDK must still be registrable — but anything the SDK *has* a contract for
should go through the typed path, where registering the wrong shape under a key
is caught at registration rather than at the decision that reads it.

Every register and resolve — including failed resolutions — emits an
:class:`~ccf.controlplane.audit.AuditEvent`, because the audit plane is only
credible if it records lookups that found nothing (whitepaper §7.8.2: the
Control Plane *is* the audit plane).

This module holds no values: no thresholds, no tables, no key names, no
defaults (CLAUDE.md §11, CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Final, Protocol, TypeAlias, cast, runtime_checkable

from ccf.authz.capability import (
    ActionKind,
    AgentDeclare,
    Authorized,
    Register,
    SkillCatalogRegister,
    SkillGrant,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.audit import AuditAction, AuditEvent, AuditLog
from ccf.controlplane.state import (
    ControlPlaneStateStore,
    InMemoryStateStore,
    verify_any,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "namespaced_key",
    "DERIVED_REGISTER_KINDS",
    "REGISTER_KINDS",
    "AmbiguousPinnedVersionError",
    "AuditEvent",
    "ControlPlaneMissing",
    "ControlPlaneProtocol",
    "ControlPlaneRegistry",
    "CrossTenantKeyRefused",
    "DerivedRegisterAuthority",
    "RegisterAuthority",
    "RefuseEmptyBump",
    "RefuseUnbumpedChange",
    "RegistrationRefusal",
    "ReplayResolver",
]


class RegistrationRefusal(CCFContract):
    """Base of the D-05 registration refusals — values, never exceptions.

    The gate discipline (``GateRefusal``): a refused registration is a normal,
    expected outcome the caller inspects, not a control-flow event. Both
    refusals are audited with ``resolved=False`` (T-05-04), because a version
    history is only trustworthy if the attempts it turned away are on record.

    Attributes:
        key: The Control Plane key involved.
        artifact_version: The author-declared ``artifact_version`` on the
            refused registration.
        detail: Human-readable statement for the operator reading a log; the
            typed fields carry the machine-readable version.
    """

    key: str
    artifact_version: str
    detail: str


class RefuseUnbumpedChange(RegistrationRefusal):
    """D-05: content changed but ``artifact_version`` did not.

    The author is claiming an old version for new bytes — the tampering shape
    T-05-01 exists to catch. Both hashes are carried so the caller can see the
    drift without re-deriving either.
    """

    existing_hash: str
    incoming_hash: str


class RefuseEmptyBump(RegistrationRefusal):
    """D-05: ``artifact_version`` bumped but the content is byte-identical.

    A version that names no change makes every later "what changed in 1.1.0?"
    question unanswerable; the bump is refused rather than recorded as history
    that never happened.
    """

    existing_version: str
    content_hash: str


class ControlPlaneMissing(LookupError):
    """A requested Control Plane key or version is not registered.

    Raised instead of returning a default. See the module docstring
    (D-IMPL-38, no-silent-default).
    """


class CrossTenantKeyRefused(PermissionError):
    """The registration key does not belong to the capability's tenant (D-IMPL-353 §1.3).

    The ONE tenant comparison the design places on the registry, and it is
    inside the handle that holds the capability rather than in a door that
    might forget: the key's tenant segment — the text before the first
    ``/`` of the ``{tenant}/{class}/{name}`` grammar — must equal
    ``authorized.tenant``. A key with no tenant segment fails the same way,
    because a key that names no tenant cannot be shown to be this one's.

    Raised, never returned: after ``verify`` the capability is known genuine
    and for this key, so a disagreement between the key's tenant and the
    capability's is the authorizer's mapping having allowed a cross-tenant
    resource — broken wiring or an attack, not a governance outcome (the I.1
    line). Nothing is appended and nothing is audited here; the gate audited
    the decision.
    """


#: The kinds under which a *door* registers — three doors, three declared
#: actions (§1.2, the registry-union clarification). The handle verifies
#: against whichever the capability was minted for, and the key IS the
#: capability's resource. Policy granularity is preserved: a mapping can
#: grant ``agent.declare`` without ``config.register``.
REGISTER_KINDS: Final[tuple[type[ActionKind], ...]] = (
    Register,
    AgentDeclare,
    SkillCatalogRegister,
)

#: The kinds under which registration is a *derived write* (§1.2): the
#: decision named something else — for ``SkillGrant``, the agent definition —
#: and the artifact registered is a record that decision created. The key is
#: derived from the capability's tenant, the declared class and the
#: artifact's own ``name``; a caller supplies none of it. Admitted by
#: :meth:`ControlPlaneRegistry.register_versioned` alone, the author-versioned
#: path the grant ledger uses.
DERIVED_REGISTER_KINDS: Final[tuple[type[ActionKind], ...]] = (SkillGrant,)

#: The static type of the door registration handles' first parameter.
RegisterAuthority: TypeAlias = (
    Authorized[Register] | Authorized[AgentDeclare] | Authorized[SkillCatalogRegister]
)

#: What ``register_versioned`` accepts: the door kinds, or the derived kind.
DerivedRegisterAuthority: TypeAlias = RegisterAuthority | Authorized[SkillGrant]

#: The separator of the ``{tenant}/{class}/{name}`` Control Plane key grammar.
_KEY_SEPARATOR: Final[str] = "/"


def _tenant_segment(key: str) -> str | None:
    tenant, separator, _ = key.partition(_KEY_SEPARATOR)
    return tenant if separator and tenant else None


def namespaced_key(*, tenant: str, key: str) -> str:
    """Confine a deployment's own key to its tenant — the one derivation (D-IMPL-354).

    The grammar is ``{tenant}/{class}[/{name}]`` and :func:`_tenant_segment`
    reads the tenant as the text before the first separator. A key already
    under ``tenant`` is returned unchanged; every other key — bare (the config
    loader's ``product_class``, a binding document's ``policy``) or prefixed
    by anything else — is placed under ``tenant``. Confinement rather than
    refusal, deliberately: a section label may legitimately contain ``/`` (a
    policy constraint named by a path), so a leading segment is not evidence
    of an author's tenant claim, and a deployment composed through the loader
    can never register outside its own tenant either way (§1.3). The
    registry's own tenant-segment check remains the guard for every direct
    caller.

    Raises:
        ValueError: ``tenant`` or ``key`` is empty, has surrounding
            whitespace, or has an empty segment; ``tenant`` contains ``/``.
    """
    for label, value in (("tenant", tenant), ("key", key)):
        if not value or value != value.strip():
            raise ValueError(f"{label} {value!r} is not a usable Control Plane key part")
    if _KEY_SEPARATOR in tenant:
        raise ValueError(f"tenant {tenant!r} may not contain {_KEY_SEPARATOR!r}")
    if any(not segment for segment in key.split(_KEY_SEPARATOR)):
        raise ValueError(f"key {key!r} has an empty segment")
    prefix = f"{tenant}{_KEY_SEPARATOR}"
    return key if key.startswith(prefix) else prefix + key


def _door_key(authorized: DerivedRegisterAuthority) -> str:
    """The key a door registration acts on: the capability's resource, verified.

    ``verify_any`` runs FIRST — against the resource the capability itself
    carries, so a retargeted resource dies on the mint tuple before it is
    read as a key — then the one tenant comparison (§1.3).
    """
    resource = getattr(authorized, "resource", "")
    verify_any(authorized, kinds=REGISTER_KINDS, resource=resource)
    if _tenant_segment(resource) != authorized.tenant:
        raise CrossTenantKeyRefused(
            f"registration key {resource!r} does not belong to tenant"
            f" {authorized.tenant!r}: the key's tenant segment must equal the"
            " capability's tenant, and a key with no tenant segment belongs to"
            " nobody (D-IMPL-353 §1.3)"
        )
    return resource


def _derived_key(
    authorized: Authorized[SkillGrant], artifact_class: ArtifactClass, validated: object
) -> str:
    """The key a derived registration lands under: ``{authorized.tenant}/{class}/{artifact.name}``.

    The artifact's own ``name`` is the only part not already fixed by the
    capability or the declared class. An artifact that also declares a
    ``tenant`` must agree with the capability's; one that declares no string
    ``name`` cannot be filed as a derived registration at all.
    """
    name = getattr(validated, "name", None)
    if not isinstance(name, str) or not name:
        raise CrossTenantKeyRefused(
            f"an artifact of class {artifact_class.class_id!r} registered as a"
            f" consequence of {authorized.kind.__name__} must carry a string"
            " `name`; without one there is no key to derive and no caller may"
            " supply one (D-IMPL-353 §1.2)"
        )
    claimed = getattr(validated, "tenant", authorized.tenant)
    if claimed != authorized.tenant or _tenant_segment(f"{authorized.tenant}/") is None:
        raise CrossTenantKeyRefused(
            f"the artifact claims tenant {claimed!r} but the capability is for"
            f" {authorized.tenant!r}; a derived registration is filed under the"
            " capability's tenant and nothing else may name one (D-IMPL-353 §1.3)"
        )
    return f"{authorized.tenant}{_KEY_SEPARATOR}{artifact_class.class_id}{_KEY_SEPARATOR}{name}"


class AmbiguousPinnedVersionError(RuntimeError):
    """One declared semver names two different contents under one key (WR-08).

    The ``register_typed`` path carries no D-05 bump check, so two different
    contents can both declare ``semver: "1.1.0"`` under the same key. A
    "pinned" resolution against that declared version would be a moving
    target — exactly the shape D-IMPL-26 forbids — so resolution refuses
    with this typed error instead of silently returning the oldest match.
    Carries the key, the declared version, and every matching content hash.
    """

    def __init__(
        self, key: str, declared_version: str, content_hashes: Sequence[str]
    ) -> None:
        self.key = key
        self.declared_version = declared_version
        self.content_hashes = tuple(content_hashes)
        super().__init__(
            f"declared version {declared_version!r} under key {key!r} matches"
            f" {len(self.content_hashes)} different contents"
            f" ({', '.join(repr(h) for h in self.content_hashes)}); a pinned"
            " resolution must name exactly one content — re-register with a"
            " bumped declared version or pin by content hash"
            " (D-IMPL-26; WR-08)"
        )


@runtime_checkable
class ControlPlaneProtocol(Protocol):
    """The read/write surface a Control Plane must offer.

    Declared as a Protocol so a remote or externally-governed control plane can
    substitute for the in-process registry without any Data Plane component
    knowing (FABR-07 extension point; CLAUDE.md §13). The in-process
    :class:`ControlPlaneRegistry` is the reference implementation, not a
    privileged one — the audit and typed-registration obligations are on the
    surface precisely so a remote plane cannot conform while quietly dropping
    them.

    **:meth:`register_versioned` is on this surface by D-IMPL-82** (Dave,
    2026-08-05, Phase 15.1 planning). The D-05 hash-verified bump check is a
    governance obligation, not an implementation detail of the in-process
    registry: it is what holds an author's ``artifact_version`` claim against
    content identity. The docstring's own argument above decides the question —
    the obligations sit on the surface precisely so a remote plane cannot
    conform while quietly dropping them, and a remote Control Plane that cannot
    run the bump check is exactly such a plane. Consequence accepted on the
    record: this is a public Protocol change and a FABR-07 remote-plane
    implementation obligation — every Control Plane implementation, not only
    this package's, must now supply it. Rejected: a narrow second
    ``VersionedRegistrationProtocol`` required only when a manifest declares
    ``versioned``, which preserves the same posture at the cost of a
    two-Protocol mental model in the phase whose subject is one mental model;
    and narrowing :func:`~ccf.deployment.manifest.load_and_boot` to the concrete
    :class:`ControlPlaneRegistry`, which breaks the Protocol-over-inheritance
    posture CLAUDE.md §11 mandates and forecloses remote control planes for
    manifest boot.
    """

    def register(self, authorized: RegisterAuthority, artifact: object) -> str:
        """Append ``artifact`` under ``authorized.resource``; return its version."""
        ...

    def register_typed(
        self,
        authorized: RegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
    ) -> str:
        """Append ``artifact`` after validating it against ``artifact_class``."""
        ...

    def register_versioned(
        self,
        authorized: DerivedRegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
        *,
        reissuable: bool = False,
    ) -> str | RegistrationRefusal:
        """Register an author-versioned artifact under the D-05 bump check."""
        ...

    def resolve(self, key: str, version: str) -> object:
        """Return the exact artifact registered as ``(key, version)``."""
        ...

    def resolve_latest(self, key: str) -> tuple[str, object]:
        """Return the most recently registered ``(version, artifact)``."""
        ...

    def audit_events(self) -> tuple[AuditEvent, ...]:
        """Return the append-only audit log, oldest first."""
        ...

    @property
    def audit_log(self) -> AuditLog:
        """The append-only log this plane records into — the composition root's audit surface (D-IMPL-354).

        On the Protocol, not only on the in-process registry, because a
        composition root records its own decision to mint on THIS log
        (``action="composition"``) before it mints, and takes the event's
        content address as the capability's ``decision_id``: a plane that
        offered no appendable log could not host a composition at all. The
        obligation sits on the surface for the reason :meth:`register_versioned`
        does — so a remote plane cannot conform while quietly dropping it.
        Holding the reference confers no rewrite capability; the log is
        append-only.
        """
        ...


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ControlPlaneRegistry:
    """In-process, append-only, versioned configuration registry.

    DESIGN.md §7; whitepaper §7.8. See the module docstring for the three
    properties this type exists to guarantee.

    Args:
        clock: Time source for audit timestamps. Injected so tests and replay
            harnesses control it; the default reads the wall clock in UTC.
            (A clock is mechanism, not a domain value — but a *hidden* clock
            would make the audit log untestable, so it is a seam.)
        audit_log: The append-only log this registry records into. Injected
            so composition sites can share ONE log — one sequence, one clock
            — between the registry and every other Control Plane service
            that audits (the grant ledger foremost): the Control Plane is
            the audit plane, singular (whitepaper §7.8.2; WR-07). The
            default constructs a fresh log, preserving existing behavior
            for callers that do not inject.
        state_store: Where mutable-until-terminal state records live
            (D-IMPL-27's mutability split; D-IMPL-18's "Control Plane's
            storage seam"). Injected so a deployment can make that state
            durable without any consumer knowing. The default constructs an
            :class:`~ccf.controlplane.state.InMemoryStateStore`, matching the
            in-process posture of the registry itself (CLAUDE.md §13).
            Registered *artifacts* never route here — they are immutable and
            versioned, and stay on the append-only path above.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        audit_log: AuditLog | None = None,
        state_store: ControlPlaneStateStore | None = None,
    ) -> None:
        self._clock: Callable[[], datetime] = clock or _utc_now
        self._versions: dict[str, list[str]] = {}
        self._artifacts: dict[tuple[str, str], object] = {}
        self._classes: dict[str, str] = {}
        self._bumps: dict[str, dict[str, tuple[str, str]]] = {}
        self._audit = audit_log if audit_log is not None else AuditLog()
        self._state_store: ControlPlaneStateStore = (
            state_store if state_store is not None else InMemoryStateStore()
        )

    @property
    def state_store(self) -> ControlPlaneStateStore:
        """The mutable-state seam this Control Plane offers (D-IMPL-18/27).

        Exposed for the same reason as :attr:`audit_log`: state that belongs
        to the Control Plane must be reachable from the Control Plane, so
        every service over one registry reads one state, rather than each
        caching its own and disagreeing (WR-05). Holding the reference
        confers no capability the Protocol does not.
        """
        return self._state_store

    @property
    def audit_log(self) -> AuditLog:
        """The append-only log this registry records into (§7.8.2; WR-07).

        Exposed so composition sites can hand the SAME instance to other
        auditing Control Plane services (e.g.
        :class:`~ccf.skills.grants.GrantLedger`), keeping registration and
        grant-lifecycle events in one monotonic sequence. The log itself is
        append-only; holding the reference confers no rewrite capability.
        """
        return self._audit

    def _record(
        self,
        *,
        action: AuditAction,
        key: str,
        version: str,
        resolved: bool,
        actor: str | None = None,
        artifact_class: str | None = None,
    ) -> None:
        self._audit.append(
            action=action,
            key=key,
            version=version,
            resolved=resolved,
            occurred_at=self._clock(),
            actor=actor,
            artifact_class=artifact_class or self._classes.get(key),
        )

    def register(self, authorized: RegisterAuthority, artifact: object) -> str:
        """Append ``artifact`` under ``authorized.resource`` and return its content version.

        **The key is the capability's resource** (D-IMPL-353 §1.2): the
        authorizer decided *this principal may register this key for this
        tenant*, and the handle acts on exactly that, taking the key, the
        tenant and the audit actor from the capability. There is no key
        parameter and no actor parameter — no second source for any of them.
        The capability is verified before anything is touched; the key's
        tenant segment is compared to the capability's tenant once, here
        (§1.3).

        The artifact must be canonically serializable; anything that is not
        (a float, a naive datetime, an unsupported type) is refused at the
        boundary rather than stored in a form replay could not reproduce.

        Registering byte-identical content again is idempotent: the existing
        version is returned and no duplicate is appended.

        Raises:
            ccf.authz.capability.CapabilityBypassError: ``authorized`` is
                fabricated, retargeted, or not one of :data:`REGISTER_KINDS`.
            CrossTenantKeyRefused: the key's tenant segment is not the
                capability's tenant.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
        """
        key = _door_key(authorized)
        actor = authorized.principal
        version = content_hash(artifact)
        versions = self._versions.setdefault(key, [])
        if version not in versions:
            versions.append(version)
            self._artifacts[(key, version)] = artifact
        self._record(
            action="register", key=key, version=version, resolved=True, actor=actor
        )
        return version

    def register_typed(
        self,
        authorized: RegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
    ) -> str:
        """Validate ``artifact`` against ``artifact_class``, then register it under ``authorized.resource``.

        The key, the tenant and the audit actor come from the capability and
        from nowhere else (D-IMPL-353 §1.2; see :meth:`register`).

        The typed path exists because a key is only a string: a mapping stored
        under a λ_c key is indistinguishable from a λ_c table until something
        decides against it. Validating at registration moves that failure to
        the moment a human made the mistake.

        A key is bound to one artifact class for the life of the registry. A
        later registration under a *different* class is refused rather than
        silently accepted — a key whose class changes mid-history cannot be
        resolved coherently at replay time, because the resolver would not know
        which contract to read the older versions under.

        Raises:
            ccf.authz.capability.CapabilityBypassError: ``authorized`` is
                fabricated, retargeted, or not one of :data:`REGISTER_KINDS`.
            CrossTenantKeyRefused: the key's tenant segment is not the
                capability's tenant.
            TypeError: the artifact does not satisfy the class contract, or the
                key is already bound to a different artifact class.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
        """
        key = _door_key(authorized)
        actor = authorized.principal
        bound = self._classes.get(key)
        if bound is not None and bound != artifact_class.class_id:
            raise TypeError(
                f"key {key!r} is already bound to artifact class {bound!r};"
                f" refusing to rebind it to {artifact_class.class_id!r}"
            )
        artifact_class.validate(artifact)
        version = content_hash(artifact)
        versions = self._versions.setdefault(key, [])
        if version not in versions:
            versions.append(version)
            self._artifacts[(key, version)] = artifact
        self._classes[key] = artifact_class.class_id
        self._record(
            action="register_typed",
            key=key,
            version=version,
            resolved=True,
            actor=actor,
            artifact_class=artifact_class.class_id,
        )
        return version

    def register_versioned(
        self,
        authorized: DerivedRegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
        *,
        reissuable: bool = False,
    ) -> str | RegistrationRefusal:
        """Register an author-versioned artifact under the D-05 bump check.

        **Two shapes of key, decided by the capability's kind, neither
        caller-supplied** (D-IMPL-353 §1.2):

        * under a door kind (:data:`REGISTER_KINDS`) the key IS
          ``authorized.resource``, exactly as :meth:`register`;
        * under the derived kind (:data:`DERIVED_REGISTER_KINDS`) — the grant
          ledger registering the grant artifact its ``skill.grant`` decision
          created — the key is derived from ``authorized.tenant``, the
          declared class and the validated artifact's own ``name``.

        Either way the tenant is the capability's and the audit actor is
        ``authorized.principal``.

        The path for artifacts carrying D-IMPL-28 two-field versioning (agent
        definitions, prompt artifacts, …). On top of :meth:`register_typed`'s
        validation and class binding, the author's ``artifact_version`` claim
        is held against content identity — the four-outcome table:

        * same content, same ``artifact_version`` — idempotent no-op; the
          existing content version is returned.
        * changed content, same ``artifact_version`` — returns
          :class:`RefuseUnbumpedChange`; nothing is stored.
        * same content, bumped ``artifact_version`` — returns
          :class:`RefuseEmptyBump`; nothing is stored.
        * changed content, bumped ``artifact_version`` — appended; the new
          content version is returned.

        Refusals are returned values, not exceptions, and every outcome —
        refusals included — is audited (``resolved=False`` on refusal).
        :meth:`register_typed` itself is untouched: artifact classes without
        author versioning keep their existing behavior byte for byte.

        The empty-bump outcome reads a re-registration as a *revision* of an
        evolving document, which is the wrong reading for a single-use
        *request* artifact — one whose whole purpose is to be submitted,
        decided, and (if declined) submitted again unchanged. ``reissuable``
        is how a caller declares that reading at the call site: with it set,
        a version bump over byte-identical content is admitted as a new
        request rather than refused. The unbumped-change refusal is
        unaffected either way — content still never changes under a version
        already claimed. The flag is a call-site statement, deliberately, so
        the registry holds no list of which artifact classes behave which
        way (CLAUDE.md §11: mechanism, not values).

        Args:
            authorized: The capability for the registration — a door kind, or
                the derived ``SkillGrant``.
            artifact: The artifact to validate and register.
            artifact_class: The class the artifact must satisfy.
            reissuable: Admit a bump over byte-identical content as a new
                request instead of refusing it as an empty bump.

        Raises:
            ccf.authz.capability.CapabilityBypassError: ``authorized`` is
                fabricated, retargeted, or of a kind this handle does not
                admit.
            CrossTenantKeyRefused: the key (given or derived) is not the
                capability's tenant's, or a derived artifact cannot name
                itself.
            TypeError: the artifact fails the class contract, the key is bound
                to a different class, or the artifact declares no string
                ``artifact_version``.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
        """
        # The derived shape is checked for FIRST only in the sense of kind
        # selection; verification itself is one call either way, and it runs
        # before the artifact is validated or any key exists.
        current = getattr(authorized, "kind", None)
        if any(current is kind for kind in DERIVED_REGISTER_KINDS):
            derived_kind = verify_any(
                authorized,
                kinds=DERIVED_REGISTER_KINDS,
                resource=getattr(authorized, "resource", ""),
            )
            assert derived_kind is SkillGrant  # the only member, proven by verify_any
            derived = cast(Authorized[SkillGrant], authorized)
            validated = artifact_class.validate(artifact)
            key = _derived_key(derived, artifact_class, validated)
        else:
            key = _door_key(authorized)
            validated = artifact_class.validate(artifact)
        actor = authorized.principal
        bound_class = self._classes.get(key)
        if bound_class is not None and bound_class != artifact_class.class_id:
            raise TypeError(
                f"key {key!r} is already bound to artifact class {bound_class!r};"
                f" refusing to rebind it to {artifact_class.class_id!r}"
            )
        declared = getattr(validated, "artifact_version", None)
        if not isinstance(declared, str):
            raise TypeError(
                f"artifact for class {artifact_class.class_id!r} declares no"
                " string artifact_version; the hash-verified bump check (D-05)"
                " has nothing to verify"
            )
        incoming = content_hash(validated)
        # The D-05 comparison asks whether the artifact's *content* changed,
        # and the content of an author-versioned artifact is everything except
        # the version claim itself — a bump alone must not read as a content
        # change, or the empty-bump outcome could never fire. The fingerprint
        # normalizes artifact_version before hashing; the stored registry
        # version stays the full content hash (D-IMPL-26 identity).
        fingerprint = content_hash(
            validated.model_copy(update={"artifact_version": ""})
        )
        bumps = self._bumps.setdefault(key, {})

        def _refused(refusal: RegistrationRefusal) -> RegistrationRefusal:
            self._record(
                action="register_versioned",
                key=key,
                version=incoming,
                resolved=False,
                actor=actor,
                artifact_class=artifact_class.class_id,
            )
            return refusal

        existing = bumps.get(declared)
        if existing is not None and existing[0] != incoming:
            return _refused(
                RefuseUnbumpedChange(
                    key=key,
                    artifact_version=declared,
                    existing_hash=existing[0],
                    incoming_hash=incoming,
                    detail=(
                        f"content under ({key!r}, artifact_version {declared!r})"
                        " changed without a version bump (D-05)"
                    ),
                )
            )
        if existing is None and not reissuable:
            for prior_version, (_prior_hash, prior_print) in bumps.items():
                if prior_print == fingerprint:
                    return _refused(
                        RefuseEmptyBump(
                            key=key,
                            artifact_version=declared,
                            existing_version=prior_version,
                            content_hash=fingerprint,
                            detail=(
                                f"artifact_version bumped to {declared!r} under"
                                f" {key!r} but the content is byte-identical to"
                                f" version {prior_version!r} (D-05)"
                            ),
                        )
                    )
        versions = self._versions.setdefault(key, [])
        if incoming not in versions:
            versions.append(incoming)
            self._artifacts[(key, incoming)] = validated
        self._classes[key] = artifact_class.class_id
        bumps[declared] = (incoming, fingerprint)
        self._record(
            action="register_versioned",
            key=key,
            version=incoming,
            resolved=True,
            actor=actor,
            artifact_class=artifact_class.class_id,
        )
        return incoming

    def artifact_class_of(self, key: str) -> str | None:
        """Return the artifact class bound to ``key``, if it was typed.

        Introspection only — not audited, because it resolves nothing.
        """
        return self._classes.get(key)

    def keys_of_class(self, class_id: str) -> tuple[str, ...]:
        """Every key bound to ``class_id``, in first-registration order.

        Introspection only — not audited, because it resolves nothing. The
        surface catalog discovery derives membership from (IN-03): registry
        state is the single store; no consumer keeps a volatile second index.
        """
        return tuple(
            key for key, bound in self._classes.items() if bound == class_id
        )

    def peek(self, key: str, version: str) -> object:
        """Return the artifact at ``(key, version)`` without auditing.

        Introspection only — deliberately unaudited, unlike :meth:`resolve`:
        declared-version matching has to *examine* every registered content
        under a key to find the one whose declared semver matches, and
        auditing those probes as resolutions would record reads that never
        happened (WR-08 side effect). Callers audit the resolution they
        actually return by calling :meth:`resolve` on the match.

        Raises:
            ControlPlaneMissing: no such key, or no such version under it.
        """
        try:
            return self._artifacts[(key, version)]
        except KeyError:
            raise ControlPlaneMissing(
                f"no Control Plane artifact registered as ({key!r}, {version!r})"
            ) from None

    def resolve(self, key: str, version: str) -> object:
        """Return the exact artifact registered as ``(key, version)``.

        Raises:
            ControlPlaneMissing: no such key, or no such version under it.
        """
        try:
            artifact = self._artifacts[(key, version)]
        except KeyError:
            self._record(
                action="resolve", key=key, version=version, resolved=False
            )
            raise ControlPlaneMissing(
                f"no Control Plane artifact registered as ({key!r}, {version!r})"
            ) from None
        self._record(action="resolve", key=key, version=version, resolved=True)
        return artifact

    def resolve_latest(self, key: str) -> tuple[str, object]:
        """Return the most recently registered ``(version, artifact)``.

        Deliberately separate from :meth:`resolve`: reaching for "latest" is a
        choice a caller states, never one it inherits by leaving an argument
        off. Replay paths must not use this method.

        Raises:
            ControlPlaneMissing: nothing has been registered under ``key``.
        """
        versions = self._versions.get(key)
        if not versions:
            self._record(action="resolve_latest", key=key, version="", resolved=False)
            raise ControlPlaneMissing(
                f"no Control Plane versions registered under {key!r}"
            )
        version = versions[-1]
        self._record(
            action="resolve_latest", key=key, version=version, resolved=True
        )
        return version, self._artifacts[(key, version)]

    def versions(self, key: str) -> tuple[str, ...]:
        """Return every version registered under ``key``, oldest first.

        Introspection only — not audited, because it resolves nothing.
        """
        return tuple(self._versions.get(key, ()))

    def audit_events(self) -> tuple[AuditEvent, ...]:
        """Return the append-only audit log, oldest first (INV-CH7-71)."""
        return self._audit.events()


class ReplayResolver:
    """A Control Plane view that can only resolve exact versions.

    Replay reproduces a decision against the configuration in force when it was
    made (whitepaper §7.10), so the replay path must never reach a "latest"
    lookup. :meth:`ControlPlaneRegistry.resolve_latest` is separately named to
    make that reach visible — this wrapper goes further and makes it
    *unreachable*: the method is not on the object, so a replay path cannot
    drift onto a moving target even by mistake.

    Wraps any :class:`ControlPlaneProtocol`, including a remote one, so the
    guarantee survives substituting the plane (D-IMPL-26).
    """

    def __init__(self, control_plane: ControlPlaneProtocol) -> None:
        self._control_plane = control_plane

    def resolve(self, key: str, version: str) -> object:
        """Return the exact artifact registered as ``(key, version)``.

        Raises:
            ControlPlaneMissing: no such key, or no such version under it.
        """
        return self._control_plane.resolve(key, version)
