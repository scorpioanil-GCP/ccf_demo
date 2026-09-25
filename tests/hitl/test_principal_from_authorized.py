"""The door mints the binding; the caller does not describe it (D-IMPL-353 §2 P6).

Written before :func:`ccf_runtime.identity_binding.principal_from_authorized`
existed. The claims:

* the binding's ``subject_id`` IS ``authorized.principal`` — there is no
  parameter through which a caller could substitute a subject (the T-07.1-05
  property, carried forward from ``principal_from_token_grant``);
* the identity-provider reference and the authentication context are the
  VERIFIED credential's :class:`~ccf.hitl.principal.AuthenticationClaims`,
  verbatim — there is no parameter for ``assurance_level`` or its siblings
  either, so a caller-typed step-up claim is unrepresentable rather than
  refused;
* ``action_time`` is injected, never read from a wall clock here;
* a credential that states no authentication is refused, typed, before any
  binding exists (``attested_authentication``);
* the two readers — off a ``TokenGrant`` and off an ``AccessToken`` — are
  the single reads of the claim, and an absent or malformed claim reads as
  ``None`` (unparseable is not permissive).
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest
from mcp.server.auth.provider import AccessToken
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims
from ccf_runtime.identity_binding import (
    ERROR_AUTHENTICATION_UNATTESTED,
    AuthenticationUnattested,
    attested_authentication,
    authentication_of_token,
    principal_from_authorized,
)

from .capabilities import submit_capability

_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_HASH = content_hash({"product": "seen"})
_CLAIMS = AuthenticationClaims(
    identity_provider_ref="oidc:acme-bank-sso",
    method="oidc",
    assurance_level="aal2",
    session_ref="session-01HZX",
)


def test_the_subject_is_the_capabilitys_principal() -> None:
    capability = submit_capability(
        tenant="acme-bank", principal="credit-officer-7", event_key="e-1"
    )
    binding = principal_from_authorized(
        capability,
        authentication=_CLAIMS,
        action_time=_TIME,
        product_content_hash=_HASH,
    )
    assert binding.approver.subject_id == "credit-officer-7"
    assert binding.approver.identity_provider_ref == _CLAIMS.identity_provider_ref
    assert binding.authentication.method == _CLAIMS.method
    assert binding.authentication.assurance_level == _CLAIMS.assurance_level
    assert binding.authentication.session_ref == _CLAIMS.session_ref
    assert binding.action_time == _TIME
    assert binding.product_content_hash == _HASH


def test_no_parameter_exists_for_the_subject_or_any_claim_axis() -> None:
    """Unrepresentable, not refused: the signature has no slot for any value
    the caller might type into the audit record."""
    parameters = set(inspect.signature(principal_from_authorized).parameters)
    assert parameters == {
        "authorized",
        "authentication",
        "action_time",
        "product_content_hash",
    }
    for forbidden in (
        "subject_id",
        "identity_provider_ref",
        "method",
        "assurance_level",
        "session_ref",
        "grant",
    ):
        assert forbidden not in parameters


def test_the_contract_validators_are_not_laundered() -> None:
    capability = submit_capability(tenant="t", principal="p", event_key="e")
    with pytest.raises(ValidationError):
        principal_from_authorized(
            capability,
            authentication=_CLAIMS,
            action_time=_TIME,
            product_content_hash="not-a-hash",
        )


def test_an_unattested_credential_is_refused_before_any_binding_exists() -> None:
    with pytest.raises(AuthenticationUnattested, match="authentication"):
        attested_authentication(None)
    assert attested_authentication(_CLAIMS) is _CLAIMS
    assert ERROR_AUTHENTICATION_UNATTESTED == "authentication-unattested"


def test_the_token_reader_is_the_single_read_and_fails_closed() -> None:
    def token(claims: object) -> AccessToken:
        return AccessToken(token="t", client_id="p", scopes=["s"], claims=claims)  # type: ignore[arg-type]

    assert authentication_of_token(
        token({AUTHENTICATION_CLAIM: _CLAIMS.model_dump(mode="json")})
    ) == _CLAIMS
    assert authentication_of_token(token(None)) is None
    assert authentication_of_token(token({})) is None
    assert authentication_of_token(token({AUTHENTICATION_CLAIM: "aal2"})) is None
    # A claim of the right shape with a missing axis is unparseable, and
    # unparseable is not permissive.
    assert (
        authentication_of_token(
            token({AUTHENTICATION_CLAIM: {"identity_provider_ref": "x"}})
        )
        is None
    )
