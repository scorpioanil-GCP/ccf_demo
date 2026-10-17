<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# sk-01 — declare and govern an agent's skills

**What a skill is.** An agent is a named, versioned definition, not code. A
*skill* is one governed capability the agent may use. Here it is
`collateral-ask`: "ask the bank's collateral product (cp-06-canonical) about one
facility." The bank's **policy regime** says which skills an agent *may* hold.
A **grant** says which skills it *does* hold. Every grant, and every refused
grant, goes into the audit log.

**Why it matters to a bank.** Three questions can be answered without trusting
the agent's own account of itself:

1. What was this agent allowed to do?
2. Did it try to take more than that?
3. Which agent made a given decision, and which skills did it hold at the time?

The decision record answers the first part of the third question outright:
dimension 4 names the agent by content hash, versioned URI and archetypes
(`D-IMPL-385`). It answers the second part by identity: dimension 4 carries the
content hash of the skill-set in force, and a child row in dimension 5 names the
skill and the grant it was asked under — but only when the child was admitted; a
refused child's row names neither (measured on the estate, FINDINGS.md). Turning
the skill-set hash back into a list of skills needs the grant artifacts, and
today those live only in the in-memory Control Plane (SK01-F-04). A skill's
requirements are not pinned in the record at all (SK01-F-03).

Built under Dave's ruling of 2026-10-16 16:58 MST (option A: build the honest
version now; the design and the ruling are the gate; README only). The ruling,
and the design findings it rests on, are recorded in `docs/DECISIONS.md` under
"sk-01 — the skills example, option A RULED 2026-10-16 16:58 MST"; the findings
themselves, parked, are in `FINDINGS.md` beside this README.

## What this demonstrates

One command, five movements:

| movement | what it shows | where it lives |
| --- | --- | --- |
| **1 · Skills declared at start** | The agent `collateral-analyst` is granted `collateral-ask` as the product opens. The audit log shows the grant was **requested** and took **effect**. | `ccf_config.yaml`: `policy.skill_governance`, `producers`, `skills`, `agent`, `grants` |
| **2 · The record names who decided and what they held** | After one real question, the decision record's dimension 4 names the agent (content hash, versioned URI, archetypes) and the identity of its skill-set; the child row in dimension 5 names the skill and the grant it was asked under, when the child was admitted. `run.py` holds both to the audit log from movement 1 and prints `yes` or `NO` for each check. | `run.py::movement_two` |
| **3 · What a model would see** | The agent is handed to the Claude Agent SDK adapter. **No model is called** and nothing is spawned. The tool list is **empty, and that is correct**: a "go ask another product" skill is never a tool a model calls — the product asks, and admits the answer under the producer's controls. | `tool_surface.py` (glue — SK01-F-02) |
| **4 · An over-reaching grant is refused at start-up, and audited** | A second deployment ships version 1.1.0 of the skill, which also wants `collateral-ledger.write`. The regime permits reading only, so the product **refuses to open** (`DeclaredGrantRefused`, check `tier-1-policy-compatibility`). The audit log shows `grant_requested` followed by `grant_refused`. | `variants/over-reach/` |
| **5 · Not yet available** | The first four items under "What this does not show", each printed from `artifacts/not-yet-available.yaml` with the finding or gap that records it. | |

**The skill chain is five declarations**, and the regime, the catalog entry and
the grant agree **by construction at open**, not by care: the SDK derives the
skill's catalog entry from `skills:`, requests each `grants:` entry through the
grant ledger against `policy.skill_governance`, and refuses by name at open on
an over-reach (movement 4), on a grant naming an undeclared skill, and on a
skill that states a type other than `mcp_product` (SK01-F-01).

**Scopes are labels.** Tier 1 compares the skill's required scopes with the
regime's permitted scopes. Nothing else in this example enforces "read" against
"write": the label `collateral-ledger.write` is refused because the regime does
not list it, not because anything here could write a ledger.

### What this does not show

- **Granting or revoking a skill while the product runs.** Every grant here is
  declared in `ccf_config.yaml` and requested as the product opens. The SDK's
  grant ledger can grant and revoke later, but no door an example can use is
  authorized to do it yet (gap 1).
- **A granted skill appearing as a model tool, or a revoked one disappearing —
  not yet possible (SK01-F-01).** This agent's only skill asks another product,
  and that kind of skill (`mcp_product`) is never a model tool
  (`src/ccf/skills/toolsurface.py::HARNESS_EXPOSABLE_SKILL_TYPES`). The empty
  list in movement 3 is the correct answer, not a gap. A tool-type skill
  (`tool`, `mcp`, `local_callable`) would appear there — but today an example
  cannot declare or grant one: the supported path derives every declared skill
  as `mcp_product` and refuses any other stated type
  (`src/ccf/deployment/config.py::_PAVED_SKILL_TYPE`). That constant's own
  comment names a second route: a tool-type skill declared in its own catalog
  document and handed to a composite through the low road's `children=` hatch.
  That route is closed to an example for a different reason. The hatch is
  refused beside a declared `agent:`/`skills:`
  (`src/ccf/products/product.py::_refuse_half_wired_composite`), so nothing on it
  requests a grant for you. The grant ledger takes only two capabilities: the
  `skill.grant` door's, which no example can reach (gap 1), or the
  composition-time `DeclaredSkillGrant`. The SDK mints the second only for
  `grants:` entries that name `skills:` entries, which are always `mcp_product`;
  minting one in example code would be a bypass, and this example's offline test
  forbids it. So neither road can grant a tool-type skill from an example today,
  and "appear / disappear" is not shown at all, not even as two openings: both
  lists would be empty.
  `tests/examples/test_sk_01_offline.py` asserts the refusal as shipped, so it
  turns red the day this becomes possible.
- **Replaying this decision.** The record names the agent, its version, its
  skill-set and the grant behind the child. Replaying a *composite* decision
  through `replay_decision` is not available yet (gap 3).
- **An agent on its own.** Today an agent that holds grants and asks another
  product exists only inside a composite product. The small product around
  `collateral-analyst` — its own identity leg, its debt rule, its Π — exists for
  that reason, not because the brief needs it (gap 4, SK01-F-05).
- **A model call.** No model is called. The tool list comes from the adapter
  alone, with no network.
- **Reading the skills back from the record alone.** The record carries the
  skill-set's content hash, not its members, and a skill's requirements are not
  pinned in it. So the record alone can neither list the skills behind that hash
  nor recheck the tier-1 decision; both need the grant artifacts, which live
  only in the in-memory Control Plane (SK01-F-03, SK01-F-04).

*Now available:* the decision record names the composing agent and the
skill-set it held (`D-IMPL-385`).

## Run it

**Run against the estate on 2026-10-16**, read-only (`fibo-v2` and `ccf_v2` on
192.168.4.76), with cp-06-canonical's door started locally from branch
`replay-evidence-383`. The demonstration question was served; the
expired-evidence variation was refused `composite-child-refusal`, its child row
`ineligible` with the producer's `ttl-refusal` / `ttl-bounds`; the
outside-the-boundary variation was refused `asked-at-outside-temporal-bound`.
All three exited 0, and in each one dimension 4 named the declared agent and its
skill-set. The estate tests (E1–E5 in `tests/examples/test_sk_01_estate.py`)
passed on their first run. No transcript is published here (README only, per
Dave's 2026-10-16 ruling); what follows is the command and what each movement
prints. Run it to see the real text.

1. **`make venv`** — the first command in a fresh clone. It installs the locked
   dependencies, including `claude-agent-sdk`, which movement 3 imports (and
   never starts).
2. **Start the producer's door** in its own terminal. It reads the estate with
   its own `CCF_CP_06C_*` variables (see that example's README) and prints
   `READY <port>`:

   ```sh
   export CCF_CP_06C_DOOR_TOKEN=<a token you choose>
   .venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
   ```

3. **Export this example's four variables.** The DSN must be **read-only**:
   nothing this example runs writes to the store it reads, and a role that could
   write would make that a promise rather than a guarantee. Both libpq spellings
   work (`host=… user=… password=…` and `postgresql://…`); libpq also reads
   `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD` itself, so the DSN can be as short as
   `dbname=<database>`. A short DSN connects as whatever role `PGUSER` names, so
   it meets the read-only requirement only when that role is itself read-only;
   this example sets no read-only session of its own. The schema is the v2
   namespace, `ccf_v2` — not the v1 namespace `ccf_dataprep/.env` names.

   ```sh
   export CCF_SK_01_POSTGRES_DSN=<read-only DSN>   CCF_SK_01_POSTGRES_SCHEMA=ccf_v2
   export CCF_SK_01_COLLATERAL_URL=http://127.0.0.1:<port>/mcp
   export CCF_SK_01_COLLATERAL_TOKEN=<the same token the door was started with>
   ```

4. **Run it:** `make example-sk-01`, or `make -s example-sk-01` — `-s` suppresses
   make's echo of the recipe, the only thing that differs between the target's
   output and the program's.
5. **Without make:**

   ```sh
   PYTHONPATH=src:runtime:examples/sk-01-declare-and-govern-agent-skills \
     .venv/bin/python examples/sk-01-declare-and-govern-agent-skills/run.py
   ```

**Variations worth trying** (each request parameter is optional; omitted, the
demonstration question in `artifacts/question.yaml` is asked):

- `make example-sk-01 FACILITY=--facility=FAC-D3D1A4 LEI=--lei=B3BS7ACMDUWISF18KY76`
  — a facility whose collateral evidence has expired at the demonstration
  instant. cp-06-canonical refused this facility `ttl-refusal` / `ttl-bounds`
  when its own estate gates were measured (2026-09-18, `D-IMPL-341`;
  `tests/examples/test_cp_06_canonical_output.py::test_a_producer_refusal_for_expired_evidence_crosses_as_an_ineligible_child`),
  so the brief should refuse, and dimension 4 should **still name the same agent
  and skill-set**: the record names who decided on a refusal too. *Measured
  2026-10-16:* the brief refused exactly so, and E3 asserts this path.
- `make example-sk-01 ASKED_AT=--asked-at=2026-09-07T10:00:00+00:00` — outside
  the one-hour temporal boundary, so the brief refuses
  `asked-at-outside-temporal-bound`, again with dimension 4 naming the agent.
  This path touches no store, and it is the one record check that runs without
  the estate (O6 in `tests/examples/test_sk_01_offline.py`).

**Exit codes.** The program exits **0** whenever every movement behaves as
declared — **including a refused question**: a governed refusal is the SDK
working, and both variations above exit 0. It exits **1** when the over-reach
variant *opens* (a defect) or any movement-2 record check prints `NO`: the
dimension-4 agent and skill-set checks, or the dimension-5 child-row checks —
which include an admitted child row that carries no grant, and a served brief
with no admitted child row for the class it requires. A missing environment variable
stops the program before movement 1 with the remedy `ccf_environment.yaml`
declares; that is a non-zero exit, and a configuration error, not a refusal. Any
other unhandled error also exits non-zero and, like a missing variable, is not a
governed refusal.

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

That applies here to three declarations in `ccf_config.yaml`: the one-hour
`temporal_boundary`, the `demonstration_serve_instant` (2026-09-07T12:05Z, the
same instant cp-06-canonical serves on), and the `half_life` / `debt_profile`
values of the brief's own leg — and to the demonstration instant pinned in
`artifacts/question.yaml`.

## The story

**Movement 1** opens the product into a Control Plane registry `run.py` owns, so
it can read the audit log afterwards. Opening registers the regime, the agent
definition and the derived catalog entry, and requests the one declared grant
through the grant ledger. `run.py` prints the agent, the skill's required scopes
beside the regime's permitted scopes, and the two audit events for the grant —
`grant_requested`, then `grant_effective` — with the grant's hash.

**Movement 2** asks the demonstration question: BGC Group, Inc.
(`2549001IGRCG4F0RLD36`) and its facility `FAC-5B8418`, at 2026-09-07T12:00Z.
cp-14 measured this collateral child **admitted** on 2026-10-11, and it was
admitted again when this example was run against the estate on 2026-10-16. The brief's own leg reads the obligor's identity row;
the collateral figures are the child's, read off the admitted contract. Then the
record: the child row names `collateral-ask@1.0.0` and its grant hash (on a
producer's refusal, it names the producer's refusal kind and reason instead, and
no skill or grant), and dimension 4
names the agent and the skill-set. Three checks are printed — the agent in the
record is the declared agent; the skill-set in the record is the set identity of
the grants the audit log recorded effective at open; and the grant on each child
row is the grant the audit log recorded effective for the skill that row names.
A missing grant is tolerated only on a row that was **not** admitted (a producer
that refused, or could not be reached): it is printed as such, and dimension 4
still names the skill-set. An admitted row without a grant prints `NO`, and so
does a **served** record with no admitted row for the required class. A refused
record may have no child row at all: the temporal boundary refuses before any
child is asked, and that is printed, not failed.

**Movement 3** must come after movement 2: before the first question, the agent
cannot be constructed (SK01-F-02). It builds the agent, hands it to the Claude
Agent SDK adapter, and prints the bound skill with its type, the model tools
(none), `allowed_tools` (empty) and the types that *would* appear.

**Movement 4** opens `variants/over-reach/` on a fresh registry. It is refused at
open, by name, before anything is composed; `run.py` prints the check and the
excess scope, and the audit log's `grant_requested` and `grant_refused` for the
variant's own grant hash.

**Movement 5** prints what is not yet available, with the finding or gap that
records each.

## Artifact-by-artifact

| file | role |
| --- | --- |
| `ccf_config.yaml` | The Control Plane document. The five skill-chain declarations, the one-child composite they live in, and the three illustrative calibrations. The skill sits in one delimited block at the end. |
| `ccf_environment.yaml` | The NAMES the identity store's DSN and schema are read from, and the remedy for each. No value. |
| `variants/over-reach/` | The same two documents with only the skill block changed (version 1.1.0, one extra scope). `test_sk_01_offline.py` holds the copy equal. |
| `artifacts/question.yaml` | The demonstration question, the brief's intent and freshness, and what the child is asked in cp-06-canonical's own vocabulary. |
| `artifacts/source-vocabulary.yaml` | The one table, its key and the four columns the identity leg reads (the result names are restated in `acquisition.py`; FINDINGS.md §2 (e)). |
| `artifacts/projection.yaml` | Which members of the child's payload the brief prints. |
| `artifacts/harness.yaml` | The adapter's constructor values. `model` is a disclosed placeholder: it is placed on the carrier, and no model is called. |
| `artifacts/not-yet-available.yaml` | Movement 5's lines. |
| `acquisition.py` | The identity leg; imports no `ccf`. |
| `deployment.py` | `acquire`, `assess`, and the one question mapping. |
| `projection.py` | Π over the graph view and the admitted child. |
| `produce.py` | One `open_product` call, and the named plan factory. |
| `tool_surface.py` | **Glue (SK01-F-02).** The only file allowed `GrantLedger(`, `SkillCatalog(` and `AgentFactory(`. |
| `run.py` | The five movements and their checks. |
| `FINDINGS.md` | SK01-F-01 … F-05, the observed friction, and the parked gaps, in the six close-report sections. |

## Whitepaper / CLAUDE.md sections exercised

- **CLAUDE.md §6.2** — the two channels: the agent's identity (channel 1, the
  `agent:` section and its derived axes) and its skills (channel 2, `skills:` and
  `grants:`), with the tier-1 policy-compatibility check and audit capture.
- **CLAUDE.md §6.4** — the agent is a definition artifact declared in
  `ccf_config.yaml`'s `agent:` section. The paved road
  (`src/ccf/products/product.py::_derive_consumer_chain`) registers and reads
  that definition and binds grants to it, but never constructs an `Agent`, and
  nothing in `src/` or `runtime/` calls the Agent Factory. The one construction
  through the Agent Factory is this example's glue, `tool_surface.py`
  (SK01-F-02), for movement 3 only. Prompts and model values live in artifacts;
  some source and attribute names are restated in code, and FINDINGS.md lists
  each (§2 (e)).
- **CLAUDE.md §7.3** — seam 2 (skill exposure) is *called*, not demonstrated:
  the Claude Agent SDK adapter's `expose_skills` runs on the granted agent, with
  no model call, and correctly returns nothing, because `collateral-ask` is an
  `mcp_product` skill, which is never a model tool. Neither half of the seam's
  contract is shown — a granted skill surfaced as a tool, and an ungranted skill
  absent. Today an example cannot declare a tool-type skill on the supported
  path, so seam 2 cannot be demonstrated from an example (SK01-F-01).
- **CLAUDE.md §9** — reads the estate and seeds nothing; the illustrative
  calibrations are disclosed.
- **Whitepaper §7.10.1** — the Decision Replay record: dimension 4 (perspective
  conditioning: the agent and its skill-set) and dimension 5 (the child row).
- **Whitepaper §6.3 / §7.6** — the Context Product Contract the brief and its child
  are served under.

## What to change first

1. **The regime and the skill** — `policy.skill_governance.permitted_scopes` and
   `skills.collateral-ask.requirements.required_scopes`. Widen the skill past the
   regime and the product refuses to open; that is movement 4.
2. **The agent** — `agent.name` and `agent.archetypes`. The record's dimension 4
   follows.
3. **The producer** — `producers.collateral` names the producer's identity and
   tenant, and the two environment variable NAMES its endpoint and credential come
   from.
4. **The question** — `artifacts/question.yaml`.

## What would fail

- **An over-reaching skill that opened** — `test_o1_…` in
  `tests/examples/test_sk_01_offline.py`, and `run.py` exits 1.
- **A declared grant not requested and put in force at open** — `test_o2_…`.
- **A tool-type skill becoming declarable** — `test_o3_…` goes red by design; the
  "not yet possible" above is then out of date.
- **The variant drifting from the deployment** — `test_o4_…`.
- **SDK machinery creeping out of the glue file** — `test_o5_…`.
- **The record no longer naming the agent or its skill-set** — O6 in
  `tests/examples/test_sk_01_offline.py`, the one estate-free example gate: it
  asks a question refused for its instant (no store is touched) and holds
  dimension 4 to the declared agent and the grants audited at open. The SDK-level
  gate is `tests/products/test_dimension_four_records_the_agent.py`.
- **The record naming the wrong agent, skill-set or grant, on a served question,
  on the expired-evidence refusal, or on a second opening** — E1, E2, E3 and E5 in
  `tests/examples/test_sk_01_estate.py`, which run only with the estate variables
  set (they skip otherwise), and `run.py` exits 1. All five passed
  on their first run against the estate (2026-10-16, read-only). The design's
  severing — the agent removed from the paved resolver in
  `src/ccf/products/product.py::_derive_consumer_chain` — turned E1, E2, E3 and E5
  red on their assertions (`'no-agent' == …`, `'no-grants' == …`); E4 does not
  depend on it and stayed green. The file was restored from saved bytes and its
  hash checked.
- **An admitted child row without its grant** — `test_o7_…` holds `run.py`'s
  child-row check estate-free; E2 holds it on the estate.
- **The tool surface showing a skill it should not** — E4, a weak gate today
  (two empty lists; FINDINGS.md, SK01-F-01).
- **FINDINGS.md or an artifact the table above lists going missing** —
  `test_every_listed_artifact_exists_and_findings_holds_every_cited_id` checks
  every listed path exists and that FINDINGS.md holds every SK01-F id this
  example cites, each PARKED.
