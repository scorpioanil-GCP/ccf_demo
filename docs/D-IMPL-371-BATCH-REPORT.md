# D-IMPL-371 — batch 4: consolidated report and the candidate for a main-merge decision

**Date:** 2026-10-06, ~07:40 MST. **Branch:** `integration-remaining-rows`. **`main` @ `933ef91f` untouched.**
No tag, no release, no SEC identifier closed; the ledger stays **13 of 29**. Cumulative with the pilot, batch-2 and
batch-3 reports (`docs/D-IMPL-368-PILOT-REPORT.md`, `docs/D-IMPL-369-BATCH-REPORT.md`, `docs/D-IMPL-370-BATCH-REPORT.md`).

## 1. The candidate

**Code tree: `91fd7965`.** The branch tip carries only docs commits after it (the close record, this report, a
regenerated coupling report); `git diff 91fd7965..<tip> -- src runtime tests tools pyproject.toml Makefile .github`
is empty. The combined regression, lints, mypy, examples and docs tests in §4 were run **once on that tree**, as ruled.

**What the candidate contains, relative to `main` @ `933ef91f`** (every change integrated under `D-IMPL-368`…`371`,
each with a red-before/green-after exploit test, named severings re-run by the orchestrator, and a close review):

| Row | State in the candidate |
| --- | --- |
| SEC-014 file modes (+ refuse-by-name delta) | integrated |
| SEC-015 CI permissions + SHA pins + Dependabot | integrated |
| SEC-021 bounded receive queues | integrated |
| SEC-024 (choice C: logs + `CCFContract`; wire unchanged; consequence documented) | integrated |
| SEC-025 child subject binding — local, mcp, mcp-product **and now peered** | integrated |
| SEC-026 Makefile credential echo + lint | integrated |
| SEC-028 hash-pinned lock incl. build set + lint; **SEC-028-F1** lock freshness | integrated |
| **SEC-022** signed issuance claims, replay refusal, declared window, peered question binding | **integrated this batch** |
| SEC-020 withheld vs nonexistent | **PARKED; not in the candidate** (reverted; branch kept) |
| SEC-017 | parked by ruling; verification evidence only |
| SEC-013, SEC-023, the lows, EX-09/10 | not started |

## 2. This batch's two repairs

**SEC-022 — INTEGRATED** (`row-sec-022` @ `e5da0fbe`). Signed issuance claims (`issued_at`, `nonce`, the answered
question and its echo) travel in the JWS protected header; the admission gate refuses `claims-missing`,
`stale-issuance` (two directional comparisons against the instant it already receives; no clock parameter) and
`replayed` (one atomic spend on a seen-set Protocol, on admission only, before the record is persisted); the peer
trust grant requires a max age and a skew with no SDK default; the composite's peered leg is bound to the asked
subject from the **verified** admission's signed claims, which closes SEC-025's parked leg (its xfail removed and a
positive control added). Nine exploit cases red→green; eight severings red; the orchestrator's own severing of the
seen-set reddened the replay case. Fable **measured** that the signature covers the issuance header (tampering nonce,
`issued_at` or subject, or removing the member, is refused). Transports and examples unchanged. The product address is
unchanged; the admission record's address moves with its new required field (no fixture pinned one).

**SEC-020 — PARKED, reverted** (`row-sec-020` @ `b371df45` kept as evidence). The final round built the rule the
previous rounds' measurements identified (re-execute the plan **without the request seed**) and passed all five
preconditions you set, including same-fabric unequal freshness and replay. The close review then **measured** a
finding on the shipped paved road: acquisition ingests the asked subject's evidence **before** the plan runs, so a
withheld subject's fabric differs from a never-acquired subject's at `computed_empty`, and no projection-time
re-execution can undo acquisition. The "by construction" docstrings were therefore false on the reference path. Your
rule for this round was explicit, so the row parks. The parked branch also carries the replay rehydration fix (which
repairs a pre-existing divergence for empty-finding products) and a recorded SDK finding: **the request seed never
reaches the final operator view** (`TraversalNeighborhood.apply` walks from class seeds only), bearing on
`D-IMPL-111` limb (a).

## 3. The single close review (`docs/D-IMPL-371-CLOSE-REVIEWS.md`)

Codex (diff only): two blocking, both inferred — one contradicts the Q14 ruling, one's mechanism Fable found not to
be the leak. Cursor: **READY**, no blocking. Fable: **NOT READY** on SEC-020 only, measured; no blocking on SEC-022.
Disposition: SEC-020 parked and reverted; SEC-022 stands. One consequence of SEC-024's ruling surfaced in a catalog
test that asserted the rejected input appears in the error text; corrected to the structured error (test only).

## 4. Regression on the candidate `91fd7965`, measured once

| Check | Result |
| --- | --- |
| the broad set (16 directories incl. skills, graph, cli, contracts, replay, peering, crossproc, products, projection) | **6743 passed, 2 failed** — the two standing reds that predate every batch |
| `tools.lints --all` | rc=0 |
| `mypy` | clean, 244 files |
| `tests/examples` (no estate export) | identical to the base (28 / 992 / 743) |
| `tools/docs_tests` | 320 passed |
| GitHub CI | docs gate and lint green on every integration commit since `3a77083c`; tests and examples jobs fail on the same single pre-existing cause as `main` (read per job in batch 3) |

## 5. Blockers and open rulings

1. **SEC-020**: route (a) a fourth round that pins or excludes this request's acquisition from the withheld
   rendering; or (b) rule the acquisition seam out of scope, narrow the docstrings, disclose the residual as a strict
   xfail. Either way, re-integrate the replay rehydration fix from the parked branch.
2. **SEC-022-R1** (ruling question, not a defect): the default in-process seen-set per gate is the Q14 ruling; the
   sharing obligation is documented, not enforced. Require an explicit seen-set, or add a boot-time check.
3. **SEC-017**: parked by ruling; the authorization proposal is owed. Not prepared this batch (it would have delayed
   execution).
4. **SEC-021-U1**: the pre-parse request-body limit on the LF leg stays explicitly open; nothing in this batch
   describes bounded queues as bounding bodies (audited twice).

## 6. Carried findings (new this batch, by name)

- **SEC-022-C-01** nonce scope is (tenant, observed peer id, nonce): a trust policy listing one key under two peer
  ids admits the same envelope twice via relabel; **C-02** `observed_peer.tenant_id` is never checked; **C-03** the
  issued-type parity test pins field names, not door validators; **C-04** no tests for an unknown claims lane or a
  naive `issued_at`; the replay consult runs after the other checks (a replayed envelope after its window reads
  `stale-issuance`); `_admit_peered` hides `replayed`/`stale-issuance` as `provenance-unverified` on the composite
  route; the in-process seen-set is never pruned; a spent nonce whose record persist fails refuses the retry (fails
  closed); `_PinnedReader` pins on no shipped substrate.
- **SEC-020** (parked): the acquisition-seam finding; the request-seed SDK finding; cross-fabric comparison is fabric
  content.
- **Process**: executor report writes were refused by the harness four times and relayed; the mkdocstrings docs gate
  checks the main checkout from any worktree; two "pre-existing" claims by executors were wrong on inspection (the
  retirement-sweep red in batch 2, the catalog-test red here), both caught by running the suites on a predecessor tree.

## 7. Recommendation

**The candidate `91fd7965` (branch tip for the docs) is ready for your main-merge decision** on the rows it carries,
with SEC-020 explicitly absent and the two ruling questions in §5 open. Nothing here is a tag or a closure.
