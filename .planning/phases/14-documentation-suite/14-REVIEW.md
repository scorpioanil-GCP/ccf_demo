---
phase: 14-documentation-suite
reviewed: 2026-08-03T00:00:00Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - tools/publish_scan.py
  - tools/publish_scan_tests/__init__.py
  - tools/publish_scan_tests/test_publish_scan.py
  - tools/publish_scan_tests/test_docstring_leaks.py
  - tools/docs_tests/__init__.py
  - tools/docs_tests/test_diagram_coverage.py
  - tools/docs_tests/test_mkdocstrings_gate.py
  - tools/docs_tests/test_openapi_drift_control.py
  - tools/docs_tests/test_snippet_gate.py
  - tools/dump_openapi.py
  - perf/gate.py
  - tests/perf_gate/test_gate.py
  - tests/http_api/test_openapi.py
  - Makefile
  - mkdocs.yml
  - .github/workflows/ci.yml
  - pyproject.toml
  - .gitignore
  - perf/baselines/local.json
  - src/ccf/halflife/debt.py
  - src/ccf/halflife/decay.py
  - src/ccf/peering/__init__.py
  - src/ccf/projection/__init__.py
  - src/ccf/controlplane/artifacts.py
  - src/ccf/operators/planner.py
  - src/ccf/operators/categories.py
  - runtime/ccf_runtime/cdc/adapter.py
  - examples/00-quickstart/run.py
  - examples/05-workflow-hitl/run.py
  - examples/04-cross-process/run.py
  - examples/external/00-hello-context/client_bare.py
findings:
  critical: 3
  warning: 12
  info: 0
  total: 15
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-08-03
**Depth:** standard
**Files Reviewed:** 31
**Status:** issues_found

## Summary

The phase's centre of gravity is `tools/publish_scan.py`, a never-publish gate whose
own docstring claims "default-deny by existence" and "no exception mechanism." Three of
its guarantees do not hold as written, and all three were reproduced empirically against
the checked-out repo rather than inferred:

1. `pub04` (include escape) is evadable by three trivially-reachable directive forms,
   two of which mkdocs happily resolves and renders into a published page.
2. The `pub01` content scan is **default-allow by file suffix and by directory name**, not
   default-deny. A verbatim copy of `docs/CCF_Whitepaper_1-2.md` placed at `site/leak.mmd`
   or `site/build/leak.md` exits 0. `.mmd` files are not hypothetical — eleven of them ship
   in `site/diagrams/` today.
3. The scanner **fails open** when it cannot see anything: a missing or empty tree yields
   zero findings and exit 0, and one of its own tests passes vacuously for exactly this reason.

CI/Makefile wiring is otherwise sound: `docs-strict` runs pre-build scan → strict build →
site scan with no `|| true`, no `-` prefix, and no `continue-on-error`, and it is composed
into both `make ci` and the always-on `docs` job. All three gate test directories run
(`tools/publish_scan_tests` and `tools/docs_tests` in the docs job; `tests/perf_gate` under
`pytest tests`).

The `perf/gate.py` scoping change is **correct and does not suppress genuine drift** —
`perf/pytest.ini` makes `perf/` its own rootdir, so benchmark ids really are
`suites/<suite>/...`, the predicate is narrow, unattributable ids stay in scope, and
`tests/perf_gate/test_gate.py` covers all three polarities. Two residual soft spots are
recorded below as warnings.

Example `run.py` diffs are comment-only marker insertions; behavior, ordering and output
are unchanged (verified by diff). The `src/` and `runtime/` docstring rewordings were
checked line-by-line against the code they document and none was made factually wrong.

## Critical Issues

### CR-01: `pub04` include-escape check is evadable by three directive forms

**File:** `tools/publish_scan.py:96,113,247-260`
**Issue:** The check fires only when a snippet target *string-prefix-matches* `docs/` or
`.planning/`, and only for single-line `--8<-- "..."` directives. Reproduced against this
repo — all three of the following are reported as **clean** by `scan_prebuild`, and a real
`mkdocs build --strict` with the project's own `base_path: ["."]` /
`restrict_base_path: true` settings embedded `docs/DECISIONS.md` into the rendered page for
each of them (309 `D-IMPL`/`Decision` occurrences in the built HTML):

```markdown
--8<-- "./docs/DECISIONS.md"          <!-- leading ./ defeats startswith -->
--8<-- "public/../docs/DECISIONS.md"  <!-- inside base_path, so restrict_base_path allows it -->
--8<--
docs/DECISIONS.md                     <!-- pymdownx block form; _INCLUDE_RE never sees it -->
--8<--
```

`references/` (whitepaper chapter material, `references/CH03`, `references/CH07`) and
absolute paths are likewise unlisted. The module docstring states `restrict_base_path`
"blocks `../` traversal but not sibling access, so this is checked here" — sibling access
is precisely what is not being caught.

The post-build shingle scan only partially compensates: it caught the `DECISIONS.md` case
because that file quotes the whitepaper, but internal prose that does not quote the
whitepaper (`SPEC_INVENTORY.md` paraphrases, `PHASE_I*_GATE.md`, `.planning/` records)
passes `pub01` untouched.

**Fix:** Invert to a positive allowlist and normalize before comparing — an escape that is
not enumerated must be a finding, not a pass:

```python
INCLUDE_ALLOWED_PREFIXES: tuple[str, ...] = ("examples/", "public/")

_INCLUDE_LINE_RE = re.compile(r'^\s*-{2,}8<-{2,}\s*"?([^"\s]*)"?\s*$')

def _include_targets(text: str) -> Iterator[tuple[int, str]]:
    """Both pymdownx forms: inline `--8<-- "t"` and the block list form."""
    in_block = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = _INCLUDE_LINE_RE.match(line)
        if m and not m.group(1):          # bare `--8<--` toggles the block form
            in_block = not in_block
            continue
        if m:
            yield lineno, m.group(1)
        elif in_block and line.strip():
            yield lineno, line.strip().strip('"')

def _escapes(target: str) -> bool:
    stem = target.split(":", 1)[0]        # strip the `:section` suffix
    if pathlib.PurePosixPath(stem).is_absolute():
        return True
    resolved = pathlib.PurePosixPath(os.path.normpath(stem)).as_posix()
    return not resolved.startswith(INCLUDE_ALLOWED_PREFIXES)
```

### CR-02: the content scan is default-allow by suffix and by directory name

**File:** `tools/publish_scan.py:99-107,213-215,225-229`
**Issue:** `scan_tree` only runs the shingle check on files whose suffix is in
`TEXT_SUFFIXES`; everything else gets `scan_path` (filename only). `iter_files`
additionally drops any path with a segment in `SKIP_DIRS` (`build`, `dist`, `.venv`, …)
before scanning. Both are allowlists in a gate whose stated posture is default-deny.

Reproduced: with `site/` fixtures containing a byte-for-byte copy of
`docs/CCF_Whitepaper_1-2.md` at `leak.mmd` and at `build/leak.md`, the scan printed nothing
and exited **0**. `.mmd` is not a synthetic suffix — mkdocs copies `public/diagrams/*.mmd`
verbatim into `site/diagrams/`, so unscanned non-`TEXT_SUFFIXES` files are already part of
the shipped tree. `.pdf`, `.csv`, `.svg`, `.mmd` and any future asset type are all
publish channels the gate does not read.

`SKIP_DIRS` is also matched against `path.parts` of the *full* path, so scanning an
absolute tree under a directory named `build`/`dist` skips every file silently.

**Fix:** Scan by exclusion, not inclusion, and restrict `SKIP_DIRS` to the walk root:

```python
#: Suffixes whose bytes are genuinely not prose. Everything else is READ.
BINARY_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".woff", ".woff2", ".ttf", ".ico", ".gz"}
)

def scan_tree(root: pathlib.Path) -> list[str]:
    shingles = whitepaper_shingles()
    findings: list[str] = []
    for path in iter_files(root):
        findings.extend(scan_path(path))
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue                       # bytes, not prose — path-checked only
        findings.extend(
            scan_text(path.read_text(encoding="utf-8", errors="ignore"), path, shingles)
        )
    return findings
```
and in `iter_files`, evaluate `SKIP_DIRS` against `path.relative_to(root).parts`, not
`path.parts`.

### CR-03: the scan fails OPEN on a missing, empty, or misdirected tree

**File:** `tools/publish_scan.py:208-217,299-327`
**Issue:** `iter_files` returns `[]` when `root` is not a directory; `scan_tree` and
`scan_prebuild` therefore return no findings and `main` returns 0. Verified:

```
$ python tools/publish_scan.py /tmp/nope-tree ; echo $?
0
```

and `scan_prebuild(Path('/tmp/nonexistent')) == []`. If `site_dir` is ever retargeted, a
build partially fails, or the scan is invoked with a typo'd path, the gate reports **clean
over nothing**. `self_test_fires()` does not close this: it only proves the shingle
machinery still matches the whitepaper file, never that the published tree was actually
read. This is the exact failure mode the module docstring says the self-test exists to
prevent ("a scan that passes everything, which is worse than no scan at all"), left open
one level up.

**Fix:** Make an unreadable or empty tree a hard error in both modes:

```python
def _require_populated(root: pathlib.Path, mode: str) -> list[pathlib.Path]:
    if not root.is_dir():
        raise SystemExit(f"{mode}: {root} is not a directory — the gate cannot "
                         "certify a tree it did not read (fail closed)")
    files = iter_files(root)
    if not files:
        raise SystemExit(f"{mode}: {root} contains no files — refusing to report "
                         "clean over an empty tree")
    return files
```
Call it from both `scan_tree` and `scan_prebuild`, and add regression tests asserting a
nonzero exit for a missing `site/` and a missing `public/`.

## Warnings

### WR-01: whitepaper figures and the `references/` tree are outside every token list

**File:** `tools/publish_scan.py:86-96`
**Issue:** `INTERNAL_PATH_TOKENS` names five tokens, but the internal tree contains
`DECISIONS.md`, `DESIGN.md`, `FEASIBILITY.md`, `ROADMAP.md`, `PHASE_I*_GATE.md` (covered
only incidentally via `PHASE_I`), `docs/figures/Fig-CH01-01.png` … and `references/CH03`,
`references/CH07`. `_FIGURE_RE` catches a figure *cited in text*, but a copied figure
**image** at `site/Fig-CH07-03.png` is `.png` (no text scan) and matches no path token.
**Fix:** Add `"DECISIONS"`, `"DESIGN"`, `"FEASIBILITY"`, `"ROADMAP"`, `"references"` to
`INTERNAL_PATH_TOKENS`, and apply `_FIGURE_RE` to path segments as well as to line content
in `scan_path`.

### WR-02: `pub02` token matching is case-sensitive

**File:** `tools/publish_scan.py:144-153`
**Issue:** `_token_matches` compiles the token verbatim. `site/ccf_whitepaper_1-2/index.html`
— the exact form a lowercased slug produces — does not match `CCF_Whitepaper`.
**Fix:** `re.search(pattern, segment, re.IGNORECASE)`. The boundary anchors keep the
`PHASE_INTEGRATION` control intact; add a lowercase case to
`test_the_real_internal_deliverable_name_still_matches`.

### WR-03: `normalize()` does no unicode or HTML-entity normalization

**File:** `tools/publish_scan.py:116-124`
**Issue:** `_NON_WORD_RE` deletes every non-`[a-z0-9 ]` codepoint, so an NFD-composed
accent (`cafe` + U+0301) tokenizes differently from its NFC form (`caf`), and an
HTML-escaped `&amp;`/`&nbsp;` injects a spurious `amp`/`nbsp` token that splits the
ten-word window. Either difference is enough to break a shingle match on rendered HTML
that is nonetheless a verbatim quote.
**Fix:** In `normalize`, run `html.unescape(text)` and
`unicodedata.normalize("NFKD", ...)` before the substitutions, and add tests for an
entity-escaped and an NFD-composed quote.

### WR-04: three gate assertions are CWD-relative and pass vacuously off-root

**File:** `tools/publish_scan.py:75,140,303`; `tools/publish_scan_tests/test_publish_scan.py:163-166`; `tools/publish_scan_tests/test_docstring_leaks.py:25-34`
**Issue:** `WHITEPAPER`, `PREBUILD_TREE` and `DOCUMENTED_TREES` are relative strings.
`test_main_exits_zero_in_prebuild_mode_on_this_repo` asserts `main(["--pre-build"]) == 0` —
which is also what a *missing* `public/` returns (see CR-03), so the test's comment
("the pre-build tree is a constant, so the mode cannot be pointed somewhere harmless")
does not hold. `_iter_python_files()` likewise rglobs relative `src`/`runtime` and yields
an empty list off-root, making `test_no_docstring_reproduces_whitepaper_body_text` pass
over zero files. `tools/docs_tests/test_diagram_coverage.py` gets this right with
`REPO_ROOT = Path(__file__).resolve().parents[2]` plus an explicit
`test_fixture_trees_are_populated` precondition.
**Fix:** Anchor all three to `pathlib.Path(__file__).resolve().parents[N]`, and add the
same populated-fixture precondition to the docstring-leak module:
`assert _iter_python_files(), "no python sources scanned"`.

### WR-05: the docstring-leak gate misses attribute docstrings and `#:` comments

**File:** `tools/publish_scan_tests/test_docstring_leaks.py:37-58`
**Issue:** `_iter_docstrings` visits only `ClassDef`/`FunctionDef`/`AsyncFunctionDef` plus
the module docstring. griffe (and therefore mkdocstrings) *also* publishes PEP 258
attribute docstrings — the bare string literal following an assignment — and `#:` comment
docs, which this codebase uses heavily (`publish_scan.py` itself is written in that style).
Whitepaper prose in either channel is published and untested here.
**Fix:** Extend the walker to collect the string-literal `ast.Expr` following each
`ast.Assign`/`ast.AnnAssign`, and to collect contiguous `#:` comment runs via `tokenize`.

### WR-06: the "gate.py never writes baselines" test is a weak source grep

**File:** `tests/perf_gate/test_gate.py:317-323`
**Issue:** The assertion only fires when `"baselines"` and `open(`/`write_text` appear on
the *same source line*. `p = BASELINES_DIR / "x.json"` on one line followed by
`p.write_text(...)` on another passes, as does `shutil.copy`, `os.replace`, or `json.dump`
to an open handle. It is a control that reads as structural but discriminates almost
nothing — the same class as the `grep -o` and inverted-`grep -c` defects already found.
**Fix:** Replace the line grep with an AST check that no call whose receiver traces back
to `BASELINES_DIR` is a mutating call, or (simpler and honest) a behavioural test:
`monkeypatch` `BASELINES_DIR` to a tmp dir, run `main()` in every mode, and assert the
directory's contents are byte-identical before and after.

### WR-07: `--suite` is never cross-checked against the ids that actually ran

**File:** `perf/gate.py:179-250,318-343`
**Issue:** `baseline_entry_in_scope` scopes on the *baseline* side only. Nothing asserts
that the *results* belong to the declared suite. `python perf/gate.py scale.raw.json
--suite micro` scopes away every scale baseline entry, reports every scale result as
`NO BASELINE — NOT GATED`, and exits 0 — a whole suite silently ungated. The Makefile pairs
them correctly today, so this is latent rather than live. Related: the scoping fix depends
on `perf/pytest.ini` keeping `perf/` as its own rootdir; invoked as `pytest perf/suites/micro`
from the repo root the ids become `perf/suites/...`, the prefix test fails, and everything
stays in scope (fail-safe direction, but the fix silently stops working).
**Fix:** In `evaluate`, assert the executed results agree with the declared suite:

```python
mismatched = sorted(
    k for k in results
    if k.startswith(SUITE_ID_PREFIX) and not baseline_entry_in_scope(k, suite)
)
if mismatched:
    raise ValueError(
        f"--suite {suite!r} does not own these result ids: {mismatched[:3]} … "
        "the gate would scope away the baseline for the suite that really ran"
    )
```

### WR-08: an empty results set gates nothing and exits 0

**File:** `perf/gate.py:198-250`
**Issue:** If pytest collects no benchmarks (a renamed suite directory, a collection error
swallowed by `-q`), `load_raw` yields `{}`, `evaluate` produces no rows, every in-scope
baseline entry emits a warning, and the run is green. A suite that measured nothing is
indistinguishable from a suite that passed.
**Fix:** When `baseline is not None and not results`, set `report.exit_code = 1` with an
explicit "suite produced no benchmarks" message.

### WR-09: the `assemble` snippet region spans an unbalanced `try:` block

**File:** `examples/00-quickstart/run.py:199,227`
**Issue:** `# --8<-- [start:assemble]` opens before the `registry = ControlPlaneRegistry()`
statement, but `# --8<-- [end:assemble]` sits *inside* the `try:` suite. The published
snippet on `public/tutorial/adopters-guide.md` therefore ends with a `try:` that has no
`except`/`finally` — with `dedent_subsections: true` the reader is shown code that cannot
be pasted and run, which is the failure mode the snippet gate exists to prevent (an
unhelpful snippet, rather than an empty one). Example behavior is unaffected.
**Fix:** Close the region before `try:` and open a separate `[start:ingest-loop]` region
for the loop body, or move the region end to after the `try/finally` closes.

### WR-10: a real leak emits one finding line per matching shingle

**File:** `tools/publish_scan.py:181-190,307-316`
**Issue:** `scan_text` appends a finding for *every* intersecting shingle. A whole-file
leak against a 107,712-shingle corpus prints tens of thousands of lines to stdout and
reports a violation count in the same order — the operator has to scroll past the signal
to find the filename. The repo's own `docs/DESIGN.md` positive control produces ~60 per
file; a whitepaper copy produces far more.
**Fix:** Emit one finding per file with the hit count and the first N examples:

```python
hits = sorted(shingles_of(normalize(text)) & shingles)
if hits:
    findings.append(format_finding(
        path, 1, RULE_SHINGLE,
        f"reproduces whitepaper body text: {len(hits)} matching "
        f"{SHINGLE_WORDS}-word run(s), e.g. {hits[0]!r}",
    ))
```
Adjust `test_internal_derived_doc_is_a_positive_control` (which currently asserts `> 20`
findings) to assert on the reported hit count instead.

### WR-11: `.github/workflows/ci.yml` carries a stale, now-false header NOTE

**File:** `.github/workflows/ci.yml:5-7`
**Issue:** "the `python -m tools.lints` runner lands in plan 04-02. Until it does, the lint
job on this branch fails by design" — `tools/lints` has existed for ten phases and the lint
job passes. A comment that documents a deliberate red build, left in place after the build
went green, teaches readers to discount the file's other (load-bearing, and correct)
"deliberately NOT `continue-on-error`" comments.
**Fix:** Delete the NOTE block.

### WR-12: `_rules()` parses findings positionally and breaks on a path containing a space

**File:** `tools/publish_scan_tests/test_publish_scan.py:28-29`
**Issue:** `f.split()[1]` assumes the rule id is the second whitespace-delimited token of
`format_finding`'s output. Any path with a space, or any change to the finding format,
silently shifts the index and turns every `RULE_X in _rules(...)` assertion into a
comparison against the wrong field — a test that fails for the wrong reason at best, and
matches the wrong token at worst.
**Fix:** Assert on substring membership (`any(RULE_SHINGLE in f for f in findings)`), as
the neighbouring `test_whitepaper_text_trips_the_shingle_rule` already does.

---

## Verified-correct (checked, no finding)

Recorded because the phase context asked these questions directly:

- **CI/Makefile wiring executes the gate.** `docs-strict` = pre-build scan → `mkdocs build
  --strict` → site scan, three separate recipe lines, no `-` prefix, no `|| true`, no
  `set +e`, no pipe. It is in `make ci` and in the always-on `docs` job, which is not
  `continue-on-error`. `tools/publish_scan_tests` and `tools/docs_tests` run in the docs
  job; `tests/perf_gate` is under `testpaths = ["tests"]` and runs in the test job.
- **`perf/gate.py` scoping does not suppress genuine drift.** `perf/pytest.ini` roots the
  perf tree, so ids are `suites/<suite>/...` (matching `perf/baselines/local.json`); the
  predicate scopes only on an exact owner-segment match, unattributable ids stay in scope,
  and `test_drift_check_still_warns_within_the_suite_that_ran` covers the vanished-benchmark
  case. See WR-07/WR-08 for the residual soft spots.
- **Example `run.py` diffs are comment-only.** `git diff 416fdda..HEAD -- examples` shows
  only `# --8<-- [start:…]` / `[end:…]` line insertions plus one README link fix; no logic,
  ordering or output change. (WR-09 is about where one marker pair was placed, not about
  behavior.)
- **Docstring rewordings are not factually wrong.** Each of the eight reworded docstrings
  was compared against the code it documents — notably `effective_half_life`
  (`micros = half_life // µs * risk_sensitivity`, so "below one shortens, above one widens"
  still holds), `context_debt` (`1 − F·C·S`, multiplicative-conjunctive as described), and
  the planner's `Policy → Similarity → Temporal → Traversal` ordering claim. All whitepaper
  section citations were preserved, as `test_docstring_leaks.py`'s docstring requires.
- **No No-Hardcoding, harness-import, or domain-value violation** was introduced by this
  phase's `src/` changes (docstring text only).

---

_Reviewed: 2026-08-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
