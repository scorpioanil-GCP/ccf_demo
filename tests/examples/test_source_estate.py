"""The KYC/UBO source estate says what the adoption argument needs it to say.

`16-RESEARCH.md` FINDING F-1 measured that the shipped FIBO dataset cannot
answer *"Who ultimately owns Acme?"*: ``ownershipPercent`` is an attribute of
the **Party entity** rather than of the ownership relationship, and every
``hasOwnershipInterestIn`` edge runs Party → Corporation in exactly one hop.
Phase 16 CONTEXT D-03's stated teaching property (multi-hop ownership chains)
and D-10's worked demonstration (aggregating percentages across hops) are both
unanswerable on that data.

Plan 16-02 extends the estate. This module is what says the extension actually
carries the properties the extension exists for — and it states them against
the **generated estate**, not against the declaration, so a generator that
dropped or mangled a record fails here rather than passing on the strength of
what the artifact says about itself.

Every domain value this module needs — which type is a natural person, which
relation is ownership, which entity the UBO question is about, what the
regulatory threshold is — is read from the artifact's ``teaching_properties``
and ``field_roles`` blocks. None is written here as a constant.
``tools/lints``' ``RULE_TREE_SCOPE`` covers ``tests`` as well as ``src``,
``runtime`` and ``examples``, so a threshold written into a test module is the
same No-Hardcoding violation as one written into a library module
(CLAUDE.md §6.4).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import sys
from collections.abc import Iterator, Mapping, Sequence
from decimal import Decimal
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:  # the tools/ package is not installed
    sys.path.insert(0, str(REPO_ROOT))

from tools.lints import (  # noqa: E402
    imported_module_names,
    submodule_import_names,
)

EXAMPLE_DIR = REPO_ROOT / "examples" / "s1-01-hello-context-product"
GENERATOR_PATH = EXAMPLE_DIR / "source_estate.py"
ARTIFACT_PATH = EXAMPLE_DIR / "artifacts" / "source-estate.yaml"

#: The packages a *source-system* generator must never reach. `ccf.graph` is
#: L3 itself, `ccf.boot` mints the single-writer token, and `ccf.deployment`
#: is the assembled front door onto both. These are SDK module names —
#: mechanism, not domain vocabulary — and the deny list is stated here rather
#: than inferred so the single-writer claim (CLAUDE.md §10; INV-CH7-10 /
#: CINV-02) is checkable at a glance.
DENIED_PACKAGES = ("ccf.graph", "ccf.boot", "ccf.deployment")

#: What each output file is, by declared format. The JSONL streams are what the
#: four out-of-tree FIBO loaders read.
JSONL_SUFFIX = ".jsonl"

HUNDRED = Decimal(100)


# ---------------------------------------------------------------------------
# Loading.
# ---------------------------------------------------------------------------


def _load_generator() -> Any:
    """Load the example's generator module from its file path.

    ``s1-01-hello-context-product`` is not an importable package name; the
    examples suite loads example modules by path, and registers the module in
    ``sys.modules`` before executing it so annotations resolve.
    """
    name = "source_estate_under_test"
    spec = importlib.util.spec_from_file_location(name, GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator() -> Any:
    return _load_generator()


@pytest.fixture(scope="module")
def declaration(generator: Any) -> Mapping[str, Any]:
    return generator.load_declaration()


@pytest.fixture(scope="module")
def estate(
    generator: Any,
    declaration: Mapping[str, Any],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    """One materialisation of the estate, shared across the module."""
    root = tmp_path_factory.mktemp("source-estate")
    manifest = generator.generate(declaration, root)
    return {"root": root, "manifest": manifest}


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def streams(estate: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Every generated JSONL stream, keyed by its file stem."""
    root: pathlib.Path = estate["root"]
    return {
        path.stem: _read_jsonl(path)
        for path in sorted(root.glob(f"*{JSONL_SUFFIX}"))
    }


@pytest.fixture(scope="module")
def roles(declaration: Mapping[str, Any]) -> Mapping[str, str]:
    return declaration["field_roles"]


@pytest.fixture(scope="module")
def teaching(declaration: Mapping[str, Any]) -> Mapping[str, Any]:
    return declaration["teaching_properties"]


@pytest.fixture(scope="module")
def entities(
    streams: Mapping[str, list[dict[str, Any]]], declaration: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return _stream_named(streams, declaration, "entities")


@pytest.fixture(scope="module")
def relationships(
    streams: Mapping[str, list[dict[str, Any]]], declaration: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return _stream_named(streams, declaration, "relationships")


def _stream_named(
    streams: Mapping[str, list[dict[str, Any]]],
    declaration: Mapping[str, Any],
    stream: str,
) -> list[dict[str, Any]]:
    """The generated rows for one declared stream, located by its output path."""
    for output in declaration["outputs"]:
        if output.get("stream") == stream and output.get("format") == "jsonl":
            return streams[pathlib.Path(output["path"]).stem]
    raise LookupError(stream)


# ---------------------------------------------------------------------------
# Graph walking over the GENERATED estate.
# ---------------------------------------------------------------------------


def _ownership_edges(
    relationships: Sequence[Mapping[str, Any]],
    roles: Mapping[str, str],
    teaching: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    kind = teaching["ownership_relationship_type"]
    return [
        edge
        for edge in relationships
        if edge.get(roles["relationship_type"]) == kind
    ]


def _by_source(
    edges: Sequence[Mapping[str, Any]], roles: Mapping[str, str]
) -> dict[str, list[Mapping[str, Any]]]:
    index: dict[str, list[Mapping[str, Any]]] = {}
    for edge in edges:
        index.setdefault(edge[roles["relationship_source_entity"]], []).append(edge)
    return index


def _paths(
    index: Mapping[str, list[Mapping[str, Any]]],
    roles: Mapping[str, str],
    start: str,
    target: str,
    visited: frozenset[str],
) -> Iterator[list[Mapping[str, Any]]]:
    """Every simple ownership path from ``start`` to ``target``.

    The ownership edges form a DAG, so ``visited`` is belt-and-braces rather
    than the thing under test — but a cycle introduced by a later edit should
    make this terminate, not hang.
    """
    for edge in index.get(start, ()):
        nxt = edge[roles["relationship_target_entity"]]
        if nxt in visited:
            continue
        if nxt == target:
            yield [edge]
            continue
        for rest in _paths(index, roles, nxt, target, visited | {nxt}):
            yield [edge, *rest]


def _fraction(edge: Mapping[str, Any], roles: Mapping[str, str]) -> Decimal:
    return Decimal(str(edge[roles["relationship_ownership_percent"]])) / HUNDRED


def _aggregate_percent(
    paths: Sequence[Sequence[Mapping[str, Any]]], roles: Mapping[str, str]
) -> Decimal:
    """Sum, over every path, of the product of that path's hop fractions."""
    total = Decimal(0)
    for path in paths:
        product = Decimal(1)
        for edge in path:
            product *= _fraction(edge, roles)
        total += product
    return total * HUNDRED


def _labels(
    entities: Sequence[Mapping[str, Any]], roles: Mapping[str, str]
) -> dict[str, str]:
    return {
        entity[roles["entity_id"]]: entity.get(roles["entity_label"], "")
        for entity in entities
    }


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_declared_estate_and_its_interpreter_are_both_present() -> None:
    """Neither half of the code-and-artifacts pair may be missing."""
    assert ARTIFACT_PATH.is_file(), f"missing declared estate: {ARTIFACT_PATH}"
    assert GENERATOR_PATH.is_file(), f"missing interpreter: {GENERATOR_PATH}"


def test_the_generator_produced_a_non_empty_estate(
    estate: dict[str, Any],
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> None:
    """Every assertion below walks these rows; empty rows make them all vacuous."""
    assert estate["manifest"]["files"], "the generator wrote no files"
    assert entities, "the generated entity stream is empty"
    assert relationships, "the generated relationship stream is empty"
    for name, count in estate["manifest"]["counts"].items():
        assert count, f"declared stream {name!r} materialised no rows"


# ---------------------------------------------------------------------------
# The properties the adoption argument rests on.
# ---------------------------------------------------------------------------


def test_an_ownership_chain_of_depth_two_exists(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    roles: Mapping[str, str],
    teaching: Mapping[str, Any],
) -> None:
    """A natural person reaches the subject only by traversing intermediates.

    This is the property FINDING F-1 found absent: every shipped ownership
    edge ran Party → Corporation in one hop, so there was no chain to walk.
    """
    index = _by_source(_ownership_edges(relationships, roles, teaching), roles)
    start = teaching["deep_chain_demonstrator"]
    subject = teaching["ultimate_owner_subject"]
    minimum = int(teaching["minimum_chain_depth"])
    labels = _labels(entities, roles)

    paths = sorted(
        _paths(index, roles, start, subject, frozenset({start})), key=len
    )
    assert paths, (
        f"no ownership path at all from {labels.get(start, start)!r} to"
        f" {labels.get(subject, subject)!r}"
    )
    shortest = paths[0]
    intermediates = [
        labels.get(
            edge[roles["relationship_target_entity"]],
            edge[roles["relationship_target_entity"]],
        )
        for edge in shortest[:-1]
    ]
    assert len(shortest) >= minimum, (
        f"the shortest ownership path from {labels.get(start, start)!r} to"
        f" {labels.get(subject, subject)!r} is {len(shortest)} hop(s) through"
        f" {intermediates}; a chain shorter than {minimum} hops is answerable"
        " by lookup and demonstrates nothing about traversal"
    )


def test_every_ownership_edge_carries_its_own_percentage(
    relationships: list[dict[str, Any]],
    roles: Mapping[str, str],
    teaching: Mapping[str, Any],
) -> None:
    """The F-1 remedy: the percentage belongs to the edge, not to the party.

    A party carries one percentage regardless of how many interests it holds,
    so an entity-level field cannot attribute a fraction per edge — and a
    chain whose hops carry no fraction cannot be aggregated at all.
    """
    key = roles["relationship_ownership_percent"]
    edges = _ownership_edges(relationships, roles, teaching)
    missing = sorted(
        str(edge.get(roles["relationship_id"]))
        for edge in edges
        if edge.get(key) is None
    )
    assert edges, "no ownership edges in the generated estate"
    assert not missing, (
        f"ownership edges with no `{key}` of their own: {missing}."
        " Their percentage would have to come from the party record, which"
        " is exactly what FINDING F-1 showed cannot work"
    )


def test_the_ultimate_beneficial_owner_requires_aggregation(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    roles: Mapping[str, str],
    teaching: Mapping[str, Any],
) -> None:
    """The assertion the adoption argument rests on.

    A vector store over chunked documents can retrieve the direct holding,
    because some passage states it. It structurally cannot produce the
    aggregate, because no passage states it — the number exists only in the
    relationships. If this test fails, the adoption-argument page is claiming
    something the data no longer demonstrates.
    """
    edges = _ownership_edges(relationships, roles, teaching)
    index = _by_source(edges, roles)
    person = teaching["aggregation_demonstrator"]
    subject = teaching["ultimate_owner_subject"]
    threshold = Decimal(str(teaching["beneficial_ownership_threshold_percent"]))
    labels = _labels(entities, roles)
    who = labels.get(person, person)
    what = labels.get(subject, subject)

    direct = [
        [edge]
        for edge in index.get(person, ())
        if edge[roles["relationship_target_entity"]] == subject
    ]
    every = list(_paths(index, roles, person, subject, frozenset({person})))
    direct_percent = _aggregate_percent(direct, roles)
    aggregate_percent = _aggregate_percent(every, roles)

    assert len(every) > len(direct), (
        f"{who!r} reaches {what!r} only directly, so aggregation has nothing"
        " to add and the demonstration is vacuous"
    )
    assert aggregate_percent != direct_percent, (
        f"{who!r} aggregates to the same {aggregate_percent} as the direct"
        f" edge alone; traversal changes no answer"
    )
    assert direct_percent < threshold, (
        f"{who!r} already holds {direct_percent} of {what!r} on the direct"
        f" edge, above the {threshold} threshold — the threshold is then"
        " answerable without traversing anything"
    )
    assert aggregate_percent >= threshold, (
        f"{who!r} aggregates to {aggregate_percent} of {what!r}, which does"
        f" not reach the {threshold} threshold; nothing crosses it under"
        " aggregation and the worked demonstration has no result"
    )


def test_the_boundary_case_percentage_is_frozen(
    entities: list[dict[str, Any]],
    roles: Mapping[str, str],
    teaching: Mapping[str, Any],
) -> None:
    """The party sitting exactly on the regulatory threshold stays there.

    A threshold nobody sits exactly on is a threshold no example can show the
    sense of, which is why this value is pinned rather than merely present.
    """
    boundary = teaching["fixed_boundary_case"]
    wanted = str(boundary["ownership_percent"])
    found = {
        entity[roles["entity_id"]]: entity.get(roles["entity_ownership_percent"])
        for entity in entities
    }
    subject = boundary["entity"]
    assert subject in found, f"the boundary-case entity {subject} is gone"
    assert str(found[subject]) == wanted, (
        f"the boundary case moved from {wanted} to {found[subject]}"
    )


def test_both_planted_near_duplicate_pairs_survive(
    entities: list[dict[str, Any]],
    roles: Mapping[str, str],
    teaching: Mapping[str, Any],
) -> None:
    """The near-duplicates are what make the Similarity axis non-trivial here."""
    present = {entity[roles["entity_id"]] for entity in entities}
    missing = sorted(
        member
        for pair in teaching["near_duplicate_pairs"]
        for member in pair
        if member not in present
    )
    assert teaching["near_duplicate_pairs"], "no near-duplicate pair declared"
    assert not missing, f"planted near-duplicates lost from the estate: {missing}"


# ---------------------------------------------------------------------------
# Mechanism: determinism, single-writer, and the No-Hardcoding Rule.
# ---------------------------------------------------------------------------


def test_the_generator_is_deterministic(
    generator: Any,
    declaration: Mapping[str, Any],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Two independent runs write byte-identical files.

    This is what lets plan 16-07's backend matrix compare a content hash
    across substrates: a difference there then means the substrate differed,
    not that the estate did.
    """
    first = tmp_path_factory.mktemp("estate-a")
    second = tmp_path_factory.mktemp("estate-b")
    left = generator.generate(declaration, first)
    right = generator.generate(declaration, second)

    assert left["checksums"] == right["checksums"]
    assert sorted(left["files"]) == sorted(right["files"])
    for name in sorted(left["files"]):
        assert (first / name).read_bytes() == (second / name).read_bytes(), (
            f"{name} differs between two runs of the same declaration; the"
            " generator is reading a clock or an unseeded source"
        )


def test_the_generator_never_touches_the_context_graph() -> None:
    """Single-writer, stated statically (CLAUDE.md §10; INV-CH7-10 / CINV-02).

    Uses both ``imported_module_names`` and ``submodule_import_names``, which
    is the CR-02 hole: the first reports ``ccf.graph`` for
    ``from ccf.graph import _writer`` and cannot tell a submodule from an
    attribute, so a rule that denies a specific module needs both.
    """
    tree = ast.parse(GENERATOR_PATH.read_text(encoding="utf-8"))
    reached: set[str] = set()
    for node in ast.walk(tree):
        reached.update(imported_module_names(node))
        reached.update(submodule_import_names(node))
    forbidden = sorted(
        name
        for name in reached
        for package in DENIED_PACKAGES
        if name == package or name.startswith(f"{package}.")
    )
    assert not forbidden, (
        f"`{GENERATOR_PATH.name}` reaches {forbidden}. It writes an enterprise"
        " source estate, and rows enter CCF's graph only through L2 ingress"
    )


def test_the_generator_refuses_to_run_without_its_artifact(
    tmp_path: pathlib.Path,
) -> None:
    """C-2: an example whose code still runs meaningfully without its artifacts
    has violated the No-Hardcoding Rule (CLAUDE.md §6.4).

    The interpreter is copied into a directory with an empty ``artifacts/``
    tree — the artifact deleted, in other words — and loaded from there, so
    its own default path resolves to the absent document.
    """
    copied = tmp_path / EXAMPLE_DIR.name
    (copied / "artifacts").mkdir(parents=True)
    (copied / GENERATOR_PATH.name).write_bytes(GENERATOR_PATH.read_bytes())

    name = "source_estate_without_its_artifact"
    spec = importlib.util.spec_from_file_location(
        name, copied / GENERATOR_PATH.name
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        with pytest.raises(module.SourceEstateError):
            module.load_declaration()
        with pytest.raises(module.SourceEstateError):
            module.generate({}, tmp_path / "out")
    finally:
        del sys.modules[name]
