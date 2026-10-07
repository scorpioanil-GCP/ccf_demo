"""The erasure trust root, fixed at composition per tenant, and the door's record signature (SEC-009; `D-IMPL-374` (4), fix round 5).

What an erasure is verified AGAINST is the deployment's statement, made once
at every store construction site and at the erasure door — never something a
filed artifact chooses. The fix-round-5 rulings:

* **R1 — the erasure workflow is fixed at composition.** An
  :class:`ErasureAuthority` names the content hash of the deployment's erasure
  workflow definition and that workflow's tenant. An approval for any other
  workflow, or in any other tenant, refuses by name; the approval policy an
  approver is judged eligible under is THAT workflow's gate's, resolved from
  the Control Plane at its pinned version — never a field of a filed record
  (``ErasureRecord`` names no approval policy).
* **R2 — the record is door-signed.** The erasure door signs the canonical
  bytes of every :class:`~ccf.erasure.ErasureRecord` it files with a
  deployment-held signing key that requesters never hold; the authority
  declares that key's PUBLIC half (private material is refused by name). The
  consult verifies the door signature before it trusts any field of the
  record (:func:`verify_erasure_entry`), so ``requested_by`` is the principal
  the door observed — the starter the engine recorded — and not what a filer
  wrote. A record without a verifying door signature is ``index-unsupported``
  and audited. The signature asserts, in its protected header, that it signs
  an erasure record (:data:`DOOR_SIGNATURE_ASSERTION`), so a door-key
  signature made for anything else never verifies as one.
* **R4 — per tenant.** :class:`ErasureTrust` maps each tenant that may erase
  to its authority: its HITL policy key (fix round 4, ruling 1), its erasure
  workflow and its door keys. The record's tenant selects the authority; a
  tenant with no authority refuses by name (``erasure-tenant-undeclared``). A
  single-tenant site declares one entry; a site that runs no erasure door
  declares none, and every erasure its index names is withheld as
  ``index-unsupported``.

**Where the door's signature travels.** In every index entry naming the
record (``door_signature``, ``door_key_id``), not inside the record artifact.
An ES256 signature is not deterministic, and the write-ahead protocol (I4)
requires a retried completion to re-append the SAME entries and re-file the
SAME record: the retry reuses the signature its prior attempt appended. What
is signed is exactly the record's canonical bytes — exactly the bytes the store
holds at the entry's ``erasure_record_address`` — so the consult verifies the
signature over the bytes it read, before parsing them.

Disclosed: the door's signature is as strong as the custody of the door's
private key, and an adopter-supplied identity provider that verifies nothing
accepts everything, door signatures included.

Algorithmic module (CINV-03): pure functions over typed inputs; no clock.
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from typing import Final

from pydantic import field_validator, model_validator

from ccf.artifacts.protocol import CONTENT_ADDRESS_PATTERN
from ccf.contracts.base import CCFContract
from ccf.erasure.contracts import ERASURE_RECORD_CLASS, ErasureRecord
from ccf.erasure.index import ErasureIndexEntry
from ccf.peering.identity import (
    IdentityError,
    IdentityProvider,
    JsonWebKey,
    SignedContextProduct,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "DOOR_SIGNATURE_ASSERTION",
    "ErasureAuthority",
    "ErasureRecordInvalid",
    "ErasureTrust",
    "sign_erasure_record",
    "verify_door_signature",
    "verify_erasure_entry",
]

#: The protected-header member a door signature asserts, with the value
#: :data:`~ccf.erasure.ERASURE_RECORD_CLASS`: the signature is FOR an erasure
#: record. Domain separation — a signature the door key made for anything else
#: does not verify as a record signature (SEC-009; `D-IMPL-374` (4), fix round
#: 5, R2).
DOOR_SIGNATURE_ASSERTION: Final[str] = "ccf_signed_class"

#: The JWK members that carry PRIVATE key material (RFC 7518 §6.2.2, §6.3.2,
#: §6.4.1). A declared door key holding one is refused by name: a consult holds
#: the door's PUBLIC key only — the signing key is the door's (R2).
_PRIVATE_JWK_MEMBERS: Final[frozenset[str]] = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth", "k"})

#: The separator of a detached compact JWS (RFC 7515 Appendix F).
_DETACHED_SEPARATOR: Final[str] = ".."

#: The Control Plane key grammar's separator, ``{tenant}/{class}/{name}``.
_KEY_SEPARATOR: Final[str] = "/"


class ErasureAuthority(CCFContract):
    """What ONE tenant's erasures are verified against, declared at composition (SEC-009; `D-IMPL-374` (4), fix round 5, R1/R2/R4).

    Attributes:
        tenant_id: The tenant — the erasure workflow's own tenant (R1).
        hitl_policy_key: The Control Plane key of the HITL policy the tenant's
            erasure gate runs under — the SAME key its HITL transport is bound
            to; it lies under ``tenant_id`` (fix round 4, ruling 1).
        workflow_definition_hash: The content hash of the tenant's erasure
            workflow definition (R1). An approval naming any other workflow
            refuses by name.
        door_keys: The erasure door's PUBLIC signing key(s), by key id (R2).
            A key carrying private material is refused by name.
    """

    tenant_id: str
    hitl_policy_key: str
    workflow_definition_hash: str
    door_keys: Mapping[str, JsonWebKey]

    @field_validator("tenant_id", "hitl_policy_key")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("an erasure authority's tenant and HITL policy key are non-empty (SEC-009)")
        return value

    @field_validator("workflow_definition_hash")
    @classmethod
    def _is_a_content_hash(cls, value: str) -> str:
        if not CONTENT_ADDRESS_PATTERN.match(value):
            raise ValueError(
                f"{value!r} is not a workflow definition's content hash (SEC-009; fix round 5, R1)"
            )
        return value

    @field_validator("door_keys")
    @classmethod
    def _public_only(cls, value: Mapping[str, JsonWebKey]) -> Mapping[str, JsonWebKey]:
        if not value:
            raise ValueError("an erasure authority declares at least one door key (SEC-009; fix round 5, R2)")
        for key_id, document in value.items():
            if not key_id:
                raise ValueError("a door key id is non-empty (SEC-009)")
            leaked = sorted(set(document) & _PRIVATE_JWK_MEMBERS)
            if leaked:
                raise ValueError(
                    f"door key {key_id!r} carries private key material {leaked!r}; a"
                    " composition declares the door's PUBLIC key only — the signing key"
                    " is held by the door and never by a reader (SEC-009; fix round 5, R2)"
                )
        return value

    @model_validator(mode="after")
    def _key_in_its_tenant(self) -> "ErasureAuthority":
        tenant, separator, _ = self.hitl_policy_key.partition(_KEY_SEPARATOR)
        if not separator or tenant != self.tenant_id:
            raise ValueError(
                f"HITL policy key {self.hitl_policy_key!r} does not lie under tenant"
                f" {self.tenant_id!r}; the key an erasure approval must pin is the"
                " tenant's own (SEC-009; fix round 4, ruling 1)"
            )
        return self


class ErasureTrust(CCFContract):
    """The erasure authorities a store construction site composes with, one per tenant (SEC-009; `D-IMPL-374` (4), fix round 5, R4).

    ``authorities`` maps each tenant that may erase to its
    :class:`ErasureAuthority`; the mapping's key is the authority's own tenant.
    Empty is a declaration: this site verifies no erasure as supported, and
    every erased address its index names stays withheld, ``index-unsupported``.
    """

    authorities: Mapping[str, ErasureAuthority]

    @model_validator(mode="after")
    def _keyed_by_tenant(self) -> "ErasureTrust":
        for tenant, authority in self.authorities.items():
            if tenant != authority.tenant_id:
                raise ValueError(
                    f"the authority keyed {tenant!r} is tenant {authority.tenant_id!r}'s;"
                    " each tenant selects its own authority (SEC-009; fix round 5, R4)"
                )
        return self

    def authority_for(self, tenant_id: str) -> ErasureAuthority | None:
        """The authority ``tenant_id``'s erasures are verified against, or ``None`` (SEC-009; `D-IMPL-374` (4), R4)."""
        return self.authorities.get(tenant_id)


class ErasureRecordInvalid(ValueError):
    """An index entry whose record the consult cannot take as a door-signed, agreeing erasure (SEC-009; `D-IMPL-374` (4), fix round 5).

    ``reason_code`` names the judgment: ``erasure-tenant-undeclared`` (the
    composition declares no authority for the entry's tenant, R4),
    ``record-address-mismatch`` (the bytes read do not hash to the entry's
    record address), ``record-signature-invalid`` (no door signature verifies
    over those bytes under the tenant's declared door keys, R2), or
    ``record-entry-mismatch`` (the record does not carry what the entry says).
    """

    def __init__(self, detail: str, *, reason_code: str) -> None:
        super().__init__(detail)
        self.reason_code = reason_code


def _payload_member(payload: bytes) -> str:
    """The unpadded base64url payload member RFC 7515 §2 fixes, for the record's bytes."""
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def sign_erasure_record(record: ErasureRecord, *, signer: IdentityProvider, key_id: str) -> str:
    """The door's detached signature over ``record``'s canonical bytes (SEC-009; `D-IMPL-374` (4), fix round 5, R2).

    The provider signs ``canonical_bytes(record)`` — the bytes the store holds
    at the record's content address — and the protected header asserts
    :data:`DOOR_SIGNATURE_ASSERTION`. Returns ``protected..signature``.

    Raises:
        ccf.peering.identity.KeyUnavailable: ``signer`` holds no key ``key_id``.
    """
    envelope = signer.sign(
        product=record, key_id=key_id, assertions={DOOR_SIGNATURE_ASSERTION: ERASURE_RECORD_CLASS}
    )
    return f"{envelope.protected}{_DETACHED_SEPARATOR}{envelope.signature}"


def verify_door_signature(
    payload: bytes,
    *,
    door_signature: str,
    door_key_id: str,
    authority: ErasureAuthority,
    identity_provider: IdentityProvider,
) -> None:
    """Refuse unless ``door_signature`` is the door's signature over exactly ``payload`` (SEC-009; `D-IMPL-374` (4), fix round 5, R2).

    The header's key id must be ``door_key_id``, the signature must verify
    against the authority's declared door keys, and the protected header must
    assert that it signs an erasure record.

    Raises:
        ErasureRecordInvalid: ``record-signature-invalid``.
    """
    protected, separator, signature = door_signature.partition(_DETACHED_SEPARATOR)
    try:
        if not separator or not protected or not signature:
            raise ValueError("the door signature is not a detached compact JWS")
        envelope = SignedContextProduct(
            payload=_payload_member(payload), protected=protected, signature=signature
        )
        if envelope.declared_key_id() != door_key_id:
            raise ValueError("the signature's key id is not the one its entry names")
        identity_provider.verify(signed=envelope, public_keys=authority.door_keys)
        if envelope.declared_header().get(DOOR_SIGNATURE_ASSERTION) != ERASURE_RECORD_CLASS:
            raise ValueError("the signature does not assert that it signs an erasure record")
    except (IdentityError, ValueError) as invalid:
        raise ErasureRecordInvalid(
            "no signature by the erasure door's declared key verifies over this"
            f" record ({invalid}) (SEC-009; D-IMPL-374 (4), fix round 5, R2)"[:400],
            reason_code="record-signature-invalid",
        ) from invalid


def verify_erasure_entry(
    entry: ErasureIndexEntry,
    payload: bytes,
    *,
    trust: ErasureTrust,
    identity_provider: IdentityProvider,
) -> tuple[ErasureRecord, ErasureAuthority]:
    """The consult's judgment of an entry's RECORD, door signature first (SEC-009; `D-IMPL-374` (4), fix round 5).

    ``payload`` is what the store holds at ``entry.erasure_record_address``.
    In order: the entry's tenant selects its authority (R4); the bytes hash to
    the entry's record address; the door's signature verifies over them (R2) —
    before any field of the record is read; and the record carries every fact
    the entry does. Returns the record and the authority its approval is then
    verified against.

    Raises:
        ErasureRecordInvalid: any of those judgments, by its reason code.
    """
    authority = trust.authority_for(entry.tenant_id)
    if authority is None:
        raise ErasureRecordInvalid(
            f"this composition declares no erasure authority for tenant {entry.tenant_id!r}"
            " (SEC-009; D-IMPL-374 (4), fix round 5, R4)",
            reason_code="erasure-tenant-undeclared",
        )
    if hashlib.sha256(payload).hexdigest() != entry.erasure_record_address:
        raise ErasureRecordInvalid(
            "the bytes read do not hash to the entry's record address (SEC-009)",
            reason_code="record-address-mismatch",
        )
    verify_door_signature(
        payload,
        door_signature=entry.door_signature,
        door_key_id=entry.door_key_id,
        authority=authority,
        identity_provider=identity_provider,
    )
    record = ErasureRecord.model_validate_json(payload)
    agrees = (
        record.tenant_id == entry.tenant_id
        and record.request_id == entry.request_id
        and record.subject_class == entry.subject_class
        and record.subject_ref == entry.subject_ref
        and record.approval_ref == entry.approval_ref
        and record.reason == entry.reason
        and record.erased_at == entry.erased_at
        and entry.content_address in {a.content_address for a in record.addresses}
    )
    if not agrees:
        raise ErasureRecordInvalid(
            "the door-signed record does not carry what its index entry says (SEC-009; U7, N2)",
            reason_code="record-entry-mismatch",
        )
    return record, authority
