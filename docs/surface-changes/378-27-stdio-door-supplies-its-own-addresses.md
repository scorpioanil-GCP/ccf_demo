# 378-27 — the stdio product door supplies its own advertised addresses

Lane `378d-stdiodoor` of `D-IMPL-378`, built to Dave's ruling C2-A (b): *"the
stdio product door stops requiring the two advertised addresses (issuer and
resource) it never uses on stdio, for example by supplying its own values as the
loopback transport does; one change in `runtime/ccf_runtime/mcp/product_door.py`
with a surface fragment and a security review, the HTTP and loopback paths
untouched."*

The two addresses are OAuth discovery metadata. An HTTP door publishes them in
its protected-resource metadata and in the `resource_metadata` hint of a 401.
No token check and no authorization decision reads them. On stdio, `FastMCP`
builds no HTTP application, so nothing advertises them. The stdio door read
them from the environment only because the egress builder takes auth settings
together with the token verifier. That stopped every stdio door spawned by a
client that does not export two door variables (measured on hw1, lane
`378d-hw1door`). The security review is the lane's `SECURITY-REVIEW-C2A.md`.

## ccf_runtime.mcp.product_door.ProductDoor

- Surface: ccf_runtime.mcp.product_door.ProductDoor
- Public surface: true
- Change type: behavior
- Before: `serve_stdio` resolved the environment document's `door.issuer_url` and `door.resource_server_url` names from the process environment and raised `EnvironmentMissing`, with the document's remedy, when either variable was unset. That happened before anything was served, so a client spawning the door saw only a closed connection.
- After: `serve_stdio` reads neither name. It hands the egress builder the stdio transport's own values, `https://stdio.invalid` and `https://stdio.invalid/mcp`, both under the reserved `.invalid` domain that never resolves, and starts with both variables unset. `server` and `serve_loopback` are unchanged: their sources are byte-identical to the base. `server` still requires both addresses with no default, and the loopback transport still advertises its own bound address. With both variables unset, the stdio door still refuses a call naming another tenant (the tenancy guard) and a call for a class outside its scope mapping (the authorizer); the guard, the authorizer, the egress builder and the entitlement source are not edited. The class and module docstrings say so.
- Why: Dave's ruling C2-A (b) (`D-IMPL-378`, recorded on `main` at `3d21afa7`). Red tests at `0c6909a3`: `tests/mcp/test_stdio_door_addresses.py::test_a_stdio_door_with_both_addresses_unset_starts_answers_and_still_refuses`, and `tests/products/test_paved_road.py::test_the_stdio_door_reads_neither_door_url_and_advertises_only_reserved_addresses`, the rewrite of the test that asserted the superseded refusal. Controls that hold before and after: the self-hosted HTTP mount, the token decision across two advertised address pairs, and the loopback door.
- Migration: none required. A stdio deployment can stop exporting the two variables. Its environment document still names them, because `DoorEnvironment` still requires both names (see below).

## ccf.deployment.environment.DoorEnvironment

- Surface: ccf.deployment.environment.DoorEnvironment
- Public surface: true
- Change type: behavior
- Before: the docstring said both URL names "are consulted by every transport EXCEPT the loopback one".
- After: documentation only. The docstring says neither SDK transport reads them. Loopback advertises its own address, stdio supplies reserved values nothing advertises, and a deployment mounting `ProductDoor.server` under its own host resolves them and passes the values. The model is unchanged: both names are still required, so every existing environment document still loads.
- Why: the behavior change above made the old sentence false. Whether the two names should become optional, now that no SDK transport reads them, is a separate decision, raised in the lane's security review and not built here.
- Migration: none.
