"""Per-principal entitlement to Context Products, as a Control Plane artifact.

SDK-defined extension. Its hooks are CLAUDE.md §7.1 (MCP as the Experience
Layer access surface) and §8.3 (the Experience Layer's three front doors); it
attaches to whitepaper §7.6 (*Context Products — System of Delivery*) and to
the Control Plane of §7.8. CLAUDE.md §11 requires an SDK extension to cite this
project's own record rather than a whitepaper section that does not specify it,
so: the ruling is Dave's of 2026-08-10 — *"I need to make a fabric change to
accommodate this"* — and the framing and measurement are
``docs/CONTEXT_PRODUCT_REVISION.md`` §10.

**Entitlement is not a new axis.** ``P`` already composes *during* assembly:
the policy operators run before similarity at every assembly step. What was
missing is ``P`` **at delivery** — who may receive a product class, and as
whom. Saying it that way keeps the change inside the whitepaper's own
vocabulary rather than introducing a parallel concept beside the six axes of
``G(E, R, T, P, Π, L)``.

This module is the artifact and its resolution surface, and nothing else. The
door that reads it lives elsewhere, which is the split
:mod:`ccf.peering.trust_policy` already makes against
:mod:`ccf.peering.admission`: the artifact a deployment declares, versions and
replays against is a different thing from the code that consults it, and
keeping them apart is what lets the entitlement be authored before any door
binds it.

It is a typed :class:`~ccf.contracts.base.CCFContract` modelled clause for
clause on :mod:`ccf.peering.trust_policy` — SDK-owned shape, deployment-owned
values — and the three properties that module argues for hold here for the
same reasons:

**Registering the wrong thing is a detectable error.** A bare mapping stored
under an entitlement key looks exactly like a correct one until a caller is
admitted against it. A typed class turns that into a validation failure at
registration, before anything can be served on it.

**Every artifact carries its own version lane.** ``policy_version`` is a
declared field with no default, validated through
:func:`~ccf.controlplane.artifact_base.validate_semver` — the one home of the
semver grammar, so the grammar cannot drift between modules. The lane is this
class's own and is never compared across artifact classes.

**Values stay out of code.** This module declares shape only. There is no
principal identifier here, no role name, no product-class name and no tenant —
every one of those is the deployment's statement about who its callers are, and
one the SDK invented would be one no examiner could trace to a decision anyone
made (CLAUDE.md §11, CINV-01; D-IMPL-38).

**A bypass is not expressible.** That ruling is structural here rather than
merely followed: **this contract has no field that could grant a principal a
product class or a role it was not declared, and none that could route a
principal around the lookup.** ``extra="forbid"`` closes the other direction — a
deployment cannot add one. What an entitlement can express is a narrower or a
wider *grant*, and a wider grant is still a declaration somebody authored and
somebody can read back. That claim is enforced by a field-enumeration test, not
by this paragraph; and it is the only claim of that strength this module makes.

**Why roles sit on the same grant as product classes.** Perspective resolution
at a door asks *which roles may this verified caller assert?*, and that is
answered by the same lookup, for the same subject, at the same moment as *may
this caller receive this class?*. Splitting them across two artifacts would
make a door resolve twice and let the two drift. What this module does **not**
touch is :class:`~ccf.projection.plan.Perspective` or the projection engine: a
door checks the grant and then constructs the perspective, and replay feeds the
*recorded* perspective rather than re-authenticating a principal who may no
longer exist.

Resolution is by pinned ``(key, version)`` through the existing Control Plane
registry, on the derivation :func:`product_entitlement_key` supplies.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.products.disclosure import DISCLOSURE_MINIMAL, DisclosureLevel
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver

__ccf_mode__ = "algorithmic"

__all__ = [
    "PRODUCT_ENTITLEMENT_POLICY",
    "PrincipalNotEntitled",
    "ProductEntitlementGrant",
    "ProductEntitlementPolicy",
    "ProductEntitlementViolation",
    "product_entitlement_key",
]


class ProductEntitlementViolation(LookupError):
    """A principal asked for something its entitlement entry does not cover.

    A :class:`LookupError` because that is literally what happened — the
    request was not found among the principal's entitlements. Raised rather
    than softened to a boolean at the resolution surfaces, so a delivery path
    cannot treat "not entitled" as "not sure".
    """


class PrincipalNotEntitled(ProductEntitlementViolation):
    """The policy names no entry for this principal at all.

    Distinct from a per-request refusal: an unconfigured principal is a caller
    the deployment never declared, not a caller overreaching a known grant, and
    an operator reading an audit log should not have to guess which they saw.
    """


class ProductEntitlementGrant(CCFContract):
    """What one principal may receive, and as whom.

    Three declared sets. The two that say what a principal may *receive* carry
    no default; the third, which says what it may *override*, defaults to the
    empty set. Empty means exactly what it says in every case — this principal
    may receive, or override, nothing of that kind — because a grant that
    quietly defaulted to "anything" would be the bypass this contract exists to
    make unreachable. The asymmetry is deliberate and runs the safe way: an
    author who forgets to state what may be received has stated nothing and
    must say so, while an author who says nothing about overrides has granted
    none (``D-IMPL-243`` then keeps every pre-existing policy's content address
    intact).

    Attributes:
        permitted_schema_names: The Context Product classes this principal may
            be served. Class names are the deployment's vocabulary; the SDK
            enumerates none of them.
        permitted_roles: The roles this principal may assert. A door resolves a
            requested role against this set *before* constructing a
            :class:`~ccf.projection.plan.Perspective`, so a caller cannot
            receive a view conditioned on a role nobody granted it. Both of
            that perspective's strings land verbatim in replay dimension 4,
            which is why the grant belongs upstream of it rather than inside
            it.
        overridable_policies: The policy identifiers this principal may ask to
            be resolved *without* (``D-IMPL-253`` Q7, Dave: *"Naming the policy
            is necessary but not sufficient authority to override it. The
            resolver must also establish that the caller/principal is entitled
            to exercise that override. Otherwise anyone who knows a policy ID
            could bypass it."*).

            **It is not a bypass and could not become one.** An entry here does
            not grant a class, a role, or a subject; it says only that *this*
            declared principal may exercise *that* declared exception, and the
            constraint artifact must itself declare
            :attr:`~ccf.controlplane.artifacts.PolicyConstraint.overridable`
            for the exception to exist at all. Two declarations, authored by
            two different people, and an override is honored only where they
            agree — while the attempt is recorded either way.

            The empty frozenset is the default and means what it says: this
            principal may override nothing. Hash-transparent at that value
            (``D-IMPL-243``), so every entitlement policy written before this
            field keeps its content address and therefore its pin.
        disclosure_level: This principal's own disclosure posture, overriding
            the policy's (``D-IMPL-253`` Q17; ``24.6-L-16``). ``None`` — the
            default — is the positive *this principal has no override*, so the
            tenant's :attr:`ProductEntitlementPolicy.disclosure_level` decides.

            **It is an override in both directions**, and deliberately so: a
            deployment may grant one reader ``full`` and hold another at
            ``minimal`` under the same tenant policy, which is exactly the
            information-barrier case ``D-IMPL-254`` names. What it cannot do is
            widen anything else — a level says what a reader may learn about a
            refusal it already received, never what it may receive.

            Hash-transparent at ``None`` (``D-IMPL-243``), so every grant
            written before this field keeps its content address.
    """

    permitted_schema_names: frozenset[str]
    permitted_roles: frozenset[str]
    overridable_policies: frozenset[str] = Field(
        default=frozenset(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    disclosure_level: DisclosureLevel | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    def require_schema(self, *, schema_name: str) -> None:
        """Raise unless this principal may be served that product class.

        Raises:
            ProductEntitlementViolation: the class is outside the grant.
        """
        if schema_name not in self.permitted_schema_names:
            raise ProductEntitlementViolation(
                f"this principal is not entitled to receive {schema_name!r}"
                f" products; its grant permits"
                f" {sorted(self.permitted_schema_names)!r}"
            )

    def require_role(self, *, role: str) -> None:
        """Raise unless this principal may assert that role.

        Raises:
            ProductEntitlementViolation: the role is outside the grant.
        """
        if role not in self.permitted_roles:
            raise ProductEntitlementViolation(
                f"this principal is not entitled to assert the role {role!r};"
                f" its grant permits {sorted(self.permitted_roles)!r}"
            )


class ProductEntitlementPolicy(CCFContract):
    """One tenant's product entitlements, as a versioned Control Plane artifact.

    Tenant-scoped by construction (D-IMPL-05): the tenant is a field on the
    artifact and part of its content, so two tenants naming the same principal
    hold two different artifacts with two different content addresses. One
    tenant's grant to a principal therefore cannot serve that principal under
    another — not by convention, but because there is no shared object for it
    to leak through.

    ``principals`` requires at least one entry: an empty policy is
    indistinguishable from a deployment that forgot to configure one, and
    registering it would let a door come up entitling nobody while looking
    configured.

    Attributes:
        tenant_id: The tenant this policy governs delivery for.
        policy_version: This artifact's own lane. No default — see the module
            docstring.
        principals: Principal identifier to its entitlements.
        disclosure_level: How much of a refusal's internal truth may cross this
            tenant's consumer boundary (``D-IMPL-253`` Q17, Dave: *"Suppression
            silence should be policy-controlled, with minimal disclosure as the
            safe default."*; ``24.6-L-16``). Interpreted by
            :func:`~ccf.products.disclosure.disclose`, which is the one step
            between the fabric's internal determination and the shell.

            The level lives **here** rather than in the adopter-owned ``policy``
            section because the SDK *interprets* it: a value the SDK reads has
            to sit in an SDK-owned, versioned artifact an examiner can resolve,
            or replay cannot say which posture was in force.

            Defaults to :data:`~ccf.products.disclosure.DISCLOSURE_MINIMAL` and
            is hash-transparent at it (``D-IMPL-243``), so every entitlement
            policy registered before this field keeps its content address — and
            a deployment that never thought about disclosure gets the safe
            posture rather than the permissive one.
    """

    tenant_id: str
    policy_version: str
    principals: Mapping[str, ProductEntitlementGrant] = Field(min_length=1)
    disclosure_level: DisclosureLevel = Field(
        default=DISCLOSURE_MINIMAL, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("policy_version")
    @classmethod
    def _version_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)

    def grant_for(self, *, principal_id: str) -> ProductEntitlementGrant:
        """Return ``principal_id``'s entitlements under this policy.

        Raises:
            PrincipalNotEntitled: this policy names no such principal. Never a
                permissive empty grant — an unconfigured principal is a
                deployment fact the delivery path must surface, not one it may
                interpret.
        """
        try:
            return self.principals[principal_id]
        except KeyError:
            raise PrincipalNotEntitled(
                f"no entitlement entry for principal {principal_id!r} under"
                f" tenant {self.tenant_id!r}"
            ) from None


#: The artifact class the registry validates entitlement policies against.
PRODUCT_ENTITLEMENT_POLICY = ArtifactClass(
    class_id="ccf.product-entitlement-policy", contract=ProductEntitlementPolicy
)


def product_entitlement_key(*, tenant_id: str) -> str:
    """Return the Control Plane key one tenant's entitlement policy registers under.

    A derivation rather than a table: the SDK supplies the shape of the key so
    two components cannot disagree about where a tenant's policy lives, and
    supplies no tenant, so it holds no deployment's vocabulary (CINV-01).
    """
    return f"{PRODUCT_ENTITLEMENT_POLICY.class_id}/{tenant_id}"
