<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# SEC-020 — what reaches the bank's configuration, and the parts to remedy

**Status, 2026-10-16.**
- **Part 4 has a provisional ruling.** Dave, 15:53 MST: *"Ruling for now: treat borrower
  scope as not a real permission under the current shared-credential configuration."*
- **Parts 1–3: accepted and closed for the tested cp-06C deployment under the provisional
  Part 4 framing** (Dave, 22:36 MST): *"The measured response comparisons pass and timing meets
  the agreed threshold. Residual timing, caller-selected borrower scope, Part 5 and identity
  work remain open. SEC-020 is not closed SDK-wide."* Built and measured on branch
  `sec-020-parts-1-3` (brief `SEC-020-PARTS-1-3-BRIEF.md`, `D-IMPL-387`); the outcome is in
  `OPEN-SECURITY-ITEMS.md` item 3.
- **Still open:** the residual timing, caller-selected borrower scope (Part 4 stays
  provisional), Part 5 (parked), the identity work, and every product other than cp-06C. A
  runtime message leak found during the build is recorded separately as **SEC-030**.

**Why this document exists.**
- The bank asked, through Dave on 2026-10-15 at 18:09, for *"a detailed breakdown of the
  SEC-02 issue more than what was presented to them"*. On 2026-10-16 at 14:37 Dave
  confirmed that "SEC-02" was a typo for SEC-020.
- Dave, 15:05: *"SEC-020 is my concern as I believe it must be decomposed and remedied
  before they will accept the SDK."*

**Evidence.** A read-only measurement of the bank configuration, taken 2026-10-16:
- **Location:** `ccf_saves/2026-10-16-383/sec020-measure/` (`MEASUREMENT.md`, raw outputs in `raw/`).
- **Setup:** the bank's own `launch.sh`, one shared door credential, the default minimal
  disclosure, a client that asks the way `verify.py` does.
- **Full sweep:** on branch commit `5a3e9b9f`, 247 tool calls, plus 3 first calls and
  5 template reads.
- **Reduced sweep:** on the delivered build `01fc424d`, 31 tool calls.
- **Timing runs:** on both builds.
- **Scope:** one host, loopback, the demonstration estate.
- **Not measured:** the current branch tip (`ccde7fd8`). It changed only how decision
  records are written.

The history of the register's other parts is in `ccf_saves/2026-10-16-383/SEC-020-BREAKDOWN-DRAFT.md`.

## What SEC-020 is

The 2026-09-23 review found that a subject withheld from a caller could be told apart from
one that does not exist. Its example was a subject withheld by the projection, which
leaves traces in debt, emptiness and expiry fields. The review rated it MEDIUM; two
residual parts were later rated HIGH by a review seat. For a bank, the risk is an
existence oracle: a caller learns that something exists without being shown it.

## What was measured in the bank configuration

**Where the leak is in this configuration.** It is not in any of the withholding
mechanisms the register lists. It is in two channels the register did not name: the bytes
of the answer and its timing.

**What `borrower_scope` does.** cp-06C requires a `borrower_scope` parameter. Its policy
step admits the facility's collateral graph only when the list names that facility's own
borrower. Otherwise the view is empty and the product refuses. It never returns a partial
answer.

| Asked | Branch `5a3e9b9f` | Delivered `01fc424d` |
|---|---|---|
| An existing facility, `borrower_scope` naming another borrower | one constant governed refusal (`ttl-anchor-refusal`, `isError: false`, with a replay reference) — 59 of 59 | the same refusal, byte-identical after masking — 10 of 10 |
| An existing facility, `borrower_scope` naming no entity | the same refusal — 60 of 60 | the same — 5 of 5 |
| A well-formed facility id that does not exist | an MCP tool error (`ccf-runtime-failure:<id>`, `isError: true`), no replay reference — 40 of 40 (and 20 of 20 under a scope naming no entity) | the same — 10 of 10 (and 5 of 5) |
| Timing, one fixed pair | medians 634 against 211 ms, ranges do not overlap (n=40 each) | 561 against 178 ms, ranges do not overlap (n=30 each) |
| Timing, 40 (30) different pairs | 500 against 193 ms; ranges overlap in the tails; P(existing slower) = 0.97 | 446 against 175 ms; overlap in the tails; 0.93 |
| Control: a question refused before any source is read | 185 against 181 ms, no separation | 149 against 150 ms, no separation |

**Also measured:**
- **Other answer routes (branch only, small samples):** the same split appeared on the
  door's advertised resource-template address (2 existing against 2 missing facilities).
  In one pair whose `subject` named an existing facility, the `facility_id` decided the
  outcome. Neither was run on the delivered build.
- **Requests refused before any source is read** answered an existing and a missing
  facility identically once the caller's echoed inputs were masked. That covers another
  tenant, an undeclared intent, and an out-of-domain argument (branch only, one pair each;
  not byte-compared on the delivered build).
- **The failure is not silent on the server.** A nonexistent id that reaches acquisition
  gets no decision record and no replay reference. But the door's log keeps a traceback
  for each failure (148 on the branch, 79 on the delivered build, across all runs). On the
  branch, the evidence folder also keeps a "pending" marker for each one, naming the asked
  facility id and `borrower_scope` (148 after all branch runs; the sweep alone left 61).
  A nonexistent id refused before acquisition, for example for an undeclared intent, does
  get a decision record.
- **Naming a facility's own borrower.** On the branch, all 60 facilities were asked with
  their own borrower as `borrower_scope`. Results:
  - 46 were served;
  - 3 were refused `ttl-bounds`;
  - 1 was refused by the over-allocation guard;
  - 10 got the same `ttl-anchor-refusal` an out-of-scope ask gets.

  On the delivered build only one such ask was made (served).

**Why it happens.** This is code reading plus measurement:
- **The not-found error.** cp-06C's acquisition raises `LookupError` for an unknown
  facility
  (`examples/cp-06-canonical-collateral-and-setoff-coverage/acquisition.py::_resolve_facility`).
  The error is not declared under `seam_refusals`, so it propagates as a runtime failure.
  That is the ruled behavior for an undeclared failure (`D-IMPL-347` B2).
- **The full fetch.** An existing facility is acquired in full. Only afterwards does the
  policy step (`policy.principal-subgraph`) empty the view.
- **The product contradicts its own contract.** cp-06C's own documents say *"an
  unresolvable facility is a refusal"*: its `ccf_config.yaml` argument description, and
  spec §0.4, *"What is refused? … an unresolvable facility"*.

**What does not reach the bank's product as delivered.**
- **Not engaged for cp-06C,** measured in-process on 5 cp-06C questions per build: the
  P6 probe, the shared-owner walk 16 (C), the stand-in checks, the composite-child path
  and the population phase.
- **Not run:** D1 (a)'s two-deployment comparison.
- **Did not fire:** E2 (ii)'s contradiction guard. The projection never withheld in the
  3 runs observed, and the outcomes show no contradiction refusal.
- **Engaged, as a cost:** the register's "one extra read per question". It ran on all 5
  probe questions, existing and missing alike. By code reading, it runs on every question
  that reaches acquisition, and not on one refused before it. So it is not what separates
  the pair.
- **Not reachable through the door.** As `verify.py` listed it on the branch build, the
  door advertises one tool (`request_context_product`, which writes a decision record per
  answer) and one product-address template, with no storage, upload or replay handle. The
  delivered build's surface was not listed; its door code is unchanged, by code reading.
  So these are not reachable:
  - question stores reachable by a raw writer;
  - the file-backed store's `get`, which does not re-hash;
  - write timing.

  Folder modes were measured at 700 and 600. An operating-system-level attack was not
  measured.

## Part 4 — what `borrower_scope` is (provisional ruling)

- **What the product says about it.** cp-06C's request schema and the tool description its
  door advertises call `borrower_scope` the borrower a caller *"is entitled to walk"*.
  `run.py` says so too.
- **What it actually is.** It is a value the caller supplies (`source:
  effective_request`), and every caller presents the same credential.
- **Dave, 2026-10-16 15:53 MST, verbatim:** *"**Ruling for now:** treat borrower scope as
  **not** a real permission under the current shared-credential configuration. Parts 1–3
  are the reachable surface. Record that explicitly in the open-items list and in the
  bank-facing breakdown so the claim matches the measured behavior. The identity work stays
  deferred until you rule otherwise."*
- **What follows, stated narrowly:**
  - In this configuration `borrower_scope` decides which facility's graph is admitted. It
    does not decide who may see what.
  - The door's caller-identity boundary is the one shared credential, with its single
    tenant grant. A call naming a tenant the grant does not carry was refused with
    byte-identical errors for one existing and one missing facility (branch, one pair).
    The door binds 127.0.0.1 only (`verify.py` on the branch; the delivered build by code
    reading).
  - Through the answer's bytes, a credential holder who does not name a facility's
    borrower learns whether a facility id exists. Through timing it learns the same, less
    sharply across many facilities.
- **The packet the bank already has.** `BANK-PACKET.md` §5, sealed in the 2026-10-13
  delivery, says *"a caller who asks about a record it is not entitled to see gets the same
  answer as a caller who asks about a record that does not exist: the same status, kind,
  external reason and fields"*.
  - **Where that holds:** at the tenant boundary this configuration enforces (measured
    on the branch, one pair; above).
  - **Where it does not:** for `borrower_scope`, which the product itself describes as an
    entitlement.
  - **What the next package must do:** say which of the two it means.
- **The identity work stays deferred.**
  - Follow-ups 7, 8 and 9 (9 being on-behalf-of identity) were deferred by Dave on
    2026-10-12 at 22:44, and again by name on 2026-10-13 at 03:53.
  - Per-employee credentials were never named in a ruling. They were listed only in an
    unvalidated local estimate, which the 03:53 message declined to authorize.

## Parts 1–3 — what is proposed for the reachable surface

### Part 1 — an unknown facility answers differently from an existing one (bytes)

**Candidate remedies, each to be measured before it is believed:**
- **(a) Give an unknown facility the refusal an out-of-scope one gets.**
  - The ground for changing the bank's product, which is an example (`D-IMPL-261`): it
    contradicts its own declared contract (above).
  - **Consequence: one record per made-up id.** The out-of-scope refusal carries a replay
    reference, so matching it means writing a decision record for every made-up id. On the
    branch those records are kept in the evidence folder.
  - **Consequence: the match is to a time-to-live refusal.** That refusal is the
    `ttl-anchor-refusal`, which 10 facilities also get under their own borrower. An unknown
    id would be indistinguishable from those too.
  - **Not yet established:** whether returning nothing for an unknown id reaches that same
    refusal byte for byte. cp-06C's envelope step would still write an anchor node for the
    asked id.
- **(b) Declare the not-found under `seam_refusals` with `cause: nonexistent`.** Not
  sufficient on its own: it mints `subject-unavailable`, which still differs from
  `ttl-anchor-refusal`.

**Test:**
- The measured comparison through the bank's door, on the tool call and on the
  resource-template address.
- Pass condition: identical after masking the per-answer reference and the caller's echoed
  inputs (what the measurement masked).
- Red today on both builds.

### Part 2 — timing

- **Cause:** an existing facility's collateral graph is fetched before the policy step
  empties it.
- **Candidate remedy:** check `borrower_scope` against the facility's borrower inside
  acquisition, before the collateral graph is read.
  - **The residual:** the check itself needs the facility row, because the borrower is
    only known from it (`acquisition.py::_resolve_facility`). An existing facility would
    still cost one lookup that a missing one does not. That residual is not measured.
  - **A note on the whitepaper:** §7.4 orders policy before traversal over the graph; it
    does not by itself require policy before source acquisition.
- **Test:** the fixed and rotating timing pairs, plus the before-acquisition control, with
  a pass threshold set before the run. No threshold has been set yet.

### Part 3 — nothing checked this on the bank's product

- **What exists:** SEC-020's closing gate module (`tests/products/test_sec020_combined_proof.py`).
  Its pin-channel test has 364 cases; the 21 that had failed now pass on the delivered
  build.
- **Where it runs:** on fixtures. Nothing runs a withheld-against-absent comparison on
  cp-06C or through `launch.sh`, and `verify.py` has no such check. Part 3 is a coverage
  gap, not a third leak.
- **Candidate remedy:**
  - make that comparison a standard gate for every shipped product;
  - add a `verify.py` check the bank can run itself.

  A byte comparison catches Part 1; Part 2 needs the timing test.

## Part 5 — the SDK-wide parts, not engaged by the bank's product as delivered

The shared-owner walk, composite-child and limitation-block rows matter for products that
declare a population phase, an early policy or a projection that can withhold. The
store-access rows apply to any deployment, but only with access the door does not give.

| Part | Rating | State |
|---|---|---|
| Shared-owner walk in a long-running service, 16 (C) | HIGH | Option (C) ruled to go to Grok first: the walk stops reading the SDK's `AuditLog` (or the whole registry), stated as a limit, and 2.4 (b) is rebuilt on it. No design document yet. |
| A composite child's record names the stand-in | HIGH (disclosed only) | Not ruled: (B) extend the constant refusal to a child asked about the stand-in, or (C) gate child records by the parent's policy |
| D1 (a) 30/88; P6 24/44; E2 (ii) 82/82 | not rated | No design or options recorded |
| Question stores reachable by a raw writer; the file-backed store's `get` does not re-hash (the MCP-backed store's does) | not rated | Operating controls (folder modes, measured); options recorded; the branch keeps every question's store across restarts |
| Timing at production scale and over the wire | not rated | Not measured |

## Proposed order

1. **Parts 1 and 2 on cp-06C:** measure the candidate remedies through the bank's door
   before and after.
2. **Part 3 alongside:** the gate and the `verify.py` check.
3. **Part 4:** confirm the provisional ruling, and make the next package's §5 say which
   boundary its refusal sentence means.
4. **Part 5:** each item as its own design, Grok first.

Each remedy goes to Grok before it is built, as Dave's practice for SEC fixes requires.
This order is a recommendation.
