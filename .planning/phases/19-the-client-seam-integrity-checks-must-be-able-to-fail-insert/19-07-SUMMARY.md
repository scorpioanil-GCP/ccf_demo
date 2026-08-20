---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 07
subsystem: client-seam prose / public-surface record
tags: [C-10, C-15, C-13, C-18, D-GATE-18, amend-never-delete, surface-manifest, CLNT-14]
requires:
  - "ccf.client.codec (the B0 block preserved verbatim for amendment by 19-01/19-02)"
  - "ccf.products.door.door_answer / door_question — the producer-minted echo and address"
  - "ccf.client.wire.TransportAdapter.ask(WireRequest) -> bytes — the bytes seam"
  - "tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py — the measurements the claim is written against"
provides:
  - "ccf.client.codec — the narrower true claim: five detected conditions, four undetected ones"
  - "ProductClient.ask — a true as_of=None paragraph, with the clock defect named and deferred"
  - "docs/surface/v0.2-surface.json — regenerated; drift is bytes-equal again"
affects:
  - "19-08 (three carried rulings named below; the shipped wording is now quotable verbatim)"
tech-stack:
  added: []
  patterns:
    - "recast a false sentence as a quoted false claim rather than deleting it — the shape binding_document.py already uses"
    - "record a plan that moved no surface on the fragments whose entries its prose is about, never in a fragment of its own"
    - "state a residual two-sidedly: what is held AND what is not, so neither half can be quoted alone"
key-files:
  created: []
  modified:
    - "src/ccf/client/codec.py"
    - "src/ccf/client/client.py"
    - "src/ccf/client/wire.py"
    - "src/ccf/client/__init__.py"
    - "src/ccf/client/adapters/__init__.py"
    - "src/ccf/client/adapters/inprocess.py"
    - "src/ccf/client/adapters/mcp_stdio.py"
    - "src/ccf/products/door.py"
    - "runtime/ccf_runtime/mcp/egress.py"
    - "examples/hw1-companies-over-revenue/consume.py"
    - "docs/surface/v0.2-surface.json"
    - "docs/surface-changes/19-01-one-outcome-shape-and-the-encoded-question.md"
    - "docs/surface-changes/19-02-the-adapter-seam-carries-bytes.md"
decisions:
  - "The plan's fourth fragment `19-01-one-wire-shape-and-a-bytes-seam.md` was NOT created — three correctly-named 19-* fragments already claim every drifting module, and a fourth would have claimed the same coverage twice"
  - "The C-15 correction recasts the false clause as a quoted false claim inside the amended paragraph, because 'amend, never delete' and 'the sentence must not be quotable as a claim' are otherwise in direct conflict"
  - "`_result_from`'s Args entry for `sent` was corrected (it claimed a use that no longer exists); the parameter itself is carried to 19-08, because removing it moves a signature and this plan changes no behaviour"
  - "runtime/http_api/routes/__init__.py and routes/product.py were read against the tree and left unedited — 19-06 left them correct, and the five-call-site enumeration re-resolves"
metrics:
  duration: "~4h"
  tasks: 3
  commits: 4
  collected_delta: "4099 -> 4099 (+0)"
  completed: 2026-08-20
---

# Phase 19 Plan 07: Make the Prose True — Summary

Replaced `D-GATE-18`'s standing prose constraint with a narrower sentence that
is true of the shipped tree, amended `ProductClient.ask`'s knowingly false
clock promise into a true one, and regenerated the public-surface manifest —
deleting nothing, and adding no test, because a prose plan that changes the
collected count has changed something other than prose.

## What Was Built

**The narrower true claim, in `ccf.client.codec`.** A dated section appended to
the `B0` block, in the amend-never-delete form the block already used. It names
what changed (the bytes seam, the producer-minted echo, the producer-computed
address, `decode_outcome` on the shipped path), then **five** conditions the
checks detect and **four** they do not — including `C-18`'s `as_of=None`
temporal residual, stated two-sidedly so neither half can be quoted alone.

**The three now-false statements beside it, corrected in place.** *"…and the
shipped adapters reconstruct"*, *"No shipped adapter calls it"*, and the three
`Raises:`/inertness paragraphs on `verify_content_address`, `check_outcome` and
`decode_outcome` each keep their original sentence and gain the dated
correction. The original *"cross-checked, not reconstructed"* argument is
explicitly marked **unchanged and right** — what was wrong was never the
argument but the code beside it.

**`C-15`'s amendment.** `ProductClient.ask` no longer promises that the
producing deployment answers against its own clock. The paragraph records that
it used to, quotes the sentence, says it was false on both shipped transports,
and states what is true: both adapters resolve `as_of=None` to
`datetime.now(UTC)` **client-side**, the instant actually used is reported on
the served vessel, and the echo carries `None` as asked. The defect is named
for a later phase and **no fix is promised**.

**The MCP door describes what it now emits.** `egress.py`'s
returns-a-`DoorOutcome` paragraph gains the two members Phase 19 added; the
*"not re-serialized"* claim was re-read against the shipped handler and
extended; the `parameters` prose now states that two axes arrive twice and that
a disagreement is **refused by name** rather than resolved by picking a winner.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | The narrower true claim across `src/`, and the amended clock sentence | `4e9c0a4` | `codec.py`, `wire.py`, `client.py`, `client/__init__.py`, `adapters/__init__.py`, `inprocess.py`, `mcp_stdio.py`, `door.py` |
| 2 | `runtime/` prose and the example's one word | `955f70c` | `egress.py`, `consume.py` |
| 3 | The surface manifest and its migration record | `9313c12` | `v0.2-surface.json`, two 19-* fragments |
| — | `_result_from`'s `sent` no longer claims to be read (carried item 3) | `a4d069b` | `client.py` |

## The narrower true sentence, quoted in full for `19-08`

`19-08`'s decision entry and the close-time human read need this verbatim. It
lives in `src/ccf/client/codec.py`'s module docstring, under the heading
**"The follow-on landed, and this is what the checks detect — and do not"**.

> **What the checks now detect**, in the words `C-10` fixes them in — the
> client detects *an answer to a different question*, and *a vessel that does
> not match the address its producer computed* — against five named
> conditions:
>
> * **corruption** of `product_json` in transit;
> * **truncation** of it;
> * **mis-routing** that swaps a vessel for another producer's, or crosses two
>   in-flight questions that are not identical;
> * **a re-serializing intermediary**, because any re-render changes the bytes
>   and not the claim travelling beside them;
> * **producer/consumer canonicalization drift**, because the consumer hashes
>   the text it received rather than re-canonicalizing it, so a producer that
>   renders differently from what it claims is caught on its own bytes.
>
> **What they do not detect.** Four cases, named because a claim that does not
> state its limits is the claim this phase exists to replace:
>
> 1. **An adversary who can rewrite the envelope.** The claim rides *in* the
>    envelope, so an actor with write access to it rewrites the echo and the
>    address to match whatever they substituted. This is non-adversarial
>    integrity and nothing more.
> 2. **A producer that mis-canonicalizes** *consistently*, which states a
>    matching address for its own wrong bytes. That case is caught by the third
>    check (the vessel's contract validation) and by cross-adapter parity,
>    never by this comparison.
> 3. **Two** *identical* **in-flight questions crossing.** Knowingly accepted:
>    the echo is the question, so two callers asking the same thing are not
>    distinguishable by it, and every field a correlation token would add is a
>    field no check reads (`C-03`).
> 4. **On a question asked with** `as_of=None` **only, a transport that alters
>    the instant the door answered against.** The client resolves that instant
>    (`C-15`), so it crosses the wire exactly once and there is no second copy
>    to compare it against; the echo faithfully carries `None` as asked
>    (`C-02`) and matches perfectly. **The other half of that axis is held**: a
>    **concrete** `as_of` crosses twice — inside the encoded question and as
>    the door's own `asked_at` — and the MCP door cross-checks the two and
>    **refuses a disagreement by name** (`C-18`). The residual is the `None`
>    path and only the `None` path; a sentence declaring the temporal axis
>    unprotected would be as false as the one this phase replaces, in the other
>    direction.
>
> **Signing is out of scope and no signature member is reserved on the wire**
> (`C-10`). Reserving one would put a member on the wire that nothing sets and
> nothing reads, which is precisely the shape this phase exists to close — the
> same shape that made both checks inert in the first place.
>
> **`D-GATE-18`'s standing prose constraint is replaced by the paragraphs
> above, not lifted.** A reader arriving here from that gate entry should land
> on a narrower true statement rather than on silence: the SDK detects a
> crossed question and an altered vessel against the five conditions named
> above; it **does not detect** an adversary who can rewrite the envelope, and
> it **does not detect** a transport that alters only the instant a question
> asked with `as_of=None` was answered at.

## Removed lines, per file, with a justification for each

24 removed lines across 13 files, against 470 insertions. **No paragraph and no
sentence was deleted.** Every removal is a line whose sentence was extended or
reflowed in place, verified by whitespace-flattened substring count that the
original wording still exists in the file.

| File | Removed | Justification |
|------|---------|---------------|
| `src/ccf/client/codec.py` | 5 | Five sentence-ending lines, each replaced by the same text plus an appended dated correction. All five originals confirmed present: *"cannot fail either"*, *"phase already declared execution-complete"*, *"reads as a live guarantee and is not one"*, *"failure the paragraph describes"*, *"package's own tests"*. |
| `src/ccf/client/client.py` | 6 | Four are the `as_of=None` paragraph's reflow (`C-15`): the false clause was moved out of the assertion and **into a quoted record** of what the paragraph used to say. Its exact wording — *"the producing deployment answers against its own clock"* — is still in the file, once, framed as false. Two are the `as_of` Args entry and `_result_from`'s `sent` Args entry, each replaced by a longer true one. |
| `src/ccf/client/wire.py` | 3 | One sentence (*"an adapter surface wide enough to express policy…"*) reflowed from three lines to five when the `D-11` amendment clause was inserted ahead of it. Original confirmed present. |
| `src/ccf/products/door.py` | 2 | The `request` and `content_address` attribute docs' final lines, each extended with the Phase 19 correction. Both originals confirmed present. |
| `runtime/ccf_runtime/mcp/egress.py` | 1 | *"had nowhere to go while the return was the product's bytes alone:"* → same text with `—` and the two further members appended. |
| `src/ccf/client/__init__.py` | 1 | The `ccf.client.wire` bullet's second line, extended with the amendment. |
| `examples/hw1-companies-over-revenue/consume.py` | 2 | The two-line tail of a three-line comment, rewritten from the conditional to the indicative. Net line count unchanged — see below. |
| `docs/surface/v0.2-surface.json` | 4 | Generated by `make surface`, never hand-edited. All four are the superseded `"shape"` strings of the four `reshaped` entries. **Zero names lost** (1119 → 1133; 187 → 189 modules). |
| `adapters/__init__.py`, `inprocess.py`, `mcp_stdio.py`, both fragments | 0 | Pure appends. |

## `consume.py`'s line count

**79 before, 79 after.** Measured with `wc -l` on both sides of the edit.

`19-RESEARCH.md` §9.3 measured the file at **80** lines against an 80-line
budget; the file is in fact **79**, so the budget had one line of headroom that
was deliberately not spent. The comment moved from *"the decoded echo **would**
differ … and the cross-check **would** report a healthy wire as failed"* to
*"the decoded echo differs from what was sent — and that cross-check is live,
so it fails a healthy wire."*

Gates, both sides of the edit: `tests/examples/test_client_example_purity.py`
and `test_client_example_budget.py` — **31 passed** before, **31 passed** after.
No line exceeds 88 columns.

**The README was left alone, deliberately.** `19-RESEARCH.md` §9.3 measured
that every `address` mention there is about *reproducibility* and that it makes
**no tamper claim**; silence is therefore not a defect, and adding prose to a
gated file with no measured need is the kind of unasked change three prior
waves in this phase have had to record.

## Every module whose manifest entry changed

Computed with `diff_surfaces(committed, build_surface())` before regenerating,
so this is the measured drift the manifest absorbed and not a prediction:

| Module | Direction |
|--------|-----------|
| `ccf.client.adapters.binding_document` | reshaped |
| `ccf.client.adapters.mcp_stdio` | added (2 names) |
| `ccf.client.codec` | added (1), reshaped (1) |
| `ccf.client.wire` | reshaped |
| `ccf.products.door` | added (8 names) |
| `ccf_runtime.http_api.errors` | added |
| `ccf_runtime.http_api.routes` | added (2), reshaped (1) |

**Every one of the seven, and every one of the eighteen individual names, was
already claimed by a fragment on disk** — verified name-by-name against the
union of `docs/surface-changes/[0-9]*-*.md`, which is exactly the text the
drift gate reads. Note the drift is wider than this phase: the manifest had not
been regenerated since Phase 17, so it also absorbed `17-10`'s and `18`'s
documented moves.

After `make surface`, `tests/test_surface_drift.py` — **9 passed** — takes the
bytes-equal path rather than the documented-drift path.

## The fragment the plan named was NOT created, and why

The plan's `files_modified` and four of its criteria name
`docs/surface-changes/19-01-one-wire-shape-and-a-bytes-seam.md`. **That file
does not exist and was not created.** Three correctly-named fragments are
already on disk and already assembled:

- `19-01-one-outcome-shape-and-the-encoded-question.md`
- `19-02-the-adapter-seam-carries-bytes.md`
- `19-06-the-http-door-publishes-the-question.md`

Between them they carry **every** item the plan's fragment was specified to
carry — the seam retype to `bytes`, the two shapes moving to `ccf.products.door`
with `ccf.client.wire` re-exporting, `DoorOutcome` gaining `request` and
`content_address`, `decode_outcome` returning `DecodedOutcome`,
`PRODUCT_REQUEST_TOOL`'s required `request`, `canonical_response`'s keyword-only
`asked`, the new `REQUEST_ECHO_HEADER`, and the deletion of `_decode`/`_encode`
— each with all seven fields (verified: 7 distinct field names in each of the
three), each with a `Migration` line, and each stating that there is **no
deprecation window** and why. A fourth fragment would have claimed the same
coverage a second time.

**The substitution, recorded as the orchestrator required:** `19-07` moved no
public surface at all, so instead of a fragment it is recorded as a prose
section — *"Amended by `19-07`"* — appended to `19-01` and `19-02`, the two
whose `Before`/`After` entries its prose is about.

**Those sections are deliberately absent from the assembled
`docs/SURFACE-CHANGES.md`, and that is the tool working correctly.**
`tools/assemble_surface_changes.py`'s own docstring: *"Fragments legitimately
also carry prose sections (rulings, verification notes), and those are passed
over."* `make surface-changes` was run and `SURFACE-CHANGES.md` came back
byte-identical. Forcing an entry into the adopter-facing log would have claimed
a surface move that did not happen — a false claim in a migration note, in the
phase whose subject is false claims. `D-IMPL-155`'s hazard (a **misnamed**
fragment silently dropped) is separately confirmed absent: all three 19-*
fragments' entries are present in the assembled log.

`git status --porcelain` after both tooling runs showed only the three intended
files. `tools/retirement_sweep.py` was **not** run (`D-IMPL-154`) and did not
need to be: `tools/docs_tests/test_retirement_sweep.py` is **33 passed** — this
plan's prose edits shifted no swept citation line number.

## The must-have truths, each verified

1. **`D-GATE-18`'s constraint is replaced by a narrower true sentence, not
   lifted, and `codec.py` says so** — quoted in full above; the constraint
   paragraph itself is intact and carries an inline pointer to its replacement.
2. **The claim states what it does not detect, and reserves no signature
   member** — `grep -c "does not detect" codec.py` = **1**;
   `grep -rniE "signature|signed|sign_" src/ccf/client/ src/ccf/products/door.py`
   returns **one** line, the sentence *"no signature member is reserved on the
   wire"*, which names no wire member and is `C-10`'s required wording.
3. **`C-18`'s residual is in the named undetected list, and stated
   two-sidedly** — it is item **4** of four (three would have meant the
   residual shipped unnamed), and the same item states that a **concrete**
   `as_of` **is** cross-checked and refused by name.
   `grep -c "as_of=None" codec.py` = **3**.
4. **Every corrected paragraph is amended, never deleted** — 24 removed lines,
   each justified above, each original confirmed present by substring.
5. **`ProductClient.ask`'s false clock sentence is amended; the clock read did
   not move and the defect is recorded for a later phase** — `grep -n "own
   clock" src/ccf/client/client.py` returns exactly one line, inside the
   amended paragraph, where it is labelled false.
6. **The manifest is regenerated and every moved module is named** — table
   above; `make surface` produced it, never a hand edit.
7. **`consume.py` stays inside its budget and its purity gate stays green** —
   79 → 79, 31 passed both sides.
8. **The trap guard held** — `grep -c "func:.*check_outcome"
   src/ccf/client/client.py` = **2**, and the phase's own thesis sentence is
   intact in the shipped source.

## Verification

| Step | Result |
|------|--------|
| `make lint` | **exit 0** — after every file, including `tools/lints/citations.py` |
| `make typecheck` | **exit 0** — 211 source files |
| `pytest tests/client -q` | **415 passed, 0 failed** |
| `pytest tests/products -q` | 480 passed |
| `pytest tests/mcp tests/http_api tests/crossproc -q` | 280 passed |
| `pytest tests/test_surface_drift.py -q` | 9 passed |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | 33 passed |
| example purity + budget | 31 passed, before **and** after the `consume.py` edit |
| **`make ci`** | **exit 0** — 3981 passed / 118 skipped / **0 failed**; 400 lint-tool; 154 publish/docs; all nine examples ran; `mkdocs build --strict` green |
| `git status --porcelain` | clean |

`make ci` was run twice — once at the end of Task 3 and again after the
`_result_from` correction — and was exit 0 both times.

### Collected-count reconciliation against the 4027 baseline

`pytest --collect-only -q` reports **4099**, unchanged by this plan. Every
increment from the phase's measured 4027 baseline traces to a named plan:

| Plan | Δ | What it added |
|------|---|---------------|
| `19-01` | +24 | the door entry's controls, the address cross-check, the cross-process leg |
| `19-02` | +2 | the question half crossing the wire; the `C-02`/`C-15` echo leg |
| `19-04` | +8 | the two `C-12` tamper legs over both subjects, plus their controls |
| `19-05` | +14 | the `C-17` AST gate and its twelve controls |
| `19-06` | +7 | the HTTP echo's presence, absence, two refusals and their guards |
| `19-03` | +17 | the single-transport controls and the codec's own byte sabotage |
| **`19-07`** | **+0** | **nothing — this plan corrects prose and adds no test** |

4027 + 24 + 2 + 8 + 14 + 7 + 17 = **4099**. `make ci`'s 3981 passed is the same
number `19-03` measured at this plan's base commit, which is the load-bearing
check for a prose plan: had it moved, something other than prose had changed.

## Deviations from Plan

### 1. A criterion that is unsatisfiable without deleting a true record — reported, not satisfied

The plan's verification item 4 and one Task 1 criterion require:

> `grep -rn "answers against its own clock" src/ runtime/ examples/ docs/ public/` returns nothing.

**As literally scoped this is unsatisfiable without two violations of this
project's own rules**, and it is precisely the defective-criterion shape the
orchestrator warned this plan was most likely to hit:

- **`docs/DECISIONS.md:442`** contains the phrase. That is the `D-GATE-17`
  entry, quoting `ProductClient.ask`'s docstring as it read on 2026-08-16.
  `docs/DECISIONS.md` is **append-only** and `HISTORICAL_RECORDS`-exempt from
  the citation lint *precisely because entries are never edited*
  (`19-RESEARCH.md` §9.3). Satisfying the criterion means editing a historical
  record to remove a quotation that was accurate when it was written.
- **`src/ccf/client/client.py:166`** contains the phrase, inside the amended
  paragraph, where it is quoted as *what the docstring used to say* and
  labelled false. Satisfying the criterion means deleting the record of the
  false claim — which the same plan forbids in its own standing hazards
  (*"A deleted paragraph in this plan is a blocking defect, not a tidy-up"*).

**What was done instead.** The substantive requirement — that no reader can
quote the tree as *claiming* the deployment's clock answers the default path —
is met and measured:

- `grep -rn "answers against its own clock" src/ runtime/ examples/ public/`
  returns **only** `client.py:166`, the recorded-as-false line.
- The plan's own second half of that criterion — `grep -n "own clock"
  src/ccf/client/client.py` shows **only the amended paragraph** — passes
  exactly: one hit, line 166.

Recorded rather than worked around, because a criterion satisfiable only by
deleting a true-but-inconvenient record is the defect shape `19-02` inverted
into a guard, one plan over.

**Note also** that the criterion was *already* vacuously green in `src/` before
this plan ran: the false sentence wrapped across lines 140–141 as *"…against
its own"* / *"clock, and…"*, so a literal grep for the phrase never matched it.
A grep criterion defeated by line wrapping is not a measurement — which is why
the sentence was found by reading, not by the grep.

### 2. Two of the plan's five `runtime/` files needed no edit — measured, then left alone

The plan lists `runtime/ccf_runtime/http_api/routes/__init__.py` and
`routes/product.py` in `files_modified` and instructs *"confirm `19-06`'s
additions read correctly in context and amend only what is wrong."* Both were
read in full against the tree and **nothing was wrong**:

- `canonical_response`'s `asked` `Args:` entry already states the
  producer-side origin, the serialize-once discipline, the absent-never-empty
  rule and — explicitly — that `C-18`'s cross-check *"has no subject on this
  door"* because the echo's boundary is built from the one `asked_at` the route
  parsed.
- The call-site enumeration was **re-counted against the tree**, not assumed:
  `grep -rn "canonical_response("` finds exactly **five** call sites, and all
  four cited line numbers (`agent.py:74`, `config.py:98`, `replay.py:47`,
  `replay.py:65`) still resolve to a `canonical_response(` call. No correction
  was owed.
- `product.py`'s sibling-asymmetry paragraph reads correctly as `19-06`
  extended it.

`D-IMPL-126`'s four-`ETag`-reasons block is untouched: `git diff` for
`routes/__init__.py` is **empty**, which is a stronger statement than "no
changed line inside the paragraph".

### 3. The `C-15` correction had to move a clause, not only append to one

Everywhere else in this plan the amendment is a pure append. The `as_of=None`
paragraph is the one exception, and it is forced: the plan requires both
*"amend-never-delete"* and *"the amended paragraph must not contain a sentence
a reader could quote as* the producing deployment answers against its own
clock*"*. Those cannot both hold while the clause remains an assertion.

The resolution is the shape `src/ccf/client/adapters/binding_document.py`
already uses in this tree (*"``asked_at`` **is not the fallback for**
``as_of=None``, and this docstring used to say it was"*): the clause is quoted
verbatim inside the correction and explicitly labelled false. Both surviving
clauses of the original sentence — *"``None`` means \*use the server's decision
instant\*"* and *"the instant it used comes back on the served vessel"* — are
preserved **verbatim**, confirmed by substring count. A first draft reworded
the second clause for precision and was reverted, because rewording a true
sentence is still a change nobody asked for.

`tests/client/test_surface.py::test_the_as_of_rule_is_documented_on_ask`
requires *"decision instant"* and *"as_of"* to remain in the docstring; both do,
and the test passes.

### 4. Where the plan's own citations were wrong

**Every line citation in the `read_first` blocks was stale.** This is the
**fifth consecutive plan in this phase** to record it, and `D-IMPL-114` already
rules that prose cites `path.py::Symbol` for exactly this reason. Every symbol
**name** was correct and was what found the code.

Two citations were wrong about more than a line number:

- **`src/ccf/client/binding.py:74` and `:170` — *"the `D-11` /
  adapter-author-surface paragraphs"*.** Those two lines are
  `AdapterFactory = Callable[[str], TransportAdapter]` and
  `) -> TransportAdapter:` — **code, not prose.** `binding.py` contains no
  `D-11` paragraph at all (`grep -n "D-11" binding.py` returns nothing) and
  restates no superseded permission, so **it was not edited.** Editing it to
  satisfy the file list would have been prose invented to match a plan.
- **`src/ccf/client/wire.py:235-274` — the `WireOutcome` class docstring and
  its `request` / `content_address` attribute docs.** Those moved to
  `src/ccf/products/door.py` in `19-01`; `wire.py` is now 126 lines. They were
  amended in `door.py`, which the plan also lists.

### 5. Carried-forward items, each dispositioned rather than left silent

The orchestrator carried four verified items into this plan.

**Item 1 — the misnamed fragment.** Handled above; the fragment was not
created and the substitution is recorded.

**Item 2 — `TransportError` dropped from `inprocess.py` by `19-02`.**
Confirmed against the tree: the name is **not imported** in that module, and
its single remaining occurrence is a prose cross-reference at `:365` saying
`BindingError` is *"a `TransportError` by inheritance"* — which is true and
correct. **The shipped prose is already consistent with the drop; no correction
was owed and none was invented.**

**Item 3 — `_result_from` still takes `sent` and nothing reads it.** Split:

- **In scope and fixed here** — the `Args:` entry read *"the request that was
  actually sent, **for the echo cross-check**"*, which stopped being true when
  that check moved into `decode_outcome`. That is a false claim in the shipped
  surface, in the phase whose subject is false claims in the shipped surface,
  so it is corrected (commit `a4d069b`): the entry now records that nothing in
  the body reads the parameter, names it as the `C-10` shape one scope over,
  and says the ruling is `19-08`'s.
- **Out of scope and carried** — removing the parameter moves a signature, and
  this plan's own scope statement is *"any behaviour change… is not in scope"*.
  **`19-08` should rule: remove `sent` from `_result_from`, or keep it with the
  docstring reason now written.**

**Item 4 — `19-06` reused `ERROR_PRODUCT_REQUEST_INCOMPLETE` for the HTTP
door's naive-`asked_at` refusal.** Not touched: `runtime/ccf_runtime/http_api/errors.py`
is outside this plan's file set for the same reason it was outside `19-06`'s,
and minting an error code is a behaviour change. **Carried to `19-08` verbatim:
rule whether a dedicated `product-asked-at-naive` code is owed.**

### 6. Not done, and deliberately

- **No behaviour change of any kind.** No test added, no test modified, no
  signature moved; the collected count is unchanged at 4099 and `make ci`'s
  3981 passed is the same figure `19-03` measured at this plan's base.
- **The README of `examples/hw1-companies-over-revenue` was not edited** — it
  makes no false claim, and the plan makes the addition optional.
- **`docs/DECISIONS.md`, `.planning/REQUIREMENTS.md`, the client spec's
  Amendment 2 and `18-CLOSE-REVIEWS.md`'s `B0` closure are untouched.** They
  are `19-08`'s, per this plan's own scope statement.
- **`tools/retirement_sweep.py` was not run** (`D-IMPL-154`), and its committed
  report was measured current rather than assumed so.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` were NOT written**, per the
  orchestrator's standing instruction that the `state.*` / `roadmap.*` SDK
  writers are known-destructive on this repo. The orchestrator owns those
  writes.

## Known Stubs

None. This plan adds no name, no member and no parameter. The one shape it
*names* as a stub — `_result_from`'s unread `sent` — is a pre-existing residual
from `19-02`, now documented rather than hidden, and carried to `19-08` for a
ruling.

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-22` is mitigated: the claim
names five detected conditions and four undetected ones, the fourth being
`C-18`'s residual, and `D-GATE-18`'s constraint is replaced rather than lifted.
`T-19-23` is mitigated: the adversarial case is named, signing is stated out of
scope, and no signature member is reserved. `T-19-24` is mitigated: the clock
promise is amended and the defect is recorded for a later phase with no fix
promised. `T-19-25` is mitigated, though not by the artifact the plan predicted
— the migration record is the three fragments that exist, verified **present in
the assembled document** rather than merely on disk. `T-19-SC` holds: this plan
installed no package and added no dependency.

## Self-Check: PASSED

Modified files, all present:
- FOUND: `src/ccf/client/codec.py`
- FOUND: `src/ccf/client/client.py`
- FOUND: `src/ccf/client/wire.py`
- FOUND: `src/ccf/client/__init__.py`
- FOUND: `src/ccf/client/adapters/__init__.py`
- FOUND: `src/ccf/client/adapters/inprocess.py`
- FOUND: `src/ccf/client/adapters/mcp_stdio.py`
- FOUND: `src/ccf/products/door.py`
- FOUND: `runtime/ccf_runtime/mcp/egress.py`
- FOUND: `examples/hw1-companies-over-revenue/consume.py`
- FOUND: `docs/surface/v0.2-surface.json`
- FOUND: `docs/surface-changes/19-01-one-outcome-shape-and-the-encoded-question.md`
- FOUND: `docs/surface-changes/19-02-the-adapter-seam-carries-bytes.md`

Deliberately absent, per the orchestrator's correction:
- ABSENT (and must stay absent): `docs/surface-changes/19-01-one-wire-shape-and-a-bytes-seam.md`

Commits (all present in `git log`):
- FOUND: `4e9c0a4` `docs(19-07): the narrower true claim across src/, and the amended clock sentence`
- FOUND: `955f70c` `docs(19-07): the MCP door describes what it now emits, and the example's tense`
- FOUND: `9313c12` `docs(19-07): regenerate the surface manifest, and record 19-07 on the fragments that exist`
- FOUND: `a4d069b` `docs(19-07): _result_from's ``sent`` no longer claims to be read`

Key links (all matched):
- `src/ccf/client/codec.py` → `does not detect` — 1 match
- `src/ccf/client/codec.py` → `shipped` — 15 matches, including the amended
  claim that `decode_outcome` now has a shipped call site
- `docs/surface/v0.2-surface.json` → `ccf.client.wire` — present
