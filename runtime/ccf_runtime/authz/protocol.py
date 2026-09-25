"""The tenant-authorizer seam and its reference interpreter (HARD-04).

SDK-defined (CLAUDE.md §8.2/§8.3; D-IMPL-68; 10-CONTEXT D-05–D-10). Both
Experience-Layer HITL doors import this seam; neither implements
authorization of its own, and authorization never sinks below the door
trust boundary (the transport stays a pure queue — D-IMPL-68 ruling text).

Load-bearing behaviors of the reference interpreter:

**Deny-by-default (T-10-01).** No resolvable mapping, no scope in the
grant, no tenant-pattern match, no action-id match, no resource-pattern match
— each yields ``allowed=False``. An allow exists only where the artifact says
so, on **all four** axes.

**The fourth axis is the resource (``SEC-002``).** A decision is about
``(grant, tenant, action, resource)``. Deciding on the first three answers
*who counts as recognized*, which leaves the finding's stated harm — *any
recognized bearer can rewrite the prompt artifact an underwriting agent runs
on* — intact in the form *any bearer holding the register action can rewrite
it*. The resource is the thing being acted on: the Control Plane key, the
content address, the product class, or the door's own action id for a door
that acts on no addressable subject. Where it comes from is declared at each
route (:mod:`ccf_runtime.authz.route_declaration`), never chosen per request.

**The mapping version is PINNED at construction, and per-call re-resolution
of "latest" is gone (``SEC-002``; supersedes D-07 for this class).** D-07 read
the mapping with ``resolve_latest`` on every call so a policy change took
effect at once. Measured against the finding, that is a privilege-escalation
edge: registration is last-registered-wins, so a bearer able to register
Control Plane artifacts could re-issue the very scope mapping that authorizes
it and have the new version in force on its next request. The authorizer now
resolves **one exact version**, fixed when the authorizer is constructed,
through :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.resolve` — the
same ``resolve_latest`` ban replay has always held (``D-IMPL-26``).

*The cost is stated rather than hidden*: rotating a scope mapping is now a
re-construction of the authorizer — a redeploy or a rebind — instead of a
registration. That is the correct direction for a policy artifact whose whole
job is to constrain the people who can write artifacts. Resolution is still
**per call and uncached**: what is pinned is *which version*, not *when it is
read*, so a Control Plane that can no longer resolve the pinned version denies
rather than serving a remembered copy.

**Both outcomes are audited (D-09/D-10; T-10-03).** Every decision —
allow and deny alike — appends one ``authz_decision`` event to the one
Control Plane audit log (WR-07), carrying the decision tuple: principal
(``actor``), tenant (``key``), action id, decision, matched tenant pattern or
``None``, artifact version, injected timestamp. The **resource** and the
resource pattern that matched are on :class:`AuthzDecision` but are not yet on
the audit event: that contract is :class:`~ccf.controlplane.audit
.AuthzDecisionAuditEvent` in ``/src``, and widening it is a change outside
this module's tree. Recorded here so the gap is visible where it is caused.

Scope strings, tenant names, resource names, mapping keys, and clock values
are all deployment values supplied by the caller (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeMappingArtifact,
    pattern_matches,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuthzDecision",
    "ControlPlaneTenantAuthorizer",
    "TenantAuthorizerProtocol",
]


from ccf.authz.decision import AuthzDecision  # relocated: D-IMPL-353, D-29


@runtime_checkable
class TenantAuthorizerProtocol(Protocol):
    """How a door asks whether a grant may act on a tenant's resource.

    Protocol rather than a base class (CLAUDE.md §11): what "authorized"
    means is the deployment's statement — the doors have business only
    with the signature, and a deployment substitutes its own authorizer by
    conforming, never by subclassing.

    **The SDK ships exactly one implementation and it is deny-by-default.**
    There is deliberately no permissive, dev, or allow-all authorizer anywhere
    in the SDK — not behind a flag, not under a ``dev`` name, not in a
    ``testing`` module — because a shipped one is a shipped one and the
    argument for reaching for it at 2am is always available. A test that needs
    a stub writes the conforming object in the test file, where a reader can
    see it, rather than importing a permissive posture from the library.
    ``tests/authz/test_no_permissive_authorizer_ships.py`` holds that claim by
    running every authorizer the package exports against an empty Control
    Plane and asserting it denies.
    """

    def authorize(
        self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str
    ) -> AuthzDecision:
        """Return the decision for ``grant`` acting on ``tenant``'s resource."""
        ...


class ControlPlaneTenantAuthorizer:
    """Reference ``TenantAuthorizerProtocol`` over the Control Plane.

    Interprets the deployment's registered
    :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact` — at the
    **pinned version** this authorizer was constructed against — and audits
    every decision through the Control Plane's own log (WR-07: one audit
    plane; the GrantLedger precedent).

    Args:
        control_plane: The registry the scope mapping resolves from and
            whose ``audit_log`` every decision lands in. No default: which
            Control Plane governs a door is a composition decision.
        scope_mapping_key: The key the deployment registered its mapping
            under. No default: key names are deployment vocabulary
            (CINV-01).
        scope_mapping_version: The **exact** version to decide under. No
            default, and no ``latest`` sentinel: a default would be
            last-registered-wins by another spelling, which is the escalation
            this parameter exists to close (``SEC-002``). The value is the
            version string
            :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_typed`
            returned for the mapping the operator intends to be in force.
        clock: Time source for audit timestamps. Injected, never read —
            the audit-module discipline.

    Raises:
        ValueError: ``scope_mapping_key`` or ``scope_mapping_version`` is
            empty. An empty pin is not a pin, and it would be discovered on
            the first request rather than at the composition root.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneRegistry,
        scope_mapping_key: str,
        scope_mapping_version: str,
        clock: Callable[[], datetime],
    ) -> None:
        if not scope_mapping_key:
            raise ValueError(
                "an authorizer needs the key its scope mapping is registered"
                " under; the empty string names no artifact and would deny"
                " every request for a reason no operator could read"
            )
        if not scope_mapping_version:
            raise ValueError(
                "an authorizer decides under ONE exact scope-mapping version"
                " and there is no default for it: resolving whatever was"
                " registered most recently lets a bearer who can register"
                " Control Plane artifacts re-issue the policy that authorizes"
                " it (SEC-002). Pass the version register_typed returned"
            )
        self._control_plane = control_plane
        self._scope_mapping_key = scope_mapping_key
        self._scope_mapping_version = scope_mapping_version
        self._clock = clock

    @property
    def scope_mapping_version(self) -> str:
        """The exact version every decision of this authorizer is made under."""
        return self._scope_mapping_version

    def authorize(
        self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str
    ) -> AuthzDecision:
        """Decide on all four axes, audit both outcomes, and return.

        Raises:
            TypeError: the artifact registered under the mapping key at the
                pinned version is not a
                :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact` — a
                near-miss mapping is refused, never interpreted (the
                HitlPolicy precedent). The attempt is audited as a deny
                *before* the raise (WR-04): even a misregistered mapping
                leaves an ``authz_decision`` trace of who asked for what.
        """
        version = self._scope_mapping_version
        matched_tenant: str | None = None
        matched_resource: str | None = None
        artifact: ScopeMappingArtifact | None = None
        try:
            # `resolve`, never `resolve_latest` (SEC-002; the D-IMPL-26 replay
            # precedent). Still read on every call — what is pinned is which
            # version, not when it is read — so a mapping that has become
            # unresolvable denies instead of serving a remembered copy.
            resolved = self._control_plane.resolve(
                self._scope_mapping_key, version
            )
        except ControlPlaneMissing:
            # Nothing at the pinned version is a deny, not an error: the
            # default posture grants nothing (T-10-01), and the deny is
            # audited below exactly as a matched-nothing deny would be.
            pass
        else:
            if not isinstance(resolved, ScopeMappingArtifact):
                # WR-04: the *attempt* is audited before the wiring error
                # surfaces — "every decision, allow and deny alike" would
                # otherwise have a hole exactly in the misconfiguration
                # window an examiner cares about.
                self._audit(
                    grant=grant,
                    tenant=tenant,
                    version=version,
                    allowed=False,
                    action_id=action_id,
                    matched=None,
                )
                raise TypeError(
                    f"artifact under {self._scope_mapping_key!r} at version"
                    f" {version!r} is not a ScopeMappingArtifact (got"
                    f" {type(resolved).__name__}); the authorizer refuses to"
                    " interpret a near-miss (D-03; D-IMPL-68)"
                )
            artifact = resolved
        if artifact is not None:
            matched_tenant, matched_resource = self._match(
                artifact=artifact,
                grant=grant,
                tenant=tenant,
                action_id=action_id,
                resource=resource,
            )
        allowed = matched_tenant is not None and matched_resource is not None
        decision = AuthzDecision(
            allowed=allowed,
            matched_scope_pattern=matched_tenant,
            matched_resource_pattern=matched_resource,
            artifact_version=version,
            action_id=action_id,
            tenant=tenant,
            resource=resource,
        )
        self._audit(
            grant=grant,
            tenant=tenant,
            version=version,
            allowed=allowed,
            action_id=action_id,
            matched=matched_tenant,
        )
        return decision

    @staticmethod
    def _match(
        *,
        artifact: ScopeMappingArtifact,
        grant: TokenGrant,
        tenant: str,
        action_id: str,
        resource: str,
    ) -> tuple[str | None, str | None]:
        """The tenant and resource patterns that jointly allow, or two ``None``s.

        **One scope entry has to satisfy every axis.** Returning the first
        tenant match and the first resource match found across *different*
        entries would let two narrow grants compose into a wide one — scope A
        reaching tenant X for any resource, scope B reaching resource Y for
        any tenant, and the pair authorizing X×Y that neither states. So the
        search returns only where one entry matched on its own, and an entry
        that matches the tenant but not the resource contributes nothing.
        """
        for scope, entry in artifact.scopes.items():
            if scope not in grant.scopes:
                continue
            if action_id not in entry.action_ids:
                continue
            tenant_hit = next(
                (
                    pattern
                    for pattern in entry.tenant_patterns
                    if pattern_matches(pattern, tenant)
                ),
                None,
            )
            if tenant_hit is None:
                continue
            resource_hit = next(
                (
                    pattern
                    for pattern in entry.resource_patterns
                    if pattern_matches(pattern, resource)
                ),
                None,
            )
            if resource_hit is None:
                continue
            return tenant_hit, resource_hit
        return None, None

    def _audit(
        self,
        *,
        grant: TokenGrant,
        tenant: str,
        version: str,
        allowed: bool,
        action_id: str,
        matched: str | None,
    ) -> None:
        """Append the one ``authz_decision`` event this decision produces."""
        self._control_plane.audit_log.append(
            action="authz_decision",
            key=tenant,
            version=version,
            resolved=allowed,
            occurred_at=self._clock(),
            actor=grant.client_id,
            artifact_class=SCOPE_MAPPING.class_id,
            authz_action_id=action_id,
            authz_matched_pattern=matched,
        )
