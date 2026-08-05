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
    SCHEMAS_DIR,
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
