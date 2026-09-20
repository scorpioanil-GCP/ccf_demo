# Qualification repair package — the 46 deferred nodes, A through E

**Branch:** `release/qualification-repairs`, from `main @ 5d795276` (verified equal to `origin/main`
before the first commit). **Investigation accepted:** `docs/QUALIFICATION-f0656746-INVESTIGATION.md`.
**Scope, as ruled:** tests, documentation and pins only — no `src/`, `runtime/`, product
configuration, TTL, policy, debt, estate data or served behavior was changed, and none needed to
be. **State:** pushed for review; not merged; the final release `make test` not run.

Date: 2026-09-19.

## 1. Repairs by root cause

| group | root cause | nodes | repair | commit(s) | behavioral change |
|---|---:|---|---|---|---|
| **A** no-obligation guard | 42 | `DecayBasis` (D-IMPL-331) and `FreshnessAggregation` (D-IMPL-333) added to `EXEMPT_DECLARATIONS` in the `DecayMode` shape, each citing its ruling; the glob test's message names the unexempted declaration it finds instead of blaming `_GLOB_CHARACTERS`; production `Literal`s untouched. Controls: removing either entry reds the real tree naming exactly that vocabulary (parametrized); a planted two-string `Literal` with no roster entry stays red. | `ae6178a6`, `4715b002` | none |
| **B** CLAUDE.md pin | 1 | whole-file byte pin removed; the two seven-member invariant lists (§3.1 Phase-D bullet, §16 bullet) located by lead-in anchor, bracket-matched, whitespace-normalized and held as ordered rosters; a missing or ambiguous anchor is red. Controls on in-memory copies: an eighth invariant, each member removed / duplicated / substituted → red naming list and member; five reflows and unrelated prose at four positions → green. Whitepaper leg untouched. D-IMPL-271 (4)(5) recorded on `main`'s log. | `e586fc87`, `bdba1c2a` | none |
| **C** citation ratchet | 1 | the 86 sites treated individually against the citing commit: 30 living `::Symbol` kept, 48 retargeted to the symbol the sentence is about, 6 marked historical with the checker's own marker (the 336 panel transcript and remediation disposition, where the line at a SHA is the claim), 2 removed as unsupportable (sentence kept). Ceiling untouched; no class exemption; the 169 checked citations still enforced, 78 more now checked. Sabotage: one repaired citation altered → the checker reds it by name. | `fd3d3f51` | none |
| **D** peering pin | 1 | whole-file hash replaced by a positive hold over `LineageEntry`'s reading-(d) shape (its four fields; no federated axis as field or attribute; extra forbidden; `ProductLineage` carries the axes; the `AdmissionRecord` carries a `ProductLineage`); the D-IMPL-332 movement recorded; negative control: a `LineageEntry` widened by one federated axis reds the hold. Production `claims.py` untouched. | `842fc066` | none |
| **E** CP-14 order node | 1 | the whole-process `sys.modules` walk replaced by an `ImportAudit` active only around the consumer action (import statements through `builtins.__import__`, `importlib.import_module` including the cached path, and an identity diff of `sys.modules`); `assembler` added to the two shared pop lists (CP-14's `modules` fixture, imported by the sibling slices, and cp-03-canonical's cross-deployment copy); frozen cp-05 loaders untouched; no reorder, no `sys.modules` clearing, no isolation. Controls without the estate: a cached producer module untouched by the action is not reported; an import hitting the cache, a fresh import, a pop-and-reimport and an `importlib.import_module` of the cached module are; hooks restored. | `d5810c4b` | none |

Records: `bdba1c2a` and `b116b57f` (D-IMPL-271 (4)(5) on `main`; the qualification report's two
misattributions corrected by appendix; the correction-1 report's dated citation of the renamed
peering node). Original measurements and the investigation stand as written.

## 2. Verification on the repair branch

| check | result |
|---|---|
| `tests/invariants` + `tests/peering` (all five groups) | **2 252 passed, 0 failed** |
| `tools/lints/tests` | 480 passed |
| `python -m tools.lints --all` (incl. the citation checker) | exit 0 |
| citation ratchet (`test_citation_coverage.py`) | 5 passed; unanchored population **0** |
| `make typecheck` | clean, 230 files |
| `tools/docs_tests` + `tools/publish_scan_tests` | 349 passed |
| CP-14 four slices + cp-03-canonical cross-deployment, one process (estate) | 37 passed |
| cp-05 output suite **then** the CP-14 isolation node, one process (estate) | 13 passed |
| the CP-14 isolation node alone (estate) | 1 passed |

**The 46 nodes, by exact id:** 46 of 46 green — 44 by the same id; the CLAUDE.md byte-pin node
(`tests/invariants/test_determination_authority_disclosure_delivery.py` `::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]`)
replaced by the two roster nodes `test_the_invariant_roster_is_the_seven_it_has_always_been[…]`,
both green; the peering hash-pin node (`tests/peering/test_admission_record.py`
`::test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in`) replaced by
`tests/peering/test_admission_record.py::test_lineage_entry_holds_reading_d_so_reading_a_cannot_creep_back_in`,
green. The full mapping with outcomes is `roster46_after_repairs.txt` in
`qualification/f0656746/repairs/evidence.tar.gz`. No new skip or expected-failure mark anywhere.

## 3. Fresh-checkout verification

Recorded in §3 of this file's next revision after the package tip was checked out fresh (no
ignored sidecars) and the same checks rerun there; see the commit that carries it.
