# 24.7 close-time panel — the findings already known (do NOT re-derive these)

You are reviewing the SHIPPED code of Phase 24.7 (`phase-24.7` at `ad8dc5a9`, diff base `6a019322`).
Everything in this file is already known, measured, and recorded in the phase's close record
(`24.7-CLOSE-PREP.md`) and the plan SUMMARYs. **Do not spend your budget re-deriving any of it.** For each
item, the question we want answered is the one under **ADJACENT** — where else the same class of defect,
omission, or design choice might live, and what each suggests about the neighborhood of the code you are
reading.

## What the phase did (one paragraph, for orientation)

Two SDK surfaces. **G-26:** `src/ccf/products/request.py::ArgumentDomain` now declares numeric bounds OR a
closed member set (`members`), exactly one shape; membership is exact typed equality; a miss is the ninth
`ProductRequestViolationReason` `not-in-domain`; `src/ccf/products/request_schema.py::render_request_input_schema`
derives `enum`/`minimum`/`maximum` from the declaration (one declaration of record) with NO publication surface;
`ProductRequest.intent` is judged against `ProductDiscovery.intents` in three states (no declaration → unjudged;
declared → authoritative; declared empty → serves none) by `request.py::refuse_intent`, hosted in
`resolver.py::GovernedResolver.resolve` before resolution, and an `intent` key under `arguments.properties` is
refused at contract construction as a shadow declaration. **G-33:** `constraints.py::resolve_effective_request`
returns `ResolutionOutcome(evidence, refusal)` at every exit; the governed resolver's refusal branch records the
partial resolution and its pins; `record.py::build_replay_record` REQUIRES `resolution=` — an `EffectiveRequest`
or a typed `ResolutionNotApplicable(reason=…)` (`no-resolution-step` | `refused-before-resolution`), `None` →
`ValueError`, omission → `TypeError`; `RefusalRecorderProtocol.record`, `ReplayRefusalRecorder.record` and
`GovernedResolver._record_refusal` require the same state; the two delivery-boundary denials state
`refused-before-resolution`; the legacy sentinel `no-request-resolution` stays the field default, readable and
hash-transparent; `engine.py::replay` refuses (`ReplayResolutionClaimMismatch`) a record whose marker claims
not-applicable while a PINNED `ProductRequestContract` or `PolicyConstraint` binding shows resolution ran — a
`ProductClassDeclaration` pin is deliberately NOT a trigger.

## K1 — the two carried pre-phase reds (NOT this phase's; do not report them)

- `tests/invariants/test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]`
  — carried since 24.6; `CLAUDE.md` cleanup is deferred by ruling.
- `tools/docs_tests/test_requirement_ledger.py::test_the_uat_roster_matches_the_records_on_disk` — the F-E
  gate-tools red carried by ruling since 24.6.

Everything else is green on the close tree: lint 0, mypy clean (217 files), chunks 2830 · 913 · 570 · 1850 passed,
legs clean, product gates 58/58.

## K2 — discretion choices taken under the rulings, each with the alternative it rejected

1. **`class-mismatch` is reused for the intent refusal** (`refuse_intent` returns `ProductRequestViolation`
   with `reason="class-mismatch"`, `key="intent"`). Rejected alternative: a tenth reason token — criterion 7
   fixes the vocabulary at nine, and the whitepaper §6.3 makes `intent` an addressing token, so the class
   "does not answer this question" reading is the existing one. **ADJACENT:** is there any consumer (door,
   status table, disclosure table, client) that reads `class-mismatch` and would now mis-handle a
   `key="intent"` instance — e.g. a message, a status, or an equivalence test that assumed
   `class-mismatch` always means the class id?
2. **`NOT_DISCOVERABLE` is compared by EQUALITY** (`discovery == NOT_DISCOVERABLE`), so a class whose
   declaration is written with the sentinel's exact content (`domain: not-discoverable`, all sets empty) is
   read as "no declaration exists" and its intent is UNJUDGED. Rejected alternative: identity (`is`), which
   would judge a same-content declaration as "declared empty → serves none". The ruling's words for the state
   are "no discovery declaration exists"; the docstring says so; a test pins it. **ADJACENT:** where else does
   the SDK distinguish absence from an empty declaration by a sentinel object, and does any of those compare
   by identity instead — and could a deployment config round-trip (YAML → model → YAML) turn an absent
   `discovery` into a same-content one, or vice versa?
3. **The `detail`-only channel for BOTH the enumerated set and the intent set** (ruled, am.3 A-8 a). The
   allowed set of a `not-in-domain` refusal and the declared intent set of an intent refusal ride ONLY in
   `ProductRequestViolation.detail`, so `PERMITTED_AT_MINIMAL` governs their exposure with no new disclosure
   row; `declared_type` carries the property's `JsonSchemaType` (or `None` for intent). Rejected alternative:
   carrying the set in `declared_type` (a `PERMITTED_AT_MINIMAL` member) — the executed sabotage shows it leaks
   at `minimal`. **ADJACENT:** is there any OTHER field on `ProductRequestViolation` (or on `ConstraintRefusal`,
   `PolicyResolutionConflict`) that a future reason could stuff a set into and that crosses at `minimal`? Does
   the `detail` string itself ever reach a channel that is not disclosure-governed (a log, a trace, an MCP
   tool-error string)?
4. **The intent refusal pins the deciding class declaration** (ruled, am.3 B-3 a) on dimension 2 beside
   `ResolutionNotApplicable(reason="refused-before-resolution")`, with `execution=None`, no request-contract
   pin and no constraint pin. **ADJACENT:** which other pre-resolution verdicts in `GovernedResolver.resolve`
   (tenant, class, lane, address, tier) mint a record, and do they pin what decided them, or nothing? Is
   there a pre-resolution verdict that mints NO record at all and therefore leaves no replay of the denial?
5. **Field name `members`** on `ArgumentDomain` (not `enum`), so the declaration is not itself named after
   the advertisement (P-1). **ADJACENT:** none needed; naming.
6. **The paired outcome is `ResolutionOutcome(evidence, refusal)`**, both required, no defaults; `completed`
   is a property. **ADJACENT:** is there any caller that still branches on `isinstance(x, EffectiveRequest)`
   or on the retired refusal union anywhere outside `examples/` (which is frozen and quarantined)?
7. **`ResolutionNotApplicableReason` has exactly two members.** The 12 SDK test recorder fixtures all state
   `no-resolution-step`, none `refused-before-resolution` (plan 06's per-site reasoning: a fixture states what
   it did, and none of them is the boundary). **ADJACENT:** is there a third genuine state the vocabulary
   cannot express — a path that STARTED resolution and was refused before producing any evidence at all
   (not the partial case, which carries `evidence`), or a served path that never resolves? If you find a real
   site, name the file and symbol; do not propose a token in the abstract.

## K3 — the D-11 evidence-base limitation (by design; not a finding)

`engine.py::_verify_resolution_claim` refuses a not-applicable marker only when a PINNED
`ProductRequestContract` or `PolicyConstraint` binding is present. A marker beside NO contract/constraint pin is
unfalsifiable from pinned state — deliberately: a class-declaration pin is not a proxy (the intent refusal pins
one legitimately). A record that omitted BOTH the resolution and its pins would replay as legitimate
non-applicability. In `src/`+`runtime/` a contract or constraint reaches `policy_bindings.bindings` only through
`GovernedResolver._applied_bindings(effective)`, which exists only once a resolution has run, so the SDK cannot
mint such a record today. **ADJACENT:** can a NON-reference resolver (a deployment's own `RefusalRecorderProtocol`
implementation, or a harness adapter) mint a record through the builder with a marker and no pins after
resolution actually ran — i.e. is the fail-closed guarantee builder-local while the pins are resolver-local?
Where is the seam that makes "resolution ran" observable to the builder independently of what the caller
chose to pin?

## K4 — plan 09's literal sabotage 2 fires nothing (measured difference, not a defect)

The by-name legacy exemption (`if value == NO_REQUEST_RESOLUTION: return`) is shadowed: the sentinel is not
JSON, so with the exemption removed the value falls into the shape guard's `except ValueError: return`. The
exemption stays as the stated D-12 promise (the `NO_GRAPH_QUERIES` precedent). The sabotage that proves the
legacy test live is the retroactive reading D-12 rejects (sentinel read AS a marker), executed red. **ADJACENT:**
is there any dimension-2 value that is neither the sentinel, a marker, nor an `EffectiveRequest` — a
malformed or hand-written string — that the shape guard silently EXEMPTS instead of refusing? Should "not a
marker" be "an `EffectiveRequest` parses" rather than "anything else returns"? Name the line.

## K5 — the wave-2→3 transient (closed; history only)

Between plan 04 (the required `resolution=`) and plan 06 (the 26 + 12 test sites re-derived), 38 SDK test
sites raised `TypeError`. Dave ruled it expected evidence. Closed at `f67bece3`. Two roster gaps were found
outside RESEARCH's walk and are recorded: `perf/suites/replay/conftest.py` (re-derived; SDK scaffolding) and the
twelve `archive/examples/` builder sites (ruled non-gating, `D-IMPL-265`, unedited). **ADJACENT:** is there any
OTHER tree the AST walk (`tests src runtime perf tools examples archive`) did not cover that calls
`build_replay_record` or a recorder — `docs/` code blocks, `public/`, a notebook, a Makefile target?

## K6 — `test_harness_trace.py`'s byte-identity test gained one `.replace()` (plan 06, Rule 3)

`test_every_pre_change_field_is_byte_for_byte_unchanged` removes every sentinel-default key from the produced
bytes and compares to a literal captured pre-extension; the stated marker is a VALUE, not a sentinel default, so it
now appears in the bytes and one more `.replace()` was added in the test's own prescribed pattern; the captured
literal is untouched. **ADJACENT:** does that `.replace()` chain now mask a real byte change elsewhere in the
record (i.e. is the pattern "one `.replace()` per extension" still a byte-identity proof, or has it become a
field-subtraction that could hide reordering)?

## K7 — the frozen examples (NOT the subject; do not report them)

`examples/` is diff-empty since the phase base; 162 `tests/examples/` ids are `xfail(strict=True)` naming
`D-IMPL-264` and their cause (builder explicitness cp-00..cp-03/s1-00/s1-01; contract construction cp-01..cp-04;
recorder explicitness and the return union on cp-04). `archive/examples/` is retired history (`D-IMPL-265`):
twelve runner modules and one perf parameter are `archived`-marked and deselected by default. A finding that
says "cp-04 is red" or "the archive does not compile against the new builder" is known and will be recorded as
re-derived. The in-phase fix `722e975e` (a docstring that quoted whitepaper §7.10 and tripped the publish-scan
shingle gate; paraphrased) is also known.

## K8 — the carry rows (open by ruling; do not report them as gaps)

- `24.7-C-01`: the render has no publication surface (MCP/HTTP/CLI) — deferred to the next Experience Layer
  phase by ruling (F-5 d). Reporting "the render is not reachable" is known.
- `24.7-C-02`: the perf `crossproc` suite spawns an archived example as its server — deferred to a perf-owning
  phase.

## What we want from you

For each of K2.1–K2.7, K3, K4, K5, K6: the ADJACENT question, answered against the bundled source with
`path.py::Symbol` citations that resolve. Beyond those: anything in the bundled `src/`/`runtime/` diff that
violates a named invariant — single-writer, composition-preservation, the three validation gates, Algorithmic ⇄
Semantic alternation (`request_schema.py` is `@algorithmic`), audit-by-construction, the No-Hardcoding Rule
(no prompt-shaped literal, no domain value in `src/`), zero harness imports in `src/`, `extra=forbid` on every
new contract, hash-transparency on every new defaulted field (there is exactly one: `ArgumentDomain.members`).
