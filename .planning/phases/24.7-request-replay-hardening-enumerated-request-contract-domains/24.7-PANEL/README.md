# Phase 24.7 — close-time cross-AI panel packet (CLAUDE.md §3.1)

**NOT RUN. The panel and the single-agent review follow Dave's evaluation of the build.**

This directory is a STAGED packet. No reviewer (`codex`, `cursor`, `gemini`, `/gsd-review`) was invoked in
plan 24.7-11; no `24.7-CLOSE-REVIEWS.md` exists; no credential was read. `24.7-RULINGS.md` §9, Dave: *"I also
agree with Plan 11 staging the panel packet but not running it. Let's evaluate the completed build first, then
decide whether the panel is useful. We should not recreate the 24.6 tail by automatically turning post-build
review into another self-perpetuating correction cycle."* The sequence: **build evaluation (Dave) → this panel,
if useful → the single-agent code review → verify every finding → fix blocking findings in-phase → present →
`D-GATE-24.7`.**

## Subject

The SHIPPED tree of `phase-24.7` at `ad8dc5a9e92daf055a7c0d06687cbcb055ea6716`, diff base `6a019322` (the
`D-IMPL-264` design sitting, where the branch forked from `main`). The subject is the code, not the plans — the
plans were reviewed before execution (`5e933119`, plan-checker VERIFICATION PASSED). Built by
`scratchpad/build_panel.py` (session scratchpad, not committed) on 2026-09-06; if a blocking finding is fixed
in-phase before the panel runs, REBUILD from the fixed tree so the fixes are among the subjects (the 24.6 precedent).

## Inventory (`wc -c`, bytes; every bundle is under the 131,072-byte argv cap — but see the stdin rule)

| File | Bytes | Contents |
| --- | --- | --- |
| `README.md` | (this file) | inventory, rules, credentials pointer |
| `known-findings.md` | 12,439 | K1–K8: what is already known and the ADJACENT question for each — reviewers are told NOT to re-derive them |
| `prompt.md` | 3,610 | the reviewer instruction: shipped code; `path.py::Symbol`; blocking/advisory; unresolvable citation = void |
| `bundle-src-part-1.md` | 119,165 | `git diff 6a019322..HEAD --stat -- src runtime`; the full diff; `runtime/ccf_runtime/authz/delivery_boundary.py` WHOLE |
| `bundle-src-part-2.md` | 78,488 | `src/ccf/products/constraints.py` WHOLE |
| `bundle-src-part-3.md` | 111,747 | `src/ccf/products/request.py` WHOLE; `src/ccf/products/request_schema.py` WHOLE (new) |
| `bundle-src-part-4.md` | 112,196 | `src/ccf/products/resolver.py` WHOLE |
| `bundle-src-part-5.md` | 43,922 | `src/ccf/replay/engine.py` WHOLE |
| `bundle-src-part-6.md` | 92,010 | `src/ccf/replay/record.py` WHOLE |
| `bundle-tests-part-1.md` | 110,650 | `tests/products/test_request_schema_render.py` (new) and `tests/lints/test_archived_examples_non_gating.py` (new) WHOLE; per-file diffs of 27 changed modules (`perf/suites/replay/conftest.py`, `pyproject.toml`, `tests/authz`, `tests/conformance`, `tests/conftest.py`, `tests/contracts`, `tests/crossproc/servers`, `tests/hitl`, `tests/http_api`, `tests/integration`, `tests/mcp`, `tests/perf_smoke`, `tests/products/test_delivery_determinism.py`, `test_disclosure.py`, `test_policy_constraint_resolver.py`, `test_policy_constraints.py`) |
| `bundle-tests-part-2.md` | 78,968 | per-file diffs of 14 changed modules (`tests/products/test_request_contract.py`, `test_resolver_seam.py`, `test_tolerance_exceeded.py`, `tests/replay/*` incl. `fixtures/golden_13bd250/produce.py`, `tests/test_surface_shape_capture.py`, `tests/workflow/*`, `tools/lints/tests/test_hash_transparent_key.py`) |
| `bundle-tests-part-3.md` | 109,501 | the `tests/examples` diff: 25 files, quarantine markers and `D-IMPL-265` module marks ONLY (criterion 21: 0 lines removed) |

Source is INLINED, not pointed at: `grep -c "def \|class " bundle-src-part-*.md` → 447. `grep -c "API_KEY="
24.7-PANEL/*` → 0. Every changed `src/` and `runtime/` file appears WHOLE in exactly one part (seven files:
`git diff 6a019322..HEAD --stat -- src runtime` → 7 files, +1123/−151).

**Left out, deliberately, and named:** `.planning/` (the criteria, plans, SUMMARYs, this record), `docs/`
(generated schemas, surface manifest, `SURFACE-CHANGES.md`, the six fragments, `DECISIONS.md`), `examples/`
(frozen, diff-empty), `archive/` (retired, diff-empty), `public/`. Reviewers are told these are not the subject
and any finding about them is out of scope.

## Delivery rule — STDIN ONLY

**Never pass a bundle as an argv string.** On this host a single argv string caps at 128 KB; a payload over that
dies `rc=126` with 0 bytes of output, which reads exactly like a clean, empty review (memory
`a-single-argv-string-caps-at-128kb`). The bundles are each under the cap, but the rule is stdin regardless:

```
# one call per reviewer per part; prompt + brief + bundle concatenated on stdin
cat prompt.md known-findings.md bundle-src-part-3.md | <reviewer command reading stdin>
```

Codex's sandbox (`bwrap`) can fail in a way that exits 0 having read nothing (memory
`cross-ai-panel-reliability-on-this-host`); inlining the source is what makes a silent sandbox failure unable to
empty the review — and the read-proof rule below is what makes it detectable.

## Read-proof rule — a reviewer counts only if BOTH hold

1. **The token.** Each bundle part carries a `READ-PROOF <part>: <hash>` line at its top, mid-payload and at its
   end (the hash is over the part name and its subject list; every part's token is different). The review must
   quote its part's token verbatim. A review that quotes none, or quotes another part's token, did not read its
   payload — record it as a FAILED reviewer, not as a reviewer.
2. **The citations.** Every finding cites `path.py::Symbol`. Before counting a finding, resolve the symbol against
   the tree at `ad8dc5a9`:

   ```
   git show ad8dc5a9:src/ccf/products/request.py | grep -n "def refuse_intent\|class ArgumentDomain"
   ```

   A finding whose symbol does not resolve is VOID and is recorded as a fabricated citation (24.6 saw a reviewer
   assert two lint checkers had no tests when 41 test functions existed; 15.1 rejected a reviewer outright for
   fabricated citations). A resolved citation is still not a correct finding — verify the claim separately, and
   where the panel and the tree disagree, sabotage the code to settle it (memory
   `a-resolved-citation-is-not-a-correct-finding`).

Record every reviewer run — command, rc, token quoted or not, findings kept / rejected with the line that rejects
each / carried for Dave — in `24.7-CLOSE-REVIEWS.md` (a distinct file, so the pre-execution plan review survives).

## Credentials (never in the tree)

Codex and Cursor authenticate from `/home/parkave/homecams_v2/.env` (memory `cross-ai-review-credentials`):
`CODEX_API_KEY` — `printenv CODEX_API_KEY | codex login --with-api-key` before `codex exec` (NOT
`OPENAI_API_KEY`; that project has no credit; the ChatGPT-account login is unreliable); `CURSOR_API_KEY` —
exported into the environment before `cursor agent -p --mode ask` (no `--trust` flag in the installed version).
Gemini: fabricates symbols freely — the read-proof and citation rules above are the defense; inline, brief, verify.

## What the panel is asked (summary; the full text is `prompt.md` and `known-findings.md`)

Not to re-derive K1–K8. To look ADJACENT: the `class-mismatch` reuse at `key="intent"` (K2.1); absence vs empty
by sentinel equality (K2.2); the `detail`-only channel and whether any other field crosses at `minimal` (K2.3);
which pre-resolution verdicts pin what decided them (K2.4); the two-member reason vocabulary and whether a third
state exists (K2.7); the D-11 evidence base — can a non-reference resolver mint a marker with no pins after
resolution ran (K3); the shape guard's "anything else → return" (K4); trees the AST walk did not cover (K5);
whether the `.replace()` chain is still a byte-identity proof (K6). And any violated named invariant in the
bundled diff.

**NOT RUN. The panel and the single-agent review follow Dave's evaluation of the build.**
