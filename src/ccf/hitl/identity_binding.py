"""JWS-signed principal binding: D-IMPL-21 reference implementation #2.

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so). D-IMPL-21 rules that HITL identity binding is pluggable via the
same ``IdentityProvider`` family as D-IMPL-15; D-IMPL-66(a) commits a second
reference implementation with **cryptographic non-repudiation**: a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` signed as a detached JWS
over its canonical bytes, so that a caller-supplied approver identity cannot
be silently substituted after the fact — post-hoc tampering is detectable at
:func:`verify_principal_binding`, not merely discouraged by convention.

**Machinery reuse, not reimplementation.** Signing and verification are
delegated entirely to :mod:`ccf.peering.identity` (D-IMPL-15): the payload
is :func:`ccf.contracts.canonical.canonical_bytes` of the binding — the same
canonical serializer the content address digests, which already refuses
naive datetimes (D-IMPL-38) — and the envelope is the provider's own
detached JWS. This module holds no key machinery, no JOSE registry, and no
algorithm choice of its own: which keys exist and which provider signs are
the deployment's statements (CINV-01).

**Trust stays outside the seam**, exactly as it does for products:
verification takes its candidate public keys from the caller, mirroring
:meth:`ccf.peering.identity.IdentityProvider.verify` — a verifier that also
resolved trust could accept a validly signed binding from a key entitled to
bind nothing.

Algorithmic module (CINV-03): pure functions over typed inputs; no LLM
dependency, no transport, no graph handle.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.peering.identity import (
    IdentityError,
    IdentityProvider,
    JsonWebKey,
    SignedContextProduct,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "PrincipalBindingInvalid",
    "SignedPrincipalBinding",
    "sign_principal_binding",
    "verify_principal_binding",
]

#: The separator of a detached compact JWS (RFC 7515 Appendix F): the
#: payload member is absent, so ``protected`` and ``signature`` abut across
#: two dots. Used only to join and split the two members the provider's
#: detached envelope carries — no base64url is sliced here.
_DETACHED_SEPARATOR = ".."


class PrincipalBindingInvalid(IdentityError):
    """The signed binding does not verify (D-IMPL-21; CLAUDE.md §8.2).

    SDK-defined. Raised for every distinguishable identity failure —
    tampered binding, unknown key, malformed envelope, wrong algorithm —
    with the underlying :mod:`ccf.peering.identity` error chained as the
    cause, so an audit consumer can distinguish a forgery from a
    configuration lag without this module re-deciding which is which.
    """


class SignedPrincipalBinding(CCFContract):
    """A principal binding together with its detached JWS (D-IMPL-21).

    SDK-defined (CLAUDE.md §8.2); D-IMPL-66(a). The binding travels in the
    clear — audit consumers read it without keys — and the signature is the
    detached compact JWS (``protected..signature``) exactly as
    :mod:`ccf.peering.identity` produced it over the binding's canonical
    bytes. A verifier recomputes those bytes from :attr:`binding`, so a
    signed copy and a delivered copy cannot silently differ.

    Attributes:
        binding: The human-principal binding that was signed.
        signature: The detached compact JWS, ``{protected}..{signature}``.
        key_id: The key identifier the signature was made under — the
            claim the verifier holds against the protected header's ``kid``.
    """

    binding: HumanPrincipalBinding
    signature: str
    key_id: str


def sign_principal_binding(
    binding: HumanPrincipalBinding,
    *,
    provider: IdentityProvider,
    key_id: str,
) -> SignedPrincipalBinding:
    """Sign ``binding``'s canonical bytes with the key under ``key_id``.

    D-IMPL-21 reference impl #2 (SDK-defined; CLAUDE.md §8.2). Delegates to
    the D-IMPL-15 provider: the payload is ``canonical_bytes(binding)``, the
    same bytes the content address digests, so there is exactly one
    serialization of the binding in play (D-IMPL-38/26).

    Raises:
        ccf.peering.identity.KeyUnavailable: the key source holds no such key.
        ccf.contracts.canonical.CanonicalizationError: the binding has no
            canonical form.
    """
    envelope = provider.sign(product=binding, key_id=key_id)
    return SignedPrincipalBinding(
        binding=binding,
        signature=(
            f"{envelope.protected}{_DETACHED_SEPARATOR}{envelope.signature}"
        ),
        key_id=key_id,
    )


def verify_principal_binding(
    signed: SignedPrincipalBinding,
    *,
    provider: IdentityProvider,
    public_keys: Mapping[str, JsonWebKey],
) -> HumanPrincipalBinding:
    """Return the verified binding, or raise :class:`PrincipalBindingInvalid`.

    The payload verified is recomputed from ``signed.binding`` — a binding
    whose approver was substituted after signing therefore fails signature
    verification, which is the non-repudiation property D-IMPL-66(a) exists
    for. ``public_keys`` is the set the caller is willing to accept,
    mirroring :meth:`ccf.peering.identity.IdentityProvider.verify`: trust
    resolution stays outside this seam.

    Raises:
        PrincipalBindingInvalid: the envelope is malformed, the declared key
            differs from :attr:`SignedPrincipalBinding.key_id`, the key is
            not offered, or the signature does not verify — each with the
            underlying typed identity error chained as the cause.
    """
    protected, separator, signature = signed.signature.partition(
        _DETACHED_SEPARATOR
    )
    if not separator or not protected or not signature:
        raise PrincipalBindingInvalid(
            "signature is not a detached compact JWS"
            " (expected protected..signature)"
        )
    envelope = SignedContextProduct(
        payload=_encode_payload(signed.binding),
        protected=protected,
        signature=signature,
    )
    try:
        declared_key_id = envelope.declared_key_id()
        if declared_key_id != signed.key_id:
            raise PrincipalBindingInvalid(
                f"envelope declares kid {declared_key_id!r} but the binding"
                f" claims key_id {signed.key_id!r}"
            )
        provider.verify(signed=envelope, public_keys=public_keys)
    except PrincipalBindingInvalid:
        raise
    except (IdentityError, ValueError) as error:
        raise PrincipalBindingInvalid(
            "signed principal binding does not verify"
        ) from error
    return signed.binding


def _encode_payload(binding: HumanPrincipalBinding) -> str:
    """Return the base64url payload member for ``binding``'s canonical bytes.

    Encoded through the same contract surface the provider emits
    (:class:`ccf.peering.identity.SignedContextProduct` round-trips its
    payload as unpadded base64url per RFC 7515 §2), via the stdlib —
    no JWS structure is assembled here.
    """
    return (
        base64.urlsafe_b64encode(canonical_bytes(binding))
        .rstrip(b"=")
        .decode("ascii")
    )
