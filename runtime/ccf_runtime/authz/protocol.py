"""The tenant-authorizer seam and its reference interpreter (HARD-04).

SDK-defined (CLAUDE.md §8.2/§8.3; D-IMPL-68; 10-CONTEXT D-05–D-10). Both
Experience-Layer HITL doors import this seam; neither implements
authorization of its own, and authorization never sinks below the door
trust boundary (the transport stays a pure queue — D-IMPL-68 ruling text).

Load-bearing behaviors of the reference interpreter:

**Deny-by-default (T-10-01).** No registered mapping, no scope in the
grant, no tenant-pattern match, no action-id match — each yields
``allowed=False``. An allow exists only where the artifact says so.

**Per-call re-resolution (D-07; T-10-02).** The scope-mapping artifact is
resolved from the Control Plane on every ``authorize()`` call — no cache,
no TTL — so a version change takes effect immediately and the *exact*
version string in force lands on the audit record (D-04).

**Both outcomes are audited (D-09/D-10; T-10-03).** Every decision —
allow and deny alike — appends one ``authz_decision`` event to the one
Control Plane audit log (WR-07), carrying the full decision tuple:
principal (``actor``), tenant (``key``), action id, decision, matched
pattern or ``None``, artifact version, injected timestamp.

Scope strings, tenant names, mapping keys, and clock values are all
deployment values supplied by the caller (CINV-01).

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
    tenant_pattern_matches,
)
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuthzDecision",
    "ControlPlaneTenantAuthorizer",
    "TenantAuthorizerProtocol",
]


class AuthzDecision(CCFContract):
    """One tenant-authorization verdict, complete enough to render and audit.

    Attributes:
        allowed: The verdict. ``False`` is the default posture; ``True``
            exists only where the scope mapping said so.
        matched_scope_pattern: The tenant pattern that granted the allow,
            or ``None`` when nothing matched (D-09).
        artifact_version: The exact scope-mapping artifact version in force
            at decision time (D-04) — the empty string when no mapping was
            registered at all, which is itself a deny.
        action_id: The door-declared action the decision concerned (D-02).
        tenant: The tenant the caller asked to act on.
    """

    allowed: bool
    matched_scope_pattern: str | None
    artifact_version: str
    action_id: str
    tenant: str


@runtime_checkable
class TenantAuthorizerProtocol(Protocol):
    """How a door asks whether a grant may act on a tenant.

    Protocol rather than a base class (CLAUDE.md §11): what "authorized"
    means is the deployment's statement — the doors have business only
    with the signature, and a deployment substitutes its own authorizer by
    conforming, never by subclassing.
    """

    def authorize(
        self, *, grant: TokenGrant, tenant: str, action_id: str
    ) -> AuthzDecision:
        """Return the decision for ``grant`` acting on ``tenant``."""
        ...


class ControlPlaneTenantAuthorizer:
    """Reference ``TenantAuthorizerProtocol`` over the Control Plane.

    Interprets the deployment's registered
    :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact` — resolved
    per call (D-07) — and audits every decision through the Control
    Plane's own log (WR-07: one audit plane; the GrantLedger precedent).

    Args:
        control_plane: The registry the scope mapping resolves from and
            whose ``audit_log`` every decision lands in. No default: which
            Control Plane governs a door is a composition decision.
        scope_mapping_key: The key the deployment registered its mapping
            under. No default: key names are deployment vocabulary
            (CINV-01).
        clock: Time source for audit timestamps. Injected, never read —
            the audit-module discipline.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneRegistry,
        scope_mapping_key: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._control_plane = control_plane
        self._scope_mapping_key = scope_mapping_key
        self._clock = clock

    def authorize(
        self, *, grant: TokenGrant, tenant: str, action_id: str
    ) -> AuthzDecision:
        """Decide, audit both outcomes, and return the decision.

        Raises:
            TypeError: the artifact registered under the mapping key is
                not a :class:`ScopeMappingArtifact` — a near-miss mapping
                is refused, never interpreted (the HitlPolicy precedent).
        """
        version = ""
        matched: str | None = None
        artifact: ScopeMappingArtifact | None = None
        try:
            version, resolved = self._control_plane.resolve_latest(
                self._scope_mapping_key
            )
        except ControlPlaneMissing:
            # No mapping registered is a deny, not an error: the default
            # posture grants nothing (T-10-01), and the deny is audited
            # below exactly as a matched-nothing deny would be.
            pass
        else:
            if not isinstance(resolved, ScopeMappingArtifact):
                raise TypeError(
                    f"artifact under {self._scope_mapping_key!r} is not a"
                    f" ScopeMappingArtifact (got"
                    f" {type(resolved).__name__}); the tenant authorizer"
                    " refuses to interpret a near-miss (D-03; D-IMPL-68)"
                )
            artifact = resolved
        if artifact is not None:
            for scope, entry in artifact.scopes.items():
                if scope not in grant.scopes:
                    continue
                if action_id not in entry.action_ids:
                    continue
                for pattern in entry.tenant_patterns:
                    if tenant_pattern_matches(pattern, tenant):
                        matched = pattern
                        break
                if matched is not None:
                    break
        decision = AuthzDecision(
            allowed=matched is not None,
            matched_scope_pattern=matched,
            artifact_version=version,
            action_id=action_id,
            tenant=tenant,
        )
        self._control_plane.audit_log.append(
            action="authz_decision",
            key=tenant,
            version=version,
            resolved=decision.allowed,
            occurred_at=self._clock(),
            actor=grant.client_id,
            artifact_class=SCOPE_MAPPING.class_id,
            authz_action_id=action_id,
            authz_matched_pattern=matched,
        )
        return decision
