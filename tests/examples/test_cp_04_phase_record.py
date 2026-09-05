"""Phase 24.4's own record, asserted mechanically rather than reported.

Three claims this phase makes about ITSELF, each of which a SUMMARY could
assert for free and none of which a SUMMARY can prove:

1. **`src/` did not move.** Locked ROADMAP criterion 49 — *"no file under
   `src/` is modified by it"*. Asserted as a pathspec diff between two PINNED
   commits, with the instrument proven able to report a change.
2. **No over-claim reached any document.** Locked criterion 2 — the
   reproducibility claim is *"byte-identical against a quiescent ledger for
   that run"* (`D-02` of `24.4-CONTEXT.md`) and *"no stronger claim appears in
   the README, the spec, the documentation page or any test name"*.
3. **No HTTP `GET` consume path exists anywhere in the example.** `D-20` —
   *"the consume path is `ProductClient` / an MCP tool ask — NEVER
   `GET /tenant/class/version`"*, part of locked criterion 47.

## Why claim 3 lives here rather than where it was first run

Plan `24.4-08` task 2 ran the no-HTTP-`GET` sweep ONCE, as a shell line in a
plan's `<verify>` block, in wave 6. Plan `24.4-09` then added
`server/serve.py`, `server/compose.py` and `server/egress-door.yaml`, and plan
`24.4-13` added `README.md` and `page/*`. Neither re-ran it. A one-shot grep in
wave 6 therefore asserted `D-20` against a tree missing the five files most
likely to violate it — the door itself among them. It is a COLLECTED test here
so that it runs on every build, over the tree as it now stands.

## Why the wording sweep declares TWO globs and not one

Criterion 2's subject includes *"any test name"*, and **every cp-04 test module
lives at `tests/examples/test_cp_04_*.py`, outside the example tree.** A single
glob over `examples/cp-04-corporate-family-tree/**` would cover no test name at
all while appearing to discharge the criterion in full. Both globs are declared
as data in :data:`DECLARED_GLOBS`, both are asserted non-empty, and the sweep is
proven able to fail from EACH of them — the phase record reproduces both
controls.

## Why the forbidden-phrase sweep uses a reviewed-denial allowlist

Two documents in this tree state a forbidden phrase in order to DENY it: the
specification quotes *"the exact replay anchor for `graph_snapshot_at`"* as a
claim that was struck, and `summary_explanations.md` lists *"a snapshot-pinned
read"* among the things the product does not give you. A sweep that tried to
tell an assertion from a denial by looking for negation words nearby would be
reading VOCABULARY rather than content — this phase's own defect class, seven
occurrences. So each denial is an explicitly REVIEWED entry in
:data:`REVIEWED_DENIALS`, anchored to a quotation of its surrounding text
rather than to a line number (`D-IMPL-114`). A new occurrence — including a new
denial — is RED until somebody reviews it and says why, which is the correct
direction for this check to fail in.

`tests/examples/test_cp_04_seams.py` carries the gate roster; this module
carries what is true of the PHASE rather than of the product.
"""

from __future__ import annotations

import ast
import fnmatch
import io
import pathlib
import re
import subprocess
import tokenize
from typing import NamedTuple, Sequence

import pytest

#: Anchored on this file rather than on ``Path.cwd()``: a scan root that depends
#: on the working directory passes or fails for reasons that have nothing to do
#: with the tree. ``parents[2]`` is the repo root from ``tests/examples/<mod>.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

PHASE_DIR = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "24.4-corporate-family-tree-cp-04-first-multi-store-product-fluree"
)

#: Where the phase's diff BASE is pinned, with the paragraph explaining why it
#: is that commit. A committed file rather than a literal in a function body,
#: on `D-GATE-20`'s reasoning: a base that does not resolve makes every
#: assertion built on it VACUOUS instead of red, and a bare SHA in source has
#: nowhere to put the justification.
BASE_COMMIT_FILE = PHASE_DIR / "24.4-BASE-COMMIT.txt"

#: Where the phase's diff CEILING is pinned. `D-IMPL-188`: a ceiling of `HEAD`
#: makes each untouched-tree assertion say two things — *this phase did not
#: write here*, and *no later phase may ever write here*. Only the first was
#: commissioned.
CEILING_COMMIT_FILE = PHASE_DIR / "24.4-CEILING-COMMIT.txt"

#: Criterion 49 names `src/` alone. `runtime/` is carried beside it because
#: Gate 1's Conflict 1 (`D-IMPL-225` amendment 1) turned on a `runtime/`
#: module — `build_egress_server` registering its product resource
#: unconditionally — and the phase RECORDED that as `D-34` rather than fixing
#: it. Whether `runtime/` moved is therefore worth asserting rather than
#: assuming, in both directions.
FABRIC: tuple[str, ...] = ("src/", "runtime/")

#: The positive control for :func:`fabric_diff`. A pathspec that matches
#: nothing produces an EMPTY diff and a zero exit — indistinguishable from a
#: tree that genuinely did not move (`VAC-01`; `D-GATE-21` finding `B-1`, where
#: `-- scr/` passed as `-- src/` for five waves). This tree DID move across the
#: same window, so a run in which it reports empty is a run in which the
#: instrument is broken.
CHANGED_TREE: tuple[str, ...] = ("examples/",)

#: A SHA that resolves to nothing, for the refusal that proves an unresolvable
#: base is failed rather than silently passed.
UNRESOLVABLE_BASE = "0" * 40

#: **Criterion 2's two subjects, as data.** Globs rather than file lists, so a
#: document or a test module added later is covered by what already exists
#: rather than by an edit somebody has to remember to make.
DECLARED_GLOBS: tuple[str, ...] = (
    "examples/cp-04-corporate-family-tree/**",
    "tests/examples/test_cp_04_*.py",
)

#: `D-02` of `24.4-CONTEXT.md`, in exactly the words the criterion locks. The
#: qualifier *"for that run"* is load-bearing: `ledger_t` moved 4,560 → 5,112
#: between two sittings six days apart, which is the measurement proving quiet
#: is a property of a RUN and never of the store.
DECLARED_CLAIM = "byte-identical against a quiescent ledger for that run"


class Forbidden(NamedTuple):
    """One claim stronger than :data:`DECLARED_CLAIM`, and why it is stronger."""

    name: str
    pattern: str
    why: str


#: The forbidden claims, as DECLARED DATA rather than as literals scattered
#: through assertions. Deliberately narrow: the house idiom *"a right count
#: with a wrong member audits clean forever"* appears 30-odd times across this
#: tree and is not a reproducibility claim, so a bare `forever` is not swept.
FORBIDDEN_CLAIMS: tuple[Forbidden, ...] = (
    Forbidden(
        "replay-pinned",
        r"replay[-\s]?pinned",
        "asserts the read is anchored to a transaction; the Fluree adapter"
        " FLOORS and cannot PIN (`D-26`).",
    ),
    Forbidden(
        "pinned-to-t",
        r"pinned to\s*`?t`?\s*=",
        "names a transaction number as the anchor; `graph_snapshot_at` is a"
        " `datetime` and store `t` is an `int` (`D-27`).",
    ),
    Forbidden(
        "exact-replay-anchor",
        r"exact replay anchor",
        "the estate survey's struck claim (`D-03`); there is no such anchor at"
        " any value of `t`.",
    ),
    Forbidden(
        "snapshot-pinned",
        r"snapshot[-\s]pinned",
        "asserts a snapshot-bounded read; the adapter floors and does not pin.",
    ),
    Forbidden(
        "reproduces-forever",
        r"(deterministic|byte-identical|reproducible|reproduces)\s+forever"
        r"|always\s+(byte-identical|reproduces)",
        "drops the run qualifier entirely and asserts a property of the store.",
    ),
)

#: Words that make a statement a REPRODUCIBILITY claim rather than a comparison
#: of two values. `artifacts/gates.yaml` says one store's `legal_name` is
#: *"byte-identical to its `rdfs:label`"*, which is a fact about two strings and
#: not a claim about re-running anything.
REPRODUCIBILITY_WORDS: tuple[str, ...] = (
    "reproduc",
    "replay",
    "deterministic",
    "re-run",
    "rerun",
)

#: The qualifiers that make an occurrence of `byte-identical` legitimate. Both
#: bound the claim to something: the first to a run, the second to a graph
#: state. A reproducibility statement carrying neither is stronger than
#: :data:`DECLARED_CLAIM`.
DECLARED_QUALIFIERS: tuple[str, ...] = (
    "for that run",
    "quiescent ledger",
    "same graph state",
)

#: Snake-case forms of the forbidden claims, for TEST NAMES. A function name has
#: nowhere to put a qualifier, so any of these in a test name is a violation
#: outright — which is why the criterion names test names separately from
#: documents.
FORBIDDEN_IN_TEST_NAMES: tuple[str, ...] = (
    "replay_pinned",
    "pinned_to_t",
    "exact_replay_anchor",
    "snapshot_pinned",
    "byte_identical",
    "deterministic_forever",
    "reproduces_forever",
)


class Denial(NamedTuple):
    """A reviewed site where a forbidden phrase is STATED in order to be denied.

    Anchored on ``quote`` — a substring that must appear in the same block as
    the hit — rather than on a line number, so that deleting the surrounding
    denial stops the allowance applying instead of leaving it pointing at
    whatever moved into that line (`D-IMPL-114`, in spirit).
    """

    host: str
    claim: str
    quote: str
    why: str


#: The two reviewed denials in this tree. Each is asserted LIVE by
#: :func:`test_every_reviewed_denial_still_matches_something`, so a stale entry
#: is a red build rather than a hole nobody notices.
REVIEWED_DENIALS: tuple[Denial, ...] = (
    Denial(
        host="examples/cp-04-corporate-family-tree/spec/CP-SPEC-004_Corporate_Family_Tree.md",
        claim="exact-replay-anchor",
        quote="estate survey once asserted",
        why="§G.4's list of three things the document does NOT claim. The"
        " phrase is quoted as the estate survey's, and struck on 2026-08-31"
        " (`D-03`); the same block says *'There is no such claim here at any"
        " value of `t`, `4560` included.'*",
    ),
    Denial(
        host="examples/cp-04-corporate-family-tree/summary_explanations.md",
        claim="snapshot-pinned",
        quote="floors* the read at a minimum",
        why="the 'what this does not give you' list. The clause immediately"
        " after it says the adapter floors rather than pins, names the bound"
        " as a quiescent ledger for that run, and records it as an open gap.",
    ),
)

#: **This module's own file, excluded from the DOCUMENT half of the sweep BY NAME**
#: — the same move `tests/invariants/test_citation_coverage.py::CHECKER_OWN_FILES`
#: makes, and for the same reason: a file whose subject is the forbidden form
#: necessarily contains the forbidden form. Measured the moment this module became
#: tracked and began sweeping itself: **NINE** findings, and all nine sit in
#: :data:`FORBIDDEN_CLAIMS`' declared patterns, in :data:`REVIEWED_DENIALS`'
#: anchors, or in the prose explaining one of those. None is a claim about the
#: product.
#:
#: **THE HOLE THIS LEAVES, NAMED RATHER THAN LEFT IMPLICIT.** An over-claim written
#: into THIS file would not be caught by the document half. It would still be
#: caught by the TEST-NAME half and by the HTTP sweep, both of which continue to
#: read this file — asserted by
#: :func:`test_the_sweeps_own_module_is_excluded_from_exactly_one_half`, which also
#: refuses the exclusion growing past one path.
SWEEP_OWN_FILE = "tests/examples/test_cp_04_phase_record.py"

#: `D-20`'s forbidden consume paths, as CALL FORMS. A call form carries its
#: opening parenthesis, which is what separates *using* an HTTP client from
#: *naming* one in a sentence that refuses it — and this tree contains two such
#: refusing sentences, in `run.py` and in the specification.
FORBIDDEN_HTTP_CALLS: tuple[str, ...] = (
    "requests.get(",
    "requests.post(",
    "httpx.get(",
    "httpx.post(",
    "urllib.request.urlopen(",
    "urlopen(",
    "http.client.HTTPConnection(",
    "aiohttp.ClientSession(",
)

#: `D-20`'s forbidden request line, swept over CODE ONLY — see
#: :func:`code_text` for what "code" means per file type. The two occurrences of
#: this string in the tree are both PROSE saying there is no such path, which is
#: precisely why a line-oriented grep is the wrong instrument here.
FORBIDDEN_HTTP_ROUTE = re.compile(r"GET\s+/")


# ===========================================================================
# git, and the refusals that keep an empty answer from meaning two things
# ===========================================================================


def _git(*args: str) -> str:
    """`git` with `check=True` semantics spelled out.

    An empty stdout from a FAILED command reads exactly like an empty stdout
    from a real answer, and every untouched-tree assertion in this module is a
    statement about an empty stdout.
    """
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"`git {' '.join(args)}` exited {completed.returncode}:"
            f" {completed.stderr.strip()}"
        )
    return completed.stdout


def phase_base_commit() -> str:
    """The pinned base, read from the file that records why it is that commit."""
    return BASE_COMMIT_FILE.read_text(encoding="utf-8").splitlines()[0].strip()


def phase_ceiling_commit() -> str:
    """The pinned ceiling, read from the file that records why it is that commit."""
    return CEILING_COMMIT_FILE.read_text(encoding="utf-8").splitlines()[0].strip()


def commit_resolves(rev: str) -> bool:
    """Whether `rev` names an object this repository holds."""
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{rev}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def tracked_under(paths: Sequence[str]) -> list[str]:
    """Every tracked path the pathspec `paths` matches.

    The refusal `D-GATE-21`'s close panel added to Phase 21's equivalent, after
    finding that `-- scr/` had stood in for `-- src/` through five waves: a
    pathspec naming nothing produces an empty diff and a zero exit, which is
    indistinguishable from a tree that did not move.
    """
    return [line for line in _git("ls-files", "--", *paths).splitlines() if line]


def fabric_diff(base: str, paths: Sequence[str], ceiling: str) -> list[str]:
    """`git diff --name-only <base>..<ceiling> -- <paths>`, as a list of paths."""
    out = _git("diff", "--name-only", f"{base}..{ceiling}", "--", *paths)
    return [line for line in out.splitlines() if line]


# ===========================================================================
# The declared globs, and what they resolve to
# ===========================================================================


def swept_files() -> list[pathlib.Path]:
    """Every file the two declared globs cover, as absolute paths.

    **Tracked files only, deliberately.** The example's documentation page is
    GENERATED into `page/cp-04.html` and `.gitignore` excludes it, so it is
    present in a working tree that has run `build_page.py` and absent in a
    fresh clone. A sweep whose subject set depends on whether somebody ran a
    generator is a sweep whose result is not reproducible — and no claim can
    reach the render except through `template.html`, `README.md`, the spec,
    `summary_explanations.md` or `artifacts/expected.yaml`, every one of which
    is tracked and swept here.
    """
    tracked = _git("ls-files").splitlines()
    hits: list[pathlib.Path] = []
    for rel in tracked:
        for glob in DECLARED_GLOBS:
            pattern = glob[:-1] + "*" if glob.endswith("**") else glob
            if fnmatch.fnmatch(rel, pattern):
                hits.append(REPO_ROOT / rel)
                break
    return sorted(hits)


def blocks(text: str) -> list[tuple[int, str]]:
    """`text` split into blocks of consecutive non-blank lines.

    Returns `(first_line_number, block_text)`. A block is the unit the sweep
    reads a statement in: a markdown paragraph or bullet, a YAML comment run, a
    docstring paragraph. Sentence-level would be too narrow — one denial in
    this tree opens with a bolded fragment and carries its refusal in the next
    sentence — and file-level would be far too wide.
    """
    out: list[tuple[int, str]] = []
    current: list[str] = []
    start = 1
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip():
            if not current:
                start = lineno
            current.append(line)
        elif current:
            out.append((start, "\n".join(current)))
            current = []
    if current:
        out.append((start, "\n".join(current)))
    return out


def code_text(path: pathlib.Path) -> str:
    """`path`'s content with prose removed, so a REFUSAL is not read as a USE.

    - `.py` — comments dropped by `tokenize`, docstrings dropped by `ast`.
      `tools.lints.citations::prose_lines` is deliberately NOT reused: it
      classifies a whole line as prose when the line carries a trailing
      comment, so `import x  # GET /y` and `do_http()  # note` both vanish.
    - `.yaml` / `.yml` — the portion of each line after an unquoted `#`.
    - `.md` — everything OUTSIDE a fenced code block, since documented prose is
      where this tree's two refusing sentences live.
    - anything else — returned whole.
    """
    source = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix

    if suffix == ".py":
        lines = source.splitlines()
        drop: set[int] = set()
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.COMMENT:
                    lines[token.start[0] - 1] = (
                        lines[token.start[0] - 1][: token.start[1]]
                    )
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(
                    node,
                    (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    continue
                body = getattr(node, "body", [])
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    first = body[0].lineno
                    last = body[0].end_lineno or first
                    drop.update(range(first, last + 1))
        except (SyntaxError, tokenize.TokenError):  # pragma: no cover - defensive
            return source
        return "\n".join(
            "" if lineno in drop else line
            for lineno, line in enumerate(lines, 1)
        )

    if suffix in {".yaml", ".yml"}:
        return "\n".join(line.split("#", 1)[0] for line in source.splitlines())

    if suffix == ".md":
        kept: list[str] = []
        fenced = False
        for line in source.splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
                kept.append("")
                continue
            kept.append(line if fenced else "")
        return "\n".join(kept)

    return source


def collected_test_names() -> list[tuple[str, int, str]]:
    """Every `def test_*` in the swept `.py` files, as `(host, line, name)`."""
    found: list[tuple[str, int, str]] = []
    for path in swept_files():
        if path.suffix != ".py":
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defensive
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            ):
                found.append((rel, node.lineno, node.name))
    return found


# ===========================================================================
# The sweeps
# ===========================================================================


class Finding(NamedTuple):
    """One swept violation, named by its file, its line and its phrase."""

    host: str
    line: int
    claim: str
    excerpt: str


def _excused(host: str, claim: str, block: str) -> bool:
    """Whether a reviewed denial covers this hit."""
    return any(
        denial.host == host and denial.claim == claim and denial.quote in block
        for denial in REVIEWED_DENIALS
    )


def over_claims() -> list[Finding]:
    """Every claim stronger than :data:`DECLARED_CLAIM` in the two globs."""
    findings: list[Finding] = []
    for path in swept_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel == SWEEP_OWN_FILE:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for start, block in blocks(text):
            lowered = block.lower()

            for forbidden in FORBIDDEN_CLAIMS:
                if not re.search(forbidden.pattern, lowered):
                    continue
                if _excused(rel, forbidden.name, block):
                    continue
                findings.append(
                    Finding(rel, start, forbidden.name, block.strip()[:200])
                )

            if "byte-identical" not in lowered:
                continue
            if not any(word in lowered for word in REPRODUCIBILITY_WORDS):
                continue
            if any(q in lowered for q in DECLARED_QUALIFIERS):
                continue
            if _excused(rel, "unqualified-byte-identical", block):
                continue
            findings.append(
                Finding(
                    rel,
                    start,
                    "unqualified-byte-identical",
                    block.strip()[:200],
                )
            )
    return findings


def over_claiming_test_names() -> list[Finding]:
    """Every test NAME carrying a claim stronger than :data:`DECLARED_CLAIM`."""
    findings: list[Finding] = []
    for host, line, name in collected_test_names():
        lowered = name.lower()
        for token in FORBIDDEN_IN_TEST_NAMES:
            if token in lowered:
                findings.append(Finding(host, line, token, name))
    return findings


def http_consume_paths() -> list[Finding]:
    """Every HTTP consume path in the cp-04 tree — `D-20`, criterion 47."""
    findings: list[Finding] = []
    for path in swept_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if not rel.startswith("examples/cp-04-corporate-family-tree/"):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(raw.splitlines(), 1):
            for call in FORBIDDEN_HTTP_CALLS:
                if call in line:
                    findings.append(Finding(rel, lineno, call, line.strip()[:160]))
        for lineno, line in enumerate(code_text(path).splitlines(), 1):
            if FORBIDDEN_HTTP_ROUTE.search(line):
                findings.append(
                    Finding(rel, lineno, "GET /", line.strip()[:160])
                )
    return findings


# ===========================================================================
# Criterion 49 — the SDK did not move
# ===========================================================================


def test_the_pinned_phase_base_resolves() -> None:
    """A base that does not resolve makes every assertion built on it vacuous."""
    base = phase_base_commit()
    assert len(base) == 40 and all(c in "0123456789abcdef" for c in base), (
        f"{BASE_COMMIT_FILE.name}'s first line must be a full 40-character SHA,"
        f" got {base!r}. An abbreviation can become ambiguous as the history"
        " grows, and a pin that stops resolving fails OPEN here."
    )
    assert commit_resolves(base), (
        f"the pinned phase base {base} does not resolve in this repository."
        " Every untouched-tree assertion below is `git diff <base>..<ceiling>`"
        " required to be EMPTY, and an unresolvable base would make them"
        " vacuously green rather than red."
    )


def test_the_pinned_diff_ceiling_resolves_and_is_a_strict_descendant() -> None:
    """A ceiling at or before the base makes the window empty and everything green."""
    base = phase_base_commit()
    ceiling = phase_ceiling_commit()
    assert commit_resolves(ceiling), (
        f"the pinned diff ceiling {ceiling} does not resolve."
    )
    assert base != ceiling, "an empty window proves nothing."
    merge_base = _git("merge-base", base, ceiling).strip()
    assert merge_base == base, (
        f"the ceiling {ceiling[:7]} is not a descendant of the base"
        f" {base[:7]} — `git merge-base` gives {merge_base[:7]}. The window"
        " does not span the phase."
    )


def test_an_unresolvable_base_is_refused_rather_than_read_as_empty() -> None:
    """The refusal that keeps a failed `git` from reading as a clean tree."""
    assert not commit_resolves(UNRESOLVABLE_BASE)
    with pytest.raises(AssertionError):
        fabric_diff(UNRESOLVABLE_BASE, FABRIC, phase_ceiling_commit())


def test_the_fabric_pathspec_names_a_tracked_subject() -> None:
    """`VAC-01`. A misspelled pathspec diffs empty exactly like a clean tree."""
    for path in FABRIC:
        assert tracked_under([path]), (
            f"the pathspec {path!r} matches NO tracked file, so a diff over it"
            " is empty for a reason that has nothing to do with whether the"
            " tree moved. `D-GATE-21` finding `B-1`: `-- scr/` stood in for"
            " `-- src/` through five waves, green the whole way."
        )
    assert not tracked_under(["srcc/"]), (
        "the near-miss control `srcc/` matched something, so this refusal no"
        " longer distinguishes a real pathspec from a typo."
    )


def test_the_diff_instrument_can_report_a_change() -> None:
    """The positive control. An instrument that reports nothing reports nothing."""
    moved = fabric_diff(phase_base_commit(), CHANGED_TREE, phase_ceiling_commit())
    assert moved, (
        f"{CHANGED_TREE} reports EMPTY across the phase window. The whole cp-04"
        " example tree was built inside that window, so an empty answer here"
        " means the diff instrument is broken and the emptiness asserted below"
        " is worth nothing."
    )


def test_no_file_under_src_moved_across_the_phase() -> None:
    """Locked criterion 49 — *'no file under `src/` is modified by it'*."""
    moved = fabric_diff(phase_base_commit(), ["src/"], phase_ceiling_commit())
    assert moved == [], (
        "criterion 49 requires `src/` to be untouched across Phase 24.4."
        f" Modified: {moved}. The phase RECORDS SDK gaps (`D-26`..`D-36`); a"
        " separate phase closes them (`D-04` of `24-CONTEXT.md`)."
    )


def test_no_file_under_runtime_moved_across_the_phase() -> None:
    """Not named by criterion 49, and worth asserting because of Conflict 1."""
    moved = fabric_diff(phase_base_commit(), ["runtime/"], phase_ceiling_commit())
    assert moved == [], (
        "`runtime/` moved across Phase 24.4."
        f" Modified: {moved}. Gate 1's Conflict 1 turned on"
        " `runtime/ccf_runtime/mcp/egress.py::build_egress_server` registering"
        " its product resource unconditionally, and `D-IMPL-225` amendment 1"
        " RECORDED that as `D-34` rather than editing it."
    )


# ===========================================================================
# Criterion 2 — no over-claim in either declared glob
# ===========================================================================


def test_the_wording_sweep_declares_two_globs() -> None:
    """One glob would cover no test name, and criterion 2 names test names."""
    assert DECLARED_GLOBS == (
        "examples/cp-04-corporate-family-tree/**",
        "tests/examples/test_cp_04_*.py",
    ), (
        "criterion 2's subject is the README, the spec, the documentation page"
        " AND any test name. Every cp-04 test module lives outside the example"
        " tree, so a single glob over the example tree covers no test name at"
        " all while appearing to discharge the criterion."
    )


def test_both_declared_globs_resolve_to_files() -> None:
    """Non-vacuity. A sweep over nothing is clean over an empty tree."""
    swept = {p.relative_to(REPO_ROOT).as_posix() for p in swept_files()}
    from_example = {
        p for p in swept if p.startswith("examples/cp-04-corporate-family-tree/")
    }
    from_tests = {
        p for p in swept if p.startswith("tests/examples/test_cp_04_")
    }
    assert len(from_example) >= 20, (
        f"the example glob resolved to {len(from_example)} tracked files."
    )
    assert len(from_tests) >= 7, (
        f"the test glob resolved to {len(from_tests)} tracked modules."
    )
    for required in (
        "examples/cp-04-corporate-family-tree/README.md",
        "examples/cp-04-corporate-family-tree/summary_explanations.md",
        "examples/cp-04-corporate-family-tree/page/template.html",
        "examples/cp-04-corporate-family-tree/page/build_page.py",
        "examples/cp-04-corporate-family-tree/spec/CP-SPEC-004_Corporate_Family_Tree.md",
    ):
        assert required in swept, (
            f"criterion 2 names {required} as a subject and the sweep did not"
            " reach it."
        )


def test_the_declared_claim_is_stated_in_the_documents_that_make_it() -> None:
    """The other half of criterion 2: the claim IS made, in exactly those words."""
    for host in (
        "examples/cp-04-corporate-family-tree/README.md",
        "examples/cp-04-corporate-family-tree/summary_explanations.md",
        "examples/cp-04-corporate-family-tree/spec/CP-SPEC-004_Corporate_Family_Tree.md",
        "examples/cp-04-corporate-family-tree/page/template.html",
    ):
        text = (REPO_ROOT / host).read_text(encoding="utf-8")
        assert DECLARED_CLAIM in text, (
            f"{host} does not state the declared claim {DECLARED_CLAIM!r} in"
            " exactly those words. Gate 1 found this sentence line-WRAPPED in"
            " the specification, where `grep -F` reported it missing while it"
            " sat plainly on the page; it is kept on one line for that reason."
        )


def test_no_claim_stronger_than_the_declared_phrase_appears_in_any_document() -> None:
    """Criterion 2, the document half, over both declared globs."""
    findings = over_claims()
    assert findings == [], "\n".join(
        [
            "a claim stronger than the declared reproducibility phrase was"
            f" found. The declared claim is {DECLARED_CLAIM!r} and no stronger"
            " claim may appear in the README, the spec, the documentation page"
            " or any test name (criterion 2, `D-02`).",
            *(
                f"  {f.host}:{f.line} [{f.claim}] {f.excerpt!r}"
                for f in findings
            ),
        ]
    )


def test_no_test_name_carries_a_claim_stronger_than_the_declared_phrase() -> None:
    """Criterion 2, the test-name half — the half a one-glob sweep drops."""
    findings = over_claiming_test_names()
    assert findings == [], "\n".join(
        [
            "a cp-04 test NAME carries a claim stronger than"
            f" {DECLARED_CLAIM!r}. A function name has nowhere to put the"
            " qualifier, so the phrase is forbidden outright there.",
            *(f"  {f.host}:{f.line} [{f.claim}] {f.excerpt}" for f in findings),
        ]
    )


def test_the_test_name_sweep_reads_a_non_empty_population() -> None:
    """Non-vacuity for the half that is easiest to leave unswept."""
    names = collected_test_names()
    assert len(names) >= 100, (
        f"the test-name sweep collected {len(names)} names. cp-04 ships more"
        " than that; a collector that found few has stopped reading the tree."
    )
    hosts = {host for host, _, _ in names}
    assert len(hosts) >= 7, f"names came from only {len(hosts)} modules: {hosts}"


def test_every_reviewed_denial_still_matches_something() -> None:
    """A stale allowlist entry is a hole nobody notices; here it is a red build."""
    for denial in REVIEWED_DENIALS:
        text = (REPO_ROOT / denial.host).read_text(encoding="utf-8")
        assert denial.quote in text, (
            f"reviewed denial {denial.claim} on {denial.host} anchors on"
            f" {denial.quote!r}, which is no longer in that file. Either the"
            " denial was rewritten — in which case re-anchor it — or it was"
            " removed, in which case delete the entry."
        )
        assert any(
            re.search(f.pattern, text.lower())
            for f in FORBIDDEN_CLAIMS
            if f.name == denial.claim
        ), (
            f"reviewed denial {denial.claim} on {denial.host} excuses a phrase"
            " that no longer appears there. An allowlist entry that covers"
            " nothing is one that will silently cover the next thing."
        )


# ===========================================================================
# Criterion 47 in part — `D-20`, and no HTTP GET consume path
# ===========================================================================


def test_no_http_get_consume_path_exists_anywhere_in_the_cp_04_tree() -> None:
    """`D-20`, standing rather than one-shot. See this module's docstring."""
    findings = http_consume_paths()
    assert findings == [], "\n".join(
        [
            "`D-20`: the consume path is `ProductClient` or an MCP tool ask,"
            " NEVER `GET /tenant/class/version`. Found:",
            *(
                f"  {f.host}:{f.line} [{f.claim}] {f.excerpt!r}"
                for f in findings
            ),
        ]
    )


def test_the_http_sweep_reads_the_files_added_after_the_one_shot_grep_ran() -> None:
    """Non-vacuity, aimed at the exact five files plan 08's grep never saw."""
    swept = {p.relative_to(REPO_ROOT).as_posix() for p in swept_files()}
    for late in (
        "examples/cp-04-corporate-family-tree/server/serve.py",
        "examples/cp-04-corporate-family-tree/server/compose.py",
        "examples/cp-04-corporate-family-tree/server/egress-door.yaml",
        "examples/cp-04-corporate-family-tree/README.md",
        "examples/cp-04-corporate-family-tree/page/template.html",
    ):
        assert late in swept, (
            f"{late} was added AFTER plan `24.4-08`'s one-shot grep ran in wave"
            " 6, and the standing sweep must reach it. That is the whole reason"
            " this check was moved out of a plan's verify block."
        )


def test_the_code_text_stripper_distinguishes_a_use_from_a_refusal() -> None:
    """The discriminator this sweep turns on, asserted rather than assumed.

    Two files in this tree say `GET /tenant/class/version` in order to refuse
    it. A line-oriented grep reads a token present in BOTH the compliant and
    the violating case, which measures vocabulary and not content — this
    phase's own defect class.
    """
    refusals = (
        "examples/cp-04-corporate-family-tree/run.py",
        "examples/cp-04-corporate-family-tree/spec/CP-SPEC-004_Corporate_Family_Tree.md",
    )
    for rel in refusals:
        path = REPO_ROOT / rel
        raw = path.read_text(encoding="utf-8")
        assert FORBIDDEN_HTTP_ROUTE.search(raw), (
            f"{rel} no longer refuses `GET /` in prose, so this control has"
            " lost its subject and proves nothing. Re-aim it."
        )
        assert not FORBIDDEN_HTTP_ROUTE.search(code_text(path)), (
            f"{rel}'s refusal survived the prose stripper, so the sweep cannot"
            " tell a refusal from a use."
        )


def test_the_sweeps_own_module_is_excluded_from_exactly_one_half() -> None:
    """The exclusion in :data:`SWEEP_OWN_FILE` is one file and one half.

    A checker excluding its own file is a standing hole. This asserts the hole
    is exactly the size it is documented to be: one path, dropped from the
    DOCUMENT half only, with the TEST-NAME half and the HTTP sweep still
    reading the same file.
    """
    swept = {p.relative_to(REPO_ROOT).as_posix() for p in swept_files()}
    assert SWEEP_OWN_FILE in swept, (
        "the sweep no longer collects its own module at all, so the two halves"
        " that are supposed to keep reading it are not reading it either."
    )
    hosts_with_names = {host for host, _, _ in collected_test_names()}
    assert SWEEP_OWN_FILE in hosts_with_names, (
        "the TEST-NAME half must still read this module — it is the half the"
        " document exclusion does NOT cover."
    )
    assert SWEEP_OWN_FILE not in {f.host for f in over_claims()}, (
        "the document half is supposed to skip this module."
    )
    # And the exclusion is a single literal, not a pattern that could grow.
    assert isinstance(SWEEP_OWN_FILE, str) and SWEEP_OWN_FILE.endswith(".py"), (
        "SWEEP_OWN_FILE must stay one concrete path. A glob here would let the"
        " document half go quiet over a whole tree."
    )


# ---------------------------------------------------------------------------
# C-20's prose half (plan 24.6-14): the two sentences that said Decision Replay
# carried NO assembler identity are retired, for THIS rung only.
# ---------------------------------------------------------------------------

#: The retired sentences, as the README and summary carried them until
#: 2026-09-05. Plan 24.6-13 threads `assembler_id`/`assembler_version` into the
#: replay record for fulfilled AND refused decisions
#: (`tests/examples/test_cp_04_seams.py::test_replay_carries_the_assembler_identity_for_fulfilled_and_refused`),
#: so a page saying replay carries none of it states a gap that is closed.
#: Scoped to cp-04 rather than added to the tree-wide sweep on purpose: the
#: same sentence stands on cp-01 and cp-02, whose replay wiring this phase did
#: not touch, and a vocabulary entry there would assert something nobody
#: measured about those rungs. The `spec/` directory is a dated record and is
#: not a host here.
RETIRED_REPLAY_SENTENCES: tuple[str, ...] = (
    "carries none of it today",
    "is a phase 24.6 ledger row",
    "evidence the example can carry today",
)

#: Where the retired sentences lived, and where they must not return.
REPLAY_PROSE_HOSTS: tuple[str, ...] = (
    "examples/cp-04-corporate-family-tree/README.md",
    "examples/cp-04-corporate-family-tree/summary_explanations.md",
)


def test_the_replay_carriage_sentences_are_retired_on_this_rung() -> None:
    """The prose says what `test_replay_carries_the_assembler_identity_for_fulfilled_and_refused` proves."""
    survivors = []
    for host in REPLAY_PROSE_HOSTS:
        lowered = (REPO_ROOT / host).read_text(encoding="utf-8").lower()
        for sentence in RETIRED_REPLAY_SENTENCES:
            if sentence in lowered:
                survivors.append(f"{host}: {sentence!r}")
    assert survivors == [], "\n".join(survivors)


def test_the_replay_carriage_guard_is_not_vacuous(tmp_path: pathlib.Path) -> None:
    """Positive control: a copy of the README with one retired sentence planted is caught."""
    planted = tmp_path / "README.md"
    planted.write_text(
        (REPO_ROOT / REPLAY_PROSE_HOSTS[0]).read_text(encoding="utf-8")
        + "\nDecision Replay carries none of it today.\n",
        encoding="utf-8",
    )
    lowered = planted.read_text(encoding="utf-8").lower()
    assert any(sentence in lowered for sentence in RETIRED_REPLAY_SENTENCES)
