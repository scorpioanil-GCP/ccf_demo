"""D-07 — what the operator-registry builder makes structural, and what it refuses.

Whitepaper §7.4 (the four canonical categories, INV-CH7-26 ordering, INV-CH7-27
similarity determinism) and §7.8 (the Control Plane declares what the fabric may
do); CLAUDE.md §6.4 and §10 for the SDK-defined ``ccf.deployment`` package.

**What these tests enforce.**

1. The ordering constraint is in the *signature*: ``view`` is keyword-only with
   ``Parameter.empty`` as its default, so a registry cannot be built before a
   view exists. This is the standing guard against the builder drifting toward
   lazy index binding because the two-phase signature is awkward.
2. The corpus tracks the boundary the caller named, not invocation time —
   asserted on **what the built index actually ranks**, not on object identity.
3. ``permitted_policy_bundle_versions`` comes from the adopter-passed pin set
   and from nowhere else (D-IMPL-76), with the negative half: the parsed policy
   *artifact* carries no such attribute at all.
4. The corpus attribute map is read from the similarity artifact's own field,
   and stays out of the L4 invoke contract.
5. The corpus ruling: an entity class the map does not name contributes no entry
   (silent, correct); an entity of a named class carrying no such attribute is
   **refused** rather than repaired. Nine deployments will follow this, so it is
   asserted rather than left to the docstring.
6. Category is never caller-declared — asserted against the module's own AST.
7. A partial operator set builds a partial registry without complaint, and a
   duplicate operator key stays fatal.

**What they do not enforce.** They do not enforce that the deployment chose the
*right* temporal boundary — which boundary a decision needs is the deployment's
policy, and the builder's whole contribution is making the choice explicit
rather than making it. They do not enforce that the corpus attribute map is
semantically correct: that ``label`` is a sensible thing to rank a bank account
on is a deployment judgement the SDK has no basis to second-guess. And they say
nothing about whether the built registry satisfies any product's declared
operator set — that comparison is Gate 2's, and it is deliberately not
reachable from this builder's return value alone.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    PolicyFilterParametersArtifact,
    SimilaritySelectParametersArtifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.deployment.operators import (
    SimilarityCorpusAttributeError,
    build_operator_registry,
)
from ccf.deployment.pins import ArtifactPin, ResolvedPins
from ccf.operators import params as operator_params
from ccf.operators.registry import DuplicateOperatorKey

from tests.deployment.conftest import (
    POLICY_BUNDLE_KEY,
    POLICY_PARAMS_KEY,
    SIGNAL_BATCH_KEY,
    SIMILARITY_KEY,
    TEMPORAL_KEY,
    TENANT,
    TRAVERSAL_KEY,
    Deployment,
)

#: The four operator-parameters manifest keys, in the fixture's vocabulary.
OPERATOR_KEYS = (TRAVERSAL_KEY, TEMPORAL_KEY, POLICY_PARAMS_KEY, SIMILARITY_KEY)

#: A test-side index version. Never an SDK value — the deployment assigns it.
INDEX_VERSION = "fixture-corpus-1"


def _boot(deployment: Deployment, tmp_path: pathlib.Path, *, name: str) -> Any:
    """Boot the fixture deployment onto its own SQLite file."""
    return load_and_boot(
        deployment.manifest_path,
        registry=ControlPlaneRegistry(),
        database_path=str(tmp_path / name),
    )


def _parameters(booted: Any, *keys: str) -> dict[str, Any]:
    """The adopter-side idiom: name your own manifest keys, no type filtering."""
    return {key: booted.artifacts[key] for key in keys}


def _envelope(booted: Any, *, envelope_id: str, hours: int, **payload: Any) -> Any:
    """A second envelope derived from the fixture's, at a later boundary."""
    template = booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0]
    return template.model_copy(
        update={
            "envelope_id": envelope_id,
            "ingestion_timestamp": template.ingestion_timestamp.replace(
                hour=template.ingestion_timestamp.hour + hours
            ),
            "raw_payload": payload,
        }
    )


def _ranked(registry: Any, view: Any) -> set[str]:
    """Which of ``view``'s entities the registry's index actually holds.

    Observable behavior, deliberately: ``TokenOverlapIndex.rank`` skips a
    candidate with no corpus entry, so the returned URI set *is* the corpus
    membership among those candidates. Asserting on this rather than on index
    identity is what makes the boundary test say something — two distinct index
    objects prove nothing about the corpus they were built from.
    """
    index = registry.resolve("similarity.corpus-select")._index
    hits = index.rank(
        tenant_id=view.tenant_id,
        query="fixture",
        candidates=tuple(record.claim.entity_uri for record in view.entities),
    )
    return {hit.entity_uri for hit in hits}


# --- (1) the ordering constraint is structural --------------------------------


def test_the_view_is_a_required_keyword_only_parameter() -> None:
    """D-07. The signature is the guard, so the signature is what is asserted.

    Not merely that omitting ``view`` raises — a default of ``None`` plus a
    runtime check would also raise, and would leave the door open to a later
    "convenience" default that builds the index lazily. ``Parameter.empty`` says
    there is no value to fall back to.
    """
    parameter = inspect.signature(build_operator_registry).parameters["view"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty

    with pytest.raises(TypeError):
        build_operator_registry(  # type: ignore[call-arg]
            parameters={},
            pins=ResolvedPins(),
            policy_bundle_key=POLICY_BUNDLE_KEY,
        )


# --- (2) the corpus tracks the caller's boundary ------------------------------


def test_the_corpus_is_read_at_the_boundary_the_caller_named(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """INV-CH7-27. Two boundaries, two corpora, asserted on what each index ranks.

    **Both ingests happen before either registry is built**, and that ordering
    is what makes the test sharp. If the earlier registry were built while the
    graph still held one entity, an implementation that ignored ``view`` and
    read the live graph at build time would produce the same one-entity corpus
    and the test would pass for the wrong reason. Building both registries
    against a two-entity graph means only the boundary carried by ``view`` can
    account for the difference.
    """
    booted = _boot(deployment, tmp_path, name="boundary.sqlite3")
    try:
        first_envelope = booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0]
        early = first_envelope.ingestion_timestamp

        second_envelope = _envelope(
            booted,
            envelope_id="envelope-fixture-2",
            hours=1,
            account_ref="acct-2",
            classification="fixture-open",
            label="fixture second account",
        )
        late = second_envelope.ingestion_timestamp
        assert late > early

        booted.handle.worker.ingest(first_envelope)
        booted.handle.worker.ingest(second_envelope)

        early_view = booted.handle.reader.as_of(tenant_id=TENANT, at=early)
        late_view = booted.handle.reader.as_of(tenant_id=TENANT, at=late)
        assert len(early_view.entities) == 1
        assert len(late_view.entities) == 2

        early_registry = build_operator_registry(
            parameters=_parameters(booted, *OPERATOR_KEYS),
            view=early_view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=INDEX_VERSION,
        )
        late_registry = build_operator_registry(
            parameters=_parameters(booted, *OPERATOR_KEYS),
            view=late_view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=INDEX_VERSION,
        )

        # The candidate set is the *later* view both times, so the difference is
        # in the corpora and not in what each index was asked about.
        early_corpus = _ranked(early_registry, late_view)
        late_corpus = _ranked(late_registry, late_view)

        assert len(early_corpus) == 1
        assert len(late_corpus) == 2
        assert early_corpus < late_corpus
    finally:
        booted.handle.close()


# --- (3) the policy pin comes from the pin set --------------------------------


def _policy_versions(registry: Any) -> frozenset[str]:
    operator = registry.resolve("policy.principal-subgraph")
    return operator.parameters.permitted_policy_bundle_versions


@pytest.mark.parametrize("version", ["pin-alpha", "pin-beta"])
def test_the_admitted_policy_versions_come_from_the_passed_pins(
    deployment: Deployment, tmp_path: pathlib.Path, version: str
) -> None:
    """D-IMPL-76. The adopter names what is admitted; the SDK looks it up.

    Parameterized over two distinct pins so the assertion cannot pass by the
    value happening to match whatever the registry holds — changing the pin
    changes admission, which is what proves the value is not read from the
    Control Plane inside the builder.
    """
    booted = _boot(deployment, tmp_path, name=f"pins-{version}.sqlite3")
    try:
        view = booted.handle.reader.as_of(
            tenant_id=TENANT,
            at=booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0].ingestion_timestamp,
        )
        registry = build_operator_registry(
            parameters=_parameters(booted, POLICY_PARAMS_KEY),
            view=view,
            pins=ResolvedPins(
                entries=(
                    ArtifactPin(
                        key=POLICY_BUNDLE_KEY,
                        version=version,
                        class_id="fixture.policy-bundle",
                    ),
                )
            ),
            policy_bundle_key=POLICY_BUNDLE_KEY,
        )

        assert _policy_versions(registry) == frozenset({version})
    finally:
        booted.handle.close()


def test_the_policy_artifact_declares_no_admitted_version_set_at_all() -> None:
    """The negative half of D-IMPL-76, and the reason the builder is the only path.

    ``PolicyFilterParametersArtifact`` is deliberately not a
    ``PolicyFilterParameters``. If it declared the field — even defaulted to an
    empty frozenset — a parsed artifact could be handed straight to
    ``PolicyFilter`` by anyone bypassing the builder, producing an operator that
    admits nothing while looking fully configured.
    """
    assert (
        "permitted_policy_bundle_versions"
        not in PolicyFilterParametersArtifact.model_fields
    )
    assert not issubclass(
        PolicyFilterParametersArtifact, operator_params.PolicyFilterParameters
    )


# --- (3b) the corpus map comes from the similarity artifact -------------------


def test_the_corpus_map_is_read_from_the_similarity_artifact(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The map is artifact state, not an ontology read and not a module constant.

    Changing the field on the artifact changes what the built index holds. If
    the builder were reading the map from anywhere else, the mutated artifact
    would make no difference.
    """
    booted = _boot(deployment, tmp_path, name="corpusmap.sqlite3")
    try:
        envelope = booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0]
        booted.handle.worker.ingest(envelope)
        view = booted.handle.reader.as_of(
            tenant_id=TENANT, at=envelope.ingestion_timestamp
        )

        declared = build_operator_registry(
            parameters=_parameters(booted, SIMILARITY_KEY),
            view=view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=INDEX_VERSION,
        )
        assert _ranked(declared, view)

        emptied = booted.artifacts[SIMILARITY_KEY].model_copy(
            update={"similarity_corpus_attribute_by_class": {}}
        )
        stripped = build_operator_registry(
            parameters={SIMILARITY_KEY: emptied},
            view=view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=INDEX_VERSION,
        )
        assert _ranked(stripped, view) == set()
    finally:
        booted.handle.close()


def test_the_corpus_map_stayed_out_of_the_l4_invoke_contract() -> None:
    """T-15-11-06. A construction-time value on the per-invocation parameter set
    would make the operator carry state no invocation reads — and would invite a
    re-read of the corpus per invocation, which is the drift this pins shut."""
    assert (
        "similarity_corpus_attribute_by_class"
        in SimilaritySelectParametersArtifact.model_fields
    )
    assert (
        "similarity_corpus_attribute_by_class"
        not in operator_params.SimilaritySelectParameters.model_fields
    )


# --- (3c) the corpus ruling: skip a class, refuse a missing attribute ---------


def test_an_entity_class_the_map_does_not_name_contributes_no_corpus_entry(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Silent skip, and correct. The map is the deployment's statement of which
    classes are rankable; a class it does not name is one the deployment chose
    to leave out of the corpus. There is nothing to repair and nothing to
    report."""
    booted = _boot(deployment, tmp_path, name="unnamed-class.sqlite3")
    try:
        envelope = booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0]
        booted.handle.worker.ingest(envelope)
        view = booted.handle.reader.as_of(
            tenant_id=TENANT, at=envelope.ingestion_timestamp
        )
        assert view.entities  # the skip is over a non-empty view, not a vacuum

        unrelated = booted.artifacts[SIMILARITY_KEY].model_copy(
            update={
                "similarity_corpus_attribute_by_class": {"fixture-other": "label"}
            }
        )
        registry = build_operator_registry(
            parameters={SIMILARITY_KEY: unrelated},
            view=view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=INDEX_VERSION,
        )

        assert _ranked(registry, view) == set()
    finally:
        booted.handle.close()


def test_an_entity_missing_its_declared_corpus_attribute_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Refuse, never repair — the ruling nine deployments will follow.

    The declaration says this class's corpus text lives at ``label`` and this
    entity has no ``label``: the artifact and the graph contradict each other.
    Skipping the entity would drop it from the corpus, ``rank`` would then pass
    over it, and the similarity operator would exclude it from the view — a
    governed omission produced by no rule anyone wrote down. Substituting an
    empty string is the same omission wearing a score.
    """
    booted = _boot(deployment, tmp_path, name="missing-attr.sqlite3")
    try:
        unlabelled = _envelope(
            booted,
            envelope_id="envelope-fixture-unlabelled",
            hours=2,
            account_ref="acct-3",
            classification="fixture-open",
        )
        booted.handle.worker.ingest(unlabelled)
        view = booted.handle.reader.as_of(
            tenant_id=TENANT, at=unlabelled.ingestion_timestamp
        )

        with pytest.raises(SimilarityCorpusAttributeError) as raised:
            build_operator_registry(
                parameters=_parameters(booted, SIMILARITY_KEY),
                view=view,
                pins=booted.pins,
                policy_bundle_key=POLICY_BUNDLE_KEY,
                similarity_index_version=INDEX_VERSION,
            )

        # The message names the attribute, so the two documents that disagree
        # are both identifiable from the failure alone.
        assert "label" in str(raised.value)
    finally:
        booted.handle.close()


# --- (4) category is never caller-declared -----------------------------------


def test_every_registered_operator_reports_its_own_category(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """INV-CH7-26. The registry's recorded category is the operator's own."""
    booted = _boot(deployment, tmp_path, name="category.sqlite3")
    try:
        envelope = booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0]
        booted.handle.worker.ingest(envelope)
        view = booted.handle.reader.as_of(
            tenant_id=TENANT, at=envelope.ingestion_timestamp
        )
        registry = build_operator_registry(
            parameters=_parameters(booted, *OPERATOR_KEYS),
            view=view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version=INDEX_VERSION,
        )

        assert len(registry) == len(OPERATOR_KEYS)
        for registration in registry.registrations():
            assert registration.category == registration.operator.category
    finally:
        booted.handle.close()


def test_the_builder_passes_no_category_to_register() -> None:
    """T-15-11-02, asserted against the module's AST rather than its behavior.

    A behavioral test would pass if a future edit declared each operator's *own*
    category explicitly — which reads harmlessly and reopens exactly the failure
    ``register`` is written to prevent, because the next edit after that one is
    the wrong literal.
    """
    from ccf.deployment import operators as module

    tree = ast.parse(inspect.getsource(module))
    register_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "register"
    ]

    assert register_calls, "no register() call found — the AST check went vacuous"
    for call in register_calls:
        assert not [keyword for keyword in call.keywords if keyword.arg == "category"]


# --- (5) partial operator sets ------------------------------------------------


def test_a_parameters_mapping_of_three_builds_a_three_operator_registry(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Which operators exist is per-deployment policy, expressed by the mapping.

    ``examples/02-skilling`` registers three, not four, so a builder with a
    hardcoded set of four keys would refuse a deployment the SDK has no business
    refusing.
    """
    booted = _boot(deployment, tmp_path, name="partial.sqlite3")
    try:
        view = booted.handle.reader.as_of(
            tenant_id=TENANT,
            at=booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0].ingestion_timestamp,
        )
        registry = build_operator_registry(
            parameters=_parameters(
                booted, TRAVERSAL_KEY, TEMPORAL_KEY, POLICY_PARAMS_KEY
            ),
            view=view,
            pins=booted.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
        )

        assert len(registry) == 3
        assert "similarity.corpus-select" not in registry
    finally:
        booted.handle.close()


# --- (6) a duplicate operator key stays fatal ---------------------------------


def test_two_entries_producing_one_operator_key_are_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """INV-CH7-29, uncaught. Two operators answering to one key make every plan
    naming it ambiguous, and keeping one of them makes the ambiguity
    invisible."""
    booted = _boot(deployment, tmp_path, name="duplicate.sqlite3")
    try:
        view = booted.handle.reader.as_of(
            tenant_id=TENANT,
            at=booted.artifacts[SIGNAL_BATCH_KEY].envelopes[0].ingestion_timestamp,
        )
        traversal = booted.artifacts[TRAVERSAL_KEY]

        with pytest.raises(DuplicateOperatorKey):
            build_operator_registry(
                parameters={
                    TRAVERSAL_KEY: traversal,
                    f"{TRAVERSAL_KEY}-again": traversal.model_copy(),
                },
                view=view,
                pins=booted.pins,
                policy_bundle_key=POLICY_BUNDLE_KEY,
            )
    finally:
        booted.handle.close()
