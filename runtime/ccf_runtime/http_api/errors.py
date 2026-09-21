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
    "ERROR_EVIDENCE_ABSENT",
    "ERROR_EVIDENCE_CLASS_UNRECOVERABLE",
    "ERROR_EVIDENCE_DISCLOSURE_WITHHELD",
    "ERROR_EVIDENCE_PRINCIPAL_MISMATCH",
    "ERROR_INVALID_GRANT",
    "ERROR_PRINCIPAL_NOT_ENTITLED",
    "ERROR_PRODUCT_CLASS_UNENTITLED",
    "ERROR_PRODUCT_DOOR_UNGOVERNED",
    "ERROR_PRODUCT_PARAMETERS_MALFORMED",
    "ERROR_PRODUCT_POLICY_ABSENT",
    "ERROR_PRODUCT_REQUEST_INCOMPLETE",
    "ERROR_PRODUCT_ROLE_UNGRANTED",
    "ERROR_ROUTE_HANDLE_ABSENT",
    "ERROR_SIGNED_BINDING_INVALID",
    "ERROR_SIGNED_BINDING_REQUIRED",
    "ERROR_SUBJECT_CONFLICT",
    "ERROR_TENANT_UNAUTHORIZED",
    "ERROR_UNAUTHENTICATED",
    "refusal_detail",
]

#: The request carried no credential the bound auth hook recognises (401).
ERROR_UNAUTHENTICATED: Final[str] = "unauthenticated"

#: The caller asked to dereference a governed record that belongs to another
#: principal (``D-IMPL-345`` R-2/R-4). Internal truth only: the shell a
#: consumer receives below ``full`` is the one every other absence produces,
#: because a principal must not learn from a refusal that a record exists.
ERROR_EVIDENCE_PRINCIPAL_MISMATCH: Final[str] = "evidence-principal-mismatch"

#: The caller's own record carries no recoverable product class, so the grant
#: that governed its serve cannot be re-decided and the record does not cross
#: (``D-IMPL-345`` §9.1). Conservative by ruling: ownership is never inferred
#: from current state for a record that predates the identity members.
ERROR_EVIDENCE_CLASS_UNRECOVERABLE: Final[str] = "evidence-class-unrecoverable"

#: The caller's own record exists and its grant holds, but the disclosure
#: level in force for that principal is below ``full`` (``D-IMPL-345`` R-2).
#: The record IS the internal truth, so the level that withheld the serve
#: withholds its record — a dereference never upgrades a caller to the cause
#: its own shell hid.
ERROR_EVIDENCE_DISCLOSURE_WITHHELD: Final[str] = "evidence-disclosure-withheld"

#: Nothing readable is at the reference: no such address, a malformed one, a
#: URI naming no registered version, bytes that are not a record, or bytes
#: that do not hash to their address (``D-IMPL-345`` R-4). ONE code for every
#: absence, at every level — the non-record artifact classes are addressed by
#: the hash of their own inputs, so a caller able to tell *bytes that are not
#: a record* from *nothing* could confirm that a particular traversal or
#: question happened.
ERROR_EVIDENCE_ABSENT: Final[str] = "evidence-absent"

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

#: This door cannot name the :class:`~ccf.projection.plan.Perspective` a
#: product would be shaped under, so it does not serve one (503; D-IMPL-108,
#: closing DI-15.5-03).
#:
#: Reached when the entitlement seams are unbound, or when they are bound but
#: no verified grant accompanies the call. Both are configuration states, which
#: is why this is a 503 and not a 403: nothing is wrong with the *caller*, and
#: telling them they are forbidden would misattribute the fault. It is the
#: HTTP counterpart of ``build_egress_server`` refusing to build an ungoverned
#: door at all — that builder can raise because its surface is authenticated by
#: construction, whereas this one must still *build* in the acknowledged
#: insecure posture (D-IMPL-73) and therefore refuses per call instead.
#:
#: The perspective is required rather than defaulted at the resolver seam
#: precisely so this state is loud: a door that manufactured a perspective here
#: would serve a product conditioned on a role nobody granted, which is
#: indistinguishable at the wire from one the door authorized.
ERROR_PRODUCT_DOOR_UNGOVERNED: Final[str] = "product-door-ungoverned"

#: A partial §6.3 request address reached the product route (400; D-IMPL-98).
#:
#: The four address axes — subject, intent, freshness and the instant — are
#: supplied together or not at all. A defaulted axis is a question nobody
#: asked, answered anyway, so the door refuses the partial address rather than
#: filling one in.
ERROR_PRODUCT_REQUEST_INCOMPLETE: Final[str] = "product-request-incomplete"

#: ``?parameters=`` did not parse as a JSON **object** (400; ``D-IMPL-133``).
#:
#: The declared remainder of a question travels on this door as one JSON
#: object rather than as flattened query keys, because JSON is self-describing:
#: a presented ``3`` and a presented ``"3"`` stay distinguishable, and
#: ``D-IMPL-103``'s one level of declared nesting crosses intact. A flat,
#: string-valued query surface could carry neither without the door guessing at
#: a coercion, which is the constraint this door's own ``_asked`` records.
#:
#: Refused rather than repaired: text that is not a JSON object is a malformed
#: argument, and a door that fell back to the empty mapping would answer a
#: question the caller did not ask while reporting success. The door renders no
#: verdict on the parameters *inside* a well-formed object — that comparison
#: belongs to the resolver, against the class it holds (D-IMPL-121).
ERROR_PRODUCT_PARAMETERS_MALFORMED: Final[str] = "product-parameters-malformed"

#: This deployment did not wire the handle this route needs, so the route
#: refuses rather than serving half-wired (503; ``D-IMPL-126`` item (3)).
#:
#: A 503 and not a 500 for the ``ERROR_PRODUCT_DOOR_UNGOVERNED`` reason: the
#: fault is the deployment's, not the caller's, and an opaque 500 would say
#: nothing about which of eight handles is absent. A 503 and not a 404 because
#: the route *exists* — it is mounted, it is in the OpenAPI document, and it
#: will answer the moment the handle is supplied; making it vanish instead
#: would be a different and unruled behaviour.
#:
#: The five handles that can be absent — ``workflow_factory``,
#: ``workflow_engine``, ``hitl_transport``, ``skill_catalog`` and
#: ``grant_ledger`` — default to ``None`` so a deployment exposing one noun
#: does not have to fabricate seven. The message names the absent field and the
#: ``create_app`` argument to supply, which is what keeps the boot-time
#: ``TypeError`` this replaces from being a diagnostic that was simply lost.
ERROR_ROUTE_HANDLE_ABSENT: Final[str] = "route-handle-absent"


def refusal_detail(*, error_code: str, message: str) -> dict[str, str]:
    """The one refusal-body shape: a constant code plus human prose."""
    return {"error_code": error_code, "message": message}
