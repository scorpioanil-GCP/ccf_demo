# Phase 20: Client Access from Three Harnesses — ADK, Anthropic Agent SDK and LangGraph Agents Reaching One Context Product over MCP - Context

**Gathered:** 2026-08-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Three client programs — one Google ADK, one Anthropic Agent SDK, one LangGraph —
each registering the **Phase 18.1 `mcp+stdio` door** on
`examples/hw1-companies-over-revenue` as an ordinary MCP tool, calling it, and
printing the returned Context Product to the console. Same product, same door,
three harnesses.

**In scope:** one new example directory holding the three client programs, a
fabric-side runner, one README, a CI-green default path, `--live` opt-in,
an AST-gated client-purity check with a named sabotage control, and the
in-phase resolution of the two prior-vintage duplicate sets.

**Not in scope, and a diff reaching here is a blocking review event:** any new
SDK mechanism — no new transport, no new adapter, no change to `ccf.client` or
the codec, no `HarnessAdapterProtocol` implementation, no file touched under
`src/ccf/client/`. Also out of scope: how the MCP server is assembled (stays
off-stage until the assembly examples), and any fourth harness.

**The ten ROADMAP Success Criteria are the gate target and are not expanded by
anything in this document.** Every decision below is a *how*, not a *what*.

</domain>

<decisions>
## Implementation Decisions

> **Numbering.** `H-NN` are decisions from *this discussion* and are a distinct
> namespace from the client design spec's `D-NN`, from Phase 18.1's `D-NN`,
> from Phase 19's `C-NN`, and from the project decision log's `D-IMPL-NN`.
> On ratification these become `D-IMPL-NN` entries in `docs/DECISIONS.md`.
> `H-01` and `H-02` were ruled by Dave in the scope-confirmation exchange
> before the gray-area rounds; the rest were ruled during them.

### The client contract — how a zero-CCF client finds the door

- **H-01:** **The pre-spawned-endpoint premise is rejected as physically
  impossible, and the contract is restated.** MCP stdio has no hand-offable
  endpoint: the client library *is* what spawns the child and owns its
  stdin/stdout. Measured against all three installed harnesses — ADK's
  `StdioConnectionParams(server_params=StdioServerParameters)`
  (`google/adk/tools/mcp_tool/mcp_session_manager.py:177`), the Claude Agent
  SDK's `McpStdioServerConfig` (`claude_agent_sdk/types.py:603`), and raw
  `mcp.client.stdio.stdio_client` — **every one takes `command + args` and
  spawns the child itself.** A runner that pre-spawns and passes pipes cannot
  work.

- **H-02:** **The locked division of responsibility.**
  - **The runner** may import `ccf`. It resolves the deployment root →
    `binding.yaml`'s `server:` key → an **opaque `command + args` pair**, seeds
    the deployment for CI, and invokes each client with that pair.
  - **Each client** imports its harness, an MCP client and stdlib, and
    **nothing from `ccf`**. It receives `command + args` as configuration and
    passes them into its harness's own stdio params. It spawns via the harness,
    registers the product tool, calls it, prints the result.

  The client's experience is therefore exactly what an adopter sees configuring
  *any* MCP server. That is a stronger teaching artifact than a CCF-specific
  spawn path, and purity is held by the client never learning what CCF is —
  not by keeping the client away from a subprocess.

- **H-03:** **The runner hands the pair over via `argv`**, as explicit flags on
  each client program. Visible in the README's documented command, greppable,
  and the client's own signature says the door's location is an *input* rather
  than knowledge. Rejected: a single env var (`CCF_MCP_SERVER_CMD` — invisible
  to `test_client_example_purity`'s command-identity checks, which read the
  documented command string); and a runner-generated `.mcp.json` (closest to
  real-world MCP configuration convention and 00-hello-context already ships an
  `.mcp.json` docs-only leg, but a fourth moving part and a file format to keep
  in step).

### What CI answers against

- **H-04:** **A declared scenario document ships in the new directory, and
  `D-32` is narrowed on the record.** Two constraints collide and left no room:
  `D-32` (Dave, 2026-08-15) forbids a *seed artifact* under `examples/`, and
  `no-hardcoding` covers `examples/`
  (`tools/lints/__main__.py::RULE_TREE_SCOPE = ("src","runtime","examples","tests")`),
  so the values cannot be Python constants in the runner either. The narrowing:
  **`D-32` governs a committed store file and a populated graph — producer
  *output* — not a declared *input* document that a fabric-side runner
  interprets.** `examples/external/00-hello-context/artifacts/events.yaml` is
  already exactly this shape and predates the ruling. The narrowing is
  deliberate and must be recorded as its own `D-IMPL` entry; it is not a quiet
  reading. Rejected: importing `tests/client/conftest.py::seed` and
  `SEEDED_ROWS` (ships zero new data and needs no narrowing, but makes a
  shipped example depend on the test tree and sends a reader into `tests/` to
  find out what the data is); and keeping the empty deployment as the CI
  subject (zero `D-32` pressure and criterion 4 still holds, since
  `test_hw1_two_transports` proves an empty deployment prints a real content
  address — rejected by Dave as a weak demonstration).

- **H-05:** **The CI subject is a seeded temporary copy, never the tracked
  tree.** The runner `copytree`s `examples/hw1-companies-over-revenue/deployment`
  into a temp directory, seeds it, **closes the writer**, spawns the door
  against the copy, and runs `consume.py` against the **same copy** to produce
  criterion 4's reference content address. hw1's tracked tree is never written
  to and its `.gitignore` stays untouched. Each leg may take its own copy so
  three spawned servers never contend for one graph. Mirrors
  `tests/client/conformance/conftest.py`. Rejected: seeding hw1's deployment in
  place (legal, since `graph.sqlite3` is gitignored, and it would leave the
  README's hw1 commands literally runnable — but CI would mutate a tracked
  example's working directory and leave populated state behind for whatever
  runs next).

  **The writer close is load-bearing, not tidiness.** The writer is held per
  graph (`ccf.graph._writer::_LIVE_WRITERS`); a seeder that stayed open makes
  the door's own boot raise `SingleWriterViolation`, and the phase would be
  measuring the seed's failure to let go rather than anything about a client.
  `tests/client/conftest.py::seed` documents this and is the pattern to
  inherit.

### How the model call is killed

- **H-06:** **The default path is "the harness invokes the registered tool",
  with no model.** This is literally what criteria 1–3 say — *registers the
  door as a tool, calls it, and prints*. Deterministic by construction, no
  fixtures needed for the ADK and LangGraph legs, and
  `examples/03-harness-portability/legs/deterministic.py`'s
  `install_no_model_guard()` is the precedent for proving nothing reached a
  model. Rejected: a model-driven default replayed through fixtures (richer —
  it would show an agent *choosing* CCF context — and it is what ruling 5's
  copied replay harness anticipated, but it costs three recordings that need a
  live key to capture, a model provider for LangGraph that is not installed,
  and fixtures that drift the day the tool schema changes).

- **H-07:** **Leg 2 runs the real `claude` CLI against a replayed model, and
  the asymmetry is stated in the example rather than smoothed over.** Measured:
  `claude_agent_sdk` routes everything — *including its MCP client* — through
  the `claude` CLI subprocess (`_internal/transport/subprocess_cli.py:159`,
  `shutil.which("claude")`). Example 03's custom-`Transport` technique replaces
  the CLI wholesale, which is exactly what removes the MCP call, so a scripted
  transport cannot satisfy criterion 2. Therefore leg 2 keeps the real CLI,
  configures the door via `McpStdioServerConfig`, and points
  `ANTHROPIC_BASE_URL` at the copied replay server.

  **Consequence, to be written into the README rather than hidden:** in the
  default path the three programs are *not* the same program three ways. ADK
  and LangGraph put the MCP client in your process, so the client drives the
  tool directly; the Claude Agent SDK puts it in an agent binary you configure.
  *Who holds the MCP session* differs by harness — and that is a genuinely
  useful thing for an adopter to learn before choosing one. What does **not**
  differ is CCF: one tool registration, one call, in all three.

  Rejected: swapping leg 2 to the raw `anthropic` SDK the way
  `examples/external/00-hello-context/client_anthropic.py` does (no CLI, replay
  already proven against `/v1/messages` — but criterion 2 says *Anthropic Agent
  SDK* and criteria are not reinterpreted at planning); and making leg 2
  `--live`-only (cheapest and most honest about the constraint, but ruling 1
  rejected "unrun" by name and criterion 6 requires a deterministic default for
  every leg).

- **H-08:** **The replay harness is copied for the leg that needs it, and only
  that leg.** Ruling 5 said what Phase 20 inherits is the **runner design** —
  deterministic default, `--live` opt-in — not a shared implementation. With
  `H-06`, only leg 2 goes through a model, so `replay_server.py` is copied into
  the new directory for leg 2 and is not carried for legs 1 and 3. Ruling 5 is
  therefore **discharged as scoped, not violated and not moot**. Rejected:
  copying it regardless to serve the `--live` legs' recording path — a
  400-line file the default path never exercises is the "member nothing reads"
  pattern Phase 19's `C-10` exists to refuse.

- **H-09:** **`--live` means one thing across all three legs: point at a real
  populated deployment** instead of the seeded temp copy. No leg gains a model
  it did not already have; for leg 2, `--live` additionally drops the replay so
  its model is real. One flag, one meaning, and **no code path exists that CI
  never exercises**. Rejected: `--live` also switching legs 1 and 3 to a
  model-driven loop (strongest demonstration, but it builds a second per-leg
  path CI never runs — criterion 6's own "documented but never run" failure
  mode — and LangGraph would need a model provider package that is not
  installed); and two orthogonal flags `--live-deployment` / `--live-model`
  (most precise about the two real axes, at the cost of four combinations per
  harness of which CI runs one).

### Layout, and the gate that follows from it

- **H-10:** **The directory is `examples/hw1-harness-clients/`** — the
  ROADMAP's own float. It names the door it reaches and what it holds, and
  sorts beside `examples/hw1-companies-over-revenue/` so a reader finds the
  door and its foreign consumers together. Rejected:
  `examples/external/01-three-harnesses/` (sits in the existing "external"
  grouping as `00-hello-context`'s numbered successor, but adjacency to the
  directory being marked historical is precisely the confusability ruling 3
  wants avoided); and `examples/hw1-three-harnesses/`.

- **H-11:** **The example root holds only the three `client_*.py`; the runner
  lives in a subdirectory.** This inverts `00-hello-context`'s layout (where
  `run.py` sits at the root) and it is the point: it makes the *existing*
  structural rule do the work.

- **H-12:** **Client purity is gated by extending
  `tests/examples/test_client_example_purity.py`**, by adding the new root to
  `CLIENT_EXAMPLE_ROOTS` — which the module's own comment invites: *"a second
  client example joins by being added here, and every function below already
  takes its root as an argument."* Its rule that **every `.py` directly in the
  example root is reader-visible** then gates the three clients untouched, and
  `H-11` puts the `ccf`-importing runner structurally outside it. **No rule is
  weakened to accommodate a file.**

  This gate is already AST-based and already refuses the two forgeries Phase 19
  spent a wave learning about — an import deferred into a function body
  (`test_the_gate_refuses_an_import_deferred_into_a_function_body`) and a
  relative import (`test_the_gate_refuses_a_relative_import`). Criterion 5 says
  *AST check*, and `examples/external/00-hello-context/run.py::_assert_zero_ccf_imports`
  is a **static grep** — the shape Phase 19's `C-17` measured inadequate. The
  grep is not the precedent to inherit.

  Per `CLNT-12` / `D-22`, **the new gate coverage carries a named sabotage
  control in the same plan that adds it.** Rejected: teaching
  `reader_visible_modules` to skip a declared fabric-side entry module (puts a
  hole in a rule built structural rather than name-based, and that hole is the
  kind a later example widens); and a fresh AST gate in the example's own suite
  (most freedom and no coupling, but a second implementation of one invariant
  is a second thing to keep in step, and its controls start from zero).

### Resolving the prior-vintage duplicates

- **H-13:** **`examples/s2-01-external-consumers/` moves out of `examples/`
  entirely**, to a clearly non-example retired-material path, with a note
  naming Phase 16, `D-IMPL-152`, and Phase 20's trio as its replacement. This
  is the only option that literally discharges ruling 3's *"the tree must not
  carry three ADK and two LangGraph clients at mixed vintages"* — afterwards
  `examples/` holds exactly one LangGraph client. **Note for planning:** this
  repository has **no existing quarantine convention** (no `_retired/`,
  `attic/`, `archive/` anywhere); its precedent for retiring things (15.4,
  15.6) is deletion plus a written record, so the destination is invented here
  and should be chosen to read as non-example on sight. Rejected:
  `examples/_retired/` (cheap and discoverable, but `examples/` still holds two
  LangGraph clients and the underscore is a convention this repo does not use);
  and leaving it in place with a retired marker (smallest diff, weakest reading
  of "quarantine", and the files still look live in a directory listing).

- **H-14:** **`examples/external/00-hello-context/` stays running and CI-green,
  and is marked historical in its README.** It is exercised by
  `make example-ext-00` and `tests/examples/test_ext00_hardening.py`. The
  marking states that its clients target the **pre-Phase-17 surface over HTTP
  with bearer auth**, and that Phase 20's trio is the canonical foreign-harness
  demonstration going forward. Ruling 3 is satisfied by a sentence, not a move.
  Rejected: retiring the whole example (cleanest tree, but it deletes eight
  passing CI assertions — auth refusal, dual serve-path byte equality, replay
  reproduction — that have nothing to do with this phase, which is scope Phase
  20 does not have).

### Claude's Discretion

- The exact filename and schema of the declared scenario document (`H-04`), and
  how many rows it declares — subject to producing a non-empty, visibly
  interesting answer.
- The subdirectory name the runner lives in (`H-11`).
- The retired-material destination path for `H-13`, subject to reading as
  non-example on sight and sitting outside `examples/`.
- Whether each leg gets its own seeded copy or the legs run sequentially
  against one (`H-05`), provided no two server children ever hold one graph.
- The precise `argv` flag names (`H-03`).
- Which requirement numbers in the `CLNT-NN` lane are minted, and their
  wording (lane itself is settled — ROADMAP ruling 4).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The phase's own charter
- `.planning/ROADMAP.md` — the Phase 20 entry: scope, the five carried-in
  rulings, and the **ten Success Criteria that are the gate target and are not
  to be expanded during planning**
- `CLAUDE.md` §7.3 — *"a harness that already speaks MCP needs no adapter for
  consumption"*, the claim under test
- `CLAUDE.md` §9 — the examples-suite discipline: runnable end-to-end, code and
  artifacts side by side, a README per example, **a broken example is a broken
  build**
- `CLAUDE.md` §6.4 — the No-Hardcoding Rule, which scopes to `examples/`

### The door this phase reaches, and the client it must agree with
- `examples/hw1-companies-over-revenue/README.md` — the frame Phase 18.1 set,
  the two documented commands, the "how a product is assembled is out of scope"
  sentence this example must echo, and the `## Populating a deployment` section
  that states `D-32`
- `examples/hw1-companies-over-revenue/consume.py` — the reference client;
  produces criterion 4's comparison address
- `examples/hw1-companies-over-revenue/deployment/binding.yaml` — the
  `server: server/serve.py` key the runner resolves (`H-02`)
- `examples/hw1-companies-over-revenue/deployment/scenario.yaml` — the
  attribute-role document a seeder reads
- `examples/hw1-companies-over-revenue/server/serve.py` — stdio-only
  (`server.run(transport="stdio")`, spawned with `argv[1]` = deployment root),
  and the stdio-identity trust statement
- `examples/hw1-companies-over-revenue/deployment/.gitignore` — where `D-32` is
  recorded as mechanism

### Prior-phase decisions this phase is bound by
- `.planning/phases/18.1-simplify-the-mcp-example-separate-the-server-from-the-client/18.1-CONTEXT.md`
  — `D-04`/`D-05` (one-token address, server command as deployment data),
  `D-10` (`server:` resolves against the deployment root's parent), `D-14`–`D-17`
  (the README frame this example must not contradict)
- `.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-CONTEXT.md`
  — `C-16` (**the MCP product tool takes the encoded `WireRequest` as a
  REQUIRED argument** — every foreign-harness caller must produce it),
  `C-17` (the narrow-AST-gate-with-named-sabotage-control shape),
  `C-10` (no member on the wire that nothing reads)
- `docs/superpowers/specs/2026-08-15-ccf-client-design.md` — the client design
  spec's `D-NN` namespace, including `D-32`

### Patterns to inherit (and one not to)
- `examples/external/00-hello-context/run.py` — the **runner design** ruling 5
  says this phase inherits: deterministic default, `--live` opt-in, bounded
  `READY` handshakes, children killed in `finally`. **Its
  `_assert_zero_ccf_imports` static grep is NOT the precedent** (`H-12`)
- `examples/external/00-hello-context/replay_server.py` — copied for leg 2 only
  (`H-08`); routes by path suffix, fingerprints each request against a recorded
  sibling, fails loudly on drift or exhaustion
- `examples/03-harness-portability/legs/deterministic.py` — **real harness loop
  machinery with no model**, and `install_no_model_guard()`; the technique
  `H-06` builds on (its code is producer-side and does not transfer)
- `tests/client/conftest.py::seed` — seeds via the deployment's own
  `scenario.yaml` + `binding.yaml` through the shipped loader, then **closes**
  to release the writer (`H-05`)
- `tests/client/conformance/conftest.py` — one fresh populated root per
  subject, never a shared one

### Gates and CI
- `tests/examples/test_client_example_purity.py` — the AST purity gate
  `H-12` extends; `CLIENT_EXAMPLE_ROOTS`, `reader_visible_modules`, and the
  command-identity checks
- `tests/examples/test_hw1_two_transports.py` — proves an **empty** deployment
  still prints a real content address; the parity-comparison controls
- `tests/client/test_surface.py` — `C-17`'s AST gate and its numbered
  CONTROL tests, the shape a new gate's sabotage control should match
- `tools/lints/__main__.py` — `RULE_TREE_SCOPE`; `no-hardcoding` covers
  `examples/`
- `Makefile` — the `examples` target list, `example-ext-00`, the
  `example-*-live-*` opt-in targets, and `ci`/`ci-core`
- `.github/workflows/ci.yml` — Python-only, `ubuntu-latest`, no node step
  today (relevant to `H-07`'s CLI dependency)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **All three harnesses are already dev dependencies** — `google-adk==2.5.0`,
  `claude-agent-sdk==0.2.128`, `langgraph==1.2.9`, composed by
  `ccf[harnesses]` into `dev` (`pyproject.toml`). No install work.
- `tests/examples/test_client_example_purity.py` — extensible by design;
  every function already takes a root argument.
- `tests/client/conftest.py::seed` — a working seed-and-release-the-writer
  implementation to re-implement against.
- `examples/external/00-hello-context/replay_server.py` — a hardened,
  fail-loud model-API replay server, copied for leg 2.
- `examples/s2-01-external-consumers/client_langgraph.py` — the
  `StructuredTool`-wrapping-a-raw-`mcp`-session shape for LangGraph. It targets
  streamable HTTP; the same shape over `stdio_client` is leg 3's likely form.
  It is being quarantined (`H-13`), so read it before the move, not after.

### Established Patterns
- **No foreign-harness client in this tree has ever spoken `mcp+stdio`.** Every
  prior one (`00-hello-context`, `s2-01`) uses `streamablehttp_client` with a
  bearer token against a server the runner stood up. Phase 20 is the first
  stdio foreign client; the HTTP clients are not a transport template.
- **`langchain-mcp-adapters` is NOT installed**, and neither is any langchain
  model provider — only `langchain_core` 1.5.1 and `langchain_protocol`. Leg 3
  either uses raw `mcp` + `StructuredTool` or the phase acquires a dependency,
  which is a decision, not a detail.
- The `install_no_model_guard()` idea from example 03: prove the absence of a
  model call rather than assert it.
- Sabotage controls accompany every new check in the same plan (`CLNT-12`).

### Integration Points
- `Makefile` — a new target for the example, wired into `examples` (criterion
  10), plus per-harness `--live` targets alongside `example-ext-00-live-*`.
- `tests/examples/test_client_example_purity.py::CLIENT_EXAMPLE_ROOTS`.
- `examples/external/00-hello-context/README.md` — the historical marking
  (`H-14`).
- `.github/workflows/ci.yml` — see the risk below.

### Risk flagged for research, not resolved here
`H-07` introduces an **always-on CI dependency on the `claude` CLI binary**,
which is not a Python package, cannot be pinned in `pyproject.toml`, and has no
install step in `ci.yml` today. It is also unverified whether the CLI can be
driven **fully offline** against a replay server — it may perform auth,
version, or telemetry handshakes that the copied `replay_server.py` would also
have to answer, and its traffic is richer and less stable than the raw
Messages API the existing fixtures record. **Research must establish this
before planning commits leg 2's default path**, because criterion 10 (`make ci`
exit 0) depends on it. If it proves undriveable offline, that is a `D-IMPL-NN`
and a stop — not a quiet demotion of leg 2 to `--live`.

</code_context>

<specifics>
## Specific Ideas

- **"The client's experience is exactly what an adopter sees when configuring
  any MCP server."** Dave's framing of `H-02`, and the sentence the README
  should be built around.
- **The asymmetry is the lesson, not the embarrassment.** `H-07` — ADK and
  LangGraph hold the MCP session in your process; the Claude Agent SDK holds it
  in an agent binary you configure. Say so.
- **"Same product, same door, three harnesses"** — the README frame named in
  ruling 2. One README, not three.
- Criterion 4's comparison is against `consume.py` **run by the runner on the
  same seeded copy**, not against a recorded address.

</specifics>

<deferred>
## Deferred Ideas

- **A model-driven leg for ADK and LangGraph** — an agent actually *choosing*
  to call CCF context is a stronger demonstration than a direct tool
  invocation, but `H-06`/`H-09` keep it out because it builds paths CI never
  runs. If it is ever wanted, it wants its own phase and its own fixtures.
- **A fourth harness.** Explicitly out of scope in the ROADMAP entry.
- **`HarnessAdapterProtocol` work (`D-IMPL-24`/`D-IMPL-25`).** Producer-side,
  and not what this phase is about — a harness *consuming* MCP needs no
  adapter, which is the claim under test.
- **Retiring `examples/external/00-hello-context/` entirely** and folding its
  unique assertions (auth refusal, dual serve-path byte equality, replay
  reproduction) elsewhere. Considered under `H-14` and rejected as scope this
  phase does not have.
- **A repository-wide retired-material convention.** `H-13` invents one
  destination for one directory; generalizing it is not this phase's job.

</deferred>

---

*Phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a*
*Context gathered: 2026-08-20*
