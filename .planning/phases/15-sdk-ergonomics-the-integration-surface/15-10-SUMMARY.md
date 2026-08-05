---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 10
subsystem: deployment
tags: [manifest, boot, control-plane, replay, d-impl-80]
requires: ["15-09", "15-06", "15-07"]
provides:
  - "ccf.deployment.load_and_boot — the load-validate-register-boot entry point"
  - "ccf.deployment-manifest artifact class (DeploymentManifest / ManifestEntry)"
  - "ResolvedPins / ArtifactPin — the pin record, register-role only"
  - "SDK_ARTIFACT_ROLES + refuse_role_the_sdk_fixes — D-IMPL-80, machine-checked"
affects:
  - "15-13 through 15-20 (example rewrites consume load_and_boot)"
  - "15-21 (surface close; twenty names claimed in this plan's fragment)"
tech-stack:
  added: []
  patterns:
    - "preflight-before-registration (backend, tenant, role)"
    - "two-phase parse-then-register"
    - "SDK-fixed artifact roles as a class-keyed mapping"
key-files:
  created:
    - src/ccf/deployment/manifest.py
    - src/ccf/deployment/pins.py
    - tests/deployment/test_manifest.py
    - docs/surface-changes/15-10-manifest.md
  modified:
    - src/ccf/controlplane/artifacts.py
    - src/ccf/deployment/classes.py
    - src/ccf/deployment/__init__.py
    - tests/deployment/conftest.py
    - tests/deployment/test_class_lookup.py
    - tests/controlplane/test_artifact_roundtrip.py
decisions:
  - "Manifest contracts live in ccf.controlplane.artifacts, not ccf.deployment.manifest — artifacts -> deployment.manifest -> deployment.classes -> artifacts closes an import cycle at import time"
  - "Backend/tenant/role preflight runs before any parse or registration, not beside the boot call (cross-AI review finding, verified real)"
  - "D-IMPL-80 enforced twice: required Literal field (silence) plus SDK_ARTIFACT_ROLES (wrongness)"
  - "DeploymentManifest refuses a manifest whose two boot pins do not name role: register entries"
metrics:
  duration: ~50m
  tasks: 3
  completed: 2026-08-04
---

# Phase 15 Plan 10: Deployment Manifest and Entry Point Summary

One manifest-driven call replaces the fourteen-line registration prologue before
every `boot()`, with the register-versus-load boundary (D-IMPL-80) enforced
mechanically rather than by docstring, and every refusal path proven to leave
the Control Plane untouched.

## What was built

**`ccf.deployment.load_and_boot`** — reads a manifest, preflights, parses every
named artifact, registers the `role: register` ones, boots, and returns a
`BootedFabric` carrying the handle, the pins, the resolved tenant, and every
parsed artifact keyed by manifest key.

**`ccf.deployment.pins`** — `ArtifactPin` and `ResolvedPins`, with exactly one
accessor. The module docstring states why `version_for` is lookup rather than
selection and why a `pins.policy_bindings()` convenience is a
governance-boundary move; a test pins the public method set exactly.

**The `ccf.deployment-manifest` artifact class** — `ManifestEntry` (path, key,
class_id, required `role`) and `DeploymentManifest` (artifacts, backend *kind*,
the two boot keys, optional tenant), refusing globs, duplicate keys, and boot
pins that name unregistered entries.

`boot()` is byte-for-byte unchanged and remains directly callable (D-14 is
additive).

## The cross-AI review finding — real, and fixed

> *"a manifest declaring `postgres` without `postgres_dsn` could still parse and
> register artifacts before failing at boot"*

**Verified against the plan text before acting: the concern was genuine.** The
plan's step 6 placed the backend check at the `boot()` call, after the
registration loop in step 3. A manifest declaring `postgres` with no DSN parses
perfectly well, so every artifact would have registered and *then* the call would
have failed — leaving Control Plane state from a fabric that never booted. That
is a replay-integrity problem: the registry would answer "what was in force" for
a deployment that never ran.

`_preflight_backend` now runs before any document is read, and refuses both the
missing-argument case and the wrong-argument case. Two tests assert the refusal
path leaves **both** the version index and the audit log empty
(`test_the_backend_preflight_runs_before_anything_is_registered`,
`test_sqlite_declared_with_no_database_path_fails_the_same_way`), plus the
plan's own test 4 asserting no SQLite file exists anywhere under `tmp_path`.

## D-IMPL-80 — the role enforcement I owned

15-09 shipped three prose defenses and stopped at the manifest boundary,
recording that nothing yet *prevented* `role: register` on `ccf.signal-batch`
and that no CI failure would fire. Two mechanisms now close it:

1. **`role` is a required `Literal["register", "load"]` with no default** — the
   choice is never made silently, and never by the SDK.
2. **`SDK_ARTIFACT_ROLES` + `refuse_role_the_sdk_fixes`** in `classes.py` — the
   choice is never made *wrongly* for the one class where the SDK knows the
   answer. I took 15-09's suggested class-id-keyed rule and generalized it one
   step: a mapping keyed on class id rather than a hardcoded comparison, so a
   future class the SDK must fix is a one-line addition. **Every class absent
   from the mapping is the adopter's call, and that is the default** — the SDK
   fixes a role only where it can say why.

The check runs in the preflight, so a manifest that would have put raw event
data into replay dimension 2 never registers anything at all.
`test_the_sdk_refuses_a_register_role_on_the_signal_batch` asserts the audit log
is empty on that path.

## Deviations from Plan

### Structural

**1. Manifest contracts live in `ccf.controlplane.artifacts`, not
`ccf.deployment.manifest`.** The plan placed `DeploymentManifest`/`ManifestEntry`
in `manifest.py` while also asking that `DEPLOYMENT_MANIFEST` be added to
`artifacts.py` and registered in `SDK_ARTIFACT_CLASSES`. Those two instructions
close a cycle: `artifacts -> deployment.manifest -> deployment.classes ->
artifacts`, which fails at *import* time, not lint time. Resolved by putting the
contracts where every other artifact contract already lives, and keeping
`manifest.py` to `load_and_boot` and `BootedFabric`. Both names are re-exported
at the `ccf.deployment` package root, so the adopter-facing import is unchanged.
This is the same class of constraint 15-07 recorded for `artifact_base.py`.

### Auto-fixed Issues

**2. [Rule 2 - Missing validation] The manifest's two boot pins must name
`register` entries**
- **Found during:** Task 1
- **Issue:** `boot()` needs a pinned version for the resolution spec and the
  policy bundle, and those versions come from the pin set — which carries
  `register` entries only. A manifest naming a key that is absent, or present
  under `role: load`, describes a deployment that cannot boot, and would have
  failed only *after* registering everything else.
- **Fix:** a second `model_validator` on `DeploymentManifest` refusing it at
  parse. Same preflight logic as the backend finding, applied one level up.
- **Files:** `src/ccf/controlplane/artifacts.py`
- **Commit:** 3eba24d

**3. [Rule 1 - Bug] 15-06's fragment parser dropped the last section of the last
fragment**
- **Found during:** Task 3
- **Issue:** `_fragment_public_added` in `tests/deployment/test_class_lookup.py`
  appends a `"## "` end-of-file sentinel, but the loop calls `.strip()` first,
  reducing it to `"##"` — which fails the `startswith("## ")` flush test. The
  final section of the lexicographically-last fragment was therefore never
  counted. It went unnoticed because 15-09's last section is
  `Public surface: false` and so was invisible to the assertion either way.
  It surfaced here as a false `added but unclaimed:
  ['ccf.deployment.refuse_role_the_sdk_fixes']`.
- **Fix:** sentinel changed to `"## eof"`, with a comment recording the trap.
- **Files:** `tests/deployment/test_class_lookup.py`
- **Commit:** aa747f2

**4. [Rule 2 - Missing coverage] Round-trip case for the new artifact class**
- **Found during:** Task 3 (`make ci-core`)
- **Issue:** `tests/controlplane/test_artifact_roundtrip.py` has a standing
  vacuity guard asserting every `SDK_ARTIFACT_CLASSES` entry has a round-trip
  case. Adding `ccf.deployment-manifest` without one failed it — the guard
  working exactly as designed.
- **Fix:** added the case, with `postgres_dsn` and `database_path` as the
  closed-world unknown keys, so the D-08 no-DSN-field property is asserted by
  the closed-world test rather than only stated in a docstring.
- **Files:** `tests/controlplane/test_artifact_roundtrip.py`
- **Commit:** aa747f2

### Test count

The plan specified eleven tests; the module has 22 test functions covering those
eleven concerns. Several concerns are naturally more than one function — tenant
resolution is four directions, the backend refusal is four cases (missing
argument each way, wrong argument, and the registry/audit-untouched assertion),
and globs are parametrized over three pattern characters. Splitting them means a
failure names which direction broke.

## Anti-pattern avoided

The known trap — a test comparing **one plan's** claims against
**phase-accumulated** state — was avoided by *not writing one*. Task 3's
acceptance criterion asking for a subset-equality check between `--report` output
and this plan's fragment is **already satisfied phase-wide** by
`tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added`,
which 15-06 wrote and 15-07 widened to scan every fragment for exactly this
reason. Adding a second, plan-scoped version would have reintroduced the trap in
its purest form. The existing test passes with this plan's fragment in place,
which is the assertion the criterion wanted.

## Verification

- `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/deployment/ tests/products/ tests/test_surface_drift.py -q` — 60 passed
- `.venv/bin/python -m tools.lints --all` — exit 0
- `make typecheck` — 166 files, no issues
- `make ci-core` — **1712 passed, 2 skipped**
- `grep -c "resolve_latest\|yaml.safe_load\|ControlPlaneRegistry("` on `manifest.py` — 0
- `git status` on `src/ccf/boot.py` — clean, unchanged
- `docs/surface/v0.2-surface.json` and `v0.2-surface-baseline.json` — untouched;
  `tools/dump_surface.py --report` run read-only, this plan's twenty names
  confirmed present in its `added` list

## Known Stubs

None.

## Threat Flags

None. The plan's threat register is fully covered: T-15-10-01 (glob refusal +
the dropped-in-file test), T-15-10-02 (loud postgres failure, no SQLite file),
T-15-10-03 (no writer on the handle), T-15-10-04 (determinism, `resolve_latest`
absent, duplicate keys refused), T-15-10-05 (no DSN field, asserted by the
closed-world round-trip case), T-15-10-06 (gate-independence guard and lint both
still pass), T-15-10-07 (role required + SDK-fixed, asserted against the audit
log), T-15-10-08 (two-phase ordering, asserted).

## Notes for the next plan

- `load_and_boot`'s docstring names the post-call spine 15-13 needs: ingest from
  `booted.artifacts[<batch-key>].envelopes`, assemble the operator `parameters`
  mapping by naming manifest keys against `booted.artifacts`, and mint MAX_TTL
  and the product-class registration in adopter code.
- **The Gate 2 tautology is not entrenched.** `load_and_boot` never touches the
  operator registry, never constructs a projection, and never names
  `required_operator_keys`. The authored source 15-09 created remains
  independent, and 15-21's AST guard has an unobstructed target.
- `tests/deployment/conftest.py`'s `deployment` fixture is a complete,
  copy-ready authoring example of a manifest plus its ten artifacts, including
  the `role: load` split.

## Self-Check: PASSED

All created files verified present on disk (`src/ccf/deployment/manifest.py`,
`src/ccf/deployment/pins.py`, `tests/deployment/test_manifest.py`,
`docs/surface-changes/15-10-manifest.md`). All three task commits verified in
`git log`: 3eba24d, 41e102d, aa747f2.
