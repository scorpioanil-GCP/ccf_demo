"""Round-trip, hash-stability and closed-world guarantees for every SDK artifact class.

Whitepaper §6.3 (typed contracts, semver lanes), §7.8 (the Control Plane as the
audit plane); D-IMPL-26 (a pin resolves an exact artifact version); D-IMPL-77.

**What this module enforces.** For every artifact class the SDK owns: a document
that parses survives serialization and re-parsing as an equal object; two
independent parses of the same document produce the same content hash, which is
what makes a registered pin reproducible rather than incidentally stable; an
unknown key is refused rather than ignored; and a document that never states its
semver lane is refused rather than defaulted.

**What it does not enforce.** Nothing here says any deployment's document is
*semantically* correct — that a λ_c band is well calibrated, or that a
resolution rule identifies the entity its author meant. Nor does it check that a
contract's field semantics match how the fabric uses them; that is the business
of the tests around each consumer. This module pins the envelope, not the
content.

The cases are a module-level list rather than per-class functions because every
plan that adds an artifact class extends it here, and
:func:`test_every_sdk_artifact_class_has_a_round_trip_case` fails when a class
reaches :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` without one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    DEPLOYMENT_CONFIG,
    DEPLOYMENT_MANIFEST,
    HALF_LIFE_TABLE,
    OPERATOR_PARAMETERS_POLICY,
    OPERATOR_PARAMETERS_SIMILARITY,
    OPERATOR_PARAMETERS_TEMPORAL,
    OPERATOR_PARAMETERS_TRAVERSAL,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PROJECTION_REQUIREMENTS,
    RESOLUTION_SPEC,
    SIGNAL_BATCH,
    ArtifactLoadError,
    ProductClassDeclaration,
    SignalBatch,
    load_artifact,
    parse_artifact,
)
from ccf.deployment.classes import SDK_ARTIFACT_CLASSES
from ccf.operators.categories import (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
    TraversalNeighborhood,
)
from ccf.operators.params import (
    PolicyFilterParameters,
    SimilaritySelectParameters,
    TemporalAsOfParameters,
    TraversalNeighborhoodParameters,
)
from ccf.projection.plan import Perspective
from ccf.signal.envelope import SignalEnvelope
from ccf.similarity.protocol import TokenOverlapIndex

_SEMVER = "1.0.0"


@dataclass(frozen=True)
class _Case:
    """One artifact class and a document that satisfies it.

    Attributes:
        artifact_class: The class under test.
        document: A document that parses cleanly against it.
        unknown_keys: Keys that are *not* declared by the contract. Injected one
            at a time by the closed-world test, so the refusal is attributed to a
            specific key rather than to a batch.
    """

    artifact_class: ArtifactClass
    document: dict[str, Any]
    unknown_keys: tuple[str, ...]


#: Every SDK-owned artifact class, with a document the SDK's own contract accepts.
#:
#: The values are fixture vocabulary, chosen only to satisfy the *shape* each
#: contract declares. They are not calibrations and carry no meaning outside this
#: module (CINV-01: the SDK ships shapes, deployments ship values).
CASES: tuple[_Case, ...] = (
    _Case(
        artifact_class=HALF_LIFE_TABLE,
        document={
            "semver": _SEMVER,
            "entries": {
                "fixture-observation": {
                    "half_life_seconds": 3600,
                    "decay_driver": "fixture-driver",
                    "supersession_event": "fixture-supersession",
                }
            },
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=HALF_LIFE_TABLE,
        # The same class, carrying one supersede-only entry beside a curve
        # entry (ledger row 24.5-L-22). `half_life_seconds` is ABSENT on the
        # event-driven row and the absence is the point: the entry declares
        # its driver and its supersession event and no rate, and a number
        # beside `supersede-only` is refused at parse. The curve row above
        # is unchanged — the reshaping is additive (D-10), and both cases
        # must keep round-tripping.
        document={
            "semver": _SEMVER,
            "entries": {
                "fixture-observation": {
                    "half_life_seconds": 3600,
                    "decay_driver": "fixture-driver",
                    "supersession_event": "fixture-supersession",
                },
                "fixture-event-driven-observation": {
                    "decay": "supersede-only",
                    "decay_driver": "fixture-rewrite",
                    "supersession_event": "fixture-superseding-event",
                },
            },
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=DEBT_PROFILE,
        document={
            "semver": _SEMVER,
            "risk_sensitivity": Decimal("1.5"),
            "forced_llm_threshold": Decimal("0.4"),
            "fail_closed_threshold": Decimal("0.8"),
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=RESOLUTION_SPEC,
        document={
            "semver": _SEMVER,
            "entity_rules": [
                {
                    "match_key": "fixture_ref",
                    "entity_class": "fixture-entity",
                    "identity_keys": ["fixture_ref"],
                    "attribute_keys": ["fixture_attribute"],
                }
            ],
            "relationship_rules": [
                {
                    "relationship_type": "fixture-edge",
                    "subject_entity_class": "fixture-entity",
                    "object_entity_class": "fixture-entity",
                }
            ],
        },
        # The three keys D-03 moves out of the ontology document: `tenant_id`
        # is the deployment's, and the two attribute maps are the operators',
        # not L2's. Naming them here states the split's purpose — the document
        # declares exactly what its consumer reads — rather than testing a
        # synthetic key that would prove only that `extra=forbid` is set.
        unknown_keys=(
            "tenant_id",
            "classification_attribute_by_class",
            "similarity_corpus_attribute_by_class",
        ),
    ),
    _Case(
        artifact_class=OPERATOR_PARAMETERS_TRAVERSAL,
        document={
            "semver": _SEMVER,
            "seed_entity_classes": ["fixture-entity"],
            "relationship_types": ["fixture-edge"],
            "depth_limit": 2,
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=OPERATOR_PARAMETERS_TEMPORAL,
        document={
            "semver": _SEMVER,
            "require_valid_at_boundary": True,
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=OPERATOR_PARAMETERS_POLICY,
        # Exactly three keys, and the omission is the point: the version set is a
        # content hash minted at registration (D-IMPL-76), so an authored
        # document has no value to state for it. These fixtures are the
        # authoring pattern adopters copy, and one inventing a plausible-looking
        # version set would teach the wrong thing.
        document={
            "semver": _SEMVER,
            "classification_attribute_by_class": {"fixture-entity": "fixture_class"},
            "permitted_classifications": ["fixture-classification"],
        },
        unknown_keys=("tenant_id", "permitted_policy_bundle_versions"),
    ),
    _Case(
        artifact_class=OPERATOR_PARAMETERS_SIMILARITY,
        document={
            "semver": _SEMVER,
            "query": "fixture query",
            "minimum_score_percent": 10,
            "ranked_entity_classes": ["fixture-entity"],
            "similarity_corpus_attribute_by_class": {
                "fixture-entity": "fixture_attribute"
            },
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=SIGNAL_BATCH,
        # The document is in the SDK's *own* envelope vocabulary — nested
        # `source: {system_id: ...}` and `raw_payload:` — because that is the
        # whole claim of this class: the batch parses into real envelopes with no
        # translation step for a second field vocabulary to drift from.
        document={
            "semver": _SEMVER,
            "tenant_id": "fixture-tenant",
            "envelopes": [
                {
                    "tenant_id": "fixture-tenant",
                    "envelope_id": "fixture-envelope",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": "2026-01-01T00:00:00Z",
                    "observed_time": "2025-12-31T23:00:00Z",
                    "raw_payload": {"fixture_source_key": "fixture-source-value"},
                }
            ],
        },
        unknown_keys=("source_system_id", "payload"),
    ),
    _Case(
        artifact_class=PERSPECTIVE,
        document={
            "semver": _SEMVER,
            "principal_id": "fixture-principal",
            "role": "fixture-role",
        },
        unknown_keys=("tenant_id",),
    ),
    _Case(
        artifact_class=PRODUCT_CLASS,
        # `max_ttl_version` is absent, and the omission is the point — the same
        # shape as the policy fixture above. Registering the MaxTTL mints that
        # pin, so an authored document has no value to state for it.
        document={
            "semver": _SEMVER,
            "schema_name": "fixture-product",
            "schema_version": "1.0.0",
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "fixture-max-ttl-key",
            "required_operator_keys": ["fixture-operator"],
        },
        unknown_keys=("tenant_id", "max_ttl_version"),
    ),
    _Case(
        artifact_class=PROJECTION_REQUIREMENTS,
        # Deliberately *not* the product-class fixture's operator key. These are
        # two separately authored documents under design E2 (D-IMPL-86), and a
        # fixture that made them agree by copy would teach the shape this class
        # exists to make authorable.
        document={
            "semver": _SEMVER,
            "plan_id": "fixture-plan",
            "required_operator_keys": ["fixture-plan-operator"],
        },
        unknown_keys=("tenant_id", "schema_name"),
    ),
    _Case(
        artifact_class=DEPLOYMENT_MANIFEST,
        # No DSN key and no database-path key, and the omission is the point
        # (D-08): the manifest declares the backend *kind* only, so a connection
        # string never lands in a versioned, content-hashed artifact. `role` is
        # stated on every entry because D-IMPL-80 gives it no default, and
        # `registration` is stated on every entry because D-IMPL-85 gives that
        # one no default either.
        document={
            "semver": _SEMVER,
            "backend": "sqlite",
            "resolution_spec_key": "fixture-resolution-spec",
            "policy_bundle_key": "fixture-policy-bundle",
            "artifacts": [
                {
                    "path": "resolution-spec.yaml",
                    "key": "fixture-resolution-spec",
                    "class_id": "ccf.resolution-spec",
                    "role": "register",
                    "registration": "typed",
                },
                {
                    "path": "policy-bundle.yaml",
                    "key": "fixture-policy-bundle",
                    "class_id": "fixture.policy-bundle",
                    "role": "register",
                    "registration": "typed",
                },
                {
                    "path": "events.yaml",
                    "key": "fixture-signal-batch",
                    "class_id": "ccf.signal-batch",
                    "role": "load",
                    "registration": "typed",
                },
            ],
        },
        unknown_keys=("postgres_dsn", "database_path"),
    ),
    _Case(
        artifact_class=DEPLOYMENT_CONFIG,
        # `D-IMPL-136`'s single-file authoring document (plan 16-28: the
        # parse layer only — nothing here derives, registers, or boots).
        # `backend_secrets` and `survivor_cap` are left at their defaults,
        # exactly as `DEPLOYMENT_MANIFEST`'s own case above does, because
        # the round-trip and hash-stability claims below do not depend on
        # which optional field carries a value. `policy` is an
        # adopter-owned, uninterpreted open mapping (design spec §14.3),
        # carried here unread the same way `DEPLOYMENT_MANIFEST`'s fixture
        # carries `fixture.policy-bundle`'s declaration unread.
        document={
            "semver": _SEMVER,
            "tenant_id": "fixture-tenant",
            "backend": "sqlite",
            "product_class": {
                "schema_name": "fixture-product",
                "schema_version": "1.0.0",
            },
            "policy": {"regime": "fixture-regime"},
        },
        # Neither is a field of this contract at all — D-08's rule that no
        # field of either document ever names a connection value, echoed
        # here exactly as `DEPLOYMENT_MANIFEST`'s own case echoes it.
        unknown_keys=("connection", "dsn"),
    ),
)

_IDS = tuple(case.artifact_class.class_id for case in CASES)


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_a_parsed_artifact_survives_serialization_and_reparsing(case: _Case) -> None:
    """Parse -> serialize -> re-parse returns an equal artifact.

    An artifact that changed under its own serializer could not be stored and
    retrieved from the ArtifactStore without drifting, which would make a
    version pin name something other than what was registered.
    """
    parsed = parse_artifact(case.document, case.artifact_class)
    reparsed = parse_artifact(parsed.model_dump(), case.artifact_class)
    assert reparsed == parsed


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_two_parses_of_one_document_hash_identically(case: _Case) -> None:
    """The content hash is a function of the document, not of the parse.

    This is the property a registered pin rests on: D-05 verifies a version bump
    by comparing content hashes, so a hash that varied between parses would make
    every bump check meaningless.
    """
    first = parse_artifact(case.document, case.artifact_class)
    second = parse_artifact(case.document, case.artifact_class)
    assert content_hash(first) == content_hash(second)


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_an_unknown_key_is_refused(case: _Case) -> None:
    """A key the contract does not declare fails at parse, one key at a time.

    Closed-world validation comes free from ``CCFContract``'s ``extra=forbid``;
    what this pins is that the artifact seam does not quietly widen it. Silently
    ignoring an unrecognized key is the failure mode that matters, because an
    author who mistypes a key would otherwise get a document that parses and
    means something other than what they wrote.
    """
    for unknown in case.unknown_keys:
        document = dict(case.document)
        document[unknown] = "unread-by-this-contract"
        with pytest.raises(ArtifactLoadError):
            parse_artifact(document, case.artifact_class)


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_a_document_that_states_no_semver_is_refused(case: _Case) -> None:
    """An artifact with no declared lane cannot be parsed, and so cannot be registered.

    ``semver`` has no default anywhere in the artifact surface: a default would
    be a version nobody chose, and the registry would then bump-check against a
    lane the author never asserted.
    """
    document = {key: value for key, value in case.document.items() if key != "semver"}
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, case.artifact_class)


def _document_for(class_id: str) -> dict[str, Any]:
    """The round-trip document for ``class_id``, so the operator tests below
    exercise the *same* fixture the envelope tests do rather than a second one
    that could drift from it."""
    for case in CASES:
        if case.artifact_class.class_id == class_id:
            return case.document
    raise AssertionError(f"no case for {class_id}")


# --- the operator-parameters classes: one vocabulary, not two -----------------


def test_a_parsed_traversal_artifact_is_accepted_by_the_traversal_operator() -> None:
    """No field translation exists between artifact and operator, because there
    is nothing to translate: the artifact *is* the parameter set.

    Proving it by construction rather than asserting it in a docstring is the
    point — a second field vocabulary would drift from the operator contract
    silently, and this is where that drift stops (T-15-08-02).
    """
    parsed = parse_artifact(
        _document_for("ccf.operator-parameters.traversal"),
        OPERATOR_PARAMETERS_TRAVERSAL,
    )
    assert isinstance(parsed, TraversalNeighborhoodParameters)
    operator = TraversalNeighborhood(parameters=parsed)
    assert operator.parameters is parsed


def test_a_parsed_temporal_artifact_is_accepted_by_the_temporal_operator() -> None:
    """Sibling of the traversal case; same claim, same absence of mapping."""
    parsed = parse_artifact(
        _document_for("ccf.operator-parameters.temporal"),
        OPERATOR_PARAMETERS_TEMPORAL,
    )
    assert isinstance(parsed, TemporalAsOfParameters)
    operator = TemporalAsOf(parameters=parsed)
    assert operator.parameters is parsed


def test_a_parsed_similarity_artifact_is_accepted_by_the_similarity_operator() -> None:
    """The artifact-only corpus map does not obstruct the operator contract.

    ``similarity_corpus_attribute_by_class`` governs index *construction* and is
    absent from :class:`SimilaritySelectParameters` on purpose; the artifact
    still satisfies that contract and reaches the operator unmapped.
    """
    parsed = parse_artifact(
        _document_for("ccf.operator-parameters.similarity"),
        OPERATOR_PARAMETERS_SIMILARITY,
    )
    assert isinstance(parsed, SimilaritySelectParameters)
    operator = SimilaritySelect(
        parameters=parsed,
        index=TokenOverlapIndex(corpus={}, index_version="fixture-index"),
    )
    assert operator.parameters is parsed


def test_the_similarity_corpus_map_is_artifact_only() -> None:
    """The construction-time value stays off the per-invocation contract.

    Adding it to :class:`SimilaritySelectParameters` would put a value no
    invocation reads onto the L4 invoke contract, which is the reason it lives
    on the artifact instead (D-03).
    """
    assert (
        "similarity_corpus_attribute_by_class"
        not in SimilaritySelectParameters.model_fields
    )


# --- the policy artifact is deliberately not an operator parameter set --------


def test_a_parsed_policy_artifact_is_not_a_policy_filter_parameter_set() -> None:
    """The incompleteness is *structural*, and this is what protects D-IMPL-76.

    ``permitted_policy_bundle_versions`` is a content hash minted at
    registration, so no artifact can declare it and the adopter passes the pin
    set to the operator-registry builder. Had the artifact subclassed
    :class:`PolicyFilterParameters` with a ``frozenset()`` default, a parsed
    document would satisfy ``isinstance`` and could be handed straight to
    :class:`PolicyFilter` by anyone bypassing the builder — yielding an operator
    that admits nothing while looking fully configured (T-15-08-05). The type
    system refuses that here.

    The refusal has two halves. The static half is the annotation:
    ``PolicyFilter.__init__`` takes a ``PolicyFilterParameters``, and the artifact
    is not one — but ``mypy``'s ``files`` are ``src`` and ``runtime``, so no test
    can assert that and this module does not pretend to. What it asserts is the
    dynamic half, which is the one that matters if the annotation is ignored: an
    operator built by bypassing the builder cannot read its own admission set at
    all. It raises rather than admitting nothing — a loud failure rather than a
    silent fail-open.
    """
    parsed = parse_artifact(
        _document_for("ccf.operator-parameters.policy"), OPERATOR_PARAMETERS_POLICY
    )
    assert not isinstance(parsed, PolicyFilterParameters)
    assert "permitted_policy_bundle_versions" not in type(parsed).model_fields
    bypassed = PolicyFilter(parameters=parsed)  # type: ignore[arg-type]
    with pytest.raises(AttributeError):
        _ = bypassed.parameters.permitted_policy_bundle_versions


def test_the_policy_document_states_no_version_set() -> None:
    """The authored document omits the pin entirely — not even an empty one.

    The fixture is the authoring pattern adopters copy. The contract is
    closed-world, so stating the key at all is a parse failure rather than a
    harmless redundancy.
    """
    document = _document_for("ccf.operator-parameters.policy")
    assert "permitted_policy_bundle_versions" not in document
    with pytest.raises(ArtifactLoadError):
        parse_artifact(
            {**document, "permitted_policy_bundle_versions": ["anything"]},
            OPERATOR_PARAMETERS_POLICY,
        )


# --- the signal batch: envelopes, one tenant, and aware timestamps ------------


def test_a_batch_parses_straight_into_envelopes() -> None:
    """No post-processing happens here, and that absence is the assertion.

    Pydantic validates each mapping into a real
    :class:`~ccf.signal.envelope.SignalEnvelope`, so the nested
    ``source: {system_id: ...}`` and ``raw_payload:`` keys arrive as the SDK's own
    contract, not as a document vocabulary something has to translate. The
    translation this replaces was 116 lines across nine sites; a translation
    relocated into ``/src`` would be the same defect with a better address.
    """
    parsed = parse_artifact(_document_for("ccf.signal-batch"), SIGNAL_BATCH)
    assert isinstance(parsed, SignalBatch)
    envelope = parsed.envelopes[0]
    assert isinstance(envelope, SignalEnvelope)
    assert envelope.source.system_id == "fixture-system"
    assert envelope.raw_payload == {"fixture_source_key": "fixture-source-value"}


def test_a_batch_timestamp_ending_in_z_parses_to_an_aware_utc_value() -> None:
    """Closes the loop with plan 15-05: the ``_instant`` helpers are redundant.

    Eleven examples each carried a helper that re-parsed ``...Z`` because PyYAML's
    timestamp resolver hands back a *naive* datetime. ``_ArtifactLoader`` removes
    that resolver, so the scalar reaches the contract as text and the field's own
    ``datetime`` annotation parses the UTC designator the author actually wrote.
    This is the test that makes those helpers redundant rather than merely
    unfashionable — so it goes through :func:`load_artifact` (real YAML), because
    routing around the loader would prove nothing about the defect it fixes.
    """
    text = (
        f'semver: "{_SEMVER}"\n'
        "tenant_id: fixture-tenant\n"
        "envelopes:\n"
        "  - tenant_id: fixture-tenant\n"
        "    envelope_id: fixture-envelope\n"
        "    source:\n"
        "      system_id: fixture-system\n"
        "    ingestion_timestamp: 2026-01-01T00:00:00Z\n"
        "    raw_payload:\n"
        "      fixture_source_key: fixture-source-value\n"
    )
    parsed = load_artifact(text, SIGNAL_BATCH)
    assert isinstance(parsed, SignalBatch)
    ingested = parsed.envelopes[0].ingestion_timestamp
    assert ingested.utcoffset() == timedelta(0)


def test_a_batch_whose_envelope_names_another_tenant_is_refused() -> None:
    """Refused, never repaired (T-15-09-01).

    Stamping the batch's ``tenant_id`` onto a disagreeing envelope would put a
    value nobody authored into the fabric's observation record, and would make a
    cross-tenant event look like a correctly-scoped one. The batch carries the
    tenant so it is authored once, in the artifact that needs it — not so the
    loader can overwrite what an envelope said.
    """
    document = _document_for("ccf.signal-batch")
    envelope = dict(document["envelopes"][0])
    envelope["tenant_id"] = "fixture-other-tenant"
    with pytest.raises(ArtifactLoadError):
        parse_artifact({**document, "envelopes": [envelope]}, SIGNAL_BATCH)


def test_an_empty_batch_is_refused() -> None:
    """An empty ``envelopes`` list is an authoring mistake, not an ingest of nothing."""
    document = _document_for("ccf.signal-batch")
    with pytest.raises(ArtifactLoadError):
        parse_artifact({**document, "envelopes": []}, SIGNAL_BATCH)


# --- the product class: what it declares, and what registration mints ---------


def test_a_parsed_perspective_artifact_is_a_perspective() -> None:
    """The parsed artifact goes where a ``Perspective`` goes, unwrapped.

    Same claim as the operator-parameters classes above: subclassing the existing
    contract means there is no second vocabulary to drift, and no adapter step
    between reading the document and conditioning the projection.
    """
    parsed = parse_artifact(_document_for("ccf.perspective"), PERSPECTIVE)
    assert isinstance(parsed, Perspective)
    assert parsed.principal_id == "fixture-principal"
    assert parsed.role == "fixture-role"


def test_the_product_class_declares_no_max_ttl_version() -> None:
    """The pin is minted by registering the MaxTTL, so no document can state it.

    D-IMPL-76's shape. Declaring it would be authoring a hash of something the
    document does not contain, and it would collapse Gate 3: the TTL ceiling and
    a product's ``expires_at`` are only a real check on each other while they come
    from independent places.
    """
    assert "max_ttl_version" not in ProductClassDeclaration.model_fields
    document = _document_for("ccf.product-class")
    assert "max_ttl_version" not in document
    with pytest.raises(ArtifactLoadError):
        parse_artifact({**document, "max_ttl_version": "1.0.0"}, PRODUCT_CLASS)


def test_a_product_class_declaring_no_operators_is_refused() -> None:
    """The whitepaper's empty-operator guard, enforced where the author can fix it.

    §7.6 specifies the guard as the first of the three validation gates and says
    why: "a projection must have resolved at least one operator to have
    meaningfully read the graph, and an empty set indicates a misconfigured
    projection rather than a trivially-successful one." A declaration of zero
    operators could only ever produce a resolved set of zero, which Gate 1 refuses
    at assembly time — so refusing it at parse is the same rule applied earlier,
    not a stricter one the SDK invented.

    A deployment that serves no product authors no document of this class. That is
    a different thing from a product class declaring that it requires nothing.
    """
    document = _document_for("ccf.product-class")
    with pytest.raises(ArtifactLoadError):
        parse_artifact({**document, "required_operator_keys": []}, PRODUCT_CLASS)


def test_a_projection_requirements_declaring_no_operators_is_refused() -> None:
    """The same empty-operator guard, on the second authored side, watched to fire.

    ``ProjectionRequirements`` carries ``min_length=1`` for exactly the whitepaper
    §7.6 reason ``ProductClassDeclaration`` does — a projection that resolved no
    operator has not meaningfully read the graph — so it gets the same standing
    negative case rather than an argument that it obviously works.

    Why a *declared* constraint needs a committed negative case at all: this
    phase's own signature finding is that a check nobody has watched fire may be
    matching nothing. A ``Field(min_length=1)`` that a Pydantic version change, a
    field rename, or a copy-paste of the wrong annotation quietly stopped
    enforcing would look identical from the source. The only way to know the
    guard is live is to hand it the document it exists to refuse.
    """
    document = _document_for("ccf.projection-requirements")
    with pytest.raises(ArtifactLoadError):
        parse_artifact(
            {**document, "required_operator_keys": []}, PROJECTION_REQUIREMENTS
        )


def test_every_sdk_artifact_class_has_a_round_trip_case() -> None:
    """No SDK artifact class ships without a round-trip guarantee.

    The vacuity guard for this module. A later plan that adds an artifact class
    to :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` without adding a case
    to :data:`CASES` fails here rather than shipping a class whose documents
    nothing checks.
    """
    assert CASES, "the case list is empty; this module would prove nothing"
    assert set(SDK_ARTIFACT_CLASSES) <= set(_IDS)
