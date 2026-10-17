# 389-01 (D-IMPL-389, 2026-10-17) — the one-step replay rebuilds a composite decision from its record

`D-IMPL-389`, gap 3 of the skills feasibility probe. Dave, 2026-10-17 01:46 MST:
*"The one-step replay command must be able to replay a composite decision from the
record alone. Supply the missing `resolve_composite_plan` step in the setup that
`serve.py replay` builds, so the engine's existing composite path is reachable. No
change to the record format or to the engine's composite logic."*

Before this, `OpenedProduct.replay_decision` refused every decision that admitted a
child product: the environment it builds did not implement the engine's
`CompositeReplayEnvironment` seam, so the engine raised `ReplayUnresolvable` ("the
environment does not implement `resolve_composite_plan`"). Composite replay worked
only where a test built its own environment.

## ccf.replay.environment.RecordedEnvironment

- Surface: ccf.replay.environment.RecordedEnvironment
- Public surface: true
- Change type: behavior
- Before: implemented `ReplayEnvironment` only (`resolve_plan`, `resolve_operators`, `rehydrate_product`); `rehydrate_product` rebuilt every product with its own lineage and its own window, which is not what a composite was served with.
- After: also implements `CompositeReplayEnvironment`. `resolve_composite_plan(*, plan_id, children)` calls the deployment's plan factory exactly as the serve did — `build_with_children` over the children the engine rebuilt from the retained contracts when the factory implements `CompositePlanFactoryProtocol`, the plain call otherwise. `rehydrate_product` composes a composite's lineage (`compose_lineage`) and expiry (`compose_expiry`) from the members each ADMITTED child row already records (`child_operators_invoked`, `child_policy_bundle_versions`, `child_graph_snapshot_at`, `child_expires_at`), as `compose_children` did at decision time; an admitted row missing one of them raises `RecordedEnvironmentUnbuildable`. A decision that admitted no child keeps its own lineage and window. And `resolve_plan`, which the engine calls for a record that admitted no child, hands a child-aware factory an empty `ChildContractView` when the record carries child rows (a composite whose requirements were walked and none admitted), as the serve did; every other record gets the plain call as before (option (c), Dave 2026-10-17 09:41 MST). No producer is asked.
- Why: a governed composite decision must be reconstructable from its record and the store (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §D, "replay and reconstruct"). With the plan seam alone, served composites still diverged on their content address (lineage and expiry), measured. Red tests: `tests/replay/test_composite_replay_decision.py` — 6 failed on `d467d73d`, five on `ReplayUnresolvable` and one on `issubclass(RecordedEnvironment, CompositeReplayEnvironment)` being false; the no-child test for option (c) failed on `ReplayDivergence` on `88fc7429`.
- Migration: none. The record format and the replay engine are unchanged. Known limit, not fixed (Dave, 2026-10-17 09:41 MST): opening a product for replay with `read_sources=False` still requires each declared producer's endpoint and credential environment variable names (`ccf.skills.producers.ProducerEnvironmentMissing`), although replay asks no producer; set them before replaying.
