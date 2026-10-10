# 380-06 (sixth round, Grok's reviewed amendment) — the Control Plane registry holds and serves independent reconstructions at all five doors

`D-IMPL-380`, the dated amendments of 2026-10-10 14:44 and 15:10 MST, Dave, verbatim: *"The copy at the approver is
not a fix. The copy has the same content, so it is the address of the live object. `registry.peek` hands that
object back, and the sink rewrites it."* *"Copy on the way in at `:551`, `:611`, and `:794`. Copy on the way out
stays at `:839` and `:852`. That covers every artifact class, not only grants."* And at 15:50 MST, under Grok's
reviewed amendment: *"Use canonical serialization and reconstruction for both copy-in and copy-out. Shallow copies
are not accepted."* *"Do not fall back to the original object or a shallow copy."* Built in lane `380f-repair`, red
tests first. **SEC-020 stays OPEN**; no SEC row closes because this repair passes.

**What the tests measure, on test fixtures.** `tests/controlplane/test_registry_isolates_artifacts.py` (10 cases, 9
red at `ef84f801`): a rewrite of the original after `register`, `register_typed` or `register_versioned` reached the
registry under an unchanged version; a nested change to what `peek` or `resolve` returned reached a later read; two
successive reads reached each other. `tests/skills/test_grant_approval_sink_cannot_reach_the_ledgers_grant_through_the_registry.py`
(1 case, red at `ef84f801`): the fifth-round approval-sink copy was bypassable through `peek`, leaving the saved
grant hashing to something other than its id. `tests/controlplane/test_registry_isolation_refusal.py` (6 cases,
with the repair): a refusal leaves no version, class binding, bump entry or audit row, and a read refusal serves
nothing and reports nothing missing.

**Why a reconstruction and not a deep copy.** `copy.deepcopy` at the five sites was measured at `ef84f801`: 377
failures, every one `TypeError: cannot pickle 'mappingproxy' object`, because `ccf.workflow.definitions` wraps
`gate_routes` in nested `MappingProxyType` so the hash does not move. The artifact's own canonical form rebuilds
those proxies through its validators.

## ccf.controlplane.registry.ArtifactIsolationRefused

- Surface: ccf.controlplane.registry.ArtifactIsolationRefused
- Public surface: true
- Change type: added
- Before: no such refusal existed; every door shared the object it was given or held.
- After: a `TypeError` raised by any of the five doors when the artifact's reconstruction would not preserve its type, its canonical bytes or its value, carrying `artifact_type`, `door` and `reason`. On a write door nothing has changed when it is raised; on a read door nothing is returned and the artifact is not reported missing (it is never the `LookupError` that `ControlPlaneMissing` is).
- Why: `D-IMPL-380` sixth round, 15:50 MST: *"If copying fails, leave no newly published version, class binding or version-bump entry, and do not record a successful registration. On retrieval failure, do not return shared state or report the artifact as missing."* Tests: `tests/controlplane/test_registry_isolation_refusal.py`.
- Migration: none for a caller whose artifacts round-trip through their own canonical form, which every SDK artifact class does (`tests/controlplane/test_artifact_roundtrip.py`). A plain mapping registered through `register` that holds a `Decimal`, a `datetime` or a tuple is now refused rather than served with those values' types silently changed; none of the 53 plain-mapping registrations measured in the suite carries one.

## ccf.controlplane.registry.ControlPlaneRegistry

- Surface: ccf.controlplane.registry.ControlPlaneRegistry
- Public surface: true
- Change type: behavior
- Before: `register`, `register_typed` and `register_versioned` stored the registrant's own object by reference, and `peek` and `resolve` returned the stored object by reference, so a registrant that changed its original after registering changed the registry's content under an unchanged version, and a reader that changed what it was handed changed what every later reader saw — including the grant ledger's own `SkillGrant`, reachable by an approval sink through `peek` at the address the sink's content-identical copy supplied.
- After: each write door stores an independent reconstruction of the artifact — rendered to its canonical bytes, rebuilt through its own type's validators (or as the parsed document for a plain mapping), and verified to preserve the type, the canonical bytes and equality — built before any registration state changes; each read door returns a fresh reconstruction of the stored one. Two reads are independent at every depth; mapping-proxy protections survive because the validators re-create them. `peek` and `resolve` no longer return the same instance twice.
- Why: `D-IMPL-380` sixth round (14:44, 15:10 and 15:50 MST). The Fable seat's finding on the fifth-round delta review, reproduced by the coordinator at `ef84f801`. Red tests: `tests/controlplane/test_registry_isolates_artifacts.py`, `tests/skills/test_grant_approval_sink_cannot_reach_the_ledgers_grant_through_the_registry.py`. Measured cost at this commit: see the lane record.
- Migration: none for a caller that treats a resolved artifact as a value. A caller that compared two reads by identity, or mutated a returned artifact expecting a later read to show it, changes — no such caller was detected in the exercised tests (baseline 34 failures / 4 errors before and after, by id).
