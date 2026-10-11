# 378-35 (R-A2) — replaying from an opened product: build the replay environment first

`D-IMPL-378` R-A2, ruled (a) by Dave on 2026-10-08 at 12:29 MST: *"Document the supported
replay-environment path."* Documentation and one test only; no SDK behavior changes. Built in lane
378e-small.

After R-A (b) (fragment 378-25), a process that builds its replay environment can replay earlier records,
served and refused, with nothing asked. One residual was left for this ruling: a process that only opens a
paved product cannot. `open_product` boots nothing, so the Control Plane the opened product holds carries
none of the declarations a record pins until a fabric is booted over it.

**Measured** in `tests/replay/test_paved_replay_needs_its_environment.py::test_an_opened_product_replays_an_earlier_record_only_after_its_environment_is_built`
(new), over one paved tree and one store, by a later opening with a Control Plane of its own:

- Opened only, asking nothing and building nothing, `replay_refusal` is refused at the first pinned binding
  the Control Plane does not hold, `ReplayUnresolvable`.
- After booting the recorded substrate read-only through `load_config_and_boot` over the opened product's
  documents and Control Plane, and building `RecordedEnvironment`, the same record reconstructs. Nothing is
  filed and nothing is acquired.

That is the supported path, and it is the one `examples/dr-01-replay-a-governed-determination/replay.py`
takes. It is now written where a replay user looks: the "Prerequisites, stated plainly" list of
`public/how-to/reconstruct-a-governed-determination.md`, and the docstrings below. Asking a question first
also makes the pins resolvable, but asking is a governed decision of its own, recorded like any other; the
how-to says so.

## ccf.replay.environment.RecordedEnvironment

- Surface: ccf.replay.environment.RecordedEnvironment
- Public surface: true
- Change type: behavior
- Before: same signature and behavior. The docstring did not say that a process which only opens a product must build this environment before it can replay
- After: same signature and behavior; documentation only. The docstring names this class as the supported way to replay from a process that did not answer the question, states the `ReplayUnresolvable` an open-only process meets, and says how to build it
- Why: `D-IMPL-378` R-A2 (a). Measured by `tests/replay/test_paved_replay_needs_its_environment.py::test_an_opened_product_replays_an_earlier_record_only_after_its_environment_is_built` and `tests/replay/test_fresh_process_replay.py::test_a_fresh_process_that_asked_nothing_replays_paved_road_records`
- Migration: none

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: same signature and behavior. The docstring said opening boots nothing
- After: same signature and behavior; documentation only. The docstring adds that a process which only opens cannot replay an earlier record until it builds the replay environment, `RecordedEnvironment`
- Why: `D-IMPL-378` R-A2 (a)
- Migration: none
