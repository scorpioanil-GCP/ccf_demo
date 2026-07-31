# Phase 8: Phase I.5 — Examples Suite & Full CI Verification - Pattern Map

**Mapped:** 2026-07-30
**Files analyzed:** ~30 (8 example dirs + CI/Make + hardening surfaces + packaging)
**Analogs found:** 12 / 14 file groups (Makefile and top-level README have no in-repo analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `examples/00-quickstart/run.py` + artifacts | example driver | batch (L1→L6 pipeline) | `tests/integration/test_proto_quickstart.py` + `tests/fixtures/banking/*.yaml` | exact (named as "the private precursor of examples/00-quickstart, which Phase 8 formalizes") |
| `examples/01-agent-basics/` | example driver + definition artifacts | request-response (factory + agent run) | `tests/fixtures/banking/agents/covenant_analytics.yaml` (+ `tests/agents/` factory tests) | exact schema match |
| `examples/02-skilling/` | example driver + grant artifacts | CRUD (grant/revoke via Control Plane) | `tests/fixtures/banking/skills/`, `tests/skills/` grant-ledger tests | role-match |
| `examples/03-harness-portability/` (incl. `legs/`) | example driver, multi-harness | request-response, deterministic + live | `tests/conformance/test_harness_portability.py` (940 ln) + `tests/conformance/test_orchestration.py` | exact |
| `examples/03-.../legs/ollama_client.py` | LLM transport | request-response (httpx→Ollama) | `src/ccf/llm/__init__.py` (`LLMClientProtocol`, bare Protocol, 34 ln) | protocol-only (no shipped impl — new code) |
| `examples/04-cross-process/` | example, 2-process | event-driven / pub-sub over MCP+A2A | `tests/crossproc/conftest.py` + `tests/crossproc/servers/*_child.py` | exact |
| `examples/05-workflow-hitl/`, `examples/06-decision-replay/` | example drivers, auth-bound | request-response + suspend/resume | `runtime/ccf_runtime/http_api/auth.py`, `tests/hitl/`, `tests/workflow/`, banking `workflows/`+`hitl.yaml` fixtures | role-match |
| `examples/07-artifact-store-mcp/` | example driver, store swap | file I/O ↔ MCP | `tests/conformance/test_artifactstore.py` (file-vs-MCP parametrization) + `tests/crossproc/servers/mcp_artifact_child.py` | exact |
| `examples/NN/README.md` ×8 | docs | — | `tests/integration/test_proto_quickstart.py` docstring (invariant table style); §9 charter | partial |
| `.github/workflows/ci.yml` (examples job) + `live-legs.yml` | config (CI) | batch | existing `.github/workflows/ci.yml` | exact |
| `Makefile` | config | batch | none — commands come from ci.yml steps and RESEARCH "full suite command" | no analog |
| Hardening: `src/ccf/hitl/identity_binding.py`, `src/ccf/hitl/transport.py`, `runtime/ccf_runtime/http_api/*` (D-14/D-16) | service/middleware | request-response | the same files (modification, not creation) | exact |
| `runtime/ccf_runtime/cli/commands/hitl.py` (D-15 removal), `tests/cli/test_cli.py` | CLI | request-response | same file, lines 44–80 | exact |
| `runtime/ccf_runtime/orchestration/adk/driver.py` (SequentialAgent migration) | orchestration driver | state-machine | same file, lines 45, 158, 193–236 | exact |
| `pyproject.toml` bump, top-level `README.md`, tag | packaging | — | pyproject (currently `0.1.0.dev0`) | partial |

## Pattern Assignments

### `examples/00-quickstart` (example driver, batch pipeline)

**Analog:** `tests/integration/test_proto_quickstart.py` — its module docstring explicitly names itself the precursor of example 00.

**Imports pattern** (lines 42–80) — the full public surface an example needs:
```python
from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (EntityResolutionRule, EntityResolutionSpec, RelationshipResolutionRule)
from ccf.boot import FabricHandle, boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.operators.categories import (PolicyFilter, ..., TraversalNeighborhood, TraversalNeighborhoodParameters)
from ccf.products.contract import (ContextProductContract, MaxTTL, ProductLineage, RegisteredProductClass, register_product_class)
```

**Core pattern:** every domain value loaded from YAML fixtures; "the code below is thin loading and asserting logic; deleting the fixtures would leave it with nothing to run (CLAUDE.md §6.4)". Copy this discipline verbatim — but author fresh artifacts under `examples/00-quickstart/artifacts/`, never copy `tests/fixtures/banking/` (CONTEXT.md Pattern 2: mirror shapes, not files).

**README pattern:** the docstring's `Invariant | What would fail here` table (lines 9–34) is the model for README "what this demonstrates" sections.

**Assertion pattern (all 8 examples):** examples are asserted programs — end `run.py` with explicit assertions and nonzero exit on failure (RESEARCH Pattern 1); no per-example pytest wrapper.

### `examples/01-agent-basics` / `02-skilling` artifact authoring

**Analog:** `tests/fixtures/banking/agents/covenant_analytics.yaml` — the complete six-axis agent-definition schema with:
- Two-field versioning: `schema_version` + `artifact_version` (D-IMPL-28)
- `referenced_artifacts:` block registering policy-bundle and debt-profile so factory ref resolution works (keys `{tenant}/{artifact_class}/{name}`; decimals quoted as strings per D-IMPL-26)
- Axis refs as versioned URIs, e.g. `ref: "ccf-artifact://acme-bank/policy-bundle/wholesale-credit@1.1.0"` — never `@latest`
- `skill_governance: {permitted_scopes: [...], grant_requires_approval: false}` envelope (example 02 exercises the tier-1/tier-2 governance check)
- `instruction_bindings: [- prompt: "ccf-artifact://.../prompt/...@1.0.0", parameters: [...]]` — refs only, no inline prompts

Example 01's fresh-domain artifacts follow this exact YAML shape; sibling dirs `tests/fixtures/banking/{prompts,skills,tasks,workflows}/` show the remaining artifact-class schemas.

### `examples/03-harness-portability` (deterministic leg)

**Analog:** `tests/conformance/test_harness_portability.py`

Key extractable machinery:
- `legs()` fixture (line 207) — the three-harness parametrization; `CCF_REQUIRE_HARNESSES=1` makes a skipped leg a failure.
- `no_model_reachable` guard (lines 182–200) — proves the deterministic leg makes no model call; reuse the guard idea in the example's deterministic mode.
- `_drive` / `_drive_all` (lines 429, 519) — one agent definition driven through all adapters; `_governed_fields(record)` (line 493) extracts the byte-comparable replay fields.
- Byte-equality assertions: `test_the_consumed_product_is_byte_identical_across_the_three_harnesses` (line 601), `test_the_governed_replay_fields_are_exactly_equal_across_harnesses` (line 693). These are the D-02 deterministic-leg assertions; live legs use structural checks only (D-04) — model the structural check on `test_a_live_record_still_carries_exactly_five_dimensions` (line 883).
- Real-loop transports: `tests/conformance/test_orchestration.py` (real `ClaudeSDKClient` over custom Transport, real ADK `Runner`, LangGraph injected callables — the 07-13 pattern D-02 mandates).

**A3 discharge target:** `runtime/ccf_runtime/adapters/claude_agent/adapter.py:385`:
```python
if not isinstance(execution, ResultMessage):
    raise TypeError(...)
```
Discharge = drive a *real SDK-produced* `ResultMessage` through `replay_trace(execution=...)` (currently fed hand-built ones). The `HarnessTrace` construction (lines 390–399: `model_usage` keys, `session_id`, `NO_HARNESS` sentinels) is the contract the real message must satisfy.

**Ollama client (`legs/ollama_client.py`):** no analog exists — `src/ccf/llm/__init__.py` is a bare `LLMClientProtocol`. Author a thin httpx client (`POST /api/chat`, base URL from env/config, never a constant) in the example dir; promote to `/runtime` only if a second consumer appears (RESEARCH Open Question 2).

### `examples/04-cross-process` (property-intelligence, fresh artifacts)

**Analog:** `tests/crossproc/conftest.py` + `tests/crossproc/servers/*_child.py`

**Spawn pattern** (conftest lines 47–107): child module binds ephemeral port 0, prints `READY {port}` on stdout; parent does `subprocess.Popen([sys.executable, str(child_module_path)], stdout=PIPE, stderr=PIPE)` and blocking-reads the handshake — no fixed ports, no sleep-and-hope. Child templates: `servers/a2a_producer_child.py` (A2A producer), `servers/mcp_egress_child.py` (MCP egress). Admission verification on the consumer side is already driven in `tests/crossproc/test_peering_exchange.py`.

**Domain rule (D-07/D-08):** property-intelligence artifacts authored fresh; zero porting from `/home/parkave/homecams_v2`.

### `examples/05` / `examples/06` — auth binding (D-14 absorption)

**Analog:** `runtime/ccf_runtime/http_api/auth.py` (73 lines, whole file relevant)

```python
class BearerTokenAuth:
    def __init__(self, *, token_source: TokenSourceProtocol) -> None: ...
    def grant_for_request(self, *, authorization_header: str | None) -> TokenGrant | None:
        scheme, _, credential = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            return None
        return self._token_source.grant_for(token=credential.strip())
```
The example must construct `create_app(auth=BearerTokenAuth(token_source=...))` (Pitfall 3), submit with a verified `TokenGrant`, and show the audited principal via `principal_from_token_grant` (`src/ccf/hitl/identity_binding.py:` — see `sign_principal_binding` line 95, `verify_principal_binding` line 123, `SignedPrincipalBinding(CCFContract)` line 73). Workflow/HITL fixture shapes: `tests/fixtures/banking/workflows/` + `hitl.yaml` (payment-release workflow, Phase 7).

### `examples/07-artifact-store-mcp`

**Analog:** `tests/conformance/test_artifactstore.py` (file-vs-MCP parametrization) and `tests/crossproc/servers/mcp_artifact_child.py` (the MCP artifact server child). The example is pure wiring: same code path, swap `FileArtifactStore` for the MCP-backed store; the conftest spawn pattern above hosts the server.

### `.github/workflows/ci.yml` + `live-legs.yml` (config, CI)

**Analog:** existing `ci.yml` (117 lines). Copy:
- Setup block (lines 20–28): checkout@v4, setup-python@v5 `python-version: "3.12", cache: pip`, `pip install -e ".[dev]"`.
- Require-don't-skip pattern (lines 70–84): `CCF_REQUIRE_POSTGRES: "1"` / `CCF_REQUIRE_HARNESSES: "1"` env with explanatory comments — apply the same posture to the examples job.
- Never `continue-on-error` (lines 100–106 comment: "a step made non-blocking to hide a gap is worse than the gap" — D-07 precedent).
- New always-on `examples` job runs `make examples`; opt-in legs in a separate `live-legs.yml` with `workflow_dispatch` + secret gating (RESEARCH alternatives table recommendation).

### `Makefile` (no analog — new)

Targets `examples`, `example-NN`, `ci`, mirroring CI commands exactly (D-10). Canonical command shapes from RESEARCH Validation Architecture:
```
CCF_REQUIRE_HARNESSES=1 PYTHONPATH=src:runtime .venv/bin/python -m pytest -q
.venv/bin/python -m mypy
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all
```
Pitfall 7: Makefile should `pip install -e ".[dev]"` (or invoke `python -m ccf_runtime.cli.main`) to avoid stale-editable `ccf`.

### Hardening wave (modifications, exact anchors)

- **D-15 removal:** `runtime/ccf_runtime/cli/commands/hitl.py` — `_decide` at line 44, deprecation warning line 46, subparser registration lines 75–80. Remove; flip the 07-19 deprecation test in `tests/cli/test_cli.py` to an absence test; grep tree-wide for `decide`; DECISIONS.md entry.
- **ADK migration:** `runtime/ccf_runtime/orchestration/adk/driver.py` — `from google.adk.agents import BaseAgent, SequentialAgent` (line 45); `SequentialAgent(` constructions at lines 206 and 236; signature at line 158. Migrate to ADK 2.5.0 non-deprecated API, or recorded-rationale suppression (Pitfall 5).
- **D-16 seam:** likely `src/ccf/hitl/transport.py` — `HITLTransportProtocol.submit(*, submission: HitlActionSubmission)` (line 200) / `HitlActionSubmission(CCFContract)` (line 119) is the enqueue/resolve authority path; compose optional-but-policy-requirable `SignedPrincipalBinding` (identity_binding.py line 73) with the requiredness a Control Plane value, never a constant. Typed refusal on unsigned submission when required.
- **Fail-closed branch + error-code constants:** `runtime/ccf_runtime/http_api/` (dependencies/routes) — `isinstance(grant, TokenGrant)` fail-closed (403/500, never caller-principal fallback); typed refusal error-code constants replacing string parsing. TDD against existing `tests/http_api`, `tests/hitl`, `tests/cli`.

## Shared Patterns

### Lint coverage over `/examples`
**Source:** `tools/lints/__main__.py:36` — `LINTED_TREES: tuple[str, ...] = ("src", "runtime", "examples")`. **Already includes `examples`** — RESEARCH Pitfall 1's "verify and extend" is largely satisfied for CINV-01; what remains to verify at plan time is per-rule scoping (CINV-02 harness-import lint must not fire on example 03's legitimate harness imports — check `tools/lints/harness_imports.py` path scoping and `allowlist.yaml`) plus adding a lint test asserting the posture.

### No-Hardcoding in example code
**Source:** `tests/integration/test_proto_quickstart.py` docstring + `covenant_analytics.yaml` header comments. Apply to every example: thin generic `run.py`, all domain values in `artifacts/*.yaml` + Jinja2 prompt artifacts, versioned-URI refs only, no `@latest`.

### Deterministic LLM seam
**Source:** injected-LLM patterns behind `LLMClientProtocol` (`src/ccf/llm/__init__.py`) as used across `tests/` semantic-stage tests. Examples 00–02, 04–07 run keyless/model-free via this seam (D-12).

### Exit-code contract
**Source:** CLI 0/1/2 precedent (I.4 gate). Every `run.py` exits 0 only on demonstrated assertions; CI treats nonzero as red.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `Makefile` | config | batch | No Makefile exists; derive targets from ci.yml steps + RESEARCH command table |
| Top-level `README.md` (D-17) | docs | — | None exists; content is install + quickstart pointers into `examples/` |
| Ollama httpx client | LLM transport | request-response | `LLMClientProtocol` is a bare Protocol with zero shipped adapters — genuinely new code, author in example 03's dir |

## Metadata

**Analog search scope:** `tests/{integration,conformance,crossproc,fixtures}`, `tools/lints`, `.github/workflows`, `runtime/ccf_runtime/{http_api,cli,adapters,orchestration}`, `src/ccf/{hitl,llm}`
**Files scanned:** ~40 listed, 8 read in excerpt detail
**Pattern extraction date:** 2026-07-30
