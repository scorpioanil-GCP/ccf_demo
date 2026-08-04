# 15-04 — CINV-01 reaches the tests/ tree (D-IMPL-78, ERGO-16)

Both entries are `Public surface: false`. `tools/dump_surface.py` walks only
`/src` and `/runtime` modules that define `__all__`, so a module under
`tools/` can never appear in the manifest diff. Confirmed empirically:
`tools/dump_surface.py --report` reports `added (0)`, `removed (0)`,
`reshaped (0)` for this plan. The live manifest
(`docs/surface/v0.2-surface.json`) and the frozen baseline were not touched.

A lint scope change is nonetheless a real migration concern for anyone with
domain literals in `tests/`, which is why D-15 requires it in this log.

## tools/lints/__main__.py

- Surface: tools/lints/__main__.py
- Public surface: false
- Change type: reshaped
- Before: `LINTED_TREES = ("src", "runtime", "examples")` and
  `RULE_TREE_SCOPE["no-hardcoding"] = ("src", "runtime", "examples")` — the
  No-Hardcoding Rule did not reach test modules
- After: both tuples gain `"tests"`. Two edits, not one: `run()` iterates
  `LINTED_TREES` and *then* filters each rule by `RULE_TREE_SCOPE`, so a tree
  named only in the scope map is never walked and the widening would be a
  no-op. `harness-imports`, `algorithmic`, and `orchestration-imports` stay
  `("src", "runtime")` — test modules exercising the harness adapters import
  harness SDKs, and CLAUDE.md §7.3 words that invariant over core
- Why: D-IMPL-78 (Dave, 2026-08-04). D-09 relocates the example CI assertions
  into `tests/`, and those assertions carry domain expectations read from
  `expected:` artifact blocks. Without this scope the relocation would move
  domain values out of a structural invariant's reach with every CI gate still
  green — a CI-invisible weakening arrived at as a side effect of an
  ergonomics change. The hole is closed before any relocation happens
- Migration: downstream forks that add test modules with inline domain
  literals — prompt-shaped strings, numeric threshold tables, direct `Agent` /
  `Task` / `Workflow` construction — will now see CI findings under
  `tests/`. The fix is the same one `/examples` already takes: read the
  expected value from the artifact the test asserts about, and construct
  agents through the Agent Factory from fixture artifacts. The exemption
  surface for a whole tree is this config file, never an allowlist entry

## tools/lints/no_hardcoding.py

- Surface: tools/lints/no_hardcoding.py
- Public surface: false
- Change type: reshaped
- Before: `cinv01a-prompt-shape` scored every prose-shaped literal that
  survived the SQL/URI/short-string filters. Developer-facing diagnostics were
  indistinguishable from prompts to the rule, so a multi-sentence CI failure
  message naming its own fix scored as a system instruction
- After: `is_developer_diagnostic()` runs before scoring. A literal that
  carries at least one `DIAGNOSTIC_MARKERS` signal — a backticked command, a
  repo-relative filename, a `callable()` reference — and does not
  `addresses_a_reader()` (role-preamble opener, second-person pronoun, or
  template-brace density) is a diagnostic, and is not scored
- Why: Dave's ruling of 2026-08-04, recorded in `15-03-audit-baseline.md` and
  binding on this plan: resolve the two prose-diagnostic false positives by
  refining the rule, **not** by adding allowlist entries. Two allowlist entries
  today becomes friction on every future diagnostic message, and this phase's
  conventions actively encourage diagnostics that name their own fix (15-01
  ships `test_the_drift_message_names_its_own_fix` asserting exactly that).
  The distinction is mechanically detectable: a prompt is a string sent to a
  model, a diagnostic is a string shown to a developer, and the old rule
  detected "long English string literal" — a proxy for the wrong thing
- Migration: a CINV-01a finding that was previously suppressed by an allowlist
  entry on a diagnostic message can have that entry deleted; none existed in
  this repo, and none were added. A genuine prompt is unaffected — the reader
  test means it cannot escape by mentioning a filename, proven by
  `test_a_prompt_wearing_diagnostic_markers_is_still_flagged`
