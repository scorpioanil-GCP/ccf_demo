# 378-01 — a refused read is bound to the tenant and the principal that asked

The forged-record re-review of the `D-IMPL-376` close-out measured, and
`377-07` disclosed: the governed evidence read recorded each refused read
through the door's recorder, and the read-refusal record named the door
RECORDER's tenant whichever tenant the refused capability named. On a door
that serves several tenants through one recorder — the MCP artifact server is
built that way, and so is an HTTP app whose authorizer admits several
tenants — tenant B's refused read was attributed to tenant A, so tenant A's
principal holding B's principal's client id passed hold 0 and hold 1 on B's
record and read the address B had asked for. Dave's ruling (2026-10-07,
`D-IMPL-378`, "Fix now"): *"Authorization must bind the requesting tenant and
principal together; a colliding principal id in the door's tenant must not
reveal another tenant's requested address. Check existing records too."*

The adjacent sweep found the same defect in every disclosure-level lookup
keyed by a principal id under the recorder's tenant, and each is bound here
with its own red test and executed severing: the governed read's hold 3, the
level the door's recorder discloses a refusal shell at, and the level that
picks the Experience door's answer to an erasure.

**Not changed, and owed to Dave.** A read-refusal record minted before this
change still names the recorder's tenant, whichever tenant asked. It is
byte-for-byte the record this change mints for the recorder's own tenant's
principal asking the same reference at the same instant
(`tests/mcp/test_read_refusal_attribution_mcp.py::test_a_record_written_before_the_binding_is_byte_for_byte_one_the_door_writes_today`),
so no rule over a record's content can refuse one to that principal and serve
it the other: on a door that served several tenants through one recorder, such
a record still reads for the colliding principal of the recorder's tenant
(recorded as a strict expected failure). Failing those records closed needs a
positive marker on new read-refusal records, or no read-refusal record readable
through the governed read at all (`D-IMPL-345` R-2 keeps a principal's own
chain readable); either is a ruling.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: a read-refusal record's resource identity named the door recorder's tenant (`refusal_recorder.tenant_id`) whichever tenant the refused capability named, so holds 0 and 1 attributed another tenant's refused read to the recorder's tenant and served it to a principal of that tenant with the same client id. Hold 3 read the disclosure level through the door's recorder under the recorder's own tenant, for the caller's principal id.
- After: a read-refusal record names `authorized.tenant` — the tenant the refused capability was verified for — beside the principal dimension 4 records, so holds 0 and 1 hold a later reader to that pair. Such a record decided under one tenant and filed by a recorder of another is served to nobody by the provenance check, which is unchanged; its own principal reads it back only through a door whose recorder is its own tenant's, as before (hold 0 refused it then). Hold 3 reads the level through the door's recorder for `authorized.tenant` and the principal together — after hold 0, the tenant the record was decided under. On a door whose callers are all of the recorder's tenant, a read-refusal record is byte-for-byte what it was and hold 3 reads the same level. Every caller inherits it: HTTP `/replay/decisions`, `/replay/resolutions` and `/artifact`, and the MCP artifact server's governed reads.
- Why: Dave, 2026-10-07 (`D-IMPL-378`). Red tests: `tests/mcp/test_read_refusal_attribution_mcp.py::test_another_tenants_read_refusal_record_answers_a_colliding_principal_as_a_missing_address_does`, `::test_a_read_refusal_record_binds_the_tenant_and_principal_the_refused_capability_named` and `::test_hold_three_reads_the_level_in_force_for_the_requesting_tenant_not_the_recorders`; `tests/http_api/test_read_refusal_attribution_http.py::test_another_tenants_read_refusal_record_answers_a_colliding_principal_as_a_missing_address_does` (all three routes) and `::test_hold_three_reads_the_level_in_force_for_the_requesting_tenant_not_the_recorders`.
- Migration: none where every caller of a door is of its recorder's tenant. Read-refusal records minted before this change are not rewritten and still replay to their own addresses (`tests/mcp/test_read_refusal_attribution_mcp.py::test_read_refusal_records_from_before_and_after_the_binding_replay_to_their_own_addresses`); on a door that served several tenants through one recorder, such a record still reads for a principal of the recorder's tenant with the same client id as the principal it names — keep client ids distinct across tenants that share a door, or give each tenant its own door and recorder. A principal of a tenant other than the recorder's never reads its own read refusals back through that door, before or after this change. A deployment-supplied recorder's `disclosure_level_for` is now asked for the capability's tenant at hold 3.

## ccf.products.resolver.ReplayRefusalRecorder

- Surface: ccf.products.resolver.ReplayRefusalRecorder
- Public surface: true
- Change type: behavior
- Before: `record` read the level it discloses a refusal shell at under the recorder's own tenant (`self.tenant_id`) for the perspective's principal. On a door serving several tenants through one recorder, another tenant's caller was disclosed at the level the recorder's tenant declares for a principal with the same client id: measured, a caller at `minimal` in its own tenant received `full` shells, telling a missing address from another of its own tenant's principals' records, and a caller at `full` received `minimal` ones.
- After: `record` reads the level under the tenant the determination was made under — the tenant a delivery-boundary determination's resource identity names, which its door established (`govern_entitlement`, `govern_absence`, `govern_erasure`, `govern_raised_refusal`'s door-built envelope, `govern_dereference`) — and under the recorder's own tenant for a determination that names none (a resolver's own refusal), for the perspective's principal. The recorded `DisclosureDecision` names that tenant's policy. Every site in `src/`, `runtime/` and `examples/` that builds a `ResourceRequestIdentity` is one of those governed steps.
- Why: Dave, 2026-10-07 (`D-IMPL-378`), the adjacent sweep. Red tests: `tests/mcp/test_read_refusal_attribution_mcp.py::test_a_refusal_of_another_tenants_principal_is_disclosed_at_its_own_level_not_the_recorders` and `tests/http_api/test_read_refusal_attribution_http.py::test_a_refusal_of_another_tenants_principal_is_disclosed_at_its_own_level_not_the_recorders`.
- Migration: none where every caller of a door is of its recorder's tenant. A door serving several tenants through one recorder now discloses another tenant's caller under that tenant's own entitlement policy — `minimal` where that tenant registers none — instead of the recorder's tenant's level for the same client id. A deployment-supplied `disclosure_level_for` is now called with tenants other than the recorder's own and must answer for them; the SDK's `ControlPlaneProductEntitlementSource.disclosure_level_for` reads that tenant's policy and answers the safe default where none is registered. Records already written are unchanged.

## ccf_runtime.authz.product_entitlement.ControlPlaneProductEntitlementSource

- Surface: ccf_runtime.authz.product_entitlement.ControlPlaneProductEntitlementSource
- Public surface: true
- Change type: behavior
- Before: `disclosure_level_for`'s docstring stated that a delivery-boundary denial's entitlement pin and level pin can name different tenants, the level being read under the tenant whose door is answering.
- After: the docstring states that both are read under the tenant the determination was made under — for a delivery-boundary denial, the tenant the caller addressed — and that the earlier reading let a door's own tenant's policy for a colliding principal id set another tenant's caller's level. The method itself is unchanged: it answers for whichever tenant it is asked.
- Why: Dave, 2026-10-07 (`D-IMPL-378`); the recorder change above made the earlier statement false.
- Migration: none.

## ccf_runtime.mcp.experience.build_experience_server

- Surface: ccf_runtime.mcp.experience.build_experience_server
- Public surface: true
- Change type: behavior
- Before: an erasure a seam met was answered by the level read under the door recorder's tenant for the caller's principal id — the opaque `ccf-runtime-failure:<id>` at `minimal`, the recorded `erased-content` shell above it. On a door serving several tenants through one recorder, another tenant's caller took the branch the recorder's tenant declares for a principal with the same client id; measured with the recorder as shipped at `7bf069cc`, a `minimal` caller received the `erased-content` shell at `full`, carrying the erasure's reason, instant and record address.
- After: the branch is chosen by the level in force for the tenant the determination is made under and the caller's principal together — on `get_context`, `get_lineage` and `get_replay_record` the tenant handed to `govern_erasure`, so the branch and the recorded shell's level are one key; on `list_agents` and `invoke_agent` the capability's tenant. Measured on `get_context` in both directions; the other four call sites are the same one-key change, read from the code.
- Why: Dave, 2026-10-07 (`D-IMPL-378`), the adjacent sweep. Red test: `tests/mcp/test_experience_level_binds_the_tenant.py::test_the_erasure_branch_reads_the_level_in_force_for_the_callers_tenant_not_the_recorders`.
- Migration: none where every caller of a door is of its recorder's tenant. On a door serving several tenants through one recorder, another tenant's caller now receives the answer its own tenant's level selects.
