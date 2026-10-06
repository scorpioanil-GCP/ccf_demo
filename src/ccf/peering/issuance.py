"""The signed issuance claims every inbound Peering envelope carries (`SEC-022`).

**SDK-defined** (CLAUDE.md §7.2, marked as an extension, not
whitepaper-derived mechanism); the whitepaper hook is §8.3 Pattern 4, whose
federation boundary is verified by the *receiving* Control Plane. Row
``SEC-022`` of ``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
ruled at Q14 (a) on all four parts and widened by ``D-IMPL-371``.

The defect this closes
----------------------

:class:`~ccf.peering.admission.PeeringAdmissionGate` verified a signature, the
peer's entitlements and the product's TTL — and nothing about *when* or *how
often* the envelope was presented. A captured envelope was admissible for its
product's whole TTL, any number of times, at any number of receivers, and the
envelope carried no question, so a peered composite child could not be held to
the subject its composite asked (``SEC-025-U1``).

What the claims are, and where they travel
------------------------------------------

:class:`IssuanceClaims` binds four facts: the instant the producer issued the
envelope (``issued_at``), a ``nonce`` the producer chose, and the question it
answered — the four axes (:class:`IssuedAnswer`, the shape of
:class:`~ccf.products.door.AnsweredQuestion`) and the request it answered
(:class:`IssuedRequest`, the shape of :class:`~ccf.products.door.WireRequest`).

**Why two local types and not the door's.** :mod:`ccf.products.door` imports,
through :mod:`ccf.products.refusal` and :mod:`ccf.graph.product_source`, this
package's admission gate; the door's types cannot be field types here without an
import cycle, and peering sits below the product door. The shapes are kept equal
member for member — ``tests/peering/test_admission_refuses_replay.py`` asserts
the field sets — and composition converts them to the door's own types, whose
validators then run (``src/ccf/products/composite.py::signed_question``).

They ride in ONE protected-header member, :data:`ISSUANCE_CLAIMS_HEADER`,
exactly as ``src/ccf/peering/eligibility.py::encode_eligibility_assertion`` /
``src/ccf/peering/eligibility.py::decode_eligibility_assertion`` carry the
eligibility assertion, and for the same reason: the JWS payload is the
product's canonical bytes — its content-address preimage — so a claim placed in
the payload would move the product's address. The protected header is part of
the JWS signing input, so every claim here is covered by the same ES256
signature as the product.

**The SDK mints no nonce and signs no envelope.** Uniqueness of the nonce per
``(tenant, peer)`` is the producer's obligation, as for the HITL claim set
(``src/ccf/hitl/identity_binding.py::HitlActionClaims``); the producer's
emitter is the deployment's (CINV-01).

What the receiving gate does with them
--------------------------------------

See :meth:`~ccf.peering.admission.PeeringAdmissionGate.admit`: an envelope whose
member is absent, unreadable or of an unknown lane is refused
``claims-missing``; one issued outside the peer grant's declared window is
refused ``stale-issuance``; and a nonce already spent by an **admission** is
refused ``replayed``. The window is judged against the ``now`` ``admit()``
already receives — this module reads no clock (``D-IMPL-358``).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from collections.abc import Mapping
from typing import Any, Final, Literal, Protocol, runtime_checkable

from pydantic import ValidationError, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes

__ccf_mode__ = "algorithmic"

__all__ = [
    "ISSUANCE_CLAIMS_HEADER",
    "ISSUANCE_CLAIMS_SCHEMA_VERSION",
    "InProcessSeenNonceSet",
    "IssuanceClaims",
    "IssuanceClaimsMalformed",
    "IssuedAnswer",
    "IssuedRequest",
    "SeenNonceSetProtocol",
    "decode_issuance_claims",
    "encode_issuance_claims",
    "issuance_staleness",
    "mint_issuance_claims",
]

#: The protected-header member the claims travel in. Distinct from the
#: producer and eligibility members, because each answers a different question
#: and a shared member would let one be presented as another.
ISSUANCE_CLAIMS_HEADER: Final = "ccf-issuance"

#: The claim set's own lane. A consumer refuses a lane it cannot read rather
#: than reading unknown members as absent — which is how an added binding would
#: otherwise be silently ignored.
ISSUANCE_CLAIMS_SCHEMA_VERSION: Final = "1.0.0"


class IssuanceClaimsMalformed(ValueError):
    """The issuance member is absent, unparseable, or a lane this build cannot read."""


def _aware(value: datetime, member: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{member} must be timezone-aware: a naive instant is not one"
            " instant (D-IMPL-38; SEC-022)"
        )
    return value


class IssuedAnswer(CCFContract):
    """The four question axes a producer signed that it answered.

    Member for member the shape of :class:`~ccf.products.door.AnsweredQuestion`
    (see the module docstring for why it is not that type).
    """

    subject: str
    intent: str
    freshness: str
    asked_at: datetime

    @field_validator("asked_at")
    @classmethod
    def _asked_at_is_aware(cls, value: datetime) -> datetime:
        return _aware(value, "asked_at")


class IssuedRequest(CCFContract):
    """The request a producer signed that it answered.

    Member for member the shape of :class:`~ccf.products.door.WireRequest`;
    composition converts it to that type, whose own parameter guard then runs.
    """

    product_id: str
    parameters: Mapping[str, Any]
    temporal_boundary: datetime | None

    @field_validator("temporal_boundary")
    @classmethod
    def _boundary_is_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware(value, "temporal_boundary")


class IssuanceClaims(CCFContract):
    """What a producer states about one envelope it issued (`SEC-022`).

    Attributes:
        schema_version: This contract's lane
            (:data:`ISSUANCE_CLAIMS_SCHEMA_VERSION`).
        issued_at: When the producer issued the envelope. **Timezone-aware**;
            a naive instant is refused, because the window comparison would
            otherwise be made in whatever zone the reader assumed.
        nonce: An opaque value the producer chose, unique per
            ``(tenant, peer)``. Non-empty. What makes a second presentation of
            the same bytes detectable.
        answered: The four question axes the producer says it answered —
            subject, intent, freshness and ``asked_at``.
        echo: The request the producer answered. Required beside ``answered``
            because the composite's shared answer check
            (``src/ccf/products/composite.py::CompositeAdmissionGate.hold_answer_to_question``)
            refuses an answer that echoes no request.
    """

    schema_version: str
    issued_at: datetime
    nonce: str
    answered: IssuedAnswer
    echo: IssuedRequest

    @field_validator("nonce")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("an issuance nonce cannot be empty (SEC-022)")
        return value

    @field_validator("issued_at")
    @classmethod
    def _issued_at_is_aware(cls, value: datetime) -> datetime:
        # The window is judged against the admission instant, and a naive
        # instant would be compared in whatever zone the reader assumed.
        return _aware(value, "issued_at")


def mint_issuance_claims(
    *,
    issued_at: datetime,
    nonce: str,
    answered: IssuedAnswer,
    echo: IssuedRequest,
) -> IssuanceClaims:
    """Assemble the claim set at the current lane. Mints nothing itself.

    ``nonce`` and ``issued_at`` are inputs: the producer supplies both, because
    a generator or a clock read here would be an SDK default for a deployment
    choice (CINV-01; ``D-IMPL-358``).
    """
    return IssuanceClaims(
        schema_version=ISSUANCE_CLAIMS_SCHEMA_VERSION,
        issued_at=issued_at,
        nonce=nonce,
        answered=answered,
        echo=echo,
    )


def encode_issuance_claims(claims: IssuanceClaims) -> str:
    """Render the claims for the protected header (canonical bytes)."""
    return canonical_bytes(claims).decode("utf-8")


def decode_issuance_claims(claim: object) -> IssuanceClaims:
    """Parse the protected-header member back into the typed claims.

    Raises:
        IssuanceClaimsMalformed: the member is absent, not a string, not JSON,
            not this contract's shape, or declares a lane this build does not
            read. Absence is not a pass.
    """
    if not isinstance(claim, str) or not claim:
        raise IssuanceClaimsMalformed(
            "the signed header carries no issuance claims; an envelope that"
            " does not say when it was issued, under which nonce and for which"
            " question cannot be held to a window or refused as a replay"
            " (SEC-022)"
        )
    try:
        parsed = json.loads(claim)
    except json.JSONDecodeError as error:
        raise IssuanceClaimsMalformed(
            f"the issuance claims are not JSON: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise IssuanceClaimsMalformed("the issuance claims are not an object")
    declared = parsed.get("schema_version")
    if declared != ISSUANCE_CLAIMS_SCHEMA_VERSION:
        raise IssuanceClaimsMalformed(
            f"the issuance claims declare schema version {declared!r}; this"
            f" build reads {ISSUANCE_CLAIMS_SCHEMA_VERSION!r}. Refused rather"
            " than read leniently: an unknown lane may bind facts this build"
            " would silently ignore"
        )
    try:
        return IssuanceClaims.model_validate_json(claim)
    except ValidationError as error:
        raise IssuanceClaimsMalformed(
            f"the issuance claims are not well formed: {error}"
        ) from error


def issuance_staleness(
    *,
    issued_at: datetime,
    now: datetime,
    max_age_seconds: int,
    skew_seconds: int,
) -> Literal["post-dated", "expired"] | None:
    """Judge ``issued_at`` against the admission instant ``now``, directionally.

    The two comparisons of ``src/ccf/hitl/transport.py::enforce_attestation``,
    never an absolute delta: an envelope may be issued at most
    ``skew_seconds`` AFTER ``now`` (a producer clock running ahead) and at most
    ``max_age_seconds`` BEFORE it. Both edges are inside the window.

    Returns:
        ``"post-dated"``, ``"expired"``, or ``None`` when inside the window.
    """
    ahead = (issued_at - now).total_seconds()
    behind = (now - issued_at).total_seconds()
    if ahead > skew_seconds:
        return "post-dated"
    if behind > max_age_seconds:
        return "expired"
    return None


@runtime_checkable
class SeenNonceSetProtocol(Protocol):
    """Where spent issuance nonces live (Q14-2 (a): in-process by default, pluggable).

    One method, atomic: a deployment with several receivers plugs one shared
    implementation into every gate, and a replay presented to any of them is
    refused. Keyed by tenant so one store can serve several tenants' gates.
    """

    def admit_once(self, *, tenant_id: str, peer_id: str, nonce: str) -> bool:
        """Record ``nonce`` as spent; ``True`` on first sight, ``False`` if already spent.

        Check-and-insert in ONE step: two concurrent presentations of the same
        nonce must not both see ``True``.
        """
        ...


class InProcessSeenNonceSet:
    """The reference :class:`SeenNonceSetProtocol`: a set behind a lock.

    The default each :class:`~ccf.peering.admission.PeeringAdmissionGate`
    constructs for itself, never shared between gates. **Bound, stated:** it
    covers one process and one gate, and its entries are retained for the
    gate's lifetime. The issuance window makes the set boundable — an entry
    older than ``max_age + skew`` can never be admitted again — but this
    reference implementation does not prune; the same retention question as the
    HITL reference transport's seen-nonce set (``CR-363-07``).
    """

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str]] = set()
        self._lock = threading.Lock()

    def admit_once(self, *, tenant_id: str, peer_id: str, nonce: str) -> bool:
        key = (tenant_id, peer_id, nonce)
        with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True
