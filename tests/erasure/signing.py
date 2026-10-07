"""The SEC-005 test signing key, for SEC-009's signature-bound erasure approvals (fix round 4).

The erasure approval is bound to a SIGNED HITL attestation (`D-IMPL-363`), so
every test that plants or approves an erasure signs for real — with a P-256 key
generated the way the SEC-005 tests generate theirs, under the same key id —
and pins its public half for the approver in a registered ``HitlPolicy``.
Never a placeholder hash. The private key lives in a per-process temporary
directory; it signs only test claims.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from functools import cache
from pathlib import Path

from joserfc.jwk import ECKey

from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.identity_binding import HitlActionClaims, SignedHitlAction, sign_hitl_action
from ccf.hitl.transport import HITL_POLICY
from ccf.peering.identity import DetachedJwsIdentityProvider, FileBackedKeySource, JsonWebKey

#: The SEC-005 tests' key id (`tests/hitl/test_sec005_attestation_controls.py`).
APPROVER_KID = "sec005-approver-signing-key"
#: Where the erasure test planes register their signed HITL policy.
HITL_POLICY_KEY = "acme-bank/hitl/erasure-attestation-policy"
#: The window this test-as-deployment states (CINV-01: no SDK default).
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60


def _write_key(directory: Path) -> None:
    key = ECKey.generate_key("P-256", parameters={"kid": APPROVER_KID})
    (directory / f"{APPROVER_KID}.jwk").write_text(json.dumps(key.as_dict(private=True)), encoding="utf-8")


@cache
def key_dir() -> Path:
    """The approver's key directory, generated once per test process."""
    directory = Path(tempfile.mkdtemp(prefix="ccf-sec009-approver-"))
    _write_key(directory)
    return directory


def forger_key_dir() -> Path:
    """A DIFFERENT key under the SAME key id — the strongest forger: every claim
    right, the declared kid right, the key material not the pinned one."""
    directory = Path(tempfile.mkdtemp(prefix="ccf-sec009-forger-"))
    _write_key(directory)
    return directory


def provider(directory: Path | None = None) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(key_source=FileBackedKeySource(directory=directory or key_dir()))


def public_jwk(directory: Path | None = None) -> JsonWebKey:
    private = json.loads(((directory or key_dir()) / f"{APPROVER_KID}.jwk").read_text(encoding="utf-8"))
    return ECKey.import_key(private).as_dict(private=False)


def register_signed_policy(registry: ControlPlaneRegistry, *, subject: str, key: str = HITL_POLICY_KEY) -> str:
    """Register the ruled signed ``HitlPolicy`` pinning the test key for ``subject``; return the key."""
    from ccf.contracts.canonical import content_hash
    from ccf.controlplane.registry import ControlPlaneMissing
    from tests.composition import register_typed_at_composition

    policy = parse_artifact(
        {
            "semver": "1.0.0",
            "signed_binding_required": True,
            "signature_max_age_seconds": MAX_AGE_SECONDS,
            "permitted_clock_skew_seconds": SKEW_SECONDS,
            "trusted_keys": {subject: {APPROVER_KID: public_jwk()}},
        },
        HITL_POLICY,
    )
    try:
        _version, standing = registry.resolve_latest(key)
    except ControlPlaneMissing:
        standing = None
    if standing is None or content_hash(standing) != content_hash(policy):
        register_typed_at_composition(registry, key, policy, HITL_POLICY)
    return key


def policy_ref(registry: ControlPlaneRegistry, key: str = HITL_POLICY_KEY) -> str:
    """The ``key@version`` the transport stamps for the policy in force."""
    version, _artifact = registry.resolve_latest(key)
    return f"{key}@{version}"


def sign(
    *,
    tenant: str,
    event_key: str,
    product_content_hash: str,
    subject_id: str,
    issued_at: datetime,
    action: str = "approve",
    nonce: str | None = None,
    directory: Path | None = None,
) -> SignedHitlAction:
    claims = HitlActionClaims(
        tenant=tenant,
        event_key=event_key,
        action=action,
        product_content_hash=product_content_hash,
        subject_id=subject_id,
        issued_at=issued_at,
        nonce=nonce or f"nonce-{event_key}",
    )
    return sign_hitl_action(claims, provider=provider(directory), key_id=APPROVER_KID)
