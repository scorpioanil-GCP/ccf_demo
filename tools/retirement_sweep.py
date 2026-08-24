#!/usr/bin/env python3
"""Repo-wide sweep for live couplings to the paths Phase 16 retires (DOCS-17).

Why this exists, stated rather than left to be rediscovered. The retirement
inventory in ``16-RESEARCH.md`` § A.1/§ A.2 walked ``examples/``,
``tests/examples/`` and ``public/`` **only**, while ``[tool.pytest] testpaths =
["tests"]`` means ``make ci`` runs the whole of ``tests/``. Every gate under
``tests/cli/``, ``tests/products/``, ``tests/conformance/``, ``tests/lints/``,
``tests/perf_smoke/``, ``tools/*_tests/`` and ``perf/`` that names a retiring
path is therefore in the always-on path and unmeasured. Three review rounds
found six instances of that one defect class, each in a different tree and each
breaking a different wave. Fixing instances one at a time loses; this module is
the class fix, and later waves **re-run it** rather than trusting the snapshot
it writes.

What it measures. Five detectors, because a token pass sees only the first:

1. **Path tokens** — a retiring path written as a string, a build recipe, a
   workflow step, a snippet include or a Markdown link. Python is read with
   ``ast`` (so a segmented ``Path(...) / "examples" / "04-cross-process"``
   construction is reconstructed and matched); everything else is read as
   text, which is deliberately coarser and is labelled as such per row.
2. **Count constants** — a module-level ``MINIMUM_*`` floor whose scan is fed
   by the retiring tree.
3. **Count scan functions** — the module-level function whose result that
   floor is compared against.
4. **Inline tree-witness assertions** — an assertion whose scan is written
   *inline in a test body*, keyed off a module-level scanned-tree tuple, with
   **neither a constant nor a named scan function**. This shape survived a
   full review round undetected. Its witnesses are measured *empirically* —
   the test is executed with the module's own enumeration helper restricted to
   one retiring path at a time — because the only textual occurrence of the
   measured witness in that module is inside a docstring, which this module's
   own liveness filter correctly classifies as not-live.
5. **Indirect executions** — a test under ``tests/`` that runs a suite,
   script or package **outside** ``tests/``, where *that* code resolves a
   retiring path. Neither hop carries a path token; the path is *constructed*.
   The measured instance is ``tests/perf_smoke/test_smoke.py`` →
   ``perf/suites/crossproc/conftest.py`` → ``examples/04-cross-process``, and
   it was found only by deleting the examples in a scratch clone and running
   the always-on path.

**Live means live, and documentary means documentary — neither means
dropped.** A hit inside a Python docstring or on a comment line is classified
``documentary`` rather than ``live``: deleting its subject leaves stale text,
not a red build. It still gets a row and an owner, because four of the
fourteen files this sweep is required to find carry *only* documentary hits
(``tests/conformance/test_harness_portability.py``,
``tests/conformance/test_a3_discharge.py``, ``perf/suites/common.py`` and
``perf/synth/artifacts/controlplane.yaml``), and each is named in an owning
plan's ``files_modified``. A filter that dropped them would report clean over
work four plans have already accepted. The severity distinction is carried in
the ``Liveness`` column, which is what the distinction is for.

A third class, ``survives``, marks a live string literal written into a
``tmp_path`` scratch tree and never resolved on disk. It survives the deletion
mechanically while still naming a directory that will not exist, so its owner
repoints the token rather than leaving the fixture to outlive its subject.

Walking. ``REPO_ROOT`` comes from this file's own location, never
``Path.cwd()``: WR-04 is the recorded failure where a CWD-relative walk scanned
zero files and the gate passed over nothing. ``tools.publish_scan.SKIP_DIRS``
is reused rather than re-invented.

Extension. The retirement schedule, the exclusions and the owner overrides are
module-level data. A later plan extends the target list without touching the
walk — and if it extends the schedule without assigning an owner, the row comes
out unowned and the gate fails, which is the point.

SDK-defined tooling (CLAUDE.md §3.1, §6.4): this is a gate over the phase's own
retirement work, not fabric mechanism.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import importlib.util
import io
import os
import pathlib
import re
import subprocess
import sys
import tokenize
import types
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# The repo root, `src/` and `runtime/` join `sys.path` explicitly rather than
# through PYTHONPATH, because detectors 2-4 import the gate modules they
# measure and this module must behave identically from any CWD (WR-04).
for _bootstrap in (REPO_ROOT, REPO_ROOT / "src", REPO_ROOT / "runtime"):
    if str(_bootstrap) not in sys.path:
        sys.path.insert(0, str(_bootstrap))

from tools.lints import (  # noqa: E402  (after the sys.path bootstrap)
    imported_module_names,
    submodule_import_names,
)
from tools.publish_scan import SKIP_DIRS  # noqa: E402


# ---------------------------------------------------------------------------
# The retirement schedule — data, so a later plan extends it without editing
# the walk. `owner` is the plan that must act; `wave` is when it acts.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Retirement:
    """One path this phase retires, with the plan and wave that retires it."""

    path: str
    owner: str
    wave: int


#: The ten retiring example directories, the `tests/examples/` modules that
#: retire with them, and the two published pages scheduled for deletion.
#: Owners and waves come from the phase's own retirement schedule: 16-15
#: retires `03-harness-portability` at wave 8; 16-17 retires `04-cross-process`
#: and `07-artifact-store-mcp` at wave 10; 16-18 retires the remaining seven,
#: the retiring test modules and the two published pages at wave 11. Each
#: owner was checked against the owning plan's own `files_modified`.
RETIREMENT_SCHEDULE: tuple[Retirement, ...] = (
    # --- wave 8 (16-15) ---
    Retirement("examples/03-harness-portability", "16-15", 8),
    Retirement("tests/examples/test_harness_portability_output.py", "16-15", 8),
    # --- wave 10 (16-17) ---
    Retirement("examples/04-cross-process", "16-17", 10),
    Retirement("examples/07-artifact-store-mcp", "16-17", 10),
    Retirement("tests/examples/test_cross_process_output.py", "16-17", 10),
    Retirement("tests/examples/test_artifact_store_output.py", "16-17", 10),
    # --- wave 11 (16-18) ---
    Retirement("examples/00-quickstart", "16-18", 11),
    Retirement("examples/01-agent-basics", "16-18", 11),
    Retirement("examples/02-skilling", "16-18", 11),
    Retirement("examples/05-workflow-hitl", "16-18", 11),
    Retirement("examples/06-decision-replay", "16-18", 11),
    Retirement("examples/08-e2e-demo", "16-18", 11),
    Retirement("examples/external/00-hello-context", "16-18", 11),
    Retirement("tests/examples/test_quickstart_output.py", "16-18", 11),
    Retirement("tests/examples/test_agent_basics_output.py", "16-18", 11),
    Retirement("tests/examples/test_skilling_output.py", "16-18", 11),
    Retirement("tests/examples/test_workflow_hitl_output.py", "16-18", 11),
    Retirement("tests/examples/test_decision_replay_output.py", "16-18", 11),
    Retirement("tests/examples/test_e2e_demo_output.py", "16-18", 11),
    Retirement("tests/examples/test_ext00_fixture_schemas.py", "16-18", 11),
    Retirement("tests/examples/test_ext00_hardening.py", "16-18", 11),
    Retirement("tests/examples/test_ext00_serve_output.py", "16-18", 11),
    Retirement("public/tutorial/adopters-guide.md", "16-18", 11),
    Retirement("public/tutorial/demo-walkthrough.md", "16-18", 11),
    # --- wave 12 (17-08) ---
    # Phase 17's condemned trees (D-27, D-31). The wave integer continues the
    # existing sequence rather than restarting at Phase 17's own wave 6: `wave`
    # orders retirements against each other for `_first_break` and the
    # cross-wave check, and Phase 17 disposes of these *after* every Phase 16
    # wave, so 12 is the ordering the field actually encodes. Existing entries
    # are not renumbered. Each path was confirmed to exist before being listed
    # — the unowned-row gate is fail-closed, and a schedule naming a path that
    # is not there is the same class of defect as one that omits a path.
    Retirement("examples/s1-00-companies-over-revenue", "17-08", 12),
    Retirement("examples/s1-01-hello-context-product", "17-08", 12),
    Retirement("tests/examples/test_s1_00_output.py", "17-08", 12),
    Retirement("tests/examples/test_s1_01_output.py", "17-08", 12),
    Retirement("tests/examples/test_s1_00_config_equivalence.py", "17-08", 12),
)

#: The disposition for a row whose owner the schedule cannot supply. It is a
#: hard gate failure by design: an unowned row means a coupling exists that no
#: plan owns, and waves 8, 10 and 11 delete into it. Closed by assigning an
#: owner, never by narrating it and never by deleting the row.
UNOWNED = "UNASSIGNED"

#: The plan that owns a *referencing file* when that differs from the plan that
#: retires the path it names. `tests/examples/test_artifact_schema_headers.py`
#: is reshaped by 16-02 (it is in 16-02's `files_modified`); the per-example
#: deletions inside it are removed by the plans that delete their examples.
REFERENCING_FILE_OWNERS: dict[str, str] = {
    "tests/examples/test_artifact_schema_headers.py": "16-02",
}

#: Trees and files measured but deliberately not assigned an owner, each with
#: the reason it is out of scope. Every entry is either an append-only record
#: that names a retiring path as *history* and is never rewritten, or a
#: document no plan in this phase may edit. Their hit counts are reported so
#: the exclusion is visible rather than silent.
EXCLUDED_FROM_ASSIGNMENT: tuple[tuple[str, str], ...] = (
    (
        "tools/retirement_sweep.py",
        "the sweep's own schedule — it names every retiring path by"
        " construction, and must go on naming them after the deletions or the"
        " re-runs waves 8, 10 and 11 depend on stop being possible",
    ),
    (".planning/", "the phase's own planning tree — not shipped, not published"),
    ("site/", "generated mkdocs output, rebuilt from public/"),
    ("CLAUDE.md", "the project charter; revised by Dave, by no plan (CLAUDE.md §2)"),
    ("docs/DECISIONS.md", "append-only decision log"),
    ("docs/ROADMAP.md", "append-only phase record"),
    ("docs/SURFACE-AUDIT.md", "append-only audit record"),
    ("docs/SURFACE-CHANGES.md", "append-only surface-change index"),
    ("docs/surface-changes/", "append-only per-plan surface-change records"),
    ("docs/PHASE_", "append-only per-phase gate records"),
    ("docs/surface/examples/before/", "frozen ERGO-03 baseline (D-15)"),
    ("docs/surface/examples/after/", "frozen ERGO-03 measurement (D-15)"),
    ("docs/surface/examples/ERGO-03-FROZEN.md", "the frozen ERGO-03 record (D-15)"),
)

#: This sweep's own report. Excluded from the walk, because a report that
#: quotes every retiring path would otherwise re-detect itself and the second
#: `--report` run would not be byte-identical to the first.
REPORT_PATH = REPO_ROOT / "docs" / "surface" / "examples" / "RETIREMENT-COUPLINGS.md"

#: Suffixes read as bytes rather than text. Everything else is attempted as
#: UTF-8 and skipped on a decode error, so the walk is default-scan: a suffix
#: allowlist is how a sweep goes blind to the one file nobody thought of.
BINARY_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip",
     ".gz", ".db", ".sqlite", ".sqlite3", ".pyc", ".so", ".dylib", ".whl"}
)

#: Build and cache directories pruned in addition to `publish_scan.SKIP_DIRS`.
#:
#: Found by the wave-2 post-merge gate, not by this module's own suite: the
#: first committed report carried **301 rows from `.pytest_cache/v/cache/
#: nodeids`**, a gitignored file whose contents are whatever tests were last
#: selected. That made the inventory a function of the developer's last pytest
#: invocation rather than of the tree, so `--report && git diff` — the gate
#: plans 16-15, 16-17 and 16-18 depend on — produced spurious diffs. The
#: shared `publish_scan.SKIP_DIRS` is deliberately not widened: it is another
#: phase's surface and the publish scan has its own reasons for what it reads.
#:
#: The set is a hand-maintained fast prune and a fallback for a non-git
#: checkout. It is **no longer the authority**: `git_ignored_entries()` asks
#: git directly, so the rule is "the inventory measures the tracked tree"
#: rather than a list of names someone remembered.
#:
#: The hand-maintained list drifting from `.gitignore` is measured, not
#: hypothetical. Plan 17-01 found five gitignored trees absent from this set —
#: `.mypy_cache/`, `build/`, `dist/`, `perf/results/` and `__pycache__/` — and
#: reproduced the consequence: a single file written to `perf/results/`, a
#: directory `.gitignore:18` ignores and the perf battery writes on every run,
#: put a row in the inventory and made `--report && git diff` a function of
#: whether a developer had run the battery. That is precisely the
#: non-reproducibility `test_no_gitignored_path_reaches_the_report` exists to
#: catch, and a second hand-list is a second thing that can drift, so the walk
#: now asks git and keeps this set only as the fallback.
ARTIFACT_DIRS: frozenset[str] = frozenset(
    {".pytest_cache", ".hypothesis", ".ruff_cache", "ccf.egg-info", "site",
     "htmlcov", ".tox", "node_modules", ".claude", ".mypy_cache", "build",
     "dist", "__pycache__"}
)


# ---------------------------------------------------------------------------
# Shape vocabulary. The four no-path-token shapes are the last four.
# ---------------------------------------------------------------------------

SHAPE_PATH_CONSTRUCTION = "path-construction"
SHAPE_MODULE_CONSTANT = "module-constant"
SHAPE_LITERAL_SET_MEMBER = "literal-set-member"
SHAPE_GLOB = "glob"
SHAPE_STRING_LITERAL = "string-literal"
SHAPE_DOCSTRING = "docstring"
SHAPE_COMMENT = "comment"
SHAPE_MAKEFILE_RECIPE = "makefile-recipe"
SHAPE_WORKFLOW_STEP = "workflow-step"
SHAPE_SNIPPET_INCLUDE = "snippet-include"
SHAPE_MARKDOWN_LINK = "markdown-link"
SHAPE_PROSE = "prose"
SHAPE_CONFIG_TOKEN = "config-token"
SHAPE_TMP_PATH_SYNTHETIC = "tmp_path-synthetic"
SHAPE_COUNT_CONSTANT = "count-constant"
SHAPE_COUNT_SCAN_FUNCTION = "count-scan-function"
SHAPE_INLINE_TREE_WITNESS = "inline-tree-witness"
SHAPE_INDIRECT_EXECUTION = "indirect-execution"

LIVE = "live"
DOCUMENTARY = "documentary"
SURVIVES = "survives"


@dataclasses.dataclass(frozen=True)
class Coupling:
    """One row of the inventory."""

    file: str
    line: int
    retiring_path: str
    shape: str
    liveness: str
    owner: str
    witnesses: str = "-"
    intermediate: str = "-"
    note: str = ""

    def sort_key(self) -> tuple[str, int, str, str]:
        return (self.file, self.line, self.shape, self.retiring_path)


# ---------------------------------------------------------------------------
# Schedule lookups.
# ---------------------------------------------------------------------------


def retiring_paths() -> tuple[str, ...]:
    """Every path the schedule retires, longest first so the most specific wins."""
    return tuple(
        sorted((entry.path for entry in RETIREMENT_SCHEDULE), key=len, reverse=True)
    )


def _entry_for(path: str) -> Retirement | None:
    for entry in RETIREMENT_SCHEDULE:
        if entry.path == path:
            return entry
    return None


def owner_for(path: str) -> str:
    """The plan that retires `path`, or the unowned disposition."""
    entry = _entry_for(path)
    return entry.owner if entry is not None else UNOWNED


def wave_for(path: str) -> int:
    """The wave `path` retires at, or a sentinel beyond every real wave."""
    entry = _entry_for(path)
    return entry.wave if entry is not None else 10**6


def containing_retirement(relative: str) -> Retirement | None:
    """The schedule entry whose path contains `relative`, if any."""
    for entry in sorted(RETIREMENT_SCHEDULE, key=lambda e: len(e.path), reverse=True):
        if relative == entry.path or relative.startswith(entry.path + "/"):
            return entry
    return None


def exclusion_reason(relative: str) -> str | None:
    """Why `relative` is measured but not assigned, or None if it is in scope."""
    for prefix, reason in EXCLUDED_FROM_ASSIGNMENT:
        if relative == prefix or relative.startswith(prefix):
            return reason
    return None


def resolve_owner(relative_file: str, retiring_path: str) -> str:
    """Owner of a row: the referencing-file override, else the schedule."""
    override = REFERENCING_FILE_OWNERS.get(relative_file)
    if override is not None:
        return override
    return owner_for(retiring_path)


# ---------------------------------------------------------------------------
# The source walk.
# ---------------------------------------------------------------------------


def git_ignored_entries() -> frozenset[str]:
    """Every repo-relative path git ignores, as POSIX strings without a slash.

    Asked of git rather than parsed out of `.gitignore`, because a second
    pattern parser is a second thing that can drift from the first — and the
    drift is what `test_no_gitignored_path_reaches_the_report` measures, so the
    walk and the gate must consult the same authority. `--directory` collapses
    a wholly-ignored directory to one entry, which is what makes this a prune
    rather than a per-file filter.

    Returns an empty set when git is unavailable or `REPO_ROOT` is not a
    checkout; the walk then falls back to `ARTIFACT_DIRS` alone. Failing open
    is deliberate: this is a reporting sweep, and a missing git binary should
    widen the report rather than abort it.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-o", "-i", "--directory", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
    except OSError:
        return frozenset()
    if proc.returncode != 0:
        return frozenset()
    return frozenset(
        line.strip().rstrip("/")
        for line in proc.stdout.splitlines()
        if line.strip()
    )


def iter_source_files() -> list[pathlib.Path]:
    """Every readable file under `REPO_ROOT`, minus the skip set and the report.

    Rooted at `REPO_ROOT`, never `Path.cwd()`. Three prunes compose: git's own
    ignore rules (`git_ignored_entries()`, the authority),
    `publish_scan.SKIP_DIRS`, and `ARTIFACT_DIRS` as a fast pre-prune and a
    non-git fallback. The result is that the walk reads the tracked tree and
    not build output — see `ARTIFACT_DIRS` for the measured failure that
    motivates asking git rather than maintaining a list.
    """
    found: list[pathlib.Path] = []
    pruned = SKIP_DIRS | ARTIFACT_DIRS
    ignored = git_ignored_entries()
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in pruned
            and relative(pathlib.Path(dirpath) / name) not in ignored
        )
        for name in sorted(filenames):
            path = pathlib.Path(dirpath) / name
            if path == REPORT_PATH:
                continue
            if path.suffix.lower() in BINARY_SUFFIXES:
                continue
            if relative(path) in ignored:
                continue
            found.append(path)
    return sorted(found)


def relative(path: pathlib.Path) -> str:
    """Repo-relative POSIX form, or the absolute form for a path outside it.

    The fallback is what lets the standing gate point each detector at a
    synthetic tree under `tmp_path` and prove the shape is detected, rather
    than asserting only against the tree that happens to be checked in.
    """
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


@dataclasses.dataclass(frozen=True)
class Unexaminable:
    """A subject the sweep could not look at.

    The sweep decides what is safe to delete. A subject it cannot examine is
    NOT evidence of no coupling — it is the absence of evidence — and the two
    were previously indistinguishable, because every failure path returned
    ``None`` and the caller moved on. The run then printed a confident total
    at exit 0. Reproduced on a real tree: under ``/usr/bin/python3`` rather
    than ``.venv/bin/python``, three gate modules fail to import, six coupling
    rows vanish, and the tool reports the smaller number without complaint.

    Recorded rather than raised so that ONE run names EVERY unexaminable
    subject; stopping at the first would hide the rest behind it.
    """

    subject: str
    stage: str
    detail: str

    def line(self) -> str:
        return f"  {self.subject} [{self.stage}] {self.detail}"


_UNEXAMINABLE: list[Unexaminable] = []


def reset_unexaminable() -> None:
    """Drop the record. Called at the top of every :func:`sweep`."""
    _UNEXAMINABLE.clear()


def record_unexaminable(subject: str, stage: str, exc: BaseException | str) -> None:
    """Note that `subject` could not be examined at `stage`, and why."""
    detail = (
        exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}".strip()
    )
    _UNEXAMINABLE.append(Unexaminable(subject=subject, stage=stage, detail=detail))


def unexaminable() -> tuple[Unexaminable, ...]:
    """Every subject this run could not examine, deduplicated, in order."""
    seen: dict[tuple[str, str, str], Unexaminable] = {}
    for item in _UNEXAMINABLE:
        seen.setdefault((item.subject, item.stage, item.detail), item)
    return tuple(seen.values())


def read_text(path: pathlib.Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        # Measured at the time this was closed: `iter_source_files()` yields
        # zero files this cannot read, so recording here costs no false red
        # today and closes the class for the day a file arrives that it can.
        record_unexaminable(relative(path), "read", exc)
        return None


# ---------------------------------------------------------------------------
# Detector 1a — the Python AST pass.
# ---------------------------------------------------------------------------


def _docstring_spans(tree: ast.Module) -> list[tuple[int, int]]:
    """Line spans of every module, class and function docstring."""
    spans: list[tuple[int, int]] = []
    holders: list[ast.AST] = [tree]
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            holders.append(node)
    for holder in holders:
        body = getattr(holder, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            spans.append((first.lineno, first.value.end_lineno or first.lineno))
    return spans


def _comment_lines(source: str) -> set[int]:
    """Line numbers carrying a `#` comment token."""
    lines: set[int] = set()
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                lines.add(token.start[0])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # DELIBERATELY NOT recorded as unexaminable, and the reason is the
        # polarity. This is a real fallback, not a swallow: it still answers,
        # by scanning for `#`-prefixed lines. What it misses is a TRAILING
        # comment, and a line missing from this set is classified as live code
        # rather than DOCUMENTARY -- so the degraded path OVER-reports a
        # coupling. For a tool that decides what is safe to delete, that is the
        # safe direction, and a false red here would be a real coupling found.
        for number, text in enumerate(source.splitlines(), start=1):
            if text.lstrip().startswith("#"):
                lines.add(number)
    return lines


def _div_chain(node: ast.BinOp) -> str | None:
    """The joined string constants of a `/` chain, e.g. `examples/04-cross-process`.

    `Path(__file__).resolve().parents[3] / "examples" / "04-cross-process"`
    carries no path token anywhere; the path is *constructed*. Reconstructing
    the chain is what makes a token pass see it.
    """
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.BinOp) and isinstance(current.op, ast.Div):
        right = current.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            parts.append(right.value)
        else:
            parts.append("*")
        current = current.left
    if isinstance(current, ast.Constant) and isinstance(current.value, str):
        parts.append(current.value)
    parts.reverse()
    return "/".join(parts) if len(parts) > 1 else None


def _function_spans(tree: ast.Module) -> list[tuple[int, int, ast.AST]]:
    spans: list[tuple[int, int, ast.AST]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((node.lineno, node.end_lineno or node.lineno, node))
    return spans


def _takes_tmp_path(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    return "tmp_path" in names


def _shape_map(tree: ast.Module) -> dict[int, str]:
    """Node-id -> shape for string constants whose syntactic role is known."""
    shapes: dict[int, str] = {}
    for statement in tree.body:
        targets: list[ast.expr] = []
        if isinstance(statement, ast.Assign):
            targets = [statement.value]
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            targets = [statement.value]
        for value in targets:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                shapes[id(value)] = SHAPE_MODULE_CONSTANT
            elif isinstance(value, (ast.Tuple, ast.List, ast.Set)):
                for element in value.elts:
                    if isinstance(element, ast.Constant) and isinstance(
                        element.value, str
                    ):
                        shapes[id(element)] = SHAPE_LITERAL_SET_MEMBER
            elif isinstance(value, ast.Dict):
                entries: list[ast.expr] = [
                    node for node in (*value.keys, *value.values) if node is not None
                ]
                for element in entries:
                    if isinstance(element, ast.Constant) and isinstance(
                        element.value, str
                    ):
                        shapes[id(element)] = SHAPE_LITERAL_SET_MEMBER
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                for element in value.args:
                    if isinstance(element, ast.Constant) and isinstance(
                        element.value, str
                    ):
                        shapes[id(element)] = SHAPE_MODULE_CONSTANT
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"glob", "rglob"}:
                for element in node.args:
                    if isinstance(element, ast.Constant) and isinstance(
                        element.value, str
                    ):
                        shapes[id(element)] = SHAPE_GLOB
    return shapes


def python_hits(path: pathlib.Path, source: str) -> list[Coupling]:
    """Every retiring-path reference in a Python module, classified."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    rel = relative(path)
    docstrings = _docstring_spans(tree)
    comments = _comment_lines(source)
    shapes = _shape_map(tree)
    functions = _function_spans(tree)
    targets = retiring_paths()

    def classify(line: int, default_shape: str) -> tuple[str, str]:
        if any(start <= line <= end for start, end in docstrings):
            return SHAPE_DOCSTRING, DOCUMENTARY
        if line in comments:
            return SHAPE_COMMENT, DOCUMENTARY
        enclosing = [span for span in functions if span[0] <= line <= span[1]]
        if enclosing:
            innermost = min(enclosing, key=lambda span: span[1] - span[0])
            if _takes_tmp_path(innermost[2]):
                return SHAPE_TMP_PATH_SYNTHETIC, SURVIVES
        return default_shape, LIVE

    found: list[Coupling] = []
    seen: set[tuple[int, str, str]] = set()

    # `/`-chain reconstructions first, so a constructed path is reported as a
    # construction rather than as two unrelated segment literals.
    nested = {
        id(node.left)
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.left, ast.BinOp)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue
        if id(node) in nested:
            continue
        chain = _div_chain(node)
        if chain is None:
            continue
        for target in targets:
            if target in chain:
                shape, liveness = classify(node.lineno, SHAPE_PATH_CONSTRUCTION)
                key = (node.lineno, target, shape)
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    Coupling(
                        file=rel,
                        line=node.lineno,
                        retiring_path=target,
                        shape=shape,
                        liveness=liveness,
                        owner=resolve_owner(rel, target),
                        note=f"constructed as `{chain}`",
                    )
                )
                break

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        for target in targets:
            # Every occurrence, at the line it actually sits on. A docstring is
            # one `Constant` whose `lineno` is where the quotes open, so
            # reporting `node.lineno` would file a hit sixty lines below its
            # own line number and make the row unusable to its owner.
            start = 0
            while True:
                index = node.value.find(target, start)
                if index == -1:
                    break
                start = index + 1
                line = node.lineno + node.value.count("\n", 0, index)
                default = shapes.get(id(node), SHAPE_STRING_LITERAL)
                shape, liveness = classify(node.lineno, default)
                key = (line, target, shape)
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    Coupling(
                        file=rel,
                        line=line,
                        retiring_path=target,
                        shape=shape,
                        liveness=liveness,
                        owner=resolve_owner(rel, target),
                    )
                )

    return found


# ---------------------------------------------------------------------------
# Detector 1b — the non-Python token pass. Deliberately coarser than the AST
# pass: it has no parser and reads a line at a time.
# ---------------------------------------------------------------------------

_MARKDOWN_LINK_RE = re.compile(r"\]\([^)]*\)")
_SNIPPET_RE = re.compile(r"-{2,}8<-{2,}")
_HASH_COMMENT_SUFFIXES = frozenset({".yml", ".yaml", ".toml", ".cfg", ".ini", ".sh"})


def _text_shape(path: pathlib.Path, line: str, offset: int) -> tuple[str, str]:
    """Shape and liveness of a token hit in a non-Python file."""
    rel = relative(path)
    suffix = path.suffix.lower()

    if path.name == "Makefile" or suffix in _HASH_COMMENT_SUFFIXES:
        hash_at = line.find("#")
        if hash_at != -1 and hash_at < offset:
            return SHAPE_COMMENT, DOCUMENTARY
        if path.name == "Makefile":
            return SHAPE_MAKEFILE_RECIPE, LIVE
        if rel.startswith(".github/workflows/"):
            return SHAPE_WORKFLOW_STEP, LIVE
        return SHAPE_CONFIG_TOKEN, LIVE

    if suffix == ".md":
        if _SNIPPET_RE.search(line):
            return SHAPE_SNIPPET_INCLUDE, LIVE
        for match in _MARKDOWN_LINK_RE.finditer(line):
            if match.start() < offset < match.end():
                return SHAPE_MARKDOWN_LINK, LIVE
        return SHAPE_PROSE, DOCUMENTARY

    return SHAPE_CONFIG_TOKEN, LIVE


def text_hits(path: pathlib.Path, source: str) -> list[Coupling]:
    """Every retiring-path token in a non-Python file, classified by line."""
    rel = relative(path)
    targets = retiring_paths()
    found: list[Coupling] = []
    for number, line in enumerate(source.splitlines(), start=1):
        seen: set[str] = set()
        for target in targets:
            offset = line.find(target)
            if offset == -1 or target in seen:
                continue
            if any(target != other and target in other for other in seen):
                continue
            seen.add(target)
            shape, liveness = _text_shape(path, line, offset)
            found.append(
                Coupling(
                    file=rel,
                    line=number,
                    retiring_path=target,
                    shape=shape,
                    liveness=liveness,
                    owner=resolve_owner(rel, target),
                )
            )
    return found


# ---------------------------------------------------------------------------
# Shared machinery for detectors 2-4: loading a gate module and reading its
# module-level scanned-tree constants.
# ---------------------------------------------------------------------------

#: Top-level repo trees a scanned-tree tuple may name. A tuple of strings is
#: only treated as a scanned-tree constant if every element is one of these.
REPO_TREES: frozenset[str] = frozenset(
    {"src", "runtime", "examples", "tests", "tools", "perf", "public", "docs"}
)


def _module_tree_constants(tree: ast.Module) -> dict[str, tuple[str, ...]]:
    """Module-level tuples naming repo trees, e.g. `BINDER_SCANNED_TREES`."""
    constants: dict[str, tuple[str, ...]] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            names = [t.id for t in statement.targets if isinstance(t, ast.Name)]
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            names = [statement.target.id]
            value = statement.value if statement.value is not None else ast.Constant(0)
        else:
            continue
        if not isinstance(value, (ast.Tuple, ast.List)) or not value.elts:
            continue
        elements = [
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ]
        if len(elements) != len(value.elts):
            continue
        if not all(element in REPO_TREES for element in elements):
            continue
        for name in names:
            constants[name] = tuple(elements)
    return constants


def _load_module(path: pathlib.Path) -> types.ModuleType | None:
    """Import a gate module by file location, without polluting `sys.modules`."""
    name = "_retirement_sweep_" + relative(path).replace("/", "_").removesuffix(".py")
    rel = relative(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        record_unexaminable(rel, "import", "no loader for this file location")
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - recorded, then refused by main()
        # NOT "yields no rows". A module that will not import yields no rows
        # AND no evidence that it had none to yield; the caller cannot tell the
        # two apart, so the run refuses instead of reporting a smaller total.
        record_unexaminable(rel, "import", exc)
        return None
    return module


def _paths_of(result: Any) -> list[str]:
    """Repo-relative paths carried by a scan result, whatever its element shape.

    The floor-backed scans return `list[tuple[Path, node]]` or `list[str]` of
    `path:line` sites; both are path-bearing, which is what makes a per-path
    witness distribution measurable rather than guessed.
    """
    paths: list[str] = []
    for element in result:
        candidate: Any = element
        if isinstance(element, tuple) and element:
            candidate = element[0]
        if isinstance(candidate, pathlib.Path):
            paths.append(relative(candidate.resolve()))
        elif isinstance(candidate, str):
            paths.append(candidate.split(":", 1)[0])
    return paths


def _distribution(paths: Iterable[str]) -> dict[str, int]:
    """How many of `paths` lie under each retiring path."""
    counts: dict[str, int] = {}
    for item in paths:
        entry = containing_retirement(item)
        if entry is not None:
            counts[entry.path] = counts.get(entry.path, 0) + 1
    return counts


def _first_break(total: int, floor: int, counts: dict[str, int]) -> str:
    """The first wave at which `total` drops below `floor`, as `wave N (plan)`.

    Measured on the tree as it stands. Waves 3-7 create new examples, so a
    floor that breaks here may have headroom by the wave that deletes into it —
    which is exactly why later plans re-run this sweep instead of reading this
    file.
    """
    remaining = total
    for wave in sorted({wave_for(path) for path in counts}):
        for path, count in counts.items():
            if wave_for(path) == wave:
                remaining -= count
        if remaining < floor:
            owners = sorted({owner_for(p) for p in counts if wave_for(p) == wave})
            return f"wave {wave} ({', '.join(owners)})"
    return "no wave in this phase"


def _owner_of_last_witness(counts: dict[str, int]) -> tuple[str, str]:
    """Owner and path of the last-retiring witness — who re-floors it finally."""
    if not counts:
        return UNOWNED, ""
    last = max(sorted(counts), key=wave_for)
    return owner_for(last), last


# ---------------------------------------------------------------------------
# Detectors 2 and 3 — count constants and their scan functions.
#
# Scope: floors, i.e. a module-level `MINIMUM_*` integer compared against
# `len(<scan function>())` in a test body. A module-level scan function with no
# floor asserts no count, so there is no count to break; the failure such a
# scan would produce surfaces through whichever floor consumes it.
# ---------------------------------------------------------------------------

FLOOR_PREFIX = "MINIMUM_"

#: The trees whose gate modules carry count couplings. Data, so a later plan
#: widens the search without editing the detector.
COUNT_COUPLING_TREES: tuple[str, ...] = ("tests/products",)


@dataclasses.dataclass(frozen=True)
class Floor:
    """A `MINIMUM_*` constant, its value, its line and its scan function."""

    name: str
    value: int
    line: int
    scan: str
    scan_line: int


def _floors(tree: ast.Module) -> list[Floor]:
    """Every `MINIMUM_*` floor paired with the scan whose length it bounds."""
    constants: dict[str, tuple[int, int]] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant):
            if isinstance(statement.value.value, int) and not isinstance(
                statement.value.value, bool
            ):
                for target in statement.targets:
                    if isinstance(target, ast.Name) and target.id.startswith(
                        FLOOR_PREFIX
                    ):
                        constants[target.id] = (statement.value.value, target.lineno)

    definitions = {
        node.name: node.lineno
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    floors: list[Floor] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bindings: dict[str, str] = {}
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Assign)
                and isinstance(inner.value, ast.Call)
                and isinstance(inner.value.func, ast.Name)
                and not inner.value.args
            ):
                for target in inner.targets:
                    if isinstance(target, ast.Name):
                        bindings[target.id] = inner.value.func.id
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Compare) or len(inner.comparators) != 1:
                continue
            if not isinstance(inner.ops[0], (ast.GtE, ast.Gt)):
                continue
            right = inner.comparators[0]
            left = inner.left
            if not isinstance(right, ast.Name) or right.id not in constants:
                continue
            if (
                not isinstance(left, ast.Call)
                or not isinstance(left.func, ast.Name)
                or left.func.id != "len"
                or not left.args
            ):
                continue
            argument = left.args[0]
            scan: str | None = None
            if isinstance(argument, ast.Name):
                scan = bindings.get(argument.id)
            elif isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name):
                scan = argument.func.id
            if scan is None or scan not in definitions:
                continue
            value, line = constants[right.id]
            floors.append(
                Floor(
                    name=right.id,
                    value=value,
                    line=line,
                    scan=scan,
                    scan_line=definitions[scan],
                )
            )
    return floors


def _count_roots(roots: Sequence[pathlib.Path] | None) -> list[pathlib.Path]:
    if roots is not None:
        return [root for root in roots if root.is_dir()]
    return [
        REPO_ROOT / name for name in COUNT_COUPLING_TREES if (REPO_ROOT / name).is_dir()
    ]


def count_coupling_rows(roots: Sequence[pathlib.Path] | None = None) -> list[Coupling]:
    """One `count-constant` row and one `count-scan-function` row per floor."""
    rows: list[Coupling] = []
    for root in _count_roots(roots):
        for path in sorted(root.rglob("test_*.py")):
            source = read_text(path)
            if source is None:
                continue
            try:
                parsed = ast.parse(source)
            except SyntaxError:
                continue
            floors = _floors(parsed)
            if not floors:
                continue
            module = _load_module(path)
            if module is None:
                continue
            rel = relative(path)
            for floor in floors:
                scan = getattr(module, floor.scan, None)
                if not callable(scan):
                    continue
                try:
                    result = scan()
                except Exception as exc:  # noqa: BLE001 - recorded, then refused
                    # An unrunnable scan is not a floor with no witnesses.
                    record_unexaminable(f"{rel}::{floor.scan}", "scan", exc)
                    continue
                paths = _paths_of(result)
                counts = _distribution(paths)
                if not counts:
                    continue
                total = len(paths)
                under = sum(counts.values())
                owner, last = _owner_of_last_witness(counts)
                spread = ", ".join(
                    f"{name}={counts[name]}" for name in sorted(counts)
                )
                note = (
                    f"floor {floor.value}, {total} witnesses, headroom"
                    f" {total - floor.value}; under retiring paths: {spread};"
                    f" first break: {_first_break(total, floor.value, counts)}"
                )
                rows.append(
                    Coupling(
                        file=rel,
                        line=floor.line,
                        retiring_path=last,
                        shape=SHAPE_COUNT_CONSTANT,
                        liveness=LIVE,
                        owner=REFERENCING_FILE_OWNERS.get(rel, owner),
                        witnesses=str(under),
                        note=f"`{floor.name}` — {note}",
                    )
                )
                rows.append(
                    Coupling(
                        file=rel,
                        line=floor.scan_line,
                        retiring_path=last,
                        shape=SHAPE_COUNT_SCAN_FUNCTION,
                        liveness=LIVE,
                        owner=REFERENCING_FILE_OWNERS.get(rel, owner),
                        witnesses=str(under),
                        note=f"`{floor.scan}()` feeds `{floor.name}` — {note}",
                    )
                )
    return rows


# ---------------------------------------------------------------------------
# Detector 4 — inline tree-witness assertions.
#
# An assertion whose evidence base is a scan written INLINE IN THE TEST BODY,
# keyed off a module-level scanned-tree tuple, with neither a `MINIMUM_*`
# constant nor a named module-level scan function. Two dead ends, both
# measured: the witness path appears in the module only inside a docstring, so
# a token pass cannot find it; and the scan is not a module-level function, so
# detector 3 cannot find it either.
#
# Witnesses are measured empirically. The module's own enumeration helper is
# replaced with one restricted to a single retiring path and the test is run:
# it passing means that path independently sustains the assertion. Running it
# with every retiring path excluded answers the question that decides whether
# there is a coupling at all — does the assertion still hold on what survives?
# ---------------------------------------------------------------------------


def _inline_scans(node: ast.AST, constants: dict[str, tuple[str, ...]]) -> list[tuple[str, str]]:
    """`(helper, tree-constant)` pairs called directly inside a test body."""
    pairs: list[tuple[str, str]] = []
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call) or not isinstance(inner.func, ast.Name):
            continue
        for argument in inner.args:
            if isinstance(argument, ast.Name) and argument.id in constants:
                pairs.append((inner.func.id, argument.id))
    return pairs


def _under(target: str) -> Callable[[str], bool]:
    """A predicate holding for repo-relative paths inside `target`."""

    def keep(item: str) -> bool:
        return item == target or item.startswith(target + "/")

    return keep


def _restricted(
    original: Callable[..., list[pathlib.Path]], keep: Callable[[str], bool]
) -> Callable[..., list[pathlib.Path]]:
    def wrapper(*args: Any, **kwargs: Any) -> list[pathlib.Path]:
        return [
            path
            for path in original(*args, **kwargs)
            if keep(relative(path.resolve()))
        ]

    return wrapper


def inline_tree_witness_rows(
    roots: Sequence[pathlib.Path] | None = None,
) -> list[Coupling]:
    """One row per assertion whose sole evidence lies under a retiring path."""
    rows: list[Coupling] = []
    for root in _count_roots(roots):
        for path in sorted(root.rglob("test_*.py")):
            source = read_text(path)
            if source is None:
                continue
            try:
                parsed = ast.parse(source)
            except SyntaxError:
                continue
            constants = _module_tree_constants(parsed)
            if not constants:
                continue
            module: types.ModuleType | None = None
            rel = relative(path)
            for node in parsed.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not node.name.startswith("test_"):
                    continue
                arguments = node.args
                if arguments.args or arguments.posonlyargs or arguments.kwonlyargs:
                    continue
                pairs = _inline_scans(node, constants)
                if not pairs:
                    continue
                helper, constant = pairs[0]
                if module is None:
                    module = _load_module(path)
                if module is None:
                    continue
                original = getattr(module, helper, None)
                test = getattr(module, node.name, None)
                if not callable(original) or not callable(test):
                    continue

                def run(keep: Callable[[str], bool]) -> bool:
                    setattr(module, helper, _restricted(original, keep))
                    try:
                        test()
                    except AssertionError:
                        return False
                    except Exception as exc:  # noqa: BLE001 - recorded, then refused
                        # An AssertionError above is a MEASUREMENT: the test
                        # failed under restriction, which is the witness. Any
                        # other exception is the absence of a measurement, and
                        # returning False here reports it as one.
                        record_unexaminable(
                            f"{relative(path)}::{node.name}", "sabotage-run", exc
                        )
                        return False
                    finally:
                        setattr(module, helper, original)
                    return True

                survivors = run(lambda item: containing_retirement(item) is None)
                if survivors:
                    continue  # headroom outside every retiring path: no coupling

                sustaining = [
                    entry.path
                    for entry in sorted(RETIREMENT_SCHEDULE, key=lambda e: e.path)
                    if run(_under(entry.path))
                ]
                if not sustaining:
                    continue
                counts = {name: 1 for name in sustaining}
                owner, last = _owner_of_last_witness(counts)
                rows.append(
                    Coupling(
                        file=rel,
                        line=node.lineno,
                        retiring_path=last,
                        shape=SHAPE_INLINE_TREE_WITNESS,
                        liveness=LIVE,
                        owner=REFERENCING_FILE_OWNERS.get(rel, owner),
                        witnesses=str(len(sustaining)),
                        note=(
                            f"`{node.name}` scans `{constant}` inline via"
                            f" `{helper}()`; no floor constant and no module-level"
                            " scan function. Sustained only by:"
                            f" {', '.join(sustaining)}. Measured by execution —"
                            " the witness appears in this module only inside a"
                            " docstring."
                        ),
                    )
                )
    return rows


# ---------------------------------------------------------------------------
# Detector 5 — indirect executions.
#
# A test under `tests/` runs a suite, script or package OUTSIDE `tests/`, and
# THAT code resolves a retiring path. Neither hop carries a path token; the
# retiring path is constructed from `__file__`. The always-on failure surfaces
# at the test, so the row is reported there with the intermediate file named.
# ---------------------------------------------------------------------------

_SUBPROCESS_CALLS = frozenset({"Popen", "run", "call", "check_call", "check_output"})


def _argv_prefixes(node: ast.Call) -> list[str]:
    """Repo-relative path prefixes named in a subprocess argv."""
    prefixes: list[str] = []
    for argument in [*node.args, *(k.value for k in node.keywords)]:
        elements: list[ast.expr] = []
        if isinstance(argument, (ast.List, ast.Tuple)):
            elements = list(argument.elts)
        else:
            elements = [argument]
        for element in elements:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                prefixes.append(element.value)
            elif isinstance(element, ast.JoinedStr):
                literal = "".join(
                    part.value
                    for part in element.values
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                )
                if literal:
                    prefixes.append(literal)
    return prefixes


def _is_subprocess_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr in _SUBPROCESS_CALLS
    return isinstance(func, ast.Name) and func.id in _SUBPROCESS_CALLS


def _outside_tests_root(token: str, repo_root: pathlib.Path) -> pathlib.Path | None:
    """The repo path a subprocess argv token names, if outside `tests/`.

    Resolution is exact: the token must name a directory or a module that
    exists. Walking up to the nearest existing parent was measured to turn
    every `perf.synth.*` import into a claim on `perf/suites/crossproc`, which
    is a false positive of the shape this detector exists to avoid producing.
    """
    cleaned = token.strip().strip("/")
    if not cleaned or cleaned.startswith("-") or cleaned.startswith("tests"):
        return None
    head = cleaned.split("/", 1)[0]
    if head not in REPO_TREES:
        return None
    candidate = repo_root / cleaned
    if candidate.is_dir():
        return candidate
    module = candidate.with_suffix(".py")
    return module if module.is_file() else None


def _constructed_retiring_paths(root: pathlib.Path) -> list[tuple[str, str]]:
    """`(intermediate file, retiring path)` for constructions under `root`."""
    found: list[tuple[str, str]] = []
    targets = retiring_paths()
    sources = sorted(root.rglob("*.py")) if root.is_dir() else [root]
    for path in sources:
        source = read_text(path)
        if source is None:
            continue
        try:
            parsed = ast.parse(source)
        except SyntaxError:
            continue
        docstrings = _docstring_spans(parsed)
        comments = _comment_lines(source)
        for node in ast.walk(parsed):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
                continue
            chain = _div_chain(node)
            if chain is None:
                continue
            if any(start <= node.lineno <= end for start, end in docstrings):
                continue
            if node.lineno in comments:
                continue
            for target in targets:
                if target in chain:
                    found.append((relative(path), target))
                    break
    return sorted(set(found))


def _package_roots(parsed: ast.Module, repo_root: pathlib.Path) -> list[pathlib.Path]:
    """Repo paths reached by an import of a package rooted outside `tests/`.

    `imported_module_names` and `submodule_import_names` are both used: the
    second exists because of Phase 15.4 CR-02, where a `from pkg import sub`
    reached a module the first form does not name.
    """
    roots: list[pathlib.Path] = []
    names: set[str] = set()
    for node in ast.walk(parsed):
        names.update(imported_module_names(node))
        names.update(submodule_import_names(node))
    for name in sorted(names):
        head = name.split(".", 1)[0]
        if head in {"tests", ""} or head not in REPO_TREES:
            continue
        resolved = _outside_tests_root("/".join(name.split(".")), repo_root)
        if resolved is not None:
            roots.append(resolved)
    return roots


def indirect_execution_rows(
    tests_root: pathlib.Path | None = None,
    repo_root: pathlib.Path | None = None,
) -> list[Coupling]:
    """One row per always-on test that executes code resolving a retiring path."""
    base = repo_root if repo_root is not None else REPO_ROOT
    root = tests_root if tests_root is not None else base / "tests"
    if not root.is_dir():
        return []
    rows: list[Coupling] = []
    for path in sorted(root.rglob("test_*.py")):
        source = read_text(path)
        if source is None:
            continue
        try:
            parsed = ast.parse(source)
        except SyntaxError:
            continue
        rel = relative(path)
        candidates: list[tuple[int, pathlib.Path]] = []
        for node in ast.walk(parsed):
            if isinstance(node, ast.Call) and _is_subprocess_call(node):
                for token in _argv_prefixes(node):
                    target_root = _outside_tests_root(token, base)
                    if target_root is not None:
                        candidates.append((node.lineno, target_root))
        for target_root in _package_roots(parsed, base):
            candidates.append((1, target_root))

        emitted: set[tuple[str, str]] = set()
        for line, target_root in sorted(candidates, key=lambda item: item[0]):
            for intermediate, target in _constructed_retiring_paths(target_root):
                key = (intermediate, target)
                if key in emitted:
                    continue
                emitted.add(key)
                rows.append(
                    Coupling(
                        file=rel,
                        line=line,
                        retiring_path=target,
                        shape=SHAPE_INDIRECT_EXECUTION,
                        liveness=LIVE,
                        owner=REFERENCING_FILE_OWNERS.get(rel, owner_for(target)),
                        intermediate=intermediate,
                        note=(
                            f"runs `{relative(target_root)}` out of process;"
                            f" `{intermediate}` constructs the retiring path from"
                            " `__file__`, so neither hop carries a path token"
                        ),
                    )
                )
    return rows


# ---------------------------------------------------------------------------
# The sweep.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Sweep:
    """Everything one run measures."""

    rows: tuple[Coupling, ...]
    files_scanned: int
    excluded: tuple[tuple[str, int, str], ...]
    retiring_source_hits: int
    unexaminable: tuple[Unexaminable, ...] = ()

    @property
    def unowned(self) -> tuple[Coupling, ...]:
        return tuple(row for row in self.rows if row.owner == UNOWNED)


def sweep() -> Sweep:
    """Measure every live coupling to every retiring path, repo-wide."""
    reset_unexaminable()
    rows: list[Coupling] = []
    excluded_counts: dict[str, tuple[int, str]] = {}
    retiring_source_hits = 0
    files_scanned = 0

    for path in iter_source_files():
        source = read_text(path)
        if source is None:
            continue
        files_scanned += 1
        rel = relative(path)
        hits = (
            python_hits(path, source)
            if path.suffix == ".py"
            else text_hits(path, source)
        )
        if not hits:
            continue

        reason = exclusion_reason(rel)
        if reason is not None:
            count, _ = excluded_counts.get(rel, (0, reason))
            excluded_counts[rel] = (count + len(hits), reason)
            continue

        source_entry = containing_retirement(rel)
        for hit in hits:
            if source_entry is not None:
                # A reference from a file that is itself deleted dies with it —
                # UNLESS the path it names goes first, which leaves the window
                # between the two waves with a dangling reference.
                if wave_for(hit.retiring_path) >= source_entry.wave:
                    retiring_source_hits += 1
                    continue
                rows.append(
                    dataclasses.replace(
                        hit,
                        note=(
                            f"{hit.note + '; ' if hit.note else ''}cross-wave: this"
                            f" file retires at wave {source_entry.wave}, the path it"
                            f" names at wave {wave_for(hit.retiring_path)}"
                        ),
                    )
                )
                continue
            rows.append(hit)

    rows.extend(count_coupling_rows())
    rows.extend(inline_tree_witness_rows())
    rows.extend(indirect_execution_rows())

    excluded = tuple(
        (name, count, reason)
        for name, (count, reason) in sorted(excluded_counts.items())
    )
    return Sweep(
        rows=tuple(sorted(rows, key=lambda row: row.sort_key())),
        files_scanned=files_scanned,
        excluded=excluded,
        retiring_source_hits=retiring_source_hits,
        unexaminable=unexaminable(),
    )


# ---------------------------------------------------------------------------
# The report.
# ---------------------------------------------------------------------------

SWEPT_TREES: tuple[str, ...] = ("examples/", "tests/examples/", "public/")


def outside_swept_trees(rows: Sequence[Coupling]) -> list[Coupling]:
    """Rows the § A.1/§ A.2 inventory could not have found — the whole point."""
    return [
        row for row in rows if not any(row.file.startswith(t) for t in SWEPT_TREES)
    ]


def _cell(text: str) -> str:
    return text.replace("|", r"\|")


def render(result: Sweep) -> str:
    """The inventory, deterministic: no timestamps, no absolute paths."""
    rows = result.rows
    files = sorted({row.file for row in rows})
    outside = outside_swept_trees(rows)
    shapes: dict[str, int] = {}
    for row in rows:
        shapes[row.shape] = shapes.get(row.shape, 0) + 1
    owners: dict[str, int] = {}
    for row in rows:
        owners[row.owner] = owners.get(row.owner, 0) + 1

    lines: list[str] = []
    lines.append("# Retirement couplings — every live reference to a retiring path")
    lines.append("")
    lines.append(
        "Generated by `tools/retirement_sweep.py --report`. Do not hand-edit: the"
        " sweep rewrites this file, and plans 16-15, 16-17 and 16-18 re-run it"
        " and diff rather than trusting this snapshot."
    )
    lines.append("")
    lines.append(
        "The retirement inventory in `16-RESEARCH.md` § A.1/§ A.2 swept"
        " `examples/`, `tests/examples/` and `public/` only, while"
        " `[tool.pytest] testpaths = [\"tests\"]` puts the whole of `tests/` in"
        " `make ci`. This inventory is repo-wide, and every row carries the plan"
        " that must act on it before its subject is deleted."
    )
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(
        "The walk covers the whole repository from the sweep's own location."
        " The number of files it read is printed by the command rather than"
        " recorded here, so that adding an unrelated file to the tree does not"
        " make this inventory stale; what does make it stale is a change to a"
        " coupling, which is the thing later waves must re-measure."
    )
    lines.append("")
    lines.append(f"- Coupling rows: **{len(rows)}** across **{len(files)}** files")
    lines.append(
        f"- Rows outside `examples/`, `tests/examples/` and `public/`:"
        f" **{len(outside)}** across"
        f" **{len({row.file for row in outside})}** files"
    )
    lines.append(
        f"- References from inside a retiring path to a path that retires no"
        f" earlier, dropped because they are deleted with their source:"
        f" **{result.retiring_source_hits}**"
    )
    lines.append("")
    lines.append("Rows by owning plan:")
    lines.append("")
    lines.append("| Owning plan | Rows |")
    lines.append("| --- | --- |")
    for owner in sorted(owners):
        lines.append(f"| {owner} | {owners[owner]} |")
    lines.append("")
    lines.append("Rows by coupling shape:")
    lines.append("")
    lines.append("| Shape | Rows |")
    lines.append("| --- | --- |")
    for shape in sorted(shapes):
        lines.append(f"| `{shape}` | {shapes[shape]} |")
    lines.append("")

    lines.append("## Reading the columns")
    lines.append("")
    lines.append(
        "- **Liveness** — `live` means deleting the subject breaks something;"
        " `documentary` means it leaves stale text in a docstring, a comment or"
        " prose; `survives` means the reference is a synthetic token written"
        " into a `tmp_path` tree and never resolved on disk, so it outlives its"
        " subject rather than breaking. All three carry an owner: a documentary"
        " row is lower severity, not unowned, and four of the files this sweep"
        " is required to find carry only documentary hits."
    )
    lines.append(
        "- **Witnesses** — for a count coupling, how many of the sites the scan"
        " finds lie under a retiring path; for an inline tree-witness"
        " assertion, how many retiring paths independently sustain it. A"
        " coupling with one witness is materially more urgent than one with"
        " headroom."
    )
    lines.append(
        "- **Intermediate** — for an indirect execution, the file between the"
        " always-on test and the retiring path. The row is filed against the"
        " test, because that is where the build goes red."
    )
    lines.append(
        "- **Owner** — the plan that must act. For a count coupling it is the"
        " plan retiring the *last* witness, because that is the plan after"
        " which the floor takes its final value; the note records the wave at"
        " which the floor first breaks on the tree as measured, which can be"
        " earlier."
    )
    lines.append("")

    lines.append("## Couplings")
    lines.append("")
    lines.append(
        "| File | Line | Retiring path | Shape | Liveness | Witnesses |"
        " Intermediate | Owner | Note |"
    )
    lines.append("| --- | ---: | --- | --- | --- | ---: | --- | --- | --- |")
    for row in rows:
        lines.append(
            "| `{file}` | {line} | `{path}` | `{shape}` | {liveness} |"
            " {witnesses} | {intermediate} | {owner} | {note} |".format(
                file=_cell(row.file),
                line=row.line,
                path=_cell(row.retiring_path),
                shape=_cell(row.shape),
                liveness=row.liveness,
                witnesses=_cell(row.witnesses),
                intermediate=(
                    f"`{_cell(row.intermediate)}`" if row.intermediate != "-" else "-"
                ),
                owner=row.owner,
                note=_cell(row.note) if row.note else "",
            )
        )
    lines.append("")

    lines.append("## Measured but not assigned")
    lines.append("")
    lines.append(
        "Append-only records and documents no plan in this phase may edit. They"
        " name retiring paths as history, so they are counted here rather than"
        " filed as work. Each entry is a named exclusion in"
        " `EXCLUDED_FROM_ASSIGNMENT` with its reason, so the exclusion is a"
        " decision on the record rather than a silence."
    )
    lines.append("")
    lines.append("| File | Hits | Reason |")
    lines.append("| --- | ---: | --- |")
    for name, count, reason in result.excluded:
        lines.append(f"| `{_cell(name)}` | {count} | {reason} |")
    lines.append("")

    lines.append("## Re-running")
    lines.append("")
    lines.append("```")
    lines.append("PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report")
    lines.append("```")
    lines.append("")
    lines.append(
        "The command is byte-deterministic: two runs against the same tree leave"
        " this file identical. It exits non-zero if any row has no owning plan."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep the repository for live couplings to the paths Phase 16"
            " retires, and assign each to an owning plan."
        )
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="rewrite docs/surface/examples/RETIREMENT-COUPLINGS.md",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = sweep()

    # The refusal comes BEFORE the write, deliberately. A run that could not
    # examine every subject has measured what happened to load, not what is
    # coupled, and rendering that over the committed report replaces a good
    # inventory with a smaller one -- while the staleness gate then reports the
    # CORRECT report as stale. An exit code alone does not protect the file.
    if result.unexaminable:
        print(
            f"REFUSING: {len(result.unexaminable)} subject(s) could not be"
            " examined, so this count is not a measurement of coupling --"
            " it is a measurement of what happened to load."
            + (" The report was NOT written." if args.report else ""),
            file=sys.stderr,
        )
        for item in result.unexaminable:
            print(item.line(), file=sys.stderr)
        return 1

    if args.report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(render(result), encoding="utf-8")
        print(f"wrote {relative(REPORT_PATH)}")

    outside = outside_swept_trees(result.rows)
    print(
        f"{len(result.rows)} coupling rows across"
        f" {len({row.file for row in result.rows})} files"
        f" ({len(outside)} rows outside the three swept trees);"
        f" {result.files_scanned} files scanned"
    )

    if result.unowned:
        print("rows with no owning plan:", file=sys.stderr)
        for row in result.unowned:
            print(f"  {row.file}:{row.line} -> {row.retiring_path}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
