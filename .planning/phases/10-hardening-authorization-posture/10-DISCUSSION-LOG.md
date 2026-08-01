# Phase 10: Hardening — Authorization & Posture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 10-hardening-authorization-posture
**Areas discussed:** Scope-mapping artifact schema, Authorizer seam & placement, Audit record shape, Gate verification surfaces

---

## Scope-mapping artifact schema

| Question | Options | Selected |
|----------|---------|----------|
| Tenant-pattern grammar | Exact + trailing wildcard / Exact only / Full glob | Exact + trailing wildcard ✓ |
| Action vocabulary source | Door-declared action IDs / Free-form strings / Validated registry | Door-declared action IDs ✓ |
| Schema shape | New typed artifact class / Extend HitlPolicy / You decide | New typed artifact class ✓ |
| Version pinning | Same semver lane pattern / Content hash / You decide | Same semver lane pattern ✓ |

---

## Authorizer seam & placement

| Question | Options | Selected |
|----------|---------|----------|
| Protocol/helper placement | Both in runtime / Protocol in src + impl in runtime / You decide | Both in runtime ✓ |
| Door invocation | Optional binding like auth hook / Always-on when auth bound / You decide | Optional binding like auth hook ✓ |
| Artifact resolution | Per request / Cache with TTL / You decide | Per request ✓ |
| MCP deny rendering | Typed MCP error + shared constants / Door-local errors / You decide | Typed MCP error + shared constants ✓ |

---

## Audit record shape

| Question | Options | Selected |
|----------|---------|----------|
| Record fields | Full decision tuple / Minimal / You decide | Full decision tuple ✓ |
| Denial auditing | Audit both / Allows only / Rate-limited denials | Audit both ✓ |
| Replay placement | Extend HITL audit path / Separate authz log / You decide | Extend HITL audit path ✓ |

---

## Gate verification surfaces

| Question | Options | Selected |
|----------|---------|----------|
| Verification surfaces | All human-action surfaces / ApprovalGate.resolve only / You decide | All human-action surfaces ✓ |
| Double verification | Verify both, idempotent / Skip if transport verified / You decide | Verify both, idempotent ✓ |
| Refusal types | Reuse existing refusals / Primitive-specific subclasses | Reuse existing refusals ✓ |
| Examples demonstration | Extend 05/06 in place / Minimal assertion only / You decide | Extend 05/06 in place ✓ |

---

All selections followed the recommended option. No scope creep; deferred
items (free-threaded hammer, docs notes, executor overhead) recorded in
CONTEXT.md `<deferred>` from Phase 9 review carry-forwards.
