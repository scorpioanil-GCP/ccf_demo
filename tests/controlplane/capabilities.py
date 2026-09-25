"""Minting helpers for handle tests — D-IMPL-353 §9 controls, in one place.

Test-side only; never ships. A handle test needs three things and needs them
identically in every tree: a *genuine* capability of a named kind for a named
tenant and resource (the positive control and the wrong-kind / wrong-resource
negatives), a roster of *fabricated* objects that must all die at ``verify``
(a stub-sentinel forgery, a ``Mock``, a bare ``object()``, a subclass that
skipped ``__init__``), and a way to *retarget* a genuine capability field by
field through ``object.__setattr__`` (§1.5g — separate from fabrication, on
purpose).

Minting here goes through the real :func:`ccf.authz.capability.mint` from an
``allowed`` :class:`~ccf.authz.decision.AuthzDecision`, exactly as the gate
does — the seam is not bypassed, it is exercised. ``ReplayMint`` goes through
:func:`~ccf.authz.capability.mint_at_composition`, the one producer the design
gives it (§2 P3).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeVar
from unittest.mock import Mock

from ccf.authz.capability import (
    ActionKind,
    Authorized,
    ReplayMint,
    mint,
    mint_at_composition,
)
from ccf.authz.decision import AuthzDecision

__all__ = [
    "DECISION_ID",
    "PRINCIPAL",
    "capability",
    "fabrications",
    "register_capability",
    "replay_mint",
    "retarget",
]

A = TypeVar("A", bound=ActionKind)

PRINCIPAL = "test-principal"
DECISION_ID = "authz-decision-test"


def capability(
    kind: type[A],
    *,
    tenant: str,
    resource: str,
    principal: str = PRINCIPAL,
    decision_id: str = DECISION_ID,
) -> Authorized[A]:
    """A genuine capability of ``kind`` for ``(tenant, resource)``."""
    decision = AuthzDecision(
        allowed=True,
        matched_scope_pattern=tenant,
        matched_resource_pattern=resource,
        artifact_version="1.0.0",
        action_id=kind.action_id,
        tenant=tenant,
        resource=resource,
    )
    return mint(kind, decision=decision, principal=principal, decision_id=decision_id)


def register_capability(
    key: str, kind: type[A], *, principal: str = PRINCIPAL
) -> Authorized[A]:
    """A registration capability whose tenant is the key's own tenant segment.

    The Control Plane key grammar is ``{tenant}/{class}/{name}``; the gate
    decides on the key as the resource and on the grant's tenant. This helper
    stands in for the gate having agreed with the key — the *disagreeing*
    case is minted explicitly by the cross-tenant control.
    """
    tenant, _, _ = key.partition("/")
    return capability(kind, tenant=tenant, resource=key, principal=principal)


def replay_mint(
    *,
    tenant: str,
    artifact_class: str,
    principal: str = "composition-root",
    decision_id: str = "composition-decision-test",
) -> Authorized[ReplayMint]:
    """The composition root's statement that this process mints ``artifact_class``."""
    return mint_at_composition(
        ReplayMint,
        tenant=tenant,
        principal=principal,
        resource=artifact_class,
        decision_id=decision_id,
    )


def fabrications(
    kind: type[ActionKind], *, tenant: str, resource: str
) -> Iterator[tuple[str, object]]:
    """The four §9 fabrications, each carrying plausible fields for ``kind``.

    Every one must die at ``verify`` on every handle. The stub-sentinel forgery
    is the one the first sabotage pass proved missing: every field agrees with
    its mint tuple and only the sentinel identity is wrong.
    """
    forged: Any = Authorized.__new__(Authorized)
    for name, value in (
        ("kind", kind),
        ("tenant", tenant),
        ("principal", PRINCIPAL),
        ("resource", resource),
        ("decision_id", DECISION_ID),
    ):
        object.__setattr__(forged, name, value)
    # `_minted` is no longer a slot: the mint record is the module's, keyed by
    # identity (F-FORGE-01) — an object built around the mint has no record.
    yield "stub-sentinel forgery", forged

    fake = Mock()
    fake.kind = kind
    fake.tenant, fake.principal = tenant, PRINCIPAL
    fake.resource, fake.decision_id = resource, DECISION_ID
    yield "Mock", fake

    yield "bare object()", object()

    skipped: Any = Authorized.__new__(Authorized)
    yield "subclass skipping __init__", skipped


#: The fields §1.5(g) requires retargeting to be tested on, with a value that
#: differs from anything a helper above mints.
RETARGETS: dict[str, object] = {
    "tenant": "other-bank",
    "principal": "impostor",
    "resource": "some/other/target",
    "decision_id": "authz-decision-9999",
}


def retarget(authorized: Authorized[Any], field: str, value: object) -> object:
    """Force ``field`` to ``value`` past the assignment guard; return the object.

    ``object.__setattr__`` bypasses ``Authorized.__setattr__``; the mint tuple
    is what makes the result unusable for anything (§1.5g).
    """
    object.__setattr__(authorized, field, value)
    return authorized
