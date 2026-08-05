# Deferred items — phase 15

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary.

## The HTTP schema route serves only the manifest-addressable classes

- **Found during:** plan 15-14, task 1
- **What:** `runtime/.../http_api/routes/schema.py` (and the `ccf schema export`
  CLI verb) enumerate `SDK_ARTIFACT_CLASSES`. Plan 15-14 committed schemas for
  six additional SDK-owned, author-versioned classes
  (`ccf.agent-definition`, `ccf.prompt-artifact`, `ccf.task-definition`,
  `ccf.skill-catalog-entry`, `ccf.skill-grant`, `ccf.workflow-definition`), so
  `docs/schemas/` now holds schemas the route answers 404 for.
- **Why it was not fixed here:** the route's set is defensible as-is — it
  documents what a *manifest* may name — and widening it is a runtime surface
  change with its own `__all__`-visible consequences, in a wave where three
  plans are writing concurrently. It is a consistency question, not a defect:
  nothing serves a wrong schema, and the committed tree remains the authoritative
  authoring baseline.
- **Where it belongs:** a follow-up that decides whether "schemas the SDK owns"
  or "classes a manifest may name" is the route's contract, and says so in the
  route's docstring either way.
