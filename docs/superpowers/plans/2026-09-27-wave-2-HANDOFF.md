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
| Offered "drop the storage version" as a candidate repair for A-F2 | proposed weakening an assertion I had just argued must not be weakened |
| Called the Gate-3 migration set "43 reds" from a two-directory run | reported a partial population's number as the whole |
| `git checkout --` on a dirty tree, wiping an uncommitted fix | used a destructive revert where an inverse edit was required — the exact trap already recorded here |

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

### Finding A-F2 — step 4 reddened two client-conformance nodes. RULED AND CLOSED.

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

**Dave ruled option 1, 2026-09-28: pin the instant.** Verbatim: *"Two serves at
two wall times must be two record versions. That is ruling 1 plus the canonical
rule you already shipped… The conformance leg's docstring already required 'the
same question at the same instant.' The fixture never did. The wave made that
visible; it did not invent a new identity rule."* And on the other two: *"2 is a
lie. Dropping the storage version hides a real difference and weakens
24.11-C-01. 3 is a reversal of ruling 1. Forbidden."*

Also ruled: threading the clock through the client adapter boot is **not a
test-only knob** — it is the same injected fabric clock as D6(d) / `D-IMPL-159`.

**Implemented and green at `b38f032e`.** `InProcessAdapter(address, *, clock=…)`
threads to `_boot` and on to `build_governed_resolver(admission_clock=…)`; the
default is the fabric's own clock, imported rather than restated. Both subjects
are composed against one now — the in-process one directly, the `mcp+stdio` child
through the environment, the one channel that reaches a separate process and one
its adapter already passes on deliberately. `tests/client`: **453 passed, 0
failed.** Two controls ship with it, one being the positive control for the
other: the channel's second spelling is held equal to the constant, and removing
the export turns the parity leg red.

---

## 11. Section H — the Gate-3 comparand migration set, CLASSIFIED

Dave ruled, 2026-09-28: *"H's comparand is not done. `served_at` on the refusal
record is not Gate 3's now… The 43 reds are the migration set, not a reason to
skip H. Classify them, migrate the fixtures that pin a fictional decision against
a live clock, then change the comparand."* H2 stays unnecessary; H1 stays as
shipped. This section is the classification. **The comparand is NOT changed yet**
and the tree is byte-for-byte as it was before the probe (digest verified).

### The population, corrected

**62 failed + 8 errors** on the **full non-example suite**
(`pytest tests/ --ignore=tests/examples`), against 8376 passed and 115 skipped.

My earlier report said "43 reds". That number was measured on
`tests/products` + `tests/replay` **only** — a narrower population than the one
the change actually reaches. 43 was not wrong about what it measured; it was
wrong as a statement about the migration set, which is 60 probe-caused nodes plus
8 errors across 22 modules.

### The cause, uniform across all 60

Gate 3 holds `now < expires_at <= now + MAX_TTL`. With `now = served_at` the
lower bound bites: every failure is a `ttl-refusal` / `ttl-bounds`, or a
`composite-child-refusal` / `child_admission` where a CHILD refused for that
reason. Measured shapes in the run: 23 assertions land on a `ttl-refusal`
envelope directly, 13 on `composite-child-refusal`.

**This is Gate 3 working, not fixture noise.** A product whose `expires_at`
already lies in the past at the moment it is handed over must not be served, and
that is precisely the gap `decided_at` could not see. The clearest instance is an
evidence-anchored class: with `ttl_anchor: from_entity_freshness`, `expires_at`
runs from an observation BEFORE the question, so a serving instant even minutes
later is past the expiry. `tests/products/test_cp05_canonical_path.py` fails
exactly there.

### Class 1 — no clock injected: a pinned question instant against a LIVE serving clock

**37 nodes, 15 modules.** These modules pass no `admission_clock`, so `served_at`
is the real wall clock while the question is pinned to a fictional instant. The
two diverge by months, so `expires_at` is always in the past.

*Migration shape:* inject a fabric clock consistent with the module's own pinned
question instant — the same seam `ccf.client.adapters.inprocess.InProcessAdapter`
just gained, and the same discipline the conformance suite already applies to
`as_of`. No fixture VALUE needs inventing: each module already declares the
instant it means.

- `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py` — 3
  - `test_a_crossed_question_is_caught_over_the_in_process_transport`
  - `test_an_absent_boundary_leaves_the_moved_instant_undetectable`
  - `test_an_altered_vessel_is_caught_over_the_in_process_transport`
- `tests/client/conformance/test_mcp_conformance.py` — 1
  - `test_the_decision_instant_is_auditable`
- `tests/client/conformance/test_the_suite_fires.py` — 1
  - `test_the_decision_instant_leg_fires_on_a_misreported_instant`
- `tests/client/test_inprocess_adapter.py` — 5
  - `test_a_first_ask_boots_the_fabric_and_returns_a_result`
  - `test_a_relative_and_absolute_root_are_one_cache_entry`
  - `test_an_explicit_as_of_reaches_the_deployment`
  - `test_the_wire_carries_exactly_the_canonical_bytes_of_the_vessel`
  - `test_two_clients_on_one_binding_share_one_fabric`
- `tests/client/test_mcp_stdio_adapter.py` — 1
  - `test_the_quoting_the_spaced_refusal_prescribes_actually_gets_past_the_grammar`
- `tests/deployment/test_replay_binding.py` — 4
  - `test_a_deployment_with_no_replay_section_is_untouched`
  - `test_a_served_products_record_lands_where_the_control_plane_said`
  - `test_an_explicit_record_class_wins_while_the_rest_stay_declared`
  - `test_the_landing_control_fires_on_a_store_rooted_anywhere_else`
- `tests/invariants/test_determination_authority_disclosure_delivery.py` — 1
  - `test_no_control_here_edits_the_real_source_tree`
- `tests/products/test_composite_integration.py` — 1
  - `test_int01b_a_real_L2_change_invalidates_the_NESTED_composite_chain`
- `tests/products/test_d_impl_338_refusal_evidence.py` — 1
  - `test_a_COMPOSITION_refusal_after_acquisition_keeps_the_childs_reported_identity`
- `tests/products/test_d_impl_339_child_contract_view.py` — 1
  - `test_an_invoked_child_that_refuses_admission_ALSO_blocks_projection`
- `tests/products/test_d_impl_342_child_question_retention.py` — 3
  - `test_c_b1_an_admitted_child_leaves_its_exact_question_on_the_parents_store`
  - `test_c_b6_replay_and_audit_need_neither_the_mapping_nor_the_producer`
  - `test_c_b7_other_bytes_at_the_address_are_a_divergence_on_both_replay_paths`
- `tests/products/test_d_impl_344_refusal_reconstruction.py` — 1
  - `test_case_8_an_optional_child_invoked_and_refused_blocks_and_reconstructs_as_optional`
- `tests/products/test_resolver_defaults.py` — 11
  - `test_an_explicit_scorer_overrides_the_default`
  - `test_the_data_only_construction_satisfies_every_assertion`
  - `test_the_default_is_selected_when_no_scorer_is_passed`
  - `test_the_default_reports_a_measured_number_rather_than_a_placeholder`
  - `test_the_half_life_artifact_moves_the_freshness_the_product_carries`
  - `test_the_half_life_control_fires_on_two_identical_numbers`
  - `test_the_half_life_control_fires_when_the_ordering_inverts`
  - `test_the_override_and_the_default_produce_different_products`
  - `test_the_override_control_fires_on_a_reference_produced_assessment`
  - `test_the_selection_control_fires_on_a_stale_pinned_version`
  - `test_the_selection_control_fires_when_the_default_is_made_inert`
- `tests/products/test_runtime_product_gate.py` — 1
  - `test_the_gate_never_runs_on_a_candidate_the_universal_gates_refused`
- `tests/replay/test_refusal_replay_record.py` — 2
  - `test_a_gate_refusal_records_the_state_it_actually_read`
  - `test_the_evidence_bundle_is_the_executions_own_facts`


### Class 2 — a clock IS injected, and the pinned serving instant is still past the expiry

**23 nodes, 7 modules.** These already pin `served_at` (the paved fixture's
`clock=lambda: ADMITTED_AT`, which is `ASKED_AT + 7 minutes`). The refusal is
therefore not an artifact of a live clock — it is the fixture's own premise being
incoherent under the correct comparand: a product with a 600-second window
anchored on evidence five minutes OLDER than the question has expired before the
seven-minute-later serve.

*Migration shape:* make each fixture's own arithmetic coherent — align the
serving gap with the declared window, or declare a window that survives it. Two
of these (`test_d_impl_341_ttl_anchor.py`) are the C11 pair already migrated once
this step and will need their instants restated a second time, which is expected:
they are the controls most tightly coupled to which instant governs.

- `tests/client/conformance/test_inprocess_conformance.py` — 1
  - `test_the_decision_instant_is_auditable`
- `tests/products/test_cp05_canonical_path.py` — 2
  - `test_the_canonical_path_serves_cp05s_declared_family`
  - `test_the_gate_seam_is_live_on_cp05s_path`
- `tests/products/test_d_impl_341_ttl_anchor.py` — 4
  - `test_c11_a_composites_mixing_floor_is_measured_from_the_evaluation_instant[breached-at-the-evaluation-instant]`
  - `test_c11_a_composites_mixing_floor_is_measured_from_the_evaluation_instant[met-at-the-evaluation-instant]`
  - `test_c6_evidence_older_than_the_window_refuses_ttl_bounds_naming_the_anchored_expiry`
  - `test_c8_an_evidence_anchored_composite_floors_on_its_anchor_and_its_children`
- `tests/products/test_d_impl_342_producer_refusal_evidence.py` — 2
  - `test_c_a2_an_admitted_child_carries_no_producer_refusal_and_its_reference_as_before`
  - `test_c_a4b_a_served_answer_rejected_inside_the_gate_carries_its_references_and_no_producer_refusal`
- `tests/products/test_delivery_determinism.py` — 1
  - `test_moving_served_at_across_the_effectivity_boundary_changes_the_determination`
- `tests/products/test_paved_consumer.py` — 9
  - `test_a_bumped_skill_beside_a_grant_in_force_is_refused_at_open_naming_both_versions`
  - `test_a_composite_is_served_with_its_child_admitted_from_declarations_alone`
  - `test_a_floor_below_the_served_lane_serves_and_the_served_lane_is_what_admission_holds`
  - `test_a_question_cannot_carry_an_instant_and_the_child_answers_the_composites`
  - `test_a_served_lane_below_the_composites_floor_is_refused_at_admission_with_the_reason`
  - `test_answer_admits_a_floor_bearing_request_the_way_resolve_admits_an_address`
  - `test_opening_twice_over_one_control_plane_serves_twice`
  - `test_the_build_children_hatch_composes_over_the_sdks_own_registrations`
  - `test_the_mapping_is_the_authority_on_the_subject_and_the_row_records_what_was_asked`
- `tests/products/test_resolver_seam.py` — 4
  - `test_a_gate_refusal_comes_back_as_an_envelope`
  - `test_a_gate_refusal_keeps_the_gates_own_typed_fields`
  - `test_a_gate_refusal_serves_nothing_and_records_everything`
  - `test_step5_a_refusal_reads_the_clock_once_and_NOW_records_served_at`


### Class 3 — base-existing, NOT in the migration set

**2 nodes.** Red at the accepted base `72bee6eb`, unrelated to the comparand, and
left alone by standing instruction.

- `tests/invariants/test_citation_coverage.py` — 1
  - `test_the_unanchored_python_citation_population_cannot_regrow`
- `tests/test_version_stamp.py` — 1
  - `test_the_installed_version_is_not_the_stale_literal_and_is_git_derived`


### What has to be true before the comparand moves

1. Every class-1 module injects a clock aligned with its pinned question instant.
2. Every class-2 fixture's window, anchor and serving gap are mutually coherent.
3. `tests/products/test_door_answer.py`'s 8 errors are resolved — they are ERRORS,
   not failures, so they are a fixture that stops constructing rather than an
   assertion that fails, and an error is never read as a pass.
4. Only then `now=served_at`, with the four `test_a_gate_refusal_*` controls in
   `test_resolver_seam.py` checked individually: three of them construct a
   DIFFERENT gate's refusal and would silently start measuring `ttl-bounds`
   instead of their own subject.
