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

`run.py` is the **call spine** and nothing else: it asserts nothing and
prints nothing. Exit code 0 means the spine executed.

Its assertions live in `tests/examples/test_quickstart_output.py`. The
split is deliberate and it matters when you read `make ci`:

```sh
make examples                        # proves the spine RUNS
pytest tests/examples/               # proves it is CORRECT
```

Both are part of `make ci`, so nothing is unguarded — but a green
`make example-00` on its own is not a correctness result, and the
invariants in the "What would fail" table below are checked by the test
module, not by the example.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `pytest tests/examples/test_quickstart_output.py`, review
> the failure, then deliberately edit `artifacts/expected.yaml` to match
> what you reviewed — regeneration is a reviewed event, landed in the same
> commit as the enrichment, with the commit body summarizing what changed
> in the output and why. No `make regen-*` targets exist, and none will be
> added.

## The story

A payments analyst at a fictional German bank needs decision context on a
corporate customer. The artifacts declare everything the fabric needs; the
code only interprets them.

0. **Name what is in force.** `artifacts/manifest.yaml` enumerates every
   other document — its path, its Control Plane key, its artifact class,
   and its `role`. `role: register` puts an artifact into the Control
   Plane and into the pinned set that is replay dimension 2; `role: load`
   parses and validates it identically and hands it back, but never puts
   it in force. Nothing is globbed: the set in force must not be a
   function of what happens to be in a directory.
1. **Declare the vocabulary.** `artifacts/resolution-spec.yaml` names four
   entity classes — `customer`, `account`, `mandate`, `branch` — with the payload
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
3. **Constrain the run.** The **Control Plane** side of the split — the
   Control Plane declares what the fabric may do (versioned config,
   policy, artifacts — also the audit plane); the Data Plane executes
   within those constraints (whitepaper §7.8). One document per class:
   `policy-bundle.yaml`, the four `operator-parameters-*.yaml` sets,
   `product-class.yaml`, `product-governance.yaml` (the TTL ceiling and
   the product's own lifetime, two separately authored numbers so Gate 3
   has something to compare), `perspective.yaml`, and `decision.yaml` for
   the instants — explicit data, never clock reads, which is what makes
   the run replayable.
4. **Project and serve.** The one piece of deployment *code* is
   `QuickstartPlan` in `run.py` — the **Projection (Π)** — the
   role-conditioned transformation that turns graph state into the view a
   given consumer is entitled to see (whitepaper §7.5). The engine runs
   the operator chain, the projection interprets it, the three L6 gates
   check the candidate, and the served view is asserted — in
   `tests/examples/test_quickstart_output.py` — against
   `artifacts/expected.yaml`:

   ```yaml
   declaration:
     entity_classes: [customer, account, branch]
     relationship_types: [holds, domiciled_at]
     entity_count: 3
   ```

   (The restricted mandate and the off-query deposit account are exactly
   what is *not* in that list.)

   The projection's declared operator set comes from
   `product-class.yaml`'s `required_operator_keys`, never from the
   operator registry's own keys. That independence is what leaves the
   lineage gate a real comparison rather than a value against itself.
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
6. **Decay is configuration.** `artifacts/half-life-table.yaml` and
   `artifacts/debt-profile.yaml` declare the
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

**One artifact class, one document.** A file is not an artifact: each class
has its own contract and its own version lane, so each gets its own
closed-world document with a `$schema` header naming the class that
validates it.

| Artifact | Class | Role | What it declares |
| --- | --- | --- | --- |
| `manifest.yaml` | `ccf.deployment-manifest` | — | Every document below, by path, key, class and role; the tenant and the backend kind |
| `resolution-spec.yaml` | `ccf.resolution-spec` | register | Entity classes, identity keys, relationship rules |
| `policy-bundle.yaml` | *deployment-authored* | register | The policy regime in force |
| `half-life-table.yaml` | `ccf.half-life-table` | register | λ_c per observation type |
| `debt-profile.yaml` | `ccf.debt-profile` | register | The D_c bands and risk sensitivity |
| `operator-parameters-traversal.yaml` | `ccf.operator-parameters.traversal` | register | Seed classes, edge types, depth bound |
| `operator-parameters-temporal.yaml` | `ccf.operator-parameters.temporal` | register | Which bitemporal axis the boundary binds |
| `operator-parameters-policy.yaml` | `ccf.operator-parameters.policy` | register | Classification attribute per class; permitted classifications |
| `operator-parameters-similarity.yaml` | `ccf.operator-parameters.similarity` | register | Query, threshold, ranked classes, corpus attribute per class |
| `perspective.yaml` | `ccf.perspective` | register | The Π role-conditioning |
| `product-class.yaml` | `ccf.product-class` | register | Schema identity, TTL anchor, assembly mode, MAX_TTL key, `required_operator_keys` |
| `product-governance.yaml` | *deployment-authored* | register | TTL ceiling, product lifetime, corpus index version, plan id, replay class |
| `events.yaml` | `ccf.signal-batch` | **load** | The L1 signal stream. Role fixed by the SDK — registering raw events would put them in replay dimension 2 |
| `decision.yaml` | *deployment-authored* | **load** | This run's instants and the freshness demonstration |
| `expected.yaml` | *deployment-authored* | **load** | What the served product should contain |

Each document carries `[ADAPT]` / `[MECHANISM]` annotations in its own
header comment, naming exactly which of its keys are yours to rename and
which the factory interprets.

Documents of a class the SDK does not own use the open `DeclaredArtifact`
envelope: the SDK fixes `semver`, `class_id` and canonical
serializability, and everything under `declaration:` is yours. Their
`$schema` header points at the envelope, because the SDK never invents a
schema for a namespace that is not its own.

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

1. `artifacts/resolution-spec.yaml` — rename the entity classes under
   `entity_rules` (`customer`, `account`, `mandate`, `branch`) and their
   `match_key`/`identity_keys`/`attribute_keys` to your source systems'
   vocabulary; rewrite `relationship_rules` for your edges.
2. `artifacts/events.yaml` — replace the `raw_payload:` blocks with your
   systems' payloads, keeping the envelope keys.
3. `artifacts/operator-parameters-*.yaml` — retune all four, especially
   `similarity.query`, `traversal.relationship_types`, and the two
   per-class attribute maps (`classification_attribute_by_class` and
   `similarity_corpus_attribute_by_class`) which now live with the
   operator that reads them.
4. `artifacts/policy-bundle.yaml` and `artifacts/product-class.yaml` —
   set your regime and rename `schema_name`. If your projection needs a
   different operator set, change `required_operator_keys` here; do not
   change it in `run.py`.
5. `artifacts/half-life-table.yaml` — replace the `entries:` rows with
   your observation types and calibrations (decimals stay quoted).
6. `artifacts/manifest.yaml` — update `tenant_id` and any `class_id` you
   renamed. Every document must be named here; nothing is discovered.
7. `artifacts/expected.yaml` — last, after one reviewed run.

On the next run expect: your entity classes in the served payload, your
relationship types surviving traversal, and a failing
`pytest tests/examples/test_quickstart_output.py` until you complete step
7 — that failure is the workflow, not a bug.

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
| λ_c is configuration, never code (INV-CH7-58) | a half-life would exist somewhere other than `artifacts/half-life-table.yaml` |
| declared and resolved operator sets stay independent (INV-CH7-47) | the projection would read the operator registry's own keys, and the lineage gate would compare a value against itself |

Every row above is checked by `tests/examples/test_quickstart_output.py`,
not by `run.py`.
