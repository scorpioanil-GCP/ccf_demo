# STATE, 2026-10-02 — Wave 2 CLOSED and MERGED. Sitting A is OPEN as a disposition sitting.

> Written at Dave's instruction so his context can be cleared. **Read this file in full
> before doing anything.** It is the handoff; the Wave 2 handoff
> (`2026-09-27-wave-2-HANDOFF.md`) is the history behind it and is still accurate for
> steps 1–16.

---

## 1. Pins — verify these FIRST, from the tree, before trusting anything below

| ref | SHA |
| --- | --- |
| `main` = `origin/main` | **verify from the tree.** It moves every time this file is amended, so no SHA here can be current. The behaviour candidate below is the pin that must NOT move. |
| the Wave 2 merge commit | `5f296156401258bc268d12bb6de00f9411b4724a` |
| `wave-2-358` (closed, merged, do not move) | `d431af05efb2a9843785a4899cd72de745646672` |
| behaviour candidate (`src/`+`runtime/` frozen at this) | `9926f594e1c01b1edda368ad5efefe3c9024f85d` |
| frozen opening sheet | `35b7e118ab190d23736ca06da77faaf36b452c21` |
| estate write fence | `8a9846fddc4309ffa7c2b04dc8228e55378a1555` |
| newest tag (unchanged all wave) | `v1.0.1` at `a4cf2fb7` |

`git diff --name-only 9926f594 main -- src/ runtime/` must still be **empty**. If it is
not, something landed that this file does not describe.

**Worktrees.** `/home/parkave/ccf_wt/mainwt` is on `main` and is where the last commits
were made (it has no `.venv`; use `/home/parkave/ccf_wt/qual-a4cf2fb7/.venv/bin/python`).
`/tmp/claude-1000/w2` is on `wave-2-358`. `/tmp/claude-1000/w2-base-51158a58` is a
detached base worktree with `tools/estate_census` grafted in (untracked).

**Always** run python as `PYTHONPATH=.:src:runtime <venv>/bin/python -B` **from the
worktree you mean**. The editable install resolves `ccf` elsewhere otherwise.

---

## 2. What is CLOSED

- **Wave 2 (`D-IMPL-358`), the fabric clock.** `D-GATE-358` is APPROVED (entry in
  `docs/DECISIONS.md`, one dense line, `**D-GATE-358`) and MERGED `--no-ff` at
  `5f296156`. Amended twice, both verbatim from Dave: the gate entry carries an
  `AMENDMENT 2026-10-01` recording the merge and the declined tag; close-panel finding 10
  carries an `AMENDMENT 2026-10-02`.
- **The tag is DECLINED, not pending.** Reason, Dave's: `v1.0.1` is a qualification
  record; Wave 2 closed no SEC identifier and did not re-derive the suite counts;
  `v1.0.2` would read as `v1.0.1` reads and the entry's disclaimers would not travel with
  a tag; a non-version marker is not required to keep the tree. **Do not cut a tag.**
- **Sitting B (close-panel finding 10)** — done as a record correction. Coverage is
  closed and pinned at three classification sites in
  `examples/s1-00-companies-over-revenue/scenario/provision.py`: `:68` supplied branch,
  `:94` container branch (both from `f491edab`), `:120` first statement of `seed()` (from
  `a084e094`). `tests/examples/test_s1_00_provision_write_fence.py` pins both branches.
  **Finding 10 stays OPEN as a SCOPE statement only**: the classifier is
  curated-roster-scoped (`CCF_CURATED_ESTATE_HOSTS`, default `192.168.4.76`), so docker
  configuration this repository does not bound can yield a non-curated remote
  destination. **A loopback-only rule is NOT proposed.**

**No SEC identifier is closed. The ledger stays 7 of 29.** Closed: `SEC-001`, `SEC-003`
(Tier 0); `SEC-002`, `SEC-004`, `SEC-012`, `SEC-016`, `SEC-018` (Tier 1). `SEC-008`,
`SEC-010` and `SEC-011` had Wave 2's engineering done and were deliberately **not**
closed.

---

## 3. What is OPEN right now: SITTING A, and it is a DISPOSITION sitting

Dave opened A on 2026-10-02. **A is not "write fifteen declarations".** Ruling 7 governs:
**disposition first, repair second.** Dave has corrected this exact over-reach three
times across the wave.

### 3.1 The mechanism, measured on `1b7a71dc` and CONFIRMED by Dave

`src/ccf/products/resolver.py:3073` sets `anchored_at` to the resolved TTL anchor, or to
`decided_at` when the resolution is not a `TTLAnchorResolution`. `:3193` sets a
non-composite `expires_at = anchored_at + product_ttl_seconds`. Gate 3 at `:3328` passes
`now=served_at`.

**Consequence: a `temporal_boundary:` declaration alone removes
`temporal-boundary-undeclared` and leaves expiry judged at the SERVE instant against a
DECISION-anchored bound.** That is the wall `s1-01` hit — declaring took its
`temporal-boundary-undeclared` refusals 38 → 0 and left all 43 nodes red on
`ttl-refusal / ttl-bounds`. `s1-01` needed a **second act**: two harness-composed
simulation periods through the SDK's `admission_clock` seam. So **"one declaration each"
is true and insufficient**, and Dave has agreed that it is.

### 3.2 The roster, measured on `1b7a71dc`. THE LEDGER NAMES 15; THE TREE HAS 16.

| trees | `ccf_config.yaml` | `ccf_environment.yaml` | count |
| --- | --- | --- | --- |
| `cp-03-canonical`, `cp-04-canonical`, `cp-06-canonical`, `cp-13-canonical`, `cp-15`, `cp-16`, `cp-17`, `cp-18`, `cp-19`, `cp-21`, `cp-23`, `cp-24`, `dr-02` | root | root | **13** |
| `hw1-companies-over-revenue` | **`deployment/ccf_config.yaml`** (nested) | none | 1 |
| `cp-22-agent-internal-assembly` | neither | neither | 1 |
| `hw1-harness-clients` | neither | neither | 1 |

**Two open roster questions, neither settled:**

1. **`hw1` in the ledger row is AMBIGUOUS.** It was derived from
   `test_hw1_empty_fabric_refusal.py` and `test_hw1_two_transports.py`, and there are TWO
   `hw1-*` trees. Which tree the row means has never been established. Resolve the name
   before giving it an answer.
2. **Dave's own enumeration said "twelve" while listing thirteen.** The tree says
   thirteen. This was raised and not yet ruled.

**AMENDMENT 2026-10-02, after §3.2 was written.** Both roster questions are RULED by
Dave. The count is **thirteen** paved pairs — his earlier "twelve" was a miscount of his
own thirteen-item list. The ledger's `hw1` means **`hw1-companies-over-revenue`**:
`tests/examples/test_hw1_empty_fabric_refusal.py:73` imports `EXAMPLE_ROOT` from
`test_hw1_two_transports`, which sets it at `:90` to `CLIENT_EXAMPLE_ROOTS[0]`, the first
key of `PERMITTED_IMPORTS`, measured as `examples/hw1-companies-over-revenue`.
`hw1-harness-clients` is the SECOND key, its own test modules
(`test_hw1_harness_clients_no_model.py`, `_readme.py`, `_retirement.py`) are absent from
`SEC358-G-01`'s new-red set, and it is **OUTSIDE this sitting**. So the roster is **13
paved pairs + `hw1-companies-over-revenue` (nested `deployment/ccf_config.yaml`, no
`ccf_environment.yaml`) + `cp-22-agent-internal-assembly` (neither) = 15 names, 15 owed
trees.** Sixteen directories exist; the sixteenth is not owed by this row. **The sentences
in §3.2 calling these two questions unsettled, and its "15 names cover 16 trees" framing,
were true when written and are false after this ruling — and so is §3.4's "`hw1` needs
its name resolved first".** Nothing else changes: the paved/nested/neither split in §3.2
is as measured, and every other question in §3.4 is still open.

### 3.3 What has NOT been measured, and must not be inferred

**Whether each tree's decision instant is HISTORICAL.** Dave's instruction, verbatim:
*"Whether each decision instant is historical was not re-measured here. Do not write
thirteen declarations on that inference."* The `CCF_CP_*` trees read a point-in-time
estate, which SUGGESTS it. Suggestion is exactly what this session's errors were made of.

### 3.4 The per-tree row A needs before any declaration lands

For each tree: **paved or not · decision instant historical or not · therefore one act or
two.** `cp-22` needs its own answer (no config at all). `hw1` needs its name resolved
first. **Service periods are NOT invented** — `s1-01`'s two were given by Dave
(2026-08-01T00:05:00Z, 2026-09-15T00:05:00Z).

### 3.5 The `s1-01` pattern, if and when a repair is authorised

Two artifacts and two code seams, all inside one tree:
`artifacts/temporal-boundary.yaml` (bare typed contract — **no `semver` key**, it is a
`CCFContract` with `extra=forbid`); one `manifest.yaml` entry with
`key: ccf.temporal-boundary-policy` (**the key is NOT free vocabulary** — the resolver
looks under `<tenant_id>/ccf.temporal-boundary-policy` and the loader places manifest
keys under the tenant); a `simulation_clock:` block in the harness's own questions
document; and the instant threaded to `build_governed_resolver(admission_clock=…)`. The
clock is **composition state and never read off a request**.

---

## 4. CARRIED. Named, not a queue. Nothing here is authorised.

- **The fifteen (sixteen) trees** — `SEC358-G-01` 263 nodes, `SEC358-G-02` 14, disjoint,
  277 total. `NOT-A-GAP` under the `D-IMPL-261` charter, which means *correct SDK
  behaviour / example defect* and **NOT** "no work owed".
  Ledger: `docs/D-IMPL-358-EXAMPLES-GAP-LEDGER.md`.
- **Close-panel findings 1–8 and 10** — `docs/D-IMPL-358-CLOSE-REVIEWS.md`. The two that
  touch named invariants: **`TemporalWriteRefused` is absent from `SDK_SEAM_REFUSALS`**,
  so the step-8 ingress refusal escapes with no replay record (audit-by-construction);
  and the **peered-child branch of the composite resolver has never executed**, which is
  the named missing Peer proof.
- **`TOKEN_*` on `cp-15`, `cp-16`, `cp-18`, `cp-21`, `cp-23`, `cp-24`** — test gates
  narrower than `open_product` requires, so a gate-satisfying environment makes those
  modules ERROR instead of skip.
- **Wave 1's eight residuals**, verbatim.
- **Citation coverage ratchet at 365** against ceiling 0. Every citation added this wave
  in line-number form was converted to `path.py::Symbol` per `D-IMPL-114` rather than
  raising the constant. **Do not raise it.**
- **`docs/surface/examples/RETIREMENT-COUPLINGS.md`** freshness — `test_retirement_sweep`
  is a standing red.

Standing reds in the non-example suite at the candidate: `test_citation_coverage` and
`test_version_stamp`, both base-existing.

---

## 5. NOT AUTHORISED. Do not start any of these without a new ruling.

No Wave 3 · no release qualification · no tag (declined, not deferred) · no repair of the
fifteen trees, Gate 3, `resolver.py`, the worker, Peer, `TOKEN_*`, the clock detector or
`SDK_SEAM_REFUSALS` · no SEC identifier closed · no example edit outside an authorised
sitting · **no connection to `192.168.4.76` of any kind** (see §6).

Other named sittings Dave has scoped but NOT opened: **C** (`SDK_SEAM_REFUSALS` +
peered-child execution — SDK surface, no example edits) and **D** (SEC-008/010/011
disposition — *acceptance criteria first, no code until those are written*).

---

## 6. TRAPS THIS SESSION PAID FOR. Read before measuring anything.

- **`.76` IS READ-ONLY AND WAS BREACHED ON 2026-10-01.** Probing whether `seed()` was
  fenced, this session called it with a curated DSN and `psycopg` attempted an outbound
  connection to the curated host. No write occurred. **It was unnecessary** — the missing
  fence call was visible in the source, already read. Recorded in gate clause (7) and in
  `a084e094`. **Prove fences with a string and a mock.** `call_count == 0` separates *the
  guard stopped it* from *something later stopped it*.
- **Never write a present-tense status sentence into a dated record.** `D-GATE-358` went
  stale three times this way (pre-push tip; a four-category sentence that dropped
  `examples/.../provision.py`; `NOT MERGED` after the merge). The fix is an **AMENDMENT
  that dates the falsification and names the CLASS** of sentences it supersedes — never a
  rewrite of the original.
- **`python -m tools.lints` with no args exits 0 having checked NOTHING.** It needs
  `--all`.
- **`git stash` does not stash untracked files.** A with/without comparison that leaves a
  new file in place returns equal numbers that mean nothing. Move the file.
- **`make` returns 2 on a failed recipe; the gate itself returns 1.** Two numbers. Report
  both.
- **Read tree roots AND subdirectories.** `hw1-companies-over-revenue`'s config is at
  `deployment/ccf_config.yaml`; a root-only glob missed it.
- **A matching count is not a matching roster.** On the estate census, base and candidate
  both had 12 failures in three modules and the node-id sets were identical — that had to
  be diffed, not compared by count.
- **`cp-03-canonical` / `cp-04-canonical` are NOT the frozen `cp-03` / `cp-04`
  specimens.** Conflating them on a filename prefix mis-files 18 nodes into the frozen
  bucket. The frozen family owes nothing: 558 of its nodes ran with byte-identical
  outcome distributions on both sides of the census.
- **Background jobs**: a full non-example suite run takes ~10.5 min and must go in the
  background; the estate census over `tests/examples` exceeds a 520s cap and needs
  chunking. **Delete a census bundle before capturing**: on timeout, `capture` leaves the
  previous bundle intact and exits 1, and a later `classify` would read it as this run's.
- **The census classifier cannot currently classify a whole-tree capture** —
  `find_credential` re-flags `redact_text`'s own `***`. Zero of `tests/examples`' node ids
  are affected, so an estate-scoped census is fine.

---

## 7. MY ERROR RECORD, kept because it is the reason this file exists

24 on the branch: 12 in the in-tree Wave 2 handoff §8, 12 more after it. Of the later 12,
Dave caught **six**: a conflated `make`/gate exit code; claiming both s1-00 DSN variables
were checked when the recipe forwards one; a `provision.py` path missing its `scenario/`
segment; aiming an amendment at the gap ledger when finding 10 lives in the close-reviews
file; dating the container-branch coverage one commit late; and filing `hw1` as one tree
when it is two.

**The pattern is one thing: writing the sentence from what I had just done rather than
from what I had already established.** The counter-discipline that worked: run it; name
the population beside the number; state which tree and which commit was measured; push
before claiming; and let a severing or a reviewer try to falsify it first.

---

## 8. THE NEXT ACTION, precisely

**Nothing is authorised to edit.** A is open as a disposition sitting and the next act is
Dave ruling the per-tree row of §3.4 — starting with the two unsettled roster questions
in §3.2 (which `hw1`; thirteen vs twelve) and the unmeasured question in §3.3 (which
decision instants are historical).

Do not write a declaration. Do not invent a service period. Do not touch `cp-22` or
either `hw1` tree. Do not open C or D.
