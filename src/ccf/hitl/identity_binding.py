"""JWS-signed HITL action claims: D-IMPL-21 reference implementation #2, as `D-IMPL-363` reshaped it.

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so). D-IMPL-21 rules that HITL identity binding is pluggable via the
same ``IdentityProvider`` family as D-IMPL-15; D-IMPL-66(a) commits a second
reference implementation with **cryptographic non-repudiation**. `D-IMPL-363`
(SEC-005, the remaining leg) moved WHAT is signed: no longer the door-minted
:class:`~ccf.hitl.principal.HumanPrincipalBinding` — whose ``action_time`` the
door stamps from its own clock, so a signer had to predict the server's clock
reading and the signed leg could not work under a wall clock (the limit
recorded at ``docs/surface-changes/353-06-the-approval-record-is-server-attested.md``)
— but a distinct, signer-stated claim set, :class:`HitlActionClaims`, carried
as :class:`SignedHitlAction`. The binding stays door-minted and unsigned; the
verifier (:func:`ccf.hitl.transport.enforce_attestation`) compares each claim
to the capability and to the minted binding, and windows the signer's
``issued_at`` against the RECORDED ``action_time`` without reading a clock of
its own.

**Machinery reuse, not reimplementation.** Signing and verification are
delegated entirely to :mod:`ccf.peering.identity` (D-IMPL-15): the payload
is :func:`ccf.contracts.canonical.canonical_bytes` of the claims — the same
canonical serializer the content address digests, which already refuses
naive datetimes (D-IMPL-38) — and the envelope is the provider's own
detached JWS. This module holds no key machinery, no JOSE registry, and no
algorithm choice of its own: which keys exist and which provider signs are
the deployment's statements (CINV-01).

**Trust stays outside the seam**, exactly as it does for products:
verification takes its candidate public keys from the caller, mirroring
:meth:`ccf.peering.identity.IdentityProvider.verify`. Under `D-IMPL-363` E5 /
C6(a) the caller is the shared verifier, and the keys it offers are the
pinned :class:`~ccf.hitl.transport.HitlPolicy`'s per-subject map — one trust
source, never a constructor fallback.

**Replaced, not deprecated** (`D-IMPL-356` §0 ruling 4; "nothing has
shipped"): ``SignedPrincipalBinding``, ``sign_principal_binding``,
``verify_principal_binding`` and ``PrincipalBindingInvalid`` are gone from
this module; nothing on the replay path ever re-parsed a stored signed
binding, so every historical record rehydrates unchanged.

Algorithmic module (CINV-03): pure functions over typed inputs; no LLM
dependency, no transport, no graph handle.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import datetime

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.hitl.principal import validate_content_hash
from ccf.peering.identity import (
    IdentityError,
    IdentityProvider,
    JsonWebKey,
    SignedContextProduct,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "AttestationInvalid",
    "HitlActionClaims",
    "SignedHitlAction",
    "sign_hitl_action",
    "verify_hitl_action",
]

#: The separator of a detached compact JWS (RFC 7515 Appendix F): the
#: payload member is absent, so ``protected`` and ``signature`` abut across
#: two dots. Used only to join and split the two members the provider's
#: detached envelope carries — no base64url is sliced here.
_DETACHED_SEPARATOR = ".."


class AttestationInvalid(IdentityError):
    """The signed attestation does not verify (D-IMPL-21; D-IMPL-363; CLAUDE.md §8.2).

    SDK-defined. Raised for every distinguishable identity failure —
    tampered claims, unknown key, malformed envelope, wrong algorithm —
    with the underlying :mod:`ccf.peering.identity` error chained as the
    cause, so an audit consumer can distinguish a forgery from a
    configuration lag without this module re-deciding which is which.
    """


class HitlActionClaims(CCFContract):
    """What the human states and signs about ONE action (D-IMPL-363 E1).

    SDK-defined. Every member is something the signer can know from the
    served queue view (:class:`~ccf.hitl.transport.PendingHitlEvent`:
    ``event_key``, ``tenant``, ``product_content_hash``) plus its own
    decision, identity, instant and nonce — and nothing the door mints.
    ``action_time`` is deliberately absent: it is the door's statement,
    recorded on the unsigned binding, and the window
    :func:`~ccf.hitl.transport.enforce_attestation` applies compares
    ``issued_at`` against it (E2, E3).

    Attributes:
        tenant: The tenant the action is filed under; must equal the
            capability's tenant at verification.
        event_key: The pending event acted on; must equal the capability's
            resource.
        action: The verdict (the :data:`~ccf.hitl.transport.HITL_ACTIONS`
            vocabulary); must equal the presented action and the minted
            binding's ``verdict`` (C1(a)).
        product_content_hash: The content hash of what the human saw; must
            equal the minted binding's.
        subject_id: Who signs; must equal the capability's principal and the
            minted binding's approver.
        issued_at: The signer's own instant — timezone-aware, refused naive.
        nonce: Non-empty and opaque. **Uniqueness per ``(tenant, event_key)``
            is the signer's obligation** (C11(a)); the reference transport
            refuses a reuse atomically. Neither length nor format is relied
            on for that guarantee, and the SDK ships no generator (CINV-01).
    """

    tenant: str
    event_key: str
    action: str
    product_content_hash: str
    subject_id: str
    issued_at: datetime
    nonce: str

    @field_validator("tenant", "event_key", "subject_id", "nonce")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("a signed HITL claim cannot be empty (D-IMPL-363)")
        return value

    @field_validator("action")
    @classmethod
    def _action_is_known(cls, value: str) -> str:
        # Imported here, not at module level: ``ccf.hitl.transport`` imports
        # this module for the claim types, and the vocabulary lives there.
        from ccf.hitl.transport import HITL_ACTIONS

        if value not in HITL_ACTIONS:
            raise ValueError(
                f"unknown HITL action {value!r}; the typed queue carries"
                f" {sorted(HITL_ACTIONS)} (D-IMPL-20)"
            )
        return value

    @field_validator("product_content_hash")
    @classmethod
    def _product_hash_is_a_content_hash(cls, value: str) -> str:
        return validate_content_hash(value)

    @field_validator("issued_at")
    @classmethod
    def _issued_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "issued_at must be timezone-aware: the freshness window is"
                " judged against the recorded door instant, and a naive"
                " instant would be compared in whatever zone the reader"
                " assumed (D-IMPL-38; D-IMPL-363 C7)"
            )
        return value


class SignedHitlAction(CCFContract):
    """The claims together with their detached JWS (D-IMPL-21; D-IMPL-363 E1).

    SDK-defined (CLAUDE.md §8.2); D-IMPL-66(a). The claims travel in the
    clear — audit consumers read them without keys — and the signature is the
    detached compact JWS (``protected..signature``) exactly as
    :mod:`ccf.peering.identity` produced it over the claims' canonical
    bytes. A verifier recomputes those bytes from :attr:`claims`, so a
    signed copy and a delivered copy cannot silently differ. This is the
    ``attestation`` a :class:`~ccf.hitl.transport.HitlActionRequest` and a
    :class:`~ccf.hitl.transport.HitlActionSubmission` carry, at both doors
    in one shape (C12(a)).

    Attributes:
        claims: The signed claim set.
        signature: The detached compact JWS, ``{protected}..{signature}``.
        key_id: The key identifier the signature was made under — the
            claim the verifier holds against the protected header's ``kid``
            and against the pinned policy's per-subject key map (E5).
    """

    claims: HitlActionClaims
    signature: str
    key_id: str


def sign_hitl_action(
    claims: HitlActionClaims,
    *,
    provider: IdentityProvider,
    key_id: str,
) -> SignedHitlAction:
    """Sign ``claims``' canonical bytes with the key under ``key_id``.

    D-IMPL-21 reference impl #2 (SDK-defined; CLAUDE.md §8.2). Delegates to
    the D-IMPL-15 provider: the payload is ``canonical_bytes(claims)``, the
    same bytes the content address digests, so there is exactly one
    serialization of the claims in play (D-IMPL-38/26).

    Raises:
        ccf.peering.identity.KeyUnavailable: the key source holds no such key.
        ccf.contracts.canonical.CanonicalizationError: the claims have no
            canonical form.
    """
    envelope = provider.sign(product=claims, key_id=key_id)
    return SignedHitlAction(
        claims=claims,
        signature=(
            f"{envelope.protected}{_DETACHED_SEPARATOR}{envelope.signature}"
        ),
        key_id=key_id,
    )


def verify_hitl_action(
    signed: SignedHitlAction,
    *,
    provider: IdentityProvider,
    public_keys: Mapping[str, JsonWebKey],
) -> HitlActionClaims:
    """Return the verified claims, or raise :class:`AttestationInvalid`.

    The payload verified is recomputed from ``signed.claims`` — claims whose
    verdict, subject or instant were substituted after signing therefore
    fail signature verification, which is the non-repudiation property
    D-IMPL-66(a) exists for. ``public_keys`` is the set the caller is willing
    to accept, mirroring :meth:`ccf.peering.identity.IdentityProvider.verify`:
    trust resolution stays outside this seam — the shared verifier offers the
    pinned policy's keys for ``claims.subject_id`` and nothing wider (E5).

    Raises:
        AttestationInvalid: the envelope is malformed, the declared key
            differs from :attr:`SignedHitlAction.key_id`, the key is not
            offered, or the signature does not verify — each with the
            underlying typed identity error chained as the cause.
    """
    protected, separator, signature = signed.signature.partition(
        _DETACHED_SEPARATOR
    )
    if not separator or not protected or not signature:
        raise AttestationInvalid(
            "signature is not a detached compact JWS"
            " (expected protected..signature)"
        )
    envelope = SignedContextProduct(
        payload=_encode_payload(signed.claims),
        protected=protected,
        signature=signature,
    )
    try:
        declared_key_id = envelope.declared_key_id()
        if declared_key_id != signed.key_id:
            raise AttestationInvalid(
                f"envelope declares kid {declared_key_id!r} but the"
                f" attestation claims key_id {signed.key_id!r}"
            )
        provider.verify(signed=envelope, public_keys=public_keys)
    except AttestationInvalid:
        raise
    except (IdentityError, ValueError) as error:
        raise AttestationInvalid(
            "signed HITL attestation does not verify"
        ) from error
    return signed.claims


def _encode_payload(claims: HitlActionClaims) -> str:
    """Return the base64url payload member for ``claims``' canonical bytes.

    Encoded through the same contract surface the provider emits
    (:class:`ccf.peering.identity.SignedContextProduct` round-trips its
    payload as unpadded base64url per RFC 7515 §2), via the stdlib —
    no JWS structure is assembled here.
    """
    return (
        base64.urlsafe_b64encode(canonical_bytes(claims))
        .rstrip(b"=")
        .decode("ascii")
    )
