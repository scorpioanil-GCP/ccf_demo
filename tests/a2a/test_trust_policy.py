"""The A2A trust-policy artifact: lane, closure, entitlement, tenancy.

Named per property defended. Two of these exist because a weaker suite would
pass against a broken implementation:

* the **field-enumeration** test makes "this contract cannot express a
  verification skip" a claim the suite enforces rather than one the docstring
  asserts — a docstring cannot fail when someone adds the field;
* the **two-tenant** test is the D-23 obligation: an entitlement check that is
  right with one tenant and wrong with two is the CR-01 defect class, and a
  single-tenant suite would not see it.

Peer identifiers, schema names, producer hashes, and policy regimes are all
fixture vocabulary. The SDK enumerates none of them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from joserfc.jwk import ECKey
from pydantic import ValidationError

from ccf.a2a.identity import JsonWebKey
from ccf.a2a.trust_policy import (
    A2A_TRUST_POLICY,
    A2ATrustPolicy,
    PeerNotTrusted,
    PeerTrustGrant,
    TrustPolicyViolation,
    trust_policy_key,
)
from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneRegistry

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

PEER = "zenith-bank"
OTHER_PEER = "meridian-bank"
PEER_KID = "zenith-bank-a2a-1"
PRODUCER_HASH = "producer-hash-fixture"
OTHER_PRODUCER_HASH = "producer-hash-fixture-other"
TENANT_ONE = "acme-bank"
TENANT_TWO = "borealis-bank"

#: Any attribute name matching one of these would let a deployment configure
#: its way around signature verification. D-IMPL-16 makes their absence the
#: mechanism, so the absence is asserted rather than described.
FORBIDDEN_FIELD_MARKERS = (
    "skip",
    "bypass",
    "trusted",
    "fast_path",
    "fastpath",
    "unverified",
    "insecure",
    "disable",
    "allow_all",
)


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def _schema_name() -> str:
    schema: str = _fixture("controlplane.yaml")["product_class"]["schema_name"]
    return schema


def _policy_regime() -> str:
    regime: str = _fixture("controlplane.yaml")["policy_bundle"]["regime"]
    return regime


def _public_jwk() -> JsonWebKey:
    key: JsonWebKey = ECKey.generate_key(
        "P-256", parameters={"kid": PEER_KID}
    ).as_dict(private=False)
    return key


def grant(
    *,
    schema_names: frozenset[str] | None = None,
    producer_hashes: frozenset[str] | None = None,
    regimes: frozenset[str] | None = None,
) -> PeerTrustGrant:
    return PeerTrustGrant(
        signing_keys={PEER_KID: _public_jwk()},
        permitted_producer_hashes=(
            producer_hashes
            if producer_hashes is not None
            else frozenset({PRODUCER_HASH})
        ),
        permitted_schema_names=(
            schema_names if schema_names is not None else frozenset({_schema_name()})
        ),
        permitted_policy_regimes=(
            regimes if regimes is not None else frozenset({_policy_regime()})
        ),
    )


def policy(*, tenant_id: str = TENANT_ONE, **kwargs: Any) -> A2ATrustPolicy:
    return A2ATrustPolicy(
        semver="1.0.0", tenant_id=tenant_id, peers={PEER: grant(**kwargs)}
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


# --- the semver lane -------------------------------------------------------


def test_a_policy_without_a_semver_lane_cannot_be_constructed() -> None:
    with pytest.raises(ValidationError):
        A2ATrustPolicy(tenant_id=TENANT_ONE, peers={PEER: grant()})  # type: ignore[call-arg]


def test_a_policy_with_a_malformed_semver_lane_is_refused() -> None:
    with pytest.raises(ValidationError):
        A2ATrustPolicy(
            semver="one", tenant_id=TENANT_ONE, peers={PEER: grant()}
        )


def test_a_policy_naming_no_peers_is_refused() -> None:
    """An empty federation is indistinguishable from an unconfigured one."""
    with pytest.raises(ValidationError):
        A2ATrustPolicy(semver="1.0.0", tenant_id=TENANT_ONE, peers={})


def test_registering_a_bare_mapping_under_the_class_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """Registering the wrong thing must be a detectable error, not a plausible
    one — the whole argument for a typed artifact class."""
    key = trust_policy_key(tenant_id=TENANT_ONE)
    with pytest.raises(TypeError):
        registry.register_typed(key, {"peers": {}}, A2A_TRUST_POLICY)


def test_a_failed_trust_policy_resolution_is_audited_as_unresolved(
    registry: ControlPlaneRegistry,
) -> None:
    """A version history is only trustworthy if the lookups that found nothing
    are on record — an admission that resolved no policy must be visible.

    Scoped deliberately to *resolution*. ``register_typed`` refuses a wrongly
    shaped artifact by raising before it records, so a refused registration
    leaves no audit event today; that gap is registry mechanism, not this
    artifact's, and is logged rather than papered over here.
    """
    key = trust_policy_key(tenant_id=TENANT_ONE)
    registry.register_typed(key, policy(), A2A_TRUST_POLICY)
    with pytest.raises(Exception):
        registry.resolve(key, "no-such-version")
    unresolved = [
        event
        for event in registry.audit_events()
        if event.key == key and not event.resolved
    ]
    assert unresolved


def test_a_registered_policy_resolves_by_pinned_key_and_version(
    registry: ControlPlaneRegistry,
) -> None:
    key = trust_policy_key(tenant_id=TENANT_ONE)
    registered = policy()
    version = registry.register_typed(key, registered, A2A_TRUST_POLICY)
    assert registry.resolve(key, version) == registered


# --- closure ---------------------------------------------------------------


def test_an_unknown_field_on_a_policy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        A2ATrustPolicy(
            semver="1.0.0",
            tenant_id=TENANT_ONE,
            peers={PEER: grant()},
            verification_required=False,  # type: ignore[call-arg]
        )


def test_an_unknown_field_on_a_peer_grant_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PeerTrustGrant(
            signing_keys={},
            permitted_producer_hashes=frozenset(),
            permitted_schema_names=frozenset(),
            permitted_policy_regimes=frozenset(),
            skip_verification=True,  # type: ignore[call-arg]
        )


def test_no_field_on_the_contract_could_express_a_verification_skip() -> None:
    """D-IMPL-16 made structural: enumerate the fields and assert the absence.

    Enforced here rather than in a docstring, because a docstring cannot fail
    when a later contributor adds ``trusted_peer_fast_path``.
    """
    names = set(A2ATrustPolicy.model_fields) | set(PeerTrustGrant.model_fields)
    offending = [
        name
        for name in names
        if any(marker in name.lower() for marker in FORBIDDEN_FIELD_MARKERS)
    ]
    assert offending == []


def test_a_policy_is_an_auditable_canonically_serializable_value() -> None:
    registered = policy()
    assert isinstance(registered, CCFContract)
    assert json.loads(registered.model_dump_json())["tenant_id"] == TENANT_ONE


# --- entitlement -----------------------------------------------------------


def test_a_peer_may_assert_only_the_producer_hashes_its_entry_lists() -> None:
    entry = policy().grant_for(peer_id=PEER)
    entry.require_producer(producer_agent_definition_hash=PRODUCER_HASH)
    with pytest.raises(TrustPolicyViolation):
        entry.require_producer(
            producer_agent_definition_hash=OTHER_PRODUCER_HASH
        )


def test_a_peer_may_send_only_the_schema_names_its_entry_lists() -> None:
    entry = policy().grant_for(peer_id=PEER)
    entry.require_schema(schema_name=_schema_name())
    with pytest.raises(TrustPolicyViolation):
        entry.require_schema(schema_name="some-other.product-class")


def test_a_peer_may_claim_only_the_policy_regimes_its_entry_lists() -> None:
    entry = policy().grant_for(peer_id=PEER)
    entry.require_policy_regime(policy_regime_id=_policy_regime())
    with pytest.raises(TrustPolicyViolation):
        entry.require_policy_regime(policy_regime_id="some-other-regime")


def test_a_peer_may_sign_only_with_the_key_ids_its_entry_lists() -> None:
    entry = policy().grant_for(peer_id=PEER)
    assert entry.signing_key(key_id=PEER_KID)
    with pytest.raises(TrustPolicyViolation):
        entry.signing_key(key_id="rotated-key-nobody-granted")


def test_an_empty_grant_permits_nothing_rather_than_everything() -> None:
    """The permissive reading of an empty set is the fast path in disguise."""
    entry = PeerTrustGrant(
        signing_keys={},
        permitted_producer_hashes=frozenset(),
        permitted_schema_names=frozenset(),
        permitted_policy_regimes=frozenset(),
    )
    with pytest.raises(TrustPolicyViolation):
        entry.require_schema(schema_name=_schema_name())
    with pytest.raises(TrustPolicyViolation):
        entry.signing_key(key_id=PEER_KID)


def test_an_unconfigured_peer_is_refused_not_given_an_empty_grant() -> None:
    with pytest.raises(PeerNotTrusted):
        policy().grant_for(peer_id=OTHER_PEER)


# --- the D-23 two-tenant case ----------------------------------------------


def test_two_tenant_policies_resolve_independently(
    registry: ControlPlaneRegistry,
) -> None:
    """One tenant's grant to a peer must not resolve for another tenant."""
    one = policy(tenant_id=TENANT_ONE, schema_names=frozenset({_schema_name()}))
    two = policy(
        tenant_id=TENANT_TWO, schema_names=frozenset({"borealis.other-product"})
    )
    key_one = trust_policy_key(tenant_id=TENANT_ONE)
    key_two = trust_policy_key(tenant_id=TENANT_TWO)
    version_one = registry.register_typed(key_one, one, A2A_TRUST_POLICY)
    version_two = registry.register_typed(key_two, two, A2A_TRUST_POLICY)

    assert key_one != key_two
    assert version_one != version_two
    resolved_one = registry.resolve(key_one, version_one)
    assert isinstance(resolved_one, A2ATrustPolicy)
    assert resolved_one.tenant_id == TENANT_ONE
    assert resolved_one.grant_for(
        peer_id=PEER
    ).permitted_schema_names == frozenset({_schema_name()})


def test_two_tenant_a_peer_permitted_for_one_is_not_permitted_for_the_other(
    registry: ControlPlaneRegistry,
) -> None:
    """The same peer, granted different classes per tenant, stays separated."""
    one = policy(tenant_id=TENANT_ONE, schema_names=frozenset({_schema_name()}))
    two = policy(
        tenant_id=TENANT_TWO, schema_names=frozenset({"borealis.other-product"})
    )
    one.grant_for(peer_id=PEER).require_schema(schema_name=_schema_name())
    with pytest.raises(TrustPolicyViolation):
        two.grant_for(peer_id=PEER).require_schema(schema_name=_schema_name())


def test_two_tenant_policies_never_share_a_control_plane_key() -> None:
    assert trust_policy_key(tenant_id=TENANT_ONE) != trust_policy_key(
        tenant_id=TENANT_TWO
    )
