# Wave 2 handoff — read this first

Written 2026-09-27 at Dave's instruction, to survive a cleared context. Nothing
here needs re-deriving; everything below was measured or ruled.

---

## 1. Where everything is, verified on origin

| ref | SHA | what it is |
| --- | --- | --- |
| `main` | **`51158a58`** | Wave 1 closed and merged. **The baseline.** |
| `wave-2-358` | **`8a9846fd`** | Wave 2 implementation branch. Steps 1 and 2(b) done. |
| `wave-2-358-sheet` | `35b7e118` | The accepted opening sheet, frozen. Do not amend. |
| `wave-1-357` | `121b5bcc` | Wave 1 candidate + gate entry. Merged. Historical. |
| `wave-1-357-record` | `b5534c36` | Wave 1's full working record and panel outputs. |

**Tags: 7, latest `v1.0.1`. No Wave 2 tag exists and none is authorized.**
All branches in sync with origin; no dirty tree anywhere.

**Worktrees:** `/home/parkave/ccf_wt/mainwt` (main), `/tmp/claude-1000/w2`
(`wave-2-358` — the working tree for this wave), `/tmp/claude-1000/w2sheet`
(the frozen sheet). `/home/parkave/ccf_code` itself sits on `wave-1-357`.
**`/tmp/claude-1000/*` does not survive a reboot — recreate with
`git worktree add`.**

---

## 2. What Wave 2 is

**`D-IMPL-358` — the fabric clock.** `SEC-008` + `SEC-010` + `SEC-011` as **one
integrated wave** with **separate acceptance criteria and dispositions per SEC
id**. The `SEC-019` rider is retained. `SEC-011` Gate 2 keeps its NOT-A-GAP
assembly-path-integrity disposition; the substantive repair is Gate 3.

The design of record is §4 of
`docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md`,
**reused not replaced**, with rulings D1–D13 locked at `D-IMPL-356`. The opening
sheet is `docs/superpowers/plans/2026-09-27-v1-0-2-wave-2-opening-sheet.md`.

**Read `D-IMPL-358` in `docs/DECISIONS.md` before touching anything.** It carries
all twelve rulings in full.

---

## 3. The locked sixteen-step sequence, and where we are

1. ✅ **DONE** — write `D-IMPL-358` with the twelve rulings plus D1–D13.
2. ⬅ **IN PROGRESS.** Build the in-tree census and write-fence support machinery
   **first**.
   - ✅ **2(b) write fence — DONE and pinned at `8a9846fd`.**
   - ⏳ **2(a) census instrument — AWAITING DAVE'S GO. This is the next action.**
3. Introduce `TemporalBoundaryPolicy` and its pinning. *(It does not exist —
   this is a creation.)*
4. Hoist and capture `served_at` **exactly once** on every governed serve.
   *(It does not exist either.)*
5. Thread `served_at` through effectivity, Gate 3, composite validity, refusals
   **and peering**.
6. Add replay `served_at` with historical-address preservation.
7. Fix the decision-instant debt control and **add its missing sabotage**.
8. Build the tenant-bound write guard **outside** the algorithmic worker; cover
   all four writer entries by proof or guard.
9. Migrate the red-when-fixed controls.
10. Run focused sabotage.
11. Run the disposable writer tests.
12. Run the read-only estate census.
13. **Only then** the example disposition and repair sitting.
14. Freeze the candidate.
15. Codex + Cursor + Gemini close panel.
16. **STOP for `D-GATE-358`.**

---

## 4. The next action, precisely

**Step 2(a): the in-tree census instrument.** Dave's ruling 8 — support
machinery under `D-IMPL-276`, not production mechanism. It must:

- read curated estates **only**;
- record **measured** before/after watermarks;
- classify **exact node ids**;
- distinguish **pass / fail / indeterminate** as three distinct states;
- refuse a malformed or missing result artifact;
- redact secrets **at generation time**;
- **never contain credentials.**

Dave: *"This time the qualification method must be reviewable from the
repository."* — the standing correction to Wave 1, whose instruments lived in an
unpreserved session workspace and are therefore gone.

**Do not start it without Dave's GO.** He said: *"Only after that is pinned: GO
for Step 2(a)."* 2(b) is now pinned, so the GO is what is awaited.

---

## 5. The twelve rulings, compressed

Full text in `D-IMPL-358`. Two of them **amend the accepted design** and must
never be quietly re-derived the other way.

1. **`served_at` is transparent-at-sentinel.** Absent preserves pre-1.0.2
   addresses; populated participates in the new address. Deliberately a
   **different mark** from `child_admitted_at`, which is `False`.
2. **AMENDS D6(d).** `D-IMPL-159` remains binding — algorithmic modules do not
   own the clock. The write guard goes at the **governed ingress/admission
   boundary**, not in `AssemblyWorker`. *"Do not weaken `D-IMPL-159` because
   existing code violates it."*
3. **Tenant comes from the ingress composition**, never the envelope, never a
   caller argument, never `resolve_latest` per envelope.
4. **All four write-capable entry points** get a disposition: `ingest` and
   `ingest_admitted` guarded on `ingestion_timestamp`; `admit_entity_claim` and
   `admit_relationship_claim` guarded on `observed_at` **or proved internal-only
   structurally**.
5. **An out-of-window write is a typed refusal before any write.** No fabricated
   replay record. Never restamp the envelope.
6. **Context Debt stays at the decision instant.** No wall clock in the scorer.
7. **The 32 undispositioned example trees** are neither implicitly frozen nor
   implicitly live. New red in `s1-01` = blocking; red in a frozen tree =
   ledgered; new red in an undispositioned tree = **stops the repair phase**.
   *"Do not mass-edit examples to manufacture a green estate run."*
8. **Census instrument in-tree** (see §4).
9. **AMENDS §4 by extension.** `PeeringAdmission.admit(now=)` joins the repair.
10. **Co-lender estate only when a close node actually reads it.**
11. **A missing policy refuses and records the required key + absence reason** —
    it never mints a fake binding.
12. **Write fence tightened** — done in 2(b).

**Two clarifications that constrain the diff:**
- Gate 3's inequality is **already two-sided**; only the **provenance of `now`**
  changes. *"Do not rewrite the check merely to make the diff look substantial."*
- The **five** refusal-recorder sites are **one** temporal-identity migration.
  *"Do not fix the named two and leave three clocks leaking into refusal
  identity."*

---

## 6. Measured facts that change the work — do not re-derive

- **`served_at` and `TemporalBoundaryPolicy` DO NOT EXIST** on the baseline.
  Both are creations. Consequence: refuse-when-undeclared names **all 38**
  example trees, not the design's "about 25".
- **Gate 3 is already two-sided** (`src/ccf/products/gates.py:1385-1386`), and
  `now` is already a required keyword.
- **The governed serve path reads exactly ONE clock**
  (`src/ccf/products/resolver.py:2633`) and it sits **inside**
  `if registered.requires:` — so non-composite serves read **none**.
- **The refusal-recorder conflation is FIVE sites, not one-plus-two.** Three are
  unnamed by the design; all three stamp a clock into a governed refusal's
  dimension-1 identity.
- **D8 ships with no control and no sabotage.** Measured: a wall-clock
  substitution in `FreshnessScorer.score` leaves the suite **153/153 green**.
- **The design's line citations are stale by 160–330 lines in the resolver.**
  Resolve every one by **symbol**.
- **`worker.py` is NOT byte-identical to v1.0.0**, contrary to the design's §1.3.
- **The writer never learns a tenant.** `AssemblyWorker.__init__` stores nothing
  tenant-shaped; `boot(tenant_ids=…)` holds the roster and does not pass it.
- **`ingest_admitted` has zero callers** in `src/` or `runtime/`.
- **Only ONE example tree is ruled live reference** (`s1-01`). `cp-00`…`cp-04`
  are frozen. **32 of 38 have no disposition.**
- **No census instrument exists in-tree.** That is what 2(a) builds.

---

## 7. Traps this project has already paid for

- **A PostgreSQL DSN has TWO serializations** — URI and libpq keyword form.
  Knowing one proves nothing about the other. A Wave 1 credential sweep that
  knew only the URI form reported "no DSN points at the estate" while a
  keyword-form DSN sat in a census log.
- **A same-length source mutation inside one mtime second loads STALE
  bytecode.** CPython validates a `.pyc` on `(mtime-seconds, size)` only. Every
  sabotage run must purge `__pycache__` **and** use `python -B` with
  `PYTHONDONTWRITEBYTECODE=1`.
- **Never redact a secret by its VALUE — redact by CONTEXT.** A value sweep on
  the 4-character password `test` rewrote 28,507 occurrences of ordinary text.
  And **no angle brackets in a placeholder** — one broke an XML census file
  silently for hours.
- **Never pipe a gate through `tail`** — you get the pager's exit code.
- **`passed` / `failed` / `errors` are three different numbers.** A collected
  test whose fixture raises is an ERROR, not a pass.
- **A grep count is not a call-site count.** `.py` only, exclude the `def` line,
  and check whether a hit is prose.
- **Two review seats must never share a worktree.**
- **`estate-env.sh` is never published.** It is the only remaining holder of the
  estate credential, mode 0600, git-ignored.
- **A worktree created fresh has no `.venv`** — use
  `/home/parkave/ccf_code/.venv/bin/python` explicitly.

---

## 8. My error record this session, kept because Dave asked for it

Dave, 2026-09-27: *"You are making too many mistakes."* That is accurate and the
pattern is worth carrying rather than forgetting.

**What I got wrong, and the shape of it:**

| error | shape |
| --- | --- |
| A brief named `SpecDrivenEntityResolution._identity_of`, which does not exist | asserted a symbol without checking it |
| A brief's own code carried literal invisible characters while instructing escapes | did not read my own output |
| Two mandated controls called `refuse_request`, which never calls `refuse_floor` — vacuous by construction | wrote a test without running it |
| `str(value)` replaced shadow-proof `str.strip(value)` while the docstring claimed the opposite | reasoned about a mechanism instead of testing it |
| A category sweep asserted `leaked == []` when U+0020 is `Zs` and admitted by design | did not run my own control |
| Measured the floor's population three times, wrong twice | measured the data instead of the mechanism |
| Invented a port policy in the write fence that nobody ruled | narrowed a protection while calling it precision |
| Reported step 2(b) as landed while it was local only | treated my own work as evidence before pushing |

**The common thread:** confident first-pass output on specifications and
measurements that had not been executed. **The counter-discipline that works,
and it is already proven here:** run the thing; name the population beside the
number; state which serialization/tree/branch was measured; push before
claiming; and let a reviewer or a severing try to falsify it before reporting it.

Every one of these was caught — by a review seat, by a severing, by the
project's own lint, or by Dave. The machinery works. The fix is to run it
earlier, not to trust the first draft more.

---

## 9. Standing prohibitions

No Wave 3. No tag. No Wave 1 repair. No adapter implementation. No HITL
implementation. No erasure code. No frozen-server migration. No release
qualification. **No SEC identifier closes merely because its implementation task
turns green.** No merge to `main` without a gate ruling.

**Wave 1's eight residuals are launch posture, not a cleanup queue**, and the
base-existing `docs/surface/examples/RETIREMENT-COUPLINGS.md` freshness failure
is **left alone** (verified red at the wave base `00fde747`).
