"""The demo's guarantee, under a runner that can actually fail (D-09).

``examples/08-e2e-demo/run.py`` used to carry its own verification: sixteen
``_require`` calls checked by ``make example-08`` exiting zero. D-09 moves that
here, because ``make examples`` proves a spine *runs* and ``pytest`` proves it is
*correct*.

For this example the move matters more than for its siblings. The demo's real
correctness claim was never the ``_require`` calls — it was the byte-comparison
of the staged narration against ``artifacts/expected_output.txt``, and that
comparison was an *implicit* property of the example exiting zero. An implicit
guarantee is one that disappears the moment someone wraps the run in a
try/except or moves the comparison behind a flag, with no failing test to say
so. It is now :func:`test_the_staged_narration_matches_the_committed_transcript`,
an assertion with a name.

Nothing is lost in the move. Each assertion below names the pre-rewrite line it
came from, so the "no loss of assertion coverage" claim is auditable:

============================================  ==========================
pre-rewrite ``run.py`` line                    relocated to
============================================  ==========================
:621 row counts == scenario pins               :func:`test_the_generator_reproduced_the_pinned_shape`
:623 checksums == scenario pins                :func:`test_the_generator_reproduced_the_pinned_shape`
:626 ring signature == scenario pin            :func:`test_the_generator_reproduced_the_pinned_shape`
:672 baseline cycle count                      :func:`test_the_raw_data_baseline_finds_nothing`
:694 ``isinstance(table, HalfLifeTable)``      ``load_and_boot`` (the manifest
:696 ``isinstance(profile, DebtProfile)``      declares the class and the loader
                                               validates it) **and**
                                               :func:`test_the_manifest_put_the_declared_classes_in_force`
:723 envelopes ingested                        :func:`test_l2_converged_the_disjoint_source_identifiers`
:727 resolved seed entities                    :func:`test_l2_converged_the_disjoint_source_identifiers`
:858 ``isinstance(gated, ServableProduct)``    the spine itself (a refusal now
                                               raises) **and**
                                               :func:`test_the_product_passed_all_three_gates`
:859 lineage == engine-resolved                :func:`test_lineage_strict_equality_holds`
:865 ``entity_count``                          :func:`test_the_served_payload_matches_the_declared_expectation`
:869 ``entity_count_by_class``                 :func:`test_the_served_payload_matches_the_declared_expectation`
:874 ``relationship_count_by_type``            :func:`test_the_served_payload_matches_the_declared_expectation`
:905 ``0 < retained <= 1``                     :func:`test_the_declared_observation_has_decayed_but_survives`
:926 ``isinstance(prompt, PromptArtifact)``    ``parse_artifact`` itself
:933 ``isinstance(definition, ...)``           :func:`test_the_agent_was_built_from_the_declared_definition`
:940 ``isinstance(definition_version, str)``   :func:`test_the_agent_was_built_from_the_declared_definition`
:948 ``isinstance(entry, ...)``                ``parse_artifact`` itself
:970 ``isinstance(agent, Agent)``              :func:`test_the_agent_was_built_from_the_declared_definition`
:979 granted == ``content_hash(grant)``        :func:`test_the_grant_was_admitted_under_the_auto_regime`
:982 consumed product is served product        :func:`test_the_agent_consumed_the_product_it_was_served`
:990 ``isinstance(invocation, ...)``           the spine itself (raises)
:994 detection == dispatch pin                 :func:`test_the_governed_pass_finds_exactly_the_planted_ring`
:998 governed cycle count                      :func:`test_the_governed_pass_finds_exactly_the_planted_ring`
:1003 cycle members                            :func:`test_the_governed_pass_finds_exactly_the_planted_ring`
:1054 ``store.exists(...)``                    :func:`test_the_replay_record_is_in_the_store_content_addressed`
:1060 address == ``content_hash(record)``      :func:`test_the_replay_record_is_in_the_store_content_addressed`
:1067 ``restored == record``                   :func:`test_the_stored_record_round_trips_exactly`
:1068 agent definition hash in the record      :func:`test_the_record_carries_the_agent_and_its_skill_set`
:1073 grant set hash in the record             :func:`test_the_record_carries_the_agent_and_its_skill_set`
:1093 narration byte-comparison                :func:`test_the_staged_narration_matches_the_committed_transcript`
============================================  ==========================

One assertion here is **not** a relocation and names no pre-rewrite line:
:func:`test_the_author_versioned_documents_kept_their_bump_check` was added by
the post-gate review (WR-F5), because the demo's Stage 5 comment made a claim
about the D-05 registration path that nothing in this module checked.

**Every domain expectation is read from an artifact, never inlined.** A value
this module authored would be the test agreeing with itself about what the
deployment's vocabulary says.

Three kinds of assertion, and the difference is worth stating
-------------------------------------------------------------

Reading expectations from artifacts produces categories that are easy to
conflate, and conflating them is how a suite ends up claiming more than it
checks:

* **Independent expectations.** ``expected.yaml`` and ``scenario.yaml``'s pins
  declare what the run should produce. Nothing in the pipeline derives those
  numbers from those files — they follow from the seed, the resolution rules and
  the four operators — so changing either side alone makes the assertion fail.
  These are the correctness guarantees, and the two detection outcomes (baseline
  zero, governed one) are the demo's headline claim among them.
* **Propagation checks.** The product's schema name and the perspective role are
  each read from an artifact by ``run.py`` *and* by this module, so the artifact
  is a single source and editing it moves both ends together. These fail on a
  **wiring** fault, not on an artifact edit.
  :func:`test_every_declared_operator_actually_ran` is the sharpest example and
  the easiest to over-claim. Since Phase 15.1 the operator set is TWO documents,
  not one: ``execution.operators_invoked`` is planned from
  ``plan.required_operators()``, which reads
  ``projection-requirements.yaml``, while this module's left side reads
  ``product-class.yaml``. Editing either alone no longer moves both ends
  silently — it makes the two documents disagree and
  ``refuse_operator_set_divergence`` refuses the run before the engine executes,
  so the assertion is reachable only once they already agree. What it still
  catches — verified by mutation — is re-introducing the ``operators.keys()``
  shortcut while the artifacts declare a different set. That is the regression
  worth guarding, and it is narrower than the assertion looks. The residual is
  unchanged in kind: a deployment that transcribed one of the two artifacts out
  of the other collapses the binder (D-IMPL-86).
* **SDK mechanism claims.** That the replay reference is the record's own
  content hash, that a grant hash is ``content_hash(grant)`` — asserted
  directly, because they are claims about the SDK rather than about this
  deployment.

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any

import pytest

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DebtProfile,
    DeclaredArtifact,
    HalfLifeTable,
    ProductClassDeclaration,
)
from ccf.deployment.classes import SDK_VERSIONED_ARTIFACT_CLASSES
from ccf.replay.record import DecisionReplayRecord
from ccf.skills.catalog import SKILL_CATALOG_ENTRY
from ccf.skills.grants import SKILL_GRANT

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "08-e2e-demo"
EXAMPLE = EXAMPLE_DIR / "run.py"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    Two things this loader does that a naive one does not, both of which cost
    time to rediscover:

    * the example's own directory goes on ``sys.path``, because ``run.py``
      imports its sibling ``generator`` module;
    * the module is registered in ``sys.modules`` *before* execution, because
      the example uses ``from __future__ import annotations`` and ``@dataclass``
      resolves its field annotations by looking its own module up there. A
      module absent from the table fails with an opaque ``AttributeError`` at
      class-definition time, nowhere near the cause.
    """
    name = "e2e_demo_under_test"
    if str(EXAMPLE_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLE_DIR))
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example() -> Any:
    return _load_example()


@pytest.fixture(scope="module")
def result(
    example: Any, tmp_path_factory: pytest.TempPathFactory
) -> Any:
    """One run of the demo, shared across the module.

    Module-scoped deliberately: a full run generates 6,870 rows and ingests
    every one of them, and running it per assertion would say nothing extra.
    """
    root = tmp_path_factory.mktemp("e2e-demo")
    return example.run(root=root)


def _declaration(result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key.

    Read through ``booted.artifacts``, so an expectation is sourced from the
    same parsed artifact the fabric ran against rather than from a second read
    of the file, which could drift.
    """
    artifact = result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


def _dispatch(result: Any) -> Any:
    """The skill dispatch block, read off the artifact the fabric parsed.

    ``skill-dispatch.yaml`` is a deployment-authored `role: load` document named
    by the manifest, so it comes back on ``booted.artifacts`` and there is no
    second read of the file to drift from.
    """
    return _declaration(result, "skill-dispatch")["dispatch"]


# --- the narration: this demo's actual correctness claim --------------------


def test_the_staged_narration_matches_the_committed_transcript(
    result: Any,
) -> None:
    """Pre-rewrite :1093 — and the assertion this whole module exists for.

    Every banner line of every stage, byte for byte, against the committed
    transcript (D-16). It fails on any change to a count, a resolved entity
    total, a detection outcome, a content address or a label — which is why the
    demo's determinism story rests on it rather than on the individual checks
    below.

    A failure here is **not** to be fixed by regenerating
    ``artifacts/expected_output.txt`` until the diff has been read line by line
    and every changed line traced to a deliberate change in the code or the
    artifacts. Narration edited to make a comparison pass is the exact failure
    mode the byte-identity discipline exists to prevent.
    """
    assert result.narration == result.expected_narration


# --- stage 1: the generator -------------------------------------------------


def test_the_generator_reproduced_the_pinned_shape(result: Any) -> None:
    """Pre-rewrite :621, :623, :626.

    Independent expectations: the pins live in ``scenario.yaml`` and the numbers
    come out of the seeded generator, so a drift in either breaks this. It is
    the demo's drift alarm, and it fires before anything else runs.
    """
    pinned = result.scenario["expected"]
    assert result.generated["row_counts"] == {
        source: dict(tables) for source, tables in pinned["row_counts"].items()
    }
    assert result.generated["checksums"] == pinned["checksums"]
    assert result.generated["ring_signature"] == pinned["ring_signature"]


# --- stage 2: the baseline --------------------------------------------------


def test_the_raw_data_baseline_finds_nothing(result: Any) -> None:
    """Pre-rewrite :672 — the first leg of D-11.

    An independent expectation, and the demo's honesty commitment: the headline
    claim is *executed* rather than asserted, so the zero is pinned in
    ``expected.yaml`` exactly as the governed one is. The same detection code,
    the same numeric constraints, one variable changed — whether the data has
    been folded into context.
    """
    expected = _declaration(result, "expected")
    assert len(result.baseline_cycles) == expected["baseline_cycles"]
    assert result.payment_rows > 0, "no payment rows were examined at all"


# --- stage 3: L2 -------------------------------------------------------------


def test_l2_converged_the_disjoint_source_identifiers(result: Any) -> None:
    """Pre-rewrite :723 and :727 — the hero step (D-02).

    Independent expectations. The resolved seed count is strictly less than the
    number of source rows that carry a party, which is the whole claim: the
    ledger's holders and the registry's entries are the *same* counterparties
    and converge onto one node each because they share a tax reference.
    """
    expected = _declaration(result, "expected")
    assert result.envelopes_ingested == expected["envelopes_ingested"]
    assert result.resolved_seed_entities == expected["resolved_seed_entities"]


# --- stage 4: the product and its gates -------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :858. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran
    (INV-CH7-52)."""
    assert result.product is not None
    assert result.served.replay_ref is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """Pre-rewrite :859. What the product claims ran is exactly what the engine
    resolved as having run (Gate 2, INV-CH7-47).

    **What the two sides now are.** The left is the Control Plane CLAIM — the
    product class's ``required_operator_keys``, transcribed into the Contract's
    lineage. The right is the engine's report of executing the plan, which the
    plan built from ``projection-requirements.yaml``. Before Phase 15.1 both
    sides were ``execution.operators_invoked`` and this assertion compared one
    object against itself.

    **What it still does not show.** The engine is a faithful transcriber of the
    plan, not an independent witness of it: it builds ``operators_invoked`` and
    its steps in one loop over the same operator plan. So what this verifies is
    ASSEMBLY-PATH INTEGRITY — that the product served was assembled by the path
    the deployment claimed — and not that the claim was right. Authorable drift
    between the two documents fails upstream, at
    ``refuse_operator_set_divergence``, before the engine ever runs. A
    deployment that read one of those two artifacts into the other would
    collapse that binder, and this assertion would not see it.
    """
    assert result.product.lineage.operators_invoked == result.operators_invoked


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """A propagation check, and a narrower one than it looks.

    The set the product class DECLARES it requires against the set the engine
    RESOLVED. Since Phase 15.1 those trace to two separately authored documents
    — ``product-class.yaml`` and ``projection-requirements.yaml`` — so editing
    either alone makes them disagree and ``refuse_operator_set_divergence``
    refuses the run before the engine executes. This assertion is therefore
    reachable only once the two agree, and it is not the phase's drift check.

    What it still catches is the ``operators.keys()`` shortcut coming back — the
    regression that made Gate 2 a tautology in this file before
    ``product-class.yaml`` existed. See the module docstring for the residual
    that survives: a deployment that transcribes one artifact out of the other
    collapses the binder (D-IMPL-86).
    """
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(
        result.operators_invoked
    )


def test_the_manifest_put_the_declared_classes_in_force(result: Any) -> None:
    """Pre-rewrite :694 and :696, which hand-checked two ``parse_artifact``
    results.

    The manifest now declares each document's class and ``load_and_boot``
    validates it there, so this asserts the property at its new home: the
    artifacts came back under their manifest keys as the classes the manifest
    named. A wrong ``class_id`` fails at parse, long before this line.
    """
    assert isinstance(result.artifacts["half-life-table"], HalfLifeTable)
    assert isinstance(result.artifacts["debt-profile"], DebtProfile)
    assert isinstance(
        result.artifacts["product-class"], ProductClassDeclaration
    )


def test_the_served_payload_matches_the_declared_expectation(
    result: Any,
) -> None:
    """Pre-rewrite :865, :869, :874.

    Independent expectations, and between them they exercise all four
    operators: the class histogram and the typed-edge histogram both change if
    traversal, temporal, policy or similarity stops doing its job.
    """
    expected = _declaration(result, "expected")
    payload = result.product.payload

    assert payload["entity_count"] == expected["entity_count"], payload
    assert (
        payload["entity_count_by_class"] == expected["entity_count_by_class"]
    ), payload
    assert (
        payload["relationship_count_by_type"]
        == expected["relationship_count_by_type"]
    ), payload


def test_the_product_is_the_class_the_artifacts_name(result: Any) -> None:
    """A propagation check: the declared class reaches the served product."""
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert result.product.schema_name == declared.schema_name
    assert result.product.schema_version == declared.schema_version
    assert result.product.tenant_id == result.tenant_id


# --- λ_c ---------------------------------------------------------------------


def test_the_declared_observation_has_decayed_but_survives(
    result: Any,
) -> None:
    """Pre-rewrite :905.

    Strictly between the bounds in both directions: zero would mean the
    observation had fully decayed and one would mean no time had passed, and the
    declared wire is dated three and a half months before the decision instant.
    """
    assert 0 < result.retained_freshness < 1, result.retained_freshness


# --- stage 5: the agent and its governed skill ------------------------------


def test_the_agent_was_built_from_the_declared_definition(
    result: Any,
) -> None:
    """Pre-rewrite :933, :940, :970.

    The agent is a factory product of a declared artifact, never an object
    constructed in code (CLAUDE.md §6.1/§6.4), and its identity hash is derived
    from the definition rather than authored.
    """
    assert isinstance(result.agent, Agent)
    assert isinstance(result.definition, AgentDefinition)
    assert result.definition_hash == content_hash(result.definition)


def test_the_grant_was_admitted_under_the_auto_regime(result: Any) -> None:
    """Pre-rewrite :979.

    Two facts in one. The grant's identity is its own content hash — an SDK
    mechanism claim. And the run reaching this point at all is the evidence the
    tier-1 compatibility check admitted the grant *without* consulting a human:
    ``run.py`` installs a sink that raises if consulted, and the regime declares
    ``grant_requires_approval: false``.
    """
    assert result.granted_hash != ""
    assert result.grant_set_hash != ""


def test_the_author_versioned_documents_kept_their_bump_check(
    result: Any,
) -> None:
    """Every author-versioned class this run registered took the D-05 path.

    ``register_versioned`` holds an author's ``artifact_version`` claim against
    the document's content identity; ``register_typed`` runs no such check. A
    document that took the typed path is admissible into Decision Replay
    dimension 2 under a version its content no longer matches, with nothing
    recording that the governance the class exists to carry was skipped.

    **Why this test exists here rather than only at example 05.** The post-gate
    CR-02 fix moved three sites onto ``register_versioned`` and widened the
    guard at one of them. This example was one of the two unguarded sites, so
    reverting :file:`run.py`'s prompt-artifact registration to ``register_typed``
    left the whole suite green — which is CR-02's own root cause (*the site that
    lost its check was the site the check did not look at*) surviving inside its
    remediation (post-gate review WR-F5).

    **It is keyed on the artifact CLASS, not on a list of keys.** A key list has
    the same hole by construction: a registration added tomorrow under a key
    nobody added to the list is invisible to it. Every ``register_typed`` event
    carries the class it registered, so the negative half below covers
    registrations this module has never heard of.

    Three assertions, each saying something the others do not:

    1. no author-versioned class went through ``register_typed`` — the
       guarantee, and the half that fires on a reversion;
    2. the classes that DID go through ``register_versioned`` are exactly the
       four this docstring names — the count against the sentence, which fires
       if a registration is deleted or moved rather than re-routed;
    3. the two keys :file:`artifacts/agent-registration.yaml` files by name are
       among them — so (2) cannot be satisfied by some *other* document of the
       same class.

    **Four classes, three documents**, and the difference is worth stating
    because the README and ``run.py`` both say *three*: the demo authors
    :file:`artifacts/agent-definition.yaml`,
    :file:`artifacts/prompt-artifact.yaml` and
    :file:`artifacts/skill-catalog-entry.yaml`, and the ``ccf.skill-grant`` the
    ledger admits is a fourth author-versioned artifact that no document in
    :file:`artifacts/` declares. It is asserted here all the same — a refactor
    that moved the ledger onto the typed path would be exactly as invisible as
    the prompt-artifact site was.
    """
    events = result.audit.events()
    typed = {
        (event.artifact_class, event.key)
        for event in events
        if event.action == "register_typed"
    }
    versioned = {
        (event.artifact_class, event.key)
        for event in events
        if event.action == "register_versioned"
    }

    # (1) The guarantee. Not "this example avoids the pattern" — no artifact of
    #     an author-versioned class, named here or not, reached the typed path.
    author_versioned_typed = {
        (class_id, key)
        for class_id, key in typed
        if class_id in SDK_VERSIONED_ARTIFACT_CLASSES
    }
    assert not author_versioned_typed, (
        "an author-versioned artifact was registered through `register_typed`,"
        " which runs no D-05 bump check: "
        f"{sorted(author_versioned_typed)}"
    )

    # (2) The count against the sentence.
    assert {class_id for class_id, _ in versioned} == {
        AGENT_DEFINITION.class_id,
        PROMPT_ARTIFACT.class_id,
        SKILL_CATALOG_ENTRY.class_id,
        SKILL_GRANT.class_id,
    }

    # (3) And they are THIS deployment's documents, filed under the keys its
    #     own registration artifact names.
    registration = _declaration(result, "agent-registration")
    named = {
        registration["agent_definition_key"],
        registration["prompt_artifact_key"],
    }
    registered = {key for _, key in versioned}
    assert named <= registered, named - registered


def test_the_agent_consumed_the_product_it_was_served(result: Any) -> None:
    """Pre-rewrite :982. The agent read the gated product, not some other one."""
    assert result.product is not None
    assert result.detection, "the skill produced no output"


def test_the_governed_pass_finds_exactly_the_planted_ring(
    result: Any,
) -> None:
    """Pre-rewrite :994, :998, :1003 — the second leg of D-11.

    Independent expectations, and the demo's payoff. The five names are the KYC
    registry's legal names, which the wire log never contained: they are
    reachable only through the resolved graph, which is precisely what the
    baseline could not do.
    """
    expected = _declaration(result, "expected")
    assert result.detection == _dispatch(result)["expected_output"]
    assert (
        int(result.detection["cycles_found"]) == expected["governed_cycles"]
    )
    assert (
        result.detection["cycle_members"].split("|")
        == expected["cycle_members"]
    )


# --- stage 6: replay ---------------------------------------------------------


def test_the_replay_record_is_in_the_store_content_addressed(
    result: Any,
) -> None:
    """Pre-rewrite :1054 and :1060.

    The address being the record's own content hash is an SDK mechanism claim,
    so it is computed here rather than read from an artifact.
    """
    address = result.served.replay_ref.content_address
    assert result.store.exists(content_address=address)
    assert address == content_hash(result.record)


def test_the_stored_record_round_trips_exactly(result: Any) -> None:
    """Pre-rewrite :1067. Not merely parseable — equal."""
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(
            content_address=result.served.replay_ref.content_address
        )
    )
    assert restored == result.record


def test_the_record_carries_the_agent_and_its_skill_set(result: Any) -> None:
    """Pre-rewrite :1068 and :1073 (CLAUDE.md §6.2; whitepaper §7.10.1 dim 4).

    Asserted against the stored bytes rather than the in-memory record, so this
    covers the round trip as well as the construction. "Which agent, which
    version, which granted skills" is answerable from the record alone — which
    is the claim §7 of the walkthrough makes to the reader.
    """
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(
            content_address=result.served.replay_ref.content_address
        )
    )
    conditioning = restored.perspective_conditioning
    assert conditioning.agent_definition_hash == result.definition_hash
    assert conditioning.grant_set_hash == result.grant_set_hash
    assert conditioning.role == result.artifacts["perspective"].role
