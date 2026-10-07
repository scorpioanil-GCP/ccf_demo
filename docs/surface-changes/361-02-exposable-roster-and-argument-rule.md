# 361-02 — one harness-exposable roster, and one argument rule at the fabric seam

`D-IMPL-361`, the v1.0.2 adapter findings. This fragment covers `TP-03` (only
`tool`, `mcp` and `local_callable` skills render as harness tools, on every
leg and in the experience listing) and `TP-04` with `SEC353-J-01` (an
undeclared wire argument is refused, never dropped, on ADK and at every
FastMCP door; and `Agent.invoke_skill` refuses undeclared, missing and
mistyped arguments before dispatch on every leg).

## ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES

- Surface: ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES
- Public surface: true
- Change type: added
- Before: absent — each adapter rendered every bound skill except `procedure`
- After: `frozenset[str] = frozenset({"tool", "mcp", "local_callable"})`, the skill types that have a harness tool surface (`TP-03`, `D-IMPL-361`)
- Why: a `peering` or `mcp_product` skill rendered as a harness tool lets the model call a peer directly, receive products nothing admitted, and drain the queue the admission gate reads (CLAUDE.md §7.2); a bound `procedure` crashed `_tools()` on every leg. The roster is SDK skill-type names, so it is mechanism.
- Migration: none; new name. An adopter rendering its own harness tools filters the agent's bound entries by this roster.

## ccf.skills.toolsurface.SkillHasNoToolSurface

- Surface: ccf.skills.toolsurface.SkillHasNoToolSurface
- Public surface: true
- Change type: added
- Before: absent — only `ProcedureHasNoToolSurface` existed
- After: `class SkillHasNoToolSurface(ValueError)`, raised by `render_tool_surface` for every skill type outside `HARNESS_EXPOSABLE_SKILL_TYPES`; `ProcedureHasNoToolSurface` is now its subclass (`TP-03`, `D-IMPL-361`)
- Why: the derivation's own floor for the roster; the subclass relation keeps every existing catch of `ProcedureHasNoToolSurface` holding
- Migration: none; catch `SkillHasNoToolSurface` to cover every non-exposable type

## ccf.skills.toolsurface.render_tool_surface

- Surface: ccf.skills.toolsurface.render_tool_surface
- Public surface: true
- Change type: behavior
- Before: refused `procedure` only; a `peering` or `mcp_product` entry rendered as a tool
- After: refuses every type outside `HARNESS_EXPOSABLE_SKILL_TYPES` with `SkillHasNoToolSurface` (`ProcedureHasNoToolSurface` for `procedure`, as before) (`TP-03`, `D-IMPL-361`)
- Why: see `ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`
- Migration: a caller rendering a `peering` or `mcp_product` entry now receives a refusal; filter by the roster first

## ccf_runtime.adapters.adk.adapter.AdkAdapter.expose_skills

- Surface: ccf_runtime.adapters.adk.adapter.AdkAdapter.expose_skills
- Public surface: true
- Change type: behavior
- Before: `_tools()` rendered every bound skill, so `peering` and `mcp_product` skills became harness tools and a bound `procedure` raised; ADK's stock `run_async` filtered the model's arguments to the callable's signature, so every declared argument was dropped, an undeclared one was dropped silently, and every value was stringified
- After: only skills whose type is in `HARNESS_EXPOSABLE_SKILL_TYPES` are rendered; the others are skipped, never raised on (`TP-03`). The tool receives ADK's raw arguments, refuses an undeclared key, and hands the rest to `invoke_skill` unstringified; every `ArgumentRefused` renders as the adapter's typed `EffectRefusal` (`TP-04`, `D-IMPL-361`). **Disclosed behavior change:** a number sent for a `string`-declared argument is now refused as mistyped, where before it was stringified and dispatched.
- Why: `TP-03` and `TP-04`, one rule on every leg
- Migration: a model that sends a number for a declared `string` argument is now refused; declare the argument's real JSON type in the skill's `argument_schema`

## ccf_runtime.adapters.langgraph.adapter.LangGraphAdapter.expose_skills

- Surface: ccf_runtime.adapters.langgraph.adapter.LangGraphAdapter.expose_skills
- Public surface: true
- Change type: behavior
- Before: the `ToolNode` rendered every bound skill (`peering` and `mcp_product` as tools; a bound `procedure` raised), and each tool stringified every argument before `invoke_skill`, so an undeclared key, a missing required argument and a wrong-typed value were dispatched and audited
- After: only exposable skill types are rendered (`TP-03`); arguments reach `invoke_skill` as they arrived and the seam's `ArgumentRefused` propagates from the tool call, fail-closed (`TP-04` follow-on, `D-IMPL-361`). **Disclosed behavior change:** a number sent for a `string`-declared argument is now refused, where before it was stringified and dispatched.
- Why: `TP-03` and `TP-04`, one rule on every leg
- Migration: as for `ccf_runtime.adapters.adk.adapter.AdkAdapter.expose_skills`

## ccf_runtime.mcp.experience.agent_tool_listing

- Surface: ccf_runtime.mcp.experience.agent_tool_listing
- Public surface: true
- Change type: behavior
- Before: omitted `procedure` skills and raised on a bound `peering` or `mcp_product` skill
- After: lists only skills whose type is in `HARNESS_EXPOSABLE_SKILL_TYPES`; the rest are omitted, never raised on (`TP-03`, `D-IMPL-361`)
- Why: the experience listing reads the same roster every adapter filters by
- Migration: none

## ccf.skills.wire_arguments.ArgumentRefused

- Surface: ccf.skills.wire_arguments.ArgumentRefused
- Public surface: true
- Change type: added
- Before: absent — the module `ccf.skills.wire_arguments` did not exist
- After: `class ArgumentRefused(Exception)`, the base of every argument refusal; carries the undeclared, missing and mistyped names in full. Deliberately not a `ValueError`, so pydantic does not re-type it on the FastMCP leg (`TP-04`, `SEC353-J-01`, `D-IMPL-361`)
- Why: one defect class, one rule, one refusal family across ADK, LangGraph, the Claude handler, `Agent.invoke_skill` and every FastMCP door
- Migration: none; new name. Catch it to handle every argument refusal.

## ccf.skills.wire_arguments.UndeclaredArgumentRefused

- Surface: ccf.skills.wire_arguments.UndeclaredArgumentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the `ArgumentRefused` raised when the first category present is an argument the declared schema does not name (`TP-04`, `D-IMPL-361`)
- Why: an undeclared argument is refused by name, never dropped
- Migration: none; new name

## ccf.skills.wire_arguments.MissingArgumentRefused

- Surface: ccf.skills.wire_arguments.MissingArgumentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the `ArgumentRefused` raised when the first category present is a required argument that is absent (`TP-04` follow-on, `D-IMPL-361`)
- Why: a missing required argument was dispatched and audited on every leg
- Migration: none; new name

## ccf.skills.wire_arguments.MistypedArgumentRefused

- Surface: ccf.skills.wire_arguments.MistypedArgumentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the `ArgumentRefused` raised when the first category present is a value whose JSON type is not the declared `type` (`TP-04` follow-on, `D-IMPL-361`)
- Why: values were stringified, never checked, so a wrong-typed value was dispatched and audited
- Migration: none; new name

## ccf.skills.wire_arguments.refuse_unconforming_arguments

- Surface: ccf.skills.wire_arguments.refuse_unconforming_arguments
- Public surface: true
- Change type: added
- Before: absent
- After: validates a presented argument mapping against a `SkillArgumentSchema` — undeclared, missing and mistyped, recursing into the one level of declared object members and array elements — and raises the matching `ArgumentRefused` naming each violation by path (`TP-04` follow-on, `D-IMPL-361`)
- Why: the whole argument rule, enforced once, at the seam every harness leg crosses
- Migration: none; new name

## ccf.skills.wire_arguments.refuse_undeclared_arguments

- Surface: ccf.skills.wire_arguments.refuse_undeclared_arguments
- Public surface: true
- Change type: added
- Before: absent
- After: raises `UndeclaredArgumentRefused` for any key outside a declared name set; the rule the ADK tool and the FastMCP guard run over the raw wire mapping (`TP-04`, `SEC353-J-01`, `D-IMPL-361`)
- Why: the early, schema-free half of the rule, for the two doors that hold a declared name set before an entry
- Migration: none; new name. The private `ccf.skills._wire_arguments` re-exports it under its first name.

## ccf.skills.wire_arguments.undeclared_arguments

- Surface: ccf.skills.wire_arguments.undeclared_arguments
- Public surface: true
- Change type: added
- Before: absent
- After: returns the presented keys outside a declared name set, sorted, without raising (`TP-04`, `D-IMPL-361`)
- Why: the measurement the refusal is built on, exposed for callers that report rather than refuse
- Migration: none; new name

## ccf.agents.agent.Agent.invoke_skill

- Surface: ccf.agents.agent.Agent.invoke_skill
- Public surface: true
- Change type: behavior
- Before: `invoke_skill(name, *, arguments: Mapping[str, str] | None = None)`; the presented arguments were dispatched and audited without being checked against the bound entry's declared `argument_schema`
- After: `invoke_skill(name, *, arguments: Mapping[str, object] | None = None)`. Before anything is dispatched or audited, the arguments are validated with `refuse_unconforming_arguments`: an undeclared key, a missing required argument, or a value not of the declared JSON type is refused by name with the `ArgumentRefused` family. Conforming values are carried to dispatch as `str` of each value, the encoding the adapters applied before (`TP-04` follow-on, `D-IMPL-361`)
- Why: every harness leg crosses this seam, so the rule enforced here holds on every leg. The manifest records class shapes, not method signatures, so the widened parameter type is recorded in this behavior entry.
- Migration: hand `invoke_skill` arguments as they arrived, typed — never pre-stringified, which would erase the type the rule checks; a caller that sent an undeclared, missing or mistyped argument now receives an `ArgumentRefused` and nothing is dispatched

## ccf_runtime.mcp.tenancy.TenantGuardedServer.tool

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer.tool
- Public surface: true
- Change type: behavior
- Before: FastMCP's per-tool argument model ignored extra keys, so an undeclared wire argument was silently dropped and the call served as a different question
- After: every guarded tool is closed over its declared arguments: an undeclared wire argument is refused with `UndeclaredArgumentRefused` naming the key, before the guard or the body runs, and the advertised `inputSchema` carries `additionalProperties: false` (`SEC353-J-01`, ruled with `TP-04` at `D-IMPL-361`)
- Why: what a tool advertises is what it enforces; an undeclared argument is refused, never dropped
- Migration: an MCP client that sent extra keys now receives a tool error naming them; send only the declared arguments
