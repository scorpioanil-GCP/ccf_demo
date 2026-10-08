# 378-25 — refusal records replay from their first question and from a freshly started process; the standard door holds its producer tenant on the structural path

Lane `378d-replayfix` of `D-IMPL-378`: two SDK defects the D-IMPL-378 "d" lanes
surfaced, remedied under CLAUDE.md §9's three-issue cap.

**Defect 1 — an audit record that could not be replayed (`CP17-F-09`,
`ATM-F-11`).** A governed refusal reached after the request was resolved
against its request contract — a resolution-stage refusal, the naive-instant
and temporal-bound refusals, a refusal held at either acquisition seam —
records that resolution on replay dimension 2, and with it the request
contract at the typed contract's own content address (`D-IMPL-310`: the pin
belongs there). The resolver registered that exact version only on the served
path, so the first question of a fresh Control Plane, refused, left a record
`replay_refusal` refused with `ReplayUnresolvable`, and whether a refusal
replayed depended on whether some served question had happened to run first in
the same process. Measured across the whole local suite before the change: 76
of 703 records built by a `GovernedResolver` pinned a request-contract version
not registered when the record was written; after it, 0 of 708. No record's
bytes, pins or address change: the same clock-pinned question sequence through
two composition roots (the in-process transport and the paved road) wrote 7
byte-identical records before and after, and each replays to its own address
after.

**Defect 1, second half — a freshly started process could not replay
(`D-IMPL-378` R-A (b), Dave, 2026-10-08).** The Control Plane is in-process,
and a boot registers no typed request contract, so a new process that booted
the deployment and asked nothing could not resolve the request-contract pin of
any earlier record, served or refused — measured on the original base and after
the first half alike. Dave ruled that the resolver also registers the contract
when it is built. After it, a new process that builds the deployment's resolver
— a transport's boot, the paved road's replay environment — replays earlier
served and refused records from the in-process transport and the paved road,
each to its own address, and a changed contract still fails replay by name. The
same 7 records are byte-identical on the original base, before this half and
after it. **What it does not reach:** the paved road boots nothing until a
question, so a fresh process that only opens a paved product cannot resolve
even the policy-bundle pin of an earlier record (it fails there first). The
supported replay environment (`RecordedEnvironment`), which boots the
question's substrate and builds the resolver, reconstructs it (measured).

**Defect 2 — `D-IMPL-343` R-6 on the structural door path.** R-6 holds a
door's declared `producer_tenant` to the deployment's tenant where a `door:`
section is derived (`src/ccf/deployment/config.py::_refuse_door_tenant_disagreement`).
A deployment composed by hand reached `open_door` with its own
`EgressDoorBinding` and nothing held it: the door opened and registered its
entitlement policy and scope mapping, and `ProductDoor.server` hands the
binding's `producer_tenant` to `build_egress_server` as the identity every
outcome asserts. R-6's own docstring states the consequence: every consumer
registered for the deployment's tenant refuses such a door
`producer-tenant-mismatch`, at the first remote question rather than at
composition. The config path is unchanged and still refuses first on the
paved road.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: `__call__` registered the typed request contract on its Control Plane only inside `GovernedResolver._register`, which the served path reaches and every refusal returns before. A refusal recorded after the resolution step pinned `(request_contract_key, content_hash(contract))` on dimension 2 while that version was unregistered unless an earlier served question in the same process had registered it, so `src/ccf/replay/engine.py::replay_refusal` raised `ReplayUnresolvable` naming the request-contract binding. And a new process held no registration of it until it had answered a question, so a process started to replay could not resolve that pin for any earlier record, served or refused.
- After: the resolver registers the typed request contract when it is built (`__post_init__`, under the `Register` capability its composition minted for that key; `D-IMPL-378` R-A), and again in `__call__` immediately before the resolution step (`CP17-F-09`); `_register` still registers the same content on the served path. Each registration is content-addressed and idempotent at the version every record decided under that contract pins, so record bytes, pins and addresses are unchanged. Any process that builds the deployment's resolver resolves that pin for every earlier record, a refusal asked first of a fresh Control Plane included; a changed contract registers at a different version, and the old pin stays unresolvable by name. A resolver built directly, not through `build_governed_resolver`, whose request-contract key names no contract is now refused when it is built with `ProductNotResolvable`; before, it was built. The docstrings of `__post_init__`, `__call__` (steps 2 and 5) and `_register` state this.
- Why: `CP17-F-09` (cp-17, charged to the cap at `D-GATE-cp-17`) and `ATM-F-11` (cp-19), carried unrepaired as estate-gated strict expected failures and reproduced offline on 2026-10-08; and `D-IMPL-378` R-A (b) for a freshly started process. Red tests: `tests/replay/test_first_question_refusal_replays.py` (the in-process transport with the request contract `role: load` and `role: register`, a resolution-stage and a temporal-bound refusal; the paved road with a refusal raised at the acquisition seam) and `tests/replay/test_fresh_process_replay.py` (a new Python process boots the deployment, asks nothing, and replays a served and a refused record from each of the in-process transport and the paved road). Guard: `tests/replay/test_fresh_process_replay.py::test_a_changed_request_contract_still_fails_replay_in_a_fresh_process`.
- Migration: none. Control Plane audit events, measured: building a resolver records one more `register` event, for the request-contract key (the in-process boot 25 → 26 events, `build_governed_resolver` 6 → 7, building a `RecordedEnvironment` 6 → 7, so building a replay environment now writes that one registration). Per question on the paved road, which builds a resolver for each question, compared with before this lane: an intent refusal and a floor refusal 0 → 1 `register` event for the request-contract key, a resolution-stage refusal 0 → 2, a served question 1 → 3. What each record pins is unchanged. Two strict expected failures keep `CP17-F-09` executable against the curated estate: `tests/examples/test_cp_17_replay.py::test_a_refusal_asked_first_of_a_fresh_product_reconstructs` and its `ATM-F-11` counterpart in `tests/examples/test_cp_19_replay.py`. They were not run for this change, because they need the estate. They assert the mechanism this change repairs, so they are run against the estate and their marks reviewed in the example migration set, not edited here.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: the `artifacts` docstring said a `role: load` artifact "is still absent from `pins`, still absent from the Control Plane registry, and still absent from replay dimension 2", which contradicted `D-IMPL-310`: a governed resolver registers and pins the typed request contract it derives from a `role: load` request-contract entry.
- After: documentation only. The boot registers and pins a `role: load` entry nowhere; a governed resolver built over the fabric registers, when it is built, the typed request contract under the same key, whatever the entry's role, and every decision that resolved a request against it pins it on dimension 2. Measured over the local suite: all 701 resolver-built records whose resolution ran pin the request contract, and none of the 7 not-applicable records do.
- Why: the record pinned what the docstring said it never would; `D-IMPL-310` rules the pin correct.
- Migration: none.

## ccf_runtime.mcp.product_door.open_door

- Surface: ccf_runtime.mcp.product_door.open_door
- Public surface: true
- Change type: behavior
- Before: a product whose `door` binding asserted a `producer_tenant` other than its `tenant_id` opened a door that registered its entitlement policy and scope mapping and asserted the other tenant on every outcome.
- After: refused with `ValueError` naming both tenants in R-6's own words ("the door binding asserts producer_tenant ... and this deployment's tenant is ...; ... (D-IMPL-343 R-6; D-IMPL-340 ruling 2)"), before the door records a composition decision or registers anything. A binding stating the product's tenant opens as before. A paved-road product whose `door:` section asserts another tenant is still refused first, at derivation, by `src/ccf/deployment/config.py::_refuse_door_tenant_disagreement`, with its unchanged message.
- Why: `D-IMPL-343` R-6 applied to the second path a door binding reaches (`D-IMPL-378`, found by lane `378d-hw1door`). Red test: `tests/mcp/test_product_door_producer_tenant.py`.
- Migration: a hand-composed deployment states its own tenant as its door binding's `producer_tenant`.

## ccf_runtime.mcp.product_door.open_door_with_verifier

- Surface: ccf_runtime.mcp.product_door.open_door_with_verifier
- Public surface: true
- Change type: behavior
- Before: as for `open_door`: a mismatched `producer_tenant` opened a door.
- After: the same refusal as `open_door`, raised by the shared `_boot_credential` before the deployment's verifier is consulted or anything is registered.
- Why: as for `open_door`. Red test: `tests/mcp/test_product_door_producer_tenant.py`, parametrized over both constructors.
- Migration: as for `open_door`.
