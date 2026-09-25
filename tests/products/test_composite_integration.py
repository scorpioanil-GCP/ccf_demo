"""`INT-01a` — one governed question, all the way through, with nothing faked.

`D-IMPL-336` Amendment 4, then **Amendment 5**. Dave's constraint, verbatim:
*"one path through the real machinery; fixture product acceptable; **no
injected outcomes map, no dictionary standing in for grant resolution, no
`deliver()` helper bypassing the delivery boundary**."*

Every unit test of this surface hands `compose_children` an outcomes map. That
proves composition and proves nothing about how a child GETS there, which is
where `O1` and `O2` both lived. This module removes the map. What runs is:

    effective grant -> actual skill dispatch -> the child's governed delivery
    -> fit checks -> compose

through the **shipped** `ccf.products.child_resolver.GrantBoundChildResolver`,
and the assertions are read back **off the store**, because the claim is that
a composite is auditable afterwards and an in-memory object cannot carry that.

**The child deliberately invokes an operator the parent does not**, which is
`R4` in its natural form: this module could not have been written before R4
was resolved, because every real child of another class collided with Gate 2.

The deployment is built by :mod:`tests.products.composite_fixture`, which
`tests/crossproc/test_composite_provider_independence.py` also drives — with
the atomic product produced in **another process**. Sharing that module is how
*"acquisition rebinds without changing the composite"* becomes a test rather
than a claim about two files agreeing.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from ccf.products.contract import ProductLineage
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import TENANT
from datetime import UTC, datetime

from ccf.products.contract import ProductLineage
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

from tests.products.composite_fixture import (
    CHILD_CALLABLE,
    CHILD_CLASS,
    CHILD_SKILL,
    _ledger,
    ask_composite,
    boot_composite,
    build_composite,
)
from tests.products.provider_boot import CHILD_CLASS
from tests.products.test_resolver_seam import (
    ASKED_AT,
    THRESHOLD_PARAMETER,
    _arguments,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    _Booted,
)
from tests.composition import composition_register
from ccf.controlplane.invalidation import register_key
from tests.skills.authority import revoke_capability


@pytest.fixture()
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """One deployment declaring TWO product classes: a parent and its child."""
    yield from boot_composite(tmp_path)


def _wire(booted: _Booted, *, grant: bool = True) -> tuple[object, object]:
    return build_composite(booted, grant=grant)


def _ask(resolver: object) -> object:
    return ask_composite(resolver)  # type: ignore[arg-type]


def test_int01a_one_governed_question_through_the_whole_machinery(
    booted: _Booted,
) -> None:
    """`INT-01a`. Grant, dispatch, door, attestation, admission, composition.

    The assertions are made against the record read back **off the store**,
    not against the in-memory outcome, because the claim is that a composite
    is auditable afterwards and an in-memory object cannot carry that.
    """
    resolver, children = _wire(booted)
    outcome = _ask(resolver)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)

    # `R4`, in its natural form: the child's own operator is in the served
    # lineage, and the parent's engine never ran it.
    operators = outcome.product.lineage.operators_invoked
    assert "similarity.corpus-select" in operators
    assert "traversal.typed-neighborhood" in operators

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_ref.uri)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1
    row = rows[0]
    assert row.required_product_class == CHILD_CLASS
    assert row.outcome_status == "admitted"
    # The producer identity is the CATALOG's and the LEDGER's, never a string
    # this test wrote (`O2`).
    assert row.producing_skill_name == CHILD_SKILL
    assert row.grant_hash
    # `D-IMPL-336` **Amendment 5**: a locally dispatched child names NO
    # producing fabric, because this fabric authenticated no producer — it ran
    # a skill it had granted. The basis records which authority applied.
    assert row.producing_fabric is None
    assert row.eligibility_basis == "local-register"
    assert row.child_asked_at == ASKED_AT
    # ...and the entities came from the child's OWN persisted record, read
    # through the one store access the resolver makes for a local child.
    # ASSERTED, not merely commented: the close panel found this line was a
    # DUPLICATE of the one above it, so the sentence promised something no
    # assertion carried.
    #
    # `local-register` is now that assertion. Before the close panel it was
    # not — the basis was recorded whether or not any entity had been resolved,
    # which is precisely the `F3` regression the panel measured. Since a local
    # child with no execution record refuses outright, this row reading
    # `local-register` means the register was consulted with real entities
    # taken from the child's own persisted record.
    assert row.eligibility_basis == "local-register"


def test_int01a_a_required_child_with_NO_GRANT_refuses(booted: _Booted) -> None:
    """The negative control, and it is the one that matters for `O2`.

    Nothing about the deployment changes except that the grant is never
    requested. The catalog entry still exists, the callable is still
    registered, and the door still works — so a resolver that dispatched on
    catalog presence rather than on an in-force grant would serve here.
    """
    resolver, _children = _wire(booted, grant=False)
    outcome = _ask(resolver)
    assert not isinstance(outcome, ServedProduct), outcome
    assert outcome.kind == "composite-child-refusal"


def test_int01a_a_REVOKED_grant_refuses_the_same_way(booted: _Booted) -> None:
    """Revocation takes effect without re-wiring anything.

    The resolver is built with the grant in force, then the grant is revoked
    through the Control Plane and the same resolver is asked again. Proves the
    bound view is read at resolution time rather than captured at wiring time
    — which is what makes a revocation a governance act rather than a restart.
    """
    resolver, _children = _wire(booted)
    assert isinstance(_ask(resolver), ServedProduct)

    ledger, agent_hash, _definition, _catalog = _ledger(booted)
    effective = ledger.effective_hashes(agent_hash)
    assert len(effective) == 1, effective
    ledger.revoke(revoke_capability(next(iter(effective)), tenant=TENANT))

    after = _ask(resolver)
    assert not isinstance(after, ServedProduct), after
    assert after.kind == "composite-child-refusal"


def test_cmpr01_a_REFUSED_composite_records_which_children_it_tried(
    booted: _Booted,
) -> None:
    """`CMP-R-01`: the rows reach the persisted record on the refused branch.

    `compose_children` has always built a row for every declared requirement,
    refused or not — deliberately, because a requirement that produced nothing
    and left no row is indistinguishable from one that was never declared.
    Those rows reached the record on the **served** path only, so the one case
    where a reader most needs to know WHICH child failed was the case the
    record did not say.

    Read back **off the store**, because the claim is about what was persisted.
    """
    resolver, _children = _wire(booted, grant=False)
    outcome = _ask(resolver)
    assert not isinstance(outcome, ServedProduct), outcome
    assert outcome.kind == "composite-child-refusal"

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_reference)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1, "the refused composite recorded no child rows"
    assert rows[0].required_product_class == CHILD_CLASS
    assert rows[0].required is True
    # The reason the composite refused is on the row, not only in the envelope
    # detail a caller may never see at `minimal` disclosure.
    assert rows[0].outcome_status != "admitted"


def test_cmpr01_a_NON_composite_refusal_records_no_rows_and_is_unchanged(
    booted: _Booted,
) -> None:
    """The control. `()` is the true claim for a refusal about no children.

    The widened seam defaults to `()` and `child_resolutions` is
    hash-transparent there, so a refusal that declares no children records the
    bytes it always recorded — the parameter buys the composite case without
    moving any existing record's content address.
    """
    from ccf.products.request import ProductRequest

    resolver, _children = _wire(booted)
    outcome = resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            # A parameter the request contract requires, omitted: refused
            # before any child is considered.
            parameters={},
        ),
    )
    assert not isinstance(outcome, ServedProduct), outcome
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_reference)
        )
    )
    assert record.content_generation_path.child_resolutions == ()


def test_r5_the_record_alone_RECONSTRUCTS_the_composite(booted: _Booted) -> None:
    """`R5` / `CMP-R-02`: a composite is reconstructible from what was written.

    **The claim, precisely.** A composite's content address covers its lineage
    — the `D-IMPL-31` union — and its expiry — the floor over its stalest
    constituent. Before this, `ChildResolution` carried a `child_lineage_ref`
    (a hash, which COMPARES lineages without REBUILDING one) and no child
    expiry at all. So no rehydrator could reproduce either value, and a
    composite was not replayable however faithfully the parent's plan re-ran.

    **Dave's constraint:** *"Replay uses retained child artifacts and recorded
    composition evidence — not fresh calls to the atomic providers."* So this
    test re-derives both quantities from the PERSISTED ROWS and holds them
    against the served product, and it never calls the child's skill again.
    The child resolver is not even wired.
    """
    from ccf.products.composition import compose_expiry, compose_lineage
    from ccf.products.contract import MaxTTL, ProductLineage

    resolver, _children = _wire(booted)
    outcome = _ask(resolver)
    assert isinstance(outcome, ServedProduct), outcome
    served = outcome.product

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_ref.uri)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert rows and all(r.outcome_status == "admitted" for r in rows)

    # Everything below comes from the ROWS. Nothing is re-dispatched.
    assert all(r.child_operators_invoked is not None for r in rows)
    assert all(r.child_expires_at is not None for r in rows)

    own = ProductLineage(
        operators_invoked=frozenset(record.content_generation_path.operator_plan),
        policy_bundle_versions=served.lineage.policy_bundle_versions,
        graph_snapshot_at=served.lineage.graph_snapshot_at,
    )
    rebuilt = compose_lineage(
        [
            own,
            *(
                ProductLineage(
                    operators_invoked=r.child_operators_invoked or frozenset(),
                    policy_bundle_versions=r.child_policy_bundle_versions
                    or frozenset(),
                    graph_snapshot_at=r.child_graph_snapshot_at or ASKED_AT,
                )
                for r in rows
            ),
        ]
    )
    # The union, re-derived from the record, IS the served lineage.
    assert rebuilt.operators_invoked == served.lineage.operators_invoked

    rebuilt_expiry = compose_expiry(
        constituent_validities=[r.child_expires_at for r in rows if r.child_expires_at],
        max_ttl=MaxTTL(seconds=_arguments(booted)["product_ttl_seconds"]),
        ttl_anchor_at=record.recorded_at,
    )
    # ...and so is the floor.
    assert rebuilt_expiry == served.expires_at


def test_r5_the_child_ROWS_are_what_carry_it_not_the_lineage_hash(
    booted: _Booted,
) -> None:
    """The sabotage that makes the test above about the new fields.

    `child_lineage_ref` was already recorded before `R5`. If reconstruction
    were possible from it, the finding would not exist. Asserted by showing
    the ref is a hash of the child's lineage — it identifies, and identifying
    is not rebuilding.
    """
    from ccf.contracts.canonical import content_hash
    from ccf.products.contract import ProductLineage

    resolver, _children = _wire(booted)
    outcome = _ask(resolver)
    assert isinstance(outcome, ServedProduct), outcome
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_ref.uri)
        )
    )
    row = record.content_generation_path.child_resolutions[0]
    assert row.child_operators_invoked is not None
    rebuilt = ProductLineage(
        operators_invoked=row.child_operators_invoked,
        policy_bundle_versions=row.child_policy_bundle_versions or frozenset(),
        graph_snapshot_at=row.child_graph_snapshot_at or ASKED_AT,
    )
    # The rebuilt lineage hashes to exactly the ref that was already there —
    # which is the point: the ref could CHECK this reconstruction and never
    # produce it.
    assert content_hash(rebuilt) == row.child_lineage_ref


def test_int01b_a_composite_serves_as_ANOTHER_composites_child(
    booted: _Booted,
) -> None:
    """`INT-01b`: leaf -> composite -> higher composite, through the shipped path.

    A composite serving as another's child was type-legal and untested. The
    chain here is three deep and every link is the same machinery: a granted
    skill, a real dispatch, a `door_answer` crossing, and
    `CompositeAdmissionGate.admit`.

    **Nothing about being a composite changes how the middle product is
    acquired**, which is the property this test exists to show — the top
    declares `requires` against a product class, not against an assembler, and
    could not tell that its child had children of its own.

    The assertion that carries the nesting is the LEAF's operator appearing in
    the TOP's lineage. It can only get there by travelling through the middle,
    so a chain that silently flattened to two levels would fail here.
    """
    from tests.products.composite_fixture import (
        HIGHER_CLASS,
        ask_higher,
        build_higher_composite,
    )

    middle, _middle_children = _wire(booted)
    higher, _higher_children = build_higher_composite(booted, middle)

    outcome = ask_higher(higher)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)

    operators = outcome.product.lineage.operators_invoked
    # the leaf's operator, two levels down
    assert "similarity.corpus-select" in operators
    assert "traversal.typed-neighborhood" in operators

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_ref.uri)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1
    # The top's own child is the MIDDLE product, not the leaf: each level
    # records what IT admitted, and the leaf's row belongs to the middle's
    # record rather than being flattened into this one.
    assert rows[0].required_product_class == PRODUCT_CLASS
    assert rows[0].outcome_status == "admitted"
    # `R5` across two levels: the middle's operator set, as the top saw it,
    # already carries the leaf's — so the top is reconstructible without
    # re-acquiring anything.
    assert rows[0].child_operators_invoked is not None
    assert "similarity.corpus-select" in rows[0].child_operators_invoked


def test_int01b_the_top_expiry_is_FLOORED_by_the_deepest_constituent(
    booted: _Booted,
) -> None:
    """The expiry floor composes down the chain, not just across one level.

    `D-IMPL-31`'s floor says a composite is never labelled fresher than its
    stalest constituent. Over a chain that has to hold transitively, or a
    two-level composite could outlive the leaf its answer rests on.
    """
    from tests.products.composite_fixture import (
        HIGHER_CLASS,
        ask_higher,
        build_higher_composite,
    )

    middle, _mc = _wire(booted)
    higher, _hc = build_higher_composite(booted, middle)

    top = ask_higher(higher)
    assert isinstance(top, ServedProduct), getattr(top, "detail", top)

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=top.replay_ref.uri)
        )
    )
    middle_expiry = record.content_generation_path.child_resolutions[0].child_expires_at
    assert middle_expiry is not None
    assert top.product.expires_at is not None
    assert top.product.expires_at <= middle_expiry, (
        "the top outlived the constituent it was assembled from"
    )


def test_a_child_whose_door_reports_NO_replay_ref_refuses_the_composite(
    booted: _Booted,
) -> None:
    """The RESOLVER half of the `F3` re-close, pinned by close panel 2.

    The gate refuses a local child with no execution record. What nothing
    pinned was the resolver's side: `_touched_entities` returns `None` when the
    child's `DoorOutcome` carries no `replay_ref`, and fable measured that
    changing that `return None` to `return ()` left all 67 tests green — `()`
    being the *verified* claim that the child read nothing, which sails through
    the gate and records `local-register`.

    The two halves have to be pinned separately because either one alone still
    lets a child through. This drives the REAL resolver over a REAL door whose
    producer reports no replay reference — a state the wire contract permits
    for a producer that is not a shipped door.
    """
    from ccf.products.door import DoorOutcome

    resolver, children = _wire(booted)

    original = children._callables.resolve(CHILD_CALLABLE)

    def without_replay_ref(arguments: object) -> object:
        answered = original(arguments)  # type: ignore[arg-type]
        outcome = DoorOutcome.model_validate_json(answered["outcome"])
        stripped = outcome.model_copy(update={"replay_ref": None})
        return {"outcome": stripped.model_dump_json()}

    children._callables._callables[CHILD_CALLABLE] = without_replay_ref

    outcome = _ask(resolver)
    assert not isinstance(outcome, ServedProduct), (
        "a child with no resolvable execution record was composed, and the row"
        " would have claimed local-register as its authority"
    )
    assert outcome.kind == "composite-child-refusal"


def test_a_peered_leg_with_NO_peering_gate_refuses_rather_than_raising(
    booted: _Booted,
) -> None:
    """The peered leg of the shipped resolver, which no test executed.

    Close panel 2 measured that deleting the `if self._peering_gate is None`
    guard — which would make the leg raise `AttributeError` on `None.admit` —
    left the suite green, because nothing ever reached it.

    A deployment that binds a peering-produced child without binding a
    `PeeringAdmissionGate` is mis-wired. That must be a governed refusal, not a
    crash: `provenance-unverified` says exactly what is absent.
    """
    from ccf.products.contract import ChildRequirement
    from ccf.skills.dispatch import PeeringInvocation

    _resolver, children = _wire(booted)
    requirement = ChildRequirement(
        product_class=CHILD_CLASS, required=True, compatible_from="1.0.0"
    )
    assert children._peering_gate is None

    outcome = children._admit_peered(
        PeeringInvocation(
            skill_name="child-door-skill",
            skill_type="peering",
            endpoint="fixture-endpoint",
            products=(),
            arguments={},
        ),
        requirement,
        consumer_lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.typed-neighborhood"}),
            policy_bundle_versions=frozenset({"fixture"}),
            graph_snapshot_at=ASKED_AT,
        ),
        now=ASKED_AT,
    )
    assert isinstance(outcome, str), outcome
    assert "binds no PeeringAdmissionGate" in outcome


# --- INT-01b: dependency invalidation from a REAL L2 source change ----------
#
# The last ruled `D-IMPL-336` deliverable. The nested chain already exists and
# is not redesigned here; what is added is the one thing it never proved —
# that a composite inherits dependency invalidation from a real graph write,
# through the boot-bound L2 writer, by COMPOSITION rather than by the test
# attaching the leaf's entity to it.

#: When the leaf was assembled. The chain's normal instant.
T0 = ASKED_AT
#: When the world changed. Between the leaf and the re-serve, on purpose.
T_WORLD = datetime(2026, 3, 2, 13, 0, tzinfo=UTC)
#: When the fabric LEARNED it. Months later, so a boundary at the wrong clock
#: would be unmistakable (`D-IMPL-335`).
T_INGEST = datetime(2026, 6, 15, tzinfo=UTC)
#: When the dependent products are re-served. After the world change.
T_LATER = datetime(2026, 3, 2, 14, 0, tzinfo=UTC)


def _supersede_the_leafs_entity(booted: _Booted) -> None:
    """Change the underlying entity through the REAL boot-bound L2 writer.

    **Everything forbidden is avoided, and the list is the point.** Nothing
    here writes to `EntityInvalidationRegister`, calls the invalidation sink,
    seeds a synthetic boundary, or attaches the leaf's entity to either
    composite. One envelope goes through `worker.ingest`; the writer
    `ccf.boot.boot` bound the sink to publishes the boundary itself
    (`D-IMPL-334`), at the instant `D-IMPL-335` rules.

    The payload differs from the fixture's on a resolution-spec ATTRIBUTE
    (`classification`), keyed on the same `account_ref` — so it resolves to the
    same entity and is a genuinely different claim, which is what supersedes
    rather than deduplicates.
    """
    booted.fabric.handle.worker.ingest(
        SignalEnvelope(
            tenant_id=TENANT,
            envelope_id="envelope-supersede-int01b",
            source=SourceIdentity(system_id="fixture-system"),
            # WHEN THE FABRIC LEARNED IT. Far from the world instant, so the
            # two clocks cannot be confused for one another.
            ingestion_timestamp=T_INGEST,
            # WHEN IT BECAME TRUE. This is what the boundary must take.
            observed_time=T_WORLD,
            raw_payload={
                "account_ref": "acct-1",
                "classification": "fixture-reclassified",
                "label": "fixture account",
            },
        )
    )


def _ask_at(resolver: object, schema: str, version: str, at: datetime) -> object:
    return resolver(  # type: ignore[operator]
        tenant=TENANT,
        product_class=schema,
        version=version,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=schema,
            schema_version=version,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=at,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )


def test_int01b_a_real_L2_change_invalidates_the_NESTED_composite_chain(
    booted: _Booted,
) -> None:
    """`INT-01b`, the last ruled deliverable: dependency propagation by composition.

    **The property.** The middle and higher composites become dependent on the
    leaf's entity *because they consumed a governed child product whose own
    evidence carried the relationship* — not because this test copied the
    entity into them. Nothing here writes to `EntityInvalidationRegister`,
    calls the invalidation sink, seeds a synthetic boundary, or attaches the
    leaf's touched entity to either composite. One envelope goes through
    `worker.ingest`, and the writer `ccf.boot.boot` bound the sink to publishes
    the boundary itself.

    **The reachable case, found by sabotage rather than by design.** The first
    version of this test pinned the leaf to an instance built at `T0` and
    re-served the composite at a later instant, expecting the stale child to be
    refused as invalidated. It was refused — as **`as-of-mismatch`**. A child
    answering for `T0` cannot satisfy a composition asked at `T_LATER` at all,
    because `F15`'s one-`as_of` invariant fires first. The test passed for the
    wrong reason, and the prescribed sabotage is what exposed it: neutering the
    child's dependency evidence left it green.

    The case that *is* reachable is **historical reconstruction**, which is
    what `D-IMPL-334` exists for — *"a previously derived product that read it
    at an older snapshot is no longer eligible to be served."* The same
    question is asked again at `T0`, **after** the world changed at
    `T_WORLD > T0`. Every level's graph snapshot is now before the boundary.

    **Where the refusal starts, measured:** at the LEAF's own gate, inside its
    own governed delivery, before `CompositeAdmissionGate.admit` is ever
    reached. The composite refuses because the child product it consumed
    refused. That is the propagation, and the sabotages below isolate it.

    **What this module does NOT prove.** Dependency SELECTIVITY — that a
    product depending on a different entity is unaffected — is not expressible
    here, because the fixture graph holds one entity. It stays covered by
    `tests/products/test_dependency_invalidation.py`. INT-01b proves nested
    propagation and re-derivation, and nothing wider.
    """
    from ccf.controlplane.invalidation import ControlPlaneInvalidationSink
    from tests.products.composite_fixture import (
        HIGHER_CLASS,
        _child_resolver,
        build_higher_composite,
    )

    # 1-3. the chain, built through the shipped path at T0.
    middle, _children = _wire(booted)
    higher, _hc = build_higher_composite(booted, middle)
    assert isinstance(
        _ask_at(middle, PRODUCT_CLASS, PRODUCT_VERSION, T0), ServedProduct
    )
    first_higher = _ask_at(higher, HIGHER_CLASS, "1.0.0", T0)
    assert isinstance(first_higher, ServedProduct), getattr(
        first_higher, "detail", first_higher
    )

    # 4. the initial dependent state: no boundary exists yet.
    sink = ControlPlaneInvalidationSink(
        registry=booted.control_plane,
        authorities=(composition_register(booted.control_plane, register_key(TENANT)),),
    )
    assert sink.register(TENANT) is None

    # 5-6. the world changes, through the real boot-bound writer and nothing
    # else. The boundary is published by the writer, not by this test.
    _supersede_the_leafs_entity(booted)
    register = sink.register(TENANT)
    assert register is not None, "the boot-bound writer published no boundary"
    boundaries = {e.invalidated_from for e in register.entries}
    # `D-IMPL-335`: the SOURCE/world clock, never the ingestion clock. The
    # split-clock control itself already lives at
    # `tests/products/test_dependency_invalidation.py` and is not restated
    # here; this is the pin that the NESTED path takes the same clock.
    assert boundaries == {T_WORLD}, boundaries
    assert T_INGEST not in boundaries

    # where it starts: the leaf's own governed delivery refuses.
    leaf_again = _ask_at(_child_resolver(booted), CHILD_CLASS, "1.0.0", T0)
    assert not isinstance(leaf_again, ServedProduct), (
        "the leaf served a reconstruction whose entity had since been superseded"
    )

    # the leaf-dependent middle composite refuses...
    after_middle = _ask_at(middle, PRODUCT_CLASS, PRODUCT_VERSION, T0)
    assert not isinstance(after_middle, ServedProduct), (
        "the middle composite served on a child that was no longer eligible"
    )
    assert after_middle.kind == "composite-child-refusal"

    # ...and so does the dependent higher composite, one level further up.
    after_higher = _ask_at(higher, HIGHER_CLASS, "1.0.0", T0)
    assert not isinstance(after_higher, ServedProduct), (
        "the higher composite served on a middle composite that had refused"
    )
    assert after_higher.kind == "composite-child-refusal"

    # RE-DERIVATION, and it is NOT a selectivity control. The same chain,
    # over the same entity, asked at an instant AFTER the change, serves.
    #
    # **What this does NOT show**: that a product depending on a DIFFERENT
    # entity still serves. The fixture graph holds ONE entity, so this module
    # cannot express dependency SELECTIVITY at all, and an earlier version of
    # this comment wrongly claimed the instant "discriminates the same
    # property". It does not — re-derivation and selectivity are different
    # claims. Selectivity is covered by the existing `D-IMPL-334`/`D-IMPL-335`
    # regression at `tests/products/test_dependency_invalidation.py`, which
    # has the entities to express it. What INT-01b proves is nested
    # PROPAGATION and RE-DERIVATION.
    assert isinstance(
        _ask_at(_child_resolver(booted), CHILD_CLASS, "1.0.0", T_LATER),
        ServedProduct,
    )
    redrawn = _ask_at(middle, PRODUCT_CLASS, PRODUCT_VERSION, T_LATER)
    assert isinstance(redrawn, ServedProduct), getattr(redrawn, "detail", redrawn)

    # permitted re-derivation restores the whole chain, two levels up.
    restored = _ask_at(higher, HIGHER_CLASS, "1.0.0", T_LATER)
    assert isinstance(restored, ServedProduct), getattr(restored, "detail", restored)


def test_int01b_the_inherited_composition_state_survives_on_the_nested_chain(
    booted: _Booted,
) -> None:
    """The four already-built properties, re-asserted on the REAL nested path.

    Dave: *"this is a regression assertion around the real nested path"* — the
    mechanisms are not reopened, only confirmed to survive two levels of
    composition rather than one.
    """
    from tests.products.composite_fixture import HIGHER_CLASS, build_higher_composite

    middle, _mc = _wire(booted)
    higher, _hc = build_higher_composite(booted, middle)
    top = _ask_at(higher, HIGHER_CLASS, "1.0.0", T0)
    assert isinstance(top, ServedProduct), getattr(top, "detail", top)

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=top.replay_ref.uri)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1
    row = rows[0]

    # (1) child dependency lineage reaches the parent — the LEAF's operator,
    # two levels down, is in the top's lineage. It can only arrive by
    # travelling through the middle.
    assert "similarity.corpus-select" in top.product.lineage.operators_invoked

    # (2) parent expiry remains bounded by its children.
    assert row.child_expires_at is not None
    assert top.product.expires_at is not None
    assert top.product.expires_at <= row.child_expires_at

    # (3) the persisted evidence identifies the contributing governed product —
    # by class, by verified address, and by the grant that authorized it.
    assert row.required_product_class == PRODUCT_CLASS
    assert row.outcome_status == "admitted"
    assert row.child_content_address and row.grant_hash
    assert row.child_operators_invoked is not None

    # (4) replay reconstructs the served composite from the record alone —
    # re-deriving the union and the floor from the ROWS, calling no child
    # skill. Proven at one level by `test_r5_*`; confirmed here at two.
    from ccf.products.composition import compose_expiry, compose_lineage
    from ccf.products.contract import MaxTTL

    own = ProductLineage(
        operators_invoked=frozenset(record.content_generation_path.operator_plan),
        policy_bundle_versions=top.product.lineage.policy_bundle_versions,
        graph_snapshot_at=top.product.lineage.graph_snapshot_at,
    )
    rebuilt = compose_lineage(
        [
            own,
            ProductLineage(
                operators_invoked=row.child_operators_invoked,
                policy_bundle_versions=row.child_policy_bundle_versions or frozenset(),
                graph_snapshot_at=row.child_graph_snapshot_at or T0,
            ),
        ]
    )
    assert rebuilt.operators_invoked == top.product.lineage.operators_invoked
    assert (
        compose_expiry(
            constituent_validities=[row.child_expires_at],
            max_ttl=MaxTTL(seconds=_arguments(booted)["product_ttl_seconds"]),
            ttl_anchor_at=record.recorded_at,
        )
        == top.product.expires_at
    )


def test_a_child_naming_ANOTHER_products_replay_record_is_refused(
    booted: _Booted,
) -> None:
    """The final review's HIGH finding: MISATTRIBUTED eligibility evidence.

    `F3` closed the **absent**-evidence case on this leg — a local child with
    no execution record refuses. This is the **misattributed** case, which
    reads as present and passes: `_touched_entities` took the entities from
    whatever record the producing skill NAMED, never checking that the record
    describes the product being admitted. `contract` was a declared parameter
    the method did not read.

    The asymmetry was the tell. The admission gate already refuses to trust the
    producer on the content address — it recomputes `content_hash(contract)`
    itself — and `DoorOutcome` already binds `replay_ref` on the refused path.
    Only the served path left it free, while the evidence needed to close it,
    `product_content_address`, was already a required field.

    Asserted here through the SHIPPED resolver: the door serves an honest
    contract and an honest address, and points `replay_ref` at a real,
    resolvable record of a different product.
    """
    from ccf.products.child_resolver import ChildRecordMismatch
    from ccf.products.door import DoorOutcome

    resolver, children = _wire(booted)

    # a real, resolvable record — of something else entirely
    first = _ask_at(resolver, PRODUCT_CLASS, PRODUCT_VERSION, T0)
    assert isinstance(first, ServedProduct), getattr(first, "detail", first)
    foreign_ref = first.replay_ref.uri

    original = children._callables.resolve(CHILD_CALLABLE)

    def honest_product_foreign_record(arguments: object) -> object:
        answered = original(arguments)  # type: ignore[arg-type]
        outcome = DoorOutcome.model_validate_json(answered["outcome"])
        # product_json and content_address untouched, so the gate's own
        # recomputation passes. ONLY the record reference is substituted.
        swapped = outcome.model_copy(update={"replay_ref": foreign_ref})
        return {"outcome": swapped.model_dump_json()}

    children._callables._callables[CHILD_CALLABLE] = honest_product_foreign_record

    with pytest.raises(ChildRecordMismatch) as raised:
        _ask_at(resolver, PRODUCT_CLASS, PRODUCT_VERSION, T0)
    assert "record of THIS product or not at all" in str(raised.value)

    # ...and the honest pairing still serves, so this is a differential rather
    # than a method that now refuses everything.
    children._callables._callables[CHILD_CALLABLE] = original
    assert isinstance(
        _ask_at(resolver, PRODUCT_CLASS, PRODUCT_VERSION, T0), ServedProduct
    )


def test_the_record_mismatch_is_wrapped_OPAQUE_at_the_delivery_doors() -> None:
    """`D-IMPL-253` Q20: a runtime failure crosses a door as an id, not prose.

    Found by the focused review of the binding repair. `ChildRecordMismatch`
    was a `RuntimeError`, and the MCP egress door wraps only
    ``(ValueError, TypeError, LookupError, OSError)`` into an opaque
    ``ccf-runtime-failure`` id — *no message, no type name, no traceback*. So
    the one exception this leg could newly raise delivered a replay-reference
    URI and two content addresses to the client.

    The base class is therefore load-bearing, and the precedent settles it:
    `ccf.replay.serve.ProductRecordMismatch` is the same defect class one layer
    up — a record that does not describe the product it is filed against
    (`D-IMPL-279`) — and is a `ValueError` for exactly this reason.

    Asserted against the door's OWN tuple, read from the runtime rather than
    restated here, so widening or narrowing that tuple moves this test.
    """
    import inspect
    import re

    from ccf.products.child_resolver import ChildRecordMismatch
    from ccf.replay.serve import ProductRecordMismatch

    source = inspect.getsource(
        __import__("ccf_runtime.mcp.egress", fromlist=["x"])
    )
    match = re.search(r"except \(([^)]*)\) as exc:\s*\n\s*raise _opaque_failure", source)
    assert match is not None, "the door's opaque-failure guard has moved"
    caught = tuple(
        getattr(__import__("builtins"), name.strip()) for name in match.group(1).split(",")
    )

    assert issubclass(ChildRecordMismatch, caught), (
        "ChildRecordMismatch escapes the door's opaque wrap and would deliver"
        f" its message — a replay-ref URI and two addresses — to a client;"
        f" the door catches {[c.__name__ for c in caught]}"
    )
    # ...and it matches the precedent it is modelled on, rather than merely
    # happening to be catchable.
    assert issubclass(ProductRecordMismatch, caught)
    assert issubclass(ChildRecordMismatch, ValueError)
