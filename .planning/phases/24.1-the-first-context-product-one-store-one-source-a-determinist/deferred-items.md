## From plan 24.1-03 (Wave 3) — out of scope, NOT fixed

- **`examples/s1-00-companies-over-revenue/backends.yaml` line 1 declares
  `$schema=../../../../docs/schemas/ccf.declared-artifact.json` — one level too
  deep.** The file sits at depth 2 under the repo root, so the correct prefix is
  `../../`. Measured: the declared path does **not** resolve; the same header at
  the correct depth does. Every `s1-01/artifacts/*.yaml` header is correct, so
  this is one file, not a convention.
  **Pre-existing at `phase-24.1-base` and unrelated to this plan's changes** —
  logged rather than fixed, per the scope boundary. It costs editor schema
  completion in that one file and nothing at runtime; no lint checks it.

---

## From plan 24.1-04 (Wave 4) — out of scope, NOT fixed

### `make ci` has been RED since Wave 3, and the subject is the `artifacts/` directory

**Found** while running `tests/examples` before committing Wave 4.

```
tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root
FAILED — covered `artifacts/` directories whose parent is not an example root
         (no `run.py` beside them): cp-00-institutional-holders/artifacts
```

**Not caused by Wave 4, and measured rather than asserted:**

| Tree state | Result |
| --- | --- |
| `examples/cp-00-institutional-holders/artifacts/` **absent** — the `phase-24.1-base` state | **29 passed** |
| **Only** Wave 3's `assembly-recipe.yaml` present — the `bd57821` state, Wave 4's six files moved aside | **1 failed**, 29 passed |
| Wave 4's three further artifacts also present | **1 failed**, 29 passed — the same single failure, not a new one |

`git log --diff-filter=A -- examples/cp-00-institutional-holders/artifacts/`
names **`313d1c0`** — Wave 3, Task 3. The gate has been red from that commit.

**What the gate requires.** `tests/examples/test_artifact_schema_headers.py::bijection_violations`
holds a two-way bijection: every directory containing `artifacts/*.yaml` must
have `tests/examples/test_artifact_schema_headers.py::EXAMPLE_ROOT_MARKER` —
literally a file named `run.py` — directly beside it, and every such root must
have an `artifacts/`. `examples/s1-01-hello-context-product` satisfies it
(`run.py` + `spine.py` + `artifacts/`). `examples/s1-00-companies-over-revenue`
is outside the gate entirely: it has no `artifacts/` — its question document
lives under `scenario/`.

**`cp-00` mixes the two shapes**: `artifacts/` from `s1-01`, and
`produce.py` / `consume.py` / `deployment.py` from `s1-00`.

**Three resolutions, none of them Wave 4's to pick**, because each reaches into
a file list Wave 4 does not own:

1. **`cp-00` gains a thin `run.py` driver**, matching `s1-01`. Cheapest against
   the gate — but `24.1-05` already assigns the driver role to `consume.py`, so
   this renames that file or adds a second driver beside it. A Wave 5 decision.
2. **The artifacts move to `scenario/`**, the `s1-00` shape. Also cheap, but
   `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml` is
   cited by path in the spec and in its own header, and the spec is Wave 3's
   committed deliverable.
3. **The marker set widens** beyond `run.py`. That edits a shipped gate, which
   `D-04` and criterion 16 both say this phase does not do.

**Recommendation, offered rather than taken:** option 1, decided by `24.1-05`
when it authors the driver — the only one that changes nothing already
committed and nothing in `src/` or `runtime/`.

**Criterion 19** requires `make ci` green **at the gate commit**, not at every
wave, so this is a phase-close blocker rather than a wave blocker. Recorded here
so it is not discovered at the gate.

### `python -m tools.lints --all` does not gate a citation whose FILE does not exist

Beside `D-42`'s recorded module-alone hole, a second limitation — **stated in
the tool's own source, so this is a bound on what green means and not a defect
report.** Measured, in both a YAML comment and a Python comment, seeded into
Wave 4's own files:

| Seeded citation | `--all` |
| --- | --- |
| `src/ccf/products/gates.py` + `::` + a fabricated symbol name — real file, symbol that does not exist | **rc=1**, named `cite03-node-id` |
| a path under `src/ccf/` that does not exist, + `::` + any symbol | **rc=0** |
| a real directory + a filename that does not exist, + `::` + any symbol | **rc=0** |

`tools/lints/citations.py::check_source` bumps an `unresolved_path` coverage
counter and continues, with the comment *"pointer, so it is unchecked rather
than a finding"* — a cited path may legitimately be an external pointer.

**Consequence a later wave must not forget:** a green `--all` proves the
SYMBOLS resolve in files that exist; it does not prove the FILE PATHS do. Wave 4
checked its own six files' paths with a separate instrument (13 `path::symbol`
citations, 12 resolving, 1 a deliberate forward reference to
`examples/cp-00-institutional-holders/deployment.py::connection` which `24.1-05`
creates). **Not proposed as SDK work** (`D-04`).

**A note on how this entry is written.** The three probes above are spelled as
descriptions rather than as literal citations. Spelling the fabricated one out
turned `--all` red on this very file — which is the rule working, and is itself
the positive control for the first row of the table.
