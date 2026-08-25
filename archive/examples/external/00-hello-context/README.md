# examples/external/00-hello-context — a bank's credit context, consumed by agents that have never heard of CCF

## What this demonstrates

> **Historical, and still green.** This example's client legs target the
> **pre-Phase-17 surface** — an authenticated MCP front door over **HTTP with
> a bearer token**, reached through `CCF_MCP_URL` and `CCF_TOKEN`. It predates
> `ccf.client`, the `mcp+stdio` transport adapter, the Phase 18.1 binding in
> which a deployment declares its own server program, and the Phase 19 wire
> form. It is **not deprecated**: it stays CI-green, and the eight assertions
> below — auth refusal, dual serve-path byte equality, byte-equal replay
> reproduction — are exercised every run and are the reason it was kept rather
> than retired.
>
> **Where it lives now, and what "CI-green" means.** In Phase 23 this tree
> moved from the suite into `archive/examples/external/00-hello-context/`
> (`D-IMPL-189`, `D-IMPL-193`), and its `make` target was deleted with the
> other thirteen (`D-04`, `D-IMPL-195` ruling 1). `D-IMPL-193` clarified
> `CLNT-30`/`H-14`'s *"stays CI-green"* to mean **its tests keep passing** —
> not that it stays a member of the always-on `examples:` aggregate. They do:
> `tests/examples/test_ext00_hardening.py`,
> `tests/examples/test_ext00_serve_output.py` and
> `tests/examples/test_ext00_fixture_schemas.py` still execute this tree on
> every commit, and the same ruling forbids retiring them rather than
> re-pointing them. Run it directly with
> `PYTHONPATH=src:runtime python archive/examples/external/00-hello-context/run.py`.
> **The marking obligation was NOT lifted by the move** — only the tree's
> location changed.
>
> **`examples/hw1-harness-clients/` is the canonical foreign-harness → MCP-door
> demonstration going forward**: one Google ADK client, one Anthropic Agent SDK
> client and one LangGraph client reaching one `mcp+stdio` door and landing on
> one content address. Start there; read this one for the HTTP-and-bearer
> posture and for what a Context Product looks like from outside the fabric.
> (Phase 20, `H-14`. The Phase 16 client programs that sat beside this example
> were retired out of `examples/` entirely — see
> `docs/retired/16-external-consumers/README.md`.)

CCF as a **black box behind a URL**. A small financial-services fabric
serves one Context Product (a typed, validated, replay-ready unit of
decision context the fabric derives and serves — a contract, not a stored
record; whitepaper §6.3, §7.6) through an authenticated MCP front door
(MCP integration — Model Context Protocol as an integration surface,
Pattern 3 in the whitepaper; bidirectional, ingress and egress, in the
SDK; whitepaper §8.3, CLAUDE.md §7.1 — SDK extension: bidirectional).
Four client legs consume it, and **none of them imports CCF** (the family
charter's zero-CCF-imports rule — see
[`examples/external/README.md`](../../../../examples/external/README.md)):

1. `client_bare.py` — a plain `mcp` client, no LLM. Also retrieves the
   product's lineage and its Decision Replay record (the five-dimension
   record — fabric snapshot, policy bindings, model version, perspective
   conditioning, generation path — that lets a decision be reproduced
   exactly; whitepaper §7.10) over the same authenticated surface.
2. `client_anthropic.py` — a textbook Anthropic-SDK tool-use agent.
3. `client_adk.py` — a textbook Google ADK agent with an `McpToolset`.
4. Claude Code / Claude Desktop / Cowork — a **docs-only leg**: register
   the running server in `.mcp.json` (see "The story") and consume it
   interactively; no code at all.

`run.py` orchestrates the fabric and all runnable legs offline and
asserts, every CI run: legs exit 0; a revoked bearer token is refused
with 401; the client legs contain zero CCF imports; this README keeps its
seven-heading shape (by exact name and order); lineage and the replay
record were retrieved over MCP; the templated resource and the
`get_context` tool serve byte-identical product JSON; `tools/list`
advertises exactly the artifact allowlist; and the served bytes are
reproduced **byte-equal** from the replay record alone, fabric-side.

`tests/examples/test_ext00_serve_output.py` owns what the fabric
*computed*: that the assembled product matches
`artifacts/expected.yaml` — a document nothing in `serve.py` reads, so
either side changing alone fails — that the lineage and the
five-dimension replay record cross the authenticated wire to a client leg
**byte-unchanged**, and that the zero-CCF-import assertion actually
refuses when a leg is given a CCF import rather than merely passing. The
example running clean proves the spine executes; that module proves it is
right.

## Run it

```bash
make example-ext-00
```

Raw fallback: `PYTHONPATH=src:runtime python examples/external/00-hello-context/run.py`.
Exit code 0 means all eight assertions above held — servers came up,
every leg consumed the front door, the refusal path fired, and the
reproduction was byte-equal.

The correctness suite runs separately and needs no vendor key:
`PYTHONPATH=src:runtime pytest tests/examples/test_ext00_serve_output.py`.

Live variants (opt-in, never CI): `make example-ext-00-live-anthropic`
and `make example-ext-00-live-adk` run the same client files against the
real vendor APIs — unset base-URL redirects, real `ANTHROPIC_API_KEY` /
`GOOGLE_API_KEY` from your environment, live model names from
`artifacts/experience.yaml` (`live_mode`). Same code, zero CI/live
branches: the SDKs' own base-URL environment variables are the only
switch. Determinism in CI comes from `replay_server.py` replaying the
versioned `fixtures/` verbatim at the transport level.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run the test module, review what changed, then deliberately
> edit `artifacts/expected.yaml` to match what you reviewed —
> regeneration is a reviewed event, landed in the same commit as the
> enrichment, with the commit body summarizing what changed in the output
> and why. The model-API fixtures under `fixtures/` have their own
> reviewed regeneration procedure — see
> [`fixtures/README.md`](fixtures/README.md).

## The story

`serve.py` boots the whole fabric from `artifacts/` in **one call** —
`load_and_boot` reads `artifacts/manifest.yaml`, which enumerates every
document this deployment puts in force, parses and validates each against
the artifact class the manifest declares for it, registers the
`role: register` ones and boots on the resulting pins. A second call,
`build_operator_registry`, turns the four operator-parameter documents
into the operator chain. Between them they replace what used to be a
YAML loader, a timestamp helper, a resolution-spec marshaller, an
envelope marshaller, a registration prologue and a 61-line inline
operator block.

What that fabric holds: one borrower, one
revolving credit facility, four financial signals ingested through the
L1–L6 layers (the fabric's six layers: L1 signal ingestion → L2 assembly,
the only writer → L3 graph → L4 operators → L5 projection → L6 product
delivery; whitepaper §7.1) into the Context Graph (the fabric's typed
state `G(E, R, T, P, Π, L)` — entities, relationships, time, policy,
projection, and lineage as one governed graph; whitepaper §5.2, §7.3).
The four Context Operators (typed, composable, read-only functions over
the graph in four categories — Traversal, Temporal, Policy, Similarity;
whitepaper §7.4) each do visible work, a Projection (Π — the
role-conditioned transformation that turns graph state into the view a
given consumer is entitled to see; whitepaper §7.5) interprets the
result, and only a gate-admitted product is served.

The serving surface is the **Experience server**, not the raw egress
server — a deliberate choice worth naming. CLAUDE.md §8.3 names the MCP
server as the Experience Layer's front door for external agent runtimes,
and the Experience surface is the only one that carries the
bearer-token auth machinery this example requires from day one. The two
surfaces also differ in URI scheme: the egress role serves product
resources, while the ArtifactStore (the Protocol-based persistence
surface for CCF artifacts — snapshots, products at rest, replay records,
Control Plane bundles; CLAUDE.md §7.4 — SDK extension) uses its own
versioned `artifact://` URIs. Do not conflate the three — egress,
experience, and artifact addressing are distinct surfaces.

Auth posture: bearer auth is **on from day one**; there is no anonymous
mode. The tokens in `artifacts/tokens.yaml` are SYNTHETIC — illustrative
values for a runnable demonstration, never production credentials. A
real deployment supplies its own `TokenSourceProtocol` implementation
backed by its identity infrastructure, and clients reference tokens via
environment variables — never inline values.

Every externally-served product is replay-recorded **before the bytes
leave** — the Decision Replay record and a serve-request record (who
asked, what they asked for, when) land in the file-backed ArtifactStore
under `.store/` with zero client obligation. `run.py` then proves the
claim: it resolves the record at its exact content address, replays it
against a fabric rebuilt from the same artifacts, and asserts the
reproduced product is byte-equal to what was served.

The fourth leg is registration, not code. With `serve.py` running (note
its `READY <port>` line), add this to a project's `.mcp.json` for Claude
Code — Claude Desktop and Cowork accept the same HTTP-server shape in
their connector settings:

```json
{
  "mcpServers": {
    "first-meridian-credit-context": {
      "type": "http",
      "url": "http://127.0.0.1:<port>/mcp",
      "headers": {
        "Authorization": "Bearer ${CCF_TOKEN}"
      }
    }
  }
}
```

Export `CCF_TOKEN` (the active token from `artifacts/tokens.yaml`) in
the environment Claude Code launches from — the `${CCF_TOKEN}` reference
keeps the token value out of the checked-in file. The tools the fabric
advertises (`get_context`, `get_lineage`, `get_replay_record`) then
appear in Claude's tool list, discovered from the server exactly as the
coded legs discover them. One deliberate note: `list_agents` returns an
**empty directory** — this deployment exposes no agents on the front
door (hello-world scope; the declaration lives in
`artifacts/experience.yaml`, key `declaration.agent_exposure`), so agent
invocation
visibly refuses rather than silently not existing.

## Artifact-by-artifact

One artifact class, one document — which is what makes an honest
`# yaml-language-server: $schema=` header on the first line of each
possible, and it is why a bundle carrying two classes had to be split:
either header would mark the other class's keys as errors in your editor.
Every document below carries one, pointing either at the SDK's committed
schema for its class or at the committed `DeclaredArtifact` envelope for
a class the SDK does not own.

| Artifact | Role | What it declares | Yours to edit vs mechanism |
| --- | --- | --- | --- |
| `artifacts/manifest.yaml` | — | The tenant, the backend *kind*, and every other document by `path`, `key`, `class_id` and `role`. No DSN and no database path: a connection string is an environment value and must not be content-hashed into the audit plane | `[ADAPT]` tenant id, keys, paths, non-`ccf.` class ids; `[MECHANISM]` every field name and the `role` values |
| `artifacts/resolution-spec.yaml` | register | Entity classes, identity and attribute keys, typed relationship rules. Closed-world over resolution rules only | `[ADAPT]` classes, match keys, attribute names; `[MECHANISM]` rule field names |
| `artifacts/events.yaml` | load | The L1 signal envelopes — the borrower, facility, and four financial signals, in the SDK's own envelope vocabulary. `load` is FIXED by the SDK: registering raw events would put them in replay dimension 2 | `[ADAPT]` all payload vocabulary and timestamps; `[MECHANISM]` envelope field names |
| `artifacts/policy-bundle.yaml` | register | The regime, jurisdiction and permitted classifications stamped onto every claim at assembly | `[ADAPT]` every declared value; `[MECHANISM]` `semver` / `class_id` / `declaration` |
| `artifacts/operator-parameters-{traversal,temporal,policy,similarity}.yaml` | register | One document per operator category, each read by exactly one consumer — including the classification map (policy) and the corpus map (similarity) | `[ADAPT]` queries, thresholds, class names, depth; `[MECHANISM]` the field names each category's contract declares |
| `artifacts/perspective.yaml` | register | The Π role-conditioning, verbatim into replay dimension 4 | `[ADAPT]` principal id and role; `[MECHANISM]` both key names |
| `artifacts/product-class.yaml` | register | The one product class, its schema lane, TTL anchor, assembly mode, MAX_TTL key, and `required_operator_keys` — the authored declared side of the lineage gate | `[ADAPT]` schema name, lane, key, operator key names; `[MECHANISM]` field names and enum values |
| `artifacts/product-governance.yaml` | register | The values the SDK declines to own: the TTL ceiling, the product TTL, the corpus version identity, the plan id, and the two ArtifactStore class names | `[ADAPT]` every declared value; `[MECHANISM]` envelope keys |
| `artifacts/focus.yaml` | register | The one entity `get_context` will serve, and the decision the context informs. Registered because it scopes what the front door may hand out | `[ADAPT]` the entity ref and decision label; `[MECHANISM]` envelope keys |
| `artifacts/decision.yaml` | load | This run's temporal boundary and `now`. Declared instants, never clock reads — which is what makes the byte-equal reproduction possible | `[ADAPT]` both instants; `[MECHANISM]` envelope keys |
| `artifacts/expected.yaml` | load | What the deployment expects the served product to contain. Read by the test module and by nothing in the serving path | `[ADAPT]` every declared value; `[MECHANISM]` envelope keys |
| `artifacts/experience.yaml` | register | Server name, auth issuer/resource/scope, tool names AND prose, the allowlist, empty agent exposure, live-mode model names | `[ADAPT]` all prose, URLs, scope and model names; `[MECHANISM]` `auth` / `tools` / `tool_allowlist` / `agent_exposure` / `live_mode` structure |
| `artifacts/tokens.yaml` | load | The SYNTHETIC token table: one active analyst entry, one revoked entry backing the 401 assertion. `load`, never `register` — credential material must not reach the audit plane | `[ADAPT]` token values, client ids, scopes; `[MECHANISM]` entry field names |
| `fixtures/*.json` | — | Recorded two-turn model-API conversations making both LLM legs deterministic offline | `[ADAPT]` by reviewed regeneration only (`fixtures/README.md`); `[MECHANISM]` filename ordinals and path-suffix routing |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §6.3, §7.6 — the Context Product contract and its delivery
- whitepaper §7.1 — the L1–L6 layered path the fabric runs end to end
- whitepaper §7.4, §7.5 — the four operator categories and Π
- whitepaper §7.10 — the five-dimension replay record; byte-equal
  reproduction asserted every run
- whitepaper §8.3 (Pattern 3) — Context Products over MCP
- CLAUDE.md §7.1 — MCP as the Experience Layer access surface (SDK
  extension)
- CLAUDE.md §7.4 — the ArtifactStore holding replay and serve records
  (SDK extension)
- CLAUDE.md §8.3 — the MCP server as the external front door (SDK
  extension)
- CLAUDE.md §6.4 — the No-Hardcoding Rule: all prose, names, tokens,
  and parameters live in the artifacts

## What to change first

Move the example to your domain by editing, in order:
`artifacts/manifest.yaml` (your `tenant_id`; the entry list changes only
if you add or drop a document), `artifacts/resolution-spec.yaml` (your
entity classes and relationship rules), `artifacts/events.yaml` (your
source events), the four `artifacts/operator-parameters-*.yaml` documents
(parameters that do visible work on your data),
`artifacts/product-class.yaml` and `artifacts/product-governance.yaml`
(your product class and its governance values), `artifacts/focus.yaml`
(the entity you serve), and — after a reviewed run —
`artifacts/expected.yaml`. Then update the tool prose in
`artifacts/experience.yaml` to describe your product.

On the next `make example-ext-00` you should see the same eight PASS
lines over your vocabulary, and the test module should stay green once
`expected.yaml` matches what you reviewed. The client legs need no
changes at all, which is the point — they never knew the domain existed.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| Bearer auth on from day one (no anonymous mode) | `run.py` PASS 2: the revoked token from `artifacts/tokens.yaml` must be refused with HTTP 401; a server that stopped enforcing auth fails CI |
| Zero CCF imports in client legs (family charter) | `run.py` PASS 3: a static grep over `client_*.py` for `import ccf` / `from ccf_runtime` fails the run on any match |
| Seven-heading README template | `run.py` PASS 4: the seven `## ` headings on this file must match the template names, in order (`README_HEADINGS` in `run.py`) |
| Lineage and replay readable by clients over MCP | `run.py` PASS 5: the bare leg's output must show `operators_invoked` and `content_generation_path` retrieved over the front door |
| One serialization across both serve paths | `run.py` PASS 6: the templated Experience resource and the `get_context` tool must return byte-identical product JSON in one authenticated session |
| Allowlist is the whole advertised surface | `run.py` PASS 7: `tools/list` must equal `tool_allowlist` from `artifacts/experience.yaml` — a tool registered outside the artifact fails the run |
| Replay record lands before bytes leave; byte-equal reproduction | `run.py` PASS 8: the record resolved from `.store/` at its exact content address must replay to the served bytes; any drift in artifacts, operators, or state raises a divergence |
| No-Hardcoding Rule (CLAUDE.md §6.4) | `make lint`: prompt prose, tool descriptions, tokens, model names, or thresholds appearing in any `.py` here fail the CI lint |
| Gate-admitted products only | `serve.py` narrows the gate result with `match`/`case ServableProduct()` and raises on a refusal. `ServableProduct` is not constructible outside `run_gates`, so nothing external can ever see an ungated product |
| The fabric computed the declared answer | `test_ext00_serve_output.py`: the assembled payload — and the payload a client leg actually received over MCP — must match `artifacts/expected.yaml`, which nothing in the serving path reads |
| Lineage and replay survive the wire | `test_ext00_serve_output.py`: the lineage block and the five-dimension record the bare leg reads back must be byte-identical to the ones the test process assembled for itself |
| The zero-import guard still refuses | `test_ext00_serve_output.py`: the guard is run against copies of the legs with a CCF import injected, and must raise. A grep that matched nothing would otherwise stay green forever |
