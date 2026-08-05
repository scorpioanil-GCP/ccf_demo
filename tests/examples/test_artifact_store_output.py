"""The ArtifactStore pluggability proof's assertions, under `pytest` (D-09).

``examples/07-artifact-store-mcp/run.py`` used to carry its own guarantee: the
``assert`` statements and ``print`` summaries of ``main()``, checked by
``make example-07`` exiting zero. D-09 moves that guarantee here, because
``make examples`` proves a spine *runs* and ``pytest`` proves it is *correct*.

**The claim being defended.** CLAUDE.md §7.4 and §9's eighth example commit the
SDK to this: swap the file-backed ArtifactStore for the MCP-backed reference
store and *nothing else in the deployment changes*. "Nothing else changed" is
the exact shape of claim that passes because a test never looked, so this
module checks it in two independent directions:

* **Structurally**, from the source — :func:`test_the_workload_takes_exactly_one_per_run_input`
  and :func:`test_no_manifest_field_names_an_artifact_store` assert that there
  is *no way* for the two runs to differ in anything but the store binding.
  These read the example's own text, so they fail if a future edit reintroduces
  a second per-run parameter or moves the store into the manifest.
* **Observationally**, from the two runs — the product bytes, the artifact
  roles, the versioned URIs, and the content addresses all agree, and every URI
  the MCP run recorded resolves against a *fresh* client at its exact version.

Neither direction is sufficient alone. The structural checks would pass over a
workload that ignored its inputs; the observational ones would pass over two
runs that differed in ten ways that happened not to move the bytes.

Provenance of every relocated line
----------------------------------

===========================================  ==========================
pre-rewrite ``run.py`` line                   relocated to
===========================================  ==========================
:394 ``isinstance(gated, ServableProduct)``   the spine itself (a refusal
                                              now raises) **and**
                                              :func:`test_the_product_passed_all_three_gates`
:398 ``entity_count``                         :func:`test_the_served_payload_matches_the_declared_expectation`
:399 entity classes                           :func:`test_the_served_payload_matches_the_declared_expectation`
:402 relationship types                       :func:`test_the_served_payload_matches_the_declared_expectation`
:506/:508 the child's READY handshake         the spine itself (a missing
                                              handshake now raises)
:524 ``mcp_bytes == file_bytes``              :func:`test_the_served_product_is_byte_identical_across_the_two_stores`
:528 the ref role sets agree                  :func:`test_the_same_artifact_roles_landed_on_both_stores`
:531 the URIs agree                           :func:`test_the_same_artifacts_landed_at_the_same_exact_versions`
:532 the content addresses agree              :func:`test_the_same_artifacts_landed_at_the_same_exact_versions`
:540 fresh-client URI resolution               :func:`test_every_recorded_uri_resolves_on_a_fresh_client_at_its_exact_version`
:541 fresh-client presence                     :func:`test_every_recorded_uri_resolves_on_a_fresh_client_at_its_exact_version`
:547 round-tripped bytes equal file run        :func:`test_every_recorded_uri_resolves_on_a_fresh_client_at_its_exact_version`
:550-555 the six printed summary lines         covered by the tests above
===========================================  ==========================

Every domain expectation is read from an artifact, never inlined — a value this
module authored would be the test agreeing with itself (CINV-01 reaches
``tests/`` under D-IMPL-78).

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys
from contextlib import ExitStack
from typing import Any

import pytest
import yaml

from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.products.contract import ContextProductContract

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "07-artifact-store-mcp"
EXAMPLE = EXAMPLE_DIR / "run.py"
MANIFEST = EXAMPLE_DIR / "artifacts" / "manifest.yaml"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.
    """
    name = "artifact_store_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def swap(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Both store-backed runs, captured while the MCP child is still up.

    ``run`` calls its observer *inside* the child's lifetime, so the fresh
    client assertion below has a live server to resolve against. The observer
    stashes the pair and the module-scoped fixture yields it — but note that
    only the assertions run inside :func:`_with_fresh_mcp_store` can touch the
    server, and that helper is called during the run, not after it.
    """
    root = tmp_path_factory.mktemp("artifact-store")
    module = _load_example()

    captured: dict[str, Any] = {}

    def observe(result: Any) -> None:
        captured["result"] = result
        with ExitStack() as stack:
            fresh = result.mcp_store_factory(stack)
            captured["fresh_resolution"] = {
                role: (
                    fresh.resolve_uri(uri=ref.uri),
                    fresh.exists(content_address=ref.content_address),
                    fresh.get(content_address=ref.content_address)
                    if role == "product"
                    else None,
                )
                for role, ref in result.over_mcp.refs.items()
            }

    module.run(root=root, observe=observe)
    return captured


@pytest.fixture(scope="module")
def result(swap: Any) -> Any:
    return swap["result"]


def _declaration(run_result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key."""
    artifact = run_result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


# --- "nothing else changes", checked structurally ---------------------------


def test_the_workload_takes_exactly_one_per_run_input() -> None:
    """The claim's structural form: there is nothing else that *could* differ.

    ``workload`` is called twice and the example's whole demonstration is that
    only the store binding varies between those calls. A second parameter would
    be a second thing that could vary, so this reads the example's own AST and
    refuses one.

    This is deliberately a source check rather than a behavioural one: a
    behavioural test cannot distinguish "the two runs were identical" from "the
    two runs differed in ways that did not move the bytes".
    """
    tree = ast.parse(EXAMPLE.read_text(encoding="utf-8"))
    workload = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "workload"
    )
    args = workload.args
    names = [argument.arg for argument in args.posonlyargs + args.args + args.kwonlyargs]
    assert names == ["store_config"], names
    assert args.vararg is None and args.kwarg is None
    assert not args.defaults and not args.kw_defaults


def test_no_manifest_field_names_an_artifact_store() -> None:
    """The store stays a call-site binding, never Control Plane state.

    D-08's reasoning, applied to substrates: a store named in a registered,
    content-hashed artifact would land in Decision Replay dimension 2, and the
    example's two runs would then genuinely differ in *what was in force* —
    which is the opposite of what the example demonstrates.

    Checked over the whole manifest document, keys and values, so a store named
    under any spelling fails rather than only the one this test anticipated.
    """
    document = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    def walk(node: Any) -> list[str]:
        if isinstance(node, dict):
            return [
                text
                for key, value in node.items()
                for text in [str(key), *walk(value)]
            ]
        if isinstance(node, list):
            return [text for item in node for text in walk(item)]
        return [str(node)]

    offenders = [text for text in walk(document) if "store" in text.lower()]
    assert not offenders, offenders

    # The walk is over the PARSED document, so comments are out of scope by
    # construction — and correctly so: a comment configures nothing. The
    # manifest's prose does discuss the store, at length, to say why it is
    # absent.
    assert walk(document), "the manifest parsed to nothing"


def test_both_runs_booted_from_the_same_manifest(result: Any) -> None:
    """The Control Plane artifacts in force are the same set, key for key.

    ``booted.artifacts`` is what the manifest produced, so equal key sets and
    equal parsed artifacts is the observational counterpart of the structural
    check above.
    """
    assert (
        result.over_file.artifacts.keys() == result.over_mcp.artifacts.keys()
    )
    for key in sorted(result.over_file.artifacts):
        assert result.over_file.artifacts[key] == result.over_mcp.artifacts[key], key


# --- the gates and the served product ---------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :394. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran."""
    assert result.over_file.product is not None
    assert result.over_mcp.product is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """What the product claims ran is exactly what the engine resolved
    (INV-CH7-47), on both runs."""
    for run_result in (result.over_file, result.over_mcp):
        assert (
            run_result.product.lineage.operators_invoked
            == run_result.operators_invoked
        )


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """The set the product class DECLARED is the set the engine RESOLVED.

    Honest about what this proves: ``operators_invoked`` is planned from the
    plan's ``required_operators()``, which is the artifact's
    ``required_operator_keys`` — so editing the artifact alone moves both ends
    and is not detected. What this DOES catch is the ``operators.keys()``
    shortcut being re-introduced while the artifact declares a different set,
    which is the regression that made Gate 2 tautological before the rewrite.
    """
    declared = result.over_file.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(
        result.over_file.operators_invoked
    )


def test_the_served_payload_matches_the_declared_expectation(
    result: Any,
) -> None:
    """Pre-rewrite :398, :399 and :402.

    Every expected value comes from ``expected.yaml``. Together they say that
    policy substituted the RESTRICTED bonded depot out along with the edge that
    would have leaked it by absence, and that similarity ranked the sea route
    out — so this fails if any of the four operators stops working.
    """
    expected = _declaration(result.over_file, "expected")
    payload = result.over_file.product.payload

    assert payload["entity_count"] == expected["entity_count"], payload
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == sorted(
        expected["entity_classes"]
    ), payload
    assert payload["relationship_types"] == sorted(
        expected["relationship_types"]
    ), payload


# --- the pluggability proof --------------------------------------------------


def test_the_served_product_is_byte_identical_across_the_two_stores(
    result: Any,
) -> None:
    """Pre-rewrite :524. The substrate is invisible to the fabric.

    Byte equality of the canonical serialization, not field-by-field
    similarity: a store that had round-tripped the product through its own
    representation would move the bytes even where every field still read the
    same.
    """
    assert result.over_mcp.product_bytes == result.over_file.product_bytes
    assert result.over_file.product_bytes, "the served product is empty"


def test_the_same_artifact_roles_landed_on_both_stores(result: Any) -> None:
    """Pre-rewrite :528, with its vacuity closed.

    Equal role sets is not enough on its own — two *empty* sets are equal — so
    the roles are also checked against the set this deployment declares in
    ``expected.yaml``. A run that quietly stopped persisting the Control Plane
    policy bundle would then fail rather than agree with itself about nothing.
    """
    expected = _declaration(result.over_file, "expected")
    assert result.over_mcp.refs.keys() == result.over_file.refs.keys()
    assert sorted(result.over_mcp.refs) == sorted(
        expected["persisted_artifact_roles"]
    )


def test_the_same_artifacts_landed_at_the_same_exact_versions(
    result: Any,
) -> None:
    """Pre-rewrite :531 and :532.

    Same versioned URI *and* same content address, per role. The URI is the
    naming index the store maintains; the address is the content hash. Both
    agreeing across two independent substrates is what "the same artifacts, at
    the same exact versions" means.
    """
    for role, over_mcp in result.over_mcp.refs.items():
        over_file = result.over_file.refs[role]
        assert over_mcp.uri == over_file.uri, role
        assert over_mcp.content_address == over_file.content_address, role


def test_every_recorded_uri_resolves_on_a_fresh_client_at_its_exact_version(
    swap: Any, result: Any
) -> None:
    """Pre-rewrite :540, :541 and :547.

    A *fresh* client, so the resolution comes off the server's own naming index
    rather than out of anything the writing client held; at the exact recorded
    address, so no "latest" was ever involved; and the product's bytes behind
    that address are byte-equal to what the file-backed run served.
    """
    resolution = swap["fresh_resolution"]
    assert resolution.keys() == result.over_mcp.refs.keys()
    for role, ref in result.over_mcp.refs.items():
        resolved_address, present, payload = resolution[role]
        assert resolved_address == ref.content_address, role
        assert present, role
        if role == "product":
            restored = ContextProductContract.model_validate_json(payload)
            assert restored == result.over_file.product


# --- the relocation itself, as a standing guard ------------------------------


def test_no_assertion_survives_in_the_example(swap: Any) -> None:
    """D-09, made machine-checkable rather than reviewed once.

    An assertion that drifted back into ``run.py`` would pass under
    ``make example-07`` while being invisible to ``pytest`` — and would vanish
    entirely under ``python -O``. Refusals in the spine raise instead.
    """
    tree = ast.parse(EXAMPLE.read_text(encoding="utf-8"))
    stray = [
        node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)
    ]
    assert not stray, f"assert statements in run.py at lines {stray}"
