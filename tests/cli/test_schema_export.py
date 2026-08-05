"""ERGO-12's committed schemas, as gates rather than as prose.

Three properties are asserted here, and they are deliberately different
kinds of assertion:

* **Freshness** — the committed ``docs/schemas/`` tree equals what the SDK
  artifact classes emit right now, on *bytes*, because the tree is reviewed
  as a diff and whitespace and key order are part of what makes that diff
  readable. Orphans and missing files count as drift too: the gate is over
  the set as much as over the bytes.
* **Vacuity** — there is at least one schema per entry in
  ``SDK_ARTIFACT_CLASSES``. A bytes-equality check over an empty tree
  passes trivially, so the count is asserted separately from the content.
* **Header correctness** — the ``$schema`` headers on example artifact
  documents name the class that *actually accepts* the document, resolve
  from the document's own directory, and agree with any deployment
  manifest that also declares the class. Existence of the target file is
  not the property worth gating: a header pointing at a real schema for the
  wrong class is exactly the failure this catches.

It lives under ``tests/`` — the already-always-on ``test`` job — so a
schema change fails CI on the same commit that causes it, with no new CI
wiring, the same arrangement ``tests/http_api/test_openapi.py`` uses for
the committed OpenAPI document.
"""

from __future__ import annotations

import json
import os
import pathlib

import pytest

from ccf.deployment.classes import SDK_ARTIFACT_CLASSES
from tools.check_schema_headers import (
    DEFERRED_PREFIX,
    HEADER_PREFIX,
    check_directory,
    check_document,
)

# The serialization recipe is stated ONCE, in ``tools/dump_schemas.py``, and
# imported here rather than restated, so the regenerator and this assertion
# cannot disagree about what "the schema" means.
from tools.dump_schemas import (
    CLASS_ID_KEY,
    DRIFT_MESSAGE,
    ENVELOPE_CLASS_ID,
    SCHEMAS_DIR,
    author_versioned_classes,
    differences,
    emit,
    serialize,
)

# Repo root from this file's own path, never ``Path.cwd()`` — pytest may be
# invoked from anywhere and the baseline is a fixed repo artifact.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_QUICKSTART_ARTIFACTS = _REPO_ROOT / "examples" / "00-quickstart" / "artifacts"


def test_every_sdk_artifact_class_has_a_committed_schema() -> None:
    """Vacuity: bytes-equality over an empty tree would pass trivially."""
    committed = sorted(SCHEMAS_DIR.glob("*.json"))
    assert len(committed) >= len(SDK_ARTIFACT_CLASSES), (
        f"{len(SDK_ARTIFACT_CLASSES)} artifact classes but"
        f" {len(committed)} committed schemas — run `make schemas`"
    )
    for class_id in SDK_ARTIFACT_CLASSES:
        assert (SCHEMAS_DIR / f"{class_id}.json").is_file(), class_id


def test_every_author_versioned_class_has_a_committed_schema() -> None:
    """The second committed set (plan 15-14), and its membership rule.

    An agent definition, a prompt artifact and a skill catalog entry are
    SDK-owned schemas an adopter authors by hand, so they need a ``$schema``
    target — but a manifest must not carry them, because ``load_and_boot``
    registers through ``register_typed`` and these classes need
    ``register_versioned``'s D-05 bump check. Hence: committed, not
    manifest-addressable.

    The membership rule is checked rather than trusted. Every member declares
    an ``artifact_version`` field (that IS what "author-versioned" means), and
    no member is manifest-addressable — so the set cannot quietly acquire a
    class that belongs in the other one.
    """
    author_versioned = author_versioned_classes()
    assert author_versioned, "the author-versioned set is empty"
    for class_id, artifact_class in author_versioned.items():
        assert "artifact_version" in artifact_class.contract.model_fields, class_id
        assert class_id not in SDK_ARTIFACT_CLASSES, class_id
        assert (SCHEMAS_DIR / f"{class_id}.json").is_file(), class_id


def test_an_envelope_header_over_an_author_versioned_class_fails(
    tmp_path: pathlib.Path,
) -> None:
    """The envelope must not become an escape hatch from these contracts either.

    Without this, an agent definition could annotate itself as
    deployment-authored — its ``class_id`` is absent from
    ``SDK_ARTIFACT_CLASSES``, which used to be the whole test — and have every
    constraint ``AgentDefinition`` declares go unchecked.
    """
    document = _envelope_document(
        tmp_path,
        "semver: '1.0.0'\nclass_id: ccf.agent-definition\ndeclaration:\n  a: 1\n",
    )
    problems = check_document(document)
    assert problems and "which the SDK owns" in problems[0], problems


def test_the_committed_schemas_match_what_the_classes_emit() -> None:
    """Freshness, asserted on bytes and over the whole set."""
    assert differences() == [], DRIFT_MESSAGE


@pytest.mark.parametrize("class_id", sorted(SDK_ARTIFACT_CLASSES))
def test_each_committed_schema_is_its_class_byte_for_byte(
    class_id: str,
) -> None:
    """Per-class, so a failure names the class rather than the tree."""
    expected = emit()[SCHEMAS_DIR / f"{class_id}.json"]
    committed = (SCHEMAS_DIR / f"{class_id}.json").read_text(encoding="utf-8")
    assert committed == expected, DRIFT_MESSAGE


def test_the_drift_message_names_the_regeneration_command() -> None:
    """Edge case: a failure nobody can act on is a failure that gets muted."""
    assert "make schemas" in DRIFT_MESSAGE
    assert "docs/schemas/" in DRIFT_MESSAGE


def test_an_orphan_schema_is_drift(tmp_path: pathlib.Path) -> None:
    """A schema for a class that no longer exists misinforms worse than a
    stale one: it claims a class exists that does not."""
    stray = SCHEMAS_DIR / "ccf.no-such-class.json"
    stray.write_text(serialize({CLASS_ID_KEY: "ccf.no-such-class"}), "utf-8")
    try:
        problems = differences()
        assert any("orphan" in problem for problem in problems), problems
    finally:
        stray.unlink()
    assert differences() == []


def test_every_committed_schema_is_annotated_with_its_class() -> None:
    """The link from file to class is a checkable claim, not a file name."""
    for class_id in SDK_ARTIFACT_CLASSES:
        document = json.loads(
            (SCHEMAS_DIR / f"{class_id}.json").read_text(encoding="utf-8")
        )
        assert document[CLASS_ID_KEY] == class_id


def test_every_quickstart_artifact_is_annotated_or_deferred() -> None:
    """No document falls through the gate silently.

    A document that is not yet a single typed artifact carries an explicit
    ``# ccf-schema: deferred(<plan>)`` marker naming the plan that closes
    it; everything else carries a header. A file with neither fails.
    """
    documents = sorted(_QUICKSTART_ARTIFACTS.glob("*.yaml"))
    assert documents, "no quickstart artifacts found"
    for path in documents:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith(HEADER_PREFIX) or first.startswith(
            DEFERRED_PREFIX
        ), path


def test_the_quickstart_headers_are_correct_not_merely_resolvable() -> None:
    """The full four-part check, over the day-1 example."""
    assert check_directory(_QUICKSTART_ARTIFACTS) == []


def test_a_header_naming_the_wrong_class_fails(
    tmp_path: pathlib.Path,
) -> None:
    """The check's own teeth: a header pointing at a real schema for a
    class that does not accept the document must fail.

    This is the property the check exists for. A weaker gate — "the path
    exists" — passes this document happily, which is why it is asserted
    here as a failure rather than assumed.
    """
    document = tmp_path / "wrong.yaml"
    target = SCHEMAS_DIR / "ccf.perspective.json"
    document.write_text(
        f"{HEADER_PREFIX}{os.path.relpath(target, tmp_path)}\n"
        "semver: 1.0.0\n"
        "tenant_id: t\n"
        "envelopes: []\n",
        encoding="utf-8",
    )
    problems = check_document(document.resolve())
    assert problems, "a wrong-class header passed the check"
    assert "does not accept this document" in problems[0], problems


def test_a_header_that_only_resolves_from_the_repo_root_fails(
    tmp_path: pathlib.Path,
) -> None:
    """Editors resolve ``$schema`` from the document's own directory."""
    document = tmp_path / "root-relative.yaml"
    document.write_text(
        f"{HEADER_PREFIX}docs/schemas/ccf.perspective.json\n"
        "principal_id: p\nrole: r\nsemver: 1.0.0\n",
        encoding="utf-8",
    )
    problems = check_document(document.resolve())
    assert problems, "a repo-root-relative header passed the check"
    assert "does not resolve" in problems[0], problems


def test_an_unannotated_document_fails(tmp_path: pathlib.Path) -> None:
    """Neither a header nor a deferral marker is a failure, not a pass."""
    document = tmp_path / "bare.yaml"
    document.write_text("# just a comment\nsemver: 1.0.0\n", encoding="utf-8")
    problems = check_document(document.resolve())
    assert problems, "an unannotated document passed the check"
    assert "explicitly deferred" in problems[0], problems


# ---------------------------------------------------------------------------
# The deployment-authored envelope (plan 15-13)
# ---------------------------------------------------------------------------
#
# A class the SDK does not own has no class-specific committed schema, so its
# documents point at the shared `DeclaredArtifact` envelope instead. Each test
# below pins one way that indirection could have weakened the gate, and each
# one fails for the reason it names.


def _envelope_document(directory: pathlib.Path, body: str) -> pathlib.Path:
    """Write a document headed with the committed envelope schema."""
    target = SCHEMAS_DIR / f"{ENVELOPE_CLASS_ID}.json"
    path = directory / "declared.yaml"
    path.write_text(
        f"{HEADER_PREFIX}{os.path.relpath(target, directory)}\n{body}",
        encoding="utf-8",
    )
    return path.resolve()


def test_the_envelope_schema_is_committed_and_annotated() -> None:
    """Without it, a deployment-authored document has no honest header."""
    document = json.loads(
        (SCHEMAS_DIR / f"{ENVELOPE_CLASS_ID}.json").read_text(encoding="utf-8")
    )
    assert document[CLASS_ID_KEY] == ENVELOPE_CLASS_ID


def test_the_envelope_is_not_an_owned_class() -> None:
    """It is committed *without* becoming manifest-addressable.

    Adding it to ``SDK_ARTIFACT_CLASSES`` would let a manifest name the
    envelope as a class and would break the "an unknown class id *is* a
    deployment-authored schema" design it exists to serve.
    """
    assert ENVELOPE_CLASS_ID not in SDK_ARTIFACT_CLASSES


def test_a_deployment_authored_document_passes_on_the_envelope(
    tmp_path: pathlib.Path,
) -> None:
    """The path this indirection exists to open."""
    document = _envelope_document(
        tmp_path, "semver: '1.0.0'\nclass_id: acme.thing\ndeclaration:\n  a: 1\n"
    )
    assert check_document(document) == []


def test_an_envelope_document_naming_no_class_fails(
    tmp_path: pathlib.Path,
) -> None:
    """The envelope is shared, so the document's own field is what identifies
    it; without one, nothing states what kind of thing it is."""
    document = _envelope_document(tmp_path, "semver: '1.0.0'\ndeclaration:\n  a: 1\n")
    problems = check_document(document)
    assert problems and "declares no `class_id`" in problems[0], problems


def test_an_envelope_header_over_an_sdk_owned_class_fails(
    tmp_path: pathlib.Path,
) -> None:
    """The envelope must not become a way to opt out of the real schema.

    Its ``declaration`` is open, so pointing an SDK-owned document at it would
    silence every constraint that class actually declares.
    """
    document = _envelope_document(
        tmp_path, "semver: '1.0.0'\nclass_id: ccf.perspective\ndeclaration:\n  a: 1\n"
    )
    problems = check_document(document)
    assert problems and "which the SDK owns" in problems[0], problems


def test_the_envelope_still_refuses_a_document_it_does_not_accept(
    tmp_path: pathlib.Path,
) -> None:
    """Open ``declaration`` does not mean an open document: the envelope's own
    three keys are still closed-world."""
    document = _envelope_document(
        tmp_path,
        "semver: '1.0.0'\nclass_id: acme.thing\ndeclaration:\n  a: 1\nstray: 2\n",
    )
    problems = check_document(document)
    assert problems and "does not accept this document" in problems[0], problems


def test_the_manifest_cross_check_reads_the_documents_own_class_id(
    tmp_path: pathlib.Path,
) -> None:
    """Two independent statements of one fact must still be compared.

    For an envelope-headed document the header carries no class identity, so
    the cross-check falls through to the document's ``class_id`` field. If it
    did not, a manifest could name any class at all for a deployment-authored
    document and nothing would fire.
    """
    _envelope_document(
        tmp_path, "semver: '1.0.0'\nclass_id: acme.thing\ndeclaration:\n  a: 1\n"
    )
    (tmp_path / "manifest.yaml").write_text(
        "semver: '1.0.0'\n"
        "tenant_id: t\n"
        "backend: sqlite\n"
        "resolution_spec_key: declared\n"
        "policy_bundle_key: declared\n"
        "artifacts:\n"
        "  - path: declared.yaml\n"
        "    key: declared\n"
        "    class_id: acme.something-else\n"
        "    role: register\n",
        encoding="utf-8",
    )
    problems = check_directory(tmp_path)
    assert problems, "a manifest disagreeing with the document passed"
    assert any("disagree" in problem for problem in problems), problems


def test_a_deferral_marker_must_name_the_closing_plan(
    tmp_path: pathlib.Path,
) -> None:
    """An exemption with no owner is an exemption that never closes."""
    document = tmp_path / "vague.yaml"
    document.write_text(f"{DEFERRED_PREFIX} someday\n", encoding="utf-8")
    problems = check_document(document.resolve())
    assert problems, "an ownerless deferral passed the check"
    assert "closing plan" in problems[0], problems


# ---------------------------------------------------------------------------
# The route and the ninth noun (D-IMPL-79)
# ---------------------------------------------------------------------------


def test_the_route_and_the_tool_spell_the_annotation_key_identically() -> None:
    """``/runtime`` never imports the repo's build tooling, so the key is
    spelled twice; this is what keeps the two spellings equal."""
    from ccf_runtime.http_api.routes.schema import (
        CLASS_ID_KEY as ROUTE_KEY,
    )

    assert ROUTE_KEY == CLASS_ID_KEY


def test_the_route_serves_a_schema_for_every_owned_class(
    deps: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """Served from the live models — the committed tree is the baseline,
    not the source."""
    from cli.conftest import run_cli

    for class_id in sorted(SDK_ARTIFACT_CLASSES):
        code, out, _ = run_cli(
            ["schema", "export", "--class-id", class_id],
            capsys,
            dependencies=deps,
        )
        assert code == 0, class_id
        assert json.loads(out)[CLASS_ID_KEY] == class_id


def test_the_served_schema_equals_the_committed_one(
    deps: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """The route and the committed baseline are the same document.

    This is the assertion that makes ``docs/schemas/`` a *baseline* rather
    than a second, independently drifting artifact.
    """
    from cli.conftest import run_cli

    class_id = "ccf.perspective"
    _, out, _ = run_cli(
        ["schema", "export", "--class-id", class_id], capsys, dependencies=deps
    )
    committed = json.loads(
        (SCHEMAS_DIR / f"{class_id}.json").read_text(encoding="utf-8")
    )
    assert json.loads(out) == committed


def test_the_list_verb_names_every_owned_class(
    deps: object, capsys: pytest.CaptureFixture[str]
) -> None:
    from cli.conftest import run_cli

    code, out, _ = run_cli(["schema", "export"], capsys, dependencies=deps)
    assert code == 0
    assert json.loads(out) == sorted(SDK_ARTIFACT_CLASSES)


def test_an_unowned_class_id_is_a_typed_404(
    deps: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """The SDK never invents a schema for a namespace that is not its own."""
    from cli.conftest import run_cli

    code, out, _ = run_cli(
        ["schema", "export", "--class-id", "acme.something"],
        capsys,
        dependencies=deps,
    )
    assert code == 1
    assert "acme.something" in out


def test_the_noun_returns_request_specs_and_main_has_no_branch() -> None:
    """D-IMPL-79: the ninth noun is a ``RequestSpec`` like the other eight.

    Asserted two ways, because the ruling is structural: every handler the
    noun registers returns ``RequestSpec`` values, and ``main`` reaches
    them through the single ``args.build(args)`` dispatch with no
    noun-specific branch anywhere in it.
    """
    import inspect

    from ccf_runtime.cli import main as cli_main
    from ccf_runtime.cli.commands import RequestSpec, schema

    parser = cli_main.build_parser()
    args = parser.parse_args(["schema", "export", "--class-id", "x"])
    specs = args.build(args)
    assert isinstance(specs, tuple)
    assert all(isinstance(spec, RequestSpec) for spec in specs)
    assert specs[0].method == "GET"

    assert schema.__all__ == ["register"]
    assert all(
        isinstance(spec, RequestSpec)
        for spec in parser.parse_args(["schema", "export"]).build(
            parser.parse_args(["schema", "export"])
        )
    )

    source = inspect.getsource(cli_main.main)
    assert source.count("args.build(args)") == 1
    # Dispatch is uniform: main never reads which noun it is running, so a
    # new noun is a registration and never a branch.
    assert "args.noun" not in source
    assert "args.verb" not in source
    for noun in ('"schema"', "'schema'"):
        assert noun not in source, noun


# --- the third bucket: no ArtifactClass is invisible ----------------------
#
# Plans 15-13 and 15-14 each found an artifact class with no honest `$schema`
# target and added an emission bucket for it. Plan 15-17 found two more and
# deferred them. The pattern is the tell: hand-maintained lists of "classes
# that need schemas" go stale the moment someone adds a class, and the failure
# is silent — an adopter simply has nothing to point a header at. These tests
# hold the discovery mechanism to the invariant that replaced the lists.


def test_every_artifact_class_in_the_tree_has_a_committed_schema() -> None:
    """The invariant the third bucket exists to hold.

    Written as a walk rather than a list for the same reason the bucket is:
    a class defined in a module nobody thought to check is exactly the class
    that goes un-emitted. When this fails, the fix is `make schemas`, not an
    edit to this test.
    """
    from tools.dump_schemas import _artifact_bearing_modules, schema_owned_classes

    import importlib

    from ccf.controlplane.artifact_base import ArtifactClass

    owned = schema_owned_classes()
    missing: list[str] = []
    for module_name in _artifact_bearing_modules():
        module = importlib.import_module(module_name)
        for name in dir(module):
            candidate = getattr(module, name, None)
            if isinstance(candidate, ArtifactClass) and candidate.class_id not in owned:
                missing.append(f"{candidate.class_id} ({module_name})")
    assert not missing, (
        "These artifact classes have no committed schema, so an adopter has"
        f" nothing to point a $schema header at: {sorted(set(missing))}."
        " Run `make schemas` and commit the result."
    )


def test_the_discovery_is_not_vacuous() -> None:
    """A walk that silently found nothing would pass the test above forever."""
    from tools.dump_schemas import _artifact_bearing_modules, unaddressable_classes

    modules = _artifact_bearing_modules()
    assert len(modules) >= 50, len(modules)
    assert any(name.startswith("ccf_runtime.") for name in modules), (
        "the walk never reached /runtime, where ccf.scope-mapping lives"
    )
    found = unaddressable_classes()
    assert "ccf.scope-mapping" in found, sorted(found)
    assert "ccf.hitl-policy" in found, sorted(found)


def test_a_schema_grants_no_manifest_addressability() -> None:
    """The line the third bucket must not blur.

    Emitting a schema is authoring help. Manifest addressability is governance:
    a manifest entry naming an author-versioned class would silently drop the
    D-05 bump check, which is why those classes are kept out of
    SDK_ARTIFACT_CLASSES despite having schemas. The same must hold here.
    """
    from ccf.deployment.classes import SDK_ARTIFACT_CLASSES
    from tools.dump_schemas import author_versioned_classes, unaddressable_classes

    for class_id in {**author_versioned_classes(), **unaddressable_classes()}:
        assert class_id not in SDK_ARTIFACT_CLASSES, (
            f"{class_id} gained manifest addressability by being given a"
            " schema; a schema is authoring help, never governance"
        )
