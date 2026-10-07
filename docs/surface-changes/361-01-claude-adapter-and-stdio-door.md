# 361-01 — the Claude adapter's child process and the stdio door's identity

`D-IMPL-361`, the v1.0.2 adapter findings. This fragment covers `TP-01`
(the in-process handler refuses before dispatch), `TP-02` (the `claude` child
is spawned from a deployment-declared allowlist, and the carrier fails closed
on the vendor's default transport), `TP-05` (the system prompt reaches the CLI
by a `0600` file, never by argv) and `EX-03`/`EX-04` (the stdio door takes a
caller-composed identity and fabricates none).

Closure record, stated as shipped (the whole-branch review's I-1, I-3 and I-4):

- `TP-01` is closed on all three legs only after I-1. The Claude in-process
  handler refused a read-only binding first; the LangGraph tools exposed on
  `carrier.tools` and the ADK tool's own `run_async` dispatched until the I-1
  fix (recorded in `361-02`). `effects: unsupported` now means no dispatch and
  no write-back on every leg.
- `TP-02` has two halves. The env half: the child is spawned from a
  deployment-declared allowlist through `adapter.transport(carrier)`, and the
  carrier fails closed on the vendor's default transport because its
  `cli_path` is below `os.devnull` (I-3). The options half: the carrier sets
  `tools=[]`, `setting_sources=[]` and `strict_mcp_config=True` unconditionally,
  and `cwd` is the per-call `0700` directory unless declared (I-4).
- Residuals, disclosed rather than closed: `max_turns` is a budget the adopter
  declares (`None` is the vendor default), not a boundary; and a custom
  transport bypasses the vendor's session-store resume
  (`client.py:126-135`, `materialize_resume_session`), so session resume is
  unavailable on the governed path — it fails safe.

## ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter

- Surface: ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter
- Public surface: true
- Change type: reshaped
- Before: `ClaudeAgentAdapter(*, model, mcp_server_name, mcp_server_version, effects)`; `inject_context` put the joined system prompt on the carrier as a string, and the vendor's default transport spawned `claude` with the fabric's whole environment
- After: new keywords `child_environment: Mapping[str, str] | None = None` (`TP-02`), the complete environment, names and values, the child receives — `None` gives the child only `DEFAULT_CHILD_ENVIRONMENT`'s names (`PATH`, `HOME`) valued from the fabric; `cwd: str | Path | None = None`, the child's working directory, `None` meaning the per-call `0700` directory (`TP-02` options half, I-4); and `max_turns: int | None = None`, the turn budget, `None` meaning the vendor default (a budget, not a boundary). New members `transport(carrier)` (`TP-02`), `prompt_directories` and `remove_prompt_directories()` (`TP-05`). `inject_context` now writes the prompt to a `0600` file in a new `0700` directory and sets `system_prompt` to the vendor's typed file form; it sets the carrier's `env` to the allowlist, `tools=[]`, `setting_sources=[]`, `strict_mcp_config=True`, and `cli_path` to a path below `os.devnull` that can never exist, so the carrier fails closed on the vendor's default transport (I-3, `D-IMPL-361`)
- Why: `TP-02` — `ClaudeAgentOptions.env` merges over `os.environ` and cannot subtract, so every fabric secret reached the child; `TP-05` — a string `system_prompt` lands on the `claude` argv as `--system-prompt <text>`, readable by every local process and any process audit
- Migration: pass `transport=adapter.transport(carrier)` to `ClaudeSDKClient(...)` or `query(...)`; without it the vendor's default transport raises `CLIConnectionError` and starts nothing. Declare `child_environment` with every variable the CLI needs beyond `PATH` and `HOME` (an API key, a proxy). The CLI no longer loads host settings, built-in tools or foreign MCP servers; a deployment that relied on any of those must now provide them as governed skills. Declare `cwd` if the session needs a particular working directory, and `max_turns` if it needs a turn budget. Call `remove_prompt_directories()` once the sessions that used the carriers have ended.

## ccf_runtime.adapters.claude_agent.ClaudeAgentAdapter

- Surface: ccf_runtime.adapters.claude_agent.ClaudeAgentAdapter
- Public surface: true
- Change type: reshaped
- Before: the package re-export of the class above, with the old constructor
- After: the same class, reshaped as recorded under `ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter` (`TP-02`, `TP-05`, I-3, I-4)
- Why: the package re-exports the class, so the manifest records the reshape under both names
- Migration: as for `ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter`

## ccf_runtime.adapters.claude_agent.adapter.AllowlistedEnvironmentTransport

- Surface: ccf_runtime.adapters.claude_agent.adapter.AllowlistedEnvironmentTransport
- Public surface: true
- Change type: added
- Before: absent — the vendor's `SubprocessCLITransport` built the child environment as `{**os.environ, ..., **options.env}` and ran a version probe that inherited the environment whole
- After: a subclass of the vendor's subprocess transport whose `connect()` spawns the child with exactly `child_environment()` — the carrier's `env` plus the vendor's own mechanism variables — and nothing inherited; the version probe is not run (`TP-02`, `D-IMPL-361`)
- Why: the env half of `TP-02` cannot be closed from options alone, because `env` merges and cannot subtract. It subclasses a private vendor module (measured against claude-agent-sdk 0.2.128), so a vendor upgrade must be re-measured against it.
- Migration: none to construct it by hand; obtain it from `ClaudeAgentAdapter.transport(carrier)`

## ccf_runtime.adapters.claude_agent.adapter.DEFAULT_CHILD_ENVIRONMENT

- Surface: ccf_runtime.adapters.claude_agent.adapter.DEFAULT_CHILD_ENVIRONMENT
- Public surface: true
- Change type: added
- Before: absent
- After: `tuple[str, ...] = ("PATH", "HOME")` — the variable NAMES the child receives when the deployment declares no `child_environment` (`TP-02`, `D-IMPL-361`)
- Why: the controller's ruling is an explicit allowlist with a minimal default; the roster is names, never values, so it is mechanism rather than a deployment value
- Migration: none; new name. A deployment that needs more declares `child_environment` in full.

## ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.transport

- Surface: ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.transport
- Public surface: true
- Change type: behavior
- Before: absent — an adopter handed the carrier to the vendor and got the vendor's default transport
- After: `transport(carrier) -> AllowlistedEnvironmentTransport`; first verifies, with `lstat`, that the carrier's system-prompt file is a regular file owned by the effective uid with mode `0600` in a directory owned by the effective uid with mode `0700`, and raises `PromptFileRefused` otherwise (I-3); then clears the carrier's fail-closed `cli_path` sentinel for this transport only and routes the permission prompt over stdio when a `can_use_tool` gate is bound. `TP-02` holds through `adapter.transport(carrier)`; the plain vendor path (`ClaudeSDKClient(options=carrier)` with no transport) fails closed with `CLIConnectionError` (`D-IMPL-361`)
- Why: the manifest records class shapes, not methods, so this new method is recorded as a behavior entry; it is the one supported way to start a session from the carrier
- Migration: pass `transport=adapter.transport(carrier)` wherever the carrier is handed to the vendor

## ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.remove_prompt_directories

- Surface: ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.remove_prompt_directories
- Public surface: true
- Change type: behavior
- Before: absent — no prompt was written at rest
- After: removes every per-call system-prompt directory recorded on `prompt_directories` and forgets it; synchronous and idempotent (`TP-05`, `D-IMPL-361`). A carrier whose directory was removed cannot start a session on either path: `transport(carrier)` refuses it with `PromptFileRefused` (also when another local user has recreated the directory, which is then not owned by the effective uid), and the vendor's default transport cannot start it because `cli_path` is below `os.devnull` (I-3).
- Why: each directory holds the full assembled prompt, including the canonical bytes of every delivered product, at rest; the adapter cannot know when the harness has finished reading it, so removal is the adopter's call
- Migration: call it once the sessions that used the adapter's carriers have ended

## ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.inject_context

- Surface: ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.inject_context
- Public surface: true
- Change type: behavior
- Before: `system_prompt` was the joined prompt string (it reached the `claude` argv); `env`, `cli_path`, `tools`, `setting_sources`, `strict_mcp_config`, `cwd` and `max_turns` were unset
- After: `system_prompt` is `{"type": "file", "path": ...}` naming a `0600` file in a new `0700` directory recorded on `prompt_directories` (`TP-05`); `env` is the deployment's allowlist (`TP-02`); `cli_path` is `/dev/null/ccf-no-cli` (below `os.devnull`, never creatable), so the vendor's default transport fails closed with `CLIConnectionError` (`TP-02`, I-3); `tools=[]`, `setting_sources=[]` and `strict_mcp_config=True` unconditionally; `cwd` is the declared one or the per-call `0700` directory; `max_turns` is the declared budget (`TP-02` options half, I-4, `D-IMPL-361`)
- Why: argv is world-readable on the host; the vendor's default transport merges the fabric's whole environment into the child; with `tools` and `setting_sources` unset the CLI keeps its built-in tools (Bash, the file tools) and loads `~/.claude/settings.json`, whose allow-rules could permit a tool without consulting `can_use_tool` (a stated risk, unmeasured against the live CLI; claude-agent-sdk 0.2.128, `subprocess_cli.py:478-488`, `:599-600`)
- Migration: as for the class: hand the vendor `adapter.transport(carrier)`, and remove the prompt directories when done

## ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.expose_skills

- Surface: ccf_runtime.adapters.claude_agent.adapter.ClaudeAgentAdapter.expose_skills
- Public surface: true
- Change type: behavior
- Before: the in-process MCP handler for each bound skill called `invoke_skill` with every argument stringified, and was reachable under `effects: unsupported` and for a skill revoked since the carrier was built, because the vendor routes a CLI `tools/call` to the handler with no Python-side permission check
- After: the handler is the adapter-owned control (`TP-01`, `D-IMPL-361`): it refuses every call when the binding declared `effects` other than `governed`, refuses a skill not in `agent.bound_skill_names` at call time, and renders an `ArgumentRefused` from the seam as an `is_error` result; arguments reach `invoke_skill` as they arrived, not stringified (`TP-04` follow-on)
- Why: `allowed_tools` and `can_use_tool` are enforced by the semi-trusted CLI and are defense in depth only
- Migration: none — a read-only binding never dispatched by design; this makes it hold without the CLI's cooperation

## ccf_runtime.mcp.product_door.ProductDoor.serve_stdio

- Surface: ccf_runtime.mcp.product_door.ProductDoor.serve_stdio
- Public surface: true
- Change type: behavior
- Before: `serve_stdio()` composed one identity from the door's own fields with `ambient_stdio_identity` and served it to every caller of the process
- After: `serve_stdio(*, identity: AuthenticatedUser)` — required in practice; omitting it (or passing anything not an `AuthenticatedUser`) is refused with `StdioIdentityRequired` before the server is built or anything is set. The door composes no identity; the caller composes one (typically with `ccf_runtime.mcp.tenancy.ambient_stdio_identity`) and passes it. Stdio remains single-principal by construction (`EX-03`/`EX-04`, `D-IMPL-361` §7.3)
- Why: an identity the door fabricates from its own fields is an identity nobody presented; making the caller compose it puts the statement where the deployment can see and own it. The manifest records class shapes, not methods, so this reshape is recorded as a behavior entry.
- Migration: build the ambient identity at the call site — `door.serve_stdio(identity=AuthenticatedUser(ambient_stdio_identity(credential=..., principal_id=..., scope=..., tenant=...)))` — as the committed examples' `server/serve.py` files now do. A deployment serving more than one principal uses `serve_loopback`.

## ccf_runtime.mcp.product_door.StdioIdentityRequired

- Surface: ccf_runtime.mcp.product_door.StdioIdentityRequired
- Public surface: true
- Change type: added
- Before: absent
- After: `class StdioIdentityRequired(ValueError)`, raised by `ProductDoor.serve_stdio` when no caller-composed `AuthenticatedUser` is passed (`EX-03`/`EX-04`, `D-IMPL-361` §7.3); exported in `ccf_runtime.mcp.product_door.__all__` (M-1)
- Why: a typed refusal naming the ruling rather than an anonymous `TypeError`. A public method raises it and the security page names it, so it is public surface.
- Migration: none; catch it by class if a deployment wants to report the omission specially

## ccf_runtime.adapters.claude_agent.adapter.PromptFileRefused

- Surface: ccf_runtime.adapters.claude_agent.adapter.PromptFileRefused
- Public surface: true
- Change type: added
- Before: absent — `transport(carrier)` admitted a prompt file of any kind, owner or mode, or none at all
- After: `class PromptFileRefused(ValueError)`, raised by `ClaudeAgentAdapter.transport` before anything connects when the carrier's system prompt is not the adapter's file form, or the file is missing, not a regular file, not owned by the effective uid or not `0600`, or its directory is not a directory owned by the effective uid with mode `0700` (`TP-05`, I-3, `D-IMPL-361`)
- Why: the prompt directory's name is published on every child's argv; after `remove_prompt_directories()` another local user could recreate it and author the system prompt of an agent holding governed skills
- Migration: none for a carrier built by `inject_context` and used before `remove_prompt_directories()`; build a new carrier rather than reusing one whose directory was removed
