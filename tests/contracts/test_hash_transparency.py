"""The hash-transparent mark and the omission rule (``D-IMPL-243``).

Whitepaper §7.10 (a decision reconstructible years later against the exact
identities it was made with); CLAUDE.md §7.4 (replay resolves exact versions,
never "latest"). Phase 24.5's close review (CR-01) measured that every
sentinel-defaulted field the phase added moved the content hash of every model
carrying it — a replay record's per-step ``parameter_hash``, its
``graph_query_sequence`` pins, every Control Plane version — because
``ccf.contracts.canonical::_normalize`` renders every field. ``D-IMPL-243``
rules that such a field is a generation change unless its owner marks it
``ccf_hash_transparent``, meaning its sentinel *is* the old contract; a marked
field is omitted at its sentinel and rendered otherwise. Dave's rule, verbatim:
"silence equals yesterday". Amendment 1 gives the key its three states —
``True`` omits at the sentinel, ``False`` is a declared generation boundary
that ``generation_mismatch`` names when absent, and no key is the pre-243
``D-IMPL-89`` lineage: rendered, never named.

Every model here is a scratch model owned by this module: the rule is about
the canonicalizer, and proving it on a real SDK contract would prove the mark
on that contract rather than the mechanism. The real marks are proven against
the ``13bd250`` tree in ``tests/replay/`` (the golden fixture) and were
measured per model in ``24.5-FIX-01-SUMMARY.md``.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.replay.record import ChildResolution, ContentGenerationPath
from ccf.skills.catalog import (
    NO_PRODUCT_CLASS,
    LocalCallableBinding,
    SkillArgumentSchema,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.contracts.canonical import (
    HASH_TRANSPARENT_KEY,
    CanonicalizationError,
    canonical_bytes,
    content_hash,
    generation_mismatch,
    hash_transparent_fields,
)
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN, StoreSnapshotPin


class _Yesterday(CCFContract):
    """The contract as it was before any field below existed."""

    a: int


class _Today(CCFContract):
    """The same contract after three transparent fields were added.

    One sentinel of each declared form the SDK uses: a plain ``default``, a
    ``default_factory``, and a model-valued default that compares by value.
    """

    a: int
    t: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    f: dict[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    pin: StoreSnapshotPin = Field(
        default=NO_STORE_SNAPSHOT_PIN,
        json_schema_extra={HASH_TRANSPARENT_KEY: True},
    )


class _TodayUnmarked(CCFContract):
    """The same addition with NO key — the pre-243 lineage (amendment 1).

    Rendered into every hash, so it IS a generation change for the hashes
    (the rule is not "defaults never count"); but never *named* by
    ``generation_mismatch``, because an absent key declares nothing and
    ``D-IMPL-89`` promises a record written before the field existed still
    resolves and replays.
    """

    a: int
    n: int = 0


class _TodayBoundary(CCFContract):
    """The same addition marked ``False`` — a DECLARED generation boundary.

    Rendered exactly as ``_TodayUnmarked.n`` is; the difference is entirely
    what ``generation_mismatch`` says about a stored object that lacks it.
    """

    a: int
    b: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: False})


class _NoSentinel(CCFContract):
    """A mark on a field with no default: nothing to be silent at."""

    a: int
    t: str = Field(json_schema_extra={HASH_TRANSPARENT_KEY: True})


class _Outer(CCFContract):
    inner: _TodayBoundary
    optional: _TodayBoundary | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    lineage: _TodayUnmarked | None = None
    silent: _Today | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


# --- the mark ---------------------------------------------------------------


def test_the_mark_is_read_from_the_field_declaration() -> None:
    assert hash_transparent_fields(_Today) == frozenset({"t", "f", "pin"})
    assert hash_transparent_fields(_Yesterday) == frozenset()
    assert hash_transparent_fields(_TodayUnmarked) == frozenset()


def test_only_the_literal_true_is_a_mark() -> None:
    class _Loose(CCFContract):
        a: int
        yes: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: 1})
        text: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: "true"}
        )

    assert hash_transparent_fields(_Loose) == frozenset()
    assert canonical_bytes(_Loose(a=1)) == b'{"a":1,"text":0,"yes":0}'


def test_a_mark_without_a_default_is_refused_not_ignored() -> None:
    with pytest.raises(CanonicalizationError, match="_NoSentinel.t") as refused:
        content_hash(_NoSentinel(a=1, t="q"))
    assert "D-IMPL-243" in str(refused.value)


# --- the omission rule: silence equals yesterday ------------------------------


def test_a_boundary_mark_renders_exactly_as_no_mark_does() -> None:
    """``False`` changes what is *named*, never what is *rendered*."""
    assert canonical_bytes(_TodayBoundary(a=1)) == b'{"a":1,"b":0}'
    assert hash_transparent_fields(_TodayBoundary) == frozenset()
    assert content_hash(_TodayBoundary(a=1)) != content_hash(_Yesterday(a=1))


def test_a_marked_field_at_its_sentinel_is_omitted() -> None:
    assert canonical_bytes(_Today(a=1)) == canonical_bytes(_Yesterday(a=1))
    assert content_hash(_Today(a=1)) == content_hash(_Yesterday(a=1))
    assert canonical_bytes(_Today(a=1)) == b'{"a":1}'


def test_the_sentinel_is_compared_by_value_not_identity() -> None:
    same_pin = StoreSnapshotPin(substrate="none", pin="no-store-snapshot-pin")
    assert same_pin is not NO_STORE_SNAPSHOT_PIN
    assert content_hash(_Today(a=1, pin=same_pin)) == content_hash(
        _Yesterday(a=1)
    )
    assert content_hash(_Today(a=1, f={})) == content_hash(_Yesterday(a=1))


@pytest.mark.parametrize(
    ("field", "value", "rendered"),
    [
        ("t", "x", b'{"a":1,"t":"x"}'),
        ("f", {"k": "v"}, b'{"a":1,"f":{"k":"v"}}'),
        (
            "pin",
            StoreSnapshotPin(substrate="fluree", pin="7"),
            b'{"a":1,"pin":{"pin":"7","substrate":"fluree"}}',
        ),
    ],
)
def test_a_non_sentinel_value_is_rendered_and_moves_the_hash(
    field: str, value: object, rendered: bytes
) -> None:
    today = _Today(a=1, **{field: value})
    assert canonical_bytes(today) == rendered
    assert content_hash(today) != content_hash(_Yesterday(a=1))


def test_an_unmarked_default_still_renders() -> None:
    """The rule is not "defaults never count"."""
    assert canonical_bytes(_TodayUnmarked(a=1)) == b'{"a":1,"n":0}'
    assert content_hash(_TodayUnmarked(a=1)) != content_hash(_Yesterday(a=1))


def test_a_transparent_model_valued_field_is_walked_when_present() -> None:
    outer = _Outer(inner=_TodayBoundary(a=1), silent=_Today(a=2, t="deep"))
    assert canonical_bytes(outer) == (
        b'{"inner":{"a":1,"b":0},"lineage":null,"optional":null,'
        b'"silent":{"a":2,"t":"deep"}}'
    )


# --- the converse: generation_mismatch, in DECLARED scope (amendment 1) ------


def test_a_stored_object_lacking_only_transparent_fields_is_the_same_generation() -> None:
    assert generation_mismatch(_Today, {"a": 1}) == ()


def test_a_stored_object_lacking_a_boundary_field_is_named() -> None:
    """``False`` → generation boundary, refuse by name."""
    assert generation_mismatch(_TodayBoundary, {"a": 1}) == ("b",)


def test_a_stored_object_lacking_an_unmarked_field_is_never_named() -> None:
    """No key → the D-IMPL-89 lineage: render, never refuse.

    This is the control amendment 1 was written for. Under the first
    specification this object was named ``("n",)``, and on a real
    pre-extension record the same rule named fifteen pre-243 fields.
    """
    assert generation_mismatch(_TodayUnmarked, {"a": 1}) == ()


def test_only_the_literal_false_is_a_boundary_mark() -> None:
    class _Loose(CCFContract):
        a: int
        zero: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: 0})
        none: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: None}
        )
        text: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: "false"}
        )

    assert generation_mismatch(_Loose, {"a": 1}) == ()


def test_a_stored_object_carrying_every_field_crosses_no_boundary() -> None:
    assert generation_mismatch(_TodayBoundary, {"a": 1, "b": 0}) == ()
    assert generation_mismatch(_TodayUnmarked, {"a": 1, "n": 0}) == ()
    assert generation_mismatch(_Today, {"a": 1, "t": "x"}) == ()


def test_nested_models_are_walked_and_reported_dotted() -> None:
    stored = {
        "inner": {"a": 1},
        "optional": {"a": 2},
        "lineage": {"a": 3},
        "silent": {"a": 4},
    }
    assert generation_mismatch(_Outer, stored) == ("inner.b", "optional.b")


def test_an_absent_nested_boundary_field_is_reported_once_as_the_outer_name() -> None:
    assert generation_mismatch(_Outer, {"inner": {"a": 1, "b": 0}}) == (
        "optional",
    )


def test_an_absent_nested_lineage_field_is_not_reported() -> None:
    stored = {"inner": {"a": 1, "b": 0}, "optional": {"a": 2, "b": 0}}
    assert generation_mismatch(_Outer, stored) == ()


def test_a_null_nested_value_is_a_leaf_not_a_walk() -> None:
    stored = {"inner": {"a": 1, "b": 0}, "optional": None, "lineage": None}
    assert generation_mismatch(_Outer, stored) == ()


# --- the marks in the tree: the ticked table, as a roster --------------------

#: Every hash-transparent field the SDK declares: ``D-IMPL-243``'s ticked
#: table (rows 1–5 and 7–10), amendment 2's seven ticks (the descendants twin
#: of row 1, ``HalfLifeEntry.half_life_seconds`` at ``None``, rows 6, 11 and
#: 12 superseded from "no mark" to ``True`` — inert until those models are
#: hashed — and ``ServeObligations``' two fields at empty), plus the TWO
#: inherited occurrences: the artifact forms of the two traversal parameter
#: classes subclass them and carry the same declarations, so the mark rides
#: the inheritance — which is the CR-01 consequence for a registered table's
#: content-hash version. A roster, never a count: a right count with a wrong
#: member audits clean forever.
_MARKED_IN_THE_TREE = frozenset(
    {
        "ccf.operators.params.TraversalNeighborhoodParameters.admitted_entity_classes",
        "ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact.admitted_entity_classes",
        "ccf.operators.params.TraversalDescendantsParameters.admitted_entity_classes",
        "ccf.controlplane.artifacts.TraversalDescendantsParametersArtifact.admitted_entity_classes",
        "ccf.graph.protocols.TraversalSpec.admitted_entity_classes",
        "ccf.graph.protocols.TraversalSpec.direction",
        # `ccf.products.contract.ProductLineage.store_snapshot_pin` stood here
        # until `D-IMPL-309` REMOVED the field: a substrate's transaction-time
        # head is execution provenance, and because these canonical bytes are
        # at once the address, the stored form and the wire form, a head
        # excluded from them would be erased rather than merely unaddressed.
        # It is recorded on the snapshot below, which keeps its mark.
        # `D-IMPL-336` — the composite/swarm surface. Three marks, each at a
        # sentinel that is the state of every artifact registered before the
        # field existed, so no catalog entry, product class or replay record
        # written earlier moves its content address. Measured, not asserted:
        # `test_d_impl_336_marks_are_silent_at_their_sentinels` below.
        "ccf.skills.catalog.SkillCatalogEntry.produces",
        "ccf.products.contract.RegisteredProductClass.requires",
        # A REQUIRED requirement can never carry a treatment (the contract
        # refuses one), so the key spares every required slot a permanent
        # `null` restating what `required` already says.
        "ccf.products.contract.ChildRequirement.absence_treatment",
        "ccf.replay.record.ContentGenerationPath.child_resolutions",
        "ccf.replay.record.ContextFabricSnapshot.store_snapshot_pin",
        # 24.6-03: the Authority layer's value in dimension 2
        # (``D-IMPL-253`` Q1/Q6, ``D-IMPL-254``). The sentinel is the
        # positive "no resolution was recorded" claim, so every record
        # written before the layer existed keeps its content address —
        # measured by `tests/replay/test_golden_13bd250.py`, not asserted.
        "ccf.replay.record.PolicyBindingsSnapshot.request_resolution",
        "ccf.projection.engine.ExecutionResult.store_snapshot_pin",
        "ccf.projection.engine.ExecutionResult.empty_results",
        "ccf.assembly.worker.ResolvedEntity.resolved_by",
        # `D-IMPL-332`. `valid_from` became nullable when the fabric stopped
        # substituting ingestion time for a valid-time no source supplied.
        # Ticked `True` rather than `False`: no stored claim LACKS the field —
        # it was required before this ruling, so every one of them carries a
        # real instant and renders it. What the sentinel buys is that a claim
        # whose source could not say renders WITHOUT it, which is the honest
        # shape of "we do not know" and moves no existing address.
        # Named on the BASE and on both concrete claim classes: the walk
        # reports the field once per class that declares or inherits it, and a
        # roster naming only the leaves would go red the moment somebody read
        # the base directly.
        "ccf.contracts.claims._TemporalClaim.valid_from",
        "ccf.contracts.claims.EntityClaim.valid_from",
        "ccf.contracts.claims.RelationshipClaim.valid_from",
        # `D-IMPL-331`. `None` is the honest value where a source could not say
        # when it observed the thing, and it is also the shape every
        # observation had before the field existed — so the sentinel means the
        # old contract twice over.
        "ccf.halflife.decay.Observation.valid_from",
        # `D-IMPL-333`. `None` is both the honest value where a deployment
        # declared no series and the shape every observation had before.
        "ccf.halflife.decay.Observation.series",
        "ccf.controlplane.artifacts.HalfLifeEntry.decay",
        # `D-IMPL-331`. Ticked for the same reason `decay` above is: a λ_c row
        # written before the field existed means "decay against the instant the
        # fabric learned this", which is exactly what it did, so silence equals
        # yesterday and every stored table version holds its identity. A
        # deployment declaring `valid-from` has said something new and it is
        # inside the hash.
        "ccf.controlplane.artifacts.HalfLifeEntry.decay_basis",
        # `D-IMPL-333`. A table written before these existed aggregated by
        # series-mean and named no series key, which is exactly what the
        # sentinels say — so silence equals yesterday and every stored λ_c
        # version holds its identity.
        "ccf.controlplane.artifacts.HalfLifeEntry.freshness_over",
        "ccf.controlplane.artifacts.HalfLifeEntry.series_key_attribute",
        "ccf.controlplane.artifacts.HalfLifeEntry.half_life_seconds",
        "ccf.controlplane.artifacts.ProductClassDeclaration.serve_obligations",
        "ccf.products.contract.RegisteredProductClass.serve_obligations",
        # 24.6-04: renamed under `D-IMPL-253` Q9 and `D-IMPL-251` C1=A —
        # same field, same sentinel, same hash posture, a name that says
        # default rather than ceiling.
        "ccf.products.contract.ServeObligations.default_debt_tolerance",
        "ccf.products.contract.ServeObligations.lineage_inputs_at",
        # `24.10-02` / `R-11` (`D-IMPL-282` option 1a): the class's own
        # declared runtime invariant, by governed identity. All three are
        # `True` and the reason is measured rather than assumed by
        # `test_each_marked_model_at_its_sentinel_hashes_as_the_base_tree_did`
        # over `ProductClassDeclaration`: a class declaring no gate must
        # canonicalize byte-identically to the same class before the member
        # existed, because pin identity IS content identity and every
        # committed declaration in this tree — and every adopter's — would
        # otherwise move. The two inner members are `True` on the
        # `ccf.products.provenance` precedent as well: a brand-new model has
        # no earlier generation to be a boundary against, and the sentinel
        # form has nothing to say under either key.
        "ccf.controlplane.artifacts.ProductClassDeclaration.declared_product_gate",
        "ccf.products.contract.DeclaredProductGate.gate_id",
        "ccf.products.contract.DeclaredProductGate.gate_version",
        # 24.6-05: the search behind an empty answer (`24.6-L-06`,
        # `D-IMPL-242` amendment 1). `None` is "no operator returned empty",
        # which is what every product assembled before the field existed was
        # saying — so a pre-phase product's `canonical_bytes` must be
        # byte-identical, and `test_a_product_with_no_finding_hashes_as_it_did`
        # below measures exactly that rather than asserting it.
        "ccf.products.contract.ContextProductContract.computed_empty",
        "ccf.products.request.ProductRequestContract.unsupported_arguments",
        # 24.6-01: the fifth declaration key (``24.6-L-07``, ``D-IMPL-253``
        # Q2). The empty mapping is "this class declares no default", which is
        # what every declaration written before the field said — so the
        # `ProductRequestContract` digest in `_BASE_TREE_DIGESTS` below must
        # still reproduce, and it does.
        "ccf.products.request.ProductRequestContract.defaults",
        # 24.6-03: the sixth declaration key (``24.6-L-07``, ``D-IMPL-253``
        # Q21) and the request's own override list (Q7). Both are silent at
        # their sentinels for the same compatibility reason as ``defaults``:
        # declaring no capability binding, and asking for no exception, are
        # what every contract and every request written before these fields
        # said — so the ``ProductRequestContract`` digest below still
        # reproduces, and a committed request's content address does not move.
        "ccf.products.request.ProductRequestContract.capability_bindings",
        "ccf.products.request.ProductRequest.policy_overrides",
        # 24.6-03: what a principal may override (``D-IMPL-253`` Q7). The
        # empty set is "this principal may override nothing", which is what
        # every entitlement policy already in force says — and a policy whose
        # content address moved would be a policy whose pin moved.
        "ccf.products.entitlement.ProductEntitlementGrant.overridable_policies",
        "ccf.assembly.worker.RelationshipResolutionRule.predicate_key",
        "ccf.assembly.worker.RelationshipResolutionRule.subject_rule",
        "ccf.assembly.worker.RelationshipResolutionRule.object_rule",
        # 24.6-01: the Authority layer's value (``24.6-L-07``, ``D-IMPL-253``
        # Q1). Three optional members on three brand-new models, so there is
        # no earlier generation to be a boundary against — ``True`` is the
        # only coherent declaration: a bound with no policy behind it, a
        # parameter nothing bounded, and an override attempt that found no
        # grant each render without the key they have nothing to say under.
        "ccf.products.provenance.ParameterBound.policy_id",
        # 24.6 correction pass (``D-IMPL-260`` P-G): the constraint's declared
        # reason rides on the bound it establishes. ``None`` for a technical
        # bound, which declares no reason; transparent so no bound written
        # before the member existed moves.
        "ccf.products.provenance.ParameterBound.reason",
        # 24.6 correction pass (``D-IMPL-260`` P-I, criterion 10): the override
        # attempts a REFUSED request made ride on the refusal, as they ride on
        # `EffectiveRequest.overrides` when the request resolves. Empty when
        # nothing was attempted; transparent so no refusal already written
        # moves.
        "ccf.products.constraints.ConstraintRefusal.overrides",
        "ccf.products.constraints.PolicyResolutionConflict.overrides",
        "ccf.products.request.ProductRequestViolation.overrides",
        "ccf.products.provenance.EffectiveParameter.bound",
        "ccf.products.provenance.OverrideRecord.grant_source",
        # 24.6-01: the policy-constraint artifact class (``24.6-L-07``,
        # ``D-IMPL-253`` Q3). Applicability's four axes are ``None`` = *any*,
        # so an applicability narrowing nothing renders as ``{}``; the
        # constraint's three optional members are its own sentinels — not
        # overridable, no stated end, no claimed ordering.
        "ccf.controlplane.artifacts.ConstraintApplicability.product_class",
        "ccf.controlplane.artifacts.ConstraintApplicability.tenant",
        "ccf.controlplane.artifacts.ConstraintApplicability.perspective_role",
        "ccf.controlplane.artifacts.ConstraintApplicability.intent",
        "ccf.controlplane.artifacts.PolicyConstraint.overridable",
        "ccf.controlplane.artifacts.PolicyConstraint.effective_until",
        "ccf.controlplane.artifacts.PolicyConstraint.priority",
        # The ninth reserved section. ``True`` and not ``False`` is
        # load-bearing rather than stylistic: a rendered
        # ``policy_constraints: null`` would move the content address of every
        # `DeploymentConfig` already written, and pin identity IS content
        # identity (`src/ccf/deployment/pins.py::ArtifactPin`). Measured, not
        # assumed: `test_a_config_naming_no_constraints_hashes_as_it_did`
        # below hashes a config at the sentinel against the same document
        # without the key.
        "ccf.controlplane.artifacts.DeploymentConfig.policy_constraints",
        # `24.10-01` / `R-12`: the tenth reserved section name (the ninth
        # `_RESERVED_SECTIONS` entry). ``True`` for exactly the reason above
        # and measured the same way, by
        # `test_a_config_naming_no_replay_binding_hashes_as_it_did`: every
        # `ccf_config.yaml` already written declares no replay binding, and a
        # rendered ``replay: null`` would move all of their pins.
        "ccf.controlplane.artifacts.DeploymentConfig.replay",
        # 24.6-07: the refusal shell's six governance members (``24.6-L-08``,
        # ``D-IMPL-253`` Q13/Q14, ``D-IMPL-256`` (1)). Each sentinel is what
        # every shell minted before this row was already saying — nothing
        # version-bearing governed it, no record was minted, no search is
        # shown, no resolution was recorded, no disclosure was applied, and it
        # was not a delivery-boundary denial — so a 24.5-shaped envelope must
        # render byte-identically. Measured by
        # `test_a_refusal_shell_at_its_sentinels_hashes_as_it_did` below, not
        # asserted.
        "ccf.products.refusal.RefusalEnvelope.policy_bindings",
        "ccf.products.refusal.RefusalEnvelope.replay_reference",
        "ccf.products.refusal.RefusalEnvelope.evidence",
        "ccf.products.refusal.RefusalEnvelope.provenance",
        "ccf.products.refusal.RefusalEnvelope.disclosure",
        "ccf.products.refusal.RefusalEnvelope.resource",
        # 24.6-07: the two optional members of the permitted-evidence bundle
        # (``24.6-L-08``). A brand-new model — the ``ccf.products.provenance``
        # precedent above — so there is no earlier generation for either to be
        # a boundary against, and ``True`` is the only coherent declaration: a
        # refusal reached with no assessment, and one reached with no empty
        # operator, each render without the key they have nothing to say under.
        "ccf.products.refusal.RefusalEvidence.debt",
        "ccf.products.refusal.RefusalEvidence.computed_empty",
        # 24.6-08: the typed code a subject-unavailable determination carried
        # (``24.6-L-21``). Same argument as the two above — a brand-new model,
        # no earlier generation — and the field is also what a DISCLOSED shell
        # carries at every level below ``full``, so it must render absent
        # rather than as an explicit null: a rendered `"error_code": null` and
        # a rendered `"error_code": "product_class_unentitled"` differ in
        # shape, and shape is a leak channel (``D-IMPL-253`` am.2 (4)).
        "ccf.products.refusal.SubjectUnavailableRefusal.error_code",
        # 24.6-08: the disclosure posture in force (``24.6-L-16``,
        # ``D-IMPL-253`` Q17). Both are hash-transparent at their sentinels —
        # ``minimal`` on the policy and ``None`` on the grant — so every
        # entitlement policy registered before this field keeps its content
        # address and therefore its pin, and a deployment that never thought
        # about disclosure lands on the safe posture rather than a permissive
        # one.
        "ccf.products.entitlement.ProductEntitlementPolicy.disclosure_level",
        "ccf.products.entitlement.ProductEntitlementGrant.disclosure_level",
        # 24.6-07: the assembler in force on replay dimension 4
        # (``D-IMPL-253`` Q16, ``D-IMPL-245`` amendment 1) and the disclosure
        # decision on dimension 5 (``D-IMPL-254``). All three are silent at
        # their sentinels, which is why the golden `13bd250` record still
        # replays — `tests/replay/test_golden_13bd250.py` measures it.
        "ccf.replay.record.PerspectiveConditioning.assembler_id",
        "ccf.replay.record.PerspectiveConditioning.assembler_version",
        "ccf.replay.record.ContentGenerationPath.disclosure_decision",
        # 24.6-14: the seventh declaration key (``D-IMPL-259``) — a parameter's
        # valid domain, and the two optional ends of one. Silent at the empty
        # mapping and at an absent end, so no committed request contract's
        # content address moves. Added by 24.6-15 at close: plan 14 ticked the
        # twin roster in `tools/lints/tests/test_hash_transparent_key.py` and
        # missed this one, which is exactly the arrival this set-equality test
        # exists to report.
        "ccf.products.request.ProductRequestContract.argument_domains",
        "ccf.products.request.ArgumentDomain.minimum",
        "ccf.products.request.ArgumentDomain.maximum",
        # 24.7-01, the enumerated shape (`D-IMPL-264` D-03/D-06): the
        # closed member set beside the two numeric ends. Silent at `None`,
        # so no committed request contract's address moves — every
        # numeric domain written before the member set existed
        # canonicalizes as it did, and the `ProductRequestContract`
        # digest below still reproduces.
        "ccf.products.request.ArgumentDomain.members",
        # `D-IMPL-325`, the EIGHTH declaration key: a default expressed as an
        # offset from the request's own `asked_at` rather than as a literal that
        # ages. Silent at the empty mapping, so no committed request contract's
        # address moves — and LOUD when populated, deliberately: two products with
        # different relative-window rules must not share one contract identity.
        "ccf.products.request.ProductRequestContract.relative_defaults",
        # `CP04C-F-01` / `D-IMPL-316`: which PAYLOAD FIELD supplies a declared
        # identity key, for rules whose source names the value positionally.
        # Silent when empty, which is every rule written before it existed, so
        # no committed resolution spec's pin moves and no entity URI shifts —
        # the repair changes where a value is read from, never what is hashed.
        "ccf.assembly.worker.EntityResolutionRule.identity_sources",
    }
)


def _every_marked_field_in_the_sdk() -> frozenset[str]:
    import importlib
    import pkgutil

    from pydantic import BaseModel

    import ccf

    for module in pkgutil.walk_packages(ccf.__path__, "ccf."):
        importlib.import_module(module.name)
    found: set[str] = set()
    seen: set[type] = set()

    def walk(cls: type) -> None:
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            if sub.__module__.startswith("ccf."):
                for name in hash_transparent_fields(sub):
                    found.add(f"{sub.__module__}.{sub.__name__}.{name}")
            walk(sub)

    walk(BaseModel)
    return frozenset(found)


def test_the_marked_fields_in_the_tree_are_exactly_the_ticked_table() -> None:
    assert _every_marked_field_in_the_sdk() == _MARKED_IN_THE_TREE


# --- silence equals yesterday, on the real models, against 13bd250 -----------

#: ``content_hash`` of each marked model at its sentinel, MEASURED under the
#: ``13bd250`` tree (the Phase 24.5 base, before any of these fields existed)
#: by ``git archive 13bd250 src | tar -x`` and the same construction under
#: ``PYTHONPATH=<scratch>/src``. The digests are the base tree's, verbatim;
#: HEAD must reproduce every one. The first is CR-01's own reproduction
#: (``34df2d94…``, the number the review measured at base).
_BASE_TREE_DIGESTS = {
    "TraversalNeighborhoodParameters": (
        "34df2d942bbe6d91bdb31d304a50a35a26ea5b291eb13d90fabca17b101775a9"
    ),
    # The directed twin (``D-IMPL-243`` amendment 2) did NOT exist at
    # ``13bd250``; its identity claim is that the canonical form renders
    # fields and never a class name, so the same three required fields at
    # HEAD, with the admission at its sentinel, MUST hash as the base tree's
    # three-field parameters did — the digest above, verbatim. A rendered
    # admission would move it; measured below.
    "TraversalDescendantsParameters": (
        "34df2d942bbe6d91bdb31d304a50a35a26ea5b291eb13d90fabca17b101775a9"
    ),
    "TraversalSpec": (
        "34df2d942bbe6d91bdb31d304a50a35a26ea5b291eb13d90fabca17b101775a9"
    ),
    "GraphQuery": "5e94449b20e50be3e6be2c7d5e566fde5226ed3062074db02f31493d1f0213e5",
    "ProductLineage": (
        "2c321c21705091837fbce2ab234e289c2f07d4fae85a960aaec03221ba0b39fc"
    ),
    "ContextFabricSnapshot": (
        "e0575d5da1537f9a5da9c9ddf3121c7c364f7509d73d24f7e78dba8758337aac"
    ),
    "HalfLifeTable": (
        "66d55b5f9358cce2e7b93a5d0198fd4df96acb3a1297e2bddd7330dba89b894c"
    ),
    "ProductClassDeclaration": (
        "99ca269ca18f91b88cc8f0769aad16646b825dbe3b9387996f4723d76e3252f1"
    ),
    "RegisteredProductClass": (
        "b79c57556c91866267adebe5f8309bab6939ff59888181fb90f5fc61f4d23b43"
    ),
    "ProductRequestContract": (
        "cbc7c95d8564e5e3065eb76f00c1bfe2bf040be906cc81d32687969a9704dfbf"
    ),
    "RelationshipResolutionRule": (
        "657bc97be381a5cf0d5afb1741462624a934a1ddc13eba5b8db76760ed0dffd1"
    ),
}


def _real_models_at_their_sentinels() -> dict[str, object]:
    from datetime import UTC, datetime

    from ccf.assembly.worker import RelationshipResolutionRule
    from ccf.controlplane.artifacts import (
        HalfLifeEntry,
        HalfLifeTable,
        ProductClassDeclaration,
    )
    from ccf.graph.protocols import GraphQuery, TraversalSpec
    from ccf.operators.params import (
        TraversalDescendantsParameters,
        TraversalNeighborhoodParameters,
    )
    from ccf.products.contract import ProductLineage, RegisteredProductClass
    from ccf.products.request import ProductRequestContract, SkillArgumentSchema
    from ccf.replay.record import ContextFabricSnapshot

    at = datetime(2026, 3, 15, tzinfo=UTC)
    spec = TraversalSpec(
        seed_entity_classes=frozenset({"a"}),
        relationship_types=frozenset({"r"}),
        depth_limit=1,
    )
    return {
        "TraversalNeighborhoodParameters": TraversalNeighborhoodParameters(
            seed_entity_classes=frozenset({"a"}),
            relationship_types=frozenset({"r"}),
            depth_limit=1,
        ),
        "TraversalDescendantsParameters": TraversalDescendantsParameters(
            seed_entity_classes=frozenset({"a"}),
            relationship_types=frozenset({"r"}),
            depth_limit=1,
        ),
        "TraversalSpec": spec,
        "GraphQuery": GraphQuery(tenant_id="t", as_of=at, traverse=spec),
        "ProductLineage": ProductLineage(
            operators_invoked=frozenset({"o"}),
            policy_bundle_versions=frozenset({"v"}),
            graph_snapshot_at=at,
        ),
        "ContextFabricSnapshot": ContextFabricSnapshot.build(
            tenant_id="t",
            temporal_boundary=at,
            store_watermark="w",
            touched_entities=("e",),
            touched_relationships=(),
        ),
        "HalfLifeTable": HalfLifeTable(
            semver="1.0.0",
            entries={
                "x": HalfLifeEntry(
                    half_life_seconds=10, decay_driver="d", supersession_event="e"
                )
            },
        ),
        "ProductClassDeclaration": ProductClassDeclaration(
            semver="1.0.0",
            schema_name="s",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key="k",
            required_operator_keys=("o",),
        ),
        "RegisteredProductClass": RegisteredProductClass(
            schema_name="s",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key="k",
            max_ttl_version="v",
        ),
        "ProductRequestContract": ProductRequestContract(
            semver="1.0.0",
            schema_name="s",
            schema_version="1.0.0",
            arguments=SkillArgumentSchema(properties={}, required=()),
        ),
        "RelationshipResolutionRule": RelationshipResolutionRule(
            relationship_type="rel", subject_entity_class="a", object_entity_class="b"
        ),
    }


@pytest.mark.parametrize("model_name", sorted(_BASE_TREE_DIGESTS))
def test_each_marked_model_at_its_sentinel_hashes_as_the_base_tree_did(
    model_name: str,
) -> None:
    """Silence equals yesterday, model by model (``D-IMPL-243``)."""
    instance = _real_models_at_their_sentinels()[model_name]
    assert content_hash(instance) == _BASE_TREE_DIGESTS[model_name]


def test_the_digest_table_and_the_construction_table_name_the_same_models() -> None:
    assert set(_real_models_at_their_sentinels()) == set(_BASE_TREE_DIGESTS)


def test_the_descendants_twin_at_a_non_sentinel_admission_moves_its_hash() -> None:
    """Amendment 2's first tick, both halves: silence equals yesterday, and a
    rendered admission is a new identity — the same two facts row 1 carries."""
    from ccf.operators.params import TraversalDescendantsParameters

    silent = TraversalDescendantsParameters(
        seed_entity_classes=frozenset({"a"}),
        relationship_types=frozenset({"r"}),
        depth_limit=1,
    )
    admitting = silent.model_copy(update={"admitted_entity_classes": frozenset({"a"})})
    assert content_hash(silent) == _BASE_TREE_DIGESTS["TraversalDescendantsParameters"]
    assert content_hash(admitting) != content_hash(silent)
    assert b"admitted_entity_classes" in canonical_bytes(admitting)
    assert b"admitted_entity_classes" not in canonical_bytes(silent)


def test_a_product_with_no_finding_hashes_as_it_did() -> None:
    """``24.6-05``: the computed-empty finding is additive by measurement.

    `ContextProductContract` is not in the base-digest table above — it had no
    marked field until this row — so the claim is measured here, in the form
    that matters: **a product with no computed-empty finding hashes exactly as
    the same product hashed before the field existed**, which is what keeps
    every served product's content address, and the golden `13bd250` replay
    record that resolves one, intact.

    The "before" side is rendered by hand with the new key removed, on
    `test_a_config_naming_no_constraints_hashes_as_it_did`'s reasoning: the
    canonical form renders fields and never a class name. The positive control
    is the second half — a product that DOES carry a finding moves, and the
    key appears in its bytes.
    """
    from datetime import UTC, datetime

    from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN
    from ccf.products.contract import (
        ComputedEmptyFinding,
        ContextProductContract,
        ProductLineage,
    )

    at = datetime(2026, 3, 15, tzinfo=UTC)
    silent = ContextProductContract(
        schema_name="fixture.product",
        schema_version="1.0.0",
        plan_id="fixture.plan",
        tenant_id="fixture-tenant",
        temporal_boundary=at,
        expires_at=at,
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"o"}),
            policy_bundle_versions=frozenset({"v"}),
            graph_snapshot_at=at,
        ),
        payload={"value": 1},
    )
    before = {
        name: getattr(silent, name)
        for name in ContextProductContract.model_fields
        if name != "computed_empty"
    }
    assert content_hash(silent) == content_hash(before)
    assert b"computed_empty" not in canonical_bytes(silent)

    carrying = silent.model_copy(
        update={
            "computed_empty": ComputedEmptyFinding(
                operators_returned_empty=frozenset({"o"}),
                operators_invoked=frozenset({"o"}),
                plan_id="fixture.plan",
                emptiness="attested",
            )
        }
    )
    assert content_hash(carrying) != content_hash(silent)
    assert b"computed_empty" in canonical_bytes(carrying)


def test_a_class_declaring_no_product_gate_hashes_as_it_did() -> None:
    """``24.10-02`` / ``R-11``: the declared product gate is additive, measured.

    The base-tree digest above already carries the strong half — the
    ``ProductClassDeclaration`` row of :data:`_BASE_TREE_DIGESTS` is the
    ``13bd250`` figure and it must still reproduce with this member in the
    model. This test carries the two halves that digest cannot state: that the
    key is **absent** from a silent declaration's bytes rather than merely
    hashing the same by coincidence, and the positive control — a declaration
    that DOES declare a gate moves, and the key appears.

    Why it matters more here than for a member nobody has authored yet: every
    committed product-class document in this tree declares no gate, and pin
    identity IS content identity (``src/ccf/deployment/pins.py::ArtifactPin``).
    A rendered ``declared_product_gate: {}`` would move every one of those
    pins, and cp-05's declarations — read under the Phase 24.10 boundary and
    never edited — are among them.
    """
    from ccf.controlplane.artifacts import ProductClassDeclaration
    from ccf.products.contract import DeclaredProductGate

    silent = ProductClassDeclaration(
        semver="1.0.0",
        schema_name="s",
        schema_version="1.0.0",
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key="k",
        required_operator_keys=("o",),
    )
    assert content_hash(silent) == _BASE_TREE_DIGESTS["ProductClassDeclaration"]
    assert b"declared_product_gate" not in canonical_bytes(silent)

    declaring = silent.model_copy(
        update={
            "declared_product_gate": DeclaredProductGate(
                gate_id="fixture.reconciliation-guard", gate_version="1.0.0"
            )
        }
    )
    assert content_hash(declaring) != content_hash(silent)
    assert b"declared_product_gate" in canonical_bytes(declaring)
    assert b"fixture.reconciliation-guard" in canonical_bytes(declaring)


def test_a_refusal_shell_at_its_sentinels_hashes_as_it_did() -> None:
    """``24.6-07``: the six shell members are additive by measurement.

    `RefusalEnvelope` is not in the base-digest table above — it had no marked
    field until this row — so the claim is measured here, in the form that
    matters: **a shell carrying none of the six hashes exactly as the same
    shell hashed before the fields existed**, which is what keeps every
    envelope that has already crossed a door byte-identical on the wire.

    The "before" side is rendered by hand with the six new keys removed, on
    `test_a_config_naming_no_constraints_hashes_as_it_did`'s reasoning: the
    canonical form renders fields and never a class name. The positive control
    is the second half — a shell that DOES carry a reference moves, and the key
    appears in its bytes — and the third is that all six are absent from the
    silent bytes, enumerated rather than sampled.
    """
    from datetime import UTC, datetime

    from ccf.products.refusal import (
        NO_REPLAY_REFERENCE,
        RefusalEnvelope,
        RequestIdentity,
    )

    at = datetime(2026, 3, 15, tzinfo=UTC)
    silent = RefusalEnvelope(
        kind="product-request-violation",
        reason="missing-required-parameter",
        key="revenue_threshold",
        detail="the question omitted a parameter the class declares required",
        fields={"declared_keys": '["revenue_threshold"]'},
        request=RequestIdentity(
            product_id="fixture.product",
            product_version="1.0.0",
            parameters={},
            temporal_boundary=at,
        ),
        pre_assembly_lineage=None,
    )
    added = (
        "policy_bindings",
        "replay_reference",
        "evidence",
        "provenance",
        "disclosure",
        "resource",
    )
    before = {
        name: getattr(silent, name)
        for name in RefusalEnvelope.model_fields
        if name not in added
    }
    assert content_hash(silent) == content_hash(before)
    for name in added:
        assert name.encode() not in canonical_bytes(silent), name

    carrying = silent.model_copy(update={"replay_reference": "ccf-artifact://r/1"})
    assert content_hash(carrying) != content_hash(silent)
    assert b"replay_reference" in canonical_bytes(carrying)
    assert silent.replay_reference == NO_REPLAY_REFERENCE


def test_a_config_naming_no_constraints_hashes_as_it_did() -> None:
    """``24.6-01``: the ninth reserved section is additive by measurement.

    `DeploymentConfig` is not in the base-digest table above, because the
    class predates neither this phase's field nor `13bd250`'s tree in a way
    that table was built to answer. So the claim is measured here instead, and
    in the form that actually matters: **a config naming no constraints hashes
    exactly as the same config hashed before the field existed** — which is
    what keeps every committed `ccf_config.yaml`'s pin identity intact, since
    pin identity IS content identity
    (`src/ccf/deployment/pins.py::ArtifactPin`).

    The "before" side is built by rendering the model's fields by hand with
    the new key removed, which is what the pre-field canonical form WAS: the
    canonical form renders fields and never a class name, so a dict of the
    same fields hashes as the model did. The positive control is the second
    assertion — a config that DOES name a constraint moves.

    **Every hash-transparent section is removed from the "before" side, not
    only this one** (`24.10-01`). The comparison's subject is *a config at its
    sentinels renders as the pre-field form did*, and a later transparent
    section — `replay`, under `R-12` — is absent from a `24.6`-era document
    for the same reason `policy_constraints` is. Reading the exclusion set off
    the declarations rather than naming one field is what stops the next
    transparent section turning this measurement red without anything having
    gone wrong.
    """
    from ccf.controlplane.artifacts import DeploymentConfig

    silent = DeploymentConfig(
        semver="1.0.0",
        backend="sqlite",
        product_class={"schema_name": "fixture.product"},
    )
    transparent = hash_transparent_fields(DeploymentConfig)
    assert "policy_constraints" in transparent, transparent
    before = {
        name: getattr(silent, name)
        for name in DeploymentConfig.model_fields
        if name not in transparent
    }
    assert content_hash(silent) == content_hash(before)

    naming = silent.model_copy(
        update={"policy_constraints": {"fixture": {"policy_id": "fixture-regime"}}}
    )
    assert content_hash(naming) != content_hash(silent)
    assert b"policy_constraints" in canonical_bytes(naming)
    assert b"policy_constraints" not in canonical_bytes(silent)


def test_a_config_naming_no_replay_binding_hashes_as_it_did() -> None:
    """`24.10-01` / `R-12`: the tenth reserved section name is additive.

    The sibling of :func:`test_a_config_naming_no_constraints_hashes_as_it_did`
    and measured the same way, because the claim that matters is the same one:
    **a config declaring no replay binding hashes exactly as the same config
    hashed before the field existed**, which is what keeps every committed
    `ccf_config.yaml`'s pin identity intact — pin identity IS content identity
    (`src/ccf/deployment/pins.py::ArtifactPin`).

    The "before" side is rendered by hand with the new key removed, on that
    test's reasoning: the canonical form renders fields and never a class name.
    The positive control is the second half — a config that DOES declare a
    binding moves, and the key appears in its bytes.
    """
    from ccf.controlplane.artifacts import DeploymentConfig

    silent = DeploymentConfig(
        semver="1.0.0",
        backend="sqlite",
        product_class={"schema_name": "fixture.product"},
    )
    transparent = hash_transparent_fields(DeploymentConfig)
    assert "replay" in transparent, transparent
    before = {
        name: getattr(silent, name)
        for name in DeploymentConfig.model_fields
        if name not in transparent
    }
    assert content_hash(silent) == content_hash(before)

    declaring = silent.model_copy(
        update={
            "replay": {
                "record_class": "fixture.replay-record",
                "query_pin_class": "fixture.graph-query",
                "store_dirname": "artifacts-store",
            }
        }
    )
    assert content_hash(declaring) != content_hash(silent)
    assert b"replay" in canonical_bytes(declaring)
    assert b"replay" not in canonical_bytes(silent)


# --- D-IMPL-336: the three new marks, measured against `main` ----------------

#: Digests MEASURED under the pre-`D-IMPL-336` tree (`main`, commit `374a3600`)
#: by ``git archive main src | tar -x`` and the same construction under
#: ``PYTHONPATH=<scratch>/src``, before any of these fields existed. HEAD must
#: reproduce both **verbatim** — that is what "the mark is silent at its
#: sentinel" means, and asserting it rather than reasoning about it is the
#: difference between a compatibility claim and a compatibility measurement.
#:
#: ``RegisteredProductClass.requires`` needs no entry here: that model already
#: carries a `13bd250` digest in ``_BASE_TREE_DIGESTS`` above, so the existing
#: measurement covers the third mark and a second one would be a weaker copy.
_PRE_336_DIGESTS = {
    "SkillCatalogEntry": (
        "53a94c2c9fd3b866236fc048565ec1e039c6db4963eeec6c56a9dc7590e91329"
    ),
    "ContentGenerationPath": (
        "a74187ca5c6e9ec6a13728b9db32544f061c7b65ad1b8ee22d21c4871977dd5e"
    ),
}


def test_d_impl_336_marks_are_silent_at_their_sentinels() -> None:
    """A catalog entry and a replay record keep their identity (`D-IMPL-336`).

    The compatibility claim the composite surface rests on: **every skill
    catalog entry registered before ``produces`` existed keeps its content
    hash, so every grant against one stays valid; and every replay record
    written before ``child_resolutions`` existed keeps its address, so nothing
    already stored has to be re-derived.**

    Measured against ``main`` rather than argued from the mark's presence —
    a field can carry the key and still render, and the key is a declaration
    while the digest is evidence.
    """
    entry = SkillCatalogEntry(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="s",
        tenant="t",
        skill_type="local_callable",
        description="d",
        argument_schema=SkillArgumentSchema(properties={}, required=frozenset()),
        binding=LocalCallableBinding(callable_ref="k"),
        requirements=SkillRequirements(
            required_scopes=frozenset(), required_context_products=frozenset()
        ),
    )
    assert entry.produces == NO_PRODUCT_CLASS
    assert content_hash(entry) == _PRE_336_DIGESTS["SkillCatalogEntry"]

    path = ContentGenerationPath(
        plan_id="plan-1",
        operator_plan=(),
        steps=(),
        product_content_address="a" * 64,
    )
    assert path.child_resolutions == ()
    assert content_hash(path) == _PRE_336_DIGESTS["ContentGenerationPath"]


def test_d_impl_336_marks_RENDER_once_declared() -> None:
    """The other half, and the one a sentinel test alone would not catch.

    A field that never rendered would be silent at every value, which is not
    transparency — it is a field nobody can use. Both marks must move the
    address the moment they carry a real declaration.
    """
    entry = SkillCatalogEntry(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="s",
        tenant="t",
        skill_type="local_callable",
        description="d",
        argument_schema=SkillArgumentSchema(properties={}, required=frozenset()),
        binding=LocalCallableBinding(callable_ref="k"),
        requirements=SkillRequirements(
            required_scopes=frozenset(), required_context_products=frozenset()
        ),
        produces="CorporateFamilyTree",
    )
    assert content_hash(entry) != _PRE_336_DIGESTS["SkillCatalogEntry"]

    path = ContentGenerationPath(
        plan_id="plan-1",
        operator_plan=(),
        steps=(),
        product_content_address="a" * 64,
        child_resolutions=(
            ChildResolution(
                required_product_class="CorporateFamilyTree",
                required=True,
                outcome_status="no-producing-skill",
            ),
        ),
    )
    assert content_hash(path) != _PRE_336_DIGESTS["ContentGenerationPath"]
