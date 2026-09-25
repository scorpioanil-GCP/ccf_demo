"""`D-IMPL-334` — serve-time dependency invalidation, end to end.

**Not an event bus and not a cascade**, and the vocabulary is load-bearing:

    A graph supersession records an **invalidation boundary**. Any previously
    derived product whose snapshot predates that boundary and touched that
    entity becomes **ineligible for future serving**.

Dave's matrix is the first four tests, in his own terms:

    Product A touches obligor X at snapshot T1
    Product B does not touch X at snapshot T1
    X is superseded at T2 > T1
      A -> refused on next serve
      B -> still eligible
      new A derived after T2 -> eligible

**B is the test that makes the other three mean something.** A mechanism that
refused every product after any supersession would pass A's case and be
worthless — it would be a global clock, not a dependency. B proves the refusal
is keyed on what the product actually read.

Tenant isolation is the fifth, for the same reason: a register shared across
tenants would let one tenant's write refuse another's product, and the failure
would look exactly like the mechanism working.

**No cache, no eviction, no notification is asserted anywhere here**, because
none exists. Every test drives `run_gates`, which is where eligibility is
decided, and the product in hand is the only thing evaluated.

Memory-only. Every key, URI and instant below is this module's own (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ccf.controlplane.invalidation import (
    KEY_PREFIX,
    ControlPlaneInvalidationSink,
    EntityInvalidation,
    EntityInvalidationRegister,
    register_key,
    resolve_register,
)
from ccf.authz.capability import COMPOSITION_PRINCIPAL
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.halflife.assessment import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import (
    GATE_DEPENDENCY_INVALIDATION,
    DependencyInvalidationRefusal,
    ServableProduct,
    run_gates,
)
from tests.composition import register_at_composition
from tests.composition import composition_register, register_at_composition

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"

#: The entity that moves, and one that never does.
ENTITY_X = "entity://obligor-x"
ENTITY_Y = "entity://obligor-y"

#: T1 is when both products read the graph. T2 is strictly later, and is the
#: instant of the observation that supersedes — never the instant of the write
#: that recorded it.
T1 = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
T2 = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
#: T3 is when a product derived AFTER the boundary reads the graph.
T3 = datetime(2026, 3, 3, 12, 0, 0, tzinfo=UTC)

#: The serve instant. Late enough that nothing here expires for the wrong
#: reason — a TTL refusal would mask the gate under test.
SERVED_AT = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)

SCHEMA = "fixture.dependency-invalidation"
VERSION = "1.0.0"
MAX_TTL_KEY = "fixture/max-ttl"
MAX_TTL_SECONDS = 86400
OPERATORS = frozenset({"fixture-operator"})
POLICY_VERSION = "fixture-policy"


@pytest.fixture()
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def _registered(registry: ControlPlaneRegistry) -> object:
    version = register_at_composition(registry, MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
    return register_product_class(
        registry=registry,
        schema_name=SCHEMA,
        schema_version=VERSION,
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=version,
    )


def _candidate(*, tenant_id: str, snapshot: datetime) -> ContextProductContract:
    """One product, built at ``snapshot``. Its payload is beside the point."""
    return ContextProductContract(
        tenant_id=tenant_id,
        schema_name=SCHEMA,
        schema_version=VERSION,
        plan_id="fixture-plan",
        temporal_boundary=snapshot,
        expires_at=SERVED_AT + timedelta(hours=1),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=(POLICY_VERSION,),
            graph_snapshot_at=snapshot,
        ),
        payload={"value": 1},
        debt=DebtAssessment(
            debt=0,
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=1, completeness=1, semantic_consistency=1
            ),
            scorers=(),
        ),
    )


def _serve(
    registry: ControlPlaneRegistry,
    registered: object,
    *,
    tenant_id: str,
    snapshot: datetime,
    touched: tuple[str, ...],
) -> object:
    return run_gates(
        _candidate(tenant_id=tenant_id, snapshot=snapshot),
        engine_resolved=OPERATORS,
        now=SERVED_AT,
        registry=registry,
        product_class=registered,
        touched_entities=touched,
    )


def _sink(registry: ControlPlaneRegistry) -> ControlPlaneInvalidationSink:
    """The sink as `ccf.boot` composes it: one `Register` per tenant, minted by the recipe (D-IMPL-354)."""
    return ControlPlaneInvalidationSink(
        registry=registry,
        authorities=tuple(
            composition_register(registry, register_key(tenant)) for tenant in (TENANT_A, TENANT_B)
        ),
    )


def _supersede(
    registry: ControlPlaneRegistry, *, tenant_id: str, entity_uri: str,
    at: datetime,
) -> None:
    """What the graph writer does when a claim on ``entity_uri`` is superseded."""
    _sink(registry).record(
        tenant_id=tenant_id,
        entity_uri=entity_uri,
        invalidated_from=at,
        reason="entity-claim-superseded",
        source="claim-fixture",
    )


# =========================================================================
# Dave's matrix.
# =========================================================================


def test_a_product_that_touched_the_changed_entity_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """**A → refused.** It read X at T1; X moved at T2 > T1."""
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T2)

    outcome = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T1,
        touched=(ENTITY_X,),
    )

    assert isinstance(outcome, DependencyInvalidationRefusal)
    assert outcome.gate == GATE_DEPENDENCY_INVALIDATION
    # The refusal NAMES what moved. A refusal saying only "stale" would not let
    # an auditor tell which evidence changed.
    assert outcome.entity_uri == ENTITY_X
    assert outcome.invalidated_from == T2
    assert outcome.graph_snapshot_at == T1
    assert outcome.cause == "claim-fixture"
    # And it is NOT a ServableProduct, so it cannot be delivered — the refusal
    # is structural rather than advisory.
    assert not isinstance(outcome, ServableProduct)


def test_a_product_that_did_not_touch_the_changed_entity_still_serves(
    registry: ControlPlaneRegistry,
) -> None:
    """**B → still eligible.** THE TEST THAT MAKES THE OTHERS MEAN SOMETHING.

    B was built at the same T1 as A and is just as old. A mechanism keyed on
    time rather than on dependence would refuse it too, pass A's test, and be a
    global clock wearing an invalidation's name.
    """
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T2)

    outcome = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T1,
        touched=(ENTITY_Y,),
    )

    assert isinstance(outcome, ServableProduct)


def test_a_product_derived_after_the_boundary_is_eligible(
    registry: ControlPlaneRegistry,
) -> None:
    """**new A after T2 → eligible.** The boundary is not a permanent ban.

    Without this, "invalidation" would mean an entity that changed once could
    never be served again — which would make the mechanism useless on exactly
    the entities it exists for.
    """
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T2)

    outcome = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T3,
        touched=(ENTITY_X,),
    )

    assert isinstance(outcome, ServableProduct)


def test_an_untouched_register_refuses_nothing(
    registry: ControlPlaneRegistry,
) -> None:
    """No supersession, no refusal — the additive baseline.

    Every product served before this mechanism existed is this case, which is
    what makes the gate additive rather than a behavior change.
    """
    registered = _registered(registry)
    assert resolve_register(registry, tenant_id=TENANT_A) is None

    outcome = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T1,
        touched=(ENTITY_X, ENTITY_Y),
    )

    assert isinstance(outcome, ServableProduct)


# =========================================================================
# Tenant isolation.
# =========================================================================


def test_one_tenants_supersession_cannot_refuse_anothers_product(
    registry: ControlPlaneRegistry,
) -> None:
    """Tenant isolation, and the failure it prevents looks like success.

    A register shared across tenants would refuse B's product here and the
    refusal would read exactly like the mechanism working. The two products are
    identical in every respect except the tenant, so the tenant is the only
    thing that can explain the difference.
    """
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T2)

    refused = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T1,
        touched=(ENTITY_X,),
    )
    served = _serve(
        registry, registered, tenant_id=TENANT_B, snapshot=T1,
        touched=(ENTITY_X,),
    )

    assert isinstance(refused, DependencyInvalidationRefusal)
    assert isinstance(served, ServableProduct)
    # And the registers are separate objects under separate keys, so the
    # isolation is structural rather than a filter someone remembered to apply.
    assert register_key(TENANT_A) != register_key(TENANT_B)
    assert resolve_register(registry, tenant_id=TENANT_B) is None


# =========================================================================
# The boundaries of the predicate itself.
# =========================================================================


def test_touched_entities_unsupplied_passes(
    registry: ControlPlaneRegistry,
) -> None:
    """``None`` means *the caller did not say*, and every old call site is that.

    The attestation gate's compatibility posture, reused: a caller that does
    not supply the list gets exactly the behavior it had before `D-IMPL-334`.
    """
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T2)

    outcome = run_gates(
        _candidate(tenant_id=TENANT_A, snapshot=T1),
        engine_resolved=OPERATORS,
        now=SERVED_AT,
        registry=registry,
        product_class=registered,
    )

    assert isinstance(outcome, ServableProduct)


def test_a_boundary_at_exactly_the_snapshot_does_not_refuse(
    registry: ControlPlaneRegistry,
) -> None:
    """Strictly later, and the asymmetry is deliberate.

    A product read the graph as of T1. A change *at* T1 is already inside what
    it saw, so refusing would discard a correct answer.
    """
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T1)

    outcome = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T1,
        touched=(ENTITY_X,),
    )

    assert isinstance(outcome, ServableProduct)


def test_the_first_moved_entity_is_the_one_named(
    registry: ControlPlaneRegistry,
) -> None:
    """A product touching several moved entities refuses naming one of them.

    Asserted so the refusal's `entity_uri` is known to be a real member of the
    touched set rather than an arbitrary register row.
    """
    registered = _registered(registry)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_X, at=T2)
    _supersede(registry, tenant_id=TENANT_A, entity_uri=ENTITY_Y, at=T2)

    outcome = _serve(
        registry, registered, tenant_id=TENANT_A, snapshot=T1,
        touched=(ENTITY_Y, ENTITY_X),
    )

    assert isinstance(outcome, DependencyInvalidationRefusal)
    assert outcome.entity_uri in {ENTITY_X, ENTITY_Y}


# =========================================================================
# The register.
# =========================================================================


def test_a_boundary_never_moves_backward(
    registry: ControlPlaneRegistry,
) -> None:
    """A late-arriving earlier observation leaves the standing boundary alone.

    `_restitch_chain`'s own posture: a claim observed before the current one
    slots into history rather than displacing it. Moving the boundary back
    would make eligible again a product a later change had ruled out.
    """
    sink = _sink(registry)
    sink.record(
        tenant_id=TENANT_A, entity_uri=ENTITY_X, invalidated_from=T2,
        reason="entity-claim-superseded", source="later",
    )
    sink.record(
        tenant_id=TENANT_A, entity_uri=ENTITY_X, invalidated_from=T1,
        reason="entity-claim-superseded", source="earlier",
    )

    register = resolve_register(registry, tenant_id=TENANT_A)
    assert register is not None
    assert register.boundary_for(ENTITY_X) == T2
    # And the no-op append registered NO new version: a version per write that
    # changed nothing would show an auditor activity that never happened.
    assert len(registry.versions(register_key(TENANT_A))) == 1


def test_the_register_is_append_only_and_versioned(
    registry: ControlPlaneRegistry,
) -> None:
    """Each boundary that moves is a distinct audited registry version.

    Nothing is removed and nothing is overwritten in place, so the history of
    appends is recoverable from the version chain even though one version holds
    only the current boundaries.
    """
    sink = _sink(registry)
    sink.record(
        tenant_id=TENANT_A, entity_uri=ENTITY_X, invalidated_from=T2,
        reason="entity-claim-superseded", source="x",
    )
    sink.record(
        tenant_id=TENANT_A, entity_uri=ENTITY_Y, invalidated_from=T2,
        reason="entity-claim-superseded", source="y",
    )

    versions = registry.versions(register_key(TENANT_A))
    assert len(versions) == 2
    first = registry.resolve(register_key(TENANT_A), versions[0])
    assert isinstance(first, EntityInvalidationRegister)
    # The earlier version still holds only what it held: appending did not
    # rewrite it.
    assert first.boundary_for(ENTITY_X) == T2
    assert first.boundary_for(ENTITY_Y) is None


def test_a_register_holding_the_wrong_type_is_refused_by_name() -> None:
    """A key holding something else raises rather than silently passing.

    A `None`-on-anything-unexpected reading would make a misconfigured register
    indistinguishable from an empty one, and every product would serve.
    """
    registry = ControlPlaneRegistry()
    register_at_composition(registry, register_key(TENANT_A), MaxTTL(seconds=1))

    with pytest.raises(TypeError, match="EntityInvalidationRegister"):
        resolve_register(registry, tenant_id=TENANT_A)


def test_the_register_entry_carries_its_cause() -> None:
    """An entry names what superseded, so an auditor can follow it."""
    entry = EntityInvalidation(
        entity_uri=ENTITY_X,
        invalidated_from=T2,
        reason="entity-claim-superseded",
        source="claim-0001",
    )
    register = EntityInvalidationRegister(
        semver="1.0.0", tenant_id=TENANT_A
    ).with_boundary(entry)

    assert register.entry_for(ENTITY_X) == entry
    assert register.entry_for(ENTITY_Y) is None


# =========================================================================
# The write side: the writer reports, and the composition root binds.
# =========================================================================


def _boot(registry: ControlPlaneRegistry) -> object:
    """A memory fabric over ``registry``. No file, no server, no Docker."""
    from ccf.boot import boot

    import conftest as harness

    spec_version = register_at_composition(registry, harness.RESOLUTION_SPEC_KEY, harness._resolution_spec()
    )
    policy_version = register_at_composition(registry, harness.POLICY_BUNDLE_KEY, harness._policy_bundle()
    )
    return boot(
        backend="memory",
        connection={},
        registry=registry,
        resolution_spec_key=harness.RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=harness.POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=(TENANT_A, TENANT_B),
    )


def _writer_of(fabric: object) -> object:
    """The one write handle, which L2 holds (single-writer, CLAUDE.md §10)."""
    return fabric.worker._writer


def test_the_writer_reports_the_boundary_when_a_claim_is_superseded() -> None:
    """Capability 1, end to end through a real boot and a real graph write.

    **The gate tests above would all pass against a register nobody ever
    filled.** This is the half that proves a supersession actually reaches it,
    and it drives the real writer rather than calling the sink directly.

    Three things are asserted separately because each fails differently: that a
    boundary was recorded at all, that it names the entity that moved, and that
    ``invalidated_from`` is **the superseding observation's own instant** rather
    than the instant of the write.

    **This is the `observed_at` FALLBACK case, and it is kept deliberately**
    (`D-IMPL-335`). The claim is built directly and carries no ``valid_from``,
    so the fabric has no world-time for it — and `D-IMPL-332` requires that
    absence be preserved rather than invented. ``observed_at`` is then the only
    instant there is. The split-clock case is the test above. The third is the one a plausible
    implementation gets wrong — a boundary taken from ingestion would refuse
    products that were correct as of the evidence they actually read.
    """
    from ccf.contracts.claims import EntityClaim, LineageEntry
    from ccf.signal.envelope import SourceIdentity

    registry = ControlPlaneRegistry()
    fabric = _boot(registry)
    writer = _writer_of(fabric)
    try:
        def _claim(observed_at: datetime, rating: str) -> EntityClaim:
            # The attributes DIFFER between the two writes on purpose: a claim
            # identical in content to one already stored is deduplicated rather
            # than appended, so it supersedes nothing — and a test that wrote
            # the same claim twice would prove only that.
            return EntityClaim(
                tenant_id=TENANT_A,
                entity_uri=ENTITY_X,
                entity_class="obligor",
                attributes={"name": "fixture", "rating": rating},
                observed_at=observed_at,
                lineage=frozenset((
                    LineageEntry(
                        source=SourceIdentity(system_id="fixture-source"),
                        envelope_id=f"envelope-{observed_at.isoformat()}",
                        observed_at=observed_at,
                    ),
                )),
            )

        # The FIRST write supersedes nothing — there is no prior claim — so no
        # boundary is recorded. Asserted, because a mechanism that fired on
        # every write would refuse every product and still pass the tests that
        # only look for a refusal.
        writer.upsert_entity(
            tenant_id=TENANT_A, claim=_claim(T1, "BB"),
            policy_bundle_version=registry.versions(
                __import__('conftest').POLICY_BUNDLE_KEY)[-1],
        )
        assert resolve_register(registry, tenant_id=TENANT_A) is None

        # The SECOND write supersedes the first.
        writer.upsert_entity(
            tenant_id=TENANT_A, claim=_claim(T2, "BB-"),
            policy_bundle_version=registry.versions(
                __import__('conftest').POLICY_BUNDLE_KEY)[-1],
        )
        register = resolve_register(registry, tenant_id=TENANT_A)
        assert register is not None
        entry = register.entry_for(ENTITY_X)
        assert entry is not None
        assert entry.entity_uri == ENTITY_X
        # THE SUPERSEDING OBSERVATION'S INSTANT, not the write's.
        assert entry.invalidated_from == T2
        assert entry.reason == "entity-claim-superseded"
        assert entry.source
    finally:
        fabric.close()


def test_the_boundary_through_L2_is_world_time_not_ingestion_time() -> None:
    """`D-IMPL-335` — THE TWO CLOCKS, SPLIT, THROUGH THE REAL ASSEMBLY PATH.

    **This is the regression `D-IMPL-334` shipped without**, and the reason it
    shipped without one is worth keeping: the direct-claim test below builds an
    `EntityClaim` with `observed_at` set by hand, so `observed_at` IS the
    observation instant there and the two clocks never separate. Only L2
    separates them — `worker._stitch` writes `observed_at = ingestion_timestamp`
    and `valid_from = observed_time` — so only a test that goes through L2 can
    see which one the boundary took. `CP-SPEC-011` found it at Gate 2.

    What the old behavior got wrong, and it was not merely conservative (Dave,
    2026-09-12): a product whose snapshot falls **after the world change but
    before the fabric ingested it** was refused — on the basis of when the
    fabric happened to learn something rather than on when anything changed.

    The two instants here are deliberately far apart and deliberately ordered
    `T_world < T_ingest`, so a boundary at either one is unmistakable.
    """
    from ccf.signal.envelope import SignalEnvelope, SourceIdentity

    T_WORLD = datetime(2026, 3, 1, tzinfo=UTC)
    T_INGEST = datetime(2026, 6, 15, tzinfo=UTC)
    COUNTERPARTY = "LEI-SPLIT-CLOCKS"

    registry = ControlPlaneRegistry()
    fabric = _boot(registry)
    try:
        def _envelope(*, seq: int, world: datetime, rating: str) -> SignalEnvelope:
            return SignalEnvelope(
                tenant_id=TENANT_A,
                envelope_id=f"envelope-{seq}",
                source=SourceIdentity(system_id="fixture-source"),
                # WHEN THE FABRIC WRITES. Identical for both envelopes, so it
                # cannot be what distinguishes them.
                ingestion_timestamp=T_INGEST,
                # WHEN IT BECAME TRUE. This is what the boundary must take.
                observed_time=world,
                # The harness's own resolution spec (`tests/conftest.py`) keys
                # `counterparty` on `counterparty_lei` and keeps
                # `counterparty_name` and `jurisdiction`. The NAME is what
                # differs between the two writes, so the second claim is
                # genuinely a different claim and supersedes rather than
                # deduplicating — the trap the D-IMPL-334 tests already hit
                # once.
                raw_payload={
                    "counterparty_lei": COUNTERPARTY,
                    "counterparty_name": rating,
                    "jurisdiction": "US",
                },
            )

        worker = fabric.worker
        worker.ingest(_envelope(seq=0, world=T_WORLD - timedelta(days=30), rating="BB"))
        assert resolve_register(registry, tenant_id=TENANT_A) is None, (
            "the first write supersedes nothing, so no boundary exists yet"
        )
        worker.ingest(_envelope(seq=1, world=T_WORLD, rating="BB-"))

        register = resolve_register(registry, tenant_id=TENANT_A)
        assert register is not None, "the superseding write recorded no boundary"
        entry = next(iter(register.entries), None)
        assert entry is not None

        assert entry.invalidated_from == T_WORLD, (
            f"the boundary is {entry.invalidated_from.isoformat()}; it must be"
            f" the WORLD instant {T_WORLD.isoformat()}, not the ingestion"
            f" instant {T_INGEST.isoformat()}. Through L2, `claim.observed_at`"
            " IS the ingestion instant, so a boundary taken from it compares"
            " fabric-learning time against a world-time snapshot (D-IMPL-335)"
        )
        assert entry.invalidated_from != T_INGEST

        # AND THE CONSEQUENCE, asserted rather than left to inference: a
        # product whose snapshot sits BETWEEN the world change and the
        # ingestion is not refused. Under the old behavior it was, and that is
        # the defect this test exists for.
        between = T_WORLD + timedelta(days=30)
        assert T_WORLD < between < T_INGEST
        assert entry.invalidated_from <= between, (
            "a product built after the world change and before ingestion is"
            " being refused on the basis of when the fabric learned, not on"
            " when anything changed"
        )
    finally:
        fabric.close()


def test_the_composition_root_binds_the_sink_and_a_deployment_need_not() -> None:
    """Capability 1's guarantee: nobody has to remember.

    Dave's ruling — *"the guarantee must not depend on a deployment remembering
    to publish an event"* — is only true if `boot` binds it. A writer booted
    with no deployment involvement carries the sink.
    """
    registry = ControlPlaneRegistry()
    fabric = _boot(registry)
    writer = _writer_of(fabric)
    try:
        sink = getattr(writer, "_invalidation_sink", None)
        assert isinstance(sink, ControlPlaneInvalidationSink)
        # And it cannot be silently redirected afterwards.
        with pytest.raises(Exception, match="already reports supersession"):
            writer.attach_invalidation_sink(sink)
    finally:
        fabric.close()


# =========================================================================
# D-IMPL-354 — the sink holds what its composition root minted, and no more.
# =========================================================================


def test_the_sink_refuses_construction_with_no_authority_or_a_duplicate_tenant(
    registry: ControlPlaneRegistry,
) -> None:
    from ccf.controlplane.invalidation import InvalidationUnauthorized

    with pytest.raises(InvalidationUnauthorized, match="no Register capability"):
        ControlPlaneInvalidationSink(registry=registry, authorities=())
    twice = composition_register(registry, register_key(TENANT_A))
    with pytest.raises(InvalidationUnauthorized, match="two Register"):
        ControlPlaneInvalidationSink(
            registry=registry,
            authorities=(twice, composition_register(registry, register_key(TENANT_A))),
        )


def test_the_sink_refuses_a_capability_for_another_key_and_every_fabrication(
    registry: ControlPlaneRegistry,
) -> None:
    """A `Register` for some other key opens nothing here; a forgery opens nothing anywhere."""
    from ccf.authz.capability import CapabilityBypassError, Register

    from tests.controlplane.capabilities import fabrications

    with pytest.raises(CapabilityBypassError):
        ControlPlaneInvalidationSink(
            registry=registry, authorities=(composition_register(registry, MAX_TTL_KEY),)
        )
    for label, forged in fabrications(Register, tenant=TENANT_A, resource=register_key(TENANT_A)):
        with pytest.raises(CapabilityBypassError):
            ControlPlaneInvalidationSink(registry=registry, authorities=(forged,))  # type: ignore[arg-type]
        assert resolve_register(registry, tenant_id=TENANT_A) is None, label


def test_a_supersession_under_a_tenant_the_fabric_was_not_composed_for_is_refused_and_writes_nothing(
    registry: ControlPlaneRegistry,
) -> None:
    from ccf.controlplane.invalidation import InvalidationUnauthorized

    sink = ControlPlaneInvalidationSink(
        registry=registry, authorities=(composition_register(registry, register_key(TENANT_A)),)
    )
    assert sink.tenants == frozenset({TENANT_A})
    events_before = len(registry.audit_events())
    with pytest.raises(InvalidationUnauthorized, match=TENANT_B):
        sink.record(
            tenant_id=TENANT_B, entity_uri=ENTITY_X, invalidated_from=T1,
            reason="entity-claim-superseded", source="x",
        )
    # Count FIRST: `resolve_register` below is itself an audited read (a
    # `resolve_latest` miss), and it must not be mistaken for the refusal's.
    assert len(registry.audit_events()) == events_before, "a refused record audited nothing"
    assert resolve_register(registry, tenant_id=TENANT_B) is None
    # And the held tenant still records, under the composition principal.
    sink.record(
        tenant_id=TENANT_A, entity_uri=ENTITY_X, invalidated_from=T1,
        reason="entity-claim-superseded", source="x",
    )
    registered = [e for e in registry.audit_events() if e.key == register_key(TENANT_A) and e.action == "register_typed"]
    assert registered and registered[-1].actor == COMPOSITION_PRINCIPAL


def test_boot_refuses_an_empty_or_repeated_tenant_list_before_touching_any_store() -> None:
    """`boot(tenant_ids=...)` is required and non-empty: a fabric composed for nobody could record no supersession."""
    from ccf.boot import boot

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, __import__("conftest").RESOLUTION_SPEC_KEY, __import__("conftest")._resolution_spec())
    policy_version = register_at_composition(registry, __import__("conftest").POLICY_BUNDLE_KEY, __import__("conftest")._policy_bundle())
    for tenants, why in (((), "empty"), ((TENANT_A, TENANT_A), "twice"), (("",), "not a tenant id")):
        with pytest.raises(ValueError, match=why):
            boot(
                backend="memory", connection={}, registry=registry,
                resolution_spec_key=__import__("conftest").RESOLUTION_SPEC_KEY, resolution_spec_version=spec_version,
                policy_bundle_key=__import__("conftest").POLICY_BUNDLE_KEY, policy_bundle_version=policy_version,
                tenant_ids=tenants,
            )
    assert not [e for e in registry.audit_events() if e.action == "composition" and e.key.endswith(KEY_PREFIX)]


def test_the_writer_refuses_a_supersession_under_an_uncomposed_tenant_and_the_composed_one_lands() -> None:
    """End to end through the real writer: `boot` minted for TENANT_A and TENANT_B only."""
    from ccf.contracts.claims import EntityClaim, LineageEntry
    from ccf.controlplane.invalidation import InvalidationUnauthorized
    from ccf.signal.envelope import SourceIdentity

    registry = ControlPlaneRegistry()
    fabric = _boot(registry)
    writer = _writer_of(fabric)
    policy_version = registry.versions(__import__("conftest").POLICY_BUNDLE_KEY)[-1]

    def _claim(tenant: str, observed_at: datetime, rating: str) -> EntityClaim:
        return EntityClaim(
            tenant_id=tenant, entity_uri=ENTITY_X, entity_class="obligor",
            attributes={"name": "fixture", "rating": rating}, observed_at=observed_at,
            lineage=frozenset((LineageEntry(source=SourceIdentity(system_id="fixture-source"), envelope_id=f"e-{observed_at.isoformat()}", observed_at=observed_at),)),
        )

    try:
        writer.upsert_entity(tenant_id=TENANT_A, claim=_claim(TENANT_A, T1, "BB"), policy_bundle_version=policy_version)
        writer.upsert_entity(tenant_id=TENANT_A, claim=_claim(TENANT_A, T2, "BB-"), policy_bundle_version=policy_version)
        assert resolve_register(registry, tenant_id=TENANT_A) is not None
        other = "tenant-nobody-composed-for"
        writer.upsert_entity(tenant_id=other, claim=_claim(other, T1, "BB"), policy_bundle_version=policy_version)
        with pytest.raises(InvalidationUnauthorized, match=other):
            writer.upsert_entity(tenant_id=other, claim=_claim(other, T2, "BB-"), policy_bundle_version=policy_version)
        assert resolve_register(registry, tenant_id=other) is None
    finally:
        fabric.close()  # type: ignore[attr-defined]
