---
phase: 6
slug: phase-i-3-cross-process-harness-adapters
status: signed-off
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-26
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` § Validation Architecture, which carries the
> full requirement→test map and the five-success-criteria coverage rows.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest==9.1.1` + `hypothesis==6.161.5` — already wired |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Async style** | plain `asyncio.run()` inside sync tests — existing repo pattern (`tests/integration/test_cdc_slice.py:182`); no async plugin added |
| **Quick run command** | `python -m pytest tests/<area> -x -q` |
| **Full suite command** | `python -m pytest -q && python -m tools.lints --all && python -m mypy` |
| **Estimated runtime** | ~full suite baseline (627 pass / 2 skip at `D-GATE-I.2`) plus this phase's additions |
| **New markers** | `crossproc` (spawns subprocesses), `harness` (requires a harness extra) — added to `[tool.pytest.ini_options] markers`, matching the existing `postgres` / `chroma` / `conformance` precedent |

---

## Sampling Rate

- **After every task commit:** `python -m pytest tests/<area> -x -q`
- **After every plan wave:** `python -m pytest -q && python -m tools.lints --all && python -m mypy`
- **Before `/gsd:verify-work`:** full suite green, all three lints green, mypy clean
- **Max feedback latency:** target < 60 s for the quick run

**Phase-specific sampling constraint:** cross-process tests (`crossproc`) must
never gate on a sleep (D-16). Any test whose readiness depends on wall-clock
delay is a defect, not a flake.

---

## Per-Task Verification Map

*Populated by the planner before execution — one row per task across all seventeen plans,
ordered by wave. This is the sampling contract, not a retrospective record: 06-16 Task 3
**verifies and signs it off** by running every command below, and does not author it.*

**50 tasks across 17 plans. 48 carry an `<automated>` verify; the 2 that do not are
blocking human checkpoints (06-02-T1 package legitimacy, 06-16-T4 the phase gate), each
immediately followed or preceded by automated evidence — no window of three consecutive
tasks lacks automated verification.**

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 06-01 | 1 | XPRC-03 | T-06-01 | Carve-out is an explicit module allowlist, not a suppression comment | lint | `python -m tools.lints --all && grep -q HARNESS_ADAPTER_MODULES tools/lints/harness_imports.py && ! grep -q 'no legitimate exceptions' tools/lints/harness_imports.py` | `tools/lints/harness_imports.py` | ✅ green |
| 06-01-T2 | 06-01 | 1 | XPRC-03 | T-06-02 | A harness import outside the allowlist still fails the lint | unit (negative) | `python -m pytest tools/lints/tests/test_harness_imports.py -q` | `tools/lints/tests/test_harness_imports.py` | ✅ green |
| 06-01-T3 | 06-01 | 1 | XPRC-03 | T-06-03 | Stale DESIGN.md allocation corrected and the decision logged | doc + lint | `grep -q 'D-IMPL-53' docs/DECISIONS.md && ! grep -q 'Phase I.4 (harness' docs/DESIGN.md && python -m tools.lints --all` | `docs/DECISIONS.md` | ✅ green |
| 06-02-T1 | 06-02 | 1 | XPRC-01 | T-06-04 | Package legitimacy confirmed by a human before install | checkpoint (blocking-human) | — (blocking human checkpoint; verified by the next task's install command) | `pyproject.toml` | ⏸️ blocking human checkpoint — not automatable |
| 06-02-T2 | 06-02 | 1 | XPRC-01 | T-06-05 | Pinned versions installed and importable; no floating ranges | integration | `pip install -e ".[harnesses]" -q && pip check && python -c "import mcp, joserfc, a2a, google.adk, langgraph, claude_agent_sdk, pydantic, yaml; assert pydantic.VERSION=='2.13.4' and yaml.__version__=='6.0.3'"` | `pyproject.toml` | ✅ green |
| 06-02-T3 | 06-02 | 1 | XPRC-03 | T-06-07 | Core install without harness extras still imports /src cleanly | unit (isolation) | `python -m mypy && python -m pytest tests/lints/test_extra_isolation.py -q` | `tests/lints/test_extra_isolation.py` | ✅ green |
| 06-03-T1 | 06-03 | 1 | XPRC-02 | T-06-09 | Callable resolution is a registry lookup, not a dotted path | unit | `python -m mypy && python -m tools.lints --all && python -c "from ccf.skills.callables import CallableRegistry, DuplicateCallableKey, CallableNotRegistered"` | `src/ccf/skills/callables.py` | ✅ green |
| 06-03-T2 | 06-03 | 1 | XPRC-02 | T-06-08 | importlib deleted; a catalog entry naming os.system resolves to nothing | unit (hostile entry) | `! grep -q importlib src/ccf/skills/dispatch.py && grep -q NotYetBound src/ccf/skills/dispatch.py && python -m mypy && python -m tools.lints --all` | `src/ccf/skills/dispatch.py` | ✅ green |
| 06-03-T3 | 06-03 | 1 | XPRC-01 | T-06-10 | Hostile-entry and multi-principal dispatch cases assert refusal | unit + fixture | `python -m pytest tests/skills/ -q && grep -q 'D-IMPL-54' docs/DECISIONS.md && python -m pytest -q` | `tests/skills/test_dispatch.py` | ✅ green |
| 06-04-T1 | 06-04 | 2 | XPRC-01 | T-06-12 | One shared client, non-deadlocking sync facade, typed errors | unit | `python -m mypy && python -m tools.lints --all && python -c "import ccf.mcp.client, ccf.mcp.errors" && ! grep -q start_blocking_portal src/ccf/mcp/client.py` | `src/ccf/mcp/client.py` | ✅ green |
| 06-04-T2 | 06-04 | 2 | XPRC-01 | T-06-13 | Egress serves products only; holds no graph handle | unit (source scan) | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf_runtime.mcp.egress as m; s=inspect.getsource(m); assert 'ccf.graph' not in s and 'ccf-product://' in s"` | `runtime/ccf_runtime/mcp/egress.py` | ✅ green |
| 06-04-T3 | 06-04 | 2 | XPRC-01 | T-06-15 | Real subprocess round trip with readiness handshake, no sleeps | cross-process | `python -m pytest tests/crossproc -q && ! grep -rq 'time.sleep' tests/crossproc/` | `tests/crossproc/test_mcp_egress.py` | ✅ green |
| 06-07-T1 | 06-07 | 2 | XPRC-02 | T-06-30 | Detached-JWS ES256 signing over the canonical product | unit | `python -m mypy && python -m tools.lints --all && python -c "from ccf.a2a.identity import IdentityProvider; import inspect, ccf.a2a.identity as m; assert 'detach_json_content' in inspect.getsource(m)"` | `src/ccf/a2a/identity.py` | ✅ green |
| 06-07-T2 | 06-07 | 2 | XPRC-02 | T-06-32 | Trust policy has no field that could express a verification skip | unit (source scan) | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf.a2a.trust_policy as m; s=inspect.getsource(m); assert 'skip' not in s.lower().replace('skipped','')"` | `src/ccf/a2a/trust_policy.py` | ✅ green |
| 06-07-T3 | 06-07 | 2 | XPRC-02 | T-06-34 | Two peers and two tenants over one policy stay separate (D-23) | unit | `python -m pytest tests/a2a/ -q` | `tests/a2a/test_identity.py` | ✅ green |
| 06-11-T1 | 06-11 | 2 | XPRC-03 | T-06-60 | Protocol exposes no FabricHandle and no GraphWriter | unit (source scan) | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf.harness.protocol as m; s=inspect.getsource(m); assert 'FabricHandle' not in s and 'GraphWriter' not in s"` | `src/ccf/harness/protocol.py` | ✅ green |
| 06-11-T2 | 06-11 | 2 | XPRC-03 | T-06-62 | harness_trace lands in replay dimension 3; record stays five-dimension | unit | `python -m pytest tests/replay -q && python -m pytest tests/conformance/test_harness_portability.py -q -k five_dimensions && grep -q 'D-IMPL-55' docs/DECISIONS.md` **[corrected 06-16 — see note (a)]** | `tests/replay/test_harness_trace.py` | ✅ green |
| 06-11-T3 | 06-11 | 2 | XPRC-03 | T-06-64 | Prompt render is sandboxed with pinned parameters only | unit | `python -m pytest tests/agents tests/harness -q && grep -q SandboxedEnvironment src/ccf/agents/prompts.py` | `src/ccf/agents/prompts.py` | ✅ green |
| 06-05-T1 | 06-05 | 3 | XPRC-01 | T-06-18 | Artifact server authenticates and serves only the artifact scheme | cross-process | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf_runtime.mcp.artifact_server as m; s=inspect.getsource(m); assert 'ccf-artifact-blob://' in s and 'ccf.graph' not in s and 'ccf-product://' not in s"` | `runtime/ccf_runtime/mcp/artifact_server.py` | ✅ green |
| 06-05-T2 | 06-05 | 3 | XPRC-01 | T-06-20 | Sync store over the shared client; no private event loop | unit | `python -m mypy && python -c "import inspect, ccf.artifacts.mcp_store as m; s=inspect.getsource(m); assert 'ccf.graph' not in s and 'new_event_loop' not in s"` | `src/ccf/artifacts/mcp_store.py` | ✅ green |
| 06-05-T3 | 06-05 | 3 | XPRC-01 | T-06-22 | ArtifactStore conformance holds for the MCP backend; roles stay separate | conformance + invariant | `python -m pytest tests/conformance/test_artifactstore.py tests/invariants/test_mcp_role_separation.py -q` | `tests/invariants/test_mcp_role_separation.py` | ✅ green |
| 06-06-T1 | 06-06 | 3 | XPRC-01 | T-06-25 | L1 does not interpret; payload opaque, observed_time None | unit | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf.signal.mcp_source as m; s=inspect.getsource(m); assert 'ccf.graph' not in s"` | `src/ccf/signal/mcp_source.py` | ✅ green |
| 06-06-T2 | 06-06 | 3 | XPRC-01 | T-06-28 | Grant check refuses before any network call | unit (zero-call assertion) | `python -m pytest tests/skills/ -q && python -m mypy && ! grep -q 'new_event_loop' src/ccf/skills/dispatch.py` | `src/ccf/skills/dispatch.py` | ✅ green |
| 06-06-T3 | 06-06 | 3 | XPRC-01 | T-06-26 | Two tenants over one adapter cannot cross (D-23) | cross-process + unit | `python -m pytest tests/signal_layer tests/crossproc tests/skills -q` **[corrected 06-16 — see note (b)]** | `tests/crossproc/test_mcp_ingress.py` | ✅ green |
| 06-08-T1 | 06-08 | 3 | XPRC-02 | T-06-37 | WireProtocol declares nothing transport-shaped | unit | `python -m mypy && python -m tools.lints --all && python -c "from ccf.a2a.wire import WireProtocol" && ! grep -rq 'from a2a\.' src/` | `src/ccf/a2a/wire.py` | ✅ green |
| 06-08-T2 | 06-08 | 3 | XPRC-02 | T-06-39 | Admission verifies signature, policy, contract, lineage before L2 | unit | `python -m mypy && python -m tools.lints --all && python -c "import ast,pathlib;t=ast.parse(pathlib.Path('src/ccf/a2a/admission.py').read_text());assert not [n for n in ast.walk(t) if isinstance(n,ast.Name) and n.id=='ControlPlaneStateStore']" && grep -q 'resolved=False' src/ccf/a2a/admission.py` **[corrected 06-16 — see note (c)]** | `src/ccf/a2a/admission.py` | ✅ green |
| 06-08-T3 | 06-08 | 3 | XPRC-02 | T-06-41 | Lineage set-union property holds under Hypothesis | property | `python -m pytest tests/a2a tests/properties -q` | `tests/properties/test_lineage_union.py` | ✅ green |
| 06-12-T1 | 06-12 | 3 | XPRC-03 | T-06-66 | Claude adapter binds four seams; harness gets no write handle | unit | `python -m mypy && python -m tools.lints --all && python -c "import ccf_runtime.adapters.claude_agent.adapter"` | `runtime/ccf_runtime/adapters/claude_agent/adapter.py` | ✅ green |
| 06-12-T2 | 06-12 | 3 | XPRC-03 | T-06-68 | Four-seam conformance suite is factory-parametrized | conformance | `python -m pytest tests/conformance/test_harness_adapter.py -q` | `tests/conformance/test_harness_adapter.py` | ✅ green |
| 06-12-T3 | 06-12 | 3 | XPRC-03 | T-06-70 | A missing harness extra fails rather than skips under CCF_REQUIRE_HARNESSES | conformance (skip mechanism) | `python -m pytest tests/conformance -q && CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance/test_harness_adapter.py -q` | `tests/conftest.py` | ✅ green |
| 06-17-T1 | 06-17 | 3 | XPRC-01 | T-06-97 | Acquisition seam carries a source key, never an address | unit | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf.mcp.acquisition as m; s=inspect.getsource(m); assert 'ccf.graph' not in s and 'new_event_loop' not in s"` | `src/ccf/projection/acquisition.py` | ✅ green |
| 06-17-T2 | 06-17 | 3 | XPRC-01 | T-06-98 | Served payload carries a value only the child process had; removing the stage fails the test | cross-process | `python -m pytest tests/projection tests/crossproc -q` | `tests/crossproc/test_mcp_acquisition.py` | ✅ green |
| 06-09-T1 | 06-09 | 4 | XPRC-02 | T-06-46 | Transport holds no graph handle and no AssemblyWorker | unit (source scan) | `python -m mypy && python -m tools.lints --all && python -c "import inspect, ccf_runtime.a2a.typed_http as m; s=inspect.getsource(m); assert 'ccf.graph' not in s and 'AssemblyWorker' not in s"` | `runtime/ccf_runtime/a2a/typed_http.py` | ✅ green |
| 06-09-T2 | 06-09 | 4 | XPRC-02 | T-06-48 | Signed two-process exchange admitted only after verification | cross-process | `python -m pytest tests/crossproc -q` | `tests/crossproc/test_a2a_exchange.py` | ✅ green |
| 06-09-T3 | 06-09 | 4 | XPRC-02 | T-06-50 | Admitted products reach L3 only through L2 | invariant | `python -m pytest tests/invariants/ -q && git diff --quiet tests/agents/test_consumption_discipline.py` | `tests/invariants/test_a2a_single_writer.py` | ✅ green |
| 06-13-T1 | 06-13 | 4 | XPRC-03 | T-06-73 | LangGraph adapter owns its topology; core imports nothing | unit | `python -m mypy && python -m tools.lints --all && python -c "import ccf_runtime.adapters.langgraph.adapter"` | `runtime/ccf_runtime/adapters/langgraph/adapter.py` | ✅ green |
| 06-13-T2 | 06-13 | 4 | XPRC-03 | T-06-75 | Protocol hardened against both adapter shapes; Claude re-verified | conformance | `python -m pytest tests/conformance/test_harness_adapter.py tests/harness -q && python -m mypy` | `src/ccf/harness/protocol.py` | ✅ green |
| 06-13-T3 | 06-13 | 4 | XPRC-03 | T-06-77 | LangGraph leg runs with zero LLM calls across two agents | conformance | `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance -q` | `tests/conformance/test_harness_adapter.py` | ✅ green |
| 06-10-T1 | 06-10 | 5 | XPRC-02 | T-06-53 | LF A2A transport behind WireProtocol; no a2a import in /src | unit | `python -m mypy && python -m tools.lints --all && ! grep -rq 'from a2a\.' src/ && python -c "import ccf_runtime.a2a.lf_a2a"` | `runtime/ccf_runtime/a2a/lf_a2a.py` | ✅ green |
| 06-10-T2 | 06-10 | 5 | XPRC-02 | T-06-55 | Same exchange passes over both transports unchanged | cross-process (parametrized) | `python -m pytest tests/crossproc -q` | `tests/crossproc/test_a2a_exchange.py` | ✅ green |
| 06-10-T3 | 06-10 | 5 | XPRC-02 | T-06-57 | a2a skill dispatch governed and audited; NotYetBound tail retained | unit | `python -m pytest tests/skills -q && python -m mypy && ! grep -q 'from a2a' src/ccf/skills/dispatch.py` | `src/ccf/skills/dispatch.py` | ✅ green |
| 06-14-T1 | 06-14 | 5 | XPRC-03 | T-06-79 | ADK adapter imports lazily; google.adk absent from core import graph | unit | `python -m mypy && python -m tools.lints --all && python -c "import ccf_runtime.adapters, sys; assert 'google.adk' not in sys.modules" && python -m pytest tests/lints -q` | `runtime/ccf_runtime/adapters/adk/adapter.py` | ✅ green |
| 06-14-T2 | 06-14 | 5 | XPRC-03 | T-06-81 | effects: unsupported is inert — declared, refused, L3 unchanged (D-10) | conformance | `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance/test_harness_adapter.py -q` | `tests/conformance/test_harness_adapter.py` | ✅ green |
| 06-14-T3 | 06-14 | 5 | XPRC-03 | T-06-83 | No adapter can obtain a write handle; live state compared | invariant | `python -m pytest tests/invariants -q && git diff --quiet tests/agents/test_consumption_discipline.py` | `tests/invariants/test_adapter_single_writer.py` | ✅ green |
| 06-15-T1 | 06-15 | 6 | XPRC-03 | T-06-86 | One harness-free agent definition runs unmodified under three adapters | conformance (portability) | `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance/test_harness_portability.py -q` | `tests/conformance/test_harness_portability.py` | ✅ green |
| 06-15-T2 | 06-15 | 6 | XPRC-03 | T-06-88 | Governed outputs equivalent; harness-attributable variance isolated (D-18) | conformance | `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance -q` | `tests/fixtures/banking/agents/` | ✅ green |
| 06-16-T1 | 06-16 | 7 | XPRC-01 | T-06-93 | CI fails rather than skips when a harness extra is absent | CI + full sweep | `CCF_REQUIRE_HARNESSES=1 python -m pytest -q && python -m tools.lints --all && python -m mypy && ! grep -rq 'from a2a\.' src/ && ! grep -rq 'claude_agent_sdk' src/` | `.github/workflows/` | ✅ green |
| 06-16-T2 | 06-16 | 7 | XPRC-02 | T-06-92 | Every gate row names its test and what would fail under breakage (D-21) | doc verification | `test -f docs/PHASE_I3_GATE.md && ! grep -q 'D-GATE-I.3' docs/DECISIONS.md && python -m pytest -q` | `docs/PHASE_I3_GATE.md` | ✅ green |
| 06-16-T3 | 06-16 | 7 | XPRC-03 | T-06-94 | Validation map verified row by row; D-GATE-I.3 deliberately unwritten | doc verification | `python -m pytest -q && grep -c 'XPRC-03' .planning/REQUIREMENTS.md && ! grep -rq 'D-GATE-I.3' docs/DECISIONS.md` | `.planning/phases/06-phase-i-3-cross-process-harness-adapters/06-VALIDATION.md` | ✅ green |
| 06-16-T4 | 06-16 | 7 | XPRC-01/02/03 | T-06-94 | Phase gate presented to Dave; D-GATE-I.3 unwritten until approval | checkpoint (blocking) | — (blocking human checkpoint; the three preceding tasks carry the automated evidence it reviews) | `docs/PHASE_I3_GATE.md` | ⏸️ blocking human checkpoint — not automatable |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⏸️ blocking human checkpoint.*

**Execution sign-off, 2026-07-27 (06-16 Task 3).** All 48 automated rows were **executed as
written**, in the project `.venv` with `PYTHONPATH=<worktree>/src:<worktree>/runtime` and
`CCF_REQUIRE_HARNESSES=1`, and all 48 exit 0 with their named file present. The 2 remaining
rows are the blocking human checkpoints, which are not automatable by definition and are
marked as such rather than ticked.

**Five rows were defective as planned and are corrected here, marked in place.** Every one
was a *row* defect, not an implementation defect — no test was weakened and no code was
changed to make a row pass:

- **(a) `06-11-T2`** asserted `len(DecisionReplayRecord.model_fields) == 5`. The shipped
  record has **7** fields: the five dimensions plus the `recorded_at` and `tenant_id`
  envelope fields. The criterion would have passed **only on an implementation that had
  dropped the envelope fields** — it required a defect. The real property, *exactly five
  dimensions*, is asserted by
  `tests/conformance/test_harness_portability.py::test_a_live_record_still_carries_exactly_five_dimensions`,
  which the row now runs.
- **(b) `06-06-T3`** named `tests/signal`, which does not exist (the package is
  `tests/signal_layer`). `pytest` exited 4 having **run nothing** — the "passes by
  executing zero tests" failure mode. Corrected to the real path; the selection is
  non-empty.
- **(c) `06-08-T2`** used `! grep -q 'ControlPlaneStateStore' src/ccf/a2a/admission.py`. The
  module contains a docstring paragraph *documenting* that it adds no such consumer (the
  D-20 constraint), so the negative grep fired on the sentence asserting compliance. This is
  the dominant defect class of this phase: **a text match cannot distinguish a violation
  from a mention of one.** Replaced with an AST identifier scan — a docstring is an
  `ast.Constant`, never an identifier, and a genuine use is an identifier and cannot escape.
- **(d) `06-16-T3`'s** File-Exists cell named `06-VALIDATION.md` as a bare filename; the
  file lives in the phase directory. Path corrected.
- **(e) `06-16-T3`'s** command cell was **corrupted at planning time** — roughly thirty lines
  of the plan's own XML `<action>`/`<acceptance_criteria>` prose had been pasted into it,
  which both destroyed the row and swallowed the table rows after it. Reconstructed from the
  plan's `<verify><automated>` block, which is what the row was meant to carry.

That five of fifty rows were unrunnable as written is itself a gate finding, recorded in
`docs/PHASE_I3_GATE.md` §4.10 alongside the thirteen false acceptance criteria the execution
waves found. It is the same defect family and the same lesson: **a verification artifact
authored but never executed is not evidence.**

**Wave map after dependency correction:** wave 1 — 06-01, 06-02, 06-03; wave 2 — 06-04,
06-07, 06-11; wave 3 — 06-05, 06-06, 06-08, 06-12, 06-17; wave 4 — 06-09, 06-13; wave 5 —
06-10, 06-14; wave 6 — 06-15; wave 7 — 06-16. Waves are `max(depends_on) + 1` and no two
plans in one wave share a file. D-02's transport → trust → harness widening still holds as
a *risk* ordering (the three harness SDKs land in waves 3–6, after the fabric-side seams
are proven); it is not a prohibition on parallelism.

**XPRC-01 consumer coverage.** The MCP client leg is bound at each consumer separately —
L1 ingress (06-06), L4/L5 decision-time acquisition (06-17), L6 egress (06-04), and the
ArtifactStore role (06-05). The Experience-layer consumer is Phase 7 scope per
`06-CONTEXT.md`'s deferral of the Experience Layer front doors, and 06-16 records that
deferral as an explicit gate row rather than leaving criterion 1 to read as unmet.

**Requirement coverage source of truth:** `06-RESEARCH.md` § "Phase Requirements
→ Test Map" (XPRC-01, XPRC-02, XPRC-03) and § "Success-criteria coverage",
which gives criterion 4 (single-writer) one concrete observable per boundary —
A2A, adapter, and ArtifactStore — and writes out the D-18 governed vs
harness-attributable split as an assertion.

---

## Wave 0 Requirements

Per `06-RESEARCH.md` § "Wave 0 gaps". The slice (D-01) delivers the shared
cross-process fixture the rest of the phase depends on, so fixture creation is
Wave 0 work in practice:

- [ ] `tests/crossproc/conftest.py` — ephemeral-port (`bind(0)`) + stdout
      readiness-handshake fixture with guaranteed teardown (D-15, D-16); no sleeps
- [ ] `crossproc` and `harness` markers registered in `pyproject.toml`
- [ ] Negative lint test pinning the D-24 carve-out boundary — a harness import in
      `ccf_runtime.a2a` / `ccf_runtime.cdc` must still fail
- [ ] Harness-extra skip mechanism: a skipped leg must name which harness and
      which extra enables it (CONTEXT.md Claude's-Discretion constraint; I.1
      CINV-04 deferral-skip precedent)

*Existing infrastructure (pytest, hypothesis, the factory-parametrized
conformance-suite pattern at `tests/conformance/test_approval_sink.py`) covers
the remainder.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none identified_ | — | — | — |

*All phase behaviors have automated verification. Research verified every harness
seam executes with **zero LLM calls** (D-09), so no leg requires a model
credential or a human in the loop.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 48/50; the 2 exceptions
      are blocking human checkpoints, which are not automatable by definition
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — verified
      against the map above; the two checkpoints are non-adjacent
- [x] Wave 0 covers all MISSING references — the four items below are delivered by 06-01,
      06-02, and 06-04 in wave 1–2, ahead of every consumer
- [x] No watch-mode flags — every command is a one-shot lint, mypy, or targeted pytest run
- [x] No sleep-gated readiness in any `crossproc` test (D-16) — asserted by a
      `grep -rn 'time.sleep' tests/crossproc/` acceptance criterion in every plan that adds
      a cross-process test (06-04, 06-06, 06-09, 06-17)
- [x] Multi-principal case present for every set-identity / admission / replay claim over
      shared Control Plane state (D-23) — 06-03-T3, 06-06-T3, 06-07-T3, 06-08-T3, 06-17-T2
- [x] Feedback latency < 60s — the per-area quick runs above; the two cross-process suites
      carry an explicit "< 30 s, no orphaned processes" criterion
- [x] `nyquist_compliant: true` set in frontmatter

**Planning-time sign-off:** contract complete, 2026-07-26.

**Execution sign-off:** 2026-07-27 (06-16 Task 3). 48/48 automated rows executed and green;
2 blocking human checkpoints marked, not ticked; 5 defective rows corrected in place with
their reasons stated above. Re-confirmed at sign-off:

- [x] **No sleep-gated readiness in any `crossproc` test (D-16)** — `grep -rn 'time.sleep'
      tests/crossproc/` is empty. Readiness is the stdout handshake from the 06-04 fixture.
- [x] **Multi-principal case present for every set-identity / admission / replay claim over
      shared Control Plane state (D-23)** — two tenants (`test_mcp_ingress.py::
      test_two_tenants_over_one_live_adapter_stay_isolated`), two peers with different keys
      and entitlements (`test_a2a_exchange.py`), two principals over one acquirer
      (`test_mcp_acquisition.py::test_two_principals_over_one_acquirer_receive_only_their_own`),
      and two agents across three harnesses (`test_harness_portability.py::
      test_two_agents_each_equal_across_harnesses_and_distinct_from_each_other`).
- [x] **`nyquist_compliant` still holds.** Execution added no task lacking an `<automated>`
      verify — the delivered task set is the planned 50, and the two checkpoints are
      non-adjacent. The planning-time value stands because it was re-checked against the
      delivered set, not because it was left alone.

**Phase approval is Dave's alone (CLAUDE.md §3.1). `D-GATE-I.3` is deliberately unwritten.**
