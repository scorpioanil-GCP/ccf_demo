# ERGO-03 — the Phase 15 surface-audit measurement, frozen

**Status:** historical record. The running check is retired.
**Ruling:** `docs/DECISIONS.md` **`D-IMPL-94`**, recording Phase 16 **`D-15`**
(Dave, 2026-08-10).
**Measured:** 2026-08-10, at tree SHA **`e7e1729`** on branch `phase-16`.
**Requirement:** ERGO-03, **Complete** (Phase 15). This document is that
requirement's shipped evidence.

## Why this document exists

ERGO-03 reads:

> The criterion-1 surface audit is an executable check recording per-example
> mechanical line counts before and after, reporting relocation and removal as
> separate figures.

The executable half was `tests/examples/test_surface_audit.py`. It compared the
live `examples/` tree against `docs/surface/examples/before/` — a baseline
written once, at Phase 15's *start*, and never regenerated. `tools/measure_examples.py`
says in its own module docstring why that baseline is immutable: rewriting it
mid-phase "destroys the comparison the audit reports", leaving the audit
comparing the rewritten tree to itself.

Phase 16 retires `examples/00`–`08` and `examples/external/00-hello-context`
and rebuilds the suite greenfield (`DOCS-17`). From the first new example
directory onward the before/after comparison is not merely stale — it is
**meaningless**, because the "after" side is no longer a rewrite of the "before"
side. It is a different tree.

`D-IMPL-94` therefore rules the *running test* retired rather than
**re-baselined** (which would destroy the Phase 15 comparison this requirement's
evidence rests on) or **deleted** (which would erase a Complete requirement's
evidence). The measurement is frozen here first; the test is retired in the same
commit.

## The measurement

Everything under this heading is **scripted output**, produced by running the
shipped report function `audit_report()` over the committed fragment
directories, before any Phase 16 example change and before the test module was
removed. `tools/measure_examples.py --check` exited **0** immediately before the
run, so every `after/` fragment matched a live re-measurement at the moment of
freezing.

Per **P-8**, the scope of the claim is stated rather than assumed: the `mech`,
`reloc` and four-total figures below are read from the committed fragments and
from `audit_report()`; the `raw` columns are read from the same fragments. The
prose either side of the block is *not* scripted and is marked as narration
where it makes a claim.

```text
baseline fragments: 24
re-measured fragments: 24

| File | mech before | mech after | reloc before | reloc after | raw before | raw after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `examples/00-quickstart/run.py` | 143 | 13 | 40 | 0 | 451 | 398 |
| `examples/01-agent-basics/run.py` | 159 | 14 | 85 | 0 | 619 | 531 |
| `examples/02-skilling/run.py` | 118 | 13 | 68 | 0 | 571 | 609 |
| `examples/03-harness-portability/legs/__init__.py` | 0 | 0 | 0 | 0 | 1 | 1 |
| `examples/03-harness-portability/legs/deterministic.py` | 0 | 0 | 11 | 11 | 507 | 527 |
| `examples/03-harness-portability/legs/live.py` | 0 | 0 | 23 | 23 | 641 | 641 |
| `examples/03-harness-portability/legs/ollama_client.py` | 0 | 0 | 0 | 0 | 147 | 147 |
| `examples/03-harness-portability/run.py` | 145 | 13 | 98 | 54 | 720 | 711 |
| `examples/04-cross-process/producer_child.py` | 143 | 13 | 14 | 1 | 630 | 597 |
| `examples/04-cross-process/run.py` | 53 | 13 | 68 | 1 | 533 | 521 |
| `examples/05-workflow-hitl/run.py` | 28 | 4 | 112 | 0 | 858 | 875 |
| `examples/06-decision-replay/run.py` | 175 | 12 | 130 | 0 | 1320 | 1179 |
| `examples/07-artifact-store-mcp/mcp_store_child.py` | 0 | 0 | 1 | 1 | 135 | 135 |
| `examples/07-artifact-store-mcp/run.py` | 132 | 13 | 27 | 1 | 587 | 636 |
| `examples/08-e2e-demo/generator.py` | 0 | 0 | 0 | 0 | 431 | 431 |
| `examples/08-e2e-demo/run.py` | 161 | 13 | 6 | 6 | 1141 | 1164 |
| `examples/external/00-hello-context/client_adk.py` | 0 | 0 | 1 | 1 | 75 | 75 |
| `examples/external/00-hello-context/client_anthropic.py` | 0 | 0 | 2 | 2 | 97 | 97 |
| `examples/external/00-hello-context/client_bare.py` | 0 | 0 | 5 | 5 | 77 | 77 |
| `examples/external/00-hello-context/fixtures/capture_proxy.py` | 0 | 0 | 7 | 7 | 415 | 415 |
| `examples/external/00-hello-context/fixtures/diff_fixtures.py` | 0 | 0 | 7 | 7 | 93 | 93 |
| `examples/external/00-hello-context/replay_server.py` | 0 | 0 | 9 | 9 | 400 | 400 |
| `examples/external/00-hello-context/run.py` | 36 | 0 | 22 | 22 | 766 | 790 |
| `examples/external/00-hello-context/serve.py` | 132 | 13 | 1 | 1 | 773 | 743 |
| **Tree total** | **1425** | **134** | **737** | **152** | **11988** | **11793** |

four separate figures, as audit_report() returns them:
{
  "mechanical_after": 134,
  "mechanical_before": 1425,
  "relocated_after": 152,
  "relocated_before": 737
}

rewritten files carrying an after/ fragment: 24
mechanical wiring removed: 1291 lines (1425 -> 134)
assertions and prints relocated: 585 lines (737 -> 152)
the two figures above are reported side by side and are never summed (D-12).
```

## Removal and relocation are two figures, never one

This is the shape ERGO-03's own wording requires — *"reporting relocation and
removal as separate figures"* — and Phase 15 `D-12` names the reason: a single
combined "lines saved" headline would let a target be hit by *moving* lines
rather than by *removing work*.

- **Mechanical wiring removed: 1291 lines** (1425 → 134, a 90.6% reduction).
  This is wiring the SDK absorbed. It is gone.
- **Assertions and prints relocated: 585 lines** (737 → 152). This work still
  exists; it moved into `tests/` under Phase 15 `D-09`.

These two numbers are reported side by side and are **not** added together. The
retired test asserted that structurally: its report function returned four
independent totals and was incapable of returning a combined one, and a
companion assertion parsed the function's own source and failed on the forbidden
names.

The clearest case for keeping them apart is `examples/external/00-hello-context/run.py`,
whose **raw line count rose** (766 → 790) while its mechanical figure fell to
zero. A combined figure would have reported that rewrite as a regression.
`examples/05-workflow-hitl/run.py` is the same shape.

## What moved between this freeze and the last narrated figure

`docs/SURFACE-AUDIT.md` §2.2 carries the same table as re-measured on
2026-08-05, after Phase 15.1. Comparing that record with the freeze above:

- **The four headline figures are unchanged**: 1425 → 134 and 737 → 152 in both.
  Every phase since 15.1 — 15.2, 15.3, 15.4 — left the mechanical and relocatable
  surfaces exactly where Phase 15 left them.
- **The `raw` column moved**, tree-wide 11735 → **11793** (+58), concentrated in
  the drivers that Phase 15.4's `connection=` mapping and Phase 15.2/15.3's
  query-pin surface touched. Stated rather than netted away: those phases cost
  an adopter lines, and none of what they cost was the mechanical boilerplate
  Criterion 1 set out to remove. That is precisely why `D-12` forbids one
  combined number.

`docs/SURFACE-AUDIT.md` §2.1 through §2.3 remain the narrative of record for
what the figures mean, for the 134 mechanical lines that deliberately remain
(the 13-line registration cluster that *is* the abstraction line), and for the
152 relocatable lines accounted for one by one under ERGO-16.

## What is retired, and what is not

**Retired:** the running check `tests/examples/test_surface_audit.py`, deleted
in the same commit that created this document. Its assertions were: no silent
regression against an `after/` fragment; a non-vacuous, still-resolving
`before/` baseline; and the structural impossibility of a combined figure. All
three were green at the moment of the freeze.

**Not retired:**

- `tools/measure_examples.py` — the AST measurement tool, and `make measure-examples`,
  both of which still work. Nothing here retires the *ability* to measure.
- `docs/surface/examples/before/` and `docs/surface/examples/after/` — the 24+24
  committed fragments this document is derived from. They are the primary
  evidence; this document is the reading of them.
- ERGO-03 itself, which stays **Complete**. A requirement is not un-met by the
  retirement of a check whose comparison a later phase's ruling made
  meaningless.

## For a reader arriving later

If you are looking for a *current* measurement of the examples tree, this
document is not it, and no such check exists at the time of writing. The Phase
16 suite is a different tree with different examples; measuring it against these
figures would compare two unrelated things. Building a fresh baseline for the
new suite is a decision for whoever wants one — it is deliberately not made
here, because making it silently is exactly the failure `D-15` was ruled to
avoid.
