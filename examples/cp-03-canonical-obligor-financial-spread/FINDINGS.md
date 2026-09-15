# Findings — cp-03-canonical

Findings raised while authoring this successor against the current SDK surface
(`CP14-F-22`, Dave, 2026-09-14). Each is adjudicated under `D-IMPL-315`: a richer
or different canonical path is a finding to adjudicate, never a licence to edit
the example. The question asked of every one is whether the behavior is
**legitimate SDK semantics** or an **actual mismatch**, with the basis stated.
Findings are raised, not resolved: every one below is Dave's to rule on.

## Closure of `CP14-F-22` — RESOLVED by a canonical sibling (Dave, 2026-09-14)

The canonical sibling and its roster admission were approved in principle on
candidate `d63f7c40`, conditional on two proof checks (`OFC-G26`, `OFC-G27`
and the isolated mutations S14b / S16b below), and merged after them. The
vocabulary is the gap ledger's, and the meaning is exactly this:

* **A real governed producer now exists for the required `credit-risk.spread`
  class.** The `D-IMPL-340` cross-process acquisition path is the acceptance
  path: a separately running producer supplies the class the composite
  requires.
* It does **not** mean the frozen producer was repaired (cp-03 and its
  quarantines are untouched), that every SDK finding below was resolved, or
  that CP-14 will serve every request: the spread can be delivered at
  tolerance `1.0` and is withheld at `0.25`. Producer availability and
  acceptability for a particular memo are different questions.
* `CP03C-F-01` stays **OPEN — SDK**. `CP03C-F-04`, `F-05`, `F-06` and `F-07`
  are carried forward, not fixed here.
* `examples/cp-03-canonical-obligor-financial-spread` is confirmed on
  `RULED_SDK_SUPPLIED_DEPLOYMENTS` by the same ruling.

---

## `CP03C-F-01` — the governed path records `from_entity_freshness` and computes `from_decision`

**Status: OPEN — SDK. Raised, not repaired. The serving half of the declaration
is held by this product's own declared gate; the expiry half is quarantined as
`OFC-G07` (`xfail(strict=True)`) and turns red the day the SDK honors it.**

### What was measured

`ccf_config.yaml` declares `ttl_anchor: from_entity_freshness`, as the
specimen did. The served contract carries `ttl_anchor="from_entity_freshness"`
and `expires_at = 2026-10-07T12:00:00+00:00` for a question asked at
`2026-09-07T12:00:00+00:00` whose freshest filing is `2026-08-10` — that is
`asked_at + 30 d`, not `2026-08-10T00:00Z + 30 d = 2026-09-09T00:00Z`.

The reason is structural, not a defect of this tree: `GovernedResolver`
computes `expires_at = decided_at + product_ttl_seconds` on every non-composite
branch (`src/ccf/products/resolver.py`, the candidate construction) and passes
`ttl_anchor=registered.ttl_anchor` through as a recorded field. Nothing in
`src/ccf` reads the anchor to compute anything: `grep -rn ttl_anchor src/ccf`
finds the type, the two contract fields, the artifact field and two
pass-throughs. `cp-04-canonical` declares the same anchor and is subject to the
same behavior; its configuration prose describes an entity-freshness expiry the
resolver does not compute.

### Why this matters here more than at rung 4

The filing-anchored window is the specimen's whole argument for the anchor
(`CP-SPEC-003` §E.1.1): rung 2 anchors on a date that never advances and refuses
permanently; rung 3 anchors on a date that moves as filers file, and its
refusals clear. A successor that silently served `asked_at + 30 d` would serve
every obligor in the estate at any instant, and the count `CP14-F-22` said rung
3 was to measure — how few obligors serve at the CP-14 instant — would read
fifty of fifty instead of three.

### What this tree does about it, and what it does not

* The class's declared product gate `cp-03-canonical.spread-freshness-window`
  (`D-IMPL-282` R-11) refuses a spread whose freshest filing plus the declared
  window is not after the asked instant. That is a deployment expressing its
  own invariant through the SDK's sanctioned slot, and it is the reason the
  population at the CP-14 instant reads three of fifty here.
* The contract's `expires_at` is NOT corrected by this tree. A product gate can
  refuse; it cannot re-anchor. The served contract therefore says
  `from_entity_freshness` and carries a decision-anchored expiry — the
  mismatch is visible on the contract, and `OFC-G07` asserts the declaration.
* No SDK code was changed (`CP14-F-22` §1, §9). Whether the resolver should
  compute `from_entity_freshness` from the served view's freshest `valid_from`
  — and over which entities — is a design question with more than one
  reading, and it needs its own decision id.

**The limitation, stated plainly (Dave's close ruling, 2026-09-14).** The
product checks the filing window at evaluation time, but the SDK currently
overstates the returned expiry for `from_entity_freshness`. This sibling does
not repair that contract mismatch. The product gate is therefore **not**
evidence that a previously returned copy remains valid until its advertised
`expires_at`: a copy served on 2026-09-07 advertises 2026-10-07 and would be
refused by the same gate if asked again after 2026-09-09. CP-14's
reconciliation must carry this — the composite's inherited expiry is not to be
treated as filing-anchored. Any SDK correction gets a separately recorded
decision and review.

### Readings for the ruling — none asserted

1. The resolver computes `expires_at` for `from_entity_freshness` classes from
   the maximum `valid_from` over the entities the served product touched, plus
   `product_ttl_seconds`, and refuses at the TTL gate when that is not after
   the decision instant. The product gate here becomes redundant and is
   removed.
2. The anchor declaration is redefined as documentation of the deployment's
   own gate, and `expires_at` stays decision-anchored by rule; the declaration
   is renamed or removed from the contract so it cannot say one thing and do
   another.
3. Something narrower for composites only, since `D-IMPL-336` F14 already
   floors a composite's expiry by its stalest admitted child.

---

## `CP03C-F-02` — one scratch root, one fabric: a door answering several questions served the first obligor's spread for the third question

**Status: FIXED in this tree (2026-09-14). A deployment defect found by the
door probe, not an SDK gap — and recorded because the failure was silent.**

### What was measured

The door hands every question the same assembly root. `deployment.connection`
first composed a FIXED file name under that root, so every question booted the
SAME SQLite fabric, which already held the previous questions' entities. The
third question, for an LEI that resolves to nothing, was SERVED: Π took the
first obligor entity in the view — the first question's — and the product's
gate saw an anchor inside the window. A stale obligor was likewise served with
the fresh one's anchor. Nothing raised; the content addresses differed, the
`D_c` matched the wrong obligor's.

### What was done

* `backends.yaml` already declared `database_path: {per_run: path}`;
  `deployment.connection` now mints a fresh `uuid` path per run, as the
  specimen did — the declaration and the behavior agree.
* Π takes the request's `subject` from the plan factory (the EFFECTIVE request
  the SDK hands it) and serves that obligor's claims and no other's. A view
  holding a second obligor cannot be served as this one's spread, whatever
  else is in it.
* `OFC-G20` holds the cross-deployment shape: a subject that resolves to
  nothing is refused by the child's own gate, never served another's figures.

---

## `CP03C-F-03` — `peer_basis: sic-and-size` was declared by the specimen and never implemented

**Status: NOT-A-GAP — a specimen observation; the successor declares only what
it answers.**

The specimen's contract and README offered `sic | sic-and-size`; its code read
the parameter only to echo it as `cohort_basis`, and selected the cohort by SIC
equality regardless. This tree declares `argument_domains.peer_basis.members:
[sic]`, so `sic-and-size` is refused `not-in-domain` as data (`OFC-G10`) rather
than accepted and ignored. Implementing a size band is a product decision for
whoever needs it, not a repair.

---

## `CP03C-F-04` — the `peer_set` λ_c row is declared and scores nothing

**Status: CARRIED from the specimen, deliberately. For Dave.**

The specimen declared three λ_c rows and built observations of two classes
(`annual_facts`, `quarterly_facts`); nothing was ever typed `peer_set`. This
tree preserves that, because `CP14-F-22` §8 forbids moving the debt reading,
and typing the cohort statistics as `peer_set` observations would move `F`.
The row is therefore configuration nobody reads — the shape `D-IMPL-323`'s
sitting called out at cp-08. Either the cohort statistics become observations
of that class (and the debt method changes, on a ruling), or the row is removed
from the successor's table.

---

## `CP03C-F-05` — a refusing producer reaches the consumer as `ineligible`, with neither its reason nor its record

**Status: OPEN — SDK observation, adjacent to the `D-IMPL-340` residuals.**

When the producer withholds the spread (`tolerance-exceeded`) or refuses on its
own gate, the consumer's `ChildResolution` row reads `outcome_status:
ineligible`, `refusal_ref: ineligible`, with the producer's identity and the
question address held — and without the producer's own refusal reason or the
replay reference its door returned in the `DoorOutcome`. The composite refuses
correctly (`child_admission`); an examiner reading the consumer's record cannot
tell a tolerance refusal from a window refusal from a suppressed obligor
without the producer's record. `D-GATE-340` recorded that a served answer with
`replay_ref=None` skips the replay-reference claim; this is the refused-answer
neighbor of that residual.

---

## `CP03C-F-06` — assembler identity is absent from the governed path's replay record

**Status: OPEN — SDK observation, carried from the specimen's own note.**

`build_replay_record` accepts `assembler_id` / `assembler_version`;
`build_governed_resolver` and `GovernedResolver.__call__` expose neither, so a
deployment on the canonical path cannot name its assembler in replay. The
specimen recorded the same absence on the hand-composed path ("Decision Replay
carries none of it today"). Not fixed here (`CP14-F-22` §1: no unrelated SDK
change).

---

## `CP03C-F-07` — cp-05's door constructs a `ProductRequestViolation` the contract no longer accepts

**Status: OPEN — observation about another tree, not touched.**

Copying `examples/cp-05-credit-exposure-rollup/server/serve.py`'s
`_wrong_address` verbatim produced a pydantic `ValidationError` inside the
door (`parameter=` is no longer a field; `key`, `declared_type`,
`presented_type`, `declared_keys`, `presented_keys` are required), which the
egress door surfaced as an opaque `ccf-runtime-failure`. This tree's door
constructs the current shape and returns `class-mismatch` at
`key=schema_version` as data with a record. cp-05's door has the same latent
mismatch on its wrong-address path and was not edited (`D-IMPL-261`).

---

## `CP03C-F-08` — `observed_at` is when the fabric learned the claim; a column's age is `valid_from`

**Status: NOT-A-GAP — a measurement recorded so the next reader does not
re-derive it.**

The first debt reading off the graph returned `F = 1` for a spread whose
columns are years old: `AssemblyWorker` sets the claim's `observed_at` to the
envelope's `ingestion_timestamp` (the request instant) and the envelope's
`observed_time` becomes `valid_from`. The specimen never met this because it
built its observations by hand from the period's own filing date. The
canonical form of that hand-dating is the declaration `D-IMPL-331` provides:
`decay_basis: valid-from` on the λ_c rows, with the filing carried as the
observation's `valid_from`. `OFC-G05` holds `F < 1`.

---

## Sabotage matrix

Each fix and each proof was made to fail deliberately at least once, on
2026-09-14, against the live estate: apply the mutation, run the target module,
restore the file by `git checkout`, verify the restoration by an empty
`git diff` — never by a clean status. Twenty-three constructible sabotages,
twenty-three RED; the tree was clean after every run.

| run | gate | mutation | verdict |
|---|---|---|---|
| S01 | `OFC-G01` | declare `intent` under `arguments.properties`, as the specimen did | **RED** (13 red) — the boot refuses the contract, so eleven tests error; the SDK's refusal is the control |
| S02 | `OFC-G05` | drop `decay_basis: valid-from` from both scored λ_c rows | **RED** (2 red) |
| S03 | `OFC-G06` | delete the window comparison from the product's gate | **RED** (1 red) |
| S04 | `OFC-G08` | raise for an unresolvable anchor instead of ingesting nothing | **RED** (1 red) |
| S05 | `OFC-G24` | compose a fixed fabric file name under the root | **RED** (1 red) |
| S06 | `OFC-G25` | drop Π's subject filter and take the first obligor in the view | **RED** (1 red) |
| S07 | `OFC-G16` | drop the door's producer assertion | **RED** (7 red) |
| S08 | `OFC-G18` | assert another producer's id at the door | **RED** (7 red) |
| S09 | `OFC-G19` | serve the class at lane `2.0.0` | **RED** (4 red) |
| S10 | `OFC-G23` | let the door retype `periods` to 4 | **RED** (1 red) |
| S11 | `OFC-G09` | remove the `discovery` declaration | **RED** (1 red) |
| S12 | `OFC-G10` | widen the `peer_basis` domain to `sic-and-size` | **RED** (1 red) |
| S13 | `OFC-G05` | score completeness as 1 rather than the evaluable fraction | **RED** (1 red) |
| S14 | `OFC-G02` | declare a second operator the class did not declare | **RED** (11 red) — red by the served fixture erroring (the mutation broke the serve before the gate's own assertion ran); the gate's specific claim was not isolated by this run |
| S15 | `OFC-G15` | append a line to the frozen specimen's README | **RED** (1 red) |
| S16 | `OFC-G03` | ingest one envelope carrying the whole spread, as the specimen did | **RED** (11 red) — red by the served fixture erroring (the mutation broke the serve before the gate's own assertion ran); the gate's specific claim was not isolated by this run |
| S17 | `OFC-G13` | import and call `build_replay_record` in the spine | **RED** (1 red) |
| S18 | `OFC-G14` | construct the plan from a literal operator set instead of `required` | **RED** (1 red) |
| S19 | `OFC-G21` | let the door override the caller's `debt_tolerance` | **RED** (1 red) |
| S20 | `OFC-G12` | let `latest-restated` drop a column | **RED** (1 red) |
| S21 | `OFC-G04` | stamp one accession over every line | **RED** (2 red) |
| S22 | `OFC-G01` | put a per-run nonce in the payload | **RED** (2 red) |
| S23 | `OFC-G17` | import the producer's assembler into the consumer process | **RED** (1 red) |

**Not constructible without an SDK edit, and recorded rather than faked:**
`OFC-G07` (the SDK computes the decision-instant anchor; the gate is the
`CP03C-F-01` evidence and goes red when the SDK honors the declaration) and
`OFC-G22` (synthesizing a child when the producer is unreachable would be an
SDK-side forgery; the gate holds the SDK's own `producer-unavailable` path).

Two verdicts are red for a coarser reason than the gate's claim: S14 and S16
broke the serve itself, so the served fixture errored and the gate's specific
assertion never ran. They are recorded as red-by-error, not as isolated proofs
of `OFC-G02` and `OFC-G03`, and they stay in the record as such.

### The two isolated mutations the close ruling required (2026-09-14)

| run | gate | mutation | verdict |
|---|---|---|---|
| S14b | `OFC-G02` | declare a second operator (`traversal.typed-neighborhood`) SEEDED FROM EVERY CLASS, so the view is unchanged and the product serves with two operators in its lineage | **RED** — the serve is green (`OFC-G01` passed; 2 red: the gate and its `OFC-G26` control), and the gate fails at its own comparison |
| S16b | `OFC-G03` | ingest ONE envelope (the obligor) and render the periods from a side channel — the specimen's payload-only representation, served | **RED** — the serve is green (`OFC-G01` passed; 3 red: the gate, its `OFC-G27` control and the debt gate, whose observations vanished with the graph), and the gate fails at its own comparison |

**Where the SDK holds no guard, said so.** Dimension 2 is built by
`GovernedResolver._applied_bindings` and stored verbatim by
`build_replay_record`; dimension 1's touched set is the execution's own
record. No validator cross-checks either against the product, and `OFC-G26` /
`OFC-G27` assert that the defective records CONSTRUCT. Those two controls
prove the gates' comparisons can fail; they do not prove the SDK refuses the
states.

## Re-expressed on the paved road — `D-IMPL-343` dogfood A (2026-09-15)

This tree is the first executable proof of the paved road: re-expressed IN
PLACE from the canonical `boot / acquire / govern` shape, with `acquisition.py`
(minus its environment reader), `projection.py`, the envelope mapping, the debt
rule, the gate predicate, the class and lane, the declared gate and the
twenty-seven gate ids unchanged. Measured, not asserted:

| measure | before (`f952b304`) | after |
|---|---|---|
| demonstration spread's content address at the CP-14 instant (BGC Group, tolerance 1.0) | `122e0a7b0b96565eac64af7cf2fbd0d5238c46529c1914b638b237187cd1c21e` | **identical** |
| its replay record's address | `b3d1c7b117552a2e231a2d23be1982a9ce624c3ed7c58ba6b115e95adaa6bceb` | **identical** — every one of the five dimensions is byte-identical, including dimension 2 (the record pins the sources the resolution consulted, and the three new sections are not among them) |
| `D_c` / signal | 0.8432753… / `fail_closed` | identical |
| code lines: produce / deployment / projection / acquisition / run / door (the counter is Appendix A of `docs/D-IMPL-343-DESIGN.md`) | 99 / 341 / 148 / 442 / 93 / 243 = 1366 | 29 / 222 / 148 / 433 / 107 / 25 = **964**; the plumbing that remains is `produce.py`'s two calls, `deployment.py`'s two ≈ 8-line adapters and the door's two lines |
| SDK names imported by the producer's Python | 30 | 19, of which 9 are the debt rule's own vocabulary (`DebtFactors`, `FreshnessScorer`, `Observation`, the two booted artifact types, the view, the envelope and its source identity, `DebtAssessment`) and 10 are mechanism |
| documents | 4 | 2 (`ccf_config.yaml`, `ccf_environment.yaml`) |
| values stated in two places | 6 (replay class; principal + role; the TTL window; class/lane in the door; five section keys; producer tenant) | 0 in documents; the gate's window is read off the served candidate |
| effective-request derivations | 2, with two postures | 1 — the resolver's own, handed to `acquire` through the declared seam |
| registries / stores / recorders per door process | 2 / 2 / 3 | 1 / 1 / 1 |
| gate ids | OFC-G01..G27 | the same 27 ids; OFC-G13 asserts `paved` and the absence of `ProductRequestViolation(` and `ReferencePolicyConstraintResolver(`; OFC-G24 asserts the per-question mint through the public surface |

**What this closes for THIS tree, by construction.** `CP03C-F-02`'s mechanism
is the SDK's (`open_product` mints per question; a tree cannot forget the
uuid). `CP03C-F-07`'s class cannot recur here (nothing in the tree constructs a
refusal envelope; the wrong-lane verdict is the product's, in `src/`).
`CP03C-F-08`'s ingestion half is refused by name at the boundary
(`refuse_foreign_envelope`); its decay-basis half is still the declaration's.
**What stays open**: `CP03C-F-01` (`D-IMPL-341`) — the gate still holds the
serving half and `OFC-G07` stays a strict xfail; `CP03C-F-05` (`D-IMPL-342`).
`CP-SPEC-003C` §"Run it" names `backends.yaml`, which is now
`ccf_environment.yaml`; the specification is a Gate-1 document and is not
edited here.
