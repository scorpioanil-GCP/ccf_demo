# Deferred items — phase 15.1

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary. Plan 15.1-10 surfaces these to Dave at the phase gate.

## The HTTP schema route still serves only the typed-registerable classes

- **Found during:** plan 15.1-03, task 2
- **What:** `runtime/ccf_runtime/http_api/routes/schema.py` (and the
  `ccf schema export` CLI verb, and `tools/dump_schemas.py`) enumerate
  `SDK_ARTIFACT_CLASSES`. Plan 15.1-03 added a second SDK-owned mapping,
  `SDK_VERSIONED_ARTIFACT_CLASSES`, holding the six **author-versioned**
  classes whose contracts declare a string `artifact_version`:

  - `ccf.agent-definition`
  - `ccf.prompt-artifact`
  - `ccf.task-definition`
  - `ccf.workflow-definition`
  - `ccf.skill-catalog-entry`
  - `ccf.skill-grant`

  `docs/schemas/` holds committed schemas for all six (plan 15-14), and the
  route answers **404** for every one of them.

- **Why it was not fixed here:** widening the served set is a runtime surface
  change with `__all__`-visible consequences that nobody has ruled on, and this
  plan's own threat register accepts it explicitly (T-15.1-03-05). Nothing
  serves a *wrong* schema; the committed tree remains the authoritative
  authoring baseline for an adopter's editor.

- **What changed since phase 15 recorded this** — the question is sharper now,
  not answered. Phase 15's `deferred-items.md` framed the route's set as
  defensible because it "documents what a *manifest* may name". After 15.1-03
  that framing is no longer accurate: a manifest **may** name all six, as
  `registration: versioned`, and `load_and_boot` dispatches them through
  `register_versioned`. So the route's actual contract has narrowed to "the
  classes a manifest may name for **typed** registration" — which is a real
  contract, but a narrower and less obvious one than the phrase it inherited.
  The route's docstring now says so precisely; the ruling is still owed.

- **Where it belongs:** a ruling on whether the route's contract is "every
  schema the SDK owns" (serve the union of both mappings) or "the classes a
  manifest may name for typed registration" (keep the set, keep the sharpened
  docstring). Either answer is defensible; the defect is that the code and the
  name have drifted apart. Interacts with the `ccf schema export` CLI verb and
  `tools/dump_schemas.py`, which read the same mapping.

## Example 05 registers an author-versioned class through `register_typed`

- **Found during:** plan 15.1-03, task 2
- **What:** `examples/05-workflow-hitl/run.py` registers `prompt-artifact.yaml`
  with `registry.register_typed(...)` even though `ccf.prompt-artifact` declares
  a string `artifact_version` and is therefore author-versioned. The adjacent
  comment says "Four are AUTHOR-VERSIONED" while only three of the four travel
  `register_versioned`.
- **Why it was not fixed here:** `refuse_registration_the_sdk_fixes` guards the
  **manifest** path, by design — a direct `registry.register_typed` call in
  adopter code is the adopter's own call, and the SDK does not police it.
  Changing the example would change its audit log, and
  `tests/examples/test_workflow_hitl_output.py::test_the_author_versioned_definitions_kept_their_bump_check`
  asserts on exactly **three** definition keys. Flipping the fourth is a
  behavior change to a shipped example plus a test edit, in a plan whose scope
  is the manifest refusal.
- **Where it belongs:** a follow-up that either moves the prompt artifact onto
  `register_versioned` (and widens the example test to four keys), or states in
  the comment why the prompt artifact is deliberately the odd one out. Note the
  wider question it raises: the SDK refuses the wrong registration path at the
  *manifest* seam and not at the *registry* seam, and whether that asymmetry is
  intended is worth Dave's word.
