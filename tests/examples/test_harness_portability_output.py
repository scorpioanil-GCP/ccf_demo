"""The harness-portability proof's assertions, under a runner that can fail (D-09).

``archive/examples/03-harness-portability/run.py`` used to carry its own guarantee:
the deterministic drive's ``assert`` statements and ``print`` summaries,
checked by ``make example-03`` exiting zero. D-09 moves that guarantee here,
because ``make examples`` proves a spine *runs* and ``pytest`` proves it is
*correct*.

**The two-harness equivalence assertion is inherited, not invented here.**
Example 03 exists to demonstrate CLAUDE.md §1's third success condition and
§7.3's closing commitment: *one agent definition running unmodified under more
than one harness, producing equivalent Context Product consumption and
equivalent replay records*. Pre-rewrite ``run.py`` asserted exactly that at
:519-522 (consumption, byte-identical across legs and equal to what the fabric
admitted) and at :531-539 (the governed replay fields, exactly equal field by
field). Both are relocated verbatim in substance below, as

* :func:`test_the_same_context_product_reached_every_harness` — consumption;
* :func:`test_the_governed_replay_fields_are_equal_across_harnesses` — replay.

Neither was weakened in the move and neither compares a value against itself:
each leg's bytes are recovered out of *that leg's own* carrier and each leg's
record is built from *that leg's own* recovered product, by
``legs/deterministic.drive_leg``. The mutation probe that establishes this is
recorded in the plan's summary.

The live legs' assertions are deliberately **not** here. They live in
``run.py``'s ``_live`` because the live legs are excluded from ``make ci``
(D-11/D-12), so moving them to ``pytest`` would move them somewhere nothing
runs them.

Provenance of every relocated line
----------------------------------

===========================================  ==========================
pre-rewrite ``run.py`` line                   relocated to
===========================================  ==========================
:225 exactly one agent definition document    :func:`test_exactly_one_agent_definition_is_shared_by_every_leg`
:401 ``isinstance(gated, ServableProduct)``   the spine itself (a refusal
                                              now raises rather than being
                                              asserted away) **and**
                                              :func:`test_the_product_passed_all_three_gates`
:404 ``entity_count``                         :func:`test_the_served_payload_matches_the_declared_expectation`
:405 entity classes                           :func:`test_the_served_payload_matches_the_declared_expectation`
:504 three distinct harness ids               :func:`test_three_distinct_harnesses_actually_ran`
:519 one distinct product-byte value          :func:`test_the_same_context_product_reached_every_harness`
:522 equal to ``canonical_bytes(consumed)``   :func:`test_the_same_context_product_reached_every_harness`
:527 one governed emission address             :func:`test_every_effect_left_through_one_governed_emission`
:531-539 governed fields equal field by field :func:`test_the_governed_replay_fields_are_equal_across_harnesses`
:543 three distinct harness traces             :func:`test_harness_attribution_stays_isolated_and_per_harness`
:546 ``harness_trace`` not governed            :func:`test_harness_attribution_stays_isolated_and_per_harness`
:550 five dimensions per record                :func:`test_every_record_carries_all_five_dimensions`
:553-571 the six printed summary lines         covered by the tests above
===========================================  ==========================

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

* **Independent expectations.** ``expected.yaml`` declares what the *served
  product* should contain and how many harness legs this deployment stands up.
  Nothing in the pipeline derives those from that file, so changing either side
  alone makes the assertion fail.
* **Propagation checks.** The perspective role, the product's schema name and
  its required operator set are read from an artifact by ``run.py`` *and* by
  this module, so the artifact is a single source and editing it moves both
  ends together. These fail on a **wiring** fault, not on an artifact edit.
* **Cross-leg equivalence.** The two inherited assertions above are neither:
  each leg produces its own value through its own adapter, and the assertion is
  that three independently produced values agree. This is the category the
  example exists for.

Every domain expectation is read from an artifact, never inlined — a value this
module authored would be the test agreeing with itself (CINV-01 reaches
``tests/`` under D-IMPL-78).

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration

pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/03-harness-portability; retired usage model, non-gating
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "03-harness-portability"
EXAMPLE = EXAMPLE_DIR / "run.py"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.
    """
    name = "harness_portability_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One deterministic drive of all three legs, shared across the module.

    Module-scoped deliberately: the drive is the unit under test, and running
    it once per assertion would say nothing extra while paying for a full boot
    and three harness sessions each time.
    """
    root = tmp_path_factory.mktemp("harness-portability")
    return _load_example().drive_deterministic(root=root)


def _governed_fields(record: Any) -> dict[str, bytes]:
    """The D-18 governed field set, from the example's own leg module.

    Imported through the example's ``sys.path`` entry rather than re-derived:
    a second definition of "which fields are governed" would let this module
    and the example disagree about what the equivalence claim covers.
    """
    sys.path.insert(0, str(EXAMPLE_DIR))
    from legs.deterministic import governed_fields

    return governed_fields(record)


def _dimension_count(record: Any) -> int:
    sys.path.insert(0, str(EXAMPLE_DIR))
    from legs.deterministic import dimension_count

    return int(dimension_count(record))


def _declaration(result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key."""
    artifact = result.bundle.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


# --- the one agent definition ----------------------------------------------


def test_exactly_one_agent_definition_is_shared_by_every_leg() -> None:
    """Pre-rewrite :225, strengthened.

    "Portable" means *one* definition under many harnesses. Two definition
    documents would let a leg quietly bind a different agent and every
    equivalence assertion below would still pass — about the wrong thing.

    The pre-rewrite check counted files in ``artifacts/agents/``, which stopped
    meaning anything once that directory gained the agent's referenced
    artifacts. This counts documents *that the agent-definition contract
    accepts*, over the whole artifact tree — so it is about definitions rather
    than about a directory listing, and a second definition dropped anywhere
    under ``artifacts/`` fails it.
    """
    from ccf.agents.definitions import AGENT_DEFINITION
    from ccf.controlplane.artifacts import ArtifactLoadError, load_artifact

    definitions = []
    for path in sorted((EXAMPLE_DIR / "artifacts").rglob("*.yaml")):
        try:
            load_artifact(path.read_text(encoding="utf-8"), AGENT_DEFINITION)
        except ArtifactLoadError:
            continue
        definitions.append(path.name)
    assert definitions == ["agent-definition.yaml"], definitions


def test_the_agent_definition_names_no_harness(result: Any) -> None:
    """CLAUDE.md §6.5, asserted rather than assumed.

    An agent is harness-neutral *by construction* because it is an artifact
    that names no harness. This reads the canonical bytes of the definition the
    factory actually constructed from and checks that no harness id the drive
    stood up appears in them.
    """
    definition_bytes = canonical_bytes(result.bundle.definition)
    for run in result.runs:
        assert run.harness_id.encode() not in definition_bytes, run.harness_id


# --- the gates and the served product ---------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :401. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran."""
    assert result.bundle.product is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """What the product claims ran is exactly what the engine resolved
    (INV-CH7-47)."""
    assert (
        result.bundle.product.lineage.operators_invoked
        == result.bundle.operators_invoked
    )


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """The set the product class DECLARED it requires is exactly the set the
    engine RESOLVED.

    Honest about what this proves, updated for design E2 (D-IMPL-86 and its
    correction of 2026-08-05): ``operators_invoked`` is planned from the plan's
    ``required_operators()``, which is now ``projection-requirements.yaml``'s
    ``required_operator_keys`` rather than the product class's — so the two
    ends are no longer the same authored value, and editing *either* document
    alone now moves only one of them. What makes that edit fail is
    ``refuse_operator_set_divergence``, called in ``run.py`` between plan
    construction and ``ProjectionEngine.execute``; this assertion is the
    downstream witness that the run got as far as executing the plan the two
    bound documents describe. What it still DOES catch on its own is the
    ``operators.keys()`` shortcut being re-introduced while the artifacts
    declare a different set, which is the regression that made Gate 2
    tautological before the rewrite.
    """
    declared = result.bundle.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(
        result.bundle.operators_invoked
    )


def test_the_run_serves_the_class_the_artifacts_name(result: Any) -> None:
    declared = result.bundle.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert result.bundle.product.schema_name == declared.schema_name
    assert result.bundle.product.schema_version == declared.schema_version
    assert result.bundle.product.tenant_id == result.bundle.tenant_id


def test_the_served_payload_matches_the_declared_expectation(
    result: Any,
) -> None:
    """Pre-rewrite :404 and :405.

    Every expected value comes from ``expected.yaml``. Together they say that
    policy substituted the RESTRICTED catalog item out along with the edge that
    would have leaked it by absence, and that similarity ranked the second
    order out — so this fails if any of the four operators stops working.
    """
    expected = _declaration(result, "expected")
    payload = result.bundle.product.payload

    assert payload["entity_count"] == expected["entity_count"], payload
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == sorted(
        expected["entity_classes"]
    ), payload
    assert payload["relationship_types"] == sorted(
        expected["relationship_types"]
    ), payload


# --- the harness-neutrality proof -------------------------------------------


def test_three_distinct_harnesses_actually_ran(result: Any) -> None:
    """Pre-rewrite :504, against the declared leg count.

    The vacuity guard for everything below it. "All legs agree" is trivially
    true of one leg, so the count this deployment declares in ``expected.yaml``
    is asserted first and the equivalence assertions inherit a non-vacuous
    population from it.
    """
    expected = _declaration(result, "expected")
    harness_ids = {run.harness_id for run in result.runs}
    assert len(harness_ids) == expected["harness_leg_count"], harness_ids


def test_the_same_context_product_reached_every_harness(result: Any) -> None:
    """**Inherited from pre-rewrite :519-522 — half of the portability proof.**

    Context Product *consumption* is equivalent across harnesses: the bytes
    recovered out of each adapter's own harness-native carrier are identical to
    each other, and identical to what the fabric admitted through
    ``agent.consume`` — so no adapter reshaped, truncated, or re-serialized the
    product on the way in.

    Each leg's value is produced independently by ``drive_leg``, which recovers
    the product from the carrier that leg's ``inject_context`` built. Nothing
    is copied between legs, so this can fail.
    """
    delivered = {run.harness_id: run.product_bytes for run in result.runs}
    assert len(set(delivered.values())) == 1, {
        name: len(value) for name, value in delivered.items()
    }
    assert set(delivered.values()) == {canonical_bytes(result.bundle.consumed)}


def test_the_governed_replay_fields_are_equal_across_harnesses(
    result: Any,
) -> None:
    """**Inherited from pre-rewrite :531-539 — the other half of the proof.**

    The *replay records* are equivalent across harnesses, field by field over
    everything D-18 governs. Each record is built by ``build_record`` from the
    product recovered out of *that leg's own* carrier, so dimension 5's content
    address moves if an adapter corrupted what it delivered — which is why this
    is a check on the adapters rather than a restatement of one shared record.

    The divergence message names the field and both harnesses: a bare "the
    records differ" is not actionable for a claim this load-bearing.
    """
    reference, *others = result.runs
    expected_fields = _governed_fields(reference.record)
    assert expected_fields, "the governed field set is empty"
    for run in others:
        actual = _governed_fields(run.record)
        assert set(actual) == set(expected_fields)
        for name in sorted(expected_fields):
            assert actual[name] == expected_fields[name], (
                f"governed replay field {name!r} diverged between"
                f" {reference.harness_id} and {run.harness_id}"
            )


def test_every_effect_left_through_one_governed_emission(result: Any) -> None:
    """Pre-rewrite :527. The governed emission is one effect, whichever harness
    drove it — no harness acquires a private path out (CLAUDE.md §7.3 seam 3)."""
    assert len({run.emission_address for run in result.runs}) == 1


def test_harness_attribution_stays_isolated_and_per_harness(
    result: Any,
) -> None:
    """Pre-rewrite :543 and :546.

    The complement of the equivalence claim, and it is what stops that claim
    being vacuous: the three harness traces are *distinct*, so the legs really
    did report different things, and ``harness_trace`` is *absent* from the
    governed field set, so harness-reported attribution never contaminates what
    CCF governs.
    """
    traces = {canonical_bytes(run.trace) for run in result.runs}
    assert len(traces) == len(result.runs), "the harness traces collapsed"
    for run in result.runs:
        assert "harness_trace" not in _governed_fields(run.record)


def test_every_record_carries_all_five_dimensions(result: Any) -> None:
    """Pre-rewrite :550 (whitepaper §7.10.1, INV-CH7-80)."""
    for run in result.runs:
        assert _dimension_count(run.record) == 5, run.harness_id


def test_the_no_model_guard_does_not_outlive_the_drive(result: Any) -> None:
    """The guard is scoped, and this is why it has to be.

    ``install_no_model_guard`` patches ``socket.socket.connect`` and
    ``socket.create_connection`` — process-global names. Under
    ``make example-03`` that was harmless: the process existed to run one
    drive. Under ``pytest`` it is not, because every later test in the session
    shares the process, and an unrestored patch makes them fail somewhere
    unrelated to the cause.

    ``result`` is requested so the drive has already run when this executes.
    """
    import socket

    assert socket.create_connection.__name__ != "refuse"
    assert socket.socket.connect.__name__ != "refuse"


# --- the relocation itself, as a standing guard ------------------------------


def test_no_assertion_survives_on_the_path_ci_actually_runs() -> None:
    """D-09, made machine-checkable rather than reviewed once.

    The plan's acceptance criterion asks for zero ``assert`` in ``run.py``.
    That is exactly right for the deterministic path and exactly wrong for the
    live one: the live legs are excluded from ``make ci`` (D-11/D-12), so
    relocating *their* assertions to ``pytest`` would move them somewhere
    nothing runs them — the opposite of D-09's reason for the move. So the
    check is scoped to what it is actually about: every remaining ``assert``
    statement in ``run.py`` must live inside ``_live``.

    Without this, an assertion could drift back onto the deterministic path
    and pass under ``make example-03`` while being invisible to ``pytest`` —
    which is the state D-09 exists to end.
    """
    import ast

    tree = ast.parse(EXAMPLE.read_text(encoding="utf-8"))
    live = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_live"
    )
    live_lines = {
        node.lineno
        for node in ast.walk(live)
        if isinstance(node, ast.Assert)
    }
    stray = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Assert) and node.lineno not in live_lines
    ]
    assert not stray, (
        "assert statements outside `_live` in run.py, on the path `make ci`"
        f" runs, at lines {stray} — relocate them to this module"
    )
