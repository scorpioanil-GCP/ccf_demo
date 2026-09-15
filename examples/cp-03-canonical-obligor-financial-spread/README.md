# Obligor Financial Spread — the canonical rung-3 example

Serves one obligor's period-aligned financial spread as a governed Context
Product — every figure naming the period it describes, the filing that asserted
it, the basis it was read under and whether a later filing changed it — with the
measured Context Debt in force when the answer was assembled, the content address
the answer hashes to, and the replay record that authorized it. Reached
in-process, and through an MCP door another deployment can acquire it from.

## What this demonstrates

There are **two** rung-3 examples in this repository and they are not versions
of each other.

| | `examples/cp-03-obligor-financial-spread` | **this tree** |
|---|---|---|
| what it is | a **frozen historical specimen** | the **current pattern to copy** |
| status | frozen under `D-IMPL-261`; **zero files changed** by this work; 13 of 17 tests quarantined | authored against the SDK as it ships today |
| does it serve? | **no** — `intent` declared as an argument, `build_replay_record` with no resolution binding | **yes** — a governed `ServedProduct` of the same class |

The specimen and this tree serve **the same product**, `credit-risk.spread`.
`CP-SPEC-014` (the credit-memo composite) requires that class at a `1.0.0`
floor and could not acquire it from a tree that does not serve; this tree is
the producer it acquires from (`CP14-F-22`). It serves lane `1.1.0` — same
major, a different lane member from the specimen's `1.0.0` — because two
deployments must never share one lane.

**Copy from here. Read cp-03 only to see how far the SDK has moved.**

### The spread is the graph

The specimen ingested one envelope carrying the whole spread and dated it from
the payload's freshest filing; the per-figure filing dates lived inside an
object the graph never held, and Π read them from a scenario carried in from
the side. Here every period, every line and every cohort statistic is its own
entity, dated from the filing that asserted it. Π reads the view; the debt
reading dates each column from the graph; a principal who may not see the
obligor sees no period, no line and no cohort either.

### The uncomfortable conclusion, kept

At the instant `CP-SPEC-014` asks (`2026-09-07T12:00:00+00:00`, held rather than
tuned), the demonstration obligor — BGC Group, on CP-14's roster — serves with
`D_c = 0.8433` (`F` 0.3189 · `C` 0.4915 · `S` 1), signal `fail_closed`: most of
its thirteen columns are years old, and a financial firm files none of several
declared industrial tags. **At CP-14's own tolerance the spread is withheld.**
Under the declared 30-day window, three of the estate's fifty obligors can be
served at that instant, two of CP-14's twenty. Nothing was moved to make that
better.

### What the SDK does not yet do

The class declares `ttl_anchor: from_entity_freshness` and the governed path
records the declaration on the served contract while computing `expires_at`
from the decision instant. This tree holds the serving half of the declaration
in the product's own declared gate and raises the expiry half as
`CP03C-F-01` — visible as a strict `xfail` that turns red the day the SDK
honors the declaration.

## Run it

```bash
make venv

# Credentials and host come from the estate's own environment;
# THE NAMESPACE DOES NOT — .env names the v1 estate (CLAUDE.md §9).
set -a; source /home/parkave/ccf_dataprep/.env; set +a
export CCF_CP_03C_POSTGRES_DSN="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
export CCF_CP_03C_POSTGRES_SCHEMA="ccf_v2"         # v2, NOT public

# The demonstration obligor at the CP-14 instant, tolerance wide open.
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0

# The same question at CP-14's own tolerance: withheld, with a replay reference.
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=0.25

# Quietly, for a transcript.
make -s example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0

# Without make.
PYTHONPATH=src:runtime:examples/cp-03-canonical-obligor-financial-spread \
  .venv/bin/python examples/cp-03-canonical-obligor-financial-spread/run.py \
  --asked-at 2026-09-07T12:00:00+00:00 --debt-tolerance 1.0

# Variations: another obligor, the other basis, another principal.
make example-cp-03-canonical LEI=549300D0WZR1VI2QGB24 ASKED_AT=2026-08-29T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0 BASIS=latest-restated
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0 PRINCIPAL=PRIN-KYC-004

# The door: stdio (the entry point door.yaml declares), or a loopback HTTP port for a harness.
PYTHONPATH=src:runtime .venv/bin/python examples/cp-03-canonical-obligor-financial-spread/server/serve.py
PYTHONPATH=src:runtime:examples/cp-03-canonical-obligor-financial-spread \
  .venv/bin/python examples/cp-03-canonical-obligor-financial-spread/run.py --door
```

`ASKED_AT` omitted asks now — and at the time of writing every obligor's
latest filing is outside the window at "now", so the run refuses on the
product's own gate. That is the product being honest about a snapshot estate,
not a broken run. A refusal exits non-zero and prints its reason and replay
reference.

The tests read the same estate and seed nothing:

```bash
CCF_REQUIRE_ESTATE=1 PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/examples/test_cp_03_canonical_output.py \
  tests/examples/test_cp_03_canonical_cross_deployment.py -q -rs
```

## The story

Three things will bite you if you change them.

### 1. `intent` is an axis, not an argument

The specimen declared `intent` under `request_contract.arguments.properties`
and required it. The SDK refuses that at contract construction: `intent` is a
top-level `ProductRequest` field, and an argument of the same name shadows it.
What a class serves is declared once, on `product_class.discovery.intents`, and
judged there — a wrong intent is refused `class-mismatch` at `key=intent`, as
data. The test injects the specimen's shape into a copy of this tree's config
and watches the SDK refuse it, so the control is real rather than remembered.

### 2. The grant is request state, not a write over an artifact

The specimen declared a literal allowlist and then wrote the calling
principal's expanded grant over its resolved policy artifact from
`deployment.py`. Here `permitted_classifications` is bound to the effective
request's `jurisdictions`, defaulted in the contract to the default
perspective's expanded grant. The value that reaches the operator travels into
the operator parameter set's content hash and into replay.

### 3. A fresh fabric per run, and Π scoped to the subject

Measured while building the door: several questions under one scratch root
booted one SQLite file, and the third question's view still held the first
obligor's spread — a subject that resolved to nothing was served somebody
else's figures. `backends.yaml` declares `per_run: path`; `deployment.
connection` mints a fresh path per run; and Π serves the subject's claims and
no other's, so a view holding a second obligor cannot be served as this one's.

## Artifact-by-artifact

| file | what it is |
|---|---|
| `ccf_config.yaml` | the single Control Plane document — every section this deployment puts in force, including the discovery intents, the request binding for the grant, and the declared product gate |
| `backends.yaml` | how the one source store is reached. Variable **names** only; no host, port, schema or credential |
| `artifacts/source-vocabulary.yaml` | the store's own table names and the two fiscal markers |
| `artifacts/spread-lines.yaml` | the tag map, the ratio definitions with their `??` fallbacks, the (empty) adjustments — the specimen's declaration, byte for byte |
| `artifacts/restatement.yaml` | the fact identity key and the materiality threshold — the specimen's declaration, byte for byte |
| `artifacts/ttl.yaml` | the 30-day window and its anchor basis |
| `artifacts/gates.yaml` | the twenty-seven declared gates and the tests that claim them |
| `acquisition.py` | the three `SELECT`s and the arithmetic interpreter. **Imports no `ccf` at all** |
| `deployment.py` | this deployment's vocabulary, the envelopes, the debt, the product's own gate |
| `projection.py` | Π — the payload, read off the view and scoped to the subject |
| `produce.py` | **the fabric's half.** Three regions: `boot`, `acquire`, `govern` |
| `run.py` | presentation. The only module that prints |
| `server/door.yaml`, `server/serve.py` | the MCP egress door, with the identity it asserts; `run.py --door` boots it on a loopback port for a harness |
| `spec/CP-SPEC-003C_…` | this tree's own specification; §G.1 approves every gate |
| `FINDINGS.md` | what authoring this against the current SDK surface exposed |

`produce.py` contains **no domain vocabulary at all**. Delete `ccf_config.yaml`
and nothing in `deployment.py` has anything left to interpret.

### What is deliberately absent

No `gate` region, no `record` region, no `serve` region, and no call to
`run_gates`, `build_replay_record` or `serve` anywhere in this tree. The
specimen's call to `build_replay_record` with no resolution binding — one of the
two defects that keep it from serving — has nowhere to exist here.

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §6.3 (intent as an addressing axis), §7.3 (typed graph state — the
spread as entities), §7.4 (the policy operator), §7.5 (Π), §7.6 (the product
contract, its three validation gates, and the TTL anchor), §7.7 (half-life and
debt — two decay rates in one payload, aged from the source's own dates), §7.10
(Decision Replay), §8.3 Pattern 3 (MCP egress). CLAUDE.md §6.4 (No-Hardcoding),
§7.1 (MCP as egress), §9 (examples are probes; the estate is evidence), §10
(single-writer).

Rulings it is authored against: `D-IMPL-264` (intent is a top-level axis;
resolution is an explicit binding), `D-IMPL-282` R-11 (a declared product gate,
supplied as a predicate), `D-IMPL-288`/`D-IMPL-295` (a request-bound operator
parameter), `D-IMPL-313`–`D-IMPL-316` and `D-IMPL-319` (the canonical sibling
pattern), `D-IMPL-331` (`decay_basis: valid-from`), `D-IMPL-340` (the producer
assertion and cross-deployment admission), `CP14-F-22` (this tree's charter).

## What to change first

1. **The obligor.** `run.py`'s `DEMONSTRATION_ANCHOR`, or `LEI=…`. Everything
   else follows from which filer you name.
2. **The instant.** `ASKED_AT=…`. The window is measured against it, and the
   debt ages every column to it.
3. **The tolerance.** `DEBT_TOLERANCE=…` is required by the contract; below the
   assessed debt the spread is withheld with the debt block.
4. **The basis.** `BASIS=latest-restated` lets the latest accession speak for
   every cell; a restated obligor's figures — and its address — move.

To point this at **your own estate**, edit `artifacts/source-vocabulary.yaml`
(the table names) and `backends.yaml` (the environment variables). To spread
different lines, edit `artifacts/spread-lines.yaml`. No Python changes.

## What would fail

Each of these is asserted in `tests/examples/test_cp_03_canonical_output.py` or
`tests/examples/test_cp_03_canonical_cross_deployment.py`, so breaking one is
loud rather than silent.

- **Declare `intent` under `arguments.properties`**, as the specimen did, and
  the SDK refuses the contract at construction — the boot never serves.
- **Drop `decay_basis: valid-from`** from the λ_c rows and every column ages
  from the ingestion instant: `F` reads exactly 1 for a spread whose columns
  are years old.
- **Delete the window comparison** from the product's gate and a spread whose
  freshest filing is a month older than the instant is served.
- **Name the suppression** in a refusal and an obligor the principal may not
  see becomes distinguishable from one that does not exist.
- **Reuse one fabric path across runs** and a subject that resolved to nothing
  is served the previous obligor's spread.
- **Drop the door's producer assertion** and the consumer refuses every
  acquisition `producer-unasserted`; assert a different identity and it refuses
  `producer-mismatch`; the door's claim about itself never authorizes.
- **Modify `examples/cp-03-obligor-financial-spread`** at all. It is frozen
  under `D-IMPL-261`; a test measures it at zero files changed against the
  branch point.
