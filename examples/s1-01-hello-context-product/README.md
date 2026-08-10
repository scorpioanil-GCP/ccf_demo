# examples/s1-01-hello-context-product — "Hello, Context Product", and where the fabric ends

## What this demonstrates

The whole fabric, end to end in one process, with no API key, no model and
**no agent anywhere in it**: boot on a manifest, ingest a handful of L1
envelopes, build the four-category operator chain, project, pass the three
delivery gates, record the decision across five dimensions, and serve one
typed **Context Product**.

It answers a question a vector store over chunked documents structurally
cannot: *"Who ultimately owns Acme Corporation?"* Jane Doe holds 12.0%
directly and 60.0% of a holding company that itself holds 30.0%. Her real
interest is 30.0%, it crosses the regime's 25.0% threshold, and **no
document in any source system states that number**. It is a sum over
ownership paths, which is what a graph is a substrate for.

**The thing to look at first is the file split.** `spine.py` holds the CCF
call spine and nothing else — seven named regions, `boot` → `ingest` →
`operators` → `project` → `gate` → `record` → `serve` — and it contains no
entity class, no source system, no identifier, no threshold, no policy
version and no query. `deployment.py` holds what you would write for your
own domain: the projection Π, this deployment's artifact-key vocabulary,
and scenario setup. The boundary is structural rather than editorial: you
can see which calls are the fabric's from the directory listing, without
the rendered documentation site. That is the whole point of the shape, and
every other example in the suite copies it.

**Section 1 is agent-free by construction.** No module here imports
`ccf.agents`, `ccf.skills`, `ccf.workflow`, `ccf.hitl` or
`ccf_runtime.adapters`, and `tests/examples/test_section_one_is_agent_free.py`
fails the build if one ever does. CCF is a context fabric first; an agent is
a consumer of what this example produces, and it arrives in Section 3.

**On the domain, and the tension it sits in.** CLAUDE.md §9 and D-IMPL-52
ask the suite to visibly cross domains, because a suite that spans unrelated
domains argues for generality more convincingly than one neutral domain held
constant. This example is KYC/UBO on a fictional bank — chosen because that
is where the multi-hop ownership data lives and where the question earns a
typed product — and Sections 2 and 3 deliberately carry *other* domains. The
horizontal mix is satisfied across the suite, not within Section 1. It is
named here rather than fallen into silently.

It also demonstrates the **No-Hardcoding Rule** (CLAUDE.md §6.4): every
entity class, attribute name, threshold, decimal scale, TTL, boundary
instant and the subject of the question itself is loaded from
`artifacts/*.yaml`. Delete `artifacts/` and neither module has anything
meaningful to run.

## Run it

```sh
make example-s1-01
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/s1-01-hello-context-product/run.py
```

`run.py` is a thin driver and not a second spine: it wires `deployment.py`
into `spine.py` and exits. It **asserts nothing and prints nothing**. Exit
code 0 means the spine executed.

Its assertions live in `tests/examples/test_s1_01_output.py`. The split is
deliberate and it matters when you read `make ci`:

```sh
make examples                        # proves the spine RUNS
pytest tests/examples/               # proves it is CORRECT
```

Both are part of `make ci`, so nothing is unguarded — but a green
`make example-s1-01` on its own is not a correctness result, and the
invariants in the "What would fail" table below are checked by the test
modules, not by the example.

To materialise the enterprise source estate this example reads from —
the world that exists before any fabric does — run:

```sh
PYTHONPATH=src:runtime python examples/s1-01-hello-context-product/run.py --estate /tmp/estate
```

Nothing that writes goes into CCF's Context Graph. Systems of record are
read-only to L1, and CCF's graph is its own store (D-IMPL-95).

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `pytest tests/examples/test_s1_01_output.py`, review the
> failure, then deliberately edit `artifacts/expected.yaml` to match what
> you reviewed — in the same commit as the enrichment, with the commit body
> saying what changed in the output and why. There is no regeneration
> target and none will be added.

## The story

A KYC analyst at a fictional bank has to name the ultimate beneficial
owners of a corporate customer before onboarding it. The artifacts declare
everything the fabric needs; the code only interprets them.

0. **Name what is in force.** `artifacts/manifest.yaml` enumerates every
   other document — its path, its Control Plane key, its artifact class and
   its `role`. `role: register` puts an artifact into the Control Plane and
   therefore into replay dimension 2; `role: load` parses and validates it
   and hands it back without putting it in force. Nothing is discovered by
   globbing: the set of artifacts in force is part of the audit record, and
   a pattern would make that set a function of what happened to be on disk.

1. **`boot`.** One call reads the manifest, parses every document it names,
   registers the `role: register` ones and boots L2/L3 on the resulting
   pins. The connection value arrives here, **from the caller** — the
   manifest declares `backend: sqlite`, a kind and nothing more, because a
   database path in a content-hashed artifact is persisted into the audit
   plane forever.

2. **`ingest`.** The L1 envelopes in `artifacts/events.yaml` are handed to
   `booted.handle.worker`, the only write handle to the graph that exists
   anywhere in the process. Nothing else in either module holds one and
   nothing can obtain one.

3. **`operators`.** The graph is read at the temporal boundary the decision
   document names, and the four-category chain is built from the four
   `operator-parameters-*.yaml` documents. Each category is load-bearing
   here rather than decorative: **traversal** walks the ownership chain
   within a typed, depth-bounded neighborhood; **temporal** holds the
   boundary against a share transfer that is recorded before it and legally
   effective a month after it; **policy** substitutes out a
   jurisdiction-restricted director along with the edge that would announce
   him by its dangling end; **similarity** ranks a below-floor screening
   candidate out of the corpus.

4. **`project`.** The projection aggregates ownership across paths. Its
   required operator set comes from its own `projection-requirements.yaml`;
   the product class's claim comes from the separate `product-class.yaml`;
   and the binder between the two lines refuses a disagreement **before the
   engine runs**, rather than repairing one afterwards.

5. **`gate`.** The MAX_TTL ceiling is registered — which is what mints its
   pin — the product class is registered, the candidate product is built
   with the lineage the Control Plane *claims*, and the three delivery gates
   run. A `ServableProduct` is not constructible outside the gate call, so
   holding one is the evidence the gates ran.

6. **`record`.** The five-dimension Decision Replay record is built from
   the execution, the served product, the perspective and the pins in force.

7. **`serve`.** The record is persisted **before** the product is
   delivered, and delivery is what the successful append returns. There is
   no branch that reaches a served product without a recorded decision.

The answer that comes out: Jane Doe at 30.0% and John Smith at 45.0% are
beneficial owners; Sarah Chen is not. Sarah is the case worth reading
twice — she holds exactly the threshold *one hop down*, and 1.125% of the
subject three hops down. A single-hop reading would report her as a
beneficial owner. Depth is not significance, and the aggregation says so.

## Artifact-by-artifact

| Document | Role | What it carries |
| --- | --- | --- |
| `manifest.yaml` | — | Every other document, its key, its class and its role. `tenant_id` and `backend` live here. |
| `resolution-spec.yaml` | register | Entity and relationship resolution rules — which identity keys reconcile a record, which relations are reified. |
| `policy-bundle.yaml` | register | The regime, the jurisdiction, the beneficial-ownership threshold and the decimal scale the answer is reported at. |
| `operator-parameters-traversal.yaml` | register | Permitted edge types and depth bound for the ownership walk. |
| `operator-parameters-temporal.yaml` | register | How the as-of boundary treats recorded-versus-effective time. |
| `operator-parameters-policy.yaml` | register | The classification the perspective is entitled to, and the substitution behaviour. |
| `operator-parameters-similarity.yaml` | register | The screening query, the score floor and the corpus attribute per class. |
| `perspective.yaml` | register | The Π role-conditioning the product is served under. |
| `product-class.yaml` | register | Schema name and lane, TTL anchor, `assembly_mode`, the MAX_TTL key, and the operator set the product *claims*. |
| `projection-requirements.yaml` | register | The plan id and the projection's *own* required operator set — the second authored side of the binder. |
| `product-governance.yaml` | register | TTL ceiling and product TTL in seconds, the similarity index version, the replay artifact class and store directory. |
| `ubo-question.yaml` | register | The question as governance: which entity is the subject, which class is a natural person, which attribute carries a stake's percentage. |
| `events.yaml` | load | The L1 signal batch — the selection of the source estate this product needs. Fixed to `role: load` by the SDK. |
| `decision.yaml` | load | This run's temporal boundary and decision instant. Authored values; nothing here reads a clock. |
| `expected.yaml` | load | What the deployment declares the served product should contain, for the test module to assert against. |
| `source-estate.yaml` | *not in the manifest* | The enterprise source estate declaration, read by `source_estate.py`. Not Control Plane state and not in replay dimension 2. |

Every document carries a `# yaml-language-server: $schema=` header and an
`[ADAPT]` / `[MECHANISM]` two-line header naming which of its keys are your
vocabulary and which are interpreted by the factory.

`assembly_mode: algorithmic` in `product-class.yaml` is a governance choice
rather than boilerplate. The field describes how the **substrate** was
assembled, and its two siblings — `llm_packaged` and `swarm_assembled` —
arrive in Phase 17 (D-IMPL-94).

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §5.2, §7.3 — the Context Graph, and its mechanism
- whitepaper §7.4 — Context Operators and the four canonical categories
- whitepaper §7.5 — Context Projection Π
- whitepaper §7.6 — the Context Product Contract and its validation gates
- whitepaper §7.8 — Control Plane and Data Plane
- whitepaper §7.10 — Decision Replay
- CLAUDE.md §6.4 — the Agent & Task Factory and the No-Hardcoding Rule
  (SDK extension)
- CLAUDE.md §7.4 — MCP Artifact Persistence, the ArtifactStore
  (SDK extension)
- CLAUDE.md §9 — SDK Usage Examples, the v0 examples suite
- CLAUDE.md §10 — Architectural Layers (L1–L6)
- CLAUDE.md §11 — Working Principles

## What to change first

`artifacts/` **is** the specialization surface, and `deployment.py` is
yours. `spine.py` is not: every line in it is a call you would have to make
anyway.

**Start with the substrate, because it is one line and it is a value in a
configuration document rather than a fact about this code.**
`artifacts/manifest.yaml` says `backend: sqlite`. Change the document, not
the code — neither `spine.py` nor `deployment.py` names a substrate
anywhere, and no connection string, host or credential appears in any
artifact. Plan 16-07 adds the per-backend siblings and the `backends.yaml`
document that makes this one driver run across all six.

Then, in order:

1. `artifacts/resolution-spec.yaml` — your entity classes, identity keys
   and relationship rules.
2. `artifacts/source-estate.yaml` and `artifacts/events.yaml` — your source
   systems' records, and the selection of them this product needs.
3. `artifacts/ubo-question.yaml` — the question. Which entity is the
   subject and which attributes carry what; this is what the projection
   interprets.
4. `artifacts/operator-parameters-*.yaml` — retune all four, especially the
   permitted edge types, the depth bound, the screening query and the score
   floor.
5. `artifacts/policy-bundle.yaml` — your regime, jurisdiction and
   threshold.
6. `artifacts/product-class.yaml` and `artifacts/projection-requirements.yaml`
   — your schema name and lane. If your projection needs a different
   operator set, change it in **both** documents; do not change it in
   `spine.py`.
7. `deployment.py` — replace `UltimateBeneficialOwnershipPlan` with your own
   projection. It is the one piece of real code you write.
8. `artifacts/manifest.yaml` — `tenant_id`, and any `class_id` you renamed.
9. `artifacts/expected.yaml` — last, after one reviewed run.

On the next run expect your entity classes in the served payload, your
relationship types surviving traversal, and a failing
`pytest tests/examples/test_s1_01_output.py` until you complete step 9 —
that failure is the workflow, not a bug.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| single-writer (INV-CH7-10) | there is no writer to obtain; `deployment.py` holds none and the fabric is booted through the real composition root |
| idempotent upsert + lineage set-union (INV-CH7-16/17) | the same party arriving from two source systems would create a second node, or overwrite instead of accumulating lineage |
| bounded traversal (INV-CH7-24) | the walk would reach past its typed, depth-bounded neighborhood, and the three registered addresses would appear in an ownership answer |
| policy substitution (INV-CH7-26) | the jurisdiction-restricted director — or the ownership edge that would leak his existence by absence — would survive |
| similarity ranking (INV-CH7-27) | the below-floor screening candidate would survive |
| temporal as-of (whitepaper §7.4) | a share transfer legally effective a month after the boundary would already count, and its incoming shareholder would be named a beneficial owner |
| aggregation across hops (phase 16 D-03) | the near-miss party at exactly the threshold one hop down would be reported as a beneficial owner, and Jane Doe's real interest would be understated |
| the three gates (INV-CH7-46/47/48) | an empty-operator, forged-lineage or over-TTL product would become servable |
| the operator-set binder (D-IMPL-86) | the projection's own required set and the product class's claim could drift apart, and the disagreement would be repaired silently instead of refused before the engine runs |
| replay before delivery (INV-CH7-79) | a product would be served with no five-dimension record in the store |
| the No-Hardcoding Rule (CLAUDE.md §6.4) | a threshold, an entity class or a query would live in `spine.py` or `deployment.py` instead of an artifact |
| the spine/deployment split (phase 16 D-11) | a fabric call would sit in `deployment.py`, or a domain value in `spine.py`, and a reader could no longer tell which code is required by CCF |
| Section 1 is agent-free (phase 16 D-12) | a module here would import an agent, skill, workflow, HITL or harness-adapter surface |

Nothing in that table is checked by `run.py`. The rows through *replay
before delivery* are checked by `tests/examples/test_s1_01_output.py`; the
No-Hardcoding row by `python -m tools.lints --all`; the spine/deployment
split by `tests/examples/test_spine_separation.py`; and the agent-free row
by `tests/examples/test_section_one_is_agent_free.py`.
