"""The max-TTL precedence, measured — ledger row ``24.5-L-23``, CUT under criterion 18.

**Class declares the cap (`max_ttl_key`); deployment supplies the number (`MaxTTL.seconds` registered under that key); serve refuses over-cap by name (`ttl-bounds`).**

That is the one sentence Phase 24.5 criterion 18 asks for, and this module is
the test that *"enforces exactly that precedence"*. ``24.5-RESEARCH.md``
measured the sentence already true of the tree at ``bcd2360``; this module
measures it again on every run, so the cut stays measured rather than
remembered. Three things are pinned:

1. The **registered** number decides, by name. A candidate whose
   ``expires_at`` sits one second past ``now + MaxTTL.seconds`` is refused by
   :func:`~ccf.products.gates.run_gates` with a
   :class:`~ccf.products.gates.TTLRefusal` whose ``gate`` is
   :data:`~ccf.products.gates.GATE_TTL_BOUNDS` and whose ``max_ttl_seconds``
   is the number the deployment registered — a number that appears nowhere in
   the class declaration.
2. The deployment's number moves the cap and the class does not change.
   Re-registering the same ``max_ttl_key`` with a larger ``MaxTTL`` at a new
   version makes the same candidate serve, while the
   :class:`~ccf.controlplane.artifacts.ProductClassDeclaration` document is
   byte-identical before and after.
3. **No field was added, and none can be added quietly.** Neither
   ``ProductClassDeclaration`` nor
   :class:`~ccf.products.contract.RegisteredProductClass` carries any
   ``max_ttl*`` name other than ``max_ttl_key`` / ``max_ttl_version``, nor any
   ``*ttl_seconds`` name, asserted by set comprehension so a future second copy
   of the ceiling goes RED here. Dave's conditional on the ledger row, verbatim:
   *"If Wave 1 cannot state that precedence in one sentence, cut L-23 then —
   don't ship two unused fields."*

The dated cut note is
``.planning/phases/24.5-sdk-gap-catch-up-cp-00-through-cp-04/24.5-DECISIONS-AT-EXECUTION.md``.
Memory backend, network-free. Every key, name and number below is this
module's own (CINV-01 reaches ``tests/``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import PRODUCT_CLASS, ProductClassDeclaration, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import GATE_TTL_BOUNDS, ServableProduct, TTLRefusal, run_gates
from tests.composition import register_at_composition

TENANT = "tenant-fixture"
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
OPERATORS = frozenset({"fixture-operator"})

#: The deployment's two numbers. The first is the cap the candidate below
#: overshoots by one second; the second is the cap it fits under.
DEPLOYMENT_CAP_SECONDS = 60
WIDENED_CAP_SECONDS = 120
CANDIDATE_TTL_SECONDS = DEPLOYMENT_CAP_SECONDS + 1


def _declaration() -> ProductClassDeclaration:
    """The authored artifact. It names the KEY of its ceiling and no number."""
    parsed = parse_artifact(
        {
            "semver": "1.0.0",
            "schema_name": "fixture.max-ttl-precedence",
            "schema_version": "1.0.0",
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "tenant-fixture/max-ttl",
            "required_operator_keys": sorted(OPERATORS),
        },
        PRODUCT_CLASS,
    )
    assert isinstance(parsed, ProductClassDeclaration)
    return parsed


def _register(
    registry: ControlPlaneRegistry,
    declaration: ProductClassDeclaration,
    *,
    seconds: int,
) -> RegisteredProductClass:
    """The deployment supplies the number under the class's key, then registers the class."""
    version = register_at_composition(registry, declaration.max_ttl_key, MaxTTL(seconds=seconds))
    return register_product_class(
        registry=registry,
        schema_name=declaration.schema_name,
        schema_version=declaration.schema_version,
        ttl_anchor=declaration.ttl_anchor,
        assembly_mode=declaration.assembly_mode,
        max_ttl_key=declaration.max_ttl_key,
        max_ttl_version=version,
    )


def _candidate(product_class: RegisteredProductClass) -> ContextProductContract:
    return ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=CANDIDATE_TTL_SECONDS),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=frozenset({POLICY_VERSION}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={},
    )


def test_the_registered_number_decides_and_serve_refuses_over_cap_by_name() -> None:
    """Limb 1 of the sentence, measured: the REGISTERED number, refused as ``ttl-bounds``."""
    registry = ControlPlaneRegistry()
    declaration = _declaration()
    product_class = _register(registry, declaration, seconds=DEPLOYMENT_CAP_SECONDS)

    outcome = run_gates(
        _candidate(product_class),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )

    assert isinstance(outcome, TTLRefusal), (
        f"a candidate {CANDIDATE_TTL_SECONDS}s out against a registered cap of"
        f" {DEPLOYMENT_CAP_SECONDS}s was not refused by the ttl-bounds gate;"
        f" got {type(outcome).__name__}"
    )
    assert outcome.gate == GATE_TTL_BOUNDS == "ttl-bounds"
    assert outcome.max_ttl_seconds == DEPLOYMENT_CAP_SECONDS
    # The number the gate read is the one in the registry under the class's
    # key — and it is nowhere in the declaration.
    registered = registry.resolve(product_class.max_ttl_key, product_class.max_ttl_version)
    assert isinstance(registered, MaxTTL)
    assert registered.seconds == outcome.max_ttl_seconds
    assert DEPLOYMENT_CAP_SECONDS not in declaration.model_dump().values()


def test_the_deployment_moves_the_cap_and_the_class_declaration_does_not_change() -> None:
    """Limb 2: re-register the key at a new version; the same candidate serves."""
    registry = ControlPlaneRegistry()
    declaration = _declaration()
    before = content_hash(declaration)
    narrow = _register(registry, declaration, seconds=DEPLOYMENT_CAP_SECONDS)
    refused = run_gates(
        _candidate(narrow),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=narrow,
    )
    assert isinstance(refused, TTLRefusal)

    widened = _register(registry, declaration, seconds=WIDENED_CAP_SECONDS)
    assert widened.max_ttl_key == narrow.max_ttl_key
    assert widened.max_ttl_version != narrow.max_ttl_version

    served = run_gates(
        _candidate(widened),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=widened,
    )

    assert isinstance(served, ServableProduct), (
        f"the same candidate was refused under a widened registered cap of"
        f" {WIDENED_CAP_SECONDS}s: {served!r}"
    )
    assert content_hash(declaration) == before
    assert content_hash(_declaration()) == before


def test_no_ceiling_in_seconds_lives_on_the_class_or_the_registered_class() -> None:
    """Limb 3, the cut measured: no second copy of the ceiling, and none can arrive quietly."""
    declared = {
        name
        for name in ProductClassDeclaration.model_fields
        if "max_ttl" in name or name.endswith("ttl_seconds")
    }
    registered = {
        name
        for name in RegisteredProductClass.model_fields
        if "max_ttl" in name or name.endswith("ttl_seconds")
    }
    assert declared == {"max_ttl_key"}, declared
    assert registered == {"max_ttl_key", "max_ttl_version"}, registered
    # And the number itself is a field of MaxTTL alone.
    assert set(MaxTTL.model_fields) == {"seconds"}
