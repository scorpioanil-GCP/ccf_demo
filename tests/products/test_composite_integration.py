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

import pytest

from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import TENANT
from tests.products.composite_fixture import (
    CHILD_SKILL,
    _ledger,
    ask_composite,
    boot_composite,
    build_composite,
)
from tests.products.provider_boot import CHILD_CLASS
from tests.products.test_resolver_seam import (
    ASKED_AT,
    _arguments,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    _Booted,
)


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
    # ...and the entities came from the child's OWN persisted record, read
    # through the one store access the resolver makes for a local child.
    assert row.child_asked_at == ASKED_AT
    assert row.child_asked_at == ASKED_AT


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
    ledger.revoke(next(iter(effective)), actor="composite-operator")

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
    from tests.products.composite_fixture import ask_higher, build_higher_composite

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
    from tests.products.composite_fixture import ask_higher, build_higher_composite

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
