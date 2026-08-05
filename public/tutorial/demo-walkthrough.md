<!--
  Snippet configuration for every literal include below lives in
  `mkdocs.yml` (pymdownx.snippets `base_path: ["."]`, repo root).
  Nothing in this page pastes code — the doc always shows the exact
  files that run in CI.
-->

# How data folds into context

*A narrated walk through `examples/08-e2e-demo`: three systems of record,
a fraud ring none of them can see, and the exact point in the fabric where
it becomes visible.*

Run it yourself first if you like — one command, deterministic, the same
run CI performs:

```
PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py
```

(or `make example-08`). Everything below is that run, stage by stage.

---

## 1. The problem: three honest databases, one invisible ring

Meridian Bank operates three systems of record, each generated as a real
SQLite database you can open with any client:

| Source | File | What it knows |
| --- | --- | --- |
| Core banking ledger | `core_banking.db` | accounts (`account_number`, `holder_name`, `holder_tax_id`) and transactions |
| Wire/payments log | `wires.db` | wire transfers between *free-text party names* with BICs and addresses |
| Counterparty/KYC registry | `kyc_registry.db` | registered legal entities (`registry_id`, `legal_name`, `tax_id`, `registered_address`) |

Hidden in the noise is a five-member fraud ring moving money in a circle:
M1 → M2 → M3 → M4 → M5 → M1, near-constant amounts, timestamps marching
forward over two weeks. The trap — and the point of the demo — is that
the ring's per-source identifiers are **genuinely disjoint**. The ledger
knows `ACCT-31-8046-1127`; the wire log knows `"Harrowpoint Cnslt Pte"`;
the registry knows `KYC-REG-70441` / `"Harrow Point Consulting Pte.
Ltd."`. No string matches across sources. Each database is internally
consistent and individually useless.

Two pieces of linking evidence exist, and **no single source holds both**:

- the ledger account and the KYC entry share a **tax reference**;
- the wire alias and the KYC entry share a **registered address**.

Joining them requires entity resolution across all three sources — the
L2 layer of the fabric. That layer is the hero of this story.

## 2. The scenario artifact — change this to make your own demo

Everything just described is a *value*, and per the No-Hardcoding Rule
(CLAUDE.md §6.4) values never live in code. The entire synthetic world —
the three source schemas, the ring members and their disjoint aliases,
the circular payments, every noise lexicon, and the determinism pins —
is one versioned definition artifact. The generator (`generator.py`) is a
pure interpreter of it: it holds zero source names, table names, aliases,
or amounts.

This file is the teaching centerpiece. **Change it to make your own
demo** — different members, a longer ring, another domain entirely — and
the same interpreter, the same fabric, and the same agent mechanism run
your story instead. (Any change invalidates the pinned checksums, so
re-pinning is a deliberate, reviewed event — that is the drift alarm
working as designed.)

```yaml
--8<-- "examples/08-e2e-demo/artifacts/scenario.yaml"
```

The interpreter that turns this artifact into three SQLite databases:

```python
--8<-- "examples/08-e2e-demo/generator.py"
```

## 3. Stage 1–2: generate, then prove raw data finds nothing

The run opens with two stages of banners (all console output is
deterministic and byte-compared in CI against
`artifacts/expected_output.txt` by `tests/examples/test_e2e_demo_output.py`
— the full expected transcript is in §8 below).

**Stage 1 — GENERATE** interprets the scenario: 6,870 rows across the
three databases, and every pinned checksum (per-database SHA-256, ring
signature) is checked against the artifact's pins.

**Stage 2 — BASELINE** is the honesty stage. The demo's headline claim —
*an agent solves a problem it could not solve from the raw data alone* —
is executed, not asserted (CONTEXT D-11). The **same** structured-cycle
detection that later finds the ring is run first over the raw per-source
rows, identifiers taken exactly as each source spells them, under the
**same** numeric constraints the governed skill will use (minimum cycle
length, consecutive-amount tolerance, span window — all read from the
skill artifact's dispatch arguments, §6). It examines 905 payment rows
and finds **0** structured cycles:

```
structured cycles found      0
verdict                      nothing to see from raw data alone
```

Why zero? The wire log names the ring's edges — but by alias. Without
resolution, the aliases attribute payments to five parties nobody knows;
the linking evidence (tax reference, registered address) sits unused in
databases the detection can't relate. One detection mechanism, two
passes, one variable changed between them: whether the data has been
folded into context.

## 4. Stage 3: L1 envelopes → L2 entity resolution

Now the fold. Every raw row becomes an L1 `SignalEnvelope` and enters the
graph through the **single writer** — `handle.worker.ingest` is the only
write path in the entire example (CLAUDE.md §10).

How rows map to envelopes, and how envelopes resolve into canonical
entities, is again entirely artifact-declared, across two documents. The
resolution spec carries the deployment's graph vocabulary — entity
classes, identity keys, relationship rules:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/resolution-spec.yaml"
```

The ingest spec carries the L1 mapping, which selects scenario sources
and columns **by mechanism role**, never by name — which is why `run.py`
contains no source vocabulary at all:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/ingest-spec.yaml"
```

Read the two load-bearing rules in the resolution spec closely:

- `identity_keys: [party_tax_ref]` — the ledger account holder and the
  KYC entry mint the **same** canonical `counterparty` URI because both
  envelopes carry the same tax reference. Neither source knows about the
  other; convergence is a property of the identity keys (whitepaper
  §7.3's idempotent upsert with multi-source lineage accumulation).
- `identity_keys: [site_address]` — the wire transfer's beneficiary
  address and the KYC entry's registered address mint the same `site`
  node. That is the **only** evidence tying a wire alias back to a
  registered counterparty, and it becomes a typed-edge chain:
  `transfer —delivered_at→ site ←registered_at— counterparty`.

The banner reports the outcome: 6,870 envelopes in, **1,205 canonical
counterparty nodes** out — 1,200 noise counterparties plus the 5 ring
members, each ring member now a single node carrying evidence from all
three sources. "Disjoint source identifiers converged on shared
evidence" is the whole of L2, in one console line.

Ambiguity, for the record, resolves to *nothing* rather than to a guess:
a display name or alias that maps to two canonicals links neither. The
demo is deterministic and honest in both passes.

## 5. Stage 4: operators → projection → gated product

With the graph assembled, the fabric serves context the governed way —
never by handing anyone the graph. The four canonical operator
categories run as a composed chain (Traversal ∘ Temporal ∘ Policy ∘
Similarity, whitepaper §7.4), a projection shapes the result for the
consuming role, and the typed Context Product passes the three
validation gates before it is served:

```
operators invoked            4
entities served              4458
typed edges served           3270
gates                        empty-operator, lineage equality, TTL - all passed
```

The fabric configuration is artifacts too — one document per artifact
class, with a single manifest naming every one of them and saying which
are put *in force* and which are merely loaded. The manifest is the
document to read first: it is the whole of what this deployment was
permitted to do, enumerated rather than globbed, and it is what `run.py`
hands to one `load_and_boot` call:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/manifest.yaml"
```

The policy bundle it puts in force, stamped onto every claim at assembly
and carried into replay dimension 2:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/policy-bundle.yaml"
```

And the per-observation-type half-life table that later shows up as a
freshness number in Stage 5, with the debt profile whose risk
sensitivity scales it:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/half-life-table.yaml"
```

```yaml
--8<-- "examples/08-e2e-demo/artifacts/debt-profile.yaml"
```

## 6. Stage 5: the agent and its governed skill find the ring

The consumer is not a script poking at the product — it is a declared,
versioned agent (`payment-ring-analytics@1.0.0`), built by the Agent
Factory from the `AnalyticsInsightsAgent` archetype, with its
specialization (context contract, policy regime, instruction binding)
fixed in a definition artifact:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/agent-definition.yaml"
```

Capability arrives through the second channel — **skilling** (CLAUDE.md
§6.2). The cycle-detection skill is a catalog entry; the grant is
admitted through the governance check against the agent's policy
envelope; and the dispatch arguments carry **every** graph-vocabulary
name and threshold the callable interprets. The callable in `run.py` is
generic walk-a-graph mechanism; the artifact tells it what a
counterparty is, what a transfer is, which edges link them, and how
tight the ring's structure must be. The catalog entry declares the
argument schema:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/skill-catalog-entry.yaml"
```

The grant that binds it, and the dispatch values the callable interprets:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/skill-dispatch.yaml"
```

Invoked over the typed Context Product — the same detection, the same
parameters as Stage 2 — the skill walks the resolved payment network
through the typed-edge chain and finds **exactly one** structured cycle:

```
structured cycles found      1
ring size                    5
ring members                 Bluegate Trading Company S.A.|Harrow Point Consulting Pte. Ltd.|Kestrel Marine Supply GmbH|Northquay Advisory Limited|Palmera Logistics S.L.
```

The five legal names are the KYC registry's — identities the wire log
never contained. Both outcomes (baseline 0, governed 1, these exact
members) are pinned in artifacts and asserted every CI run.

Note what the structure buys: the noise wire graph *does* contain
topological cycles among name-level parties. Bare cycle-finding would
cry wolf. The ring separates from the noise because of the structural
constraints the artifact declares — near-constant consecutive amounts,
strictly increasing timestamps, a bounded span — applied to *resolved*
parties. The parameters are values; move them in `skills.yaml` and watch
the boundary move.

Note which of these documents the deployment manifest names and which it
does not. `ccf.agent-definition`, `ccf.prompt-artifact` and
`ccf.skill-catalog-entry` are **author-versioned**: they register through
`register_versioned`, which holds the author's declared `artifact_version`
against the document's content identity. `load_and_boot` registers through
`register_typed`, which does not run that check — so those three classes are
deliberately not manifest-addressable and `run.py` registers them itself.
They carry real `$schema` headers all the same.

## 7. Stage 6: replay, and why you can trust any of this

The decision does not evaporate when the process exits. Stage 6 records
and serves the five-dimension Decision Replay record (whitepaper
§7.10.1): fabric snapshot, policy bindings, model version, perspective
conditioning, and generation path — extended with the agent's version
and the **skill-set in force** at decision time (its hash prints in the
banner). Months later, the question "which agent, which configuration,
which granted skills, over exactly which context found this ring?" is
answerable from the record alone.

Determinism is pinned three ways (CONTEXT D-08): the documented seed and
per-database checksums in the scenario artifact; the pinned baseline and
governed detection outcomes; and the full staged narration byte-compared
against the committed transcript. Two consecutive runs are byte-identical
on stdout.

## 8. The expected transcript

This is the committed file the run's stdout must equal, byte for byte —
the same banners you saw quoted above:

```
--8<-- "examples/08-e2e-demo/artifacts/expected_output.txt"
```

And the thin, generic driver that produced it — six labeled stages of
loading and mapping, opening with a single `load_and_boot` call over the
manifest above; deleting the artifacts would leave it nothing to run
(§6.4). It checks nothing itself: the driver returns its state and
`tests/examples/test_e2e_demo_output.py` holds every assertion,
including the byte-comparison, where a test runner can fail a build:

```python
--8<-- "examples/08-e2e-demo/run.py"
```

## 9. Running it yourself

```
PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py
```

or `make example-08`; it also runs inside `make examples` and therefore
`make ci`, deterministically, on every commit. A full run takes roughly
40 seconds, dominated by 6,870 per-row SQLite ingests.

Optionally, `--live` adds a narration-only step (never in always-on CI):
the prompt artifact below is rendered against the deterministic
detection outcome and an Ollama-style local model writes an
investigation summary. Detection itself is identical in both modes —
the model narrates a result the fabric already proved:

```yaml
--8<-- "examples/08-e2e-demo/artifacts/prompt-artifact.yaml"
```

**Where to go next:** open `examples/08-e2e-demo/artifacts/scenario.yaml`
and change something — a member, an amount, the tolerance. The pins will
fail loudly, you will re-pin deliberately, and the demo will be yours.
