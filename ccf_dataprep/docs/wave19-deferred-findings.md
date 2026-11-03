# Wave 19 — deferred findings

Findings raised by Wave 19's task reviews and deliberately not fixed. None
blocks anything; none was rated above Minor; all are recorded here so a later
wave can pick one up deliberately rather than rediscover it.

**Why this file exists.** These live only in
`.superpowers/sdd/wave19-plan/progress.md`, which is **git-ignored scratch** —
`git clean -fdx` destroys it and git history does not carry it. Wave 18 hit
exactly this loss once (`docs/wave18-deferred-findings.md`'s own opening
explains it) — writing "N minors deferred" as a count rather than naming them
lost the findings the moment the scratch directory was cleaned. This file
follows that precedent: named findings, not a count.

**What "minor" meant here.** Minor is the review rubric's *ship it* tier —
narrower coverage than ideal, an untested-but-safe fallback path, a
diagnostic field that could be misread later. Everything Important or
Critical that Wave 19's reviews raised was fixed in a fix round before the
task closed; none of those are repeated here. The one exception worth naming
explicitly: Task 16's own review raised 2 Important findings (both partition
checks whose label claimed more than their implementation delivered) and 1
Minor, and **all three were fixed** in fix round 1 (commit `f08fa5f`) and
confirmed by a scoped re-review — nothing from Task 16's review is open.

Provenance: 16 task reviews (Tasks 1–16) and their fix rounds,
`.superpowers/sdd/wave19-plan/progress.md`, 2026-08-27.

IDs are stable. Cite them as `W19-D01`.

---

## Open

### W19-D01 — `generators/verify_fibo_wave19.py:606-613`: rejected-term domain/range recorded as hardcoded prose, not extracted programmatically

Found in Task 3's review. `ALL_TERMS` (the list of terms confirmed bound)
extracts each term's domain/range live from the ontology every time the
script runs. `REJECTED_TRAPS` (the two "related-party" lookalikes checked
and rejected — `cmns-pts:hasRelatedPartyRole`,
`fibo-sec-fund-civ:fundHasRelatedParty` — see
`docs/ccf_dataprep_v2.md`'s Wave 19 extension) instead carries its
domain/range as a hand-written string in each entry's `note` field.

Both values are confirmed correct as of 2026-08-27. The gap is that a later
FIBO release changing either term's domain or range, or a transcription
slip in the prose itself, would not be caught by re-running the script —
only `ALL_TERMS` re-verifies against the live ontology on every run.

**Fix, if picked up:** extract `REJECTED_TRAPS`'s domain/range the same way
`ALL_TERMS` does, so a re-run can catch drift rather than only a fresh
human read of the ontology.

### W19-D02 — `loaders/load_group_edges.py:~197-205`: local-name collision avoidance untested against an actual collision

Found in Task 6's review. When minting a Fluree node for one of the 37 GLEIF
entities with no prior node, the loader builds a local name and falls back
to appending `"2"` if that name is already in `used_locals`. No collision
occurred in this run (166 entities, 37 minted, 0 collisions), so the
fallback path itself has never executed against real data — it is read as
safe by inspection, not exercised.

**Fix, if picked up:** a unit test that seeds `used_locals` with a
colliding name before minting, to exercise the `+= "2"` branch directly
rather than relying on the live data continuing to avoid it by chance.

### W19-D03 — dependency-edge write path: idempotency verified only by read-only inspection, not a live re-run

Found in Task 7's review. The reviewer's sandbox could not execute a live
write against the shared Fluree/Postgres estate, so
`loaders/load_group_edges.py`'s handling of Task 7's 4
`economicallyDependentOn` edges was confirmed idempotent by inspecting the
ledger's state (no duplicate triples, stable triple count across the
controller's own two runs) rather than by the reviewer re-running the
loader itself and observing a second execution firsthand.

This is not a live discrepancy — the controller *did* run the loader twice
and confirmed the triple count and by-value state were unchanged
(`docs/ccf_dataprep_v2.md`'s Wave 19 Task 7 entry records the exact
before/after). The gap is procedural: the review gate's own independent
re-run of a write path, which caught real defects elsewhere this wave, did
not happen for this one loader.

**Fix, if picked up:** none needed unless the loader changes again — if it
does, get a reviewer with write access to re-run it rather than relying on
the implementer/controller's own re-run.

### W19-D04 — `sources/screening/wave19_proposals.json` carries generation-time diagnostic fields that read as authoritative

Found in Tasks 13+14's review. The JSON artifact `generators/generate_proposals.py`
writes keeps `existing_exposure_usd` / `existing_collateral_usd` alongside
the two `exposure_proposal` rows it drives into Postgres — figures the
generator computed *at generation time* to size the two hypothetical
proposals (`BREACHES`, `FITS_AFTER_MITIGATION`) against the live estate.

`sources/` is not one of the five authoritative stores, so this is not a
single-writer violation — nothing reads these fields back as ground truth
today. The risk is a future reader opening the JSON directly (rather than
querying `ccf_v2.exposure_proposal`) and mistaking a generation-time
snapshot for a live, re-queryable figure — the underlying group exposures
and collateral values can move if the estate changes, and this file would
not track that.

**Fix, if picked up:** either drop the two diagnostic fields from the
artifact once the Postgres rows are written, or add a comment/field naming
them explicitly as "as measured at generation time, not authoritative."

---

## Closed during Wave 19 — do not redo

| ID | Finding | Closed by |
|---|---|---|
| (Task 15's) | `validators/large_exposure.py:353-354,498-501` — `carries_methodology`/`carries_replay_attribution` loaded into `Context` but read by no floor | Task 16 added the `examiner plan carries methodology AND replay attribution` count specifically to close this — see `docs/ccf_dataprep_v2.md`'s Wave 19 conditions.py section |
| (Task 16's, 2 Important + 1 Minor) | `check_wave19()`'s two new partition checks (`W19-2` "no connected-group table", `W19-3` "no regime rule text outside MongoDB") matched narrower patterns than their labels claimed | Fix round 1, commit `f08fa5f` — both widened to allowlist-based scans (`WAVE19_GROUP_TABLE_ALLOWLIST`, `WAVE19_REGIME_TEXT_COLUMN_ALLOWLIST`), re-review confirmed clean |

## Not a defect — an honest, recorded divergence, not listed above as a "finding" to fix

**The jurisdiction span is 12 of a ~15 shape**, not a review finding but a
measured shortfall against §F's own figure. 9 of 26 control-basis connected
components span ≥ 3 jurisdictions on real GLEIF edges alone (Wave 15); Task
7's 4 engineered `economicallyDependentOn` edges closed 3 more via
defensible supplier-concentration judgments (9 → 12). A 4th candidate
(Agilysys ∪ Hain Celestial) was considered and **rejected** — no plausible
supply, funding, or tenancy link exists between a hospitality-software
vendor and a packaged-foods company. Recorded in three places already
(`conditions.py`'s `groups recompute` check text,
`docs/ccf_dataprep_v2.md`'s Wave 19 entry, `docs/HANDOFF.md`), deliberately
**not** added to `spec_coverage.py` — that file maps §C catalog elements,
and no §C row names a jurisdiction-span population for a divergence note to
attach to (Task 16's own ruling, `progress.md`). Nothing further to fix
here without inventing a merge the data does not support.
