# Property-not-shape gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `phase-16` green with no example modified, by rewriting two test
gates to assert the properties their docstrings claim rather than the filenames
and call sites the first example happened to have.

**Architecture:** `tests/examples/test_spine_separation.py` discovers roles from
file content (regions, prints, `ccf` imports) instead of from four filename
constants. `tests/products/test_gate_two_call_shape.py` conditions its binder
demand on the premise the demand rests on — the deployment registering a
`ccf.projection-requirements` artifact — read as a conjunction with the AST and
defaulting fail-closed. Both changes are test-only; no `src/`, `runtime/` or
`examples/` file is touched.

**Tech Stack:** Python 3.12+, `pytest`, `ast`, `pathlib`, `re`. No new
dependencies.

**Spec:** `docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md`

## Global Constraints

- **No example file changes.** If a task appears to require editing anything
  under `examples/`, stop — the design is wrong, not the example. The only
  writes under `examples/` are to `tmp_path` copies inside controls.
- **No `src/` or `runtime/` changes.** This is a test-gate rewrite.
- **Run tests with `.venv/bin/python -m pytest`.** There is no bare `python` on
  PATH in this environment.
- **`grep` is a ugrep shim that auto-recurses.** Use `command grep` for any
  measurement whose result is quoted in a commit message or a docstring.
- **Every predicate the shipped tree is judged by is the same function the
  negative controls exercise.** Keep `spine_problems(directory)` as gate 1's
  aggregate and `_binder_collapses(scope, path)` as gate 2's, so a control
  cannot pass against code the tree is not judged by.
- **Floors and ceilings carry `FLOOR_REMOVAL_INSTRUCTION`.** No headroom.
- **Docstrings record what a check cannot do.** Both modules state their limits
  explicitly; new predicates follow that convention or the module becomes a
  claim it cannot support.

---

### Task 1: Gate 1 — role discovery and the region properties (P1–P4)

**Files:**
- Modify: `tests/examples/test_spine_separation.py` (module constants at
  lines 44–67; `spine_problems` at 143–171; tests at 191–304)

**Interfaces:**
- Produces, consumed by Task 2 and by both tasks' controls:
  - `CCF_IMPORT_RE: re.Pattern[str]`
  - `fabric_facing(directory: pathlib.Path) -> list[pathlib.Path]`
  - `region_modules(directory: pathlib.Path) -> list[pathlib.Path]`
  - `spine_problems(directory: pathlib.Path) -> list[str]` (kept, rewritten)
- Consumes from the existing module, unchanged: `modules_in`, `markers`,
  `opened`, `unbalanced`, `CANONICAL_MARKERS`, `MARKER_RE`, `split_examples`,
  `EXAMPLES_ROOT`, `SECTION_ONE_GLOB`, `_copied_example`.

**Scope note carried from the spec's first planning correction:** region
properties scan **every** module; only the printing properties (Task 2) scan
fabric-facing modules. A `--8<--` region in a module importing no `ccf` is still
published-snippet surface.

- [ ] **Step 1: Write the failing controls**

Replace `test_the_gate_refuses_a_renamed_spine` (lines 417–428) with the control
for the direction it used to cover, and generalise the two module-named region
controls into one. Delete
`test_the_gate_refuses_a_canonical_marker_in_the_report_module` (lines 484–505)
outright.

```python
def test_the_gate_refuses_an_example_with_no_region_carrying_module(
    tmp_path: pathlib.Path,
) -> None:
    """Zero carriers is a refusal, not a vacuous pass.

    This is the direction the deleted rename control used to cover. Renaming a
    module is now legal by design, so the property that replaces it is that
    SOME module carries the seven regions — which a rename cannot break and a
    deletion can.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    for name in CANONICAL_MARKERS:
        text = text.replace(f"[start:{name}]", "").replace(f"[end:{name}]", "")
    spine.write_text(text, "utf-8")

    problems = spine_problems(example)
    assert any("no module opens" in problem for problem in problems), problems


def test_the_gate_refuses_a_second_module_carrying_canonical_regions(
    tmp_path: pathlib.Path,
) -> None:
    """A canonical region belongs to exactly one module, whatever it is called.

    Injected into a module that is NOT fabric-facing, because the region
    properties scan every module: a marker in a module importing no `ccf` still
    publishes a snippet, and scoping the region check would make it invisible.
    """
    example = _copied_example(tmp_path)
    carrier = region_modules(example)[0]
    outsiders = [
        module for module in modules_in(example) if module not in fabric_facing(example)
    ]
    # A non-fabric-facing module when the example has one, because that is the
    # case the scope rule could hide; any sibling otherwise.
    sibling = outsiders[0] if outsiders else next(
        module for module in modules_in(example) if module != carrier
    )
    name = CANONICAL_MARKERS[-1]
    sibling.write_text(
        sibling.read_text(encoding="utf-8")
        + f"\n# --8<-- [start:{name}]\n# --8<-- [end:{name}]\n",
        "utf-8",
    )

    problems = spine_problems(example)
    assert any("more than one module" in problem for problem in problems), problems
```

- [ ] **Step 2: Run the controls to verify they fail**

Run: `.venv/bin/python -m pytest tests/examples/test_spine_separation.py -k "no_region_carrying or second_module" -v`

Expected: FAIL with `NameError: name 'region_modules' is not defined`.

- [ ] **Step 3: Replace the filename constants with discovery**

Delete `SPINE_MODULE`, `REPORT_MODULE`, `SILENT_MODULES`, `PRINTING_MODULE`
(lines 48–64). Keep `PRINT_RE`. Add:

```python
#: How a module declares itself part of the fabric. The taxonomy applies to
#: modules that make CCF calls, because this gate is about how fabric calls
#: separate from adopter code — a module making none is not party to that
#: separation. `examples/s1-00/scenario/provision.py` fabricates a Postgres
#: source system, imports no `ccf`, prints, and says `THIS IS NOT CCF` in its
#: own docstring; it is out of scope by that principle rather than by name.
#:
#: **This governs the PRINTING properties only.** The region properties scan
#: every module: a `--8<--` region in a module importing no `ccf` is still
#: published-snippet surface, and scoping it would make such a marker invisible.
CCF_IMPORT_RE = re.compile(r"^[ \t]*(?:from|import)[ \t]+ccf\b", re.MULTILINE)
```

Add the two discovery functions after `modules_in`:

```python
def fabric_facing(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every module in the example that makes CCF calls."""
    return [
        module
        for module in modules_in(directory)
        if CCF_IMPORT_RE.search(module.read_text(encoding="utf-8"))
    ]


def region_modules(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every module opening at least one of the seven canonical regions.

    Over ALL modules, not the fabric-facing ones — see `CCF_IMPORT_RE`.
    """
    return [
        module
        for module in modules_in(directory)
        if set(opened(module)) & set(CANONICAL_MARKERS)
    ]
```

- [ ] **Step 4: Rewrite `spine_problems` against P1–P4**

Replace lines 143–171 entirely:

```python
def spine_problems(directory: pathlib.Path) -> list[str]:
    """Every way one example directory fails the separation contract.

    A single predicate over a directory, so the shipped tree and the injected
    copies below are judged by the same code rather than by two descriptions of
    the same intent. The properties, and which modules each scans:

    * P1/P4 — exactly one module opens canonical regions (ALL modules)
    * P2 — that module opens the seven `D-07` names, in order (that module)
    * P3 — every region it opens, it closes; none interleave (ALL modules)

    P5 and P6 are the printing properties and live in `print_problems`.
    """
    problems: list[str] = []
    carriers = region_modules(directory)
    if not carriers:
        return [
            f"{directory.name}: no module opens any of the seven canonical"
            f" regions {CANONICAL_MARKERS}. Section 1's shape is the CCF call"
            " spine in one module and the adopter's own code in another"
            " (phase 16 CONTEXT D-11, criterion 6) — the spine is whichever"
            " module carries the regions, and this example has none."
        ]
    if len(carriers) > 1:
        problems.append(
            f"{directory.name}: more than one module opens canonical regions"
            f" ({[module.name for module in carriers]}). A canonical region"
            " belongs to exactly one module; a region spanning two publishes a"
            " snippet straddling the boundary this example exists to draw."
        )

    spine = carriers[0]
    found = opened(spine)
    missing = [name for name in CANONICAL_MARKERS if name not in found]
    extra = [name for name in found if name not in CANONICAL_MARKERS]
    if missing:
        problems.append(f"{spine.name} opens no region for {missing}")
    if extra:
        problems.append(
            f"{spine.name} opens {extra}, which is marker vocabulary outside"
            " the seven D-07 names — D-11 adds none"
        )
    if not missing and not extra and found != CANONICAL_MARKERS:
        problems.append(
            f"{spine.name} opens the seven regions in order {found},"
            f" expected {CANONICAL_MARKERS}"
        )

    for module in modules_in(directory):
        problems.extend(f"{module.name}: {problem}" for problem in unbalanced(module))
    return problems
```

- [ ] **Step 5: Rewrite the region tests against the discovered module**

Replace `test_every_section_one_example_ships_a_spine_module` (lines 213–221)
with the P1 assertion, and repoint the three that named `SPINE_MODULE`:

```python
@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_exactly_one_module_carries_the_canonical_regions(
    directory: pathlib.Path,
) -> None:
    """P1 and P4, stated from both ends.

    The spine is whichever module carries the seven regions — a property a
    reader can check by opening the files, and one a rename cannot break. The
    previous form named `spine.py`, which made `D-IMPL-127`'s `produce.py` a
    failure while every property it claimed to prove held.
    """
    carriers = region_modules(directory)
    assert carriers, (
        f"{directory.name}: no module opens any canonical region"
    )
    assert len(carriers) == 1, (
        f"{directory.name}: {[module.name for module in carriers]} each open"
        " canonical regions; exactly one module must"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_spine_opens_the_seven_canonical_regions_in_order(
    directory: pathlib.Path,
) -> None:
    """P2 — both directions reported by name: what is missing and what is extra.

    Ordering is asserted as well as membership. The seven names are a
    decomposition a beginner is meant to be able to follow top to bottom, and a
    spine that records before it gates reads as a different story.
    """
    spine = region_modules(directory)[0]
    found = opened(spine)
    missing = [name for name in CANONICAL_MARKERS if name not in found]
    extra = [name for name in found if name not in CANONICAL_MARKERS]
    assert not missing, f"{directory.name}/{spine.name} opens no region for {missing}"
    assert not extra, (
        f"{directory.name}/{spine.name} opens {extra}, which is marker"
        " vocabulary outside the seven D-07 names — D-11 adds none"
    )
    assert found == CANONICAL_MARKERS, (
        f"{directory.name}/{spine.name} opens the seven regions in order"
        f" {found}, expected {CANONICAL_MARKERS}"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_every_region_opened_anywhere_is_closed(directory: pathlib.Path) -> None:
    """P3 — opened, closed, and never interleaved, in every module."""
    for module in modules_in(directory):
        problems = unbalanced(module)
        assert not problems, f"{directory.name}/{module.name}: " + "; ".join(problems)
```

Delete `test_no_region_spans_the_spine_and_a_sibling_module` (lines 263–287) —
P1/P4 and P3 together are what it asserted. Delete
`test_every_section_one_example_ships_a_report_module` (lines 307–327) and
`test_the_report_module_opens_no_canonical_region` (lines 330–347).

Repoint `test_the_marker_pattern_matches_the_shipped_form` (line 191) at the
discovered module:

```python
def test_the_marker_pattern_matches_the_shipped_form() -> None:
    """The regex is checked against a marker the suite actually ships.

    A pattern that matched nothing would make every assertion below vacuous,
    and the probe form is the one ``tools/docs_tests/test_snippet_gate.py``
    uses: look for the literal a source file contains.
    """
    spine = region_modules(split_examples(EXAMPLES_ROOT)[0])[0]
    assert f"[start:{CANONICAL_MARKERS[0]}]" in spine.read_text(encoding="utf-8")
    assert markers(spine), f"{spine} contains markers the pattern does not match"
```

- [ ] **Step 6: Repoint the remaining `SPINE_MODULE` references in the controls**

`test_the_gate_refuses_a_spine_whose_regions_are_out_of_order` (line 431),
`test_the_gate_refuses_an_unclosed_region` (line 452),
`test_the_gate_refuses_marker_vocabulary_outside_the_seven` (line 470) and
`test_the_gate_refuses_a_region_that_spans_both_modules` (line 508) each open
`example / SPINE_MODULE`. Replace every such line with:

```python
    spine = region_modules(example)[0]
```

Delete `test_the_gate_refuses_a_region_that_spans_both_modules` — Step 1's
`test_the_gate_refuses_a_second_module_carrying_canonical_regions` replaces it.

- [ ] **Step 7: Run the whole module**

Run: `.venv/bin/python -m pytest tests/examples/test_spine_separation.py -v`

Expected: PASS for every region test on both `s1-00` and `s1-01`. The printing
test `test_the_fabric_facing_modules_stay_silent_and_the_driver_prints` still
FAILS on `s1-00` — Task 2 rewrites it. Confirm the failure is that one test and
no other.

- [ ] **Step 8: Commit**

```bash
git add tests/examples/test_spine_separation.py
git commit -m "test(examples): discover the spine from its regions, not its filename

P1-P4 over every module in the example. The four filename constants and the
two tests that only asserted a filename are gone; `spine_problems` stays the
aggregate predicate the controls exercise. Region properties scan every module
because a marker outside the fabric-facing set is still snippet surface.

Refs docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md §3"
```

---

### Task 2: Gate 1 — the printing properties and the scope predicate (P5, P6)

**Files:**
- Modify: `tests/examples/test_spine_separation.py`

**Interfaces:**
- Consumes from Task 1: `fabric_facing`, `region_modules`, `spine_problems`,
  `CCF_IMPORT_RE`.
- Produces: `printing_modules(directory) -> list[pathlib.Path]`;
  `print_problems(directory) -> list[str]`, the aggregate the printing controls
  exercise.

- [ ] **Step 1: Write the failing controls**

Append after the region controls. The scope-predicate control is two-sided
because a refusal-only control passes just as happily against a predicate that
classifies everything as fabric-facing.

```python
def test_the_gate_refuses_a_region_carrying_module_that_prints(
    tmp_path: pathlib.Path,
) -> None:
    """P5 — this is what `D-11` is actually about.

    The published snippets are the spine's regions. A print inside them is a
    line an adopter would never write, inflating the example's apparent
    integration cost — the Phase 14.1 finding, restated as a property of
    whichever module carries the regions rather than of a module named
    `spine.py`.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8") + '\nprint("noise")\n', "utf-8"
    )

    problems = print_problems(example)
    assert any("carries the regions and prints" in p for p in problems), problems


def test_the_gate_refuses_an_example_that_prints_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """P6, zero direction — the shape Dave's ruling of 2026-08-13 rejected.

    Without this the printing check passes just as happily against a silent
    example: one that runs and shows a reader nothing.
    """
    example = _copied_example(tmp_path)
    for module in printing_modules(example):
        module.write_text(
            PRINT_RE.sub("_muted(", module.read_text(encoding="utf-8")), "utf-8"
        )

    problems = print_problems(example)
    assert any("prints nothing" in problem for problem in problems), problems


def test_the_gate_refuses_two_fabric_facing_printers(
    tmp_path: pathlib.Path,
) -> None:
    """P6, two direction — printing must not creep back across the split."""
    example = _copied_example(tmp_path)
    silent = next(
        module
        for module in fabric_facing(example)
        if not PRINT_RE.search(module.read_text(encoding="utf-8"))
    )
    silent.write_text(
        silent.read_text(encoding="utf-8") + '\nprint("noise")\n', "utf-8"
    )

    problems = print_problems(example)
    assert any("more than one" in problem for problem in problems), problems


def test_the_fabric_facing_scope_admits_and_excludes_on_the_import(
    tmp_path: pathlib.Path,
) -> None:
    """The control for the one new convention, both halves.

    HW-1's `scenario/provision.py` prints and imports no `ccf`. If the scope
    predicate did not exclude it, P6 would be false for a correct example; if
    the predicate excluded everything, P5 and P6 would pass over an empty set.
    One test asserts both directions against the same file.
    """
    example = _copied_example(tmp_path)
    outsider = example / "scenario" / "provision.py"
    # Asserted, not skipped. A skip here would silently disable the only
    # control of the one convention this rewrite introduces, on the day
    # somebody moved the file.
    assert outsider.is_file(), (
        f"{example.name} no longer ships scenario/provision.py — repoint this"
        " control at whichever module prints and imports no `ccf`"
    )

    # (a) it prints, imports no `ccf`, and the example is still compliant.
    assert PRINT_RE.search(outsider.read_text(encoding="utf-8"))
    assert not CCF_IMPORT_RE.search(outsider.read_text(encoding="utf-8"))
    assert not print_problems(example), print_problems(example)

    # (b) the same file, now importing `ccf`, is a second printer and refused.
    outsider.write_text(
        "import ccf.deployment\n" + outsider.read_text(encoding="utf-8"), "utf-8"
    )
    problems = print_problems(example)
    assert any("more than one" in problem for problem in problems), problems
```

- [ ] **Step 2: Run the controls to verify they fail**

Run: `.venv/bin/python -m pytest tests/examples/test_spine_separation.py -k "prints or scope_admits" -v`

Expected: FAIL with `NameError: name 'print_problems' is not defined`.

- [ ] **Step 3: Implement the printing discovery and aggregate**

Add after `region_modules`:

```python
def printing_modules(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every fabric-facing module that writes to the terminal."""
    return [
        module
        for module in fabric_facing(directory)
        if PRINT_RE.search(module.read_text(encoding="utf-8"))
    ]


def print_problems(directory: pathlib.Path) -> list[str]:
    """P5 and P6 — which side of the split writes to a terminal.

    Always-on and substrate-free by construction: it reads files. Both
    directions are needed. Without P5, printing creeps back into the spine and
    the published snippets grow lines an adopter would never write; without
    P6's lower bound, this passes just as happily against the silent example
    the ruling of 2026-08-13 rejected.

    Scoped to fabric-facing modules, which is what keeps a per-example
    provisioning utility — printing, importing no `ccf`, and explicitly not CCF
    — from counting as a second driver.
    """
    problems: list[str] = []
    facing = fabric_facing(directory)
    if not facing:
        return [
            f"{directory.name}: no module imports `ccf`, so the printing"
            " properties would pass over an empty set"
        ]

    carriers = region_modules(directory)
    if carriers and PRINT_RE.search(carriers[0].read_text(encoding="utf-8")):
        problems.append(
            f"{directory.name}/{carriers[0].name} carries the regions and"
            " prints. Presentation belongs in the module that drives the run;"
            " a printed line inside a published region is snippet surface an"
            " adopter would never write."
        )

    printers = printing_modules(directory)
    if not printers:
        problems.append(
            f"{directory.name} prints nothing — the example runs and shows a"
            " reader nothing (Dave's ruling, 2026-08-13)"
        )
    elif len(printers) > 1:
        problems.append(
            f"{directory.name}: more than one fabric-facing module prints"
            f" ({[module.name for module in printers]}). Exactly one drives"
            " the run."
        )
    return problems
```

- [ ] **Step 4: Replace the named-module printing test**

Replace `test_the_fabric_facing_modules_stay_silent_and_the_driver_prints`
(lines 350–377) with:

```python
@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_spine_is_silent_and_exactly_one_module_prints(
    directory: pathlib.Path,
) -> None:
    """P5 and P6, over the shipped tree, through the controls' own predicate."""
    problems = print_problems(directory)
    assert not problems, f"{directory.name}: " + "; ".join(problems)
```

- [ ] **Step 5: Add the fabric-facing vacuity precondition**

Extend `test_the_section_one_tree_is_populated` (line 179) with the direction
the existing preconditions do not cover — an empty *fabric-facing* set rather
than an empty *directory* set:

```python
    for directory in split_examples(EXAMPLES_ROOT):
        assert modules_in(directory), f"{directory.name} contains no Python module"
        assert fabric_facing(directory), (
            f"{directory.name} has no module importing `ccf` — the printing"
            " properties would pass over an empty set"
        )
```

- [ ] **Step 6: Run the whole module and confirm green on both examples**

Run: `.venv/bin/python -m pytest tests/examples/test_spine_separation.py -v`

Expected: PASS, all tests, both `s1-00` and `s1-01`. This is the point at which
gate 1's 16 failures reach zero.

- [ ] **Step 7: Confirm no example file was touched**

Run: `git status --short examples/`

Expected: empty output.

- [ ] **Step 8: Commit**

```bash
git add tests/examples/test_spine_separation.py
git commit -m "test(examples): P5/P6 over fabric-facing modules, with a two-sided scope control

The spine is silent and exactly one fabric-facing module prints, discovered
rather than named. `scenario/provision.py` prints and imports no `ccf`, so the
scope predicate excludes it on the principle the gate already claims; the
control asserts both directions against that one file.

Gate 1's 16 failures are closed with no example modified.

Refs docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md §3, §5.1"
```

---

### Task 3: Gate 2 — the premise detector

**Files:**
- Modify: `tests/products/test_gate_two_call_shape.py` (constants near line
  380; new functions after `_shares_a_source` at line 1148)

**Interfaces:**
- Consumes, unchanged: `_scope_nodes`, `_callee`, `_keyword`, `_path`,
  `_resolve_at`, `_at`, `_bindings`, `_plan_sources`, `_shares_a_source`,
  `LINEAGE_CONSTRUCTOR`, `LINEAGE_DECLARED_KEYWORD`, `REPO_ROOT`.
- Produces, consumed by Tasks 4 and 5:
  - `REQUIREMENTS_CLASS_ID: str`
  - `_deployment_root(path: pathlib.Path) -> pathlib.Path | None`
  - `_registers_requirements(root: pathlib.Path | None) -> bool`
  - `_class_claim(scope, bindings) -> tuple[str, ...] | None`
  - `_one_document(scope, path, bindings, plan_classes=None) -> bool`

- [ ] **Step 1: Write the failing controls for the detector itself**

Add near the other structural tests:

```python
def test_the_premise_detector_reads_the_shipped_tree_correctly() -> None:
    """Row B is pinned to its cause, not to HW-1 happening to pass.

    Every projecting deployment registers `ccf.projection-requirements` except
    HW-1, which authors one operator-set document and says so in its own
    module docstring. Asserting the detector's answer on the real tree is what
    stops the exemption drifting to mean something else later.
    """
    roots = {
        _deployment_root(path)
        for path, _ in _projecting_scopes()
    }
    roots.discard(None)
    exempt = sorted(
        str(root.relative_to(REPO_ROOT))
        for root in roots
        if not _registers_requirements(root)
    )
    assert exempt == ["examples/s1-00-companies-over-revenue"], exempt


def test_a_body_with_no_artifact_tree_is_subject_to_the_demand() -> None:
    """Fail-closed, and it keeps an existing control armed.

    `test_the_binder_tripwire_detects_a_projection_that_skips_it` synthesizes
    its violating body in `tmp_path`, which registers nothing. A default of
    *exempt* would silence that control on the day the conditioning lands,
    while it still reported green. Independently of the controls, a tree with
    no Control Plane must not buy an exemption by having nothing registered.
    """
    assert _deployment_root(REPO_ROOT / "nowhere" / "run.py") is None
    assert not _registers_requirements(None)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/products/test_gate_two_call_shape.py -k "premise_detector or no_artifact_tree" -v`

Expected: FAIL with `NameError: name '_deployment_root' is not defined`.

- [ ] **Step 3: Add the constant**

After `BINDER_PLAN_KEYWORD` (line 390):

```python
#: The Control Plane class the binder's second operand comes from. Its
#: registration is the premise the binder demand rests on: design E2 compares
#: the product class's claim against the projection's OWN document, and a
#: deployment that authors one document has no second operand for the
#: comparison. Read from any manifest in the deployment's artifact tree —
#: `examples/04-cross-process` declares it in `producer-manifest.yaml`, so a
#: fixed filename would answer wrongly there (D-IMPL-137).
REQUIREMENTS_CLASS_ID = "ccf.projection-requirements"

#: How that registration is spelled in a manifest. The `class_id:` line is the
#: Control Plane registration proper; the artifact file's own `$schema` comment
#: names the same string and is deliberately NOT the signal, because a file
#: present but unregistered is not in force.
REQUIREMENTS_REGISTRATION_RE = re.compile(
    r"^[ \t]*class_id:[ \t]*ccf\.projection-requirements[ \t]*$", re.MULTILINE
)

#: Deployments claiming the one-document exemption. **No headroom, on purpose**
#: — the module's floors stop coverage shrinking silently and this stops the
#: exemption spreading silently, which is the same instrument inverted. A
#: second deployment claiming it cannot arrive without an edit here.
MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1
```

Add `import re` to the imports (line 352 area) if absent.

- [ ] **Step 4: Implement the detector**

Add after `_shares_a_source` (line 1148):

```python
# --- the premise: does this deployment have two documents? --------------------


def _deployment_root(path: pathlib.Path) -> pathlib.Path | None:
    """The nearest ancestor of ``path`` under ``examples/`` holding artifacts.

    Returns ``None`` for a body with no artifact tree — a synthesized fixture
    under ``tmp_path``, or a tree outside ``examples/``. That answer is
    load-bearing: see :func:`_one_document` for why it is fail-closed.
    """
    examples = REPO_ROOT / "examples"
    for candidate in (path.parent, *path.parents):
        if not candidate.is_relative_to(examples):
            return None
        if (candidate / "artifacts").is_dir():
            return candidate
    return None


def _registers_requirements(root: pathlib.Path | None) -> bool:
    """Whether this deployment registers a ``ccf.projection-requirements``.

    Any YAML in the artifact tree, because the manifest's filename varies —
    ``examples/04-cross-process`` declares it in ``producer-manifest.yaml``.
    """
    if root is None:
        return False
    return any(
        REQUIREMENTS_REGISTRATION_RE.search(document.read_text(encoding="utf-8"))
        for document in (root / "artifacts").rglob("*.yaml")
    )


def _class_claim(
    scope: ast.AST, bindings: dict[str, tuple[_Binding, ...]]
) -> tuple[str, ...] | None:
    """Where this body's product-class operator claim reads.

    Row A reads it from the binder's own ``declared=``. Rows B and C have no
    binder call, so it comes from ``ProductLineage(operators_invoked=…)`` —
    already this module's anchor for the product's side of Gate 2.

    ``None`` where no lineage is assembled: the two replay environments'
    ``resolve_plan`` methods construct a plan and return it. Those bodies are
    subject to the demand (:func:`_one_document`), and both sit in
    two-document deployments, so nothing about them moves.
    """
    for node in _scope_nodes(scope):
        if not (isinstance(node, ast.Call) and _callee(node) == LINEAGE_CONSTRUCTOR):
            continue
        argument = _keyword(node, LINEAGE_DECLARED_KEYWORD)
        if argument is not None:
            return _resolve_at(_path(argument), _at(argument), bindings)
    return None


def _one_document(
    scope: ast.AST,
    path: pathlib.Path,
    bindings: dict[str, tuple[_Binding, ...]],
    plan_classes: frozenset[str] | None = None,
) -> bool:
    """Whether the binder demand's premise is false for this body (D-IMPL-137).

    **A conjunction of two independent readings, and every other combination is
    refused.** The artifact tree says whether a second document is registered;
    the AST says whether the code actually reads one source. Row C — no
    registration, and a ``required=`` reading somewhere unrelated — means a
    second operator set was authored somewhere the Control Plane does not know
    about, and it stays red because this returns ``False`` and the demand
    applies unchanged.

    Fail-closed in three places, each deliberate: no artifact tree, no readable
    class claim, and no readable plan source. An absence of evidence is not the
    exemption; the exemption is claimable only by a deployment that HAS
    artifacts and demonstrably lacks that one.
    """
    root = _deployment_root(path)
    if root is None or _registers_requirements(root):
        return False
    claim = _class_claim(scope, bindings)
    if claim is None:
        return False
    sources = list(_plan_sources(scope, bindings, plan_classes).values())
    if not sources or any(source is None for source in sources):
        return False
    return all(_shares_a_source(claim, source) for source in sources)
```

- [ ] **Step 5: Run the detector controls**

Run: `.venv/bin/python -m pytest tests/products/test_gate_two_call_shape.py -k "premise_detector or no_artifact_tree" -v`

Expected: PASS. The two binder failures on `s1-00` are still present — Task 4
consumes the detector.

- [ ] **Step 6: Commit**

```bash
git add tests/products/test_gate_two_call_shape.py
git commit -m "test(products): read the binder demand's premise from the Control Plane

The demand rests on two independently authored operator-set documents. Whether
a deployment HAS the second one is a fact about its artifacts, and this reads it
there — any manifest in the tree, since 04-cross-process names its
producer-manifest.yaml. Fail-closed with no artifact tree, so the synthesized
controls stay armed.

Detector only; nothing consumes it yet.

Refs docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md §4.2, §4.4"
```

---

### Task 4: Gate 2 — conditioning the demand, and the ceiling

**Files:**
- Modify: `tests/products/test_gate_two_call_shape.py` (`_binder_collapses`
  lines 1841–1924; the coverage test at 1982–2014; `MINIMUM_PROJECTING_BODIES`
  at 446–447)

**Interfaces:**
- Consumes from Task 3: `_one_document`, `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS`,
  `_deployment_root`, `_registers_requirements`.
- Produces: `_one_document_deployments() -> list[str]`.

**Correction carried from the spec's second planning correction:** properties
**(2) and (3)** are conditioned together. Property (2) is
`any(call.handed == execution.plan … for call in calls)`; with zero binder calls
`any([])` is `False`, so it fires on every execution and is HW-1's second
current failure. Property (1) stays unconditional.

- [ ] **Step 1: Condition properties (2) and (3) in `_binder_collapses`**

Insert immediately after `problems: list[str] = []` (line 1846):

```python
    # D-IMPL-137: properties (2) and (3) ask whether the binder was called on
    # the right object at the right time. Where the deployment authors ONE
    # operator-set document there is no second operand for the binder to
    # compare, so there is no call for them to ask about — and property (2),
    # spelled as `any(... for call in calls)`, would otherwise fire on every
    # execution merely because `calls` is empty. Property (1) stays
    # unconditional: a body that calls the binder anyway is still refused for
    # the tautology, which is what makes this an absence of demand rather than
    # a licence.
    demanded = not _one_document(scope, path, bindings, plan_classes)
```

Wrap block (3) (lines 1868–1885) and block (2) (lines 1887–1922) in
`if demanded:`. Leave block (1) (lines 1848–1866) at its current indentation.

- [ ] **Step 2: Condition the coverage assertion**

In `test_every_projecting_example_body_names_the_binder` (line 1982), insert
before the assertion:

```python
    if _one_document(scope, path, _bindings(scope)):
        # D-IMPL-137, row B. The deployment registers no
        # `ccf.projection-requirements` AND its plan's `required=` reads the
        # product class's own claim, so the binder would compare a value
        # against itself — the shape `_binder_collapses` property (1) refuses.
        # The exemption is bounded by
        # `test_the_one_document_exemption_has_not_spread`, not by this early
        # return, and row C is refused by this assertion because
        # `_one_document` returns False for it.
        return
```

- [ ] **Step 3: Add the ceiling and its test**

Add beside the other floor tests:

```python
def _one_document_deployments() -> list[str]:
    """Every deployment claiming the D-IMPL-137 exemption, by root."""
    claimed: set[str] = set()
    for path, scope in _projecting_scopes():
        if _one_document(scope, path, _bindings(scope)):
            root = _deployment_root(path)
            if root is not None:
                claimed.add(str(root.relative_to(REPO_ROOT)))
    return sorted(claimed)


def test_the_one_document_exemption_has_not_spread() -> None:
    """The ceiling, which is the module's floor discipline inverted.

    A floor stops coverage shrinking silently. Nothing stopped the *exemption*
    spreading silently, and an exemption that spreads quietly is how a
    conditioned demand becomes no demand. `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS`
    has no headroom for the same reason the floors have none.
    """
    claimed = _one_document_deployments()
    assert len(claimed) <= MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS, (
        f"{len(claimed)} deployments claim the D-IMPL-137 one-document"
        f" exemption, {MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS} permitted."
        f" {FLOOR_REMOVAL_INSTRUCTION} Claimed: {claimed}"
    )
```

- [ ] **Step 4: Re-measure `MINIMUM_PROJECTING_BODIES` and fix its comment**

Run: `.venv/bin/python -m pytest tests/products/test_gate_two_call_shape.py -k every_projecting_example_body_names_the_binder --collect-only -q`

The collected count is the number of projecting bodies, and the ids name each
one. Set the constant to that count and replace its comment (lines 445–447) with
what the number is actually made of, read from those ids. The current comment —
*"Nine bodies that construct a plan and execute it, plus the two replay
environments' `resolve_plan` methods"* — is stale.

- [ ] **Step 5: Run the module**

Run: `.venv/bin/python -m pytest tests/products/test_gate_two_call_shape.py -v`

Expected: PASS, all tests, including both `s1-00` bodies. This is the point at
which gate 2's 2 failures reach zero.

- [ ] **Step 6: Confirm the conditioning did not silence an existing control**

Run: `.venv/bin/python -m pytest tests/products/test_gate_two_call_shape.py -k "detects_a_projection_that_skips_it or reject_a_binder_that_cannot_fail" -v`

Expected: PASS. These are the controls §4.4's fail-closed default exists to keep
armed. If either now passes for the wrong reason, `_deployment_root` is
returning a root for a `tmp_path` fixture — fix that, not the control.

- [ ] **Step 7: Commit**

```bash
git add tests/products/test_gate_two_call_shape.py
git commit -m "test(products): condition the binder demand on its own premise (D-IMPL-137)

A deployment authoring one operator-set document has no second operand for
`refuse_operator_set_divergence` to compare, and the gate had no compliant state
for it: demanding the call, then refusing it by property (1) as a tautology.

Properties (2) and (3) are conditioned together — (2) is `any(... for call in
calls)` and fires on every execution when `calls` is empty. Property (1) stays
unconditional, so a body that calls the binder anyway is still refused.

Ceilinged at one exempt deployment, with the existing floor-removal discipline.

Gate 2's 2 failures are closed with no example modified.

Refs docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md §4.3, §4.5"
```

---

### Task 5: Gate 2 — the row-B and row-C controls

**Files:**
- Modify: `tests/products/test_gate_two_call_shape.py`

**Interfaces:**
- Consumes from Tasks 3 and 4: `_one_document`, `_binder_collapses`,
  `_deployment_root`, `_registers_requirements`.

The row-C control mutates a copy of HW-1 rather than synthesizing a fixture, for
the reason `_copied_example` exists in gate 1: a synthetic body proves the
predicate can refuse something; a mutated real one proves it refuses the shape
an author would actually write.

- [ ] **Step 1: Write the row-C control**

```python
def test_a_second_operator_set_outside_the_control_plane_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """Row C — the shape the exemption must never admit (D-IMPL-137).

    The exemption is not "no artifact, no demand". It is earned by a positive
    reading: the deployment registers no `ccf.projection-requirements` AND its
    code demonstrably reads one source. A deployment that registers nothing
    while its plan's `required=` reads somewhere unrelated has authored a
    second operator set the Control Plane does not know about — the two
    readings disagree, and that disagreement is the finding.

    Mutated from the shipped HW-1 rather than synthesized, so what is refused
    is the edit an author would actually make.
    """
    source = REPO_ROOT / "examples" / "s1-00-companies-over-revenue"
    destination = tmp_path / source.name
    shutil.copytree(source, destination)
    assert not _registers_requirements(destination), "HW-1 registers none"

    produce = destination / "produce.py"
    text = produce.read_text(encoding="utf-8")
    mutated = text.replace(
        "required=tuple(scenario.product_class.required_operator_keys),",
        "required=tuple(scenario.operator_parameters),",
        1,
    )
    assert mutated != text, "the plan construction moved; update this control"
    produce.write_text(mutated, "utf-8")

    tree = _parse(produce)
    assert tree is not None
    problems: list[str] = []
    for scope in _scopes(tree):
        problems.extend(_binder_collapses(scope, produce))
    assert any("with no `refuse_operator_set_divergence`" in p for p in problems), (
        problems
    )
```

Add `import shutil` to the imports if absent.

- [ ] **Step 2: Write the row-B control**

```python
def test_hw1_claims_the_exemption_for_the_stated_reason() -> None:
    """Row B, pinned to its cause rather than to HW-1 happening to pass.

    Both halves asserted separately, because either alone would keep passing if
    the other silently changed: the deployment registers no requirements
    artifact, and the body's plan reads the product class's own claim.
    """
    produce = (
        REPO_ROOT / "examples" / "s1-00-companies-over-revenue" / "produce.py"
    )
    root = _deployment_root(produce)
    assert root is not None and not _registers_requirements(root)

    tree = _parse(produce)
    assert tree is not None
    exempt = [
        scope
        for scope in _scopes(tree)
        if _one_document(scope, produce, _bindings(scope))
    ]
    assert exempt, "HW-1's projecting body no longer reads one document"
```

- [ ] **Step 3: Write the ceiling control**

```python
def test_the_exemption_ceiling_refuses_a_second_claimant() -> None:
    """The ceiling fires at two, watched rather than assumed.

    A constant nothing has been seen to trip is a constant nobody has tested.
    Exercised through `_exemption_problems`, the same predicate
    `test_the_one_document_exemption_has_not_spread` judges the tree by, against
    a synthesized second claimant — standing a real one up on disk would mean
    shipping it.
    """
    assert not _exemption_problems(["examples/s1-00-companies-over-revenue"])
    problems = _exemption_problems(
        ["examples/s1-00-companies-over-revenue", "examples/s1-02-invented"]
    )
    assert problems and "s1-02-invented" in problems[0], problems
```

This requires Task 4 Step 3 to expose the comparison as a predicate rather than
inline it in the assertion. Task 4's `test_the_one_document_exemption_has_not_spread`
therefore reads:

```python
def _exemption_problems(claimed: list[str]) -> list[str]:
    """Whether this set of claimants exceeds the ceiling.

    A predicate rather than an inline comparison, so the ceiling test and its
    control judge by the same code — the same reason `spine_problems` and
    `_binder_collapses` are predicates.
    """
    if len(claimed) <= MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS:
        return []
    return [
        f"{len(claimed)} deployments claim the D-IMPL-137 one-document"
        f" exemption, {MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS} permitted."
        f" {FLOOR_REMOVAL_INSTRUCTION} Claimed: {claimed}"
    ]


def test_the_one_document_exemption_has_not_spread() -> None:
    """The ceiling, which is the module's floor discipline inverted.

    A floor stops coverage shrinking silently. Nothing stopped the *exemption*
    spreading silently, and an exemption that spreads quietly is how a
    conditioned demand becomes no demand. `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS`
    has no headroom for the same reason the floors have none.
    """
    problems = _exemption_problems(_one_document_deployments())
    assert not problems, "; ".join(problems)
```

- [ ] **Step 4: Run the three controls**

Run: `.venv/bin/python -m pytest tests/products/test_gate_two_call_shape.py -k "second_operator_set or hw1_claims or ceiling_refuses" -v`

Expected: PASS, all three.

- [ ] **Step 5: Verify the row-C control actually fires for the right reason**

Temporarily change the row-C control's replacement string to a no-op edit and
confirm the test FAILS (the assertion that `mutated != text` catches it), then
restore. This confirms the control is not passing on a copy it never mutated.

- [ ] **Step 6: Commit**

```bash
git add tests/products/test_gate_two_call_shape.py
git commit -m "test(products): controls for rows B and C, and for the exemption ceiling

Row C is mutated from the shipped HW-1 rather than synthesized: a deployment
registering no requirements artifact while its plan reads an unrelated source
has a second operator set outside the Control Plane, and the two readings
disagreeing is the finding. Row B pins the exemption to its cause; the ceiling
is watched to fire.

Refs docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md §5.2"
```

---

### Task 6: Record D-IMPL-137 and verify the phase

**Files:**
- Modify: `docs/DECISIONS.md` (insert after the `D-IMPL-136` paragraph, line
  414, before the `D-GATE-15.6` entry)

- [ ] **Step 1: Write the decision entry**

`docs/DECISIONS.md` entries are single bold-led paragraphs, blank-line
separated, not `###` headers. Match that form exactly:

```markdown
**D-IMPL-137 — The `refuse_operator_set_divergence` demand is conditioned on the registration of the second document; a one-document deployment is a legitimate shape. `D-IMPL-86` is narrowed, not revoked.** RESOLVED. Date: 2026-08-14. Approver: Dave. **Origin.** HW-1 (`examples/s1-00-companies-over-revenue`) authors ONE operator-set document — its plan's `required=` reads the product class's own `required_operator_keys` — and `tests/products/test_gate_two_call_shape.py` had **no compliant state for it**: the coverage assertion demanded the binder call, and had HW-1 made it, `_binder_collapses` property (1) would have refused the same call as a tautology, because `declared=scenario.product_class` is a prefix of the plan's source path. The only exit property (1)'s own message names — *"Build the plan's `required=` from the projection's OWN document"* — is not a code edit but **authoring a second artifact**. The demand was therefore not *call the binder*; it was *adopt the two-document design*, which is a design mandate wearing a call-site check's clothing and is the rigidity `D-IMPL-132` forbade for operators. **Ruled: the demand fires only where its premise holds.** The premise is that two independently authored operator-set documents exist, which is a fact about the **Control Plane** and is read there — any manifest in the deployment's artifact tree declaring `class_id: ccf.projection-requirements` (any manifest, because `examples/04-cross-process` declares it in `producer-manifest.yaml`). Measured across the tree: every deployment with a projecting body registers it **except HW-1**. **The detector is a conjunction of two independent readings, and every other combination is refused.** Registration absent AND the plan's `required=` sharing a source with the class claim ⇒ **one document, demand does not fire**. Registration present AND sharing ⇒ refused by property (1), unchanged. Registration absent AND **not** sharing ⇒ **refused** — a second operator set was authored somewhere the Control Plane does not know about, and the two readings disagreeing is itself the finding. **The exemption is fail-closed in three places**: no artifact tree, no readable class claim, and no readable plan source all mean the demand applies. That is not only a convenience — it keeps `test_the_binder_tripwire_detects_a_projection_that_skips_it` armed, whose fixture is synthesized under `tmp_path` and registers nothing, and it refuses a tree the exemption by having no Control Plane at all. **Where the class claim is read in a body that never calls the binder**: `ProductLineage(operators_invoked=…)`, already the module's anchor for the product's side of Gate 2; a body assembling no lineage — the two replay environments' `resolve_plan` methods — is subject to the demand, and both sit in two-document deployments so nothing about them moves. **Properties (2) and (3) are conditioned together, property (1) is not.** Property (2) is spelled `any(call.handed == execution.plan … for call in calls)` and with zero binder calls `any([])` is `False`, so leaving it unconditional would fire on every execution; property (1) staying unconditional is what makes this an absence of demand rather than a licence, since a one-document body that calls the binder anyway is still refused for the tautology. **The exemption is ceilinged at one** (`MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS`), no headroom, carrying the module's existing `FLOOR_REMOVAL_INSTRUCTION`: the floors stop coverage shrinking silently and this stops the exemption spreading silently, which is the same instrument inverted. **What this does NOT do.** It does not narrow the authorship residual `R-3`, which `D-IMPL-86` establishes as AST-undetectable in principle and which remains open and recorded in `src/ccf/deployment/binder.py`'s module docstring. It does not touch Gate 2 proper: the L6 comparison of `lineage.operators_invoked` against `engine_resolved` still does real work in a one-document deployment, because those two sides are the declaration and the engine's resolution — two sources whatever the upstream document count is, and HW-1 is green on that tripwire today. **Governs:** `tests/products/test_gate_two_call_shape.py`. **Narrows** `D-IMPL-86` (and its correction of 2026-08-05); neither is revoked. **Consistent with** `D-IMPL-132`. Originates: the brainstorming session of 2026-08-14, full design at `docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md` §4.
```

- [ ] **Step 2: Verify the entry landed in the right place**

Run: `command grep -n "D-IMPL-136\|D-IMPL-137\|D-GATE-15.6" docs/DECISIONS.md`

Expected: line numbers ascending in that order, with `D-IMPL-137` between the
other two.

- [ ] **Step 3: Run both gates and the phase's core suite**

Run: `.venv/bin/python -m pytest tests/examples/test_spine_separation.py tests/products/test_gate_two_call_shape.py -q`

Expected: PASS, zero failures.

Run: `make ci-core`

Expected: PASS. The four `tools/` failures accepted as `DI-15.6-01(a)` residuals
are the only permitted red; if anything else fails, it is this change's problem.

- [ ] **Step 4: Confirm the whole change is test-and-docs only**

Run: `git diff --stat main...HEAD -- src/ runtime/ examples/`

Expected: empty output.

- [ ] **Step 5: Commit**

```bash
git add docs/DECISIONS.md
git commit -m "docs(decisions): record D-IMPL-137 — the binder demand is conditioned on its premise

A one-document deployment is a legitimate shape. The demand fires only where
two independently authored operator-set documents are registered, detected as a
conjunction of the Control Plane and the AST, fail-closed on absence and
ceilinged at one exempt deployment. Narrows D-IMPL-86; R-3 stays open; Gate 2
proper is untouched.

Refs docs/superpowers/specs/2026-08-14-property-not-shape-gating-design.md"
```

---

## Verification

The phase is done when all four hold:

1. `.venv/bin/python -m pytest tests/examples/test_spine_separation.py tests/products/test_gate_two_call_shape.py -q` — zero failures (was 18).
2. `git status --short examples/` — empty. No example was modified.
3. `git diff --stat 8169b56..HEAD -- src/ runtime/ examples/` — empty. **Scoped to
   this plan's base, not `main...HEAD`:** `phase-16` already carries HW-1 and
   plans 16-22/23/24, which legitimately changed `src/` and `examples/`, so a
   branch-wide diff answers a different question and never comes back empty.
4. `make ci-core` — green but for the four accepted `tools/` residuals.
