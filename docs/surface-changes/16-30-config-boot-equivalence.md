# 16-30 — `load_config_and_boot`, and the equivalence proof

## What did **not** change

- `load_and_boot`'s signature is the same six-token line —
  `load_and_boot(manifest_path: str | Path, *, registry: ControlPlaneProtocol,
  connection: Mapping[str, object] | None = None, tenant_id: str | None =
  None) -> BootedFabric`, byte-identical to BASE, confirmed by
  `inspect.signature` comparison.
- `load_and_boot`'s refusal set is the same, from the same functions
  (`_resolve_tenant`, `_preflight_adapter`, `_resolve_secret_references`,
  `_document_inside_the_deployment`, the D-IMPL-84/D-IMPL-85 checks in the
  register loop) — every one of those functions is called by both doors now,
  never duplicated.
- `tests/deployment/test_manifest.py` — the standing regression net for
  `load_and_boot`, twelve enforced properties — passes with an **empty**
  `git diff --stat $BASE..HEAD -- tests/deployment/test_manifest.py`. The
  extraction (`_preflight_entries`, `_register_and_boot`) moved code; it did
  not change what that file asserts, and the file was not touched to make it
  pass.
- `ManifestEntry` still requires `role` and `registration` with no default
  (D-IMPL-80, D-IMPL-85) — this plan narrows nothing about that pair.
- **No file under `examples/` was written by any plan in this set.** Dave's
  dual-model ruling (2026-08-14): new examples are authored single-file;
  existing ones convert only when next rebuilt for their own reasons. The
  repository now carries a live running example of each authoring form:
  `examples/s1-00-companies-over-revenue` (multi-file, unedited) plus the
  equivalence proof's fixtures under `tests/` (this plan) and, prospectively,
  whichever example `16-31`'s single-file conversion targets — outside this
  plan's scope. `git diff --stat $BASE..HEAD -- examples/` is empty, in
  every task of this plan.
- `docs/schemas/` is untouched — `load_config_and_boot` adds no artifact
  class; it registers instances of classes `16-28` and `16-29` already
  shipped.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: added
- Before: did not exist
- After: `load_config_and_boot(config_path: str | Path, *, registry:
  ControlPlaneProtocol, connection: Mapping[str, object] | None = None,
  tenant_id: str | None = None) -> BootedFabric`. Parses a `ccf_config.yaml`,
  derives a `DeploymentManifest` plus its documents through
  `derive_deployment`, runs the same preflight `load_and_boot` runs
  (`_preflight_entries`, `_preflight_adapter`, `_resolve_secret_references`
  — the same three functions, imported and called, never re-implemented),
  validates every materialised document through `parse_artifact`, and calls
  the same `_register_and_boot` `load_and_boot` calls to register the
  `role: register` entries and boot. Returns the same `BootedFabric` shape:
  `handle`, `pins`, `tenant_id`, `artifacts` (both roles), `survivor_cap`
- Why: `D-IMPL-136` §10's compatibility commitment — *"existing multi-file
  deployments work unchanged"* — closed by construction rather than by
  convention: the register loop and the preflight are extracted, not
  duplicated, so the two doors cannot drift on the D-05 bump-check dispatch,
  the D-IMPL-80 role/pin distinction, or the containment check. Proved by
  `tests/deployment/test_config_equivalence.py` (a synthetic deployment
  authored both ways boots to an equal `ResolvedPins` and equal
  `BootedFabric.artifacts`) and
  `tests/examples/test_s1_00_config_equivalence.py` (HW-1's eight committed
  documents and a hand-authored single-file fixture register at identical
  content addresses, 8/8) — design spec §3's argument, now a regression test
  rather than an argument
- Migration: none. New surface; every existing multi-file deployment keeps
  working with no edit, and the multi-file form carries no deprecation date

## ccf.deployment.load_config_and_boot

- Surface: ccf.deployment.load_config_and_boot
- Public surface: true
- Change type: added
- Before: did not exist
- After: re-export of `ccf.deployment.config.load_config_and_boot` from
  `ccf.deployment.__init__`'s `__all__`, exactly as `load_and_boot` and
  `derive_deployment` are re-exported at the package — an adopter imports
  `from ccf.deployment import load_config_and_boot` alongside the rest of
  the wiring surface
- Why: package-level ergonomics, same reasoning as every other
  `ccf.deployment.*` re-export
- Migration: none. New surface

## What a `ccf_config.yaml` cannot express, for the record

There is no `signal_batch` section among the eight reserved names, and that
is a decision recorded at derivation time (`16-29`) and held to by this
plan's equivalence proof: `tests/deployment/test_config_equivalence.py`
excludes a `ccf.signal-batch` entry from its compared artifact set, named in
its own module docstring rather than silently dropped. Registering a signal
batch would content-hash raw event data into Control Plane state and
therefore into Decision Replay dimension 2 (`D-IMPL-80`) — events are what
the fabric *observed*, not what it was *permitted to do*. A deployment that
needs one keeps a manifest, which the dual model supports indefinitely
(Dave's ruling, 2026-08-14), and boots it through `load_and_boot` instead of
`load_config_and_boot`.

## The three-lines-not-two divergence from design spec §6.1, restated here

`16-29` recorded that an adopter-owned section (`policy`, `request_contract`)
states **three** bookkeeping lines — `class_id` alongside `role` and
`registration` — where design spec §6.1 originally said two, corrected by
Dave's ruling `D-IMPL-138`(a) on 2026-08-15. `derive_deployment` cannot
derive an adopter's `class_id` from the section name without inventing an
adopter namespace, which `D-IMPL-84` forbids by reserving exactly one prefix,
`ccf.`. This plan's equivalence fixtures (both halves) state all three lines
on every adopter-owned section they author, which is what makes them
authorable at all under the corrected rule — restated here because a fragment
reader arriving at `16-30` alone, without having read `16-29`'s fragment,
would otherwise not know why.
