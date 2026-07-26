"""``ContextProductContract`` — the typed delivery contract (whitepaper §6.3).

Whitepaper §6.3 (the specification elements) and §7.6 (delivery); DESIGN.md
§2B.3, which maps the specification *elements* onto the Fig-CH07-13 typed base
*fields* and records the eight-versus-nine element drift under D-IMPL-30.

Field-to-element mapping realized here:

===========================================  ================================
Field                                        Specification element
===========================================  ================================
``schema_name`` / ``schema_version``         Schema; Semantic Versioning
``plan_id``                                  Π identity (binds product to plan)
``expires_at`` + ``ttl_anchor``              TTL
``lineage.operators_invoked``                Lineage
``lineage.policy_bundle_versions``           Policy Binding
``lineage.graph_snapshot_at``                Lineage (temporal anchor)
``payload``                                  per-product typed content
===========================================  ================================

Freshness SLA, Discovery, Addressability, and Assembly Mode are *class-level*
registration properties maintained by the Control Plane rather than instance
fields — a product does not carry a copy of its class's governance, it is
governed by it. :class:`RegisteredProductClass` is where they live.

**Semver lanes are per product class** (INV-CH7-49): ``schema_version`` is a
field on the instance and is never compared across classes, so a bump on one
product never touches another.

**MAX_TTL has no SDK default** (D-IMPL-39). It is required Control Plane
configuration per product class, and the absence of a registered value is a
failure at *class registration* — before any product of that class can exist —
rather than a surprise on the first serve. This module therefore holds no TTL
number, no freshness figure, and no threshold of any kind (CLAUDE.md §11,
CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol

__ccf_mode__ = "algorithmic"

__all__ = [
    "AssemblyMode",
    "ContextProductContract",
    "MaxTTL",
    "ProductClassRegistrationError",
    "ProductLineage",
    "RegisteredProductClass",
    "TTLAnchor",
    "register_product_class",
]

#: Whitepaper §7.6 TTL granularity (D-IMPL-31): a product's expiry is anchored
#: either to the decision that requested it or to the freshness of the entities
#: it was assembled from. Which one is a per-class declaration.
TTLAnchor = Literal["from_decision", "from_entity_freshness"]

#: Whitepaper §7.6 assembly modes (INV-CH7-55, the ninth contract element per
#: D-IMPL-30). I.1 is Mode 1 throughout — no LLM participates anywhere in the
#: fabric core.
AssemblyMode = Literal["algorithmic", "llm_packaged", "swarm_assembled"]


class ProductClassRegistrationError(ValueError):
    """A product class cannot be registered as configured.

    Raised — never returned, never warned — because a class whose governance
    configuration is absent or malformed must not become servable. D-IMPL-39.
    """


class MaxTTL(CCFContract):
    """The per-class TTL ceiling, as a Control Plane artifact.

    A typed artifact rather than a bare integer so that registering the wrong
    thing under the MAX_TTL key is a detectable error rather than a plausible
    one, and so the ceiling gets its own content-addressed version — which is
    what lands in the policy-bindings replay dimension.

    ``seconds`` is declared with no default: a missing ceiling is a deployment
    error, not a number the SDK is entitled to choose (D-IMPL-38).
    """

    seconds: int


class RegisteredProductClass(CCFContract):
    """Class-level governance of one product class, resolved at registration.

    Attributes:
        schema_name: Class identity.
        schema_version: The class's own semver lane (INV-CH7-49).
        ttl_anchor: Declared TTL derivation anchor (D-IMPL-31).
        assembly_mode: Declared mode (INV-CH7-55).
        max_ttl_key: Control Plane key of the class's MAX_TTL artifact.
        max_ttl_version: The pinned version of it. Pinned rather than
            "latest" so that the ceiling a decision was gated against is
            re-resolvable years later (whitepaper §7.10, D-IMPL-26).
    """

    schema_name: str
    schema_version: str
    ttl_anchor: TTLAnchor
    assembly_mode: AssemblyMode
    max_ttl_key: str
    max_ttl_version: str


class ProductLineage(CCFContract):
    """The L axis as it appears on a delivered product (INV-CH7-47).

    Attributes:
        operators_invoked: The operator set the *producer declares* it ran.
            Declared, not observed — the L6 lineage gate compares it against
            the engine's independent record, and a field the engine filled in
            would make that comparison vacuous.
        policy_bundle_versions: Every Control Plane policy-bundle version bound
            into the state this product was assembled from. A set, because
            state assembled under two bundle versions has two bindings and
            collapsing them would lose the one that mattered.
        graph_snapshot_at: The temporal anchor of the graph state read.
    """

    operators_invoked: frozenset[str]
    policy_bundle_versions: frozenset[str]
    graph_snapshot_at: datetime


class ContextProductContract(CCFContract):
    """The typed unit L6 delivers — and the only thing an agent may consume.

    Whitepaper §6.3, §7.6; DESIGN.md §2B.3. ``extra=forbid`` and frozen by
    inheritance from :class:`~ccf.contracts.base.CCFContract`: an unvalidated
    or forged product is a validation failure, never a served product.

    Constructing an instance of this class is *not* the same as having
    something servable. This type is the candidate; :class:`
    ~ccf.products.gates.ServableProduct` is the gated result, and only
    :mod:`ccf.products.gates` can mint one.
    """

    schema_name: str
    schema_version: str
    plan_id: str
    tenant_id: str
    temporal_boundary: datetime
    expires_at: datetime
    ttl_anchor: TTLAnchor
    lineage: ProductLineage
    payload: Mapping[str, Any]


def register_product_class(
    *,
    registry: ControlPlaneProtocol,
    schema_name: str,
    schema_version: str,
    ttl_anchor: TTLAnchor,
    assembly_mode: AssemblyMode,
    max_ttl_key: str,
    max_ttl_version: str,
) -> RegisteredProductClass:
    """Register a product class, requiring its MAX_TTL to already exist.

    Whitepaper §7.6; D-IMPL-39. The MAX_TTL is resolved *here*, at
    registration, so a deployment that forgot to configure a ceiling finds out
    while wiring the fabric rather than when a product is about to be served —
    at which point the only remaining options are a silent default (forbidden)
    or a failure in front of a caller.

    Raises:
        ProductClassRegistrationError: no MAX_TTL is registered at
            ``(max_ttl_key, max_ttl_version)``, or the artifact there is not a
            :class:`MaxTTL`.
    """
    try:
        artifact = registry.resolve(max_ttl_key, max_ttl_version)
    except ControlPlaneMissing as missing:
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares MAX_TTL at "
            f"({max_ttl_key!r}, {max_ttl_version!r}), which is not registered; "
            "MAX_TTL is required Control Plane configuration per product class "
            "and the SDK ships no default (D-IMPL-39)"
        ) from missing
    if not isinstance(artifact, MaxTTL):
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares MAX_TTL at "
            f"({max_ttl_key!r}, {max_ttl_version!r}), which holds "
            f"{type(artifact).__name__}, not MaxTTL"
        )
    return RegisteredProductClass(
        schema_name=schema_name,
        schema_version=schema_version,
        ttl_anchor=ttl_anchor,
        assembly_mode=assembly_mode,
        max_ttl_key=max_ttl_key,
        max_ttl_version=max_ttl_version,
    )
