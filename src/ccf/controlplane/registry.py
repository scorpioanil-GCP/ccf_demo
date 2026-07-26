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
artifact against a declared :class:`~ccf.controlplane.artifacts.ArtifactClass`
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

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import ArtifactClass
from ccf.controlplane.audit import AuditAction, AuditEvent, AuditLog

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuditEvent",
    "ControlPlaneMissing",
    "ControlPlaneProtocol",
    "ControlPlaneRegistry",
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
    """

    def register(self, key: str, artifact: object) -> str:
        """Append ``artifact`` under ``key``; return its version."""
        ...

    def register_typed(
        self, key: str, artifact: object, artifact_class: ArtifactClass
    ) -> str:
        """Append ``artifact`` after validating it against ``artifact_class``."""
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
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._clock: Callable[[], datetime] = clock or _utc_now
        self._versions: dict[str, list[str]] = {}
        self._artifacts: dict[tuple[str, str], object] = {}
        self._classes: dict[str, str] = {}
        self._bumps: dict[str, dict[str, tuple[str, str]]] = {}
        self._audit = audit_log if audit_log is not None else AuditLog()

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

    def register(self, key: str, artifact: object, *, actor: str | None = None) -> str:
        """Append ``artifact`` under ``key`` and return its content version.

        The artifact must be canonically serializable; anything that is not
        (a float, a naive datetime, an unsupported type) is refused at the
        boundary rather than stored in a form replay could not reproduce.

        Registering byte-identical content again is idempotent: the existing
        version is returned and no duplicate is appended.

        Raises:
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
        """
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
        key: str,
        artifact: object,
        artifact_class: ArtifactClass,
        *,
        actor: str | None = None,
    ) -> str:
        """Validate ``artifact`` against ``artifact_class``, then register it.

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
            TypeError: the artifact does not satisfy the class contract, or the
                key is already bound to a different artifact class.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
        """
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
        key: str,
        artifact: object,
        artifact_class: ArtifactClass,
        *,
        actor: str | None = None,
    ) -> str | RegistrationRefusal:
        """Register an author-versioned artifact under the D-05 bump check.

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

        Raises:
            TypeError: the artifact fails the class contract, the key is bound
                to a different class, or the artifact declares no string
                ``artifact_version``.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
        """
        bound_class = self._classes.get(key)
        if bound_class is not None and bound_class != artifact_class.class_id:
            raise TypeError(
                f"key {key!r} is already bound to artifact class {bound_class!r};"
                f" refusing to rebind it to {artifact_class.class_id!r}"
            )
        validated = artifact_class.validate(artifact)
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
        if existing is None:
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
