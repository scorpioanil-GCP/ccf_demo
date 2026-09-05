"""``P`` at delivery: one definition of *entitled*, for every exposed door.

SDK-defined extension (CLAUDE.md §7.1, §8.3). Plan ``15.5-03`` shipped the
*artifact* — :mod:`ccf.products.entitlement`, a tenant's declaration of which
Context Product classes each principal may receive and which roles it may
assert. This module is the *door* half: the seams an exposed product door
holds, the reference source that resolves that artifact per call and audits
every decision, and the one resolution order all three doors run.

**Why this lives in a third module rather than in one of the doors.** The
tree exposes the same three-string product signature at three places — the
fabric-internal MCP egress resource, the Experience front-door resource, and
the HTTP ``GET /product/...`` route. Three doors that disagreed about what
"entitled" means is the drift ``run_gates``/``run_federated_gates`` share
their comparison functions specifically to prevent. But the doors may not
import each other either:
``tests/invariants/test_mcp_role_separation.py`` asserts that the MCP roles
are separate modules importing none of their siblings, so that the
authenticated one is never one decorator away from the anonymous one. The
resolution is the one :mod:`ccf_runtime.authz.protocol` already models for
the two HITL doors — a shared seam in a package neither door owns, imported
by both, owned by neither.

**Entitlement is checked after authentication, never instead of it**
(:mod:`ccf.peering.trust_policy`'s posture at the federated boundary,
transplanted to the local one). Every entry point here takes an
already-verified :class:`~ccf_runtime.mcp.auth.TokenGrant`; nothing in this
module verifies a credential, and nothing here accepts a caller-supplied
principal.

**The seams are required at the MCP doors, not optional-and-inert.**
``hitl.py``'s ``_enforce_tenant_authz`` is inert when no authorizer is bound
because it retrofits authorization onto a door that had already shipped. The
product doors are receiving their *first* governance, so an optional seam
would ship the exact gap ``docs/CONTEXT_PRODUCT_REVISION.md`` §11.2 measured
— a door that answers everyone — and would make deny-by-default a
deployment's choice rather than the SDK's.

**Both outcomes are audited (D-09/D-10).** The reference source appends one
``authz_decision`` event per decision to the one Control Plane audit log,
carrying the verified principal, the tenant, the declared action id
(:data:`~ccf_runtime.authz.refusals.ACTION_PRODUCT_RETRIEVE`) and the exact
policy version in force — which is only exact because the artifact is
**re-resolved on every call, with no cache and no TTL** (D-07;
:class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer`'s posture).

**The role is decided, never asserted (T-15.5-19).** A caller may *request*
a role; the deployment's :class:`PerspectiveResolverProtocol` proposes one
from the verified grant; and the entitlement decides. The resolved
perspective's role — not the requested one — is what
:meth:`~ccf.products.entitlement.ProductEntitlementGrant.require_role` is
asked about, so a resolver that ignores its argument cannot mint a view
nobody granted. The resolved perspective's ``principal_id`` must equal the
verified ``client_id`` for the same reason it does on the HITL door
(D-IMPL-67): both strings land verbatim in replay dimension 4, and a record
naming someone who never called is worse than no record.

**Nothing sinks below the door.** :meth:`ProjectionEngine.execute` still
takes an already-resolved :class:`~ccf.projection.plan.Perspective` and
learns nothing about who asked; replay feeds the *recorded* perspective and
never re-resolves one, so a decision replays even after its principal is
gone. ``tests/invariants/test_mcp_role_separation.py`` asserts both
structurally.

Principal identifiers, role names, tenant names, product-class names and
policy keys are all deployment values carried on the wire or in the
artifact. This module holds none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Protocol, runtime_checkable

from mcp.server.auth.middleware.auth_context import get_access_token

from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
from ccf.products.disclosure import DISCLOSURE_MINIMAL, DisclosureLevel
from ccf.products.provenance import ProvenanceSource
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    PrincipalNotEntitled,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    ProductEntitlementViolation,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf_runtime.authz.refusals import ACTION_PRODUCT_RETRIEVE
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
    ERROR_PRODUCT_POLICY_ABSENT,
    ERROR_PRODUCT_ROLE_UNGRANTED,
    ERROR_SUBJECT_CONFLICT,
    refusal_detail,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "ControlPlaneProductEntitlementSource",
    "PerspectiveResolverProtocol",
    "ProductEntitlementRefused",
    "ProductEntitlementSourceProtocol",
    "UnverifiedProductCallerRefused",
    "entitled_perspective",
    "verified_grant",
]


class ProductEntitlementRefused(ProductEntitlementViolation):
    """A door refused a verified caller, with the typed code for the refusal.

    Subclasses the artifact's own
    :class:`~ccf.products.entitlement.ProductEntitlementViolation` so a
    deployment catching the artifact's type catches the door's too, and
    carries :attr:`error_code` so each door can render the *same* decision in
    its own protocol — a typed 403 body on HTTP, a protocol-native error on
    MCP — without either inventing a string (D-08, the one-vocabulary /
    two-renderings posture the HITL doors already hold).

    ``str(...)`` is the one refusal-body shape
    (:func:`~ccf_runtime.http_api.errors.refusal_detail`) rendered as JSON, so
    the MCP rendering is machine-attributable without a second contract.
    """

    def __init__(self, *, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(
            json.dumps(
                refusal_detail(error_code=error_code, message=message)
            )
        )


class UnverifiedProductCallerRefused(RuntimeError):
    """No verified access token accompanies the in-flight product call.

    The D-26 auth middleware should make this unreachable — every door that
    calls :func:`verified_grant` is authenticated by construction — but the
    door refuses rather than falling back to an anonymous read when the
    precondition fails. The counterpart of
    :class:`~ccf_runtime.mcp.hitl_server.UnverifiedCallerRefused` on the
    product surfaces.
    """


@runtime_checkable
class PerspectiveResolverProtocol(Protocol):
    """How a door turns a verified grant into a Π role-conditioning tuple.

    Protocol rather than a base class (CLAUDE.md §11), on
    :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`'s own reasoning:
    which role a verified caller holds is the deployment's statement about
    its own identity substrate, and the SDK has no business owning its shape
    — only its signature. Keyword-only for the same reason that seam is, so
    the arguments cannot be transposed.

    The resolver **proposes**; it does not decide. Whatever
    :class:`~ccf.projection.plan.Perspective` it returns is checked against
    the principal's entitlement grant before any product is served, so a
    resolver cannot widen what the deployment declared.
    """

    def __call__(
        self, *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Return the perspective ``grant`` may be conditioned under.

        Args:
            grant: The verified caller identity. Never a caller's claim.
            tenant: The tenant the product is addressed under.
            requested_role: The role the caller asked for, or ``None`` when
                the surface carries no way to ask — the MCP product URIs
                have three segments and no role among them, so on those
                doors the resolver derives the role from ``grant`` alone.
                There is no SDK default: a role the SDK invented would be
                one no examiner could trace to a decision anyone made.
        """
        ...


@runtime_checkable
class ProductEntitlementSourceProtocol(Protocol):
    """How a door asks whether a verified caller may receive a class, as whom.

    Protocol rather than a base class (CLAUDE.md §11) on the same terms as
    :class:`~ccf_runtime.authz.protocol.TenantAuthorizerProtocol`: what
    "entitled" means is the deployment's statement, and the doors have
    business only with the signature.
    """

    def authorize(
        self, *, grant: TokenGrant, tenant: str, product_class: str, role: str
    ) -> ProductEntitlementGrant:
        """Return the caller's grant, or raise; audit either way.

        Raising rather than returning a verdict is the artifact's own
        posture, carried up to the door: a delivery path must not be able to
        treat "not entitled" as "not sure".

        Raises:
            ProductEntitlementRefused: the caller is not entitled to that
                class, or not to that role, or is not declared at all, or
                the tenant declares no policy.
        """
        ...


class ControlPlaneProductEntitlementSource:
    """Reference :class:`ProductEntitlementSourceProtocol` over the Control Plane.

    Resolves the tenant's
    :class:`~ccf.products.entitlement.ProductEntitlementPolicy` under
    :func:`~ccf.products.entitlement.product_entitlement_key` — **per call,
    no cache, no TTL** (D-07) — runs the artifact's two raising checks, and
    appends one ``authz_decision`` event per decision to the Control Plane's
    own audit log (WR-07: one audit plane).

    Args:
        control_plane: The registry the policy resolves from and whose
            ``audit_log`` every decision lands in. No default: which Control
            Plane governs a door is a composition decision.
        clock: Time source for audit timestamps. Injected, never read — the
            audit-module discipline.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneRegistry,
        clock: Callable[[], datetime],
    ) -> None:
        self._control_plane = control_plane
        self._clock = clock

    def _audit(
        self, *, grant: TokenGrant, tenant: str, version: str, allowed: bool
    ) -> None:
        """Append the one ``authz_decision`` event this decision produces."""
        self._control_plane.audit_log.append(
            action="authz_decision",
            key=tenant,
            version=version,
            resolved=allowed,
            occurred_at=self._clock(),
            actor=grant.client_id,
            artifact_class=PRODUCT_ENTITLEMENT_POLICY.class_id,
            authz_action_id=ACTION_PRODUCT_RETRIEVE,
            authz_matched_pattern=None,
        )

    def authorize(
        self, *, grant: TokenGrant, tenant: str, product_class: str, role: str
    ) -> ProductEntitlementGrant:
        """Decide, audit both outcomes, and return the grant or raise.

        Raises:
            ProductEntitlementRefused: any of the four deny paths.
            TypeError: the artifact registered under the tenant's
                entitlement key is not a ``ProductEntitlementPolicy``, **or is
                one whose own ``tenant_id`` is not the tenant whose key it was
                found under** — a near-miss is refused, never interpreted (the
                ``ControlPlaneTenantAuthorizer`` precedent). The attempt is
                audited as a deny *before* the raise (WR-04), so even a
                misregistered policy leaves a trace of who asked for what.

                The second limb is what makes
                :class:`~ccf.products.entitlement.ProductEntitlementPolicy`'s
                *"tenant-scoped by construction"* claim true at the door
                rather than at the artifact only. The key
                (:func:`~ccf.products.entitlement.product_entitlement_key`)
                and the artifact's ``tenant_id`` field are supplied
                **independently** by whoever registers the policy, and nothing
                upstream binds them; without this check a policy whose content
                says tenant B, registered under tenant A's key, authorizes
                A's door with B's grants. Found by the Phase 15.5 close-time
                cross-AI panel (`15.5-CLOSE-REVIEWS.md`, finding P1).
        """
        key = product_entitlement_key(tenant_id=tenant)
        version = ""
        entitled: ProductEntitlementGrant | None = None
        refusal: ProductEntitlementRefused | None = None
        try:
            version, resolved = self._control_plane.resolve_latest(key)
        except ControlPlaneMissing:
            # No policy registered is a deny, not an error: the default
            # posture grants nothing, and a door whose governance
            # configuration is absent must not become servable.
            refusal = ProductEntitlementRefused(
                error_code=ERROR_PRODUCT_POLICY_ABSENT,
                message=(
                    f"no product entitlement policy is registered under"
                    f" {key!r}; a delivery door with no policy in force"
                    " refuses rather than serves (deny-by-default)"
                ),
            )
        else:
            if not isinstance(resolved, ProductEntitlementPolicy):
                self._audit(
                    grant=grant, tenant=tenant, version=version, allowed=False
                )
                raise TypeError(
                    f"artifact under {key!r} is not a"
                    f" ProductEntitlementPolicy (got"
                    f" {type(resolved).__name__}); the delivery door refuses"
                    " to interpret a near-miss"
                )
            if resolved.tenant_id != tenant:
                self._audit(
                    grant=grant, tenant=tenant, version=version, allowed=False
                )
                raise TypeError(
                    f"policy under {key!r} declares tenant"
                    f" {resolved.tenant_id!r}, not {tenant!r}; the key and the"
                    " artifact's own tenant are supplied independently, so the"
                    " door compares them rather than trusting the lookup — a"
                    " misregistered policy is a near-miss and is refused, never"
                    " interpreted"
                )
            try:
                entitled = resolved.grant_for(principal_id=grant.client_id)
            except PrincipalNotEntitled as absent:
                refusal = ProductEntitlementRefused(
                    error_code=ERROR_PRINCIPAL_NOT_ENTITLED,
                    message=str(absent),
                )
            else:
                try:
                    entitled.require_schema(schema_name=product_class)
                except ProductEntitlementViolation as violation:
                    refusal = ProductEntitlementRefused(
                        error_code=ERROR_PRODUCT_CLASS_UNENTITLED,
                        message=str(violation),
                    )
                else:
                    try:
                        entitled.require_role(role=role)
                    except ProductEntitlementViolation as violation:
                        refusal = ProductEntitlementRefused(
                            error_code=ERROR_PRODUCT_ROLE_UNGRANTED,
                            message=str(violation),
                        )
        self._audit(
            grant=grant,
            tenant=tenant,
            version=version,
            allowed=refusal is None,
        )
        if refusal is not None:
            raise refusal
        if entitled is None:  # pragma: no cover - unreachable by construction
            raise ProductEntitlementRefused(
                error_code=ERROR_PRODUCT_POLICY_ABSENT,
                message="no grant resolved and no refusal raised",
            )
        return entitled

    def disclosure_level_for(
        self, *, tenant: str, principal_id: str
    ) -> tuple[DisclosureLevel, ProvenanceSource | None]:
        """The disclosure posture in force for one principal, with its pin.

        ``24.6-L-16``; ``D-IMPL-253`` Q17, Dave: *"Suppression silence should be
        policy-controlled, with minimal disclosure as the safe default."*

        Three answers and one order: the principal's own grant override if it
        declares one, else the tenant policy's level, else
        :data:`~ccf.products.disclosure.DISCLOSURE_MINIMAL` with a ``None``
        source — *no policy is registered, so the safe default applied*, which
        is a claim rather than a silence.

        **A different question from** :meth:`authorize`, asked of the same
        artifact. That one decides whether the caller may receive the class;
        this one decides how much of a refusal's internal truth may cross. Both
        pins land in replay dimension 2 when both exist, and they can name
        different tenants: a denial is decided under the tenant the caller
        addressed, while the level is read under the tenant whose door is
        answering.

        Resolved **per call, no cache, no TTL**, exactly as :meth:`authorize`
        resolves the same artifact (D-07).

        Args:
            tenant: The tenant whose policy sets the posture.
            principal_id: The verified caller, for the per-grant override.

        Returns:
            The level and the artifact source that set it, or the safe default
            with ``None``.

        Raises:
            TypeError: the artifact under the tenant's key is not a
                ``ProductEntitlementPolicy``, or declares a different tenant.
                A near-miss is refused and never interpreted — disclosing under
                another tenant's policy is the elevation the tenant-scoped key
                exists to prevent (``T-24.6-29``).
        """
        key = product_entitlement_key(tenant_id=tenant)
        try:
            version, resolved = self._control_plane.resolve_latest(key)
        except ControlPlaneMissing:
            return DISCLOSURE_MINIMAL, None
        if not isinstance(resolved, ProductEntitlementPolicy):
            raise TypeError(
                f"artifact under {key!r} is not a ProductEntitlementPolicy"
                f" (got {type(resolved).__name__}); the disclosure level is"
                " read from the tenant's own entitlement policy and the door"
                " refuses to interpret a near-miss"
            )
        if resolved.tenant_id != tenant:
            raise TypeError(
                f"policy under {key!r} declares tenant {resolved.tenant_id!r},"
                f" not {tenant!r}; the key and the artifact's own tenant are"
                " supplied independently, so the door compares them rather"
                " than trusting the lookup"
            )
        source = ProvenanceSource(kind="artifact", identity=key, version=version)
        grant = resolved.principals.get(principal_id)
        if grant is not None and grant.disclosure_level is not None:
            return grant.disclosure_level, source
        return resolved.disclosure_level, source


def verified_grant() -> TokenGrant:
    """The in-flight caller's verified identity, or refuse.

    The A1 spike verdict (``tests/crossproc/test_fastmcp_resource_token_
    spike.py``) is what makes this usable inside an MCP **resource** handler
    and not only inside a tool: ``get_access_token()`` is populated for
    resource reads on an authenticated ``FastMCP`` instance. Both product
    resources rely on that, exactly as the HITL queue resource already does.

    Raises:
        UnverifiedProductCallerRefused: no verified token in context.
    """
    token = get_access_token()
    if token is None:
        raise UnverifiedProductCallerRefused(
            "no verified access token accompanies this call; an entitled"
            " product surface decides on verified identities only (D-26)"
        )
    return TokenGrant(client_id=token.client_id, scopes=tuple(token.scopes))


def entitled_perspective(
    *,
    grant: TokenGrant,
    tenant: str,
    product_class: str,
    requested_role: str | None,
    entitlement_source: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
) -> Perspective:
    """The one resolution order every exposed product door runs.

    Order, and the order *is* the security property:

    1. The caller is already authenticated — this function takes a verified
       grant and cannot be handed a claim.
    2. The deployment's resolver proposes a perspective from that grant. A
       pure derivation: no fabric is touched and no product is assembled, so
       proposing is not receiving.
    3. The proposed subject must be the verified subject (D-IMPL-67).
    4. The entitlement decides — on the **resolved** role, so a resolver
       that ignored ``requested_role`` cannot widen the grant, and on the
       requested class, so ``P`` applies per class at delivery.
    5. Only then may the caller's door resolve a product.

    Args:
        grant: The verified caller identity.
        tenant: The tenant the product is addressed under.
        product_class: The Context Product class being requested.
        requested_role: The role the caller asked for, or ``None`` on a
            surface with no way to ask.
        entitlement_source: The deployment's entitlement decision seam.
        perspective_resolver: The deployment's role-derivation seam.

    Returns:
        The perspective the caller is entitled to be conditioned under.

    Raises:
        ProductEntitlementRefused: the subject conflicts with the verified
            identity, or the entitlement refused the class or the role.
    """
    perspective = perspective_resolver(
        grant=grant, tenant=tenant, requested_role=requested_role
    )
    if perspective.principal_id != grant.client_id:
        raise ProductEntitlementRefused(
            error_code=ERROR_SUBJECT_CONFLICT,
            message=(
                "identity conflict: the resolved perspective's principal"
                " does not match the verified caller identity; the"
                " conditioned subject is derived from the verified grant,"
                " never substituted (D-IMPL-67; D-IMPL-21)"
            ),
        )
    entitlement_source.authorize(
        grant=grant,
        tenant=tenant,
        product_class=product_class,
        role=perspective.role,
    )
    return perspective
