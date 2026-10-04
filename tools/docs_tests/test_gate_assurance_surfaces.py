"""`SEC-011` C1–C4 — the published gate-assurance surfaces, as doors.

**What this module gates, and why it is a docs test rather than a code test.**
`docs/DECISIONS.md` **D-IMPL-364** rules that `SEC-011` requires *"A1, B1
recorded, and C1–C4"*. A1 and B1 are mechanism and are already pinned by
controls under `tests/`. C1–C4 are **assurance surfaces**: what the published
tree tells a bank's assurance reviewer about which validation gate can fail,
on which path, and under which test. They are prose and nav, so they are
gated here — in the suite `make gate-tools` and `.github/workflows/ci.yml`
both run — rather than in `tests/`.

**The four clauses, quoted in each test's docstring.** Taken verbatim from
`D-IMPL-364`:

* *C1 (the page).* `public/concepts/invariants.md`'s three-gates passage
  states the assembly-path-integrity reading of Gate 2 and no longer
  advertises that the gate catches a lineage set that does not match what
  actually contributed as an independent forgery witness.
* *C2 (the controls register).* A page under `public/reference` maps each gate
  token in `src/ccf/products/gates.py` … plus the pre-execution binder
  `refuse_operator_set_divergence` and the consumer-side expiry check in
  `src/ccf/agents/agent.py`, to the path on which each can fail and the test
  that reddens it; a docs test asserts every token has a row and every row's
  test node resolves.
* *C3 (Gate 1, per choice 6).* The register states that on the governed path
  `GATE_EMPTY_OPERATOR` is unreachable because
  `src/ccf/controlplane/artifacts.py::ProductClassDeclaration` and
  `::ProjectionRequirements` declare `required_operator_keys` with
  `min_length=1` … pinned by
  `tests/products/test_empty_operator_halves.py::test_the_declared_half_refuses_a_product_that_declares_no_operators`.
* *C4 (the record agrees with the tree).*
  `docs/surface-changes/358-05-trusted-time.md`'s sentence that Gate 3's
  comparand is unchanged is dated as true-at-step-5 and false after step 7,
  or removed, so no published record denies the Gate 3 repair.

**Why the token roster is DERIVED and the gate names are RULED.** The register
has to carry a row per gate token, and the tokens are code
(`src/ccf/products/gates.py`). Reading them with a line-scoped grep would let a
renamed constant quietly drop a row, so they are parsed by AST: every
module-level ``NAME`` beginning ``GATE_`` bound to a string literal.
:data:`RULED_GATE_NAMES` is the exact roster `D-IMPL-364` C2 enumerates, and
:func:`test_the_gate_token_roster_is_the_ruled_exact_set` compares the parsed
set against it as an **exact set, not a count** — a count passes forever with
the wrong member (`verify-rosters-not-counts`). A ninth gate token therefore
reddens here first, which is the intended order: the ruling names eight, so a
ninth is a decision before it is a row.

**Why the register is read strictly.** An unparseable table row is a
**failure, not a skip**. A lenient reader that silently drops a malformed row
reports a clean register over rows it never judged — the posture
`tools/publish_scan.py::require_populated` refuses and the one
`collection-is-not-execution` names. :func:`table_rows` therefore raises
:class:`RegisterError` on a table with no delimiter, no data rows, or a data
row whose cell count disagrees with its header; and every data row must carry
at least one ``tests/…py::test_…`` citation that resolves to a function
definition in that file, by AST, in the shipped tree.

**Fenced blocks are not rows.** A table inside a ``` fence renders as a code
sample rather than as a register row, so :func:`table_rows` skips fenced
regions. That is parsing, not leniency: the published page has no rendered row
there to judge.

**Positive controls.** Every parser in this module is applied to a scratch
string that must FAIL it *and* to one that must pass — the refusing half alone
cannot distinguish a gate that refuses the defect from a gate that refuses
everything (`tools/docs_tests/test_surface_fragment_bullets.py` carries the
same pairing and states the reason). The scratch strings are read through the
same functions the shipped-tree assertions use; nothing is reimplemented for
the control.

**No clock, no network, no estate.** Every subject is a file in this
repository. There is nothing here to pin a clock against.
"""

from __future__ import annotations

import ast
import pathlib
import re
from typing import NamedTuple

import pytest

from tools.docs_tests import _prose

# ---------------------------------------------------------------------------
# Subjects, all resolved from this file rather than from the process CWD.
# A CWD-relative read yields an empty corpus and turns every assertion below
# into a test that passes over nothing — the failure
# `tools/publish_scan_tests/test_docstring_leaks.py::test_the_walk_does_not_depend_on_the_process_cwd`
# records.
# ---------------------------------------------------------------------------

REPO_ROOT = _prose.REPO_ROOT

#: Where the gate tokens live. Parsed, never grepped.
GATES_MODULE = REPO_ROOT / "src" / "ccf" / "products" / "gates.py"

#: C1's subject.
INVARIANTS_PAGE = _prose.PUBLIC_DIR / "concepts" / "invariants.md"

#: C2's subject. The page the GREEN phase must author.
REGISTER_PAGE = _prose.PUBLIC_DIR / "reference" / "controls-register.md"

#: C2's publication half. `public/` is the only tree mkdocs reads (D-01) and
#: publication is default-deny by existence: a page no nav entry names is a
#: WARNING, and `strict: true` makes it fatal.
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"

#: The register's nav path, as mkdocs spells it (`public/`-relative).
REGISTER_NAV_PATH = "reference/controls-register.md"

#: C4's subject.
TRUSTED_TIME_FRAGMENT = REPO_ROOT / "docs" / "surface-changes" / "358-05-trusted-time.md"

# ---------------------------------------------------------------------------
# C1 — the three-gates passage.
# ---------------------------------------------------------------------------

#: The heading of the passage C1 governs, as the page spells it.
THREE_GATES_HEADING = "## The three validation gates"

#: The forgery reading D-IMPL-86 element 4 and D-IMPL-300 retire. Gate 2
#: compares the Control Plane claim as transcribed into the Contract against
#: the engine's execution of the same plan; the engine builds `operators_invoked`
#: and `steps` in one loop, so it has no return path where invoked ≠ planned
#: and cannot witness a forged lineage set.
#: `tools/docs_tests/test_gate_two_wording.py` guards the *independence*
#: spelling across the whole published tree; this constant is the one phrase
#: that spelling leaves standing, because it asserts the forgery catch without
#: using the word "independent".
FORGERY_READING = "does not match what actually contributed"

#: The correction, as `src/ccf/deployment/__init__.py` states it canonically
#: and as `public/tutorial/adopters-guide.md` and
#: `public/reference/artifacts/product-registration.md` already carry it.
ASSEMBLY_PATH_READING = "assembly-path integrity"

# ---------------------------------------------------------------------------
# C2 — the gate-token roster and the register's required rows.
# ---------------------------------------------------------------------------

#: The exact roster `D-IMPL-364` C2 enumerates. An exact set rather than a
#: count: a count audits clean forever with the wrong member.
RULED_GATE_NAMES = frozenset(
    {
        "GATE_EMPTY_OPERATOR",
        "GATE_LINEAGE_EQUALITY",
        "GATE_LINEAGE_ATTRIBUTABILITY",
        "GATE_TTL_BOUNDS",
        "GATE_TTL_ANCHOR",
        "GATE_SOURCE_ATTESTATION",
        "GATE_DEPENDENCY_INVALIDATION",
        "GATE_DECLARED_OBLIGATIONS",
    }
)

#: The two non-gate controls `D-IMPL-364` C2 requires rows for, each as the
#: set of spellings a row may use. The binder admits only its symbol, because
#: `refuse_operator_set_divergence` is the name the ruling and
#: `src/ccf/products/resolver.py` both use. The consumer-side expiry check
#: admits either its symbol or its module path, because `D-IMPL-364` names it
#: by module ("the consumer-side expiry check in `src/ccf/agents/agent.py`")
#: and the design names it by site.
REQUIRED_SUBJECTS: dict[str, tuple[str, ...]] = {
    "the pre-execution binder": ("refuse_operator_set_divergence",),
    "the consumer-side expiry check": (
        "Agent.consume",
        "agents/agent.py",
        "ccf.agents.agent",
    ),
}

#: A test citation, as the register must spell it: a `tests/`-rooted module
#: path and a `test_`-prefixed function name, joined by `::`. Bare line
#: numbers are not a citation in this repository and are not accepted here.
CITATION = re.compile(r"(tests/[A-Za-z0-9_./-]*\.py)::(test_[A-Za-z0-9_]+)")

# ---------------------------------------------------------------------------
# C3 — the Gate 1 disclosure.
# ---------------------------------------------------------------------------

#: The upstream constraint that makes Gate 1 unreachable on the governed path.
GATE_ONE_CONSTRAINT = "min_length=1"

#: The direct-`run_gates` control `D-IMPL-364` C3 pins, as `path::name`.
GATE_ONE_CONTROL = (
    "tests/products/test_empty_operator_halves.py",
    "test_the_declared_half_refuses_a_product_that_declares_no_operators",
)

# ---------------------------------------------------------------------------
# C4 — the surface-change record.
# ---------------------------------------------------------------------------

#: The denial, allowing either apostrophe an author might type.
GATE_THREE_DENIAL = re.compile(r"Gate 3['’]s comparand is unchanged")

#: What dates the denial. Either marker discharges C4; so does deleting the
#: sentence.
#:
#: ``true at step 5`` is matched case-insensitively because an author writing
#: the repair will capitalize it at a sentence start ("**True at step 5, false
#: after step 7.**") and a gate that reddened on the capital would be a gate
#: about typography. ``AMENDED`` stays case-sensitive: it is an all-caps
#: editorial marker in this repository's records, and the lower-case word
#: appears in ordinary prose.
DATED_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("true at step 5", re.compile(r"true at step 5", re.IGNORECASE)),
    ("AMENDED", re.compile(r"AMENDED")),
)

#: How far from the denial a marker may sit and still be read as qualifying it.
#: Measured on whitespace-collapsed text, so a reflow cannot move it.
MARKER_WINDOW = 300


class RegisterError(Exception):
    """A row of the shipped register could not be read.

    Raised rather than skipped: a reader that drops a malformed row reports a
    clean register over rows it never judged.
    """


class MarkdownRow(NamedTuple):
    """One rendered data row of a markdown table.

    Attributes:
        lineno: 1-based line number, so a failure can be opened directly.
        cells: The row's cells, stripped, in document order.
        raw: The row's source line, whitespace-collapsed and nothing stripped —
            code spans survive, which is the only way a citation written as
            `` `tests/…py::test_…` `` is visible.
    """

    lineno: int
    cells: tuple[str, ...]
    raw: str


def _collapse(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Parsers. Each is a pure function over text so a positive control can drive
# it with a scratch string through the same code path the tree assertions use.
# ---------------------------------------------------------------------------


def gate_tokens(source: str) -> dict[str, str]:
    """Every module-level ``GATE_*`` string constant, by AST.

    Args:
        source: The text of `src/ccf/products/gates.py`.

    Returns:
        Constant name to its string value, for every module-level assignment
        whose target name starts ``GATE_`` and whose value is a string
        literal. Annotated assignments count; a ``GATE_*`` bound to anything
        other than a string literal does not, and is reported by
        :func:`test_the_gate_token_roster_is_the_ruled_exact_set` as a missing
        member rather than silently admitted.
    """
    tree = ast.parse(source)
    tokens: dict[str, str] = {}
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id.startswith("GATE_"):
                tokens[target.id] = value.value
    return tokens


def table_rows(text: str) -> list[MarkdownRow]:
    """Every rendered data row of every markdown table in `text`, strictly.

    A table is a run of consecutive lines whose stripped form starts with
    ``|``, outside any fenced block. It must carry a header row, a delimiter
    row, and at least one data row; every data row must carry the header's
    cell count. Anything else raises.

    Raises:
        RegisterError: a table has no delimiter row, no data row, or a data
            row whose cell count disagrees with its header's.
    """
    rows: list[MarkdownRow] = []
    lines = text.splitlines()
    block: list[tuple[int, str]] = []
    fence: str | None = None

    def flush() -> None:
        if block:
            rows.extend(_read_table(block))
            block.clear()

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        opener = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence is not None:
            if opener is not None and opener.group(1)[0] == fence[0]:
                fence = None
            continue
        if opener is not None:
            flush()
            fence = opener.group(1)
            continue
        if stripped.startswith("|"):
            block.append((lineno, stripped))
            continue
        flush()
    flush()
    return rows


def _cells(line: str) -> tuple[str, ...] | None:
    """`line`'s cells, or None when it is not a readable table row."""
    if not (line.startswith("|") and line.endswith("|")) or len(line) < 2:
        return None
    return tuple(cell.strip() for cell in line[1:-1].split("|"))


def _is_delimiter(cells: tuple[str, ...]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell) is not None for cell in cells
    )


def _read_table(block: list[tuple[int, str]]) -> list[MarkdownRow]:
    """One table block's data rows, strictly."""
    first_line = block[0][0]
    parsed: list[tuple[int, tuple[str, ...], str]] = []
    for lineno, line in block:
        cells = _cells(line)
        if cells is None:
            raise RegisterError(
                f"line {lineno}: a table line that is not a readable row —"
                " a rendered row opens and closes with '|'. An unreadable row"
                " is a failure rather than a skip, because a row nobody could"
                f" parse is a row nobody judged: {line!r}"
            )
        parsed.append((lineno, cells, line))

    if len(parsed) < 3:
        raise RegisterError(
            f"the table at line {first_line} has {len(parsed)} line(s): a"
            " register table needs a header, a delimiter and at least one data"
            " row. A header-only table publishes a register with no controls"
            " in it and would satisfy a lenient reader."
        )
    header = parsed[0][1]
    if not _is_delimiter(parsed[1][1]):
        raise RegisterError(
            f"the table at line {first_line} has no delimiter row under its"
            f" header, so markdown renders it as prose rather than as a table:"
            f" {parsed[1][2]!r}"
        )
    rows: list[MarkdownRow] = []
    for lineno, cells, raw in parsed[2:]:
        if len(cells) != len(header):
            raise RegisterError(
                f"line {lineno}: the row carries {len(cells)} cells against a"
                f" {len(header)}-cell header, so its values render against the"
                f" wrong columns: {raw!r}"
            )
        rows.append(MarkdownRow(lineno=lineno, cells=cells, raw=_collapse(raw)))
    return rows


_TEST_FUNCTIONS: dict[pathlib.Path, frozenset[str]] = {}


def defined_functions(path: pathlib.Path) -> frozenset[str]:
    """Every function name defined in `path`, at any nesting depth, by AST.

    Nested and method definitions count: a control may be a method on a test
    class, and a citation to it is still resolvable. A file that does not
    exist, or does not parse, yields the empty set — the caller reports the
    citation as unresolved, which is the same verdict a reviewer would reach.
    """
    cached = _TEST_FUNCTIONS.get(path)
    if cached is not None:
        return cached
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        names: frozenset[str] = frozenset()
    else:
        names = frozenset(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    _TEST_FUNCTIONS[path] = names
    return names


def citation_resolves(module: str, name: str, *, root: pathlib.Path = REPO_ROOT) -> bool:
    """Whether `module`::`name` is a function definition in the shipped tree."""
    return name in defined_functions(root / module)


def audit_register(
    text: str,
    *,
    tokens: dict[str, str],
    root: pathlib.Path = REPO_ROOT,
) -> list[str]:
    """Every way the register `text` fails `D-IMPL-364` C2, as sentences.

    Raises:
        RegisterError: a row could not be read. Unreadable is a failure.
    """
    rows = table_rows(text)
    problems: list[str] = []

    if not rows:
        problems.append(
            "the register carries no table rows at all: C2 requires a row per"
            " gate token, so a page with no rows discharges nothing"
        )

    for name in sorted(tokens):
        value = tokens[name]
        # The token must be a CELL of the row — the row's own token column —
        # not merely mentioned in another row's prose: measured 2026-10-04,
        # deleting the shipped `ttl-bounds` row left this audit green because
        # the consumer-side row's text cites that token. A code span that
        # merely CONTAINS the token (`ttl-bounds-x`) does not count either.
        naming = [row for row in rows if f"`{value}`" in row.cells]
        if not naming:
            problems.append(
                f"no row names the gate token {value!r} ({name} in"
                " src/ccf/products/gates.py): every token needs the path on"
                " which it can fail and the test that reddens it"
            )

    for subject, spellings in REQUIRED_SUBJECTS.items():
        if not any(
            any(spelling in row.raw for spelling in spellings) for row in rows
        ):
            problems.append(
                f"no row names {subject}: C2 requires one beyond the gate"
                f" tokens, spelled as any of {list(spellings)}"
            )

    for row in rows:
        citations = CITATION.findall(row.raw)
        if not citations:
            problems.append(
                f"line {row.lineno}: the row cites no test as"
                " 'tests/...py::test_...', so it names a control an assurance"
                f" reviewer cannot run: {row.raw!r}"
            )
            continue
        for module, name in citations:
            if not citation_resolves(module, name, root=root):
                problems.append(
                    f"line {row.lineno}: the citation {module}::{name} resolves"
                    " to no function definition in that file — a register that"
                    " points at a control which does not exist is worse than"
                    " one that points at none"
                )
    return problems


def gate_one_disclosure_problems(
    text: str, *, empty_operator_token: str, root: pathlib.Path = REPO_ROOT
) -> list[str]:
    """Every way the register `text` fails `D-IMPL-364` C3, as sentences.

    The scope is the union of the rows naming the empty-operator token and any
    section whose heading names it, because C3 admits either ("the register's
    empty-operator-guard row (or a dedicated section)").
    """
    scope: list[str] = [row.raw for row in table_rows(text) if empty_operator_token in row.raw]
    scope.extend(
        body
        for heading, body in sections(text).items()
        if empty_operator_token in heading or "empty-operator" in heading.lower()
    )
    joined = _collapse(" ".join(scope))

    problems: list[str] = []
    if not scope:
        problems.append(
            f"nothing in the register names {empty_operator_token!r}, so C3's"
            " disclosure has nowhere to live"
        )
        return problems
    if GATE_ONE_CONSTRAINT not in joined:
        problems.append(
            f"the {empty_operator_token} disclosure does not name"
            f" {GATE_ONE_CONSTRAINT!r}: C3 requires the register to say WHY"
            " Gate 1 is unreachable on the governed path —"
            " ProductClassDeclaration and ProjectionRequirements declare"
            " required_operator_keys with that constraint, so an empty set is"
            " refused at artifact validation"
        )
    module, name = GATE_ONE_CONTROL
    if f"{module}::{name}" not in joined:
        problems.append(
            f"the {empty_operator_token} disclosure does not cite"
            f" {module}::{name}: C3 pins Gate 1's own refusal to that"
            " direct-run_gates control, which is the only route that reaches it"
        )
    elif not citation_resolves(module, name, root=root):
        problems.append(
            f"the cited Gate 1 control {module}::{name} resolves to no"
            " function definition in that file"
        )
    return problems


def sections(text: str) -> dict[str, str]:
    """Each ``##``-or-deeper heading in `text` mapped to its own body.

    A section's body runs to the next heading at the same depth or shallower,
    so a ``###`` subsection stays inside its ``##`` parent.
    """
    lines = text.splitlines()
    found: dict[str, str] = {}
    open_sections: list[tuple[str, int, list[str]]] = []

    def close(depth: int) -> None:
        while open_sections and open_sections[-1][1] >= depth:
            heading, _, body = open_sections.pop()
            found[heading] = "\n".join(body)

    for line in lines:
        match = re.match(r"^(#{2,6})\s+(.*)$", line)
        if match is not None:
            close(len(match.group(1)))
            open_sections.append((line.strip(), len(match.group(1)), []))
            continue
        for _, _, body in open_sections:
            body.append(line)
    close(2)
    return found


def three_gates_passage(text: str) -> str:
    """The whitespace-collapsed body of the three-gates section of `text`."""
    return _collapse(sections(text).get(THREE_GATES_HEADING, ""))


def undated_denials(text: str) -> list[str]:
    """Every `Gate 3's comparand is unchanged` in `text` with no dated marker.

    Returns the offending windows, so a failure quotes the sentence rather
    than pointing at a line number the next reflow invalidates.
    """
    collapsed = _collapse(text)
    offenders: list[str] = []
    for match in GATE_THREE_DENIAL.finditer(collapsed):
        window = collapsed[
            max(0, match.start() - MARKER_WINDOW) : match.end() + MARKER_WINDOW
        ]
        if not any(pattern.search(window) for _, pattern in DATED_MARKERS):
            offenders.append(window)
    return offenders


def reference_nav_pages(config_text: str) -> set[str]:
    """Every `.md` page `mkdocs.yml` lists under its top-level Reference entry.

    Scoped to the Reference block rather than to the whole nav, because C2
    says the register is "a page under `public/reference`" — a nav entry for
    it filed under Tutorial would publish the page and still misfile it.
    """
    block = re.search(
        r"^nav:\s*$(?P<body>.*?)(?=^\S|\Z)", config_text, re.MULTILINE | re.DOTALL
    )
    if block is None:
        return set()
    body = block.group("body").splitlines()
    pages: set[str] = set()
    inside: int | None = None
    for line in body:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if inside is not None and indent <= inside:
            inside = None
        if re.match(r"^\s*-\s+Reference:\s*$", line):
            inside = indent
            continue
        if inside is None:
            continue
        found = re.search(r":\s*([A-Za-z0-9_][A-Za-z0-9_./-]*\.md)\s*$", line)
        if found is not None:
            pages.add(found.group(1))
    return pages


# ---------------------------------------------------------------------------
# C1 — the three-gates passage.
# ---------------------------------------------------------------------------


def test_the_invariants_page_states_assembly_path_integrity_not_forgery() -> None:
    """C1: the passage states assembly-path integrity, not the forgery catch.

    `D-IMPL-364` C1, verbatim: *"`public/concepts/invariants.md`'s three-gates
    passage states the assembly-path-integrity reading of Gate 2 and no longer
    advertises that the gate catches a lineage set that does not match what
    actually contributed as an independent forgery witness."*

    The reason the forgery reading is wrong is mechanical, not editorial:
    `ccf.projection.engine.ProjectionEngine.execute` builds ``operators_invoked``
    and ``steps`` in one loop over the same operator plan, so it has no return
    path where invoked ≠ planned. `D-IMPL-86` element 4 and `D-IMPL-300` are
    the rulings of record, and the failable control runs BEFORE execution at
    `src/ccf/deployment/binder.py::refuse_operator_set_divergence` (called from the resolver).
    """
    passage = three_gates_passage(INVARIANTS_PAGE.read_text(encoding="utf-8"))

    assert passage, (
        f"{_prose.relative(INVARIANTS_PAGE)} has no {THREE_GATES_HEADING!r}"
        " section. C1's subject is that passage; a reader that finds no section"
        " would assert over an empty string and pass forever, so the heading's"
        " absence is reported rather than tolerated"
    )
    assert FORGERY_READING not in passage, (
        f"{_prose.relative(INVARIANTS_PAGE)}'s three-gates passage still"
        f" advertises the forgery reading of Gate 2 ({FORGERY_READING!r}). The"
        " gate compares the Control Plane claim as transcribed into the"
        " Contract against the engine's execution of the same plan; the engine"
        " transcribes that plan faithfully and cannot witness a lineage set"
        " that disagrees with what contributed. Published as-is, this sentence"
        " tells a bank's assurance reviewer that a control exists which does"
        f" not. The passage reads: {passage!r}"
    )
    assert ASSEMBLY_PATH_READING.lower() in passage.lower(), (
        f"{_prose.relative(INVARIANTS_PAGE)}'s three-gates passage does not"
        f" state the correction ({ASSEMBLY_PATH_READING!r}), which"
        " public/tutorial/adopters-guide.md and"
        " public/reference/artifacts/product-registration.md already carry."
        " C1 requires the page to say what Gate 2 does verify, not merely to"
        f" stop saying what it does not. The passage reads: {passage!r}"
    )


# ---------------------------------------------------------------------------
# C2 — the controls register.
# ---------------------------------------------------------------------------


def test_the_controls_register_exists_and_is_published() -> None:
    """C2, the publication half: the page exists and nav names it.

    `D-IMPL-364` C2, verbatim: *"A page under `public/reference` maps each gate
    token in `src/ccf/products/gates.py` … to the path on which each can fail
    and the test that reddens it."*

    Existence is not publication (`D-IMPL-324` — *declaration is not a door*).
    `public/` is the only tree mkdocs reads and publication is default-deny by
    existence (D-01), so a register nobody can navigate to is a file rather
    than an assurance surface — and under ``strict: true`` with
    ``validation.nav.omitted_files: warn`` it is also a red build.
    """
    assert REGISTER_PAGE.is_file(), (
        f"{_prose.relative(REGISTER_PAGE)} does not exist. C2 requires a"
        " controls register under public/reference mapping each gate token,"
        " the pre-execution binder and the consumer-side expiry check to the"
        " path on which each can fail and the test that reddens it"
    )
    assert REGISTER_PAGE.read_text(encoding="utf-8").strip(), (
        f"{_prose.relative(REGISTER_PAGE)} is empty: an empty page satisfies"
        " an existence check and discharges nothing"
    )

    listed = reference_nav_pages(MKDOCS_CONFIG.read_text(encoding="utf-8"))
    assert listed, (
        "mkdocs.yml's nav has no readable Reference block, so this assertion"
        " would judge an empty roster and pass over anything"
    )
    assert REGISTER_NAV_PATH in listed, (
        f"mkdocs.yml's nav Reference block does not list {REGISTER_NAV_PATH}."
        " The page is unreachable from the site's navigation, and D-01 makes"
        " publication default-deny by existence. Reference currently lists:"
        f" {sorted(listed)}"
    )


def test_the_gate_token_roster_is_the_ruled_exact_set() -> None:
    """The register's row roster is derived from code, and the code is pinned.

    `D-IMPL-364` C2 enumerates the eight tokens by name:
    *"`GATE_EMPTY_OPERATOR`, `GATE_LINEAGE_EQUALITY`,
    `GATE_LINEAGE_ATTRIBUTABILITY`, `GATE_TTL_BOUNDS`, `GATE_TTL_ANCHOR`,
    `GATE_SOURCE_ATTESTATION`, `GATE_DEPENDENCY_INVALIDATION`,
    `GATE_DECLARED_OBLIGATIONS`."*

    An exact set, never a count: a count audits clean forever with the wrong
    member. A ninth gate token reddens here before it reddens the register,
    which is the right order — the ruling names eight, so a ninth is a
    decision first and a row second.
    """
    parsed = gate_tokens(GATES_MODULE.read_text(encoding="utf-8"))

    assert set(parsed) == set(RULED_GATE_NAMES), (
        "the GATE_* constants parsed from"
        f" {_prose.relative(GATES_MODULE)} are not the roster D-IMPL-364 C2"
        f" rules. Parsed: {sorted(parsed)}. Ruled:"
        f" {sorted(RULED_GATE_NAMES)}. If a gate token was added or removed,"
        " that is a decision: record it, update this roster and the controls"
        " register in the same commit"
    )
    assert all(value for value in parsed.values()), (
        "a GATE_* constant is bound to the empty string, which cannot name a"
        f" register row: {parsed}"
    )
    assert len(set(parsed.values())) == len(parsed), (
        "two GATE_* constants share a token value, so a register row naming"
        f" that value cannot be attributed to one gate: {parsed}"
    )


def test_every_gate_token_has_a_register_row_and_every_cited_test_resolves() -> None:
    """C2, the content half: a row per control, and every citation resolves.

    `D-IMPL-364` C2, verbatim: *"… plus the pre-execution binder
    `refuse_operator_set_divergence` and the consumer-side expiry check in
    `src/ccf/agents/agent.py`, to the path on which each can fail and the test
    that reddens it; a docs test asserts every token has a row and every row's
    test node resolves."*

    Read strictly. An unreadable row raises :class:`RegisterError` and fails
    here rather than being dropped: a reader that skips what it cannot parse
    reports a clean register over rows it never judged.
    """
    assert REGISTER_PAGE.is_file(), (
        f"{_prose.relative(REGISTER_PAGE)} does not exist; C2's row audit has"
        " no subject. test_the_controls_register_exists_and_is_published"
        " carries the same failure with the authoring instruction"
    )
    tokens = gate_tokens(GATES_MODULE.read_text(encoding="utf-8"))
    assert tokens, (
        f"no GATE_* constants parsed from {_prose.relative(GATES_MODULE)}: the"
        " row audit would judge an empty roster and pass over anything"
    )

    try:
        problems = audit_register(
            REGISTER_PAGE.read_text(encoding="utf-8"), tokens=tokens
        )
    except RegisterError as refused:
        pytest.fail(
            f"{_prose.relative(REGISTER_PAGE)} carries a table row this gate"
            " could not read. An unreadable row is a failure rather than a"
            f" skip. The reader's refusal, verbatim:\n\n{refused}"
        )

    assert not problems, (
        f"{_prose.relative(REGISTER_PAGE)} does not discharge D-IMPL-364 C2:\n\n"
        + "\n".join(f"  - {problem}" for problem in problems)
    )


# ---------------------------------------------------------------------------
# C3 — the Gate 1 disclosure.
# ---------------------------------------------------------------------------


def test_the_register_discloses_gate_one_is_unreachable_on_the_governed_path() -> None:
    """C3: Gate 1's unreachability, its cause, and its direct control.

    `D-IMPL-364` C3, verbatim: *"The register states that on the governed path
    `GATE_EMPTY_OPERATOR` is unreachable because
    `src/ccf/controlplane/artifacts.py::ProductClassDeclaration` and
    `::ProjectionRequirements` declare `required_operator_keys` with
    `min_length=1` and an empty set is refused at artifact validation; its own
    refusal is reachable only by calling `run_gates` directly, pinned by
    `tests/products/test_empty_operator_halves.py::test_the_declared_half_refuses_a_product_that_declares_no_operators`."*

    Choice 6 as Dave ruled it: *"Gate 1 disclosure suffices, with the upstream
    constraints and direct-`run_gates` control cited."* Disclosure is the whole
    remedy — the gate is not being repaired, so the register has to say that a
    reviewer who audits Gate 1 on the governed path will find a control that
    cannot fire there, and where the one that can fire lives.
    """
    assert REGISTER_PAGE.is_file(), (
        f"{_prose.relative(REGISTER_PAGE)} does not exist; C3's disclosure has"
        " no page to live on"
    )
    tokens = gate_tokens(GATES_MODULE.read_text(encoding="utf-8"))
    token = tokens.get("GATE_EMPTY_OPERATOR")
    assert token, (
        "GATE_EMPTY_OPERATOR did not parse from"
        f" {_prose.relative(GATES_MODULE)}, so C3's subject cannot be located"
    )

    try:
        problems = gate_one_disclosure_problems(
            REGISTER_PAGE.read_text(encoding="utf-8"), empty_operator_token=token
        )
    except RegisterError as refused:
        pytest.fail(
            f"{_prose.relative(REGISTER_PAGE)} carries a table row this gate"
            f" could not read, so C3's scope is unknown:\n\n{refused}"
        )

    assert not problems, (
        f"{_prose.relative(REGISTER_PAGE)} does not discharge D-IMPL-364 C3:\n\n"
        + "\n".join(f"  - {problem}" for problem in problems)
    )


# ---------------------------------------------------------------------------
# C4 — the surface-change record.
# ---------------------------------------------------------------------------


def test_the_358_05_fragment_no_longer_denies_the_gate_3_repair() -> None:
    """C4: no published record denies the Gate 3 repair.

    `D-IMPL-364` C4, verbatim: *"`docs/surface-changes/358-05-trusted-time.md`'s
    sentence that Gate 3's comparand is unchanged is dated as true-at-step-5
    and false after step 7, or removed, so no published record denies the Gate
    3 repair."*

    The sentence was true when it was written: at step 5 nothing called the
    temporal-bound judgment. `SEC-011` A1 then made Gate 3's comparand the
    fabric instant `served_at`. A fragment is a dated record and may keep its
    original words, so either discharge is accepted — delete the sentence, or
    date it — but a record that reads in the present tense while the tree says
    otherwise is a published denial of the repair.
    """
    offenders = undated_denials(TRUSTED_TIME_FRAGMENT.read_text(encoding="utf-8"))

    assert not offenders, (
        f"{_prose.relative(TRUSTED_TIME_FRAGMENT)} still states that Gate 3's"
        " comparand is unchanged with no dated marker"
        f" ({' or '.join(repr(label) for label, _ in DATED_MARKERS)}) within"
        f" {MARKER_WINDOW} characters. SEC-011 A1 made Gate 3's comparand the"
        " fabric instant served_at, so the sentence now denies a shipped"
        " repair. Either remove it or date it. The window(s):\n\n"
        + "\n\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Positive controls. Every parser above, driven by a scratch string that must
# fail it AND one that must pass. A refusal test on its own cannot distinguish
# a gate that refuses the defect from a gate that refuses everything.
# ---------------------------------------------------------------------------

#: A register that discharges C2 and C3, used as the accepting half of every
#: control below. Its citations are real nodes in this tree on purpose: a
#: scratch page whose citations did not resolve could not prove the accepting
#: path at all.
_GOOD_REGISTER = """# Controls register

| Control | Token | Fails on | Reddened by |
| --- | --- | --- | --- |
| Gate 1 | `empty-operator-guard` | `run_gates` called directly; unreachable on the governed path because `ProductClassDeclaration` and `ProjectionRequirements` declare `required_operator_keys` with `min_length=1` | `tests/products/test_empty_operator_halves.py::test_the_declared_half_refuses_a_product_that_declares_no_operators` |
| Gate 2 | `lineage-strict-equality` | assembly-path integrity, self-satisfying post-execution | `tests/products/test_gate_two_call_shape.py::test_a_second_operator_set_outside_the_control_plane_is_refused` |
| Gate 2, federated | `lineage-attributability` | federated serve | `tests/gates/test_federated_gates.py::test_attributability_is_checked_before_ttl` |
| Gate 3 | `ttl-bounds` | governed serve at `served_at` | `tests/gates/test_product_gates.py::test_expiry_beyond_max_ttl_is_refused` |
| TTL anchor | `ttl-anchor-unresolvable` | anchored expiry | `tests/products/test_d_impl_341_ttl_anchor.py::test_c6_evidence_older_than_the_window_refuses_ttl_bounds_naming_the_anchored_expiry` |
| Attestation | `source-attestation` | governed serve | `tests/gates/test_product_gates.py::test_expiry_exactly_at_max_ttl_is_allowed` |
| Invalidation | `dependency-invalidation` | governed serve | `tests/gates/test_product_gates.py::test_expiry_beyond_max_ttl_is_refused` |
| Obligations | `declared-obligations` | governed serve | `tests/gates/test_product_gates.py::test_expiry_beyond_max_ttl_is_refused` |
| Pre-execution binder | `refuse_operator_set_divergence` | before execution | `tests/products/test_gate_two_call_shape.py::test_a_second_operator_set_outside_the_control_plane_is_refused` |
| Consumer expiry | `Agent.consume` | consumer admission | `tests/agents/test_agent.py::test_consume_refuses_an_expired_product_rather_than_degrading` |
"""


def _ruled_tokens() -> dict[str, str]:
    """The shipped token roster, which the controls below audit against."""
    return gate_tokens(GATES_MODULE.read_text(encoding="utf-8"))


def test_control_the_token_parser_reads_the_shipped_module_and_a_scratch_one() -> None:
    """Positive control for :func:`gate_tokens`, both halves."""
    assert _ruled_tokens(), "the AST parse of the shipped gates module read nothing"

    scratch = gate_tokens(
        "GATE_SCRATCH = 'scratch-token'\n"
        "GATE_NOT_A_STRING = 7\n"
        "NOT_A_GATE = 'other'\n"
        "def f():\n    GATE_LOCAL = 'nested'\n"
    )
    assert scratch == {"GATE_SCRATCH": "scratch-token"}, (
        "the parser must take module-level GATE_* string constants only — a"
        " non-string binding, a non-GATE name and a function-local assignment"
        f" are all outside the roster: {scratch}"
    )


def test_control_the_register_audit_accepts_a_well_formed_scratch_page() -> None:
    """Positive control, accepting half: the audit is not refusing everything."""
    problems = audit_register(_GOOD_REGISTER, tokens=_ruled_tokens())
    assert not problems, (
        "the scratch register discharges C2 by construction; if this fails the"
        f" audit refuses conforming pages too: {problems}"
    )
    assert not gate_one_disclosure_problems(
        _GOOD_REGISTER, empty_operator_token=_ruled_tokens()["GATE_EMPTY_OPERATOR"]
    ), "the scratch register discharges C3 by construction"


def test_control_the_register_audit_refuses_a_row_with_the_wrong_cell_count() -> None:
    """Positive control: an unparseable row is a failure, not a skip."""
    broken = _GOOD_REGISTER.replace(
        "| Gate 3 | `ttl-bounds` | governed serve at `served_at` |",
        "| Gate 3 | `ttl-bounds` |",
    )
    with pytest.raises(RegisterError) as refused:
        audit_register(broken, tokens=_ruled_tokens())
    assert "cells against a" in str(refused.value), (
        "the refusal must say the row's cell count disagrees with its header's,"
        f" so the author can see which row renders wrong: {refused.value}"
    )


def test_control_the_register_audit_refuses_a_table_with_no_delimiter() -> None:
    """Positive control: a table markdown renders as prose is not a register."""
    no_delimiter = _GOOD_REGISTER.replace("| --- | --- | --- | --- |\n", "")
    with pytest.raises(RegisterError) as refused:
        audit_register(no_delimiter, tokens=_ruled_tokens())
    assert "no delimiter row" in str(refused.value)


def test_control_the_register_audit_refuses_a_missing_gate_token() -> None:
    """Positive control: a dropped token row is named, not averaged away."""
    tokens = _ruled_tokens()
    without_ttl = "\n".join(
        line for line in _GOOD_REGISTER.splitlines() if "`ttl-bounds`" not in line
    )
    problems = audit_register(without_ttl + "\n", tokens=tokens)
    assert any(tokens["GATE_TTL_BOUNDS"] in problem for problem in problems), (
        "the audit must name the token whose row is missing, by its literal"
        f" value, so the GREEN author knows what to write: {problems}"
    )


def test_control_the_register_audit_refuses_a_row_citing_no_test() -> None:
    """Positive control: a row with no runnable control is refused."""
    uncited = _GOOD_REGISTER.replace(
        "| `tests/agents/test_agent.py::test_consume_refuses_an_expired_product_rather_than_degrading` |",
        "| covered |",
    )
    problems = audit_register(uncited, tokens=_ruled_tokens())
    assert any("cites no test" in problem for problem in problems), (
        f"a row naming no 'tests/...py::test_...' must be refused: {problems}"
    )


def test_control_the_register_audit_refuses_a_citation_that_resolves_to_nothing() -> None:
    """Positive control: the citation is resolved by AST, not pattern-matched."""
    fabricated = _GOOD_REGISTER.replace(
        "test_consume_refuses_an_expired_product_rather_than_degrading",
        "test_a_control_that_was_never_written",
    )
    problems = audit_register(fabricated, tokens=_ruled_tokens())
    assert any("resolves to no function definition" in problem for problem in problems), (
        "a citation whose node does not exist must be refused — the shape of a"
        f" node id is not evidence that it runs: {problems}"
    )


def test_control_the_gate_one_audit_refuses_a_row_without_the_constraint() -> None:
    """Positive control for C3: disclosure means the cause AND the control."""
    tokens = _ruled_tokens()
    token = tokens["GATE_EMPTY_OPERATOR"]

    no_cause = _GOOD_REGISTER.replace(
        "unreachable on the governed path because `ProductClassDeclaration`"
        " and `ProjectionRequirements` declare `required_operator_keys` with"
        " `min_length=1`",
        "unreachable on the governed path",
    )
    assert any(
        GATE_ONE_CONSTRAINT in problem
        for problem in gate_one_disclosure_problems(
            no_cause, empty_operator_token=token
        )
    ), "a disclosure that omits the upstream constraint must be refused"

    no_control = _GOOD_REGISTER.replace(
        "`tests/products/test_empty_operator_halves.py::test_the_declared_half_refuses_a_product_that_declares_no_operators`",
        "`tests/gates/test_product_gates.py::test_expiry_beyond_max_ttl_is_refused`",
    )
    assert any(
        GATE_ONE_CONTROL[1] in problem
        for problem in gate_one_disclosure_problems(
            no_control, empty_operator_token=token
        )
    ), "a disclosure that omits the direct-run_gates control must be refused"


def test_control_the_three_gates_reader_sees_the_forgery_phrase_and_the_fix() -> None:
    """Positive control for C1's reader, both halves, over scratch pages."""
    bad = (
        "# Invariants\n\n"
        f"{THREE_GATES_HEADING}\n\n"
        "Each gate closes a way a product could be well-typed and still be a\n"
        "lie: derived from no operators at all, carrying a lineage set that\n"
        "does not match what actually contributed, or served past the\n"
        "freshness envelope it advertises.\n\n"
        "## Another invariant\n\nassembly-path integrity lives here instead.\n"
    )
    passage = three_gates_passage(bad)
    assert FORGERY_READING in passage, (
        "the reader must see the forgery phrase even though it wraps across"
        f" three source lines — paragraph scoping is the point: {passage!r}"
    )
    assert ASSEMBLY_PATH_READING not in passage, (
        "the reader must not be exonerated by the correction appearing in a"
        " DIFFERENT section, which is exactly how a line-scoped or"
        f" whole-page grep passes a wrong page: {passage!r}"
    )

    good = bad.replace(
        "carrying a lineage set that\ndoes not match what actually contributed",
        "carrying a lineage set that\nthe assembly path did not produce"
        " (assembly-path integrity)",
    )
    fixed = three_gates_passage(good)
    assert FORGERY_READING not in fixed and ASSEMBLY_PATH_READING in fixed, (
        f"the corrected scratch page must read clean: {fixed!r}"
    )

    assert three_gates_passage("# A page with no such section\n") == "", (
        "a page without the heading must yield the empty string, which is what"
        " lets the shipped-tree assertion report the heading's absence rather"
        " than passing over nothing"
    )


def test_control_the_fragment_reader_dates_a_denial_but_not_an_undated_one() -> None:
    """Positive control for C4's reader, both halves."""
    denial = "Nothing yet CALLS it: Gate 3's comparand is unchanged, composite remaining validity is unchanged."
    assert undated_denials(denial), "an undated denial must be reported"
    assert not undated_denials(
        "**True at step 5, false after step 7.** " + denial
    ), "a dated denial discharges C4 — a fragment is a dated record"
    assert not undated_denials("AMENDED at step 7. " + denial), (
        "the AMENDED marker discharges C4 too"
    )
    assert not undated_denials("true at step 5. " + denial), (
        "the marker is matched case-insensitively, so the lower-case spelling"
        " discharges C4 as well as the sentence-initial capital"
    )
    assert undated_denials("true at step 5. " + ("x " * 200) + denial), (
        "a marker 400 characters upstream of the denial must NOT discharge it:"
        f" the window is {MARKER_WINDOW} characters, so a date that qualifies"
        " some other sentence cannot exonerate this one"
    )
    assert undated_denials(
        denial.replace("Gate 3's", "Gate 3’s")
    ), "a curly apostrophe must not hide the denial"


def test_control_the_nav_reader_scopes_to_the_reference_block() -> None:
    """Positive control for C2's publication half, both halves."""
    config = (
        "site_name: x\n"
        "nav:\n"
        "  - Home: index.md\n"
        "  - Tutorial:\n"
        "      - Guide: tutorial/adopters-guide.md\n"
        "  - Reference:\n"
        "      - Controls register: reference/controls-register.md\n"
        "      - HTTP API: reference/http-api.md\n"
        "plugins:\n"
        "  - search\n"
    )
    listed = reference_nav_pages(config)
    assert listed == {REGISTER_NAV_PATH, "reference/http-api.md"}, (
        "the reader must return exactly the Reference block's pages, as an"
        f" exact set: {sorted(listed)}"
    )

    misfiled = config.replace(
        "      - Controls register: reference/controls-register.md\n", ""
    ).replace(
        "  - Tutorial:\n",
        "  - Tutorial:\n      - Controls register: reference/controls-register.md\n",
    )
    assert REGISTER_NAV_PATH not in reference_nav_pages(misfiled), (
        "a register filed under Tutorial publishes the page and misfiles it;"
        " the scoped reader is what catches that"
    )
    assert reference_nav_pages("site_name: x\n") == set(), (
        "a config with no nav must yield the empty set rather than a false"
        " positive"
    )


def test_control_the_subjects_resolve_under_this_repository_root() -> None:
    """Non-vacuity: every subject this module reads is in THIS tree.

    A CWD-relative read turns all four clauses into tests that pass over
    nothing. :data:`REPO_ROOT` comes from
    `tools/docs_tests/_prose.py::REPO_ROOT`, which resolves from the file.
    """
    assert GATES_MODULE.is_file(), GATES_MODULE
    assert INVARIANTS_PAGE.is_file(), INVARIANTS_PAGE
    assert MKDOCS_CONFIG.is_file(), MKDOCS_CONFIG
    assert TRUSTED_TIME_FRAGMENT.is_file(), TRUSTED_TIME_FRAGMENT
    assert REGISTER_PAGE.parent.is_dir(), (
        "public/reference/ must exist for the register to be authored into it:"
        f" {REGISTER_PAGE.parent}"
    )
    module, name = GATE_ONE_CONTROL
    assert citation_resolves(module, name), (
        f"the Gate 1 control D-IMPL-364 C3 pins ({module}::{name}) does not"
        " resolve in this tree, so C3's citation requirement would be"
        " unsatisfiable"
    )
