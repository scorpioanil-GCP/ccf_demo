# Phase 24.8 — close-time cross-AI panel packet (CLAUDE.md §3.1)

**NOT RUN. The panel and the single-agent review follow Dave's evaluation of the build.**

This directory is a STAGED packet. No reviewer (`codex`, `cursor`, `gemini`, `/gsd-review`) was
invoked in plan 24.8-07; no `24.8-CLOSE-REVIEWS.md` exists; no credential was read or written into
the tree. Per memory `pause-after-the-product-is-built` and the `D-IMPL-266` precedent from 24.7, the
sequence is: **build evaluation (Dave) → this panel, if useful → the single-agent code review →
verify every finding against the tree → fix blocking findings in-phase → present → `D-GATE-24.8`.**

## Subject

The SHIPPED tree of `phase-24.8` at `d7c4946b7b19d34b198bf1d3d5a951a4eaa852ea`, diff base
`8567d683` (the `D-IMPL-267` design sitting, where the branch forked from `main`). **The subject is
the code, not the plans** — the plans were reviewed before execution (`c5586450`, plan-checker
VERIFICATION PASSED), and CLAUDE.md §3.1 makes shipped code the close-time target. Built by
`scratchpad/build_panel.py` (session scratchpad, not committed) on 2026-09-07; if a blocking finding
is fixed in-phase before the panel runs, **REBUILD from the fixed tree** so the fixes are among the
subjects (the 24.6 precedent).

## Inventory (`wc -c`, bytes; every part is under the 131,072-byte argv cap — but see the stdin rule)

| File | Bytes | Contents |
| --- | --- | --- |
| `README.md` | (this file) | inventory, rules, credentials pointer |
| `prompt.md` | 5,392 | the reviewer instruction: shipped code; `path.py::Symbol`; blocking/advisory; unresolvable citation = void; the three questions most wanted |
| `known-findings.md` | 10,305 | K1–K12: what is already known and the ADJACENT question for each — reviewers are told NOT to re-derive them |
| `bundle-src.md` | 79,401 | `git diff 8567d683..HEAD --stat -- src docs/GRAPH_QUERY_SEMANTICS.md`; **`src/ccf/operators/categories.py` WHOLE**; **`src/ccf/graph/fallback.py` WHOLE**; the document banner (`:1-12`), `GQ-10` (`:201-220`), `GQ-13` (`:261-288`), `GQ-16` (`:316-329`) and `GQ-35` with the whole 1.3.0 entry (`:621-701`) in full; then the diff itself |
| `bundle-tests-part-1.md` | 79,317 | the two NEW test modules WHOLE: `tests/conformance/test_operator_tier_differential.py`, `tests/operators/test_traversal_unresolved_reference.py` |
| `bundle-tests-part-2.md` | 52,747 | the `tests` diffstat, then per-file diffs of the five changed modules: `tests/conformance/query_corpus.py`, `tests/operators/test_traversal_admission.py`, `tests/operators/test_traversal_direction.py`, `tests/properties/test_composition.py`, `tests/fixtures/banking/edge_graphs.yaml` |

Source is **INLINED, not pointed at**: `grep -c '^\s*\(def \|class \)' bundle-src.md` → 38;
`bundle-tests-part-1.md` → 54; `grep -c '_bounded_walk' bundle-src.md` → 12. Both changed `src/`
files appear WHOLE (`git diff 8567d683..HEAD --name-only -- src runtime` → exactly those two).
`grep -cE 'API_KEY[=]' 24.8-PANEL/*` → **0** across every file. (The pattern is written with the
`[=]` character class deliberately: a README that spells the literal token out matches its own
assertion and reports a false positive — the first run of this check returned 2, both of them this
sentence and the one under Credentials.)

**Left out, deliberately, and named:** `.planning/` (the criteria, plans, SUMMARYs, `24.8-CLOSE-PREP.md`),
`examples/` and `tests/examples/` (frozen under `D-IMPL-261`, diff-empty against the base),
generated `docs/schemas` and `docs/surface`, `docs/DECISIONS.md`, `archive/`, `public/`, `runtime/`
(diff-empty). Reviewers are told these are not the subject and any finding about them is out of
scope.

## Delivery rule — STDIN ONLY

**Never pass a bundle as an argv string.** On this host a single argv string caps at 128 KB; a
payload over that dies `rc=126` with 0 bytes of output, which reads exactly like a clean, empty
review (memory `a-single-argv-string-caps-at-128kb`). Every part here is under the cap, but the rule
is stdin regardless:

```
# one call per reviewer per part; prompt + brief + bundle concatenated on stdin
cat prompt.md known-findings.md bundle-src.md | <reviewer command reading stdin>
```

Codex's sandbox (`bwrap`) can fail in a way that **exits 0 having read nothing** (memory
`cross-ai-panel-reliability-on-this-host`); inlining the source is what makes a silent sandbox
failure unable to empty the review — and the read-proof rule below is what makes it detectable.

## Read-proof rule — a reviewer counts only if BOTH hold

1. **The token.** Each part carries a `READ-PROOF <part>: <hash>` line at its top, mid-payload and at
   its end; each part's token is different. The review must quote its part's token verbatim. A review
   that quotes none, or quotes another part's token, **did not read its payload** — record it as a
   FAILED reviewer, not as a reviewer.

   | Part | Token |
   | --- | --- |
   | `bundle-src` | `READ-PROOF bundle-src: 33364fe6c78b4141019dd8a4` |
   | `bundle-tests-part-1` | `READ-PROOF bundle-tests-part-1: a25c7016b2cddc69c5c52beb` |
   | `bundle-tests-part-2` | `READ-PROOF bundle-tests-part-2: 726378dc7147ade40bc98aac` |

2. **The citations.** Every finding cites `path.py::Symbol`. Before counting a finding, **resolve the
   symbol against the tree** at `d7c4946b`:

   ```
   git show d7c4946b:src/ccf/operators/categories.py | grep -n "^def _bounded_walk\|class TraversalNeighborhood"
   ```

   A finding whose symbol does not resolve is **VOID** and is recorded as a fabricated citation (24.6
   saw a reviewer assert two lint checkers had no tests when 41 test functions existed; 15.1 rejected
   a reviewer outright for fabricated citations). **A resolved citation is still not a correct
   finding** — verify the claim separately, and where the panel and the tree disagree, sabotage the
   code to settle it (memory `a-resolved-citation-is-not-a-correct-finding`). Three reviewers
   agreeing is not evidence (memory `three-reviewers-agreeing-is-not-evidence`); pin every rejected
   premise as a control.

Record every reviewer run — command, rc, token quoted or not, findings kept / rejected with the line
that rejects each / carried for Dave — in **`24.8-CLOSE-REVIEWS.md`** (a distinct file, so the
pre-execution plan review survives).

## Credentials (never in the tree)

Codex and Cursor authenticate from `/home/parkave/homecams_v2/.env` (memory
`cross-ai-review-credentials`). `CODEX_API_KEY` — `printenv CODEX_API_KEY | codex login
--with-api-key` before `codex exec` (**not** `OPENAI_API_KEY`; that project has no credit; the
ChatGPT-account login is unreliable). `CURSOR_API_KEY` — exported into the environment before
`cursor agent -p --mode ask` (no `--trust` flag in the installed version). Gemini fabricates symbols
freely — the read-proof and citation rules above are the defense: inline, brief, verify. **No key
appears anywhere in this packet:** `grep -cE 'API_KEY[=]' 24.8-PANEL/*` → 0, and a broader scan for a
credential-shaped value (`(API_KEY|SECRET|TOKEN|PASSWORD)\s*[=:]\s*[A-Za-z0-9_-]{16,}`) returns nothing.

## What the panel is asked (summary; the full text is `prompt.md` and `known-findings.md`)

Not to re-derive K1–K12 — the ruled mechanism and its two rejected alternatives (K1), the two
intermediate-class conventions (K2), the ontology-oriented curated case (K3), the deliberate `X -> B`
orientation (K4), the non-discriminating cycle test and its sabotage (K5), the view-independent
provenance the silence check rests on (K6), the depth-3 byte control (K7), the strict-red wave-1
commits (K8), the two research-roster defects (K9), the two measured-vs-stated differences (K10), the
`GQ-11` cross-reference the amendment did not add (K11), and the three carries (K12).

**To look ADJACENT.** The three questions most wanted:

1. Any **other** place in `src/` that walks persisted edges over a view it did not endpoint-close —
   the engine's survivor-cap branch, `planner.py`'s compose/cache paths, any in-process consumer of a
   raw `as_of` view — and any **other** test holding an operator to something weaker than
   `fallback.answer`.
2. Any **other** prose site in `src/` making a *current-rendering* claim about a versioned document,
   as opposed to an arrival note.
3. Whether `GQ-11` (walk-start selection), read alone, can be taken to permit a claim-less URI as a
   walk start.

Plus any violated named invariant in the bundled code (CLAUDE.md §10–§11; INV-CH7-20/24/40).

**NOT RUN. The panel and the single-agent review follow Dave's evaluation of the build.**
