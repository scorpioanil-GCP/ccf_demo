# 377-07 — the governed read serves only what the fabric's record writer filed

The re-review of the `D-IMPL-376` close-out, confirmed by the coordinator:
the governed evidence read took a record's tenant (hold 0) and principal
(hold 1) from the bytes stored at the address and never checked who filed
those bytes. Anyone able to file an artifact — another tenant on its own
client lane, or a principal of this tenant on this tenant's client lane, each
with an ordinary `ArtifactWrite` — could file the canonical bytes of a
`DecisionReplayRecord` claiming tenant A and principal P, and P's governed
reads served them as P's own evidence: the MCP artifact server's blob and
presence resources, and HTTP `/replay/decisions`, `/replay/resolutions` and
`/artifact`, each `200`. Dave's ruling ("Fix now"): the governed read serves a
record only if the store shows it was filed by the fabric's own record writer
under the tenant the record claims; anything else answers exactly like a
missing address; a store that cannot answer that question refuses rather than
serves.

**Two limits, disclosed rather than changed** (both on the security page,
§4.10). (1) The MCP artifact server's client lane serves a tenant's own
client-lane filings to that tenant's principals without the governed read, so
a record-shaped forgery a principal files on its own tenant's client lane
still crosses the blob and presence resources as a client-lane artifact
(`tests/mcp/test_forged_record_mcp.py`, a strict expected failure); every
governed read refuses it. (2) A read-refusal record names the tenant of the
door that refused the read, whichever tenant the refused caller's capability
named, so on a door that serves several tenants through one recorder, a
principal of the door's tenant with the same client id reads another tenant's
principal's read-refusal records — the references it asked for, never content.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: the holds read the record's tenant and principal from the bytes at the address; nothing checked who filed those bytes, so a record-shaped forgery filed on any client lane was served to the principal it named.
- After: before any hold, the store's own naming (`names_at`) must show the address filed under the record's deciding tenant in a class the store's `WriteKinds` declares under `ReplayMint` — a kind no door can mint, held only by the fabric's record writers, which file a record only under the tenant it names. Anything else answers exactly as a missing address does: `nonexistent` / `evidence-absent`, recorded through the door's recorder, at every disclosure level. A store whose substrate answers no `names_at` or declares no `WriteKinds` raises `UnattributableDeliveryBoundaryError` before anything is read, recorded or clocked. Every caller inherits it: the HTTP evidence routes and the MCP artifact server's governed reads. Unchanged: genuine records read for their owners, the owner's own read-refusal chain reads (`D-IMPL-345` C20), and the C-2 tenant hold.
- Why: the forged-record finding (`D-IMPL-376` close-out). Red tests: `tests/http_api/test_forged_record_http.py::test_a_record_forged_on_another_tenants_client_lane_answers_as_a_missing_address_does` and `::test_a_record_forged_on_the_tenants_own_client_lane_answers_as_a_missing_address_does` (all three routes); `tests/mcp/test_forged_record_mcp.py::test_a_record_forged_on_another_tenants_client_lane_answers_as_a_missing_address_does` and `::test_a_store_that_cannot_attribute_an_address_refuses_rather_than_serves` (both parametrizations).
- Migration: a deployment-supplied artifact substrate behind a governed door answers `names_at` and declares `WriteKinds`, as the shipped `FileArtifactStore` and `McpArtifactStore` do. A record filed under a tenant other than the one it was decided under — a delivery-boundary denial addressed to another tenant at a door whose recorder is a different tenant's — no longer reads for anyone.

## ccf_runtime.authz.delivery_boundary.UnattributableDeliveryBoundaryError

- Surface: ccf_runtime.authz.delivery_boundary.UnattributableDeliveryBoundaryError
- Public surface: true
- Change type: added
- Before: absent.
- After: a `TypeError` `govern_dereference` raises when its store's substrate answers no `names_at` or declares no `WriteKinds`, so it cannot show who filed an address. Raised right after the capability check and the PM5 check, before anything is read, recorded or clocked: a wiring defect, refused where an operator sees it, never a determination about a caller — the posture of `UnconsultedDeliveryBoundaryError`.
- Why: the forged-record finding (`D-IMPL-376` close-out): "a store that cannot answer that question refuses rather than serves."
- Migration: none for the shipped stores.
