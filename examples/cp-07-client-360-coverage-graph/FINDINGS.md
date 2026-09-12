# Findings — cp-07 client 360 / coverage graph

Adjudicated under `D-IMPL-315`: *"canonical path is richer"* is a finding to
adjudicate, never a licence to edit the example. Each entry states whether the
defect is the SDK's, this example's, the spec's, or the estate's — and each one
below was **measured before it was written**.

---

## `CP07-F-01` — the declared λ_c made `D_c` read `fail_closed` on every anchor, and the calibration is now ILLUSTRATIVE

**Status: RESOLVED by ruling (Dave, 2026-09-10). The half-life is a declared
demonstration value, labeled as one everywhere it appears.**

### What was measured at §E's declared ~7 days

Every anchor in the estate, whatever else was true of it:

```
freshness            = 0.0409
completeness         = 1
D_c                  = 0.9591      signal: fail_closed
```

And the unfavorable reading — one observation per admitted interaction, 200 of
them — scored `F = 0.0038`, `D_c = 0.9962`. Both readings `fail_closed`, so the
choice of reading did not rescue the signal.

**The estate is a point-in-time snapshot, not a live feed.** Its newest
interaction anywhere is **2026-08-18**, and the spread of last-contact dates
across every client is **27 days**. Against a 7-day half-life the entire
population sits three to seven half-lives out, so the term carried no
information about any particular client.

### The sharper defect underneath, found by sabotage

Reverting to 7 days and re-running the freshness comparison does not merely make
both anchors bad — **it inverts their order**:

```
stale anchor   (last contact 2026-07-22)  F = 0.0633
current anchor (last contact 2026-08-16)  F = 0.0409
```

At that decay every party's contribution is within rounding of zero, so what the
mean actually reports is party-count structure rather than recency. **A
calibration that ranks the staler relationship as fresher is not a strict
calibration — it is a term that has stopped measuring its own subject.** That is
why this could not be left as *"the estate is stale and `fail_closed` is
correct"*.

### The ruling, and the principle it sets

Dave, 2026-09-10, verbatim: *"Choose illustrative parameter values that make the
scenario work against the available snapshot, and disclose where those values
are demonstration-specific rather than production recommendations."* And:
*"The purpose of the examples is to demonstrate how CCF behaves when parameters
change, not to establish Wells Fargo's production policy values."*

`interaction_record` and `relationship_strength` are now **90 days**, declared
in `ccf_config.yaml` beside a note saying what the number is and is not. The
ruling applies beyond this rung: **whenever static estate data forces an
illustrative threshold, any example may choose one, and must label it.**

### What was NOT done to reach it

No timestamp is faked. `asked_at` is the real decision instant. The decay is the
SDK's own `FreshnessScorer` reading the declared table, and the observations are
real last-contact dates from the estate. **Only the declared half-life is a
demonstration value.**

### What the calibration buys — the mechanism, observable

| anchor | last contact | `F` | `D_c` | signal |
|---|---|---|---|---|
| Caesars Entertainment | 2026-07-22 | 0.3437 | 0.6563 | **`forced_llm`** |
| Suburban Propane (demo) | 2026-08-16 | 0.5279 | 0.4721 | `ok` |
| Container Store (control) | 2026-08-17 | 0.4774 | 0.5226 | `ok` |

The stale anchor scores strictly worse and **crosses a governance threshold the
current anchors do not**. A threshold nothing ever crosses is a threshold nobody
has tested; this one is now exercised by real clients rather than asserted.

Two directional tests hold it:
`test_a_stale_relationship_scores_worse_freshness_than_a_current_one` and
`test_the_stale_anchor_crosses_a_governance_threshold_the_others_do_not`. Neither
pins a number, because pinning `0.6563` would turn a documented demonstration
value back into a fixture.

**`CP-SPEC-007` §E's ~7-day rows are superseded by this entry** and should be
corrected to 90 days with the illustrative label when the spec is next revised.

---

## `CP07-F-02` — completeness is an ADMISSION property here, not a manufactured ratio

**Status: RESOLVED by ruling (Dave, 2026-09-10): *"Keep completeness as an
admission/checkability property rather than manufacturing a ratio."***

§E defines `C` as *"people the enrich leg resolved ÷ people the walk admitted"*.
Measured, it is exactly `1` on every anchor, for two reasons that would each be
sufficient alone:

1. **The estate carries no unresolved participant.** Every subject of a
   `participatedIn` edge resolves to a row in the roster leg — 25 of 25 on the
   demonstration client, 18 of 18 on the stale anchor, 16 of 16 on the control.
2. **The ingestion guard refuses the state the metric would score.**
   `deployment.ingest` asserts that no admitted node lacks a kind. An edge
   endpoint with no node claim of its own IS that state, so a run carrying an
   unresolved participant fails at ingestion and never reaches `debt()`.

**This is kept as it is, deliberately.** The honest reading of `C = 1` here is
not *"the metric is broken"* — it is *"every party this graph walked was
admitted and named, and the fabric is structurally unable to serve one that was
not."* That is a real property of the answer and it is worth stating. The
alternative — inventing a denominator so the number moves — would manufacture a
ratio to make a term look alive, which is worse than a term that honestly reads
one.

The reading that WOULD move, if a future estate carries the gap: the participants
PostgreSQL names in `interaction_participant` that the roster leg could not
resolve (`Coverage.unresolved_participants`, currently `0` everywhere). Serving
those as unnamed nodes — cp-06's *"unresolved debtor names are served, not
hidden"* discipline — would make it visible, and would also change what the
ingestion guard means. Recorded as the path, not taken.

---

## `CP07-F-03` — a class default cannot express a RELATIVE time window

**Status: CLOSED. The SDK gap is FIXED (`D-IMPL-325`) and this example has
adopted the fix.** The class now declares an offset the fabric resolves against
the request's own `asked_at`; the absolute date is gone. Details at the end of
this entry.

`CP-SPEC-007` §B.2 declares the default for `since` as **`−365 days`**. A
`ProductRequestContract`'s `defaults` block holds literal values, so what the
artifact can actually carry is an absolute ISO date:

```yaml
defaults:
  since: "2024-09-01"
```

That value **ages silently**. On the day it was written it meant *two years of
history*; a year from now it means three, the fan-out grows, and nothing
anywhere says the default drifted. The alternative — computing the date in
`deployment.request` — is worse: it puts a governance value back into code and
gives the deployment a second authority for one bound, which is the shape
`D-IMPL-315` exists to keep out.

**What the SDK would need:** a declared relative default, resolved against the
request's own `asked_at` at constraint-resolution time, so that the value stays a
Control Plane artifact and stays honest. Nothing in the current
`ProductRequestContract` surface expresses it.

### How it was closed

`D-IMPL-325` (Dave, 2026-09-10) added `ProductRequestContract.relative_defaults`
as a **separate** field — `defaults` stays literal-only — carrying
`offset_seconds: int` (negative; the SDK's existing duration vocabulary, per
`HalfLifeEntry.half_life_seconds`) and `render: Literal["date", "timestamp"]`
(declared, never inferred from JSON Schema `type: string`). It resolves in
`resolve_effective_request` beside the literal defaults and before the caller
overlay, reading `request.asked_at` — the instant that function already
evaluates constraint effectivity at, so it reads no clock and stays pure.

**What replay records is the resolved LITERAL**, under authority `default` with
the contract's own pin — never the offset. Dave's stated invariant: *"Replay
records the resolved absolute value and `authority=default`, not a rule that
gets recomputed later."* A rule re-evaluated at replay time would answer one
decision differently on two days.

The declaration is validated at declaration time (the parameter exists, is not
inert, carries exactly one default authority, and its declared type can hold the
render) and the **computed** value at request time (the normal domain and
conformity checks, which the resolution's existing conformity step already runs
over effective values). Dave ruled against forbidding a relative default where
an `argument_domains` entry exists: *"That is not weaker governance; the value
simply does not exist until `asked_at` exists."*

### What this example adopted, and the one thing that changed with it

`ccf_config.yaml` now declares:

```yaml
relative_defaults:
  since:
    offset_seconds: -63072000   # two years
    render: date
```

**Two years, not the `−365 days` `CP-SPEC-007` §B.2 declared — and the reason is
`CP07-F-04` arriving from the other direction.** Measured before the value was
chosen, served against the curated estate at `asked_at` 2026-09-11 on
`JJAX4X60DE65EYFOTY73` with the class `limit` of 200:

| offset | resolved `since` | available | NTK withheld | admitted | truncated |
|---|---|---|---|---|---|
| −31536000 (1 yr) | 2025-09-11 | **179** | **0** | 179 | **False** |
| −47304000 (1.5 yr) | 2025-03-12 | 218 | 1 | 200 | True |
| **−63072000 (2 yr)** | 2024-09-11 | **240** | **1** | 200 | **True** |
| −78840000 (3 yr) | 2023-09-12 | 240 | 1 | 200 | True |

At −365 days **two of this rung's demonstrations stop firing**: truncation
(179 < 200) and need-to-know withholding (the one classified interaction is
older than a year). That is exactly the contradiction `CP07-F-04` adjudicated,
and it is resolved the same way — in favor of the demonstrations. Two years
reproduces the retired absolute default's behavior exactly while no longer
aging. The offset is an **illustrative calibration** under `D-IMPL-323`,
labeled in `ccf_config.yaml`, the README and §B.2.

`test_the_declared_window_still_exceeds_the_class_limit` asserts both
demonstrations still fire, so a later author narrowing the offset is told at the
point of the change rather than discovering it in prose.

**One test changed, and it is the allowed case.** `D-IMPL-261` permits an
example change when *"the SDK surface it legitimately consumes was deliberately
changed"*. `test_the_class_default_resolves_for_a_caller_who_sent_no_bound` read
`config()["request_contract"]["defaults"]["since"]`, an authority location that
no longer holds the window. Its stated intent — read the declaration, never a
literal — is preserved: it now reads the declared offset and derives the
expected date from the instant the door was driven at. Nothing was weakened to
make it pass.

---

## `CP07-F-04` — `CP-SPEC-007` §B.2 makes two claims that cannot both hold

**Status: RESOLVED in this build. Defect in the SPEC, corrected here, and the
correction is recorded rather than silently applied.**

§B.2 states both:

- `since` default is **`−365 days`**; and
- *"truncation disclosure fires at 240 on `JJAX4X60DE65EYFOTY73`"*.

Measured: that client holds **240** interactions spanning **2024-09-21 →
2026-08-16**. A 365-day window holds **180** of them — under the `limit` of 200,
so **nothing truncates** and the rung demonstrates nothing.

Resolved in favour of the second claim, because it is the one the rung exists to
teach: the class default `since` is `2024-09-01`, the full history, and the
default run truncates at 200 of 240 exactly as §B.2 promises. §B.2's first
cell is wrong and should be corrected to match when the spec is next revised.

This is a spec correction, not an example fix under `D-IMPL-261`: the example was
built to the spec, the spec disagreed with itself, and the reconciliation is
disclosed here rather than buried in a YAML default.

---

## `CP07-F-05` — the bound manufactures a coverage gap, and only the disclosure separates it from a real one

**Status: NOT A DEFECT. The product's own subject, recorded because it is the
measurement the rung exists to produce.**

Same client, same instant, same estate:

| `limit` | admitted | truncated | coverage gaps | material |
|---|---|---|---|---|
| 500 | 239 of 240 | `False` | 0 | 0 |
| 200 (default) | 200 of 240 | `True` | 0 | 0 |
| 20 | 20 of 240 | `True` | **3** | **2** |

(`239 of 240` rather than `240`: one interaction on this anchor is
classified need-to-know and is never materialized, so it is not admissible and
does not count as truncation.)

At `limit=20` the product reports three officers *nobody has ever met*, two of
them in material roles. The meetings happened; they fell outside the window. The
finding is not wrong about the graph it was given — it is wrong about the world,
and **nothing inside the payload distinguishes the two** except
`evidence_boundary`.

That is why the disclosure is a declared `product_gate` (`D-IMPL-282`) rather
than a line of prose: a payload cut by its bound that does not say so becomes a
governed refusal before a consumer sees it.
`test_a_silent_truncation_is_refused_by_the_declared_gate` sabotages the
disclosure and watches the SDK refuse; disarming the gate turns it red.

---

## `CP07-F-06` — three identity traps, each of which produced a silently empty graph

**Status: RESOLVED. Estate/vocabulary facts, now declared rather than assumed.**

Recorded because each one costs a build the same way — an empty or disconnected
graph, no exception, a payload that looks like an answer.

1. **A client is not addressed by its LEI.** `JJAX4X60DE65EYFOTY73` is the node
   `SuburbanPropanePartnersLP`. Walking from the LEI returns **zero edges,
   silently**. Resolved through `ex:lei` and declared in
   `artifacts/source-vocabulary.yaml`.
2. **Node ids carry a kind prefix.** Interaction `INT-00000` is the node
   `interaction-INT-00000`. Minting the node claim at the unprefixed id puts it
   at a URI no edge points to; `deployment.ingest` catches it — *200 of 450
   admitted nodes carry no kind* — but only because that assertion exists.
3. **`employedBy` is FIBO's `isEmployedBy`, in a different namespace.** An
   earlier revision of this spec asserted that no `participatedIn` predicate
   existed in `fibo-v2`, from a search that looked only at `ex:` local names. It
   holds **8,032 assertions**. `ccf-dataprep` corrected the claim before any code
   was written against it, and the decoys (`ex:participationIn` /
   `ex:participationOf`, 97 each, an unrelated syndicate reification) are named
   in the vocabulary so nobody repeats the search.

---

## `CP07-F-07` — the TTL ceiling binds, inverting every rung before this one

**Status: NOT A DEFECT. Recorded because it is a contrast worth teaching.**

On cp-02, cp-04 and cp-06 the **data** expires the product: a filed document or
a valuation decays faster than any declared ceiling. Here every declared λ_c is
**slower** than §B's 12-hour ceiling — the slowest is an officer roster at a
year — because the question is about the bank's own current posture rather than
a document's age, which is what `ttl_anchor: from_decision` declares.

`CoverageScenario.product_ttl_seconds` therefore takes the **minimum** of the
fastest λ_c and the class ceiling. Taking the λ_c alone produced a `ttl-bounds`
refusal on the first end-to-end run, which is the SDK's third validation gate
doing exactly its job: a 7-day expiry cannot be served under a 12-hour
obligation.

---

## `CP07-F-08` — cp-06's shipped MCP door cannot answer its first call

**Status: FIXED at `54c4227d`, merged at `b85cf524`, accepted by Dave at
`D-IMPL-324`. The deferral this entry records was honored: the repair landed on
its own branch, not this one.**

Dave's ruling named the cause correctly and inverted the intuitive order:
*"declaration ≠ door"* — cp-06 shipped a door that had **never been booted**, and
`test_cp_06_mcp_door.py` (the driven-door test) is the actual fix. The two
defects this entry found were consequences. Deleting the hand-rolled
`RefusalEnvelope` was classified as *"the refusal path becoming honest"* rather
than a bug fix.

**Original status, kept because the deferral was the right call:** defect in
ANOTHER example (`examples/cp-06-collateral-and-setoff-coverage`), already merged
to `main`, found by driving cp-07's door, and deliberately not fixed on this
branch — that would have mixed two claims behind one review (the `CP06-F-01`
precedent).

`server/serve.py` hands the resolver a scratch root:

```python
resolver=build_resolver(root=root / "assembly"),
```

`root / "assembly"` is **never created**. `deployment.connection` then hands
SQLite a path inside it, and SQLite does not create a missing parent. Measured
2026-09-10, driving the shipped cp-06 door with the shipped cp-04 MCP driver
against the curated estate:

```
cp-06 door isError: True | Error executing tool request_context_product:
                           unable to open database file
```

**Why it was invisible.** cp-06 ships `server/door.yaml` and `server/serve.py`
and a test that the door *declares* a `module:callable` entry point — a static
check that reads the YAML. **Nothing ever booted the door.** A door that has
never been opened passes every test written about its declaration.

The failure also arrives as an MCP transport error rather than a governed
response, which from a consumer's side is indistinguishable from a producer that
never started.

cp-07's own door creates the directory where it names it, and
`tests/examples/test_cp_07_mcp_door.py` drives the shipped door end to end so
this class of defect cannot ship again from this tree.

---

## `CP07-F-09` — a door's hand-rolled refusal could not be constructed, and turned a governed "no" into a runtime failure

**Status: RESOLVED in cp-07 by DELETING the compensating code. The same defect
is OPEN in cp-06 on `main`, and is not fixed on this branch.**

Both doors carried this:

```python
if not facility or not scope:
    return RefusalEnvelope(
        reason="missing-required-argument", key=..., detail=...)
```

`RefusalEnvelope` declares none of those fields. It requires `kind`, `fields`,
`request` and `pre_assembly_lineage`, and `kind` must come from the SDK's
`REFUSAL_KINDS` vocabulary. The constructor raises a `ValidationError`, the
egress layer catches it as a runtime failure, and the caller receives:

```
Error executing tool request_context_product: ccf-runtime-failure:<id>
```

which the SDK's own docstring reserves for *"CCF or its runtime failed"* and
explicitly promises a governed determination never arrives as.

### The resolution, and why it is a deletion rather than a repair

The door should never have refused this. `lei` and `principal_scope` are
`required` in the request contract, so **the Control Plane already refuses a
question missing either** — and does it properly. With the hand-rolled check
deleted, the same call now returns:

```
kind      : product-request-violation
fields    : declared_keys [...,"lei",...] / presented_keys [... no "lei" ...]
replay_ref: ccf-artifact://cp-07-demo/ccf.replay-record/ccdf15f2…
isError   : false        # a governed refusal is a SUCCESSFUL response
```

This is `D-IMPL-289` exactly: *code that reconstructs what should have been
declared dies with the declaration fix.* The door refuses nothing of its own,
and the refusal it used to fabricate is now a governed determination with a kind,
a key and a replay record.

**A second compensating path was deleted with it.** `deployment.acquire_for`
fell back to the caller's raw parameters when the constraint resolver refused —
which would have run the source reads at bounds governance had just declined to
grant. A refused question is now not read at all: `acquisition.nothing_acquired`
carries the anchor far enough for the governed resolver to issue its refusal, and
neither source store is touched.

---

## `CP07-F-10` — `make product-gates` cannot be made green for any rung built since cp-04, and this rung is the fourth

**Status: CLOSED by `D-IMPL-326` and `D-IMPL-327`, and closed the way this entry
asked — the ruling changed the tool's model, and no number was invented.**

Dave ruled it a tooling-model fix: a gate's acceptance authority may be a
numbered ROADMAP criterion **or** a cited clause of the product's own `CP-SPEC`,
exactly one per gate, with the checker resolving document → clause → the gate's
own id inside that clause. `D-IMPL-327` then gave cp-04-canonical its own
`CP-SPEC-004C` and cp-05's §G.2 stable ids. Measured at that close:
**`checked 9 product trees, 93 declared gates, 93 executing`**. The correction
this entry's own text needs is recorded below.

**One correction to what is written here.** This entry says
`tools/check_product_gates.py` *"requires a locked ROADMAP criterion"*. It never
did — the word ROADMAP appears nowhere in that file. The requirement lived in
`docs/schemas/product-gates/cp.product-gates.json`, where `criterion` sat in the
gate item's `required` list. The distinction mattered: it made the fix a schema
edit rather than a checker rewrite.

**What remains, and it is a different thing:** `CP07-F-11` carries the two §G.1
gates cp-07's roster does not declare.

`tools/check_product_gates.py` requires every `examples/cp-*` tree to carry
`artifacts/gates.yaml`. Measured on `main` at this branch's base, with no cp-07
work in the tree:

```
examples/cp-04-canonical-corporate-family-tree: artifacts/gates.yaml is missing
examples/cp-05-credit-exposure-rollup:          artifacts/gates.yaml is missing
examples/cp-06-collateral-and-setoff-coverage:  artifacts/gates.yaml is missing
```

cp-07 is the fourth, and the reason is the same for all four.

### Why the roster cannot be written as the schema stands

`docs/schemas/product-gates/cp.product-gates.json` makes **`criterion` a
required field** on every gate, described as *"the locked ROADMAP
success-criterion number this gate discharges. One gate per criterion and one
criterion per gate."* That binding exists for cp-00 through cp-04, which were
built inside numbered GSD phases with locked ROADMAP criteria.

**cp-05, cp-06 and cp-07 were not.** They are ladder rungs built directly, and
there is no locked ROADMAP criterion for a gate here to discharge. Writing a
roster would mean inventing criterion numbers that bind to nothing — a
declaration that reads as evidence and is not, which is the failure mode this
whole artifact class exists to prevent.

### The three readings, for Dave

1. **Make `criterion` optional**, or add an explicit "no phase criterion"
   value. The gate roster survives, the false binding does not, and all four
   rungs can declare their gates as data.
2. **Scope the checker to rungs built inside a numbered phase.** `product_trees`
   globs `examples/cp-*` *"by construction, not by an allowlist"` — deliberately
   — so this would mean re-deciding that construction, not adding an exemption.
3. **Mint ROADMAP criteria retroactively** for the four rungs. This contradicts
   `D-GATE-19` (*criteria must exist before execution, never authored
   retroactively*) and is recorded only for completeness.

Nothing is done here. The gates cp-07 declares are executed and sabotaged —
`test_a_silent_truncation_is_refused_by_the_declared_gate` watches the fourth
validation gate refuse, and `deployment.ingest`'s two guards were each watched
red against the live estate — but they are not declared as a roster, because the
roster as specified cannot be written truthfully for this rung.


---

## `CP07-F-11` — two of §G.1's eight gates were not in the roster

**Status: FIXED, 2026-09-11.** `artifacts/gates.yaml` now carries **9**, and
§G.1 declares nine, because closing this split one gate in two.

**`C36-G06`** — *"the enrich leg issues a fixed number of queries regardless of
graph size"* — needed a counting seam, which is why it had no test.
`_GraphLeg.query` is now wrapped for the duration of two acquisitions and the
call counts compared across two clients of very different size. Measured: **5
and 5**. Sabotaged by making the participation walk issue one query per
interaction row, which takes the counts to **205 and 44** and reddens the
equality limb. The test also requires the fixed count to be SMALL, because an
equal count that rose with the estate would satisfy neither half.

**`C36-G08`** — was two claims under one id, and a gate carries one `test:`.
Mapping it to either test would have claimed evidence for half its statement.
**§G.1 is now split**: `C36-G08` is *"`shape_of` reads this tree as
`canonical`"* and `C36-G09` is *"the plan factory takes its operators only from
the resolver's `required`"*, each mapped to the test that already proved it.
Both test docstrings were updated to claim their id, because the checker
requires the executing test to be the evidence — a roster entry pointing at a
function that does not name the gate is exactly the `L-18` witness class.

**No gate was declared against a test that does not assert it.**
