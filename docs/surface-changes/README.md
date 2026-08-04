# Surface-change fragments — the curated half of D-15

D-15 asks for two things that only work together: a **generated** manifest of
the SDK's public surface (`docs/surface/v0.2-surface.json`, produced by
`tools/dump_surface.py`), and a **curated** log carrying the rationale and the
migration guidance a generated diff can never supply. This directory is the
curated half.

## Why fragments rather than one file

D-15 requires the curated log be written **incrementally, as plans land** — a
log assembled retroactively at phase close is a log written from the diff,
which is exactly the thing it is supposed to add information to. But Phase 15
executes many plans in **parallel waves**, and a single `docs/SURFACE-CHANGES.md`
edited by every one of them would force those plans into serial waves for a
documentation reason.

So each plan owns one file. Nobody conflicts with anybody. Plan 15-21 assembles
the fragments into `docs/SURFACE-CHANGES.md` at phase close.

**Do not create `docs/SURFACE-CHANGES.md` in this directory or at the docs
root before 15-21.** Assembly is 15-21's job.

## Fragment naming

```
docs/surface-changes/15-NN-<slug>.md
```

`NN` is the plan number. `<slug>` is a short kebab-case description of the
plan's subject — e.g. `15-02-deployment-package.md`.

## Entry shape — seven fields

One section per change. Every section carries all seven fields:

| Field | Meaning |
| --- | --- |
| `Surface` | The single literal token that changed — see the rules below |
| `Public surface` | `true` or `false` — see "the classification field" below |
| `Change type` | Exactly one of `added`, `reshaped`, `removed`, `behavior` |
| `Before` | What the surface was |
| `After` | What the surface is now |
| `Why` | The reason the change was made — the thing a diff cannot say |
| `Migration` | What an adopter has to do, or `none` if nothing |

Example:

```markdown
## ccf.deployment.operators.build_operator_registry

- Surface: ccf.deployment.operators.build_operator_registry
- Public surface: true
- Change type: added
- Before: absent — callers assembled an OperatorRegistry by hand
- After: a two-phase builder that registers and then seals the registry
- Why: hand assembly let a half-registered registry reach L4
- Migration: replace hand assembly with the builder; the old path still works
```

## The classification field — `Public surface`

`Public surface` is a boolean, `true` or `false`, and it is the field that
makes the phase-close cross-check **satisfiable**.

The generated manifest is derived from the `__all__` of every module under
`/src` and `/runtime`, so it can only ever see **Python public-API changes**.
But D-15 requires this log to carry everything an adopter must act on, and
several of those things are not public API at all:

- the lint-scope change in **15-04**,
- `tools/measure_examples.py` and `make measure-examples` in **15-03**,
- the committed JSON Schemas in **15-12**,
- the artifact-document format changes in **15-09** and **15-13 through 15-20**.

Without this field, plan 15-21's `log → diff` assertion would demand a manifest
diff line for every one of those entries and fail at wave 14 — the most
expensive point in the phase. With it, the diff-agreement assertion is scoped
to `Public surface: true` entries and stays exact for them.

### `Surface` when `Public surface: true`

`Surface` **must carry the fully dotted, fully-qualified name** of what
changed — `ccf.deployment.operators.build_operator_registry`, not "the operator
builder" and not the bare module.

Two mechanisms depend on that string literally:

1. the standing drift gate, `tests/test_surface_drift.py`, which matches
   drifting names against fragment text;
2. plan 15-21's `tests/test_surface_completeness.py`, which matches the same
   string at **name granularity** and additionally requires the entry's
   `Change type` to agree with the **direction** of the diff.

A fragment whose `Surface` field is prose, or whose `Change type` disagrees
with what the manifest shows, fails the phase-close cross-check.

### `Surface` when `Public surface: false`

`Surface` carries the repo-relative file path, the Make target, or the artifact
class id that changed — e.g. `tools/measure_examples.py`,
`make measure-examples`, `ccf.signal-batch` (document format), or
`examples/00-quickstart/artifacts/events.yaml`.

It is still a **single literal token, never prose**, so the entry stays
greppable and the drift gate's substring match still works.

### The classification is not an escape hatch

Plan 15-21 asserts **both directions** against it:

- A public-API change misclassified `Public surface: false` fails the
  `diff → log` direction, which requires a matching entry carrying
  `Public surface: true`.
- A `Public surface: false` entry whose `Surface` string *does* appear in the
  manifest diff also fails, because the classification contradicts what the
  manifest shows.

Misclassifying in either direction is a red build, not a quiet pass.

## `Change type` — the four values

`added`, `reshaped`, `removed`, `behavior`. `Change type` must **agree with the
direction** of the phase-close diff.

The `behavior` class exists because D-02 changes `load_artifact`'s return
values without removing or reshaping a signature — something a pure signature
diff can never catch. That is precisely why D-15 requires *both* the generated
manifest and this curated log.

A `behavior` entry may be:

- **`Public surface: true`** — an exported Python name whose observable
  behavior changed, as with `load_artifact`. This is the **only
  public-surface class exempt from needing a matching diff line at phase
  close.** Every other public-surface class must correspond to a real diff
  line, and a claim with no diff line is a defect.
- **`Public surface: false`** — the thing that changed behaviorally is not a
  Python name at all and therefore can never appear in the manifest diff. A
  regenerated replay fixture is the worked case; see 15-17. These entries are
  governed by the same absent-from-diff assertion as every other `false`
  entry — **the exemption is about the *diff-matching* direction, never about
  classification.**

## The two-file naming scheme and the single-owner rule

- **`docs/surface/v0.2-surface.json` is the live manifest.** It is written by
  exactly two plans: **15-01** (phase start) and **15-21** (phase close).
- **`docs/surface/v0.2-surface-baseline.json` is the frozen phase-start copy.**
  It is written **once, by 15-01, and never again**. It is the immutable
  "before" side of the ROADMAP Success Criterion 6 diff, which 15-21 produces
  by diffing the final live manifest against it.

Every other plan leaves **both** files untouched. Instead it runs:

```bash
PYTHONPATH=src:runtime .venv/bin/python tools/dump_surface.py --report
```

`--report` writes nothing and always exits 0. It prints the fully-qualified
names added, removed, and reshaped relative to the committed manifest, so a
plan can positively assert that the names it claims to add actually appear.
The plan then writes a fragment here.

The single-owner rule is not a convenience: a whole-tree file regenerated
concurrently in eleven worktrees would pass `--check` in each of them
pre-merge and leave the tree stale after the second merge, on a file no plan
then owns.

Note that the **unqualified path is deliberately the live one**. The obvious
alternative — freeze the plain name and qualify the live one — would leave
every future contributor reaching for "the surface manifest", finding
`v0.2-surface.json`, and getting the *stale* snapshot. Qualifying the frozen
file instead means no tool and no test is ever re-pointed, and a stale read is
impossible by naming.
