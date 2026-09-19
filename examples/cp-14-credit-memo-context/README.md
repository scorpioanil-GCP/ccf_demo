# Credit Memo Context — rung 14, the five-child composite on the paved road

`credit-risk.credit-memo-context` @ `1.0.0` · Tier 5 · five required children from five
producers in five other processes · reads the curated `.76` estate through its own two
legs, writes nothing · `CP-SPEC-014`

**A consumer can use the product it needs without knowing how its provider assembled
it.** Five producers — two frozen specimens' paved successors, one paved re-expression,
one frozen specimen behind a wrapper door, one canonical producer — answer five mapped
questions over the SDK's standard door; the memo composes what they served and rebuilds
none of it.

> **Scope of this delivery.** It proves five-provider acquisition, admitted-content
> composition, governed refusal, and reconstruction. It does not complete the full
> memo-assembly specification: twelve of `CP-SPEC-014`'s twenty-nine gates are executed
> here; the seventeen that name the memo's own unbuilt logic stay planned obligations of
> that contract (spec §0.0a, `FINDINGS.md` `CP14-F-37`). `memo_type` admits the one
> implemented mode, `annual-review`.

## What this demonstrates

**Both outcomes, neither promised.** At the memo's governed tolerance (0.25, the v2
policy's default at the CP-14 instant) three producers WITHHOLD — the spread, the
exposure roll-up and the covenant cross-reference each measure a Context Debt above
it — the family and the collateral are admitted, and the composite refuses on its
required slots with all five rows persisted and the first blocking producer's reason
retained (the other withheld rows carry the admission verdict, `D-IMPL-342`). At
the labeled diagnostic tolerance (1.0) all five children are admitted under
`provider-controls` and the memo is SERVED: `D_c` 1.0 `fail_closed`, because inherited
debt is the per-factor minimum and the exposure child's freshness is zero against a
four-hour half-life. Nothing was tuned to obtain either outcome; the transcript in
`page/run-transcript.txt` is both, verbatim.

**The consumer determines which question to ask; it answers nothing.** The covenant
child takes the evidence nodes it may read. Which nodes are the memo's is a fact about
the obligor's own facility documents — the roster's document keys joined to the
ledger's anchors (`CP14-F-28`) — and the mapping reads exactly that and nothing below
the anchor. The other four questions are the memo's subject, its facility and its
tolerance, mapped once in `deployment.py`.

**Composition is from the admitted contracts, and read correctly — provably so.** Each
memo section records the content address it was composed from, and that address equals
the address the admission row retained — five for five. Every printed field names the
child member it is (`projection.SECTION_FIELDS`) and an independent test holds each to
the retained child: the collateral figure is the child's collateral after haircuts,
with set-off and total kept apart; the spread's basis is the member the producer
serves. A controlled variant that asks the collateral child a different question moves
the collateral section and the memo's address and nothing else. The product's content
address and the replay record's address are two identities, printed separately, and
the record names the product it served. With every producer process exited, replay rebuilds the memo
from the retained contracts and reproduces its bytes; the governed refusal reconstructs
along its recorded path with the admitted children's evidence intact.

## Run it

```
export CCF_CP_14_POSTGRES_DSN=postgresql://...   CCF_CP_14_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_14_FLUREE_URL=http://<host>:8090    CCF_CP_14_FLUREE_LEDGER=fibo-v2
# boot the five producers, each in its own terminal, and export the port each prints:
.venv/bin/python examples/cp-03-canonical-obligor-financial-spread/run.py --door      # CCF_CP14_SPREAD_URL
.venv/bin/python examples/cp-04-canonical-corporate-family-tree/run.py --door         # CCF_CP14_FAMILY_URL
.venv/bin/python examples/door-cp-05-credit-exposure-rollup/run.py --door             # CCF_CP14_EXPOSURE_URL
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door # CCF_CP14_COLLATERAL_URL
.venv/bin/python examples/cp-13-canonical-covenant-cross-reference/run.py --door      # CCF_CP14_COVENANT_URL
export CCF_CP14_SPREAD_URL=http://127.0.0.1:<port>/mcp CCF_CP14_SPREAD_TOKEN=<the door's credential>   # and the other four
make -s example-cp-14                                       # the governed question: refused, five rows
make -s example-cp-14 DEBT_TOLERANCE=--debt-tolerance=1.0   # the labeled diagnostic: served
.venv/bin/python examples/cp-14-credit-memo-context/run.py --debt-tolerance 1.0
```

Each door's credential is the value of its `CCF_CP_*_DOOR_TOKEN` variable, or a token
it mints per boot when that is unset. The v2 namespaces are not in
`ccf_dataprep/.env`, which names v1. The governed run exits 0 with a refusal: a
refusal is an answer.

## The story

### 0. Five doors, one registration each

`ccf_config.yaml` declares the five requirements, the five producers by identity and
tenant, the five skills and the agent that holds their grants; the SDK registers,
asks, admits and composes. The consumer constructs none of that machinery.

### 1. The governed question refuses honestly

Three producers withhold at 0.25. The composite refuses `composite-child-refusal`; the
disclosed envelope stays minimal; the record retains the first blocking producer's
`tolerance-exceeded` and identity, the admission verdict on every withheld row, and the
admitted family and collateral contracts by address and by bytes.

### 2. The diagnostic serves, and says what it is

**Measured 2026-09-15 and preserved as the historical result.** Since
`D-IMPL-341` (2026-09-18) the collateral producer refuses this facility's
question — its valuation is older than the window it now anchors on — so the
required slot is `ineligible` and the memo refuses at the diagnostic tolerance
too. The section below is what the memo served before that, and what it will
serve again once the collateral class's calibration is ruled (`CP14-F-40`,
cp-06-canonical `CP06C-F-05`). Nothing in it was tuned away.

At 1.0 the memo serves five sections read off five admitted payloads by name — the
spread's periods, the family's entities and circuits, the exposure's regime and
totals, the collateral's coverage with collateral and set-off apart, the covenant's
checked citations — and inherits the worst factor per axis: freshness from the exposure
child, completeness from the covenant child. It expires with its stalest child. Asked a
second time against unchanged inputs it yields the same product address.

### 3. Reconstruction without the providers

Replay resolves the five retained contracts from the consumer's own store, hands them
to the memo's own plan factory, and reproduces the served address with no door alive.

## Artifact-by-artifact

| file | role |
|---|---|
| `ccf_config.yaml` | the product, its five requirements, the five producer registrations, skills, agent, replay binding, TTL — one document |
| `ccf_environment.yaml` | the NAMES the roster and ledger legs and the five endpoints and credentials are read from |
| `artifacts/source-vocabulary.yaml` | the roster tables, the facility document keys and the three ledger terms the question determination reads |
| `artifacts/gates.yaml` | the twelve declared gates the completion executes against the five real producers |
| `spec/CP-SPEC-014_…md` | the specification, Gate 1 |
| `produce.py` | the spine: one `open_product`, a named plan factory with its child-aware seam, the mapping bound to the resolved sources |
| `deployment.py` | the ONE question mapping, the roster leg's envelopes, `D_c` |
| `acquisition.py` | the roster read and the two question-determination reads |
| `projection.py` | Π: the obligor off the view, five sections off the admitted contracts |
| `run.py` | presentation only |
| `page/` | the generator, the template and the committed transcript of both runs |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §6.6 (recursive context enrichment: a product of products), §7.6 (the
three gates and the composite's admission), §7.7 (inherited debt per factor), §7.10
(five child rows on every exit; reconstruction from retained artifacts). CLAUDE.md
§7.1 (MCP as the producer boundary), §7.2 (cross-deployment admission under a
registered identity), §9 (probes, not repair targets; both outcomes demonstrated),
§10 (L2 the only writer). `D-IMPL-336`/`338`/`339`/`340`/`343`/`344`.

## What to change first

`producers:` in `ccf_config.yaml` to point a slot at another producer of the same class
— the lane floor and the identity are the only things the consumer holds it to.
`deployment.py::MemoQuestions` to ask a slot a different question;
`projection.py::SECTION_FIELDS` to print another member a child serves. Nothing in
`produce.py` is yours.

## What would fail

Ask the covenant child with no sources (it refuses, and so does the composite); compose
a section from a store re-query instead of the admitted contract (`CMC-G28`); read a
pledge, an ownership record or a financial fact in the consumer's own leg (`CMC-G27`);
construct the child resolver or the admission gate by hand (`CMC-G23`); wrap a withheld
child as a served empty section (`CMC-G18`); resolve a child from its producer during
replay (`CMC-G29`); print a child's `coverage.total` as collateral, or read a member
where the producer does not put it (the field-mapping control); label the record's
address as the product's (the identity control).
