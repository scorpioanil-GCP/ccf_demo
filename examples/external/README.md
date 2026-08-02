# examples/external — the external-consumer family charter

> "The beauty of CCF is it's a black box to the client caller if I want
> it to operate that way."

This directory is a distinct example **family**, unified by a
*consumption model* rather than a domain (Phase 13.1 D-01): an agent
built entirely **outside** CCF — its own harness, its own loop —
consumes decision-ready, typed Context Products (a Context Product is a
typed, validated, replay-ready unit of decision context the fabric
derives and serves — a contract, not a stored record; whitepaper §6.3,
§7.6) by pointing at the CCF MCP egress surface (MCP is the Model
Context Protocol, the open standard by which agent runtimes discover
and call external tools/resources; CCF uses it as its primary egress
front door — CLAUDE.md §7.1, §8.3; whitepaper §8.3 Pattern 3). The
existing suite examples `00`–`08` are unchanged and demonstrate CCF's
*internal* mechanism; this family demonstrates the **primary adoption
path**: CCF as governed context infrastructure behind a URL, never a
framework the client must adopt.

## The zero-CCF-imports rule

Client code in this family imports **nothing from CCF** (D-06). No
`ccf` imports, no `ccf_runtime` imports, no CCF-shaped helper modules.
The only CCF knowledge a client has is:

1. an MCP server URL (`CCF_MCP_URL`), and
2. a bearer token (`CCF_TOKEN`).

Each client leg must read as a textbook example of *its own harness* —
a plain `anthropic`-SDK agent, a plain Google ADK agent, a plain `mcp`
client. If a reviewer cannot hand a client file to an engineer who has
never heard of CCF and have it read as idiomatic harness code, the leg
fails the charter. Every example's `run.py` asserts this mechanically
(a grep for CCF imports in `client_*.py` is part of the assertion
suite).

Everything CCF-shaped — the fabric, artifacts, the MCP egress server,
auth, serve-side replay — lives on the **server side** of each example
(`serve.py` plus `artifacts/`, self-contained per example, D-04). The
fabric still records a replay-ready serve record for every product
served (snapshot, policy bindings, lineage — whitepaper §7.10), with
zero client-side obligation; lineage and the replay record are
themselves readable by clients over the same MCP surface.

## The band map (D-02)

| Band | Domain | Status |
| --- | --- | --- |
| `00-hello-context` | Hello world — minimal financial-services scenario: one product, one decision the served context visibly changes | Phase 13.1 |
| `10`–`19` | Financial-services depth progression (credit review, covenant monitoring, policy-pressure scenarios) | Reserved — future phases |
| `50+` | The SituationalIntelligence family | Reserved — future phases |

New domains slot into unused bands without renumbering existing
examples. The progression story is deliberate: hello world now → deep
financial services (10-band) → SituationalIntelligence (50-band).

## Client-leg conventions

Every example in this family follows the multi-leg pattern
(structural analog: `examples/03-harness-portability`):

- **Leg naming:** one file per harness, `client_<harness>.py` —
  `client_bare.py` (generic `mcp` client, no LLM),
  `client_anthropic.py` (pure Anthropic-SDK agent),
  `client_adk.py` (Google ADK agent with the CCF MCP server registered
  as a toolset). A fourth, docs-only leg registers the server with
  Claude Code / Claude Desktop / Claude Cowork via a `.mcp.json`
  snippet in the example README — a first-class leg, not a footnote.
- **Env-var-only configuration, zero code branches:** client legs read
  `CCF_MCP_URL` and `CCF_TOKEN` from the environment. CI determinism is
  achieved by redirecting the *model API* base URL via the harness's
  own env var (e.g. `ANTHROPIC_BASE_URL`) to a local replay server
  serving recorded, versioned fixture responses — the client code
  contains no `if CI:` branches and runs unmodified in live mode when
  the redirect var is unset and real keys are supplied (D-08/D-09).
  Fixture regeneration is a reviewed event with a documented command
  (D-10).
- **Both MCP surfaces demonstrated (D-11):** Context Products
  listed/readable as MCP Resources, and a `get_context`-style MCP Tool
  callable mid-loop with an entity/scope argument. Lineage and replay
  retrieval over the same read-only surface is asserted (D-15).

## Auth posture (D-12)

Bearer-token auth is **on from day one**. There is no anonymous mode in
this family — financial-services users need the real posture from the
first touch. Clients pass the token via the `CCF_TOKEN` env var; the
server side uses the Phase-10 auth machinery. All tokens in these
examples are **synthetic fixtures** for demonstration; real deployments
supply credentials through their own token source — no real credential
ever appears in this tree.

## Why this family exists

CCF layers onto any agent harness as the trust-and-control plane; it
never absorbs the agent loop and never ships one (CLAUDE.md §7.3).
Users must never be forced to construct agents inside CCF — that
becomes tech debt. These examples *demonstrate* rather than assert that
the MCP egress / Experience Layer seam (CLAUDE.md §7.1, §8.3;
whitepaper §8.3 Pattern 3) is sufficient for a complete external
consumer: governed context in response to a request, lineage and replay
on demand, nothing required of the client.
