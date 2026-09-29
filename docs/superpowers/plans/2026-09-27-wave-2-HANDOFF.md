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

---

## 12. Section H closed — every tracked node, to its final result

Dave, 2026-09-28: *"List all eight `test_door_answer.py` setup-error node IDs
alongside the 60 migration failure nodes. Track each to its final result. Keep the
two baseline failures separate, and report skipped or otherwise unexecuted checks
explicitly."*

**Commits, in the ruled order:** classes 1 and 2 at `416fa420`, the comparand at
`2ee67428`. The comparand was NOT moved before the migration.

**Verification of this table:** the 68 node ids below were run as an explicit node
list — `pytest <68 ids> -rA` — which reports a per-node outcome and errors on an id
that does not resolve. Result: **68 passed, 0 failed, 0 errors, 0 skipped, 0
xfailed, 0 xpassed.** Nothing in this population was unexecuted; a mistyped or
renamed id would have failed the run rather than silently dropping out of it.

**A correction to the class labels, and the roster is unaffected.** My class
assignment came from scanning each module's own text for a clock, which mis-files
any module whose clock arrives through an imported helper — measured on the
composite family and on `test_paved_consumer.py`. The node ROSTER is what the
migration was allowed to use and it is unchanged; the labels below are as
originally recorded, marked `1*` where the module in fact inherits a pinned clock
and so behaved as class 2. The distinction changed the shape of each repair, never
which nodes were in scope.

**`tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py`** — 3 tracked, failures
- [x] `test_a_crossed_question_is_caught_over_the_in_process_transport` — class 1 → **passes**
- [x] `test_an_absent_boundary_leaves_the_moved_instant_undetectable` — class 1 → **passes**
- [x] `test_an_altered_vessel_is_caught_over_the_in_process_transport` — class 1 → **passes**

**`tests/client/conformance/test_inprocess_conformance.py`** — 1 tracked, failures
- [x] `test_the_decision_instant_is_auditable` — class 2 → **passes**

**`tests/client/conformance/test_mcp_conformance.py`** — 1 tracked, failures
- [x] `test_the_decision_instant_is_auditable` — class 1 → **passes**

**`tests/client/conformance/test_the_suite_fires.py`** — 1 tracked, failures
- [x] `test_the_decision_instant_leg_fires_on_a_misreported_instant` — class 1 → **passes**

**`tests/client/test_inprocess_adapter.py`** — 5 tracked, failures
- [x] `test_a_first_ask_boots_the_fabric_and_returns_a_result` — class 1 → **passes**
- [x] `test_a_relative_and_absolute_root_are_one_cache_entry` — class 1 → **passes**
- [x] `test_an_explicit_as_of_reaches_the_deployment` — class 1 → **passes**
- [x] `test_the_wire_carries_exactly_the_canonical_bytes_of_the_vessel` — class 1 → **passes**
- [x] `test_two_clients_on_one_binding_share_one_fabric` — class 1 → **passes**

**`tests/client/test_mcp_stdio_adapter.py`** — 1 tracked, failures
- [x] `test_the_quoting_the_spaced_refusal_prescribes_actually_gets_past_the_grammar` — class 1 → **passes**

**`tests/deployment/test_replay_binding.py`** — 4 tracked, failures
- [x] `test_a_deployment_with_no_replay_section_is_untouched` — class 1 → **passes**
- [x] `test_a_served_products_record_lands_where_the_control_plane_said` — class 1 → **passes**
- [x] `test_an_explicit_record_class_wins_while_the_rest_stay_declared` — class 1 → **passes**
- [x] `test_the_landing_control_fires_on_a_store_rooted_anywhere_else` — class 1 → **passes**

**`tests/invariants/test_determination_authority_disclosure_delivery.py`** — 1 tracked, failures
- [x] `test_no_control_here_edits_the_real_source_tree` — class 1 → **passes**

**`tests/products/test_composite_integration.py`** — 1 tracked, failures
- [x] `test_int01b_a_real_L2_change_invalidates_the_NESTED_composite_chain` — class 1 → **passes**

**`tests/products/test_cp05_canonical_path.py`** — 2 tracked, failures
- [x] `test_the_canonical_path_serves_cp05s_declared_family` — class 2 → **passes**
- [x] `test_the_gate_seam_is_live_on_cp05s_path` — class 2 → **passes**

**`tests/products/test_d_impl_338_refusal_evidence.py`** — 1 tracked, failures
- [x] `test_a_COMPOSITION_refusal_after_acquisition_keeps_the_childs_reported_identity` — class 1 → **passes**

**`tests/products/test_d_impl_339_child_contract_view.py`** — 1 tracked, failures
- [x] `test_an_invoked_child_that_refuses_admission_ALSO_blocks_projection` — class 1 → **passes**

**`tests/products/test_d_impl_341_ttl_anchor.py`** — 4 tracked, failures
- [x] `test_c11_a_composites_mixing_floor_is_measured_from_the_evaluation_instant[breached-at-the-evaluation-instant]` — class 2 → **passes**
- [x] `test_c11_a_composites_mixing_floor_is_measured_from_the_evaluation_instant[met-at-the-evaluation-instant]` — class 2 → **passes**
- [x] `test_c6_evidence_older_than_the_window_refuses_ttl_bounds_naming_the_anchored_expiry` — class 2 → **passes**
- [x] `test_c8_an_evidence_anchored_composite_floors_on_its_anchor_and_its_children` — class 2 → **passes**

**`tests/products/test_d_impl_342_child_question_retention.py`** — 3 tracked, failures
- [x] `test_c_b1_an_admitted_child_leaves_its_exact_question_on_the_parents_store` — class 1 → **passes**
- [x] `test_c_b6_replay_and_audit_need_neither_the_mapping_nor_the_producer` — class 1 → **passes**
- [x] `test_c_b7_other_bytes_at_the_address_are_a_divergence_on_both_replay_paths` — class 1 → **passes**

**`tests/products/test_d_impl_342_producer_refusal_evidence.py`** — 2 tracked, failures
- [x] `test_c_a2_an_admitted_child_carries_no_producer_refusal_and_its_reference_as_before` — class 2 → **passes**
- [x] `test_c_a4b_a_served_answer_rejected_inside_the_gate_carries_its_references_and_no_producer_refusal` — class 2 → **passes**

**`tests/products/test_d_impl_344_refusal_reconstruction.py`** — 1 tracked, failures
- [x] `test_case_8_an_optional_child_invoked_and_refused_blocks_and_reconstructs_as_optional` — class 1 → **passes**

**`tests/products/test_delivery_determinism.py`** — 1 tracked, failures
- [x] `test_moving_served_at_across_the_effectivity_boundary_changes_the_determination` — class 2 → **passes**

**`tests/products/test_door_answer.py`** — 8 tracked, errors
- [x] `test_a_single_space_inside_the_vessel_breaks_the_address_it_claims` — class 1* → **passes**
- [x] `test_an_absent_boundary_is_echoed_absent_though_the_door_answered_at_one` — class 1* → **passes**
- [x] `test_an_explicit_boundary_is_echoed_as_that_boundary` — class 1* → **passes**
- [x] `test_control_a_sabotaged_door_makes_the_address_assertion_raise[claims-a-constant]` — class 1* → **passes**
- [x] `test_control_a_sabotaged_door_makes_the_address_assertion_raise[hashes-a-second-rendering]` — class 1* → **passes**
- [x] `test_control_the_resolved_instant_witness_fires_when_the_echo_carries_it` — class 1* → **passes**
- [x] `test_the_claimed_address_is_sha256_of_the_vessel_beside_it` — class 1* → **passes**
- [x] `test_the_echo_is_the_whole_question_and_not_a_projection_of_it` — class 1* → **passes**

**`tests/products/test_paved_consumer.py`** — 9 tracked, failures
- [x] `test_a_bumped_skill_beside_a_grant_in_force_is_refused_at_open_naming_both_versions` — class 2 → **passes**
- [x] `test_a_composite_is_served_with_its_child_admitted_from_declarations_alone` — class 2 → **passes**
- [x] `test_a_floor_below_the_served_lane_serves_and_the_served_lane_is_what_admission_holds` — class 2 → **passes**
- [x] `test_a_question_cannot_carry_an_instant_and_the_child_answers_the_composites` — class 2 → **passes**
- [x] `test_a_served_lane_below_the_composites_floor_is_refused_at_admission_with_the_reason` — class 2 → **passes**
- [x] `test_answer_admits_a_floor_bearing_request_the_way_resolve_admits_an_address` — class 2 → **passes**
- [x] `test_opening_twice_over_one_control_plane_serves_twice` — class 2 → **passes**
- [x] `test_the_build_children_hatch_composes_over_the_sdks_own_registrations` — class 2 → **passes**
- [x] `test_the_mapping_is_the_authority_on_the_subject_and_the_row_records_what_was_asked` — class 2 → **passes**

**`tests/products/test_resolver_defaults.py`** — 11 tracked, failures
- [x] `test_an_explicit_scorer_overrides_the_default` — class 1 → **passes**
- [x] `test_the_data_only_construction_satisfies_every_assertion` — class 1 → **passes**
- [x] `test_the_default_is_selected_when_no_scorer_is_passed` — class 1 → **passes**
- [x] `test_the_default_reports_a_measured_number_rather_than_a_placeholder` — class 1 → **passes**
- [x] `test_the_half_life_artifact_moves_the_freshness_the_product_carries` — class 1 → **passes**
- [x] `test_the_half_life_control_fires_on_two_identical_numbers` — class 1 → **passes**
- [x] `test_the_half_life_control_fires_when_the_ordering_inverts` — class 1 → **passes**
- [x] `test_the_override_and_the_default_produce_different_products` — class 1 → **passes**
- [x] `test_the_override_control_fires_on_a_reference_produced_assessment` — class 1 → **passes**
- [x] `test_the_selection_control_fires_on_a_stale_pinned_version` — class 1 → **passes**
- [x] `test_the_selection_control_fires_when_the_default_is_made_inert` — class 1 → **passes**

**`tests/products/test_resolver_seam.py`** — 4 tracked, failures
- [x] `test_a_gate_refusal_comes_back_as_an_envelope` — class 2 → **passes**
- [x] `test_a_gate_refusal_keeps_the_gates_own_typed_fields` — class 2 → **passes**
- [x] `test_a_gate_refusal_serves_nothing_and_records_everything` — class 2 → **passes**
- [x] `test_step5_a_refusal_reads_the_clock_once_and_NOW_records_served_at` — class 2 → **passes**

**`tests/products/test_runtime_product_gate.py`** — 1 tracked, failures
- [x] `test_the_gate_never_runs_on_a_candidate_the_universal_gates_refused` — class 1 → **passes**

**`tests/replay/test_refusal_replay_record.py`** — 2 tracked, failures
- [x] `test_a_gate_refusal_records_the_state_it_actually_read` — class 1 → **passes**
- [x] `test_the_evidence_bundle_is_the_executions_own_facts` — class 1 → **passes**

### The two baseline failures, kept separate

Red at the accepted base `72bee6eb`, never in the migration set, untouched:

- [ ] `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow` — base-existing, still red **by ruling**
- [ ] `tests/test_version_stamp.py::test_the_installed_version_is_not_the_stale_literal_and_is_git_derived` — base-existing, still red **by ruling**

One of them moved without being worked on: the unanchored-citation ratchet reads
**362** where the base reads 363, because two rotted line-number citations were
converted to the `path.py::Symbol` form while fixing what this step broke. Still
above its ceiling of 0, so still red, and still not this step's to close.

### Nothing else was left unexecuted

The full non-example suite after `2ee67428`: **8445 passed, 115 skipped, 2
failed** — the two above. The 115 skips are the standing estate- and
extra-gated population (`postgres`, `fluree`, `mongo`, `neo4j`, `harness`,
`crossproc` where a backend is absent), unchanged by this step and not part of it.
`tests/examples` is excluded by ruling and was not run.

---

## 13. Bound / Bind / Comp / Peer / Gate — verified, guarded, falsified

Dave's ruling, 2026-09-28: *"R1–R4, P1 and severings 1–11 were GO-text echoes, not
sheet identifiers. Do not invent a roster under those names."* So the ledger is
named by PROPERTY, and each entry carries the one concrete `src/` edit that
falsifies it. `tests/products/test_served_at_severings.py::STEP5_SEVERING_LEDGER`.

All five properties were already WIRED at `acd1930e`. They were not all guarded.
A read-only verification pass over each one found four real gaps, three of them
MEASURED escapes rather than reasoned ones.

### What the verification found, and what it cost to close

| property | wired | the gap found | closed by |
| --- | --- | --- | --- |
| Bound | yes | placement rests solely on E5's `calls == []`; nothing else notices the order | the severing that invokes acquisition one block early |
| Bind | yes | **measured escape** — E2 filtered on the tenant-qualified key, so a binding minted under the BARE class id carried a fabricated version `"unknown"` straight past it | E2 widened to the class id, plus a severing that mints exactly that shape |
| Comp | yes | only ONE parametrized leg guarded `evaluated_at`, behaviorally, through a 180-second floor margin entangled with the parent's own anchor | a kwarg-level control asserting the value `compose_children` was handed, plus its severing |
| Gate | yes | **measured** — all three `test_served_at_pinning.py` legs stay GREEN under `now=decided_at`; the comparand had NO control at all | a behavioral pair on the case the change exists for, plus its severing |
| Peer | yes | the two interior hops are unguarded; a one-word substitution left the ENTIRE suite green | a structural hop guard (limitation stated) plus its severing |

**The Gate finding is the one worth reading twice.** The companion control written
for the clock ruling was believed to guard the comparand. It does not: its subject
is `served_at`'s presence in the replay record, and both of its pinned instants sit
inside the declared window against either comparand. On `from_decision` the expiry
and the comparand move together, so Gate 3's lower bound could never bite — which
means the change had been made and nothing would have noticed it being undone.

The new control is the only arithmetic that separates the two instants:

    asked/decided 12:00 → expires 12:00 + 300s = 12:05 → served 12:07

valid with five minutes left when decided, expired for two when handed over.

### Peer — proven, and honestly under-guarded

**No code repair was needed.** There is exactly ONE production call site
(`src/ccf/products/child_resolver.py:576`); its instant is the single hoisted
`served_at` across five hops; `GovernedResolver.__call__` accepts no instant; and
`admission_clock` is a boot-fixed zero-arg callable nothing mutates per request.
Every test caller passes a deterministic fixture constant, not a clock. Nothing
under `src/ccf/peering/` reads an ambient clock — verified by an AST walk
deliberately WIDER than the shipped detector (aliased roots, bare-name calls,
non-call references, `today()`), and clean.

`archive/examples/04-cross-process/run.py` holds the only other two peering
`admit(` calls in the repository. They are EXCLUDED: `archive/` is a dated
reference surface (`D-IMPL-351` — no fixes, no findings), and no live `examples/`
file calls `.admit(` at all. Recorded so they never read as unrepaired governed
paths.

**The falsification is STRUCTURAL and that is stated, not hidden.** The behavioral
end-to-end control does not exist because no path to it exists: `_admit` requires a
`ResolvedProducer`, mint-only through `resolve_producing_grant` from a
module-private `BoundSkillView`, and **no deployment in `src/`, `runtime/` or
`examples/` wires a `PeeringAdmissionGate` into a child resolver at all**. So there
is nothing to borrow and nothing to drive. The hazard is nonetheless specific:
`ChildResolver._admit` receives BOTH `asked_at` and `admitted_at`, so a
caller-supplied instant sits in scope beside the fabric one at the exact line that
feeds the verdict — a one-word edit the whole suite was measured to permit.

### Residuals recorded, NOT worked

1. **Replay re-judges a peered child's admission at replay wall-clock.**
   `src/ccf/replay/environment.py:116` rebuilds the resolver through
   `build_governed_resolver(**opened.build_arguments(fabric))`, carrying the
   DEPLOYMENT's `admission_clock` (default `_utc_now`) rather than the `served_at`
   the record pinned. Fabric-controlled, so the Peer property holds and no A2A
   caller can influence it — but it is a replay-determinism question and nothing
   guards it. **Step 6 territory; not started.**
2. **The Peer property is currently vacuous on shipped code.** `peering_gate=` is
   supplied at exactly one place and the paved road passes it nothing, so a peered
   child today takes the honest refusal at `child_resolver.py:569-573`. The property
   holds for the first deployment that wires a gate, and it holds because the SDK
   threads the instant — not because any deployment gets it right.
3. **The peering clock detector is narrower than its own docstring.** It matches
   only attribute calls rooted at the literal names `datetime`/`time`. The wider
   sweep is clean today, so this is hardening rather than a reproduced hole — but
   the docstring claims a guarantee the detector does not deliver.

### The last step-5 control, and residual 3 closed

**Bound's restamp half now has its own control**, on the leg it belongs to.
`test_resolver_seam.py::test_Bound_the_out_of_window_refusal_record_carries_the_ONE_hoisted_served_at`
drives the real out-of-window `TemporalBoundRefusal`, asserts its specific reason,
resolves the refusal's own replay reference and reads the PERSISTED record.

Its instrument is what makes it work: an **advancing** clock, returning `ADMITTED_AT`
on the first read and one second later each time after. A clock pinned to a constant
cannot tell one read from two — a second read returns the same instant, the record
looks right, and only a counter notices. Against an advancing clock a restamp is a
wrong VALUE. The three instants are deliberately distinct (asked thirty days back,
`recorded_at` following the question, `served_at` the fabric's), asserted as
distinct, so a control in which they coincided could not tell a restamp from a
substitution from the truth.

**Three mutations, named separately and NOT folded into the six-entry ledger** —
those six are one-edit-per-property falsifications; these are three ways to break one
half of one property, and renumbering to absorb them would make the ledger's own
arithmetic lie. `BOUND_RESTAMP_MUTATIONS`:

| mutation | what it does | caught by |
| --- | --- | --- |
| `restamped-from-a-second-clock-read` | `served_at=self.admission_clock()` | the record carries `ADMITTED_AT + 1s` and reads are `[1, 1]` |
| `substituted-with-the-questions-instant` | `served_at=request.asked_at` | the record carries the question's instant |
| `omitted-entirely` | the argument dropped | a `TypeError` at the call — `served_at` is a REQUIRED keyword on the recorder (`D-IMPL-264` amendment 1, *"No intermediate layer may manufacture the marker from omission"*), so omission cannot silently yield a record at all |

**Residual 3 is CLOSED, test-only.** The clock detector matched only attribute CALLS
rooted at the literal names `datetime`/`time`, while its docstring claimed to guard
"reads no ambient clock". Four shapes walked past it: an aliased root
(`datetime as dt`), a bare-name call (`from time import time`), a non-call reference
(`Field(default_factory=datetime.now)`), and `today()`/`perf_counter()`. The detector
now sees all of them, each proven by a planted shape, and **the sweep over all six
`src/ccf/peering/` modules is clean before and after** — so this is hardening, not a
reproduced hole, and no production code moved.

### Residuals still carried

1. **Replay re-judges a peered child on the deployment clock** —
   `replay/environment.py:116`. **Step 6, ruled. Not touched.**
2. **Peer is structurally guarded; behavioral integration coverage is deferred.**
   No deployment wires a `PeeringAdmissionGate` into a child resolver, and a
   `ResolvedProducer` is mint-only via `resolve_producing_grant` from a
   module-private `BoundSkillView` — so there is no governed path to drive. A gate
   was NOT stood up merely to make the ledger look finished. The structural hop
   guard plus the one-word-edit severing is the proof this tree can support.

---

## 14. Step 6 — the replay-clock residual is REFUTED, and recorded time verified

**Step 6 changed no production code, and that is the finding.** Dave's instruction was
explicit: reproduce the residual before prescribing its repair, and *"do not change
production code merely because the constructor carries a callable."* The constructor
does carry the callable. Replay never reads it.

### The residual as written, and what was measured

The residual read: *"replay re-judges a peered child's admission at replay wall-clock,
because `src/ccf/replay/environment.py:116` rebuilds the resolver via
`build_governed_resolver(**opened.build_arguments(fabric))`, which carries the
DEPLOYMENT's `admission_clock` (default `_utc_now`) rather than the `served_at` pinned
on the record."*

**Verdict: REFUTED.** The premise is true and the conclusion does not follow.

| probe | result |
| --- | --- |
| `arguments["admission_clock"] is <the raising clock>` | **True** — the callable IS carried |
| a RAISING `admission_clock`, then `replay(...)` through the supported path | **never invoked.** Reconstruction completed; replayed product address identical to the recorded one; bytes identical |
| the SAME raising callable on the SERVE path (positive control) | **raises**, at `resolver.py::GovernedResolver.__call__` where `served_at` is obtained |

A counter would not have settled this — a counter on a callable nobody invokes reads the
same as a callable that does not exist. A clock that RAISES turns *"was it read?"* into a
fact the measurement cannot miss.

**Two live-time reads DO exist on the wider path, and neither is a temporal evaluation of
the historical determination.** Both were found by making all seven `_utc_now` functions
in `src/` raise:

1. `load_config_and_boot` → `deployment/manifest.py::_mint_register`,
   `occurred_at=_utc_now()` — an audit event about REOPENING the fabric.
2. `RecordedEnvironment.__init__` → `build_governed_resolver` → `__post_init__` →
   `_mint_replay_at_composition` → `_composition_decision(occurred_at=_utc_now())` —
   minting the resolver's own replay capability at composition.

Both are bookkeeping instants about the act of reconstructing. Neither participates in
judging what the original determination was. Recorded so a later reader does not
rediscover them and mistake them for the residual.

**Structurally, the clock is not even reachable from the reconstruction object.**
`RecordedEnvironment.__init__` reads three declarations off the rebuilt resolver
(`plan_factory`, `policy_bundle_key`, `product_ttl_seconds`) and **discards it**. The
mutation that falsifies the clock control therefore needs TWO anchors — one to smuggle the
clock onto the environment, one to read it — because there is nothing there to call.

**The reported peered-child re-judgment is not reachable through the supported path at
all.** A real composite with one admitted child replays to `ReplayUnresolvable`: *"this
decision composed 1 admitted child product(s) and the environment does not implement
`resolve_composite_plan`."* No instrument fired. Consistent with step 5's finding that no
deployment wires a `PeeringAdmissionGate` anywhere.

### Corrected characterization, for the record

> Replay does not consult the deployment clock when reconstructing a determination. The
> deployment's `admission_clock` is carried into the rebuilt resolver and is never
> invoked; the resolver itself is discarded after three declarations are read off it.
> Live time is read twice on the wider path — reopening the fabric, and minting the
> reconstruction's own replay capability — and neither is a temporal evaluation of the
> recorded determination. The peered-child re-judgment the original residual described is
> unreachable through the supported replay path.

### What replay's temporal evaluation actually uses

Measured, not assumed: `replay/engine.py` calls `resolve_ttl_anchor(...,
decided_at=record.recorded_at, ...)` — a RECORDED instant. And `grep served_at
src/ccf/replay/{engine,serve,environment}.py` returns **zero hits**: replay does not read
`served_at` at all, so there was never a path for it to be re-derived on.

### Controls added — `tests/replay/test_step6_recorded_time.py`, 11 tests

**Historical bytes retain their address.** On the ONE committed pre-field record in the
tree: `tests/replay/fixtures/golden_13bd250/artifacts/401bfc18…`, `producing_commit
13bd250e7a9d9ea12daf596ef86597557aad702f` = tag `phase-24.5-base`, and **that tree
declares `served_at` zero times** (verified with `git show <commit>:src/ccf/replay/record.py`).
So it is pre-field by PROVENANCE, not by inspection alone. The expected address is read
from the evidence in two independent places — the artifact's own filename and the
manifest's `record_content_address` — and held equal, so the central assertion is not a
re-hash compared against itself. Measured: loading it under today's model reproduces the
stored bytes BYTE-IDENTICALLY and `content_hash` equals the stored address.

**Populated time remains addressed.** Two records differing in `served_at` and nothing
else take different addresses; restoring the sentinel restores the historical address. No
product content is required to change.

**Deployment time cannot change reconstruction.** The raising-clock control, its positive
control on the serve path, and a second leg reconstructing the same record under
deployment clocks FIVE YEARS apart with an identical reproduced address.

**Pinned policy remains pinned.** The shared mechanism is already proven for the debt
profile by `test_engine_rehydration.py::test_a_replay_reproduces_the_obligation_in_force_at_decision_time`,
which is cited rather than duplicated. What is ADDED covers the binding step 5 itself
introduced and that control predates: a later `ccf.temporal-boundary-policy` version
registered under the same key does not displace the recorded one. Both halves asserted —
the rebinding is genuinely different and genuinely available.

### Falsifications — `STEP6_RECORD_MUTATIONS`, three entries

Named separately from step 5's ledgers; folding them in would make that ledger's
arithmetic wrong about what it covers. `src/` and `runtime/` verified unchanged after the
campaign, and no `__pycache__` was written (`python -B`, `PYTHONDONTWRITEBYTECODE=1`).

| mutation | effect |
| --- | --- |
| `transparency-mark-flipped-to-a-generation-boundary` | the pre-field record stops reproducing its stored address |
| `populated-served-at-dropped-from-addressed-content` | two distinct serve instants share one address |
| `a-live-clock-read-inserted-into-reconstruction` | the raising-clock control reddens |

**The third is explicitly NOT a repair.** Dave's named mutation was *"replacing the
recorded evaluation instant with the deployment-clock path that the reproduction
identified."* The reproduction identified NO such path. Rather than manufacture an
execution path to validate the earlier wording, it inserts a clock read that does not
exist on the shipped tree and shows the control catching it — evidence that the guard
discriminates, not evidence of a defect.

### Residual dispositions after step 6

1. **Replay-clock residual — CLOSED by refutation**, with the measured evidence above.
   No production change. `replay/environment.py` untouched.
2. **Peer behavioral-coverage residual — UNCHANGED and carried.** Structurally guarded;
   end-to-end behavioral integration remains unproven, and step 6's composite probe
   independently confirms why: the supported path raises `ReplayUnresolvable` before any
   child re-judgment. No `PeeringAdmissionGate` deployment was invented.
3. **Detector widening — closed in step 5**, test-only. Untouched here.

---

## 15. Step 7 — the debt instant. Sheet §3.7 REFUTED; the real gap was a different one

**No production code changed.** Ruling 6 holds on this tree and always did; what was
missing was a control whose subject is the instant.

### §3.7 does not reproduce

The sheet recorded: *"with a plugin making `FreshnessScorer.score` read a wall clock
instead of the instant handed to it, the suite is **153 passed / 0 failed / 0 errors**
— unchanged. The D8 ruling is unprovable as the design stands."*

Measured with exactly that substitution, applied as a scratch pytest plugin (the tree
never edited):

| population | control | under the substitution |
| --- | --- | --- |
| `tests/halflife/` | **225 passed** | **220 passed, 5 failed** |
| `tests/products/` | **1724 passed** | **1719 passed, 5 failed** |

**Ten tests redden.** And the claim cannot have been measured over these files:
`tests/halflife/`, `src/ccf/halflife/` and `tests/products/test_reference_debt_scorer.py`
are BYTE-IDENTICAL between the sheet's baseline `51158a58` and this tree, and all ten
reddening tests were present at that baseline. The 153-node population could not be
identified and **was not invented** — the likeliest reading is a population that never
invoked the subject, or a plugin that never bound the class attribute. A green run over
a population that never calls the thing under test measures nothing.

Positive control for the instrument: an identity plugin that passes `now` through leaves
`tests/halflife/` at 225 passed with 16 `score` calls intercepted — so the interception
machinery breaks nothing and the substitution is the cause of every red.

### But the protection was INCIDENTAL, which is the real finding

Four of the ten redden because they pin freshness at exactly `Decimal(1)` for an
observation dated AT the handed instant, and `decay.freshness` returns exactly 1 only at
zero age. Those are VALUE assertions that a clock read happens to break. Re-date such a
fixture by one second for an unrelated reason and the protection disappears with nothing
to notice.

Measured against Dave's three categories:

- **(a) value/band controls** — many.
- **(b) which instant is used** — exactly ONE deliberate control in the whole tree
  (`test_reference_debt_scorer.py::test_the_instant_is_the_views_own_as_of`), and it sits
  one frame ABOVE `FreshnessScorer.score` on `AssemblyDebtScorer.__call__`, framed as a
  provenance claim, with no severing.
- **(c) the scorer reads no clock at all** — **EMPTY.** No debt-side analogue of
  `tests/peering/test_admission_clock.py`. The one near-miss
  (`test_debt.py::test_the_recency_is_carried_and_never_consumed`) scans only
  `halflife/assessment.py`, which holds no computation, by raw substring, with no
  positive control — so `debt.py` and `decay.py`, where the computation actually lives,
  were never scanned.

### What step 7 built — `tests/halflife/test_step7_debt_instant.py`, 9 tests

**(c), the empty category.** An AST sweep over every module that participates in a debt
figure — all of `src/ccf/halflife/` plus `products/debt_scorer.py`, the frame that hands
the instant down — using the ONE widened detector from step 5's section J, imported
rather than restated. With its own positive control (the sweep runs over different files
than the detector was written for) and a vacuity guard.

**(b), at the level it was missing.** Every `now=` in `tests/halflife/test_debt.py` is
the single module constant `NOW`, so nothing there can tell the handed instant from any
other. The new control scores ONE observation at TWO instants a year apart and requires
the figure to follow the argument. Plus the structural half: `now` is keyword-only with
no default, so no caller can omit it and fall back to whatever is in scope.

**A deliberately LONG half-life, and the reason is arithmetic.** `relevance_ratio`
quantizes to `RATIO_QUANTUM = 1E-18`. At the fixture calibrations (λ_c 3600 s, and
cp-06's 86400 s) a wall-clock reading is thousands of half-lives old and the figure
UNDERFLOWS to `0E-18` — so a strict inequality would redden because both readings
collapsed to the quantum, not because a different instant was measured, and a non-strict
one would go green. **A control must not be built on the quantum.** At 180 days neither
reading underflows, and the control asserts that distance explicitly rather than
trusting a comment.

### The severing caught a defect in my own control

`STEP7_DEBT_MUTATIONS` — `the-freshness-scorer-reads-a-wall-clock`, a two-anchor edit
(`debt.py` imports only `datetime`, so the substitution must bring `UTC` with it; a
severing that raised `NameError` would redden for an import error, which is not evidence
about a temporal property).

**The first draft of the control asserted only the ORDERING** — `at_near > at_far` — and
the severing showed it **still passing** under the substitution. Two `datetime.now()`
calls land microseconds apart, so the later reading is very slightly staler and the
ordering holds by accident of call order, the two figures differing in about the twelfth
decimal place. The control now asserts a MAGNITUDE: a year at a 180-day half-life is more
than two half-lives, so the figure must more than HALVE, which two clock reads a
microsecond apart cannot produce whatever their order. The severing asserts the GAP
collapses (honest gap ≈ 0.75, severed gap ≈ 1e-12) and that the magnitude assertion would
indeed have failed.

### FINDING S7-F1 — the reference scorer measures from `asked_at`, not the decision instant

Surfaced, NOT fixed: repairing it changes which instant the shipped reference scorer
measures from, which is a production behavior change beyond this step's named scope.

- `decay.freshness`'s docstring (`src/ccf/halflife/decay.py::freshness`) says `now` is *"The
  decision instant. Injected, never read from a clock."*
- The shipped reference scorer passes `now=view.as_of`
  (`src/ccf/products/debt_scorer.py::AssemblyDebtScorer`), and `view.as_of` is `request.asked_at` — the
  resolver's only `reader.as_of(` call binds `at=request.asked_at`
  (`src/ccf/products/resolver.py::GovernedResolver`).
- `decided_at` reaches a scorer on exactly ONE branch: `InstantAwareDebtScorerProtocol.score_at`
  (`src/ccf/products/resolver.py::InstantAwareDebtScorerProtocol`). The other two branches receive no instant at all. The SDK's
  one conformer, `_AssessAdapter.score_at` (`src/ccf/products/product.py::_AssessAdapter`), hands
  `decided_at` to the DEVELOPER's callable and does not force it into `FreshnessScorer`.

So wherever a product class declares a decision-instant parameter — making `decided_at`
differ from `asked_at` — the reference scorer measures decay from the question's instant
while ruling 6 says the debt is computed at the decision instant. On fixtures where the
two coincide the gap is invisible, which is why no control noticed.

**Not the recorded `observed_at == asked_at` degeneracy** — that one is about a fixture
and is explicitly not this step's subject. This is about which of two DIFFERENT instants
the shipped scorer reads, and it needs a ruling.
