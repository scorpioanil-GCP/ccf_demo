"""Typed refusal error-code constants for the HTTP front door (08-02).

SDK-defined (CLAUDE.md §8.3). Closes the Ollama MEDIUM finding from the
Phase 7 gap-cycle reviews (07-REVIEWS rounds 2-3): refusal responses carry
a machine-readable ``error_code`` whose values are the named constants
below, so no client or test ever parses refusal prose. Every refusal body
emitted by the auth composition is the shape produced by
:func:`refusal_detail` — ``{"error_code": <constant>, "message": <prose>}``
— where the prose is human context and the code is the contract.

The values are **stable API surface**: renaming a value is a breaking
change to every consumer, so each constant documents what it means in one
line. ``ERROR_SIGNED_BINDING_REQUIRED`` and ``ERROR_SIGNED_BINDING_INVALID``
are exported now, ahead of the refusal branches that emit them (08-03's
signed-binding door mapping), so later plans and examples never invent
strings.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Final

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERROR_INVALID_GRANT",
    "ERROR_PRINCIPAL_NOT_ENTITLED",
    "ERROR_PRODUCT_CLASS_UNENTITLED",
    "ERROR_PRODUCT_POLICY_ABSENT",
    "ERROR_PRODUCT_ROLE_UNGRANTED",
    "ERROR_SIGNED_BINDING_INVALID",
    "ERROR_SIGNED_BINDING_REQUIRED",
    "ERROR_SUBJECT_CONFLICT",
    "ERROR_TENANT_UNAUTHORIZED",
    "ERROR_UNAUTHENTICATED",
    "refusal_detail",
]

#: The request carried no credential the bound auth hook recognises (401).
ERROR_UNAUTHENTICATED: Final[str] = "unauthenticated"

#: The body principal's subject conflicts with the verified caller
#: identity (403; D-IMPL-67/21 — the audited subject is derived, never
#: the caller's claim).
ERROR_SUBJECT_CONFLICT: Final[str] = "subject-conflict"

#: The stashed grant object is not a ``TokenGrant`` — a fail-closed
#: refusal (403): the caller-supplied principal is never used as the
#: fallback (Codex fail-closed finding, 07-REVIEWS round 2).
ERROR_INVALID_GRANT: Final[str] = "invalid-grant"

#: A signed principal binding is required by the door and absent
#: (reserved for 08-03's signed-binding door mapping).
ERROR_SIGNED_BINDING_REQUIRED: Final[str] = "signed-binding-required"

#: A signed principal binding was presented and failed verification
#: (reserved for 08-03's signed-binding door mapping).
ERROR_SIGNED_BINDING_INVALID: Final[str] = "signed-binding-invalid"

#: The authenticated caller's grant does not authorize this tenant ×
#: action under the scope mapping in force (403; HARD-04; D-IMPL-68 —
#: deny-by-default at the doors, one code for both renderings, D-08).
ERROR_TENANT_UNAUTHORIZED: Final[str] = "tenant-unauthorized"

#: The tenant has no registered ``ccf.product-entitlement-policy`` at all
#: (403; 15.5-06). A deny rather than an error: a door whose governance
#: configuration is absent must refuse, never answer everyone.
ERROR_PRODUCT_POLICY_ABSENT: Final[str] = "product-policy-absent"

#: The tenant's entitlement policy names no entry for the verified
#: principal (403; 15.5-06). Distinct from a per-request refusal: an
#: unconfigured principal is a caller the deployment never declared, not one
#: overreaching a known grant, and an operator reading a refusal should not
#: have to guess which they saw.
ERROR_PRINCIPAL_NOT_ENTITLED: Final[str] = "principal-not-entitled"

#: The verified principal's grant does not permit the requested Context
#: Product class (403; 15.5-06 — ``P`` applied at delivery).
ERROR_PRODUCT_CLASS_UNENTITLED: Final[str] = "product-class-unentitled"

#: The role the resolved :class:`~ccf.projection.plan.Perspective` carries is
#: outside the verified principal's grant (403; 15.5-06). A caller may
#: request a role; only the grant decides whether it is received.
ERROR_PRODUCT_ROLE_UNGRANTED: Final[str] = "product-role-ungranted"


def refusal_detail(*, error_code: str, message: str) -> dict[str, str]:
    """The one refusal-body shape: a constant code plus human prose."""
    return {"error_code": error_code, "message": message}
