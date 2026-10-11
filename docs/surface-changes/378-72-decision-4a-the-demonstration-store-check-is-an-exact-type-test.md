# 378-72 (decision 4 (a)) — demonstration time only over the SDK's own `FileArtifactStore` class, by exact type

`D-IMPL-378` decision 4, ruled by Dave on 2026-10-09 at 16:38 MST, adopting Grok's recommendation, verbatim:
*"(a) Exact type."* The option he ruled on (lane `378i-devref`'s P-1 (a)) reads: *"Tighten it to the SDK's own class:
an exact-type check (`type(store) is FileArtifactStore`). Consequences: a subclass is refused with
`artifact-store-not-development`."* It amends what fragment `378-50` left as it was ("It does not change the
artifact-store half"). Built in lane `378j-small2`. Nothing here changes a SEC row.

**The hole, measured.** The guard `src/ccf/products/demonstration_clock.py::_refuse_outside_development_substrates`
tested the composition's artifact store with `isinstance`, so an instance of any subclass of
`ccf.artifacts.file_store.FileArtifactStore` passed it. Red with `src/` and `runtime/` unchanged from the base: a
subclass that overrides nothing composed a `DeclaredServeClock` at `compose_serve_clock`, and at the in-process door
its question was served at the declared instant.

What holds now (`tests/client/test_demonstration_serve_instant.py`):

- The store check is `type(artifact_store) is FileArtifactStore`. A subclass, even one that overrides nothing, is
  refused at composition with `DemonstrationServeInstantRefused`, reason `artifact-store-not-development`:
  `test_a_subclass_of_the_sdks_file_store_is_refused_at_composition` and, where a deployment meets it,
  `test_a_subclass_of_the_sdks_file_store_is_refused_at_the_in_process_door`.
- The disclosed-limit test `test_a_subclass_of_the_sdks_file_store_passes_the_store_check`, which pinned the
  admission, failed by design once the check was tightened and was flipped:
  `test_a_subclass_of_the_sdks_file_store_fails_the_store_check` composes over the SDK's own class and over a
  subclass on one boot, and only the first gets the declared clock.
- SP §4.14's store sentence says so.

**Who is affected.** `git grep -nE "class [A-Za-z_0-9]+\([^)]*FileArtifactStore" -- .` on this tree finds two
subclasses: the test's own `_SubclassStore`, and `tests/workflow/test_restore_missing_approval_request.py::TraceStore`,
whose tests declare no demonstration serve instant. `compose_serve_clock` returns before the store check when the
tenant declares none, so a composition over a subclass that declares nothing is unaffected. The SDK's own compositions
construct `FileArtifactStore` itself.

**What this does NOT do.** It does not change the graph half (decision 6 (b), fragment `378-50`). No refusal class,
reason token, `key` attribute, record or content address changes; only the store refusal's message is reworded.

## ccf.products.demonstration_clock.compose_serve_clock

- Surface: ccf.products.demonstration_clock.compose_serve_clock
- Public surface: true
- Change type: behavior
- Before: same signature. Admitted a declared demonstration serve instant over an artifact store that is an instance of `FileArtifactStore`, so an instance of a subclass passed (`isinstance`)
- After: same signature. Admits a declaration only over an artifact store whose class is `FileArtifactStore` itself; a subclass, even one that overrides nothing, is refused with `DemonstrationServeInstantRefused`, reason `artifact-store-not-development`. The graph half is unchanged. `ccf.products.resolver.build_governed_resolver` and the in-process door call it, so both refuse the same way
- Why: `D-IMPL-378` decision 4 (a). Red tests: `tests/client/test_demonstration_serve_instant.py::test_a_subclass_of_the_sdks_file_store_is_refused_at_composition` and `tests/client/test_demonstration_serve_instant.py::test_a_subclass_of_the_sdks_file_store_is_refused_at_the_in_process_door`
- Migration: a composition that declared a demonstration serve instant over its own subclass of `FileArtifactStore` is now refused at composition; compose over `FileArtifactStore` itself. A composition whose tenant declares no demonstration serve instant is unaffected

## ccf.products.demonstration_clock.DemonstrationServeInstantRefused

- Surface: ccf.products.demonstration_clock.DemonstrationServeInstantRefused
- Public surface: true
- Change type: behavior
- Before: raised with reason `artifact-store-not-development` when the composition's artifact store was not an instance of `FileArtifactStore`
- After: raised with the same reason when the store's class is not `FileArtifactStore` itself, so also for an instance of a subclass. The message says a subclass is refused too. The `graph-substrate-not-development` reason, the `key` attribute and the `ValueError` base are unchanged
- Why: `D-IMPL-378` decision 4 (a)
- Migration: none for a caller that branches on the class or the reason token. A caller that matched the message text reads the new wording
