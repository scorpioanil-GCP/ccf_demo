"""D-08 — the snippet drift gate, proven live rather than assumed.

`check_paths: true` in `mkdocs.yml` is the entirety of D-08. At the
extension's default (`false`) BOTH a missing snippet file and a missing named
section build clean at exit 0, emitting an EMPTY code block onto the published
page — and `--strict` cannot help, because nothing is emitted to warn about. A
guide whose every code block is an include would then ship silently blank the
moment a marker was renamed.

This module is the negative control for that setting. It builds throwaway
mkdocs projects in a temporary directory and asserts the build FAILS for each
failure mode, and succeeds for the clean control.

Both violating cases are exercised separately on purpose: `pymdownx.snippets`
guards them at two different call sites — one when opening the file, one when
locating the named section inside it — so a config regression could plausibly
restore one guard without the other. A single combined case would pass while
half the gate was dead.

`base_path` resolves against the PROCESS CWD, not against the config file's
directory. Every subprocess below therefore runs with `cwd` set to the
throwaway project root and `base_path: ["."]`, which is the same relationship
the real build has (`mkdocs.yml` at the repo root, `make` run from the repo
root). Getting this wrong makes the clean case fail for the wrong reason.

The working tree is never modified: sources are COPIED into the temporary
directory before being mutated.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The source the guide includes from, and one region marker inside it.
SNIPPET_SOURCE = REPO_ROOT / "examples" / "00-quickstart" / "run.py"
SECTION = "ontology"

#: Subprocess bound — a hung mkdocs must fail the suite, not stall CI.
BUILD_TIMEOUT_SECONDS = 180

CONFIG = """\
site_name: snippet gate fixture
docs_dir: docs
site_dir: site
strict: true
markdown_extensions:
  - pymdownx.snippets:
      base_path: ["."]
      check_paths: true
      restrict_base_path: true
      dedent_subsections: true
"""


def _project(root: pathlib.Path, *, page: str, source: str | None) -> None:
    """Write a throwaway mkdocs project: config, one page, one snippet source."""
    (root / "mkdocs.yml").write_text(CONFIG, encoding="utf-8")
    docs = root / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(page, encoding="utf-8")
    if source is not None:
        (root / "source.py").write_text(source, encoding="utf-8")


def _build(root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mkdocs", "build"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_SECONDS,
    )


def _page(target: str) -> str:
    return f'# Fixture\n\n```py\n--8<-- "{target}"\n```\n'


# --- violating case 1: a deleted marker ------------------------------------


def test_a_deleted_section_marker_fails_the_strict_build(
    tmp_path: pathlib.Path,
) -> None:
    original = SNIPPET_SOURCE.read_text(encoding="utf-8")
    assert f"[start:{SECTION}]" in original, "fixture drifted from its source"
    stripped = "".join(
        line
        for line in original.splitlines(keepends=True)
        if f"[start:{SECTION}]" not in line
    )
    _project(tmp_path, page=_page(f"source.py:{SECTION}"), source=stripped)

    result = _build(tmp_path)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "Snippet" in result.stdout + result.stderr


# --- violating case 2: a missing file --------------------------------------


def test_a_missing_snippet_file_fails_the_strict_build(
    tmp_path: pathlib.Path,
) -> None:
    _project(tmp_path, page=_page("no-such-file.py"), source=None)

    result = _build(tmp_path)

    assert result.returncode != 0, result.stdout + result.stderr


# --- clean case ------------------------------------------------------------


def test_the_unmodified_source_builds_clean(tmp_path: pathlib.Path) -> None:
    _project(
        tmp_path,
        page=_page(f"source.py:{SECTION}"),
        source=SNIPPET_SOURCE.read_text(encoding="utf-8"),
    )

    result = _build(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
