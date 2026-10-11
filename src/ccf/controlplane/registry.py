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

import hashlib
import json
from dataclasses import dataclass
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Final, Protocol, TypeAlias, cast, runtime_checkable

from pydantic import BaseModel

from ccf.authz.capability import (
    CompositionRegister,
    InvalidationRecordRegister,
    ActionKind,
    AgentDeclare,
    CapabilityBypassError,
    Authorized,
    Register,
    SkillCatalogRegister,
    SkillGrant,
    verify,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
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
    "ArtifactIsolationRefused",
    "AuditEvent",
    "ControlPlaneMissing",
    "ControlPlaneProtocol",
    "ControlPlaneRegistry",
    "CrossTenantKeyRefused",
    "DerivedRegisterAuthority",
    "INVALIDATION_RECORD_CLASS_ID",
    "INVALIDATION_RECORD_PREFIX",
    "TypedRegisterAuthority",
    "invalidation_record_key",
    "RegisterAuthority",
    "RefuseEmptyBump",
    "RefuseUnbumpedChange",
    "RegistrationRefusal",
    "RegistryIntegrityFailure",
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
    CompositionRegister,
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
    Authorized[Register]
    | Authorized[CompositionRegister]
    | Authorized[AgentDeclare]
    | Authorized[SkillCatalogRegister]
)

#: What ``register_versioned`` accepts: the door kinds, or the derived kind.
DerivedRegisterAuthority: TypeAlias = RegisterAuthority | Authorized[SkillGrant]

#: What ``register_typed`` accepts: the door kinds, or the invalidation-record kind (``D-IMPL-382``).
TypedRegisterAuthority: TypeAlias = RegisterAuthority | Authorized[InvalidationRecordRegister]

#: The class segment under which a tenant's entity-invalidation records live:
#: ``{tenant}/ccf.entity-invalidation/{sha256(entity_uri)}`` (``D-IMPL-382`` option A). Mechanism,
#: not a domain value: it is the one prefix the invalidation-record capability may write under.
INVALIDATION_RECORD_PREFIX: Final[str] = "ccf.entity-invalidation"

#: The one artifact class the invalidation-record capability may register (``D-IMPL-382``):
#: *"It must not authorize another tenant, another artifact class, or general registry writes."*
INVALIDATION_RECORD_CLASS_ID: Final[str] = "ccf.entity-invalidation-record"

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
    _refuse_the_invalidation_range(resource)
    return resource


def _refuse_the_invalidation_range(key: str) -> None:
    """No door, composition or derived write may land in a tenant's invalidation range (``D-IMPL-382``).

    ``{tenant}/ccf.entity-invalidation`` and everything under it belong to
    :class:`~ccf.authz.capability.InvalidationRecordRegister` alone, which derives its keys
    itself. The focused review of ``b66ab4fa`` reproduced what an open range allows: a door
    capability minted for an exact record key planted an earlier boundary and a refused product
    served; other content there made every serve touching that entity raise and blocked the sink.
    """
    _, separator, rest = key.partition(_KEY_SEPARATOR)
    class_segment = rest.split(_KEY_SEPARATOR, 1)[0] if separator else ""
    if class_segment == INVALIDATION_RECORD_PREFIX:
        raise CapabilityBypassError(
            f"{key!r} is in the entity-invalidation range, which only the invalidation-record"
            " capability may write, under keys it derives itself (D-IMPL-382)"
        )


def invalidation_record_key(*, tenant_id: str, entity_uri: str) -> str:
    """The key of one tenant's invalidation record for one entity (``D-IMPL-382`` option A).

    ``{tenant}/ccf.entity-invalidation/{sha256(entity_uri)}``: the entity URI is hashed so any URI
    is a usable key segment and no URI can introduce a separator.
    """
    digest = hashlib.sha256(entity_uri.encode("utf-8")).hexdigest()
    return f"{tenant_id}{_KEY_SEPARATOR}{INVALIDATION_RECORD_PREFIX}{_KEY_SEPARATOR}{digest}"


def _invalidation_record_key(
    authorized: Authorized[InvalidationRecordRegister], artifact_class: ArtifactClass, validated: object
) -> str:
    """The key an invalidation record lands under, derived — never named by a caller (``D-IMPL-382``).

    In order, each refusal a ``CapabilityBypassError`` or ``CrossTenantKeyRefused``: the
    capability is genuine and unretargeted for exactly this kind on its minted resource; that
    resource is exactly the capability's own tenant's invalidation prefix; the class is the
    entity-invalidation record class and nothing else; the record names the capability's tenant
    and a non-empty entity. Dave, 2026-10-11 07:32: *"The authorization amendment covers only
    entity-invalidation records belonging to the capability's tenant. It must not authorize
    another tenant, another artifact class, or general registry writes."*
    """
    verify(authorized, kind=InvalidationRecordRegister, resource=getattr(authorized, "resource", ""))
    if _KEY_SEPARATOR in authorized.tenant or not authorized.tenant:
        raise CrossTenantKeyRefused(
            f"tenant {authorized.tenant!r} is not a usable key segment: a tenant id containing"
            f" {_KEY_SEPARATOR!r} would file records under another tenant's segment (D-IMPL-353 §1.3;"
            " D-IMPL-382)"
        )
    expected_prefix = f"{authorized.tenant}{_KEY_SEPARATOR}{INVALIDATION_RECORD_PREFIX}"
    if authorized.resource != expected_prefix:
        raise CrossTenantKeyRefused(
            f"an invalidation-record capability for tenant {authorized.tenant!r} must be minted for"
            f" {expected_prefix!r}, not {authorized.resource!r}; it writes its own tenant's"
            " invalidation records and nothing else (D-IMPL-382)"
        )
    # The class OBJECT, not its id: an ArtifactClass carrying the record's id over another contract,
    # or over a subclass of the record, is another artifact class (review of b66ab4fa).
    from ccf.controlplane.invalidation import ENTITY_INVALIDATION_RECORD, EntityInvalidationRecord

    if artifact_class is not ENTITY_INVALIDATION_RECORD or type(validated) is not EntityInvalidationRecord:
        raise CapabilityBypassError(
            f"an invalidation-record capability registers {INVALIDATION_RECORD_CLASS_ID!r} only,"
            f" not {artifact_class.class_id!r} with contract {type(validated).__name__}; it"
            " authorizes no other artifact class (D-IMPL-382)"
        )
    tenant_id = getattr(validated, "tenant_id", None)
    entity_uri = getattr(validated, "entity_uri", None)
    if tenant_id != authorized.tenant:
        raise CrossTenantKeyRefused(
            f"the invalidation record names tenant {tenant_id!r} but the capability is for"
            f" {authorized.tenant!r}; a record is filed under the capability's tenant only (D-IMPL-382)"
        )
    if not isinstance(entity_uri, str) or not entity_uri:
        raise CrossTenantKeyRefused(
            "an invalidation record must name its entity; without one there is no key to derive"
            " and no caller may supply one (D-IMPL-382)"
        )
    return invalidation_record_key(tenant_id=authorized.tenant, entity_uri=entity_uri)


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
    key = f"{authorized.tenant}{_KEY_SEPARATOR}{artifact_class.class_id}{_KEY_SEPARATOR}{name}"
    _refuse_the_invalidation_range(key)
    return key


class ArtifactIsolationRefused(TypeError):
    """An artifact the registry could not reconstruct independently — refused, never shared (``D-IMPL-380``, sixth round).

    The registry holds and serves *reconstructions*, never a registrant's
    object and never a reader's (Dave, 2026-10-10 15:50 MST, under Grok's
    reviewed amendment: *"Use canonical serialization and reconstruction for
    both copy-in and copy-out. Shallow copies are not accepted."*). When the
    reconstruction of an artifact would not preserve its type, its canonical
    bytes or its value, the door refuses with this error rather than falling
    back (*"Do not fall back to the original object or a shallow copy."*). On a
    write door nothing has changed when it is raised — no version, no class
    binding, no bump entry, no audit row. On a read door nothing is returned,
    and the artifact is not reported missing: this is a ``TypeError``, never
    the ``LookupError`` that :class:`ControlPlaneMissing` is; ``resolve`` and
    ``resolve_latest`` record the refused read as a resolve that did not
    resolve, so the audit plane sees it.

    Attributes:
        artifact_type: the Python type name of the artifact that was refused.
        door: the registry door that refused — ``register``,
            ``register_typed``, ``register_versioned``, ``peek`` or ``resolve``.
        reason: the guarantee the reconstruction failed to preserve.
    """

    def __init__(self, *, artifact_type: str, door: str, reason: str) -> None:
        self.artifact_type = artifact_type
        self.door = door
        self.reason = reason
        super().__init__(
            f"{door}: the registry could not reconstruct a {artifact_type}"
            f" independently — {reason}"
        )


class RegistryIntegrityFailure(RuntimeError):
    """A registered ``(key, version)`` whose record is missing a half or whose bytes do not hash to its version.

    ``D-IMPL-380``, 2026-10-11 00:15 (Dave): *"An existing artifact with missing
    or inconsistent byte storage is an integrity failure, not 'artifact
    missing.' Failed writes must publish neither half."* The registry stores
    one record per ``(key, version)`` — the verified reconstruction and the
    canonical bytes it was rebuilt from — written by one assignment after every
    write-door check has passed. A read that finds the record without its
    bytes, or with bytes that do not hash to the version it sits under, has
    found corruption, and says so by this name: a ``RuntimeError``, never the
    ``LookupError`` that :class:`ControlPlaneMissing` is, which is raised only
    when nothing was ever registered under the key and version. ``resolve`` and
    ``resolve_latest`` record the read as a resolve that did not resolve.

    Attributes:
        key: the Control Plane key.
        version: the content version the record sits under.
        door: the read door that found the failure.
        reason: which half is missing or inconsistent.
    """

    def __init__(self, *, key: str, version: str, door: str, reason: str) -> None:
        self.key = key
        self.version = version
        self.door = door
        self.reason = reason
        super().__init__(
            f"{door}: the registry's record for ({key!r}, {version!r}) failed"
            f" its integrity check — {reason}"
        )


@dataclass(frozen=True, slots=True)
class _Held:
    """What the registry holds under one ``(key, version)``: both halves, one record.

    ``artifact`` is the write door's verified reconstruction — never served to
    a reader, only compared against what a read parses. ``rendered`` is the
    canonical bytes that reconstruction was rebuilt from and verified to render
    back to; the version is their hash, and every read parses them afresh.
    """

    artifact: object
    rendered: bytes


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

    **Class identity is on this surface by ``D-IMPL-378`` K2** (Dave,
    2026-10-08): both typed registration methods validate with
    ``artifact_class.validate(artifact)``, so a document stating one class is
    never filed as another, whichever plane registers it. The conformance check
    for an implementation is
    ``tests/conformance/test_control_plane_class_identity.py``.
    """

    def register(self, authorized: RegisterAuthority, artifact: object) -> str:
        """Append ``artifact`` under ``authorized.resource``; return its version."""
        ...

    def register_typed(
        self,
        authorized: TypedRegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
    ) -> str:
        """Append ``artifact`` after validating it against ``artifact_class``.

        **Validating means** ``artifact_class.validate(artifact)``, called
        before anything is stored or audited (``D-IMPL-378`` K2). Among what it
        refuses is an artifact whose own top-level ``class_id`` disagrees with
        the class it is registered as, raised as
        :class:`~ccf.controlplane.artifact_base.ArtifactClassIdMismatch`, as
        :meth:`ControlPlaneRegistry.register_typed` raises it. An implementation
        that checks only the contract's type files a document stating one class
        under another. An implementation proves it with
        ``tests/conformance/test_control_plane_class_identity.py``, its factory
        added to that module's ``PLANES``.
        """
        ...

    def register_versioned(
        self,
        authorized: DerivedRegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
        *,
        reissuable: bool = False,
    ) -> str | RegistrationRefusal:
        """Register an author-versioned artifact under the D-05 bump check.

        The artifact is validated with ``artifact_class.validate(artifact)``
        before the bump check runs and before anything is stored or audited
        (``D-IMPL-378`` K2), so an artifact whose own top-level ``class_id``
        disagrees with the class it is registered as is refused, raised as
        :class:`~ccf.controlplane.artifact_base.ArtifactClassIdMismatch`, as
        :meth:`ControlPlaneRegistry.register_versioned` raises it. An
        implementation proves it with
        ``tests/conformance/test_control_plane_class_identity.py``, its factory
        added to that module's ``PLANES``.
        """
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


def _reconstructed(
    artifact: object, *, door: str, rendered: bytes | None = None
) -> _Held:
    """The write side: an independent reconstruction of ``artifact`` AND the bytes it was rebuilt from, verified, or a refusal.

    ``D-IMPL-380``, sixth round, as corrected on 2026-10-11 (Dave, 00:15 and
    00:28): the artifact is rendered **once** here (or the caller passes the
    render it already took), the version is the hash of those bytes, and the
    bytes are kept beside the reconstruction in one :class:`_Held` so the read
    doors can parse them instead of rendering again. Every sixth-round
    guarantee is checked exactly as before.

    **Why a reconstruction and not a copy.** The fifth round handed the
    approval sink ``grant.model_copy(deep=True)``; the copy's content was the
    live object's registry address and ``peek`` handed the live object back.
    Then ``copy.deepcopy`` at these doors was measured: 377 failures at
    ``ef84f801``, every one ``TypeError: cannot pickle 'mappingproxy' object``,
    because :mod:`ccf.workflow.definitions` wraps ``gate_routes`` in nested
    ``MappingProxyType`` precisely so the hash does not move — the field was
    made tamper-proof by being made uncopyable. A reconstruction from the
    artifact's own canonical form has no such limit: the model's validators
    rebuild the proxies, and every nested value is new.

    **What is preserved, and checked.** The artifact's canonical bytes are
    rendered once (``canonical_bytes``), parsed, and rebuilt — through
    ``model_validate`` on the artifact's own type for a model, or as the parsed
    document for a plain mapping (``register`` accepts one). The result is then
    held to three guarantees, each refused by name: the **type** is the
    artifact's own (a typed artifact is never silently a plain dictionary);
    the **canonical bytes** are unchanged, which is the content hash that is
    its version; and the result is **equal** to the artifact. The third check
    is not redundant with the second: a plain mapping holding a ``Decimal``
    renders as a string, so its bytes agree with the rebuilt string while its
    value does not. A hash-transparent field survives because of what the mark
    means (``D-IMPL-243``, *"silence equals yesterday"*): it is omitted from the
    rendering only when it equals its sentinel, and the sentinel is what the
    field's own default restores.

    **Cost, measured at this commit** on the covenant-review workflow
    definition: about 30 µs for the rebuild plus the verifying render, against
    the 12.8 µs the write doors already spend hashing. The read doors pay it on
    every call; shallow copies were ruled out (*"Shallow copies are not
    accepted."*).

    Raises:
        ArtifactIsolationRefused: the reconstruction raised, or failed one of
            the three guarantees. Nothing is returned and nothing falls back.
        ccf.contracts.canonical.CanonicalizationError: the artifact has no
            canonical form — the refusal every write door already documents.
    """
    rendered = canonical_bytes(artifact) if rendered is None else rendered
    artifact_type = type(artifact).__name__
    try:
        document = json.loads(rendered)
        rebuilt: object
        if isinstance(artifact, BaseModel):
            rebuilt = type(artifact).model_validate(document)
            if rebuilt is artifact:
                raise ArtifactIsolationRefused(
                    artifact_type=artifact_type,
                    door=door,
                    reason=(
                        "reconstruction returned the artifact itself"
                        " (a validator that interns instances by content)"
                    ),
                )
        else:
            rebuilt = document
    except (TypeError, ValueError) as exc:
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason=f"reconstruction raised {type(exc).__name__}: {exc}",
        ) from exc
    if type(rebuilt) is not type(artifact):
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason=f"reconstruction changed the type to {type(rebuilt).__name__}",
        )
    if canonical_bytes(rebuilt) != rendered:
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason="reconstruction changed the canonical bytes",
        )
    if rebuilt != artifact:
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason="reconstruction is not equal to the artifact (a nested value changed type)",
        )
    return _Held(artifact=rebuilt, rendered=rendered)


def _isolated(artifact: object, *, door: str) -> object:
    """The sixth-round name for the write-side reconstruction, kept for its callers and its severings."""
    return _reconstructed(artifact, door=door).artifact


def _hash_of(rendered: bytes) -> str:
    """The content version of already-rendered canonical bytes — ``content_hash`` without the render."""
    return hashlib.sha256(rendered).hexdigest()


def _served(held: object, *, key: str, version: str, door: str) -> object:
    """The read side: parse the verified bytes and prove the result is the registered artifact.

    ``D-IMPL-380``, 2026-10-11 (Dave, 00:15): *"A successful parse is
    insufficient."* In order, each refusal by name:

    1. **Integrity** — the record holds both halves and its bytes hash to the
       version it sits under; otherwise :class:`RegistryIntegrityFailure`,
       never :class:`ControlPlaneMissing`.
    2. **Parse** — the bytes through the stored artifact's own type (the parsed
       document for a plain document). A parse that raises refuses.
    3. **Type** — the parse is the stored reconstruction's type.
    4. **Value** — the parse ``==`` the stored reconstruction, field by field,
       with no render. This is the proof: it does not assume that identical
       bytes make a validator deterministic; a validator that returns changed
       content on retrieval without raising fails here.
    5. **Identity** — the parse is not the stored reconstruction (an interning
       validator can hand back a cached instance from a parse). Checked for
       models and containers; an immutable scalar cannot be mutated and may be
       interned by the interpreter.

    Nothing here renders: that is the cost target, not the proof.
    """
    if not isinstance(held, _Held) or not held.rendered:
        raise RegistryIntegrityFailure(
            key=key,
            version=version,
            door=door,
            reason="the record holds no verified canonical bytes beside its reconstruction",
        )
    if _hash_of(held.rendered) != version:
        raise RegistryIntegrityFailure(
            key=key,
            version=version,
            door=door,
            reason="the stored canonical bytes do not hash to the version they sit under",
        )
    stored = held.artifact
    artifact_type = type(stored).__name__
    try:
        document = json.loads(held.rendered)
        served: object = (
            type(stored).model_validate(document) if isinstance(stored, BaseModel) else document
        )
    except (TypeError, ValueError) as exc:
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason=f"the parse of the verified bytes raised {type(exc).__name__}: {exc}",
        ) from exc
    if type(served) is not type(stored):
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason=f"the parse changed the type to {type(served).__name__}",
        )
    if isinstance(stored, (BaseModel, dict, list)) and served is stored:
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason=(
                "the parse returned the stored reconstruction itself"
                " (a validator that interns instances by content)"
            ),
        )
    if served != stored:
        raise ArtifactIsolationRefused(
            artifact_type=artifact_type,
            door=door,
            reason=(
                "the parse is not equal to the stored reconstruction"
                " (a validator that returns changed content on retrieval)"
            ),
        )
    return served


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
        self._artifacts: dict[tuple[str, str], _Held] = {}
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
        boundary rather than stored in a form replay could not reproduce. It
        must also survive reconstruction from that form with its type and
        value intact (``D-IMPL-380``, sixth round): a plain mapping holding a
        ``Decimal``, a ``datetime`` or a tuple — or a bare tuple, ``datetime``
        or ``Decimal`` as the artifact — renders faithfully but rebuilds as a
        different Python type, and is refused rather than stored with its
        values silently changed. Register a typed model instead; its
        validators restore the types.

        **An untyped document is JSON-native** (``D-IMPL-380``, 2026-10-10
        18:25): the values it may hold are exactly those ``json.loads`` of its
        own canonical bytes gives back — ``str``, ``int``, ``bool``, ``None``,
        ``list`` and ``dict`` — because that parse *is* the reconstruction the
        registry stores and serves. A ``model_dump()`` in python mode is not
        such a document: it keeps the model's ``Decimal``, ``datetime`` and
        tuple values, and is refused. Pass the model itself, or
        ``model_dump(mode="json")``. Nothing is coerced; the canonical
        restrictions above stay as they are.

        Registering byte-identical content again is idempotent: the existing
        version is returned and no duplicate is appended.

        Raises:
            ccf.authz.capability.CapabilityBypassError: ``authorized`` is
                fabricated, retargeted, or not one of :data:`REGISTER_KINDS`.
            CrossTenantKeyRefused: the key's tenant segment is not the
                capability's tenant.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
            ArtifactIsolationRefused: the artifact could not be reconstructed
                from its canonical form with its type, bytes, value and
                identity preserved; nothing was registered (``D-IMPL-380``,
                sixth round).
        """
        key = _door_key(authorized)
        actor = authorized.principal
        # D-IMPL-380, sixth round: the registry's own reconstruction is built
        # and verified BEFORE any registration state changes, so a refusal
        # leaves no version, no binding and no audit row behind — on every
        # registration, including an idempotent one, so the drift refusal
        # cannot be bypassed by registering known bytes under a drifted value.
        # Rendered once: the version is the hash of the bytes the record keeps.
        held = _reconstructed(artifact, door="register")
        version = _hash_of(held.rendered)
        known = version in self._versions.get(key, ())
        versions = self._versions.setdefault(key, [])
        if not known:
            versions.append(version)
            self._artifacts[(key, version)] = held
        self._record(
            action="register", key=key, version=version, resolved=True, actor=actor
        )
        return version

    def register_typed(
        self,
        authorized: TypedRegisterAuthority,
        artifact: object,
        artifact_class: ArtifactClass,
    ) -> str:
        """Validate ``artifact`` against ``artifact_class``, then register it under ``authorized.resource``.

        Under the invalidation-record kind (``D-IMPL-382``) the key is not the capability's
        resource but derived from the record by :func:`_invalidation_record_key`, which also
        confines the kind to its own tenant's invalidation records.

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
            ccf.controlplane.artifact_base.ArtifactClassIdMismatch: the
                artifact states a ``class_id`` other than ``artifact_class``'s
                own — a ``TypeError``, raised by ``artifact_class.validate``
                before anything is stored or audited (``D-IMPL-378``).
            ccf.controlplane.artifact_base.ReservedArtifactClassId: the
                artifact states ``artifact_class``'s own ``class_id`` and it is
                in the reserved ``ccf.`` namespace — a ``ValueError``, raised by
                ``artifact_class.validate`` before anything is stored or audited
                (``D-IMPL-378`` K1 follow-up).
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
            ArtifactIsolationRefused: the artifact could not be reconstructed
                from its canonical form with its type, bytes, value and
                identity preserved; nothing was registered (``D-IMPL-380``,
                sixth round).
        """
        if getattr(authorized, "kind", None) is InvalidationRecordRegister:
            record_authority = cast(Authorized[InvalidationRecordRegister], authorized)
            key = _invalidation_record_key(record_authority, artifact_class, artifact_class.validate(artifact))
        else:
            key = _door_key(cast(RegisterAuthority, authorized))
        actor = authorized.principal
        bound = self._classes.get(key)
        if bound is not None and bound != artifact_class.class_id:
            raise TypeError(
                f"key {key!r} is already bound to artifact class {bound!r};"
                f" refusing to rebind it to {artifact_class.class_id!r}"
            )
        artifact_class.validate(artifact)
        # D-IMPL-380, sixth round: reconstructed and re-validated against the
        # class before any registration state changes, on every registration
        # (the idempotent path verifies too; it only skips the store).
        # Rendered once: the version is the hash of the bytes the record keeps.
        rebuilt = _reconstructed(artifact, door="register_typed")
        version = _hash_of(rebuilt.rendered)
        known = version in self._versions.get(key, ())
        held = _Held(artifact=artifact_class.validate(rebuilt.artifact), rendered=rebuilt.rendered)
        versions = self._versions.setdefault(key, [])
        if not known:
            versions.append(version)
            self._artifacts[(key, version)] = held
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
            ccf.controlplane.artifact_base.ArtifactClassIdMismatch: the
                artifact states a ``class_id`` other than ``artifact_class``'s
                own — a ``TypeError``, raised by ``artifact_class.validate``
                before anything is stored or audited (``D-IMPL-378``).
            ccf.controlplane.artifact_base.ReservedArtifactClassId: the
                artifact states ``artifact_class``'s own ``class_id`` and it is
                in the reserved ``ccf.`` namespace — a ``ValueError``, raised by
                ``artifact_class.validate`` before anything is stored or audited
                (``D-IMPL-378`` K1 follow-up).
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form.
            ArtifactIsolationRefused: the artifact could not be reconstructed
                from its canonical form with its type, bytes, value and
                identity preserved; nothing was registered (``D-IMPL-380``,
                sixth round).
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
        rendered = canonical_bytes(validated)
        incoming = _hash_of(rendered)
        # The D-05 comparison asks whether the artifact's *content* changed,
        # and the content of an author-versioned artifact is everything except
        # the version claim itself — a bump alone must not read as a content
        # change, or the empty-bump outcome could never fire. The fingerprint
        # normalizes artifact_version before hashing; the stored registry
        # version stays the full content hash (D-IMPL-26 identity).
        fingerprint = content_hash(
            validated.model_copy(update={"artifact_version": ""})
        )
        # D-IMPL-380, sixth round: read-only until the reconstruction below has
        # been verified — `setdefault` here left an empty bump map behind a
        # refusal (the sixth-round delta review, both CLI seats).
        bumps = self._bumps.get(key, {})

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
        known = incoming in self._versions.get(key, ())
        # D-IMPL-380, sixth round: reconstructed and re-validated against the
        # class before any registration state changes — after the D-05 refusals
        # above, which record a refusal and never a registration — on every
        # registration (the idempotent path verifies too; it only skips the store).
        rebuilt = _reconstructed(validated, door="register_versioned", rendered=rendered)
        held = _Held(artifact=artifact_class.validate(rebuilt.artifact), rendered=rebuilt.rendered)
        versions = self._versions.setdefault(key, [])
        if not known:
            versions.append(incoming)
            self._artifacts[(key, incoming)] = held
        self._classes[key] = artifact_class.class_id
        bumps = self._bumps.setdefault(key, {})
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
            ArtifactIsolationRefused: the stored artifact could not be
                reconstructed faithfully; nothing is returned and nothing is
                reported missing (``D-IMPL-380``, sixth round).
            RegistryIntegrityFailure: the record is missing its verified bytes
                or they do not hash to ``version``; corruption, not absence.
        """
        try:
            held = self._artifacts[(key, version)]
        except KeyError:
            raise ControlPlaneMissing(
                f"no Control Plane artifact registered as ({key!r}, {version!r})"
            ) from None
        # D-IMPL-380, sixth round: a reader receives a reconstruction, never
        # the registry's object — the door the fifth-round bypass used.
        return _served(held, key=key, version=version, door="peek")

    def resolve(self, key: str, version: str) -> object:
        """Return the exact artifact registered as ``(key, version)``.

        Raises:
            ControlPlaneMissing: no such key, or no such version under it.
            ArtifactIsolationRefused: the stored artifact could not be
                reconstructed faithfully; nothing is returned and nothing is
                reported missing (``D-IMPL-380``, sixth round).
            RegistryIntegrityFailure: the record is missing its verified bytes
                or they do not hash to ``version``; corruption, not absence.
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
        # D-IMPL-380, sixth round: reconstructed before the success row. A
        # refusal serves nothing and is recorded as a resolve that did not
        # resolve — the module's promise is that every resolve, a failed one
        # included, reaches the audit plane (the sixth-round delta review,
        # Fable seat, F3).
        try:
            served = _served(artifact, key=key, version=version, door="resolve")
        except (ArtifactIsolationRefused, RegistryIntegrityFailure):
            self._record(action="resolve", key=key, version=version, resolved=False)
            raise
        self._record(action="resolve", key=key, version=version, resolved=True)
        return served

    def resolve_latest(self, key: str) -> tuple[str, object]:
        """Return the most recently registered ``(version, artifact)``.

        Deliberately separate from :meth:`resolve`: reaching for "latest" is a
        choice a caller states, never one it inherits by leaving an argument
        off. Replay paths must not use this method.

        Raises:
            ControlPlaneMissing: nothing has been registered under ``key``.
            ArtifactIsolationRefused: the stored artifact could not be
                reconstructed faithfully; nothing is returned and nothing is
                reported missing (``D-IMPL-380``, sixth round, site 6).
            RegistryIntegrityFailure: the record is missing its verified bytes
                or they do not hash to the version; corruption, not absence.
        """
        versions = self._versions.get(key)
        if not versions:
            self._record(action="resolve_latest", key=key, version="", resolved=False)
            raise ControlPlaneMissing(
                f"no Control Plane versions registered under {key!r}"
            )
        version = versions[-1]
        # D-IMPL-380, sixth round, SITE 6 — beyond the five sites the order
        # enumerated. The order named `peek` and `resolve`; this is a third
        # read door, and it returned the registry's object by reference (the
        # sixth-round delta review: every seat; the Fable seat replayed the
        # grant-sink exploit through it). The same reconstruction, through the
        # same helper, before the success row; a refusal is recorded as a
        # resolve that did not resolve. Struck by one revert if the ruling
        # keeps to the five.
        try:
            served = _served(
                self._artifacts[(key, version)], key=key, version=version, door="resolve_latest"
            )
        except (ArtifactIsolationRefused, RegistryIntegrityFailure):
            self._record(
                action="resolve_latest", key=key, version=version, resolved=False
            )
            raise
        self._record(
            action="resolve_latest", key=key, version=version, resolved=True
        )
        return version, served

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
