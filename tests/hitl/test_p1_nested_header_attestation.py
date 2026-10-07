"""T4-P1 at HITL attestation: a nested protected header is refused by name, never a crash (`D-IMPL-374`, final fix wave FW-1).

The whole-branch review found the defect in the shared parser
``ccf.peering.identity.SignedContextProduct.declared_header``: its ``except``
covered only ``ValueError``, so a deeply nested JSON header raised an uncaught
``RecursionError``. :func:`~ccf.hitl.identity_binding.verify_hitl_action`
reads the declared key id under ``except (IdentityError, ValueError)``, so a
signed HITL attestation carrying such a header crashed the authority path
instead of being refused as an attestation that does not verify.
"""

from __future__ import annotations

import base64

import pytest
from joserfc.jwk import ECKey

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.identity_binding import AttestationInvalid, verify_hitl_action
from ccf.hitl.transport import HITL_POLICY, SignedBindingInvalidRefused
from ccf.peering.identity import DetachedJwsIdentityProvider, JsonWebKey, SignatureMalformed
from tests.controlplane.composition import compose_register_typed
from tests.hitl.test_signed_binding_authority import (  # noqa: F401 - pytest fixtures
    APPROVER_KID,
    POLICY_KEY,
    _TENANT,
    _attest,
    _binding,
    _claims,
    _policy,
    _submit,
    _transport,
    approver_key,
    key_dir,
    other_key,
    plane,
    provider,
    trusted_keys,
)

#: Nested past any recursion limit the JSON decoder honors (test data).
DEPTH = 100_000


def _nested_header() -> str:
    text = "[" * DEPTH + "]" * DEPTH
    return base64.urlsafe_b64encode(text.encode("ascii")).rstrip(b"=").decode("ascii")


def test_p1_verify_refuses_a_nested_header_attestation_as_malformed(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    signed = _attest(_claims(), provider)
    _, _, signature = signed.signature.partition("..")
    nested = signed.model_copy(update={"signature": f"{_nested_header()}..{signature}"})
    public: dict[str, JsonWebKey] = {APPROVER_KID: approver_key.as_dict(private=False)}
    with pytest.raises(AttestationInvalid) as refused:
        verify_hitl_action(nested, provider=provider, public_keys=public)
    assert isinstance(refused.value.__cause__, SignatureMalformed)


def test_p1_the_authority_path_refuses_a_nested_header_attestation_by_name(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    compose_register_typed(plane, POLICY_KEY, _policy(required=True, trusted_keys=trusted_keys), HITL_POLICY)
    transport = _transport(plane, provider)
    signed = _attest(_claims(), provider)
    _, _, signature = signed.signature.partition("..")
    nested = signed.model_copy(update={"signature": f"{_nested_header()}..{signature}"})
    with pytest.raises(SignedBindingInvalidRefused):
        _submit(transport, _binding(), nested)
    assert transport.submissions(tenant=_TENANT) == ()
