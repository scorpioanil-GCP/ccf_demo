"""`SEC-022`: the signed issuance claims a test producer attaches to an envelope.

A producer — never the SDK — mints the claims: the SDK ships no signer for the
A2A envelope and no nonce generator (the deployment's emitter signs; CINV-01).
This helper is that emitter's half, for tests: it renders the one
protected-header member carrying ``issued_at``, a fresh ``nonce`` and the
question the producer answered (`D-IMPL-371`).

The window values below are THIS FIXTURE'S numbers, not recommendations — the
SDK ships no default (Q14 (a), `D-IMPL-356`). ``WINDOW_MAX_AGE_SECONDS`` is wide
enough for the `SEC-010` B3 fixture, whose question and fabric instants are
seven minutes (420 s) apart
(``tests/products/test_d364_peered_child_served_at.py``).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime

from ccf.peering.issuance import (
    ISSUANCE_CLAIMS_HEADER,
    IssuedAnswer,
    IssuedRequest,
    encode_issuance_claims,
    mint_issuance_claims,
)

#: The protected-header member name — the SDK's constant.
ISSUANCE_HEADER = ISSUANCE_CLAIMS_HEADER

#: This fixture's declared window. Not a recommendation.
WINDOW_MAX_AGE_SECONDS = 900
WINDOW_SKEW_SECONDS = 60

#: Fixture-side question vocabulary (deployment values, authored test-side).
FIXTURE_SUBJECT = "acct-1"
FIXTURE_INTENT = "fixture-intent"
FIXTURE_FRESHNESS = "fixture-freshness"


def fresh_nonce() -> str:
    """A nonce unique per envelope — the signer's obligation, not the SDK's."""
    return uuid.uuid4().hex


def window() -> dict[str, int]:
    """The two grant members, for a ``PeerTrustGrant(**..., **window())``."""
    return {
        "signature_max_age_seconds": WINDOW_MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": WINDOW_SKEW_SECONDS,
    }


def issuance_member(
    *,
    product: object,
    issued_at: datetime,
    subject: str = FIXTURE_SUBJECT,
    nonce: str | None = None,
    parameters: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """The one header member: ``{ISSUANCE_HEADER: <canonical JSON claims>}``."""
    boundary: datetime = product.temporal_boundary  # type: ignore[attr-defined]
    claims = mint_issuance_claims(
        issued_at=issued_at,
        nonce=nonce if nonce is not None else fresh_nonce(),
        answered=IssuedAnswer(
            subject=subject,
            intent=FIXTURE_INTENT,
            freshness=FIXTURE_FRESHNESS,
            asked_at=boundary,
        ),
        echo=IssuedRequest(
            product_id=product.schema_name,  # type: ignore[attr-defined]
            parameters=dict(parameters or {"subject": subject}),
            temporal_boundary=boundary,
        ),
    )
    return {ISSUANCE_HEADER: encode_issuance_claims(claims)}
