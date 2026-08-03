# Phase 13: Examples Suite Upgrade - Pattern Map

**Mapped:** 2026-08-02
**Files analyzed:** ~26 (8 READMEs + ~16 artifact files + optional run.py touches)
**Analogs found:** all — every file to modify has an in-repo analog (this phase modifies existing files; nothing is created from scratch except possibly a shared gloss/template reference)

## File Classification

This phase is documentation + definition-artifact work. All files are modifications of existing files.

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `examples/00..07/README.md` (8 files, rewrites) | docs | n/a (narration) | `examples/08-e2e-demo/README.md` + `examples/05-workflow-hitl/README.md` | exact (prose bar + section shape) |
| `examples/01-agent-basics/artifacts/agent.yaml` (D-06 enrichment) | config (agent definition artifact) | interpreted-by-factory | itself — already the best-commented artifact in the suite | exact |
| `examples/NN/artifacts/controlplane.yaml` (enrichment + `expected` blocks) | config (Control Plane bundle) | interpreted-by-run.py, runtime-asserted | `examples/00-quickstart/artifacts/controlplane.yaml` | exact |
| `examples/NN/artifacts/halflife.yaml` (new/enriched where D-07 lands half-life) | config (λ_c table) | interpreted | `examples/00-quickstart/artifacts/halflife.yaml` | exact |
| `examples/05` or `06/artifacts/hitl.yaml` (OverrideBoundary / ReviewQueue additions, D-07) | config (HITL material) | interpreted, runtime-asserted (`expected_gate`) | `examples/05-workflow-hitl/artifacts/hitl.yaml` | exact |
| `examples/NN/run.py` (only where a new artifact field needs interpreting, D-08) | script (interpreter + asserter) | read artifacts → run fabric → assert | `examples/00-quickstart/run.py` (expected-block assertion pattern) | exact |
| Shared gloss table / template skeleton (Wave-0, planner discretion on location) | docs | n/a | README template in `13-RESEARCH.md` Architecture Patterns section | exact (already drafted) |

## Pattern Assignments

### READMEs 00–07 (docs, rewrite to D-02 template)

**Analogs:** `examples/08-e2e-demo/README.md` (prose quality bar), `examples/05-workflow-hitl/README.md` (invariant-table + "what would fail" shape to extend).

**Hook-paragraph pattern** (`08-e2e-demo/README.md` lines 1–13): title of form `# examples/NN-name — one-line hook (REQ tags)`, then a bolded-domain paragraph that states the headline claim as "executed, not asserted."

**Run-it pattern** (`08-e2e-demo/README.md` lines 14–21):
```markdown
## Run it

```
make example-08
```

(or `PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py`).
Exit code 0 means every assertion held — ...
```
Copy verbatim shape per example; Phase 13 appends the D-10 regeneration warning here. Per Research Pitfall 1: for 00–07 the "regeneration" text is "run `make example-NN`, review the assertion output, edit the `expected:` block in `<file>` deliberately — this is a reviewed event"; only 08 documents a literal regeneration command.

**"What would fail" pattern** (`05-workflow-hitl/README.md` lines 33–45): a two-column table `| Invariant | What would fail here |` with each row citing the CLAUDE.md/whitepaper section or D-IMPL. This existing table IS the D-02 "What would fail" section — extend it, don't replace it. It also doubles as the D-06 success test for example 01 (one concrete failure per axis).

**Citations pattern** (`05-workflow-hitl/README.md` lines 47–55): bulleted CLAUDE.md §§, whitepaper §§, D-IMPL refs. Becomes the "Whitepaper / CLAUDE.md sections exercised" section.

**"What to change first" / Adapt-it pattern** (`05-workflow-hitl/README.md` lines 70–81): names exact artifact file + key, with a "flip X and re-run to watch behavior change with zero code change" verb. Copy this framing — it is D-08's teaching point and D-11's required concreteness:
```markdown
`artifacts/hitl.yaml` — flip `signed_binding_required` and re-run to
watch behavior change with zero code change ... `run.py` is thin
mechanism; deleting the artifacts leaves it nothing to run (§6.4).
```

**Anti-pattern in the analog:** `08-e2e-demo/README.md` lines 50–54 end by linking `docs/demo-walkthrough.md`. Per D-01, the upgraded 00–07 READMEs must be self-contained — do NOT copy that outbound-walkthrough section. Also do not copy any `--8<--` include machinery (D-03; none exists in READMEs today, keep it that way).

**Section order is fixed by D-02** (see 13-RESEARCH.md lines 109–118 for the ready-made skeleton): What this demonstrates → Run it → The story → Artifact-by-artifact (table with "yours to edit vs mechanism" column, D-12) → Whitepaper/CLAUDE.md sections exercised → What to change first → What would fail. Existing READMEs order differently (05 puts "Run it" before "What it demonstrates") — reorder to template while keeping their content.

---

### Definition artifacts (config, interpreted-by-mechanism)

**Analog for header-comment style:** `examples/01-agent-basics/artifacts/agent.yaml` lines 1–10:
```yaml
# Agent-basics agent definition — a declared, versioned Control Plane
# artifact (CLAUDE.md §6.1/§6.2; D-IMPL-28). Field-service domain, D-IMPL-52.
#
# All six specialization axes are here, as values. `/src` holds none of
# them ... Two-field versioning per D-IMPL-28; decimals quoted so they
# parse as text, never floats (D-IMPL-26).
```
Every enriched artifact keeps/extends this style: header citing CLAUDE.md § + D-IMPL, domain tag per D-IMPL-52, and the phase adds the D-11 editable/structural markers (`# [ADAPT] ...` / `# [MECHANISM] ...` per 13-RESEARCH.md lines 126–129 — exact wording is Claude's discretion but must be identical across all eight examples).

**Analog for six-axis structure (D-06):** same file, lines 37–71 — axes 1–6 each carry an `# axis N — ...` comment. D-06 work is making each axis *observably matter* in the run, not restructuring; axes 4/5 resolve through `referenced_artifacts` (lines 19–35: `forced_llm_threshold: "0.30"`, `fail_closed_threshold: "0.75"` — the debt-profile headroom for making axis 5 visible).

**Analog for `expected:` blocks:** `examples/00-quickstart/artifacts/controlplane.yaml` lines 82–91:
```yaml
# What the served product should contain, as declared by the deployment that
# authored the events above. The driver asserts against these instead of
# carrying domain expectations of its own.
expected:
  entity_classes: [customer, account]
  relationship_types: [holds]
  entity_count: 2
```
Every artifact enrichment that changes output updates the co-located `expected` block in the same commit (D-09). The blocks live in: `controlplane.yaml` (00, 01, 02, 03, 04, 06, 07), `skills.yaml` (02, 06), `hitl.yaml` (05, 06 — `expected_gate` under `drive:`), plus `scenario.yaml` checksums + `expected_output.txt` for 08 only.

**Analog for half-life/debt enrichment (D-07):** `examples/00-quickstart/artifacts/halflife.yaml` — row shape per entry:
```yaml
half_life_table:
  semver: "1.0.0"
  entries:
    payment-mandate-status:
      half_life_seconds: 86400
      decay_driver: mandate lifecycle events
      supersession_event: mandate amendment or revocation
```
Critical convention (file header, lines 9–11): **decimal values are QUOTED strings** — the canonical serializer refuses floats. Same rule in `agent.yaml` (`risk_sensitivity: "1.2"`) and `hitl.yaml` (`debt_factors: freshness: "1.0"`). Any new numeric artifact value with a decimal point must be quoted.

**Analog for HITL artifact material (D-07 Override/ReviewQueue placement):** `examples/05-workflow-hitl/artifacts/hitl.yaml` — patterns to copy: `keys:` block for Control Plane keys; approver `identity`/`authentication` structure with `subject_id` = active token `client_id`; `drive:` block for execution drive values; `node_outputs:` for deployment content; explicit key-material comment ("key bytes are never artifact content, only the name is"). The SDK primitives to exercise: `src/ccf/hitl/override.py` — `OverrideBoundary.propose()` (line 194) / `.resolve()` (line 224), records via `OverrideActionRecord`; `src/ccf/hitl/review_queue.py` — `ReviewQueue.submit_for_review()` (line 221) / `.release()` (270) / `.reject()` (304), `ReviewQueueItem` with pinned `output_ref` (validator at line 113). Research recommendation: OverrideBoundary → example 06 (original + override both in replay), ReviewQueue → 05 or 06; don't force both into one.

---

### `run.py` touches (script, only-if-needed per D-08)

**Analog:** `examples/00-quickstart/run.py` lines 351–360 — the expected-block assertion pattern:
```python
# The served view matches what the deployment declared it expects.
expected = control["expected"]
payload = gated.product.payload
assert payload["entity_count"] == expected["entity_count"], payload
```
Pattern properties to preserve when a new artifact field needs interpreting: read the value from the loaded artifact dict (never a code constant), assert with the payload as the assertion message, and add a one-line comment explaining what invariant the assertion witnesses. Any string that looks like a prompt, threshold, or domain vocabulary in run.py fires the No-Hardcoding lint — interpreter code only.

## Shared Patterns

### README template skeleton + gloss table (Wave 0)
**Source:** `13-RESEARCH.md` lines 109–118 (skeleton already drafted) + D-04.
**Apply to:** all eight READMEs. One shared task fixes exact headings and a term→one-line-gloss→whitepaper-§ table (Context Product, L1–L6, half-life λ_c → §7.7, Context Debt D_c → §7.7.4, replay → §7.10.1, Control/Data Plane → §7.8, projection Π → §7.5, ...) so eight parallel tasks don't drift (Research Pitfall 4).

### Atomic-commit + verification workflow
**Apply to:** every per-example task. Enrich artifacts → `make example-NN` → update `expected` blocks → rewrite README → one commit (artifacts + expected + README, body summarizing the output delta, D-09). Before commit: `make example-NN` + `make lint`; phase gate `make ci` (tests outside the example consume example artifacts — `tests/examples/test_demo_generator.py`, `tests/conformance/test_harness_portability.py`; Research Pitfall 2).

### Domain-tenant hygiene
**Source:** `05-workflow-hitl/README.md` lines 57–68 ("Domain rationale") and `hitl.yaml`/`tokens.yaml`. Each example keeps its own tenant vocabulary (`meridian-bank`, `cascadia-fieldworks`, `sterling-mutual`, ...) — enrichment stays inside the example's existing tenant/domain (D-05); tokens stay obviously synthetic.

### Example 03 caution
Enrichment targets the deterministic leg only (`legs/deterministic`); never touch live legs into CI, and verify `__pycache__` is not committed (present in tree under 03/04/08; Research Pitfall 5).

## No Analog Found

None. Every file this phase touches exists, and every pattern needed (README prose bar, artifact commenting, expected-block assertion, HITL primitives) has a shipped in-repo exemplar. The only genuinely new content shape — the `[ADAPT]`/`[MECHANISM]` header markers (D-11) and the artifact-by-artifact "yours to edit vs mechanism" README table (D-12) — is specified directly in CONTEXT/RESEARCH with drafted syntax.

## Metadata

**Analog search scope:** `examples/00`–`08`, `src/ccf/hitl/`, `13-CONTEXT.md`, `13-RESEARCH.md`
**Files read in full or targeted:** 08 README, 05 README, 01 agent.yaml, 00 controlplane.yaml, 00 halflife.yaml (header), 05 hitl.yaml (lines 1–60), 00 run.py (assertion region), hitl module signatures
**Pattern extraction date:** 2026-08-02
