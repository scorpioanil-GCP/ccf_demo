# Phase 21: Requirement-Ledger Reconciliation — What Is Actually Discharged - Pattern Map

**Mapped:** 2026-08-21
**Files analyzed:** 4 new artifacts (1 test module, 1 optional shared parser, 1 pinned-base file, 1 diff helper — the helper may live inside the test module)
**Analogs found:** 4 / 4 — every new artifact has a shipped in-tree analog. **Nothing here is greenfield except the markdown-table parser itself**, and even that has a shape precedent (`tools/docs_tests/_prose.py`).

> **Scope note.** This phase creates almost no new files. It writes verdicts into
> `.planning/REQUIREMENTS.md` status cells and adds standing checks. The file list below is
> exactly the set RESEARCH.md §5 and §8 name — it is not expanded here.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/docs_tests/test_requirement_ledger.py` — Check A (bare-basename / nonexistent-path REFUSAL, D-06/criterion 4) | standing gate (test module over a tracked document) | file-I/O → transform → refusal list | `tools/docs_tests/test_no_stale_example_paths.py` | **exact** — same predicate (`(REPO_ROOT / token).exists()`), same directory, same gate leg, same control style |
| …same module — Check B (two-channel agreement, D-02/criterion 10) | standing gate (structural parse + set comparison) | file-I/O → parse → set diff | `tools/docs_tests/test_advisory_discharge.py` | **exact** — reader functions + preconditions section + doctored-copy controls |
| …same module — the **sabotage controls** (D-08, `D-IMPL-170`) | control tests | pure-function-over-doctored-input | `tests/examples/test_hw1_harness_clients_runner_gates.py` | **exact** — this module *is* `D-IMPL-170`'s named discharge |
| Strict-parse helper (module-level functions, or `tools/docs_tests/_ledger.py` if split) | utility / shared reader | transform (text → structured rows) | `tools/docs_tests/_prose.py` | **role-match** — no markdown-**table** parser exists anywhere in the tree; `_prose.py` is the precedent for *how to extract one shared reader once* |
| `fabric_diff(base, paths)` (criterion 12) + `.planning/phases/21-*/21-BASE-COMMIT.txt` | utility + config artifact | subprocess → string | `tests/examples/test_hw1_harness_clients_readme.py:462-506` + `.planning/phases/20-*/20-BASE-COMMIT.txt` | **exact** — copy verbatim, widen the path tuple |

**Verified absences.** `grep -rn 'split("|")' tools/ tests/ --include=*.py` returns one unrelated
hit; there is **no markdown-table parser in the tree** to reuse. `grep -rln 'REQUIREMENTS.md'
tools/ tests/` returns only `tools/lints/citations.py` and `tools/lints/tests/test_citations.py`,
both prose mentions. The parser is genuinely new code; everything around it is copied.

---

## Wiring: how a new file reaches `make gate-tools`

**Automatic. No registration.** Confirmed by reading the mechanism, not by assuming it.

`Makefile:188-190`:

```make
gate-tools: ## Run the tools/ suites CI runs that `testpaths` excludes from `make test`
	$(ENV_DOCS) $(PYTHON) -m pytest tools/lints/tests -q
	$(ENV_DOCS) $(PYTHON) -m pytest tools/publish_scan_tests tools/docs_tests -q
```

with `PYTHON := .venv/bin/python` (`Makefile:10`) and `ENV_DOCS := PYTHONPATH=.:src:runtime`
(`Makefile:23`). Leg 2 is a **directory argument to pytest**, so any new `tools/docs_tests/test_*.py`
is collected on the next run with no edit to the Makefile, `pyproject.toml`, or CI.

Reachability upward:
- `Makefile:138` — `ci-core: lint typecheck test gate-tools ## Mid-phase verification sweep — MUST stay green from Wave 1 onward`
- `Makefile:172` — `ci: ci-core examples docs-strict gate-tools`
- `.github/workflows/ci.yml:339` — `run: pytest tools/publish_scan_tests tools/docs_tests -q` (the docs job, run **before** `make docs-strict`)
- `.github/workflows/ci.yml:35` — `run: pytest tools/lints/tests -q` (the lint job)

`pyproject.toml:142` — `testpaths = ["tests"]` — is why `tools/` needs `gate-tools` at all. **The
one thing that would break wiring is putting the new module anywhere other than
`tools/lints/tests/`, `tools/publish_scan_tests/` or `tools/docs_tests/`.** A new sibling
directory (`tools/ledger_tests/`) would be invisible to every gate — that is the exact defect
`Makefile:130-137` records as `DEF-17-08`, *"THREE WAVES SHIPPED PAST A RED GATE."*

`tools/docs_tests/test_openapi_drift_control.py:18-22` states the precedent in its own words:

```python
"""...
This lives in `tools/docs_tests/` rather than `tests/` for the reason
`tools/lints/tests/` states: a gate's own controls sit outside `testpaths`
and run in the CI step that precedes the gate they defend. Plan 14-10's CI
job already runs `pytest tools/publish_scan_tests tools/docs_tests -q`, so
this file joins that step with no further wiring.
"""
```

---

## Pattern Assignments

### `tools/docs_tests/test_requirement_ledger.py` — Check A (D-06 refusal)

**Analog: `tools/docs_tests/test_no_stale_example_paths.py`** (308 lines). Closest because it is
*the same predicate*: it asserts that every path token named in prose exists on disk, it lives in
the target directory, and it carries the exact five-part structure Check A needs (readers →
preconditions → shipped assertions → controls with a baseline).

**Imports pattern** (`test_no_stale_example_paths.py`, head + `test_advisory_discharge.py:61-72`):

```python
from __future__ import annotations

import pathlib
import re
import shutil

import pytest

from tools.docs_tests import _prose
```

`_prose.REPO_ROOT` is the root every docs_test resolves against, and the reason is documented at
`tools/docs_tests/_prose.py:59-64`:

```python
#: The repo root, resolved from this file rather than from the process CWD.
#: A CWD-relative walk yields zero pages off-root and turns every gate built on
#: this module into a test that passes over nothing — WR-04's exact failure,
#: recorded at
#: `tools/publish_scan_tests/test_docstring_leaks.py::test_the_walk_does_not_depend_on_the_process_cwd`.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
```

**Core predicate + offender-list pattern** (`test_no_stale_example_paths.py:83-107`) — copy this
shape exactly; `refuse_unresolvable` is `prose_path_offenders` with a different token regex:

```python
def _resolves(target: str) -> bool:
    return (_prose.REPO_ROOT / target).exists()


def prose_path_offenders(pages: list[pathlib.Path]) -> list[str]:
    """`page:line -> missing path` for every unresolvable prose path token."""
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages, prose_only=False):
        for token in PATH_TOKEN.findall(paragraph.raw):
            if not _resolves(token):
                offenders.append(
                    f"{_prose.relative(page)}:{paragraph.lineno} -> {token}"
                )
    return offenders
```

Three properties to carry across verbatim: **a list of strings, not a bool**; **each entry names
the location and the offending token**; **the function takes its subject as an argument** (here
`pages`), which is what makes the controls possible.

⚠️ For Check A, RESEARCH.md §4(d) requires `.is_file()`, not `.exists()` — a citation naming a
*directory* must not resolve as a file citation. Deviate deliberately and say so in the docstring.

**Preconditions / vacuity-guard pattern** (`test_no_stale_example_paths.py:130-163`) — this is
CONTROL 5 in RESEARCH.md §5, and the section banner is part of the pattern:

```python
# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_the_published_tree_is_populated() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    assert _prose.published_pages(), f"no markdown pages under {_prose.PUBLIC_DIR}"


def test_the_scan_finds_path_tokens_to_check() -> None:
    """The corpus contains example paths at all.

    Without this the assertion below passes over an empty set — and it would do
    so most convincingly right after a rewrite renamed every example directory,
    which is precisely when it is needed.
    """
    tokens = prose_path_tokens(_prose.published_pages())
    assert tokens, (
        "no examples/ or tests/examples/ path token found in published prose — "
        "this gate is scanning nothing"
    )


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _prose.published_pages(), "the walk resolved against the CWD, not the repo"
```

The `monkeypatch.chdir` test is cheap and directly relevant: this phase's checker resolves cited
paths against a root, and a CWD-relative resolution refuses everything or nothing depending on
where pytest was invoked.

**Shipped-assertion pattern** (`test_no_stale_example_paths.py:170-177`) — the failure message
explains *why the property matters*, not just what failed:

```python
def test_every_prose_path_reference_resolves_on_disk() -> None:
    offenders = prose_path_offenders(_prose.published_pages())
    assert not offenders, (
        "published prose names paths that do not exist. These are invisible to "
        "the strict build because they are not snippet includes — the page just "
        "starts lying: " + "; ".join(offenders)
    )
```

For Check A the message must name the **second** reason it exists (RESEARCH.md Pitfall 3): the
citation lint catches a symbol *rename* but silently drops a file *move*.

**Citation-token regexes to reuse rather than re-derive** — import or mirror from
`tools/lints/citations.py`, do not hand-roll:

```python
# tools/lints/citations.py:251-253
NODE_ID = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.py)::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"
)
```

```python
# tools/lints/citations.py:245-248
CITATION = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.(?:" + _SUFFIX_ALT + r"))"
    r":(?P<lines>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)(?![\w-])"
)
```

The refusal predicate closes both holes because of `resolve_cited`'s ordering
(`tools/lints/citations.py:429-449`) — the direct branch fires first and the index is never
consulted:

```python
def resolve_cited(
    cited: str, base: pathlib.Path, index: dict[str, list[str]]
) -> tuple[pathlib.Path | None, bool]:
    """Resolve a cited path; returns ``(path, ambiguous)``.

    A path that exists as written wins outright. ...
    """
    direct = base / cited
    if direct.is_file():
        return direct, False
    name = cited.rsplit("/", 1)[-1]
    candidates = [
        c for c in index.get(name, ()) if c == cited or c.endswith("/" + cited)
    ]
    if len(candidates) == 1:
        return base / candidates[0], False
    return None, len(candidates) > 1
```

If the check ever needs the ambiguity *count* for a message (CONTROL 1 asserts the message names
the ambiguity), reuse `citations.repo_index` (`tools/lints/citations.py:365-377`) rather than a
bare `rglob` — it prunes `SKIP_DIRS` (`:220`), which is the `DEF-17-04` worktree hazard
RESEARCH.md Pitfall 10 records.

---

### `tools/docs_tests/test_requirement_ledger.py` — Check B (two-channel agreement)

**Analog: `tools/docs_tests/test_advisory_discharge.py`** (533 lines). Closest because it is the
docs_tests module that (a) parses a *structured region* out of a tracked non-Markdown-prose file,
(b) holds two independent readings of the repo to each other, and (c) carries a full numbered
control suite including a positive control.

**Region-slicing pattern** (`test_advisory_discharge.py:120-147`) — the nav block is sliced by a
header regex with a lookahead, exactly the shape the traceability-table locate needs. Note the
comment explaining the lookahead's failure mode, which is the same failure mode a table parser
has when the table is last in the file:

```python
#: The nav block: from the top-level ``nav:`` key to the next top-level key, or
#: to end of file — `nav:` is last in `mkdocs.yml` today, and a lookahead that
#: only accepted a following key would silently parse nothing if it stayed last.
NAV_BLOCK = re.compile(r"^nav:\s*$(?P<body>.*?)(?=^\S|\Z)", re.MULTILINE | re.DOTALL)

#: One nav entry's page path.
NAV_PAGE = re.compile(r":\s*([A-Za-z0-9_][A-Za-z0-9_./-]*\.md)\s*$", re.MULTILINE)


# --------------------------------------------------------------------------
# Readers.
# --------------------------------------------------------------------------


def nav_pages(config_text: str) -> set[str]:
    """Every page path enumerated in `mkdocs.yml`'s nav, `public/`-relative."""
    block = NAV_BLOCK.search(config_text)
    if block is None:
        return set()
    return set(NAV_PAGE.findall(block.group("body")))
```

⚠️ **Deviate on one point.** `nav_pages` returns `set()` on a missed header — that is exactly the
"0 disagreements, clean" failure CONTROL 8 must refuse. Check B's parser must either **raise** or
return a value the caller refuses. `test_advisory_discharge.py` gets away with it because
`test_the_published_tree_and_the_nav_are_populated` (`:274-282`) holds the floor separately:

```python
def test_the_published_tree_and_the_nav_are_populated() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    assert _prose.published_pages(), f"no markdown pages under {_prose.PUBLIC_DIR}"
    assert MKDOCS_CONFIG.is_file(), f"missing site config: {MKDOCS_CONFIG}"
    pages = nav_pages(_config_text())
    assert pages, "no nav entries parsed from mkdocs.yml — the nav block moved"
    assert "index.md" in pages, f"nav parsed but looks wrong: {sorted(pages)[:5]}"
```

`assert "index.md" in pages, f"nav parsed but looks wrong: {sorted(pages)[:5]}"` is the shape to
copy for the ledger: **a floor on the count is not enough; assert a known member is present.** The
ledger's equivalents are `133 ids each side` and e.g. `"HARD-01" in ids`.

**Doctored-copy control pattern** (`test_advisory_discharge.py:412-426`) — the `_copy` helper and
the baseline test that makes every later refusal attributable to the mutation:

```python
# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may check nothing.
# --------------------------------------------------------------------------


def _copy(tmp_path: pathlib.Path, relative: str) -> pathlib.Path:
    source = _prose.PUBLIC_DIR / relative
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / pathlib.Path(relative).name
    shutil.copy(source, target)
    return target


def test_the_unmodified_copies_pass(tmp_path: pathlib.Path) -> None:
    """The controls' baseline: every refusal below comes from the mutation."""
    a8 = _copy(tmp_path, A8_PAGE)
    assert a8_offenders(a8) == []
    assert submodule_import_sites([a8], []) == []
    assert stale_boot_signatures([a8]) == []
```

**Both polarities** (`test_advisory_discharge.py:491-521`) — the negative control and its positive
twin, with docstrings saying which half of the discrimination proof each is:

```python
def test_the_a3_gate_refuses_a_stale_boot_signature(
    tmp_path: pathlib.Path,
) -> None:
    """The pre-15.4 spelling, which is exactly what A-3 found published.

    This is also this half's non-vacuity proof: HEAD carries no `boot(`
    invocation with arguments, so without a control the assertion would be
    passing over an empty set with nobody the wiser.
    """
    page = _copy(tmp_path, A8_PAGE)
    with page.open("a", encoding="utf-8") as handle:
        handle.write('\n```py\nboot(database_path="graph.db", tenant_id="acme")\n```\n')
    offenders = stale_boot_signatures([page])
    assert offenders, "the gate admitted a boot() call with a parameter it lacks"
    assert any("database_path" in offender for offender in offenders), offenders


def test_the_a3_gate_admits_a_correct_boot_signature(
    tmp_path: pathlib.Path,
) -> None:
    """Both polarities: a current call must not be reported.

    Without this the stale-signature control would also pass if the extractor
    reported every keyword it found.
    """
```

That second docstring is the argument for RESEARCH.md §5's **positive control** on Check A
(`src/ccf/client/client.py::ProductClient` must **not** be refused).

---

### The sabotage-control idiom — the part that matters most

**Analog: `tests/examples/test_hw1_harness_clients_runner_gates.py`.** This module is
`D-IMPL-170`'s **named discharge** (`docs/DECISIONS.md:501`: *"Discharged by
`tests/examples/test_hw1_harness_clients_runner_gates.py`, which carries `CONTROL 1`-`9b`"*). It is
the reference implementation of "standing test, not a SUMMARY probe."

**The idiom, in one sentence:** *the checker is a pure function of a document (or of a stdout, or
of a text); the shipped assertion hands it the real subject and expects `[]`; the control hands
**the very same function** a doctored subject and asserts a non-empty refusal.* Both are GREEN in
CI. The control is green **because it observed the refusal fire**. Nothing is mutated on disk,
nothing is skipped, nothing lives in a SUMMARY.

**Module docstring** (`test_hw1_harness_clients_runner_gates.py:1-29`) — quote-worthy in full,
because the last paragraph is the contract:

```python
"""Standing sabotage controls for the four runner gates that carry Criteria 1-4.

`examples/hw1-harness-clients/runner/drive.py` holds the checks that decide
whether a harness leg actually did what this phase claims: ...

**Why this module exists.** Those checks shipped with their controls run as
one-shot mutation probes, recorded as a RED->GREEN table in a plan SUMMARY.
Dave ruled (2026-08-21) that a probe recorded only in a SUMMARY does not
discharge `CLNT-12`:

    A control is something the suite can still run and that can still go red. A
    narrative measurement in a SUMMARY is evidence that someone looked once; it
    is not enforcement. [...] If the property is worth claiming, it gets a real
    control.

The close panel's B-3 named the gap and B-1 was its direct consequence: an
asymmetry between `marker_violations` (which compared whole WORDS) and
`observed_markers` (which matches raw SUBSTRINGS) let a row named `product`,
`text` or `ntex` be accepted as a payload marker and then be satisfied by
chrome alone — so an address-only leg passed the very check written to refuse
it. No standing control was positioned to see it.

Every gate below therefore appears twice: once driven with the real inputs it
sees on a default-path run, and once with the property deliberately broken and
the gate watched going red.
"""
```

**The non-vacuity twin that must precede the controls** (`:134-152`):

```python
# --- the shipped inputs pass -------------------------------------------------


def test_the_six_declared_names_are_accepted(drive: types.ModuleType) -> None:
    """Non-vacuity for every control below: the real markers are not refused.

    Without this, a `marker_violations` that refused everything would make each
    control below pass for the wrong reason.
    """
```

**One control in full** (`:166-186`) — note: parametrised over the five spellings that escaped, a
docstring naming *the defect it reproduces*, and a failure message naming the offending input:

```python
# --- CONTROL 1-3: marker_violations, watched refusing ------------------------


@pytest.mark.parametrize("name", ["product", "text", "ntex", "Product", "CONTEXT"])
def test_control_1_a_marker_chrome_can_satisfy_is_refused(
    drive: types.ModuleType, name: str
) -> None:
    """CONTROL 1 — B-1's escape, as a standing control.

    Each of these is a substring of something the runner, the reference client
    or the three harness clients print themselves. Accepting any of them makes
    "stdout carries a declared company name" true of a run that printed no
    payload at all, which is exactly what `payload_violations` exists to refuse.
    `product` is the one that matters most: all three clients print the literal
    line `context product`, and the vocabulary originally omitted the word.
    """
    violations = drive.marker_violations(
        [name, "Volanti Logistics"], sorted(drive.CONSOLE_VOCABULARY)
    )
    assert violations, f"{name!r} was accepted as a payload marker"


def test_control_2_an_empty_marker_set_is_refused(drive: types.ModuleType) -> None:
    """CONTROL 2 — the vacuity floor. A search over no markers passes on anything."""
    assert drive.marker_violations([], sorted(drive.CONSOLE_VOCABULARY))
```

**The exact idiom, itemised for the executor:**

1. **Section banner naming the numbered range and the function under control** —
   `# --- CONTROL 1-3: marker_violations, watched refusing ---`.
2. **Test name is a sentence carrying the control number** —
   `test_control_1_a_marker_chrome_can_satisfy_is_refused`. Numbered so a SUMMARY, a plan and a
   review can all refer to the same control by name.
3. **Docstring says which defect it reproduces and why acceptance would be wrong.**
4. **The control calls the SAME function the shipped assertion calls.** This is the load-bearing
   property. `tests/examples/test_hw1_harness_clients_readme.py:28-37` states the failure it
   avoids:

   ```python
   """...
   **Every property is a module-level function taking its subject as a
   parameter.** That is the design of the module rather than a style choice, and
   the defect class it avoids is the one this project has recorded across three
   phases: a control specified as *"copy the subject, break it, assert the check
   fails"* against an assertion that reads a **fixed path**. The copy is never
   what the assertion looks at, so the control passes for the wrong reason and
   the property stays unproven.
   """
   ```
5. **The assertion is `assert violations` / `assert offenders`, plus a second assertion that the
   message names the thing** — `assert any(element in violation for violation in violations)`
   (`test_hw1_harness_clients_readme.py:346-350`). A control that only checks non-emptiness passes
   when the checker refuses everything.
6. **A vacuity control per checker** — empty input set refuses rather than returns `[]`
   (CONTROL 2 above; `test_control_2_an_empty_required_mapping_is_a_vacuity_violation` at
   `test_hw1_harness_clients_readme.py:352-357`, which asserts on the refusal reason:
   `assert "mapping is empty" in violations[0]`).
7. **A baseline test proving the unmutated subject passes**, so every refusal is attributable to
   the mutation (`test_the_unmodified_copies_pass`).
8. **Nothing on disk is mutated.** `test_openapi_drift_control.py:25-27` states the discipline:
   *"It never writes. Not to `openapi.json`, not anywhere. The mutation is on a parsed copy held
   in memory."* Phase 21 must hold this hard — the subject is a tracked planning file inside three
   always-on machines.

**Mapping to RESEARCH.md §5's control table:**

| RESEARCH control | Idiom element | Nearest shipped twin |
|---|---|---|
| CONTROL 1 (`client.py::ask`, ambiguous) | doctored table text → `refuse_unresolvable` non-empty, message names ambiguity | `test_control_1_a_marker_chrome_can_satisfy_is_refused` |
| CONTROL 2 (`spine.py::ask`, unique basename) | parametrise CONTROL 1 over both spellings | the `@pytest.mark.parametrize` in CONTROL 1 |
| CONTROL 3 (`src/ccf/nope/nope.py::x`) | same function, nonexistent path | `test_the_gate_refuses_an_injected_missing_prose_path` (`test_no_stale_example_paths.py:212-223`) |
| CONTROL 4 (`docs/foo.md::heading`) | suffix-discipline refusal | `test_the_boot_extractor_does_not_match_load_and_boot` (boundary held from the false-positive side) |
| CONTROL 5 (vacuity) | zero rows / zero citations refuses | `test_control_2_an_empty_marker_set_is_refused` |
| positive control | real citation is **not** refused | `test_the_a3_gate_admits_a_correct_boot_signature` |
| CONTROL 6–7 (channel drift / missing id) | doctored table text | `test_control_1_a_readme_missing_one_element_names_that_element` |
| CONTROL 8 (misspelled table header → `{}`) | parser **refuses** rather than reporting clean | `test_the_published_tree_and_the_nav_are_populated`'s `assert pages, "…the nav block moved"` |
| CONTROL 9 (out-of-vocabulary verdict) | doctored cell with `Done` | `test_control_3_each_stated_marker_property_goes_red` (parametrised properties) |

---

### `fabric_diff(base, paths)` + `21-BASE-COMMIT.txt` (criterion 12)

**Analog: `tests/examples/test_hw1_harness_clients_readme.py:462-506`.** Copy verbatim; rename;
widen `paths`. RESEARCH.md §8 already specifies the widening (`src/ runtime/`, and per Pitfall 1
also `examples/ public/ docs/ pyproject.toml`).

```python
def phase_base_commit() -> str:
    """The pinned diff base, read from the file plan `20-01` wrote."""
    first_line = BASE_COMMIT_FILE.read_text(encoding="utf-8").splitlines()[0]
    return first_line.strip()


def client_surface_diff(base: str, paths: Sequence[str]) -> str:
    """``git diff --stat <base>..HEAD -- <paths>``, as a string.

    A function of its arguments so a control can hand it a base and a path that
    genuinely **do** differ and watch the assertion built on it fail. That
    control is the point of the whole design: *an assertion that a diff is
    empty passes trivially when the diff command is broken, unresolvable or
    misspelled*, and an empty string from a failed command is indistinguishable
    from an empty string from a clean tree. This project has recorded that
    check-that-cannot-fail shape across Phases 17, 18.1 and 19.

    Three refusals rather than a quiet empty string: an empty base, an empty
    path list (``git diff --stat <base>..HEAD --`` limits to nothing and prints
    nothing, forever), and a non-zero exit from `git` itself.
    """
    if not base.strip():
        raise AssertionError(
            "no diff base was given, so `git diff` would compare HEAD against"
            " nothing and print nothing — which reads exactly like a clean tree"
        )
    if not paths:
        raise AssertionError(
            "no paths were given, so the diff is limited to nothing and is"
            " empty regardless of what the phase changed"
        )
    completed = subprocess.run(
        ["git", "diff", "--stat", f"{base}..HEAD", "--", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"`git diff --stat {base}..HEAD -- {list(paths)}` exited"
            f" {completed.returncode}, so its empty output says nothing about"
            f" the tree.\nstderr: {completed.stderr.strip()}"
        )
    return completed.stdout
```

**Constants** (`:60-87`) — including `CHANGED_TREE`, the path that must genuinely differ, and its
maintenance note:

```python
#: Where plan `20-01` pinned criterion 7's diff base. Pinned in a file rather
#: than resolved at close time from a branch name, because a base that does not
#: resolve makes an "is empty" assertion vacuous rather than failing it.
BASE_COMMIT_FILE = (
    REPO_ROOT / ".planning" / "phases"
    / "20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a"
    / "20-BASE-COMMIT.txt"
)

#: A path that genuinely differs across this phase, for `CONTROL 6`. Every plan
#: of Phase 20 wrote here; if this ever came back empty the control would be
#: the thing to fix, not the assertion.
CHANGED_TREE = ("examples/",)

#: A SHA that resolves to nothing, for `CONTROL 7`. Hex so it is syntactically
#: a revision, absent so it is not one.
UNRESOLVABLE_BASE = "0000000000000000000000000000000000000000"
```

⚠️ For Phase 21 the only tree that *will* differ is `.planning/` (and the new test module), so
`CHANGED_TREE = (".planning/",)`. Pick it deliberately and comment why.

**The base-resolves precondition** (`:509-532`) — a full-SHA regex plus `git rev-parse --verify`:

```python
def test_the_pinned_diff_base_resolves() -> None:
    """Non-vacuity: the base is a commit `git` can actually reach. ..."""
    base = phase_base_commit()
    assert re.fullmatch(r"[0-9a-f]{40}", base), (
        f"the pinned base {base!r} is not a full SHA; a short or annotated"
        " value is one rename away from resolving to something else"
    )
```

**CONTROL 6 and 7** (`:562-598`) — the two that matter; CONTROL 6 is the one `20-08-SUMMARY.md`
records as having earned its place:

```python
def test_control_6_a_base_and_path_that_differ_produce_output() -> None:
    """CONTROL 6 — the diff machinery is watched producing something.

    **This is the control that matters.** Both assertions above pass on an
    empty string, and an empty string is what a broken command, an unresolvable
    base or a misspelled path all produce. Handing the same function a pair
    that genuinely differs is the only thing separating "the client surface did
    not change" from "nothing was compared".
    """
    diff = client_surface_diff(phase_base_commit(), CHANGED_TREE)
    assert diff.strip(), (...)


def test_control_7_an_unresolvable_base_fails_loudly() -> None:
    """CONTROL 7 — a base `git` cannot resolve raises instead of returning ''. ..."""
    try:
        result = client_surface_diff(UNRESOLVABLE_BASE, CLIENT_SURFACE)
    except AssertionError as failure:
        assert "exited" in str(failure)
        return
    raise AssertionError(
        "an unresolvable base returned"
        f" {result!r} instead of failing; an 'is empty' assertion built on"
        " that reports success for a comparison that never happened"
    )
```

**`21-BASE-COMMIT.txt` file format** — copy `.planning/phases/20-*/20-BASE-COMMIT.txt` byte-shape:
SHA alone on line 1, then `#` comment lines naming what reads it and why it is pinned:

```
9e4bd0e5c54c22133f32c108b96de3aebbf6dfae
# The Phase 20 diff base. Read by plan 20-08's criterion-7 assertion:
#   git diff --stat $(head -1 <this file>)..HEAD -- src/ccf/client/
# must print nothing. Pinned here at plan 20-01 rather than resolved at close
# time from a branch name, because a base that does not resolve makes the
# assertion vacuous rather than failing it.
```

Written in the **first** plan, not at close.

---

### The strict-parse helper

**No parser analog exists** (verified: no markdown-table parser anywhere in `tools/` or `tests/`).
The analog is for **whether and how to extract it**: `tools/docs_tests/_prose.py:1-13`.

```python
"""Paragraph-scoped reading of the published tree, extracted once.

**Why this module exists at all.** Three gates in this package need to ask a
question of the form *"does any published paragraph say X without also saying
Y?"* — the Gate-2 wording gate, the stale-path gate, and the documented-command
gate. `16-PATTERNS.md` § *No Analog Found* records that nothing in the tree did
paragraph-scoped matching over ``public/**/*.md``: two halves existed —
`tools.publish_scan.normalize` knows how to strip markup, and
`tools.lints.citations.citation_sentence` knows how to join a window and map an
offset back into it — and this module is their composition. Extracted once
rather than inlined three times, because three copies of a scoping rule drift
into three different scoping rules.
"""
```

**Read this as a threshold, not an instruction.** `_prose.py` was extracted because **three**
gates needed it. Phase 21 has **two** checks and RESEARCH.md §5 recommends one module holding
both, sharing the parser as module-level functions. That is consistent: extract to `_ledger.py`
only if the planner splits the checks into two modules. Either way, **do not write the parser
twice** — CONTEXT.md's discretion clause says the planner may split but "should not duplicate the
parser."

Naming convention for the leading `_`: a non-`test_` module inside `tools/docs_tests/` is not
collected by pytest and is imported as `from tools.docs_tests import _ledger`.

---

## Shared Patterns

### Test naming and docstrings
**Source:** `tools/lints/tests/test_citations.py:1-13`, `:64-99`
**Apply to:** every test in the new module

```python
"""Unit tests for the cross-file citation checker (`tools/lints/citations.py`).

Every case is built as a real two-file tree under `tmp_path`, because a
citation is a claim about a *second* file and a checker for it cannot be
exercised from one source string.

The first test in the file is the **watched-to-fail** case: it reproduces the
exact defect this checker was written for — a docstring edit above a function
shifts the function down and silently falsifies every citation of it — and it
asserts both halves, that the citation was true before the edit and false
after. That pair is what makes the check a discriminator rather than a
tripwire that is always red or always green.
"""
```

- **Test names are sentences.** `test_the_citation_is_clean_before_the_docstring_edit`,
  `test_a_docstring_edit_above_the_cited_symbol_is_caught`.
- **Every test carries a docstring saying which half of the discrimination proof it is.**
- **Section banners:** `# --- the watched-to-fail pair ---`.

### Fixture constants with `#:` provenance comments
**Source:** `tools/lints/tests/test_citations.py:38-61`
**Apply to:** every doctored-table fixture

```python
#: The cited module, before and after a two-line docstring insertion. The
#: insertion is the only difference; it moves `refuse` from line 5 to line 7.
_CITED_BEFORE = '''"""A module.
...
'''
```

`#:` comments (Sphinx-style attribute docs) are the house style for module-level constants across
`tools/` and `tests/`. Each says **what the constant is for and what the single difference is**.

### Small module-level helpers
**Source:** `tools/lints/tests/test_citations.py:29-36`
**Apply to:** the new module's fixture builders

```python
def _write(base: pathlib.Path, rel: str, text: str) -> pathlib.Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]
```

`encoding="utf-8"` is passed explicitly on **every** read and write in this tree, without
exception. The ledger carries em dashes and typographic quotes; do not rely on the platform
default.

### `from __future__ import annotations` first
Present in every module read for this map. Non-negotiable house style.

---

## The subject's own shape — `.planning/REQUIREMENTS.md`'s two channels

This is the pattern the verdict-writing plans copy, and the parser's input contract.

### Channel 1 — the checkbox list (lines 11–244, 133 ids)

Header context (`.planning/REQUIREMENTS.md:7-15`):

```markdown
## v0.2 Requirements

### Hardening (HARD)

- [ ] **HARD-01**: The D-IMPL ruling batch (WR-01 mapping shape, ApprovalGate×D-16 composition, perf governance, docs toolchain/publishing, D-10 amendment, create_app warning) is surfaced to Dave as one Phase D mini-cycle and rulings logged in `docs/DECISIONS.md`
- [ ] **HARD-02**: In-memory HITL transports are thread-safe with a documented Protocol concurrency contract and a passing stress test (WR-02)
- [x] **HARD-04**: HITL doors enforce per-tenant authorization per Dave's WR-01 ruling — deny-by-default, typed 403, authz decision in the audit record, cross-door × cross-action test matrix (WR-01)
```

Exact form: `- [ ] **ID**: <text>` or `- [x] **ID**: <text>`. RESEARCH.md §1's regex:
`r'^- \[([ xX])\] \*\*([A-Z]+-\d+)\*\*'`.

The checked rows carry their evidence **inline in the same bullet**, extended with `—
**COMPLETE** (…)` clauses and sometimes indented `  - ` sub-bullets (see `DCD-09` at `:148`,
`CPS-03` at `:125`). Sub-bullets are continuation lines, not new ids — the regex is anchored at
`^- ` and will not match them.

### Channel 2 — the traceability table (header at 264, separator 265, rows 266–398)

```markdown
## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 9 | Pending |
| HARD-02 | Phase 9 | Pending |
| HARD-04 | Phase 10 | Complete |
```

Exactly 3 cells per row after splitting on `|` and stripping. Contiguous run after the separator.

### The `DCD-` status-cell shape D-01 adopts verbatim

**`DCD-10`, the model CONTEXT.md names — quoted in full from `.planning/REQUIREMENTS.md:364`:**

```markdown
| DCD-10 | Phase 15.6 | **Complete over the ruled scope** (plan `15.6-11`, `D-IMPL-123`) — 101 of 114; the 13 `D-IMPL-114` names are held back by ruling |
```

The grammar, itemised: `**<bolded verdict>**` · ` (` · backticked citations comma-separated · `)`
· ` — ` (em dash, spaced) · the qualifying clause.

Its checkbox-channel twin (`.planning/REQUIREMENTS.md:149`) carries the *long* form with the
`path::symbol` evidence — note both channels agree on Complete-ness and the table cell is the
compressed summary:

```markdown
- [x] **DCD-10**: `DI-15.5-08` — the `.py`-target unanchored citation population is reduced over the ruled scope and cannot regrow, gated in **both** directions — **COMPLETE over the ruled scope** (plan `15.6-11`, `D-IMPL-123`: 101 of 114, holding back the 13 records `D-IMPL-114` names). `tests/invariants/test_citation_coverage.py::MAXIMUM_UNANCHORED_PY_CITATIONS` is **0** — the tree's first ceiling — with `::MINIMUM_SCANNED_CITATION_HOSTS` and `::MINIMUM_CITATIONS_READ` as the floors. It fired at this very gate, on the gate package itself
```

**The other four vocabulary shapes in force today** (`:356`, `:363`, `:365`, `:368`):

```markdown
| DCD-02 | Phase 15.6 | **Partial** (plans `15.6-05`, `15.6-06`) — carrier and replay plumbing Complete; pointer population **Pending by design** under `D-IMPL-119` limb 3(b), until the assembly path is principal-scoped |
| DCD-09 | Phase 15.6 | **Complete as ruled** (plan `15.6-10`, `D-IMPL-122`) — 39 multi-method Protocols descoped with a recorded reason, which travels with the requirement |
| DCD-11 | Phase 15.6 | **Complete** (plan `15.6-03`) — with `DI-15.6-01`(b), the schema-description channel, recorded as a known coverage hole owned by Phase 16 |
| DCD-12 | Phase 15.6 | **Complete** (plan `15.6-12`, `D-GATE-15.6`, Dave 2026-08-13) |
```

Two parser consequences the planner must carry:

1. **The verdict token is the leading bolded run, cut before `(` or `—`.** `DCD-02`'s cell
   contains a *second* bolded phrase (`**Pending by design**`) after the em dash. A parser that
   scans the whole cell for `**…**` finds two verdicts on a compliant row. RESEARCH.md §1's
   regex anchors at `^` for this reason.
2. **The Complete-family test is membership, not string inequality.** `Complete`,
   `Complete as ruled`, `Complete over the ruled scope`. A `!= "Complete"` predicate yields 56
   rows, not 54.

### The citation form already working in this file

35 of the file's 39 citations are `NODE_ID` (`.py::symbol`); only 4 are line citations. Live
examples from the checkbox channel (`:141`, `:143`):

```markdown
`src/ccf/halflife/decay.py::Observation`
`src/ccf/products/contract.py::ContextProductContract`
`tests/replay/test_engine_rehydration.py::test_a_rehydration_that_swaps_one_pointer_is_divergence`
`tests/invariants/test_no_obligation_vocabulary.py`
`src/ccf/products/bind.py::refuse_bound_payload`
```

Note the `::name` continuation form used for a second symbol in the same file
(`::MINIMUM_SCANNED_CITATION_HOSTS` at `:149`) — **`NODE_ID` will not match a bare `::name` with
no path**, so it is unchecked. Do not use it in new verdict cells; write the full path each time.

---

## Anti-Patterns — things in the tree that look like analogs but are weaker

| Anti-pattern | Where it appears | Why it is weaker |
|---|---|---|
| **A control recorded as a RED→GREEN table in a plan SUMMARY** | `20-03-SUMMARY.md` (`CONTROL A`–`F` over `drive.py`'s three gates) | Ruled insufficient at `docs/DECISIONS.md:501` (`D-IMPL-170`). *"A narrative measurement in a SUMMARY is evidence that someone looked once; it is not enforcement."* Its direct cost was close-panel `B-1` — an address-only leg passing the check written to refuse it. **This is D-08's whole reason for existing. Do not produce one.** |
| **A control that copies the subject and breaks the copy, against an assertion that reads a fixed path** | named as the avoided defect at `tests/examples/test_hw1_harness_clients_readme.py:28-37` | The copy is never what the assertion looks at, so the control passes for the wrong reason and the property stays unproven. Recorded across three phases. The fix is the parameterised-function design. |
| **A parser that returns `set()` / `{}` on a missed header** | `tools/docs_tests/test_advisory_discharge.py::nav_pages` (`:135-141`) | `return set()` on a `None` match. Safe *there* only because a separate precondition test asserts the parse is populated. For Check B this is CONTROL 8's exact subject — a misspelled table header must **refuse**, not report "0 disagreements, clean." Copy the structure, not the silent-empty return. |
| **`@pytest.mark.skipif` on a control** | `tools/lints/tests/test_substrate_names.py:193-196, 207-210, 233-236` | Legitimate there (the vocabulary may contain no generic stem), but a *skipped* control is a control that stopped checking without going red. Phase 21 has no environmental dependency; **no control in the new module should be skippable.** |
| **A stale claim about gate reachability in a module docstring** | `tools/docs_tests/test_resolver_seam_obligations.py:38-41` — *"`tools/docs_tests` runs as its own CI step and **not** under `make ci-core`"* | **False today.** `Makefile:138` is `ci-core: lint typecheck test gate-tools`. Do not copy that sentence into the new module; state reachability against `Makefile:138`/`:172`/`:188-190` as they read now. (Flag as an observation; fixing it is out of this phase's scope.) |
| **A gate whose failure is a warning, or which only runs by hand** | `make conformance` (`Makefile:152-153`, with its rationale at `:140-151`) — deliberately *not* a prerequisite of `ci`; `tools/retirement_sweep.py --report` — a script, and a **write** despite the flag name (`D-IMPL-154`) | A target that is "a NAME, not a second collection path" is fine when something else collects the tests. A new check placed anywhere `gate-tools` does not name would be invisible. **The new module goes in `tools/docs_tests/` and nowhere else.** |
| **Asserting only that a refusal list is non-empty** | the weak form of every control | A checker that refuses *everything* passes it. Every control pairs `assert violations` with `assert any(<the expected token> in v for v in violations)` and a baseline test proving the unmutated subject passes. |
| **Asserting that a document contains a string** (e.g. that `docs/DECISIONS.md` contains `D-GATE-21`) | not in the tree; named as the shape to avoid in RESEARCH.md §Validation criterion 14 | *"A test asserting the string `D-GATE-21` exists would be exactly the check-that-cannot-fail shape this project keeps recording."* Criterion 14 is inspection, correctly. |
| **A bare `rglob` when indexing the tree** | avoided by `tools/lints/citations.py:365-377`, which prunes `SKIP_DIRS` (`:220`) | `DEF-17-04` (2026-08-15): six live agent worktrees put seven entries under one basename and hid two real unanchored citations behind a green run. Reuse `citations.repo_index` or prune the same `SKIP_DIRS`. |
| **A floor expressed only as a count** | contrasted at `tools/docs_tests/test_advisory_discharge.py:280-282` | `assert pages` is weaker than `assert "index.md" in pages, f"nav parsed but looks wrong: {sorted(pages)[:5]}"`. For the ledger: assert 133 ids **and** that a known id is present in each channel. |

---

## No Analog Found

| File / element | Role | Data Flow | Reason |
|---|---|---|---|
| The markdown **traceability-table** parser (locate header → contiguous row run → 3-cell split → leading-bolded-verdict extraction) | utility | transform | Nothing in `tools/` or `tests/` parses a markdown table. `_prose.py` does paragraph scoping; `test_advisory_discharge.py` does YAML-block slicing; neither reads a pipe table. Use RESEARCH.md §1's algorithm, wrapped in the reader/precondition/control structure above. |
| A checker over `.planning/REQUIREMENTS.md` of any kind | gate | file-I/O | `grep -rln 'REQUIREMENTS.md' tools/ tests/` returns two files, both prose mentions. Greenfield subject, established shape. |

---

## Metadata

**Analog search scope:** `tools/docs_tests/`, `tools/lints/tests/`, `tools/publish_scan_tests/`,
`tests/examples/`, `tests/invariants/`, `tests/products/`, `Makefile`,
`.github/workflows/ci.yml`, `pyproject.toml`, `.planning/REQUIREMENTS.md`,
`.planning/phases/20-*/20-BASE-COMMIT.txt`, `docs/DECISIONS.md`.
**Files read for excerpts:** 12.
**Read-only:** no tracked file was modified in producing this map.
**Pattern extraction date:** 2026-08-21, against branch `phase-21` at `9455fc2`.
