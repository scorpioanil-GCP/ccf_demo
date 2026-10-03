"""HumanPrincipalBinding — no HITL action without a principal (D-IMPL-21).

Written before the implementation per the TDD discipline. The claims pinned
here: all four D-IMPL-21 fields are required (approver identity,
authentication context, action time, content hash of the product the
approver saw); two distinct approvers produce distinguishable bindings
(D-23 multi-principal); and the binding is frozen and canonically
serializable, so it can land in the replay record byte for byte.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)

ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)


def _binding_document() -> dict[str, Any]:
    return {
        "approver": {
            "subject_id": "credit-officer-7",
            "identity_provider_ref": "oidc:acme-bank-sso",
        },
        "authentication": {
            "method": "oidc",
            "assurance_level": "aal2",
            "session_ref": "session-01HZX",
        },
        "action_time": ACTION_TIME,
        "product_content_hash": content_hash({"product": "seen"}),
        "verdict": "approve",
    }


def _binding(**mutations: Any) -> HumanPrincipalBinding:
    document = _binding_document()
    document.update(mutations)
    return HumanPrincipalBinding.model_validate(document)


def test_a_complete_binding_validates() -> None:
    binding = _binding()
    assert isinstance(binding.approver, ApproverIdentity)
    assert isinstance(binding.authentication, AuthenticationContext)
    assert binding.action_time == ACTION_TIME


@pytest.mark.parametrize(
    "omitted",
    ["approver", "authentication", "action_time", "product_content_hash"],
)
def test_omitting_any_d_impl_21_field_is_a_validation_error(
    omitted: str,
) -> None:
    document = _binding_document()
    del document[omitted]
    with pytest.raises(ValidationError, match=omitted):
        HumanPrincipalBinding.model_validate(document)


def test_a_non_content_hash_product_reference_is_refused() -> None:
    with pytest.raises(ValidationError, match="content hash"):
        _binding(product_content_hash="not-a-hash")


def test_two_approvers_produce_distinct_distinguishable_bindings() -> None:
    """D-23: multi-principal — identity distinguishes bindings."""
    first = _binding()
    second = _binding(
        approver={
            "subject_id": "credit-officer-9",
            "identity_provider_ref": "oidc:acme-bank-sso",
        }
    )
    assert first != second
    assert first.approver.subject_id != second.approver.subject_id
    assert content_hash(first) != content_hash(second)


def test_the_binding_is_frozen() -> None:
    binding = _binding()
    with pytest.raises(ValidationError):
        binding.action_time = datetime(2026, 8, 1, tzinfo=UTC)  # type: ignore[misc]


def test_the_binding_round_trips_through_canonical_serialization() -> None:
    binding = _binding()
    rebuilt = HumanPrincipalBinding.model_validate(_binding_document())
    assert canonical_bytes(binding) == canonical_bytes(rebuilt)
    assert content_hash(binding) == content_hash(rebuilt)


def test_a_naive_action_time_cannot_reach_canonical_serialization() -> None:
    """The action time is injected; a naive one is refused before replay."""
    from ccf.contracts.canonical import CanonicalizationError

    binding = _binding(action_time=datetime(2026, 7, 30, 12, 0, 0))
    with pytest.raises(CanonicalizationError):
        canonical_bytes(binding)


# --- D-IMPL-353 §2 P6: the claims a binding is minted FROM ----------------------
#
# ``AuthenticationClaims`` is what the deployment's credential verifier states
# about HOW a bearer authenticated. It travels on the verified grant and in the
# token's claims under ``AUTHENTICATION_CLAIM``; the doors mint the binding's
# identity-provider reference and authentication context from it and from
# nothing else. These tests pin the contract's shape and its wire key.


def test_authentication_claims_carry_the_four_provider_statements() -> None:
    from ccf.hitl.principal import AuthenticationClaims

    claims = AuthenticationClaims(
        identity_provider_ref="oidc:acme-bank-sso",
        method="oidc",
        assurance_level="aal2",
        session_ref="session-01HZX",
    )
    assert set(AuthenticationClaims.model_fields) == {
        "identity_provider_ref",
        "method",
        "assurance_level",
        "session_ref",
    }
    # No default on any of them: a verifier that says nothing about one axis
    # has not attested the authentication, and the door must refuse rather
    # than fill the blank.
    assert all(
        field.is_required() for field in AuthenticationClaims.model_fields.values()
    )
    assert claims.assurance_level == "aal2"


def test_authentication_claims_refuse_extra_and_missing_fields() -> None:
    from ccf.hitl.principal import AuthenticationClaims

    with pytest.raises(ValidationError):
        AuthenticationClaims.model_validate(
            {"identity_provider_ref": "x", "method": "m", "assurance_level": "a"}
        )
    with pytest.raises(ValidationError):
        AuthenticationClaims.model_validate(
            {
                "identity_provider_ref": "x",
                "method": "m",
                "assurance_level": "a",
                "session_ref": "s",
                "subject_id": "not-a-claim-axis",
            }
        )


def test_the_authentication_claim_key_is_a_stable_wire_constant() -> None:
    from ccf.hitl.principal import AUTHENTICATION_CLAIM

    assert AUTHENTICATION_CLAIM == "ccf.authentication"


def test_the_content_hash_validator_is_shared_and_refuses_non_hashes() -> None:
    """One validator for the binding and for the door-facing request
    (:class:`~ccf.hitl.transport.HitlActionRequest`), so the two cannot
    disagree about what a product identity looks like."""
    from ccf.hitl.principal import validate_content_hash

    good = content_hash({"product": "seen"})
    assert validate_content_hash(good) == good
    for bad in ("", "not-a-hash", "B" * 64, "a" * 63, "a" * 65):
        with pytest.raises(ValueError, match="content hash"):
            validate_content_hash(bad)
