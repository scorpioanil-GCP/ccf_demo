# Domain code versus SDK plumbing — measured after D-IMPL-343 and D-IMPL-344

**Asked by Dave, 2026-09-16:** *"a report on LOC comparison between domain and SDK
plumbing like you did before with the new enhancements."* The "before" is the
measurement `docs/D-IMPL-343-DESIGN.md` §1 and §7 made on `1e22dae2`; this report
re-runs the same counter (Appendix A there, reproduced below) on the same subjects at
their pre-paving commits and at the current tree (`cp-14-gate-2-slice-1 @ 05f208f8`,
on `main @ 66be7cb8`, which carries `D-IMPL-343` and `D-IMPL-344`). Every number is
measured, none estimated; the 343 design's §7 "after" column was an estimate and is
compared against the measurement in §3.

**Reading rule.** *Plumbing* is code an adopter writes only because the SDK asked for it:
`produce.py` (the spine) and `server/serve.py` (the door). *Domain* is the deployment's
own vocabulary and logic: `deployment.py`, `acquisition.py`, `projection.py`.
*Presentation* is `run.py`, which prints and is never published-snippet surface.
*Documents* are the declaration files (`ccf_config.yaml`, `ccf_environment.yaml`, and
the pre-343 `backends.yaml`, `server/door.yaml`, `artifacts/ttl.yaml`), counted as
physical lines / non-comment lines. *SDK names imported* is the number of distinct
`ccf.` names imported by the plumbing files plus `deployment.py` — how much of the SDK
an adopter has to know to write the tree.

## 1 · The three producers that moved, before and after

| subject | plumbing (py) | domain (py) | `run.py` | documents phys / non-comment | SDK names imported |
|---|---|---|---|---|---|
| cp-03 frozen — hand-composed low road (the specimen `D-IMPL-261` froze) | 209 | 974 | 198 | 362 / 138 | 40 |
| cp-03-canonical **before** 343 (low road, `1e22dae2`) | **342** | 931 | 93 | 558 / 273 | 37 |
| cp-03-canonical **after** (paved, today) | **54** | 803 | 107 | 550 / 279 | **18** |
| cp-04 frozen — hand-composed low road | 518 | 1641 | 229 | 698 / 206 | 57 |
| cp-04-canonical **before** paving (low road, `e388ee56`) | **96** | 585 | 75 | 493 / 204 | 27 |
| cp-04-canonical **after** (paved, today) | **58** | 462 | 88 | 531 / 238 | **16** |
| cp-14 consumer (paved, today; the only consumer tree) | 45 | 274 | 71 | 330 / 216 | 18 |

Per file, the two paved producers today:

| tree | `produce.py` | `server/serve.py` | `deployment.py` | `acquisition.py` | `projection.py` | `run.py` |
|---|---|---|---|---|---|---|
| cp-03-canonical before → after | 99 → **29** | 243 → **25** | 341 → 222 | 442 → 433 | 148 → 148 | 93 → 107 |
| cp-04-canonical before → after | 96 → **33** | (none) → **25** | 223 → 112 | 201 → 189 | 161 → 161 | 75 → 88 |

**What the numbers say.**

- **Plumbing fell by 84 % on the spread producer (342 → 54) and by 40 % on the family
  producer (96 → 58), while the family producer gained a door it did not have.** The
  spread producer's hand-written door (243 lines) became a 25-line launcher; its spine
  (99) became 29 lines of three regions. The family producer had no door at all before
  slice 2; its 25-line door is the same launcher.
- **Domain code also fell** — 931 → 803 and 585 → 462 — and not because domain logic
  was deleted: `deployment.py` shed the effective-request re-derivation, the perspective
  and TTL restatements, and the backend-settings reader that the road now supplies
  (`D-IMPL-343` R-4, the "two authorities for one number" duplications §4 of the design
  counted). `projection.py` is byte-identical in both trees, which is the cleanest
  statement that Π was never plumbing.
- **The SDK an adopter must know halved**: 37 → 18 and 27 → 16 distinct `ccf.` names.
  The remaining names on the paved trees are the ones a deployment cannot avoid naming —
  the request, the envelope, the signal, the debt assessment, the refusal type — not the
  resolver, registry, store, writer or recorder.
- **Documents did not shrink and were not meant to.** The declaration files carry
  roughly the same non-comment lines before and after (273 → 279; 204 → 238). What
  changed is their number and their authority: four documents became two, and the
  values the design found stated twice (replay class, principal and role, TTL, class and
  lane, the five section keys, the producer tenant) are now stated once. The family
  producer's documents grew by 34 non-comment lines because it now declares `replay:`,
  `ttl:` and `door:` sections it previously had no door to need.
- **`run.py` grew a little on both trees** (93 → 107, 75 → 88): each gained a `--door`
  flag and a few lines printing the refusal's reason and replay reference. Presentation,
  not plumbing.

## 2 · The consumer side

There was no consumer tree before `D-IMPL-343`; the only consumer of a governed
`mcp_product` child was a test. The comparison the design made in §2 is re-measured:

| subject | code lines |
|---|---|
| low-road consumer proof, `tests/examples/test_cp_03_canonical_cross_deployment.py` at `1e22dae2` | 419 |
| the same file today (unchanged in substance) | 422 |
| paved consumer proof, `tests/examples/test_cp_03_canonical_paved_consumer.py` today | **191** |
| the CP-14 consumer tree today — plumbing / domain / presentation | **45** / 274 / 71 |

The CP-14 tree reaches five producers through four declarations (`requires`,
`producers:`, `skills:`, `agent:`) and one keyword (`questions=`); its 45 plumbing
lines are the spine's three regions plus the composite plan factory's
`build_with_children` adapter. The D-IMPL-343 close measured the same thing from the
other side: 129 + 38 lines of consumer wiring became 15, and nine hand-built Control
Plane objects became zero.

## 3 · Against the design's estimate

`docs/D-IMPL-343-DESIGN.md` §7 estimated the paved spread producer at ≈ 20 / ≈ 215 /
148 / ≈ 429 / ≈ 85 / ≈ 8 code lines (produce / deployment / projection / acquisition /
run / server) — ≈ 905 in all — and plumbing at ≈ 35–45.

| file | estimated | measured | note |
|---|---|---|---|
| `produce.py` | ≈ 20 | 29 | the `product(scratch, environ=)` context manager and the `assemble_and_serve` shim the proofs call |
| `server/serve.py` | ≈ 8 | 25 | argument parsing for `--door` and the token remedy line; the door call itself is one line |
| `deployment.py` | ≈ 215 | 222 | as estimated |
| `acquisition.py` | ≈ 429 | 433 | as estimated |
| `projection.py` | 148 | 148 | unchanged, as stated |
| `run.py` | ≈ 85 | 107 | the `--door` flag and refusal printing were not in the estimate |
| **total** | **≈ 905** | **964** | plumbing **54** against the estimated 35–45 |

The estimate was 6 % optimistic overall and 9–19 lines optimistic on plumbing; the
difference is in the two launcher files, and it is all argument handling.

## 4 · The producers the next CP-14 slices reach, as they stand today

These are the low-road trees `D-IMPL-340` froze. They are not on the paved road, and
the slice-2 census (`examples/cp-14-credit-memo-context/FINDINGS.md`) classed each.

| tree | class | plumbing (py) | domain (py) | `run.py` | documents phys / non-comment | SDK names imported |
|---|---|---|---|---|---|---|
| cp-06 collateral (`credit-risk.collateral-coverage`) | B — a paved sibling is the route | 247 | 749 | 84 | 430 / 253 | 32 |
| cp-13 covenant (`credit-risk.covenant-cross-reference`) | B — a paved sibling is the route | 88 | 897 | 130 | 256 / 167 | 14 |
| cp-05 exposure (`credit-risk.exposure-rollup`) | C — `CP14-F-33`, no seam for its post-traversal aggregation | 473 | 420 | 304 | 625 / 290 | 40 |

Read against §1, the paved-sibling route for cp-06 should land near the family
producer's shape: plumbing in the 50s, the 150-line door gone, and roughly a third of
`deployment.py` (236 today) absorbed by the road. cp-13 has little plumbing to lose
(88) and no door; its cost is domain re-expression, not SDK ceremony. cp-05 is the
outlier — 473 plumbing lines, more than its domain code — and that is `CP14-F-33`'s
measurement, not a paving target.

## 5 · What this report does not claim

It counts lines, not difficulty, and it counts one adopter's trees, not a population.
A line of `deployment.py` that restates a config value is domain by file and plumbing
by nature; the design's §4 duplication census is the instrument for that, not this
counter. The consumer figures compare a test module to a test module and a tree to
nothing, because no consumer tree existed before.

## Appendix A · Reproducing the numbers

The counter is `docs/D-IMPL-343-DESIGN.md` Appendix A verbatim (code lines = physical
lines carrying at least one token that is not a comment, blank, indentation or end
marker, excluding docstring lines). The historical subjects are read with
`git show <sha>:<path>`; the files and categories are the ones named in the reading
rule above. The session's script is not committed; the counter and the file list are
sufficient to reproduce every cell, and the 343 baseline (`1366` and `419` at
`1e22dae2`) reproduces exactly.
