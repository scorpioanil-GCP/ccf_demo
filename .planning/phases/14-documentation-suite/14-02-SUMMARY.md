---
phase: 14-documentation-suite
plan: 02
subsystem: publish-safety
tags: [d-02, d-20, lint, docs, security]
requires: []
provides:
  - tools/publish_scan.py (the D-02 never-publish gate)
  - tools/publish_scan_tests/ (gate unit tests + standing docstring regression gate)
affects:
  - src/ccf/halflife/debt.py
  - src/ccf/halflife/decay.py
  - src/ccf/peering/__init__.py
  - src/ccf/projection/__init__.py
  - src/ccf/controlplane/artifacts.py
  - src/ccf/operators/planner.py
  - src/ccf/operators/categories.py
  - runtime/ccf_runtime/cdc/adapter.py
tech-stack:
  added: []
  patterns:
    - "publish scan styled as a fourth CCF invariant lint (tools/lints analog)"
    - "shingle intersection against the whitepaper, N=10, no allowlist"
    - "boundary-anchored denylist token matching (matches_module discipline)"
key-files:
  created:
    - tools/publish_scan.py
    - tools/publish_scan_tests/__init__.py
    - tools/publish_scan_tests/test_publish_scan.py
    - tools/publish_scan_tests/test_docstring_leaks.py
  modified:
    - src/ccf/halflife/debt.py
    - src/ccf/halflife/decay.py
    - src/ccf/peering/__init__.py
    - src/ccf/projection/__init__.py
    - src/ccf/controlplane/artifacts.py
    - src/ccf/operators/planner.py
    - src/ccf/operators/categories.py
    - runtime/ccf_runtime/cdc/adapter.py
decisions:
  - "SHINGLE_WORDS = 10, with the measured N-sensitivity sweep carried inline"
  - "No allowlist and no report-only mode on the publish scan (D-20)"
  - "Zero-finding post-build scans re-scan the whitepaper and exit 2 if the gate is dead"
metrics:
  duration: ~50m
  completed: 2026-08-03
requirements: [DOCS-02]
---

# Phase 14 Plan 02: Publish-Safety Gate and the D-20 Docstring Rework Summary

A blocking, allowlist-free publish scanner (`tools/publish_scan.py`) built as a fourth CCF
invariant lint, with paired positive/negative/self-test controls, plus the eleven
whitepaper-quoting docstrings it exposed rewritten to paraphrase-plus-citation and held there by
a standing `ast`-driven regression gate.

## What Shipped

**`tools/publish_scan.py`** — four rules, all blocking:

| Rule | Fires on |
|------|----------|
| `pub01-whitepaper-shingle` | ten consecutive normalized words of whitepaper body text in a published file |
| `pub02-internal-path` | a path naming an internal deliverable, or a `Fig-CHNN-NN` figure cited in page text |
| `pub03-symlink` | any symlink under the pre-build `public/` tree |
| `pub04-include-escape` | a snippet include whose target starts `docs/` or `.planning/` |

Normalization strips HTML tags first, then backtick code spans, then lowercases and reduces to
`[a-z0-9 ]` — so neither an element boundary nor inline markup can mask a quote. The whitepaper
shingle set is built once per process behind `whitepaper_shingles()`.

Deliberate omissions, recorded in the module docstring so they read as decisions rather than
oversights: no allowlist, no `--exit-zero`, no warn-only or report-only mode (D-20). The CLI has
exactly two options — the positional tree and `--pre-build`.

Self-test: a post-build scan that finds nothing re-scans the whitepaper itself and exits **2**
(distinct from a leak's exit 1) if that does not fire. A gate that silently stops matching after a
whitepaper reformat is worse than no gate.

**`tools/publish_scan_tests/`** — a real package beside `tools/lints/tests/`, outside `testpaths`
per the existing CI precedent. 16 tests in `test_publish_scan.py` across four banner sections:
violating cases (self-test polarity, `DESIGN.md` positive control, HTML masking, path and figure
denylist, symlink, both include-escape prefixes), clean cases (the two D-03-moved docs,
example-source includes, and the D-18/D-22 compatibility assertion that `§7.6` and `D-IMPL-71` are
identifiers rather than body text), the denylist boundary, and exit codes. Polarities and rule
tokens are asserted; no measured count is.

**`test_docstring_leaks.py`** — walks every `.py` under `src/` and `runtime/` with `ast`, feeds
every module/class/function docstring to the same shingle check, and reports file plus qualified
symbol for every hit. Verified by temporarily re-inserting one quoted sentence: the failure output
reads `src/ccf/projection/__init__.py::<module> — 2 shingle hit(s)`.

## The D-20 Rewrites

Eleven docstrings across eight modules were flagged and reworked:

| Module | Symbols |
|--------|---------|
| `src/ccf/halflife/debt.py` | `<module>` (35 hits), `DebtSignal`, `context_debt` |
| `src/ccf/halflife/decay.py` | `Observation`, `effective_half_life` |
| `src/ccf/controlplane/artifacts.py` | `<module>` |
| `src/ccf/operators/planner.py` | `<module>` |
| `src/ccf/operators/categories.py` | `PolicyFilter` |
| `src/ccf/peering/__init__.py` | `<module>` |
| `src/ccf/projection/__init__.py` | `<module>` |
| `runtime/ccf_runtime/cdc/adapter.py` | `<module>` |

Every rewrite keeps the whitepaper section citation, the invariant ID, the `D-IMPL-NN`
references and the formulas, and replaces contiguous runs of whitepaper prose with the SDK's own
account of what the code does and why the contract forces it. `debt.py` still carries
`D_c = 1 − (F · C · S)` and `INV-CH7-62`. All eight modules still contain a `§` citation.

**Discrepancy from research (recorded per the plan's instruction).** 14-RESEARCH.md predicted 13
flagged docstrings; the scanner found **11**. The scanner's answer is authoritative. The most
likely source of the gap is granularity — research counted at N=10 over a docstring extraction
that may have included nested or overlapping spans; the `ast.get_docstring` walk here counts one
entry per documented node.

**The `decay.py` inline quotation stays.** The short span
`"these values are illustrative, not empirical"` in the `decay.py` module docstring was run
through `scan_text` rather than judged by eye: the module docstring was never flagged, so the
span does not participate in any ten-word shingle. Per the plan, judgment does not overrule the
scanner in either direction — it may stay, and it does.

## Deviations from Plan

**None affecting scope.** Two mechanical notes:

1. Task 1 was executed TDD-first (a RED commit of the control tests preceded the scanner), and
   Task 2 therefore extended that file rather than creating it — the HTML-masking case from Task
   1's `<behavior>` block was the addition. Net artifacts are exactly as specified.
2. `scan_text` emits `pub01` findings ahead of `pub02` findings so that the first finding on a
   whitepaper-fed scan is the shingle hit, as Task 2's acceptance criteria require.

The worktree has no `.venv`; verification used the repo interpreter at
`/home/parkave/ccf_code/.venv/bin/python` with the same `PYTHONPATH` the Makefile sets. No
Makefile or CI wiring was added — the plan scopes those elsewhere in the phase.

## Verification

| Check | Result |
|-------|--------|
| `python tools/publish_scan.py --pre-build` | exit 0 |
| `pytest tools/publish_scan_tests -q` | 17 passed |
| `python -m tools.lints --all` (`make lint`) | exit 0 |
| `python -m mypy` (`make typecheck`) | Success, 161 source files |
| `CCF_REQUIRE_HARNESSES=1 pytest -q` (`make test`) | 1533 passed, 2 skipped |
| `docs/DESIGN.md` positive control | >20 `pub01` findings |
| `docs/security-notes.md`, `docs/demo-walkthrough.md` | 0 `pub01` findings |
| `grep -E 'D-20|publish_scan' tools/lints/allowlist.yaml` | no matches — no exception added |
| `git diff -U0 -- src runtime` | docstring text only; no executable line changed |

Docstring text is not a string constant CINV-01a scores, confirmed empirically by `make lint`
passing after the rewrite rather than by assertion.

## Threat Flags

None. All seven `mitigate` dispositions in the plan's threat register (T-14-08 through T-14-14)
are realized: the docstring leak is closed and gated (T-14-08), the symlink and include-escape
pre-build guards exist with tmp-tree tests (T-14-09/10), `SHINGLE_WORDS = 10` carries its
control-failure justification inline (T-14-11), the self-test exit-2 path is in place and
asserted (T-14-12), no softening flag exists in the CLI (T-14-13), and per-file citation presence
was verified across all eight touched modules (T-14-14).

## Self-Check: PASSED

- `tools/publish_scan.py` — FOUND
- `tools/publish_scan_tests/__init__.py` — FOUND
- `tools/publish_scan_tests/test_publish_scan.py` — FOUND
- `tools/publish_scan_tests/test_docstring_leaks.py` — FOUND
- Commits `4006a2a`, `2193e7c`, `ecbd78b`, `8e0ce16`, `bf70c78` — all present in `git log`
