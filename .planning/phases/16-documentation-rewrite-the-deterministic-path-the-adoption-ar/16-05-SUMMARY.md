---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 05
status: paused-at-checkpoint
subsystem: examples
tags: [fluree, context-product, kyc, ubo, replay, no-hardcoding, harness-free]

requires:
  - phase: 15.6
    provides: the D-IMPL-118 top-level debt carrier, D-IMPL-119 limb 3(b), D-IMPL-124
  - phase: 16-04
    provides: tools/docs_tests/test_gate_two_wording.py, the standing Gate-2 wording gate
provides:
  - "examples/s1-01-hello-context-product running on a Fluree backend selected by artifacts/manifest.yaml + artifacts/backends.yaml"
  - "the connection-profile interpreter and the three value sources (from_env, per_run identifier, per_run path) that plan 16-07 extends to six backends"
  - "a printing example: report.py, a presentation-only sibling with no snippet marker region"
affects:
  - "plan 16-07 (V-4, the six-backend matrix) — extends artifacts/backends.yaml, changes no Python"
  - "plan 16-08 and every later Section-1 example — copies the three-file shape (spine / deployment / report)"

tech-stack:
  added: []
  patterns:
    - "connection profiles as a declared artifact outside the manifest, on questions.yaml's not-in-the-manifest model"
    - "presentation as a third named module carrying no snippet marker region"

key-files:
  created:
    - examples/s1-01-hello-context-product/artifacts/backends.yaml
    - examples/s1-01-hello-context-product/report.py
  modified:
    - examples/s1-01-hello-context-product/artifacts/manifest.yaml
    - examples/s1-01-hello-context-product/deployment.py
    - examples/s1-01-hello-context-product/run.py
    - examples/s1-01-hello-context-product/spine.py
    - examples/s1-01-hello-context-product/README.md
    - tests/examples/test_s1_01_output.py
    - tests/examples/test_spine_separation.py
    - Makefile

decisions:
  - "The refusal remedy text lives in artifacts/backends.yaml, not in deployment.py — the only way to satisfy both 'the refusal names the fluree/server:4.1.4 container' and 'no substrate name in deployment.py'"
  - "The substrate line in section 2 is read from artifacts/manifest.yaml by report.py, because the replay record's graph_adapter field reads `no-adapter` (see findings)"
  - "The D-IMPL-119 absence assertion iterates record.context_fabric_snapshot.touched_entities, because Assembled carries no view and adding one would falsify the byte-unchanged criterion"

metrics:
  duration: "one session"
  completed: 2026-08-13
  tasks_completed: 2
  tasks_total: 3
---

# Phase 16 Plan 05: Hello CCF — Fluree Backend, Printed Output (Summary)

`examples/s1-01-hello-context-product` now runs on a live Fluree server chosen
by two configuration documents, and prints six named sections that carry a
newcomer from the question asked to everything that travels with the answer.

**Status: `paused-at-checkpoint`.** Tasks 1 and 2 are complete and committed.
Task 3 is a `checkpoint:human-verify` with `gate="blocking"` and was
deliberately not attempted.

## Commits

| Task | Commit | What it did |
| --- | --- | --- |
| 1 | `1dee7c7` | `refactor(16-05)`: substrate moved to Fluree, selected by `artifacts/backends.yaml`; example gated out of the always-on `examples` aggregate |
| 2 | `12fe906` | `feat(16-05)`: `report.py` and the printing driver; four false `D-09` citations corrected |

Both on `phase-16`. Not pushed, not merged.

## What Task 1 changed

- **`artifacts/backends.yaml`** (new, 96 lines). A `ccf.declared-artifact`,
  deliberately **not** in the manifest, on `questions.yaml`'s model: connection
  material is deployment environment, not Control Plane state, and has no
  business in replay dimension 2. Its `declaration.profiles` block is keyed by
  backend kind. Each setting names exactly one of three value sources —
  `from_env: NAME`, `per_run: identifier` with a `prefix:`, `per_run: path`
  with a `filename:`. Two profiles ship (`fluree`, `sqlite`), which is what
  makes the reader a general interpreter rather than a Fluree-shaped hole.
- **`artifacts/manifest.yaml`**: `backend: sqlite` → `backend: fluree`, one
  line, plus the prose rewritten to the two-document arrangement. No
  `backend_secrets` entry — the local container answers unauthenticated, and a
  declared env reference that does not resolve is a refusal rather than a
  fallback, so declaring one would make the example unrunnable.
- **`deployment.py`**: `CONNECTION_PATH_KEY` and `DATABASE_FILENAME` deleted.
  `connection(*, root)` keeps its signature and becomes an interpreter:
  `_declared_kind()` reads the manifest's one line, `_profile(kind)` looks up
  the profile, and the settings are resolved through `_from_environment` or
  `_per_run`. The only branch is over the three source kinds.
- **`tests/examples/test_s1_01_output.py`**: `pytestmark = pytest.mark.fluree`
  and both fabric-booting fixtures request the session-scoped `fluree_url`
  fixture.
- **`Makefile`**: `example-s1-01` removed from the `examples:` prerequisite
  list and moved beside the container-gated legs.

### Three refusals, none of which falls back

| Refusal | Observed |
| --- | --- |
| `backends.yaml` moved aside | exit 1, `FileNotFoundError: …/artifacts/backends.yaml is missing. … there is no default to fall back to: the code is an interpreter and this document is what it interprets (CLAUDE.md §6.4, the No-Hardcoding Rule).` |
| `CCF_TEST_FLUREE_URL` unset and unexported | exit 1, `RuntimeError` — *"CCF_TEST_FLUREE_URL is unset; start a fluree/server:4.1.4 container and export the base URL. It supplies `url`, which artifacts/backends.yaml declares this deployment reads from the environment. There is no default and no fallback to another backend kind."* |
| No profile for the declared kind | `KeyError` naming the kinds the document does declare (code path present; not exercised, since both shipped profiles resolve) |

**Negative control run, unprompted by the plan.** Pointing
`CCF_TEST_FLUREE_URL` at a dead port produced
`httpx.ConnectError: [Errno 111] Connection refused` and exit 1. The example
genuinely crosses a network boundary; there is no silent SQLite path left.

## What Task 2 changed

`report.py` (new, 336 lines) is a presentation-only sibling. It exposes
`render(assembled, *, index, total) -> str` and
`render_contrast(answers) -> str`; both **return** strings and print nothing,
`run.py` prints them. It carries **zero** snippet marker regions
(`grep -c -- "--8<--" report.py` → `0`), so not one printed line is publication
surface. `--quiet` writes zero bytes and exits 0; the default is to print.

`spine.py` changed in exactly two places, both docstring prose — the two false
`D-09` citations at lines 69-70 and 241.

## Wall-clock time

**5.9 s** for `make example-s1-01` — three questions, three full boots, three
ingest cycles of 19 envelopes each over HTTP into Fluree, three assemblies,
three replay records written, and 337 lines rendered. Well under the 60 s flag
threshold. `make leg-fluree` (76 tests) is 39 s.

## The printed output, verbatim

This is the record the Task 3 checkpoint reads, independent of a terminal.
Produced by `make example-s1-01` at commit `12fe906`.

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
      classification_attribute_by_class = [corporation->corporation_classification, ownership_stake->stake_classification, party->party_classification, registered_address->address_classification, screening_candidate->screening_classification]
      permitted_classifications = [kyc-disclosable]
  similarity operator         similarity.corpus-select
      minimum_score_percent = 40
      query = Acme Corporation Inc.
      ranked_entity_classes = [screening_candidate]
      similarity_corpus_attribute_by_class = [screening_candidate->screening_legal_name]
  temporal operator           temporal.as-of-boundary
      require_valid_at_boundary = True
  traversal operator          traversal.typed-neighborhood
      depth_limit = 6
      relationship_types = [holds_stake, screened_against, stake_incident_to]
      seed_entity_classes = [party]
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

QUESTION 2 of 3 — asked, not configured
--------------------------------------------------------------------------
  subject                     http://example.org/fibo/BetaHoldings
  intent                      kyc-onboarding
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
      classification_attribute_by_class = [corporation->corporation_classification, ownership_stake->stake_classification, party->party_classification, registered_address->address_classification, screening_candidate->screening_classification]
      permitted_classifications = [kyc-disclosable]
  similarity operator         similarity.corpus-select
      minimum_score_percent = 40
      query = Acme Corporation Inc.
      ranked_entity_classes = [screening_candidate]
      similarity_corpus_attribute_by_class = [screening_candidate->screening_legal_name]
  temporal operator           temporal.as-of-boundary
      require_valid_at_boundary = True
  traversal operator          traversal.typed-neighborhood
      depth_limit = 6
      relationship_types = [holds_stake, screened_against, stake_incident_to]
      seed_entity_classes = [party]
  projection                  fibo-kyc.ultimate-beneficial-ownership.plan
  perspective role            kyc-analyst

  Algorithmic stages narrow the graph; the projection reads it.
  No model saw raw signal, and no model was called at all.

THE ANSWER
--------------------------------------------------------------------------
  subject                     http://example.org/fibo/BetaHoldings
  threshold                   25.000 percent   policy-bundle.yaml

  At or above the threshold — the beneficial owners:
    Jane Elizabeth Doe        60.000 percent   http://example.org/fibo/JaneDoe

  Below the threshold — the near miss the threshold removed:
    short by 25.000           0.000 percent   http://example.org/fibo/JohnSmith
    short by 21.250           3.750 percent   http://example.org/fibo/SarahChen

  Each percent above is a SUM OVER OWNERSHIP PATHS.
  A direct holding, plus a fraction of an intermediary's holding.
  Composed over: 5 corporation, 8 ownership_stake, 3 party, 1 screening_candidate.
  Aggregates: JaneDoe 60.000, JohnSmith 0.000, SarahChen 3.750.
  No record of any source system states any of those numbers.
  That is the difference between assembling and looking up.

WHAT TRAVELS WITH THE ANSWER
--------------------------------------------------------------------------
  content address             c9df093534f1ed5e85bd0b4955fba80ed25ab9bb16af784f264843cedbc9d734
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
  replay record address       29b20e767d6b535d097f071f752aea81cb8f20beb969b1327b5311beda2a7454
  graph queries pinned        2 of 2 resolvable

  REPLAY IT — the record resolves, by exact version:
    the graph snapshot instant and the policy bundle version;
    the perspective, the request, and the operator plan;
    and every graph query, pinned by its own content address.
  Nothing above was read from a clock.
  Whitepaper §7.10 Decision Replay.

QUESTION 3 of 3 — asked, not configured
--------------------------------------------------------------------------
  subject                     http://example.org/fibo/AcmeCorp
  intent                      kyc-periodic-review
  freshness                   as-of-boundary
  as-of instant               2026-09-15 00:00:00+00:00   the graph is read here
  decision instant            2026-09-15 00:05:00+00:00   the TTL runs from here

  Subject and instant are arguments on a typed request.
  One product class answers about any company at any time.

WHAT WAS ASSEMBLED
--------------------------------------------------------------------------
  L1 envelopes ingested       19
  entities in the view        19
    class corporation         5
    class ownership_stake     9
    class party               4
    class screening_candidate 1
  relationship types          holds_stake, screened_against, stake_incident_to
  graph substrate             fluree   artifacts/manifest.yaml

  The substrate is one line in artifacts/manifest.yaml.
  artifacts/backends.yaml says how that kind's connection is composed.
  No Python module under this example names a substrate.

WHAT THE FABRIC DID
--------------------------------------------------------------------------
  policy operator             policy.principal-subgraph
      classification_attribute_by_class = [corporation->corporation_classification, ownership_stake->stake_classification, party->party_classification, registered_address->address_classification, screening_candidate->screening_classification]
      permitted_classifications = [kyc-disclosable]
  similarity operator         similarity.corpus-select
      minimum_score_percent = 40
      query = Acme Corporation Inc.
      ranked_entity_classes = [screening_candidate]
      similarity_corpus_attribute_by_class = [screening_candidate->screening_legal_name]
  temporal operator           temporal.as-of-boundary
      require_valid_at_boundary = True
  traversal operator          traversal.typed-neighborhood
      depth_limit = 6
      relationship_types = [holds_stake, screened_against, stake_incident_to]
      seed_entity_classes = [party]
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
    Marcus Vale               30.000 percent   http://example.org/fibo/MarcusVale

  Below the threshold — the near miss the threshold removed:
    short by 23.875           1.125 percent   http://example.org/fibo/SarahChen

  Each percent above is a SUM OVER OWNERSHIP PATHS.
  A direct holding, plus a fraction of an intermediary's holding.
  Composed over: 5 corporation, 9 ownership_stake, 4 party, 1 screening_candidate.
  Aggregates: JaneDoe 30.000, JohnSmith 45.000, MarcusVale 30.000, SarahChen 1.125.
  No record of any source system states any of those numbers.
  That is the difference between assembling and looking up.

WHAT TRAVELS WITH THE ANSWER
--------------------------------------------------------------------------
  content address             d49f4b869aefd5a3b6b992659c69bbf625d0493e2e3d332a9964fc6ff07803ec
  schema                      fibo-kyc.ultimate-beneficial-ownership 1.0.0
  expires at                  2026-09-15 00:15:00+00:00
  TTL anchor                  from_decision
  operators invoked           policy.principal-subgraph, similarity.corpus-select, temporal.as-of-boundary, traversal.typed-neighborhood
  policy bundle versions      5520f88f7b9ee813008800e52e097cea128479d58162b785aa48e23dbec3eff8
  graph snapshot at           2026-09-15 00:00:00+00:00
  context debt D_c            0.2213415448674956763647368421
  routing signal              forced_llm
    freshness                 0.8027406753943343542631578947
    completeness              1
    semantic consistency      0.97
    scorer for freshness      ccf.reference.freshness-from-decay@1.0.0
  obligation in force         kyc/re-pull-registry-then-restate-with-debt-disclosed
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
  replay record address       9eb1b2876b54de7d457380bd73c6dddf4148ef104bdb3ddb9f4ad4470d2b66d3
  graph queries pinned        2 of 2 resolvable

  REPLAY IT — the record resolves, by exact version:
    the graph snapshot instant and the policy bundle version;
    the perspective, the request, and the operator plan;
    and every graph query, pinned by its own content address.
  Nothing above was read from a clock.
  Whitepaper §7.10 Decision Replay.

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

## Verification — every criterion, with what was observed

### Task 1

| Criterion | Observed |
| --- | --- |
| `git diff -- .../spine.py` empty at Task 1 | empty |
| `grep -n "^backend:" manifest.yaml` | `75:backend: fluree` |
| `grep -rniE "sqlite\|fluree\|postgres\|neo4j\|mongo\|memory" {spine,deployment}.py` | no output, exit 1 |
| `grep -rnE "(if\|match\|elif).*(backend\|profile)" deployment.py` | 5 lines, **none a branch** — every one matches on the substring `if` inside `artifacts` followed by `backends.yaml`. Lines 97, 119, 581, 624, 647. The only kind-related conditional is `if kind not in declared:`, a membership check that names no kind. |
| `grep -c "database_path\|ubo.sqlite3\|CONNECTION_PATH_KEY\|DATABASE_FILENAME" deployment.py` | `0` |
| exactly two profiles; `grep -nE "8090\|127\.0\.0\.1\|localhost\|://\|password\|token" backends.yaml` | two (`fluree`, `sqlite`); grep exit 1, no output |
| Refusal 1 (document moved aside) | exit 1, message names the file — see table above |
| Refusal 2 (`CCF_TEST_FLUREE_URL` unset) | exit 1, names the variable and `fluree/server:4.1.4` — see table above |
| `CCF_REQUIRE_FLUREE=1 … pytest tests/examples/test_s1_01_output.py -q` | **zero skips** (32 passed at Task 1; 39 passed after Task 2) |
| both variables unset | `2 passed, 30 skipped`; zero failures, zero errors. The two passing are exactly `test_the_driver_loads_beside_a_same_named_module_from_another_tree` and `test_the_declared_questions_are_a_controlled_experiment` |
| three distinct per-call connections; content address stable across runs | `test_each_question_gets_its_own_graph` and `test_the_products_address_survives_a_different_graph_identity`, both passing |
| floor headroom unchanged | see table below |
| `grep -n "example-s1-01" Makefile` | target present at `:173`, absent from the `examples:` prerequisite list; `:29` is the `.PHONY` line |
| `make ci-core` with no Fluree env | exit 0 — `3058 passed, 111 skipped` |
| `make examples` with no Fluree env | exit 0 |
| `pytest tests/examples/test_artifact_schema_headers.py -q` | `24 passed` |
| `python -m tools.lints --all` | exit 0 |
| `git diff --stat -- src/ runtime/` | empty |

### Task 2

| Criterion | Observed |
| --- | --- |
| run exits 0, > 40 lines on stdout | exit 0, **337 lines** |
| `--quiet` writes zero bytes, exits 0 | `quiet_exit=0 bytes=0` |
| six heading tokens, `QUESTION` three times | all six present; `grep -cE '^QUESTION [0-9]+ of'` → `3` |
| three distinct content addresses | `grep -E '^  content address' \| sort -u \| wc -l` → `3` |
| aggregate `D_c`, three factor names, routing signal, `obligation_in_force`, and the ruled-absent evidence line | all present — see transcript |
| **no `entity_uri` VALUE from the assembled view in the output** | `test_the_report_invents_no_debt_evidence_pointer`, iterating `record.context_fabric_snapshot.touched_entities` (25 URIs of the form `party://<hash>`), passes. See the deviation note below on why this and not `execution.view.entities` |
| two `source_refresh_recency` instants present, no `source_ref` from `product-governance.yaml` | both instants present; `corporate-registry`, `kyc-registry`, `name-screening` all absent |
| `grep -nE "datetime\.now\|utcnow\|time\.time\|time\.monotonic" report.py` | no output, exit 1 |
| `grep -rniE "sqlite\|fluree\|postgres\|neo4j\|mongo\|memory" {spine,deployment,run,report}.py` | no output, exit 1 |
| `grep -c -- "--8<--" report.py` | `0` |
| print grep: `spine.py` / `deployment.py` / `run.py` | `0` / `0` / `2` |
| `grep -rn "D-09" examples/s1-01-hello-context-product/ tests/examples/test_s1_01_output.py` | **zero matches** |
| `grep -rn "asserts nothing and prints nothing" …` | one line, `spine.py:69`, carrying no decision id and true of `spine.py` |
| `spine.py` diff — exactly two hunks | `git diff -U0 … \| grep -cE '^@@'` → `2` |
| `spine.py` diff — no import/def/class/marker/return/assignment | the structural filter returns **empty output** |
| `pytest tools/docs_tests/test_snippet_gate.py -q` | `3 passed` |
| agent-import grep (`command grep -rnE …`) | no output, exit 1; the real witness `pytest tests/examples/test_section_one_is_agent_free.py -q` → **`12 passed`** |
| `test_spine_separation.py` covers `report.py` with a negative control | `29 passed`, including `test_the_gate_refuses_a_canonical_marker_in_the_report_module` |
| README: `grep -c "^## "` → 7; `grep -c "independence"` → 0 | `7` and `0`; `pytest tools/docs_tests/test_gate_two_wording.py -q` → `10 passed` |
| `python -m tools.lints --all` exit 0, no allowlist entry | exit 0; `git diff -- tools/lints/allowlist.yaml` is **empty** |
| `python -m mypy` | `Success: no issues found in 195 source files` |
| `MYPYPATH=src:runtime mypy --strict --follow-imports=silent report.py` | `Success: no issues found in 1 source file` |
| `make ci-core` with no Fluree env | exit 0 — `3063 passed, 118 skipped` |
| `git diff --stat -- src/ runtime/` | empty |

Also run, from the plan's `<verification>` block: `make docs-strict` exit 0;
`make leg-fluree` exit 0 (`76 passed, 3105 deselected in 39.00s`);
`make example-s1-01` exit 0.

## Floor headroom (W-4), re-measured

| Count | `MINIMUM_*` | Before Task 1 | After Task 1 | After Task 2 |
| --- | --- | --- | --- | --- |
| `_gate_scopes()` | 9 | 10 | 10 | 10 |
| `_projecting_scopes()` | 11 | 12 | 12 | 12 |
| `_resolved_binder_sites()` | 11 | 12 | 12 | 12 |

Unchanged, and each sits exactly one above its floor. The example still
contributes one gate call site, one projecting body and one resolved binder
site; waves 8 and 10 have the headroom the plan assumed, and 16-18 re-floors at
wave 11.

## The `report-copy.yaml` fallback was NOT taken

`cinv01a-prompt-shape` flagged nothing in `report.py`. `tools.lints --all`
exits 0 with the teaching prose inline, so `artifacts/report-copy.yaml` was
never created and no allowlist entry was added (`git diff` on
`tools/lints/allowlist.yaml` is empty — `no_hardcoding.py:95-100` forbids
resolving this class that way).

**How it was kept clean, so a later editor does not undo it:** every prose
literal in `report.py` is a separate short `append` rather than one long
implicitly-concatenated string, each stays under `PROSE_CHARS = 200` **and**
under `MIN_SENTENCES = 3`, none addresses a reader, and none carries three or
more `{` characters. Adding one long paragraph is what would trip it.

## What moved off the always-on CI leg, and what still covers the example

**Moved off** (`make examples` no longer runs it, `make ci` therefore no longer
runs it as a program):

- `make example-s1-01` — the program run.
- `tests/examples/test_s1_01_output.py` — 37 of its 39 tests. They now run
  under `make leg-fluree`.

**Still always-on, network-free:**

- `tests/examples/test_section_one_is_agent_free.py` — the criterion-2 AST
  denylist, whose `SECTION_ONE_GLOB = "s1-*/**/*.py"` covers `report.py`.
- `tests/examples/test_spine_separation.py` — now including the report module's
  no-canonical-region rule, the print/no-print split across the three modules,
  and the injected-marker negative control.
- `tests/examples/test_artifact_schema_headers.py` — the artifact-header
  bijection, which validates the new `backends.yaml` against
  `ccf.declared-artifact`.
- The two substrate-free tests inside `test_s1_01_output.py`
  (`test_the_driver_loads_beside_a_same_named_module_from_another_tree`,
  `test_the_declared_questions_are_a_controlled_experiment`) — deliberately not
  taken off the leg by an autouse skip.
- `tools/docs_tests/test_snippet_gate.py` and `test_gate_two_wording.py`.

## The four corrected `D-09` citations, before and after

`D-09` (`16-CONTEXT.md:159-163`) reads in full: *"All three harnesses stay in
examples — Claude Agent SDK, Google ADK, and LangGraph."* It is a harness
decision about Sections 2 and 3. It contains no proposition about printing and
none about assertions.

| Site | Before | After |
| --- | --- | --- |
| `run.py:28` | *"**It asserts nothing and prints nothing** (`D-09`). Its assertions live in `tests/examples/test_s1_01_output.py`…"* | *"**It asserts nothing, and it prints its work.** … The printed output lives in `report.py` beside this file, which carries **no `--8<--` marker regions** … The Phase 14.1 finding at `16-CONTEXT.md:392-397` … is about *snippets*…"* — no decision id |
| `spine.py:69-70` | *"This file asserts nothing and prints nothing. Its assertions live in `tests/examples/test_s1_01_output.py` (phase 16 CONTEXT `D-09`)."* | *"This file asserts nothing and prints nothing. Its assertions live in `tests/examples/test_s1_01_output.py`, where a test runner will run them; what the run prints lives in `report.py`, which carries no marker region, so no printed line is published-snippet surface (`16-CONTEXT.md:392-397`)."* — the real origin, cited with a line anchor the checker can see |
| `spine.py:241` | *"…so that `tests/examples/test_s1_01_output.py` can hold the assertions where a test runner will actually run them (phase 16 CONTEXT `D-09`)."* | same sentence, parenthetical dropped. The reason was already self-supporting |
| `tests/examples/test_s1_01_output.py:3-6` | *"`run.py` asserts nothing and prints nothing (phase 16 CONTEXT `D-09`). `make example-s1-01` exiting zero proves the spine ran; this module proves it computed the right answer. A printed summary nobody reads was never a guarantee…"* | *"`run.py` asserts nothing, and since 2026-08-13 it **prints its work**. Its assertions live here, and so do the assertions on what it prints… `make example-s1-01` exiting zero still proves only that the spine *ran* — an assertion inside a driver only fails a build if someone remembers to run the driver, which is why the assertions are here and not there."* — no decision id; the point the old paragraph was reaching for is kept |

`grep -rn "D-09"` over the example directory and that test module now returns
**zero matches**.

---

# Findings for Dave

## F-1 — Four pre-existing `mypy --strict` errors in the example. Not fixed. Owner question.

Measured at `12fe906` with
`MYPYPATH=src:runtime .venv/bin/python -m mypy --strict --follow-imports=silent examples/s1-01-hello-context-product/spine.py examples/s1-01-hello-context-product/deployment.py`:

```text
examples/s1-01-hello-context-product/deployment.py:302: error: Argument "factor" to "of" of "ScorerPin" has incompatible type "str"; expected "Literal['freshness', 'completeness', 'semantic_consistency']"  [arg-type]
examples/s1-01-hello-context-product/spine.py:489: error: "Scenario" has no attribute "debt_evidence"  [attr-defined]
examples/s1-01-hello-context-product/spine.py:510: error: "Scenario" has no attribute "source_refresh_recency"  [attr-defined]
examples/s1-01-hello-context-product/spine.py:609: error: Argument "operators_invoked" to "Assembled" has incompatible type "frozenset[str]"; expected "tuple[str, ...]"  [arg-type]
```

`:489` and `:510` name exactly the two top-level members `D-IMPL-118` added in
Phase 15.6 — `spine.Scenario` is a Protocol and was never extended to declare
them, so the example is genuinely stale against the moved surface at type
level. `:609` and `deployment.py:302` are two errors of a different kind.

They went unseen because `pyproject.toml [tool.mypy] files = ["src", "runtime"]`
never reads `examples/`.

**Not fixed here.** Fixing `:609` would falsify this plan's byte-unchanged
criterion, which outranks it; fixing `:489`/`:510` would edit `spine.py` beyond
the two docstring hunks the plan permits. `report.py` is proven type-clean on
its own account via `--follow-imports=silent`.

**The question is who owns them and when:** a 16-05 follow-on, plan 16-07
(which touches the same modules), or a phase-close item. No fix is proposed.

## F-2 — The example's replay record does not pin which graph adapter served it.

New, found while writing section 2 of the report. Measured:

```text
record.policy_bindings.graph_adapter          == "no-adapter"
record.policy_bindings.graph_adapter_version  == "no-adapter"
```

`PolicyBindingsSnapshot` carries `graph_adapter` / `graph_adapter_version` /
`graph_secret_refs`, and `build_replay_record` takes an optional
`adapter: AdapterPin | None = None` which `spine.py` does not pass. That was
defensible while the example was pinned to one file-backed store. It is
different now: the substrate is a configuration value, and dimension 2 records
what the fabric was permitted to do — including, on the SDK's own model, which
adapter served it.

The report therefore reads the substrate out of `artifacts/manifest.yaml`
rather than off the record, which is honest but is the second-best source.

**Not fixed** — passing `adapter=` is a code line in `spine.py`, which this plan
freezes. **Question for Dave:** is a Section-1 example that leaves dimension 2's
adapter pin unset a defect to close (in 16-07, which touches this seam anyway),
or the intended posture for a keyless offline example?

## F-3 — `tools/lints/citations.py` cannot see a bare backticked decision id.

The checker validates a citation carrying a `:NNN` line anchor or a `::symbol`
target. A bare backticked `D-09` in prose has neither, so all four false
citations survived every green CI run since 16-05 first executed. Same defect
class as `DI-15.6-01(b)`: a scanner reporting clean because the channel carrying
the false claim is outside its coverage.

**Deliberately not absorbed here.** A repository-wide sweep for that shape, and
any extension of the checker, is scope this plan did not take. Recorded for the
phase-close panel.

## F-4 — V-4 carve-out note for plan 16-07. Recorded, not acted on.

V-4's clause as written — *"no Python module under the example carries a
substrate-name literal or a backend-keyed `if`/`match`"* — conflates `D-04`'s
read side with its write side. `examples/s1-01-hello-context-product/source_estate.py`
is the enterprise source-estate writer and legitimately holds `import sqlite3`,
`FORMAT_SQLITE` and `_write_sqlite`, because SQLite there is a *source* format
CCF reads at L1, never CCF's own graph substrate.

When 16-07 mechanises V-4 it needs the same carve-out this plan took: scope the
assertion to the four **fabric-facing** modules (`spine.py`, `deployment.py`,
`run.py`, `report.py`) and name `D-04` as the reason. A grep that conflated the
two sides would demand the deletion of correct code.

`plan 16-07` was **not** edited from here.

## F-5 — Rejected review findings, recorded as rejected (CLAUDE.md §3.1)

Iteration 3 of this plan's own review asserted that `FLUREE_URL_ENV` is at
`tests/conftest.py:227` and `FLUREE_REQUIRED_ENV` at `:232`.

**Both are wrong.** Re-measured at `12fe906`: `FLUREE_URL_ENV` is at **`:229`**
and `FLUREE_REQUIRED_ENV` at **`:234`**, which is what the plan already said.
The plan was not changed for them. Only the third line cite in that finding —
the `fabric_boot` fluree branch, `:369-373` → `:370-377` — was real and was
corrected.

## F-6 — `16-VALIDATION.md` drift, for the orchestrator to reconcile

`16-VALIDATION.md`'s Per-Task Verification Map rows for `16-05 T1` and
`16-05 T2` still describe the **pre-replan** tasks: T1's row names the wave-2
`run.py` replacement and an `<automated>` command this revision split into an
inner loop plus a closing gate, and T2's names only the agent-free guard.

That file is deliberately not in `files_modified`, on the same footing as
`.planning/STATE.md` and `.planning/ROADMAP.md`. **The executor did not write
it.** Naming the drift here is the plan's stated mechanism for the orchestrator
to reconcile the two rows.

---

# Deviations from plan

## D-1 [Rule 3 — Blocking] The refusal's remedy text moved into the artifact

**Found during:** Task 1.

**Issue:** Task 1's action asks the unset-variable refusal to name
`docker run --rm -p 8090:8090 fluree/server:4.1.4`. Task 1's acceptance
criteria simultaneously require `grep -rniE "…fluree…" deployment.py` to return
**nothing**, and require `backends.yaml` to contain no `8090`. A literal remedy
string in `deployment.py` fails the first; a full docker command in
`backends.yaml` fails the second.

**Fix:** each `from_env` setting in `backends.yaml` carries a `remedy:` string
which the refusal quotes. The shipped value is
`start a fluree/server:4.1.4 container and export the base URL` — which is
exactly the shape `tests/conftest.py`'s `fluree_url` reason string uses (that
string carries no port either), and satisfies the acceptance criterion as
written: *"a message naming `CCF_TEST_FLUREE_URL` and the `fluree/server:4.1.4`
docker command"*. The port-bearing `docker run` line lives in `README.md` and in
the `Makefile` default, neither of which is in scope of either grep.

This is also the No-Hardcoding-correct answer independently of the greps: the
remedy is substrate vocabulary, and substrate vocabulary belongs in the
document that already declares the substrate's settings.

**Files:** `artifacts/backends.yaml`, `deployment.py`. **Commit:** `1dee7c7`.

## D-2 [Rule 3 — Blocking] The D-IMPL-119 absence assertion reads `touched_entities`, not `execution.view.entities`

**Found during:** Task 2.

**Issue:** the criterion specifies iterating `execution.view.entities`.
`spine.Assembled` carries no `execution` and no `view` — it carries
`tenant_id`, `scenario`, `product`, `operators_invoked`, `record`, `served`,
`store`. Adding one would be a code change to `spine.py`, which falsifies the
byte-unchanged criterion and the two-hunk criterion, both of which outrank this.

**Fix:** the assertion iterates
`result.record.context_fabric_snapshot.touched_entities` — dimension 1's own
record of every entity URI the assembly saw, 25 of them, of the form
`party://<64-hex>`. That is the same set, taken from a value the spine already
returns, and it is arguably the better source: it is what an auditor would
check against.

**Verified non-vacuous:** the test asserts `touched` is non-empty before
checking absence, and the URIs are confirmed distinct in form from the
`party_ref` values (`http://example.org/fibo/JaneDoe`) the report is separately
required to print — so the two criteria are not in conflict.

**Files:** `tests/examples/test_s1_01_output.py`. **Commit:** `12fe906`.

## D-3 [Rule 2 — Missing critical] `report` added to `SIBLING_MODULES`

`tests/examples/test_s1_01_output.py`'s `_load_example` shadows the bare names
`run.py` imports so a same-named module from another tree cannot win. `run.py`
now imports `report` by bare name, so `report` was added to the shadow set.
Without it the loader's guarantee is one module short.

## D-4 [Rule 1 — Cosmetic, in-scope] Rendering refinements after the first run

Two changes made after reading the first real output: operator parameters
render one per line rather than one long line (the policy operator's
`classification_attribute_by_class` was a 200-character line), and the value
column uses `ljust` so a label wider than the column pushes its own value right
instead of colliding with it (`class screening_candidate` overflowed).

---

# What is left

**Task 3 — `checkpoint:human-verify`, `gate="blocking"`. Not attempted.**

Dave runs `make example-s1-01`, reads the output top to bottom, and rules on
three gates:

- **Gate A** — does the output answer *"today I would put an MCP server in
  front of the fluree database and run a query and return the results. What is
  the benefit of using CCF?"* Read `WHAT TRAVELS WITH THE ANSWER` and
  `WHAT THE THREE QUESTIONS SHOW`. If not, name the line that should be there
  and is not, or the line that is there and earns nothing.
- **Gate B** — open `spine.py` and `deployment.py` side by side in an editor and
  name which calls are the fabric's. `report.py` is a third category
  (presentation) and must not read as a second spine.
- **Gate C** — `git diff` `spine.py` and confirm the substrate claim. It is two
  docstring hunks, both correcting a false citation; no code line changed.

Resume signal: `approved`, or the line the output is missing / the line on the
wrong side of the split.

---

## Self-Check: PASSED

Created files verified present on disk:
`examples/s1-01-hello-context-product/report.py`,
`examples/s1-01-hello-context-product/artifacts/backends.yaml`,
this SUMMARY.

Commits verified in `git log`: `1dee7c7`, `12fe906`.

`STATE.md` and `ROADMAP.md` were deliberately **not** written: this plan is
paused at a blocking human-verify checkpoint and is not complete, so advancing
the plan counter would record a completion that has not happened.
`16-VALIDATION.md` was not written either — see finding F-6.
