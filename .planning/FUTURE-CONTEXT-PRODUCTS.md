# Future work — Context Products for Commercial Banking and CIB

**Recorded:** 2026-08-15, during Phase 17 execution, at Dave's instruction.
**Status:** NOT SCHEDULED. This is a placeholder carrying information that must
not be lost, not an approved phase.

---

## The sequencing Dave stated

**Now — client side only.** The next several examples stay on the consumption
side, built from the simple existing examples plus the **FIBO data already
loaded into the backend stores** (four live databases outside this repository,
loaded for exactly this purpose — see `D-32` in Phase 17's CONTEXT).

This is Phase 17's ruled scope, and it **extends past Phase 17**. More
client-side work follows before any producer-side work begins.

**Later — Context Product construction.** At some point — Dave said possibly as
soon as 2026-08-16 — the work turns to developing Context Products for:

- **Commercial Banking**
- **Corporate Investment Banking**

The approach is deliberately staged: **start simple, then get progressively more
sophisticated in *how* the Context Product is constructed.** The sophistication
is in the construction, not in the domain surface.

## Where the specifications live

Dave maintains Context Product specifications in his **Obsidian vault**,
reachable through the `obsidian-vault` MCP server. The `obsidian-vault-access`
skill carries the navigation order, attribution rules, and vocabulary
discipline — read it before querying.

When the time comes, the queries look like:

> *"what context product specifications exist — let's start with simple ones first"*

> *"give me the full spec for covenant-cross-reference"*

## The constraint, stated plainly

**Do not query the vault for these specifications until Dave explicitly
approves.**

Dave's words: *"do not do this until I approve as we have much more client side
work to do before we get to the Context Product creation."*

The reason this constraint is worth honouring rather than treating as
scheduling: pulling producer-side design into a client-only phase is the exact
conflation that got Phase 16's example rejected. `consume.py` imported
`deployment.MANIFEST`; the consumer held a path into the producer's Control
Plane. Reaching for product specifications while the client surface is still
being built recreates that pressure at the design level instead of the code
level.

## What must survive into that work

Two properties already ruled, which the construction work must preserve:

- **Context products are assembled per request, never precomputed.** A client
  parameter routed through config, a Makefile, or an environment variable is
  the tell that something has gone wrong.
- **Mechanism, not values.** Whatever a Commercial Banking or CIB product needs
  — half-lives, thresholds, projection roles, policy bundles, ontology — lives
  in Control Plane artifacts. The SDK ships the machinery; the domain lives in
  configuration. A product class that hard-codes a covenant threshold is the
  No-Hardcoding Rule firing (`CLAUDE.md` §6.4).
