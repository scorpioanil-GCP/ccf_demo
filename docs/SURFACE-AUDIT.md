# Phase 15 surface audit

The phase-close answer to ROADMAP Phase 15 Success Criteria 1, 4, 5 and 6. Every
number here is **generated from an executable measurement**, not transcribed
from a plan or estimated from a diff — the tools that produced them are named
under each section so any figure can be reproduced.

| Section | Answers |
| --- | --- |
| 1 | Criterion 6 — the generated public-surface diff and its cross-check against the curated log |
| 2 | Criterion 1 — the measured before/after of the adopter-facing surface, relocation and removal separately |
| 3 | Criterion 4 — per shipped helper, "what does this hide from the replay record?" |
| 4 | The two governance items the phase surfaced, and their disposition |
| 5 | The `/gsd-review` report, its triage, and the advisory findings carried forward |
| 6 | **Phase 15.1** — the gap-closure criterion-by-criterion evidence, the items carried to that phase's gate, and what the phase-close review found |

**Two phases, two documents in one file.** Sections 1–5 answer **Phase 15**'s
success criteria. Section 6 answers **Phase 15.1**'s, which are a different and
independently numbered list. The collision that matters: *Phase 15 Criterion 1*
is the measured adopter-facing surface (§2), while *Phase 15.1 Criterion 1* is
the manifest registration refusal (§6). A row citing "Criterion 1" means
whichever list its own section belongs to, and §6.1 says so again at the point
of use.

---

## 1. The generated public-surface diff (Criterion 6)

**Sources.** `docs/surface/v0.2-surface-baseline.json` (frozen at phase start by
plan 15-01, byte-unchanged since — see the immutability assertion below) diffed
against the live surface via
`tools.dump_surface.diff_surfaces(baseline, build_surface())`. The tables below
are emitted from that call, not transcribed.

The live manifest `docs/surface/v0.2-surface.json` was regenerated **in place,
exactly once, by this plan**. That is the single-owner rule
(`docs/surface-changes/README.md`): 15-01 writes it at phase start, 15-21 writes
it at phase close, and the nineteen plans in between run
`tools/dump_surface.py --report` and claim their drift with a fragment. Nothing
was re-pointed here — no `SURFACE_PATH` change and no test edited to read a
different file — because the live manifest never moved. `--check` now exits 0
for the first time since 15-01, so the documented-drift gate has degenerated to
plain bytes-equality with nothing left unclaimed.

### 1.1 What moved

#### Added (52)

| Fully-qualified name | Claimed by |
| --- | --- |
| `ccf.controlplane.artifact_base.ArtifactClass` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifact_base.VersionedArtifact` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifact_base.validate_semver` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.ArtifactRole` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.DEBT_PROFILE` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.DEPLOYMENT_MANIFEST` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.DeploymentManifest` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.HALF_LIFE_TABLE` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.ManifestEntry` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_POLICY` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_SIMILARITY` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TEMPORAL` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TRAVERSAL` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OperatorParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.PERSPECTIVE` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.PRODUCT_CLASS` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.PerspectiveArtifact` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.PolicyFilterParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.ProductClassDeclaration` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.RESOLUTION_SPEC` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.SIGNAL_BATCH` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.SignalBatch` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.SimilaritySelectParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.TemporalAsOfParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.VersionedArtifact` | `15-07-resolution-spec.md` |
| `ccf.deployment.ArtifactPin` | `15-10-manifest.md` |
| `ccf.deployment.BootedFabric` | `15-10-manifest.md` |
| `ccf.deployment.DeploymentManifest` | `15-10-manifest.md` |
| `ccf.deployment.ManifestEntry` | `15-10-manifest.md` |
| `ccf.deployment.ResolvedPins` | `15-10-manifest.md` |
| `ccf.deployment.SDK_ARTIFACT_CLASSES` | `15-06-class-lookup.md` |
| `ccf.deployment.SDK_ARTIFACT_ROLES` | `15-10-manifest.md` |
| `ccf.deployment.SimilarityCorpusAttributeError` | `15-11-operator-builder.md` |
| `ccf.deployment.UnpinnedArtifactError` | `15-10-manifest.md` |
| `ccf.deployment.build_operator_registry` | `15-11-operator-builder.md` |
| `ccf.deployment.classes.SDK_ARTIFACT_CLASSES` | `15-06-class-lookup.md` |
| `ccf.deployment.classes.SDK_ARTIFACT_ROLES` | `15-10-manifest.md` |
| `ccf.deployment.classes.refuse_role_the_sdk_fixes` | `15-10-manifest.md` |
| `ccf.deployment.classes.resolve_artifact_class` | `15-06-class-lookup.md` |
| `ccf.deployment.load_and_boot` | `15-10-manifest.md` |
| `ccf.deployment.manifest.BootedFabric` | `15-10-manifest.md` |
| `ccf.deployment.manifest.load_and_boot` | `15-10-manifest.md` |
| `ccf.deployment.operators.SimilarityCorpusAttributeError` | `15-11-operator-builder.md` |
| `ccf.deployment.operators.build_operator_registry` | `15-11-operator-builder.md` |
| `ccf.deployment.pins.ArtifactPin` | `15-10-manifest.md` |
| `ccf.deployment.pins.ResolvedPins` | `15-10-manifest.md` |
| `ccf.deployment.pins.UnpinnedArtifactError` | `15-10-manifest.md` |
| `ccf.deployment.refuse_role_the_sdk_fixes` | `15-10-manifest.md` |
| `ccf.deployment.resolve_artifact_class` | `15-06-class-lookup.md` |
| `ccf_runtime.cli.commands.schema.register` | `15-12-schema-export.md` |
| `ccf_runtime.http_api.routes.schema.build_router` | `15-12-schema-export.md` |

#### Removed (0)

*None.* This is a finding, not an omission. D-15B granted free rein on the
public API pre-1.0 and the phase used none of it in the removing direction:
every helper Phase 15 shipped is **additive**, and every path that worked at
phase start still works. Section 3's D-14 row and
`tests/deployment/test_direct_construction.py` assert that positively rather
than inferring it from an empty list.

#### Reshaped (1)

| Fully-qualified name | Claimed by |
| --- | --- |
| `ccf.assembly.worker.EntityResolutionSpec` | `15-07-resolution-spec.md` |

`semver` became a required field with no default (D-IMPL-77). It participates in
`content_hash(spec)`, so every `resolution_spec_version` pin minted after the
change differs from one minted before it. Existing Decision Replay records stay
valid against the artifact versions they name — nothing is invalidated and no
record changes shape.

#### Behavior — exempt from diff agreement (1 public)

| Fully-qualified name | Claimed by |
| --- | --- |
| `ccf.controlplane.artifacts.load_artifact` | `15-05-timestamps.md` |

D-02. `load_artifact`'s signature did not move; what it returns for a
timestamp-shaped scalar did. A generated signature diff is **structurally
incapable** of seeing this, which is the whole reason D-15 asks for a curated
log alongside the manifest rather than instead of it.

### 1.2 The cross-check, and what makes it a check

`docs/SURFACE-CHANGES.md` carries **267 entries** — 54 naming a public Python
surface, 213 naming something real that is not Python API (lint scope, tooling,
committed schemas, and artifact *document* formats).

`tests/test_surface_completeness.py` asserts six properties against that log,
reading it through `assemble_surface_changes.parse_entries()` — the same parser
that assembles the document, so "what the log says" has exactly one definition:

| # | Property | Falsification, run once and reverted |
| --- | --- | --- |
| 1 | The diff is non-empty and **both** classification partitions are non-empty | an empty diff would make every assertion below vacuously true |
| 2 | Every diff line has a matching **public** entry with an agreeing `Change type` | deleting the `ccf.deployment.load_and_boot` entry → fails naming that exact name, `NO ENTRY` |
| 3 | Every public non-`behavior` entry has a matching diff line | adding an entry for `ccf.deployment.does_not_exist` → fails naming it |
| 4 | No `Public surface: false` entry names anything in the diff | flipping `load_and_boot` to `false` → fails with `WRONG CLASSIFICATION`, **not** `NO ENTRY` |
| 5 | `ccf.controlplane.artifacts.load_artifact` carries a `behavior` entry | retyping it `reshaped` → fails naming that surface |
| 6 | The frozen baseline is byte-identical to what 15-01 committed | pinned by SHA-256 **and** by commit provenance |

Changing one entry's `Change type` from `added` to `removed` fails **both**
directions with distinct messages — `WRONG CHANGE TYPE. Found ['removed']; the
manifest shows 'added'` from the diff→log side and `claims 'removed' … but the
manifest shows it under ['added'] instead` from the log→diff side. A mismatched
direction and a misclassification are never reported as a missing entry, because
each needs a different fix.

**Assertions 2 and 4 together close the classification in both directions.**
That is why `Public surface` is a *checked field* rather than an annotation: an
executor who mislabels a real public-API change to duck assertion 3 fails
assertion 2 instead.

**The two gates are a designed pair.** `tests/test_surface_drift.py` is
module-granular and direction-blind on purpose — cheap, always-on, survivable
across fourteen parallel waves. This module is exact and runs at phase close and
thereafter. Weakening either without the other is a regression, and both
docstrings say so.

### 1.3 Baseline immutability, verified

`docs/surface/v0.2-surface-baseline.json` is byte-identical to what 15-01
committed:

```
sha256  cef0d469db249947f8392331a50bc94bf92d46a4266e4945e2b59944dac043cc
```

`git log --oneline -- docs/surface/v0.2-surface-baseline.json` shows **two**
commits, `6e6d3f5 feat(15-01)` and `c4e7ca4 fix(15-01)` — both plan 15-01's, the
second being 15-01's own in-plan correction making the manifest import-order
independent. The rule the plan text states as "exactly one commit" is written
once **by 15-01** and never again by any other plan; that is what
`test_the_frozen_baseline_was_written_only_by_plan_15_01` asserts, and it is
what holds. The bytes at `c4e7ca4` hash to the digest above.

---

## 2. The measured adopter-facing surface (Criterion 1)

**Sources.** `tools/measure_examples.py` (an AST measurement, not a regex),
frozen at phase start into `docs/surface/examples/before/` and re-measured into
`docs/surface/examples/after/`. The table below was rendered from the
`audit_report()` function in the ERGO-03 audit module under `tests/examples/`,
which returned four independent totals and a per-file breakdown and was
**structurally incapable** of returning a combined figure — a companion
assertion parsed the function's own source and failed on the forbidden names.

**That module was retired on 2026-08-10 and no longer exists** (`D-IMPL-94` /
Phase 16 `D-15`) — see **§2.5** below for the ruling, and
`docs/surface/examples/ERGO-03-FROZEN.md` for the same measurement frozen as
scripted output at a named tree SHA. The paragraph above is left in the past
tense rather than rewritten, so the record of how this table was produced
survives its producer.

### 2.1 Removal and relocation are two figures, never one

Per D-12 there is **no target number**. What follows is the achieved number, and
the executable audit pinned it: `test_no_rewritten_example_has_silently_regressed`
compared every `after/` fragment against a live re-measurement, so a later edit
could not quietly re-inflate an example a rewrite plan had already thinned. That
assertion was green at its retirement on 2026-08-10 and the figures below are
the ones it last pinned (§2.5).

`mechanical` is wiring the SDK absorbed — it is *gone*. `relocated` is
assertions and print summaries that moved into `tests/` under D-09 — the work
still exists, in a better place. **They are never summed.** A single "lines
saved" headline would conflate a helper that removed work with a file that
moved lines, and D-12 names that conflation as the risk.

`examples/external/00-hello-context/run.py` is why the rule is not pedantry: its
raw line count **rose** 766 → 790 while its mechanical figure fell 36 → 0. What
disappeared there was a hand-built operator registry and a
registration-prologue-plus-`boot`; what arrived was a nesting level and four
typed reads. A combined figure would have reported that plan as a regression.
`examples/05-workflow-hitl/run.py` is the same shape (858 → 866 raw, 28 → 4
mechanical, 112 → 0 relocated).

### 2.2 Per file, and the tree

| File | mech before | mech after | reloc before | reloc after | raw before | raw after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `examples/00-quickstart/run.py` | 143 | 13 | 40 | 0 | 451 | 396 |
| `examples/01-agent-basics/run.py` | 159 | 14 | 85 | 0 | 619 | 529 |
| `examples/02-skilling/run.py` | 118 | 13 | 68 | 0 | 571 | 607 |
| `examples/03-harness-portability/legs/__init__.py` | 0 | 0 | 0 | 0 | 1 | 1 |
| `examples/03-harness-portability/legs/deterministic.py` | 0 | 0 | 11 | 11 | 507 | 527 |
| `examples/03-harness-portability/legs/live.py` | 0 | 0 | 23 | 23 | 641 | 641 |
| `examples/03-harness-portability/legs/ollama_client.py` | 0 | 0 | 0 | 0 | 147 | 147 |
| `examples/03-harness-portability/run.py` | 145 | 13 | 98 | 54 | 720 | 711 |
| `examples/04-cross-process/producer_child.py` | 143 | 13 | 14 | 1 | 630 | 595 |
| `examples/04-cross-process/run.py` | 53 | 13 | 68 | 1 | 533 | 519 |
| `examples/05-workflow-hitl/run.py` | 28 | 4 | 112 | 0 | 858 | 866 |
| `examples/06-decision-replay/run.py` | 175 | 12 | 130 | 0 | 1320 | 1160 |
| `examples/07-artifact-store-mcp/mcp_store_child.py` | 0 | 0 | 1 | 1 | 135 | 135 |
| `examples/07-artifact-store-mcp/run.py` | 132 | 13 | 27 | 1 | 587 | 636 |
| `examples/08-e2e-demo/generator.py` | 0 | 0 | 0 | 0 | 431 | 431 |
| `examples/08-e2e-demo/run.py` | 161 | 13 | 6 | 6 | 1141 | 1146 |
| `examples/external/00-hello-context/client_adk.py` | 0 | 0 | 1 | 1 | 75 | 75 |
| `examples/external/00-hello-context/client_anthropic.py` | 0 | 0 | 2 | 2 | 97 | 97 |
| `examples/external/00-hello-context/client_bare.py` | 0 | 0 | 5 | 5 | 77 | 77 |
| `examples/external/00-hello-context/fixtures/capture_proxy.py` | 0 | 0 | 7 | 7 | 415 | 415 |
| `examples/external/00-hello-context/fixtures/diff_fixtures.py` | 0 | 0 | 7 | 7 | 93 | 93 |
| `examples/external/00-hello-context/replay_server.py` | 0 | 0 | 9 | 9 | 400 | 400 |
| `examples/external/00-hello-context/run.py` | 36 | 0 | 22 | 22 | 766 | 790 |
| `examples/external/00-hello-context/serve.py` | 132 | 13 | 1 | 1 | 773 | 741 |
| **Tree total** | **1425** | **134** | **737** | **152** | **11988** | **11735** |

**Mechanical wiring removed: 1291 lines** (1425 → 134, a 90.6% reduction).
**Assertions and prints relocated: 585 lines** (737 → 152). These two numbers
are reported side by side and are not added together.

**Re-measured 2026-08-05 after Phase 15.1 (plan 15.1-09), and the raw column
moved the wrong way.** Design E2 (D-IMPL-86) added a second authored artifact
per deployment, a hoisted plan local, a binder call, and the comment blocks
explaining all three. Re-measuring every `after/` fragment: **`mech`, `reg` and
`removable` did not move at all** — 1425 → 134 and 737 → 152 are unchanged — but
`raw` rose at nine of the ten drivers, tree-wide **11312 → 11735**, including
+46 at `00-quickstart`, +48 at `01-agent-basics` and +63 at `02-skilling`. The
table above now carries the re-measured figures rather than the pre-15.1 ones.
Stated plainly rather than netted away: **E2 cost an adopter lines, and none of
what it cost was the mechanical boilerplate Criterion 1 set out to remove.** It
bought a check that can fail; it did not buy brevity, and this section is the
wrong place to imply otherwise. That is also exactly why D-12 forbids a single
combined figure — a "lines saved" headline here would have hidden a real
ergonomic cost behind an unrelated real win.

The 134 mechanical lines that remain are almost entirely the **13-line
registration cluster** each rewritten driver still carries: the author-versioned
definition classes that keep their D-05 bump check, the MaxTTL/product-class
pair that is the D-15A line, and the two SDK classes a manifest cannot address.
Those are not residue — they are the abstraction line, visible on the page.

The 152 relocated lines that remain are pinned by tests the rewrite plans were
not permitted to touch. `examples/external/00-hello-context/run.py` keeps 22
because `tests/examples/test_ext00_hardening.py` asserts each of `PASS 1:`
through `PASS 8:` appears in a real run; `examples/03-harness-portability`'s
legs keep theirs for the same class of reason. The claims behind that narration
were relocated even where the narration could not be.

### 2.3 The 152 lines that did not relocate — ERGO-16, line by line

ERGO-16 reads "**every** example's CI assertions and print summaries relocate
to a parallel `tests/` module". The measurement says 152 relocatable lines
remain. Both statements are in this document, so the gap gets an accounting
rather than a footnote — it was raised as a blocking finding at the phase-close
review and it is the one item this plan cannot close on its own authority.

Every remaining line, with the reason it stayed:

| Category | Lines | Where | Why it did not move |
| --- | ---: | --- | --- |
| **Not an example driver** | 65 | `03-harness-portability/legs/{deterministic,live}.py` (34); `external/00-hello-context/client_{bare,anthropic,adk}.py` (8), `fixtures/{capture_proxy,diff_fixtures}.py` (14), `replay_server.py` (9) | None was a rewrite target and none is an example driver. The three client legs are **required** to stay untouched — ERGO-15 and EXAM-04 rest on their zero CCF imports, and 15-20 asserts an empty `git diff` on all three plus the fixtures and the replay server. |
| **Excluded from `make ci` by design** | 54 | `03-harness-portability/run.py` | Every one is inside `_live`, the opt-in provider leg (D-11). Relocating them would move assertions somewhere **nothing runs them**. 15-15 enforced the property the criterion was protecting in the form that survives: `test_no_assertion_survives_on_the_path_ci_actually_runs` parses `run.py` and refuses any `assert` outside `_live`. |
| **Pinned by an out-of-scope test** | 22 | `external/00-hello-context/run.py` | Eight of its ten `print` calls are the `PASS 1:`–`PASS 8:` lines, and `tests/examples/test_ext00_hardening.py` runs the file as a subprocess and asserts each one appears. That module was out of scope for 15-20 and its acceptance criteria required it unmodified. The *claims* behind the narration were relocated to `tests/examples/test_ext00_serve_output.py`; the console output could not be. |
| **Process protocol, not narration** | 4 | `external/.../serve.py`, `04-cross-process/{producer_child,run}.py`, `07/mcp_store_child.py` | `READY <port>` handshakes (a parent's blocking `readline()` is the readiness gate) and one stderr passthrough on child failure. Neither is an assertion nor a summary. |
| **The narration *is* the deliverable** | 6 | `08-e2e-demo/run.py` | DEMO-03's byte-compared staged transcript. Its sixteen `_require` checks *did* relocate; the measurement never counted them, because they were function calls rather than `assert` statements. |
| **Total** | **152** | | |

**What this means for ERGO-16, stated as the question rather than the answer.**
Read as "every example *driver*'s assertions and print summaries relocate,
except where relocation would move an assertion somewhere nothing runs it or
break a test the plan was forbidden to touch", the requirement is met and the
residual is exactly the set of principled exceptions above. Read as literally
"every", it is not. **That reading is Dave's to rule on** — it is carried to
the phase gate rather than resolved here (CLAUDE.md §3.1: an unsurfaced
decision is a blocking finding, and the correct response is to surface it).

### 2.4 The day-1 integration

`examples/00-quickstart/run.py` — the file the phase opened against — is
**451 → 396 raw lines** (350 at the Phase 15 gate, before Phase 15.1's E2 work
added the projection-requirements read, the hoisted plan and the binder call),
with mechanical wiring **143 → 13** and every one of
its 40 assertion/print lines relocated to `tests/`. Both halves of the ROADMAP's
opening complaint are answered: the ~85 assertion/print lines that "no adopter
writes" are out of the published snippets, and the ~105 lines of YAML→typed
marshalling are absorbed into `parse_artifact`-reachable artifact classes.

**The import-line collapse is the secondary win, and it is measurable.** The
quickstart carried **54 import lines across 27 distinct SDK names** before the
rewrite and carries **41** after (36 at the Phase 15 gate; E2 added the
requirements read and the binder import). Tree-wide, import lines fell
**974 → 867**. An
adopter's first impression of an SDK is how many of its names they must know to
write anything at all, and that number went down while capability did not.

### 2.5 ERGO-03's running check is retired; the measurement is frozen (D-IMPL-94 / D-15)

**Recorded 2026-08-10, plan 16-01.** The executable half of this section — the
test module under `tests/examples/` that produced the table in §2.2 — **no
longer exists**. It was deleted deliberately, and this note is here so that a
reader arriving at §2.2 finds the measurement rather than an absence.

**The ruling** is `docs/DECISIONS.md` **`D-IMPL-94`**, recording Phase 16
**`D-15`** (Dave, 2026-08-10). **The reason** is structural, not cleanup: the
check compared the live `examples/` tree against `docs/surface/examples/before/`,
a baseline frozen once at Phase 15's *start* and never regenerated. Phase 16
retires `examples/00`–`08` and `examples/external/00-hello-context` and rebuilds
the suite greenfield (`DOCS-17`), so from the first new example directory onward
the comparison is not stale but **meaningless** — the "after" side stops being a
rewrite of the "before" side and becomes a different tree.

`D-IMPL-94` rejected the two alternatives explicitly. **Re-baselining** would
have destroyed the Phase 15 comparison this requirement's evidence rests on, and
`tools/measure_examples.py` warns in its own docstring that a mid-phase re-freeze
does exactly that. **Deleting without capture** would have erased a **Complete**
requirement's shipped evidence.

**Where the measurement now lives:** `docs/surface/examples/ERGO-03-FROZEN.md`,
written from scripted output at tree SHA `e7e1729` **before** any Phase 16
example change and before the module was removed, reporting relocation and
removal as separate figures per ERGO-03's own wording. The four headline
figures there are identical to §2.2's — 1425 → 134 mechanical and 737 → 152
relocated — and the `raw` column is re-measured (11735 → 11793 tree-wide, the
lines Phases 15.2/15.3/15.4 added).

**What did not retire:** `tools/measure_examples.py` and `make measure-examples`
still work; the 24 `before/` and 24 `after/` fragments stay committed and are
the primary evidence; and **ERGO-03 stays Complete** — a requirement is not
un-met by the retirement of a check whose comparison a later ruling made
meaningless.

---

## 3. What each shipped helper hides from the replay record (Criterion 4)

Criterion 4 asks that every shipped helper be answerable to "what does this hide
from the replay record?" with **"nothing"**, and that the answer carry a reason
rather than an assurance. The abstraction line is D-15A: marshalling and wiring
only. Every point where a deployment *asserts something the fabric then
verifies* stays in adopter code.

| Surface | What it does | What it hides from the replay record | Why, and what enforces it |
| --- | --- | --- | --- |
| `ccf.deployment.resolve_artifact_class` | class-id string → `ArtifactClass` | **Nothing.** It resolves a name to a contract and returns it; it registers nothing, pins nothing, and reads no document. | An SDK-owned id resolves from a hand-maintained mapping reviewed with the code; every other id lands on the `DeclaredArtifact` envelope **by design** (D-01), and SDK ids resolve *first* so a manifest cannot shadow an SDK class into the permissive envelope. `tests/deployment/test_class_lookup.py` holds the mapping to the module's actual exports and asserts the shadowing order. |
| `ccf.deployment.load_and_boot` | manifest → parse → validate → register → `boot()` | **Nothing.** It changes what *produces* the pins, never what `boot` requires of them. It does not execute operators, does not run the three validation gates, and does not build a product's lineage record. | The manifest **enumerates**: `ManifestEntry` refuses `*`, `?` and `[` at parse, because a glob would make dimension 2 of the replay record a function of directory contents at boot time, recorded by no artifact. `boot()` itself is byte-unchanged. The gate boundary is held by the `cinv02-deployment-gates` lint rule (no allowlist) and by `tests/products/test_gate_independence.py::test_no_deployment_callable_takes_both_shapes`. |
| `ccf.deployment.build_operator_registry` | operator-parameters artifacts + `GraphView` → populated `OperatorRegistry` | **Nothing.** It constructs operators; it does not run them, and it does not answer "which operators does this product require". | The `view` is a **required keyword with no default** so the ordering constraint lives in the signature (D-07): the similarity corpus is read at a boundary the deployment named, never lazily at first invocation — INV-CH7-27 cannot name a corpus that is a function of invocation timing. The builder exposes **no "required keys" convenience**, deliberately, so passing the registry's own keys to both sides of Gate 2 is not made easier to write than to avoid. `tests/deployment/test_operator_builder.py` pins the required-keyword shape, the boundary read, and the refuse-never-repair corpus ruling. |
| `ccf.deployment.ResolvedPins` | the `(key, version, class_id)` record a manifest load produces | **Nothing — and the design is a constraint on what it must never grow.** `version_for` is **lookup**, not selection: the caller already knows the key it wants. | A `pins.policy_bindings()` helper would shorten the adopter's `build_replay_record` call and, in doing so, move the *selection* of which bindings are in force out of the deployment and into the SDK — dimension 2 assembled by a rule nobody in the deployment wrote down. That is a governance move in an ergonomics costume. `tests/deployment/test_manifest.py::test_resolved_pins_has_exactly_one_public_method` pins the public method set exactly. |
| `ccf.deployment.BootedFabric` | handle + pins + tenant + parsed artifacts | **Nothing, and D-IMPL-80 is why.** `role: load` entries are parsed and returned **but never registered and never pinned** — so a signal batch never content-hashes raw event data into Control Plane state, and therefore never enters Decision Replay dimension 2. `role` is **required with no default**, so the choice is never made silently: an entry omitting it is a parse failure, and `role: register` on `ccf.signal-batch` is refused outright. `artifacts` carries both roles because **role governs registration and pinning, never visibility** (D-IMPL-80 amendment). | `tests/deployment/test_manifest.py::test_a_manifest_entry_naming_no_role_is_refused`, `::test_the_sdk_refuses_a_register_role_on_the_signal_batch`, `::test_a_load_role_entry_is_returned_but_never_registered`, and `::test_the_pin_set_covers_every_register_role_entry_and_no_other`. |
| The eleven artifact classes (`ccf.resolution-spec`, the four `ccf.operator-parameters.*`, `ccf.signal-batch`, `ccf.perspective`, `ccf.product-class`, `ccf.deployment-manifest`, and the two pre-existing) | YAML → validated typed object through `parse_artifact` | **Nothing.** They replace hand-written marshallers with the same seam that already served half-life tables and debt profiles — same float refusal, same zone-less-timestamp refusal, same resolver suppression. One document, one class. | `ProductClassDeclaration.required_operator_keys` is the case that matters: it gives the **projection plan's declaration** an authored source independent of the engine's resolution — which is what made the tautologies in §4 findable at all. Stated precisely, because the loose version is easy to repeat: Gate 2's own two arguments are `candidate.lineage.operators_invoked` and `engine_resolved`, and `required_operator_keys` is *upstream* of both. What the artifact buys is that the plan stops being a restatement of the engine's configuration, which is the independence everything downstream of it — the empty-operator guard, and every declared-vs-resolved check — silently depends on. `PolicyFilterParametersArtifact` deliberately declares **no** `permitted_policy_bundle_versions` (D-IMPL-76) — the adopter passes the pin set, keeping the admission set visible where every other pin is. |
| `ccf.controlplane.artifacts.load_artifact` (behavior, D-02) | reads timestamp-shaped scalars as text | **Nothing — it stopped hiding something.** Previously PyYAML's resolver silently produced a *naive* `datetime`, which the registry then refused as non-canonicalizable, and eleven call sites hand-normalized it six different ways. Now the scalar arrives as `str`, a `datetime`-annotated contract field parses it aware, and a zone-less date-time is **refused at parse** naming D-IMPL-38 rather than read as naive. | `tests/controlplane/test_timestamps.py` pins all five properties, including that the shared `yaml.SafeLoader` is unmutated so YAML parsing elsewhere in the process is unaffected. |

### 3.1 The two places the line was deliberately not crossed

Both were reachable ergonomic wins the phase declined, and each has a standing
assertion rather than a comment:

1. **`run_gates` is still called from adopter code, with both of its arguments
   assembled there.** What the phase declined was a wiring helper that ran the
   gate on the adopter's behalf; gate execution, and the assembly of both
   arguments, stay where the deployment can see them. Enforced by the
   `cinv02-deployment-gates` lint rule — which **takes no allowlist** — by
   `tests/products/test_gate_independence.py` (a perturbation regression test
   plus an AST identifier guard over `src/ccf/deployment/`), and by
   `tests/lints/test_deployment_gates_ban.py`, the opposite-direction guard
   proving the ban did not widen beyond its one importer.

   **What this item used to claim, and what was not true as shipped.** It
   asserted that the two inputs to `run_gates` were independently sourced in
   adopter code — `candidate.lineage.operators_invoked` being what the producer
   *declares*, `engine_resolved` being what the projection engine *observed
   itself running*. That is CR-2 stated as a property, and the code did not have
   it: at all **nine** call sites both arguments were filled from
   `execution.operators_invoked` — the same **object**, not merely the same
   value (D-GATE-15 second amendment, correction (2)). The keeping-a-helper-out
   half was true and remains true. The two-sources half was not. That is
   recorded here rather than quietly restated, because §3.1 is this audit's
   statement of where the abstraction line was drawn, and a reader has to learn
   that one of its two claims did not hold.

   **What Phase 15.1 did about it (D-IMPL-86, design E2).** The projection's
   required operator set became its own authored artifact
   (`ccf.projection-requirements`), separate from the product class's claim.
   `ccf.deployment.binder.refuse_operator_set_divergence` compares the two, and
   is called **between plan construction and `ProjectionEngine.execute`** — not
   at boot, a placement D-IMPL-86's correction of 2026-08-05 withdrew as
   impossible, since `load_and_boot` has no `ProjectionPlan` in scope at any of
   its preflights. And Gate 2 is documented for what it verifies —
   **assembly-path integrity** — rather than for an independence it never had.
   Authorable drift now fails at the binder; Gate 2 holds a served product to
   the assembly path the deployment claimed.

2. **The pin set has no bindings helper.** See the `ResolvedPins` row above.
   `version_for` is the one accessor this type may ever grow, and
   `test_resolved_pins_has_exactly_one_public_method` is what stops it growing a
   second.

### 3.2 D-14: the phase added a path and removed none

The generated diff in §1 shows **zero removals**, and
`tests/deployment/test_direct_construction.py` asserts the positive property
that an empty removal list only implies: `EntityResolutionSpec`, `SignalEnvelope`,
all four `*Parameters` classes and `boot()` are each importable from their
original modules and **directly constructible with no manifest, no
`load_and_boot`, and no `ccf.deployment` import anywhere in that test module**.
Its prologue is the pre-phase adopter code this phase made optional, written out
longhand, because a promise with no executable assertion is a comment.

---

## 4. The two surfaced governance items, and their disposition

D-15A reserves the right to revisit the abstraction line surface by surface, and
requires such cases be **surfaced as decisions, not resolved by the phase**.
Research §5.5 surfaced exactly two. Both are closed.

### G-A — `permitted_policy_bundle_versions` sourcing

**Ruled by D-IMPL-76 (Dave, 2026-08-04): option (b), the adopter passes the pin
set.** `PolicyFilterParameters.permitted_policy_bundle_versions` is a set of
content hashes minted at registration time, so a typed
`ccf.operator-parameters.policy` artifact class *cannot* declare it. The ruling
puts it in `build_operator_registry`'s signature as an argument the adopter
supplies from `booted.pins`.

Implemented as ruled: `PolicyFilterParametersArtifact` declares no admitted
version set at all (`test_the_policy_artifact_declares_no_admitted_version_set_at_all`),
and the builder reads it from the passed pins
(`test_the_admitted_policy_versions_come_from_the_passed_pins`).

Worth recording because the call was close: the D-IMPL-76 entry itself notes
that D-15A would have *permitted* option (a) — `PolicyFilter._admits` compares
two sources, but it is an operator predicate whose whole job is the comparison,
not a validation gate catching a producer misdeclaring. **The ruling took the
conservative side of a permitted choice**, at a cost of one adopter line.

### G-B — `required_operators()` returning `operators.keys()`

**Closed at the instances; watched by a tripwire at the pattern.** The framing
this heading previously carried — "closed structurally, in two layers", and that
the earlier "remains a pattern-level risk" reading "no longer holds and must not
be carried forward" — is **withdrawn**. It had the correction backwards: it
explicitly forbade the weaker framing that is in fact the accurate one. The
pattern-level risk is real for any receiver the guard's convention list does not
name.

**Layer 1, the instances.** Every projection in the suite now declares its keys
from `ProductClassDeclaration.required_operator_keys`, authored in the
product-class artifact. 15-09 defines the field; 15-13 fixes the quickstart
origin; 15-14 through 15-20 carry it through the rest of the suite.

**Layer 2, the pattern — a tripwire, not a wall.**
`tests/products/test_required_operators_guard.py` is a standing AST guard over
`src/`, `runtime/` and `examples/`: any `required_operators` implementation
reading the operator registry's own keys is a red build. Matching on AST
identifiers rather than source text means a *comment* cannot defeat it, and
receiver aliasing is followed to a fixed point. It is **not** dataflow analysis,
and a **rename of the receiver does defeat it**: the refused receivers are a
convention list (`operators`, `registry`, `_registry`, plus the enclosing
function's own parameter names), so a projection that named its registry
something else entirely passes. The claim the module supports is its own —
"every spelling the phase found, and the obvious evasions of them", not
"impossible to write" — and this audit had been contradicting the guard it was
describing. Layer 1 closed the instances; layer 2 catches a recurrence in the
shapes it knows.

D-IMPL-86 makes this a **structural limit rather than a caution** (D-GATE-15
second amendment, point (3)): **no AST gate can distinguish an authored literal
from a transcribed one**, because the compliant state and the violating state
are textually identical. A tripwire is the most an AST check can be here — which
is why design E2 put the load-bearing refusal in a binder over two authored
documents rather than in a guard over source.

### 4.1 What G-B was actually protecting — the phase's strongest finding

The phase found **nine instances of "a check that passes for a reason unrelated
to what it claims to verify."** Two are outright correctness defects, found
independently in the same wave by plans that never communicated. The full ledger
is below; each row cites the SUMMARY that recorded it. Row 9 was found **after**
the phase gate, by the cross-AI review of 2026-08-05, and is entered here rather
than deferred to a later document — see the **Recorded discrepancy** note below,
which is amended rather than replaced so the count's own history survives.

| # | Plan | The check | Why it passed for the wrong reason |
| --- | --- | --- | --- |
| 1 | 15-06 | the class-lookup anti-drift test | scanning `__all__` finds **zero** `ArtifactClass` instances — the two shipped constants are not in it — so the test that exists to keep the hand-maintained mapping honest would have passed while proving nothing. Recorded as `[Rule 1 - Vacuous assertion]`. |
| 2 | 15-13 | Gate 2 in `examples/00-quickstart` | `QuickstartPlan(required=operators.keys())` — the declared side read from the engine's own registry. The origin instance, and the one 15-13's R6 turned into a rule for every later rewrite. |
| 3 | 15-14 | Gate 2 in examples 01 and 02 | neither pre-rewrite file had a Gate 2 check *at all*, because both built their plan from `operators.keys()`. The four new assertions are marked **New** rather than relocated, so the no-loss audit stays honest in both directions. |
| 4 | 15-15 | example 07's "nothing else changed" claim | "nothing else changed" is exactly the shape of claim that passes because a test never looked. Now watched by an AST **tripwire** *and* defended observationally from two runs, with the role-set checked against a declared `persisted_artifact_roles` so two empty sets cannot agree vacuously. The observational half is the load-bearing one: the AST half catches the shapes it names and no others. |
| 5 | 15-16 | Gate 2 in `examples/08-e2e-demo` | fixed at the instance, and the module docstring now states plainly that editing the artifact alone moves both ends and is **not** detected — the over-claim this phase had made repeatedly. |
| 6 | 15-17 | **lineage strict equality in `examples/06-decision-replay`** | **A correctness defect.** `GridLoadPlan(required=...)` was fed from `operators.keys()` in the record phase *and* from `self._registry().keys()` in `GridReplayEnvironment.resolve_plan` — so Gate 2 compared a value against itself in the original decision **and again in the forensic replay that exists to prove that decision**. The file whose entire subject is audit-by-construction was, at that seam, auditing nothing. |
| 7 | 15-18 | **the A2A entitlement assertion in `examples/04-cross-process`** | **A correctness defect.** Both processes read one `artifacts/controlplane.yaml`; the consumer computed the producer's policy version from it, registered that same mapping as its own bundle, and asserted the two were equal. That compared **two reads of the producer's own file**, in the example that exists to demonstrate Control Plane admission verification. It could not fail; dropping the policy bundle from both sides would have kept it green. |
| 8 | 15-19 | the fail-closed evidence in `examples/05-workflow-hitl` | `transport.submissions(tenant=...) == ()` is meaningful only **between** the four refusals and the first legitimate admission. Relocated naively to read after the run, it counts legitimate landings and goes green for a transport that admitted every refusal too, as long as the count happens to match. Recorded by 15-19 as the **eighth** instance. |
| 9 | 15.1-09 | Gate 2's two arguments at every `run_gates` call site in the examples suite | Across **nine** files, `ProductLineage(operators_invoked=execution.operators_invoked)` was compared against `engine_resolved=execution.operators_invoked` — the same **object**, not merely the same value (D-GATE-15 second amendment, correction (2)). Deliberately **not** bolded as an outright correctness defect: the products these examples served were in fact correct and no wrong answer was ever produced, so the "two are outright correctness defects" clause above stays true. What was absent was the **proof** — the gate could not have failed for any edit an author could make. Closed by design E2 (D-IMPL-86): a second authored artifact, a binder between plan construction and `ProjectionEngine.execute`, and Gate 2 restated as assembly-path integrity. |

**Two further second-site occurrences are documented but deliberately not
numbered**, because each is a second site of an already-counted defect rather
than a new discovery:

- **15-19**, same file: the escalation check read its expected handler out of
  `workflow_definition.exception_refs` — *the very document the engine resolved
  the handler from*. It now reads an independently authored
  `drive.expected_exception_handler`, so it is two statements agreeing rather
  than the engine agreeing with its own input.
- **15-20**, `examples/external/00-hello-context`: the Gate 2 tautology existed
  **twice** — in `serve.py` and again in `run.py`'s
  `HelloReplayEnvironment.resolve_plan`, which would have reproduced the
  original decision's tautology *inside the replay that exists to prove that
  decision*, structurally the same shape 15-17 found in a different file. 15-20
  states explicitly that the running finding "did not gain a ninth instance
  here" — the pattern was already named; what its second site demonstrates is
  that **a rewrite fixing the tautology only where the plan text names it leaves
  the replay path carrying it.**

**Amended 2026-08-05 (plan 15.1-09): row 9 does not contradict 15-20.** 15-20's
explicit declining of a ninth remains true *as 15-20 meant it* — the tautology
in `examples/external/00-hello-context`'s replay path was a second site of an
already-counted defect, and it is still listed immediately above as one. Row 9
is a different shape: not a second site of one file's finding, but the
**record-leg call site itself, tree-wide across all nine drivers**. A per-file
reading found no ninth; a cross-file reading of the same call shape found one.

**Recorded discrepancy.** The phase's handoff note (`.continue-here.md`) put the
count at seven and the executor brief put it at eight, attributing new instances
to both 15-19 and 15-20. Counted from the SUMMARYs themselves, the correct
figure is **eight numbered instances**: 15-19's SUMMARY numbers its fail-closed
finding as the eighth, and 15-20's SUMMARY explicitly declines a ninth. The
ledger above is the count this audit stands behind.

**Amended 2026-08-05 (plan 15.1-09).** The sentence immediately above — "The
ledger above is the count this audit stands behind" — was true of the eight-row
ledger it was written against, and is now falsified. The post-gate cross-AI
review of 2026-08-05 (cursor) found a ninth: the Gate 2 call-site collapse, now
entered as row 9. **The audit's eight was an undercount**, and D-GATE-15's first
amendment recorded the consequence. This note is appended rather than replacing
the paragraph above it, because deleting the record of the earlier count dispute
would be exactly the audit-trail destruction §5.3 row A-6 argues against — the
history of this count is part of what the section is for, and a ledger that has
been wrong twice about its own size is worth showing as such.

**Why this is the phase's strongest argument beyond ergonomics.** Neither
correctness defect was visible until **typed artifacts gave the declared side an
authored source**. While the declaration and the resolution came out of the same
bundle read, no amount of reading the assertion could tell you it was comparing
a value with itself. And no line-count measurement would have surfaced either —
they are invisible to Criterion 1 and were found only because Criterion 2's
reshaping forced the two sides apart.

---

## 5. The phase-close review, its triage, and what is carried forward

CLAUDE.md §3.1 step 1: the self-review runs **before** anything is presented to
Dave, and a review report is a precondition of requesting approval, never a
substitute for it. `/gsd-review --phase "Phase 15" --all` was run against the
deliverables in this document — the audit, the completeness test, the
assembler, the three standing gates, and `src/ccf/deployment` — rather than
against the plan text.

`claude` was excluded for independence: this review ran inside Claude Code.

| Reviewer | Verdict | Blocking | Advisory |
| --- | --- | ---: | ---: |
| codex (`gpt-5.1-codex-max`) | not ready to present | 2 | 2 |
| cursor | ready to present | 0 | 6 |
| gemini | ready to present | 0 | 2 |

### 5.1 Blocking findings — both closed inside the phase

**B-1 — the G-B guard was weaker than this document claimed (codex).**
`tests/products/test_required_operators_guard.py` refused a `.keys()` read off
a named receiver but not off a **local alias** of one: `ops = self._registry()`
followed by `ops.keys()` passed, while the module docstring claimed the AST
approach defeated rename-style bypasses. A guard presented as the structural
closure of a fidelity invariant may not over-claim.

*Closed.* The refused-receiver set is now computed to a **fixed point** over
local assignments, `:=` bindings, and annotated assignments, so alias chains are
followed rather than only the first hop; `_receiver_name` sees through a walrus
and an `await`. Four new probes exercise the alias spellings, and the docstring
now states what the approach does **not** buy: this is receiver aliasing, not
dataflow — a registry arriving through a helper's return value or under a name
the module does not recognise is out of reach. The claim is "every spelling the
phase found, and the obvious evasions of them", not "impossible to write".

**B-2 — ERGO-16 says "every"; the measurement says 152 remain (codex).**
The requirement's checkbox and the delivered number disagreed with nothing in
between. *Closed as far as an executor may close it:* §2.3 now accounts for
**every one of the 152 lines** by category with its reason, and the reading of
"every" is carried to the phase gate as a ruling item rather than resolved
here. Two reviewers did not raise it; that does not make it wrong, and §3.1
classes an unsurfaced decision as blocking.

### 5.2 Advisory findings, acted on immediately

Three were cheap and strengthened a gate, so they were fixed rather than
carried:

- **The schema-header gate used a floor, not a set (codex).** `>= 9` would let
  a directory drop out of coverage silently while the count stayed above the
  floor. It now asserts the **exact** ten-directory set by name.
- **The baseline provenance check was described more strongly than it is
  (codex).** It keys on commit-subject text, not a pinned hash, and returns
  without asserting where git is absent or history is shallow. The docstring now
  says so: corroboration for the digest, not an unfakeable provenance proof.
- **"The declared side of Gate 2" was imprecise (cursor).** Gate 2's own two
  arguments are `lineage.operators_invoked` and `engine_resolved`;
  `required_operator_keys` is *upstream* of both. Corrected in §3 and in the
  guard's docstring and failure message, before Phase 16 quotes either.

### 5.3 Advisory findings carried forward

| # | Finding | Disposition |
| --- | --- | --- |
| A-1 | 52 additions include package re-exports (`ccf.deployment.X` **and** `ccf.deployment.manifest.X`), so the migration note can read as 52 new concepts (cursor) | **Phase 16.** Permitted by D-15B and additive under D-14. Phase 16 should document `from ccf.deployment import …` as the single preferred day-1 import and treat submodule FQNs as implementation detail. |
| A-2 | No fragment covers the surface toolchain itself — `tools/dump_surface.py`, `make surface`, baseline immutability (cursor) | **Phase 16.** Not a Criterion 6 miss: fragments record *changes*, and the toolchain is 15-01's own machinery, described in `docs/surface-changes/README.md`. A maintainer-facing "how the surface record works" page belongs in the documentation rewrite. |
| A-3 | The published docs still describe the pre-15 surface (cursor) | **Phase 16, already scoped.** Phase 14's G-01 was deliberately deferred to 16 for exactly this reason, and the documentation rewrite is a stated Phase 15 non-goal. `make docs-strict` green means the site builds, not that it is current. |
| A-4 | Several `tests/examples/test_*_output.py` checks compare `required_operator_keys` against `operators_invoked` and document that editing the artifact alone moves both ends (cursor) | **Carried as a standing caution.** The honesty is deliberate (15-13 R6). Phase 16 must not promote those as independence proofs; the independent statements are the *consumer-side* ones (15-18) and the artifact-vs-engine comparison. |
| A-5 | Shared `public/` prose collisions across the rewrite waves — `docs-strict` catches an orphaned include, not a mis-pointed one (round-2 cross-AI, open since mid-execution) | **Closed by practice, carried as a gap.** Every rewrite plan opened each including section and read it against its new target, and 15-17, 15-18 and 15-16 each corrected prose the rewrite had falsified. No automated check exists for a mis-pointed include, and building one is Phase 16's concern since Phase 16 rewrites the prose anyway. |
| A-6 | Stale plan text — execution corrected several plans and the PLAN.md files still carry the old guidance (round-2 cross-AI, open since mid-execution) | **Carried, deliberately.** Only 15-07's was amended in place (`0a4e433`). This plan hit three instances itself and recorded each in its summary rather than editing history. A PLAN.md is the record of what was *intended*; the SUMMARY is the record of what was *built*, and rewriting the former to match the latter would destroy the audit trail the discrepancies live in. **The correct fix is a convention, not an edit**: a phase's auditor reads SUMMARYs, and this document says so. |
| A-7 | A future "strict mode" could make the operator registry a read-only proxy refusing `.keys()` during projection, moving the G-B check from static AST to runtime (gemini) | **Out of scope; a candidate `D-IMPL-NN` for a later Phase D mini-cycle.** It is new fabric behavior, which Phase 15's non-goals exclude. |
| A-8 | D-IMPL-80's "role governs registration and pinning, never visibility" is subtle and needs explicit documentation (gemini) | **Phase 16.** `role: load` artifacts are reachable on `BootedFabric.artifacts` and absent from the replay pin set; the reference pages must say both. |

### 5.4 Two open questions carried to the gate

Neither is a defect; both are decisions this plan declines to make on Dave's
behalf.

1. **Does `docs/SURFACE-CHANGES.md` publish in v0.2's site, or wait for Phase
   16?** Phase 14 established `public/` as the published tree with
   default-deny-by-existence, and the precedent is to write in `docs/` and let
   the documentation phase `git mv`. Followed here; the editorial call is open.
2. **Should the deferred idea — recording the deployment-manifest content hash
   on the replay record — become a `D-IMPL-NN` for a Phase D mini-cycle?** It
   was surfaced during planning and deliberately left out of scope.

Plus the ERGO-16 reading from §2.3.

---

## 6. Phase 15.1 gap closure: criterion-by-criterion evidence

Phase 15.1 closed the two HIGH defects a post-gate cross-AI review found against
Phase 15 (CR-1, CR-2), plus the mechanism Dave ruled in at **D-IMPL-86** to close
the second properly. Because design E2 revises the gated 15-09 decision, the
phase ran as a **Phase D mini-cycle under CLAUDE.md §3.1**, with D-IMPL-86 and its
correction of 2026-08-05 as the ruling of record.

**Read the numbering warning at the top of this document first.** The nine rows
below are **Phase 15.1's** success criteria, quoted from `.planning/ROADMAP.md`'s
`### Phase 15.1:` section. They are *not* Phase 15's, which §§1–5 answer. Where a
Phase 15.1 criterion number collides with a Phase 15 one — Criterion 1 most
sharply — the row says which it means.

> **DATED NOTE — 2026-08-06. This section was written for the gate of 2026-08-05,
> which was withdrawn. Read it with that history in view.** Everything in §§6.1–6.6
> below is a record of what plan 15.1-10 observed against the merged tree on
> **2026-08-05**, and it remains accurate *as of that date*. It is **not** the
> record of how Phase 15.1 closed. What happened after it was written:
>
> 1. The `/gsd:execute-phase` workflow runs its `code_review_gate` step **after**
>    the phase gate, so `gsd-code-reviewer` first ran against the phase's 45
>    changed Python files once the approval was already logged. It returned
>    **3 Critical, 7 Warning, 5 Info** (`15.1-REVIEW.md`).
> 2. Dave **withdrew** the approval on 2026-08-06 rather than carry the findings
>    forward (`D-GATE-15.1 (withdrawal, 2026-08-06)` in `docs/DECISIONS.md`).
> 3. **Five review rounds** followed — Criticals **3 → 1 → 1 → 1 → 0** across
>    `15.1-REVIEW.md`, `15.1-REVIEW-FIXES.md`, `-2.md`, `-3.md`, `-4.md` — closed
>    by remediation plans **15.1-11 … 15.1-17**.
> 4. Dave **re-approved on 2026-08-06** on the round-5 verdict of 0 Critical /
>    2 Warning / 4 Info (`D-GATE-15.1 (re-approved, 2026-08-06)`).
>
> **Two consequences for a reader of §§6.1–6.6.** *(a)* The verification matrix in
> §6.2 is superseded — its `make test` figure of 2059 predates seven remediation
> plans; the matrix of record is the one in the re-approval entry, observed
> 2026-08-06. Several file:line citations in §6.1 have likewise moved (the CR-01
> containment fix shifted `ManifestEntry`'s fields and `load_and_boot`'s dispatch
> by roughly 100 lines). *(b)* §6.4's five carried items are **not** the full
> carried set any more. Five further residuals were added by the review rounds —
> **R5-WR-01**, **R5-WR-02**, **R4-WR-03**, the two standing tripwire limits, and
> **IN-F1/IN-F2/IN-F4**. The one file that carries the complete set, each with its
> source review document, is
> `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md`. Phase 16 should
> read that file, not this section, for what it inherits.
>
> Nothing below is edited, because a dated record of what was observed on a date is
> what a later reader consults; rewriting it to match a later tree destroys the
> audit trail (§5.3 row A-6), and this section's own §6.3 is an argument for that
> discipline.

### 6.1 The nine criteria and what establishes each

| # | The criterion (Phase 15.1, quoted) | What establishes it |
| --- | --- | --- |
| 1 | "A manifest that declares an author-versioned class (`ccf.workflow-definition`, `ccf.agent-definition`, `ccf.task-definition`) for typed registration is **refused at load**, with a test that asserts the refusal — not a test that the examples happen to avoid the pattern" — *this is Phase 15.1's Criterion 1, not §2's adopter-surface measurement* | `refuse_registration_the_sdk_fixes` (`src/ccf/deployment/classes.py`), called in `src/ccf/deployment/manifest.py::load_and_boot`'s preflight — before `_preflight_backend` and before any document is read. Tests: `tests/deployment/test_manifest.py::test_an_author_versioned_class_declared_typed_registration_is_refused`, `::test_an_envelope_squat_on_an_sdk_class_id_is_refused`, and `::test_the_ccf_namespace_reservation_is_wide_not_a_four_id_list` (×3 ids). Command: `pytest tests/deployment/test_manifest.py -k "squat or typed_registration"` → **2 passed, 28 deselected**. Every one of the seven collected members was **watched to fail** with the source reverted, and the failure *reasons* recorded (15.1-03-SUMMARY) — three raised `DID NOT RAISE ValueError`, i.e. the squat booted, registered and pinned, which is the executed reproduction of CR-1. The refusal was also watched to **admit**: the four-row matrix in `tests/deployment/test_class_lookup.py` failed exactly its admit rows under forced always-refuse and exactly its refuse rows under forced no-op. |
| 2 | "The registration mode is declared per entry in the manifest and dispatched by `load_and_boot`; the artifact author does not have to know which of two registration paths their class belongs to" | `RegistrationMode = Literal["typed","versioned"]` and `ManifestEntry.registration` — **required, no default** (D-IMPL-85) — in `src/ccf/controlplane/artifacts.py`; `load_and_boot`'s phase two branches on `entry.registration`, with an `isinstance` narrowing that turns a returned `RegistrationRefusal` into a loud raise and **no fallback to `register_typed`**. `docs/schemas/ccf.deployment-manifest.json` carries `registration` in `$defs.ManifestEntry.required`. **163 entries across 11 documents** migrated, count taken by parsing rather than by memory. Test: `::test_a_manifest_entry_naming_no_registration_is_refused`, watched to fail with a default present and pass without one — which is what separates it from passing on the sibling `role` refusal firing first. |
| 3 | "`lineage.operators_invoked` is filled from the product-class declaration — never from `execution.operators_invoked` — in every example that runs Gate 2, and the projection's required operator set comes from its own Control Plane artifact rather than from the product-class artifact, so the declared and executed sets are separately authored" | **Both halves, separately.** *Half one — the tree-wide grep.* `grep -rn "ProductLineage(" -A 2 examples/` shows **thirteen** lineage constructions and **not one** reads `execution`: nine read `frozenset(declared.required_operator_keys)` (the nine CR-2 sites — 00:301, 01:377, 02:387, 03:397, 04/producer_child:391, 06:627, 07:412, 08:885, external/00/serve:495), two read `record.content_generation_path.operator_plan` (the replay legs at 06:391 and external/00/run:221), one reads the consumer's own lineage artifact (04/run:282), and one the HITL example's operator key (05:688). *Half two — the projection reads its own artifact.* **Nine** `artifacts/projection-requirements.yaml` documents exist (00, 01, 02, 03, 04, 06, 07, 08, external/00), each `$schema`-headed at `ccf.projection-requirements`, each named by a manifest entry, and each supplying the plan's `required=` rather than the product class. Structural enforcement rather than grep: `tests/products/test_gate_two_call_shape.py` — 9 gate call sites scanned, **zero violations**. |
| 4 | "A binder **refuses** when `product_class.required_operator_keys != frozenset(plan.required_operators())`, placed … between plan construction and `ProjectionEngine.execute`, **not** inside `load_and_boot` … and a test proves the refusal fires when the two artifacts are edited into disagreement … The residual the placement creates … is named in the deliverables and surfaced at the gate, not left in a docstring" | **Both halves of the amended criterion.** *The refusal.* `refuse_operator_set_divergence(*, declared, plan) -> None` in `src/ccf/deployment/binder.py`, comparing as **sets**, refusing and never repairing. `tests/deployment/test_binder.py` — 5 tests, every case reaching the binder through documents parsed by `load_artifact` (`grep -c "ProductClassDeclaration("` and `"ProjectionRequirements("` are both **0**), including a superset, a subset, and a plan that ignores its own artifact. Both halves watched: forced always-admit failed exactly the four refuse cases, forced always-refuse failed exactly the admit case. At **example** scale the refusal was watched to fire from a one-key edit at all nine sites, from *either* document (15.1-05/06/07 SUMMARYs) — at example 04 it fires upstream of signing and emission, so a consumer can never receive a claim the producer's own plan contradicts. Placement cited at **both** interval bounds, which is what surfaced the finding that the interval was *empty* before the plan was hoisted to a local. *The residual.* Named in four parts in the binder's module docstring, in the `Migration` field of `docs/surface-changes/15.1-04-operator-set-binder.md`, in §6.2 item 5 below, and put to Dave at the gate as a **separate ruling** from the authorship residual. |
| 5 | "Gate 2 is documented for what it verifies — **assembly-path integrity** … and every site asserting that it compares two independently authored sets is corrected, including `src/ccf/products/gates.py`'s module docstring and `:244-250`, the `ProductClassDeclaration` docstring …, and `docs/SURFACE-AUDIT.md` §3.1 item 1. D-IMPL-57's intra-fabric … premise is corrected with it" | All four named sites corrected, plus five the criterion did not name. `src/ccf/products/gates.py` (module docstring gate-2 sequence `:14-24`, and `run_federated_gates` `:258-286`); `ProductClassDeclaration` at `src/ccf/controlplane/artifacts.py::ProductClassDeclaration`; **§3.1 item 1 of this document** (lines 358-381 — the claim is quoted, then stated as not-true-as-shipped, then E2's answer). Unnamed but found and corrected: `src/ccf/projection/plan.py`'s module docstring, which carried the same over-claim; `public/tutorial/adopters-guide.md` and `public/reference/artifacts/product-registration.md`, the two adopter-facing pages; **eight** `product-class.yaml` comment blocks (not the two the widening named); and `docs/schemas/ccf.product-class.json`, a *generated* file that embeds the class docstring verbatim as `description`. D-IMPL-57 corrected by an **appended dated note** — `git diff --numstat docs/DECISIONS.md`: 2 insertions, **0 deletions**, so the original entry is byte-unchanged and the ruling is not reopened. **Four further sites were found at the phase-close review and corrected there** — see §6.6, and note the reason they were missed: the phase swept for one *spelling* of the over-claim and there were two. Final sweep: no site in `src/`, `runtime/`, `tests/`, `examples/` or `public/` asserts the corrected-away property in either vocabulary; the surviving occurrences are all negations or a quoted-then-answered superseded claim. |
| 6 | "A tripwire refuses any call site filling both of Gate 2's arguments from `execution`, closing the shape CR-2 found" | `tests/products/test_gate_two_call_shape.py` (D-IMPL-86 element 5), scanning `src`, `runtime`, `examples` at **lexical-body** granularity, resolving identifier *paths* (not bare roots) with alias tracking to a fixed point, and treating `frozenset`/`set`/`tuple`/`list`/`sorted`/`cast` as transparent. Five malicious probes caught, three benign probes correctly not caught, and a cross-body negative test proving the scan is not an `ast.walk` from the class node. Watched to fire: reverting the declared-side `operators_invoked=` argument inside `examples/00-quickstart/run.py::run` to `execution.operators_invoked` failed the tripwire with a message naming both lines. A companion binder-coverage tripwire holds **all eleven** projecting bodies under `examples/` to naming the binder — floors of 9 gate call sites and 11 projecting bodies, each proven non-vacuous by raising it and watching the module fail. |
| 7 | "`docs/SURFACE-AUDIT.md` §4.1 is corrected: 'eight instances' is an undercount, and the ninth (the Gate 2 call-site pattern) is entered with the same accounting discipline" | **§4.1 of this document.** Headline reads nine; row 9 is entered with its plan, its check and its reason. It is **deliberately not bolded** as an outright correctness defect, with the reason stated in the row — the products served were correct; what was absent was the proof — which keeps the "two are outright correctness defects" clause true. Both the "Recorded discrepancy" paragraph and the second-sites block are **amended, never deleted** (verified: zero deletions in those passages), including a note reconciling row 9 against 15-20's explicit declining of a ninth: a per-file reading found none, a cross-file reading of the same call shape found one. |
| 8 | "The new AST gates are restated as **tripwires** … rather than as structural enforcement on par with single-writer DI, strengthened by D-IMPL-86's finding that no AST gate can distinguish an authored literal from a transcribed one" | The `Closed structurally, in two layers` heading in §4 is **withdrawn with its reasoning stated** ("it had the correction backwards — it explicitly forbade the weaker framing that is in fact the accurate one"); layer 2 is restated as a tripwire a *receiver rename* defeats, which is what the guard's own module docstring in `tests/products/test_required_operators_guard.py` always said and this audit had been contradicting. `grep -c "tripwire" docs/SURFACE-AUDIT.md` → **4** (was 0). The genuine walls stay walls: `git diff --exit-code` against the phase base for `tools/lints/` and `tests/deployment/test_direct_construction.py` exits **0** — the import lints were not restated. |
| 9 | "The public-surface manifest and the `--check` drift gate stay green; no replay dimension is hidden by anything this phase adds" | *Manifest and gate.* `docs/surface/v0.2-surface.json` regenerated once by this plan (the single-owner rule); `tools/dump_surface.py --check` and `tools/assemble_surface_changes.py --check` both exit **0**, so the documented-drift gate is at plain bytes-equality with nothing unclaimed. `git diff --exit-code docs/surface/v0.2-surface-baseline.json` exits 0 — the digest-pinned frozen baseline was **not** touched. *No replay dimension hidden.* Stated explicitly because the criterion asks for it: the projection-requirements artifact is `role: register` at **all nine** sites (verified per file), so it is registered and pinned and therefore **enters** Decision Replay dimension 2 rather than being hidden from it — the same argument `product-class.yaml` already carried. And `ArtifactPin.registration` (**D-IMPL-83**) adds a **recorded fact without adding a selector**: it is a field on the pin, and `ResolvedPins` still exposes exactly one public method, `version_for`, held there by `tests/deployment/test_manifest.py::test_resolved_pins_has_exactly_one_public_method`. A `registration_for` accessor would have moved *selection* into the SDK; recording the mode does not. The audit log remains primary evidence; the pin-set content hash changing is an accepted, documented consequence. |

### 6.2 The verification matrix, as observed

Every command below was run by this plan against the merged tree and its exit
status read. A gate not run is a gate this document cannot report. **The figures
are from the re-run after the phase-close review's three blocking findings were
closed** (§6.6), not from the pre-review run; both runs were green and reported
identical numbers.

| Gate | Command | Observed |
| --- | --- | --- |
| Lints (CINV-01/02/03, orchestration split, No-Hardcoding) | `python -m tools.lints --all` | **exit 0** |
| Typecheck | `make typecheck` | **exit 0** — `no issues found in 170 source files` |
| Full suite | `make test` | **2059 passed, 2 skipped**, 105 warnings, 319.77s |
| Ten examples | `make examples` | **exit 0** — all ten invoked and passed (00–08 + `external/00`; `make` stops on first failure) |
| Docs | `make docs-strict` | **exit 0** — pre-build scan, `mkdocs build --strict`, site scan |
| Composite | `make ci` | **exit 0** |
| Committed schemas | `make schemas` then `git diff --exit-code docs/schemas/` | wrote 24 schemas; diff **exit 0** |
| Example artifact `$schema` headers | `make schema-headers` | **exit 0** — checked 10 artifact directories |
| Public-surface drift | `tools/dump_surface.py --check` | **exit 0** |
| Curated log assembly | `tools/assemble_surface_changes.py --check` | **exit 0** |
| Frozen baseline immutability | `git diff --exit-code docs/surface/v0.2-surface-baseline.json` | **exit 0** |

Excluded by design and deliberately not "fixed" here: example 03's `--mode live`
leg, `ext-00`'s live legs, example 08's `--live`, and the perf battery
(D-10/D-11/D-IMPL-70).

### 6.3 Three criteria this phase found to be wrong as written

Recorded rather than satisfied, because a criterion met by changing the code to
suit a bad check is the defect this phase was convened to close.

1. **`grep -rn "operators_invoked=execution.operators_invoked" examples/` must
   NOT be empty.** Plan 15.1-10's own verification step 6 asks for no output.
   Three executors concluded independently, from disjoint files, that zeroing it
   would *undo* the phase: every surviving occurrence is a **result-carrier
   dataclass field** handing the *engine's* resolution to the paired test module,
   which is exactly what turns
   `assert result.product.lineage.operators_invoked == result.operators_invoked`
   from a tautology into a two-source comparison. **The count observed at phase
   close is 5**, not the 8 those executors predicted — examples 00, 01 and 02
   route the same value through a named local (`engine_transcription`), so the
   *literal* string is absent while the *property* is identical. The 8 was
   carried from 15.1-07 to 15.1-08 to the phase-close brief without being
   re-measured against the post-15.1-05 tree. The substantive check is
   `grep -n "ProductLineage(" -A 2 examples/`, and the structural one is the
   tripwire in row 6 above.
2. **`grep -c "independent witness" src/ccf/products/gates.py` cannot reach 0
   honestly.** It is **3**, and all three are negations or the quoted superseded
   claim answered on the next line. The decisive evidence that this is a
   line-wrapping artifact and not a semantic check: `src/ccf/deployment/binder.py`
   contains the *identical negated sentence* and greps to **0** only because the
   phrase wraps across a line break. A grep measures token absence; the property
   is claim absence, and the two diverge **in both directions**.
3. **`docs/SURFACE-CHANGES.md` is not ordered `15-02…15-20` then
   `15.1-01…15.1-09`.** The assembler groups by change type first (Added /
   Reshaped / Removed / Behavior), then by public / not-public, so fragment order
   applies **within** each group. Verified mechanically: all **six** groups are
   monotonic under the `(major, minor, plan)` key, with every 15.1 fragment
   sorting after every Phase 15 one. Also, only **four** 15.1 fragments exist
   (01–04) — plans 15.1-05 through 15.1-09 added no public Python name, so they
   correctly wrote none.

### 6.4 Carried to the gate — five items, recorded rather than closed

The register §5.4 established, continued for this phase. **Items 4 and 5 are two
distinct residuals of the same family, not one residual stated twice.** Merging
them would understate what this phase asks Dave to accept.

**Disposition at the gate (`D-GATE-15.1`, Dave, 2026-08-05).** All five items are
**carried forward — accepted at approval, and not closed by it.** Dave's verbatim
reply to the gate presentation was **"Approved"**: one approval of the phase as
presented, **not five separate written rulings** on the five items the presentation
enumerated. Items 1, 4 and 5 were put to him as ruling items R-4, R-3 and R-2
respectively, and each remains open and inherits to Phase 16; items 2 (D-IMPL-81)
and 3 (`BootedFabric.artifacts`) were already carried debt and stay so. The one
item the approval does **ratify** is not in this register — it is R-5, plan
15.1-02's Criterion-6 gate edit to `tests/test_surface_completeness.py` assertion
3, which was presented explicitly as an executor-made gate edit needing human
ratification (`15.1-REVIEWS.md` §6). Nothing here should be read as resolved. A
reader arriving at this register after the gate is reading five open items.

1. **The HTTP `/schema` route's contract.** The route, the `ccf schema export`
   CLI verb and `tools/dump_schemas.py` all enumerate `SDK_ARTIFACT_CLASSES` — 12
   typed-registerable classes — and answer **404** for the six author-versioned
   ones (`ccf.agent-definition`, `ccf.prompt-artifact`, `ccf.task-definition`,
   `ccf.workflow-definition`, `ccf.skill-catalog-entry`, `ccf.skill-grant`),
   *all six of which have committed schemas in `docs/schemas/`* (verified). Phase
   15 deferred this on the grounds that the route "documents what a *manifest*
   may name"; after 15.1-03 that framing is no longer accurate — a manifest **may**
   name all six, as `registration: versioned`. The route's real contract has
   narrowed to "the classes a manifest may name for **typed** registration". The
   docstring now says so precisely; the ruling is still owed. Recorded in
   `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md`.
2. **D-IMPL-81 — pinning the deployment manifest itself.** Ruled out of Phase
   15.1's scope by the two-HIGH-items ruling and unaffected by the E2 widening.
   Still **open debt** against Phase 16 or later.
3. **`BootedFabric.artifacts` role blurring.** `role: load` entries are reachable
   on `artifacts` and absent from the replay pin set, because role governs
   registration and pinning, never visibility (D-IMPL-80 amendment). Both halves
   need saying together in the reference pages; §5.3 row A-8 routes it to Phase 16.
4. **D-IMPL-86's *authorship* residual.** A deployment that reads one artifact
   into the other still collapses the binder, so dual authorship remains
   **convention-assisted at the authoring boundary** even though the check itself
   is structural. D-IMPL-86 accepts this in its own "Consequences accepted"
   paragraph, and D-IMPL-86 strengthens *why* it cannot be closed by a gate: no
   AST gate can distinguish an authored literal from a transcribed one. Recorded
   in the binder's module docstring and here rather than softened.
5. **D-IMPL-86's *placement* residual — a second, distinct residual.** Stated in
   the four parts the binder's module docstring carries, from the
   `D-IMPL-86 (correction, 2026-08-05)` entry:
   1. The binder sits **between plan construction and `ProjectionEngine.execute`**,
      in adopter code, because `load_and_boot` has no `ProjectionPlan` in scope at
      any of its preflights (`src/ccf/deployment/manifest.py::_resolve_tenant` as
      the correction cites it — it cited a line inside that helper, and the line
      has since moved twice, which is exactly why `D-IMPL-114` retired the form). The SDK therefore never invokes it.
   2. It **returns `None`**, so nothing observable at runtime proves it was called
      — no product field, no pin, no audit event. A deployment that omits it
      produces byte-identical output.
   3. **Nothing outside the SDK's own `examples/` tree holds a deployment to
      calling it at all.** An adopter who omits the call gets no error, no
      warning, and no degraded output.
   4. The AST coverage check that enforces the call
      (`tests/products/test_gate_two_call_shape.py`) is **scoped to `examples/`
      only** — a check on the SDK's own teaching material, not on adopters.

   It is **carried to Phase 16** and surfaced at this gate for Dave's ruling,
   because it is the same shape as the defect this phase was convened to close: a
   governance guarantee that holds by convention outside the tree the SDK controls.

### 6.5 Two further items this phase surfaced, for the record

Neither is a criterion and neither is a residual of the mechanism; both are
things a later reader would otherwise have to rediscover.

- **Correcting a docstring silently changes a shipped schema.** `make schemas`
  embeds each class docstring verbatim as the JSON Schema `description`, so
  `docs/schemas/ccf.product-class.json` — the ERGO-12 authoring baseline an
  adopter's editor reads — carried the false "two independent mechanisms" claim
  until it was regenerated. It was found by a red `tests/cli/test_schema_export.py`,
  not by inspection. Any future docstring correction to a contract class is also a
  committed-schema change, and the drift assertion in the always-on `test` job is
  what makes that visible rather than silent.
- **The SDK refuses a wrong registration path at the *manifest* seam and not at
  the *registry* seam.** `examples/05-workflow-hitl/run.py` registers the
  author-versioned `ccf.prompt-artifact` through `register_typed`, which is legal
  under the code as built — `refuse_registration_the_sdk_fixes` guards the manifest
  path by design, and a direct `registry.register_typed` call is the adopter's own.
  Whether that asymmetry is intended is a design question, not a defect, and it is
  recorded in `deferred-items.md` rather than resolved here.

### 6.6 What the phase-close review found, and the sweep defect behind it

The full round, its triage and every finding's source verification live in
`.planning/phases/15.1-ergonomics-gap-closure/15.1-REVIEWS.md`. Two things belong
in the audit of record.

**Four more sites asserted the corrected-away claim, and Criterion 5 was not
actually met until they were fixed.** Cursor found one; re-sweeping on its
vocabulary found three more.

| Site | What it asserted |
| --- | --- |
| `src/ccf/deployment/__init__.py` | "Lineage strict equality … is a real check precisely because those two values arrive from two independent sources" — in `/src`, in the package docstring of the package the binder lives in |
| `tests/products/test_required_operators_guard.py` | the guard's **failure message** told an author the declaration and resolution "must remain two independent mechanisms" and to "Declare the keys from the `ccf.product-class` artifact … instead" — which after E2 is the one thing that collapses the pair the binder compares |
| `tests/products/test_gate_independence.py` | module title and rationale, both asserting the two inputs "arrive from two independent sources" — in a module plan 15.1-08 amended without correcting the claim above its own addition |
| `tests/lints/test_deployment_gates_ban.py` | the same sentence, as the lint rule's stated justification |

All four are corrected to the assembly-path reading, with the transcriber
mechanism named and authorable drift pointed at the binder. **No assertion,
refusal condition, scan constant or lint rule was touched** — only the claims
about why they exist.

**The defect worth naming is the sweep, not the sites.** Plan 15.1-09 swept for
the phrase **"independent witness"** — the *engine-as-witness* spelling — and
corrected nine sites. These four use a second spelling of the same over-claim:
**"two independent sources"**, the *two-inputs-to-the-gate* spelling. One false
property, two vocabularies; a search keyed to one found one. This is §6.3 item 2's
lesson recurring inside the very phase that recorded it — **a token search is not
a claim search** — and it is the reason Criterion 5's evidence row now names the
sweep rather than a grep count.

For Phase 16: correcting a claim means sweeping for the *claim*, in every phrasing
the tree has used for it. The two phrasings known so far are recorded above.

