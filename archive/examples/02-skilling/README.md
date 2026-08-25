# examples/02-skilling — grant, exercise, refuse, revoke: capability under governance, and the agent never changes

## What this demonstrates

Skilling — channel 2 of the two-channel specialization model
(Specialization axes / skilling: channel 1 fixes who the agent is (six
axes: archetype, context contract, perspective, policy regime,
half-life/debt profile, instruction bindings); channel 2 — skilling —
governs what it can currently do (CLAUDE.md §6.2 — SDK extension)). A
skill is granted to a running agent through the Control Plane / Data
Plane split (the Control Plane declares what the fabric may do —
versioned config, policy, artifacts, also the audit plane; the Data
Plane executes within those constraints (whitepaper §7.8)), exercised,
and revoked — while an impermissible grant is refused by the tier-1
governance compatibility check, every transition is audited, and the
skill-set in force lands in the Decision Replay record (the
five-dimension record — fabric snapshot, policy bindings, model
version, perspective conditioning, generation path — that lets a
decision be reproduced exactly (whitepaper §7.10)).

The single most important assertion: `artifacts/agent-definition.yaml`
is byte-identical before and after the whole cycle. Capability changed
four times; identity never moved.

## Run it

```sh
make example-02
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/02-skilling/run.py
```

`run.py` is the **call spine** and nothing else — it asserts nothing and
prints nothing. Exit code 0 means the spine executed, which does include
the governance refusal: an admitted impermissible grant raises there
rather than being asserted away. The correctness guarantee lives in
`tests/examples/test_skilling_output.py`, where a test runner can fail a
build (D-09); that module's docstring maps every relocated assertion to
the pre-rewrite line it came from and names the two audit-by-construction
checks it exists for.

Check the assertions:

```sh
PYTHONPATH=src:runtime python -m pytest tests/examples/test_skilling_output.py
```

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run the test module, review the failures, then deliberately
> edit `artifacts/expected.yaml` and the `expected_excess`,
> `expected_output` and `expected_grant_actions` blocks in
> `artifacts/skilling-scenario.yaml` to match what you reviewed —
> regeneration is a reviewed event, landed in the same commit as the
> enrichment, with the commit body summarizing what changed and why. No
> `make regen-*` targets exist, and none will be added.

## The story

A clinical-trials-operations deployment (`helix-trials`) runs an
enrollment-analytics agent — declared in
`artifacts/agent-definition.yaml` from
the `analytics_insights` archetype (Archetype vs agent: an archetype is
a functional template the SDK ships as code; an agent is a declared,
versioned Control Plane artifact the Agent Factory produces from one —
CLAUDE.md §6.1, SDK extension). Its axis-4 policy regime carries the
governance envelope: see `artifacts/agent-policy-regime.yaml`, key
`declaration.skill_governance.permitted_scopes` — exactly one scope,
`enrollment-read`, and deliberately not `protocol-write`.

The run proceeds in six audited movements:

1. **A minimal fabric boots and serves one Context Product** (a typed,
   validated, replay-ready unit of decision context the fabric derives
   and serves — a contract, not a stored record; whitepaper §6.3, §7.6)
   from the events in `artifacts/events.yaml` — including a restricted
   unblinded cohort the policy operator substitutes out before anything
   downstream sees it.
2. **Three skills register in the Control Plane catalog** — one
   document each, enumerated by `artifacts/skilling-scenario.yaml`, key
   `declaration.catalog_documents`: a permitted local callable
   (`enrollment-metrics`), a permitted-but-never-granted MCP resource
   (`site-status-feed`), and a tool requiring `protocol-write`
   (`protocol-amendment-writeback`). Registration is discovery; a grant
   is capability — the catalog is wider than any agent's bound set.
3. **The permitted grant binds.** The audit log records
   `grant_requested`, then `grant_effective`. The agent's bound surface
   now holds exactly one skill — not the registered-and-grantable
   `site-status-feed`, which stays invisible (§7.3 seam 2: skills the
   agent has not been granted do not exist from its point of view).
4. **The skill is exercised and replay captures the set in force.**
   The replay record's dimension 4 carries the content hash of the
   in-force grant set — a decision replays against the skills the agent
   actually had, not the skills it has now.
5. **The impermissible grant is refused.** The tier-1 check compares
   the entry's `requirements.required_scopes` against the regime
   envelope and returns a typed refusal naming the exact excess —
   `protocol-write`, declared as the expected outcome in
   `artifacts/skilling-scenario.yaml`, key
   `declaration.expected_excess.scopes`. The audit log
   records `grant_requested`, `grant_refused`; nothing binds; the
   in-force set identity does not move.
6. **The permitted grant is revoked** — `grant_revoked` lands on the
   log, and the *same constructed agent object* loses the skill at
   invoke time: binding resolves from ledger state, not from
   construction-time capture.

Then the closing assertion: the definition file's bytes, the
definition's content hash, and its registered version set are all
unchanged. Five capability transitions, zero identity transitions.

## Artifact-by-artifact

Every document is exactly one artifact class and carries a
`# yaml-language-server: $schema=` header naming the schema that
validates it (`make schema-headers DIR=examples/02-skilling/artifacts`).

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/manifest.yaml` | What this deployment puts in force: tenant, backend kind, and every artifact with its key, class and `role`. **Three operator-parameters documents, not four** | `[ADAPT]` `tenant_id`, keys, paths, deployment class ids; `[MECHANISM]` `backend`, `resolution_spec_key`, `policy_bundle_key`, `artifacts`, `path`, `key`, `class_id`, `role` |
| `artifacts/agent-definition.yaml` | The agent definition — six specialization axes, and nothing else | `[ADAPT]` tenant, names, product-class names, role values; `[MECHANISM]` the six axis field names, `schema_version`, `artifact_version`, `ref` |
| `artifacts/agent-policy-regime.yaml` | The axis-4 regime carrying the `skill_governance` envelope the tier-1 check reads | `[ADAPT]` regime name, classifications, scope identifiers; `[MECHANISM]` `skill_governance`, `permitted_scopes`, `grant_requires_approval` |
| `artifacts/agent-debt-profile.yaml` | The axis-5 tolerance the agent replays against | `[ADAPT]` calibrated values; `[MECHANISM]` the three profile keys |
| `artifacts/skill-catalog-*.yaml` | One catalog entry each — three types on show: `local_callable`, `mcp`, `tool` | `[ADAPT]` skill names, scopes, descriptions, bindings; `[MECHANISM]` `skill_type`, `binding`, `requirements`, `argument_schema` |
| `artifacts/skilling-scenario.yaml` | The channel-2 script: which catalog documents to register, the two grant documents, the expected refusal excess, the audited action sequence, the callable output content and the dispatch arguments/expected output | `[ADAPT]` every name and value; `[MECHANISM]` `semver`, `class_id`, `declaration` and the grant field names |
| `artifacts/agent-registration.yaml` | The Control Plane keys the author-versioned artifacts register under | `[ADAPT]` key paths; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/resolution-spec.yaml` | The deployment vocabulary: entity and relationship resolution rules | `[ADAPT]` classes, types, attribute names; `[MECHANISM]` `entity_rules` / `relationship_rules` field names |
| `artifacts/policy-bundle.yaml` | The policy bundle the *fabric* boots under | `[ADAPT]` `class_id`, regime, jurisdiction, classifications; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/operator-parameters-*.yaml` | One document per registered operator category — traversal, temporal, policy | `[ADAPT]` class names, relationship types, classifications, the depth value; `[MECHANISM]` the parameter field names |
| `artifacts/product-class.yaml` | The served class, and the three `required_operator_keys` Gate 2 compares against | `[ADAPT]` schema name, MAX_TTL key, operator key names; `[MECHANISM]` every field name |
| `artifacts/product-governance.yaml` | MAX_TTL seconds, product TTL, plan id, replay record class | `[ADAPT]` `class_id`, every value; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/perspective.yaml` | The Π role-conditioning the product is served under | `[ADAPT]` principal id, role; `[MECHANISM]` `principal_id`, `role` |
| `artifacts/events.yaml` | The L1 signal envelopes, including the multi-source lineage pair and the restricted cohort | `[ADAPT]` all payload content; `[MECHANISM]` envelope field names |
| `artifacts/decision.yaml` | The temporal boundary and the decision instant — also the injected clock, which is why it is read one line before the manifest | `[ADAPT]` `class_id`, both instants; `[MECHANISM]` `semver`, `class_id`, `declaration` |
| `artifacts/expected.yaml` | What the served product should contain, and how many operators this deployment registers | `[ADAPT]` `class_id`, every value; `[MECHANISM]` `semver`, `class_id`, `declaration` |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.8 — Control Plane as the governing and audit plane
- whitepaper §7.10 — Decision Replay, dimension 4 (perspective
  conditioning, here extended with the grant-set hash)
- CLAUDE.md §6.2 channel 2 — skilling: governed grants, replay capture,
  the policy-regime envelope (SDK extension)
- CLAUDE.md §6.4 — No-Hardcoding: scopes, entries, grants and expected
  outputs are all artifact values (SDK extension)
- CLAUDE.md §7.3 seam 2 — ungranted skills do not exist from the
  agent's surface (SDK extension)

## What to change first

The `artifacts/skill-catalog-*.yaml` documents **are** the capability
surface:

- add your own catalog entry as a new document and name it in
  `skilling-scenario.yaml`'s `catalog_documents` — four skill types ship
  (`tool`, `local_callable`, `mcp`, `peering`); requirement scopes are
  opaque identifiers your policy regimes must permit. On the next run
  you will see them register; nothing binds until you add a grant
  document under `grants:` in the scenario artifact.
- widen (or narrow) `skill_governance.permitted_scopes` in
  `artifacts/agent-policy-regime.yaml` — that is an axis-4 change and
  therefore a new agent version, which is exactly the channel separation
  on show. Widen it to include `protocol-write` and the spine itself
  raises — the example *requires* the refusal to fire — so update
  `expected_excess.scopes` and `expected_grant_actions` together, as a
  reviewed event.
- set `grant_requires_approval: true` to route grants through a tier-2
  `ApprovalSink` of your own (the example's sink raises if consulted,
  proving tier 2 stays out of an auto regime).

## What would fail

| Invariant | What would fail here |
| --- | --- |
| channel separation (CLAUDE.md §6.2) | the grant/exercise/revoke cycle would change `artifacts/agent-definition.yaml` (asserted byte-identical), the definition's content hash, or its registered version set |
| tier-1 governance is non-waivable (D-IMPL-29) | the `protocol-write`-requiring grant would bind; the refusal is a typed returned value naming the exact excess scopes |
| audit-by-construction (CLAUDE.md §6.2) | a grant or revocation without its `grant_*` action on the one Control Plane audit log, in order: requested, effective, requested, refused, revoked |
| skill-set in force in replay | dimension 4's `grant_set_hash` would not equal the content hash of the in-force grant set at the exercise step |
| live bound view | a revoked skill would still dispatch — binding is resolved from ledger state at invoke time, on the same constructed agent |
| skills the agent lacks do not exist (CLAUDE.md §7.3 seam 2) | an ungranted (`site-status-feed`), refused, or revoked skill would be visible from the agent's surface instead of raising the typed `SkillNotBound` |
| no execution surface for the SDK | the local callable would be imported from a dotted path in an artifact rather than resolved from the key the composition root registered |
| tier 2 stays out of an auto regime (D-IMPL-29) | the approval sink would be consulted although the regime declares `grant_requires_approval: false` (the sink raises if touched) |
| No-Hardcoding (CLAUDE.md §6.4) | a scope identifier, skill entry, grant value or expected output appearing in `run.py` — `make lint` rejects it |
| the operator set is the deployment's decision | a fourth operator appearing in the registry, or `required_operator_keys` naming one this fabric does not register — the manifest's artifact set is the only thing that decides |
