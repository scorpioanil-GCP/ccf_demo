# 378-35 (C1-late) — a running service keeps the demonstration serve instant it was built with

`D-IMPL-378` C1-late, ruled (a) by Dave on 2026-10-08 at 12:29 MST: *"Running services retain their
startup snapshot. Document that later registration takes effect only after rebuilding."* Documentation
and tests only; no SDK behavior changes. Built in lane 378e-small.

C1 (fragment 378-22) lets a deployment declare the instant it serves at. The declaration is read once,
when the resolver is built (`src/ccf/products/demonstration_clock.py::compose_serve_clock`, called by
`build_governed_resolver`). A declaration registered after that is not read by the built resolver. That
is the designed protection against switching a running service into demonstration mode (the C1 design's
threat T3), and the ruling keeps it.

**What rebuilding is, on each surface, measured** in `tests/client/test_demonstration_serve_instant.py`:

- **A composition root.** A declaration registered into its Control Plane after the resolver is built
  does not reach that resolver: its records keep the composed clock's `served_at` and pin no declaration
  (`::test_a_declaration_registered_after_composition_does_not_reach_the_resolver`). The next
  `build_governed_resolver` call over the same Control Plane reads it, serves at the declared instant and
  pins the declaration's exact version
  (`::test_a_declaration_registered_after_composition_takes_effect_only_in_a_resolver_built_after_it`,
  new).
- **The in-process adapter.** It boots each deployment once per process, building its Control Plane from
  the deployment's `ccf_config.yaml` at that boot
  (`src/ccf/client/adapters/inprocess.py::InProcessAdapter._ensure_booted`), so a declaration takes effect
  there when the process next starts.
- **The paved road.** *(Amended 2026-10-11 by fragment `20261011-01`, G1-SDK-01: the paved road now takes
  its snapshot at `open_product` and honors a declaration its `ccf_config.yaml` states at open when the
  caller composes no clock. The sentence that follows is the 2026-10-08 statement, kept as history.)* It
  builds a resolver for every question, but it composes its own clock, so it never honors a declaration. A declaration registered after `open_product` makes the next question raise
  `DemonstrationServeInstantConflict`, by name, before anything is acquired
  (`::test_the_paved_road_refuses_a_declaration_registered_after_open_at_the_next_question`, new). The
  standard door over an opened product calls the same `answer` (`src/ccf/products/product.py::OpenedProduct.resolve`).

**Where it is written down:** the docstrings below, the module docstrings of
`ccf.products.demonstration_clock` (rule 2) and `ccf.controlplane.demonstration_serve_instant`, the
security page's §4.14 (a new closing paragraph, the first public description of the declaration), and
fragment 378-22's ruling sentence.

## ccf.products.demonstration_clock.compose_serve_clock

- Surface: ccf.products.demonstration_clock.compose_serve_clock
- Public surface: true
- Change type: behavior
- Before: same signature and behavior. The docstring said it is called once, and the module docstring said C1-late was not ruled
- After: same signature and behavior; documentation only. The docstring states that the declaration it reads is the one the resolver serves on for its whole life, and that a later declaration takes effect only when a resolver is built again
- Why: `D-IMPL-378` C1-late (a): document that later registration takes effect only after rebuilding. Measured by `tests/client/test_demonstration_serve_instant.py::test_a_declaration_registered_after_composition_does_not_reach_the_resolver` and `::test_a_declaration_registered_after_composition_takes_effect_only_in_a_resolver_built_after_it`
- Migration: none

## ccf.client.adapters.inprocess.InProcessAdapter

- Surface: ccf.client.adapters.inprocess.InProcessAdapter
- Public surface: true
- Change type: behavior
- Before: same signature and behavior. The constructor's docstring said a declaration is honored and a clock beside it is refused, and did not say when the declaration is read
- After: same signature and behavior; documentation only. The docstring states that the declaration is read at the deployment's one boot per process, from its `ccf_config.yaml`, and that one declared later takes effect at the deployment's next boot, in a new process
- Why: `D-IMPL-378` C1-late (a)
- Migration: none
