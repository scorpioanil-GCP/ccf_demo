"""The erasure-consulting store — the ONE consult at the substrate read (G4; SEC-009, `D-IMPL-374` (4)).

Design ``D-IMPL-367`` §3 with fix-round-1 rulings C1, (i), (ii), I3, I6, I7.
The consult lives inside the store the deployment holds, as a decorator
around whatever store it is given, composed at EVERY store construction site
through :func:`compose_erasure_consult`, over a REQUIRED
:class:`~ccf.erasure.ErasureIndexProtocol` — a composition without a declared
index refuses by name (:class:`ErasureIndexUnavailable`). On an empty index
the decorator is identity.

* **Tenant scope (I6, ruling (i)).** A store composed for a tenant — or the
  per-tenant view :meth:`ErasureConsultingStore.scoped` a multi-tenant door
  takes for the caller's VERIFIED tenant — withholds only what that tenant
  erased, with the erasure's reason, instant and record address. A
  tenantless read (the replay engine, ``record_of``, child admission, the MCP
  client lane) WITHHOLDS if any tenant erased the address, with the reason and
  record address REDACTED, so no tenant learns another's erasure.
* **The record is the only authority (U7, §8, I3), and it is door-signed
  (fix round 5, R2).** At composition every entry of every tenant
  (``tenants()`` → ``entries()``) is validated against its
  ``ccf.erasure-record``, read through the inner store
  (:func:`~ccf.erasure.verify_erasure_entry`): the entry's tenant selects its
  declared :class:`~ccf.erasure.ErasureAuthority` (R4); the bytes must hash to
  the entry's record address; the erasure DOOR's signature must verify over
  them under that authority's door keys — before any field of the record is
  read; and the record must name the tenant, the address, the hashed subject
  and the approval reference the entry carries. Its approval is then verified
  against the same authority (:func:`~ccf.erasure.verify_erasure_approval`).
  An entry that fails — its record missing (a completion that died between
  the write-ahead entry and the record), unsigned, or disagreeing — still
  withholds its address, with the reason ``index-unsupported`` and nothing of
  the record, and is audited ``erasure_index_unsupported``. An entry appended
  after composition is validated the first time a read meets it.
* **O(1) per read (I7).** A scoped read is one ``lookup``; a tenantless read
  is one ``lookup`` per tenant. No read scans entries.

:meth:`ErasureConsultingStore.get` and :meth:`ErasureConsultingStore.resolve_uri`
consult; :meth:`ErasureConsultingStore.exists` does **not** (U8); ``put``
passes through. The Protocol's four verbs are unchanged and no removal or
un-erasure surface exists (U6). Algorithmic module (CINV-03): the
``index-unsupported`` audit event is stamped with the fabric clock injected at
composition (ruling 3), never a wall clock and never the disputed entry's own
``erased_at``.

**Boot validation is memoized per index head** (ruling 4): the key is the
index's identity (its file path, for the file index), its entry count, the
store's identity (its root, for a file store), the Control Plane's **policy
head** — :func:`~ccf.erasure.approval.policy_head`, the digest of its
registration history — the digest of the composed
:class:`~ccf.erasure.ErasureTrust`, and the **identity provider instance**
the verdicts were judged with (fix round 5, R3), held strongly in the memo
entry so its identity cannot be reused by another object while the entry
lives. So a site that composes once per question — the governed resolver —
does not re-read every record; an append changes the count, ANY Control Plane
registration (a rotated HITL policy foremost) changes the head, and either
invalidates it; and a verdict judged under one provider — a do-nothing one,
say — is never served to a site that composed another. The same head keys
the verdicts a composed store and its tenant views hold: a registration
re-judges them on the next consult. A verdict is never keyed by a Control
Plane object's identity (fix round 4, ruling 4). Only SUPPORTED entries are
memoized: an unsupported one is re-judged, and audited, by every composition.

**The trust root is fixed at composition** (fix round 4, rulings 1 and 5;
fix round 5, R1, R2, R4): every site passes the deployment's Control Plane and
its :class:`~ccf.erasure.ErasureTrust` — for each tenant that may erase, the
HITL policy key its HITL transport is bound to, the content hash of its
erasure workflow, and the erasure door's public signing key — and there is no
fresh-registry fallback; a composition without them, or a re-composition of
an already composed store with a different Control Plane, identity provider
or trust, refuses by name (:class:`~ccf.erasure.ErasureCompositionRefused`).
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Final

from pydantic import ValidationError

from ccf.artifacts.protocol import (
    ArtifactName,
    ArtifactRef,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    ArtifactWriteAuthority,
    WriteKinds,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.audit import AuditLog
from ccf.erasure.approval import (
    ErasureApprovalInvalid,
    PinnedPolicySource,
    policy_head,
    reference_approval_verifier,
    verify_erasure_approval,
)
from ccf.erasure.contracts import ERASURE_RECORD_CLASS, ErasureApproval, ErasureRecord
from ccf.erasure.errors import ErasedContentRefused, ErasureCompositionRefused, ErasureIndexCorrupt
from ccf.erasure.index import ErasureIndexEntry, ErasureIndexProtocol
from ccf.erasure.trust import ErasureAuthority, ErasureTrust, verify_erasure_entry
from ccf.peering.identity import IdentityProvider

__ccf_mode__ = "algorithmic"

__all__ = [
    "INDEX_UNSUPPORTED",
    "ErasedContentRefused",
    "ErasureCompositionRefused",
    "ErasureConsultingStore",
    "ErasureIndexUnavailable",
    "compose_erasure_consult",
]

#: The reason a withheld address carries when its index entry is not supported
#: by an agreeing erasure record (design §8; mechanism vocabulary).
INDEX_UNSUPPORTED: Final[str] = "index-unsupported"


class ErasureIndexUnavailable(TypeError):
    """A store construction site declared no erasure index (SEC-009; `D-IMPL-374` (4), C1).

    Raised at composition — where an operator sees it — never at a read: a
    store that could not consult would serve erased bytes silently.
    """


#: Supported-entry keys per (index head, store, policy head, trust, identity
#: provider) — ruling 4, and fix round 5 R3. Each value holds the provider
#: instance the verdicts were judged with, STRONGLY: its identity is part of the
#: key, so it must not be reused by another object while the entry lives, and a
#: read is honored only when the entry's provider IS the reader's. Bounded: the
#: oldest head is dropped past the bound, which only costs a re-validation.
_VALIDATED_HEADS: dict[
    tuple[str, int, str, str, str, int],
    tuple[IdentityProvider, frozenset[tuple[str, str, str]]],
] = {}
_VALIDATED_HEADS_BOUND: Final[int] = 64
_VALIDATED_HEADS_LOCK = threading.Lock()


def _identity(subject: object, attribute: str) -> str:
    named = getattr(subject, attribute, None)
    return f"{attribute}:{named}" if named is not None else f"id:{id(subject)}"


class _Verdicts:
    """Validation results shared by a composed store and its tenant views.

    Keyed by the Control Plane's policy head (fix round 4, ruling 4): when the
    head moves — any registration — every SUPPORTED verdict is dropped and
    re-judged on the next consult. ``audited`` is kept, so an entry already
    audited unsupported is not audited again for the same reason.
    """

    def __init__(self) -> None:
        self.valid: set[tuple[str, str, str]] = set()
        self.audited: set[tuple[str, str, str]] = set()
        self.corrupt: str | None = None
        self.head: str | None = None

    def refresh(self, head: str) -> None:
        """Drop every supported verdict judged under a different policy head."""
        if head != self.head:
            self.valid.clear()
            self.head = head


class ErasureConsultingStore:
    """An :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` that refuses to serve erased content (SEC-009; `D-IMPL-374` (4)).

    Construct through :func:`compose_erasure_consult`.
    """

    def __init__(
        self,
        inner: ArtifactStoreProtocol,
        *,
        index: ErasureIndexProtocol,
        audit_log: AuditLog,
        clock: Callable[[], datetime],
        control_plane: PinnedPolicySource,
        erasure_trust: ErasureTrust,
        tenant_id: str | None,
        identity_provider: IdentityProvider | None = None,
        _verdicts: _Verdicts | None = None,
    ) -> None:
        self._inner = inner
        self._index = index
        self._audit_log = audit_log
        self._clock = clock
        self._control_plane = control_plane
        self._erasure_trust = erasure_trust
        self._trust_digest = content_hash(erasure_trust)
        # The provider as DECLARED (``None`` is the reference verifier), kept
        # so a re-composition can be held to the same declaration (ruling 5).
        self._declared_identity_provider = identity_provider
        self._identity_provider = (
            reference_approval_verifier() if identity_provider is None else identity_provider
        )
        self._tenant_id = tenant_id
        self._verdicts = _Verdicts() if _verdicts is None else _verdicts

    # -- composition introspection ------------------------------------------------

    @property
    def inner(self) -> ArtifactStoreProtocol:
        """The decorated store."""
        return self._inner

    @property
    def index(self) -> ErasureIndexProtocol:
        """The declared erasure index."""
        return self._index

    @property
    def control_plane(self) -> PinnedPolicySource:
        """The Control Plane each approval's pinned HITL policy is resolved through (fix round 4)."""
        return self._control_plane

    @property
    def erasure_trust(self) -> ErasureTrust:
        """The per-tenant erasure authorities fixed at composition (SEC-009; `D-IMPL-374` (4), fix round 5, R1, R2, R4)."""
        return self._erasure_trust

    @property
    def identity_provider(self) -> IdentityProvider | None:
        """The identity provider as declared at composition; ``None`` is the SDK's reference verifier."""
        return self._declared_identity_provider

    @property
    def tenant_id(self) -> str | None:
        """The tenant this view is scoped to, or ``None`` for tenantless reads."""
        return self._tenant_id

    @property
    def write_kinds(self) -> WriteKinds | None:
        """The inner store's write-kinds declaration, so wiring checks read through the decorator."""
        declared = getattr(self._inner, "write_kinds", None)
        return declared if isinstance(declared, WriteKinds) else None

    def names_at(self, *, content_address: str) -> tuple[ArtifactName, ...]:
        """The inner store's naming introspection — never a byte read.

        Raises:
            AttributeError: the inner store answers no naming (C2 then refuses
                an erasure over it by name, ``class-unverifiable``).
        """
        names = getattr(self._inner, "names_at")
        found: tuple[ArtifactName, ...] = names(content_address=content_address)
        return found

    def scoped(self, tenant_id: str) -> "ErasureConsultingStore":
        """This store as one tenant's view (I6): withholds only what ``tenant_id`` erased."""
        return ErasureConsultingStore(
            self._inner,
            index=self._index,
            audit_log=self._audit_log,
            clock=self._clock,
            control_plane=self._control_plane,
            erasure_trust=self._erasure_trust,
            tenant_id=tenant_id,
            identity_provider=self._declared_identity_provider,
            _verdicts=self._verdicts,
        )

    def validate_all(self) -> None:
        """Validate every entry of every tenant against its record (boot; §8), memoized per index head (ruling 4)."""
        try:
            entries = [
                entry
                for tenant in sorted(self._index.tenants())
                for entry in self._index.entries(tenant_id=tenant)
            ]
        except ErasureIndexCorrupt as corrupt:
            # N3: the store composes and then refuses EVERY read — fail closed.
            self._verdicts.corrupt = str(corrupt)
            return
        # The Control Plane's POLICY HEAD is part of the memo key: verification
        # resolves the pinned HITL policy, the approval policy and the workflow
        # definition THROUGH it, so a head validated under one registration
        # history is never accepted under another, and any registration — a
        # rotated HITL policy foremost — re-validates (fix round 4, ruling 4).
        # Never the Control Plane object's identity. The composed trust and the
        # identity provider INSTANCE are part of it too (fix round 5, R3): a
        # verdict judged under one provider — a do-nothing one, say — is never
        # served to a site composed with another. The provider is held strongly
        # in the entry, and honored only when it IS this site's.
        policies = policy_head(self._control_plane)
        self._verdicts.refresh(policies)
        head = (
            _identity(self._index, "path"),
            len(entries),
            _identity(self._inner, "root"),
            f"policies:{policies}",
            f"trust:{self._trust_digest}",
            id(self._identity_provider),
        )
        with _VALIDATED_HEADS_LOCK:
            cached = _VALIDATED_HEADS.get(head)
        known = cached[1] if cached is not None and cached[0] is self._identity_provider else None
        keys = {(e.tenant_id, e.content_address, e.erasure_record_address) for e in entries}
        if known is not None:
            self._verdicts.valid |= known & keys
        for entry in entries:
            self._supported(entry)
        with _VALIDATED_HEADS_LOCK:
            _VALIDATED_HEADS[head] = (self._identity_provider, frozenset(self._verdicts.valid & keys))
            while len(_VALIDATED_HEADS) > _VALIDATED_HEADS_BOUND:
                _VALIDATED_HEADS.pop(next(iter(_VALIDATED_HEADS)))

    # -- the consult -------------------------------------------------------------------

    def _supported(self, entry: ErasureIndexEntry) -> bool:
        """Whether ``entry``'s record exists and agrees; audits a disagreement once."""
        key = (entry.tenant_id, entry.content_address, entry.erasure_record_address)
        if key in self._verdicts.valid:
            return True
        try:
            payload = self._inner.get(content_address=entry.erasure_record_address)
            # Fix round 5: the entry's tenant selects its declared authority
            # (R4); the DOOR's signature is verified over the bytes before any
            # field of the record is read (R2); then every fact the entry
            # carries must be the RECORD's (U7; N2) — the served reason and
            # instant are therefore the record's own — and its approval must
            # verify against the same authority.
            record, authority = verify_erasure_entry(
                entry, payload, trust=self._erasure_trust, identity_provider=self._identity_provider
            )
            agrees = self._approved(record, authority)
        except (ArtifactStoreError, KeyError, OSError, ValidationError, ValueError):
            agrees = False
        if agrees:
            self._verdicts.valid.add(key)
            return True
        if key not in self._verdicts.audited:
            self._verdicts.audited.add(key)
            self._audit_log.append(
                action="erasure_index_unsupported",
                key=f"{entry.tenant_id}/{entry.content_address}",
                version=entry.erasure_record_address,
                resolved=False,
                occurred_at=self._clock(),
                artifact_class=ERASURE_RECORD_CLASS,
            )
        return False

    def _approved(self, record: ErasureRecord, authority: ErasureAuthority) -> bool:
        """Whether ``record.approval_ref`` resolves to a VERIFIED signed approval of this request (fix rounds 4 and 5).

        The door filed it before the index append; it is content-addressed and
        immutable, and the door-signed record names it. It must be for the
        tenant's DECLARED erasure workflow, in that tenant (fix round 5, R1);
        its signed HITL attestation is verified against the key the tenant's
        HITL policy — the key fixed at composition, at the version the approval
        pins — declares for the signer, resolved through this store's composed
        Control Plane; its signed claims must name this request's gate, this
        tenant, the gate's state hash, the record's approver and the approving
        verdict; the signature must predate that version's supersession; the
        approver must not be the requester the door signed and must be eligible
        under the declared workflow's gate policy; and the gate must be one that
        workflow declares (:func:`~ccf.erasure.approval.verify_erasure_approval`).
        A missing, unsigned or unverifiable approval raises, and the caller
        counts that as unsupported.
        """
        payload = self._inner.get(content_address=record.approval_ref)
        if hashlib.sha256(payload).hexdigest() != record.approval_ref:
            return False
        approval = ErasureApproval.model_validate_json(payload)
        try:
            verify_erasure_approval(
                approval,
                tenant_id=record.tenant_id,
                request_id=record.request_id,
                approver=record.actor,
                requested_by=record.requested_by,
                authority=authority,
                control_plane=self._control_plane,
                identity_provider=self._identity_provider,
            )
        except ErasureApprovalInvalid:
            return False
        return True

    def _refusal(self, entry: ErasureIndexEntry, *, disclose: bool) -> ErasedContentRefused:
        # A registration since the last judgment re-judges (ruling 4); reads
        # that meet no erased address never touch the Control Plane.
        self._verdicts.refresh(policy_head(self._control_plane))
        supported = self._supported(entry)
        if not supported:
            return ErasedContentRefused(
                content_address=entry.content_address,
                erasure_record_address=None,
                reason=INDEX_UNSUPPORTED if disclose else None,
                erased_at=None,
            )
        return ErasedContentRefused(
            content_address=entry.content_address,
            erasure_record_address=entry.erasure_record_address if disclose else None,
            reason=entry.reason if disclose else None,
            erased_at=entry.erased_at if disclose else None,
        )

    def _consult(self, content_address: str) -> None:
        """THE consult: refuse an address the index names as erased."""
        try:
            self._consult_index(content_address)
        except ErasureIndexCorrupt as corrupt:
            # N3: typed, and closed — no address is served under a corrupt index.
            raise ErasureIndexCorrupt(str(corrupt), content_address=content_address) from None

    def _consult_index(self, content_address: str) -> None:
        if self._verdicts.corrupt is not None:
            raise ErasureIndexCorrupt(self._verdicts.corrupt)
        if self._tenant_id is not None:
            entry = self._index.lookup(tenant_id=self._tenant_id, content_address=content_address)
            if entry is not None:
                raise self._refusal(entry, disclose=True)
            return
        for tenant in sorted(self._index.tenants()):
            entry = self._index.lookup(tenant_id=tenant, content_address=content_address)
            if entry is not None:
                raise self._refusal(entry, disclose=False)

    # -- the four Protocol verbs -------------------------------------------------------

    def put(self, authorized: ArtifactWriteAuthority, artifact: object) -> ArtifactRef:
        """Pass through to the inner store: erasure is a read-side control (SEC-009)."""
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        """The inner store's bytes, unless the index names the address erased (SEC-009).

        Raises:
            ErasedContentRefused: the address was erased.
        """
        self._consult(content_address)
        return self._inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        """The inner store's truth; deliberately NOT consulted (U8; SEC-009)."""
        return self._inner.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        """The inner store's resolution, refused when it names an erased address (SEC-009).

        Raises:
            ErasedContentRefused: the resolved address was erased.
        """
        address = self._inner.resolve_uri(uri=uri)
        self._consult(address)
        return address


def compose_erasure_consult(
    store: ArtifactStoreProtocol,
    *,
    index: ErasureIndexProtocol,
    audit_log: AuditLog,
    clock: Callable[[], datetime],
    control_plane: PinnedPolicySource,
    erasure_trust: ErasureTrust,
    tenant_id: str | None = None,
    identity_provider: IdentityProvider | None = None,
) -> ErasureConsultingStore:
    """THE composition helper every store construction site uses (SEC-009; `D-IMPL-374` (4), C1, (i), U12).

    Wraps ``store`` over the REQUIRED ``index``, the REQUIRED fabric
    ``clock`` (which stamps the ``index-unsupported`` audit; ruling 3), the
    REQUIRED ``control_plane`` — the DEPLOYMENT's, through which each approval's
    pinned HITL policy, the declared erasure workflow and its gate's approval
    policy are resolved; there is no fresh-registry fallback (fix round 4,
    ruling 5) — and the REQUIRED ``erasure_trust`` (fix round 5, R1, R2, R4):
    for each tenant that may erase, its :class:`~ccf.erasure.ErasureAuthority`
    — the HITL policy key its HITL transport is bound to, the content hash of
    its erasure workflow, and the erasure door's public signing key. The
    record's tenant selects the authority; a tenant with none is
    ``index-unsupported``; a single-tenant site declares one entry, and a site
    that runs no erasure door declares none. ``identity_provider`` is the
    verifier the deployment's HITL transport verifies with — and the door
    signature is verified with it too; ``None`` is the SDK's reference
    detached-JWS verifier (no signing material). An adopter-supplied provider
    that verifies nothing accepts everything; that is the adopter's trust
    choice. It validates every entry against its record (§8; memoized per index
    head, policy head, trust and provider instance — ruling 4, R3), and returns
    the store scoped to ``tenant_id`` — or tenantless (``None``) for a
    multi-tenant site whose doors take :meth:`ErasureConsultingStore.scoped`
    views for the caller's verified tenant. A store already composed is
    re-scoped, never re-wrapped: it must have been composed over the SAME index
    (M1) and with the SAME Control Plane, identity provider and trust (ruling 5).

    Raises:
        ErasureIndexUnavailable: ``index`` is not an
            :class:`~ccf.erasure.ErasureIndexProtocol`, or ``store`` was already
            composed over a different index.
        ErasureCompositionRefused: no Control Plane, or one that offers no
            pinned-read surface; ``erasure_trust`` is not an
            :class:`~ccf.erasure.ErasureTrust`; or ``store`` was already
            composed with a different Control Plane, identity provider or trust.
    """
    if control_plane is None or not isinstance(control_plane, PinnedPolicySource):
        raise ErasureCompositionRefused(
            "the erasure consult is composed over the DEPLOYMENT's Control Plane —"
            f" got {type(control_plane).__name__}; there is no fresh-registry"
            " fallback, because a consult verifying against a registry that lacks"
            " the deployment's HITL policy would mark every genuine erasure"
            " index-unsupported (SEC-009; D-IMPL-374 (4), fix round 4, ruling 5)"
        )
    if not isinstance(erasure_trust, ErasureTrust):
        raise ErasureCompositionRefused(
            "the erasure consult takes the deployment's ErasureTrust — for each"
            " tenant that may erase, its HITL policy key, its erasure workflow's"
            " content hash and the erasure door's public key, fixed here and never"
            f" chosen by a filed artifact; got {type(erasure_trust).__name__}"
            " (SEC-009; D-IMPL-374 (4), fix round 5, R1, R2, R4)"
        )
    if not isinstance(index, ErasureIndexProtocol):
        raise ErasureIndexUnavailable(
            f"{type(index).__name__} is not an ErasureIndexProtocol; every store"
            " construction site declares its durable erasure index, and a store"
            " that cannot consult would serve erased content (SEC-009; D-IMPL-374"
            " (4), C1)"
        )
    if isinstance(store, ErasureConsultingStore):
        # N1: the SAME index by identity of what it is — its file path —
        # never by object identity (a deployment reopens its index).
        if _identity(store.index, "path") != _identity(index, "path"):
            raise ErasureIndexUnavailable(
                "this store was already composed over a different erasure index;"
                " re-composing it over another would consult the wrong erasures"
                " (SEC-009; M1)"
            )
        # Ruling 5: the trust root a store was composed with is never silently
        # replaced — a different Control Plane, identity provider or trust
        # refuses by name.
        for axis, same in (
            ("control_plane", store.control_plane is control_plane),
            ("identity_provider", store.identity_provider is identity_provider),
            ("erasure_trust", store.erasure_trust == erasure_trust),
        ):
            if not same:
                raise ErasureCompositionRefused(
                    f"this store was already composed with a different {axis}; a"
                    " re-composition that ignored the new one would leave the store"
                    " verifying against a trust root this site did not name (SEC-009;"
                    " D-IMPL-374 (4), fix round 4, ruling 5)"
                )
        if store.tenant_id == tenant_id:
            return store
        return store.scoped(tenant_id) if tenant_id is not None else ErasureConsultingStore(
            store.inner,
            index=index,
            audit_log=audit_log,
            clock=clock,
            control_plane=control_plane,
            erasure_trust=erasure_trust,
            tenant_id=None,
            identity_provider=identity_provider,
            _verdicts=store._verdicts,
        )
    composed = ErasureConsultingStore(
        store,
        index=index,
        audit_log=audit_log,
        clock=clock,
        control_plane=control_plane,
        erasure_trust=erasure_trust,
        tenant_id=tenant_id,
        identity_provider=identity_provider,
    )
    composed.validate_all()
    return composed
