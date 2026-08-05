---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 12
subsystem: tooling-and-experience
tags: [json-schema, ergo-12, d-impl-79, cli, http-api, drift-gate]
requires: ["15-10", "15-09", "15-08", "15-07"]
provides:
  - "docs/schemas/ — one committed JSON Schema per SDK artifact class"
  - "tools/dump_schemas.py — regenerator with --check and exported serialize()"
  - "tools/check_schema_headers.py — $schema header CORRECTNESS gate, auto-arming per directory"
  - "make schemas / make schema-headers"
  - "GET /schema and GET /schema/{class_id} — the D-IMPL-79 route"
  - "ccf schema export — the ninth CLI noun, RequestSpec like the other eight"
affects:
  - "15-13 through 15-20 (each writes its own headers and runs `make schema-headers DIR=...`)"
  - "15-21 (tree-wide header gate; fragment assembly)"
  - "Phase 16 (a shipped schema instance to literal-include)"
tech-stack:
  added: []
  patterns:
    - "committed-derivative + regenerator + bytes-equality gate (the D-12 triad, second instance)"
    - "annotation-in-the-artifact (x-ccf-class-id) so a file->class link is checkable, not a file name"
    - "auto-arming gate: a directory joins the checked set when it carries its first annotation"
    - "explicit, owner-named deferral marker instead of a knowingly-false annotation"
key-files:
  created:
    - tools/dump_schemas.py
    - tools/check_schema_headers.py
    - docs/schemas/ (11 files)
    - runtime/ccf_runtime/http_api/routes/schema.py
    - runtime/ccf_runtime/cli/commands/schema.py
    - tests/cli/test_schema_export.py
    - docs/surface-changes/15-12-schema-export.md
  modified:
    - Makefile
    - runtime/ccf_runtime/cli/main.py
    - runtime/ccf_runtime/http_api/app.py
    - openapi.json
    - docs/DECISIONS.md
    - examples/00-quickstart/artifacts/*.yaml
decisions:
  - "Route prefix is singular /schema, matching the CLI noun and the other eight prefixes, not the plural the plan text used"
  - "D-IMPL-22's noun enumeration amended to nine — mechanical consequence of D-IMPL-79, which tests/http_api/test_routes.py reads"
  - "Quickstart documents carry an owner-named deferral marker, not a header: no SDK class accepts them today (verified), so a header would be a false editor hint"
  - "Header correctness is checked through the SDK's own load_artifact, not jsonschema — same validator the adopter's boot runs, and no new dependency"
metrics:
  duration: ~75m
  tasks: 3
  completed: 2026-08-04
---

# Phase 15 Plan 12: Schema Export Summary

Every SDK artifact class now has a committed JSON Schema an adopter can point
an editor at, a route and a CLI noun to fetch one, and a gate that checks the
`$schema` headers on artifact documents are *right* rather than merely
resolvable.

## What was built

**`tools/dump_schemas.py` + `docs/schemas/`** — eleven committed schemas, one
per entry in `SDK_ARTIFACT_CLASSES`, each annotated `x-ccf-class-id`.
`--check` writes nothing and reports drifted, missing, **and orphan** files;
`serialize()` is exported so the regenerator and the assertion cannot disagree
about what "the schema" means. Same triad as Phase 14's `openapi.json`, on the
same D-12 reasoning one step earlier: the schemas are what adopters author
*against*, before anything runs.

**`tools/check_schema_headers.py` + `make schema-headers`** — the header gate,
described in full below.

**`GET /schema`, `GET /schema/{class_id}`, and `ccf schema export`** — per
D-IMPL-79 the CLI noun returns `RequestSpec`s like the other eight and
`main()` gained no branch. The route emits from the live models rather than
reading `docs/schemas/`, so the committed tree stays a *baseline* rather than
becoming a second independently drifting artifact — a test asserts the served
document equals the committed one.

## The two review findings, and what each turned into

### codex: "the header test may prove only path existence"

**Verified against the tree before acting, and the concern was structural
rather than hypothetical** — a naive implementation of this plan's Task 3
would indeed have written `assert Path(target).exists()`. The gate that
shipped checks four things per document, each closing a way a header can be
wrong while looking right:

1. The header is the **first line** — a header buried below a comment block
   works in some editors and not others.
2. The target **resolves from the document's own directory**, which is how an
   editor resolves it. A repo-root-relative header that only works under
   pytest is broken in the only place it is actually read. Asserted
   negatively too: `test_a_header_that_only_resolves_from_the_repo_root_fails`.
3. The schema's `x-ccf-class-id` names a **real SDK class** and matches its
   committed file name. Reading the class id out of the *document* rather than
   off the path is what makes this a check rather than a restatement.
4. **The named class actually accepts the document**, via the SDK's own
   `load_artifact`. This is the strongest available form of correctness and
   costs no new dependency — the validator the adopter's fabric runs at boot
   is the validator the header is checked against. Asserted negatively by
   `test_a_header_naming_the_wrong_class_fails`, which points a real schema at
   a document of a different class and requires a failure. A path-existence
   gate passes that document happily, which is exactly why it is a test.

Plus a fifth, which activates automatically from 15-13 onward: when the
directory carries a `ccf.deployment-manifest`, every entry's declared
`class_id` must equal the class id in the header of the file at its `path`.
The manifest and the header are two independent statements of one fact,
authored in two different files, and this asserts they agree — precisely the
`artifact path → declared class_id → expected schema` cross-check codex asked
for.

### cursor + ollama: "a bad header fails only at 15-21, the most expensive point"

The gate **auto-arms per directory**. `tools/check_schema_headers.py` with no
arguments checks every `examples/**/artifacts` directory that already carries
at least one header or deferral marker. So a rewrite plan's directory joins
the checked set the moment that plan writes its first header, and a broken one
fails at wave 10–13 rather than at wave 14.

**What 15-14 through 15-20 should run in their own verify step:**

```
make schema-headers DIR=examples/NN-<name>/artifacts
```

It is also always-on in the `test` job via `tests/cli/test_schema_export.py`,
so a plan that forgets to run it still fails on its own commit. 15-21's
tree-wide form is `python tools/check_schema_headers.py --require-all`, which
drops the auto-arming and demands every discovered directory be annotated.

## Who owns schema regeneration after this plan

**Stated explicitly, because this was the second half of the cursor/ollama
finding.** Adding or changing an `ArtifactClass` after this plan requires
re-running `make schemas` and committing the result. That obligation is
**enforced, not remembered**: `tests/cli/test_schema_export.py` asserts
bytes-equality per class in the always-on `test` job, so a new class with no
committed schema, a changed field, or a Pydantic bump is a red build on the
commit that causes it — with a failure message naming `make schemas`.

**Ownership therefore sits with the plan that touches the class, not with
15-21.** There is no window in which a stale tree passes. 15-21 inherits no
regeneration debt from this arrangement; it inherits only the tree-wide header
gate (its own Task 4), which is a different obligation.

## Deviations from Plan

### 1. [Rule 1 — correctness] Quickstart documents carry a deferral marker, not a `$schema` header

- **Found during:** Task 3
- **Issue:** the plan asks for a `# yaml-language-server: $schema=` header on
  every `examples/00-quickstart/artifacts/*.yaml`. Checked empirically against
  all eleven classes: **no SDK artifact class accepts any of the four
  documents.** Each is a multi-artifact bundle (`halflife.yaml` holds a
  half-life table *and* a debt profile *and* a `demonstration` block;
  `controlplane.yaml` holds seven unrelated artifacts), and every contract is
  `extra=forbid`. A header would therefore annotate every key belonging to the
  other artifacts as an error — a wall of false positives in the adopter's
  editor, which is worse than no hint at all, and is exactly the
  "resolvable but wrong" failure the review asked me to prevent.
- **Fix:** each document carries an explicit
  `# ccf-schema: deferred(15-13) …` first line naming the plan that closes it
  and the reason. The gate treats a marker as accounted-for and a document
  with **neither** a header nor a marker as a failure, so nothing falls
  through silently. 15-13 Task 1 already reshapes these into typed per-class
  documents with a manifest and its acceptance criteria say each file "keeps
  or gains" a header — so the headers land there, alongside the reshaped
  documents they describe, which is where they are reviewable anyway.
- **Files modified:** `examples/00-quickstart/artifacts/*.yaml`
- **Commit:** 6a12853

### 2. [Rule 3 — blocking] Route prefix `/schema`, and D-IMPL-22's noun enumeration amended

- **Found during:** Task 2
- **Issue:** `tests/http_api/test_routes.py::test_mounted_nouns_equal_the_ruling_text`
  asserts **set-equality** between mounted path prefixes and the noun list it
  parses out of D-IMPL-22's ruling text in `docs/DECISIONS.md`. A ninth mounted
  noun fails it two ways: the ruling text names eight, and the plan's plural
  `/schemas` prefix would not match the singular CLI noun even once the text
  was amended.
- **Fix:** mounted at `/schema` (singular), so the CLI noun, the route prefix,
  the ruling text, and the other eight prefixes all agree on one word for one
  thing; and D-IMPL-22's enumeration amended to nine with a dated note that
  the addition is the **mechanical consequence of D-IMPL-79** — Dave's
  2026-08-04 ruling that `ccf schema export` reaches generation through a
  route. This is recording a decision already made, not making one: D-IMPL-79
  cannot be implemented without a ninth noun.
- **Files modified:** `docs/DECISIONS.md`,
  `runtime/ccf_runtime/http_api/app.py`,
  `runtime/ccf_runtime/cli/commands/schema.py`
- **Commit:** 6717a5e

### 3. [Rule 3 — blocking] `runtime/ccf_runtime/http_api/routes/`, not `http/routes/`

- **Found during:** Task 2
- **Issue:** the plan's `files_modified` names
  `runtime/ccf_runtime/http/routes/schema.py`; the package is `http_api`.
- **Fix:** used the real path. No other change.
- **Commit:** 6717a5e

### 4. [Deliberate omission] No plan-scoped `--report` subset test

Binding ruling 5 in the execution brief forbids it, and `--report` reports the
**accumulated** phase set (~46 names) rather than this plan's, so a
subset-equality assertion is not satisfiable at plan scope anyway. The
phase-wide `test_the_phases_fragments_claim_exactly_what_was_added` covers it.
This plan's two additions —
`ccf_runtime.cli.commands.schema.register` and
`ccf_runtime.http_api.routes.schema.build_router` — were confirmed present in
`--report`'s `added` list by hand before the fragment was written.

## Verification

| Check | Result |
| --- | --- |
| `tools/dump_schemas.py --check` | exit 0 |
| `pytest tests/cli/ tests/http_api/ -q` | 150 passed |
| `pytest tests/test_surface_drift.py -q` | 6 passed |
| `make ci` | **exit 0** (lint, mypy --strict over 168 files, full pytest, ten examples, docs-strict) |
| `docs/surface/v0.2-surface{,-baseline}.json` | untouched (`git status` clean for `docs/surface/`) |
| `src/ccf/deployment/operators.py` | not modified (15-11 owns it) |
| `openapi.json` diff | two added paths, nothing else |

## Known Stubs

None.

## Threat Flags

None. The one new surface, `GET /schema`, was already in the plan's threat
register (T-15-12-01, disposition `accept`): it exposes SDK-owned artifact
shapes that ship in the published reference already — no tenant data, no
values, no deployment configuration. It is mounted behind the same `guarded`
dependency list as every other non-health router, so a deployment that binds
an auth hook gets the same posture here as everywhere else.

## Self-Check: PASSED
