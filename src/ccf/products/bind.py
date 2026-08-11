"""Bind-time payload conformity — where a payload meets its class's schema.

SDK-defined; the ruling of record is ``docs/DECISIONS.md`` **D-IMPL-102**, and
``D-IMPL-98`` supplies the surface this runs on. CLAUDE.md §11 requires an SDK
extension to cite this project's own record rather than the whitepaper, and
this is one: whitepaper §7.6 commits to *three* validation gates and this
module is deliberately **not** a fourth.

**Dave's ruling, verbatim** (D-IMPL-102): *"Q5 payload validation → Schema
validity at registration + payload conformity at Bind (request time). Gate
scripts remain structural only."* Three limbs, and this module is the second
held honest by the third:

1. **Schema validity at registration** — plan ``15.5-07``. A malformed
   *declaration* is refused at wiring time: a malformed
   :data:`~ccf.products.payload.ProductPayloadSchema` cannot be constructed at
   all, and :func:`~ccf.products.contract.register_product_class` refuses a
   pin that resolves to something which is not one.
2. **Payload conformity at bind — request time.** *This module.* An actual
   payload is held to the schema its class declared, at the point a request
   has bound to that class and the class's pinned schema is therefore in hand.
3. **No fourth gate.** :func:`ccf.products.gates.run_gates` is untouched and
   imports nothing from here. The shipped gates stay **structural** — each of
   their verdicts depends only on the product's own shape (an empty operator
   set, a lineage inequality, a TTL outside its bounds, an attested mode
   outside an accepted set) — whereas a payload verdict depends on a schema a
   *deployment* declared. A payload gate would have been the first
   configurable member of a set whose value is that none of them is, which is
   the line limb 3 draws. :class:`~ccf.products.payload.PayloadSchemaViolation`
   correspondingly does not derive from
   :class:`~ccf.products.gates.GateRefusal`, so a payload verdict cannot
   travel as a gate verdict even by accident.

**Where a caller joins this, precisely.** ``D-IMPL-98`` ruled that every
product class declares a **typed request contract** as a Control Plane
artifact, and ``D-IMPL-108`` gave the widening of the resolver seam — the
three-string ``(tenant, product_class, version)`` surface at
``runtime/ccf_runtime/mcp/egress.py`` and ``…/mcp/experience.py`` — to plan
``15.5-15``. This module is the payload half of that bind and takes neither a
request nor a door: it needs the :class:`
~ccf.products.contract.RegisteredProductClass` a request resolved to, the
payload delivered under it, and the Control Plane the pin resolves in. The
join is therefore one call from the bound path —
``refuse_bound_payload(payload=…, product_class=…, registry=…)`` — placed
after the payload exists and before it leaves the bind. Keeping the request
contract out of this signature is what lets ``15.5-08`` and ``15.5-15`` land
their surfaces without reopening this one.

**Why this is not simply inlined at the call site.** A conformity check
written at each bound path would be as many readings of "conforms" as there
are paths. There is one comparison —
:func:`~ccf.products.payload.refuse_payload` — and this module is the one
place that resolves a class's pin and hands it that comparison, for the reason
:func:`~ccf.products.gates.refuse_attestation` is one function: two layers
that each implement a check drift, and a drifted admission check is an
admission bypass on whichever layer is laxer.

**A bad product is returned; a broken deployment is raised.** The posture
:mod:`ccf.products.gates` states at its own head. A payload that misses its
declared schema is a bad **product** and comes back as a value that cannot be
swallowed by a bare ``except``. A pin that has vanished from the Control Plane
since registration, or that now holds something other than a schema, is a
broken **deployment** and is raised — the same asymmetry ``run_gates`` keeps
for its own MAX_TTL pin.

This module holds no property name, no domain type and no threshold
(CLAUDE.md §11, CINV-01), and no principal: entitlement is resolved at the
door (plan ``15.5-06``), never here.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.products.contract import NO_PAYLOAD_SCHEMA, RegisteredProductClass
from ccf.products.payload import (
    PayloadSchemaViolation,
    ProductPayloadSchema,
    refuse_payload,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "refuse_bound_payload",
    "resolve_declared_payload_schema",
]


def resolve_declared_payload_schema(
    *,
    product_class: RegisteredProductClass,
    registry: ControlPlaneProtocol,
) -> ProductPayloadSchema | None:
    """Resolve the schema a class pinned at registration, or ``None``.

    The pin is ``(payload_schema_key, payload_schema_version)`` and it is
    resolved by *exact* version, never latest — the schema a payload was held
    to has to be re-resolvable years later for the decision to replay at all
    (D-IMPL-26, and the discipline
    :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.resolve_latest`
    exists to keep off replay paths).

    Only the key is tested against :data:`
    ~ccf.products.contract.NO_PAYLOAD_SCHEMA` because the halves move
    together: :func:`~ccf.products.contract.register_product_class` refuses a
    half-declared pin, so a class that reaches bind with a declared key has a
    declared version too.

    Returns:
        The pinned schema, or ``None`` when the class declared none. ``None``
        asserts *this class has not declared what its payload must look like*
        — the positive reading :data:`
        ~ccf.products.contract.NO_PAYLOAD_SCHEMA` carries — and never *the
        lookup was skipped*.

    Raises:
        ccf.controlplane.registry.ControlPlaneMissing: the pinned schema has
            disappeared from the Control Plane since registration. Raised
            rather than returned: a broken deployment is not a bad product.
        TypeError: the pin now holds something that is not a payload schema.
    """
    if product_class.payload_schema_key == NO_PAYLOAD_SCHEMA:
        return None
    artifact = registry.resolve(
        product_class.payload_schema_key, product_class.payload_schema_version
    )
    if not isinstance(artifact, ProductPayloadSchema):
        raise TypeError(
            f"product class {product_class.schema_name!r} pins its payload "
            f"schema at ({product_class.payload_schema_key!r}, "
            f"{product_class.payload_schema_version!r}), which holds "
            f"{type(artifact).__name__}, not a payload schema "
            f"({ProductPayloadSchema.__name__}); the pin resolved to a schema "
            "at registration, so the Control Plane has changed under it "
            "(D-IMPL-102 limb 1)"
        )
    return artifact


def refuse_bound_payload(
    *,
    payload: Mapping[str, Any],
    product_class: RegisteredProductClass,
    registry: ControlPlaneProtocol,
) -> PayloadSchemaViolation | None:
    """Hold one payload to the schema its class declared — D-IMPL-102 limb 2.

    The bind-time half of the ruling. Called from the bound request path once
    the payload exists and before it leaves that path; see the module
    docstring for exactly where ``15.5-08``'s typed request contract and
    ``15.5-15``'s widened resolver seam join.

    Pure apart from the single pinned Control Plane resolution it needs to
    learn *which* schema: no clock, no network, no graph read. The comparison
    it delegates to is pure outright, so the same ``(payload, class,
    Control Plane state)`` reaches the same verdict at replay — which is the
    property every comparison in this package is required to have.

    Args:
        payload: The payload as delivered — :attr:`
            ~ccf.products.contract.ContextProductContract.payload` on the
            vessel, taken as a mapping so the check is available before a
            vessel has been constructed as well as after.
        product_class: The class the request bound to, carrying the schema pin
            established at registration.
        registry: The Control Plane the pin resolves in.

    Returns:
        ``None`` when the payload conforms, **or when the class declared no
        schema** — the compatibility posture stated positively: a class that
        has not declared what its payload must look like holds it to nothing,
        and that gap is visible in the registration rather than papered over
        here. Otherwise the :class:`
        ~ccf.products.payload.PayloadSchemaViolation` naming the first failure
        and carrying both sides of the comparison that failed.

    Raises:
        ccf.controlplane.registry.ControlPlaneMissing: the pinned schema is
            gone from the Control Plane.
        TypeError: the pin holds something that is not a payload schema.
    """
    declared = resolve_declared_payload_schema(
        product_class=product_class, registry=registry
    )
    if declared is None:
        return None
    return refuse_payload(payload=payload, declared=declared)
