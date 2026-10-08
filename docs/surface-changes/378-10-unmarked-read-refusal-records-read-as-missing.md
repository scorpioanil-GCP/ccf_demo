# 378-10 — a read-refusal record without the marker reads as missing for everyone

`378-01` bound a read-refusal record to the tenant and the principal that
asked, and left one case open for a ruling: a read-refusal record minted
before that change names the door recorder's tenant whichever tenant asked,
and is byte-for-byte the record the door mints for its own tenant's principal
asking the same reference at the same instant, so nothing in it let the
governed read refuse it to a colliding principal and serve the other to its
owner. Dave's ruling (2026-10-07, Q3, `D-IMPL-378`), verbatim: *"(a) Old,
unmarked read-refusal records read as missing for everyone. The marker must
have trusted provenance; caller-supplied bytes cannot confer trust. Document
the loss of owner read-back."*

Every read-refusal record the governed read mints now carries a marker on its
resource identity, and the governed read answers a read-refusal record without
it exactly as a missing address, for every caller. The marker is written only
by the governed read and read only by it, in one step placed immediately after
its existing provenance check, so it counts only on bytes that check has
proved the fabric's record writer filed under the deciding tenant: a marked
record filed on a client lane confers nothing. **Owner read-back of a
read-refusal record minted before the marker is lost.**

## ccf.products.refusal.ResourceRequestIdentity

- Surface: ccf.products.refusal.ResourceRequestIdentity
- Public surface: true
- Change type: reshaped
- Before: four members — `surface`, `address`, `tenant_id`, `determined_at`. Nothing in a read-refusal record said whether its `tenant_id` was the tenant the refused capability was verified for (as `378-01` writes it) or the door recorder's (as the writer before `378-01` did); for the recorder's own tenant's principal the two records were byte-for-byte one.
- After: adds `tenant_from: Literal["capability"] | None`, hash-transparent at `None`. `"capability"` is the positive claim that `tenant_id` is the tenant the deciding capability was verified for, bound to the principal replay dimension 4 records. Only `ccf_runtime.authz.delivery_boundary.govern_dereference` writes it, on every read-refusal record it mints, and only it reads it. Every resource identity recorded before the field existed keeps its content address. A disclosed shell carries the resource identity at `full` only, so the marker crosses a door only at `full`.
- Why: Dave, 2026-10-07 (Q3; `D-IMPL-378`). Red tests: `tests/mcp/test_read_refusal_attribution_mcp.py::test_a_record_written_before_the_marker_is_told_apart_from_one_the_door_writes_today` and `::test_a_new_read_refusal_record_carries_the_marker_and_still_binds_who_asked`.
- Migration: none for a reader of the type: the member is optional and defaults to `None`. Code that builds its own `ResourceRequestIdentity` leaves it `None`; only the governed read states `"capability"`.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: a read-refusal record minted before `378-01` named the door recorder's tenant whichever tenant asked, and on a door serving several tenants through one recorder it still read for a principal of the recorder's tenant with the same client id as the principal it named (recorded as a strict expected failure).
- After: every read-refusal record it mints carries the marker (`ResourceRequestIdentity.tenant_from == "capability"`). One step, placed immediately after the provenance check and before hold 0, answers a read-refusal record without the marker exactly as a missing address — `nonexistent` / `evidence-absent`, recorded through the door's recorder, at every disclosure level — for every caller: the principal it names, another principal of the same tenant (who read `unauthorized` at hold 1 before) and another tenant's principal with the same client id. The marker is read in that step and nowhere else, so a record carrying it that the fabric's record writer did not file answers as missing: measured for a marked record filed on another tenant's client lane and on the tenant's own client lane, at the MCP artifact server's blob and presence resources, at HTTP `/replay/decisions`, `/replay/resolutions` and `/artifact`, and to `govern_dereference` called in process. With the provenance check severed those forgeries cross, so the marker confers trust only through it.
- Why: Dave, 2026-10-07 (Q3; `D-IMPL-378`). Red tests: `tests/mcp/test_read_refusal_attribution_mcp.py::test_a_read_refusal_record_written_before_the_marker_reads_as_missing_for_everyone`, `::test_a_marked_read_refusal_record_filed_on_a_client_lane_answers_as_a_missing_address_does` (both client lanes), `::test_a_marked_read_refusal_record_filed_on_a_client_lane_confers_nothing_on_an_in_process_governed_read`, `::test_read_refusal_records_from_before_and_after_the_binding_replay_to_their_own_addresses`; `tests/http_api/test_read_refusal_attribution_http.py::test_a_read_refusal_record_written_before_the_marker_reads_as_missing_for_everyone` and `::test_a_marked_read_refusal_record_filed_on_a_client_lane_answers_as_a_missing_address_does` (both client lanes).
- Migration: **owner read-back of read-refusal records minted before this change is lost.** Every read-refusal record minted before the marker answers as a missing address, through the HTTP evidence routes and the MCP artifact server's governed reads, to every caller — the principal it names included. The records are not rewritten: they stay in the store and still reconstruct at their own addresses through `ccf.replay.engine.replay_refusal` (`tests/mcp/test_read_refusal_attribution_mcp.py::test_read_refusal_records_from_before_and_after_the_binding_replay_to_their_own_addresses`); an examiner reads them from the store, not through a door. A read-refusal record minted from now on carries the marker and reads back for its own principal through the door whose recorder is its tenant's, as before.
