# 378-35 (C2-A2) — the door's two address names are optional in the environment document

`D-IMPL-378` C2-A2, ruled (a) by Dave on 2026-10-08 at 12:29 MST: make both names optional. Built in
lane 378e-small.

After C2-A (b) (fragment 378-27) no SDK transport reads the environment document's `door.issuer_url` or
`door.resource_server_url`: the stdio transport supplies reserved `.invalid` values, the loopback transport
advertises its own bound address, and a deployment that mounts `ProductDoor.server` under its own host
passes both values itself. `src/ccf/deployment/environment.py::DoorEnvironment` still required every
deployment to declare both names, which is configuration nothing reads.

**What was measured before the change** (red tests, committed first): a `door:` block naming only the
credential was refused `Field required` for both names; a stdio door spawned from such a document never
started; and the block could not be built in process.

**Every SDK reader of the two names, measured.** `git grep -n "issuer_url\|resource_server_url" -- src
runtime` finds only `DoorEnvironment`'s own declaration and docstrings, and `ProductDoor.server`'s two
keyword parameters with the stdio and loopback values passed to them. The one SDK code that reads the
`door:` block, `runtime/ccf_runtime/mcp/product_door.py::_boot_credential`, reads `credential` only. No
path reads either name, so none can be left to default silently. The self-hosted mount takes values, not
names: `ProductDoor.server` has no default for either, refuses a call that omits them with a `TypeError`
naming both parameters, and refuses `None` (`tests/mcp/test_stdio_door_addresses.py::test_a_door_composes_over_a_door_block_naming_only_the_credential`).

**What holds now**: `tests/deployment/test_door_environment_optional_addresses.py` and the two C2-A2 tests
in `tests/mcp/test_stdio_door_addresses.py`. A document whose `door:` block names only the credential
loads, and both names read as absent. A door composes over it and reads its credential. A stdio door
spawned from it starts, answers, and still refuses another tenant and a class outside its scope mapping.

**Existing documents are unaffected.** A document naming all three loads with exactly the names and
remedies it declares (control). The environment document is never content-hashed or registered, so no
content address, pin or record changes. All 21 committed `ccf_environment.yaml` documents load after the
change; the 15 with a `door:` block all declare both names and keep them.

**Also changed:** the refusal `open_door` raises when the environment document names no `door:` block at
all now says the credential is read from that block and the two address names are optional. Before, it
said the issuer and resource-server addresses are read by the names declared there, which C2-A (b) had
already made untrue. No committed JSON Schema covers the environment document, so `make schemas` has
nothing to regenerate.

## ccf.deployment.environment.DoorEnvironment

- Surface: ccf.deployment.environment.DoorEnvironment
- Public surface: true
- Change type: reshaped
- Before: three required members, `credential`, `issuer_url` and `resource_server_url`, each an `EnvironmentValue`
- After: `credential` required; `issuer_url` and `resource_server_url` are `EnvironmentValue | None`, defaulting to `None` (hash-transparent, `D-IMPL-243`)
- Why: `D-IMPL-378` C2-A2 (a): no SDK transport reads either name, and configuration nothing reads is not required. Red tests: `tests/deployment/test_door_environment_optional_addresses.py::test_an_environment_document_whose_door_names_only_the_credential_loads`, `tests/mcp/test_stdio_door_addresses.py::test_a_stdio_door_whose_document_names_neither_address_starts_answers_and_still_refuses`, `::test_a_door_composes_over_a_door_block_naming_only_the_credential`
- Migration: none; a document declaring both names loads unchanged. A deployment may drop the two names unless its own code reads them; code that read `door.issuer_url` or `door.resource_server_url` must now handle `None`
