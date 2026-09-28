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
2. ✅ **DONE.** The in-tree census and write-fence support machinery.
   - ✅ **2(b) write fence — pinned at `8a9846fd`.**
   - ✅ **2(a) census instrument — `f7f55468`, plus the generation-time
     redaction repair at `ec627325`.**
3. ✅ **DONE — `d50f9bf3`.** `TemporalBoundaryPolicy` and its pinning.
4. ✅ **DONE — `78420ece`.** `served_at` hoisted and captured exactly once per
   governed serve. **Carries one measured regression — see §10.**
5. ⬅ **IN PROGRESS.** Thread `served_at` through effectivity, Gate 3, composite
   validity, refusals **and peering**.
   - ✅ areas 3 and 6 (refusal vocabulary; refusal temporal identity across five
     recorder families).
   - ✅ area 1 (policy effectivity at `served_at` in all three layers) —
     `72bee6eb`, accepted.
   - ✅ **section A — the config authoring surface** (see §10).
   - ⏳ sections B–T: areas 2, 4, 5, 7, 8; live enforcement; the severing ledger.
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
| Reported step 4 complete while it reddened two client-conformance nodes | measured the changed population, not the dependent one |

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

---

## 10. Step 5 section A — the config authoring surface, and two findings

### What landed

`ccf.temporal-boundary-policy` is **manifest-addressable** and `ccf_config.yaml`
gains a reserved `temporal_boundary:` section. This is what makes ruling 11
livable: a rule that refuses every undeclared deployment needs somewhere for the
declaration to be written, and the alternative was weakening the rule. Dave's
ruling was explicit — *"There is no exception to ruling 11 … Do not weaken the
temporal rule to avoid adding this authoring surface."*

Mechanically new: a third reserved-section derivation bucket,
`_RESERVED_BARE_TYPED_SECTIONS` — typed, body verbatim, **no injected `semver`**,
because the step-3 contract declares no semantic version and inventing one would
put a value in the document that the contract does not have. The existing two
buckets are untouched and every existing reserved section still derives
byte-for-byte as before.

Verified end to end: `ccf_config.yaml` → `DeploymentConfig` → `derive_deployment`
→ manifest + document → `load_config_and_boot` → Control Plane registration →
`resolve_temporal_boundary` → `PinnedTemporalBoundary` → `.binding ==
PolicyBinding(key, registered_version)`.

**The key is derived, never authored.** It is always
`temporal_boundary_policy_key(tenant_id=config.tenant_id)`; stating `key`,
`class_id`, `role` or `registration` inside the section is refused **by name**
rather than ignored or honored, and a section present with no top-level
`tenant_id` is refused rather than given an invented tenant or a class-only key.

### A10 — the examples fact, RECORDED not fixed

**A config-driven example that declares no `temporal_boundary:` will refuse every
question once enforcement lands** (the remainder of step 5), because ruling 11
admits no exception and absence means *undeclared* — not unbounded. Nothing is
repaired here and no example is edited: the examples were not mass-edited, by
ruling, and **their disposition is steps 12 and 13.** Recorded now so that the
first red example in step 13 is a known consequence rather than a discovery.

The fixture configs that had to keep exercising their own subject were given an
explicit, deliberately **wide** boundary instead: `tests/client/fixtures/deployment/ccf_config.yaml`
and the two paved-road builders in `tests/products/paved_fixture.py`. Those
numbers are **fixture values, authored in the documents** — there is no constant
in `src/`, and the SDK still supplies no duration default. Producer and consumer
are separate tenants and each declares its own bound; measured, they derive two
different keys (`paved-child-tenant/…` and `replay-binding-fixture-tenant/…`), so
a consumer's declaration cannot authorize a producer's.

### Finding A-F1 — `ccf.entity-invalidation-register` is addressable by no manifest

Measured while choosing how to satisfy `tests/deployment/test_class_lookup.py`.
The control takes `ccf.controlplane.artifacts` as its source of truth for *"the
real constant"*; widening it to walk the whole `ccf.controlplane` package finds
**21** artifact classes, one of which —
`ccf.controlplane.invalidation.ENTITY_INVALIDATION_REGISTER` — is in **neither**
`SDK_ARTIFACT_CLASSES` nor `SDK_VERSIONED_ARTIFACT_CLASSES`. By the control's own
charter (b), *"an SDK artifact class that a manifest cannot address is a class no
adopter can register."*

**Not fixed here.** Widening the population would turn a green control red on
code this step does not own, and manifest-addressability for that class is a
ruling, not a cleanup. The narrow repair was taken instead: the temporal-boundary
constant is exposed from `ccf.controlplane.artifacts`, following `RESOLUTION_SPEC`,
whose contract likewise lives in another module.

### Finding A-F2 — step 4 reddened two client-conformance nodes. BLOCKER, needs a ruling.

Bisected, not inferred:

| commit | `test_mcp_conformance.py::test_served_parity` |
| --- | --- |
| `8a9846fd` (wave 2 fence) | **passed** |
| `d50f9bf3` (step 3) | **passed** |
| `78420ece` (step 4) | **failed** |
| `72bee6eb` (area 1, accepted) | **failed** |

Also red: `tests/client/conformance/test_the_suite_fires.py::test_two_honest_subjects_agree`.
Section A did **not** cause either; both are red at `72bee6eb` with no Section-A
work present.

**The mechanism.** `served_at` is marked `HASH_TRANSPARENT_KEY: True`, and
`ccf/contracts/canonical.py` states the semantics in Dave's own words: *"Any
non-sentinel value is rendered and must move the hash."* A populated `served_at`
is therefore inside the replay record's content hash, so **two serves of one
question at two wall-clock instants produce two record versions.** The leg
compares every declared field of `Result` across transports, `replay_ref` among
them.

**What actually disagrees is narrower than the failure reads.** The record's name
is byte-identical across transports (`5b1bce07…`); only the trailing `@version`
differs. The transports agree on the **determination identity** and disagree on
the **stored record's content hash** — the distinction this project already ruled
at `24.11-C-01`.

**Why I am not picking a repair.** The leg's own docstring says *"The same
question **at the same instant** answers identically everywhere"* — a condition
its fixture does not establish. `build_governed_resolver` takes an injectable
`admission_clock`, but the conformance subjects boot through
`ccf.client.adapters.inprocess::_boot`, which takes only a `BindingDocument`, and
one subject is a **separate process**, so no monkeypatch reaches it. The three
candidate repairs are all rulings, not plumbing:

1. **Pin the instant** — thread a clock through the client adapter's boot. Honest
   and matches the docstring, but adds an SDK client-surface parameter whose only
   consumer is a test.
2. **Compare the determination identity** — keep comparing the product's content
   address and the record's name; stop comparing the record's storage version.
   Defensible under `24.11-C-01`, but it narrows a load-bearing assertion, and
   this project refuses that move everywhere else.
3. **Move `served_at` off the hashed record** — contradicts ruling 1 and
   `D-IMPL-243` amendment 1.

Per CLAUDE.md §15 this is a `D-IMPL` question, so it is surfaced rather than
defaulted. **Step 5 cannot be reported complete while it stands.**
