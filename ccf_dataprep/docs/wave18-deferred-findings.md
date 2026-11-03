# Wave 18 — deferred findings

Findings raised by Wave 18's task reviews and its whole-branch review, triaged
as **Minor** and deliberately not fixed. None blocks anything; all are recorded
so a later wave can pick them up deliberately rather than rediscover them.

**Why this file exists.** These lived only in
`.superpowers/sdd/wave18-plan/progress.md`, which is **git-ignored scratch** —
`git clean -fdx` destroys it and git history does not carry it. The whole-branch
review also found that ledger was recording *counts* rather than findings: three
tasks said "8", "8" and "13 minors deferred" and had transcribed two between
them. This file is the durable copy.

**What "minor" meant here.** Minor is the review rubric's *ship it* tier —
polish, narrower coverage than ideal, a report that described its own evidence
loosely. Anything that made a task untrustworthy was Important and was fixed in
a fix round; anything that would have blocked merge was Critical and none
occurred. So nothing below is a known bug in the loaded data.

**Findings that were *not* minor** — the estate-level limits a consumer or a
future wave actually needs — were promoted into `docs/known-issues.md` §34–§44
and are not repeated here.

Provenance: 17 task reviews, 9 fix rounds and one whole-branch review,
2026-08-25 to 2026-08-27. Merged at `7785028`; this file added after.

---

## Status at a glance

| | |
|---|---|
| Findings in the task ledger | 55 |
| Plus minor findings from the whole-branch review with no task-ledger line | 2 |
| **Entries below** | **57** |
| — closed by later work in the same wave | 6 |
| — promoted to `docs/known-issues.md` | 5 |
| — dismissed on inspection (not defects) | 2 |
| — **open** | **44** |

These counts are derived from this file and reconciled against
`.superpowers/sdd/wave18-plan/progress.md`, not asserted. Every one of the 55
ledger findings maps to an entry here. The reconciliation is worth re-running if
you edit this file — an earlier draft of this very document claimed 51 and 41,
both wrong, because the pattern used to count them missed four variant labels
(`minor (deferred, pre-existing)`, `minor (deferred, STRONG candidate…)`).

Four are flagged cheap-and-worthwhile: **D45**, **D01**, **D44**, **D18**.

IDs are stable. Cite them as `W18-D07`.

---

## Closed during Wave 18 — do not redo

Recorded as deferred, then closed by later work. Listed so nobody spends an hour
fixing something already fixed.

| ID | Finding | Closed by |
|---|---|---|
| C1 | `CAPTION_MAX_GAP` had no dedicated unit test (Task 2) | Final fix wave — `validators/test_syndicate.py:1078-1108`, gap inside vs outside the threshold, different answers required |
| C2 | The envelope disjointness claim was narrative, enforced nowhere (Task 10) | Final fix wave — `generators/generate_disclosure_envelopes.py:184-188`, `assert not (set(request_scope) & set(disclose_scope))` on the live generation path |
| C3 | `test_no_threshold_node_stores_a_computed_pass_fail_outcome` was vacuously true against an empty graph (Task 11b) | Final fix wave — population asserted non-empty before the negative claim |
| C4 | The "record nothing if absent" path was unexercised (Task 11) | Task 11b — `test_extract_one_records_absence_and_emits_no_passage_when_heading_missing` |
| C5 | "Tasks 8/14/16 import rather than re-derive" was unverifiable when raised (Task 6) | Verified at Task 8 and again by the whole-branch review: all three loaders import `WAVE18_EXCLUDED_FACILITIES` / `TRANCHE_TO_FACILITIES`; none re-derives |
| C6 | `member_commitment` / `amendment_vote_posture` granularity needed an assembly-time check (Task 7) | Answered by Task 17's §C mapping |

---

## Promoted to `docs/known-issues.md` — recorded there, not here

Deferred findings judged to be estate-level limits a consumer or a future wave
needs. They are **not** repeated in the open list below.

| Finding | Task | Now |
|---|---|---|
| `_snc_document()` omits `passage_count`, which every other document row carries | 12 | §37 |
| The banded row's citation span is 14 chars against 21 on exact rows — a digit-length side channel | 14 | §40 |
| `DECLARATION_SPECS`' TTL and latency values are hand-picked literals; a fourth declaration would silently become a second contrast | 15 | §41 |
| `extract_agent` drops a leading "The" from an institution name | 1 | §43 |
| The two planting tests restore in a `finally`; a killed process between commit and restore leaves residue | 17 | §44 |

---

## Open — tests and guards that are narrower than they look

The wave's dominant theme. None is a false result today; each is a check that
would not notice a specific regression.

**W18-D01 · The original 13 `ex:` terms are not in the automated absence check.**
*Task 4 · `generators/verify_fibo_wave18.py:164` (`EX_MINTED_CHECKED_ABSENT`)*
The manifest carries 14 entries, all Wave 18's own. The 13 terms Task 4 bound
were confirmed absent from the ontology by **ad hoc grep** by two people — a
check that is neither reproducible nor committed. Flagged at the time as a strong
candidate. Closing it: append the 13 names and re-run; the script does the rest.
Verify first whether any were added since — the manifest grew through Tasks 9,
10 and 11b and the overlap was never re-checked.

**W18-D02 · `test_mongo_holds_no_typed_edge` checks one hypothetical field.**
*Task 11* It probes `participatesIn` rather than edge-shaped structure generally.
The reviewer noted `participatesIn` is the real predicate this wave uses, so it
guards a plausible mistake rather than a strawman — but a differently-named edge
would pass.

**W18-D03 · The second conjunct test asserts the symptom, not the row.**
*Task 17 · `validators/test_syndicate.py`* One of the two exemption-conjunct
tests asserts `LEAK INWARD` appears; its sibling additionally derives the
`federation_attestation` row id live and asserts the exact
`pg context_debt.<column>#<debt_id>` substring. Not exploitable —
`_is_permitted_debt_reference` has exactly one call site, so no other path
produces that message — but the rigor is asymmetric.

**W18-D04 · Six boundary tests do not assert baseline-green before flipping.**
*Task 17* Unlike the W18-2 and W18-4-absent tests, they do not establish the
check passes before mutating the constant, so a check that was already red would
read as a successful falsification.

**W18-D05 · `test_the_planted_needle_never_reached_the_peer_fabric` reads a snapshot.**
*Task 16 · `validators/test_syndicate.py`* It checks `_BASE_CTX`'s deepcopy
rather than a fresh store read. It proves no test mutation leaked into the shared
snapshot — the only failure available, since nothing writes to a store — but the
name promises more than it does. Cheap: read the store.

**W18-D06 · Route counts print on PASS but not on FAIL.**
*Task 16 · `validators/syndicate.py`* `shares_are_sourced` builds its
canonical-vs-variant route counts only in the success path. A run where the
variant route widened *and* something else failed hides the widening.

**W18-D07 · `spec_coverage.py` has no unconfigured-peer guard.**
*Task 17 · `validators/spec_coverage.py:1667`* `n = mp.probe()` is uncaught, so
the three peer probes raise `CoLenderNotConfigured` as a traceback where
`conditions.py` SKIPs and `partition.py` FAILs with an explanation.

**W18-D08 · The `#20` block's direct counts raise rather than SKIP.**
*Task 17 · `validators/conditions.py:2130`* An absent table crashes `collect()`
instead of skipping. House style — consistent with every other product block —
so fixing it means changing the convention, not one block.

---

## Open — guards described more broadly than they scan

**W18-D09 · The outward boundary arm scans two identifier families.**
*Task 17 · `validators/partition.py:1859`* `_our_wave18_identifiers` covers
`SYNM-` and `SDT-` only. A mirrored `own_position`, `competition_law_rule` or
`syndicate_projection_plan` row on the peer would not be seen by the cell scan.
A wholesale table copy is still caught by the `unexpected_tables` arm. The
docstring was corrected in the fix wave to claim only what it does; the coverage
was deliberately left.

**W18-D10 · The Context Debt exemption has no ceiling.**
*Task 17 · `validators/partition.py`* The exempt set grows one-for-one with
`federation_attestation` rows, and the PASS detail reports `len(debt_subjects)`
rather than the number of hits actually exempted — so a widening exemption is
visible only indirectly.

**W18-D11 · The compensating assertion's reach is narrow.**
*Task 17 · `validators/partition.py:2135`* It checks each debt row's `reason`
for the literal `str(ttl)`/`str(latency)` of that declaration. Blind to
`attestation`, `disclosure_precision` and band bounds, and loose enough to
false-positive on a coincidental digit run in free text.

**W18-D12 · `strays` is unfalsified, by choice.**
*Task 17 · `validators/partition.py:2316`* Both sides read live from
`information_schema`, so nothing is patchable — but the same hoist-a-seam move
applied to W18-4 would make it falsifiable without touching the peer's DDL. The
paragraph in the Task 17 report records this as available work, not blocked work.
Coverage meanwhile is real: ARM 2's `unexpected_tables` catches a shared name
outside the two peer tables, ARM 1's `peer table {t} exists in ours` catches it
when the name *is* one of them.

**W18-D13 · `_assert_peer_ledger()`'s docstring claims parity it does not have.**
*Task 14 · `loaders/load_peer_wave18.py:130-141`* It is entirely config-derived —
it compares `.env` against `.env` — with no server-side half. The Postgres gate's
value is that its third gate asks the **server**. The literal is still
hardcoded, so it is additive protection; the claim is the problem.

**W18-D14 · Two §C probes count a quantity adjacent to their row's.**
*Task 17 · `validators/spec_coverage.py`* "Administrative agent identity" counts
12 `ex:administeredBy` edges where the row is about 4 institutions; "Syndicate
composition — lender names and commitments" counts commitments only. Neither
carries a floor, so nothing rests on them.

---

## Open — duplication and drift risk

**W18-D15 · `ex:amends` is a second Python constant.**
*Task 9 · `ccf/syndicate.py`* Declared rather than imported from
`loaders/load_temporal_wave5.py`. Identical value, documented reasoning, but a
cross-module literal duplicate — the class `ccf/syndicate.py` exists to prevent.

**W18-D16 · `document` and `facility_ids` are duplicated onto every threshold dict.**
*Task 11b · `generators/extract_voting_thresholds.py:592-629`* Also carried once
at the parent level. Harmless — the artifact is regenerated wholesale — but it
roughly doubles the redundant fields.

**W18-D18 · `postures[voter] = value` — last row wins.**
*Task 16 · `validators/syndicate.py:440`* A voter carrying two `ex:votePosture`
literals silently loses one, changing the distinct-posture tally in either
direction. Cheap: raise on the second.

**W18-D19 · `vote_postures_diverge`'s voter count is the size of the read.**
*Task 16 · `validators/syndicate.py:436`* `_load_vote` inner-joins `votePosture`
with no independent `COUNT(*)`, so a voter with a `votesOn` edge and no posture
is invisible and "18 voter(s)" is unestablished. Direction is safe — fewer voters
cannot manufacture divergence, only reduce it.

**W18-D20 · `reconcile_peer_graph`'s `_esc` round-trip flattens literal types.**
*Task 14 · `loaders/load_peer_wave18.py:316-338`* Every literal is re-serialised
as a plain string, so a typed or language-tagged literal would not match the
generated `DELETE DATA` and would survive retraction — under-retracting the
mechanism that makes an append-only store idempotent. Harmless for this loader's
own output; a hole for anything added later.

**W18-D21 · Two independent derivations of the 12-facility population.**
*Tasks 8 and 13* `loaders/load_fluree_wave18.py` derives it from
`wave18_schedules.json`; `loaders/load_sqlite_wave18.py` from Postgres
`facility WHERE source_document = ANY(...)`. Both now carry a loud assert (the
Fluree side gained one in the final fix wave), so drift fails rather than
diverges — but the two derivations remain.

---

## Open — cost, size and style

**W18-D22 · `validators/test_syndicate.py` wants splitting.** Past 2,300 lines
across seventeen appends; a peer-fabric module of its own was the reviewer's
suggestion. *Tasks 14, 16*

**W18-D23 · `validators/partition.py` is 2,289 lines** (+606 in Task 17 alone)
and `validators/conditions.py` 2,913; `check_wave18` is ~180 lines of inline
try/except that would read better as four named functions. *Task 17*

**W18-D24 · Each of the 8 new boundary tests runs the whole of `check_wave18()`**,
so the suite makes eight full passes over both fabrics and all four stores, and
hard-requires a live configured peer. *Task 17*

**W18-D25 · `_ctx()` deep-copies ~12k probe dicts per test**; the floor suite
takes 28.85 s. Cost, not a defect. *Task 16*

**W18-D26 · `resolve_rssd()` and `_cert_for()` each call `_fdic_candidates()`**
for the same institution — two round trips where one would do. *Task 3*

**W18-D27 · `fetch_snc_report.py:116-118` builds `PdfReader` twice** over the
same 12-page file. *Task 12*

**W18-D28 · `_assert_peer_target(cur)` runs `SELECT current_database(),
current_user` and the next line re-runs it.** *Task 14 · have the gate return the
tuple*

**W18-D29 · `co_lender_update` is called with and without `ledger=`** in adjacent
lines; both resolve to `CO_LENDER_FLUREE_LEDGER`. Cosmetic asymmetry that reads
as significant. *Task 14*

**W18-D30 · `build_counterparties(rows, filed)` never uses `filed`.** Dead
parameter. *Task 14*

**W18-D31 · `import copy` and `from validators import syndicate` sit mid-file**
at `validators/test_syndicate.py:2061`, and `_BASE_CTX` is a module-level mutable
global — guarded by a leak test, so style rather than risk. *Task 16*

**W18-D32 · `main()`'s stats print runs only after `load_structure()` returns**,
so a failed assert raises before the stats table appears. Small loss of CLI debug
visibility. *Task 8*

**W18-D33 · The `AdministrativeAgent` `rdf:type` triple is appended once per
facility** for a member administering several, inflating the insert batch with
identical duplicates. Pre-existing; harmless under Fluree set semantics. *Task 8*

**W18-D34 · The mirror bundle attachment ends with a trailing `---`** carried
over from the document's section separator. *Task 17*

**W18-D45 · The "no Postgres-owned attribute" test is a hardcoded six-name whitelist.**
*Task 8 · `validators/partition.py`* It cannot see a **new** leaked attribute
under a different name — this project's own *gate blind to its own population*
pattern. Brief-mandated, so not the implementer's defect, and flagged at the time
as a candidate for the final fix wave. Strengthening it means enumerating the
property rather than listing the names. The most substantive item on this list.

**W18-D43 · `is_connector` does not stop-word-check its left neighbour.**
*Task 1 · `generators/extract_facilities.py`* Measured latent — unobserved
across the 65-document corpus — but nothing stops a stop-word neighbour being
read as part of an institution name.

**W18-D44 · HANDOFF points a new reader at the wrong environment spellings.**
*Task 17 · `docs/HANDOFF.md`* It cites `.env.example`'s `CO_LENDER_PGHOST` /
`CO_LENDER_PGUSER` while this machine is configured from `~/.bashrc` under
`CO_LENDER_HOST` / `CO_LENDER_PG_USER`. `ccf/config.py:236-248` accepts both
spellings so a fresh setup works — but nothing tells a reader where the live
values actually come from, which is what makes `known-issues.md` §39's rotation
trap dangerous. Closing this one is worth more than its size suggests.

---

## Open — report accuracy, no code effect

These describe the wave's own reports and reviews, not the estate. Recorded
because the pattern is worth knowing: **implementer reports written from intent
rather than from the diff.** The whole-branch review suggested naming this to the
next wave's dispatch rather than fixing it retroactively.

- **W18-D35** *Task 1* — determinism evidence was a count ("0 rows differ"), not
  a named value pair. The re-reviewer confirmed the property by inspection; the
  code is correct.
- **W18-D36** *Task 2* — the RED evidence for the offset/newline bug is
  confounded: the brief's flat regex returns `[]` on that fixture because it is
  pipe-delimited, not because of the newline. The underlying claim is true and
  was isolated independently; only the account of *how* it was verified is wrong.
- **W18-D37** *Task 6* — `known-issues.md` lists `FAC-DFCB72`'s two offsets in
  two places. Redundant, not contradictory.
- **W18-D38** *Task 10* — the report's "files changed" list names
  `docs/ccf_dataprep_v2.md`, which the diff never touched, contradicting its own
  earlier line saying that file was left as-is.
- **W18-D39** *Task 12* — the pypdf byte-stability claim has no committed
  transcript, unlike the rest of that report's evidence sections. Immaterial:
  `DOCUMENT_ID` is a fixed literal and the upsert filters on it, never on
  `text_sha256`.
- **W18-D40** *Task 13* — the revert-to-green half of the content-probe
  falsification shows the probe re-passing but never displays the restored
  `rule_text` for `CLR-001`. Restoration asserted, not queried.
- **W18-D41** *Task 15* — the report says "8 new tests (5 verbatim, 3 added)";
  the diff has 7 (5 + 2), consistent with the 89→96 count. Narrative wrong,
  deliverable right.
- **W18-D42** *Task 16* — `precision_is_mixed`'s detail line double-counts the
  ledger literals: "99 peer cells … plus the peer ledger's literals" when the 99
  already includes them.

---

## Recorded and dismissed — not defects

Kept so they are not re-raised.

- **`main()` has no per-floor `try/except`** in `validators/syndicate.py`, so a
  `TypeError` would abort the run with no summary. Identical to
  `validators/aml_typology.py`, which the plan mandated modelling on exactly.
  House style. *Task 16*
- **`test_peer_writes_landed_in_the_peer_database` tests no writes.** True, and
  plan-mandated — the test is brief-verbatim. *Task 14*

---

## Related

- `docs/known-issues.md` §34–§44 — the estate-level limits, including the
  deleted `shares_reconcile` floor and its four causes, the empty-table hazard,
  the class the lineage population misses, the credential entanglement, and the
  planting-test crash window.
- `docs/backlog.md` — agreed, scoped, unscheduled work. Different thing: backlog
  items are *decided*, these are *deferred*.
- `docs/HANDOFF.md` — current state and what to do next.
