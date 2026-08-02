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

The single most important assertion: `artifacts/agent.yaml` is
byte-identical before and after the whole cycle. Capability changed
four times; identity never moved.

## Run it

```sh
make example-02
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/02-skilling/run.py
```

Exit code 0 means every assertion held — **including the governance
refusal**; the example fails if the tier-1 check does not fire. CI
treats nonzero as red.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-02`, review the assertion output, then
> deliberately edit the `expected:` block in
> `artifacts/controlplane.yaml` and the `expected_excess` /
> `expected_output` blocks in `artifacts/skills.yaml` to match what you
> reviewed — regeneration is a reviewed event, landed in the same
> commit as the enrichment, with the commit body summarizing what
> changed in the output and why. No `make regen-*` targets exist, and
> none will be added.

## The story

A clinical-trials-operations deployment (`helix-trials`) runs an
enrollment-analytics agent — declared in `artifacts/agent.yaml` from
the `analytics_insights` archetype (Archetype vs agent: an archetype is
a functional template the SDK ships as code; an agent is a declared,
versioned Control Plane artifact the Agent Factory produces from one —
CLAUDE.md §6.1, SDK extension). Its axis-4 policy regime carries the
governance envelope: see `artifacts/agent.yaml`, key
`skill_governance.permitted_scopes` — exactly one scope,
`enrollment-read`, and deliberately not `protocol-write`.

The run proceeds in six audited movements:

1. **A minimal fabric boots and serves one Context Product** (a typed,
   validated, replay-ready unit of decision context the fabric derives
   and serves — a contract, not a stored record; whitepaper §6.3, §7.6)
   from the events in `artifacts/events.yaml` — including a restricted
   unblinded cohort the policy operator substitutes out before anything
   downstream sees it.
2. **Three skills register in the Control Plane catalog** (see
   `artifacts/skills.yaml`, key `skills`): a permitted local callable
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
   `artifacts/skills.yaml`, key `expected_excess.scopes`. The audit log
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

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/agent.yaml` | The agent definition — six specialization axes, including the axis-4 regime with the `skill_governance` envelope | `[ADAPT]` tenant, names, scope identifiers, thresholds; `[MECHANISM]` the six axis field names, `referenced_artifacts` structure, `skill_governance` field names |
| `artifacts/skills.yaml` | The skill catalog entries (three types on show: `local_callable`, `mcp`, `tool`), the grant documents, the expected refusal excess, the callable output content, dispatch arguments/expected output | `[ADAPT]` skill names, scopes, descriptions, output values; `[MECHANISM]` `skill_type`, `binding`, `requirements`, `argument_schema` and the top-level block names |
| `artifacts/controlplane.yaml` | Fabric bundle: keys, policy bundle, operator parameters, product class, perspective, decision instants, the `expected:` block | `[ADAPT]` all values including `expected:`; `[MECHANISM]` every field name |
| `artifacts/ontology.yaml` | The deployment vocabulary: entity/relationship resolution rules, classification attributes | `[ADAPT]` classes, types, attribute names; `[MECHANISM]` `entity_rules` / `relationship_rules` field names |
| `artifacts/events.yaml` | The L1 signal envelopes, including the multi-source lineage pair and the restricted cohort | `[ADAPT]` all payload content; `[MECHANISM]` envelope field names |

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

`artifacts/skills.yaml` **is** the capability surface:

- add your own catalog entries under `skills:` — four skill types ship
  (`tool`, `local_callable`, `mcp`, `peering`); requirement scopes are
  opaque identifiers your policy regimes must permit. On the next run
  you will see them register; nothing binds until you add a grant
  document under `grants:`.
- widen (or narrow) `skill_governance.permitted_scopes` in
  `artifacts/agent.yaml` — that is an axis-4 change and therefore a new
  agent version, which is exactly the channel separation on show. Widen
  it to include `protocol-write` and the refusal assertion in `run.py`
  will fail — the example *requires* the refusal to fire, so update
  `expected_excess.scopes` and the grant expectations together, as a
  reviewed event.
- set `grant_requires_approval: true` to route grants through a tier-2
  `ApprovalSink` of your own (the example's sink raises if consulted,
  proving tier 2 stays out of an auto regime).

## What would fail

| Invariant | What would fail here |
| --- | --- |
| channel separation (CLAUDE.md §6.2) | the grant/exercise/revoke cycle would change `artifacts/agent.yaml` (asserted byte-identical), the definition's content hash, or its registered version set |
| tier-1 governance is non-waivable (D-IMPL-29) | the `protocol-write`-requiring grant would bind; the refusal is a typed returned value naming the exact excess scopes |
| audit-by-construction (CLAUDE.md §6.2) | a grant or revocation without its `grant_*` action on the one Control Plane audit log, in order: requested, effective, requested, refused, revoked |
| skill-set in force in replay | dimension 4's `grant_set_hash` would not equal the content hash of the in-force grant set at the exercise step |
| live bound view | a revoked skill would still dispatch — binding is resolved from ledger state at invoke time, on the same constructed agent |
| skills the agent lacks do not exist (CLAUDE.md §7.3 seam 2) | an ungranted (`site-status-feed`), refused, or revoked skill would be visible from the agent's surface instead of raising the typed `SkillNotBound` |
| no execution surface for the SDK | the local callable would be imported from a dotted path in an artifact rather than resolved from the key the composition root registered |
| tier 2 stays out of an auto regime (D-IMPL-29) | the approval sink would be consulted although the regime declares `grant_requires_approval: false` (the sink raises if touched) |
| No-Hardcoding (CLAUDE.md §6.4) | a scope identifier, skill entry, grant value or expected output appearing in `run.py` — `make lint` rejects it |
