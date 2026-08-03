# Phase 12: Synthetic-Data Demonstration - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 8 new/modified files
**Analogs found:** 7 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `examples/08-e2e-demo/run.py` | example entry (pipeline composition + assertions) | batch / request-response | `examples/00-quickstart/run.py` + `examples/01-agent-basics/run.py` | exact |
| `examples/08-e2e-demo/generator.py` | utility (artifact-interpreting data generator) | batch / file-I/O (SQLite) | `perf/synth/generator.py` | exact (discipline; mirror, never import) |
| `examples/08-e2e-demo/artifacts/*.yaml` (scenario, ontology, agent, controlplane, halflife, skills, prompt) | config (definition artifacts) | — | `examples/00-quickstart/artifacts/` + `examples/01-agent-basics/artifacts/` + example 06 `skills.yaml` | exact |
| cycle-detection skill wiring (in run.py) | skill callable + catalog/grant/dispatch | request-response | `examples/06-decision-replay/run.py` (skilled-agent block) | exact |
| `--live` mode branch (in run.py) | CLI flag + opt-in LLM narration | request-response | `examples/03-harness-portability/run.py` `main()`/`_live()` | exact |
| `examples/08-e2e-demo/README.md` | docs | — | `examples/06-decision-replay/README.md` (short, links out) | role-match |
| `Makefile` (`example-08` target, `examples` aggregate) | config (build target) | — | Makefile lines 50-74 | exact |
| `docs/demo-walkthrough.md` | docs (mkdocs-compatible with snippets includes) | — | none in repo | no analog |

## Pattern Assignments

### `examples/08-e2e-demo/run.py` (example entry, L1→L6 pipeline + agent)

**Analog:** `examples/00-quickstart/run.py` (pipeline skeleton) and `examples/01-agent-basics/run.py` (agent factory layer on top).

**Module docstring pattern** (00-quickstart lines 1-18): docstring states what is demonstrated with §-citations, notes every domain value comes from `artifacts/*.yaml` (No-Hardcoding §6.4), and gives the run command. Copy this framing verbatim in shape.

**Loader helpers** (00-quickstart lines 78-95) — copy exactly:
```python
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))

def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38).
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
```
Apply the same UTC normalization when reading ISO-8601 strings out of the SQLite source files (research Pitfall 1).

**Resolution spec + envelope builders** (00-quickstart lines 98-131): `_resolution_spec(ontology)` builds `EntityResolutionSpec` from `ontology["entity_rules"]`/`["relationship_rules"]`; `_envelopes(...)` maps artifact rows to `SignalEnvelope(tenant_id=..., envelope_id=..., source=SourceIdentity(system_id=...), ingestion_timestamp=_instant(...), observed_time=_instant(...), raw_payload=dict(...))`. The demo replaces the YAML event list with SQLite `SELECT ... ORDER BY ...` rows but keeps the same row→envelope mapping shape.

**Fabric boot + ingest** (00-quickstart lines 192-221):
```python
with tempfile.TemporaryDirectory(prefix="ccf-quickstart-") as scratch:
    root = Path(scratch)
    registry = ControlPlaneRegistry()
    spec_version = registry.register(keys["resolution_spec"], _resolution_spec(ontology))
    policy_version = registry.register(keys["policy_bundle"], control["policy_bundle"])
    ...
    handle = boot(
        database_path=root / "quickstart.sqlite3",
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        ...
    finally:
        handle.close()
```
Single-writer: ingestion only via `handle.worker.ingest` (§10). Generator writes SQLite files into `root`, never the graph.

**Operator chain from artifacts** (00-quickstart lines 223-288): register `PolicyFilter`, `SimilaritySelect` (with `TokenOverlapIndex` corpus built from `handle.reader.as_of(...)`), `TemporalAsOf`, `TraversalNeighborhood` — every parameter from `control["operator_parameters"]`.

**Projection class pattern** (00-quickstart lines 134-178): a plan class with `plan_id` property, `required_operators()`, and `invoke(*, view, operator_outputs, perspective, temporal_boundary) -> ProjectionOutput`. The demo's Π should project the resolved-entity payment graph payload (entities + payment edges) for the cycle-detection skill to consume.

**Gates, expected-values assertions, replay serve** (00-quickstart lines 306-404): `register_product_class(...)` → `ContextProductContract(... lineage=ProductLineage(operators_invoked=execution.operators_invoked, ...))` → `run_gates(...)`; then the expected-block assertion pattern (lines 352-360):
```python
expected = control["expected"]
payload = gated.product.payload
assert payload["entity_count"] == expected["entity_count"], payload
```
Then `build_replay_record(...)` + `FileArtifactStore` + `serve(...)` + store round-trip asserts (lines 362-404). The demo pins ring detection (and the zero-cycle baseline) via `expected` blocks in artifacts exactly this way — never as code constants.

**Agent factory layer** (01-agent-basics lines 233-260, 402-416): register the prompt artifact typed, register every `agent_doc["referenced_artifacts"]` via `declared_artifact_class`/`parse_artifact`/`register_typed`, register the definition with `register_versioned(definition_key, definition, AGENT_DEFINITION)`, then:
```python
agent = AgentFactory(control_plane=registry).construct(
    definition_key=definition_key,
    definition_version=definition_version,
)
assert agent.identity.definition_hash == content_hash(definition)
```
Agent archetype list in `agent.yaml` is `["analytics_insights"]` (D-09), mirroring example 01's declaration.

**Final print block** (00-quickstart lines 419-429 / 01 lines 515-525): `print("examples/NN-name: OK")` followed by aligned key-fact lines, then `return 0`; `if __name__ == "__main__": sys.exit(main())`. For D-16 staged narration, extend this into per-stage banners — build the full narration string deterministically, print it, and byte-compare it against a committed expected-output artifact (research Pattern 4 recommendation).

---

### `examples/08-e2e-demo/generator.py` (utility, batch → SQLite files)

**Analog:** `perf/synth/generator.py` — mirror the discipline, do not import (D-05).

**Seed + epoch constants pattern** (perf/synth/generator.py lines 40-57):
```python
#: The documented fixed seed (D-08). Changing it invalidates every pinned
#: shape/checksum ... update those pins in the same commit or the drift
#: alarm fires, as designed.
PERF_SEED = 20260801
...
#: Fixed epoch all observation timestamps derive from (never a clock read).
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
```
Demo difference per CONTEXT D-07/D-08: the seed itself lives in `scenario.yaml` (`rng = random.Random(scenario["seed"])`), and expected checksums/row counts live in the scenario (or sibling expected-values) artifact, asserted by run.py — not module constants.

**Artifact interpretation pattern** (lines 63-71): `yaml.safe_load((_ARTIFACTS / "ontology.yaml").read_text(encoding="utf-8"))` cached once; every vocabulary value (source-system names, ring member aliases, amounts, noise params) comes from the artifact; the module holds none of it. Module docstring cites the D-numbers and CLAUDE.md §6.4/§10, including the single-writer note (lines 22-25): "this module ... emits [rows]; ingestion happens exclusively through `handle.worker.ingest`."

**Deterministic RNG threading** (lines 130-193): one `random.Random(seed + offset)` per generation stream, distinct offsets per stream (`PERF_SEED + rung`, `+1`, `+2`) so streams stay independent but reproducible. Fail loudly on infeasible configurations (`raise ValueError(...)`, lines 169-173) rather than looping.

**Checksum pattern** (lines 206-220) — checksum logical content, sorted, never file bytes (research Pitfall 2):
```python
def rung_checksum(rung: int) -> str:
    """sha256 over the SORTED entity URIs and edge triples (D-08)."""
    digest = hashlib.sha256()
    for uri in sorted(...):
        digest.update(uri.encode("utf-8")); digest.update(b"\n")
    ...
    return digest.hexdigest()
```
Demo equivalent: sha256 over sorted row tuples per SQLite source + ring-signature hash, compared to `scenario.yaml` expected values.

**Deterministic timestamps** (lines 255-270): `observed = EPOCH + timedelta(minutes=sequence, seconds=rng.randrange(60))` — never a clock read. Store as ISO-8601 with explicit offset in SQLite; parse back with `_instant`.

---

### Cycle-detection skill (catalog + grant + dispatch, inside run.py)

**Analog:** `examples/06-decision-replay/run.py` lines 693-735; registry mechanism in `src/ccf/skills/callables.py`.

**Full skilled-agent block to copy** (06 run.py lines 694-735):
```python
catalog = SkillCatalog(registry)
entry = parse_artifact(skills_doc["skills"]["feeder_load_metrics"], SKILL_CATALOG_ENTRY)
assert isinstance(catalog.register(entry), str)
ledger = GrantLedger(control_plane=registry, catalog=catalog, sink=UnconsultedSink(), clock=clock)
callables = CallableRegistry()
callables.register(skills_doc["callable"]["registered_key"], <SkillCallable>)
agent = AgentFactory(control_plane=registry, callable_registry=callables).construct(
    definition_key=definition_key,
    definition_version=definition_version,
    bound_skills=ledger.bound_view(definition_hash),
)
grant = SkillGrant(agent_definition_hash=definition_hash, **skills_doc["grant"])
granted = ledger.request(grant, definition=definition, actor=skills_doc["actors"]["requesting_actor"])
invocation = agent.invoke_skill(
    skills_doc["grant"]["skill_name"],
    arguments=skills_doc["dispatch"]["arguments"],
)
assert isinstance(invocation, SkillInvocation)
assert dict(invocation.output) == skills_doc["dispatch"]["expected_output"]
```
The demo's callable is the cycle-detection function (example-local, registered at the composition root — Open Question 1's recommended resolution). Contract from `src/ccf/skills/callables.py` line 53:
```python
SkillCallable = Callable[[Mapping[str, str]], Mapping[str, str]]
```
Registration is explicit at the composition root, append-only, duplicate keys fatal (`CallableRegistry.register`, lines 84-92); `callable_ref` is a key, never a module path. Parameters (relationship type to walk, thresholds) come from `skills.yaml` arguments; the expected ring output pins in `skills.yaml`'s `dispatch.expected_output`. The baseline contrast (D-11) reuses the same detection function directly over raw SQLite rows in a "Stage 0" pass and asserts zero cycles.

Also copy example 02's callable-factory shape (`examples/02-skilling/run.py` lines 197-199, `_bind_callable`) if the callable needs artifact-supplied output vocabulary.

---

### `--live` narration branch (inside run.py)

**Analog:** `examples/03-harness-portability/run.py`.

**Argparse gating** (03 run.py lines 692-708):
```python
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("deterministic", "live"), required=True)
    parser.add_argument("--provider", choices=("ollama", "anthropic"))
    arguments = parser.parse_args()
    if arguments.mode == "live":
        if arguments.provider is None:
            print("... --mode live requires --provider ...", file=sys.stderr)
            return 2
        return _live(arguments.provider)
    return _deterministic()
```
For the demo a simpler `--live` boolean flag is fine (CONTEXT D-10), but keep: deferred live-only imports inside the live branch (03 line 581: `from legs.live import ...` — "imported here so `--mode live` never requires the deterministic [deps]" and vice versa, line 473), live config in an artifact (`live.yaml`, line 590), and assertions never on model text — only on what CCF governs (03 lines 16-24, 640-667). Detection runs identically in both modes (D-12); `--live` gets no Makefile/CI wiring.

**Deterministic-mode LLM seam** (01-agent-basics lines 187-205, `ScriptedAnalyst`): a scripted `LLMClientProtocol` stub whose model id and outputs are artifact data — reuse if the deterministic path needs any LLM-shaped step.

---

### `Makefile` (example-08 target)

**Analog:** Makefile lines 50-74. Copy exactly:
```make
example-08: ## Run examples/08-e2e-demo (deterministic, D-08/D-16)
	$(ENV) $(PYTHON) examples/08-e2e-demo/run.py

examples: example-00 ... example-07 example-08 ## Run all nine examples ...
```
Also append `example-08` to the `.PHONY` list (lines 22-23). Note example-03's pattern: the CI target passes only the deterministic flag; live variants (`example-03-live-*`, lines 108-111) are separate targets excluded from `examples`. If the demo defaults to deterministic with `--live` opt-in, no flag is needed in the CI target. `.github/workflows/ci.yml` runs `make examples` — no CI file change needed.

---

### `examples/08-e2e-demo/artifacts/*.yaml`

**Analogs:** `examples/00-quickstart/artifacts/` (ontology.yaml, events.yaml, controlplane.yaml, halflife.yaml — banking vocabulary to extend per D-01), `examples/01-agent-basics/artifacts/` (agent.yaml with `agent_definition`, `referenced_artifacts`, `keys` blocks; prompt.yaml with `prompt_artifact` + `keys`), example 06's `skills.yaml` (blocks: `skills.<name>` catalog entry, `callable.registered_key`, `grant`, `actors.requesting_actor`, `dispatch.arguments`, `dispatch.expected_output`). `scenario.yaml` is new but follows perf/synth's `artifacts/ontology.yaml` role: all vocabulary + seed + expected checksums/row counts + ring definition (disjoint per-source identifiers — Pitfall 4).

---

### `examples/08-e2e-demo/README.md`

**Analog:** any existing example README (all follow §9: what it demonstrates, whitepaper/CLAUDE.md sections exercised, what to change first). Keep short; link to `docs/demo-walkthrough.md` (D-14).

## Shared Patterns

### No-Hardcoding (§6.4)
**Source:** every analog's docstring + structure. Apply to run.py, generator.py, and the walkthrough. Code is loader/interpreter/assertion logic only; every domain value (ring, aliases, amounts, thresholds, banner fact values, expected outputs) lives in `artifacts/*.yaml`. Expected-values assertion idiom: `expected = control["expected"]; assert payload[...] == expected[...], payload`.

### UTC normalization at every boundary
**Source:** `_instant` (00-quickstart lines 85-95). Apply to YAML loads and SQLite reads alike (D-IMPL-38).

### Deterministic ordering
**Source:** perf/synth (sorted before hashing, seeded offsets, fixed EPOCH). Apply to generation, SQLite reads (`ORDER BY`), narration string construction, and any set iteration.

### Byte-compare discipline
**Source:** `ccf.contracts.canonical.canonical_bytes` / `content_hash` as used in 00 (line 390) and 06 (line 977: `assert canonical_bytes(outcome.product) == canonical_bytes(...)`). Apply to the reproduced product and to the D-16 narration (recommend committed expected-output file compared in-run — zero CI changes).

### Live-never-in-CI
**Source:** Makefile lines 45-48 + 108-111; 03 run.py structure. `--live` gets no `examples`/`ci` wiring.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/demo-walkthrough.md` | docs (mkdocs + pymdownx.snippets literal includes) | — | No mkdocs docs exist yet (Phase 14 owns the site). Use `--8<-- "examples/08-e2e-demo/..."` repo-root-relative include paths and note the base_path assumption in a header comment for Phase 14 (RESEARCH Pitfall 5 / A2). |

## Metadata

**Analog search scope:** `examples/00,01,02,03,06`, `perf/synth/`, `src/ccf/skills/`, `Makefile`, `docs/`
**Files scanned:** 9 read in detail (5 full, 4 targeted ranges/greps)
**Pattern extraction date:** 2026-08-01
