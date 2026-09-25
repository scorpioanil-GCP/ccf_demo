"""``AuthzDecision`` — one authorization verdict, complete enough to render and audit.

Relocated from ``ccf_runtime.authz.protocol`` under D-IMPL-353 (D-29: the
capability that consumes it lives in ``src/``). The Protocol that PRODUCES
decisions stays in ``runtime/``; this is the data it produces.
"""

from __future__ import annotations

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

__ccf_mode__ = "algorithmic"

__all__ = ["AuthzDecision"]


class AuthzDecision(CCFContract):
    """One authorization verdict, complete enough to render and audit.

    Attributes:
        allowed: The verdict. ``False`` is the default posture; ``True``
            exists only where the scope mapping said so on every axis.
        matched_scope_pattern: The tenant pattern that granted the allow,
            or ``None`` when nothing matched (D-09).
        matched_resource_pattern: The resource pattern that granted the
            allow, or ``None`` when nothing matched (``SEC-002``). Separate
            from the tenant pattern rather than folded into it: an examiner
            asking *which rule let this through* needs both halves, and a
            single concatenated string is a value nothing can filter on.
        artifact_version: The exact scope-mapping artifact version the
            decision was made under (D-04). Always the authorizer's pin, and
            present even on the deny that follows an unresolvable pin — a
            deny whose version were blank would be indistinguishable from a
            deny under a mapping that simply said no.
        action_id: The door-declared action the decision concerned (D-02).
        tenant: The tenant the decision was made under — selected from the
            **verified grant's** set, never a tenant the caller named
            (:mod:`ccf_runtime.authz.tenancy`).
        resource: The thing the action was to be performed on.
        decision_id: The content address of the ``authz_decision`` audit
            event recording this decision (D-IMPL-353 §1.5a). The SDK's
            authorizer **always** supplies it, allow and deny alike; the
            field is optional-typed only so a decision can be constructed
            where no log exists (the capability seam's own tests). **A gate
            mints no capability from an allow that carries none**: an allow
            with no record is an allow nothing can be traced to, and the
            HTTP gate refuses the request as a deployment fault rather than
            minting an untraceable authority.
    """

    allowed: bool
    matched_scope_pattern: str | None
    matched_resource_pattern: str | None
    artifact_version: str
    action_id: str
    tenant: str
    resource: str
    #: ``True`` — hash-transparent at the sentinel (``D-IMPL-243``): a decision
    #: built with no id renders as the pre-D-IMPL-353 contract did; a real id
    #: is a real claim and is rendered.
    decision_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

