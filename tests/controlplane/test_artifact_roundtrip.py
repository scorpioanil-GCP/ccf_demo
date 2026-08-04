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
    RESOLUTION_SPEC,
    ArtifactLoadError,
    parse_artifact,
)
from ccf.deployment.classes import SDK_ARTIFACT_CLASSES

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


def test_every_sdk_artifact_class_has_a_round_trip_case() -> None:
    """No SDK artifact class ships without a round-trip guarantee.

    The vacuity guard for this module. A later plan that adds an artifact class
    to :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` without adding a case
    to :data:`CASES` fails here rather than shipping a class whose documents
    nothing checks.
    """
    assert CASES, "the case list is empty; this module would prove nothing"
    assert set(SDK_ARTIFACT_CLASSES) <= set(_IDS)
