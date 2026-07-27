# Deferred items — Phase I.3

Out-of-scope discoveries, logged rather than fixed (executor SCOPE BOUNDARY).

## From plan 06-09 (wave 4)

**1. [RESOLVED by 06-13, verified at merge `86c498a`.]
`tests/conformance/test_harness_adapter.py` — two pre-existing failures,
environment-dependent.**

> **Resolution (orchestrator, wave 4 merge).** Root cause was cross-agent
> environment interference, not a defect on the base: worktrees isolate the
> filesystem but **all agents share one `.venv`**. Plan 06-13 installed
> `langgraph==1.2.9` into that shared venv while 06-09 was mid-flight, which
> retroactively falsified the tests' environmental premise. 06-09 measured the
> failures correctly and correctly attributed them elsewhere. 06-13 repointed
> both tests at a sentinel, `ABSENT_HARNESS = "ccf_no_such_harness_sdk"`, so the
> absent-harness path is exercised against a name that can never be installed.
> Full suite on the merged tree: 866 passed / 2 skipped, zero failures.
>
> Carried forward as a *process* finding for the gate: an environment-dependent
> test decays into vacuity exactly when the project succeeds, and had these been
> written with `skipif` rather than as assertions, the decay would have been
> silent. Wave 5 repeats the hazard — 06-14 installs `google-adk` into the same
> shared venv while 06-10 runs.

- `test_an_absent_harness_skips_with_an_instruction_not_a_mystery`
- `test_an_absent_harness_fails_when_the_environment_requires_it`

Both call `harness_unavailable("langgraph", "langgraph")` and expect it to
raise `Skipped` / `Failed`. In the project venv **langgraph is installed**, so
the harness is not absent and neither raises. The tests assert the behaviour of
the *absent*-harness path while naming a harness that is present, so they pass
only in an environment where the `langgraph` extra is missing — which is not
the documented `pip install -e ".[dev]"` environment.

Confirmed pre-existing on base `d51f9af`: the suite fails identically with
06-09's three new files excluded (801 passed / 2 failed), and 06-09 touched
nothing under `tests/conformance/` or `runtime/ccf_runtime/adapters/`.

Owner: plan 06-13 / the harness-adapter wave. The fix is to exercise the
absent-harness path against a name that is genuinely not installed (or to
monkeypatch the availability probe) rather than against a real harness.

**2. `tests/invariants/test_mcp_role_separation.py` digests the SQLite main
file only.**

`test_a_full_store_cycle_leaves_the_fabric_byte_identical` hashes
`database_path.read_bytes()`. The SQLite backend runs in WAL mode
(`src/ccf/graph/backends/sqlite.py:149`), so a committed write lands in
`<db>-wal` and can leave the main file byte-identical — 06-09 hit exactly this
and had to widen its own digest to cover `-wal`. The ArtifactStore assertion is
therefore weaker than it reads: it would not detect a write that had not yet
been checkpointed.

Not a live defect (no artifact-side write exists), but the observable is
weaker than its docstring claims. Owner: whichever plan next touches
`tests/invariants/test_mcp_role_separation.py`; the fix is the same
main-file-plus-WAL digest 06-09 uses.

> **Ownership assigned (orchestrator, wave 4 close): plan 06-16.** No wave-5
> plan touches this file, so "whichever plan next touches it" resolves to the
> gate package. Treat it as in scope for 06-16's verification sweep rather than
> as an observation to record: this is an *invariant* test whose assertion is
> weaker than it reads, and the single-writer / MCP role-separation property it
> guards is one the phase gate must evidence structurally (CLAUDE.md §7.4, §10).
> A byte-identical assertion that cannot observe an un-checkpointed WAL write is
> a false-green of the same family as the `mypy --strict src` CI override (06-02)
> and the absent-harness environmental premise above.

---

## Escalated to Dave at the wave-5 close (orchestrator)

**3. `AdmittedProduct` is not bound on L2's entry point — deferred by three
plans across three waves, each with a stated reason.**

Status: the invariant HOLDS but is not ENFORCED. CLAUDE.md §7.2 commits that an
inbound A2A Context Product "is not admissible to L3 until the consuming Control
Plane validates its Policy bindings", and §10 calls single-writer
"architectural, not advisory".

- 06-08 built the gate; left the binding, flagged it.
- 06-09 declined (`worker.py` outside `files_modified`) and stated its own
  evidence as deliberately weaker than a type guarantee: the consumer path is
  *observed* to run gate → `AdmittedProduct` → `worker.ingest`, AST-asserted as
  the only ingest call site, and a bypass makes the tamper test fail.
- 06-10 declined with a substantive reason, not scope avoidance:
  `AssemblyWorker.ingest` takes a `SignalEnvelope` and serves **every** L1
  source, so binding `AdmittedProduct` onto it would break CDC and MCP ingress.

Closing it properly requires a **second federated entry point** — a change to
L2's declared surface, which is a design decision rather than an executor
auto-fix. 06-10's concrete proposal: add
`AssemblyWorker.ingest_admitted(admitted: AdmittedProduct)` deriving envelopes
internally. Everything needed exists; only the ruling does not.

**4. `McpSkillRegistry` is not threaded from `AgentFactory` to `Agent`.**

Verified open at the wave-5 close: `Agent.invoke_skill(self, name, *, arguments)`
takes no registry, so an `mcp` skill invoked *through an Agent* refuses with
`McpSkillUnregistered`. `dispatch_skill` binds the transport correctly; the
wiring stops at `agent.py` / `factory.py`. Raised by 06-06, which noted it
"must close before harness skill exposure can surface an `mcp` skill as a
working tool" — i.e. before 06-15's neutrality proof, if that proof exercises an
`mcp`-transport skill.

## Resolved at the wave-5 close (orchestrator)

**`pip check` breakage was venv drift, not a pinning defect — NO ACTION NEEDED.**
06-14 correctly reported `pip check` broken after its `google-adk` install
(`opentelemetry-exporter-otlp-proto-grpc 1.44.0` vs `opentelemetry-sdk 1.42.1`)
and inferred "a CI image build would surface it". The inference was backwards.
Dry-run resolves of both documented commands are internally consistent:
`.[dev]` → otel 1.42.1 with no exporter at all; `.[dev,chroma]` → otel 1.42.1
**and** exporter 1.42.1. Only a long-lived incrementally-mutated venv reaches the
broken state: `chromadb` was installed in an earlier phase when otel was 1.44.0
(pulling exporter 1.44.0), and `google-adk` later downgraded the *sdk* without
downgrading the already-installed *exporter*. CI resolves from scratch and never
sees it. Local venv repaired by pinning the exporter to 1.42.1; `pip check`
clean, 926 passed / 2 skipped. D-08's one-command requirement is intact.
