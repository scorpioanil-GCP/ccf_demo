---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
status: retired
retired: 2026-08-17
ruling: D-IMPL-152
superseded_by: [17, 18]
---

# PHASE 16 IS RETIRED — NOT PAUSED, NOT PARKED, NOT RESUMABLE

Ruled by Dave, 2026-08-17, recorded as **`D-IMPL-152`**. Earlier records in this
repository call Phase 16 *"stopped"*, *"parked"* or *"open"* and say things like
*"resume Phase 16 at 7/21"*. **Those are superseded. Do not resume this phase.**

## What happened

Phase 16 executed **6 of 21** plans and was stopped on 2026-08-15 when its
example surface was rejected — a 722-line example whose consumer imported the
producer, an architectural coupling that could not be patched out. Phase 17
restarted from the client side instead and shipped
`examples/hw1-companies-over-revenue`: a small, honest example whose `consume.py`
imports only stdlib, `ccf.client` and an adapter. Phase 18 took that same example
and added an MCP server to it, so one `consume.py` now runs unmodified over two
transports.

That is the direction of travel: **evolve the working example outward, on the
client side and the context-production side, rather than resume a plan set
written against a surface that no longer exists.**

## What is in `abandoned/`

The **14 unexecuted plans** (`16-07` … `16-20`) were moved to `abandoned/` rather
than deleted, per this project's standing discipline of keeping the reasoning and
changing the behaviour. They are moved out of the phase directory's top level
**so plan discovery stops counting them** — `*-PLAN.md` globs are directory-scoped
and non-recursive, so leaving them in place made every progress figure read the
phase as carrying 14 outstanding plans forever.

The 16 executed plans and their SUMMARYs stay where they are. **The work Phase 16
actually completed is real and is not withdrawn.**

## THE PLAN SET IS RETIRED. THE OBLIGATIONS ARE NOT DISCHARGED.

This is the part that must not be lost. Several abandoned plans carried real SDK
obligations under `CLAUDE.md` §9 (the eight-example v0 suite) and §13 (in-scope
for v0). Retiring the phase retires **the approach**, not **the need**:

| Abandoned plan | The obligation it carried, still owed |
| --- | --- |
| `16-07` | Backend selected by a configuration artifact, with a matrix asserting it |
| `16-08` | The staleness / half-life half of the fabric in the adoption argument |
| `16-09` | Harness portability across all three harnesses (§9 example 03) |
| `16-10` | Cross-process consumption over MCP **and A2A** (§9 example 04) |
| `16-11` | Archetype → agent artifact → factory → skill catalog → grant/revoke (§9 examples 01–02) |
| `16-12` | `make ci`'s documented claim made true; CI locks |
| `16-13`–`16-20` | Adopters guide, examples migration, docs gates, and the review protocol |

**None of these is closed by this retirement.** When each becomes current it must
be **re-derived against the surface that exists then**, not lifted from
`abandoned/`. The abandoned plans are readable as history and as a checklist of
what was once intended — they are **not** a work queue, and nothing should be
executed from that directory.

## Why the plans cannot simply be resumed

They describe a surface that no longer exists. The example tree they document was
rejected; `ccf.client`, the adapter conformance suite, `DoorOutcome`, the
`mcp+stdio` adapter and the two-transport `hw1` example were all built after they
were written. A plan that names files, symbols and page structures from the
rejected surface would need rewriting rather than executing, and rewriting it is
the same cost as planning fresh against the real one — with the added hazard that
the stale text reads authoritative.
