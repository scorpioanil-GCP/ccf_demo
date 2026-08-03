# examples/external/00-hello-context — a bank's credit context, consumed by agents that have never heard of CCF

## What this demonstrates

CCF as a **black box behind a URL**. A small financial-services fabric
serves one Context Product (a typed, validated, replay-ready unit of
decision context the fabric derives and serves — a contract, not a stored
record; whitepaper §6.3, §7.6) through an authenticated MCP front door
(MCP integration — Model Context Protocol as an integration surface,
Pattern 3 in the whitepaper; bidirectional, ingress and egress, in the
SDK; whitepaper §8.3, CLAUDE.md §7.1 — SDK extension: bidirectional).
Four client legs consume it, and **none of them imports CCF** (the family
charter's zero-CCF-imports rule — see [`../README.md`](../README.md)):

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

## Run it

```bash
make example-ext-00
```

Raw fallback: `PYTHONPATH=src:runtime python examples/external/00-hello-context/run.py`.
Exit code 0 means all six assertions above held — servers came up,
every leg consumed the front door, the refusal path fired, and the
reproduction was byte-equal.

Live variants (opt-in, never CI): `make example-ext-00-live-anthropic`
and `make example-ext-00-live-adk` run the same client files against the
real vendor APIs — unset base-URL redirects, real `ANTHROPIC_API_KEY` /
`GOOGLE_API_KEY` from your environment, live model names from
`artifacts/experience.yaml` (`live_mode`). Same code, zero CI/live
branches: the SDKs' own base-URL environment variables are the only
switch. Determinism in CI comes from `replay_server.py` replaying the
versioned `fixtures/` verbatim at the transport level.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-ext-00`, review the assertion output, then
> deliberately edit the `expected:` block in `artifacts/product.yaml` to
> match what you reviewed — regeneration is a reviewed event, landed in
> the same commit as the enrichment, with the commit body summarizing
> what changed in the output and why. The model-API fixtures under
> `fixtures/` have their own reviewed regeneration procedure — see
> [`fixtures/README.md`](fixtures/README.md).

## The story

`serve.py` boots the whole fabric from `artifacts/`: one borrower, one
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
`artifacts/experience.yaml`, key `agent_exposure`), so agent invocation
visibly refuses rather than silently not existing.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/ontology.yaml` | Tenant id, entity classes and resolution rules, relationship types, similarity-corpus and classification attribute maps | `[ADAPT]` tenant id, classes, attribute names; `[MECHANISM]` rule field names the resolution spec interprets |
| `artifacts/events.yaml` | The L1 signal envelopes — the borrower, facility, and four financial signals | `[ADAPT]` all payload vocabulary and timestamps; `[MECHANISM]` envelope field names |
| `artifacts/controlplane.yaml` | Operator parameters, policy bundle, decision instants, TTLs, Control Plane keys, artifact class names | `[ADAPT]` parameter values, instants, TTLs; `[MECHANISM]` key names and `artifacts:` class keys |
| `artifacts/product.yaml` | The one product class, its plan id, the entity focus, and the `expected:` self-check block | `[ADAPT]` schema name, plan id, focus, expected values; `[MECHANISM]` `product_class` / `focus` / `expected` field names |
| `artifacts/experience.yaml` | Server name, auth issuer/resource/scope, tool names AND prose, empty agent exposure, live-mode model names | `[ADAPT]` all prose, URLs, scope and model names; `[MECHANISM]` `auth` / `tools` / `agent_exposure` / `live_mode` structure |
| `artifacts/tokens.yaml` | The SYNTHETIC token table: one active analyst entry, one revoked entry backing the 401 assertion | `[ADAPT]` token values, client ids, scopes; `[MECHANISM]` `tokens` entry field names |
| `fixtures/*.json` | Recorded two-turn model-API conversations making both LLM legs deterministic offline | `[ADAPT]` by reviewed regeneration only (`fixtures/README.md`); `[MECHANISM]` filename ordinals and path-suffix routing |

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
`artifacts/ontology.yaml` (your `tenant_id`, entity classes, resolution
and relationship rules), `artifacts/events.yaml` (your source events),
`artifacts/controlplane.yaml` (operator parameters that do visible work
on your data), and `artifacts/product.yaml` (your product class, focus
entity, and — after a reviewed run — its `expected:` block). Then update
the tool prose in `artifacts/experience.yaml` to describe your product.
On the next `make example-ext-00` you should see the same six PASS lines
over your vocabulary: the client legs need no changes at all, which is
the point — they never knew the domain existed.

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
| Gate-admitted products only | `serve.py`'s self-check: the served payload must match `artifacts/product.yaml` `expected:` before the server ever announces `READY` |
