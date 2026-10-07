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

### The expiry runs from the filing (since `D-IMPL-341`)

The class declares `ttl_anchor: from_entity_freshness`, and since `D-IMPL-341`
(validation pass 2026-09-18) the governed path computes it: the served
`expires_at` is the freshest filing date the admitted view carries — the
`spread_period` row's clock in `ccf_config.yaml` — plus the declared 30-day
window, and the contract records that instant as `ttl_anchor_at`. Measured on
the demonstration obligor at the CP-14 instant: anchor `2026-08-10`, expiry
`2026-09-09T00:00Z`, where before 341 the same question carried
`2026-10-07T12:00Z` (`CP03C-F-01`, closed; `FINDINGS.md`). An expired spread
is refused by the SDK's own TTL gate — `ttl-refusal` / `ttl-bounds` — before
the product's declared gate runs; that gate keeps its no-obligor half and now
cross-checks the payload's anchor member against the window the contract
carries. An empty admitted view — an obligor the estate does not hold, or one
the principal may not see — is refused `ttl-anchor-refusal` /
`ttl-anchor-unresolvable` for the same reason: with no filing there is no
instant to anchor on, and the two cases stay byte-identical (`OFC-G08`).

Plainly: **the advertised `expires_at` is now the filing window, and a copy
you were served is exactly as current as the filing it rests on.**

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

# The door on a loopback HTTP port for a harness — it advertises its OWN bound address, so
# no URL variable is needed; the bearer credential is minted per boot unless you set it.
PYTHONPATH=src:runtime:examples/cp-03-canonical-obligor-financial-spread \
  .venv/bin/python examples/cp-03-canonical-obligor-financial-spread/run.py --door

# The door on stdio, for an MCP client that spawns it. The two OAuth addresses are
# deployment environment (`ccf_environment.yaml` names the variables; no URL is configuration):
export CCF_CP_03C_DOOR_ISSUER_URL=https://issuer.example      CCF_CP_03C_DOOR_RESOURCE_URL=https://door.example/mcp
PYTHONPATH=src:runtime .venv/bin/python examples/cp-03-canonical-obligor-financial-spread/server/serve.py
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
else's figures. On the paved road (`D-IMPL-343`) the per-question fabric is the
SDK's to mint: `ccf_environment.yaml` names the substrate's setting, prefix and
suffix, `open_product` mints a fresh path under the caller's scratch for EVERY
question, and Π serves the subject's claims and no other's, so a view holding a
second obligor cannot be served as this one's. Nothing in this tree remembers
a uuid.

### The paved road (`D-IMPL-343`)

This tree is the first executable proof of the paved road: it was re-expressed
IN PLACE from the canonical `boot / acquire / govern` shape with its domain
code, its calculations, its projection, its debt rule, its class and lane, its
declared gate and its twenty-seven gates unchanged — and the demonstration
spread's **content address and replay record are byte-identical** before and
after (`122e0a7b…` / `b3d1c7b1…`, measured at the CP-14 instant). What changed
is who owns the plumbing:

| before | after |
|---|---|
| `produce.py` 99 code lines: a registry, a boot, an effective-request re-derivation, an ingest loop, a fifteen-keyword builder call, a store, a record readback | `produce.py` ≈ 30: a named `plan_factory`, ONE `open_product(...)` call binding three verbs, ONE `opened.answer(...)` |
| `server/serve.py` 243 code lines: a second registry, a hand-built entitlement policy, a token file, two recorders over a second store, a hand-built `class-mismatch` envelope, wire re-typing, the builder call, the stdio block, the loopback body | `server/serve.py` ≈ 20: `door = open_door(opened)`, then `door.serve_stdio(identity=AuthenticatedUser(ambient_stdio_identity(credential=door.credential, principal_id=door.principal_id, scope=door.scope, tenant=door.tenant_id)))` / `open_door(opened).serve_loopback(...)` — since `D-IMPL-361` the stdio door composes no identity of its own, so `serve.py` composes it from the door's four fields (it was ≈ 12 lines with a bare `serve_stdio()` before that change) |
| four documents (`ccf_config.yaml`, `backends.yaml`, `server/door.yaml`, `artifacts/ttl.yaml`); six values stated in two places | two documents (`ccf_config.yaml`, `ccf_environment.yaml`); zero values stated twice — a principal, role, URL or credential under `door:` is refused by name |
| the effective request derived twice, with two postures | once, by the resolver, handed to `acquire` through the declared seam |
| two replay stores, three refusal recorders per door process | one store, one recorder, shared by the spine and the door |

What the developer still writes is exactly the ruled split: `acquisition.py`
(the SELECTs), `projection.py` (Π), `deployment.py` (the envelopes, the debt
rule, the gate predicate — and now two ≈ 8-line adapters, `acquire` and
`assess`, that hand those to the SDK's contexts), and the two documents.

## Artifact-by-artifact

| file | what it is |
|---|---|
| `ccf_config.yaml` | the single Control Plane document — every section this deployment puts in force, including the discovery intents, the request binding for the grant, and the declared product gate |
| `ccf_environment.yaml` | the deployment's ENVIRONMENT: the per-question substrate, the source store's variable **names** and remedies, the door's credential and address names. No host, port, schema, credential or URL — a Control Plane value written here is refused by name |
| `artifacts/source-vocabulary.yaml` | the store's own table names and the two fiscal markers |
| `artifacts/spread-lines.yaml` | the tag map, the ratio definitions with their `??` fallbacks, the (empty) adjustments — the specimen's declaration, byte for byte |
| `artifacts/restatement.yaml` | the fact identity key and the materiality threshold — the specimen's declaration, byte for byte |
| `artifacts/gates.yaml` | the twenty-seven declared gates and the tests that claim them |
| `acquisition.py` | the three `SELECT`s and the arithmetic interpreter. **Imports no `ccf` at all** |
| `deployment.py` | this deployment's vocabulary, the envelopes, the debt, the product's own gate |
| `projection.py` | Π — the payload, read off the view and scoped to the subject |
| `produce.py` | **the fabric's half.** Two regions: `boot` (one `open_product` call binding the three verbs) and `answer` (one governed question) |
| `run.py` | presentation. The only module that prints |
| `server/serve.py` | the standard MCP egress door, about twenty lines over `open_door`; on stdio it composes the ambient identity from the door's own fields and passes it to `serve_stdio(identity=...)`, because the door no longer fabricates one (`D-IMPL-361`, `EX-03`/`EX-04`); the identity it asserts and the prose it advertises are `ccf_config.yaml`'s `door:` section; `run.py --door` boots it on a loopback port for a harness |
| `spec/CP-SPEC-003C_…` | this tree's own specification; §G.1 approves every gate |
| `FINDINGS.md` | what authoring this against the current SDK surface exposed |

`produce.py` contains **no domain vocabulary at all**. Delete `ccf_config.yaml`
and nothing in `deployment.py` has anything left to interpret.

### What is deliberately absent

No `gate` region, no `record` region, no `serve` region, and no call to
`run_gates`, `build_replay_record` or `serve` anywhere in this tree — and, on
the paved road, no `build_governed_resolver`, no `ReferencePolicyConstraintResolver`
and no `ProductRequestViolation` either: the structural classifier reads this
tree as `paved`, and a tree that composed the resolver beside `open_product`
would be refused `double-spined` by name. The
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
(the table names) and `ccf_environment.yaml` (the environment variable names).
To spread different lines, edit `artifacts/spread-lines.yaml`. No Python
changes.

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
