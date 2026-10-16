<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# SEC-020 — decomposed into parts that can each be remedied (PROPOSED)

**Status: a proposal for Dave and Grok. Nothing here is ruled or built.** 2026-10-16.
Dave, 15:05 MST: *"SEC-020 is my concern as I believe it must be decomposed and remedied
before they will accept the SDK."* The bank asked for *"a detailed breakdown of the
SEC-020 issue"* (relayed 2026-10-15 18:09; Dave confirmed SEC-020 at 14:37).

Evidence:
- **Measurement of the bank configuration** (read-only, 2026-10-16):
  `ccf_saves/2026-10-16-383/sec020-measure/MEASUREMENT.md`. The bank's own `launch.sh`,
  one shared credential, minimal disclosure, on the delivered build `01fc424d` and on this
  branch; 278 door calls plus timing runs.
- **The register's history and open parts:** `ccf_saves/2026-10-16-383/SEC-020-BREAKDOWN-DRAFT.md`
  (code and records reading).

## What SEC-020 is

A caller can tell a record it is not allowed to see from a record that does not exist.
For a bank that is an existence oracle: it confirms that a facility, a counterparty or a
deal exists without revealing its contents. The 2026-09-23 review rated it MEDIUM; two
residual parts were later rated HIGH by a review seat.

## The headline the bank needs

**In the delivered bank configuration SEC-020 is reachable, but not through any of the
parts the register lists.** Measured:

| Asked | What the caller gets |
|---|---|
| A facility that exists, outside the caller's stated `borrower_scope` | a governed refusal (`ttl-anchor-refusal`), `isError: false`, with a replay reference — 59 of 59 |
| A well-formed facility id that does not exist | a tool error (`ccf-runtime-failure:<id>`), `isError: true`, no replay reference, nothing recorded — 40 of 40 |
| Timing for the same pair | medians 634 ms against 211 ms; the ranges do not overlap (one host, one scale) |

Two facts make the oracle what it is, both measured:
1. cp-06C's acquisition raises an undeclared `LookupError` for an unknown facility, so the
   door turns it into a runtime failure. A facility that exists is fetched in full and only
   then emptied by the scope policy.
2. `borrower_scope` is a parameter the caller supplies, under one shared credential. A
   caller who states the facility's own borrower gets the full answer (60 of 60 facilities
   gave their normal outcome). In this configuration the "restriction" is the caller's own
   statement, not an entitlement. What leaks is **existence**, and finding it needs no
   borrower identifier.

Everything the register lists (the P6 probe, the shared-owner walk, the stand-in checks,
the composite-child record, the three limitation blocks) was measured **not engaged** for
cp-06C. The raw-writer, store-`get` and write-timing gaps are not reachable through the
door (store folders measured 700, files 600).

## The parts, in proposed order

### Part 1 — the bank's product answers "does not exist" differently (bytes). Reaches the bank.

- **Cause:** cp-06C raises `LookupError` for an unknown facility
  (`examples/cp-06-canonical-collateral-and-setoff-coverage/acquisition.py::_resolve_facility`).
  The error is not declared under `seam_refusals`, so it propagates as a runtime failure
  (`PKG-F-03`: an undeclared failure propagates, by ruling).
- **Candidate remedies (each to be measured, not assumed):**
  - (a) cp-06C answers an unknown facility with exactly the refusal an out-of-scope
    facility gets. For example, acquisition returns nothing for an unknown id and lets the
    same empty-view path refuse it. This is a change to the bank's product, which is an
    example (`D-IMPL-261`: allowed when the example is objectively wrong, and an existence
    oracle in the delivered configuration is that).
  - (b) Declare the not-found under `seam_refusals` as `cause: nonexistent`. On its own
    this does **not** close the gap: it mints `subject-unavailable`, while out-of-scope
    gives `ttl-anchor-refusal`, so the two answers would still differ.
- **Test:** the pair above, through the bank's door, byte-identical after masking the
  per-answer reference; red today.

### Part 2 — timing. Reaches the bank.

- **Cause:** a facility that exists is fetched in full before the scope policy empties it;
  an unknown one is not. Policy runs after acquisition, not before it (whitepaper §7.4:
  policy before traversal).
- **Candidate remedy:** apply `borrower_scope` at acquisition, so neither an out-of-scope
  facility nor an unknown one fetches anything. The measured control, a question refused
  before acquisition, did not separate (185 against 182 ms). The residual is whatever
  lookup a scope check itself needs; it must be measured.
- **Test:** the timing pair with an overlap criterion stated in advance, plus the
  before-acquisition control.

### Part 3 — the SDK's own SEC-020 gate never ran on the bank's product. SDK coverage.

- SEC-020's closing gate (`tests/products/test_sec020_combined_proof.py::test_a_pin_filed_in_one_deployment_reads_alike_in_both`,
  21 cases) and the rest of that module run on fixtures. Nothing runs it, or anything like it, on cp-06C or through `launch.sh`, and
  `verify.py` never compares a restricted answer with a nonexistent one. That is why
  Part 1 was found only today.
- **Candidate remedy:** a withheld-against-absent check as a standard gate for every
  shipped product a deployment serves, including one through the bank's door, and a
  `verify.py` check the bank can run itself.

### Part 4 — what the restriction is. A ruling, not a fix.

- cp-06C's request schema describes `borrower_scope` as *"one borrower identifier this
  request is entitled to walk"*. With one shared credential it cannot be an entitlement:
  any caller can state any borrower. Hiding existence from a caller who can ask for everything protects
  little, and Parts 1 and 2 only stop existence leaking to a caller who does not already
  know the borrower.
- A real entitlement needs a verified caller identity. That is follow-ups 7, 8 and 9
  (deferred by Dave on 2026-10-12 22:44 and 2026-10-13 03:53), or a per-employee
  credential configuration (9a).
- **Decision for Dave:** is `borrower_scope` meant to be an entitlement in the bank's
  setup? If yes, Part 4 needs the identity work. If no, Parts 1–3 are the whole of what
  reaches the bank, and the register should say so.

### Part 5 — the SDK-wide parts. Do not reach the bank's product as delivered.

These matter for any product that withholds through its projection or declares an early
policy or a population phase. They stay open with their recorded options:

| Part | Rating | Recorded path to close |
|---|---|---|
| Shared-owner walk in a long-running service, 16 (C) | HIGH | Design (C): the walk compares but does not read the SDK's audit log; Grok first, then build and re-measure. No design document exists yet. |
| A composite child's record names the stand-in | HIGH (disclosed only) | Not ruled: (B) extend the constant refusal to a child asked about the stand-in, or (C) gate child records by the parent's policy |
| D1 (a) 30/88; P6 24/44; E2 (ii) 82/82 | not rated | No design; E2 (ii) holds only for a class that falsely declares it never withholds |
| Question stores reachable by a raw writer; a store's own `get` checks nothing | not rated | Operating controls (folder modes, measured); options recorded |
| Timing at production scale and over the wire | not rated | Not designed |

## What we propose doing first

1. **Part 1 and Part 2 together, on cp-06C:** one change (scope at acquisition, unknown
   handled like out-of-scope) may close both. Measure through the bank's door before and
   after.
2. **Part 3 alongside:** the gate that would have caught this, and a `verify.py` check.
3. **Part 4:** Dave's ruling. It decides how much more the bank needs.
4. **Part 5:** after 1–4, each as its own design for Grok first.

This order is a recommendation; each part's remedy goes to Grok before it is built.
