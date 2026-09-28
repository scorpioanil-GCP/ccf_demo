# 358-05 — trusted time becomes live: a temporal-bound refusal, and one instant per invocation in every governed refusal

`D-IMPL-358` Wave 2 step 5, **partially landed** — this fragment claims only what
is on the tree. Two of the step's areas are complete: the governed
`temporal-bound-refusal` vocabulary, and the refusal temporal-identity migration
across all five recorder families. The remaining areas are named in the step
record and are not claimed here.

**What is true on this tree.** A governed refusal exists for a question that
reaches outside the window a tenant declares, with a pure judgment behind it; and
every governed refusal from one invocation now carries the ONE instant that
invocation read, beside — never instead of — the question's own instant.

**What is NOT true on this tree, stated so no reader infers it.** Nothing yet
CALLS the temporal-bound judgment: policy effectivity is still evaluated at
`asked_at`, Gate 3's comparand is unchanged, composite remaining validity is
unchanged, and `PeeringAdmission.admit(now=)` is unchanged. Those are the
remainder of step 5.

## ccf.products.refusal.TemporalBoundRefusal

- Surface: ccf.products.refusal.TemporalBoundRefusal
- Public surface: true
- Change type: added
- Before: absent — no governed refusal named a question reaching outside a declared temporal window, and no vocabulary token existed for one
- After: a `CCFContract` with a closed three-reason `Literal` (`temporal-boundary-undeclared`, `asked-at-outside-temporal-bound`, `decision-instant-outside-temporal-bound`), the canonical policy key, the trusted `served_at` it was judged at, and — for the two window reasons — the instant that fell outside and the declared bounds. The three defaulted members are declared **generation boundaries** (`HASH_TRANSPARENT_KEY: False`), because nothing predates this type: a transparent mark buys silence so that records written before a member existed keep their address, and no refusal of this kind has ever been written
- Why: `D-IMPL-358` step 5 with ruling 11. Three reasons rather than one because they are three different facts with three different remedies — an undeclared policy is the operator's to fix and the caller can do nothing about it, while an out-of-window question is the caller's. Collapsing them would send one of the two to the wrong party
- Migration: none. A new kind on a path nothing yet reaches; no existing refusal changes shape or address

## ccf.products.refusal.refuse_temporal_bound

- Surface: ccf.products.refusal.refuse_temporal_bound
- Public surface: true
- Change type: added
- Before: absent
- After: a **pure** judgment — it reads no clock and no registry — taking an already-resolved `PinnedTemporalBoundary | TemporalBoundaryUndeclared`, the trusted `served_at`, and both instants (`asked_at` and the derived decision instant), returning the refusal or `None`. `asked_at` is judged first so a question outside both is reported deterministically by the axis a caller controls most directly. The arithmetic is `ccf/peering/eligibility.py::_evidence_too_old`'s, reused rather than re-invented, which is what keeps two declared durations in this fabric meaning the same thing — and which fixes the reading of zero as the strictest bound rather than as unbounded
- Why: `D-IMPL-358` step 5. The judgment is separated from the resolution so that the instant and the policy both arrive as arguments and nothing about where they came from is decided here — the same split step 3 made between resolving a policy and pinning it
- Migration: none; no caller exists yet

## ccf.products.refusal.REFUSAL_KINDS

- Surface: ccf.products.refusal.REFUSAL_KINDS
- Public surface: true
- Change type: reshaped
- Before: twenty-seven kinds
- After: twenty-eight — `temporal-bound-refusal` joins, and `_PRE_ASSEMBLY_REFUSALS` gains the type because the judgment is pre-acquisition and pre-graph-read, so no candidate exists and no lineage is invented for it. The token was checked against all twenty-seven for the vocabulary's substring rule (no token may contain another): no collision
- Why: `D-IMPL-358` step 5. A refusal that is not in the roster cannot cross a door, be disclosed, or be given a status — the roster IS the vocabulary
- Migration: a consumer switching exhaustively on the kind gains one arm. Every structural gate over the vocabulary enumerated exactly what registration was owed and is green: the disclosure statement and minimal tables, the door's status map, the MCP parity check, and the per-kind envelope test

## ccf.products.resolver.RefusalRecorderProtocol

- Surface: ccf.products.resolver.RefusalRecorderProtocol
- Public surface: true
- Change type: reshaped
- Before: `record(...)` took `recorded_at` and no live instant, so a recorder had no way to state when a determination was actually made — and two of the five governed recorder families stamped live clock time into `recorded_at`, moving a refusal's dimension-1 boundary off the question
- After: a **required keyword** `served_at: datetime | None`, with no default and explicitly nullable. Required so no site can omit it; nullable so a surface that genuinely has no live instant asserts that rather than being assumed. The shape follows the ruling this module already quotes — `D-IMPL-264` amendment 1, *"No intermediate layer may manufacture the marker from omission."* `recorded_at` is untouched and is NOT a synonym: the question's instant bounds the record and the live instant travels beside it
- Why: `D-IMPL-358` step 5. One invocation reads one clock, and every refusal it produces must carry that instant rather than a fresh one — a recorder that read its own clock would put two instants in one determination
- Migration: **every conforming recorder and every caller must pass it**, which the required keyword makes a type error rather than a silent default. All five governed families are migrated: the resolver's own path, `OpenedProduct`'s address refusal, the delivery boundary's four sites, the typed raised refusal, and the entitlement refusal. The most consequential repair is the address refusal, which had `request.asked_at` in scope three lines above and stamped `recorded_at=self._clock()` anyway

## ccf.products.disclosure.EXTERNAL_STATEMENTS

- Surface: ccf.products.disclosure.EXTERNAL_STATEMENTS
- Public surface: true
- Change type: reshaped
- Before: no statement for the new kind, which the closure gate refuses
- After: one statement covering all three reasons, chosen so that it does not tell an external consumer a tenant is MISCONFIGURED — that is the operator's fact and exactly the internal state the minimal level exists to withhold. `PERMITTED_AT_MINIMAL` permits the two declared bounds and nothing else, on the `ttl-refusal` precedent: a declared ceiling is actionable, the fabric's own instants are not, and the policy key never crosses
- Why: `D-IMPL-358` step 5 with `D-IMPL-254` — what crosses a consumer boundary is the disclosure step's decision and no refusal type's
- Migration: none for existing kinds. At minimal, the undeclared reason discloses nothing actionable, correctly: nothing the caller could do would fix it
