"""The Peering trust-policy Control Plane artifact (D-IMPL-16).

SDK-defined extension (CLAUDE.md §7.2), attaching to whitepaper §8.3 Pattern 4
and to the Control Plane of §7.8. This is the configuration the admission gate
reads to answer one question — *what is this peer entitled to assert?* — and it
answers no other.

**Trust inputs are declared per Peering; the verdict is not** (``D-IMPL-59``
part 4). This artifact is keyed on the *peer*, never on the transport that
carried the peer's bytes, so the same peer is the same peer whichever Peering
transport reached it — A2A being the reference transport (part 2), not the
category. What the artifact supplies is an *input* to a decision made above
every transport by :class:`~ccf.peering.admission.PeeringAdmissionGate`; nothing
declared here concludes admission.

It is a typed :class:`~ccf.contracts.base.CCFContract`, modeled on
:class:`~ccf.controlplane.artifacts.HalfLifeTable`: SDK-owned shape,
deployment-owned values. The three properties the artifacts module argues for
hold here for the same reasons:

**Registering the wrong thing is a detectable error.** A bare mapping stored
under a trust-policy key looks exactly like a correct one until an inbound
product is admitted against it. A typed class turns that into a validation
failure at registration, before anything can be admitted on it.

**Every artifact carries its own semver lane.** ``semver`` is a declared field
with no default, so a policy whose author never stated its lane cannot be
registered. The lane is this class's own and is never compared across artifact
classes.

**Values stay out of code.** This module declares shape only. There is no peer
name here, no key identifier, no JWK material, no schema name, and no policy
regime — every one of those is the deployment's statement about its own
federation, and one the SDK invented would be one no examiner could trace to a
decision anyone made (CLAUDE.md §11, CINV-01; D-IMPL-38).

**Verification is not configurable.** D-IMPL-16 rules that every inbound
Peering Context Product is verified, with no fast path for a high-trust peer. That
ruling is structural here rather than merely followed: **this contract has no
field that could turn signature verification off, and none that could route a
peer around it.** ``extra="forbid"`` closes the other direction — a deployment
cannot add one. What a trust tier can express is narrower or wider *entitlement*
— which keys, which producers, which product classes, which regimes — and
entitlement is checked after verification, never instead of it. That claim is
enforced by a field-enumeration test, not by this paragraph; and it is the only
claim of that strength this module makes.

Resolution is by pinned ``(key, version)`` through the existing Control Plane
registry, and registration refusals are audited with ``resolved=False`` on the
registry's own path, because a federation's version history is only trustworthy
if the attempts it turned away are on record.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.peering.identity import JsonWebKey

__ccf_mode__ = "algorithmic"

__all__ = [
    "PEERING_TRUST_POLICY",
    "PeeringTrustPolicy",
    "PeerNotTrusted",
    "PeerTrustGrant",
    "TrustPolicyViolation",
    "trust_policy_key",
]


class TrustPolicyViolation(LookupError):
    """A peer asserted something its trust-policy entry does not cover.

    A :class:`LookupError` because that is literally what happened — the
    assertion was not found among the peer's entitlements. Raised rather than
    softened to a boolean at the resolution surfaces, so an admission path
    cannot treat "not entitled" as "not sure".
    """


class PeerNotTrusted(TrustPolicyViolation):
    """The policy names no entry for this peer at all.

    Distinct from a per-assertion refusal: an unknown peer is a federation that
    was never configured, not a peer overreaching a known grant, and a
    deployment reading its audit log should not have to guess which it saw.
    """


class PeerTrustGrant(CCFContract):
    """What one peer is entitled to assert, per D-IMPL-16.

    Four declared sets and one declared issuance window, none with a default. Empty is expressible and means
    exactly what it says — this peer may assert nothing of that kind — because
    a grant that quietly defaulted to "anything" would be the fast path this
    contract exists to make unreachable.

    Attributes:
        signing_keys: Public JWKs this peer may sign with, keyed by the ``kid``
            its protected header will declare. The admission gate hands this
            mapping to :meth:`~ccf.peering.identity.IdentityProvider.verify`, which
            is how a peer's identity is bound to its entitlements: a product
            signed by a key outside this mapping is not this peer's, whatever
            the header claims.
        permitted_producer_hashes: The ``producer_agent_definition_hash``
            values this peer may claim to have produced under.
        permitted_schema_names: The Context Product classes it may send.
        permitted_policy_regimes: The policy-regime identifiers it may claim.
        signature_max_age_seconds: How long before the admission instant this
            peer's envelope may have been issued (`SEC-022`). Positive.
        permitted_clock_skew_seconds: How far after the admission instant this
            peer's envelope may claim to have been issued — its clock running
            ahead (`SEC-022`). Non-negative.

    **The issuance window has no default** (Q14-3 (a), ``D-IMPL-356``,
    ``D-IMPL-38``): both members are required, so a grant whose author never
    stated how stale or how post-dated this peer's envelopes may be cannot be
    constructed. Per peer rather than per policy, because *what this peer may
    assert* is this contract's one question, and a federation can tolerate a
    slow peer without widening every peer. Named after the HITL pair
    (``src/ccf/hitl/transport.py::HitlPolicy``), with the same validators.
    The window is an entitlement checked after signature verification, never
    instead of it.
    """

    signing_keys: Mapping[str, JsonWebKey]
    permitted_producer_hashes: frozenset[str]
    permitted_schema_names: frozenset[str]
    permitted_policy_regimes: frozenset[str]
    signature_max_age_seconds: int
    permitted_clock_skew_seconds: int

    @field_validator("signature_max_age_seconds")
    @classmethod
    def _max_age_is_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(
                "signature_max_age_seconds must be a positive number of"
                " seconds (SEC-022)"
            )
        return value

    @field_validator("permitted_clock_skew_seconds")
    @classmethod
    def _skew_is_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                "permitted_clock_skew_seconds cannot be negative (SEC-022)"
            )
        return value

    def signing_key(self, *, key_id: str) -> JsonWebKey:
        """Return the public JWK this peer may sign with under ``key_id``.

        Raises:
            TrustPolicyViolation: the peer's entry lists no such key.
        """
        try:
            return self.signing_keys[key_id]
        except KeyError:
            raise TrustPolicyViolation(
                f"this peer is not entitled to sign with kid {key_id!r}"
            ) from None

    def require_producer(self, *, producer_agent_definition_hash: str) -> None:
        """Raise unless this peer may assert that producer.

        Raises:
            TrustPolicyViolation: the hash is outside the peer's entry.
        """
        if producer_agent_definition_hash not in self.permitted_producer_hashes:
            raise TrustPolicyViolation(
                "this peer is not entitled to assert producer"
                f" {producer_agent_definition_hash!r}"
            )

    def require_schema(self, *, schema_name: str) -> None:
        """Raise unless this peer may send that product class.

        Raises:
            TrustPolicyViolation: the schema is outside the peer's entry.
        """
        if schema_name not in self.permitted_schema_names:
            raise TrustPolicyViolation(
                f"this peer is not entitled to send {schema_name!r} products"
            )

    def require_policy_regime(self, *, policy_regime_id: str) -> None:
        """Raise unless this peer may claim that policy regime.

        Raises:
            TrustPolicyViolation: the regime is outside the peer's entry.
        """
        if policy_regime_id not in self.permitted_policy_regimes:
            raise TrustPolicyViolation(
                "this peer is not entitled to claim policy regime"
                f" {policy_regime_id!r}"
            )


class PeeringTrustPolicy(CCFContract):
    """One tenant's federation policy, as a versioned Control Plane artifact.

    Tenant-scoped by construction (D-IMPL-05): the tenant is a field on the
    artifact and part of its content, so two tenants naming the same peer hold
    two different artifacts with two different content addresses. One tenant's
    grant to a peer therefore cannot admit that peer for another — not by
    convention, but because there is no shared object for it to leak through.

    ``peers`` requires at least one entry: an empty policy is indistinguishable
    from a deployment that forgot to configure one, and registering it would
    let a federation come up trusting nothing while looking configured.

    Attributes:
        semver: This artifact's own lane. No default — see the module
            docstring.
        tenant_id: The tenant this policy governs admission for.
        peers: Peer identifier to its entitlements.
    """

    semver: str
    tenant_id: str
    peers: Mapping[str, PeerTrustGrant] = Field(min_length=1)

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)

    def grant_for(self, *, peer_id: str) -> PeerTrustGrant:
        """Return ``peer_id``'s entitlements under this policy.

        Raises:
            PeerNotTrusted: this policy names no such peer. Never a permissive
                empty grant — an unconfigured peer is a deployment fact the
                admission path must surface, not one it may interpret.
        """
        try:
            return self.peers[peer_id]
        except KeyError:
            raise PeerNotTrusted(
                f"no trust-policy entry for peer {peer_id!r} under tenant"
                f" {self.tenant_id!r}"
            ) from None


#: The artifact class the registry validates trust policies against.
PEERING_TRUST_POLICY = ArtifactClass(
    class_id="ccf.peering-trust-policy", contract=PeeringTrustPolicy
)


def trust_policy_key(*, tenant_id: str) -> str:
    """Return the Control Plane key one tenant's trust policy registers under.

    A derivation rather than a table: the SDK supplies the shape of the key so
    two components cannot disagree about where a tenant's policy lives, and
    supplies no tenant, so it holds no deployment's vocabulary (CINV-01).
    """
    # Tenant-first (``{tenant}/{class}``): the registry's one tenant comparison
    # reads the segment before the first ``/`` (D-IMPL-353 §1.3), so a
    # class-first key could be registered only by a capability whose tenant
    # was the class name.
    return f"{tenant_id}/{PEERING_TRUST_POLICY.class_id}"
