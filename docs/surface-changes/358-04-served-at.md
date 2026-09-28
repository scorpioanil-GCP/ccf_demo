# 358-04 — `served_at`: one clock read, hoisted, and captured on every governed serve

`D-IMPL-358` Wave 2 step 4. The instant a governed answer was handed over becomes a
member of replay dimension 5, and the fabric-controlled clock that supplies it is
read **exactly once per call** at the entry to the governed path.

**The truthful claim at this step.** Every governed serve now records when it
answered, and the clock behind that instant is read once. It is **not** true that
requests are temporally bounded: nothing compares `served_at` to anything. Gate 3
is untouched, policy effectivity is untouched, composite validity is untouched,
refusal records do not carry it yet, and `PeeringAdmission` is untouched — all of
that is step 5.

**What the hoist changed, precisely.** Before this step the clock was read inside
`if registered.requires:`, so a **non-composite serve read no clock at all** and had
no instant with which to say when it answered. The read now happens once at
`__call__` entry — after the three address checks that RAISE on a mis-wiring, and
before everything that produces a governed outcome — and the composite branch takes
that same value (`admitted_at := served_at`). The composite window is therefore
byte-identical to the window it was, and the read-once-per-composition control still
measures what it measured.

**A refusal path reads the instant and records nothing with it at this step.** That
is the ruled placement rather than an oversight: moving the read later and then
moving it again in step 5 would make step 5 redo step 4.
`tests/products/test_resolver_seam.py::test_step4_a_refusal_reads_the_clock_once_and_records_no_served_at_YET`
asserts the boundary and names itself as expected to be amended there.

**One existing control's premise is retired by ruling 1, and it is renamed rather
than quietly flipped.** `test_o3_a_non_composite_never_reads_the_admission_clock`
asserted `reads == []` on the stated reasoning that *"reading a clock it has no use
for would be harmless and still wrong: it would make the value look load-bearing on
a path where nothing consumes it."* A non-composite serve now consumes it. The
control is `test_o3_a_non_composite_reads_the_admission_clock_EXACTLY_ONCE` and
still enforces the property worth having — one read, not none, because a second read
would put two instants in one answer.

## ccf.replay.record.ContentGenerationPath

- Surface: ccf.replay.record.ContentGenerationPath
- Public surface: true
- Change type: reshaped
- Before: sixteen members; the dimension related two instants — `request.asked_at`, carried on the request it holds, and the record's own `recorded_at`
- After: a seventeenth member, `served_at: datetime | None`, `Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})` — **transparent at the sentinel**. A third instant, and the record now says all three rather than one of them twice: what the question asks as of, when the decision was taken, and when the answer was handed over. `recorded_at` is untouched on both the served and the refusal path
- Why: `D-IMPL-358` ruling 1. The mark is the ruling and not a preference: `None` — every record written before the member existed — canonicalizes exactly as it did, so no pre-1.0.2 address moves and the member's mere schema presence is not a generation boundary; a populated value participates, so **two serves of one question are two records**, which is the audit reading a bank needs. Deliberately NOT `ChildResolution.child_admitted_at`'s `{HASH_TRANSPARENT_KEY: False}`: the accepted design asserted transparency while citing that field as its precedent, and ruling 1 settles that this one is transparent. The precedent it actually follows is `ttl_anchor_at` on this same class — same shape, same sentinel, same mark
- Migration: none for a stored record. Every record written before the member existed rehydrates to the address it was written at, measured by the two rosters that hold the transparent set by name (`tests/contracts/test_hash_transparency.py` and `tests/replay/test_generation_mismatch.py`), both of which required this field to be DECLARED rather than merely marked. `THE_FIFTEEN` is unchanged, which is the load-bearing half: a row that grew that lineage would make an old record refuse. **For a caller that compares addresses across serves**: two serves of one question now differ, so any "same determination twice" assertion must pin the clock — which is what proves the clock is the only difference

## ccf.replay.record.build_replay_record

- Surface: ccf.replay.record.build_replay_record
- Public surface: true
- Change type: reshaped
- Before: twenty-one keyword-only parameters; the builder had no way to be told when the answer was served, because nothing in the fabric knew
- After: a new keyword-only parameter `served_at: datetime | None = None`, passed straight through to the dimension. Passed rather than derived, unlike the sibling `ttl_anchor_at` immediately above it in the same construction, which is read off the product because the product carries it — no artifact carries the instant the answer was handed over, so only the resolver that read the clock can supply it
- Why: `D-IMPL-358` step 4. One builder already mints every record on both the served and the refusal path, so the capture belongs in its signature rather than in a second construction
- Migration: none. The parameter defaults to `None`, so every existing caller writes a record whose address is exactly what it was

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: `admission_clock` was invoked inside `if registered.requires:` only, so a non-composite serve read no clock; `__call__`'s docstring asserted that *"nothing here reads a clock"*, which was already untrue of that branch
- After: `served_at = self.admission_clock()` once at the entry to the governed path; the composite branch binds `admitted_at` to that same value; the served build site passes `served_at` to `build_replay_record`. **No second clock anywhere.** The docstring sentence is corrected rather than removed: the graph boundary still needs no clock and still comes from `request.asked_at`, and the sentence now says which claim was previously overstated
- Why: `D-IMPL-358` step 4 — a governed serve that cannot say when it answered cannot be audited for it, and one read per call is what keeps a single answer on a single instant
- Migration: none for a deployment: `admission_clock` already existed, already defaulted, and is already wired by `build_governed_resolver` and `open_product(clock=)`. **For a test that counts clock reads on a non-composite serve**, the count is now one rather than zero; that is the ruled change and the one in-tree control asserting zero is renamed and re-pointed
