# Client 360 / Coverage Graph — rung 7

`coverage.client-360.v1` · Tier 2 · PostgreSQL + Fluree · reads the curated
`.76` estate, writes nothing.

**Who at the bank actually knows whom at the client — and where the evidence
ran out.**

## What this demonstrates

**A graph can be populated and still be incomplete, and only the product can
tell you which.** Every rung before this one asked whether the fabric had the
right facts. This one asks a harder question: *the fabric returned 200
interactions — were there 200?*

Two things are demonstrated together, and the second is why the first matters.

**1. Coverage is a path, not a field.** A CRM answers *"who is the covering
banker?"* — one column, one value, always populated, frequently wrong. It cannot
answer *"who has met this person, how recently, and alongside whom?"*, because
that is a walk over an interaction graph and there is no column to put it in.
The product returns each banker's measured relationship strength and, from the
same frame, the **coverage gaps**: client-side officers whose strongest
bank-side relationship is weak or absent. On the control client that is nine
officers nobody has ever met.

**2. A bounded acquisition can manufacture a coverage gap that does not exist.**
Measured on the demonstration anchor, at the class default `limit=200`:

```
coverage gaps : 0
```

At `limit=20`, same client, same instant, same estate:

```
coverage gaps : 3      of those, MATERIAL roles : 2
```

The bound did not discover that nobody has met the CFO. It hid the meeting. The
finding is not wrong about the graph it was given — it is wrong about the world,
and nothing inside the payload distinguishes the two. That is why truncation
disclosure here is a **declared validation gate**, the product's fourth, and not
a line of prose: a payload that was cut by its bound and does not say so is
refused before a consumer sees it.

**And truncation is deliberately NOT folded into Context Debt.** Forty omitted
of 240 is not incompleteness; it is a deliberate act with a known edge, and the
edge is disclosed rather than scored. `D_c` measures something else — how
complete the evidence *that was admitted* actually is. The two statements are
different and the product makes both.

## Run it

```bash
export CCF_CP_07_FLUREE_URL=http://<host>:8090
export CCF_CP_07_FLUREE_LEDGER=fibo-v2          # the v2 namespace, never fibo:main
export CCF_CP_07_POSTGRES_DSN=postgresql://<user>@<host>:5432/<db>
export CCF_CP_07_POSTGRES_SCHEMA=ccf_v2         # never public

make example-cp-07                                       # the truncated anchor
make example-cp-07 LEI=--lei=529900L7KB2N9KXCDI76        # the untruncated control
make example-cp-07 LIMIT=--limit=20                      # watch gaps appear
make example-cp-07 NTK=--need-to-know                    # a different graph, not a redaction
```

Every flag is **omitted** unless you pass it, so the class default in
`ccf_config.yaml` resolves — a different act from passing the default's value.

Both legs are read-only. L3 is a per-run SQLite file discarded with the run;
nothing is written to either source store (CLAUDE.md §9).

```bash
.venv/bin/python -m pytest tests/examples/test_cp_07_output.py
```

The tests skip without the four variables and are directional throughout: they
assert business relationships — a wider window cannot admit less, a tighter bound
cannot find fewer gaps, `D_c` must not track the size of the bound — rather than
counts that go stale the next time `ccf-dataprep` loads a meeting.

## The story

A coverage banker is preparing for a meeting. The CRM says three bankers cover
SUBURBAN PROPANE PARTNERS LP. That is true and nearly useless: it does not say
who has actually spoken to anybody, how recently, or which of the client's
twenty-two officers has never met a soul from the bank.

The product assembles the answer from two stores that each hold half of it. The
**edges** — who covers whom, who took part in what, who is employed by whom —
are Fluree's. The **attributes** — names, seniority, desks, dates, channels,
need-to-know classification — are PostgreSQL's. Neither store can answer the
question and nothing is duplicated across them.

Three identity facts had to be *declared* rather than assumed, and each one cost
a silent empty graph before it was:

- **A client is not addressed by its LEI.** `JJAX4X60DE65EYFOTY73` is the node
  `SuburbanPropanePartnersLP`. Walking from the LEI returns nothing, silently.
  `artifacts/source-vocabulary.yaml` declares `ex:lei` as the predicate to
  resolve *through*.
- **A business id needs its kind prefix to become a node id.** Interaction
  `INT-00000` is the node `interaction-INT-00000`. The payload still says
  `INT-00000`, because a consumer joins on the source's spelling.
- **`employedBy` is FIBO's `isEmployedBy`, in a different namespace.** A search
  that looked only at `ex:` local names reported `participatedIn` absent when it
  holds 8,032 assertions. That false claim reached the spec and was corrected by
  `ccf-dataprep` before any code was written against it.

Then the bounds. `since` and `limit` are **correctness features**, not
conveniences, and they are applied **in the read** — `ORDER BY interaction_date
DESC, interaction_id LIMIT n` — never by fetching everything and slicing. So is
the policy envelope: an interaction the principal may not see is never
materialized, so no participation edge to it is ever walked. Asking with
`include_need_to_know` returns a *different graph*, not a redacted one.

Ingestion order is a contract. Thin edge envelopes go first and attributed node
claims last, because the last claim at a URI wins and does not merge — an edge
arriving after a node erases that node's attributes and the payload then serves
a banker with no name and no seniority, with nothing raised. `deployment.ingest`
asserts the outcome rather than trusting the order; reversing the two lines
fails the run with *226 of 250 admitted nodes carry no kind*.

Then Π scores, reading **the admitted graph and nothing else** — no backend
lookup happens inside the projection, which is what lets the score replay from
the snapshot rather than from whatever the source held at read time.

One inversion is worth naming because it reverses every rung before it. On
cp-02, cp-04 and cp-06 the *data* expires the product: a filed document or a
valuation decays faster than any ceiling anyone would declare. Here every
declared λ_c is **slower** than the 12-hour class ceiling — the slowest is an
officer roster at a year — because the question is about the bank's own current
posture rather than a document's age. The ceiling binds, and
`ttl_anchor: from_decision` says so at registration.

## Artifact-by-artifact

| File | What it carries | Delete it and… |
|---|---|---|
| `ccf_config.yaml` | the whole deployment: product class, the declared truncation gate's identity, both operators, the request contract with its bounds and domains, the resolution rules, λ_c, the debt profile, the policy bundle | `produce.py` has nothing to interpret |
| `backends.yaml` | variable **names** and remedy text for both source legs, and the per-run SQLite path. No host, no credential | the run cannot find either estate and says which variable is missing |
| `artifacts/source-vocabulary.yaml` | the sources' own names — four edge IRIs with measured counts, the `lei` resolution predicate, the node kind prefixes, and the tables | `acquisition.py` knows no predicate and no table |
| `artifacts/projection.yaml` | the scoring weights, the seniority ranks, the recency horizon, the gap threshold, the material roles, and the truncation disclosure note | Π has no weights and the No-Hardcoding lint refuses the alternative |
| `server/door.yaml` | the MCP door's governance values and its `module:callable` entry point | `server/serve.py` has nothing to open |
| `spec/CP-SPEC-007_*.md` | Gate 1 — written **before** any of this code existed | you lose the record of what was promised before it was built |

Code beside them is thin and generic: `produce.py` names no predicate, table,
edge, weight or number at all.

## Whitepaper / CLAUDE.md sections exercised

- **§7.4 Context Operators** — two registered operators, policy before
  traversal. The vault lists five verbs for this product; three of them are not
  registered L4 operators on this SDK and must not enter `operators_invoked`,
  or lineage strict equality would seal a document claiming work no operator
  did (§D.2.1).
- **§7.5 Context Projection** — Π reads the admitted graph only. Structural
  typing: `required_operators()` + `invoke()`, no base class.
- **§7.6 Context Product Contract** — the three SDK validation gates plus this
  product's own fourth, supplied as a `product_gate` and executed by the SDK at
  the ruled point (`D-IMPL-282`: the gate's identity is the Control Plane's,
  its implementation the deployment's).
- **§7.7.4 Context Debt** — and the boundary around it: a disclosed bound is
  not a debt input.
- **§7.10 Decision Replay** — the five-dimension record, with dimension 2 a
  superset of the product's own policy lineage (`D-IMPL-310`).
- **CLAUDE.md §6.4 No-Hardcoding** — every weight, threshold, note, IRI and
  table name is in an artifact.
- **CLAUDE.md §9** — the curated estate is evidence, not a fixture: read-only
  on both legs, nothing seeded, no ledger created.
- **CLAUDE.md §10** — single-writer: `booted.handle.worker` is the only write
  handle to L3 in the process.

## What to change first

1. **`artifacts/projection.yaml`** — the weights and the gap threshold. They are
   this bank's judgment about what a relationship is worth, not the SDK's. Raise
   `gap.weak_at_or_below` and more officers become gaps; change
   `gap.material_roles` and the ones that matter change.
2. **`artifacts/source-vocabulary.yaml`** — the four edge IRIs and the node
   prefixes. Point them at your own graph's names and nothing in the code
   changes.
3. **`ccf_config.yaml::request_contract.defaults`** — especially `limit` and
   `since`. They are the acquisition boundary, and this example exists to show
   that moving them moves the *answer*, not just the runtime.
4. **`ccf_config.yaml::half_life`** — four signal classes. On this rung they are
   all slower than the TTL ceiling; on your estate they may not be, and the
   product will expire on whichever binds.

## What would fail

- **Reverse the ingestion order** (nodes before edges) and `deployment.ingest`
  raises: *226 of 250 admitted nodes carry no kind after ingestion.* Without
  that assertion the payload would serve unnamed bankers and say nothing.
- **Drop a kind prefix** from a node address and the same guard fires — *200 of
  450* — because the node was minted at a URI no edge points to.
- **Suppress the `truncated` flag** while leaving the counts intact and the
  declared gate turns the product into a **governed refusal**. `tests/examples/
  test_cp_07_output.py::test_a_silent_truncation_is_refused_by_the_declared_gate`
  does exactly that, and disarming the gate turns the test red.
- **Fold truncation into `D_c`** and
  `test_truncation_is_not_folded_into_context_debt` fails: it measures `D_c`
  across two bounds that omit an order of magnitude apart and requires the score
  not to track them.
- **Point `CCF_CP_07_FLUREE_LEDGER` at `fibo:main`** (the v1 namespace) and the
  client resolves to no node — an empty coverage graph that looks like a client
  nobody knows.
- **Ask for an LEI that resolves to no row** and acquisition raises rather than
  returning an empty graph. An unknown client is a claim about the request; an
  empty graph is a claim about the world, and they mean opposite things.

Open findings — including the `D_c` reading this estate produces at the declared
λ_c, and the `since` default this build had to reconcile — are in `FINDINGS.md`.
