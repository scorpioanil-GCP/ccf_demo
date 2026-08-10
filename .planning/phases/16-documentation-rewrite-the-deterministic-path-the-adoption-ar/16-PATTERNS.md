# Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument - Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** 29 new/modified file groups
**Analogs found:** 26 / 29 (3 NO-ANALOG, 1 history-only)
**Tree state:** `84f4501` + uncommitted `.planning/` edits

> **What this file is for.** RESEARCH.md already established *what* Phase 16
> builds and *what it must not break*. This file answers the one question it
> does not: **"which existing file does an executor open, and what does it
> copy?"** Every excerpt below was read out of the tree in this session. Where
> nothing exists to copy, the entry says `NO ANALOG` and names the nearest
> partial rather than inventing a shape.

---

## File Classification

### Group 1 — the eight new test modules (RESEARCH § *Validation Architecture* → *Wave 0 Gaps*)

| New file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `tests/examples/test_backend_matrix.py` | test | batch / parametrized-over-substrate | `tests/conformance/test_graphstore.py::graph_backend` (+ `tests/conftest.py::fabric_boot`) | **exact** |
| `tests/examples/test_section_one_is_agent_free.py` | test | transform (AST over source) | `tests/agents/test_consumption_discipline.py` | **exact** |
| `tests/examples/test_spine_separation.py` | test | file-I/O (marker parse over source) | `tools/docs_tests/test_diagram_coverage.py` (+ `test_snippet_gate.py` marker probe) | role-match |
| `tools/docs_tests/test_no_stale_example_paths.py` | test (gate control) | file-I/O + path resolution over `public/**/*.md` | `tools/docs_tests/test_diagram_coverage.py` | **exact** |
| `tools/docs_tests/test_gate_two_wording.py` | test (gate control) | transform (paragraph-scoped prose scan) | **composite** — `tools/lints/citations.py::citation_sentence` + `tools/publish_scan.py::normalize` | partial (see § *No Analog*) |
| `tools/docs_tests/test_adoption_argument.py` | test (gate control) | file-I/O + presence assertion | `tools/docs_tests/test_diagram_coverage.py` | role-match |
| `tools/docs_tests/test_advisory_discharge.py` | test (gate control) | file-I/O + presence assertion | `tools/docs_tests/test_diagram_coverage.py` | role-match |
| `tools/docs_tests/test_documented_commands_exist.py` | test (gate control) | bijection (Makefile ↔ `public/**/*.md`) | `tools/docs_tests/test_diagram_coverage.py` | **exact shape** |

### Group 2 — the parameterized backend runner (D-06)

| New file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `examples/<sec1>/run.py` (`--backend`) | example driver | request-response | `examples/00-quickstart/run.py` (spine) + `examples/03-harness-portability/run.py:691-702` (argparse) | **exact** (two sources) |
| `examples/<sec1>/artifacts/manifest-<backend>.yaml` ×6 | config artifact | CRUD | `examples/00-quickstart/artifacts/manifest.yaml` | **exact** |
| the connection resolver (`--backend` → `connection=` mapping) | utility | transform | `tests/conftest.py::fabric_boot` inner `factory` (:314-390) | **exact** |
| `examples/<sec1>/artifacts/backends.yaml` (opt-in DGX defaults) | config artifact | CRUD | `examples/03-harness-portability/artifacts/live.yaml` | **exact** |
| the network-free proof (socket guard) | utility | event-driven | `examples/03-harness-portability/legs/deterministic.py::install_no_model_guard` | **exact** |

### Group 3 — a new example directory (Sections 1–3)

| New file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `examples/<new>/spine.py` + `deployment.py` (D-11 split) | example code | request-response | `examples/external/00-hello-context/{run,serve}.py` split; `examples/03-harness-portability/legs/` | role-match |
| `examples/<new>/artifacts/*.yaml` | artifact set | CRUD | `examples/00-quickstart/artifacts/` (16 docs); wording from `examples/05-workflow-hitl/artifacts/manifest.yaml` | **exact** (⚠ see F-1 flag) |
| `examples/<new>/README.md` | doc | — | `examples/00-quickstart/README.md` (7 headings) | **exact** |
| `tests/examples/test_<new>_output.py` | test | request-response | `tests/examples/test_quickstart_output.py` | **exact** |
| `Makefile` `example-<new>` target | config | — | `Makefile:82-112` | **exact** |
| `examples/<sec2>/client_adk.py` | client leg | request-response | `examples/external/00-hello-context/client_adk.py` | **exact** |
| `examples/<sec2>/client_bare.py` | client leg | request-response | `examples/external/00-hello-context/client_bare.py` | **exact** |
| `examples/<sec2>/client_claude_agent.py` | client leg | request-response | `client_anthropic.py` (raw `anthropic` SDK — **near, not same**) | partial |
| `examples/<sec2>/client_langgraph.py` | client leg | request-response | — | **NO ANALOG** |
| FIBO data extension (corp→corp edges) | fixture generator | batch | `examples/08-e2e-demo/generator.py` + `/home/parkave/fluree/examples/fibo/load_neo4j.py` | role-match |

### Group 4 — new published pages

| New file | Role | Diátaxis | Closest analog | Match |
|---|---|---|---|---|
| Section-1 tutorial page | doc | tutorial | `public/tutorial/adopters-guide.md` | **exact** |
| Section-1 how-to (deterministic assembly) | doc | how-to | `public/how-to/grant-and-revoke-a-skill.md` | **exact** |
| Section-1 concept (six axes of `G`) | doc | concept | `public/concepts/invariants.md` (form only) | **NO ANALOG** (content) |
| artifact reference page | doc | reference | `public/reference/artifacts/product-registration.md` | **exact** |
| protocol reference page | doc | reference | `public/reference/protocols/context-products.md` | **exact** |
| the adoption-argument page (D-10) | doc | concept/explanation | — | **NO ANALOG** |
| `mkdocs.yml` nav entries | config | — | `mkdocs.yml` `nav:` block | **exact** |

### Group 5 — CI additions

| New file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `.github/workflows/live-legs.yml` DGX job | config | — | `live-legs.yml::examples-live-anthropic` (:94-138) | **exact** |
| `Makefile` `gate-16` target | config | — | `make gate-15.3` — **git history only**, `d364b65^` | history-only |
| `tools/gates/gate_16.py` (if scripted) | utility | transform | `tools/gates/gate_15_3.py` at `d364b65^`; output contract from `tools/lints/__main__.py` | history-only |

### Group 6 — the ruling

| New file | Role | Closest analog | Match |
|---|---|---|---|
| `docs/DECISIONS.md` `D-IMPL-94` | record | `docs/DECISIONS.md` D-IMPL-63 (:187) / D-IMPL-93 (:318) | **exact** |

---

## Pattern Assignments

### 1. `tests/examples/test_backend_matrix.py` (test, parametrized-over-substrate)

**Analog:** `tests/conformance/test_graphstore.py` + `tests/conftest.py`

**The parametrization shape** (`tests/conformance/test_graphstore.py:47-99`) — copy the
param list *and* the marks; the marks are already registered in `pyproject.toml`
and already gate the `make leg-*` targets:

```python
@pytest.fixture(
    params=[
        pytest.param("sqlite"),
        pytest.param("memory"),
        pytest.param("demo"),
        pytest.param("postgres", marks=pytest.mark.postgres),
        pytest.param("neo4j", marks=pytest.mark.neo4j),
        pytest.param("mongo", marks=pytest.mark.mongo),
        pytest.param("fluree", marks=pytest.mark.fluree),
    ]
)
def graph_backend(
    request: pytest.FixtureRequest, fabric_boot: Callable[..., "FabricHandle"]
) -> "FabricHandle":
    """A booted fabric per backend under test.

    ... not one test body below changed, and no test body knows which
    substrate it is running on. That is what makes the suite evidence of
    parity rather than two suites that happen to agree.
    """
```

> **Carry that docstring sentence forward.** It is the exact claim D-06 asks the
> example matrix to make, already written by the phase that earned it.

**The connection resolver** (`tests/conftest.py:314-379`) — this is the shape the
example's `--backend` → `connection=` mapping should take, keyed on each
adapter's own config-model field names:

```python
    def factory(
        *, database_path: Path | None = None, backend: str = "sqlite"
    ) -> "FabricHandle":
        # The keys are the field names on the adapter's own connection
        # contract (plan 15.4-04), not `boot`'s — `boot` has no per-database
        # parameter left to name.
        location: dict[str, Any]
        if backend == "postgres":
            location = {
                "dsn": request.getfixturevalue("postgres_dsn"),
                "schema_name": f"ccf_test_{uuid.uuid4().hex}",
            }
        elif backend == "sqlite":
            location = {"database_path": database_path or tmp_path / ...}
        elif backend == "memory":
            location = {}          # this adapter's contract has no fields
        elif backend in ("neo4j", "mongo"):
            location = {"uri": ..., "partition": f"ccf_test_{uuid.uuid4().hex}"}
        elif backend == "fluree":
            location = {"url": ..., "partition": f"ccf_test_{uuid.uuid4().hex}"}
        else:
            raise NotImplementedError(backend)
```

⚠ **`memory` is `{}`, not a flag.** Copy that branch verbatim in spirit — a
selection flag there re-forks what 15.4 un-forked.

⚠ **The `else: raise NotImplementedError(backend)` is load-bearing.** RESEARCH's
*Don't Hand-Roll* forbids an `if backend == …` cascade *for selection*; this
cascade selects **connection arguments**, not the adapter. Selection stays
`DeploymentManifest.backend` → registry lookup. Keep the two distinguishable in
the code, or a reviewer will read it as the forbidden cascade.

**What to compare, and what NOT to compare** — from
`tests/conformance/test_substrate_differential.py:1-58`:

> *"**Comparisons happen on canonical bytes, never raw rows** — what keeps the
> suite backend-neutral instead of backend-flaky."*

Assert `content_hash(product_sqlite) == content_hash(product_<b>)` on the served
`ContextProductContract`. **Do not assert byte-identical replay records**
(RESEARCH P-3): `PolicyBindingsSnapshot.graph_adapter` / `graph_adapter_version` /
`graph_secret_refs` are dimension-2 facts as of 15.4-08 and *should* differ.

---

### 2. `tests/examples/test_section_one_is_agent_free.py` (test, AST over source)

**Analog:** `tests/agents/test_consumption_discipline.py` — this is the tree's
AST import-allowlist test, and its structure transfers whole.

**The AST extractor** (`tests/agents/test_consumption_discipline.py:112-123`):

```python
def _ccf_imports(source: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name for alias in node.names
                if alias.name.startswith("ccf")
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("ccf"):
                imported.add(node.module)
    return imported
```

⚠ **Prefer the shared helpers over this local copy.** `tools/lints/__init__.py`
ships `imported_module_names(node, *, package="")` (:122) and
`submodule_import_names(node, *, package="")` (:137). The second exists because
of Phase 15.4's **CR-02**: `from ccf.graph import _writer` binds
`ccf.graph._writer` but `imported_module_names` reports only `ccf.graph`, and
*both* the lint and the invariant test that mirrored it were blind to that form.
The docstring says why it lives in the shared module:

> *"Lives here rather than in one checker because every import rule needs it …
> and a helper imported from a sibling checker is how one rule's edit silently
> changes another's."*

A Section-1 guard that hand-rolls `_ccf_imports` inherits the CR-02 hole for
`from ccf import agents`.

**The parametrized assertion** (`:126-140`) — copy the shape and the
message-names-the-rule discipline:

```python
@pytest.mark.parametrize(
    "module_path",
    sorted(AGENTS_PACKAGE.glob("*.py")),
    ids=lambda p: p.name,
)
def test_agents_modules_import_only_the_consumption_surface(
    module_path: Path,
) -> None:
    for module in sorted(_ccf_imports(module_path.read_text())):
        assert module.startswith(ALLOWED_CCF_PREFIXES), (
            f"{module_path} imports {module!r}, which is outside the agents"
            " package's permitted consumption surface — no path from Agent"
            " to L1–L5 (AGNT-01; CLAUDE.md §10; DESIGN.md §3.1)"
        )
```

For Section 1 the polarity inverts: a **denylist** (`ccf.agents`, `ccf.skills`,
`ccf.workflow`, `ccf.hitl`, `ccf_runtime.adapters`) rather than an allowlist.
Keep the allowlist-comment discipline anyway — the analog annotates *every*
admitted prefix with the plan/finding that admitted it, which is what makes the
list reviewable rather than accreted.

**The negative control** — see § *Shared Patterns → Negative controls*. This
module needs one: inject `from ccf.agents import AgentFactory` into a copy under
`tmp_path` and assert the guard refuses.

---

### 3. `tests/examples/test_spine_separation.py` (test, marker parse over source)

**Analog (structure):** `tools/docs_tests/test_diagram_coverage.py` — the
bijection + report-both-directions-by-name shape.
**Analog (marker probe):** `tools/docs_tests/test_snippet_gate.py:39-40, 89-90`.

The marker literal, verified in use (`test_snippet_gate.py:89-90`):

```python
    original = SNIPPET_SOURCE.read_text(encoding="utf-8")
    assert f"[start:{SECTION}]" in original, "fixture drifted from its source"
```

Source-side marker form, verified in `examples/00-quickstart/run.py:156-165`:

```python
    # --8<-- [start:boot]
    booted = load_and_boot(
        MANIFEST,
        registry=registry,
        connection={"database_path": str(root / "quickstart.sqlite3")},
    )
    # --8<-- [end:boot]
```

**The canonical spine marker set** — verified as the seven names in
`examples/00-quickstart/run.py` (:156, 186, 194, 222, 248, 327, 345):
`boot`, `ingest`, `operators`, `project`, `gate`, `record`, `serve`.
RESEARCH D.3 recommends these become the standard set every Section-1 example
uses; the test should assert exactly that ordered set, every opened marker
closed, and **no marker region spanning both the spine and deployment modules**.

**The precondition test is mandatory** — copy `test_diagram_coverage.py:66-80`
verbatim in spirit:

```python
# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_fixture_trees_are_populated() -> None:
    """Both sides of the bijection are non-empty.

    Without this, a renamed `public/diagrams/` would make every assertion below
    pass over empty sets.
    """
    assert DIAGRAM_DIR.is_dir(), f"missing diagram tree: {DIAGRAM_DIR}"
    ...
```

---

### 4. `tools/docs_tests/test_no_stale_example_paths.py` (gate control, `public/**/*.md`)

**Analog:** `tools/docs_tests/test_diagram_coverage.py` — this is the closest
structural match in the tree, and the new module should be a near-clone with the
regex and the resolution target swapped.

**Path resolution and CWD discipline** (`:22-24, 33-44`):

```python
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The Phase D diagram sources — the artifacts whose publication is at stake.
DIAGRAM_DIR = REPO_ROOT / "public" / "diagrams"

#: A `pymdownx.snippets` include naming a diagram, e.g.
#: `--8<-- "public/diagrams/pillar-hitl.mmd"`. The capture is the bare
#: filename, which is what both sides of the bijection are keyed on.
INCLUDE_RE = re.compile(r'-{2,}8<-{2,}\s*"[^"]*?/diagrams/([A-Za-z0-9_.-]+\.mmd)"')
```

> *"Paths resolve from this file's location, never from the process CWD"* — the
> module docstring says it, and `test_docstring_leaks.py:25-28` records **WR-04**,
> where a CWD-relative walk scanned zero files and the gate passed over nothing.

**Do not hand-roll the include parser.** `tools/publish_scan.py::include_targets`
(:190-215) already handles both forms and says why a one-form parser is useless:

```python
def include_targets(text: str) -> list[tuple[int, str]]:
    """`(lineno, target)` for every snippet include in `text`.

    `pymdownx.snippets` accepts two forms and the gate must see both: the
    inline `--8<-- "target"`, and the block form, in which a bare `--8<--`
    opens a list of one-per-line targets and a second bare `--8<--` closes it.
    A gate that parses only the inline form is defeated by a two-line edit.
    """
```

The **new** half this module owns is the *prose-only* path token — the seven
pages in RESEARCH § A.2's second table that name `tests/examples/test_*.py` in
running text, invisible to `check_paths`. That extraction must be
paragraph-scoped (see § *Shared Patterns → Paragraph scoping*), because a wrapped
Markdown sentence hides a path from a line-scoped regex — RESEARCH P-2 records
Phase 15.1 under-counting the same sweep **six times** on exactly that.

---

### 5. `tools/docs_tests/test_gate_two_wording.py` (gate control, paragraph-scoped prose)

**No single analog.** Two halves exist; the module is their composition. See
§ *No Analog Found* for the honest statement of the gap.

**Half one — sentence scoping with offset→sentence mapping**
(`tools/lints/citations.py:279-294, 491-503`). This is the tree's only working
implementation of "match in a joined window, map back":

```python
#: How many lines either side of a citation are joined before the citation's
#: own sentence is cut out of them. Two, because the convention's instance in
#: ``ccf.deployment.binder`` wraps one sentence across three lines.
#:
#: The marker must then land in *the citation's own sentence*, not merely
#: nearby. Nearness is not enough: one line of `.planning/REQUIREMENTS.md` is a
#: four-thousand-character paragraph that opens by saying an *earlier* record's
#: line numbers "have since moved" and then makes six present-tense citations
#: of its own. A line-scoped marker exempts all six; a sentence-scoped marker
#: exempts none, which is right.
MARKER_WINDOW = 2

#: What ends a sentence for marker scoping: terminal punctuation followed by
#: whitespace. Deliberately crude — a mis-split truncates the window, which can
#: only cost a marker, never invent one.
_SENTENCE_BREAK = re.compile(r"[.!?]\s")
```

```python
def citation_sentence(lines: list[str], lineno: int, column: int) -> str:
    """The sentence carrying the citation at `lineno`/`column`."""
    lo = max(0, lineno - 1 - MARKER_WINDOW)
    before = lines[lo : lineno - 1]
    window = " ".join(before + lines[lineno - 1 : lineno + MARKER_WINDOW])
    offset = sum(len(line) + 1 for line in before) + column

    start = 0
    for match in _SENTENCE_BREAK.finditer(window, 0, offset):
        start = match.end()
    end_match = _SENTENCE_BREAK.search(window, offset)
    end = end_match.end() if end_match else len(window)
    return window[start:end]
```

`citations.py` already walks `public` (`GATED_TREES`, :153-164), so this helper
runs over the target tree today.

**Half two — markup-stripping normalization over published Markdown**
(`tools/publish_scan.py:141-150`):

```python
def normalize(text: str) -> list[str]:
    """Lowercased word sequence with markup and code spans removed.

    HTML tags go first so an element boundary inside a quoted sentence cannot
    split a shingle; backtick code spans go next so a rendered identifier does
    not glue two unrelated words together.
    """
    stripped = _CODE_SPAN_RE.sub(" ", _TAG_RE.sub(" ", text))
    return _NON_WORD_RE.sub(" ", stripped.lower()).split()
```

**The wording to assert against — copy it, do not paraphrase it.** RESEARCH P-4
is explicit. The canonical sentence, verified at
`src/ccf/deployment/__init__.py:72-79` and mirrored in
`tests/examples/test_gate_two_divergence.py:8-20`:

> *"Gate 2 verifies **assembly-path integrity**: the claim transcribed into the
> Context Product Contract equals the projection engine's execution of the plan.
> … It does **not** detect producer misdeclaration. The engine is a *faithful
> transcriber of the plan*, not an independent witness of it: it builds
> `operators_invoked` and `steps` in one loop over the same operator plan …"*

**And the published form already in the tree** (`public/reference/artifacts/product-registration.md:23-28`):

> *"Gate 2 sits downstream of both and verifies assembly-path integrity — the
> engine transcribes the plan faithfully rather than witnessing it
> independently, so it cannot catch a misdeclaration (`D-IMPL-86`)."*

---

### 6–8. `test_adoption_argument.py`, `test_advisory_discharge.py`, `test_documented_commands_exist.py`

**Analog for all three:** `tools/docs_tests/test_diagram_coverage.py`.

`test_documented_commands_exist.py` is the closest of the three — it is literally
a second bijection, `Makefile` targets ↔ command strings in `public/**/*.md`.
Copy the both-directions-reported-by-name discipline (`:88-118`):

```python
def test_no_diagram_is_orphaned() -> None:
    """Every diagram is embedded by at least one Concepts page."""
    orphans = sorted(diagram_names() - set(embeds_by_diagram()))
    assert not orphans, (
        "Phase D diagrams exist but are published by no Concepts page — they "
        "have silently stopped being part of the documentation: "
        + ", ".join(orphans)
    )
```

**The Makefile side is machine-readable and stable** — `.PHONY` at `Makefile:28-36`
enumerates every target, and `examples:` at `:112` is the composition list:

```make
.PHONY: help install lint typecheck test ci-core ci examples \
	example-00 example-01 example-02 example-03 example-04 example-05 \
	example-06 example-07 example-08 example-ext-00 \
	...

examples: example-00 example-01 example-02 example-03 example-04 example-05 example-06 example-07 example-08 example-ext-00 ## Run all ten examples in order, stopping on first failure
```

For `test_advisory_discharge.py`, the A-8 strings to assert both halves of are
already written at `src/ccf/deployment/manifest.py:118-138`:

> *"`role` governs registration and pinning, never visibility. A `role: load`
> artifact appearing here is still absent from `pins`, still absent from the
> Control Plane registry, and still absent from replay dimension 2."*

For `test_adoption_argument.py`, the assertion set is the **exact inverse of
G-01's zero-hit measurement** — see RESEARCH V-7. The nearest structural sibling
for "assert this file contains these strings, and prove the check is not
vacuous" is `tools/docs_tests/test_openapi_drift_control.py` (below).

---

### 9. `examples/<sec1>/run.py` — the parameterized runner body

**Analog (spine):** `examples/00-quickstart/run.py`
**Analog (CLI):** `examples/03-harness-portability/run.py:691-702`

**The module docstring is the template.** `examples/00-quickstart/run.py:1-23`
states the four things every new example's header must state — what it is, that
it asserts nothing, that its artifacts carry everything, and its one run command:

```python
"""examples/00-quickstart — "Hello, Context Product" (EXAM-01).

The smallest possible fabric, end to end and in one process: load a deployment
manifest, ingest a handful of events through L1, assemble into the graph, run
the four-category operator chain, project, gate, record the decision, and serve
one typed Context Product — keyless and model-free, on SQLite and the
file-backed ArtifactStore (D-12/D-13).

This file is the **call spine** an adopter would actually write, and nothing
else. It asserts nothing and prints nothing: its assertions live in
``tests/examples/test_quickstart_output.py``, where they are run by ``pytest``
and can fail a build (D-09). ``make example-00`` running clean means the spine
executed.

Every domain value — entity classes, source systems, identifiers, thresholds,
policy versions, MAX_TTL, the query, the boundary — is loaded from
``artifacts/*.yaml`` and enumerated by ``artifacts/manifest.yaml``. Deleting
the artifacts leaves this file with nothing meaningful to run (CLAUDE.md §6.4,
the No-Hardcoding Rule).

Run it: ``make example-00`` (or
``PYTHONPATH=src:runtime python examples/00-quickstart/run.py``).
"""
```

> **This example is No-Hardcoding-compliant** and is the safe one to copy. It is
> also the file A-1's import convention should be demonstrated from — its import
> block (`:49-53`) already uses `from ccf.deployment import …` and never a
> submodule FQN.

**The argparse precedent** (`examples/03-harness-portability/run.py:691-702`) —
`--backend` should mirror `--mode`'s shape, including `required=True` and the
explicit refusal on a bad combination:

```python
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("deterministic", "live"), required=True
    )
    parser.add_argument("--provider", choices=("ollama", "anthropic"))
    arguments = parser.parse_args()
```

⚠ **`choices=` must come from `ccf.graph.registry.declared_names()`, not a
literal tuple.** A literal six-name tuple in an example is the substrate-name
hardcode 15.4 removed from `DeploymentManifest.backend`; `cinv04-substrate-name`
scopes `src/` only, so nothing in CI would catch it in `examples/`.

---

### 10. `examples/<sec1>/artifacts/manifest-<backend>.yaml` — thin per-backend manifests

**Analog:** `examples/00-quickstart/artifacts/manifest.yaml`

**The `[ADAPT]` / `[MECHANISM]` header** (`:26-34`) — reproduce it, and extend
the same two-word vocabulary to the *code* file headers for D-11 (RESEARCH D.3
option 3; costs no new marker vocabulary):

```yaml
# [ADAPT] domain vocabulary — safe to change for your domain
# [MECHANISM] structural keys interpreted by the factory — do not rename
#
# In this file: `tenant_id`, every `key`, every `path`, and the
# non-`ccf.`-prefixed `class_id` values are [ADAPT]; the keys `semver`,
# `tenant_id`, `backend`, `resolution_spec_key`, `policy_bundle_key`,
# `artifacts`, `path`, `key`, `class_id`, `role` and `registration`, the
# `ccf.`-prefixed class ids, and the `role` and `registration` values are
# [MECHANISM].

semver: "1.0.0"

tenant_id: meridian-bank
backend: sqlite
```

**The connection-string prohibition, already written** (`:11-15`) — carry it
verbatim in spirit, because it is exactly why D-06 splits the manifest from the
`connection=` mapping:

```yaml
# The BACKEND is declared as a kind only (D-08). There is no DSN and no
# database path here, deliberately: a connection string is a deployment
# ENVIRONMENT value, and putting one in a versioned, content-hashed artifact
# would persist it into the audit plane.
```

⚠ **`load_and_boot` preflights that every entry's document lies inside the
deployment** (RESEARCH B.2). Six sibling `manifest-<backend>.yaml` files in one
`artifacts/` directory, all naming the same relative artifact paths, satisfies
this. Manifests in per-backend subdirectories do not.

---

### 11. `examples/<sec1>/artifacts/backends.yaml` — the opt-in DGX config artifact

**Analog:** `examples/03-harness-portability/artifacts/live.yaml` (64 lines)

**The header is the whole pattern** (`:1-27`) — an env-overridable, credential-free,
deliberately-not-in-the-manifest configuration document:

```yaml
# yaml-language-server: $schema=../../../docs/schemas/ccf.declared-artifact.json
# Live-mode provider and runner configuration for the portability drive
# (plan 08-11; D-03/D-04). Everything here is a *deployment* value — endpoint
# defaults, model identifiers, auth-token placeholders, timeout and budget
# numbers, and the drive turn a live session is sent — which is why none of it
# is a code constant (No-Hardcoding Rule, CLAUDE.md §6.4). Environment
# variables override the defaults recorded here:
#
#   CCF_OLLAMA_BASE_URL       overrides providers.ollama.default_base_url
#   CCF_OLLAMA_MODEL          overrides providers.ollama.default_model
#   CCF_LIVE_TIMEOUT_SECONDS  overrides runner.default_timeout_seconds
#   ANTHROPIC_API_KEY         required for --provider anthropic (never stored)
#
# **Not a manifest entry, deliberately.** This document configures the opt-in
# live legs, which are excluded from `make ci` (D-11/D-12). Naming it in the
# manifest would make the CI leg parse and hand back configuration for a mode
# it never enters; `run.py` loads it in `_live` and nowhere else.
```

And the key-gating precedent (`:41-44`) — the exact posture the DGX creds need:

```yaml
    anthropic:
      # Key-gated (D-03): the key comes from ANTHROPIC_API_KEY in the
      # environment, is never written to an artifact, and its absence is a
      # refusal, not a fallback.
```

---

### 12. The network-free proof (socket guard)

**Analog:** `examples/03-harness-portability/legs/deterministic.py:93-123`

```python
def install_no_model_guard() -> Iterator[None]:
    """Fail the run if anything opens a socket (D-02, T-08-25).

    **A context manager, and the scoping is not cosmetic.** The guard patches
    two module-level names, and the drive now runs inside ``pytest`` as well as
    under ``make example-03`` (D-09). An unscoped patch would survive the drive
    and refuse egress for every *later* test in the same process ...
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the deterministic portability drive attempted network egress; it"
            " must run real harness machinery in-process with no model (D-02)"
        )

    connect = socket.socket.connect
    create_connection = socket.create_connection
    socket.socket.connect = refuse  # type: ignore[method-assign, assignment]
    socket.create_connection = refuse  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = connect  # type: ignore[method-assign]
        socket.create_connection = create_connection
```

**And the fire-check that makes it evidence** (`examples/03-harness-portability/run.py:515-525`):

```python
    with install_no_model_guard():
        # The guard is only evidence if it fires. A guard that silently failed
        # to install would leave every "no network" claim below unbacked, so
        # the example refuses to proceed rather than reporting a property it
        # did not establish.
        try:
            socket.create_connection(("127.0.0.1", 9))
        except AssertionError:
            pass
        else:  # pragma: no cover - a broken guard is a broken example
            raise RuntimeError("the no-model guard is not installed")
```

⚠ **The always-on backend matrix uses `sqlite` and `memory` only, so a
non-loopback guard is right; a *total* socket refusal would break nothing today
but would forbid the localhost container path forever.** RESEARCH R-5 warns the
planner not to resolve the container question silently — mirror that here by
guarding non-loopback egress specifically, and stating why in the docstring.

---

### 13. `examples/<new>/README.md`

**Analog:** `examples/00-quickstart/README.md` — seven `## ` headings, in order,
verified at `:3, 26, 62, 149, 184, 198, 229`:

```
## What this demonstrates
## Run it
## The story
## Artifact-by-artifact
## Whitepaper / CLAUDE.md sections exercised
## What to change first
## What would fail
```

**The template is machine-asserted**, so it is a contract rather than a
convention — `examples/external/00-hello-context/run.py:433-455`:

```python
def _assert_seven_heading_readme() -> None:
    """D-17/D-08: the seven Phase-13 template headings, by name, in order."""
    readme = (_EXAMPLE_ROOT / "README.md").read_text(encoding="utf-8")
    headings = tuple(
        line[len("## "):].strip()
        for line in readme.splitlines()
        if line.startswith("## ")
    )
    if len(headings) != len(README_HEADINGS):
        raise AssertionError(
            f"README.md has {len(headings)} '## ' headings; the template "
            f"requires exactly {len(README_HEADINGS)}: {headings}"
        )
```

⚠ `examples/06-decision-replay/README.md:189` carries the heading **"Gate 2
independence (INV-CH7-47)"** — the exact framing criterion 8 forbids. It dies
with the example; **do not carry that heading forward** when writing the new
READMEs by reference to the old ones.

---

### 14. `tests/examples/test_<new>_output.py`

**Analog:** `tests/examples/test_quickstart_output.py`

**The module loader** (`:101-116`) — every example test in the tree uses this,
and the `sys.modules`-before-`exec_module` step is not optional:

```python
def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.
    """
    name = "quickstart_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
```

**The two-categories-of-assertion docstring** (`:54-77`) — reproduce this section
in every new `test_*_output.py`. It is what keeps A-4 honest by construction:

> * **Independent expectations.** `expected.yaml` declares what the *served
>   product* should contain. Nothing in the pipeline derives those numbers from
>   that file … so changing either side alone makes the assertion fail.
> * **Propagation checks.** The temporal boundary, the perspective role, the
>   product's schema name and its required operator set are each read from an
>   artifact by `run.py` *and* by this module, so the artifact is a single
>   source and editing it moves both ends together …
>
> Both belong here. Only the first is a statement about whether the fabric
> computed the right answer, and this module does not claim otherwise.

**The A-4 site, with its own honest caveat already written** (`:187-208`) — this
is the wording SURFACE-AUDIT A-4 says must **not** be promoted as an
independence proof, and the disclaimer must travel with the assertion:

```python
def test_every_declared_operator_actually_ran(result: Any) -> None:
    """...
    Still not proven here: that the two were authored rather than copied. A
    deployment that reads one document into the other collapses the binder, and
    this assertion goes back to comparing one value against itself with nothing
    in the output to show for it.
    """
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(result.operators_invoked)
```

**The genuinely independent statements** are the consumer-side ones —
`tests/examples/test_cross_process_output.py:268` and
`tests/examples/test_ext00_serve_output.py:275`. Those are the two the new suite
may cite as independence.

---

### 15. Section 2 client legs

**`client_adk.py` — exact analog exists:** `examples/external/00-hello-context/client_adk.py`.
Its import block is the whole demonstration and must stay legible:

```python
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types
```

Its docstring states the claim in the form the new legs should restate
(`client_adk.py:1-16`):

> *"Zero CCF imports (D-06); the only CCF knowledge is `CCF_MCP_URL` and
> `CCF_TOKEN`."* … *"Determinism in CI is transport-level only (D-09) …
> No CI/live branch exists."*

**`client_bare.py` — exact analog**, and it is the only client leg carrying
snippet markers (`:27, 39, 63` → `mcp-connect`, `mcp-discover`, `mcp-resource`).
Those three names are the published decomposition of an MCP client leg; reuse
them.

**`client_claude_agent.py` — partial only.** `client_anthropic.py` drives the
**raw `anthropic` SDK + `mcp` client**, not `claude-agent-sdk`. It is the nearest
in-tree shape (env-configured, zero-CCF, replay-server-determinized) but it is
not the same harness binding. RESEARCH F-2 confirms this gap.

**`client_langgraph.py` — NO ANALOG.** See § *No Analog Found*.

---

### 16. The FIBO data extension (F-1)

**Analog (in-tree, No-Hardcoding-compliant):** `examples/08-e2e-demo/generator.py:1-37`

```python
"""Deterministic synthetic source-system generator for the e2e demo (DEMO-01).

This module is a **pure interpreter** of ``artifacts/scenario.yaml``
(CLAUDE.md §6.4 No-Hardcoding Rule; Phase 12 CONTEXT D-05..D-08): it holds no
vocabulary — no source names, table names, column names, aliases, amounts, or
lexicon words. Everything domain-specific comes from the scenario artifact;
this code knows only mechanism roles ...

Structural constraints:

- **Single-writer (CLAUDE.md §10):** this module never touches the Context
  Graph. It writes standalone SQLite *source-system* files only; rows enter
  the fabric exclusively through ``handle.worker.ingest`` in ``run.py``.
- **Determinism (D-08 ...):** one ``random.Random(scenario["seed"] + offset)``
  per generation stream ... every timestamp derives from the scenario's fixed
  ``epoch`` plus offsets — never a clock read ...
```

> **This is the single most important pattern for the F-1 data extension.** The
> extension writes an *enterprise source estate*, never CCF's graph — which is
> D-04's read-side/write-side split expressed as code. `generator.py`'s
> single-writer paragraph is the sentence to reproduce.

**Analog (out-of-tree, the substrate shapes):**
`/home/parkave/fluree/examples/fibo/load_neo4j.py:1-13` — the env-first,
placeholder-fallback connection posture and the JSONL reader:

```python
# Prefer env vars; fall back to placeholders you can edit
URI = os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "CHANGE_ME")

ENTITIES = Path("mongo-entities.json")
RELS = Path("mongo-relationships.json")
```

⚠ **`192.168.4.76` must not enter the repo as a literal in a `.py` file.**
RESEARCH V-4(d) makes `git grep -c "192.168.4.76" -- examples/ public/ src/
runtime/` a gate returning 0 **except** in an env-defaulted, value-free artifact.
The `live.yaml` pattern (entry 11) is where a default endpoint legitimately
lives; a Python constant is not.

---

### 17. New published pages

**Front matter: there is none.** Every page under `public/` opens on an H1.
The single exception is `public/tutorial/demo-walkthrough.md:1-6`, an HTML
comment (not YAML front matter):

```markdown
<!--
  Snippet configuration for every literal include below lives in
  `mkdocs.yml` (pymdownx.snippets `base_path: ["."]`, repo root).
  Nothing in this page pastes code — the doc always shows the exact
  files that run in CI.
-->

# How data folds into context
```

**Tutorial analog:** `public/tutorial/adopters-guide.md:1-40`. Its opening states
the include contract and the through-line — both worth restating per new
tutorial page:

> *"Every block of code and every artifact on this page is **literal-included
> from an example the CI pipeline runs**. Nothing here is pasted, so nothing
> here can drift: if one of these sources moves, this page fails to build. Each
> section names the one command that runs its example, so you can reproduce what
> you are reading as you read it."*

⚠ **This page is RESEARCH R-1** — 447 lines, 35 includes, six of ten examples.
Copy its *form*, never edit the file itself before the terminal wave.

**How-to analog:** `public/how-to/grant-and-revoke-a-skill.md:1-53`. The shape
is: intent paragraph → "the single assertion worth carrying away" → include
provenance line → `## Before you start` → the run command in a fenced `sh`
block → numbered `## Step N` sections, each pairing one YAML whole-file include
with one marker include:

````markdown
Run the worked example at any point with:

```sh
make example-02
```

Exit 0 means every assertion held, including the refusal — the example fails
if the governance check does not fire.

## Step 1 — declare the catalog

...

```yaml
--8<-- "examples/02-skilling/artifacts/skill-catalog-enrollment-metrics.yaml"
```

The driver registers what the artifact declared. Note that registration binds
nothing — a catalog entry is an offer, not a capability:

```py
--8<-- "examples/02-skilling/run.py:skill-catalog"
```
````

**Reference (artifact) analog:** `public/reference/artifacts/product-registration.md:1-40`.
Shape: intent paragraph → bare `:::` mkdocstrings directives → `## Worked
example` → whole-file YAML includes with prose explaining *what the document
does not declare and why*.

**Reference (protocol) analog:** `public/reference/protocols/context-products.md:1-33`.
Nearly all `:::` directives, plus the cross-link discipline that avoids the
strict build's duplicate-identifier failure:

> *"The registration surface a product class is served under … is generated
> once, on [Context Product registration](../artifacts/product-registration.md),
> because it is an authoring artifact rather than a runtime Protocol. Rendering
> it twice would give the same identifier two primary URLs, which the strict
> build refuses."*

**Concept analog:** `public/concepts/invariants.md:1-33`. The per-invariant
triple — **The promise. / Why the architecture forces it. / How it is enforced.**
— plus a mermaid include. That triple is the right template for a page teaching
the six axes of `G`, with each axis mapped to its observable surface (RESEARCH
C.1's table).

**Nav registration** — `mkdocs.yml` `nav:` enumerates every path explicitly with
**no globs**, and under `validation.nav.omitted_files: warn` + `--strict`, a new
page absent from nav *fails the build* and a nav entry whose file was deleted
*fails the build*. Copy the existing indentation and the section grouping:

```yaml
  - How-to:
      # D-17 placement: the security and deployment notes lead the How-to
      # section.
      - Manage keys and secrets: how-to/security-and-deployment.md
      - Grant and revoke a skill: how-to/grant-and-revoke-a-skill.md
```

**Citation form (`cite01/02/03`).** Verified: **`public/` carries zero
`file.py:NNN` citations today.** Both greps returned empty. The in-use form for
pointing at mechanism is (a) a backticked decision id — `` `D-IMPL-86` ``,
`` `INV-CH7-47` `` — and (b) an mkdocstrings `:::` directive. The safest posture
for new pages is to keep it that way; if a source citation is unavoidable, use
`module.py::symbol`, never `module.py:NNN`.

**Include-path allowlist.** `tools/publish_scan.py:104-112` is a **positive**
allowlist — a new example directory outside `examples/` fires
`pub04-include-escape`:

```python
INCLUDE_ALLOWED_PREFIXES: tuple[str, ...] = (
    "examples/",
    "public/",
    "perf/baselines/",
)

#: Individual repo-root files the published tree legitimately embeds. Kept
#: separate from the prefixes so a root-level file cannot open a whole tree.
INCLUDE_ALLOWED_FILES: frozenset[str] = frozenset({"openapi.json"})
```

---

### 18. `.github/workflows/live-legs.yml` — the DGX opt-in job

**Analog:** `live-legs.yml::examples-live-anthropic` (:94-138) — the two
load-bearing parts are the dispatch-only guard and the fail-fast secret step:

```yaml
  examples-live-anthropic:
    name: example 03 live leg (Anthropic, secret-gated — D-11)
    runs-on: ubuntu-latest
    # Dispatch only, same reason as the Ollama leg above — and one sharper: a
    # scheduled run of this job spends real API credit weekly, and on a
    # repository without the secret it would go red every Monday for a reason
    # unrelated to anything anyone changed.
    if: github.event_name == 'workflow_dispatch'
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      # Fail fast with a clear message when the secret is absent, before any
      # setup work. The key reaches only this job and is never echoed
      # (T-08-28); the deterministic pipeline in ci.yml is keyless.
      - name: Require ANTHROPIC_API_KEY secret
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "::error::ANTHROPIC_API_KEY secret is not configured for this" \
              "repository. Add it under Settings > Secrets and variables >" \
              "Actions, then re-dispatch this workflow."
            exit 1
          fi
          echo "ANTHROPIC_API_KEY secret is present."
```

**The `.venv` provisioning step is mandatory** for any job invoking a `make`
target — it is what makes the CI and local command strings identical (D-10),
and it appears in every job in both workflows:

```yaml
      # The Makefile targets use .venv/bin/python; provide the venv the same
      # editable install the job already has, so CI and local runs execute the
      # identical `make examples` command string (D-10).
      - name: Provision .venv for the Makefile command surface
        run: |
          python -m venv .venv
          .venv/bin/pip install -e ".[dev]"
```

⚠ **Do not copy the `ci.yml` service-container credential pattern for the DGX.**
RESEARCH B.3: `ccf_test_password` in the workflow file is acceptable only because
the container is ephemeral and localhost-only. DGX credentials are real, and go
through `${{ secrets.* }}` + `backend_secrets: [{field, env_var}]`.

**The Makefile leg pattern to mirror** (`Makefile:138-155`) — env-overridable URI
default, `CCF_REQUIRE_*=1` so a skip is a failure, `-rs` so skips are reported:

```make
leg-neo4j: ## Neo4j leg against a real server — Cypher pushdown byte-identical to the fallback (plan 15.2-12)
	$(ENV) CCF_REQUIRE_NEO4J=1 CCF_TEST_NEO4J_URI=$(CCF_TEST_NEO4J_URI) \
		$(PYTHON) -m pytest tests -q -m neo4j -rs
```

---

### 19. `make gate-16` — HISTORY-ONLY ANALOG

**`make gate-15.3` does not exist in the tree.** It was retired by plan 15.4-07
(commit `d364b65`, *"retire the D-IMPL-92 line-budget gate, replaced not
removed"*). `Makefile:153-158` carries the retirement note in prose. The gate is
recoverable, and `D-GATE-15.4` records the SHA deliberately so it stays
retrievable.

**Recover it with:**

```
git show 50e79e7:Makefile              # the target, lines 145-151
git show d364b65^:tools/gates/gate_15_3.py
```

**The target** (`git show 50e79e7:Makefile:150-151`):

```make
gate-15.3: ## Phase 15.3 permitted-change-surface gate — D-IMPL-92 layer 2 (blocking, D-07)
	$(ENV) $(PYTHON) -m tools.gates.gate_15_3
```

**The three disciplines to inherit** (from `gate_15_3.py`'s own docstring, at
`d364b65^`):

1. **Location.** `tools/gates/`, not `tools/lints/` — *"the check lives with the
   phase rather than in `tools/lints`, because it asserts a fact about one
   phase's diff, not a standing invariant."*
2. **Output contract, copied from `tools/lints` and nothing else.** Findings as
   `path:line rule message` on stdout, summary on stderr, `return 1` on any
   finding, one named `RULE_*` constant per rule. **No report-only mode** —
   *"the exit code is the only gate signal, because a non-blocking mode is how
   an invariant quietly stops being one."*
3. **Two visibly-distinct layers.** LAYER 1 NORMATIVE (the claim, quoted) and
   LAYER 2 MECHANICAL (the approximation that runs). *"a reader must be able to
   tell them apart."*

⚠ **And inherit its failure mode as a warning.** `D-GATE-15.4` records that
`gate_15_3.py` was pinned to one commit range and one adapter by construction
(`PHASE_BASE`, `ADAPTER_MODULE`), and crashed with `KeyError: 'enum'` when run
once before removal. A `gate_16.py` should state its own expected supersession.

**Criterion 10's assertion, with D-13's carve-out** — RESEARCH V-10 plus
CONTEXT D-13: `git diff --stat <base>..HEAD -- src/ runtime/` carries **one
enumerated exception** (the `ProductClassDeclaration` docstring in
`src/ccf/controlplane/artifacts.py`), not zero.

---

### 20. `docs/DECISIONS.md` — the `D-IMPL-94` entry

**Next free id verified: `D-IMPL-94`.** Highest present is `D-IMPL-93` (line 318).

**Two house shapes are in use. Pick by kind.**

**Shape A — a resolved open question** (`docs/DECISIONS.md:187`, D-IMPL-63). Use
this if D-02 is framed as answering an open item:

```markdown
---

**D-IMPL-63 — D-IMPL-21 reference identity-binding implementations.** RESOLVED — **deferred. 2026-07-30. Approver: Dave.** The two D-IMPL-21 reference identity-binding implementations … move to **explicit follow-up-phase scope** — a named deferral, not an indefinite posture. … Surfacing context, preserved: surfaced by the Phase I.4 gate review (Codex finding C-3). … Question for Dave: defer both reference impls to a named phase (with the caller-supplied posture stated as the v0 …
```

**Shape B — a standing ruling with measured evidence** (`:318`, D-IMPL-93). Use
this for D-02, which is a structural ruling about where Mode 2 attaches:

```markdown
**D-IMPL-93 — The substrate-evolution standard: …** Date: 2026-08-09. Decided by: Dave, clarifying the criterion Phase 15.3's gate had been approximating. **Why this is recorded.** … **The standard, in three tests.** … **What the tree measured against it, 2026-08-09 at `773ed92`.** … **What is NOT relaxed.** … **Consequence.** … **Scope.** Standing. … Originates: Dave, 2026-08-09, in response to …; `src/ccf/boot.py`; `src/ccf/graph/_writer.py`; …
```

**House conventions, verified across both:** a `---` separator before each entry;
the entry is **one paragraph** with bold sub-headers inline (never sub-headings);
`**D-IMPL-NN — Title.**` opener; an explicit date and approver; a
`Surfacing context, preserved:` or `Originates:` tail naming every source file
and decision consulted; backticked path citations. **`docs/DECISIONS.md` is
exempt from `cite01/02/03`** (`tools/lints/citations.py:173-178`), so `file:NNN`
citations are permitted there and nowhere else in this phase's output.

**The D-02 ruling's own evidence is already assembled** in RESEARCH D.4 — the
`serve()` signature, the *"exactly two acts"* description, and the Phase 04
decision (*"serve() is one expression because the replay append returns the
delivery capability — there is no branch that reaches delivery without a
recorded decision"*). Q-2 (what `assembly_mode` describes) folds into the same
entry per RESEARCH's recommendation. D-13, D-14 and D-15 from CONTEXT ride in the
same ruling package.

---

## Shared Patterns

### Negative controls — apply to every new guard

**Source:** `tests/examples/test_ext00_serve_output.py:425-459`
**Apply to:** `test_section_one_is_agent_free.py`, the AST-upgraded zero-import
guard, `test_spine_separation.py`, `test_adoption_argument.py`

This is the pattern RESEARCH names, and it is verified present and parametrized:

```python
def test_the_committed_client_legs_import_no_ccf(run_module: Any) -> None:
    """The charter, over the shipped files (mirrors ``run.py`` PASS 3)."""
    run_module._assert_zero_ccf_imports()


@pytest.mark.parametrize(
    "injected", ["from ccf.boot import boot\n", "import ccf_runtime\n"]
)
def test_the_zero_import_assertion_fails_when_a_leg_imports_ccf(
    run_module: Any,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    injected: str,
) -> None:
    """The assertion is verified to REFUSE, not merely to pass.

    A grep that matched nothing would be green forever, and this example's
    whole point rests on it. The legs are copied to ``tmp_path``, one is given
    a CCF import, and ``_EXAMPLE_ROOT`` is pointed at the copies — so the real
    function, its real glob and its real regex are exercised. Both import
    forms are probed because the pattern must catch ``from ccf ...`` and
    ``import ccf_runtime`` alike.
    """
    for leg in sorted(EXAMPLE_DIR.glob("client_*.py")):
        shutil.copy(leg, tmp_path / leg.name)
    monkeypatch.setattr(run_module, "_EXAMPLE_ROOT", tmp_path)

    # The copies alone still pass — so the failure below is the injection.
    run_module._assert_zero_ccf_imports()

    target = tmp_path / "client_bare.py"
    target.write_text(injected + target.read_text(encoding="utf-8"), "utf-8")
    with pytest.raises(AssertionError) as excinfo:
        run_module._assert_zero_ccf_imports()
    assert "client_bare.py" in str(excinfo.value)
```

**The guard it controls** (`examples/external/00-hello-context/run.py:421-430`) —
this is the function RESEARCH says to *upgrade to AST, not rebuild*:

```python
def _assert_zero_ccf_imports() -> None:
    """D-06: static grep over the client legs — the charter, mechanically."""
    pattern = re.compile(r"^(import|from) (ccf|ccf_runtime)", re.MULTILINE)
    offenders = [
        path.name
        for path in sorted(_EXAMPLE_ROOT.glob("client_*.py"))
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    if offenders:
        raise AssertionError(f"CCF imports found in client legs: {offenders}")
```

⚠ **The known blind spot to close.** Line-anchored, so it misses
`importlib.import_module("ccf")`, an indented import inside a function, and
`__import__`. The AST upgrade must use `tools/lints/__init__.py`'s
`imported_module_names` **and** `submodule_import_names` (CR-02), and the
parametrized negative control must gain params for each newly-caught spelling —
a widened matcher with an unwidened control is a widening nobody proved.

**Two more negative-control precedents worth reading:**

- `tools/docs_tests/test_snippet_gate.py` — three cases: two violating polarities
  (deleted marker, missing file) exercised *separately on purpose* because
  `pymdownx.snippets` guards them at two call sites, plus a clean control.
- `tools/docs_tests/test_openapi_drift_control.py:50-74` — both polarities on
  every run, and the drift-proof victim selection: *"Whichever path sorts first —
  never a literal endpoint name, so route churn cannot turn this control into a
  no-op."*

### Vacuous-pass preconditions — apply to every new gate module

**Source:** `tools/docs_tests/test_diagram_coverage.py:66-80`, echoed at
`tools/publish_scan_tests/test_docstring_leaks.py:143-163`
**Apply to:** all five new `tools/docs_tests/` modules and
`tests/examples/test_spine_separation.py`

```python
# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# WR-04: the walk was CWD-relative, so off-root it scanned zero files and the
# gate below passed over nothing. `tools/docs_tests/test_diagram_coverage.py`
# is the model.
# --------------------------------------------------------------------------


def test_documented_trees_are_populated() -> None:
    for tree in DOCUMENTED_TREES:
        root = REPO_ROOT / tree
        assert root.is_dir(), f"missing documented tree: {root}"
    assert _iter_python_files(), "no python sources scanned"


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _iter_python_files(), "the walk resolved against the CWD, not the repo"
```

Plus the invariant every one of these modules opens with:

```python
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
```

### Paragraph scoping — the anti-under-count discipline

**Sources:** `tools/lints/citations.py:279-294, 491-503` (sentence window +
offset mapping); `tools/publish_scan.py:141-150` (markup-stripping normalization).
**Apply to:** `test_gate_two_wording.py`, `test_no_stale_example_paths.py`'s
prose half, `test_adoption_argument.py`, and **every prose sweep in the phase**.

RESEARCH P-2 is the reason: *"Phase 15.1 under-counted the same sweep six
times; the fix that finally worked was paragraph-scoping."* A plan step spelled
`grep -rn "<phrase>"` is the warning sign.

### AST over source — always use the shared helpers

**Source:** `tools/lints/__init__.py:122-162`
**Apply to:** `test_section_one_is_agent_free.py`, the zero-import guard upgrade,
`test_spine_separation.py`'s "no domain vocabulary in the spine" assertion.

```python
def submodule_import_names(node: ast.AST, *, package: str = "") -> list[str]:
    """Dotted names an ``ImportFrom`` reaches by naming a *submodule*.

    ``from ccf.graph import _writer`` binds ``ccf.graph._writer`` just as surely
    as ``import ccf.graph._writer`` does, but :func:`imported_module_names`
    reports only ``ccf.graph`` for it ...

    Lives here rather than in one checker because every import rule needs it —
    ``cinv02-harness``, ``cinv02-graph-writer``, ``cinv02-backend-import``,
    ``cinv02-deployment-gates``, ``cinv03-algorithmic`` and
    ``d06-orchestration-split`` — and a helper imported from a sibling checker
    is how one rule's edit silently changes another's.
    """
```

The richer AST-channel walk — module, class/function, PEP 258 attribute
docstrings, **and `#:` comment runs** — is at
`tools/publish_scan_tests/test_docstring_leaks.py:105-135`. Read it if the phase
needs to scan documented text out of a source file rather than imports.

### The corrected superseded-claim wording (R-8)

**Source:** `examples/05-workflow-hitl/artifacts/manifest.yaml:26-63`
**Apply to:** every new manifest and every artifact-explanation comment.

⚠ **This is the wording to converge on.** RESEARCH R-8: the superseded-claim
sweep is **still open in `examples/01`–`04`**, those directories retire under
D-07 — *"but the same false claims may be copied forward into the new examples
if anyone writes the new artifacts by reference to the old ones."*

```yaml
# **What is NOT here, and why.** Six documents in this directory are outside the
# manifest. None of them is outside it because naming one would be *dangerous* —
# that was true when plan 15-19 wrote this note, and the SDK has since closed it.
# What the SDK now does, so an adopter reading this file learns the mechanism
# rather than a convention:
#
#   * The `ccf.` prefix is RESERVED (D-IMPL-84). A manifest entry naming a
#     `ccf.`-prefixed class id the SDK does not ship is REFUSED at load, before
#     any document is read. ...
#   * The registration PATH is fixed by the class, not by the deployment
#     (D-IMPL-85). Declaring `registration: typed` for an author-versioned class
#     is refused in the same preflight, because `register_typed` runs no D-05
#     bump check and the author's `artifact_version` claim would go unheld.
```

**Do not copy** `examples/00`–`04` manifest prose asserting that a manifest
*cannot* name an author-versioned class. RESEARCH § *State of the Art* records
the correction: a manifest **may** name all six as `registration: versioned`;
what is refused is `registration: typed` for such a class.

### `[ADAPT]` / `[MECHANISM]` → the D-11 structural separation

**Source:** `examples/00-quickstart/artifacts/manifest.yaml:26-34` (and
`live.yaml:23-27`, `harnesses.yaml`)
**Apply to:** every new artifact **and**, per RESEARCH D.3 option 3, the header
of every new code file in the spine/deployment split.

CONTEXT explicitly says this convention *"should inform"* D-11. Extending the
same two words to code headers costs no new marker vocabulary — which is what
D-11 forbids.

### The example-code assertion ban (ERGO-16 / D-09)

**Source:** `examples/00-quickstart/run.py:9-13`; `tests/examples/test_quickstart_output.py:1-11`
**Apply to:** every new example.

> *"This file is the **call spine** an adopter would actually write, and nothing
> else. It asserts nothing and prints nothing: its assertions live in
> `tests/examples/test_quickstart_output.py` … `make example-00` running clean
> means the spine executed."*

This is half the reason Phase 16 exists (~85 assertion/print lines inflating
apparent integration cost). New examples must be **thinner** than today's, not
richer (CLAUDE.md §6.4 / C-2).

---

## No Analog Found

Files with no close match in the tree. The planner should use RESEARCH.md
patterns, or accept these as genuinely new work.

| File / pattern | Role | Data flow | Nearest partial | Why it is not an analog |
|---|---|---|---|---|
| `examples/<sec2>/client_langgraph.py` | client leg | request-response | `runtime/ccf_runtime/adapters/langgraph/adapter.py` | **The adapter is not a client.** It imports `ccf` (it binds the four §7.3 seams inside nodes it constructs) and is the exact inverse of Section 2's zero-CCF-dependency claim. Nothing in the tree drives an MCP session from a LangGraph node. RESEARCH F-2 and R-4 both confirm; `langchain-mcp-adapters` is not installed and is **recommended against**. RESEARCH's recommended path — `mcp.ClientSession` + `streamablehttp_client` inside a node, tools bound by hand — has no in-tree precedent either. **Spike this in Wave 1 against the *existing* `examples/external` server.** |
| The adoption-argument page (D-10) | doc | — | `public/concepts/invariants.md` (promise / why / enforcement triple) | **G-01 measured zero hits site-wide** for "why not just", "instead of building", "rather than building", "compared to". No published page in this project has ever made a comparative-rationale argument. The *page form* can be borrowed from `invariants.md`; the *genre* is new. Its evidence table is already assembled in RESEARCH § E, including the mandatory `passage_anchor` honesty caveat. |
| A page teaching the six axes of `G(E, R, T, P, Π, L)` | doc | — | `public/concepts/whitepaper-index.md:19` (a bare table row) | RESEARCH C.1 verified: `grep "six axes"` over `public/` returns three hits, and all but one are about the **six specialization axes of an agent**. This is genuinely new content. The axis→observable-surface mapping is in RESEARCH C.1 and is the material to write from. |
| A single paragraph-scoped assertion over `public/**/*.md` | test helper | transform | **two halves, both real** — `citations.py::citation_sentence` (offset→sentence, over a tree that includes `public`) and `publish_scan.py::normalize` (markup-stripping over published Markdown) | No existing module does paragraph-scoped matching over `public/**/*.md`. `test_diagram_coverage.py` walks the tree but matches a line-scoped regex; `publish_scan.py` normalizes whole files rather than paragraphs. `test_gate_two_wording.py` is the composition of the two halves and should extract a shared helper rather than inlining it three times across V-5/V-7/V-8. |
| `make gate-16` / `tools/gates/gate_16.py` | config / utility | transform | `tools/gates/gate_15_3.py` at `d364b65^` — **retired, git history only** | Recoverable and worth reading (three disciplines listed in entry 19), but not in the working tree. Its output contract came from `tools/lints/__main__.py::main`, which *is* live. |

---

## Retirement Map — analogs that die, and where their patterns must land first

Per D-07 there is no partial state. These are the files an executor will be
tempted to open as analogs *after* they are gone. Their patterns are captured
above; the source files are not durable.

| Retiring | Pattern captured in this file at |
|---|---|
| `examples/00-quickstart/` | entries 9, 10, 13; shared § *example-code assertion ban* |
| `examples/03-harness-portability/` | entries 9, 11, 12 |
| `examples/05-workflow-hitl/artifacts/manifest.yaml` | shared § *corrected superseded-claim wording* ⚠ **highest-value capture** |
| `examples/08-e2e-demo/generator.py` | entry 16 |
| `examples/external/00-hello-context/` | entries 13, 15; shared § *negative controls* |
| `tests/examples/test_quickstart_output.py` | entry 14 |
| `tests/examples/test_ext00_serve_output.py` | shared § *negative controls* |
| `tests/examples/test_gate_two_divergence.py` (rewritten, not retired) | entry 5 |

⚠ **`tools/docs_tests/test_snippet_gate.py:39-40` hard-points at
`examples/00-quickstart/run.py` and its `[start:ontology]` marker** — which no
longer exists, and which is why two of its three tests fail at HEAD. Repointing
those two constants at a new example and marker is a Wave-0 prerequisite
(RESEARCH § *Wave 0 Gaps*), not cleanup.

---

## Metadata

**Analog search scope:** `tests/examples/`, `tests/conformance/`, `tests/agents/`,
`tests/conftest.py`, `tools/docs_tests/`, `tools/publish_scan_tests/`,
`tools/lints/`, `tools/publish_scan.py`, `examples/` (all 10 directories),
`public/` (41 pages), `mkdocs.yml`, `Makefile`, `.github/workflows/`,
`docs/DECISIONS.md`, plus `git show` against `50e79e7` and `d364b65^` for the
retired gate, and `/home/parkave/fluree/examples/fibo/` (out of repo).

**Files opened and excerpted:** 27
**Pattern extraction date:** 2026-08-10
**Tree state:** `84f4501`
