# Phase 11: Performance Battery - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 14 new/modified files
**Analogs found:** 12 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `perf/conftest.py` | test fixture module | request-response (fixture factory) | `tests/conftest.py` | exact |
| `perf/suites/micro/*.py` | test (benchmark) | request-response | `tests/conftest.py` fixture usage + Pattern 1 in RESEARCH | role-match |
| `perf/suites/scale/*.py` | test (benchmark, pedantic) | batch | `examples/04-cross-process/producer_child.py` (L1→L6 pipeline shape) | role-match |
| `perf/suites/crossproc/*.py` | test (benchmark, subprocess) | request-response over wire | `tests/crossproc/conftest.py` + `examples/04-cross-process/run.py` | exact |
| `perf/suites/replay/*.py` | test (benchmark) | batch/transform | `examples/06-decision-replay/run.py` + `tests/replay/` | role-match |
| `perf/synth/generator.py` | utility (fixture generator) | event-driven emission (L1 envelopes) | `examples/04-cross-process/producer_child.py` (`_envelopes`, `_resolution_spec`, artifact loading) | exact |
| `perf/synth/artifacts/*.yaml` | config (definition artifacts) | — | `examples/04-cross-process/artifacts/ontology.yaml` | exact |
| `perf/gate.py` | utility/CLI script (report + gate) | file-I/O + transform | `tools/lints/__main__.py` | role-match |
| `perf/thresholds.toml` | config | — | `pyproject.toml` TOML conventions | role-match |
| `perf/baselines/<runner>.json` | config (committed data) | — | no analog (new artifact class) | none |
| `perf/README.md` | docs | — | `examples/04-cross-process/README.md` | role-match |
| `.github/workflows/perf.yml` | config (CI workflow) | event-driven (workflow_dispatch) | `.github/workflows/live-legs.yml` | exact |
| `Makefile` (perf targets) | config | — | `Makefile` existing target style | exact |
| `tests/perf_smoke/`, `tests/perf_gate/`, `tests/perf_synth/` | test (deterministic) | request-response | `tools/lints/tests/` + `tests/lints/` | exact |
| `pyproject.toml` (perf extra) | config | — | existing optional-dependencies block | exact |

## Pattern Assignments

### `perf/conftest.py` (fixture module)

**Analog:** `tests/conftest.py`

**Fixture-factory + composition-root-only boot pattern** (lines 197–259). Perf fixtures must boot the same way — no test-only writers:

```python
@pytest.fixture
def fabric_boot(tmp_path, request) -> Iterator[Callable[..., "FabricHandle"]]:
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry
    handles: list[FabricHandle] = []
    def factory(*, database_path=None, backend="sqlite") -> "FabricHandle":
        registry = ControlPlaneRegistry()
        spec_version = registry.register(RESOLUTION_SPEC_KEY, _resolution_spec())
        policy_version = registry.register(POLICY_BUNDLE_KEY, _policy_bundle())
        ...
        handle = boot(registry=registry, resolution_spec_key=..., ...)
        handles.append(handle)
        return handle
    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()
```

Perf variant: **session-scoped** per-rung fabric fixtures (rung build cost amortized), Control Plane keys as module constants in perf code (tests/conftest.py lines 38–40 shows keys living in test code, never `/src`).

**Values-from-artifact loading** (tests/conftest.py lines 285–299) — read YAML fixture values by path, `yaml.safe_load((Path(__file__).parent / ... ).read_text())`; the synth ontology follows the same discipline.

**Env-var required/skip idiom** (lines 101–157): `CCF_PERF_RUNNER_CLASS` handling should mirror `POSTGRES_DSN_ENV` / `CCF_REQUIRE_*` shape — env var constants with `#:` doc comments, explicit names, no fingerprinting.

---

### `perf/suites/crossproc/*.py` + subprocess fixture

**Analog:** `tests/crossproc/conftest.py` (whole file, 119 lines) — this is THE shared cross-process fixture; reuse or copy its shape exactly.

**READY-handshake spawn, never sleep** (lines 64–89):

```python
proc = subprocess.Popen([sys.executable, str(child_module_path)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    announcement = proc.stdout.readline().strip()
    if not announcement.startswith(f"{READY_TOKEN} "):
        _, stderr = proc.communicate(timeout=TERMINATE_TIMEOUT_SECONDS)
        raise AssertionError(f"... did not announce readiness ...; stderr:\n{stderr}")
    yield int(announcement.split()[1])
finally:
    proc.terminate()
    try:
        proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait()
```

Perf differences: make the fixture **session-scoped** and add explicit warm-up round-trips before yielding the client (Pitfall 5). Multi-port announce shape is in `examples/04-cross-process/producer_child.py` lines 605–626 (`print(f"READY {mcp_port} {a2a_port}")` only after `server.started` flags flip) and the parent parse at `run.py` lines 332–338. Process-group teardown for a child that owns servers: `run.py` lines 496–513 (`os.killpg(os.getpgid(proc.pid), SIGTERM)` → wait → SIGKILL fallback).

**MCP client round-trip to benchmark** (`run.py` lines 359–366):

```python
with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
    mcp_client = McpResourceClient(url=f"http://127.0.0.1:{mcp_port}/mcp", bridge=bridge)
    over_mcp = mcp_client.read_text(address.uri)
```

Peering/A2A round-trip: `TypedHttpWire` construction (`run.py` lines 292–307; import `from ccf_runtime.peering.typed_http import TypedHttpWire`).

---

### `perf/synth/generator.py` (deterministic generator, L2-only)

**Analog:** `examples/04-cross-process/producer_child.py`

**Artifact loading + resolution-spec construction** (lines 131–163):

```python
def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))

def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    return EntityResolutionSpec(
        entity_rules=tuple(EntityResolutionRule(
            match_key=rule["match_key"], entity_class=rule["entity_class"],
            identity_keys=tuple(rule["identity_keys"]),
            attribute_keys=tuple(rule.get("attribute_keys", ()))) for rule in ontology["entity_rules"]),
        relationship_rules=tuple(...),
    )
```

**Envelope emission through L1 — the only write path** (lines 166–178 + ingest at line 318–319):

```python
SignalEnvelope(tenant_id=..., envelope_id=..., source=SourceIdentity(system_id=...),
               ingestion_timestamp=_instant(...), observed_time=_instant(...),
               raw_payload=dict(item["payload"]))
...
for envelope in _envelopes(ontology, events):
    handle.worker.ingest(envelope)
```

The generator produces `SignalEnvelope` streams from `random.Random(seed)`; it must never import `ccf.graph` internals. Timestamps derive from seed + fixed epoch via `_instant`-style UTC discipline (lines 135–141 — naive datetimes are refused by the canonical serializer).

**Operator/projection/product construction for scale + micro suites** (lines 320–436): full four-category `OperatorRegistry` registration (PolicyFilter/SimilaritySelect/TemporalAsOf/TraversalNeighborhood with `*Parameters`), `ProjectionEngine(reader=handle.reader, registry=operators).execute(...)`, `register_product_class(...)`, `ContextProductContract(...)`, `run_gates(candidate, engine_resolved=..., now=..., registry=..., product_class=...)`. The micro suite benchmarks these exact call shapes; the scale suite times `handle.worker.ingest` loops (assembly) and `engine.execute` (projection) separately.

**Factory construction for micro-suite factory benchmark** (lines 286–306, 452–458): `parse_artifact(...)` + `registry.register_versioned(key, definition, AGENT_DEFINITION)` + `AgentFactory(control_plane=registry).construct(definition_key=..., definition_version=...)`.

---

### `perf/synth/artifacts/*.yaml` (neutral ontology)

**Analog:** `examples/04-cross-process/artifacts/ontology.yaml`

Header + shape to copy (lines 1–30): explanatory comment block citing D-decisions and §6.4, then:

```yaml
schema_version: "1.0.0"
artifact_version: "1.0.0"
tenant_id: <neutral-tenant>
entity_rules:
  - match_key: <key>
    entity_class: <class>
    identity_keys: [<key>]
    attribute_keys: [...]
relationship_rules: ...
```

Use deliberately meaningless names (`node_alpha`, `rel_link` style) per D-09. Same file also carries operator parameters / product-class blocks — see example 04's `controlplane.yaml` for the keys/product_class/max_ttl layout.

---

### `perf/gate.py` (report + gate script)

**Analog:** `tools/lints/__main__.py`

**Script anatomy** (lines 1–66): module docstring stating exit-code semantics, `argparse`, config-as-module-constants with `#:` doc comments, dict-of-checkers dispatch, exit nonzero only on gated findings. Key contrast the docstring must invert: lints deliberately have *no* report-only mode; gate.py **must** have one (D-13 missing-baseline → loud notice + exit 0). State that difference explicitly in the docstring, citing D-13/D-IMPL-70.

```python
"""`python perf/gate.py <raw.json> --suite <name>` — report + gate, one pipeline.
Exit nonzero only on a gated regression; missing baseline → loud
"NO BASELINE — NOT GATED" per entry and exit 0 (D-13)."""
```

Read thresholds with stdlib `tomllib`; validate loosen-only overrides at load; runner class from `CCF_PERF_RUNNER_CLASS`. Percentiles from sorted `b["stats"]["data"]` (RESEARCH Pattern 6). Report baseline entries with no matching benchmark and vice versa (Pitfall 6).

---

### `tests/perf_gate/`, `tests/perf_synth/`, smoke test (deterministic, always-on)

**Analog:** `tools/lints/tests/` (unit tests of a repo-owned checker on fixture inputs) and `tests/lints/` (tests asserting scope/isolation).

Gate tests: pure-function tests over synthetic JSON/TOML fixtures written to `tmp_path` — same style as `tools/lints/tests/test_runner.py`. Synth tests: assert pinned `(entity_count, edge_count, observation_count)` + sha256 checksum per rung. Smoke test: invoke pytest on `perf/suites` with `--benchmark-disable` (one iteration each); keep `perf/` out of collection — `pyproject.toml` `[tool.pytest.ini_options] testpaths = ["tests"]` (line 90–91) already excludes it; perf tree gets its own rootdir config.

---

### `.github/workflows/perf.yml`

**Analog:** `.github/workflows/live-legs.yml`

**Opt-in dispatch skeleton** (lines 10–49):

```yaml
name: perf
on:
  workflow_dispatch:
    inputs:
      suite:
        description: "Suite to run (all|micro|scale|crossproc|replay)"
        required: false
        default: "all"
        type: string
jobs:
  perf:
    runs-on: ubuntu-24.04        # pin the image — the runner class key names it
    timeout-minutes: 30
    env:
      CCF_PERF_RUNNER_CLASS: gh-ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - name: Provision .venv for the Makefile command surface
        run: |
          python -m venv .venv
          .venv/bin/pip install -e ".[dev]"
      - run: make perf ...
```

live-legs.yml provisions `.venv` explicitly (lines 46–49) because the Makefile hardcodes `.venv/bin/python` — copy that step verbatim. Copy the top-of-file comment style explaining the opt-in posture (lines 1–9). Upload `perf/results/` via `actions/upload-artifact@v4` with `if: always()`.

**Deviation from analog:** live-legs pins `ubuntu-latest`; perf.yml must pin `ubuntu-24.04` (runner-class key stability, RESEARCH note).

---

### `Makefile` perf targets

**Analog:** `Makefile` (lines 10–41)

```make
PYTHON := .venv/bin/python
ENV := PYTHONPATH=src:runtime

target: ## One-line description with decision citation (D-NN)
	$(ENV) $(PYTHON) -m pytest -q
```

Copy: `$(ENV) $(PYTHON)` invocation form (extend `PYTHONPATH` to `src:runtime:perf` in perf targets only), `## help` comments (auto-help at lines 19–21 requires them), `.PHONY` registration (line 15), composite-target style `ci: ci-core examples` (line 41) → `perf: perf-micro perf-scale perf-xproc perf-replay`. Comment block above `ci` (lines 37–40) is the model for documenting that perf never joins `ci`.

---

### `pyproject.toml` perf extra

**Analog:** `pyproject.toml` `[project.optional-dependencies]` (lines 61–84)

Pattern: pinned versions with a rationale comment; extras composed into `dev` via self-referential `ccf[...]`:

```toml
perf = ["pytest-benchmark==5.2.3"]
dev = [ ..., "ccf[harnesses]", "ccf[perf]" ]
```

Also add `perf/results/` to `.gitignore`.

---

### `perf/suites/replay/*.py`

**Analog:** `examples/06-decision-replay/run.py` (byte-exact replay resolution flow) and `tests/replay/test_engine_rehydration.py` (replay-engine test call shapes). Per rung: assert byte-exact reproduction of a sampled decision using the example-06 resolution path, then `benchmark.pedantic(replay_fn, rounds=3, iterations=1, warmup_rounds=1)`; log-log curve fit is new code in the suite (stdlib `math`, RESEARCH Pattern 5).

### `perf/suites/micro/` — `run_coroutine_sync` benchmark

**Analog:** `runtime/ccf_runtime/orchestration/common.py` lines 77–89:

```python
def run_coroutine_sync(
    coro: Coroutine[object, object, _T], *, timeout: float | None = None
) -> _T:
```

Benchmark from a plain sync test (no asyncio plugin) with a trivial coroutine, matching the production call shape (Pitfall 7).

## Shared Patterns

### Module docstrings citing decisions and CLAUDE.md sections
**Source:** every analog (e.g. `tests/crossproc/conftest.py` lines 1–26, `tools/lints/__main__.py` lines 1–17)
**Apply to:** all new perf modules. First line names what the module is; body names the D-NN decisions and invariants it serves; `#:` doc comments on module constants.

### Values-in-artifacts, mechanism-in-code (No-Hardcoding)
**Source:** `examples/04-cross-process/producer_child.py` lines 121–132 + `artifacts/ontology.yaml` header
**Apply to:** generator, suites, gate. All ontology values, and any perf-suite domain vocabulary, in YAML under `perf/synth/artifacts/`; code is `_load()` + typed construction. Thresholds/baselines are TOML/JSON artifacts, never code constants. Note: `tools/lints/__main__.py` `LINTED_TREES = ("src", "runtime", "examples")` (line 36) does **not** include `perf/` — plans should decide (and document) whether CINV lints extend to `perf/`; check `RULE_TREE_SCOPE` lines 47–52.

### Env-var-driven behavior with explicit constants
**Source:** `tests/conftest.py` lines 99–131; `examples/04-cross-process/producer_child.py` lines 125–128
**Apply to:** `CCF_PERF_RUNNER_CLASS` (gate.py, Makefile default `local`, perf.yml sets `gh-ubuntu-24.04`); shared-vocabulary constants so producer/consumer of the env var cannot disagree on a name.

### Subprocess lifecycle: handshake + guaranteed teardown
**Source:** `tests/crossproc/conftest.py` lines 46–89 (canonical); `examples/04-cross-process/run.py` lines 314–344, 496–513 (multi-port + process-group variant)
**Apply to:** crossproc suite fixture. Never sleep-gate; always terminate→wait→kill in `finally`; capture child stderr for diagnosis.

### Timing judgments only in gate.py
**Source:** RESEARCH anti-patterns + D-IMPL-70
**Apply to:** every benchmark test. Correctness asserts only (`assert result is not None`, byte-exact replay, checksum shape); never `assert elapsed < X` in any suite.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `perf/baselines/<runner-class>.json` | committed data artifact | — | First committed-baseline artifact class in the repo; shape fully specified by D-12 + RESEARCH Pattern 6 (`{"metadata": {date, commit, approved}, "benchmarks": {id: median_seconds}}`) |
| `perf/thresholds.toml` (schema) | config | — | No prior TOML config artifact beyond pyproject; schema specified by D-11/D-19..D-22 (`[suite.<name>] default` + `[override."<id>"] threshold`, loosen-only) |

## Metadata

**Analog search scope:** `tests/` (conftest, crossproc, replay, lints), `examples/04-cross-process/`, `examples/06-decision-replay/`, `tools/lints/`, `Makefile`, `.github/workflows/`, `pyproject.toml`, `runtime/ccf_runtime/orchestration/`
**Files scanned:** ~10 read in depth, ~30 listed
**Pattern extraction date:** 2026-08-01
