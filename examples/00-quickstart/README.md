# examples/00-quickstart — the smallest possible fabric, "Hello, Context Product"

## What this demonstrates

The whole fabric, end to end in one process, with no API key and no model:
register an ontology, ingest a handful of events, assemble, run the
four-category operator chain, project, pass the three delivery gates,
record the decision, and serve one **Context Product** — a typed,
validated, replay-ready unit of decision context the fabric derives and
serves — a contract, not a stored record (whitepaper §6.3 (specification),
§7.6 (delivery)). The events land in the **Context Graph** — the fabric's
typed state `G(E, R, T, P, Π, L)` — entities, relationships, time, policy,
projection, and lineage as one governed graph (whitepaper §5.2
(definition), §7.3 (mechanism)) — by way of the **L1–L6 layers** — the
fabric's six layers: L1 signal ingestion → L2 assembly (the only writer) →
L3 graph → L4 operators → L5 projection → L6 product delivery (whitepaper
§7.1).

It also demonstrates the **No-Hardcoding Rule** — no prompts, agent
definitions, thresholds, or routing values in code — code is interpreters
and factories; everything specific lives in versioned artifacts, CI-lint
enforced (CLAUDE.md §6.4 — SDK extension): `run.py` holds no entity class,
threshold, query string, TTL, half-life or expected result. Every later
example builds on this shape.

## Run it

```sh
make example-00
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/00-quickstart/run.py
```

The driver is an asserted program: exit code 0 means every invariant in
the "What would fail" table below held; any failure exits nonzero, and CI
treats nonzero as red.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-00`, review the assertion output, then
> deliberately edit the `expected:` block in `artifacts/controlplane.yaml`
> to match what you reviewed — regeneration is a reviewed event, landed in
> the same commit as the enrichment, with the commit body summarizing what
> changed in the output and why. No `make regen-*` targets exist, and none
> will be added.

## The story

A payments analyst at a fictional German bank needs decision context on a
corporate customer. The artifacts declare everything the fabric needs; the
code only interprets them.

1. **Declare the vocabulary.** `artifacts/ontology.yaml` names four entity
   classes — `customer`, `account`, `mandate`, `branch` — with the payload
   keys that mint each one's identity, and three typed relationships
   (`holds`, `authorizes`, `domiciled_at`). The same customer arriving
   from two source systems converges on one node because both mint the
   same identity URI.
2. **Ingest the signal.** `artifacts/events.yaml` carries five envelopes
   built so every layer has real work: `ev-100`/`ev-101` assert the same
   customer from two systems (lineage accumulates by set-union, no second
   node); `ev-102` adds an off-query deposit account the similarity
   **Context Operators** — typed, composable, read-only functions over the
   graph in four categories — Traversal, Temporal, Policy, Similarity
   (whitepaper §7.4) — must rank out; `ev-103` carries a *restricted*
   mandate the policy operator must substitute away, together with the
   edge that would leak its existence by absence; `ev-104` adds the branch
   the surviving account is domiciled at, giving the depth-bounded
   traversal a genuine second hop.
3. **Constrain the run.** `artifacts/controlplane.yaml` is the
   **Control Plane** side of the split — the Control Plane declares what
   the fabric may do (versioned config, policy, artifacts — also the audit
   plane); the Data Plane executes within those constraints (whitepaper
   §7.8). It pins the policy bundle, all four operator parameter sets (see
   key `operator_parameters`), the product class and its TTL ceiling, the
   perspective, and the decision instants — explicit data, never clock
   reads, which is what makes the run replayable.
4. **Project and serve.** The one piece of deployment *code* is
   `QuickstartPlan` in `run.py` — the **Projection (Π)** — the
   role-conditioned transformation that turns graph state into the view a
   given consumer is entitled to see (whitepaper §7.5). The engine runs
   the operator chain, the projection interprets it, the three L6 gates
   check the candidate, and the served view is asserted against the
   `expected:` block the deployment authored:

   ```yaml
   expected:
     entity_classes: [customer, account, branch]
     relationship_types: [holds, domiciled_at]
     entity_count: 3
   ```

   (The restricted mandate and the off-query deposit account are exactly
   what is *not* in that list.)
5. **Record before delivery.** A five-dimension **Decision Replay
   record** — the record (fabric snapshot, policy bindings, model version,
   perspective conditioning, generation path) that lets a decision be
   reproduced exactly (whitepaper §7.10 ("The Five-Dimension Replay
   Record")) — is written to the file-backed **ArtifactStore** — the
   Protocol-based persistence surface for CCF artifacts (snapshots,
   products at rest, replay records, Control Plane bundles), with
   file-backed and MCP-backed reference implementations (CLAUDE.md §7.4 —
   SDK extension) — before the product is served, and read back to prove
   it round-trips.
6. **Decay is configuration.** `artifacts/halflife.yaml` declares the
   **Context Half-life (λ_c)** — a per-observation-type decay rate
   declaring how fast context goes stale — a Control Plane value, never
   code (whitepaper §7.7) — and the **Context Debt (D_c)** — the
   quantified shortfall when freshness or completeness drops below
   threshold; elevated debt gates Forced-LLM and Fail-Closed behavior
   (whitepaper §7.7 ("`D_c` Formulas")) — profile. The driver evaluates
   one declared observation's freshness at the decision instant.

The scenario got richer — one more entity class, one more relationship
type, one more event, one more half-life row — without touching `run.py`:
that is the No-Hardcoding boundary doing its job.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/ontology.yaml` | Entity classes, identity keys, relationship rules, classification and similarity-corpus attributes | `[ADAPT]`: class names, match keys, attribute names, relationship types. `[MECHANISM]`: `entity_rules`, `match_key`, `identity_keys`, `relationship_rules`, `classification_attribute_by_class`, `similarity_corpus_attribute_by_class` |
| `artifacts/events.yaml` | The L1 signal stream, in the source systems' vocabulary | `[ADAPT]`: everything under `payload:`, source system ids. `[MECHANISM]`: `envelope_id`, `source_system_id`, `ingestion_timestamp`, `observed_time`, `payload` |
| `artifacts/controlplane.yaml` | Policy bundle, operator parameters, product class, MAX_TTL, perspective, decision instants, `expected:` block | `[ADAPT]`: key names, bundle values, parameter values, schema name, expected values. `[MECHANISM]`: section names `keys`, `policy_bundle`, `operator_parameters`, `product_class`, `perspective`, `decision`, `expected` and their sub-keys |
| `artifacts/halflife.yaml` | λ_c calibrations per observation type and the D_c debt profile | `[ADAPT]`: observation-type names and every calibrated value. `[MECHANISM]`: `half_life_seconds`, `decay_driver`, `supersession_event`, `risk_sensitivity`, `forced_llm_threshold`, `fail_closed_threshold` |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §5.2 / §7.3 — the Context Graph and identity-key entity
  resolution
- whitepaper §7.4 — the four-category operator algebra
- whitepaper §7.5 — projection Π
- whitepaper §7.6 — the Context Product Contract and its three gates
- whitepaper §7.7 — context half-life λ_c and the debt profile
- whitepaper §7.10 — the five-dimension Decision Replay record
- CLAUDE.md §6.4 — the No-Hardcoding Rule (SDK extension)
- CLAUDE.md §7.4 — the ArtifactStore (SDK extension)
- CLAUDE.md §9, §10 — examples discipline; L1–L6 layering and the
  single-writer invariant

## What to change first

`artifacts/` **is** the specialization surface. To move this example to
your domain:

1. `artifacts/ontology.yaml` — rename the entity classes under
   `entity_rules` (`customer`, `account`, `mandate`, `branch`) and their
   `match_key`/`identity_keys`/`attribute_keys` to your source systems'
   vocabulary; rewrite `relationship_rules` for your edges; point
   `classification_attribute_by_class` and
   `similarity_corpus_attribute_by_class` at your attribute names.
2. `artifacts/events.yaml` — replace the `payload:` blocks with your
   systems' payloads, keeping the envelope keys.
3. `artifacts/controlplane.yaml` — set your `policy_bundle`, retune every
   set under `operator_parameters` (especially `similarity.query` and
   `traversal.relationship_types`), rename `product_class.schema_name`,
   and then — after one reviewed run — rewrite the `expected:` block.
4. `artifacts/halflife.yaml` — replace the `entries:` rows with your
   observation types and calibrations (decimals stay quoted).

On the next run expect: your entity classes in the served payload, your
relationship types surviving traversal, and an assertion failure on
`expected:` until you complete the reviewed-edit step above — that failure
is the workflow, not a bug.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| single-writer (INV-CH7-10) | there is no writer to obtain; the fabric is booted through the real composition root |
| idempotent upsert + lineage set-union (INV-CH7-16/17) | the same customer arriving from `core-banking` and `crm` would create a second node, or overwrite instead of accumulating lineage |
| policy substitution (INV-CH7-26) | the restricted mandate — or the `authorizes` edge that would leak its existence by absence — would survive |
| similarity ranking (INV-CH7-27) | the off-query deposit account would survive |
| bounded traversal (INV-CH7-24) | the walk would reach past its typed, depth-bounded neighborhood — the branch is admitted only because `domiciled_at` is declared and depth 2 covers it |
| the three gates (INV-CH7-46/47/48) | an empty-operator, forged-lineage or over-TTL product would become servable |
| lineage strict equality | the product's `operators_invoked` would diverge from what the engine resolved as having run |
| replay before delivery (INV-CH7-79) | a product would be served with no five-dimension record in the store |
| λ_c is configuration, never code (INV-CH7-58) | a half-life would exist somewhere other than `artifacts/halflife.yaml` |
