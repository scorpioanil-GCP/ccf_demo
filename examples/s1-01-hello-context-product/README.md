# examples/s1-01-hello-context-product — "Hello, Context Product", and where the fabric ends

## What this demonstrates

**A Context Product is something you CALL, not something you configure.**
That is the first claim, it is the one everything else here rests on, and
one command shows it:

```sh
make example-s1-01
```

That asks the same product class three questions and gets three different
answers out of one graph, one ingest, and no second query:

| # | Question | Beneficial owners it returns | D_c |
| --- | --- | --- | --- |
| 1 | Who ultimately owns **Acme**, as of **1 Aug 2026**? | Jane Doe 30.0%, John Smith 45.0% | 0.035 — `ok` |
| 2 | Who ultimately owns **Beta Holdings**, as of **1 Aug 2026**? | Jane Doe 60.0% | 0.035 — `ok` |
| 3 | Who ultimately owns **Acme**, as of **15 Sep 2026**? | Jane Doe 30.0%, John Smith 45.0%, **Marcus Vale 30.0%** | 0.221 — `forced_llm` |

Read the pairs. **1 versus 2** is a different *company*: Jane's interest
doubles, John's falls to zero, and the answer is a different list of
people. **1 versus 3** is a different *instant*: a share transfer that was
already sitting in the graph on 1 August but was not legally effective
until September makes Marcus Vale a beneficial owner — and nothing was
re-ingested in between. The measured Context Debt rises with the staleness
and crosses this deployment's Forced-LLM band, so the answer arrives saying
*how much to trust it* and *which dimension is weak*.

Ask a fourth question that is in no artifact at all:

```sh
PYTHONPATH=src:runtime python examples/s1-01-hello-context-product/run.py \
  --subject http://example.org/fibo/GammaBank \
  --as-of 2026-08-01T00:00:00Z \
  --decision-instant 2026-08-01T00:05:00Z
```

Nothing was edited. The subject and both instants are fields on a typed
`ProductRequest`, validated at the door against the request surface the
product class declares (whitepaper §6.3 *Addressability*, D-IMPL-98). This
is the difference between the verb *aggregate* and the verb *assemble*: the
question is not knowable at design time, so it is not written down at
design time.

It answers a question a vector store over chunked documents structurally
cannot. Jane Doe holds 12.0% of Acme directly and 60.0% of a holding
company that itself holds 30.0%. Her real interest is 30.0%, it crosses the
regime's 25.0% threshold, and **no document in any source system states
that number**. It is a sum over ownership paths, which is what a graph is a
substrate for — and it is a *different* sum depending on which company you
ask about and when.

Under all of that: the whole fabric, end to end in one process, with no API
key, no model and **no agent anywhere in it** — boot on a manifest, ingest a
handful of L1 envelopes, build the four-category operator chain, project,
pass the three delivery gates, record the decision across five dimensions,
pin the graph questions that were actually asked, and serve one typed
**Context Product** carrying its own debt.

**The thing to look at second is the file split.** `spine.py` holds the CCF
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
entity class, attribute name, threshold, decimal scale, TTL and λ_c rate is
loaded from `artifacts/*.yaml`. Delete `artifacts/` and neither module has
anything meaningful to run.

The rule cuts the other way too, and the distinction is worth holding on to.
The *vocabulary* the question is asked in — which class is a natural person,
which attribute carries a stake's percentage — is Control Plane governance
and belongs in an artifact. The *subject and the instant* are not: re-asking
about a different company is not a governance change, and freezing them into
a document is what made this example configurable rather than callable
before plan 15.5-13.

## Run it

**Prerequisite: a reachable Fluree server.** `artifacts/manifest.yaml` declares
`backend: fluree`, and a run that cannot reach one **refuses** rather than
falling back to anything.

```sh
docker run --rm -p 8090:8090 fluree/server:4.1.4
```

```sh
make example-s1-01                       # the three declared questions
```

or, directly:

```sh
CCF_TEST_FLUREE_URL=http://localhost:8090 \
  PYTHONPATH=src:runtime python examples/s1-01-hello-context-product/run.py
```

`CCF_TEST_FLUREE_URL` is the variable `artifacts/backends.yaml` names — the same
one `tests/conftest.py` gates the Fluree test leg on, so one export configures
both. `make example-s1-01` defaults it to `http://localhost:8090`. Unset it and
the run stops with a message naming the variable and the container to start.

**Dated note, 2026-10-06 (D-IMPL-374 (1), SEC-013).** The Fluree store now
mints a writer only under a declared, held cross-process writer lease, and a
boot without one is refused with `WriterLeaseRequired`. `artifacts/backends.yaml`
therefore declares a third Fluree setting, `writer_lease_lock_dir`, composed as
the run's own absolute scratch root; the SDK derives the lock file inside it
from the graph identity. This is a deliberate change to the SDK surface the
example consumes (D-IMPL-261), not a repair of the example.

Each run attaches to a **fresh graph inside one CCF-owned ledger**, so repeated
runs accumulate graphs in a long-lived container. That is the deliberate trade
for a single Fluree lane; discarding the container discards them all.

`--quiet` suppresses all output and exits 0. The **default is to print**.

With no arguments it asks the three questions `artifacts/questions.yaml`
declares. With `--subject`, `--as-of` and `--decision-instant` — supplied
together, none of them defaulted — it asks one of yours instead. A defaulted
subject would be the frozen answer this example was rewritten to remove, and
a defaulted instant is a clock read wearing a disguise: the driver reads the
clock or takes the instant as an argument, and the fabric never does either
(which is exactly what makes replay feed the recorded boundary back through
the same code path and get the same answer).

`run.py` is a thin driver and not a second spine: it wires `deployment.py`
into `spine.py`, prints, and exits. It **asserts nothing**, and what it prints
is composed by `report.py` — a presentation-only sibling that returns strings,
carries no snippet marker region, and therefore puts not one printed line into
the published documentation. Exit code 0 means the spine executed.

The assertions live in `tests/examples/test_s1_01_output.py`. The split is
deliberate and it matters when you read `make ci`:

```sh
make example-s1-01                   # proves the spine RUNS, and shows its work
make leg-fluree                      # proves it is CORRECT
```

This example is **not** in the always-on `make examples` aggregate, and that is
a rule rather than an oversight: always-on CI is deterministic and network-free,
and a job that ran this target would need a service container. `make leg-fluree`
is what exercises it in CI. Three gates over this example do stay always-on,
because they need no substrate: the agent-free AST guard, the spine/deployment
separation gate, and the artifact-header check.

A green `make example-s1-01` on its own is still not a correctness result, and
the invariants in the "What would fail" table below are checked by the test
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

**What you will see.** Abridged from an actual run — three questions, six
sections each, 337 lines in full:

```text
QUESTION 1 of 3 — asked, not configured
--------------------------------------------------------------------------
  subject                     http://example.org/fibo/AcmeCorp
  intent                      kyc-periodic-review
  freshness                   as-of-boundary
  as-of instant               2026-08-01 00:00:00+00:00   the graph is read here
  decision instant            2026-08-01 00:05:00+00:00   the TTL runs from here

  Subject and instant are arguments on a typed request.
  One product class answers about any company at any time.

WHAT WAS ASSEMBLED
--------------------------------------------------------------------------
  L1 envelopes ingested       19
  entities in the view        17
    class corporation         5
    class ownership_stake     8
    class party               3
    class screening_candidate 1
  relationship types          holds_stake, screened_against, stake_incident_to
  graph substrate             fluree   artifacts/manifest.yaml

  The substrate is one line in artifacts/manifest.yaml.
  artifacts/backends.yaml says how that kind's connection is composed.
  No Python module under this example names a substrate.

WHAT THE FABRIC DID
--------------------------------------------------------------------------
  policy operator             policy.principal-subgraph
      permitted_classifications = [kyc-disclosable]
  similarity operator         similarity.corpus-select
      minimum_score_percent = 40
  ... (each operator's own parameters, four categories) ...
  projection                  fibo-kyc.ultimate-beneficial-ownership.plan
  perspective role            kyc-analyst

  Algorithmic stages narrow the graph; the projection reads it.
  No model saw raw signal, and no model was called at all.

THE ANSWER
--------------------------------------------------------------------------
  subject                     http://example.org/fibo/AcmeCorp
  threshold                   25.000 percent   policy-bundle.yaml

  At or above the threshold — the beneficial owners:
    Jane Elizabeth Doe        30.000 percent   http://example.org/fibo/JaneDoe
    John Michael Smith        45.000 percent   http://example.org/fibo/JohnSmith

  Below the threshold — the near miss the threshold removed:
    short by 23.875           1.125 percent   http://example.org/fibo/SarahChen

  Each percent above is a SUM OVER OWNERSHIP PATHS.
  A direct holding, plus a fraction of an intermediary's holding.
  Composed over: 5 corporation, 8 ownership_stake, 3 party, 1 screening_candidate.
  Aggregates: JaneDoe 30.000, JohnSmith 45.000, SarahChen 1.125.
  No record of any source system states any of those numbers.
  That is the difference between assembling and looking up.

WHAT TRAVELS WITH THE ANSWER
--------------------------------------------------------------------------
  content address             19b230aca20349d216384b12b4309a958f0b21285f9820d373eac67e89bef536
  schema                      fibo-kyc.ultimate-beneficial-ownership 1.0.0
  expires at                  2026-08-01 00:15:00+00:00
  TTL anchor                  from_decision
  operators invoked           policy.principal-subgraph, similarity.corpus-select, temporal.as-of-boundary, traversal.typed-neighborhood
  policy bundle versions      5520f88f7b9ee813008800e52e097cea128479d58162b785aa48e23dbec3eff8
  graph snapshot at           2026-08-01 00:00:00+00:00
  context debt D_c            0.0348251467461090910588235294
  routing signal              ok
    freshness                 0.9950256219112277411764705882
    completeness              1
    semantic consistency      0.97
    scorer for freshness      ccf.reference.freshness-from-decay@1.0.0
  obligation in force         ccf.no-obligation-in-force
      what this deployment said this signal obliges it to do
      CCF supplies the binding and none of the vocabulary
      whitepaper §7.7 Context Debt and Context Half-life
  debt evidence               0 pointers
      omitted by ruling, D-IMPL-119 limb 3(b), until a later phase
      adds principal scoping to the assembly path
  oldest source refresh       2026-08-01 00:00:00+00:00
  newest source refresh       2026-08-10 23:45:00+00:00
      two instants, D-IMPL-124: no system is named here
      and no count of them is given either
  replay record class         decision-replay-record
  replay record address       28af74697b53c819275e9e5d506b2e26c608453ce7b8bc2c6126c7807ba13880
  graph queries pinned        2 of 2 resolvable

  REPLAY IT — the record resolves, by exact version:
    the graph snapshot instant and the policy bundle version;
    the perspective, the request, and the operator plan;
    and every graph query, pinned by its own content address.
  Nothing above was read from a clock.
  Whitepaper §7.10 Decision Replay.

... QUESTION 2 of 3 and QUESTION 3 of 3, in the same six sections ...

WHAT THE THREE QUESTIONS SHOW
--------------------------------------------------------------------------
  Read artifacts/questions.yaml as pairs, not as a list.

  Same instant, different subject:
      A asked about           http://example.org/fibo/AcmeCorp   2026-08-01 00:00:00+00:00
      A answered              http://example.org/fibo/JaneDoe, http://example.org/fibo/JohnSmith
      A address               19b230aca20349d216384b12b4309a958f0b21285f9820d373eac67e89bef536
      B asked about           http://example.org/fibo/BetaHoldings   2026-08-01 00:00:00+00:00
      B answered              http://example.org/fibo/JaneDoe
      B address               c9df093534f1ed5e85bd0b4955fba80ed25ab9bb16af784f264843cedbc9d734

  Same subject, different instant:
      A asked about           http://example.org/fibo/AcmeCorp   2026-08-01 00:00:00+00:00
      A answered              http://example.org/fibo/JaneDoe, http://example.org/fibo/JohnSmith
      A address               19b230aca20349d216384b12b4309a958f0b21285f9820d373eac67e89bef536
      B asked about           http://example.org/fibo/AcmeCorp   2026-09-15 00:00:00+00:00
      B answered              http://example.org/fibo/JaneDoe, http://example.org/fibo/JohnSmith, http://example.org/fibo/MarcusVale
      B address               d49f4b869aefd5a3b6b992659c69bbf625d0493e2e3d332a9964fc6ff07803ec

  Same product class, same code, same artifacts.
  A different question, therefore a different answer.
  Each answer separately addressed and separately replayable.
```

The content addresses above are this estate's; re-run and they reproduce,
because nothing in the path reads a clock and the graph a run attaches to is
not part of a product's address.

0. **Name what is in force.** `artifacts/manifest.yaml` enumerates every
   other document — its path, its Control Plane key, its artifact class and
   its `role`. `role: register` puts an artifact into the Control Plane and
   therefore into replay dimension 2; `role: load` parses and validates it
   and hands it back without putting it in force. Nothing is discovered by
   globbing: the set of artifacts in force is part of the audit record, and
   a pattern would make that set a function of what happened to be on disk.

1. **`boot`.** One call reads the manifest, parses every document it names,
   registers the `role: register` ones and boots L2/L3 on the resulting
   pins. The connection values arrive here, **from the caller** — the
   manifest declares `backend: fluree`, a kind and nothing more, because a
   host, a path or a credential in a content-hashed artifact is persisted
   into the audit plane forever. How that kind's settings are composed is
   `artifacts/backends.yaml`'s job, and it holds an environment variable's
   *name* and a per-run rule rather than a value.

2. **`ingest`.** The L1 envelopes in `artifacts/events.yaml` are handed to
   `booted.handle.worker`, the only write handle to the graph that exists
   anywhere in the process. Nothing else in either module holds one and
   nothing can obtain one.

2b. **The door.** Before the graph is touched, `refuse_request` compares the
   caller's `ProductRequest` against `artifacts/request-contract.yaml` — the
   address first (is this even a question for this class, at this lane?),
   then the class-declared parameters, whose declared world is *closed*. A
   parameter the class never declared is refused rather than forwarded,
   because a parameter that reaches plan selection undeclared is an argument
   nobody governed. Nothing on the request says who is asking: role and
   tenant are things a door **establishes** from a verified grant, never
   things a request **claims**.

3. **`operators`.** The graph is read at the temporal boundary **the request
   asked as of**, and the four-category chain is built from the four
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

5. **`gate`.** The MAX_TTL ceiling and the request contract are registered —
   which is what mints their pins — the product class is registered against
   both, the candidate product is built with the lineage the Control Plane
   *claims* **and the Context Debt measured over what was actually
   assembled**, and the three delivery gates run. A `ServableProduct` is not
   constructible outside the gate call, so holding one is the evidence the
   gates ran.

6. **`record`.** The five-dimension Decision Replay record is built from
   the execution, the served product, the perspective and the pins in force.

7. **`serve`.** The canonical bytes of every graph query the engine issued
   are persisted, *then* the record, *then* the product is delivered — and
   delivery is what the successful append returns. There is no branch that
   reaches a served product without a recorded decision, and no moment at
   which the record pins a question the store cannot resolve.

The answer that comes out for question 1: Jane Doe at 30.0% and John Smith
at 45.0% are beneficial owners; Sarah Chen is not. Sarah is the case worth
reading twice — she holds exactly the threshold *one hop down*, and 1.125%
of the subject three hops down. A single-hop reading would report her as a
beneficial owner. Depth is not significance, and the aggregation says so.

**Which question a decision answered is pinned, on both readings** — and
until 2026-08-11 only one of the two was. The record's
`graph_query_sequence` pins the questions put to the **graph**. Questions 1
and 3 pin differently because the boundary is compiled into the query, and
questions 1 and 2 now pin differently too, because the request's subject
seeds the traversal (D-IMPL-111 limb (a)). Their *first* pin is still shared:
that segment carries the policy family and no walk, and a query with seeds
and no walk to start is not well formed.

The question put to the **product** — subject, intent, freshness and the
instant it was asked as of — is carried verbatim in replay dimension 5
(D-IMPL-111 limb (b)). It was recorded nowhere before that ruling: the
subject was *recoverable* from the served payload and the boundary from
dimension 1, but `intent` and `freshness` were in no dimension at all, and
recovery-by-inference is not the same property as a pin.

## Artifact-by-artifact

| Document | Role | What it carries |
| --- | --- | --- |
| `manifest.yaml` | — | Every other document, its key, its class and its role. `tenant_id` and `backend` live here. |
| `resolution-spec.yaml` | register | Entity and relationship resolution rules — which identity keys reconcile a record, which relations are reified. |
| `policy-bundle.yaml` | register | The regime, the jurisdiction, the beneficial-ownership threshold and the decimal scale the answer is reported at. |
| `operator-parameters-traversal.yaml` | register | Permitted edge types and depth bound for the ownership walk. |
| `operator-parameters-temporal.yaml` | register | How the as-of boundary treats recorded-versus-effective time. |
| `operator-parameters-policy.yaml` | register | The classification the perspective is entitled to, and the substitution behaviour. |
| `operator-parameters-similarity.yaml` | register | The screening query, the score floor, the corpus attribute per class, and **the corpus's `index_version`** — its version identity, which lives here as of `D-IMPL-292` because the artifact that declares the corpus map is the one that owns which corpus it is. |
| `perspective.yaml` | register | The Π role-conditioning the product is served under. |
| `product-class.yaml` | register | Schema name and lane, TTL anchor, `assembly_mode`, the MAX_TTL key, and the operator set the product *claims*. |
| `projection-requirements.yaml` | register | The plan id and the projection's *own* required operator set — the second authored side of the binder. |
| `product-governance.yaml` | register | TTL ceiling and product TTL in seconds, the replay and query-pin artifact classes and store directory, the request-contract key, what a complete assembly holds, and the declared S factor. **The similarity index version is no longer here** — `D-IMPL-292` gave it a canonical home on `operator-parameters-similarity.yaml`, beside the corpus map the same artifact already declared, so the registry builder reads the corpus identity off the declaration that owns it rather than from a value this document restated. |
| `ubo-question.yaml` | register | The **vocabulary** the question is asked in: which class is a natural person, which attribute carries a stake's percentage. The subject is *not* here — that is the caller's. |
| `half-life-table.yaml` | register | λ_c per observation type. This deployment types observations by resolved entity class; a share transfer decays over months, a screening hit over a week. |
| `debt-profile.yaml` | register | The CAR bands — risk sensitivity, and the D_c thresholds at which the answer routes to Forced-LLM or Fail-Closed — plus what each of those states obliges this deployment to do. The obligations are this bank's words; the SDK ships none. |
| `events.yaml` | load | The L1 signal batch — the selection of the source estate this product needs. Fixed to `role: load` by the SDK. |
| `request-contract.yaml` | load | The class's **request surface**: which questions it answers, and the class-declared parameters beyond the four address axes. `load`, because the pin binding it to the class is minted by registering it. |
| `expected.yaml` | load | What the deployment declares the served products should contain, for the test module to assert against — all three questions. |
| `questions.yaml` | *not in the manifest* | The questions the bundled demonstration **asks**. Caller input, not Control Plane state; a question is not a permission and belongs in no replay dimension. Read directly by `run.py`. |
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

**Start with the substrate, because it is two documents and no code.**
`artifacts/manifest.yaml` says `backend: fluree` — that is the KIND, and it is
one line. `artifacts/backends.yaml` says how that kind's connection settings are
COMPOSED: which environment variable carries the server's location, and which
settings are minted fresh per run so a shared server gives each run its own
graph. Neither document holds a value; between them they hold a name and a rule.

Change the documents, not the code. No Python module under this example names a
substrate anywhere, and no connection string, host, path or credential appears
in any artifact. To run on a different kind: add a profile to `backends.yaml`
and change the one line in `manifest.yaml`. A deployment whose server needs a
credential adds one `backend_secrets` entry to `manifest.yaml` naming the
environment variable that carries it — the name is content-hashed, the value
never is.

Plan 16-07 adds the remaining four profiles and the equality matrix that runs
this one driver across all six kinds.

Then, in order:

1. `artifacts/resolution-spec.yaml` — your entity classes, identity keys
   and relationship rules.
2. `artifacts/source-estate.yaml` and `artifacts/events.yaml` — your source
   systems' records, and the selection of them this product needs.
3. `artifacts/ubo-question.yaml` — the question's **vocabulary**: which
   class is a natural person, which attributes carry what. This is what the
   projection interprets. The *subject* is not here and should not be put
   back — see `artifacts/questions.yaml` and `--subject` for where a
   question comes from.
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
8. `artifacts/request-contract.yaml` and `artifacts/questions.yaml` — the
   questions your class answers, and the ones the demonstration asks.
9. `artifacts/half-life-table.yaml` and `artifacts/debt-profile.yaml` — your
   λ_c rates and your CAR bands. These are regulatory posture, not tuning:
   they decide when your fabric escalates instead of answering.
   **`signal_obligations` in the same document is `[ADAPT]` in the strongest
   sense the No-Hardcoding Rule has** — it is what each routing state
   *obliges you to do*, and no CCF release contains any of those words. The
   SDK validates the keys, because `DebtSignal` is its own type; it never
   parses, checks or acts on the values. Bind the states you have an answer
   for and leave the rest unbound: the delivered product then carries a named
   sentinel saying so, which is a positive claim rather than a silence. What
   the product carries is the obligation in force **at the time** — rebind
   these tomorrow and yesterday's replay still reproduces yesterday's
   obligation. Whether anything then *happens* is your code's job; wiring an
   action is exactly the step CCF leaves to you, because taking it would mean
   the SDK had chosen your escalation policy.
10. `artifacts/manifest.yaml` — `tenant_id`, and any `class_id` you renamed.
11. `artifacts/expected.yaml` — last, after one reviewed run.

On the next run expect your entity classes in the served payload, your
relationship types surviving traversal, and a failing
`pytest tests/examples/test_s1_01_output.py` until you complete step 11 —
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
| assemble, not aggregate (plan 15.5-13) | two companies, or two instants, would get the same answer — the subject or the boundary would have stopped reaching the fabric from the request |
| resolvable query pins (T-15.2-28) | the record would pin graph questions whose canonical bytes are in no store, so an auditor could not ask what was asked |
| debt rides the vessel (D-IMPL-100) | the product would arrive with `debt=None`, and its consumer would have no way to know how much to trust it |
| debt is measured (whitepaper §7.7) | the same question six weeks later would report the same freshness, and the CAR signal would be a constant wearing a measurement's clothes |
| replay before delivery (INV-CH7-79) | a product would be served with no five-dimension record in the store |
| the No-Hardcoding Rule (CLAUDE.md §6.4) | a threshold, an entity class or a query would live in `spine.py` or `deployment.py` instead of an artifact |
| the spine/deployment split (phase 16 D-11) | a fabric call would sit in `deployment.py`, or a domain value in `spine.py`, and a reader could no longer tell which code is required by CCF |
| Section 1 is agent-free (phase 16 D-12) | a module here would import an agent, skill, workflow, HITL or harness-adapter surface |

Nothing in that table is checked by `run.py`. The rows through *replay
before delivery* are checked by `tests/examples/test_s1_01_output.py`; the
No-Hardcoding row by `python -m tools.lints --all`; the spine/deployment
split by `tests/examples/test_spine_separation.py`; and the agent-free row
by `tests/examples/test_section_one_is_agent_free.py`.
