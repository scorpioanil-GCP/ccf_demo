# Phase I.3 — Cross-Process & Harness Adapters: Gate Package

**Phase:** 6 (Phase I.3) · **Branch:** `phase-i3` · **Assembled:** 2026-07-27
**Protocol:** CLAUDE.md §3.1 (self-review → triage → present to Dave → `D-GATE-I.3` → merge)
**Gate bar:** the D-17 checklist carried from I.1 and I.2 — every row names a passing test or
lint **and what would fail if the implementation were broken**. No numeric coverage gate.

> **Status: AWAITING REVIEW.** `D-GATE-I.3` is **deliberately unwritten**. `/gsd-review`
> passing is necessary and never sufficient; approval authority is Dave's alone
> (CLAUDE.md §3.1, §2). The absence of the entry is grep-asserted by this plan's
> acceptance criteria, exactly as `05-07` did for I.2.

> **How to read the rows.** The I.2 retrospective's binding process finding is that gate
> prose drafted from *plan intent* overclaims — I.2's had to be rewritten in 05-10. Every
> row below was therefore drafted from a test that fails under the broken implementation,
> and states that failure in its own column. A claim without such a column is a claim
> without evidence, and none appears here.

---

## 1. Verification Evidence — Execution Record

**What actually ran, and where. This is the post-closure sweep, executed 2026-07-27 in plan
06-23 — after every gap-closure commit listed in §1.6.** The pre-closure numbers 06-16
recorded (940 passed / 2 skipped, 188 conformance) are **superseded, not averaged**: a gate
whose evidence predates its own fixes is the failure mode §1.1 exists to prevent, so the
earlier run is named here only as the baseline the new one is compared against.

Base: `cf8395d` (the tip of gap-closure wave 5) plus this plan's commits, on the `06-23`
worktree. Interpreter: `/home/parkave/ccf_code/.venv/bin/python` (Python 3.12) with
`PYTHONPATH=<worktree>/src:<worktree>/runtime`. **The `PYTHONPATH` is load-bearing**: both
`ccf` and `ccf_runtime` are installed editable against the *main* checkout, so run from a
worktree without it, `pytest` silently reports on code that is not under test. Asserted
rather than assumed before any leg ran — `ccf.__file__` and `ccf_runtime.__file__` were both
printed and both resolve inside the worktree
(`<worktree>/src/ccf/__init__.py`, `<worktree>/runtime/ccf_runtime/__init__.py`). Stating the
environment, not just the command, is the direct lesson of finding §1.1 below.

| Leg | Command | Result |
|-----|---------|--------|
| Full suite | `python -m pytest -q -rs` | **987 passed, 2 skipped**, exit 0 |
| Full suite, harnesses mandatory | `CCF_REQUIRE_HARNESSES=1 python -m pytest -q -rs` | **987 passed, 2 skipped**, exit 0 — no harness leg skipped |
| Harness conformance alone | `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance -q -rs` | **193 passed**, all three harness legs executed (was 188; 06-20's adversarial legs added five) |
| CINV-02 carve-out boundary tests (row 1's corrected citation) | `python -m pytest tools/lints/tests -q` | **49 passed** |
| Invariant lints (CINV-01a/b/c, CINV-02 incl. the D-24 carve-out, CINV-03) | `python -m tools.lints --all` | **exit 0, zero findings** |
| Strict typing | `python -m mypy` | **Success: no issues found in 99 source files** (`src` **and** `runtime`) |
| Dependency coherence | `python -m pip check` | **No broken requirements found** |
| Harness SDKs present | `pip show claude-agent-sdk langgraph google-adk` | `0.2.128` / `1.2.9` / `2.5.0` |

**The pass count rose 940 → 987 and no test was removed** — the deletion constraint is
checked directly in §1.6 rather than inferred from the count.

**The 2 skips are the same two deliberate deferrals I.2 ended with, and nothing else.**
Both name their activating phase in the skip reason, printed by `-rs`:

| Skipped check | Activating phase | Reason string emitted |
|---------------|------------------|------------------------|
| `hitl-action-capture` | **Phase I.4** | every HITL action lands in replay dimension 2 by construction (CLAUDE.md §8.2) |
| `workflow-trace-capture` | **Phase I.4** | every workflow execution trace lands in replay dimensions 4 and 5 by construction (CLAUDE.md §8.1) |

Both reason strings are quotations of CLAUDE.md §8.1/§8.2 commitments, marked as such under
the D-21 sweep in §4.9.

### 1.1 Three gate-evidence integrity findings this phase produced

Recorded first because all three are cases of **a check reporting on something other than what
it claimed**, which is the failure mode a gate document exists to prevent. *(The count was
raised from two to three in 06-22; this sentence still said "both" and is corrected here — the
same class of residual as the one row 1 names.)*

1. **CI was running `mypy --strict src`, overriding `[tool.mypy] files`.** Extending the
   config to include `runtime` — which 06-02 did, per research B2 — would have had **zero
   effect in CI**. The majority of this phase's code (every adapter, transport, and MCP
   server lives under `/runtime`) would have shipped unchecked while a gate document cited
   "mypy --strict clean". Fixed in 06-02 to a bare `mypy`, so `[tool.mypy] files` is the
   single source of truth. **Consequence for the record:** the I.1 and I.2 gate rows citing
   "mypy --strict clean" were narrower than they read — they covered `src` only, which was
   accurate for those phases' code but is not a precedent this phase could have inherited.
2. **The prior mypy-clean claim was environment-dependent.** `chromadb` is deliberately
   absent from the `dev` extra, so any environment without the optional `chroma` extra —
   **including CI** — failed with `import-not-found`. Also fixed in 06-02. A type-check
   result that depends on which optional extra happens to be installed is not a property of
   the code.

3. **This document's own row 1 cited the wrong test directory** *(**closes A4**, found by the
   2026-07-27 cross-AI gate review)*. Row 1 pointed at `tests/lints/` for the four CINV-02
   carve-out boundary tests. That directory **exists** but holds unrelated tests
   (`test_cinv01c_behavioral.py`, `test_extra_isolation.py`); the boundary tests are in
   `tools/lints/tests/test_harness_imports.py`. So the citation was wrong in *exactly* the
   same class as findings 1 and 2 — a reader following it would have found a real directory
   with real passing tests and concluded the claim was evidenced. Corrected in row 1, with the
   corrected path verified by running it rather than by inspection. **The count in this
   heading was two and is now three, deliberately:** a gate document that quietly absorbs a
   third instance of its own named defect class is committing that defect a fourth time.

None of the three was a code defect. All three were *evidence* defects, and they are the
reason the table above states the interpreter, the working tree, and the `PYTHONPATH` rather
than a bare command name — and the reason every path this document cites is now checked to
resolve (§4.13).

### 1.2 Cross-cutting greps the checklist cites (all empty)

| Spot check | Command | Result |
|------------|---------|--------|
| No A2A transport dependency in core | `grep -rn 'from a2a\|import a2a' src/` | **empty** (exit 1) |
| No harness import anywhere in core | `grep -rn 'langgraph\|google.adk\|claude_agent_sdk' src/` | **empty** (exit 1) — corroborating CINV-02's zero findings |
| No dynamic import in skill dispatch (D-19/D-IMPL-54) | `grep -rn 'importlib' src/ccf/skills/` | **empty** (exit 1) |

**Five more the gap-closure wave earned**, re-run in this plan. Each is the retired form of a
defect the wave closed, so a non-empty result would mean a closure had regressed:

| Spot check | Command | Result |
|------------|---------|--------|
| B1's retired witness is gone (06-18) | `grep -c engine_resolved src/ccf/peering/admission.py` | **0** |
| B1's retired docstring admission is gone (06-18) | `grep -rl "structurally vacuous" src/` | **0 files** |
| The pre-D-IMPL-59 seam name is fully retired (06-24/06-25) | `grep -rl "ccf\.a2a\|ccf_runtime\.a2a" src runtime tests tools` | **0 files** |
| The pre-amendment class id is gone (D-IMPL-58, amended 2026-07-27) | `grep -rl '"admission_record"' src runtime tests` | **0 files** |
| No unsuffixed seam Protocol, against Dave's `PeeringProtocol` ruling | `grep -rlE "^class Peering\(\|^class Peering:" src/` | **0 files** |

And the two positive forms of the same rulings, which a `== 0` check cannot establish:

| Ruling | Command | Result |
|--------|---------|--------|
| D-IMPL-58 class id, registered exactly once | `grep -rn 'class_id="ccf.admission-record"' src runtime tests` | **1 hit**, `src/ccf/peering/admission.py:471` |
| D-IMPL-59 Protocol name | `grep -c "class PeeringProtocol" src/ccf/peering/protocol.py` | **1** |

> **Correction to this plan's own acceptance criteria, recorded rather than worked around.**
> 06-23's criteria located the `class_id` registration in `src/ccf/controlplane/artifacts.py`.
> That file exists, but the registration **cannot** live there: `products.contract →
> controlplane.registry → controlplane.artifacts` is an import cycle, which is why 06-19 placed
> `ADMISSION_RECORD` beside the contract it declares, in `src/ccf/peering/admission.py`. The
> criterion's *property* — the class id is `ccf.admission-record` and is declared exactly once —
> **holds**, and is verified above at the real location. The same mis-citation appeared in
> 06-19's and 06-24's criteria; it is recorded here so the third instance is not silent.

These greps **corroborate**; they do not carry the claims. A grep cannot distinguish a
violation from a *mention* of one, which is precisely why the load-bearing versions of all
three are AST scans and lint rules (rows 1, 4, 8 below). See §4.9.

### 1.3 D-02 wave ordering, as delivered

The ruled risk ordering — **slice → transport → trust → harness → gate** — was executed:
wave 1 blockers (06-01 D-24 carve-out, 06-02 packaging/typing, 06-03 D-19 control); wave 2
the D-01 vertical slice (06-04) plus the two `/src`-only plans it does not block (06-07
trust, 06-11 harness contract); wave 3 transports and the acquisition leg (06-05, 06-06,
06-08, 06-12, 06-17); waves 4–5 the remaining transports and adapters (06-09, 06-13, 06-10,
06-14); wave 6 the portability proof (06-15); wave 7 this gate (06-16). The blocking
orderings held absolutely: D-24 preceded every harness import, D-19 preceded every transport
plan, and D-07's Claude → LangGraph → ADK harness order was preserved.

### 1.4 D-06: every proof shipped as a test fixture; no `/examples` directory was created

`ls examples/` is unchanged from its pre-phase state — this phase created nothing there. Per
D-06 every wave's proof is a test fixture under `tests/fixtures/banking/`, and the
eight-example suite of CLAUDE.md §9 is handed to **Phase 8 (I.5)**, which owns it in the
ROADMAP. Example 03 (harness portability) and example 07 (ArtifactStore swap) both depend on
mechanism this phase delivered; neither is claimed as delivered here.

### 1.5 Supply chain and secrets

- **No package installs occurred in this plan.** The phase's harness and transport
  dependencies were installed under 06-02, whose blocking human checkpoint covered them, and
  the phase slopcheck audit returned 13/13 OK.
- **Repository scan for key material added this phase:** `git diff --name-only` across the
  phase branch contains no `.pem`, `.jwk`, `.p12`, or token-shaped file. A2A and MCP key
  material is generated per test into a `tmp_path` and never committed; what the fixtures
  declare is which *identifiers* a peer may sign under, which is policy, not secret.

### 1.6 The gap-closure wave: which findings, which plans, which commits

The 2026-07-27 cross-AI gate review returned **three blocking findings and seven advisories**
(`06-REVIEWS.md`, which now carries a 10-row disposition table). Two decisions surfaced
*during* the closure work and were ruled by Dave mid-wave, which grew the wave from four plans
to six. Every closure is a code or docs change on `phase-i3`; none is a re-presentation of
existing work as closed.

| Plan | Closes | Substance | Commits |
|------|--------|-----------|---------|
| **06-18** | **B1** | The federated gate sequence stops passing the producer's own `operators_invoked` as an `engine_resolved` witness to a gate named strict equality. `GATE_LINEAGE_ATTRIBUTABILITY` / `LineageAttributionRefusal` added; gates 1 and 3 factored into `_refuse_empty_operators` / `_refuse_ttl` and shared with the local sequence. D-IMPL-57 reading (a) | `95d5b7f`, `6855afe`, `3ba090d`, `711b094`, `7c6dc3a` |
| **06-19** | **B2** | `AdmissionRecord` (class id `ccf.admission-record`) declared, persisted at the crossing, referenced from the audit append, and resolvable by replay at an exact version — `replay/engine.py` generalized to contract-parametrized `resolve_artifact` / `resolve_artifact_at_uri`. `LineageEntry` untouched, asserted. D-IMPL-58 reading (d) | `cb80b33`, `466f309`, `dc71c66`, `77ef83d`, `713efde`, `0bb79d2`, `8b69d56` |
| **06-20** | **B3** | Adversarial harness legs give the seam-3 emission and seam-4 trace equalities a real failure mode; the suite's own docstring states what it drives and does not drive | `bd34919`, `24dbddb`, `b2cddf1`, `8f6e1b5`, `c1a59ad` |
| **06-21** | **A1, A2** | The transport instance scan parametrized over structurally discovered transports with a live count guard (`LfA2AWire` included); the `AdmittedProduct` claim scoped to "a type error on every unforced path" | `27e39ca`, `c56209e`, `043f951` |
| **06-24** | **D-IMPL-59** (parts 1–4) | The federation seam relocated to `ccf.peering`; `WireProtocol` → `PeeringProtocol`; `wire.py` → `protocol.py`; transports under `ccf_runtime.peering`; tests under `tests/peering/`; audit verdict members and gate id values → `peering-*`. Part 4 pinned as a property test | `84dad4c`, `a2cc6f8`, `20c029c`, `96849d8` |
| **06-25** | **D-IMPL-59** (skill surface) | The catalog and dispatcher speak `peering`; the `a2a` skill_type token retired | `9acf32a`, `0d57313`, `3e82288` |
| **06-22** | **B1–B3 prose, A1/A2/A4/A5** | Gate rows and criterion prose narrowed to what the suite holds, each narrowing carrying the finding id that forced it; §3.2.1, §3.3.1, §4.13 added; `06-REVIEWS.md` disposition table | `db54701`, `fa3c98a`, `942dc7e`, `d86aa16` |
| **06-23** *(this plan)* | gate re-presentation | The sweep above, the row-by-row re-verification in §2, and `06-VALIDATION.md`'s wave map | this plan |

**No code was deleted anywhere in the wave.** Checked two ways, both empty:
`git diff --diff-filter=D --name-only pre-peering -- src/ runtime/ tests/ tools/` (the wave,
against the pinned `pre-peering` tag) and
`git diff --diff-filter=D --name-only main...HEAD -- src/ runtime/ tests/` (the whole phase).
Every relocation is a rename: `git diff -M --name-status pre-peering HEAD` reports **16**
`R`-status paths across `src/ runtime/ tests/ tools/`.

**Three advisories are carried forward, not closed** — A3, A6, A7, each with a stated
consequence in §5. **A3 in particular is open**: see §3.3.1 and §5.

**`D-GATE-I.3` is not logged.** The Gate Log in `docs/DECISIONS.md` ends at `D-GATE-I.2`;
`grep -cE "^\*?\*?D-GATE-I\.3 —|^#+ .*D-GATE-I\.3" docs/DECISIONS.md` → **0**. A literal
`grep -c "D-GATE-I.3"` returns **1**, and that hit is a *prose mention inside D-IMPL-58's own
text* ("Phase I.3 cannot be honestly presented for `D-GATE-I.3`") — not an entry. It was
already present at this plan's base and is deliberately left alone: deleting a sentence from a
decision-log entry to satisfy a counter would be a worse defect than the counter it satisfies.

---

## 2. Per-Invariant Checklist (D-17 pattern)

Every row: the claim, **scoped to its actual enforcement (D-21)**, the named test or lint,
and what would fail under a broken implementation.

| # | Claim, at the strength it is enforced | Named mechanism | What would fail if broken |
|---|----------------------------------------|-----------------|---------------------------|
| 1 | **Harness neutrality — lint-enforced: no module outside `ccf_runtime.adapters.*` may import a harness package.** A structural module-path carve-out (D-24), never an allowlist | Lint rule `cinv02-harness` (`tools/lints/harness_imports.py`) via `python -m tools.lints --all`; the four negative boundary tests pinning the carve-out's edge are in **`tools/lints/tests/test_harness_imports.py`** — `::test_a_harness_import_inside_the_adapter_path_is_permitted`, `::test_a_harness_import_in_the_a2a_module_is_still_flagged` (which feeds `ccf_runtime.peering.lf_a2a`; only the test's *name* still says a2a), `::test_a_harness_import_in_the_cdc_module_is_still_flagged`, `::test_a_harness_import_in_a_lookalike_sibling_module_is_still_flagged`. *(Corrected citation — **closes A4**: this row previously cited `tests/lints/`, which exists but holds unrelated tests, `test_cinv01c_behavioral.py` and `test_extra_isolation.py`.)* Verified by running them: `pytest tools/lints/tests -q` → 49 passed | A harness import in `ccf.*`, `ccf_runtime.peering`, `ccf_runtime.cdc`, or `ccf_runtime.mcp` fires the lint. The negative tests are what stop the carve-out degrading into an unguarded prefix match — without them, a rename into `ccf_runtime.adapters_helper` would pass |
| 2 | **Zero harness imports in `/src`** — the same rule at its narrowest, corroborated textually | `cinv02-harness` over `/src`; §1.2 grep | As row 1. The grep alone would be satisfied by a docstring and is cited as corroboration only |
| 3 | **Single-writer across the Peering boundary — asserted by AST and attribute scans over the shipped modules, plus live state comparison.** Not "no path". **Every transport `ccf_runtime.peering` ships is constructed and attribute-scanned, the D-IMPL-14 default `LfA2AWire` included** *(claim **strengthened** by new coverage — **closes A1**; the scan previously constructed `TypedHttpWire` only, so the default transport carried the source-scan half alone)* | `tests/invariants/test_peering_single_writer.py` — import scan, identifier scan, and constructed-instance attribute scan over every discovered `ccf_runtime.peering` module. The transport *class* set is discovered **structurally** (`PeeringProtocol`-shaped: defined in a discovered module, offering both `emit` and `receive`) and `TRANSPORT_BUILDERS` is keyed by class rather than by name, so a third transport joins by being discovered and a rename cannot silently drop a leg. Legs observed: `[TypedHttpWire]`, `[LfA2AWire]`. Plus the live two-process case and the refused-product digest | A transport importing `ccf.graph`/`ccf.assembly`, naming a write-surface type, or holding one under a private attribute. Two count guards fail first: `test_transport_modules_were_actually_discovered` if the discovery helper silently returns nothing — the quietest way an invariant test stops being one — and **`test_every_discovered_transport_is_actually_constructed`** if construction coverage falls behind discovery, which is precisely how A1 happened. 06-21 measured the second guard's failure: `2 transport(s) are constructed but 1 were discovered`, naming both counts and both name-lists |
| 4 | **Single-writer across the adapter boundary** — same three-way scan, same scope statement | `tests/invariants/test_adapter_single_writer.py::test_no_adapter_module_names_a_fabric_write_surface`, `::test_no_constructed_adapter_holds_a_fabric_write_surface`, `::test_no_adapter_constructor_accepts_a_fabric_object`, `::test_no_adapter_instance_exposes_a_fabric_object`, `::test_an_effect_reaches_l3_only_through_emit_effect_into_l2` | An adapter accepting or exposing a fabric object, or an effect reaching L3 by any route other than `emit_effect` → L2 |
| 5 | **Single-writer across the ArtifactStore** — a full store cycle leaves the graph substrate byte-identical, **write-ahead log included** | `tests/invariants/test_mcp_role_separation.py::test_a_full_store_cycle_leaves_the_fabric_byte_identical`, guarded by `::test_the_byte_identical_digest_can_actually_see_a_committed_write` | An artifact server or store writing through to the graph. **The guard is load-bearing and new in 06-16**: the SQLite backend runs `journal_mode = WAL`, and it is *measured* that a committed L2 write leaves the main file byte-identical and changes only `<db>-wal`. The former main-file-only digest could not have observed the write it existed to rule out |
| 6 | **An inbound Peering product is not offerable to L2 unless the Control Plane admitted it — a type error on every unforced path** *(narrowed to Python's import model — **closes A2**, D-21. The row previously contrasted a type error against a mere discipline with no scope qualifier at all; the retired phrasing is deliberately not reproduced here, so the stronger claim cannot be recovered from this document by copy-paste — 06-21's precedent, which removed the adjective `unforgeable` rather than quoting it)* | `AssemblyWorker.ingest_admitted(admitted: AdmittedProduct, ...)`; `tests/crossproc/test_peering_exchange.py::test_the_federated_door_does_not_accept_an_unadmitted_product` asserts both the declared annotation and that every construction not carrying the gate's token fails at construction; `::test_the_unforgeability_claim_is_scoped_to_the_unforced_path` pins the boundary of that claim — `_ADMISSION_TOKEN` is importable, so forging requires naming a private member of `ccf.peering.admission`, which Python permits and no runtime check can prevent (advisory A2, D-21). Both edges are asserted: token withheld → `AdmissionBypassError`; private token imported and passed → construction succeeds, so the wording cannot be re-strengthened without a red suite | Re-widening `ingest_admitted` to take an `InboundProduct`/`object`, **or** dropping the construction token — at which point the annotation would still read correctly and mean nothing. Both halves are asserted because either alone is cosmetic. `ingest(SignalEnvelope)` is deliberately unchanged: it serves CDC and MCP ingress, and binding the type onto it would have broken two paths to constrain a third |
| 7 | **The Peering trust policy has no field that could express a verification skip.** This one earns strong wording: the state is genuinely unrepresentable in the contract | `src/ccf/peering/trust_policy.py` (`PeeringTrustPolicy`, `extra=forbid`, no skip/bypass/fast-path member); `tests/peering/test_admission.py` — every inbound product runs all six checks in order, D-IMPL-16 with no high-trust fast path; `tests/peering/test_peering_verdict.py::test_the_gate_offers_exactly_one_admission_entry_point` pins the absence of an `admit_fast` / `admit_trusted` surface | Adding a bypass field would have to change the contract, which `extra=forbid` makes a visible schema change rather than a runtime option. A tier narrows or widens *what* a peer may assert, never *whether* it is checked |
| 8 | **`local_callable` dispatch imports nothing; a dotted module path is not a value the resolution surface can express.** Also earns strong wording (D-IMPL-54 closing IN-06/D-19) | `src/ccf/skills/callables.py` + `src/ccf/skills/dispatch.py`; `tests/skills/test_callables.py`; §1.2 grep showing `importlib` gone from `src/ccf/skills/` | An entry naming `os.system` resolves to no registered key and is refused **without anything being imported**. The I.2 posture was a precondition on where the ref came from; this is a property of how it is resolved — required, because I.3 made artifacts remotely sourceable |
| 9 | **`effects: unsupported` is a conformance-verified absence: declared, refusal observed firing, L3 unchanged, no write handle obtainable** — four parts, not one declaration | `tests/conformance/test_harness_adapter.py::test_seam_3_refuses_when_the_adapter_declared_effects_unsupported` and `::test_effects_unsupported_is_inert_not_merely_declared` | An adapter that declared `unsupported` and still emitted. The second test is the one that matters: a declaration alone is a convention, and D-21 names exactly this as the claim class that degrades |
| 10 | **All four harness seams bind, per adapter, across three harnesses** | `tests/conformance/test_harness_adapter.py` — seam 1 `::test_seam_1_carries_the_pinned_instructions_and_the_typed_product`, `::test_seam_1_hands_the_harness_no_fabric_write_surface`; seam 2 `::test_seam_2_exposes_exactly_the_bound_skill_set`, `::test_seam_2_follows_a_revocation_without_re_declaring_the_agent`, `::test_seam_2_is_per_agent_not_per_catalog_the_two_agent_case`, `::test_seam_2_does_not_leak_an_ungranted_catalog_entry_into_the_carrier`; seam 3 `::test_seam_3_returns_a_governed_emission_as_a_typed_value`; seam 4 `::test_seam_4_records_what_the_harness_reported`, `::test_seam_4_reads_what_the_harness_carried_not_what_the_adapter_held`, `::test_seam_4_cannot_touch_a_governed_replay_dimension` | An adapter exposing an ungranted catalog entry, re-reading its own held state instead of the harness's trace, or writing into a governed replay dimension. The two-agent case (D-23) is what stops a per-catalog implementation passing a per-agent claim |
| 11 | **The absent-harness path is exercised against a name that can never be installed** | `tests/conformance/test_harness_adapter.py::test_an_absent_harness_skips_with_an_instruction_not_a_mystery`, `::test_an_absent_harness_fails_when_the_environment_requires_it`, both against the `ABSENT_HARNESS` sentinel | Re-pointing either at a real harness. They previously named `langgraph`, and went green only in an environment lacking the extra — so **installing langgraph retroactively falsified them**. An environment-dependent test decays into vacuity exactly when the project succeeds |
| 12 | **A skipped harness leg fails the build rather than passing it** | `CCF_REQUIRE_HARNESSES` in `tests/conftest.py::harness_unavailable`; the CI `test` job exports it and runs `pytest tests/conformance -q -rs`, not `continue-on-error` | Removing the env var: the conformance suite would collect all three legs, skip every one, and report green over the only evidence the §7.3 portability claim has. Mirrors the `CCF_REQUIRE_POSTGRES` leg rather than inventing a second pattern |
| 13 | **The two MCP server roles are separate modules, and neither reaches L3** | `tests/invariants/test_mcp_role_separation.py` — import/source scans over `ccf_runtime.mcp.egress` and `ccf_runtime.mcp.artifact_server`, plus URI-scheme disjointness | Merging the roles, or one importing the other and inheriting its trust posture; or either minting the other's URI scheme, after which a replay record could not tell which kind of address it held |
| 14 | **Lineage continuity is a property of the Peering admission boundary, persisted as an immutable `AdmissionRecord` and resolvable at an exact version** — *not* a property of graph state. The producer's operator plan, policy versions and graph anchor all survive the set-union, in the persisted record. `LineageEntry` is untouched, asserted rather than assumed *(narrowed — **closes B2**; D-IMPL-58 reading (d), closure item 6)* | `src/ccf/peering/admission.py::union_lineage` plus `AdmissionRecord` / `ADMISSION_RECORD` (`class_id` `ccf.admission-record`); `tests/properties/test_lineage_union.py` for the set-union law itself; **`tests/peering/test_admission_record.py::test_the_union_is_observed_in_persisted_state_through_the_replay_path`** — the union read back out of the ArtifactStore through `ccf.replay.engine.resolve_artifact`, deliberately **not** off the transient `AdmittedProduct` wrapper | Replacement in either direction. The two operator sets are disjoint in the fixture by deliberate choice, so taking the producer's wholesale loses `temporal.as-of` and ignoring it loses what actually produced the product. **And — this is what B2 found — a claim resting on the wrapper:** `AssemblyWorker.ingest_admitted` never reads `admitted.lineage`, so before 06-19 the union was a property of an object L2 discards. `::test_an_admission_persists_an_admission_record` and `::test_a_store_outage_is_not_reported_as_an_admission` fail if a crossing is reported admitted with no record behind it |
| 15 | **Canonical bytes survive both wires unchanged** | `tests/crossproc/test_peering_exchange.py`, every case parametrized over the typed-HTTP and LF A2A legs | Any re-serialization en route: the signature is over the producer's canonical bytes, so a normalizing transport refuses the *genuine* product, not only the tampered one. An assertion that had to differ per transport would mean the Contract was not the stable layer |
| 16 | **No-Hardcoding across the phase's new surfaces** | Lint rules `cinv01a-prompt-shape`, `cinv01b-numeric-table`, `cinv01c-factory-bypass` via `tools.lints --all` | A peer id, ceiling, endpoint path, producer hash, server address, or federation entity class appearing in `/src` or `/runtime`. Every one lives in `tests/fixtures/banking/*.yaml`; the Peering transport fixture's own header (`a2a.yaml` — named for the wire it configures, per D-IMPL-59 part 2) states that deleting it leaves the test module with nothing to run |
| 17 | **Algorithmic ⇄ Semantic Alternation over the new modules** | Lint rule `cinv03-algorithmic`; `tests/crossproc/test_mcp_acquisition.py::test_no_llm_client_is_reachable_from_the_acquisition_path` | An LLM client reachable from the decision-time acquisition path — the module most likely to acquire one, since it is where content arrives |
| 18 | **Replay-by-construction: dimension 3 gains `harness_trace` and the record still carries exactly five dimensions** (D-25, D-IMPL-55) | `tests/conformance/test_harness_portability.py::test_a_live_record_still_carries_exactly_five_dimensions`, `::test_the_harness_trace_is_isolated_and_differs_per_harness`, `::test_the_governed_field_set_is_exhaustive_over_the_record` | A sixth dimension block — an INV-CH7-80 fidelity defect, not an option — or harness-attributable fields leaking into the governed comparison, which would make the portability equivalence trivially true |
| 19 | **An `mcp`-transport skill invoked through an `Agent` reaches its transport; an unwired deployment refuses by name rather than fabricating an endpoint** | `tests/integration/test_agent_slice.py::test_a_granted_mcp_skill_is_invocable_through_the_agent_seam` and `::test_an_unwired_deployment_still_refuses_an_mcp_skill_by_name` — an inversion pair over the same grant, entry and agent with only the registry withheld | Dropping `mcp_skills` anywhere along `AgentFactory` → `Agent` → `dispatch_skill`. The inversion is what stops the positive case passing against an implementation that had quietly stopped fail-closing; the read also asserts the URI the *deployment* registered, so a threading that arrived by fabricating an endpoint fails too (T-06-24) |
| 20 | **The MCP artifact server authenticates, backed by mechanism rather than by an unbacked claim** (D-26) | `SourceBackedTokenVerifier` against `FastMCP`'s `TokenVerifier`, with the dev token source behind a Protocol (`tests/crossproc/servers/mcp_artifact_child.py`); `tests/conformance/test_artifactstore.py::test_a_store_presenting_a_rejected_token_is_refused_as_an_outage` | A server that accepted any token, or a store whose rejected token surfaced as something other than an outage. §7.4's "authenticated" would otherwise be a word in a docstring. Real custody backends (PKI/HSM) remain out of v0 per §13, exactly as D-13 scopes A2A key custody |
| 21 | **What the federated gate sequence checks is attribution, not verification: INV-CH7-47 is verifiable *within* a fabric and attributable *across* one** *(narrowed — **closes B1**; D-IMPL-57 reading (a), closure item 2)*. What admission establishes is that the declared operator plan is covered by a signature from a key the peer was entitled to use, and is therefore **non-repudiable** — not that the plan was run. **Accepted consequence, carried across from Dave's ruling in its own words rather than softened: *a compromised or buggy peer can assert an operator plan it did not run, and the consuming fabric will admit the product.*** A narrowing that omits the cost is not a narrowing | `ccf.products.gates.run_federated_gates` (`GATE_LINEAGE_ATTRIBUTABILITY`, `LineageAttributionRefusal`) — the federated sequence is empty-operator guard → **attributability** → TTL bounds, sharing gates 1 and 3 with the local sequence rather than duplicating them; `src/ccf/peering/admission.py::_run_federated_gates` passes check 2's verified content address as an **independent** witness; `tests/gates/test_federated_gates.py` (10 cases, incl. `::test_the_federated_sequence_takes_no_engine_resolved_witness`); `tests/peering/test_admission_attributability.py::test_a_signed_but_non_canonical_payload_is_refused_as_unattributable` drives the case end-to-end **through `admit`**, asserting that signature verification *succeeded* first | Restoring the vacuous invocation. Before 06-18 the sequence was handed `engine_resolved=product.lineage.operators_invoked` — the producer's *own* claim as its own witness — and the module docstring said so ("structurally vacuous here"). 06-18 measured the counterfactual: with the old wiring restored, 3 of the 6 attributability tests fail and the unattributable product is admitted. Also fails: a product whose bytes differ from the bytes whose signature verified, and a lineage tampered under the original signature (which refuses at the *signature* check — the property reading (a) stands or falls on) |

**Every row names an existing, passing `file::function` or lint rule id, and every row states
its failure mode.** The D-17 bar is met.

---

## 3. Requirement and Success-Criteria Evidence Map

### 3.1 XPRC-01 — bidirectional MCP

**One row per consumer of the MCP client, not one row for the client library.** The library
existing is not a seam being bound (D-21): what makes an edge *bound* is that removing the
binding breaks a test.

| Edge | Evidence | What would fail |
|------|----------|-----------------|
| **L1 ingress** (06-06) | `tests/crossproc/test_mcp_ingress.py::test_records_cross_the_process_boundary_into_valid_envelopes`, `::test_acquired_signal_reaches_the_graph_only_through_l2`, `::test_two_tenants_over_one_live_adapter_stay_isolated` | An adapter interpreting the payload (L1 does not), or acquired signal reaching L3 other than through L2. The two-tenant case is the D-23 multi-principal requirement |
| **L4/L5 decision-time acquisition** (06-17) | `tests/crossproc/test_mcp_acquisition.py::test_the_served_payload_carries_a_value_only_the_child_had`, `::test_the_operator_plan_ran_with_no_io_of_its_own`, `::test_two_principals_over_one_acquirer_receive_only_their_own`; `tests/projection/test_acquisition.py::test_acquisition_runs_after_the_operator_plan_and_before_invoke` | **Removing `ProjectionEngine`'s acquisition stage makes both files fail** — that is exactly what distinguishes a bound edge from an importable class. The payload carries a value only the child process held, so an in-process shortcut cannot produce it |
| **L6 egress server** (06-04) | `tests/crossproc/test_mcp_egress.py::test_the_product_crosses_the_process_boundary_intact`, `::test_the_server_advertises_the_product_resource`, `::test_a_foreign_address_is_refused_rather_than_served` | A server that served an address it was not asked for, or a product that did not survive the boundary intact |
| **ArtifactStore role** (06-05) | `tests/invariants/test_mcp_role_separation.py` (rows 5, 13); `tests/conformance/test_artifactstore.py` | Merging the artifact role into egress, or the store acquiring a route into L3 |
| **Experience layer** | **DEFERRED to Phase 7 (I.4) — no I.3 evidence, and none is claimed.** | *(see the deferral note below)* |

> **Checklist row — Experience-layer MCP edge, deferred.** Criterion 1 names an Experience
> edge among the MCP client's consumers. `06-CONTEXT.md` defers the Experience Layer front
> doors (CLI, HTTP API) out of I.3, and the ROADMAP places EXPR-01/02/03 in **Phase 7**. So
> criterion 1's Experience edge has **no I.3 evidence and is not asserted to have any**. A
> reviewer reading criterion 1 is reading a *named scope boundary*, not a missing leg. Where
> it lands: Phase 7, alongside the CLI and HTTP front doors.
>
> **Amended by 06-22 *(closes A5)*.** This note previously ended: "The ROADMAP criterion text
> stands as written and is not amended — only its evidence section records the boundary."
> That was precisely the gap the review found. The gate deferred the edge honestly while the
> criterion kept naming it, and a criterion that reads broader than its own evidence is an
> over-claim wherever the honest sentence happens to live. ROADMAP criterion 1 now names the
> edges I.3 delivers and records the Experience edge as Phase 7 scope, so the two documents
> agree rather than one compensating for the other.

### 3.2 XPRC-02 — Peering federation (A2A is the reference transport, not the concept)

**Vocabulary, per `D-IMPL-59` (Dave, 2026-07-27).** The federation seam is a **Peering**: a
governed exchange between two peer fabrics, each holding its own Control Plane. Its Protocol
is `PeeringProtocol` (`src/ccf/peering/protocol.py`), and **A2A is its reference transport**,
alongside the standard-free typed-HTTP leg. MCP is explicitly *outside* the Peering seam
(part 3): MCP ingress is asymmetric — there is no counterparty Control Plane to verify
against, and it **originates** lineage rather than merging it — so it remains its own surface
per CLAUDE.md §7.1. Where this document previously said "A2A" for the *category*, it now says
Peering; where it says A2A, it means the wire.

| Element | Evidence | What would fail |
|---------|----------|-----------------|
| Typed products across real processes, behind `PeeringProtocol` | `tests/crossproc/test_peering_exchange.py::test_a_signed_product_crosses_two_processes_and_is_admitted`, `::test_the_transport_satisfies_the_wire_protocol`; every case parametrized over both wires (row 15) | An in-process double: the producer is a separate OS process with its own graph file and heap, which is what makes "the consumer holds no write handle to the producer's graph" literally true rather than argued (D-15) |
| Identity and signing (D-IMPL-15) | `src/ccf/peering/identity.py` (detached JWS, ES256); `tests/peering/test_admission.py` signature cases; two peers with different keys and entitlements (D-23) | A single-principal proof passes against a gate that checks signatures over every key it holds — which is exactly the defect the two-peer case catches |
| Admission before L2 (D-IMPL-16) | `src/ccf/peering/admission.py` — `PeeringAdmissionGate`, six ordered checks; rows 6, 7, 21; `tests/invariants/test_peering_single_writer.py::test_a_refused_product_leaves_l3_byte_identical` | A consumer that ingested first and checked after. The refused message's entities would appear in the graph and the digest would move |
| Lineage set-union (D-14), and where its continuity lives (D-IMPL-58) | Row 14 | As row 14 |
| What the lineage gate checks at the boundary (D-IMPL-57) | Row 21 | As row 21 |
| A Peering declares trust *inputs*, never the verdict (D-IMPL-59 part 4) | `tests/peering/test_peering_verdict.py` (6 cases): a purpose-built `_ForgingPeering` that satisfies `isinstance(..., PeeringProtocol)` and attempts to construct an `AdmittedProduct` outside the gate raises `AdmissionBypassError`; `::test_no_discovered_transport_names_the_verdict` is parametrized over the *discovered* transport set, with `::test_transport_modules_were_actually_discovered` as its count guard | A transport arriving with its own private check. 06-24 measured the counterfactual: with the token comparison neutered to `if False:`, the forging case fails with `DID NOT RAISE`. **This is a verified property, not a design intention** — the same structural device as the harness adapter's inability to acquire a write handle, applied at a second boundary |

#### 3.2.1 What the Peering re-description changed, and what it deliberately did not

Recorded because a rename that is not scoped reads as a rebuild, and because the vocabulary a
reviewer reads should be the vocabulary the code uses.

- **Changed:** the seam's package (`ccf.peering`, `ccf_runtime.peering`), its Protocol
  (`WireProtocol` → `PeeringProtocol`, suffixed per the naming ruling recorded alongside
  D-IMPL-59), the gate (`PeeringAdmissionGate`), the trust-policy artifact
  (`PeeringTrustPolicy` / `PEERING_TRUST_POLICY`), the audit verdict members
  (`peering_admitted`, `peering_admission_refused`), the gate id *values* (`a2a-*` →
  `peering-*`), the skill surface (`peering` skill type,
  `Peering{Binding,Invocation,SkillRegistry,SkillUnregistered}`, `peering_skills=`), and the
  test tree (`tests/peering/`).
- **Deliberately not changed. No code was deleted** — the constraint was checked as
  `git diff --diff-filter=D --name-only pre-peering -- src/ runtime/ tests/ tools/` producing
  no output, against the pinned tag `pre-peering`
  (`f45a23d639816ef40f3b169194628f4669012c9b`), and every move is a `git mv` recorded as a
  rename. **A2A is not withdrawn** (part 2): it remains a v0 commitment and the reference
  transport. Transports keep their protocol names (`lf_a2a.py`, `typed_http.py`, `LfA2AWire`)
  — a transport is correctly named for the wire it speaks. `AdmittedProduct`,
  `ingest_admitted`, `union_lineage`, `InboundProduct` and `PeerRef` were **already
  transport-neutral**; only their docstrings said A2A. Nothing under `src/ccf/mcp*` or
  `ccf_runtime/mcp/` was touched, which is part 3 stated as a diff check.
- **One residual, named rather than left to be discovered:** the CINV-02 boundary test
  `tools/lints/tests/test_harness_imports.py::test_a_harness_import_in_the_a2a_module_is_still_flagged`
  still carries `a2a` in its *function name* while the module it feeds is
  `ccf_runtime.peering.lf_a2a`. The assertion is correct; only the label lags.

### 3.3 XPRC-03 — harness adapters

| Element | Evidence | What would fail |
|---------|----------|-----------------|
| `HarnessAdapterProtocol` + three reference adapters (D-IMPL-24) | `src/ccf/harness/protocol.py`; `runtime/ccf_runtime/adapters/{claude_agent,langgraph,adk}/`; `tests/conformance/test_harness_adapter.py` parametrized over all three (188 passing) | Rows 9–12 |
| All four seams bound | Row 10 | Row 10 |
| Zero harness imports in core | Rows 1–2 | Rows 1–2 |
| **Seam-level portability demonstrated at four seams; loop-level portability outstanding** *(narrowed — **closes B3**; see §3.3.1)* | `tests/conformance/test_harness_portability.py::test_the_consumed_product_is_byte_identical_across_the_three_harnesses`, `::test_the_governed_replay_fields_are_exactly_equal_across_harnesses`, `::test_the_agent_definition_names_no_harness`, `::test_two_agents_each_equal_across_harnesses_and_distinct_from_each_other`, plus the four adversarial cases 06-20 added (`::test_a_leg_that_corrupted_the_governed_emission_turns_the_equality_red`, `::test_a_leg_that_corrupted_its_reported_trace_is_detected`, `::test_a_dropped_harness_trace_is_caught_by_liveness_not_by_absence`, and the conforming-adapter pin) | An agent definition naming a harness; or a "portability" proof that compared nothing, which the exhaustiveness and two-agent tests are there to prevent. **The "compared nothing" hazard is now fully closed on all three compared axes, not on the consumption axis alone:** every equality the module asserts has a demonstrated failure mode, driven through the same `_drive` the honest legs use. 06-20 measured the counterfactual — reducing the adversarial wrapper to a pure delegate produces `DID NOT RAISE AssertionError` |

#### 3.3.1 What the portability evidence proves, and what it does not (closes B3)

The row label above previously read **"Portability demonstrated, not asserted"**. That label
is supported in its *seam-translation* reading and unsupported in its *loop-execution*
reading, and the distinction is now written into the row rather than left to a reader's
charity. Blocking finding B3 was scope, not fraud.

**What the evidence proves.** Three adapters translate **one** agent definition into their own
harness-native carriers equivalently; recover the typed Context Product back out of those
carriers byte-identically; expose exactly the currently-bound skill-set; produce governed
emissions that a corrupted leg would break; and report **distinguishable**, per-harness
replay traces checked against each leg's own declared `reported_model` and `trace_id`. The
agent definition names no harness. Two distinct agents each stay equal across harnesses and
distinct from each other, so a per-catalog implementation cannot pass a per-agent claim.

**What it does not prove.** No harness reasoning loop is executed. `_drive` calls the four
seams directly — `inject_context` → `expose_skills` → `capture_effect` → `replay_trace` —
which is the whole of what runs. And the limit 06-20 was required to record verbatim:

> **All three shipped adapters' `capture_effect` remain delegations to `Agent.emit_effect`, so
> the honest three-leg emission equality still cannot fail. The adversarial leg proves the
> assertion is sensitive to perturbation, not that the three adapters are independent
> implementations.**

Any document reading the emission axis as three independent implementations *agreeing* is
over-claiming. The defensible reading — and the one the suite's own module docstring states —
is **"the fabric, not the harness, decides what an effect is."**

**Where the unproven half lands, handed forward rather than deleted.** Loop-level execution of
one agent definition under two real harness loops is **`examples/03-harness-portability`'s
obligation in Phase 8 (I.5)**, per CLAUDE.md §9 example 03, which §7.3 assigns to the examples
suite. So §7.3's "one agent definition **running unmodified** under at least two harnesses" is
**outstanding**, not discharged here — I.3 delivers the mechanism that obligation is built on.
`CLAUDE.md` is Dave's document and is deliberately **not edited** by this phase; if the phase
believed §7.3 needed amendment, that would be a request in §6, and none is made.

**Also outstanding on this axis: advisory A3** — the Claude leg's seam-4 `execution()` is a
hand-built `ResultMessage` seeded from fixtures, while ADK and LangGraph push values through
real harness machinery. **A3 is not closed.** See §5.

### 3.4 The five ROADMAP Phase 6 success criteria

**Criterion 1 — bidirectional MCP; ArtifactStore role in a distinct module from egress.**
§3.1 above, edge by edge, with the Experience edge recorded as a Phase 7 deferral. Role
separation: rows 5 and 13.

**Criterion 2 — Peering behind `PeeringProtocol` with identity, admission and lineage union.**
§3.2 above. The D-IMPL-14 default wire (LF A2A) and the standard-free typed-HTTP leg both
ship, and every assertion runs unchanged over both — the substitution claim, checked rather
than stated. **Two narrowings on this criterion, both traceable:**

- *(closes B1, D-IMPL-57 closure item 2)* **Lineage is attributable across the Peering
  boundary and verifiable within a fabric.** Strict-equality verification does **not** travel:
  the consumer never re-resolves the producer's operator plan, it holds the producer to what
  it signed. Row 21 states the accepted consequence in Dave's own words.
- *(closes B2, D-IMPL-58 closure item 6)* **Lineage continuity is a property of the Peering
  admission boundary, persisted as an immutable `AdmissionRecord` and resolvable at an exact
  version** — not a property of graph state. Row 14. `LineageEntry` is untouched.

**Criterion 3 — `HarnessAdapterProtocol` + reference adapters bind all four seams; the
zero-harness-imports lint stays green.** §3.3 above; rows 1, 2, 9, 10. **Narrowed** *(closes
B3)*: what is demonstrated is seam-level equivalence across three harnesses with a
demonstrated failure mode on every compared axis — **not** execution under a harness reasoning
loop, which is example 03's Phase 8 obligation. §3.3.1 states both halves, including the
`capture_effect`-delegation limit verbatim.

**Criterion 4 — single-writer demonstrably holds across three boundaries.** Three separate
observables, deliberately not one:

| Boundary | Observable | Row |
|----------|------------|-----|
| Peering | `tests/invariants/test_peering_single_writer.py` — scans, live exchange, refused-product digest | 3 |
| Adapter | `tests/invariants/test_adapter_single_writer.py` — scans plus the `emit_effect` → L2 path | 4 |
| ArtifactStore | `tests/invariants/test_mcp_role_separation.py` — byte-identical cycle, WAL-inclusive, with its sensitivity guard | 5 |

Strengthened this plan by Dave's ruling: the federated route into L2 is now a **typed door**
(row 6), so the Peering leg of this criterion is carried by the type system and not only by
observation — at the scope row 6 now states (advisory A2).

**Criterion 5 — MCP-backed ArtifactStore passes the *same* conformance suite as the
file-backed impl, with no other deployment change to swap.** `tests/conformance/test_artifactstore.py`
is factory-parametrized over both implementations: **the same suite, no test-body change, and
the swap is the factory parameter alone.** What would fail: an MCP store needing a relaxed
assertion — at which point the Protocol would not be the substitutable layer, and example 07
(Phase 8) could not be written.

---

## 4. Discretionary Choices (in-phase judgment, NOT new `D-IMPL` entries)

Recorded for the reviewer, per the I.2 precedent. One genuine whitepaper-silent gap *did*
surface and is logged as a decision — see §4.12.

1. **The harness skip mechanism and `CCF_REQUIRE_HARNESSES`.** Deliberately the same shape
   as `CCF_REQUIRE_POSTGRES` rather than a second idiom: two mechanisms for "the environment
   can require what would otherwise silently skip" would drift, and a reader would have to
   learn both. The skip message is an instruction (which extra installs what), not a mystery.
2. **The module tree below the D-03/D-04 boundaries.** D-03 and D-04 fix where the MCP roles
   and the adapters live; the arrangement *inside* those boundaries
   (`ccf_runtime/adapters/<harness>/`, `ccf_runtime/peering/<wire>.py`,
   `ccf_runtime/mcp/{egress,artifact_server}.py`) was chosen in-phase to keep each adapter
   and each wire independently deletable.
3. **Extras composition.** `dev` composes `harnesses`, which composes the three per-harness
   extras. Research assumption A1 asked whether a self-referential extra resolves under the
   project's pip: it does, and `pip check` is clean — so the documented one-command install
   (D-08) remains one command.
4. **The `Part` field chosen for the LF A2A payload** (research assumption A2). The canonical
   bytes travel in a `bytes`-carrying part rather than through a protobuf `Struct`. A
   `Struct` would re-serialize, and the signature is over the producer's canonical bytes, so
   the genuine product would stop verifying. Asserted directly in
   `tests/crossproc/test_peering_exchange.py` rather than inferred.
5. **The mypy override scope** (research assumption A3) — **corrected, and the correction
   matters.** Four vendor overrides (`google.adk.*`, `langgraph.*`, `langchain_core.*`,
   `claude_agent_sdk.*`) were **measured inert and removed in 06-16**: all four packages ship
   `py.typed`, and `mypy` passes over `src` + `runtime` with none of the blocks present,
   verified by deleting them and re-running. `mcp` and `a2a-sdk` ship `py.typed` too and
   never had a block at all. The removed comments asserted the opposite — "ships no py.typed
   marker" — for every one of them. This is the **mirror image** of the D-21 defect: a claim
   of *looseness* that does not hold understates the enforcement in force, and a gate citing
   "these vendor boundaries are not strict-checked" would have been describing a config
   rather than the build. Those seams are genuinely strict-checked.
6. **The `AdmittedProduct` token-versus-lint decision, with its stated reason and its live
   counter-precedent.** D-12 *removed* a construction token from `Agent` in favour of the
   CINV-01c lint, so a token is not house style and its use has to be argued. The argument:
   an `Agent` is constructed by an in-process factory the SDK controls, so a lint over the
   SDK's own code answers the question. An `AdmittedProduct` describes something that arrived
   from an **untrusted remote peer**, and its constructibility *is* the trust boundary — the
   property needed is not "SDK code went through the factory" but "nothing outside this
   module can produce the value L2 accepts, however it got here". A lint cannot say that
   about code the SDK does not ship: a deployment's own transport, or a third-party wire.
   So the token stays and the claim stays strong (row 7's class). The corresponding
   `AgentFactory` docstring, which still led with "no path", was rewritten in 06-16 to its
   actual enforcement.
7. **Threading the Peering skill registry alongside the MCP one.** Dave's ruling named
   `McpSkillRegistry`; `PeeringSkillRegistry` (then `A2ASkillRegistry`) had the identical gap and the identical shape, and
   closing one alone would have re-opened the same deferred item under a different name. Both
   are optional and fail-closed, on the established `callable_registry` precedent.
8. **`FederatedIngestSpec` carries the federation vocabulary.** `ingest_admitted` needs to
   know which payload member holds the peer's records and how the peer's key names map onto
   the consumer's; both are deployment statements, so they live in a declared spec and not in
   `/src`. The SDK ships no default key name and no default correspondence.

### 4.9 D-21 phrase sweep, both forms

Swept over shipped docstrings (`src/`, `runtime/`), this document, and the phase's plan set,
for **every** occurrence of "by construction", "no path", "cannot", and "impossible" —
whether or not accompanied by an explanatory clause.

| Corpus | Hits (`by construction` / `no path` / `impossible`) | Disposition |
|--------|------|-------------|
| `src/` + `runtime/` docstrings | **28** (185 including the much looser "cannot") | 27 name the structural reason or the enforcing mechanism in the surrounding sentence; **1 rewritten in 06-16** — `AgentFactory`'s "there is no path to an `Agent` that bypasses this class", which D-12 had reduced to a lint-enforced property. Now stated as such, with the `AdmittedProduct` contrast |
| This document | see rows | Two claims use strong wording and are argued to earn it: **row 7** (the trust policy has no field that could express a skip — `extra=forbid` makes adding one a visible schema change) and **row 8** (`local_callable` dispatch imports nothing; a dotted path is not a value the resolution surface can express). Every other row is scoped to lint, scan, or conformance evidence |
| Phase plan set | **57** | Plan text is not a shipped claim; the ones that became shipped claims are covered by the two rows above |
| Quotations | — | The legitimate exception class: quotations of CLAUDE.md or the whitepaper (§6.5's "harness-neutral **by construction**", §8.1/§8.2's replay commitments quoted verbatim in the two skip-reason strings). Marked as quotations wherever they appear, and not rewritten — rewriting a quotation would misreport the source |

### 4.10 Thirteen false acceptance criteria — a process finding worth recording

Waves 2–6 found **thirteen** acceptance criteria across this phase's plans that were false
against the actual code. The gate records this because the *pattern* is more useful than the
count:

- Several would have passed **only on a wrong implementation** — one required breaking
  idempotent re-delivery; one required a `model_fields` count already false; one demanded a
  property whose literal implementation would have tempted a write path into an adapter.
- One selected **zero tests** and would have "passed" by executing nothing (a `-k` selector
  matching no name exits 5). 06-15 subsequently verified all of its selectors non-empty
  pre-emptively, which is now the practice.
- One directly contradicted its own task's action text.
- **The dominant defect, by a wide margin: a grep over source text standing in for a
  structural property.** Text matching cannot distinguish a violation from a *mention* of
  one, and multiple criteria tripped on docstrings that documented compliance.

The reliable replacements, all proven in this phase and used throughout §2: **AST
identifier/import scans** (a docstring is an `ast.Constant`, not an identifier),
**type-level constraints** (row 6), and **inversion/mutation tests** (rows 5, 19). Carried
to Phase 7 planning as a standing constraint.

### 4.11 Environment interference between parallel worktrees

Worktrees isolate the filesystem but **all agents share one `.venv`**. 06-13 installed
`langgraph` while 06-09 was mid-flight, retroactively falsifying two tests' environmental
premise (row 11). 06-09 measured the failures correctly and attributed them correctly. The
durable fix was the `ABSENT_HARNESS` sentinel; the durable *lesson* is that a test whose
premise is "this package is not installed" decays into vacuity exactly when the project
succeeds — and had those been written with `skipif` rather than as assertions, the decay
would have been silent.

Relatedly, the `pip check` breakage 06-14 reported was **venv drift, not a pinning defect**:
dry-run resolves of both documented install commands are internally consistent, and only a
long-lived incrementally-mutated venv reaches the broken state. CI resolves from scratch and
never sees it. `pip check` is clean (§1).

### 4.12 One new decision surfaced: `D-IMPL-56` (OPEN)

`SkillCatalogEntry` declares **neither a tool description nor an argument schema**, yet ADK's
`FunctionTool`, LangGraph's `StructuredTool`, and the Claude Agent SDK's tool block all want
both. **All three adapters surfaced it independently**, which is the signal that it is not an
adapter's problem. 06-12 set the in-phase precedent — compose the description from fields the
entry already carries, and transcribe `Agent.invoke_skill`'s `Mapping[str, str]` into one
shared schema constant — and 06-13/06-14 followed it, rather than authoring prose in SDK code
(a No-Hardcoding breach) or inventing three descriptions (which would break the D-18
equivalence 06-15 proves). That is a workaround. Where the fields belong is the skill-catalog
artifact schema — a Control Plane decision (CLAUDE.md §6.2, D-IMPL-12/28), not an adapter's.
Logged in `docs/DECISIONS.md` as **D-IMPL-56, awaiting Dave**.

See also §4 item 5 and §4.9 — the other two places this phase corrected a claim about its
own enforcement rather than about its code.

### 4.13 Citation-resolution sweep (added 06-22, prompted by A4)

Advisory A4 was a citation pointing at a directory that existed and held *different* tests —
the failure mode a reader cannot detect by following the link, because following it succeeds.
So the correction is not just row 1's path; it is a mechanical check that every path and every
`file::function` this document names resolves. Run over the whole document after the 06-22
edits:

| Sweep | Result |
|-------|--------|
| Backticked `tests/`, `tools/`, `src/`, `runtime/` paths extracted and `test -e`d | **47 checked, 0 genuinely missing.** Four were flagged and all four adjudicated: three (`runtime/adapters/`, `runtime/mcp/`, `runtime/peering/`) are extraction artifacts of `ccf_runtime/adapters/`, `ccf_runtime/mcp/`, `ccf_runtime/peering/`, all of which exist; one — `examples/03-harness-portability` — **deliberately does not exist**, being the Phase 8 forward reference §3.3.1 hands the loop-level portability obligation to |
| Every cited `file::function` resolved to a `def` in the named module | **63 checked, 0 missing** |

A row citing a name that does not exist is the same defect class as a row claiming a property
that does not hold, and this phase has now recorded three instances of it (§1.1). The sweep is
cheap and is the reason a fourth is not sitting in this document unnoticed.

---

## 5. Handoff to Phase I.4

**Prerequisites — not notes.**

- **D-20 — `ControlPlaneStateStore.put` still neither audits nor requires a token.** The
  audit pairing in `grants.py` is paired-call *convention*. I.3 deliberately added no second
  consumer of that seam (the Peering admission gate resolves everything by pinned `(key,
  version)` and incurs no mutable state — stated explicitly in
  `src/ccf/peering/admission.py`). Note that 06-19 added an **ArtifactStore** write at
  admission (row 14); that is the artifact substrate per D-IMPL-27, not the
  `ControlPlaneStateStore` seam this item is about.
  **I.4 cannot inherit the convention**: workflow suspend/resume multiplies the call sites,
  and one missed pair is silent Control Plane state with no audit record (INV-CH7-71).
  Closing this — an audit-bearing write path, or a token the store requires — is a
  prerequisite for the first I.4 plan that touches the seam, not a follow-up.
- **D-22 — `test_consumption_discipline.py` remains a direct-import check with no transitive
  closure.** Adapter modules are now in the import graph. Any future widening of
  `ALLOWED_CCF_PREFIXES` needs a transitive-closure argument, as I.2's
  `ccf.controlplane.resolution` widening received — **never a precedent argument**. The
  claim the surface has earned is "`Agent`'s own imports reach no fabric layer", and
  `src/ccf/harness/protocol.py` says so in as many words; do not upgrade the wording.
- **D-IMPL-45 — `TraceCorrelationHook` attaches to the `harness_trace` slot in I.4.** The
  slot exists now (D-25/D-IMPL-55, row 18) and is isolated from the governed fields.
- **The `claude` CLI is not required by anything in this phase.** Noted explicitly so a
  reviewer does not read "Claude Agent SDK adapter present, no CLI installed" as a gap: the
  adapter binds the SDK's Python surface, and the conformance suite exercises it without a
  CLI.
- **`D-IMPL-56` (§4.12) is open** and touches the skill-catalog artifact schema. I.4's
  workflow definitions bind skills at agent nodes; a resolution before then avoids a second
  round of adapter-side derivation. **This is advisory A6's carry-forward target.** Consequence
  if it stays open: every future adapter re-derives tool description and argument schema in
  `/runtime`, and the first one to derive them differently **silently breaks the D-18 harness
  equivalence** 06-15 proves. Not a style note — a divergence that no current test would catch,
  because today all three adapters follow 06-12's precedent.
- **Advisory A7 — the LangGraph adapter's three-node topology (`_build_graph`) must not be
  inherited as a workflow engine.** It is documented and necessary: LangGraph is a
  topology-owning harness, so an adapter that bound its seams without declaring a graph would
  not bind them at all. But it is **the one place in this SDK that authors execution shape**,
  and `D-IMPL-17` scopes the in-SDK Workflow primitive to in-fabric coordination with durable
  orchestration behind `OrchestrationProtocol`. **Prerequisite for I.4's first orchestration
  plan:** the Workflow primitive is built against D-IMPL-17's boundary, *not* by generalizing
  `_build_graph` — an adapter's private topology is harness-internal (CLAUDE.md §13) and
  promoting it would make the SDK ship the loop it commits to never shipping (§7.3).
- **Advisory A3 — one of three seam-4 legs is a fixture echo, and it is not closed.** The
  Claude adapter's `execution()` builds a `ResultMessage` by hand from fixture values, while
  the ADK and LangGraph legs push values through real harness machinery. **Consequence:** the
  trace-equivalence evidence in §3.3 is **two-legged in substance**, not three. 06-20 reduced
  the exposure — the corrupted-trace and dropped-trace cases give the axis a failure mode
  independent of how any one leg's `execution()` is built, and the trace assertion now checks
  attribution against each leg's own declared `reported_model` and `trace_id` — but replacing
  the hand-built message with a real SDK-driven execution remains **open**. Carried to
  **Phase 8, `examples/03-harness-portability`**, where a real Claude Agent SDK execution is
  available and where §3.3.1's loop-level obligation already lands. Whoever writes that example
  owns A3; it is not discharged by anything in I.3.
- **The two remaining CINV-04 deferrals are I.4's** — `hitl-action-capture` and
  `workflow-trace-capture` (§1). Activating them is what takes the suite's skip count to
  zero.
- **Research assumptions resolved this phase:** A1 (self-referential extra resolves — §4
  item 3), A2 (LF A2A payload part — §4 item 4), A3 (mypy overrides — **corrected**, §4
  item 5). None remains
  open with unquantified risk.

---

## 6. What Dave Is Asked To Decide

1. Read §1 (what ran, in what environment, and the two evidence-integrity findings), §2 (the
   checklist — for any row that reads as a claim rather than as evidence, run the command it
   names and ask what would fail if the implementation were broken), §3 (requirements and the
   five criteria, including criterion 1's named Experience-layer deferral), §4 (discretionary
   calls, the D-21 sweep, and `D-IMPL-56`, §4.12), §5 (the I.4 handoff, D-20 first).
2. Optionally re-run, **from the repository root with the project interpreter**:
   `CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q -rs && .venv/bin/python -m tools.lints --all && .venv/bin/python -m mypy`
3. **Rule on `D-IMPL-56`** (§4.12) — it is open and does not block this gate, but it will
   accrue adapter-side derivations until it closes.
4. **Approve or reject the Phase I.3 gate.**

On approval — and only on approval — the `D-GATE-I.3` entry is appended to
`docs/DECISIONS.md` with the date, and `phase-i3` is merged into `main` with `--no-ff`, the
merge commit referencing the gate entry (CLAUDE.md §2.2, §3.1 step 4). Phase 7 begins after
both, and not before.
