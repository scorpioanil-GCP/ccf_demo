# Phase 14: Documentation Suite - Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 18 new/modified files
**Analogs found:** 15 / 18

> **Path correction (verify before planning).** `14-CONTEXT.md` §canonical_refs names
> **`src/ccf/lints/`** as the CINV lint harness location. **That directory does not exist.**
> The harness is at **`tools/lints/`** (`__init__.py`, `__main__.py`, `no_hardcoding.py`,
> `harness_imports.py`, `algorithmic.py`, `orchestration_imports.py`, `allowlist.yaml`,
> `tests/`). Every reference below is to the verified path. `14-RESEARCH.md` gets this right
> (`tools/lints/__main__.py`); CONTEXT does not.
>
> Also verified absent today: `mkdocs.yml`, `openapi.json`, `public/`, `site/` in `.gitignore`,
> and any `--8<--` marker inside `examples/` (the only existing `--8<--` directives in the repo
> are the 10 *include sites* in `docs/demo-walkthrough.md`, all whole-file).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/publish_scan.py` | lint/gate script | batch / file-I/O | `tools/lints/no_hardcoding.py` + `tools/lints/__main__.py` | exact |
| `tools/publish_scan_tests/` (or `tools/lints/tests/` sibling) | test | batch | `tools/lints/tests/test_harness_imports.py` | exact |
| `tools/docs_tests/test_snippet_gate.py` | test (negative control) | batch | `tools/lints/tests/test_harness_imports.py` (violating/clean split) | role-match |
| `tools/docs_tests/test_mkdocstrings_gate.py` | test (negative control) | batch | same | role-match |
| `tools/dump_openapi.py` | utility / generator | transform → file-I/O | `perf/gate.py` invocation shape + `tests/http_api/conftest.py::app` | role-match |
| `tests/http_api/test_openapi.py` (extend) | test (drift check) | request-response | same file, `test_the_document_serializes_as_json` | exact |
| `Makefile` (`docs`, `docs-strict`, `docs-serve`, `ci:`) | config / build | batch | `Makefile` `lint` / `perf-micro` targets | exact |
| `.github/workflows/ci.yml` (new `docs` job) | config / CI | batch | `ci.yml` `examples` job (lines 119–157) | exact |
| `pyproject.toml` (`docs` extra) | config | — | `[project.optional-dependencies] perf` / `harnesses` (lines 61–102) | exact |
| `.gitignore` (`site/`) | config | — | `perf/results/` entry | exact |
| `mkdocs.yml` | config | — | — | **none** (new toolchain) |
| `public/README.md` | doc (charter) | — | `examples/external/README.md` | exact |
| `public/index.md` | doc | — | `README.md` §Documentation (as counter-example — D-21) | partial |
| `public/tutorial/demo-walkthrough.md` (git mv) | doc | — | itself (`docs/demo-walkthrough.md`) | exact |
| `public/how-to/security-and-deployment.md` (git mv) | doc | — | itself (`docs/security-notes.md`) | exact |
| `public/concepts/pillars/*.md` | doc | — | `docs/demo-walkthrough.md` include style + `docs/diagrams/*.mmd` | role-match |
| `public/reference/**/*.md` | doc (generated) | — | — | **none** (mkdocstrings `:::` is new to repo) |
| `examples/0[0-7]/**/run.py` + `examples/external/**` (marker comments) | source annotation | — | `examples/00-quickstart/run.py` module docstring/stage shape | role-match |
| 13 docstrings in `src/`+`runtime/` (D-20 rework) | docstring | — | `ccf.artifacts.protocol.ArtifactStoreProtocol`, `ccf.harness.protocol.HarnessAdapterProtocol` | exact |

---

## Pattern Assignments

### `tools/publish_scan.py` (lint/gate script, batch)

**Analog:** `tools/lints/no_hardcoding.py` + `tools/lints/__main__.py`.
**This is the phase's single most important mapping** — the publish scan must read as a fourth
CCF invariant lint, not a novel script.

**Module-docstring pattern** — states the invariant, names the ruling, enumerates the rules with
rule-token headings, and explicitly justifies (or refuses) an allowlist. From
`tools/lints/no_hardcoding.py:1-37`:

```python
"""CINV-01 — the No-Hardcoding Rule (CLAUDE.md §6.4).

"Code contains interpreters and factories, never the things interpreted."
Three heuristics, one AST walk, plus the D-08 allowlist:

``cinv01a-prompt-shape``
    A string constant that looks like a prompt or system instruction. Scored
    against four signals; two are enough. ...

Unlike the import rules, CINV-01 has legitimate exceptions, so it takes an
allowlist: ``tools/lints/allowlist.yaml`` ...
"""
```

For the publish scan the corresponding docstring must say the **opposite** on allowlists —
D-20 rules the scan is purely default-deny with zero exceptions. Say so explicitly in the
docstring, in the same register.

**Blocking-by-design pattern** (`tools/lints/__main__.py:1-17`) — copy this posture verbatim in
spirit; it is the reason the gate stays a gate:

```python
"""`python -m tools.lints` — the blocking CI gate for CINV-01/02/03 (D-07).

Exit code is the only gate signal. There is deliberately no report-only,
warning-only, or `--exit-zero` mode: D-07 requires the lints to block from the
first fabric commit, and a non-blocking mode is how an invariant quietly stops
being one.
"""
```

**Tuning-knob-as-named-constant pattern** (`tools/lints/no_hardcoding.py:62-81`) — the shingle
length N=10 and the denylist strings go here, as documented module constants with `#:` Sphinx
comments explaining *why the value*, never as inline magic numbers:

```python
# --- CINV-01a tuning knobs -------------------------------------------------

#: Below this length a string cannot plausibly be a prompt; skip scoring.
MIN_PROMPT_CHARS = 40
#: Signal (d): prose length.
PROSE_CHARS = 200
...
#: Number of signals required to flag.
PROMPT_SCORE_THRESHOLD = 2
```

RESEARCH's N-sensitivity sweep (N=8 → 22 hits, N=10 → 13, N=20 → control fails) is exactly the
kind of justification this comment style carries.

**Rule-token constants** (`no_hardcoding.py:52-54`) — every finding class gets a stable token so
the runner and tests can key off it:

```python
RULE_PROMPT_SHAPE = "cinv01a-prompt-shape"
RULE_NUMERIC_TABLE = "cinv01b-numeric-table"
RULE_FACTORY_BYPASS = "cinv01c-factory-bypass"
```

The scan needs the same for its distinct checks: shingle hit, path/filename denylist hit,
pre-build symlink, pre-build `--8<--` reaching `docs/`|`.planning/`.

**Finding format + shared helper** (`tools/lints/__init__.py:27-37`) — reuse it, do not invent a
second format:

```python
__all__ = ["format_finding", "imported_module_names", "matches_module", "read_tree"]

def format_finding(path: pathlib.Path, lineno: int, rule: str, message: str) -> str:
    """Render one finding in the shared ``path:line rule message`` format."""
    return f"{path}:{lineno} {rule} {message}"
```

Note `tools/lints/__init__.py` documents the contract that every checker exposes the *same pair
of entrypoints* (`check_source(source, path, module_name)` / `check(path, module_name)`) "so the
runner can treat them uniformly." The publish scan operates on rendered HTML rather than Python
ASTs, so it will not match that signature exactly — but it should expose an equivalent
`scan_text(text, path) -> list[str]` / `scan_tree(root) -> list[str]` pair for the same reason:
the unit tests drive the pure-string entrypoint, CI drives the tree entrypoint.

**CLI + exit-code pattern** (`tools/lints/__main__.py:115-181`) — argparse with a `--base`
default of cwd, findings printed to stdout, a summary to stderr, `return 1` on any finding,
`raise SystemExit(main())`:

```python
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rules = list(CHECKERS) if args.all or not args.selected else args.selected

    findings = run(args.base, rules)
    for finding in findings:
        print(finding)

    if findings:
        print(
            f"\n{len(findings)} CCF invariant violation(s)."
            " Fix the code, or — for CINV-01 only — add a reviewed entry to"
            " tools/lints/allowlist.yaml.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The scan is invoked as `python tools/publish_scan.py site` (per RESEARCH's Makefile sketch) and
needs a `--pre-build` mode; keep the same `main(argv) -> int` + `SystemExit` shape so it is
testable in-process.

**Scope-as-config pattern** (`tools/lints/__main__.py:36-57`) — the trees a rule covers are
declared data with a comment justifying each scoping decision, plus a `SKIP_DIRS` set:

```python
LINTED_TREES: tuple[str, ...] = ("src", "runtime", "examples")

RULE_TREE_SCOPE: dict[str, tuple[str, ...]] = {
    "no-hardcoding": ("src", "runtime", "examples"),
    "harness-imports": ("src", "runtime"),
    ...
}

SKIP_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".venv", "venv", "build", "dist", ".mypy_cache"}
)
```

The scan's equivalents: the shingle **source** path (`docs/CCF_Whitepaper_1-2.md`), the scanned
tree (`site/`), the pre-build tree (`public/`), and the include-path prefix denylist
(`docs/`, `.planning/`).

**Dot-bounded matching discipline** (`tools/lints/__init__.py:55-60`) — the repo's standing habit
of making a substring check precise so a lookalike cannot match. The path/filename denylist
(`CCF_Whitepaper`, `SPEC_INVENTORY`, `PHASE_I`, …) should carry the same care and the same
comment style:

```python
def matches_module(name: str, prefixes: Iterable[str]) -> bool:
    """True when `name` equals or is a dotted descendant of any prefix.

    Dot-bounded so ``langgraphql`` never matches the ``langgraph`` deny entry.
    """
    return any(name == p or name.startswith(p + ".") for p in prefixes)
```

**Path-matching for allowlist-style entries** (`no_hardcoding.py:102-117`) — if any path
comparison is needed, follow `_is_factory_module`'s exact-or-segment-anchored-suffix rule
(`posix == entry or posix.endswith("/" + entry)`), never a bare `in`.

**Do NOT copy:** the `Allowlist` / `AllowlistEntry` / `load_allowlist` / `apply_allowlist`
machinery (`no_hardcoding.py:125-216`). D-20 rules the publish scan takes **no allowlist**.
That machinery is the analog's one deliberately-not-inherited part; say so in the scan's
docstring so the omission reads as a decision.

---

### `tools/publish_scan_tests/` and `tools/docs_tests/` (test, batch)

**Analog:** `tools/lints/tests/test_harness_imports.py` (and `tools/lints/tests/__init__.py`,
which exists — the tests directory is a real package).

These tests are **not** under `tests/` and therefore not covered by
`[tool.pytest.ini_options] testpaths = ["tests"]`. The precedent is exact: `ci.yml:34-35` runs
them as a separate step, with a comment explaining why:

```yaml
      # The checkers are the enforcement mechanism for three named invariants,
      # so they are themselves tested in CI. `pytest tests` in the test job does
      # not cover them (testpaths is the shipped suite); run them here, before
      # the gate they implement.
      - name: Lint checker unit tests (CINV-01/02/03)
        run: pytest tools/lints/tests -q
```

**Test-file structure pattern** (`tools/lints/tests/test_harness_imports.py:1-21, 55-56, 82-83`)
— docstring naming the invariant and its ruling, a small extractor helper, then explicit
`# --- violating cases ---` / `# --- clean cases ---` / `# --- the carve-out and its boundary ---`
section banners:

```python
"""Unit tests for the CINV-02 harness-import checker (CLAUDE.md §7.3, D-06)."""

from tools.lints.harness_imports import RULE_GRAPH_WRITER, RULE_HARNESS, check_source

SRC = pathlib.Path("src/ccf/operators/traversal.py")

def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


# --- violating cases -------------------------------------------------------

def test_plain_harness_import_is_flagged() -> None:
    findings = check_source("import langgraph\n", SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_HARNESS]
    assert "langgraph" in findings[0]


# --- clean cases -----------------------------------------------------------

def test_module_named_like_a_harness_prefix_is_not_flagged() -> None:
    # `langgraphql` is not `langgraph`; prefix matching must respect dot bounds.
    assert check_source("import langgraphql\n", SRC, "ccf.operators.traversal") == []
```

Map RESEARCH's four negative drift tests onto this shape:

| Drift test | "Violating case" | "Clean case" |
|---|---|---|
| deleted snippet marker | temp-copy a source with `[start:x]` stripped → `mkdocs build --strict` nonzero | unmodified tree → exit 0 |
| renamed Protocol | inject `::: ccf.does.not.Exist` → nonzero | every curated `:::` resolves |
| changed OpenAPI endpoint | mutated spec ≠ committed `openapi.json` | committed file matches |
| leaked whitepaper text | scanner fed `docs/CCF_Whitepaper_1-2.md` fires (**self-test**) | fed `public/how-to/security-and-deployment.md` → zero |

The last row is the direct analog of `test_module_named_like_a_harness_prefix_is_not_flagged`:
a paired positive/negative control on the same mechanism. RESEARCH measured both controls
already (60 hits on `docs/DESIGN.md`, 0 on the two moved files) — assert those polarities, not
the exact counts.

**Boundary-case naming pattern** — note how the analog names the lookalike file `EVIL` and
comments *why* the boundary must hold (`test_harness_imports.py:87, 109-113`). The publish scan
wants the same for its symlink and include-path guards.

---

### `tools/dump_openapi.py` + `tests/http_api/test_openapi.py` (utility + test, request-response)

**Analog for the fixture reuse:** `tests/http_api/conftest.py:352-370` — do not duplicate this
wiring in the dump tool if it can be avoided; RESEARCH's "Don't Hand-Roll" row says so
explicitly.

```python
@pytest.fixture(scope="module")
def app(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        # This fixture is about the routes, not the posture; the D-IMPL-73
        # warning has its own dedicated suite (test_insecure_default_warning).
        acknowledge_insecure_default=True,
    )
```

**Analog for the drift test itself:** the existing file it extends,
`tests/http_api/test_openapi.py:1-37`. Note its stated discipline — *assert what the document
emits, never hardcode prose about it* — and its `_document(app)` accessor:

```python
"""EXPR-03's "valid OpenAPI spec" as a passing test, not prose (07-10 Task 2).

The generated document is asserted from what ``app.openapi()`` actually
emits (research A1: validate the emitted version field, never hardcode
prose about it); ...
"""

def _document(app: Any) -> dict[str, Any]:
    document: dict[str, Any] = app.openapi()
    return document


def test_the_emitted_document_is_openapi_3(app: Any) -> None:
    """The version field of the document itself, not a claim about it."""
    document = _document(app)
    version = document["openapi"]
    assert version.startswith("3."), version
    # Recorded for the SUMMARY: FastAPI 0.140.0 emits this exact value.
    assert version == "3.1.0"
```

The new drift test slots in beside these with the same `(app: Any)` fixture signature. Copy the
"Recorded for the SUMMARY: FastAPI 0.140.0 emits this exact value" comment habit for the
regeneration-command note RESEARCH asks for in the failure message.

**Loud-comment-on-the-pin pattern** — `test_every_contract_bearing_route_lands_a_schema`
(`:40-60`) enumerates contract names as an explicit tuple. If the drift test needs a
serialization recipe, state it once as a module constant with the `sort_keys=True, indent=2`
determinism rationale inline.

---

### `Makefile` — `docs`, `docs-strict`, `docs-serve`, amended `ci:` (config, batch)

**Analog:** the `lint` and `perf-micro` targets, plus the `ci:` composition comment block.

**Header contract** (`Makefile:1-11`) — every new target must honour this or the D-10 mirror
claim breaks:

```make
# CCF SDK — single documented command surface for CI and developers (D-10).
# Every target CI runs, a developer runs the same way; the Makefile mirrors
# .github/workflows/ci.yml command-for-command (Phase I.5, plan 08-01).
#
# All Python invocations use the project venv interpreter explicitly and set
# PYTHONPATH=src:runtime so src-layout packages resolve without relying on the
# editable install being fresh (08-RESEARCH.md Pitfall 7 — `make install`
# refreshes it regardless).

PYTHON := .venv/bin/python
ENV := PYTHONPATH=src:runtime
```

**Target pattern** — `$(ENV) $(PYTHON) -m <module>` with a `## ` help string naming the ruling
(`Makefile:35-42`):

```make
lint: ## CCF invariant lints — CINV-01/02/03 + orchestration split (blocking, D-07)
	$(ENV) $(PYTHON) -m tools.lints --all

typecheck: ## mypy --strict over src + runtime ([tool.mypy] files is authoritative)
	$(ENV) $(PYTHON) -m mypy
```

**Multi-command target pattern** (`Makefile:92-96`) — the precedent for `docs-strict` running the
build *and then* the scan as two lines in one target:

```make
perf-micro: ## Micro-benchmarks: operators, factory, gates, run_coroutine_sync (D-23/D-05; 10% gate D-19)
	mkdir -p perf/results
	$(ENV_PERF) $(PYTHON) -m pytest perf/suites/micro -q \
		--benchmark-disable-gc --benchmark-json=perf/results/micro.raw.json
	$(ENV_PERF) $(PYTHON) perf/gate.py perf/results/micro.raw.json --suite micro
```

**Composition-change pattern** (`Makefile:44-50`) — the `ci:` line carries a comment block above
it recording *which plan finalized it and why*. D-IMPL-72's amendment appends to this block; it
does not rewrite the D-10 text:

```make
ci-core: lint typecheck test ## Mid-phase verification sweep — MUST stay green from Wave 1 onward

# Finalized in plan 08-12: `ci` = ci-core + examples is the phase gate
# command, reproducing the always-on Actions pipeline (ci.yml lint + test +
# examples jobs) locally command-for-command (D-10). Live legs are opt-in
# (live-legs.yml, D-11) and deliberately not part of `ci`.
ci: ci-core examples ## Full local reproduction of the always-on pipeline (D-10)
```

**`.PHONY` pattern** (`Makefile:21-26`) — a multi-line backslash-continued list grouped by
family; add `docs docs-strict docs-serve` (and `openapi` if a target is created) as a new group.

**Opt-in-target precedent for `docs-serve`** (`Makefile:84-90`, `116-126`) — the perf and live-leg
targets carry an inline comment stating they NEVER join `ci`. `docs-serve` needs the same
one-liner, since it is the only new target that must stay out of CI.

---

### `.github/workflows/ci.yml` — new `docs` job (config, batch)

**Analog:** the `examples` job, `ci.yml:119-157`. It is the closest match because it is the only
existing job that (a) drives the Makefile surface and (b) therefore provisions `.venv`:

```yaml
  # The v0 examples suite is the adoption contract (CLAUDE.md §9): a broken
  # example is a broken build. Always-on per D-10 — the same `make examples`
  # a developer runs locally, command-for-command. Example 03 runs its
  # deterministic leg here; the live legs are opt-in in live-legs.yml (D-11).
  # Deliberately NOT `continue-on-error` — per the I.1 D-07 precedent, a step
  # made non-blocking to hide a gap is worse than the gap.
  examples:
    name: examples suite (00–07, reference backends)
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install package with dev extras
        run: python -m pip install -e ".[dev]"

      # The Makefile targets use .venv/bin/python; provide the venv the same
      # editable install the job already has, so CI and local runs execute the
      # identical `make examples` command string (D-10).
      - name: Provision .venv for the Makefile command surface
        run: |
          python -m venv .venv
          .venv/bin/pip install -e ".[dev]"

      - name: Run all eight examples (make examples)
        run: make examples
```

Copy: the `name:` that states what the job proves, `checkout@v4` + `setup-python@v5` with
`cache: pip`, the two-step install (`pip install -e ".[dev]"` then a `.venv` provisioned the same
way, with the verbatim comment explaining why), and a final step that invokes **one make target**.
The docs job adds only `actions/upload-artifact@v4` for D-05.

**Comment-block-above-the-job pattern** — every job in this file is preceded by a prose block
naming the ruling that makes it always-on and stating explicitly that it is not
`continue-on-error`. The docs job needs the same block citing D-IMPL-71 (built, never hosted),
D-IMPL-72 (joins always-on CI), and D-02 (the scan is part of the gate, not a follow-up).

**Counter-analog — `perf.yml:1-38`** — read it to see what the docs job must *not* look like.
It is the repo's opt-in shape: `on: workflow_dispatch` only, a pinned runner image, and a header
stating "no push, no pull_request, no schedule triggers, ever." The docs job is the opposite
posture and should not borrow the pinned-image or dispatch-input machinery.

---

### `pyproject.toml` — the `docs` extra (config)

**Analog:** `[project.optional-dependencies]`, `pyproject.toml:61-102`.

```toml
[project.optional-dependencies]
# chromadb is NEVER a core dependency (heavy transitive tree) — 04-RESEARCH.md Standard Stack.
chroma = ["chromadb==1.5.9"]
...
# 11-RESEARCH.md Standard Stack (D-01): pytest-benchmark is the locked timing
# harness for the perf battery — benchmarks are pytest tests under perf/ and
# never join always-on CI (Phase-8 D-10 / D-IMPL-70). A1 compatibility with
# the pytest 9.1.1 pin verified empirically at plan 11-01 execution.
perf = ["pytest-benchmark==5.2.3"]
dev = [
  "pytest==9.1.1",
  ...
  # D-08: CI and contributors get all three harness legs from `pip install -e ".[dev]"`.
  "ccf[harnesses]",
  # Phase 11 D-01: dev environments get the perf harness from the same one command.
  "ccf[perf]",
  # Phase 13.1: CI installs the Anthropic client leg for examples/external (EXAM-04).
  "ccf[anthropic]",
]
```

Three things to copy exactly:
1. **Every group carries a comment naming the phase/decision that added it and why it is not
   core.** The `docs` extra's comment cites D-IMPL-71 and the MkDocs-2.0 pin rationale (RESEARCH
   Pitfall 7).
2. **Exact `==` pins throughout, never `>=`.** RESEARCH's proposed block already conforms.
3. **`dev` composes sub-extras via the self-referential `ccf[...]` form**, each on its own line
   with its own comment — so `"ccf[docs]"` joins `dev` in the same style, and no CI job needs an
   install-step change.

Also note `[tool.mypy] files` (pyproject ~line 119) covers `src` + `runtime` only, so
`tools/publish_scan.py` and `tools/dump_openapi.py` are **not** type-checked — matching the
existing `tools/lints/` posture. The compensating control is unit tests, which is why the test
mapping above is non-optional.

---

### `.gitignore` — `site/` (config)

**Analog:** the perf-results entry (`.gitignore`, near the tail):

```
# Perf battery run outputs are never committed (Phase 11 D-02); baselines are.
perf/results/
# Runtime ArtifactStore output of examples/external servers — never committed.
examples/external/*/.store/
```

Every generated-output entry in this file carries a one-line comment naming the ruling and
distinguishing what *is* committed. `site/` follows: build output, never committed (D-02/Pitfall
6); `public/` and `openapi.json` are committed.

---

### `public/README.md` (doc, charter)

**Analog:** `examples/external/README.md:1-30` — the family-charter README that CONTEXT D-06
explicitly names as the precedent.

```markdown
# examples/external — the external-consumer family charter

> "The beauty of CCF is it's a black box to the client caller if I want
> it to operate that way."

This directory is a distinct example **family**, unified by a
*consumption model* rather than a domain (Phase 13.1 D-01): ...

## The zero-CCF-imports rule

Client code in this family imports **nothing from CCF** (D-06). No
`ccf` imports, no `ccf_runtime` imports, no CCF-shaped helper modules.
The only CCF knowledge a client has is:
```

Copy the shape precisely: `# <dir> — the <thing> charter` title, a framing pull-quote or single
paragraph naming the ruling, then a `## The <name> rule` section stating the invariant in the
negative with a bolded **nothing/never**, then the enumerated consequences. For `public/`:
"## The never-publish rule" — everything here is published; `docs/` holds the whitepaper and
internal deliverables and must never be referenced from here; `tools/publish_scan.py` proves it
post-build on the artifact that ships.

Two content items the analog does not supply but this phase needs, both from RESEARCH:
the Mermaid-CDN caveat (Pitfall 5 — diagrams are blank when the downloaded artifact is opened
offline) and a line explaining that `D-IMPL-NN` refers to the SDK's internal decision log (D-22 /
Open Question 3).

**Nav exclusion:** this file stays out of `nav` and needs `not_in_nav: |` in `mkdocs.yml`
(RESEARCH A5, unverified — verify in Wave 0).

---

### `public/**/*.md` snippet include sites (doc)

**Analog:** `docs/demo-walkthrough.md` — the only file in the repo that already uses the include
mechanism, in 10 places, all whole-file, all repo-root-relative. Its HTML header comment
(`:1-13`) was written in Phase 12 *anticipating* this phase:

```html
<!--
  Phase 14 docs-site note: every `--8<--` directive below is a
  pymdownx.snippets literal include whose path is REPO-ROOT-RELATIVE.
  When this page is mounted in mkdocs, configure

      markdown_extensions:
        - pymdownx.snippets:
            base_path: [".."]   # or the repo root, relative to docs/

  so the include paths (examples/08-e2e-demo/...) resolve unchanged
  (Phase 12 RESEARCH A2). Nothing in this page pastes code — the doc
  always shows the exact files that run in CI.
-->
```

Two consequences for the planner: (a) with `mkdocs.yml` at repo root and `base_path: ["."]` these
paths resolve **unchanged** after the D-03 `git mv` — the move needs no include-path edits;
(b) this header comment becomes stale on the move and should be replaced with a one-line pointer
to `mkdocs.yml`, not deleted (the "nothing in this page pastes code" sentence is the DOCS-01
non-goal restated and is worth keeping).

**Include-site shape** (`docs/demo-walkthrough.md:78, 266`) — a prose paragraph that says what the
file is and why, then the fenced include, never a fence alone:

````markdown
--8<-- "examples/08-e2e-demo/artifacts/scenario.yaml"
````

Existing include sites, all whole-file, confirming RESEARCH's D-09 recommendation
("artifacts are included whole"): `artifacts/scenario.yaml`, `generator.py`, `ontology.yaml`,
`controlplane.yaml`, `halflife.yaml`, `agent.yaml`, `skills.yaml`, `expected_output.txt`,
`run.py`, `prompt.yaml`.

---

### `examples/0[0-7]/**/run.py` — marker comments (source annotation)

**Analog:** `examples/00-quickstart/run.py:1-18` — the module docstring already names the stages
the markers will delimit, in order. Use it as the marker-name vocabulary rather than inventing one:

```python
"""examples/00-quickstart — "Hello, Context Product" (EXAM-01).

The smallest possible fabric, end to end and in one process: register an
ontology, ingest a handful of events through L1, assemble into the graph,
run the four-category operator chain, project, gate, record the decision,
and serve one typed Context Product — keyless and model-free, on SQLite and
the file-backed ArtifactStore (D-12/D-13).

Every domain value ... is loaded from ``artifacts/*.yaml``. The code below is thin loading
and asserting logic; deleting the artifacts leaves it with nothing
meaningful to run (CLAUDE.md §6.4, the No-Hardcoding Rule).

Run it: ``make example-00`` (or
``PYTHONPATH=src:runtime python examples/00-quickstart/run.py``).
Exit code 0 means every assertion below held; any failure exits nonzero.
"""
```

That docstring yields the stage names directly: `ontology`, `ingest`, `assemble`, `operators`,
`project`, `gate`, `record`, `serve`.

Every example directory has the identical shape — `artifacts/`, `README.md`, `run.py` — verified
for `examples/00-quickstart`. **No `--8<--` marker exists anywhere under `examples/` today**;
this is greenfield annotation across all nine directories plus `examples/external/`.

**Lint impact:** `tools/lints/__main__.py:36` scopes CINV-01 over `("src", "runtime", "examples")`,
so the marker pass touches the No-Hardcoding tree. Markers are **comments**, and
`no_hardcoding.check_source` walks `ast.Constant` string nodes only (`:333-348`) — comments are
not in the AST at all, so no finding is possible. Confirm empirically with `make lint` after the
marker pass rather than asserting it.

---

### The 13 D-20 docstring rewrites (docstring)

**Target shape — analog 1:** `ccf.artifacts.protocol.ArtifactStoreProtocol`
(`src/ccf/artifacts/protocol.py:189-190`). A one-line class docstring: paraphrased commitment,
`§` citation, zero quoted body text.

```python
class ArtifactStoreProtocol(Protocol):
    """Immutable, content-addressed artifact persistence (CLAUDE.md §7.4)."""
```

**Target shape — analog 2:** `ccf.harness.protocol.HarnessAdapterProtocol`
(`src/ccf/harness/protocol.py:171-187`). The longer form: summary line with citation, then
paragraphs of *the SDK's own reasoning* — where implementations live, how conformance is verified,
why the arguments are keyword-only. Every sentence is authored, none quoted.

```python
class HarnessAdapterProtocol(Protocol):
    """Structural contract for a harness binding (CLAUDE.md §7.3; D-IMPL-25).

    Implementations live under ``runtime/ccf_runtime/adapters/<harness>/`` and
    nowhere else (D-04, D-IMPL-53). Conformance is verified by the shared
    factory-parametrized suite run against the **real** SDKs with no LLM calls
    (D-09) — a double written to the Protocol we designed can pass while the
    real surface disagrees, which is the failure this whole seam exists to
    prevent.
    ...
    """
```

**Method-level target shape** (`src/ccf/artifacts/protocol.py:192-206`) — summary line, then
behavioural commitment in the SDK's voice, then a `Raises:` block:

```python
    def put(self, *, tenant_id: str, artifact_class: str, name: str, artifact: object) -> ArtifactRef:
        """Store ``artifact`` and return its reference.

        Idempotent by construction: storing byte-identical content again
        returns the same address and leaves the stored bytes untouched. There
        is deliberately no ``overwrite`` parameter.

        Raises:
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form and therefore no stable identity.
        """
```

**The leak shape to rewrite away from** — `src/ccf/halflife/debt.py:290-298` and
`src/ccf/halflife/decay.py:1-20`. Both cite correctly *and* quote:

```python
def context_debt(factors: DebtFactors) -> Decimal:
    """Return ``D_c = 1 − (F · C · S)`` (whitepaper §7.7; INV-CH7-62).

    Multiplicative-conjunctive by commitment: any factor at zero drives D_c to
    one, which is the algebraic statement of the Trust Triangle's conjunctive
    gating — a product whose lineage leg is weak fails the triangle even when
    the other two legs are strong (INV-CH7-66). ...
    """
```

```python
"""λ_c — Context Half-life as formal decay (whitepaper §7.7).

The whitepaper commits to one formula::

    R(t) = R₀ × (1/2)^((t − t₀) / λ_c)
...
The SDK ships the curve and refuses to ship the calibration — the whitepaper's
own illustrative table says as much ("these values are illustrative, not
empirical"). ...
"""
```

The rewrite rule these analogs establish: **the formula, the section number, the invariant ID,
and the SDK's own explanation of consequences all stay; contiguous runs of whitepaper prose go.**
The `decay.py` inline quotation (`"these values are illustrative, not empirical"`) is a
short quoted span — verify whether it forms a 10-word shingle before deciding it must go; the
scan, not judgment, is the arbiter (run `tools/publish_scan.py` over the docstring text).

The remaining leak sites RESEARCH located, all needing the same treatment:
`src/ccf/halflife/{debt,decay}.py`, `src/ccf/peering/__init__.py`,
`src/ccf/projection/__init__.py`, `src/ccf/controlplane/artifacts.py`,
`src/ccf/operators/{planner,categories}.py`, `runtime/ccf_runtime/cdc/adapter.py`.

---

## Shared Patterns

### Gate posture — blocking, no report-only mode
**Source:** `tools/lints/__main__.py:8-11`; echoed at `.github/workflows/ci.yml:1-7, 100-104, 122-124`.
**Apply to:** `tools/publish_scan.py`, the `docs-strict` Makefile target, the `docs` CI job.

```python
Exit code is the only gate signal. There is deliberately no report-only,
warning-only, or `--exit-zero` mode: D-07 requires the lints to block from the
first fabric commit, and a non-blocking mode is how an invariant quietly stops
being one.
```

and in CI:

```yaml
      # Deliberately NOT `continue-on-error`: per the I.1 D-07 precedent, a step
      # made non-blocking to hide a gap is worse than the gap.
```

This repo has said the same thing three separate times. Anything in this phase that would soften
the docs gate (`continue-on-error`, an allowlist, a `|| true`) must be argued against this text.

### Citation-in-the-comment
**Source:** everywhere — `Makefile:35`, `pyproject.toml:62`, `ci.yml:119-124`,
`no_hardcoding.py:86`, `.gitignore`.
**Apply to:** every new Makefile target, every pyproject entry, every gitignore line, every CI
job, every module constant in the scan.

The invariant convention: **no configuration line lands without a `D-NN` / `D-IMPL-NN` /
`CLAUDE.md §N` / `INV-CHNN-NN` reference and a sentence of why.** `Makefile:92`
(`## Micro-benchmarks: … (D-23/D-05; 10% gate D-19)`) and `pyproject.toml:85-89` are the
densest examples.

### Justify the not-inherited part
**Source:** `no_hardcoding.py:31-37` (why CINV-01 alone takes an allowlist);
`tools/lints/__main__.py:38-46` (why CINV-02 is scoped off `examples/`);
`perf.yml:1-13` (why perf is never always-on).
**Apply to:** `tools/publish_scan.py` (why it takes **no** allowlist, D-20), the `docs` extra
(why it is not core), `docs-serve` (why it never joins `ci`).

This repo consistently documents the *absence* of a mechanism as deliberately as its presence.

### Makefile-mirrors-CI, `.venv` provisioned
**Source:** `Makefile:1-11` + `ci.yml:148-157`.
**Apply to:** the `docs` job and `docs-strict` target.

The CI job runs exactly one make target; the job provisions `.venv` with the same editable
install it already has, with the verbatim justifying comment. A docs job invoking `mkdocs build`
directly would break the D-10 mirror.

### Tests for the gate itself, outside `testpaths`
**Source:** `ci.yml:30-35` + `tools/lints/tests/` (a real package with `__init__.py`).
**Apply to:** the publish-scan tests and the four negative drift tests.

`[tool.pytest.ini_options] testpaths = ["tests"]` does not reach `tools/`; the gate's tests get
their own explicit CI step, run **before** the gate they implement.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `mkdocs.yml` | config | — | No YAML build-tool config exists in this repo (`pyproject.toml` + `Makefile` + workflows are the whole config surface). Use `14-RESEARCH.md` §"Complete `mkdocs.yml` skeleton" — it is probe-verified, including the two silent-default traps (`check_paths: true`, `validation.*: warn`). The only local convention to import is the comment-with-citation habit above: annotate `check_paths`, `dedent_subsections`, `base_path`, and `validation` with the D-number and pitfall each defends. |
| `public/reference/**/*.md` (mkdocstrings `:::` pages) | doc (generated) | — | No `:::` directive exists anywhere in the repo. Use RESEARCH "Pattern 2" and the D-13 surface inventory (every path in it was grep-verified). |
| `public/index.md` | doc | — | `README.md` is the nearest existing landing page but D-21 rules it explicitly **not** the model — it links three never-publish paths (`README.md:80-90`: `docs/CCF_Whitepaper_1-2.md`, `docs/DECISIONS.md`, `docs/SPEC_INVENTORY.md`). Treat it as a counter-example. Note `README.md:85-86` also links `docs/diagrams/` and must be repointed to `public/diagrams/` as part of D-03. |

## Metadata

**Analog search scope:** `tools/`, `.github/workflows/`, `Makefile`, `pyproject.toml`,
`.gitignore`, `docs/`, `examples/`, `tests/http_api/`, `src/ccf/{artifacts,harness,halflife}/`
**Files scanned:** 24 read in full or targeted-range; ~40 path/existence assertions verified
**Pattern extraction date:** 2026-08-03
