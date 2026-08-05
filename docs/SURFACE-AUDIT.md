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
`docs/surface/examples/after/`. The table is rendered from
`tests/examples/test_surface_audit.py::audit_report()`, which returns four
independent totals and a per-file breakdown, and is **structurally incapable**
of returning a combined figure — `test_audit_report_never_returns_a_combined_figure`
parses its own source and fails on the forbidden names.

### 2.1 Removal and relocation are two figures, never one

Per D-12 there is **no target number**. What follows is the achieved number,
and the executable audit pins it: `test_no_rewritten_example_has_silently_regressed`
compares every `after/` fragment against a live re-measurement, so a later edit
cannot quietly re-inflate an example a rewrite plan already thinned.

`mechanical` is wiring the SDK absorbed — it is *gone*. `relocated` is
assertions and print summaries that moved into `tests/` under D-09 — the work
still exists, in a better place. **They are never summed.** A single "lines
saved" headline would conflate a helper that removed work with a file that
moved lines, and D-12 names that conflation as the risk.

`examples/external/00-hello-context/run.py` is why the rule is not pedantry: its
raw line count **rose** 766 → 781 while its mechanical figure fell 36 → 0. What
disappeared there was a hand-built operator registry and a
registration-prologue-plus-`boot`; what arrived was a nesting level and four
typed reads. A combined figure would have reported that plan as a regression.
`examples/05-workflow-hitl/run.py` is the same shape (858 → 866 raw, 28 → 4
mechanical, 112 → 0 relocated).

### 2.2 Per file, and the tree

| File | mech before | mech after | reloc before | reloc after | raw before | raw after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `examples/00-quickstart/run.py` | 143 | 13 | 40 | 0 | 451 | 350 |
| `examples/01-agent-basics/run.py` | 159 | 14 | 85 | 0 | 619 | 481 |
| `examples/02-skilling/run.py` | 118 | 13 | 68 | 0 | 571 | 544 |
| `examples/03-harness-portability/legs/__init__.py` | 0 | 0 | 0 | 0 | 1 | 1 |
| `examples/03-harness-portability/legs/deterministic.py` | 0 | 0 | 11 | 11 | 507 | 527 |
| `examples/03-harness-portability/legs/live.py` | 0 | 0 | 23 | 23 | 641 | 641 |
| `examples/03-harness-portability/legs/ollama_client.py` | 0 | 0 | 0 | 0 | 147 | 147 |
| `examples/03-harness-portability/run.py` | 145 | 13 | 98 | 54 | 720 | 675 |
| `examples/04-cross-process/producer_child.py` | 143 | 13 | 14 | 1 | 630 | 553 |
| `examples/04-cross-process/run.py` | 53 | 13 | 68 | 1 | 533 | 519 |
| `examples/05-workflow-hitl/run.py` | 28 | 4 | 112 | 0 | 858 | 866 |
| `examples/06-decision-replay/run.py` | 175 | 12 | 130 | 0 | 1320 | 1105 |
| `examples/07-artifact-store-mcp/mcp_store_child.py` | 0 | 0 | 1 | 1 | 135 | 135 |
| `examples/07-artifact-store-mcp/run.py` | 132 | 13 | 27 | 1 | 587 | 596 |
| `examples/08-e2e-demo/generator.py` | 0 | 0 | 0 | 0 | 431 | 431 |
| `examples/08-e2e-demo/run.py` | 161 | 13 | 6 | 6 | 1141 | 1104 |
| `examples/external/00-hello-context/client_adk.py` | 0 | 0 | 1 | 1 | 75 | 75 |
| `examples/external/00-hello-context/client_anthropic.py` | 0 | 0 | 2 | 2 | 97 | 97 |
| `examples/external/00-hello-context/client_bare.py` | 0 | 0 | 5 | 5 | 77 | 77 |
| `examples/external/00-hello-context/fixtures/capture_proxy.py` | 0 | 0 | 7 | 7 | 415 | 415 |
| `examples/external/00-hello-context/fixtures/diff_fixtures.py` | 0 | 0 | 7 | 7 | 93 | 93 |
| `examples/external/00-hello-context/replay_server.py` | 0 | 0 | 9 | 9 | 400 | 400 |
| `examples/external/00-hello-context/run.py` | 36 | 0 | 22 | 22 | 766 | 781 |
| `examples/external/00-hello-context/serve.py` | 132 | 13 | 1 | 1 | 773 | 699 |
| **Tree total** | **1425** | **134** | **737** | **152** | **11988** | **11312** |

**Mechanical wiring removed: 1291 lines** (1425 → 134, a 90.6% reduction).
**Assertions and prints relocated: 585 lines** (737 → 152). These two numbers
are reported side by side and are not added together.

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

### 2.3 The day-1 integration

`examples/00-quickstart/run.py` — the file the phase opened against — is
**451 → 350 raw lines**, with mechanical wiring **143 → 13** and every one of
its 40 assertion/print lines relocated to `tests/`. Both halves of the ROADMAP's
opening complaint are answered: the ~85 assertion/print lines that "no adopter
writes" are out of the published snippets, and the ~105 lines of YAML→typed
marshalling are absorbed into `parse_artifact`-reachable artifact classes.

**The import-line collapse is the secondary win, and it is measurable.** The
quickstart carried **54 import lines across 27 distinct SDK names** before the
rewrite and carries **36** after. Tree-wide, import lines fell **974 → 820**. An
adopter's first impression of an SDK is how many of its names they must know to
write anything at all, and that number went down while capability did not.

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
| The eleven artifact classes (`ccf.resolution-spec`, the four `ccf.operator-parameters.*`, `ccf.signal-batch`, `ccf.perspective`, `ccf.product-class`, `ccf.deployment-manifest`, and the two pre-existing) | YAML → validated typed object through `parse_artifact` | **Nothing.** They replace hand-written marshallers with the same seam that already served half-life tables and debt profiles — same float refusal, same zone-less-timestamp refusal, same resolver suppression. One document, one class. | `ProductClassDeclaration.required_operator_keys` is the case that matters: it gives the *declared* side of Gate 2 an **authored source independent of the engine's resolution**, which is what made the tautologies in §4 findable at all. `PolicyFilterParametersArtifact` deliberately declares **no** `permitted_policy_bundle_versions` (D-IMPL-76) — the adopter passes the pin set, keeping the admission set visible where every other pin is. |
| `ccf.controlplane.artifacts.load_artifact` (behavior, D-02) | reads timestamp-shaped scalars as text | **Nothing — it stopped hiding something.** Previously PyYAML's resolver silently produced a *naive* `datetime`, which the registry then refused as non-canonicalizable, and eleven call sites hand-normalized it six different ways. Now the scalar arrives as `str`, a `datetime`-annotated contract field parses it aware, and a zone-less date-time is **refused at parse** naming D-IMPL-38 rather than read as naive. | `tests/controlplane/test_timestamps.py` pins all five properties, including that the shared `yaml.SafeLoader` is unmutated so YAML parsing elsewhere in the process is unaffected. |

### 3.1 The two places the line was deliberately not crossed

Both were reachable ergonomic wins the phase declined, and each has a standing
assertion rather than a comment:

1. **`run_gates` still takes two independently sourced inputs in adopter code.**
   `candidate.lineage.operators_invoked` is what the producer *declares*;
   `engine_resolved` is what the projection engine *observed itself running*.
   Lineage strict equality (whitepaper §7.6, INV-CH7-47) is a real check only
   because those arrive from two sources. A helper computing both from one input
   would leave the gate green and the invariant gone with no failing test to say
   so. Enforced by the `cinv02-deployment-gates` lint rule — which **takes no
   allowlist** — by `tests/products/test_gate_independence.py` (a perturbation
   regression test plus an AST identifier guard over `src/ccf/deployment/`), and
   by `tests/lints/test_deployment_gates_ban.py`, the opposite-direction guard
   proving the ban did not widen beyond its one importer.

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

**Closed structurally, in two layers.** The earlier framing — that G-B "remains
a pattern-level risk" — no longer holds and must not be carried forward.

**Layer 1, the instances.** Every projection in the suite now declares its keys
from `ProductClassDeclaration.required_operator_keys`, authored in the
product-class artifact. 15-09 defines the field; 15-13 fixes the quickstart
origin; 15-14 through 15-20 carry it through the rest of the suite.

**Layer 2, the pattern.** `tests/products/test_required_operators_guard.py` is a
standing AST guard over `src/`, `runtime/` and `examples/`: any
`required_operators` implementation reading the operator registry's own keys is
a red build, matched on AST identifiers rather than source text so a rename and
a comment both fail to defeat it. Layer 1 closed the instances; layer 2 is what
makes G-B closed rather than merely cleaned up.

### 4.1 What G-B was actually protecting — the phase's strongest finding

The phase found **eight instances of "a check that passes for a reason unrelated
to what it claims to verify."** Two are outright correctness defects, found
independently in the same wave by plans that never communicated. The full ledger
is below; each row cites the SUMMARY that recorded it.

| # | Plan | The check | Why it passed for the wrong reason |
| --- | --- | --- | --- |
| 1 | 15-06 | the class-lookup anti-drift test | scanning `__all__` finds **zero** `ArtifactClass` instances — the two shipped constants are not in it — so the test that exists to keep the hand-maintained mapping honest would have passed while proving nothing. Recorded as `[Rule 1 - Vacuous assertion]`. |
| 2 | 15-13 | Gate 2 in `examples/00-quickstart` | `QuickstartPlan(required=operators.keys())` — the declared side read from the engine's own registry. The origin instance, and the one 15-13's R6 turned into a rule for every later rewrite. |
| 3 | 15-14 | Gate 2 in examples 01 and 02 | neither pre-rewrite file had a Gate 2 check *at all*, because both built their plan from `operators.keys()`. The four new assertions are marked **New** rather than relocated, so the no-loss audit stays honest in both directions. |
| 4 | 15-15 | example 07's "nothing else changed" claim | "nothing else changed" is exactly the shape of claim that passes because a test never looked. Now defended structurally from the AST *and* observationally from two runs, with the role-set checked against a declared `persisted_artifact_roles` so two empty sets cannot agree vacuously. |
| 5 | 15-16 | Gate 2 in `examples/08-e2e-demo` | fixed at the instance, and the module docstring now states plainly that editing the artifact alone moves both ends and is **not** detected — the over-claim this phase had made repeatedly. |
| 6 | 15-17 | **lineage strict equality in `examples/06-decision-replay`** | **A correctness defect.** `GridLoadPlan(required=...)` was fed from `operators.keys()` in the record phase *and* from `self._registry().keys()` in `GridReplayEnvironment.resolve_plan` — so Gate 2 compared a value against itself in the original decision **and again in the forensic replay that exists to prove that decision**. The file whose entire subject is audit-by-construction was, at that seam, auditing nothing. |
| 7 | 15-18 | **the A2A entitlement assertion in `examples/04-cross-process`** | **A correctness defect.** Both processes read one `artifacts/controlplane.yaml`; the consumer computed the producer's policy version from it, registered that same mapping as its own bundle, and asserted the two were equal. That compared **two reads of the producer's own file**, in the example that exists to demonstrate Control Plane admission verification. It could not fail; dropping the policy bundle from both sides would have kept it green. |
| 8 | 15-19 | the fail-closed evidence in `examples/05-workflow-hitl` | `transport.submissions(tenant=...) == ()` is meaningful only **between** the four refusals and the first legitimate admission. Relocated naively to read after the run, it counts legitimate landings and goes green for a transport that admitted every refusal too, as long as the count happens to match. Recorded by 15-19 as the **eighth** instance. |

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

**Recorded discrepancy.** The phase's handoff note (`.continue-here.md`) put the
count at seven and the executor brief put it at eight, attributing new instances
to both 15-19 and 15-20. Counted from the SUMMARYs themselves, the correct
figure is **eight numbered instances**: 15-19's SUMMARY numbers its fail-closed
finding as the eighth, and 15-20's SUMMARY explicitly declines a ninth. The
ledger above is the count this audit stands behind.

**Why this is the phase's strongest argument beyond ergonomics.** Neither
correctness defect was visible until **typed artifacts gave the declared side an
authored source**. While the declaration and the resolution came out of the same
bundle read, no amount of reading the assertion could tell you it was comparing
a value with itself. And no line-count measurement would have surfaced either —
they are invisible to Criterion 1 and were found only because Criterion 2's
reshaping forced the two sides apart.

