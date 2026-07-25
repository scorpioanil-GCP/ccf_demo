"""Minimal versioned Control Plane registry (SDK-defined mechanism).

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

Every register and resolve — including failed resolutions — emits an
:class:`AuditEvent`, because the audit plane is only credible if it records
lookups that found nothing.

This module holds no values: no thresholds, no tables, no key names, no
defaults (CLAUDE.md §11, CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuditEvent",
    "ControlPlaneMissing",
    "ControlPlaneProtocol",
    "ControlPlaneRegistry",
]

AuditAction = Literal["register", "resolve", "resolve_latest"]


class ControlPlaneMissing(LookupError):
    """A requested Control Plane key or version is not registered.

    Raised instead of returning a default. See the module docstring
    (D-IMPL-38, no-silent-default).
    """


class AuditEvent(CCFContract):
    """One audit-plane record of a Control Plane interaction (INV-CH7-71).

    Attributes:
        sequence: Monotonic position in this registry's audit log.
        action: Which interaction occurred.
        key: The configuration key involved.
        version: The version involved, or the version requested when the
            resolution failed.
        resolved: Whether the interaction succeeded. Failed resolutions are
            recorded too — an audit plane that only logs successes cannot
            answer "what did the deployment ask for and not have?"
        occurred_at: Timestamp from the injected clock.
    """

    sequence: int
    action: AuditAction
    key: str
    version: str
    resolved: bool
    occurred_at: datetime


@runtime_checkable
class ControlPlaneProtocol(Protocol):
    """The read/write surface a Control Plane must offer.

    Declared as a Protocol so a remote or externally-governed control plane can
    substitute for the in-process registry without any Data Plane component
    knowing (FABR-07 extension point; CLAUDE.md §13).
    """

    def register(self, key: str, artifact: object) -> str:
        """Append ``artifact`` under ``key``; return its version."""
        ...

    def resolve(self, key: str, version: str) -> object:
        """Return the exact artifact registered as ``(key, version)``."""
        ...

    def resolve_latest(self, key: str) -> tuple[str, object]:
        """Return the most recently registered ``(version, artifact)``."""
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
    """

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock: Callable[[], datetime] = clock or _utc_now
        self._versions: dict[str, list[str]] = {}
        self._artifacts: dict[tuple[str, str], object] = {}
        self._audit: list[AuditEvent] = []

    def _record(
        self,
        *,
        action: AuditAction,
        key: str,
        version: str,
        resolved: bool,
    ) -> None:
        self._audit.append(
            AuditEvent(
                sequence=len(self._audit),
                action=action,
                key=key,
                version=version,
                resolved=resolved,
                occurred_at=self._clock(),
            )
        )

    def register(self, key: str, artifact: object) -> str:
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
        self._record(action="register", key=key, version=version, resolved=True)
        return version

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
        return tuple(self._audit)
