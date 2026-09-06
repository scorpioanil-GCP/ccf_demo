"""Archive runners are marked ``archived``, and only archive runners are — D-IMPL-265.

Dave's ruling (2026-09-06, verbatim in ``24.7-RULINGS.md`` §10): *"archive/examples/
contains retired examples whose usage model is not supported guidance. They are
preserved for historical/technical reference but are not compatibility consumers
of the current SDK. No archived source is modified to accommodate 24.7. Tests whose
only purpose is exercising those retired examples are removed from the
release-gating denominator or explicitly marked archived/non-gating. HW/CP
examples remain the supported example and diagnostic surfaces."*

The harness realizes that as a registered ``archived`` marker (``pyproject.toml``)
and a root-``conftest`` hook that DESELECTS marked items unless ``--run-archived``
is passed (``tests/conftest.py``). What this module defends is the category
boundary, in both directions:

* **Every archive RUNNER carries the marker.** A test module that executes a
  retired program — loads it with ``importlib.util.spec_from_file_location`` /
  ``runpy`` or spawns it with ``subprocess`` / a ``_spawn`` helper — and whose
  target is one of the archive's program entry points (``run.py``, ``serve.py``,
  ``producer_child.py``: the three files that hold the twelve archived
  ``build_replay_record`` sites D-IMPL-265 names) must be marked at module level.
  An unmarked runner would put a retired example back into the release gate.
* **Only archive runners carry the marker.** A marked module that does not
  execute an archive program would be hiding a live SDK test behind the
  non-gating category. Guards that merely *read* the archive — retirement
  guards, schema-header gates, README-template readers, the demo-generator and
  fixture-schema smoke tests — are the supported surface's own tests and stay
  gating.

The classifier is one AST walk with three independent kinds of evidence (an
``archive/examples`` path expression, a load-or-spawn call, a program-file
target), and a module is a runner only when all three are present; the
evidence is reported on failure so a misclassification is arguable from the
message. Docstrings are excluded from the evidence — a test that *describes*
an archive path in prose is not executing it. The controls below run the same
classifier over synthetic modules so a silent AST-pattern drift cannot pass
this guard vacuously.

The ``crossproc`` perf-smoke parameter is the one non-module case: the perf
battery's crossproc suite spawns ``archive/examples/04-cross-process/
producer_child.py`` (carry row ``24.7-C-02``), so its smoke parameter carries
the marker — and the rule here is derived, not pinned: a suite's parameter is
marked exactly when a module under ``perf/suites/<suite>/`` is an archive
runner. The day that suite is re-pointed at a supported child, this test says
the mark must come off.

This module deliberately spells the archive prefix as a component tuple and
never joins it into one literal, so the classifier does not read the guard's
own constants as an archive path.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys
import tomllib
from dataclasses import dataclass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"
PERF_SUITES_ROOT = REPO_ROOT / "perf" / "suites"
PERF_SMOKE = TESTS_ROOT / "perf_smoke" / "test_smoke.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"

#: The marker D-IMPL-265 registers, and the option that re-includes it.
MARKER = "archived"
RUN_ARCHIVED_OPTION = "--run-archived"

#: The retired tree, as path components — see the module docstring for why
#: these are never joined into a single literal here.
ARCHIVE_PREFIX: tuple[str, str] = ("archive", "examples")

#: The archive's program entry points: the files that hold the twelve archived
#: builder sites D-IMPL-265 names (00..08 ``run.py``, ``04-cross-process/
#: producer_child.py``, ``external/00-hello-context/serve.py``). Loading or
#: spawning one of these is "exercising the retired example"; loading a helper
#: beside them (``generator.py``, ``replay_server.py``) is not.
PROGRAMS: frozenset[str] = frozenset({"run.py", "serve.py", "producer_child.py"})

#: Calls that execute a module by path.
LOADERS: frozenset[str] = frozenset(
    {"spec_from_file_location", "exec_module", "run_path", "run_module"}
)
#: ``subprocess`` calls that spawn a program.
SPAWNERS: frozenset[str] = frozenset({"run", "Popen", "call", "check_call", "check_output"})
#: Example-side spawn helpers (``run_module._spawn("serve.py", ...)``).
SPAWN_HELPERS: frozenset[str] = frozenset({"_spawn"})


@dataclass(frozen=True)
class Classification:
    """One module's evidence, each kind as ``what:line`` strings."""

    path: str
    archive_paths: tuple[str, ...]
    programs: tuple[str, ...]
    executes: tuple[str, ...]
    marked: bool

    @property
    def is_runner(self) -> bool:
        return bool(self.archive_paths and self.programs and self.executes)

    def evidence(self) -> str:
        return (
            f"{self.path}: archive_paths={list(self.archive_paths)} "
            f"programs={list(self.programs)} executes={list(self.executes)} "
            f"marked={self.marked}"
        )


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _div_chain(node: ast.BinOp) -> list[str]:
    """Flatten ``a / "b" / "c"`` into its components, left to right."""
    parts: list[str] = []
    cursor: ast.expr = node
    while isinstance(cursor, ast.BinOp) and isinstance(cursor.op, ast.Div):
        right = cursor.right
        parts.append(right.value if isinstance(right, ast.Constant) and isinstance(right.value, str) else "<expr>")
        cursor = cursor.left
    parts.append(cursor.value if isinstance(cursor, ast.Constant) and isinstance(cursor.value, str) else "<expr>")
    parts.reverse()
    return parts


def _has_archive_prefix(components: list[str]) -> bool:
    return any(
        tuple(components[i : i + len(ARCHIVE_PREFIX)]) == ARCHIVE_PREFIX
        for i in range(len(components) - len(ARCHIVE_PREFIX) + 1)
    )


def _call_name(node: ast.Call) -> tuple[str | None, str]:
    """``(base, attr)`` for ``base.attr(...)``; ``(None, name)`` for ``name(...)``."""
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name):
            return base.id, func.attr
        if isinstance(base, ast.Attribute):
            return base.attr, func.attr
        return "<expr>", func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return "<expr>", "<expr>"


def _marked_archived(tree: ast.Module) -> bool:
    """A module-level ``pytestmark = pytest.mark.archived`` (or a list holding it)."""
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in statement.targets):
            continue
        for node in ast.walk(statement.value):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == MARKER
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "mark"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "pytest"
            ):
                return True
    return False


def classify(path: pathlib.Path, root: pathlib.Path = REPO_ROOT) -> Classification:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_ids(tree)
    joined_prefix = "/".join(ARCHIVE_PREFIX)
    archive_paths: dict[int, str] = {}
    programs: list[str] = []
    executes: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            components = _div_chain(node)
            if _has_archive_prefix(components):
                joined = "/".join(components)
                # Keep the longest chain per line: sub-chains of one expression
                # are also BinOps and would otherwise repeat as shorter prefixes.
                if len(joined) > len(archive_paths.get(node.lineno, "")):
                    archive_paths[node.lineno] = f"{joined}:{node.lineno}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            if joined_prefix in node.value:
                archive_paths.setdefault(node.lineno, f"{node.value[:72]!r}:{node.lineno}")
            if node.value.rsplit("/", 1)[-1] in PROGRAMS:
                programs.append(f"{node.value}:{node.lineno}")
        elif isinstance(node, ast.Call):
            base, name = _call_name(node)
            if name in LOADERS or name in SPAWN_HELPERS:
                executes.append(f"{base + '.' if base else ''}{name}:{node.lineno}")
            elif name in SPAWNERS and base == "subprocess":
                executes.append(f"subprocess.{name}:{node.lineno}")

    return Classification(
        path=path.relative_to(root).as_posix(),
        archive_paths=tuple(archive_paths[k] for k in sorted(archive_paths)),
        programs=tuple(programs),
        executes=tuple(executes),
        marked=_marked_archived(tree),
    )


def _python_modules(tree_root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        p for p in tree_root.rglob("*.py") if "__pycache__" not in p.parts and p.is_file()
    )


def classify_tree(tree_root: pathlib.Path, root: pathlib.Path = REPO_ROOT) -> dict[str, Classification]:
    return {c.path: c for c in (classify(p, root) for p in _python_modules(tree_root))}


# --- The guard --------------------------------------------------------------------


def test_every_archive_runner_is_marked_and_only_archive_runners_are() -> None:
    """Set equality between "executes an archive program" and "marked archived".

    Both directions are stated: an unmarked runner drags a retired example back
    into the release gate; a marked non-runner hides a live SDK test behind the
    non-gating category. The failure names every offender with its evidence.
    """
    table = classify_tree(TESTS_ROOT)
    runners = {path for path, c in table.items() if c.is_runner}
    marked = {path for path, c in table.items() if c.marked}
    assert runners, "the classifier found no archive runner under tests/ — vacuous"
    unmarked_runners = sorted(runners - marked)
    marked_non_runners = sorted(marked - runners)
    assert not unmarked_runners and not marked_non_runners, (
        "D-IMPL-265: archive runners must carry `pytestmark = pytest.mark.archived`, "
        "and nothing else may\n"
        "unmarked runners (execute an archive program, no marker):\n  "
        + "\n  ".join(table[p].evidence() for p in unmarked_runners)
        + "\nmarked non-runners (marker, but no archive program executed):\n  "
        + "\n  ".join(table[p].evidence() for p in marked_non_runners)
    )


def test_the_perf_smoke_parameter_is_marked_exactly_for_the_suites_that_run_the_archive() -> None:
    """Derived, not pinned: a suite's smoke parameter is ``archived`` iff a module
    under ``perf/suites/<suite>/`` executes an archive program (``24.7-C-02``)."""
    tree = ast.parse(PERF_SMOKE.read_text(encoding="utf-8"), filename=str(PERF_SMOKE))
    suites: dict[str, bool] = {}
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SUITES" for t in statement.targets)
        ):
            continue
        assert isinstance(statement.value, (ast.Tuple, ast.List))
        for element in statement.value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                suites[element.value] = False
            elif isinstance(element, ast.Call) and _call_name(element) == ("pytest", "param"):
                first = element.args[0]
                assert isinstance(first, ast.Constant) and isinstance(first.value, str)
                marks = [k.value for k in element.keywords if k.arg == "marks"]
                suites[first.value] = any(
                    isinstance(n, ast.Attribute) and n.attr == MARKER
                    for m in marks
                    for n in ast.walk(m)
                )
            else:  # pragma: no cover — a shape this guard cannot read must fail loudly
                raise AssertionError(f"unreadable SUITES element at line {element.lineno}")
    assert suites, f"no SUITES assignment found in {PERF_SMOKE}"

    should_be_marked = {
        suite: any(c.is_runner for c in classify_tree(PERF_SUITES_ROOT / suite).values())
        for suite in suites
    }
    assert suites == should_be_marked, (
        "D-IMPL-265 / 24.7-C-02: the smoke parameter carries `archived` exactly when its "
        f"suite executes an archive program\n  marked now: {suites}\n  should be: {should_be_marked}"
    )
    assert any(should_be_marked.values()), "no perf suite executes the archive — vacuous"


def test_the_marker_is_registered_citing_the_ruling() -> None:
    markers = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["pytest"][
        "ini_options"
    ]["markers"]
    registered = [m for m in markers if m.startswith(f"{MARKER}:")]
    assert len(registered) == 1, f"expected one `{MARKER}:` marker, found {registered}"
    assert "D-IMPL-265" in registered[0] and RUN_ARCHIVED_OPTION in registered[0]


def test_the_hook_deselects_by_default_and_run_archived_reincludes() -> None:
    """The hook as executed: one runner module collected in a child pytest,
    with and without the option. The module is the classifier's first runner,
    so this test pins no file name of its own."""
    table = classify_tree(TESTS_ROOT)
    runner = sorted(p for p, c in table.items() if c.is_runner)[0]

    def collect(*extra: str) -> str:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", runner, "--collect-only", "-q", "-p", "no:cacheprovider", *extra],
            cwd=REPO_ROOT,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout + completed.stderr

    default = collect()
    assert " deselected" in default, f"default collection of {runner} did not deselect:\n{default}"
    assert "::" not in default, f"default collection of {runner} still lists ids:\n{default}"

    reincluded = collect(RUN_ARCHIVED_OPTION)
    assert " deselected" not in reincluded, f"{RUN_ARCHIVED_OPTION} still deselected:\n{reincluded}"
    assert f"{runner}::" in reincluded, f"{RUN_ARCHIVED_OPTION} collected no id from {runner}:\n{reincluded}"


# --- Controls: the classifier on synthetic modules ---------------------------------


def _write(base: pathlib.Path, rel: str, source: str) -> pathlib.Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


_RUNNER = (
    "import importlib.util\nimport pathlib\nimport pytest\n"
    "REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]\n"
    'EXAMPLE = REPO_ROOT / "archive" / "examples" / "00-quickstart" / "run.py"\n'
    "def load():\n"
    '    spec = importlib.util.spec_from_file_location("x", EXAMPLE)\n'
    "    return spec\n"
)
_MARK = "pytestmark = pytest.mark.archived\n"
_READER = (
    "import pathlib\n"
    "REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]\n"
    'SOURCE = REPO_ROOT / "archive" / "examples" / "external" / "00-hello-context" / "run.py"\n'
    "def test_reads():\n"
    '    assert "README_HEADINGS" in SOURCE.read_text()\n'
)
_HELPER_LOADER = (
    "import importlib.util\nimport pathlib\n"
    "REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]\n"
    'EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "08-e2e-demo"\n'
    "def load():\n"
    '    return importlib.util.spec_from_file_location("g", EXAMPLE_DIR / "generator.py")\n'
)
_PROSE_ONLY = (
    '"""Describes ' + "/".join(ARCHIVE_PREFIX) + '/00-quickstart/run.py, never touches it."""\n'
    "import subprocess\n"
    "def test_git():\n"
    '    subprocess.run(["git", "log", "--", "run.py"], check=True)\n'
)


def test_control_an_unmarked_runner_is_a_runner_and_a_marked_one_is_marked(
    tmp_path: pathlib.Path,
) -> None:
    unmarked = classify(_write(tmp_path, "tests/x/test_runner.py", _RUNNER), tmp_path)
    assert unmarked.is_runner and not unmarked.marked, unmarked.evidence()
    marked = classify(_write(tmp_path, "tests/x/test_marked.py", _RUNNER + _MARK), tmp_path)
    assert marked.is_runner and marked.marked, marked.evidence()


def test_control_readers_helper_loaders_and_prose_are_not_runners(
    tmp_path: pathlib.Path,
) -> None:
    """Each negative control lacks exactly one of the three evidence kinds."""
    reader = classify(_write(tmp_path, "tests/x/test_reader.py", _READER), tmp_path)
    assert reader.archive_paths and reader.programs and not reader.executes, reader.evidence()
    helper = classify(_write(tmp_path, "tests/x/test_helper.py", _HELPER_LOADER), tmp_path)
    assert helper.archive_paths and helper.executes and not helper.programs, helper.evidence()
    prose = classify(_write(tmp_path, "tests/x/test_prose.py", _PROSE_ONLY), tmp_path)
    assert prose.executes and prose.programs and not prose.archive_paths, prose.evidence()
    assert not any(c.is_runner for c in (reader, helper, prose))


def test_control_the_guard_reds_on_a_planted_unmarked_runner(tmp_path: pathlib.Path) -> None:
    """The set-equality check, driven over a synthetic tests/ tree."""
    _write(tmp_path, "tests/x/test_planted.py", _RUNNER)
    _write(tmp_path, "tests/x/test_marked.py", _RUNNER + _MARK)
    table = classify_tree(tmp_path / "tests", tmp_path)
    runners = {p for p, c in table.items() if c.is_runner}
    marked = {p for p, c in table.items() if c.marked}
    assert runners - marked == {"tests/x/test_planted.py"}
    assert marked - runners == set()
