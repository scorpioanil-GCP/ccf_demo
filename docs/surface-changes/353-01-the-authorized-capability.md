# 353-01 — the `Authorized` capability, where it lives, and the CLI's typed authority bundle

`D-IMPL-353` (design accepted 2026-09-24; `docs/D-IMPL-353-DESIGN.md`) closes the
root cause the security review of 2026-09-23 put under `SEC-001`: authorization was
optional by construction. The remedy is a capability in the shape of
`StateWriteToken` — a handle takes an `Authorized[Kind]` it cannot build, so
unauthorized work is unrepresentable rather than "missed a check".

## What did NOT change, stated first

- **No action id changed value.** The 27 `ACTION_*` strings are the same strings;
  `ccf_runtime.authz.refusals` still exports every one of them as a named
  re-export. A caller that imports them from there is unchanged.
- **`AuthzDecision` is the same contract**, re-exported from
  `ccf_runtime.authz.protocol` where it has always been importable.
- **No handle signature changes are recorded here.** The registry, state, artifact,
  engine, HITL and MCP handle changes land with their own lanes' fragments; this
  fragment records the capability itself, its move into `src/`, and the CLI bundle.

## Why two spellings of one capability

The capability was cut at `934a4ce9` in `ccf_runtime.authz.capability`. The handles
that must take it live in `src/` (`ccf.controlplane`, `ccf.artifacts`, the workflow
state) and `src` may not import `runtime` (`D-29`, 12 controls in
`tests/invariants/test_src_does_not_import_runtime.py::test_no_module_under_src_imports_the_runtime_package`). So at `a3388601` the
definitions moved to `src/ccf/authz/` and the runtime module became an explicit
named re-export (`from ccf.authz.capability import N as N`). Both spellings name
the same objects; the §4 lint's `d353-authz-mint-site` rule resolves either
spelling to the definer and treats the shim as a mint site in neither.

## ccf.authz.actions.ACTION_AGENT_DECLARE

- Surface: ccf.authz.actions.ACTION_AGENT_DECLARE
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_AGENT_DECLARE`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_AGENT_DECLARE` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_AGENT_LIST

- Surface: ccf.authz.actions.ACTION_AGENT_LIST
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_AGENT_LIST`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_AGENT_LIST` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_AGENT_READ

- Surface: ccf.authz.actions.ACTION_AGENT_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_AGENT_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_AGENT_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_AGENT_VERSIONS

- Surface: ccf.authz.actions.ACTION_AGENT_VERSIONS
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_AGENT_VERSIONS`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_AGENT_VERSIONS` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_ARTIFACT_READ

- Surface: ccf.authz.actions.ACTION_ARTIFACT_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_ARTIFACT_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_ARTIFACT_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_ARTIFACT_WRITE

- Surface: ccf.authz.actions.ACTION_ARTIFACT_WRITE
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_ARTIFACT_WRITE`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_ARTIFACT_WRITE` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_BACKENDS_READ

- Surface: ccf.authz.actions.ACTION_BACKENDS_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_BACKENDS_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_BACKENDS_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_CONFIG_KEYS_READ

- Surface: ccf.authz.actions.ACTION_CONFIG_KEYS_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_CONFIG_KEYS_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_CONFIG_KEYS_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_CONFIG_REGISTER

- Surface: ccf.authz.actions.ACTION_CONFIG_REGISTER
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_CONFIG_REGISTER`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_CONFIG_REGISTER` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_CONFIG_RESOLVE

- Surface: ccf.authz.actions.ACTION_CONFIG_RESOLVE
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_CONFIG_RESOLVE`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_CONFIG_RESOLVE` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_CONFIG_VERSIONS_READ

- Surface: ccf.authz.actions.ACTION_CONFIG_VERSIONS_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_CONFIG_VERSIONS_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_CONFIG_VERSIONS_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_DOCS_READ

- Surface: ccf.authz.actions.ACTION_DOCS_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_DOCS_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_DOCS_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_HEALTH_READ

- Surface: ccf.authz.actions.ACTION_HEALTH_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_HEALTH_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_HEALTH_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_HITL_ACTION_SUBMIT

- Surface: ccf.authz.actions.ACTION_HITL_ACTION_SUBMIT
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_HITL_ACTION_SUBMIT`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_HITL_ACTION_SUBMIT` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_HITL_QUEUE_READ

- Surface: ccf.authz.actions.ACTION_HITL_QUEUE_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_HITL_QUEUE_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_HITL_QUEUE_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_OPENAPI_READ

- Surface: ccf.authz.actions.ACTION_OPENAPI_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_OPENAPI_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_OPENAPI_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_PRODUCT_RETRIEVE

- Surface: ccf.authz.actions.ACTION_PRODUCT_RETRIEVE
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_PRODUCT_RETRIEVE`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_PRODUCT_RETRIEVE` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_REPLAY_READ

- Surface: ccf.authz.actions.ACTION_REPLAY_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_REPLAY_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_REPLAY_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_SCHEMA_LIST

- Surface: ccf.authz.actions.ACTION_SCHEMA_LIST
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_SCHEMA_LIST`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_SCHEMA_LIST` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_SCHEMA_READ

- Surface: ccf.authz.actions.ACTION_SCHEMA_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_SCHEMA_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_SCHEMA_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_SKILL_CATALOG_READ

- Surface: ccf.authz.actions.ACTION_SKILL_CATALOG_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_SKILL_CATALOG_REGISTER

- Surface: ccf.authz.actions.ACTION_SKILL_CATALOG_REGISTER
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_REGISTER`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_REGISTER` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_SKILL_GRANT

- Surface: ccf.authz.actions.ACTION_SKILL_GRANT
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_SKILL_GRANT`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_SKILL_GRANT` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_SKILL_REVOKE

- Surface: ccf.authz.actions.ACTION_SKILL_REVOKE
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_SKILL_REVOKE`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_SKILL_REVOKE` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_WORKFLOW_INVOKE

- Surface: ccf.authz.actions.ACTION_WORKFLOW_INVOKE
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_WORKFLOW_INVOKE`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_WORKFLOW_INVOKE` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_WORKFLOW_RESUME

- Surface: ccf.authz.actions.ACTION_WORKFLOW_RESUME
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_WORKFLOW_RESUME`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_WORKFLOW_RESUME` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.actions.ACTION_WORKFLOW_STATUS_READ

- Surface: ccf.authz.actions.ACTION_WORKFLOW_STATUS_READ
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.refusals.ACTION_WORKFLOW_STATUS_READ`
- After: the definition; `ccf_runtime.authz.refusals.ACTION_WORKFLOW_STATUS_READ` is a named re-export of it with the same string value
- Why: `D-29` — `src` handles must resolve action ids without importing `runtime`; the capability's `kind_for_action` maps these ids to kinds
- Migration: none; new `src` code imports from `ccf.authz.actions`, runtime code may keep the old spelling

## ccf.authz.capability.ActionKind

- Surface: ccf.authz.capability.ActionKind
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: the closed vocabulary's base: every action id is a subclass, never an instance (`__new__` refuses), so a kind is a type mypy can carry
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.AgentDeclare

- Surface: ccf.authz.capability.AgentDeclare
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `agent.declare` — the static tag `Authorized[AgentDeclare]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.AgentList

- Surface: ccf.authz.capability.AgentList
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `agent.list` — the static tag `Authorized[AgentList]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.AgentRead

- Surface: ccf.authz.capability.AgentRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `agent.read` — the static tag `Authorized[AgentRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.AgentVersions

- Surface: ccf.authz.capability.AgentVersions
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `agent.versions` — the static tag `Authorized[AgentVersions]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ArtifactRead

- Surface: ccf.authz.capability.ArtifactRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `artifact.read` — the static tag `Authorized[ArtifactRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ArtifactWrite

- Surface: ccf.authz.capability.ArtifactWrite
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `artifact.write` — the static tag `Authorized[ArtifactWrite]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.Authorized

- Surface: ccf.authz.capability.Authorized
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: the capability — not constructible outside `mint`; generic over its kind; every field frozen; a `_minted` tuple binds kind, tenant, principal, resource and decision id together
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.BackendsRead

- Surface: ccf.authz.capability.BackendsRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `backends.read` — the static tag `Authorized[BackendsRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.CapabilityBypassError

- Surface: ccf.authz.capability.CapabilityBypassError
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: raised when something other than `mint` tries to build or alter an `Authorized`
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ConfigKeysRead

- Surface: ccf.authz.capability.ConfigKeysRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `config.keys.read` — the static tag `Authorized[ConfigKeysRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ConfigRegister

- Surface: ccf.authz.capability.ConfigRegister
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `config.register` — the static tag `Authorized[ConfigRegister]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ConfigResolve

- Surface: ccf.authz.capability.ConfigResolve
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `config.resolve` — the static tag `Authorized[ConfigResolve]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ConfigVersionsRead

- Surface: ccf.authz.capability.ConfigVersionsRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `config.versions.read` — the static tag `Authorized[ConfigVersionsRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.DocsRead

- Surface: ccf.authz.capability.DocsRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `docs.read` — the static tag `Authorized[DocsRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.Execute

- Surface: ccf.authz.capability.Execute
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `workflow.invoke` — the static tag `Authorized[Execute]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.GrantMutate

- Surface: ccf.authz.capability.GrantMutate
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: alias of `SkillGrant` — the grant ledger's kind
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.HealthRead

- Surface: ccf.authz.capability.HealthRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `health.read` — the static tag `Authorized[HealthRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.HitlQueueRead

- Surface: ccf.authz.capability.HitlQueueRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `hitl.queue.read` — the static tag `Authorized[HitlQueueRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.HitlSubmit

- Surface: ccf.authz.capability.HitlSubmit
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `hitl.action.submit` — the static tag `Authorized[HitlSubmit]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.OpenApiRead

- Surface: ccf.authz.capability.OpenApiRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `openapi.read` — the static tag `Authorized[OpenApiRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ProductRetrieve

- Surface: ccf.authz.capability.ProductRetrieve
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `product.retrieve` — the static tag `Authorized[ProductRetrieve]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.Register

- Surface: ccf.authz.capability.Register
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: alias of `ConfigRegister` — the registry handle's kind
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ReplayMint

- Surface: ccf.authz.capability.ReplayMint
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: the composition-root kind; no `ACTION_*` string reaches it
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.ReplayRead

- Surface: ccf.authz.capability.ReplayRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `replay.read` — the static tag `Authorized[ReplayRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.Resume

- Surface: ccf.authz.capability.Resume
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `workflow.resume` — the static tag `Authorized[Resume]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.SchemaList

- Surface: ccf.authz.capability.SchemaList
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `schema.list` — the static tag `Authorized[SchemaList]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.SchemaRead

- Surface: ccf.authz.capability.SchemaRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `schema.read` — the static tag `Authorized[SchemaRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.SkillCatalogRead

- Surface: ccf.authz.capability.SkillCatalogRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `skill.catalog.read` — the static tag `Authorized[SkillCatalogRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.SkillCatalogRegister

- Surface: ccf.authz.capability.SkillCatalogRegister
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `skill.catalog.register` — the static tag `Authorized[SkillCatalogRegister]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.SkillGrant

- Surface: ccf.authz.capability.SkillGrant
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `skill.grant` — the static tag `Authorized[SkillGrant]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.SkillRevoke

- Surface: ccf.authz.capability.SkillRevoke
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `skill.revoke` — the static tag `Authorized[SkillRevoke]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.WorkflowStatusRead

- Surface: ccf.authz.capability.WorkflowStatusRead
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: `ActionKind` for action id `workflow.status.read` — the static tag `Authorized[WorkflowStatusRead]` carries
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.kind_for_action

- Surface: ccf.authz.capability.kind_for_action
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: action id → kind; refuses `replay.mint` by name so a wire-supplied action can never mint the composition-root kind
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.mint

- Surface: ccf.authz.capability.mint
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: the ONE constructor: takes an allowed `AuthzDecision` and refuses a kind that is not the decision's action's kind
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.mint_at_composition

- Surface: ccf.authz.capability.mint_at_composition
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: the composition root's mint for `ReplayMint` only — the replay writer's authority, issued once where the deployment is composed
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.capability.verify

- Surface: ccf.authz.capability.verify
- Public surface: true
- Change type: added
- Before: absent — authorization was a per-site check a caller could skip
- After: the runtime tooth every handle calls: mint identity, current fields against the minted tuple, kind by identity, resource by equality
- Why: `D-IMPL-353` §1: a handle that requires an `Authorized[Kind]` cannot be reached with authorization missing; two teeth — `mypy --strict` on the kind, `verify` at use
- Migration: handles take `Authorized[...]` from the HTTP gate or the MCP wrapper (the only mint sites); nothing else constructs one

## ccf.authz.decision.AuthzDecision

- Surface: ccf.authz.decision.AuthzDecision
- Public surface: true
- Change type: added
- Before: the definition lived in `ccf_runtime.authz.protocol.AuthzDecision`
- After: the definition; `ccf_runtime.authz.protocol.AuthzDecision` is a named re-export of it
- Why: `mint` takes an `AuthzDecision` and lives in `src/` (`D-29`)
- Migration: none

## ccf_runtime.authz.capability.ActionKind

- Surface: ccf_runtime.authz.capability.ActionKind
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ActionKind` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.AgentDeclare

- Surface: ccf_runtime.authz.capability.AgentDeclare
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.AgentDeclare` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.AgentList

- Surface: ccf_runtime.authz.capability.AgentList
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.AgentList` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.AgentRead

- Surface: ccf_runtime.authz.capability.AgentRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.AgentRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.AgentVersions

- Surface: ccf_runtime.authz.capability.AgentVersions
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.AgentVersions` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ArtifactRead

- Surface: ccf_runtime.authz.capability.ArtifactRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ArtifactRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ArtifactWrite

- Surface: ccf_runtime.authz.capability.ArtifactWrite
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ArtifactWrite` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.Authorized

- Surface: ccf_runtime.authz.capability.Authorized
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.Authorized` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.BackendsRead

- Surface: ccf_runtime.authz.capability.BackendsRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.BackendsRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.CapabilityBypassError

- Surface: ccf_runtime.authz.capability.CapabilityBypassError
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.CapabilityBypassError` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ConfigKeysRead

- Surface: ccf_runtime.authz.capability.ConfigKeysRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ConfigKeysRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ConfigRegister

- Surface: ccf_runtime.authz.capability.ConfigRegister
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ConfigRegister` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ConfigResolve

- Surface: ccf_runtime.authz.capability.ConfigResolve
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ConfigResolve` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ConfigVersionsRead

- Surface: ccf_runtime.authz.capability.ConfigVersionsRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ConfigVersionsRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.DocsRead

- Surface: ccf_runtime.authz.capability.DocsRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.DocsRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.Execute

- Surface: ccf_runtime.authz.capability.Execute
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.Execute` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.GrantMutate

- Surface: ccf_runtime.authz.capability.GrantMutate
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.GrantMutate` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.HealthRead

- Surface: ccf_runtime.authz.capability.HealthRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.HealthRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.HitlQueueRead

- Surface: ccf_runtime.authz.capability.HitlQueueRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.HitlQueueRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.HitlSubmit

- Surface: ccf_runtime.authz.capability.HitlSubmit
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.HitlSubmit` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.OpenApiRead

- Surface: ccf_runtime.authz.capability.OpenApiRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.OpenApiRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ProductRetrieve

- Surface: ccf_runtime.authz.capability.ProductRetrieve
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ProductRetrieve` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.Register

- Surface: ccf_runtime.authz.capability.Register
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.Register` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ReplayMint

- Surface: ccf_runtime.authz.capability.ReplayMint
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ReplayMint` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.ReplayRead

- Surface: ccf_runtime.authz.capability.ReplayRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.ReplayRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.Resume

- Surface: ccf_runtime.authz.capability.Resume
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.Resume` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.SchemaList

- Surface: ccf_runtime.authz.capability.SchemaList
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.SchemaList` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.SchemaRead

- Surface: ccf_runtime.authz.capability.SchemaRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.SchemaRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.SkillCatalogRead

- Surface: ccf_runtime.authz.capability.SkillCatalogRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.SkillCatalogRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.SkillCatalogRegister

- Surface: ccf_runtime.authz.capability.SkillCatalogRegister
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.SkillCatalogRegister` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.SkillGrant

- Surface: ccf_runtime.authz.capability.SkillGrant
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.SkillGrant` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.SkillRevoke

- Surface: ccf_runtime.authz.capability.SkillRevoke
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.SkillRevoke` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.WorkflowStatusRead

- Surface: ccf_runtime.authz.capability.WorkflowStatusRead
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.WorkflowStatusRead` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.kind_for_action

- Surface: ccf_runtime.authz.capability.kind_for_action
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.kind_for_action` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.mint

- Surface: ccf_runtime.authz.capability.mint
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.mint` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.mint_at_composition

- Surface: ccf_runtime.authz.capability.mint_at_composition
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.mint_at_composition` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.authz.capability.verify

- Surface: ccf_runtime.authz.capability.verify
- Public surface: true
- Change type: added
- Before: absent at `d895d889`; the definition from `934a4ce9` to `a605661f`
- After: a named re-export of `ccf.authz.capability.verify` — the definition moved to `src/` at `a3388601`
- Why: runtime callers (HTTP gate, MCP wrapper, engine, CLI) reach the capability through the runtime package while `src` handles require it without importing `runtime` (`D-29`)
- Migration: none; either spelling names the same object, and the lint treats this module as a mint site in neither

## ccf_runtime.http_api.app.HttpAuthority

- Surface: ccf_runtime.http_api.app.HttpAuthority
- Public surface: true
- Change type: added
- Before: the CLI's in-process leg took `authority: Mapping[str, object] | None` and passed it to `create_app` behind `# type: ignore[arg-type]`
- After: a `TypedDict` naming exactly `create_app`'s five required keyword seams (`auth`, `authorizer`, `product_entitlement`, `perspective_resolver`, `refusal_recorder`); `main(authority=)` takes it and the ignore is gone
- Why: `D-IMPL-353` §4 rule 6 (`d353-authz-type-ignore`): an untyped authority bag forced past the type checker is the shape the lint refuses; `tests/cli/test_authority_bundle.py::test_the_bundle_names_exactly_create_apps_keyword_seams` holds the bundle's keys and types equal to `create_app`'s so they cannot drift
- Migration: an embedder calling `main(dependencies=..., authority=...)` supplies an `HttpAuthority`; an incomplete bundle is a mypy error where it is written

