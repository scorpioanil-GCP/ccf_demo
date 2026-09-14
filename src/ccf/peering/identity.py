"""Agent identity and detached-JWS signing over canonical product bytes.

SDK-defined extension (CLAUDE.md §7.2 — "Identity and attestation"), attaching
to whitepaper §8.3 Pattern 4; D-IMPL-15 fixes the primitive as a detached JWS.

**What is signed is the content address's own preimage.** The payload is
:func:`ccf.contracts.canonical.canonical_bytes` of the product — byte for byte
the same input :func:`ccf.contracts.canonical.content_hash` digests. That
coupling is the point: a consumer that verifies the signature and recomputes
the content address has checked one artifact, not two, so there is no gap
between "the bytes a peer signed" and "the bytes the fabric will record".

**Detached, because the payload already travels.** A signature envelope that
carried a second copy of the product would let the two copies disagree, and
a verifier would then have to choose. :func:`joserfc.jws.detach_json_content`
yields exactly ``{"protected", "signature"}``; the payload rides beside it and
is reattached at verification. The detachment is the library's — hand-rolled
base64url slicing of a compact JWS is where verification bugs hide, and
D-13 makes this path load-bearing for admission.

**ES256, and not EdDSA.** ``joserfc`` refuses ``EdDSA`` by default with
``UnsupportedAlgorithmError``, and emits ``SecurityWarning: EdDSA is deprecated
via RFC 9864`` even when handed an explicit registry that permits it. ES256
(ECDSA on P-256) is verified working with no warning. This is recorded so a
later contributor does not read the choice as legacy and "modernize" it back.

Scope of what ships here, stated plainly (D-21):

* **Provided.** Genuine ES256 signing and verification over canonical bytes,
  a typed failure for each distinguishable way verification can fail, and a
  **file-backed, development-grade** key source behind a custody Protocol.
* **Not provided.** PKI, key rotation policy, hardware custody, or a trust
  store. Key custody at production grade is deployment infrastructure
  (CLAUDE.md §13), which is exactly why it is a Protocol here rather than an
  implementation. Channel security is out of v0 scope per D-13, so this module
  says nothing about how the bytes reached the verifier.

What this module does **not** decide is as load-bearing as what it does: it
holds no notion of which peer is trusted, which schema a peer may send, or
which key belongs to whom. Verification is handed the candidate public keys by
its caller; selecting them is :mod:`ccf.peering.trust_policy`'s job and the
admission gate's. A verifier that also resolved trust could admit a validly
signed product from a peer entitled to send nothing.

Algorithmic module (CINV-03): pure functions over typed inputs and a file read
for the dev key source; no LLM dependency, no transport, no graph handle.
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
from collections.abc import Iterable, Mapping
from typing import Any, Final, Protocol, runtime_checkable

from joserfc import jws
from joserfc.errors import JoseError
from joserfc.jwk import ECKey
from joserfc.jws import JWSRegistry, FlattenedJSONSerialization
from joserfc.registry import JWS_HEADER_REGISTRY, HeaderParameter

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash

__ccf_mode__ = "algorithmic"

__all__ = [
    "PRODUCT_SIGNATURE_TYPE",
    "SIGNING_ALGORITHM",
    "AlgorithmNotPermitted",
    "DetachedJwsIdentityProvider",
    "FileBackedKeySource",
    "IdentityError",
    "IdentityProvider",
    "JsonWebKey",
    "KeyUnavailable",
    "SignatureInvalid",
    "SignatureMalformed",
    "SignedContextProduct",
    "SigningKeySource",
    "UnknownSigningKey",
    "signed_product_address",
]

#: The one algorithm the reference provider signs and verifies with. A
#: mechanism constant, not a deployment value: see the module docstring for why
#: EdDSA is not an option here, and why a deployment that wants a different
#: curve substitutes an ``IdentityProvider``, not a config entry.
SIGNING_ALGORITHM = "ES256"

#: The ``typ`` claimed in the protected header. It names *what was signed* — a
#: canonical Context Product — so a signature over some other CCF artifact
#: cannot be replayed as a product signature.
PRODUCT_SIGNATURE_TYPE = "application/ccf-product+json"

#: A JWK as a plain mapping. Deliberately not a ``joserfc`` key type: the
#: custody seam and the trust-policy artifact both traffic in keys, and neither
#: should be pinned to this module's choice of JOSE library.
JsonWebKey = Mapping[str, str]


class IdentityError(Exception):
    """Base of the typed identity failures.

    Typed rather than bare because the admission gate's response differs per
    case: an unknown key identifier may mean a peer rotated and the trust
    policy has not been updated, whereas a bad signature means the bytes and
    the claim disagree. A gate that conflated them would log a forgery as a
    configuration lag.
    """


class UnknownSigningKey(IdentityError, LookupError):
    """The protected header names a key the verifier was not offered.

    Distinct from :class:`SignatureInvalid` on purpose: nothing was checked
    here, so this is not evidence about the payload either way.
    """


class SignatureInvalid(IdentityError):
    """The signature does not verify against the payload and the key.

    Covers both a tampered payload and a signature made by some other key —
    which are the same fact from the verifier's side, and are deliberately not
    reported as different ones: distinguishing them would require guessing at
    the producer's intent from a failed check.
    """


class AlgorithmNotPermitted(IdentityError):
    """The protected header declares an algorithm the verifier does not accept.

    The classic JWS elevation path is a header that renames the algorithm and a
    verifier that believes it. The declared algorithm is therefore checked
    against the verifier's own configured one before any key is used.
    """


class SignatureMalformed(IdentityError):
    """The envelope is not a well-formed detached JWS.

    Raised before verification is attempted, so a caller never reads "invalid
    signature" for input that carried no signature to check.
    """


class KeyUnavailable(IdentityError, LookupError):
    """A key source holds no key under the requested identifier."""


def _b64url(raw: bytes) -> str:
    """Base64url-encode ``raw`` without padding, per RFC 7515 §2.

    Used only to reattach a received payload to a detached envelope before
    handing the whole thing to :func:`joserfc.jws.deserialize_json`. It never
    constructs, splits, or parses a JWS — that is the library's job, and
    RFC 7515 fixes this encoding for the payload member regardless.
    """
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    """Reverse :func:`_b64url`, restoring the stripped padding.

    Raises:
        SignatureMalformed: ``text`` is not valid unpadded base64url.
    """
    padded = text + "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise SignatureMalformed(
            "envelope member is not valid base64url"
        ) from error


#: The largest protected header this build will sign or verify, in bytes.
#:
#: `D-IMPL-336` **R1**, and it was a BLOCKING defect rather than a tuning
#: question: ``joserfc``'s :class:`~joserfc.jws.JWSRegistry` defaults
#: ``max_header_length`` to **512** and ``_registry_declaring`` never set it,
#: so the peered composite path was **unreachable** — every honest envelope
#: carrying a child-eligibility assertion exceeded the cap and raised before
#: any CCF check ran. Measured on this tree: the encoded assertion is **448
#: bytes** and a complete protected header with ``alg``, ``kid``, a producer
#: assertion and that assertion is **621 bytes**.
#:
#: **This is a wire-format bound, not a domain value** — the same class as
#: ``joserfc``'s own 128000-byte payload cap, and it is declared here rather
#: than left to the library's default because the default was chosen for
#: envelopes that carry no CCF assertion. It is deliberately still a BOUND: an
#: unbounded header would let a peer force arbitrary allocation before its
#: signature is checked, and
#: ``test_an_oversized_protected_header_is_still_refused`` holds it to that.
#:
#: Derived, not picked: the header's variable members are the producer hash
#: (64 hex), one encoded eligibility assertion, and two URIs. 2048 leaves
#: roughly 3x headroom over the measured 621 for longer consumer scopes and
#: composition identities, while staying two orders of magnitude below the
#: payload cap.
MAX_PROTECTED_HEADER_BYTES: Final = 2048


def _registry_declaring(names: Iterable[str], *, algorithm: str) -> JWSRegistry:
    """Return a JWS registry that *declares* ``names`` as string headers.

    ``joserfc`` refuses an unregistered protected-header member outright, which
    is the correct default — an unknown header is usually a mistake or an
    injection. CCF's assertion members are therefore declared rather than
    smuggled past the check: the registry is built from exactly the members
    present, each typed as a string, and ``strict_check_header`` stays on. The
    alternative — disabling the check — would also admit whatever *else* an
    envelope happened to carry, which is the shape this parameter exists to
    prevent.
    """
    declared = dict(JWS_HEADER_REGISTRY)
    for name in names:
        if name not in declared:
            declared[name] = HeaderParameter(
                "CCF emitter assertion, covered by the signature", "str"
            )
    registry = JWSRegistry(header_registry=declared, algorithms=[algorithm])
    # `R1`. The library's 512-byte default is a class attribute and it made the
    # peered path unreachable; see MAX_PROTECTED_HEADER_BYTES. Set on the
    # INSTANCE, so no other joserfc user in this process is affected.
    registry.max_header_length = MAX_PROTECTED_HEADER_BYTES
    return registry


class SignedContextProduct(CCFContract):
    """A canonical Context Product together with its detached JWS.

    Three text members rather than one opaque blob, because the detachment is
    the contract: :func:`joserfc.jws.detach_json_content` yields exactly
    ``protected`` and ``signature``, and the payload travels separately. Modeled
    explicitly so a verifier that quietly accepted an embedded payload — the
    shape where a signed copy and a delivered copy can differ — does not
    typecheck.

    All three are base64url text so the contract is canonically serializable
    (the canonical form has no rendering for ``bytes``) and therefore itself
    content-addressable and auditable.

    Attributes:
        payload: Base64url of ``canonical_bytes(product)``.
        protected: The detached JWS protected header, base64url as signed.
        signature: The detached JWS signature, base64url.
    """

    payload: str
    protected: str
    signature: str

    def canonical_payload(self) -> bytes:
        """Return the canonical product bytes this envelope carries.

        Raises:
            SignatureMalformed: the payload member is not base64url.
        """
        return _b64url_decode(self.payload)

    def content_address(self) -> str:
        """Return the ``sha256`` content address of the carried product.

        Computable without verifying anything — it describes the bytes, not
        their provenance. The admission gate verifies *and* compares; this
        method exists so it can do the second half against the same bytes it
        did the first half against (D-IMPL-26).

        Raises:
            SignatureMalformed: the payload member is not base64url.
        """
        return hashlib.sha256(self.canonical_payload()).hexdigest()

    def declared_header(self) -> Mapping[str, Any]:
        """Return the decoded protected header.

        Unverified by construction — the header is read to *find* the key to
        verify with, so it cannot itself have been verified yet. Every claim in
        it is a claim until :meth:`IdentityProvider.verify` returns.

        Raises:
            SignatureMalformed: the header is not base64url JSON object.
        """
        try:
            decoded = json.loads(_b64url_decode(self.protected))
        except ValueError as error:
            raise SignatureMalformed(
                "protected header is not JSON"
            ) from error
        if not isinstance(decoded, dict):
            raise SignatureMalformed("protected header is not a JSON object")
        return decoded

    def declared_key_id(self) -> str:
        """Return the ``kid`` the protected header claims.

        This is the string the trust-policy artifact keys on, and it is a
        *claim*: it selects which public key to try, and is proven only by the
        signature verifying against that key.

        Raises:
            SignatureMalformed: the header carries no string ``kid``.
        """
        key_id = self.declared_header().get("kid")
        if not isinstance(key_id, str) or not key_id:
            raise SignatureMalformed("protected header declares no kid")
        return key_id


@runtime_checkable
class SigningKeySource(Protocol):
    """The custody seam: where a deployment's own private keys come from.

    A Protocol because custody is the deployment's infrastructure — an HSM, a
    cloud KMS, a mounted secret — and the SDK has no business choosing.
    :class:`FileBackedKeySource` is the development reference, not a
    recommendation.

    What the Protocol omits is deliberate: there is no peer key lookup here.
    A key source holds *this* deployment's signing material; other parties'
    public keys arrive through the trust-policy artifact, so a compromised or
    over-broad key source cannot silently become a trust store.

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.
    """

    def signing_key(self, *, key_id: str) -> JsonWebKey:
        """Return the private JWK registered under ``key_id``.

        Raises:
            KeyUnavailable: no key is held under that identifier.
        """
        ...

    def key_ids(self) -> tuple[str, ...]:
        """Return every key identifier this source can sign with."""
        ...


@runtime_checkable
class IdentityProvider(Protocol):
    """Signing and verification of Context Products (CLAUDE.md §7.2).

    D-IMPL-15. The surface is exactly what emission and admission need and
    nothing else: there is no transport, no L2 handle, and no graph handle on
    it, so identity stays a pure algorithmic concern that a wire cannot reach
    around. Verification takes its candidate public keys as an argument rather
    than resolving them, which is what keeps the trust decision outside this
    seam (see the module docstring).

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.
    """

    def sign(
        self,
        *,
        product: object,
        key_id: str,
        assertions: Mapping[str, str] | None = None,
    ) -> SignedContextProduct:
        """Sign ``product``'s canonical bytes with the key under ``key_id``.

        ``assertions`` are additional protected-header members the emitter
        claims alongside the product — the producer identity foremost. They go
        in the *protected* header, which is part of the JWS signing input, so
        an assertion is covered by the signature exactly as the payload is.
        That placement is what lets the admission gate hold a peer to what it
        asserted: an assertion carried outside the signature could be rewritten
        in flight by anyone, and a governance check against a rewritable claim
        checks nothing (:mod:`ccf.peering.admission`).

        Raises:
            KeyUnavailable: the key source holds no such key.
            ValueError: an assertion would overwrite ``alg``, ``kid``, or
                ``typ`` — the members that establish *how* and *by whom* the
                envelope was signed are the provider's to state, never the
                caller's.
            ccf.contracts.canonical.CanonicalizationError: the product has no
                canonical form, and therefore nothing stable to sign.
        """
        ...

    def verify(
        self,
        *,
        signed: SignedContextProduct,
        public_keys: Mapping[str, JsonWebKey],
    ) -> bytes:
        """Return the verified payload bytes of ``signed``.

        ``public_keys`` maps key identifier to public JWK — the set the caller
        is willing to accept for this product, typically one peer's entry from
        the trust-policy artifact.

        Raises:
            SignatureMalformed: the envelope is not a well-formed detached JWS.
            AlgorithmNotPermitted: the header declares another algorithm.
            UnknownSigningKey: the declared ``kid`` is not in ``public_keys``.
            SignatureInvalid: the signature does not verify.
        """
        ...


class FileBackedKeySource:
    """A development key source reading JWKs from a directory.

    **Development-grade, and stated as such.** It offers no encryption at rest,
    no rotation, no access control, and no audit of key use — it reads files.
    It exists so the signing path is exercisable end to end without standing up
    custody infrastructure, and so :class:`SigningKeySource` ships with a
    working implementation like every other Protocol in the SDK. Production
    custody is deployment infrastructure (CLAUDE.md §13).

    Each key is one JSON file named ``{key_id}.jwk`` in ``directory``. No key
    material, and no key identifier, is baked into this class: which keys exist
    is the deployment's statement (CINV-01).

    Args:
        directory: Where the JWK files live.
    """

    #: Filename suffix of a key document in the directory.
    SUFFIX = ".jwk"

    def __init__(self, *, directory: pathlib.Path) -> None:
        self._directory = directory

    def signing_key(self, *, key_id: str) -> JsonWebKey:
        """Return the private JWK stored as ``{key_id}.jwk``.

        Raises:
            KeyUnavailable: no such file, or its content is not a JWK object.
        """
        path = self._directory / f"{key_id}{self.SUFFIX}"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise KeyUnavailable(
                f"no signing key is held under {key_id!r}"
            ) from error
        except ValueError as error:
            raise KeyUnavailable(
                f"the key document for {key_id!r} is not JSON"
            ) from error
        if not isinstance(document, dict) or not all(
            isinstance(value, str) for value in document.values()
        ):
            raise KeyUnavailable(
                f"the key document for {key_id!r} is not a JWK object"
            )
        return document

    def key_ids(self) -> tuple[str, ...]:
        """Return every key identifier present in the directory, sorted."""
        if not self._directory.is_dir():
            return ()
        return tuple(
            sorted(
                path.name[: -len(self.SUFFIX)]
                for path in self._directory.iterdir()
                if path.name.endswith(self.SUFFIX)
            )
        )


class DetachedJwsIdentityProvider:
    """The reference :class:`IdentityProvider`: detached JWS, ES256.

    CLAUDE.md §7.2; D-IMPL-15. See the module docstring for the algorithm
    choice, the detachment, and the boundary of what "provided" means.

    Args:
        key_source: Where private signing material comes from.
        algorithm: The one algorithm accepted on both paths. Defaults to
            :data:`SIGNING_ALGORITHM`; a deployment substituting it is
            declaring a different interoperability profile, so it is a
            constructor argument rather than a lookup at use.
    """

    def __init__(
        self,
        *,
        key_source: SigningKeySource,
        algorithm: str = SIGNING_ALGORITHM,
    ) -> None:
        self._key_source = key_source
        self._algorithm = algorithm

    @property
    def algorithm(self) -> str:
        """The algorithm this provider signs with and accepts."""
        return self._algorithm

    def sign(
        self,
        *,
        product: object,
        key_id: str,
        assertions: Mapping[str, str] | None = None,
    ) -> SignedContextProduct:
        """Sign ``product``'s canonical bytes; see :meth:`IdentityProvider.sign`.

        Raises:
            KeyUnavailable: the key source holds no such key, or holds one that
                is not a usable EC key.
            ValueError: an assertion collides with a reserved header member.
            ccf.contracts.canonical.CanonicalizationError: the product has no
                canonical form.
        """
        payload = canonical_bytes(product)
        private = self._import_key(self._key_source.signing_key(key_id=key_id))
        header: dict[str, str] = {
            "alg": self._algorithm,
            "kid": key_id,
            "typ": PRODUCT_SIGNATURE_TYPE,
        }
        for name, claim in (assertions or {}).items():
            if name in header:
                raise ValueError(
                    f"assertion {name!r} would overwrite the reserved protected"
                    " header member of the same name"
                )
            header[name] = claim
        # One header member, so joserfc's overloads resolve this to the RFC 7515
        # *flattened* JSON serialization — which is what makes the detachment
        # call below typed rather than a cast.
        envelope = jws.serialize_json(
            {"protected": header},
            payload,
            private,
            registry=_registry_declaring(header, algorithm=self._algorithm),
        )
        # `jws.detach_content` is the library's exported entry point; for a
        # JSON serialization it dispatches straight to `detach_json_content`
        # (joserfc/jws.py). Called through the export rather than reaching into
        # `joserfc._rfc7515.json`, because `detach_json_content` is not in
        # `joserfc.jws.__all__` and a private import would be a typed hole. The
        # detachment is still entirely the library's — nothing here slices
        # base64url.
        detached = jws.detach_content(envelope)
        protected = detached.get("protected")
        signature = detached.get("signature")
        if not isinstance(protected, str) or not isinstance(signature, str):
            # Unreachable against joserfc 1.7.4, which returns exactly these
            # two members; asserted rather than assumed because a silently
            # reshaped envelope would produce signatures nothing can verify.
            raise SignatureMalformed(
                "detached envelope did not carry protected and signature"
            )
        return SignedContextProduct(
            payload=_b64url(payload),
            protected=protected,
            signature=signature,
        )

    def verify(
        self,
        *,
        signed: SignedContextProduct,
        public_keys: Mapping[str, JsonWebKey],
    ) -> bytes:
        """Return the verified payload; see :meth:`IdentityProvider.verify`."""
        header = signed.declared_header()
        declared_algorithm = header.get("alg")
        if declared_algorithm != self._algorithm:
            raise AlgorithmNotPermitted(
                f"envelope declares alg {declared_algorithm!r};"
                f" this verifier accepts {self._algorithm!r} only"
            )
        key_id = signed.declared_key_id()
        if key_id not in public_keys:
            raise UnknownSigningKey(
                f"no public key was offered for kid {key_id!r}"
            )
        public = self._import_key(public_keys[key_id])
        payload = signed.canonical_payload()
        # Reattachment is the one place a payload is re-encoded, and RFC 7515
        # §2 fixes that encoding for the payload member. Everything structural
        # about the JWS — header parsing, signing input assembly, signature
        # checking — stays inside the library.
        reattached: FlattenedJSONSerialization = {
            "protected": signed.protected,
            "signature": signed.signature,
            "payload": _b64url(payload),
        }
        try:
            verified = jws.deserialize_json(
                reattached,
                public,
                registry=_registry_declaring(
                    header, algorithm=self._algorithm
                ),
            )
        except JoseError as error:
            raise SignatureInvalid(
                f"signature does not verify for kid {key_id!r}"
            ) from error
        return bytes(verified.payload)

    @staticmethod
    def _import_key(document: JsonWebKey) -> ECKey:
        """Import a JWK mapping as an EC key.

        Raises:
            KeyUnavailable: the document is not an importable EC JWK. Reported
                as a custody failure rather than a signature failure — nothing
                about a payload has been observed at this point.
        """
        try:
            return ECKey.import_key(dict(document))
        except (JoseError, ValueError) as error:
            raise KeyUnavailable(
                "key document is not an importable EC JWK"
            ) from error


def signed_product_address(product: object) -> str:
    """Return the content address a signed envelope for ``product`` will carry.

    Exposed so a producer can record the address it is about to sign without
    re-deriving the canonical form, and so the coupling asserted in the module
    docstring — signature payload *is* content-address preimage — has one
    callable statement rather than a convention.

    Raises:
        ccf.contracts.canonical.CanonicalizationError: no canonical form.
    """
    return content_hash(product)
