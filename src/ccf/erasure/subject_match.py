# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The erasure door's subject match, judged where the bytes are (SEC-009; `D-IMPL-378`, Dave's 16:40 MST item 5 — D3b).

SDK-defined (CLAUDE.md §7.4, §8.2). The erasure door verifies every address a
request names: the stored bytes hash to the address, they parse, a value at one
of the subject class's declared key paths hashes to the request's salted
``subject_ref`` — and where the subject also sits in a replay-input field of a
record the fabric's record writer filed, the request is refused
``replay-input`` (``runtime/ccf_runtime/erasure/door.py::ErasureDoor._verify_addresses``).
This module holds that judgment once, so every place that makes it makes it the
same way:

* :func:`judge_subject` — the judgment over stored bytes. The in-process door
  applies it to the bytes it reads; the MCP artifact server applies it, for the
  erasure door alone, to client-lane bytes it does not serve
  (``runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server``, tool
  ``match_artifact_subject``), so the door over the MCP-backed store reaches the
  in-process door's outcome without the bytes crossing.
* :class:`SubjectMatchQuery` — what the door asks: its tenant, the address, the
  salted reference, and the subject class's declared key paths and salt — and
  :class:`SubjectMatchAnswer`, the one verdict it gets back. Never the bytes,
  never the document, never a value read out of it.
* :func:`sign_subject_match_query` / :func:`verify_subject_match_query` — the
  door's detached signature over a query, by the door key its tenant's
  :class:`~ccf.erasure.ErasureAuthority` declares, asserting
  :data:`SUBJECT_MATCH_CLASS` in the protected header. Domain-separated: a
  door-key signature made for an erasure record or for the door's composition
  probe does not verify as a query, and a query's signature does not verify as
  a record's (:func:`~ccf.erasure.verify_door_signature` requires the record
  class). The query names its tenant, so a signature for one tenant's query is
  no signature for another's, even under a shared door key.

**The verdict is the door's own vocabulary, coarsened on the wire.**
:data:`SubjectJudgment` tells bytes that do not hash to the address from bytes
that do not parse, because the in-process door's refusal messages do;
:data:`SubjectMatchVerdict` folds both into ``subject-unverifiable``, the
door's refusal code for either.

**What this does not do.** It reads no store, decides no record provenance (the
door asks :func:`~ccf.replay.provenance.filed_by_record_writer` itself when the
judgment is ``subject-in-replay-input``), and holds no key: signing is the
door's, verifying is the server's, against keys the deployment declared at
composition. A signature is as strong as the custody of the door's private key
— the same key the door signs its erasure records with.

Algorithmic module (CINV-03): pure functions over typed inputs; no clock.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Final, Literal

from pydantic import Field, field_validator

from ccf.artifacts.protocol import CONTENT_ADDRESS_PATTERN
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.erasure.contracts import REPLAY_INPUT_PATHS
from ccf.erasure.trust import DOOR_SIGNATURE_ASSERTION, ErasureAuthority
from ccf.peering.identity import IdentityError, IdentityProvider, SignedContextProduct

__ccf_mode__ = "algorithmic"

__all__ = [
    "SUBJECT_MATCH_CLASS",
    "SubjectJudgment",
    "SubjectMatchAnswer",
    "SubjectMatchQuery",
    "SubjectMatchSignatureInvalid",
    "SubjectMatchVerdict",
    "judge_subject",
    "sign_subject_match_query",
    "subject_match_verdict",
    "verify_subject_match_query",
]

#: What a subject-match query's signature asserts in its protected header,
#: under :data:`~ccf.erasure.DOOR_SIGNATURE_ASSERTION`: the signature is FOR a
#: subject-match query, never a record or a probe (domain separation).
SUBJECT_MATCH_CLASS: Final[str] = "ccf.erasure-subject-match"

#: The judgment over stored bytes, in the order it is made.
SubjectJudgment = Literal[
    "bytes-not-at-address",
    "bytes-unparseable",
    "subject-not-found",
    "subject-in-replay-input",
    "subject-found",
]

#: The one answer the server gives the door: ``subject-unverifiable`` for bytes
#: that do not hash to the address or do not parse, and for every address the
#: server does not judge.
SubjectMatchVerdict = Literal[
    "subject-unverifiable",
    "subject-not-found",
    "subject-in-replay-input",
    "subject-found",
]

#: The separator of a detached compact JWS (RFC 7515 Appendix F).
_DETACHED_SEPARATOR: Final[str] = ".."


class SubjectMatchQuery(CCFContract):
    """What the erasure door asks about one requested address (SEC-009; `D-IMPL-378`, D3b).

    Attributes:
        tenant_id: The door's tenant. On the server it is the caller's verified
            tenant, never a wire value, so a signature over one tenant's query
            does not cover another's.
        content_address: The requested address.
        subject_ref: The request's salted subject reference (sha256 hex).
        key_paths: The subject class's declared key paths (its declaration
            already refuses a path that reaches a replay input).
        subject_ref_salt: The subject class's declared salt.
    """

    tenant_id: str = Field(min_length=1)
    content_address: str
    subject_ref: str
    key_paths: tuple[str, ...] = Field(min_length=1)
    subject_ref_salt: str = Field(min_length=1)

    @field_validator("content_address", "subject_ref")
    @classmethod
    def _is_a_sha256_digest(cls, value: str) -> str:
        if not CONTENT_ADDRESS_PATTERN.match(value):
            raise ValueError("an address and a salted subject reference are sha256 hex digests (SEC-009)")
        return value

    @field_validator("key_paths")
    @classmethod
    def _non_empty_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not path for path in value):
            raise ValueError("a subject key path is non-empty (SEC-009)")
        return value


class SubjectMatchAnswer(CCFContract):
    """The server's whole answer to the door's subject match: one verdict (SEC-009; `D-IMPL-378`, D3b)."""

    verdict: SubjectMatchVerdict


class SubjectMatchSignatureInvalid(ValueError):
    """No signature by the declared door key of the query's tenant verifies over exactly this query (D3b)."""


def _values_at(document: object, path: str) -> tuple[str, ...]:
    """The scalar value(s) at a dotted path — a list contributes its scalar members."""
    node = document
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return ()
        node = node[part]
    members = node if isinstance(node, list) else [node]
    return tuple(str(m) for m in members if isinstance(m, (str, int)) and not isinstance(m, bool))


def _hashes_to(salt: str, values: tuple[str, ...], subject_ref: str) -> bool:
    for value in values:
        material = salt.encode("utf-8") + b"\x00" + value.encode("utf-8")
        if hashlib.sha256(material).hexdigest() == subject_ref:
            return True
    return False


def _carries(document: object, paths: tuple[str, ...], query: SubjectMatchQuery) -> bool:
    return any(_hashes_to(query.subject_ref_salt, _values_at(document, path), query.subject_ref) for path in paths)


def judge_subject(payload: bytes, query: SubjectMatchQuery) -> SubjectJudgment:
    """Judge the bytes stored at ``query.content_address`` — the erasure door's judgment, in its order (D3b).

    Byte fidelity FIRST (Dave's E1 (a), ``D-IMPL-378``; ``D-IMPL-89``): bytes
    that do not hash to the address are not the artifact it names, and nothing
    is judged from them. Then they must parse; then a value at a declared key
    path must hash to the salted reference; then whether the subject also sits
    in a replay-input field (:data:`~ccf.erasure.REPLAY_INPUT_PATHS`).
    """
    if hashlib.sha256(payload).hexdigest() != query.content_address:
        return "bytes-not-at-address"
    try:
        document = json.loads(payload)
    except (ValueError, RecursionError):
        return "bytes-unparseable"
    if not _carries(document, query.key_paths, query):
        return "subject-not-found"
    if _carries(document, REPLAY_INPUT_PATHS, query):
        return "subject-in-replay-input"
    return "subject-found"


def subject_match_verdict(judgment: SubjectJudgment) -> SubjectMatchVerdict:
    """The wire verdict for ``judgment``: bytes not at the address, or unparseable, are ``subject-unverifiable``."""
    if judgment == "subject-not-found":
        return "subject-not-found"
    if judgment == "subject-in-replay-input":
        return "subject-in-replay-input"
    if judgment == "subject-found":
        return "subject-found"
    return "subject-unverifiable"


def sign_subject_match_query(query: SubjectMatchQuery, *, signer: IdentityProvider, key_id: str) -> str:
    """The erasure door's detached signature over ``query``'s canonical bytes (D3b). Returns ``protected..signature``.

    Raises:
        ccf.peering.identity.KeyUnavailable: ``signer`` holds no key ``key_id``.
    """
    envelope = signer.sign(product=query, key_id=key_id, assertions={DOOR_SIGNATURE_ASSERTION: SUBJECT_MATCH_CLASS})
    return f"{envelope.protected}{_DETACHED_SEPARATOR}{envelope.signature}"


def verify_subject_match_query(
    query: SubjectMatchQuery,
    *,
    door_signature: str,
    authority: ErasureAuthority,
    identity_provider: IdentityProvider,
) -> None:
    """Refuse unless ``door_signature`` is the door's signature over exactly ``query`` (D3b).

    ``authority`` must be the query's tenant's; the signature must verify over
    the query's canonical bytes against the authority's declared door keys, and
    its protected header must assert :data:`SUBJECT_MATCH_CLASS`.

    Raises:
        SubjectMatchSignatureInvalid: any of those.
    """
    protected, separator, signature = door_signature.partition(_DETACHED_SEPARATOR)
    try:
        if authority.tenant_id != query.tenant_id:
            raise ValueError("the authority is another tenant's")
        if not separator or not protected or not signature:
            raise ValueError("the signature is not a detached compact JWS")
        payload = base64.urlsafe_b64encode(canonical_bytes(query)).rstrip(b"=").decode("ascii")
        envelope = SignedContextProduct(payload=payload, protected=protected, signature=signature)
        identity_provider.verify(signed=envelope, public_keys=authority.door_keys)
        if envelope.declared_header().get(DOOR_SIGNATURE_ASSERTION) != SUBJECT_MATCH_CLASS:
            raise ValueError("the signature does not assert that it signs a subject-match query")
    except (IdentityError, ValueError) as invalid:
        raise SubjectMatchSignatureInvalid(
            "no signature by the erasure door's declared key verifies over this subject-match query"
            " (SEC-009; D-IMPL-378, D3b)"
        ) from invalid
