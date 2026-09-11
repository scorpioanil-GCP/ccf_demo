# Findings — cp-07 client 360 / coverage graph

Adjudicated under `D-IMPL-315`: *"canonical path is richer"* is a finding to
adjudicate, never a licence to edit the example. Each entry states whether the
defect is the SDK's, this example's, the spec's, or the estate's — and each one
below was **measured before it was written**.

---

## `CP07-F-01` — `D_c` reads `fail_closed` on every anchor, and freshness is the whole of it

**Status: OPEN. Needs a ruling. NOT tuned around.**

### The measurement

Demonstration anchor, class defaults, 2026-09-10:

```
freshness            = 0.0409
completeness         = 1
semantic_consistency = 1
D_c                  = 0.9591      signal: fail_closed
```

The control client reads `0.9492`, also `fail_closed`. The `D_c` is entirely the
freshness term.

### Why

§E declares `λ_c` for `interaction_record` at **~7 days**. The newest interaction
anywhere in the curated estate is **2026-08-16** — about 25 days before the
decision instant, or three and a half half-lives. Every anchor therefore scores
near zero on freshness, whatever else is true of it.

The freshness observation supplied per party is that party's **most recent**
contact, not one observation per historical interaction; that reading was chosen
deliberately (a relationship refreshed last week is current whether two meetings
sit behind it or two hundred) and it is the *favorable* one. The unfavorable
reading — one observation per admitted interaction, 200 of them — scores
`F = 0.0038`, `D_c = 0.9962`. **Both readings are `fail_closed`**; the choice of
reading does not rescue the signal, which is why the ruling below is about the
declaration and not about the code.

### What this is NOT

It is not an SDK defect. `FreshnessScorer` reads the declared table and returns
what the declaration implies. It is also not something to fix by moving a
number: **the estate is what it is, the spec ruled ~7 days at Gate 1, and
optimizing a λ_c until the signal reads green would make the product's own debt
measurement decorative.**

### The question for Dave

Three readings, and one of them is his to pick:

1. **λ_c is miscalibrated for this signal class.** An *interaction record* does
   not decay — the meeting happened. What decays is **coverage currency**, and a
   coverage banker would not call a three-week-old contact stale. On this
   reading `interaction_record` wants something closer to 30–60 days and the
   spec's §E row is corrected.
2. **The estate is stale and `fail_closed` is the correct answer.** A coverage
   product whose freshest evidence is 25 days old genuinely should not be
   trusted for meeting prep without a human, which is exactly what
   `fail_closed` means. Nothing changes; the product is telling the truth.
3. **The reading of "interaction recency" is wrong.** Freshness should follow
   the single most recent interaction *anywhere in the graph* rather than a
   per-party average, so one current contact keeps the whole picture current.

This example implements (2) as shipped, because it is the one that changes
nothing and asserts nothing Dave has not ruled.

---

## `CP07-F-02` — the completeness term cannot move in this deployment, for two independent reasons

**Status: OPEN. Needs a ruling. Recorded rather than repaired, because
`D_c` that does not move when the evidence moves is decorative.**

§E defines `C` as *"people the enrich leg resolved ÷ people the walk
admitted"*. Measured, it is exactly `1` on both anchors, and it is `1` for two
reasons that would each be sufficient alone:

1. **The estate carries no unresolved participant.** Every subject of a
   `participatedIn` edge on both anchors resolves to a row in the roster leg —
   25 of 25 on the demonstration client, 16 of 16 on the control.
2. **The ingestion guard refuses the state the metric would score.**
   `deployment.ingest` asserts that no admitted node lacks a kind. An edge
   endpoint with no node claim of its own IS that state, so a run carrying an
   unresolved participant fails at ingestion and never reaches `debt()`.

Reason 2 is the load-bearing one and it is structural: the guard and the metric
measure the same condition, one fail-closed and one as a score, so the score can
only ever read `1`. The guard is right — a graph with unnamed nodes should not be
served — but it means `C` contributes nothing on this rung.

**What `C` could measure instead**, if Dave wants it to move: the participants
PostgreSQL names in `interaction_participant` that the roster leg could not
resolve (`Coverage.unresolved_participants`, currently `0` on both anchors).
That is genuinely a completeness gap, it is not pinned by the guard, and serving
those parties as unnamed nodes — cp-06's own *"unresolved debtor names are
served, not hidden"* discipline — would make it visible. It also changes what the
ingestion guard means, so it is not a change to make without a ruling.

---

## `CP07-F-03` — a class default cannot express a RELATIVE time window

**Status: OPEN. SDK gap, small and real.**

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

**Status: OPEN. Defect in ANOTHER example
(`examples/cp-06-collateral-and-setoff-coverage`), already merged to `main`.
Found by driving cp-07's door, which inherited the same code shape. NOT fixed on
this branch — that would mix two claims behind one review (the `CP06-F-01`
precedent).**

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

**Status: OPEN. Needs a ruling. NOT resolved by inventing numbers.**

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
