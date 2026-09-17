# Covenant Cross-Reference (canonical) — rung 13 on the paved road

`credit-risk.covenant-cross-reference` @ `1.0.0` · Tier 3 · PostgreSQL `ccf_v2` +
Fluree `fibo-v2` + MongoDB `fibo_v2` · reads the curated `.76` estate, writes nothing ·
`CP-SPEC-013C`

**The same product as the frozen rung-13 specimen, served by a different producer
through the SDK's standard door — and with the evidence Π serves recorded in the graph
instead of carried in from the side.**

## What this demonstrates

**Producer substitution on the paved road.** `examples/cp-13-covenant-cross-reference`
is frozen (`D-IMPL-261`), still serves on the low road, and ships no door — which is why
CP-14's covenant slot could not reach it (`CP14-F-26`). This tree serves the same class
from its own tenant and its own door, and the lane it serves was **decided by
measurement**: at the specimen's demonstration instant, for the four evidence sources
its question selects, the successor's canonical payload hashes to the specimen's, field
for field (`CXRC-G14`). So it is `1.0.0` — a second producer of one product — and what
differs is exactly what a sibling under its own tenant cannot share: `tenant_id`,
`plan_id`, the policy-bundle version. Payload equivalence is not contract identity.

**The evidence IS the graph.** The specimen handed its Π the whole acquisition result
through a closure — every chain, every citation, the policy envelope, the retrieval, the
governing register — and measured two debt factors off that same object. The paved road
hands Π the effective request and nothing from the side, so here each admitted anchor
node carries its chain, the envelope and the governing register as claims, and both Π and
the debt reading read the governed view (`CXRC-G15`). A source the caller may not read
is not in the view, and it counts for nothing — in the payload and in the debt.

**The entitlement principal is the perspective's role** (`CXRC-G22`). The register keys
on the roles the specimen passed as a per-call argument; on the road the acquisition
checks `perspective.role`. The door serves every caller as the deployment's declared
credit officer; a local caller states a perspective; nothing names itself.

**What the road removed.** No registry, boot call, effective-request re-derivation,
ingest loop, fourteen-keyword builder call, store, record readback, or `backends.yaml`.
Two documents, two regions, four callables, and a 27-line door launcher where the
specimen had none.

What the product shows, unchanged from the specimen: every served citation re-hashed
against the passage `ex:evidencedBy` names; a point anchor and an unverifiable span
reported as debt with a reason, never quoted; the retrieval bounded before it ranks; the
governing text chosen by `governs_from`; `ex:governedBy` absent and not invented; an
unembedded memorandum `not-evaluable` rather than "no result".

## Run it

```
export CCF_CP_13C_POSTGRES_DSN=postgresql://...   CCF_CP_13C_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_13C_FLUREE_URL=http://<host>:8090    CCF_CP_13C_FLUREE_LEDGER=fibo-v2
export CCF_CP_13C_MONGO_URI=mongodb://...          CCF_CP_13C_MONGO_DB=fibo_v2
make -s example-cp-13-canonical
make -s example-cp-13-canonical ROLE=--role=control-room CORPUS_SCOPE=--corpus-scope=filed-and-internal
make -s example-cp-13-canonical ROLE=--role=relationship-manager CORPUS_SCOPE=--corpus-scope=filed-and-internal   # refused, never narrowed
make -s example-cp-13-canonical DEBT_TOLERANCE=--debt-tolerance=0.10                                             # withheld: D_c above tolerance
.venv/bin/python examples/cp-13-canonical-covenant-cross-reference/run.py --door
```

The default question is `artifacts/question.yaml`: four evidence sources chosen off the
ledger, intent `compliance-test`, `as_of` 2026-09-13, the class defaults for
`corpus_scope` and `resolve_depth`. The v2 namespaces are not in `ccf_dataprep/.env`,
which names v1.

## The story

### 0. Two regions, and the SDK owns the rest

`produce.py` binds `acquire`, `project`, `assess` and `gate` to the two documents in one
`open_product` call and asks one governed question. The door is `open_door` over the
same opened product, reached by `run.py --door`.

### 1. The evidence moved into the graph, and replay can now reconstruct it

`deployment.envelopes` puts `source_json`, `envelope_json`, `governing_json` and
`seeded_on` on each anchor node; `resolution.entity_rules` admits them; `projection.py`
reads them off the admitted anchors in the view and `deployment.assess` reads `C` and
`S` off the same claims. A changed chain in the view changes the served citations and
the debt factor in step, and Π's constructor takes no estate, so there is no side channel
to obtain the old evidence from. Replay rebuilds the product — and its debt factors —
from the recorded snapshot with no acquisition object alive (`CXRC-G25`).

### 2. The lane is a measurement, not a claim

The four demonstration sources at `2026-09-13T00:00:00+00:00`: full canonical payload
hashes equal, zero field-level differences, the same debt factors (`F` 1, `C` 0.1905,
`S` 1), the same expiry. The frozen specimen is the control, run in-process by the same
test against the same estate.

### 3. Two governed axes the specimen left open

`intent` is judged on the declared discovery set (`CXRC-G21`; the specimen accepts any
intent), and a question that admits no evidence node is refused by the declared lineage
obligation with a record (`CXRC-G23`; the specimen raised `ValueError` before any read).
Both are deliberate differences, recorded in `CP-SPEC-013C` §G.3 and in `FINDINGS.md`,
never averaged into the lane comparison. Two conditions still RAISE exactly as the
specimen raises them, because they are the walk's own contract: an unknown evidence
node and a role with no entitlement row.

## Artifact-by-artifact

| file | role |
|---|---|
| `ccf_config.yaml` | the product, its request contract, operators, resolution rules, λ_c table, D_c profile, policy, perspective, discovery set, replay binding, TTL and door — one document, one authority per value |
| `ccf_environment.yaml` | the NAMES the three sources and the door's credential are read from; no value |
| `artifacts/source-vocabulary.yaml` | every IRI, collection, field and table the three legs read |
| `artifacts/question.yaml` | the demonstration question `run.py` asks by default |
| `artifacts/gates.yaml` | the twenty-five declared product gates and the tests that claim them |
| `spec/CP-SPEC-013C_…md` | the successor's specification, committed before its implementation |
| `produce.py` | the spine: `boot` and `answer` |
| `deployment.py` | `acquire` (the principal off the perspective), the envelopes (edges first, evidence on the anchors), `assess` off the view, the gate |
| `acquisition.py` | the three legs, unchanged from the specimen except that the road hands it its settings |
| `projection.py` | Π, reading the view; the claim builders the deployment ingests with |
| `server/serve.py` | the standard door launcher, stdio or loopback |
| `run.py` | presentation only |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.3 (single writer, thin edges first), §7.4 (policy before traversal, two
registered operators), §7.5 (Π reads the view), §7.6 (the three gates plus the product's
own), §7.7 (`D_c = 1 − F·C·S`, evidence debt off the view), §7.10 (five-dimension
replay; passage-level lineage; a refused determination reconstructs through
`D-IMPL-344`). CLAUDE.md §6.4 (no value in code), §7.1 (the standard egress door), §9
(the estate is evidence), §10 (L2 the only writer). `D-IMPL-340` (cross-deployment
acquisition), `D-IMPL-343` (the paved road), `D-IMPL-344` (refusal reconstruction).

## What to change first

The two documents. A different estate is six names in `ccf_environment.yaml`; a
different corpus policy or λ_c is `ccf_config.yaml`; a different anchor vocabulary is
`artifacts/source-vocabulary.yaml` and the `traversal.typed-neighborhood` declaration.
`projection.py` and `acquisition.py` are the domain and are yours to change; nothing in
them is SDK mechanism.

## What would fail

Serve a citation without re-hashing it (`CXRC-G01`); quote a point anchor (`G02`);
post-filter the retrieval (`G03`); narrow an unentitled scope (`G04`); select the
governing text by filing date (`G05`); hide the seed (`G06`); answer an unknown source
with an empty chain (`G07`); invent a governing edge (`G09`); count an unembedded
memorandum as a non-hit (`G10`); hand Π the acquisition result through a closure or read
`C` off a constant instead of the view (`G15`); compose the resolver beside the opened
product (`G16`); edit one specimen file or reuse its tenant (`G17`); take the producer
identity from the answer rather than the registration (`G19`); drop `discovery.intents`
(`G21`); read the principal off a request parameter (`G22`); serve an empty
cross-reference (`G23`); mint the substrate once per opened product (`G24`); rehydrate
the product from the served outcome instead of the snapshot (`G25`).
