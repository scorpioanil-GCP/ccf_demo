# Adapter findings TP-01…TP-05 and the stdio door: close under the three-check acceptance

Spec: `docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md` §7.1 and §7.3 (the findings,
the verified facts, the known fix per finding) and `docs/DECISIONS.md` `D-IMPL-361`. Acceptance: Dave,
2026-10-06 19:21 MST — red before, green after, one severing, no prose closure.

## Global Constraints (binding on every task)

1. **Acceptance per finding is exactly three things.** (a) A test that is RED on the base tree and GREEN after the
   patch, asserting the hole AS WORDED in the spec (not a proxy). (b) ONE named severing: a specific edit that
   removes the new check, under which that test goes RED again. (c) Nothing else closes it. Commit the red test
   FIRST in its own commit (`test(TP-NN): red — <hole>`), then the fix (`fix(TP-NN): <mechanism>`), so the ledger
   can cite both SHAs. The severing is run, not described: purge every `__pycache__` under the tree and invoke
   `python -B` (CPython validates a cached `.pyc` on mtime-seconds and size, so a same-length edit otherwise loads
   stale bytecode and the severing never executes). Restore the file from saved bytes, never `git checkout --`.
   Record the severing's exact edit, the command, and the red output in the report.
2. **Interpreter and import check.** Use `/home/parkave/ccf_code/.venv/bin/python` (claude-agent-sdk 0.2.128,
   google-adk 2.5.0 installed). Before any test, run from your worktree
   `python -c "import ccf, ccf_runtime; print(ccf.__file__, ccf_runtime.__file__)"` and confirm both resolve
   INSIDE your worktree, not `/home/parkave/ccf_code`. If they do not, stop and report NEEDS_CONTEXT.
3. **Tests are offline.** No vendor subprocess is launched; no `claude` CLI, no network, no estate. Tests inspect
   what the adapter constructs (the options carrier, the in-process handler, the transport's environment, the
   argv-bound option, the ADK tool's run path) by calling it directly.
4. **Invariants that still hold.** No harness import under `src/` (CI lint). No prompt or instruction string
   literals in code (No-Hardcoding, CLAUDE.md §6.4). Typed contracts (`extra="forbid"`). The SDK ships mechanism,
   never values: an allowlist is deployment-declared; a roster of SDK skill-type NAMES is mechanism. US English.
   Cite the finding id (`TP-NN`) and `D-IMPL-361` in the docstring of every changed public symbol.
5. **Scope.** Change only the files the task names plus the tests. No documentation pages, no `DECISIONS.md`
   entries, no CHANGELOG (the controller writes the ledger line). Do not weaken or delete an existing test to get
   green; if an existing test pins the defective behavior, say so in the report and change it in the fix commit
   with the reason in the commit message.
6. **Counts come from captured files.** Run the covering test files and `tests/conformance/test_harness_adapter.py`
   with `-p no:cacheprovider -q 2>&1 | tee <report-dir>/<task>-tests.txt`; report passed / failed / errors as three
   numbers from that file. Then `mypy` on the changed files. The full suite is not required per task.
7. **Rulings made by the controller, carried here:** TP-02 child environment is an explicit allowlist, deployment-
   declared; when nothing is declared the child receives ONLY `PATH` and `HOME` (names, not values); every other
   variable is opt-in by name. Harness-exposable skill types are exactly `tool`, `mcp`, `local_callable`. Unknown
   wire arguments are REFUSED, never dropped, on ADK and on FastMCP. The system prompt reaches the CLI by file, mode
   0600, in a directory the adapter creates with mode 0700. The stdio door never fabricates an identity from its
   own fields; the caller composes one explicitly.

## Task 1 — Claude Agent SDK adapter: TP-01, TP-02, TP-05

Files: `runtime/ccf_runtime/adapters/claude_agent/adapter.py`; tests under `tests/adapters/claude_agent/`
(create the directory if absent) and the false-green driver in `tests/conformance/test_harness_adapter.py:478-500`.

**TP-01 — a read-only binding must not dispatch.** The vendor (0.2.128) routes CLI `tools/call` straight to the
in-process handler built by `_skill_handler` (adapter.py ~185-203) with NO Python-side permission check; the
`can_use_tool` gate at `_permission_gate` (~297-320) is enforced only by the semi-trusted CLI. Red test: construct
the adapter with `effects="unsupported"`, obtain the in-process handler for a bound skill (through
`inject_context`'s carrier `mcp_servers[...]` or by calling `_skill_handler` directly — measure which reaches the
real handler), call it with declared arguments, and assert the fabric's `invoke_skill` was NOT reached and the
result is a refusal naming the reason. Today it dispatches. Fix: the same two conditions the permission gate
applies (effects not governed → refuse; skill not in `agent.bound_skill_names` at call time → refuse) inside the
handler, BEFORE `invoke_skill`, returning an MCP error result (`{"content":[...], "isError": True}`) carrying the
adapter's own refusal reason. Severing: delete the effects condition inside the handler. Also invert the
false-green conformance driver at `tests/conformance/test_harness_adapter.py:483-495`: it pokes the vendor gate
with `{}`; add a driver leg that calls the in-process handler with declared arguments so the conformance refusal
proves the adapter-owned control, not the CLI's.

**TP-02 — the child environment.** Measure first: in the vendor's `claude_agent_sdk/_internal/transport/
subprocess_cli.py` (0.2.128), how is the subprocess environment built from `ClaudeAgentOptions.env` — does it
MERGE over `os.environ` or REPLACE it? Record the line numbers. Red test: with an unrelated variable set in
`os.environ` (e.g. `CCF_TEST_SECRET=...`), build the carrier and the environment the transport would hand the
child; assert the secret is ABSENT and the allowlisted names are present. Fix: the adapter takes
`child_environment: Mapping[str, str] | None` (the names and values to pass, deployment-declared) with the
controller's ruling for the undeclared case (`PATH`, `HOME` only, read from the fabric's environment by name);
set `carrier.env`. If the vendor merges over `os.environ` so `env` alone cannot subtract, ALSO ship a transport
subclass in the adapter module that builds the child environment from the allowlist only, expose it as the
adapter's `transport(carrier)` for the adopter to pass to `ClaudeSDKClient`/`query`, and make the red test assert
on that transport's environment. Severing: restore the merge (or delete the allowlist filter).

**TP-05 — the system prompt off argv.** Measure first: does the bundled CLI accept `--system-prompt-file`? (`grep`
the vendor package for the flag and check `extra_args` plumbing in `subprocess_cli.py`.) Red test: build the
carrier and assert `system_prompt` is not a string on the carrier and that the file option names a path whose
mode is `0600`, whose parent is `0700`, and whose bytes equal the assembled prompt (instructions + serialized
products, as `inject_context` joins them today at ~277-279). Fix: write the file, pass it via `extra_args`, leave
`system_prompt` unset; the directory is created per `inject_context` call with `tempfile.mkdtemp` (0700) and its
path is recorded on the adapter for the adopter to remove (document that in the docstring; do not add a
background cleaner). Severing: pass the string again. If the flag is unsupported in the pinned CLI, report BLOCKED
with the measurement.

## Task 2 — TP-03: the harness-exposable roster at the tool surface

Files: `src/ccf/skills/toolsurface.py`; `_tools()` in each of `runtime/ccf_runtime/adapters/{claude_agent,adk,
langgraph}/adapter.py`; tests under `tests/skills/` and `tests/adapters/`.

Today `render_tool_surface` refuses only `procedure` (raises `ProcedureHasNoToolSurface`), so a bound `peering` or
`mcp_product` skill renders as a harness tool (TP-03: the model calls it directly, receives unadmitted peer
products and drains the queue the admission gate reads), and no adapter catches the procedure refusal, so a bound
`procedure` skill makes `_tools()` raise on all three legs. Red tests: (a) for each of the three adapters, an agent
bound to a `peering` skill (and separately an `mcp_product` skill) exposes it as a tool today → must not;
(b) an agent bound to a `procedure` skill crashes `_tools()` today → must render the other skills and skip it.
Fix: `HARNESS_EXPOSABLE_SKILL_TYPES = frozenset({"tool", "mcp", "local_callable"})` in `toolsurface.py` (SDK
skill-type names: mechanism, not values); `render_tool_surface` refuses every non-exposable type with one typed
exception (`SkillHasNoToolSurface`, keeping `ProcedureHasNoToolSurface` as its subclass so existing catches and
tests hold); each adapter's `_tools()` filters by the roster before rendering and never raises for a bound
non-exposable skill. Severing: remove the roster filter from `render_tool_surface` (the adapters' filters then
decide; the test must redden on the `render_tool_surface` unit test AND the adapter test is kept as the second
witness — report both). Where `D-IMPL-25`'s "required iff the bound agent has a non-empty skill-set" is encoded
(search `HarnessAdapterProtocol` and the conformance suite), re-read it as "non-empty EXPOSABLE skill-set" and
report where you changed it.

## Task 3 — TP-04 and SEC353-J-01: undeclared wire arguments are refused, declared ones arrive

Files: `runtime/ccf_runtime/adapters/adk/adapter.py` (`_DeclaredSkillTool`, `_skill_tool` ~406-437); the FastMCP
tool registration for the product door and egress in `runtime/ccf_runtime/mcp/product_door.py` / `egress.py`
(find the site where the wire argument schema is handed to FastMCP); tests under `tests/adapters/adk/` and
`tests/mcp/`.

**ADK.** Measure first with google-adk 2.5.0: build `_DeclaredSkillTool` over a skill with one declared string
argument and run it through ADK's own run path (`run_async(args={...}, tool_context=...)` with a minimal context,
or whatever the vendor requires — record what you used) with a model-supplied value. The spec reports that
`call(**arguments: str)` receives NOTHING because ADK binds arguments against the inspected signature and a bare
`**kwargs` matches no declared name, so `invoke_skill` audits an empty mapping. Red test A: the declared argument
value reaches `invoke_skill`. Red test B: an undeclared key is REFUSED (an `EffectRefusal` through the adapter's
existing `_refusal` path, or a typed error result), not dropped. Fix: construct the callable with the declared
parameter names (build the signature from `surface.input_schema`, or override `run_async` to forward the raw
`args` mapping and validate it against the declared schema with `additionalProperties: false`), refusing unknown
keys before `invoke_skill`. Severing: drop the unknown-key check.

**FastMCP (SEC353-J-01).** Measure first: register the product tool as the door does and call it with one extra
argument not in the schema; the spec records that FastMCP drops it silently. Red test: the extra argument is
refused with a typed error naming the key. Fix: validate the raw wire arguments against the declared schema before
the handler runs (the same rule as ADK, stated once as a shared helper in `src/ccf/skills/` if both sites can use
it; otherwise two small call-site checks with a shared message shape). Severing: delete the validation call.

## Task 4 — the stdio door: no fabricated identity (EX-03 / EX-04, D-IMPL-361 §7.3)

Files: `runtime/ccf_runtime/mcp/product_door.py` (`serve_stdio` ~242-266); every call site of `serve_stdio(`
under `runtime/` and `examples/` (grep; list them in the report); tests under `tests/mcp/`.

Today `serve_stdio()` composes an `AuthenticatedUser` from the door's own `credential`, `principal_id`, `scope`
and `tenant_id` and sets it for every caller of the process. Red test: `serve_stdio()` called with no identity
argument sets an authenticated context from the door fields (assert via `auth_context_var` with `server.run`
stubbed) → after the fix it REFUSES with a typed error naming the ruling, and `serve_stdio(identity=...)` sets
exactly the identity passed. Fix: `serve_stdio` takes a required keyword `identity: AuthenticatedUser`; the door
removes the implicit composition; the docstring states stdio is single-principal by construction and the caller
composes the ambient identity. Update each call site to compose the identity explicitly with the same values it
used implicitly before (behavior-preserving at every call site; `D-IMPL-261` permits it because the SDK surface
changed deliberately). Severing: restore the implicit composition when `identity` is omitted.
