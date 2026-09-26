"""The L2 write path: envelope in, resolved and policy-bound graph state out.

DESIGN.md §2A.3 (the four converging concerns) and §2A.5.4 (the write path end
to end). The conformance suite next door asserts what the *store* owes; this
module asserts what *assembly* owes — that source vocabulary becomes canonical
E and R under a stated temporal rule, with policy bound on the way in.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from ccf.assembly.worker import (
    NO_RESOLVING_RULE,
    EntityResolutionRule,
    EntityResolutionSpec,
    IdentityRefused,
    RelationshipResolutionRule,
    ResolvedEntity,
    SpecDrivenEntityResolution,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from tests.composition import register_at_composition

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT = "tenant-a"
SPEC_KEY = "test/entity-resolution-spec"
POLICY_KEY = "test/policy-bundle"
INGESTED_AT = datetime(2026, 2, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2026, 1, 15, tzinfo=UTC)


def envelope(
    *,
    envelope_id: str = "env-1",
    system_id: str = "core-banking",
    observed_time: datetime | None = OCCURRED_AT,
    payload: dict[str, Any] | None = None,
) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id=envelope_id,
        source=SourceIdentity(system_id=system_id),
        ingestion_timestamp=INGESTED_AT,
        observed_time=observed_time,
        raw_payload=payload
        if payload is not None
        else {
            "counterparty_lei": "5493001KJTIIGC8Y1R12",
            "counterparty_name": "Acme Holdings",
            "jurisdiction": "GB",
            "facility_id": "RCF-0001",
            "facility_type": "revolver",
            "currency": "GBP",
        },
    )


def test_ingest_resolves_entities_and_the_typed_edge_between_them(
    fabric: "FabricHandle",
) -> None:
    """One source event becomes two canonical E nodes and one first-class R.

    The edge is persisted, not derived at query time (INV-CH7-20): a later read
    finds it in the graph without re-deriving it from the payload, which is what
    lets it carry its own lineage and its own supersession history.
    """
    result = fabric.worker.ingest(envelope())

    assert len(result.entities) == 2
    assert len(result.relationships) == 1

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert {r.claim.entity_class for r in view.entities} == {
        "counterparty",
        "facility",
    }
    edge = view.relationships[0].claim
    assert edge.relationship_type == "obligor_of"
    assert edge.subject_uri.startswith("counterparty://")
    assert edge.object_uri.startswith("facility://")


def test_entity_uris_converge_across_source_systems(
    fabric: "FabricHandle",
) -> None:
    """The same identifier from two systems resolves to one node (INV-CH7-18).

    Convergence is the whole point of resolution: without it the graph holds
    two Acmes and every operator over it is wrong. The URI is derived from
    declared identity values, never from where the record lived, so it also
    survives a source migration (INV-CH8-01).
    """
    first = fabric.worker.ingest(envelope(envelope_id="env-1", system_id="core"))
    second = fabric.worker.ingest(envelope(envelope_id="env-2", system_id="kyc"))

    assert [r.node_key for r in first.entities] == [r.node_key for r in second.entities]

    uri = first.entities[0].node_key
    history = fabric.reader.entity_history(tenant_id=TENANT, entity_uri=uri)
    assert len(history) == 1, "one node, one claim — the state did not change"
    assert {e.source.system_id for e in history[0].claim.lineage} == {"core", "kyc"}
    assert {e.envelope_id for e in history[0].claim.lineage} == {"env-1", "env-2"}


def test_replaying_one_envelope_changes_nothing(fabric: "FabricHandle") -> None:
    """Idempotence end to end, not merely at the store (INV-CH7-17)."""
    fabric.worker.ingest(envelope())
    second = fabric.worker.ingest(envelope())

    assert all(r.lineage_added == 0 for r in second.entities)
    assert all(not r.claim_created for r in second.entities)


def test_valid_time_opens_at_the_source_time_when_the_source_can_say(
    fabric: "FabricHandle",
) -> None:
    """Bitemporal stitching: observed-time is ingestion, valid-time is the event."""
    fabric.worker.ingest(envelope())

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    claim = view.entities[0].claim

    assert claim.observed_at == INGESTED_AT
    assert claim.valid_from == OCCURRED_AT


def test_valid_time_stays_absent_when_the_source_cannot_say(
    fabric: "FabricHandle",
) -> None:
    """`D-IMPL-332` — unknown stays unknown, on the assembly path.

    **This test is the inversion of the one it replaces.** Until
    ``D-IMPL-332`` it read
    ``test_valid_time_opens_at_ingestion_when_the_source_cannot_say`` and
    asserted ``claim.valid_from == INGESTED_AT``, describing that as *"the
    stated reconciliation rule, not a silent default"*. The rule was stated
    and it was still a substitution: ``observed_at`` answers *when the fabric
    learned this* and ``valid_from`` answers *when this was true in the
    world*, and filling the second from the first turns *"we learned it at 2
    PM"* into *"it became true at 2 PM"* — a claim about the world that no
    source made.

    It also defeated ``D-IMPL-331`` from below. A λ_c row declaring
    ``decay_basis: valid-from`` reads this field; with ingestion time
    substituted into it, such a row reports a perfectly fresh figure for an
    observation whose real age nobody knows, and ``MissingDecayInstant`` — the
    refusal built for exactly that case — becomes unreachable through the
    fabric.
    """
    fabric.worker.ingest(envelope(observed_time=None))

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    claim = view.entities[0].claim

    assert claim.valid_from is None, (
        "the fabric manufactured a valid-time the source never supplied"
    )
    assert claim.observed_at == INGESTED_AT, (
        "the OTHER axis is unchanged and must stay so: the fabric always knows"
        " when it learned a claim, and `D-IMPL-332` does not touch that"
    )


def test_partial_identity_is_refused_rather_than_hashed() -> None:
    """A URI minted from partial identity would silently split an entity.

    A rule can legitimately match on one key and identify on several — an
    account is selected by its presence and identified by institution plus
    number. When the second identity key is absent, hashing what is there would
    mint a *different* URI for the same real entity, and the graph would hold
    two of it with no way to notice. Refusing is the only safe answer.
    """
    from ccf.assembly.worker import (
        EntityResolutionRule,
        EntityResolutionSpec,
        SpecDrivenEntityResolution,
    )

    strategy = SpecDrivenEntityResolution(
        spec=EntityResolutionSpec(
            semver="1.0.0",
            entity_rules=(
                EntityResolutionRule(
                    match_key="account_number",
                    entity_class="account",
                    identity_keys=("institution_id", "account_number"),
                ),
            )
        )
    )

    with pytest.raises(ValueError, match="partial identity"):
        strategy.resolve(envelope=envelope(payload={"account_number": "0001"}))


def test_an_unresolvable_payload_produces_no_graph_state(
    fabric: "FabricHandle",
) -> None:
    """No rule matched is a legitimate outcome, not an error or a guess."""
    result = fabric.worker.ingest(envelope(payload={"unrelated_key": "value"}))

    assert result.entities == ()
    assert result.relationships == ()
    assert fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).entities == ()


def test_every_claim_carries_the_bound_policy_bundle_version(
    fabric: "FabricHandle",
) -> None:
    """P is bound at assembly, never post-processed (INV-CH7-03)."""
    fabric.worker.ingest(envelope())

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)

    bound = {r.policy_bundle_version for r in view.entities}
    bound |= {r.policy_bundle_version for r in view.relationships}
    assert bound == {fabric.worker.policy_bundle_version}


def test_a_fabric_whose_policy_bundle_is_unregistered_refuses_to_boot(
    tmp_path: Path, banking_spec: Any
) -> None:
    """Fail at boot, not on the first write (D-IMPL-38, no silent defaults).

    A fabric that started without a policy binding would write unbound claims
    until someone noticed — and those claims are exactly the ones an audit
    would later be unable to explain.
    """
    from ccf.boot import boot

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, SPEC_KEY, banking_spec)

    with pytest.raises(ControlPlaneMissing):
        boot(
            backend="sqlite",
            connection={"database_path": tmp_path / "unbound.sqlite3"},
            registry=registry,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version="never-registered",
            tenant_ids=(TENANT,),
        )


def test_a_failed_boot_leaves_the_graph_bootable(
    tmp_path: Path, banking_spec: Any
) -> None:
    """A half-boot must not strand the graph as permanently written-to.

    Otherwise a configuration typo would make the database unusable until the
    process restarted — the single-writer check turning into a footgun instead
    of a guardrail.
    """
    from ccf.boot import boot

    database_path = tmp_path / "retry.sqlite3"
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, SPEC_KEY, banking_spec)

    with pytest.raises(ControlPlaneMissing):
        boot(
            backend="sqlite",
            connection={"database_path": database_path},
            registry=registry,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version="never-registered",
            tenant_ids=(TENANT,),
        )

    policy_version = register_at_composition(registry, POLICY_KEY, {"regime": "retry"})
    handle = boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=(TENANT,),
    )
    try:
        assert handle.worker.policy_bundle_version == policy_version
    finally:
        handle.close()


# ---------------------------------------------------------------------------
# 24.5-L-21 — L2 mints a relationship only when the envelope selects it, and
# never a self-loop. The cp-04 one-envelope shape (`24.4-D-35`) is reproduced
# here as a fixture; `examples/` is not touched.
# ---------------------------------------------------------------------------

#: cp-04's six family predicates, as its `ccf_config.yaml` declared them at
#: 2805803 — the twelve rules removed under `24.4-D-35` were these six, each
#: once as anchor→member and once as member→member.
FAMILY_PREDICATES = (
    "owns",
    "controls",
    "isDirectlyConsolidatedBy",
    "isUltimatelyConsolidatedBy",
    "hasGlobalUltimateParent",
    "hasDomesticUltimateParent",
)
LEI = "5493001KJTIIGC8Y1R12"
PARENT_LEI = "529900T8BM49AURSDO55"


def _two_class_spec(
    *,
    rules: tuple[RelationshipResolutionRule, ...],
    member_key: str = "lei",
    anchor_key: str = "lei",
) -> EntityResolutionSpec:
    """cp-04's resolution shape: two classes, ONE node under both.

    Both entity rules match and identify on the same payload key by default,
    so one envelope resolves one identity under ``family_anchor`` *and*
    ``family_member`` — two URIs (the class is the scheme), one node. Passing a
    different ``anchor_key`` makes the two rules resolve two distinct nodes.
    """
    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key=anchor_key,
                entity_class="family_anchor",
                identity_keys=(anchor_key,),
            ),
            EntityResolutionRule(
                match_key=member_key,
                entity_class="family_member",
                identity_keys=(member_key,),
            ),
        ),
        relationship_rules=rules,
    )


def _cp04_twelve_rules(
    *, predicate_key: str | None = None
) -> tuple[RelationshipResolutionRule, ...]:
    """The twelve rules cp-04 declared before `24.4-D-35` removed them."""
    rules: list[RelationshipResolutionRule] = []
    for predicate in FAMILY_PREDICATES:
        rules.append(
            RelationshipResolutionRule(
                relationship_type=predicate,
                subject_entity_class="family_anchor",
                object_entity_class="family_member",
                predicate_key=predicate_key,
            )
        )
        rules.append(
            RelationshipResolutionRule(
                relationship_type=predicate,
                subject_entity_class="family_member",
                object_entity_class="family_member",
                predicate_key=predicate_key,
            )
        )
    return tuple(rules)


def _parent_child_spec(
    *, rules: tuple[RelationshipResolutionRule, ...]
) -> EntityResolutionSpec:
    """Two entity rules of ONE class on two payload keys — an edge envelope.

    ``parent`` resolves ``parent_lei`` and ``child`` resolves ``lei``; both
    mint ``family_member`` URIs, so any edge between them is member-to-member.
    """
    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="parent_lei",
                entity_class="family_member",
                identity_keys=("parent_lei",),
            ),
            EntityResolutionRule(
                match_key="lei",
                entity_class="family_member",
                identity_keys=("lei",),
            ),
        ),
        relationship_rules=rules,
    )


def _self_loops(handle: "FabricHandle") -> list[Any]:
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    return [
        r for r in view.relationships if r.claim.subject_uri == r.claim.object_uri
    ]


@pytest.fixture
def spec_fabric() -> Iterator[Callable[[EntityResolutionSpec], "FabricHandle"]]:
    """A factory booting a memory-backed fabric over a given resolution spec.

    The session ``fabric`` fixture boots the banking spec; these tests need
    their own vocabulary, so they boot their own graph and close it on
    teardown.
    """
    from ccf.boot import boot

    handles: list[FabricHandle] = []

    def factory(spec: EntityResolutionSpec) -> "FabricHandle":
        registry = ControlPlaneRegistry()
        spec_version = register_at_composition(registry, SPEC_KEY, spec)
        policy_version = register_at_composition(registry, POLICY_KEY, {"regime": "l-21"})
        handle = boot(
            backend="memory",
            connection={},
            registry=registry,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version=policy_version,
            tenant_ids=(TENANT,),
        )
        handles.append(handle)
        return handle

    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()


def test_one_node_under_two_classes_and_twelve_co_occurrence_rules_mints_no_self_loop(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """The cp-04 one-envelope case: no rule mints a self-loop (24.5-L-21).

    MEASURED on the base tree (`phase-24.5-base` = 13bd250, worker untouched
    at 55c2fe6) with exactly this fixture, before Task 1 of plan 24.5-10
    landed::

        rules=12 entities=2 relationships=12 view_relationships=12 self_loops=6

    — the figure cp-04 recorded live under `24.4-D-35`. The six self-loops were
    the member→member rules: one envelope resolves one ``family_member``, and
    co-occurrence paired it with itself. After the fix the same fixture gives::

        rules=12 entities=2 relationships=6 view_relationships=6 self_loops=0

    The six that remain are the anchor→member rules, which join the node's
    two URIs (``family_anchor://h`` and ``family_member://h``). They are what
    co-occurrence by class means, and a rule with none of the selector fields
    keeps that meaning unchanged (D-10) — the self-loop skip is the ONE
    behavior every mode shares. The case that mints nothing at all is the
    next test: rules that select their predicate, on an envelope that selects
    none.
    """
    handle = spec_fabric(_two_class_spec(rules=_cp04_twelve_rules()))

    result = handle.worker.ingest(envelope(payload={"lei": LEI}))

    assert len(result.entities) == 2, "one node, two classes, two URIs"
    assert _self_loops(handle) == [], "a self-loop was minted from one envelope"
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert all(
        r.claim.subject_uri != r.claim.object_uri for r in view.relationships
    ), "self-loop present in the reader's view"
    # The D-10 control, pinned: the six anchor→member co-occurrence edges are
    # still minted, one per predicate, exactly as before the phase.
    assert len(result.relationships) == 6
    assert {r.claim.relationship_type for r in view.relationships} == set(
        FAMILY_PREDICATES
    )
    assert all(
        r.claim.subject_uri.startswith("family_anchor://")
        and r.claim.object_uri.startswith("family_member://")
        for r in view.relationships
    )


def test_the_cp_04_one_envelope_case_mints_nothing_the_envelope_did_not_select(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """Criterion 16's zero / zero: ingest mints only what the envelope selects.

    The same twelve rules, now each declaring ``predicate_key="predicate"``,
    and cp-04's actual node envelope — one node, no predicate — mint ZERO
    relationships and ZERO self-loops. When the envelope does select a
    predicate, exactly that predicate's rules are the only ones that fire;
    the member→member one is still a self-loop and still skipped.
    """
    handle = spec_fabric(
        _two_class_spec(rules=_cp04_twelve_rules(predicate_key="predicate"))
    )

    node = handle.worker.ingest(envelope(payload={"lei": LEI}))

    assert len(node.entities) == 2
    assert node.relationships == ()
    assert handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).relationships == ()

    selected = handle.worker.ingest(
        envelope(envelope_id="env-2", payload={"lei": LEI, "predicate": "owns"})
    )

    assert len(selected.relationships) == 1
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert [r.claim.relationship_type for r in view.relationships] == ["owns"]
    assert _self_loops(handle) == []


def test_a_predicate_selector_rule_mints_only_the_selected_predicate(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """Twelve predicate-keyed rules, one envelope, exactly one edge.

    Six predicates in two orderings: ``parent→child`` selected under the
    payload key ``predicate``, ``child→parent`` under ``inverse_predicate``.
    The envelope carries ``predicate: owns`` and no inverse, so eleven rules
    are silent for the one reason the mechanism has — the envelope did not
    select them: five by a value that names another predicate, six by a key
    the envelope does not carry. The comparison is against each rule's own
    ``relationship_type``, so a payload can never name a type no rule
    declares (T-24.5-26).
    """
    rules: list[RelationshipResolutionRule] = []
    for predicate in FAMILY_PREDICATES:
        rules.append(
            RelationshipResolutionRule(
                relationship_type=predicate,
                subject_entity_class="family_member",
                object_entity_class="family_member",
                predicate_key="predicate",
                subject_rule="parent_lei",
                object_rule="lei",
            )
        )
        rules.append(
            RelationshipResolutionRule(
                relationship_type=predicate,
                subject_entity_class="family_member",
                object_entity_class="family_member",
                predicate_key="inverse_predicate",
                subject_rule="lei",
                object_rule="parent_lei",
            )
        )
    assert len(rules) == 12
    handle = spec_fabric(_parent_child_spec(rules=tuple(rules)))

    result = handle.worker.ingest(
        envelope(payload={"lei": LEI, "parent_lei": PARENT_LEI, "predicate": "owns"})
    )

    assert len(result.entities) == 2
    assert len(result.relationships) == 1
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert len(view.relationships) == 1
    edge = view.relationships[0].claim
    assert edge.relationship_type == "owns"
    by_key = {r.node_key: r for r in result.entities}
    parent_uri, child_uri = edge.subject_uri, edge.object_uri
    assert parent_uri in by_key and child_uri in by_key
    strategy = SpecDrivenEntityResolution(spec=_parent_child_spec(rules=()))
    resolved = {
        item.resolved_by: item.entity_uri
        for item in strategy.resolve(
            envelope=envelope(payload={"lei": LEI, "parent_lei": PARENT_LEI})
        )
    }
    assert (parent_uri, child_uri) == (resolved["parent_lei"], resolved["lei"]), (
        "the edge runs parent→child, chosen by the entity rule that resolved each"
    )

    # A payload value naming a type no rule declares selects nothing.
    stray = handle.worker.ingest(
        envelope(
            envelope_id="env-2",
            payload={"lei": LEI, "parent_lei": PARENT_LEI, "predicate": "ownedBy"},
        )
    )
    assert stray.relationships == ()


def test_a_member_to_member_edge_is_expressible_from_one_envelope(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """Criterion 16's third clause: two entities of one class, one typed edge.

    Under co-occurrence by class this was impossible — one envelope resolved
    at most one ``family_member`` (`24.4-D-35`). With endpoint selectors the
    rule picks the parent by the rule that resolved it and the child likewise,
    and the edge joins two distinct URIs of the same class.
    """
    handle = spec_fabric(
        _parent_child_spec(
            rules=(
                RelationshipResolutionRule(
                    relationship_type="owns",
                    subject_entity_class="family_member",
                    object_entity_class="family_member",
                    subject_rule="parent_lei",
                    object_rule="lei",
                ),
            )
        )
    )

    result = handle.worker.ingest(
        envelope(payload={"lei": LEI, "parent_lei": PARENT_LEI})
    )

    assert len(result.entities) == 2
    assert len(result.relationships) == 1
    edge = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).relationships[0].claim
    assert edge.relationship_type == "owns"
    assert edge.subject_uri != edge.object_uri
    assert edge.subject_uri.startswith("family_member://")
    assert edge.object_uri.startswith("family_member://")
    assert _self_loops(handle) == []


def test_an_endpoint_no_rule_claims_is_not_selectable(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A custom strategy that leaves ``resolved_by`` at the sentinel.

    Its entities are reachable by class, so a co-occurrence rule still mints
    between them; a rule selecting endpoints by rule finds nothing to choose,
    because an endpoint no rule claims cannot be chosen by rule.
    """
    import ccf.boot

    class _Unclaimed:
        """Wraps the reference strategy and drops the resolving rule."""

        def __init__(self, *, spec: EntityResolutionSpec) -> None:
            self.spec = spec
            self._inner = SpecDrivenEntityResolution(spec=spec)

        def resolve(self, *, envelope: SignalEnvelope) -> tuple[ResolvedEntity, ...]:
            return tuple(
                ResolvedEntity(
                    entity_uri=item.entity_uri,
                    entity_class=item.entity_class,
                    attributes=item.attributes,
                )
                for item in self._inner.resolve(envelope=envelope)
            )

    monkeypatch.setattr(ccf.boot, "SpecDrivenEntityResolution", _Unclaimed)
    by_rule = RelationshipResolutionRule(
        relationship_type="owns",
        subject_entity_class="family_member",
        object_entity_class="family_member",
        subject_rule="parent_lei",
        object_rule="lei",
    )
    by_class = RelationshipResolutionRule(
        relationship_type="controls",
        subject_entity_class="family_member",
        object_entity_class="family_member",
    )
    handle = spec_fabric(_parent_child_spec(rules=(by_rule, by_class)))

    result = handle.worker.ingest(
        envelope(payload={"lei": LEI, "parent_lei": PARENT_LEI})
    )

    assert len(result.entities) == 2
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    minted = sorted(r.claim.relationship_type for r in view.relationships)
    assert "owns" not in minted, "a selector rule chose an entity no rule claims"
    # By class, both orderings of the two distinct members mint (no self-loop).
    assert minted == ["controls", "controls"]
    assert _self_loops(handle) == []
    # The sentinel is what the strategy left in place.
    assert ResolvedEntity(
        entity_uri="x://1", entity_class="x", attributes={}
    ).resolved_by == NO_RESOLVING_RULE


def test_co_occurrence_rules_still_mint_between_distinct_entities(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """The pre-phase control on the two-class spec (D-10).

    A rule with none of the selector fields, over two DISTINCT nodes of two
    classes, mints exactly the one edge co-occurrence always minted — and the
    banking fixture's own test above (``obligor_of``) is untouched.
    """
    handle = spec_fabric(
        _two_class_spec(
            anchor_key="anchor_lei",
            rules=(
                RelationshipResolutionRule(
                    relationship_type="owns",
                    subject_entity_class="family_anchor",
                    object_entity_class="family_member",
                ),
            ),
        )
    )

    result = handle.worker.ingest(
        envelope(payload={"anchor_lei": PARENT_LEI, "lei": LEI})
    )

    assert len(result.entities) == 2
    assert len(result.relationships) == 1
    edge = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).relationships[0].claim
    assert edge.relationship_type == "owns"
    assert edge.subject_uri.startswith("family_anchor://")
    assert edge.object_uri.startswith("family_member://")
    assert edge.subject_uri != edge.object_uri


def test_a_rule_with_no_selector_fields_is_the_pre_phase_rule() -> None:
    """Additive over breaking: the three required fields still construct alone,
    the three selectors default to ``None``, and a half endpoint selector is
    refused rather than read as class-on-one-side."""
    rule = RelationshipResolutionRule(
        relationship_type="owns",
        subject_entity_class="a",
        object_entity_class="b",
    )
    assert (rule.predicate_key, rule.subject_rule, rule.object_rule) == (
        None,
        None,
        None,
    )
    with pytest.raises(ValidationError, match="both of their fields or neither"):
        RelationshipResolutionRule(
            relationship_type="owns",
            subject_entity_class="a",
            object_entity_class="b",
            subject_rule="a_key",
        )
    with pytest.raises(ValidationError, match="24.5-L-21"):
        RelationshipResolutionRule(
            relationship_type="owns",
            subject_entity_class="a",
            object_entity_class="b",
            object_rule="b_key",
        )


# --- CP04C-F-01: a position is not an identity (`D-IMPL-316`) ----------------


def _positional_spec(
    *, remap: bool, rules: tuple[RelationshipResolutionRule, ...]
) -> EntityResolutionSpec:
    """Two endpoint rules reading two payload fields, one declared identity.

    With ``remap`` the two rules read ``parent_lei`` and ``lei`` into the SAME
    declared identity key, which is the repair. Without it each rule identifies
    the entity by the payload field's own name, which is the shipped defect and
    is kept here as this module's negative control.
    """
    def rule(match: str) -> EntityResolutionRule:
        if remap:
            return EntityResolutionRule(
                match_key=match,
                entity_class="family_member",
                identity_keys=("entity_lei",),
                identity_sources={"entity_lei": match},
            )
        return EntityResolutionRule(
            match_key=match, entity_class="family_member", identity_keys=(match,)
        )

    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(rule("parent_lei"), rule("lei")),
        relationship_rules=rules,
    )


_OWNS = RelationshipResolutionRule(
    relationship_type="owns",
    subject_entity_class="family_member",
    object_entity_class="family_member",
    subject_rule="parent_lei",
    object_rule="lei",
)
_CONTROLS = RelationshipResolutionRule(
    relationship_type="controls",
    subject_entity_class="family_member",
    object_entity_class="family_member",
    subject_rule="lei",
    object_rule="parent_lei",
)


def test_one_lei_in_both_endpoint_positions_is_one_entity(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """`CP04C-F-01` case 1. The same value, read from two payload fields.

    Before the repair the two fields' NAMES were inside the identity hash, so
    one company observed once as a parent and once as a child became two
    entities — and nothing reported it, because both URIs were well-formed.
    """
    handle = spec_fabric(_positional_spec(remap=True, rules=(_OWNS,)))

    handle.worker.ingest(envelope(payload={"parent_lei": LEI, "lei": PARENT_LEI}))
    handle.worker.ingest(
        # The SAME company, now in the other position.
        envelope(envelope_id="e2", payload={"parent_lei": PARENT_LEI, "lei": LEI})
    )

    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert len(view.entities) == 2, "one company reached two URIs by position"


def test_a_same_class_edge_still_mints_under_a_remapped_identity(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """`CP04C-F-01` case 2. The repair must not cost the feature it repairs.

    Sharing one declared identity key must not collapse the endpoints onto one
    URI — which would make every edge a self-loop and mint nothing at all.
    """
    handle = spec_fabric(_positional_spec(remap=True, rules=(_OWNS,)))

    result = handle.worker.ingest(
        envelope(payload={"parent_lei": PARENT_LEI, "lei": LEI})
    )

    assert len(result.entities) == 2
    assert len(result.relationships) == 1
    edge = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).relationships[0].claim
    assert edge.subject_uri != edge.object_uri
    assert _self_loops(handle) == []


def test_a_mutual_pair_is_two_entities_and_two_edges(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """`CP04C-F-01` case 3 — the case that makes this a real defect.

    Mutual ownership is ordinary: the cp-04 family fixture carries 22 such
    pairs. Under positional identity this produced FOUR entities for two
    companies, so a family of 49 nodes could not be assembled at all.
    """
    handle = spec_fabric(_positional_spec(remap=True, rules=(_OWNS,)))

    # TWO envelopes, because that is how a mutual pair actually arrives: one
    # edge per source assertion, each naming its own parent and child. A single
    # envelope minting both directions would never put one company into both
    # positions, which is the whole condition under test.
    handle.worker.ingest(envelope(payload={"parent_lei": PARENT_LEI, "lei": LEI}))
    handle.worker.ingest(
        envelope(envelope_id="e2", payload={"parent_lei": LEI, "lei": PARENT_LEI})
    )

    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert len(view.entities) == 2, "two companies became more than two entities"
    assert len(view.relationships) == 2, "the mutual pair lost one of its edges"


def test_positional_identity_reproduces_the_duplicate_entity_defect(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """`CP04C-F-01` case 4 — the negative control, and it must stay red-able.

    Identical envelopes, identical rules, with the ONE difference that each
    rule identifies the entity by the payload field's own name. Two companies
    become four entities. Without this control the three assertions above would
    pass just as happily against a fabric that never had the defect, and would
    prove nothing about the repair.
    """
    handle = spec_fabric(_positional_spec(remap=False, rules=(_OWNS,)))

    handle.worker.ingest(envelope(payload={"parent_lei": PARENT_LEI, "lei": LEI}))
    handle.worker.ingest(
        envelope(envelope_id="e2", payload={"parent_lei": LEI, "lei": PARENT_LEI})
    )

    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert len(view.entities) == 4, (
        "the defect did not reproduce, so the repair's proof is measuring"
        " something other than what it claims"
    )


def test_a_source_field_cannot_supply_an_undeclared_identity_key() -> None:
    """A remap naming a key the rule does not identify by is refused.

    Ignored, it would silently fall back to the payload field of the same name
    as the declared key, mint a different URI, and report nothing — the exact
    silent wrong-identity failure this field exists to remove.
    """
    with pytest.raises(ValidationError, match="does not declare as identity keys"):
        EntityResolutionRule(
            match_key="parent_lei",
            entity_class="family_member",
            identity_keys=("entity_lei",),
            identity_sources={"typo_lei": "parent_lei"},
        )


# --- SEC-007 / D-IMPL-357 B1 / B2: identity admissibility at the mint site --


def _lei_rule() -> EntityResolutionSpec:
    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(match_key="lei", entity_class="company", identity_keys=("lei",)),
        ),
    )


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (None, "null"),
        ("", "empty"),
        ("   ", "empty"),
        (True, "bool"),
        (1.5, "float"),
        ({"lei": "x"}, "non-scalar"),
        (["x"], "non-scalar"),
        (b"x", "non-scalar"),
    ],
)
def test_an_inadmissible_identity_value_is_refused_by_name(value: object, reason: str) -> None:
    """D-IMPL-357 B1 (SEC-007): presence is not admissibility."""
    strategy = SpecDrivenEntityResolution(spec=_lei_rule())
    with pytest.raises(IdentityRefused) as caught:
        strategy.resolve(envelope=envelope(payload={"lei": value}))
    assert caught.value.reason == reason
    assert caught.value.key == "lei" and caught.value.entity_class == "company"


def test_int_and_decimal_identities_keep_their_positional_string_uris() -> None:
    """D-IMPL-357 B2 / D-IMPL-316: the coercion is what bare str() did, so no
    existing URI moves."""
    strategy = SpecDrivenEntityResolution(spec=_lei_rule())
    for value, text in ((7, "7"), (Decimal("1.50"), "1.50")):
        (resolved,) = strategy.resolve(envelope=envelope(payload={"lei": value}))
        assert resolved.entity_uri == f"company://{content_hash({'lei': text})}"


def test_two_null_identity_envelopes_mint_nothing_and_no_edge(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """THE NEGATIVE CONTROL (SEC-007). Before B1, both envelopes minted ONE
    phantom node (`company://<hash of {"lei": "None"}>`) and the owns rule
    minted a real edge onto it. Re-enable bare str() and this reddens on both
    counts — the second assertion is the one that proves the false edge."""
    handle = spec_fabric(_positional_spec(remap=True, rules=(_OWNS,)))
    for envelope_id, payload in (
        ("e1", {"parent_lei": None, "lei": LEI}),
        ("e2", {"parent_lei": None, "lei": PARENT_LEI}),
    ):
        with pytest.raises(IdentityRefused):
            handle.worker.ingest(envelope(envelope_id=envelope_id, payload=payload))
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert len(view.entities) == 0
    assert len(view.relationships) == 0
