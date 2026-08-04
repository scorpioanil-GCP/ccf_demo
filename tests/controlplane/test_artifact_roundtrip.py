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
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    OPERATOR_PARAMETERS_POLICY,
    OPERATOR_PARAMETERS_SIMILARITY,
    OPERATOR_PARAMETERS_TEMPORAL,
    OPERATOR_PARAMETERS_TRAVERSAL,
    RESOLUTION_SPEC,
    ArtifactLoadError,
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


def test_every_sdk_artifact_class_has_a_round_trip_case() -> None:
    """No SDK artifact class ships without a round-trip guarantee.

    The vacuity guard for this module. A later plan that adds an artifact class
    to :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` without adding a case
    to :data:`CASES` fails here rather than shipping a class whose documents
    nothing checks.
    """
    assert CASES, "the case list is empty; this module would prove nothing"
    assert set(SDK_ARTIFACT_CLASSES) <= set(_IDS)
